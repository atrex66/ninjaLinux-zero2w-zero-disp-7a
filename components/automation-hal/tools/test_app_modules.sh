#!/bin/sh
# A native Linux SDK/runtime staging tree is required; never use the live prefix.
set -eu
stage=$(readlink -f "${1:?usage: test_app_modules.sh STAGED_PREFIX}")
project=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
repo=$(CDPATH= cd -- "$project/../.." && pwd)
[ "$stage" != /opt/automation-hal ] && [ -x "$stage/bin/ahal" ] || exit 2
# Root is a fresh tmpfs; host tools and staged HAL are read-only. No host /data,
# /tmp, /run, user configuration, network or SysV IPC enters the test.
exec bwrap --die-with-parent --unshare-all --tmpfs / \
 --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
 --dir /etc --ro-bind /etc/alternatives /etc/alternatives \
 --dir /tmp --dir /data --dir /opt --ro-bind "$stage" /opt/automation-hal \
 --proc /proc --dev /dev \
 --ro-bind "$project/tests/app_module_integration.py" /test.py \
 --ro-bind "$repo/third_party/yapps" /test-yapps \
 --clearenv --setenv PATH /usr/bin:/bin --setenv HOME /tmp \
 --setenv PYTHONPATH /test-yapps --setenv LC_ALL C -- /usr/bin/python3 /test.py
