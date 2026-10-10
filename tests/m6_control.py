"""EXTENSION deterministic adversarial control tests; no GPU/Redis claims."""
import copy
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from dataclasses import replace, asdict
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.m6_demo import Simulation
from flash.localization import analyze
from flash.m6_protocol import digest, window_seconds, provisional
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_controller import GlobalController, LocalController, TRIGGER
from flash.m6_store import transaction, Unavailable, MemoryStore


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.s = Simulation()
        self.simulations = getattr(self, 'simulations', []) + [self.s]

    def tearDown(self):
        if os.environ.get('M6_EVIDENCE_DIR'):
            path=Path(os.environ['M6_EVIDENCE_DIR']);path.mkdir(parents=True,exist_ok=True)
            documents=[sim.store.read(sim.run) for sim in self.simulations]
            (path/(self._testMethodName+'.json')).write_text(json.dumps(documents,indent=2)+'\n')

    def doc(self):
        return self.s.store.read(self.s.run)

    def mutate(self, fn):
        return transaction(self.s.store, self.s.run, fn)

    def reset(self, now):
        self.s.poll(now)
        self.s.boundaries(now + .1)
        self.s.poll(now + .1)
        self.s.global_.tick(now + .2)

    def test_two_epochs_m4_equivalence_and_traces(self):
        original = json.loads((ROOT/'tests/m4_cases/three_groups_max_then_min/input.json').read_text())
        expected = analyze(original)
        for now, request_id, epoch in [(0,'first',1),(30,'second',2)]:
            result = self.s.cycle(now, request_id)
            self.assertEqual(result['profile_epoch'], epoch)
            self.assertEqual(result['result']['candidate_ranks'], expected['candidate_ranks'])
            self.assertEqual(result['result']['status'], expected['status'])
            self.assertEqual(result['transitions'], ['MONITOR','PROFILE_REQUESTED','PROFILE_ARMING',
                'PROFILE_COLLECTING','PROFILE_DRAINING','PROFILE_READY','ANALYZED_PROVISIONAL',
                'MONITOR_RESET_REQUESTED','MONITOR'])
            self.assertTrue(result['reset_verified'])
            self.assertFalse(result['result']['final_alert'])
            self.assertEqual(result['result']['final_fault_ranks'], [])
            self.assertTrue(all(s['row']['profile_epoch']==epoch for n in result['profile_nodes'].values() for s in n['samples']))
        self.assertEqual(self.doc()['state'], 'MONITOR')

    def test_window_ms_floor_and_long_iteration(self):
        record = IterationReader(self.s.store,self.s.run,0).read()['records'][-1]
        self.assertEqual(window_seconds(record),20)
        self.assertEqual(window_seconds(replace(record, iteration_time_ms=10000)),22)
        self.s.arm()
        self.s.global_.tick(20.199)
        self.assertEqual(self.doc()['state'],'PROFILE_COLLECTING')
        self.s.global_.tick(20.2)
        self.assertEqual(self.doc()['state'],'PROFILE_DRAINING')
        with self.assertRaises(ValueError): window_seconds(None)
        with self.assertRaises(ValueError): window_seconds(replace(record,timing_boundary='unknown'))
        with self.assertRaises(ValueError): window_seconds(replace(record,timing_boundary='after_optimizer_cuda_complete'))

    def test_manual_request_idempotence_and_conflict(self):
        one = self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='first')
        two = self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='first')
        self.assertEqual(one['profile_epoch'],two['profile_epoch'])
        self.assertEqual(two['status'],'DUPLICATE_CONFIRMED')
        other = copy.deepcopy(self.s.manifest);other['parallel_states'][0]['label']='different'
        with self.assertRaises(ValueError):self.s.global_.start(TRIGGER,other,0,request_id='first')
        with self.assertRaises(ValueError):self.s.global_.start('AUTO',self.s.manifest,0,request_id='auto')

    def test_command_ack_without_application_and_missing_scope(self):
        self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')
        self.s.poll(0);self.s.global_.tick(0)
        self.assertEqual(self.doc()['state'],'PROFILE_ARMING')
        self.assertTrue(all(not n['applied'] for n in self.doc()['active']['nodes'].values()))
        self.s.boundaries(.1,skip=(5,));self.s.poll(.1);self.s.global_.tick(.2)
        self.assertEqual(self.doc()['state'],'PROFILE_ARMING')
        self.assertIsNone(self.s.probes['node-1'].boundary(5,.3,legal=False))
        result=self.s.global_.tick(5)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertIsNone(self.doc()['active']['analysis'])
        self.reset(5)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'TIMEOUT')

    def test_missing_node_timeout(self):
        self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')
        self.s.locals['node-0'].tick(0)
        self.s.global_.tick(0)
        self.assertEqual(self.doc()['state'],'PROFILE_REQUESTED')
        self.assertEqual(self.s.global_.tick(5)['status'],'TIMEOUT')
        self.reset(5)

    def test_duplicate_ack_is_exact_idempotent(self):
        self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')
        self.s.poll(0)
        ack=copy.deepcopy(self.doc()['active']['nodes']['node-0']['ack'])
        self.s.poll(.1);self.s.poll(.2)
        self.assertEqual(self.doc()['active']['nodes']['node-0']['ack'],ack)
        self.assertEqual(len([e for e in self.doc()['events'] if e['kind']=='COMMAND_ACK']),2)

    def test_missing_data_fails_closed(self):
        self.s.arm();self.s.samples(1)
        self.s.probes['node-1'].samples.pop()
        self.s.poll(2)
        self.s.finish(20.2)
        result=self.doc()['epochs'][-1]['result']
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['final_fault_ranks'],[])

    def test_profile_duplicate_origin_rejected(self):
        self.s.arm();self.s.samples(1)
        probe=self.s.probes['node-0'];probe.samples.append(copy.deepcopy(probe.samples[0]))
        self.s.poll(2);self.s.finish(20.2)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')

    def test_profile_corruption_old_run_old_epoch_unsupported(self):
        for kind in ('hash','run','epoch','stream','communicator','unit'):
            with self.subTest(kind=kind):
                self.setUp();self.s.arm();self.s.samples(1)
                sample=self.s.probes['node-0'].samples[0]
                if kind=='hash':sample['sha256']='0'*64
                else:
                    field,value={'run':('run_id','old-run'),'epoch':('profile_epoch',9),
                        'stream':('timing_status','UNSUPPORTED'),'communicator':('identity_source','UNRESOLVED_SPLIT'),
                        'unit':('duration_unit','ms')}[kind]
                    sample['row'][field]=value;sample['sha256']=digest(sample['row'])
                self.s.poll(2);self.s.finish(20.2)
                self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')

    def test_no_previous_epoch_data_reuse(self):
        self.s.cycle(0,'first')
        self.s.arm(30,'second')
        self.s.finish(50.2)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')
        self.assertGreater(sum(n['ignored_old'] for n in self.doc()['epochs'][-1]['profile_nodes'].values()),0)
        self.assertTrue(all(not n['samples'] for n in self.doc()['epochs'][-1]['profile_nodes'].values()))

    def test_sample_window_boundary_not_cpu_wall_duration(self):
        self.s.arm();self.s.samples(20.2)
        self.s.finish(20.2)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')
        self.assertEqual(sum(n['outside_window'] for n in self.doc()['epochs'][-1]['profile_nodes'].values()),6)

    def test_partial_reset_blocks_next_epoch(self):
        self.s.arm();self.s.samples(1);self.s.finish(20.2,reset_skip=(5,))
        self.assertEqual(self.doc()['state'],'MONITOR_RESET_REQUESTED')
        self.assertEqual(self.s.probes['node-1'].states[5]['state'],1)
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,21,request_id='next')['status'],'BLOCKED')
        self.s.global_.tick(25.6)
        self.assertEqual(self.doc()['state'],'BLOCKED')
        self.assertFalse(self.doc()['active']['reset_verified'])
        self.assertEqual(self.doc()['active']['failure']['status'],'TIMEOUT')

    def test_local_restart_invalidates_epoch_and_fences_old_owner(self):
        self.s.arm();old=self.s.locals['node-0']
        new=LocalController(self.s.store,self.s.run,'node-0',old.probe)
        self.s.locals['node-0']=new;old.probe.fence=new.fence
        with self.assertRaisesRegex(ValueError,'STALE'):old.tick(1)
        self.s.global_.tick(1);self.reset(1)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')
        self.s.cycle(30,'second')

    def test_global_restart_aborts_and_fences_old_commands(self):
        self.s.arm();old=self.s.global_
        command=copy.deepcopy(self.s.probes['node-0'].pending)
        self.s.global_=GlobalController(self.s.store,self.s.run,self.s.nodes,resume=True)
        with self.assertRaisesRegex(ValueError,'STALE'):old.tick(1)
        with self.assertRaises(ValueError):self.s.probes['node-0'].request(command)
        self.s.global_.tick(1);self.reset(1)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'ABORTED')

    def test_disconnect_then_reconcile_not_no_candidate(self):
        self.s.arm();self.s.store.online=False
        self.assertEqual(self.s.global_.tick(1)['status'],'BLOCKED')
        self.assertTrue(all(l.tick(1)['status']=='BLOCKED' for l in self.s.locals.values()))
        self.s.store.online=True;self.s.poll(2);self.s.global_.tick(2);self.reset(2)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'ABORTED')

    def test_delayed_transport_bounded_error(self):
        self.s.arm();self.s.store.delay=True
        self.assertEqual(self.s.global_.tick(1)['status'],'BLOCKED')
        self.s.store.delay=False;self.s.global_.tick(2);self.reset(2)

    def test_data_timeout_not_no_candidate(self):
        self.s.arm();self.s.samples(1);self.s.global_.tick(20.2)
        self.assertEqual(self.s.global_.tick(25.2)['status'],'TIMEOUT')
        self.reset(25.2)

    def test_lost_registration_restart_blocked(self):
        self.s.arm();self.s.store.values.clear()
        self.assertEqual(self.s.global_.tick(1)['status'],'BLOCKED')
        with self.assertRaises(Unavailable):GlobalController(self.s.store,self.s.run,self.s.nodes,resume=True)

    def test_ambiguous_and_no_candidate_preserved(self):
        for fixture,status in [('std_convention_disagreement','AMBIGUOUS_SPEC'),('normal_equal','NO_CANDIDATE')]:
            with self.subTest(fixture=fixture):
                s=Simulation(fixture);result=s.cycle(0,'first')
                self.assertEqual(result['result']['status'],status)
                self.assertTrue(result['reset_verified'])

    def test_group_shared_counts_not_records(self):
        s=Simulation('nested_group_shared_members');result=s.cycle(0,'first')
        expected=analyze(json.loads((ROOT/'tests/m4_cases/nested_group_shared_members/input.json').read_text()))
        self.assertEqual(result['completeness'],expected['completeness'])
        self.assertLess(result['completeness']['independent_process_scopes'],result['completeness']['records'])

    def test_iteration_duplicate_conflict_gap_retention_restart(self):
        p=IterationPublisher(self.s.store,self.s.run,0)
        first=IterationReader(self.s.store,self.s.run,0).read()['records'][0]
        self.assertEqual(p.publish(first)['status'],'DUPLICATE_CONFIRMED')
        self.assertEqual(p.publish(replace(first,iteration_time_ms=101))['status'],'CONFLICT')
        self.assertEqual(p.publish(replace(first,iteration=3))['status'],'GAP_OR_OUT_OF_ORDER')
        with self.assertRaises(ValueError):p.publish(replace(first,run_id='old'))
        for i in range(2,503):self.assertEqual(p.publish(replace(first,iteration=i))['status'],'WRITE_CONFIRMED')
        read=IterationReader(self.s.store,self.s.run,0).read()
        self.assertEqual(len(read['records']),500);self.assertEqual(read['retained_from'],3)
        self.assertEqual(p.publish(first)['status'],'STALE_OUTSIDE_RETENTION')
        self.assertEqual(IterationReader(self.s.store,self.s.run,0).read(after_iteration=0)['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(IterationPublisher(self.s.store,self.s.run,0).publish(replace(first,iteration=503))['status'],'WRITE_CONFIRMED')
        self.assertEqual(read['records'][-1].timing_boundary,first.timing_boundary)
        self.assertFalse(read['records'][-1].cuda_completion_wait)

    def test_iteration_unconfirmed_reply_retry_and_corruption(self):
        record=IterationReader(self.s.store,self.s.run,0).read()['records'][0]
        p=IterationPublisher(self.s.store,self.s.run,0)
        self.s.store.lose_reply=True
        self.assertEqual(p.publish(replace(record,iteration=2))['status'],'WRITE_UNCONFIRMED')
        self.assertEqual(p.publish(replace(record,iteration=2))['status'],'DUPLICATE_CONFIRMED')
        self.mutate(lambda d:d['iterations']['0']['records'][0].update(sha256='bad'))
        with self.assertRaises(ValueError):IterationReader(self.s.store,self.s.run,0).read()

    def test_iteration_rank_isolation_and_missing_boundary(self):
        record=IterationReader(self.s.store,self.s.run,0).read()['records'][0]
        p=IterationPublisher(self.s.store,self.s.run,1)
        self.assertEqual(p.publish(replace(record,global_rank=1))['status'],'WRITE_CONFIRMED')
        self.assertEqual(IterationReader(self.s.store,self.s.run,1).read()['records'][0].global_rank,1)
        self.s.publish_iteration(2,boundary='unknown')
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='bad')['status'],'INSUFFICIENT_EVIDENCE')

    def test_cas_concurrent_publication_and_fenced_registration(self):
        record=replace(IterationReader(self.s.store,self.s.run,0).read()['records'][0],iteration=2)
        receipts=[]
        def submit():receipts.append(IterationPublisher(self.s.store,self.s.run,0).publish(record))
        workers=[threading.Thread(target=submit) for _ in range(4)]
        for w in workers:w.start()
        for w in workers:w.join()
        self.assertEqual(sum(r['status']=='WRITE_CONFIRMED' for r in receipts),1)
        self.assertEqual(sum(r['status']=='DUPLICATE_CONFIRMED' for r in receipts),3)
        with self.assertRaises(ValueError):GlobalController(self.s.store,self.s.run,{'node-0':[0],'node-1':[1]},resume=True)

    def test_finished_manual_request_stays_idempotent_and_clock_monotone(self):
        self.s.cycle(0,'first')
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,30,request_id='first')['status'],'DUPLICATE_CONFIRMED')
        self.assertEqual(self.doc()['profile_epoch'],1)
        self.s.arm(30,'second')
        with self.assertRaises(ValueError):self.s.global_.tick(29)

    def test_manifest_coverage_and_hash_integrity(self):
        plan=copy.deepcopy(self.s.manifest);plan['communicators'].pop()
        with self.assertRaises(ValueError):self.s.global_.start(TRIGGER,plan,0,request_id='bad')
        self.assertEqual(self.doc()['profile_epoch'],0)
        self.s.arm();self.s.samples(1)
        self.mutate(lambda d:d['active']['manifest'].update(context={'run_id':'old','profile_epoch':1}))
        self.s.finish(20.2)
        self.assertEqual(self.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')

    def test_restart_during_partial_reset_requires_new_boundaries(self):
        self.s.arm();self.s.samples(1);self.s.finish(20.2,reset_skip=(5,))
        old=self.s.locals['node-0']
        new=LocalController(self.s.store,self.s.run,'node-0',old.probe)
        self.s.locals['node-0']=new;old.probe.fence=new.fence
        self.s.global_=GlobalController(self.s.store,self.s.run,self.s.nodes,resume=True)
        self.s.global_.tick(21)
        self.assertEqual(self.doc()['state'],'MONITOR_RESET_REQUESTED')
        self.assertEqual(len(self.doc()['active']['reset_attempts']),1)
        self.s.poll(21);self.s.global_.tick(21.1)
        self.assertEqual(self.doc()['state'],'MONITOR_RESET_REQUESTED')
        self.reset(21.2)
        self.assertTrue(self.doc()['epochs'][-1]['reset_verified'])

    def test_iteration_timeout_and_cursor_gap_visible(self):
        reader=IterationReader(self.s.store,self.s.run,0)
        self.assertEqual(reader.read(now=60,timeout_seconds=60)['status'],'TIMEOUT')
        self.assertEqual(reader.read(now=0,timeout_seconds=60)['status'],'READ_CONFIRMED')
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,60,request_id='late')['status'],'TIMEOUT')
        self.assertEqual(self.doc()['profile_epoch'],0)

    def test_future_applied_boundary_cannot_arm_earlier_window(self):
        self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')
        self.s.poll(0);self.s.global_.tick(0)
        self.s.boundaries(2);self.s.poll(2);self.s.global_.tick(1)
        self.assertEqual(self.doc()['state'],'PROFILE_ARMING')
        self.s.global_.tick(2)
        self.assertEqual(self.doc()['state'],'PROFILE_COLLECTING')
        with self.assertRaises(ValueError):self.s.probes['node-0'].sample(0,self.s.rows[0],1)

    def test_missing_iteration_not_zero_filled(self):
        self.mutate(lambda d:d['iterations'].clear())
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='missing')['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(self.doc()['profile_epoch'],0)


if __name__=='__main__':unittest.main(verbosity=2)
