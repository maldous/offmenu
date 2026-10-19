"""Inactive, exact-source HTTPS HEAD transport for an owner-gated diagnostic.

Importing this module does not perform I/O or authorize a request. The owner must
validate provenance, one-shot claims and live guards before calling observe_head.
A source supplies ``exact_url`` with a redacted repr. The trusted, top-level pure
sanitizer runs in the child; only its bounded JSON output crosses the private
pipe. No response body API, redirect handling, retry, cookie jar, HTTP client,
proxy configuration or ambient authentication is used here.

Each application-facing TLS recv requests exactly one byte, including across
informational sections, and stops at the final CRLFCRLF. TLS implementations may
process encrypted records internally; those are not application body reads.
"""
from contextlib import redirect_stderr, redirect_stdout
import ipaddress
import json
import math
import multiprocessing
import os
import re
import select
import socket
import ssl
import struct
import threading
import time
from urllib.parse import urlsplit

MAX_HEADER_BYTES = 65536
MAX_FINAL_FIELDS = 100
MAX_RESULT_BYTES = 65536
SOURCE_SECONDS = 15.0
_CLEANUP_SECONDS = 0.25
_MIN_WORK_SECONDS = 0.01
_CODES = frozenset((
    'head-input-invalid', 'head-header-invalid',
    'head-header-envelope-exceeded', 'head-header-field-limit',
    'head-deadline-exceeded', 'head-transport-failed',
    'head-sanitizer-failed', 'head-worker-failed',
    'head-worker-protocol-invalid', 'head-result-too-large',
    'head-worker-cleanup-failed', 'head-platform-unsupported',
))
ERROR_CODES = _CODES
_TOKEN = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_STATUS = re.compile(rb'HTTP/1\.[01] ([1-5][0-9]{2}) [\t\x20-\x7e\x80-\xff]*\r\n\Z')
_HOST = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\Z')


class HeadTransportError(Exception):
    """An allowlisted code, never the originating exception or raw metadata."""
    def __init__(self, code):
        self.code = code if code in _CODES else 'head-transport-failed'
        super().__init__(self.code)


class SupervisorCleanupError(HeadTransportError):
    """Fatal: the owner must stop if the OS cannot verify worker termination."""


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise HeadTransportError('head-deadline-exceeded')
    return remaining


def _target(url):
    """Validate without decoding, normalizing, repairing or replacing the target."""
    try:
        if (type(url) is not str or len(url) > MAX_HEADER_BYTES
                or not url.startswith('https://') or '#' in url or '\\' in url
                or any(ord(c) < 33 or ord(c) > 126 for c in url)
                or re.search(r'%(?![0-9A-Fa-f]{2})', url)):
            raise ValueError
        parts = urlsplit(url)
        if (not parts.hostname or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)):
            raise ValueError
        host = parts.hostname
        if ':' in host:
            ipaddress.IPv6Address(host)
            if '%' in host:
                raise ValueError
        elif not _HOST.fullmatch(host) or any(not label or len(label) > 63
                or label.startswith('-') or label.endswith('-')
                for label in host.split('.')):
            raise ValueError
        authority = parts.netloc
        # Reject unusual authority spellings rather than silently repairing them.
        allowed_authorities = {host, host + ':443'}
        if ':' in host:
            allowed_authorities = {'[' + host + ']', '[' + host + ']:443'}
        if authority.lower() not in allowed_authorities:
            raise ValueError
        tail = url[len('https://') + len(authority):]
        target = tail if tail.startswith('/') else '/' + tail
        request = ('HEAD ' + target + ' HTTP/1.1\r\nHost: ' + authority
                   + '\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n')
        return host, request.encode('ascii')
    except (ValueError, TypeError, UnicodeError, AttributeError):
        raise HeadTransportError('head-input-invalid') from None


