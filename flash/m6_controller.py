"""ADAPTATION fenced poll state machine; EXTENSION manual/CPU-only execution.

No change_detection/Rbeast import and no evaluator/ground truth inputs.
"""
import copy
from dataclasses import asdict
from flash.profile_input import validate_bundle, InputError
from flash.localization import analyze
from flash.m6_protocol import (registration, event, digest, number, window_seconds,
                               provisional, identity, StaleOwner, MAX_EPOCHS)
from flash.m6_store import transaction, Unavailable
from flash.m6_iteration import IterationReader

TRIGGER = 'MANUAL_TEST_TRIGGER'


def _node_command(doc, active, node, state):
    return dict(schema_version=1, run_id=doc['run_id'], node_id=node,
                profile_epoch=active['profile_epoch'], expected_nodes=doc['expected_nodes'],
                expected_ranks=doc['nodes'][node]['ranks'], requested_state=state,
                command_id=f"e{active['profile_epoch']}-g{doc['global_generation']}-s{state}-{node}",
                generation=doc['global_generation'], local_generation=doc['nodes'][node]['generation'],
                deadline_seconds=active['deadline_seconds'], requested_at_seconds=active['command_at_seconds'])


def _request(doc, state):
    a = doc['active']
    a['nodes'] = {n: dict(command=_node_command(doc, a, n, state), ack=None,
                         applied={}, samples=[], ready=None, ignored_old=0)
                  for n in doc['expected_nodes']}


def _failed(doc, status, reason):
    a = doc['active']
    if a['failure'] is None:
        a['failure'] = provisional(status, reason)
        event(doc, 'FAILURE', profile_epoch=a['profile_epoch'], status=status, reason=reason)


