# M6-A boundaries and sources

Baseline: PR9 7746fccb88718a5567da0d042d2679672d4226fc /
2fc769bd39f96d58e7fb1ea261f984bf24380590. New branch codex/m6a-control-plane.
Original851 files must remain byte-exact except STATUS/GAPS append. No old failed
FLASH code, logs or trees accessed. No GreyHound source reused.

| Choice | Classification / exact authority |
|---|---|
| three-tier Redis topology; Monitor0/Profile1 | PAPER SPEC S1/S4, chapter3 pp23–24/27–29 |
| bounded500 iteration channel; ms | PAPER SPEC S2, chapter3 pp25–27 |
| max(ms/1000×2.2,20 seconds) | PAPER SPEC S4, chapter3 pp27–29 |
| request versus per-scope applied, no all-rank Header proof | ADAPTATION baseline `native/probe.cpp:apply_boundary`, `flash/reader.py:Reader.request`, `docs/m3/DESIGN.md` |
| EVAL atomic mutation; standalone one document | UPSTREAM official Redis EVAL docs; ADAPTATION revision CAS/quotas/lifecycle |
| generation fencing, ACK, hashes, timeout/reset protocol | ADAPTATION G07/G16/G20, new m6 modules |
| strict manifest/Group counts and unchanged provisional min-rank ordering | ADAPTATION baseline `flash/profile_input.py:validate_bundle`, `flash/localization.py:analyze`; PAPER SPEC S6 |
| logical nodes, manual trigger, virtual legal scopes, simulated fixture durations | EXTENSION; M4 synthetic fixtures declared before execution |
| 5s control/reset,60s receiver freshness, bounds | ADAPTATION engineering budgets, not scientific threshold choices |

Fixture source SHA256 is saved before use. Normal input is unchanged M4
three_groups_max_then_min; additional normal_equal, std_convention_disagreement
and nested_group_shared_members cover no candidate, ambiguity and correlated
Group records. Adaptation is copying and replacing run/epoch/node identifiers;
no duration/count/label adjustment or results-driven sample generation. Existing
synthetic cuda_results arrays are fixture evidence only, never actual CUDA calls.
Controllers receive communicator/sample manifest only; Probe receives input rows,
not evaluator, fault rank or expected outcome. Unit tests independently compare
against the existing M4 analyzer. Group sample counts come from M4, unchanged.

Python iteration transport accepts original validated IterationRecord fields.
Only explicitly known completion boundaries can drive profiling; M6-A exercises
CPU simulated completion only. Production framework callback, transfer ACK versus
GPU completion, restart persistence and actual Probe fencing are still G20 OPEN.
Unsupported streams/comm identities/epochs and insufficient samples fail strict
M4 validation; no fallback zero or dropped rank.

Control architecture is GlobalController↔Store(Redis or deterministic CAS mock)
↔LocalController↔CPU ProbeAdapter. Redis tests use actual GET/EVAL socket traffic
when possible; they still use virtual-clock samples and same-process logical
nodes. They do not validate distributed training, physical machines, native ABI
migration or GPU. Native regressions, if available, use existing CPU mock libraries
only, no rebuild and CUDA_VISIBLE_DEVICES empty. Existing approved M3 fixture is
read-only for unchanged validator regression; modifications occur in a new
private temporary copy. Formal environment identity is hashed before/after.

Not authorized: Rbeast auto trigger, library migration, GPU/NCCL training or faults,
M6-B, two-machine automatic loop, final fault alert, paper precision/recall.
G01/G02/G04/G09/G13/G20 remain OPEN regardless of engineering checks.

Superseding authorization: after initial missing-dependency BLOCKED results,
the user explicitly permitted real Redis installation for M6-A. UPSTREAM fixed
Redis8.10.2 commit498ecd0d6d007db11ddb3aea9428552598a78622 and redis-py8.1.0
source/function/URL/SHA/license are in dependency-lock.json. Redis core is built
unmodified with existing tools, make -C src -j2 redis-server redis-cli
MALLOC=libc BUILD_TLS=no OPTIMIZATION=-O2 (ADAPTATION private CPU build).
Choose upstream AGPLv3 option; redis-py MIT. No upstream binary/source is committed.
Python client lives in a new private .venv-m6; formal .venv-m5 remains unchanged.
Redis processes are owned temporary children with port0, socket0600, directory0700,
persistence disabled and disable-thp=no (no host THP adjustment). No system service.
redis-py8 Redis.__init__ omits socket_connect_timeout on Unix socket shortcut;
explicit ConnectionPool passes both finite deadlines to UnixDomainSocketConnection
and disables hidden retries. Strict RedisStore deadline validation is retained.
Only installation/replay dependencies were authorized; real GPU/scientific gates
and runtime migration remain unchanged. Installed dependencies are retained
privately for replay; temporary servers/sockets are released after every test.
