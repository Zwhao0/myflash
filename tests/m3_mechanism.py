"""ADAPTATION: direct NCCL mechanism workload; independent of unchanged M1 numeric baseline.
CPU delay=20ms; GPU prework=40 fp32 512x512 matmuls on compute stream,
communication stream waits its end Event before the Probe start Event. No host sleep in GPU scenarios.
"""
import argparse,ctypes,datetime,json,os,sys,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m1_baseline import loaded_versions,own_memory_mib
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['mechanism','group'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 import torch
 rank=int(os.environ['RANK']);local=int(os.environ['LOCAL_RANK']);world=int(os.environ['WORLD_SIZE']);assert world==2
 torch.cuda.set_device(local);torch.cuda.set_per_process_memory_fraction(.01,local);torch.set_num_threads(1)
 expected=os.environ['FLASH_GPU_UUIDS'].split(',');actual=str(torch.cuda.get_device_properties(local).uuid)
 norm=lambda s:s.lower().removeprefix('gpu-').replace('-','');assert norm(actual)==norm(expected[local])
 lib=ctypes.CDLL(str(ROOT/'build/libm2_lifecycle_driver.so'),mode=os.RTLD_GLOBAL)
 # Load the actually mapped runtime as global for the public dynamic CUDA entrypoints.
 for line in Path('/proc/self/maps').read_text().splitlines():
  if '/libcudart.so' in line:ctypes.CDLL(line.split()[-1],mode=os.RTLD_GLOBAL|os.RTLD_NOLOAD);break
 api=ctypes.CDLL(None);ptr=ctypes.c_void_p;ci=ctypes.c_int
 for name,args in {'ncclGetUniqueId':[ptr],'ncclGroupStart':[],'ncclGroupEnd':[],'ncclAllReduce':[ptr,ptr,ctypes.c_size_t,ci,ci,ptr,ptr],'ncclCommDestroy':[ptr],'flash_profile_request':[ctypes.c_uint32,ctypes.c_uint64]}.items():getattr(api,name).argtypes=args;getattr(api,name).restype=ci
 for name in ['flash_profile_cuda_calls','flash_profile_cuda_syncs']:getattr(api,name).restype=ctypes.c_uint64
 lib.flash_m2_init_config.argtypes=[ctypes.POINTER(ptr),ci,ptr,ci];lib.flash_m2_init_config.restype=ci
 store=torch.distributed.TCPStore(os.environ['MASTER_ADDR'],int(os.environ['MASTER_PORT'])+2,world,rank==0,datetime.timedelta(seconds=120))
 uid=ctypes.create_string_buffer(128)
 if rank==0:assert api.ncclGetUniqueId(uid)==0;store.set('uid',uid.raw)
 uid.raw=store.get('uid');comm=ptr();assert lib.flash_m2_init_config(ctypes.byref(comm),world,uid,rank)==0
 stream=torch.cuda.Stream();compute=torch.cuda.Stream();other=torch.cuda.Stream();rows=[];controls=[];truth=[]
 record=dict(status='FAIL',rank=rank,local_rank=local,world_size=world,pid=os.getpid(),gpu_uuid=expected[local],rows=rows,controls=controls,communication_stream=stream.cuda_stream,compute_stream=compute.cuda_stream)
 epoch=0
 def request(state,e):
  assert api.flash_profile_request(state,e)==0;controls.append(dict(state=state,epoch=e,cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs()))
 def barrier(key):
  store.set(key+'-'+str(rank),'ready');store.wait([key+'-'+str(r) for r in range(world)])
 def submit(x,s=stream):
  before=api.flash_profile_cuda_calls();t=time.perf_counter_ns()
  assert api.ncclAllReduce(x.data_ptr(),x.data_ptr(),x.numel(),7,0,comm,ptr(s.cuda_stream))==0
  return dict(host_call_ns=time.perf_counter_ns()-t,probe_cuda_delta=api.flash_profile_cuda_calls()-before)
 def tensor(value):
  with torch.cuda.stream(stream):x=torch.full((4096,),float(value),dtype=torch.float32,device=local)
  stream.synchronize();return x
 try:
  # Kernel/cublas warmup outside any measured scope, finite bounded allocated workspace.
  left=torch.ones((512,512),device=local);right=torch.ones_like(left);output=torch.empty_like(left)
  with torch.cuda.stream(compute):
   for _ in range(3):torch.mm(left,right,out=output)
  compute.synchronize()
  for cycle in [1,2]:
   request(0,epoch);x=tensor(rank+1);barrier(f'monitor-{cycle}');stats=submit(x);stream.synchronize()
   assert torch.all(x==3).item() and stats['probe_cuda_delta']==0
   rows.append(dict(case='monitor',cycle=cycle,**stats))
   epoch=cycle;request(1,epoch)
   cases=['normal','cpu0','cpu1','gpu0','gpu1'] if a.mode=='mechanism' else ['single','group','nested','multi_stream']
   repeats=13 if a.mode=='mechanism' else 4
   for case in cases:
    for sample in range(repeats):
     x=tensor(rank+1);y=tensor(rank+2);barrier(f'{cycle}-{case}-{sample}')
     target=int(case[-1]) if case.startswith(('cpu','gpu')) else None
     gpu_ms=None
     if case.startswith('cpu') and rank==target:time.sleep(.020)
     if case.startswith('gpu') and rank==target:
      start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
      with torch.cuda.stream(compute):
       start.record()
       for _ in range(40):torch.mm(left,right,out=output)
       end.record()
      stream.wait_event(end) # Same dependency chain; hook start is enqueued after this wait.
     outer_start=torch.cuda.Event(enable_timing=True);outer_stop=torch.cuda.Event(enable_timing=True);outer_start.record(stream)
     sync_before=api.flash_profile_cuda_syncs()
     if case in ['group','nested','multi_stream']:
      assert api.ncclGroupStart()==0
      if case=='nested':assert api.ncclGroupStart()==0
      first=submit(x)
      if case=='multi_stream':other.wait_stream(stream)
      second=submit(y,other if case=='multi_stream' else stream)
      assert api.flash_profile_cuda_syncs()==sync_before # No wait before submission.
      if case=='nested':
       assert api.ncclGroupEnd()==0;assert api.flash_profile_cuda_syncs()==sync_before
      assert api.ncclGroupEnd()==0
      assert api.flash_profile_cuda_syncs()==sync_before+(case!='multi_stream')
     else:first=submit(x);second=None
     outer_stop.record(stream);outer_stop.synchronize();other.synchronize()
     assert torch.all(x==3).item()
     if second:assert torch.all(y==5).item()
     if case.startswith('gpu') and rank==target:end.synchronize();gpu_ms=start.elapsed_time(end)
     rows.append(dict(case=case,cycle=cycle,epoch=epoch,sample=sample,warmup=sample<3 if a.mode=='mechanism' else False,first=first,second=second,outer_interval_us=outer_start.elapsed_time(outer_stop)*1000,gpu_prework_ms=gpu_ms))
     truth.append(dict(case=case,cycle=cycle,sample=sample,target_rank=target,type='GPU dependency prework' if case.startswith('gpu') else 'CPU sleep' if case.startswith('cpu') else 'none',cpu_sleep_s=.020 if case.startswith('cpu') else 0,gpu_matmuls=40 if case.startswith('gpu') else 0))
   request(0,epoch);x=tensor(rank+1);barrier(f'restored-{cycle}');stats=submit(x);stream.synchronize()
   assert torch.all(x==3).item() and stats['probe_cuda_delta']==0
   rows.append(dict(case='restored',cycle=cycle,**stats))
  assert api.ncclCommDestroy(comm)==0
  record.update(status='PASS',communicators_destroyed=True,runtime=loaded_versions(),own_process_memory_mib=own_memory_mib(),cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs())
  assert record['own_process_memory_mib']<=2048
 except BaseException:record['error']=traceback.format_exc();raise
 finally:
  (a.output/f'rank-{rank}.json').write_text(json.dumps(record,indent=2));(a.output/f'evaluator-truth-rank-{rank}.json').write_text(json.dumps(truth,indent=2))
if __name__=='__main__':main()
