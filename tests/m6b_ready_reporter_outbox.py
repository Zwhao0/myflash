"""EXTENSION TASK08 CPU mock reliability; no real Redis/native/GPU bridge."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.iteration_reporter import IterationRecord, IterationReporter, PublicationUnconfirmed
from flash.iteration_outbox import DurableIterationOutbox, DurableIterationConsumer
from flash.m6_controller import GlobalController
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_protocol import digest
from flash.m6_store import MemoryStore, transaction


def record(i=1, **changes):
    values = dict(run_id='task08', global_rank=0, iteration=i, iteration_time_ms=10.0,
                  timestamp='2026-10-11T00:00:00+00:00', source='CPU_MOCK',
                  timing_boundary='cpu_simulated_iteration_end', cuda_completion_wait=False)
    values.update(changes)
    return IterationRecord(**values)


class Reliability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'outbox.sqlite'
        self.cursor_path = Path(self.tmp.name) / 'cursor.sqlite'
        self.store = MemoryStore()
        GlobalController(self.store, 'task08', {'node-0': [0], 'node-1': [1]})
        self.publisher = IterationPublisher(self.store, 'task08', 0, clock=lambda: 10.0)
        self.reader = IterationReader(self.store, 'task08', 0)

    def box(self, path=None):
        value = DurableIterationOutbox(path or self.path, self.store, 'task08', 0, clock=lambda: 10.0)
        self.addCleanup(value.close)
        return value

    def consumer(self):
        value = DurableIterationConsumer(self.cursor_path, self.store, 'task08', 0)
        self.addCleanup(value.close)
        return value

    def reporter(self, publisher, waits=None):
        ticks = iter([1000000, 4000000, 5000000, 9000000])
        return IterationReporter(publisher, 'task08', 0, source='CPU_MOCK',
            timing_boundary='cpu_simulated_iteration_end', clock=lambda: next(ticks),
            completion_wait=None if waits is None else lambda: waits.append(1))

    def publish_many(self, count):
        for i in range(1, count + 1):
            self.assertTrue(self.publisher.publish(record(i))['confirmed'])

    def child(self, code, expected):
        env = os.environ.copy(); env['PYTHONPATH'] = str(ROOT)
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.path), str(self.cursor_path)],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
        print(json.dumps(dict(case=self._testMethodName, argv=result.args, exit_code=result.returncode,
                              stdout=result.stdout, stderr=result.stderr)), flush=True)
        self.assertEqual(result.returncode, expected, result.stderr)

    def test_reporter_write_before_disconnect_keeps_exact_record(self):
        r = self.reporter(self.publisher)
        self.store.online = False; r.begin(1)
        with self.assertRaises(PublicationUnconfirmed) as ctx: r.end()
        frozen = ctx.exception.record
        self.assertIs(r.pending, frozen); self.assertIsNotNone(r.active)
        with self.assertRaises(ValueError): r.begin(2)
        with self.assertRaises(ValueError): r.abort()
        self.store.online = True
        self.assertIs(r.end(), frozen)
        self.assertEqual(self.reader.read()['records'], [frozen]); self.assertIsNone(r.active)

    def test_reporter_lost_ack_never_retimes_or_resynchronizes(self):
        waits = []; r = self.reporter(self.publisher, waits)
        r.begin(1); self.store.lose_reply = True
        with self.assertRaises(PublicationUnconfirmed): r.end()
        frozen = r.pending
        self.assertIs(r.end(), frozen); self.assertEqual(waits, [1, 1])
        self.assertEqual(frozen.iteration_time_ms, 3.0)
        self.assertEqual(self.reader.read()['records'], [frozen])

    def test_reporter_exception_preserves_frozen_record(self):
        seen = []
        class Sink:
            def publish(inner, item):
                seen.append(item)
                if len(seen) == 1: raise ConnectionError('unknown outcome')
        r = self.reporter(Sink()); r.begin(1)
        with self.assertRaises(ConnectionError): r.end()
        r.end(); self.assertIs(seen[0], seen[1])

    def test_reporter_malformed_false_or_wrong_hash_ack_rejected(self):
        for receipt in ({}, True, {'status': 'WRITE_UNCONFIRMED', 'confirmed': False},
                        {'status': 'WRITE_CONFIRMED', 'confirmed': True, 'sha256': 'wrong', 'server_memory_ack': True}):
            class Sink:
                def publish(inner, item): return receipt
            r = self.reporter(Sink()); r.begin(1)
            with self.assertRaises(PublicationUnconfirmed): r.end()
            self.assertIsNotNone(r.pending)

    def test_outbox_write_before_disconnect_restart(self):
        box = self.box(); self.store.online = False
        self.assertEqual(box.publish(record())['status'], 'WRITE_UNCONFIRMED')
        recovered = self.box(); self.assertEqual(recovered.pending, record()); self.assertEqual(recovered.position, 0)
        self.store.online = True; self.assertTrue(recovered.recover()['confirmed'])
        self.assertIsNone(recovered.pending); self.assertEqual(recovered.position, 1)
        self.assertEqual(recovered.next_iteration, 2)

    def test_outbox_lost_ack_recovered_by_read_no_second_cas(self):
        box = self.box(); self.store.lose_reply = True
        self.assertEqual(box.publish(record())['status'], 'WRITE_UNCONFIRMED')
        before = self.store.read('task08')
        restarted = self.box(); receipt = restarted.recover()
        self.assertEqual(receipt['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(self.store.read('task08'), before)
        self.assertEqual(restarted.position, 1)

    def test_disconnect_at_cas_before_write(self):
        box = self.box(); original = self.store.cas
        def disconnect(*args):
            self.store.online = False
            return original(*args)
        self.store.cas = disconnect
        self.assertEqual(box.publish(record())['status'], 'WRITE_UNCONFIRMED')
        self.assertEqual(box.position, 0); self.assertEqual(box.pending, record())
        self.store.online = True; self.store.cas = original
        self.assertNotIn('0', self.store.read('task08')['iterations'])
        self.assertTrue(self.box().recover()['confirmed'])

    def test_repeated_unknown_attempts_one_write_per_call(self):
        box = self.box(); original = self.store.cas; calls = []
        def lost(*args):
            calls.append(args[1]); self.store.lose_reply = True
            return original(*args)
        self.store.cas = lost
        self.assertEqual(box.publish(record())['status'], 'WRITE_UNCONFIRMED')
        for _ in range(3): self.assertTrue(box.recover()['confirmed'] if box.pending else box.publish(record())['confirmed'])
        self.assertEqual(len(calls), 1); self.assertEqual(box.position, 1)

    def test_remote_loss_after_previous_ack_does_not_skip_gap(self):
        box = self.box(); box.publish(record()); box.enqueue(record(2))
        self.store.values['task08']['iterations'].clear()
        self.assertEqual(box.recover()['status'], 'GAP_OR_OUT_OF_ORDER')
        self.assertEqual(box.pending, record(2)); self.assertEqual(box.position, 1)

    def test_outbox_duplicate_and_local_conflict(self):
        box = self.box(); self.assertTrue(box.publish(record())['confirmed'])
        self.assertEqual(box.publish(record())['status'], 'DUPLICATE_CONFIRMED')
        with self.assertRaisesRegex(ValueError, 'conflicting'): box.publish(replace(record(), iteration_time_ms=11))
        self.assertEqual(box.position, 1)

    def test_remote_conflict_retains_pending(self):
        box = self.box(); box.enqueue(record())
        self.publisher.publish(replace(record(), iteration_time_ms=11))
        self.assertEqual(box.recover()['status'], 'CONFLICT')
        self.assertEqual(box.pending, record()); self.assertEqual(box.position, 0)
        self.assertEqual(self.box().recover()['status'], 'CONFLICT')

    def test_pending_blocks_next_gap_or_scope(self):
        box = self.box(); box.enqueue(record())
        for item in (record(2), record(3), record(global_rank=1), record(run_id='other')):
            with self.assertRaises(ValueError): box.enqueue(item)
        self.assertEqual(box.pending, record())

    def test_missing_remote_registration_never_recreated(self):
        box = self.box(); box.enqueue(record()); self.store.values.clear()
        self.assertEqual(box.recover()['status'], 'BLOCKED')
        self.assertEqual(box.position, 0); self.assertEqual(self.store.values, {})

    def test_remote_hash_corruption_never_acknowledged(self):
        box = self.box(); box.enqueue(record()); self.publisher.publish(record())
        transaction(self.store, 'task08', lambda d: d['iterations']['0']['records'][0].update(sha256='bad'))
        with self.assertRaises(ValueError): box.recover()
        self.assertEqual(box.position, 0); self.assertEqual(box.pending, record())

    def test_local_corruption_and_scope_rejected(self):
        box = self.box(); box.enqueue(record())
        box.db.execute("UPDATE records SET sha256='bad'")
        with self.assertRaises(ValueError): self.box()
        for run, rank in (('other', 0), ('task08', 1)):
            with self.assertRaises(ValueError): DurableIterationOutbox(self.path, self.store, run, rank)

    def test_outbox_bad_schema_not_rebuilt(self):
        self.path.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError): self.box()
        self.assertEqual(self.path.read_bytes(), b'not a database')

    def test_enqueue_commits_before_transport(self):
        box = self.box(); original = box.reader.read
        def inspect(**kwargs):
            self.assertEqual(self.box().pending, record())
            return original(**kwargs)
        box.reader.read = inspect
        self.assertTrue(box.publish(record())['confirmed'])

    def test_false_ack_not_removed(self):
        box = self.box()
        box.publisher.publish = lambda r: dict(status='WRITE_CONFIRMED', confirmed=True, sha256='bad', server_memory_ack=True)
        self.assertFalse(box.publish(record())['confirmed'])
        self.assertEqual(box.pending, record()); self.assertEqual(box.position, 0)

    def test_durable_reporter_restart_recovers_unconfirmed(self):
        box = self.box(); r = self.reporter(box); r.begin(1); self.store.online = False
        with self.assertRaises(PublicationUnconfirmed): r.end()
        frozen = r.pending; self.store.online = True; restarted = self.box()
        self.assertTrue(restarted.recover()['confirmed'])
        self.assertEqual(self.reader.read()['records'], [frozen])
        self.assertIs(r.end(), frozen); self.assertEqual(restarted.next_iteration, 2)

    def test_outbox_500_ack_plus_pending_never_evicted(self):
        box = self.box()
        for i in range(1, 501): self.assertTrue(box.publish(record(i))['confirmed'])
        self.store.online = False; box.publish(record(501))
        self.assertEqual(box.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 501)
        self.assertEqual(self.box().pending, record(501))
        self.store.online = True; self.assertTrue(box.recover()['confirmed'])
        self.assertEqual(box.db.execute('SELECT MIN(iteration),MAX(iteration),COUNT(*) FROM records').fetchone(), (2,501,500))
        with self.assertRaises(ValueError): box.publish(record(1))

    def test_unknown_exact_retention_boundary(self):
        box = self.box(); box.enqueue(record()); self.publish_many(500)
        self.assertTrue(box.recover()['confirmed']); self.assertEqual(box.position, 1)

    def test_unknown_evicted_result_not_guessed(self):
        box = self.box(); box.enqueue(record()); self.publish_many(501)
        self.assertEqual(box.recover()['status'], 'STALE_OUTSIDE_RETENTION')
        self.assertEqual(box.pending, record()); self.assertEqual(box.position, 0)

    def test_consumer_poll_does_not_advance_restart_redelivers(self):
        self.publish_many(2); c = self.consumer()
        batch = c.poll()['records']; self.assertEqual(c.position, 0)
        restarted = self.consumer(); self.assertEqual(restarted.poll()['records'], batch)
        self.assertEqual(restarted.commit(batch), 2)
        self.assertEqual(self.consumer().poll()['records'], [])

    def test_consumer_prefix_only_no_skip_change_or_fabrication(self):
        self.publish_many(3); c = self.consumer(); batch = c.poll()['records']
        for bad in ([batch[1]], [replace(batch[0], iteration_time_ms=11)],
                    [replace(batch[0], iteration_time_ms=10)], [record(4)], []):
            with self.assertRaises(ValueError): c.commit(bad)
            self.assertEqual(c.position, 0)
        self.assertEqual(c.commit(batch[:1]), 1)
        with self.assertRaises(ValueError): c.commit(batch[1:])
        self.assertEqual(c.poll()['records'], batch[1:])

    def test_consumer_two_instances_stale_commit(self):
        self.publish_many(2); a = self.consumer(); b = self.consumer()
        batch_a = a.poll()['records']; batch_b = b.poll()['records']
        a.commit(batch_a[:1])
        with self.assertRaisesRegex(ValueError, 'changed'): b.commit(batch_b)
        self.assertEqual(b.position, 1)
        self.assertEqual(b.commit(b.poll()['records']), 2)

    def test_consumer_500_boundary_gap_and_restart(self):
        self.publish_many(500); c = self.consumer(); self.assertEqual(len(c.poll()['records']), 500)
        self.publisher.publish(record(501))
        self.assertEqual(self.consumer().poll()['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(c.commit([record(1)]), 1)
        restarted = self.consumer(); self.assertEqual(len(restarted.poll()['records']), 500)
        self.assertEqual(restarted.commit(restarted.poll()['records']), 501)

    def test_consumer_missing_offline_future_hash_keeps_cursor(self):
        self.publish_many(1); c = self.consumer(); c.commit(c.poll()['records'])
        self.store.online = False
        with self.assertRaises(ConnectionError): c.poll()
        with self.assertRaises(ValueError): c.commit([record()])
        self.assertEqual(c.position, 1); self.store.online = True
        self.store.values['task08']['iterations'].clear()
        self.assertEqual(c.poll()['status'], 'INSUFFICIENT_EVIDENCE'); self.assertEqual(c.position, 1)

    def test_consumer_ledger_kind_scope_and_overflow(self):
        box = self.box()
        with self.assertRaises(ValueError): DurableIterationConsumer(self.path, self.store, 'task08', 0)
        with self.assertRaises(ValueError): box.enqueue(record(2**63))
        self.assertIsNone(box.pending)

    def test_consumer_corruption_future_and_missing_run_fail_closed(self):
        self.publish_many(1); c = self.consumer()
        transaction(self.store, 'task08', lambda d: d['iterations']['0']['records'][0].update(sha256='bad'))
        with self.assertRaises(ValueError): c.poll()
        self.assertEqual(c.position, 0)
        self.store.values['task08']['iterations']['0']['records'][0]['sha256'] = digest(asdict(record()))
        c.commit(c.poll()['records'])
        self.store.values['task08']['iterations']['0']['last'] = 0
        self.store.values['task08']['iterations']['0']['records'] = []
        self.assertEqual(c.poll()['status'], 'INSUFFICIENT_EVIDENCE')
        self.store.values.clear(); self.assertEqual(c.poll()['status'], 'BLOCKED')
        self.assertEqual(c.position, 1)

    def test_new_outbox_uncommitted_enqueue_rolls_back_on_process_exit(self):
        self.child('''
import os,sys
from dataclasses import asdict
from flash.iteration_outbox import DurableIterationOutbox
from flash.iteration_reporter import IterationRecord
from flash.m6_protocol import encode,digest
from flash.m6_store import MemoryStore
b=DurableIterationOutbox(sys.argv[1],MemoryStore(),'task08',0)
r=IterationRecord('task08',0,1,10.0,'2026-10-11T00:00:00+00:00','CPU_MOCK','cpu_simulated_iteration_end',False)
b.db.execute('BEGIN IMMEDIATE')
b.db.execute('INSERT INTO records VALUES (?,?,?)',(1,encode(asdict(r)),digest(asdict(r))))
os._exit(76)
''', 76)
        recovered = self.box(); self.assertIsNone(recovered.pending); self.assertEqual(recovered.position, 0)
        self.assertTrue(recovered.publish(record())['confirmed'])

    def test_process_crash_after_enqueue_and_before_commit(self):
        prelude = '''
import os,sys
from flash.iteration_outbox import DurableIterationOutbox
from flash.iteration_reporter import IterationRecord
from flash.m6_store import MemoryStore
r=IterationRecord('task08',0,1,10.0,'2026-10-11T00:00:00+00:00','CPU_MOCK','cpu_simulated_iteration_end',False)
b=DurableIterationOutbox(sys.argv[1],MemoryStore(),'task08',0)
'''
        self.child(prelude + 'b.enqueue(r)\nos._exit(71)', 71)
        self.assertEqual(self.box().pending, record())
        self.child(prelude + "b.db.execute('BEGIN IMMEDIATE')\nb.db.execute('UPDATE metadata SET position=1')\nos._exit(72)", 72)
        recovered = self.box(); self.assertEqual(recovered.position, 0); self.assertEqual(recovered.pending, record())
        self.assertTrue(recovered.recover()['confirmed'])

    def test_process_crash_remote_committed_local_ack_not_committed(self):
        code = '''
import json,os,sys
from dataclasses import asdict
from flash.iteration_outbox import DurableIterationOutbox
from flash.iteration_reporter import IterationRecord
from flash.m6_controller import GlobalController
from flash.m6_store import MemoryStore
s=MemoryStore();GlobalController(s,'task08',{'node-0':[0],'node-1':[1]})
r=IterationRecord('task08',0,1,10.0,'2026-10-11T00:00:00+00:00','CPU_MOCK','cpu_simulated_iteration_end',False)
b=DurableIterationOutbox(sys.argv[1],s,'task08',0,clock=lambda:10.0)
def crash(record,receipt):
    with open(sys.argv[1]+'.remote.json','w') as f:
        json.dump(s.values,f);f.flush();os.fsync(f.fileno())
    os._exit(73)
b._acknowledge=crash
b.publish(r)
'''
        self.child(code, 73)
        self.store.values = json.loads(Path(str(self.path)+'.remote.json').read_text())
        before = self.store.read('task08'); recovered = self.box()
        self.assertEqual(recovered.pending, record()); self.assertTrue(recovered.recover()['confirmed'])
        self.assertEqual(self.store.read('task08'), before)

    def test_process_crash_consumer_after_poll_and_after_commit(self):
        code = '''
import os,sys
from flash.iteration_outbox import DurableIterationConsumer
from flash.iteration_reporter import IterationRecord
from flash.m6_iteration import IterationPublisher
from flash.m6_controller import GlobalController
from flash.m6_store import MemoryStore
s=MemoryStore();GlobalController(s,'task08',{'node-0':[0],'node-1':[1]})
r=IterationRecord('task08',0,1,10.0,'2026-10-11T00:00:00+00:00','CPU_MOCK','cpu_simulated_iteration_end',False)
IterationPublisher(s,'task08',0).publish(r)
c=DurableIterationConsumer(sys.argv[2],s,'task08',0)
batch=c.poll()['records']
'''
        self.child(code + 'os._exit(74)', 74)
        self.publish_many(1); self.assertEqual(self.consumer().poll()['records'], [record()])
        self.child(code + 'c.commit(batch)\nos._exit(75)', 75)
        self.assertEqual(self.consumer().position, 1); self.assertEqual(self.consumer().poll()['records'], [])


if __name__ == '__main__': unittest.main(verbosity=2)
