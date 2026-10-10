"""ADAPTATION/EXTENSION: bounded CPU diagnostics, never production defaults.

UPSTREAM Rbeast0.1.25 sdist/wheel; see docs/m5/repeatability/ROOT_CAUSE.md.
The exported-symbol experiment uses only initialized diagnostic-owned buffers.
It does not hook, patch, or replace any function or production stream.
"""
import argparse
import base64
import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.rbeast_adapter import PARAMETERS, json_safe, candidates_from_raw, RbeastAdapter
from flash.change_detection import prefix_replay
from flash.iteration_reporter import IterationRecord

SCENARIOS = ('stable', 'sustained', 'growth_19', 'growth_20', 'growth_21', 'spike', 'recovery')
THREAD_VARS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def runtime():
    import numpy as np
    import Rbeast as rb
    assert importlib.metadata.version('Rbeast') == '0.1.25'
    assert np.__version__ == '2.2.6'
    return np, rb


def library(rb):
    paths = list(Path(rb.__file__).parent.glob('Rbeast*.so'))
    assert len(paths) == 1
    return ctypes.CDLL(str(paths[0])), paths[0]


def dispatch(lib):
    pointer = ctypes.c_void_p.in_dll(lib, 'local_pcg_set_seed').value
    names = ('gen_pcg_set_seed', 'avx_pcg_set_seed', 'avx512_pcg_set_seed')
    return dict(cpu_current=ctypes.c_uint8.in_dll(lib, 'GLOBAL_CPU_CURRENT').value,
                seed_function=next((n for n in names if ctypes.cast(getattr(lib, n), ctypes.c_void_p).value == pointer), 'UNKNOWN'))


def array_bytes(out):
    """Preserve every ndarray's dtype/shape/exact bytes, including NaN payloads."""
    import numpy as np
    result = {}
    def walk(v, path):
        if isinstance(v, np.ndarray):
            data = v.tobytes(order='C')
            result[path] = dict(dtype=v.dtype.str, shape=list(v.shape), sha256=sha(data),
                                bytes_base64=base64.b64encode(data).decode())
        elif hasattr(v, '__dict__'):
            walk(vars(v), path)
        elif isinstance(v, dict):
            for k, child in v.items():
                walk(child, path + '.' + k if path else k)
        elif isinstance(v, (tuple, list)):
            for i, child in enumerate(v):
                walk(child, path + '.' + str(i))
    walk(out, '')
    return result


def native_fit(values, params):
    np, rb = runtime()
    data = np.asarray(values, dtype=np.float64)
    begin = time.monotonic()
    out = rb.beast(data, **params)
    raw = json_safe(out)
    arrays = array_bytes(out)
    lib, path = library(rb)
    # Capture invalid native outputs too; never weaken the production validation.
    try:
        candidates = candidates_from_raw(raw, len(values))
        candidate_error = ('INVALID_NATIVE_CANDIDATE' if any(
            c['reason'] not in (None, 'PADDED_SLOT') for c in candidates) else None)
    except ValueError as error:
        candidates = []
        candidate_error = str(error)
    return dict(input=values, input_dtype=data.dtype.str, input_shape=list(data.shape),
                input_sha256=sha(data.tobytes()), parameters=params, raw=raw,
                raw_json_sha256=sha(canonical(raw)), arrays=arrays,
                posterior_bytes_sha256=sha(canonical(arrays)), dispatch=dispatch(lib),
                native_binary_sha256=sha(path.read_bytes()), elapsed_s=time.monotonic()-begin,
                native_candidates=candidates, candidate_validation_error=candidate_error)


def reference_worker(args):
    if args.pinned:
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    params = dict(PARAMETERS, mcmc_chains=args.chains)
    if args.cpu != 'auto':
        params['cputype'] = args.cpu
    values = [100+(i % 3)*.2+(30 if i >= 15 else 0) for i in range(30)]
    fits = [native_fit(values, params) for _ in range(args.count)]
    save(args.output, dict(fits=fits, affinity=sorted(os.sched_getaffinity(0)),
                         thread_environment={v:os.environ.get(v) for v in THREAD_VARS},
                         threads_after=len(list(Path('/proc/self/task').iterdir()))))


