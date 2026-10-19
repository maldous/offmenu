"""Count-only terminal observations; never collection authority or accounting.

Only the owner process writes stderr. Worker activity is sampled at task entry,
not inferred from submitted futures. No URLs, paths, identifiers, exceptions,
headers, or source contents are accepted as display values.
"""
from __future__ import annotations

from contextlib import contextmanager
from collections import deque
import math
import sys
import threading
import time


STAGES = frozenset({"starting", "inventory", "downloads", "verifying", "preparing", "saving",
                    "publishing", "finished", "failed", "interrupted"})
FIELDS = frozenset({
    "download_configured", "download_effective", "download_queued", "download_total",
    "download_completed", "download_reused", "downloaded", "preparation_configured",
    "preparation_effective", "preparation_queued", "preparation_total",
    "preparation_completed", "preparation_reused", "prepared", "failed", "held",
    "network_bytes", "prepared_bytes", "inventory_classified", "inventory_total",
    "coverage_verified", "coverage_total", "verified_original_records",
    "extraction_held_records", "extraction_held_verified_records",
    "retained_preparation_unselected_held", "retained_selected", "retained_verified",
    "retained_verified_payload_bytes",
})
UNKNOWN_INITIAL = frozenset({
    "download_configured", "download_effective", "download_queued", "download_total",
    "preparation_configured", "preparation_effective", "preparation_queued",
    "preparation_total", "held", "network_bytes", "prepared_bytes", "inventory_total",
    "coverage_verified", "coverage_total", "verified_original_records",
    "extraction_held_records", "extraction_held_verified_records",
    "retained_preparation_unselected_held", "retained_selected", "retained_verified",
    "retained_verified_payload_bytes",
})


def asset_record_counts(outcomes):
    """Count outcome records, including aliases, without implying unique files.

    Verified custody is independent of extraction readiness or failure. The
    verified extraction-held subset requires verified custody and the explicit
    extraction-held outcome. A hold does not establish a publisher prohibition:
    the selected preparation scope may leave extraction unselected.
    Only these integer counts may be passed to the reporter.
    """
    counts = {"failed": 0, "held": 0, "verified_original_records": 0,
              "extraction_held_records": 0, "extraction_held_verified_records": 0}
    for row in outcomes:
        verified = row["custody"] == "verified-original"
        held = row["stage"] == "held"
        counts["failed"] += row["stage"] == "error"
        counts["held"] += held
        counts["verified_original_records"] += verified
        extraction_held = held and row["code"] == "extract-permission-held"
        counts["extraction_held_records"] += extraction_held
        counts["extraction_held_verified_records"] += verified and extraction_held
    return counts


class SharedActivity:
    """Single-writer byte slots shared with spawned preparation workers.

Each submitted job owns one slot, written only by its worker. The parent may
clear a slot only AFTER that future completes or its worker has been joined.
No IPC queue, feeder, shared lock, or child-held lock can block collection or
deadline cleanup. Counts are sampled observations, not durable accounting.
"""

    def __init__(self, context, jobs):
        if type(jobs) is not int or not 0 <= jobs <= 10000:
            raise ValueError("invalid-progress-capacity")
        self.slots = context.RawArray("B", jobs)
        self._uncertain = False

    @contextmanager
    def running(self, slot):
        self.slots[slot] = 1
        try:
            yield
        finally:
            self.slots[slot] = 0

    def clear_completed(self, slot):
        self.slots[slot] = 0

    def mark_uncertain(self):
        self._uncertain = True

    def confirm_all_stopped(self):
        """Call only after every owned worker has been joined or shut down."""
        for slot in range(len(self.slots)):
            self.slots[slot] = 0
        self._uncertain = False

    def count(self):
        if self._uncertain:
            return None
        # A single byte has no torn integer reads. Retry a changing sample and
        # report unknown rather than inventing a synchronized point-in-time count.
        previous = bytes(self.slots)
        for _ in range(3):
            current = bytes(self.slots)
            if previous == current:
                return sum(current)
            previous = current
        return None


_worker_activity = None


def initialize_preparation_worker(storage, activity):
    """Keep the existing parser storage lock; add only shared observations."""
    from . import media_preparation
    global _worker_activity
    media_preparation.configure_storage_lock(storage)
    _worker_activity = activity


