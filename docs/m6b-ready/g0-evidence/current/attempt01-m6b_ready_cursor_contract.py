"""ADAPTATION strict cursor contract; EXTENSION deterministic CPU evidence.

Source: tasks/06b_ready_g0_evidence.md section 6. This is a required red test
against the unchanged reader, retained for the later Gate 4 green regression.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.iteration_reporter import IterationRecord
from flash.m6_controller import GlobalController
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_store import MemoryStore

OUTPUT = None


class CursorContract(unittest.TestCase):
    def setup_stream(self, count=1, missing=False):
        self.store = MemoryStore()
        self.run = 'm6b-cursor-cpu'
        if not missing:
            self.controller = GlobalController(self.store, self.run, {'node-0': [0]})
            publisher = IterationPublisher(self.store, self.run, 0, clock=lambda: 10.0)
            for iteration in range(1, count + 1):
                record = IterationRecord(self.run, 0, iteration, 100.0,
                    '2026-10-10T00:00:00+00:00', 'CPU_SIMULATED_FRAMEWORK',
                    'cpu_simulated_iteration_end', False)
                self.assertEqual(publisher.publish(record)['status'], 'WRITE_CONFIRMED')
        self.reader = IterationReader(self.store, self.run, 0)

    def observe(self, cursor, suffix='', **kwargs):
        doc = self.store.read(self.run)
        stream = None if doc is None else doc['iterations'].get('0')
        receipt = dict(case=self._testMethodName + suffix,
            input=dict(after_iteration_repr=repr(cursor), cursor_type=type(cursor).__name__,
                       read_kwargs=kwargs),
            server_last=None if stream is None else stream['last'],
            server_retained_from=None if not stream or not stream['records']
                else stream['records'][0]['record']['iteration'],
            server_stream=stream,
            reader_sha256=hashlib.sha256((ROOT/'flash/m6_iteration.py').read_bytes()).hexdigest())
        try:
            result = self.reader.read(after_iteration=cursor, **kwargs)
        except (ValueError, TypeError) as exc:
            receipt['exception'] = dict(type=type(exc).__name__, message=str(exc))
            result = None
        else:
            receipt['returned'] = {k: [asdict(r) for r in v] if k == 'records' else v
                                   for k, v in result.items()}
        # Persist the full input/server state/return BEFORE asserting the contract.
        path = OUTPUT / (receipt['case'] + '.json')
        with path.open('x') as handle:
            json.dump(receipt, handle, indent=2, allow_nan=False)
            handle.write('\n')
        print(json.dumps(dict(case=receipt['case'], input=receipt['input'],
            last=receipt['server_last'], retained_from=receipt['server_retained_from'],
            returned_status=None if result is None else result['status'],
            exception=receipt.get('exception')), allow_nan=False), flush=True)
        return result

    def assert_rejected(self, result):
        if result is not None:
            self.assertIn(result['status'], ('INSUFFICIENT_EVIDENCE', 'BLOCKED'),
                          'cursor must not receive READ_CONFIRMED')

    def test_future_one_step(self):
        self.setup_stream(); self.assert_rejected(self.observe(2))

    def test_future_large(self):
        self.setup_stream(); self.assert_rejected(self.observe(1000000))

    def test_future_after_500_retained(self):
        self.setup_stream(501); self.assert_rejected(self.observe(502))

    def test_legal_boundaries_keep_full_window(self):
        self.setup_stream(501)
        for cursor in (501, 1):
            with self.subTest(cursor=cursor):
                result = self.observe(cursor, '-' + str(cursor))
                self.assertEqual(result['status'], 'READ_CONFIRMED')
                self.assertEqual([r.iteration for r in result['records']], list(range(2, 502)))

    def test_cursor_before_retention_gap(self):
        self.setup_stream(501)
        self.assertEqual(self.observe(0)['status'], 'INSUFFICIENT_EVIDENCE')

    def test_missing_run(self):
        self.setup_stream(missing=True)
        self.assertEqual(self.observe(0)['status'], 'BLOCKED')

    def test_empty_history(self):
        self.setup_stream(0)
        self.assertEqual(self.observe(0)['status'], 'INSUFFICIENT_EVIDENCE')

    def test_expired_record(self):
        self.setup_stream()
        self.assertEqual(self.observe(1, now=70.0, timeout_seconds=60.0)['status'], 'TIMEOUT')

    def test_invalid_types_strict_integer_adaptation(self):
        self.setup_stream()
        for index, cursor in enumerate((True, False, -1, 0.5, 1.0, '1',
                                        float('nan'), float('inf'), float('-inf'))):
            with self.subTest(cursor=repr(cursor)):
                self.assert_rejected(self.observe(cursor, '-' + str(index)))


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output
    OUTPUT.mkdir(parents=True, exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CursorContract)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
