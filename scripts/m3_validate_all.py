# ADAPTATION: final read-only validation over immutable raw runs; no re-labeling or edits.
import argparse,datetime,json,socket,subprocess
from pathlib import Path
from m3_verify import verify
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--node-rank',type=int,required=True);a=p.parse_args()
 out=ROOT/'runs'/('m3-validation-node-'+str(a.node_rank)+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir();results=[]
 for run,mode,world in [('m3abc-local-01','mechanism',2),('m3d-roce-01','mechanism',2),('m3e-group-01','group',2),('m3e-group-02','group',2),('m3f-allreduce-01','allreduce',16),('m3f-ddp-01','ddp',16),('m3f-allreduce-02','allreduce',16),('m3f-ddp-02','ddp',16)]:
  d=ROOT/'runs'/run/f'node-{a.node_rank}'
  if d.exists():results.append(dict(run_id=run,**verify(d,world,mode,True)))
 result=dict(status='PASS',node_rank=a.node_rank,results=results,raw_evidence_dir=str(out.relative_to(ROOT)));(out/'validation.json').write_text(json.dumps(result,indent=2));(ROOT/f'docs/m3/final-validation-node-{a.node_rank}.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status='PASS',runs=len(results))))
if __name__=='__main__':main()
