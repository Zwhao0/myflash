# M5-R: evidence levels and proposed remedy

Scope: CPU-only investigation of Rbeast0.1.25/NumPy2.2.6 on node-0;
base PR6 commit baa7638d775e1462240f0f63207c145ce209fcab. The formal
M5 adapter, model and strict tests are unchanged. No upstream patch, native rebuild,
version replacement or development dependency installation occurred.

## Fixed source authority (UPSTREAM)

[Official version metadata](https://pypi.org/project/rbeast/0.1.25/) and
the already downloaded fixed sdist, SHA256
8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec,
are source authority. The approved cp312 manylinux x86_64 wheel SHA256 is
1bde99a4c3b6cc8b130c8cd2d179385c50dbba6b00d82917ecb2475b0083eab5.
Installed binary and per-file source hashes are recorded in data/manifest.json,
data/source-index.json and the private run. No claim that a Git master SHA uniquely
identifies the released wheel; previous master audit is historical evidence only.
Packaged LICENSE specifies MIT (copyright Henk Griffioen); no native source is
copied into FLASH. Exact source paths below are relative to rbeast-0.1.25 sdist.

## Seed and thread path (UPSTREAM, read-only analysis)

1. `py_src/Rbeast/beast.py:beast`, lines440–444: Python `mcmc_seed` is
   passed as `mcmc.seed`; the requested burnin/chains/thinning/samples are passed
   separately. Nonzero seed20261010 is unchanged throughout M5-R.
2. `ext_src/beastv2_io_in_args.c:GetArg_3rd_MCMC___`, lines970/986:
   supplied seed is read with GetScalar; missing seed becomes0. There is no
   evidence that this particular supplied nonzero seed is dropped.
3. `ext_src/beastv2_COREV4.c:beast2_main_corev4`, lines54/73–74:
   the automatic local stream is declared without initialization; nonzero seed
   is offset by0x4f352a3dc. Timer seed is used only for seed0.
   `abc_rand_pcg_local.h:r_vslNewStream` invokes the selected local seeder.
4. `ext_src/glue_code.c:mainFunction`, lines168–176: one input series
   (numOfPixels1) runs serial `beast2_main_corev4`. Its chain loop at COREV4
   line285 processes chains sequentially using the local stream; three chains do
   not create three parallel workers. The separate multi-pixel core has its own
   automatic local stream per worker (COREV4_mthrd lines56/75–76), and mutable
   global function pointers/GAUSS initialization exist. Those multi-pixel/reentrant
   paths are outside this single-series experiment; no thread-race root cause
   or general thread safety claim is established.
5. `ext_src/glue_code.c:GetArg_GlobalFlagss` / `abc_common.c:GetNativeCPUType,
   SetupRoutines_ByCPU`: CPU detection selects RNG and vector routines. The actual
   exported `local_pcg_set_seed` pointer and GLOBAL_CPU_CURRENT are observed after
   each fit. Auto selects AVX512 on the tested host. Environment thread settings
   and affinity change only this experiment's processes, not system settings.

Native printed configuration is preserved privately, including adjustments:
requested segment minimum1 becomes2 and precision prior componentwise is printed
as uniform. These are unchanged M5 behaviors, not new scientific approvals.

## Suspicious implementation (UPSTREAM)

`ext_src/abc_rand_pcg_local.h:local_pcg32_random_struct` is a union.
AVX2 `increment` is byte32, overlapping AVX512 `state512[4]`;
AVX512 `increment512` is byte64. In
`ext_src/abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed`, lines105–108,
the function assigns increment512 but reads increment to construct initial state.
The later state512 stores occur after this read. An automatic uninitialized stream
therefore supplies indeterminate memory to a nominally seeded RNG. Zeroing the
stream alone would avoid indeterminate reads but would still leave the wrong-field
initialization formula, so it is not a validated mathematical repair.

The generic/AVX2 seeders initialize their own increment before reading it
(`abc_rand_pcg_local_generic.c:gen_pcg_set_seed`,
`abc_rand_pcg_local_avx2.c:avx_pcg_set_seed`). This is source evidence, not by itself
proof of how the installed binary executes.

## Reproducible minimal experiment (ADAPTATION)

`scripts/m5_repeatability.py:rng_worker` calls exported functions from the existing
loaded wheel using isolated, fully initialized, aligned, owned buffers. It changes
only the old uint64 at byte32 (0,1,0x123456789abcdef0), with the same effective seed
20261010+0x4f352a3dc. Each prefill repeats twice. No function pointer, library global,
production stream or binary is patched; no uninitialized buffer is used in the
diagnostic itself. Only assigned state fields and the16 generated uint32 values are
compared, not untouched padding. Complete values are in data/rng.json.

For AVX512 all six initialized state vectors match the source-derived recurrence
that includes the old byte32 word. Changing that word changes initialized state and
generated random numbers; repeating the same word reproduces them. Generic and
AVX2 output streams do not depend on the changed word. This confirms a specific
seed-initialization defect in the actual installed wheel, not merely suspicious C.

Read-only installed-binary disassembly independently shows at0x27a0d an addition
from0x20(%rdi), preceding the state stores; at0x27a11 it writes the intended
increment to0x40(%rdi). Sanitized disassembly is in data/seeder-disassembly.txt;
original command/path/output remain private.
Installed serial-core disassembly also loads `local_pcg_set_seed` and calls it
indirectly at0x52d3b/0x52d42 with the stack stream at rbp-0xaf0. The sanitized
initialization excerpt is data/core-initialization-disassembly.txt; full output is
private run02/core-disassembly.txt. Fixed source abc_001_config.h lines30–31 selects
PCGRAND_LIBRARY1/MKLRAND_LIBRARY0, and abc_rand.h includes the local-PCG macros.
Thus the observed selected callback is on the installed serial inference path,
not merely an exported but unused diagnostic symbol.

## Causal scope and limits

The local RNG defect is **CONFIRMED** by an intervention on prior buffer contents,
an exact predicted state calculation, generated random-number differences and
installed instruction evidence. Normal M5 auto dispatch is verified to use this
seeder. Same-process/fresh-process, one-/three-chain, affinity/thread and instruction
controls are reported separately in RESULTS; holding CPU scheduling fixed does
not initialize stack memory.

This gives a concrete causal mechanism for seeded stream failure and strong
evidence linking it to M5's numerical failure. An API change to SSE/AVX2 changes
both RNG and floating-point vector routines, so that control alone cannot prove
the initializer is the sole source of every posterior discrepancy. A patched
AVX512-wheel intervention restoring the original two strict tests has **NOT_RUN**.
We do not claim all AVX512 operations are nondeterministic or that M5 is repaired.

First decision batch also observed three `invalid cpOccPr` rejections and candidate
presence flips. The first diagnostic lost raw on those validation exceptions;
the original stderr/input/decision records remain, and complete independent batch02
captures all outputs before validation. No specific invalid probability value or
causal explanation of that additional rejection is inferred without its raw.
See RESULTS and data/first-run-failures.json; no probability clipping/tolerance was
introduced to evade the unchanged production validation.

## Proposed patch and retest (ADAPTATION, NOT_APPROVED / NOT_RUN)

Proposed minimal native change: at AVX512 seeder line107 replace the read of
`rng->increment` with `rng->increment512`. Consider explicit zero initialization
of both serial/multi-thread local stream declarations as defense in depth, but
evaluate that separately from the one-line mathematical fix. No patch is applied.

Risks: seeded trajectories and posterior values will change; compiler/flags and
binary ABI must match; an upstream source wheel may differ from the approved
binary build beyond this line. A partial initialization fix does not establish
global thread safety. A cputype AVX2 workaround likewise changes RNG/numerical
semantics and is not silently acceptable as an M5 default change.

Before any build, obtain approval for the exact source patch, isolated build
environment/development dependencies and candidate wheel installation. Preserve
the approved runtime read-only; install candidate only in a new environment.
Record source diff, compiler/flags/headers, wheel and binary SHA, license and build
logs. Use new run_ids for the buffer experiment, unchanged m5_real_api/m5_replay,
the full predeclared matrix and20×7 decision replays, plus M5/privacy regressions.
Require real exit0 on the original strict assertions and array byte equality;
keep all previous FAIL evidence. Cross-ISA exact equality is not implied and
should be separately characterized. No M6 until a later explicit review.
