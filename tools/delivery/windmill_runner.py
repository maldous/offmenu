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

"""Cooperative host admission, not a cgroup or security boundary.

The supervisor owns a common lock while reading every reservation and committing
its durable marker. Limits are operating demand, never ceiling x job count.
"""
import os
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parents[2] / 'tools/delivery/capacity-policy.json'
POLICY_BYTES = POLICY_PATH.read_bytes()
POLICY = json.loads(POLICY_BYTES)
ACCOUNTING = POLICY.get('resource_accounting', 'reserved-maxima-v1')
if ACCOUNTING not in ('reserved-maxima-v1', 'observed-host-v1'):
    raise ValueError('InvalidResourceAccounting')
OBSERVED_HOST = ACCOUNTING == 'observed-host-v1'
JOB_CEILING = POLICY['windmill']['resource_pool_jobs']
WORKER_CEILING = POLICY['windmill']['computation_subprocesses_per_job']
OVERHEAD_CEILING = POLICY['windmill']['overhead_processes_per_job']
GIB = 1024**3
CPU_RESERVE = POLICY['host']['cpu_reserve']
MEMORY_RESERVE = POLICY['host']['memory_reserve_bytes']
NATIVE_CPU_RESERVATION = POLICY['symphony']['cpu_budget_millis']
NATIVE_MEMORY_RESERVATION = POLICY['symphony']['memory_budget_bytes']
MEMORY_BUDGET = (POLICY['host']['memory_budget_bytes'] if OBSERVED_HOST else
                 POLICY['host']['memory_budget_bytes'] - NATIVE_MEMORY_RESERVATION)
DISK_RESERVE = POLICY['host']['disk_reserve_bytes']
IO_BUDGET = (POLICY['host']['io_slots'] if OBSERVED_HOST else
             POLICY['host']['io_slots'] - POLICY['symphony']['io_slots'])
PROCESS_BUDGET = JOB_CEILING * (WORKER_CEILING + OVERHEAD_CEILING)


def overlap(a, b):
    a, b = Path(a), Path(b)
    return a == b or a in b.parents or b in a.parents


def validate_resources(value, mode, scope=Path('/offmenu')):
    fields = {'workers', 'overhead_processes', 'cpu_millis', 'memory_bytes',
              'output_bytes', 'read_roots', 'write_roots'}
    if not isinstance(value, dict) or set(value) not in (fields, fields | {'io_slots'}):
        raise ValueError('CapacityResourceSchema')
    if 'io_slots' not in value:
        value = dict(value, io_slots=1)
    limits = {'io_slots': (1, IO_BUDGET), 'workers': (1, WORKER_CEILING),
              'overhead_processes': (1, OVERHEAD_CEILING),
              'cpu_millis': (1, 27000), 'memory_bytes': (1024**2, MEMORY_BUDGET),
              'output_bytes': (0, 64 * GIB)}
    for key, (low, high) in limits.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError('CapacityResourceRange')
    for key in ('read_roots', 'write_roots'):
        paths = value[key]
        if not isinstance(paths, list) or len(paths) > 32:
            raise ValueError('CapacityRootCount')
        for raw in paths:
            if not isinstance(raw, str) or len(raw) > 4096:
                raise ValueError('CapacityRootValue')
            path = Path(raw)
            if not path.is_absolute() or '..' in path.parts or str(path) != raw:
                raise ValueError('CapacityRootCanonical')
            if path != scope and scope not in path.parents:
                raise ValueError('CapacityRootScope')
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('CapacityRootSymlink')
        if len(set(paths)) != len(paths):
            raise ValueError('CapacityRootDuplicate')
    if mode == 'read' and value['write_roots']:
        raise ValueError('CapacityReadHasWrites')
    if mode == 'write' and not value['write_roots']:
        raise ValueError('CapacityWritesUndeclared')
    # A pooled writer must not modify the shared coordinator itself.
    control = scope / 'data/.offmenu-platform'
    protected = [control / name for name in ('locks', 'jobs', 'checkpoints')]
    protected += [scope / 'scripts/windmill', scope / 'tools/delivery',
                  scope / '.delivery/windmill-runtime', scope / '.offmenu-runtime']
    if any(overlap(p, q) for p in value['write_roots'] for q in protected):
        raise ValueError('CapacityCoordinatorWrite')
    return value


def requested_processes(value):
    return value['workers'] + value['overhead_processes']


def memory_available():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) * 1024
    raise ValueError('CapacityMemoryUnavailable')


def free_bytes(root):
    fs = os.statvfs(root)
    return fs.f_bavail * fs.f_frsize


