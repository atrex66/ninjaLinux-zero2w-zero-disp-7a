#!/usr/bin/python3
"""Prepare/apply a backed-up Raspberry Pi CPU layout. Never reboot or start outputs."""
import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile

from cpu_layout import load_layout, online_cpus

PROJECT = Path(__file__).resolve().parents[1]


def cpu_list(cpus):
    return ','.join(str(cpu) for cpu in sorted(cpus))


def boot_line(text, layout):
    if len(text.strip().splitlines()) != 1 or not any(t.startswith('root=') for t in text.split()):
        raise ValueError('Expected a single-line Raspberry Pi kernel command line with root=')
    settings = {'isolcpus': 'domain,managed_irq,' + cpu_list([layout['ui_cpu'], layout['hal_cpu']]),
                'irqaffinity': cpu_list(layout['system_cpus'])}
    tokens = [t for t in text.split() if t.split('=', 1)[0] not in settings]
    return ' '.join(tokens + [f'{k}={v}' for k, v in settings.items()]) + '\n'


def planned_files(root, config):
    layout = load_layout(config)
    system = ' '.join(map(str, sorted(layout['system_cpus'])))
    files = {'/etc/automation-hal/cpu-layout.json': json.dumps(layout, indent=2) + '\n',
             '/etc/systemd/system.conf.d/90-automation-cpu.conf':
                 f'[Manager]\nCPUAffinity=\nCPUAffinity={system}\n',
             '/etc/systemd/system/irqbalance.service.d/90-automation-cpu.conf':
                 '[Service]\nEnvironment=IRQBALANCE_BANNED_CPULIST=' + cpu_list([layout['ui_cpu'], layout['hal_cpu']]) + '\n'}
    for unit, role in [('automation-hal', 'hal'), ('magorautomate-hal', 'hal'), ('magorautomate', 'ui')]:
        cpu = layout[role + '_cpu']
        files[f'/etc/systemd/system/{unit}.service.d/90-automation-cpu.conf'] = (
            '[Service]\nEnvironment=AUTOMATION_CPU_CONFIG=/etc/automation-hal/cpu-layout.json\n'
            f'Environment=RTAPI_CPU_NUMBER={layout["hal_cpu"]}\n'
            f'CPUAffinity=\nCPUAffinity={cpu}\nAllowedCPUs={cpu}\n')
    boot = root / 'boot/firmware/cmdline.txt'
    files['/boot/firmware/cmdline.txt'] = boot_line(boot.read_text(), layout)
    # Both files are pure Python: no target architecture/toolchain dependence.
    for name in ('cpu_layout.py', 'runner.py'):
        files['/opt/automation-hal/libexec/' + name] = (PROJECT / 'tools' / name).read_text()
    return files


def write_atomic(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.cpu-layout-', delete=False) as f:
            name = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


def install(root, files):
    backup = root / 'var/backups/automation-hal' / datetime.now().strftime('cpu-layout-%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True, mode=0o700)
    manifest = {}
    for name in files:
        path = root / name.lstrip('/')
        if path.is_symlink():
            raise ValueError(f'Refusing to replace symlink: {path}')
        manifest[name] = {'data': base64.b64encode(path.read_bytes()).decode(), 'mode': path.stat().st_mode & 0o777} if path.exists() else None
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    (backup / 'planned.json').write_text(json.dumps(files, indent=2))
    # Install the helper before enabling the profile; change the boot line last.
    order = sorted(files, key=lambda name: (0 if '/libexec/' in name else 2 if name.startswith('/boot/') else 1, name))
    written = []
    try:
        for name in order:
            before = manifest[name]
            mode = before['mode'] if before else (0o755 if name.endswith('/runner.py') else 0o644)
            write_atomic(root / name.lstrip('/'), files[name].encode(), mode)
            written.append(name)
    except Exception:
        for name in reversed(written):
            path = root / name.lstrip('/')
            before = manifest[name]
            if before is None:
                path.unlink(missing_ok=True)
            else:
                write_atomic(path, base64.b64decode(before['data']), before['mode'])
        raise
    return backup


def restore(backup):
    backup = Path(backup).resolve(strict=True)
    parent = Path('/var/backups/automation-hal').resolve()
    if backup.parent != parent:
        raise ValueError('Restore only accepts /var/backups/automation-hal/cpu-layout-*')
    manifest = json.loads((backup / 'manifest.json').read_text())
    for name, data in manifest.items():
        path = Path(name)
        if data is None:
            path.unlink(missing_ok=True)
        else:
            write_atomic(path, base64.b64decode(data['data']), data['mode'])
    subprocess.run(['systemctl', 'daemon-reload'], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=PROJECT / 'packaging/cpu-layout.json')
    parser.add_argument('--root', type=Path, default=Path('/'), help='staging root for review/tests')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.restore:
        if root != Path('/') or os.geteuid() != 0:
            parser.error('Restoring system files requires root on the target')
        restore(args.restore)
        print('Files restored; reboot to restore kernel/system CPU placement.')
        return
    files = planned_files(root, args.config)
    if not args.apply:
        print(json.dumps(files, indent=2))
        return
    if root == Path('/'):
        if os.geteuid() != 0:
            parser.error('Use sudo on the identified target')
        model = Path('/proc/device-tree/model').read_text()
        if 'Raspberry Pi' not in model or not Path('/boot/firmware').is_mount():
            parser.error('Expected a Raspberry Pi with mounted /boot/firmware')
        layout = load_layout(args.config)
        if not {layout['hal_cpu'], layout['ui_cpu'], *layout['system_cpus']} <= online_cpus():
            parser.error('The CPU layout requires unavailable CPUs')
        if 'cpuset' not in Path('/sys/fs/cgroup/cgroup.controllers').read_text().split():
            parser.error('cgroup v2 cpuset controller is required for AllowedCPUs')
        if not Path('/opt/automation-hal/bin/ahal').is_file():
            parser.error('Standalone Automation HAL must already be installed')
    backup = install(root, files)
    if root == Path('/'):
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
    print(f'Backup: {backup}\nApplied files only. Reboot required for kernel isolation and system defaults. No service restarted.')


if __name__ == '__main__':
    main()
