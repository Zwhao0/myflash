# Candidate and first-observation stability

| Build/batch | Reference fits | Native decision fits | Prefixes | Integrity issues | Native validation errors |
|---|---:|---:|---:|---:|---:|
| B/1 | 640 | 4900 | 6300 | 0 | 0 |
| C/1 | 640 | 4900 | 6300 | 0 | 0 |
| C/2 | 640 | 4900 | 6300 | 0 | 0 |
| B/2 | 640 | 4900 | 6300 | 0 | 0 |

Candidate C decision/native-validity gate: **PASS**.
All seven fixtures have20 complete45-prefix replays per build/batch. Each
real fit uses a new interpreter, original30s timeout and original filtering.
Ten no-fit prefixes/replay use original retained-sample guards, never zeros
or fake fits. Both20% denominators, probability-qualified/filtered cp sets,
candidate presence, first observing iteration and every filter stage remain.
Per-prefix posterior-byte equality is checked across all40 repetitions,
independently of candidate stability. Errors remain distinct from no candidate.

Strong fixture stability does not establish behavior near cpPr0.8, production
false-positive rate, GPU fault precision/recall or paper1–2 iteration latency.
G01/G02/G04/G09/G13/G20 stay OPEN; final_alert=false.
