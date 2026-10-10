"""ADAPTATION/EXTENSION: isolated P1 capture and exact diagnostics.

Frozen M5 numerical/filter code is imported without modification. Diagnostic
buffers are fully initialized, owned and laid out by the compiled ABI probe.
"""
import argparse
import base64
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.rbeast_adapter import PARAMETERS, json_safe, candidates_from_raw, RbeastAdapter
from flash.change_detection import prefix_replay
from flash.iteration_reporter import IterationRecord
from scripts.m5_repeatability import array_bytes, library, dispatch, SCENARIOS, THREAD_VARS

MASK=(1<<64)-1
MULT=6364136223846793005
STATE=0x853c49e6748fea9b
SEQ=0xda3e39cb94b95bdb
LANES=(0,4,1,5,2,6,3,7)
CURRENT=None


def sha(data):return hashlib.sha256(data).hexdigest()


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(value)+b'\n')


def clean_env(pinned=False):
    e=dict(os.environ,PYTHONNOUSERSITE='1',PIP_CONFIG_FILE=os.devnull)
    e.pop('PYTHONPATH',None)
    if pinned:e.update({k:'1' for k in THREAD_VARS})
    return e


def kill_owned(p):
    if p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()


def interrupted(signum,frame):
    if CURRENT is not None:kill_owned(CURRENT)
    raise SystemExit(128+signum)


def execute(argv,dest,timeout,env=None,input_text=None):
    """Only the command's owned group is eligible for timeout termination."""
    global CURRENT
    dest.parent.mkdir(parents=True,exist_ok=True)
    begin=time.monotonic()
    with dest.with_suffix('.stdout').open('wb') as stdout,dest.with_suffix('.stderr').open('wb') as stderr:
        p=subprocess.Popen(argv,cwd=ROOT,env=env or clean_env(),stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                           stdout=stdout,stderr=stderr,start_new_session=True)
        CURRENT=p
        timed_out=False
        try:p.communicate(input=input_text.encode() if input_text is not None else None,timeout=timeout)
        except subprocess.TimeoutExpired:timed_out=True;kill_owned(p)
        finally:CURRENT=None
    receipt=dict(argv=argv,exit_code=124 if timed_out else p.returncode,
                 timeout=timed_out,elapsed_s=time.monotonic()-begin)
    save(dest.with_suffix('.command.json'),receipt)
    return receipt


def integer_reference(seed,count=64):
    """Independent modulo-2^64 scalar recurrence, not prior-memory predictor.

    Repeated single steps also compute the jump constants; output is PCG XSH-RR
    in the source's SIMD packing order. Zero-seed/state preprocessing retained.
    """
    initstate=STATE ^ seed
    if initstate==0:initstate=STATE
    seq=seed or SEQ
    increment=((seq<<1)|1)&MASK
    s=(increment+initstate)&MASK
    lanes=[0]*8
    for i in LANES:
        s=(s*MULT+increment)&MASK;lanes[i]=s
    initial=list(lanes)
    jump_mult=1;jump_inc=0
    for _ in range(8):
        jump_mult=(jump_mult*MULT)&MASK
        jump_inc=(jump_inc*MULT+increment)&MASK
    output=[]
    while len(output)<count:
        for i in LANES:
            x=(((lanes[i]>>18)^lanes[i])>>27)&0xffffffff
            r=lanes[i]>>59
            output.append(((x>>r)|(x<<((-r)&31)))&0xffffffff)
        for i in range(8):
            # Eight scalar steps, independently of the calculated jump.
            for _ in range(8):lanes[i]=(lanes[i]*MULT+increment)&MASK
    return dict(effective_seed=seed,increment=increment,state512=initial,
                multiplier8=jump_mult,increment8=jump_inc,output=output[:count])


def runtime():
    import numpy as np
    import Rbeast as rb
    assert np.__version__=='2.2.6' and importlib.metadata.version('Rbeast')=='0.1.25'
    lib,path=library(rb)
    return np,rb,lib,path


def native_fit(values,params,dest):
    np,rb,lib,path=runtime()
    data=np.asarray(values,dtype=np.float64)
    result=rb.beast(data,**params)
    raw=json_safe(result);arrays=array_bytes(result)
    capture=dict(input=values,input_dtype=data.dtype.str,input_shape=list(data.shape),
        input_sha256=sha(data.tobytes()),parameters=params,raw=raw,arrays=arrays,
        raw_json_sha256=sha(canonical(raw)),posterior_bytes_sha256=sha(canonical(arrays)),
        dispatch=dispatch(lib),native_binary_sha256=sha(path.read_bytes()),
        interpreter_sha256=sha(Path(sys.executable).resolve().read_bytes()),
        versions=dict(Rbeast=importlib.metadata.version('Rbeast'),numpy=np.__version__,python=sys.version),
        candidate_validation='NOT_RUN')
    # Persist the complete native tree and bytes before any candidate validator.
    save(dest,capture)
    try:
        candidates=candidates_from_raw(raw,len(values))
        error='INVALID_NATIVE_CANDIDATE' if any(c['reason'] not in (None,'PADDED_SLOT') for c in candidates) else None
    except ValueError as e:candidates=[];error=str(e)
    capture.update(native_candidates=candidates,candidate_validation_error=error,
                   candidate_validation='FAIL' if error else 'PASS')
    save(dest,capture)
    return capture


