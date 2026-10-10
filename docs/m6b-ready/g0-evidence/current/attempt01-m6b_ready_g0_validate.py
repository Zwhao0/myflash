"""ADAPTATION bounded CPU-only collector. Required cursor FAIL stays FAIL.

Source: tasks/06b_ready_g0_evidence.md sections 6/7. No registry, Redis, GPU,
Rbeast fit or native entry point is called. Outputs must be private and new.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--machine-alias', required=True)
    parser.add_argument('--only-privacy', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1')
    env.pop('LD_PRELOAD', None)
    env['M6_EVIDENCE_DIR'] = str(output/'control-states')
    commands = [('control', ['tests/m6_control.py'], 120),
                ('demo', ['scripts/m6_demo.py', '--output', str(output/'demo')], 120),
                ('cursor', ['tests/m6b_ready_cursor_contract.py', '--output', str(output/'cursor')], 120),
                ('privacy-units', ['tests/privacy_check_test.py'], 120),
                ('privacy', ['scripts/privacy_check.py'], 600)]
    if args.only_privacy:
        commands = commands[-2:]
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT, env=env)
    paths = [p for p in tracked.decode().split('\0') if p]
    for p in ('scripts/m6b_ready_g0_validate.py', 'tests/m6b_ready_cursor_contract.py'):
        if p not in paths:
            paths.append(p)
    manifest = dict(task='M6B-READY-G0-E', overall='IN_PROGRESS',
        machine_alias=args.machine_alias, os=platform.platform(), python=sys.version,
        executable=sys.executable, cwd=str(ROOT),
        code_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, env=env).decode().strip(),
        worktree_diff=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, env=env).decode(),
        input_source_hashes={p: sha(ROOT/p) for p in paths},
        environment=dict(LD_PRELOAD='REMOVED', CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1'),
        commands=[])
    for name, argv, budget in commands:
        command = [sys.executable] + argv
        receipt = dict(command=command, cwd=str(ROOT), timeout_budget_seconds=budget,
                       environment=manifest['environment'], child_finished=False)
        (output/(name+'.command.json')).write_text(json.dumps(receipt, indent=2)+'\n')
        start = time.monotonic()
        with (output/(name+'.stdout.txt')).open('wb') as stdout, (output/(name+'.stderr.txt')).open('wb') as stderr:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            receipt['owned_pid'] = child.pid
            timed_out = False
            try:
                child.wait(timeout=budget)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        receipt.update(exit_code=child.returncode, timeout=timed_out, child_finished=True,
            elapsed_wall_seconds=time.monotonic()-start,
            status='TIMEOUT' if timed_out else ('PASS' if child.returncode == 0 else 'FAIL'),
            stdout=name+'.stdout.txt', stderr=name+'.stderr.txt',
            stdout_sha256=sha(output/(name+'.stdout.txt')), stderr_sha256=sha(output/(name+'.stderr.txt')))
        (output/(name+'.receipt.json')).write_text(json.dumps(receipt, indent=2)+'\n')
        manifest['commands'].append(receipt)
        (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps(dict(name=name, exit_code=child.returncode, timeout=timed_out,
                              child_finished=True)), flush=True)
    failed = any(c['exit_code'] != 0 or c['timeout'] for c in manifest['commands'])
    manifest['overall'] = 'FAIL' if failed else 'PASS_LIMITED_CPU_CHECKS'
    manifest['driver_exit_code'] = int(failed)
    manifest['resources'] = dict(all_owned_children_waited=True, redis_started=0, gpu_started=0,
                                  new_native_libraries=0, rbeast_fits=0)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
