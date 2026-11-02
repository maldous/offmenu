"""Finite publisher-owner lifecycle; never a caller-selected privileged runner.

Production invoke() runs only as the installed UID984/GID976 custodian. Outer
observe reads the named ORIGINAL receipt and never starts a process or creates
state. Missing preparation/terminal proof stays held. Installation, exact sudo
permission and mandatory host approval are separate; this module grants none.
"""
import base64
import csv
import ctypes
import io
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import UUID


INSTALL = Path('/opt/offmenu-publisher')
CONFIG = Path('/etc/offmenu-publisher/config.json')
CLAIM = Path('/var/lib/offmenu-publisher/integration')
ENTRY = INSTALL / 'tools/delivery/native_publisher_invocation.py'
PUBLISHER = INSTALL / 'tools/delivery/github-app-publisher.mjs'
PYTHON = INSTALL / 'venv/bin/python'
NODE = Path('/usr/bin/node')
CLOSURE = INSTALL / 'native-harness-closure.json'
MANIFEST_LIMIT = 16*1024*1024
PUBLIC_CA = 'venv/lib/python3.12/site-packages/certifi/cacert.pem'
LIMIT = 65536
WIRE_LIMIT = 16384
TIMEOUT = 180
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
       'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}
INNER = {'version', 'mode', 'operation_id', 'issue_id', 'project_id', 'owner',
         'unit_sha256', 'packet_sha256', 'source_sha256'}
STATUSES = {'ready', 'pending', 'unknown', 'verified', 'denied', 'failed'}


class InvocationHold(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise InvocationHold(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value, limit=LIMIT):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'
        require(len(raw) <= limit, 'json_size')
        return raw
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise InvocationHold('json_encoding') from None


def fingerprint(value):
    return sha(wire(value, 1048576)[:-1])


def decode(raw, limit=LIMIT):
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'json_size')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_key')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: require(False, 'json_number'))
    except (ValueError, UnicodeError, RecursionError):
        raise InvocationHold('json_decode') from None


def exact(value, fields):
    return type(value) is dict and set(value) == set(fields)


