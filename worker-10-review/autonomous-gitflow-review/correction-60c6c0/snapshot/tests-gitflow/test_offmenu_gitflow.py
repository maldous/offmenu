"""Small disposable repositories; no operations on OffMenu's actual refs."""
import hashlib
import fcntl
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/offmenu-gitflow.py'
spec = importlib.util.spec_from_file_location('gitflow', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'origin.git'
        self.repo = self.root / 'worker-09'
        self.ev = self.root / 'receipts'
        self.ev.mkdir()
        self.policy_path = self.root / 'policy.json'
        self.run_git(self.root, 'init', '--bare', str(self.remote))
        self.run_git(self.root, 'clone', str(self.remote), str(self.repo))
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.git('switch', '-c', 'main')
        (self.repo / 'sample').write_text('baseline\n')
        self.git('add', 'sample')
        self.git('commit', '-m', 'synthetic accepted baseline')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.git('tag', '-a', 'v1.0.0', '-m', 'synthetic baseline')
        self.git('branch', 'develop')
        self.git('push', 'origin', 'main', 'develop', 'v1.0.0')
        self.proof = self.root / 'morgan.txt'
        self.proof.write_text('Synthetic Morgan approval fixture. Not a real release.\n')
        self.policy = {
            'schema': 'offmenu-gitflow-policy/1', 'pool_limit': 32, 'evidence_dir': str(self.ev),
            'common_dir': str((self.repo / '.git').resolve()), 'origin': str(self.remote),
            'baseline': dict(self.verdict(sha=self.base), tag='v1.0.0', tag_object=self.git('rev-parse', 'v1.0.0').strip()),
            'released_main': dict(self.verdict(sha=self.base), tag='v1.0.0', tag_object=self.git('rev-parse', 'v1.0.0').strip()),
            'lines': {line: self.verdict(sha=self.base, line=line) for line in ('main', 'develop')},
            'workers': {'9': {'path': str(self.repo), 'owner': 'fixture-worker09', 'custody': 'clear',
                              'evidence': self.reference(), 'active_task': None, 'open_prs': [],
                              'recovery_dependencies': [], 'evidence_dependencies': []}},
            'base_exceptions': {str(i): {'status': 'preserved transition exception'} for i in range(1, 9)},
            'reviews': [], 'reconciliations': [], 'develop_initialized': True,
        }
        self.write_policy()

    def run_git(self, cwd, *args):
        p = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, env=m.git_environment())
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def git(self, *args):
        return self.run_git(self.repo, *args)

    def reference(self):
        return {'path': str(self.proof), 'sha256': hashlib.sha256(self.proof.read_bytes()).hexdigest()}

    def verdict(self, **kwargs):
        return dict(reviewer='Morgan', verdict='accepted', qualification='qualified', utc=m.utc(),
                    evidence=self.reference(), **kwargs)

    def write_policy(self):
        self.policy_path.write_text(json.dumps(self.policy))

    def command(self, *args, ok=True):
        self.write_policy()
        p = subprocess.run(['python3', '-B', str(SCRIPT), '--repo', str(self.repo),
                            '--policy', str(self.policy_path), '--evidence-dir', str(self.ev),
                            *args], capture_output=True, text=True, env=m.git_environment())
        self.assertEqual(p.returncode, 0 if ok else 2, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        receipt = json.loads(Path(out['receipt']).read_text()) if 'receipt' in out else out
        return out, receipt

    def start(self, kind='feature', task='fixture', check=False, ok=True):
        args = ['start', '--worker', '9', '--kind', kind, '--task', task]
        if check:
            args.append('--check-only')
        return self.command(*args, ok=ok)

    def commit(self, content='feature'):
        (self.repo / 'sample').write_text(content + '\n')
        self.git('add', 'sample')
        self.git('commit', '-m', content)
        return self.git('rev-parse', 'HEAD').strip()

    def ready(self, start):
        checks = self.root / 'checks.json'
        checks.write_text(json.dumps(self.reference()))
        return self.command('ready', '--worker', '9', '--start', start['receipt'], '--checks', str(checks))

    def review(self, line, candidate, source, base=None):
        self.policy['reviews'].append(self.verdict(operation='integrate-' + line, candidate=candidate,
                                                   source=source, base=base or self.base))

    def delivery_fixture(self):
        self.git('switch', '-c', 'feature/delivery')
        head = self.commit('reviewed delivery')
        self.git('push', 'origin', 'feature/delivery')
        self.policy['routine_delivery'] = {'authorizer': 'Matt', 'project': 'OffMenu',
            'scope': 'normal-qualified-gitflow', 'evidence': self.reference()}
        self.policy['reviews'] = [self.verdict(operation='deliver-develop', candidate=head, base=self.base, source=head)]
        snapshot = {'state': 'open', 'base_ref': 'develop', 'head_ref': 'feature/delivery', 'head': head, 'base': self.base,
            'owner': 'worker09', 'url': 'https://example.invalid/fixture/pr',
            'independent_review': {'state': 'passed', 'reviewer': 'worker13', 'head': head,
                                   'base': self.base, 'evidence': self.reference()},
            'requirements_status': 'known', 'required_reviews': [], 'required_checks': [], 'security_alerts': [],
            'advisory_reviews': [{'state': 'pending', 'open_findings': 0, 'reviewer': 'codex'}],
            'platform_confirmation': {'state': 'confirmed', 'head': head, 'base': self.base,
                                      'evidence': self.reference()}}
        return head, snapshot

    def delivery_command(self, head, snapshot, ok=True):
        path = self.root / 'snapshot.json';path.write_text(json.dumps(snapshot))
        return self.command('delivery', '--worker', '9', '--snapshot', str(path),
                            '--head', head, '--base', self.base, ok=ok)

    def test_routine_delivery_advisory_pending_disclosed_not_approval(self):
        head, snapshot = self.delivery_fixture()
        _, r = self.delivery_command(head, snapshot)
        self.assertEqual(r['status'], 'allowed')
        self.assertEqual(r['advisory_disclosures'][0]['state'], 'pending')
        self.assertIn('no PR creation/push/merge', r['meaning'])
        self.assertEqual(self.git('rev-parse', 'origin/develop').strip(), self.base)

    def test_routine_delivery_required_pending_and_unknown_requirements_block(self):
        head, snapshot = self.delivery_fixture()
        snapshot['required_reviews'] = [{'head': head, 'state': 'PENDING'}]
        _, r = self.delivery_command(head, snapshot, ok=False)
        self.assertIn('required review', r['error'])
        snapshot['required_reviews'] = []
        snapshot['required_checks'] = [{'head': head, 'status': 'in_progress', 'conclusion': None}]
        self.delivery_command(head, snapshot, ok=False)
        snapshot['required_checks'] = []
        snapshot['requirements_status'] = 'unavailable'
        self.delivery_command(head, snapshot, ok=False)

    def test_routine_delivery_stale_review_verdict_confirmation_and_late_finding(self):
        head, snapshot = self.delivery_fixture()
        original = json.loads(json.dumps(snapshot))
        snapshot['independent_review']['head'] = self.base
        self.delivery_command(head, snapshot, ok=False)
        snapshot = json.loads(json.dumps(original));snapshot['platform_confirmation']['state'] = 'pending'
        self.delivery_command(head, snapshot, ok=False)
        snapshot = json.loads(json.dumps(original));snapshot['advisory_reviews'][0]['open_findings'] = 1
        self.delivery_command(head, snapshot, ok=False)
        snapshot = json.loads(json.dumps(original));self.policy['reviews'][0]['candidate'] = self.base
        self.delivery_command(head, snapshot, ok=False)

    def test_explicit_client_enforcement_allows_unavailable_origin_not_pending_required(self):
        head, snapshot = self.delivery_fixture()
        snapshot['requirements_status'] = 'origin-unavailable-client-enforced'
        self.delivery_command(head, snapshot, ok=False)
        self.policy['client_enforcement'] = {'accepted_by': 'Matt', 'origin_protection': 'unavailable',
            'bypassable_outside_workflow': True, 'evidence': self.reference()}
        _, r = self.delivery_command(head, snapshot)
        self.assertFalse(r['origin_protected'])
        snapshot['required_checks'] = [{'head': head, 'status': 'completed', 'conclusion': 'failure'}]
        self.delivery_command(head, snapshot, ok=False)

    def test_malformed_review_and_evidence_fail_closed_with_durable_receipt(self):
        head, snapshot = self.delivery_fixture()
        valid = json.loads(json.dumps(self.policy['reviews']))
        cases = [None, [None], ['wrong'], {}, [dict(valid[0], utc=False)],
                 [dict(valid[0], evidence={'path': 123, 'sha256': []})]]
        for value in cases:
            with self.subTest(reviews=value):
                self.policy['reviews'] = value
                out, r = self.delivery_command(head, snapshot, ok=False)
                self.assertEqual(r['status'], 'blocked')
                self.assertTrue(Path(out['receipt']).is_file())
                self.assertIsNotNone(r.get('error'))
        self.policy['reviews'] = valid
        snapshot['independent_review'] = None
        self.delivery_command(head, snapshot, ok=False)

    def test_launcher_rejects_all_path_abbreviations_equals_and_separator(self):
        launcher = SCRIPT.with_name('offmenu-gitflow-launch.py')
        self.write_policy()
        prefix = ['python3', '-B', str(launcher), '--policy', str(self.policy_path), '--evidence-dir', str(self.ev)]
        for option in ('--r', '--re', '--rep', '--repo', '--w', '--wo', '--wor', '--work', '--worke', '--worker'):
            for form in ([option, str(self.repo)], [option + '=' + str(self.repo)]):
                with self.subTest(form=form):
                    p = subprocess.run(prefix + form + ['start', '--kind', 'feature', '--task', 'override'],
                                       cwd=self.repo, env=m.git_environment(), text=True, capture_output=True)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertIn('binds', p.stderr)
        for option in ('--', '--?'):
            p = subprocess.run(prefix + [option, 'start'], cwd=self.repo, env=m.git_environment(),
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 2)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')
        # Direct helper parsing also rejects abbreviations on every parser.
        p = subprocess.run(['python3', '-B', str(SCRIPT), '--rep', str(self.repo),
                            '--policy', str(self.policy_path), '--evidence-dir', str(self.ev),
                            'start', '--worker', '9', '--kind', 'feature', '--task', 'abbrev'],
                           env=m.git_environment(), text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)

    def normal_retirement_fixture(self):
        start, _ = self.start()
        head = self.commit('normal merged task')
        ready, _ = self.ready(start)
        branch = 'feature/09/fixture'
        self.git('push', 'origin', branch)
        self.policy['routine_delivery'] = {'authorizer': 'Matt', 'project': 'OffMenu',
            'scope': 'normal-qualified-gitflow', 'evidence': self.reference()}
        self.policy['reviews'] = [self.verdict(operation='deliver-develop', candidate=head, base=self.base, source=head)]
        snap = {'state': 'open', 'base_ref': 'develop', 'head_ref': branch, 'head': head, 'base': self.base,
            'owner': 'worker09', 'url': 'https://example.invalid/normal/pr',
            'independent_review': {'state': 'passed', 'reviewer': 'worker13', 'head': head,
                                   'base': self.base, 'evidence': self.reference()},
            'requirements_status': 'known', 'required_reviews': [], 'required_checks': [],
            'advisory_reviews': [], 'security_alerts': [],
            'platform_confirmation': {'state': 'confirmed', 'head': head, 'base': self.base, 'evidence': self.reference()}}
        gate, _ = self.delivery_command(head, snap)
        self.git('switch', 'develop')
        self.git('merge', '--no-ff', head, '-m', 'normal provider fixture')
        merged = self.git('rev-parse', 'HEAD').strip()
        self.git('push', 'origin', 'develop')
        after = {'state': 'merged', 'base_ref': 'develop', 'url': snap['url'], 'head': head,
                 'base': self.base, 'merge_sha': merged, 'normal_merge': True, 'merged_at': m.utc(),
                 'provider_evidence': self.reference()}
        path = self.root / 'provider-merge.json';path.write_text(json.dumps(after))
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=merged)
        self.policy['workers']['9'].update(active_task='fixture', ignored_custody='preserved',
                                          ignored_evidence=self.reference(), retirement=self.verdict(source=head, task='fixture'))
        return start, ready, gate, path, head, merged

    def test_normal_provider_receipt_can_retire_exact_task_then_fresh_dispatch(self):
        start, ready, gate, path, head, merged = self.normal_retirement_fixture()
        receipt, r = self.command('merge_receipt', '--worker', '9', '--snapshot', str(path),
                                 '--preflight', gate['receipt'], '--ready', ready['receipt'])
        self.assertEqual(r['task_linkage']['source'], head)
        self.command('retire', '--worker', '9', '--start', start['receipt'], '--ready', ready['receipt'],
                     '--integration', receipt['receipt'])
        self.assertTrue(self.repo.is_dir())
        self.policy['workers']['9']['active_task'] = None
        self.policy['routine_develop'] = {'reviewer': 'Morgan', 'verdict': 'reviewed-integration-line',
            'sha': merged, 'evidence': self.reference()}
        _, r = self.start(task='fresh-next-task')
        self.assertEqual(r['base'], merged)

    def test_normal_receipt_missing_linkage_or_forged_parents_cannot_launder_retirement(self):
        start, ready, gate, path, head, merged = self.normal_retirement_fixture()
        unlinked, _ = self.command('merge_receipt', '--worker', '9', '--snapshot', str(path), '--preflight', gate['receipt'])
        args = ['retire', '--worker', '9', '--start', start['receipt'], '--ready', ready['receipt'], '--integration']
        _, r = self.command(*args, unlinked['receipt'], ok=False)
        self.assertIn('cannot launder', r['error'])
        linked, _ = self.command('merge_receipt', '--worker', '9', '--snapshot', str(path),
                                  '--preflight', gate['receipt'], '--ready', ready['receipt'])
        raw = json.loads(Path(linked['receipt']).read_text())
        raw['merge_parents'] = [head, self.base]
        forged = self.ev / 'forged-normal-receipt.json';forged.write_text(json.dumps(raw))
        self.command(*args, str(forged), ok=False)
        raw['merge_parents'] = [self.base, head];raw['task_linkage']['ready_sha256'] = '0' * 64
        forged.write_text(json.dumps(raw));self.command(*args, str(forged), ok=False)
        self.assertEqual(self.git('rev-parse', 'feature/09/fixture').strip(), head)

    def test_known_security_alert_requires_separate_exact_disposition(self):
        head, snapshot = self.delivery_fixture();snapshot['security_alerts'] = ['synthetic scanner alert']
        _, r = self.delivery_command(head, snapshot, ok=False)
        self.assertIn('security disposition', r['error'])
        snapshot['security_confirmation'] = {'state': 'confirmed', 'head': head, 'base': self.base,
                                             'evidence': self.reference()}
        self.delivery_command(head, snapshot)
        snapshot['security_confirmation']['head'] = self.base
        self.delivery_command(head, snapshot, ok=False)

    def test_normal_merge_receipt_exact_parents_and_tree_without_posthoc_approval(self):
        head, snapshot = self.delivery_fixture()
        gate, _ = self.delivery_command(head, snapshot)
        self.git('switch', 'develop')
        self.git('merge', '--no-ff', head, '-m', 'normal fixture merge')
        merged = self.git('rev-parse', 'HEAD').strip()
        self.git('push', 'origin', 'develop')
        after = {'url': snapshot['url'], 'state': 'merged', 'base_ref': 'develop', 'head': head,
            'base': self.base, 'merge_sha': merged, 'normal_merge': True, 'merged_at': m.utc(),
            'provider_evidence': self.reference()}
        path = self.root / 'merge-snapshot.json';path.write_text(json.dumps(after))
        args = ['merge_receipt', '--worker', '9', '--snapshot', str(path), '--preflight', gate['receipt']]
        _, r = self.command(*args)
        self.assertEqual(r['merge_parents'], [self.base, head])
        after['base'] = head;path.write_text(json.dumps(after));self.command(*args, ok=False)
        after['base'] = self.base;after['merged_at'] = '2000-01-01T00:00:00Z'
        path.write_text(json.dumps(after));self.command(*args, ok=False)

    def test_routine_delivery_live_head_or_base_movement_blocks(self):
        head, snapshot = self.delivery_fixture()
        self.commit('post review head')
        self.git('push', 'origin', 'feature/delivery')
        _, r = self.delivery_command(head, snapshot, ok=False)
        self.assertIn('live PR head changed', r['error'])

    def test_routine_delivery_never_relabels_merged_pr_as_approval(self):
        head, snapshot = self.delivery_fixture();snapshot['state'] = 'merged'
        _, r = self.delivery_command(head, snapshot, ok=False)
        self.assertIn('historical merge', r['error'])

    def test_per_worker_launcher_binds_path_and_refuses_owner_override(self):
        launcher = SCRIPT.with_name('offmenu-gitflow-launch.py')
        self.write_policy()
        args = ['python3', '-B', str(launcher), '--policy', str(self.policy_path),
                '--evidence-dir', str(self.ev), 'start', '--kind', 'feature', '--task', 'launcher-task']
        p = subprocess.run(args, cwd=self.repo, env=m.git_environment(), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feature/09/launcher-task')
        p = subprocess.run(args + ['--worker', '2'], cwd=self.repo, env=m.git_environment(),
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn('binds', p.stderr)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feature/09/launcher-task')

    def test_busy_fetch_lock_refuses_cached_base_without_switch(self):
        with (self.remote / 'offmenu-fetch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _, r = self.start(ok=False)
        self.assertIn('lock is busy', r['error'])
        self.assertIsNone(r['fetches'][0]['exit_code'])
        self.assertIsNone(r['fetches'][0]['sha'])
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')

    def test_routine_dispatch_from_reviewed_line_without_release(self):
        self.policy['baseline'] = {};self.policy['lines'] = {}
        self.policy['routine_delivery'] = {'authorizer': 'Matt', 'project': 'OffMenu',
            'scope': 'normal-qualified-gitflow', 'evidence': self.reference()}
        self.policy['routine_develop'] = {'reviewer': 'Morgan', 'verdict': 'reviewed-integration-line',
            'sha': self.base, 'evidence': self.reference()}
        _, r = self.start()
        self.assertIn('release uncertified', r['dispatch_qualification'])

    def test_integration_preserves_ignored_collision_bytes(self):
        start, _ = self.start()
        (self.repo / 'collision').write_text('incoming tracked bytes')
        self.git('add', 'collision')
        self.git('commit', '-m', 'feature collision')
        source = self.git('rev-parse', 'HEAD').strip()
        ready, _ = self.ready(start)
        self.git('switch', 'develop')
        (self.repo / '.git/info/exclude').write_text('collision\n')
        (self.repo / 'collision').write_text('ignored integration owner bytes')
        self.review('develop', source, source)
        _, r = self.command('integrate', '--worker', '9', '--ready', ready['receipt'],
                            '--candidate', source, ok=False)
        self.assertIn('merge failed', r['error'])
        self.assertEqual((self.repo / 'collision').read_text(), 'ignored integration owner bytes')
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.base)

    def test_retirement_detach_preserves_ignored_collision_and_task_branch(self):
        start, ready, integration, source = self.integrated_fixture()
        (self.repo / 'collision').write_text('incoming tracked bytes')
        self.git('add', 'collision')
        self.git('commit', '-m', 'develop collision after integration')
        target = self.git('rev-parse', 'HEAD').strip()
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=target)
        self.git('switch', 'feature/09/fixture')
        (self.repo / '.git/info/exclude').write_text('collision\n')
        (self.repo / 'collision').write_text('ignored retirement owner bytes')
        w = self.policy['workers']['9']
        w.update(active_task='fixture', ignored_custody='preserved', ignored_evidence=self.reference(),
                 retirement=self.verdict(source=source, task='fixture'))
        _, r = self.command('retire', '--worker', '9', '--start', start['receipt'],
                            '--ready', ready['receipt'], '--integration', integration['receipt'], ok=False)
        self.assertIn('switch failed', r['error'])
        self.assertEqual((self.repo / 'collision').read_text(), 'ignored retirement owner bytes')
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feature/09/fixture')
        self.assertEqual(self.git('rev-parse', 'feature/09/fixture').strip(), source)

    def test_inherited_git_locations_cannot_redirect_fixture_or_script(self):
        guard = self.root / 'guard'
        self.run_git(self.root, 'init', str(guard))
        self.run_git(guard, 'config', 'user.name', 'Guard')
        self.run_git(guard, 'config', 'user.email', 'guard@example.invalid')
        (guard / 'owner').write_text('guarded owner bytes')
        self.run_git(guard, 'add', 'owner')
        self.run_git(guard, 'commit', '-m', 'guard')
        before = self.run_git(guard, 'rev-parse', 'HEAD')
        index = (guard / '.git/index').read_bytes()
        overrides = {'GIT_DIR': str(guard / '.git'), 'GIT_WORK_TREE': str(guard),
                     'GIT_INDEX_FILE': str(guard / '.git/index'), 'GIT_COMMON_DIR': str(guard / '.git'),
                     'GIT_OBJECT_DIRECTORY': str(guard / '.git/objects'),
                     'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(guard / '.git/objects'),
                     'GIT_NAMESPACE': 'sentinel', 'GIT_CONFIG_COUNT': '1',
                     'GIT_CONFIG_KEY_0': 'core.worktree', 'GIT_CONFIG_VALUE_0': str(guard),
                     'GIT_CONFIG_PARAMETERS': "'core.worktree='"}
        # The real shared repository is observed read-only; contamination always
        # points at the disposable guard. Portable runs omit only this host proof.
        shared = Path('/home/user/src/offmenu/.git')
        def shared_snapshot():
            if not shared.is_dir():
                return {'available': False}
            p = subprocess.run(['git', '--git-dir', str(shared), 'rev-parse', 'refs/heads/main'],
                               text=True, capture_output=True, env=m.git_environment())
            self.assertEqual(p.returncode, 0, p.stderr)
            index_path = shared / 'index'
            return {'common_dir': str(shared.resolve()), 'main': p.stdout.strip(),
                    'index_sha256': hashlib.sha256(index_path.read_bytes()).hexdigest() if index_path.exists() else None}
        real_before = shared_snapshot()
        author_repo = SCRIPT.parent.parent
        def author_identity():
            p = subprocess.run(['git', '-C', str(author_repo), 'rev-parse', 'HEAD'],
                               text=True, capture_output=True, env=m.git_environment())
            self.assertEqual(p.returncode, 0, p.stderr)
            branch = subprocess.run(['git', '-C', str(author_repo), 'branch', '--show-current'],
                                    text=True, capture_output=True, env=m.git_environment())
            self.assertEqual(branch.returncode, 0, branch.stderr)
            return {'head': p.stdout.strip(), 'branch': branch.stdout.strip()}
        author_before = author_identity()
        retained = Path('/home/user/Documents/Codex/2026-10-14/task-2/worker-09-gitflow/receipts')
        retained_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in retained.glob('*.json')}
        code_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                       (SCRIPT, SCRIPT.parent.parent / 'docs/OFFMENU_GITFLOW.md', Path(__file__).resolve())}
        with patch.dict(os.environ, overrides):
            # Fixture helper must still operate in its requested repository.
            self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.base)
            # Intentionally pass the polluted environment to the CLI, so its own
            # child Git sanitization is tested independently of command().
            self.write_policy()
            p = subprocess.run(['python3', '-B', str(SCRIPT), '--repo', str(self.repo),
                                '--policy', str(self.policy_path), '--evidence-dir', str(self.ev),
                                'start', '--worker', '9', '--kind', 'feature', '--task', 'ambient-env'],
                               text=True, capture_output=True, env=dict(os.environ))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(os.environ['GIT_DIR'], overrides['GIT_DIR'])
        self.assertEqual(shared_snapshot(), real_before)
        self.assertEqual(author_identity(), author_before)
        self.assertEqual({p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in retained_before}, retained_before)
        self.assertEqual({path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in code_before}, code_before)
        self.assertEqual(self.run_git(guard, 'rev-parse', 'HEAD'), before)
        self.assertEqual((guard / '.git/index').read_bytes(), index)
        self.assertEqual((guard / 'owner').read_text(), 'guarded owner bytes')
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feature/09/ambient-env')
        proof_path = os.environ.get('OFFMENU_GITFLOW_ISOLATION_PROOF')
        if proof_path:
            Path(proof_path).write_text(json.dumps({'contamination_target': str(guard),
                'variables': sorted(overrides), 'sentinel_head_unchanged': True, 'sentinel_index_unchanged': True,
                'sentinel_owner_bytes_unchanged': True, 'real_shared_before': real_before,
                'real_shared_after': shared_snapshot(), 'author_identity_unchanged': author_before,
                'retained_receipt_hashes_unchanged': retained_before, 'tracked_code_hashes_unchanged': code_before}, indent=2) + '\n')

    def test_dispatch_preserves_ignored_collision_bytes(self):
        # Main has ignored owner data; freshly qualified develop tracks that path.
        self.git('switch', 'develop')
        (self.repo / 'collision').write_text('incoming tracked bytes')
        self.git('add', 'collision')
        self.git('commit', '-m', 'track collision on develop')
        advanced = self.git('rev-parse', 'HEAD').strip()
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=advanced)
        self.git('switch', 'main')
        (self.repo / '.git/info/exclude').write_text('collision\n')
        (self.repo / 'collision').write_text('preserved ignored owner bytes')
        self.assertEqual(self.git('status', '--porcelain').strip(), '')
        _, r = self.start(ok=False)
        self.assertIn('switch failed', r['error'])
        self.assertEqual((self.repo / 'collision').read_text(), 'preserved ignored owner bytes')
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')

    def provisional(self):
        self.policy['baseline'] = {}
        self.policy['released_main'] = {}
        self.policy['lines'] = {}
        receipt = self.root / 'provisional-bootstrap.json'
        receipt.write_text(json.dumps({
            'schema': 'offmenu-provisional-develop/1',
            'verdict': 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE',
            'seed': self.base, 'localDevelop': self.base, 'fetchedDevelop': self.base,
            'releaseCertified': False, 'tagCreated': False, 'mainChanged': False}))
        self.policy['provisional_bootstrap'] = {
            'reviewer': 'Morgan', 'authorization': 'ordinary-development-start',
            'verdict': 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE',
            'qualification': 'unqualified', 'line': 'develop', 'sha': self.base, 'utc': m.utc(),
            'evidence': {'path': str(receipt), 'sha256': hashlib.sha256(receipt.read_bytes()).hexdigest()}}
        # Demonstrate that dispatch needs no certified first release or tag.
        self.git('push', 'origin', '--delete', 'v1.0.0')
        self.git('tag', '-d', 'v1.0.0')

    def test_provisional_feature_dispatch_records_truthful_readiness(self):
        self.provisional()
        start, r = self.start()
        self.assertEqual(r['base'], self.base)
        self.assertEqual(r['fetches'][0]['exit_code'], 0)
        self.assertEqual(r['dispatch_qualification'], 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE')
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.base)
        source = self.commit('provisional feature')
        _, r = self.ready(start)
        self.assertEqual(r['candidate'], source)
        self.assertEqual(r['dispatch_qualification'], 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE')
        self.assertEqual(r['completion'], 'ready_for_Morgan_review')

    def test_provisional_bugfix_dispatch(self):
        self.provisional()
        _, r = self.start(kind='bugfix')
        self.assertEqual(r['base_line'], 'develop')
        self.assertEqual(r['dispatch_base'], self.base)

    def test_provisional_unapproved_dispatch_refused(self):
        self.provisional()
        self.policy['provisional_bootstrap']['reviewer'] = 'worker09'
        _, r = self.start(ok=False)
        self.assertIn('Morgan provisional', r['error'])
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')
        self.policy['provisional_bootstrap']['reviewer'] = 'Morgan'
        self.policy['provisional_bootstrap']['authorization'] = 'integration-only'
        self.start(ok=False)
        del self.policy['provisional_bootstrap']
        _, r = self.start(ok=False)
        self.assertIn('no accepted release baseline', r['error'])

    def test_provisional_stale_fetched_develop_refused(self):
        self.provisional()
        self.git('switch', 'develop')
        advanced = self.commit('develop advanced after authorization')
        self.git('push', 'origin', 'develop')
        self.git('switch', 'main')
        _, r = self.start(ok=False)
        self.assertEqual(r['fetches'][0]['sha'], advanced)
        self.assertIn('stale provisional baseline', r['error'])
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')

    def test_provisional_cannot_qualify_release_hotfix_or_integration(self):
        self.provisional()
        self.start(kind='release', task='release-attempt', ok=False)
        self.start(kind='hotfix', task='hotfix-attempt', ok=False)
        start, _ = self.start()
        source = self.commit('provisional feature')
        ready, _ = self.ready(start)
        self.git('switch', 'develop')
        self.review('develop', source, source)
        _, r = self.command('integrate', '--worker', '9', '--ready', ready['receipt'],
                            '--candidate', source, ok=False)
        self.assertIn('no accepted release baseline', r['error'])
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.base)

    def test_provisional_bootstrap_evidence_mismatch_refused(self):
        self.provisional()
        record = self.policy['provisional_bootstrap']
        path = Path(record['evidence']['path'])
        data = json.loads(path.read_text())
        data['releaseCertified'] = True
        path.write_text(json.dumps(data))
        _, r = self.start(ok=False)
        self.assertIn('digest mismatch', r['error'])
        record['evidence']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        _, r = self.start(ok=False)
        self.assertIn('must not claim release', r['error'])

    def test_fresh_feature_dispatch_and_review_readiness(self):
        out, r = self.start()
        self.assertEqual(r['status'], 'completed')
        self.assertEqual(r['base'], self.base)
        self.assertEqual(r['fetches'][0]['exit_code'], 0)
        self.assertEqual(r['fetches'][0]['sha'], self.base)
        self.assertTrue(r['fetches'][0]['completed_utc'].endswith('Z'))
        candidate = self.commit()
        _, ready = self.ready(out)
        self.assertEqual(ready['candidate'], candidate)
        self.assertEqual(ready['completion'], 'ready_for_Morgan_review')
        self.assertNotIn('accepted', ready)

    def test_dry_run_does_not_consume_unique_task_and_second_task_blocks(self):
        _, r = self.start(check=True)
        self.assertEqual(r['status'], 'allowed')
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')
        self.start()
        _, r = self.start(task='second', ok=False)
        self.assertIn('active task', r['error'])

    def test_dirty_and_untracked_never_switch(self):
        before = self.git('symbolic-ref', 'HEAD')
        (self.repo / 'untracked').write_text('preserve me')
        _, r = self.start(ok=False)
        self.assertIn('custody', r['error'])
        self.assertEqual(self.git('symbolic-ref', 'HEAD'), before)
        self.assertEqual((self.repo / 'untracked').read_text(), 'preserve me')
        self.assertEqual(r['fetches'], [])

    def test_missing_develop_does_not_use_cached_ref(self):
        self.git('push', 'origin', '--delete', 'develop')
        _, r = self.start(ok=False)
        self.assertNotEqual(r['fetches'][0]['exit_code'], 0)
        self.assertIsNone(r['fetches'][0]['sha'])
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')

    def test_preserves_broken_capture_ref(self):
        broken = self.repo / '.git/refs/codex/turn-diffs/captures/fixture/base'
        broken.parent.mkdir(parents=True)
        broken.write_bytes(b'')
        # A new object forces connectivity negotiation through the malformed ref.
        publisher = self.root / 'publisher'
        self.run_git(self.root, 'clone', str(self.remote), str(publisher))
        self.run_git(publisher, 'config', 'user.name', 'Publisher')
        self.run_git(publisher, 'config', 'user.email', 'fixture@example.invalid')
        self.run_git(publisher, 'switch', 'develop')
        (publisher / 'fresh').write_text('new remote object')
        self.run_git(publisher, 'add', 'fresh')
        self.run_git(publisher, 'commit', '-m', 'fresh develop')
        self.run_git(publisher, 'push', 'origin', 'develop')
        _, r = self.start(ok=False)
        self.assertNotEqual(r['fetches'][0]['exit_code'], 0)
        self.assertEqual(broken.read_bytes(), b'')
        self.assertIn('bad object', r['fetches'][0]['stderr'])

    def test_unqualified_and_ambiguous_custody_block(self):
        self.policy['lines']['develop']['qualification'] = 'unqualified'
        _, r = self.start(ok=False)
        self.assertEqual(r['fetches'][0]['exit_code'], 0)
        self.assertIn('unqualified', r['error'])
        self.policy['lines']['develop']['qualification'] = 'qualified'
        self.policy['workers']['9']['recovery_dependencies'] = ['retained original']
        _, r = self.start(ok=False)
        self.assertIn('recovery_dependencies', r['error'])

    def test_pool_path_origin_and_unique_branch(self):
        self.command('start', '--worker', '33', '--kind', 'feature', '--task', 'bad', ok=False)
        self.policy['workers']['9']['path'] = str(self.root / 'other')
        self.start(ok=False)
        self.policy['workers']['9']['path'] = str(self.repo)
        self.policy['origin'] = 'wrong-origin'
        self.start(ok=False)
        self.policy['origin'] = str(self.remote)
        self.start()
        self.start(ok=False)

    def test_no_accepted_baseline_and_evidence_tamper(self):
        self.policy['baseline'] = {}
        _, r = self.start(ok=False)
        self.assertIn('no accepted release baseline', r['error'])
        self.policy['baseline'] = dict(self.verdict(sha=self.base), tag='v1.0.0', tag_object=self.git('rev-parse', 'v1.0.0').strip())
        self.proof.write_text('changed approval')
        _, r = self.start(ok=False)
        self.assertIn('digest mismatch', r['error'])

    def test_release_tag_is_pinned_on_canonical_remote(self):
        self.git('push', 'origin', '--delete', 'v1.0.0')
        _, r = self.start(ok=False)
        self.assertIn('tag unavailable', r['error'])
        self.assertNotEqual(r['tag_checks'][0]['exit_code'], 0)

    def test_stale_qualified_line_sha_blocks_dispatch(self):
        self.git('switch', 'develop')
        changed = self.commit('advanced')
        self.git('push', 'origin', 'develop')
        _, r = self.start(ok=False)
        self.assertEqual(r['fetches'][0]['sha'], changed)
        self.assertIn('exact sha', r['error'])

    def integrated_fixture(self, kind='feature', line='develop'):
        start, _ = self.start(kind=kind)
        source = self.commit(kind + ' change')
        ready, _ = self.ready(start)
        self.git('switch', line)
        self.review(line, source, source)
        integrated, _ = self.command('integrate', '--worker', '9', '--ready', ready['receipt'],
                                     '--line', line, '--candidate', source)
        return start, ready, integrated, source

    def test_exact_review_required_and_successful_integration(self):
        start, _ = self.start()
        source = self.commit()
        ready, _ = self.ready(start)
        self.git('switch', 'develop')
        args = ['integrate', '--worker', '9', '--ready', ready['receipt'], '--candidate', source]
        _, r = self.command(*args, ok=False)
        self.assertIn('exact candidate', r['error'])
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.base)
        self.review('develop', source, source)
        _, r = self.command(*args)
        self.assertEqual(r['candidate'], source)
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), source)

    def test_feature_cannot_bypass_release_to_main(self):
        start, _ = self.start()
        source = self.commit()
        ready, _ = self.ready(start)
        self.git('switch', 'main')
        self.review('main', source, source)
        _, r = self.command('integrate', '--worker', '9', '--ready', ready['receipt'], '--line', 'main',
                            '--candidate', source, ok=False)
        self.assertIn('only reviewed hotfixes', r['error'])

    def test_changed_task_and_wrong_verdict_do_not_integrate(self):
        start, _ = self.start()
        source = self.commit()
        ready, _ = self.ready(start)
        self.commit('post review change')
        self.git('switch', 'develop')
        self.review('develop', source, source)
        _, r = self.command('integrate', '--worker', '9', '--ready', ready['receipt'], '--candidate', source, ok=False)
        self.assertIn('changed after', r['error'])

    def test_preserved_exception_ready_does_not_claim_fresh_dispatch(self):
        self.git('switch', '-c', 'worker/09/foundation')
        self.commit('foundation implementation')
        self.policy['workers']['9']['active_task'] = 'foundation'
        args = ['exception', '--worker', '9', '--task', 'foundation']
        self.command(*args, ok=False)
        self.policy['base_exceptions']['9'] = {
            'authorization': 'Matt', 'evidence': self.reference(), 'base': self.base,
            'task': 'foundation', 'branch': 'worker/09/foundation', 'kind': 'feature'}
        start, r = self.command(*args)
        self.assertEqual(r['qualification'], 'unqualified-base-exception')
        self.assertEqual(r['fetches'], [])
        _, r = self.ready(start)
        self.assertEqual(r['base_line'], 'preserved-exception')
        self.assertTrue(r['exception'])
        self.assertEqual(r['completion'], 'ready_for_Morgan_review')
        self.command(*args, ok=False)

    def test_wrong_reviewer_and_duplicate_verdict_block(self):
        start, _ = self.start()
        source = self.commit()
        ready, _ = self.ready(start)
        self.git('switch', 'develop')
        self.review('develop', source, source)
        self.policy['reviews'][0]['reviewer'] = 'worker09'
        args = ['integrate', '--worker', '9', '--ready', ready['receipt'], '--candidate', source]
        _, r = self.command(*args, ok=False)
        self.assertIn('Morgan accepted', r['error'])
        self.policy['reviews'][0]['reviewer'] = 'Morgan'
        self.policy['reviews'].append(dict(self.policy['reviews'][0]))
        self.command(*args, ok=False)

    def test_develop_advance_requires_reconciliation(self):
        start, _ = self.start()
        source = self.commit('feature changes')
        ready, _ = self.ready(start)
        self.git('switch', 'develop')
        (self.repo / 'other').write_text('other work')
        self.git('add', 'other')
        self.git('commit', '-m', 'advance develop')
        advanced = self.git('rev-parse', 'HEAD').strip()
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=advanced)
        self.git('merge', '--no-ff', source, '-m', 'prepare exact synthetic candidate')
        candidate = self.git('rev-parse', 'HEAD').strip()
        # Restore fixture target by normal checkout of a temporary test branch, then
        # move develop back in this disposable repository only.
        self.git('switch', '--detach', candidate)
        self.git('branch', '-f', 'develop', advanced)
        self.git('switch', 'develop')
        self.review('develop', candidate, source, base=advanced)
        args = ['integrate', '--worker', '9', '--ready', ready['receipt'], '--candidate', candidate]
        _, r = self.command(*args, ok=False)
        self.assertIn('reconciliation required', r['error'])
        self.policy['reconciliations'] = [self.verdict(source=source, develop=advanced)]
        self.command(*args)

    def test_hotfix_requires_accepted_released_main(self):
        self.policy['released_main'] = {}
        _, r = self.start(kind='hotfix', ok=False)
        self.assertIn('Morgan accepted', r['error'])
        self.policy['released_main'] = dict(self.verdict(sha=self.base), tag='v1.0.0', tag_object=self.git('rev-parse', 'v1.0.0').strip())
        _, r = self.start(kind='hotfix')
        self.assertEqual(r['base_line'], 'main')

    def test_release_requires_backmerge_qualification_and_immutable_tag(self):
        start, _ = self.start(kind='release')
        candidate = self.commit('release fix')
        self.git('switch', 'main')
        self.policy['reviews'] = [self.verdict(operation='promote-release', candidate=candidate,
                                               base=self.base, source=self.base)]
        args = ['promote', '--worker', '9', '--start', start['receipt'], '--candidate', candidate, '--tag', 'v1.1.0']
        _, r = self.command(*args, ok=False)
        self.assertIn('back-merged', r['error'])
        # Simulate separately reviewed backmerge/publication in the fixture.
        self.git('switch', 'develop')
        self.git('merge', '--ff-only', candidate)
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=candidate)
        self.policy['reviews'] = [self.verdict(operation='promote-release', candidate=candidate,
                                               base=self.base, source=candidate)]
        self.git('switch', 'main')
        self.command(*args)
        self.assertEqual(self.git('rev-parse', 'v1.1.0^{commit}').strip(), candidate)
        self.command(*args, ok=False)
        self.assertEqual(self.git('rev-parse', 'v1.1.0^{commit}').strip(), candidate)

    def test_develop_initialized_once_only_with_exact_baseline_decision(self):
        self.git('push', 'origin', '--delete', 'develop')
        self.git('branch', '-d', 'develop')
        self.policy['develop_initialized'] = False
        self.policy['reviews'] = [self.verdict(operation='initialize-develop', candidate=self.base,
                                               base=self.base, source=self.base)]
        self.command('initialize', '--worker', '9')
        self.assertEqual(self.git('rev-parse', 'develop').strip(), self.base)
        self.command('initialize', '--worker', '9', ok=False)
        self.git('branch', '-d', 'develop')
        _, r = self.command('initialize', '--worker', '9', ok=False)
        self.assertIn('initialization receipt exists', r['error'])

    def test_retire_requires_review_integration_custody_and_preserves_path(self):
        start, ready, integrated, source = self.integrated_fixture()
        args = ['retire', '--worker', '9', '--start', start['receipt'], '--ready', ready['receipt'],
                '--integration', integrated['receipt']]
        self.command(*args, ok=False)
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=source)
        w = self.policy['workers']['9']
        w.update(active_task='fixture', ignored_custody='preserved', ignored_evidence=self.reference(),
                 retirement=self.verdict(source=source, task='fixture'))
        w['open_prs'] = ['PR fixture']
        self.command(*args, ok=False)
        w['open_prs'] = []
        self.command(*args)
        self.assertTrue(self.repo.is_dir())
        self.assertIn(f'worktree {self.repo}', self.git('worktree', 'list', '--porcelain'))
        p = subprocess.run(['git', '-C', str(self.repo), 'show-ref', '--verify', 'refs/heads/feature/09/fixture'],
                           capture_output=True, env=m.git_environment())
        self.assertNotEqual(p.returncode, 0)

    def test_hotfix_retirement_requires_both_lines(self):
        start, ready, integrated, source = self.integrated_fixture(kind='hotfix', line='main')
        self.git('push', 'origin', 'main')
        self.git('tag', '-a', 'v1.0.1', source, '-m', 'synthetic released hotfix')
        self.git('push', 'origin', 'v1.0.1')
        self.policy['released_main'] = dict(self.verdict(sha=source), tag='v1.0.1', tag_object=self.git('rev-parse', 'v1.0.1').strip())
        self.policy['lines']['main'] = self.verdict(line='main', sha=source)
        w = self.policy['workers']['9']
        w.update(active_task='fixture', ignored_custody='preserved', ignored_evidence=self.reference(),
                 retirement=self.verdict(source=source, task='fixture'))
        args = ['retire', '--worker', '9', '--start', start['receipt'], '--ready', ready['receipt'],
                '--integration', integrated['receipt']]
        _, r = self.command(*args, ok=False)
        self.assertIn('not integrated', r['error'])
        self.git('switch', 'develop')
        self.git('merge', '--ff-only', source)
        self.git('push', 'origin', 'develop')
        self.policy['lines']['develop'] = self.verdict(line='develop', sha=source)
        self.command(*args)


if __name__ == '__main__':
    unittest.main()
