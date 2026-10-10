"""ADAPTATION: conservative publication checks; never print matched values.

Source: tasks/04_privacy.md and docs/privacy/AUDIT.md. Standard library only.
This is a heuristic text check, not a complete secret scanner or rights review.
"""
import argparse
import hashlib
import ipaddress
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'credential_signature': re.compile(
        r'gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}'
        r'|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}'
        r'|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
        r'|eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'
    ),
    'user_home': re.compile(r'/(?:home|Users)/[A-Za-z0-9_.-]+'),
    'machine_hostname': re.compile(r'\bgpu-0[12]\b'),
    'gpu_uuid': re.compile(r'GPU-[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}'),
    'mac_address': re.compile(r'(?i)(?<![\w:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![\w:])'),
    'url_credentials': re.compile(r'(?i)(?:https?|redis|ssh)://[^\s/:]+:[^\s/@]+@'),
}
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
ASSIGNMENT = re.compile(
    r'''(?i)["']?(?:password|passwd|api_key|access_token|secret_key)["']?\s*[:=]\s*["']([^"'\n]{8,})["']'''
)
LOCK_VERSION = re.compile(r'^\s*[A-Za-z0-9_.-]+==\S+\s+--hash=sha256:[0-9a-f]{64}\s*$')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def scan_text(path, content):
    """Return only line numbers and categories, never original values."""
    findings = []
    for line_number, line in enumerate(content.splitlines(), 1):
        categories = {name for name, rule in RULES.items() if rule.search(line)}
        for match in ASSIGNMENT.finditer(line):
            value = match.group(1)
            if not (value.startswith('<') and value.endswith('>')):
                categories.add('credential_assignment')
        # Exempt the version token only, not an arbitrary line in a lock file.
        address_line = '' if path.endswith('.lock') and LOCK_VERSION.fullmatch(line) else line
        for match in IPV4.finditer(address_line):
            try:
                address = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if address.is_loopback or address.is_unspecified:
                continue
            if any(address in network for network in (
                ipaddress.ip_network('192.0.2.0/24'),
                ipaddress.ip_network('198.51.100.0/24'),
                ipaddress.ip_network('203.0.113.0/24'),
            )):
                continue  # Documentation-only addresses.
            categories.add('ipv4_address')
        findings.extend((line_number, category) for category in sorted(categories))
    return findings


def sensitive_path(path):
    parts = Path(path).parts
    name = Path(path).name
    return (
        any(p in {'runs', 'secrets', 'credentials', '.ssh'} for p in parts)
        or name in {'.env', '服务器.md'}
        or (name.startswith('.env.') and name != '.env.example')
        or name.startswith('config.local.')
        or Path(path).suffix in {'.pem', '.key', '.p12', '.pfx', '.ndjson'}
        or (Path(path).suffix == '.log' and not path.startswith('docs/m0/'))
    )


def reviewed_synthetic_fixture(path, data):
    """Only exact reviewed M4 CPU fixture bytes may bypass the raw-file ban.

    Text content still goes through every identity/credential rule below.
    Source hashes and review scope: docs/privacy/synthetic-fixtures.json.
    """
    if not path.startswith('tests/m4_cases/') or not path.endswith('.ndjson'):
        return False
    manifest = ROOT / 'docs/privacy/synthetic-fixtures.json'
    if not manifest.is_file():
        return False
    expected = {entry['path']: entry['sha256'] for entry in json.loads(manifest.read_text())['files']}
    return expected.get(path) == hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='scan all locally fetched commit trees')
    args = parser.parse_args()
    entries = []
    if args.history:
        seen = set()
        for commit in git('rev-list', '--all').decode().splitlines():
            for row in git('ls-tree', '-rz', commit).split(b'\0'):
                if not row:
                    continue
                meta, path = row.split(b'\t', 1)
                _, kind, sha = meta.decode().split()
                key = (sha, path)
                if kind == 'blob' and key not in seen:
                    seen.add(key)
                    entries.append((path.decode(), git('cat-file', 'blob', sha), sha[:12]))
    else:
        for raw_path in git('ls-files', '-z').split(b'\0'):
            if raw_path:
                path = raw_path.decode()
                entries.append((path, (ROOT / path).read_bytes(), 'worktree'))
    failures = 0
    for path, data, scope in entries:
        if sensitive_path(path) and not reviewed_synthetic_fixture(path, data):
            print(f'{scope} {path}: prohibited_private_file')
            failures += 1
        try:
            content = data.decode('utf-8')
            if '\0' in content:
                raise UnicodeDecodeError('utf-8', data, 0, 1, 'binary NUL')
        except UnicodeDecodeError:
            if path != 'references/chapter3.pdf':
                print(f'{scope} {path}: unreviewed_binary')
                failures += 1
            else:
                print(f'{scope} {path}: NOT_SCANNED_BINARY; redistribution rights pending')
            continue
        for line, category in scan_text(path, content):
            print(f'{scope} {path}:{line}: {category}')
            failures += 1
    print(f'TEXT_CHECK {"FAIL" if failures else "PASS"}; files={len(entries)}; findings={failures}')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