def hex64(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def uuid(value):
    try:
        require(type(value) is str and str(UUID(value)) == value and UUID(value).int != 0, 'uuid')
    except (ValueError, AttributeError):
        raise InvocationHold('uuid') from None


def continuation(value, identity):
    """Finite ROOT-sealed same-operation history grant, not invocation authority."""
    pre = isinstance(value,dict) and 'pre_admission_refusal' in value
    require(exact(value, {'version','operation_id','unit_sha256','packet_sha256','claim_sha256',
        'previous_selection_sha256','previous_capability','previous_record_sha256','receipts'} |
        ({'pre_admission_refusal'} if pre else set()))
        and type(value['version']) is int and value['version'] == 1, 'continuation_shape')
    for key in ('operation_id','unit_sha256','packet_sha256','claim_sha256',
                'previous_selection_sha256','previous_record_sha256'):
        require(hex64(value[key]), 'continuation_hash')
    require(all(value[k] == identity[k] for k in ('operation_id','unit_sha256','packet_sha256')),
            'continuation_identity')
    claim = dict(binding_sha256=identity['operation_id'],
        directory=str(CLAIM/('transaction-'+identity['operation_id'])),owner=identity['owner'])
    require(value['claim_sha256'] == fingerprint(claim), 'continuation_claim')
    cap = value['previous_capability']
    require(exact(cap, {'version','closure_sha256','host_confirmation_sha256'})
        and type(cap['version']) is int and cap['version'] == 1
        and all(hex64(cap[k]) for k in ('closure_sha256','host_confirmation_sha256')),
        'continuation_capability')
    receipts = value['receipts']
    require(type(receipts) is list and (receipts == [] if pre else 1 <= len(receipts) <= 128),
            'continuation_receipts')
    if pre:
        refused=value['pre_admission_refusal']
        require(exact(refused,{'invocation_id','request_sha256','reason','evidence_sha256'})
            and refused['reason'] == 'closure_canonical_bytes'
            and hex64(refused['request_sha256']) and hex64(refused['evidence_sha256']),
            'pre_admission_refusal')
        uuid(refused['invocation_id'])
    ids = []
    for ref in receipts:
        require(exact(ref, {'invocation_id','closure_sha256','receipt_sha256'})
            and hex64(ref['closure_sha256']) and hex64(ref['receipt_sha256']), 'continuation_receipt')
        uuid(ref['invocation_id']); ids.append(ref['invocation_id'])
    require(len(ids) == len(set(ids)), 'continuation_duplicate')
    return value


def original_receipt_closure(record, current_closure, grant):
    """Old bytes retain old closure pins only under the exact sealed whitelist."""
    intent = record['intent']
    if grant is not None:
        selected = [r for r in grant['receipts'] if r['invocation_id'] == intent['invocation_id']]
        if selected:
            ref = selected[0]
            require(sha(wire(record)) == ref['receipt_sha256']
                and intent['closure_sha256'] == ref['closure_sha256'], 'continuation_receipt_drift')
            return ref['closure_sha256']
    require(intent['closure_sha256'] == current_closure, 'unadmitted_historical_receipt')
    return current_closure


def request(raw):
    value = decode(raw, WIRE_LIMIT)
    require(exact(value, {'version', 'mode', 'invocation_id', 'request'})
            and type(value['version']) is int and value['version'] == 1
            and value['mode'] in ('invoke', 'observe', 'review'), 'outer_request')
    uuid(value['invocation_id'])
    inner = value['request']
    require(exact(inner, INNER) and type(inner['version']) is int and inner['version'] == 1
            and inner['mode'] in ('observe', 'step', 'publish'), 'inner_request')
    for key in ('operation_id', 'unit_sha256', 'packet_sha256', 'source_sha256'):
        require(hex64(inner[key]), 'request_hash')
    for key in ('issue_id', 'project_id'):
        uuid(inner[key])
    owner = inner['owner']
    require(value['mode'] != 'review' or inner['mode'] == 'observe', 'review_read_only')
    require(type(owner) is str and 0 < len(owner) <= 200 and owner == owner.strip()
            and all(ord(c) >= 32 and ord(c) != 127 for c in owner), 'request_owner')
    return value


def association(config, inner):
    """Only sealed byte association; independent127 checks remain authoritative."""
    try:
        require(type(config['version']) is int and config['version'] in (1, 2)
                and type(config['publisherUid']) is int and config['publisherUid'] == 984
                and type(config['publisherGid']) is int and config['publisherGid'] == 976, 'config_identity')
        binding, n = config['binding'], config['snapshot']['native_runtime']
        require(inner['mode'] != 'publish' or (config['version'] == 1
                and 'source_projection' not in binding
                and config.get('integration_admission', {}).get('kind') ==
                    'native-source-reviewed-integration-v1'), 'publication_only_admission')
        require(exact(n, {'issue_id', 'project_id', 'owner', 'unit_sha256', 'packet_sha256', 'source'}), 'sealed_native')
        s = n['source']
        require(exact(s, {'repository', 'branch', 'base', 'head', 'tree', 'target', 'policy_sha256'})
                and s['repository'] == binding['repository'] == 'maldous/offmenu'
                and n['owner'] == binding['owner'] == config['logicalOwner']
                and n['issue_id'] == binding['issue_id']
                and ('project_id' not in binding or n['project_id'] == binding['project_id']), 'sealed_source')
        for key in ('base', 'head', 'tree'):
            require(type(s[key]) is str and re.fullmatch('[0-9a-f]{40}', s[key]), 'source_hash')
        require(hex64(s['policy_sha256']), 'source_policy')
        if config['version'] == 2:
            require(s == binding['candidate']['source'] and s['branch'] == 'develop'
                    and s['target'] == 'main', 'release_source')
        else:
            source_base = binding['base']
            if 'source_projection' in binding:
                p = binding['source_projection']
                require(exact(p, {'version','profile','source','target','merge_tree','outputs',
                    'unit_sha256','operation_key','receipt','review_sha256'})
                    and binding.get('version') == 2
                    and type(p['version']) is int and p['version'] == 1
                    and p['profile'] == 'identity-client-focused'
                    and exact(p['source'], {'head','base','tree','branch'})
                    and exact(p['target'], {'base','tree'})
                    and p['source'] == {key:s[key] for key in ('head','base','tree','branch')}
                    and p['target']['base'] == binding['base']
                    and all(type(v) is str and re.fullmatch('[0-9a-f]{40}', v)
                            for v in (p['target']['base'],p['target']['tree'],p['merge_tree']))
                    and p['outputs'] == binding['outputs']
                    and p['unit_sha256'] == n['unit_sha256'] and hex64(p['unit_sha256'])
                    and p['operation_key'] == binding['validation_operation_key'] and hex64(p['operation_key'])
                    and hex64(p['review_sha256']) and exact(p['receipt'], {'path','sha256'})
                    and type(p['receipt']['path']) is str and p['receipt']['path'].startswith('/')
                    and hex64(p['receipt']['sha256'])
                    and hex64(config['codePins'].get('src/offmenu/delivery/identity_source_projection.py')),
                    'integration_projection')
                source_base = p['source']['base']
            require(s['base'] == source_base and all(s[key] == binding[key] for key in ('head', 'tree'))
                    and s['branch'] == binding['head_branch'] and s['target'] == 'develop', 'integration_source')
        identity = dict(operation_id=fingerprint(binding), issue_id=n['issue_id'],
                        project_id=n['project_id'], owner=n['owner'], unit_sha256=n['unit_sha256'],
                        packet_sha256=n['packet_sha256'], source_sha256=fingerprint(s))
        require(all(inner[key] == value for key, value in identity.items()), 'sealed_association')
        return 'release' if config['version'] == 2 else 'integration'
    except (KeyError, TypeError, AttributeError):
        raise InvocationHold('sealed_config') from None


def inner_response(value, inner, phase):
    fields = {'version', 'kind', 'request_sha256', 'phase', 'status'} | (INNER - {'version', 'mode'})
    require(exact(value, fields) and type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-response-v1' and value['phase'] == phase
            and value['status'] in STATUSES and value['request_sha256'] == fingerprint(inner)
            and all(value[key] == inner[key] for key in INNER - {'version', 'mode'}), 'publisher_response')
    return value


def validate_closure(raw, source_head):
    """Shared128 canonical manifest. SHA256 is file bytes, not fingerprint()."""
    value = decode(raw, MANIFEST_LIMIT)
    require(exact(value, {'version', 'kind', 'source_head', 'source_tree', 'node_sha256', 'files'})
            and type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-closure-v1'
            and value['source_head'] == source_head and hex64(value['node_sha256']), 'closure_shape')
    for key in ('source_head', 'source_tree'):
        require(type(value[key]) is str and re.fullmatch('[0-9a-f]{40}', value[key]), 'closure_source')
    files = value['files']
    require(type(files) is dict and 0 < len(files) <= 50000, 'closure_files')
    for name, pin in files.items():
        require(type(name) is str and 0 < len(name) <= 1024 and not name.startswith('/')
                and '\\' not in name and all(ord(c) >= 32 and ord(c) != 127 for c in name)
                and all(p not in ('', '.', '..', '.git', '.ssh', '.aws', '.codex', '.env')
                        for p in name.split('/')) and hex64(pin), 'closure_path')
        require(not name.lower().endswith('.pem') or name == PUBLIC_CA, 'private_pem_refused')
        require(name != 'native-harness-closure.json', 'closure_self_reference')
    required = {'tools/delivery/native_publisher_invocation.py', 'tools/delivery/windmill_runner.py',
                'tools/delivery/capacity-policy.json', 'tools/delivery/github-app-publisher.mjs',
                'tools/delivery/github-app-adapter.mjs', 'tools/delivery/integration-gateway.mjs',
                'src/offmenu/delivery/integration.py', 'venv/bin/python'}
    require(required <= files.keys(), 'closure_required')
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii') + b'\n'
    require(raw == canonical, 'closure_canonical_bytes')
    return value


def _file_hash(path, uid=0, maximum=64*1024*1024):
    """Bounded streaming hash: do not materialize dependency/interpreter bodies."""
    require(path.resolve() == path, 'canonical_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1
                and not before.st_mode & 0o022 and before.st_size <= maximum, 'file_custody')
        digest = hashlib.sha256(); size = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk); require(size <= maximum, 'file_size'); digest.update(chunk)
        after = os.fstat(fd)
        require(size == before.st_size and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file_drift')
        return digest.hexdigest()
    finally:
        os.close(fd)


def _public_ca_record(root, files, uid=0):
    if PUBLIC_CA not in files:
        return
    records = [name for name in files if re.fullmatch(
        r'venv/lib/python3\.12/site-packages/certifi-[a-zA-Z0-9_.-]+\.dist-info/RECORD', name)]
    require(len(records) == 1, 'public_ca_record')
    path = root/records[0]
    require(_file_hash(path, uid) == files[records[0]], 'public_ca_record_pin')
    rows = list(csv.reader(io.StringIO(_read(path, uid, stat.S_IMODE(path.stat().st_mode), MANIFEST_LIMIT).decode('utf-8'))))
    rows = [row for row in rows if row and row[0] == 'certifi/cacert.pem']
    expected = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(files[PUBLIC_CA])).rstrip(b'=').decode('ascii')
    require(len(rows) == 1 and len(rows[0]) == 3 and rows[0][1] == expected
            and rows[0][2].isdigit() and len(rows[0][2]) <= 12
            and int(rows[0][2]) == (root/PUBLIC_CA).stat().st_size, 'public_ca_record_pin')


