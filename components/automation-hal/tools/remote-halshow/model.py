"""Original HALShow's read API, served entirely from remote snapshots."""
import fnmatch,re,time
KINDS=('comp','pin','param','sig','funct','thread')
TYPE=r'(bit|float|s32|u32|s64|u64|port)'
PATTERNS={
 'pin':re.compile(r'^\s*\d+\s+'+TYPE+r'\s+(?:IN|OUT|I/O)\s+(\S+)\s+(\S+)'),
 'param':re.compile(r'^\s*\d+\s+'+TYPE+r'\s+(?:RO|RW)\s+(\S+)\s+(\S+)'),
 'sig':re.compile(r'^'+TYPE+r'\s+(\S+)\s+(\S+)'),
 'comp':re.compile(r'^\s*\d+\s+(?:User|RT)\s+(\S+)'),
 'funct':re.compile(r'^\s*\d+\s+\S+\s+\S+\s+(?:YES|NO)\s+\d+\s+(\S+)'),
 'thread':re.compile(r'^\s*\d+\s+(?:YES|NO)\s+(\S+)\s+\(')}
class Catalog:
 def __init__(self,tables):
  self.tables=tables;self.rows={};self.headers={}
  for kind in KINDS:
   rows={};header=[];current=None
   for line in tables.get(kind,'').splitlines(keepends=True):
    match=PATTERNS[kind].match(line)
    if match:
     fields=match.groups();name=fields[-1]
     if not re.fullmatch(r'[A-Za-z0-9_.:-]+',name):current=None;continue
     current={'name':name,'raw':line}
     if kind in ('pin','param','sig'):current.update(type=fields[0],value=fields[1])
     rows[name]=current
    elif current is not None:current['raw']+=line
    else:header.append(line)
   self.rows[kind]=rows;self.headers[kind]=''.join(header)
 @staticmethod
 def matches(name,patterns):return not patterns or any(not p or name.startswith(p) or fnmatch.fnmatchcase(name,p) for p in patterns)
 def command(self,args):
  if not args:raise ValueError('Olvasás: show, list, getp, gets, ptype, stype')
  op,*rest=args
  if op in ('show','list'):
   kind=rest[0] if rest else 'all';patterns=rest[1:]
   if kind not in (*KINDS,'all'):raise ValueError('Ismeretlen HAL objektumtípus: '+kind)
   kinds=KINDS if kind=='all' else (kind,)
   if op=='list':return tuple(name for k in kinds for name in self.rows[k] if self.matches(name,patterns))
   return ''.join(self.headers[k]+''.join(r['raw'] for name,r in self.rows[k].items() if self.matches(name,patterns)) for k in kinds)
  if op in ('getp','ptype','gets','stype') and len(rest)==1:
   kinds=('sig',) if op in ('gets','stype') else ('pin','param')
   for k in kinds:
    if rest[0] in self.rows[k]:return self.rows[k][rest[0]]['type' if op in ('ptype','stype') else 'value']
   raise ValueError('Nem található: '+rest[0])
  raise ValueError('Csak olvasó kapcsolat: ez a parancs nincs engedélyezve')
