# TASK08 G20 Reporter/outbox — CPU mock result

Baseline: PR18 exact `89cfdbb679b55aa8f81d39f39c72e77426976d85`, tree
`5edc2add8eb963a2f03086f635c5ba8a1f658eba`. User explicitly selects this source;
independent PR18 review PASS is not inferred. Local independent branch
`codex/m6b-ready-g20-reporter-outbox`, worktree `m6b-s8-work`.

CPU functional acceptance **PASS**: 33 new tests and94 unchanged tests;
every final test command exit0, no timeout, children waited. Local MacBook Air,
macOS26.6.2 arm64, existing bundled CPython3.12.14 and SQLite runtime captured in
`validation.json`. No installation or server operation. This is not GPU,
Redis socket/disk, physical fail-stop, performance or M6-B evidence.

## Defect and final behavior

The preserved baseline reproduction exits1: offline MemoryStore returns
WRITE_UNCONFIRMED, but Reporter.end() returns a completed record and sets
active=None. Final Reporter checks structured status/confirmed/SHA/server-memory
ACK, freezes elapsed milliseconds and completion timestamp once, and raises
PublicationUnconfirmed without clearing active/pending on an invalid or unknown
receipt. Repeated end() resubmits the same immutable payload without another
clock read or CUDA completion wait. Exceptions also retain it. begin() blocks
another iteration; abort() refuses to discard a completed pending record.
Legacy LocalHistory/None-returning local sinks preserve their original interface;
that legacy return is not a remote durability proof.

DurableIterationOutbox is an explicit opt-in Publisher wrapper, not installed in
M6 production callers. SQLite transaction enqueue commits before any transport
read/write. Scope is one run/rank/path with one framework writer and at most one
pending record. Retention is500 ACKed records **plus** the pending record; pending
never ages out with the remote500 window. Synchronous EXTRA, DELETE journal and
fullfsync ON are requested and synchronous/journal settings checked. Database
initialization fsyncs its existing parent directory; no implicit directory,
schema repair, run registration, seed cursor or background retry loop.

Each publish/recover invocation reads the unchanged IterationReader first.
Exact retained payload confirms a server-memory ACK without another CAS.
Absent new record is exactly resubmitted via unchanged IterationPublisher;
unknown ACK remains pending. Local/remote conflict, malformed ACK, corrupted
payload, missing run, sequence gap and evicted unknown cannot advance local ACK.
Local ACK watermark and500 retention update in one SQLite transaction.
Restart exposes pending/position/next_iteration; recover() is bounded to one read
and at most one Publisher invocation (Publisher retains its existing8 CAS
contention attempts). Application resume must reconcile its own checkpoint with
these positions; this code never fabricates completed iterations to catch up.

DurableIterationConsumer uses a **separate** scope-bound path. poll() calls the
original Reader with persisted cursor and selects records strictly beyond it;
the original Reader continues returning the full retained window. poll() never
advances cursor. commit() accepts only a nonempty exact delivered prefix and
atomically compares the old cursor before advancement. Changed payload, skip,
unseen record or stale second consumer instance is rejected. Restart after poll
redelivers; restart after cursor commit starts after that position. Application
side effects are not part of this SQLite transaction and need application
idempotence; no exactly-once side-effect guarantee.

## Exercised boundaries and limits

New tests cover read disconnect, CAS disconnect before commit, commit followed
by lost ACK, exact retry, duplicate/no second CAS, local and remote conflicts,
malformed ACK, local/remote corruption, missing run/restart, ordered backpressure,
scope/schema/integer validation, durable Reporter restart,500 ACK plus pending,
exact500 boundary and501 eviction, explicit consumer prefix, stale concurrent
consumer, poll/commit restart and retention gap. Six actual owned CPU child
exits71–76 are intentional crash checkpoints (parent assertions exit0), each
bounded10s: committed enqueue, uncommitted local ACK, remote commit before local
ACK, consumer before/after commit, uncommitted enqueue rollback. MemoryStore
remote state in one child is exported and reloaded as a mock snapshot, not
represented as durable Redis or an external service.

