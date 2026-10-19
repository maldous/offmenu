"""Synthetic-only transport tests. No real HTTP, DNS or target assets are used."""
from contextlib import ExitStack
from dataclasses import dataclass, field
import http.client
import io
import json
import multiprocessing
import os
import signal
import socket
import ssl
import struct
import sys
import time
import unittest
from unittest.mock import patch

from offmenu.refresh import owner_head_transport as head
from offmenu.refresh import owner_head_metadata as metadata


@dataclass(frozen=True)
class Source:
    exact_url: str = field(repr=False, default='https://example.invalid/exact%2Fpath?a=1&a=2')


class FakeSocket:
    def __init__(self, payload=b'HTTP/1.1 200 OK\r\nContent-Length: 9000\r\n\r\nBODY-MUST-STAY-UNTOUCHED'):
        self.payload = payload
        self.position = 0
        self.sizes = []
        self.sent = []
        self.timeouts = []
        self.closed = False
        self.connected = []
        self.handshakes = 0

    def settimeout(self, timeout):
        if timeout <= 0:
            raise AssertionError('nonpositive timeout')
        self.timeouts.append(timeout)

    def connect(self, address):
        self.connected.append(address)

    def do_handshake(self):
        self.handshakes += 1

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        self.sizes.append(size)
        if size != 1:
            raise AssertionError('read-ahead forbidden')
        data = self.payload[self.position:self.position + size]
        self.position += len(data)
        return data

    def close(self):
        self.closed = True

    def makefile(self, *args, **kwargs):
        raise AssertionError('buffered response reader forbidden')

    def read(self, *args, **kwargs):
        raise AssertionError('body read forbidden')

    def unwrap(self):
        raise AssertionError('TLS shutdown read forbidden')


class FakeContext:
    def __init__(self, stream):
        self.stream = stream
        self.wraps = []
        self.loaded = []
        self.alpn = []

    def load_default_certs(self, purpose):
        self.loaded.append(purpose)

    def set_alpn_protocols(self, protocols):
        self.alpn = protocols

    def wrap_socket(self, stream, **kwargs):
        self.wraps.append((stream, kwargs))
        return self.stream


def safe_sanitizer(source, status, headers, count):
    return {'status': status, 'headerCount': len(headers), 'headerBytes': count,
            'bodyBytesRead': 0}


def synthetic_head(url, deadline, *, on_request):
    on_request()
    return 302, [('Location', 'https://other.invalid/secret?Signature=RAW-CAPABILITY'),
                 ('Set-Cookie', 'RAW-COOKIE')], 100


def exploding_sanitizer(*args):
    raise ValueError('RAW-CAPABILITY RAW-COOKIE')


def noisy_sanitizer(*args):
    print('RAW-CAPABILITY')
    print('RAW-COOKIE', file=sys.stderr)
    os.write(1, b'RAW-CAPABILITY\n')
    os.write(2, b'RAW-COOKIE\n')
    return {'status': 200}


def huge_sanitizer(*args):
    return {'safe': 'x' * head.MAX_RESULT_BYTES}


def blocking_dns(*args, **kwargs):
    time.sleep(60)
    raise AssertionError('late DNS completion must never happen')


def synthetic_success_worker(source, deadline, sanitizer, pipe):
    output = head._SafePipe(pipe)
    output.send({'stage': 'ready'})
    output.send({'stage': 'request-attempted'})
    output.send({'ok': True, 'requestAttempted': True,
                 'observation': {'status': 200, 'bodyBytesRead': 0}})
    pipe.close()


def synthetic_partial_frame_worker(source, deadline, sanitizer, pipe):
    os.write(pipe.fileno(), struct.pack('!i', 1000) + b'{')
    time.sleep(60)


def synthetic_ignore_term_worker(source, deadline, sanitizer, pipe):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    output = head._SafePipe(pipe)
    output.send({'stage': 'ready'})
    output.send({'stage': 'request-attempted'})
    time.sleep(60)


def synthetic_crash_worker(source, deadline, sanitizer, pipe):
    os._exit(9)


