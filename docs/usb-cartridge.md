# USB application cartridge

**[Magyar](usb-cartridge.hu.md)**

An optional build-time addon starts the application described by a USB
stick's `autostart.json`, provided the stick is connected before power-on.
Keep the same SD system and swap application cartridges without installing
or copying an application into the system.

## Build an image

```sh
NINJALINUX_USB_AUTOSTART=1 ./scripts/build.sh rt
# Also works with rt-wifi or rt-wifi-ap
```

Normal builds keep the addon disabled. The addon uses a separate output tree
(`/tmp/fastlinux-build-usb`) and image (`artifacts/fastlinux-rt-usb.img.gz`).
Use a separate `FASTLINUX_OUT` when changing addon settings. This option does
not enable Wi-Fi or internet sharing.

The build script enables `BR2_PACKAGE_NINJALINUX_USB_AUTOSTART=y` and appends
`board/fastlinux/usb-autostart.fragment` for built-in USB mass-storage/SCSI
disk support and UTF-8 FAT filenames. Manual Buildroot configurations need
both the switch and fragment. Previously released images do not acquire this
feature automatically: build an addon-enabled image first. Afterwards,
changing cartridges does not require rewriting the SD card.

## Prepare a cartridge

FAT32 with an MBR partition table is recommended and can be edited directly
on Windows. ext4 and a filesystem placed directly on the whole USB disk are
also supported. exFAT and NTFS are unsupported.

Copy the **contents** of [examples/usb-cartridge](../examples/usb-cartridge)
to the stick's root:

```text
autostart.json
app/
  main.py
```

The example displays a fullscreen PySide6 label. Replace it with your own app
or an export from ui-tools. Use Python/Qt modules already available in the
image: dependencies are not installed from the cartridge.

```json
{
  "version": 1,
  "writable": true,
  "type": "python3",
  "program": "app/main.py",
  "args": [],
  "cwd": "app"
}
```

- `version`: currently `1`.
- `writable`: `true` enables writes and persistent cartridge settings.
  `false` or an absent field keeps read-only media and RAM state.
  The supplied example enables it.
- `type`: `python3` or `native`.
- `program`: program file, relative to the volume root.
- `args`: optional array of strings, passed literally without shell evaluation.
- `cwd`: optional working directory relative to the volume root, default `.`.
  The example starts in the application's own directory.

For a native executable, use `"type": "native"` and e.g.
`"program": "app/panel"`. Build for AArch64 Linux with compatible ninjaLinux
libraries; mark it executable on ext4. Python files need no executable bit.
Paths must remain inside the volume. Save JSON as UTF-8 without a BOM.

## Boot and operation

1. Insert the stick while power is off. Display touch, Ethernet and the stick
   may share the Zero 2 W's single USB host connection; provide a suitable
   USB hub and adequate power.
2. Power on. Init scans once before starting the UI. The discovery window is
   three seconds; filesystem mount attempts can take additional time. Actual
   boot overhead has not been measured on hardware.
3. Exactly one valid cartridge overrides the built-in app. No cartridge, an
   invalid manifest/program path, or multiple valid cartridges selects the
   usual built-in app. Unselected/invalid volumes are unmounted.
4. Inserting a stick later never launches or switches applications. Power off
   to change cartridges. Do not unplug a stick while its application is running.

Discovery mounts all volumes read-only. Only the uniquely selected cartridge
is reopened writable (`rw,nodev,nosuid`) when `writable: true`; other volumes
are never written by the scanner. The app runs directly from USB using the
existing EGLFS/KMS environment and UI affinity. The supervisor restarts it
two seconds after exit/crash. Boot without the cartridge to bypass a broken
app. Writable mount/state-directory failure selects the built-in app instead.

In writable mode, `HOME` is `.ninjalinux-state` on the stick; XDG cache,
config and data use its `cache`, `config` and `data` subdirectories. Standard
Qt QSettings/XDG settings therefore **stay on the cartridge**, rather than in
the internal `/data`. Explicit application writes to `/data/...` are not
redirected: use QSettings, XDG locations or the cartridge's own directory.
Shut down cleanly before removing writable media.

With `writable: false`, the selected volume remains `ro,nodev,nosuid`. FAT uses
UTF-8 filenames; ext4 disables journal replay (`noload`), so use a cleanly
unmounted ext4 volume. HOME/XDG locations are then in RAM under
`/run/ninjalinux-usb-app/home` and are lost on reboot. Python bytecode writes
are disabled in both modes. Root stays read-only; the addon does not install
an app or alter internal `/data` configuration. Ordinary services, including
SSH key management, still operate independently. This is not a sandbox:
cartridges run as the existing UI user, root. Use trusted cartridges.

## Diagnostics and verification

Over SSH:

```sh
cat /tmp/usb-app.log
cat /run/ninjalinux-usb-app/selected.json
cat /tmp/fastlinux-ui.log
mount | grep ninjalinux-usb-app
```

No `selected.json` means the built-in app is selected. The `scanned` marker
prevents another scan within the same boot; it is not persistent configuration.
Only USB-backed `sd*` block devices are considered, never SD-card partitions.

Run offline tests with `python3 -m unittest discover -s tests`. Coverage includes
manifest/path validation, literal arguments, boot-only discovery, ambiguity,
mount failures, RAM directories and execution. Mount/exec operations are mocked.
Buildroot Kconfig resolution was checked. A complete addon image build, physical
USB boot and RT load measurements remain to be performed.
