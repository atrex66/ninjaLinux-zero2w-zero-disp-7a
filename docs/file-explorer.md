# On-demand browser file explorer

**[Magyar](file-explorer.hu.md)**

Manage ninjaLinux's `/data` directory from a desktop or mobile browser on
the local network. No PC/phone installation or SSH key is needed: each
appliance has its own configured access code.

![Desktop file explorer](screenshots/file-explorer.png)

## Build and enable

```sh
NINJALINUX_FILE_EXPLORER=1 ./scripts/build.sh rt
# Combine with other addons:
NINJALINUX_FILE_EXPLORER=1 NINJALINUX_USB_AUTOSTART=1 \
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.png" ./scripts/build.sh rt
```

The addon uses separate output/image names ending in `-explorer`, e.g.
`/tmp/fastlinux-build-explorer` and `artifacts/fastlinux-rt-explorer.img.gz`.
All addons above together use `-usb-logo-explorer`. It also supports `rt-wifi`
and `rt-wifi-ap`. Use separate `FASTLINUX_OUT` trees when changing addons.
Previously released images do not update automatically: build an addon image.

Fill the `token` in the [example configuration](../examples/file-explorer/file-explorer.json)
with **your own random access code**. The sample intentionally has an empty
code and cannot activate the listener. There is no shared/default code.

```json
{
  "enabled": true,
  "port": 8080,
  "idle_timeout": 30,
  "token": ""
}
```

Fill the `token` field: use 24–128 printable ASCII characters without
whitespace. On Linux, generate one with:

```sh
python3 -c 'import secrets; print(secrets.token_urlsafe(24))'
```

Windows PowerShell:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Save JSON as UTF-8 without a BOM. Either:

- Put `file-explorer.json` in the FAT boot partition of the powered-off
  appliance's SD card. First valid provisioning copies it to
  `/data/file-explorer.json`; no SSH access is required.
- With existing SSH access, create `/data/file-explorer.json` directly,
  with mode `600`.

An existing `/data/file-explorer.json` takes precedence and is never replaced
from boot. Missing, disabled or invalid settings keep the web service off;
**normal appliance/UI startup continues**. Restart the service after changes:
`/etc/init.d/S38file-explorer restart`, or reboot. After provisioning, the
copy of the access code on the boot partition can be removed.

## Operation

Open **`http://192.168.0.234:8080`**, using the Pi's actual address and configured
port. On a local Wi-Fi AP, its AP address also works. Enter the access code;
the `EN`/`HU` button switches languages.

- Browse directories, move up and use breadcrumbs back to `/data`.
- Upload one or more files, up to 64 MiB each, with explicit overwrite
  confirmation. Uploads use temporary files and atomic replacement; an
  interrupted transfer preserves the original. Existing ownership/mode are retained.
- Download files to the PC/phone.
- Create folders and rename files/folders without overwriting another entry.
- Confirm deletion of files or empty folders; no recursive deletion.
- Edit UTF-8 text up to 1 MiB, with explicit save/overwrite confirmation,
  including JSON, HAL and text settings.

Changes do not automatically restart HAL or the UI. The root partition stays
read-only. Symlinks/special files are neither followed nor modified; each
listing supports at most 5000 entries. Cartridge mounts below `/data/cartridges` are also browsable; writes
require the cartridge's `writable: true` setting.

The access code stays only in the browser tab's memory; reloading/signing out
requires entering it again. Filenames/content are never executed as HTML.
This uses local **HTTP without TLS**, intended for a trusted machine/local
network; do not expose it to the internet.

## Activation and timeouts

Only BusyBox `inetd` stays resident, listening on the chosen port. Python
starts **on an incoming TCP connection**, before reading its HTTP request.
A browser request cannot be detected with no listener at all.

In inetd `wait` mode, the worker inherits the listening socket. One worker
serves requests sequentially, without polling or browser keepalives. It exits
after `idle_timeout` (default 30, configurable 5–300 seconds) without a new
connection. The next operation automatically reactivates it without reloading
the page. Empty/slow connections have a 15-second socket timeout; each request
has a 60-second absolute deadline. Other operations may wait during a long
transfer. Listener and worker use housekeeping CPUs 0–1, outside HAL's
isolated cores.

## Diagnostics and verification

```sh
cat /tmp/file-explorer.log
cat /run/ninjalinux-file-explorer/inetd.pid
cat /run/ninjalinux-file-explorer/worker.pid
```

The last file exists only while a Python worker is active. Stop with
`/etc/init.d/S38file-explorer stop`. Set `enabled: false` in
`/data/file-explorer.json` and restart the service/appliance to keep it off.

Run `python3 -m unittest discover -s tests` with local loopback sockets permitted
and Pillow installed. Tests use temporary directories and real HTTP, checking
authentication, path/symlink boundaries, interrupted uploads, atomic rename,
idle exit/reactivation. Chromium desktop/mobile verification covered UTF-8
upload/edit/save, folders, download/delete, language switching and sign-out.
Buildroot Kconfig resolution was checked. Target installation, a complete image
build and RT load measurements remain pending; the live Pi was not modified.
