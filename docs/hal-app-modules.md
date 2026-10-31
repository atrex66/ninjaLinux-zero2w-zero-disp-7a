# Application realtime HAL modules from /data or a cartridge

**[Magyar](hal-app-modules.hu.md)**

The extended ninjaLinux platform supports app modules without changing system
files. Older released images do not automatically support it: build an image
with the new loader. The live Pi was not upgraded.

## Packaging and installation

```text
/data/apps/my-app/
  hal/main.hal
  rtlib/my_component.so
  lib/                 private dependencies, when needed
```

Boot cartridges now mount below `/data/cartridges/volume-sdX…`, leaving the
internal `/data` in place. Their `rtlib` stays on USB. Use the app's
`NINJALINUX_CARTRIDGE_ROOT` environment variable instead of hardcoding a disk
name. Modules need read access only, so read-only cartridges also work.

Build a **userspace RTAPI `.so`**, not a Linux-kernel `.ko`, using the matching
StandaloneHAL/Automation HAL SDK, AArch64 target toolchain, libc/ABI and private
IPC adaptations. An ordinary LinuxCNC binary or another architecture is not
compatible. Use `halcompile --compile` in the development SDK; a native PC SDK
produces native PC modules, not Pi binaries. Do not install build tools into
the appliance or alter its system environment to satisfy an app dependency.

Copy the finished module from your app package into its own directory:

```sh
mkdir -p /data/apps/my-app/rtlib
cp my_component.so /data/apps/my-app/rtlib/my_component.so
chmod 644 /data/apps/my-app/rtlib/my_component.so
```

For a cartridge, put it in `rtlib/` on the stick from the PC. No copying into
`/opt`, root remount, `ldconfig` or system `halcompile --install` is needed.
The HAL user `ahal` needs read/traverse access. Private library dependencies
belong in the app's `lib/`, with an appropriate package-relative RPATH;
never replace system libraries.

## Loading

The HAL configuration uses the usual **module name**, without a suffix/path:

```hal
loadrt my_component count=1
# Follow with the component's addf/net/... configuration.
```

Select extra directories when starting the session:

```sh
ninjalinux-hal start /data/apps/my-app/hal/main.hal \
  --rtlib /data/apps/my-app/rtlib
```

From a cartridge's own launcher:

```sh
ninjalinux-hal start "$NINJALINUX_CARTRIDGE_ROOT/hal/main.hal" \
  --rtlib "$NINJALINUX_CARTRIDGE_ROOT/rtlib"
```

Repeat `--rtlib` to add directories in search order. Paths must be absolute,
existing directories without `:`; the image's administrator launcher accepts
only paths resolving below `/data`. The existing command without extra
options still works. Generic `ahal run` accepts the same option, run by the
non-root HAL owner with suitable realtime limits.

Do not start a second HAL alongside a live session. Paths are fixed at session
startup; a later `ahal cmd` environment does not change them. USB discovery
never automatically starts HAL or loads code: the application's own authorized
startup handles that.

## System priority

1. `/opt/automation-hal/rtlib` is always searched first.
2. Only absent module names are looked up in the explicit app directories.
3. A broken existing system module fails; it never falls back to app code.
4. Core `hal_lib` must come from the system.
5. App modules must be regular files, not symlinks/FIFOs/devices. `/` and `..`
   remain forbidden in module names.

The launcher derives internal `AHAL_RTLIB_PATH` solely from explicit `--rtlib`
options and clears inherited values. Legacy `HAL_RTMOD_DIR` is not this feature's
switch. Loading app code is not sandboxing or automatic code verification;
use app-specific module names rather than trying to replace system components.

Keep USB connected throughout the session; stop your app/HAL cleanly before
changing files/media. There is no implicit hot reload. The web explorer now
sees `/data/cartridges`; writes still depend on the cartridge's `writable` setting.

## Verification

After a native PC HAL/SDK build and installation into a staging directory only:

```sh
sh components/automation-hal/tools/test_app_modules.sh \
  /tmp/ninja-hal-module-stage/opt/automation-hal
```

This compiles and loads a real RTAPI module under `/data/cartridges` inside a
new tmpfs root and private filesystem/PID/IPC/network namespaces. It checks a
cyclically increasing pin, system priority, explicit paths and invalid
path/symlink rejection, without touching host/Pi HAL. Scheduling is **PC sim
mode**, not a physical PREEMPT_RT latency measurement. Full Pi image rebuild,
physical USB mounts and target RT/I/O validation remain pending. Unit tests
are in `tests/test_hal_app_modules.py`.
