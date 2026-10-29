import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


host = load("runner_host_setup", ROOT / "tools/operations/runner_host_setup.py")
jobs = load("dispatch_foo_job", ROOT / "tools/operations/dispatch_foo_job.py")


class SetupTests(unittest.TestCase):
    def test_default_is_read_only_and_never_contacts_network(self):
        with patch.object(host, "preflight", return_value={"status": "preflight"}), patch.object(host, "install_runner") as install, patch.object(host, "register_runner") as register, patch.object(host, "publish_report") as publish, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(host.main([]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "preflight")
        install.assert_not_called(); register.assert_not_called(); publish.assert_not_called()

    def test_pinned_official_assets(self):
        self.assertEqual(host.VERSION, "2.337.0")
        self.assertEqual(host.ASSETS["x86_64"][1], "70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613")
        self.assertEqual(host.ASSETS["aarch64"][1], "9b1dc70626422526e3c94767cf024896beb15da5342a3f4819bf2feac13e0393")

    def test_scrubbed_environment(self):
        with patch.dict(os.environ, {"GH_TOKEN": "do-not-leak", "SSH_AUTH_SOCK": "/secret/agent", "AWS_SECRET_ACCESS_KEY": "do-not-leak"}):
            result = host.minimal_env()
        self.assertNotIn("do-not-leak", json.dumps(result))
        self.assertEqual(set(result), {"HOME", "USER", "LOGNAME", "PATH", "LANG", "PYTHONDONTWRITEBYTECODE"})

    def test_cache_root_rejects_broad_paths_and_injection(self):
        for path in ("/", "/home", "/root", "/tmp/a\nUser=root", "/tmp/%h", "/tmp/a:b", "/tmp/../etc"):
            with self.subTest(path=path), self.assertRaises(host.SetupError):
                host.cache_source(path)

    def test_cache_root_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "link").symlink_to(root / "data")
            with self.assertRaises(host.SetupError):
                host.cache_source(str(root / "link"))

    def test_service_confines_runtime_and_starts_as_user(self):
        unit = host.service_text(Path("/dataset/cache"))
        for setting in ("User=offmenu-runner", "Group=offmenu-runner", "NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=tmpfs", "PrivateTmp=yes", "CapabilityBoundingSet=", "BindReadOnlyPaths=/dataset/cache:/srv/offmenu-refresh/cache", "ReadWritePaths=/srv/offmenu-runner /srv/offmenu-refresh/outputs", "KillMode=control-group"):
            self.assertIn(setting, unit)
        self.assertNotIn("sudo", unit)
        self.assertNotIn("GITHUB_TOKEN", unit)

    def test_existing_directory_modes_must_already_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            host.validate_host_directory(root, os.getuid(), os.getgid(), 0o700)
            with self.assertRaises(host.SetupError):
                host.validate_host_directory(root, os.getuid(), os.getgid(), 0o755)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)

    def test_cache_placeholder_must_be_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o755)
            host.validate_host_directory(root, os.getuid(), os.getgid(), 0o755, empty=True)
            (root / "unrelated").write_text("preserve")
            with self.assertRaises(host.SetupError):
                host.validate_host_directory(root, os.getuid(), os.getgid(), 0o755, empty=True)
            self.assertEqual((root / "unrelated").read_text(), "preserve")

    def test_tar_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "a.tar.gz"
            with tarfile.open(archive, "w:gz") as f:
                info = tarfile.TarInfo("../escape")
                info.size = 1
                f.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(host.SetupError):
                host.safe_extract(archive, root / "out")
            self.assertFalse((root / "escape").exists())

    def test_tar_absolute_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "a.tar.gz"
            with tarfile.open(archive, "w:gz") as f:
                info = tarfile.TarInfo("link")
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc"
                f.addfile(info)
            with self.assertRaises(host.SetupError):
                host.safe_extract(archive, root / "out")

    def test_unrecognized_existing_install_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "actions-runner"
            runner.mkdir()
            (runner / "keep").write_text("do not delete")
            with patch.object(host, "RUNNER_HOME", root), patch.object(host, "RUNNER_DIR", runner), patch.object(host, "require_host"), patch.object(host, "require_runner_identity"), patch.object(host.platform, "machine", return_value="x86_64"), patch.object(host.subprocess, "run") as network, self.assertRaises(host.SetupError):
                host.install_runner()
            network.assert_not_called()
            self.assertEqual((runner / "keep").read_text(), "do not delete")

    def test_valid_existing_install_is_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "actions-runner"
            runner.mkdir()
            for name in ("config.sh", "runsvc.sh"):
                (runner / name).write_text("existing")
            (runner / ".offmenu-install.json").write_text(json.dumps({"repository": host.REPO, "initialVersion": host.VERSION, "sha256": host.ASSETS["x86_64"][1]}))
            with patch.object(host, "RUNNER_HOME", root), patch.object(host, "RUNNER_DIR", runner), patch.object(host, "require_host"), patch.object(host, "require_runner_identity"), patch.object(host.platform, "machine", return_value="x86_64"), patch.object(host.subprocess, "run") as network, contextlib.redirect_stdout(io.StringIO()):
                host.install_runner()
            network.assert_not_called()

    def test_registration_requires_local_tty_without_reading_a_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".offmenu-install.json").write_text("{}")
            with patch.object(host, "RUNNER_DIR", root), patch.object(host, "require_runner_identity"), patch.object(host.sys.stdin, "isatty", return_value=False), patch.object(host.subprocess, "run") as config, self.assertRaises(host.SetupError):
                host.register_runner()
            config.assert_not_called()


