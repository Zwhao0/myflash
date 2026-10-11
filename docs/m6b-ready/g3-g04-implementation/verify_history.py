"""ADAPTATION: reuse task06 evidence; EXTENSION CPU replay, evaluator joins last."""
import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from flash.localization import analyze, analyze_approved_g04
from flash.profile_input import read_records


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inputs, rows, one_scope = {}, [], []
    def read(path):
        inputs[str(path.relative_to(ROOT))] = digest(path)
        return json.loads(path.read_text())
    matrix = read(ROOT / 'docs/m6b-ready/g3-g04-decisions/matrix.json')
    historical = {r['id']: r for r in matrix['rows']}
    names = read(ROOT / 'tests/m4_cases/index.json')
    assert len(names) == 65
    for name in names:
        folder = ROOT / 'tests/m4_cases' / name
        bundle = read(folder / 'input.json')
        ingestion_error = None
        if (folder / 'ingestion.json').exists():
            config = read(folder / 'ingestion.json')
            supplements = read(folder / config['supplements']) if config.get('supplements') else None
            paths = [folder / f for f in config['records']]
            for path in paths:
                inputs[str(path.relative_to(ROOT))] = digest(path)
            try:
                bundle['records'], _ = read_records(paths, config['format'], bundle['context'], supplements)
            except (ValueError, KeyError, TypeError) as error:
                ingestion_error = str(error)
        if ingestion_error is None:
            actual = analyze_approved_g04(bundle)
        else:
            # Raw ingestion gate remains unchanged; no substituted normalized data.
            actual = dict(status='INCOMPLETE', candidate_ranks=[], final_fault_ranks=[],
                          final_alert=False, ingestion_error=ingestion_error)
        key = 'fixture/' + name
        old = historical[key]
        assert actual['status'] == old['recommended']['status'], (key, actual['status'], old['recommended'])
        assert actual['candidate_ranks'] == old['recommended']['candidate_ranks'], key
        assert actual['final_fault_ranks'] == [] and not actual['final_alert'], key
        if old['kind'] == 'synthetic_fixture' and old['recommended']['status'] == 'INCOMPLETE':
            one_scope.append(name)
            assert actual['groups'], key
            selected = [g for t in actual['tags'].values() for g in t['selected_groups']]
            assert any(c['sample_count'] == 1 for h in selected for c in actual['groups'][h]['local_communicators']), key
        rows.append(dict(id=key, task06_recommended=old['recommended'], actual=actual))
    assert len(one_scope) == 14, one_scope
    supplement = read(ROOT / 'docs/m4/supplement/samples.json')
    saved = read(ROOT / 'docs/m4/supplement/results.json')['results']
    lookup = {(r['run_id'], r['epoch']): r for r in saved}
    predictions = []
    full_equal = 0
    for bundle in supplement['bundles']:
        context = bundle['context']
        key = (context['run_id'], context['profile_epoch'])
        predictions.append((key[0] + '/epoch' + str(key[1]), bundle, lookup[key]['prediction']))
    for epoch in [1, 2]:
        predictions.append(('m4-multigroup-normal-01/epoch' + str(epoch),
            read(ROOT / ('docs/m4/multigroup-input-epoch%d.json' % epoch)),
            read(ROOT / ('docs/m4/multigroup-prediction-epoch%d.json' % epoch))))
    assert len(predictions) == 32
    for key, bundle, saved_default in predictions:
        default = analyze(bundle)
        assert default == saved_default, key
        full_equal += 1
        actual = analyze_approved_g04(bundle)
        old = historical[key]
        assert actual['status'] == old['recommended']['status'], key
        assert actual['candidate_ranks'] == old['recommended']['candidate_ranks'], key
        assert actual['final_fault_ranks'] == [] and not actual['final_alert'], key
        # Independent truth/scenario is attached only after both predictions finish.
        rows.append(dict(id=key, task06_recommended=old['recommended'], actual=actual,
                         default_whole_prediction_equal=True, evaluation_only=old['evaluation_only']))
    summary = dict(status='PASS', default_full_predictions_equal=full_equal, fixtures=65,
        approved_normalized_replays=97, single_scope_valid_to_INCOMPLETE=one_scope,
        approved_statuses=dict(Counter(r['actual']['status'] for r in rows)),
        new_native_fits=0, new_gpu_runs=0, final_alert=False,
        reused_task06_matrix_sha256=inputs['docs/m6b-ready/g3-g04-decisions/matrix.json'])
    out = dict(summary=summary, rows=rows, input_sha256=inputs,
        source_sha256={s: digest(ROOT / s) for s in ['flash/localization.py', 'flash/profile_input.py',
            'tests/m6b_ready_approved_localization.py', 'docs/m6b-ready/g3-g04-implementation/verify_history.py']},
        host=platform.node(), platform=platform.platform(), python=sys.version, argv=sys.argv)
    (args.output / 'history.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
