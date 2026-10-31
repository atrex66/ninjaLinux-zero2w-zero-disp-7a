#!/bin/bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec >"$ROOT/logs/release-build.log" 2>&1
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
ARGS=(-C "$ROOT/vendor/buildroot-2026.08.1" O="$OUT" BR2_EXTERNAL="$ROOT" BR2_JLEVEL=2)
(
 flock -n 9 || exit 2
 make "${ARGS[@]}" fastlinux_rt_defconfig &&
 make "${ARGS[@]}" automation-hal-reinstall &&
 make "${ARGS[@]}" fastlinux-demo-rebuild
) 9>"$ROOT/logs/build.lock" && FASTLINUX_JOBS=2 bash "$ROOT/scripts/build.sh" rt
status=$?
printf '%s\n' "$status" > "$ROOT/logs/release-build.exit"
exit "$status"