def _read(path, uid, mode, maximum=LIMIT):
    require(path.resolve() == path, 'canonical_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == mode and 0 < st.st_size <= maximum, 'file_custody')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        require(len(raw) == st.st_size and (st.st_ino, st.st_dev, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                == (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file_drift')
        return raw
    finally:
        os.close(fd)


def _directory(path, uid, mode=None):
    st = path.lstat()
    require(path.resolve() == path and stat.S_ISDIR(st.st_mode) and st.st_uid == uid
            and not st.st_mode & 0o022 and (mode is None or stat.S_IMODE(st.st_mode) == mode), 'directory_custody')


class _Host:
    uid = 984
    root = CLAIM
    cwd = INSTALL
    command = (str(NODE), str(PUBLISHER), '--native-rpc')
    timeout = TIMEOUT

    def admit(self, inner):
        require((os.getuid(), os.geteuid(), os.getgid(), os.getegid()) == (984, 984, 976, 976), 'publisher_identity')
        require(Path(__file__).resolve() == ENTRY and Path(sys.executable).resolve() == PYTHON, 'installed_entry')
        # Validate the entire import closure before importing maintained helpers.
        entries = [INSTALL]
        count = 0
        while entries:
            path = entries.pop()
            count += 1
            require(count <= 50000 and len(path.relative_to(INSTALL).parts) <= 24, 'closure_bounds')
            st = path.lstat()
            require(st.st_uid == 0 and not st.st_mode & 0o022 and not stat.S_ISLNK(st.st_mode), 'sealed_closure')
            if stat.S_ISDIR(st.st_mode):
                entries.extend(path.iterdir())
            else:
                require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'sealed_file')
        for path in (*INSTALL.parents, *CONFIG.parents, *CLAIM.parents):
            _directory(path, 0)
        raw = _read(CONFIG, 0, 0o440, 1048576)
        config = decode(raw, 1048576)
        require(CONFIG.stat().st_gid == 976, 'config_group')
        phase = association(config, inner)
        manifest_raw = _read(CLOSURE, 0, 0o444, MANIFEST_LIMIT)
        manifest = validate_closure(manifest_raw, config['sourceHead'])
        files = manifest['files']
        selected = {str(path.relative_to(INSTALL)) for path in INSTALL.rglob('*')
                    if path.is_file() and path != CLOSURE}
        require(selected == set(files), 'closure_exact_files')
        _public_ca_record(INSTALL, files)  # Public CA exception requires its pinned RECORD before PEM read.
        total = 0
        for name, pin in files.items():
            path = INSTALL/name
            total += path.stat().st_size
            require(total <= 1024*1024*1024, 'closure_total_size')
            require(_file_hash(path) == pin, 'closure_byte_pin')
        for path, mode in ((ENTRY, 0o444), (PYTHON, 0o555)):
            require(stat.S_IMODE(path.stat().st_mode) == mode, 'entry_mode')
        for parent in NODE.parents:
            _directory(parent, 0)
        require(NODE.stat().st_mode & 0o111 and _file_hash(NODE, maximum=256*1024*1024)
                == manifest['node_sha256'], 'node_pin')
        require(type(config['codePins']) is dict and 0 < len(config['codePins']) <= 32, 'code_pins')
        require(all(files.get(name) == pin for name, pin in config['codePins'].items())
                and files['venv/bin/python'] == config['pythonSha256'], 'existing_code_pins')
        # No legacy-state migration or new Controller initialization.
        _directory(CLAIM, 984, 0o700)
        directory = CLAIM / ('transaction-' + inner['operation_id'])
        require(directory.exists(), 'prepared_transaction_missing')
        _directory(directory, 984, 0o700)
        require(decode(_read(directory/'binding.json', 984, 0o600, 1048576), 1048576) == config['binding'], 'prepared_binding')
        _read(directory/'state.json', 984, 0o600, 1048576)
        claim = decode(_read(CLAIM/'active-owner.json', 984, 0o600))
        require(claim == dict(binding_sha256=inner['operation_id'], directory=str(directory), owner=inner['owner']), 'existing_owner_claim')
        self.continuation = (continuation(config['nativeContinuation'], inner)
                             if 'nativeContinuation' in config else None)
        sys.path.insert(0, str(INSTALL/'tools/delivery'))
        self.runner = importlib.import_module('windmill_runner')
        return directory, phase, sha(manifest_raw)

    def review(self, directory, inner, closure):
        """Read the original pending checkpoint; no graph setup or side receipt."""
        return pending_review(directory, inner, closure, root=CLAIM, uid=984)


