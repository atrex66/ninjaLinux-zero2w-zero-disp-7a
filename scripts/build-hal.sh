#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
BUILD="${NINJALINUX_HAL_BUILD:-/tmp/ninjalinux-hal-build}"
export PYTHONPATH="$ROOT/third_party/yapps${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
bash "$ROOT/scripts/prepare-hal-deps.sh" "$BUILD/build-deps"
SYSROOT="$OUT/host/aarch64-buildroot-linux-gnu/sysroot"
cmake -S "$ROOT/components/automation-hal" -B "$BUILD" -G Ninja \
 -DCMAKE_TOOLCHAIN_FILE="$OUT/host/share/buildroot/toolchainfile.cmake" \
 -DCMAKE_BUILD_TYPE=MinSizeRel -DCMAKE_INSTALL_PREFIX=/opt/automation-hal \
 -DPython3_EXECUTABLE="$OUT/host/bin/python3" \
 -DPython3_INCLUDE_DIR="$SYSROOT/usr/include/python3.14" \
 -DPython3_LIBRARY="$SYSROOT/usr/lib/libpython3.14.so" \
 -DBOOST_INCLUDE_DIR="$BUILD/build-deps" \
 -DUDEV_LIBRARY="$SYSROOT/usr/lib/libudev.so"
cmake --build "$BUILD" --parallel 2
STAGE="$ROOT/artifacts/hal-rootfs"
mkdir -p "$STAGE"
DESTDIR="$STAGE" cmake --install "$BUILD"
find "$STAGE/opt/automation-hal" -type f \( -name '*.so' -o -name '*.so.*' -o -name halcmd -o -name rtapi_app -o -name inivar -o -name halsampler -o -name halstreamer \) \
 -exec "$OUT/host/bin/aarch64-linux-strip" --strip-unneeded {} +
tar -czf "$ROOT/artifacts/automation-hal-aarch64.tar.gz" -C "$STAGE" opt/automation-hal
sha256sum "$ROOT/artifacts/automation-hal-aarch64.tar.gz" > "$ROOT/artifacts/automation-hal-aarch64.tar.gz.sha256"
