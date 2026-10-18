"""Authored metadata fixtures only: never access an original or candidate body."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio37 as portfolio
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.serialization import encode_records

NOW = '2026-10-18T00:00:00Z'


def observation(profile, *, checked_at=NOW):
    """Synthetic metadata testimony, not a downloaded or parsed observation."""
    return {'sourceId': profile['sourceId'], 'releaseId': profile['releaseId'],
            'inputSha256': profile['original']['sha256'],
            'inputBytes': profile['original']['bytes'],
            'metadataSha256': profile['validationReceipt']['sha256'],
            'acquisitionReceiptSha256': profile['acquisitionReceipt']['sha256'],
            'originalAcquiredAt': profile['originalAcquiredAt'],
            'metadataCheckedAt': checked_at, 'status': 'present'}


class PortfolioBindingsTests(unittest.TestCase):
    def setUp(self):
        self.document, self.digest = portfolio.bindings()
        self.profiles = {p['country']: p for p in self.document['rows']}
        self.sk = self.profiles['SK']

    def test_complete_portfolio_has_no_acceptance_or_silent_category_completion(self):
        self.assertEqual(tuple(self.profiles), ('NP', 'PK', 'PS', 'SK'))
        self.assertEqual(sum(len(p['applicability']) for p in self.profiles.values()), 24)
        for p in self.profiles.values():
            self.assertFalse(p['bodyProcessingAuthorized'])
            self.assertFalse(p['productionAdmission'])
            self.assertFalse(p['countryComplete'])
            self.assertTrue(all(not c['acceptedWholeCategory'] for c in p['applicability']))
            self.assertTrue(p['blockers'])
        self.assertIsNone(self.profiles['NP']['nativeFieldOriginDeclarations']['numericCells'])
        self.assertIsNone(self.profiles['PK']['nativeFieldOriginDeclarations']['price'])
        self.assertIsNone(self.profiles['PS']['nativeFieldOriginDeclarations']['foodObservations'])
        pbs = self.profiles['PK']['additionalInputBindings'][0]
        self.assertEqual(pbs['releasePeriod'], '2026-02-26')
        self.assertIsNone(pbs['currency'])
        self.assertIsNone(pbs['tableSelectors'])
        self.assertFalse(pbs['bodyProcessingAuthorized'])
        self.assertEqual(self.sk['declarations']['units'], ['I25', 'I15', 'RCH_M', 'RCH_A', 'RCH_MV12MAVR'])

    def test_every_metadata_datum_resolves_to_exact_config_selector(self):
        rows = portfolio.metadata_records()
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(field_origin_errors(row, {portfolio.CONFIG.name: self.digest}), [])
            self.assertEqual(set(row['provenance']['fieldOrigins']), set(datum_pointers(row['data'])))
            for pointer, origin in row['provenance']['fieldOrigins'].items():
                value = self.document
                for part in origin['sourceField'].split('/')[1:]:
                    token = part.replace('~1', '/').replace('~0', '~')
                    value = value[int(token)] if isinstance(value, list) else value[token]
                target = row
                for part in pointer.split('/')[1:]:
                    token = part.replace('~1', '/').replace('~0', '~')
                    target = target[int(token)] if isinstance(target, list) else target[token]
                self.assertEqual(value, target)
        self.assertEqual(encode_records(rows), encode_records(portfolio.metadata_records()))

    def test_valid_metadata_has_cache_reuse_but_no_body_verification_or_admission(self):
        result = portfolio.assess_input(self.sk, observation(self.sk), now=NOW)
        self.assertEqual(result['outcome'], 'valid')
        self.assertEqual(result['cacheDecision'], 'reuse-retained-input-no-download')
        self.assertFalse(result['bodyBytesVerified'])
        self.assertFalse(result['bodyProcessingAuthorized'])
        self.assertEqual(result['acceptedRecords'], 0)
        self.assertEqual(result['networkRequests'], 0)

    def test_missing_input_and_unknown_acquisition_have_distinct_diagnostics(self):
        absent = portfolio.assess_input(self.sk, None, now=NOW)
        unknown = portfolio.assess_input(self.profiles['NP'], observation(self.profiles['NP']), now=NOW)
        self.assertEqual(absent['diagnostics'], ['metadata-input-missing'])
        self.assertEqual(unknown['diagnostics'], ['original-acquisition-time-unestablished'])
        self.assertEqual(unknown['outcome'], 'missing')
        self.assertIsNone(unknown['acquisitionAgeDays'])

    def test_held_metadata_does_not_clear_existing_blockers(self):
        item = observation(self.sk)
        item['status'] = 'held'
        result = portfolio.assess_input(self.sk, item, now=NOW)
        self.assertEqual(result['outcome'], 'held')
        self.assertEqual(result['blockers'], self.sk['blockers'])
        self.assertFalse(result['bodyProcessingAuthorized'])

    def test_stale_after_30_days_recent_validation_never_resets_acquisition(self):
        now = '2026-11-14T22:18:53.051837Z'
        result = portfolio.assess_input(self.sk, observation(self.sk, checked_at=now), now=now)
        self.assertEqual(result['outcome'], 'stale')
        self.assertEqual(result['acquisitionAgeDays'], 31)
        self.assertEqual(result['cacheDecision'], 'conditional-refresh-review-no-download')
        self.assertEqual(result['originalAcquiredAt'], self.sk['originalAcquiredAt'])
        self.assertEqual(result['networkRequests'], 0)
        boundary = '2026-11-13T22:18:53.051837Z'
        result = portfolio.assess_input(self.sk, observation(self.sk, checked_at=boundary), now=boundary)
        self.assertEqual(result['outcome'], 'stale')
        self.assertEqual(result['acquisitionAgeDays'], 30)

    def test_malformed_identity_pin_timestamp_and_unknown_fields_fail_closed(self):
        for field, value in [('sourceId', 'other'), ('releaseId', 'newer'),
                             ('inputSha256', '0' * 64), ('inputBytes', True),
                             ('metadataSha256', '0' * 64),
                             ('acquisitionReceiptSha256', '0' * 64),
                             ('originalAcquiredAt', NOW),
                             ('metadataCheckedAt', 'tomorrow'),
                             ('metadataCheckedAt', '2026-10-19T00:00:00Z'),
                             ('status', []), ('unexpected', True)]:
            with self.subTest(field=field, value=value):
                item = observation(self.sk)
                item[field] = value
                self.assertEqual(portfolio.assess_input(self.sk, item, now=NOW)['outcome'], 'malformed')
        self.assertEqual(portfolio.assess_input(self.sk, [], now=NOW)['outcome'], 'malformed')

    def test_multiple_errors_accumulate_and_failed_peer_does_not_hide_valid_peer(self):
        item = observation(self.sk)
        item.update(inputSha256='wrong', metadataCheckedAt='invalid')
        result = portfolio.assess_input(self.sk, item, now=NOW)
        self.assertEqual(result['diagnostics'], ['metadata-binding-mismatch', 'metadata-time-invalid'])
        plan = portfolio.assess_portfolio({'NP': [], 'PK': None, 'SK': observation(self.sk)}, now=NOW)
        self.assertEqual(len(plan['sources']), 4)
        self.assertEqual(plan['sources'][0]['outcome'], 'malformed')
        self.assertEqual(plan['sources'][3]['outcome'], 'valid')
        self.assertFalse(plan['countryComplete'])

    def test_metadata_observer_only_reads_allowlisted_authored_receipts(self):
        # Replace the two trusted document paths with tiny authored fixtures.
        with tempfile.TemporaryDirectory() as directory:
            p = deepcopy(self.sk)
            for key, data in [('validationReceipt', {'actualSourceValidation': {'input': p['original']}}),
                              ('acquisitionReceipt', {'finishedUTC': p['originalAcquiredAt']})]:
                raw = canonical(data)
                target = Path(directory) / (key + '.json')
                target.write_bytes(raw)
                p[key] = {'path': str(target), 'sha256': sha(raw)}
            original_read = Path.read_bytes
            seen = []
            def read(path):
                seen.append(str(path))
                self.assertTrue(str(path).startswith(directory + '/'))
                return original_read(path)
            with patch.object(Path, 'read_bytes', read):
                item = portfolio.observe_metadata(p, checked_at=NOW)
            self.assertEqual(item['inputSha256'], p['original']['sha256'])
            self.assertEqual(set(seen), {p[k]['path'] for k in ('validationReceipt', 'acquisitionReceipt')})
            Path(p['validationReceipt']['path']).write_text('{}')
            with self.assertRaises(RefreshError):
                portfolio.observe_metadata(p, checked_at=NOW)

    def test_exclusive_publication_replay_is_noop_and_changed_frozen_output_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            first = portfolio.publish_metadata(path)
            before = path.stat()
            second = portfolio.publish_metadata(path)
            after = path.stat()
            self.assertEqual((first['sha256'], first['bytes']), (second['sha256'], second['bytes']))
            self.assertEqual(second['decision'], 'reused-noop')
            self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
            path.write_bytes(b'frozen-different-artifact')
            with self.assertRaises(RefreshError):
                portfolio.publish_metadata(path)
            self.assertEqual(path.read_bytes(), b'frozen-different-artifact')

    def test_shared_qualifier_accepts_authored_metadata_fixture_only_and_rejects_tampering(self):
        from offmenu.refresh.acceptance import Asset, SourceContract, accept, fingerprint, ids_digest
        # The config and two new authored evidence files are the entire fixture
        # bundle. None of its original/candidate/receipt path declarations is opened.
        row = portfolio.metadata_records()[3]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            assets = []
            for name, raw in [(portfolio.CONFIG.name, portfolio.CONFIG.read_bytes()),
                              ('rights.txt', b'Authored metadata fixture only; no publisher source rights granted.'),
                              ('scope.txt', b'One authored SK metadata binding; no country or dataset acceptance.')]:
                (bundle / name).write_bytes(raw)
                assets.append(Asset(name, len(raw), sha(raw)))
            schema = {'source-input-binding-metadata': {
                'type': 'object', 'additionalProperties': False,
                'required': ['id', 'kind', 'schemaVersion', 'provenance', 'data'],
                'properties': {'id': {'const': row['id']},
                               'kind': {'const': row['kind']},
                               'schemaVersion': {'const': '1.0'},
                               'provenance': {'const': row['provenance']},
                               'data': {'const': self.sk}}}}
            contract = SourceContract(
                self.sk['sourceId'], self.sk['releaseId'], 'authored-metadata-fixture-only',
                self.document['authoredAt'], tuple(assets), 1, ids_digest([row['id']]),
                schema, fingerprint(schema),
                lambda record: field_origin_errors(record, {portfolio.CONFIG.name: self.digest}),
                self.digest, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                fixture=True)
            candidate = root / 'candidate.jsonl'
            def evaluate(record):
                raw = encode_records([record])
                candidate.write_bytes(raw)
                manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                            'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                            'candidateSha256': sha(raw), 'candidateBytes': len(raw),
                            'inputFiles': [vars(a) for a in assets],
                            'rightsEvidenceSha256': assets[1].sha256,
                            'scopeEvidenceSha256': assets[2].sha256}
                return accept(contract, bundle, candidate, manifest)
            result = evaluate(row)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertEqual(result['status'], 'accepted-fixture-scope')
            self.assertFalse(result['productionAccepted'])
            changed = deepcopy(row)
            changed['data']['original']['sha256'] = '0' * 64
            result = evaluate(changed)
            self.assertFalse(result['accepted'])
            self.assertIn('record-schema-invalid', result['errors'])


if __name__ == '__main__':
    unittest.main()
