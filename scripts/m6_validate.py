"""ADAPTATION exact command/exit/hash receipts and immutable baseline audit."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
BASE='7746fccb88718a5567da0d042d2679672d4226fc'


def sha(data):return hashlib.sha256(data).hexdigest()


def baseline():
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
        input=('\n'.join(BASE+':'+n for n in names)+'\n').encode())
    offset=0;entries=[]
    for name in names:
        end=raw.index(b'\n',offset);header=raw[offset:end].split();size=int(header[-1])
        old=raw[end+1:end+1+size];offset=end+size+2
        current=(ROOT/name).read_bytes()
        append=name in ('STATUS.md','GAPS.md')
        passed=current.startswith(old) if append else current==old
        entries.append(dict(path=name,baseline_sha256=sha(old),current_sha256=sha(current),
                            append_only=append,unchanged_or_append=passed))
    assert all(e['unchanged_or_append'] for e in entries),'baseline preservation failure'
    return entries


def tree_hashes(directory):
    if directory is None:return None
    return {str(p.relative_to(directory)):sha(p.read_bytes()) for p in sorted(directory.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}


def execute(command, folder, tag, timeout=120):
    path=folder/(tag+'.log');started=time.monotonic()
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',
             M6_EVIDENCE_DIR=str(folder/(tag+'-states')))
    env.pop('LD_PRELOAD',None)
    timed_out=False
    with path.open('wb') as out:
        child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
                               env=env,start_new_session=True)
        try:code=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            code=124
    return dict(command=command,exit_code=code,timeout=timed_out,log=str(path.relative_to(ROOT)),
                log_sha256=sha(path.read_bytes()),elapsed_test_wall_seconds=time.monotonic()-started,
                status='PASS' if code==0 else 'BLOCKED' if code==3 and tag=='redis' else 'FAIL',
                child_finished=child.poll() is not None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--native-artifacts',type=Path);p.add_argument('--approved-project',type=Path)
    p.add_argument('--formal-environment',type=Path)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
    before=baseline();formal_before=tree_hashes(args.formal_environment)
    binaries_before=tree_hashes(args.native_artifacts)
    source_checks=[]
    if args.native_artifacts:
        if args.approved_project is None:raise ValueError('source provenance project required')
        for e in before:
            if e['path'].startswith('native/'):
                source=args.approved_project/e['path']
                source_checks.append(dict(path=e['path'],match=source.is_file() and sha(source.read_bytes())==e['baseline_sha256']))
        if not all(e['match'] for e in source_checks):raise ValueError('existing artifact source provenance mismatch')
        if (ROOT/'build').exists():raise ValueError('do not replace an existing build directory')
        (ROOT/'build').symlink_to(args.native_artifacts.resolve(),target_is_directory=True)
        fixture=args.approved_project/'runs/m3abc-local-01'
        if fixture.is_dir():(ROOT/'runs/m3abc-local-01').symlink_to(fixture.resolve(),target_is_directory=True)
    commands=[('control',[sys.executable,'tests/m6_control.py']),
        ('demo',[sys.executable,'scripts/m6_demo.py','--output',str(out/'demo')]),
        ('redis',[sys.executable,'tests/m6_redis.py']),
        ('m4',[sys.executable,'tests/m4_offline.py','--output',str(out/'m4-fixtures')]),
        ('reporter',[sys.executable,'tests/m5_reporter.py']),
        ('detection',[sys.executable,'tests/m5_detection.py']),
        ('api-fields',[sys.executable,'tests/m5_api_fields.py']),
        ('contract',[sys.executable,'tests/m5_contract_evidence.py',str(out/'contract.json')]),
        ('p1-units',[sys.executable,'tests/m5_p1_compare.py']),
        ('s1-units',[sys.executable,'tests/m5_s1_offline.py']),
        ('privacy-units',[sys.executable,'tests/privacy_check_test.py']),
        ('privacy',[sys.executable,'scripts/privacy_check.py'])]
    results=[execute(cmd,out,tag,180 if tag=='m4' else 120) for tag,cmd in commands]
    native=[]
    if args.native_artifacts:
        for name in ('m2_ring','m2_hook_smoke','m2_lifecycle','m3_reader','m3_hook','m3_validation'):
            result=execute([sys.executable,'tests/'+name+'.py'],out,name)
            native.append(result)
            if result['exit_code']:break
    after=baseline();formal_after=tree_hashes(args.formal_environment)
    binaries_after=tree_hashes(args.native_artifacts)
    assert formal_before==formal_after,'formal environment changed'
    assert binaries_before==binaries_after,'existing native artifacts changed'
    versions={}
    for name in ('Rbeast','numpy','redis'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='NOT_INSTALLED'
    code_paths=sorted([str(p.relative_to(ROOT)) for pattern in ('flash/m6_*.py','scripts/m6_*.py','tests/m6_*.py') for p in ROOT.glob(pattern)])
    manifest=dict(task='M6-A',machine=platform.node(),os=platform.platform(),python=sys.version,
        code_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_diff=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        code_hashes={n:sha((ROOT/n).read_bytes()) for n in code_paths},versions=versions,
        baseline=BASE,baseline_files=len(before),preservation=after,source_checks=source_checks,
        formal_file_count=None if formal_before is None else len(formal_before),formal_unchanged=formal_before==formal_after,
        native_artifact_hashes=binaries_before,native_unchanged=binaries_before==binaries_after,
        commands=results,native_commands=native,native_status='NOT_RUN' if not native else 'PASS' if len(native)==6 and all(r['exit_code']==0 for r in native) else 'FAIL',
        final_alert=False,final_fault_ranks=[],gpu='NOT_RUN',cross_physical_nodes='NOT_RUN',
        automatic_detection='NOT_APPROVED',next_unique_task='independent ChatGPT GitHub technical review')
    failures=[r for r in results+native if r['status']=='FAIL']
    redis_result=next(r for r in results if r['command'][-1]=='tests/m6_redis.py')
    manifest['status']='FAIL' if failures else 'BLOCKED' if redis_result['status']=='BLOCKED' else 'M6-A ENGINEERING PASS'
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(status=manifest['status'],exits=[r['exit_code'] for r in results],
        native_exits=[r['exit_code'] for r in native],baseline_files=len(before),
        formal_unchanged=manifest['formal_unchanged'],native_unchanged=manifest['native_unchanged'])))
    return 1 if failures else 3 if manifest['status']=='BLOCKED' else 0


if __name__=='__main__':raise SystemExit(main())
