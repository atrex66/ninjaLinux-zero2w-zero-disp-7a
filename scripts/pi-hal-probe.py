"""Run as ahal via `ahal python`; record period error in the existing session.

The RT component counts every cycle. Briefly stop the software-only test
thread at the end to read a consistent histogram, then restart it.
"""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import hal

folder = Path(sys.argv[1])
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 130
ahal = '/opt/automation-hal/bin/ahal'

def cmd(*args):
    return subprocess.run([ahal, 'cmd', *args], check=True,
                          text=True, capture_output=True).stdout

observer = hal.component('ninjalinux-probe-observer')
try:
    observer.newpin('python-binding-test', hal.HAL_BIT, hal.HAL_IN)
    observer.ready()
    observer['python-binding-test'] = True
    assert observer['python-binding-test'] is True
    hal.set_p('ninja-latency.0.reset', 'TRUE')
    time.sleep(.05)
    irq_before = Path('/proc/interrupts').read_text()
    began = time.monotonic()
    hal.set_p('ninja-latency.0.reset', 'FALSE')
    record = dict(probe_start_monotonic=began, success=False,
                  kernel=platform.release(), period_ns=1000000,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  isolated=Path('/sys/devices/system/cpu/isolated').read_text().strip(),
                  python_binding_test=True, metric='absolute HAL period error',
                  interrupts_before=irq_before)
    (folder / 'conditions.json').write_text(json.dumps(record, indent=2))
    time.sleep(max(0, began + duration - time.monotonic()))
    cmd('stop')
    try:
        time.sleep(.02)
        fields = ('interval-ns', 'minimum-ns', 'maximum-ns', 'jitter-ns',
                  'current-error-ns', 'mean-jitter-ns', 'samples', 'long-intervals')
        values = {key: hal.get_value('ninja-latency.0.' + key) for key in fields}
        histogram = [hal.get_value(f'ninja-latency.0.histogram-{i:02d}')
                     for i in range(128)]
        assert sum(histogram) == int(values['samples'])
        record.update(values=values, histogram=histogram,
                      end_monotonic=time.monotonic(),
                      interrupts_after=Path('/proc/interrupts').read_text(),
                      thread=cmd('show', 'thread'))
        assert record['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    finally:
        cmd('start')
    record['success'] = True
    (folder / 'hal-result.json').write_text(json.dumps(record, indent=2) + '\n')
finally:
    observer.exit()
