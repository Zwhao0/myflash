"""ADAPTATION TASK09 opt-in bridge, CPU-tested only; no native/GPU claim.

Same-project sources at PR19 b082d169: Reader, ABI2 request/boundary/read,
M6 fenced controllers and strict M4 validation. Native ABI and defaults unchanged.
The caller supplies already-owned Reader objects; discovery/unlink is not here.
Receive times share ONE host clock. Durable raw persistence is not provided.
"""
import copy
from flash.iteration_reporter import IterationReporter, PublicationUnconfirmed, confirmed_receipt
from flash.reader import API
from flash.m6_protocol import digest, number, provisional, StaleOwner
from flash.m6_controller import GlobalController, LocalController, _failed
from flash.m6_store import transaction, Unavailable
from flash.profile_input import InputError, require, validate_bundle
from flash.localization import analyze_approved_g04

SOURCE = 'CPU_ABI2_READER_BRIDGE'
BOUNDARY = 'abi2_fresh_scope_record'
LIMIT = 4096
COUNTERS = ('dropped_full', 'dropped_lock', 'errors', 'bad_records')


class StrictAckPublisher:
    """Explicit selection; None and unconfirmed ACK never reach legacy success."""
    def __init__(self, publisher):
        self.publisher = publisher

    def publish(self, record):
        receipt = self.publisher.publish(record)
        if not confirmed_receipt(record, receipt, legacy_none=False):
            raise PublicationUnconfirmed(record, receipt)
        return receipt


def strict_reporter(publisher, run_id, rank, **kwargs):
    return IterationReporter(StrictAckPublisher(publisher), run_id, rank, **kwargs)


def uint(value, field, minimum=0):
    require(type(value) is int and value >= minimum, 'invalid ABI2 ' + field)
    return value


def raw_valid(raw, run, node, rank, pid):
    require(all(raw.get(k) == v for k, v in dict(run_id=run, node_id=node,
            global_rank=rank, pid=pid).items()), 'ABI2 record identity mismatch')
    for field in ('publish_seq', 'call_seq', 'timestamp_ns', 'thread_id', 'comm_ptr',
                  'comm_generation', 'count', 'group_id', 'group_depth', 'stream_ptr',
                  'state', 'profile_epoch', 'api', 'identity'):
        uint(raw[field], field, 1 if field == 'publish_seq' else 0)
    require(raw['state'] in (0, 1) and raw['api'] in API, 'ABI2 record enum mismatch')
    require(not any(k in raw for k in ('truth', 'target_rank', 'fault_label', 'expected_result')),
            'truth prohibited')
    require(raw['record_digest'] == digest({k: v for k, v in raw.items() if k != 'record_digest'}),
            'ABI2 record digest mismatch')


def scope_record(raw):
    # A fresh successful standalone collective or outer GroupStart is actual
    # evidence of a legal application boundary in the unchanged native Probe.
    return (type(raw.get('result')) is int and raw['result'] == 0 and
            ((1 <= raw['api'] <= 8 and raw['group_id'] == 0 and raw['group_depth'] == 0) or
             (raw['api'] == 20 and raw['group_id'] > 0 and raw['group_depth'] == 1)))


def normalize(raw):
    """Same-project read_records m3_ndjson field mapping; preserve us/elements."""
    require(1 <= raw['api'] <= 8, 'Profile collective required')
    require(raw['identity'] == 1 and raw['identity_source'] == 'UNIQUE_ID_SHA256',
            'unreliable ABI2 communicator identity')
    return dict(run_id=raw['run_id'], node_id=raw['node_id'], global_rank=raw['global_rank'],
        profile_epoch=raw['profile_epoch'], process_instance=str(raw['pid']),
        id_hash=raw['id_hash'], comm_generation=raw['comm_generation'],
        comm_rank=raw['comm_rank'], comm_size=raw['comm_size'], identity_source=raw['identity_source'],
        timing_scope={0: 'none', 1: 'collective', 2: 'group_shared'}.get(raw['timing_scope']),
        timing_status={0: 'NOT_APPLICABLE', 1: 'VALID', 2: 'UNSUPPORTED', 3: 'INVALID_DURATION'}.get(raw['timing_status']),
        duration_us=raw['duration_us'], duration_unit='us', timing_definition='m3_cuda_event_v2',
        state=raw['state'], api=API[raw['api']], count=raw['count'], count_unit=raw['count_unit'],
        datatype=raw['datatype'], group_id=raw['group_id'], group_depth=raw['group_depth'],
        thread_id=str(raw['thread_id']), sample_seq=raw['publish_seq'], result=raw['result'],
        cuda_results=copy.deepcopy(raw['cuda_results']))


