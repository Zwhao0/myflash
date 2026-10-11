"""EXTENSION fixed C historical replay and sensitivity; ADAPTATION evidence checks.

Stdlib only. No Rbeast import, fit, evaluator truth, server or service operations.
Run with --output <new private directory>; assertions preserve strict evidence.
"""
import argparse
import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import struct
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from flash.change_detection import detect, preprocess, DetectionConfig
from flash.iteration_reporter import IterationRecord
from flash.rbeast_adapter import PARAMETERS, CANDIDATE_C_SHA256


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SavedAdapter:
    def __init__(self, saved):
        self.saved = saved
        self.calls = 0

    def analyze(self, values):
        self.calls += 1
        assert values == self.saved['preprocessing']['values_ms']
        engine = self.saved['engine']
        assert engine is not None and engine['parameters'] == PARAMETERS
        if 'input_sha256' in engine:
            assert engine['input_sha256'] == sha(struct.pack('<'+'d'*len(values), *values))
        return engine


def check_prefix(saved, fixture):
    t = saved['latest_iteration']
    assert saved['input'] == fixture[:t]
    records = [IterationRecord(**r) for r in fixture[:t]]
    adapter = SavedAdapter(saved)
    legacy = detect(records, adapter)
    assert legacy == saved, 'default output changed at prefix ' + str(t)
    before = sha(canonical(saved))
    new = detect(records, adapter, approved_rules=True)
    assert before == sha(canonical(saved)), 'saved evidence mutated'
    assert new['final_alert'] is False and new['unresolved'] == ['G20']
    if new['engine'] is not None:
        assert new['engine'] == saved['engine']
    assert new.get('preprocessing') == saved['preprocessing']
    # Independently use the saved native cp pair and current slices, not trigger fields.
    values = saved['preprocessing']['values_ms']
    mapping = saved['preprocessing']['index0_to_iteration']
    expected_A, expected_B = [], []
    all_slots = []
    previous = None
    for c in new['candidates']:
        assert not c['final_alert']
        if not c['model_candidate']:
            assert c['reason'] == 'PADDED_SLOT' and not c['detection_trigger']
            all_slots.append(dict(slot=c['slot'], reason=c['reason']))
            continue
        i, slot = c['index0'], c['slot']
        raw = saved['engine']['raw']['trend']
        assert raw['cp'][slot] == c['cp'] == i+1
        assert raw['cpPr'][slot] == c['cpPr']
        j = mapping[i]
        prob = raw['cpPr'][slot] >= .8
        spacing = previous is None or j-previous >= 2
        if prob and spacing:
            previous = j
        left, right, recent = values[:i], values[i:], values[i+1:]
        b = statistics.fmean(left) if left else None
        d = statistics.fmean(right) if right else None
        r = statistics.fmean(recent) if recent else None
        delta = None if b is None or d is None else d-b
        recovery = None if not left or not recent or delta == 0 else (d-r)/delta
        A = None if not b or delta is None else delta/b
        B = None if not d or delta is None else delta/d
        qualified = prob and spacing and recovery is not None and recovery < .75 and delta > 0
        qa = qualified and A is not None and A > .2
        qb = qualified and B is not None and B > .2
        gate = t-j+1 > 20
        assert c['iteration'] == j
        assert (b, d, r) == tuple(c['statistics'][k] for k in
            ('baseline_mean', 'degraded_mean', 'recent_mean'))
        assert c['stages']['probability']['passed'] == prob
        assert c['stages']['spacing']['passed'] == spacing
        assert c['stages']['recovery']['value'] == recovery
        assert c['stages']['degradation']['duration_growth'] == A
        assert c['stages']['degradation']['throughput_loss'] == B
        assert c['qualified_candidate'] == qa
        assert c['stages']['persistence']['decision'] == gate
        assert c['detection_trigger'] == (qa and gate)
        if qa and gate:
            expected_A.append(j)
        if qb and gate:
            expected_B.append(j)
        all_slots.append(dict(slot=slot, cp=c['cp'], cpPr=c['cpPr'], original_iteration=j,
            b_ms=b, d_ms=d, r_ms=r, A=A, B=B, recovery=recovery,
            probability_pass=prob, spacing_pass=spacing, qualified_A=qa, qualified_B=qb,
            inclusive_span=t-j+1, retained_right=len(right), inclusive_pass=gate,
            detection_trigger=c['detection_trigger'], status=c['status'], reason=c['reason']))
    assert new['detection_trigger'] == bool(expected_A)
    return dict(iteration=t, status=new['status'], detection_trigger=new['detection_trigger'],
        triggered_A=expected_A, diagnostic_triggered_B=expected_B, final_alert=False,
        input_sha256=sha(canonical(saved['input'])),
        raw_json_sha256=sha(canonical(saved['engine']['raw'])) if saved['engine'] else None,
        candidates=all_slots)


