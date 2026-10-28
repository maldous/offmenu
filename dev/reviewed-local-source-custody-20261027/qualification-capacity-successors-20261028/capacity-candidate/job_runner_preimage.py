#!/usr/bin/env python3
"""Confined, synchronous job supervisor. No network, daemonization, or credentials.
Run inside the approved SSH jail; invoke long calls through Windmill background jobs.
Read mode is a scheduling promise, NOT a filesystem read-only security boundary.
Receipts/logs on this filesystem survive sessions, not disk loss or hostile same-UID code.
"""
import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
import uuid

VERSION = 1
DEFAULT_ROOT = '/offmenu/data/.offmenu-platform'
TERMINAL = {'succeeded', 'failed', 'timed_out', 'cancelled', 'supervisor_error', 'blocked_reconciliation'}
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
LOG_LIMIT = 1024 * 1024
STOP = False


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_dir(path):
    path = Path(path).absolute()
    for current in [*reversed(path.parents), path]:
        if current.is_symlink():
            raise ValueError('Symlink directory refused')
        if not current.exists():
            try: current.mkdir(mode=0o700)
            except FileExistsError: pass
            fd = os.open(current.parent, os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        if not current.is_dir() or current.is_symlink():
            raise ValueError('Unsafe directory')
    return path


def atomic(path, value):
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, sort_keys=True)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
        d = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(d)
        finally: os.close(d)
    finally:
        if temp.exists(): temp.unlink()


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        return json.load(f)


def setup(root, job_id):
    if not ID.fullmatch(job_id):
        raise ValueError('Invalid job id')
    root = safe_dir(root)
    for name in ('jobs', 'artifacts', 'locks', 'checkpoints'):
        safe_dir(root / name)
    return root, root / 'jobs' / job_id


def status(root, job_id):
    root, directory = setup(root, job_id)
    if not directory.exists(): return {'job_id': job_id, 'status': 'not_found'}
    if directory.is_symlink(): raise ValueError('Symlink job refused')
    receipt = directory / 'receipt.json'
    if not receipt.exists():
        return {'job_id': job_id, 'status': 'unknown', 'reconcile_required': True}
    record = read_json(receipt)
    if record['status'] not in TERMINAL:
        # A stale heartbeat is evidence of uncertainty, never permission to replay.
        record['heartbeat_age_seconds'] = round(max(0, time.time() - record.get('heartbeat_at', 0)), 2)
        record['reconcile_required'] = record['heartbeat_age_seconds'] > 15
    return record


def cancel(root, job_id):
    root, directory = setup(root, job_id)
    record = status(root, job_id)
    if record['status'] in TERMINAL or record['status'] == 'not_found': return record
    atomic(directory / 'cancel.json', {'requested_at': time.time()})
    return {'job_id': job_id, 'status': 'cancellation_requested', 'terminal_verified': False}


def locked_file(path):
    return os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)


def stop_requested(directory):
    return STOP or (directory / 'cancel.json').exists()


def descendants():
    """Only descendants of this supervisor; never inspect environment/command lines."""
    parent = os.getpid()
    edges = {}
    for item in Path('/proc').iterdir():
        if not item.name.isdigit(): continue
        try:
            text = (item / 'stat').read_text()
            rest = text[text.rfind(')') + 2:].split()
            edges[int(item.name)] = int(rest[1])
        except (OSError, ValueError, IndexError): pass
    found = set()
    while True:
        new = {pid for pid, ppid in edges.items() if ppid == parent or ppid in found}
        if new <= found: return found
        found |= new


def cleanup(proc):
    """Subreaper + per-process-group kill, including children that called setsid()."""
    deadline = time.monotonic() + 3
    while True:
        try: os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        for pid in descendants():
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
        proc.poll()
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if not pid: break
            except ChildProcessError: break
        remaining = descendants()
        if not remaining: return True
        if time.monotonic() >= deadline: return False
        time.sleep(.02)


