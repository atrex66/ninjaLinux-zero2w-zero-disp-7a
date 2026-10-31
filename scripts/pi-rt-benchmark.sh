#!/bin/sh
set -u
cd /data/rt-test
zcat /proc/config.gz | grep -q '^CONFIG_PREEMPT_RT=y$' || exit 2
uname -a > graphics-10m-context.txt
cat /proc/uptime >> graphics-10m-context.txt
cat /run/fastlinux-ui.pid >> graphics-10m-context.txt
cat /tmp/fastlinux-ui.log >> graphics-10m-context.txt
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor >> graphics-10m-context.txt
cyclictest --mlockall --smp --priority=80 --interval=1000 --distance=0 --duration=10m --quiet --json=graphics-10m.json > graphics-10m.log 2>&1
result=$?
cat /proc/uptime >> graphics-10m-context.txt
cat /run/fastlinux-ui.pid >> graphics-10m-context.txt
printf '%s\n' "$result" > graphics-10m.exit
exit "$result"
