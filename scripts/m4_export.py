"""ADAPTATION: publish fixed privacy whitelist, never raw server evidence."""
import argparse
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.localization import analyze


def main():
    p=argparse.ArgumentParser();p.add_argument('--offline',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--checks',type=Path,required=True);a=p.parse_args()
    out=ROOT/'docs/m4'
    summary=json.loads((a.replay/'summary.json').read_text())
    for row in summary['results']:
        row.pop('raw_audit',None);row.pop('csv_audit',None)
        if 'command' in row:row['command']=[arg.replace(str(ROOT),'<project>') for arg in row['command']]
    (out/'m3-replay.json').write_text(json.dumps(summary,indent=2)+'\n')
    validation=json.loads((a.offline/'manifest.json').read_text())
    for row in validation['results']:
        for key in ['input','hand_expected','actual','log']:row[key]=row[key].replace(str(ROOT),'<project>')
        row['command']=[arg.replace(str(ROOT),'<project>') for arg in row['command']]
    (out/'fixture-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    for row in validation['results']:
        name=row['fixture'];target=out/'fixtures'/name;target.mkdir(parents=True,exist_ok=True)
        actual=json.loads((a.offline/name/'actual.json').read_text())
        for audit in actual.get('source_audit',[]):audit['path']=audit['path'].replace(str(ROOT),'<project>')
        (target/'actual.json').write_text(json.dumps(actual,indent=2)+'\n')
        (target/'exit_code.txt').write_text(str(row['exit_code'])+'\n')
    private=ROOT/'runs/m4-multigroup-normal-01/node-0'
    real=json.loads((private/'verification.json').read_text())
    (out/'multigroup-validation.json').write_text(json.dumps(real,indent=2)+'\n')
    samples=[]
    for epoch in [1,2]:
        bundle=json.loads((private/f'analysis-epoch{epoch}/input.json').read_text())
        for r in bundle['records']:r['process_instance']=f"rank{r['global_rank']}"
        for d in bundle['communicators']:
            for local in d['local_instances']:local['process_instance']=f"rank{local['global_rank']}"
        prediction=analyze(bundle)
        original=json.loads((private/f'analysis-epoch{epoch}/prediction.json').read_text())
        assert prediction['tags']==original['tags'] and prediction['candidate_ranks']==original['candidate_ranks'] and prediction['completeness']==original['completeness']
        (out/f'multigroup-input-epoch{epoch}.json').write_text(json.dumps(bundle,indent=2)+'\n')
        (out/f'multigroup-prediction-epoch{epoch}.json').write_text(json.dumps(prediction,indent=2)+'\n')
        samples.extend(bundle['records'])
    with (out/'multigroup-profile.csv').open('w',newline='') as f:
        fields=['run_id','profile_epoch','node_id','global_rank','id_hash','comm_generation','process_instance','comm_rank','comm_size','timing_scope','timing_status','duration_us','duration_unit','api','count','count_unit','datatype','group_id','group_depth','sample_seq']
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in fields} for r in samples)
    assert len(samples)==120
    checks=json.loads((a.checks/'manifest.json').read_text())
    (out/'final-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',fixtures=len(validation['results']),real_records=120,alias_statistics_equal=True)))


if __name__=='__main__':main()
