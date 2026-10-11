"""Read-only prerequisite-native audit; no fit or assertion modification."""
from pathlib import Path
import json,sys,math
run=Path(__file__).resolve().parent;repo=run/'checkout';out=run/'execution01'
sys.path.insert(0,str(repo))
from scripts.m5_p1_compare import validate_fit
from flash.rbeast_adapter import PARAMETERS
errors=[];checked=0
def probability(raw,where):
    global checked
    checked+=1
    values=raw['trend']['cpOccPr']
    for i,v in enumerate(values):
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not 0<=v<=1:
            errors.append(dict(file=where,index=i,reason='INVALID_cpOccPr'))
auto=json.loads((out/'auto-path-fit.json').read_text())
values=[100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)]
problems=validate_fit(auto,'1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb',values,PARAMETERS)
if problems:errors.append(dict(file='auto-path-fit.json',errors=problems))
probability(auto['raw'],'auto-path-fit.json')
for file in ('api/raw-before-assertions.json','field-contract/raw.json'):
    for i,raw in enumerate(json.loads((out/file).read_text())):probability(raw,file+':'+str(i))
full=json.loads((out/'replay/sustained.json').read_text())['decisions']
capture=json.loads((out/'prefix-capture.json').read_text())
for name,rows in [('full',full),('short',capture['short'])]:
    for i,row in enumerate(rows):
        if row.get('engine') and row['engine'].get('raw'):
            probability(row['engine']['raw'],name+':'+str(i+1))
result=dict(status='PASS' if not errors else 'FAIL',actual_prerequisite_native_raw_trees=checked,
            fit_count_added_by_this_audit=0,errors=errors,original_parser_used_for_auto_fit=True,
            cpOccPr_check='finite numeric in original legal [0,1] range; includes translated-coordinate API outputs')
(run/'native-gate-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert not errors
