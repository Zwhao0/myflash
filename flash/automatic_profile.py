"""ADAPTATION TASK12 durable decision/intent -> cursor ACK -> idempotent request.

No worker, native fit, Redis connection or production switch is started here.
One caller owns the consumer and this ledger. CPU adapters require explicit
simulation selection; real C selection retains the existing identity guard.
"""
import copy
from dataclasses import asdict
import json

from flash.change_detection import detect, DetectionConfig, APPROVED_RULES_VERSION, APPROVED_PACKET_HEAD
from flash.iteration_outbox import _Ledger
from flash.iteration_reporter import IterationRecord, integer, validate_sequence
from flash.m6_protocol import digest, encode, provisional, StaleOwner, number
from flash.m6_store import Unavailable
from flash.rbeast_adapter import RbeastAdapter, CANDIDATE_C_SHA256, PARAMETERS

AUTO_TRIGGER = 'DETECTOR_AUTOMATIC_V1'
REQUEST_VERSION = 'flash.profile.automatic.v1'
RULES = dict(G01='a', G02='inclusive_span', G13='A')


def logical_request_id(body):
    # Native diagnostics/refit randomness and controller generation cannot mint
    # a second logical ID for one confirmed iteration and approved rule version.
    return 'auto-' + digest(dict(interface_version=REQUEST_VERSION, run_id=body['run_id'],
                                record_sha256=digest(body['record']),
                                detector_version=APPROVED_RULES_VERSION,
                                approved_packet_head=APPROVED_PACKET_HEAD,
                                expected_c_sha256=CANDIDATE_C_SHA256))


def request_for(record, decision, manifest, mode):
    body = dict(interface_version=REQUEST_VERSION, run_id=record.run_id,
                record=asdict(record), decision=copy.deepcopy(decision),
                manifest=copy.deepcopy(manifest), adapter_mode=mode,
                expected_c_sha256=CANDIDATE_C_SHA256)
    body['request_id'] = logical_request_id(body)
    return body


def validate_request(request, run):
    if not isinstance(request, dict) or set(request) != {
            'interface_version', 'run_id', 'record', 'decision', 'manifest',
            'adapter_mode', 'expected_c_sha256', 'request_id'}:
        raise ValueError('automatic v1 request fields mismatch')
    record = IterationRecord(**request['record'])
    decision = request['decision']
    inputs = [IterationRecord(**r) for r in decision.get('input', [])]
    validate_sequence(inputs)
    engine = decision.get('engine') or {}
    if (request['interface_version'] != REQUEST_VERSION or request['run_id'] != run or
            (record.run_id, record.global_rank) != (run, 0) or
            request['expected_c_sha256'] != CANDIDATE_C_SHA256 or
            request['adapter_mode'] not in ('CPU_SIMULATION', 'C_IDENTITY_GUARDED') or
            decision.get('interface_version') != APPROVED_RULES_VERSION or
            decision.get('approved_packet_head') != APPROVED_PACKET_HEAD or
            decision.get('approved_rules') != RULES or
            decision.get('config') != asdict(DetectionConfig()) or
            engine.get('status') != 'OK' or engine.get('parameters') != PARAMETERS or
            len(inputs) > 30 or any((r.run_id, r.global_rank) != (run, 0) for r in inputs) or
            decision.get('latest_iteration') != record.iteration or
            decision.get('status') != 'DETECTION_TRIGGERED' or
            decision.get('detection_trigger') is not True or
            decision.get('final_alert') is not False or
            not decision.get('input') or decision['input'][-1] != request['record'] or
            not any(c.get('detection_trigger') is True for c in decision.get('candidates', []))):
        raise ValueError('formal approved detection_trigger required')
    if request['adapter_mode'] == 'C_IDENTITY_GUARDED':
        if (engine.get('runtime_selection') != 'candidate-c-opt-in' or
                (engine.get('runtime_identity') or {}).get('native_sha256') != CANDIDATE_C_SHA256):
            raise ValueError('specified C identity not evidenced')
    if request['request_id'] != logical_request_id(request):
        raise ValueError('automatic request_id/content mismatch')


