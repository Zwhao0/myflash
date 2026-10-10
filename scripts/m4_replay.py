"""ADAPTATION: offline M3 replay and evaluator; analyze sees no case/target/truth."""
import argparse
import copy
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.profile_input import read_records
from flash.localization import analyze


def manifest(records,context,label,evidence):
    comms=[]
    by_hash=defaultdict(list)
    for r in records:by_hash[r['id_hash']].append(r)
    for h,rows in by_hash.items():
        by_local=defaultdict(list)
        for r in rows:by_local[(r['node_id'],r['global_rank'],r['process_instance'],r['comm_generation'])].append(r)
        locals_=[]
        for (node,rank,process,gen),rs in by_local.items():
            scopes={('group',r['thread_id'],r['group_id']) if r['timing_scope']=='group_shared' else ('collective',r['sample_seq']) for r in rs}
            locals_.append(dict(node_id=node,global_rank=rank,process_instance=process,comm_generation=gen,comm_rank=rs[0]['comm_rank'],expected_samples=len(scopes),expected_records=len(rs)))
        # Membership must agree with each raw communicator size; incomplete rank cannot redefine it.
        members=sorted({r['global_rank'] for r in rows})
        assert len(members)==rows[0]['comm_size']
        comms.append(dict(id_hash=h,members=members,local_instances=locals_))
    return dict(schema_version=1,context=context,records=records,communicators=comms,
        parallel_states=[dict(label=label,members=d['members'],id_hashes=[d['id_hash']],evidence=evidence) for d in comms])


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    public=ROOT/'docs/m3'
    summaries=[]; total_mechanism=0
    source_runs=['m3abc-local-01','m3d-roce-01','m3e-group-02','m3f-allreduce-02','m3f-ddp-02']
    for run in source_runs:
        ndjson=list((ROOT/'runs'/run).glob('node-*/probe/*.ndjson')) + list((ROOT/'runs/m4-replay-source/runs'/run).glob('node-*/probe/*.ndjson'))
        assert ndjson,run
        all_raw=[json.loads(l) for f in ndjson for l in f.read_text().splitlines()]
        profiles=[r for r in all_raw if r['state']==1 and 1<=r['api']<=8]
        # Raw source from gpu-02 is transferred project-locally for read-only replay.
        supplements={}
        for node in [0,1]:
            path=public/f'profile-samples-node-{node}.csv'
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            for r in all_raw:
                if (r['node_id']=='node-0') != (node==0):continue
                if 1<=r['api']<=8:
                    key=f"{r['run_id']}:{r['global_rank']}:{r['publish_seq']}"
                    supplements[key]={k:r[k] for k in ('node_id','pid','thread_id','comm_generation','comm_rank','comm_size','identity_source','result')}
                    supplements[key]['source_csv_sha256']=sha
        epochs=sorted({r['profile_epoch'] for r in profiles})
        for epoch in epochs:
            context=dict(run_id=run,profile_epoch=epoch,source_run_policy='explicit_selection')
            raw_records,raw_audit=read_records(ndjson,'m3_ndjson',context)
            if 'group' not in run:
                expected_per_rank=65 if run in source_runs[:2] else 6 if 'allreduce' in run else (12 if epoch==1 else 8)
                expected_ranks=set(range(2 if run in source_runs[:2] else 16))
                assert set(r['global_rank'] for r in raw_records)==expected_ranks
                assert all(n==expected_per_rank for n in Counter(r['global_rank'] for r in raw_records).values()),'M3 verified sample count mismatch'
            csv_records,csv_audit=read_records([public/'profile-samples-node-0.csv',public/'profile-samples-node-1.csv'],'m3_csv',context,supplements)
            assert raw_records and len(raw_records)==len(csv_records)
            sort=lambda rows:sorted(rows,key=lambda r:(r['global_rank'],r['sample_seq']))
            assert sort(raw_records)==sort(csv_records),'CSV/raw mismatch'
            label='DDP' if 'ddp' in run else 'mechanism_pair' if run in source_runs[:2] else 'collective_test'
            b=manifest(raw_records,context,label,'M3 workload creates explicit WORLD members; no TP/EP traffic inference')
            d=a.output/f'{run}-epoch{epoch}';d.mkdir()
            (d/'input.json').write_text(json.dumps(b,indent=2)+'\n')
            command=[sys.executable,'scripts/m4_analyze.py','--input',str(d/'input.json'),'--output',str(d/'prediction.json')]
            with (d/'analysis.log').open('w') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            prediction=json.loads((d/'prediction.json').read_text())
            expected_code=2 if 'group' in run else 0
            assert r.returncode==expected_code,(run,r.returncode)
            summaries.append(dict(run_id=run,epoch=epoch,records=len(raw_records),status=prediction['status'],candidate_ranks=prediction['candidate_ranks'],
                csv_raw_exact=True,command=command,exit_code=r.returncode,raw_audit=raw_audit,csv_audit=csv_audit))
            if run not in source_runs[:2]:continue
            # Evaluator-only trace maps sample order to workload windows. It is never supplied to analyze.
            samples=[row for node in [0,1] for row in csv.DictReader((public/f'samples-node-{node}.csv').open()) if row['run_id']==run and int(row['profile_epoch'])==epoch]
            mapping={}
            for rank in [0,1]:
                rs=sorted([r for r in raw_records if r['global_rank']==rank],key=lambda r:r['sample_seq'])
                ss=[s for s in samples if int(s['rank'])==rank]
                assert len(rs)==len(ss)==65
                for rr,ssr in zip(rs,ss):
                    assert rr['duration_us']==float(ssr['duration_us'])
                    mapping[(rank,rr['sample_seq'])]=ssr
            for i,case in enumerate(['normal','cpu0','cpu1','gpu0','gpu1']):
                for policy in ['all13','fixed_warmup3']:
                    rs=[r for r in raw_records if mapping[(r['global_rank'],r['sample_seq'])]['case']==case and (policy=='all13' or mapping[(r['global_rank'],r['sample_seq'])]['warmup']=='False')]
                    ctx=dict(run_id=run,profile_epoch=epoch,window_id=f'w{i+1}',selection_policy=policy)
                    bb=manifest(rs,ctx,'mechanism_pair','M3 explicit WORLD [0,1]; predetermined sequence window; evaluator truth excluded')
                    output=analyze(bb)
                    wd=d/f'w{i+1}-{policy}';wd.mkdir()
                    (wd/'input.json').write_text(json.dumps(bb,indent=2)+'\n')
                    (wd/'prediction.json').write_text(json.dumps(output,indent=2)+'\n')
                    target=[] if case=='normal' else [int(case[-1])]
                    (wd/'evaluator.json').write_text(json.dumps(dict(case=case,truth_ranks=target,predicted=output['candidate_ranks'],match=target==output['candidate_ranks'],
                        interpretation='mechanism evidence only; normal provisional candidates count as false positives'),indent=2)+'\n')
                    summaries.append(dict(run_id=run,epoch=epoch,window_id=f'w{i+1}',selection_policy=policy,records=len(rs),case=case,
                        truth_ranks=target,candidate_ranks=output['candidate_ranks'],status=output['status'],match=target==output['candidate_ranks']))
                    if policy=='all13':total_mechanism+=len(rs)
    assert total_mechanism==520,total_mechanism
    report=dict(status='PASS',machine=platform.node(),mechanism_records=total_mechanism,raw_csv_equal=True,results=summaries,
        limitation='M3 has one communicator group/window, so it does not validate real Stage1; normal candidates are not suppressed.')
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',mechanism_records=total_mechanism,results=len(summaries))))


if __name__=='__main__':main()
