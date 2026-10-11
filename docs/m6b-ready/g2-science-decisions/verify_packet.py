"""EXTENSION: read-only fixed historical audit; standard library, no detector/native import.
Run: python3 docs/m6b-ready/g2-science-decisions/verify_packet.py --output <new private path>
No fitting or formal scientific rule implementation. Fails on original assertion mismatch.
"""
import argparse,ast,json,hashlib,math,statistics,platform,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);arg=p.parse_args()
 root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
 load=lambda p:json.loads((root/p).read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
 packet=json.loads((out/'SCIENTIFIC_DECISIONS.json').read_text());assert packet['final_alert'] is False
 assert set(packet['decisions'])=={'G01','G02','G13'}
 for x in packet['decisions'].values():
  assert x['approved'] is None and x['required_owner_approval'] is True
  assert x['recommended'] in [v['id'] for v in x['options']]
  assert all(v['approved'] is None for v in x['options'])
 tree=ast.parse((root/'flash/rbeast_adapter.py').read_text());n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PARAMETERS' for t in n.targets));parameters={k.arg:ast.literal_eval(k.value) for k in n.value.keywords};assert len(parameters)==24 and parameters==packet['decisions']['G01']['parameters']
 expected=load('docs/m5/science-s1/data/timeline-summary.json')['summary'];summary_lookup={(s['batch'],s['scenario']):s for s in expected}
 timeline=load('docs/m5/science-s1/data/timeline.json');timeline_lookup={(s['batch'],s['scenario']):s['prefixes'] for s in timeline}
 coverage=load('docs/m5/science-s1/data/repeat-coverage.json');assert len(coverage)==280
 ledger={};counts=dict(replays=0,prefixes=0,candidates=0,independent_first_replay_prefixes=0);scenario_results=[]
 config=dict(window=30,thresh_prob=0.8,degradation_thresh=0.2,warmup=3,zscore=3.0,spacing=2,recovery=0.75)
 rules=['span_inclusive_gt20','elapsed_exclusive_gt20','retained_right_gt20','qualified_consecutive_prefixes_gt20','right_guard_original_k1','right_guard_original_k2']
 for batch in ['m5-p1-c-batch01','m5-p1-c-batch02']:
  for scenario in ['stable','sustained','growth_19','growth_20','growth_21','spike','recovery']:
   file='docs/m5/patch-p1/data/'+batch+'/decisions-'+scenario+'.json';blob=(root/file).read_bytes();ledger[file]=sha(blob);doc=json.loads(blob);assert doc['scenario']==scenario and len(doc['replays'])==20
   fixturefile='tests/m5_fixtures/records/'+scenario+'.json';fixture=load(fixturefile)
   # Fixtures are lists of serialized IterationRecord; no evaluator/ground truth read.
   if isinstance(fixture,dict):fixture=fixture['records']
   ledger[fixturefile]=sha((root/fixturefile).read_bytes());assert len(fixture)==45
   first=doc['replays'][0]['decisions'];assert len(first)==45
   for replay in doc['replays']:
    decisions=replay['decisions'];assert decisions==first
    for i,d in enumerate(decisions,1):
     assert d['input']==fixture[:i] and d['latest_iteration']==i and d['final_alert'] is False and d['config']==config
     if d['engine'] is not None:assert d['engine']['parameters']==parameters
     counts['prefixes']+=1
    counts['replays']+=1
   for item in [c for c in coverage if c['batch']==batch and c['scenario']==scenario]:assert item['source_sha256']==sha(blob)
   streak={};firstprob=None;firstpre=None;firstF=dict(A=None,B=None);firstRules={F:{r:None for r in rules} for F in ['A','B']};disagree=[]
   for t,d in enumerate(first,1):
    counts['independent_first_replay_prefixes']+=1
    window=fixture[:t][-30:];eligible=[r for r in window if r['iteration']>3];v=[r['iteration_time_ms'] for r in eligible]
    m=statistics.fmean(v) if v else None;std=statistics.pstdev(v) if v else None
    kept=[r for r in eligible if std==0 or abs((r['iteration_time_ms']-m)/std)<=3]
    prepared=d['preprocessing'];values=[r['iteration_time_ms'] for r in kept];mapping=[r['iteration'] for r in kept]
    assert values==prepared['values_ms'] and mapping==prepared['index0_to_iteration']
    if len(values)<8 or len(set(values))<=1:assert not d['candidates']
    else:assert d['engine']['status']=='OK'
    native=d['engine']['raw']['trend'] if d['engine'] and d['engine']['status']=='OK' else None
    if native:
     assert len(native['cp'])==len(native['cpPr']) and len(native['cpOccPr'])==len(values)
     assert all(type(q) in (float,int) and math.isfinite(q) and 0<=q<=1 for q in native['cpOccPr'])
    prev=None;qualified={'A':[], 'B':[]};gate_triggers={F:{r:[] for r in rules} for F in ['A','B']};probcp=[];precp=[];active=set()
    for c in d['candidates']:
     counts['candidates']+=1
     if c['reason']=='PADDED_SLOT':continue
     i=c['index0'];j=mapping[i];assert c['iteration']==j
     assert native['cp'][c['slot']]==c['cp'] and native['cpPr'][c['slot']]==c['cpPr']
     prob=c['cpPr']>=0.8;spacing=prev is None or j-prev>=2
     assert prob==c['stages']['probability']['passed'] and spacing==c['stages']['spacing']['passed']
     if prob and spacing:prev=j
     left,right,recent=values[:i],values[i:],values[i+1:]
     b=statistics.fmean(left) if left else None;dv=statistics.fmean(right) if right else None;rv=statistics.fmean(recent) if recent else None
     assert (b,dv,rv)==tuple(c['statistics'][k] for k in ['baseline_mean','degraded_mean','recent_mean'])
     delta=None if b is None or dv is None else dv-b
     rec=None if not left or not recent or delta==0 else (dv-rv)/delta
     assert rec==c['stages']['recovery']['value']
     A=None if not b else delta/b;B=None if not dv or delta is None else delta/dv
     assert A==c['stages']['degradation']['duration_growth'] and B==c['stages']['degradation']['throughput_loss']
     if prob:probcp.append(j);firstprob=t if firstprob is None else firstprob
     pre=prob and spacing and rec is not None and rec<0.75 and delta>0
     if pre:precp.append(j);firstpre=t if firstpre is None else firstpre
     for F,q in [('A',A),('B',B)]:
      passed=pre and q is not None and q>0.2
      key=(F,j)
      streak[key]=streak.get(key,0)+1 if passed else 0
      active.add(key)
      if passed:
       qualified[F].append(j);firstF[F]=t if firstF[F] is None else firstF[F]
      gates=[t-j+1>20,t-j>20,len(right)>20,streak[key]>20,t-j>=1,t-j>=2]
      for r,g in zip(rules,gates):
       if passed and g:
        gate_triggers[F][r].append(j);firstRules[F][r]=t if firstRules[F][r] is None else firstRules[F][r]
    for key in list(streak):
     if key not in active:streak[key]=0
    h=timeline_lookup[batch,scenario][t-1]
    assert h['provisional_cp']==qualified and h['persistence_triggers']==gate_triggers
    assert h['probability_qualified_cp']==probcp and h['pre_intensity_filter_cp']==precp
    if bool(qualified['A'])!=bool(qualified['B']):disagree.append(t)
   e=summary_lookup[batch,scenario]
   assert firstprob==e['first_probability_iteration'] and firstpre==e['first_pre_intensity_filter_iteration']
   assert firstF==e['first_provisional_iteration'] and firstRules==e['first_persistence_rule_iteration']
   assert disagree==e['provisional_disagreement_iterations']
   assert e['final_alert'] is False and e['final_alert_iteration'] is None
   scenario_results.append(dict(batch=batch,scenario=scenario,first_probability=firstprob,first_provisional=firstF,first_persistence=firstRules,disagreement=disagree))
 for path in ['docs/m5/science-s1/data/timeline.json','docs/m5/science-s1/data/timeline-summary.json','docs/m5/science-s1/data/sensitivity.json','docs/m5/science-s1/data/repeat-coverage.json']:
  ledger[path]=sha((root/path).read_bytes())
 from fractions import Fraction
 bounds=json.loads((out/'THRESHOLD_BOUNDARIES.json').read_text());assert [x['degraded_ms'] for x in bounds]==[119,120,121,125,126]
 for x in bounds:
  a=Fraction(x['degraded_ms']-100,100);b=Fraction(x['degraded_ms']-100,x['degraded_ms']);assert x['A_pass']==(a>Fraction(1,5)) and x['B_pass']==(b>Fraction(1,5));assert x['A']==float(a) and x['B']==float(b)
 result=dict(status='PASS_LOCAL_STATIC_HISTORICAL_ARITHMETIC_ONLY',source_head=packet['baseline']['head'],source_tree=packet['baseline']['tree'],host_class='local macOS CPU',python=sys.version,platform=platform.platform(),counts=counts,inputs_sha256=ledger,results=scenario_results,native_fits=0,GPU_experiments=0,final_alert=False,scientific_status='NOT_APPROVED')
 arg.output.parent.mkdir(parents=True,exist_ok=True);arg.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(status=result['status'],counts=counts,native_fits=0)))
if __name__=='__main__':main()
