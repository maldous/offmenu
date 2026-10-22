"""Synthetic metadata only: no source network, native files, claims, or datasets."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prep = module('fixed_collection_fixture', 'prepare-fixed-collection.py')
dispatch = module('fixed_collection_dispatch', 'dispatch-foo-job.py')


def summary():
    return {'schemaVersion': 'offmenu-adopted-country-lookup-summary/1',
            'commit': prep.ADOPTED_COMMIT, 'registrySHA256': prep.ADOPTED_REGISTRY_SHA256,
            'adoptedStatus': 'REVIEWED_AND_ADOPTED_METADATA_ONLY',
            'sourceDescriptorLookup': {'file:known': {
                'recordedExistenceState': 'held-locally-with-evidence'}}}


def snapshot(records):
    return {'schemaVersion': 'offmenu-owner-custody-snapshot/2', 'observedAt': '2026-10-18T13:00:00Z',
            'snapshotIsLiveOwnershipClearance': False, 'sourceBodiesRead': False,
            'sourceBodiesUploaded': False, 'sourceClaimsChanged': False,
            'reservationsReleased': False, 'networkAcquisitionEnabled': False,
            'metadata': [{'targetId': 'pending-00-primary', 'access': 'observed',
                'pinStatus': 'match', 'metadataSHA256': 'a' * 64, 'heldBodyRead': False, 'owner': 4,
                'reconciliation': {'records': records, 'recordsObserved': len(records),
                    'recordsTruncated': False, 'metadataReferences': [], 'unavailableFields': []}}],
            'discoveredMetadata': []}


class PreparationTests(unittest.TestCase):
    def project(self, rows):
        return prep.prepare(summary(), snapshot(rows))

    def test_preserves_positive_held_evidence_without_promoting_rights(self):
        report = self.project([{'assetId': 'file:known'}])
        row = report['sources'][0]
        self.assertEqual(row['disposition'], 'retained-reported')
        self.assertTrue(row['retainedEvidenceObserved'])
        self.assertFalse(row['acquisitionEnabled'])
        self.assertIn('current-ownership-not-cleared', row['blockers'])

    def test_unmatched_never_means_missing(self):
        row = self.project([{'assetId': 'file:unmatched'}])['sources'][0]
        self.assertEqual(row['disposition'], 'unresolved')
        self.assertIn('adopted-id-unmatched-not-absence', row['blockers'])

    def test_all_results_capture_mixed_holds_partials_and_owners(self):
        rows = [{'assetId': 'a', 'holdsPresent': True},
                {'assetId': 'b', 'partialBytes': 12},
                {'assetId': 'c', 'status': 'complete', 'claimStatus': 'active'},
                {'assetId': 'd', 'reservedBytes': 16},
                {'assetId': 'e', 'heldExistence': True}]
        result = self.project(rows)
        self.assertEqual(result['observations'], 5)
        self.assertEqual(result['sourceDispositions'], 5)
        self.assertEqual(result['counts'], {'held': 1, 'partial': 1, 'owned-observation': 1,
                                          'retained-reported': 1, 'unresolved': 1})
        self.assertIn('reservation-reconciliation-required', result['sources'][3]['blockers'])
        self.assertTrue(all(not r['acquisitionEnabled'] for r in result['sources']))

    def test_shared_exact_asset_retains_multiple_evidence_rows_once(self):
        rows = [{'assetId': 'same', 'country': 'AA'}, {'assetId': 'same', 'country': 'BB'}]
        report = self.project(rows)
        self.assertEqual(report['sourceDispositions'], 1)
        self.assertEqual(len(report['sources'][0]['observations']), 2)

    def test_shared_asset_conflicting_hashes_are_explicit(self):
        rows = [{'assetId': 'same', 'sha256': h * 64, 'bytes': 1} for h in ('a', 'b')]
        self.assertIn('asset-identity-conflict-requires-reconciliation',
                      self.project(rows)['sources'][0]['blockers'])

    def test_unbound_url_does_not_deduplicate_representations(self):
        rows = [{'sourceUrl': 'https://example.test/asset', 'country': c} for c in ('AA', 'BB')]
        self.assertEqual(self.project(rows)['sourceDispositions'], 2)

    def test_identical_complete_source_representation_deduplicates(self):
        row = {'sourceId': 'shared', 'release': '2026-10', 'bytes': 1, 'sha256': 'a' * 64}
        self.assertEqual(self.project([row, row])['sourceDispositions'], 1)

    def test_hold_and_retained_evidence_both_survive(self):
        row = self.project([{'assetId': 'file:known', 'holdCodes': ['source-held']}])['sources'][0]
        self.assertEqual(row['disposition'], 'held')
        self.assertTrue(row['retainedEvidenceObserved'])

    def test_explicit_existence_hold_is_not_possession(self):
        for state in ('held', 'blocked', 'quarantined'):
            row = self.project([{'assetId': 'file:known', 'existenceState': state}])['sources'][0]
            self.assertEqual(row['disposition'], 'held')
            self.assertTrue(row['retainedEvidenceObserved'])
        row = self.project([{'assetId': 'new', 'existenceState': 'held-locally-with-evidence'}])['sources'][0]
        self.assertEqual(row['disposition'], 'retained-reported')

    def test_unbound_hash_and_reservation_fragments_are_not_sources(self):
        result = self.project([{'sha256': 'a' * 64}, {'reservedBytes': 50}, {'sourceId': 'source'}])
        self.assertEqual(result['sourceDispositions'], 1)
        self.assertEqual(result['unboundObservationCount'], 2)
        self.assertEqual(result['sourceBoundObservations'], 1)
        self.assertEqual(result['reservationObservationCount'], 1)
        self.assertEqual(result['unboundReservationObservationCount'], 1)
        self.assertFalse(result['capacityEvidence']['reservationTotalsAuthoritative'])
        self.assertFalse(result['capacityEvidence']['unknownCommitmentsAssumedZero'])

    def test_exact_url_hash_size_join_preserves_possession_and_source_holds(self):
        adopted = summary()
        adopted['recipeIngredientAndArchiveDetails'] = [{'assetId': 'file:detail',
            'sourceUrl': 'https://example.test/source', 'recordedSHA256': 'a' * 64,
            'recordedBytes': 123, 'heldExistence': True, 'release': 'r1',
            'holds': ['source-use-review'], 'unresolved': ['budget']}]
        result = prep.prepare(adopted, snapshot([{'sourceUrl': 'https://example.test/source',
                                                'sha256': 'a' * 64, 'bytes': 123}]))
        row = result['sources'][0]
        self.assertTrue(row['adoptedIdMatch'])
        self.assertTrue(row['retainedEvidenceObserved'])
        self.assertEqual(row['disposition'], 'held')
        self.assertEqual(row['adoptedConstraints'][0]['holds'], ['source-use-review'])
        self.assertEqual(row['adoptedMatchEvidence'][0]['basis'], 'same-row-exact-url-sha256-bytes')
        # Canonical datatype is deliberately absent: it cannot erase possession.

    def test_adjacent_fragments_never_join_and_release_labels_remain_explicit(self):
        adopted = summary()
        adopted['recipeIngredientAndArchiveDetails'] = [{'assetId': 'file:detail',
            'sourceUrl': 'https://example.test/source', 'recordedSHA256': 'a' * 64,
            'recordedBytes': 123, 'heldExistence': True, 'release': 'r1'}]
        result = prep.prepare(adopted, snapshot([{'sourceUrl': 'https://example.test/source'},
                                                {'sha256': 'a' * 64, 'bytes': 123}]))
        self.assertFalse(result['sources'][0]['adoptedIdMatch'])
        self.assertFalse(result['sources'][0]['retainedEvidenceObserved'])
        result = prep.prepare(adopted, snapshot([{'sourceUrl': 'https://example.test/source',
            'sha256': 'a' * 64, 'bytes': 123, 'release': 'r2'}]))
        row = result['sources'][0]
        self.assertTrue(row['retainedEvidenceObserved'])
        self.assertTrue(row['adoptedMatchEvidence'][0]['releaseLabelDiffers'])
        self.assertEqual(row['adoptedMatchEvidence'][0]['observedRelease'], 'r2')
        self.assertFalse(row['acquisitionEnabled'])

    def test_compound_stop_and_partial_are_conserved(self):
        row = self.project([{'sourceId': 'ca-cookbook', 'partialBytes': 33538266,
            'status': 'TRANSPORT_FORMAT_CAP_OR_CAPACITY_STOP_NO_RETRY'}])['sources'][0]
        self.assertEqual(row['disposition'], 'held')
        self.assertIn('partial-transfer-reconciliation-required', row['blockers'])
        self.assertEqual(row['observations'][0]['record']['partialBytes'], 33538266)

    def test_claim_owner_is_adverse_observation_without_current_clearance(self):
        value = snapshot([])
        claimed = snapshot([{'sourceUrl': 'https://example.test/source', 'owner': 4}])['metadata'][0]
        claimed['category'] = 'claims'
        value['discoveredMetadata'] = [claimed]
        row = prep.prepare(summary(), value)['sources'][0]
        self.assertEqual(row['disposition'], 'owned-observation')
        self.assertIn('current-ownership-not-cleared', row['blockers'])
        self.assertFalse(row['acquisitionEnabled'])

    def test_compound_complete_reports_physical_evidence_without_semantic_type(self):
        row = self.project([{'sourceId': 'original',
            'status': 'ACQUIRED_COMPLETE_SOURCE_PRIVATE_REFERENCE'}])['sources'][0]
        self.assertEqual(row['disposition'], 'retained-reported')
        self.assertTrue(row['retainedEvidenceObserved'])
        failed = self.project([{'sourceId': 'original',
            'status': 'HELD_OR_FAILED_NO_RETRY'}])['sources'][0]
        self.assertEqual(failed['disposition'], 'held')
        self.assertFalse(failed['retainedEvidenceObserved'])

    def test_withheld_packet_and_nonexhaustive_catalogue_are_explicit(self):
        value = snapshot([])
        value['metadata'][0].update(pinStatus='withheld-source-hold', heldBodyRead=True, owner=31)
        value['discovery'] = {'claimsCatalogIdentified': True, 'reservationsCatalogIdentified': False,
                              'scopeExhaustive': False, 'unidentifiedIsEmpty': False}
        result = prep.prepare(summary(), value)
        self.assertEqual(result['withheldPacketCount'], 1)
        self.assertTrue(result['packets'][0]['bodyWithheldBySourceHold'])
        self.assertFalse(result['snapshotDiagnostics']['reservationsCatalogIdentified'])
        self.assertFalse(result['snapshotDiagnostics']['unidentifiedIsEmpty'])
        self.assertFalse(result['capacityEvidence']['admissionBudgetEstablished'])

    def test_inaccessible_or_empty_packet_is_retained(self):
        value = snapshot([])
        value['metadata'][0].update(access='permission-denied', reconciliation=None)
        result = prep.prepare(summary(), value)
        self.assertEqual(result['packets'][0]['access'], 'permission-denied')
        self.assertEqual(result['sourceDispositions'], 0)

    def test_truncated_projection_preserves_explicit_blocker(self):
        value = snapshot([{'assetId': 'known'}])
        value['metadata'][0]['reconciliation']['recordsTruncated'] = True
        result = prep.prepare(summary(), value)
        self.assertIn('metadata-projection-truncated', result['sources'][0]['blockers'])

    def test_v1_cannot_qualify_import(self):
        value = snapshot([])
        value['schemaVersion'] = 'offmenu-owner-custody-snapshot/1'
        with self.assertRaisesRegex(prep.RefreshError, 'custody-import-invalid'):
            prep.prepare(summary(), value)

    def test_no_live_clearance_promoted(self):
        value = snapshot([])
        value['snapshotIsLiveOwnershipClearance'] = True
        with self.assertRaisesRegex(prep.RefreshError, 'custody-import-invalid'):
            prep.prepare(summary(), value)

    def test_no_configured_snapshot_fails_before_io(self):
        with patch.object(prep, 'SNAPSHOT_PIN', None), patch.object(prep.os, 'open') as opened:
            with self.assertRaisesRegex(prep.RefreshError, 'corrected-custody-snapshot-not-pinned'):
                prep.imported_snapshot(ROOT)
            opened.assert_not_called()

    def test_strict_pin_no_symlink_or_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ok.json').write_bytes(b'{}')
            good = hashlib.sha256(b'{}').hexdigest()
            self.assertEqual(prep.pinned_bytes(root, ('ok.json', good)), b'{}')
            with self.assertRaisesRegex(prep.RefreshError, 'fixed-input-pin-mismatch'):
                prep.pinned_bytes(root, ('ok.json', 'f' * 64))
            (root / 'link.json').symlink_to(root / 'ok.json')
            with self.assertRaises((prep.RefreshError, OSError)):
                prep.pinned_bytes(root, ('link.json', good))

    def test_validator_executes_only_exact_verified_bytes(self):
        validator = b'def validate_imported_snapshot(value):\n return value\n'
        calls = []
        def pinned(root, pin):
            calls.append(pin)
            return validator if pin == ('validator.py', 'a' * 64) else b'{}'
        with patch.object(prep, 'SNAPSHOT_PIN', ('snapshot.json', 'b' * 64)), \
             patch.object(prep, 'EXPORTER_PIN', ('validator.py', 'a' * 64)), \
             patch.object(prep, 'pinned_bytes', side_effect=pinned):
            self.assertEqual(prep.imported_snapshot(Path('/nonexistent')), {})
        self.assertEqual(calls.count(('validator.py', 'a' * 64)), 1)

    def test_pin_path_escape_refused(self):
        for path in ('/tmp/elsewhere', '../elsewhere'):
            with self.assertRaisesRegex(prep.RefreshError, 'fixed-input-invalid'):
                prep.pinned_bytes(ROOT, (path, 'f' * 64))

    def test_immutable_output_reuse_and_conflict(self):
        report = self.project([{'assetId': 'known'}])
        with tempfile.TemporaryDirectory() as directory, patch.object(prep, 'OUTPUT', Path(directory)):
            prep.save_detail(report)
            prep.save_detail(report)
            paths = list(Path(directory).iterdir())
            self.assertEqual(len(paths), 1)
            paths[0].write_text('corrupt')
            with self.assertRaisesRegex(prep.RefreshError, 'output-collision'):
                prep.save_detail(report)

    def test_main_refuses_arguments_and_never_networks(self):
        with patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            for args, code in [(['--path', '/etc/passwd'], 'unexpected-arguments'),
                               ([], 'corrected-custody-snapshot-not-pinned')]:
                out = io.StringIO()
                with patch('sys.stdout', out), patch.object(prep, 'SNAPSHOT_PIN', None):
                    self.assertEqual(prep.main(args), 2)
                self.assertEqual(json.loads(out.getvalue())['errorCode'], code)

    def test_summary_is_closed_and_every_zero_and_false_is_typed(self):
        with patch.object(prep, 'SNAPSHOT_PIN', ('fixture.json', 'a' * 64)):
            report = prep.summary_report(self.project([{'assetId': 'known'}]))
        for key, value in [('networkRequests', False), ('sourceContentsUploaded', True),
                           ('counts', {'unknown': 1}), ('minimumCacheSeconds', 29 * 86400)]:
            corrupted = dict(report, **{key: value})
            with self.assertRaises(ValueError):
                prep.sanitize_report(corrupted)
        with self.assertRaises(ValueError):
            prep.sanitize_report(dict(report, arbitrary='private-text'))
        self.assertGreaterEqual(report['minimumCacheSeconds'], 30 * 86400)

    def test_dispatch_request_remains_exact_three_fields(self):
        request = {'schemaVersion': 1, 'jobId': 'fixture-collection', 'profile': 'collection-prepare'}
        self.assertEqual(dispatch.parse_request(json.dumps(request).encode()), request)
        for key in ('path', 'command', 'selection', 'sourceUrl'):
            with self.assertRaises(dispatch.JobError):
                dispatch.parse_request(json.dumps(dict(request, **{key: 'untrusted'})).encode())
        steps = dispatch.profile_steps('collection-prepare', ROOT, 'a' * 40)
        self.assertEqual([s[0] for s in steps], ['readiness', 'collection-preparation-tests', 'collection-prepare'])
        self.assertEqual(steps[-1][2][-1], 'scripts/prepare-fixed-collection.py')

    def test_dispatch_sanitizes_summary_and_marks_explicit_block(self):
        report = prep.summary_report(error='corrected-custody-snapshot-not-pinned')
        evidence = dispatch.safe_evidence(json.dumps(report).encode())
        self.assertEqual(evidence['collectionPreparation'], report)
        result = {'status': 'failed', 'exitCode': 2, 'durationSeconds': 0, 'evidence': evidence}
        with patch.object(dispatch, 'run_child', return_value=result):
            self.assertEqual(dispatch.run_step('collection-prepare', [], ROOT)['status'], 'blocked')

    def test_does_not_invoke_existing_collector_or_any_transport(self):
        source = (ROOT / 'scripts' / 'prepare-fixed-collection.py').read_text()
        tree = ast.parse(source)
        calls = {node.func.id for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {'collect_registry', 'CachedAcquirer', 'HTTPSFileTransport', 'eval'})


if __name__ == '__main__':
    unittest.main()
