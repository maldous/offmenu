#!/usr/bin/env python3
"""Reviewed SELECT over a finalized local Parquet input, with local-only output.

Use through the existing capacity-admitted Foo runner, not as an SQL security
sandbox. Inputs/SQL are trusted and explicitly selected by the owner. The engine
uses an independent in-memory connection and never opens the live SQLite DB.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import resource
import stat
import sys
import threading
import time

GIB = 1024**3
ROOT = Path('/offmenu/data/.offmenu-platform')
RUNTIME = ROOT / 'duckdb/1.5.6-bc9619ed7d4f'
OUTPUT_ROOT = ROOT / 'sql_queries'
JOB = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
VERSION = '1.5.6'
MAX_SQL = 32000


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_path(value, *, existing=False):
    path = Path(value)
    if not path.is_absolute() or str(path) != str(value) or '..' in path.parts:
        raise ValueError('PATH_CANONICAL_REQUIRED')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('SYMLINK_REFUSED')
    if existing and not path.is_file():
        raise ValueError('REGULAR_INPUT_REQUIRED')
    return path


def selected_file(path, limit=None):
    path = canonical_path(path, existing=True)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('REGULAR_INPUT_REQUIRED')
        if limit is None:
            return identity(before)
        value = stream.read(limit + 1)
        if len(value) > limit or identity(before) != identity(os.fstat(stream.fileno())):
            raise ValueError('INPUT_SIZE_OR_CHANGE')
        return value


def identity(st):
    return {'device': st.st_dev, 'inode': st.st_ino, 'bytes': st.st_size,
            'mtime_ns': st.st_mtime_ns, 'ctime_ns': st.st_ctime_ns}


def make_plan(job_id, input_path, sql_path, *, threads=4, memory_gib=8,
              spill_gib=20, result_gib=2):
    """One process, many engine threads; reserve CPU/RAM/disk once per query.

    27 CPU / 54 GiB / 64 GiB are the current admitted per-job limits, not an
    optimum or a request to consume all capacity. Admission is authoritative.
    """
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        raise ValueError('JOB_ID_INVALID')
    ranges = {'threads': (threads, 1, 27), 'memory_gib': (memory_gib, 1, 43),
              'spill_gib': (spill_gib, 1, 62), 'result_gib': (result_gib, 1, 62)}
    for value, low, high in ranges.values():
        if type(value) is not int or not low <= value <= high:
            raise ValueError('QUERY_BUDGET_INVALID')
    # Buffer limits are not process-RSS limits: reserve at least 25% plus 1 GiB.
    process_memory = math.ceil(memory_gib * 1.25) * GIB + GIB
    output_bytes = (spill_gib + result_gib) * GIB + 1024**2
    if process_memory > 54 * GIB or output_bytes > 64 * GIB:
        raise ValueError('QUERY_BUDGET_EXCEEDS_ADMISSION')
    source, sql = canonical_path(input_path), canonical_path(sql_path)
    for path in (source, sql):
        if not path.is_relative_to('/offmenu'):
            raise ValueError('INPUT_OUTSIDE_APPROVED_CHECKOUT')
    if source.suffix.lower() != '.parquet':
        raise ValueError('FINALIZED_PARQUET_REQUIRED')
    output = OUTPUT_ROOT / job_id
    if source.is_relative_to(output) or sql.is_relative_to(output):
        raise ValueError('INPUT_OUTPUT_OVERLAP')
    return {'format': 'offmenu-duckdb-query-plan-v1', 'job_id': job_id,
            'input_path': str(source), 'sql_path': str(sql), 'output_dir': str(output),
            'engine': {'version': VERSION, 'threads': threads,
                       'memory_gib': memory_gib, 'spill_gib': spill_gib},
            'result_max_bytes': result_gib * GIB,
            'resources': {'workers': 1, 'overhead_processes': 2,
                          'cpu_millis': threads * 1000, 'memory_bytes': process_memory,
                          'output_bytes': output_bytes,
                          'read_roots': sorted({str(source.parent), str(sql.parent), str(RUNTIME)}),
                          'write_roots': [str(output)]}}


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('PLAN_INVALID')
    try:
        engine = plan['engine']
        desired = make_plan(plan['job_id'], plan['input_path'], plan['sql_path'],
                            threads=engine['threads'], memory_gib=engine['memory_gib'],
                            spill_gib=engine['spill_gib'],
                            result_gib=plan['result_max_bytes'] // GIB)
    except (KeyError, TypeError, ZeroDivisionError):
        raise ValueError('PLAN_INVALID') from None
    if plan != desired:
        raise ValueError('PLAN_RESERVATION_MISMATCH')
    return desired


def connect(plan, temp):
    # Uses the already-installed pinned package; does not alter the old runtime,
    # dependencies, credentials, host settings or security configuration.
    engine = plan['engine']
    if engine['threads'] > len(os.sched_getaffinity(0)):
        raise ValueError('ENGINE_THREADS_EXCEED_ASSIGNED_CPUS')
    sys.path.insert(0, str(RUNTIME / 'venv/lib/python3.12/site-packages'))
    duckdb = importlib.import_module('duckdb')
    if duckdb.__version__ != VERSION:
        raise ValueError('ENGINE_VERSION_MISMATCH')
    con = duckdb.connect(':memory:', config={
        'threads': str(engine['threads']), 'memory_limit': str(engine['memory_gib']) + 'GiB',
        'max_temp_directory_size': str(engine['spill_gib']) + 'GiB',
        'temp_directory': str(temp), 'autoinstall_known_extensions': 'false',
        'autoload_known_extensions': 'false', 'allow_community_extensions': 'false',
        'allow_unsigned_extensions': 'false'})
    try:
        con.execute('SET allowed_paths = ?', [[plan['input_path']]])
        con.execute('SET allowed_directories = ?', [[str(Path(plan['output_dir'])) + '/']])
        con.execute('SET enable_external_access = false')
        con.execute('SET lock_configuration = true')
        return con
    except BaseException:
        con.close()
        raise


def private_dir(path):
    canonical_path(path)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        sync_dir(path.parent)
    st = path.stat()
    if not path.is_dir() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise ValueError('PRIVATE_OUTPUT_DIRECTORY_REQUIRED')


def sync_dir(path):
    fd = os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(path.parent)


def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while value := stream.read(1024**2):
            h.update(value)
    return h.hexdigest()


def bounded_copy(con, target, maximum):
    """Sampled output guard, not a filesystem quota; brief overshoot is possible."""
    stop, exceeded = threading.Event(), threading.Event()
    def watch():
        while not stop.wait(0.05):
            try:
                over = target.stat().st_size > maximum
            except FileNotFoundError:
                continue
            except OSError:
                over = True  # Unobservable output is not safe to keep growing.
            if over:
                exceeded.set()
                con.interrupt()
                return
    watcher = threading.Thread(target=watch, name='result-budget', daemon=True)
    watcher.start()
    try:
        try:
            rows = con.execute('EXPLAIN ANALYZE COPY (SELECT * FROM _offmenu_query_output) '
                               'TO ? (FORMAT PARQUET, COMPRESSION ZSTD)', [str(target)]).fetchall()
        except Exception:
            if exceeded.is_set():
                raise ValueError('RESULT_BUDGET_EXCEEDED') from None
            raise
    finally:
        stop.set()
        watcher.join()
    if exceeded.is_set() or target.stat().st_size > maximum:
        raise ValueError('RESULT_BUDGET_EXCEEDED')
    return rows


def run(plan, *, connector=connect):
    plan = validate_plan(plan)
    source = Path(plan['input_path'])
    sql = selected_file(plan['sql_path'], MAX_SQL).decode('utf-8')
    before = selected_file(source)
    output = Path(plan['output_dir'])
    # Owner-private roots already exist from installation. Never create /offmenu.
    if not ROOT.is_dir():
        raise ValueError('RUNTIME_ROOT_MISSING')
    private_dir(ROOT)
    private_dir(OUTPUT_ROOT)
    output.mkdir(mode=0o700)  # Exclusive ID: no overwrite, replay or resume.
    sync_dir(output.parent)
    temp = output / 'spill'
    temp.mkdir(mode=0o700)
    sync_dir(temp.parent)
    write_new(output / 'plan.json', encode(plan))
    con = connector(plan, temp)
    try:
        statements = con.extract_statements(sql)
        if len(statements) != 1 or str(statements[0].type) != 'StatementType.SELECT':
            raise ValueError('ONE_SELECT_REQUIRED')
        # SQL is owner-reviewed, not arbitrary SQL from an untrusted web user.
        con.read_parquet(str(source)).create_view('input_data')
        con.sql(sql).create_view('_offmenu_query_output')
        input_metadata = con.execute('SELECT num_rows, num_row_groups FROM parquet_file_metadata(?)',
                                     [str(source)]).fetchone()
        target = output / 'result.parquet'
        start, cpu = time.perf_counter(), time.process_time()
        # ANALYZE executes this COPY once: no second data scan just for profiling.
        profile = bounded_copy(con, target, plan['result_max_bytes'])
        elapsed, cpu_seconds = time.perf_counter() - start, time.process_time() - cpu
        if selected_file(source) != before:
            raise ValueError('INPUT_CHANGED_DURING_QUERY')
        size = target.stat().st_size
        if size > plan['result_max_bytes']:
            raise ValueError('RESULT_BUDGET_EXCEEDED')
        os.chmod(target, 0o600)
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        rows = con.execute('SELECT num_rows FROM parquet_file_metadata(?)', [str(target)]).fetchone()[0]
        profile_bytes = encode(profile)
        if len(profile_bytes) > 1024**2:
            raise ValueError('PROFILE_BUDGET_EXCEEDED')
        write_new(output / 'profile.json', profile_bytes)
        receipt = {'format': 'offmenu-duckdb-query-receipt-v1', 'job_id': plan['job_id'],
                   'status': 'completed', 'plan_sha256': sha(encode(plan)),
                   'sql_sha256': sha(sql.encode()), 'input_stat': before,
                   'input_content_hash_verified': False,
                   'input_rows': input_metadata[0], 'input_row_groups': input_metadata[1],
                   'engine': plan['engine'], 'result_rows': rows, 'result_bytes': size,
                   'result_sha256': hash_file(target), 'profile_sha256': sha(profile_bytes),
                   'query_wall_seconds': elapsed, 'query_cpu_seconds': cpu_seconds,
                   'cpu_to_wall_ratio': cpu_seconds / elapsed if elapsed else 0,
                   'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'security': {'external_access': False, 'extension_autoload': False,
                                'extension_autoinstall': False, 'configuration_locked': True}}
        # Last file is the completion marker. Failed/incomplete outputs are kept
        # local for reconciliation, never called completed or silently retried.
        write_new(output / 'receipt.json', encode(receipt))
        return receipt
    finally:
        con.close()


def read_status(job_id):
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        raise ValueError('JOB_ID_INVALID')
    output = canonical_path(OUTPUT_ROOT / job_id)
    receipt_path = output / 'receipt.json'
    if not receipt_path.exists():
        return {'job_id': job_id, 'status': 'incomplete' if output.exists() else 'not_found'}
    value = json.loads(selected_file(receipt_path, MAX_SQL))
    plan = validate_plan(json.loads(selected_file(output / 'plan.json', MAX_SQL)))
    if (value.get('format') != 'offmenu-duckdb-query-receipt-v1'
            or value.get('job_id') != job_id or value.get('status') != 'completed'
            or value.get('plan_sha256') != sha(encode(plan))):
        raise ValueError('RECEIPT_IDENTITY_INVALID')
    # Small allowlisted status, never SQL/profile text or actual result rows.
    integers = ('input_rows', 'input_row_groups', 'result_rows', 'result_bytes', 'process_peak_rss_kib')
    floats = ('query_wall_seconds', 'query_cpu_seconds', 'cpu_to_wall_ratio')
    hashes = ('plan_sha256', 'sql_sha256', 'result_sha256', 'profile_sha256')
    for field in integers:
        if type(value.get(field)) is not int or value[field] < 0:
            raise ValueError('RECEIPT_METRIC_INVALID')
    for field in floats:
        if type(value.get(field)) not in (int, float) or not math.isfinite(value[field]) or value[field] < 0:
            raise ValueError('RECEIPT_METRIC_INVALID')
    for field in hashes:
        if not isinstance(value.get(field), str) or not re.fullmatch('[0-9a-f]{64}', value[field]):
            raise ValueError('RECEIPT_DIGEST_INVALID')
    if selected_file(output / 'result.parquet')['bytes'] != value['result_bytes']:
        raise ValueError('RESULT_SIZE_MISMATCH')
    return dict({field: value[field] for field in (*integers, *floats, *hashes)},
                job_id=job_id, status='completed', engine=plan['engine'],
                input_content_hash_verified=False, result_content_reverified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--job-id', required=True)
    p.add_argument('--input', required=True)
    p.add_argument('--sql', required=True)
    for flag, default in (('threads', 4), ('memory-gib', 8), ('spill-gib', 20), ('result-gib', 2)):
        p.add_argument('--' + flag, type=int, default=default)
    sub.add_parser('run')  # Exact plan passed on stdin; same resources go to runner.
    sub.add_parser('status').add_argument('--job-id', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'plan':
            result = make_plan(args.job_id, args.input, args.sql, threads=args.threads,
                               memory_gib=args.memory_gib, spill_gib=args.spill_gib,
                               result_gib=args.result_gib)
        elif args.action == 'status':
            result = read_status(args.job_id)
        else:
            raw = sys.stdin.buffer.read(MAX_SQL + 1)
            if len(raw) > MAX_SQL:
                raise ValueError('PLAN_TOO_LARGE')
            result = run(json.loads(raw))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        # Never echo SQL, data, plans, arbitrary exception bodies or credentials.
        print(json.dumps({'ok': False, 'error_class': type(error).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
