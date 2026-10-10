"""ADAPTATION M6-A v1; PAPER constants from SPEC S2/S4. CPU control only."""
import hashlib
import json
import math
import re

SCHEMA_VERSION = 1
STATES = ('MONITOR', 'PROFILE_REQUESTED', 'PROFILE_ARMING', 'PROFILE_COLLECTING',
          'PROFILE_DRAINING', 'PROFILE_READY', 'ANALYZED_PROVISIONAL',
          'MONITOR_RESET_REQUESTED', 'BLOCKED')
FAILURES = ('INCOMPLETE', 'TIMEOUT', 'ABORTED', 'STALE', 'BLOCKED')
MAX_EPOCHS, MAX_EVENTS, MAX_BYTES = 100, 10000, 8 * 1024 * 1024


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise ValueError('invalid identity')
    return value


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite nonnegative time required')
    return value


def window_seconds(record):
    # PAPER §3.2.3 pp27–29. No reinterpretation of completion boundary.
    if record is None or record.timing_boundary not in ('cpu_simulated_iteration_end',
                                                       'after_optimizer_cuda_complete'):
        raise ValueError('missing/unknown completed iteration boundary')
    if record.timing_boundary == 'after_optimizer_cuda_complete' and not record.cuda_completion_wait:
        raise ValueError('CUDA completion not evidenced')
    return max(record.iteration_time_ms / 1000 * 2.2, 20.0)


def event(doc, kind, **fields):
    if len(doc['events']) >= MAX_EVENTS:
        raise ValueError('evidence capacity exhausted; new run required')
    doc['events'].append(dict(sequence=len(doc['events']) + 1, kind=kind, **fields))


def provisional(status, reason=None):
    return dict(status=status, reason=reason, final_alert=False, final_fault_ranks=[])


def registration(run_id, nodes):
    identity(run_id)
    if len(nodes) != 2:
        raise ValueError('M6-A requires two explicitly declared logical nodes')
    ranks = []
    for node, values in nodes.items():
        identity(node)
        if not values or any(type(r) is not int or r < 0 for r in values):
            raise ValueError('invalid expected ranks')
        ranks.extend(values)
    if len(set(ranks)) != len(ranks) or 0 not in ranks:
        raise ValueError('duplicate ranks or missing rank0')
    return dict(schema_version=SCHEMA_VERSION, run_id=run_id, revision=0,
                expected_nodes=sorted(nodes), expected_ranks=sorted(ranks),
                nodes={n: dict(ranks=sorted(v), generation=0) for n, v in nodes.items()},
                global_generation=0, profile_epoch=0, state='MONITOR', active=None,
                epochs=[], events=[], iterations={}, final_alert=False, final_fault_ranks=[])
