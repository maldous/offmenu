"""One-shot App capture SOURCE; callable only, no import/CLI side effects.

Activation requires independent host/custody review and a trusted operator.
Injection parameters are trusted offline test seams, never configuration inputs.
Proof v1 binds the three reviewed artifacts by SHA256 and explicit owner decisions;
the digest supplied out of band authenticates the entire proof, not its claims alone.
"""
import base64
import contextlib
import io
import hashlib
import hmac
import html
import http.client
import http.server
import json
import os
import re
import secrets
import signal
import ssl
import stat
import time
import urllib.parse

OWNER = 'maldous'
PERMISSIONS = {'contents': 'write', 'pull_requests': 'write', 'metadata': 'read'}
HOST = '127.0.0.1:49181'
CALLBACK = 'http://' + HOST + '/callback'
INACTIVE_HOOK = {'url': 'https://github.com/maldous/offmenu', 'active': False}
KEY = '/etc/offmenu-publisher/github-app-private-key.pem'
REGISTRATION = '/etc/offmenu-publisher/app-registration.json'
RECEIPT = '/var/lib/offmenu-publisher/app-capture.jsonl'
PROOF = '/var/lib/offmenu-publisher/protected-current-runtime-proof.json'
LIMIT = 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}\Z')


class Held(Exception):
    """Fixed, nonsecret failure; never wrap an upstream exception's text."""


def require(value):
    if not value:
        raise Held('capture-held')


def manifest():
    return {'name': 'OffMenu Local Publisher - maldous',
            'url': 'https://github.com/maldous/offmenu', 'public': False,
            'default_permissions': dict(PERMISSIONS), 'default_events': [],
            'request_oauth_on_install': False, 'redirect_url': CALLBACK,
            'hook_attributes': dict(INACTIVE_HOOK)}


def form(state):
    require(isinstance(state, str) and re.fullmatch(r'[A-Za-z0-9_-]{32,128}', state))
    action = 'https://github.com/settings/apps/new?state=' + state
    return ('<!doctype html><meta charset="utf-8"><title>OffMenu App registration</title>'
            '<form method="post" action="' + action + '"><input type="hidden" '
            'name="manifest" value="' + html.escape(json.dumps(manifest()), quote=True) +
            '"><button type="submit">Review GitHub App creation</button></form>').encode()


def parse_request(target, hosts, state, consumed=False):
    require(hosts == [HOST] and isinstance(target, str) and len(target) <= 1024)
    require(not consumed and target.isascii() and '%' not in target)
    try:
        parsed = urllib.parse.urlsplit(target)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except (ValueError, UnicodeError):
        raise Held('capture-held') from None
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment)
    require(parsed.path in ('/start', '/callback'))
    fields = dict(pairs)
    expected = {'state'} if parsed.path == '/start' else {'state', 'code'}
    require(len(pairs) == len(fields) and set(fields) == expected)
    require(hmac.compare_digest(fields['state'], state))
    if parsed.path == '/callback':
        require(re.fullmatch(r'[A-Za-z0-9_-]{20,200}', fields['code']))
    return parsed.path, fields.get('code')


def json_object(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= LIMIT)

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    try:
        result = json.loads(raw, object_pairs_hook=unique)
        require(type(result) is dict)
        return result
    except Exception:
        raise Held('capture-held') from None


def validate_proof(raw, digest):
    require(isinstance(digest, str) and HEX.fullmatch(digest))
    require(hmac.compare_digest(hashlib.sha256(raw).hexdigest(), digest))
    proof = json_object(raw)
    require(type(proof.get('version')) is int and proof['version'] == 1)
    for field in ('protected_coordinator_source_sha256', 'protected_unit_sha256',
                  'guard_receipt_sha256'):
        require(isinstance(proof.get(field), str) and HEX.fullmatch(proof[field]))
    for field in ('actual_host_proof_accepted', 'credentials_absent',
                  'source_custody_accepted', 'root_custody_accepted'):
        require(proof.get(field) is True)
    return digest