class Abi2ProbeAdapter:
    source = SOURCE

    def __init__(self, run_id, node_id, readers, fence, *, scope_threads):
        require(bool(readers), 'explicit per-rank Readers required')
        self.run_id, self.node_id, self.readers, self.fence = run_id, node_id, dict(readers), fence
        self.ranks = set(readers)
        require(set(scope_threads) == self.ranks, 'explicit single scope thread per rank required')
        self.scope_threads = {r: uint(t, 'scope thread', 1) for r, t in scope_threads.items()}
        self.pending, self.now = None, None
        self.events, self.samples, self.audit = [], [], []
        self.contexts, self.sequences, self.baselines, self.groups = {}, {}, {}, {}
        for rank, reader in self.readers.items():
            uint(rank, 'rank')
            s = reader.snapshot()
            self._snapshot(s, rank)
            self.contexts[rank] = (s['pid'], s['created_ns'])
            self.sequences[rank] = s['read_pos']

    def _snapshot(self, s, rank, *, clean=False):
        require(s['abi'] == 2 and s['event_bytes'] == 280, 'ABI2 layout mismatch')
        require((s['run_id'], s['node_id'], s['global_rank']) ==
                (self.run_id, self.node_id, rank), 'ABI2 snapshot identity mismatch')
        for f in ('pid', 'created_ns', 'read_pos', 'write_pos', 'capacity', 'requested_control',
                  'applied_control', 'state', 'closed', 'poisoned', *COUNTERS):
            uint(s[f], f, 1 if f in ('pid', 'capacity', 'created_ns') else 0)
        require(s['state'] in (0, 1) and s['state'] == (s['applied_control'] & 1), 'ABI2 state/control mismatch')
        require(s['requested_control'] <= (1 << 64) - 1 and s['applied_control'] <= (1 << 64) - 1 and
                (s['applied_control'] >> 1) <= (s['requested_control'] >> 1),
                'ABI2 control order mismatch')
        require(s['read_pos'] <= s['write_pos'] <= s['read_pos'] + s['capacity'], 'ABI2 cursor mismatch')
        require(s['closed'] == 0 and s['poisoned'] == 0, 'closed/poisoned ABI2 writer')
        if hasattr(self, 'contexts') and rank in self.contexts:
            require((s['pid'], s['created_ns']) == self.contexts[rank], 'ABI2 writer replaced')
        if clean:
            require(all(s[k] == 0 for k in COUNTERS), 'ABI2 loss/error counters invalidate Profile')
        return s

    def _bounded(self, sequence):
        require(len(sequence) < 10000, 'bridge evidence capacity exhausted')

    def request(self, command):
        number(self.now)
        if not self.fence(command):
            raise StaleOwner('STALE ABI2 request')
        require((command['run_id'], command['node_id'], set(command['expected_ranks'])) ==
                (self.run_id, self.node_id, self.ranks), 'ABI2 command identity mismatch')
        epoch = uint(command['profile_epoch'], 'epoch', 1)
        state = uint(command['requested_state'], 'requested_state')
        require(state in (0, 1) and epoch <= (1 << 63) - 1, 'ABI2 control range')
        require(command['requested_at_seconds'] <= self.now, 'command from future')
        if self.pending != command:
            if self.pending:
                require(epoch >= self.pending['profile_epoch'], 'epoch regression')
                require(not (epoch == self.pending['profile_epoch'] and
                        self.pending['requested_state'] == 0 and state == 1), 'ended epoch reentry')
            self.pending = copy.deepcopy(command)
            self.baselines, self.groups = {}, {}
            for rank, reader in self.readers.items():
                s = self._snapshot(reader.snapshot(), rank, clean=state == 1)
                self.baselines[rank] = s['write_pos']
                reader.request(state, epoch)
                after = self._snapshot(reader.snapshot(), rank, clean=state == 1)
                require(after['requested_control'] == epoch * 2 + state, 'ABI2 request unconfirmed')
        self.poll()

    def poll(self):
        cmd = self.pending
        if cmd is None:
            return
        for rank, reader in self.readers.items():
            if not self.fence(cmd):
                raise StaleOwner('STALE ABI2 drain')
            s = self._snapshot(reader.snapshot(), rank, clean=cmd['requested_state'] == 1)
            require(s['requested_control'] == cmd['profile_epoch'] * 2 + cmd['requested_state'],
                    'ABI2 control overwritten')
            for _ in range(LIMIT):
                raw = reader.read(acknowledge=False)
                if raw is None:
                    break
                raw_valid(raw, self.run_id, self.node_id, rank, s['pid'])
                require(raw['publish_seq'] == self.sequences[rank] + 1, 'ABI2 publication gap/duplicate')
                require(raw['profile_epoch'] <= cmd['profile_epoch'], 'future ABI2 epoch')
                matching = (raw['publish_seq'] > self.baselines[rank] and
                            raw['state'] == cmd['requested_state'] and raw['profile_epoch'] == cmd['profile_epoch'])
                s = self._snapshot(reader.snapshot(), rank, clean=cmd['requested_state'] == 1)
                require(raw['publish_seq'] <= s['write_pos'], 'ABI2 record ahead of writer')
                if matching:
                    require(raw['thread_id'] == self.scope_threads[rank], 'undeclared ABI2 scope thread')
                    require(s['requested_control'] == s['applied_control'] == cmd['profile_epoch'] * 2 + cmd['requested_state'],
                            'record/header application disagreement')
                    group_key = (rank, raw['thread_id'])
                    if raw['api'] == 20 and raw['result'] == 0:
                        if raw['group_depth'] == 1:
                            require(group_key not in self.groups, 'overlapping ABI2 Group scopes')
                            self.groups[group_key] = raw['group_id']
                        else:
                            require(self.groups.get(group_key) == raw['group_id'], 'nested Group without outer scope')
                    if 1 <= raw['api'] <= 8 and raw['group_id']:
                        require(self.groups.get(group_key) == raw['group_id'], 'Group sample without current outer scope')
                    if raw['api'] == 21 and raw['group_depth'] == 1:
                        require(self.groups.get(group_key) == raw['group_id'], 'GroupEnd without current outer scope')
                        del self.groups[group_key]
                    stamp = dict(command_id=cmd['command_id'], generation=cmd['generation'],
                                 local_generation=cmd['local_generation'])
                    if scope_record(raw) and not any(e['command_id'] == cmd['command_id'] and
                            e['global_rank'] == rank and e['generation'] == cmd['generation'] and
                            e['local_generation'] == cmd['local_generation'] for e in self.events):
                        self._bounded(self.events)
                        self.events.append(dict(run_id=self.run_id, node_id=self.node_id, global_rank=rank,
                            profile_epoch=cmd['profile_epoch'], requested_state=cmd['requested_state'],
                            scope_sequence=raw['publish_seq'], applied_at_seconds=self.now,
                            boundary=BOUNDARY, source=SOURCE, raw=copy.deepcopy(raw),
                            snapshot=copy.deepcopy(s), baseline=self.baselines[rank], **stamp))
                    if raw['state'] == 1 and 1 <= raw['api'] <= 8:
                        row = normalize(raw)
                        self._bounded(self.samples)
                        self.samples.append(dict(source=SOURCE, row=row, sha256=digest(row),
                            collected_at_seconds=self.now, raw=copy.deepcopy(raw), **stamp))
                self._bounded(self.audit)
                self.audit.append(dict(rank=rank, sequence=raw['publish_seq'], raw_sha256=raw['record_digest'],
                                       selected=matching, command_id=cmd['command_id']))
                # CPU memory staging before ACK, never a disk durability guarantee.
                reader.acknowledge(raw['publish_seq'])
                require(reader.snapshot()['read_pos'] == raw['publish_seq'], 'ABI2 read ACK unconfirmed')
                self.sequences[rank] = raw['publish_seq']
            else:
                raise InputError('bounded ABI2 drain exhausted; no ready claim')


