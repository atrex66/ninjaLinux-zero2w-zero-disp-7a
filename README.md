# ninjaLinux for Zero 2 W and Zero-DISP-7A

**[Magyar / Hungarian](README.hu.md)** · English

[Download release candidate v0.1.0-rc1: SD image, checksums and corresponding sources](https://github.com/atrex66/ninjaLinux-zero2w-zero-disp-7a/releases/tag/v0.1.0-rc1)

A fast-boot PREEMPT_RT Linux appliance for Raspberry Pi Zero 2 W and Waveshare
Zero-DISP-7A, with Python/PySide6, hardware-accelerated EGLFS/KMS graphics,
USB touch and standalone LinuxCNC-derived Automation HAL.

The combined SD image has passed a physical boot, touch, SSH provisioning,
HAL functional test and a short graphics/Ethernet timing trial. This is a
release candidate; a clean build on another machine and physical motion I/O
have not been validated.

## System

| Item | Configuration |
|---|---|
| Kernel | `6.12.61-ninjalinux-rt-irq1`, PREEMPT_RT only |
| IRQ fix | BCM2836 ARMCTRL routing respects domain housekeeping CPUs |
| CPU0–1 | System processes and device IRQ threads |
| CPU2 | PySide6 GUI |
| CPU3 | HAL, actual RT thread verified as SCHED_FIFO 98 |
| Graphics | VC4 V3D 2.1, Mesa EGL/GLES, Qt EGLFS/KMS, 1024×600 at 60 Hz |
| Software | Buildroot 2026.08.1; Qt/PySide6 6.11.2; Python 3.14.8 |
| Ethernet | USB RTL8152; static `192.168.0.234/24`; gateway `192.168.0.1` |
| Storage | Read-only root; RAM-backed temporary files; 1 GiB persistent `/data` |
| SD image | 1,678,770,176 bytes; compressed image 65.4 MiB |

The default `rt` image has no desktop, X11, Wayland, login terminals, Wi-Fi, Bluetooth or audio output.
BusyBox init starts the GUI directly, without a systemd multi-user target.
Required device drivers are built in for the default profile. HAL userspace `.so` components are
separate from kernel modules. VC4 requires some ALSA/ASoC infrastructure;
audio output is disabled in the device tree.

## Measurements — physical Zero 2 W, 2026-10-31

### HAL period error, graphics and USB/Ethernet load

Both runs used a 1 ms HAL thread, SCHED_FIFO 98 on CPU3, continuously animated
PySide6/VC4 graphics and 70 MiB transmitted over RTL8152 Ethernet/SSH at about
1 MiB/s. The transfer occupied seconds 55–125. The RT component records every
cycle; the thread briefly stops at the end for a consistent histogram read,
then restarts. Requested observation was 130 seconds; command processing
made each complete observation about 131 seconds.

| Trial | Cycles | Max. absolute period error | Mean absolute period error | Intervals ≥2 ms |
|---|---:|---:|---:|---:|
| Development system with patched RT + HAL | 131,023 | 45.677 µs | 1.694 µs | 0 |
| Combined RT + HAL SD image, freshly booted | 131,019 | **37.708 µs** | **1.896 µs** | 0 |

| IRQ observation during the same trials | Development system | Combined SD image |
|---|---:|---:|
| USB IRQ increments on CPU0–1 | 1,372,008 | 1,371,688 |
| All ARMCTRL device IRQ increments on CPU2 | 0 | 0 |
| All ARMCTRL device IRQ increments on CPU3 | 0 | 0 |

Actual device IRQ thread affinity was CPU0–1, GUI affinity CPU2 and HAL RT
thread affinity CPU3. The boot ID and GUI process remained unchanged.
Local timers, IPI and IRQ-work activity remain; this is not a claim that CPU3
receives no interrupts. `NO_HZ_FULL` and RCU offload are not enabled. Keep
housekeeping CPUs 0–1 online.

[Combined-image raw data and report](docs/meresek/2026-10-31-sd-image/report.json)
· [development trial](docs/meresek/2026-10-31-hal-irq/report.json)

### Earlier cyclictest baseline — different metric

The earlier unisolated RT kernel ran four locked-memory SCHED_FIFO 80
cyclictest threads for 600 seconds, each with a 1 ms interval, while the
PySide6 GPU animation ran. There was no HAL, IRQ patch or Ethernet stress.
Total: 2,399,892 cycles; maximum wake-up latency across all CPUs: **398 µs**.

| CPU | Maximum wake-up latency | Mean wake-up latency |
|---|---:|---:|
| 0 | 398 µs | 14.13 µs |
| 1 | 294 µs | 12.99 µs |
| 2 | 310 µs | 11.47 µs |
| 3 | 360 µs | 11.92 µs |

HAL absolute period error and cyclictest wake-up latency are different
metrics. Their durations, priorities and workloads also differ; **these
numbers do not establish a direct speed-up ratio**. The baseline tool's raw
`realtime=0` field relied on an absent legacy sysfs file; the running kernel's
own configuration and uname independently confirmed PREEMPT_RT.
[Baseline report](docs/meresek/2026-10-31-rt-baseline/report.json).

### Boot and functional checks

- Combined SD image: first rendered frame at **8.02 seconds of kernel uptime**.
  This is one boot, excluding firmware time; it is not total power-on timing
  or a repeated boot-time distribution.
- VC4 V3D 2.1 hardware rendering and the touch-test button worked; the user
  confirmed touch operation on the freshly flashed image.
- First boot generated a new per-device Ed25519 SSH host key and imported the
  supplied public administrator key from the FAT partition; key login worked.
- HAL `and2`/`timedelay` software logic produced **FALSE → TRUE → FALSE**.
  The Python binding created, wrote and read a component pin successfully.
- The 1.6 GiB test image was completely read back from the 2 GB SD card and
  its SHA256 matched before the physical boot.

These short software-only tests are not physical CNC acceptance tests or
worst-case timing guarantees. CPU temperature was unavailable. Sustained SD
stress, controlled touch stress, long repeated runs and actual I/O validation
remain application-specific work.

## Build

On an x86_64 Linux host:

```sh
bash scripts/fetch-buildroot.sh
bash scripts/build.sh rt
```

Host prerequisites include GCC/G++, make, rsync, bison, flex, CMake, Ninja,
unzip, wget and LLVM19 headers under `/usr/lib/llvm-19`. Scripts do not install
global packages. Buildroot fetches pinned sources and the Bootlin ARM64
GCC14.3/glibc toolchain. Boost1.83 headers and Yapps2.2.1 sources are included
under `third_party`; the old SD card and host LinuxCNC installation are not
required. A clean rebuild on a different host is still untested.

The default build directory is `/tmp/fastlinux-build`; it disappears on host
reboot and a clean build can exceed a 7.8 GiB tmpfs. Use a larger location:

```sh
FASTLINUX_OUT=/path/with/enough/space bash scripts/build.sh rt
```

Output: `artifacts/fastlinux-rt.img.gz` and its SHA256 file. The image has a
64 MiB boot partition, 512 MiB root and 1024 MiB data partition, fitting the
tested 2,008,023,040-byte card. Only one RT kernel is included.

## First boot

1. Flash the image to an SD card; this replaces that card's contents.
2. Copy your **public** SSH key to the FAT boot partition as `authorized_keys`
   before the first boot. Never copy a private key.
3. Connect the display and RTL8152 Ethernet, then boot. The GUI starts directly.
4. SSH to `root@192.168.0.234` with the corresponding key. Each card creates
   its own host key under `/data/ssh`; no shared private host key or developer
   administrator key is baked into the release image.

Without a supplied public key the GUI works, but remote login is unavailable.
Import occurs only while `/data/ssh/authorized_keys` is absent. Password SSH
login is disabled. DNS defaults to `84.2.44.8` and `84.2.46.8`; adjust the
network configuration for other networks. Persistent files belong under `/data`.

## Standalone HAL

HAL is installed under `/opt/automation-hal`, with a dedicated `ahal` user,
private IPC keys and runtime state. It starts manually; the GUI remains a
graphics/touch demo and is not a HAL control panel.

```sh
ninjalinux-hal start /data/hal/logic.hal
```

The administrator launcher passes RT/memory limits, then drops to `ahal`.
The RT thread runs on CPU3. The command stays in the foreground; Ctrl-C stops
its own session. The supplied example has no physical motion output.

From another SSH connection:

```sh
su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal cmd show thread'
su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal python'
```

Checks and source collection:

```sh
zcat /proc/config.gz | grep '^CONFIG_PREEMPT_RT=y$'
fastlinux-python-check
# Run on the Pi after starting the software-only HAL example:
python3 pi-runtime-check.py
# Run on the build host:
bash scripts/collect-legal-info.sh
```

The target check script is `scripts/pi-runtime-check.py`; copy it to the Pi
before invoking it. `fastlinux-rt-check 10m` runs the independent cyclictest
recipe. The HAL timing probe stops/restarts its software thread and must not
be run while controlling physical machinery.

## Sources and licenses

Original project scripts/overlay/demo: MIT. Automation HAL and latency
component: GPL-2.0-or-later. Other components retain their own licenses.
See [LICENSE](LICENSE), [third-party notes](third_party/README.hu.txt), and
[source/license collection notes](docs/LICENC-ALLAPOT.hu.txt).

Binary release candidates include the generic SD image, SHA256 checksums and
a corresponding-source bundle with Buildroot, applied patches, project source,
package licenses, and pinned GCC/glibc runtime sources. The separately
personalized test image, SD backups, local logs and personal keys are excluded.

## Remote access guides

- [SSHFS: mount remote files from Linux](docs/sshfs.md)
- [Original HALShow: connect and watch the running Pi HAL](docs/halshow.md)
- [Windows: PowerShell SSH, WinSCP and WSL2 HALShow](docs/windows-remote.md)

See [changes.log](changes.log) for the project change history. The application has its own repository and operator manuals.

## Optional local Wi-Fi / hand-controller AP

Choose at build time: `./scripts/build.sh rt-wifi` for a local Wi-Fi client, or `./scripts/build.sh rt-wifi-ap` for a dedicated WPA2 access point with DHCP for remote hand controllers. The default `rt` stays Ethernet-only. AP address: `192.168.4.1`; no internet gateway, DNS forwarding, bridge, NAT or cloud services are added. The hand-controller command protocol is a separate future layer.

[Build profiles, provisioning and verification limits](docs/wifi.md). All three Buildroot profiles and the pinned kernel configurations were resolved; 14 offline tests and firmware alias/hash checks passed. A new complete SD image and physical Wi-Fi/AP/RT tests are still pending.
