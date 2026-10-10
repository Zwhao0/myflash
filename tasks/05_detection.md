# M5 approved scope (2026-10-10)
User approves M5a–e continuous internal progression; stop before M6.
Base main 9c66be49c33b9022573011e1dd2846721cca3833.
No changes to existing M1–M4 implementation, thresholds, samples or results.

1. M5a allowed: flash/iteration_reporter.py, tests/m5_reporter.py,
   tests/m5_ddp.py, scripts/m5_launch.py, docs/m5/DESIGN.md.
   Interface: completed iteration record, local bounded persistence; tests strict
   validation/500 retention/reload, opt-in 2-GPU DDP. Exit on invalid records,
   launch timeout 300s and own process group cleanup.
2. M5b allowed: flash/rbeast_adapter.py, docs/m5/dependencies.*, SOURCES.md.
   Inspect real wheel metadata/API; no installation until explicit approval.
3. M5c allowed: flash/change_detection.py, tests/m5_detection.py, fixtures,
   GAPS.md. Strict iteration sequence, explicit mappings, full evidence.
   Unresolved scientific choices stay AMBIGUOUS_SPEC.
4. M5d allowed: scripts/m5_replay.py, tests/m5_replay.py, fixed fixtures,
   sanitized results; CPU real Rbeast prefix replay after dependency approval.
5. M5e: bounded opt-in DDP/reload and existing CPU regressions; docs/m5,
   STATUS.md, privacy/CI only. No fault injection, Redis or auto Profile.

PAPER parameters: window30, probability0.8, degradation0.2, warmup3,
z-score3, spacing2, recovery0.75. Source chapter3 pp25–27/33/35.
ADAPTATION: validation/storage/timeout/evidence isolation.
