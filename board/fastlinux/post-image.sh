#!/bin/sh
set -eu
BOARD="$BR2_EXTERNAL_FASTLINUX_PATH/board/fastlinux"
cp "$BOARD/config.txt" "$BINARIES_DIR/rpi-firmware/config.txt"
cp "$BOARD/BOOT-README.txt" "$BINARIES_DIR/rpi-firmware/BOOT-README.txt"
cp "$BOARD/cmdline.txt" "$BINARIES_DIR/rpi-firmware/cmdline.txt"
# Keep only overlays used by this board.
for f in "$BINARIES_DIR/rpi-firmware/overlays/"*.dtbo; do
 case "${f##*/}" in vc4-kms-v3d.dtbo|disable-wifi.dtbo|disable-bt.dtbo|dwc2.dtbo) ;; *) rm -f "$f";; esac
done
# Persistent settings and later HAL configurations live outside the RO root.
if [ ! -f "$BINARIES_DIR/data.ext4" ]; then
 truncate -s 1024M "$BINARIES_DIR/data.ext4"
 "$HOST_DIR/sbin/mkfs.ext4" -F -E lazy_itable_init=0,lazy_journal_init=0 -L FASTDATA -O ^metadata_csum_seed,^orphan_file "$BINARIES_DIR/data.ext4"
fi
# The release FAT contains exactly one kernel; old development artifacts are
# deliberately excluded by the explicit genimage file list.
CFG="$BOARD/genimage.cfg"
mkdir -p "$BINARIES_DIR/empty-root"
rm -rf "$BUILD_DIR/genimage-fastlinux.tmp"
genimage --rootpath "$BINARIES_DIR/empty-root" --tmppath "$BUILD_DIR/genimage-fastlinux.tmp" --inputpath "$BINARIES_DIR" --outputpath "$BINARIES_DIR" --config "$CFG"
[ "$(stat -c %s "$BINARIES_DIR/sdcard.img")" -le 2008023040 ]
