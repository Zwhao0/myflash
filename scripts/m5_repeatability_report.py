"""ADAPTATION: lossless identity-free M5-R data and descriptive comparisons.

Input is this run's diagnostics only. Original M5 evidence is never overwritten.
No acceptance threshold or inference of a universal statistical bound is added.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.m5_repeatability import canonical, sha, save, SCENARIOS, ROOT


def load(path):
    return json.loads(path.read_text())


def compare(reference, current):
    import numpy as np
    differences = {}
    for field in sorted(set(reference['arrays']) | set(current['arrays'])):
        a, b = reference['arrays'].get(field), current['arrays'].get(field)
        if a is None or b is None or a['dtype'] != b['dtype'] or a['shape'] != b['shape']:
            differences[field] = dict(shape_or_dtype_changed=True)
            continue
        dt = np.dtype(a['dtype'])
        ba, bb = [base64.b64decode(x['bytes_base64']) for x in (a,b)]
        bits_a, bits_b = [np.frombuffer(x, dtype=np.uint8).reshape(-1,dt.itemsize) for x in (ba,bb)]
        changed = int(np.any(bits_a != bits_b,axis=1).sum())
        va, vb = [np.frombuffer(x,dtype=dt) for x in (ba,bb)]
        finite = np.isfinite(va) & np.isfinite(vb)
        differences[field] = dict(changed_elements=changed, total_elements=len(va),
             max_abs_finite_difference=float(np.max(np.abs(va[finite].astype(float)-vb[finite].astype(float)))) if finite.any() else None,
             byte_equal=ba == bb)
    return dict(raw_json_equal=reference['raw_json_sha256'] == current['raw_json_sha256'],
                posterior_array_bytes_equal=reference['posterior_bytes_sha256'] == current['posterior_bytes_sha256'],
                array_differences=differences,
                changed_elements=sum(d.get('changed_elements',0) for d in differences.values()),
                cp_equal=reference['raw']['trend']['cp'] == current['raw']['trend']['cp'],
                cpPr_equal=reference['raw']['trend']['cpPr'] == current['raw']['trend']['cpPr'],
                cpOccPr_equal=reference['raw']['trend']['cpOccPr'] == current['raw']['trend']['cpOccPr'])


def fit_public(fit):
    fit['full_output_sha256'] = sha(canonical(dict(raw=fit['raw_json_sha256'],arrays=fit['posterior_bytes_sha256'])))
    return fit


def reference_report(run, output):
    summary = []
    for group in sorted((run/'reference').iterdir()):
        for process_mode in ('same','fresh'):
            workers = [load(p) for p in sorted((group/process_mode).glob('*.json')) if p.stem.isdigit()]
            fits = [fit_public(f) for w in workers for f in w['fits']]
            assert len(fits) == 20
            assert len({f['input_sha256'] for f in fits}) == 1
            assert len({sha(canonical(f['parameters'])) for f in fits}) == 1
            for f in fits:
                f['vs_first'] = compare(fits[0],f)
            dest = 'reference-'+group.name+'-'+process_mode+'.json'
            save(output/dest, dict(configuration=group.name, process_mode=process_mode,
                 worker_affinities=[w['affinity'] for w in workers],
                 thread_environment=workers[0]['thread_environment'],
                 threads_after=[w['threads_after'] for w in workers], fits=fits))
            summary.append(dict(configuration=group.name,process_mode=process_mode,repetitions=len(fits),
                unique_raw_json=len({f['raw_json_sha256'] for f in fits}),
                unique_full_output=len({f['full_output_sha256'] for f in fits}),
                cp_unique=len({sha(canonical(f['raw']['trend']['cp'])) for f in fits}),
                cpPr_unique=len({sha(canonical(f['raw']['trend']['cpPr'])) for f in fits}),
                cpOccPr_unique=len({sha(canonical(f['raw']['trend']['cpOccPr'])) for f in fits}),
                changed_elements_vs_first=[f['vs_first']['changed_elements'] for f in fits],
                actual_dispatch=fits[0]['dispatch'],data=dest))
    return summary


def qualified(d, rule):
    if rule == 'probability':
        return sorted(c['iteration'] for c in d['candidates']
                      if c['reason'] != 'PADDED_SLOT' and c.get('iteration') is not None
                      and c['stages']['probability']['passed'])
    key = 'provisional_'+rule+'_candidate'
    return sorted(c['iteration'] for c in d['candidates'] if c.get(key,False))


def adjacent_drift(sequences):
    return any(abs(a-b)==1 for s in sequences for t in sequences
               for a in set(s)-set(t) for b in set(t)-set(s))


def scenario_report(run, output, scenario):
    reps = []
    rules = ('probability','duration','throughput')
    for directory in sorted((run/'decisions'/scenario).iterdir()):
        if not directory.is_dir(): continue
        replay = load(directory/'decisions.json')
        fits = [fit_public(load(p)) for p in sorted(directory.glob('fit-*.json')) if p.name.count('.') == 1]
        # command.json excluded; lossless native output moved to fits, never deleted.
        for d in replay['decisions']:
            d.pop('input',None)  # exact immutable fixture retained below
            if d.get('engine'):
                d['engine'].pop('raw')  # identical raw tree in referenced fit
        observations = [{rule:qualified(d,rule) for rule in rules} for d in replay['decisions']]
        first = {rule:next((i+1 for i,o in enumerate(observations) if o[rule]),None) for rule in rules}
        reps.append(dict(repetition=int(directory.name),decisions=replay['decisions'],fits=fits,
                         candidates_by_prefix=observations,first_candidate_iteration=first))
    assert len(reps) == 20
    assert all(len(r['decisions']) == 45 for r in reps)
    baseline = reps[0]['fits']
    for r in reps:
        assert len(r['fits']) == len(baseline)
        for ref,f in zip(baseline,r['fits']):
            assert ref['input_sha256'] == f['input_sha256']
            assert ref['parameters'] == f['parameters']
            f['vs_repetition0_same_prefix'] = compare(ref,f)
    prefixes = []
    for k in range(45):
        decisions = [r['decisions'][k] for r in reps]
        candidates = [r['candidates_by_prefix'][k] for r in reps]
        by_rule = {}
        for rule in rules:
            sequences = [o[rule] for o in candidates]
            presence = [bool(s) for s in sequences]
            valid_presence = [bool(s) for s,d in zip(sequences,decisions)
                              if d.get('engine') and d['engine']['status']=='OK']
            by_rule[rule] = dict(present_repetitions=sum(presence),presence_flip=len(set(presence))>1,
                valid_native_presence_flip=len(set(valid_presence))>1,
                unique_cp_sets=sorted({tuple(s) for s in sequences}),
                adjacent_iteration_drift=adjacent_drift(sequences))
        per_cp = {}
        for rep,d in enumerate(decisions):
            for c in d['candidates']:
                cp = c.get('iteration')
                if cp is None: continue
                key = str(cp)
                if key not in per_cp: per_cp[key] = []
                per_cp[key].append(dict(repetition=rep,cpPr=c['cpPr'],raw_coordinate=c['cp'],
                    probability_pass=c['stages']['probability']['passed'],
                    duration_growth=c['stages']['degradation']['duration_growth'],
                    throughput_loss=c['stages']['degradation']['throughput_loss']))
        raw_cp_sets = [sorted(c['iteration'] for c in d['candidates']
                              if c.get('iteration') is not None) for d in decisions]
        engine = [d.get('engine') for d in decisions]
        valid = [e for e in engine if e]
        prefixes.append(dict(iteration=k+1,rules=by_rule,cpPr_by_original_iteration=per_cp,
            native_cp_sets=sorted({tuple(s) for s in raw_cp_sets}),
            native_cp_adjacent_drift=adjacent_drift(raw_cp_sets),
            native_rejected_repetitions=[i for i,e in enumerate(engine) if e and e['status']!='OK'],
            denominator_candidate_disagreement_repetitions=sum(o['duration'] != o['throughput'] for o in candidates),
            posterior_byte_unique=len({e['posterior_bytes_sha256'] for e in valid}) if valid else None,
            raw_json_unique=len({e['raw_json_sha256'] for e in valid}) if valid else None))
    dest = 'decisions-'+scenario+'.json'
    fixture = ROOT/'tests/m5_fixtures/records'/(scenario+'.json')
    save(output/dest,dict(scenario=scenario,fixture=load(fixture),fixture_sha256=sha(fixture.read_bytes()),
                         repetitions=reps,prefix_comparisons=prefixes))
    by_rule = {}
    for rule in rules:
        first = [r['first_candidate_iteration'][rule] for r in reps]
        by_rule[rule] = dict(first_candidate_iterations=first,ever_present_repetitions=sum(x is not None for x in first),
            prefix_presence_flip_iterations=[p['iteration'] for p in prefixes if p['rules'][rule]['presence_flip']],
            valid_native_presence_flip_iterations=[p['iteration'] for p in prefixes if p['rules'][rule]['valid_native_presence_flip']],
            adjacent_drift_iterations=[p['iteration'] for p in prefixes if p['rules'][rule]['adjacent_iteration_drift']],
            candidate_cp_sets_differ_iterations=[p['iteration'] for p in prefixes if len(p['rules'][rule]['unique_cp_sets'])>1])
    probability = []
    for p in prefixes:
        for cp, observations in p['cpPr_by_original_iteration'].items():
            values = [o['cpPr'] for o in observations]
            probability.append(dict(prefix=p['iteration'],original_iteration=int(cp),
                                    present_repetitions=len(values),minimum=min(values),maximum=max(values),
                                    range=max(values)-min(values),probability_passes=sum(v>=.8 for v in values)))
    return dict(scenario=scenario,repetitions=20,native_fits=sum(len(r['fits']) for r in reps),rules=by_rule,
        probability_distributions=probability,
        denominator_disagreement_iterations=[p['iteration'] for p in prefixes if p['denominator_candidate_disagreement_repetitions']],
        native_cp_sets_differ_iterations=[p['iteration'] for p in prefixes if len(p['native_cp_sets'])>1],
        native_cp_adjacent_drift_iterations=[p['iteration'] for p in prefixes if p['native_cp_adjacent_drift']],
        native_rejections=[dict(iteration=p['iteration'],repetitions=p['native_rejected_repetitions'])
                           for p in prefixes if p['native_rejected_repetitions']],
        posterior_identical_all_repetitions=all(p['posterior_byte_unique'] in (None,1) for p in prefixes),
        numerical_different_prefixes=[p['iteration'] for p in prefixes if p['posterior_byte_unique'] not in (None,1)],
        data=dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    save(args.output/'manifest.json',load(args.run/'manifest.json'))
    save(args.output/'rng.json',load(args.run/'rng.json'))
    references = reference_report(args.run,args.output)
    scenarios = [scenario_report(args.run,args.output,s) for s in SCENARIOS]
    save(args.output/'summary.json',dict(reference=references,scenarios=scenarios,
         statistical_bound='NOT_ESTABLISHED; descriptive finite fixed-input sample only',final_alert=False))
    files = {p.name:dict(sha256=sha(p.read_bytes()),size_bytes=p.stat().st_size)
             for p in sorted(args.output.glob('*.json'))}
    save(args.output/'data-index.json',files)
    print('M5-R comparison export complete; raw posterior arrays/bytes retained')


if __name__ == '__main__': main()
