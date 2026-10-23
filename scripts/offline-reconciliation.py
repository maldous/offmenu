#!/usr/bin/env python3
"""Bounded, read-only observations of exact known Foo metadata paths.

No downloads, source-file bodies, discovery, process inspection/control, mounts,
credentials, ledger writes, ownership claims, or coordinator are implemented.
"""
from __future__ import annotations
import argparse
import datetime as dt
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = 'offmenu-offline-reconciliation/1'
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
MAX_NODES = 50000
MAX_DEPTH = 24
MAX_REPORT = 10 * 1024
MODES = ('source-claims', 'transfer-receipts', 'native-continuity', 'disk-reservations', 'pending-ownership')
NATIVE = '/home/user/Documents/Codex/2026-10-13/task-3'
ORIGINALS = '/home/user/src/offmenu-data/originals'
# Unknown paths are deliberately unregistered; never derive them from a report.
TARGETS = {
    'source-claims': (),
    'transfer-receipts': (
        ('ph20-recovery-metadata', '/home/user/Documents/Codex/2026-10-18/worker64-acquisition-continuity/next-real-continuation-foodblog-20261018/actual8805-current-recovery.json', 'json'),
    ),
    'native-continuity': (
        ('native-handover', NATIVE + '/permanent-ledger/handover.json', 'json'),
        ('native-events', NATIVE + '/permanent-ledger/events.jsonl', 'jsonl-tail'),
        ('worker57-result', '/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/final-cut8822-reconciliation/result.json', 'json'),
        ('operating-entrypoint', NATIVE + '/OFFMENU-OPERATING-ENTRYPOINT.md', 'metadata-only'),
    ),
    'disk-reservations': (),
    'pending-ownership': (
        ('native-handover', NATIVE + '/permanent-ledger/handover.json', 'json'),
        ('worker57-refill-summary', '/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/later-next-eleven-refill-packets/eleven-packet-summary.json', 'json'),
        ('owner31-hold-summary', '/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/owner31-source-use-incident-retained/hold-propagation-result.json', 'metadata-only'),
    ),
}
SPACE_TARGETS = (
    ('runner-cache', '/srv/offmenu-refresh/cache'),
    ('runner-output', '/srv/offmenu-refresh/outputs'),
    ('native-originals', ORIGINALS),
)
ACCESS_STATES = {'observed', 'missing', 'permission-denied', 'symlink-forbidden',
                 'not-directory', 'not-regular-file', 'read-failed', 'size-limit',
                 'invalid-metadata', 'changed-during-read', 'node-limit'}
STATES = {'pending', 'queued', 'running', 'active', 'claimed', 'complete', 'completed',
          'failed', 'blocked', 'held', 'partial', 'interrupted', 'cancelled', 'closed',
          'needs_owner', 'needs-owner', 'received', 'verified', 'accepted', 'unassigned'}
STATUS_FIELDS = {'status', 'state', 'claimStatus', 'transferStatus', 'collectionStatus'}
OWNER_FIELDS = {'owner', 'ownerId', 'owner_id', 'worker', 'workerId', 'worker_id'}
LIST_FIELDS = {'claims', 'receipts', 'partials', 'transfers', 'reservations', 'pending',
               'tasks', 'workers', 'results', 'events', 'sources', 'files', 'collections'}
RESERVATION_FIELDS = {'reservedBytes', 'reserved_bytes', 'reservationBytes', 'reservation_bytes'}
SEQUENCE_FIELDS = {'sequence', 'seq', 'journalSequence', 'eventSequence'}
TIME_FIELDS = {'timestamp', 'observedAt', 'createdAt', 'updatedAt', 'eventAt'}
TIME_RE = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def timestamp(value):
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        raise ValueError('invalid-time')
    dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value


def _uint(value):
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError('invalid-count')
    return value


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate-key')
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


