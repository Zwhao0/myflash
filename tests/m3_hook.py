# ADAPTATION: CPU-only event ordering/errors/state-machine fixture.
import ctypes,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def child():
 mock=ctypes.CDLL(str(ROOT/'build/libm3_mock_nccl.so'),mode=os.RTLD_GLOBAL)
 cuda=ctypes.CDLL(str(ROOT/'build/libm3_mock_cuda.so'),mode=os.RTLD_GLOBAL);api=ctypes.CDLL(None)
 ptr=ctypes.c_void_p;ci=ctypes.c_int
 class ID(ctypes.Structure):_fields_=[('bytes',ctypes.c_char*128)]
 sig={'ncclCommInitRankConfig':[ctypes.POINTER(ptr),ci,ID,ci,ptr],'ncclAllReduce':[ptr,ptr,ctypes.c_size_t,ci,ci,ptr,ptr],'ncclGroupStart':[],'ncclGroupEnd':[],'ncclCommDestroy':[ptr], 'flash_profile_request':[ctypes.c_uint32,ctypes.c_uint64]}
 for name,args in sig.items():f=getattr(api,name);f.argtypes=args;f.restype=ci
 for name in ['flash_profile_cuda_calls','flash_profile_cuda_syncs']:getattr(api,name).restype=ctypes.c_uint64
 comm=ptr();assert api.ncclCommInitRankConfig(ctypes.byref(comm),2,ID(b'a'*128),0,None)==0
 def ar(n=1,s=None):
  x=(ctypes.c_int64*1)(3);y=(ctypes.c_int64*1)();rc=api.ncclAllReduce(x,y,n,4,0,comm,s)
  if rc==0:assert y[0]==6
  return rc
 assert ar()==0 and api.flash_profile_cuda_calls()==0
 for epoch in [1,2]:
  assert api.flash_profile_request(1,epoch)==0;assert ar()==0
  assert api.ncclGroupStart()==0;assert api.ncclGroupStart()==0;before=cuda.flash_mock_cuda_waits()
  assert ar()==0;assert api.flash_profile_request(0,epoch)==0;assert ar()==0
  assert api.ncclGroupEnd()==0 and cuda.flash_mock_cuda_waits()==before
  assert api.ncclGroupEnd()==0 and cuda.flash_mock_cuda_waits()==before+1
  saved=api.flash_profile_cuda_calls();assert ar()==0 and saved==api.flash_profile_cuda_calls()
 assert api.flash_profile_request(1,3)==0
 for mode in range(1,8):cuda.flash_mock_cuda_mode(mode);assert ar()==0
 cuda.flash_mock_cuda_mode(0)
 assert api.ncclGroupStart()==0;assert ar()==0;assert ar(s=ptr(123))==0;before=cuda.flash_mock_cuda_waits();assert api.ncclGroupEnd()==0;assert cuda.flash_mock_cuda_waits()==before
 for rc in [7,5]:
  mock.flash_mock_group_result(rc);assert api.ncclGroupStart()==0;assert ar()==0;assert ar()==0
  before=cuda.flash_mock_cuda_waits();assert api.ncclGroupEnd()==rc;assert cuda.flash_mock_cuda_waits()==before
 mock.flash_mock_group_result(0)
 assert api.ncclGroupStart()==0;assert api.ncclGroupStart()==0;assert ar()==0;assert ar()==0
 mock.flash_mock_group_result(5);before=cuda.flash_mock_cuda_waits();assert api.ncclGroupEnd()==5
 mock.flash_mock_group_result(0);assert api.ncclGroupEnd()==0;assert cuda.flash_mock_cuda_waits()==before
 assert ar(42)==4
 assert api.flash_profile_request(0,3)==0;saved=api.flash_profile_cuda_calls();assert ar()==0 and saved==api.flash_profile_cuda_calls()
 assert cuda.flash_mock_cuda_live()==0
 assert api.ncclCommDestroy(comm)==0
 assert api.flash_profile_request(1,3)!=0

def main():
 if '--child' in sys.argv:child();return
 from flash.reader import Reader
 run='m3mock_'+str(time.monotonic_ns());env=os.environ.copy();env.update(LD_PRELOAD=str(ROOT/'build/libflash_probe.so'),FLASH_RUN_ID=run,FLASH_NODE_ID='mock',RANK='0')
 p=subprocess.run([sys.executable,__file__,'--child'],env=env,text=True,capture_output=True,timeout=30);print(p.stdout+p.stderr);assert p.returncode==0
 names=list(Path('/dev/shm').glob(f'flash_m2_{run}_mock_*'));assert len(names)==1
 r=Reader('/'+names[0].name,run,'mock');events=[]
 while (e:=r.read()) is not None:events.append(e)
 data=[e for e in events if e['api']==1];valid=[e for e in data if e.get('timing_status')==1]
 assert len(valid)==6 and all(e['duration_us']==2500 for e in valid)
 invalid=[e for e in data if e.get('timing_status')==3];assert len(invalid)==11 and all(e['duration_us'] is None for e in invalid)
 unsupported=[e for e in data if e.get('timing_status')==2];assert len(unsupported)==5 and all(e['duration_us'] is None for e in unsupported)
 for epoch in [1,2]:
  rows=[e for e in valid if e['profile_epoch']==epoch];assert len(rows)==3
  group=[e for e in rows if e['timing_scope']==2];assert len(group)==2 and group[0]['group_id']==group[1]['group_id']
 assert all('duration_us' not in e for e in data if e['state']==0)
 s=r.snapshot();assert s['write_pos']==s['read_pos']==s['attempts']==len(events) and s['closed']==1 and s['errors']==0
 r.cleanup();print(json.dumps(dict(status='PASS',synthetic=True,valid=len(valid),invalid=len(invalid),unsupported=len(unsupported),events=len(events),live_events=0)))
if __name__=='__main__':main()
