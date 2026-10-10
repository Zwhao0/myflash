"""EXTENSION rule arithmetic; ADAPTATION evidence integrity, never GPU/native PASS."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import m5_s1_analysis as a


class Rules(unittest.TestCase):
    def test_exact_boundaries(self):
        for d,expected_A in [(119,False),(120,False),(121,True)]:
            r=a.ratios(100,d)
            self.assertEqual(r['A']['value'],(d-100)/100)
            self.assertEqual(r['B']['value'],(d-100)/d)
            self.assertEqual(r['A']['passed'],expected_A)
            self.assertFalse(r['B']['passed'])
        self.assertFalse(a.ratios(100,125)['B']['passed'])
        self.assertTrue(a.ratios(100,126)['B']['passed'])

    def test_direction(self):
        for d in [100,90]:
            for x in a.ratios(100,d).values():
                self.assertLessEqual(x['value'],0);self.assertFalse(x['passed'])

    def test_invalid_no_zero_fill(self):
        for b,d in [(0,100),(100,0),(0,0),(-1,100),(100,-1),(None,100),(100,None),(True,100),('100',120),(100,float('nan')),(float('inf'),100)]:
            r=a.ratios(b,d)
            for x in r.values():
                self.assertIsNone(x['value']);self.assertIsNone(x['passed']);self.assertIsNotNone(x['reason'])
        self.assertEqual(a.ratios(0,100)['A']['reason'],'ZERO_DENOMINATOR')
        self.assertEqual(a.ratios(100,0)['B']['reason'],'ZERO_DENOMINATOR')

    def test_persistence_off_by_one(self):
        self.assertFalse(a.persistence(40,21,20,20)['span_inclusive_gt20'])
        p=a.persistence(41,21,21,20)
        self.assertTrue(p['span_inclusive_gt20']);self.assertFalse(p['elapsed_exclusive_gt20'])
        self.assertFalse(p['qualified_consecutive_prefixes_gt20'])
        p=a.persistence(42,21,21,21)
        self.assertTrue(p['elapsed_exclusive_gt20']);self.assertTrue(p['qualified_consecutive_prefixes_gt20'])
        self.assertFalse(a.persistence(41,21,19,21)['retained_right_gt20'])

    def test_guard_independent(self):
        for latest,k1,k2 in [(21,False,False),(22,True,False),(23,True,True)]:
            p=a.persistence(latest,21,latest-20,1)
            self.assertEqual(p['right_guard_original_k1'],k1);self.assertEqual(p['right_guard_original_k2'],k2)
        with self.assertRaises(ValueError):a.persistence(20,21,1,1)


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved=json.loads((a.ROOT/'docs/m5/patch-p1/data/m5-p1-c-batch01/decisions-sustained.json').read_text())['replays'][0]['decisions']
        cls.output=json.loads((a.ROOT/'docs/m5/science-s1/data/sensitivity.json').read_text())

    def test_saved_prefix_and_raw_mapping(self):
        history={}
        for saved in self.saved:
            row=a.analyze_prefix(saved,history)
            for c in row['candidates']:
                if c['index0'] is not None:
                    self.assertEqual(c['original_iteration'],row['mapping'][int(c['cp'])-1])
                    self.assertLessEqual(c['original_iteration'],row['iteration'])
            self.assertFalse(row['final_alert']);self.assertIsNone(row['final_alert_iteration'])

    def test_removed_outlier_and_rolling_window_mapping(self):
        series=json.loads((a.ROOT/'docs/m5/patch-p1/data/m5-p1-c-batch01/decisions-spike.json').read_text())['replays'][0]['decisions']
        prepared=a.prepare(series[29]['input'])
        self.assertIsNone(prepared['iteration_to_index0']['21'])
        self.assertNotIn(21,prepared['index0_to_iteration'])
        prepared=a.prepare(series[40]['input'])
        self.assertEqual(prepared['window_iterations'],list(range(12,42)))
        self.assertEqual(prepared['index0_to_iteration'][9],22)

    def test_future_invariance(self):
        history={};short=[a.analyze_prefix(x,history) for x in self.saved[:23]]
        altered=copy.deepcopy(self.saved)
        for x in altered[23:]:x['input']=[{'unusable_future':True}]
        history={};self.assertEqual(short,[a.analyze_prefix(x,history) for x in altered[:23]])

    def test_future_injected_into_prefix_rejected(self):
        saved=copy.deepcopy(self.saved[21]);saved['input'].append(self.saved[22]['input'][-1])
        with self.assertRaises(ValueError):a.analyze_prefix(saved,{})

    def test_missing_or_invalid_not_silently_skipped(self):
        for mutation in ['probability','occurrence','input','final','mapping','mean']:
            x=copy.deepcopy(self.saved[21])
            if mutation=='probability':x['engine']['raw']['trend']['cpPr'][0]=1.01
            elif mutation=='occurrence':x['engine']['raw']['trend']['cpOccPr'][0]=None
            elif mutation=='input':x['input'][0]['iteration_time_ms']=None
            elif mutation=='final':x['final_alert']=True
            elif mutation=='mapping':x['preprocessing']['index0_to_iteration'][0]=100
            else:x['candidates'][0]['statistics']['baseline_mean']=0
            with self.assertRaises(ValueError):a.analyze_prefix(x,{})

    def test_streak_reset_on_gap_and_drift(self):
        h={};a.analyze_prefix(self.saved[21],h);self.assertEqual(h[(21,'A')],1)
        a.analyze_prefix(self.saved[22],h);self.assertEqual(h[(21,'A')],2)
        a.analyze_prefix(self.saved[0],h);self.assertEqual(h,{})
        h={(20,'A'):20};r=a.analyze_prefix(self.saved[21],h)
        self.assertEqual(h[(21,'A')],1);self.assertNotIn((20,'A'),h)

    def test_all_rows_and_separate_options(self):
        self.assertEqual(len(self.output['scenarios']),14)
        for series in self.output['scenarios']:
            self.assertEqual([r['iteration'] for r in series['prefixes']],list(range(1,46)))
            for row in series['prefixes']:
                self.assertFalse(row['final_alert']);self.assertEqual(set(row['provisional']),{'A','B'})
                for c in row['candidates']:
                    if c['index0'] is not None:self.assertEqual(set(c['formulas']),{'A','B'})
        coverage=json.loads((a.ROOT/'docs/m5/science-s1/data/repeat-coverage.json').read_text())
        self.assertEqual(len(coverage),280);self.assertEqual(sum(c['prefixes'] for c in coverage),12600)

    def test_published_values_match_saved(self):
        history={};rows=[a.analyze_prefix(x,history) for x in self.saved]
        published=next(s['prefixes'] for s in self.output['scenarios'] if s['batch']=='m5-p1-c-batch01' and s['scenario']=='sustained')
        self.assertEqual(rows,published)

    def test_output_hash_index(self):
        root=a.ROOT/'docs/m5/science-s1/data'
        for p,h in json.loads((root/'hash-index.json').read_text()).items():
            self.assertEqual(a.sha((root/p).read_bytes()),h)

    def test_frozen_tree_and_input_hashes(self):
        index=json.loads((a.ROOT/'docs/m5/science-s1/data/input-hashes.json').read_text())
        self.assertEqual(index,a.preserved())

    def test_traceable_repository_and_paper_citations(self):
        d=json.loads((a.ROOT/'docs/m5/science-s1/data/source-receipts.json').read_text())
        lines=(a.ROOT/'references/chapter3_extracted.txt').read_text().splitlines()
        for r in d['paper']:
            line=lines[r['text_line']-1];self.assertIn(r['anchor'],line);self.assertEqual(a.sha(line.encode()),r['line_sha256'])
            self.assertEqual(r['original_pdf_page'],r['printed_page']+16)
        for path,h in d['paper_files'].items():self.assertEqual(a.sha((a.ROOT/path).read_bytes()),h)
        for r in d['upstream']:
            if r['nature']=='ADAPTATION':
                blob=(a.ROOT/r['path']).read_bytes();self.assertEqual(a.sha(blob),r['file_sha256'])
                span='\n'.join(blob.decode().splitlines()[r['line_start']-1:r['line_end']]);self.assertEqual(a.sha(span.encode()),r['span_normalized_lf_sha256'])
        from flash.rbeast_adapter import PARAMETERS
        self.assertEqual({k:v['value'] for k,v in d['parameters'].items()},PARAMETERS)
        self.assertTrue(all(v['paper_authority'] is False for v in d['parameters'].values()))


if __name__=='__main__':unittest.main()
