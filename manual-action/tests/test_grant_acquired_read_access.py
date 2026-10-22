"""Pure/synthetic ACL tests: no Foo calls or public-file ACL mutations."""
import copy
import ctypes
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import contextlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import grant_acquired_read_access as handoff


def acl(owner=6, group=0, other=0):
    return {(handoff.USER_OBJ, None): owner, (handoff.GROUP_OBJ, None): group, (handoff.OTHER, None): other}


class FakeACL:
    def __init__(self, values):
        self.values = copy.deepcopy(values)
        self.writes = []
        self.fail_calls = set()
        self.after_set = None
    def get(self, fd):
        return copy.deepcopy(self.values[fd])
    def set(self, fd, value):
        self.writes.append((fd, copy.deepcopy(value)))
        if len(self.writes) in self.fail_calls:
            raise handoff.Refusal('acl_operation_failed')
        self.values[fd] = copy.deepcopy(value)
        if self.after_set:
            self.after_set(fd, value)


class NarrowACLTests(unittest.TestCase):
    def setUp(self):
        self.owner = SimpleNamespace(st_uid=1111, st_gid=1111)
        self.uid = 2222

    def desired(self, original, required=4, groups=()):
        return handoff.plan_acl(original, self.uid, required, self.owner, groups)

    def test_private_file_named_read_only_no_effective_group_world_grant(self):
        original = acl()
        result = self.desired(original)
        self.assertEqual(result[(handoff.USER, self.uid)], 4)
        self.assertEqual(result[(handoff.MASK, None)], 4)
        self.assertEqual(result[(handoff.GROUP_OBJ, None)], 0)
        self.assertEqual(result[(handoff.OTHER, None)], 0)
        self.assertEqual(original, acl())
        before = handoff.effective_acl_entries(original)
        after = handoff.effective_acl_entries(result)
        self.assertTrue(all(after[k] == v for k, v in before.items()))

    def test_directory_grant_is_traversal_not_listing_or_write(self):
        result = self.desired(acl(owner=7), required=1)
        self.assertEqual(result[(handoff.USER, self.uid)], 1)
        self.assertEqual(handoff.target_access(result, self.owner, self.uid, set()), 1)

    def test_preexisting_directory_read_cannot_be_combined_with_new_traverse(self):
        original = {**acl(owner=7), (handoff.MASK, None): 4, (handoff.USER, self.uid): 4}
        with self.assertRaisesRegex(handoff.Refusal, 'target_existing_permissions_exceed_scope'):
            self.desired(original, required=1)

    def test_mask_expansion_that_would_expose_latent_group_rights_is_blocked(self):
        original = {**acl(group=7), (handoff.MASK, None): 0, (handoff.USER, 3333): 0}
        with self.assertRaisesRegex(handoff.Refusal, 'acl_mask_expansion_would_broaden_others'):
            self.desired(original)

    def test_mask_expansion_that_would_expose_latent_named_user_rights_is_blocked(self):
        original = {**acl(), (handoff.MASK, None): 1, (handoff.USER, 3333): 7}
        with self.assertRaisesRegex(handoff.Refusal, 'acl_mask_expansion_would_broaden_others'):
            self.desired(original)

    def test_preexisting_effective_masked_principals_are_unchanged(self):
        original = {**acl(group=4), (handoff.MASK, None): 5,
                    (handoff.USER, 3333): 5, (handoff.GROUP, 4444): 4}
        result = self.desired(original)
        a, b = handoff.effective_acl_entries(original), handoff.effective_acl_entries(result)
        self.assertTrue(all(b[k] == v for k, v in a.items()))

    def test_target_existing_write_or_file_execute_permission_blocks(self):
        for bits in (1, 2, 3, 5, 6, 7):
            with self.subTest(bits=bits):
                original = {**acl(), (handoff.MASK, None): 7, (handoff.USER, self.uid): bits}
                with self.assertRaisesRegex(handoff.Refusal, 'target_existing_permissions_exceed_scope'):
                    self.desired(original)

    def test_existing_same_target_grant_is_idempotent(self):
        first = self.desired(acl())
        self.assertEqual(self.desired(first), first)

    def test_named_user_precedes_group_and_other_rights(self):
        original = {**acl(group=7, other=7), (handoff.MASK, None): 7, (handoff.USER, self.uid): 4}
        self.assertEqual(handoff.target_access(original, self.owner, self.uid, {1111}), 4)

    def test_multiple_group_entries_union_effective_permissions(self):
        original = {**acl(group=1), (handoff.MASK, None): 5, (handoff.GROUP, 4444): 4}
        self.assertEqual(handoff.target_access(original, self.owner, self.uid, {1111, 4444}), 5)

    def test_no_default_acl_or_unknown_tag_in_serialization(self):
        text = handoff.acl_text(self.desired(acl()))
        self.assertEqual(text, 'user::rw-\nuser:2222:r--\ngroup::---\nmask::r--\nother::---\n')
        self.assertNotIn('default', text)
        for broken in ({}, {**acl(), (handoff.USER, None): 4}, {**acl(), (999, None): 4}):
            with self.assertRaises(handoff.Refusal):
                handoff.acl_text(broken)

    def plan(self):
        entries = []
        for fd, directory in ((1, False), (2, False), (3, True)):
            original = acl(owner=7 if directory else 6)
            entries.append({'fd': fd, 'path': '/fixture/dir' if directory else '/fixture/dir/file' + str(fd),
                'directory': directory, 'identity': [1, fd, 1, 0], 'owner_uid': 1111, 'owner_gid': 1111,
                'nlink': 1, 'default_acl': None, 'original': original,
                'desired': self.desired(original, required=1 if directory else 4)})
        return {'entries': entries, 'target_uid': 2222, 'actor_uid': 1111}

    def test_durable_snapshot_precedes_any_acl_write_and_default_acl_untouched(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        snapshots = []
        def snapshot(data):
            self.assertEqual(backend.writes, [])
            snapshots.append(data)
        with patch.object(handoff, 'unchanged_data', return_value=True), patch.object(handoff, 'default_acl', return_value=None):
            result = handoff.apply_plan(plan, backend, snapshot)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['outcome'], 'applied')
        self.assertEqual(result['changed_acls'], 3)
        self.assertEqual([fd for fd, _ in backend.writes], [1, 2, 3])
        self.assertEqual(snapshots[0]['target_uid'], 2222)
        self.assertTrue(all('original_acl' in r and 'planned_acl' in r for r in snapshots[0]['entries']))

    def test_snapshot_failure_never_changes_any_acl(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        with self.assertRaises(OSError):
            handoff.apply_plan(plan, backend, lambda data: (_ for _ in ()).throw(OSError()))
        self.assertEqual(backend.writes, [])

    def test_apply_failure_rolls_back_only_our_exact_still_matching_changes(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        original = copy.deepcopy(backend.values)
        backend.fail_calls = {2}
        with patch.object(handoff, 'unchanged_data', return_value=True), patch.object(handoff, 'default_acl', return_value=None):
            result = handoff.apply_plan(plan, backend, lambda data: None)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['outcome'], 'rolled_back')
        self.assertTrue(result['rollback_complete'])
        self.assertEqual(backend.values, original)

    def test_rollback_failure_is_partial_never_success(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        backend.fail_calls = {2, 3}
        with patch.object(handoff, 'unchanged_data', return_value=True), patch.object(handoff, 'default_acl', return_value=None):
            result = handoff.apply_plan(plan, backend, lambda data: None)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['error_code'], 'rollback_incomplete')
        self.assertFalse(result['rollback_complete'])

    def test_external_acl_change_is_not_overwritten_during_rollback(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        external = {**plan['entries'][0]['desired'], (handoff.OTHER, None): 4}
        def interfere(fd, value):
            if fd == 1:
                backend.values[1] = external
        backend.after_set = interfere
        with patch.object(handoff, 'unchanged_data', return_value=True), patch.object(handoff, 'default_acl', return_value=None):
            result = handoff.apply_plan(plan, backend, lambda data: None)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(backend.values[1], external)
        self.assertEqual(len(backend.writes), 1)

    def test_default_acl_race_blocks_without_writing_default_acl(self):
        plan = self.plan()
        backend = FakeACL({r['fd']: r['original'] for r in plan['entries']})
        with patch.object(handoff, 'unchanged_data', return_value=True), patch.object(handoff, 'default_acl', return_value='changed'):
            result = handoff.apply_plan(plan, backend, lambda data: None)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'default_acl_changed')
        self.assertEqual(backend.values[3], plan['entries'][2]['original'])

    def test_sanitizer_drops_private_acl_paths_and_requires_applied_mode(self):
        value = {'schemaVersion': handoff.SCHEMA, 'mode': 'apply', 'status': 'complete',
            'outcome': 'applied', 'error_code': 'none', 'source_bytes_verified': handoff.EXPECTED_BYTES,
            'source_artifacts_verified': 50, 'provenance_receipts_verified': 50, 'traversal_directories_verified': 9,
            'read_only_scope_verified': True, 'other_effective_permissions_preserved': True,
            'private_path': '/fixture/private', 'original_acl': 'private',
            'target_account': handoff.TARGET, 'manifest_sha256': handoff.MANIFEST_SHA, 'scope_plan_sha256': handoff.SCOPE_PLAN_SHA,
            'source_artifacts': 50, 'provenance_receipts': 50, 'traversal_directories': 9, 'changed_acls': 109,
            'raw_data_uploaded': False, 'source_bytes_modified': False, 'default_acls_modified': False}
        clean = handoff.sanitize_report(value)
        self.assertNotIn('/fixture', json.dumps(clean))
        self.assertNotIn('original_acl', clean)
        with self.assertRaises(ValueError):
            handoff.sanitize_report({**value, 'mode': 'plan'})
        with self.assertRaises(ValueError):
            handoff.sanitize_report({**value, 'provenance_receipts_verified': 49})
        for key, bad in (('target_account', 'root'), ('manifest_sha256', '0' * 64),
                ('source_artifacts', 49), ('traversal_directories', 10), ('changed_acls', 110),
                ('raw_data_uploaded', None), ('source_bytes_modified', 'false')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                handoff.sanitize_report({**value, key: bad})
        for key in ('target_account', 'manifest_sha256', 'raw_data_uploaded'):
            missing = dict(value); missing.pop(key)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                handoff.sanitize_report(missing)

    def test_libacl_absence_blocks_instead_of_installing(self):
        with patch.object(ctypes, 'CDLL', side_effect=OSError('not installed')):
            with self.assertRaisesRegex(handoff.Refusal, 'libacl_unavailable'):
                handoff.LibACL()

    def test_fixed_manifest_scope_and_canonical_pin(self):
        manifest = handoff.read_manifest()
        self.assertEqual(hashlib.sha256(handoff.canonical(manifest)).hexdigest(), handoff.MANIFEST_SHA)
        rows = handoff.selected_artifacts(manifest)
        self.assertEqual(len(rows), 50)
        observed = handoff.read_scope_plan(manifest)
        self.assertEqual(set(observed), {(s['id'], a['name']) for s, a in rows})
        self.assertEqual(len({s['id'] for s, _ in rows}), 6)
        changed = copy.deepcopy(manifest)
        next(s for s in changed['sources'] if s['production_enabled'])['artifacts'].pop()
        with self.assertRaisesRegex(handoff.Refusal, 'scope_mismatch'):
            handoff.selected_artifacts(changed)

    def test_actor_must_existing_nonroot_dedicated_account(self):
        account = SimpleNamespace(pw_uid=1111, pw_gid=1111)
        target = SimpleNamespace(pw_uid=2222, pw_gid=2222)
        with patch.object(handoff.pwd, 'getpwnam', side_effect=[account, target]), patch.object(handoff.os, 'getuid', return_value=0), patch.object(handoff.os, 'geteuid', return_value=0):
            with self.assertRaisesRegex(handoff.Refusal, 'wrong_actor'):
                handoff.resolve_accounts()

    def test_default_cli_is_nonmutating_plan(self):
        account = SimpleNamespace(pw_uid=1111, pw_gid=1111)
        target = SimpleNamespace(pw_uid=2222, pw_gid=2222)
        plan = {'held': [], 'entries': [], 'source_bytes': handoff.EXPECTED_BYTES}
        with patch.object(handoff, 'resolve_accounts', return_value=(account, target, set())), \
                patch.object(handoff, 'LibACL'), patch.object(handoff, 'read_manifest', return_value={}), \
                patch.object(handoff, 'make_plan', return_value=plan), patch.object(handoff, 'prepare_state') as write_state, \
                patch.object(handoff, 'apply_plan') as apply, patch.object(handoff, 'atomic_private') as write, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = handoff.main([])
        self.assertEqual(code, 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value['status'], 'planned')
        self.assertEqual(value['mode'], 'plan')
        write_state.assert_not_called(); apply.assert_not_called(); write.assert_not_called()

    def test_actual_system_libacl_read_is_valid_on_synthetic_temp_only(self):
        try:
            handoff.LibACL()
        except handoff.Refusal:
            self.skipTest('no existing libacl')
        with tempfile.TemporaryDirectory(prefix='acl-read-fixture-') as directory:
            path = Path(directory) / 'synthetic'
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            try:
                try:
                    result = handoff.LibACL().get(fd)
                except handoff.Refusal:
                    if ctypes.get_errno() == errno.ENOTSUP:
                        self.skipTest('fixture filesystem does not support POSIX ACLs')
                    raise
                self.assertEqual(result, acl())
            finally:
                os.close(fd)

    def test_libacl_load_does_not_spawn_lookup_commands(self):
        import subprocess
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('external lookup')):
            try:
                handoff.LibACL()
            except handoff.Refusal:
                self.skipTest('no existing libacl')

    def test_libacl_native_numeric_qualifier_roundtrip_without_filesystem_write(self):
        try:
            backend = handoff.LibACL()
        except handoff.Refusal:
            self.skipTest('no existing libacl')
        for original in (acl(), {**acl(), (handoff.MASK, None): 5,
                (handoff.USER, 2222): 4, (handoff.GROUP, 3333): 1},
                {**acl(), (handoff.MASK, None): 5, (handoff.USER, 4294967294): 4,
                 (handoff.GROUP, 4294967293): 1}):
            with patch.object(backend.lib, 'acl_get_fd', side_effect=lambda unused: backend.lib.acl_from_text(handoff.acl_text(original).encode())):
                self.assertEqual(backend.get(-1), original)

    def test_full_ctime_guard_detects_same_size_mtime_restored_edit(self):
        with tempfile.TemporaryDirectory(prefix='acl-ctime-fixture-') as directory:
            path = Path(directory) / 'fixture'
            path.write_bytes(b'public!')
            fd = handoff.hold_path(path)
            try:
                before = os.fstat(fd)
                entry = {'fd': fd, 'path': str(path), 'directory': False, 'nlink': 1,
                    'identity': handoff.data_identity(before), 'expected_signature': handoff.signature(before),
                    'owner_uid': before.st_uid, 'owner_gid': before.st_gid}
                self.assertTrue(handoff.unchanged_data(entry))
                path.write_bytes(b'secret!')
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                after = os.fstat(fd)
                self.assertEqual(handoff.data_identity(after), entry['identity'])
                # Native filesystems may report both writes in one ctime tick.
                # Explicit observations test the guard without assuming a clock
                # transition, skipping coverage, or weakening production checks.
                fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns',
                          'st_ctime_ns', 'st_uid', 'st_gid', 'st_nlink')
                for ctime, expected in ((before.st_ctime_ns, True),
                                        (before.st_ctime_ns + 1, False)):
                    observed = SimpleNamespace(**{name: getattr(before, name) for name in fields})
                    observed.st_ctime_ns = ctime
                    self.assertEqual(handoff.data_identity(observed), entry['identity'])
                    with patch.object(handoff.os, 'fstat', return_value=observed), \
                            patch.object(handoff, 'path_stat', return_value=observed):
                        self.assertIs(handoff.unchanged_data(entry), expected)
                # Real held-file bytes must still reject a same-size/mtime edit,
                # even when coarse metadata alone cannot distinguish that edit.
                with self.assertRaisesRegex(handoff.Refusal, 'checksum_mismatch'):
                    handoff.verify_bytes(fd, {'bytes': 7,
                        'sha256': hashlib.sha256(b'public!').hexdigest()}, time.monotonic() + 5)
            finally:
                os.close(fd)

    def test_symlink_parent_or_leaf_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='acl-path-fixture-') as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'real' / 'source').write_bytes(b'fixture')
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaises(OSError):
                handoff.hold_path(root / 'link' / 'source')
            (root / 'leaf').symlink_to(root / 'real' / 'source')
            with self.assertRaises(OSError):
                handoff.hold_path(root / 'leaf')


class ScopePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='acl-scope-fixture-')
        self.root = Path(self.tmp.name) / 'outputs' / 'batch' / 'source-cache'
        self.root.mkdir(parents=True)
        for path in (self.root, self.root.parent, self.root.parent.parent):
            path.chmod(0o700)
        self.manifest = handoff.read_manifest()
        self.total = 0
        self.observed_hashes = {}
        self.paths = []
        for source, artifact in handoff.selected_artifacts(self.manifest):
            directory = self.root / source['id']
            directory.mkdir(exist_ok=True, mode=0o700)
            path = directory / artifact['name']
            raw = ('generated fixture ' + source['id'] + artifact['name']).encode()
            artifact['expected_bytes'] = len(raw)
            artifact['max_bytes'] = len(raw)
            digest = hashlib.sha256(raw).hexdigest()
            self.observed_hashes[(source['id'], artifact['name'])] = digest
            if artifact.get('sha256'):
                artifact['sha256'] = digest
            receipt = {'schema': 'offmenu-source-fetch/1', 'source_id': source['id'],
                'artifact': artifact['name'], 'artifact_key': hashlib.sha256(handoff.canonical({
                    'source': source['id'], 'revision': source['revision'], 'artifact': artifact})).hexdigest(),
                'source_revision': source['revision'], 'origin_url': artifact['url'],
                'license': source['license'], 'license_evidence': source['license_evidence'],
                'attribution': source['attribution'], 'license_scope_note': source.get('license_scope_note'),
                'artifact_metadata_evidence': source.get('artifact_metadata_evidence'),
                'catalog_resource_id': artifact.get('resource_id'),
                'artifact_license_evidence': artifact.get('license_evidence'),
                'transport_integrity': artifact.get('transport_integrity', 'https'),
                'acquisition_only': True, 'ingested': False, 'raw_data_uploaded': False,
                'status': 'complete', 'bytes': len(raw), 'sha256': digest,
                'expected_bytes': artifact['expected_bytes'], 'expected_sha256': artifact.get('sha256'),
                'checksum_basis': 'publisher_sha256_verified' if artifact.get('sha256') else 'locally_observed_not_publisher_authenticated'}
            path.write_bytes(raw); path.chmod(0o600)
            receipt_path = Path(str(path) + '.receipt.json')
            receipt_path.write_text(json.dumps(receipt)); receipt_path.chmod(0o600)
            self.paths.extend((path, receipt_path))
            self.total += len(raw)
        info = self.root.stat()
        self.actor = SimpleNamespace(pw_uid=info.st_uid, pw_gid=info.st_gid)
        self.target = SimpleNamespace(pw_uid=info.st_uid + 100000, pw_gid=info.st_gid + 100000)
        class ModeACL:
            def get(self, fd):
                # Simulate existing ACLs from actual fixture mode bits only.
                mode = os.fstat(fd).st_mode
                return acl((mode >> 6) & 7, (mode >> 3) & 7, mode & 7)
        self.backend = ModeACL()

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, denied_ancestor=None):
        # Model already-authorized traversal of every out-of-scope ancestor,
        # including private runner TMPDIR parents. Never chmod actual ancestors,
        # and never override access checks on selected nodes or sibling children.
        ancestors = {(info.st_dev, info.st_ino)
            for path in self.root.parent.parent.parents for info in (path.stat(),)}
        denied = None
        if denied_ancestor is not None:
            info = Path(denied_ancestor).stat()
            denied = (info.st_dev, info.st_ino)
            self.assertIn(denied, ancestors)
        real_access = handoff.target_access
        def access(original, info, uid, groups):
            identity = (info.st_dev, info.st_ino)
            if identity in ancestors:
                return 0 if identity == denied else 1
            return real_access(original, info, uid, groups)
        with patch.object(handoff, 'EXPECTED_BYTES', self.total), patch.object(handoff, 'target_access', side_effect=access):
            return handoff.make_plan(self.manifest, self.actor, self.target, {self.target.pw_gid}, self.backend, self.root, observed_hashes=self.observed_hashes)

    def test_fixture_under_private_tmpdir_parent_models_only_outside_traversal(self):
        private_parent = Path(self.tmp.name) / 'private-runner-tmpdir'
        private_parent.mkdir(mode=0o700)
        before = private_parent.stat().st_mode
        old_root = self.root
        old_root.parent.parent.rename(private_parent / 'outputs')
        self.root = private_parent / 'outputs' / 'batch' / 'source-cache'
        self.paths = [self.root / path.relative_to(old_root) for path in self.paths]
        plan = self.plan()
        try:
            self.assertEqual(len(plan['entries']), 109)
            self.assertEqual({Path(entry['path']) for entry in plan['entries'] if entry['directory']},
                {self.root.parent.parent, self.root.parent, self.root}
                | {self.root / sid for sid in handoff.FAMILY_COUNTS})
        finally:
            for fd in plan['held']: os.close(fd)
        self.assertEqual(private_parent.stat().st_mode, before)

    def test_production_guard_refuses_one_unauthorized_outside_ancestor_without_writes(self):
        # All other outside ancestors are modeled traversable; only this private
        # generated directory is denied. The actual production guard must refuse.
        with patch.object(self.backend, 'set', create=True) as write:
            with self.assertRaisesRegex(handoff.Refusal, 'outside_ancestor_not_traversable'):
                self.plan(denied_ancestor=self.tmp.name)
            write.assert_not_called()

    def test_closed_50_plus_50_plus_9_scope_is_verified_readonly(self):
        before = {path: (path.read_bytes(), path.stat().st_mode) for path in self.paths}
        plan = self.plan()
        try:
            self.assertEqual(len(plan['entries']), 109)
            self.assertEqual(sum(e['directory'] for e in plan['entries']), 9)
            self.assertEqual(plan['source_bytes'], self.total)
            self.assertEqual(set(Path(e['path']) for e in plan['entries'] if not e['directory']), set(self.paths))
            self.assertTrue(all(e['desired'][(handoff.USER, self.target.pw_uid)] == (1 if e['directory'] else 4) for e in plan['entries']))
        finally:
            for fd in plan['held']: os.close(fd)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mode) for path in self.paths})

    def test_hardlinked_artifact_blocks_before_any_acl_write(self):
        os.link(self.paths[0], self.root / 'unselected-alias')
        with self.assertRaisesRegex(handoff.Refusal, 'unexpected_hardlink'):
            self.plan()

    def test_opaque_extra_receipt_payload_is_not_shared(self):
        receipt = json.loads(self.paths[1].read_text())
        receipt['unreviewed_private_data'] = 'not shareable'
        self.paths[1].write_text(json.dumps(receipt))
        with self.assertRaisesRegex(handoff.Refusal, 'receipt_schema_unreviewed'):
            self.plan()

    def test_edited_source_and_receipt_cannot_replace_pinned_acquired_bytes(self):
        target = next(p for p in self.paths if p.suffix == '.html')
        replacement = b'x' * len(target.read_bytes())
        target.write_bytes(replacement)
        receipt_path = Path(str(target) + '.receipt.json')
        receipt = json.loads(receipt_path.read_text())
        receipt['sha256'] = hashlib.sha256(replacement).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(handoff.Refusal, 'checksum_mismatch'):
            self.plan()

    def test_new_traversal_cannot_expose_unselected_readable_sibling(self):
        sibling = self.root.parent.parent / 'unselected'
        sibling.write_bytes(b'not in approved cohort')
        sibling.chmod(0o644)
        with self.assertRaisesRegex(handoff.Refusal, 'unlisted_sibling_exposure'):
            self.plan()

    def test_unselected_private_sibling_is_metadata_checked_without_body_read(self):
        sibling = self.root.parent.parent / 'private-unselected'
        sibling.write_bytes(b'private fixture never read')
        sibling.chmod(0o600)
        inode = sibling.stat().st_ino
        real_read = os.read
        def guard(fd, count):
            if os.fstat(fd).st_ino == inode:
                raise AssertionError('unselected sibling payload read')
            return real_read(fd, count)
        with patch.object(handoff.os, 'read', side_effect=guard):
            plan = self.plan()
        for fd in plan['held']: os.close(fd)

    def test_unselected_traversable_directory_blocks_without_recursion(self):
        sibling = self.root.parent.parent / 'unselected-directory'
        sibling.mkdir(mode=0o700)
        # Materialize this generated fixture's intended ACL-visible mode even
        # under the runner service umask 0077; no existing ancestor is changed.
        sibling.chmod(0o701)
        self.assertEqual(sibling.stat().st_mode & 0o777, 0o701)
        with self.assertRaisesRegex(handoff.Refusal, 'unlisted_sibling_exposure'):
            self.plan()

    def test_unselected_symlink_is_conservatively_refused(self):
        (self.root.parent.parent / 'unselected-link').symlink_to('/tmp')
        with self.assertRaisesRegex(handoff.Refusal, 'unlisted_sibling_exposure'):
            self.plan()

    def test_changed_cache_digest_blocks_before_grant(self):
        original = self.paths[0].read_bytes()
        self.paths[0].write_bytes(b'x' * len(original))
        with self.assertRaisesRegex(handoff.Refusal, 'checksum_mismatch'):
            self.plan()


if __name__ == '__main__':
    unittest.main()
