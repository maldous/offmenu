"""Focused checks for native OffMenu admission; no credentials or model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dev.delivery import symphony_launch as launch
from dev.delivery import symphony_workspace as workspace
from dev.delivery.symphony_codex import isolated_codex_environment


class NativeAdmission(unittest.TestCase):
    def payload(self):
        return {'data': {'issue': {'id': launch.ISSUE_ID, 'identifier': 'UIF-90', 'project': {'id': launch.PROJECT_ID, 'slugId': launch.NATIVE_SLUG_ID}, 'team': {'id': '53f584e7-70a1-4b1e-b982-b815210e47d4'}, 'state': {'name': 'In Progress'}, 'labels': {'nodes': [{'name': launch.LABEL}]}}, 'issues': {'nodes': [{'id': launch.ISSUE_ID}]}}}

    def check_payload(self, payload):
        import io
        with patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
            return launch.tracker_preflight({'OFFMENU_LINEAR_API_KEY': 'test-not-a-real-key'})

    def test_exact_issue_scope(self):
        self.assertEqual(self.check_payload(self.payload())['candidate_count'], 1)

    def test_wrong_project_fails(self):
        payload = self.payload()
        payload['data']['issue']['project']['id'] = 'another-project'
        with self.assertRaises(RuntimeError):
            self.check_payload(payload)

    def test_second_issue_fails(self):
        payload = self.payload()
        payload['data']['issues']['nodes'].append({'id': 'other'})
        with self.assertRaises(RuntimeError):
            self.check_payload(payload)

    def test_missing_credential_route_fails(self):
        with self.assertRaises(RuntimeError):
            launch.credential({})

    def test_dirty_source_prevents_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launch, 'prerequisite', return_value={'source_branch': launch.BRANCH, 'tracked_source_clean': False}):
                with self.assertRaises(RuntimeError):
                    launch.prepare(Path(directory), 'gpt-6.1-sol')
            self.assertFalse((Path(directory)/'WORKFLOW.md').exists())

    def test_wrong_workspace_is_never_admitted(self):
        with patch('sys.argv', ['hook', 'admit', '--source', '/tmp/source', '--head', 'a'*40]), patch.object(Path, 'cwd', return_value=Path('/tmp/UIF-89')):
            with self.assertRaises(SystemExit):
                workspace.main()


class CodexIsolation(unittest.TestCase):
    def test_owned_home_references_auth_without_config_copy_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root/'existing'
            original.mkdir()
            auth = original/'auth.json'
            auth.write_text('fake fixture; never a real credential')
            (original/'config.toml').write_text('workstation_fixture = true')
            runtime = root/'runtime'
            runtime.mkdir()
            with isolated_codex_environment({'CODEX_HOME': str(original)}, runtime) as environment:
                owned = Path(environment['CODEX_HOME'])
                self.assertEqual(owned.stat().st_mode & 0o777, 0o700)
                self.assertTrue((owned/'auth.json').is_symlink())
                self.assertEqual((owned/'auth.json').resolve(), auth)
                self.assertFalse((owned/'config.toml').exists())
                self.assertEqual(environment['CODEX_SQLITE_HOME'], str(runtime/'codex-state'))
            self.assertFalse(owned.exists())
            self.assertTrue(auth.exists())
            self.assertTrue((original/'config.toml').exists())

    def test_native_failure_is_not_normal_turn_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            logs = runtime/'logs'
            logs.mkdir()
            (logs/'symphony.log.1').write_text('Agent run failed for issue_id='+launch.ISSUE_ID+': initialize timeout')
            self.assertEqual(launch.native_outcome(runtime), 'failed')


if __name__ == '__main__':
    unittest.main()
