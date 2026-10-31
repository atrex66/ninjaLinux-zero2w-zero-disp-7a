#!/usr/bin/env python3
"""Read-only Automation HAL snapshot stream over an authenticated SSH session."""
import argparse,json,os,pwd,signal,subprocess,sys,time
from pathlib import Path
KINDS=('comp','pin','param','sig','funct','thread')
def main():
 p=argparse.ArgumentParser();p.add_argument('--interval',type=float,default=.5);p.add_argument('--once',action='store_true')
 p.add_argument('--run-as',default='ahal');p.add_argument('--prefix',default='/opt/automation-hal');a=p.parse_args()
 interval=max(.25,min(10,a.interval))
 if os.geteuid()==0:
  user=pwd.getpwnam(a.run_as);os.setgroups([]);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 if hasattr(os,'sched_getaffinity'):
  cpus=os.sched_getaffinity(0)&{0,1}
  if cpus:os.sched_setaffinity(0,cpus)
 runtime=Path('/tmp')/f'automation-hal-{os.getuid()}'/'control.sock'
 env=os.environ.copy();env['RTAPI_FIFO_PATH']=str(runtime);env['HAL_RTMOD_DIR']=a.prefix+'/rtlib';env['LC_ALL']='C'
 executable=a.prefix+'/bin/halcmd';metadata={};meta_time=0;sequence=0
 signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
 try:
  while True:
   start=time.monotonic();sequence+=1
   try:
    if not runtime.is_socket():raise RuntimeError('Nincs futó saját HAL ezen a felhasználón')
    tables={};full=not metadata or start-meta_time>=3
    for kind in KINDS:
     if kind in ('comp','funct','thread') and not full:tables[kind]=metadata[kind];continue
     result=subprocess.run([executable,'show',kind],env=env,capture_output=True,text=True,timeout=2)
     if result.returncode:raise RuntimeError(result.stderr.strip() or f'halcmd show {kind}: {result.returncode}')
     tables[kind]=result.stdout
    if full:metadata={k:tables[k] for k in ('comp','funct','thread')};meta_time=start
    frame=dict(protocol=1,ok=True,sequence=sequence,unix_time=time.time(),interval=interval,uid=os.getuid(),tables=tables)
   except (OSError,RuntimeError,subprocess.TimeoutExpired) as e:
    metadata={};frame=dict(protocol=1,ok=False,error=str(e),unix_time=time.time())
   print(json.dumps(frame,separators=(',',':')),flush=True)
   if a.once:break
   time.sleep(max(.02,interval-(time.monotonic()-start)))
 except (BrokenPipeError,KeyboardInterrupt):pass
if __name__=='__main__':main()
