# M6-A engineering results

**M6-A ENGINEERING PASS.** CPU mock, actual isolated Redis transport and
compatible M2–M5 CPU regressions pass. This does not establish M6 overall PASS,
automatic detection/localization science, GPU/cross-machine behavior, precision/
recall reproduction or a usable final fault alert. `final_alert=false`,
`final_fault_ranks=[]`; G01/G02/G04/G09/G13/G20 remain OPEN.

Implementation: independent versioned control plane, atomic revision CAS, global/
local fencing, original IterationRecord transport and500 retention, command ACK
separate from actual per-rank scope proof, strict20s minimum sampling, current-epoch
sample/hash integrity, existing M4 provisional analysis and verified Monitor reset.
Only MANUAL_TEST_TRIGGER; no automatic detector import. Sources/classifications in
CONTROL_PROTOCOL and INTEGRATION_BOUNDARIES; no GreyHound source reused.

| Acceptance area | Result | Evidence |
|---|---|---|
| protocol/state machine | CPU PASS | final32 deterministic tests + exact successful state trace |
| actual Redis | PASS on node-0 | Redis8.10.2/client8.1.0; six actual GET/EVAL/socket cases exit0, including owned server stop/restart/lost document |
| idempotence/epoch isolation | CPU PASS | exact duplicate request/iteration, conflict rejection, old epoch ignored, missing current data rejected |
| ACK versus rank application | CPU PASS | ACK-only/missing node/missing rank cannot arm; future or absent scope cannot prove applied |
| completeness/failure closure | CPU PASS | corruption/run/epoch/unit/unsupported timing/comm/duplicate origin/incomplete samples fail; TIMEOUT distinct from NO_CANDIDATE |
| reset and consecutive epochs | CPU PASS | epochs1/2 both provisional and Monitor verified; partial reset blocks next round; restart needs fresh fenced boundaries |
| unchanged M2–M5 CPU compatibility | PASS on node-0 | M2 ring+hook, M3 reader+hook+validator, M4 65fixtures; M5 Reporter4/detection8/contract/P1 units/S1 offline16/privacy6 exit0 |
| privacy/history preservation | PASS current text scope | original851 files unchanged except STATUS/GAPS append; full text scan and hash receipts; binary PDF rights remain existing limitation |

Normal loop uses predeclared existing M4 synthetic fixture
three_groups_max_then_min. Input source SHA is in fixture-index.json. Only copied
run/epoch/node IDs change, durations/count/labels unchanged. Two logical nodes,
three ranks each, independent epochs1/2, duration20.0 virtual seconds each,
PROVISIONAL_CANDIDATE agrees with unchanged M4. No injected truth or target rank is
read by Global/Local/Probe. Additional unchanged synthetic fixtures verify
NO_CANDIDATE, AMBIGUOUS_SPEC and Group shared-scope counts. Virtual seconds do not
measure elapsed collection time or overhead. There are no new real GPU samples.

Actual machines: local macOS arm64/Python3.9.6; approved node-0 Linux x86_64,
Intel Xeon Platinum8463B/Python3.12.3, existing formal Rbeast0.1.25/NumPy2.2.6.
No Rbeast fit, formal runtime migration, GPU/NCCL workload, fault injection or
second physical node run. After explicit installation authorization, a private
Redis core build and separate client venv were installed using existing tools.
Source commit/URL/SHA/license and actual install command/exit/log are in
dependency-lock.json and installation.json. Four owned Redis process starts
(including one failed test attempt and a stop/restart pair) all exit0; socket0600,
port0, no persistence, no host THP adjustment or system service change. Installed
dependencies remain private for replay. Native FLASH tests use
existing CPU mock artifacts; source matches PR9, before/after hashes match.
Formal1424 non-cache files hash identically before/after. Read-only links to
approved existing artifacts/M3 fixture are used only by unchanged regressions.

Retained attempts:

