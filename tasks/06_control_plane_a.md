# M6-A approved CPU control plane (2026-10-10)
User authorizes phases A–E continuously, independent Draft PR then stop.
Baseline PR9 7746fccb88718a5567da0d042d2679672d4226fc /
2fc769bd39f96d58e7fb1ea261f984bf24380590; clean verified locally and GitHub.
Branch codex/m6a-control-plane; base codex/m5-s1-science-audit.

Allowed: flash/m6_protocol.py, flash/m6_store.py, flash/m6_iteration.py,
flash/m6_probe.py, flash/m6_controller.py, scripts/m6_validate.py,
scripts/m6_demo.py, tests/m6_control.py, tests/m6_redis.py, docs/m6/**,
this task; STATUS/GAPS append only. Private receipts/scripts under ignored runs/.
No other tracked paths needed. Original 851 files preserved; no old failed FLASH
implementation is opened or searched. Native Probe, ABI, algorithms, thresholds,
Rbeast, fixture bytes, historical evidence and formal environment remain unchanged.

Interfaces: versioned JSON documents, atomic revision CAS, generation-fenced
controller ownership, IterationRecord publisher/reader, CPU-only ProbeAdapter
request and per-rank scope evidence, polling Local/Global controllers.
PAPER SPEC S1/S2/S4: topology, Monitor/Profile, 500 records and window seconds.
UPSTREAM Redis official EVAL/LTRIM semantics (links in protocol).
ADAPTATION: run/epoch isolation, bounded evidence, fencing, acceptance/application
separation, deadlines/reset, loss/restart fail closed. EXTENSION: logical nodes,
virtual-clock scopes and unchanged M4 synthetic fixture replay with original SHA.
No automatic detector is imported. G01/G02/G04/G09/G13/G20 remain OPEN.

Predeclared input: tests/m4_cases/three_groups_max_then_min/input.json for normal
loop; normal_equal, std_convention_disagreement and Group fixtures for edge cases.
Map ranks alternating node-0/node-1, rewrite only run/epoch/node identifiers in a
new in-memory copy. Preserve timing/count/communicator fields and source SHA;
never use expected.json/evaluator in controllers or Probe. No generated GPU data.

Tests: deterministic window, command/ACK/application, 2 epochs, duplicate/conflict,
missing node/rank/scope/data, corruption, stale run/epoch, unsupported data,
partial reset, controller restart/fencing, timeout, disconnect/retry and AMBIGUOUS.
Redis actual test only if existing server/client available; isolated private socket,
port 0, owned process, bounded child timeout; no dependency installation or flush.
CPU regressions M4 fixtures/M5 Reporter/detection/contract/privacy; native M2/M3
only if existing toolchain artifacts are compatible, otherwise NOT_RUN/BLOCKED.
Per test max 120s, M4 180s; terminate only spawned children. Redis run dir mode0700,
socket0600; terminate only Popen child, retain logs/failed artifacts, never global
cleanup. Absence of Redis => real integration BLOCKED and overall conditional.

Deliver docs protocol/state/schema/boundaries/results/validation, input/source
hashes and full private command/exit/log receipt with sanitized public index.
Run privacy and baseline byte preservation checks, ordinary push and Draft PR.
No merge, visibility change, GPU/NCCL job or M6-B. final_fault_ranks=[] always.
Next unique task: independent ChatGPT GitHub technical review of M6-A.

Regression resource scope (declared before use): ignored build/ symlink to the
already existing, approved project CPU test artifacts; ignored runs/m3abc-local-01
read-only reference to the verified M3 fixture for its unchanged validator test.
No native rebuild/install or old experiment file mutation. Verify native source
hashes versus PR9 and artifact hashes before/after. Only CPU mocks run, with
CUDA_VISIBLE_DEVICES empty; native child processes have bounded own-group timeout.
Formal .venv-m5 is used only for standard-library/parser unit regressions and
read-only identity/hash audit. No Rbeast fit or package changes.
