#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
BUILD="${NINJALINUX_HAL_BUILD:-/tmp/ninjalinux-hal-build}"
STAGE="$ROOT/artifacts/hal-rootfs/opt/automation-hal"
PYTHONPATH="$ROOT/third_party/yapps" "$OUT/host/bin/python3" \
 "$BUILD/halcompile.py" --preprocess -o "$BUILD/ninja_latency.c" \
 "$ROOT/components/ninja-latency/ninja_latency.comp"
"$OUT/host/bin/aarch64-linux-gcc" -shared -fPIC -DRTAPI -DSIM -D__MODULE__ \
 -D_GNU_SOURCE -Os -fno-fast-math -I "$STAGE/include" -Wl,-Bsymbolic \
 "$BUILD/ninja_latency.c" -o "$STAGE/rtlib/ninja_latency.so" -lm
"$OUT/host/bin/aarch64-linux-strip" --strip-unneeded "$STAGE/rtlib/ninja_latency.so"
