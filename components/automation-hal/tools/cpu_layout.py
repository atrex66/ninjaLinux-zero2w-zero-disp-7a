#!/usr/bin/python3
"""Shared CPU layout for HAL and its UI; fail closed if pinning fails."""
import argparse
import json
import os
from pathlib import Path
import sys

DEFAULT_CONFIG = Path('/etc/automation-hal/cpu-layout.json')


def load_layout(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or set(data) != {'version', 'hal_cpu', 'ui_cpu', 'system_cpus'}:
        raise ValueError('CPU layout requires version, hal_cpu, ui_cpu and system_cpus')
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Unsupported CPU layout version')
    system = data['system_cpus']
    if not isinstance(system, list) or not system:
        raise ValueError('system_cpus must be a nonempty list')
    cpus = [data['hal_cpu'], data['ui_cpu'], *system]
    if any(type(cpu) is not int or not 0 <= cpu < 1024 for cpu in cpus):
        raise ValueError('CPU indices must be integers between 0 and 1023')
    if len(set(cpus)) != len(cpus):
        raise ValueError('HAL, UI and system CPUs must be distinct')
    return data


def online_cpus():
    result = set()
    for item in Path('/sys/devices/system/cpu/online').read_text().strip().split(','):
        bounds = item.split('-')
        result.update(range(int(bounds[0]), int(bounds[-1]) + 1))
    return result


def selected_config(explicit=None):
    if explicit is not None:
        return Path(explicit)
    value = os.environ.get('AUTOMATION_CPU_CONFIG')
    if value:
        return Path(value)
    return DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else None


def apply_role(role, path):
    path = Path(path).resolve(strict=True)
    layout = load_layout(path)
    required = {layout['hal_cpu'], layout['ui_cpu'], *layout['system_cpus']}
    missing = required - online_cpus()
    if missing:
        raise ValueError(f'CPU layout references offline/unavailable CPUs: {sorted(missing)}')
    target = {layout[role + '_cpu']} if role in ('hal', 'ui') else set(layout['system_cpus'])
    # Deliberately permit widening an inherited taskset/CPUAffinity mask.
    # A cgroup cpuset restriction still applies; readback must match exactly.
    os.sched_setaffinity(0, target)
    actual = os.sched_getaffinity(0)
    if actual != target:
        raise RuntimeError(f'CPU pinning failed: requested {sorted(target)}, effective {sorted(actual)}')
    os.environ['AUTOMATION_CPU_CONFIG'] = str(path)
    os.environ['RTAPI_CPU_NUMBER'] = str(layout['hal_cpu'])
    print(f'Automation CPU: {role} -> {sorted(actual)}; HAL RT -> CPU{layout["hal_cpu"]}', file=sys.stderr)
    return layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=selected_config() or DEFAULT_CONFIG)
    parser.add_argument('--role', choices=('hal', 'ui', 'system'), required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        parser.error('A command to execute is required after --')
    apply_role(args.role, args.config)
    os.execvp(command[0], command)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        sys.exit(f'Automation CPU: {exc}')
