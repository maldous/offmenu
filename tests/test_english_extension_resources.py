"""Synthetic work bounds and an offline wheel-resource regression only."""
from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import offmenu.refresh.english_extension as english
from offmenu.refresh.acceptance import ids_digest, qualify
from test_english_extension import Fixture, WORK, digest, encode


class EvidenceWorkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))
        self.calls = []
        original = self.f.evidence
        def resolve(pin):
            self.calls.append((pin['path'], pin['sha256']))
            return original(pin)
        self.f.evidence = resolve

    def test_repeated_large_pin_is_resolved_and_hashed_once(self):
        payload = b'X' * (1024 * 1024)
        pin = self.f.pin('large-evidence.bin', payload)
        self.f.t['evidence'] = [dict(pin) for _ in range(64)]
        sha256 = hashlib.sha256
        hashed = []
        def count(data=b'', *args, **kwargs):
            if data is payload:
                hashed.append(len(data))
            return sha256(data, *args, **kwargs)
        with patch.object(english.hashlib, 'sha256', side_effect=count):
            self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f), ())
        self.assertEqual(self.calls.count((pin['path'], pin['sha256'])), 1)
        self.assertEqual(hashed, [len(payload)])

    def test_distinct_large_pins_stop_at_cumulative_byte_budget(self):
        self.f.policy = replace(self.f.policy, max_total_evidence_bytes=2 * 1024 * 1024)
        self.f.t['evidence'] = [self.f.pin(f'large-{i}.bin', bytes([i]) * (1024 * 1024)) for i in range(4)]
        self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f),
                         ('english-evidence-work-bound-exceeded',))
        self.assertEqual(len([p for p, _ in self.calls if p.startswith('large-')]), 2)

    def test_unique_resolver_calls_stop_before_dispatch(self):
        self.f.policy = replace(self.f.policy, max_evidence_reads=2)
        self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f),
                         ('english-evidence-work-bound-exceeded',))
        self.assertEqual(len(self.calls), 2)

    def test_many_tiny_pins_cannot_bypass_read_budget(self):
        self.f.policy = replace(self.f.policy, max_evidence_reads=12)
        self.f.t['evidence'] = [self.f.pin(f'tiny-{i}.bin', b'x') for i in range(100)]
        self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f),
                         ('english-evidence-work-bound-exceeded',))
        self.assertEqual(len(self.calls), 12)

    def test_cache_does_not_survive_a_validation_call(self):
        pin = self.f.pin('versioned.bin', b'original')
        self.f.t['evidence'] = [pin, dict(pin)]
        self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f), ())
        self.f.blobs[pin['path']] = b'changed'
        self.assertEqual(english.validate_extension(self.f.ext, self.f.policy, self.f),
                         ('english-evidence-pin-mismatch',))
        self.assertEqual(self.calls.count((pin['path'], pin['sha256'])), 2)

    def test_cache_key_includes_hash_not_only_path(self):
        pins = [{'path': 'same.bin', 'sha256': digest(raw)} for raw in (b'first', b'second')]
        data = {pin['sha256']: raw for pin, raw in zip(pins, (b'first', b'second'))}
        def resolve(pin):
            self.calls.append(pin['sha256'])
            return data[pin['sha256']]
        self.f.evidence = resolve
        check = english._Check(self.f.policy, self.f)
        self.assertEqual(check.evidence(pins[0]), b'first')
        self.assertEqual(check.evidence(pins[1]), b'second')
        self.assertEqual(check.evidence(dict(pins[0])), b'first')
        self.assertEqual(self.calls, [p['sha256'] for p in pins])

    def test_exact_budget_and_verified_repeat(self):
        check = english._Check(replace(self.f.policy, max_total_evidence_bytes=4, max_evidence_reads=2), self.f)
        first = self.f.pin('one', b'ab'); second = self.f.pin('two', b'cd')
        self.assertEqual(check.evidence(first), b'ab')
        self.assertEqual(check.evidence(second), b'cd')
        self.assertEqual(check.evidence(dict(first)), b'ab')
        with self.assertRaisesRegex(english.EvidenceError, '^english-evidence-work-bound-exceeded$'):
            check.evidence(self.f.pin('three', b'e'))
        self.assertEqual(len(self.calls), 2)

    def test_invalid_budget_configuration_fails_closed(self):
        for name, value in [('max_evidence_reads', True), ('max_evidence_reads', 0),
                            ('max_total_evidence_bytes', -1), ('max_total_evidence_bytes', 1.5)]:
            with self.subTest(name=name, value=value):
                policy = replace(self.f.policy, **{name: value})
                self.assertEqual(english.validate_extension(self.f.ext, policy, self.f),
                                 ('english-evidence-work-bound-exceeded',))
                self.assertEqual(self.calls, [])

    def test_existing_qualify_boundary_retains_work_budget_diagnostic(self):
        self.f.policy = replace(self.f.policy, max_evidence_reads=2)
        root = Path(self.temp.name); bundle = root / 'outer-inputs'; bundle.mkdir()
        for name, raw in [('original.txt', self.f.text.encode()), ('rights.json', b'{}'), ('scope.json', b'{}')]:
            (bundle / name).write_bytes(raw)
        contract = replace(self.f.original_contract, expected_ids_sha256=ids_digest(['budget-fixture']),
                           semantic_validator=english.semantic_validator(self.f.policy, self.f))
        row = {'id': 'budget-fixture', 'kind': 'sourceAssertion', 'schemaVersion': '1.0',
               'provenance': {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                              'fetchedAt': contract.acquired_at}, 'data': self.f.ext}
        raw = encode([row]) + b'\n'; candidate = root / 'outer.jsonl'; candidate.write_bytes(raw)
        manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                    'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                    'rightsEvidenceSha256': contract.rights_evidence.sha256,
                    'scopeEvidenceSha256': contract.scope_evidence.sha256,
                    'candidateBytes': len(raw), 'candidateSha256': digest(raw),
                    'inputFiles': [vars(asset) for asset in contract.inputs]}
        result = qualify(contract, bundle, candidate, manifest, scratch_root=root)
        self.assertFalse(result['qualified'])
        self.assertIn('english-evidence-work-bound-exceeded', result['errors'])
        self.assertTrue(result['fixture'])
        self.assertNotIn('accepted', result)
        self.assertEqual(len(self.calls), 2)