Durability starts **after local enqueue transaction commit**. A crash before
that commit cannot recover an unrecorded elapsed time; the test verifies rollback,
not recovery of unknown work. SQLite/filesystem errors propagate while Reporter
keeps the frozen record where the process remains alive. Power-loss, filesystem
faults, Redis AOF/replication/HA, arbitrary database corruption repair, multiple
framework writers and real training checkpoint recovery are NOT_RUN/unsupported.
The original Publisher confirmed_at_seconds caller-clock contract is unchanged;
cross-process monotonic clock/freshness remains a G20 follow-up. Original500
remote retention, schemas, controller, detection and localization are unchanged.

## Sources and evidence

- PAPER: SPEC S2 / G20, chapter3 pp25,35 completed iteration / ms /500 retention;
  existing specification used, no new paper scientific rule inferred.
- ADAPTATION: exact baseline `flash/iteration_reporter.py:IterationReporter.end`,
  `flash/m6_iteration.py:IterationPublisher.publish/IterationReader.read`,
  `flash/m6_store.py:MemoryStore/transaction`; new frozen ACK, local SQLite ledger
  and explicit consumer processing cursor. No GreyHound or third-party source copied.
- UPSTREAM: [Python sqlite3 transaction API](https://docs.python.org/3.12/library/sqlite3.html)
  and [SQLite synchronous/journal PRAGMAs](https://www.sqlite.org/pragma.html#pragma_synchronous).
  Standard-library/runtime APIs only; documentation is not empirical crash evidence.
- EXTENSION: artificial MemoryStore faults and owned process exits in new tests;
  unchanged CPU science regressions prove compatibility only.

`validation.json` contains command/exit/runtime/source and original raw-log SHA
receipts; `preservation.json` binds every original tracked file. Exact private
argv, machine identity, raw stdio, pre-assert cursor observations and initial
baseline failure are retained under `runs/task08-g20-20261011/`. cpu01 had28 tests
exit0; manual review then hardened malformed ACK normalization and consumer
payload type-sensitive equality, and added5 tests; cpu02 has33 tests exit0.
No original assertion was removed or weakened. Initial project-root Git128,
early receipt inspection before completion1 are tool-transcript-only;
raw logs NOT_CAPTURED for those probes, not acceptance tests. Historical
Two document patch-context errors have no process exit and are transcript-only.
Evidence verifier01 exits1 from an incorrect repository parent index; its source
and raw logs are preserved. Verifier02 fixes only that index and exits0, verifying
all commands/source/log hashes and2015 base files (2012 byte-identical,2 append-only,
1 permitted Reporter modification); runtime/tests are unchanged.
FAIL/NOT_CAPTURED,915-cache inventory gap and rights/privacy OPEN/DEFERRED remain.

Next unique task: independent review of this local TASK08 snapshot and evidence.
G20 **CPU_TRANSPORT_CONTRACT_PASS_ONLY**, broader G20 remains OPEN. No remote
push/PR/merge or task09; stop after this delivery.

## Authorized GitHub publication supplement / 2026-10-11
Human now authorizes GitHub push for independent ChatGPT review. The earlier
local-only statements remain historical. `review-logs.json` contains saved full
CPU stdout/stderr with project, home, interpreter/unique temporary paths redacted,
original and sanitized hashes, true exits and intentional crash assertions.
A separate publication snapshot directly parents exactPR18; original unpublished
commits/private logs are retained locally. Only documentation changes; actual
Reporter/outbox/test hashes match validation.json. No new GPU/Redis or CPU claims.
Publication branch codex/m6b-ready-g20-reporter-review, Draft base exactPR18 branch;
remote head/tree and PR identity are independently read back before delivery.

SSH443 preflight exit128: network closed before authentication reply; original
error retained privately. Publication uses the connected GitHub Git object API,
not a shell push; API commit metadata may differ, local/remote tree must match.
No host-key bypass/global configuration change/private key exposure.