class GlobalController:
    def __init__(self, store, run_id, nodes, *, resume=False, control_timeout=5.0, reset_timeout=5.0, iteration_timeout=60.0):
        self.store, self.run_id = store, run_id
        self.control_timeout, self.reset_timeout = number(control_timeout), number(reset_timeout)
        self.iteration_timeout = number(iteration_timeout)
        if iteration_timeout <= 0: raise ValueError('positive iteration deadline required')
        if min(control_timeout, reset_timeout) <= 0:
            raise ValueError('positive finite deadlines required')
        expected = registration(run_id, nodes)
        old = store.read(run_id)
        if old is None:
            if resume:
                raise Unavailable('lost run document; operator recovery required')
            if not store.cas(run_id, -1, expected):
                raise Unavailable('registration race; explicitly resume known run')
        elif {n: old['nodes'][n]['ranks'] for n in old['expected_nodes']} != {n: sorted(v) for n, v in nodes.items()}:
            raise ValueError('registration identity cannot change')
        def claim(doc):
            doc['global_generation'] += 1
            if doc['active']:
                _failed(doc, 'ABORTED', 'global controller restart; explicit Monitor reset required')
            event(doc, 'GLOBAL_CLAIM', generation=doc['global_generation'])
            return doc['global_generation']
        self.generation = transaction(store, run_id, claim)
        self.disconnected = False
        self.receipts = []

    def _owned(self, doc):
        if doc['global_generation'] != self.generation:
            raise StaleOwner('STALE global fencing token')

    def start(self, trigger, manifest, now, *, request_id):
        number(now)
        identity(request_id)
        request_hash = digest(dict(trigger=trigger, manifest=manifest))
        try:
            existing = self.store.read(self.run_id)
        except Unavailable as exc:
            self.disconnected = True
            result = provisional('BLOCKED', str(exc)); self.receipts.append(result)
            return result
        if existing is None:
            result = provisional('BLOCKED', 'lost run document; operator reconciliation/new run required')
            self.receipts.append(result)
            return result
        self._owned(existing)
        for prior in existing['epochs'] + ([existing['active']] if existing['active'] else []):
            if prior['request_id'] == request_id:
                if prior['request_sha256'] != request_hash:
                    raise ValueError('conflicting manual request_id')
                return dict(status='DUPLICATE_CONFIRMED', profile_epoch=prior['profile_epoch'],
                            final_alert=False, final_fault_ranks=[])
        if trigger != TRIGGER:
            raise ValueError('only MANUAL_TEST_TRIGGER is approved')
        stream = IterationReader(self.store, self.run_id, 0).read(now=now, timeout_seconds=self.iteration_timeout)
        if stream['status'] != 'READ_CONFIRMED':
            return provisional(stream['status'], stream.get('reason'))
        latest = stream['records'][-1]
        try:
            duration = window_seconds(latest)
        except ValueError as exc:
            return provisional('INSUFFICIENT_EVIDENCE', str(exc))
        if manifest.get('records'):
            raise ValueError('Global manifest must not preload samples')
        if not manifest.get('communicators') or not manifest.get('parallel_states'):
            return provisional('INSUFFICIENT_EVIDENCE', 'missing manifest')
        if any(k in manifest for k in ('truth', 'target_rank', 'fault_label', 'expected_result')):
            raise ValueError('truth prohibited')
        def begin(doc):
            self._owned(doc)
            if doc['active'] and doc['active']['request_id'] == request_id:
                if doc['active']['request_sha256'] != request_hash:
                    raise ValueError('conflicting manual request_id')
                return dict(status='DUPLICATE_CONFIRMED', profile_epoch=doc['profile_epoch'], final_alert=False, final_fault_ranks=[])
            if doc['state'] != 'MONITOR' or doc['active']:
                return provisional('BLOCKED', 'previous epoch/reset not closed')
            if len(doc['epochs']) >= MAX_EPOCHS:
                return provisional('BLOCKED', 'epoch capacity exhausted; archive/new run')
            doc['profile_epoch'] += 1
            epoch = doc['profile_epoch']
            plan = copy.deepcopy(manifest)
            plan.update(schema_version=1, context=dict(run_id=self.run_id, profile_epoch=epoch), records=[])
            locals_ = [local for d in plan['communicators'] for local in d['local_instances']]
            pairs = {(x['node_id'], x['global_rank']) for x in locals_}
            expected_pairs = {(n, r) for n, nd in doc['nodes'].items() for r in nd['ranks']}
            if pairs != expected_pairs:
                raise ValueError('manifest must cover exactly registered node/rank set')
            doc['active'] = dict(profile_epoch=epoch, trigger=trigger, request_id=request_id, request_sha256=request_hash,
                command_at_seconds=now, started_at_seconds=now,
                last_time_seconds=now, duration_seconds=duration, iteration_record=asdict(latest),
                iteration_sha256=digest(asdict(latest)), manifest=plan, manifest_sha256=digest(plan),
                deadline_seconds=now + self.control_timeout, window=None, failure=None,
                analysis=None, nodes={}, transitions=['MONITOR', 'PROFILE_REQUESTED'])
            doc['state'] = 'PROFILE_REQUESTED'
            _request(doc, 1)
            event(doc, 'PROFILE_REQUEST', profile_epoch=epoch, generation=self.generation,
                  trigger=trigger, duration_seconds=duration, at_seconds=now)
            return dict(status='PROFILE_REQUESTED', profile_epoch=epoch, final_alert=False, final_fault_ranks=[])
        return transaction(self.store, self.run_id, begin)

    def _transition(self, doc, state, now):
        doc['state'] = state
        doc['active']['transitions'].append(state)
        event(doc, 'TRANSITION', state=state, profile_epoch=doc['active']['profile_epoch'], at_seconds=now)

    def _reset(self, doc, now):
        a = doc['active']
        a.setdefault('profile_nodes', copy.deepcopy(a['nodes']))
        if doc['state'] == 'MONITOR_RESET_REQUESTED':
            a.setdefault('reset_attempts', []).append(copy.deepcopy(a['nodes']))
        a['deadline_seconds'] = now + self.reset_timeout
        a['command_at_seconds'] = now
        _request(doc, 0)
        self._transition(doc, 'MONITOR_RESET_REQUESTED', now)

    def _all_applied(self, doc, state):
        a = doc['active']
        for node, nd in a['nodes'].items():
            cmd = nd['command']
            if nd['ack'] is None or nd['ack']['command_sha256'] != digest(cmd):
                return False
            if set(nd['applied']) != {str(r) for r in doc['nodes'][node]['ranks']}:
                return False
            for rank, proof in nd['applied'].items():
                if (proof['global_rank'] != int(rank) or proof['node_id'] != node or
                    proof['run_id'] != self.run_id or proof['profile_epoch'] != a['profile_epoch'] or
                    proof['requested_state'] != state or proof['source'] != 'CPU_SIMULATED_PROBE' or
                    proof['command_id'] != cmd['command_id'] or proof['generation'] != self.generation or
                    proof['local_generation'] != doc['nodes'][node]['generation'] or
                    proof['scope_sequence'] <= 0 or proof['applied_at_seconds'] < cmd['requested_at_seconds'] or
                    proof['applied_at_seconds'] > a['last_time_seconds'] or
                    proof['boundary'] != 'legal_scope_start'):
                    return False
        return True

    def _analyze(self, doc):
        a = doc['active']
        if not self._all_applied(doc, 1):
            raise InputError('missing actual per-rank Profile evidence')
        if digest(a['manifest']) != a['manifest_sha256']:
            raise InputError('manifest hash mismatch')
        bundle = copy.deepcopy(a['manifest'])
        for node, nd in a['nodes'].items():
            ready = nd['ready']
            if not ready or ready['command_sha256'] != digest(nd['command']) or ready['data_sha256'] != digest(nd['samples']):
                raise InputError('node ready receipt/hash missing or corrupt')
            for sample in nd['samples']:
                row = sample['row']
                if (sample['source'] != 'CPU_SIMULATED_PROBE' or digest(row) != sample['sha256'] or
                    sample['command_id'] != nd['command']['command_id'] or
                    sample['generation'] != self.generation or
                    sample['local_generation'] != doc['nodes'][node]['generation'] or
                    row['node_id'] != node or row['global_rank'] not in doc['nodes'][node]['ranks'] or
                    row['run_id'] != self.run_id or row['profile_epoch'] != a['profile_epoch'] or
                    row['timing_definition'] != 'synthetic_nonnegative_v1' or
                    not a['window']['start_seconds'] <= sample['collected_at_seconds'] < a['window']['end_seconds']):
                    raise InputError('sample identity/window/hash/fence mismatch')
                bundle['records'].append(row)
        # Existing M4 is the completeness authority, including independent Group scopes.
        valid = validate_bundle(bundle)
        result = analyze(bundle)
        result.update(final_alert=False, final_fault_ranks=[], source='CPU_SIMULATED_M4_REPLAY',
                      input_sha256=digest(bundle), manifest_sha256=a['manifest_sha256'])
        a['analysis'] = result
        a['completeness'] = valid['completeness']
        a['data_sha256'] = digest(bundle)

    def tick(self, now):
        number(now)
        recovered = self.disconnected
        def advance(doc):
            self._owned(doc)
            a = doc['active']
            if a is None:
                return provisional(doc['state'])
            if now < a['last_time_seconds']:
                raise ValueError('clock regression')
            a['last_time_seconds'] = now
            if recovered:
                _failed(doc, 'ABORTED', 'control transport lost; reconciliation/reset required')
            state = doc['state']
            if state == 'BLOCKED':
                return provisional('BLOCKED', 'operator must verify all ranks Monitor before new run')
            if a['failure'] and state != 'MONITOR_RESET_REQUESTED':
                self._reset(doc, now)
                return a['failure']
            if state == 'MONITOR_RESET_REQUESTED':
                if any(nd['command']['generation'] != self.generation or
                       nd['command']['local_generation'] != doc['nodes'][node]['generation']
                       for node, nd in a['nodes'].items()):
                    self._reset(doc, now)
                    return provisional('MONITOR_RESET_REQUESTED', 'fenced reset reissued; old partial proof retained')
                if self._all_applied(doc, 0):
                    a['reset_verified'] = True
                    a['reset_nodes'] = copy.deepcopy(a['nodes'])
                    a['result'] = a['failure'] or a['analysis'] or provisional('ABORTED', 'no analysis')
                    a['closed_at_seconds'] = now
                    a['transitions'].append('MONITOR')
                    event(doc, 'MONITOR_VERIFIED', profile_epoch=a['profile_epoch'], at_seconds=now)
                    doc['epochs'].append(copy.deepcopy(a))
                    doc['active'], doc['state'] = None, 'MONITOR'
                    return a['result']
                if now >= a['deadline_seconds']:
                    _failed(doc, 'TIMEOUT', 'Monitor reset missing per-rank scope evidence')
                    a['reset_verified'] = False
                    a['recovery_required'] = 'operator must reconcile exact run/node/rank Probe state; no new epoch'
                    self._transition(doc, 'BLOCKED', now)
                    return provisional('BLOCKED', a['recovery_required'])
                return provisional(state)
            if now >= a['deadline_seconds']:
                _failed(doc, 'TIMEOUT', 'control/data deadline: ' + state)
                self._reset(doc, now)
                return a['failure']
            if state == 'PROFILE_REQUESTED':
                if all(nd['ack'] is not None for nd in a['nodes'].values()):
                    self._transition(doc, 'PROFILE_ARMING', now)
            elif state == 'PROFILE_ARMING':
                if self._all_applied(doc, 1):
                    a['window'] = dict(start_seconds=now, end_seconds=now + a['duration_seconds'],
                                       time_domain='single_host_cpu_simulation_monotonic_seconds')
                    a['deadline_seconds'] = a['window']['end_seconds'] + self.control_timeout
                    self._transition(doc, 'PROFILE_COLLECTING', now)
            elif state == 'PROFILE_COLLECTING':
                if now >= a['window']['end_seconds']:
                    self._transition(doc, 'PROFILE_DRAINING', now)
            elif state == 'PROFILE_DRAINING':
                if all(nd['ready'] is not None for nd in a['nodes'].values()):
                    try:
                        self._analyze(doc)
                    except (InputError, KeyError, TypeError, ValueError) as exc:
                        _failed(doc, 'INCOMPLETE', str(exc))
                        self._reset(doc, now)
                        return a['failure']
                    self._transition(doc, 'PROFILE_READY', now)
            elif state == 'PROFILE_READY':
                self._transition(doc, 'ANALYZED_PROVISIONAL', now)
            elif state == 'ANALYZED_PROVISIONAL':
                self._reset(doc, now)
            return provisional(doc['state'])
        try:
            result = transaction(self.store, self.run_id, advance)
            self.disconnected = False
            self.receipts.append(result)
            return result
        except Unavailable as exc:
            self.disconnected = True
            result = provisional('BLOCKED', str(exc))
            self.receipts.append(result)
            return result


