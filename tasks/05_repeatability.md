# M5-R approved CPU investigation (2026-10-10)

Authorization: current user M5-R request; continue Draft PR6 at baa7638.
Allowed changes: this task, scripts/m5_repeatability.py,
scripts/m5_repeatability_report.py, docs/m5/repeatability/**,
append-only STATUS.md/GAPS.md. Root workspace STATUS is a private mirror.
Interfaces: diagnostic CLI only; no production adapter/default changes.
PAPER: existing thresholds and final_alert=false retained.
UPSTREAM: pinned Rbeast0.1.25 wheel/sdist, NumPy2.2.6, existing isolated runtime.
ADAPTATION: hash/full-output capture, bounded own subprocess, process-local affinity,
read-only exported-symbol inspection and independent RNG-buffer experiment.
EXTENSION: repeated existing synthetic fixtures; never GPU experiment evidence.

Predeclared matrix: reference exact tests/m5_real_api input, seed20261010,
same-process20 and fresh-process20, original affinity and fixed one CPU with
OMP/OPENBLAS/MKL/NUMEXPR threads1; three-chain and diagnostic one-chain;
supported cputype SSE/AVX2/AVX512 with actual dispatch verified.
Decision matrix: stable/sustained/growth_19/growth_20/growth_21/spike/recovery,
20 complete prefix replays each, original three-chain model in adapter subprocess
per native fit, one fixed allowed CPU/threads1. No evaluator truth supplied.
No result-dependent changes to seed/model/threshold/input selection.
Every fit preserves exact input float64 hash, full parameters, raw JSON and array
byte hashes (NaN bit patterns included), full candidate stages and differences.
Raw subprocess stdout/stderr and exact private argv/paths stay under new run_id.

Tests: unchanged m5_real_api/m5_replay assertions, M5 reporter/detection, existing
privacy tests/check and byte preservation of all pre-existing files except appended
STATUS/GAPS. Diagnostic command exit0 means completed measurement, not repeatability
PASS. Timeout per native call30s; overall CPU run3600s, stop only own process group.
No GPU/NCCL/Redis/control service, no dependency installation/native compilation.
If patch/rebuild/new dependency becomes necessary, deliver proposal and stop pending
approval. Finish with separate strict and decision conclusions; no M6.

Execution update: batch01 exposed three cpOccPr validation failures; its diagnostic
saved raw too late and lost those three trees. Keep source archive, all original
records, failed exporter fit-count assertion and missing-output status. Correct only
diagnostic capture order and rerun the whole identical matrix under batch02, with
the same20 repeats/seed/parameters/scenarios. No sample substitution or exclusion.
Export native rejection separately from valid-posterior probability flips. Keep
every original strict test and validation range unchanged.
