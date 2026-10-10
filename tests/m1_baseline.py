"""M1 native NCCL/DDP baseline; no FLASH or GreyHound code.
UPSTREAM APIs: PyTorch 2.8 distributed, DDP, CUDA Event documentation.
ADAPTATION: synthetic workload, assertions, UUID mapping, local evidence files.
"""
import argparse,ctypes,datetime,json,os,re,socket,subprocess,time,traceback
from pathlib import Path


def loaded_versions():
    mapped=set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts=line.split(None,5)
        if len(parts)==6 and re.search(r'lib(nccl|cudart|cuda)\.so',parts[5]):
            mapped.add(parts[5])
    versions=[]
    for path in sorted(mapped):
        family='nccl' if 'libnccl.so' in path else 'cudart' if 'libcudart.so' in path else None
        if not family: continue
        lib=ctypes.CDLL(path,mode=os.RTLD_NOLOAD|os.RTLD_LOCAL)
        fn=getattr(lib,'ncclGetVersion' if family=='nccl' else 'cudaRuntimeGetVersion')
        fn.argtypes=[ctypes.POINTER(ctypes.c_int)];fn.restype=ctypes.c_int
        value=ctypes.c_int();rc=fn(ctypes.byref(value))
        if rc!=0: raise RuntimeError(f'{family} version query returned {rc}')
        versions.append(dict(family=family,path=path,encoded=value.value))
    if not any(x['family']=='nccl' for x in versions):
        raise RuntimeError('NCCL runtime library not found in actual process maps')
    return dict(mapped_libraries=sorted(mapped),versions=versions)


def own_memory_mib():
    r=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,check=True)
    entries=[]
    for line in r.stdout.splitlines():
        pid,used=[x.strip() for x in line.split(',')]
        if pid==str(os.getpid()): entries.append(float(used))
    if not entries: raise RuntimeError('Own GPU process memory unavailable; cannot verify budget')
    return sum(entries)


