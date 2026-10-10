"""ADAPTATION: strict offline Profile schema and evidence validation (M4 DESIGN)."""
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


class InputError(ValueError):
    pass


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)) or int(value) < minimum:
        raise InputError("invalid " + name)
    return int(value)


def require(condition, reason):
    if not condition:
        raise InputError(reason)


def read_records(paths, source_format, context, supplements=None):
    """Select a declared run/epoch from full M3 streams; never infer labels or truth."""
    rows, audit = [], []
    for path in paths:
        path = Path(path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if source_format == "m3_ndjson":
            require(not data or data.endswith(b"\n"), "incomplete NDJSON tail")
            raw = [json.loads(line) for line in data.splitlines()]
            if raw:
                first = raw[0]
                for seq, row in enumerate(raw, 1):
                    require(row["publish_seq"] == seq, "raw publication gap/duplicate")
                    require(all(row[k] == first[k] for k in ("run_id", "node_id", "pid", "global_rank")), "raw context changed")
                    payload = {k: v for k, v in row.items() if k != "record_digest"}
                    require(row.get("record_digest") == hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "raw digest mismatch")
                require(first["run_id"] == context["run_id"], "cross-run raw file")
        elif source_format == "m3_csv":
            raw = list(csv.DictReader(data.decode().splitlines()))
            require(supplements is not None, "M3 CSV needs evidence sidecar")
        else:
            raise InputError("unsupported input format")
        selected = 0
        for row in raw:
            if row["run_id"] != context["run_id"]:
                require(source_format == "m3_csv" and context.get("source_run_policy") == "explicit_selection", "cross-run source")
                continue
            if integer(row["state"], "state") != 1 or integer(row["profile_epoch"], "epoch") != context["profile_epoch"]:
                continue
            api = row.get("api_name", row["api"])
            if source_format == "m3_ndjson" and not 1 <= row["api"] <= 8:
                continue
            rank = integer(row.get("global_rank", row.get("rank")), "rank")
            seq = integer(row["publish_seq"], "publish_seq", 1)
            if source_format == "m3_csv":
                key = f"{row['run_id']}:{rank}:{seq}"
                require(key in supplements, "missing CSV sample evidence")
                extra = supplements[key]
                allowed = {"node_id", "pid", "process_instance", "thread_id", "comm_generation", "comm_rank", "comm_size", "identity_source", "result", "source_csv_sha256"}
                require(set(extra) <= allowed, "CSV sidecar cannot overwrite measured fields")
                require(extra.get("source_csv_sha256") == digest, "CSV sidecar digest mismatch")
                source = dict(row, **extra)
                api = row["api"]
            else:
                source = row
            status = source["timing_status"]
            scope = source["timing_scope"]
            cuda = source["cuda_results"]
            if isinstance(cuda, str):
                cuda = json.loads(cuda)
            rows.append(dict(run_id=source["run_id"], profile_epoch=integer(source["profile_epoch"], "epoch", 1),
                node_id=source["node_id"], global_rank=rank, id_hash=source.get("id_hash", source.get("comm_id_hash")),
                comm_generation=integer(source["comm_generation"], "generation", 1), process_instance=str(source.get("process_instance", source.get("pid", ""))),
                comm_rank=integer(source["comm_rank"], "comm_rank"), comm_size=integer(source["comm_size"], "comm_size", 1),
                identity_source=source["identity_source"], timing_scope={0:"none", 1:"collective", 2:"group_shared"}.get(scope, scope),
                timing_status={0:"NOT_APPLICABLE",1:"VALID",2:"UNSUPPORTED",3:"INVALID_DURATION"}.get(status, status),
                duration_us=None if source.get("duration_us") in (None, "") else float(source["duration_us"]), duration_unit="us", timing_definition="m3_cuda_event_v2", state=1,
                api=api, count=integer(source["count"], "count"), count_unit=source["count_unit"], datatype=integer(source["datatype"], "datatype"),
                group_id=integer(source["group_id"], "group_id"), group_depth=integer(source["group_depth"], "group_depth"),
                thread_id=str(source["thread_id"]), sample_seq=seq, result=integer(source["result"], "result"), cuda_results=cuda))
            selected += 1
        audit.append(dict(path=str(path), sha256=digest, source_records=len(raw), selected_records=selected,
            selection="explicit run/epoch and Profile collective; other epochs/Monitor audited, not pooled"))
    return rows, audit


def validate_bundle(bundle):
    require(bundle.get("schema_version") == 1, "unsupported schema")
    context = bundle["context"]
    run = context["run_id"]
    epoch = integer(context["profile_epoch"], "profile_epoch", 1)
    require(isinstance(run, str) and bool(run), "empty run_id")
    records = bundle["records"]
    require(bool(records), "empty Profile input")
    declarations = bundle["communicators"]
    require(bool(declarations), "missing communicator manifest")
    hashes = [d["id_hash"] for d in declarations]
    require(len(hashes) == len(set(hashes)), "duplicate communicator declaration")
    require(all(re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes), "invalid id_hash")
    expected, rank_nodes = {}, {}
    for d in declarations:
        members = d["members"]
        require(bool(members) and len(members) == len(set(members)), "invalid member set")
        members = [integer(r, "member rank") for r in members]
        local_members = set()
        for local in d["local_instances"]:
            rank = integer(local["global_rank"], "rank")
            node = local["node_id"]
            require(isinstance(node, str) and bool(node), "empty node")
            require(rank not in rank_nodes or rank_nodes[rank] == node, "rank mapped to multiple nodes")
            rank_nodes[rank] = node
            key = (d["id_hash"], node, rank, str(local["process_instance"]), integer(local["comm_generation"], "generation", 1))
            require(key not in expected, "duplicate local communicator instance")
            require(bool(key[3]), "empty process_instance")
            integer(local["expected_samples"], "expected_samples", 1)
            integer(local["expected_records"], "expected_records", 1)
            expected[key] = local
            local_members.add(rank)
        require(local_members == set(members), "manifest missing rank/communicator")
    by_hash = {d["id_hash"]:d for d in declarations}
    scopes, seen, counts, values, signatures = {}, set(), Counter(), defaultdict(dict), set()
    normalized = []
    for raw in records:
        r = dict(raw)
        require(r["run_id"] == run and integer(r["profile_epoch"], "epoch", 1) == epoch, "run/epoch pollution")
        for key in ("global_rank", "comm_generation", "sample_seq", "comm_rank", "comm_size", "count", "datatype", "group_id", "group_depth", "state", "result"):
            r[key] = integer(r[key], key, 1 if key in ("comm_generation", "sample_seq", "comm_size") else 0)
        require(r["state"] == 1, "non-Profile record")
        require(r["identity_source"] == "UNIQUE_ID_SHA256", "unreliable communicator identity")
        require(r["id_hash"] in by_hash, "unexpected communicator")
        require(r["global_rank"] in by_hash[r["id_hash"]]["members"], "unexpected rank")
        require(r["comm_size"] == len(by_hash[r["id_hash"]]["members"]) and r["comm_rank"] < r["comm_size"], "communicator size/rank mismatch")
        instance = (r["id_hash"], r["node_id"], r["global_rank"], str(r["process_instance"]), r["comm_generation"])
        require(instance in expected, "undeclared local instance")
        require(r["comm_rank"] == expected[instance]["comm_rank"], "local rank mapping mismatch")
        sample = (r["node_id"], str(r["process_instance"]), r["sample_seq"])
        require(sample not in seen, "duplicate sample")
        seen.add(sample)
        require(r["timing_status"] == "VALID", "non-VALID timing: " + str(r["timing_status"]))
        require(r["duration_unit"] == "us" and r["count_unit"] == "elements", "unit mismatch")
        duration = r["duration_us"]
        require(not isinstance(duration, bool) and duration is not None and duration != "", "missing/boolean duration")
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            raise InputError("illegal duration")
        require(math.isfinite(duration) and duration >= 0, "nonfinite/negative duration")
        require(r["timing_definition"] in ("m3_cuda_event_v2", "synthetic_nonnegative_v1"), "unknown timing definition")
        if r["timing_definition"] == "m3_cuda_event_v2":
            require(duration > 0, "M3 valid timing must be positive")
        cuda = r["cuda_results"]
        require(isinstance(cuda, list) and len(cuda) == 11 and all(type(v) is int for v in cuda) and cuda[:10] == [0]*10 and cuda[10] == -1 and r["result"] == 0, "incomplete/failed timing API evidence")
        require(r["api"] in ("ncclAllReduce", "ncclAllGather", "ncclBroadcast", "ncclBcast", "ncclReduce", "ncclReduceScatter", "ncclSend", "ncclRecv"), "unknown NCCL API")
        require(r["datatype"] <= 11, "unsupported datatype")
        scope = r["timing_scope"]
        require(scope in ("collective", "group_shared"), "invalid timing scope")
        if scope == "group_shared":
            require(r["group_id"] > 0 and r["group_depth"] > 0, "invalid Group identity")
            timing = (r["node_id"], str(r["process_instance"]), str(r["thread_id"]), "group", r["group_id"])
        else:
            require(r["group_id"] == 0 and r["group_depth"] == 0, "collective has Group metadata")
            timing = (*sample, "collective")
        shared = (duration, r["timing_status"], tuple(cuda))
        require(timing not in scopes or scopes[timing] == shared, "Group shared timing mismatch")
        scopes[timing] = shared
        values[instance][timing] = duration
        counts[instance] += 1
        signatures.add((r["api"], r["count"], r["datatype"]))
        r["duration_us"] = duration
        normalized.append(r)
    for d in declarations:
        mapping = defaultdict(set)
        for local in d["local_instances"]:
            mapping[local["global_rank"]].add(local["comm_rank"])
        require(all(len(v) == 1 for v in mapping.values()) and {next(iter(v)) for v in mapping.values()} == set(range(len(d["members"]))), "inconsistent local/global rank bijection")
    for key, local in expected.items():
        require(len(values[key]) == local["expected_samples"] and counts[key] == local["expected_records"], "incomplete communicator samples/records")
    states = bundle["parallel_states"]
    require(bool(states), "missing explicit parallel states")
    tag_hashes, matched = defaultdict(set), set()
    for state in states:
        require(isinstance(state["label"], str) and bool(state["label"]) and bool(state["evidence"]), "missing label evidence")
        require(len(state["members"]) == len(set(state["members"])), "duplicate parallel member")
        eligible = state.get("id_hashes", hashes)
        require(bool(eligible) and len(eligible) == len(set(eligible)), "empty/duplicate parallel identities")
        for h in eligible:
            require(h in by_hash, "parallel state references missing communicator")
            if set(state["members"]) == set(by_hash[h]["members"]):
                tag_hashes[state["label"]].add(h)
                matched.add(h)
            elif "id_hashes" in state:
                raise InputError("parallel state member mismatch")
    require(matched == set(hashes), "unmatched communicator label/member set")
    shared_comms = defaultdict(set)
    for r in normalized:
        if r["timing_scope"] == "group_shared":
            shared_comms[(r["node_id"], str(r["process_instance"]), str(r["thread_id"]), r["group_id"])].add(r["id_hash"])
    risks = []
    if len(signatures) > 1:
        risks.append("HETEROGENEOUS_API_COUNT_DATATYPE: duration baseline retained without normalization")
    if shared_comms:
        risks.append("GROUP_SHARED: repeated members collapsed per local communicator/scope")
    if any(len(v) > 1 for v in shared_comms.values()):
        risks.append("CORRELATED_CROSS_COMM_GROUP: common duration is not independent timing")
    return dict(context=context, records=normalized, declarations=by_hash, instances=values,
        tags={k:sorted(v) for k,v in tag_hashes.items()},
        completeness=dict(records=len(normalized), independent_process_scopes=len(scopes), communicator_scope_observations=sum(len(v) for v in values.values()),
            expected_instances=len(expected), valid_records=len(normalized)),
        measurement_signatures=[dict(api=api, count=count, count_unit="elements", datatype=datatype,
            member_records=sum(1 for r in normalized if (r["api"], r["count"], r["datatype"]) == (api, count, datatype)))
            for api,count,datatype in sorted(signatures)], risks=risks)
