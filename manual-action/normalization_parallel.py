"""Bounded, persistent CPU workers for DB-only public-record normalization.

Only JSON envelopes from the caller's bounded database batch cross local IPC.
Workers use spawn (never fork), own no database handles, and call run_rules with
store=None. Original payloads are transient; compact artifacts leave workers
without source_original. No raw exception text enters returned errors/metrics.
The parent alone owns immutable writes, source binding checks and checkpoints.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, TimeoutError
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
import json
import math
import multiprocessing
import os
import time

PUBLIC_DOMAINS = frozenset(('barcodes', 'ingredients', 'recipes', 'dietary',
                            'suppliers', 'citations'))
SOURCE_KEYS = ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256')
MAX_WORKERS = 22
MAX_BATCH_ROWS = 128
DEFAULT_BYTES = 4 * 1024 * 1024
MAX_BYTES = 16 * 1024 * 1024
ERROR_CODES = frozenset(('outside_public_domain', 'invalid_source_envelope',
    'rules_input_limit', 'source_content_hash_mismatch', 'rules_validation_error',
    'rules_execution_error', 'rules_output_limit'))
_worker_cancel = None


class RulesWorkerError(RuntimeError):
    """Sanitized infrastructure fault: stop globally; do not advance a batch."""


class RulesBatchLimitError(ValueError):
    """Retry the same uncommitted input as smaller batches; never truncate it."""


@dataclass
class RulesStats:
    submitted_tasks: int = 0
    completed_tasks: int = 0
    peak_inflight_tasks: int = 0
    worker_restarts: int = 0
    worker_cpu_ns: int = 0
    worker_wall_ns: int = 0
    worker_pids: set = field(default_factory=set)


def available_workers(requested=16):
    """Leave a configurable CPU allowance; 22 is the hard cap, not a default."""
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 1:
        raise ValueError('invalid_rules_workers')
    try:
        available = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        available = os.cpu_count() or 1
    return min(requested, MAX_WORKERS, max(1, available))


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _identity(record):
    if not isinstance(record, dict):
        return {key: None for key in SOURCE_KEYS}
    # Malformed identities cannot carry arbitrarily large/private objects out.
    return {key: value if isinstance(value := record.get(key), str) and len(value) <= 4096
            else None for key in SOURCE_KEYS}


def _error(source, code):
    return {'source': source, 'artifact': None, 'artifact_sha256': None,
            'error_code': code}


def _init_worker(cancel):
    global _worker_cancel
    _worker_cancel = cancel


def _compact(encoded_record, versions):
    """Exactly one rules evaluation; digest precedes removal of the original."""
    from normalization_api import NormalizationError, Versions
    from normalization_core import artifact_digest, run_rules
    record = json.loads(encoded_record)
    source = _identity(record)
    if source['domain'] not in PUBLIC_DOMAINS:
        return _error(source, 'outside_public_domain')
    try:
        artifact = run_rules(record, versions=Versions(**versions), store=None)
        full_digest = artifact_digest(artifact)
        del artifact['source_original']
        return {'source': source, 'artifact': artifact,
                'artifact_sha256': full_digest, 'error_code': None}
    except NormalizationError as exc:
        code = ('source_content_hash_mismatch' if exc.args == ('source_content_hash_mismatch',)
                else 'rules_validation_error')
        return _error(source, code)
    except (MemoryError, OSError):
        raise RulesWorkerError('rules_worker_resource_failure') from None
    except Exception:
        return _error(source, 'rules_execution_error')


def _run_task_unchecked(frames, versions, output_limit):
    started, cpu_started = time.monotonic_ns(), time.process_time_ns()
    outputs, size, overflow = [], 0, False
    for index, body in frames:
        if _worker_cancel is not None and _worker_cancel.is_set():
            break
        value = _compact(body, versions)
        result = _encoded(value)
        if len(result) + 32 > output_limit:
            result = _encoded(_error(value['source'], 'rules_output_limit'))
        if size + len(result) + 32 > output_limit:
            overflow = True
            break
        outputs.append((index, result))
        size += len(result) + 32
    return {'outputs': outputs, 'overflow': overflow, 'pid': os.getpid(),
            'start_ns': started, 'end_ns': time.monotonic_ns(),
            'cpu_ns': time.process_time_ns() - cpu_started}


def _run_task(frames, versions, output_limit):
    try:
        return _run_task_unchecked(frames, versions, output_limit)
    except (MemoryError, OSError):
        raise RulesWorkerError('rules_worker_resource_failure') from None


class RulesExecutor:
    """One persistent spawn pool per engine; use as a context manager.

    run_batch accepts at most max_batch_rows (128) and max_input_bytes (4 MiB)
    serialized public input. At most 2*workers pure tasks are outstanding, each
    returning <=max_output_bytes. The returned list itself is also byte-capped;
    aggregate expansion raises RulesBatchLimitError so the single writer can
    halve and retry the uncommitted batch. An oversized individual output is a
    finite per-record error, not a truncated artifact. There is no corpus queue.

    check_cancel is parent-only and must raise when deadline/disk/cancellation
    requires stopping. It runs before admission, while waiting every 100 ms,
    and before returning. On abort all owned workers are terminated, including
    an in-progress rule call. No result has any durable side effect.
    """
    def __init__(self, workers=16, *, max_batch_rows=MAX_BATCH_ROWS,
                 max_input_bytes=DEFAULT_BYTES, max_output_bytes=DEFAULT_BYTES,
                 max_inflight_tasks=None, check_cancel=None, on_task_done=None):
        self.workers = available_workers(workers)
        self.actual_workers = 0
        if (isinstance(max_batch_rows, bool) or not isinstance(max_batch_rows, int)
                or not 1 <= max_batch_rows <= MAX_BATCH_ROWS):
            raise ValueError('invalid_rules_batch_rows')
        for value in (max_input_bytes, max_output_bytes):
            if isinstance(value, bool) or not isinstance(value, int) or not 16384 <= value <= MAX_BYTES:
                raise ValueError('invalid_rules_byte_limit')
        self.max_batch_rows = max_batch_rows
        self.max_input_bytes = max_input_bytes
        self.max_output_bytes = max_output_bytes
        maximum = 2 * self.workers
        self.max_inflight_tasks = maximum if max_inflight_tasks is None else max_inflight_tasks
        if (isinstance(self.max_inflight_tasks, bool) or not isinstance(self.max_inflight_tasks, int)
                or not 1 <= self.max_inflight_tasks <= maximum):
            raise ValueError('invalid_rules_inflight_limit')
        self.check_cancel = check_cancel or (lambda: None)
        self.on_task_done = on_task_done
        self.stats = RulesStats()
        self._pool = None
        self._cancel = None
        self._closed = False
        self._active = False

    def __enter__(self):
        if self._closed:
            raise RuntimeError('rules_executor_closed')
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close(abort=exc_type is not None)

    def _ensure_pool(self):
        if self._pool is None:
            context = multiprocessing.get_context('spawn')
            self._cancel = context.Event()
            self._pool = ProcessPoolExecutor(max_workers=self.workers, mp_context=context,
                initializer=_init_worker, initargs=(self._cancel,))
        return self._pool

    def _abort_pool(self):
        pool, self._pool = self._pool, None
        if self._cancel is not None:
            self._cancel.set()
        if pool is None:
            return
        # Python >=3.14 supplies a public termination API. The deployed 3.12
        # executor does not; capture only this pool's own process handles before
        # shutdown, never enumerate or terminate unrelated host processes.
        processes = list((getattr(pool, '_processes', None) or {}).values())
        terminate = getattr(pool, 'terminate_workers', None)
        if terminate is not None:
            terminate()
        else:
            for process in processes:
                if process.is_alive():
                    process.terminate()
            pool.shutdown(wait=False, cancel_futures=True)
        deadline = time.monotonic() + 2.0
        for process in processes:
            process.join(max(0.0, deadline - time.monotonic()))
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join(0.2)

    def close(self, *, abort=False):
        if self._closed:
            return
        if abort or self._active:
            self._abort_pool()
        elif self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=True)
            self._pool = None
        self._closed = True

    def _prepare(self, records):
        frames, results, sources, input_size = [], [], [], 0
        for index, record in enumerate(records):
            self.check_cancel()
            if index >= self.max_batch_rows:
                raise RulesBatchLimitError('rules_batch_row_limit')
            source = _identity(record)
            sources.append(source)
            results.append(None)
            if source['domain'] not in PUBLIC_DOMAINS:
                results[index] = _error(source, 'outside_public_domain')
                continue
            if any(source[key] is None for key in SOURCE_KEYS):
                results[index] = _error(source, 'invalid_source_envelope')
                continue
            try:
                body = _encoded(record)
            except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError):
                results[index] = _error(source, 'invalid_source_envelope')
                continue
            if len(body) + 32 > self.max_input_bytes:
                results[index] = _error(source, 'rules_input_limit')
                continue
            input_size += len(body) + 32
            if input_size > self.max_input_bytes:
                raise RulesBatchLimitError('rules_batch_input_limit')
            frames.append((index, body))
        return frames, results, sources

    def _collect(self, frames, results, sources, versions):
        from collections import deque
        task_rows = max(1, math.ceil(len(frames) / self.max_inflight_tasks))
        tasks = iter(frames[start:start + task_rows] for start in range(0, len(frames), task_rows))
        pending = deque()
        ended = False
        output_size = sum(len(_encoded(value)) + 32 for value in results if value is not None)
        if output_size > self.max_output_bytes:
            raise RulesBatchLimitError('rules_batch_output_limit')
        while pending or not ended:
            while not ended and len(pending) < self.max_inflight_tasks:
                self.check_cancel()
                try:
                    task = next(tasks)
                except StopIteration:
                    ended = True
                    break
                future = self._ensure_pool().submit(_run_task, task, versions, self.max_output_bytes)
                self.actual_workers = len(self._pool._processes or {})
                pending.append((future, task))
                self.stats.submitted_tasks += 1
                self.stats.peak_inflight_tasks = max(self.stats.peak_inflight_tasks, len(pending))
            if not pending:
                break
            future, task = pending.popleft()
            while True:
                self.check_cancel()
                try:
                    response = future.result(timeout=0.1)
                    break
                except TimeoutError:
                    if future.done():
                        raise RuntimeError('rules_worker_timeout_failure') from None
            self.stats.completed_tasks += 1
            if len(self.stats.worker_pids) < 2 * MAX_WORKERS:
                self.stats.worker_pids.add(response['pid'])
            self.stats.worker_cpu_ns += response['cpu_ns']
            self.stats.worker_wall_ns += response['end_ns'] - response['start_ns']
            if self.on_task_done is not None:
                self.on_task_done({key: response[key] for key in ('pid', 'start_ns', 'end_ns', 'cpu_ns')})
            if response['overflow']:
                raise RulesBatchLimitError('rules_batch_output_limit')
            if [index for index, _ in response['outputs']] != [frame[0] for frame in task]:
                raise RuntimeError('rules_worker_protocol_error')
            for index, encoded_result in response['outputs']:
                output_size += len(encoded_result) + 32
                if output_size > self.max_output_bytes:
                    raise RulesBatchLimitError('rules_batch_output_limit')
                value = json.loads(encoded_result)
                if (value.get('source') != sources[index] or
                        value.get('error_code') not in ERROR_CODES | {None}):
                    raise RuntimeError('rules_worker_protocol_error')
                artifact = value.get('artifact')
                if value['error_code'] is None and (not isinstance(artifact, dict)
                        or 'source_original' in artifact or artifact.get('source') != sources[index]):
                    raise RuntimeError('rules_worker_protocol_error')
                results[index] = value
        return results

    def run_batch(self, records, versions=None):
        from normalization_api import Versions
        if self._closed or self._active:
            raise RuntimeError('rules_executor_closed_or_busy')
        self._active = True
        try:
            version_map = (versions or Versions()).as_dict()
            frames, results, sources = self._prepare(records)
            # Worker death is safe to retry: there are no child stores/cursors.
            # A second pool failure propagates a fixed code, never raw context.
            for attempt in range(2):
                try:
                    result = self._collect(frames, results[:], sources, version_map)
                    self.check_cancel()
                    return result
                except BrokenProcessPool:
                    self._abort_pool()
                    self.stats.worker_restarts += 1
                    if attempt:
                        raise RulesWorkerError('rules_worker_pool_failed') from None
        except (MemoryError, OSError):
            self._abort_pool()
            raise RulesWorkerError('rules_worker_resource_failure') from None
        except BaseException:
            self._abort_pool()
            raise
        finally:
            self._active = False
