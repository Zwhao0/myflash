# M6-A control protocol v1

Scope: CPU control engineering only; `MANUAL_TEST_TRIGGER`; two logical nodes on
one host, CPU simulated Probe, virtual seconds. `final_alert=false` and
`final_fault_ranks=[]` are invariants. No detector import or evaluator input.

PAPER: SPEC S1/S2/S4, chapter3 §3.2.1 pp23–24, §3.2.2 pp25–27,
§3.2.3 pp27–29: Global↔Redis↔Local↔Probe; 0 Monitor / 1 Profile;
iteration ms; 500 records; max(ms/1000×2.2,20 seconds).
ADAPTATION: all following versioning, fencing, hash, receipt, timeouts and failure
semantics. Exact source baseline PR9 7746fccb88718a5567da0d042d2679672d4226fc:
`flash/reader.py:Reader.request`, `native/probe.cpp:apply_boundary`,
`docs/m3/DESIGN.md`, `flash/profile_input.py:validate_bundle`,
`flash/localization.py:analyze`. No GreyHound code reused.

`schema_version=1`, immutable run_id, expected_nodes and disjoint expected_ranks,
node rank mapping, monotonically increasing profile_epoch. A run is registered
once. A duplicate manual request_id with identical manifest/trigger returns its
original epoch; conflicting request_id is rejected; completed requests never
reopen an epoch. New epoch requires verified Monitor closure of prior epoch.

Commands bind run_id/node_id/profile_epoch, requested_state, expected node/rank
sets, command_id, global generation, local generation, requested_at_seconds and
deadline_seconds. ACK contains exact command hash, accepted_at_seconds and
`COMMAND_ACCEPTED_ONLY`. It is not an applied-state event. Each rank must produce
an actual CPU simulated legal scope event with state, epoch, command_id, both
fences, rank/node/run, increasing scope sequence and application time. No scope
means no evidence. Header/latest rank is never an all-rank proof.

Requests written ≠ Local accepted ≠ Probe applied ≠ all ranks applied ≠ valid
sampling complete. M3 freezes state per outer Group/collective scope; the mock
applies at legal scope start and records completion data separately. It does not
implement native ABI or CUDA, and cannot prove real GPU completion.

Window starts after all rank evidence and ends after the full PAPER duration.
Sample envelopes bind source=CPU_SIMULATED_PROBE, run/epoch/rank/node, command/fences,
collected_at_seconds, row and SHA256. No pre-window/at-end sample is pooled;
old command events are counted as ignored. Data hashes, per-node drain hashes,
manifest hash, M4 exact expected samples/records and all ranks are required.
Samples preserve communicator hash, process instance, comm generation, Group
batch, count(elements), duration(us), timing definition. Group shared records
are counted by unchanged M4 independent-scope logic, not multiplied into timings.

Analysis is existing M4 only, with PROVISIONAL_CANDIDATE, NO_CANDIDATE or
AMBIGUOUS_SPEC. Missing/corrupt/unsupported data is INCOMPLETE with reason;
missing iteration/unknown completion is INSUFFICIENT_EVIDENCE; stale confirmed
iteration is TIMEOUT. TIMEOUT never becomes NO_CANDIDATE. Commands and error
receipts include finite deadline/error reason. No final rank is emitted.

Reset requires a new Monitor command ACK and fresh actual boundary proof from
every expected rank. Partial reset stays pending then BLOCKED. Profile result,
failed/reset attempts, original partial evidence and reason are retained.
A restarted owner increments its fencing generation, invalidates the active
round, and reissues reset with new fences. Old owner writes/boundaries are rejected.
An unrecovered BLOCKED run needs operator reconciliation of exact run/node/ranks;
no new epoch, no automatic recovery claim. Transport loss produces an unconfirmed
receipt locally; reconnect records ABORTED and requires verified reset. No probe
application is asserted while disconnected, and reset may remain physically
unapplied until future legal scopes. This is not high availability.

UPSTREAM: Redis scripts execute atomically; optimistic CAS is conditional on the
whole document revision. This is an API semantic, not a persistence guarantee.
[Redis EVAL documentation](https://redis.io/docs/latest/develop/programmability/eval-intro/)
and [Redis LTRIM](https://redis.io/docs/latest/commands/ltrim/) were checked for the
engineering design. Implementation stores a bounded JSON list inside one atomic
run document, with `records[-500:]`; no copied Redis source or client source.
Real loaded Redis/client versions are reported only if actual integration runs.
