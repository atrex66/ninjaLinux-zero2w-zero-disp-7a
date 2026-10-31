#!/usr/bin/env python3
"""Finalize optional Wi-Fi files in a disposable Buildroot target/image tree."""
from pathlib import Path
import sys

def enabled(config):
    return 'BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y' in Path(config).read_text().splitlines()

def target(root,wifi,ap=False):
    root=Path(root)
    # The generic dnsmasq init would start a second, unrestricted instance.
    (root/'etc/init.d/S80dnsmasq').unlink(missing_ok=True)
    if not ap:
        for name in ('usr/libexec/ninjalinux-wifi-ap','etc/ninjalinux-wifi-ap.dnsmasq.conf'):
            (root/name).unlink(missing_ok=True)
    if not wifi:
        for name in ('etc/init.d/S36wifi','usr/libexec/ninjalinux-wifi','usr/libexec/ninjalinux-wifi-dhcp'):
            (root/name).unlink(missing_ok=True)
        return
    # Keep the two Zero 2 W radio revisions and the kernel's board-name aliases.
    brcm=root/'lib/firmware/brcm'
    for p in brcm.iterdir():
        keep=p.name.startswith(('brcmfmac43436-', 'brcmfmac43436s-',
              'brcmfmac43430-sdio.raspberrypi,model-zero-2-w.',
              'brcmfmac43430b0-sdio.raspberrypi,model-zero-2-w.'))
        if '.raspberrypi,' in p.name and ',model-zero-2-w.' not in p.name:keep=False
        if not keep and (p.is_file() or p.is_symlink()):p.unlink()
    cypress=root/'lib/firmware/cypress'
    if cypress.exists():
        for p in cypress.iterdir():
            if p.is_file() or p.is_symlink():p.unlink()
    for prefix in ('brcmfmac43430','brcmfmac43430b0'):
        for ext in ('bin','txt'):
            p=brcm/f'{prefix}-sdio.raspberrypi,model-zero-2-w.{ext}'
            assert p.is_file(),f'Missing/dangling Zero 2 W firmware: {p}'

def boot(root,wifi):
    root=Path(root)
    if wifi:
        p=root/'config.txt';p.write_text(p.read_text().replace('dtoverlay=disable-wifi\n',''))
        (root/'overlays/disable-wifi.dtbo').unlink(missing_ok=True)
        p=root/'BOOT-README.txt';p.write_text(p.read_text().replace('Wi-Fi vagy Bluetooth','Bluetooth')+
            '\nOptional local Wi-Fi profile: connection starts only with a matching\n'
            '/data/wifi/wpa_supplicant.conf (rt-wifi) or hostapd.conf (rt-wifi-ap).\n'
            'See docs/wifi.md or docs/wifi.hu.md. No internet sharing.\n')

if __name__=='__main__':
    mode,config,root=sys.argv[1:]
    if mode=='target':target(root,enabled(config),'BR2_PACKAGE_HOSTAPD=y' in Path(config).read_text().splitlines())
    else:boot(root,enabled(config))