def fsync_dir(path):
    fd = os.open(path, os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def try_lock(path, kind=fcntl.LOCK_EX):
    fd = locked_file(path)
    try: fcntl.flock(fd, kind | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd); return None
    return fd


def inflight(root):
    records = []
    for n in range(2):
        path = root / 'locks' / ('execution-slot-%s.inflight.json' % n)
        if path.exists():
            try: record = read_json(path)
            except (OSError, ValueError): record = {'mode': 'unknown'}
            records.append((n, record))
    return records


def run(root, job_id, command, mode, timeout):
    global STOP
    STOP = False
    if mode not in ('read', 'write') or not 1 <= timeout <= 1800:
        raise ValueError('Invalid mode or timeout')
    if not isinstance(command, str) or not command or '\0' in command or len(command.encode()) > 32000:
        raise ValueError('Invalid command')
    root, directory = setup(root, job_id)
    source_sha = digest(Path(__file__).read_bytes())
    spec = {'command_sha256': digest(command.encode()), 'mode': mode,
            'timeout_seconds': timeout, 'runner_sha256': source_sha}
    request_sha = digest(json.dumps(spec, sort_keys=True).encode())
    def existing():
        record = status(root, job_id)
        if record.get('request_sha256') not in (None, request_sha):
            return {'job_id': job_id, 'status': 'id_conflict', 'reconcile_required': True}
        return record
    if directory.exists(): return existing()
    fds, proc, sel, logs = [], None, None, {}
    record = None
    marker = None
    admitted = False
    def update(**values):
        record.update(values); record['heartbeat_at'] = time.time()
        atomic(directory / 'receipt.json', record)
    def busy(reason):
        return {'job_id': job_id, 'status': 'busy', 'reason': reason, 'reserved': False}
    def blocked(reason, records):
        return {'job_id': job_id, 'status': 'blocked_reconciliation', 'reason': reason,
                'reserved': False, 'reconcile_required': True,
                'unresolved_jobs': [r.get('job_id','unknown') for _,r in records]}
    def stop(signum, frame):
        global STOP
        STOP = True
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(sig, stop)
    try:
        # Long jobs reserve only one Windmill execution worker. All admission is
        # nonblocking: a second call returns promptly, leaving control capacity.
        if timeout > 30:
            fd = try_lock(root / 'locks' / 'execution-long.lock')
            if fd is None: return busy('long_job_active')
            fds.append(fd)
        access = try_lock(root / 'locks' / 'execution-access.lock', fcntl.LOCK_EX if mode == 'write' else fcntl.LOCK_SH)
        if access is None: return busy('incompatible_job_active')
        fds.append(access)
        records = inflight(root)
        if timeout > 30 and any(r.get('timeout_seconds', 1800) > 30 for _,r in records):
            return blocked('unresolved_long_job_marker', records)
        # With an exclusive access lock, no cooperating live job can own any
        # marker. Readers may overlap only a live/suspected read in another slot.
        if records and (mode == 'write' or any(r.get('mode') != 'read' for _,r in records)):
            return blocked('unresolved_inflight_marker', records)
        slot = None
        stale_slot = False
        for n in range(2):
            fd = try_lock(root / 'locks' / ('execution-slot-%s.lock' % n))
            if fd is None: continue
            candidate = root / 'locks' / ('execution-slot-%s.inflight.json' % n)
            if candidate.exists():
                stale_slot = True
                os.close(fd); continue
            slot = n; fds.append(fd); marker = candidate; break
        if slot is None:
            if stale_slot: return blocked('no_safe_slot', records)
            return busy('two_slots_active')
        try:
            directory.mkdir(mode=0o700); fsync_dir(directory.parent)
        except FileExistsError: return existing()
        record = {'version': VERSION, 'job_id': job_id, **spec,
                  'request_sha256': request_sha, 'status': 'starting',
                  'created_at': time.time(), 'heartbeat_at': time.time(),
                  'logs': {'stdout': str(directory / 'stdout.log'), 'stderr': str(directory / 'stderr.log')}}
        atomic(directory / 'receipt.json', record)
        # Marker survives supervisor crashes; only verified cleanup removes it.
        atomic(marker, {'job_id': job_id, 'mode': mode, 'timeout_seconds': timeout, 'request_sha256': request_sha})
        admitted = True
        if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
            raise RuntimeError('SubreaperUnavailable')
        for name in ('stdout', 'stderr'):
            fd = os.open(directory / (name + '.log'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            logs[name] = os.fdopen(fd, 'wb')
        if stop_requested(directory):
            update(status='cancelled', child_tree_gone=True, finished_at=time.time())
            marker.unlink(); fsync_dir(marker.parent)
            return record
        deadline = time.monotonic() + timeout
        proc = subprocess.Popen(['/bin/bash', '--noprofile', '--norc', '-c', command],
                                cwd=os.getcwd(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True, close_fds=True)
        update(status='running', started_at=time.time())
        sel = selectors.DefaultSelector()
        for name, stream in (('stdout', proc.stdout), ('stderr', proc.stderr)):
            os.set_blocking(stream.fileno(), False); sel.register(stream, selectors.EVENT_READ, name)
        sizes = {'stdout': 0, 'stderr': 0}; seen = dict(sizes)
        outcome = None; last_heartbeat = time.monotonic()
        while sel.get_map() or proc.poll() is None:
            if stop_requested(directory): outcome = 'cancelled'; break
            if time.monotonic() >= deadline: outcome = 'timed_out'; break
            for key, events in sel.select(.1):
                chunk = os.read(key.fileobj.fileno(), 16384)
                if not chunk: sel.unregister(key.fileobj); continue
                name = key.data; seen[name] += len(chunk)
                kept = chunk[:max(0, LOG_LIMIT - sizes[name])]
                logs[name].write(kept); sizes[name] += len(kept)
            if time.monotonic() - last_heartbeat >= 2:
                update(); last_heartbeat = time.monotonic()
        code = proc.poll()
        gone = cleanup(proc)
        for f in logs.values(): f.flush(); os.fsync(f.fileno())
        update(status=(outcome or ('succeeded' if code == 0 else 'failed')) if gone else 'supervisor_error',
               reconcile_required=not gone, exit_code=code, finished_at=time.time(), child_tree_gone=gone,
               log_bytes=sizes, output_bytes=seen,
               logs_truncated={k:seen[k]>sizes[k] for k in seen})
        if gone:
            marker.unlink(); fsync_dir(marker.parent)
        else: update(error_class='ChildCleanupUnverified')
    except Exception as error:
        gone = cleanup(proc) if proc else True
        if record is None: raise
        update(status='supervisor_error', error_class=type(error).__name__, child_tree_gone=gone,
               reconcile_required=not gone)
        if admitted and gone and marker.exists():
            marker.unlink(); fsync_dir(marker.parent)
    finally:
        if sel: sel.close()
        if proc:
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()
        for f in logs.values(): f.close()
        for fd in reversed(fds): os.close(fd)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=DEFAULT_ROOT)
    subs = parser.add_subparsers(dest='action', required=True)
    for name in ('run', 'status', 'cancel'):
        sub = subs.add_parser(name); sub.add_argument('--job-id', required=True)
        if name == 'run':
            sub.add_argument('--mode', choices=('read', 'write'), default='write')
            sub.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()
    try:
        if args.action == 'run':
            raw = sys.stdin.buffer.read(65537)
            if len(raw)>65536: raise ValueError('Request too large')
            request = json.loads(raw)
            if set(request) != {'command'}: raise ValueError('Invalid request')
            result = run(args.root,args.job_id,request['command'],args.mode,args.timeout)
        else: result = globals()[args.action](args.root,args.job_id)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status':'request_error','error_class':type(error).__name__})); return 2

if __name__ == '__main__': sys.exit(main())
