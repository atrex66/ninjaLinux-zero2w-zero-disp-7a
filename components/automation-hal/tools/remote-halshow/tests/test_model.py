import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import Catalog
class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.c=Catalog({'pin':'Component Pins:\nOwner Type Dir Value Name\n 10 bit OUT TRUE axis.ready ==> ready\n 10 float IN -2.5 axis.pos\n 10 bit IN FALSE axis.enable\n',
    'sig':'Signals:\nType Value Name (linked to)\nbit TRUE ready\n <== axis.ready\n ==> control.ready\nfloat -2.5 position\n <== scale.position\n',
    'param':'Parameters:\nOwner Type Dir Value Name\n 7 s32 RW 99 servo.tmax\n',
    'comp':'Loaded HAL Components:\nID Type Name PID State\n 10 RT axis ready\n',
    'funct':'Exported Functions:\nOwner CodeAddr Arg FP Users Name\n 10 abcd abcd YES 1 axis.update\n',
    'thread':'Realtime Threads:\nPeriod FP Name (Time,Max-Time)\n 1000000 YES servo ( 5, 99 )\n 1 axis.update\n'})
 def test_type_value_and_pin_parameter_lookup(self):
  self.assertEqual(self.c.command(('ptype','axis.ready')),'bit')
  self.assertEqual(self.c.command(('getp','axis.ready')),'TRUE')
  self.assertEqual(self.c.command(('getp','axis.pos')),'-2.5')
  self.assertEqual(self.c.command(('getp','servo.tmax')),'99')
 def test_signal_connections_stay_with_the_selected_signal(self):
  text=self.c.command(('show','sig','ready'))
  self.assertIn('<== axis.ready',text);self.assertIn('==> control.ready',text)
  self.assertNotIn('scale.position',text)
 def test_prefix_and_wildcard_match_halcmd(self):
  self.assertEqual(len(self.c.command(('list','pin','axis.'))),3)
  self.assertEqual(self.c.command(('list','pin','*.enable')),('axis.enable',))
 def test_all_object_groups_are_supported(self):
  for kind in ('comp','pin','param','sig','funct','thread'):self.assertTrue(self.c.command(('list',kind)))
  self.assertEqual(self.c.command(('list','thread')),('servo',))
  self.assertIn('axis.update',self.c.command(('show','thread','servo')))
 def test_writes_and_process_commands_are_rejected(self):
  for op in ('setp','sets','net','unlinkp','start','stop','loadrt','unload','source','loadusr'):
   with self.assertRaises(ValueError):self.c.command((op,'axis.enable','TRUE'))
 def test_removed_pin_is_an_error_not_a_stale_value(self):
  with self.assertRaises(ValueError):self.c.command(('getp','missing.pin'))
if __name__=='__main__':unittest.main()
