"""Authored metadata/projection examples only; no retained source-body access."""
import copy
from dataclasses import replace
from pathlib import Path
import errno
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh import acceptance as q
from offmenu.refresh import owner19_bindings as reader
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.owner19_bindings import (
    MetadataReadFailure, catalogue, inspect_binding, inspect_portfolio, main, pointer, read_metadata,
)
from offmenu.refresh.reference_adapters import (
    ReferenceFormatError, candidate_bytes, normalize_reference, reference_semantics,
)

NOW = '2026-10-18T00:00:00Z'


class Owner19BindingsTests(unittest.TestCase):
    def fixture(self, *, acquired='2026-10-13T00:00:00Z', holds=None):
        raw = canonical({'sourceId': 'authored-example', 'releaseId': 'fixture-v1',
                         'originalAcquiredAt': acquired, 'recordCount': 1,
                         'nativeUnit': None, 'quantityBasis': None})
        binding = {'id': 'authored-only', 'country': 'AF', 'sourceId': 'authored-example',
                   'releaseId': 'fixture-v1', 'types': ['authored-reference'],
                   'metadata': [{'key': 'manifest', 'path': '/opaque-not-read.json',
                                 'sha256': sha(raw), 'assertions': [
                                     {'selector': '/sourceId', 'equals': 'authored-example'},
                                     {'selector': '/nativeUnit', 'equals': None}]}],
                   'acquisitionClock': {'artifact': 'manifest', 'selector': '/originalAcquiredAt'},
                   'nativeBasis': {'unit': None, 'quantityBasis': None},
                   'fieldDeclarations': [], 'recordInventory': {'authoredRecords': 1},
                   'inputFormat': 'authored-metadata-only', 'holds': holds or []}
        return binding, {'manifest': raw}

    def inspect(self, binding, buffers, **kwargs):
        return inspect_binding(binding, buffers, now=kwargs.pop('now', NOW), **kwargs)

    def test_valid_metadata_is_not_source_or_staging_admission(self):
        b, buffers = self.fixture()
        result = self.inspect(b, buffers)
        self.assertEqual(result['status'], 'valid-metadata-only')
        self.assertEqual(result['metadataIntegrity'], 'valid')
        self.assertEqual(result['clock']['acquisitionAgeDays'], 5)
        self.assertFalse(result['clock']['cacheReuseAuthorized'])
        self.assertEqual(result['sourceAdmission'], 'not-enabled')
        self.assertEqual(result['recordsStaged'], 0)
        self.assertFalse(result['countryComplete'])

    def test_missing_held_malformed_and_stale_outcomes(self):
        b, buffers = self.fixture()
        self.assertEqual(self.inspect(b, {})['status'], 'missing')
        held = copy.deepcopy(b)
        held['holds'] = [{'code': 'source-use-unreviewed', 'owner': 'reviewer'}]
        self.assertEqual(self.inspect(held, buffers)['status'], 'held')
        for raw in (b'{', b'[]', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e400}'):
            with self.subTest(raw=raw):
                self.assertEqual(self.inspect(b, {'manifest': raw})['status'], 'malformed')
        self.assertEqual(self.inspect(b, {'manifest': b'{}'})['status'], 'stale')
        self.assertEqual(self.inspect(b, {'manifest': b'{}'})['diagnostics'][0]['code'],
                         'stale-input-pin')

    def test_isolated_diagnostics_do_not_suppress_later_bindings_or_leak_input(self):
        b, buffers = self.fixture()
        bad = copy.deepcopy(b)
        bad['id'] = 'bad'
        malformed = b'{"private-header":"never-emit-this",'
        out = inspect_portfolio([bad, b], {'bad': {'manifest': malformed}, b['id']: buffers}, now=NOW)
        self.assertEqual([r['status'] for r in out['results']], ['malformed', 'valid-metadata-only'])
        self.assertNotIn('never-emit-this', str(out))
        broken = copy.deepcopy(b)
        del broken['sourceId']
        out = inspect_portfolio([broken, b], {b['id']: buffers}, now=NOW)
        self.assertEqual(out['results'][0]['diagnostics'][0]['code'], 'invalid-binding-metadata')
        self.assertEqual(out['results'][1]['status'], 'valid-metadata-only')

    def test_clock_does_not_rejuvenate_and_unchanged_metadata_replay_is_noop(self):
        b, buffers = self.fixture()
        first = self.inspect(b, buffers)
        later = self.inspect(b, buffers, now='2026-11-12T00:00:00Z', previous_key=first['buildKey'])
        self.assertEqual(later['clock']['acquisitionAgeDays'], 30)
        self.assertEqual(later['clock']['acquisitionClockStatus'], 'revalidation-review-required')
        self.assertEqual(later['clock']['originalAcquiredAt'], first['clock']['originalAcquiredAt'])
        self.assertNotEqual(later['clock']['metadataValidatedAt'], first['clock']['metadataValidatedAt'])
        self.assertEqual(later['buildKey'], first['buildKey'])
        self.assertEqual(later['replay'], 'no-op-unchanged-metadata')
        self.assertFalse(later['clock']['refreshAuthorized'])
        stale = self.inspect(b, {'manifest': b'{}'}, previous_key=first['buildKey'])
        self.assertNotEqual(stale['replay'], 'no-op-unchanged-metadata')

    def test_unknown_future_and_non_utc_clocks(self):
        b, buffers = self.fixture()
        b['acquisitionClock'] = None
        self.assertIsNone(self.inspect(b, buffers)['clock']['acquisitionAgeDays'])
        b, buffers = self.fixture(acquired='2026-10-19T00:00:00Z')
        self.assertEqual(self.inspect(b, buffers)['diagnostics'][0]['code'],
                         'invalid-original-acquisition-clock')
        with self.assertRaises(RefreshError):
            self.inspect(b, buffers, now='2026-10-18T11:00:00+11:00')

    def test_code_pin_and_declared_input_changes_change_build_identity(self):
        b, buffers = self.fixture()
        original = self.inspect(b, buffers)['buildKey']
        with patch('offmenu.refresh.owner19_bindings.implementation_pins', return_value={'test': 'b'*64}):
            self.assertNotEqual(self.inspect(b, buffers)['buildKey'], original)
        b['metadata'][0]['sha256'] = 'a'*64
        self.assertNotEqual(self.inspect(b, buffers)['buildKey'], original)

    def test_selector_assertions_require_exact_types_and_literal_unknowns(self):
        b, buffers = self.fixture()
        b['metadata'][0]['assertions'][0]['equals'] = 1
        self.assertEqual(self.inspect(b, buffers)['status'], 'malformed')
        self.assertIsNone(pointer({'a/b': [None]}, '/a~1b/0'))
        for selector in ['/a~2', '/a/01', '/a/-1']:
            with self.subTest(selector=selector), self.assertRaises(RefreshError):
                pointer({'a': [0, 1]}, selector)

    def test_catalogue_never_enables_any_country_or_source_operation(self):
        cat = catalogue()
        self.assertEqual({b['country'] for b in cat['bindings']}, {'AF', 'AM', 'BT', 'CN'})
        self.assertEqual(len(cat['bindings']), 6)
        for b in cat['bindings']:
            self.assertFalse(b['stagingEnabled'])
            self.assertTrue(b['holds'])
            self.assertIsNone(b['acquisitionClock'])
            self.assertTrue(all(a['sha256'] for a in b['metadata']))
        af = cat['bindings'][0]
        result = self.inspect(af, {})
        self.assertEqual(result['adapter']['status'], 'source-format-mismatch')
        self.assertEqual(result['adapter']['expectedSourceFormat'], 'overture-place-json-projection')

    def test_cli_defaults_to_no_retained_file_reads(self):
        with patch('offmenu.refresh.owner19_bindings.read_metadata') as read, patch('builtins.print') as output:
            self.assertEqual(main(['--now', NOW]), 0)
            read.assert_not_called()
            self.assertIn('missing', output.call_args.args[0])

    def test_reader_does_not_follow_metadata_to_raw_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            raw = canonical({'bodyPath': '/opaque-not-read.raw'})
            path.write_bytes(raw)
            b, _ = self.fixture()
            b['metadata'][0]['path'] = str(path)
            self.assertEqual(read_metadata(b), {'manifest': raw})

    def test_filesystem_denial_is_not_reported_as_missing_input(self):
        b, _ = self.fixture()
        with patch('offmenu.refresh.owner19_bindings.safe_path', side_effect=PermissionError):
            result = self.inspect(b, read_metadata(b))
        self.assertEqual(result['status'], 'blocked-access')
        self.assertEqual(result['diagnostics'][0]['code'], 'metadata-read-denied')
        self.assertEqual(self.inspect(b, {'manifest': MetadataReadFailure('metadata-path-rejected')})
                         ['status'], 'blocked-filesystem')

    def test_shared_projection_fixture_does_not_accept_legacy_normalized_shape(self):
        # Entirely authored source projection, not an AF country record.
        projection = [{'id': 'authored-place-1', 'names': {'primary': 'Authored Example'},
                       'taxonomy': {'primary': 'restaurant', 'hierarchy': ['food_and_drink']},
                       'sources': [{'property': '', 'dataset': 'authored', 'record_id': 'one',
                                    'provider': 'Overture', 'license': 'CDLA-Permissive-2.0'}]}]
        raw = canonical(projection)
        rows = normalize_reference('overture-food-places', '2026-09-23.1', raw, acquired_at=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(reference_semantics(rows[0]), [])
        self.assertEqual(rows[0]['countries'], [])
        self.assertEqual(field_origin_errors(rows[0], {'authored.json': sha(raw)}),
                         ['field-origins-required'])
        # A schema validator must not invent per-datum origins. The old AF
        # singleton normalized JSONL is neither this projection nor this schema.
        with self.assertRaises(ReferenceFormatError):
            normalize_reference('overture-food-places', '2026-09-23.1',
                                candidate_bytes(rows), acquired_at=NOW)
        # Coverage utility includes null/zero, but does not prove source semantics.
        data = {'nativeUnit': None, 'quantity': 0}
        self.assertEqual(set(datum_pointers(data)), {'/data/nativeUnit', '/data/quantity'})

    def test_authored_staging_contract_requires_every_origin_and_operation_scope(self):
        """Use the real generic qualifier, with a wholly authored private fixture.

        The semantic callback checks literal native selectors as well as generic
        origin coverage, so a made-up coordinate cannot qualify a value.
        """
        source = {'name': 'Authored crop', 'quantity': 0, 'nativeUnit': None}
        raw = canonical(source)
        source_pin = sha(raw)
        row = {'id': 'authored:one', 'kind': 'authored-owner19-reference', 'schemaVersion': '1.0',
               'provenance': {'sourceId': 'owner19-authored-only', 'releaseId': 'fixture-v1',
                              'fetchedAt': NOW}, 'data': source.copy()}
        origins = {}
        for key in source:
            origins['/data/' + key] = {'kind': 'source', 'sourceId': 'owner19-authored-only',
                'releaseId': 'fixture-v1', 'inputPath': 'authored.json', 'inputSha256': source_pin,
                'sourceRecordId': 'one', 'sourceField': '/' + key}
        row['provenance']['fieldOrigins'] = copy.deepcopy(origins)

        def semantics(candidate):
            errors = field_origin_errors(candidate, {'authored.json': source_pin})
            for key, value in source.items():
                origin = candidate['provenance']['fieldOrigins'].get('/data/' + key, {})
                if origin.get('sourceField') != '/' + key or candidate['data'].get(key) != value:
                    errors.append('authored-native-selector-mismatch')
            return errors

        schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'provenance', 'data'],
                  'properties': {'data': {'type': 'object', 'additionalProperties': False,
                    'required': ['name', 'quantity', 'nativeUnit'], 'properties': {
                        'name': {'const': source['name']}, 'quantity': {'const': 0},
                        'nativeUnit': {'type': 'null'}}}}}
        schemas = {'authored-owner19-reference': schema}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            assets = []
            for name, content in [('authored.json', raw),
                    ('rights.json', canonical({'scope': 'authored-only', 'operations': ['retain', 'parse', 'transform']})),
                    ('scope.json', canonical({'ids': ['authored:one'], 'count': 1}))]:
                (bundle / name).write_bytes(content)
                assets.append(q.Asset(name, len(content), sha(content)))
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(canonical([row]))
            contract = q.SourceContract(source_id='owner19-authored-only', release_id='fixture-v1',
                scope_id='authored-owner19-selector-fixture-only', acquired_at=NOW, inputs=tuple(assets),
                expected_records=1, expected_ids_sha256=q.ids_digest([row['id']]),
                schemas=schemas, schemas_sha256=q.fingerprint(schemas), semantic_validator=semantics,
                policy_sha256=sha(b'authored-owner19-selector-policy-v1'),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)

            def manifest():
                body = candidate.read_bytes()
                return {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': NOW, 'normalizedRecords': 1, 'candidateSha256': sha(body),
                        'candidateBytes': len(body), 'inputFiles': [vars(a) for a in assets],
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256}

            result = q.qualify(contract, bundle, candidate, manifest())
            self.assertTrue(result['qualified'], result['errors'])
            held = q.qualify(replace(contract, permitted_operations=frozenset(('retain',))),
                             bundle, candidate, manifest())
            self.assertIn('operation-rights-missing', held['errors'])
            del row['provenance']['fieldOrigins']['/data/nativeUnit']
            candidate.write_bytes(canonical([row]))
            result = q.qualify(contract, bundle, candidate, manifest())
            self.assertIn('field-origin-missing', result['errors'])
            row['provenance']['fieldOrigins'] = copy.deepcopy(origins)
            row['provenance']['fieldOrigins']['/data/name']['sourceField'] = '/quantity'
            candidate.write_bytes(canonical([row]))
            result = q.qualify(contract, bundle, candidate, manifest())
            self.assertIn('authored-native-selector-mismatch', result['errors'])


