"""ADAPTATION: full exact output comparator and independent artifact ledger.

Identity metadata is not part of the numerical digest. Raw logical tree and all
ndarray fields/dtypes/shapes/bytes are. Original strict tests stay untouched.
"""
import argparse
import base64
import copy
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.m5_p1_diagnostic import canonical,sha,save,SCENARIOS
from flash.rbeast_adapter import PARAMETERS,candidates_from_raw,json_safe
from flash.change_detection import preprocess, DetectionConfig
from flash.iteration_reporter import IterationRecord


def difference(a,b,path=''):
    """First difference, including type/field/NaN/signed-zero changes."""
    if type(a)!=type(b):return dict(path=path,kind='type',left_type=type(a).__name__,right_type=type(b).__name__)
    if isinstance(a,dict):
        if set(a)!=set(b):return dict(path=path,kind='fields',missing_left=sorted(set(b)-set(a)),missing_right=sorted(set(a)-set(b)))
        for k in sorted(a):
            d=difference(a[k],b[k],path+'.'+k)
            if d:return d
    elif isinstance(a,list):
        if len(a)!=len(b):return dict(path=path,kind='length',left=len(a),right=len(b))
        for i,(x,y) in enumerate(zip(a,b)):
            d=difference(x,y,path+f'[{i}]')
            if d:return d
    elif isinstance(a,float):
        if struct.pack('>d',a)!=struct.pack('>d',b):return dict(path=path,kind='float_bits',left=a,right=b)
    elif a!=b:return dict(path=path,kind='value',left=a,right=b)
    return None


def numerical(fit):return dict(raw=fit['raw'],arrays=fit['arrays'])


def numeric_digest(fit):return sha(canonical(numerical(fit)))


def compare(a,b):
    d=difference(numerical(a),numerical(b))
    return dict(equal=d is None,first_difference=d)


def validate_fit(fit,expected_binary,values,parameters):
    errors=[]
    for key,want in [('native_binary_sha256',expected_binary),('parameters',parameters),('input',values),
       ('input_dtype','<f8'),('input_shape',[len(values)]),
       ('input_sha256',sha(b''.join(struct.pack('<d',v) for v in values)))]:
        if difference(fit.get(key),want):errors.append(key)
    if fit.get('raw_json_sha256')!=sha(canonical(fit['raw'])):errors.append('raw_digest')
    if fit.get('posterior_bytes_sha256')!=sha(canonical(fit['arrays'])):errors.append('array_digest')
    selected=fit.get('dispatch',{})
    seeders={1:'gen_pcg_set_seed',2:'avx_pcg_set_seed',3:'avx512_pcg_set_seed'}
    if selected.get('seed_function')!=seeders.get(selected.get('cpu_current')) or selected.get('cpu_current') not in seeders:
        errors.append('unknown_or_inconsistent_actual_dispatch')
    import numpy as np
    for field,array in fit['arrays'].items():
        data=base64.b64decode(array['bytes_base64'],validate=True)
        dtype=np.dtype(array['dtype'])
        count=1
        for size in array['shape']:count*=size
        if len(data)!=count*dtype.itemsize or sha(data)!=array['sha256']:errors.append('array_bytes:'+field)
        decoded=json_safe(np.frombuffer(data,dtype=dtype).reshape(array['shape']))
        raw_value=fit['raw']
        try:
            for key in field.split('.'):raw_value=raw_value[int(key)] if isinstance(raw_value,list) else raw_value[key]
            if difference(raw_value,decoded):errors.append('raw_array_reference:'+field)
        except (KeyError,IndexError,ValueError,TypeError):errors.append('raw_array_reference:'+field)
    if fit.get('candidate_validation_error') or fit.get('candidate_validation')!='PASS':errors.append('native_validation')
    try:
        validated=candidates_from_raw(fit['raw'],len(values))
        if any(c['reason'] not in (None,'PADDED_SLOT') for c in validated) and 'native_validation' not in errors:errors.append('native_validation')
        if 'native_candidates' in fit and difference(validated,fit['native_candidates']):errors.append('candidate_validation_reference')
    except ValueError:
        if 'native_validation' not in errors:errors.append('native_validation')
    return errors


def receipt_errors(receipt):
    return [] if receipt.get('exit_code')==0 and receipt.get('timeout') is False else ['worker_failure_or_timeout']


def load(path):return json.loads(path.read_text())


