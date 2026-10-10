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
        broken.client=redis.Redis(unix_socket_path=str(ROOT/'runs/nonexistent-m6a-owned.socket'),
                                 socket_timeout=.2,socket_connect_timeout=.2)
        with self.assertRaises(Unavailable):broken.read(self.s.run)
        broken.client=original
        self.assertEqual(broken.read(self.s.run)['run_id'],self.s.run)
        self.assertIsNone(broken.read('not-this-run'))
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')['status'],'PROFILE_REQUESTED')
        self.assertEqual(self.s.global_.start(TRIGGER,self.s.manifest,0,request_id='one')['status'],'DUPLICATE_CONFIRMED')


def main():
    global CLIENT
    executable=shutil.which('redis-server')
    module=importlib.util.find_spec('redis')
    if not executable or module is None:
        print(json.dumps(dict(status='BLOCKED',redis_server_found=bool(executable),
                             existing_python_client_found=module is not None,
                             reason='no installation authorized',real_gpu=False)))
        return 3
    import redis
    runs=ROOT/'runs';runs.mkdir(exist_ok=True)
    owned=Path(tempfile.mkdtemp(prefix='m6r-',dir=runs));os.chmod(owned,0o700)
    socket=owned/'r.sock'
    if len(str(socket).encode())>=100:raise ValueError('private socket path too long')
    command=[executable,'--port','0','--unixsocket',str(socket),'--unixsocketperm','600',
             '--save','','--appendonly','no','--dir',str(owned)]
    with (owned/'redis.log').open('wb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        CLIENT=redis.Redis(unix_socket_path=str(socket),socket_timeout=.5,socket_connect_timeout=.5)
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
