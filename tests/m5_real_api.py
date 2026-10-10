"""UPSTREAM real Rbeast API contract, CPU only. Requires approved dependencies."""
import importlib.metadata
import inspect
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import Rbeast as rb
from flash.rbeast_adapter import PARAMETERS,json_safe,candidates_from_raw

p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False)
assert importlib.metadata.version('Rbeast')=='0.1.25'
assert np.__version__=='2.2.6'
sig=inspect.signature(rb.beast)
assert 'mcmc_burbin' in sig.parameters and 'mcmc_burnin' not in sig.parameters
values=np.array([100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)])
results=[]
for start in [1,1,101]:
 params=dict(PARAMETERS,start=start)
 out=json_safe(rb.beast(values,**params));results.append(out)
(p/'raw-before-assertions.json').write_text(json.dumps(results,indent=2)+'\n')
assert results[0]==results[1], 'seeded result not reproducible'
assert results[0]['time']==list(range(1,31))
assert results[2]['time']==list(range(101,131))
a=results[0]['trend'];b=results[2]['trend']
assert all(y==x+100 for x,y in zip(a['cp'],b['cp']) if x is not None)
assert a['cpPr']==b['cpPr']
assert a['cp'][0]==16, 'reference step coordinate differs'
assert candidates_from_raw(results[0],30)[0]['index0']==15
(p/'contract.json').write_text(json.dumps(dict(status='PASS',signature=str(sig),parameters=PARAMETERS,versions=dict(Rbeast=importlib.metadata.version('Rbeast'),numpy=np.__version__,python=sys.version),input=values.tolist(),raw=results,coordinate_verified='time coordinate cp with start/deltat; cp-1 when start1',probability_fields='cpPr localized vs cpOccPr per-time; not run-length posterior'),indent=2)+'\n')
print('real CPU API contract PASS')
