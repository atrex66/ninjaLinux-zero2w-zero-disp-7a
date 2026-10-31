#!/usr/bin/env python3
"""Validate the stored target evidence and emit a compact comparison report."""
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1])
raw = folder / 'hal-load1'
result = json.loads((raw / 'hal-result.json').read_text())
network = json.loads((raw / 'network-load.json').read_text())
before = json.loads((folder / 'context-before.json').read_text())
after = json.loads((folder / 'context-after.json').read_text())
ui = json.loads((folder / 'ui-after.json').read_text())

def interrupts(text):
    parsed = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        name, tail = line.split(':', 1)
        parts = tail.split()
        if len(parts) >= 4 and all(x.isdigit() for x in parts[:4]):
            parsed[name.strip()] = (list(map(int, parts[:4])), ' '.join(parts[4:]))
    return parsed

def deltas(record):
    a, b = (interrupts(record['interrupts_' + when]) for when in ('before', 'after'))
    return {irq: dict(counts=[y-x for x,y in zip(a[irq][0], values[0])],
                      description=values[1]) for irq, values in b.items() if irq in a}

irq = deltas(result)
assert result['success'] and result['python_binding_test']
assert result['boot_id'] == before['boot_id'].strip() == after['boot_id']
assert result['isolated'] == '2-3'
assert network['sent_bytes'] == network['expected_bytes'] == 70 * 1024**2
assert result['probe_start_monotonic'] <= network['start_monotonic'] < network['end_monotonic'] <= result['end_monotonic']
assert sum(result['histogram']) == result['values']['samples']
armctrl = {k:v for k,v in irq.items() if 'ARMCTRL' in v['description']}
assert armctrl and all(v['counts'][2:] == [0,0] for v in armctrl.values())
usb = [v for v in armctrl.values() if 'usb' in v['description']]
assert usb and sum(sum(v['counts']) for v in usb) > 0
rt = [t for t in after['tasks'] if t['comm'].startswith('rtapi_app:T#')]
assert rt and all(t['policy'] == 1 and t['priority'] == 98 and t['cpus'] == [3] for t in rt)
assert all(t['cpus'] == [0,1] for t in after['tasks'] if t['comm'].startswith('irq/'))
assert before['ui_log'].find('PYSIDE_GL_RENDERER: VC4 V3D 2.1') >= 0
assert ui['pid'] == int(after['ui_pid']) and ui['cpus'] == [2]
assert ui['boot_id'] == result['boot_id']

report = dict(validated=True, kernel=result['kernel'], period_us=1000,
    sample_count=int(result['values']['samples']),
    observed_window_s=result['end_monotonic']-result['probe_start_monotonic'],
    max_absolute_period_error_us=result['values']['jitter-ns']/1000,
    mean_absolute_period_error_us=result['values']['mean-jitter-ns']/1000,
    long_intervals_ge_two_periods=result['values']['long-intervals'],
    network_payload_bytes=network['sent_bytes'],
    armctrl_irq_deltas=armctrl, all_irq_deltas=irq,
    rt_threads=rt, same_boot=True,
    limitations=['Short software-only HAL trial; no physical motion I/O.',
                 'Period error is not cyclictest wake-up latency.',
                 'Local timer and IPIs remain; NO_HZ_FULL/RCU offload disabled.',
                 'No target CPU temperature reading; no worst-case guarantee.',
                 'No controlled touch stimulus or sustained SD stress in this trial.'])
(folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('all_irq_deltas','armctrl_irq_deltas')}, indent=2))
