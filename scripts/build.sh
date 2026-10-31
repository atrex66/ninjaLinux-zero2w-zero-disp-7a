#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-rt}"
case "$PROFILE" in rt) ;; *) echo 'Usage: build.sh [rt] — release supports PREEMPT_RT only' >&2; exit 2;; esac
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
BR="$ROOT/vendor/buildroot-2026.08.1"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
mkdir -p "$OUT" "$ROOT/logs" "$ROOT/artifacts"
# Keep large disk images on disk; source/compile work stays in tmpfs.
if [ ! -e "$OUT/images" ] && [ ! -L "$OUT/images" ]; then
 mkdir -p "$ROOT/artifacts/build-images"
 ln -s "$ROOT/artifacts/build-images" "$OUT/images"
fi
exec 9>"$ROOT/logs/build.lock"
flock -n 9 || { echo "A FastLinux build is already running" >&2; exit 1; }
ARGS=(-C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" "BR2_JLEVEL=${FASTLINUX_JOBS:-4}" 'BR2_WGET=wget -nd -t 2 --timeout=30')
make "${ARGS[@]}" "fastlinux_${PROFILE}_defconfig"
DRIVER="$OUT/build/linux-custom/drivers/irqchip/irq-bcm2836.c"
if [ -f "$DRIVER" ] && ! grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"; then
 make "${ARGS[@]}" linux-dirclean
fi
if [ -f "$OUT/.fastlinux-profile" ] && [ "$(cat "$OUT/.fastlinux-profile")" != "$PROFILE" ]; then
 make "${ARGS[@]}" -j"${FASTLINUX_JOBS:-4}" linux-reconfigure 2>&1 | tee "$ROOT/logs/kernel-${PROFILE}.log"
fi
make "${ARGS[@]}" -j"${FASTLINUX_JOBS:-4}" 2>&1 | tee "$ROOT/logs/build-${PROFILE}.log"
KDIR="$(find "$OUT/build" -maxdepth 1 -type d -name 'linux-*' | head -1)"
python3 "$ROOT/scripts/validate-config.py" "$KDIR/.config" "$PROFILE"
cp "$KDIR/.config" "$ROOT/artifacts/kernel-${PROFILE}.config"
cp "$KDIR/arch/arm64/boot/Image" "$ROOT/artifacts/Image-${PROFILE}"
grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"
printf '%s\n' "$PROFILE" > "$OUT/.fastlinux-profile"
# Keep the deliverable outside tmpfs, compressed to conserve disk space.
NAME=rt
gzip -1 -c "$OUT/images/sdcard.img" > "$ROOT/artifacts/fastlinux-${NAME}.img.gz.partial"
mv "$ROOT/artifacts/fastlinux-${NAME}.img.gz.partial" "$ROOT/artifacts/fastlinux-${NAME}.img.gz"
sha256sum "$ROOT/artifacts/fastlinux-${NAME}.img.gz" > "$ROOT/artifacts/fastlinux-${NAME}.img.gz.sha256"
bash "$ROOT/scripts/validate-image.sh" "$OUT"
