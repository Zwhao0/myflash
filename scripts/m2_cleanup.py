# ADAPTATION: cleanup only validated, drained, closed objects of this exact run/node.
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.reader import Reader
def main():
 p=argparse.ArgumentParser();p.add_argument("--run-id",required=True);p.add_argument("--node-rank",type=int,required=True);a=p.parse_args()
 root=Path(__file__).resolve().parents[1];out=root/"runs"/a.run_id/f"node-{a.node_rank}"
 result=json.loads((out/"probe/reader-result.json").read_text());assert result["status"]=="PASS"
 cleaned=[];absent=[]
 for snapshot in result["snapshots"]:
  assert snapshot["run_id"]==a.run_id and snapshot["node_id"]==f"node-{a.node_rank}" and snapshot["closed"] and snapshot["read_pos"]==snapshot["write_pos"]
  if not (Path("/dev/shm")/snapshot["name"][1:]).exists():
   absent.append(snapshot["name"]);continue
  with Reader(snapshot["name"],a.run_id,f"node-{a.node_rank}") as r:
   current=r.snapshot();assert current["closed"] and current["write_pos"]==current["read_pos"]
   assert current["created_ns"]==snapshot["created_ns"] and current["pid"]==snapshot["pid"]
   r.cleanup();cleaned.append(snapshot["name"])
 (out/"cleanup.json").write_text(json.dumps(dict(status="PASS",removed=cleaned,already_absent=absent),indent=2))
 print(json.dumps(dict(status="PASS",removed_count=len(cleaned),already_absent_count=len(absent))))
if __name__=="__main__":main()
