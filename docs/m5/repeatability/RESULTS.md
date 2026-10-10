# M5-R results (2026-10-10)

**Strict numerical repeatability: FAIL.** Both unchanged strict tests exited1
again in independent run m5-r-strict-20261010-01. **Decision stability: no
unconditional PASS.** The complete second batch has stable qualified decisions on
the seven fixed fixtures, but first-batch validation rejections caused candidate
presence flips. All evidence remains; no final FLASH alert or M6 acceptance.

## Numerical repeatability (UPSTREAM / ADAPTATION)

node-0 Intel Xeon Platinum8463B,2 sockets×48 cores×2 threads, Linux6.8.0,
Python3.12.3, unchanged isolated Rbeast0.1.25/NumPy2.2.6. No GPU experiment.
Run m5-r-20261010-02:32 cells×20 fits=640, exact reference input/seed20261010.
Numbers below are unique full logical-output/array-byte hashes per20 fits;
JSON equality has the same unique counts. Inherited and pinned means the protocol's
affinity/thread controls; original3-chain defaults remain unchanged.

| Chains | Affinity/threads | CPU request | Same process | Fresh process |
|---:|---|---|---:|---:|
| 3 | inherited | auto | 5 | 16 |
| 3 | pinned/1 | auto | 5 | 14 |
| 1 | inherited | auto | 6 | 13 |
| 1 | pinned/1 | auto | 6 | 12 |
| 3 | inherited | AVX512 | 5 | 12 |
| 3 | pinned/1 | AVX512 | 6 | 15 |
| 1 | inherited | AVX512 | 6 | 16 |
| 1 | pinned/1 | AVX512 | 5 | 14 |
| 1 or3 | inherited or pinned/1 | SSE | 1 (all4 cells) | 1 (all4 cells) |
| 1 or3 | inherited or pinned/1 | AVX2 | 1 (all4 cells) | 1 (all4 cells) |

Actual dispatch is AVX512 for auto/AVX512, generic for SSE, AVX2 for AVX2;
the requested AVX512 spelling falls through to auto in this version (EXPERIMENTS).
Single-chain and scheduling controls do not remove failure. Cross-ISA equality
is not asserted; SSE/AVX2 are diagnostic controls, not an approved default fix.
First batch m5-r-20261010-01 gives the same qualitative repeatability conclusion.

For pinned original3-chain auto, the reference's strong cp16 and paired cpPr1
are identical, **while cpOccPr and numerous other posterior arrays vary**.
Changed array elements versus the first fit:204–211 for nonidentical same-process
fits,186–211 for nonidentical fresh-process fits (some complete duplicates also
occur). Same-process maximum absolute differences include cpOccPr0.001125000075,
sig2 0.013381332159, marginal likelihood0.212196350098, trend.Y0.000350952148;
full exact values/counts for every field and fit are in data/reference-*.json.
These finite observed ranges are not a general numerical-error bound.

## Upstream evidence and repair status

The **installed AVX512 seeder's prior-memory dependence is CONFIRMED**:
same seed, different initialized old word at byte32, different initial states and
random output; all six source-derived state predictions match exactly. Identical
prefills reproduce the outputs; generic/AVX2 controls are independent of that word.
Installed disassembly reads0x20 before state initialization, distinct from intended
increment at0x40. Actual normal auto dispatch uses that defective seeder.
ROOT_CAUSE distinguishes this causal evidence from a claim that it is the sole
cause of every posterior difference. Patched-AVX512 restoration of the original
strict tests is NOT_RUN. No patch/rebuild/install/upgrade occurred; proposal and
risks are delivered for later approval.

## Complete fixed-input decision batch (PAPER / EXTENSION)

Run02:7 fixtures×20 complete replays×45 prefixes=6300 decisions,
4900 actual native fits (700 per fixture); other prefixes use existing short-input
guards. All20 repetitions keep the same seed/model/thresholds/input policy, one
fixed allowed CPU and thread environment1. Capturing adapter preserves the original
per-fit fresh-process boundary and existing candidate validation/filter functions.
Data/decisions-*.json contains all full arrays/bytes, inputs, mappings, stages,
conditional cpPr observations, prefix-level differences and hashes.

| Fixed fixture | Probability-qualified original cp iterations | First probability observation | First duration candidate | First throughput candidate |
|---|---|---:|---:|---:|
| stable | none | none | none | none |
| sustained | 21 | 22 | 22 | 22 |
| growth19% | 21 | 22 | none | none |
| growth20% | 21 | 22 | 23 | none |
| growth21% | 21 | 22 | 22 | none |
| spike | none | none | none | none |
| recovery | 21,28 | 22 | 22 | 22 |

