"""EXTENSION separate synthetic evaluator; detector never imports this module.
Metrics concern window candidates, not complete FLASH alert accuracy.
"""
import argparse
import json
from pathlib import Path


def evaluate(result, truth):
    decisions=result['decisions'];onset=truth['onset_iteration'];tol=truth['matching_tolerance_iterations']
    probability=[];duration=[];throughput=[]
    for d in decisions:
        for c in d.get('candidates',[]):
            if c.get('stages',{}).get('probability',{}).get('passed'):
                probability.append((d['latest_iteration'],c['iteration']))
            if c.get('provisional_duration_candidate'):duration.append((d['latest_iteration'],c['iteration']))
            if c.get('provisional_throughput_candidate'):throughput.append((d['latest_iteration'],c['iteration']))
    row=dict(**truth,probability_candidate_decisions=len(probability),normal_pseudo_candidates=len(probability) if onset is None else None,
             final_alerts=0,classification='synthetic-window-evidence-not-FLASH-accuracy')
    for name,events in [('probability',probability),('duration_assumption',duration),('throughput_assumption',throughput)]:
        matched=[k for k,cp in events if onset is not None and abs(cp-onset)<=tol and k>=onset]
        first=min(matched) if matched else None
        row[name]=dict(first_any_candidate_iteration=min((k for k,_ in events),default=None),
                       first_matched_candidate_iteration=first,delay_iterations=first-onset if first else None,
                       missed=onset is not None and not matched,
                       pseudo_candidate_decisions=sum(onset is None or abs(cp-onset)>tol for k,cp in events))
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    truth=json.loads(a.truth.read_text())
    out={name:evaluate(json.loads((a.results/(name+'.json')).read_text()),event) for name,event in truth.items()}
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'scenarios':len(out),'final_alerts':0}))

if __name__=='__main__':main()
