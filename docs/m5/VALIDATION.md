# M5 validation and private evidence

Actual machine node-0 Linux x86_64/Python3.12.3; CPU Rbeast and2 approved H800 for
DDP. Local macOS/Python3.9 checks only validate standard-library modules/publication.
Complete real commands and raw logs stay in server `runs/`; public validation.json
contains exact exit codes and commands with identities replaced by placeholders.
M5 checkout itself is isolated under `runs/m5-work`, base9c66be49; original root/M1
venv remain unchanged. `runs/m5-access/setup.sh` is the complete actual dependency
setup command; install.log/pip-before.log/pip-after.log preserve installation/checks.

## Executed commands (cwd M5 checkout)

```sh
<project>/.venv-m5/bin/python tests/m5_reporter.py
<project>/.venv-m5/bin/python tests/m5_detection.py
<project>/.venv-m5/bin/python tests/m5_api_fields.py runs/m5-validation-02/api-fields
<project>/.venv-m5/bin/python scripts/m5_replay.py --input tests/m5_fixtures/records --output runs/m5-validation-02/replay
<project>/.venv-m5/bin/python tests/m5_causality.py runs/m5-validation-02/causality.json
<project>/.venv-m5/bin/python scripts/m5_evaluate.py --results runs/m5-validation-02/replay --truth tests/m5_fixtures/evaluator.json --output runs/m5-validation-02/metrics.json
python3 scripts/m3_cpu_suite.py
python3 tests/m3_validation.py
python3 tests/m4_offline.py --output runs/m5-validation-03/m4-fixtures
python3 scripts/m3_validate_public.py
```

M5 tests/field/replay/causality/evaluator0. M3 CPU suite first five checks0; sixth
private-fixture-dependent verifier1. Follow-up unchanged verifier0 after attaching
same project `runs/m3abc-local-01`; no fixture data/source/assertion edited. M4 fixtures
and M3 public evidence0. Individual CPU suite commands/exit/raw logs in its nested
m3-cpu manifest, retained in isolated checkout runs.

```sh
# three sequential runs, same2 approved UUIDs, no preload or fault injection
python3 scripts/m1_launch.py --python <project>/.venv-m5/bin/python --run-id m5-ddp-baseline-02 --gpus <approved-2-GPU-UUIDs> --mode ddp --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29970 --timeout 300 --allow-shared
python3 scripts/m5_launch.py --python <project>/.venv-m5/bin/python --run-id m5-ddp-off-02 --gpus <approved-2-GPU-UUIDs> --mode ddp --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29971 --timeout 300 --allow-shared
python3 scripts/m5_launch.py --python <project>/.venv-m5/bin/python --run-id m5-ddp-on-02 --gpus <approved-2-GPU-UUIDs> --mode ddp --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29972 --timeout 300 --allow-shared --reporter
<project>/.venv-m5/bin/python scripts/m5_verify_ddp.py --off runs/m5-ddp-off-02/node-0 --on runs/m5-ddp-on-02/node-0 --output runs/m5-validation-03/ddp.json
```

All4 exits0. Each `runs/m5-work/runs/m5-ddp-*-02/node-0` has full manifest/argv,
GPU/occupancy/preflight,torchrun/NCCL logs and per-rank numerical output; Reporter-on
adds local JSON histories. suite3.py independently compares original M1 Loss/delta.
The launcher preserves safety/own PGID cleanup, per-run commands/native library maps
and exit codes. No distributed Redis/Profile experiment claimed.

## Strict known failed commands (unchanged assertions)

```sh
<project>/.venv-m5/bin/python tests/m5_real_api.py runs/m5-validation-01/api
<project>/.venv-m5/bin/python tests/m5_real_api.py runs/m5-api-debug-01
<project>/.venv-m5/bin/python tests/m5_replay.py runs/m5-validation-02/replay
```

Each exits1 for exact native seeded output inequality; first logs in
runs/m5-work/runs/m5-validation-01/02.log, debug in runs/m5-access/api-debug-01.log/.exit,
last in runs/m5-access/exact-replay.log/.exit. Separate isolated repeat also false,
runs/m5-access/isolated-repeat.json. Inputs/seed/model fixed. Neither real input-causality
PASS nor field contract PASS overrides strict repeatability FAIL. Initial setup Git
bundle-ref and transport/download failures remain tool/server records, no fabricated
GPU result. First API failure lacked a structured raw dump; follow-up saves raw before
assertions, first console log kept unchanged.

## Public evidence boundary

replay/*.json contains full synthetic input prefixes/raw native fields/maps/filter
stages; ddp.json contains permitted small-workload numerical audit and rank0 replay.
api-raw.json and repeatability-failure.json contain statistical results only. No raw
training/NCCL logs, host identities, UUIDs, sensitive paths or complete private commands.
Exporter strips only duplicate serialized result envelope from native stdout; raw
fields are unchanged. Current existing privacy check and tests gate publication;
CI uses unchanged existing privacy workflow. Existing inherited PDF rights/history
warnings are unchanged, no new reference redistribution or history cleanup.

Source hashes, preserved-file equality, final local publication checks and GitHub
head/tree/CI receipt are in baseline-preservation.json, publication-validation.json
and private publication receipt. Stop at M5 review; no automatic M6.

Additional execution: `python3 runs/m5-access/postflight.py` exit0, log
runs/m5-access/postflight.log; own GPU PIDs0. Arithmetic/invalid-return evidence CLI
exit0, unit-evidence.json marked unit-only; 1ms native worker deadline correctly
returns INSUFFICIENT_EVIDENCE/NATIVE_TIMEOUT, native-timeout.json. These do not change
thresholds or establish successful native recovery. Early one-line postflight command
had a literal-newline syntax error and one local fixture creation used wrong cwd;
corrected standalone script paths, no GPU rerun or scientific change. Their tool
exit/error receipts are retained; initial redirected missing-script stderr was not
separately preserved before retry, so no complete raw-log claim for that ancillary error.
