"""EXTENSION artificial ABI2 Reader protocol, never native/CUDA evidence."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.reader import API, IDENTITY
from flash.iteration_reporter import IterationReporter, PublicationUnconfirmed
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_store import MemoryStore, transaction
from flash.m6_controller import TRIGGER, GlobalController
from flash.m6_protocol import digest, StaleOwner
from flash.m6_abi2_bridge import (Abi2ProbeAdapter, Abi2LocalController, Abi2GlobalController,
                                  strict_reporter, SOURCE, normalize)


class MockReader:
    """Reader API only. EXTENSION artificial dictionaries with explicit raw digests."""
    def __init__(self, run, node, rank):
        self.s = dict(abi=2, event_bytes=280, capacity=10000, pid=100 + rank,
            created_ns=1000 + rank, run_id=run, node_id=node, global_rank=rank,
            requested_control=0, applied_control=0, state=0, read_pos=0, write_pos=0,
            dropped_full=0, dropped_lock=0, errors=0, bad_records=0, closed=0, poisoned=0)
        self.queue, self.history, self.calls = [], [], []
        self.error = None
        self.drop_request = self.drop_ack = False

    def snapshot(self):
        if self.error == 'snapshot': raise OSError('CPU mock snapshot error')
        return copy.deepcopy(self.s)

    def request(self, state, epoch):
        self.calls.append((state, epoch))
        if self.error == 'request': raise OSError('CPU mock request error')
        if not self.drop_request: self.s['requested_control'] = epoch * 2 + state

    def emit(self, api=1, duration=2.0, **changes):
        self.s['write_pos'] += 1
        row = dict(run_id=self.s['run_id'], node_id=self.s['node_id'], global_rank=self.s['global_rank'],
            pid=self.s['pid'], publish_seq=self.s['write_pos'], call_seq=self.s['write_pos'], timestamp_ns=1,
            thread_id=1, comm_ptr=10000 + self.s['global_rank'], comm_generation=1,
            count=16, group_id=0, stream_ptr=200, api=api, result=0, comm_rank=self.s['global_rank'],
            comm_size=2, datatype=7, op=0, peer=-1, group_depth=0, identity=1, id_hash='a'*64,
            state=self.s['state'], profile_epoch=self.s['applied_control'] >> 1)
        if row['state'] == 1:
            row.update(timing_scope=1 if api <= 8 else 0, timing_status=1 if api <= 8 else 0,
                       device=0, sync_block_ns=1, duration_us=duration if api <= 8 else None,
                       cuda_results=[0]*10 + [-1])
        row.update(changes)
        row.update(api_name=API[row['api']], identity_source=IDENTITY[row['identity']],
                   count_unit='elements' if 1 <= row['api'] <= 8 else 'not_applicable')
        row['record_digest'] = digest(row)
        self.queue.append(row)
        self.history.append(copy.deepcopy(row))
        return row

    def boundary(self):
        self.s['applied_control'] = self.s['requested_control']
        self.s['state'] = self.s['applied_control'] & 1
        gid=self.s['write_pos']+1
        self.emit(api=20, group_id=gid, group_depth=1)
        self.emit(api=21, group_id=gid, group_depth=1)

    def read(self, acknowledge=True):
        if self.error == 'read': raise OSError('CPU mock read error')
        if not self.queue: return None
        row = copy.deepcopy(self.queue[0])
        if acknowledge: self.acknowledge(row['publish_seq'])
        return row

    def acknowledge(self, seq):
        if self.error == 'ack': raise OSError('CPU mock ack error')
        if self.drop_ack: return
        assert seq == self.queue[0]['publish_seq'] == self.s['read_pos'] + 1
        self.queue.pop(0); self.s['read_pos'] = seq


class Harness:
    def __init__(self, *, group=False, scopes=2, durations=(2,18)):
        self.run='task09'; self.nodes={'node-0':[0], 'node-1':[1]}
        self.store=MemoryStore(); self.g=Abi2GlobalController(self.store,self.run,self.nodes)
        self.readers={r:MockReader(self.run,n,r) for n,rs in self.nodes.items() for r in rs}
        self.probes={};self.locals={}; self.group=group;self.scopes=scopes;self.durations=durations
        for node, ranks in self.nodes.items():
            p=Abi2ProbeAdapter(self.run,node,{r:self.readers[r] for r in ranks},lambda cmd:False,scope_threads={r:1 for r in ranks})
            local=Abi2LocalController(self.store,self.run,node,p);p.fence=local.fence
            self.probes[node]=p;self.locals[node]=local
        self.manifest=dict(schema_version=1, context=dict(run_id=self.run,profile_epoch=1), records=[],
            communicators=[dict(id_hash='a'*64,members=[0,1],local_instances=[dict(
                node_id='node-'+str(r),global_rank=r,process_instance=str(100+r),comm_generation=1,
                comm_rank=r,expected_samples=scopes,expected_records=scopes*(2 if group else 1)) for r in (0,1)])],
            parallel_states=[dict(label='DP',members=[0,1],id_hashes=['a'*64],evidence='CPU artificial declaration')])
        self.iteration()

    def doc(self): return self.store.read(self.run)
    def mutate(self,fn): return transaction(self.store,self.run,fn)
    def iteration(self,i=1,now=0):
        ticks=iter([0,100000000])
        r=strict_reporter(IterationPublisher(self.store,self.run,0,clock=lambda:now),self.run,0,
            source='CPU_MOCK_FRAMEWORK',timing_boundary='cpu_simulated_iteration_end',clock=lambda:next(ticks))
        r.begin(i); return r.end()
    def poll(self,now): return [x.tick(now) for x in self.locals.values()]
    def boundaries(self,skip=()):
        for r,x in self.readers.items():
            if r not in skip:x.boundary()
    def arm(self,now=0,request='first'):
        self.g.start(TRIGGER,self.manifest,now,request_id=request);self.poll(now);self.g.tick(now)
        self.boundaries();self.poll(now+.1);self.g.tick(now+.2)
    def samples(self,now=1,skip=(),changes=None):
        for rank,x in self.readers.items():
            if rank in skip: continue
            for _ in range(self.scopes):
                if self.group:
                    gid=x.s['write_pos']+1;x.emit(api=20,group_id=gid,group_depth=1)
                    for _ in range(2):x.emit(duration=self.durations[rank],group_id=gid,group_depth=1,timing_scope=2,**(changes or {}))
                    x.emit(api=21,group_id=gid,group_depth=1)
                else:x.emit(duration=self.durations[rank],**(changes or {}))
        return self.poll(now)
    def reset(self,now,skip=()):
        self.poll(now);self.boundaries(skip);self.poll(now+.1);return self.g.tick(now+.2)
    def finish(self,skip=()):
        end=self.doc()['active']['window']['end_seconds'];self.g.tick(end);self.poll(end)
        self.g.tick(end+.1);self.g.tick(end+.2);self.g.tick(end+.3)
        return self.reset(end+.3,skip)
    def cycle(self,now=0,request='first'):
        self.arm(now,request);self.samples(now+1);self.finish();return self.doc()['epochs'][-1]


class BridgeTests(unittest.TestCase):
    def setUp(self): self.h=Harness()
    def tearDown(self):
        out=os.environ.get('TASK09_EVIDENCE_DIR')
        if out:
            path=Path(out);path.mkdir(exist_ok=True)
            (path/(self._testMethodName+'.json')).write_text(json.dumps(dict(
                doc=self.h.doc(),raw={str(r):x.history for r,x in self.h.readers.items()},
                audits={n:p.audit for n,p in self.h.probes.items()},source='ARTIFICIAL_CPU_READER'),indent=2)+'\n')
    def assert_refused(self):
        doc=self.h.doc();a=doc['active'] or doc['epochs'][-1]
        self.assertFalse((a.get('result') or a.get('analysis') or {}).get('final_alert',False))
        self.assertEqual((a.get('result') or a.get('analysis') or {}).get('final_fault_ranks',[]),[])
        return a
    def test_two_epochs_strict_units_scope_and_reset(self):
        for now,req,epoch in [(0,'first',1),(30,'second',2)]:
            if epoch==2:self.h.iteration(2,now)
            e=self.h.cycle(now,req)
            self.assertEqual(e['profile_epoch'],epoch);self.assertTrue(e['reset_verified'])
            self.assertEqual(e['result']['status'],'PROVISIONAL_CANDIDATE')
            self.assertEqual(e['result']['candidate_ranks'],[0]);self.assertEqual(e['result']['ruleset'],'G04-task07-v1')
            self.assertEqual(e['completeness']['records'],4)
            self.assertEqual(e['transitions'],['MONITOR','PROFILE_REQUESTED','PROFILE_ARMING','PROFILE_COLLECTING',
                'PROFILE_DRAINING','PROFILE_READY','ANALYZED_PROVISIONAL','MONITOR_RESET_REQUESTED','MONITOR'])
            for n in e['profile_nodes'].values():
                for s in n['samples']:
                    self.assertEqual(s['row']['duration_unit'],'us');self.assertEqual(s['row']['count_unit'],'elements')
                    self.assertEqual(s['row']['timing_definition'],'m3_cuda_event_v2');self.assertEqual(s['row']['profile_epoch'],epoch)
            self.assert_refused()
        self.assertEqual(self.h.doc()['state'],'MONITOR')
    def test_shared_group_keeps_records_and_independent_scopes(self):
        self.h=Harness(group=True);e=self.h.cycle()
        self.assertEqual(e['result']['status'],'PROVISIONAL_CANDIDATE')
        self.assertEqual(e['completeness']['records'],8);self.assertEqual(e['completeness']['independent_process_scopes'],4)
        self.assertEqual(e['completeness']['communicator_scope_observations'],4)
    def test_header_and_command_ack_do_not_arm(self):
        h=self.h;h.g.start(TRIGGER,h.manifest,0,request_id='first');h.poll(0);h.g.tick(0)
        for r in h.readers.values():r.s.update(applied_control=3,state=1)
        h.poll(.1);h.g.tick(.2)
        self.assertEqual(h.doc()['state'],'PROFILE_ARMING');self.assertIsNone(h.doc()['active']['window'])
        self.assertEqual(h.g.tick(5)['status'],'TIMEOUT');self.assertIsNone(self.assert_refused()['analysis'])
    def test_missing_rank_scope_timeout_and_reset_blocks_new_epoch(self):
        h=self.h;h.g.start(TRIGGER,h.manifest,0,request_id='first');h.poll(0);h.g.tick(0)
        h.boundaries(skip=(1,));h.poll(.1);h.g.tick(.2);h.g.tick(5)
        h.reset(5,skip=(1,));self.assertEqual(h.g.tick(10)['status'],'BLOCKED')
        self.assertEqual(h.g.start(TRIGGER,h.manifest,11,request_id='second')['status'],'BLOCKED')
        self.assertFalse(h.doc()['active']['reset_verified']);self.assert_refused()
    def test_pre_request_record_cannot_be_relabelled(self):
        h=self.h;x=h.readers[0];x.s.update(applied_control=3,requested_control=3,state=1);x.emit(api=20,group_id=1,group_depth=1)
        h.g.start(TRIGGER,h.manifest,0,request_id='first');h.poll(0);h.g.tick(0)
        h.readers[1].boundary();h.poll(.1);h.g.tick(.2)
        self.assertEqual(h.doc()['state'],'PROFILE_ARMING');self.assertFalse(h.probes['node-0'].audit[0]['selected'])
    def test_stale_raw_epoch_is_audited_not_pooled(self):
        h=self.h;h.arm();h.readers[0].emit(profile_epoch=0,state=0);h.samples()
        e=h.finish();self.assertEqual(e['status'],'PROVISIONAL_CANDIDATE')
        self.assertFalse(h.probes['node-0'].audit[2]['selected'])
    def test_missing_rank_data_rejected(self):
        h=self.h;h.arm();h.samples(skip=(1,));r=h.finish()
        self.assertEqual(r['status'],'INCOMPLETE');self.assert_refused()
    def test_single_scope_is_insufficient_under_approved_g04(self):
        self.h=Harness(scopes=1);e=self.h.cycle()
        self.assertEqual(e['result']['status'],'INCOMPLETE');self.assertEqual(e['result']['candidate_ranks'],[])
    def test_future_epoch_refused_without_ack(self):
        h=self.h;h.arm();x=h.readers[0];x.emit(profile_epoch=2);h.poll(1)
        self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE');self.assertEqual(x.s['read_pos'],2)
    def test_corrupt_digest_gap_and_duplicate_rejected(self):
        for field,value in [('record_digest','bad'),('publish_seq',8),('publish_seq',2)]:
            with self.subTest(field=field,value=value):
                self.h=Harness();h=self.h;h.arm();x=h.readers[0];row=x.emit();row[field]=value
                if field!='record_digest':row['record_digest']=digest({k:v for k,v in row.items() if k!='record_digest'})
                h.poll(1);self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE');self.assertEqual(x.s['read_pos'],2)
    def test_loss_closed_poison_and_replacement_reject(self):
        for field,value in [('dropped_full',1),('dropped_lock',1),('errors',1),('bad_records',1),
                            ('closed',1),('poisoned',1),('pid',999),('created_ns',999)]:
            with self.subTest(field=field):
                self.h=Harness();h=self.h;h.arm();h.readers[0].s[field]=value;h.poll(1)
                self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE');self.assert_refused()
    def test_request_read_ack_and_snapshot_errors_reject(self):
        for kind in ['request','read','ack','snapshot']:
            with self.subTest(kind=kind):
                self.h=Harness();h=self.h
                if kind=='request':h.readers[0].error=kind;h.arm()
                else:h.arm();h.readers[0].error=kind;h.readers[0].emit();h.poll(1)
                self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE');self.assert_refused()
    def test_unconfirmed_request_and_read_ack_refused(self):
        for flag in ['drop_request','drop_ack']:
            with self.subTest(flag=flag):
                self.h=Harness();h=self.h
                if flag=='drop_request':setattr(h.readers[0],flag,True);h.arm()
                else:h.arm();setattr(h.readers[0],flag,True);h.readers[0].emit();h.poll(1)
                self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE')
    def test_invalid_profile_values_rejected(self):
        cases=[dict(timing_status=2),dict(timing_status=3),dict(duration_us=None),dict(duration_us=0),
               dict(duration_us=-1),dict(result=1),dict(cuda_results=[0]*11),dict(identity=2),dict(comm_rank=9),
               dict(comm_generation=2),dict(group_id=99),dict(timing_scope=2),dict(datatype=12)]
        for changes in cases:
            with self.subTest(changes=changes):
                self.h=Harness();h=self.h;h.arm();h.samples(changes=changes);r=h.finish()
                self.assertEqual(r['status'],'INCOMPLETE');self.assert_refused()
    def test_wrong_units_and_group_duration_mismatch(self):
        for kind in ['units','group']:
            self.h=Harness(group=kind=='group');h=self.h;h.arm();h.samples()
            def alter(d):
                s=d['active']['nodes']['node-0']['samples'][0]
                if kind=='units':s['row']['count_unit']='bytes'
                else:s['row']['duration_us']=99
                s['sha256']=digest(s['row'])
            h.mutate(alter)
            # Freeze local observation to exercise global rejection of a hash-consistent changed row.
            end=h.doc()['active']['window']['end_seconds'];h.g.tick(end);h.poll(end);h.mutate(alter)
            h.mutate(lambda d:d['active']['nodes']['node-0']['ready'].update(data_sha256=digest(d['active']['nodes']['node-0']['samples'])))
            self.assertEqual(h.g.tick(end+.1)['status'],'INCOMPLETE');self.assert_refused()
    def test_hash_consistent_group_duration_mismatch(self):
        self.h=Harness(group=True);h=self.h;h.arm()
        for rank,x in h.readers.items():
            for _ in range(2):
                gid=x.s['write_pos']+1;x.emit(api=20,group_id=gid,group_depth=1)
                x.emit(duration=2,group_id=gid,group_depth=1,timing_scope=2)
                x.emit(duration=3,group_id=gid,group_depth=1,timing_scope=2);x.emit(api=21,group_id=gid,group_depth=1)
        h.poll(1);self.assertEqual(h.finish()['status'],'INCOMPLETE')
    def test_sample_and_ready_hash_corruption_refused(self):
        for kind in ['sample','ready']:
            self.h=Harness();h=self.h;h.arm();h.samples();end=h.doc()['active']['window']['end_seconds'];h.g.tick(end);h.poll(end)
            def corrupt(d):
                nd=d['active']['nodes']['node-0']
                if kind=='sample':nd['samples'][0]['sha256']='bad';nd['ready']['data_sha256']=digest(nd['samples'])
                else:nd['ready']['data_sha256']='bad'
            h.mutate(corrupt);self.assertEqual(h.g.tick(end+.1)['status'],'INCOMPLETE')
    def test_command_ack_exact_selection(self):
        for field,value in [('command_id','other'),('command_sha256','bad'),('kind','APPLIED'),
                            ('source','other'),('local_generation',9),('local_generation',True),('accepted_at_seconds',10)]:
            with self.subTest(field=field):
                self.h=Harness();h=self.h;h.g.start(TRIGGER,h.manifest,0,request_id='first');h.poll(0);h.g.tick(0)
                h.boundaries();h.poll(.1);h.mutate(lambda d:d['active']['nodes']['node-0']['ack'].update({field:value}));h.g.tick(.2)
                self.assertEqual(h.doc()['state'],'PROFILE_ARMING');self.assertIsNone(h.doc()['active']['window'])
    def test_forged_or_mixed_source_scope_cannot_arm(self):
        for field,value in [('source','CPU_SIMULATED_PROBE'),('profile_epoch',2),('baseline',999),('boundary','legal_scope_start')]:
            self.h=Harness();h=self.h;h.g.start(TRIGGER,h.manifest,0,request_id='first');h.poll(0);h.g.tick(0);h.boundaries();h.poll(.1)
            h.mutate(lambda d:d['active']['nodes']['node-0']['applied']['0'].update({field:value}));h.g.tick(.2)
            self.assertEqual(h.doc()['state'],'PROFILE_ARMING')
    def test_partial_reset_requires_fresh_monitor_record(self):
        h=self.h;h.arm();h.samples();h.finish(skip=(1,))
        self.assertEqual(h.doc()['state'],'MONITOR_RESET_REQUESTED')
        h.readers[1].s.update(applied_control=2,state=0);h.poll(21);h.g.tick(21.1)
        self.assertEqual(h.doc()['state'],'MONITOR_RESET_REQUESTED');h.readers[1].boundary();h.poll(21.2);h.g.tick(21.3)
        self.assertEqual(h.doc()['state'],'MONITOR');self.assertTrue(h.doc()['epochs'][-1]['reset_verified'])
    def test_controller_restart_fences_old_owner(self):
        h=self.h;h.arm();old=h.g;h.g=Abi2GlobalController(h.store,h.run,h.nodes,resume=True)
        with self.assertRaises(StaleOwner):old.tick(1)
        h.g.tick(1);h.reset(1);self.assertEqual(h.doc()['epochs'][-1]['result']['status'],'ABORTED')
    def test_local_restart_invalidates_epoch_and_old_boundaries(self):
        h=self.h;h.arm();old=h.locals['node-0'];p=h.probes['node-0']
        new=Abi2LocalController(h.store,h.run,'node-0',p);p.fence=new.fence;h.locals['node-0']=new
        with self.assertRaises(StaleOwner):old.tick(1)
        h.g.tick(1);h.poll(1);h.g.tick(1.1)
        self.assertEqual(h.doc()['state'],'MONITOR_RESET_REQUESTED');h.reset(1.2)
        self.assertEqual(h.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')
    def test_disconnect_and_reconnect_invalidates_epoch(self):
        h=self.h;h.arm();h.store.online=False
        self.assertEqual(h.g.tick(1)['status'],'BLOCKED');self.assertEqual(h.locals['node-0'].tick(1)['status'],'BLOCKED')
        h.store.online=True;h.g.tick(2);h.reset(2)
        self.assertEqual(h.doc()['epochs'][-1]['result']['status'],'ABORTED')
    def test_mode_and_manifest_mismatch_rejected(self):
        store=MemoryStore();GlobalController(store,'other',{'node-0':[0],'node-1':[1]})
        with self.assertRaises(ValueError):Abi2GlobalController(store,'other',{'node-0':[0],'node-1':[1]},resume=True)
        h=self.h;h.manifest['communicators'][0]['local_instances'][0]['process_instance']='wrong'
        h.arm();h.samples();self.assertEqual(h.finish()['status'],'INCOMPLETE')
    def test_bounded_drain_and_truth_fields_rejected(self):
        import flash.m6_abi2_bridge as bridge
        from unittest.mock import patch
        h=self.h;h.arm();h.readers[0].emit();h.readers[0].emit()
        with patch.object(bridge,'LIMIT',1):h.poll(1)
        self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE')
        self.h=Harness();h=self.h;h.arm();h.readers[0].emit(target_rank=1);h.poll(1)
        self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE')

    def test_group_scope_lineage_and_unfinished_drain_refused(self):
        for kind in ['missing_start','unfinished','wrong_thread','wrong_group']:
            with self.subTest(kind=kind):
                self.h=Harness(group=True);h=self.h;h.arm()
                for rank,x in h.readers.items():
                    for _ in range(2):
                        gid=x.s['write_pos']+1
                        if kind!='missing_start':x.emit(api=20,group_id=gid,group_depth=1)
                        x.emit(group_id=gid+(1 if kind=='wrong_group' else 0),group_depth=1,
                               timing_scope=2,thread_id=2 if kind=='wrong_thread' else 1)
                        if kind!='unfinished':x.emit(api=21,group_id=gid,group_depth=1)
                h.poll(1)
                if not h.doc()['active']['failure']:
                    end=h.doc()['active']['window']['end_seconds'];h.g.tick(end);h.poll(end)
                self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE')
                self.assert_refused()
    def test_drain_snapshot_corruption_and_late_read_rejected(self):
        h=self.h;h.arm();h.samples();end=h.doc()['active']['window']['end_seconds'];h.g.tick(end);h.poll(end)
        def corrupt(d):
            ready=d['active']['nodes']['node-0']['ready']
            ready['snapshots']['0']['write_pos']+=1;ready['snapshots_sha256']=digest(ready['snapshots'])
        h.mutate(corrupt);self.assertEqual(h.g.tick(end+.1)['status'],'INCOMPLETE')
    def test_late_and_future_samples_cannot_enter_window(self):
        h=self.h;h.arm();end=h.doc()['active']['window']['end_seconds'];h.samples(end)
        self.assertEqual(h.finish()['status'],'INCOMPLETE');self.assert_refused()
    def test_ambiguous_numeric_boundary_is_preserved(self):
        self.h=Harness(durations=(80,120));e=self.h.cycle()
        self.assertEqual(e['result']['status'],'AMBIGUOUS_SPEC');self.assertFalse(e['result']['final_alert'])

    def test_restart_during_partial_reset_requires_new_generation_scope(self):
        h=self.h;h.arm();h.samples();h.finish(skip=(1,))
        p=h.probes['node-0'];old=h.locals['node-0']
        h.locals['node-0']=Abi2LocalController(h.store,h.run,'node-0',p);p.fence=h.locals['node-0'].fence
        h.g.tick(21);h.poll(21);h.g.tick(21.1)
        self.assertEqual(h.doc()['state'],'MONITOR_RESET_REQUESTED')
        h.boundaries();h.poll(21.2);h.g.tick(21.3)
        self.assertEqual(h.doc()['state'],'MONITOR');self.assertTrue(h.doc()['epochs'][-1]['reset_verified'])
        with self.assertRaises(StaleOwner):old.tick(21.4)
    def test_bridge_restart_requires_fresh_reader_record_not_old_header(self):
        h=self.h;h.arm();old=h.locals['node-0']
        p=Abi2ProbeAdapter(h.run,'node-0',{0:h.readers[0]},lambda cmd:False,scope_threads={0:1})
        new=Abi2LocalController(h.store,h.run,'node-0',p);p.fence=new.fence
        h.probes['node-0']=p;h.locals['node-0']=new;h.g.tick(1);h.poll(1);h.g.tick(1.1)
        self.assertEqual(h.doc()['state'],'MONITOR_RESET_REQUESTED')
        h.reset(1.2);self.assertEqual(h.doc()['state'],'MONITOR')
        self.assertEqual(h.doc()['epochs'][-1]['result']['status'],'INCOMPLETE')

    def test_explicit_thread_declaration_and_unexpected_thread_refused(self):
        h=self.h
        with self.assertRaises(ValueError):Abi2ProbeAdapter(h.run,'node-0',{0:h.readers[0]},lambda c:False,scope_threads={})
        h.arm();h.readers[0].emit(thread_id=2);h.poll(1)
        self.assertEqual(h.doc()['active']['failure']['status'],'INCOMPLETE')
        p=Abi2ProbeAdapter(h.run,'node-0',{0:h.readers[0]},lambda c:False,scope_threads={0:2})
        with self.assertRaises(ValueError):Abi2LocalController(h.store,h.run,'node-0',p)


class StrictReporterTests(unittest.TestCase):
    def make(self,sink,strict=True,waits=None):
        clock=iter([0,3000000])
        ctor=strict_reporter if strict else IterationReporter
        return ctor(sink,'strict09',0,source='CPU_MOCK',timing_boundary='cpu_simulated_iteration_end',
                    clock=lambda:next(clock),completion_wait=(lambda:waits.append(1)) if waits is not None else None)
    def test_none_is_rejected_in_explicit_strict_path_legacy_preserved(self):
        class Sink:
            def publish(self,r):return None
        legacy=self.make(Sink(),strict=False);legacy.begin(1);self.assertEqual(legacy.end().iteration,1)
        strict=self.make(Sink());strict.begin(1)
        with self.assertRaises(PublicationUnconfirmed):strict.end()
        self.assertIsNotNone(strict.active);self.assertIsNotNone(strict.pending)
    def test_unknown_or_malformed_ack_retains_frozen_record(self):
        for changes in [dict(status='WRITE_UNCONFIRMED'),dict(sha256='bad'),dict(confirmed=1),
                        dict(server_memory_ack=1),dict(status='CONFLICT')]:
            with self.subTest(changes=changes):
                seen=[];waits=[]
                class Sink:
                    def publish(self,r):
                        seen.append(r);ack=dict(status='WRITE_CONFIRMED',sha256=digest(asdict(r)),confirmed=True,server_memory_ack=True)
                        if len(seen)==1:ack.update(changes)
                        return ack
                r=self.make(Sink(),waits=waits);r.begin(1)
                with self.assertRaises(PublicationUnconfirmed):r.end()
                frozen=r.pending;self.assertIs(r.end(),frozen);self.assertIs(seen[0],seen[1]);self.assertEqual(waits,[1,1])
    def test_strict_memory_store_lost_ack_and_exact_retry(self):
        h=Harness();ticks=iter([0,4000000]);r=strict_reporter(IterationPublisher(h.store,h.run,0,clock=lambda:0),h.run,0,
            source='CPU_MOCK',timing_boundary='cpu_simulated_iteration_end',clock=lambda:next(ticks))
        r.begin(2);h.store.lose_reply=True
        with self.assertRaises(PublicationUnconfirmed):r.end()
        frozen=r.pending;self.assertIs(r.end(),frozen);self.assertEqual(IterationReader(h.store,h.run,0).read()['last'],2)


if __name__=='__main__':unittest.main(verbosity=2)
