"""ADAPTATION diagnostic unit checks; never native/GPU experiment evidence."""
import base64
import copy
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.m5_p1_compare import compare,receipt_errors,validate_fit,numeric_digest
from scripts.m5_p1_diagnostic import canonical,sha,integer_reference
from flash.rbeast_adapter import candidates_from_raw

data=struct.pack('<dd',0.0,float('nan'))
fit=dict(raw=dict(x=[0.0,None],trend=dict(cp=[1],cpPr=[.9],cpOccPr=[.1,.2])),arrays={'x':dict(dtype='<f8',shape=[2],bytes_base64=base64.b64encode(data).decode(),sha256=sha(data))},
    input=[1.,2.],input_dtype='<f8',input_shape=[2],input_sha256=sha(struct.pack('<dd',1.,2.)),parameters={},native_binary_sha256='binary',
    candidate_validation='PASS',candidate_validation_error=None,dispatch=dict(cpu_current=3,seed_function='avx512_pcg_set_seed'))
fit.update(raw_json_sha256=sha(canonical(fit['raw'])),posterior_bytes_sha256=sha(canonical(fit['arrays'])))
assert compare(fit,copy.deepcopy(fit))['equal']
changed=copy.deepcopy(fit);changed.update(pid=123,elapsed_s=9.,private_path='<path>')
assert numeric_digest(fit)==numeric_digest(changed)
for mutate in ('missing','shape','signed_zero','nan_payload','raw_field'):
    other=copy.deepcopy(fit)
    if mutate=='missing':other['arrays'].pop('x')
    elif mutate=='shape':other['arrays']['x']['shape']=[1,2]
    elif mutate=='signed_zero':other['arrays']['x']['bytes_base64']=base64.b64encode(struct.pack('<d',-0.)+data[8:]).decode()
    elif mutate=='nan_payload':other['arrays']['x']['bytes_base64']=base64.b64encode(data[:8]+struct.pack('<Q',0x7ff8000000000001)).decode()
    else:other['raw']['extra']=1
    assert not compare(fit,other)['equal'],mutate
assert not validate_fit(fit,'binary',[1.,2.],{})
illegal=copy.deepcopy(fit);illegal['candidate_validation_error']='invalid cpOccPr';illegal['candidate_validation']='FAIL'
assert 'native_validation' in validate_fit(illegal,'binary',[1.,2.],{})
for key,value in [('cpPr',[1.01]),('cpOccPr',[1.01,.2])]:
    raw=copy.deepcopy(fit['raw']);raw['trend'][key]=value
    try:
        c=candidates_from_raw(raw,2);assert any(x['reason']=='INVALID_PROBABILITY' for x in c)
    except ValueError:pass
assert receipt_errors(dict(exit_code=124,timeout=True))
assert receipt_errors(dict(exit_code=-11,timeout=False))
assert not receipt_errors(dict(exit_code=0,timeout=False))
r=integer_reference(20261010+0x4f352a3dc)
assert r['state512'][0]==9765033702070386375
assert r['output'][:4]==[4050055311,3378167518,714449352,2232581618]
assert len(integer_reference(0)['output'])==64
print('P1 exact comparator/invalid-output/timeout/reference unit checks PASS; not native experiment')