def reference(args):
    if args.pinned:os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True,exist_ok=False)
    params=dict(PARAMETERS,mcmc_chains=args.chains)
    if args.cpu!='auto':params['cputype']=args.cpu
    values=[100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)]
    for i in range(args.count):native_fit(values,params,args.output/f'fit-{i:02d}.json')
    save(args.output/'worker.json',dict(count=args.count,affinity=sorted(os.sched_getaffinity(0)),
        thread_environment={k:os.environ.get(k) for k in THREAD_VARS},
        threads_after=len(list(Path('/proc/self/task').iterdir()))))


class CapturingAdapter(RbeastAdapter):
    def __init__(self,directory):super().__init__();self.directory=directory;self.call=0

    def analyze(self,values):
        dest=self.directory/f'fit-{self.call:03d}.json';self.call+=1
        command=[sys.executable,str(Path(__file__).resolve()),'fit','--output',str(dest)]
        # The native child inherits this decision worker's group. On decision
        # timeout the parent suite owns and terminates this entire group.
        begin=time.monotonic();timed_out=False
        with dest.with_suffix('.stdout').open('wb') as stdout,dest.with_suffix('.stderr').open('wb') as stderr:
            p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,env=clean_env())
            try:p.communicate(canonical(values),timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out=True;p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        save(dest.with_suffix('.command.json'),dict(argv=command,exit_code=124 if timed_out else p.returncode,
            timeout=timed_out,elapsed_s=time.monotonic()-begin,raw_capture='PRESENT' if dest.exists() else 'NOT_CAPTURED'))
        if timed_out or p.returncode or not dest.exists():
            return dict(status='INSUFFICIENT_EVIDENCE',reason='NATIVE_TIMEOUT' if timed_out else 'NATIVE_WORKER_FAILED',raw=None)
        fit=json.loads(dest.read_text());error=fit['candidate_validation_error']
        return dict(status='INSUFFICIENT_EVIDENCE' if error else 'OK',
            reason='INVALID_NATIVE_CANDIDATE: '+error if error else None,raw=fit['raw'],
            parameters=fit['parameters'],candidates=fit['native_candidates'],input_sha256=fit['input_sha256'],
            capture_file=dest.name,dispatch=fit['dispatch'])


def decision(args):
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True,exist_ok=False)
    fixture=ROOT/'tests/m5_fixtures/records'/f'{args.scenario}.json'
    records=[IterationRecord(**r) for r in json.loads(fixture.read_text())['records']]
    rows=prefix_replay(records,CapturingAdapter(args.output))
    assert all(r['final_alert'] is False for r in rows)
    save(args.output/'decisions.json',dict(scenario=args.scenario,fixture_sha256=sha(fixture.read_bytes()),decisions=rows))


def rng(args):
    np,rb,lib,path=runtime()
    abi=json.loads(args.abi.read_text())
    assert abi['u64_sizeof']==8 and abi['sizeof']>=abi['INCREMENT_8steps']+8
    alignment=max(64,abi['alignof']);assert alignment&(alignment-1)==0
    seed=PARAMETERS['mcmc_seed']+0x4f352a3dc
    expected=integer_reference(seed)
    rows=[]
    for name,generate,fields in [('gen_pcg_set_seed','gen_pcg_random',[0,8]),
        ('avx_pcg_set_seed','avx_pcg_random',[abi['state']+i*8 for i in range(4)]+[abi['increment'],abi['increment']+8,abi['increment']+16]),
        ('avx512_pcg_set_seed','avx512_pcg_random',[abi['state512']+i*8 for i in range(8)]+[abi[k] for k in ('increment512','MULTIPLIER_8steps','INCREMENT_8steps')])]:
        seeder=getattr(lib,name);seeder.argtypes=[ctypes.c_void_p,ctypes.c_uint64,ctypes.c_uint64];seeder.restype=None
        generator=getattr(lib,generate);generator.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int32];generator.restype=None
        for fill in (0,0xa5):
            for word in (0,1,0x123456789abcdef0):
                for rep in range(2):
                    owner=ctypes.create_string_buffer(abi['sizeof']+alignment)
                    address=(ctypes.addressof(owner)+alignment-1)&~(alignment-1)
                    ctypes.memset(address,fill,abi['sizeof'])
                    ctypes.c_uint64.from_address(address+abi['increment']).value=word
                    reused=[]
                    for cycle in range(2):
                        seeder(address,STATE,seed)
                        assigned=[ctypes.c_uint64.from_address(address+k).value for k in fields]
                        values=(ctypes.c_uint32*64)();generator(address,values,64)
                        ref_words=expected['state512']+[expected[k] for k in ('increment','multiplier8','increment8')]
                        reused.append(dict(cycle=cycle,initialized_words=assigned,output=list(values),
                            reference_equal=(assigned==ref_words and list(values)==expected['output']) if name.startswith('avx512') else None))
                    rows.append(dict(function=name,fill=fill,prior_word=word,repeat=rep,cycles=reused))
    f512=[c for r in rows if r['function']=='avx512_pcg_set_seed' for c in r['cycles']]
    controls={name:len({sha(canonical(c)) for r in rows if r['function']==name for c in r['cycles'] if c['cycle']==0})==1
              for name in ('gen_pcg_set_seed','avx_pcg_set_seed')}
    result=dict(native_binary_sha256=sha(path.read_bytes()),abi=abi,reference=expected,experiments=rows,
        corrected_reference_matches=all(r['reference_equal'] for r in f512),
        prior_content_independent=len({sha(canonical(dict(initialized_words=c['initialized_words'],output=c['output']))) for c in f512})==1,
        reused_buffer_repeats=all(r['cycles'][0]['initialized_words']==r['cycles'][1]['initialized_words'] and r['cycles'][0]['output']==r['cycles'][1]['output'] for r in rows if r['function']=='avx512_pcg_set_seed'),
        unmodified_control_independence=controls)
    # A normal inference sets actual callback; direct experiment never writes it.
    native_fit([100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)],PARAMETERS,args.output.with_name('auto-path-fit.json'))
    result['normal_auto_dispatch']=dispatch(lib)
    save(args.output,result)
    print(json.dumps({k:result[k] for k in ('corrected_reference_matches','prior_content_independent','reused_buffer_repeats','normal_auto_dispatch')}))


