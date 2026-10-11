# M6B-READY Gate 0 baseline audit

ADAPTATION: fixed Git DAG and original-evidence preservation audit. PAPER: SPEC S2/S4/S6 remains the scientific source; no scientific choices are approved here. UPSTREAM: existing Git object/Redis dependency metadata; no third-party source or wheel is newly published. EXTENSION: current deterministic CPU cursor inputs.

Remote read-only checks matched the supplied baseline before branch creation: Public; PR10 Draft/Open/unmerged, base codex/m5-s1-science-audit, head codex/m6a-control-plane. New branch codex/m6b-ready-g0-evidence did not exist. Only this independent branch is published, base codex/m6a-control-plane.

| Snapshot | Commit | Tree | Parents |
|---|---|---|---|
|M6-A published|5b91977b07b4f357e0c2e37490739e4a5803fea0|5eeeef0101538597b08a1482c3b17d2b9b6be0f6|03a761440e418ec7176e03ac979d7505d3ef7ff5|
|M6-A executed|e3f6b4225db83ec97e0b59161fa4f46a14ab9f68|3c2935aa340fea3a74c5937e678093fa05c5c319|083e208d48b72f695959889a9c239662f4e19938|
|main|ce984ea21a604092312442c7c788f2f4b244fad4|2fc769bd39f96d58e7fb1ea261f984bf24380590|ca6923d58d1fd5b2a0f899176780b17d6bd7e364 6855af26d5e5da7d58231ebf6a76417bc5350d77|
|M5-R|ed954f5a289e2a9f3c585f7f5af3792d0fde0c8d|36d19267fbbbaa12cacbaaac42bd3a56e4cac68b|004b1d6f98a9052db4edcf243f8c6d5359d5eed1|
|M5-P1|d2973f5fa66ae99ec7ea09ea7040a11d1b95b845|c81e05380685e86acccde6ff97638d49d02457c8|a4db998865cab0f6e7d59a51301b9ee5d7678687|
|M5-S1|7746fccb88718a5567da0d042d2679672d4226fc|2fc769bd39f96d58e7fb1ea261f984bf24380590|2f8971f4d2402ea64363edba1af7cb2ae97bdd4a|

PR10 versus main is diverged: ahead10/behind4; merge-base 7746fccb88718a5567da0d042d2679672d4226fc. Main and M5-S1 trees are identical. The two commits after e3f6b4 change only documentation/task/STATUS/GAPS; `git diff e3f6b4 5b91977 -- flash scripts tests` is empty. This round executes the identical existing M6 source plus two newly added files, bound by their exact file SHA in validation.json. Execution HEAD is 5b91977 with added uncommitted files; a later publication commit is not retroactively claimed as an executed clean HEAD.

Read commands: GitHub REST GET repo, PR10, heads/main, heads/codex/m6a-control-plane, heads/codex/m5-s1-science-audit, Git commits and compare/main...head; local git show/rev-parse/rev-list/merge-base/diff. Original remote responses/command receipts stay in the private current run. No merge/rebase/reset/force-push.

## Historical snapshots and preservation

The following whole exact-snapshot tracked trees were compared to the task baseline; STATUS/GAPS must have original byte prefixes, all other files byte-identical. No historical fits/builds were rerun.
- M5-R: 598 files preserved at ed954f5a289e2a9f3c585f7f5af3792d0fde0c8d. Relevant report/index: docs/m5/repeatability/{RESULTS.md,validation.json,data/first-run-failures.json}.
- M5-P1: 832 files preserved at d2973f5fa66ae99ec7ea09ea7040a11d1b95b845. Relevant report/index: docs/m5/patch-p1/{RESULTS.md,validation.json,data-index.json}.
- M5-S1: 851 files preserved at 7746fccb88718a5567da0d042d2679672d4226fc. Relevant report/index: docs/m5/science-s1/{RESULTS.md,validation.json,data/input-hashes.json}.

M5-R strict FAIL and three NOT_CAPTURED raw fits remain. P1 candidate C has only finite engineering scope; production still has the original wheel. Historical privacy CI proves its checked text only. New engineering admission, science, GPU and cross-machine results are separate gates.

## Original M6 evidence

EVIDENCE_INDEX.json re-read1175 historical pointers (1171 data-index entries + publication/preservation/installation pointers): all VERIFIED, none MISSING/MISMATCH. Original and sanitized SHA values are explicitly separate. Full historical combined stdout/stderr is public as .txt; original runner did not retain separately split streams, so historical separate stdout/stderr is NOT_CAPTURED. No raw exit was filled in. Current subprocess stdout/stderr are separately retained.

historical-review.json parses server-relevant-05 original manifest (execution e3f6b4), confirms all3 exits0/no timeout/child_finished, matching source/log SHA; lists all32 CPU and6 Redis test names with completed statistics. It independently checks original iteration/manifest/sample/drain/M4 data hashes, two epoch transitions, node ACK versus six per-rank CPU applied proofs and Monitor reset. Full state JSONs are linked by EVIDENCE_INDEX. ACK-only TIMEOUT, partial-reset BLOCKED, missing/corrupt INCOMPLETE, fencing/restart/old-epoch rejection are preserved. All sources and clocks are CPU simulated.

server-validation-04 Redis setup FAIL, initial Redis BLOCKED, privacy120s timeout, detached-parent NOT_CAPTURED, postflight Path/bytes failure and publication wrapper failure remain in the complete historical manifests/logs. historical cleanup0 and formal protection receipts are distinct from this round’s formal hash observation; no new historical Redis PID/socket0 assertion is made.

Original Redis installation authorization was found in the same project M6-A user message; see APPROVALS.json. Scope is installation for M6-A; versions/path and per-message timestamp were not explicit. Future reuse remains REQUIRES_OWNER_DECISION.

Executor: evidence delivered, cursor contract FAIL, M6B-READY BLOCKED. Independent ChatGPT review PENDING. Stop after this Draft PR; no M5-S2/G20 repair/M6-B.

Publication identity audit supplement: first ordinary push8540313 exposed
textual historical process-id prefixes in4 Redis logs, outside the existing
text scanner rules. Current tree aliases those PIDs and updates sanitized SHA.
Original SHA/data/status/exit/time are unchanged. Earlier public commit retains
PID identities; history/privacy closure requires owner decision. No force-push
or history rewriting is performed; exact-head CI proves only its text scope.
