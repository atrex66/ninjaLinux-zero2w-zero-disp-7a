#!/usr/bin/env python3
"""Offline image and DHCP-policy tests. Never modifies host network state."""
import importlib.machinery,importlib.util,shutil,tempfile,unittest,subprocess,os,sys
sys.dont_write_bytecode=True
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 loader=importlib.machinery.SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(name,loader)
 module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module
image=load('wifi_image',ROOT/'scripts/configure-wifi-image.py')
dhcp=load('wifi_dhcp',ROOT/'board/fastlinux/rootfs-overlay/usr/libexec/ninjalinux-wifi-dhcp')
class ImageTests(unittest.TestCase):
 def test_no_wifi_removes_optional_startup_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ('etc/init.d/S36wifi','usr/libexec/ninjalinux-wifi','usr/libexec/ninjalinux-wifi-dhcp'):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
   image.target(root,False)
   self.assertFalse((root/'etc/init.d/S36wifi').exists())
   self.assertEqual(list((root/'usr/libexec').iterdir()),[])
 def test_boot_enables_only_wifi_and_preserves_bt_audio_flags(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);shutil.copy2(ROOT/'board/fastlinux/config.txt',root/'config.txt')
   shutil.copy2(ROOT/'board/fastlinux/BOOT-README.txt',root/'BOOT-README.txt')
   (root/'overlays').mkdir();(root/'overlays/disable-wifi.dtbo').touch()
   image.boot(root,True);text=(root/'config.txt').read_text()
   self.assertNotIn('disable-wifi',text);self.assertIn('dtoverlay=disable-bt',text)
   self.assertIn('dtparam=audio=off',text);self.assertFalse((root/'overlays/disable-wifi.dtbo').exists())
 def test_firmware_pruning_keeps_alias_targets_and_regdb(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);brcm=root/'lib/firmware/brcm';brcm.mkdir(parents=True)
   (root/'lib/firmware/regulatory.db').touch()
   for prefix,target in [('brcmfmac43430','brcmfmac43436s'),('brcmfmac43430b0','brcmfmac43436')]:
    for ext in ('bin','txt'):
     (brcm/f'{target}-sdio.{ext}').touch()
     (brcm/f'{prefix}-sdio.raspberrypi,model-zero-2-w.{ext}').symlink_to(f'{target}-sdio.{ext}')
   (brcm/'brcmfmac4356-sdio.bin').touch();image.target(root,True)
   self.assertFalse((brcm/'brcmfmac4356-sdio.bin').exists())
   self.assertTrue((root/'lib/firmware/regulatory.db').exists())
 def test_config_switch_has_exact_enabled_semantics(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config';p.write_text('# BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI is not set\n')
   self.assertFalse(image.enabled(p));p.write_text('BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y\n')
   self.assertTrue(image.enabled(p))
class DHCPTests(unittest.TestCase):
 def calls(self,event,env):
  with patch.object(dhcp.subprocess,'run') as run:
   dhcp.main(event,env);return [c.args[0] for c in run.call_args_list]
 def test_lease_adds_lower_priority_routes_and_source_policy(self):
  env=dict(interface='wlan0',ip='192.168.0.88',subnet='255.255.255.0',router='192.168.0.1')
  for event in ('bound','renew'):
   calls=self.calls(event,env)
   self.assertIn(['ip','addr','add','192.168.0.88/24','dev','wlan0','noprefixroute'],calls)
   self.assertIn(['ip','route','add','192.168.0.0/24','dev','wlan0','src','192.168.0.88','metric','600'],calls)
   self.assertIn(['ip','rule','add','priority','16600','from','192.168.0.88/32','lookup','166'],calls)
   self.assertFalse(any('eth0' in c for c in calls))
   self.assertFalse(any('default' in c for c in calls))
 def test_deconfigure_only_removes_wifi_state(self):
  calls=self.calls('deconfig',dict(interface='wlan0'))
  self.assertTrue(all('166' in c or '16600' in c or 'wlan0' in c for c in calls))
  self.assertNotIn(['ip','route','flush','table','main'],calls)
 def test_bad_lease_or_interface_cannot_change_routes(self):
  for env in (dict(interface='eth0'),dict(interface='wlan0',ip='invalid')):
   with patch.object(dhcp.subprocess,'run') as run:
    with self.assertRaises(ValueError):dhcp.main('bound',env)
    run.assert_not_called()
 def test_no_router_keeps_on_link_management(self):
  calls=self.calls('bound',dict(interface='wlan0',ip='10.0.0.8',subnet='255.255.255.0'))
  self.assertFalse(any('default' in c for c in calls))
 def test_ignored_events_do_not_modify_routes(self):
  self.assertEqual(self.calls('leasefail',dict(interface='wlan0')),[])
class APTests(unittest.TestCase):
 CONFIG='interface=wlan0\ndriver=nl80211\ncountry_code=HU\nssid=TestOnly\nhw_mode=g\nchannel=6\nwpa=2\nwpa_key_mgmt=WPA-PSK\nrsn_pairwise=CCMP\nwpa_passphrase=ExampleOnly123\n'
 def execute(self,config):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);conf=root/'hostapd.conf';conf.write_text(config);log=root/'actions'
   for name in ('ip','dnsmasq','hostapd','start-stop-daemon'):
    p=root/name;p.write_text('#!/bin/sh\nprintf "%s\\n" "'+name+' $*" >> "$TEST_ACTIONS"\n');p.chmod(0o755)
   env=dict(os.environ,PATH=str(root)+':'+os.environ['PATH'],TEST_ACTIONS=str(log),NINJALINUX_WIFI_AP_CONFIG=str(conf))
   p=subprocess.run(['sh',str(ROOT/'board/fastlinux/rootfs-overlay/usr/libexec/ninjalinux-wifi-ap')],env=env,capture_output=True,text=True)
   return p.returncode,log.read_text() if log.exists() else ''
 def test_ap_requires_encryption_before_network_actions(self):
  status,log=self.execute('interface=wlan0\ndriver=nl80211\n')
  self.assertNotEqual(status,0);self.assertEqual(log,'')
 def test_ap_rejects_bridge_before_network_actions(self):
  status,log=self.execute(self.CONFIG+'bridge=br0\n')
  self.assertNotEqual(status,0);self.assertEqual(log,'')
 def test_ap_runs_local_address_and_daemons_with_no_default_route(self):
  status,log=self.execute(self.CONFIG)
  self.assertEqual(status,0);self.assertIn('ip address replace 192.168.4.1/24 dev wlan0',log)
  self.assertIn('dnsmasq --conf-file=',log);self.assertIn('hostapd -P',log)
  self.assertNotIn('default',log);self.assertNotIn('eth0',log)
 def test_duplicate_security_setting_cannot_open_ap(self):
  status,log=self.execute(self.CONFIG+'wpa=0\n')
  self.assertNotEqual(status,0);self.assertEqual(log,'')
 def test_dhcp_advertises_neither_gateway_nor_dns(self):
  text=(ROOT/'board/fastlinux/rootfs-overlay/etc/ninjalinux-wifi-ap.dnsmasq.conf').read_text().splitlines()
  for directive in ('port=0','interface=wlan0','dhcp-option=option:router','dhcp-option=option:dns-server'):
   self.assertIn(directive,text)

if __name__=='__main__':unittest.main()
