# Future iteration cursor contract: FAIL

ADAPTATION strict nonnegative integer consumer cursor; not a paper requirement. PAPER only specifies500-item retention (SPEC S2). Source: unchanged flash/m6_iteration.py:IterationReader.read at baseline5b91977, file SHA57dd7ce9cf80287ee0b73782c6ca0bab9be406c303bfa30e6d5f4b60ef835ba9.

The reader checks only `after_iteration + 1 < records[0].iteration`. It does not check future cursors against stream.last or reject invalid numeric types. Existing tests/m6_control.py:iteration_timeout_and_cursor_gap_visible covers old retention gaps; future applied-boundary scope coverage is a different condition.

node-0 Python3.12.3 command: `<existing-formal-python> tests/m6b_ready_cursor_contract.py --output <new-private-output>`. Original full argv/cwd/env/input/source SHA, separate stdout/stderr and every pre-assert observation are in current/validation-02 and indexed with original/sanitized SHA. Test exit1, timeoutfalse, child_finishedtrue,9 tests completed,9 failures, no expectedFailure/skip. Driver exit1/FAIL.

| Input | Server last / retained_from | Actual behavior | Contract |
|---|---|---|---|
|0 (test_cursor_before_retention_gap)|501 / 2|INSUFFICIENT_EVIDENCE|preserve existing boundary/window/status|
|0 (test_empty_history)|None / None|INSUFFICIENT_EVIDENCE|preserve existing boundary/window/status|
|1 (test_expired_record)|1 / 1|TIMEOUT|preserve existing boundary/window/status|
|502 (test_future_after_500_retained)|501 / 2|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|1000000 (test_future_large)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|2 (test_future_one_step)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|True (test_invalid_types_strict_integer_adaptation-0)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|False (test_invalid_types_strict_integer_adaptation-1)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|-1 (test_invalid_types_strict_integer_adaptation-2)|1 / 1|INSUFFICIENT_EVIDENCE|reject; FAIL if READ_CONFIRMED|
|0.5 (test_invalid_types_strict_integer_adaptation-3)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|1.0 (test_invalid_types_strict_integer_adaptation-4)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|'1' (test_invalid_types_strict_integer_adaptation-5)|1 / 1|{'type': 'TypeError', 'message': 'can only concatenate str (not "int") to str'}|reject; FAIL if READ_CONFIRMED|
|nan (test_invalid_types_strict_integer_adaptation-6)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|inf (test_invalid_types_strict_integer_adaptation-7)|1 / 1|READ_CONFIRMED|reject; FAIL if READ_CONFIRMED|
|-inf (test_invalid_types_strict_integer_adaptation-8)|1 / 1|INSUFFICIENT_EVIDENCE|reject; FAIL if READ_CONFIRMED|
|1 (test_legal_boundaries_keep_full_window-1)|501 / 2|READ_CONFIRMED|preserve existing boundary/window/status|
|501 (test_legal_boundaries_keep_full_window-501)|501 / 2|READ_CONFIRMED|preserve existing boundary/window/status|
|0 (test_missing_run)|None / None|BLOCKED|preserve existing boundary/window/status|

Minimum counterexample: publish one valid iteration (last1), read after_iteration2 → READ_CONFIRMED with the full record. Same for1000000; after501 publications with exactly500 retained (retained_from2,last501), cursor502 → READ_CONFIRMED. These three required failures alone block G0. True/False,0.5/1.0,NaN/+Inf also receive READ_CONFIRMED (six additional strict integer contract failures). Negative integer and -Inf take INSUFFICIENT_EVIDENCE; string raises TypeError.

after_iteration501 and retained_from-1=1 both return the entire500-record retained window, preserving existing behavior. retained_from-2=0 is INSUFFICIENT_EVIDENCE. Missing run BLOCKED; empty history INSUFFICIENT_EVIDENCE; age60s at the declared receiver deadline TIMEOUT.

First attempt: newly added test mistakenly registered one logical node;8 setup ERRORs and exit1, separately retained in current/validation-01 with its original test source/hash. Only the new test changed to two declared logical nodes and was rerun under a new output directory. No reader, original test, scientific threshold or assertion was changed. The first failed setup is not cursor defect acceptance.

No fix made. Retain this required red test unchanged for the later separately approved Gate4 green regression. A successful defect demonstration is not a passing functional gate.
