#!/bin/sh
set -eu
# No login terminals. Dedicated foreground supervisor is respawned by PID 1.
sed -i '/getty/d; /fastlinux-ui/d' "$TARGET_DIR/etc/inittab"
printf '\n::respawn:/usr/bin/fastlinux-ui\n' >> "$TARGET_DIR/etc/inittab"
# Root stays read-only; ephemeral state lives in RAM.
cat > "$TARGET_DIR/etc/fstab" <<'EOF'
/dev/root / ext4 ro,noatime 0 1
proc /proc proc defaults 0 0
sysfs /sys sysfs defaults 0 0
devpts /dev/pts devpts defaults,gid=5,mode=620,ptmxmode=0666 0 0
tmpfs /dev/shm tmpfs mode=1777 0 0
tmpfs /tmp tmpfs mode=1777 0 0
tmpfs /run tmpfs mode=0755 0 0
/dev/mmcblk0p3 /data ext4 defaults,noatime 0 0
EOF
# Do not perform a remount-rw of root in the stock init sequence.
sed -i '\|/bin/mount -o remount,rw /|d' "$TARGET_DIR/etc/inittab"
rm -f "$TARGET_DIR/etc/init.d/S40network" "$TARGET_DIR/etc/init.d/S50crond" "$TARGET_DIR/etc/init.d/S11modules"
# /var is provided by Buildroot as symlinks into /tmp; inspect at image validation.

# The base profile is module-free; rt-wifi needs its wireless modules.
if ! grep -q '^BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y$' "$BR2_CONFIG"; then
 rm -rf "$TARGET_DIR/lib/modules"
fi

chmod 700 "$TARGET_DIR/root"
# Generic releases must not contain a developer key or a shared private host key.
rm -rf "$TARGET_DIR/root/.ssh"
ln -s /data/ssh "$TARGET_DIR/root/.ssh"
rm -f "$TARGET_DIR/etc/dropbear/"*_host_key

mkdir -p "$TARGET_DIR/data"

# Fail the build if Kconfig silently dropped a required graphics/RT dependency.
for kdir in "$BUILD_DIR"/linux-*; do
 [ -f "$kdir/.config" ] || continue
 profile=normal
 grep -q '^CONFIG_PREEMPT_RT=y$' "$kdir/.config" && profile=rt
 if grep -q '^BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y$' "$BR2_CONFIG"; then
  profile=rt-wifi
  if grep -q '^BR2_PACKAGE_HOSTAPD=y$' "$BR2_CONFIG"; then profile=rt-wifi-ap; fi
 fi
 python3 "$BR2_EXTERNAL_FASTLINUX_PATH/scripts/validate-config.py" "$kdir/.config" "$profile"
done

python3 "$BR2_EXTERNAL_FASTLINUX_PATH/scripts/configure-wifi-image.py" target "$BR2_CONFIG" "$TARGET_DIR"
