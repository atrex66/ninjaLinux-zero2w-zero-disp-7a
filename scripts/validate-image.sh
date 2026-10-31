#!/bin/bash
set -euo pipefail
OUT="${1:-/tmp/fastlinux-build}"
TARGET="$OUT/target"
file "$TARGET/usr/bin/fastlinux-demo"
readelf -h "$TARGET/usr/bin/fastlinux-demo" | grep -q 'Machine:.*AArch64'
find "$TARGET/usr" -name libqeglfs.so -print | grep .
find "$TARGET/usr" -name '*eglfs*kms*.so' -print | grep .
find "$TARGET/usr" \( -name vc4_dri.so -o -name 'libgallium*.so*' \) -print | grep .
grep -q '^::respawn:/usr/bin/fastlinux-ui$' "$TARGET/etc/inittab"
! grep -q 'remount,rw\|getty' "$TARGET/etc/inittab"
test -e "$TARGET/usr/bin/python3"
find "$TARGET/usr/lib" -path "*/site-packages/PySide6/QtWidgets*.so" -print | grep .
! test -e "$TARGET/usr/bin/Xorg"
test "$(readlink "$TARGET/root/.ssh")" = /data/ssh
test -z "$(find "$TARGET/etc/dropbear" -name '*_host_key' -print)"
test -x "$TARGET/etc/init.d/S20sshkeys"
test -x "$TARGET/opt/automation-hal/bin/ahal"
test -f "$TARGET/opt/automation-hal/rtlib/ninja_latency.so"
# Buildroot adds package users in its fakeroot image tree, after target-finalize.
"$OUT/host/sbin/debugfs" -R 'cat /etc/passwd' "$OUT/images/rootfs.ext4" 2>/dev/null | grep -q '^ahal:x:1000:1000:'
grep -q 'isolcpus=domain,managed_irq,2,3 irqaffinity=0,1' "$OUT/images/rpi-firmware/cmdline.txt"
python3 "$(dirname "$0")/validate-config.py" "$OUT/build/linux-custom/.config" rt
cmp "$OUT/images/Image" "$OUT/build/linux-custom/arch/arm64/boot/Image"
"$OUT/host/bin/mdir" -i "$OUT/images/boot.vfat" :: > "$OUT/images/boot-list.txt"
! grep -Ei 'Image-rt|config-normal|config-rt' "$OUT/images/boot-list.txt"
for fs in rootfs.ext4 data.ext4; do
 "$OUT/host/sbin/e2fsck" -fn "$OUT/images/$fs"
done
"$OUT/host/bin/mdir" -i "$OUT/images/boot.vfat" ::
python3 - "$OUT/images/sdcard.img" <<'PY'
import pathlib,struct,sys
p=pathlib.Path(sys.argv[1]); size=p.stat().st_size
assert size<=2008023040
with p.open('rb') as f: m=f.read(512)
assert m[510:512]==b'\x55\xaa'
prev=0
for n in range(3):
 _,_,kind,_,start,count=struct.unpack_from('<B3sB3sII',m,446+16*n)
 assert kind==(12 if n==0 else 131)
 assert start>=prev and (start+count)*512<=size
 prev=start+count
 print('Partition',n+1,'type',hex(kind),'start',start,'sectors',count)
print('Image size:',size,'bytes; card:',2008023040,'bytes')
PY
printf 'Offline image checks passed. Physical Pi boot, touch and RT timing still require target testing.\n'