def validate_response(status, headers, raw):
    require(status == 201)
    lowered = [(k.lower(), v) for k, v in headers]
    types = [v for k, v in lowered if k == 'content-type']
    require(len(types) == 1 and types[0].split(';')[0].strip().lower() == 'application/json')
    require(not any(k in ('location', 'content-encoding') for k, _ in lowered))
    lengths = [v for k, v in lowered if k == 'content-length']
    require(len(lengths) <= 1)
    if lengths:
        require(re.fullmatch(r'[0-9]{1,7}', lengths[0]) and int(lengths[0]) == len(raw))
    data = json_object(raw)
    require(type(data.get('id')) is int and 0 < data['id'] <= 2**53 - 1)
    require(type(data.get('owner')) is dict and data['owner'].get('login') == OWNER)
    require(data.get('permissions') == PERMISSIONS and data.get('events') == [])
    # The documented conversion schema omits public. Privacy is fixed in the
    # submitted manifest and checked on the GitHub registration form.
    require('public' not in data or data['public'] is False)
    # Conversions may omit hook_attributes; an explicit enabled hook is refused.
    require(data.get('hook_attributes', INACTIVE_HOOK) == INACTIVE_HOOK)
    require(not data.get('webhook_url') and not data.get('hook_url'))
    pem = data.get('pem')
    require(isinstance(pem, str) and 128 <= len(pem) <= 65536 and pem.isascii())
    match = re.fullmatch(r'-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----\n'
                         r'([A-Za-z0-9+/=\n]+)-----END \1-----\n?', pem)
    require(match)
    try:
        decoded = base64.b64decode(match[2].replace('\n', ''), validate=True)
        require(64 <= len(decoded) <= 49152 and decoded[0] == 0x30)
    except Exception:
        raise Held('capture-held') from None
    # No client_secret/webhook_secret leaves this function.
    return data['id'], pem.encode('ascii')


def exchange(code, timeout):
    """Direct HTTPS: OS trust store, no proxy lookup, redirect or retry support."""
    require(re.fullmatch(r'[A-Za-z0-9_-]{20,200}', code) and 0 < timeout <= 30)
    # The default SSL helper honors these inherited certificate/key-log overrides.
    require(not any(name in os.environ for name in
                    ('SSL_CERT_FILE', 'SSL_CERT_DIR', 'SSLKEYLOGFILE')))
    connection = http.client.HTTPSConnection('api.github.com', timeout=timeout,
                                              context=ssl.create_default_context())
    try:
        connection.request('POST', '/app-manifests/' + code + '/conversions', body=b'',
                           headers={'Accept': 'application/vnd.github+json',
                                    'X-GitHub-Api-Version': '2022-11-28',
                                    'User-Agent': 'offmenu-app-capture', 'Content-Length': '0'})
        response = connection.getresponse()
        raw = response.read(LIMIT + 1)
        require(len(raw) <= LIMIT)
        return response.status, response.getheaders(), raw
    except Exception:
        raise Held('capture-held') from None
    finally:
        connection.close()