class QueueTests(unittest.TestCase):
    def request(self, profile="smoke", job_id="foo-test-001"):
        return {"schemaVersion": 1, "jobId": job_id, "profile": profile}

    def test_exact_schema_and_profiles(self):
        self.assertEqual(jobs.parse_request(json.dumps(self.request()).encode()), self.request())
        for value in (self.request() | {"command": "rm -rf /"}, self.request(profile="shell"), self.request(job_id="../../home"), self.request() | {"profile": []}, self.request() | {"schemaVersion": True}):
            with self.subTest(value=value), self.assertRaises(jobs.JobError):
                jobs.parse_request(json.dumps(value).encode())

    def test_duplicate_keys_and_overlimit_refused(self):
        for raw in (b'{"schemaVersion":1,"jobId":"foo-test-001","profile":"smoke","profile":"readiness"}', b" " * 1025):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(raw)

    def test_no_arbitrary_commands_from_request(self):
        for profile in jobs.PROFILES:
            for _, _, command in jobs.profile_steps(profile, ROOT, "a" * 40):
                self.assertIsInstance(command, list)
                self.assertNotIn("bash", command)
                self.assertNotIn("sudo", command)
                self.assertNotIn("gh", command)

    def test_smoke_independent_steps_continue_and_dependents_skip(self):
        calls = []
        def fake(command, code, timeout=240):
            calls.append(command)
            status = "failed" if "unittest" in command else "passed"
            return {"status": status, "exitCode": 1 if status == "failed" else 0, "durationSeconds": 0.01, "evidence": {}}
        with patch.object(jobs, "run_child", side_effect=fake):
            result = jobs.run_profile(self.request(), "a" * 40, ROOT, "123", "1")
        self.assertEqual(result["status"], "failed")
        self.assertEqual([s["status"] for s in result["steps"]], ["passed", "passed", "failed", "skipped", "skipped"])
        self.assertEqual(len(calls), 3)

    def test_inventory_failure_does_not_skip_independent_tests_and_replay(self):
        def fake(command, code, timeout=240):
            status = "failed" if "inventory" in command else "passed"
            return {"status": status, "exitCode": int(status == "failed"), "durationSeconds": 0.01, "evidence": {"resultAction": "verified-no-op"}}
        with patch.object(jobs, "run_child", side_effect=fake):
            report = jobs.run_profile(self.request(), "a" * 40, ROOT, "123", "1")
        self.assertEqual(report["status"], "failed")
        self.assertEqual([s["status"] for s in report["steps"]], ["passed", "failed", "passed", "passed", "passed"])

    def test_failure_not_masked_by_last_step_success(self):
        with patch.object(jobs, "run_child", return_value={"status": "failed", "exitCode": 17, "durationSeconds": 0, "evidence": {}}):
            report = jobs.run_profile(self.request(), "a" * 40, ROOT, "123", "1")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["steps"][0]["exitCode"], 17)

    def test_cancelled_distinct_and_remaining_skipped(self):
        with patch.object(jobs, "run_child", return_value={"status": "cancelled", "exitCode": 130, "durationSeconds": 0, "evidence": {}}):
            report = jobs.run_profile(self.request(), "a" * 40, ROOT, "123", "1")
        self.assertEqual(report["status"], "cancelled")
        self.assertTrue(all(s["skipReason"] == "job-cancelled" for s in report["steps"][1:]))

    def test_raw_output_is_not_published(self):
        secret = b'{"secret":"ghp_PRIVATE_EXAMPLE","path":"/home/private/data"}'
        evidence = jobs.safe_evidence(secret)
        self.assertNotIn("PRIVATE", json.dumps(evidence))
        self.assertNotIn("/home", json.dumps(evidence))
        self.assertEqual(evidence["stdoutBytes"], len(secret))

    def test_malformed_evidence_shapes_are_safe(self):
        for value in ({"schemaVersion": "offmenu-refresh-inventory/1", "counts": []},
                      {"status": []}, {"action": {}}, {"errorCode": []}):
            evidence = jobs.safe_evidence(json.dumps(value).encode())
            self.assertIn("stdoutSha256", evidence)

    def test_output_capture_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "OUTPUT", Path(tmp)):
            (Path(tmp) / "tmp").mkdir()
            result = jobs.run_child([os.sys.executable, "-c", "import os; os.write(1, b'x' * 2097152)"], ROOT)
        self.assertEqual((result["status"], result["exitCode"]), ("output-limit", 125))
        self.assertLessEqual(result["evidence"]["stdoutBytes"], jobs.MAX_CHILD_OUTPUT)

    def test_privileged_destination_symlinks_and_writable_ancestors_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target").write_text("unrelated")
            (root / "link").symlink_to(root / "target")
            with self.assertRaises(host.SetupError):
                host.validate_privileged_destination(root / "link", b"replacement")
            self.assertEqual((root / "target").read_text(), "unrelated")

    def test_receipt_reuse_does_not_execute_twice(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "OUTPUT", Path(tmp)):
            report = {"schemaVersion": 1, "status": "passed", "steps": []}
            with patch.object(jobs, "run_profile", return_value=report.copy()) as run:
                jobs.execute(self.request(), "a" * 40, ROOT, "123", "1")
                result = jobs.execute(self.request(), "a" * 40, ROOT, "124", "1")
                self.assertEqual(run.call_count, 1)
            self.assertEqual(result["delivery"], "existing-receipt-no-execution")

    def test_reused_job_id_for_different_profile_fails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "OUTPUT", Path(tmp)), patch.object(jobs, "run_profile", return_value={"schemaVersion": 1, "status": "passed", "steps": []}):
            jobs.execute(self.request(), "a" * 40, ROOT, "123", "1")
            with self.assertRaises(jobs.JobError):
                jobs.execute(self.request(profile="inventory"), "a" * 40, ROOT, "124", "1")

    def test_kernel_lock_released_after_exception(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "OUTPUT", Path(tmp)):
            with patch.object(jobs, "run_profile", side_effect=RuntimeError("synthetic crash")), self.assertRaises(RuntimeError):
                jobs.execute(self.request(), "a" * 40, ROOT, "123", "1")
            with patch.object(jobs, "run_profile", return_value={"schemaVersion": 1, "status": "passed", "steps": []}):
                report = jobs.execute(self.request(), "a" * 40, ROOT, "124", "1")
            self.assertEqual(report["status"], "passed")

    def test_timeout_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, "OUTPUT", Path(tmp)):
            (Path(tmp) / "tmp").mkdir()
            timeout = jobs.run_child([os.sys.executable, "-c", "import time; time.sleep(20)"], ROOT, timeout=0.05)
            failed = jobs.run_child([os.sys.executable, "-c", "raise SystemExit(7)"], ROOT)
        self.assertEqual((timeout["status"], timeout["exitCode"]), ("timeout", 124))
        self.assertEqual((failed["status"], failed["exitCode"]), ("failed", 7))


if __name__ == "__main__":
    unittest.main()
