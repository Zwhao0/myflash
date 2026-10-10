"""ADAPTATION: explicit optional Probe entry, retaining M1 resource checks.
UPSTREAM: https://docs.pytorch.org/docs/2.8/elastic/run.html
"""
import argparse,datetime,hashlib,json,os,re,signal,socket,subprocess,sys,time
from pathlib import Path


def group_members(pgid):
    # Read PID/PGID only; retain just our own new session's members.
    r=subprocess.run(['ps','-eo','pid=,pgid='],text=True,capture_output=True,check=True,timeout=5)
    return [int(line.split()[0]) for line in r.stdout.splitlines() if int(line.split()[1])==pgid]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--python',default=sys.executable)
    p.add_argument('--profile',action='store_true')
    p.add_argument('--probe',action='store_true',help='explicit M2 LD_PRELOAD selection')
    p.add_argument('--run-id',required=True)
    p.add_argument('--gpus',required=True,help='explicit comma-separated full GPU UUIDs')
    p.add_argument('--mode',choices=['allreduce','ddp','mechanism','group'],required=True)
    p.add_argument('--nnodes',type=int,default=1);p.add_argument('--node-rank',type=int,default=0)
    p.add_argument('--master-addr',default='127.0.0.1');p.add_argument('--master-port',type=int,default=29551)
    p.add_argument('--timeout',type=int,default=300)
    p.add_argument('--allow-shared',action='store_true',help='only with explicit small-test user authorization')
    p.add_argument('--socket-ifname',help='exact, verified local interface name')
    a=p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',a.run_id):p.error('invalid run_id')
    uuids=a.gpus.split(',')
    if len(set(uuids))!=len(uuids) or any(not re.fullmatch(r'GPU-[0-9a-fA-F-]{36}',x) for x in uuids):p.error('unique full GPU UUIDs required')
    if not 20<=a.timeout<=300 or not 1<=a.nnodes<=2 or not 0<=a.node_rank<a.nnodes or not 1024<=a.master_port<=65535:p.error('invalid launch bounds')
    root=Path(__file__).resolve().parents[1];out=root/'runs'/a.run_id/f'node-{a.node_rank}'
    out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
    started=time.monotonic()
    source_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
    source_diff=subprocess.run(['git','diff','--binary','HEAD'],cwd=root,capture_output=True,check=True).stdout
    (out/'source.diff').write_bytes(source_diff)
    manifest=dict(source_commit=source_commit,source_diff_sha256=hashlib.sha256(source_diff).hexdigest(),run_id=a.run_id,node_rank=a.node_rank,host=socket.gethostname(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=sys.argv,timeout_s=a.timeout,gpus=uuids,status='BLOCKED',exit_code=77,source_hashes={str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),root/'tests/m1_baseline.py']})
    process=None;reader=None;reader_log=None;result=77
    try:
        if os.environ.get('LD_PRELOAD'):raise RuntimeError('LD_PRELOAD must be empty for native baseline')
        if any(x in os.environ for x in ['NCCL_IB_DISABLE','NCCL_P2P_DISABLE','NCCL_SHM_DISABLE','NCCL_NET']):raise RuntimeError('Unset inherited transport overrides before native baseline')
        r=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.total,memory.used,mig.mode.current','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
        (out/'gpu-preflight.log').write_text(r.stdout+r.stderr)
        gpu={}
        for line in r.stdout.splitlines():
            uuid,total,used,mig=[x.strip() for x in line.split(',')];gpu[uuid]=(float(total),float(used),mig)
        r=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
        (out/'occupancy-private.log').write_text(r.stdout+r.stderr)
        occupied={line.split(',')[0].strip() for line in r.stdout.splitlines() if line.strip()}
        for uuid in uuids:
            if uuid not in gpu:raise RuntimeError('Selected UUID missing')
            total,used,mig=gpu[uuid]
            if mig not in ['Disabled','[N/A]']:raise RuntimeError('MIG not supported by this mapping test')
            if total-used<3072:raise RuntimeError('Less than approved 3072 MiB free on selected GPU')
            if not a.allow_shared and uuid in occupied:raise RuntimeError('Selected GPU occupied; explicit shared-test authorization required')
        # Import preflight is host-only and uses exactly the requested Python.
        r=subprocess.run([a.python,'-c','import torch; import torch.distributed as d; assert d.is_nccl_available(); print(torch.__version__,torch.version.cuda)'],capture_output=True,text=True,timeout=20)
        (out/'python-preflight.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(f'PyTorch/NCCL preflight failed: {r.returncode}')
        env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=','.join(uuids),CUDA_DEVICE_ORDER='PCI_BUS_ID',FLASH_GPU_UUIDS=','.join(uuids),OMP_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':16:8',NCCL_DEBUG='INFO',NCCL_DEBUG_SUBSYS='INIT,NET,GRAPH',NCCL_DEBUG_FILE=str(out/'nccl.%h.%p.log'),NCCL_BUFFSIZE='1048576',NCCL_MIN_CTAS='1',NCCL_MAX_CTAS='1',NCCL_NVLS_ENABLE='0')
        if a.socket_ifname:env['NCCL_SOCKET_IFNAME']='='+a.socket_ifname
        manifest['test_environment']={k:env[k] for k in ['CUDA_VISIBLE_DEVICES','CUDA_DEVICE_ORDER','FLASH_GPU_UUIDS','OMP_NUM_THREADS','CUBLAS_WORKSPACE_CONFIG','NCCL_DEBUG','NCCL_DEBUG_SUBSYS','NCCL_DEBUG_FILE','NCCL_BUFFSIZE','NCCL_MIN_CTAS','NCCL_MAX_CTAS','NCCL_NVLS_ENABLE']}
        if 'NCCL_SOCKET_IFNAME' in env:manifest['test_environment']['NCCL_SOCKET_IFNAME']=env['NCCL_SOCKET_IFNAME']
        cmd=[a.python,'-m','torch.distributed.run','--nnodes',str(a.nnodes),'--nproc-per-node',str(len(uuids)),'--node-rank',str(a.node_rank),'--master-addr',a.master_addr,'--master-port',str(a.master_port),'--max-restarts','0',str(root/'tests/m1_baseline.py'),'--mode',a.mode,'--output',str(out)]
        if a.mode in ['mechanism','group']:cmd[cmd.index(str(root/'tests/m1_baseline.py'))]=str(root/'tests/m3_mechanism.py')
        elif a.profile:cmd[cmd.index(str(root/'tests/m1_baseline.py'))]=str(root/'tests/m3_regression.py')
        if a.probe:
            lib=root/'build/libflash_probe.so'
            if not lib.is_file():raise RuntimeError('Probe not built')
            env.update(LD_PRELOAD=str(lib),FLASH_RUN_ID=a.run_id,FLASH_NODE_ID=f'node-{a.node_rank}',FLASH_NCCL_LIBRARY=str(root/'.venv-m1/lib/python3.12/site-packages/nvidia/nccl/lib/libnccl.so.2'),FLASH_RING_CAPACITY='8192',FLASH_CUDA_LIBRARY=str(root/'.venv-m1/lib/python3.12/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12'))
            manifest['probe']=True;manifest['probe_library_sha256']=hashlib.sha256(lib.read_bytes()).hexdigest()
            manifest['probe_environment']={k:env[k] for k in ['LD_PRELOAD','FLASH_RUN_ID','FLASH_NODE_ID','FLASH_NCCL_LIBRARY','FLASH_RING_CAPACITY']}
            reader_cmd=[a.python,'-m','flash.reader','--run-id',a.run_id,'--node-id',f'node-{a.node_rank}','--output',str(out/'probe'),'--stop-file',str(out/'reader.stop'),'--timeout',str(a.timeout)]
            manifest['reader_command']=reader_cmd
            reader_log=(out/'reader.log').open('x')
            reader=subprocess.Popen(reader_cmd,stdout=reader_log,stderr=subprocess.STDOUT,cwd=root,start_new_session=True)
        manifest['command']=cmd
        with (out/'torchrun.log').open('x') as log:
            process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=root,env=env,start_new_session=True)
            manifest['launch_pid']=process.pid
            try:result=process.wait(timeout=max(1,a.timeout-60-(time.monotonic()-started)))
            except subprocess.TimeoutExpired:
                result=124;os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        if group_members(process.pid):
            result=1;os.killpg(process.pid,signal.SIGTERM);time.sleep(0.5)
            if group_members(process.pid):os.killpg(process.pid,signal.SIGKILL)
        manifest['remaining_own_pids']=group_members(process.pid)
        if manifest['remaining_own_pids']:result=1
        expected=range(a.node_rank*len(uuids),(a.node_rank+1)*len(uuids))
        records=[]
        if result==0:
            for rank in expected:
                value=json.loads((out/f'rank-{rank}.json').read_text());records.append(value)
                if value['status']!='PASS' or not value.get('communicators_destroyed' if a.mode in ['mechanism','group'] else 'process_group_destroyed'):result=1
            # Local UUID uniqueness and global expected ranks are checked per node.
            if len({v['gpu_uuid'] for v in records})!=len(uuids):result=1
        manifest['status']='PASS' if result==0 else 'FAIL'
        manifest['exit_code']=result
    except BaseException as error:
        manifest['error']=type(error).__name__+': '+str(error)
        if process is not None:
            result=1;manifest['status']='FAIL';manifest['exit_code']=result
            if group_members(process.pid):os.killpg(process.pid,signal.SIGKILL)
    finally:
        if reader is not None:
            (out/'reader.stop').write_text('training process exited; drain current run')
            try:reader_rc=reader.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(reader.pid,signal.SIGKILL);reader_rc=reader.wait(timeout=5)
            manifest['reader_exit_code']=reader_rc
            if reader_rc and manifest['exit_code']==0:manifest.update(exit_code=1,status='FAIL')
            if reader_log:reader_log.close()
        manifest['source_hashes'].update({str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for q in list((root/'native').glob('*'))+list((root/'flash').glob('*.py'))+list((root/'tests').glob('m2_*'))+list((root/'tests').glob('m3_*'))+list((root/'scripts').glob('m2_*'))+list((root/'scripts').glob('m3_*')) if q.is_file()})
        manifest['elapsed_s']=time.monotonic()-started
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
        print(json.dumps(dict(status=manifest['status'],exit_code=manifest['exit_code'],run_dir=str(out))))
    return manifest['exit_code']


if __name__=='__main__':sys.exit(main())
