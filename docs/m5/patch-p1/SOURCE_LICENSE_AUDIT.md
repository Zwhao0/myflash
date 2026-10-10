# Fixed-release source and license audit (UPSTREAM)

Only PyPI rbeast0.1.25 sdist SHA256
8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec is built.
Every source-index file (AVX512/AVX2/generic seeder, union, both cores, glue,
parser, Python wrapper, config, LICENSE) is checked on node-0 before changes.
pyproject.toml requires setuptools>=61 and wheel, backend setuptools.build_meta.
setup.py declares Rbeast0.1.25, existing ext_src C files plus abc_ioFlushcpp.cpp,
P_RELEASE=1/R_INTERFACE=0, and runtime numpy>=1.10.0. No NumPy build header
requirement or additional build dependency is present. Original files remain.

Packaged LICENSE is MIT, copyright2017 Henk Griffioen. The native seeder and
union have PCG project links without a complete PCG license notice. Other
native files reference implementation sources; abc_dirent.h declares copyright
1998–2019 Toni Ronkko and MIT with a link to tronkko/dirent. Package MIT
classifier alone does not resolve these third-party provenance/notice questions.
No conflicting license was inferred from absent notices. All packaged LICENSE
and native notices are retained in private extracted source. Their exact hashes
and the wheel's included notices are recorded in build-manifest.json.

Public wheel/source-tree distribution: BLOCKED pending complete third-party
attribution/licensing review. This task only privately builds/tests the source;
no wheel, full third-party tree or external source download is committed.
The minimal.patch includes only the changed line and necessary context with
precise release/path/function identification. No new licensing is assigned to
upstream code. Existing paper redistribution and project LICENSE issues remain
OPEN. No GreyHound reuse.
