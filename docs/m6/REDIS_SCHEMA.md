# M6-A Redis schema and lifecycle

ADAPTATION namespace: `flash:m6a:v1:{run_id}:document`, one standalone Redis string.
Entire schema1 JSON document updated by Lua EVAL revision compare-and-set.
Global/local generations increment atomically on claims; each logical mutation
checks its generation. Bounded CAS contention retries: 8. External Probe effects
are performed outside CAS, after command acceptance, and recheck current fences
at scope boundaries. This protects the CPU adapter; extending it to a real shared
memory ABI is NOT_RUN and needs a separately approved protocol.

| Object | Content |
|---|---|
| root | schema/run/revision, immutable nodes/ranks, global generation, node generation, state, epoch counter, final flags |
| active | request_id/hash, trigger, iteration record/hash, manifest/hash, duration/window/deadline, transitions, node evidence, analysis, first failure |
| node evidence | command/hash ACK, per-rank applied proof, sample envelopes, ignored-old/outside-window counts, drain receipt/data hash |
| epochs | closed original Profile evidence, reset attempts/proof, result, closed time; never reused as current data |
| events | sequential receipt/claim/request/transition/failure/reset history |
| iterations[rank] | last accepted one-based iteration, ≤500 original records/hashes/receiver confirmation times |

PAPER 500-item bound from SPEC S2/§3.2.2 pp25–27. IterationRecord fields including
actual iteration, iteration_time_ms, timestamp/source, timing_boundary and
cuda_completion_wait are preserved verbatim. Transport identity is separate
from timing. Receiver time is one-host monotonic receipt time, not iteration end.
Same retained iteration+exact full record hash => DUPLICATE_CONFIRMED. Different
value for retained iteration => CONFLICT, never overwrite. Future gap/out of
order => GAP_OR_OUT_OF_ORDER. Evicted older iterations => STALE_OUTSIDE_RETENTION;
exact dedup cannot be proven beyond 500 and no success is invented. A cursor
before retained history returns insufficient evidence. Freshness deadline returns
TIMEOUT. Reconnecting publishers inspect and resume last stored iteration;
source restart cannot silently reset the counter to1; use a new run_id.

WRITE_CONFIRMED/DUPLICATE_CONFIRMED means server memory response observed.
WRITE_UNCONFIRMED means request may or may not have committed; re-read and retry
exact saved record. This publisher returns receipts; it is an independent stage
for already completed IterationRecords, not a silent drop-in Reporter sink.
Keep the original Reporter/LocalHistory measurement and completed-record outbox;
caller must inspect receipts. No CUDA synchronize is added. G20 remains OPEN.

No live-run TTL (automatic expiry would destroy fences). 100 epochs / 10000
receipt events / 8MiB document hard limits; exceeding capacity rejects mutation
and needs archive/new run, never silently truncate evidence. Polling may retain
local unconfirmed receipts; controller service persistence is not implemented.
Finite socket/connect timeouts required. No Pub/Sub loss assumptions, no
unbounded Redis iteration list, no cross-node ordering promise beyond atomic
run document revision. Redis server identity is checked; restart/missing document
blocks resumption. INFO and CAS are separate operations: no atomic guarantee
against server restart in between; no HA/cluster/failover support.

Temporary actual integration uses a dedicated owned Popen server, port0,
socket0600 inside dir0700, no persistence and disable-thp=no. The human user's
supplemental authorization permits the private fixed Redis build and isolated
redis-py venv described in dependency-lock.json/installation.json; initial
missing-dependency BLOCKED receipts remain historical. No formal environment or
system service change. Tests delete only exact allocated run keys and terminate
only owned children, preserving stdout/receipts. No FLUSHALL/FLUSHDB, system
Redis configuration, shared server or global cleanup. Missing dependencies
still return exit3/BLOCKED, not a skipped PASS. Successful write is not disk
durability, training completion or scientific detection success.

ADAPTATION: the manual CPU harness uses rank0's fresh, confirmed iteration for
the window formula; other ranks retain independently isolated iteration streams.
This engineering selection is not a cross-rank training completion rule. G20
remains OPEN; actual training/rank aggregation requires a separately approved
contract. Actual transport coverage and cleanup limits are in VALIDATION.md.
