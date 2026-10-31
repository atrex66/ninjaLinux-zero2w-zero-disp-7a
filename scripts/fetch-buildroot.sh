#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$ROOT/vendor/buildroot-2026.08.1.tar.xz"
mkdir -p "$ROOT/vendor"
if [ ! -f "$ARCHIVE" ]; then
 wget -O "$ARCHIVE.partial" https://buildroot.org/downloads/buildroot-2026.08.1.tar.xz
 mv "$ARCHIVE.partial" "$ARCHIVE"
fi
printf '%s  %s\n' 34fb7bea8a213ffde39cc02e61703391560f26e0850f03138c722d0b09880f2b "$ARCHIVE" | sha256sum -c -
if [ ! -d "$ROOT/vendor/buildroot-2026.08.1" ]; then
 tar -xJf "$ARCHIVE" -C "$ROOT/vendor"
fi
