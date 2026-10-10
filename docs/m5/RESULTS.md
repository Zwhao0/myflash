# M5 results (2026-10-10)

M5 implementation and finite experiments delivered. Reporter/real API field contract/
processing/input causality/DDP numerical checks passed. Strict seeded output
repeatability FAILED. Scientific final detection remains AMBIGUOUS_SPEC; no complete
FLASH detection PASS and no M6 progression.

## Actual acceptance

| Requirement | Result | Evidence |
|---|---|---|
| Reporter completed iteration/retention/reload | PASS | four standard-library tests, 2 ranks×20 real DDP records; no missing/duplicate; ddp.json |
| Rbeast real environment | RUN/PASS compatibility | node-0 CPU, Python3.12.3, Rbeast0.1.25/NumPy2.2.6; approved isolated environment, hash-locked wheel closure2; M1 still has neither package |
| Actual cp/probability fields | PASS API contract | api-fields.json/api-raw.json; step cp16→index15, start101 gives cp116; cpPr localized occurrence versus cpOccPr per-time; neither run-length posterior |
| Sliding window/preprocessing/filter evidence | PASS implementation | paper constants, original mappings, full raw outputs/stages; 8 unit tests; only statistical facts/provisional assumptions |
| Prefix replay no future input | PASS input audit | real native inputs of full run and prefix24 identical; 35 and14 native calls; causality.json. No equality claim for stochastic outputs |
| Exact repeated output/prefix output equality | FAIL | repeatability-failure.json and unchanged tests/m5_real_api.py / tests/m5_replay.py; seed does not reproduce exact output on this wheel |
| Real small load/numerical regression | PASS | original M1 baseline plus independent Reporter off/on:3 launches×2H800×20steps, all launch/verify0; identical Loss/parameter delta; off/on all gradients and final parameters equal |
| M1–M4 preservation/regression | PASS checked scope | all existing source/results except append-only GAPS/STATUS byte-preserved; original M1 run, M2/M3 CPU checks, M3 private-fixture verifier, 65 M4 fixtures and public M3 evidence checks |
| Full FLASH alert accuracy/Redis/Profile closure | NOT_RUN | no final alert, fault injection, distributed service or automatic control |

## CPU fixed-input candidate observations

26 scenarios, 791 prefix decisions:560 actual native window fits,224 insufficient
(e.g. warmup/short/constant),7 invalid-input decisions. Inputs are fixed synthetic
iteration durations, not GPU faults. The seed/model/thresholds were not tuned after
seeing output. Complete inputs/raw native fields/maps/stages are in replay/*.json;
NaN padding is null, duplicate M5_RESULT transport envelope removed from stdout with
all structured raw values retained. Original full envelopes remain server-side.

Primary-event matching tolerance ±2 original iterations is an EXTENSION, not paper
accuracy. Decision delay = first matched candidate decision minus event iteration;
no wall-time/end-to-end detection latency. Columns for duration/throughput are
unapproved formula interpretations and never actual alerts.

| Scenario | First probability candidate | Probability delay | Duration-growth provisional delay | Throughput-loss provisional delay |
|---|---:|---:|---:|---:|
| stable | none | n/a | n/a | n/a |
| single spike | none | missed change candidate | none | none |
| sustained35ms rise, onset21 | 22 | 1 | 1 | 1 |
| rise21/recovery28 | 22 | 1 | 1 | 1 |
| multiple changes, primary16 | 17 | 1 | 1 | 1 |
| adjacent changes, primary21 | 22 | 1 | 2 | 2 |
| early window-edge change6 | 11 | 5 | 5 | 5 |
| growth19%, onset21 | 22 | 1 | missed | missed |
| growth20%, onset21 | 22 | 1 | 2 | missed |
| growth21%, onset21 | 22 | 1 | 1 | missed |
| growth24%, onset21 | 22 | 1 | 1 | missed |
| growth25%, onset21 | 22 | 1 | 1 | 2 |
| growth26%, onset21 | 22 | 1 | 1 | 1 |

The low-amplitude deterministic noise means a nominal20% fixture can exceed exactly
0.2 for some mean slices; input values are preserved, no threshold/labels adjusted.
Stable45 iterations observed0 probability-qualified candidates; warmup/outlier/
latest-endpoint scenes likewise0 in this replay. This does not establish false-alarm
rate. metrics.json `pseudo_candidate_decisions` outside primary-onset tolerance also
includes genuine recovery/secondary changes (e.g. recovery18); interpret as unmatched
primary-event candidates, never as18 false alarms. The single-spike miss concerns a
structural candidate; filtering a transient spike is not FLASH false-negative proof.

## Real PyTorch DDP smoke

node-0,2 approved H800; native NCCL2.27.3/CUDA12.8, Torch2.8.0+cu128, same676-parameter
M1 model/data seeds. All3 launches and verification exit0; all process groups destroyed
and own process-group leftovers0. Reporter enabled records exactly1..20 per rank;
rank0 records reload through the real adapter. Actual per-rank GPU process memory
1000MiB, below2048MiB end guard; allocator1% cap, preflight3072MiB free, total300s limit.
No clocks, OOM, network disturbance or other-job termination. Resident data has no
loader; timing explicitly includes CUDA completion and test finite/gradient audit
work. It does not attribute compute/communication shares or reproduce Megatron timing.

rank0 recorded1.65283–192.362437ms; rank1 1.619057–202.374021ms. First-step warmup and
natural variance are retained; rank0 replay produced0 probability-qualified candidates.
No performance-overhead inference from these single paired runs. Full commands,
UUIDs/PIDs/version library paths and training/NCCL logs remain server runs only.

## Failure preservation and remaining gates

Same-process and isolated seeded fits vary in native posterior arrays. Read-only
same-version source audit suggests an AVX512 union-state seed defect, unconfirmed
as actual wheel cause. No library rebuild/patch/upgrade/replacement; exact assertions
remain and exact prefix-output test exits1. M5 reproducible-native-output acceptance
is BLOCKED pending reviewed upstream remedy; fixed-input replay ran and all failures
are published separately.

M3 CPU verifier first failed because the isolated clone lacked its private verified
fixture. With only that same-project immutable run attached read-only, the unchanged
verifier passed. Export identity gate first rejected absolute source-hash dictionary
keys; these were replaced by relative names, hashes/numbers unchanged. Original logs
and failures remain server-side. No assertions or parameters weakened.

G01/G02/G13/G20 all OPEN. G20's declared small DDP callback boundary is functional,
while general-framework/transport semantics remain open. G01 includes probability,
model/index policies and strict reproducibility; G02 persistence>20 versus1–2; G13
20% denominator and injected-strength meaning. M6 needs approved final rule, Redis
queue/idempotent ACK/restart, profile_epoch/status propagation/node ACKs, complete
bounded sampling, rearm/debounce and failure paths. None is exercised here.
