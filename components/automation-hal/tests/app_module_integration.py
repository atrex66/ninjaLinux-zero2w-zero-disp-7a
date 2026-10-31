#!/usr/bin/python3
"""Run only through tools/test_app_modules.sh in a disposable bwrap namespace."""
import os,subprocess,time,signal,shutil
from pathlib import Path
prefix=Path('/opt/automation-hal');app=Path('/data/cartridges/test-app');rtlib=app/'rtlib';rtlib.mkdir(parents=True)
comp=rtlib/'cartridge_probe.comp';comp.write_text('component cartridge_probe;\npin out u32 ticks;\nfunction _;\nlicense "GPL";\n;;\nFUNCTION(_) { ticks++; }\n')
subprocess.run([str(prefix/'bin/ahal'),'compile','--compile',str(comp)],cwd=rtlib,check=True,timeout=30)
assert (rtlib/'cartridge_probe.so').is_file()
# A packaged module must beat an app file with the same name, even if corrupt.
(rtlib/'threads.so').write_text('must never be loaded')
config=app/'main.hal';config.write_text('loadrt threads name1=app-thread period1=1000000\nloadrt cartridge_probe count=1\naddf cartridge-probe.0 app-thread\nstart\n')
empty=Path('/data/apps/empty/rtlib');empty.mkdir(parents=True)
# Ambient variables must not grant extra module paths.
env=os.environ.copy();env['AHAL_RTLIB_PATH']=str(rtlib)
failed=subprocess.run([str(prefix/'bin/ahal'),'run','--mode','sim',str(config)],env=env,capture_output=True,text=True,timeout=10)
assert failed.returncode != 0, failed.stdout + failed.stderr
assert 'Module not found' in failed.stdout + failed.stderr, failed.stdout + failed.stderr

def cmd(*args,ok=True):
 r=subprocess.run([str(prefix/'bin/ahal'),'cmd',*args],capture_output=True,text=True,timeout=5)
 assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
 return r.stdout.strip()
with (app/'run.log').open('w+') as log:
 p=subprocess.Popen([str(prefix/'bin/ahal'),'run','--mode','sim','--rtlib',str(empty),'--rtlib',str(rtlib),str(config)],stdout=log,stderr=log)
 try:
  for _ in range(150):
   log.flush();text=(app/'run.log').read_text()
   if 'configuration loaded' in text:break
   assert p.poll() is None,text
   time.sleep(.04)
  else:raise AssertionError((app/'run.log').read_text())
  time.sleep(.05);ticks=int(cmd('getp','cartridge-probe.0.ticks'));assert ticks>0,ticks
  cmd('loadrt','/data/cartridges/test-app/rtlib/cartridge_probe.so',ok=False)
  (rtlib/'bad_module.so').symlink_to(rtlib/'cartridge_probe.so')
  cmd('loadrt','bad_module',ok=False)
  print('PASS: real HAL + SDK app module from /data/cartridges, ticks=',ticks,', explicit paths, system priority, absolute names and symlinks rejected')
 finally:
  p.terminate()
  p.wait(timeout=10)
