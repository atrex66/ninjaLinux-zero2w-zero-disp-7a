#!/usr/bin/env python3
"""The original LinuxCNC HALShow, with an SSH snapshot-backed HAL command."""
import argparse,hashlib,json,os,queue,re,shlex,subprocess,sys,threading,time,tkinter as tk
from pathlib import Path
from tkinter import ttk,messagebox,filedialog
from model import Catalog
ROOT=Path(__file__).resolve().parent
DEFAULT_KEY=Path.home()/'.ssh/id_ed25519'
KNOWN=ROOT.parents[3]/'logs/ssh_known_hosts_generic'
class Connection:
 def __init__(self,profile):
  self.profile=profile;self.catalog=Catalog({});self.last=0.;self.error='Kapcsolódás…';self.count=0
  self.lock=threading.Lock();self.stopping=threading.Event();self.process=None
  self.thread=threading.Thread(target=self.run,daemon=True)
 def start(self):self.thread.start()
 def online(self):return time.monotonic()-self.last<max(3.,self.profile['interval']*4) and not self.error
 def run(self):
  p=self.profile
  args=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-p',str(p['port']),'-l',p['user']]
  if p['identity']:args+=['-i',p['identity']]
  if p['known_hosts']:args+=['-o','UserKnownHostsFile='+p['known_hosts']]
  command='/usr/bin/python3 /opt/automation-hal/libexec/halshow_agent.py --interval '+str(p['interval'])
  while not self.stopping.is_set():
   try:
    self.process=subprocess.Popen([*args,p['host'],command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    for line in self.process.stdout:
     if self.stopping.is_set():break
     if len(line)>2_000_000:raise ValueError('Túl nagy diagnosztikai válasz')
     frame=json.loads(line)
     if frame.get('protocol')!=1:raise ValueError('Nem támogatott diagnosztikai protokoll')
     if frame.get('ok'):
      catalog=Catalog(frame['tables'])
      with self.lock:self.catalog=catalog;self.last=time.monotonic();self.error='';self.count+=1
     else:self.error=frame.get('error','A távoli HAL nem érhető el')
    stderr=self.process.stderr.read().strip()
    if not self.stopping.is_set():self.error=stderr or 'Az SSH-kapcsolat megszakadt; újracsatlakozás…'
   except (OSError,ValueError) as e:self.error=str(e)
   finally:
    if self.process and self.process.poll() is None:self.process.terminate()
   self.stopping.wait(2)
 def stop(self):
  self.stopping.set()
  if self.process and self.process.poll() is None:self.process.terminate()
  self.thread.join(timeout=2)
class Application:
 def __init__(self,args):
  self.args=args;self.root=tk.Tk();self.root.withdraw();self.client=None;self.loaded=False;self.closing=False
  self.state=ROOT/'state';self.state.mkdir(exist_ok=True)
  self.profile=dict(host=args.host or '192.168.0.234',user=args.user,port=args.port,identity=args.identity,
                    known_hosts=args.known_hosts,interval=args.interval)
  self.root.tk.createcommand('exit',self.close)
  self.root.tk.createcommand('_remote_hal',self.hal)
  self.root.tk.createcommand('_remote_online',lambda:bool(self.client and self.client.online()))
  if args.host:self.connect(self.profile)
  else:self.dialog()
 def dialog(self):
  dialog=tk.Toplevel(self.root);self.dialog_window=dialog;dialog.title('Távoli eredeti HALShow');dialog.resizable(False,False)
  frame=ttk.Frame(dialog,padding=20);frame.grid();self.fields={}
  for row,(key,label) in enumerate((('host','IP-cím / gépnév'),('user','SSH-felhasználó'),('port','SSH-port'),('identity','SSH-kulcs'),('known_hosts','Ismert gépkulcsok'))):
   ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=5)
   var=tk.StringVar(value=str(self.profile[key]));self.fields[key]=var
   ttk.Entry(frame,textvariable=var,width=54).grid(row=row,column=1,pady=5)
   if key in ('identity','known_hosts'):
    ttk.Button(frame,text='…',width=3,command=lambda k=key:self.browse(k)).grid(row=row,column=2)
  self.connect_status=tk.StringVar(value='Csak olvasás · a távoli saját HAL figyelése SSH-n keresztül')
  ttk.Label(frame,textvariable=self.connect_status,wraplength=540).grid(row=5,column=0,columnspan=3,sticky='w',pady=12)
  self.connect_button=ttk.Button(frame,text='Kapcsolódás',command=self.submit);self.connect_button.grid(row=6,column=1,sticky='e')
  dialog.protocol('WM_DELETE_WINDOW',self.close);dialog.bind('<Return>',lambda e:self.submit())
 def browse(self,key):
  path=filedialog.askopenfilename(parent=self.dialog_window)
  if path:self.fields[key].set(path)
 def submit(self):
  p={k:v.get().strip() for k,v in self.fields.items()}
  try:p['port']=int(p['port']);self.connect(p)
  except ValueError as e:self.connect_status.set(str(e))
 def connect(self,p):
  if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:\-]*',p['host']):raise ValueError('Érvényes IP-cím vagy gépnév szükséges')
  if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.\-]*',p['user']):raise ValueError('Érvényes SSH-felhasználó szükséges')
  if not 1<=p['port']<=65535:raise ValueError('Érvénytelen SSH-port')
  p['interval']=self.args.interval
  if self.client:self.client.stop()
  self.profile=p;self.client=Connection(p);self.client.start()
  if hasattr(self,'connect_status'):self.connect_status.set('Kapcsolódás…')
  self.root.after(100,self.wait_first)
 def wait_first(self):
  if self.closing:return
  if self.client.online():self.load_original();return
  if hasattr(self,'connect_status'):self.connect_status.set(self.client.error)
  elif self.client.error:self.root.deiconify();self.root.title('Távoli HALShow – kapcsolódás');self.show_start_error()
  self.root.after(300,self.wait_first)
 def show_start_error(self):
  if not hasattr(self,'start_status'):
   self.start_status=tk.StringVar();ttk.Label(self.root,textvariable=self.start_status,padding=20,wraplength=700).pack()
  self.start_status.set(self.client.error+'\nA kapcsolat automatikusan újrapróbálkozik.')
 def hal(self,*args):
  try:
   if not self.client:raise ValueError('Nincs távoli kapcsolat')
   with self.client.lock:return ('ok',self.client.catalog.command(args))
  except Exception as e:return ('error',str(e))
 def load_original(self):
  if self.loaded:return
  self.loaded=True
  if hasattr(self,'dialog_window'):self.dialog_window.destroy()
  if hasattr(self,'start_status'):
   for widget in self.root.winfo_children():widget.destroy()
  profile_id=hashlib.sha256((self.profile['host']+':'+str(self.profile['port'])+'/'+self.profile['user']).encode()).hexdigest()[:16]
  prefs=self.state/profile_id;prefs.mkdir(exist_ok=True);os.environ['CONFIG_DIR']=str(prefs)
  self.root.tk.setvar('argv',());self.root.tk.setvar('argc',0)
  original=(ROOT/'vendor/bin/halshow.tcl').read_text()
  # A single behavioral patch: keep the original watch UI, omit write controls.
  needle='    $::cisp create text $::col1_width'
  if original.count(needle)!=1:raise RuntimeError('Ismeretlen eredeti HALShow-verzió')
  # source must retain the original script directory for its relative bootstrap.
  self.root.tk.eval('trace add execution proc leave _remote_proc_created')
  self.root.after(0,self.root.deiconify)
  self.root.tk.call('source',str(ROOT/'vendor/bin/halshow.tcl'))
  self.root.tk.eval('trace remove execution proc leave _remote_proc_created')
  self.root.tk.eval('''
    rename refreshItem _remote_original_refreshItem
    proc refreshItem {cnum vartype varname} {
      if {[_remote_online] && ![catch {_remote_original_refreshItem $cnum $vartype $varname}]} {return}
      if {[llength [$::cisp find withtag oval$cnum]]} {$::cisp itemconfigure oval$cnum -fill gray60}
      if {[llength [$::cisp find withtag text$cnum]]} {$::cisp itemconfigure text$cnum -text "—"}
    }
    set ::watchInterval 250
  ''')
  self.root.tk.call('.f2.b.label','configure','-text','HAL lekérdezés:')
  self.root.tk.call('setStatusbar','Csak olvasás: show, list, getp, gets, ptype, stype')
  bar=ttk.Frame(self.root,padding=(6,4));bar.pack(side='top',fill='x',before='.main')
  self.banner=tk.StringVar();ttk.Label(bar,textvariable=self.banner).pack(side='left')
  ttk.Label(bar,text='Csak olvasás').pack(side='right')
  self.tick()
  if self.args.smoke:
   for name in ('pin+stepgen-ninja.0.encoder.0.position','pin+stepgen-ninja.0.inputs.0','sig+dro-position-x','param+dro-thread.tmax'):
    self.root.tk.call('watchHAL',name)
   self.root.tk.call(self.root.tk.getvar('nb'),'raise','pw')
   self.root.after(1800,self.smoke)
 def tick(self):
  if self.closing:return
  online=self.client.online();age=time.monotonic()-self.client.last
  text=f'{self.profile["host"]} · '+(f'Online · {len(self.client.catalog.rows["pin"])} pin · {self.profile["interval"]*1000:.0f} ms' if online else 'Nincs friss adat · '+self.client.error[:120])
  self.banner.set(text);self.root.title('HALShow · '+self.profile['host']+(' · Online' if online else ' · Offline'))
  self.root.after(250,self.tick)
 def smoke(self):
  try:
   assert self.client.online()
   catalog=self.client.catalog;assert len(catalog.rows['pin'])>50
   assert int(self.root.tk.getvar('watchlist_len'))==4
   assert catalog.command(('getp','stepgen-ninja.0.connected'))=='TRUE'
   try:catalog.command(('setp','stepgen-ninja.0.outputs.0','TRUE'));raise AssertionError('Write accepted')
   except ValueError:pass
   self.root.update_idletasks()
   if self.args.screenshot:
    subprocess.run(['import','-window',str(self.root.winfo_id()),self.args.screenshot],check=True,timeout=5)
   report={'original_halshow':True,'remote_host':self.profile['host'],'received_snapshots':self.client.count,
           'objects':{k:len(v) for k,v in catalog.rows.items()},'watch_count':4,'write_rejected':True}
   if self.args.report:Path(self.args.report).write_text(json.dumps(report,indent=2))
   print(json.dumps(report),flush=True)
  except Exception as e:
   print('SMOKE FAILED:',repr(e),file=sys.stderr);self.args.failure=True
  finally:self.close()
 def close(self,*args):
  if self.closing:return ''
  self.closing=True
  if self.loaded:
   try:self.root.tk.call('saveIni')
   except tk.TclError:pass
  if self.client:self.client.stop()
  try:self.root.destroy()
  except tk.TclError:pass
  return ''
 def run(self):
  self.root.tk.eval('''
   proc _remote_proc_created {command code result op} {
     if {[lindex $command 1] ne "watchHAL"} {return}
     set body [info body watchHAL]
     set needle {    $::cisp create text $::col1_width}
     set body [string map [list $needle "    set writable 0\\n$needle"] $body]
     # Defining the replacement would retrigger this trace: temporarily remove it.
     trace remove execution proc leave _remote_proc_created
     proc watchHAL {which} $body
     trace add execution proc leave _remote_proc_created
   }
  ''')
  try:self.root.mainloop()
  finally:self.close()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host');p.add_argument('--user',default='root');p.add_argument('--port',type=int,default=22)
 p.add_argument('--identity',default=str(DEFAULT_KEY));p.add_argument('--known-hosts',default=str(KNOWN) if KNOWN.exists() else '')
 p.add_argument('--interval',type=float,default=.5);p.add_argument('--smoke',action='store_true');p.add_argument('--screenshot');p.add_argument('--report')
 a=p.parse_args();a.failure=False;a.interval=max(.25,min(10,a.interval));app=Application(a);app.run();return 1 if a.failure else 0
if __name__=='__main__':sys.exit(main())
