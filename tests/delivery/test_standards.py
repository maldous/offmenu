"""Architecture discovery and naming compliance against a versioned contract."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from offmenu.delivery.standards import check, discover, valid_name


class StandardsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offmenu-standard-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q', '-b', 'feature/test')
        self.git('config', 'user.name', 'Standards Test')
        self.git('config', 'user.email', 'standards@example.invalid')
        (self.root / '.gitignore').write_text('.delivery/\ndata/\n')
        self.policy = {'version': '1.0.0', 'roots': {
            '.gitignore': {}, 'repository-standard.json': {}, 'src': {}, 'tests': {}},
            'legacy_paths': []}
        self.write_policy()
        (self.root / 'src/offmenu').mkdir(parents=True)
        (self.root / 'src/offmenu' / '__init__.py').write_text('')
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def write_policy(self):
        (self.root / 'repository-standard.json').write_text(json.dumps(self.policy))

    def test_discovery_reports_tracked_architecture_and_manifest_hash(self):
        result = discover(self.root)
        self.assertEqual(result['branch'], 'feature/test')
        self.assertEqual(result['revision'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(result['roots']['src'], 1)
        self.assertEqual(result['tracked_files'], 3)
        self.assertEqual(len(result['manifests']['repository-standard.json']), 64)

    def test_new_root_and_nonconforming_filename_fail(self):
        (self.root / 'mystery').mkdir()
        (self.root / 'mystery' / 'BadName.py').write_text('')
        result = check(self.root)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual({e['rule'] for e in result['errors']}, {'unclassified-root', 'filename'})

    def test_new_conforming_python_file_passes(self):
        (self.root / 'src/offmenu' / 'safe_module.py').write_text('')
        result = check(self.root)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['standard_version'], '1.0.0')

    def test_explicit_legacy_exception_is_path_specific(self):
        (self.root / 'src/offmenu' / 'BadName.py').write_text('')
        self.policy['legacy_paths'] = ['src/offmenu/BadName.py']
        self.write_policy()
        self.assertEqual(check(self.root)['status'], 'passed')
        (self.root / 'src/offmenu' / 'OtherBadName.py').write_text('')
        result = check(self.root)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'], [{'path': 'src/offmenu/OtherBadName.py', 'rule': 'filename'}])

    def test_ignored_private_runtime_and_data_are_excluded(self):
        for name in ('.delivery', 'data'):
            (self.root / name).mkdir()
            (self.root / name / 'PrivateEvidence.json').write_text('{}')
        self.assertEqual(check(self.root)['status'], 'passed')
        self.assertEqual(discover(self.root)['untracked_count'], 0)

    def test_retired_test_root_rejected_even_if_classified(self):
        (self.root / 'tests-web').mkdir()
        (self.root / 'tests-web' / 'safe.test.mjs').write_text('')
        self.policy['roots']['tests-web'] = {}
        self.write_policy()
        result = check(self.root)
        self.assertEqual(result['status'], 'failed')
        self.assertIn({'path': 'tests-web/safe.test.mjs', 'rule': 'retired-test-root'}, result['errors'])

    def test_python_and_conventional_names(self):
        for value in ('offmenu/__init__.py', 'offmenu/__main__.py', 'offmenu/safe_module.py',
                      'docs/README.md', 'apps/web/src/scanner-worker.js'):
            self.assertTrue(valid_name(value), value)
        for value in ('offmenu/BadModule.py', 'offmenu/bad-module.py', 'docs/Bad Name.md'):
            self.assertFalse(valid_name(value), value)


if __name__ == '__main__':
    unittest.main()
