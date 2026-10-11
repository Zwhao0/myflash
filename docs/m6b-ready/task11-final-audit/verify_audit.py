"""ADAPTATION TASK11 static/document integrity only. Never imports FLASH."""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE = 'b517c5a922d52895e274c3758b5b7c2c409d91ca'
PACKET = 'docs/m6b-ready/task11-final-audit'
TASK = 'tasks/06b_ready_task11_final_admission_audit.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args, data=None):
    return subprocess.run(['git', *args], cwd=root, input=data,
                          capture_output=True, check=True).stdout


def verify(root):
    packet = root / PACKET
    tree = git(root, 'ls-tree', '-rz', '--full-tree', BASE)
    entries = {}
    for item in tree.split(b'\0'):
        if item:
            meta, name = item.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            assert kind == 'blob', 'unexpected base object'
            entries[name.decode()] = dict(mode=mode, blob=blob)
    protected = [p for p in entries if p not in ('STATUS.md', 'GAPS.md')]
    # Git blob hashing without filters covers original bytes, including large evidence.
    actual = git(root, 'hash-object', '--no-filters', '--stdin-paths',
                 data=('\n'.join(protected) + '\n').encode()).decode().splitlines()
    assert len(actual) == len(protected)
    assert all(a == entries[p]['blob'] for p, a in zip(protected, actual)), 'protected byte change'
    for p in ('STATUS.md', 'GAPS.md'):
        old = git(root, 'show', BASE + ':' + p)
        assert (root / p).read_bytes().startswith(old), 'non-append document change'
    changed = set(git(root, 'diff', '--name-only', BASE).decode().splitlines())
    changed.update(git(root, 'ls-files', '--others', '--exclude-standard').decode().splitlines())
    assert all(p in ('STATUS.md', 'GAPS.md', TASK) or p.startswith(PACKET + '/')
               for p in changed), 'outside authorized files'
    for line in git(root, 'diff', '--summary', BASE).decode().splitlines():
        # Staged additions are allowed; existing modes/renames/deletions are not.
        assert line.startswith(' create mode 100644 '), 'mode/rename/delete change'

    ledger = json.loads((packet / 'SOURCE_LEDGER.json').read_text())
    assert ledger['base_head'] == BASE
    assert ledger['base_tree'] == git(root, 'rev-parse', BASE + '^{tree}').decode().strip()
    for item in ledger['files']:
        content = (root / item['path']).read_bytes()
        assert sha(content) == item['sha256'], item['path']
        assert content == git(root, 'show', BASE + ':' + item['path']), item['path']
        lines = content.decode().splitlines()
        for anchor in item['anchors']:
            assert lines[anchor['line'] - 1] == anchor['text'], 'source line changed'

    evidence = json.loads((packet / 'INHERITED_EVIDENCE.json').read_text())
    assert evidence['new_runtime_tests'] == 0 and evidence['base_head'] == BASE
    for group in evidence['source_bindings']:
        validation = json.loads((root / group['validation']).read_text())
        if group['selector'] == 'bridge05':
            values = next(c['receipt']['sources'] for c in validation['commands']
                          if c['label'] == 'bridge05')
        else:
            values = validation[group['selector']]
        for item in group['files']:
            current = sha((root / item['path']).read_bytes())
            assert item['saved_sha256'] == values[item['path']]
            assert item['current_sha256'] == current
            assert item['relation'] == ('MATCH' if current == item['saved_sha256'] else 'SUPERSEDED')
            if item['relation'] == 'SUPERSEDED':
                assert group['validation'] == 'docs/m6/validation.json'
                assert item['path'] == 'flash/m6_iteration.py'
                assert item['covered_by'] == 'task09 bridge05'
    for group in evidence['review_logs']:
        index = json.loads((root / group['index']).read_text())
        assert len(group['files']) == len(index['logs'])
        for item, saved in zip(group['files'], index['logs']):
            assert item['path'] == saved['path']
            assert item['sha256'] == saved['review_sha256'] == sha((root / item['path']).read_bytes())
    for group in evidence['inline_review_logs']:
        index = json.loads((root / group['index']).read_text())
        assert len(group['streams']) == len(index['logs']) * 2
        for item in group['streams']:
            saved = next(x for x in index['logs'] if x['label'] == item['label'])[item['stream']]
            assert sha(saved['text'].encode()) == saved['sanitized_sha256'] == item['sha256']

    checklist = json.loads((packet / 'CHECKLIST.json').read_text())
    assert checklist['base_head'] == BASE and checklist['execution_authorized'] is False
    assert checklist['admission'] == 'BLOCKED'
    audit = (packet / 'AUDIT.md').read_text()
    for category, prefix, count in [('blockers', 'B', 10), ('accepted_deviations', 'A', 8),
                                    ('gpu_queue', 'U', 7)]:
        ids = [x['id'] for x in checklist[category]]
        first = 0 if prefix == 'U' else 1
        assert ids == [prefix + str(n).zfill(2) for n in range(first, first + count)]
        assert all(x in audit for x in ids)
    assert all(x['status'] == 'NOT_RUN' and x['authorized'] is False
               for x in checklist['gpu_queue'])
    assert checklist['new_scientific_decisions'] == []

    controller = (root / 'flash/m6_controller.py').read_text()
    assert "TRIGGER = 'MANUAL_TEST_TRIGGER'" in controller
    assert "if trigger != TRIGGER:" in controller
    assert "only MANUAL_TEST_TRIGGER is approved" in controller
    bridge = ast.parse((root / 'flash/m6_abi2_bridge.py').read_text())
    global_ = next(n for n in bridge.body if isinstance(n, ast.ClassDef)
                   and n.name == 'Abi2GlobalController')
    assert not any(isinstance(n, ast.FunctionDef) and n.name == 'start' for n in global_.body)
    assert 'analyze_approved_g04(bundle)' in (root / 'flash/m6_abi2_bridge.py').read_text()
    assert 'collected_at_seconds=self.now' in (root / 'flash/m6_abi2_bridge.py').read_text()
    assert "'single_host_cpu_simulation_monotonic_seconds'" in controller

    # Only local Markdown file links; official external URLs have separate provenance.
    for path in packet.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if not target.startswith(('https://', 'http://', '#')):
                assert (path.parent / target.split('#')[0]).exists(), (path.name, target)
    for path in packet.glob('*.json'):
        json.loads(path.read_text())
    return dict(status='DOCUMENT_STATIC_INTEGRITY_PASS_ONLY', base_head=BASE,
                base_tree=ledger['base_tree'], base_files=len(entries),
                protected_byte_identical=len(protected), append_only_files=2,
                changed_paths=sorted(changed), source_files=len(ledger['files']),
                inherited_source_bindings=sum(len(g['files']) for g in evidence['source_bindings']),
                inherited_review_logs=sum(len(g['files']) for g in evidence['review_logs']),
                inherited_inline_review_streams=sum(len(g['streams']) for g in evidence['inline_review_logs']),
                runtime_tests_executed=0, native_fits=0, gpu='NOT_RUN', redis='NOT_RUN',
                server='NOT_PROBED', m6b_admission='BLOCKED',
                checker_sha256=sha(Path(__file__).read_bytes()))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = verify(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
