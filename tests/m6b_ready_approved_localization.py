"""EXTENSION: deterministic CPU arithmetic/identity cases; no GPU evidence."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.localization import analyze, analyze_approved_g04, _g04_cv, _g04_threshold
from flash.profile_input import validate_bundle


def fixture(name):
    return json.loads((ROOT / 'tests/m4_cases' / name / 'input.json').read_text())


def make(groups, labels=None):
    """Each hash specifies rank -> [local-instance scope-duration lists]."""
    prototype = fixture('single_group_min_rank')['records'][0]
    bundle = dict(schema_version=1, context=dict(run_id='cpu-g04', profile_epoch=1),
                  communicators=[], records=[], parallel_states=[])
    sequences = {}
    for h, ranks in groups.items():
        members = sorted(ranks)
        d = dict(id_hash=h, members=members, local_instances=[])
        for rank, instances in ranks.items():
            for generation, scopes in enumerate(instances, 1):
                process = 'p' + str(rank)
                d['local_instances'].append(dict(node_id='n0', global_rank=rank,
                    process_instance=process, comm_generation=generation, comm_rank=members.index(rank),
                    expected_samples=len(scopes), expected_records=len(scopes)))
                for duration in scopes:
                    sequences[rank] = sequences.get(rank, 0) + 1
                    r = dict(prototype, run_id='cpu-g04', id_hash=h, global_rank=rank,
                        process_instance=process, comm_generation=generation, comm_rank=members.index(rank),
                        comm_size=len(members), duration_us=duration, sample_seq=sequences[rank])
                    bundle['records'].append(r)
        bundle['communicators'].append(d)
    if labels is None:
        labels = {'DP': list(groups)}
    for label, hashes in labels.items():
        for h in hashes:
            bundle['parallel_states'].append(dict(label=label, id_hashes=[h], members=sorted(groups[h]),
                                                  evidence='explicit CPU group declaration'))
    return bundle


A, B, C = 'a' * 64, 'b' * 64, 'c' * 64


def pair(x, y):
    return make({A: {0: [[x, x]], 1: [[y, y]]}})


class ApprovedG04(unittest.TestCase):
    def result(self, bundle, status, candidates=None):
        original = copy.deepcopy(bundle)
        r = analyze_approved_g04(bundle)
        self.assertEqual(r['status'], status)
        if candidates is not None:
            self.assertEqual(r['candidate_ranks'], candidates)
        self.assertEqual(r['final_fault_ranks'], [])
        self.assertFalse(r['final_alert'])
        self.assertEqual(bundle, original)
        json.dumps(r, allow_nan=False)
        return r

    def test_single_group_min_rank(self):
        r = self.result(pair(2, 18), 'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual(r['tags']['DP']['stage1'], 'SINGLE_GROUP_DIRECT')
        self.assertIsNone(r['tags']['DP']['group_cv'])

    def test_singleton_excluded(self):
        r = self.result(make({A: {0: [[100, 100]]}, B: {0: [[2, 2]], 1: [[18, 18]]}}),
                        'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual(r['tags']['DP']['excluded_single_rank'], [A])
        self.assertEqual(r['tags']['DP']['selected_groups'], [B])

    def test_stage1_max_not_plot_mean(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[40, 40]]},
                             B: {0: [[30, 30]], 1: [[30, 30]]}}), 'PROVISIONAL_CANDIDATE', [0])
        row = r['tags']['DP']
        self.assertEqual(row['selected_groups'], [A])
        self.assertLess(row['clique_scores']['scores'][A], row['clique_scores']['scores'][B])

    def test_stage1_passing_cv_max_tie(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[18, 18]]},
                             B: {0: [[2, 2]], 1: [[18, 18]]},
                             C: {0: [[2, 2]], 1: [[2, 2]]}}), 'AMBIGUOUS_SPEC', [0])
        self.assertEqual(r['tags']['DP']['selected_groups'], [A, B])
        self.assertIn('MAX_GROUP_TIE', r['reasons'])
        self.assertEqual(len(r['tags']['DP']['stage2']), 2)

    def test_equal_group_maxima_cv_skip(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[18, 18]]},
                             B: {0: [[2, 2]], 1: [[18, 18]]}}), 'NO_CANDIDATE', [])
        self.assertEqual(r['tags']['DP']['selected_groups'], [])

    def test_min_rank_tie(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[2, 2]], 2: [[18, 18]]}}), 'AMBIGUOUS_SPEC', [0, 1])
        self.assertIn('MIN_RANK_TIE', r['reasons'])

    def test_weights_flip_is_diagnostic_only(self):
        # Q-TWO complete analogue of the original unequal-count fixture.
        r = self.result(make({A: {0: [[1] * 18, [100] * 2], 1: [[20] * 2, [30] * 18]}}),
                        'PROVISIONAL_CANDIDATE', [1])
        row = r['tags']['DP']['stage2'][A]
        self.assertEqual(row['minimum_ranks'], [1])
        self.assertEqual(row['sensitivity']['W_SCOPE']['minimum_ranks'], [0])
        self.assertTrue(row['sensitivity']['W_SCOPE']['diagnostic_only'])
        self.assertEqual(set(r['cross_tag']['support']), {'1'})
        old = self.result(fixture('aggregation_weights_disagree'), 'INCOMPLETE', [])
        obs = old['tags']['DP']['stage2'][A]
        self.assertEqual(obs['minimum_ranks'], [1])
        self.assertEqual(obs['sensitivity']['W_SCOPE']['minimum_ranks'], [0])

    def test_r_group_19_20_21(self):
        self.result(pair(81, 119), 'NO_CANDIDATE', [])
        r = self.result(pair(8, 12), 'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual(r['tags']['DP']['stage2'][A]['thresholds']['0']['exact_score'], '1/5')
        self.assertEqual(r['tags']['DP']['stage2'][A]['thresholds']['0']['score'], 0.2)
        self.result(pair(79, 121), 'PROVISIONAL_CANDIDATE', [0])

    def test_nominal_20_float_rational_disagreement(self):
        r = self.result(pair(80, 120), 'AMBIGUOUS_SPEC', [])
        t = r['tags']['DP']['stage2'][A]['thresholds']['0']
        self.assertFalse(t['floating_gate'])
        self.assertTrue(t['exact_gate'])
        self.assertEqual(t['exact_score'], '1/5')
        self.assertLess(t['score'], 0.2)

    def test_cv_convention_disagreement(self):
        r = self.result(pair(9.2, 10.8), 'AMBIGUOUS_SPEC', [])
        self.assertIn('CV_CONVENTION_DISAGREEMENT', r['reasons'])
        self.assertEqual(_g04_cv([9.2, 10.8])['floating_gate'], {'population': False, 'sample': True})

    def test_cv_exact_boundary_and_neighbors(self):
        self.assertEqual(_g04_cv([90, 110])['decision'], 'AMBIGUOUS_SPEC')
        self.assertIn('CV_NUMERIC_DISAGREEMENT', _g04_cv([90, 110])['reasons'])
        self.assertEqual(_g04_cv([9, 11])['decision'], 'ABOVE')
        self.assertEqual(_g04_cv([90.00001, 109.99999])['decision'], 'AMBIGUOUS_SPEC')
        self.assertEqual(_g04_cv([89.99999, 110.00001])['decision'], 'ABOVE')
        x = _g04_cv([1, 1.1, 0.9])
        self.assertIsNotNone(x['sample'])
        self.assertEqual(x['sample'] >= 0.1, x['exact_gate']['sample'])

    def test_stage1_cv_guard(self):
        r = self.result(make({A: {0: [[1, 1]], 1: [[9.2, 9.2]]},
                             B: {0: [[1, 1]], 1: [[10.8, 10.8]]}}), 'AMBIGUOUS_SPEC', [])
        self.assertEqual(r['tags']['DP']['stage2'], {})
        self.assertIn('CV_CONVENTION_DISAGREEMENT', r['reasons'])

    def test_zero_mean_and_insufficient_sample(self):
        self.result(pair(0, 0), 'AMBIGUOUS_SPEC', [])
        self.assertEqual(_g04_cv([0, 0])['population'], None)
        self.assertEqual(_g04_cv([1])['decision'], 'AMBIGUOUS_SPEC')
        self.assertIsNone(_g04_cv([1])['sample'])
        self.assertEqual(_g04_threshold({0: 0, 1: 0}, 0)['decision'], 'AMBIGUOUS_SPEC')
        self.result(make({A: {0: [[2]], 1: [[18]]}}), 'INCOMPLETE', [])

    def test_group_members_do_not_inflate_scope_support(self):
        b = pair(2, 18)
        for local in b['communicators'][0]['local_instances']:
            local['expected_samples'] = 1
        for r in b['records']:
            r.update(timing_scope='group_shared', group_id=1, group_depth=1)
        r = self.result(b, 'INCOMPLETE', [])
        self.assertEqual([c['sample_count'] for c in r['groups'][A]['local_communicators']], [1, 1])
        for record in b['records'][1::2]:
            record.update(group_id=2, group_depth=2)
        for local in b['communicators'][0]['local_instances']:
            local['expected_samples'] = 2
        r = self.result(b, 'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual([c['sample_count'] for c in r['groups'][A]['local_communicators']], [2, 2])
        # count is payload elements, never temporal sample support.
        for record in b['records']:
            record['count'] = 4096
        self.assertEqual(analyze_approved_g04(b)['candidate_ranks'], [0])

    def test_cross_comm_shared_scope_and_identity(self):
        b = make({A: {0: [[2, 2]], 1: [[18, 18]]}, B: {0: [[2, 2]], 1: [[18, 18]]}},
                 {'DP': [A], 'TP': [B]})
        for h in (A, B):
            by_rank = {}
            for r in b['records']:
                if r['id_hash'] == h:
                    by_rank[r['global_rank']] = by_rank.get(r['global_rank'], 0) + 1
                    r.update(timing_scope='group_shared', group_id=by_rank[r['global_rank']], group_depth=1)
        r = self.result(b, 'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual(set(r['groups']), {A, B})
        self.assertEqual(r['groups'][A]['local_communicators'][0]['timing_scopes'],
                         r['groups'][B]['local_communicators'][0]['timing_scopes'])
        self.assertEqual(len(r['cross_tag']['support']['0']['evidence']), 2)
        self.assertTrue(r['risks'])

    def test_agree_and_conflict(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[18, 18]]}}, {'DP': [A], 'TP': [A]}),
                        'PROVISIONAL_CANDIDATE', [0])
        self.assertEqual(r['cross_tag']['support']['0']['labels'], ['DP', 'TP'])
        r = self.result(make({A: {0: [[2, 2]], 1: [[18, 18]]}, B: {0: [[18, 18]], 1: [[2, 2]]}},
                            {'DP': [A], 'TP': [B]}), 'AMBIGUOUS_SPEC', [0, 1])
        self.assertTrue(r['cross_tag']['conflict'])

    def test_incomplete_priority_retains_other_label_evidence(self):
        r = self.result(make({A: {0: [[2, 2]], 1: [[18, 18]]}, B: {0: [[2]], 1: [[18]]}},
                            {'DP': [A], 'TP': [B]}), 'INCOMPLETE', [0])
        self.assertIn('DP', r['cross_tag']['support']['0']['labels'])
        self.assertEqual(r['groups'][B]['local_communicators'][0]['avg_latency_us'], 2)

    def test_missing_invalid_data(self):
        for name in ['missing_rank', 'missing_duration', 'missing_parallel_states', 'duplicate_sample',
                     'bad_cuda_evidence', 'negative_duration', 'group_duration_mismatch', 'missing_sample']:
            with self.subTest(name=name):
                self.result(fixture(name), 'INCOMPLETE', [])
        self.result({}, 'INCOMPLETE', [])

    def test_no_candidate_and_zero_rank(self):
        self.result(pair(20, 20), 'NO_CANDIDATE', [])
        self.result(pair(0, 20), 'PROVISIONAL_CANDIDATE', [0])
        self.result(pair(math.ulp(0.0), math.ulp(0.0)), 'NO_CANDIDATE', [])
        self.result(pair(1e308, 1e308), 'NO_CANDIDATE', [])

    def test_evaluator_fields_never_change_output(self):
        b = pair(2, 18)
        baseline = analyze_approved_g04(b)
        b['expected'] = {'fault_rank': 1}
        b['evaluator'] = {'truth_ranks': [1], 'inject_at': 3, 'scenario': 'normal'}
        self.assertEqual(analyze_approved_g04(b), baseline)


if __name__ == '__main__':
    unittest.main()