def decide(request, active, cpu_count, available_memory, available_disk):
    """Pure conservative decision; caller validates records under one lock.

    CPU demand is independent of worker count. Legacy mode reserves aggregate
    maxima and the native partition. Observed mode checks each job maximum
    against actual shared host headroom; resident work is already in the sample.
    Neither mode guarantees instantaneous kernel enforcement or throughput.
    """
    demands = [request] if OBSERVED_HOST else [*active, request]
    if sum(x.get('io_slots', 1) for x in demands) > IO_BUDGET:
        return 'capacity_io_reserved'
    if len(active) >= JOB_CEILING:
        return 'capacity_slots_active'
    all_resources = demands
    native_cpu = 0 if OBSERVED_HOST else NATIVE_CPU_RESERVATION
    native_memory = 0 if OBSERVED_HOST else NATIVE_MEMORY_RESERVATION
    if sum(x['cpu_millis'] for x in all_resources) > max(0, (cpu_count - CPU_RESERVE) * 1000 - native_cpu):
        return 'capacity_cpu_reserved'
    memory = sum(x['memory_bytes'] for x in all_resources)
    if memory > min(MEMORY_BUDGET, available_memory - MEMORY_RESERVE - native_memory):
        return 'capacity_memory_reserved'
    if sum(requested_processes(x) for x in [*active, request]) > PROCESS_BUDGET:
        return 'capacity_processes_reserved'
    future_logs = 0 if OBSERVED_HOST else JOB_CEILING * 2 * 1024**2
    if sum(x['output_bytes'] for x in all_resources) + DISK_RESERVE + future_logs > available_disk:
        return 'capacity_disk_reserved'
    for other in active:
        if (any(overlap(a, b) for a in request['write_roots'] for b in other['write_roots'] + other['read_roots'])
                or any(overlap(a, b) for a in request['read_roots'] for b in other['write_roots'])):
            return 'capacity_paths_conflict'
    return None


VERSION = 3
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
    for n in range(JOB_CEILING):
        path = root / 'locks' / ('execution-slot-%s.inflight.json' % n)
        if path.exists():
            try: record = read_json(path)
            except (OSError, ValueError): record = {'mode': 'unknown'}
            records.append((n, record))
    return records



def capacity_usage():
    rss = 0
    children = descendants()
    for pid in children:
        try:
            stat = Path('/proc', str(pid), 'stat').read_text()
            rss += max(0, int(stat[stat.rfind(')') + 2:].split()[21])) * os.sysconf('SC_PAGE_SIZE')
        except OSError as error:
            # procfs may report ENOENT or ESRCH when a child exits between
            # enumeration and read. Other errors must retain the failure hold.
            if error.errno not in (errno.ENOENT, errno.ESRCH):
                raise
    return {'processes': len(children), 'rss_bytes': rss}


