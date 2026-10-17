import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_foo_setup", ROOT / "scripts/check-foo-setup.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class SetupBatchTests(unittest.TestCase):
    def test_all_three_steps_run_independently_after_failure(self):
        seen = []
        def fake(name, command, log_dir):
            seen.append(name)
            (log_dir / (name + ".stderr")).write_text("Ran 1 test in 0.001s\n")
            return {"stepId": name, "status": "failed" if name != "refresh-unit-tests" else "passed",
                    "exitCode": 7 if name != "refresh-unit-tests" else 0, "durationSeconds": 0.1}
        with tempfile.TemporaryDirectory() as tmp, patch.object(batch, "run_step", side_effect=fake):
            report = batch.run_batch(Path(tmp))
        self.assertEqual(seen, ["preflight", "runner-unit-tests", "refresh-unit-tests"])
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["steps"][0]["exitCode"], 7)
        self.assertEqual(report["steps"][-1]["status"], "passed")

    def test_zero_discovered_tests_are_not_a_pass(self):
        def fake(name, command, log_dir):
            (log_dir / (name + ".stderr")).write_text("Ran 0 tests in 0.000s\n")
            return {"stepId": name, "status": "failed" if name == "preflight" else "passed",
                    "exitCode": 1 if name == "preflight" else 0, "durationSeconds": 0.1}
        with tempfile.TemporaryDirectory() as tmp, patch.object(batch, "run_step", side_effect=fake):
            report = batch.run_batch(Path(tmp))
        self.assertEqual(report["status"], "failed")
        self.assertTrue(all(s.get("errorCode") == "no-test-execution-established" for s in report["steps"][1:]))

    def test_preflight_strips_unknown_private_fields(self):
        value = {"reportKind": "offmenu-runner-host-preflight", "linux": True,
                 "distribution": "debian", "pythonVersion": "3.12.1",
                 "secret": "PRIVATE_TOKEN", "cachePath": "/home/private/dataset", "tools": {"curl": True, "secret": "PRIVATE_TOKEN"}}
        result = batch.sanitized_preflight(json.dumps(value).encode())
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("/home", json.dumps(result))
        self.assertEqual(result["tools"], {"curl": True})

    def test_token_environment_not_inherited(self):
        with patch.dict(os.environ, {"GH_TOKEN": "PRIVATE", "AWS_SECRET_ACCESS_KEY": "PRIVATE", "SSH_AUTH_SOCK": "/private/socket"}):
            for github in (False, True):
                result = batch.environment(Path("/tmp/check"), for_github=github)
                self.assertNotIn("PRIVATE", json.dumps(result))
                self.assertNotIn("SSH_AUTH_SOCK", result)

    def test_publish_requires_existing_login_and_does_not_try_login(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(batch.shutil, "which", return_value="/usr/bin/gh"), patch.object(batch.os, "getuid", return_value=1000), patch.object(batch.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
            result = batch.publish_once({"status": "failed"}, 30, Path(tmp))
        self.assertEqual(result, "not-posted-existing-gh-login-required")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][1:3], ["auth", "status"])

    def test_dedicated_uid_cannot_publish_with_misleading_user_environment(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"USER": "ordinary-user"}), patch.object(batch.shutil, "which", return_value="/usr/bin/gh"), patch.object(batch.os, "getuid", return_value=1234), patch.object(batch.pwd, "getpwuid", return_value=SimpleNamespace(pw_name="offmenu-runner")), patch.object(batch.subprocess, "run") as run:
            result = batch.publish_once({"status": "passed"}, 30, Path(tmp))
        self.assertEqual(result, "not-posted-use-normal-user-account")
        run.assert_not_called()

    def test_publish_posts_exactly_once_to_requested_repository(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(batch.shutil, "which", return_value="/usr/bin/gh"), patch.object(batch.os, "getuid", return_value=1000), patch.object(batch.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            result = batch.publish_once({"status": "failed", "steps": [{"stepId": "tests", "exitCode": 2}]}, 30, Path(tmp))
            payload = json.loads((Path(tmp) / "github-report.json").read_text())
            self.assertIn('"exitCode": 2', payload["body"])
        self.assertEqual(result, "posted")
        self.assertEqual(run.call_count, 2)
        posted = run.call_args.args[0]
        self.assertIn("repos/maldous/offmenu/issues/30/comments", posted)
        self.assertIn("POST", posted)

    def test_uncertain_publication_is_never_retried(self):
        calls = [subprocess.CompletedProcess([], 0), subprocess.TimeoutExpired("gh", 60)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(batch.shutil, "which", return_value="/usr/bin/gh"), patch.object(batch.os, "getuid", return_value=1000), patch.object(batch.subprocess, "run", side_effect=calls) as run:
            result = batch.publish_once({"status": "passed"}, 30, Path(tmp))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(result, "post-not-verified-check-github-before-retrying")

    def test_capture_logs_private_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            result = batch.run_step("test", [os.sys.executable, "-c", "import os; os.write(1, b'x'*2097152)"], log_dir)
            self.assertEqual(result["status"], "output-limit")
            self.assertLessEqual((log_dir / "test.stdout").stat().st_size, batch.LOG_LIMIT)
            self.assertEqual((log_dir / "test.stdout").stat().st_mode & 0o777, 0o600)

    def test_timeout_and_actual_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            result = batch.run_step("timeout", [os.sys.executable, "-c", "import time; time.sleep(10)"], log_dir, timeout=0.05)
            failed = batch.run_step("failed", [os.sys.executable, "-c", "raise SystemExit(9)"], log_dir)
        self.assertEqual(result["status"], "timeout")
        self.assertNotEqual(result["exitCode"], 0)
        self.assertEqual(failed["exitCode"], 9)

    def test_main_without_publish_never_calls_github(self):
        with patch.object(batch, "run_batch", return_value={"status": "passed"}), patch.object(batch, "publish_once") as publish, patch.object(batch.os, "getuid", return_value=1000), patch.object(batch.os, "geteuid", return_value=1000), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(batch.main([]), 0)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
