#!/usr/bin/env python3
"""Write and read back only the previously identified 2 GB removable card."""
import dbus, gzip, hashlib, json, os, pathlib, struct, sys
root=pathlib.Path(__file__).resolve().parent.parent
image=pathlib.Path(sys.argv[1]).resolve()
assert image.is_file()
size=image.stat().st_size
assert 0 < size <= 2008023040
with image.open('rb') as f:
 mbr=f.read(512)
assert mbr[510:512]==b'\x55\xaa','Missing DOS partition signature'
parts=[struct.unpack_from('<B3sB3sII',mbr,446+i*16) for i in range(4)]
assert parts[0][2]==0x0c and parts[1][2]==0x83,'Unexpected partition layout'
assert (parts[1][4]+parts[1][5])*512 <= size,'Partition outside image'
backup=pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/'backups/sd-original-121220160204.img.gz'
meta=json.loads(backup.with_suffix('.json').read_text())
# Verify the complete recovery copy before changing the card.
h=hashlib.sha256(); total=0
with gzip.open(backup,'rb') as f:
 while b:=f.read(4*1024*1024): h.update(b); total+=len(b)
assert total==2008023040 and h.hexdigest()==meta['sha256_uncompressed'],'Recovery copy verification failed'
bus=dbus.SystemBus(); obj=bus.get_object('org.freedesktop.UDisks2','/org/freedesktop/UDisks2/block_devices/sdb')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
b=props.GetAll('org.freedesktop.UDisks2.Block')
assert int(b['Size'])==2008023040 and not b['ReadOnly']
drive=bus.get_object('org.freedesktop.UDisks2',b['Drive'])
dp=dbus.Interface(drive,'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.UDisks2.Drive')
assert str(dp['Serial'])=='121220160204' and str(dp['ConnectionBus'])=='usb'
# Refuse to overwrite a mounted partition.
manager=dbus.Interface(bus.get_object('org.freedesktop.UDisks2','/org/freedesktop/UDisks2'),'org.freedesktop.DBus.ObjectManager')
for path,ifs in manager.GetManagedObjects().items():
 part=ifs.get('org.freedesktop.UDisks2.Partition',{})
 if str(part.get('Table',''))==str(obj.object_path):
  assert not ifs.get('org.freedesktop.UDisks2.Filesystem',{}).get('MountPoints',[]),'Card is mounted'
block=dbus.Interface(obj,'org.freedesktop.UDisks2.Block')
fd=block.OpenForRestore({},timeout=600).take(); expected=hashlib.sha256()
written=0
with image.open('rb') as src,os.fdopen(fd,'wb',buffering=0) as dst:
 while chunk:=src.read(4*1024*1024):
  expected.update(chunk)
  view=memoryview(chunk)
  while view:
   n=dst.write(view)
   assert n and n>0
   view=view[n:]
  written+=len(chunk)
  if written%(64*1024*1024)==0: print('write',written,'/',size,flush=True)
 os.fsync(dst.fileno())
 os.posix_fadvise(dst.fileno(),0,size,os.POSIX_FADV_DONTNEED)
fd=block.OpenForBackup({},timeout=600).take(); actual=hashlib.sha256(); left=size
with os.fdopen(fd,'rb',buffering=0) as src:
 os.posix_fadvise(src.fileno(),0,size,os.POSIX_FADV_DONTNEED)
 while left:
  chunk=src.read(min(left,4*1024*1024)); assert chunk
  actual.update(chunk); left-=len(chunk)
  if (size-left)%(64*1024*1024)==0: print('readback',size-left,'/',size,flush=True)
assert expected.digest()==actual.digest(),'SD readback mismatch'
block.Rescan({})
report={'image':str(image),'bytes':size,'serial':'121220160204','sha256':actual.hexdigest(),'readback_verified':True}
(root/'logs/flash-verified.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
