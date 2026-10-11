# M6B-READY-G0F task01: cursor engineering contract PASS

node-0 existing Python3.12.3, execution97a639979689a82974c129827f018fd4fe2b872b /
treed1787e5fe0f095d91f69e4ab8ab6348d840ccdcd, clean. Exact baseline PR11
70a83e7dfc3f705420464e0eb4dc0cb1807bac4e; independent Draft base
codex/m6b-ready-g0-evidence. Final publication head/tree/CI are recorded in the
private publication receipt after push; execution source hashes remain binding.

ADAPTATION: non-None after_iteration must be a builtin int >=0, checked with the
existing strict integer helper before any store access. Invalid bool/float/string/
NaN/Inf/negative/int-subclass values raise ValueError. After original hash, identity,
sequence and retention validation, a valid cursor above stream.last returns
INSUFFICIENT_EVIDENCE with reason `consumer cursor ahead of last confirmed iteration`.
None, retained_from-1 and last still return the full retained window. No slicing,
invented iteration, waiting loop or scientific mechanism change. PAPER SPEC S2 only
specifies500 retained items; this cursor contract is an engineering adaptation.

| Unchanged test entry / new boundary entry | Tests completed | Actual exit | Timeout |
|---|---:|---:|---|
| tests/m6b_ready_cursor_contract.py --output <private-run>/validation-01/cursor |9|0|false|
| tests/m6b_ready_cursor_extra.py |8|0|false|
| tests/m6_control.py |32|0|false|
| tests/m5_reporter.py |4|0|false|
| tests/m5_detection.py |8|0|false|
| tests/m5_s1_offline.py |16|0|false|

77 tests, six children individually waited, no skips/expected failures. Actual
collector child exit0 is captured by its waiting supervisor; launch is not counted
as completion. Full argv/cwd/environment/source hashes, stdout/stderr/original and
sanitized SHA are in validation.json and EVIDENCE_INDEX.json. Complete per-case
cursor observations and control states are in evidence/validation-01. New tests
cover validation before reads across empty/populated/missing/offline runs, None,
exact500 window boundaries, last+1 and huge integers, retained earliest neighbor,
corruption precedence and unconfirmed commit reply followed by read/exact retry.

All1394 baseline files protected: only flash/m6_iteration.py changes existing
source; STATUS/GAPS are appended at delivery. Other flash modules, all old tests,
fixtures and515 original G0-E evidence files are byte preserved. The old red test
SHAfca99d078fb4ac5c1a9dc99ba3fa0293961969617e4e684f4eeafd7a4994c6cf,
raw23-file failure directory and9-failure/exit1 history are retained; ORIGINAL_RED.json
binds raw/public hashes. Formal1424 non-cache files match historical inventory and
pre/post; original Rbeast.so remains
a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157.
Original server checkout e3f6b422 remains clean/unchanged; no service was created,
all owned test children waited, own run sockets0.

Initial checkout setup exit128 and subsequent absent-driver probe exit1 are kept
in failures.json and raw private runs; tests did not start on either failure.
The second setup fetched the known e3f6b422 snapshot and exact later Git objects,
then verified the full baseline and protected bytes. No assertion was weakened.

No Redis, native fit/build/install, GPU/NCCL, node-1, formal caller adoption or M6-B.
G01/G02/G04/G13 science remains not approved; M6B-READY as a whole remains BLOCKED.
Historical privacy/PID/binary rights audit DEFERRED/OPEN under current task package;
normal publication CI is limited to its actual text rules, not science or history.
Next unique task: independent ChatGPT review of the new Draft PR exact head,
implementation and evidence. Stop here; task02 is not authorized by this completion.

Publication preparation on local-macOS existing Python3.9.6: ordinary Git diff
check0; unchanged six privacy unit tests0; changed110-path text/path scope
check0/findings0 before these receipts were exported. Execution-to-delivery
flash/tests/scripts hashes match exactly. Public publication-check-01 binds
complete command/log hashes. Final new receipt bytes receive an additional
changed-path scan; normal GitHub full-tree CI is observed after publication.
No historical privacy/rights audit was performed.

Publication transport attempts are retained: local HTTPS push128 (no configured
write authentication), default SSH read128 (host key verification), SSH443 read128
(no local public-key authorization). No host-key bypass, credential provisioning
or history rewrite was performed. The node-0 SSH prepush read also stopped128 on host-key verification, retained
privately. An existing local GitHub-specific identity was explicitly selected
and its read authorization verified0. This existing identity is used for ordinary
Git push without changing system SSH configuration; final outcome is in the
private publication receipt and Draft PR metadata. No private-key contents were
read or disclosed. These transport failures do not change CPU results.

Initial server publication helper exited1 with template SyntaxError before any
execution or writes. Full private error retained; saved helper was corrected
and locally parsed before retry. Runtime source/tests and original evidence
were unaffected.
