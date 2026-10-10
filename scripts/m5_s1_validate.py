"""ADAPTATION bounded CPU-only receipts; no native imports/fits/install commands."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from m5_s1_analysis import ROOT, BASE, preserved, sha


def files(root):
    return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--sdist',type=Path,required=True);p.add_argument('--formal-root',type=Path,required=True);a=p.parse_args()
    if not a.run_id.startswith('m5-s1-') or '/' in a.run_id:raise ValueError('invalid run_id')
    run=ROOT/'runs'/a.run_id;run.mkdir(parents=True,exist_ok=False)
    formal_before=files(a.formal_root);assert formal_before
    before=preserved()
    (run/'formal-before.json').write_text(json.dumps(formal_before,indent=2)+'\n')
    receipts=[]
    commands=[('sources',[sys.executable,'scripts/m5_s1_sources.py','--sdist',str(a.sdist),'--output','docs/m5/science-s1/data/source-receipts.json']),
              ('analysis',[sys.executable,'scripts/m5_s1_analysis.py','--output','docs/m5/science-s1/data']),
              ('offline-tests',[sys.executable,'tests/m5_s1_offline.py']),
              ('reporter',[sys.executable,'tests/m5_reporter.py']),
              ('detection',[sys.executable,'tests/m5_detection.py']),
              ('contract',[sys.executable,'tests/m5_contract_evidence.py',str(run/'contract.json')]),
              ('m4-offline',[sys.executable,'tests/m4_offline.py','--output',str(run/'m4')]),
              ('p1-readback',[sys.executable,'scripts/m5_p1_readback.py','--output',str(run/'p1-readback.json')]),
              ('privacy-unit',[sys.executable,'tests/privacy_check_test.py']),
              ('diff',['git','diff','--check']),
              ('privacy-current',[sys.executable,'scripts/privacy_check.py'])]
    def sanitize(arg):
        if arg==str(a.sdist):return '<fixed-sdist>'
        if arg.startswith(str(ROOT)):return arg.replace(str(ROOT),'') .lstrip('/')
        if arg==sys.executable:return 'python3'
        return arg
    for name,argv in commands:
        start=time.monotonic();log=run/(name+'.log')
        with log.open('w') as out:
            try:r=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=600);code=r.returncode;timedout=False
            except subprocess.TimeoutExpired:code=None;timedout=True
        private=dict(run_id=a.run_id,argv=argv,cwd=str(ROOT),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),exit_code=code,timed_out=timedout,elapsed_s=time.monotonic()-start,log=str(log),log_sha256=sha(log.read_bytes()),input_tree_sha256=sha(json.dumps(before,sort_keys=True).encode()))
        (run/(name+'.command.json')).write_text(json.dumps(private,indent=2)+'\n')
        receipts.append(dict(run_id=a.run_id,check=name,argv=[sanitize(x) for x in argv],code_sha=private['head'],input_snapshot_sha256=private['input_tree_sha256'],working_code_sha256={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in sorted((ROOT/'scripts').glob('m5_s1_*.py'))},machine='node-0 CPU only',python=platform.python_version(),os=platform.system(),arch=platform.machine(),exit_code=code,timed_out=timedout,log='runs/'+a.run_id+'/'+log.name,log_sha256=private['log_sha256'],output_stdout_stderr_sha256=private['log_sha256'],elapsed_s=private['elapsed_s'],status='PASS' if code==0 else 'FAIL'))
        print(name,code,flush=True)
    formal_after=files(a.formal_root);after=preserved();assert before==after
    (run/'formal-after.json').write_text(json.dumps(formal_after,indent=2)+'\n')
    same=formal_before==formal_after
    public=dict(task='M5-S1',run_id=a.run_id,baseline=BASE,executed_head=receipts[0]['code_sha'],
                working_diff_sha256=sha(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT)),
                machine='node-0 Intel Xeon Platinum 8463B Linux x86_64 CPU',python=platform.python_version(),
                checks=receipts,original_files_checked=len(before),originals_unchanged=True,
                formal_files_checked=len(formal_before),formal_runtime_unchanged=same,
                formal_manifest_before_sha256=sha(json.dumps(formal_before,sort_keys=True).encode()),
                formal_manifest_after_sha256=sha(json.dumps(formal_after,sort_keys=True).encode()),
                input_index_sha256=sha((ROOT/'docs/m5/science-s1/data/input-hashes.json').read_bytes()),
                output_hashes=json.loads((ROOT/'docs/m5/science-s1/data/hash-index.json').read_text()),
                historical_failures_preserved=True,final_alert=False,
                not_run=['new native fits','GPU/NCCL/Redis','M5 native API/replay rerun','M2/M3 compiled hook tests (no new build or GPU scope)','runtime adoption','M6'],
                scientific_validity='NOT_APPROVED',gaps='OPEN / REQUIRES_OWNER_DECISION',
                overall='PASS' if same and all(x['status']=='PASS' for x in receipts) else 'FAIL',
                publication='PENDING exact commit/tree and its CI; see PR and private publication receipt')
    target=ROOT/'docs/m5/science-s1/validation.json';target.write_text(json.dumps(public,indent=2)+'\n')
    (run/'validation.json').write_text(json.dumps(public,indent=2)+'\n')
    return 0 if public['overall']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
