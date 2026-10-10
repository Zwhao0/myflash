# CPU mock verifies forwarding, failure rc, recursive calls and multithread Group metadata.
import ctypes,json,os,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def child():
 lib=ctypes.CDLL(str(ROOT/"build/libm2_mock_nccl.so"),mode=os.RTLD_GLOBAL);api=ctypes.CDLL(None)
 ptr=ctypes.c_void_p;ci=ctypes.c_int
 class ID(ctypes.Structure):_fields_=[("bytes",ctypes.c_char*128)]
 signatures={"ncclCommInitRankConfig":[ctypes.POINTER(ptr),ci,ID,ci,ptr],"ncclAllReduce":[ptr,ptr,ctypes.c_size_t,ci,ci,ptr,ptr],"ncclGroupStart":[],"ncclGroupEnd":[],"ncclCommDestroy":[ptr]}
 for name,args in signatures.items():f=getattr(api,name);f.argtypes=args;f.restype=ci
 comm=ptr();assert api.ncclCommInitRankConfig(ctypes.byref(comm),2,ID(b"a"*128),0,None)==0
 errors=[]
 def worker(k):
  try:
   for i in range(100):
    x=(ctypes.c_int64*1)(k+i);y=(ctypes.c_int64*1)(0)
    assert api.ncclGroupStart()==0
    assert api.ncclAllReduce(x,y,1,4,0,comm,None)==0 and y[0]==2*x[0]
    assert api.ncclGroupEnd()==0
  except BaseException as e:errors.append(repr(e))
 ts=[threading.Thread(target=worker,args=(i*100,)) for i in range(4)]
 for t in ts:t.start()
 for t in ts:t.join()
 assert not errors,errors
 assert api.ncclAllReduce(None,None,42,4,0,comm,None)==4
 assert api.ncclGroupEnd()==5
 assert api.ncclCommDestroy(comm)==0
 lib.flash_mock_nonblocking.restype=ci;assert lib.flash_mock_nonblocking()==7
def main():
 if "--child" in sys.argv:child();return
 from flash.reader import Reader
 run="mock_"+str(os.getpid())+"_"+str(time.monotonic_ns())
 env=os.environ.copy();env.update(LD_PRELOAD=str(ROOT/"build/libflash_probe.so"),FLASH_RUN_ID=run,FLASH_NODE_ID="mock",FLASH_RING_CAPACITY="8192",RANK="0")
 r=subprocess.run([sys.executable,__file__,"--child"],env=env,text=True,capture_output=True,timeout=30)
 print(r.stdout+r.stderr);assert r.returncode==0
 names=list(Path("/dev/shm").glob(f"flash_m2_{run}_mock_*"));assert len(names)==1
 reader=Reader("/"+names[0].name,run,"mock");events=[]
 while (e:=reader.read()) is not None:events.append(e)
 snapshot=reader.snapshot();assert snapshot["closed"]==1 and snapshot["write_pos"]==snapshot["attempts"]==len(events)
 assert snapshot["dropped_full"]==snapshot["dropped_lock"]==snapshot["errors"]==0
 data=[e for e in events if e["api"]==1]
 assert len(data)==401 and {e["call_seq"] for e in events}==set(range(1,len(events)+1))
 unsupported=[e for e in events if e["result"]==7];assert len(unsupported)==1 and unsupported[0]["identity"]==4 and unsupported[0]["id_hash"]==""
 assert len({e["thread_id"] for e in data if e["result"]==0})==4
 assert len({e["group_id"] for e in data if e["result"]==0})==400
 assert [e["result"] for e in data if e["count"]==42]==[4]
 assert any(e["api"]==21 and e["result"]==5 for e in events)
 assert all(e["op"]==0 and e["datatype"]==4 for e in data)
 reader.cleanup()
 print(json.dumps(dict(status="PASS",synthetic=True,events=len(events),threads=4,forwarded_error_codes=[4,5,7],recursive_internal_init_suppressed=True)))
if __name__=="__main__":main()
