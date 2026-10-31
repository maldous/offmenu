"""Offline synthetic capture tests: no real custody, socket, TLS or identity calls."""
import base64
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location(
    'capture', Path(__file__).resolve().parents[2] / 'tools/delivery/github_app_capture.py')
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
STATE = 's' * 43
CODE = 'c' * 40
TARGET = '/callback?code=' + CODE + '&state=' + STATE
PEM = ('-----BEGIN RSA PRIVATE KEY-----\n' +
       base64.b64encode(b'\x30' + b'x' * 127).decode() +
       '\n-----END RSA PRIVATE KEY-----\n')
PROOF = {'version': 1, 'protected_coordinator_source_sha256': 'a' * 64,
         'protected_unit_sha256': 'b' * 64, 'guard_receipt_sha256': 'c' * 64,
         'actual_host_proof_accepted': True, 'credentials_absent': True,
         'source_custody_accepted': True, 'root_custody_accepted': True}


def response(**changes):
    obj = {'id': 123, 'owner': {'login': 'maldous'}, 'permissions': dict(c.PERMISSIONS),
           'events': [], 'public': False, 'pem': PEM,
           'client_secret': 'UNUSED-SECRET', 'webhook_secret': 'UNUSED-SECRET'}
    obj.update(changes)
    return 201, [('Content-Type', 'application/json')], json.dumps(obj).encode()


class MemoryIO:
    """Descriptor filesystem with explicit synthetic root metadata and short writes."""
    O_RDONLY, O_RDWR, O_CREAT, O_EXCL = os.O_RDONLY, os.O_RDWR, os.O_CREAT, os.O_EXCL
    O_NOFOLLOW, O_NONBLOCK, O_DIRECTORY = os.O_NOFOLLOW, os.O_NONBLOCK, os.O_DIRECTORY
    SEEK_SET, SEEK_END = os.SEEK_SET, os.SEEK_END

    def __init__(self):
        self.nodes, self.fds = {}, {}
        self.next_fd = 10
        self.syncs, self.opens = [], []
        self.fail_path = None
        for path in ('/', '/etc', '/var', '/var/lib', '/etc/offmenu-publisher',
                     '/var/lib/offmenu-publisher'):
            self.add(path, stat.S_IFDIR | (0o750 if path.endswith('publisher') else 0o755),
                     gid=976 if path.endswith('publisher') else 0)
        self.add(c.PROOF, stat.S_IFREG | 0o440, json.dumps(PROOF).encode())

    def add(self, path, mode, data=b'', uid=0, gid=0):
        self.nodes[path] = SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid,
                                          st_nlink=1, st_dev=1, st_ino=len(self.nodes) + 1,
                                          st_size=len(data), data=data)

    def open(self, path, flags, mode=0, dir_fd=None):
        if dir_fd is not None:
            path = self.fds[dir_fd][0].rstrip('/') + '/' + path
        self.opens.append((path, flags))
        if path in self.nodes:
            if flags & self.O_CREAT and flags & self.O_EXCL:
                raise FileExistsError()
            if stat.S_ISLNK(self.nodes[path].st_mode) and flags & self.O_NOFOLLOW:
                raise OSError('synthetic symlink')
        elif flags & self.O_CREAT:
            self.add(path, stat.S_IFREG | mode)
        else:
            raise FileNotFoundError()
        if flags & self.O_DIRECTORY and not stat.S_ISDIR(self.nodes[path].st_mode):
            raise OSError('synthetic non-directory')
        self.next_fd += 1
        self.fds[self.next_fd] = [path, 0]
        return self.next_fd

    def fstat(self, fd):
        return copy.copy(self.nodes[self.fds[fd][0]])

    def stat(self, path, dir_fd=None, follow_symlinks=False):
        if dir_fd is not None:
            path = self.fds[dir_fd][0].rstrip('/') + '/' + path
        if path not in self.nodes:
            raise FileNotFoundError()
        return copy.copy(self.nodes[path])

    def read(self, fd, count):
        path, offset = self.fds[fd]
        data = self.nodes[path].data[offset:offset + count]
        self.fds[fd][1] += len(data)
        return data

    def write(self, fd, raw):
        path, offset = self.fds[fd]
        if path == self.fail_path and offset > 0:
            raise OSError('PRIVATE ERROR MUST NOT ESCAPE')
        raw = raw[:17]  # Exercise write-all rather than idealized single writes.
        node = self.nodes[path]
        node.data = node.data[:offset] + raw + node.data[offset + len(raw):]
        node.st_size = len(node.data)
        self.fds[fd][1] += len(raw)
        return len(raw)

    def fchown(self, fd, uid, gid):
        node = self.nodes[self.fds[fd][0]]
        node.st_uid, node.st_gid = uid, gid

    def fchmod(self, fd, mode):
        node = self.nodes[self.fds[fd][0]]
        node.st_mode = stat.S_IFMT(node.st_mode) | mode

    def lseek(self, fd, offset, whence):
        self.fds[fd][1] = offset + (self.fstat(fd).st_size if whence == self.SEEK_END else 0)

    def fsync(self, fd):
        self.syncs.append(self.fds[fd][0])

    def close(self, fd):
        del self.fds[fd]

    @property
    def digest(self):
        return hashlib.sha256(self.nodes[c.PROOF].data).hexdigest()


