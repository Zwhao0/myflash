"""ADAPTATION strict Reporter contract unit tests; not GPU experiments."""
import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import IterationRecord, IterationReporter, LocalHistory


def record(i=1, **changes):
    values=dict(run_id='test',global_rank=0,iteration=i,iteration_time_ms=10,
                timestamp='2026-10-10T00:00:00+00:00',source='fixture',
                timing_boundary='explicit complete iteration',cuda_completion_wait=False)
    values.update(changes)
    return IterationRecord(**values)


class ReporterTests(unittest.TestCase):
    def test_retention_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'history.json';h=LocalHistory(p,'test',0)
            for i in range(1,505):h.publish(record(i))
            self.assertEqual([r.iteration for r in h.load(p)],list(range(5,505)))
            h=LocalHistory(p,'test',0);h.publish(record(505))
            self.assertEqual(h.records[0].iteration,6)
            for i in [505,507,504]:
                with self.assertRaises(ValueError):h.publish(record(i))
            with self.assertRaises(ValueError):h.publish(record(506,global_rank=1))
            self.assertEqual(len(h.load(p)),500)

    def test_invalid_records(self):
        for kw in [dict(iteration_time_ms=x) for x in [0,-1,True,float('nan'),float('inf')]] + [dict(iteration=0),dict(iteration=True),dict(timestamp='2026-01-01'),dict(cuda_completion_wait=None),dict(source='')]:
            with self.assertRaises(ValueError):record(**kw)

    def test_callback_boundaries_abort(self):
        received=[];waits=[]
        class Sink:
            def publish(self,r):received.append(r)
        ticks=iter([1000000,4000000,5000000])
        r=IterationReporter(Sink(),'test',0,source='test',timing_boundary='test',completion_wait=lambda:waits.append(1),clock=lambda:next(ticks))
        with self.assertRaises(ValueError):r.end()
        r.begin(1)
        with self.assertRaises(ValueError):r.begin(1)
        value=r.end();self.assertEqual(value.iteration_time_ms,3)
        self.assertEqual(len(waits),2);self.assertEqual(len(received),1)
        r.begin(2);r.abort();self.assertEqual(len(received),1)

    def test_reload_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            for ids in [[1,1],[1,3],[2,1]]:
                p.write_text(json.dumps({'schema':1,'records':[dataclasses.asdict(record(i)) for i in ids]}))
                with self.assertRaises(ValueError):LocalHistory.load(p)

if __name__=='__main__':unittest.main()
