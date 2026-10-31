# Optional Wi-Fi builds: local automation networks

[Magyar](wifi.hu.md)

The default `rt` image remains Ethernet-only. All profiles use PREEMPT_RT,
VC4/EGLFS, USB touch and the same IRQ/core-isolation patch.

| Build command | Local networking support |
|---|---|
| `./scripts/build.sh rt` | Existing Ethernet-only, module-free kernel |
| `./scripts/build.sh rt-wifi` | On-board Wi-Fi client, WPA2-PSK and DHCP address |
| `./scripts/build.sh rt-wifi-ap` | Dedicated WPA2 AP and local DHCP for remote hand controllers |

The AP profile adds hostapd/dnsmasq rather than wpa_supplicant. It does not
provide a hand-controller command protocol yet: it provides its local network.
These profiles add no internet sharing, bridge, NAT, DNS forwarding, cloud
service or desktop. Wi-Fi DHCP clients use only the local address/subnet,
not a DHCP-supplied default route or DNS. Existing Ethernet configuration is
unchanged. The Pi Zero 2 W radio supports **2.4 GHz**; see the
[Raspberry Pi hardware documentation](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/getting-started/setting-up.adoc).

## Build isolation and firmware

Defaults use separate build outputs: `/tmp/fastlinux-build`,
`/tmp/fastlinux-build-rt-wifi`, `/tmp/fastlinux-build-rt-wifi-ap`, and separate
image directories under `artifacts/`. A `FASTLINUX_OUT` override must also
remain profile-specific. The builder rejects mixing profiles in one output
tree: Buildroot cannot uninstall packages simply by switching configuration.
Images are named `fastlinux-rt[-wifi[-ap]].img.gz`, with checksums.

The Wi-Fi fragment enables only cfg80211, brcmutil and brcmfmac as loadable
wireless subsystems. Other required drivers remain built in. Loading Wi-Fi
from the background worker after root is mounted avoids requesting firmware
before `/lib/firmware` is available. No configuration file means no Wi-Fi
connection worker or module load from this service. GUI boot does not wait
for association or DHCP. Bluetooth and audio output remain disabled.

Firmware uses Buildroot's already pinned, hash-checked
[LibreELEC package](https://github.com/LibreELEC/brcmfmac_sdio-firmware-rpi/tree/6596d332eaadd63e2413e3937715a084f61c39e2).
Only the Zero 2 W's 43436/43436s files and required board-name aliases are kept.
Its proprietary firmware license remains part of Buildroot `legal-info`;
wireless-regdb and user-space packages keep their own licenses.

## Dedicated AP for hand controllers

Use the `rt-wifi-ap` image. Through Ethernet/SSH, create `/data/wifi` with mode
700, then `/data/wifi/hostapd.conf` with mode 600. Example (replace SSID,
passphrase and country with your own settings):

```ini
interface=wlan0
driver=nl80211
country_code=HU
ieee80211d=1
ssid=ninjaLinux-Control
hw_mode=g
channel=6
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=REPLACE_WITH_YOUR_OWN_PASSWORD
ap_isolate=1
```

The passphrase must be 8-63 printable ASCII characters. No shared real password is built into
the image or stored in Git. Keep `wpa_supplicant.conf` disabled/absent in AP
mode. Then:

```sh
/etc/init.d/S36wifi start
```

The Pi is **192.168.4.1/24** on this network; clients receive
**192.168.4.20-192.168.4.100**. DHCP advertises neither an internet gateway nor
a DNS server; dnsmasq's DNS service is disabled (`port=0`). The subnet is
separate from Ethernet's `192.168.0.0/24`. There is no bridge or forwarding
configuration. The service rejects open or bridged AP configuration.

Join the SSID from the controller/PC/phone and connect to `192.168.4.1`.
SSH/HALShow still require their existing SSH credentials; knowing the Wi-Fi
passphrase alone does not grant SSH access. A phone may report “no internet”:
choose to stay connected to this local network. AP client isolation allows
each controller to reach the Pi, without direct client-to-client traffic.

The ordinary DNS/DHCP init service is removed; only the explicit AP worker
starts the DHCP instance bound to `wlan0`. Processes are pinned to CPU0-1.
`stop`/`restart` use the same init script; restarting Wi-Fi drops its clients.

## Optional client profile

Use `rt-wifi`. Create `/data/wifi/wpa_supplicant.conf` with mode 600, inside a
mode-700 directory (replace the example settings):

```ini
ctrl_interface=/run/wpa_supplicant
country=HU
update_config=0
network={
    ssid="YOUR_LOCAL_NETWORK"
    psk="YOUR_OWN_PASSWORD"
    key_mgmt=WPA-PSK
}
```

Start the same init script. The local DHCP address is visible using
`ip -4 addr show dev wlan0`. Main-table Wi-Fi subnet routes have metric 600;
Ethernet's existing routes remain preferred. Source-based table 166, rule
priority 16600, ensures replies to the Wi-Fi address leave Wi-Fi when the
radio and Ethernet share a LAN. No Wi-Fi default route or DNS change is made.
This is not automatic internet failover. Table 166/priority 16600 are reserved
for this service. Disable one configuration before selecting the other mode;
the services reject two active Wi-Fi configuration files.

## Inspection and current verification

`/tmp/wifi.log`, `iw dev`, `ip -4 addr show dev wlan0`, and `ip rule` provide
network diagnostics. For station association use `wpa_cli -i wlan0 status`.
For AP leases inspect `/run/ninjalinux-wifi-ap.leases`.

Verified offline: all three Buildroot configurations resolve; the exact
pinned kernel's RT and wireless kernel configurations resolve and pass the
profile validator; pinned firmware archive SHA-256 matches; both board aliases
remain valid after pruning; tests cover DHCP routes, configuration isolation,
AP encryption/bridge guards, DHCP-only operation and daemon lifecycle.

**No new Wi-Fi SD image or physical Wi-Fi/AP/RT measurement has been completed.**
The existing Pi/card is unchanged. A complete image build and a physical
association/hand-controller-network test remain, including IRQ placement and
HAL timing under active Wi-Fi traffic. Existing Ethernet-only latency results
do not certify the Wi-Fi profile.

Offline regression command: `python3 tests/test_wifi.py`. For a Wi-Fi/AP release, run legal-info with its matching build tree, for example `FASTLINUX_OUT=/tmp/fastlinux-build-rt-wifi-ap ./scripts/collect-legal-info.sh`.
