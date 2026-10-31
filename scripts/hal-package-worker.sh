#!/bin/bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec >"$ROOT/logs/build-hal-package.log" 2>&1
exec 9>"$ROOT/logs/build.lock"
flock -n 9 || exit 2
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
BR="$ROOT/vendor/buildroot-2026.08.1"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
make -C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" fastlinux_rt_defconfig && \
make -C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" BR2_JLEVEL=2 automation-hal
result=$?
printf '%s\n' "$result" >"$ROOT/logs/build-hal-package.exit"
exit "$result"
