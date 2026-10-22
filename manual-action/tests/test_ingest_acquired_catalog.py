"""Generated receipt/cache fixtures only: never a claim about Foo's live files."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_acquired_catalog as catalog
from fetch_sources import artifact_key as fetch_artifact_key
from ingest_api import source_key
from ingest_store import _fingerprint


class AcquiredCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='offmenu-acquired-catalog-fixture-')
        self.root = Path(self.tmp.name) / 'cache'
        self.root.mkdir()
        self.manifest = json.loads(catalog.DEFAULT_MANIFEST.read_text())
        self.manifest['sources'] = [s for s in self.manifest['sources'] if s['production_enabled']]
        self.receipts = {}
        for source in self.manifest['sources']:
            for artifact in source['artifacts']:
                # These deliberately tiny synthetic bytes test custody, not parsing.
                raw = json.dumps({'fixture': source['id'], 'artifact': artifact['name']}).encode()
                artifact['expected_bytes'] = len(raw)
                artifact['max_bytes'] = max(len(raw), 1024)
                if artifact.get('sha256'):
                    artifact['sha256'] = hashlib.sha256(raw).hexdigest()
                self.put(source, artifact, raw)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, source, artifact, raw):
        target = self.root / source['id'] / artifact['name']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        receipt = {'schema': 'offmenu-source-fetch/1', 'source_id': source['id'],
            'artifact': artifact['name'], 'artifact_key': fetch_artifact_key(source, artifact),
            'source_revision': source['revision'], 'origin_url': artifact['url'],
            'license': source['license'], 'license_evidence': source['license_evidence'],
            'attribution': source['attribution'], 'license_scope_note': source.get('license_scope_note'),
            'artifact_metadata_evidence': source.get('artifact_metadata_evidence'),
            'catalog_resource_id': artifact.get('resource_id'),
            'artifact_license_evidence': artifact.get('license_evidence'),
            'transport_integrity': artifact.get('transport_integrity', 'https'),
            'acquisition_only': True, 'ingested': False, 'raw_data_uploaded': False,
            'status': 'complete', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'expected_bytes': artifact.get('expected_bytes'), 'expected_sha256': artifact.get('sha256'),
            'checksum_basis': 'publisher_sha256_verified' if artifact.get('sha256') else 'locally_observed_not_publisher_authenticated',
            'completed_at': '2026-10-22T00:00:00Z'}
        receipt_path = Path(str(target) + '.receipt.json')
        receipt_path.write_text(json.dumps(receipt))
        self.receipts[(source['id'], artifact['name'])] = receipt_path
        return target, receipt_path

    def discover(self, existing=(), **options):
        return catalog.discover_acquired_sources({'acquired_cache_root': str(self.root),
            'acquired_manifest': self.manifest, **options}, existing_sources=existing)

    def chosen(self, sid, name=None):
        source = next(s for s in self.manifest['sources'] if s['id'] == sid)
        artifact = next((a for a in source['artifacts'] if a['name'] == name), source['artifacts'][0])
        return source, artifact, self.root / sid / artifact['name']

    def alter_receipt(self, sid, field, value):
        source, artifact, path = self.chosen(sid)
        receipt_path = self.receipts[(sid, artifact['name'])]
        receipt = json.loads(receipt_path.read_text())
        receipt[field] = value
        receipt_path.write_text(json.dumps(receipt))

    def test_exact_50_bindings_and_no_broad_scandir(self):
        with patch('os.scandir', side_effect=AssertionError('no directory crawl')):
            result = self.discover()
        self.assertTrue(result['complete'])
        self.assertFalse(result['truncated'])
        self.assertEqual(len(result['sources']), 50)
        self.assertEqual(result['counts']['candidate'], 50)
        self.assertEqual(len(catalog.BINDINGS), 50)
        self.assertEqual({s['provider'] for s in result['sources']}, {s['id'] for s in self.manifest['sources']})
        self.assertTrue(all(s['metadata']['acquisition']['verified'] is True for s in result['sources']))
        self.assertTrue(all(s['custody'] == 'private_local_cache_verified_against_receipt' for s in result['sources']))
        self.assertTrue(all(s['loaded'] is False for s in result['sources']))
        expected = {'menus.json': ['recipes', 'citations'],
            'denrees-extrait-de-datameal.json': ['ingredients', 'citations'],
            'liste-des-ft-des-denrees-de-la-cc-tls.json': ['citations'],
            'met_plat_cantine.json': ['recipes', 'ingredients', 'citations']}
        for row in result['sources']:
            if row['artifact_name'] in expected:
                self.assertEqual(row['domains'], expected[row['artifact_name']])
        cnous = next(s for s in result['sources'] if s['provider'] == 'fr_cnous_menus')
        self.assertEqual(cnous['domains'], ['recipes', 'ingredients', 'citations'])
        self.assertEqual(cnous['metadata']['acquisition']['transport_integrity'], 'unverified_http')

    def test_fetch_key_is_exact_canonical_contract(self):
        for source in self.manifest['sources']:
            for artifact in source['artifacts']:
                self.assertEqual(catalog.artifact_key(source, artifact), fetch_artifact_key(source, artifact))

    def test_receipt_hash_size_and_source_identity_mismatches_are_isolated(self):
        for field, value in (('source_id', 'other'), ('artifact_key', '0' * 64),
                ('source_revision', 'other'), ('origin_url', 'https://invalid.example/'),
                ('license', 'fabricated'), ('bytes', 1), ('sha256', '0' * 64),
                ('acquisition_only', 1), ('ingested', True), ('status', 'partial')):
            with self.subTest(field=field):
                source, artifact, path = self.chosen('forkrecipe')
                receipt_path = self.receipts[(source['id'], artifact['name'])]
                original = receipt_path.read_bytes()
                self.alter_receipt('forkrecipe', field, value)
                result = self.discover()
                row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
                self.assertEqual(row['disposition'], 'incomplete-hold')
                self.assertFalse(row['metadata']['acquisition']['verified'])
                self.assertEqual(result['counts']['candidate'], 49)
                self.assertFalse(result['complete'])
                receipt_path.write_bytes(original)

    def test_cache_same_size_corruption_is_detected(self):
        _, _, path = self.chosen('forkrecipe')
        original = path.read_bytes()
        path.write_bytes(b'x' * len(original))
        result = self.discover()
        row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
        self.assertEqual(row['reason'], 'cache_checksum_mismatch')
        self.assertEqual(result['counts']['candidate'], 49)

    def test_no_cache_mutations_and_metadata_only_repeat(self):
        before = {p: (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}
        first = self.discover()
        old_keys = {r['id']: source_key(r) for r in first['sources']}
        old_fp = {r['id']: _fingerprint(r) for r in first['sources']}
        with patch.object(catalog, '_verify_file', side_effect=AssertionError('unchanged source must not be rehashed')):
            second = self.discover(first['sources'], acquired_max_hash_bytes=0)
        self.assertTrue(second['complete'])
        for row in second['sources']:
            self.assertEqual(row['metadata']['acquisition']['verification_basis'], 'cached_byte_hash_and_current_metadata')
            self.assertEqual(source_key(row), old_keys[row['id']])
            self.assertEqual(_fingerprint(row), old_fp[row['id']])
        after = {p: (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_changed_identity_does_not_reuse_old_digest(self):
        first = self.discover()
        _, _, path = self.chosen('forkrecipe')
        info = path.stat()
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 10_000_000))
        real_verify = catalog._verify_file
        with patch.object(catalog, '_verify_file', wraps=real_verify) as verify:
            second = self.discover(first['sources'])
        self.assertEqual(verify.call_count, 1)
        self.assertTrue(second['complete'])

    def test_missing_receipt_is_not_inferred_from_summary_or_final_file(self):
        source, artifact, _ = self.chosen('forkrecipe')
        self.receipts[(source['id'], artifact['name'])].unlink()
        (self.root / 'fetch-summary.json').write_text('{"status":"complete","files":50}')
        result = self.discover()
        self.assertEqual(result['counts']['candidate'], 49)
        self.assertTrue(any(e['code'] == 'selected_file_missing' for e in result['errors']))

    def test_permissions_fail_per_file_without_chmod_or_fallback(self):
        _, _, denied = self.chosen('forkrecipe')
        real_regular = catalog._regular
        def guarded(path):
            if path == denied:
                raise PermissionError('fixture must not expose this text')
            return real_regular(path)
        with patch.object(catalog, '_regular', side_effect=guarded), patch('os.chmod', side_effect=AssertionError('no chmod')):
            result = self.discover()
        row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
        self.assertEqual(row['disposition'], 'unreadable')
        self.assertEqual(row['reason'], 'read_permission_denied')
        self.assertEqual(result['counts']['candidate'], 49)
        self.assertNotIn('fixture must not expose', json.dumps(result))

    def test_permission_is_rechecked_before_reusing_prior_verification(self):
        first = self.discover()
        _, _, denied = self.chosen('forkrecipe')
        regular = catalog._regular
        with patch.object(catalog, '_regular', side_effect=lambda p: (_ for _ in ()).throw(PermissionError()) if p == denied else regular(p)):
            second = self.discover(first['sources'])
        self.assertEqual(next(r for r in second['sources'] if r['provider'] == 'forkrecipe')['reason'], 'read_permission_denied')

    def test_symlink_file_and_parent_are_not_followed(self):
        source, artifact, path = self.chosen('forkrecipe')
        target = path.with_name('offscope')
        path.rename(target)
        path.symlink_to(target)
        first = self.discover()
        self.assertEqual(first['counts']['candidate'], 49)
        path.unlink()
        target.rename(path)
        directory = path.parent
        alternate = directory.with_name('elsewhere')
        directory.rename(alternate)
        directory.symlink_to(alternate, target_is_directory=True)
        second = self.discover()
        self.assertEqual(second['counts']['candidate'], 49)

    def test_rights_hold_does_not_block_unrelated_families(self):
        source, _, _ = self.chosen('forkrecipe')
        source['rights_status'] = 'rights_unresolved'
        result = self.discover()
        row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
        self.assertEqual(row['disposition'], 'restricted')
        self.assertEqual(result['counts']['candidate'], 49)
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['complete'])  # Catalog complete, not ingest complete.

    def test_disabled_sources_are_dispositions_not_fake_input_files(self):
        self.manifest['sources'].append({'id': 'held_fixture', 'production_enabled': False,
                                        'disabled_reason': 'fixture unresolved', 'artifacts': []})
        result = self.discover()
        self.assertEqual(len(result['sources']), 50)
        self.assertEqual(result['source_dispositions'], [{'source_id': 'held_fixture', 'status': 'disabled',
                                                         'reason': 'source_disabled_in_reviewed_manifest'}])

    def test_unknown_artifact_never_uses_generic_parser(self):
        source, artifact, _ = self.chosen('forkrecipe')
        artifact['name'] = 'unknown.tar.gz'
        result = self.discover()
        row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
        self.assertEqual(row['disposition'], 'adapter-required')
        self.assertNotIn('acquired_adapter', row)
        self.assertFalse(row['metadata']['acquisition']['verified'])

    def test_file_budget_resumes_exact_next_index_without_resetting_retained(self):
        first = self.discover(acquired_max_files=4)
        self.assertTrue(first['truncated'])
        self.assertEqual(first['resume_cursor']['next_index'], 4)
        second = self.discover(first['sources'], acquired_resume_cursor=first['resume_cursor'])
        self.assertEqual(len(second['sources']), 46)
        self.assertFalse(second['truncated'])
        merged = catalog.merge_acquired_sources(first['sources'], second)
        self.assertEqual(len(merged), 50)
        self.assertEqual(len({s['id'] for s in merged}), 50)
        changed = copy.deepcopy(first['resume_cursor'])
        changed['manifest_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identity_changed'):
            self.discover(acquired_resume_cursor=changed)

    def test_byte_budget_never_marks_unhashed_file_verified(self):
        result = self.discover(acquired_max_hash_bytes=1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['sources'], [])
        self.assertEqual(result['resume_cursor']['next_index'], 0)
        self.assertEqual(result['stop_reason'], 'hash_byte_budget')

    def test_merge_preserves_unrelated_ids_fingerprints_and_arbitrary_cursor(self):
        unrelated = {'id': 'existing-retained', 'path': '/known/retained.json',
            'sha256': '1' * 64, 'adapter_version': 7, 'format': 'json', 'cursor': 12345,
            'source_version': 'preserved', 'metadata': {'evidence': 'unchanged'}}
        original = copy.deepcopy(unrelated)
        result = self.discover([unrelated])
        merged = catalog.merge_acquired_sources([unrelated], result)
        self.assertEqual(merged[0], original)
        self.assertEqual(unrelated, original)

    def test_medline_pairs_remain_distinct_and_attribution_preserved(self):
        result = self.discover()
        rows = [r for r in result['sources'] if r['provider'] == 'medlineplus_healthy_recipes']
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({r['work_id'] for r in rows}), 6)
        self.assertEqual({r['language'] for r in rows}, {'en', 'es'})
        self.assertTrue(all(r['counterpart_url'] and r['metadata']['acquisition']['artifact_attribution'] for r in rows))

    def test_compatible_verified_byte_alias_is_deduplicated(self):
        first = self.discover()
        row = next(r for r in first['sources'] if r['provider'] == 'forkrecipe')
        alias_path = Path(self.tmp.name) / 'retained-forkrecipe.tar.gz'
        alias_path.write_bytes(Path(row['path']).read_bytes())
        alias = copy.deepcopy(row)
        alias.update(id='retained-compatible-source', path=str(alias_path), identity=catalog._identity(alias_path.stat()))
        result = self.discover([alias])
        current = next(r for r in result['sources'] if r['provider'] == 'forkrecipe')
        self.assertEqual(current['disposition'], 'duplicate')
        self.assertEqual(current['duplicate_of'], alias['id'])

    def test_alias_with_incompatible_parser_not_silently_skipped(self):
        first = self.discover()
        row = next(r for r in first['sources'] if r['provider'] == 'forkrecipe')
        alias_path = Path(self.tmp.name) / 'retained-copy.tar.gz'
        alias_path.write_bytes(Path(row['path']).read_bytes())
        alias = copy.deepcopy(row)
        alias.update(id='generic-old-input', path=str(alias_path), identity=catalog._identity(alias_path.stat()))
        alias.pop('acquired_adapter')
        result = self.discover([alias])
        current = next(r for r in result['sources'] if r['provider'] == 'forkrecipe')
        self.assertEqual(current['disposition'], 'candidate')
        self.assertIn(alias['id'], current['metadata']['acquisition']['content_aliases'])

    def test_known_restricted_alias_never_becomes_cleared(self):
        first = self.discover()
        row = next(r for r in first['sources'] if r['provider'] == 'forkrecipe')
        row['restricted'] = True
        row['disposition'] = 'restricted'
        result = self.discover([row])
        current = next(r for r in result['sources'] if r['provider'] == 'forkrecipe')
        self.assertEqual(current['disposition'], 'restricted')

    def test_receipt_replaced_during_hash_is_not_accepted(self):
        source, artifact, path = self.chosen('forkrecipe')
        receipt_path = self.receipts[(source['id'], artifact['name'])]
        real_verify = catalog._verify_file
        def replacement(target, receipt, budget):
            out = real_verify(target, receipt, budget)
            if target == path:
                receipt_path.write_bytes(receipt_path.read_bytes() + b' ')
            return out
        with patch.object(catalog, '_verify_file', side_effect=replacement):
            result = self.discover()
        current = next(r for r in result['sources'] if r['provider'] == 'forkrecipe')
        self.assertEqual(current['reason'], 'receipt_changed_during_verification')
        self.assertFalse(current['metadata']['acquisition']['verified'])


    def test_access_preflight_reads_no_payload_and_reports_only_access(self):
        options = {'acquired_cache_root': str(self.root), 'acquired_manifest': self.manifest}
        with patch.object(catalog, '_verify_file', side_effect=AssertionError('no hash')):
            result = catalog.preflight_acquired_access(options)
        self.assertEqual(result['status'], 'readable')
        self.assertEqual(result['counts']['artifact_receipt_pairs_readable'], 50)
        self.assertFalse(result['integrity_verified'])
        source, artifact, _ = self.chosen('forkrecipe')
        self.receipts[(source['id'], artifact['name'])].unlink()
        result = catalog.preflight_acquired_access(options)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['counts']['artifact_receipt_pairs_blocked'], 1)

    @unittest.skipUnless(hasattr(os, 'O_PATH'), 'Linux O_PATH contract')
    def test_parent_walk_uses_opath_not_directory_listing(self):
        calls = []
        actual = os.open
        def observed(path, flags, *args, **kwargs):
            calls.append((path, flags))
            return actual(path, flags, *args, **kwargs)
        with patch.object(catalog.os, 'open', side_effect=observed):
            result = self.discover()
        self.assertTrue(result['complete'])
        directory_calls = [flags for _, flags in calls if flags & os.O_DIRECTORY]
        self.assertTrue(directory_calls)
        self.assertTrue(all(flags & os.O_PATH and flags & os.O_NOFOLLOW for flags in directory_calls))

    def test_manifest_format_binding_mismatch_is_held(self):
        source, artifact, _ = self.chosen('forkrecipe')
        artifact['format'] = 'json'
        result = self.discover()
        row = next(s for s in result['sources'] if s['provider'] == 'forkrecipe')
        self.assertEqual(row['reason'], 'manifest_format_binding_mismatch')
        self.assertFalse(row['metadata']['acquisition']['verified'])


if __name__ == '__main__':
    unittest.main()
