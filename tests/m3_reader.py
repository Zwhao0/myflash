# ADAPTATION: CPU crash-recovery tests; not GPU evidence.
import sys,json,os,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.reader import recover_tail
from m2_ring import RingTests
class RecoveryTests(RingTests):
 def test_tail_and_replay(self):
  name,h=self.create();r=self.reader(name)
  for x in [7,8,9]:self.lib.flash_test_write(h,x,2)
  one=r.read();two=r.read(acknowledge=False);context=r.snapshot()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/"events.ndjson";complete=(json.dumps(one)+"\n").encode()
   p.write_bytes(complete+b'{"publish_seq":2,"count":')
   self.assertEqual(recover_tail(p,context),[one]);self.assertEqual(p.read_bytes(),complete)
   r.close();r=self.reader(name);self.assertEqual(r.read()["count"],8);self.assertEqual(r.read()["count"],9)
 def test_middle_corruption_and_confirmed_loss(self):
  name,h=self.create();r=self.reader(name)
  for x in [7,8,9]:self.lib.flash_test_write(h,x,2)
  rows=[r.read(),r.read(),r.read()];context=r.snapshot()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/"events.ndjson"
   for data in [json.dumps(rows[0])+"\nBROKEN\n"+json.dumps(rows[2])+"\n",json.dumps(rows[0])+"\n",json.dumps(rows[0])+"\n"+json.dumps(rows[1])]:
    p.write_text(data)
    with self.assertRaises((ValueError,KeyError)):recover_tail(p,context)
    self.assertEqual(p.read_text(),data)
   rows[1]["count"]=999;p.write_text("".join(json.dumps(x)+"\n" for x in rows))
   with self.assertRaises(ValueError):recover_tail(p,context)
 def test_control_protocol(self):
  name,h=self.create();r=self.reader(name)
  for state,epoch in [(2,1),(1,0)]:
   with self.assertRaises(OSError):r.request(state,epoch)
  r.request(1,1);self.assertEqual(r.snapshot()["requested_control"],3)
  r.request(0,1)
  with self.assertRaises(OSError):r.request(1,1)
  r.request(1,2)
  with self.assertRaises(OSError):r.request(0,1)
if __name__=="__main__":unittest.main(verbosity=2)
