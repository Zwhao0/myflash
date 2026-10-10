"""ADAPTATION: fixed sequential suite and exact run cleanup; evaluator gate only."""
import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def postflight(out,run_id):
    node=out/'node-0'
    own={json.loads(p.read_text())['pid'] for p in node.glob('rank-*.json')}
    m=json.loads((node/'manifest.json').read_text());own.add(m.get('launch_pid',-1))
    commands=[['ps','-eo','pid='],['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits']]
    residual=[];checks=[]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,text=True,capture_output=True,timeout=10)
        (out/f'postflight-{i}.log').write_text(r.stdout+r.stderr)
        assert r.returncode==0
        current={int(x.strip()) for x in r.stdout.splitlines() if x.strip().isdigit()}
        matches=sorted(own & current);residual.extend(matches);checks.append(dict(command=cmd,exit_code=r.returncode,remaining_own_count=len(matches)))
    shm=list(Path('/dev/shm').glob('flash_m2_'+run_id+'_node-0_*'))
    report=dict(status='PASS' if not residual and not shm else 'FAIL',checked_own_pids=sorted(own),checks=checks,remaining_shm=[str(p) for p in shm])
    (out/'postflight.json').write_text(json.dumps(report,indent=2))
    return report['status']=='PASS'


def main():
    p=argparse.ArgumentParser();p.add_argument('--suite-id',required=True);p.add_argument('--layout',choices=['core','five'],required=True);p.add_argument('--core-suite');a=p.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_-]{1,55}',a.suite_id)
    if a.layout=='five':
        assert a.core_suite
        previous=json.loads((ROOT/'runs'/a.core_suite/'suite.json').read_text())
        assert previous['status']=='PASS' and previous['conditional_ordering_pass'], 'core gate required'
    output=ROOT/'runs'/a.suite_id;output.mkdir(exist_ok=False);output.chmod(0o700)
    approved=json.loads((ROOT/'runs/m1d-20261010-allreduce-04/node-0/manifest.json').read_text())['gpus'][:4];assert len(approved)==4
    plan=[dict(scenario=c,repetition=r) for c in 'ABCDE' for r in range(1,(2 if a.layout=='core' else 1)+1)]
    (output/'plan.json').write_text(json.dumps(dict(layout=a.layout,plan=plan,epochs=[1,2],warmup=3,profile_samples=10,delay_ms=20,fixed_order=True,gpus=approved),indent=2))
    report=dict(status='IN_PROGRESS',layout=a.layout,plan=plan,runs=[],conditional_ordering_pass=False)
    for i,item in enumerate(plan,1):
        run_id=f'{a.suite_id}-w{i:02d}'
        out=ROOT/'runs'/run_id;out.mkdir(exist_ok=False);out.chmod(0o700)
        commands=[['python3','scripts/m4_late_launch.py','--python',str(ROOT/'.venv-m1/bin/python'),'--run-id',run_id,'--gpus',','.join(approved),'--mode','multigroup','--layout',a.layout,'--scenario',item['scenario'],'--nnodes','1','--node-rank','0','--master-addr','127.0.0.1','--master-port',str(29921+i),'--timeout','300','--allow-shared','--probe'],
            ['python3','scripts/m4_late_verify.py','--run-id',run_id,'--layout',a.layout],['python3','scripts/m2_cleanup.py','--run-id',run_id,'--node-rank','0']]
        receipts=[];failed=False
        for j,cmd in enumerate(commands):
            if j==1 and failed:continue
            start=time.monotonic()
            with (out/f'command-{j}.log').open('x') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            receipts.append(dict(command=cmd,exit_code=r.returncode,log=str(out/f'command-{j}.log'),elapsed_s=time.monotonic()-start))
            if r.returncode:failed=True
            (out/'control.json').write_text(json.dumps(dict(plan=item,commands=receipts),indent=2))
        try:clean=postflight(out,run_id)
        except BaseException as error:
            clean=False;(out/'postflight-error.json').write_text(json.dumps(dict(error=repr(error))))
        row=dict(run_id=run_id,scenario=item['scenario'],repetition=item['repetition'],exit_codes=[x['exit_code'] for x in receipts],cleanup_pass=clean)
        if not failed:
            v=json.loads((out/'node-0/verification.json').read_text())
            row['windows']=[dict(epoch=w['epoch'],status=w['prediction']['status'],candidates=w['prediction']['candidate_ranks'],stage1_match=w['evaluator']['stage1_match'],stage2_match=w['evaluator']['stage2_match']) for w in v['windows']]
        report['runs'].append(row);report['status']='FAIL' if failed or not clean else 'IN_PROGRESS'
        (output/'suite.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(row),flush=True)
        if failed or not clean:return 1
    delayed=[w for r in report['runs'] if r['scenario']!='A' for w in r['windows']]
    report['conditional_ordering_pass']=all(w['stage1_match'] and w['stage2_match'] for w in delayed)
    report['status']='PASS';report['scientific_status']='CONDITIONAL_ORDERING_PASS' if report['conditional_ordering_pass'] else 'EXPECTED_ORDERING_FAIL'
    (output/'suite.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(status='PASS',scientific_status=report['scientific_status'])),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