- local-validation-01: M6/M4/Reporter/detection/contract/privacy pass; two old
  NumPy-dependent entries fail missing NumPy; S1 exact arithmetic fails under
  Python3.9 (four errors); Redis exit3. No original assertion changes.
- server-validation-01: M6/M4/Reporter/detection/contract/P1/S1/privacy unit pass;
  API-field entry lacks mandatory output argv (IndexError before any fit),
  mistaken M2 lifecycle entry exits2 at argparse before torch/GPU, full privacy
  reaches120s protection (exit124). Native sequence stops at that error. All raw
  failed/partial receipts kept. These are invalid CPU registry/command-budget
  selections, not evidence that a GPU or fit ran.
- server-validation-02: corrected CPU registry; actual child exits
  `0,0,3,0,0,0,0,0,0,0,0`, five native CPU exits all0. Scanner gets separate600s
  budget for >700MiB historical byte evidence; scientific sample window remains20s.
- server-relevant-03: final controller code3cc3e9b,32 tests0, two-epoch demo0,
  Redis3; actual wrapper exit3 captured. Its source snapshot was hash verified;
  current executable acceptance is server-relevant-05. Prior driver launches were detached and their parent exit statuses
  were not captured; completed manifests contain independently waited actual
  test child exit codes. Launch receipts are never represented as completed tests.
- server-validation-04: newly installed real Redis failed six test setups before
  registration: redis-py8's Unix socket shortcut omitted the explicitly requested
  connect timeout from pool kwargs; strict RedisStore correctly rejected it.
  Retained FAIL driver1/Redis1. All ten other CPU commands and five native tests0;
  formal/native bytes unchanged. Explicit ConnectionPool now passes both finite
  deadlines, with no hidden retry; strict adapter checks remain unchanged.
- server-relevant-05: final executable codee3f6b4225db83ec97e0b59161fa4f46a14ab9f68;
  32 deterministic tests0, demo0, six actual Redis tests0, waited driver0. Actual
  Redis covers two epochs/all-rank reset, concurrent exact dedup/conflict/500
  retention, ACK-only timeout/partial reset, controller restart/fencing/old epoch,
  real socket disconnect/reconnect and actual owned server stop/restart/data loss.
  Old server owners and active-run resume fail closed; a new run completes.
  Exact current executable file hashes match this execution.
- actual postflight PASS: owned Redis PIDs0/sockets0, all child exits0, formal1424
  unchanged, original Rbeast native SHAa7432000… unchanged, read-only validation
  links released. An initial private postflight helper passed a Path to a bytes
  hash helper and exited1; no acceptance receipt was produced. The corrected
  rerun exits0, retains the error log and verifies the already released links.
- final publication privacy: first scan prints TEXT_CHECK PASS but private wrapper
  exits1 on relative-path receipt formatting; child exit was NOT_CAPTURED and
  excluded. Raw log retained. Corrected absolute-path invocation exits0 (164.68s),
  TEXT_CHECK PASS/files876/findings0. Publication metadata additions receive
  a further exact changed-file text check; CI is checked on the published head.
- early development syntax error exit1 retained; early uncommitted source
  snapshots not captured and excluded from acceptance. Latest committed-code
  acceptance is independently bound by exact per-file hashes.

Private raw stdout/stderr, exact machine/argv, state documents and manifests remain
under runs/. data-index.json provides relative path/SHA/byte index; validation.json
has sanitized command/exit/log/hash receipts. Original raw archive bytes are kept.
STATUS/GAPS receive appended records only. No failed case/old evidence is deleted.
Initial Redis absence BLOCKED records and earlier FAIL attempts remain historical;
the authorized actual run supersedes the earlier overall BLOCKED conclusion.
Publication final head/tree/CI is bound in Draft PR and private publication receipt;
privacy CI validates publication text, not Redis/science/GPU.

Next unique task: independent ChatGPT GitHub technical review of M6-A. No M6-B,
merge, runtime adoption or real GPU job is authorized by this delivery.
