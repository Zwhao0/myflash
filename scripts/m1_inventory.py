"""ADAPTATION: host-only M1 inventory; no CUDA context, service or installation."""
import argparse,ctypes,datetime,importlib.metadata as md,json,os,re,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--peer');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
rid='m1a-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=root/'runs'/rid;out.mkdir(parents=True,exist_ok=False);os.chmod(out,0o700)
commands=[['hostname'],['uname','-srmo'],['cat','/etc/os-release'],['id','-un'],['nvidia-smi','--query-gpu=index,name,uuid,pci.bus_id,memory.total,memory.used,utilization.gpu,driver_version','--format=csv'],['nvidia-smi','-L'],['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_gpu_memory','--format=csv'],['nvidia-smi','topo','-m'],['lspci','-nn'],['numactl','--hardware'],['nvcc','--version'],['readlink','-f','/usr/local/cuda'],['ip','-br','link'],['ip','-br','addr'],['ip','route','show'],['rdma','link','show'],['ibv_devinfo'],['ibdev2netdev'],['ibstat'],['df','-h',str(root),'/dev/shm'],[sys.executable,'--version'],['ldconfig','-p']]
if a.peer:commands.extend([['ip','route','get',a.peer],['ping','-c','2','-W','2',a.peer]])
records=[];results={}
for i,cmd in enumerate(commands):
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=20);rc=r.returncode;body=r.stdout+r.stderr
 except FileNotFoundError:rc=127;body='NOT_INSTALLED'
 except subprocess.TimeoutExpired:rc=124;body='TIMEOUT'
 name=f'{i:02}.log';(out/name).write_text(body);records.append(dict(command=cmd,exit_code=rc,log=name));results[cmd[0]+' '+(cmd[1] if len(cmd)>1 else '')]=(rc,body)
packages={}
for name in ['torch','nvidia-nccl-cu12','nvidia-cuda-runtime-cu12','megatron-core','transformer-engine','flash-attn','Rbeast','redis']:
 try:packages[name]=md.version(name)
 except md.PackageNotFoundError:packages[name]='NOT_INSTALLED'
stack={'python':sys.version,'executable':sys.executable,'packages':packages,'executables':{n:shutil.which(n) for n in ['python','python3','conda','torchrun','nvcc','redis-cli','redis-server','docker','podman']},'known_env_paths_exist':{str(q):q.exists() for q in [Path.home()/'miniconda3/bin/python',Path.home()/'anaconda3/bin/python',Path('/opt/conda/bin/python'),root/'.venv/bin/python']}}
try:
 import torch
 stack.update(torch=str(torch.__version__),torch_path=torch.__file__,torch_build_cuda=torch.version.cuda,torch_git=torch.version.git_version)
 loaded=set()
 for line in Path('/proc/self/maps').read_text().splitlines():
  parts=line.split(None,5)
  if len(parts)==6 and re.search(r'lib(nccl|cudart|cuda)\.so',parts[5]):loaded.add(parts[5])
 stack['mapped_libraries']=sorted(loaded);stack['runtime_versions']=[]
 for path in sorted(loaded):
  family='nccl' if 'libnccl.so' in path else 'cudart' if 'libcudart.so' in path else None
  if not family:continue
  try:
   lib=ctypes.CDLL(path,mode=os.RTLD_NOLOAD|os.RTLD_LOCAL);fn=getattr(lib,'ncclGetVersion' if family=='nccl' else 'cudaRuntimeGetVersion');fn.argtypes=[ctypes.POINTER(ctypes.c_int)];fn.restype=ctypes.c_int
   value=ctypes.c_int();rc=fn(ctypes.byref(value));stack['runtime_versions'].append(dict(family=family,path=path,exit_code=rc,encoded=value.value))
  except Exception as e:stack['runtime_versions'].append(dict(path=path,error=type(e).__name__))
except Exception as e:stack['torch_import_error']=type(e).__name__+': '+str(e)
(out/'stack.json').write_text(json.dumps(stack,indent=2));(out/'manifest.json').write_text(json.dumps({'run_id':rid,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':records,'stack_command':'host-only inline Python; source inventory.py'},indent=2));(out/'inventory.py').write_text(Path(__file__).read_text() if '__file__' in globals() and Path(__file__).is_file() else 'source supplied via project scripts/m1_inventory.py')
print('RUN_DIR',out);print('PYTHON',sys.version.split()[0]);print('PACKAGES',json.dumps(packages));print('EXECUTABLES',json.dumps(stack['executables']));print('ENV_PATHS_EXIST',json.dumps(stack['known_env_paths_exist']));print('TORCH_IMPORT',stack.get('torch_import_error','OK'))
for r in records:print('PROBE',r['command'][0],r['exit_code'],r['log'])
# Only aggregate output; raw machine identity/topology/jobs stay in out.
print('GPU_COUNT',len(results['nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,memory.total,memory.used,utilization.gpu,driver_version'][1].splitlines())-1)
print('RDMA_ETHERNET_PORTS',results['ibstat '][1].count('Link layer: Ethernet') if 'ibstat ' in results else 0)
