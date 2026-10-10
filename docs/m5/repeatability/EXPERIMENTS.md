# M5-R CPU protocol and evidence layout

Predeclared task: tasks/05_repeatability.md (user M5-R authorization).
Implementation: scripts/m5_repeatability.py, scripts/m5_repeatability_report.py.
All experiments use existing node-0 Linux x86_64 / Python3.12.3 isolated environment,
Rbeast0.1.25, NumPy2.2.6; no install, native rebuild or GPU workload.
Formal M5 source/defaults/assertions remain byte-preserved.

## Reference numerical matrix (ADAPTATION)

Input is exactly tests/m5_real_api.py's30 float64 values:
100+(i%3)*0.2+(30 if i>=15 else0), i0..29. Parameters are the original
flash/rbeast_adapter.py PARAMETERS, including seed20261010. Crossed controls:

- consecutive calls in one Python process / one new interpreter per call;
- inherited affinity and thread environment / fixed first allowed CPU with
  OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1;
- original three chains / diagnostic one chain;
- cputype omitted(auto) / SSE / AVX2 / AVX512.

20 fits per cell,32 cells,640 fits. New processes are launched serially. Native
one-series fitting is serial even when process imports create BLAS worker threads;
actual process task counts, environment and affinity are recorded. cputype is
accepted by the fixed wheel's official Python wrapper, not a custom env override.
The source parser has case/string quirks: AVX2 selects2, SSE selects1, AVX512
spelling falls through to auto (source checks character3=='4'). On this host auto
selects3. Actual function pointer is recorded, so the AVX512 cell is an explicit
requested-spelling/observed-dispatch control, not proof that spelling forces3 on
another CPU. No instruction-mode cell becomes a production default.

## Decision stability matrix (PAPER / EXTENSION)

Seven existing immutable fixtures,20 repetitions each:
stable, sustained, growth_19, growth_20, growth_21, spike, recovery.
No additional noise/sample labels, evaluator truth, result-selected seeds or sample
exclusions. All45 prefixes are processed through existing prefix_replay/preprocess/
filter_candidates with original3-chain PARAMETERS and PAPER thresholds.
The capturing adapter preserves the original one-new-interpreter-per-native-fit
boundary,30s timeout, raw conversion and candidate extraction. It adds exact
native array bytes and actual RNG dispatch; it does not cache or reuse output.
Constant/short prefixes retain the original insufficient-evidence guard.
All subprocesses inherit one fixed allowed CPU and thread environment1.

Record separately at every prefix and repetition:
cp/cpPr paired slots; mapped original iteration; cpOccPr; every other native array;
any cpPr>=0.8 candidate (before spacing/recovery); provisional duration/throughput
candidate sets after unchanged downstream filters; first observing iteration for
each rule; yes/no flips; qualified cp-set changes and adjacent-iteration drift;
cpPr distribution conditional on the cp appearing (absence is not imputed as0);
exact JSON and native array-byte equality. The two unapproved denominator rules
remain (degraded-baseline)/baseline and (degraded-baseline)/degraded, strict>0.2.
These are candidate comparisons; final_alert=false in every decision.

## Complete comparison data

data/data-index.json lists byte sizes and SHA256 for the sanitized data files.
data/reference-*.json contains every fit, full input and parameters, full raw output,
every ndarray's dtype/shape/base64 bytes and hashes, actual dispatch, per-field
changed-element counts/max finite absolute difference against the first fit.
data/decisions-*.json stores exact fixed fixture, all repetitions/complete stage
outputs and fits, plus per-prefix comparisons. Native raw trees are moved from
decision.engine.raw to the referenced fit to avoid duplicate storage; inputs are
represented by the complete immutable fixture/prefix position. No numeric field
is redacted or rounded. NaN padding is null in raw JSON and exact bits in ndarray
bytes. Missing cp observations remain missing, never fabricated zeros.
data/summary.json gives descriptive ranges and decision differences; it is not an
acceptance test. data/rng.json is the complete initialized-buffer causal experiment.

## Execution, safety and private evidence

CPU suite uses nice10, timeout3600s with TERM then KILL5s, private native worker
timeout30s, reference worker60s, decision worker120s. Affinity is process-local to
CPU0 within the inherited allowed set0..191; no exclusive reservation is claimed.
No other process or system affinity/thread setting is changed. Only this run's
owned process group is eligible for timeout cleanup. Native stdout/stderr,
unredacted argv and paths are retained privately for each worker and fit.
Command exit0 means the measurement completed, not scientific repeatability PASS.

Canonical complete commands with identity placeholders (exact private paths/argv
are in validation.json's private log references):

```sh
nice -n 10 timeout -k 5 3600 <project>/.venv-m5/bin/python scripts/m5_repeatability.py suite --output runs/m5-r-20261010-01 --count 20
<project>/.venv-m5/bin/python scripts/m5_repeatability_report.py --run runs/m5-r-20261010-01 --output docs/m5/repeatability/data
```

Complete batch command uses run_id m5-r-20261010-02; first batch01 is preserved.
Same crossed32×20 matrix and seven20-repeat decision inputs were used in both;
the only code correction is diagnostic raw capture before candidate-validation
failure. First suite exit0 is measurement completion with three missing raw outputs,
not data-completeness PASS. Its first comparison export exits1 with the original
fit-count assertion; neither failure nor partial export is overwritten. Full batch02
suite/export exit0; all4900 native decision outputs are captured. EXPERIMENTS'
initial command with01 is the historical first run, not the complete-data source.

Suite launch: server runs/m5-work/runs/m5-r-launch-20261010-{01,02}/suite.stdout,
suite.stderr and suite.exit. Runs: server runs/m5-work/runs/m5-r-20261010-{01,02};
reference/**/{00..19}.{json,command.json,stdout,stderr}, decisions/<scenario>/<repeat>/
{decisions.json,fit-*.json,fit-*.command.json,fit-*.stdout,fit-*.stderr}.
Each worker command receipt includes exact argv/exit/elapsed time.
The exploratory RNG check is independently preserved as runs/m5-r-probe-01.
Strict-test/regression commands and actual exit codes are listed in validation.json
and RESULTS. Independent strict run m5-r-strict-20261010-01 has00..05.log,
validation-private.json and API/replay raw. A private runpy wrapper in
runs/m5-access/m5-r-prefix-capture.py additionally executes unchanged m5_replay
and saves full/short globals when its assertion fails, in m5-r-prefix-capture-01.
No assertion is intercepted or suppressed. Historical docs/m5 repeatability-failure and original
server runs/m5-validation-* remain intact.

Sources: PAPER SPEC S3; UPSTREAM fixed wheel/sdist documented in ROOT_CAUSE;
ADAPTATION process/hash/output/timeout capture; EXTENSION synthetic repeated
prefix analysis. GreyHound algorithm/source is not used in this task.
