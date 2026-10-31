#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-rt}"
USB_APP="${NINJALINUX_USB_AUTOSTART:-0}"
case "$USB_APP" in 0|1) ;; *) echo 'NINJALINUX_USB_AUTOSTART must be 0 or 1' >&2; exit 2;; esac
case "$PROFILE" in rt|rt-wifi|rt-wifi-ap) ;; *) echo 'Usage: build.sh [rt|rt-wifi|rt-wifi-ap] — PREEMPT_RT only' >&2; exit 2;; esac
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
BR="$ROOT/vendor/buildroot-2026.08.1"
DEFAULT_OUT=/tmp/fastlinux-build
DEFAULT_IMAGES=build-images
if [ "$PROFILE" != rt ]; then DEFAULT_OUT=/tmp/fastlinux-build-$PROFILE; DEFAULT_IMAGES=build-images-$PROFILE; fi
if [ "$USB_APP" = 1 ]; then DEFAULT_OUT="$DEFAULT_OUT-usb"; DEFAULT_IMAGES="$DEFAULT_IMAGES-usb"; fi
OUT="${FASTLINUX_OUT:-$DEFAULT_OUT}"
# Buildroot cannot uninstall packages from a reused output tree.
if [ -f "$OUT/.config" ]; then
 old_usb=0
 grep -q '^BR2_PACKAGE_NINJALINUX_USB_AUTOSTART=y$' "$OUT/.config" && old_usb=1
 [ "$old_usb" = "$USB_APP" ] || { echo 'Use a separate FASTLINUX_OUT for USB addon changes' >&2; exit 2; }
 existing=rt
 if grep -q '^BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y$' "$OUT/.config"; then
  existing=rt-wifi
  if grep -q '^BR2_PACKAGE_HOSTAPD=y$' "$OUT/.config"; then existing=rt-wifi-ap; fi
 fi
 [ "$existing" = "$PROFILE" ] || { echo "Use a separate FASTLINUX_OUT for $PROFILE; existing tree is $existing" >&2; exit 2; }
fi
mkdir -p "$OUT" "$ROOT/logs" "$ROOT/artifacts"
# Keep large disk images on disk; source/compile work stays in tmpfs.
if [ ! -e "$OUT/images" ] && [ ! -L "$OUT/images" ]; then
 mkdir -p "$ROOT/artifacts/$DEFAULT_IMAGES"
 ln -s "$ROOT/artifacts/$DEFAULT_IMAGES" "$OUT/images"
fi
exec 9>"$ROOT/logs/build.lock"
flock -n 9 || { echo "A FastLinux build is already running" >&2; exit 1; }
ARGS=(-C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" "BR2_JLEVEL=${FASTLINUX_JOBS:-4}" 'BR2_WGET=wget -nd -t 2 --timeout=30')
make "${ARGS[@]}" "fastlinux_${PROFILE//-/_}_defconfig"
if [ "$USB_APP" = 1 ]; then
 "$BR/utils/config" --file "$OUT/.config" --enable BR2_PACKAGE_NINJALINUX_USB_AUTOSTART
 fragments="$(sed -n 's/^BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES="\(.*\)"/\1/p' "$OUT/.config")"
 "$BR/utils/config" --file "$OUT/.config" --set-str BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES "$fragments $ROOT/board/fastlinux/usb-autostart.fragment"
 make "${ARGS[@]}" olddefconfig
fi
DRIVER="$OUT/build/linux-custom/drivers/irqchip/irq-bcm2836.c"
if [ -f "$DRIVER" ] && ! grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"; then
 make "${ARGS[@]}" linux-dirclean
fi
if [ -f "$OUT/.fastlinux-profile" ] && [ "$(cat "$OUT/.fastlinux-profile")" != "$PROFILE" ]; then
 make "${ARGS[@]}" -j"${FASTLINUX_JOBS:-4}" linux-reconfigure 2>&1 | tee "$ROOT/logs/kernel-${PROFILE}.log"
fi
make "${ARGS[@]}" -j"${FASTLINUX_JOBS:-4}" 2>&1 | tee "$ROOT/logs/build-${PROFILE}.log"
KDIR="$(find "$OUT/build" -maxdepth 1 -type d -name 'linux-*' | head -1)"
python3 "$ROOT/scripts/validate-config.py" "$KDIR/.config" "$PROFILE" "$USB_APP"
VARIANT="$PROFILE"
if [ "$USB_APP" = 1 ]; then VARIANT="$VARIANT-usb"; fi
cp "$KDIR/.config" "$ROOT/artifacts/kernel-${VARIANT}.config"
cp "$KDIR/arch/arm64/boot/Image" "$ROOT/artifacts/Image-${VARIANT}"
grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"
printf '%s\n' "$PROFILE" > "$OUT/.fastlinux-profile"
# Keep the deliverable outside tmpfs, compressed to conserve disk space.
NAME="$PROFILE"
if [ "$USB_APP" = 1 ]; then NAME="$NAME-usb"; fi
gzip -1 -c "$OUT/images/sdcard.img" > "$ROOT/artifacts/fastlinux-${NAME}.img.gz.partial"
mv "$ROOT/artifacts/fastlinux-${NAME}.img.gz.partial" "$ROOT/artifacts/fastlinux-${NAME}.img.gz"
sha256sum "$ROOT/artifacts/fastlinux-${NAME}.img.gz" > "$ROOT/artifacts/fastlinux-${NAME}.img.gz.sha256"
bash "$ROOT/scripts/validate-image.sh" "$OUT"