def _read_head(tls_socket, deadline):
    """Read only status/header bytes; retain duplicates for strict sanitization."""
    wire_bytes = 0

    def line():
        nonlocal wire_bytes
        value = bytearray()
        while True:
            if wire_bytes >= MAX_HEADER_BYTES:
                raise HeadTransportError('head-header-envelope-exceeded')
            tls_socket.settimeout(_remaining(deadline))
            byte = tls_socket.recv(1)
            if type(byte) is not bytes or len(byte) != 1:
                raise HeadTransportError('head-header-invalid')
            wire_bytes += 1
            value.extend(byte)
            if byte == b'\n':
                if not value.endswith(b'\r\n'):
                    raise HeadTransportError('head-header-invalid')
                return bytes(value)
            if len(value) > 1 and value[-2] == 13:
                raise HeadTransportError('head-header-invalid')

    while True:
        status_line = line()
        match = _STATUS.fullmatch(status_line)
        if not match:
            raise HeadTransportError('head-header-invalid')
        status = int(match.group(1))
        if status == 101:
            raise HeadTransportError('head-header-invalid')
        headers = []
        while True:
            raw = line()
            if raw == b'\r\n':
                break
            name, separator, value = raw[:-2].partition(b':')
            if (not separator or not _TOKEN.fullmatch(name)
                    or any(c < 32 and c != 9 or c == 127 for c in value)):
                raise HeadTransportError('head-header-invalid')
            headers.append((name.decode('ascii'), value.lstrip(b' \t').decode('latin-1')))
            if status >= 200 and len(headers) > MAX_FINAL_FIELDS:
                raise HeadTransportError('head-header-field-limit')
        if status >= 200:
            _remaining(deadline)
            return status, headers, wire_bytes


def _head_once(url, deadline, *, on_request=None):
    """One DNS resolution, one TCP connection, one TLS session, one exact HEAD.

    Intended only inside the supervised process. No address failover or retry.
    Closing TLS does not unwrap or read peer close-notify/application bytes.
    """
    raw_socket = tls_socket = None
    try:
        host, request = _target(url)
        _remaining(deadline)
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM,
                                       proto=socket.IPPROTO_TCP)
        _remaining(deadline)
        if not addresses:
            raise HeadTransportError('head-transport-failed')
        family, socktype, proto, _, address = addresses[0]
        raw_socket = socket.socket(family, socktype, proto)
        raw_socket.settimeout(_remaining(deadline))
        raw_socket.connect(address)
        _remaining(deadline)
        # Unlike create_default_context(), this never enables SSLKEYLOGFILE.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_default_certs(ssl.Purpose.SERVER_AUTH)
        context.set_alpn_protocols(['http/1.1'])
        tls_socket = context.wrap_socket(raw_socket, server_hostname=host,
                                        do_handshake_on_connect=False)
        tls_socket.settimeout(_remaining(deadline))
        tls_socket.do_handshake()
        _remaining(deadline)
        if on_request is not None:
            on_request()
        tls_socket.settimeout(_remaining(deadline))
        tls_socket.sendall(request)
        result = _read_head(tls_socket, deadline)
    except HeadTransportError:
        raise
    except (TimeoutError, socket.timeout):
        raise HeadTransportError('head-deadline-exceeded') from None
    except BaseException:
        raise HeadTransportError('head-transport-failed') from None
    finally:
        # A blocked close is contained by the outer process deadline, too.
        for stream in (tls_socket, raw_socket):
            if stream is not None:
                try:
                    stream.close()
                except BaseException:
                    pass
    _remaining(deadline)
    return result


def _encoded(frame):
    """The pipe carries JSON, never pickle or exception objects."""
    try:
        data = json.dumps(frame, ensure_ascii=True, allow_nan=False,
                          separators=(',', ':')).encode('ascii')
    except BaseException:
        raise HeadTransportError('head-sanitizer-failed') from None
    if len(data) > MAX_RESULT_BYTES:
        raise HeadTransportError('head-result-too-large')
    return data