class LocalController:
    def __init__(self, store, run_id, node_id, probe):
        self.store, self.run_id, self.node_id, self.probe = store, run_id, node_id, probe
        def claim(doc):
            if node_id not in doc['nodes']:
                raise ValueError('undeclared node')
            doc['nodes'][node_id]['generation'] += 1
            if doc['active']:
                _failed(doc, 'INCOMPLETE', 'local controller restarted; fresh boundary/reset required')
            event(doc, 'LOCAL_CLAIM', node_id=node_id, generation=doc['nodes'][node_id]['generation'])
            return doc['nodes'][node_id]['generation']
        self.generation = transaction(store, run_id, claim)
        self.disconnected, self.receipts = False, []

    def fence(self, command):
        doc = self.store.read(self.run_id)
        if not doc or not doc['active']:
            return False
        return (command['generation'] == doc['global_generation'] and
                command['local_generation'] == doc['nodes'][self.node_id]['generation'] and
                command['command_id'] == doc['active']['nodes'][self.node_id]['command']['command_id'])

    def tick(self, now):
        number(now)
        recovered = self.disconnected
        def accept(doc):
            if doc['nodes'][self.node_id]['generation'] != self.generation:
                raise StaleOwner('STALE local fencing token')
            a = doc['active']
            if a is None:
                return None
            if recovered:
                _failed(doc, 'ABORTED', 'local transport lost; invalidate epoch')
            nd = a['nodes'][self.node_id]
            cmd = nd['command']
            if (cmd['generation'] != doc['global_generation'] or cmd['local_generation'] != self.generation):
                return None  # Await fenced reset; never apply an old command.
            if nd['ack'] is None:
                nd['ack'] = dict(command_id=cmd['command_id'], command_sha256=digest(cmd),
                                 accepted_at_seconds=now, local_generation=self.generation,
                                 kind='COMMAND_ACCEPTED_ONLY', source='CPU_LOCAL_CONTROLLER')
                event(doc, 'COMMAND_ACK', node_id=self.node_id, command_id=cmd['command_id'])
            return copy.deepcopy(cmd)
        try:
            command = transaction(self.store, self.run_id, accept)
            self.disconnected = False
            if command is None:
                return provisional('IDLE')
            # Side effect is separate from ACK. Simulator rechecks fencing at each boundary.
            self.probe.request(command)
            def observe(doc):
                if doc['nodes'][self.node_id]['generation'] != self.generation:
                    raise StaleOwner('STALE local fencing token')
                a = doc['active']
                if not a:
                    raise ValueError('closed epoch during observation')
                nd = a['nodes'][self.node_id]
                if nd['command'] != command:
                    raise StaleOwner('STALE command during observation')
                matching = [e for e in self.probe.events if e['command_id'] == command['command_id'] and
                            e['generation'] == command['generation'] and e['local_generation'] == self.generation]
                for proof in matching:
                    if proof['requested_state'] != command['requested_state'] or proof['profile_epoch'] != a['profile_epoch']:
                        _failed(doc, 'INCOMPLETE', 'applied state/epoch mismatch')
                        continue
                    old = nd['applied'].get(str(proof['global_rank']))
                    if old is None or proof['scope_sequence'] > old['scope_sequence']:
                        nd['applied'][str(proof['global_rank'])] = copy.deepcopy(proof)
                nd['ignored_old'] = len(self.probe.events) - len(matching)
                if command['requested_state'] == 1 and a['window'] is not None:
                    candidates = [s for s in self.probe.samples if s['command_id'] == command['command_id'] and
                                  s['generation'] == command['generation'] and s['local_generation'] == self.generation]
                    nd['samples'] = [copy.deepcopy(s) for s in candidates if
                                     a['window']['start_seconds'] <= s['collected_at_seconds'] < a['window']['end_seconds']]
                    nd['outside_window'] = len(candidates) - len(nd['samples'])
                    if doc['state'] == 'PROFILE_DRAINING':
                        nd['ready'] = dict(command_sha256=digest(command), data_sha256=digest(nd['samples']),
                                           drained_at_seconds=now, records=len(nd['samples']),
                                           source='CPU_SIMULATED_DRAIN', completeness='PENDING_M4_VALIDATION')
                return dict(status='OBSERVED', command_id=command['command_id'],
                            applied_ranks=sorted(int(r) for r in nd['applied']),
                            final_alert=False, final_fault_ranks=[])
            result = transaction(self.store, self.run_id, observe)
            self.receipts.append(result)
            return result
        except Unavailable as exc:
            # No ability to prove remote Probe reset while disconnected. Fail closed;
            # caller must run the explicit reconciliation/reset after reconnect.
            self.disconnected = True
            result = provisional('BLOCKED', str(exc))
            result['recovery'] = 'reconnect, invalidate epoch, request Monitor, observe every rank boundary'
            self.receipts.append(result)
            return result
