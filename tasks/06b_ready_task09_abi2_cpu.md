# TASK09 — M3 ABI2 与 M6 控制面 CPU 桥接

Human authorization 2026-10-11: this task starts ONLY from PR19 exact
b082d16939aab0d4ba4b9208475886c4b9ec808c / tree10188bb80a4b9a10dff46c6eac5bb425fe3828ad.
No independent review PASS is inferred. PR19 remains Draft/unmerged.
Branch codex/task09-m3-abi2-m6-cpu; separate checkout m6b-s9-work.

Allowed new flash/m6_abi2_bridge.py, tests/task09_abi2_cpu.py, this task,
docs/m6b-ready/task09-abi2-cpu/**; STATUS/GAPS append only. All existing
source/tests/fixtures/native ABI/scientific parameters immutable.

PAPER SPEC S1/S4/S5, pp23–24/27–35: 0/1, CUDA Event units, Group shared
scopes, communicator identity. ADAPTATION: explicit opt-in strict ACK wrapper,
Reader request/read(false)/ack/snapshot interface, exact control word and fresh
post-request record evidence, generation fencing, complete Profile validation,
verified Monitor reset. Same-project source ledger bound to exact base:
reader.Reader; native/ring.cpp request/boundary/snapshot/flash_ring_read;
profile_input.read_records/validate_bundle; m6_controller Global/LocalController;
localization.analyze_approved_g04; iteration_reporter.confirmed_receipt.
No GreyHound/third-party code reuse. EXTENSION: injected CPU Reader mock only;
mock timing is artificial, not measured CUDA/GPU/native ABI execution.

Strict ACK selection: None/malformed/unknown/wrong digest rejected by explicit
wrapper; legacy Reporter unchanged. Command accepted ACK is NOT application.
ABI2 header alone is NOT fresh per-rank proof: require matching state/epoch
raw record after request baseline. A bridge cannot manufacture missing GPU
completion/scope evidence. Same-host CPU receive clock only; actual cross-host
clock/window mapping and durable raw persistence remain OPEN.

Tests: two complete epochs, hash/ACK/epoch/source/scope/window fences, Group
scope counts, missing rank/node/communicator/scopes, CUDA/NCCL errors, bad units,
duplicate/conflict, poisoned/closed/loss counters, bounded drain, read/ack/request
errors, restart/disconnect, partial reset and timeout, retained strict Reporter
pending. Run original targeted CPU control32/Reporter/outbox/cursor/detector/
approved localizer regressions. No full G04/M5 native matrix, M2b/M3 repetition.
Each command <=120s; own spawned process group timeout only; preserve failures.

Private runs/task09-abi2-cpu-20261011 receipts: exact argv/cwd/host/version,
exit/stdout/stderr/hash. New documentation records source and preservation hashes.
Exit after local reviewable CPU result; no publish authorization inferred,
no native compile/server/Redis service/GPU/fault injection/M6-B/merge/task10.

Read-only source finding: native/probe.cpp control is thread_local. TASK09
therefore REQUIRES explicit scope_threads={rank: thread_id}, exactly one thread
per declared rank, persisted with pid/created_ns and hash in run registration.
Unexpected current-command threads or changed scope declarations fail closed.
Multi-thread/application-wide timer teardown is NOT_VERIFIED. Group lineage
must have current outer GroupStart/End; unfinished groups cannot be ready.
Drain-ready records carry exact per-rank read/write snapshots and clean counters.
