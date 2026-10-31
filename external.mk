include $(sort $(wildcard $(BR2_EXTERNAL_FASTLINUX_PATH)/package/*/*.mk))
# The firmware package only installs boot files; exclude unrelated prebuilt
# kernels/modules and legacy userspace tools from its unpacked source tree.
RPI_FIRMWARE_EXCLUDES += modules opt