def prepare_asset_observed(slot, *args, **kwargs):
    from . import media_preparation
    with _worker_activity.running(slot):
        return media_preparation.prepare_asset(*args, **kwargs)


def prepare_function_observed(activity, slot, prepare, *args):
    with activity.running(slot):
        return prepare(*args)


class ProgressReporter:
    """Flushed, bounded-cadence stderr lines, including non-TTY terminals.

    Start, changed stage, and stop emit immediately. Ordinary counter changes
    are sampled at most once per interval (default five seconds). Broken stderr
    disables presentation without changing collection decisions or results.
    """

    def __init__(self, *, stream=None, interval=5.0, clock=time.monotonic):
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or not math.isfinite(interval) or interval < 0.05:
            raise ValueError("invalid-progress-interval")
        self.stream = sys.stderr if stream is None else stream
        self.interval = interval
        self.clock = clock
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._initial_flushed = threading.Event()
        self._pending = deque(maxlen=16)
        self._thread = None
        self._started = None
        self._closed = False
        self._sink_failed = False
        self._stage = "starting"
        self._execution_stage = None
        self._download_active = 0
        self._preparation_activity = None
        self._network_meter = None
        self._values = {key: None if key in UNKNOWN_INITIAL else 0 for key in FIELDS}

    def start(self):
        with self._lock:
            if self._started is not None or self._closed:
                return self
            self._started = self.clock()
            self._pending.append(self._snapshot_locked())
            self._wake.set()
            self._thread = threading.Thread(target=self._run, name="collection-progress", daemon=True)
            self._thread.start()
        self._initial_flushed.wait(timeout=0.2)
        return self

    def _run(self):
        while True:
            self._wake.wait(self.interval)
            self._wake.clear()
            with self._lock:
                snapshots = list(self._pending) or [self._snapshot_locked()]
                self._pending.clear()
                closed = self._closed
            # Never hold the state lock or block a collection worker on stderr.
            # A stalled terminal can stall only this daemon presentation thread.
            for snapshot in snapshots:
                self._emit(snapshot)
                self._initial_flushed.set()
            if closed:
                return

    def update(self, **values):
        if set(values) - FIELDS or any(value is not None and (type(value) is not int or not 0 <= value <= 2**63 - 1) for value in values.values()):
            raise ValueError("invalid-progress-count")
        with self._lock:
            if not self._closed:
                self._values.update(values)

    def increment(self, **values):
        if set(values) - FIELDS or any(type(value) is not int or not 0 <= value <= 10000 for value in values.values()):
            raise ValueError("invalid-progress-count")
        with self._lock:
            if not self._closed:
                for key, value in values.items():
                    self._values[key] = (self._values[key] or 0) + value

    def observe(self, *, preparation_activity=None, network_meter=None):
        with self._lock:
            self._preparation_activity = preparation_activity
            self._network_meter = network_meter

    def stage(self, stage):
        if stage not in STAGES:
            raise ValueError("invalid-progress-stage")
        with self._lock:
            if not self._closed and stage != self._stage:
                self._stage = stage
                if self._started is not None:
                    self._pending.append(self._snapshot_locked())
                    self._wake.set()

    def execution_stage(self, stage):
        """Select only the collector-validated fetch or parse display context."""
        if stage not in {"fetch", "parse"}:
            raise ValueError("invalid-progress-execution-stage")
        with self._lock:
            if not self._closed and stage != self._execution_stage:
                self._execution_stage = stage
                if self._started is not None:
                    self._pending.append(self._snapshot_locked())
                    self._wake.set()

    def _download_change(self, change):
        with self._lock:
            self._download_active = max(0, self._download_active + change)

    def wrap_transport(self, transport):
        def observed(*args, **kwargs):
            self._download_change(1)
            try:
                response = transport(*args, **kwargs)
            except BaseException:
                self._download_change(-1)
                raise
            return _ObservedResponse(response, self)
        return observed

    def snapshot(self):
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self):
        values = dict(self._values)
        values.update(stage=self._stage, execution_stage=self._execution_stage, download_active=self._download_active,
                      preparation_active=0, elapsed_seconds=max(0, int(self.clock() - self._started)) if self._started is not None else 0)
        if self._preparation_activity is not None:
            values["preparation_active"] = self._preparation_activity.count()
        if self._network_meter is not None:
            # Only this explicitly selected integer crosses the display boundary.
            count = self._network_meter.snapshot().get("bodyBytesRead")
            values["network_bytes"] = count if type(count) is int and count >= 0 else None
        return values

    def _emit(self, values):
        if self._sink_failed:
            return
        def value(key):
            number = values[key]
            return "unknown" if number is None else str(number)
        def difference(total, subset):
            first, second = values[total], values[subset]
            return "unknown" if first is None or second is None or second > first else str(first - second)
        execution = values["execution_stage"]
        worker_label = "verification" if execution == "fetch" else "parse" if execution == "parse" else "prep"
        if execution == "parse":
            acquisition = (
                f" | acquisition jobs={value('download_total')} completed={value('download_completed')}"
                f" queued={value('download_queued')} active={value('download_active')}"
            )
        else:
            acquisition = (
                f" | download active={value('download_active')} effective={value('download_effective')} configured={value('download_configured')}"
                f" queued={value('download_queued')} completed={value('download_completed')}/{value('download_total')}"
                f" downloaded={value('downloaded')} reused={value('download_reused')}"
            )
        line = (
            f"OffMenu {execution or 'pass'} stage={values['stage']} elapsed={value('elapsed_seconds')}s"
            + acquisition
            + f" | {worker_label} active={value('preparation_active')} effective={value('preparation_effective')} configured={value('preparation_configured')}"
            f" queued={value('preparation_queued')} completed={value('preparation_completed')}/{value('preparation_total')}"
        )
        if execution != "fetch":
            line += f" prepared-ready-total={value('prepared')} new={difference('prepared', 'preparation_reused')} reused={value('preparation_reused')}"
        line += f" | asset records verified-original-records={value('verified_original_records')} (aliases included)"
        if execution == "fetch":
            line += f" failed-collection={value('failed')} held-collection={value('held')}"
        else:
            line += (
                f" failed-stage={value('failed')} held-stage={value('held')}"
                f" extraction-held-stage={value('extraction_held_records')} verified-extraction-held={value('extraction_held_verified_records')} other-held-stage={difference('held', 'extraction_held_records')}"
            )
        line += f" | bytes network-body-read={value('network_bytes')}"
        if execution != "fetch":
            line += f" new-preparation-storage-known={value('prepared_bytes')} (includes partial output)"
        payload_label = "local custody payloads" if execution == "parse" else "retained payloads"
        line += (
            f" | {payload_label} completed-verified={value('retained_verified')}/{value('retained_selected')}"
            f" verified-payload-bytes={value('retained_verified_payload_bytes')} (excludes other local I/O)"
        )
        if execution != "fetch":
            line += f" preparation-unselected-held={value('retained_preparation_unselected_held')}"
        line += (
            f" | inventory classified={value('inventory_classified')}/{value('inventory_total')}"
            f" | coverage verified={value('coverage_verified')}/{value('coverage_total')}\n"
        )
        try:
            self.stream.write(line)
            self.stream.flush()
        except (OSError, ValueError):
            self._sink_failed = True

    def stop(self, stage="finished"):
        if stage not in {"finished", "failed", "interrupted"}:
            raise ValueError("invalid-progress-stage")
        with self._lock:
            if self._closed:
                return
            self._stage = stage
            self._closed = True
            if self._started is not None:
                self._pending.append(self._snapshot_locked())
                self._wake.set()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.2)


class _ObservedResponse:
    """Preserve transport behavior, counting only open request/response work."""

    def __init__(self, response, reporter):
        self._response = response
        self._reporter = reporter
        self._active = True

    def __getattr__(self, name):
        return getattr(self._response, name)

    def _finish(self):
        if self._active:
            self._active = False
            self._reporter._download_change(-1)

    def read(self, *args, **kwargs):
        try:
            block = self._response.read(*args, **kwargs)
        except BaseException:
            self._finish()
            raise
        if not block:
            self._finish()
        return block

    def close(self):
        try:
            return self._response.close()
        finally:
            self._finish()