def pending_review(directory, inner, closure, *, root, uid):
    # root/uid are fixed by _Host; injection is in-process synthetic tests only.
    # Recheck ownership under the original existing lock after admission.
    lock = os.open(root/'repository-owner.lock', os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == 0o600, 'review_lock')
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        binding = decode(_read(directory/'binding.json', uid, 0o600, 1048576), 1048576)
        require(fingerprint(binding) == inner['operation_id'] and binding['version'] == 2
                and binding['issue_id'] == inner['issue_id'] and binding['owner'] == inner['owner'],
                'review_binding')
        claim = decode(_read(root/'active-owner.json', uid, 0o600))
        require(claim == dict(binding_sha256=inner['operation_id'], directory=str(directory),
                              owner=inner['owner']), 'review_current_claim')
        require(decode(_read(directory/'repository-claim.json', uid, 0o600)) == claim,
                'review_immutable_claim')
        state = decode(_read(directory/'state.json', uid, 0o600, 1048576), 1048576)
        if (state.get('binding_sha256') == inner['operation_id']
            and state.get('status') in ('publication-ready','publication-verified')
            and state.get('publication', {}).get('effect') in ('ready','verified')
            and not state.get('merge_effect')):
            return dict(version=1,kind='native-publisher-unit-review-v1',status='not-ready',
                        request_sha256=fingerprint(inner),closure_sha256=closure)
        require(state.get('binding_sha256') == inner['operation_id']
                and state.get('status') == 'merge-intent' and state.get('merge_effect') == 'pending'
                and not state.get('helper_consumed')
                and state.get('action', {}).get('kind') == 'merge-pr', 'review_pending')
        # Open read-only, retain typed checkpoint bytes for the existing v2 decoder.
        # Check consumed inode custody; SQLite receives no caller-supplied path.
        database = directory/'graph.sqlite'
        info = database.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600, 'review_checkpoint_custody')
        # SQLite mode=ro alone can create WAL/SHM files. With the owner's
        # shared lock held, require a fully checkpointed database and use
        # immutable reads; never ignore an uncheckpointed WAL or repair it.
        wal = directory/'graph.sqlite-wal'
        require(not wal.exists() or (not wal.is_symlink() and wal.stat().st_size == 0),
                'review_checkpoint_wal')
        with sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
            row = db.execute("SELECT type,checkpoint FROM checkpoints WHERE thread_id=? AND checkpoint_ns='' ORDER BY checkpoint_id DESC LIMIT 1",
                             (inner['operation_id'],)).fetchone()
        require(row is not None and row[0] == 'msgpack' and type(row[1]) is bytes
                and 0 < len(row[1]) <= 524288, 'review_checkpoint')
        return dict(version=1, kind='native-publisher-unit-review-v1',
                    request_sha256=fingerprint(inner), closure_sha256=closure,
                    binding=binding, decision=state, checkpoint=base64.b64encode(row[1]).decode('ascii'))
    finally:
        os.close(lock)