class Custody:
    """Root-only descriptor-relative filesystem operations; never creates directories."""

    def __init__(self, io=os):
        self.io = io
        self.dirs = {}
        self.receipt = None
        self.proof_digest = None

    def directory(self, path):
        io = self.io
        fd = io.open('/', io.O_RDONLY | io.O_DIRECTORY | io.O_NOFOLLOW)
        try:
            for part in path.strip('/').split('/'):
                info = io.fstat(fd)
                require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and
                        info.st_mode & 0o022 == 0)
                child = io.open(part, io.O_RDONLY | io.O_DIRECTORY | io.O_NOFOLLOW, dir_fd=fd)
                io.close(fd)
                fd = child
            info = io.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and
                    info.st_mode & 0o022 == 0)
            require(info.st_gid == 976 and stat.S_IMODE(info.st_mode) == 0o750)
            self.dirs[path] = fd
        except Exception:
            io.close(fd)
            raise Held('capture-held') from None

    def parent(self, path):
        parent, name = path.rsplit('/', 1)
        return self.dirs[parent], name

    def absent(self, path):
        fd, name = self.parent(path)
        try:
            self.io.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise Held('capture-held')

    def read_proof(self):
        io = self.io
        parent, name = self.parent(PROOF)
        fd = io.open(name, io.O_RDONLY | io.O_NOFOLLOW | io.O_NONBLOCK, dir_fd=parent)
        try:
            s = io.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1 and
                    s.st_mode & 0o022 == 0 and 0 < s.st_size <= LIMIT)
            raw = io.read(fd, LIMIT + 1)
            require(len(raw) == s.st_size)
            return raw
        finally:
            io.close(fd)

    def write_all(self, fd, raw):
        while raw:
            count = self.io.write(fd, raw)
            require(0 < count <= len(raw))
            raw = raw[count:]
        self.io.fsync(fd)

    def create(self, path, raw, mode, gid):
        io = self.io
        parent, name = self.parent(path)
        fd = io.open(name, io.O_RDWR | io.O_CREAT | io.O_EXCL | io.O_NOFOLLOW, 0o600,
                     dir_fd=parent)
        try:
            io.fchown(fd, 0, gid)
            self.write_all(fd, raw)
            io.fchmod(fd, mode)
            io.fsync(fd)
            s = io.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_gid == gid and
                    s.st_nlink == 1 and stat.S_IMODE(s.st_mode) == mode and s.st_size == len(raw))
            named = io.stat(name, dir_fd=parent, follow_symlinks=False)
            require((s.st_dev, s.st_ino) == (named.st_dev, named.st_ino))
            io.lseek(fd, 0, io.SEEK_SET)
            require(io.read(fd, len(raw) + 1) == raw)
            io.lseek(fd, 0, io.SEEK_END)
            io.fsync(parent)
            return fd
        except Exception:
            io.close(fd)
            # Preserve partial files for trusted reconciliation; never unlink/retry.
            raise Held('capture-held') from None

    def prepare(self, digest):
        self.directory('/etc/offmenu-publisher')
        self.directory('/var/lib/offmenu-publisher')
        for path in (KEY, REGISTRATION, RECEIPT):
            self.absent(path)
        validate_proof(self.read_proof(), digest)
        self.proof_digest = digest
        raw = json.dumps({'phase': 'intent', 'owner': OWNER, 'permissions': PERMISSIONS,
                          'proof_sha256': digest, 'key_path': KEY}).encode() + b'\n'
        self.receipt = self.create(RECEIPT, raw, 0o600, 0)

    def verify_proof(self):
        validate_proof(self.read_proof(), self.proof_digest)

    def record(self, phase, app_id=None):
        raw = json.dumps({'phase': phase, 'app_id': app_id, 'owner': OWNER}).encode() + b'\n'
        self.write_all(self.receipt, raw)

    def capture(self, app_id, pem):
        self.verify_proof()
        fd = self.create(KEY, pem, 0o440, 976)
        self.io.close(fd)
        raw = json.dumps({'app_id': app_id, 'owner': OWNER, 'permissions': PERMISSIONS,
                          'key_path': KEY}).encode() + b'\n'
        fd = self.create(REGISTRATION, raw, 0o440, 976)
        self.io.close(fd)

    def close(self):
        for fd in ([self.receipt] if self.receipt is not None else []) + list(self.dirs.values()):
            self.io.close(fd)


class Session:
    """One conversion attempt; consumed state survives every partial/unknown failure."""

    def __init__(self, custody, state, deadline, clock, transport):
        form(state)  # Validate injected state as well as real token_urlsafe output.
        self.custody, self.state, self.deadline = custody, state, deadline
        self.clock, self.transport = clock, transport
        self.consumed = False
        self.result = {'phase': 'waiting'}

    def request(self, target, hosts):
        require(self.clock() < self.deadline)
        path, code = parse_request(target, hosts, self.state, self.consumed)
        if path == '/start':
            return form(self.state)
        self.consumed = True
        self.result = {'phase': 'unknown'}
        try:
            self.custody.verify_proof()
            self.custody.record('conversion-intent')
            response = self.transport(code, min(30, self.deadline - self.clock()))
            app_id, pem = validate_response(*response)
            self.custody.record('converted', app_id)
            self.result = {'phase': 'partial', 'app_id': app_id}
            self.custody.capture(app_id, pem)
            self.custody.record('captured', app_id)
            self.result = {'phase': 'captured', 'app_id': app_id, 'owner': OWNER,
                           'permissions': dict(PERMISSIONS), 'key_path': KEY,
                           'registration_path': REGISTRATION, 'receipt_path': RECEIPT}
        except Exception:
            try:
                self.custody.record(self.result['phase'], self.result.get('app_id'))
            except Exception:
                pass  # Immutable initial intent still blocks reuse.
        return b'<!doctype html><title>Capture status</title>Return to the trusted operator.'


