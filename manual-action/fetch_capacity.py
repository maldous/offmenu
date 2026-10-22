#!/usr/bin/env python3
"""Read-only filesystem capacity for two fixed existing Foo runner directories.

No directory creation/listing, file-body reads, network, downloads or DB access.
"""
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import PurePosixPath
import re
import socket
import sys

SCHEMA = 'offmenu-additional-source-capacity/1'
PATHS = {
    'outputs': '/srv/offmenu-refresh/outputs',
    'sourceCache': '/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache',
}
RESERVE_BYTES = 10 * 1024**3
SAFETY_BUFFER_BYTES = 2 * 65536  # fetch_sources.CHUNK × 2; exact initial guard.
MINIMUM_BYTES = RESERVE_BYTES + SAFETY_BUFFER_BYTES
NUMBERS = ('totalBytes', 'freeBytes', 'availableBytes', 'totalInodes', 'freeInodes',
           'availableInodes', 'initialDeficitBytes')
ERRORS = {'none', 'missing', 'symlink_or_not_directory', 'permission_denied', 'io_error'}
ZERO_FIELDS = ('acquisitions', 'downloads', 'sourceWrites', 'dbWrites',
               'networkRequests', 'directoryListings', 'fileBodyReads')


def timestamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def error_code(error):
    if error.errno == errno.ENOENT:
        return 'missing'
    if error.errno in (errno.ELOOP, errno.ENOTDIR):
        return 'symlink_or_not_directory'
    if error.errno in (errno.EACCES, errno.EPERM):
        return 'permission_denied'
    return 'io_error'


def open_directory_components(path):
    """Pin each directory by FD; never follow a symlink at any component."""
    path = PurePosixPath(path)
    if not path.is_absolute() or '..' in path.parts:
        raise OSError(errno.EINVAL, 'fixed_path_invalid')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def blocked_row(code):
    return {'status': 'blocked', 'errorCode': code, **{k: None for k in NUMBERS},
            'readOnly': None, 'reserveSatisfied': None}


def observe(path):
    fd = None
    try:
        fd = open_directory_components(path)
        info = os.fstatvfs(fd)
        device = os.fstat(fd).st_dev
        unit = info.f_frsize
        available = info.f_bavail * unit
        row = {'status': 'observed', 'errorCode': 'none',
               'totalBytes': info.f_blocks * unit, 'freeBytes': info.f_bfree * unit,
               'availableBytes': available, 'totalInodes': info.f_files,
               'freeInodes': info.f_ffree, 'availableInodes': info.f_favail,
               'readOnly': bool(info.f_flag & os.ST_RDONLY),
               'initialDeficitBytes': max(0, MINIMUM_BYTES - available),
               'reserveSatisfied': available >= MINIMUM_BYTES}
        return row, device
    except OSError as error:
        return blocked_row(error_code(error)), None
    finally:
        if fd is not None:
            os.close(fd)


def collect():
    observations = {name: observe(path) for name, path in PATHS.items()}
    devices = [observations[name][1] for name in PATHS]
    return {'schema': SCHEMA, 'schemaVersion': SCHEMA, 'executionHost': 'Foo',
            'status': 'complete' if all(row[0]['status'] == 'observed' for row in observations.values()) else 'blocked',
            'scope': 'runner-outputs-only', 'observedAt': timestamp(),
            'reserveBytes': RESERVE_BYTES, 'safetyBufferBytes': SAFETY_BUFFER_BYTES,
            'initialMinimumAvailableBytes': MINIMUM_BYTES,
            'outputs': observations['outputs'][0], 'sourceCache': observations['sourceCache'][0],
            'sameFilesystem': devices[0] == devices[1] if None not in devices else None,
            'homeFilesystemObserved': False, **{key: 0 for key in ZERO_FIELDS}}


def sanitize_report(value):
    """Closed projection; contradictions, arbitrary strings and unknown keys fail."""
    expected = {'schema', 'schemaVersion', 'executionHost', 'status', 'scope', 'observedAt',
                'reserveBytes', 'safetyBufferBytes', 'initialMinimumAvailableBytes',
                'outputs', 'sourceCache', 'sameFilesystem', 'homeFilesystemObserved', *ZERO_FIELDS}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('invalid_capacity_report_keys')
    if (value['schema'] != SCHEMA or value['schemaVersion'] != SCHEMA or value['executionHost'] != 'Foo'
            or value['scope'] != 'runner-outputs-only' or value['homeFilesystemObserved'] is not False
            or value['reserveBytes'] != RESERVE_BYTES or value['safetyBufferBytes'] != SAFETY_BUFFER_BYTES
            or value['initialMinimumAvailableBytes'] != MINIMUM_BYTES
            or not isinstance(value['observedAt'], str)
            or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value['observedAt'])
            or any(type(value[k]) is not int or value[k] != 0 for k in ZERO_FIELDS)):
        raise ValueError('invalid_capacity_boundary')
    observed = []
    clean_rows = {}
    for name in PATHS:
        row = value[name]
        keys = {'status', 'errorCode', 'readOnly', 'reserveSatisfied', *NUMBERS}
        if not isinstance(row, dict) or set(row) != keys or row.get('errorCode') not in ERRORS:
            raise ValueError('invalid_capacity_row')
        if row['status'] == 'observed':
            if (row['errorCode'] != 'none' or any(type(row[k]) is not int or not 0 <= row[k] <= 2**64 for k in NUMBERS)
                    or type(row['readOnly']) is not bool or type(row['reserveSatisfied']) is not bool
                    or not row['availableBytes'] <= row['freeBytes'] <= row['totalBytes']
                    or not row['availableInodes'] <= row['freeInodes'] <= row['totalInodes']
                    or row['initialDeficitBytes'] != max(0, MINIMUM_BYTES - row['availableBytes'])
                    or row['reserveSatisfied'] is not (row['availableBytes'] >= MINIMUM_BYTES)):
                raise ValueError('invalid_capacity_observation')
            observed.append(name)
        elif row['status'] == 'blocked':
            if row['errorCode'] == 'none' or any(row[k] is not None for k in (*NUMBERS, 'readOnly', 'reserveSatisfied')):
                raise ValueError('invalid_capacity_failure')
        else:
            raise ValueError('invalid_capacity_status')
        clean_rows[name] = {k: row[k] for k in sorted(keys)}
    expected_status = 'complete' if len(observed) == len(PATHS) else 'blocked'
    if value['status'] != expected_status:
        raise ValueError('contradictory_capacity_status')
    if (len(observed) == 2 and type(value['sameFilesystem']) is not bool
            or len(observed) != 2 and value['sameFilesystem'] is not None):
        raise ValueError('invalid_filesystem_relation')
    return {**{k: value[k] for k in expected - set(PATHS)}, **clean_rows}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print('capacity_arguments_refused', file=sys.stderr)
        return 2
    if (socket.gethostname().split('.')[0].lower() != 'foo'
            or os.environ.get('RUNNER_NAME', 'foo-offmenu') != 'foo-offmenu'):
        print('capacity_wrong_execution_host', file=sys.stderr)
        return 2
    try:
        result = sanitize_report(collect())
    except (ValueError, OSError):
        print('capacity_report_validation_failed', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if result['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