def compact_decision(decision):
    # All decision/filter fields are preserved; raw is separately full-compared.
    d=copy.deepcopy(decision)
    if d.get('engine'):
        d['engine'].pop('raw',None)
        d['engine'].pop('capture_file',None) # File identity, not a numeric field.
    return d


def qualified(d,rule):
    if rule=='probability':
        return sorted(c['iteration'] for c in d['candidates'] if c.get('iteration') is not None
            and c.get('stages',{}).get('probability',{}).get('passed'))
    return sorted(c['iteration'] for c in d['candidates'] if c.get('provisional_'+rule+'_candidate'))


def validate_batch(run,binary,output):
    """Independent expected counts/inputs/bytes and ledger referential checks."""
    protocol=load(ROOT/'docs/m5/patch-p1/protocol.json')
    # Fixed-model field contract from frozen real-API evidence, not a posterior
    # value/label oracle. Prevent uniformly missing capture fields from passing.
    field_contract=load(ROOT/'docs/m5/repeatability/data/reference-original-c3-auto-fresh.json')
    expected_array_fields=set(field_contract['fits'][0]['arrays'])
    assert len(expected_array_fields)==24
    expected=load(run/'expected-run-ledger.json')
    receipts=load(run/'worker-receipts-private.json')
    artifacts=load(run/'artifact-ledger-private.json')
    errors=[]
    manifest=load(run/'manifest.json')
    if manifest['protocol_sha256']!=sha((ROOT/'docs/m5/patch-p1/protocol.json').read_bytes()):errors.append('protocol_hash')
    if manifest['binary_sha256']!=binary:errors.append('manifest_binary')
    recorded={r['path'] for r in artifacts}
    actual={str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p.name!='artifact-ledger-private.json'}
    if recorded!=actual:errors.append('artifact_ledger_fields')
    for item in artifacts:
        p=run/item['path']
        if not p.exists() or p.stat().st_size!=item['size'] or sha(p.read_bytes())!=item['sha256']:errors.append('artifact:'+item['path'])
    if len({x['path'] for x in expected})!=len(expected) or len(receipts)!=len(expected):errors.append('worker_counts')
    expected_cells=[]
    for c in protocol['cells']:
        label=f"{c['affinity']}-c{c['chains']}-{c['requested_cpu']}-{c['process']}"
        expected_cells.extend(f'reference/{label}/{i:02d}' for i in range(1 if c['process']=='same' else 20))
    expected_decisions=[f'decisions/{s}/{i:02d}' for s in SCENARIOS for i in range(20)]
    if {x['path'] for x in expected}!=set(expected_cells+expected_decisions):errors.append('expected_ledger_protocol')
    receipt_map={r['path']:r for r in receipts}
    reference={};reference_workers={};decision_groups={s:[] for s in SCENARIOS}
    fit_count=0;prefix_count=0;array_count=0;native_errors=0
    fit_errors=[]
    for item in expected:
        if receipt_errors(receipt_map.get(item['path'],{})):errors.append('receipt:'+item['path'])
        directory=run/item['path']
        files=sorted(directory.glob('fit-*.json'));files=[p for p in files if '.command.' not in p.name]
        if len(files)!=item['expected_fits']:errors.append('fit_count:'+item['path'])
        fits=[load(p) for p in files];fit_count+=len(fits)
        for fit in fits:
            if set(fit['arrays'])!=expected_array_fields:errors.append('array_field_contract:'+item['path'])
        if item['kind']=='reference':
            c=item['cell'];params=dict(PARAMETERS,mcmc_chains=c['chains'])
            worker_path=directory/'worker.json'
            if not worker_path.exists():errors.append('missing_worker_metadata:'+item['path'])
            else:
                worker=load(worker_path)
                if worker['count']!=item['expected_fits']:errors.append('worker_fit_count:'+item['path'])
                if c['affinity']=='pinned' and (len(worker['affinity'])!=1 or any(x!='1' for x in worker['thread_environment'].values())):
                    errors.append('pinned_controls:'+item['path'])
                reference_workers.setdefault(directory.parent.name,[]).append(dict(path=item['path'],**worker))
            if c['requested_cpu']!='auto':params['cputype']=c['requested_cpu']
            values=[100+(i%3)*.2+(30 if i>=15 else 0) for i in range(30)]
            for fit in fits:
                problems=validate_fit(fit,binary,values,params);array_count+=len(fit['arrays'])
                native_errors+=int('native_validation' in problems)
                if problems:fit_errors.append(dict(path=item['path'],errors=problems))
            key=directory.parent.name;reference.setdefault(key,[]).extend(fits)
        else:
            s=item['scenario'];fixture=ROOT/'tests/m5_fixtures/records'/f'{s}.json'
            rows=[IterationRecord(**r) for r in load(fixture)['records']]
            d=load(directory/'decisions.json');prefix_count+=len(d['decisions'])
            if sha(fixture.read_bytes())!=protocol['fixture_hashes'][s] or d['fixture_sha256']!=protocol['fixture_hashes'][s]:errors.append('fixture_hash:'+item['path'])
            if len(d['decisions'])!=45:errors.append('prefix_count:'+item['path'])
            mapped={p.name:f for p,f in zip(files,fits)}
            for p in files:
                receipt=p.with_suffix('.command.json')
                if not receipt.exists():errors.append('missing_fit_receipt:'+item['path']+'/'+p.name)
                else:
                    r=load(receipt)
                    if receipt_errors(r) or r.get('raw_capture')!='PRESENT':errors.append('fit_receipt:'+item['path']+'/'+p.name)
                for suffix in ('.stdout','.stderr'):
                    if not p.with_suffix(suffix).exists():errors.append('missing_fit_log:'+item['path']+'/'+p.name)
            native_index=0
            for prefix,record in enumerate(d['decisions'],1):
                expected_input=preprocess(rows[:prefix],DetectionConfig())
                values=expected_input['values_ms']
                should_fit=len(values)>=8 and expected_input['population_std_ms']!=0 and len(set(values))!=1
                if record.get('engine'):
                    name=record['engine'].get('capture_file')
                    if name!=f'fit-{native_index:03d}.json':errors.append('fit_order:'+item['path']+f':{prefix}')
                    native_index+=1
                    if not should_fit or name not in mapped:errors.append('fit_reference:'+item['path']+f':{prefix}');continue
                    fit=mapped[name]
                    problems=validate_fit(fit,binary,values,PARAMETERS);array_count+=len(fit['arrays'])
                    native_errors+=int('native_validation' in problems)
                    if problems:fit_errors.append(dict(path=item['path'],prefix=prefix,errors=problems))
                    expected_status='INSUFFICIENT_EVIDENCE' if fit.get('candidate_validation_error') else 'OK'
                    if record['engine'].get('status')!=expected_status:errors.append('engine_validation_reference:'+item['path']+f':{prefix}')
                    if difference(record['engine']['raw'],fit['raw']):errors.append('raw_reference:'+item['path'])
                elif should_fit:errors.append('missing_engine:'+item['path']+f':{prefix}')
                elif record.get('reason') not in ('NATIVE_MINIMUM_8_RETAINED_SAMPLES_GUARD','CONSTANT_SERIES_ZERO_VARIANCE'):errors.append('non_fit_reason:'+item['path'])
                if record['final_alert'] is not False:errors.append('final_alert')
            decision_groups[s].append(dict(decisions=d['decisions'],fits=mapped))
    if fit_count!=5540 or prefix_count!=6300:errors.append('total_counts')
    if array_count!=132960:errors.append('total_array_count')
    summaries=[]
    for cell,fits in sorted(reference.items()):
        if len(fits)!=20:errors.append('cell_count:'+cell)
        for f in fits:
            if f['dispatch']!=fits[0]['dispatch']:errors.append('dispatch_drift:'+cell)
        first_diffs=[compare(fits[0],f) for f in fits]
        summaries.append(dict(cell=cell,fits=len(fits),unique_outputs=len({numeric_digest(f) for f in fits}),
            dispatch=fits[0]['dispatch'],differences=first_diffs))
        save(output/f'reference-{cell}.json',dict(cell=cell,workers=reference_workers.get(cell,[]),fits=fits))
    decisions_summary=[]
    for scenario,groups in decision_groups.items():
        by_prefix=[]
        for index in range(45):
            digest=[];stage_digest=[];diffs=[]
            for g in groups:
                d=g['decisions'][index];stage_digest.append(sha(canonical(compact_decision(d))))
                e=d.get('engine')
                digest.append(numeric_digest(g['fits'][e['capture_file']]) if e and e.get('capture_file') in g['fits'] else None)
                diffs.append(difference(compact_decision(groups[0]['decisions'][index]),compact_decision(d)))
            by_prefix.append(dict(prefix=index+1,unique_native=len(set(digest)),unique_decision_stages=len(set(stage_digest)),differences=diffs))
        first={rule:[next((d['latest_iteration'] for d in g['decisions'] if qualified(d,rule)),None) for g in groups]
               for rule in ('probability','duration','throughput')}
        decisions_summary.append(dict(scenario=scenario,repeats=len(groups),prefixes=by_prefix,first_observation=first))
        save(output/f'decisions-{scenario}.json',dict(scenario=scenario,replays=groups))
    result=dict(run_id=run.name,counts=dict(fits=fit_count,reference_fits=sum(len(f) for f in reference.values()),
        native_decision_fits=fit_count-sum(len(f) for f in reference.values()),prefixes=prefix_count,arrays=array_count),
        integrity_errors=errors,native_errors=native_errors,fit_errors=fit_errors,
        reference=summaries,decisions=decisions_summary)
    save(output/'batch-summary.json',result)
    return result,reference,decision_groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    execution=load(args.execution/'execution-private.json');manifest=load(args.build/'build-manifest.json')
    matrices=[];groups={};all_decisions={}
    for entry in execution['batches']:
        dest=args.output/entry['run_id'];dest.mkdir()
        try:
            summary,ref,dec=validate_batch(args.execution/entry['run_id'],manifest['builds'][entry['build']]['native_binary_sha256'],dest)
            matrices.append(dict(build=entry['build'],batch=entry['batch'],**summary))
            for cell,fits in ref.items():groups.setdefault((entry['build'],cell),[]).extend(fits)
            for s,replays in dec.items():all_decisions.setdefault((entry['build'],s),[]).extend(replays)
        except (OSError,ValueError,KeyError,AssertionError) as error:
            matrices.append(dict(build=entry['build'],batch=entry['batch'],integrity_errors=[type(error).__name__+': '+str(error)]))
    across=[]
    # Group all process/affinity/request aliases by model and observed ISA.
    actual={}
    for (label,cell),fits in groups.items():
        across.append(dict(build=label,cell=cell,count=len(fits),unique_outputs=len({numeric_digest(f) for f in fits})))
        for fit in fits:
            key=(label,fit['parameters']['mcmc_chains'],fit['dispatch']['cpu_current'],fit['dispatch']['seed_function'])
            actual.setdefault(key,[]).append(fit)
    controls=[dict(build=k[0],chains=k[1],actual_cpu=k[2],actual_seeder=k[3],count=len(f),
        unique_outputs=len({numeric_digest(x) for x in f}),first_difference=next((compare(f[0],x)['first_difference'] for x in f if not compare(f[0],x)['equal']),None)) for k,f in actual.items()]
    decision_across=[]
    for (label,s),replays in all_decisions.items():
        native_per_prefix=[]
        for index in range(45):
            signatures=[]
            for replay in replays:
                engine=replay['decisions'][index].get('engine')
                signatures.append(numeric_digest(replay['fits'][engine['capture_file']]) if engine and engine.get('capture_file') in replay['fits'] else None)
            native_per_prefix.append(len(set(signatures)))
        decision_across.append(dict(build=label,scenario=s,replays=len(replays),
            unique_native_per_prefix=native_per_prefix,
            unique_complete_stages=len({sha(canonical([compact_decision(d) for d in r['decisions']])) for r in replays})))
    c_matrices=[m for m in matrices if m['build']=='C']
    c_integrity=len(c_matrices)==2 and all(not m['integrity_errors'] and not any(
        any(e!='native_validation' for e in f['errors']) for f in m['fit_errors']) for m in c_matrices)
    c_native_validity=c_integrity and all(m['native_errors']==0 for m in c_matrices)
    c_numeric=c_integrity and all(x['unique_outputs']==1 for x in controls if x['build']=='C') and all(
        all(n==1 for n in x['unique_native_per_prefix']) for x in decision_across if x['build']=='C')
    c_decision=c_native_validity and all(x['unique_complete_stages']==1 for x in decision_across if x['build']=='C')
    result=dict(matrices=matrices,cross_batch_cells=across,same_model_actual_isa_controls=controls,
        decision_cross_batches=decision_across,C_integrity='PASS' if c_integrity else 'FAIL' if execution['batches'] else 'NOT_RUN',
        C_numerical='PASS' if c_numeric else 'FAIL' if execution['batches'] else 'NOT_RUN',
        C_native_validity='PASS' if c_native_validity else 'FAIL' if execution['batches'] else 'NOT_RUN',
        C_decisions='PASS' if c_decision else 'FAIL' if execution['batches'] else 'NOT_RUN')
    save(args.output/'comparison.json',result)
    print(json.dumps({k:result[k] for k in ('C_integrity','C_numerical','C_decisions')}))


if __name__=='__main__':main()
