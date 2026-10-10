"""Reuse approved UUID mapping and exact run cleanup; no injection or system changes."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--master-port',type=int,default=29911);a=p.parse_args()
    previous=ROOT/'runs/m1d-20261010-allreduce-04/node-0/manifest.json'
    gpus=json.loads(previous.read_text())['gpus'][:4];assert len(gpus)==4
    out=ROOT/'runs'/a.run_id;out.mkdir(exist_ok=False)
    commands=[['python3','scripts/m4_launch.py','--python',str(ROOT/'.venv-m1/bin/python'),'--run-id',a.run_id,'--gpus',','.join(gpus),'--mode','multigroup','--nnodes','1','--node-rank','0','--master-addr','127.0.0.1','--master-port',str(a.master_port),'--timeout','300','--allow-shared','--probe'],
        ['python3','scripts/m4_verify_real.py','--run-id',a.run_id],['python3','scripts/m2_cleanup.py','--run-id',a.run_id,'--node-rank','0']]
    results=[]
    for i,cmd in enumerate(commands):
        started=time.monotonic()
        with (out/f'command-{i}.log').open('x') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        results.append(dict(command=cmd,exit_code=r.returncode,log=str(out/f'command-{i}.log'),elapsed_s=time.monotonic()-started))
        (out/'control.json').write_text(json.dumps(dict(mapping_source=str(previous),normal_only=True,commands=results),indent=2))
        if r.returncode:
            print(json.dumps(dict(status='FAIL',command_index=i,exit_code=r.returncode)));return r.returncode
    print(json.dumps(dict(status='PASS',run_id=a.run_id,exit_codes=[x['exit_code'] for x in results])))
    return 0


if __name__=='__main__':raise SystemExit(main())