def check_arrays(fit):
    assert fit['native_binary_sha256'] == CANDIDATE_C_SHA256
    assert fit['parameters'] == PARAMETERS and fit['candidate_validation'] == 'PASS'
    assert sha(struct.pack('<'+'d'*len(fit['input']), *fit['input'])) == fit['input_sha256']
    assert sha(canonical(fit['raw'])) == fit['raw_json_sha256']
    assert sha(canonical(fit['arrays'])) == fit['posterior_bytes_sha256']
    for key, array in fit['arrays'].items():
        data = base64.b64decode(array['bytes_base64'], validate=True)
        assert sha(data) == array['sha256']
        dtype = array['dtype']
        assert dtype in ('<f4', '<f8'), dtype
        count = math.prod(array['shape'])
        assert len(data) == count * (4 if dtype == '<f4' else 8)
        decoded = struct.unpack('<'+('f' if dtype == '<f4' else 'd')*count, data)
        raw = fit['raw']
        for component in key.split('.'):
            raw = raw[component]
        def flatten(v):
            return [x for sub in v for x in flatten(sub)] if isinstance(v, list) else [v]
        flat = flatten(raw)
        assert len(flat) == count
        assert all(a == b if math.isfinite(a) else b is None for a, b in zip(decoded, flat))
    return len(fit['arrays'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    ledger = {}
    def load(path):
        blob = (ROOT/path).read_bytes()
        ledger[path] = sha(blob)
        return json.loads(blob)
    packet = load('docs/m6b-ready/g2-science-decisions/SCIENTIFIC_DECISIONS.json')
    assert packet['decisions']['G01']['parameters'] == PARAMETERS and len(PARAMETERS) == 24
    timeline = load('docs/m5/science-s1/data/timeline.json')
    lookup = {(s['batch'], s['scenario']): s['prefixes'] for s in timeline}
    scenarios = ['stable', 'sustained', 'growth_19', 'growth_20', 'growth_21', 'spike', 'recovery']
    counts = dict(replays=0, prefixes=0, detailed_prefixes=0, native_candidate_slots=0,
                  strict_prefixes=0, reference_arrays=0, reference_fits_read=0, new_native_fits=0)
    result = []
    # The patch makes accidental native invocation an assertion failure.
    with patch('flash.rbeast_adapter.subprocess.run', side_effect=AssertionError('native execution forbidden')):
        for parent, batches in [('docs/m5/patch-p1/data', ['m5-p1-c-batch01', 'm5-p1-c-batch02']),
                ('docs/m6b-ready/g1-s2-c/data', ['s2-c-batch01', 's2-c-batch02'])]:
            for batch in batches:
                for scenario in scenarios:
                    path = parent+'/'+batch+'/decisions-'+scenario+'.json'
                    saved = load(path)
                    fixture_doc = load('tests/m5_fixtures/records/'+scenario+'.json')
                    fixture = fixture_doc['records'] if isinstance(fixture_doc, dict) else fixture_doc
                    assert isinstance(fixture, list) and len(fixture) == 45
                    assert len(saved['replays']) == 20
                    first = saved['replays'][0]['decisions']
                    rows = None
                    for repeat in saved['replays']:
                        assert repeat['decisions'] == first
                        checked = [check_prefix(d, fixture) for d in repeat['decisions']]
                        assert len(checked) == 45
                        counts['replays'] += 1
                        counts['prefixes'] += len(checked)
                        if rows is None:
                            rows = checked
                        else:
                            assert checked == rows
                    # Compare all six existing sensitivity diagnostics without making them rules.
                    p1_batch = batch.replace('s2-c-', 'm5-p1-c-')
                    for r, old in zip(rows, lookup[p1_batch, scenario]):
                        assert r['triggered_A'] == old['persistence_triggers']['A']['span_inclusive_gt20']
                        assert r['diagnostic_triggered_B'] == old['persistence_triggers']['B']['span_inclusive_gt20']
                        r['sensitivity_only'] = old['persistence_triggers']
                    counts['detailed_prefixes'] += len(rows)
                    counts['native_candidate_slots'] += sum(len(r['candidates']) for r in rows)
                    result.append(dict(batch=batch, scenario=scenario, source=path,
                        first_detection_trigger=next((r['iteration'] for r in rows if r['detection_trigger']), None),
                        first_diagnostic_B=next((r['iteration'] for r in rows if r['diagnostic_triggered_B']), None),
                        A_B_disagreements=[r['iteration'] for r in rows if bool(r['triggered_A']) != bool(r['diagnostic_triggered_B'])],
                        prefixes=rows))
        # Historical strict assertion remains whole-output equality, including raw arrays.
        for path in ['docs/m5/patch-p1/data/C-strict-prefix-raw.json',
                     'docs/m6b-ready/g1-s2-c/runtime/prefix-capture.json']:
            capture = load(path)
            assert len(capture['full']) == 45 and len(capture['short']) == 24
            assert capture['full'][:24] == capture['short']
            for key in ('full', 'short'):
                fixture = capture[key][-1]['input']
                rows = [check_prefix(d, fixture) for d in capture[key]]
                counts['strict_prefixes'] += len(rows)
            assert [check_prefix(d, capture['full'][-1]['input']) for d in capture['full'][:24]] == rows
        # Only two fixed C c3-auto-fresh reference cells are decoded, not a new matrix.
        for batch in ('s2-c-batch01', 's2-c-batch02'):
            doc = load('docs/m6b-ready/g1-s2-c/data/'+batch+'/reference-pinned-c3-auto-fresh.json')
            assert len(doc['fits']) == 20
            for fit in doc['fits']:
                counts['reference_arrays'] += check_arrays(fit)
                counts['reference_fits_read'] += 1
            assert all(f['raw'] == doc['fits'][0]['raw'] and f['arrays'] == doc['fits'][0]['arrays'] for f in doc['fits'])
        native = load('docs/m6b-ready/g1-c-optin/evidence/verification03/native/candidate_c.json')
        identity = native['engine']['runtime_identity']
        assert identity['native_sha256'] == CANDIDATE_C_SHA256 and identity['mapped_library_segments']
        assert native['engine']['runtime_selection'] == 'candidate-c-opt-in'
        assert native['engine']['worker_exit_code'] == 0 and native['engine']['native_fit_started']
        wrong = load('docs/m6b-ready/g1-c-optin/evidence/verification03/native/wrong_binary.json')
        assert wrong['engine']['worker_exit_code'] == 78 and wrong['engine']['native_fit_started'] is False
        comparison = load('docs/m6b-ready/g1-s2-c/data/comparison.json')
        assert all(comparison[k] == 'PASS' for k in ['C_integrity', 'C_native_validity', 'C_numerical', 'C_decisions'])
    output = dict(status='PASS_LOCAL_CPU_HISTORICAL_RULES_ONLY', counts=counts,
        machine=platform.node(), platform=platform.platform(), python=sys.version,
        historical_native_sha256=CANDIDATE_C_SHA256, binary_this_round='NOT_PROBED',
        inherited_runtime_identity=identity, inputs_sha256=ledger,
        source_sha256={p:sha((ROOT/p).read_bytes()) for p in
            ['flash/change_detection.py', 'flash/rbeast_adapter.py', 'tests/m6b_ready_approved_detection.py',
             'docs/m6b-ready/g2-approved-detector/verify_history.py']},
        final_alert=False, GPU_experiments=0, scenarios=result)
    (args.output/'history.json').write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=output['status'], counts=counts,
        results=[{k:s[k] for k in ['batch', 'scenario', 'first_detection_trigger', 'first_diagnostic_B', 'A_B_disagreements']} for s in result]), indent=2))


if __name__ == '__main__':
    main()
