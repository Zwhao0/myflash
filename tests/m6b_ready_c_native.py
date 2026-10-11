"""EXTENSION bounded real CPU detect -> worker opt-in and restoration evidence.
Run with the existing formal interpreter. Output directory must be new.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.change_detection import detect
from flash.iteration_reporter import IterationRecord
from flash.rbeast_adapter import CANDIDATE_C_SHA256, PARAMETERS, RbeastAdapter

ORIGINAL='a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157'
p=argparse.ArgumentParser()
p.add_argument('--candidate-python',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
values=[100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)]
records=[IterationRecord('task03-cpu',0,i,v,'2026-10-11T00:00:00+00:00','synthetic','task03',False) for i,v in enumerate(values,1)]
rows={}
for name,adapter,sha,selection in [
        ('default_before',None,ORIGINAL,'default'),
        ('candidate_c',RbeastAdapter(candidate_c_python=a.candidate_python),CANDIDATE_C_SHA256,'candidate-c-opt-in'),
        ('wrong_binary',RbeastAdapter(candidate_c_python=sys.executable),ORIGINAL,None),
        ('default_restored',None,ORIGINAL,'default')]:
    result=detect(records,adapter=adapter)
    (a.output/(name+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    engine=result['engine'];identity=engine['runtime_identity']
    assert not result['final_alert']
    assert engine['parameters']==PARAMETERS
    assert identity['native_sha256']==sha and identity['mapped_library_lines']
    assert identity['sys_executable']==(a.candidate_python if name=='candidate_c' else sys.executable)
    if name=='wrong_binary':
        assert result['status']=='BLOCKED' and result['reason']=='CANDIDATE_C_IDENTITY_REJECTED'
        assert engine['worker_exit_code']==78 and not engine['native_fit_started'] and engine['raw'] is None
    else:
        assert engine['status']=='OK' and engine['worker_exit_code']==0 and engine['native_fit_started']
        assert engine['runtime_selection']==selection
        assert len(engine['raw']['trend']['cpOccPr'])==len(result['preprocessing']['values_ms'])
    rows[name]=dict(status=result['status'],worker_exit_code=engine['worker_exit_code'],
        runtime_identity=identity,native_fit_started=engine['native_fit_started'],final_alert=result['final_alert'],
        output_sha256=hashlib.sha256((a.output/(name+'.json')).read_bytes()).hexdigest())
for key in ('sys_executable','sys_prefix','Rbeast_file','native_module','native_file','native_sha256'):
    assert rows['default_before']['runtime_identity'][key]==rows['default_restored']['runtime_identity'][key]
# Original binary's historical full posterior FAIL is not tested or reclassified.
(a.output/'validation.json').write_text(json.dumps(dict(status='PASS_CONTROLLED_CPU_OPT_IN',
    native_fits=3,wrong_binary_rejections=1,parameters=PARAMETERS,calls=rows),indent=2)+'\n')
print('real CPU detect/worker: C opt-in, wrong .so rejection, default restoration PASS; native fits=3')
