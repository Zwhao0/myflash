"""ADAPTATION: synthetic publication checks, not GPU experiments."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'privacy_check', Path(__file__).resolve().parents[1] / 'scripts/privacy_check.py'
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PublicationChecks(unittest.TestCase):
    def categories(self, text, path='example.txt'):
        return {category for _, category in checker.scan_text(path, text)}

    def test_credentials_detected_without_returning_value(self):
        value = 'gh' + 'p_' + 'x' * 36
        findings = checker.scan_text('example', value)
        self.assertIn('credential_signature', {x[1] for x in findings})
        self.assertNotIn(value, repr(findings))
        self.assertIn('credential_assignment', self.categories('password="' + 'x' * 16 + '"'))
        self.assertIn('url_credentials', self.categories('https://' + 'user:pass@' + 'example.invalid'))

    def test_machine_identity_detected(self):
        self.assertIn('user_home', self.categories('/' + 'home/' + 'person/project'))
        self.assertIn('machine_hostname', self.categories('gpu-' + '01'))
        self.assertIn('gpu_uuid', self.categories('GPU-' + '12345678-' + '1234-' * 3 + '123456789abc'))
        self.assertIn('mac_address', self.categories(':'.join(['ab'] * 6)))

    def test_ip_and_locked_version_are_distinct(self):
        address = '.'.join(['10', '20', '30', '40'])
        self.assertIn('ipv4_address', self.categories(address))
        locked = 'library==' + address + ' --hash=sha256:' + 'a' * 64
        self.assertEqual(self.categories(locked, 'requirements.lock'), set())
        self.assertIn('ipv4_address', self.categories(locked + ' # server', 'requirements.lock'))

    def test_placeholders_loopback_and_documentation_addresses(self):
        self.assertEqual(self.categories('password="<redacted>" node-0 <project> 127.0.0.1 0.0.0.0 192.0.2.1'), set())

    def test_private_files_cannot_be_published(self):
        for name in ['.env', '.env.production', 'runs/run/manifest.json', '.ssh/config', 'key.pem', 'raw.ndjson', 'config.local.json', 'raw.log']:
            self.assertTrue(checker.sensitive_path(name), name)
        for name in ['.env.example', 'docs/m0/01_bootstrap.log', 'native/probe.cpp']:
            self.assertFalse(checker.sensitive_path(name), name)

    def test_only_exact_reviewed_synthetic_raw_bytes_are_allowed(self):
        path = 'tests/m4_cases/raw_ndjson_valid/rank-0.ndjson'
        data = (checker.ROOT / path).read_bytes()
        self.assertTrue(checker.reviewed_synthetic_fixture(path, data))
        self.assertFalse(checker.reviewed_synthetic_fixture(path, data + b'\n'))
        self.assertFalse(checker.reviewed_synthetic_fixture('tests/m4_cases/new/rank-0.ndjson', data))
        self.assertFalse(checker.reviewed_synthetic_fixture('runs/run/raw.ndjson', data))
        self.assertTrue(checker.sensitive_path(path))


if __name__ == '__main__':
    unittest.main()
