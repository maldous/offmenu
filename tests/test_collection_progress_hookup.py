"""Offline hookup fixtures: no downloads, publication, or installed file edits."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from offmenu.refresh.collection_progress import ProgressReporter
import test_global_collection as fixture


ROOT = Path(__file__).resolve().parents[1]
g = fixture.g


class HookupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.GlobalTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.output = io.StringIO()
        self.reporter = ProgressReporter(stream=self.output, interval=0.05).start()
        self.addCleanup(self.reporter.stop)

    def retained(self, count=2, bad_last=False):
        f = self.fixture
        f.selected.update(sources=[], maximumRequests=0, maximumTransferBytes=0, preparation=[])
        for index in range(count):
            bad = bad_last and index == count - 1
            raw = b"not JSON" if bad else b"a,b\n1,2\n" * 1000
            path = f.root / ("progress-synthetic-" + str(index))
            path.write_bytes(raw)
            contract = {
                "schemaVersion": g.media.SCHEMA,
                "assetId": f.manifest["assets"][index]["assetId"],
                "expectedSHA256": fixture.f.a.sha(raw), "expectedBytes": len(raw),
                "expectedMediaTypes": ["application/json"] if bad else ["text/csv"],
                "permissions": {"read": True, "extract": True, "copy": True}, "holds": [],
                "parameters": {} if bad else {"encoding": "utf-8", "delimiter": ",", "hasHeader": True},
            }
            f.manifest["assets"][index].update(
                disposition="retained",
                retainedOriginal={"path": str(path), "sha256": fixture.f.a.sha(raw), "bytes": len(raw)},
                preparationContract=contract,
            )

    def test_download_results_reuse_and_inventory_never_imply_coverage(self):
        f = self.fixture
        first = f.clean_global(f.execute(terminal=self.reporter))
        state = self.reporter.snapshot()
        self.assertEqual(state["download_active"], 0)
        self.assertEqual(state["download_completed"], 5)
        self.assertEqual(state["downloaded"], 5)
        self.assertEqual(state["network_bytes"], first["networkBytesRead"])
        self.assertEqual(state["held"], 1)
        self.assertEqual(state["inventory_classified"], 9)
        self.assertEqual(state["coverage_total"], 3237)
        self.assertIsNone(state["coverage_verified"])
        reporter = ProgressReporter(stream=io.StringIO()).start()
        self.addCleanup(reporter.stop)
        second = f.clean_global(f.execute(terminal=reporter))
        self.assertEqual(second["networkRequests"], 0)
        self.assertEqual(reporter.snapshot()["download_reused"], 5)
        self.assertEqual(reporter.snapshot()["downloaded"], 0)
        self.assertEqual(reporter.snapshot()["download_active"], 0)

    def test_real_spawn_preparation_counts_errors_and_cache_reuse(self):
        self.retained(3, bad_last=True)
        first = self.fixture.clean_global(self.fixture.execute(terminal=self.reporter))
        state = self.reporter.snapshot()
        self.assertEqual(state["preparation_completed"], 3)
        self.assertEqual(state["preparation_total"], 3)
        self.assertEqual(state["preparation_active"], 0)
        self.assertEqual(state["prepared"], 2)
        self.assertEqual(state["failed"], 1)
        self.assertEqual(state["prepared_bytes"], first["preparedBytes"])
        reporter = ProgressReporter(stream=io.StringIO()).start()
        self.addCleanup(reporter.stop)
        second = self.fixture.clean_global(self.fixture.execute(terminal=reporter))
        self.assertEqual(second["preparedBytes"], 0)
        self.assertEqual(reporter.snapshot()["preparation_reused"], 2)
        self.assertEqual(reporter.snapshot()["prepared"], 2)

    def test_zero_preparation_capacity_never_claims_active_worker(self):
        self.retained(1)
        resources = dict(g.effective_resources(g.DEFAULT_PARALLELISM))
        resources["preparationWorkers"] = 0
        with patch.object(g, "effective_resources", return_value=resources):
            report = self.fixture.execute(terminal=self.reporter)
        state = self.reporter.snapshot()
        self.assertEqual(state["preparation_active"], 0)
        self.assertEqual(state["preparation_effective"], 0)
        self.assertEqual(state["preparation_configured"], 8)
        self.assertEqual(state["preparation_completed"], 1)
        self.assertEqual(state["failed"], 1)
        self.assertEqual(report["changes"][0]["preparation"], None)

    def test_worker_activity_is_entry_not_submission(self):
        self.retained(2)
        started = threading.Barrier(3)
        release = threading.Event()
        result = []
        def prepare(asset, contract, path, folder, deadline, maximum):
            started.wait(timeout=5)
            release.wait(timeout=5)
            return {
                "status": "unsupported", "errorCode": "parser-unavailable",
                "stages": {"integrity": "passed", "media": "passed", "extraction": "unsupported"},
                "actualMediaType": "text/csv", "originalSHA256": contract["expectedSHA256"],
                "originalBytes": contract["expectedBytes"], "outputs": [],
                "nextStageReady": False, "metrics": {},
            }, None, 0
        thread = threading.Thread(target=lambda: result.append(self.fixture.execute(prepare=prepare, terminal=self.reporter)))
        thread.start()
        try:
            started.wait(timeout=5)
            self.assertEqual(self.reporter.snapshot()["preparation_active"], 2)
            self.assertEqual(self.reporter.snapshot()["preparation_completed"], 0)
            release.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(self.reporter.snapshot()["preparation_active"], 0)
            self.assertEqual(self.reporter.snapshot()["preparation_completed"], 2)
            self.assertEqual(result[0]["observedPeakPreparations"], 2)
        finally:
            release.set()
            thread.join(timeout=5)

    def test_deadline_cleanup_keeps_final_activity_zero(self):
        self.retained(1)
        with patch.object(g, "MAX_SECONDS", 20.01):
            report = self.fixture.execute(terminal=self.reporter)
        self.assertEqual(report["networkRequests"], 0)
        self.assertEqual(self.reporter.snapshot()["preparation_active"], 0)

    def test_main_stdout_is_one_machine_json_and_stderr_finishes(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = g.main(["--invalid-synthetic-argument"])
        self.assertEqual(code, 2)
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertNotIn("OffMenu", stdout.getvalue())
        self.assertIn("stage=starting", stderr.getvalue())
        self.assertIn("stage=failed", stderr.getvalue())
        self.assertNotIn("--invalid", stderr.getvalue())

    def test_interrupt_emits_final_status_without_exception_text(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(g, "_main", side_effect=KeyboardInterrupt("synthetic-private-message")), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(KeyboardInterrupt):
                g.main([])
        self.assertIn("stage=interrupted", stderr.getvalue())
        self.assertNotIn("synthetic-private-message", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def test_real_launcher_exec_preserves_stdout_and_live_stderr(self):
        with tempfile.TemporaryDirectory() as name:
            home = Path(name)
            root = home / "offmenu-global-collection"
            source = root / "sources" / ("a" * 40)
            (source / "scripts").mkdir(parents=True)
            (root / "pins").mkdir()
            root.chmod(0o700)
            (root / "pins" / ("a" * 40 + ".json")).write_text(json.dumps({"commit": "a" * 40, "tree": "b" * 40}))
            (source / "scripts/collect-fixed-global.py").write_text(
                "import json,sys\nprint('synthetic-live-progress',file=sys.stderr,flush=True)\nprint(json.dumps({'synthetic':True}))\n"
            )
            driver = (
                "import importlib.util\n"
                f"spec=importlib.util.spec_from_file_location('launcher',{str(ROOT / 'scripts/run-global-on-foo.py')!r})\n"
                "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n"
                f"m.__file__={str(source / 'scripts/run-global-on-foo.py')!r}\n"
                f"m.clean_environment=lambda:{{'HOME':{str(home)!r},'PATH':'/usr/bin:/bin'}}\n"
                "m.verify_source=lambda *args:None\n"
                "m.run()\n"
            )
            result = subprocess.run([sys.executable, "-c", driver], text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"synthetic": True})
            self.assertIn("stage=verifying-installation", result.stderr)
            self.assertIn("synthetic-live-progress", result.stderr)

    def test_launcher_startup_sink_failure_or_stall_is_nonfatal(self):
        spec = importlib.util.spec_from_file_location("progress_launcher", ROOT / "scripts/run-global-on-foo.py")
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with patch.object(launcher.os, "write", side_effect=BrokenPipeError("synthetic-private-error")):
            launcher.announce_progress()
        entered, release = threading.Event(), threading.Event()
        def stalled(*_):
            entered.set()
            release.wait(5)
        try:
            with patch.object(launcher.os, "write", side_effect=stalled):
                started = time.monotonic()
                launcher.announce_progress()
                self.assertTrue(entered.is_set())
                self.assertLess(time.monotonic() - started, 0.8)
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
