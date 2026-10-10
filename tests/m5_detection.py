"""Arithmetic/invalid-native fixtures only, not a real Rbeast PASS."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.change_detection import DetectionConfig, preprocess, filter_candidates, detect, prefix_replay
from flash.iteration_reporter import IterationRecord
from flash.rbeast_adapter import candidates_from_raw


def records(values, ids=None):
    return [IterationRecord('fixture',0,i,x,'2026-10-10T00:00:00+00:00','synthetic','fixture',False)
            for i,x in zip(ids or range(1,len(values)+1),values)]


def candidate(i,p=0.9):return dict(index0=i,slot=i,cp=i+1,cpPr=p,reason=None)


class Tests(unittest.TestCase):
    def test_means_latest_and_recovery(self):
        p=dict(values_ms=[10,10,20,20,20],index0_to_iteration=[4,5,6,7,8])
        r=filter_candidates(p,[candidate(2)],8,DetectionConfig())[0]
        self.assertEqual(r['statistics']['baseline_mean'],10)
        self.assertEqual(r['statistics']['degraded_mean'],20)
        self.assertEqual(r['statistics']['recent_mean'],20)
        self.assertEqual(r['stages']['recovery']['value'],0)
        self.assertEqual(r['status'],'AMBIGUOUS_SPEC')
        p['values_ms']=[10,10,50,10,10]
        r=filter_candidates(p,[candidate(2)],8,DetectionConfig())[0]
        self.assertAlmostEqual(r['stages']['recovery']['value'],1)
        self.assertEqual(r['reason'],'TRANSIENT_RECOVERY')

    def test_right_endpoint_zero_denominator(self):
        for vals,i in [([10,10,20],2),([10,10,10],1),([20,20,20],0)]:
            p=dict(values_ms=vals,index0_to_iteration=list(range(4,4+len(vals))))
            r=filter_candidates(p,[candidate(i)],6,DetectionConfig())[0]
            self.assertEqual(r['status'],'INSUFFICIENT_EVIDENCE')
            self.assertIsNone(r['stages']['recovery']['value'])

    def test_spacing_original_iterations(self):
        p=dict(values_ms=[10,10,20,20,20],index0_to_iteration=[4,5,7,8,9])
        r=filter_candidates(p,[candidate(3),candidate(2),candidate(1)],9,DetectionConfig())
        self.assertEqual(r[1]['stages']['spacing']['original_iteration_distance'],2)
        self.assertEqual(r[2]['reason'],'ADJACENT_CHANGEPOINT')

    def test_preprocessing_mapping(self):
        p=preprocess(records([10]*20+[1000]+[10]*20),DetectionConfig())
        self.assertEqual(p['window_iterations'],list(range(12,42)))
        self.assertIsNone(p['iteration_to_index0']['21'])
        self.assertEqual(p['index0_to_iteration'][9],22)
        self.assertEqual(p['stages'][9]['reason'],'ZSCORE_OUTLIER')
        p=preprocess(records([1000,800,600]+[10]*7),DetectionConfig())
        self.assertEqual(p['index0_to_iteration'],list(range(4,11)))
        self.assertEqual(p['population_std_ms'],0)

    def test_input_defects(self):
        for ids in [[1,1],[1,3],[2,1]]:
            self.assertEqual(detect(records([10,11],ids))['status'],'INVALID_INPUT')
        self.assertEqual(detect([])['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(detect(records([10]*20))['reason'],'CONSTANT_SERIES_ZERO_VARIANCE')

    def test_native_shapes_and_indices(self):
        raw=dict(trend=dict(cp=[3,None],cpPr=[.9,None],cpOccPr=[0,.1,.7,0]))
        result=candidates_from_raw(raw,4)
        self.assertEqual(result[0]['index0'],2)
        self.assertEqual(result[0]['cpOccPr_at_coordinate'],.7)
        self.assertEqual(result[1]['reason'],'PADDED_SLOT')
        for change in [dict(cp=[0],cpPr=[.9]),dict(cp=[1],cpPr=[1.2])]:
            bad=dict(trend=dict(cpOccPr=[0]*4,**change))
            self.assertIsNotNone(candidates_from_raw(bad,4)[0]['reason'])
        with self.assertRaises(ValueError):candidates_from_raw({},4)
        with self.assertRaises(ValueError):candidates_from_raw(dict(trend=dict(cp=[],cpPr=[],cpOccPr=[])),4)

    def test_threshold_sensitivity_facts(self):
        p=dict(values_ms=[100,100,120,120,120],index0_to_iteration=[4,5,6,7,8])
        r=filter_candidates(p,[candidate(2,.8)],8,DetectionConfig())[0]
        self.assertTrue(r['stages']['probability']['passed'])
        self.assertEqual(r['stages']['degradation']['duration_growth'],.2)
        self.assertFalse(r['stages']['degradation']['duration_growth_pass'])
        self.assertAlmostEqual(r['stages']['degradation']['throughput_loss'],1/6)
        self.assertFalse(r['stages']['persistence']['decision'] is not None)
        with self.assertRaises(ValueError):DetectionConfig(window=31)

    def test_prefix_causality(self):
        class AuditOnly:
            def __init__(self):self.inputs=[]
            def analyze(self,v):
                self.inputs.append(v[:]);return dict(status='OK',candidates=[])
        rs=records([10+i%3 for i in range(45)])
        a=AuditOnly();full=prefix_replay(rs,a)
        b=AuditOnly();short=prefix_replay(rs[:20],b)
        self.assertEqual(full[:20],short)
        self.assertEqual(a.inputs[0],[r.iteration_time_ms for r in rs[3:11]])
        self.assertTrue(all(e['latest_iteration']==i for i,e in enumerate(full,1)))
        self.assertTrue(all(not e['final_alert'] for e in full))

if __name__=='__main__':unittest.main()
