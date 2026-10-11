"""ADAPTATION approved-rule CPU contracts; artificial arithmetic, zero native fits."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flash.change_detection import DetectionConfig, detect, filter_candidates, preprocess, prefix_replay
from flash.rbeast_adapter import RbeastAdapter, PARAMETERS
from m5_detection import candidate, records


def filtered(values, mapping=None):
    return dict(values_ms=values, index0_to_iteration=mapping or list(range(4, 4+len(values))))


def row(values, i=2, mapping=None, p=.9, latest=None):
    prepared = filtered(values, mapping)
    return filter_candidates(prepared, [candidate(i, p)],
        latest or prepared['index0_to_iteration'][-1], DetectionConfig(), approved_rules=True)[0]


class RawAdapter:
    def __init__(self, coordinate=3, probability=.9):
        self.coordinate, self.probability, self.inputs = coordinate, probability, []

    def analyze(self, values):
        self.inputs.append(values[:])
        return dict(status='OK', parameters=copy.deepcopy(PARAMETERS), raw=dict(trend=dict(cp=[self.coordinate, None],
            cpPr=[self.probability, None], cpOccPr=[.1]*len(values))), candidates=[])


class Tests(unittest.TestCase):
    def test_inclusive_20_21_22(self):
        for count, passed in [(20, False), (21, True), (22, True)]:
            r = row([100]*2 + [130]*count)
            self.assertEqual(r['stages']['persistence']['observed_original_iterations'], count)
            self.assertEqual(r['detection_trigger'], passed)
            self.assertTrue(r['model_candidate'])
            self.assertTrue(r['qualified_candidate'])
            self.assertFalse(r['final_alert'])

    def test_strict_binary64_A_and_diagnostic_B(self):
        cases = [(119, False, False), (120, False, False), (121, True, False),
                 (125, True, False), (126, True, True),
                 (math.nextafter(120., -math.inf), False, False),
                 (math.nextafter(120., math.inf), True, False)]
        for d, a, b in cases:
            with self.subTest(d=d):
                # Two identical right samples preserve the exact nextafter mean.
                # The sparse mapping isolates arithmetic from the age gate.
                r = row([100]*2 + [d]*2, mapping=[4, 5, 6, 26])
                self.assertEqual(r['statistics']['degraded_mean'], d)
                g = r['stages']['degradation']
                self.assertEqual(g['duration_growth'], (d-100)/100)
                self.assertEqual(g['throughput_loss'], (d-100)/d)
                self.assertEqual(g['duration_growth_pass'], a)
                self.assertEqual(g['throughput_loss_pass'], b)
                self.assertEqual(r['detection_trigger'], a)
                self.assertIsNone(g['measured_throughput'])

    def test_compressed_count_does_not_gate_original_span(self):
        # Original21 positions but only19 retained samples; no retained_samples AND.
        mapping = [4, 5] + [j for j in range(6, 27) if j not in (10, 20)]
        r = row([100]*2 + [130]*19, mapping=mapping)
        self.assertEqual(r['statistics']['right_sample_count'], 19)
        self.assertEqual(r['iteration'], 6)
        self.assertTrue(r['detection_trigger'])
        # k1/k2 true at only3 positions must not OR into the primary rule.
        self.assertFalse(row([100]*2 + [130]*3)['detection_trigger'])

    def test_real_preprocess_removal_and_compressed_cp(self):
        rs = records([100]*10 + [1000] + [130]*20)
        prepared = preprocess(rs, DetectionConfig())
        self.assertEqual(prepared['window_iterations'], list(range(2, 32)))
        self.assertIsNone(prepared['iteration_to_index0']['11'])
        i = prepared['index0_to_iteration'].index(12)
        self.assertEqual(i, 7)
        r = filter_candidates(prepared, [candidate(i)], 31, DetectionConfig(), approved_rules=True)[0]
        self.assertEqual(r['iteration'], 12)
        self.assertFalse(r['detection_trigger'])
        prepared = preprocess(records([100]*10 + [1000] + [130]*21), DetectionConfig())
        i = prepared['index0_to_iteration'].index(12)
        r = filter_candidates(prepared, [candidate(i)], 32, DetectionConfig(), approved_rules=True)[0]
        self.assertTrue(r['detection_trigger'])

    def test_drift_uses_current_cp_and_current_means(self):
        a = row([100]*2 + [130]*21)
        b = row([100]*3 + [130]*20, i=3)
        self.assertTrue(a['detection_trigger'])
        self.assertEqual(a['iteration'], 6)
        self.assertEqual(b['iteration'], 7)
        self.assertFalse(b['detection_trigger'])
        rs = records([100]*5 + [130]*40)
        prepared = preprocess(rs, DetectionConfig())
        self.assertEqual(prepared['index0_to_iteration'], list(range(16, 46)))
        r = filter_candidates(prepared, [candidate(2)], 45, DetectionConfig(), approved_rules=True)[0]
        self.assertEqual(r['statistics']['baseline_mean'], 130)
        self.assertFalse(r['detection_trigger'])
        self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')

    def test_probability_and_spacing_before_recovery(self):
        for p, expected in [(math.nextafter(.8, 0), False), (.8, True)]:
            self.assertEqual(row([100]*2+[130]*21, p=p)['detection_trigger'], expected)
        prepared = filtered([100, 100, 500, 130, 130, 130])
        rows = filter_candidates(prepared, [candidate(3), candidate(2)], 9,
            DetectionConfig(), approved_rules=True)
        self.assertEqual(rows[0]['reason'], 'TRANSIENT_RECOVERY')
        self.assertEqual(rows[1]['reason'], 'ADJACENT_CHANGEPOINT')
        self.assertFalse(any(x['detection_trigger'] for x in rows))
        rows = filter_candidates(prepared, [candidate(2, .79), candidate(3)], 9,
            DetectionConfig(), approved_rules=True)
        self.assertIsNone(rows[1]['stages']['spacing']['original_iteration_distance'])

    def test_exact_recovery_and_direction_precedence(self):
        r = row([100]*2 + [250, 115, 115], latest=40)
        self.assertEqual(r['stages']['recovery']['value'], .75)
        self.assertEqual(r['reason'], 'TRANSIENT_RECOVERY')
        for values in ([100]*2+[90]*21, [100]*23):
            r = row(values)
            self.assertFalse(r['detection_trigger'])
            self.assertFalse(r['qualified_candidate'])

    def test_invalid_values_and_insufficient_means_fail_closed(self):
        for bad in (None, 0, -1, True, '100', math.nan, math.inf):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                row([bad, 100]+[130]*21)
        for values, i in [([100, 130], 0), ([100, 130], 1), ([100]*4, 2),
                          ([5e-324]*2+[1e308]*21, 2)]:
            r = row(values, i=i)
            self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
            self.assertFalse(r['detection_trigger'])
        with patch('flash.change_detection.RbeastAdapter.analyze', side_effect=AssertionError('fit forbidden')):
            r = detect(records([1e308, 1e308]*10), approved_rules=True)
        self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertFalse(r['detection_trigger'])
        r = row([5e-324]*2+[1e100]*2, mapping=[4, 5, 6, 26])
        self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertIsNone(r['stages']['degradation']['duration_growth'])
        json.dumps(r, allow_nan=False)

    def test_input_missing_duplicate_order_empty_short_constant(self):
        for ids in ([1, 1], [1, 3], [2, 1]):
            self.assertEqual(detect(records([10, 11], ids), approved_rules=True)['status'], 'INVALID_INPUT')
        self.assertEqual(detect([{'bad': 'record'}], approved_rules=True)['status'], 'INVALID_INPUT')
        with patch('flash.change_detection.RbeastAdapter.analyze', side_effect=AssertionError('fit forbidden')):
            for rs in ([], records([10, 11]), records([10]*20)):
                r = detect(rs, approved_rules=True)
                self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
                self.assertFalse(r['detection_trigger'])

    def test_invalid_raw_and_padding(self):
        rs = records([100]*10+[130]*21)
        mutations = [dict(cp=[0], cpPr=[.9]), dict(cp=[3], cpPr=[1.01]),
                     dict(cp=[3, 3], cpPr=[.9, .9]), dict(cp=[3], cpPr=[]),
                     dict(cp=[None], cpPr=[.9]), dict(cp=[3], cpPr=[True]),
                     dict(cp=[3], cpPr=[.9], cpOccPr=[None]*28)]
        for mutation in mutations:
            adapter = RawAdapter()
            engine = adapter.analyze([100]*28)
            engine['raw']['trend'].update(mutation)
            with patch.object(adapter, 'analyze', return_value=engine):
                r = detect(rs, adapter, approved_rules=True)
            self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
            self.assertFalse(r['detection_trigger'])
        r = detect(rs, RawAdapter(coordinate=8), approved_rules=True)
        self.assertTrue(r['detection_trigger'])
        self.assertFalse(r['candidates'][-1]['model_candidate'])
        self.assertFalse(r['final_alert'])
        self.assertEqual(r['unresolved'], ['G20'])

    def test_engine_failure_never_becomes_no_trigger(self):
        rs = records([100]*10+[130]*21)
        for status, reason in [('BLOCKED', 'CANDIDATE_C_IDENTITY_REJECTED'),
                               ('INSUFFICIENT_EVIDENCE', 'NATIVE_TIMEOUT'),
                               ('INSUFFICIENT_EVIDENCE', 'NATIVE_WORKER_FAILED')]:
            a = RawAdapter()
            with patch.object(a, 'analyze', return_value=dict(status=status, reason=reason)):
                r = detect(rs, a, approved_rules=True)
            self.assertEqual((r['status'], r['reason']), (status, reason))
            self.assertFalse(r['detection_trigger'])

    def test_parameter_identity_and_missing_engine_output(self):
        rs = records([100]*10+[130]*21)
        for engine in ({}, dict(status='OK'), dict(status='OK', parameters={}),
                       dict(status='OK', parameters=dict(PARAMETERS, mcmc_seed=1))):
            adapter = RawAdapter()
            with patch.object(adapter, 'analyze', return_value=engine):
                r = detect(rs, adapter, approved_rules=True)
            self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
            self.assertFalse(r['detection_trigger'])

    def test_no_future_leakage_and_default_optin(self):
        rs = records([100+i%3 for i in range(45)])
        a, b = RawAdapter(), RawAdapter()
        full = prefix_replay(rs, a, approved_rules=True)
        short = prefix_replay(rs[:24], b, approved_rules=True)
        self.assertEqual(full[:24], short)
        self.assertEqual(a.inputs[:len(b.inputs)], b.inputs)
        self.assertTrue(all(not e['final_alert'] for e in full))
        old = detect(rs, RawAdapter())
        self.assertEqual(old['status'], 'AMBIGUOUS_SPEC')
        self.assertNotIn('detection_trigger', old)
        self.assertEqual(RbeastAdapter().candidate_c_python, None)
        for bad in ('true', 1, None):
            with self.assertRaises(ValueError):
                detect(rs, approved_rules=bad)


if __name__ == '__main__':
    unittest.main()