def run(root, job_id, command, mode, timeout, resources=None):
    global STOP
    STOP = False
    if mode not in ('read', 'write') or not 1 <= timeout <= 1800:
        raise ValueError('Invalid mode or timeout')
    if not isinstance(command, str) or not command or '\0' in command or len(command.encode()) > 32000:
        raise ValueError('Invalid command')
    if resources is not None:
        resources = validate_resources(resources, mode)
    root, directory = setup(root, job_id)
    source_sha = digest(Path(__file__).read_bytes())
    spec = {'command_sha256': digest(command.encode()), 'mode': mode,
            'timeout_seconds': timeout, 'runner_sha256': source_sha,
            'capacity_policy_sha256': digest(POLICY_BYTES)}
    if resources is not None:
        spec['resources'] = resources
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
    admission_fd = None
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
        # All v3 admissions share one short transaction lock. It is released
        # immediately after the durable reservation, never held while working.
        admission_fd = try_lock(root / 'locks' / 'capacity-admission.lock')
        if admission_fd is None: return busy('capacity_admission_busy')
        fds.append(admission_fd)
        # Legacy callers retain their exact long-job and shared-write exclusion.
        if resources is None and timeout > 30:
            fd = try_lock(root / 'locks' / 'execution-long.lock')
            if fd is None: return busy('long_job_active')
            fds.append(fd)
        lock_kind = fcntl.LOCK_EX if mode == 'write' and resources is None else fcntl.LOCK_SH
        access = try_lock(root / 'locks' / 'execution-access.lock', lock_kind)
        if access is None: return busy('incompatible_job_active')
        fds.append(access)
        records = inflight(root)
        if resources is None:
            if any(r.get('capacity_version') == 1 for _, r in records):
                return busy('capacity_pool_active')
            if timeout > 30 and any(r.get('timeout_seconds', 1800) > 30 for _,r in records):
                return blocked('unresolved_long_job_marker', records)
            if records and (mode == 'write' or any(r.get('mode') != 'read' for _,r in records)):
                return blocked('unresolved_inflight_marker', records)
        else:
            active_resources = []
            for n, item in records:
                live = try_lock(root / 'locks' / ('execution-slot-%s.lock' % n))
                if live is not None:
                    os.close(live)
                    return blocked('unresolved_inflight_marker', records)
                if item.get('capacity_version') != 1:
                    return busy('capacity_legacy_active')
                try:
                    active_resources.append(validate_resources(item['resources'], item['mode']))
                except (KeyError, ValueError, TypeError):
                    return blocked('unresolved_inflight_marker', records)
            reason = decide(resources, active_resources, len(os.sched_getaffinity(0)),
                            memory_available(), free_bytes(root))
            if reason: return busy(reason)
        slot = None
        stale_slot = False
        for n in range(JOB_CEILING if resources is not None else POLICY['windmill']['legacy_compatibility_slots']):
            fd = try_lock(root / 'locks' / ('execution-slot-%s.lock' % n))
            if fd is None: continue
            candidate = root / 'locks' / ('execution-slot-%s.inflight.json' % n)
            if candidate.exists():
                stale_slot = True
                os.close(fd); continue
            slot = n; fds.append(fd); marker = candidate; break
        if slot is None:
            if stale_slot: return blocked('no_safe_slot', records)
            return busy('capacity_slots_active' if resources is not None else 'two_slots_active')
        try:
            directory.mkdir(mode=0o700); fsync_dir(directory.parent)
        except FileExistsError: return existing()
        record = {'version': VERSION, 'job_id': job_id, **spec,
                  'request_sha256': request_sha, 'status': 'starting',
                  'created_at': time.time(), 'heartbeat_at': time.time(),
                  'logs': {'stdout': str(directory / 'stdout.log'), 'stderr': str(directory / 'stderr.log')}}
        atomic(directory / 'receipt.json', record)
        # Marker survives supervisor crashes; only verified cleanup removes it.
        reservation = {'job_id': job_id, 'mode': mode, 'timeout_seconds': timeout, 'request_sha256': request_sha}
        if resources is not None:
            reservation.update(capacity_version=1, resources=resources)
        atomic(marker, reservation)
        admitted = True
        os.close(admission_fd); fds.remove(admission_fd); admission_fd = None
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
        child_env = None
        child_preexec = None
        if resources is not None:
            child_env = dict(os.environ, OFFMENU_COMPUTATION_SUBPROCESS_CEILING=str(resources['workers']),
                             OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                             NUMEXPR_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
            first = CPU_RESERVE if OBSERVED_HOST else CPU_RESERVE + (NATIVE_CPU_RESERVATION + 999)//1000
            compute_cpus = sorted(os.sched_getaffinity(0))[first:]
            def child_preexec():
                os.sched_setaffinity(0, compute_cpus)
        proc = subprocess.Popen(['/bin/bash', '--noprofile', '--norc', '-c', command],
                                cwd=os.getcwd(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True, close_fds=True, env=child_env, preexec_fn=child_preexec)
        update(status='running', started_at=time.time())
        sel = selectors.DefaultSelector()
        for name, stream in (('stdout', proc.stdout), ('stderr', proc.stderr)):
            os.set_blocking(stream.fileno(), False); sel.register(stream, selectors.EVENT_READ, name)
        sizes = {'stdout': 0, 'stderr': 0}; seen = dict(sizes)
        outcome = None; last_heartbeat = time.monotonic(); last_capacity_sample = 0
        while sel.get_map() or proc.poll() is None:
            if stop_requested(directory): outcome = 'cancelled'; break
            if time.monotonic() >= deadline: outcome = 'timed_out'; break
            if resources is not None and time.monotonic() - last_capacity_sample >= .5:
                usage = capacity_usage()
                # Sampled guardrails are not instantaneous kernel enforcement.
                if usage['processes'] > requested_processes(resources) or usage['rss_bytes'] > resources['memory_bytes']:
                    outcome = 'failed'; update(error_class='CapacityBudgetExceeded'); break
                if OBSERVED_HOST and memory_available() < MEMORY_RESERVE:
                    outcome = 'failed'; update(error_class='CapacityHostMemoryPressure'); break
                if free_bytes(root) < DISK_RESERVE:
                    outcome = 'failed'; update(error_class='CapacityDiskReserve'); break
                last_capacity_sample = time.monotonic()
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
            if set(request) not in ({'command'}, {'command', 'resources'}): raise ValueError('Invalid request')
            result = run(args.root,args.job_id,request['command'],args.mode,args.timeout,request.get('resources'))
        else: result = globals()[args.action](args.root,args.job_id)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status':'request_error','error_class':type(error).__name__})); return 2

if __name__ == '__main__': sys.exit(main())
