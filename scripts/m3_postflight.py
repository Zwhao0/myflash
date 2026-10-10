# ADAPTATION: observe only this M3 run list and rank PIDs; no process termination or broad cleanup.
import argparse,datetime,hashlib,json,os,socket,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--node-rank',type=int,required=True);a=p.parse_args()
 out=ROOT/'runs'/('m3-postflight-node-'+str(a.node_rank)+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
 names=['m3abc-local-01','m3d-roce-01','m3e-group-01','m3e-group-02','m3f-allreduce-01','m3f-ddp-01','m3f-allreduce-02','m3f-ddp-02','m3d-monitor-local-01','m3d-monitor-cross-01','m3d-monitor-allreduce-01','m3d-monitor-ddp-01','m3d-monitor-lifecycle-01','m3d-native-01']
 all_pids=[];remaining=[];shm=[];proof=[]
 for run in names:
  d=ROOT/'runs'/run/f'node-{a.node_rank}'
  if not d.exists():continue
  for path in d.glob('rank-*.json'):all_pids.append(json.loads(path.read_text())['pid'])
  shm.extend(str(p) for p in Path('/dev/shm').glob(f'flash_m2_{run}_node-{a.node_rank}_*'))
  if (d/'probe/reader-result.json').exists():
   s=json.loads((d/'probe/reader-result.json').read_text())['snapshots'];assert all(x['state']==0 and x['closed']==1 and x['write_pos']==x['read_pos'] and x['attempts']==x['write_pos'] and all(x[k]==0 for k in ['errors','dropped_full','dropped_lock','bad_records','poisoned']) for x in s)
   proof.append(dict(run_id=run,events=sum(x['write_pos'] for x in s)))
 for pid in all_pids:
  try:os.kill(pid,0);remaining.append(pid)
  except ProcessLookupError:pass
 commands=[['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader,nounits'],['nvidia-smi','--query-gpu=index,name,driver_version,memory.used,utilization.gpu','--format=csv,noheader'],['python3','-c',"import json,hashlib; from pathlib import Path; m=json.loads(Path('docs/m3/baseline-hashes.json').read_text()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in m['files'].items())"]]
 records=[];gpu_own=[]
 for index,cmd in enumerate(commands):
  r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);(out/f'{index}.log').write_text(r.stdout+r.stderr);records.append(dict(command=cmd,exit_code=r.returncode,log=str(out/f'{index}.log')));assert r.returncode==0
  if index==0:gpu_own=[line for line in r.stdout.splitlines() if int(line.split(',')[0]) in all_pids]
  if index==2:assert not r.stdout
 result=dict(host=socket.gethostname(),node_rank=a.node_rank,status='PASS' if not remaining and not shm and not gpu_own else 'FAIL',commands=records,rank_pids_checked=len(all_pids),remaining_own_pids=remaining,own_gpu_pids=gpu_own,remaining_run_shm=shm,proof=proof,probe_sha256=hashlib.sha256((ROOT/'build/libflash_probe.so').read_bytes()).hexdigest(),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'native').glob('*.cpp'))+list((ROOT/'native').glob('*.hpp'))+list((ROOT/'flash').glob('*.py'))})
 (out/'manifest.json').write_text(json.dumps(result,indent=2));assert result['status']=='PASS'
 public={k:result[k] for k in ['node_rank','status','rank_pids_checked','probe_sha256','source_hashes','proof']};public.update(remaining_own_pids=0,own_gpu_pids=0,remaining_run_shm=0,raw_evidence_dir=str(out.relative_to(ROOT)),command_exit_codes=[x['exit_code'] for x in records])
 (ROOT/f'docs/m3/postflight-node-{a.node_rank}.json').write_text(json.dumps(public,indent=2));print(json.dumps(public))
if __name__=='__main__':main()
