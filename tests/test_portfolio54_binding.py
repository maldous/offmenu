"""Authored metadata only: never read retained originals, stages or manifests."""
from copy import deepcopy
from datetime import timedelta
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import acceptance as q
from offmenu.refresh import portfolio54_binding as b
from offmenu.refresh.core import timestamp


class Portfolio54Tests(unittest.TestCase):
    def authored_binding(self):
        return {'country': 'AUTHORED', 'dataType': 'authored-metadata-only',
                'sourceId': 'worker54-authored-metadata', 'releaseId': 'test-v1',
                'targetSourceId': 'worker54-authored-original',
                'targetReleaseId': 'test-v1', 'originalSha256': 'a' * 64,
                'manifest': {'path': 'authored.json', 'sha256': 'b' * 64},
                'originalAcquiredAt': '2026-10-14T00:00:00Z', 'holds': [],
                'fields': {'unknown': {'value': None, 'unknownSymbol': 'authored-unknown'}}}

    def observation(self, country='KM'):
        d = b.bindings()[country]
        return {'sourceId': d['targetSourceId'], 'releaseId': d['targetReleaseId'],
                'manifestSha256': d['manifest']['sha256'],
                'originalSha256': d['originalSha256'],
                'acquiredAt': d['originalAcquiredAt'],
                'validatedAt': '2026-10-18T00:00:00Z'}

    def test_valid_metadata_remains_held_and_never_admitted(self):
        r = b.plan('KM', self.observation(), now='2026-10-18T01:00:00Z')
        self.assertEqual(r['inputStatus'], 'valid')
        self.assertEqual(r['disposition'], 'held')
        self.assertEqual(r['originalAgeSeconds'],
                         (timestamp('2026-10-18T01:00:00Z') - timestamp(
                             self.observation()['acquiredAt'])).total_seconds())
        self.assertEqual(r['validationAgeSeconds'], 3600)
        self.assertEqual(r['cacheStatus'], 'minimum-reuse-window')
        for key in ('fetchAllowed', 'sourceBodyAccessAllowed', 'qualified', 'accepted'):
            self.assertFalse(r[key])
        self.assertIn('readme-403-no-retry', r['holds'])
        # Caller cannot introduce a grant/clear holds through observation JSON.
        modified = self.observation(); modified['holds'] = []
        self.assertEqual(b.plan('KM', modified, now='2026-10-18T01:00:00Z')[
            'inputStatus'], 'malformed')

    def test_missing_malformed_and_multiple_diagnostics(self):
        self.assertEqual(b.plan('KM', None, now='2026-10-18T00:00:00Z')[
            'inputStatus'], 'missing')
        for value in ([], 'secret://do-not-echo', {'unexpected': True}):
            r = b.plan('KM', value, now='2026-10-18T00:00:00Z')
            self.assertEqual(r['inputStatus'], 'malformed')
            self.assertNotIn('secret', json.dumps(r))
        value = self.observation(); value['manifestSha256'] = '0' * 64
        value['acquiredAt'] = 'not-a-time'; value['validatedAt'] = None
        r = b.plan('KM', value, now='2026-10-18T00:00:00Z')
        self.assertTrue({'input-identity-or-pin-mismatch', 'input-time-malformed',
                         'validation-time-required', 'source-processing-held'} <= set(r['diagnostics']))

    def test_revalidation_does_not_reset_original_cache_clock(self):
        value = self.observation()
        original = timestamp(value['acquiredAt'])
        now = original + timedelta(seconds=b.MIN_TTL)
        value['validatedAt'] = now.isoformat()
        r = b.plan('KM', value, now=now.isoformat())
        self.assertEqual(r['inputStatus'], 'stale')
        self.assertEqual(r['originalAgeSeconds'], b.MIN_TTL)
        self.assertEqual(r['validationAgeSeconds'], 0)
        self.assertIn('original-cache-window-elapsed', r['diagnostics'])
        self.assertFalse(r['fetchAllowed'])
        # An observation cannot replace the historical evidence timestamp.
        value['acquiredAt'] = now.isoformat()
        r = b.plan('KM', value, now=now.isoformat())
        self.assertIn('acquisition-time-evidence-mismatch', r['diagnostics'])

    def test_stale_validation_unknown_acquisition_and_invalid_clocks(self):
        value = self.observation()
        value['validatedAt'] = '2026-10-14T23:00:00Z'
        r = b.plan('KM', value, now='2026-11-15T00:00:00Z')
        self.assertIn('input-validation-stale', r['diagnostics'])
        r = b.plan('KP', self.observation('KP'), now='2026-10-18T01:00:00Z')
        self.assertIn('acquisition-time-required', r['diagnostics'])
        self.assertIn('original-acquisition-evidence-required', r['diagnostics'])
        self.assertIsNone(r['originalAgeSeconds'])
        for clock in ('2026-10-18T00:00:00', 'bad', None):
            self.assertIn('binding-clock-invalid', b.plan('KM', self.observation(),
                          now=clock)['diagnostics'])
        value = self.observation(); value['validatedAt'] = '2026-10-14T00:00:00Z'
        self.assertIn('validation-before-acquisition', b.plan('KM', value,
                      now='2026-10-18T01:00:00Z')['diagnostics'])

    def test_literal_declarations_and_exact_per_datum_origins(self):
        for country in ('KM', 'KN', 'KP', 'KR'):
            row = b.metadata_record(country)
            self.assertEqual(b.metadata_semantic_errors(country, row), [])
            mutated = deepcopy(row)
            name = next(iter(mutated['data']))
            mutated['data'][name] = 'invented'
            self.assertIn('worker54-declaration-mismatch',
                          b.metadata_semantic_errors(country, mutated))
            mutated = deepcopy(row)
            mutated['provenance']['fieldOrigins'] = {}
            self.assertIn('field-origin-inventory-mismatch',
                          b.metadata_semantic_errors(country, mutated))
        km = b.metadata_record('KM')
        self.assertIsNone(km['data']['referenceMass'])
        self.assertEqual(km['data']['unitD'], 'Kcal')
        self.assertEqual(km['data']['unitN'], 'mgrs')
        self.assertEqual(km['provenance']['fieldOrigins']['/data/unitN']['sourceField'],
                         '/columnProposals/13/literalUnitToken')
        self.assertIn('readme-403-no-retry', km['holds'])
        self.assertFalse(km['sourceProcessingAllowed'])
        # Python numeric equality must not hide changed JSON representation.
        kr = b.metadata_record('KR'); kr['data']['editionClaim'] = 2016.0
        self.assertIn('worker54-declaration-mismatch', b.metadata_semantic_errors('KR', kr))

    def test_noop_identity_includes_binding_policy_not_validation_age(self):
        # Separate authored identity, not a real country with holds removed.
        # Public plan() cannot select/register this fixture descriptor.
        d = self.authored_binding()
        value = {'sourceId': d['targetSourceId'], 'releaseId': d['targetReleaseId'],
                 'manifestSha256': d['manifest']['sha256'],
                 'originalSha256': d['originalSha256'],
                 'acquiredAt': d['originalAcquiredAt'],
                 'validatedAt': '2026-10-18T00:00:00Z'}
        first = b._plan(d, value, now='2026-10-18T01:00:00Z')
        self.assertEqual(first['replay'], 'metadata-ready')
        value['validatedAt'] = '2026-10-18T00:30:00Z'
        second = b._plan(d, value, now='2026-10-18T01:00:00Z',
                         previous_key=first['replayKey'])
        self.assertEqual(second['replay'], 'noop')
        d['fields']['newUnknown'] = {'value': None, 'unknownSymbol': 'authored-unknown'}
        changed = b._plan(d, value, now='2026-10-18T01:00:00Z',
                          previous_key=first['replayKey'])
        self.assertEqual(changed['replay'], 'metadata-ready')
        self.assertNotEqual(changed['replayKey'], first['replayKey'])

    def test_missing_schema_dependency_fails_closed(self):
        with patch.object(b, 'Draft202012Validator', None):
            r = b.plan('KM', self.observation(), now='2026-10-18T01:00:00Z')
        self.assertIn('schema-validator-unavailable', r['diagnostics'])
        self.assertEqual(r['inputStatus'], 'malformed')
        self.assertFalse(r['fetchAllowed'])

    def test_shared_qualifier_accepts_only_authored_fixture_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bundle = root / 'bundle'; bundle.mkdir()
            payload = b'{"note":"AUTHORED metadata fixture; no publisher data"}'
            rights = b'{"scope":"authored fixture only"}'
            scope = b'{"expectedIds":["offmenu:worker54:KM"]}'
            assets = []
            for name, content in [('authored.json', payload), ('rights.json', rights),
                                  ('scope.json', scope)]:
                (bundle / name).write_bytes(content)
                assets.append(q.Asset(name, len(content), hashlib.sha256(content).hexdigest()))
            d = {'country': 'KM', 'dataType': 'authored-metadata-fixture',
                 'sourceId': 'worker54-authored', 'releaseId': 'test-only-v1',
                 'metadataValidatedAt': '2026-10-18T00:00:00Z',
                 'manifest': {'path': 'authored.json', 'sha256': assets[0].sha256},
                 'fields': {'note': {'value': 'AUTHORED metadata fixture; no publisher data',
                            'selector': '/note', 'sourceRecordId': 'authored'},
                            'basis': {'value': None, 'unknownSymbol': 'authored-unknown'}}}
            row = b._record(d)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(q.canonical([row]) + b'\n')
            schema = {'type': 'object', 'const': row}
            schemas = {row['kind']: schema}
            contract = q.SourceContract(source_id=d['sourceId'], release_id=d['releaseId'],
                scope_id='authored-worker54-metadata-only', acquired_at=d['metadataValidatedAt'],
                inputs=tuple(assets), expected_records=1,
                expected_ids_sha256=q.ids_digest([row['id']]), schemas=schemas,
                schemas_sha256=q.fingerprint(schemas),
                semantic_validator=partial(b._semantic_errors, d),
                policy_sha256=q.fingerprint(d), rights_evidence=assets[1],
                scope_evidence=assets[2], permitted_operations=frozenset(('retain', 'parse', 'transform')),
                fixture=True)
            raw = candidate.read_bytes()
            manifest = {'sourceId': d['sourceId'], 'releaseId': d['releaseId'],
                'acquiredAt': d['metadataValidatedAt'], 'normalizedRecords': 1,
                'candidateBytes': len(raw), 'candidateSha256': hashlib.sha256(raw).hexdigest(),
                'rightsEvidenceSha256': assets[1].sha256,
                'scopeEvidenceSha256': assets[2].sha256,
                'inputFiles': [vars(a) for a in assets]}
            result = q.accept(contract, bundle, candidate, manifest)
            self.assertTrue(result['accepted'], result['errors'])
            self.assertFalse(result['productionAccepted'])
            self.assertFalse(result['countryCoverageComplete'])
            (bundle / 'authored.json').write_text('corrupted')
            rejected = q.qualify(contract, bundle, candidate, manifest)
            self.assertIn('input-custody-mismatch', rejected['errors'])

    def test_cli_is_deterministic_bounded_stdin_only_and_isolates_errors(self):
        cmd = [sys.executable, '-m', 'offmenu.refresh.portfolio54_binding',
               '--country', 'KM', '--now', '2026-10-18T01:00:00Z', '--observation', '-']
        raw = json.dumps(self.observation()).encode()
        first = subprocess.run(cmd, input=raw, capture_output=True)
        second = subprocess.run(cmd, input=raw, capture_output=True)
        self.assertEqual(first.returncode, 2)  # Source held, not execution failure.
        self.assertEqual(first.stdout, second.stdout)
        declaration = subprocess.run(cmd[:-2] + ['--declaration'], capture_output=True)
        self.assertEqual(declaration.returncode, 0)
        self.assertEqual(json.loads(declaration.stdout), b.metadata_record('KM'))
        for raw in (b'{"sourceId":1,"sourceId":2}', b'x' * (b.MAX_METADATA + 1)):
            failed = subprocess.run(cmd, input=raw, capture_output=True)
            self.assertEqual(json.loads(failed.stdout)['diagnostics'], ['metadata-request-invalid'])
        # Failure does not contaminate an independent country's fixed report.
        before = b.plan('KR', None, now='2026-10-18T01:00:00Z')
        b.plan('KM', 'malformed', now='bad')
        self.assertEqual(before, b.plan('KR', None, now='2026-10-18T01:00:00Z'))

    def test_deep_bounded_json_returns_typed_refusal_and_peer_stays_usable(self):
        command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio54_binding',
                   '--country', 'KM', '--now', '2026-10-18T01:00:00Z', '--observation', '-']
        for payload in (b'[' * 30000 + b'0' + b']' * 30000,
                        b'{"a":' * 10000 + b'0' + b'}' * 10000):
            with self.subTest(prefix=payload[:1]):
                self.assertEqual(len(payload), 60001)
                self.assertLess(len(payload), b.MAX_METADATA)
                refused = subprocess.run(command, input=payload, capture_output=True, timeout=5)
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stderr, b'')
                result = json.loads(refused.stdout)
                self.assertEqual(result['inputStatus'], 'malformed')
                self.assertEqual(result['diagnostics'], ['metadata-request-invalid'])
                for flag in ('fetchAllowed', 'sourceBodyAccessAllowed', 'qualified', 'accepted'):
                    self.assertFalse(result[flag])
                peer = subprocess.run(command[:5] + ['KN'] + command[6:-2],
                                      capture_output=True, timeout=5)
                self.assertEqual(peer.returncode, 2)
                self.assertEqual(peer.stderr, b'')
                self.assertEqual(json.loads(peer.stdout)['inputStatus'], 'missing')


if __name__ == '__main__':
    unittest.main()
