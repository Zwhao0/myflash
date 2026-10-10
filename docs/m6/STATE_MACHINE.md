# M6-A state machine

All distributed control detail here is ADAPTATION; manual/CPU virtual scope inputs
are EXTENSION. PAPER supplies 0/1 and window, not this state machine.

| State | Advance evidence | Fail closed |
|---|---|---|
| MONITOR | registration and fresh confirmed rank0 iteration + manual request | unknown boundary/missing iteration => insufficient; no epoch |
| PROFILE_REQUESTED | every expected node ACK of exact command | missing/late node => TIMEOUT |
| PROFILE_ARMING | every rank actual Profile scope with current command/fences | ACK/header alone insufficient; absent rank => TIMEOUT |
| PROFILE_COLLECTING | full max(ms/1000×2.2,20s) expires | no shortened window; stream/comm/timing failure => INCOMPLETE |
| PROFILE_DRAINING | all node drain hashes/receipts present before deadline | missing node/data => TIMEOUT; bad hash/schema => INCOMPLETE |
| PROFILE_READY | unchanged M4 strict validation + saved provisional evidence | no localization on incomplete data |
| ANALYZED_PROVISIONAL | result saved with no final alert; issue Monitor command | scientific gaps never closed |
| MONITOR_RESET_REQUESTED | all nodes ACK AND every rank fresh Monitor boundary | partial reset => TIMEOUT and BLOCKED |
| MONITOR | append complete epoch receipt; next epoch allowed | old data/messages never replenish next round |

Successful trace retains every named state. Failure stores first failure with
reason and requests reset; result still records INCOMPLETE/TIMEOUT/ABORTED even
if Monitor reset succeeds. STALE owners receive fencing errors and cannot alter
current run. BLOCKED retains active failure, partial evidence and explicit operator
condition; it cannot be silently converted into Monitor. Source errors are not
fixed by filling zero, dropping a node or changing expected sample counts.

ADAPTATION deadlines: control ACK/arming/drain allowance 5s; reset 5s; receiver
iteration freshness 60s (configurable positive finite engineering deadlines,
not scientific thresholds). The sampling duration is fixed PAPER and unaffected.
All clocks in M6-A are one-host CPU seconds. Virtual-clock tests advance time but
make no physical duration/performance claims. Cross-host monotonic clocks are
unsupported. Nodes and controllers restart by ownership claim; active round is
invalidated and new reset fences required. Restart during partial reset retains
prior attempt and requires new boundary proofs, even if physical rank already
looks Monitor. No disk or failover recovery is promised.
