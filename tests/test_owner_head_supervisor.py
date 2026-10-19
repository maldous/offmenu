"""Synthetic aggregate process supervision. No real DNS, HTTP or owner data."""
from contextlib import ExitStack, redirect_stdout
import importlib.util
import io
import json
import multiprocessing
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('owner_head_supervisor_under_test',
    ROOT / 'scripts/diagnose-owner-five-heads.py')
supervisor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervisor
SPEC.loader.exec_module(supervisor)
_DESCENDANT_PID = None


def report():
    return supervisor.diagnostic.report_template('diagnostic-inactive')


def check_report(value):
    if type(value) is not dict or value.get('schemaVersion') != 'offmenu-owner-head-result/1':
        raise ValueError('diagnostic-result-invalid')


def successful_worker(pipe, deadline):
    os.setsid()
    frames = supervisor._Frames(pipe)
    frames.send({'ready': True})
    frames.send({'result': report()})
    pipe.close()


def stuck_before_session(pipe, deadline):
    time.sleep(60)


def stuck_before_ready(pipe, deadline):
    os.setsid()
    time.sleep(60)


def stuck_after_ready(pipe, deadline):
    os.setsid()
    supervisor._Frames(pipe).send({'ready': True})
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


def partial_frame_worker(pipe, deadline):
    os.setsid()
    os.write(pipe.fileno(), struct.pack('!i', 1000) + b'{')
    time.sleep(60)


def bad_protocol_worker(pipe, deadline):
    os.setsid()
    pipe.send_bytes(b'{"result":{}}')
    pipe.close()


def duplicate_json_worker(pipe, deadline):
    os.setsid()
    pipe.send_bytes(b'{"ready":true,"ready":true}')
    pipe.close()


def invalid_result_worker(pipe, deadline):
    os.setsid()
    frames = supervisor._Frames(pipe)
    frames.send({'ready': True})
    frames.send({'result': {'secret': 'RAW-CAPABILITY'}})
    pipe.close()


def over_envelope_worker(pipe, deadline):
    os.setsid()
    frames = supervisor._Frames(pipe)
    frames.send({'ready': True})
    # Bypass the safe writer to exercise the independent parent cap. It cannot
    # consume 65537 bytes even though the declared frame itself is <=65536.
    payload = b'{"result":"' + b'x' * (supervisor.MAX_BYTES - 13) + b'"}'
    pipe.send_bytes(payload)
    time.sleep(60)


def crash_with_descendant(pipe, deadline):
    os.setsid()
    child = os.fork()
    if child == 0:
        time.sleep(60)
        os._exit(0)
    _DESCENDANT_PID.value = child
    os._exit(9)


def ready_with_descendant(pipe, deadline):
    os.setsid()
    child = os.fork()
    if child == 0:
        time.sleep(60)
        os._exit(0)
    _DESCENDANT_PID.value = child
    supervisor._Frames(pipe).send({'ready': True})
    time.sleep(60)


def noisy_execute(*, deadline):
    print('RAW-CAPABILITY')
    print('RAW-COOKIE', file=sys.stderr)
    os.write(1, b'RAW-CAPABILITY\n')
    os.write(2, b'RAW-COOKIE\n')
    return report()


def failed_execute(*, deadline):
    raise ValueError('RAW-CAPABILITY RAW-COOKIE')


def executing_process(pid):
    path = Path('/proc') / str(pid) / 'stat'
    try:
        state = path.read_text().rsplit(') ', 1)[1][0]
    except FileNotFoundError:
        return False
    return state not in ('Z', 'X')