def synthetic_before_attempt_crash_worker(source, deadline, sanitizer, pipe):
    head._SafePipe(pipe).send({'stage': 'ready'})
    os._exit(9)


def synthetic_bad_protocol_worker(source, deadline, sanitizer, pipe):
    pipe.send_bytes(b'{"ok":true,"observation":{"status":200},"requestAttempted":true}')
    pipe.close()


def synthetic_after_result_block_worker(source, deadline, sanitizer, pipe):
    synthetic_success_worker(source, deadline, sanitizer, pipe)
    time.sleep(60)


def synthetic_blocking_operation(*args, **kwargs):
    time.sleep(60)
    raise AssertionError('late network operation must never happen')


def synthetic_explicit_pre_request_failure(url, deadline, **kwargs):
    raise head.HeadTransportError('head-transport-failed')


class NoNetworkTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(socket, 'getaddrinfo', side_effect=AssertionError('real DNS forbidden')))
        self.stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('real socket forbidden')))

    def tearDown(self):
        self.stack.close()


class HeaderParserTests(NoNetworkTests):
    def parse(self, payload):
        stream = FakeSocket(payload)
        result = head._read_head(stream, time.monotonic() + 5)
        return result, stream

    def test_stops_exactly_at_final_headers_without_body_read_ahead(self):
        prefix = b'HTTP/1.1 200 OK\r\nContent-Length: 999999\r\n\r\n'
        result, stream = self.parse(prefix + b'SECRET BODY')
        self.assertEqual(result, (200, [('Content-Length', '999999')], len(prefix)))
        self.assertEqual(stream.position, len(prefix))
        self.assertEqual(set(stream.sizes), {1})
        self.assertEqual(stream.payload[stream.position:], b'SECRET BODY')

    def test_interim_sections_share_one_envelope_and_only_final_fields_return(self):
        interim = b'HTTP/1.1 100 Continue\r\nInterim: hidden\r\n\r\nHTTP/1.1 103 Early Hints\r\nLink: hidden\r\n\r\n'
        final = b'HTTP/1.1 302 Found\r\nLocation: /exact?a=1\r\n\r\n'
        result, stream = self.parse(interim + final + b'BODY')
        self.assertEqual(result, (302, [('Location', '/exact?a=1')], len(interim + final)))
        self.assertEqual(stream.position, len(interim + final))

    def test_envelope_accepts_exact_limit_and_never_reads_byte_65537(self):
        fixed = b'HTTP/1.1 200 OK\r\nX: \r\n\r\n'
        payload = b'HTTP/1.1 200 OK\r\nX: ' + b'a' * (head.MAX_HEADER_BYTES - len(fixed)) + b'\r\n\r\n'
        result, stream = self.parse(payload + b'BODY')
        self.assertEqual(result[2], 65536)
        self.assertEqual(stream.position, 65536)
        stream = FakeSocket(payload[:-4] + b'a\r\n\r\nBODY')
        with self.assertRaisesRegex(head.HeadTransportError, '^head-header-envelope-exceeded$'):
            head._read_head(stream, time.monotonic() + 5)
        self.assertEqual(stream.position, 65536)

    def test_interim_bytes_cannot_reset_envelope(self):
        interim = b'HTTP/1.1 103 Early Hints\r\nX: ' + b'a' * 40000 + b'\r\n\r\n'
        final = b'HTTP/1.1 200 OK\r\nX: ' + b'b' * 30000 + b'\r\n\r\n'
        stream = FakeSocket(interim + final)
        with self.assertRaisesRegex(head.HeadTransportError, '^head-header-envelope-exceeded$'):
            head._read_head(stream, time.monotonic() + 5)
        self.assertEqual(stream.position, 65536)

    def test_duplicate_fields_and_order_preserved(self):
        result, _ = self.parse(b'HTTP/1.1 200 OK\r\nX-Value: one\r\nx-value:\ttwo \t\r\nLocation: /a\r\nLocation: /b\r\n\r\n')
        self.assertEqual(result[1], [('X-Value', 'one'), ('x-value', 'two \t'), ('Location', '/a'), ('Location', '/b')])

    def test_trailing_spaces_crossing_value_limit_reach_sanitizer_unchanged(self):
        fields = b'Content-Type: ' + b'x' * 8192 + b'  \r\n\r\n'
        result, _ = self.parse(b'HTTP/1.1 302 Found\r\n' + fields + b'BODY')
        expected = list(http.client.parse_headers(io.BytesIO(fields)).items())
        self.assertEqual(result[1], expected)
        self.assertEqual(len(result[1][0][1]), 8194)
        facts = metadata._header_facts(result[1],
            {'url': Source().exact_url, 'mediaIntake': {'redirect': False}}, result[0])
        self.assertEqual(facts['genericHeaderFailurePoint'], 'value-length')
        self.assertEqual(facts['oversizedNames'], ['content-type'])
        self.assertEqual(facts['currentGETValidatorOnHEADHeaders'], 'invalid-response-headers')

    def test_trailing_tab_is_preserved_for_sanitizer_syntax_failure(self):
        fields = b'Content-Type: \ttext/csv \t\r\n\r\n'
        result, _ = self.parse(b'HTTP/1.1 302 Found\r\n' + fields + b'BODY')
        expected = list(http.client.parse_headers(io.BytesIO(fields)).items())
        self.assertEqual(result[1], expected)
        self.assertEqual(result[1], [('Content-Type', 'text/csv \t')])
        facts = metadata._header_facts(result[1],
            {'url': Source().exact_url, 'mediaIntake': {'redirect': False}}, result[0])
        self.assertEqual(facts['genericHeaderFailurePoint'], 'syntax')
        self.assertEqual(facts['invalidValueCount'], 1)
        self.assertEqual(facts['currentGETValidatorOnHEADHeaders'], 'media-intake-header-invalid')

    def test_slow_trickle_checks_shared_absolute_deadline_each_byte(self):
        clock = [10.0]
        stream = FakeSocket()
        original_recv = stream.recv
        def receive(size):
            clock[0] += 0.1
            return original_recv(size)
        stream.recv = receive
        with patch.object(head.time, 'monotonic', side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(head.HeadTransportError, '^head-deadline-exceeded$'):
                head._read_head(stream, 10.25)
        self.assertEqual(stream.position, 3)

    def test_final_field_limit_100(self):
        result, _ = self.parse(b'HTTP/1.1 200 OK\r\n' + b'X: y\r\n' * 100 + b'\r\nBODY')
        self.assertEqual(len(result[1]), 100)
        with self.assertRaisesRegex(head.HeadTransportError, '^head-header-field-limit$'):
            self.parse(b'HTTP/1.1 200 OK\r\n' + b'X: y\r\n' * 101 + b'\r\nBODY')

    def test_malformed_status_headers_and_folded_values_fail_without_values(self):
        bad = [b'HTTP/2 200 OK\r\n\r\n', b'HTTP/1.1 999 RAW-SECRET\r\n\r\n',
               b'HTTP/1.1 101 Switching Protocols\r\n\r\n', b'HTTP/1.1 200 OK\n\n',
               b'HTTP/1.1 200 OK\r\nX : RAW-SECRET\r\n\r\n',
               b'HTTP/1.1 200 OK\r\n RAW-SECRET\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nX: RAW\x00SECRET\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nX: RAW\rSECRET\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nX: RAW\x7fSECRET\r\n\r\n',
               b'HTTP/1.1 200 OK\r\nX: incomplete']
        for payload in bad:
            with self.subTest(payload=payload[:15]):
                with self.assertRaises(head.HeadTransportError) as error:
                    self.parse(payload)
                self.assertEqual(str(error.exception), 'head-header-invalid')
                self.assertNotIn('RAW', repr(error.exception))


class ExchangeTests(NoNetworkTests):
    def exchange(self, url=Source().exact_url, stream=None):
        stream = stream or FakeSocket()
        context = FakeContext(stream)
        dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('192.0.2.1', 443)),
               (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('192.0.2.2', 443))]
        with patch.object(socket, 'getaddrinfo', return_value=dns) as lookup, \
                patch.object(socket, 'socket', return_value=stream) as factory, \
                patch.object(ssl, 'SSLContext', return_value=context) as tls_factory:
            result = head._head_once(url, time.monotonic() + 5)
        return result, stream, context, lookup, factory, tls_factory

    def test_one_exact_head_no_cookie_auth_proxy_or_key_logging(self):
        with patch.dict(os.environ, {'https_proxy': 'https://proxy.invalid',
                'HTTP_PROXY': 'https://proxy.invalid', 'SSLKEYLOGFILE': '/must/not/write',
                'NETRC': '/must/not/read'}):
            result, stream, context, lookup, factory, tls_factory = self.exchange()
        self.assertEqual(result[0], 200)
        self.assertEqual(stream.sent, [b'HEAD /exact%2Fpath?a=1&a=2 HTTP/1.1\r\nHost: example.invalid\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n'])
        self.assertEqual(stream.connected, [('192.0.2.1', 443)])
        self.assertEqual(lookup.call_count, 1)
        self.assertEqual(factory.call_count, 1)
        tls_factory.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        self.assertEqual(context.alpn, ['http/1.1'])
        self.assertEqual(context.wraps[0][1], {'server_hostname': 'example.invalid', 'do_handshake_on_connect': False})
        self.assertEqual(stream.handshakes, 1)
        self.assertTrue(stream.closed)

    def test_empty_query_and_case_sensitive_escaped_target_preserved(self):
        _, stream, *_ = self.exchange('https://EXAMPLE.invalid:443/Ab%2fCd?')
        self.assertTrue(stream.sent[0].startswith(b'HEAD /Ab%2fCd? HTTP/1.1\r\nHost: EXAMPLE.invalid:443\r\n'))

    def test_redirect_never_opens_second_connection_or_reads_body(self):
        stream = FakeSocket(b'HTTP/1.1 302 Found\r\nLocation: https://else.invalid/?Signature=RAW\r\n\r\nBODY')
        result, stream, _, lookup, factory, _ = self.exchange(stream=stream)
        self.assertEqual(result[0], 302)
        self.assertEqual(len(stream.sent), 1)
        self.assertEqual(lookup.call_count, 1)
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(stream.payload[stream.position:], b'BODY')

    def test_invalid_urls_rejected_before_dns_and_without_echo(self):
        bad = ['http://example.invalid/a', 'https://u:p@example.invalid/a',
               'https://example.invalid:444/a', 'https://example.invalid/a#fragment',
               'https://example.invalid/a\r\nCookie: RAW', 'https://example.invalid/a b',
               'https://example.invalid/%QQ', 'https://example.invalid\\path',
               'https://example.invalid:/a', 'https://example..invalid/a',
               'https://[fe80::1%25eth0]/a']
        for url in bad:
            with self.subTest(prefix=url[:8]):
                with self.assertRaisesRegex(head.HeadTransportError, '^head-input-invalid$'):
                    head._head_once(url, time.monotonic() + 5)

    def test_connect_error_has_no_address_fallback_and_closed_error(self):
        stream = FakeSocket()
        stream.connect = lambda address: (_ for _ in ()).throw(OSError('RAW-CAPABILITY'))
        with self.assertRaisesRegex(head.HeadTransportError, '^head-transport-failed$'):
            self.exchange(stream=stream)
        self.assertTrue(stream.closed)
        self.assertEqual(stream.sent, [])


