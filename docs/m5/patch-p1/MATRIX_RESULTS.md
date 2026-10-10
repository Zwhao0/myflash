# Full exact numerical matrices

| Build/batch | Reference fits | Native decision fits | Prefixes | Integrity issues | Native validation errors |
|---|---:|---:|---:|---:|---:|
| B/1 | 640 | 4900 | 6300 | 0 | 0 |
| C/1 | 640 | 4900 | 6300 | 0 | 0 |
| C/2 | 640 | 4900 | 6300 | 0 | 0 |
| B/2 | 640 | 4900 | 6300 | 0 | 0 |

Candidate C full-posterior gate: **PASS**; integrity: **PASS**.
matrix-data.json gives every cell and combined same-model/actual-ISA group,
including inherited versus fixed affinity/thread environment, same/fresh
process and both batches. Requested AVX512 spelling is not treated as
proof of dispatch. Cross-ISA posterior equality is not required.

All logical trees and24 arrays/fit are exported losslessly with dtype,shape,
base64 bytes and SHA256. Comparison preserves NaN payload/signed zero and
does not mix PID/path/time metadata into numeric digests. First differences
are retained; no failures/samples are discarded. Complete expected/actual
ledgers and independently checked inputs/model/fixture/byte counts accompany
each batch. Measurement completion is not acceptance.

Inputs are iteration times in ms: the reference is30 float64 samples/240
bytes; mcmc_samples8000 is a different sample count. Receipt elapsed_s is
seconds and is not CUDA Event/collective timing. Inherited reference
worker affinity/thread counts and pinned observations are exported.
An owned-process point inspection confirms decision/native workers on
CPU0 with all four thread variables1. Full batches effectively run at
nice19 because nested nice10 saturates, versus protocol nominal10; this
lower priority is identical for B/C and never used for a performance
claim. Sampling code, seed, model, thread settings and order are unchanged.
