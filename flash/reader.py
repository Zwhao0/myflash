# ADAPTATION: C++ bridge owns all shared-memory access and memory ordering.
import argparse,ctypes,errno,json,os,re,time,hashlib
from pathlib import Path
API={1:"ncclAllReduce",2:"ncclAllGather",3:"ncclBroadcast",4:"ncclBcast",5:"ncclReduce",6:"ncclReduceScatter",7:"ncclSend",8:"ncclRecv",10:"ncclCommInitRank",11:"ncclCommInitRankConfig",12:"ncclCommSplit",13:"ncclCommInitAll",14:"ncclCommInitRankScalable",20:"ncclGroupStart",21:"ncclGroupEnd",22:"ncclGroupSimulateEnd",30:"ncclCommFinalize",31:"ncclCommDestroy",32:"ncclCommAbort",40:"ncclCommGetAsyncError",41:"ncclCommCount",42:"ncclCommUserRank",43:"ncclGetUniqueId",44:"ncclGetVersion",45:"ncclCommRegister",46:"ncclCommDeregister",47:"ncclMemAlloc",48:"ncclMemFree",49:"ncclRedOpCreatePreMulSum",50:"ncclRedOpDestroy",100:"COMM_MAPPING"}
IDENTITY={0:"UNKNOWN",1:"UNIQUE_ID_SHA256",2:"UNRESOLVED_SPLIT",3:"PENDING_GROUP",4:"UNSUPPORTED_INIT"}
class Reader:
    def __init__(self,name,run_id,node_id,library=None):
        self.name=name;self.run_id=run_id;self.node_id=node_id
        path=library or Path(__file__).resolve().parents[1]/"build/libflash_reader.so"
        self.lib=ctypes.CDLL(str(path),use_errno=True)
        self.lib.flash_ring_open.argtypes=[ctypes.c_char_p]*3;self.lib.flash_ring_open.restype=ctypes.c_void_p
        self.lib.flash_ring_read.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t];self.lib.flash_ring_read.restype=ctypes.c_int
        self.lib.flash_ring_snapshot.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t];self.lib.flash_ring_snapshot.restype=ctypes.c_int
        self.lib.flash_ring_ack.argtypes=[ctypes.c_void_p,ctypes.c_uint64];self.lib.flash_ring_ack.restype=ctypes.c_int
        self.lib.flash_ring_close.argtypes=[ctypes.c_void_p];self.lib.flash_ring_close.restype=None
        self.lib.flash_ring_unlink.argtypes=[ctypes.c_char_p]*3;self.lib.flash_ring_unlink.restype=ctypes.c_int
        self.lib.flash_ring_request.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint64];self.lib.flash_ring_request.restype=ctypes.c_int
        self.handle=self.lib.flash_ring_open(name.encode(),run_id.encode(),node_id.encode())
        if not self.handle:raise OSError(ctypes.get_errno(),"bridge open failed",name)
        try:self.context=self.snapshot()
        except BaseException:
            self.close();raise
        self.last_seq=self.context["read_pos"]
    def _check(self,rc):
        if rc<0:raise OSError(-rc,"shared memory bridge error",self.name)
        return rc
    def snapshot(self):
        buffer=ctypes.create_string_buffer(4096)
        self._check(self.lib.flash_ring_snapshot(self.handle,buffer,len(buffer)))
        value=json.loads(buffer.value)
        if value["abi"]!=2 or value["state"] not in (0,1) or value["run_id"]!=self.run_id or value["node_id"]!=self.node_id:raise ValueError("ABI/state/run identity mismatch")
        return value
    def request(self,state,epoch):
        self._check(self.lib.flash_ring_request(self.handle,state,epoch))
    def acknowledge(self,sequence):
        self._check(self.lib.flash_ring_ack(self.handle,sequence));self.last_seq=sequence
    def read(self,acknowledge=True):
        buffer=ctypes.create_string_buffer(4096)
        rc=self._check(self.lib.flash_ring_read(self.handle,buffer,len(buffer)))
        if not rc:return None
        value=json.loads(buffer.value)
        if value["publish_seq"]!=self.last_seq+1:raise ValueError("noncontiguous publication sequence")

        if value["global_rank"]!=self.context["global_rank"]:raise ValueError("rank mismatch")
        if value["api"] not in API or value["identity"] not in IDENTITY:raise ValueError("unknown event ABI enum")
        if value["identity"] in (1,3) and not re.fullmatch("[0-9a-f]{64}",value["id_hash"]):raise ValueError("invalid unique-id SHA256")
        if value["identity"] in (0,2,4) and value["id_hash"]:raise ValueError("unresolved identity carries hash")
        value.update(run_id=self.run_id,node_id=self.node_id,pid=self.context["pid"],api_name=API[value["api"]],identity_source=IDENTITY[value["identity"]],count_unit="bytes" if value["api"] in (45,47) else "elements" if value["api"] in range(1,9) else "not_applicable")
        value["record_digest"]=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if acknowledge:self.acknowledge(value["publish_seq"])
        return value
    def close(self):
        if self.handle:self.lib.flash_ring_close(self.handle);self.handle=None
    def cleanup(self):
        self.close();self._check(self.lib.flash_ring_unlink(self.name.encode(),self.run_id.encode(),self.node_id.encode()))
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
def recover_tail(path,context):
    """Only an incomplete unacknowledged last line may be truncated. Fail closed otherwise."""
    if not path.exists():
        if context["read_pos"]:raise ValueError("acknowledged output missing")
        return []
    data=path.read_bytes();lines=data.splitlines(keepends=True);rows=[];offset=0
    for index,line in enumerate(lines):
        if not line.endswith(b"\n"):
            if index!=len(lines)-1:raise ValueError("interior incomplete line")
            if len(rows)<context["read_pos"]:raise ValueError("acknowledged data truncated")
            with path.open("r+b") as f:f.truncate(offset);f.flush();os.fsync(f.fileno())
            break
        row=json.loads(line)
        content={k:v for k,v in row.items() if k!="record_digest"}
        if row.get("record_digest")!=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(",",":")).encode()).hexdigest():raise ValueError("durable record checksum mismatch")
        if row["publish_seq"]!=len(rows)+1 or any(row[k]!=context[k] for k in ("pid","global_rank","run_id","node_id")):
            raise ValueError("durable sequence/context mismatch")
        rows.append(row);offset+=len(line)
    if len(rows)<context["read_pos"] or len(rows)>context["write_pos"]:raise ValueError("acknowledged data absent or output ahead of ring")
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument("--run-id",required=True);p.add_argument("--node-id",required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--stop-file",type=Path,required=True)
    p.add_argument("--timeout",type=int,default=300);a=p.parse_args()
    if not re.fullmatch("[A-Za-z0-9_-]{1,80}",a.run_id) or not re.fullmatch("[A-Za-z0-9_-]{1,32}",a.node_id) or not 1<=a.timeout<=300:p.error("invalid run/node/budget")
    a.output.mkdir(parents=True,exist_ok=True);readers={};streams={};persisted={};errors=[];started=time.monotonic();stopped=None
    try:
        while time.monotonic()-started<a.timeout:
            for path in Path("/dev/shm").glob(f"flash_m2_{a.run_id}_{a.node_id}_*"):
                name="/"+path.name
                if name in readers:continue
                try:
                    reader=Reader(name,a.run_id,a.node_id);readers[name]=reader
                    event_path=a.output/f"events-{reader.context['pid']}-{reader.context['created_ns']}.ndjson"
                    existing=recover_tail(event_path,reader.context)
                    persisted[name]={e["publish_seq"] for e in existing}
                    streams[name]=event_path.open("a")
                except (OSError,ValueError) as error:
                    if getattr(error,"errno",None)!=errno.EAGAIN:errors.append(dict(name=name,error=str(error)));readers[name]=None
            for name,reader in readers.items():
                if reader is None:continue
                try:
                    # Bound each buffer's turn so other local ranks can be drained.
                    for _ in range(4096):
                        event=reader.read(acknowledge=False)
                        if event is None:break
                        if event["publish_seq"] not in persisted[name]:
                            streams[name].write(json.dumps(event)+"\n");streams[name].flush();os.fsync(streams[name].fileno())
                            persisted[name].add(event["publish_seq"])
                        reader.acknowledge(event["publish_seq"])
                    streams[name].flush()
                except (OSError,ValueError) as error:
                    errors.append(dict(name=name,error=str(error)));reader.close();readers[name]=None
            if a.stop_file.exists():
                if stopped is None:stopped=time.monotonic()
                if time.monotonic()-stopped>=0.5:break
            time.sleep(0.005)
        if stopped is None:errors.append(dict(error="reader timeout without launcher stop"))
        snapshots=[]
        for name,reader in readers.items():
            if reader is not None:
                snap=reader.snapshot();snap["name"]=name;snapshots.append(snap)
                if snap["read_pos"]!=snap["write_pos"] or not snap["closed"] or snap["poisoned"]:errors.append(dict(name=name,error="incomplete lifecycle/drain"))
                reader.close()
        result=dict(status="PASS" if readers and not errors else "FAIL",snapshots=snapshots,errors=errors)
        (a.output/"reader-result.json").write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(status=result["status"],buffers=len(snapshots),errors=len(errors))))
        return 0 if result["status"]=="PASS" else 1
    finally:
        for stream in streams.values():stream.close()
        for reader in readers.values():
            if reader is not None:reader.close()
if __name__=="__main__":raise SystemExit(main())