Every first-observation entry above is the same in20/20 repetitions. It is the
prefix's observing iteration, distinct from the changepoint's original iteration.
No qualified cp-set differences, adjacent qualified-cp drift or candidate presence
flips occurred in this **second** batch; no native validation rejection occurred.
Every fixture has35/35 fitted prefixes whose full posterior bytes differ across
repetitions. Low-probability raw cp sets differ and drift by1 original iteration
(all seven fixtures have such drift); exact affected prefixes are in summary.json.

| Fixture | Largest conditional cpPr range over all observed cp/prefix pairs | cpPr range of points that meet0.8 |
|---|---:|---|
| stable | 0.023791670799 | none |
| sustained | 0.049875020981 | 1–1 |
| growth19% | 0.023833364248 | 1–1 |
| growth20% | 0.030208379030 | 1–1 |
| growth21% | 0.020000040531 | 0.999958336353–1 |
| spike | 0.025541663170 | none |
| recovery | 0.031250059605 | 0.992291629314–1 |

Ranges here are rounded only for readability; data retains full values/distributions
and occurrence counts. Conditional ranges omit absent cp observations without
imputing them. Stable/spike outcomes include the unchanged preprocessing behavior;
they do not prove a general false-positive rate or native spike-filter performance.

The two unapproved20% denominator interpretations disagree at14 growth20 prefixes,
all24 prefixes22..45 of growth21, and3 recovery prefixes30..32. For nominal20%,
duration candidate membership itself changes with prefix means/noise phase (e.g.
23 qualifies while26 does not), consistently across repetitions. This is different
from a stochastic repetition flip. Exact ratios/stages and input hashes are retained;
no threshold, comparison operator, seed or fixture label was changed. The lack of
near0.8 posterior points in these existing fixtures limits generalization of the
probability-gate result; strong cp agreement alone does not settle other inputs.

## First-batch failures remain part of the conclusion

Run01 also executed20 repeats per fixture. It recorded three native-output
validation exceptions (`invalid cpOccPr`): sustained repeat04/prefix28,
sustained repeat11/prefix35, growth19 repeat01/prefix29 (repeat indices0-based).
At these identical prefixes other repetitions produced probability candidates;
sustained also flipped both provisional denominator candidates. Thus operational
candidate presence flips **were observed**, even though first candidate observing
iterations stayed unchanged. These are validation-rejection flips, not demonstrated
crossings of0.8 by a valid posterior. Missing/error output never becomes a zero.

The first diagnostic incorrectly extracted candidates before saving raw output;
three rejected raw trees were consequently NOT_CAPTURED. Their exact inputs/hashes,
parameters, exit1 stderr, decisions and missing-output status are retained in
data/first-run-failures.json and original private run. The other4897 raw fits and all
first-batch records remain private, including partial export/assertion failure.
This capture defect was corrected only in the diagnostic, then the **entire**
predeclared matrix was rerun under a new run_id; no failed repeat was replaced,
deleted or selected out. Run02 captures all4900 raw fits. Specific invalid numeric
values from Run01 cannot be reconstructed and are not guessed; no claim of a
particular overshoot value or confirmed cause of that validation defect is made.

## Independent conclusions and impact

Strict repeatability remains **FAIL**; original m5_real_api and exact prefix replay
assertions still exit1. Native RNG initializer defect is confirmed locally; successful
repair and exclusive end-to-end root-cause proof remain NOT_RUN.

Decision stability is **conditional empirical stability in the complete second
batch**, with an overall **no-unconditional-PASS** conclusion because the first
batch has real candidate presence flips. Low-probability raw cp and full posterior
instability remain. Repeated fixed-seed runs are not independent sampled seeds;
no confidence interval, probability of future flips or universal error bound is
inferred from20 repeats. The second batch cannot erase the first failures.

Recommendation: **do not accept bounded statistical repeatability as a substitute
for strict PASS at this point**. Prefer the reviewed isolated initializer repair
and independent strict/decision retests. If a later review chooses a statistical
criterion, first define its numerical tolerance, candidate-flip/invalid-output
allowance and required fixtures/environment coverage, then measure it on independent
inputs. Such criteria would be an explicit ADAPTATION, not a paper result.

M6 would inherit occasional missing candidates/variable evidence and possibly
variable trigger timing. A final rule, rearm/debounce/restart semantics and any
stochastic acceptance policy require approval; none is implemented here. Paper
experiments would need repeated-run candidate/error/delay distributions, independent
truth and separate automated-detection versus forced-profile metrics. Fixed-fixture
stability cannot establish GPU fault precision/recall or reproduce paper latency.
G01/G02/G13/G20 remain OPEN; final_alert=false; stop for user review.

Exact commands/exits/private log locations: validation.json and EXPERIMENTS.md.
Preservation and privacy checks: preservation.json / publication-validation.json.