def _write(path, value):
    """Bounded same-directory write/fsync; never initializes a job runner."""
    raw = wire(value)
    # Same-dir temporary, no overwrite of any other invocation's record.
    temp = path.with_name('.' + path.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temp.exists():
            temp.unlink()


def _echild():
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                return False
        except ChildProcessError:
            return True


def _starttime(pid):
    try:
        text = Path('/proc', str(pid), 'stat').read_text()
        return int(text[text.rfind(')')+2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def _supervise(inner, phase, host):
    """One fresh SAME-UID subreaper; no recovery inference in this function."""
    require(_echild(), 'preexisting_children')
    require(ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0, 'subreaper_unavailable')
    subreaper = ctypes.c_int()
    require(ctypes.CDLL(None, use_errno=True).prctl(37, ctypes.byref(subreaper), 0, 0, 0) == 0
            and subreaper.value == 1, 'subreaper_readback')
    stopped = [False]
    previous = {}
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        previous[sig] = signal.signal(sig, lambda *_: stopped.__setitem__(0, True))
    proc = None
    sel = selectors.DefaultSelector()
    output = bytearray()
    outcome, response, reaped, gone = 'supervisor_error', None, False, False
    pid, start = None, None
    try:
        proc = subprocess.Popen(host.command, cwd=host.cwd, env=ENV, close_fds=True,
                                start_new_session=True, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pid, start = proc.pid, _starttime(proc.pid)
        payload = memoryview(wire(inner)); sent = 0; errors = 0
        for stream, label, events in ((proc.stdin, 'in', selectors.EVENT_WRITE),
                                       (proc.stdout, 'out', selectors.EVENT_READ),
                                       (proc.stderr, 'err', selectors.EVENT_READ)):
            os.set_blocking(stream.fileno(), False); sel.register(stream, events, label)
        deadline = time.monotonic() + host.timeout
        outcome = 'succeeded'
        while sel.get_map() or proc.poll() is None:
            if stopped[0]:
                outcome = 'cancelled'; break
            if time.monotonic() >= deadline:
                outcome = 'timed_out'; break
            for key, _ in sel.select(.02):
                stream, label = key.fileobj, key.data
                if label == 'in':
                    try:
                        sent += os.write(stream.fileno(), payload[sent:])
                    except BrokenPipeError:
                        sent = len(payload)
                    if sent == len(payload):
                        sel.unregister(stream); stream.close()
                else:
                    chunk = os.read(stream.fileno(), 4096)
                    if not chunk:
                        sel.unregister(stream); continue
                    if label == 'out':
                        output.extend(chunk)
                    else:
                        errors += len(chunk)
                    if len(output) > WIRE_LIMIT or errors > 4096:
                        outcome = 'output_limit'; break
            if outcome == 'output_limit':
                break
        if outcome == 'succeeded' and proc.poll() != 0:
            outcome = 'publisher_error'
    except Exception:
        outcome = 'supervisor_error'
    finally:
        try:
            if proc is not None:
                # Only reusable termination helpers; their census is not proof.
                host.runner.cleanup(proc)
                proc.wait(timeout=1)
                reaped = True
            gone = _echild()  # SAME subreaper, after actual direct-child reap.
        except Exception:
            gone = False
        sel.close()
        if proc is not None:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream and not stream.closed:
                    stream.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if outcome == 'succeeded':
        try:
            response = inner_response(decode(bytes(output), WIRE_LIMIT), inner, phase)
        except InvocationHold:
            outcome = 'invalid_response'
    return dict(outcome=outcome, child_started=proc is not None, child_pid=pid,
                child_starttime=start, subreaper_verified=True, direct_child_reaped=reaped,
                waitpid_echild=gone, child_tree_gone=gone and (proc is None or reaped),
                response=response, response_sha256=fingerprint(response) if response is not None else None)


def _result(envelope, record):
    terminal = record['terminal'] if record else None
    return dict(version=1, kind='native-publisher-invocation-v1',
                operation_id=envelope['request']['operation_id'], invocation_id=envelope['invocation_id'],
                request_sha256=fingerprint(envelope['request']),
                status='not-found' if record is None else ('complete' if terminal and terminal['child_tree_gone'] else 'unknown'),
                response=terminal['response'] if terminal else None,
                receipt={'sha256': sha(wire(record)), 'body': record} if record else None)


def validate_result(value, envelope, closure_sha256):
    """Pure126 boundary: a body hash alone is NOT privileged authentication."""
    envelope = request(wire(envelope))
    require(exact(value, {'version', 'kind', 'operation_id', 'invocation_id', 'request_sha256',
                          'status', 'response', 'receipt'}), 'outer_response')
    require(type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-invocation-v1'
            and value['operation_id'] == envelope['request']['operation_id']
            and value['invocation_id'] == envelope['invocation_id']
            and value['request_sha256'] == fingerprint(envelope['request']), 'result_identity')
    if value['receipt'] is None:
        require(value['status'] == 'not-found' and value['response'] is None, 'missing_receipt')
        return value
    ref = value['receipt']
    require(exact(ref, {'sha256', 'body'}) and ref['sha256'] == sha(wire(ref['body'])), 'receipt_hash')
    record = ref['body']
    require(exact(record, {'version', 'kind', 'intent', 'terminal'}) and type(record['version']) is int
            and record['version'] == 1 and record['kind'] == 'native-publisher-invocation-record-v1', 'receipt_shape')
    intent = record['intent']
    require(exact(intent, {'operation_id', 'invocation_id', 'request', 'request_sha256', 'closure_sha256',
                           'phase', 'supervisor_pid', 'supervisor_starttime'})
            and intent['operation_id'] == value['operation_id'] and intent['invocation_id'] == value['invocation_id']
            and intent['request'] == envelope['request'] and intent['request_sha256'] == value['request_sha256']
            and intent['closure_sha256'] == closure_sha256 and hex64(closure_sha256)
            and intent['phase'] in ('integration', 'release')
            and type(intent['supervisor_pid']) is int and intent['supervisor_pid'] > 0
            and type(intent['supervisor_starttime']) is int and intent['supervisor_starttime'] > 0, 'receipt_intent')
    terminal = record['terminal']
    if terminal is not None:
        require(exact(terminal, {'outcome', 'child_started', 'child_pid', 'child_starttime', 'subreaper_verified',
                                 'direct_child_reaped', 'waitpid_echild', 'child_tree_gone', 'response', 'response_sha256'}), 'terminal_shape')
        require(terminal['outcome'] in ('succeeded', 'publisher_error', 'timed_out', 'cancelled',
                                        'output_limit', 'invalid_response', 'supervisor_error'), 'terminal_outcome')
        require((type(terminal['child_pid']) is int and terminal['child_pid'] > 0)
                if terminal['child_started'] else terminal['child_pid'] is None, 'terminal_child')
        require(terminal['child_starttime'] is None or
                (type(terminal['child_starttime']) is int and terminal['child_starttime'] > 0), 'terminal_child')
        for key in ('child_started', 'subreaper_verified', 'direct_child_reaped', 'waitpid_echild', 'child_tree_gone'):
            require(type(terminal[key]) is bool, 'terminal_boolean')
        proven = terminal['subreaper_verified'] and terminal['waitpid_echild'] and (
            not terminal['child_started'] or terminal['direct_child_reaped'])
        require(terminal['child_tree_gone'] == proven and value['response'] == terminal['response'], 'terminal_proof')
        if terminal['response'] is not None:
            inner_response(terminal['response'], envelope['request'], intent['phase'])
            require(terminal['response_sha256'] == fingerprint(terminal['response'])
                    and terminal['outcome'] == 'succeeded', 'terminal_response')
        else:
            require(terminal['response_sha256'] is None, 'terminal_response')
    expected = 'complete' if terminal and terminal['child_tree_gone'] else 'unknown'
    require(value['status'] == expected and (terminal is not None or value['response'] is None), 'result_status')
    return value


def _invoke(raw, host):
    envelope = request(raw)
    if type(host) is not _Host:
        # Disposable in-process tests only; there is no executable selector.
        require(os.getuid() not in (0, 984) and Path('/tmp') in host.root.resolve().parents
                and host.root.resolve() == host.root, 'synthetic_scope')
    directory, phase, closure = host.admit(envelope['request'])
    if envelope['mode'] == 'review':
        require(phase == 'integration', 'review_phase')
        return host.review(directory, envelope['request'], closure)
    grant = getattr(host, 'continuation', None)
    if grant is not None:
        continuation(grant, envelope['request'])
        require(phase == 'integration', 'continuation_phase')
    uid = host.uid
    path = directory / ('native-invocation-' + envelope['invocation_id'] + '.json')
    def existing():
        require(not path.is_symlink(), 'receipt_symlink')
        record = decode(_read(path, uid, 0o600)) if path.exists() else None
        expected = original_receipt_closure(record, closure, grant) if record else closure
        return validate_result(_result(envelope, record), envelope, expected)
    # No lock creation, mkdir, prctl, subprocess, claim or receipt mutation.
    if envelope['mode'] == 'observe':
        return existing()
    lock = os.open(directory/'native-invocation.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == 0o600, 'invocation_lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InvocationHold('invocation_busy') from None
        if path.exists():
            return existing()  # Same id never executes twice, including terminal failures.
        entries = list(directory.iterdir())
        require(len(entries) <= 256, 'invocation_custody_bound')
        historical = set()
        for item in entries:
            if item.name.startswith('native-invocation-') and item.name.endswith('.json'):
                previous = decode(_read(item, uid, 0o600))
                require(exact(previous, {'version', 'kind', 'intent', 'terminal'})
                        and previous['intent']['operation_id'] == envelope['request']['operation_id'], 'prior_invocation')
                prior_envelope = dict(version=1, mode='observe', invocation_id=previous['intent']['invocation_id'],
                                      request=previous['intent']['request'])
                require(all(previous['intent']['request'][k] == envelope['request'][k]
                    for k in INNER - {'mode'}), 'prior_invocation_identity')
                old_closure = original_receipt_closure(previous, closure, grant)
                validate_result(_result(prior_envelope, previous), prior_envelope, old_closure)
                require(previous['terminal'] is not None and previous['terminal']['child_tree_gone'] is True,
                        'prior_invocation_unresolved')
                if grant and any(r['invocation_id'] == prior_envelope['invocation_id'] for r in grant['receipts']):
                    terminal = previous['terminal']
                    require((terminal['response'] is not None and terminal['response']['status'] not in ('pending','unknown'))
                        or (terminal['response'] is None and prior_envelope['request']['mode'] == 'observe'),
                        'continuation_unknown_effect')
                    historical.add(prior_envelope['invocation_id'])
        require(grant is None or historical == {r['invocation_id'] for r in grant['receipts']},
                'continuation_receipt_missing')
        record = dict(version=1, kind='native-publisher-invocation-record-v1', terminal=None,
                      intent=dict(operation_id=envelope['request']['operation_id'], invocation_id=envelope['invocation_id'],
                                  request=envelope['request'], request_sha256=fingerprint(envelope['request']),
                                  closure_sha256=closure, phase=phase, supervisor_pid=os.getpid(),
                                  supervisor_starttime=_starttime(os.getpid())))
        require(type(record['intent']['supervisor_starttime']) is int, 'supervisor_identity')
        _write(path, record)  # Before spawn; a crash retains an unresolved intent.
        record['terminal'] = _supervise(envelope['request'], phase, host)
        _write(path, record)  # A failed write leaves the prior intent, never a success reply.
        return existing()  # Actual durable bytes, not the in-memory proposed receipt.
    finally:
        os.close(lock)


def invoke(raw):
    """Fixed installed publisher-owner entry; no source/config/key selectors."""
    return _invoke(raw, _Host())


def main():
    require(len(sys.argv) == 1, 'arguments')
    os.umask(0o077)
    result = invoke(sys.stdin.buffer.read(WIRE_LIMIT + 1))
    sys.stdout.buffer.write(wire(result, 1048576 if result.get('kind') == 'native-publisher-unit-review-v1' else LIMIT))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('native-invocation-held\n')
        sys.exit(1)
