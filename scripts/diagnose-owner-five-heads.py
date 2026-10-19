#!/usr/bin/env python3
"""Inactive exact-five HEAD entrypoint; aggregate supervision covers all owner I/O."""
import contextlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import select
import signal
import struct
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from offmenu.refresh import owner_head_diagnostic as diagnostic

MAX_BYTES = 65536
MAX_SECONDS = 90.0


def _uncertain_report(code):
    value = diagnostic.report_template(code)
    value.update(status='incomplete-consumed', sourceAttemptsConsumed=5,
                 requestAttemptUnknownCount=5, sourceMetadataUnchanged=None)
    return value


class _Frames:
    """All JSON, length prefixes, and readiness bytes share one envelope."""
    def __init__(self, pipe):
        self.pipe = pipe
        self.sent = 0

    def send(self, value):
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode('ascii')
        if self.sent + len(raw) + 4 > MAX_BYTES:
            raise ValueError('diagnostic-result-invalid')
        self.pipe.send_bytes(raw)
        self.sent += len(raw) + 4


def _worker(pipe, deadline):
    output = _Frames(pipe)
    try:
        os.setsid()  # All HEAD descendants stay in this cancellable process group.
        with open(os.devnull, 'w') as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                try:
                    import resource
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                    output.send({'ready': True})
                    value = diagnostic.execute_owner(deadline=deadline)
                    output.send({'result': value})
                except BaseException:
                    output.send({'result': _uncertain_report('diagnostic-supervisor-failed')})
    except BaseException:
        # No raw exception, URL, header or guard metadata reaches stderr/stdout.
        pass
    finally:
        pipe.close()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('diagnostic-result-invalid')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('diagnostic-result-invalid')


def _cleanup(proc, deadline):
    """Kill the entire group before reaping its leader (and releasing its PID).

    A child may execute setsid before its ready frame reaches the reader. It may
    also execute setsid between the first killpg and a direct kill; a second
    killpg before join covers that window. Never poll/is_alive/exitcode before
    group cleanup, because those methods can reap the leader and recycle its PID.
    """
    if proc.pid is None:
        proc.close()
        return
    pid = proc.pid
    try:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            # Still before setsid, or exited before creating a group. The child
            # PID is reserved because no wait/poll has reaped it at this point.
            proc.kill()
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.join(timeout=max(0.0, deadline - time.monotonic()))
        if proc.is_alive():
            raise RuntimeError('diagnostic-supervisor-failed')
        proc.close()
    except BaseException:
        raise RuntimeError('diagnostic-supervisor-failed') from None


def supervise(*, worker=_worker, seconds=90, context=None):
    """Single-threaded POSIX/fork only; no synchronous spawn serialization gap."""
    started = time.monotonic()
    if (type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0
            or os.name != 'posix' or threading.active_count() != 1
            or threading.current_thread() is not threading.main_thread()):
        return diagnostic.report_template('diagnostic-supervisor-failed')
    duration = min(MAX_SECONDS, seconds)
    deadline = started + duration
    work_deadline = deadline - min(1.0, duration / 4)
    try:
        ctx = context or multiprocessing.get_context('fork')
        if ctx.get_start_method() != 'fork':
            return diagnostic.report_template('diagnostic-supervisor-failed')
    except BaseException:
        return diagnostic.report_template('diagnostic-supervisor-failed')
    read = write = proc = None
    launched = False
    value = None
    failure = 'diagnostic-supervisor-failed'
    ready = False
    buffer = bytearray()
    total = 0
    try:
        read, write = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=worker, args=(write, work_deadline), daemon=False)
        if time.monotonic() >= work_deadline:
            raise TimeoutError
        proc.start()
        launched = True
        write.close()
        os.set_blocking(read.fileno(), False)
        while True:
            remaining = work_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            # The sentinel observes exit without reaping the group leader.
            available = select.select([read.fileno(), proc.sentinel], [], [], remaining)[0]
            if not available:
                raise TimeoutError
            if read.fileno() not in available:
                break  # Leader exited; cleanup must also kill orphan descendants.
            if total >= MAX_BYTES:
                raise ValueError('diagnostic-result-invalid')
            try:
                block = os.read(read.fileno(), min(4096, MAX_BYTES - total))
            except BlockingIOError:
                continue
            if not block:
                break
            total += len(block)
            buffer.extend(block)
            while len(buffer) >= 4:
                size = struct.unpack('!i', buffer[:4])[0]
                if not 0 < size <= MAX_BYTES:
                    raise ValueError('diagnostic-result-invalid')
                if len(buffer) < size + 4:
                    break
                frame = json.loads(bytes(buffer[4:4 + size]), object_pairs_hook=_pairs,
                                   parse_constant=_constant)
                del buffer[:4 + size]
                if frame == {'ready': True} and not ready:
                    ready = True
                elif ready and type(frame) is dict and set(frame) == {'result'} and value is None:
                    value = frame['result']
                else:
                    raise ValueError('diagnostic-result-invalid')
            if value is not None:
                if buffer:
                    raise ValueError('diagnostic-result-invalid')
                break
    except TimeoutError:
        value = None
        failure = 'diagnostic-deadline'
    except (ValueError, TypeError, UnicodeError, RecursionError):
        value = None
        failure = 'diagnostic-result-invalid'
    except BaseException:
        value = None
    finally:
        try:
            if proc is not None:
                launched = launched or proc.pid is not None
                _cleanup(proc, deadline)
        finally:
            if read is not None:
                read.close()
            if write is not None:
                write.close()
    failed_report = _uncertain_report if launched else diagnostic.report_template
    if time.monotonic() > deadline:
        return failed_report('diagnostic-deadline')
    if value is None:
        return failed_report(failure)
    try:
        diagnostic.validate_report(value)
        if len(diagnostic.canonical(value)) > MAX_BYTES:
            raise ValueError('diagnostic-result-invalid')
    except BaseException:
        return failed_report('diagnostic-result-invalid')
    if time.monotonic() > deadline:
        return failed_report('diagnostic-deadline')
    return value


def main(argv=None):
    if sys.argv[1:] if argv is None else argv:
        value = diagnostic.report_template('diagnostic-config-invalid')
    elif diagnostic.ACTIVATION_SHA256 is None:
        # This short circuit must precede process creation and owner-local I/O.
        value = diagnostic.report_template('diagnostic-inactive')
    else:
        try:
            value = supervise()
        except BaseException:
            value = _uncertain_report('diagnostic-supervisor-failed')
    print(diagnostic.canonical(value).decode(), end='')
    return 0 if value['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
