"""ADAPTATION cursor boundaries; EXTENSION deterministic CPU MemoryStore tests.

Source: tasks/06b_ready_g0f_cursor.md. No Redis, native fits or GPU work.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flash.iteration_reporter import IterationRecord
from flash.m6_controller import GlobalController
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_store import MemoryStore, transaction


class CountingStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.read_calls = 0

    def read(self, run):
        self.read_calls += 1
        return super().read(run)


class CursorExtra(unittest.TestCase):
    def setUp(self):
        self.store = CountingStore()
        self.run = 'm6b-g0f-cpu'
        GlobalController(self.store, self.run, {'node-0': [0], 'node-1': [1]})
        self.publisher = IterationPublisher(self.store, self.run, 0, clock=lambda: 10.0)
        self.reader = IterationReader(self.store, self.run, 0)

    def record(self, iteration):
        return IterationRecord(self.run, 0, iteration, 100.0,
            '2026-10-11T00:00:00+00:00', 'CPU_SIMULATED_FRAMEWORK',
            'cpu_simulated_iteration_end', False)

    def publish(self, count):
        for iteration in range(1, count + 1):
            self.assertEqual(self.publisher.publish(self.record(iteration))['status'], 'WRITE_CONFIRMED')

    def test_invalid_cursors_before_any_store_read(self):
        class IntSubclass(int):
            pass
        invalid = (True, False, -1, 0.5, 1.0, '1', float('nan'),
                   float('inf'), float('-inf'), IntSubclass(1), [], {})
        # A missing/offline run must not hide invalid input or issue a read.
        for state in ('empty', 'populated', 'missing', 'offline'):
            if state == 'populated':
                self.publish(1)
            elif state == 'missing':
                self.store.values.clear()
            elif state == 'offline':
                self.store.online = False
            for cursor in invalid:
                with self.subTest(state=state, cursor=repr(cursor)):
                    before = self.store.read_calls
                    with self.assertRaisesRegex(ValueError, '^invalid after_iteration$'):
                        self.reader.read(after_iteration=cursor)
                    self.assertEqual(self.store.read_calls, before)

    def test_none_keeps_full_retained_window(self):
        self.publish(501)
        result = self.reader.read()
        self.assertEqual(result['status'], 'READ_CONFIRMED')
        self.assertEqual([r.iteration for r in result['records']], list(range(2, 502)))

    def test_exact_500_boundaries_keep_full_window(self):
        self.publish(500)
        for cursor in (0, 499, 500):
            with self.subTest(cursor=cursor):
                result = self.reader.read(after_iteration=cursor)
                self.assertEqual(result['status'], 'READ_CONFIRMED')
                self.assertEqual([r.iteration for r in result['records']], list(range(1, 501)))

    def test_future_reason_and_no_fabricated_records(self):
        self.publish(1)
        before = self.store.read(self.run)
        for cursor in (2, 10**100):
            with self.subTest(cursor=cursor):
                result = self.reader.read(after_iteration=cursor)
                self.assertEqual(result['status'], 'INSUFFICIENT_EVIDENCE')
                self.assertEqual(result['reason'], 'consumer cursor ahead of last confirmed iteration')
                self.assertNotIn('records', result)
        self.assertEqual(self.store.read(self.run), before)

    def test_adjacent_retention_gap_preserved(self):
        self.publish(502)
        self.assertEqual(self.reader.read(after_iteration=1)['status'], 'INSUFFICIENT_EVIDENCE')
        result = self.reader.read(after_iteration=2)
        self.assertEqual(result['status'], 'READ_CONFIRMED')
        self.assertEqual([r.iteration for r in result['records']], list(range(3, 503)))

    def test_hash_corruption_not_hidden_by_future_cursor(self):
        self.publish(1)
        transaction(self.store, self.run,
            lambda doc: doc['iterations']['0']['records'][0].update(sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'iteration data hash mismatch'):
            self.reader.read(after_iteration=2)

    def test_retention_corruption_not_hidden_by_future_cursor(self):
        self.publish(1)
        transaction(self.store, self.run, lambda doc: doc['iterations']['0'].update(last=2))
        with self.assertRaisesRegex(ValueError, 'iteration retention/order mismatch'):
            self.reader.read(after_iteration=3)

    def test_lost_commit_reply_read_then_exact_retry(self):
        self.store.lose_reply = True
        record = self.record(1)
        result = self.publisher.publish(record)
        self.assertEqual(result['status'], 'WRITE_UNCONFIRMED')
        self.assertFalse(result['confirmed'])
        self.assertEqual(self.reader.read(after_iteration=2)['status'], 'INSUFFICIENT_EVIDENCE')
        result = self.reader.read(after_iteration=1)
        self.assertEqual(result['status'], 'READ_CONFIRMED')
        self.assertEqual(result['records'], [record])
        self.assertEqual(self.publisher.publish(record)['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(self.reader.read(after_iteration=0)['records'], [record])


if __name__ == '__main__':
    unittest.main(verbosity=2)
