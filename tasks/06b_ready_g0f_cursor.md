# M6B-READY-G0F / task 01: future iteration cursor

Human authorization: user requests task01 from FLASH_M6B_READY_Codex_Tasks.
Exact baseline PR11:70a83e7dfc3f705420464e0eb4dc0cb1807bac4e,
tree43a4688efb720156b62defdce2b7e6c155a22763; verified clean locally,
remote branches match declared PR10/main and PR11 is Draft/open/unmerged.
New branch codex/m6b-ready-g0f-cursor; Draft base codex/m6b-ready-g0-evidence.

Allowed: flash/m6_iteration.py; new tests/m6b_ready_cursor_extra.py,
this task, docs/m6b-ready/g0f-cursor/**; STATUS/GAPS append only.
Original red test, fixtures, other flash modules and historical evidence immutable.
Private collector, command/log/manifest and Git receipts stay in ignored runs/.

ADAPTATION: IterationReader.read validates a non-None cursor with existing
iteration_reporter.integer(value,0,'after_iteration') before store access.
That helper requires type(value) is int, excluding bool and int subclasses.
Only after original record/hash/sequence/retention validation, a cursor greater
than stream.last returns INSUFFICIENT_EVIDENCE with an auditable reason.
None reads the current window; legal retained_from-1 and last return the entire
retained window, without slicing. Original gap/missing/empty/expiry/hash rules
remain. PAPER SPEC S2 only defines500-item retention; this contract is engineering.
No GreyHound reuse, external dependency or scientific algorithm change.

EXTENSION tests: unchanged nine red-contract tests now green; new eight boundary
tests for validation before reads (including missing/offline runs), None/full500,
last+1/huge future/no mutation, retained earliest neighbor, corrupted hash/order,
and unconfirmed commit reply/read/exact resubmission. Existing tests/m6_control.py
(32), tests/m5_reporter.py, tests/m5_detection.py, tests/m5_s1_offline.py run with
their unchanged CPU argv, locked by existing scripts/m6_validate.py.

Machine: node-0, existing formal Python3.12.3 only. No new environment/install,
Redis/service/native fit/build/GPU/NCCL/node-1 activity. Each test bounded120s,
own subprocess group waited; timeout cleanup only owned group. Clear LD_PRELOAD,
CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE=1. New private output directory.
Formal1424 non-cache files and original.so must match before/after and historical
SHA a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157.
Whole baseline tree hashes protect other modules/fixtures/history, STATUS/GAPS
checked as byte prefixes. Retain any failing attempt; never weaken assertions.

Deliver RESULT, validation, source/approval ledger, preservation, postflight,
failed-attempt index, complete sanitized logs and old-red immutable hashes.
Normal publication CI retained with actual checkout/head/tree distinction;
historical privacy/PID/copyright audit DEFERRED/OPEN as user task package directs.
Only cursor engineering contract may PASS. Science G01/G02/G04/G13 and M6-B
remain not approved. Stop after independent Draft PR; next unique task is
independent review of this exact head/evidence, not task02 execution.