class Abi2LocalController(LocalController):
    def __init__(self, store, run_id, node_id, probe):
        require(isinstance(probe, Abi2ProbeAdapter), 'explicit ABI2 adapter required')
        scopes = {str(r): dict(pid=probe.contexts[r][0], created_ns=probe.contexts[r][1],
                              thread_id=probe.scope_threads[r]) for r in probe.ranks}
        old = store.read(run_id)
        require(old is not None and old.get('bridge_source') == SOURCE, 'explicit ABI2 run required')
        previous = old['nodes'][node_id].get('abi2_scopes')
        require(previous is None or previous == scopes, 'ABI2 scope declaration changed; new run required')
        super().__init__(store, run_id, node_id, probe)
        def declare(doc):
            require(doc['nodes'][node_id]['generation'] == self.generation, 'scope owner changed')
            doc['nodes'][node_id].update(abi2_scopes=scopes, abi2_scopes_sha256=digest(scopes))
        transaction(store, run_id, declare)

    def tick(self, now):
        self.probe.now = number(now)
        try:
            result = super().tick(now)
            if result['status'] == 'OBSERVED':
                def ready(doc):
                    if doc['nodes'][self.node_id]['generation'] != self.generation:
                        raise StaleOwner('STALE ABI2 drain receipt')
                    a = doc['active']
                    if not a or doc['state'] != 'PROFILE_DRAINING':
                        return
                    nd = a['nodes'][self.node_id]
                    require(nd['command'] == self.probe.pending, 'ABI2 drain command changed')
                    snapshots = {str(r): self.probe._snapshot(reader.snapshot(), r, clean=True)
                                 for r, reader in self.probe.readers.items()}
                    require(not self.probe.groups, 'unfinished ABI2 Group scope at drain')
                    if any(s['read_pos'] != s['write_pos'] for s in snapshots.values()):
                        nd['ready'] = None
                        return
                    for r, s in snapshots.items():
                        require(s['read_pos'] == self.probe.sequences[int(r)] and
                                s['requested_control'] == s['applied_control'] == 2 * a['profile_epoch'] + 1,
                                'ABI2 drain control/cursor mismatch')
                    nd['ready'].update(source='CPU_ABI2_DRAIN', snapshots=snapshots,
                                       snapshots_sha256=digest(snapshots))
                transaction(self.store, self.run_id, ready)
            return result
        except StaleOwner:
            raise
        except (ValueError, OSError, KeyError, TypeError) as exc:
            def fail(doc):
                if doc['nodes'][self.node_id]['generation'] != self.generation:
                    raise StaleOwner('STALE ABI2 local failure')
                if doc['active']:
                    _failed(doc, 'INCOMPLETE', 'ABI2 bridge: ' + str(exc))
                return provisional('INCOMPLETE', str(exc))
            try:
                return transaction(self.store, self.run_id, fail)
            except Unavailable as unavailable:
                self.disconnected = True
                return provisional('BLOCKED', str(unavailable))


