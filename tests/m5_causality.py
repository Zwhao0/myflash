"""Real native input audit; output repeatability has its own unchanged FAIL test."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import IterationRecord
from flash.change_detection import prefix_replay
from flash.rbeast_adapter import RbeastAdapter

class NativeAudit:
    def __init__(self):self.calls=[];self.native=RbeastAdapter()
    def analyze(self,values):
        self.calls.append(values[:]);return self.native.analyze(values)

rows=[IterationRecord(**r) for r in json.loads(Path('tests/m5_fixtures/records/sustained.json').read_text())['records']]
a,b=NativeAudit(),NativeAudit()
full=prefix_replay(rows,a);short=prefix_replay(rows[:24],b)
assert a.calls[:len(b.calls)]==b.calls
for k,d in enumerate(full,1):
 assert d['input']==[__import__('dataclasses').asdict(r) for r in rows[:k]]
 if d.get('engine'):
  assert d['engine']['status']=='OK',(k,d['engine'].get('reason'))
  assert d['engine']['raw']['time']==list(range(1,len(d['preprocessing']['values_ms'])+1))
assert all(not d['final_alert'] for d in full)
Path(sys.argv[1]).write_text(json.dumps(dict(status='PASS',native_calls_full=len(a.calls),native_calls_prefix=len(b.calls),full=full,short=short,input_prefix_identical=True,output_repeatability='FAIL separate test; not assumed'),indent=2)+'\n')
print('real native input prefix causality PASS')
