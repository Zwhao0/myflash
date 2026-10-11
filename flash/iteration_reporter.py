"""PAPER iteration-end reporting; ADAPTATION strict local, bounded persistence.
No torch import or CUDA synchronization unless a framework explicitly supplies it.
"""
import datetime
import hashlib
import json
import math
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


def integer(value, minimum, field):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid ' + field)


@dataclass(frozen=True)
class IterationRecord:
    run_id: str
    global_rank: int
    iteration: int
    iteration_time_ms: float
    timestamp: str
    source: str
    timing_boundary: str
    cuda_completion_wait: bool

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.run_id):
            raise ValueError('invalid run_id')
        integer(self.global_rank, 0, 'global_rank')
        integer(self.iteration, 1, 'iteration (one-based)')
        if (type(self.iteration_time_ms) not in (int, float) or
                not math.isfinite(self.iteration_time_ms) or self.iteration_time_ms <= 0):
            raise ValueError('iteration_time_ms must be finite and positive')
        try:
            stamp = datetime.datetime.fromisoformat(self.timestamp)
            if stamp.utcoffset() is None:
                raise ValueError('timezone required')
        except (ValueError, TypeError):
            raise ValueError('invalid timestamp') from None
        if any(not isinstance(x, str) or not x.strip() for x in (self.source, self.timing_boundary)):
            raise ValueError('source and timing boundary required')
        if type(self.cuda_completion_wait) is not bool:
            raise ValueError('explicit CUDA completion semantics required')


class Publisher(Protocol):
    """M6 may implement Redis publication of a completed record; no connection here."""
    def publish(self, record: IterationRecord) -> object: ...


class PublicationUnconfirmed(RuntimeError):
    """Completed record retained; retry end() without recomputing timing."""
    def __init__(self, record, receipt):
        super().__init__('iteration publication not confirmed')
        self.record, self.receipt = record, receipt


def confirmed_receipt(record, receipt, *, legacy_none=False):
    """ADAPTATION exact M6 ACK contract; None only for legacy local sinks."""
    if receipt is None:
        return legacy_none
    payload = json.dumps(asdict(record), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return (isinstance(receipt, dict) and receipt.get('confirmed') is True and
            receipt.get('status') in ('WRITE_CONFIRMED', 'DUPLICATE_CONFIRMED') and
            receipt.get('sha256') == hashlib.sha256(payload.encode()).hexdigest() and
            receipt.get('server_memory_ack') is True)


def validate_sequence(records):
    """Reject, never sort away publication order defects or fill gaps."""
    previous = None
    for record in records:
        if not isinstance(record, IterationRecord):
            raise ValueError('IterationRecord required')
        if previous:
            if (record.run_id, record.global_rank) != (previous.run_id, previous.global_rank):
                raise ValueError('mixed run or rank')
            if record.iteration != previous.iteration + 1:
                raise ValueError('missing, duplicate or out-of-order iteration')
        previous = record
    return records


class LocalHistory:
    """Single-writer per run/rank. Atomic replace; storage work excluded from timing."""
    def __init__(self, path, run_id, global_rank, limit=500):
        integer(limit, 1, 'limit')
        if limit > 500:
            raise ValueError('maximum history is 500')
        integer(global_rank, 0, 'global_rank')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id):
            raise ValueError('invalid run_id')
        self.path = Path(path)
        self.run_id, self.global_rank, self.limit = run_id, global_rank, limit
        self.records = self.load(self.path) if self.path.exists() else []
        if len(self.records) > limit or any((r.run_id, r.global_rank) != (run_id, global_rank) for r in self.records):
            raise ValueError('history scope/limit mismatch')

    @staticmethod
    def load(path):
        raw = json.loads(Path(path).read_text())
        if raw.get('schema') != 1 or not isinstance(raw.get('records'), list) or len(raw['records']) > 500:
            raise ValueError('invalid history schema')
        return validate_sequence([IterationRecord(**r) for r in raw['records']])

    def publish(self, record):
        if (record.run_id, record.global_rank) != (self.run_id, self.global_rank):
            raise ValueError('history scope mismatch')
        validate_sequence(self.records[-1:] + [record])
        if not self.records and record.iteration != 1:
            raise ValueError('new history must begin with iteration 1')
        updated = (self.records + [record])[-self.limit:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.tmp')
        with temporary.open('x') as stream:
            os.chmod(temporary, 0o600)
            json.dump({'schema': 1, 'records': [asdict(r) for r in updated]}, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        self.records = updated


class IterationReporter:
    """Explicit begin/end framework callback, no periodic inferred iterations.

    begin: after optional CUDA drain, before measured data/compute work.
    end: after optimizer and optional CUDA completion wait, before publication.
    A failed body must abort; it must never publish a completed iteration.
    """
    def __init__(self, publisher, run_id, global_rank, *, source, timing_boundary,
                 completion_wait=None, clock=time.perf_counter_ns):
        self.publisher, self.run_id, self.global_rank = publisher, run_id, global_rank
        self.source, self.timing_boundary = source, timing_boundary
        self.completion_wait, self.clock = completion_wait, clock
        self.active = None
        self.pending = None

    def begin(self, iteration):
        integer(iteration, 1, 'iteration')
        if self.active is not None:
            raise ValueError('iteration already active')
        if self.completion_wait:
            self.completion_wait()
        self.active = (iteration, self.clock())

    def abort(self):
        if self.pending is not None:
            raise ValueError('completed unconfirmed iteration cannot be aborted; retry end')
        self.active = None

    def end(self):
        if self.active is None:
            raise ValueError('no active iteration')
        if self.pending is None:
            if self.completion_wait:
                self.completion_wait()
            iteration, start = self.active
            elapsed = (self.clock() - start) / 1_000_000
            self.pending = IterationRecord(self.run_id, self.global_rank, iteration, elapsed,
                                 datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 self.source, self.timing_boundary, self.completion_wait is not None)
        record = self.pending
        receipt = self.publisher.publish(record)
        if not confirmed_receipt(record, receipt, legacy_none=True):
            raise PublicationUnconfirmed(record, receipt)
        self.active = None
        self.pending = None
        return record
