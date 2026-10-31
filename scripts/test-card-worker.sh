#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec >"$ROOT/logs/test-card.log" 2>&1
exec 9>"$ROOT/logs/flash.lock"
flock -n 9 || exit 2
trap 'printf "%s\n" "$?" > "$ROOT/logs/test-card.exit"' EXIT
BACKUP="$ROOT/backups/sd-working-rt-hal-20261031.img.gz"
/usr/bin/python3 "$ROOT/scripts/backup-card.py" "$BACKUP"
# The public release remains generic. Provision only a disposable test copy.
sha256sum -c "$ROOT/artifacts/fastlinux-rt.img.gz.sha256"
IMAGE="$ROOT/artifacts/pi-test-rt-hal.img"
gzip -dc "$ROOT/artifacts/fastlinux-rt.img.gz" | cp --sparse=always /dev/stdin "$IMAGE"
"/tmp/fastlinux-build/host/bin/mcopy" -o -i "$IMAGE@@1048576" \
 /home/ninja/.ssh/id_ed25519.pub ::authorized_keys
"/tmp/fastlinux-build/host/bin/mtype" -i "$IMAGE@@1048576" ::authorized_keys | \
 cmp /home/ninja/.ssh/id_ed25519.pub -
/usr/bin/python3 "$ROOT/scripts/flash-card.py" "$IMAGE" "$BACKUP"
udisksctl power-off -b /dev/sdb
