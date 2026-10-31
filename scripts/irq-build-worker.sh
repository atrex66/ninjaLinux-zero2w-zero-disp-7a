#!/bin/bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -f "$ROOT/logs/build-rt-irq1.exit"
"$ROOT/scripts/build-irq-kernel.sh"
result=$?
printf '%s\n' "$result" > "$ROOT/logs/build-rt-irq1.exit"
exit "$result"
