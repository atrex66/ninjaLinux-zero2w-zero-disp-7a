#!/bin/bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec 9>"$ROOT/logs/flash.lock"
flock -n 9 || exit 1
rm -f "$ROOT/logs/flash.exit"
/usr/bin/python3 "$ROOT/scripts/flash-card.py" "$ROOT/artifacts/build-images/sdcard.img"
status=$?
printf '%s\n' "$status" > "$ROOT/logs/flash.exit"
exit "$status"
