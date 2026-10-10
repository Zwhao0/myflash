"""UPSTREAM actual Redis transport gates; absence is BLOCKED exit3, never skip/PASS.
EXTENSION scopes/clock/fixture remain CPU mock even when transport is real.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.m6_demo import Simulation
from flash.m6_store import RedisStore, Unavailable
from flash.m6_controller import GlobalController, LocalController, TRIGGER
from flash.m6_iteration import IterationPublisher, IterationReader

CLIENT=None


def private_client(socket, timeout):
    """UPSTREAM redis-py8 Redis(unix_socket_path=...) drops connect timeout.

    Explicit pool config reaches UnixDomainSocketConnection._connect. Both
    deadlines stay finite; no hidden transport retry can confirm a lost reply.
    """
    import redis
    from redis.backoff import NoBackoff
    from redis.retry import Retry
    return redis.Redis(connection_pool=redis.ConnectionPool(
        connection_class=redis.UnixDomainSocketConnection,path=str(socket),
        socket_timeout=timeout,socket_connect_timeout=timeout,
        retry=Retry(NoBackoff(),0)))


class RedisTests(unittest.TestCase):
    def setUp(self):
        self.s=Simulation(store=RedisStore(CLIENT),run='m6r-'+uuid.uuid4().hex)

    def tearDown(self):
        # Only the known namespace allocated by this test is deleted.
        doc=self.s.store.read(self.s.run)
        if os.environ.get('M6_EVIDENCE_DIR'):
            p=Path(os.environ['M6_EVIDENCE_DIR']);p.mkdir(parents=True,exist_ok=True)
            (p/(self._testMethodName+'.json')).write_text(json.dumps(doc,indent=2)+'\n')
        self.assertEqual(CLIENT.delete(self.s.store.key(self.s.run)),1)
        self.assertIsNone(CLIENT.get(self.s.store.key(self.s.run)))

    def test_two_epochs_actual_lua_and_private_socket(self):
        first,second=self.s.cycle(0,'one'),self.s.cycle(30,'two')
        self.assertEqual([first['profile_epoch'],second['profile_epoch']],[1,2])
        self.assertEqual(first['result']['candidate_ranks'],second['result']['candidate_ranks'])
        self.assertTrue(first['reset_verified'] and second['reset_verified'])
        self.assertFalse(second['result']['final_alert'])
        self.assertTrue(self.s.store.client.info('server')['redis_version'])

    def test_concurrent_idempotence_conflict_and_500(self):
        record=IterationReader(self.s.store,self.s.run,0).read()['records'][0]
        receipts=[]
        def worker():receipts.append(IterationPublisher(self.s.store,self.s.run,0).publish(replace(record,iteration=2)))
        workers=[threading.Thread(target=worker) for _ in range(4)]
        for w in workers:w.start()
        for w in workers:w.join()
        self.assertEqual(sum(r['status']=='WRITE_CONFIRMED' for r in receipts),1)
        self.assertEqual(sum(r['status']=='DUPLICATE_CONFIRMED' for r in receipts),3)
        p=IterationPublisher(self.s.store,self.s.run,0)
        self.assertEqual(p.publish(replace(record,iteration=2,iteration_time_ms=101))['status'],'CONFLICT')
        for i in range(3,503):self.assertEqual(p.publish(replace(record,iteration=i))['status'],'WRITE_CONFIRMED')
        self.assertEqual(len(IterationReader(self.s.store,self.s.run,0).read()['records']),500)

    def test_acceptance_timeout_partial_monitor(self):
        self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')
        self.s.poll(0);self.s.global_.tick(0)
        self.assertEqual(self.s.store.read(self.s.run)['state'],'PROFILE_ARMING')
        self.assertEqual(self.s.global_.tick(5)['status'],'TIMEOUT')
        self.s.poll(5);self.s.boundaries(5.1,skip=(5,));self.s.poll(5.1)
        self.s.global_.tick(10)
        self.assertEqual(self.s.store.read(self.s.run)['state'],'BLOCKED')

    def test_restart_fencing_and_previous_epoch_not_pooled(self):
        self.s.arm()
        old=self.s.global_
        self.s.global_=GlobalController(self.s.store,self.s.run,self.s.nodes,resume=True)
        with self.assertRaises(ValueError):old.tick(1)
        self.s.global_.tick(1);self.s.poll(1);self.s.boundaries(1.1);self.s.poll(1.1);self.s.global_.tick(1.2)
        self.assertEqual(self.s.store.read(self.s.run)['epochs'][-1]['result']['status'],'ABORTED')
        self.s.arm(30,'two');self.s.finish(50.2)
        self.assertEqual(self.s.store.read(self.s.run)['epochs'][-1]['result']['status'],'INCOMPLETE')

    def test_client_reconnect_and_namespace_isolation(self):
        import redis
        broken=RedisStore(CLIENT)
        original=broken.client
        broken.client=private_client(ROOT/'runs/nonexistent-m6a-owned.socket',.2)
        with self.assertRaises(Unavailable):broken.read(self.s.run)
        broken.client=original
        self.assertEqual(broken.read(self.s.run)['run_id'],self.s.run)
        self.assertIsNone(broken.read('not-this-run'))
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')['status'],'PROFILE_REQUESTED')
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')['status'],'DUPLICATE_CONFIRMED')

    def test_actual_server_stop_restart_and_lost_document(self):
        """UPSTREAM server run_id changes; ADAPTATION refuses active-run recovery."""
        import redis
        owned=Path(tempfile.mkdtemp(prefix='m6s-',dir=ROOT/'runs'))
        os.chmod(owned,0o700);socket=owned/'r.sock'
        self.assertLess(len(str(socket).encode()),100)
        command=[shutil.which('redis-server'),'--port','0','--unixsocket',str(socket),
                 '--unixsocketperm','600','--disable-thp','no','--save','','--appendonly','no','--dir',str(owned)]
        client=private_client(socket,.2)
        children=[];logs=[];exits=[];proof={}
        def start():
            log=(owned/('server-'+str(len(children))+'.log')).open('wb');logs.append(log)
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);children.append(child)
            until=time.monotonic()+5
            while True:
                try:client.ping();break
                except redis.exceptions.ConnectionError:
                    if time.monotonic()>=until or child.poll() is not None:raise
                    time.sleep(.05)
            self.assertEqual(socket.stat().st_mode&0o777,0o600)
        def stop():
            child=children[-1]
            if child.poll() is None:child.terminate()
            try:code=child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();code=child.wait(timeout=5)
            exits.append(code)
            self.assertEqual(code,0)
        try:
            start();store=RedisStore(client)
            simulated=Simulation(store=store,run='m6s-'+uuid.uuid4().hex)
            simulated.arm();proof['before_stop']=store.read(simulated.run)
            old_id=store.server_id;stop()
            self.assertEqual(simulated.global_.tick(1)['status'],'BLOCKED')
            self.assertFalse(simulated.global_.receipts[-1]['final_alert'])
            proof['disconnect_receipt']=simulated.global_.receipts[-1]
            start();new_id=client.info('server')['run_id']
            self.assertNotEqual(old_id,new_id)
            with self.assertRaises(Unavailable):store.read(simulated.run)
            with self.assertRaises(Unavailable):store.cas(simulated.run,0,proof['before_stop'])
            self.assertEqual(simulated.global_.tick(2)['status'],'BLOCKED')
            fresh=RedisStore(client);self.assertIsNone(fresh.read(simulated.run))
            with self.assertRaises(Unavailable):GlobalController(fresh,simulated.run,simulated.nodes,resume=True)
            replacement=Simulation(store=fresh,run='m6s-'+uuid.uuid4().hex)
            result=replacement.cycle(0,'fresh-run')
            self.assertTrue(result['reset_verified']);self.assertFalse(result['result']['final_alert'])
            proof.update(old_server_id=old_id,new_server_id=new_id,old_run_lost=True,
                         replacement_run=fresh.read(replacement.run))
            self.assertEqual(client.delete(fresh.key(replacement.run)),1)
            self.assertEqual(client.dbsize(),0)
        finally:
            client.close()
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    try:exits.append(child.wait(timeout=5))
                    except subprocess.TimeoutExpired:child.kill();exits.append(child.wait(timeout=5))
            for log in logs:log.close()
            if socket.exists():socket.unlink()
            proof.update(command=command,child_exits=exits,
                         child_finished=all(c.poll() is not None for c in children),
                         socket_remaining=socket.exists(),other_services_touched=False)
            (owned/'restart.json').write_text(json.dumps(proof,indent=2)+'\n')
            if os.environ.get('M6_EVIDENCE_DIR'):
                (Path(os.environ['M6_EVIDENCE_DIR'])/'actual-server-restart.json').write_text(json.dumps(proof,indent=2)+'\n')
        self.assertEqual(exits,[0,0])


def main():
    global CLIENT
    executable=shutil.which('redis-server')
    module=importlib.util.find_spec('redis')
    if not executable or module is None:
        print(json.dumps(dict(status='BLOCKED',redis_server_found=bool(executable),
                             existing_python_client_found=module is not None,
                             reason='Redis binary/client missing; install separately only with authorization',real_gpu=False)))
        return 3
    import redis
    runs=ROOT/'runs';runs.mkdir(exist_ok=True)
    owned=Path(tempfile.mkdtemp(prefix='m6r-',dir=runs));os.chmod(owned,0o700)
    socket=owned/'r.sock'
    if len(str(socket).encode())>=100:raise ValueError('private socket path too long')
    command=[executable,'--port','0','--unixsocket',str(socket),'--unixsocketperm','600',
             '--disable-thp','no','--save','','--appendonly','no','--dir',str(owned)]
    with (owned/'redis.log').open('wb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        CLIENT=private_client(socket,.5)
        results=None
        try:
            until=time.monotonic()+5
            while True:
                try:
                    CLIENT.ping();break
                except redis.exceptions.ConnectionError:
                    if time.monotonic()>=until or child.poll() is not None:raise
                    time.sleep(.05)
            if (socket.stat().st_mode&0o777)!=0o600:raise ValueError('socket permissions')
            info=CLIENT.info('server')
            results=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RedisTests))
            (owned/'transport.json').write_text(json.dumps(dict(redis_version=info['redis_version'],
                client_version=redis.__version__,command=command,real_transport=True,
                simulated_probe=True,virtual_clock=True,tests=results.testsRun,success=results.wasSuccessful()),indent=2)+'\n')
        finally:
            CLIENT.close()
            child.terminate() if child.poll() is None else None
            try:exit_code=child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill();exit_code=child.wait(timeout=5)
            if socket.exists():socket.unlink()  # exact owned object after child completion
            (owned/'cleanup.json').write_text(json.dumps(dict(child_exit=exit_code,
                child_finished=child.poll() is not None,socket_remaining=socket.exists(),
                raw_logs_retained=True,other_services_touched=False))+'\n')
    print(json.dumps(dict(status='PASS' if results and results.wasSuccessful() and exit_code==0 else 'FAIL',
                         private_receipts=str(owned),child_exit=exit_code)))
    return 0 if results and results.wasSuccessful() and exit_code==0 else 1


if __name__=='__main__':raise SystemExit(main())
