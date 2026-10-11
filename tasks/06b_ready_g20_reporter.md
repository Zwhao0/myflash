# TASK08 — G20 Reporter/outbox, CPU mock only

Authorization: human 2026-10-11 asks for durable outbox, ACK validation,
unknown-result retry, restart/recovery and consumer cursor consistency using
existing MemoryStore, from PR18 exact89cfdbb679b55aa8f81d39f39c72e77426976d85
/ tree5edc2add8eb963a2f03086f635c5ba8a1f658eba. Independent worktree
m6b-s8-work, branch codex/m6b-ready-g20-reporter-outbox. No inference of
independent PR18 review PASS; exact source is explicitly authorized by user.

Allowed: flash/iteration_reporter.py; new flash/iteration_outbox.py;
tests/m6b_ready_reporter_outbox.py; this task; docs/m6b-ready/g20-reporter/**;
STATUS.md/GAPS.md append only. Original Publisher/Reader/MemoryStore,
M6 controller/protocol, detector/locator, all existing tests/fixtures immutable.

PAPER SPEC S2 / G20 pp25,35: completed iteration records, time_ms,500 retention.
ADAPTATION: freeze completed record once; accept legacy None publishers but
require structured ACK status/boolean/hash for M6; unresolved end raises and
keeps active/pending; abort cannot discard completed unconfirmed record.
SQLite standard-library local outbox, explicit per-run/rank identity, durable
enqueue BEFORE read/publish, one pending record/backpressure,500 acknowledged
records retained. One bounded recovery attempt per caller invocation; read
first, exact retained-record match confirms, otherwise exact resubmit; conflict,
evicted unknown, missing run, corruption fail closed. No fabricated ACK.
Consumer poll never advances durable cursor; explicit commit of delivered exact
prefix advances atomically; restart can redeliver, application effects require
application idempotence. No exactly-once side-effect guarantee.
UPSTREAM: Python sqlite3 transaction API / SQLite journal/synchronous PRAGMAs
(official URLs in RESULT). Existing machine library/version measured, no install.
EXTENSION: artificial MemoryStore disconnect/lost ACK/duplicates/conflicts and
bounded self-exiting CPU subprocesses, not GPU or Redis network experiments.

Tests: first preserve baseline Reporter defect reproduction; new regression
and outbox crash/restart/cursor cases; unchanged Reporter4, cursor9+8, control32,
CPU detection8 and approved detector/localization13+20 regressions. Each command
120s timeout, only own child process group may be terminated; crash test children
self-exit at explicit transaction checkpoints,10s bound. No unrelated PID/GPU.
Full argv/cwd/host/version/exit/stdout/stderr/source hashes in private task run;
public command receipts and preservation evidence in task docs.

Exit: retain failures, never weaken assertions; stop on unresolved failure.
No real Redis/service/install/native compile/fit/GPU/server/bridge/M6-B/merge.
No remote publication requested in TASK08; deliver local reviewable snapshot.
Next unique task independent TASK08 implementation/evidence review; STOP.

2026-10-11 human explicitly approves GitHub publication for ChatGPT review.
Publish separate codex/m6b-ready-g20-reporter-review snapshot, parent exactPR18,
retain local unpublished commits/private receipts. Documentation-only redaction
and sanitized review logs allowed; runtime/tests fixed to prior acceptance SHA.
Draft base codex/m6b-ready-g3-g04-implementation must still equal exact89cfdbb.
Use existing GitHub identity SSH443, no force/main/previous PR mutation; STOP.
