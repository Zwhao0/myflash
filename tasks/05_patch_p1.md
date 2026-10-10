# M5-P1 isolated one-line AVX512 repair (2026-10-10)

Authorization: owner message “执行这个任务书”, referring to
FLASH_M5_P1_ISOLATED_PATCH_TASK_DRAFT.md. This approves its bounded node-0 CPU
build/install/test scope, not formal runtime adoption, M6 or merge.
Baseline: PR7 ed954f5a289e2a9f3c585f7f5af3792d0fde0c8d,
tree 36d19267fbbbaa12cacbaaac42bd3a56e4cac68b;
main ca6923d58d1fd5b2a0f899176780b17d6bd7e364 verified before work.

Allowed: this task, scripts/m5_p1_*.py, tests/m5_p1_*.py and standalone ABI
helper, docs/m5/patch-p1/**, append-only STATUS/GAPS. Original flash/, M1–M5
tests/fixtures, repeatability driver and historical evidence are frozen.
Interface: isolated build and diagnostic CLIs only.
UPSTREAM: fixed PyPI Rbeast0.1.25 sdist, actual Python3.12.3/GCC13.3,
setuptools80.9.0 (formal environment), wheel0.42.0 (system environment),
NumPy2.2.6 approved wheel; exact hashes in requirements-build.lock.
ADAPTATION: only increment -> increment512 in avx512_pcg_set_seed,
lossless diagnostic capture and provenance/ABI checks.
PAPER: SPEC S3 thresholds preserved, final_alert=false.
EXTENSION: repeated synthetic fixtures; no GPU evidence or scientific approval.

Tests/exit: RNG mechanism + unchanged API/prefix assertions first; any C failure
blocks full matrix. A/B control failures retained without suppressing C.
If C prerequisite gates pass, two predeclared B/C batches: B,C then C,B;
each 32 cells x20 reference fits plus 7 fixtures x20x45 prefixes /4900 fits.
Every full tree/array dtype/shape/bytes, candidate stage and observed dispatch
compared exactly within and across batches and execution/affinity controls for
the same model/actual ISA. No rounding/tolerance/clipping/sample substitution.
Private runs contain wheels, paths, command receipts and native output.

Resource limits: nice10; one serial worker at a time, owned subprocess only;
native fit30s, reference120s, decision180s, each full batch3600s, each build900s,
TERM then KILL5s. Inherited affinity versus first allowed CPU/thread vars1 is
process-local. No GPUs/NCCL/Redis/fault injection/system installs/node-1.
Do not pip into formal .venv-m5. Preserve before/after source/package/binary
hashes. Missing tools or out-of-scope dependency -> BLOCKED. On failed gate,
only existing predeclared controls/comparisons/regressions, then stop.
Deliver separate Draft PR based on PR7 branch; no merge/force push/M6.
