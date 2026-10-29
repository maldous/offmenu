"""End-to-end bounded worker tests; only authored fixtures are admitted in memory."""
import copy
import dataclasses
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import execution
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.national_field_origins import policy_sha256
from offmenu.refresh.execution_worker import NATIONAL_ORIGIN_POLICY_SHA256
from test_national_field_origins import afcd, mext, save

ROOT = Path(__file__).resolve().parents[1]


def build_fixture(root, source):
    bundle = root / 'bundle'
    bundle.mkdir()
    if source == 'afcd':
        _, rows = afcd(bundle)
        save(bundle, 'Nutrient-details.xlsx', {'Authored': [['fixture metadata']]})
    else:
        _, rows = mext(bundle)
        shutil.rmtree(bundle / 'legacy-output')
    (bundle / 'rights.json').write_text('{"fixture":true,"productionRights":false}')
    (bundle / 'scope.json').write_text('{"fixture":true,"productionScope":false}')
    inputs = tuple((p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(bundle.iterdir()))
    mapping = {name: digest for name, size, digest in inputs}
    entry = execution.Admission(source, execution._release(source)['releaseId'], inputs,
        '2026-10-18T00:00:00Z', mapping['rights.json'], mapping['scope.json'], len(rows))
    return bundle, entry


class NationalOriginWorkerTests(unittest.TestCase):
    def test_worker_serializes_origins_and_qualification_checks_them(self):
        self.assertEqual(policy_sha256(), NATIONAL_ORIGIN_POLICY_SHA256)
        for source in ('afcd', 'mext'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle, entry = build_fixture(root, source)
                output = root / 'candidate'
                with patch.dict(execution.ADMISSIONS, {source: entry}):
                    receipt = execution.execute(source, bundle, output, repository=ROOT)
                raw = (output / 'candidate.jsonl').read_bytes()
                with gzip.open(output / 'normalized.jsonl.gz', 'rb') as stream:
                    self.assertEqual(raw, stream.read())
                rows = [json.loads(line)[0] for line in raw.splitlines()]
                manifest = json.loads((output / 'manifest.json').read_text())
                self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest['candidateSha256'])
                self.assertEqual(len(raw), manifest['candidateBytes'])
                self.assertEqual(policy_sha256(), manifest['fieldOriginPolicySha256'])
                self.assertEqual(policy_sha256(), receipt['fieldOriginPolicySha256'])
                self.assertIsNone(receipt['acceptedCount'])
                self.assertEqual('not-performed', receipt['qualification'])
                pins = {name: digest for name, size, digest in entry.inputs}
                for row in rows:
                    self.assertEqual([], field_origin_errors(row, pins, policy_pins=(policy_sha256(),)))
                origins = rows[0]['provenance']['fieldOrigins']
                self.assertEqual('source', origins['/data/foodName']['kind'])
                self.assertEqual('constant', origins['/data/basis/amount']['kind'])
                self.assertEqual('derived', origins['/data/nutrients/energy/value']['kind'])
                self.assertEqual('D4' if source == 'afcd' else 'D13', origins['/data/foodName']['cell'])
                # A complete exact-row schema is appropriate only for this tiny
                # authored fixture. It is never a production source schema.
                schemas = {'nutrientProfile': {'anyOf': [{'const': copy.deepcopy(row)} for row in rows]}}
                assets = tuple(Asset(*item) for item in entry.inputs)
                by_name = {asset.path: asset for asset in assets}
                visited = []
                def semantic(row):
                    visited.append(row['id'])
                    return field_origin_errors(row, pins, policy_pins=(NATIONAL_ORIGIN_POLICY_SHA256,))
                contract = SourceContract(source, entry.release_id, 'authored-origin-fixture',
                    entry.acquired_at, assets, entry.expected_records, ids_digest(r['id'] for r in rows),
                    schemas, fingerprint(schemas), semantic, policy_sha256(),
                    by_name['rights.json'], by_name['scope.json'],
                    frozenset(('retain', 'parse', 'transform')), fixture=True)
                result = qualify(contract, bundle, output / 'candidate.jsonl', manifest)
                self.assertTrue(result['qualified'], result['errors'])
                self.assertTrue(result['fixture'])
                self.assertEqual(len(rows), len(visited))
                # Recompute custody after deleting an origin: qualification must
                # reject semantics, not merely notice the digest changed.
                rows[0]['provenance']['fieldOrigins'].pop('/data/foodName')
                altered = b''.join(json.dumps([row], sort_keys=True).encode() + b'\n' for row in rows)
                (output / 'tampered.jsonl').write_bytes(altered)
                altered_manifest = {**manifest, 'candidateSha256':hashlib.sha256(altered).hexdigest(), 'candidateBytes':len(altered)}
                rejected = qualify(contract, bundle, output / 'tampered.jsonl', altered_manifest)
                self.assertFalse(rejected['qualified'])
                self.assertIn('field-origin-inventory-mismatch', rejected['errors'])
        self.assertEqual({}, execution.ADMISSIONS)

    def test_origin_expansion_retains_bounds_and_never_emits_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, entry = build_fixture(root, 'afcd')
            # Isolated test copy lowers a limit to make a small authored input
            # cross the output bound after origins are attached. No production
            # limit, script pin, or admission is changed.
            isolated = root / 'bounded-worker'
            shutil.copytree(ROOT / 'src/offmenu', isolated / 'src/offmenu', ignore=shutil.ignore_patterns('__pycache__'))
            implementation = isolated / 'src/offmenu/refresh/execution.py'
            code = implementation.read_text()
            self.assertIn('MAX_OUTPUT = 256 * 1024**2', code)
            implementation.write_text(code.replace('MAX_OUTPUT = 256 * 1024**2', 'MAX_OUTPUT = 15000'))
            destination = root / 'oversize'
            request = {'entry':dataclasses.asdict(entry), 'bundle':str(bundle), 'destination':str(destination), 'repository':str(ROOT)}
            worker = isolated / 'src/offmenu/refresh/execution_worker.py'
            diagnostic_call = 'import runpy; runpy.run_path(' + repr(str(worker)) + ')["main"]()'
            process = subprocess.run([sys.executable, '-I', '-c', diagnostic_call],
                                     input=json.dumps(request).encode(), capture_output=True, timeout=30)
            self.assertNotEqual(0, process.returncode)
            self.assertIn(b'origin-expanded-output-bound-exceeded', process.stderr)
            with gzip.open(destination / 'normalized.jsonl.gz', 'rb') as stream:
                self.assertLess(len(stream.read()), 15000)
            self.assertFalse((destination / 'execution-receipt.json').exists())
            self.assertFalse((destination / 'candidate.jsonl').stat().st_size > 15000)
            self.assertEqual(256 * 1024**2, execution.MAX_OUTPUT)
            self.assertEqual({}, execution.ADMISSIONS)