def main():
    if not __debug__: raise RuntimeError('Python optimization disables correctness assertions')
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['allreduce','ddp'],required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--local-rank','--local_rank',type=int,default=None)
    p.add_argument('--steps',type=int,default=20)
    p.add_argument('--elements',type=int,default=4096)
    a=p.parse_args()
    if not 20<=a.steps<=100 or not 1<=a.elements<=65536:
        p.error('steps must be 20..100; element count must be 1..65536')
    import torch
    import torch.distributed as dist
    from torch.nn.parallel import DistributedDataParallel as DDP
    rank=int(os.environ['RANK']);local=int(os.environ['LOCAL_RANK']);world=int(os.environ['WORLD_SIZE'])
    if a.local_rank is not None: assert a.local_rank==local,'CLI/env local rank mismatch'
    record=dict(status='FAIL',mode=a.mode,rank=rank,local_rank=local,world_size=world,pid=os.getpid(),host=socket.gethostname(),steps=a.steps,torch=str(torch.__version__),torch_git=torch.version.git_version,torch_build_cuda=torch.version.cuda,rows=[])
    path=a.output/f'rank-{rank}.json'
    try:
        expected=os.environ['FLASH_GPU_UUIDS'].split(',')
        assert len(expected)==int(os.environ['LOCAL_WORLD_SIZE'])
        assert 0<=local<len(expected)
        assert torch.cuda.device_count()==len(expected)
        torch.cuda.set_device(local)
        prop=torch.cuda.get_device_properties(local)
        actual=str(prop.uuid)
        normalize=lambda s:s.lower().removeprefix('gpu-').replace('-','')
        assert normalize(actual)==normalize(expected[local]),'CUDA/rank UUID mismatch'
        record.update(gpu_uuid=expected[local],cuda_uuid=actual,gpu_name=prop.name,visible_devices=os.environ['CUDA_VISIBLE_DEVICES'])
        # ADAPTATION: 1% allocator cap; NCCL/context allocations separately audited.
        torch.cuda.set_per_process_memory_fraction(0.01,local)
        torch.set_num_threads(1)
        torch.manual_seed(20261010);torch.cuda.manual_seed_all(20261010)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False
        dist.init_process_group('nccl',timeout=datetime.timedelta(seconds=120))
        assert dist.get_rank()==rank and dist.get_world_size()==world
        dist.barrier();torch.cuda.synchronize(local)
        probe=torch.tensor([rank+1],device=local,dtype=torch.int64)
        dist.all_reduce(probe)
        assert probe.item()==world*(world+1)//2
        if a.mode=='allreduce':
            x=torch.empty(a.elements,dtype=torch.int64,device=local)
            for step in range(a.steps+5):
                x.fill_(rank+1+step)
                torch.cuda.synchronize(local)
                start=torch.cuda.Event(enable_timing=True);stop=torch.cuda.Event(enable_timing=True)
                begin=time.perf_counter();start.record()
                work=dist.all_reduce(x,op=dist.ReduceOp.SUM,async_op=True);work.wait()
                stop.record();stop.synchronize()
                completed_ms=(time.perf_counter()-begin)*1000
                expected_sum=world*(world+1)//2+step*world
                assert bool(torch.all(x==expected_sum).item()),f'AllReduce wrong at step {step}'
                record['rows'].append(dict(step=step,warmup=step<5,expected_sum=expected_sum,elements=a.elements,bytes=a.elements*x.element_size(),cuda_dependency_interval_ms=start.elapsed_time(stop),host_completion_ms=completed_ms))
            record.update(collectives_checked=a.steps+5,initial_expected_sum=world*(world+1)//2,dtype='int64')
        else:
            model=torch.nn.Sequential(torch.nn.Linear(16,32),torch.nn.Tanh(),torch.nn.Linear(32,4)).to(local)
            ddp=DDP(model,device_ids=[local],output_device=local,bucket_cap_mb=1,broadcast_buffers=False)
            optimizer=torch.optim.SGD(ddp.parameters(),lr=0.01)
            initial=torch.cat([v.detach().flatten() for v in model.parameters()]).clone()
            def check_sync():
                values=torch.cat([v.detach().flatten() for v in model.parameters()])
                reference=values.clone();dist.broadcast(reference,src=0)
                error=(values-reference).abs().max()
                assert error.item()<=1e-6,'DDP parameter divergence'
                return values,error.item()
            check_sync()
            # Rank-specific deterministic data tests real gradient averaging.
            generator=torch.Generator(device=local);generator.manual_seed(20261010+rank)
            x=torch.randn(8,16,device=local,generator=generator)
            y=torch.randn(8,4,device=local,generator=generator)
            for step in range(a.steps):
                torch.cuda.synchronize(local);begin=time.perf_counter()
                optimizer.zero_grad(set_to_none=True)
                loss=torch.nn.functional.mse_loss(ddp(x),y)
                assert torch.isfinite(loss).item(),'Nonfinite loss'
                loss.backward()
                for parameter in model.parameters():
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all().item(),'Missing/nonfinite gradient'
                optimizer.step();torch.cuda.synchronize(local)
                elapsed=(time.perf_counter()-begin)*1000
                values,error=check_sync()
                assert torch.isfinite(values).all().item(),'Nonfinite parameter'
                record['rows'].append(dict(step=step,loss=loss.item(),iteration_ms=elapsed,max_parameter_sync_error=error))
            final,error=check_sync()
            delta=(final-initial).abs().max().item()
            assert delta>0,'Parameters did not update'
            record.update(parameter_count=final.numel(),max_parameter_delta=delta,max_final_sync_error=error,final_loss=record['rows'][-1]['loss'],parallel_groups={'DP':list(range(world))},moe=False)
        record.update(runtime=loaded_versions(),peak_allocated_bytes=torch.cuda.max_memory_allocated(local),peak_reserved_bytes=torch.cuda.max_memory_reserved(local),own_process_memory_mib=own_memory_mib())
        record['memory_target_mib']=1536
        record['memory_target_exceeded']=record['own_process_memory_mib']>1536
        assert record['own_process_memory_mib']<=2048,'Process exceeded small-test 2048 MiB safety ceiling'
        dist.barrier();torch.cuda.synchronize(local)
        dist.destroy_process_group()
        record['process_group_destroyed']=True
        record['status']='PASS'
    except BaseException:
        record['error']=traceback.format_exc()
        raise
    finally:
        # Failure teardown can wait; external launcher bounds total time.
        if dist.is_initialized():
            try:dist.destroy_process_group()
            except BaseException:record['destroy_error']=traceback.format_exc()
        with path.open('x') as f:json.dump(record,f,indent=2)


if __name__=='__main__': main()
