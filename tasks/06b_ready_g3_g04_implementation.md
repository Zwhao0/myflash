# M6B-READY task07: approved G04 opt-in CPU implementation

Human authorization 2026-10-11: PR17 exact HEAD8fa096c9af00449a1ce940f99d153406cfe323e1/tree5f05021646305fffd23663fe42bfa92b7bac7d43 independently reviewed PASS; all eight G04 dimensions explicitly approved. New independent branch codex/m6b-ready-g3-g04-implementation at that exact HEAD; PR base codex/m6b-ready-g3-g04-decisions, subject to exact remote readback.

Allowed files: flash/localization.py; new tests/m6b_ready_approved_localization.py; this task; new docs/m6b-ready/g3-g04-implementation/**; STATUS/GAPS append only. Interface analyze_approved_g04(bundle), leaving analyze(bundle) and production callers unchanged. Profile schema/validation unchanged. PAPER max-group/min-rank/plot separation; ADAPTATION approved S1-MAX/W-EQUAL/R-GROUP/T-GE/C-GUARD/N-GUARD/Q-TWO/F-PROVISIONAL and conservative evidence; EXTENSION CPU synthetic cases only. No GreyHound code reuse.

Validation: unchanged original65 fixture assertions and saved exits;32 default full historical predictions exact equal; reuse task06 existing recommended sensitivity evidence; deterministic Stage1/Stage2/tie/weight/CV/numeric/threshold/Q-TWO/Group/identity/conflict/missing tests; record actual host/runtime/argv/source SHA/exit/raw logs. Preserve14original valid one-scope inputs/labels, observing new INCOMPLETE only on new entry. Final sets always empty, no final alerts.

Exit: retain all failures; stop on unresolvable failure without reducing assertions or altering thresholds. No M5 native matrix, native compile/fit, GPU/NCCL, Redis service, installation, fault injection, privacy专项, M6-B/task08 or merge. Publish separate Draft PR after passing CPU acceptance, supply exact head/tree for independent review, then STOP.
