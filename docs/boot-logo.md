# Custom boot logo

**[Magyar](boot-logo.hu.md)**

A PNG/SVG logo is converted to 1024×600 on the **build host** and embedded in
PSplash. The Pi needs neither an SVG renderer nor image-file decoding at boot.
The logo is optional; ordinary images keep their existing behavior.

## Build

```sh
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.png" ./scripts/build.sh rt
# Same logo from SVG:
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.svg" ./scripts/build.sh rt
# Combine with USB cartridges:
NINJALINUX_USB_AUTOSTART=1 \
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.png" ./scripts/build.sh rt
```

Set the variable to your own PNG/SVG path to replace the example. The option
also works with `rt-wifi` and `rt-wifi-ap`. The supplied example uses the
user's ninja-eyes vector artwork, with white filled paths on black.
[PNG](../examples/boot-logo/ninjalinux.png) · [SVG](../examples/boot-logo/ninjalinux.svg).

The host needs Python 3 and Pillow (`python3-pil` on Debian). SVG additionally
requires `rsvg-convert` (`librsvg2-bin`) or ImageMagick. The PNG input needs no
SVG renderer. Conversion preserves aspect ratio, centers the image and fills
transparency/unused space with black. A 1024×600 source gives exact placement.
Convert SVG text to paths when you want independence from host fonts.

Logo builds use a separate tree and image:
`/tmp/fastlinux-build-logo`, `artifacts/fastlinux-rt-logo.img.gz`.
With USB enabled, the suffix is `-usb-logo`. Use separate `FASTLINUX_OUT` trees
when changing addon settings. Changing the image inside a logo-enabled tree
forces a PSplash rebuild. Replacing this early logo requires a new system
image; application cartridges remain independently interchangeable.

## When is it visible?

Early userspace init (`S12boot-logo`) starts the logo after `/dev/fb0` becomes
available and before the Qt/Python application. It is not the first firmware
frame after power-on: kernel/display initialization happens first. There is
no artificial minimum display duration or animation. The framebuffer writer
stops before Qt starts. Exact appearance time and KMS/Qt handoff still need
physical testing; seamless handoff has not been established on hardware.

## Skip errors without blocking startup

- Missing, unreadable, malformed or unsupported source images produce a warning
  and the build **continues without the logo**. Missing host converters also
  skip it. Inputs are limited to 16 MiB; SVG conversion has a ten-second timeout.
- The finished logo is compiled into the program: no separate PNG/SVG is read at boot.
- Init never waits for the splash process. Its background framebuffer discovery
  lasts at most five seconds, or until the UI starts.
- A failed writer simply exits. UI startup waits at most approximately 0.3 seconds
  for splash shutdown; UI restarts never restart the logo. Splash init always
  returns success.

This handles logo failures, without hiding unrelated system build errors.

## Diagnostics and verification

```sh
cat /tmp/boot-logo.log
ls /run/ninjalinux-boot-logo
```

Temporary state lives in `/run`, with no logo state written to the SD card.
The writer uses `psplash -n`, with no console/VT switching, progress bar or
startup message. PSplash keeps its original GPL-2.0-or-later license and is
covered by Buildroot source/license collection; repository scripts retain
the repository license.

Run offline tests using `python3 -m unittest discover -s tests` (requires Pillow).
Tests cover PNG size/transparency, SVG conversion, missing/bad images and splash
startup/shutdown races without a real framebuffer. Buildroot Kconfig resolution
was checked. A complete logo-enabled image build, physical Pi boot and RT
measurements remain pending.
