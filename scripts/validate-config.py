#!/usr/bin/env python3
import pathlib, sys
p=pathlib.Path(sys.argv[1]); s=p.read_text().splitlines(); cfg=dict(x.split('=',1) for x in s if x.startswith('CONFIG_') and '=' in x)
profile=sys.argv[2] if len(sys.argv)>2 else 'rt'
wifi=profile in ('rt-wifi','rt-wifi-ap')
required=['SMP','SYSVIPC','HIGH_RES_TIMERS','FUTEX','DEVTMPFS','EXT4_FS','MMC','MMC_SDHCI_IPROC','MMC_BCM2835','I2C_BCM2835','CLK_BCM2835','CLK_RASPBERRYPI','RASPBERRYPI_POWER','RASPBERRYPI_FIRMWARE','BCM2835_MBOX','DRM','DRM_VC4','USB_DWC2','USB_HID','HID_MULTITOUCH','INPUT_EVDEV','INET','USB_RTL8152']
if wifi:required += ['MODULES','WIRELESS','WLAN','BRCMFMAC_SDIO','FW_LOADER']
for k in required:
 assert cfg.get('CONFIG_'+k)=='y',f'Missing built-in driver: {k}'
for k in ['BT','MEDIA_SUPPORT','DRM_V3D','SND_DUMMY','SND_ALOOP','SND_SEQUENCER','SND_RAWMIDI','USB_SERIAL','USB_STORAGE','ETHERNET','NETFILTER','NFS_FS','F2FS_FS','AUTOFS_FS','BLK_DEV_RAM','BLK_DEV_LOOP','BLK_DEV_INITRD','EFI']:
 assert cfg.get('CONFIG_'+k) not in ('y','m'),f'Unexpected enabled subsystem: {k}'
if wifi:
 for k in ('CFG80211','BRCMUTIL','BRCMFMAC'):
  assert cfg.get('CONFIG_'+k)=='m',f'Expected load-after-root Wi-Fi module: {k}'
 modules={key for key,value in cfg.items() if value=='m'}
 assert modules=={'CONFIG_CFG80211','CONFIG_BRCMUTIL','CONFIG_BRCMFMAC'},f'Unexpected loadable modules: {modules}'
for k in (['BRCMFMAC_USB','BRCMFMAC_PCIE'] if wifi else ['MODULES','WLAN','CFG80211','BRCMFMAC']):
 assert cfg.get('CONFIG_'+k) not in ('y','m'),f'Unexpected wireless subsystem: {k}'
if profile in ('rt','rt-wifi','rt-wifi-ap'):
 assert cfg.get('CONFIG_PREEMPT_RT')=='y','PREEMPT_RT did not resolve to y'
print('Kernel configuration checks passed:',p)
