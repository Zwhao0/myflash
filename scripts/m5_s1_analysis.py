"""ADAPTATION independent, fail-closed replay of SAVED C evidence; no native fits.

EXTENSION A/B and persistence rules are separate unapproved diagnostics.
Only analyze_prefix consumes observations; evaluator metadata is joined afterwards.
"""
import argparse
import ast
import hashlib
import json
import math
import statistics
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd2973f5fa66ae99ec7ea09ea7040a11d1b95b845'
SCENARIOS = ('stable', 'sustained', 'growth_19', 'growth_20', 'growth_21', 'spike', 'recovery')
CONFIG = dict(window=30, thresh_prob=0.8, degradation_thresh=0.2, warmup=3,
              zscore=3.0, spacing=2, recovery=0.75)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def ratios(baseline, degraded):
    """Positive physical means only. Zero/negative/invalid never becomes a zero ratio."""
    answer = {}
    for name, denominator in [('A', baseline), ('B', degraded)]:
        reason = ('INVALID_INPUT' if not finite(baseline) or not finite(degraded)
                  else 'ZERO_DENOMINATOR' if denominator == 0
                  else 'NONPOSITIVE_DURATION' if baseline <= 0 or degraded <= 0 else None)
        value = None if reason else (degraded - baseline) / denominator
        answer[name] = dict(value=value, passed=None if value is None else value > 0.2,
                            comparison='>', threshold=0.2, reason=reason)
    return answer


def persistence(latest, cp, retained_right, streak):
    if any(type(x) is not int for x in (latest, cp, retained_right, streak)) or latest < cp or cp < 1 or retained_right < 1 or streak < 0:
        raise ValueError('invalid persistence evidence')
    return dict(span_inclusive_gt20=latest-cp+1 > 20,
                elapsed_exclusive_gt20=latest-cp > 20,
                retained_right_gt20=retained_right > 20,
                qualified_consecutive_prefixes_gt20=streak > 20,
                right_guard_original_k1=latest-cp >= 1,
                right_guard_original_k2=latest-cp >= 2)


def prepare(records):
    for k, row in enumerate(records, 1):
        if row['iteration'] != k or row['global_rank'] != 0 or not finite(row['iteration_time_ms']) or row['iteration_time_ms'] <= 0:
            raise ValueError('invalid prefix input')
    window = records[-30:]
    eligible = [r['iteration_time_ms'] for r in window if r['iteration'] > 3]
    mean = statistics.fmean(eligible) if eligible else None
    std = statistics.pstdev(eligible) if eligible else None
    sample_std = statistics.stdev(eligible) if len(eligible) > 1 else None
    stages, mapping, values = [], [], []
    for r in window:
        warm = r['iteration'] <= 3
        z = None if warm else 0.0 if std == 0 else abs((r['iteration_time_ms']-mean)/std)
        sz = 0.0 if sample_std == 0 else abs((r['iteration_time_ms']-mean)/sample_std) if sample_std and not warm else None
        reason = 'WARMUP' if warm else 'ZSCORE_OUTLIER' if z > 3 else None
        i = None if reason else len(values)
        if reason is None:
            mapping.append(r['iteration']); values.append(r['iteration_time_ms'])
        stages.append(dict(iteration=r['iteration'], time_ms=r['iteration_time_ms'],
                           warmup_removed=warm, zscore_population=z, zscore_sample=sz,
                           threshold=3.0, filtered_index0=i, reason=reason))
    return dict(window_iterations=[r['iteration'] for r in window], stages=stages,
                mean_ms=mean, population_std_ms=std, sample_std_ms=sample_std,
                index0_to_iteration=mapping, iteration_to_index0={str(r['iteration']):r['filtered_index0'] for r in stages},
                values_ms=values, temporal_semantics='compressed retained samples; original iteration mapping preserved')