@unittest.skipUnless(os.name == 'posix', 'POSIX process-group supervision')
class AggregateSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.before = {p.pid for p in multiprocessing.active_children()}
        self.stack.enter_context(patch.object(socket, 'getaddrinfo', side_effect=AssertionError('real DNS forbidden')))
        self.stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('real socket forbidden')))
        self.original_validator = supervisor.diagnostic.validate_report
        self.validator = self.stack.enter_context(patch.object(supervisor.diagnostic, 'validate_report',
                                                              side_effect=check_report, create=True))

    def tearDown(self):
        self.stack.close()
        self.assertEqual({p.pid for p in multiprocessing.active_children()} - self.before, set())

    def run_worker(self, worker=successful_worker, seconds=0.4):
        return supervisor.supervise(worker=worker, seconds=seconds)

    def test_safe_result_is_validated_and_group_reaped(self):
        value = self.run_worker()
        self.assertEqual(value, report())
        self.validator.assert_called_once_with(value)

    def test_timeout_covers_before_setsid_before_ready_and_after_ready(self):
        for worker in (stuck_before_session, stuck_before_ready, stuck_after_ready):
            with self.subTest(worker=worker.__name__):
                start = time.monotonic()
                value = self.run_worker(worker)
                self.assertLess(time.monotonic() - start, 0.65)
                self.assertEqual(value['code'], 'diagnostic-deadline')
                self.assertEqual(value['status'], 'incomplete-consumed')
                self.assertEqual(value['sourceAttemptsConsumed'], 5)
                self.assertEqual(value['requestAttemptUnknownCount'], 5)
                self.assertIsNone(value['sourceMetadataUnchanged'])

    def test_partial_frame_cannot_stall_past_deadline(self):
        start = time.monotonic()
        value = self.run_worker(partial_frame_worker)
        self.assertLess(time.monotonic() - start, 0.65)
        self.assertEqual(value['code'], 'diagnostic-deadline')

    def test_protocol_and_duplicate_json_fail_closed(self):
        for worker in (bad_protocol_worker, duplicate_json_worker):
            with self.subTest(worker=worker.__name__):
                value = self.run_worker(worker)
                self.assertEqual(value['code'], 'diagnostic-result-invalid')

    def test_result_is_schema_validated_not_only_shallowly_accepted(self):
        value = self.run_worker(invalid_result_worker)
        self.assertEqual(value['code'], 'diagnostic-result-invalid')
        self.assertNotIn('RAW', json.dumps(value))

    def test_combined_pipe_envelope_includes_stage_and_length_prefixes(self):
        value = self.run_worker(over_envelope_worker)
        self.assertEqual(value['code'], 'diagnostic-result-invalid')
        class Sink:
            def __init__(self): self.data = []
            def send_bytes(self, value): self.data.append(value)
        sink = Sink()
        frames = supervisor._Frames(sink)
        frames.send({'ready': True})
        with self.assertRaisesRegex(ValueError, '^diagnostic-result-invalid$'):
            frames.send({'result': 'x' * (supervisor.MAX_BYTES - 20)})
        self.assertLessEqual(sum(len(item) + 4 for item in sink.data), supervisor.MAX_BYTES)

    def test_production_worker_suppresses_python_and_native_output(self):
        read_fd, write_fd = os.pipe()
        old_out, old_err = os.dup(1), os.dup(2)
        try:
            os.dup2(write_fd, 1)
            os.dup2(write_fd, 2)
            with patch.object(supervisor.diagnostic, 'execute_owner', side_effect=noisy_execute):
                value = self.run_worker(supervisor._worker)
        finally:
            os.dup2(old_out, 1)
            os.dup2(old_err, 2)
            for fd in (write_fd, old_out, old_err):
                os.close(fd)
        try:
            output = os.read(read_fd, 65536)
        finally:
            os.close(read_fd)
        self.assertEqual(output, b'')
        self.assertEqual(value, report())

    def test_production_worker_exceptions_do_not_echo_private_values(self):
        with patch.object(supervisor.diagnostic, 'execute_owner', side_effect=failed_execute):
            value = self.run_worker(supervisor._worker)
        self.assertEqual(value['code'], 'diagnostic-supervisor-failed')
        self.assertEqual(value['status'], 'incomplete-consumed')
        self.assertEqual(value['requestAttemptUnknownCount'], 5)
        self.assertNotIn('RAW', json.dumps(value))

    def test_spawn_and_multithreaded_contexts_fail_without_process_creation(self):
        context = multiprocessing.get_context('spawn')
        with patch.object(context, 'Process') as factory:
            value = supervisor.supervise(context=context)
        factory.assert_not_called()
        self.assertEqual(value['code'], 'diagnostic-supervisor-failed')
        with patch.object(supervisor.threading, 'active_count', return_value=2), \
                patch.object(multiprocessing, 'get_context') as factory:
            value = self.run_worker()
        factory.assert_not_called()
        self.assertEqual(value['code'], 'diagnostic-supervisor-failed')

    def test_cleanup_kills_groups_before_reaping_and_closes_setsid_race(self):
        events = []
        class Process:
            pid = 123456789
            def kill(self): events.append('kill')
            def join(self, timeout): events.append('join')
            def is_alive(self): events.append('is_alive'); return False
            def close(self): events.append('close')
        def killpg(pid, sig):
            self.assertEqual(pid, 123456789)
            self.assertEqual(sig, signal.SIGKILL)
            events.append('killpg')
            if events.count('killpg') == 1:
                raise ProcessLookupError
        with patch.object(os, 'killpg', side_effect=killpg):
            supervisor._cleanup(Process(), time.monotonic() + 0.1)
        self.assertEqual(events, ['killpg', 'kill', 'killpg', 'join', 'is_alive', 'close'])

    @unittest.skipUnless(Path('/proc/self/stat').exists(), 'Linux process state check')
    def test_crashed_owner_and_timeout_both_stop_descendants(self):
        global _DESCENDANT_PID
        for worker in (crash_with_descendant, ready_with_descendant):
            with self.subTest(worker=worker.__name__):
                _DESCENDANT_PID = multiprocessing.get_context('fork').Value('i', 0)
                value = self.run_worker(worker)
                pid = _DESCENDANT_PID.value
                self.assertGreater(pid, 0)
                deadline = time.monotonic() + 0.2
                while executing_process(pid) and time.monotonic() < deadline:
                    time.sleep(0.005)
                self.assertFalse(executing_process(pid), 'descendant can still execute after return')
                self.assertIn(value['code'], ('diagnostic-deadline', 'diagnostic-supervisor-failed'))
                self.assertEqual(value['status'], 'incomplete-consumed')
                self.assertEqual(value['requestAttemptUnknownCount'], 5)
        _DESCENDANT_PID = None

    def test_uncertain_report_satisfies_real_report_contract(self):
        # The production validator is pure for the empty-item fallback. Retain
        # the method from before the local validator seam for this assertion.
        with patch.object(supervisor.diagnostic, 'validate_report', self.original_validator):
            value = supervisor._uncertain_report('diagnostic-deadline')
            self.assertEqual(supervisor.diagnostic.validate_report(value), value)

    def test_total_deadline_is_capped_and_includes_cleanup_reserve(self):
        with patch.object(supervisor, 'MAX_SECONDS', 0.4):
            start = time.monotonic()
            value = self.run_worker(stuck_after_ready, seconds=900)
        self.assertLess(time.monotonic() - start, 0.65)
        self.assertEqual(value['code'], 'diagnostic-deadline')

    def test_inactive_main_cannot_start_supervisor_or_owner_io(self):
        out = io.StringIO()
        with patch.object(supervisor.diagnostic, 'ACTIVATION_SHA256', None), \
                patch.object(supervisor, 'supervise') as start, \
                patch.object(supervisor.diagnostic, 'execute_owner') as execute, redirect_stdout(out):
            code = supervisor.main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())['code'], 'diagnostic-inactive')
        start.assert_not_called()
        execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
