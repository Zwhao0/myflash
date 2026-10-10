# ADAPTATION: 2-rank direct NCCL public API lifecycle/Group functional test.
# Probe contains no synchronization; GPU completion is asserted by the workload.
import argparse,ctypes,datetime,json,os,sys,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m1_baseline import own_memory_mib,loaded_versions
def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",default="lifecycle");p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    import torch
    rank=int(os.environ["RANK"]);local=int(os.environ["LOCAL_RANK"]);world=int(os.environ["WORLD_SIZE"])
    assert world==2 and __debug__
    torch.cuda.set_device(local);torch.cuda.set_per_process_memory_fraction(.01,local);torch.set_num_threads(1)
    expected=os.environ["FLASH_GPU_UUIDS"].split(",")
    actual=str(torch.cuda.get_device_properties(local).uuid)
    normalize=lambda s:s.lower().removeprefix("gpu-").replace("-","")
    assert normalize(actual)==normalize(expected[local])
    lib=ctypes.CDLL(str(Path(__file__).resolve().parents[1]/"build/libm2_lifecycle_driver.so"),mode=os.RTLD_GLOBAL)
    api=ctypes.CDLL(None)
    ptr=ctypes.c_void_p;i32=ctypes.c_int;size=ctypes.c_size_t
    signatures={
     "ncclGetUniqueId":[ptr],"ncclGroupStart":[],"ncclGroupEnd":[],
     "ncclAllReduce":[ptr,ptr,size,i32,i32,ptr,ptr],"ncclAllGather":[ptr,ptr,size,i32,ptr,ptr],
     "ncclBroadcast":[ptr,ptr,size,i32,i32,ptr,ptr],"ncclReduce":[ptr,ptr,size,i32,i32,i32,ptr,ptr],
     "ncclReduceScatter":[ptr,ptr,size,i32,i32,ptr,ptr],"ncclSend":[ptr,size,i32,i32,ptr,ptr],"ncclRecv":[ptr,size,i32,i32,ptr,ptr],
     "ncclCommSplit":[ptr,i32,i32,ctypes.POINTER(ptr),ptr],
     "ncclCommFinalize":[ptr],"ncclCommDestroy":[ptr],"ncclCommCount":[ptr,ctypes.POINTER(i32)],
     "ncclCommUserRank":[ptr,ctypes.POINTER(i32)],"ncclCommGetAsyncError":[ptr,ctypes.POINTER(i32)],
    }
    for name,args in signatures.items():fn=getattr(api,name);fn.argtypes=args;fn.restype=i32
    for name in ["flash_m2_init_config","flash_m2_init_rank"]:
     fn=getattr(lib,name);fn.argtypes=[ctypes.POINTER(ptr),i32,ptr,i32];fn.restype=i32
    rows=[];comms=[];record=dict(status="FAIL",rank=rank,local_rank=local,world_size=world,pid=os.getpid(),gpu_uuid=expected[local],rows=rows)
    def call(name,*args):
     rc=getattr(api,name)(*args);rows.append(dict(api=name,result=rc));assert rc==0,(name,rc)
    def sync():torch.cuda.synchronize(local)
    def tensor(value,n=1):return torch.full((n,),float(value),dtype=torch.float32,device=local)
    def allreduce(comm,value,group=False):
     x=tensor(value,16);call("ncclAllReduce",x.data_ptr(),x.data_ptr(),16,7,0,comm,None)
     if not group:sync();assert bool(torch.all(x==value*world).item())
     return x
    try:
     store=torch.distributed.TCPStore(os.environ["MASTER_ADDR"],int(os.environ["MASTER_PORT"])+2,world,rank==0,datetime.timedelta(seconds=120))
     def uid(label):
      data=ctypes.create_string_buffer(128)
      if rank==0:call("ncclGetUniqueId",data);store.set(label,data.raw)
      data.raw=store.get(label);return data
     cid=uid("init-config");comm=ptr()
     rc=lib.flash_m2_init_config(ctypes.byref(comm),world,cid,rank);assert rc==0;rows.append(dict(api="ncclCommInitRankConfig",result=rc));comms.append(comm)
     n=i32();r=i32();err=i32()
     call("ncclCommCount",comm,ctypes.byref(n));call("ncclCommUserRank",comm,ctypes.byref(r));call("ncclCommGetAsyncError",comm,ctypes.byref(err))
     assert n.value==world and r.value==rank and err.value==0
     x=allreduce(comm,2)
     call("ncclGroupStart");call("ncclGroupStart")
     x=allreduce(comm,3,True);y=allreduce(comm,4,True)
     call("ncclGroupEnd");call("ncclGroupEnd");sync()
     assert bool(torch.all(x==6).item()) and bool(torch.all(y==8).item())
     inp=tensor(rank+1);out=tensor(0,world)
     call("ncclAllGather",inp.data_ptr(),out.data_ptr(),1,7,comm,None);sync();assert out.tolist()==[1.,2.]
     inp=tensor(7 if rank==0 else 0);out=tensor(0)
     call("ncclBroadcast",inp.data_ptr(),out.data_ptr(),1,7,0,comm,None);sync();assert out.item()==7
     inp=tensor(rank+1,world);out=tensor(0)
     call("ncclReduceScatter",inp.data_ptr(),out.data_ptr(),1,7,0,comm,None);sync();assert out.item()==3
     inp=tensor(rank+1);out=tensor(0)
     call("ncclReduce",inp.data_ptr(),out.data_ptr(),1,7,0,0,comm,None);sync()
     if rank==0:assert out.item()==3
     transfer=tensor(9 if rank==0 else 0)
     call("ncclGroupStart")
     if rank==0:call("ncclSend",transfer.data_ptr(),1,7,1,comm,None)
     else:call("ncclRecv",transfer.data_ptr(),1,7,0,comm,None)
     call("ncclGroupEnd");sync();assert transfer.item()==9
     split=ptr();call("ncclCommSplit",comm,0,world-1-rank,ctypes.byref(split),None);comms.append(split)
     call("ncclCommUserRank",split,ctypes.byref(r));assert r.value==world-1-rank
     allreduce(split,5)
     cid=uid("init-rank-group");second=ptr()
     call("ncclGroupStart")
     rc=lib.flash_m2_init_rank(ctypes.byref(second),world,cid,rank);assert rc==0;rows.append(dict(api="ncclCommInitRank",result=rc))
     call("ncclGroupEnd");assert second.value;comms.append(second);allreduce(second,6)
     for c in reversed(comms):call("ncclCommFinalize",c);call("ncclCommDestroy",c)
     record.update(communicators_destroyed=True,runtime=loaded_versions(),own_process_memory_mib=own_memory_mib(),status="PASS")
     assert record["own_process_memory_mib"]<=2048
    except BaseException:
     record["status"]="FAIL";record["error"]=traceback.format_exc();raise
    finally:
     (a.output/f"rank-{rank}.json").write_text(json.dumps(record,indent=2))
if __name__=="__main__":main()
