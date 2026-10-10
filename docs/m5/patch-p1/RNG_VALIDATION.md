# RNG causal validation

| Build | API exit | Prefix exit | RNG prior independence | Reuse | Correct integer reference |
|---|---:|---:|---|---|---|
| A | 1 | 1 | False | False | False |
| B | 0 | 1 | False | False | False |
| C | 0 | 0 | True | True | True |

The independent scalar uint64 reference implements source seed preprocessing,
modulo arithmetic, state lane order0,4,1,5,2,6,3,7, PCG XSH-RR output and
eight scalar steps per lane; it does not read old_word. Full64-output reference
and all prior-word0/1/0x123456789abcdef0, fill0/0xa5, repeats and reused-buffer
cycles are in rng-data.json. Initializing diagnostic buffers never modifies
production objects/globals. Layout is measured from release headers.

Unmodified generic/AVX2 integer control streams equal across A/B/C: True.
C seeder no longer reads prior byte32; it uses computed registers, so a
literal byte64 load is not required. B still reads byte32. Binary excerpts
show serial core loads selected local_pcg_set_seed and calls indirectly;
actual normal auto fit selects avx512_pcg_set_seed, CPU_CURRENT3.

This is a bounded one-series defect intervention, not multi-pixel/reentrant
thread safety or BEAST posterior equality across ISAs. No scientific adoption.