class _SafePipe:
    """Bound all stage, framing and result bytes together, not just each frame."""
    def __init__(self, pipe):
        self.pipe = pipe
        self.sent = 0

    def send(self, frame):
        data = _encoded(frame)
        if self.sent + len(data) + 4 > MAX_RESULT_BYTES:
            raise HeadTransportError('head-result-too-large')
        self.pipe.send_bytes(data)
        self.sent += len(data) + 4


def _send_frame(pipe, frame):
    pipe.send(frame)


def _worker(source, deadline, sanitizer, pipe):
    """Trusted child entrypoint. Raw values stay in this process's memory only."""
    attempted = False
    output = _SafePipe(pipe)
    try:
        # OS descriptors also suppress native tracebacks and callback os.write.
        with open(os.devnull, 'w') as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            with redirect_stdout(sink), redirect_stderr(sink):
                try:
                    import resource
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                except (ImportError, OSError, ValueError):
                    return
                _send_frame(output, {'stage': 'ready'})

                def request_started():
                    nonlocal attempted
                    _send_frame(output, {'stage': 'request-attempted'})
                    attempted = True

                try:
                    status, headers, count = _head_once(source.exact_url, deadline,
                                                       on_request=request_started)
                    _remaining(deadline)
                    try:
                        safe = sanitizer(source, status, headers, count)
                    except BaseException:
                        raise HeadTransportError('head-sanitizer-failed') from None
                    if type(safe) is not dict:
                        raise HeadTransportError('head-sanitizer-failed')
                    _remaining(deadline)
                    _send_frame(output, {'ok': True, 'requestAttempted': attempted,
                                       'observation': safe})
                except BaseException as exc:
                    code = exc.code if isinstance(exc, HeadTransportError) else 'head-worker-failed'
                    _send_frame(output, {'ok': False, 'requestAttempted': attempted,
                                       'transport_error': code})
    except BaseException:
        # No traceback or raw exception leaves this child, including pipe errors.
        pass
    finally:
        pipe.close()


def _error(code, attempted='unknown'):
    return {'ok': False, 'requestAttempted': attempted,
            'transport_error': code if code in _CODES else 'head-worker-failed'}


def _reap(process, cutoff):
    """Terminate, escalate, and verify death before any ordinary return."""
    if process.is_alive():
        process.terminate()
        process.join(timeout=min(0.03, max(0.0, cutoff - time.monotonic())))
    if process.is_alive():
        process.kill()
    process.join(timeout=max(0.0, cutoff - time.monotonic()))
    if process.is_alive():
        # Never return an apparently completed observation with an unverified child.
        # An OS failure to reap is fatal for the diagnostic, not a retry condition.
        raise SupervisorCleanupError('head-worker-cleanup-failed') from None
    process.close()


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError


def _read_frames(fd, deadline):
    """Incremental nonblocking multiprocessing send_bytes framing.

    Connection.recv_bytes can block on an incomplete frame after poll succeeds.
    Reading the POSIX pipe ourselves keeps a truncated/stuck writer supervised.
    """
    pending = bytearray()
    received = 0
    os.set_blocking(fd, False)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise HeadTransportError('head-deadline-exceeded')
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            raise HeadTransportError('head-deadline-exceeded')
        if received >= MAX_RESULT_BYTES:
            raise HeadTransportError('head-worker-protocol-invalid')
        try:
            chunk = os.read(fd, min(4096, MAX_RESULT_BYTES - received))
        except BlockingIOError:
            continue
        if not chunk:
            raise HeadTransportError('head-worker-failed')
        received += len(chunk)
        pending.extend(chunk)
        while len(pending) >= 4:
            length = struct.unpack('!i', pending[:4])[0]
            if not 0 < length <= MAX_RESULT_BYTES:
                raise HeadTransportError('head-worker-protocol-invalid')
            if len(pending) < length + 4:
                break
            data = bytes(pending[4:length + 4])
            del pending[:length + 4]
            try:
                frame = json.loads(data, object_pairs_hook=_strict_pairs,
                                   parse_constant=_reject_constant)
                if type(frame) is not dict:
                    raise ValueError
            except (ValueError, UnicodeError, RecursionError):
                raise HeadTransportError('head-worker-protocol-invalid') from None
            yield frame


