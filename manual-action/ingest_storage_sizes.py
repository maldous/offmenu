"""Bounded metadata-only sizes for fixed runner staging paths, never DB content.

No directory enumeration, SQLite connection, source/cache scan, or file open is
performed. Independent lstat observations are not an atomic disk-usage total.
Allocated bytes sum reported blocks over these paths, not deduplicated/exclusive
physical usage, a filesystem total, or an attribution of ingest growth.
"""
from __future__ import annotations
from runner_paths import resolve_layout
from pathlib import Path
import stat
from ingest_api import DOMAINS

SCHEMA = 'offmenu-storage-sizes/1'
FILES = ('database', 'wal', 'shm')
SUFFIXES = ('', '-wal', '-shm')
METRICS = ('logical_bytes', 'allocated_bytes')
MAX_BYTES = 10**15
FILE_COUNT = len(DOMAINS) * len(FILES)


def _bytes(value):
    return value if type(value) is int and 0 <= value <= MAX_BYTES else None


def _totals(domains):
    rows = [row for domain in DOMAINS for row in domains[domain]]
    totals = {'files_total': FILE_COUNT}
    for index, metric in enumerate(METRICS):
        values = [row[index] for row in rows]
        totals[metric.replace('_bytes', '_files_known')] = sum(value is not None for value in values)
        totals[metric] = _bytes(sum(values)) if all(value is not None for value in values) else None
    return totals


def unknown_storage_sizes():
    domains = {domain: [[None, None] for _ in FILES] for domain in DOMAINS}
    return {'schema': SCHEMA, 'scope': 'fixed_runner_staging_database_paths_only',
        'snapshot_scope': 'independent_file_metadata_not_atomic',
        'method': 'lstat_only_no_content_reads', 'files': list(FILES), 'metrics': list(METRICS),
        'domains': domains, 'totals': _totals(domains),
        'cache': {'scope': 'not_measured', 'logical_bytes': None, 'allocated_bytes': None}}


def validate_storage_sizes(value):
    """Strict optional public field; exact finite shape, no paths/free text."""
    expected = unknown_storage_sizes()
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError('invalid_storage_sizes')
    for field in ('schema', 'scope', 'snapshot_scope', 'method', 'files', 'metrics', 'cache'):
        if value[field] != expected[field]:
            raise ValueError('invalid_storage_sizes')
    domains = value['domains']
    if type(domains) is not dict or set(domains) != set(DOMAINS):
        raise ValueError('invalid_storage_sizes')
    for rows in domains.values():
        if type(rows) is not list or len(rows) != len(FILES):
            raise ValueError('invalid_storage_sizes')
        for row in rows:
            if type(row) is not list or len(row) != len(METRICS):
                raise ValueError('invalid_storage_sizes')
            if any(item is not None and (type(item) is not int or _bytes(item) is None) for item in row):
                raise ValueError('invalid_storage_sizes')
            if row[0] is None and row[1] is not None:
                raise ValueError('invalid_storage_sizes')
    totals = value['totals']
    if type(totals) is not dict or set(totals) != set(expected['totals']):
        raise ValueError('invalid_storage_sizes')
    if any(item is not None and type(item) is not int for item in totals.values()):
        raise ValueError('invalid_storage_sizes')
    if totals != _totals(domains):
        raise ValueError('invalid_storage_sizes')
    return value


def _directory_status(path, cache):
    # Fixed ancestor checks only; no listdir/glob/walk and no symlink traversal.
    if path in cache:
        return cache[path]
    if path.parent != path and _directory_status(path.parent, cache) != 'directory':
        cache[path] = cache[path.parent]
        return cache[path]
    try:
        result = path.lstat()
        status = 'directory' if stat.S_ISDIR(result.st_mode) else 'unknown'
    except FileNotFoundError:
        status = 'absent'
    except OSError:
        status = 'unknown'
    cache[path] = status
    return status


def capture_storage_sizes(state_dir):
    """At most 24 leaf stats plus fixed ancestors; absent files are known zero.

    Allocated bytes use the OS st_blocks value (512-byte units), not logical
    length. Missing st_blocks, denied/nonregular/symlink paths are unknown.
    Cache/source directory sizes are intentionally unmeasured and null.
    """
    value = unknown_storage_sizes()
    layout = resolve_layout(state_dir)
    ancestors = {}
    for domain in DOMAINS:
        directory = layout.domain_path(domain).parent
        status = _directory_status(directory, ancestors)
        for index, suffix in enumerate(SUFFIXES):
            if status == 'absent':
                value['domains'][domain][index] = [0, 0]
                continue
            if status != 'directory':
                continue
            try:
                observed = (directory / (domain + '.sqlite3' + suffix)).lstat()
                if not stat.S_ISREG(observed.st_mode):
                    continue
                logical = _bytes(observed.st_size)
                blocks = getattr(observed, 'st_blocks', None)
                allocated = _bytes(blocks * 512) if type(blocks) is int and blocks >= 0 else None
                if logical is not None:
                    value['domains'][domain][index] = [logical, allocated]
            except FileNotFoundError:
                value['domains'][domain][index] = [0, 0]
            except OSError:
                pass
    value['totals'] = _totals(value['domains'])
    return validate_storage_sizes(value)
