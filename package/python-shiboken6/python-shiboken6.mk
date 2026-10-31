PYTHON_SHIBOKEN6_VERSION = 6.11.2
PYTHON_SHIBOKEN6_SOURCE = pyside-setup-everywhere-src-$(PYTHON_SHIBOKEN6_VERSION).tar.xz
PYTHON_SHIBOKEN6_SITE = https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-$(PYTHON_SHIBOKEN6_VERSION)-src
PYTHON_SHIBOKEN6_LICENSE = LGPL-3.0, GPL-2.0, GPL-3.0
PYTHON_SHIBOKEN6_LICENSE_FILES = LICENSES/LGPL-3.0-only.txt LICENSES/GPL-2.0-only.txt LICENSES/GPL-3.0-only.txt LICENSES/Qt-GPL-exception-1.0.txt
PYTHON_SHIBOKEN6_INSTALL_STAGING = YES
PYTHON_SHIBOKEN6_CMAKE_BACKEND = ninja
PYTHON_SHIBOKEN6_DEPENDENCIES = python3 qt6base host-pyside-generator
PYTHON_SHIBOKEN6_CONF_OPTS = -DBUILD_TESTS=OFF -DFORCE_LIMITED_API=ON \
 -DPython_EXECUTABLE=$(HOST_DIR)/bin/python3 \
 -DPython_INCLUDE_DIR=$(STAGING_DIR)/usr/include/python$(PYTHON3_VERSION_MAJOR) \
 -DPython_LIBRARY=$(STAGING_DIR)/usr/lib/libpython$(PYTHON3_VERSION_MAJOR).so \
 -DPython_ROOT_DIR=$(STAGING_DIR)/usr \
 -DPYTHON_SITE_PACKAGES=/usr/lib/python$(PYTHON3_VERSION_MAJOR)/site-packages \
 -DQFP_PYTHON_HOST_PATH=$(HOST_DIR)/bin/python3 \
 -DQFP_PYTHON_TARGET_PATH=$(STAGING_DIR)/usr \
 -DQFP_QT_TARGET_PATH=$(STAGING_DIR)/usr \
 -DQFP_QT_HOST_PATH=$(HOST_DIR) \
 -DQFP_SHIBOKEN_HOST_PATH=$(HOST_DIR)/share/fastlinux/shiboken/shiboken6_generator
# Official generator wheel bundles its host dependencies; no host Clang SDK is needed.
PYTHON_SHIBOKEN6_CONF_OPTS += -DSHIBOKEN_WRAPPER_HOST_CLANG_LIB_PATH=$(HOST_DIR)/share/fastlinux/shiboken/shiboken6_generator \
 -DSHIBOKEN_WRAPPER_HOST_QT_LIB_PATH=$(HOST_DIR)/share/fastlinux/shiboken/shiboken6_generator/Qt/lib
PYTHON_SHIBOKEN6_BUILD_ENV = CLANG_INSTALL_DIR=/usr/lib/llvm-19
PYTHON_SHIBOKEN6_SUBDIR = sources/shiboken6
$(eval $(cmake-package))
