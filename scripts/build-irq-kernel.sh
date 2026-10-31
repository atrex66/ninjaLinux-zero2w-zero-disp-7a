#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${FASTLINUX_OUT:-/tmp/fastlinux-build}"
export PATH="$ROOT/vendor/hostdeps/root/usr/bin:$PATH"
export BISON_PKGDATADIR="$ROOT/vendor/hostdeps/root/usr/share/bison"
unset M4
exec 9>"$ROOT/logs/build.lock"
flock -n 9 || exit 1
ARGS=(-C "$ROOT/vendor/buildroot-2026.08.1" O="$OUT" BR2_EXTERNAL="$ROOT" "BR2_JLEVEL=${FASTLINUX_JOBS:-4}")
make "${ARGS[@]}" fastlinux_rt_defconfig
# A newly introduced package patch must run at extraction/patch time.
DRIVER="$OUT/build/linux-custom/drivers/irqchip/irq-bcm2836.c"
if [ -f "$DRIVER" ] && ! grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"; then
 make "${ARGS[@]}" linux-dirclean
fi
make "${ARGS[@]}" -j"${FASTLINUX_JOBS:-4}" linux
KERNEL="$OUT/build/linux-custom"
python3 "$ROOT/scripts/validate-config.py" "$KERNEL/.config" rt
grep -q '^CONFIG_CPU_ISOLATION=y$' "$KERNEL/.config"
grep -q 'housekeeping_test_cpu(next_route, HK_TYPE_DOMAIN)' "$DRIVER"
cp "$KERNEL/arch/arm64/boot/Image" "$ROOT/artifacts/Image-rt-irq1"
cp "$KERNEL/.config" "$ROOT/artifacts/kernel-rt-irq1.config"
sha256sum "$ROOT/artifacts/Image-rt-irq1" > "$ROOT/artifacts/Image-rt-irq1.sha256"