class MetadataReaderCorrectionTests(unittest.TestCase):
    """W19-R17-1: only authored files; never execute a predecessor FIFO open."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / 'metadata.json'
        self.binding, buffers = Owner19BindingsTests().fixture()
        self.raw = buffers['manifest']
        self.path.write_bytes(self.raw)
        self.binding['metadata'][0]['path'] = str(self.path)

    def assert_closed(self, descriptors):
        for descriptor in set(descriptors):
            with self.assertRaises(OSError) as caught:
                os.fstat(descriptor)
            self.assertEqual(caught.exception.errno, errno.EBADF)

    def test_regular_descriptor_read_closes_all_handles_and_preserves_bytes(self):
        actual_open = os.open
        descriptors = []
        def track(*args, **kwargs):
            descriptor = actual_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(reader.os, 'open', side_effect=track):
            buffers = read_metadata(self.binding)
        self.assertEqual(buffers['manifest'], self.raw)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assert_closed(descriptors)
        self.assertEqual(inspect_binding(self.binding, buffers, now=NOW)['status'], 'valid-metadata-only')

    def test_replacement_symlink_is_not_read_and_later_peer_survives(self):
        unselected = self.root / 'unselected.json'
        unselected.write_bytes(b'{"unselected":"authored-only"}')
        preserved = self.root / 'preserved.json'
        actual_open = os.open
        descriptors = []
        def swap(name, flags, *args, **kwargs):
            if name == self.path.name:
                self.assertTrue(flags & os.O_NOFOLLOW)
                self.assertTrue(flags & os.O_NONBLOCK)
                self.path.rename(preserved)
                self.path.symlink_to(unselected)
            descriptor = actual_open(name, flags, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(reader.os, 'open', side_effect=swap), patch.object(reader.os, 'read') as read:
            buffers = read_metadata(self.binding)
            read.assert_not_called()
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-path-rejected'))
        self.assertEqual(preserved.read_bytes(), self.raw)
        self.assertEqual(unselected.read_bytes(), b'{"unselected":"authored-only"}')
        self.assert_closed(descriptors)
        peer, healthy = Owner19BindingsTests().fixture()
        peer['id'] = 'later-peer'
        result = inspect_portfolio([self.binding, peer],
                                  {self.binding['id']: buffers, peer['id']: healthy}, now=NOW)
        self.assertEqual([r['status'] for r in result['results']],
                         ['blocked-filesystem', 'valid-metadata-only'])

    def test_replacement_fifo_is_opened_nonblocking_rejected_before_read_and_closed(self):
        actual_open = os.open
        descriptors = []
        preserved = self.root / 'preserved.json'
        def swap(name, flags, *args, **kwargs):
            if name == self.path.name:
                # Guard first: a regressed blocking open is never executed.
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                self.path.rename(preserved)
                os.mkfifo(self.path)
            descriptor = actual_open(name, flags, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(reader.os, 'open', side_effect=swap), patch.object(reader.os, 'read') as read:
            buffers = read_metadata(self.binding)
            read.assert_not_called()
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-not-regular'))
        self.assertEqual(preserved.read_bytes(), self.raw)
        self.assert_closed(descriptors)

    def test_replacement_parent_symlink_cannot_redirect_leaf_open(self):
        parent = self.root / 'metadata-parent'
        parent.mkdir()
        self.path.rename(parent / self.path.name)
        replacement = self.root / 'unselected-parent'
        replacement.mkdir()
        (replacement / self.path.name).write_bytes(b'authored-unselected')
        self.binding['metadata'][0]['path'] = str(parent / self.path.name)
        actual_open = os.open
        descriptors = []
        def swap(name, flags, *args, **kwargs):
            if name == parent.name:
                self.assertTrue(flags & os.O_NOFOLLOW)
                self.assertTrue(flags & os.O_DIRECTORY)
                parent.rename(self.root / 'preserved-parent')
                parent.symlink_to(replacement, target_is_directory=True)
            descriptor = actual_open(name, flags, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(reader.os, 'open', side_effect=swap), patch.object(reader.os, 'read') as read:
            buffers = read_metadata(self.binding)
            read.assert_not_called()
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-path-rejected'))
        self.assertEqual((self.root / 'preserved-parent' / self.path.name).read_bytes(), self.raw)
        self.assert_closed(descriptors)

    def test_oversize_descriptor_is_rejected_before_read(self):
        with self.path.open('wb') as stream:
            stream.truncate(reader.MAX_METADATA_BYTES + 1)
        with patch.object(reader.os, 'read') as read:
            buffers = read_metadata(self.binding)
            read.assert_not_called()
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-limit-or-type'))

    def test_descriptor_change_is_not_returned_as_valid_metadata(self):
        actual_fstat = os.fstat
        calls = []
        def changed(descriptor):
            state = actual_fstat(descriptor)
            calls.append(descriptor)
            if len(calls) == 2:
                fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
                values = {field: getattr(state, field) for field in fields}
                values['st_mtime_ns'] += 1
                return SimpleNamespace(**values)
            return state
        with patch.object(reader.os, 'fstat', side_effect=changed):
            buffers = read_metadata(self.binding)
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-changed-during-read'))
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assert_closed(calls)

    def test_read_failure_closes_descriptor_and_missing_stays_missing(self):
        actual_open = os.open
        descriptors = []
        def track(*args, **kwargs):
            descriptor = actual_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        with patch.object(reader.os, 'open', side_effect=track), \
                patch.object(reader.os, 'read', side_effect=OSError(errno.EIO, 'authored failure')):
            buffers = read_metadata(self.binding)
        self.assertEqual(buffers['manifest'], MetadataReadFailure('metadata-read-failed'))
        self.assert_closed(descriptors)
        self.path.unlink()
        self.assertEqual(read_metadata(self.binding), {'manifest': None})


if __name__ == '__main__':
    unittest.main()