def suite(args):
    args.output.mkdir(parents=True,exist_ok=False)
    protocol=json.loads((ROOT/'docs/m5/patch-p1/protocol.json').read_text())
    np,rb,lib,path=runtime()
    assert lib.GetNativeCPUType()==3
    save(args.output/'manifest.json',dict(run_id=args.output.name,machine='node-0',
        binary_sha256=sha(path.read_bytes()),python=sys.version,parameters=PARAMETERS,
        protocol_sha256=sha((ROOT/'docs/m5/patch-p1/protocol.json').read_bytes()),
        gpu=False,final_alert=False))
    ledger=[]
    for cell in protocol['cells']:
        label=f"{cell['affinity']}-c{cell['chains']}-{cell['requested_cpu']}-{cell['process']}"
        for repeat in range(1 if cell['process']=='same' else 20):
            directory=args.output/'reference'/label/f'{repeat:02d}'
            ledger.append(dict(path=str(directory.relative_to(args.output)),kind='reference',
                expected_fits=20 if cell['process']=='same' else 1,cell=cell))
    for scenario in SCENARIOS:
        for repeat in range(20):
            ledger.append(dict(path=f'decisions/{scenario}/{repeat:02d}',kind='decision',scenario=scenario,
                expected_prefixes=45,expected_fits=35,fixture_sha256=protocol['fixture_hashes'][scenario]))
    save(args.output/'expected-run-ledger.json',ledger)
    receipts=[]
    for item in ledger:
        dest=args.output/item['path'];worker=[sys.executable,str(Path(__file__).resolve())]
        if item['kind']=='reference':
            cell=item['cell'];command=worker+['reference','--output',str(dest),'--count',str(item['expected_fits']),
                '--chains',str(cell['chains']),'--cpu',cell['requested_cpu']]
            if cell['affinity']=='pinned':command+=['--pinned']
            receipt=execute(command,dest.with_suffix('.run'),120,clean_env(cell['affinity']=='pinned'))
        else:
            command=worker+['decision','--output',str(dest),'--scenario',item['scenario']]
            receipt=execute(command,dest.with_suffix('.run'),180,clean_env(True))
        receipts.append(dict(path=item['path'],**receipt))
        save(args.output/'worker-receipts-private.json',receipts)
        print(item['path'],receipt['exit_code'],flush=True)
    artifacts=[dict(path=str(p.relative_to(args.output)),size=p.stat().st_size,sha256=sha(p.read_bytes()))
               for p in sorted(args.output.rglob('*')) if p.is_file()]
    save(args.output/'artifact-ledger-private.json',artifacts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['reference','decision','fit','rng','suite'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--abi',type=Path)
    parser.add_argument('--count',type=int,default=20)
    parser.add_argument('--chains',type=int,choices=[1,3],default=3)
    parser.add_argument('--cpu',choices=['auto','SSE','AVX2','AVX512'],default='auto')
    parser.add_argument('--pinned',action='store_true')
    parser.add_argument('--scenario',choices=SCENARIOS)
    args=parser.parse_args()
    signal.signal(signal.SIGTERM,interrupted)
    if args.mode=='fit':native_fit(json.load(sys.stdin),PARAMETERS,args.output)
    else:globals()[args.mode](args)


if __name__=='__main__':main()
