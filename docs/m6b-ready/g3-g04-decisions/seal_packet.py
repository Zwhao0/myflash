"""ADAPTATION: verify original-byte preservation and decision artifact integrity."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--reviewed-source', type=Path, required=True)
    parser.add_argument('--raw-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    packet = Path(__file__).resolve().parent
    baseline = json.loads(args.baseline.read_text())
    preservation = {'baseline_head': baseline['head'], 'baseline_tree': baseline['tree'],
                    'files': len(baseline['files']), 'reviewed_source_unchanged': True,
                    'candidate_protected_unchanged': True, 'append_only': {}, 'hashes': baseline['files']}
    for rel, original in baseline['files'].items():
        assert sha(args.reviewed_source / rel) == original, ('reviewed source changed', rel)
        path = root / rel
        if rel in ('STATUS.md', 'GAPS.md'):
            before = (args.reviewed_source / rel).read_bytes()
            assert path.read_bytes().startswith(before), ('not append-only', rel)
            preservation['append_only'][rel] = {'before_sha256': original, 'after_sha256': sha(path),
                                               'appended_bytes': len(path.read_bytes()) - len(before)}
        else:
            assert sha(path) == original, ('protected changed', rel)
    data = json.loads((packet / 'matrix.json').read_text())
    raw = json.loads((args.raw_run / 'audit04/matrix.json').read_text())
    assert data['rows'] == raw['rows'] and data['input_sha256'] == raw['input_sha256']
    assert data['raw_matrix_sha256'] == sha(args.raw_run / 'audit04/matrix.json')
    assert raw['auditor_sha256'] == sha(packet / 'audit_matrix.py')
    assert len(data['rows']) == 137 and len(data['policies']) == 288
    assert len(data['fixtures']) == 65 and all(r['status'] == 'PASS' for r in data['fixtures'])
    assert all(row['recommended'].get('live_final_fault_ranks', []) == [] for row in data['rows'])
    assert data['summary']['approval'] is None and data['summary']['new_native_fits'] == 0
    approvals = json.loads((packet / 'APPROVAL_LEDGER.json').read_text())
    assert approvals['approved'] is None and not approvals['final_alert']
    assert all(d['approved_choice'] is None and not d['implementation_authorized'] for d in approvals['dimensions'])
    receipt = json.loads((args.raw_run / 'audit04.receipt.json').read_text())
    assert receipt['exit_code'] == 0 and not receipt['timeout']
    validation = {'status': 'PASS_CPU_READ_ONLY_AUDIT', 'science': 'REQUIRES_OWNER_DECISION',
                  'machine': 'local-macOS', 'platform': platform.platform(), 'python': sys.version,
                  'source_head': baseline['head'], 'source_tree': baseline['tree'],
                  'audit_source_sha256': sha(packet / 'audit_matrix.py'),
                  'sealer_sha256': sha(Path(__file__)), 'matrix_sha256': sha(packet / 'matrix.json'),
                  'raw_matrix_sha256': data['raw_matrix_sha256'], 'summary': data['summary'],
                  'fixture_assertions': '65 unchanged expected assertion sets; 24 valid and 41 rejected',
                  'full_M4_prediction_equality': 32, 'M3_public_stat_windows': 40,
                  'M3_raw_identity_digest_revalidation': 'NOT_RUN; historical evidence inherited',
                  'commands': 'commands.json; exact argv/host/exit/stdout/stderr in private run',
                  'raw_receipt_sha256': sha(args.raw_run / 'audit04.receipt.json'),
                  'new_GPU_runs': 0, 'new_native_fits': 0, 'runtime_installation': 'NOT_RUN',
                  'server_runtime_preservation': 'NOT_PROBED', 'prior_915_cache_gap': 'NOT_CAPTURED unchanged',
                  'historical_rights_privacy': 'DEFERRED/OPEN', 'final_alert': False}
    postflight = {'machine': 'local-macOS', 'scope': 'read-only CPU document analysis',
                  'owned_GPU_jobs_created': 0, 'Redis_processes_created': 0, 'native_workers_created': 0,
                  'services_installed': 0, 'temporary_server_resources': 'NONE_CREATED',
                  'reviewed_checkout_all_1954_bytes_unchanged': True,
                  'task06_protected_files': len(baseline['files']) - 2,
                  'scientific_algorithm_changes': [], 'next_task07': 'NOT_RUN', 'final_alert': False}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in [('preservation.json', preservation), ('validation.json', validation), ('postflight.json', postflight)]:
        encoded = json.dumps(content, ensure_ascii=False, separators=(',', ':')) + '\n'
        (args.output / name).write_text(encoded)
        (packet / name).write_text(encoded)
    print(json.dumps({'status': validation['status'], 'source_files_preserved': preservation['files'],
                      'protected_candidate_files': postflight['task06_protected_files'],
                      'matrix_cells': data['summary']['cells'], 'science': validation['science']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
