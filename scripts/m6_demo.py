"""EXTENSION predeclared CPU fixture replay with virtual seconds, no truth input."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flash.iteration_reporter import IterationRecord
from flash.m6_protocol import digest
from flash.m6_store import MemoryStore
from flash.m6_controller import GlobalController, LocalController, TRIGGER
from flash.m6_probe import ProbeAdapter
from flash.m6_iteration import IterationPublisher


class Simulation:
    def __init__(self, fixture='three_groups_max_then_min', *, store=None, run='m6a-cpu'):
        # Input only. Expected results and evaluator are never read here.
        path = ROOT / 'tests/m4_cases' / fixture / 'input.json'
        data = path.read_bytes()
        bundle = json.loads(data)
        if any(r['timing_definition'] != 'synthetic_nonnegative_v1' for r in bundle['records']):
            raise ValueError('predeclared synthetic fixture required')
        self.source = dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(),
                           source='M4_SYNTHETIC_FIXTURE', derived_source='CPU_SIMULATION',
                           adaptation='copy; run/epoch/node identifiers only; no duration/count/label edits')
        ranks = sorted({r['global_rank'] for r in bundle['records']})
        self.nodes = {'node-0': [r for r in ranks if r % 2 == 0], 'node-1': [r for r in ranks if r % 2 == 1]}
        for d in bundle['communicators']:
            for local in d['local_instances']:
                local['node_id'] = 'node-' + str(local['global_rank'] % 2)
        for row in bundle['records']:
            row['node_id'] = 'node-' + str(row['global_rank'] % 2)
        self.rows = bundle.pop('records')
        bundle['records'] = []
        self.manifest = bundle
        self.store, self.run = store or MemoryStore(), run
        self.global_ = GlobalController(self.store, run, self.nodes)
        self.probes, self.locals = {}, {}
        for node, members in self.nodes.items():
            # Bound to the controller after ownership claim; no shared Header shortcut.
            probe = ProbeAdapter(run, node, members, lambda command: False)
            local = LocalController(self.store, run, node, probe)
            probe.fence = local.fence
            self.probes[node], self.locals[node] = probe, local
        self.publish_iteration()

    def publish_iteration(self, iteration=1, time_ms=100.0, boundary='cpu_simulated_iteration_end', now=0):
        record = IterationRecord(self.run, 0, iteration, time_ms, '2026-10-10T00:00:00+00:00',
                                 'CPU_SIMULATED_FRAMEWORK', boundary, False)
        return IterationPublisher(self.store, self.run, 0, clock=lambda:now).publish(record)

    def poll(self, now):
        return [local.tick(now) for local in self.locals.values()]

    def boundaries(self, now, *, skip=()):
        for probe in self.probes.values():
            for rank in probe.ranks - set(skip):
                probe.boundary(rank, now)

    def arm(self, now=0, request_id='manual-1'):
        result = self.global_.start(TRIGGER, self.manifest, now, request_id=request_id)
        self.poll(now)
        self.global_.tick(now)
        self.boundaries(now + 0.1)
        self.poll(now + 0.1)
        self.global_.tick(now + 0.2)
        return result

    def samples(self, now):
        for row in self.rows:
            self.probes[row['node_id']].sample(row['global_rank'], row, now)
        self.poll(now)

    def finish(self, end, *, reset_skip=()):
        self.global_.tick(end)
        self.poll(end)
        self.global_.tick(end + 0.1)
        self.global_.tick(end + 0.2)
        self.global_.tick(end + 0.3)
        self.poll(end + 0.3)
        self.boundaries(end + 0.4, skip=reset_skip)
        self.poll(end + 0.4)
        return self.global_.tick(end + 0.5)

    def cycle(self, now, request_id):
        self.arm(now, request_id)
        self.samples(now + 1)
        end = self.store.read(self.run)['active']['window']['end_seconds']
        self.finish(end)
        return self.store.read(self.run)['epochs'][-1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sim = Simulation()
    first, second = sim.cycle(0, 'manual-1'), sim.cycle(30, 'manual-2')
    report = dict(source=sim.source, time_domain='VIRTUAL_CLOCK_NO_PERFORMANCE_CLAIM',
                  logical_nodes_same_host=True, real_gpu=False, real_redis=False,
                  epochs=[first, second], state=sim.store.read(sim.run))
    (args.output/'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(epochs=[e['profile_epoch'] for e in report['epochs']],
                         statuses=[e['result']['status'] for e in report['epochs']],
                         reset_verified=[e['reset_verified'] for e in report['epochs']],
                         sha256=digest(report), final_alert=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
