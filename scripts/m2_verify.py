# ADAPTATION: independent functional-event validator; no detection or localization.
import argparse,json,sys,hashlib
from collections import Counter,defaultdict
from pathlib import Path
def verify(directory,world,mode):
    manifest=json.loads((directory/"manifest.json").read_text())
    assert manifest["exit_code"]==0 and manifest["status"]=="PASS"
    ranks=[json.loads(p.read_text()) for p in sorted(directory.glob("rank-*.json"))]
    expected=list(range(manifest["node_rank"]*len(manifest["gpus"]),(manifest["node_rank"]+1)*len(manifest["gpus"])))
    assert sorted(r["rank"] for r in ranks)==expected
    for r in ranks:
        assert r["status"]=="PASS" and r["world_size"]==world and r["own_process_memory_mib"]<=2048
        if mode=="allreduce":assert r["collectives_checked"]==25 and len(r["rows"])==25 and r["initial_expected_sum"]==world*(world+1)//2
        if mode=="ddp":
            assert len(r["rows"])==20 and r["parameter_count"]==676 and r["max_parameter_delta"]>0
            assert all(s["max_parameter_sync_error"]<=1e-6 for s in r["rows"])
    result=dict(node_rank=manifest["node_rank"],mode=mode,ranks=expected,training_exit=manifest["exit_code"],probe=manifest.get("probe",False),elapsed_s=manifest["elapsed_s"],source_hashes=manifest["source_hashes"])
    if not manifest.get("probe"):return result
    assert manifest["reader_exit_code"]==0
    reader=json.loads((directory/"probe/reader-result.json").read_text());assert reader["status"]=="PASS" and not reader["errors"]
    snapshots=reader["snapshots"];assert sorted(s["global_rank"] for s in snapshots)==expected
    for r in ranks:
        assert next(s for s in snapshots if s["global_rank"]==r["rank"])["pid"]==r["pid"]
    for s in snapshots:
        assert s["state"]==0 and s["closed"]==1 and s["read_pos"]==s["write_pos"]>0
        assert s["attempts"]==s["write_pos"] and not any(s[k] for k in ["dropped_full","dropped_lock","errors","bad_records","poisoned"])
    events=[]
    for p in sorted((directory/"probe").glob("events-*.ndjson")):
        events.extend(json.loads(line) for line in p.read_text().splitlines())
    by_rank=defaultdict(list)
    for e in events:
        assert e["run_id"]==manifest["run_id"] and e["node_id"]==f"node-{manifest['node_rank']}"
        assert e["global_rank"] in expected and e["result"]==0 and e["timestamp_ns"]>0 and e["call_seq"]>0
        assert not any("duration" in k for k in e)
        by_rank[e["global_rank"]].append(e)
    summaries=[]
    for rank in expected:
        row=by_rank[rank];snap=next(s for s in snapshots if s["global_rank"]==rank)
        assert len(row)==snap["write_pos"] and {e["pid"] for e in row}=={snap["pid"]}
        assert [e["publish_seq"] for e in row]==list(range(1,len(row)+1))
        counts=Counter(e["api_name"] for e in row)
        data=[e for e in row if 1<=e["api"]<=8]
        assert data and counts["ncclAllReduce"]>0
        if mode=="lifecycle":assert counts["ncclGroupStart"]>0 and counts["ncclGroupEnd"]>0
        mapped=[e for e in data if e["identity"]==1]
        assert mapped and all(e["comm_ptr"]>0 and e["comm_generation"]>0 and len(e["id_hash"])==64 and 0<=e["comm_rank"]<e["comm_size"] for e in mapped)
        if mode!="lifecycle":
            assert len(mapped)==len(data) # major training paths must have reliable unique-id identity
            assert {e["comm_size"] for e in mapped}=={world}
            assert {e["comm_rank"] for e in mapped}=={rank}
        if mode=="allreduce":assert len([e for e in data if e["api"]==1 and e["count"]==4096 and e["datatype"]==4])==25
        if mode=="ddp":
            assert counts["ncclBcast"]==26 and counts["ncclAllGather"]==1 and counts["ncclAllReduce"]==23
        if mode=="lifecycle":
            for name in ["ncclCommInitRank","ncclCommInitRankConfig","ncclCommSplit","ncclCommFinalize","ncclCommDestroy","COMM_MAPPING","ncclAllGather","ncclBroadcast","ncclReduce","ncclReduceScatter"]:
                assert counts[name]>0,name
            assert any(e["group_id"]==0 for e in data) and any(e["group_id"]>0 for e in data) and any(e["group_depth"]==2 for e in data)
            unresolved=[e for e in data if e["identity"]==2]
            assert unresolved and all(e["id_hash"]=="" for e in unresolved)
            assert counts["ncclSend"]==1 if rank==0 else counts["ncclRecv"]==1
        summaries.append(dict(rank=rank,events=len(row),apis=dict(counts),identities=sorted({e["identity_source"] for e in data}),id_hashes=sorted({e["id_hash"] for e in mapped}),comm_sizes=sorted({e["comm_size"] for e in mapped}),group_inside=sum(e["group_id"]>0 for e in data),group_outside=sum(e["group_id"]==0 for e in data)))
    result.update(reader_exit=manifest["reader_exit_code"],rank_summaries=summaries,total_events=len(events),loss=0)
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--run-id",required=True);p.add_argument("--node-rank",type=int,required=True);p.add_argument("--world",type=int,required=True);p.add_argument("--mode",choices=["allreduce","ddp","lifecycle"],required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];directory=root/"runs"/a.run_id/f"node-{a.node_rank}"
    result=verify(directory,a.world,a.mode)
    (directory/"verification.json").write_text(json.dumps(dict(status="PASS",**result),indent=2))
    print(json.dumps(dict(status="PASS",total_events=result.get("total_events"),ranks=result["ranks"])))
if __name__=="__main__":main()
