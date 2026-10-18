"""Shared fixture lifecycle regressions. No historical inputs or online requests."""
import base64
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import gzip
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core, fixture_resources, policy, registry, serialization
from offmenu.refresh.__main__ import main
from offmenu_norway import adapter

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/norway'
GOLDEN_CONTENT = '09d8c24fff64d0a26b567dbc831632b102789843a8d52bed791faf2bf82e1153'
GOLDEN_TRANSPORT = '246d3afdcf54f0386db40170a328cd394651bf2053fa8e207a7c8abe35706455'


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'work'
        self.entry = registry.fixture('norway', repin_runtime=True)

    def replay(self, **kwargs):
        return core.replay_fixture('norway', self.workspace, repin_runtime=True, **kwargs)

    def cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(args)
        return code, json.loads(output.getvalue())

    def rows(self):
        with sqlite3.connect(self.workspace / 'checkpoint.sqlite') as db:
            return db.execute('SELECT run_id,identity,pins,stage,artifacts FROM runs ORDER BY rowid').fetchall()

    def test_resource_bytes_match_exact_reviewed_fixture_and_lock(self):
        self.assertEqual(fixture_resources.NORWAY_LOCK, (ROOT / 'tests/fixtures/norway.lock.json').read_bytes())
        self.assertEqual(self.entry.blobs, {p.name: p.read_bytes() for p in FIXTURE.iterdir()})
        self.assertEqual(self.entry.dependencies, adapter.DEPENDENCIES)

    def test_untrusted_labels_and_modified_locks_fail_before_body_or_cache_reads(self):
        with patch.object(registry.base64, 'b64decode', side_effect=AssertionError('body read')):
            for name in ('historical-source-snapshot', 'ciqual', '../norway', 'matvaretabellen'):
                with self.assertRaisesRegex(core.RefreshError, 'fixture-not-registered'):
                    core.replay_fixture(name, self.workspace)
            lock = copy.deepcopy(self.entry.lock)
            lock['scope'] = 'historical-source-snapshot'
            with patch.object(fixture_resources, 'NORWAY_LOCK', core.canonical(lock)):
                with self.assertRaisesRegex(core.RefreshError, 'fixture-lock-pin-mismatch'):
                    self.replay()
        self.assertFalse(self.workspace.exists())

    def test_dependency_rights_contract_rejected_before_body_reads(self):
        with patch.object(registry, 'verify', side_effect=core.RefreshError('asset-checksum-mismatch')):
            with patch.object(registry.base64, 'b64decode', side_effect=AssertionError('body read')):
                with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
                    self.replay()
        self.assertFalse(self.workspace.exists())

    def test_changed_each_body_or_missing_member_is_never_admitted(self):
        for name in fixture_resources.NORWAY_BLOBS:
            changed = dict(fixture_resources.NORWAY_BLOBS)
            changed[name] = base64.b64encode(b'{}').decode()
            with patch.object(fixture_resources, 'NORWAY_BLOBS', changed):
                with self.assertRaisesRegex(core.RefreshError, 'fixture-input-pin-mismatch'):
                    self.replay()
            changed.pop(name)
            with patch.object(fixture_resources, 'NORWAY_BLOBS', changed):
                with self.assertRaisesRegex(core.RefreshError, 'fixture-bundle-set-mismatch'):
                    self.replay()
        self.assertFalse(self.workspace.exists())

    def test_cli_forbids_arbitrary_source_paths_locks_modules_and_historical_scope(self):
        for flag in ('--input-root', '--lock', '--module', '--scope'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                main(['replay-fixture', '--fixture', 'norway', '--workspace', str(self.workspace), flag, 'SECRET'])
            self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.workspace.exists())

    def test_shared_cli_replay_noop_force_and_no_acceptance(self):
        args = ['replay-fixture', '--fixture', 'norway', '--workspace', str(self.workspace), '--repin-synthetic-runtime']
        code, first = self.cli(args)
        self.assertEqual(code, 0)
        self.assertEqual(first['counts']['normalized'], 2)
        self.assertIsNone(first['counts']['accepted'])
        self.assertEqual(first['acceptance'], 'not-performed')
        self.assertFalse(first['countryCoverage']['complete'])
        self.assertFalse(first['network']['osNetworkConfinementVerified'])
        self.assertNotIn(str(self.root), json.dumps(first))
        final = self.workspace / 'releases' / first['identity']
        mtimes = {p.name: p.stat().st_mtime_ns for p in final.iterdir()}
        with patch.object(core, 'transform_bundle', side_effect=AssertionError('no-op transformed')):
            code, second = self.cli(args)
        self.assertEqual(second['action'], 'verified-no-op')
        third = self.replay(force=True)
        self.assertEqual(third['action'], 'force-verified-identical')
        self.assertEqual(first['artifacts'], third['artifacts'])
        self.assertEqual(mtimes, {p.name: p.stat().st_mtime_ns for p in final.iterdir()})
        self.assertEqual(len(list((self.workspace / 'cache/sha256').iterdir())), 4)
        self.assertFalse(list(self.workspace.glob('**/.norway-candidate.lock')))
        self.assertEqual(list((self.workspace / 'staging').iterdir()), [])
        self.assertFalse((self.workspace / 'accepted').exists())

    def test_independent_roots_reproduce_and_canonical_golden_is_always_checked(self):
        first = self.replay()
        other = core.replay_fixture('norway', self.root / 'other', repin_runtime=True)
        self.assertEqual(first['identity'], other['identity'])
        self.assertEqual(first['artifacts'], other['artifacts'])
        self.assertEqual(first['canonicalContentSha256'], GOLDEN_CONTENT)
        if adapter.runtime() == {'implementation': 'CPython', 'python': '3.12.14', 'zlib': '1.3.2'}:
            self.assertEqual(first['artifacts']['normalized.jsonl.gz']['sha256'], GOLDEN_TRANSPORT)
        # Source-library golden records and metadata remain byte-identical.
        original = adapter.render(self.entry.lock, FIXTURE)
        final = self.workspace / 'releases' / first['identity']
        self.assertEqual((final / 'normalized.jsonl.gz').read_bytes(), original['normalized.jsonl.gz'])
        self.assertEqual((final / 'source-metadata.json').read_bytes(), original['source-metadata.json'])

    def test_all_crash_boundaries_resume_same_run_and_bundle(self):
        for boundary in ('cached', 'transformed', 'renamed-before-checkpoint', 'published'):
            with self.subTest(boundary=boundary):
                self.workspace = self.root / boundary
                def crash(stage):
                    if stage == boundary:
                        raise RuntimeError('interrupted')
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    self.replay(failpoint=crash)
                run_id = self.rows()[0][0]
                with self.assertRaisesRegex(core.RefreshError, 'requires-resume'):
                    self.replay()
                result = self.replay(resume=True)
                self.assertEqual(result['runId'], run_id)
                self.assertEqual(self.rows()[0][3], 'complete')
                self.assertEqual(len(list((self.workspace / 'releases').iterdir())), 1)

    def test_partial_bundle_copy_never_reaches_cached_and_resumes_own_temporary(self):
        original = core.cache_input
        calls = 0
        def interrupted(source, target, expected, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                target.with_name(target.name + '.copy-' + kwargs['copy_id']).write_bytes(b'partial')
                raise RuntimeError('copy interrupted')
            return original(source, target, expected, **kwargs)
        with patch.object(core, 'cache_input', side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, 'copy interrupted'):
                self.replay()
        self.assertEqual(self.rows()[0][3], 'started')
        stray = self.workspace / 'cache/sha256/untouched.copy-other'
        stray.write_bytes(b'not this run')
        self.replay(resume=True)
        self.assertEqual(stray.read_bytes(), b'not this run')
        self.assertEqual(len(list((self.workspace / 'cache/sha256').glob('*.copy-*'))), 1)

    def test_partial_transform_is_restarted_and_unrelated_staging_untouched(self):
        def partial(caches, destination, entry, key, **kwargs):
            destination.mkdir()
            (destination / 'normalized.jsonl.gz').write_bytes(b'partial')
            raise RuntimeError('transform interrupted')
        with patch.object(core, 'transform_bundle', side_effect=partial):
            with self.assertRaises(RuntimeError):
                self.replay()
        other = self.workspace / 'staging/other'
        other.mkdir()
        (other / 'keep').write_text('untouched')
        self.assertEqual(self.replay(resume=True)['status'], 'complete')
        self.assertEqual((other / 'keep').read_text(), 'untouched')

    def test_corrupt_each_cache_member_and_force_are_refused(self):
        result = self.replay()
        for item in self.entry.lock['inputs']:
            cache = self.workspace / 'cache/sha256' / item['sha256']
            original = cache.read_bytes()
            for force in (False, True):
                cache.write_bytes(b'corrupt')
                with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
                    self.replay(force=force)
                self.assertEqual(cache.read_bytes(), b'corrupt')
                cache.write_bytes(original)
                # Errors leave started runs requiring this identity's resume.
                self.replay(resume=True)
        self.assertEqual(len(list((self.workspace / 'releases').iterdir())), 1)

    def test_shared_workspace_has_cross_source_checkpoints_caches_and_locks(self):
        def crash(stage):
            raise RuntimeError('interrupted')
        with self.assertRaises(RuntimeError):
            self.replay(failpoint=crash)
        manifest_path = ROOT / 'tests/fixtures/corpus-refresh/input-manifest.json'
        manifest = core.load_manifest(manifest_path)
        # Existing historical-snapshot behavior remains permitted by v1.
        manifest['scope'] = 'historical-source-snapshot'
        old = core.replay(manifest, manifest_path.parent, self.workspace)
        result = self.replay(resume=True)
        self.assertEqual(old['schemaVersion'], 'offmenu-refresh-receipt/1')
        self.assertEqual(old['scope'], 'historical-source-snapshot')
        self.assertNotEqual(old['identity'], result['identity'])
        self.assertEqual(len(list((self.workspace / 'cache/sha256').iterdir())), 5)
        self.assertEqual({p.name for p in (self.workspace / 'locks').iterdir()}, {'wikibooks.lock', 'matvaretabellen.lock'})
        self.assertEqual(len({r[1] for r in self.rows()}), 2)
        self.assertTrue(all(r[3] == 'complete' for r in self.rows()))

    def test_source_and_workspace_locks_block_without_replacing_inode(self):
        (self.workspace / 'locks').mkdir(parents=True)
        for lock in (self.workspace / 'workspace.lock', self.workspace / 'locks/matvaretabellen.lock'):
            with core.writer_lock(lock):
                before = lock.stat().st_ino
                with self.assertRaisesRegex(core.RefreshError, 'writer-lock-held'):
                    self.replay()
                self.assertEqual(lock.stat().st_ino, before)
        self.assertFalse((self.workspace / 'checkpoint.sqlite').exists())

    def test_changed_code_blocks_publish_and_resume_requires_identical_pins(self):
        original = core.code_identity
        calls = 0
        def changed(**kwargs):
            nonlocal calls
            calls += 1
            result = original(**kwargs)
            if calls > 1:
                result['codeFingerprint'] = 'f' * 64
            return result
        with patch.object(core, 'code_identity', side_effect=changed):
            with self.assertRaisesRegex(core.RefreshError, 'code-changed-during-run'):
                self.replay()
        self.assertEqual(list((self.workspace / 'releases').iterdir()), [])
        with patch.dict(serialization.POLICY, {'schemaVersion': 'changed-policy'}):
            with self.assertRaisesRegex(core.RefreshError, 'no-matching-run'):
                self.replay(resume=True)
        self.assertEqual(self.replay(resume=True)['status'], 'complete')

    def test_corrupt_transport_is_not_overwritten(self):
        result = self.replay()
        output = self.workspace / 'releases' / result['identity'] / 'normalized.jsonl.gz'
        altered = bytearray(output.read_bytes())
        altered[4] = 1  # gzip mtime only, identical uncompressed content
        output.write_bytes(altered)
        self.assertEqual(gzip.decompress(altered), gzip.decompress(adapter.render(self.entry.lock, FIXTURE)['normalized.jsonl.gz']))
        with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
            self.replay()
        self.assertEqual(output.read_bytes(), altered)

    def test_runtime_labels_change_build_pins_not_canonical_content(self):
        first = registry.render(self.entry, FIXTURE, 'a' * 64)
        alternative = {**adapter.runtime(), 'python': 'synthetic-other-runtime'}
        with patch.object(adapter, 'runtime', return_value=alternative):
            other = registry.fixture('norway', repin_runtime=True)
            second = registry.render(other, FIXTURE, 'b' * 64)
        self.assertEqual(first['content-manifest.json'], second['content-manifest.json'])
        self.assertEqual(first['source-metadata.json'], second['source-metadata.json'])
        self.assertEqual(gzip.decompress(first['normalized.jsonl.gz']), gzip.decompress(second['normalized.jsonl.gz']))
        self.assertNotEqual(first['build-manifest.json'], second['build-manifest.json'])
        self.assertNotEqual(core.sha(core.canonical(self.entry.pins())), core.sha(core.canonical(other.pins())))

    def test_gzip_policy_changes_only_build_and_transport_not_content(self):
        first = registry.render(self.entry, FIXTURE, 'a' * 64)
        with patch.dict(serialization.POLICY, {'gzip': {'filename': '', 'mtime': 1, 'compresslevel': 9}}):
            second = registry.render(self.entry, FIXTURE, 'b' * 64)
        self.assertEqual(first['content-manifest.json'], second['content-manifest.json'])
        self.assertNotEqual(first['normalized.jsonl.gz'], second['normalized.jsonl.gz'])
        self.assertEqual(gzip.decompress(first['normalized.jsonl.gz']), gzip.decompress(second['normalized.jsonl.gz']))
        self.assertNotEqual(first['build-manifest.json'], second['build-manifest.json'])

    def test_plan_does_not_decode_source_or_create_workspace(self):
        with patch.object(registry.base64, 'b64decode', side_effect=AssertionError('decoded source')):
            code, result = self.cli(['plan-fixture', '--fixture', 'norway', '--repin-synthetic-runtime'])
        self.assertEqual(code, 0)
        self.assertFalse(result['assetBytesVerifiedByThisPlan'])
        self.assertEqual(result['networkRequests'], 0)
        self.assertIsNone(result['acquisitionAgeDays'])
        self.assertFalse(self.workspace.exists())

    def test_30_day_policy_uses_original_acquisition_and_no_304_or_200_reset(self):
        acquired = datetime(2026, 9, 1, tzinfo=timezone.utc)
        evidence = {'schemaVersion': 'offmenu-refresh-acquisition-evidence/2',
                    'inputBundleSha256': self.entry.bundle_key(), 'originalAcquiredAt': acquired.isoformat(),
                    'revalidations': []}
        before = core.sha(core.canonical(self.entry.pins()))
        early = policy.plan_fixture('norway', evidence, now=acquired + timedelta(days=29, hours=23), repin_runtime=True)
        self.assertEqual(early['decision'], 'reuse-verified-retained-inputs')
        for status in ('not-modified-304', 'identical-body-200'):
            evidence['revalidations'] = [{'observedAt': (acquired + timedelta(days=30)).isoformat(),
                                         'result': status, 'inputBundleSha256': self.entry.bundle_key()}]
            late = policy.plan_fixture('norway', evidence, now=acquired + timedelta(days=30), repin_runtime=True)
            self.assertEqual(late['acquisitionAgeDays'], 30)
            self.assertEqual(late['decision'], 'revalidation-review-required-no-download')
            self.assertEqual(late['nextOnlineStep'], 'none')
        self.assertEqual(before, core.sha(core.canonical(registry.fixture('norway', repin_runtime=True).pins())))
        evidence['inputBundleSha256'] = 'e' * 64
        with self.assertRaisesRegex(core.RefreshError, 'evidence-bundle-mismatch'):
            policy.plan_fixture('norway', evidence, now=acquired, repin_runtime=True)

    def test_force_refresh_does_not_acquire_or_create_workspace(self):
        code, result = self.cli(['replay-fixture', '--fixture', 'norway', '--workspace', str(self.workspace), '--force-refresh'])
        self.assertEqual(code, 2)
        self.assertEqual(result['errorCode'], 'online-acquisition-not-implemented')
        self.assertFalse(self.workspace.exists())

    def test_packaged_identity_is_content_based_without_git_or_legacy_script(self):
        with patch.object(core.subprocess, 'check_output', side_effect=FileNotFoundError()):
            result = core.code_identity(extra_files=self.entry.dependencies, packaged=True)
        self.assertIsNone(result['codeCommit'])
        self.assertIsNone(result['codeDirty'])
        self.assertRegex(result['codeFingerprint'], r'^[0-9a-f]{64}$')
        with patch.object(core.subprocess, 'check_output', side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(core.RefreshError, 'git-code-identity-unavailable'):
                core.code_identity()

    def test_shared_serializer_has_fixed_headers_and_semantic_arrays(self):
        raw = serialization.encode_records([{'z': None, 'a': [0, None, 'trace']}, {'a': 'é'}])
        self.assertEqual(raw, b'[{"a":[0,null,"trace"],"z":null}]\n[{"a":"\xc3\xa9"}]\n')
        compressed = serialization.compress(raw)
        self.assertEqual(compressed[:10], b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x04\xff')
        self.assertEqual(gzip.decompress(compressed), raw)
        with self.assertRaises(ValueError):
            serialization.encode_records([{'amount': float('nan')}])


if __name__ == '__main__':
    unittest.main()
