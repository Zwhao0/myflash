"""ADAPTATION: fixed privacy whitelist, full latency samples, alias replay equality."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flash.localization import analyze,cv,rank_scores
from flash.profile_input import validate_bundle,InputError


def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--core',required=True);p.add_argument('--five');a=p.parse_args()
    public=ROOT/'docs/m4/supplement';public.mkdir(parents=True,exist_ok=True)
    private=ROOT/'runs/m4-supplement-access'
    experiment_base=json.loads((private/'baseline.json').read_text())
    base=json.loads((private/'publication-baseline.json').read_text()) if (private/'publication-baseline.json').exists() else experiment_base
    preserved=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in base['hashes'].items());assert preserved
    suites=[a.core]+([a.five] if a.five else [])
    bundles=[];results=[];all_hashes=set();digests=[];receipts=[]
    for suite_id in suites:
        suite=json.loads((ROOT/'runs'/suite_id/'suite.json').read_text());assert suite['status']=='PASS'
        for row in suite['runs']:
            run=row['run_id'];node=ROOT/'runs'/run/'node-0'
            v=json.loads((node/'verification.json').read_text())
            post=json.loads((ROOT/'runs'/run/'postflight.json').read_text());assert post['status']=='PASS'
            clean=json.loads((node/'cleanup.json').read_text());assert clean['status']=='PASS'
            control=json.loads((ROOT/'runs'/run/'control.json').read_text())
            receipts.append(dict(run_id=run,exit_codes=[x['exit_code'] for x in control['commands']],postflight='PASS',removed_shm=len(clean['removed']),already_absent=len(clean['already_absent'])))
            assert all(x==0 for x in receipts[-1]['exit_codes'])
            current=set(v['windows'][0]['prediction']['groups']);assert not current & all_hashes;all_hashes.update(current)
            assert set(v['windows'][1]['prediction']['groups'])==current
            for w in v['windows']:
                epoch=w['epoch'];b=json.loads((node/f'analysis-epoch{epoch}/input.json').read_text())
                original=json.loads((node/f'analysis-epoch{epoch}/prediction.json').read_text())
                for r in b['records']:r['process_instance']='rank'+str(r['global_rank'])
                for decl in b['communicators']:
                    for local in decl['local_instances']:local['process_instance']='rank'+str(local['global_rank'])
                prediction=analyze(b)
                for group in original['groups'].values():
                    for local in group['local_communicators']:local['process_instance']='rank'+str(local['global_rank'])
                original.pop('source_audit',None)
                assert prediction==original,'public/private statistical mismatch'
                for audit in w['source_audit']:
                    digests.append(dict(run_id=run,epoch=epoch,sha256=audit['sha256'],source_records=audit['source_records'],selected_records=audit['selected_records']))
                bundles.append(b)
                evaluation=w['evaluator']
                evaluation={k:v for k,v in evaluation.items() if k!='entry_intervals'} | dict(entry_skew_ms=[x['entry_skew_ms'] for x in evaluation['entry_intervals']])
                runtime=sorted({(r['family'],r['encoded']) for rank in v['runtime'] for r in rank['versions']})
                group_rank_sensitivity={}
                for h,g in prediction['groups'].items():
                    means={c['global_rank']:c['avg_latency_us'] for c in g['local_communicators']}
                    group_rank_sensitivity[h]=dict(cv=cv(list(means.values())),rank_scores=rank_scores(means),rank_means_us=means,local_samples={str(c['global_rank']):c['sample_count'] for c in g['local_communicators']})
                results.append(dict(all_group_rank_sensitivity=group_rank_sensitivity,run_id=run,layout=v['layout'],repetition=row['repetition'],epoch=epoch,evaluator=evaluation,prediction=prediction,integrity=v['integrity'],isolation=w['epoch'],
                    memory_mib=v['memory_mib'],runtime_versions=[dict(family=f,encoded=n) for f,n in runtime],torch=v['torch'],torch_build_cuda=v['torch_build_cuda'],gpu_name=v['gpu_name']))
    # Real cross-run / cross-epoch replacement rejected, plus original per-window mutations.
    pollution=[]
    for name,source in [('other_epoch',bundles[1]),('other_run',bundles[2])]:
        b=copy.deepcopy(bundles[0]);b['records'][0]=copy.deepcopy(source['records'][0])
        try:validate_bundle(b)
        except InputError as error:pollution.append(dict(kind=name,rejected=True,reason=str(error)))
        else:raise AssertionError('real cross-context contamination accepted')
    save(public/'samples.json',dict(schema_version=1,bundles=bundles,interpretation='all 10 predetermined Profile samples per rank/communicator/epoch, exact measured us; process identity aliases only'))
    save(public/'results.json',dict(scope='M4 real controlled CPU lateness supplement',results=results))
    delayed=[r for r in results if r['layout']=='core' and r['evaluator']['truth_ranks']]
    normal=[r for r in results if r['layout']=='core' and not r['evaluator']['truth_ranks']]
    summary=dict(status='PASS',base_main=experiment_base['base'],publication_main=base['base'],protected_files=len(base['hashes']),protected_sha_equal=preserved,windows=len(results),profile_records=sum(len(b['records']) for b in bundles),unique_communicators=len(all_hashes),
        conditional_core_windows=len(delayed),stage1_matches=sum(r['evaluator']['stage1_match'] for r in delayed),stage2_matches=sum(r['evaluator']['stage2_match'] for r in delayed),normal_core_windows=len(normal),normal_core_candidates=sum(r['evaluator']['normal_candidate'] for r in normal),
        aliases_preserve_all_statistics=True,real_cross_context_rejections=pollution,raw_audit=digests,receipts=receipts,precheck=json.loads((private/'precheck.json').read_text()),probe_sha256=json.loads((private/'inventory.json').read_text())['probe_sha256'],
        G04='OPEN',final_fault_ranks=[],interpretation='conditional ordering evidence; not full FLASH automatic precision/recall; 20% filter remains unresolved/disabled, dual weights/std unchanged')
    save(public/'validation.json',summary)
    save(private/'export-receipt.json',dict(command=sys.argv,exit_code=0,output_files=[str(q) for q in sorted(public.iterdir())],public_sha256={q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in public.iterdir() if q.is_file()}))
    print(json.dumps({k:summary[k] for k in ['status','windows','profile_records','unique_communicators','stage1_matches','stage2_matches','normal_core_candidates','protected_files']}))


if __name__=='__main__':main()
