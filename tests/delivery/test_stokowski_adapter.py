"""Meaningful execution-boundary checks; no model or tracker calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0, str(TOOLS))
import stokowski_worker as worker


class StokowskiBoundaryTests(unittest.TestCase):
    def test_child_actually_receives_only_selected_environment(self):
        environment = dict(os.environ, LINEAR_API_KEY='tracker-canary',
                           UNKNOWN_PROVIDER_TOKEN='provider-canary',
                           OPENAI_API_KEY='api-canary', LANGSMITH_API_KEY='trace-canary')
        result = subprocess.check_output([sys.executable, '-c',
            'import os,json;print(json.dumps(dict(os.environ)))'],
            env=worker.child_environment(environment), text=True)
        actual = json.loads(result)
        for key in ('LINEAR_API_KEY','UNKNOWN_PROVIDER_TOKEN','OPENAI_API_KEY','LANGSMITH_API_KEY'):
            self.assertNotIn(key, actual)
        self.assertEqual(actual['LANGSMITH_TRACING'], 'false')
        self.assertNotIn('canary', result)

    def test_current_codex_command_has_json_and_no_legacy_flags(self):
        args = worker.codex_command(Path('/workspace'),Path('/private/final.txt'))
        self.assertEqual(args[1], 'exec')
        self.assertIn('--json',args)
        self.assertNotIn('--quiet',args)
        self.assertNotIn('--prompt',args)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',args)
        self.assertEqual(args[-1], '-')
        with self.assertRaises(ValueError):
            worker.codex_command(Path('/workspace'),Path('/private/final.txt'),'unapproved-model')

    def test_event_parser_requires_explicit_completed_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'events.jsonl'
            path.write_text('not json\n'+json.dumps({'type':'thread.started','thread_id':'native-123'})+'\n')
            self.assertFalse(worker.summarize_events(path)['turn_completed'])
            with path.open('a') as stream:
                stream.write(json.dumps({'type':'turn.completed','usage':{'input_tokens':12}})+'\n')
            result = worker.summarize_events(path)
            self.assertEqual(result['session_id'],'native-123')
            self.assertTrue(result['turn_completed'])
            self.assertEqual(result['usage']['input_tokens'],12)

    def test_timeout_reaps_detached_grandchild(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root/'attempts'/'UIF-92'
            directory.mkdir(parents=True)
            marker = root/'child.pid'
            script = ('import subprocess,sys,time,pathlib; '
                      'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],start_new_session=True); '
                      f'pathlib.Path({str(marker)!r}).write_text(str(p.pid)); time.sleep(60)')
            result = worker.supervise([sys.executable,'-c',script], '', root,
                     worker.child_environment(os.environ),directory,1,
                     {'memory_bytes':1024**3},64)
            self.assertEqual(result['status'],'timed_out')
            self.assertTrue(result['child_tree_gone'])
            self.assertFalse(Path('/proc',marker.read_text()).exists())

    def test_cancellation_receipt_requires_process_termination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root/'attempts'/'UIF-92'
            directory.mkdir(parents=True)
            (root/'cancel.json').write_text('{}')
            result = worker.supervise([sys.executable,'-c','import time;time.sleep(60)'],
                     '', root, worker.child_environment(os.environ),directory,5,
                     {'memory_bytes':1024**3},64)
            self.assertEqual(result['status'],'cancelled')
            self.assertTrue(result['child_tree_gone'])


if __name__ == '__main__':
    unittest.main()
