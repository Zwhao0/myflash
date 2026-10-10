# ADAPTATION: read-only cross-node checks of privacy-whitelisted evidence.
import csv, hashlib, json, math, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/m3'
def load(n):return json.loads((D/n).read_text())
def rows(n):return list(csv.DictReader((D/n).open()))
def main():
 post=[load(f'postflight-node-{i}.json') for i in range(2)]
 assert all(p['status']=='PASS' and all(p[k]==0 for k in ('remaining_own_pids','own_gpu_pids','remaining_run_shm')) and p['command_exit_codes']==[0,0,0] for p in post)
 assert post[0]['probe_sha256']==post[1]['probe_sha256']
 assert post[0]['source_hashes']==post[1]['source_hashes']
 for f,h in {**load('baseline-hashes.json')['files'],**post[0]['source_hashes']}.items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
 validation=[load(f'final-validation-node-{i}.json') for i in range(2)]
 for v in validation:
  assert v['status']=='PASS'
  for r in v['results']:
   assert r['status']=='PASS' and r['loss']==0
   assert r['complete_profile']==(not r['run_id'].startswith('m3e-group'))
 samples=sum((rows(f'samples-node-{i}.csv') for i in range(2)),[])
 assert len(samples)==520
 cold=[r for r in samples if r['warmup']=='False'];assert len(cold)==400
 distributions=sum((rows(f'distributions-node-{i}.csv') for i in range(2)),[]);assert len(distributions)==20
 for d in distributions:
  values=[float(s['duration_us']) for s in cold if all(s[k]==d[k] for k in ('run_id','rank','case'))]
  assert len(values)==int(d['samples'])==20
  for k,v in [('median_us',statistics.median(values)),('mean_us',statistics.mean(values)),('min_us',min(values)),('max_us',max(values))]:assert math.isclose(float(d[k]),v,rel_tol=1e-12,abs_tol=1e-9),(d,k)
 profile=sum((rows(f'profile-samples-node-{i}.csv') for i in range(2)),[])
 rank_sets={}
 for r in profile:
  if r['comm_id_hash']:
   rank_sets.setdefault((r['run_id'],r['comm_id_hash']),set()).add(int(r['rank']))
  if r['timing_status']=='VALID':assert math.isfinite(float(r['duration_us'])) and float(r['duration_us'])>0
  else:assert r['duration_us']==''
 for run in ('m3d-roce-01','m3f-allreduce-01','m3f-allreduce-02','m3f-ddp-01','m3f-ddp-02'):
  sets=[v for (rid,h),v in rank_sets.items() if rid==run]
  assert sets and all(s==set(range(2 if run=='m3d-roce-01' else 16)) for s in sets),(run,sets)
 for run,expected in [('m3f-allreduce-02',192),('m3f-ddp-02',320),('m3e-group-02',80)]:assert sum(r['run_id']==run and r['timing_status']=='VALID' for r in profile)==expected
 result=dict(status='PASS',raw_samples=520,nonwarmup_samples=400,distributions=20,profile_rows=len(profile),cross_node_rank_sets='complete',baseline_hashes='unchanged',group_complete_profile=False,probe_sha256=post[0]['probe_sha256'])
 (D/'public-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
