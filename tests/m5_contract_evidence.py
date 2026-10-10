"""ADAPTATION arithmetic and invalid-return evidence; NEVER native detector PASS."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.change_detection import DetectionConfig,filter_candidates
from flash.rbeast_adapter import candidates_from_raw
cases=[('sustained',[10,10,20,20,20],[3]),('recovery_boundary',[10,10,35,12.5,12.5],[3]),('right_endpoint',[10,10,20],[3]),('zero_denominator',[10,10,10,10],[3]),('adjacent',[10,10,20,30,30],[3,4]),('spacing_two',[10,10,20,20,30,30],[3,5])]
result=[]
for name,values,coordinates in cases:
 raw={'time':list(range(1,len(values)+1)),'trend':{'cp':coordinates,'cpPr':[.9]*len(coordinates),'cpOccPr':[0]*len(values)}}
 candidates=candidates_from_raw(raw,len(values));prepared={'values_ms':values,'index0_to_iteration':list(range(4,4+len(values)))}
 filtered=filter_candidates(prepared,candidates,len(values)+3,DetectionConfig())
 result.append(dict(case=name,input_ms=values,raw_fixture=raw,mapping=prepared['index0_to_iteration'],evidence=filtered,classification='UNIT_ARITHMETIC_NOT_NATIVE_EXECUTION'))
 if name=='recovery_boundary':assert filtered[0]['stages']['recovery']['value']==.75 and filtered[0]['reason']=='TRANSIENT_RECOVERY'
 if name=='right_endpoint':assert filtered[0]['status']=='INSUFFICIENT_EVIDENCE'
 if name=='adjacent':assert filtered[1]['reason']=='ADJACENT_CHANGEPOINT'
for raw in json.loads(Path('tests/m5_fixtures/native_invalid.json').read_text()):
 try:
  parsed=candidates_from_raw(raw,8);assert any(r['reason'] for r in parsed)
  result.append(dict(raw_fixture=raw,parser_evidence=parsed,classification='INVALID_RETURN_UNIT_FIXTURE'))
 except ValueError as error:result.append(dict(raw_fixture=raw,reason=str(error),classification='INVALID_RETURN_UNIT_FIXTURE'))
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print('arithmetic/invalid-return evidence PASS (not native Rbeast execution)')
