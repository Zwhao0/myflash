"""ADAPTATION read-only verification of TASK08 acceptance and base preservation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
DOC = Path(__file__).resolve().parent


def sha(data): return hashlib.sha256(data).hexdigest()


def verify(private_run):
    validation = json.loads((DOC / 'validation.json').read_text())
    for path, expected in validation['final_source_sha256'].items():
        assert sha((ROOT / path).read_bytes()) == expected, path
    checks = []
    for case in validation['commands']:
        receipt = json.loads((private_run / case['label'] / 'receipt.json').read_text())
        assert receipt['exit_code'] == case['exit_code'] and not receipt['timeout'] and receipt['child_waited']
        for name in ('stdout.txt', 'stderr.txt'):
            assert sha((private_run / case['label'] / name).read_bytes()) == receipt[name + '_sha256']
        assert sha((private_run / case['label'] / 'sources.json').read_bytes()) == receipt['sources_sha256']
        if case['label'] in validation['final_test_labels']:
            sources = json.loads((private_run / case['label'] / 'sources.json').read_text())
            for path, expected in validation['final_source_sha256'].items():
                assert sources[path] == expected, (case['label'], path)
        checks.append(dict(label=case['label'], exit_code=receipt['exit_code']))
    preservation = json.loads((DOC / 'preservation.json').read_text())
    base = preservation['base_head']
    entries = subprocess.check_output(['git', 'ls-tree', '-rz', base], cwd=ROOT).split(b'\0')
    pairs = []
    for entry in entries:
        if entry:
            metadata, path = entry.split(b'\t', 1)
            pairs.append((metadata.split()[2].decode(), path.decode()))
    blobs = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                           input=''.join(blob+'\n' for blob, _ in pairs).encode(),
                           capture_output=True, check=True).stdout
    offset = 0; results = []
    for blob, path in pairs:
        end = blobs.index(b'\n', offset)
        fields = blobs[offset:end].split(); size = int(fields[2]); offset = end + 1
        original = blobs[offset:offset+size]; offset += size + 1
        current = (ROOT / path).read_bytes()
        if path in ('STATUS.md', 'GAPS.md'):
            assert current.startswith(original), path
            relation = 'APPEND_ONLY'
        elif path == 'flash/iteration_reporter.py':
            relation = 'ALLOWED_MODIFICATION'
        else:
            assert current == original, path
            relation = 'BYTE_IDENTICAL'
        results.append(dict(path=path, base_sha256=sha(original), relation=relation))
    assert len(results) == preservation['base_files']
    assert sha(json.dumps(results, sort_keys=True, separators=(',', ':')).encode()) == preservation['manifest_sha256']
    print(json.dumps(dict(status='PASS', commands=checks, tracked_base_files=len(results),
                          protected_byte_identical=sum(r['relation']=='BYTE_IDENTICAL' for r in results)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-run', type=Path, required=True)
    args = parser.parse_args()
    verify(args.private_run)
