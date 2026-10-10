"""ADAPTATION: validate independent predetermined multigroup layout and counts."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.profile_input import read_records
from flash.localization import analyze
from scripts.m4_replay import manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    d=ROOT/'runs'/a.run_id/'node-0'
    m=json.loads((d/'manifest.json').read_text());reader=json.loads((d/'probe/reader-result.json').read_text())
    assert m['exit_code']==m['reader_exit_code']==0 and m['status']==reader['status']=='PASS'
    states=json.loads((d/'parallel-states-rank-0.json').read_text())
    assert [(s['label'],s['members']) for s in states]==[('DP',[0,1]),('DP',[2,3]),('TP',[0,2]),('TP',[1,3]),('DP',[0,1])]
    assert len({s['id_hashes'][0] for s in states})==5
    for rank in range(4):
        r=json.loads((d/f'rank-{rank}.json').read_text());assert r['status']=='PASS' and r['communicators_destroyed'] and r['own_process_memory_mib']<=2048
        assert json.loads((d/f'parallel-states-rank-{rank}.json').read_text())==states
        assert all(row['numerics'] for row in r['rows'])
        assert len(r['rows'])==(48 if rank in (0,1) else 32)
    assert not reader['errors']
    assert sorted(s['global_rank'] for s in reader['snapshots'])==list(range(4))
    for snapshot in reader['snapshots']:
        assert snapshot['closed'] and snapshot['read_pos']==snapshot['write_pos'] and not snapshot['poisoned']
        assert snapshot['attempts']==snapshot['write_pos']
        assert all(snapshot[k]==0 for k in ['dropped_full','dropped_lock','bad_records','errors'])
        assert snapshot['requested_control']==snapshot['applied_control'] and snapshot['state']==0
        pid=next(json.loads((d/f'rank-{rank}.json').read_text())['pid'] for rank in range(4) if rank==snapshot['global_rank'])
        assert pid==snapshot['pid']
    files=list((d/'probe').glob('*.ndjson'));assert len(files)==4
    raw=[json.loads(line) for f in files for line in f.read_text().splitlines()]
    for snapshot in reader['snapshots']:
        assert snapshot['read_pos']==len([r for r in raw if r['global_rank']==snapshot['global_rank']])
    predictions=[]
    for epoch in [1,2]:
        context=dict(run_id=a.run_id,profile_epoch=epoch)
        records,audit=read_records(files,'m3_ndjson',context)
        counts=Counter((r['id_hash'],r['global_rank']) for r in records)
        assert len(records)==60 and len(counts)==10 and all(v==6 for v in counts.values())
        b=manifest(records,context,'temporary', 'explicit test definition')
        b['parallel_states']=states
        prediction=analyze(b)
        assert len(prediction['tags']['DP']['max_avg_latency_us'])==3 and len(prediction['tags']['TP']['max_avg_latency_us'])==2
        prediction['source_audit']=audit
        out=d/f'analysis-epoch{epoch}';out.mkdir(exist_ok=True)
        (out/'input.json').write_text(json.dumps(b,indent=2)+'\n')
        (out/'prediction.json').write_text(json.dumps(prediction,indent=2)+'\n')
        predictions.append(dict(epoch=epoch,status=prediction['status'],candidate_ranks=prediction['candidate_ranks'],tags=prediction['tags'],truth_fault_ranks=[]))
    report=dict(status='PASS',run_id=a.run_id,records=120,communication_groups=5,local_communicator_instances=10,normal_only=True,
        interpretation='real Stage1 arithmetic/data path, not fault localization accuracy; any candidate is provisional false positive',predictions=predictions)
    (d/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',records=120,groups=5,candidates=[x['candidate_ranks'] for x in predictions])))


if __name__=='__main__':main()