class CaptureTests(unittest.TestCase):
    def run_capture(self, io=None, transport=None, listener=None, **kwargs):
        io = io or MemoryIO()
        transport = transport or Mock(return_value=response())
        listener = listener or (lambda session, announce: session.request(TARGET, [c.HOST]))
        result = c.capture_once(io.digest, custody=c.Custody(io), identity=lambda: (0, 0),
                                state_factory=lambda n: STATE, clock=lambda: 10,
                                transport=transport, listener=listener,
                                guard=contextlib.nullcontext, **kwargs)
        self.assertFalse(io.fds)
        return result, io, transport

    def test_manifest_and_escaped_nonautomatic_form(self):
        m = c.manifest()
        self.assertEqual(m['default_permissions'], c.PERMISSIONS)
        self.assertEqual(m['redirect_url'], c.CALLBACK)
        self.assertFalse(m['public'])
        self.assertEqual(m['hook_attributes'], {'url': 'https://github.com/maldous/offmenu', 'active': False})
        page = c.form(STATE).decode()
        self.assertIn('https://github.com/settings/apps/new?state=' + STATE, page)
        self.assertIn('&quot;', page)
        self.assertNotIn('<script', page)
        self.assertNotIn('onload', page)
        self.assertEqual(m['default_events'], [])
        self.assertFalse(m['request_oauth_on_install'])

    def test_callback_boundaries(self):
        self.assertEqual(c.parse_request(TARGET, [c.HOST], STATE), ('/callback', CODE))
        self.assertEqual(c.parse_request('/start?state=' + STATE, [c.HOST], STATE), ('/start', None))
        bad = [TARGET + '&extra=x', TARGET + '&code=' + CODE,
               TARGET.replace(STATE, 'z' * 43), TARGET.replace(CODE, 'a'),
               TARGET.replace('/callback', '/unknown'), 'https://' + c.HOST + TARGET,
               TARGET + '#fragment', TARGET.replace(CODE, '%63' * 40),
               '/callback?state=' + STATE, TARGET + '&state=' + STATE, TARGET + '&PRIVATE-MALFORMED-CODE']
        for target in bad:
            with self.subTest(target=target), self.assertRaises(c.Held):
                c.parse_request(target, [c.HOST], STATE)
        for hosts in ([], [c.HOST, c.HOST], ['localhost:49181'], ['evil.example'], ['127.0.0.1']):
            with self.subTest(hosts=hosts), self.assertRaises(c.Held):
                c.parse_request(TARGET, hosts, STATE)
        with self.assertRaises(c.Held):
            c.parse_request(TARGET, [c.HOST], STATE, True)

    def test_documented_conversion_without_public(self):
        status, headers, raw = response()
        data = json.loads(raw)
        data.pop('public')
        raw = json.dumps(data).encode()
        self.assertEqual(c.validate_response(status, [('Content-Type', 'application/json')], raw),
                         (123, PEM.encode()))

    def test_response_rejections(self):
        self.assertEqual(c.validate_response(*response()), (123, PEM.encode()))
        changes = [{'id': True}, {'id': 0}, {'id': '123'}, {'owner': {'login': 'other'}},
                   {'permissions': {'contents': 'write', 'pull_requests': 'write'}},
                   {'permissions': dict(c.PERMISSIONS, actions='write')},
                   {'permissions': dict(c.PERMISSIONS, metadata='write')},
                   {'events': ['push']}, {'public': True}, {'hook_attributes': {'active': True}},
                   {'hook_attributes': {'url': 'https://evil.example', 'active': False}},
                   {'hook_attributes': {'active': False}},
                   {'hook_url': 'https://evil.example'}, {'pem': PEM.replace('END RSA', 'END')},
                   {'pem': PEM.replace('eHh4', '!!!!')}, {'pem': 'x' * 65537}]
        for change in changes:
            with self.subTest(change=list(change)), self.assertRaises(c.Held):
                c.validate_response(*response(**change))
        for status, headers, raw in [(302, [('Location', 'https://evil')], b'{}'),
                                     (201, [], b'{}'),
                                     (201, [('Content-Type', 'text/plain')], b'{}'),
                                     (201, [('Content-Type', 'application/json')] * 2, b'{}'),
                                     (201, [('Content-Type', 'application/json'), ('Content-Encoding', 'gzip')], b'{}'),
                                     (201, [('Content-Type', 'application/json'), ('Location', 'https://evil')], b'{}'),
                                     (201, [('Content-Type', 'application/json'), ('Content-Length', '1')], b'{}'),
                                     (201, [('Content-Type', 'application/json')], b'x' * (c.LIMIT + 1)),
                                     (201, [('Content-Type', 'application/json')], b'{"id":1,"id":2}')]:
            with self.subTest(status=status, headers=headers), self.assertRaises(c.Held):
                c.validate_response(status, headers, raw)

    def test_success_exact_custody_and_receipts(self):
        result, io, transport = self.run_capture()
        self.assertEqual(result['phase'], 'captured')
        transport.assert_called_once_with(CODE, 30)
        for path in (c.KEY, c.REGISTRATION):
            node = io.nodes[path]
            self.assertEqual((node.st_uid, node.st_gid, stat.S_IMODE(node.st_mode)), (0, 976, 0o440))
            self.assertIn(path, io.syncs)
        self.assertEqual(io.nodes[c.KEY].data, PEM.encode())
        node = io.nodes[c.RECEIPT]
        self.assertEqual((node.st_uid, node.st_gid, stat.S_IMODE(node.st_mode)), (0, 0, 0o600))
        phases = [json.loads(line)['phase'] for line in node.data.splitlines()]
        self.assertEqual(phases, ['intent', 'conversion-intent', 'converted', 'captured'])
        for path in (c.RECEIPT, c.REGISTRATION):
            self.assertNotIn(b'PRIVATE KEY', io.nodes[path].data)
            self.assertNotIn(b'UNUSED-SECRET', io.nodes[path].data)
            self.assertNotIn(CODE.encode(), io.nodes[path].data)
        for path, flags in io.opens:
            self.assertTrue(flags & os.O_NOFOLLOW)
            if path in (c.KEY, c.REGISTRATION, c.RECEIPT):
                self.assertTrue(flags & os.O_EXCL)
        self.assertNotIn('pem', result)

    def test_proof_false_missing_drift_and_unsafe(self):
        for field in ('actual_host_proof_accepted', 'credentials_absent', 'source_custody_accepted',
                      'root_custody_accepted', 'protected_unit_sha256'):
            io = MemoryIO()
            proof = dict(PROOF, **{field: False})
            io.nodes[c.PROOF].data = json.dumps(proof).encode()
            io.nodes[c.PROOF].st_size = len(io.nodes[c.PROOF].data)
            result, io, transport = self.run_capture(io)
            self.assertEqual(result, {'phase': 'held'})
            transport.assert_not_called()
            self.assertNotIn(c.RECEIPT, io.nodes)
        with self.assertRaises(c.Held):
            c.validate_proof(json.dumps(PROOF).encode(), '0' * 64)
        for kind in ('missing', 'symlink', 'writable', 'owner', 'hardlink'):
            io = MemoryIO()
            if kind == 'missing':
                del io.nodes[c.PROOF]
                digest = 'a' * 64
            else:
                digest = io.digest
                if kind == 'symlink':
                    io.nodes[c.PROOF].st_mode = stat.S_IFLNK | 0o777
                elif kind == 'writable':
                    io.nodes[c.PROOF].st_mode |= 0o020
                elif kind == 'owner':
                    io.nodes[c.PROOF].st_uid = 1000
                else:
                    io.nodes[c.PROOF].st_nlink = 2
            store = c.Custody(io)
            with self.assertRaises((c.Held, OSError)):
                store.prepare(digest)
            store.close()
            self.assertNotIn(c.RECEIPT, io.nodes)

    def test_existing_files_and_unsafe_directories(self):
        for path in (c.KEY, c.REGISTRATION, c.RECEIPT):
            for mode in (stat.S_IFREG | 0o440, stat.S_IFLNK | 0o777):
                io = MemoryIO()
                io.add(path, mode)
                result, io, transport = self.run_capture(io)
                self.assertEqual(result['phase'], 'held')
                transport.assert_not_called()
        for path, attr, value in [('/etc', 'st_uid', 1000), ('/var', 'st_mode', stat.S_IFDIR | 0o777),
                                  ('/etc/offmenu-publisher', 'st_gid', 1000),
                                  ('/var/lib/offmenu-publisher', 'st_mode', stat.S_IFDIR | 0o755),
                                  ('/etc', 'st_mode', stat.S_IFLNK | 0o755)]:
            io = MemoryIO()
            setattr(io.nodes[path], attr, value)
            result, io, transport = self.run_capture(io)
            self.assertEqual(result['phase'], 'held')
            transport.assert_not_called()

    def test_partial_write_preserved_and_blocks_second_invocation(self):
        for path in (c.KEY, c.REGISTRATION, c.RECEIPT):
            io = MemoryIO()
            io.fail_path = path
            result, io, transport = self.run_capture(io)
            self.assertEqual(result['phase'], 'held' if path == c.RECEIPT else 'partial')
            self.assertIn(path, io.nodes)
            self.assertTrue(io.nodes[path].data)
            second, _, again = self.run_capture(io)
            self.assertEqual(second['phase'], 'held')
            again.assert_not_called()

    def test_unknown_no_retry_replay_or_secret_error(self):
        transport = Mock(side_effect=OSError('SECRET RESPONSE PEM CODE'))
        def listener(session, announce):
            session.request(TARGET, [c.HOST])
            self.assertTrue(session.consumed)
            with self.assertRaises(c.Held):
                session.request(TARGET, [c.HOST])
        result, io, _ = self.run_capture(transport=transport, listener=listener)
        self.assertEqual(result, {'phase': 'unknown'})
        transport.assert_called_once()
        self.assertIn(b'unknown', io.nodes[c.RECEIPT].data)
        self.assertNotIn(b'SECRET', io.nodes[c.RECEIPT].data)
        self.assertNotIn(c.KEY, io.nodes)
        second, _, again = self.run_capture(io)
        self.assertEqual(second['phase'], 'held')
        again.assert_not_called()

    def test_bad_response_consumed_and_expiry(self):
        result, io, transport = self.run_capture(transport=Mock(return_value=response(public=True)))
        self.assertEqual(result['phase'], 'unknown')
        self.assertNotIn(c.KEY, io.nodes)
        result, io, transport = self.run_capture(listener=lambda session, announce: None)
        self.assertEqual(result['phase'], 'expired')
        transport.assert_not_called()
        self.assertIn(b'expired', io.nodes[c.RECEIPT].data)
        session = c.Session(Mock(), STATE, 1, lambda: 2, Mock())
        with self.assertRaises(c.Held):
            session.request(TARGET, [c.HOST])
        self.assertFalse(session.consumed)

    def test_nonroot_never_prepares(self):
        for identity in ((1000, 1000), (1000, 0), (0, 1000)):
            store = Mock()
            result = c.capture_once('a' * 64, identity=lambda: identity, custody=store,
                                    guard=contextlib.nullcontext)
            self.assertEqual(result['phase'], 'held')
            store.prepare.assert_not_called()

    def test_intent_precedes_listener_and_unused_conversion_never_retries(self):
        fs = MemoryIO()
        def listener(session, announce):
            records = [json.loads(line) for line in fs.nodes[c.RECEIPT].data.splitlines()]
            self.assertEqual([row['phase'] for row in records], ['intent'])
            self.assertEqual(records[0]['proof_sha256'], fs.digest)
            self.assertIn(c.RECEIPT, fs.syncs)
            with self.assertRaises(c.Held):
                session.request(TARGET.replace(STATE, 'z' * 43), [c.HOST])
            self.assertFalse(session.consumed)
            session.request(TARGET, [c.HOST])
        result, _, transport = self.run_capture(fs, listener=listener)
        self.assertEqual(result['phase'], 'captured')
        transport.assert_called_once()

    def test_readback_and_metadata_mismatch_preserve_files(self):
        for kind in ('bytes', 'mode', 'inode'):
            fs = MemoryIO()
            original_read, original_stat, original_fchmod = fs.read, fs.stat, fs.fchmod
            if kind == 'bytes':
                def read(fd, count):
                    raw = original_read(fd, count)
                    return b'corrupt' if fs.fds[fd][0] == c.KEY else raw
                fs.read = read
            elif kind == 'mode':
                def chmod(fd, mode):
                    original_fchmod(fd, 0o444 if fs.fds[fd][0] == c.KEY else mode)
                fs.fchmod = chmod
            else:
                def named_stat(path, **kwargs):
                    info = original_stat(path, **kwargs)
                    if path == 'github-app-private-key.pem':
                        info.st_ino += 1
                    return info
                fs.stat = named_stat
            result, fs, transport = self.run_capture(fs)
            self.assertEqual(result['phase'], 'partial')
            self.assertIn(c.KEY, fs.nodes)
            self.assertNotIn(c.REGISTRATION, fs.nodes)
            transport.assert_called_once()

    def test_deadline_guard_synthetic_signals_restored_and_no_takeover(self):
        # Signal methods are mocks: no real process timers or handlers are touched.
        with patch.object(c.signal, 'getitimer', return_value=(0.0, 0.0)), \
                patch.object(c.signal, 'getsignal', return_value='prior'), \
                patch.object(c.signal, 'signal') as install, \
                patch.object(c.signal, 'setitimer') as timer:
            with self.assertRaises(c.Held):
                with c.deadline_guard():
                    stop = install.call_args.args[1]
                    stop()
            self.assertEqual(timer.call_args_list[0].args, (c.signal.ITIMER_REAL, 899))
            self.assertEqual(timer.call_args_list[-1].args, (c.signal.ITIMER_REAL, 0))
            self.assertEqual(install.call_args.args, (c.signal.SIGALRM, 'prior'))
        with patch.object(c.signal, 'getitimer', return_value=(1.0, 0.0)), \
                patch.object(c.signal, 'setitimer') as timer:
            with self.assertRaises(c.Held):
                with c.deadline_guard():
                    self.fail('must refuse existing timer')
            timer.assert_not_called()

    def test_proof_drift_before_exchange_and_key_write(self):
        for when in ('listener', 'transport'):
            fs = MemoryIO()
            def drift():
                fs.nodes[c.PROOF].data = fs.nodes[c.PROOF].data.replace(b'aaaa', b'ffff', 1)
            def listener(session, announce):
                if when == 'listener':
                    drift()
                session.request(TARGET, [c.HOST])
            def exchange(code, timeout):
                if when == 'transport':
                    drift()
                return response()
            transport = Mock(side_effect=exchange)
            result, fs, _ = self.run_capture(fs, listener=listener, transport=transport)
            self.assertEqual(result['phase'], 'unknown' if when == 'listener' else 'partial')
            self.assertNotIn(c.KEY, fs.nodes)
            self.assertEqual(transport.call_count, 0 if when == 'listener' else 1)

    def test_listener_synthetic_socket_headers_methods_and_logging(self):
        # Instantiate the actual handler with a memory socket; never bind/listen.
        for target, host, method, expected in [('/start?state=' + STATE, c.HOST, 'GET', 200),
                                               (TARGET, c.HOST, 'GET', 200),
                                               (TARGET, 'evil.example', 'GET', 400),
                                               ('/unknown', c.HOST, 'GET', 400),
                                               (TARGET, c.HOST, 'SECRET_METHOD', 501)]:
            now = [0]
            store = Mock()
            session = c.Session(store, STATE, 20, lambda: now[0], Mock(return_value=response()))
            class Socket:
                def __init__(self):
                    self.output = bytearray()
                    self.input = (method + ' ' + target + ' HTTP/1.1\r\nHost: ' + host +
                                  '\r\n\r\n').encode()
                def settimeout(self, value):
                    pass
                def makefile(self, *args):
                    return io.BytesIO()
                def recv(self, count):
                    raw, self.input = self.input[:count], self.input[count:]
                    return raw
                def sendall(self, raw):
                    self.output.extend(raw)
            sock = Socket()
            class Server:
                def __init__(self, address, handler):
                    self.handler = handler
                    self.server_name, self.server_port = address
                    self.assert_address = address
                def __enter__(self):
                    self_outer.assertEqual(self.assert_address, ('127.0.0.1', 49181))
                    return self
                def __exit__(self, *args):
                    pass
                def handle_request(self):
                    self.handler(sock, ('127.0.0.1', 45678), self)
                    now[0] = 21
            self_outer = self
            announce = Mock()
            with patch.object(c.http.server, 'HTTPServer', Server), \
                    patch('sys.stderr', new_callable=io.StringIO) as stderr, \
                    patch('sys.stdout', new_callable=io.StringIO) as stdout:
                c.serve(session, announce)
                self.assertEqual(stderr.getvalue() + stdout.getvalue(), '')
            wire = sock.output.decode()
            self.assertIn(' ' + str(expected) + ' ', wire.split('\r\n')[0])
            self.assertIn('Cache-Control: no-store', wire)
            self.assertNotIn(CODE, wire)
            self.assertNotIn('SECRET_METHOD', wire)
            if expected == 200:
                self.assertIn('Referrer-Policy: no-referrer', wire)
                self.assertIn("default-src 'none'; form-action https://github.com", wire)
            announce.assert_called_once_with({'phase': 'waiting', 'start_url':
                'http://' + c.HOST + '/start?state=' + STATE})

    def test_tls_environment_overrides_refused_before_connection(self):
        for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR', 'SSLKEYLOGFILE'):
            with patch.dict(c.os.environ, {name: '/synthetic'}, clear=True), \
                    patch.object(c.http.client, 'HTTPSConnection') as https, \
                    patch.object(c.ssl, 'create_default_context') as trust:
                with self.assertRaises(c.Held):
                    c.exchange(CODE, 20)
                https.assert_not_called()
                trust.assert_not_called()

    def test_https_fixed_endpoint_no_retry_and_bound(self):
        for raw in (response()[2], b'x' * (c.LIMIT + 1)):
            connection = Mock()
            connection.getresponse.return_value.read.return_value = raw
            connection.getresponse.return_value.status = 201
            connection.getresponse.return_value.getheaders.return_value = response()[1]
            with patch.object(c.ssl, 'create_default_context', return_value='OS-TRUST') as trust, \
                    patch.object(c.http.client, 'HTTPSConnection', return_value=connection) as https:
                if len(raw) > c.LIMIT:
                    with self.assertRaises(c.Held):
                        c.exchange(CODE, 20)
                else:
                    self.assertEqual(c.exchange(CODE, 20)[2], raw)
                https.assert_called_once_with('api.github.com', timeout=20, context='OS-TRUST')
                trust.assert_called_once_with()
                args, kwargs = connection.request.call_args
                self.assertEqual(args, ('POST', '/app-manifests/' + CODE + '/conversions'))
                self.assertEqual(kwargs['headers']['X-GitHub-Api-Version'], '2022-11-28')
                self.assertEqual(kwargs['headers']['Accept'], 'application/vnd.github+json')
                connection.request.assert_called_once()
                connection.getresponse.return_value.read.assert_called_once_with(c.LIMIT + 1)
                connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
