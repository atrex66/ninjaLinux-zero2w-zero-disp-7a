#!/usr/bin/env python3
import dbus, gzip, hashlib, json, os, pathlib, time
import sys
root = pathlib.Path(__file__).resolve().parent.parent
bus = dbus.SystemBus()
obj = bus.get_object('org.freedesktop.UDisks2','/org/freedesktop/UDisks2/block_devices/sdb')
props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
block = props.GetAll('org.freedesktop.UDisks2.Block')
assert int(block['Size']) == 2008023040 and not block['ReadOnly']
drive = bus.get_object('org.freedesktop.UDisks2', block['Drive'])
dp = dbus.Interface(drive, 'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.UDisks2.Drive')
assert str(dp['Serial']) == '121220160204'
p = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'backups'/'sd-original-121220160204.img.gz'
assert not p.exists(), 'Backup already exists'
assert not pathlib.Path(str(p)+'.partial').exists(), 'Partial backup already exists'
manager=dbus.Interface(bus.get_object('org.freedesktop.UDisks2','/org/freedesktop/UDisks2'),'org.freedesktop.DBus.ObjectManager')
for path,interfaces in manager.GetManagedObjects().items():
    part=interfaces.get('org.freedesktop.UDisks2.Partition',{})
    if str(part.get('Table',''))==str(obj.object_path):
        assert not interfaces.get('org.freedesktop.UDisks2.Filesystem',{}).get('MountPoints',[]), 'Card is mounted'
fd = dbus.Interface(obj, 'org.freedesktop.UDisks2.Block').OpenForBackup({}).take()
h = hashlib.sha256(); size = 0
with os.fdopen(fd,'rb') as src, gzip.open(str(p)+'.partial','wb',compresslevel=1) as dst:
    while True:
        b=src.read(4*1024*1024)
        if not b: break
        h.update(b); dst.write(b); size += len(b)
        if size%(64*1024*1024)==0: print('backup',size,'/ 2008023040',flush=True)
assert size == 2008023040
os.rename(str(p)+'.partial',p)
meta={'device':'/dev/sdb','serial':'121220160204','bytes':size,'sha256_uncompressed':h.hexdigest()}
p.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta), flush=True)
