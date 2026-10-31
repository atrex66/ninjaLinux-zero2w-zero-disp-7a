#!/bin/bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -f "$ROOT/logs/build-hal.exit"
"$ROOT/scripts/build-hal.sh"
result=$?
printf '%s\n' "$result" > "$ROOT/logs/build-hal.exit"
exit "$result"
