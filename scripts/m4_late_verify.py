"""ADAPTATION: fixed completeness contract, independent CLI, then evaluator truth."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.profile_input import read_records,validate_bundle,InputError
from scripts.m4_replay import manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--layout',choices=['core','five'],required=True);a=p.parse_args()
    d=ROOT/'runs'/a.run_id/'node-0'
    m=json.loads((d/'manifest.json').read_text());reader=json.loads((d/'probe/reader-result.json').read_text())
    assert m['exit_code']==m['reader_exit_code']==0 and m['status']==reader['status']=='PASS'
    groups=[('DP',[0,1]),('DP',[2,3]),('TP',[0,2]),('TP',[1,3]),('DP',[0,1])]
    if a.layout=='core':groups=groups[:2]
    states=json.loads((d/'parallel-states-rank-0.json').read_text())
    assert [(s['label'],s['members']) for s in states]==groups
    assert len({s['id_hashes'][0] for s in states})==len(groups)
    ranks=[]
    for rank in range(4):
        r=json.loads((d/f'rank-{rank}.json').read_text());ranks.append(r)
        assert r['status']=='PASS' and r['communicators_destroyed'] and r['own_process_memory_mib']<=2048
        assert json.loads((d/f'parallel-states-rank-{rank}.json').read_text())==states
        expected=[(epoch,phase,i,sample) for epoch in [1,2] for phase,n in [('warmup',3),('profile',10),('monitor_after',1)] for sample in range(n) for i,(_,members) in enumerate(groups) if rank in members]
        assert [(x['epoch'],x['phase'],x['group_index'],x['sample']) for x in r['rows']]==expected
        for x in r['rows']:
            assert x['numerics'] and x['expected_sum']==sum(v+1 for v in groups[x['group_index']][1])
            assert x['id_hash']==states[x['group_index']]['id_hashes'][0]
            assert x['ready_begin_ns']<=x['ready_end_ns']<=x['enter_ns']<=x['return_ns']<=x['complete_ns']
        assert r['controls'][-1]['state']==0 and r['controls'][-1]['epoch']==2
        assert len(r['controls'])==8
        assert r['cuda_syncs']==20*sum(rank in members for _,members in groups)
    assert not reader['errors']
    assert sorted(s['global_rank'] for s in reader['snapshots'])==list(range(4))
    for s in reader['snapshots']:
        assert s['run_id']==a.run_id and s['node_id']=='node-0' and s['closed'] and s['read_pos']==s['write_pos'] and not s['poisoned']
        assert s['attempts']==s['write_pos'] and all(s[k]==0 for k in ['dropped_full','dropped_lock','bad_records','errors'])
        assert s['requested_control']==s['applied_control'] and s['state']==0 and s['pid']==ranks[s['global_rank']]['pid']
    files=sorted((d/'probe').glob('*.ndjson'));assert len(files)==4
    raw=[json.loads(l) for f in files for l in f.read_text().splitlines()]
    for s in reader['snapshots']:assert s['read_pos']==sum(r['global_rank']==s['global_rank'] for r in raw)
    assert {r['run_id'] for r in raw}=={a.run_id}
    assert {r['profile_epoch'] for r in raw if r['state']==1}=={1,2}
    windows=[];isolation=[]
    for epoch in [1,2]:
        context=dict(run_id=a.run_id,profile_epoch=epoch)
        records,audit=read_records(files,'m3_ndjson',context)
        expected=Counter({(s['id_hashes'][0],r):10 for s in states for r in s['members']})
        assert Counter((r['id_hash'],r['global_rank']) for r in records)==expected
        assert len(records)==len(groups)*20
        assert all(r['timing_scope']=='collective' and r['timing_status']=='VALID' and r['duration_us']>0 and r['api']=='ncclAllReduce' and r['count']==4096 and r['datatype']==7 for r in records)
        # Expected identities/members/counts come from the fixed workload, not discovered subset.
        b=manifest(records,context,'temporary','explicit fixed synthetic NCCL groups')
        b['parallel_states']=states
        assert {x['id_hash']:x['members'] for x in b['communicators']}=={s['id_hashes'][0]:s['members'] for s in states}
        for decl in b['communicators']:
            for local in decl['local_instances']:local.update(expected_samples=10,expected_records=10)
        validate_bundle(b)
        ad=d/f'analysis-epoch{epoch}';ad.mkdir(exist_ok=True)
        (ad/'input.json').write_text(json.dumps(b,indent=2)+'\n')
        command=[sys.executable,'scripts/m4_analyze.py','--input',str(ad/'input.json'),'--output',str(ad/'prediction.json')]
        with (ad/'analysis.log').open('w') as log:rc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        assert rc==0
        prediction=json.loads((ad/'prediction.json').read_text());assert not prediction['final_fault_ranks']
        # Raw order agrees with the independently persisted workload order, by reliable hash.
        for rank in range(4):
            observed=[r['id_hash'] for r in sorted(records,key=lambda r:r['sample_seq']) if r['global_rank']==rank]
            expected_order=[x['id_hash'] for x in ranks[rank]['rows'] if x['epoch']==epoch and x['phase']=='profile']
            assert observed==expected_order
        for kind in ['run','epoch','communicator','missing']:
            bad=copy.deepcopy(b)
            if kind=='run':bad['records'][0]['run_id']='different-run'
            elif kind=='epoch':bad['records'][0]['profile_epoch']=3-epoch
            elif kind=='communicator':bad['records'][0]['id_hash']='f'*64
            else:bad['records'].pop()
            try:validate_bundle(bad)
            except InputError as error:isolation.append(dict(epoch=epoch,kind=kind,rejected=True,reason=str(error)))
            else:raise AssertionError('contamination accepted')
        # Truth is first read AFTER CLI execution; never part of input or analysis command.
        truths=[json.loads((d/f'evaluator-truth-rank-{rank}.json').read_text()) for rank in range(4)]
        assert len({json.dumps(t['target'],sort_keys=True) for t in truths})==1
        target=truths[0]['target'];scenario=truths[0]['scenario']
        events=[e for t in truths for e in t['injections']]
        assert len(events)==(0 if target is None else 26)
        if target is not None:
            expected_events=[(ep,phase,sample) for ep in [1,2] for phase,n in [('warmup',3),('profile',10)] for sample in range(n)]
            assert [(e['epoch'],e['phase'],e['sample']) for e in events]==expected_events
            assert all(e['group_index']==target['group_index'] and e['rank']==target['rank'] and e['requested_ms']==20 and e['actual_ms']>=20 for e in events)
            assert all(not t['injections'] for rank,t in enumerate(truths) if rank!=target['rank'])
        # Host timestamps are same-machine monotonic; evaluate scheduling without changing samples.
        intervals=[]
        for sample in range(10):
            spans=[]
            for i,(_,members) in enumerate(groups):
                rr=[next(x for x in ranks[r]['rows'] if x['epoch']==epoch and x['phase']=='profile' and x['group_index']==i and x['sample']==sample) for r in members]
                spans.append((min(x['enter_ns'] for x in rr),max(x['complete_ns'] for x in rr)))
                if target is not None and i==target['group_index']:
                    tr=next(x for x in rr if x in ranks[target['rank']]['rows'])
                    other=next(x for x in rr if x is not tr)
                    intervals.append(dict(sample=sample,entry_skew_ms=(tr['enter_ns']-other['enter_ns'])/1e6))
            assert all(spans[i][1]<=spans[i+1][0] for i in range(len(spans)-1)), 'overlapping group execution'
        selected=prediction['tags']['DP']['selected_groups']
        if target is None:
            evaluation=dict(scenario=scenario,truth_ranks=[],normal_candidate=bool(prediction['candidate_ranks']),candidates=prediction['candidate_ranks'],stage1_match=None,stage2_match=None)
        else:
            h=states[target['group_index']]['id_hashes'][0]
            step=prediction['tags']['DP']['stage2'].get(h,{})
            match=bool(step) and all(v['candidates']==[target['rank']] for v in step['methods'].values())
            evaluation=dict(scenario=scenario,truth_ranks=[target['rank']],target_group_index=target['group_index'],target_id_hash=h,stage1_match=selected==[h],stage2_match=match,candidates=prediction['candidate_ranks'])
        evaluation.update(status=prediction['status'],entry_intervals=intervals,interpretation='conditional ordering only; not full automatic precision/recall')
        (ad/'evaluator.json').write_text(json.dumps(evaluation,indent=2)+'\n')
        windows.append(dict(epoch=epoch,records=len(records),analysis_exit_code=rc,prediction=prediction,evaluator=evaluation,source_audit=audit))
    report=dict(status='PASS',run_id=a.run_id,layout=a.layout,groups=len(groups),local_instances=len(groups)*2,profile_records=len(groups)*40,windows=windows,isolation=isolation,
        integrity=dict(numerics=True,positive_cuda_event_durations=True,raw_digest_sequence=True,exact_counts=True,monitor_recovery=True,serial_groups=True,reader_loss=0,reader_errors=0),
        memory_mib=[r['own_process_memory_mib'] for r in ranks],runtime=[r['runtime'] for r in ranks],torch=ranks[0]['torch'],torch_build_cuda=ranks[0]['torch_build_cuda'],gpu_name=ranks[0]['gpu_name'])
    (d/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',records=report['profile_records'],candidates=[w['prediction']['candidate_ranks'] for w in windows],stage1=[w['evaluator']['stage1_match'] for w in windows],stage2=[w['evaluator']['stage2_match'] for w in windows])))


if __name__=='__main__':main()
