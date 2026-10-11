"""ADAPTATION static source/evidence preservation, no runtime imports/fits."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = '0dd0e1c5cac043aef1449d5cfe9e74ed38447cf3'
PREFIX = 'docs/m6b-ready/task12-auto-profile/'
ALLOWED = {'flash/m6_controller.py', 'flash/automatic_profile.py',
           'tests/task12_auto_profile.py', 'tasks/06b_ready_task12_auto_profile.md',
           'STATUS.md', 'GAPS.md'}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    rows = git('ls-tree', '-rz', BASE).split(b'\0')
    # Batch the same pinned blobs. The original per-file Git subprocess reads
    # took85.7s and final verify02 timed out90s; assertions are unchanged.
    blobs = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '--batch'],
                           input=b''.join(row.split(b'\t')[0].split()[2]+b'\n'
                                          for row in rows if row),
                           check=True, capture_output=True).stdout
    offset=0; baseline={}
    for raw in rows:
        if not raw: continue
        end=blobs.index(b'\n',offset); header=blobs[offset:end].split()
        assert header[1]==b'blob'
        start=end+1; size=int(header[2]); path=raw.split(b'\t')[1].decode()
        baseline[path]=blobs[start:start+size]; offset=start+size+1
    assert offset==len(blobs)
    protected = 0; append_only = 0; base_names = set()
    for raw in rows:
        if not raw: continue
        meta, name = raw.split(b'\t'); path = name.decode(); base_names.add(path)
        old = baseline[path]
        new = (ROOT/path).read_bytes()
        if path in ('STATUS.md', 'GAPS.md'):
            assert new.startswith(old), path; append_only += 1
        elif path != 'flash/m6_controller.py':
            assert new == old, path; protected += 1
    files = set(git('ls-files', '-z').decode().split('\0')) | set(
        git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0'))
    files.discard('')
    changed = [p for p in sorted(files) if p not in base_names or
               baseline[p] != (ROOT/p).read_bytes()]
    assert all(p in ALLOWED or p.startswith(PREFIX) for p in changed), changed
    assert not (base_names-files), 'deleted tracked paths'
    modes = {row.split(b'\t')[1].decode(): row.split()[0].decode()
             for row in rows if row}
    for raw in git('ls-files', '-s', '-z').split(b'\0'):
        if raw:
            meta, p = raw.split(b'\t'); p=p.decode()
            if p in modes: assert meta.split()[0].decode()==modes[p], p
    sys.path.insert(0, str(ROOT/'scripts'))
    from privacy_check import scan_text, sensitive_path
    findings=[]
    for p in changed:
        data = (ROOT/p).read_bytes()
        if p in ('STATUS.md', 'GAPS.md'): data=data[len(baseline[p]):]
        assert not sensitive_path(p), p
        findings += [dict(path=p,line=n,category=c) for n,c in scan_text(p,data.decode())]
    assert not findings, findings
    ledger=json.loads((ROOT/PREFIX/'SOURCE_LEDGER.json').read_text())
    for item in ledger['sources']:
        data=baseline[item['path']]
        assert sha(data)==item['sha256'], item['path']
    validation=json.loads((ROOT/PREFIX/'validation.json').read_text())
    for run in validation['runs']:
        assert run['exit_code']==0 and run['timeout'] is False
        for p, digest in run['executed_source_sha256'].items():
            assert sha((ROOT/p).read_bytes())==digest, p
        for stream in ('stdout','stderr'):
            assert sha((ROOT/PREFIX/run[stream+'_path']).read_bytes())==run[stream+'_public_sha256']
    output=dict(status='STATIC_PRESERVATION_PASS', base=BASE, base_files=len(base_names),
                protected_files=protected, append_only=append_only,
                changed_paths=changed, changed_text_findings=0,
                source_bindings=len(ledger['sources']), verified_runs=len(validation['runs']))
    print(json.dumps(output,indent=2))
    return 0

if __name__=='__main__': sys.exit(main())
