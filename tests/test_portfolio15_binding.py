"""Isolated authored metadata; no corpus reads, network or acceptance."""
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.portfolio15 import load_catalog, plan, read_metadata, portfolio_requirements
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify

FIXTURES = Path(__file__).parent / 'fixtures/portfolio15'
NOW = '2026-10-18T00:00:00Z'


def contract(raw=None):
    raw = raw if raw is not None else (FIXTURES / 'valid-metadata.json').read_bytes()
    fields = {}
    for name, pointer, types in [('title', '/title', ['string']),
                                  ('sourceRecordId', '/identifier', ['string']),
                                  ('nativeUnit', '/quantity/unit', ['string', 'null']),
                                  ('quantityBasis', '/quantity/basis', ['string', 'null'])]:
        fields[name] = {'kind': 'source', 'evidence': 'fixture', 'pointer': pointer, 'types': types}
    fields['authoritativeEdition'] = {'kind': 'constant', 'value': None, 'types': ['null']}
    return {'id': 'authored-bd-metadata', 'country': 'BD', 'types': ['prices/baskets'],
            'sourceId': 'authored-fixture-only', 'releaseId': 'synthetic-v1',
            'sourceRecordId': '0007', 'metadataHeld': False, 'sourceHolds': ['body-not-selected'],
            'applicabilityNote': 'Authored metadata test, no country coverage.',
            'countrySelector': {'evidence': 'fixture', 'pointer': '/country'},
            'evidence': {'fixture': {'recordedPath': '/authored-only/metadata.json',
                                     'sha256': sha(raw), 'bytes': len(raw)}},
            'fields': fields,
            'cache': {'originalAcquiredAt': {'evidence': 'fixture', 'pointer': '/originalAcquiredAt'},
                      'lastValidatedAt': {'evidence': 'fixture', 'pointer': '/validatedAt'},
                      'validationKind': 'authored-local-validation',
                      'meaning': 'Authored capture event, not production HTTP evidence.'},
            'sourceAsset': {'path': '/never-follow/source.pdf', 'sha256': 'a' * 64,
                            'bytes': 42, 'role': 'authored-only-opaque-claim'}}, raw


