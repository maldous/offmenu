"""Offline count-only progress, concurrency, and process cleanup tests."""
from concurrent.futures import ThreadPoolExecutor
import io
import multiprocessing
import threading
import time
import unittest

from offmenu.refresh.collection_progress import ProgressReporter, SharedActivity


class Stream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def isatty(self):
        return False

    def flush(self):
        self.flushes += 1
        super().flush()


def process_activity(activity, slot, entered, release, fail=False):
    try:
        with activity.running(slot):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("synthetic-timeout")
            if fail:
                raise RuntimeError("synthetic-error")
    except RuntimeError:
        pass


class ProgressTests(unittest.TestCase):
    def reporter(self, **kwargs):
        stream = Stream()
        reporter = ProgressReporter(stream=stream, **kwargs).start()
        self.addCleanup(reporter.stop)
        return reporter, stream

    def test_immediate_start_stage_final_flush_and_non_tty(self):
        clock = [100.0]
        reporter, stream = self.reporter(clock=lambda: clock[0])
        self.assertIn("stage=starting", stream.getvalue())
        reporter.update(download_configured=8, download_effective=2, download_total=6,
                        download_queued=6, coverage_total=3237, inventory_total=10)
        clock[0] = 107.0
        reporter.stage("downloads")
        reporter.update(download_queued=0, download_completed=6, download_reused=6,
                        inventory_classified=10)
        reporter.stop()
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("stage=downloads elapsed=7s", lines[1])
        self.assertIn("active=0 effective=2 configured=8", lines[1])
        self.assertIn("queued=0 completed=6/6 downloaded=0 reused=6", lines[-1])
        self.assertIn("inventory classified=10/10", lines[-1])
        self.assertIn("coverage verified=unknown/3237", lines[-1])
        self.assertEqual(stream.flushes, len(lines))
        self.assertNotIn("\r", stream.getvalue())
        self.assertNotIn("\x1b", stream.getvalue())
        reporter.stop()
        self.assertEqual(len(stream.getvalue().splitlines()), 3)

    def test_periodic_output_is_bounded_not_per_event(self):
        reporter, stream = self.reporter(interval=0.05)
        for _ in range(5000):
            reporter.increment(download_completed=1)
        time.sleep(0.16)
        reporter.stop()
        self.assertLessEqual(len(stream.getvalue().splitlines()), 7)
        self.assertGreaterEqual(len(stream.getvalue().splitlines()), 3)
        self.assertEqual(reporter.snapshot()["download_completed"], 5000)

    def test_unknown_totals_and_zero_workers_are_not_percentages(self):
        reporter, stream = self.reporter()
        reporter.update(preparation_configured=8, preparation_effective=0)
        reporter.stage("preparing")
        reporter.stop("failed")
        text = stream.getvalue()
        self.assertIn("prep active=0 effective=0 configured=8", text)
        self.assertIn("completed=0/unknown", text)
        for forbidden in ("%", "ETA", "MB/s", "throughput"):
            self.assertNotIn(forbidden, text)

    def test_concurrent_downloads_count_actual_transport_entry_and_eof(self):
        reporter, _ = self.reporter()
        barrier = threading.Barrier(9)
        release = threading.Event()
        class Response:
            status = 200
            headers = {"Authorization": "synthetic-secret"}
            def read(self, *_):
                return b""
            def close(self):
                pass
        transport = reporter.wrap_transport(lambda *_: Response())
        def worker(_):
            response = transport("https://example.invalid/?signed=synthetic-secret")
            barrier.wait(timeout=3)
            release.wait(timeout=3)
            response.read(1)
            response.close()
            response.close()
            reporter.increment(download_completed=1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            barrier.wait(timeout=3)
            self.assertEqual(reporter.snapshot()["download_active"], 8)
            release.set()
            for future in futures:
                future.result(timeout=3)
        self.assertEqual(reporter.snapshot()["download_active"], 0)
        self.assertEqual(reporter.snapshot()["download_completed"], 8)

    def test_transport_errors_balance_activity_and_preserve_exception(self):
        reporter, stream = self.reporter()
        failure = OSError("synthetic-private-error")
        def raises(*_):
            raise failure
        with self.assertRaises(OSError) as result:
            reporter.wrap_transport(raises)()
        self.assertIs(result.exception, failure)
        self.assertEqual(reporter.snapshot()["download_active"], 0)
        class Response:
            read = raises
            close = raises
        response = reporter.wrap_transport(lambda: Response())()
        with self.assertRaises(OSError):
            response.read(1)
        with self.assertRaises(OSError):
            response.close()
        self.assertEqual(reporter.snapshot()["download_active"], 0)
        reporter.stop("failed")
        self.assertNotIn("synthetic-private-error", stream.getvalue())

    def test_only_count_schema_crosses_display_boundary(self):
        reporter, stream = self.reporter()
        for values in ({"url": "https://example.invalid/secret"}, {"held": "secret"}, {"held": True}, {"held": -1}):
            with self.assertRaises(ValueError):
                reporter.update(**values)
        with self.assertRaises(ValueError):
            reporter.stage("https://example.invalid/secret")
        class Meter:
            def snapshot(self):
                return {"bodyBytesRead": 42, "Authorization": "synthetic-secret"}
        reporter.observe(network_meter=Meter())
        reporter.stop()
        self.assertIn("bytes network-body-read=42", stream.getvalue())
        self.assertNotIn("secret", stream.getvalue())
        self.assertNotIn("http", stream.getvalue())

    def test_broken_stderr_is_nonfatal(self):
        class Broken:
            def write(self, _):
                raise BrokenPipeError("synthetic-secret")
            def flush(self):
                raise AssertionError("unreachable")
        reporter = ProgressReporter(stream=Broken()).start()
        reporter.update(download_completed=2)
        reporter.stage("downloads")
        reporter.stop("failed")
        self.assertEqual(reporter.snapshot()["download_completed"], 2)

    def test_stalled_sink_cannot_block_collection_events_or_shutdown(self):
        entered, release = threading.Event(), threading.Event()
        class Stalled:
            def write(self, _):
                entered.set()
                release.wait(5)
            def flush(self):
                pass
        start = time.monotonic()
        reporter = ProgressReporter(stream=Stalled()).start()
        try:
            self.assertTrue(entered.wait(1))
            reporter.update(download_completed=1)
            reporter.stage("downloads")
            reporter.stop()
            self.assertLess(time.monotonic() - start, 0.8)
        finally:
            release.set()
            reporter._thread.join(timeout=2)

    def test_spawned_workers_signal_entry_exit_and_exception(self):
        ctx = multiprocessing.get_context("spawn")
        activity = SharedActivity(ctx, 2)
        entered = [ctx.Event(), ctx.Event()]
        release = ctx.Event()
        processes = [ctx.Process(target=process_activity, args=(activity, i, entered[i], release, bool(i))) for i in range(2)]
        try:
            for process in processes:
                process.start()
            for event in entered:
                self.assertTrue(event.wait(5))
            self.assertEqual(activity.count(), 2)
            release.set()
            for process in processes:
                process.join(5)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(activity.count(), 0)
        finally:
            release.set()
            for process in processes:
                if process.is_alive():
                    process.kill()
                process.join(2)

    def test_killed_worker_has_no_orphaned_progress_lock(self):
        ctx = multiprocessing.get_context("spawn")
        activity = SharedActivity(ctx, 1)
        entered, release = ctx.Event(), ctx.Event()
        process = ctx.Process(target=process_activity, args=(activity, 0, entered, release))
        process.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertEqual(activity.count(), 1)
            activity.mark_uncertain()
            self.assertIsNone(activity.count())
            process.terminate()
            process.join(5)
            self.assertFalse(process.is_alive())
            activity.confirm_all_stopped()
            self.assertEqual(activity.count(), 0)
        finally:
            if process.is_alive():
                process.kill()
                process.join(2)
        self.assertEqual(SharedActivity(ctx, 0).count(), 0)


if __name__ == "__main__":
    unittest.main()
