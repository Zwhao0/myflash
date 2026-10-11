"""PAPER 500-item retention; ADAPTATION confirmed, ordered, run/rank channel."""
import time
from dataclasses import asdict
from flash.iteration_reporter import IterationRecord, validate_sequence, integer
from flash.m6_protocol import digest, event, provisional, identity, number
from flash.m6_store import transaction, Unavailable


class IterationPublisher:
    def __init__(self, store, run_id, rank, *, clock=time.monotonic):
        identity(run_id); integer(rank, 0, 'rank')
        self.store, self.run_id, self.rank, self.clock = store, run_id, rank, clock

    def publish(self, record):
        if not isinstance(record, IterationRecord) or (record.run_id, record.global_rank) != (self.run_id, self.rank):
            raise ValueError('iteration identity mismatch')
        payload = asdict(record)
        confirmed_at = number(self.clock())
        def write(doc):
            if self.rank not in doc['expected_ranks']:
                raise ValueError('undeclared rank')
            stream = doc['iterations'].setdefault(str(self.rank), dict(last=0, records=[]))
            kept = stream['records']
            old = next((r for r in kept if r['record']['iteration'] == record.iteration), None)
            if old:
                status = 'DUPLICATE_CONFIRMED' if old['sha256'] == digest(payload) else 'CONFLICT'
            elif record.iteration <= stream['last']:
                status = 'STALE_OUTSIDE_RETENTION'
            elif record.iteration != stream['last'] + 1:
                status = 'GAP_OR_OUT_OF_ORDER'
            else:
                kept.append(dict(record=payload, sha256=digest(payload), confirmed_at_seconds=confirmed_at))
                stream['records'] = kept[-500:]
                stream['last'] = record.iteration
                status = 'WRITE_CONFIRMED'
            event(doc, 'ITERATION_RECEIPT', rank=self.rank, iteration=record.iteration, status=status)
            return dict(status=status, confirmed=status in ('WRITE_CONFIRMED', 'DUPLICATE_CONFIRMED'),
                        sha256=digest(payload), server_memory_ack=True,
                        disk_or_gpu_completion_proven=False)
        try:
            return transaction(self.store, self.run_id, write)
        except Unavailable as exc:
            return dict(status='WRITE_UNCONFIRMED', confirmed=False, reason=str(exc),
                        sha256=digest(payload), retry='read then exact resubmit; never invent iteration')


class IterationReader:
    def __init__(self, store, run_id, rank):
        identity(run_id); integer(rank, 0, 'rank')
        self.store, self.run_id, self.rank = store, run_id, rank

    def read(self, *, now=None, timeout_seconds=None, after_iteration=None):
        # ADAPTATION: reject invalid cursors before any store access.
        if after_iteration is not None:
            integer(after_iteration, 0, 'after_iteration')
        doc = self.store.read(self.run_id)
        if doc is None:
            return provisional('BLOCKED', 'run state missing/restart')
        stream = doc['iterations'].get(str(self.rank))
        if not stream or not stream['records']:
            return provisional('INSUFFICIENT_EVIDENCE', 'no iteration records')
        records = []
        for item in stream['records']:
            if digest(item['record']) != item['sha256']:
                raise ValueError('iteration data hash mismatch')
            record = IterationRecord(**item['record'])
            if (record.run_id, record.global_rank) != (self.run_id, self.rank):
                raise ValueError('iteration run/rank pollution')
            records.append(record)
        validate_sequence(records)
        if len(records) > 500 or records[-1].iteration != stream['last']:
            raise ValueError('iteration retention/order mismatch')
        if after_iteration is not None and after_iteration > stream['last']:
            return provisional('INSUFFICIENT_EVIDENCE', 'consumer cursor ahead of last confirmed iteration')
        if after_iteration is not None and after_iteration + 1 < records[0].iteration:
            return provisional('INSUFFICIENT_EVIDENCE', 'consumer cursor gap outside 500-item retention')
        if timeout_seconds is not None:
            from flash.m6_protocol import number
            number(timeout_seconds); number(now)
            age = now - stream['records'][-1]['confirmed_at_seconds']
            if age < 0:
                return provisional('BLOCKED', 'iteration receiver clock domain mismatch')
            if age >= timeout_seconds:
                return provisional('TIMEOUT', 'no fresh confirmed iteration within receiver deadline')
        return dict(status='READ_CONFIRMED', records=records, retained_from=records[0].iteration,
                    last=stream['last'], earlier_evicted=records[0].iteration > 1)
