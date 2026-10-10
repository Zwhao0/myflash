# M5 source ledger

| Nature | Source | Choice and change |
|---|---|---|
| PAPER | references/chapter3.pdf §3.2.2 pp25–27, §3.3.2 p33, §3.3.3 p35; SPEC S2/S3/S5 | rank0 completed iteration, retention500, window30 and seven thresholds, three means/recovery formula. PDF pp26/27/35 visually verified. |
| UPSTREAM | [Rbeast PyPI](https://pypi.org/project/rbeast/0.1.25/), approved wheel SHA in dependencies.json; wheel Rbeast/beast.py:beast docstring/signature | actual package/API, cp/cpPr/cpOccPr and time coordinates; mcmc_burbin spelling. Third-party package invoked, no algorithm copied. Rbeast metadata/packaged license inspected in private wheel audit; wheel metadata and packaged LICENSE specify MIT. |
| UPSTREAM | [NumPy2.2.6 release metadata](https://pypi.org/pypi/numpy/2.2.6/json) | cp312 manylinux x86_64, no Python dependency closure; runtime verified separately. BSD license with bundled license notices. |
| UPSTREAM | [PyTorch2.8 CUDA synchronize](https://docs.pytorch.org/docs/2.8/generated/torch.cuda.synchronize.html), [DDP](https://docs.pytorch.org/docs/2.8/generated/torch.nn.parallel.DistributedDataParallel.html) | device completion wait is explicit; DDP gradient synchronization is numerical audit. Target version2.8.0+cu128, unchanged M1 install. |
| UPSTREAM reference only | [GreyHound fixed snapshot](https://github.com/wutianyuan1/Greyhound/blob/d641b3997c17de700e1ef7d37e353418df7e336d/detector/control_plane/slow_detection.py):find_performance_drop L82–132 / validate_performance_drop L34–80 | rb.beast with season none/hasOutlier true; ncp_mode/cp/cpPr use and max-mean denominator reviewed. No code copied. No ACF, pause validation or mitigation imported; no treating its index cast or default10% as FLASH facts. Fixed-snapshot root LICENSE fetch returned404; license remains UNKNOWN and no copying is authorized. |
| ADAPTATION | base9c66be49:tests/m1_baseline.py:main / scripts/m1_launch.py:main,group_members; project AGENTS | isolated M5 copies retain small workload/assertions/resource checks, add opt-in callback and gradient/off/on audit. Original files untouched. Local strict single-writer/atomic persistence, original-index mapping, native subprocess/error/timeout evidence. |
| ADAPTATION | GAPS G01/G02/G13/G20 and user M5 scope | all unresolved assumptions labeled; no final rule/Redis/profile switching. Installation only after explicit user approval; offline wheel hashes, M1 reuse via independent environment path, pip check. |
| EXTENSION | tests/m5_fixtures; scripts/m5_evaluate.py | fixed synthetic inputs and independent evaluator matching tolerance2; experiments are CPU synthetic evidence, not GPU fault experiments. |

Dependency installation authorization: user explicitly approved Rbeast0.1.25 and
NumPy2.2.6 in isolated node-0 .venv-m5 during this M5 turn. Wheel payload downloaded
from TLS mirror and SHA256 matched official PyPI metadata; no system package install.
All parameters/assumptions in DESIGN and per-window output; experimental config is
not an approved resolution of scientific gaps.

UPSTREAM additional read-only audit: official Rbeast0.1.25 sdist SHA
8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec,
Python/ext_src/abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed and
abc_rand_pcg_local.h:local_pcg32_random_struct. Possible uninitialized union-state
seed defect, inference only. Master f9e7e53867c18713330828779f580dbe28be34d4 also
reviewed as public source; wheel/sdist remain installed-version authority. No source
copied/patched/compiled. This audit is limited to the repeatability failure.
