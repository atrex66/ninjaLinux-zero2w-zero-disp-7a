AUTOMATION_HAL_VERSION = 0.1.0
AUTOMATION_HAL_SITE = $(BR2_EXTERNAL_FASTLINUX_PATH)/components/automation-hal
AUTOMATION_HAL_SITE_METHOD = local
AUTOMATION_HAL_LICENSE = GPL-2.0+
AUTOMATION_HAL_LICENSE_FILES = COPYING vendor/COPYING vendor/COPYING.more
AUTOMATION_HAL_DEPENDENCIES = python3 host-python3 eudev
AUTOMATION_HAL_CMAKE_BACKEND = ninja
AUTOMATION_HAL_CONF_ENV = PYTHONPATH=$(BR2_EXTERNAL_FASTLINUX_PATH)/third_party/yapps
AUTOMATION_HAL_BUILD_ENV = PYTHONPATH=$(BR2_EXTERNAL_FASTLINUX_PATH)/third_party/yapps
define AUTOMATION_HAL_PREPARE_DEPS
	bash $(BR2_EXTERNAL_FASTLINUX_PATH)/scripts/prepare-hal-deps.sh $(@D)/build-deps
endef
AUTOMATION_HAL_PRE_CONFIGURE_HOOKS += AUTOMATION_HAL_PREPARE_DEPS
AUTOMATION_HAL_CONF_OPTS = -DCMAKE_INSTALL_PREFIX=/opt/automation-hal \
 -DPython3_EXECUTABLE=$(HOST_DIR)/bin/python3 \
 -DPython3_INCLUDE_DIR=$(STAGING_DIR)/usr/include/python$(PYTHON3_VERSION_MAJOR) \
 -DPython3_LIBRARY=$(STAGING_DIR)/usr/lib/libpython$(PYTHON3_VERSION_MAJOR).so \
 -DBOOST_INCLUDE_DIR=$(@D)/build-deps \
 -DUDEV_LIBRARY=$(STAGING_DIR)/usr/lib/libudev.so
AUTOMATION_HAL_USERS = ahal 1000 ahal 1000 * /data/hal /bin/false - Automation HAL runtime
define AUTOMATION_HAL_INSTALL_LATENCY_PROBE
	PYTHONPATH=$(BR2_EXTERNAL_FASTLINUX_PATH)/third_party/yapps $(HOST_DIR)/bin/python3 \
	 $(@D)/halcompile.py --preprocess -o $(@D)/ninja_latency.c \
	 $(BR2_EXTERNAL_FASTLINUX_PATH)/components/ninja-latency/ninja_latency.comp
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -shared -fPIC -DRTAPI -DSIM \
	 -D__MODULE__ -D_GNU_SOURCE -fno-fast-math -Wl,-Bsymbolic \
	 -I$(TARGET_DIR)/opt/automation-hal/include $(@D)/ninja_latency.c \
	 -o $(TARGET_DIR)/opt/automation-hal/rtlib/ninja_latency.so -lm
	mkdir -p $(TARGET_DIR)/opt/automation-hal/share/ninja-latency
	cp $(BR2_EXTERNAL_FASTLINUX_PATH)/components/ninja-latency/ninja_latency.comp \
	 $(BR2_EXTERNAL_FASTLINUX_PATH)/components/ninja-latency/COPYING \
	 $(TARGET_DIR)/opt/automation-hal/share/ninja-latency/
endef
AUTOMATION_HAL_POST_INSTALL_TARGET_HOOKS += AUTOMATION_HAL_INSTALL_LATENCY_PROBE
$(eval $(cmake-package))
