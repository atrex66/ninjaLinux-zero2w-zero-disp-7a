#!/bin/bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-rt}"
case "$PROFILE" in rt|rt-wifi|rt-wifi-ap) ;; *) exit 2;; esac
rm -f "$ROOT/logs/build-${PROFILE}.exit"
"$ROOT/scripts/build.sh" "$PROFILE"
status=$?
printf '%s\n' "$status" > "$ROOT/logs/build-${PROFILE}.exit"
exit "$status"
