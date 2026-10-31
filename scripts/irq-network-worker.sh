#!/bin/bash
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ssh -i /home/ninja/.ssh/id_ed25519 -o IdentitiesOnly=yes -o UserKnownHostsFile="$ROOT/logs/ssh_known_hosts" -o StrictHostKeyChecking=yes -o BatchMode=yes root@192.168.0.234 \
 'taskset -c 0,1 python3 /data/irq-test/network-load.py /data/irq-test/load1' >/dev/null 2>"$ROOT/logs/irq-network-load.log"
printf '%s\n' "$?" > "$ROOT/logs/irq-network-load.exit"
