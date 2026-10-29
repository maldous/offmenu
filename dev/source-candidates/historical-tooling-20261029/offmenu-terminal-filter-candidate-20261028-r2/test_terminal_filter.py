import base64
import hashlib
import json
import io
from types import SimpleNamespace
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import terminal_filter as f


def saved(data, root):
    path, stream = f.new_artifact(Path(root)/'private')
    with stream:
        stream.write(data)
    return f.finalize(path, profile='synthetic-fixture', returncode=None,
                      cancelled=False, elapsed=0)


class FilterTests(unittest.TestCase):
    def assert_original(self, meta, data):
        path = Path(meta['original_artifact'])
        self.assertEqual(path.read_bytes(), data)
        self.assertEqual(meta['original_sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(meta['original_bytes'], len(data))
        self.assertEqual(path.stat().st_mode & 0o777, 0o400)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_known_unittest_omissions_are_explicit(self):
        data = b'test_one (synthetic.Tests.test_one) ... ok\n\n----------\nRan 1 test in 0.1s\n\nOK\n'
        with tempfile.TemporaryDirectory() as root:
            meta = saved(data, root)
            self.assert_original(meta, data)
            result = json.loads(f.summarize(meta))
            self.assertEqual(result['mode'], 'strict_unittest_ok')
            self.assertEqual(result['omitted_bytes'], len(data)-len(result['retained_text'].encode()))
            self.assertEqual(result['omitted_records'], 4)
            self.assertEqual(result['execution_outcome'], 'not_observed')
            self.assertFalse(result['summary_is_full_evidence'])

    def test_unknown_diagnostic_never_classified_as_harmless(self):
        data = b'test_one (synthetic.Tests.test_one) ... ok\nUNUSUAL DIAGNOSTIC needs attention\nRan 1 test in 0.1s\nOK\n'
        with tempfile.TemporaryDirectory() as root:
            meta = saved(data, root)
            result = json.loads(f.summarize(meta, 2048))
            self.assertEqual(result['mode'], 'bounded_raw_chunks')
            self.assertEqual(result['omitted_bytes'], 0)
            reconstructed = b''.join(base64.b64decode(c['base64']) for c in result['raw_chunks'])
            self.assertEqual(reconstructed, data)
            self.assert_original(meta, data)

    def test_long_unicode_binary_lines_are_exact_and_summary_is_bounded(self):
        for data in (b'ERROR '+b'x'*10000, ('error: '+('é☃'*4000)).encode(), b'\x00\xff\xfe\x1b[31mFAIL\n'*1000):
            with self.subTest(length=len(data)), tempfile.TemporaryDirectory() as root:
                meta = saved(data, root)
                output = f.summarize(meta, 1280)
                self.assertLessEqual(len(output), 1280)
                result = json.loads(output)
                self.assertEqual(result['mode'], 'bounded_raw_chunks')
                self.assertTrue(result['diagnostic_omission_possible'])
                self.assertEqual(result['omitted_bytes'], len(data)-sum(c['bytes'] for c in result['raw_chunks']))
                for chunk in result['raw_chunks']:
                    self.assertEqual(base64.b64decode(chunk['base64']),data[chunk['offset']:chunk['offset']+chunk['bytes']])
                self.assert_original(meta, data)

    def test_nonzero_exit_and_failure_diagnostics_survive_without_shell_evaluation(self):
        command = [sys.executable, '-c', "import os,sys;os.write(1,b'FAIL synthetic diagnostic\\n');os.write(2,b'ERROR detail\\n');sys.exit(7)", 'literal; $(not-a-command)']
        with tempfile.TemporaryDirectory() as root:
            meta = f.capture_command(command, Path(root)/'private', profile='synthetic-fixture', cwd=root)
            self.assertEqual(meta['command_argv'], command)
            self.assertEqual(meta['process_returncode'], 7)
            self.assertEqual(f.shell_status(meta), 7)
            result = json.loads(f.summarize(meta))
            self.assertEqual(result['execution_outcome'], 'exited_nonzero')
            self.assertEqual(result['omitted_bytes'], 0)
            self.assert_original(meta, b'FAIL synthetic diagnostic\nERROR detail\n')

    def test_cancellation_before_launch_stays_cancelled_without_forged_exit(self):
        with tempfile.TemporaryDirectory() as root, patch.object(f.subprocess, 'Popen', side_effect=f.CaptureCancelled(signal.SIGTERM)):
            meta = f.capture_command((sys.executable, '-c', 'pass'), Path(root)/'private', profile='synthetic-fixture', cwd=root)
            self.assertTrue(meta['cancelled'])
            self.assertIsNone(meta['process_returncode'])
            self.assertEqual(f.shell_status(meta), 143)
            self.assert_original(meta, b'')

    def test_public_entrypoint_preserves_nonzero_status(self):
        command = (sys.executable, '-c', "import sys;print('ERROR synthetic');sys.exit(9)")
        with tempfile.TemporaryDirectory() as root:
            output = io.BytesIO()
            with patch.object(f, 'ROOT', Path(root)), patch.dict(f.COMMANDS, {'synthetic-test-only': command}), patch.object(f.sys, 'stdout', SimpleNamespace(buffer=output)):
                status = f.main(['run', 'synthetic-test-only'])
            self.assertEqual(status, 9)
            result = json.loads(output.getvalue())
            self.assertEqual(result['process_returncode'], 9)
            self.assertEqual(result['execution_outcome'], 'exited_nonzero')

    def test_post_exit_persistence_failure_preserves_known_nonzero_cli_status(self):
        command = (sys.executable, '-c', "import os,sys;os.write(1,b'ERROR retained failure\\n');sys.exit(7)")
        for target in ('finalize', 'os.fsync'):
            with self.subTest(failed_operation=target), tempfile.TemporaryDirectory() as root:
                output, errors = io.BytesIO(), io.StringIO()
                with patch.object(f, 'ROOT', Path(root)), patch.dict(f.COMMANDS, {'synthetic-test-only': command}), patch.object(f.sys, 'stdout', SimpleNamespace(buffer=output)), patch.object(f.sys, 'stderr', errors), patch('terminal_filter.'+target, side_effect=OSError):
                    status = f.main(['run', 'synthetic-test-only'])
                self.assertEqual(status, 7)
                report = json.loads(errors.getvalue())
                self.assertEqual(report['tool_status'], 'failed_closed')
                self.assertEqual(report['error_type'], 'OSError')
                self.assertEqual(report['process_returncode'], 7)
                self.assertFalse(report['finalized_receipt_returned'])
                self.assertIsNone(report['capture_receipt'])
                self.assertNotIn('original_sha256', report)
                self.assertEqual(output.getvalue(), b'')
                artifact = Path(report['original_artifact'])
                self.assertEqual(artifact.read_bytes(), b'ERROR retained failure\n')
                self.assertEqual(artifact.stat().st_mode & 0o077, 0)

    def test_cancellation_and_persistence_failure_preserve_cli_143(self):
        command = (sys.executable, '-c', 'pass')
        for target in ('finalize', 'os.fsync'):
            with self.subTest(failed_operation=target), tempfile.TemporaryDirectory() as root:
                output, errors = io.BytesIO(), io.StringIO()
                with patch.object(f, 'ROOT', Path(root)), patch.dict(f.COMMANDS, {'synthetic-test-only': command}), patch.object(f.subprocess, 'Popen', side_effect=f.CaptureCancelled(signal.SIGTERM)), patch.object(f.sys, 'stdout', SimpleNamespace(buffer=output)), patch.object(f.sys, 'stderr', errors), patch('terminal_filter.'+target, side_effect=OSError):
                    status = f.main(['run', 'synthetic-test-only'])
                self.assertEqual(status, 143)
                report = json.loads(errors.getvalue())
                self.assertEqual(report['tool_status'], 'failed_closed')
                self.assertEqual(report['error_type'], 'OSError')
                self.assertIsNone(report['process_returncode'])
                self.assertTrue(report['cancelled'])
                self.assertEqual(report['cancellation_signal'], signal.SIGTERM)
                self.assertFalse(report['finalized_receipt_returned'])
                self.assertIsNone(report['capture_receipt'])
                self.assertNotIn('original_sha256', report)
                self.assertEqual(Path(report['original_artifact']).read_bytes(), b'')
                self.assertEqual(output.getvalue(), b'')

    def test_cli_rejects_arbitrary_commands_and_paths_before_capture(self):
        with patch.object(f, 'capture_command') as capture, patch.object(f, 'save_named_log') as save:
            for args in (['run', 'arbitrary-command'], ['saved', '/etc/passwd']):
                with self.assertRaises(SystemExit) as error:
                    f.main(args)
                self.assertEqual(error.exception.code, 2)
            capture.assert_not_called()
            save.assert_not_called()

    def test_changed_named_input_and_nonprivate_directory_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root)/'synthetic.log'
            source.write_bytes(b'changed unknown contents')
            with patch.dict(f.SAVED_LOGS, {'synthetic': (source, '0'*64)}):
                with self.assertRaises(ValueError):
                    f.save_named_log('synthetic', Path(root)/'private')
            directory = Path(root)/'public'
            directory.mkdir(mode=0o755)
            with self.assertRaises(ValueError):
                f.new_artifact(directory)

    def test_cancellation_retains_diagnostics_reaps_child_and_status(self):
        for cancellation in (signal.SIGINT, signal.SIGTERM):
            self.check_cancellation(cancellation)

    def check_cancellation(self, cancellation):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root)/'started'
            child = "import os,signal,time;signal.signal(signal.SIGINT,lambda *a: (os.write(2,b'ERROR cancelled fixture\\n'),exit(23)));signal.signal(signal.SIGTERM,lambda *a: (os.write(2,b'ERROR cancelled fixture\\n'),exit(23)));open('started','w').write(str(os.getpid()));time.sleep(30)"
            command = [sys.executable, '-c', child]
            # Real worker process, real SIGINT, only synthetic controlled output.
            runner = "import json,sys;from pathlib import Path;import terminal_filter as f;m=f.capture_command(json.loads(sys.argv[1]),Path(sys.argv[2])/'private',profile='synthetic-fixture',cwd=sys.argv[2]);print(json.dumps(m),flush=True);sys.exit(f.shell_status(m))"
            proc = subprocess.Popen([sys.executable, '-c', runner, json.dumps(command), root],
                                    cwd=f.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+3
                while not marker.exists() and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(marker.exists())
                pid = int(marker.read_text())
                proc.send_signal(cancellation)
                stdout, stderr = proc.communicate(timeout=3)
                self.assertEqual(proc.returncode, 128+cancellation, stderr)
                meta = json.loads(stdout)
                self.assertTrue(meta['cancelled'])
                self.assertEqual(meta['cancellation_signal'], cancellation)
                self.assertEqual(meta['process_returncode'], 23)
                self.assertIn(b'ERROR cancelled fixture', Path(meta['original_artifact']).read_bytes())
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
