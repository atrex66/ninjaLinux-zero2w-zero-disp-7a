#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
exec 9>"$ROOT/logs/build.lock"
flock -n 9 || exit 2
make -C "$ROOT/vendor/buildroot-2026.08.1" O="$OUT" BR2_EXTERNAL="$ROOT" \
 LEGAL_INFO_DIR="$ROOT/artifacts/legal-info" legal-info
# Buildroot's report explicitly asks for Buildroot sources as well.
mkdir -p "$ROOT/artifacts/legal-info/project-sources"
cp "$ROOT/vendor/buildroot-2026.08.1.tar.xz" "$ROOT/artifacts/legal-info/project-sources/"
tar --exclude=__pycache__ --exclude='*.pyc' -czf "$ROOT/artifacts/legal-info/project-sources/ninjalinux-build-sources.tar.gz" \
 -C "$ROOT" board components configs docs package scripts third_party \
 Config.in external.desc external.mk LICENSE README.md README.hu.md README.hu.txt
python3 "$ROOT/scripts/collect-toolchain-sources.py"
(cd "$ROOT/artifacts/legal-info" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
