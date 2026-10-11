"""EXTENSION controlled CPU failure points. No native/Redis/GPU execution."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.m6_demo import Simulation
from flash.automatic_profile import DurableAutomaticProfiler, request_for, validate_request, AUTO_TRIGGER
from flash.iteration_outbox import DurableIterationConsumer
from flash.iteration_reporter import IterationRecord
from flash.m6_controller import GlobalController, TRIGGER
from flash.m6_iteration import IterationPublisher
from flash.m6_protocol import digest, StaleOwner
from flash.rbeast_adapter import PARAMETERS, RbeastAdapter


class CPUAdapter:
    def __init__(self): self.calls = []
    def analyze(self, values):
        self.calls.append(values[:])
        cp = next((i + 1 for i, v in enumerate(values) if v >= 130), None)
        return dict(status='OK', parameters=copy.deepcopy(PARAMETERS),
                    raw=dict(trend=dict(cp=[] if cp is None else [cp],
                        cpPr=[] if cp is None else [.9], cpOccPr=[.1] * len(values))))


class AutoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.s = Simulation(run='task12')
        self.adapter = CPUAdapter()
        self.consumer = self.open_consumer()
        self.profiler = self.open_profiler()
        self.publisher = IterationPublisher(self.s.store, self.s.run, 0, clock=lambda: 0)
        base = self.s.store.read(self.s.run)['iterations']['0']['records'][0]['record']
        self.base = base
        for i in range(2, 33):
            rec = dict(base, iteration=i, iteration_time_ms=100. if i <= 10 else 130.)
            self.assertTrue(self.publisher.publish(IterationRecord(**rec))['confirmed'])

    def open_consumer(self):
        c = DurableIterationConsumer(self.path/'consumer.sqlite', self.s.store, self.s.run, 0)
        self.addCleanup(c.close); return c

    def tearDown(self):
        output = os.environ.get('TASK12_EVIDENCE_DIR')
        if output:
            try:
                rows = self.profiler._rows()
                journal = dict(position=self.profiler.position,
                               row_sha256=[digest(row) for row in rows],
                               latest=rows[-1] if rows else None)
            except ValueError as error:
                journal = dict(validation_error=str(error))
            evidence = dict(case=self._testMethodName, consumer_cursor=self.consumer.position,
                            journal=journal, document=copy.deepcopy(self.s.store.values.get(self.s.run)))
            destination = Path(output); destination.mkdir(parents=True, exist_ok=True)
            (destination/(self._testMethodName+'.json')).write_text(json.dumps(evidence, indent=2)+'\n')

    def open_profiler(self, **kwargs):
        options = dict(adapter=self.adapter, approved_rules=True, cpu_simulation=True)
        options.update(kwargs)
        p = DurableAutomaticProfiler(self.path/'decision.sqlite', self.consumer,
                                    self.s.global_, self.s.manifest, **options)
        self.addCleanup(p.close); return p

    def before_trigger(self):
        for i in range(1, 31):
            result = self.profiler.step(1)
            self.assertEqual(result['status'], 'DECISION_ACKNOWLEDGED', (i, result))
        self.assertEqual(self.consumer.position, 30)

    def request(self): return self.profiler._rows()[-1]['request']

    def restart(self, controller=False):
        if controller:
            self.s.global_ = GlobalController(self.s.store, self.s.run, self.s.nodes, resume=True)
        self.consumer = self.open_consumer()
        self.profiler = self.open_profiler()

    def test_formal_trigger_only_and_distinct_controller_entry(self):
        self.before_trigger()
        result = self.profiler.step(1)
        self.assertEqual(result['status'], 'PROFILE_REQUESTED')
        doc = self.s.store.read(self.s.run)
        self.assertEqual(doc['active']['trigger'], AUTO_TRIGGER)
        self.assertEqual(doc['active']['automatic_request'], self.request())
        self.assertEqual(doc['active']['duration_seconds'], 20)
        self.assertEqual(self.consumer.position, 31)
        self.assertFalse(doc['final_alert']); self.assertEqual(doc['final_fault_ranks'], [])
        with self.assertRaises(ValueError):
            self.s.global_.start(AUTO_TRIGGER, self.s.manifest, 1, request_id='bad')

    def test_exact_duplicate_and_conflict(self):
        self.before_trigger(); first = self.profiler.step(1)
        r = self.request()
        second = self.s.global_.start_automatic_v1(r, 1)
        self.assertEqual(second['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(first['profile_epoch'], second['profile_epoch'])
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 1)
        for key, value in [('request_id', 'wrong'), ('interface_version', 'old'),
                           ('expected_c_sha256', 'wrong')]:
            bad = copy.deepcopy(r); bad[key] = value
            with self.assertRaises(ValueError): self.s.global_.start_automatic_v1(bad, 1)
        # Same source/rules has the same ID even if its payload differs; this is
        # a conflict, never an opportunity to submit another Profile epoch.
        changed = copy.deepcopy(r['manifest']); changed['parallel_states'][0]['label'] = 'different'
        conflicting = request_for(IterationRecord(**r['record']), r['decision'], changed, 'CPU_SIMULATION')
        self.assertEqual(conflicting['request_id'], r['request_id'])
        with self.assertRaises(ValueError): self.s.global_.start_automatic_v1(conflicting, 1)

    def test_finished_request_deduplicates_after_reset_and_next_trigger_is_retained(self):
        self.before_trigger(); self.profiler.step(1); r = self.request()
        self.s.poll(1); self.s.global_.tick(1); self.s.boundaries(1.1)
        self.s.poll(1.1); self.s.global_.tick(1.2); self.s.samples(2)
        end = self.s.store.read(self.s.run)['active']['window']['end_seconds']
        self.s.finish(end)
        self.assertEqual(self.s.global_.start_automatic_v1(r, end+1)['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(self.profiler.step(end+1)['status'], 'PROFILE_REQUESTED')
        self.assertEqual(self.consumer.position, 32)
        self.assertNotEqual(self.request()['request_id'], r['request_id'])
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 2)

    def test_controller_C_identity_and_approved_config_fail_closed(self):
        self.before_trigger(); self.profiler.step(1); r = self.request()
        for changes in (dict(config={}), dict(engine=dict(status='OK', parameters={})),
                        dict(engine=None)):
            d = copy.deepcopy(r['decision']); d.update(changes)
            bad = request_for(IterationRecord(**r['record']), d, self.s.manifest, 'CPU_SIMULATION')
            with self.assertRaises(ValueError): self.s.global_.start_automatic_v1(bad, 1)
        real = request_for(IterationRecord(**r['record']), r['decision'], self.s.manifest, 'C_IDENTITY_GUARDED')
        with self.assertRaises(ValueError): self.s.global_.start_automatic_v1(real, 1)

    def test_invalid_raw_freezes_without_cursor_ack(self):
        self.before_trigger()
        engine = self.adapter.analyze([100]*7+[130]*21)
        engine['raw']['trend']['cpPr'] = [1.1]
        with patch.object(self.adapter, 'analyze', return_value=engine):
            self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 30)
        self.restart(); self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')

    def test_intent_with_acknowledged_cursor_but_evicted_source_is_never_dropped(self):
        self.s.arm(0); self.before_trigger(); self.profiler.step(1)
        r = self.request()
        self.s.store.values[self.s.run]['iterations']['0']['records'] = [
            self.s.store.values[self.s.run]['iterations']['0']['records'][-1]]
        self.restart()
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.request(), r); self.assertEqual(self.consumer.position, 31)

    def test_corrupt_or_missing_intent_refused_at_reopen(self):
        self.before_trigger(); self.profiler.step(1)
        row = self.profiler._rows()[-1]; row['request'] = None
        with self.profiler._transaction(): self.profiler._save(row)
        with self.assertRaisesRegex(ValueError, 'missing durable intent'): self.restart()

    def test_concurrent_completed_duplicate_is_checked_inside_CAS(self):
        self.before_trigger(); self.profiler.step(1); r = self.request()
        # Hide the prior epoch from only the preliminary read, as if another
        # caller publishes/completes between that read and the transaction read.
        original = self.s.store.read; calls = []
        def hide_once(run):
            d = original(run); calls.append(1)
            if len(calls) == 1:
                d['active'] = None; d['epochs'] = []; d['state'] = 'MONITOR'
            return d
        with patch.object(self.s.store, 'read', side_effect=hide_once):
            result = self.s.global_.start_automatic_v1(r, 1)
        self.assertEqual(result['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 1)

    def test_candidates_and_nonboolean_trigger_never_request(self):
        self.before_trigger(); self.profiler.step(1)
        for trigger in (False, 1, 'true', None):
            bad = copy.deepcopy(self.request()); bad['decision']['detection_trigger'] = trigger
            with self.assertRaises(ValueError): validate_request(bad, self.s.run)
        for changes in (dict(status='NO_DETECTION_TRIGGER'), dict(final_alert=True),
                        dict(interface_version='old'), dict(approved_rules={}), dict(candidates=[])):
            r = self.request(); d = copy.deepcopy(r['decision']); d.update(changes)
            bad = request_for(IterationRecord(**r['record']), d, self.s.manifest, 'CPU_SIMULATION')
            with self.assertRaises(ValueError): validate_request(bad, self.s.run)

    def test_disconnect_before_request_keeps_intent_and_backpressure(self):
        self.before_trigger()
        original = self.consumer.commit
        def disconnect(records):
            result = original(records); self.s.store.online = False; return result
        with patch.object(self.consumer, 'commit', side_effect=disconnect):
            self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 31); r = self.request()
        self.restart()
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 31)
        self.s.store.online = True
        self.assertEqual(self.profiler.step(1)['status'], 'PROFILE_REQUESTED')
        self.assertEqual(self.request(), r)

    def test_lost_remote_ack_and_reopen_no_duplicate_epoch_or_refit(self):
        self.before_trigger(); self.s.store.lose_reply = True
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        calls = len(self.adapter.calls); r = self.request()
        self.assertIsNone(self.profiler._rows()[-1]['receipt'])
        self.restart()
        result = self.profiler.step(1)
        self.assertEqual(result['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(len(self.adapter.calls), calls); self.assertEqual(self.request(), r)
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 1)

    def test_crash_after_decision_before_cursor_ack_replays_frozen_decision(self):
        self.before_trigger(); calls = len(self.adapter.calls)
        with patch.object(self.consumer, 'commit', side_effect=RuntimeError('crash after intent commit')):
            with self.assertRaises(RuntimeError): self.profiler.step(1)
        self.assertEqual(self.consumer.position, 30); self.assertEqual(self.profiler.position, 31)
        r = self.request(); self.restart()
        self.assertEqual(self.profiler.step(1)['status'], 'PROFILE_REQUESTED')
        self.assertEqual(self.consumer.position, 31); self.assertEqual(self.request(), r)
        self.assertEqual(len(self.adapter.calls), calls + 1)

    def test_crash_before_local_commit_does_not_ack(self):
        self.before_trigger()
        with patch.object(self.profiler, '_save', side_effect=RuntimeError('local write failure')):
            with self.assertRaises(RuntimeError): self.profiler.step(1)
        self.assertEqual(self.consumer.position, 30); self.assertEqual(self.profiler.position, 30)
        self.restart(); self.assertEqual(self.profiler.step(1)['status'], 'PROFILE_REQUESTED')

    def test_crash_after_remote_accept_before_local_receipt(self):
        self.before_trigger(); original = self.profiler._save
        def fail(row):
            if row['receipt'] is not None: raise RuntimeError('crash before receipt save')
            return original(row)
        with patch.object(self.profiler, '_save', side_effect=fail):
            with self.assertRaises(RuntimeError): self.profiler.step(1)
        self.restart()
        self.assertEqual(self.profiler.step(1)['status'], 'DUPLICATE_CONFIRMED')
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 1)

    def test_busy_active_retains_trigger_and_blocks_next_cursor(self):
        self.s.arm(0)
        self.before_trigger()
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        r = self.request(); self.assertEqual(self.consumer.position, 31)
        for _ in range(3): self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 31); self.assertEqual(self.request(), r)
        self.s.samples(2); end = self.s.store.read(self.s.run)['active']['window']['end_seconds']
        self.s.finish(end)
        self.assertEqual(self.profiler.step(end + 1)['status'], 'PROFILE_REQUESTED')
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 2)

    def test_trigger_during_partial_reset_waits_for_verified_monitor(self):
        self.s.arm(0); self.s.samples(2)
        end = self.s.store.read(self.s.run)['active']['window']['end_seconds']
        self.s.finish(end, reset_skip=(0,))
        self.assertEqual(self.s.store.read(self.s.run)['state'], 'MONITOR_RESET_REQUESTED')
        self.before_trigger()
        self.assertEqual(self.profiler.step(end + 1)['status'], 'BLOCKED')
        self.s.boundaries(end + 1); self.s.poll(end + 1); self.s.global_.tick(end + 1.1)
        self.assertEqual(self.profiler.step(end + 1.2)['status'], 'PROFILE_REQUESTED')

    def test_stale_generation_cannot_dispatch_and_new_owner_replays(self):
        self.before_trigger(); original = self.consumer.commit
        def restart_owner(records):
            answer = original(records)
            self.s.global_ = GlobalController(self.s.store, self.s.run, self.s.nodes, resume=True)
            return answer
        with patch.object(self.consumer, 'commit', side_effect=restart_owner):
            self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.s.store.read(self.s.run)['profile_epoch'], 0)
        self.restart()
        self.assertEqual(self.profiler.step(1)['status'], 'PROFILE_REQUESTED')
        old = self.profiler.controller
        self.restart(controller=True)
        with self.assertRaises(StaleOwner): old.start_automatic_v1(self.request(), 1)
        # Accepted logical ID remains accepted after owner restart, even though
        # existing controller aborts the epoch and requires its normal reset.
        self.assertEqual(self.s.global_.start_automatic_v1(self.request(), 1)['status'], 'DUPLICATE_CONFIRMED')

    def test_missing_remote_document_or_accepted_history_blocks(self):
        self.before_trigger(); self.profiler.step(1)
        original = self.s.store.read(self.s.run)
        self.s.store.values.pop(self.s.run)
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 31)
        damaged = copy.deepcopy(original); damaged['active'] = None; damaged['state'] = 'MONITOR'
        self.s.store.values[self.s.run] = damaged
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 31)

    def test_recovery_rejects_changed_or_evicted_unacked_source(self):
        self.before_trigger()
        with patch.object(self.consumer, 'commit', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError): self.profiler.step(1)
        item = self.s.store.values[self.s.run]['iterations']['0']['records'][30]
        item['record']['iteration_time_ms'] = 131.; item['sha256'] = digest(item['record'])
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 30)
        self.s.store.values[self.s.run]['iterations']['0']['records'] = [
            self.s.store.values[self.s.run]['iterations']['0']['records'][-1]]
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')

    def test_native_failure_freezes_decision_without_ack(self):
        self.before_trigger()
        with patch.object(self.adapter, 'analyze', return_value=dict(status='BLOCKED', reason='C_REJECTED')):
            self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(self.consumer.position, 30); self.assertIsNone(self.request())
        self.restart()
        calls = len(self.adapter.calls)
        self.assertEqual(self.profiler.step(1)['status'], 'BLOCKED')
        self.assertEqual(len(self.adapter.calls), calls)

    def test_explicit_optin_C_and_rank_scope_gates(self):
        for options in (dict(approved_rules=False), dict(cpu_simulation=1),
                        dict(cpu_simulation=False), dict(adapter=RbeastAdapter()),
                        dict(cpu_simulation=False, adapter=RbeastAdapter())):
            with self.assertRaises(ValueError): self.open_profiler(**options)
        c = DurableIterationConsumer(self.path/'rank1.sqlite', self.s.store, self.s.run, 1)
        self.addCleanup(c.close)
        with self.assertRaises(ValueError):
            DurableAutomaticProfiler(self.path/'bad.sqlite', c, self.s.global_, self.s.manifest,
                                     adapter=self.adapter, approved_rules=True, cpu_simulation=True)

    def test_capacity_and_binding_changes_block_without_skipping(self):
        p = DurableAutomaticProfiler(self.path/'limited.sqlite', self.consumer, self.s.global_, self.s.manifest,
                                    adapter=self.adapter, approved_rules=True, cpu_simulation=True, max_decisions=1)
        self.addCleanup(p.close)
        self.assertEqual(p.step(1)['status'], 'DECISION_ACKNOWLEDGED')
        self.assertEqual(p.step(1)['status'], 'BLOCKED'); self.assertEqual(self.consumer.position, 1)
        with self.assertRaises(ValueError): self.open_profiler()

    def test_deterministic_request_and_prefix_inputs_no_future_leak(self):
        self.before_trigger(); self.profiler.step(1)
        r = self.request()
        self.assertEqual(request_for(IterationRecord(**r['record']), r['decision'], self.s.manifest,
                                     'CPU_SIMULATION'), r)
        self.assertEqual(r['decision']['latest_iteration'], 31)
        self.assertEqual(r['decision']['input'][-1]['iteration'], 31)
        self.assertLessEqual(len(r['decision']['input']), 30)
        self.assertNotIn('truth', r); self.assertEqual(len(self.adapter.calls[-1]), 28)

    def test_subprocess_hard_exit_after_intent_commit_reopens(self):
        self.before_trigger()
        # The child rebuilds only CPU MemoryStore input; it uses the actual same
        # local SQLite files, then exits without Python cleanup at the ACK edge.
        code = '''
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()/'tests'))
from task12_auto_profile import CPUAdapter
from scripts.m6_demo import Simulation
from flash.iteration_outbox import DurableIterationConsumer
from flash.automatic_profile import DurableAutomaticProfiler
from flash.iteration_reporter import IterationRecord
from flash.m6_iteration import IterationPublisher
s=Simulation(run='task12')
b=s.store.read(s.run)['iterations']['0']['records'][0]['record']
pub=IterationPublisher(s.store,s.run,0,clock=lambda:0)
for i in range(2,33): pub.publish(IterationRecord(**dict(b,iteration=i,iteration_time_ms=100. if i<=10 else 130.)))
c=DurableIterationConsumer(Path(sys.argv[1])/'consumer.sqlite',s.store,s.run,0)
p=DurableAutomaticProfiler(Path(sys.argv[1])/'decision.sqlite',c,s.global_,s.manifest,adapter=CPUAdapter(),approved_rules=True,cpu_simulation=True)
c.commit=lambda records: os._exit(73)
p.step(1)
'''
        child = subprocess.run([sys.executable, '-B', '-c', code, str(self.path)],
                               cwd=ROOT, capture_output=True, text=True, timeout=15)
        print(json.dumps(dict(case=self._testMethodName, exit_code=child.returncode,
                              stdout=child.stdout, stderr=child.stderr)), flush=True)
        self.assertEqual(child.returncode, 73, child.stderr)
        self.restart()
        self.assertEqual(self.consumer.position, 30)
        self.assertEqual(self.profiler.step(1)['status'], 'PROFILE_REQUESTED')
        self.assertEqual(self.consumer.position, 31)


if __name__ == '__main__': unittest.main(verbosity=2)
