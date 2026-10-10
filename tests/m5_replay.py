"""Real Rbeast prefix equivalence and all output structure checks."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import IterationRecord
from flash.change_detection import prefix_replay

results=Path(sys.argv[1]);fixture=Path('tests/m5_fixtures/records/sustained.json')
rows=[IterationRecord(**r) for r in json.loads(fixture.read_text())['records']]
full=json.loads((results/'sustained.json').read_text())['decisions']
short=prefix_replay(rows[:24]);assert full[:24]==short
for file in results.glob('*.json'):
 data=json.loads(file.read_text())
 for k,d in enumerate(data['decisions'],1):
  assert d['final_alert'] is False
  if 'input' not in d:continue
  assert len(d['input'])==k or not d['input']
  assert all(r['iteration']<=d['latest_iteration'] for r in d['input']) if d['status']!='INVALID_INPUT' else True
  if d.get('engine',{}):
   e=d['engine'];assert e['status']=='OK', (file.name,k,e.get('reason'))
   p=d['preprocessing'];assert len(p['values_ms'])<=30
   assert e['raw']['time']==list(range(1,len(p['values_ms'])+1))
   for i,it in enumerate(p['index0_to_iteration']):assert p['iteration_to_index0'][str(it)]==i
print('real prefix equivalence and output invariants PASS')