class CapturingAdapter(RbeastAdapter):
    """Same subprocess boundary, parameters, candidate extraction as M5 adapter.

    New worker additionally captures native array bytes and actual RNG dispatch.
    No result is cached or reused. One new interpreter per native fit.
    """
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.call = 0

    def analyze(self, values):
        index = self.call
        self.call += 1
        dest = self.directory / ('fit-%03d.json' % index)
        command = [sys.executable, str(Path(__file__).resolve()), 'fit', '--output', str(dest)]
        t = time.monotonic()
        try:
            run = subprocess.run(command, input=json.dumps(values), text=True,
                                 capture_output=True, timeout=self.timeout_s)
            (self.directory / ('fit-%03d.stdout' % index)).write_text(run.stdout)
            (self.directory / ('fit-%03d.stderr' % index)).write_text(run.stderr)
            save(self.directory / ('fit-%03d.command.json' % index),
                 dict(argv=command, exit_code=run.returncode, elapsed_s=time.monotonic()-t))
            if run.returncode:
                return dict(status='INSUFFICIENT_EVIDENCE', reason='NATIVE_WORKER_FAILED', raw=None)
            fit = json.loads(dest.read_text())
            error = fit['candidate_validation_error']
            return dict(status='INSUFFICIENT_EVIDENCE' if error else 'OK',
                        reason='INVALID_NATIVE_CANDIDATE: '+error if error else None,
                        raw=fit['raw'], parameters=fit['parameters'],
                        candidates=fit['native_candidates'], input_sha256=fit['input_sha256'],
                        raw_json_sha256=fit['raw_json_sha256'], posterior_bytes_sha256=fit['posterior_bytes_sha256'],
                        dispatch=fit['dispatch'], capture_file=dest.name)
        except subprocess.TimeoutExpired:
            save(self.directory / ('fit-%03d.command.json' % index),
                 dict(argv=command, exit_code=None, reason='NATIVE_TIMEOUT'))
            return dict(status='INSUFFICIENT_EVIDENCE', reason='NATIVE_TIMEOUT', raw=None)


def decision_worker(args):
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(exist_ok=False)
    fixture = ROOT / 'tests/m5_fixtures/records' / (args.scenario + '.json')
    rows = [IterationRecord(**r) for r in json.loads(fixture.read_text())['records']]
    result = prefix_replay(rows, CapturingAdapter(args.output))
    assert all(d['final_alert'] is False for d in result)
    save(args.output / 'decisions.json', dict(scenario=args.scenario,
         fixture_sha256=sha(fixture.read_bytes()), decisions=result))


def rng_worker(args):
    """Finite causal experiment on the installed seeder, initialized buffers only.

    Source union: state512[8] at0, increment512 at64; AVX2 increment at32.
    Observe only assigned state8/inc/multiplier/increment fields, not padding.
    No calls to SetupRoutines and no writes to library globals.
    """
    np, rb = runtime()
    lib, path = library(rb)
    seed = PARAMETERS['mcmc_seed'] + 0x4f352a3dc
    mask = (1 << 64)-1
    rows = []
    for name, random_name, words in [('gen_pcg_set_seed','gen_pcg_random',2),
                                    ('avx_pcg_set_seed','avx_pcg_random',7),
                                    ('avx512_pcg_set_seed','avx512_pcg_random',11)]:
        seeder = getattr(lib, name)
        seeder.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
        seeder.restype = None
        generator = getattr(lib, random_name)
        generator.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32]
        generator.restype = None
        for old_word in (0, 1, 0x123456789abcdef0):
            for repeat in range(2):
                buffer = ctypes.create_string_buffer(256)
                address = (ctypes.addressof(buffer)+63) & ~63
                ctypes.memset(address, 0, 128)
                ctypes.c_uint64.from_address(address+32).value = old_word
                seeder(address, 0x853c49e6748fea9b, seed)
                initialized = [ctypes.c_uint64.from_address(address+8*i).value for i in range(words)]
                predicted = None
                if name == 'avx512_pcg_set_seed':
                    inc = ((seed << 1) | 1) & mask
                    state = (old_word + (0x853c49e6748fea9b ^ seed)) & mask
                    expected = [0]*8
                    for lane in (0,4,1,5,2,6,3,7):
                        state = (state*6364136223846793005+inc) & mask
                        expected[lane] = state
                    predicted = dict(state512=expected, matches=initialized[:8] == expected)
                output = (ctypes.c_uint32*16)()
                generator(address, output, 16)
                rows.append(dict(function=name, prior_word_at_byte32=old_word,
                     repeat=repeat, seed=seed, initialized_words=initialized,
                     predicted_from_source=predicted, rng_output=list(output)))
    save(args.output, dict(native_binary_sha256=sha(path.read_bytes()), experiments=rows,
         note='Own initialized buffers only; no production stream or function altered'))


