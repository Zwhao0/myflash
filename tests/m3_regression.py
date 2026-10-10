# ADAPTATION: runtime wrapper runs unchanged M1 with two explicit Profile epochs.
import ctypes,json,os,runpy,sys
from pathlib import Path
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
ROOT=Path(__file__).resolve().parents[1]
for line in Path('/proc/self/maps').read_text().splitlines():
 if '/libcudart.so' in line:ctypes.CDLL(line.split()[-1],mode=os.RTLD_GLOBAL|os.RTLD_NOLOAD);break
api=ctypes.CDLL(None);api.flash_profile_request.argtypes=[ctypes.c_uint32,ctypes.c_uint64];api.flash_profile_request.restype=ctypes.c_int
api.flash_profile_cuda_calls.restype=ctypes.c_uint64;api.flash_profile_cuda_syncs.restype=ctypes.c_uint64
rows=[];index=0;state=0;epoch=0;step_saved=0
mode=sys.argv[sys.argv.index('--mode')+1]
out=Path(sys.argv[sys.argv.index('--output')+1])
def request(s,e):
 global state,epoch
 assert api.flash_profile_request(s,e)==0;state=s;epoch=e
 rows.append(dict(state=s,epoch=e,cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs()))
def boundary():
 global index
 index+=1
 if index==4:request(1,1)
 if index==10:request(0,1)
 if index==(15 if mode=="allreduce" else 12):request(1,2)
 if index==(21 if mode=="allreduce" else 16):request(0,2)
 saved=api.flash_profile_cuda_calls()
 return saved
if mode=='allreduce':
 original=dist.all_reduce
 def ar(*args,**kwargs):
  saved=boundary();value=original(*args,**kwargs)
  if not state:assert api.flash_profile_cuda_calls()==saved
  return value
 dist.all_reduce=ar
else:
 original=DDP.forward
 def forward(*args,**kwargs):
  global index,step_saved
  # Twenty unchanged steps; profile steps4..9 and12..15.
  saved=boundary();step_saved=saved;value=original(*args,**kwargs)
  if not state:assert api.flash_profile_cuda_calls()==saved
  return value
 DDP.forward=forward
 optimizer_step=torch.optim.SGD.step
 def step(*args,**kwargs):
  if not state:assert api.flash_profile_cuda_calls()==step_saved
  return optimizer_step(*args,**kwargs)
 torch.optim.SGD.step=step
request(0,0)
runpy.run_path(str(ROOT/'tests/m1_baseline.py'),run_name='__main__')
request(0,epoch)
# Final M1 collectives after profile steps provide actual Monitor boundaries.
(out/f'profile-rank-{os.environ["RANK"]}.json').write_text(json.dumps(dict(controls=rows,cuda_calls=api.flash_profile_cuda_calls(),cuda_syncs=api.flash_profile_cuda_syncs()),indent=2))