class DurableAutomaticProfiler(_Ledger):
    """Opt-in single-owner synchronous dispatcher, bounded to max_decisions.

    Uses a separate SQLite ledger. Decision+intent share ONE local transaction;
    the unchanged consumer ACK follows it. Unknown remote outcomes keep intent.
    Successful remote ACK is server-memory evidence only. No cross-store atomic
    or exactly-once execution claim. Capacity/unknown outcomes impose backpressure.
    """
    def __init__(self, path, consumer, controller, manifest, *, adapter,
                 approved_rules, cpu_simulation=False, max_decisions=500):
        if approved_rules is not True or type(cpu_simulation) is not bool:
            raise ValueError('explicit approved rules and simulation selection required')
        integer(max_decisions, 1, 'max_decisions')
        if (consumer.rank != 0 or consumer.run_id != controller.run_id or
                consumer.reader.store is not controller.store):
            raise ValueError('confirmed rank0 consumer/controller scope mismatch')
        if cpu_simulation:
            if isinstance(adapter, RbeastAdapter):
                raise ValueError('CPU simulation cannot select native adapter')
            mode = 'CPU_SIMULATION'
        else:
            if type(adapter) is not RbeastAdapter or adapter.candidate_c_python is None:
                raise ValueError('explicit identity-guarded C adapter required')
            mode = 'C_IDENTITY_GUARDED'
        self.consumer, self.controller, self.adapter = consumer, controller, adapter
        self.manifest, self.mode, self.max_decisions = copy.deepcopy(manifest), mode, max_decisions
        binding = dict(consumer_path=str(consumer.path.absolute()), manifest=self.manifest,
                       mode=mode, c_sha256=CANDIDATE_C_SHA256, rules=RULES,
                       candidate_c_python=getattr(adapter, 'candidate_c_python', None),
                       max_decisions=max_decisions)
        super().__init__(path, consumer.run_id, 0, 'automatic-v1-' + digest(binding))
        try:
            self._rows()
        except BaseException:
            self.close()
            raise

    def _rows(self):
        result = []
        for iteration, payload, sha in self.db.execute(
                'SELECT iteration,payload,sha256 FROM records ORDER BY iteration'):
            row = json.loads(payload)
            if digest(row) != sha or encode(row) != payload:
                raise ValueError('automatic ledger hash/canonical content mismatch')
            record = IterationRecord(**row['record'])
            if (record.run_id, record.global_rank, record.iteration) != (self.run_id, 0, iteration):
                raise ValueError('automatic ledger record scope mismatch')
            if row['request'] is not None:
                validate_request(row['request'], self.run_id)
                if (row['request']['record'] != row['record'] or
                        row['request']['decision'] != row['decision'] or
                        row['request']['manifest'] != self.manifest or
                        row['request']['adapter_mode'] != self.mode):
                    raise ValueError('automatic intent/decision binding mismatch')
            elif row['decision'].get('detection_trigger') is True:
                raise ValueError('trigger decision missing durable intent')
            if type(row['processable']) is not bool:
                raise ValueError('automatic ledger processable flag invalid')
            receipt = row['receipt']
            if receipt is not None:
                if (row['request'] is None or not row['processable'] or
                        receipt.get('status') not in ('PROFILE_REQUESTED', 'DUPLICATE_CONFIRMED') or
                        receipt.get('request_id') != row['request']['request_id'] or
                        receipt.get('request_sha256') != digest(row['request']) or
                        receipt.get('server_memory_ack') is not True or self.consumer.position < iteration):
                    raise ValueError('automatic ledger receipt/intent mismatch')
                integer(receipt['profile_epoch'], 1, 'profile_epoch')
            result.append(row)
        if len(result) != self.position or len(result) > self.max_decisions:
            raise ValueError('automatic ledger position/capacity mismatch')
        if [r['record']['iteration'] for r in result] != list(range(1, self.position + 1)):
            raise ValueError('automatic ledger gap')
        if self.consumer.position not in (self.position, max(0, self.position - 1)):
            raise ValueError('consumer cursor not covered by durable decisions')
        return result

    def _save(self, row):
        payload = encode(row)
        self.db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)',
                        (row['record']['iteration'], payload, digest(row)))

    def _persist(self, record, decision, request, processable):
        # The fault tests crash before/after this transaction; no cursor is
        # touched here. Full input and request manifest are frozen for replay.
        with self._transaction():
            if self.position + 1 != record.iteration:
                raise ValueError('decision order changed; single owner required')
            row = dict(record=asdict(record), decision=decision, request=request,
                       processable=processable, receipt=None)
            self._save(row)
            self.db.execute('UPDATE metadata SET position=? WHERE singleton=1', (record.iteration,))
        return row

    def _dispatch(self, row, now):
        result = self.controller.start_automatic_v1(row['request'], now)
        if result['status'] not in ('PROFILE_REQUESTED', 'DUPLICATE_CONFIRMED'):
            return provisional('BLOCKED', 'intent retained: ' + str(result))
        integer(result['profile_epoch'], 1, 'profile_epoch')
        # ACK has to bind the exact logical request and epoch; a crash before
        # this save causes an exact resend and remote deduplication.
        with self._transaction():
            row['receipt'] = dict(result, request_id=row['request']['request_id'],
                                  request_sha256=digest(row['request']), server_memory_ack=True)
            self._save(row)
        return row['receipt']

    def step(self, now):
        """At most one new iteration/refit and one automatic submission per call.

        No deletion or implicit skip/retry of a frozen failed Detector decision.
        Repeated prefix triggers are separate intents, not coalesced episodes.
        """
        number(now)
        try:
            rows = self._rows()
            doc = self.controller.store.read(self.run_id)
            if doc is None:
                return provisional('BLOCKED', 'run document missing; intents retained')
            self.controller._owned(doc)
            # Detect loss of already ACKed server-memory request evidence.
            epochs = doc['epochs'] + ([doc['active']] if doc['active'] else [])
            for row in rows:
                if row['receipt'] and not any(
                        e['request_id'] == row['request']['request_id'] and
                        e['request_sha256'] == digest(row['request']) and
                        e['profile_epoch'] == row['receipt']['profile_epoch'] for e in epochs):
                    return provisional('BLOCKED', 'accepted request evidence lost; operator reconciliation required')
            if rows and not rows[-1]['processable']:
                return provisional('BLOCKED', 'frozen Detector failure; cursor unacknowledged')
            # Crash between decision/intent COMMIT and consumer ACK: poll and
            # prove the same confirmed record, then ACK without another refit.
            if self.consumer.position < self.position:
                delivery = self.consumer.poll()
                if delivery['status'] != 'READ_CONFIRMED' or not delivery['records']:
                    return provisional('BLOCKED', 'cannot re-prove pending cursor record')
                record = delivery['records'][0]
                if asdict(record) != rows[-1]['record']:
                    return provisional('BLOCKED', 'pending cursor record changed')
                self.consumer.commit([record])
            for row in rows:
                if row['request'] is not None and row['receipt'] is None:
                    return self._dispatch(row, now)
            if self.position >= self.max_decisions:
                return provisional('BLOCKED', 'decision capacity reached; archive/new run; cursor retained')
            delivery = self.consumer.poll()
            if delivery['status'] != 'READ_CONFIRMED':
                return delivery
            if not delivery['records']:
                return provisional('IDLE', 'no new confirmed iteration')
            record = delivery['records'][0]
            # Keep at most 30 original iteration records; preprocessing/window
            # and all thresholds remain the existing approved Detector's job.
            prefix = [IterationRecord(**row['record']) for row in rows[-29:]] + [record]
            decision = detect(prefix, self.adapter, approved_rules=True)
            engine = decision.get('engine')
            processable = (decision['status'] in ('NO_DETECTION_TRIGGER', 'DETECTION_TRIGGERED',
                                                 'INSUFFICIENT_EVIDENCE') and
                           (engine is None or engine.get('status') == 'OK') and
                           not str(decision.get('reason', '')).startswith('INVALID_NATIVE_OR_ARITHMETIC'))
            request = (request_for(record, decision, self.manifest, self.mode)
                       if decision['detection_trigger'] is True else None)
            if request is not None:
                validate_request(request, self.run_id)
            row = self._persist(record, decision, request, processable)
            if not processable:
                return provisional('BLOCKED', 'Detector failure saved; cursor unacknowledged')
            self.consumer.commit([record])
            return (self._dispatch(row, now) if request is not None else
                    dict(status='DECISION_ACKNOWLEDGED', iteration=record.iteration,
                         detection_trigger=False, final_alert=False, final_fault_ranks=[]))
        except (Unavailable, StaleOwner) as error:
            return provisional('BLOCKED', str(error) + '; intent/cursor recovery required')