def execute(command, dest, env, timeout):
    dest.parent.mkdir(parents=True, exist_ok=True)
    begin = time.monotonic()
    try:
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=timeout)
        dest.with_suffix('.stdout').write_text(run.stdout)
        dest.with_suffix('.stderr').write_text(run.stderr)
        code = run.returncode
    except subprocess.TimeoutExpired as error:
        dest.with_suffix('.stdout').write_bytes(error.stdout or b'')
        dest.with_suffix('.stderr').write_bytes(error.stderr or b'')
        code = 124
    receipt = dict(argv=command, exit_code=code, elapsed_s=time.monotonic()-begin)
    save(dest.with_suffix('.command.json'), receipt)
    if code:
        raise RuntimeError('diagnostic worker failed; evidence retained: '+str(dest))
    return receipt


def suite(args):
    args.output.mkdir(parents=True, exist_ok=False)
    np, rb = runtime()
    lib, path = library(rb)
    cpu = lib.GetNativeCPUType()
    assert cpu == 3, 'SSE/AVX2/AVX512 diagnostic requires recorded AVX512 host'
    manifest = dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
        run_id=args.output.name, machine='node-0', platform=platform.platform(), python=sys.version,
        Rbeast=importlib.metadata.version('Rbeast'), numpy=np.__version__, native_cpu_type=cpu,
        native_binary_sha256=sha(path.read_bytes()), affinity=sorted(os.sched_getaffinity(0)),
        fixed_cpu=min(os.sched_getaffinity(0)), repetitions=args.count, parameters=PARAMETERS,
        scenarios=list(SCENARIOS), gpu_experiments=False, final_alert=False,
        source_hashes={p:sha((ROOT/p).read_bytes()) for p in ('flash/rbeast_adapter.py','flash/change_detection.py',
                       'tests/m5_real_api.py','tests/m5_replay.py','scripts/m5_repeatability.py')})
    save(args.output/'manifest.json', manifest)
    env = dict(os.environ)
    pinned = dict(env, **{v:'1' for v in THREAD_VARS})
    worker = [sys.executable, str(Path(__file__).resolve())]
    for mode in ('original', 'pinned'):
        for chains in (3, 1):
            for cputype in ('auto', 'SSE', 'AVX2', 'AVX512'):
                label = '%s-c%d-%s' % (mode, chains, cputype)
                for process_mode in ('same', 'fresh'):
                    count = args.count if process_mode == 'same' else 1
                    for repeat in range(1 if process_mode == 'same' else args.count):
                        output = args.output/'reference'/label/process_mode/('%02d.json'%repeat)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        command = worker+['reference','--output',str(output),'--chains',str(chains),
                                          '--cpu',cputype,'--count',str(count)]
                        if mode == 'pinned': command+=['--pinned']
                        execute(command, output, pinned if mode == 'pinned' else env, 60)
                    print(label, process_mode, 'completed', flush=True)
    execute(worker+['rng','--output',str(args.output/'rng.json')], args.output/'rng.json', pinned,30)
    for scenario in SCENARIOS:
        for repeat in range(args.count):
            output = args.output/'decisions'/scenario/('%02d'%repeat)
            execute(worker+['decision','--scenario',scenario,'--output',str(output)],output,pinned,120)
            print('decision',scenario,repeat+1,'completed',flush=True)
    print('M5-R CPU measurement complete; strict assertions evaluated separately',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('suite','reference','fit','decision','rng'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--chains', type=int, choices=(1,3), default=3)
    parser.add_argument('--cpu', choices=('auto','SSE','AVX2','AVX512'), default='auto')
    parser.add_argument('--pinned', action='store_true')
    parser.add_argument('--scenario', choices=SCENARIOS)
    args = parser.parse_args()
    if args.mode == 'suite': suite(args)
    elif args.mode == 'reference': reference_worker(args)
    elif args.mode == 'decision': decision_worker(args)
    elif args.mode == 'rng': rng_worker(args)
    else: save(args.output, native_fit(json.load(sys.stdin), PARAMETERS))


if __name__ == '__main__':
    main()
