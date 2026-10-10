# ADAPTATION: verifier must reject incomplete/failed profiling evidence; CPU fixtures from private run.
import copy,json,sys,unittest,tempfile,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from m3_verify import verify
class EvidenceTests(unittest.TestCase):
 def test_reject_missing_rank_loss_timeout_and_invalid_duration(self):
  original=ROOT/'runs/m3abc-local-01/node-0'
  # Existing verified actual run remains immutable; all changes are private CPU fixture copies.
  with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
   d=Path(tmp)/'fixture';shutil.copytree(original,d)
   verify(d,2,'mechanism',True)
   rank=d/'rank-1.json';saved=rank.read_bytes();rank.unlink()
   with self.assertRaises(AssertionError):verify(d,2,'mechanism',True)
   rank.write_bytes(saved)
   m=d/'manifest.json';saved=m.read_bytes();v=json.loads(saved);v['exit_code']=124;m.write_text(json.dumps(v))
   with self.assertRaises(AssertionError):verify(d,2,'mechanism',True)
   m.write_bytes(saved)
   p=d/'probe/reader-result.json';saved=p.read_bytes();v=json.loads(saved);v['snapshots'][0]['dropped_full']=1;p.write_text(json.dumps(v))
   with self.assertRaises(AssertionError):verify(d,2,'mechanism',True)
   p.write_bytes(saved)
   p=next((d/'probe').glob('*.ndjson'));saved=p.read_bytes();lines=p.read_text().splitlines();v=json.loads(lines[3]);v['duration_us']=0;lines[3]=json.dumps(v);p.write_text('\n'.join(lines)+'\n')
   with self.assertRaises(AssertionError):verify(d,2,'mechanism',True)
   p.write_bytes(saved)
   # A present rank that never enters epoch2 must not become a complete profiling success.
   rows=[json.loads(line) for line in saved.decode().splitlines()]
   for v in rows:
    if v['state']==1 and v['profile_epoch']==2:
     v['state']=0
     for key in ['duration_us','timing_scope','timing_status','device','sync_block_ns','cuda_results']:v.pop(key,None)
     v.pop('record_digest');v['record_digest']=hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   p.write_text(''.join(json.dumps(v)+'\n' for v in rows))
   with self.assertRaises(AssertionError):verify(d,2,'mechanism',True)
   p.write_bytes(saved)
if __name__=='__main__':unittest.main(verbosity=2)
