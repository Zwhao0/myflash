"""ADAPTATION: install approved locked M1 wheels in a project-only venv.
No host driver/toolkit/NCCL/system packages are changed.
"""
import argparse,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--approved',action='store_true');a=p.parse_args()
if not a.approved:p.error('Requires explicit user approval of project-isolated torch dependencies')
root=Path(__file__).resolve().parents[1];depot=root/'.wheels-m1';venv=root/'.venv-m1';out=root/'runs'/('m1-offline-install-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir();os.chmod(out,0o700)
manifest=json.loads((depot/'wheel-manifest.json').read_text())
for package in manifest['packages']:
    wheel=depot/package['wheel']
    if wheel.stat().st_size!=package['bytes'] or hashlib.sha256(wheel.read_bytes()).hexdigest()!=package['sha256']:
        raise RuntimeError('Wheel size/hash mismatch: '+package['wheel'])
# Independent primary-source hash checks for the principal binaries.
primary={'torch':'b2aca0939fb7e4d842561febbd4ffda67a8e958ff725c1c27e244e85e982173c','nvidia-nccl-cu12':'adf27ccf4238253e0b826bce3ff5fa532d65fc42322c8bfdfaf28024c0fbe039'}
for name,digest in primary.items():assert next(x for x in manifest['packages'] if x['name']==name)['sha256']==digest
commands=[[str(venv/'bin/python'),'-m','pip','install','--no-index','--disable-pip-version-check','--find-links',str(depot),'--require-hashes','--report',str(out/'pip-report.json'),'-r',str(depot/'requirements.lock')],[str(venv/'bin/python'),'-m','pip','check'],[str(venv/'bin/python'),'-c','import torch,importlib.metadata as m; print("TORCH",torch.__version__,"BUILD_CUDA",torch.version.cuda,"NCCL_API",torch.cuda.nccl.version()); print("NCCL_WHEEL",m.version("nvidia-nccl-cu12")); print("TORCH_PATH",torch.__file__)']]
records=[]
for i,command in enumerate(commands):
    try:
        r=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=240);rc=r.returncode;body=r.stdout+r.stderr
    except subprocess.TimeoutExpired as e:
        rc=124;body='INSTALL COMMAND TIMEOUT; child terminated by subprocess.run\n'
    (out/f'{i:02}.log').write_text(body);records.append(dict(command=command,exit_code=rc,log=f'{i:02}.log'))
    print('OFFLINE_STAGE',i,'EXIT',rc,flush=True)
    if i>0:print(body[-2000:],flush=True)
    if rc:break
(out/'manifest.json').write_text(json.dumps(dict(packages=manifest['packages'],commands=records,status='PASS' if len(records)==3 and all(x['exit_code']==0 for x in records) else 'FAIL'),indent=2));print('RUN_DIR',out,flush=True)
sys.exit(0 if len(records)==3 and all(x['exit_code']==0 for x in records) else 1)
