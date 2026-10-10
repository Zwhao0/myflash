"""EXTENSION CPU simulator of M3 request/scope application, never CUDA timing."""
import copy
from flash.m6_protocol import digest, number


class ProbeAdapter:
    source = 'CPU_SIMULATED_PROBE'

    def __init__(self, run_id, node_id, ranks, fence):
        self.run_id, self.node_id, self.ranks, self.fence = run_id, node_id, set(ranks), fence
        self.pending = None
        self.states = {r: dict(state=0, epoch=0, sequence=0) for r in ranks}
        self.events, self.samples = [], []

    def request(self, command):
        if not self.fence(command):
            raise ValueError('stale Probe request')
        if command['run_id'] != self.run_id or command['node_id'] != self.node_id:
            raise ValueError('Probe identity mismatch')
        if self.pending:
            old = self.pending
            if (command['generation'], command['local_generation']) < (old['generation'], old['local_generation']):
                raise ValueError('stale generation')
            if command['profile_epoch'] < old['profile_epoch']:
                raise ValueError('epoch regression')
            if command['profile_epoch'] == old['profile_epoch'] and old['requested_state'] == 0 and command['requested_state'] == 1:
                raise ValueError('ended epoch cannot reenter Profile')
        self.pending = copy.deepcopy(command)

    def boundary(self, rank, now, *, legal=True):
        number(now)
        if rank not in self.ranks:
            raise ValueError('unexpected rank')
        if not legal or self.pending is None:
            return None
        command = self.pending
        if not self.fence(command):
            raise ValueError('stale boundary fence')
        state = self.states[rank]
        if now < state.get('last_boundary_seconds', 0) or now < command['requested_at_seconds']:
            raise ValueError('scope clock regression/before command')
        state.update(last_boundary_seconds=now, state=command['requested_state'], epoch=command['profile_epoch'],
                     sequence=state['sequence'] + 1, command_id=command['command_id'])
        evidence = dict(run_id=self.run_id, node_id=self.node_id, global_rank=rank,
                        profile_epoch=state['epoch'], requested_state=state['state'],
                        command_id=command['command_id'], generation=command['generation'],
                        local_generation=command['local_generation'], scope_sequence=state['sequence'],
                        applied_at_seconds=now, boundary='legal_scope_start', source=self.source)
        self.events.append(evidence)
        return evidence

    def sample(self, rank, row, now):
        number(now)
        state = self.states[rank]
        if state['state'] != 1 or not self.pending or state.get('command_id') != self.pending['command_id']:
            raise ValueError('rank not applied current Profile command')
        if not self.fence(self.pending):
            raise ValueError('stale sample fence')
        # row values come from a declared fixture; no target labels accepted.
        if now < state['last_boundary_seconds']:
            raise ValueError('sample before applied scope')
        row = copy.deepcopy(row)
        if row['timing_definition'] != 'synthetic_nonnegative_v1':
            raise ValueError('CPU adapter accepts declared synthetic timing only')
        if row['global_rank'] != rank:
            raise ValueError('sample rank mismatch')
        row.update(run_id=self.run_id, node_id=self.node_id, profile_epoch=state['epoch'])
        envelope = dict(source=self.source, row=row, sha256=digest(row), collected_at_seconds=now,
                        command_id=self.pending['command_id'], generation=self.pending['generation'],
                        local_generation=self.pending['local_generation'])
        self.samples.append(envelope)
        return envelope