def analyze_prefix(saved, history):
    """No evaluator, future prefix, or complete fixture accepted by this interface."""
    n = saved['latest_iteration']
    if type(n) is not int or len(saved['input']) != n or saved['config'] != CONFIG or saved['final_alert'] is not False:
        raise ValueError('prefix identity/config/final-alert mismatch')
    prepared = prepare(saved['input'])
    if prepared != saved['preprocessing']:
        raise ValueError('independent preprocessing mismatch')
    values, mapping = prepared['values_ms'], prepared['index0_to_iteration']
    engine = saved['engine']
    answer = dict(iteration=n, input_sha256=sha(canonical(saved['input'])),
                  retained_input_sha256=sha(struct.pack('<'+'d'*len(values), *values)),
                  source_decision_sha256=sha(canonical(saved)), mapping=mapping,
                  preprocessing=prepared, source_status=saved['status'], source_reason=saved.get('reason'),
                  evidence_state=None, candidates=[], first_filter_pass=False,
                  provisional={'A':False, 'B':False}, final_alert=False,
                  final_alert_iteration=None, final_alert_status='NOT_APPROVED/NOT_RUN')
    if engine is None:
        if saved['candidates'] or saved['status'] != 'INSUFFICIENT_EVIDENCE':
            raise ValueError('unexpected unfitted prefix')
        answer['evidence_state'] = 'INSUFFICIENT_EVIDENCE'
        history.clear()
        return answer
    if engine['status'] != 'OK':
        raise ValueError('C has invalid native output; preserve failure and stop')
    if engine['input_sha256'] != answer['retained_input_sha256']:
        raise ValueError('fit input hash mismatch')
    trend = engine['raw']['trend']
    cp, probs, occ = [trend[k] for k in ('cp', 'cpPr', 'cpOccPr')]
    if len(cp) != len(probs) or len(occ) != len(values) or any(not finite(x) or not 0 <= x <= 1 for x in occ):
        raise ValueError('invalid native probability/shape')
    raw = []
    seen = set()
    for slot, (coordinate, prob) in enumerate(zip(cp, probs)):
        if coordinate is None and prob is None:
            raw.append(dict(slot=slot, cp=None, cpPr=None, index0=None, reason='PADDED_SLOT'))
            continue
        if not finite(coordinate) or coordinate != int(coordinate) or not 1 <= coordinate <= len(values) or not finite(prob) or not 0 <= prob <= 1 or coordinate in seen:
            raise ValueError('invalid native candidate; no clipping')
        seen.add(coordinate)
        raw.append(dict(slot=slot, cp=coordinate, cpPr=prob, index0=int(coordinate)-1, reason=None))
    previous = None
    new_history = {}
    for c in sorted(raw, key=lambda c:(c['index0'] is None, c['index0'] or 0, c['slot'])):
        row = dict(c)
        if c['reason']:
            row.update(evidence_state='PADDED_SLOT', original_iteration=None)
            answer['candidates'].append(row)
            continue
        i = c['index0']; point = mapping[i]
        left, right, recent = values[:i], values[i:], values[i+1:]
        b = statistics.fmean(left) if left else None
        d = statistics.fmean(right) if right else None
        r = statistics.fmean(recent) if recent else None
        delta = None if b is None or d is None else d-b
        rec = None if not left or not recent or delta == 0 else (d-r)/delta
        probability = c['cpPr'] >= 0.8
        distance = None if previous is None else point-previous
        spacing = distance is None or distance >= 2
        if probability and spacing:
            previous = point
        recovery_pass = None if rec is None else rec < 0.75
        passed = probability and spacing and recovery_pass is True and delta > 0
        formulas = ratios(b, d)
        provisional = {f:passed and formulas[f]['passed'] is True for f in ('A','B')}
        rules = {}
        for f in ('A','B'):
            key = (point, f)
            streak = history.get(key, 0)+1 if provisional[f] else 0
            if streak: new_history[key] = streak
            rules[f] = dict(qualified_streak=streak, gates=persistence(n, point, len(right), streak),
                            triggers={k:provisional[f] and v for k,v in persistence(n, point, len(right), streak).items()})
        state = ('INSUFFICIENT_EVIDENCE' if probability and spacing and rec is None
                 else 'PROVISIONAL_CANDIDATE' if any(provisional.values())
                 else 'VALID_OUTPUT_NO_PROVISIONAL_CANDIDATE')
        row.update(original_iteration=point, cpOccPr_at_coordinate=occ[i],
                   means_ms=dict(baseline=b,degraded=d,recent=r),
                   counts=dict(left=len(left),right=len(right),recent=len(recent)),
                   probability_pass=probability, spacing_pass=spacing, original_distance=distance,
                   recovery_ratio=rec, recovery_pass=recovery_pass, positive_delta=None if delta is None else delta > 0,
                   pre_intensity_filter_pass=passed, formulas=formulas, provisional=provisional,
                   persistence=rules, evidence_state=state,
                   formula_threshold_disagreement=formulas['A']['passed'] != formulas['B']['passed'],
                   provisional_disagreement=provisional['A'] != provisional['B'])
        answer['first_filter_pass'] |= passed
        for f in ('A','B'):answer['provisional'][f] |= provisional[f]
        # Exact arithmetic cross-check against immutable original result, not loose tolerance.
        old = next(x for x in saved['candidates'] if x['slot'] == c['slot'])
        if old['iteration'] != point or old['statistics']['baseline_mean'] != b or old['statistics']['degraded_mean'] != d or old['statistics']['recent_mean'] != r:
            raise ValueError('saved mean/mapping mismatch')
        dg = old['stages']['degradation']
        if dg['duration_growth'] != formulas['A']['value'] or dg['throughput_loss'] != formulas['B']['value'] or old['stages']['recovery']['value'] != rec:
            raise ValueError('saved ratio/recovery mismatch')
        if old['stages']['probability']['passed'] != probability or old['stages']['spacing']['passed'] != spacing or bool(old.get('provisional_duration_candidate')) != provisional['A'] or bool(old.get('provisional_throughput_candidate')) != provisional['B']:
            raise ValueError('saved filtering mismatch')
        answer['candidates'].append(row)
    history.clear(); history.update(new_history)
    if any(answer['provisional'].values()): answer['evidence_state'] = 'PROVISIONAL_CANDIDATE'
    elif any(c['evidence_state']=='INSUFFICIENT_EVIDENCE' for c in answer['candidates']):answer['evidence_state']='INSUFFICIENT_EVIDENCE'
    else:answer['evidence_state']='VALID_OUTPUT_NO_PROVISIONAL_CANDIDATE'
    return answer


