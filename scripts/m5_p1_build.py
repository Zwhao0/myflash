"""ADAPTATION: fixed-source private build, never modify formal runtime.

Uses only pre-transferred hash-locked packages, existing compiler/headers.
No dependency resolver/network/system installation. Exact commands remain private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import sysconfig
import tarfile
import time
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SDIST = '8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec'
OLD = b'state = state * PCG_DEFAULT_MULTIPLIER_64 + rng->increment;'
NEW = b'state = state * PCG_DEFAULT_MULTIPLIER_64 + rng->increment512;'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, v):
    p.write_text(json.dumps(v, indent=2, allow_nan=False)+'\n')


def run(command, cwd, out, env, timeout=900):
    begin = time.monotonic()
    with out.with_suffix('.stdout').open('wb') as stdout, out.with_suffix('.stderr').open('wb') as stderr:
        p = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                             start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); p.wait()
            code = 124
    save(out.with_suffix('.command.json'), dict(argv=command, exit_code=code,
         elapsed_s=time.monotonic()-begin))
    if code: raise RuntimeError('build step failed; original evidence retained: '+out.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--sdist', type=Path, required=True)
    args = parser.parse_args()
    assert sys.version_info[:3] == (3,12,3)
    assert sha(args.sdist) == SDIST
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output.resolve()
    env = dict(os.environ, PYTHONNOUSERSITE='1', PIP_CONFIG_FILE=os.devnull,
               PIP_CACHE_DIR=str(out/'cache'), TMPDIR=str(out/'tmp'))
    env.pop('PYTHONPATH', None)
    (out/'tmp').mkdir()
    bp = out/'build-env'
    venv.EnvBuilder(with_pip=True).create(bp)
    py = str(bp/'bin/python')
    lock = ROOT/'docs/m5/patch-p1/requirements-build.lock'
    run([py,'-m','pip','install','--no-index','--find-links',str(args.packages),
         '--no-deps','--require-hashes','-r',str(lock)], ROOT, out/'install-build',env)
    manifest = dict(sdist_sha256=SDIST, compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
        compiler_sha256=sha(Path('/usr/bin/gcc').resolve()), python=sys.version,
        python_binary_sha256=sha(Path(sys.executable).resolve()),
        sysconfig={k:sysconfig.get_config_var(k) for k in ('CC','CXX','CFLAGS','CCSHARED','LDSHARED','LDFLAGS')},
        environment={k:env.get(k) for k in ('CC','CXX','CFLAGS','CPPFLAGS','CXXFLAGS','LDFLAGS',
          'SOURCE_DATE_EPOCH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
        packages={p.name:sha(p) for p in args.packages.glob('*.whl')}, builds={})
    source_index=json.loads((ROOT/'docs/m5/repeatability/data/source-index.json').read_text())['files']
    trees={}
    for label, tag in (('B','1b'),('C','2c')):
        source=out/label/'source'; source.mkdir(parents=True)
        with tarfile.open(args.sdist) as archive:
            archive.extractall(source,filter='data')
        source=source/'rbeast-0.1.25'
        checks={p:sha(source/p) for p in source_index}
        assert checks==source_index
        original={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
        if label=='C':
            p=source/'ext_src/abc_rand_pcg_local_avx512.c'
            data=p.read_bytes(); assert data.count(OLD)==1
            p.write_bytes(data.replace(OLD,NEW))
        trees[label]={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
        if label=='C':
            assert set(trees['B'])==set(trees['C'])
            assert [k for k in trees['B'] if trees['B'][k]!=trees['C'][k]]==['ext_src/abc_rand_pcg_local_avx512.c']
        dist=out/label/'dist';dist.mkdir()
        # Locked setuptools build backend via its unchanged setup entry point;
        # bdist_wheel build tag is the only packaging difference.
        command=[py,'setup.py','bdist_wheel','--build-number',tag,'--dist-dir',str(dist)]
        run(command,source,out/(label+'-build'),env)
        wheels=list(dist.glob('*.whl'));assert len(wheels)==1
        wheel=wheels[0];assert 'linux_x86_64' in wheel.name and 'manylinux' not in wheel.name
        target=out/(label+'-env');venv.EnvBuilder(with_pip=True).create(target)
        tpy=str(target/'bin/python')
        numpy=next(args.packages.glob('numpy-2.2.6-*.whl'))
        run([tpy,'-m','pip','install','--no-index','--no-deps',str(numpy),str(wheel)],ROOT,out/(label+'-install'),env)
        probe=subprocess.check_output([tpy,'-c',
            'import Rbeast,numpy,importlib.metadata,pathlib,json,hashlib;'
            'p=next(pathlib.Path(Rbeast.__file__).parent.glob("Rbeast*.so"));'
            'print(json.dumps({"version":importlib.metadata.version("Rbeast"),"numpy":numpy.__version__,"so":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}))'],env=env,text=True)
        identity=json.loads(probe);assert identity['version']=='0.1.25' and identity['numpy']=='2.2.6'
        so=Path(identity['so'])
        abi=out/label/'abi'
        flags=shlex.split(sysconfig.get_config_var('CFLAGS'))
        command=shlex.split(sysconfig.get_config_var('CC'))+flags+['-fPIC','-DP_RELEASE=1','-DR_INTERFACE=0',
           '-I'+str(source/'ext_src'),str(ROOT/'tests/m5_p1_abi.c'),'-o',str(abi)]
        run(command,ROOT,out/(label+'-abi-build'),env,120)
        layout=json.loads(subprocess.check_output([str(abi)],text=True,env=env))
        save(out/label/'abi.json',layout)
        for name, command in [('ldd',['ldd',str(so)]),('symbols',['nm','-D',str(so)]),
            ('elf',['readelf','-h',str(so)]),('seeder',['objdump','-d','--disassemble=avx512_pcg_set_seed',str(so)]),
            ('serial-core',['objdump','-d','--disassemble=beast2_main_corev4',str(so)])]:
            run(command,ROOT,out/(label+'-'+name),env,60)
        with zipfile.ZipFile(wheel) as z:
            wheel_metadata=z.read(next(p for p in z.namelist() if p.endswith('/WHEEL'))).decode()
            notices={p:hashlib.sha256(z.read(p)).hexdigest() for p in z.namelist() if 'LICENSE' in p or 'NOTICE' in p}
        manifest['builds'][label]=dict(wheel=wheel.name,wheel_sha256=sha(wheel),
            native_binary_sha256=identity['sha256'],wheel_metadata=wheel_metadata,
            source_files=trees[label],source_index_original=checks,abi=layout,
            wheel_notices=notices,build_tag=tag,distribution_version='0.1.25')
        save(out/'build-manifest.json',manifest)
        print(label,'built',wheel.name,identity['sha256'],flush=True)
    assert manifest['builds']['B']['abi']==manifest['builds']['C']['abi']
    save(out/'build-manifest.json',manifest)


if __name__=='__main__':main()