class Abi2GlobalController(GlobalController):
    """Explicit CPU bridge selection; source-bound state cannot resume as M6-A."""
    def __init__(self, store, run_id, nodes, **kwargs):
        old = store.read(run_id)
        if old is not None:
            require(old.get('bridge_source') == SOURCE, 'bridge mode mismatch; new run required')
        super().__init__(store, run_id, nodes, **kwargs)
        transaction(store, run_id, lambda doc: doc.update(bridge_source=SOURCE))

    def _all_applied(self, doc, state):
        try:
            require(doc.get('bridge_source') == SOURCE, 'bridge mode corrupted')
            a = doc['active']
            for node, nd in a['nodes'].items():
                cmd, ack = nd['command'], nd['ack']
                require(ack is not None and ack['command_id'] == cmd['command_id'] and
                    ack['command_sha256'] == digest(cmd) and ack['local_generation'] == cmd['local_generation'] and
                    ack['kind'] == 'COMMAND_ACCEPTED_ONLY' and ack['source'] == 'CPU_LOCAL_CONTROLLER' and
                    cmd['requested_at_seconds'] <= number(ack['accepted_at_seconds']) <= a['last_time_seconds'],
                    'strict command ACK mismatch')
                require(set(nd['applied']) == {str(r) for r in doc['nodes'][node]['ranks']}, 'missing rank scope')
                uint(ack['local_generation'], 'ACK generation', 1)
                for rank, proof in nd['applied'].items():
                    for field in ('global_rank', 'profile_epoch', 'requested_state', 'generation',
                                  'local_generation', 'scope_sequence', 'baseline'):
                        uint(proof[field], 'proof ' + field)
                    require((proof['global_rank'], proof['node_id'], proof['run_id'], proof['profile_epoch'],
                        proof['requested_state'], proof['command_id'], proof['generation'], proof['local_generation'],
                        proof['source'], proof['boundary']) == (int(rank), node, self.run_id, a['profile_epoch'],
                        state, cmd['command_id'], self.generation, doc['nodes'][node]['generation'], SOURCE, BOUNDARY),
                        'ABI2 proof fence mismatch')
                    scopes = doc['nodes'][node]['abi2_scopes']
                    require(doc['nodes'][node]['abi2_scopes_sha256'] == digest(scopes), 'scope declaration corrupt')
                    raw, snap = proof['raw'], proof['snapshot']
                    declared = scopes[rank]
                    require((raw['thread_id'], snap['pid'], snap['created_ns']) ==
                            (declared['thread_id'], declared['pid'], declared['created_ns']),
                            'ABI2 proof thread/process scope mismatch')
                    raw_valid(raw, self.run_id, node, int(rank), snap['pid'])
                    require(scope_record(raw) and proof['scope_sequence'] == raw['publish_seq'] > proof['baseline'] and
                        raw['state'] == state and raw['profile_epoch'] == a['profile_epoch'] and
                        snap['abi'] == 2 and snap['event_bytes'] == 280 and
                        snap['run_id'] == self.run_id and snap['node_id'] == node and snap['global_rank'] == int(rank) and
                        snap['requested_control'] == snap['applied_control'] == 2 * a['profile_epoch'] + state and
                        snap['state'] == state and snap['closed'] == snap['poisoned'] == 0 and
                        (state == 0 or all(snap[k] == 0 for k in COUNTERS)) and
                        cmd['requested_at_seconds'] <= number(proof['applied_at_seconds']) <= a['last_time_seconds'],
                        'ABI2 fresh scope evidence mismatch')
            return True
        except (ValueError, TypeError, KeyError):
            return False

    def _analyze(self, doc):
        a = doc['active']
        require(self._all_applied(doc, 1), 'missing ABI2 applied evidence')
        require(digest(a['manifest']) == a['manifest_sha256'], 'manifest hash mismatch')
        bundle = copy.deepcopy(a['manifest'])
        for node, nd in a['nodes'].items():
            ready = nd['ready']
            require(ready is not None and ready['command_sha256'] == digest(nd['command']) and
                    ready['data_sha256'] == digest(nd['samples']) and ready['records'] == len(nd['samples']),
                    'ABI2 ready/hash mismatch')
            require(ready['source'] == 'CPU_ABI2_DRAIN' and
                    ready['snapshots_sha256'] == digest(ready['snapshots']) and
                    set(ready['snapshots']) == set(nd['applied']) and
                    a['window']['end_seconds'] <= number(ready['drained_at_seconds']) <= a['last_time_seconds'],
                    'ABI2 drain snapshot/time mismatch')
            for rank, snap in ready['snapshots'].items():
                proof = nd['applied'][rank]
                require(snap['abi'] == 2 and snap['event_bytes'] == 280 and
                    (snap['run_id'], snap['node_id'], snap['global_rank'], snap['pid'], snap['created_ns']) ==
                    (self.run_id, node, int(rank), proof['snapshot']['pid'], proof['snapshot']['created_ns']) and
                    snap['read_pos'] == snap['write_pos'] >= proof['scope_sequence'] and
                    snap['requested_control'] == snap['applied_control'] == 2 * a['profile_epoch'] + 1 and
                    snap['state'] == 1 and snap['closed'] == snap['poisoned'] == 0 and all(snap[k] == 0 for k in COUNTERS),
                    'ABI2 incomplete drain snapshot')
            for sample in nd['samples']:
                row, raw = sample['row'], sample['raw']
                proof = nd['applied'][str(row['global_rank'])]
                raw_valid(raw, self.run_id, node, row['global_rank'], proof['snapshot']['pid'])
                require(raw['thread_id'] == doc['nodes'][node]['abi2_scopes'][str(row['global_rank'])]['thread_id'],
                        'ABI2 sample thread mismatch')
                require(sample['source'] == SOURCE and row == normalize(raw) and digest(row) == sample['sha256'] and
                    sample['command_id'] == nd['command']['command_id'] and sample['generation'] == self.generation and
                    sample['local_generation'] == doc['nodes'][node]['generation'] and
                    row['run_id'] == self.run_id and row['profile_epoch'] == a['profile_epoch'] and row['node_id'] == node and
                    row['sample_seq'] >= proof['scope_sequence'] and
                    a['window']['start_seconds'] <= number(sample['collected_at_seconds']) < a['window']['end_seconds'],
                    'ABI2 sample epoch/scope/window/fence mismatch')
                bundle['records'].append(row)
        valid = validate_bundle(bundle)
        result = analyze_approved_g04(bundle)
        result.update(final_alert=False, final_fault_ranks=[], source=SOURCE,
                      input_sha256=digest(bundle), manifest_sha256=a['manifest_sha256'])
        a['analysis'], a['completeness'], a['data_sha256'] = result, valid['completeness'], digest(bundle)