def _open_exact(path, directory=False):
    """Open every component without following symlinks, including ancestors."""
    parts = Path(path).parts
    if not Path(path).is_absolute() or any(p in ('.', '..') for p in parts):
        raise ValueError('invalid-fixed-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for index, name in enumerate(parts[1:]):
            last = index == len(parts) - 2
            # Inspect each component without following links before opening it.
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise OSError(errno.ELOOP, 'symlink-forbidden')
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
            if not last or directory:
                flags |= os.O_DIRECTORY
            child = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _error(error):
    return {errno.ENOENT: 'missing', errno.EACCES: 'permission-denied',
            errno.EPERM: 'permission-denied', errno.ELOOP: 'symlink-forbidden',
            errno.ENOTDIR: 'not-directory'}.get(error.errno, 'read-failed')


def summarize(records):
    result = {'recordsParsed': len(records), 'mappingNodesObserved': 0,
              'listFieldCounts': {}, 'statusFieldCounts': {}, 'ownerFieldCounts': {},
              'reservationFieldCounts': {}, 'reservationFieldByteSums': {},
              'maximumSequenceObserved': None, 'latestTimestampObserved': None}
    todo = [(record, 0) for record in records]
    nodes = 0
    while todo:
        value, depth = todo.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError('node-limit')
        if isinstance(value, dict):
            result['mappingNodesObserved'] += 1
            for key, item in value.items():
                if key in LIST_FIELDS and isinstance(item, (list, dict)):
                    result['listFieldCounts'][key] = result['listFieldCounts'].get(key, 0) + len(item)
                if key in STATUS_FIELDS and isinstance(item, str) and item in STATES:
                    result['statusFieldCounts'][item] = result['statusFieldCounts'].get(item, 0) + 1
                if key in OWNER_FIELDS and ((type(item) is int and 0 <= item <= 64) or
                        (isinstance(item, str) and re.fullmatch(r'(?:worker[- ]?)?(?:0?[0-9]|[1-5][0-9]|6[0-4])', item))):
                    owner = str(int(re.sub(r'^worker[- ]?', '', str(item))))
                    result['ownerFieldCounts'][owner] = result['ownerFieldCounts'].get(owner, 0) + 1
                if key in RESERVATION_FIELDS and type(item) is int and 0 <= item <= 2**53:
                    result['reservationFieldCounts'][key] = result['reservationFieldCounts'].get(key, 0) + 1
                    result['reservationFieldByteSums'][key] = result['reservationFieldByteSums'].get(key, 0) + item
                    _uint(result['reservationFieldByteSums'][key])
                if key in SEQUENCE_FIELDS and type(item) is int and 0 <= item <= 2**63 - 1:
                    result['maximumSequenceObserved'] = max(result['maximumSequenceObserved'] or 0, item)
                if key in TIME_FIELDS and isinstance(item, str) and TIME_RE.fullmatch(item):
                    try:
                        stamp = timestamp(item)
                    except ValueError:
                        continue
                    old = result['latestTimestampObserved']
                    if old is None or dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')) > dt.datetime.fromisoformat(old.replace('Z', '+00:00')):
                        result['latestTimestampObserved'] = stamp
                if isinstance(item, (dict, list)):
                    todo.append((item, depth + 1))
        elif isinstance(value, list):
            todo.extend((item, depth + 1) for item in value)
    return result


def observe_file(target):
    label, path, kind = target
    result = {'targetId': label, 'path': path, 'readMode': kind, 'access': 'read-failed',
              'fileBytes': None, 'modifiedAtNs': None, 'metadataBytesRead': 0,
              'wholeFileObserved': False, 'metadataSHA256': None, 'digestScope': None, 'summary': None}
    fd = None
    try:
        fd = _open_exact(path)
        before = os.fstat(fd)
        result.update(fileBytes=before.st_size, modifiedAtNs=before.st_mtime_ns)
        if not stat.S_ISREG(before.st_mode):
            result['access'] = 'not-regular-file'
            return result
        if kind == 'metadata-only':
            result['access'] = 'observed'
            return result
        offset = max(0, before.st_size - MAX_BYTES) if kind == 'jsonl-tail' else 0
        if before.st_size > MAX_BYTES and kind != 'jsonl-tail':
            result['access'] = 'size-limit'
            return result
        os.lseek(fd, offset, os.SEEK_SET)
        data = bytearray()
        while len(data) <= MAX_BYTES:
            chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        result['metadataBytesRead'] = len(data)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            result['access'] = 'changed-during-read'
            return result
        if len(data) > MAX_BYTES:
            result['access'] = 'size-limit'
            return result
        raw = bytes(data)
        if kind == 'jsonl-tail':
            if offset:
                raw = raw.partition(b'\n')[2]
            lines = raw.splitlines()
            nonempty = [line for line in lines if line.strip()]
            rows = nonempty[-MAX_ROWS:]
            records = [_json(line) for line in rows]
            result['wholeFileObserved'] = offset == 0 and len(nonempty) <= MAX_ROWS
        else:
            records = [_json(raw)]
            result['wholeFileObserved'] = True
        result['summary'] = summarize(records)
        result['metadataSHA256'] = hashlib.sha256(data).hexdigest()
        result['digestScope'] = 'whole-file' if offset == 0 else 'bounded-tail'
        result['access'] = 'observed'
    except OSError as error:
        result['access'] = _error(error)
    except (ValueError, UnicodeError, RecursionError) as error:
        result['access'] = 'node-limit' if str(error) == 'node-limit' else 'invalid-metadata'
        result['summary'] = None
        result['wholeFileObserved'] = False
    finally:
        if fd is not None:
            os.close(fd)
    return result


def observe_space(target):
    label, path = target
    result = {'targetId': label, 'path': path, 'access': 'read-failed',
              'availableBytes': None, 'availableInodes': None, 'readOnly': None}
    fd = None
    try:
        fd = _open_exact(path, directory=True)
        value = os.fstatvfs(fd)
        result.update(access='observed', availableBytes=value.f_bavail * value.f_frsize,
                      availableInodes=max(0, value.f_favail), readOnly=bool(value.f_flag & os.ST_RDONLY))
    except OSError as error:
        result['access'] = _error(error)
    finally:
        if fd is not None:
            os.close(fd)
    return result


def collect(mode):
    report = {'schemaVersion': SCHEMA, 'mode': mode,
              'observedAt': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
              'status': 'blocked', 'reason': 'unregistered-metadata-paths',
              'files': [observe_file(t) for t in TARGETS[mode]],
              'spaces': [observe_space(t) for t in SPACE_TARGETS] if mode == 'disk-reservations' else [],
              'metadataRegistrationComplete': bool(TARGETS[mode]),
              'nativeProcessesObserved': False, 'safeToAcquireEstablished': False,
              'reservationTotalsAuthoritative': False, 'ownershipEstablished': False,
              'sourceContentsUploaded': False, 'sourceWrites': 0, 'downloads': 0,
              'fieldCountsAreObservationsOnly': True}
    if TARGETS[mode]:
        if not all(v['access'] == 'observed' for v in report['files']):
            report['reason'] = 'metadata-access-incomplete'
        elif not all(v['wholeFileObserved'] for v in report['files'] if v['readMode'] != 'metadata-only'):
            report['reason'] = 'bounded-metadata-sample-only'
        else:
            report.update(status='complete', reason='registered-observations-complete')
    return sanitize_report(report)


def sanitize_summary(value):
    keys = {'recordsParsed', 'mappingNodesObserved', 'listFieldCounts', 'statusFieldCounts',
            'ownerFieldCounts', 'reservationFieldCounts', 'reservationFieldByteSums',
            'maximumSequenceObserved', 'latestTimestampObserved'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('invalid-summary')
    out = {key: _uint(value[key]) for key in ('recordsParsed', 'mappingNodesObserved')}
    for key, allowed in (('listFieldCounts', LIST_FIELDS), ('statusFieldCounts', STATES),
                         ('ownerFieldCounts', {str(n) for n in range(65)}),
                         ('reservationFieldCounts', RESERVATION_FIELDS), ('reservationFieldByteSums', RESERVATION_FIELDS)):
        if not isinstance(value[key], dict) or not set(value[key]) <= allowed:
            raise ValueError('invalid-summary-map')
        out[key] = {k: _uint(v) for k, v in value[key].items()}
    out['maximumSequenceObserved'] = None if value['maximumSequenceObserved'] is None else _uint(value['maximumSequenceObserved'])
    out['latestTimestampObserved'] = None if value['latestTimestampObserved'] is None else timestamp(value['latestTimestampObserved'])
    return out


def sanitize_report(value):
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA or value.get('mode') not in MODES:
        raise ValueError('invalid-report')
    mode = value['mode']
    out = {'schemaVersion': SCHEMA, 'mode': mode, 'observedAt': timestamp(value['observedAt'])}
    expected_flags = {'nativeProcessesObserved': False, 'safeToAcquireEstablished': False,
                      'reservationTotalsAuthoritative': False, 'ownershipEstablished': False,
                      'sourceContentsUploaded': False, 'sourceWrites': 0, 'downloads': 0,
                      'fieldCountsAreObservationsOnly': True,
                      'metadataRegistrationComplete': bool(TARGETS[mode])}
    for key, required in expected_flags.items():
        if type(value.get(key)) is not type(required) or value[key] != required:
            raise ValueError('invalid-flag')
        out[key] = required
    files = value.get('files')
    if not isinstance(files, list) or len(files) != len(TARGETS[mode]):
        raise ValueError('invalid-targets')
    out['files'] = []
    for row, (label, path, kind) in zip(files, TARGETS[mode]):
        if not isinstance(row, dict) or (row.get('targetId'), row.get('path'), row.get('readMode')) != (label, path, kind) or row.get('access') not in ACCESS_STATES:
            raise ValueError('invalid-target')
        clean = {'targetId': label, 'path': path, 'readMode': kind, 'access': row['access']}
        for key in ('fileBytes', 'modifiedAtNs'):
            clean[key] = None if row.get(key) is None else _uint(row[key])
        clean['metadataBytesRead'] = _uint(row.get('metadataBytesRead'))
        if clean['metadataBytesRead'] > MAX_BYTES + 1 or type(row.get('wholeFileObserved')) is not bool:
            raise ValueError('invalid-read-bound')
        clean['wholeFileObserved'] = row['wholeFileObserved']
        digest, scope = row.get('metadataSHA256'), row.get('digestScope')
        if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
            raise ValueError('invalid-digest')
        if scope not in (None, 'whole-file', 'bounded-tail') or (digest is None) != (scope is None):
            raise ValueError('invalid-digest-scope')
        clean.update(metadataSHA256=digest, digestScope=scope)
        clean['summary'] = None if row.get('summary') is None else sanitize_summary(row['summary'])
        if row['access'] != 'observed' and (clean['summary'] is not None or digest is not None or clean['wholeFileObserved']):
            raise ValueError('invalid-blocked-summary')
        if row['access'] == 'observed':
            if clean['fileBytes'] is None or clean['modifiedAtNs'] is None:
                raise ValueError('missing-file-stat')
            if kind != 'metadata-only' and (clean['summary'] is None or digest is None):
                raise ValueError('missing-metadata-summary')
            if clean['wholeFileObserved'] and (scope != 'whole-file' or clean['metadataBytesRead'] != clean['fileBytes']):
                raise ValueError('invalid-complete-read')
        if kind == 'metadata-only' and (clean['metadataBytesRead'] or clean['summary'] is not None or digest is not None or clean['wholeFileObserved']):
            raise ValueError('unexpected-body-read')
        out['files'].append(clean)
    spaces = value.get('spaces')
    expected = SPACE_TARGETS if mode == 'disk-reservations' else ()
    if not isinstance(spaces, list) or len(spaces) != len(expected):
        raise ValueError('invalid-spaces')
    out['spaces'] = []
    for row, (label, path) in zip(spaces, expected):
        if not isinstance(row, dict) or (row.get('targetId'), row.get('path')) != (label, path) or row.get('access') not in ACCESS_STATES:
            raise ValueError('invalid-space')
        clean = {'targetId': label, 'path': path, 'access': row['access']}
        for key in ('availableBytes', 'availableInodes'):
            clean[key] = None if row.get(key) is None else _uint(row[key])
        if row.get('readOnly') is not None and type(row['readOnly']) is not bool:
            raise ValueError('invalid-space-flag')
        clean['readOnly'] = row.get('readOnly')
        out['spaces'].append(clean)
    reason = ('unregistered-metadata-paths' if not TARGETS[mode] else
              'metadata-access-incomplete' if not all(r['access'] == 'observed' for r in out['files']) else
              'bounded-metadata-sample-only' if not all(r['wholeFileObserved'] for r in out['files'] if r['readMode'] != 'metadata-only') else
              'registered-observations-complete')
    status = 'complete' if reason == 'registered-observations-complete' else 'blocked'
    if value.get('status') != status or value.get('reason') != reason:
        raise ValueError('invalid-report-status')
    out.update(status=status, reason=reason)
    if len(canonical(out)) > MAX_REPORT:
        raise ValueError('report-size-limit')
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=MODES)
    args = parser.parse_args(argv)
    report = collect(args.mode)
    print(canonical(report).decode())
    return 0 if report['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
