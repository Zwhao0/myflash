# Original unchanged strict assertions

| Build | API exit | Prefix exit | RNG prior independence | Reuse | Correct integer reference |
|---|---:|---:|---|---|---|
| A | 1 | 1 | False | False | False |
| B | 0 | 1 | False | False | False |
| C | 0 | 0 | True | True | True |

C independently generates complete sustained replay, then independently computes
the short prefix using original tests/m5_replay.py bytes. P1 capture wrapper
uses finally to retain globals; original assertions/exceptions propagate.
Source hashes match protocol.json. No slicing to fabricate short execution,
no version monkeypatch, tolerance, skip, xfail or exception-to-exit0.
All first differences and full raw trees are in strict-data.json and data/.
A/B failures remain control results, including B API occasional success.
Native stdout/stderr and actual commands/exits stay in the private run;
validation.json lists sanitized receipts with private evidence references.
