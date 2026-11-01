"""UIF-133: fixed identity-stage command, source custody and Journal identities."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import stokowski_operations as operations


class IdentityProfileTests(unittest.TestCase):
    def spec(self, **changes):
        output = {'tests/edge/handler-auth-dispatch.test.mjs': 'a' * 64}
        spec = dict(version=3, issue='UIF-96',
            issue_id='c82fda68-a594-4855-8b68-7e220f7fa517', stage='validate',
            owner='synthetic-owner', branch='bugfix/synthetic-identity', head='b' * 40,
            base='c' * 40, policy_sha256='d' * 64, acceptance_sha256='e' * 64,
            runner_sha256='f' * 64, executor_sha256='1' * 64, control_sha256='2' * 64,
            profile='identity-client-focused', outputs=output,
            workspace='/offmenu/data/.offmenu-platform/workspaces/synthetic-identity',
            local_source_root='/synthetic/candidate',
            execution=dict(task_fit='deterministic reviewed source validation',
                requested_model=None, requested_effort=None, provider_route='none',
                resolved_model=None, resolution_status='not-applicable'),
            origin=dict(kind='reviewed-source-v1', admission_sha256='e' * 64,
                review_sha256='3' * 64, author='synthetic-author', authors=['synthetic-author'],
                provenance=[dict(path='/synthetic/native-receipt.json', sha256='4' * 64,
                    author='synthetic-author', owner='synthetic-author', session='original-session',
                    source_head='5' * 40, contribution_head='6' * 40, outputs=output,
                    path_mapping={name: name for name in output}, derivation=None)]))
        return dict(spec, **changes)

    def test_fixed_profile_argv_resources_and_no_candidate_selectors(self):
        spec = self.spec()
        operations.validated(spec)
        args = operations.bridge_arguments(spec)
        self.assertEqual(operations.IDENTITY_COMMAND, ('/bin/node', '--test',
            '--test-isolation=none', '--test-reporter=tap',
            'tests/web/offmenu-identity-client.test.mjs',
            'tests/edge/handler-auth-dispatch.test.mjs'))
        self.assertEqual(shlex.split(args['command'])[:2], ['/offmenu/.venv-delivery/bin/python', '-c'])
        self.assertEqual(args['mode'], 'read')
        self.assertEqual(args['timeout_seconds'], 180)
        self.assertEqual(args['resources'], operations.bridge_arguments(
            dict(spec, profile='current-journal-focused'))['resources'])
        for extra in ({'argv': ['other']}, {'environment': {'HOME': '/real-home'}},
                      {'test_selectors': ['other']}, {'profile': 'identity-client-focused.other'}):
            with self.subTest(extra=extra), self.assertRaises(operations.OperationError):
                operations.validated(dict(spec, **extra))

    def candidate(self, directory):
        root = Path(directory) / 'candidate'
        root.mkdir()
        def git(*args):
            return subprocess.check_output(['/usr/bin/git', '-C', str(root),
                '-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
                *args], stderr=subprocess.PIPE).decode().strip()
        git('init', '-b', 'bugfix/synthetic-identity')
        for name in operations.IDENTITY_TESTS:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('// synthetic baseline\n')
        git('add', '.'); git('commit', '-m', 'base')
        base = git('rev-parse', 'HEAD')
        target = root / operations.IDENTITY_TESTS[1]
        target.write_text('// synthetic accepted contribution\n')
        git('add', '.'); git('commit', '-m', 'contribution')
        head = git('rev-parse', 'HEAD')
        output = {operations.IDENTITY_TESTS[1]: hashlib.sha256(target.read_bytes()).hexdigest()}
        archive = subprocess.check_output(['/usr/bin/git', '-C', str(root), 'archive',
            base, *operations.IDENTITY_TESTS])
        spec = self.spec(base=base, head=head, outputs=output,
                         local_source_root=str(root), control_sha256=hashlib.sha256(archive).hexdigest())
        spec['origin']['provenance'][0].update(source_head=base, contribution_head=head,
            outputs=output, path_mapping={name: name for name in output})
        return root, spec

    def run_validator(self, root, spec, *, counts=None, exit_code=0, mutation=None):
        counts = counts or dict(tests=14, suites=0, **{'pass': 14}, fail=0,
                                cancelled=0, skipped=0, todo=0)
        tap = 'TAP version 13\n' + ''.join(f'# {key} {value}\n' for key, value in counts.items())
        actual_run = subprocess.run
        caches = []
        def run(argv, **kwargs):
            if argv[0] != '/bin/node':
                return actual_run(argv, **kwargs)
            self.assertEqual(argv, operations.IDENTITY_COMMAND)
            self.assertEqual(kwargs['cwd'], root)
            self.assertEqual(kwargs['timeout'], 150)
            env = kwargs['env']
            self.assertNotIn('CLOUDFLARE_API_TOKEN', env)
            self.assertNotIn('NODE_OPTIONS', env)
            self.assertEqual(env['CLOUDFLARE_CF_FETCH_ENABLED'], 'false')
            self.assertEqual(env['WRANGLER_SEND_METRICS'], 'false')
            cache = Path(env['MINIFLARE_CACHE_DIR'])
            self.assertFalse(cache.is_relative_to(root))
            self.assertEqual(Path(env['HOME']), cache.parent)
            cache.mkdir(); (cache / 'cf.json').write_text('{"synthetic":true}')
            caches.append(cache)
            if mutation:
                mutation()
            return subprocess.CompletedProcess(argv, exit_code, stdout=tap, stderr='')
        try:
            with patch('subprocess.run', side_effect=run), \
                 patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'synthetic-not-forwarded',
                                         'NODE_OPTIONS': '--synthetic-not-forwarded'}), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exec(compile(operations.identity_validation_code(spec, root),
                             '<synthetic-identity-validator>', 'exec'), {})
        finally:
            self.assertTrue(all(not cache.exists() for cache in caches))

    def test_real_source_oracles_and_scratch_keep_candidate_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec = self.candidate(directory)
            self.run_validator(root, spec)
            self.assertFalse((root / '.wrangler').exists())
            self.assertEqual(subprocess.check_output(['/usr/bin/git', '-C', str(root),
                'status', '--porcelain']), b'')

    def test_failed_or_skipped_or_missing_summary_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec = self.candidate(directory)
            cases = [dict(exit_code=1),
                     dict(counts=dict(tests=14, suites=0, **{'pass': 13}, fail=0,
                                      cancelled=0, skipped=1, todo=0)),
                     dict(counts={'tests': 14})]
            for case in cases:
                with self.subTest(case=case), self.assertRaises(AssertionError):
                    self.run_validator(root, spec, **case)

    def test_after_oracle_runs_even_when_node_fails_and_rejects_untracked_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec = self.candidate(directory)
            def dirty():
                cache = root / '.wrangler/cache'
                cache.mkdir(parents=True); (cache / 'cf.json').write_text('untracked')
            with self.assertRaisesRegex(AssertionError, 'dirty source'):
                self.run_validator(root, spec, exit_code=1, mutation=dirty)

    def test_source_and_control_drift_refuse_before_node(self):
        with tempfile.TemporaryDirectory() as directory:
            root, spec = self.candidate(directory)
            with self.assertRaisesRegex(AssertionError, 'control source drift'):
                self.run_validator(root, dict(spec, control_sha256='0' * 64))
            (root / operations.IDENTITY_TESTS[1]).write_text('changed after review')
            with self.assertRaisesRegex(AssertionError, 'dirty source'):
                self.run_validator(root, spec)

    def test_profile_and_executor_identity_survive_journal_reopen_without_reprepare(self):
        spec = self.spec()
        with tempfile.TemporaryDirectory() as directory:
            journal = operations.Journal(Path(directory) / 'operations')
            key = journal.prepare(spec)
            _, first = journal.read(key)
            journal.cancel(key)
            reopened = operations.Journal(journal.root)
            self.assertEqual(reopened.prepare(spec), key)
            self.assertTrue(reopened.read(key)[1]['cancel_requested'])
            self.assertEqual(reopened.read(key)[1]['windmill_job_id'], first['windmill_job_id'])
            self.assertNotEqual(key, operations.operation_key(dict(spec, executor_sha256='9' * 64)))
            self.assertNotEqual(key, operations.operation_key(dict(spec, profile='current-journal-focused')))
            with reopened.db() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM operations').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM events WHERE event='prepared'").fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