class EnglishWheelResourceTests(unittest.TestCase):
    def test_offline_wheel_isolated_resource_matches_canonical_schema(self):
        repository = Path(__file__).resolve().parents[1]
        expected = hashlib.sha256((repository / 'offmenu/refresh/english_extension.schema.json').read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            root = Path(temporary)
            source = root / 'source'; source.mkdir()
            shutil.copytree(repository / 'offmenu', source / 'offmenu', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(repository / 'pyproject.toml', source / 'pyproject.toml')
            artifacts = root / 'wheels'; artifacts.mkdir()
            guard = "import socket\ndef denied(*a,**k): raise AssertionError('network forbidden')\nsocket.socket.connect=denied\nsocket.create_connection=denied\nsocket.getaddrinfo=denied\n"
            script = guard + 'from setuptools.build_meta import build_wheel\nbuild_wheel(' + repr(str(artifacts)) + ')\n'
            built = subprocess.run([sys.executable, '-I', '-B', '-c', script], cwd=source,
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            wheel, = artifacts.glob('*.whl')
            installed = root / 'isolated-wheel'; installed.mkdir()
            with zipfile.ZipFile(wheel) as archive:
                self.assertIn('offmenu/refresh/english_extension.py', archive.namelist())
                self.assertIn('offmenu/refresh/english_extension.schema.json', archive.namelist())
                for name in archive.namelist():
                    self.assertFalse(Path(name).is_absolute())
                    self.assertNotIn('..', Path(name).parts)
                archive.extractall(installed)
            probe = guard + '''import sys,json,hashlib
from pathlib import Path
from importlib.resources import files
sys.path.insert(0,sys.argv[1])
from offmenu.refresh import english_extension as module
from jsonschema import Draft202012Validator
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
raw=files('offmenu.refresh').joinpath('english_extension.schema.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
schema=json.loads(raw)
Draft202012Validator.check_schema(schema)
assert schema['properties']['schemaVersion']['const']=='offmenu-english-gold-extension/proposal-2'
assert callable(module.EnglishPolicy) and callable(module.validate_extension)
print('isolated-wheel-canonical-english-schema-pass; source/model/network operations=0')
'''
            checked = subprocess.run([sys.executable, '-I', '-B', '-c', probe, str(installed), expected],
                                     cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn('isolated-wheel-canonical-english-schema-pass', checked.stdout)


if __name__ == '__main__':
    unittest.main()
