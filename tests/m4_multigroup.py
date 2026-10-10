"""ADAPTATION: finite normal-only direct NCCL multi-group validation, not MoE."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m1_baseline import loaded_versions,own_memory_mib
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['multigroup'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import torch
    rank=int(os.environ['RANK']);local=int(os.environ['LOCAL_RANK']);world=int(os.environ['WORLD_SIZE']);assert world==4
    torch.cuda.set_device(local);torch.cuda.set_per_process_memory_fraction(.01,local);torch.set_num_threads(1)
    expected=os.environ['FLASH_GPU_UUIDS'].split(',');actual=str(torch.cuda.get_device_properties(local).uuid)
    norm=lambda s:s.lower().removeprefix('gpu-').replace('-','');assert norm(actual)==norm(expected[local])
    lib=ctypes.CDLL(str(ROOT/'build/libm2_lifecycle_driver.so'),mode=os.RTLD_GLOBAL)
    for line in Path('/proc/self/maps').read_text().splitlines():
        if '/libcudart.so' in line:ctypes.CDLL(line.split()[-1],mode=os.RTLD_GLOBAL|os.RTLD_NOLOAD);break
    api=ctypes.CDLL(None);ptr=ctypes.c_void_p;ci=ctypes.c_int
    for name,args in {'ncclGetUniqueId':[ptr],'ncclAllReduce':[ptr,ptr,ctypes.c_size_t,ci,ci,ptr,ptr],'ncclCommDestroy':[ptr],'flash_profile_request':[ctypes.c_uint32,ctypes.c_uint64]}.items():
        getattr(api,name).argtypes=args;getattr(api,name).restype=ci
    api.flash_profile_cuda_calls.restype=ctypes.c_uint64;api.flash_profile_cuda_syncs.restype=ctypes.c_uint64
    lib.flash_m2_init_config.argtypes=[ctypes.POINTER(ptr),ci,ptr,ci];lib.flash_m2_init_config.restype=ci
    store=torch.distributed.TCPStore(os.environ['MASTER_ADDR'],int(os.environ['MASTER_PORT'])+2,world,rank==0,datetime.timedelta(seconds=120))
    groups=[('DP',[0,1]),('DP',[2,3]),('TP',[0,2]),('TP',[1,3]),('DP',[0,1])]
    comms={};states=[];rows=[];controls=[]
    record=dict(status='FAIL',rank=rank,pid=os.getpid(),gpu_uuid=expected[local],world_size=world,rows=rows,controls=controls)
    stream=torch.cuda.Stream()
    def barrier(key):
        store.set(key+'-'+str(rank),'ready');store.wait([key+'-'+str(r) for r in range(world)])
    def request(state,epoch):
        assert api.flash_profile_request(state,epoch)==0
        controls.append(dict(state=state,epoch=epoch,cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs()))
    try:
        for i,(label,members) in enumerate(groups):
            uid=ctypes.create_string_buffer(128)
            if rank==members[0]:assert api.ncclGetUniqueId(uid)==0;store.set('uid'+str(i),uid.raw)
            uid.raw=store.get('uid'+str(i));h=hashlib.sha256(uid.raw).hexdigest()
            states.append(dict(label=label,members=members,id_hashes=[h],evidence='explicit direct NCCL group definition in tests/m4_multigroup.py; synthetic parallel labels, not real MoE'))
            if rank in members:
                comm=ptr();assert lib.flash_m2_init_config(ctypes.byref(comm),len(members),uid,members.index(rank))==0;comms[i]=comm
            barrier('init'+str(i))
        request(0,0)
        for epoch in [1,2]:
            for phase in ['monitor_before','profile','monitor_after']:
                request(1 if phase=='profile' else 0,epoch-1 if phase=='monitor_before' else epoch)
                for sample in range(6 if phase=='profile' else 1):
                    for i,(label,members) in enumerate(groups):
                        key=f'{epoch}-{phase}-{sample}-{i}'
                        barrier(key+'-ready')
                        if rank in members:
                            with torch.cuda.stream(stream):x=torch.full((4096,),float(rank+1),device=local,dtype=torch.float32)
                            stream.synchronize();before=api.flash_profile_cuda_calls();syncs=api.flash_profile_cuda_syncs()
                            assert api.ncclAllReduce(x.data_ptr(),x.data_ptr(),4096,7,0,comms[i],ptr(stream.cuda_stream))==0
                            stream.synchronize();assert torch.all(x==sum(r+1 for r in members)).item()
                            if phase!='profile':assert api.flash_profile_cuda_calls()==before
                            else:assert api.flash_profile_cuda_syncs()==syncs+1
                            rows.append(dict(epoch=epoch,phase=phase,group_index=i,sample=sample,numerics=True))
                        barrier(key+'-done')
        request(0,2)
        for comm in comms.values():assert api.ncclCommDestroy(comm)==0
        record.update(status='PASS',communicators_destroyed=True,runtime=loaded_versions(),own_process_memory_mib=own_memory_mib(),cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs())
        assert record['own_process_memory_mib']<=2048
    except BaseException:
        record['error']=traceback.format_exc();raise
    finally:
        (a.output/f'rank-{rank}.json').write_text(json.dumps(record,indent=2))
        (a.output/f'parallel-states-rank-{rank}.json').write_text(json.dumps(states,indent=2))
        (a.output/f'evaluator-truth-rank-{rank}.json').write_text(json.dumps(dict(faults=[],scenario='normal_only',interpretation='no fault injection; any candidate is provisional false positive'),indent=2))


if __name__=='__main__':main()
