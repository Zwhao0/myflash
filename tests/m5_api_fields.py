"""Real native field contract, independent of failed full-output repeatability test."""
import inspect
import importlib.metadata
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import Rbeast as rb
from flash.rbeast_adapter import PARAMETERS,json_safe,candidates_from_raw
p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False)
values=np.array([100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)])
raw=[json_safe(rb.beast(values,**dict(PARAMETERS,start=s))) for s in [1,101]]
(p/'raw.json').write_text(json.dumps(raw,indent=2)+'\n')
assert raw[0]['time']==list(range(1,31))
assert raw[1]['time']==list(range(101,131))
assert raw[0]['trend']['cp'][0]==16 and raw[1]['trend']['cp'][0]==116
parsed=candidates_from_raw(raw[0],30)
assert parsed[0]['index0']==15
assert len(raw[0]['trend']['cpOccPr'])==30
assert len(raw[0]['trend']['cp'])==len(raw[0]['trend']['cpPr'])
(p/'contract.json').write_text(json.dumps(dict(status='PASS',signature=str(inspect.signature(rb.beast)),parameters=PARAMETERS,versions=dict(Rbeast=importlib.metadata.version('Rbeast'),numpy=np.__version__,python=sys.version),input=values.tolist(),parsed=parsed,coordinate='time cp-1 when start1/deltat1',repeatability='FAIL in separate unchanged test; field contract does not assert repeatability'),indent=2)+'\n')
print('real Rbeast coordinate/field contract PASS; repeatability separate FAIL')
