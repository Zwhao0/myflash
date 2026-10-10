# ADAPTATION: select exactly previously approved M1 UUIDs and preserve raw launch commands.
import argparse,json,subprocess,sys,time
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--run-id",required=True);p.add_argument("--node-rank",type=int,default=0)
 p.add_argument("--nnodes",type=int,default=1);p.add_argument("--gpu-count",type=int,required=True)
 p.add_argument("--mode",choices=["allreduce","ddp","lifecycle"],required=True);p.add_argument("--probe",action="store_true")
 p.add_argument("--master-port",type=int,default=29751);a=p.parse_args()
 root=Path(__file__).resolve().parents[1]
 # This project's M1 final successful mapping is the authorization provenance.
 previous=root/"runs/m1d-20261010-allreduce-04"/f"node-{a.node_rank}"/"manifest.json"
 m=json.loads(previous.read_text());gpus=m["gpus"][:a.gpu_count]
 assert 1<=a.gpu_count<=8 and len(gpus)==a.gpu_count
 cmd=["python3","scripts/m2_launch.py","--python",str(root/".venv-m1/bin/python"),"--run-id",a.run_id,"--gpus",",".join(gpus),"--mode",a.mode,"--nnodes",str(a.nnodes),"--node-rank",str(a.node_rank),"--master-addr","127.0.0.1" if a.nnodes==1 else m["command"][m["command"].index("--master-addr")+1],"--master-port",str(a.master_port),"--timeout","300","--allow-shared"]
 if a.probe:cmd.append("--probe")
 out=root/"runs"/a.run_id;out.mkdir(parents=True,exist_ok=True)
 control=out/f"control-node-{a.node_rank}.json"
 with control.open("x") as f:json.dump(dict(command=cmd,mapping_source=str(previous),FLASH=a.probe,state=0 if a.probe else None,fault_injection=False,truth="not applicable",predictions="not applicable"),f,indent=2)
 started=time.monotonic()
 with (out/f"launch-node-{a.node_rank}.log").open("x") as f:
  proc=subprocess.run(cmd,cwd=root,text=True,stdout=f,stderr=subprocess.STDOUT)
 elapsed=time.monotonic()-started
 (out/f"exit-node-{a.node_rank}.json").write_text(json.dumps(dict(exit_code=proc.returncode,elapsed_s=elapsed),indent=2))
 print(json.dumps(dict(run_id=a.run_id,node_rank=a.node_rank,exit_code=proc.returncode,elapsed_s=elapsed)))
 if proc.returncode:return proc.returncode
 cmd=["python3","scripts/m2_verify.py","--run-id",a.run_id,"--node-rank",str(a.node_rank),"--world",str(a.nnodes*a.gpu_count),"--mode",a.mode]
 r=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
 (out/f"verify-node-{a.node_rank}.log").write_text(r.stdout+r.stderr)
 (out/f"verify-node-{a.node_rank}.json").write_text(json.dumps(dict(command=cmd,exit_code=r.returncode),indent=2))
 print(r.stdout+r.stderr)
 if r.returncode==0 and a.probe:
  cmd=["python3","scripts/m2_cleanup.py","--run-id",a.run_id,"--node-rank",str(a.node_rank)]
  cleanup=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
  (out/f"cleanup-node-{a.node_rank}.log").write_text(cleanup.stdout+cleanup.stderr)
  (out/f"cleanup-node-{a.node_rank}.json").write_text(json.dumps(dict(command=cmd,exit_code=cleanup.returncode),indent=2))
  print(cleanup.stdout+cleanup.stderr)
  if cleanup.returncode:return cleanup.returncode
 return r.returncode
if __name__=="__main__":sys.exit(main())
