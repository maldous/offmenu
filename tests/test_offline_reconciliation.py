import contextlib
import errno
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

probe = load('offline_reconciliation_test', ROOT / 'scripts/offline-reconciliation.py')
jobs = load('offline_reconciliation_dispatcher_test', ROOT / 'scripts/dispatch-foo-job.py')

class ReconciliationTests(unittest.TestCase):
    def target(self, root, name='metadata.json', kind='json'):
        return ('fixture', str(root / name), kind)

    def test_request_remains_exact_three_fields(self):
        request = {'schemaVersion': 1, 'jobId': 'reconcile-test-001', 'profile': 'offline-reconciliation'}
        self.assertEqual(jobs.parse_request(json.dumps(request).encode()), request)
        for extra in ({'path': '/etc/shadow'}, {'command': 'sh'}, {'readRoot': '/'}):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(json.dumps(request | extra).encode())

    def test_profile_is_fixed_serial_and_no_mutating_commands(self):
        steps = jobs.profile_steps('offline-reconciliation', ROOT, 'a' * 40)
        self.assertEqual([s[0] for s in steps], ['readiness', 'reconciliation-tests', *probe.MODES])
        for step, deps, command in steps[2:]:
            self.assertEqual(deps, ['readiness', 'reconciliation-tests'])
            self.assertEqual(command[1:], ['-B', 'scripts/offline-reconciliation.py', '--mode', step])
        self.assertNotIn('offline-replay', [s[0] for s in steps])

    def test_unregistered_paths_are_unknown_without_any_filesystem_reads(self):
        with patch.object(probe, '_open_exact') as opening:
            for mode in ('source-claims',):
                report = probe.collect(mode)
                self.assertEqual(report['status'], 'blocked')
                self.assertFalse(report['metadataRegistrationComplete'])
                self.assertFalse(report['safeToAcquireEstablished'])
        opening.assert_not_called()

    def test_metadata_projection_never_echoes_raw_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = self.target(root)
            (root / 'metadata.json').write_text(json.dumps({'secret': 'ghp_NEVER_PUBLISH',
                'claims': [{'status': 'active', 'owner': 'worker57', 'reservedBytes': 4096,
                            'token': 'private'}, {'status': 'pending', 'owner': 49}],
                'journalSequence': 8822, 'updatedAt': '2026-10-18T12:00:00Z'}))
            out = probe.observe_file(target)
            self.assertEqual(out['access'], 'observed')
            self.assertTrue(out['wholeFileObserved'])
            summary = out['summary']
            self.assertEqual(summary['statusFieldCounts'], {'active': 1, 'pending': 1})
            self.assertEqual(summary['ownerFieldCounts'], {'57': 1, '49': 1})
            self.assertEqual(summary['reservationFieldByteSums'], {'reservedBytes': 4096})
            self.assertEqual(summary['maximumSequenceObserved'], 8822)
            self.assertNotIn('private', json.dumps(out))
            self.assertNotIn('ghp_', json.dumps(out))

    def test_file_contents_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'metadata.json'
            before = b'{"status":"pending"}'
            path.write_bytes(before)
            probe.observe_file(self.target(root))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(root.iterdir()), [path])

    def test_metadata_only_does_not_read_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'metadata.json').write_bytes(b'SECRET BODY')
            with patch.object(probe.os, 'read', side_effect=AssertionError('body read')):
                out = probe.observe_file(self.target(root, kind='metadata-only'))
            self.assertEqual(out['access'], 'observed')
            self.assertEqual(out['metadataBytesRead'], 0)
            self.assertIsNone(out['summary'])

    def test_missing_and_permission_errors_preserve_exact_registered_path(self):
        target = ('known', '/exact/registered/file.json', 'json')
        for error, expected in ((errno.ENOENT, 'missing'), (errno.EACCES, 'permission-denied')):
            with patch.object(probe, '_open_exact', side_effect=OSError(error, 'private detail must not leak')):
                out = probe.observe_file(target)
            self.assertEqual(out['access'], expected)
            self.assertEqual(out['path'], target[1])
            self.assertNotIn('private detail', json.dumps(out))
            self.assertIsNone(out['summary'])

    def test_symlink_leaf_and_ancestor_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / 'real'
            real.mkdir()
            (real / 'data.json').write_text('{}')
            (root / 'link').symlink_to(real, target_is_directory=True)
            (root / 'leaf').symlink_to(real / 'data.json')
            for path in (root / 'leaf', root / 'link/data.json'):
                self.assertEqual(probe.observe_file(('fixture', str(path), 'json'))['access'], 'symlink-forbidden')

    def test_special_file_is_not_consumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.mkfifo(root / 'metadata.json')
            out = probe.observe_file(self.target(root))
            self.assertEqual(out['access'], 'not-regular-file')
            self.assertEqual(out['metadataBytesRead'], 0)

    def test_oversize_json_is_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'metadata.json').write_bytes(b' ' * 100)
            with patch.object(probe, 'MAX_BYTES', 99), patch.object(probe.os, 'read') as reading:
                out = probe.observe_file(self.target(root))
            self.assertEqual(out['access'], 'size-limit')
            reading.assert_not_called()

    def test_bounded_jsonl_tail_is_explicit_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'events.jsonl').write_text(''.join(json.dumps({'sequence': n}) + '\n' for n in range(200)))
            with patch.object(probe, 'MAX_BYTES', 256), patch.object(probe, 'MAX_ROWS', 5):
                out = probe.observe_file(self.target(root, 'events.jsonl', 'jsonl-tail'))
            self.assertEqual(out['access'], 'observed')
            self.assertFalse(out['wholeFileObserved'])
            self.assertEqual(out['summary']['recordsParsed'], 5)
            self.assertEqual(out['summary']['maximumSequenceObserved'], 199)
            self.assertLessEqual(out['metadataBytesRead'], 256)

    def test_row_limit_without_byte_limit_is_still_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'events.jsonl').write_text('{}\n' * 6)
            with patch.object(probe, 'MAX_ROWS', 5):
                out = probe.observe_file(self.target(root, 'events.jsonl', 'jsonl-tail'))
            self.assertFalse(out['wholeFileObserved'])

    def test_invalid_duplicate_nonfinite_metadata_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for raw in ('{"status":"pending","status":"active"}', '{"x":NaN}', 'private not json'):
                (root / 'metadata.json').write_text(raw)
                out = probe.observe_file(self.target(root))
                self.assertEqual(out['access'], 'invalid-metadata')
                self.assertIsNone(out['summary'])
                self.assertNotIn('private not json', json.dumps(out))

    def test_node_limit_fails_closed(self):
        with patch.object(probe, 'MAX_NODES', 2), self.assertRaises(ValueError):
            probe.summarize([{'a': [[], []]}])

    def test_changing_file_is_not_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'metadata.json'
            path.write_text('{}')
            original = probe.os.read
            def mutate(fd, size):
                result = original(fd, size)
                path.write_text('{"status":"active"}')
                return result
            with patch.object(probe.os, 'read', side_effect=mutate):
                out = probe.observe_file(self.target(root))
            self.assertEqual(out['access'], 'changed-during-read')
            self.assertIsNone(out['summary'])

    def test_space_probe_no_directory_listing_or_file_body_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(probe.os, 'scandir', side_effect=AssertionError('listing')), patch.object(probe.os, 'read', side_effect=AssertionError('body')):
                out = probe.observe_space(('fixture', tmp))
            self.assertEqual(out['access'], 'observed')
            self.assertGreater(out['availableBytes'], 0)

    def test_sanitizer_drops_unknown_keys_and_rejects_path_injection(self):
        report = probe.collect('source-claims')
        report['secret'] = 'NEVER_PUBLISH'
        clean = probe.sanitize_report(report)
        self.assertNotIn('NEVER_PUBLISH', json.dumps(clean))
        report['files'] = [{'path': '/etc/shadow'}]
        with self.assertRaises(ValueError):
            probe.sanitize_report(report)

    def test_sanitizer_rejects_authority_claims_and_boolean_integer_confusion(self):
        for key, value in (('sourceContentsUploaded', True), ('downloads', True), ('safeToAcquireEstablished', True), ('status', 'complete')):
            report = probe.collect('source-claims')
            report[key] = value
            with self.assertRaises(ValueError):
                probe.sanitize_report(report)

    def test_summary_cannot_publish_arbitrary_status_owner_or_key(self):
        for key, item in (('statusFieldCounts', {'ghp_SECRET': 1}), ('ownerFieldCounts', {'secret': 1}), ('listFieldCounts', {'token': 1})):
            summary = probe.summarize([{}])
            summary[key] = item
            with self.assertRaises(ValueError):
                probe.sanitize_summary(summary)

    def test_dispatcher_only_publishes_sanitized_schema(self):
        report = probe.collect('source-claims')
        report['secret'] = 'NEVER_PUBLISH'
        evidence = jobs.safe_evidence(json.dumps(report).encode())
        self.assertEqual(evidence['offlineReconciliation']['mode'], 'source-claims')
        self.assertNotIn('NEVER_PUBLISH', json.dumps(evidence))

    def test_blocked_probe_does_not_skip_remaining_independent_probes(self):
        seen = []
        def child(command, code, timeout=240):
            if '--mode' in command:
                mode = command[-1]
                seen.append(mode)
                return {'status': 'failed', 'exitCode': 2, 'durationSeconds': 0,
                        'evidence': {'offlineReconciliation': {'mode': mode, 'status': 'blocked'}}}
            return {'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {}}
        with patch.object(jobs, 'run_child', side_effect=child):
            report = jobs.run_profile({'jobId': 'reconcile-test-001', 'profile': 'offline-reconciliation'}, 'a'*40, ROOT, '1', '1')
        self.assertEqual(seen, list(probe.MODES))
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual([s['exitCode'] for s in report['steps']], [0, 0, 2, 2, 2, 2, 2])
        self.assertFalse(report['safeToAcquireEstablished'])

    def test_cli_returns_two_for_unknown_scope_and_no_unreviewed_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(probe.main(['--mode', 'source-claims']), 2)
        self.assertEqual(json.loads(out.getvalue())['reason'], 'unregistered-metadata-paths')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            probe.main(['--mode', 'source-claims', '--path', '/etc/shadow'])

if __name__ == '__main__':
    unittest.main()
