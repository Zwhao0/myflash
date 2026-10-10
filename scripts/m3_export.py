# ADAPTATION: independent evaluator exports a fixed privacy whitelist; raw evidence stays on servers.
import argparse,csv,hashlib,json,math,re,statistics,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def public_command(command,node):
 out=[x.replace(str(ROOT),'<project>') for x in command]
 for i,x in enumerate(out):
  if i and out[i-1]=='--gpus':out[i]=f'<approved_GPU_UUID_list_node_{node}>'
  elif i and out[i-1]=='--master-addr' and x!='127.0.0.1':out[i]='<gpu01_master_address>'
 return out
def distribution(values):
 s=sorted(values)
 def q(p):
  pos=(len(s)-1)*p;lo=math.floor(pos);hi=math.ceil(pos);return s[lo]+(s[hi]-s[lo])*(pos-lo)
 return dict(samples=len(s),min_us=s[0],p10_us=q(.1),median_us=statistics.median(s),mean_us=statistics.mean(s),p90_us=q(.9),max_us=s[-1],std_us=statistics.pstdev(s))
def main():
 p=argparse.ArgumentParser();p.add_argument('--node-rank',type=int,required=True);a=p.parse_args();samples=[];summaries=[];dist=[];profile_samples=[]
 run_ids=['m3abc-local-01','m3d-roce-01','m3e-group-01','m3e-group-02','m3f-allreduce-01','m3f-ddp-01','m3f-allreduce-02','m3f-ddp-02','m3d-monitor-local-01','m3d-monitor-cross-01','m3d-monitor-allreduce-01','m3d-monitor-ddp-01','m3d-monitor-lifecycle-01','m3d-native-01']
 for run in run_ids:
  d=ROOT/'runs'/run/f'node-{a.node_rank}'
  if not d.exists():continue
  m=json.loads((d/'manifest.json').read_text())
  if not m.get('probe'):
   ranks=[json.loads(p.read_text()) for p in d.glob('rank-*.json')]
   summaries.append(dict(run_id=run,node_rank=a.node_rank,training_exit=m['exit_code'],verify_exit=json.loads((d.parent/f'verify-node-{a.node_rank}.json').read_text())['exit_code'],probe=False,command=public_command(json.loads((d.parent/f'control-node-{a.node_rank}.json').read_text())['command'],a.node_rank),numerics=[dict(rank=r['rank'],status=r['status'],collectives_checked=r['collectives_checked'],initial_expected_sum=r['initial_expected_sum']) for r in ranks]));continue
  verification=json.loads((d/'verification.json').read_text());cleanup=json.loads((d/'cleanup.json').read_text())
  summary=dict(run_id=run,node_rank=a.node_rank,training_exit=m['exit_code'],reader_exit=m['reader_exit_code'],verify_exit=json.loads((d.parent/f'verify-node-{a.node_rank}.json').read_text())['exit_code'],cleanup=dict(status=cleanup["status"],removed_count=len(cleanup["removed"]),already_absent_count=len(cleanup["already_absent"])),verification=verification,probe_sha256=m['probe_library_sha256'],source_hashes=m['source_hashes'],rank_runtime_versions=[],memory_mib=[],training_checks=[],command=json.loads((d.parent/f'control-node-{a.node_rank}.json').read_text())['command'])
  if 'source_hashes' in summary['verification']:summary['verification']['source_hashes']={k.replace(str(ROOT),'<project>'):v for k,v in summary['verification']['source_hashes'].items()}
  # Public command uses project-relative entrypoints. UUID/address remain in private expanded manifest.
  summary['command']=public_command(summary['command'],a.node_rank)
  logs=[p.read_text() for p in d.glob('nccl.*.log')];summary['roce_lines']=sum(len(re.findall(r'NET/IB[^\n]*RoCE',s)) for s in logs)
  raw=[json.loads(l) for p in (d/'probe').glob('*.ndjson') for l in p.read_text().splitlines()]
  for rpath in sorted(d.glob('rank-*.json')):
   r=json.loads(rpath.read_text());rank=r['rank'];summary['rank_runtime_versions'].append(dict(rank=rank,versions=[dict(family=v['family'],encoded=v['encoded']) for v in r['runtime']['versions']]))
   summary['memory_mib'].append(dict(rank=rank,own_process_memory_mib=r['own_process_memory_mib']))
   summary['training_checks'].append(dict(rank=rank,steps=len(r['rows']),status=r['status'],max_parameter_delta=r.get('max_parameter_delta'),max_final_sync_error=r.get('max_final_sync_error'),collectives_checked=r.get('collectives_checked')))
   stream_aliases={}
   for event in [e for e in raw if e['global_rank']==rank and 1<=e['api']<=8]:
    key=event['stream_ptr']
    if key not in stream_aliases:stream_aliases[key]='stream'+str(len(stream_aliases))
    profile_samples.append(dict(run_id=run,rank=rank,publish_seq=event['publish_seq'],call_seq=event['call_seq'],profile_epoch=event['profile_epoch'],state=event['state'],api=event['api_name'],count=event['count'],count_unit=event['count_unit'],datatype=event['datatype'],comm_id_hash=event['id_hash'],stream_alias=stream_aliases[key],group_id=event['group_id'],group_depth=event['group_depth'],timing_scope={0:'none',1:'collective',2:'group_shared'}.get(event.get('timing_scope',0)),timing_status={0:'NOT_APPLICABLE',1:'VALID',2:'UNSUPPORTED',3:'INVALID_DURATION'}.get(event.get('timing_status',0)),duration_us=event.get('duration_us'),sync_block_ns=event.get('sync_block_ns'),cuda_results=json.dumps(event.get('cuda_results'))))
   data=[e for e in raw if e['global_rank']==rank and 1<=e['api']<=8 and e['state']==1]
   rows=[row for row in r['rows'] if 'sample' in row]
   if run not in ['m3abc-local-01','m3d-roce-01']:continue
   assert len(data)==len(rows)
   for event,row in zip(data,rows):
    samples.append(dict(run_id=run,rank=rank,profile_epoch=event['profile_epoch'],cycle=row['cycle'],case=row['case'],sample=row['sample'],warmup=row['warmup'],count=event['count'],count_unit='elements',datatype=event['datatype'],state=event['state'],duration_us=event['duration_us'],sync_block_ns=event['sync_block_ns'],timing_scope='collective',comm_id_hash=event['id_hash'],stream_role='communication',device=event['device'],gpu_prework_ms=row['gpu_prework_ms'],outer_interval_us=row['outer_interval_us'],host_call_ns=row['first']['host_call_ns']))
   for case in ['normal','cpu0','cpu1','gpu0','gpu1']:
    values=[s['duration_us'] for s in samples if s['run_id']==run and s['rank']==rank and s['case']==case and not s['warmup']]
    dist.append(dict(run_id=run,rank=rank,case=case,**distribution(values)))
  summaries.append(summary)
 out=ROOT/'docs/m3';out.mkdir(exist_ok=True)
 for name,rows in [('samples',samples),('distributions',dist),('profile-samples',profile_samples)]:
  if rows:
   with (out/f'{name}-node-{a.node_rank}.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 (out/f'evidence-node-{a.node_rank}.json').write_text(json.dumps(dict(runs=summaries),indent=2))
 print(json.dumps(dict(node=a.node_rank,runs=len(summaries),raw_samples=len(samples),distributions=dist)))
if __name__=='__main__':main()