class Portfolio15BindingTests(unittest.TestCase):
    def evaluate(self, document=None, *, now=NOW, operation='metadata-bind', previous=None):
        raw = canonical(document) if document is not None else None
        binding, raw = contract(raw)
        return plan(binding, {'fixture': raw}, now=now, operation=operation, previous_build=previous)

    def test_valid_metadata_has_exact_shared_provenance_and_no_acceptance(self):
        binding, raw = contract()
        result = plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['status'], 'READY_METADATA_ONLY')
        row = result['record']
        self.assertEqual(row['data']['sourceRecordId'], '0007')
        self.assertIsNone(row['data']['nativeUnit'])
        self.assertIsNone(row['data']['quantityBasis'])
        self.assertIsNone(row['data']['authoritativeEdition'])
        self.assertEqual(set(row['provenance']['fieldOrigins']), set(datum_pointers(row['data'])))
        policies = {x['policySha256'] for x in row['provenance']['fieldOrigins'].values()
                    if x['kind'] == 'constant'}
        self.assertEqual(field_origin_errors(row, {'fixture.json': sha(raw)}, policy_pins=policies), [])
        for flag in ['sourceAccepted', 'countryComplete', 'goldAdmitted', 'sourceAssetVerifiedByThisPlan']:
            self.assertFalse(result[flag])
        self.assertEqual(result['sourceBodyReads'], 0)
        self.assertEqual(result['networkRequests'], 0)

    def test_missing_input_is_distinct_from_malformed(self):
        binding, _ = contract()
        result = plan(binding, {}, now=NOW)
        self.assertEqual((result['status'], result['diagnostics']), ('MISSING', ['metadata-input-missing']))

    def test_missing_selector_does_not_create_default(self):
        document = json.loads((FIXTURES / 'valid-metadata.json').read_bytes())
        del document['identifier']
        result = self.evaluate(document)
        self.assertEqual((result['status'], result['diagnostics']), ('MISSING', ['metadata-field-missing']))
        self.assertIsNone(result['record'])

    def test_body_hold_precedes_json_and_filesystem_access(self):
        binding, _ = contract()
        with patch('offmenu.refresh.portfolio15.safe_path', side_effect=AssertionError('no IO')):
            self.assertEqual(read_metadata(binding, operation='parse'), {})
        result = plan(binding, {'fixture': b'not json'}, now=NOW, operation='parse')
        self.assertEqual((result['status'], result['diagnostics']), ('HELD', ['body-operation-not-selected']))
        self.assertIsNone(result['record'])

    def test_explicit_metadata_hold_is_not_escaped_by_cached_bytes(self):
        binding, raw = contract()
        binding['metadataHeld'] = True
        self.assertEqual(plan(binding, {'fixture': raw}, now=NOW)['status'], 'HELD')

    def test_duplicate_json_key_fails_closed(self):
        raw = (FIXTURES / 'malformed-metadata.json').read_bytes()
        binding, raw = contract(raw)
        self.assertEqual(plan(binding, {'fixture': raw}, now=NOW)['status'], 'MALFORMED')

    def test_pin_mismatch_does_not_echo_input_or_path(self):
        binding, raw = contract()
        result = plan(binding, {'fixture': raw + b' private-secret'}, now=NOW)
        self.assertEqual(result['status'], 'MALFORMED')
        self.assertNotIn('private-secret', json.dumps(result))
        self.assertNotIn('/authored-only', json.dumps(result))

    def test_country_mismatch_is_not_equivalence(self):
        document = json.loads((FIXTURES / 'valid-metadata.json').read_bytes())
        document['country'] = 'BE'
        result = self.evaluate(document)
        self.assertEqual(result['diagnostics'], ['metadata-country-mismatch'])

    def test_literal_identifier_cannot_be_coerced_from_number(self):
        document = json.loads((FIXTURES / 'valid-metadata.json').read_bytes())
        document['identifier'] = 7
        self.assertEqual(self.evaluate(document)['diagnostics'], ['metadata-field-type-mismatch'])

    def test_nonfinite_and_overflow_json_are_rejected(self):
        raw = (FIXTURES / 'valid-metadata.json').read_bytes()
        for value in [b'NaN', b'1e999']:
            poisoned = raw.replace(b'"0007"', value)
            binding, _ = contract(poisoned)
            self.assertEqual(plan(binding, {'fixture': poisoned}, now=NOW)['status'], 'MALFORMED')

    def test_unchanged_evidence_has_noop_despite_clock_progress(self):
        first = self.evaluate()
        second = self.evaluate(now='2026-10-19T00:00:00Z', previous=first['buildKey'])
        self.assertEqual(second['replay'], 'NO_OP')
        self.assertEqual(second['record'], first['record'])
        self.assertNotEqual(second['cache']['acquisitionAgeSeconds'], first['cache']['acquisitionAgeSeconds'])

    def test_thirty_day_boundary_stale_even_after_recent_validation(self):
        document = json.loads((FIXTURES / 'valid-metadata.json').read_bytes())
        document['validatedAt'] = '2026-10-30T23:59:00Z'
        result = self.evaluate(document, now='2026-10-31T00:00:00Z')
        self.assertEqual(result['status'], 'STALE')
        self.assertEqual(result['cache']['minimumReuseSeconds'], 30 * 86400)
        self.assertFalse(result['cache']['validationResetsOriginalAcquisition'])
        self.assertFalse(result['cache']['automaticDownloadAllowed'])

    def test_missing_acquisition_is_not_invented_from_validation(self):
        binding, raw = contract()
        binding['cache']['originalAcquiredAt'] = None
        result = plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['diagnostics'], ['original-acquisition-evidence-missing'])
        self.assertIsNone(result['cache'])

    def test_future_validation_or_naive_clock_is_malformed(self):
        document = json.loads((FIXTURES / 'valid-metadata.json').read_bytes())
        document['validatedAt'] = '2026-10-19T00:00:00Z'
        self.assertEqual(self.evaluate(document)['status'], 'MALFORMED')
        self.assertEqual(self.evaluate(now='2026-10-18T00:00:00')['status'], 'MALFORMED')

    def test_reviewed_loader_verifies_metadata_only_and_rejects_links(self):
        binding, raw = contract()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'metadata.json'
            path.write_bytes(raw)
            binding['evidence']['fixture']['recordedPath'] = str(path)
            self.assertEqual(read_metadata(binding), {'fixture': raw})
            # Corpus path remains opaque, regardless of its existence or type.
            self.assertEqual(binding['sourceAsset']['path'], '/never-follow/source.pdf')
            link = Path(temp) / 'linked.json'
            link.symlink_to(path)
            binding['evidence']['fixture']['recordedPath'] = str(link)
            with self.assertRaises(RefreshError):
                read_metadata(binding)

    def test_catalog_portfolio_scope_and_body_holds(self):
        catalog = load_catalog()
        self.assertEqual(len(catalog['bindings']), 6)
        self.assertEqual({b['country'] for b in catalog['bindings']}, {'BD', 'BE', 'BF', 'BG'})
        for binding in catalog['bindings']:
            self.assertTrue(binding['sourceHolds'])
            self.assertEqual(plan(binding, {}, now=NOW, operation='transform')['status'], 'HELD')

    def test_shared_coverage_keeps_all_twenty_four_requirements_unaccepted(self):
        result = portfolio_requirements()
        self.assertEqual(result['requiredCountryDomainCells'], 24)
        self.assertEqual(result['acceptedCountryDomainCells'], 0)
        self.assertFalse(result['countryCoverageComplete'])
        self.assertTrue(all(x['errors'] == ['country-domain-contract-missing'] for x in result['cells']))

    def test_shared_fixture_qualification_consumes_real_binding_output(self):
        binding, raw = contract()
        report = plan(binding, {'fixture': raw}, now=NOW)
        row = report['record']
        self.assertEqual(row['provenance']['fetchedAt'], '2026-10-01T00:00:00Z')
        schema = {'type': 'object', 'additionalProperties': False,
                  'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                  'properties': {
                      'id': {'const': row['id']},
                      'kind': {'const': 'source-input-metadata-binding'},
                      'schemaVersion': {'const': 'owner15-metadata-binding/1'},
                      'data': {'type': 'object', 'additionalProperties': False,
                               'required': list(row['data']),
                               'properties': {'title': {'type': 'string'},
                                              'sourceRecordId': {'const': '0007'},
                                              'nativeUnit': {'type': 'null'},
                                              'quantityBasis': {'type': 'null'},
                                              'authoritativeEdition': {'type': 'null'}}},
                      'provenance': {'type': 'object', 'additionalProperties': False,
                                     'required': ['sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins'],
                                     'properties': {'sourceId': {'const': binding['sourceId']},
                                                    'releaseId': {'const': binding['releaseId']},
                                                    'fetchedAt': {'const': row['provenance']['fetchedAt']},
                                                    'fieldOrigins': {'type': 'object'}}}}}
        schemas = {'source-input-metadata-binding': schema}
        policies = tuple({o['policySha256'] for o in row['provenance']['fieldOrigins'].values()
                          if o['kind'] == 'constant'})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / 'authored-bundle'
            bundle.mkdir()
            files = {'fixture.json': raw,
                     'rights.json': canonical({'scope': 'authored-fixture-only'}),
                     'scope.json': canonical({'records': [row['id']], 'countryAcceptance': False})}
            assets = tuple(Asset(name, len(content), sha(content)) for name, content in files.items())
            for name, content in files.items():
                (bundle / name).write_bytes(content)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(canonical([row]))
            reviewed = SourceContract(
                source_id=binding['sourceId'], release_id=binding['releaseId'],
                scope_id='authored-owner15-binding-fixture',
                acquired_at=row['provenance']['fetchedAt'], inputs=assets,
                expected_records=1, expected_ids_sha256=ids_digest([row['id']]),
                schemas=schemas, schemas_sha256=fingerprint(schemas),
                semantic_validator=lambda r: field_origin_errors(r, {'fixture.json': sha(raw)},
                                                                 policy_pins=policies),
                policy_sha256=fingerprint({'policy': 'authored-fixture-only'}),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')),
                fixture=True, max_records=1, max_input_bytes=16384, max_output_bytes=16384)
            manifest = {'sourceId': reviewed.source_id, 'releaseId': reviewed.release_id,
                        'acquiredAt': reviewed.acquired_at,
                        'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256,
                        'normalizedRecords': 1, 'candidateBytes': candidate.stat().st_size,
                        'candidateSha256': sha(candidate.read_bytes()),
                        'inputFiles': [vars(a) for a in assets]}
            result = qualify(reviewed, bundle, candidate, manifest, scratch_root=root)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            self.assertNotIn('accepted', result)
            # Qualification is never upgraded to actual-source or country acceptance.
            self.assertFalse(report['sourceAccepted'])
            held = qualify(replace(reviewed, holds=('authored-hold',)), bundle, candidate,
                           manifest, scratch_root=root)
            self.assertIn('source-held', held['errors'])


if __name__ == '__main__':
    unittest.main()
