#!/bin/sh
# SPDX-License-Identifier: MIT
# Manual EGLFS launch. It does not stop the installed GUI or change boot files.
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$app_dir/app.py" ] || { echo "Build a UI bundle first; use its run-pi.sh" >&2; exit 1; }
export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_INTEGRATION=eglfs_kms
export QT_QPA_EGLFS_HIDECURSOR=1
export QT_QPA_FONTDIR=/usr/share/fonts/dejavu
if [ -z "${XDG_RUNTIME_DIR:-}" ]; then
    XDG_RUNTIME_DIR="${TMPDIR:-/tmp}/ninjaui-$(id -u)"
    export XDG_RUNTIME_DIR
    (umask 077; mkdir -p "$XDG_RUNTIME_DIR")
fi
if [ -z "${QT_QPA_EGLFS_KMS_CONFIG:-}" ]; then
    for connector in /sys/class/drm/card*-HDMI-A-*/status; do
        [ -f "$connector" ] || continue
        card=${connector%/*}; card=${card##*/}; card=${card%%-*}
        [ -c "/dev/dri/$card" ] || continue
        QT_QPA_EGLFS_KMS_CONFIG="$XDG_RUNTIME_DIR/ninjaui-kms.json"
        export QT_QPA_EGLFS_KMS_CONFIG
        (umask 077; printf '{"device":"/dev/dri/%s"}\n' "$card" > "$QT_QPA_EGLFS_KMS_CONFIG")
        break
    done
fi
hal_read=0
for arg in "$@"; do [ "$arg" != --hal-read ] || hal_read=1; done
if [ "$hal_read" = 1 ]; then
    set -- /opt/automation-hal/bin/ahal python "$app_dir/app.py" --fullscreen "$@"
else
    set -- /usr/bin/python3 "$app_dir/app.py" --fullscreen "$@"
fi
# Match the existing four-core ninjaLinux profile, when it is actually active.
if [ "$(cat /sys/devices/system/cpu/isolated 2>/dev/null || true)" = 2-3 ]; then
    exec taskset -c 2 "$@"
fi
exec "$@"
