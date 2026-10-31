"""Opt-in read-only integration check against an already-running private HAL."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import Connection,KNOWN,DEFAULT_KEY
p=dict(host='192.168.0.234',user='root',port=22,identity=str(DEFAULT_KEY),known_hosts=str(KNOWN),interval=.5)
c=Connection(p)
def wait(predicate,timeout=12):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.05)
 raise RuntimeError(c.error)
try:
 c.start();wait(c.online);initial=c.count
 assert c.catalog.command(('getp','stepgen-ninja.0.connected'))=='TRUE'
 c.process.terminate() # Only our SSH client; never touch the HAL owner/runtime.
 wait(lambda:not c.online());wait(lambda:c.online() and c.count>initial)
 print(json.dumps(dict(connected=True,snapshots=c.count,recovered_after_own_ssh_disconnect=True,objects={k:len(v) for k,v in c.catalog.rows.items()})))
finally:c.stop()
