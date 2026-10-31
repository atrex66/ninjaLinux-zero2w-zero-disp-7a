#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?HAL dependency destination required}"
mkdir -p "$DEST"
(cd "$ROOT" && sha256sum -c third_party/boost/SHA256SUMS)
if [ ! -f "$DEST/boost/.ninjalinux-verified" ]; then
 tar -xzf "$ROOT/third_party/boost/boost-headers-1.83.0.tar.gz" -C "$DEST"
 cp "$ROOT/third_party/boost/SHA256SUMS" "$DEST/boost/.ninjalinux-verified"
fi