@unittest.skipUnless(os.name == 'posix', 'POSIX worker supervision')
class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.before = {p.pid for p in multiprocessing.active_children()}
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(socket, 'getaddrinfo', side_effect=AssertionError('real DNS forbidden')))
        self.stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('real socket forbidden')))
        self.context = multiprocessing.get_context('fork')

    def tearDown(self):
        self.stack.close()
        self.assertEqual({p.pid for p in multiprocessing.active_children()} - self.before, set())

    def run_head(self, seconds=2, sanitizer=safe_sanitizer, **kwargs):
        return head.observe_head(Source(), absolute_deadline=time.monotonic() + seconds,
                                 sanitizer=sanitizer, process_context=self.context, **kwargs)

    def test_worker_sanitizes_before_pipe_and_uses_request_stage(self):
        with patch.object(head, '_head_once', side_effect=synthetic_head):
            result = self.run_head()
        self.assertEqual(result, {'ok': True, 'requestAttempted': True,
                                 'observation': {'status': 302, 'headerCount': 2,
                                                 'headerBytes': 100, 'bodyBytesRead': 0}})
        self.assertNotIn('RAW', json.dumps(result))
        self.assertNotIn('Signature', json.dumps(result))

    def test_worker_exception_is_closed_without_raw_values(self):
        with patch.object(head, '_head_once', side_effect=synthetic_head):
            result = self.run_head(sanitizer=exploding_sanitizer)
        self.assertEqual(result, {'ok': False, 'requestAttempted': True,
                                 'transport_error': 'head-sanitizer-failed'})

    def test_os_and_python_stdout_stderr_are_suppressed(self):
        # pytest/unittest capture cannot observe forked StringIO copies. Real OS
        # pipes verify dup2 and redirect_stdout together without writing files.
        read_fd, write_fd = os.pipe()
        old_out, old_err = os.dup(1), os.dup(2)
        try:
            os.dup2(write_fd, 1)
            os.dup2(write_fd, 2)
            with patch.object(head, '_head_once', side_effect=synthetic_head):
                result = self.run_head(sanitizer=noisy_sanitizer)
        finally:
            os.dup2(old_out, 1)
            os.dup2(old_err, 2)
            for fd in (write_fd, old_out, old_err):
                os.close(fd)
        try:
            emitted = os.read(read_fd, 65536)
        finally:
            os.close(read_fd)
        self.assertEqual(emitted, b'')
        self.assertTrue(result['ok'])

    def test_oversized_sanitizer_result_fails_closed(self):
        with patch.object(head, '_head_once', side_effect=synthetic_head):
            result = self.run_head(sanitizer=huge_sanitizer)
        self.assertEqual(result['transport_error'], 'head-result-too-large')

    def test_explicit_failure_before_attempt_is_proven_false(self):
        with patch.object(head, '_head_once', side_effect=synthetic_explicit_pre_request_failure):
            result = self.run_head()
        self.assertEqual(result['requestAttempted'], False)
        self.assertEqual(result['transport_error'], 'head-transport-failed')

    def test_blocked_dns_is_killed_and_reaped_before_return(self):
        with patch.object(socket, 'getaddrinfo', side_effect=blocking_dns):
            start = time.monotonic()
            result = self.run_head(seconds=0.45)
        self.assertLess(time.monotonic() - start, 0.7)
        self.assertEqual(result['transport_error'], 'head-deadline-exceeded')
        self.assertEqual(result['requestAttempted'], 'unknown')

    def test_connect_tls_send_recv_and_close_blocking_are_all_supervised(self):
        dns = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                '', ('192.0.2.1', 443))]
        for operation in ('connect', 'do_handshake', 'sendall', 'recv', 'close'):
            with self.subTest(operation=operation):
                stream = FakeSocket()
                setattr(stream, operation, synthetic_blocking_operation)
                with patch.object(socket, 'getaddrinfo', return_value=dns), \
                        patch.object(socket, 'socket', return_value=stream), \
                        patch.object(ssl, 'SSLContext', return_value=FakeContext(stream)):
                    start = time.monotonic()
                    result = self.run_head(seconds=0.4)
                self.assertLess(time.monotonic() - start, 0.65)
                self.assertEqual(result['transport_error'], 'head-deadline-exceeded')
                if operation in ('sendall', 'recv', 'close'):
                    self.assertIs(result['requestAttempted'], True)
                else:
                    self.assertEqual(result['requestAttempted'], 'unknown')

    def test_blocked_sanitizer_is_supervised_after_request(self):
        with patch.object(head, '_head_once', side_effect=synthetic_head):
            start = time.monotonic()
            result = self.run_head(seconds=0.4, sanitizer=synthetic_blocking_operation)
        self.assertLess(time.monotonic() - start, 0.65)
        self.assertEqual(result['transport_error'], 'head-deadline-exceeded')
        self.assertIs(result['requestAttempted'], True)

    def test_partial_pipe_frame_cannot_block_supervisor(self):
        with patch.object(head, '_worker', synthetic_partial_frame_worker):
            start = time.monotonic()
            result = self.run_head(seconds=0.45)
        self.assertLess(time.monotonic() - start, 0.7)
        self.assertEqual(result['transport_error'], 'head-deadline-exceeded')

    def test_sigterm_ignored_escalates_to_kill_and_no_late_worker(self):
        with patch.object(head, '_worker', synthetic_ignore_term_worker):
            start = time.monotonic()
            result = self.run_head(seconds=0.45)
        self.assertLess(time.monotonic() - start, 0.7)
        self.assertEqual(result['transport_error'], 'head-deadline-exceeded')
        self.assertIs(result['requestAttempted'], True)

    def test_success_child_stuck_after_result_is_stopped_before_return(self):
        with patch.object(head, '_worker', synthetic_after_result_block_worker):
            result = self.run_head()
        self.assertTrue(result['ok'])

    def test_crashes_never_claim_zero_requests(self):
        for worker in (synthetic_crash_worker, synthetic_before_attempt_crash_worker):
            with self.subTest(worker=worker.__name__), patch.object(head, '_worker', worker):
                result = self.run_head()
            self.assertEqual(result['transport_error'], 'head-worker-failed')
            self.assertEqual(result['requestAttempted'], 'unknown')

    def test_protocol_requires_stage_before_success(self):
        with patch.object(head, '_worker', synthetic_bad_protocol_worker):
            result = self.run_head()
        self.assertEqual(result['transport_error'], 'head-worker-protocol-invalid')

    def test_expired_deadline_starts_no_process(self):
        with patch.object(self.context, 'Process') as factory:
            result = self.run_head(seconds=0.1)
        factory.assert_not_called()
        self.assertEqual(result['requestAttempted'], False)

    def test_source_limit_includes_cleanup_and_does_not_reset_global_deadline(self):
        with patch.object(head, 'SOURCE_SECONDS', 0.45), \
                patch.object(head, '_worker', synthetic_ignore_term_worker):
            start = time.monotonic()
            result = self.run_head(seconds=90)
        self.assertLess(time.monotonic() - start, 0.7)
        self.assertEqual(result['transport_error'], 'head-deadline-exceeded')

    def test_default_fork_works_with_importable_pure_worker(self):
        with patch.object(head, '_worker', synthetic_success_worker):
            result = head.observe_head(Source(), absolute_deadline=time.monotonic() + 3,
                                       sanitizer=safe_sanitizer)
        self.assertTrue(result['ok'], result)

    def test_spawn_and_multithreaded_hosts_fail_before_child_start(self):
        context = multiprocessing.get_context('spawn')
        with patch.object(context, 'Process') as factory:
            result = head.observe_head(Source(), absolute_deadline=time.monotonic() + 3,
                                       sanitizer=safe_sanitizer, process_context=context)
        factory.assert_not_called()
        self.assertEqual(result['transport_error'], 'head-platform-unsupported')
        self.assertIs(result['requestAttempted'], False)
        with patch.object(head.threading, 'active_count', return_value=2):
            result = self.run_head()
        self.assertEqual(result['transport_error'], 'head-platform-unsupported')
        self.assertIs(result['requestAttempted'], False)

    def test_total_pipe_envelope_counts_framing_and_stage_messages(self):
        class Sink:
            def __init__(self): self.data = []
            def send_bytes(self, data): self.data.append(data)
        sink = Sink()
        output = head._SafePipe(sink)
        output.send({'stage': 'ready'})
        output.send({'stage': 'request-attempted'})
        with self.assertRaisesRegex(head.HeadTransportError, '^head-result-too-large$'):
            output.send({'ok': True, 'data': 'a' * (head.MAX_RESULT_BYTES - 50)})
        self.assertLessEqual(sum(len(data) + 4 for data in sink.data), head.MAX_RESULT_BYTES)


if __name__ == '__main__':
    unittest.main()
