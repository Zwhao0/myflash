# Matched private builds (UPSTREAM / ADAPTATION)

Fixed sdist and all thirteen source-index files were rehashed on node-0. Actual
Python3.12.3, GCC/G++13.3.0, development headers and existing objdump/readelf/nm
were used. requirements-build.lock pins exact package versions/hashes selected
from node-0 formal setuptools80.9.0 and system wheel0.42.0, plus approved
NumPy2.2.6. PyPI package metadata and downloaded wheels were hash-checked before
installation. No additional dependency was resolved or installed.

Private build-env was made with existing Python/venv/ensurepip. Installation
uses --no-index --no-deps --require-hashes and project-local caches/TMPDIR;
no system package or formal .venv-m5 pip command occurred. Candidate envs contain
only NumPy and their own wheel, with PYTHONNOUSERSITE=1 and no PYTHONPATH.
The original pyproject.toml/setuptools backend and setup.py are unchanged.
The locked backend's setup.py bdist_wheel entry point generates legal build tags
1b and2c without changing distribution version0.1.25; no version monkeypatching.
Actual cp312-cp312-linux_x86_64 tags are preserved. Packaging semantics were
checked against [PyPA wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/).

```sh
python3 scripts/m5_p1_build.py --output runs/m5-p1-build-01 --packages <private-packages> --sdist <fixed-sdist>
<build-env>/bin/python setup.py bdist_wheel --build-number 1b --dist-dir <private-B-dist>
<build-env>/bin/python setup.py bdist_wheel --build-number 2c --dist-dir <private-C-dist>
```

B/C use identical locked toolchain, sysconfig compile/link flags and inherited
build environment. Source pragmas (including upstream Ofast) are retained;
no optimization/fast-math/CPU-dispatch/thread change was used to obtain PASS.
Their source file maps were captured before build-generated files: exactly
ext_src/abc_rand_pcg_local_avx512.c differs. All other file hashes match.
The release uses CRLF. An initial LF-context patch dry-run failed; the exact
CRLF diff applied but Git flagged patch-file whitespace. minimal.patch is now
a minimal zero-context LF review diff (whitespace-aware dry-run passed). For
reproduction use scripts/m5_p1_build.py's byte-preserving substitution; it keeps
all original release line endings. Actual B/C builds always used that exact
byte substitution, unaffected by these review-patch formatting corrections.

build-manifest.json records compiler/Python identities, environment, sysconfig,
source file maps, original source-index checks, wheel/.so hashes, WHEEL metadata,
included license notices and ABI. Private build stdout/stderr and every step's
exact argv/real exit code are retained in runs/m5-p1-build-01/*.command.json.
The detached build launch has a launch exit receipt; compilation/install/ABI/
inspection commands each have their own real completion receipts. The launch
receipt alone is not used as a completed-build PASS.

Standalone tests/m5_p1_abi.c is compiled with the actual C compiler/sysconfig
CFLAGS/-fPIC and P_RELEASE=1/R_INTERFACE=0 against the exact release header.
B/C both sizeof96, alignof32, U64 size8, increment offset32, increment512 offset64,
MULTIPLIER_8steps offset72 and INCREMENT_8steps offset80. ctypes uses that measured
layout and source prototypes (U64 uint64_t; U32 uint32_t; I32 int32_t), with explicit
argtypes/restype. Shared dependencies, ELF ABI and exported symbols are inspected.
Seeder and serial-core instruction excerpts accompany RNG_VALIDATION.md.

A remains the official wheel and formal binary. Private before/after manifests
cover every non-pycache formal environment file and every baseline tracked source
file. Candidate fit receipts record actual loaded .so and interpreter SHA256.
No formal migration/node-1 verification or production adoption is authorized.
Third-party redistribution questions remain in SOURCE_LICENSE_AUDIT.md; wheels
and full extracted source stay in server-private runs.