def observe_head(source, *, absolute_deadline, sanitizer, process_context=None):
    """Run one bounded HEAD and return only a sanitized result or closed error.

    ``absolute_deadline`` is the owner's aggregate monotonic deadline (90s for
    the complete five-source diagnostic, including guards). This call also caps
    itself at 15s including process startup, DNS, TLS, close, and cleanup. A short
    cleanup reserve is deducted from the child's work budget. The sanitizer must
    be a trusted pure top-level callable and must never return raw URLs, header
    values, credentials or exception strings. The owner must be a single-threaded
    POSIX process. Fork avoids spawn's synchronous, potentially blocking source
    serialization before supervision begins; other start methods fail closed.

    ``requestAttempted`` is true after the pre-send child stage, false only with
    positive proof of no attempt, and 'unknown' after an unproven worker failure.
    A fatal SupervisorCleanupError requires the owner to stop all further work.
    This transport creates no files except opening /dev/null, and is inactive
    until an owner-gated caller explicitly invokes it.
    """
    started = time.monotonic()
    if (type(absolute_deadline) not in (int, float)
            or not math.isfinite(absolute_deadline) or not callable(sanitizer)):
        return _error('head-input-invalid', False)
    cutoff = min(absolute_deadline, started + SOURCE_SECONDS)
    work_deadline = cutoff - _CLEANUP_SECONDS
    if work_deadline - started < _MIN_WORK_SECONDS:
        return _error('head-deadline-exceeded', False)
    if (os.name != 'posix' or threading.active_count() != 1
            or threading.current_thread() is not threading.main_thread()):
        return _error('head-platform-unsupported', False)
    try:
        _target(source.exact_url)
    except BaseException:
        return _error('head-input-invalid', False)
    try:
        context = process_context or multiprocessing.get_context('fork')
        if context.get_start_method() != 'fork':
            return _error('head-platform-unsupported', False)
    except BaseException:
        return _error('head-platform-unsupported', False)
    reader = writer = process = None
    attempted = 'unknown'
    outcome = None
    launched = False
    ready = False
    try:
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(target=_worker,
                                  args=(source, work_deadline, sanitizer, writer),
                                  daemon=True)
        _remaining(work_deadline)
        process.start()
        launched = True
        writer.close()
        for frame in _read_frames(reader.fileno(), work_deadline):
            if frame == {'stage': 'ready'} and not ready:
                ready = True
                continue
            if frame == {'stage': 'request-attempted'} and ready and attempted == 'unknown':
                attempted = True
                continue
            if (ready and type(frame.get('ok')) is bool
                    and type(frame.get('requestAttempted')) is bool
                    and (attempted is not True or frame['requestAttempted'] is True)):
                if frame['ok'] is True and (set(frame) == {'ok', 'requestAttempted', 'observation'}
                        and type(frame['observation']) is dict and attempted is True
                        and frame['requestAttempted'] is True):
                    outcome = frame
                    break
                if frame['ok'] is False and (set(frame) == {'ok', 'requestAttempted', 'transport_error'}
                        and frame['transport_error'] in _CODES
                        and (frame['requestAttempted'] is False or attempted is True)):
                    outcome = frame
                    break
            raise HeadTransportError('head-worker-protocol-invalid')
    except HeadTransportError as exc:
        outcome = _error(exc.code, attempted)
    except BaseException:
        outcome = _error('head-worker-failed', attempted)
    finally:
        if writer is not None:
            writer.close()
        if reader is not None:
            reader.close()
        if launched:
            _reap(process, cutoff)
        elif process is not None:
            # A failed start can still create a child on some contexts.
            if process.pid is not None:
                _reap(process, cutoff)
            else:
                process.close()
    if time.monotonic() > cutoff:
        return _error('head-deadline-exceeded', attempted)
    return outcome or _error('head-worker-failed', attempted)
