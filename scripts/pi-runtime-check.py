#!/usr/bin/env python3
"""Read-only target acceptance snapshot; run as root after starting the demo HAL."""
import gzip
import json
import os
from pathlib import Path
import platform
import re

def read(path):
    return Path(path).read_text()

config = gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
assert 'CONFIG_PREEMPT_RT=y\n' in config
assert platform.release() == '6.12.61-ninjalinux-rt-irq1'
isolated = read('/sys/devices/system/cpu/isolated').strip()
assert isolated == '2-3'
ui_pid = int(read('/run/fastlinux-ui.pid'))
assert sorted(os.sched_getaffinity(ui_pid)) == [2]
ui_log = read('/tmp/fastlinux-ui.log')
assert 'PYSIDE_GL_RENDERER: VC4 V3D 2.1' in ui_log
mounts = read('/proc/mounts')
assert any(p[1] == '/' and 'ro' in p[3].split(',') for p in map(str.split, mounts.splitlines()))
assert any(p[1] == '/data' and 'rw' in p[3].split(',') for p in map(str.split, mounts.splitlines()))
assert Path('/root/.ssh').is_symlink() and os.readlink('/root/.ssh') == '/data/ssh'
assert Path('/data/ssh/dropbear_ed25519_host_key').stat().st_mode & 0o777 == 0o600
assert Path('/data/ssh/authorized_keys').stat().st_mode & 0o777 == 0o600
tasks = []
for proc in Path('/proc').glob('[0-9]*'):
    try:
        comm = (proc / 'comm').read_text().strip()
        if comm == 'rtapi_app' or comm.startswith('irq/') or int(proc.name) == ui_pid:
            for task in (proc / 'task').iterdir():
                tid = int(task.name)
                tasks.append(dict(pid=int(proc.name), tid=tid,
                    uid=proc.stat().st_uid, comm=(task / 'comm').read_text().strip(),
                    policy=os.sched_getscheduler(tid), priority=os.sched_getparam(tid).sched_priority,
                    cpus=sorted(os.sched_getaffinity(tid))))
    except (FileNotFoundError, ProcessLookupError):
        pass
rt = [t for t in tasks if t['comm'].startswith('rtapi_app:T#')]
assert rt and all(t['uid'] == 1000 and t['policy'] == 1 and t['priority'] == 98 and t['cpus'] == [3] for t in rt)
assert all(t['cpus'] == [0,1] for t in tasks if t['comm'].startswith('irq/'))
interrupts = read('/proc/interrupts')
for line in interrupts.splitlines():
    if 'ARMCTRL' in line:
        assert list(map(int, line.split(':',1)[1].split()[:4]))[2:] == [0,0]
frame = re.search(r'PYSIDE_FIRST_FRAME_KERNEL_UPTIME:\s*([\d.]+)', ui_log)
print(json.dumps(dict(validated=True, kernel=platform.release(), uptime=read('/proc/uptime'),
    boot_id=read('/proc/sys/kernel/random/boot_id').strip(), isolated=isolated,
    cmdline=read('/proc/cmdline'), mac=read('/sys/class/net/eth0/address').strip(),
    ui_pid=str(ui_pid), ui_log=ui_log, first_frame_kernel_uptime_s=float(frame[1]),
    tasks=tasks, interrupts=interrupts, softirqs=read('/proc/softirqs'),
    workqueue_cpumask=read('/sys/devices/virtual/workqueue/cpumask').strip(),
    root_readonly=True, data_writable=True, per_device_ssh_hostkey=True), indent=2))
