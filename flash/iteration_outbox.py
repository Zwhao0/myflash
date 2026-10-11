"""ADAPTATION G20 local durability and explicit consumer acknowledgement.

CPU contract: original MemoryStore/IterationPublisher/IterationReader unchanged.
SQLite transactions persist records before transport and cursor after processing.
Remote ACK proves server memory only. No CUDA, Redis disk or exactly-once effects.
"""
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3

from flash.iteration_reporter import IterationRecord, confirmed_receipt, integer, validate_sequence
from flash.m6_iteration import IterationPublisher, IterationReader
from flash.m6_protocol import digest, encode, identity
from flash.m6_store import Unavailable


def _index(value):
    integer(value, 0, 'durable iteration')
    if value > 2**63 - 1:
        raise ValueError('durable iteration exceeds SQLite integer range')


def _unconfirmed(record, status, reason):
    return dict(status=status, confirmed=False, sha256=digest(asdict(record)), reason=reason,
                server_memory_ack=False, disk_or_gpu_completion_proven=False)


class _Ledger:
    """One owned local path, scope bound, serialized transactions, finite lock wait.

    Existing malformed/incomplete databases are refused, never rebuilt silently.
    New directory must already exist; journal/database stay inside that directory.
    """
    def __init__(self, path, run_id, rank, kind):
        identity(run_id); integer(rank, 0, 'rank'); _index(rank)
        self.path = Path(path)
        self.run_id, self.rank = run_id, rank
        fresh = False
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError('ledger must be an owned regular file')
        else:
            os.close(fd); fresh = True
        self.db = sqlite3.connect(str(self.path), timeout=1, isolation_level=None)
        try:
            if self.db.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                raise ValueError('DELETE journal required')
            self.db.execute('PRAGMA synchronous=EXTRA')
            self.db.execute('PRAGMA fullfsync=ON')
            if self.db.execute('PRAGMA synchronous').fetchone()[0] != 3:
                raise ValueError('EXTRA synchronous required')
            if fresh:
                with self._transaction():
                    self.db.execute('CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
                                    'schema INTEGER, kind TEXT, run TEXT, rank INTEGER, position INTEGER)')
                    self.db.execute('CREATE TABLE records (iteration INTEGER PRIMARY KEY, payload TEXT, sha256 TEXT)')
                    self.db.execute('INSERT INTO metadata VALUES (1,1,?,?,?,0)', (kind, run_id, rank))
                directory = os.open(self.path.parent, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            if self.db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError('ledger integrity check failed')
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            if tables != [('metadata',), ('records',)]:
                raise ValueError('ledger schema mismatch')
            rows = self.db.execute('SELECT singleton,schema,kind,run,rank,position FROM metadata').fetchall()
            if len(rows) != 1 or rows[0][:5] != (1, 1, kind, run_id, rank):
                raise ValueError('ledger scope/schema mismatch')
            _index(rows[0][5])
        except BaseException:
            self.db.close()
            raise

    @contextmanager
    def _transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    @property
    def position(self):
        value = self.db.execute('SELECT position FROM metadata WHERE singleton=1').fetchone()[0]
        _index(value)
        return value

    def close(self):
        self.db.close()

    def _record(self, row):
        iteration, payload, sha = row
        record = IterationRecord(**json.loads(payload))
        if (record.run_id, record.global_rank, record.iteration) != (self.run_id, self.rank, iteration):
            raise ValueError('outbox record identity mismatch')
        if digest(asdict(record)) != sha or encode(asdict(record)) != payload:
            raise ValueError('outbox record hash/canonical payload mismatch')
        return record


class DurableIterationOutbox(_Ledger):
    """500 ACKed records plus at most one pending record; never evict pending.

    publish(record) is Reporter-compatible. recover() replays frozen pending on
    restart; next_iteration is for explicit framework resume, never inferred work.
    No worker/retry timer: each invocation attempts one read and at most one write.
    """
    def __init__(self, path, store, run_id, rank, *, clock=None):
        super().__init__(path, run_id, rank, 'outbox')
        self.reader = IterationReader(store, run_id, rank)
        kwargs = {} if clock is None else dict(clock=clock)
        self.publisher = IterationPublisher(store, run_id, rank, **kwargs)
        try: self._validate()
        except BaseException:
            self.close(); raise

    def _validate(self):
        with self._transaction():
            ack = self.position
            rows = self.db.execute('SELECT iteration,payload,sha256 FROM records ORDER BY iteration').fetchall()
            records = validate_sequence([self._record(row) for row in rows])
            expected_start = max(1, ack - 499)
            if (len(records) > 501 or (ack and not records) or
                    (records and (records[0].iteration != expected_start or
                     records[-1].iteration not in (ack, ack + 1)))):
                raise ValueError('outbox retention/watermark mismatch')

    @property
    def pending(self):
        self._validate()
        row = self.db.execute('SELECT iteration,payload,sha256 FROM records WHERE iteration>?',
                              (self.position,)).fetchone()
        return None if row is None else self._record(row)

    @property
    def next_iteration(self):
        pending = self.pending
        return self.position + 1 if pending is None else pending.iteration

    def enqueue(self, record):
        if not isinstance(record, IterationRecord) or (record.run_id, record.global_rank) != (self.run_id, self.rank):
            raise ValueError('outbox record identity mismatch')
        _index(record.iteration)
        self._validate()
        with self._transaction():
            row = self.db.execute('SELECT iteration,payload,sha256 FROM records WHERE iteration=?',
                                  (record.iteration,)).fetchone()
            if row is not None:
                if self._record(row) != record or row[2] != digest(asdict(record)):
                    raise ValueError('outbox conflicting resubmission')
            else:
                if record.iteration != self.position + 1:
                    raise ValueError('outbox gap/stale/out-of-order iteration')
                if self.db.execute('SELECT 1 FROM records WHERE iteration>?', (self.position,)).fetchone():
                    raise ValueError('outbox pending record must be resolved first')
                self.db.execute('INSERT INTO records VALUES (?,?,?)',
                                (record.iteration, encode(asdict(record)), digest(asdict(record))))

    def _acknowledge(self, record, receipt):
        if not confirmed_receipt(record, receipt):
            if (isinstance(receipt, dict) and receipt.get('confirmed') is False and
                    receipt.get('sha256') == digest(asdict(record)) and
                    receipt.get('status') in ('WRITE_UNCONFIRMED', 'CONFLICT',
                        'STALE_OUTSIDE_RETENTION', 'GAP_OR_OUT_OF_ORDER')):
                return receipt
            return _unconfirmed(record, 'WRITE_UNCONFIRMED', 'publisher ACK missing/invalid; pending retained')
        with self._transaction():
            row = self.db.execute('SELECT iteration,payload,sha256 FROM records WHERE iteration=?',
                                  (record.iteration,)).fetchone()
            if row is None or self._record(row) != record:
                raise ValueError('acknowledgement missing/conflicting local record')
            ack = self.position
            if record.iteration > ack:
                if record.iteration != ack + 1:
                    raise ValueError('acknowledgement order mismatch')
                self.db.execute('UPDATE metadata SET position=? WHERE singleton=1', (record.iteration,))
                self.db.execute('DELETE FROM records WHERE iteration<=?', (record.iteration - 500,))
        return receipt

    def _resolve(self, record):
        try:
            result = self.reader.read()
        except Unavailable as exc:
            return _unconfirmed(record, 'WRITE_UNCONFIRMED', str(exc))
        if result['status'] == 'BLOCKED':
            return _unconfirmed(record, 'BLOCKED', result['reason'])
        if result['status'] == 'READ_CONFIRMED':
            match = next((r for r in result['records'] if r.iteration == record.iteration), None)
            if match is not None:
                if digest(asdict(match)) != digest(asdict(record)):
                    return _unconfirmed(record, 'CONFLICT', 'remote record differs; pending retained')
                receipt = dict(status='DUPLICATE_CONFIRMED', confirmed=True, sha256=digest(asdict(record)),
                               server_memory_ack=True, disk_or_gpu_completion_proven=False,
                               evidence='exact retained record read')
                return self._acknowledge(record, receipt)
            if record.iteration <= result['last']:
                return _unconfirmed(record, 'STALE_OUTSIDE_RETENTION', 'cannot prove evicted unknown result')
        receipt = self.publisher.publish(record)
        return self._acknowledge(record, receipt)

    def publish(self, record):
        self.enqueue(record)
        return self._resolve(record)

    def recover(self):
        record = self.pending
        return None if record is None else self._resolve(record)


class DurableIterationConsumer(_Ledger):
    """Persist cursor only after explicit successful application processing.

    poll uses unchanged Reader full-window contract then selects new records.
    commit acknowledges a delivered prefix only. Crash before commit redelivers.
    Cursor is separate from publisher ACK and cannot be seeded/skipped forwards.
    """
    def __init__(self, path, store, run_id, rank):
        super().__init__(path, run_id, rank, 'consumer')
        self.reader = IterationReader(store, run_id, rank)
        self.delivery = None
        if self.db.execute('SELECT COUNT(*) FROM records').fetchone()[0] != 0:
            self.close(); raise ValueError('consumer ledger contains outbox records')

    def poll(self, **kwargs):
        self.delivery = None
        cursor = self.position
        result = self.reader.read(after_iteration=cursor, **kwargs)
        if result['status'] != 'READ_CONFIRMED':
            return result
        records = [r for r in result['records'] if r.iteration > cursor]
        self.delivery = (cursor, tuple(records))
        return dict(result, records=records, consumer_cursor=cursor)

    def commit(self, records):
        if not isinstance(records, (list, tuple)) or not records or self.delivery is None:
            raise ValueError('nonempty delivered prefix required')
        before, delivered = self.delivery
        records = tuple(records)
        if (len(records) > len(delivered) or
                any(not isinstance(r, IterationRecord) for r in records) or
                [digest(asdict(r)) for r in records] != [digest(asdict(r)) for r in delivered[:len(records)]] or
                records[0].iteration != before + 1):
            raise ValueError('consumer cannot skip/change/commit unseen records')
        with self._transaction():
            if self.position != before:
                raise ValueError('consumer cursor changed; poll again')
            self.db.execute('UPDATE metadata SET position=? WHERE singleton=1', (records[-1].iteration,))
        self.delivery = None
        return self.position
