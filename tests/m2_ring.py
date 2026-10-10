# CPU-only synthetic ABI/concurrency tests; these are not GPU experiments.
import ctypes,errno,json,os,threading,time,unittest,sys,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.reader import Reader
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/"build/libflash_ring_test.so"
class RingTests(unittest.TestCase):
    def setUp(self):
        self.lib=ctypes.CDLL(str(LIB),use_errno=True)
        self.lib.flash_ring_create.argtypes=[ctypes.c_char_p]*3+[ctypes.c_int,ctypes.c_uint32];self.lib.flash_ring_create.restype=ctypes.c_void_p
        self.lib.flash_test_write.argtypes=[ctypes.c_void_p,ctypes.c_uint64,ctypes.c_int];self.lib.flash_test_write.restype=ctypes.c_int
        self.lib.flash_test_corrupt.argtypes=[ctypes.c_void_p,ctypes.c_int];self.lib.flash_test_corrupt.restype=ctypes.c_int
        self.lib.flash_test_lock.argtypes=[ctypes.c_void_p];self.lib.flash_test_lock.restype=ctypes.c_int
        self.lib.flash_test_unlock.argtypes=[ctypes.c_void_p];self.lib.flash_test_unlock.restype=ctypes.c_int
        self.lib.flash_test_owner_die.argtypes=[ctypes.c_void_p];self.lib.flash_test_owner_die.restype=None
        self.lib.flash_ring_close.argtypes=[ctypes.c_void_p];self.lib.flash_ring_close.restype=None
        self.created=[];self.readers=[]
        self.run="unit_"+str(os.getpid())+"_"+str(time.monotonic_ns())
    def create(self,cap=4,suffix="a",run=None):
        actual=run or self.run;name=f"/flash_m2_{actual}_unit_{suffix}"
        h=self.lib.flash_ring_create(name.encode(),actual.encode(),b"unit",3,cap)
        self.assertTrue(h);self.created.append([name,h,actual]);return name,h
    def reader(self,name,run=None):
        r=Reader(name,run or self.run,"unit",LIB);self.readers.append(r);return r
    def tearDown(self):
        for r in self.readers:r.close()
        for name,h,run in self.created:
            if h:self.lib.flash_ring_close(h)
            # Test fixture cleanup only its exact O_EXCL-created object, even if intentionally poisoned.
            libc=ctypes.CDLL(None,use_errno=True);libc.shm_unlink.argtypes=[ctypes.c_char_p]
            rc=libc.shm_unlink(name.encode());self.assertTrue(rc==0 or ctypes.get_errno()==errno.ENOENT)
    def test_boundaries_and_wrap(self):
        name,h=self.create(2);r=self.reader(name)
        for cycle in range(40):
            values=[0,2**64-1] if cycle==0 else [2*cycle,2*cycle+1]
            for value in values:self.assertEqual(self.lib.flash_test_write(h,value,2),0)
            for value in values:self.assertEqual(r.read()["count"],value)
            self.assertIsNone(r.read())
        self.assertEqual(r.snapshot()["write_pos"],80);self.assertEqual(r.snapshot()["read_pos"],80)
    def test_full_and_loss(self):
        name,h=self.create(1);r=self.reader(name)
        self.assertEqual(self.lib.flash_test_write(h,1,2),0)
        for _ in range(9):self.assertEqual(self.lib.flash_test_write(h,2,2),-errno.ENOSPC)
        s=r.snapshot();self.assertEqual((s["attempts"],s["dropped_full"],s["write_pos"]),(10,9,1))
        self.assertEqual(r.read()["count"],1);self.assertIsNone(r.read())
    def test_bounded_lock_loss(self):
        name,h=self.create();r=self.reader(name);locked=threading.Event();release=threading.Event()
        def holder():
            self.assertEqual(self.lib.flash_test_lock(h),0);locked.set();release.wait(2)
            self.assertEqual(self.lib.flash_test_unlock(h),0)
        t=threading.Thread(target=holder);t.start();self.assertTrue(locked.wait(1))
        self.assertEqual(self.lib.flash_test_write(h,3,2),-errno.ETIMEDOUT)
        release.set();t.join()
        snapshot=r.snapshot();self.assertEqual(snapshot["attempts"],1);self.assertEqual(snapshot["dropped_lock"],1);self.assertEqual(snapshot["write_pos"],0)
    def test_concurrent_threads_and_reader(self):
        name,h=self.create(64);r=self.reader(name);received=[];results=[];failures=[]
        def writer(index):
            try:
                for i in range(1200):results.append(self.lib.flash_test_write(h,index*1200+i,2))
            except BaseException as e:failures.append(str(e))
        workers=[threading.Thread(target=writer,args=(i,)) for i in range(4)]
        for t in workers:t.start()
        while any(t.is_alive() for t in workers):
            value=r.read()
            if value is not None:received.append(value["count"])
        for t in workers:t.join()
        while (value:=r.read()) is not None:received.append(value["count"])
        self.assertFalse(failures);self.assertEqual(len(results),4800)
        self.assertEqual(len(received),len(set(received)))
        s=r.snapshot();self.assertEqual(s["attempts"],4800)
        self.assertEqual(len(received),results.count(0));self.assertEqual(s["bad_records"],0)
        self.assertEqual(s["attempts"],len(received)+s["dropped_full"]+s["dropped_lock"]);self.assertEqual(s["errors"],0)
    def test_reader_restart_and_exclusive_reader(self):
        name,h=self.create(4);r=self.reader(name)
        for value in range(3):self.lib.flash_test_write(h,value,2)
        self.assertEqual(r.read()["count"],0)
        with self.assertRaises(OSError):self.reader(name)
        r.close();r2=self.reader(name)
        self.assertEqual([r2.read()["count"],r2.read()["count"]],[1,2]);self.assertIsNone(r2.read())
    def test_unacknowledged_reader_restart(self):
        name,h=self.create();r=self.reader(name);self.lib.flash_test_write(h,77,2)
        event=r.read(acknowledge=False);self.assertEqual(event["count"],77);self.assertEqual(r.snapshot()["read_pos"],0)
        r.close();r2=self.reader(name)
        self.assertEqual(r2.read()["publish_seq"],event["publish_seq"]);self.assertIsNone(r2.read())
    def test_cli_restart_durable_before_ack(self):
        name,h=self.create();r=self.reader(name)
        for value in [7,8,9]:self.lib.flash_test_write(h,value,2)
        event=r.read(acknowledge=False);context=r.snapshot()
        with tempfile.TemporaryDirectory(prefix="flash-m2-reader-") as tmp:
            out=Path(tmp);event_path=out/f"events-{context['pid']}-{context['created_ns']}.ndjson"
            with event_path.open("w") as stream:
                stream.write(json.dumps(event)+"\n");stream.flush();os.fsync(stream.fileno())
            r.close();self.lib.flash_ring_close(h);self.created[0][1]=None
            stop=out/"stop";stop.write_text("fixture closed")
            cmd=[sys.executable,"-m","flash.reader","--run-id",self.run,"--node-id","unit","--output",str(out),"--stop-file",str(stop),"--timeout","5"]
            child=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=10)
            self.assertEqual(child.returncode,0,child.stdout+child.stderr)
            rows=[json.loads(x) for x in event_path.read_text().splitlines()]
            self.assertEqual([x["publish_seq"] for x in rows],[1,2,3])
            self.assertEqual([x["count"] for x in rows],[7,8,9])
            self.assertEqual(json.loads((out/"reader-result.json").read_text())["status"],"PASS")
    def test_run_isolation_and_stale(self):
        n1,h1=self.create();n2,h2=self.create(run=self.run+"_other")
        self.lib.flash_test_write(h1,7,2);self.lib.flash_test_write(h2,9,2)
        with self.assertRaises(OSError):self.reader(n1,run=self.run+"_other")
        self.assertEqual(self.reader(n1).read()["count"],7)
        self.assertEqual(self.reader(n2,run=self.run+"_other").read()["count"],9)
    def test_bad_record_and_abi(self):
        name,h=self.create();r=self.reader(name);self.lib.flash_test_write(h,5,2)
        self.assertEqual(self.lib.flash_test_corrupt(h,0),0)
        with self.assertRaises(OSError) as e:r.read()
        self.assertEqual(e.exception.errno,errno.EBADMSG);self.assertEqual(r.snapshot()["bad_records"],1)
        r.close();self.lib.flash_test_corrupt(h,1)
        with self.assertRaises(OSError) as e:self.reader(name)
        self.assertEqual(e.exception.errno,errno.EPROTO)
    def test_normal_writer_close_and_cleanup(self):
        name,h=self.create();r=self.reader(name);self.lib.flash_test_write(h,8,2)
        r.close()
        with self.assertRaises(OSError):r.cleanup() # active writer and unread data cannot be removed
        self.lib.flash_ring_close(h);self.created[0][1]=None
        r2=self.reader(name);self.assertEqual(r2.snapshot()["closed"],1);self.assertEqual(r2.read()["count"],8)
        r2.cleanup();self.assertFalse((Path("/dev/shm")/name[1:]).exists())
    def test_owner_death_is_poisoned(self):
        name,h=self.create();child=os.fork()
        if child==0:self.lib.flash_test_owner_die(h)
        self.assertEqual(os.waitpid(child,0)[1],0)
        with self.assertRaises(OSError) as e:self.reader(name)
        self.assertEqual(e.exception.errno,errno.EIO)
if __name__=="__main__":unittest.main(verbosity=2)