def serve(session, announce):
    """Finite serial listener; suppress all request/exception logging."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(max(0.001, min(2, session.deadline - session.clock())))
            super().setup()

        def log_message(self, *args):
            pass

        def send_error(self, code, message=None, explain=None):
            # Base errors can otherwise reflect attacker-controlled methods.
            self.send_response(code)
            self.send_header('Content-Length', '0')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()

        def handle(self):
            # Absolute deadline and small aggregate header bound, including slow clients.
            raw = bytearray()
            while b'\r\n\r\n' not in raw:
                require(session.clock() < session.deadline and len(raw) < 8192)
                self.connection.settimeout(max(0.001, min(2, session.deadline - session.clock())))
                chunk = self.connection.recv(min(1024, 8192 - len(raw)))
                require(chunk)
                raw.extend(chunk)
            require(raw.endswith(b'\r\n\r\n'))
            self.rfile.close()
            self.rfile = io.BytesIO(raw)
            self.close_connection = True
            self.handle_one_request()

        def do_GET(self):
            try:
                require(not self.headers.get_all('Transfer-Encoding') and
                        not self.headers.get_all('Content-Length'))
                body = session.request(self.path, self.headers.get_all('Host', []))
                self.send_response(200)
            except Exception:
                body = b'Capture held.'
                self.send_response(400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action https://github.com; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

    class Server(http.server.HTTPServer):
        def handle_error(self, *args):
            pass

    with Server(('127.0.0.1', 49181), Handler) as server:
        announce({'phase': 'waiting', 'start_url': 'http://' + HOST + '/start?state=' + session.state})
        while not session.consumed and session.clock() < session.deadline:
            server.timeout = min(0.5, session.deadline - session.clock())
            server.handle_request()


@contextlib.contextmanager
def deadline_guard():
    """Process-local hard stop, restored on exit; refuses another alarm's ownership.

    Trusted operator must invoke on the main thread. No background job is created.
    """
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0))
    previous = signal.getsignal(signal.SIGALRM)

    def stop(*args):
        raise Held('capture-held')

    signal.signal(signal.SIGALRM, stop)
    try:
        signal.setitimer(signal.ITIMER_REAL, 899)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def capture_once(trusted_proof_sha256, *, custody=None, identity=None,
                 clock=time.monotonic, state_factory=secrets.token_urlsafe,
                 transport=exchange, listener=serve, announce=lambda receipt: None,
                 guard=deadline_guard):
    """Trusted operator call only. No arbitrary paths, owners or permissions.

    Returns sanitized status only. No retries; partial/unknown outcomes require
    operator reconciliation, including after a crash with only intent retained.
    """
    store = custody if custody is not None else Custody()
    session = None
    try:
        who = identity() if identity is not None else (os.getuid(), os.geteuid())
        require(who == (0, 0))
        with guard():
            deadline = clock() + 895  # Reserve five seconds for final local bookkeeping.
            store.prepare(trusted_proof_sha256)
            session = Session(store, state_factory(32), deadline, clock, transport)
            listener(session, announce)
            if not session.consumed:
                store.record('expired')
                return {'phase': 'expired'}
            return dict(session.result)
    except Exception:
        return dict(session.result) if session is not None and session.consumed else {'phase': 'held'}
    finally:
        try:
            store.close()
        except Exception:
            pass
