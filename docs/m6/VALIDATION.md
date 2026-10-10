# M6-A validation and evidence replay

See validation.json for each actual test's machine alias, full sanitized argv,
code SHA/per-file hash, exit, timeout, raw log path/hash and result. Private manifests
retain exact machine identity/absolute argv. Code acceptance final modules/tests
match committede3f6b4225db83ec97e0b59161fa4f46a14ab9f68 and latest_code_hashes.
Original M2–M5 code/fixtures/evidence match PR9. preservation.json includes all851
path hashes, source matches and pre/post native artifact hashes. STATUS/GAPS are
append-only. formal1424 non-cache files were hashed and asserted equal across
server validation, installation and final actual integration; no detector fits or formal environment writes apart from excluded
interpreter caches. Original scientific native strict tests remain unchanged and
NOT_RUN this control-only milestone.

CPU commands, from checkout with an existing compatible interpreter:

```sh
python3 tests/m6_control.py
python3 scripts/m6_demo.py --output runs/m6a-new-demo
python3 tests/m6_redis.py
python3 scripts/m6_validate.py --output runs/m6a-new-validation
```

Each output directory must be new. The Redis CLI returns3/BLOCKED if either
redis-server or redis-py is missing, never skip/PASS. After explicit human
installation authorization, node-0 uses the private fixed dependency build and
separate .venv-m6 (dependency-lock.json/installation.json). The final actual
Redis command is `<private-client-python> tests/m6_redis.py`, with PATH prefixed
by `<private-redis-src>`; exact absolute argv is in the private manifest.
`--redis-python <private-client-python>` selects that interpreter only for the
Redis test when running m6_validate; all original CPU regressions retain the
formal interpreter. The binary is built with existing tools:

```sh
make -C <fixed-source>/src -j2 redis-server redis-cli MALLOC=libc BUILD_TLS=no OPTIMIZATION=-O2
python3 -m venv <private-deps>/.venv-m6
<private-deps>/.venv-m6/bin/python -m pip install --no-index --no-deps <fixed-wheel>
```

Archive and wheel SHA256 are checked before unpack/install. No system packages,
services, FLASH native rebuild or formal environment migration. Actual Redis
runs socket-only (port0), directory0700/socket0600, no persistence and
`--disable-thp no`. The client explicitly configures pool read/connect deadlines
and no hidden retries. Six actual tests PASS in server-relevant-05; transport.json
records loaded Redis8.10.2/client8.1.0, actual command and CPU/virtual-clock markers.
Server stop/restart changes run_id, drops the old nonpersistent document and
blocks old-store reads/writes and active-run resume. A fresh run alone completes.
This proves the exercised local socket transport; delayed replies and lost-response
branches remain deterministic mock evidence, not measured network impairments.
No disk durability, HA or cross-host recovery claim. Four owned server starts
all finish exit0, exact keys/sockets released and logs retained. postflight.json
confirms zero owned server PIDs/sockets; dependencies are retained privately.
postflight-before-install.json preserves the earlier no-instance receipt.

Compatible native CPU regression invocation also supplies existing
`--native-artifacts`, `--approved-project`, `--formal-environment`; exact values
are private. These create ignored read-only references to existing approved test
libraries/fixture, not a native build. `CUDA_VISIBLE_DEVICES` is empty and inherited
LD_PRELOAD is removed in child test environment. Children start their own process
group; test120s, M4 180s and full text privacy600s limits terminate only that group.
All completed test children are recorded finished; original native fixture tests
perform their exact owned shm cleanup and temporary copies are removed. Public
postflight receipt records final references/process release; unrelated resources
and old raw files remain untouched.

| Required abnormal case | CPU evidence |
|---|---|
| duplicate request/ACK, conflicting iteration | exact retained value/hash comparison; one effective iteration, no overwritten value |
| Redis delay/disconnect/lost response | deterministic Unavailable-before/after-commit; unconfirmed receipt and exact retry; actual socket disconnect/reconnect and server restart PASS; synthetic delay/lost-response only |
| local/global restart and old owner | incremented generations, retained failure, STALE receipt, reissued reset |
| ACK without applied/scope missing/rank or node missing | stays requested/arming then TIMEOUT, no analysis |
| missing/duplicate/corrupt/unsupported Profile | INCOMPLETE; M4 strict count/identity/unit/Group validator unchanged |
| run/epoch pollution and between-round leftovers | no prior samples pooled; missing next-epoch data fails |
| partly Monitor ranks and reset restart | no complete reset claim; BLOCKED or new current-fence scope proofs |
| drain timeout versus no candidate | TIMEOUT preserved; equal complete fixture alone gives NO_CANDIDATE |
| ambiguous locator | complete unchanged std-convention fixture returns AMBIGUOUS_SPEC, still resets |
| no/freshness-expired/unknown-boundary iteration | insufficient/TIMEOUT; no zero or inferred CUDA completion |
| initial invalid transport deadlines | rejected before the first network operation, including None/zero/negative/NaN/inf/bool |
| Group shared duration | independent scope count remains less than member record count |

Sources are fixed M4 inputs with original hashes (fixture-index.json), not
results-derived generated timings. No expected.json/evaluator/fault label enters
controller/Probe input. CPU scope evidence contains explicit source marker and
virtual time domain. Upstream semantic references are linked in CONTROL_PROTOCOL;
loaded Redis/client versions and build/license hashes are recorded, not inferred.

Limitations: one Redis single document, bounded CAS, no disk durability/HA/cluster;
external Probe effects are outside Redis transaction and CPU adapter checks fences
at boundaries. Real shared-memory ABI fencing, cross-host clocks, GPU timing,
real process kill/restart, training completion/ACK/recovery and all six scientific
GAPS remain unapproved. Lost/blocked state needs exact operator reconciliation and
a new run where necessary; no cleanup routine can prove ranks actually applied.
