"""ADAPTATION: declared control/strict gates and conditional two-batch runner.

One node-0 CPU subprocess group at a time. All statuses reflect real receipts,
never the orchestration exit code alone. No formal installation or mutation.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import signal

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.m5_p1_diagnostic import execute, clean_env, save, sha, interrupted


def preservation(formal):
    # Read-only bytes excluding interpreter-created pycache artifacts.
    env=Path(formal).absolute().parents[1]
    assert env.name=='.venv-m5', 'preservation is restricted to the formal project venv'
    files={str(p.relative_to(env)):sha(p.read_bytes()) for p in env.rglob('*')
           if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts}
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only','ed954f5a289e2a9f3c585f7f5af3792d0fde0c8d'],cwd=ROOT,text=True).splitlines()
    source={p:sha((ROOT/p).read_bytes()) for p in paths}
    return dict(formal_environment=files,baseline_source=source)


def main():
    signal.signal(signal.SIGTERM,interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--formal-python',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    output=args.output.resolve();build=args.build.resolve()
    before=preservation(args.formal_python);save(output/'preservation-before-private.json',before)
    manifest=json.loads((build/'build-manifest.json').read_text())
    results=dict(protocol_sha256=sha((ROOT/'docs/m5/patch-p1/protocol.json').read_bytes()),
                 machine='node-0',gpu=False,final_alert=False,controls={},batches=[],regressions={})
    def record():save(output/'progress.json',results)
    interpreters=dict(A=str(args.formal_python),B=str(build/'B-env/bin/python'),C=str(build/'C-env/bin/python'))
    for label in ('A','B','C'):
        py=interpreters[label];base=output/label;base.mkdir()
        abi=build/('B' if label=='A' else label)/'abi.json'
        rng=execute([py,'scripts/m5_p1_diagnostic.py','rng','--abi',str(abi),'--output',str(base/'rng.json')],base/'rng.run',30,clean_env(True))
        api=execute([py,'tests/m5_real_api.py',str(base/'api')],base/'strict-api.run',120)
        replay=execute([py,'scripts/m5_replay.py','--input','tests/m5_fixtures/records/sustained.json','--output',str(base/'replay')],base/'generate-replay.run',180,clean_env(True))
        assertion=execute([py,'scripts/m5_p1_strict.py',str(base/'prefix-capture.json'),str(base/'replay')],base/'strict-prefix.run',180,clean_env(True))
        r=json.loads((base/'rng.json').read_text()) if (base/'rng.json').exists() else {}
        results['controls'][label]=dict(rng_receipt=rng,api_receipt=api,replay_receipt=replay,prefix_receipt=assertion,
            rng_correct_reference=r.get('corrected_reference_matches',False),prior_independent=r.get('prior_content_independent',False),
            reuse_repeats=r.get('reused_buffer_repeats',False),auto_dispatch=r.get('normal_auto_dispatch'),
            rng_controls=r.get('unmodified_control_independence'))
        record();print(label,'RNG',rng['exit_code'],'API',api['exit_code'],'PREFIX',assertion['exit_code'],flush=True)
    c=results['controls']['C']
    prerequisite=(all(c[k]['exit_code']==0 for k in ('rng_receipt','api_receipt','replay_receipt','prefix_receipt'))
        and c['rng_correct_reference'] and c['prior_independent'] and c['reuse_repeats']
        and all(c['rng_controls'].values()) and c['auto_dispatch']==dict(cpu_current=3,seed_function='avx512_pcg_set_seed'))
    results['C_prerequisite_gate']='PASS' if prerequisite else 'FAIL';record()
    if prerequisite:
        for batch,order in enumerate((('B','C'),('C','B')),1):
            for label in order:
                run_id=f'm5-p1-{label.lower()}-batch{batch:02d}'
                dest=output/run_id
                receipt=execute(['nice','-n','10',interpreters[label],'scripts/m5_p1_diagnostic.py','suite','--output',str(dest)],
                                output/(run_id+'.run'),3600)
                results['batches'].append(dict(build=label,batch=batch,run_id=run_id,receipt=receipt));record()
                print(run_id,receipt['exit_code'],flush=True)
    else:
        results['full_matrix']='NOT_RUN: C prerequisite gate failed';record()
    for name in ('m5_reporter','m5_detection','m5_api_fields','m5_contract_evidence','m5_p1_compare','privacy_check_test'):
        command=[interpreters['C'],f'tests/{name}.py']
        if name=='m5_api_fields':command.append(str(output/'field-contract'))
        if name=='m5_contract_evidence':command.append(str(output/'arithmetic-evidence.json'))
        r=execute(command,output/(name+'.run'),120)
        results['regressions'][name]=r;record();print(name,r['exit_code'],flush=True)
    after=preservation(args.formal_python);save(output/'preservation-after-private.json',after)
    results['preservation_equal']=before==after
    results['scientific_validity']='NOT_APPROVED/OPEN'
    results['formal_adoption']='NOT_APPROVED'
    results['M6']='NOT_APPROVED'
    save(output/'execution-private.json',results)
    record();print('M5-P1 execution complete; independent data validation still required',flush=True)


if __name__=='__main__':main()
