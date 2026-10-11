"""ADAPTATION: owner-approved C-only isolated acceptance; no build/adoption.

Reuses unchanged P1 RNG, matrix, comparator and original strict assertions.
All resources are restricted to the new private run and their owned children.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE='3ba7dad2070ad13466b4f14562ee54fa4a3e818b'
CURRENT=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def files(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts}
def clean_env(pinned=False):
    e=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',PIP_CONFIG_FILE=os.devnull)
    for k in ('PYTHONPATH','LD_PRELOAD'):e.pop(k,None)
    if pinned:e.update({k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    return e
def kill(p):
    if p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
def interrupted(signum,frame):
    if CURRENT is not None:kill(CURRENT)
    raise SystemExit(128+signum)
def execute(argv,dest,deadline,env=None):
    global CURRENT
    start=time.monotonic();timed_out=False;effective=env or clean_env()
    with dest.with_suffix('.stdout').open('wb') as out,dest.with_suffix('.stderr').open('wb') as err:
        child=subprocess.Popen(argv,cwd=ROOT,stdout=out,stderr=err,env=effective,start_new_session=True,stdin=subprocess.DEVNULL)
        CURRENT=child
        try:child.wait(timeout=deadline)
        except subprocess.TimeoutExpired:timed_out=True;kill(child)
        finally:CURRENT=None
    r=dict(argv=argv,cwd=str(ROOT),pid=child.pid,pgid=child.pid,exit_code=child.returncode,
        timeout=timed_out,deadline_s=deadline,elapsed_s=time.monotonic()-start,child_finished=True,
        environment={k:effective.get(k) for k in ('PYTHONNOUSERSITE','PYTHONDONTWRITEBYTECODE','CUDA_VISIBLE_DEVICES','LD_PRELOAD','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
        stdout_sha256=sha(dest.with_suffix('.stdout')),stderr_sha256=sha(dest.with_suffix('.stderr')))
    save(dest.with_suffix('.command.json'),r)
    return r
def verify_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None;checked=0
        record=next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
        for n,h,size in csv.reader(io.StringIO(z.read(record).decode())):
            b=z.read(n);assert not size or int(size)==len(b)
            if h:
                alg,value=h.split('=',1)
                assert base64.urlsafe_b64encode(hashlib.new(alg,b).digest()).decode().rstrip('=')==value;checked+=1
        metadata={n:z.read(n).decode() for n in z.namelist() if n.endswith(('/WHEEL','/METADATA'))}
        return dict(sha256=sha(path),record_members=checked,metadata=metadata)
def main():
    signal.signal(signal.SIGTERM,interrupted)
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    project=a.project.resolve();out=a.output.resolve()
    assert out.is_relative_to(project/'runs') and not out.exists()
    assert sys.version_info[:3]==(3,12,3)
    out.mkdir();before=files(project/'.venv-m5');save(out/'formal-before.json',before)
    original_source={name:sha(ROOT/name) for name in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()}
    save(out/'source-before.json',original_source)
    result=dict(task='M6B-READY-G1-S2-C-EXECUTE',machine='node-0',gpu=False,final_alert=False,batches=[],receipts=[],status='IN_PROGRESS')
    envroot=out/'.venv-m5-s2-c';py=str(envroot/'bin/python')
    def run(label,argv,deadline=120,pinned=False):
        r=execute(argv,out/(label+'.run'),deadline,clean_env(pinned));result['receipts'].append(dict(label=label,**r))
        save(out/'progress.json',result);print(label,r['exit_code'],flush=True)
        assert r['exit_code']==0 and not r['timeout'],label+' failed; evidence retained'
        return r
    try:
        result['execution_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        result['execution_tree']=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
        for path in ('scripts/m6b_ready_s2_execute.py','scripts/m6b_ready_s2_identity.py'):result.setdefault('execution_source_sha',{})[path]=sha(ROOT/path)
        manifest=json.loads((ROOT/'docs/m5/patch-p1/build-manifest.json').read_text())
        protocol=json.loads((ROOT/'docs/m5/patch-p1/protocol.json').read_text())
        for name,want in protocol['immutable_hashes'].items():assert sha(ROOT/name)==want
        for name,want in protocol['fixture_hashes'].items():assert sha(ROOT/'tests/m5_fixtures/records'/f'{name}.json')==want
        build=project/'runs/m5-p1-work/runs/m5-p1-build-01'
        wheel=build/'C/dist'/manifest['builds']['C']['wheel']
        packages=project/'runs/m5-p1-access/packages'
        numpy=packages/'numpy-2.2.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
        sdist=project/'runs/m5-p1-access/rbeast-0.1.25.tar.gz'
        assert sha(wheel)==manifest['builds']['C']['wheel_sha256'] and sha(numpy)==manifest['packages'][numpy.name]
        assert sha(sdist)==manifest['sdist_sha256']
        assert sha(Path(sys.executable).resolve())==manifest['python_binary_sha256']
        assert next(v for k,v in before.items() if 'Rbeast/' in k and k.endswith('.so'))=='a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157'
        abi=build/'C/abi.json';assert json.loads(abi.read_text())==manifest['builds']['C']['abi']
        result['preflight']=dict(wheel=verify_zip(wheel),numpy=verify_zip(numpy),sdist_sha256=sha(sdist),
            dependency_lock_sha256=sha(ROOT/'docs/m5/patch-p1/requirements-build.lock'),abi=json.loads(abi.read_text()),
            abi_helper_sha256=sha(build/'C/abi'),python=sys.version,executable=sys.executable,
            platform=os.uname().machine,candidate_wheel_path=str(wheel),numpy_wheel_path=str(numpy))
        assert os.uname().machine=='x86_64'
        staging=out/'wheels';staging.mkdir()
        for path in (wheel,numpy):(staging/path.name).symlink_to(path)
        lock=out/'runtime.lock';lock.write_text('Rbeast==0.1.25 --hash=sha256:'+sha(wheel)+'\nnumpy==2.2.6 --hash=sha256:'+sha(numpy)+'\n')
        result['runtime_lock_sha256']=sha(lock);save(out/'preflight.json',result)
        run('create-isolated-venv',[sys.executable,'-m','venv',str(envroot)])
        save(out/'isolated-before-install.json',files(envroot))
        run('install-offline',[py,'-m','pip','install','--no-index','--no-deps','--no-compile','--require-hashes','--find-links',str(staging),'-r',str(lock)])
        run('identity',[py,'scripts/m6b_ready_s2_identity.py','--environment',str(envroot),'--output',str(out/'identity.json')])
        result['identity']=json.loads((out/'identity.json').read_text())
        so=Path(result['identity']['native_file'])
        for label,argv in [('elf',['readelf','-h',str(so)]),('symbols',['nm','-D',str(so)]),('dependencies',['ldd',str(so)]),('seeder',['objdump','-d','--disassemble=avx512_pcg_set_seed',str(so)])]:run(label,argv,60)
        symbols=(out/'symbols.stdout').read_text()
        for name in ('GetNativeCPUType','GLOBAL_CPU_CURRENT','local_pcg_set_seed','avx512_pcg_set_seed'):assert name in symbols
        run('abi-helper',[str(build/'C/abi')],30)
        assert json.loads((out/'abi-helper.stdout').read_text())==manifest['builds']['C']['abi']
        run('rng',[py,'scripts/m5_p1_diagnostic.py','rng','--abi',str(abi),'--output',str(out/'rng.json')],30,True)
        rng=json.loads((out/'rng.json').read_text())
        assert all(rng[k] for k in ('corrected_reference_matches','prior_content_independent','reused_buffer_repeats'))
        assert all(rng['unmodified_control_independence'].values())
        assert rng['normal_auto_dispatch']==dict(cpu_current=3,seed_function='avx512_pcg_set_seed')
        run('strict-api',[py,'tests/m5_real_api.py',str(out/'api')])
        run('full-replay',[py,'scripts/m5_replay.py','--input','tests/m5_fixtures/records/sustained.json','--output',str(out/'replay')],180,True)
        run('strict-prefix',[py,'scripts/m5_p1_strict.py',str(out/'prefix-capture.json'),str(out/'replay')],180,True)
        for batch in (1,2):
            name=f's2-c-batch{batch:02d}'
            receipt=run(name,['nice','-n','10',py,'scripts/m5_p1_diagnostic.py','suite','--output',str(out/name)],3600)
            result['batches'].append(dict(build='C',batch=batch,run_id=name,receipt=receipt))
            save(out/'execution-private.json',result)
        for name in ('m5_reporter','m5_detection','m5_api_fields','m5_contract_evidence','m5_p1_compare','m5_s1_offline','m6_control','m6b_ready_cursor_contract','m6b_ready_cursor_extra','privacy_check_test'):
            argv=[py,f'tests/{name}.py']
            if name=='m5_api_fields':argv.append(str(out/'field-contract'))
            if name=='m5_contract_evidence':argv.append(str(out/'arithmetic-evidence.json'))
            if name=='m6b_ready_cursor_contract':argv.extend(['--output',str(out/'cursor-contract')])
            run(name,argv)
        save(out/'execution-private.json',result)
        run('complete-comparison',[py,'scripts/m5_p1_compare.py','--execution',str(out),'--build',str(build),'--output',str(out/'comparison')],900,True)
        comparison=json.loads((out/'comparison/comparison.json').read_text())
        for k in ('C_integrity','C_numerical','C_native_validity','C_decisions'):assert comparison[k]=='PASS',k
        result['status']='PASS_ISOLATED_C_ENGINEERING_ONLY'
    except BaseException as error:
        result['status']='FAIL_OR_BLOCKED';result['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        after=files(project/'.venv-m5');save(out/'formal-after.json',after)
        result['formal_files']=len(after);result['formal_preserved']=before==after
        result['source_preserved']=original_source=={name:sha(ROOT/name) for name in original_source}
        result['own_current_child']=None if CURRENT is None else CURRENT.pid
        result['scientific_validity']='NOT_APPROVED/OPEN';result['formal_adoption']='NOT_APPROVED'
        if envroot.exists():save(out/'isolated-after.json',files(envroot))
        save(out/'execution-private.json',result);save(out/'progress.json',result)
        assert result['formal_preserved'] and result['source_preserved'],'preservation failed'

if __name__=='__main__':main()
