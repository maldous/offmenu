"""Authored metadata; no retained source bodies, acquisition or live services."""
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import acceptance as q
from offmenu.refresh import portfolio04_binding as b
from offmenu.refresh.reference_adapters import candidate_bytes

FIXTURE = Path(__file__).parent / 'fixtures/portfolio04/metadata.json'
NOW = '2026-10-18T00:00:00Z'


def fixture(raw=None):
    raw = FIXTURE.read_bytes() if raw is None else raw
    fields = {k: {'evidence': 'fixture', 'selector': '/' + k}
              for k in json.loads(FIXTURE.read_bytes())}
    profile = {'schemaVersion': 'portfolio04-bindings/1', 'evidence': {
        'fixture': {'path': str(FIXTURE), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'bytes': len(raw)}}, 'bindings': [{
        'id': 'CH:authored', 'country': 'CH', 'sourceId': 'authored-metadata',
        'metadataReleaseId': 'authored-fixture-2026', 'dataTypes': ['prices/baskets'],
        'holds': [], 'requiredFields': ['datasetRelease', 'nativeUnit', 'nativeBasis',
                                      'fieldSelector', 'operationUseClause'], 'fields': fields}]}
    return profile, {'fixture': raw}


class Portfolio04BindingTests(unittest.TestCase):
    def test_valid_deterministic_and_per_datum_origins(self):
        profile, metadata = fixture()
        before = copy.deepcopy(profile)
        result = b.evaluate(profile, metadata, now=NOW)
        self.assertEqual('metadata-ready', result['results'][0]['status'])
        self.assertEqual(result, b.evaluate(profile, metadata, now=NOW))
        self.assertEqual(before, profile)
        row = result['candidateRecords'][0]
        pins = {'fixture.json': profile['evidence']['fixture']['sha256']}
        self.assertEqual([], b.field_origin_errors(row, pins, policy_pins=(b.POLICY,)))
        self.assertEqual([], b.metadata_semantic_errors(row, {'fixture.json': json.loads(metadata['fixture'])}))
        self.assertEqual(0, row['data']['value'])
        self.assertFalse(result['productionAdmission'])
        self.assertFalse(result['results'][0]['sourceOperationAuthorized'])

    def test_missing_evidence_and_unknown_fields_are_distinct(self):
        profile, metadata = fixture()
        missing = b.evaluate(profile, {}, now=NOW)
        self.assertEqual('missing', missing['results'][0]['status'])
        self.assertIn('evidence-missing', missing['results'][0]['errors'])
        self.assertEqual([], missing['candidateRecords'])
        profile['bindings'][0]['fields']['nativeUnit'] = {'unknown': 'dictionary not retained'}
        unknown = b.evaluate(profile, metadata, now=NOW)
        self.assertEqual('missing', unknown['results'][0]['status'])
        self.assertIn('nativeUnit', unknown['results'][0]['missingFields'])
        self.assertIsNone(unknown['candidateRecords'][0]['data']['nativeUnit'])

    def test_hold_wins_even_with_complete_fields(self):
        profile, metadata = fixture()
        profile['bindings'][0]['holds'] = ['explicit-source-no-read']
        result = b.evaluate(profile, metadata, now=NOW)
        self.assertEqual('held', result['results'][0]['status'])
        self.assertEqual(['explicit-source-no-read'], result['results'][0]['holds'])
        self.assertFalse(result['results'][0]['cache']['networkAllowed'])

    def test_stale_acquisition_not_reset_by_fresh_validation_or_replay(self):
        profile, metadata = fixture()
        first = b.evaluate(profile, metadata, now=NOW)
        boundary = b.evaluate(profile, metadata, now='2026-10-31T00:00:00Z',
                              previous_candidate_sha256=first['candidateSha256'])
        self.assertEqual('stale', boundary['results'][0]['status'])
        self.assertEqual('no-op', boundary['replay'])  # candidate bytes only, not readiness
        cache = boundary['results'][0]['cache']
        self.assertEqual(30 * 86400, cache['originalAgeSeconds'])
        self.assertEqual('2026-10-01T00:00:00Z', cache['originalAcquiredAt'])
        self.assertEqual('2026-10-31T00:00:00Z', cache['metadataVerifiedAt'])
        self.assertFalse(cache['networkAllowed'])
        young = b.evaluate(profile, metadata, now='2026-10-30T23:59:59Z')
        self.assertEqual('metadata-ready', young['results'][0]['status'])
        self.assertEqual('under-minimum-reuse', young['results'][0]['cache']['state'])

    def test_pin_drift_duplicate_keys_and_bad_selectors_fail_closed(self):
        profile, metadata = fixture()
        changed = b.evaluate(profile, {'fixture': metadata['fixture'] + b' '}, now=NOW)
        self.assertEqual('malformed', changed['results'][0]['status'])
        self.assertIn('evidence-pin-mismatch', changed['results'][0]['errors'])
        profile, metadata = fixture(b'{"x":1,"x":2}')
        duplicate = b.evaluate(profile, metadata, now=NOW)
        self.assertIn('evidence-json-malformed', duplicate['results'][0]['errors'])
        profile, metadata = fixture()
        profile['bindings'][0]['fields']['nativeUnit']['selector'] = '/missing'
        result = b.evaluate(profile, metadata, now=NOW)
        self.assertEqual(['field-selector-unresolved'], result['results'][0]['errors'])

    def test_isolated_bad_binding_does_not_block_peer_metadata(self):
        profile, metadata = fixture()
        bad = copy.deepcopy(profile['bindings'][0]); bad['id'] = 'AE:bad'
        bad['fields']['value']['selector'] = '/missing'
        profile['bindings'].append(bad)
        result = b.evaluate(profile, metadata, now=NOW)
        self.assertEqual(['malformed', 'metadata-ready'], [r['status'] for r in result['results']])
        self.assertEqual(['CH:authored'], [r['id'] for r in result['candidateRecords']])

    def test_origin_value_and_unknown_policy_tampering(self):
        profile, metadata = fixture()
        row = b.evaluate(profile, metadata, now=NOW)['candidateRecords'][0]
        documents = {'fixture.json': json.loads(metadata['fixture'])}
        row['data']['value'] = False  # bool and numeric zero must not compare equal
        self.assertIn('metadata-origin-value-mismatch', b.metadata_semantic_errors(row, documents))
        profile['bindings'][0]['fields']['nativeUnit'] = {'unknown': 'not held'}
        row = b.evaluate(profile, metadata, now=NOW)['candidateRecords'][0]
        row['provenance']['fieldOrigins']['/data/nativeUnit']['symbol'] = 'invented'
        self.assertIn('metadata-unknown-policy-mismatch', b.metadata_semantic_errors(row, documents))

    def test_future_bad_time_profile_bounds_and_identity(self):
        profile, metadata = fixture()
        future = b.evaluate(profile, metadata, now='2026-09-01T00:00:00Z')
        self.assertIn('acquisition-time-invalid', future['results'][0]['errors'])
        with self.assertRaises(ValueError):
            b.evaluate(profile, metadata, now='2026-10-18T00:00:00')
        with self.assertRaises(ValueError):
            b.evaluate(profile, metadata, now=NOW, previous_candidate_sha256='not-a-hash')
        profile['bindings'].append(copy.deepcopy(profile['bindings'][0]))
        with self.assertRaisesRegex(ValueError, 'binding-identity-invalid'):
            b.evaluate(profile, metadata, now=NOW)
        profile, metadata = fixture(); profile['evidence']['fixture']['bytes'] = b.MAX_EVIDENCE + 1
        with self.assertRaisesRegex(ValueError, 'metadata-pin-invalid'):
            b.evaluate(profile, metadata, now=NOW)

    def test_reader_only_uses_fixed_metadata_paths_never_original_path(self):
        profile, metadata = fixture()
        opened = []
        original_open = os.open
        def tracked(path, *args, **kwargs):
            opened.append(str(path))
            return original_open(path, *args, **kwargs)
        with patch.object(os, 'open', tracked):
            loaded = b.read_metadata(profile)
            result = b.evaluate(profile, loaded, now=NOW)
        self.assertEqual([str(FIXTURE)], opened)
        self.assertEqual('/must-not-open/raw-source.pdf', result['candidateRecords'][0]['data']['originalAssetPath'])

    def test_symlink_missing_and_oversized_metadata_fail_closed(self):
        profile, metadata = fixture()
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / 'link.json'; link.symlink_to(FIXTURE.resolve())
            profile['evidence']['fixture']['path'] = str(link)
            self.assertEqual({}, b.read_metadata(profile))
            profile['evidence']['fixture']['path'] = str(Path(directory) / 'absent.json')
            self.assertEqual({}, b.read_metadata(profile))
        result = b.evaluate(*fixture(), now=NOW)
        profile, metadata = fixture()
        metadata['fixture'] = b' ' * (b.MAX_EVIDENCE + 1)
        oversize = b.evaluate(profile, metadata, now=NOW,
                              previous_candidate_sha256=result['candidateSha256'])
        self.assertNotEqual('no-op', oversize['replay'])
        self.assertEqual('malformed', oversize['results'][0]['status'])

    def test_regular_path_replacement_cannot_block_cli_or_hide_peer(self):
        """Race the actual open boundary in a killed/reaped child, authored only."""
        script = r'''
import json, os, sys
from pathlib import Path
from unittest.mock import patch
from offmenu.refresh import portfolio04_binding as b
profile = json.loads(sys.stdin.read())
target = Path(profile['evidence']['fixture']['path'])
mode = sys.argv[1]
b.load_catalogue = lambda: profile
real_path_open, real_os_open = Path.open, os.open
swapped = False
def swap():
    global swapped
    if swapped:
        return
    swapped = True
    if mode == 'regular-before':
        replacement = target.with_name('replacement.json')
        replacement.write_bytes(b'{}')
        os.replace(replacement, target)
    else:
        target.unlink()
        os.mkfifo(target)
    print('authored-path-swap:' + mode, file=sys.stderr, flush=True)
def path_open(path, *args, **kwargs):
    if path == target:
        swap()
    return real_path_open(path, *args, **kwargs)
def os_open(path, flags, *args, **kwargs):
    if Path(path) == target and mode != 'fifo-after':
        swap()
    fd = real_os_open(path, flags, *args, **kwargs)
    if Path(path) == target and mode == 'fifo-after':
        swap()
    return fd
with patch.object(Path, 'open', path_open), patch.object(os, 'open', os_open):
    raise SystemExit(b.main(['--now', '2026-10-18T00:00:00Z']))
'''
        for mode in ('fifo-before', 'regular-before', 'fifo-after'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                profile, _ = fixture()
                first = Path(directory) / 'racy.json'
                peer = Path(directory) / 'peer.json'
                first.write_bytes(FIXTURE.read_bytes()); peer.write_bytes(FIXTURE.read_bytes())
                profile['evidence']['fixture']['path'] = str(first)
                profile['evidence']['peer'] = {**profile['evidence']['fixture'], 'path': str(peer)}
                sibling = copy.deepcopy(profile['bindings'][0]); sibling['id'] = 'CH:peer'
                for field in sibling['fields'].values():
                    field['evidence'] = 'peer'
                profile['bindings'][0]['id'] = 'AE:racy'
                profile['bindings'].append(sibling)
                # run(timeout=...) kills and reaps a regression before failing.
                process = subprocess.run([sys.executable, '-B', '-c', script, mode],
                    cwd=Path(__file__).resolve().parents[1], input=json.dumps(profile),
                    text=True, capture_output=True, timeout=2)
                self.assertEqual(2, process.returncode, process.stderr)
                self.assertIn('authored-path-swap:' + mode, process.stderr)
                report = json.loads(process.stdout)
                self.assertEqual({'AE:racy': 'missing', 'CH:peer': 'metadata-ready'},
                                 {r['id']: r['status'] for r in report['results']})
                self.assertEqual(['CH:peer'], [r['id'] for r in report['candidateRecords']])

    def test_shared_qualification_with_authored_contract_not_real_admission(self):
        profile, metadata = fixture()
        result = b.evaluate(profile, metadata, now=NOW)
        row = result['candidateRecords'][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'bundle'; bundle.mkdir()
            assets = []
            for name, raw in [('fixture.json', metadata['fixture']),
                              ('rights.json', b'{"fixture":true}'),
                              ('scope.json', b'{"expectedFixtureRecords":1}')]:
                (bundle / name).write_bytes(raw)
                assets.append(q.Asset(name, len(raw), hashlib.sha256(raw).hexdigest()))
            candidate = root / 'candidate.jsonl'; candidate.write_bytes(candidate_bytes([row]))
            schema = {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
                'properties': {'kind': {'const': 'portfolio04-source-input-binding'},
                               'data': {'type': 'object', 'required': ['nativeUnit', 'nativeBasis']}}}
            schemas = {row['kind']: schema}
            pins = {'fixture.json': assets[0].sha256}
            documents = {'fixture.json': json.loads(metadata['fixture'])}
            def semantics(record):
                return b.field_origin_errors(record, pins, policy_pins=(b.POLICY,)) + b.metadata_semantic_errors(record, documents)
            contract = q.SourceContract(source_id=row['provenance']['sourceId'],
                release_id=row['provenance']['releaseId'], scope_id='authored-metadata-only',
                acquired_at=row['data']['originalAcquiredAt'], inputs=tuple(assets),
                expected_records=1, expected_ids_sha256=q.ids_digest([row['id']]),
                schemas=schemas, schemas_sha256=q.fingerprint(schemas),
                semantic_validator=semantics, policy_sha256=b.POLICY,
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                'acquiredAt': contract.acquired_at, 'rightsEvidenceSha256': assets[1].sha256,
                'scopeEvidenceSha256': assets[2].sha256, 'normalizedRecords': 1,
                'inputFiles': [vars(a) for a in assets], 'candidateBytes': candidate.stat().st_size,
                'candidateSha256': result['candidateSha256']}
            receipt = q.accept(contract, bundle, candidate, manifest)
            self.assertTrue(receipt['accepted'], receipt['errors'])
            self.assertFalse(receipt['productionAccepted'])
            self.assertFalse(receipt['countryCoverageComplete'])
            held = q.qualify(replace(contract, holds=('explicit-no-read',)), bundle, candidate, manifest)
            self.assertIn('source-held', held['errors'])
            row['data']['nativeUnit'] = 'invented-unit'
            candidate.write_bytes(candidate_bytes([row]))
            manifest.update(candidateBytes=candidate.stat().st_size,
                            candidateSha256=hashlib.sha256(candidate.read_bytes()).hexdigest())
            bad = q.qualify(contract, bundle, candidate, manifest)
            self.assertIn('metadata-origin-value-mismatch', bad['errors'])

    def test_profile_contains_all_countries_and_six_explicit_requirements(self):
        profile = json.loads(b.PROFILE.read_bytes())
        b._profile(profile)
        self.assertEqual(b.PORTFOLIO, set(profile['countryTypeRequirements']))
        self.assertTrue(all(len(x) == 6 for x in profile['countryTypeRequirements'].values()))
        self.assertEqual(12, len(profile['bindings']))
        self.assertTrue(all(x['holds'] for x in profile['bindings']))


if __name__ == '__main__':
    unittest.main()
