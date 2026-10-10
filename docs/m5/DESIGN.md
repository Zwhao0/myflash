# M5 design and scientific boundary
PAPER: chapter3 §3.2.2 pp25–27, §3.3.2 p33, §3.3.3 p35 (PDF visually checked).
User authorization: full M5a–e, stop before M6. Base main 9c66be49.

## Completed iteration callback
ADAPTATION: one-based global training iteration, begin/end only; local single-writer
per run/rank JSON snapshot with strict consecutive publication and at most500 records.
Atomic replace/fsync; failed iteration aborted, no fabricated record. Timestamp is UTC
wall time of completion, duration uses monotonic ns converted to ms. UTC stamps are
metadata, never cross-machine duration measurements. Reject mixed scopes/invalid,
duplicate, missing and out-of-order records instead of sorting or filling.
PAPER: rank0 is detector input. Every rank may report for completeness audit.
Redis Publisher Protocol is interface only; no service or distributed closure.

Timing includes forward/backward/gradient sync/optimizer and explicit completion wait
only when supplied by framework. In resident-data DDP smoke, there is no data loader;
CUDA pre-drain occurs before begin, completion wait before end, local publication and
post-step sync audit excluded. DDP communication, explicit gradient verification communication and Python finite-gradient assertions
are included. Optional general caller may begin before data loading, and must label
that boundary. Aggregate duration cannot attribute shares of compute, communication,
data loading or synchronization; those need separate instrumentation. Extra CUDA
synchronization and fsync can affect wall throughput; no low-overhead claim.
§3.3.3 periodic sender must transport already completed records, never infer boundaries.

## Detection evidence (M5c)
PAPER constants: window30, thresh_prob0.8, degradation_thresh0.2, warmup3,
z-score3.0, spacing2 iterations, recovery_ratio>=0.75 filtered.
ADAPTATION: take last30 original records before filtering global iterations1..3;
population z-score (absolute value), zero variance keeps points with z=0.
Removed points retain bidirectional iteration/index mapping. Rbeast sees compressed
regular array start1/deltat1; this changes temporal spacing after removal and is
explicitly an unapproved scientific assumption (G01), not missing-data imputation.
All output states remain AMBIGUOUS_SPEC/PROVISIONAL evidence; no final alert.

Rbeast adapter uses real pinned rb.beast in one disposable CPU subprocess per
window with 30s timeout; fatal native errors/timeout cannot manufacture a candidate.
A full refit is retrospective within published prefix, not classical incremental
BOCD. Minimum8 retained observations is an explicit engineering guard; empty/constant
input returns insufficient evidence without invoking an undefined native fit.
All native arrays and print output are saved. NaN padding becomes JSON null and is
identified as PADDED_SLOT; invalid coordinates/probabilities fail evidence. cp slots
are sorted chronologically after validation; all slots are audited, not truncated to
ncp_mode. This candidate policy is G01 experimental, not FLASH paper fact.

UPSTREAM: native cp is a time coordinate. With start1/deltat1 index0=cp-1.
cpPr is localized occurrence posterior; cpOccPr is per-time posterior, never silently
substituted. Rbeast model hasOutlier=False is an explicit experimental choice after
paper z-score removal; GreyHound hasOutlier=True is not adopted as FLASH fact.
Native segment min1/margins0, trend orders0..1, knots0..10, nonzero seed20261010,
3 chains/8000samples/thin5/burbin200 and precision prior are logged. These choices
remain scientific assumptions G01 even when API compatibility passes. Native warning
adjustments and all outputs remain evidence; library defaults never become paper facts.

PAPER means use whole retained left [:cp], right [cp:] including latest, recent
[cp+1:]. Original iteration distances enforce spacing2; the first probability-qualified
chronological point anchors spacing even when a later scientific filter rejects it.
That stage ordering/anchor is ADAPTATION requiring scientific review. Each candidate
records probability, spacing, slices/counts, both degradation denominators, recovery,
observed persistence and skip reason, including insufficient rightmost samples and
zero denominator. Negative duration delta is not sustained slowdown. No final alert.

EXTENSION: separate evaluator uses fixed synthetic onset and ±2 original-iteration
matching tolerance. It reports first candidate decision, matched delay, missed and
pseudo-candidate decisions for probability and two provisional denominator rules.
These are window-refit candidate metrics; no alert deduplication/FLASH accuracy claim.
Detector input consists only of iteration records, never evaluator metadata or truth.
Prefix k contains only records1..k; full replay versus truncated replay is checked
again using real seeded Rbeast. Rank1 data is only a Reporter completeness audit.

M6 still requires Redis authentication/isolation, completed-record queue/ACK/idempotency,
control status0/1 with profile_epoch, node ACKs, complete samples, bounded collection,
rearm/debounce, failure handling and an approved final detection rule. None executes here.
