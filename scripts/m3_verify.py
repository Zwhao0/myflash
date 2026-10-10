# ADAPTATION: independent evidence verifier, no rank localization or automatic decisions.
import argparse,json,math,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
def verify(directory,world,mode,profile):
 m=json.loads((directory/'manifest.json').read_text());assert m['exit_code']==0 and m['reader_exit_code']==0
 expected=list(range(m['node_rank']*len(m['gpus']),(m['node_rank']+1)*len(m['gpus'])))
 ranks=[json.loads(p.read_text()) for p in directory.glob('rank-*.json')];assert sorted(x['rank'] for x in ranks)==expected
 result=json.loads((directory/'probe/reader-result.json').read_text());assert result['status']=='PASS' and not result['errors']
 snapshots=result['snapshots'];assert sorted(x['global_rank'] for x in snapshots)==expected
 events=[]
 for p in sorted((directory/'probe').glob('events-*.ndjson')):events.extend(json.loads(line) for line in p.read_text().splitlines())
 by_rank=defaultdict(list)
 for e in events:
  content={k:v for k,v in e.items() if k!='record_digest'}
  assert e['record_digest']==hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  assert e['result']==0 and e['run_id']==m['run_id'] and e['node_id']==f"node-{m['node_rank']}"
  assert e['global_rank'] in expected;by_rank[e['global_rank']].append(e)
 reports=[]
 for rank in expected:
  r=next(x for x in ranks if x['rank']==rank);s=next(x for x in snapshots if x['global_rank']==rank);rows=by_rank[rank];data=[e for e in rows if 1<=e['api']<=8]
  assert r['status']=='PASS' and r['world_size']==world and r['own_process_memory_mib']<=2048 and r['pid']==s['pid']
  assert s['abi']==2 and s['state']==0 and s['closed']==1
  assert s['requested_control']==s['applied_control'] and not (s['applied_control']&1)
  assert s['attempts']==s['write_pos']==s['read_pos']==len(rows)
  assert not any(s[k] for k in ['dropped_full','dropped_lock','errors','bad_records','poisoned'])
  assert [e['publish_seq'] for e in rows]==list(range(1,len(rows)+1))
  assert all(e['identity']==1 and len(e['id_hash'])==64 and e['comm_rank']==rank and e['comm_size']==world and e['comm_ptr'] and e['comm_generation'] for e in data)
  actual=r['runtime']['versions'];assert any(v['family']=='nccl' and v['encoded']==22703 for v in actual);assert any(v['family']=='cudart' and v['encoded']==12080 for v in actual)
  timed=[e for e in data if e['state']==1];valid=[e for e in timed if e['timing_status']==1];unsupported=[e for e in timed if e['timing_status']==2]
  if mode!='group':assert not unsupported # Unsupported samples never make a complete normal profile.
  assert all('duration_us' not in e for e in data if e['state']==0)
  assert all(e['timing_status'] in (1,2) for e in timed)
  for e in valid:
   assert e['device']==r['local_rank']
   assert math.isfinite(e['duration_us']) and e['duration_us']>0 and e['sync_block_ns']>=0
   assert all(e['cuda_results'][i]==0 for i in range(10)) and e['cuda_results'][10]==-1
   assert e['timing_scope']==(2 if e['group_id'] else 1)
  assert all(e['duration_us'] is None for e in unsupported)
  scopes={('group',e['group_id']) if e['group_id'] else ('single',e['call_seq']) for e in valid}
  if profile or mode in ['mechanism','group']:
   assert {e['profile_epoch'] for e in valid}=={1,2}
   for epoch in [1,2]:assert any(e['state']==0 and e['profile_epoch']==epoch for e in data)
  else:assert not timed
  counts=Counter(e['api_name'] for e in rows)
  if mode=='allreduce':
   assert r['collectives_checked']==25 and len(r['rows'])==25 and r['initial_expected_sum']==world*(world+1)//2
   assert len([e for e in data if e['api']==1 and e['count']==4096 and e['datatype']==4])==25
  if mode=='ddp':
   assert len(r['rows'])==20 and r['parameter_count']==676 and r['max_parameter_delta']>0
   assert all(x['max_parameter_sync_error']<=1e-6 for x in r['rows'])
   assert counts['ncclBcast']==26 and counts['ncclAllGather']==1 and counts['ncclAllReduce']==23
  if mode in ['allreduce','ddp'] and profile:
   assert len(valid)==(12 if mode=='allreduce' else 20)
   ctrl=json.loads((directory/f'profile-rank-{rank}.json').read_text());assert ctrl['cuda_syncs']==len(scopes) and ctrl['cuda_calls']>0
  if mode=='mechanism':
   assert len(data)==134 and len(valid)==130 and not unsupported and all(e['stream_ptr']==r['communication_stream'] for e in data)
   assert r['cuda_syncs']==130
   workload=[row for row in r['rows'] if 'sample' in row];assert len(workload)==len(valid)
   for event,row in zip(valid,workload):
    assert event['profile_epoch']==row['epoch'] and event['duration_us']<=row['outer_interval_us']+2
    if row['case'].startswith('gpu') and row['gpu_prework_ms'] is not None:assert row['gpu_prework_ms']>0
  if mode=='group':
   assert len(data)==60 and len(valid)==40 and len(unsupported)==16 and r['cuda_syncs']==24
   groups=defaultdict(list)
   for e in timed:
    if e['group_id']:groups[e['group_id']].append(e)
   assert len(groups)==24
   for members in groups.values():assert len(members)==2 and len({(e['profile_epoch'],e['timing_status'],e['duration_us']) for e in members})==1
   assert any(e['group_depth']==2 for e in valid)
  reports.append(dict(rank=rank,events=len(rows),profile_records=len(timed),valid_records=len(valid),unsupported=len(unsupported),timing_scopes=len(scopes),sync_block_ns=sum(next(e['sync_block_ns'] for e in valid if (('group',e['group_id']) if e['group_id'] else ('single',e['call_seq']))==key) for key in scopes),apis=dict(counts)))
 assert len({r['gpu_uuid'] for r in ranks})==len(expected)
 return dict(status='PASS',complete_profile=(not any(x['unsupported'] for x in reports)) if profile or mode in ['mechanism','group'] else None,ranks=reports,total_events=len(events),loss=0)
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--node-rank',type=int,required=True);p.add_argument('--world',type=int,required=True);p.add_argument('--mode',required=True);a=p.parse_args()
 d=ROOT/'runs'/a.run_id/f'node-{a.node_rank}';control=json.loads((ROOT/'runs'/a.run_id/f'control-node-{a.node_rank}.json').read_text());profile='--profile' in control['command']
 result=verify(d,a.world,a.mode,profile);(d/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