def preserved():
    paths = subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
    index = {}
    for path in paths:
        old = subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
        current = (ROOT/path).read_bytes()
        if not (current.startswith(old) if path in ('STATUS.md','GAPS.md') else current == old):
            raise ValueError('original changed: '+path)
        index[path] = sha(old)
    return index


def analyze_all():
    inputs = preserved()
    tree = ast.parse((ROOT/'flash/rbeast_adapter.py').read_text())
    assignment = next(x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PARAMETERS' for t in x.targets))
    parameters = {k.arg:ast.literal_eval(k.value) for k in assignment.value.keywords}
    results = []
    receipts = []
    for batch in ('m5-p1-c-batch01','m5-p1-c-batch02'):
        directory = ROOT/'docs/m5/patch-p1/data'/batch
        for scenario in SCENARIOS:
            path = directory/('decisions-'+scenario+'.json')
            evidence = json.loads(path.read_text())
            fixture = json.loads((ROOT/'tests/m5_fixtures/records'/(scenario+'.json')).read_text())['records']
            if evidence['scenario'] != scenario or len(evidence['replays']) != 20:
                raise ValueError('missing scenario/repeat')
            reference = None
            for repeat, replay in enumerate(evidence['replays']):
                if len(replay['decisions']) != 45:raise ValueError('missing prefix')
                history = {}; output = []
                for n, saved in enumerate(replay['decisions'],1):
                    if saved['input'] != fixture[:n] or saved['latest_iteration'] != n:
                        raise ValueError('future/fixture input mismatch')
                    if saved['engine'] and saved['engine']['parameters'] != parameters:
                        raise ValueError('native parameters changed')
                    output.append(analyze_prefix(saved, history))
                if reference is None:reference = output
                elif reference != output:raise ValueError('saved C repeats differ')
                receipts.append(dict(batch=batch,scenario=scenario,repeat=repeat,
                                     prefixes=45, source_file=str(path.relative_to(ROOT)),
                                     source_sha256=inputs[str(path.relative_to(ROOT))],
                                     replay_sha256=sha(canonical(replay)), analyzed_sha256=sha(canonical(output))))
            results.append(dict(batch=batch,scenario=scenario,prefixes=reference))
    # Evaluator truth joined only here; analyze_prefix never receives it.
    evaluator = json.loads((ROOT/'tests/m5_fixtures/evaluator.json').read_text())
    summary = []
    for result in results:
        rows = result['prefixes']
        def first(predicate):return next((r['iteration'] for r in rows if predicate(r)),None)
        rules = {}
        for f in ('A','B'):
            rules[f] = {k:first(lambda r:any(c.get('persistence',{}).get(f,{}).get('triggers',{}).get(k,False) for c in r['candidates']))
                        for k in persistence(21,1,21,21)}
        summary.append(dict(batch=result['batch'],scenario=result['scenario'],
                            evaluator_onset_iteration=evaluator[result['scenario']]['onset_iteration'],
                            first_probability_iteration=first(lambda r:any(c.get('probability_pass') for c in r['candidates'])),
                            first_pre_intensity_filter_iteration=first(lambda r:r['first_filter_pass']),
                            first_provisional_iteration={f:first(lambda r:r['provisional'][f]) for f in ('A','B')},
                            first_persistence_rule_iteration=rules,
                            evidence_state_counts={s:sum(r['evidence_state']==s for r in rows) for s in sorted({r['evidence_state'] for r in rows})},
                            formula_disagreement_iterations=[r['iteration'] for r in rows if any(c.get('formula_threshold_disagreement') for c in r['candidates'])],
                            provisional_disagreement_iterations=[r['iteration'] for r in rows if any(c.get('provisional_disagreement') for c in r['candidates'])],
                            final_alert=False, final_alert_iteration=None, scientific_status='OPEN / REQUIRES_OWNER_DECISION'))
    if [r['prefixes'] for r in results[:7]] != [r['prefixes'] for r in results[7:]]:
        raise ValueError('C batches differ')
    return dict(baseline=BASE, nature='EXTENSION', units='ms; sample counts distinct from original iteration span',
                final_alert=False, scenarios=results), dict(baseline=BASE, final_alert=False,summary=summary), receipts, inputs


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    data, summary, receipts, inputs=analyze_all()
    timelines=[]
    for series, brief in zip(data['scenarios'],summary['summary']):
        timelines.append(dict(batch=series['batch'],scenario=series['scenario'],
            evaluation_only_onset_iteration=brief['evaluator_onset_iteration'],
            prefixes=[dict(iteration=r['iteration'], evidence_state=r['evidence_state'],
                model_cp_original_iterations=[c['original_iteration'] for c in r['candidates'] if c['index0'] is not None],
                probability_qualified_cp=[c['original_iteration'] for c in r['candidates'] if c.get('probability_pass')],
                pre_intensity_filter_cp=[c['original_iteration'] for c in r['candidates'] if c.get('pre_intensity_filter_pass')],
                provisional_cp={f:[c['original_iteration'] for c in r['candidates'] if c.get('provisional',{}).get(f)] for f in ('A','B')},
                cp_age_gt20=[c['original_iteration'] for c in r['candidates'] if c['index0'] is not None and r['iteration']-c['original_iteration']+1>20],
                persistence_triggers={f:{k:[c['original_iteration'] for c in r['candidates'] if c.get('persistence',{}).get(f,{}).get('triggers',{}).get(k)] for k in persistence(21,1,21,21)} for f in ('A','B')},
                final_alert=False,final_alert_iteration=None,final_alert_status='NOT_APPROVED/NOT_RUN') for r in series['prefixes']]))
    for name,value in [('sensitivity.json',data),('timeline.json',timelines),('timeline-summary.json',summary),('repeat-coverage.json',receipts),('input-hashes.json',inputs)]:
        (args.output/name).write_bytes(canonical(value)+b'\n')
    index={str(p.relative_to(args.output)):sha(p.read_bytes()) for p in sorted(args.output.glob('*.json')) if p.name!='hash-index.json'}
    (args.output/'hash-index.json').write_bytes(canonical(index)+b'\n')
    print(json.dumps(dict(status='PASS',prefixes_checked=12600,unique_prefix_rows=630,repeats=280,native_fits=0,final_alert=False,outputs=index)))


if __name__=='__main__':main()
