#!/usr/bin/env python3
"""One normal-user, metadata-only Foo custody snapshot. No acquisition or access changes."""
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

MAX_BYTES = 2 * 1024 * 1024

MAX_ROWS = 5000

MAX_NODES = 50000

MAX_DEPTH = 24

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

CUTOVER_SHA256 = '70728e4a78d6a6bc785ee9ba1001bfcd8774b4286064615fe58d2c0d3bf21c1e'
CUTOVER_B64 = 'ewogICJzY2hlbWFfdmVyc2lvbiI6IDEsCiAgImdlbmVyYXRlZF9hdF91dGMiOiAiMjAyNi0xMC0xOFQxMjo1ODo1MFoiLAogICJzdGFnZSI6ICJDT01QTEVURV9SRUFEX09OTFlfSEFORE9WRVIiLAogICJwZW5kaW5nX3JlY2VpcHRzIjogWwogICAgewogICAgICAib3duZXIiOiAxLAogICAgICAic2VxdWVuY2UiOiA5MjE4LAogICAgICAiZXZlbnRfaWQiOiAib3duZXIwMS1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItMjAyNjEwMTgtZmluaXRlLXJlc3VsdCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM4OWYtMjM5Yy03MTkxLTg1NTUtNTNiZjE1MmQ2ZTg0IiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZmLWM4NjctNzMxZS05YjE5LTZhZDUzN2EwNzIxMiIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItMDEvTS1SRUNJUEUtSU5HUkVESUVOVC1BRlRFUjg5NDItVzAxLTIwMjYxMDE4L2ZpbmFsLXJlY2lwZS1pbmdyZWRpZW50LXJlc3VsdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjU5NDViNGY4NzkxNGYzZjM2MmQ0ZTBiNmY4ZjBkZGI0NjQ3YTM5Y2MwZjJiODYwZjNkMzg4NjMzM2FkYjc2MGIiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj0xfG93bmVyMDEtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLTIwMjYxMDE4LWZpbml0ZS1yZXN1bHR8c2hhMjU2PTU5NDViNGY4NzkxNGYzZjM2MmQ0ZTBiNmY4ZjBkZGI0NjQ3YTM5Y2MwZjJiODYwZjNkMzg4NjMzM2FkYjc2MGIiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogMiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA0NTc0NTAsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIk9yaWdpbmFsIGxhbmd1YWdlLCBzb3VyY2UtdXNlLCBhdHRyaWJ1dGlvbiwgY3VzdG9keSwgdHlwZSwgcmlnaHRzIGFuZCBjb3ZlcmFnZSBsaW1pdGF0aW9ucyByZXRhaW5lZDsgbm8gcmVjaXBlLXJlY29yZCBvciBjb3VudHJ5LWNvbXBsZXRpb24gYWNjZXB0YW5jZS4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA0LAogICAgICAic2VxdWVuY2UiOiA5MjQ0LAogICAgICAiZXZlbnRfaWQiOiAib3duZXIwNC1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzhhNS0xNTM4LTc4NjEtOGIwZi1kM2QyODMxMWZjNjIiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjAxLTc0NzMtNzYzNy04MWE4LTQzYjY0NGUwMGMzYSIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDEtY2NjZi03N2I1LTgyZDgtMjY3YTJlNjYwOTM3IiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvc3JjL29mZm1lbnUtZGF0YS9vcmlnaW5hbHMvY291bnRyeS1mb2xsb3d0aHJvdWdoLTIwMjYxMDE1L293bmVyLTQvcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLTIwMjYxMDE4L3Jlc3VsdC1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogImVjNmM5ODMwMGFlNWMzM2UwYTA0YjhjZmU5Mjk0OTQxMzNlZTgyMGViMDJmNjNmMDMxNGJkYWE5ZTYzZmQ4ZDgiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvc3JjL29mZm1lbnUtZGF0YS9vcmlnaW5hbHMvY291bnRyeS1mb2xsb3d0aHJvdWdoLTIwMjYxMDE1L293bmVyLTQvcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLTIwMjYxMDE4L3NvdXJjZS1zdGF0dXMtY29ycmVjdGlvbi5qc29uIiwKICAgICAgICAgICJzaGEyNTYiOiAiOWE5YWNlNjM3Y2I1MGE2MGQ3ZmY0N2RmNGJiNTJkZGU0MjAxNWE3YzM0YTA1YzNkMWFhNzg2NjNmMGVhNzIxMSIKICAgICAgICB9CiAgICAgIF0sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj00fG93bmVyMDQtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9ZWM2Yzk4MzAwYWU1YzMzZTBhMDRiOGNmZTkyOTQ5NDEzM2VlODIwZWIwMmY2M2YwMzE0YmRhYTllNjNmZDhkOCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAyMywKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiAxODU4Nzk2MSwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiMjMgb3JpZ2luYWxzIGluY2x1ZGUgb25lIHNoYXJlZCBIWkIgY29va2Jvb2sgb25jZS4gRUNNIHNvdXJjZS1zdGF0dXMgY29ycmVjdGlvbiBpcyBIVFRQNDAzLCBub3QgYSByZWRpcmVjdCwgYW5kIG5vdCBhbm90aGVyIGFjcXVpc2l0aW9uIHJlc3VsdC4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiAxMCwKICAgICAgInNlcXVlbmNlIjogOTI4NSwKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjEwLXN1YnN0YW50aWFsLWFmdGVyODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGVkLWJlOGMtNzM0MC1iMjVlLTg3YmVlOTI3MmQ3ZSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDItMDA5Yy03MDY3LTg2NGUtZjVhNTNiNjMyYWY3IiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMi05NjgwLTcwYWQtOGZlYS04MWJhYmJmYWE3MmEiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIxMC1zdWJzdGFudGlhbC1hZnRlcjg5NDIvcmVzdWx0LW1hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiNmUxZWRjYjI1N2FhODcxYjI5N2YyYTBhYTM2YWRkYzQwNDJlYmJlNjdlNTNlMDVhODNjYzA5ZjQyNDM4NDczMyIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIxMC1zb3VyY2UtY29weS1jdXN0b2R5L3NvdXJjZS1jb3B5LWludmVudG9yeS1maW5hbC5qc29uIiwKICAgICAgICAgICJzaGEyNTYiOiAiMDJkZWRiODVkMmMxOTFhM2Q2ZDU0OTJiZDYyZTE5NTY3OWRkZjc4MTI3OTAwOWY3YWE2NDg3NzA3MzM5NGZkNiIKICAgICAgICB9LAogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyMTAtZW5kLXRvLWVuZC1zb3VyY2UtYmF0Y2gvYmF0Y2gtcmVzdWx0Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICJiM2NjNjA5OWQzYzJjMTNiNWZmZTU4OTZiNjU5NGRiMDEyMjY0MTBkZWZjNWQwNTAzZDkzNWQxOGU3ODY1Mzg0IgogICAgICAgIH0sCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIxMC1zb3VyY2UtcmVmaWxsLTEwNTAvcmVmaWxsLXJlc3VsdC5qc29uIiwKICAgICAgICAgICJzaGEyNTYiOiAiMzc3ZDdlNmVhNDk3OTI3NjY1NThhMDZiYmU4MGQ0MmJkOWY1ZmM3MGMwYmEzMmQ1YWI3MzEzMzRkZjIzNDAyYSIKICAgICAgICB9CiAgICAgIF0sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj0xMHx3b3JrZXIxMC1zdWJzdGFudGlhbC1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4fHNoYTI1Nj02ZTFlZGNiMjU3YWE4NzFiMjk3ZjJhMGFhMzZhZGRjNDA0MmViYmU2N2U1M2UwNWE4M2NjMDlmNDI0Mzg0NzMzIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMzU3MTk4NiwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiU0EgcGFwZXIgcmVwb3J0cyBTT0ZUV0FSRS1lc3RpbWF0ZWQgY29tcG9zaXRpb24sIG5vdCBsYWJvcmF0b3J5IG9yIG5hdGlvbmFsIGFuYWx5dGljYWwgbWVhc3VyZW1lbnRzLiBOTyByZWNpcGUgY29sbGVjdGlvbiBkb2VzIG5vdCBsaWZ0IGV4aXN0aW5nIG5hdGlvbmFsIE5PIHNvdXJjZSBob2xkcy4gTmF0aXZlIHR1cm4gd2FzIHJlcG9ydGluZywgbm8gb3duIHRyYW5zZmVyIHJ1bm5pbmc7IGV4dGVybmFsIHF1ZXVlIHVua25vd24uIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMTEsCiAgICAgICJzZXF1ZW5jZSI6IDkxOTgsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIxMS1yZWNpcGUtcmVmaWxsODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGVlLTBkMjktNzVkMC04M2RmLWRhNGY3YWM2YzlhNCIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZS1mN2E4LTc3YjctYTJiZC1hZmRjMTA4MmFjMDkiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTExL3JlY2lwZS1pbmdyZWRpZW50LXJlZmlsbDg5NDItMjAyNjEwMTgvcmVzdWx0LW1hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiNzhjYTgzODcyOGFhYWU3NDQwM2ExZmNjNGRmYzBhNDY0NzZmYmRkM2JkNjM0NWEzMGQ0OWM4MzRlODlkNDkxNCIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTExfHdvcmtlcjExLXJlY2lwZS1yZWZpbGw4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9NzhjYTgzODcyOGFhYWU3NDQwM2ExZmNjNGRmYzBhNDY0NzZmYmRkM2JkNjM0NWEzMGQ0OWM4MzRlODlkNDkxNCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA1OCwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA0NTA1Mjk5OSwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiNTggc291cmNlLWNvbnRlbnQgb2JqZWN0cyA9NTQgcmVjaXBlIEhUTUwrMSByZWNpcGUtYmVhcmluZyBQREYrMyBpbmdyZWRpZW50IG5hcnJhdGl2ZXM7NDUsMDUyLDk5OSBCIGRlcml2ZWQgYnkgYWRkaW5nIHRoZSB0aHJlZSBleHBsaWNpdCBjYXRlZ29yeSB0b3RhbHMuNjQgcmVzcG9uc2VmaWxlcy80NSw5NDEsMDY2IEIgaW5jbHVkZXM2IHByZXBhcmF0aW9uL3N1cHBvcnQgZmlsZXMuIE5vIGFuYWx5dGljYWwgY29tcG9zaXRpb24gZGF0YXNldCBhY3F1aXJlZC4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiAxMiwKICAgICAgInNlcXVlbmNlIjogOTIxNywKICAgICAgImV2ZW50X2lkIjogIm93bmVyMTItcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLU1OLXN1YnNldC1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGVlLTUyNTItN2Y2My04YjQzLWNmNzMwZWNkN2UwNSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZi1jODY4LTcxOWMtOWZiZi04MjNiNmEzZDIwMjgiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIxMi1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDIvTU4tYXV0aG9yLXJlY2lwZXMtb3V0Y29tZS5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjdmNTVlZmE2MTgzMGQ1YzE3NjNhYzQ2ODdkYjgzMTEzNmYwMzc4ZmU5MzkyN2I0OTBmYzU0MGQxYjM0N2RjMjMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj0xMnxvd25lcjEyLXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1NTi1zdWJzZXQtcmVzdWx0LTIwMjYxMDE4fHNoYTI1Nj03ZjU1ZWZhNjE4MzBkNWMxNzYzYWM0Njg3ZGI4MzExMzZmMDM3OGZlOTM5MjdiNDkwZmM1NDBkMWIzNDdkYzIzIiwKICAgICAgInN0YXR1cyI6ICJQQVJUSUFMX1JFU1VMVF9SRUNPUkRFRF9QT1JURk9MSU9fQUNUSVZFX1VOUkVDT05DSUxFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogMjcsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMjA4OTM3LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJPbmx5IE1OIHN1YnNldCBpcyB0ZXJtaW5hbDsgdGVuIGV4cGxpY2l0IGluZ3JlZGllbnQvcHJlcGFyYXRpb24gcGFnZXMgYW5kMTcgcGFydGlhbGx5IHF1YWxpZmllZCBzb3VyY2UgcGFnZXMuIE1hbGkgY2hhcHRlciBHRVQgdW5kZXJ3YXkgYW5kIE15YW5tYXIgcHJlcGFyYXRpb24gb25nb2luZyBpbiB0aGlzIHJlcG9ydC4gRG8gbm90IGR1cGxpY2F0ZSBvciB0cmVhdCBwb3J0Zm9saW8gY29tcGxldGUuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMTMsCiAgICAgICJzZXF1ZW5jZSI6IG51bGwsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIxMy1yZWNpcGVzLWFmdGVyODk0Mi1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGYxLTM4NWItNzA4MS05YjhjLTE1MDlhOGVkZmYxOCIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZi0yNjI0LTcwNTYtYjhiYi0zY2RlYjU4OTEyNTUiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIxMy1yZWNpcGVzLWFmdGVyODk0Mi9yZWNpcGUtaW5ncmVkaWVudC1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogImFmYjg2ZmFlNDg4ZmExNGIzODVjZjI0YTE3NDE5OWEyZDcyN2I5MjllNDZjNzliNGE5MDdhM2IyYzZmYmEwODAiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj0xM3x3b3JrZXIxMy1yZWNpcGVzLWFmdGVyODk0Mi1yZXN1bHR8c2hhMjU2PWFmYjg2ZmFlNDg4ZmExNGIzODVjZjI0YTE3NDE5OWEyZDcyN2I5MjllNDZjNzliNGE5MDdhM2IyYzZmYmEwODAiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogNiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA5MjQ0MjA1LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJPcmlnaW5hbCBsYW5ndWFnZSwgc291cmNlLXVzZSwgYXR0cmlidXRpb24sIGN1c3RvZHksIHR5cGUsIHJpZ2h0cyBhbmQgY292ZXJhZ2UgbGltaXRhdGlvbnMgcmV0YWluZWQ7IG5vIHJlY2lwZS1yZWNvcmQgb3IgY291bnRyeS1jb21wbGV0aW9uIGFjY2VwdGFuY2UuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMTQsCiAgICAgICJzZXF1ZW5jZSI6IDkxNDgsCiAgICAgICJldmVudF9pZCI6ICJXMTQtcmVjaXBlLWluZ3JlZGllbnQtcmVmaWxsLWFmdGVyODk0Mi1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGYxLTZlMjgtN2JhMS04ZDg1LTg1YjM5ZTNhZWFlMSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZS1kMjBlLTc3ZGEtOThjMi0yMzdhZDY5YjA5NDgiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTE0L1JFQ0lQRS1SRUZJTEwtODk0Mi0yMDI2MTAxOC9yZWNpcGUtaW5ncmVkaWVudC1zb3VyY2UtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICIyNjA0ZTczOTRkMjRlMTk1ZmQ4NmIyZDc1YTAzOTA2YWVjZjY5OTQ1YmU2MWZmZjc2ODg0YWQ2OGE1Zjc3NzhiIgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9MTR8VzE0LXJlY2lwZS1pbmdyZWRpZW50LXJlZmlsbC1hZnRlcjg5NDItcmVzdWx0fHNoYTI1Nj0yNjA0ZTczOTRkMjRlMTk1ZmQ4NmIyZDc1YTAzOTA2YWVjZjY5OTQ1YmU2MWZmZjc2ODg0YWQ2OGE1Zjc3NzhiIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDgsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMzM0NjU3MiwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiQ2FtYnJpZGdlIFRyaXN0YW4gaGlzdG9yaWNhbCBwYXBlciBpcyBwcml2YXRlIHJlc2VhcmNoIG9ubHksIG5vIHRoaXJkLXBhcnR5IHJhdyBzaGFyaW5nIG9yIHByb2R1Y3QvZGF0YWJhc2UgdXNlOyBtZXRhZGF0YSBhbmQgY29udHJhY3Qgb25seSB0bzU3LiBIaXN0b3JpY2FsIHNhbXBsZSBpcyBub3QgY3VycmVudCBTSC9Bc2NlbnNpb24gY292ZXJhZ2UuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMTYsCiAgICAgICJzZXF1ZW5jZSI6IDkyOTIsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIxNi1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzhmMi0wNjU3LTdkNjAtYmU5ZS1hMGUxMDBkNjhiZmQiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjAyLWU4MmEtNzU3OC1hOWM4LTM5OTAyNDMyNGI4NyIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDMtM2Q5YS03MjBhLTg4MjMtNjY1YmQ2ZjlmNTJhIiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvLmNvZGV4L3Zpc3VhbGl6YXRpb25zLzIwMjYvMTAvMTQvMDFhMTM4ZjItMDY1Ny03ZDYwLWJlOWUtYTBlMTAwZDY4YmZkL3JlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi9iYXRjaC1yZXN1bHQuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICI0ZWUzMDhjNTEzNmVhYzJmZmI5NDRmZWM5NmYwMmY5N2E5MDljNTY4OTg1YjE0ODhiNzMxM2FiOTEwYWJkNGM1IgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9MTZ8d29ya2VyMTYtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9NGVlMzA4YzUxMzZlYWMyZmZiOTQ0ZmVjOTZmMDJmOTdhOTA5YzU2ODk4NWIxNDg4YjczMTNhYjkxMGFiZDRjNSIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA0LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDI1OTQwNjgsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIlNVU1RMSVZFUyBtaXhlZC1jb3VudHJ5IFBERiBjb3VudHMgb25jZTsgb25seSBwYWdlNiBleHBsaWNpdGx5IEJlbmluLiBCSSBubyBuZXcgZ2VudWluZSByZWNpcGUgYm9keS4gT2NjdXJyZW5jZXMgYXJlIG5vdCBjYW5vbmljYWwgcmVjaXBlcy4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiAyMiwKICAgICAgInNlcXVlbmNlIjogbnVsbCwKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjIyLXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGZhLTFkMTUtNzcwMS05NGExLTM5YmRmMTlmZmIyMiIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDItZTgyYS03NTc4LWE5YzgtMzk5MDI0MzI0Yjg3IiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMy1jMDk4LTcxYTMtODExZi00Njc5M2FjMjc2ODkiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIyMi1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDIvbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICIxMzAzMjNhNmEwZjM0MDViMDQ5MTM1OGQ0MzJkNGY3NTY0YjdiMWZlN2M4YjU2ZjdlNzk3MGM0ZTQxMDY2MGQ5IgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9MjJ8d29ya2VyMjItcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9MTMwMzIzYTZhMGYzNDA1YjA0OTEzNThkNDMyZDRmNzU2NGI3YjFmZTdjOGI1NmY3ZTc5NzBjNGU0MTA2NjBkOSIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA4LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDE5ODA5NTI0LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJGaW5hbCBpbmNsdWRlcyBhbHJlYWR5IGNoZWNrZWQgc3Vic2V0OTEyMjoyb3JpZ2luYWxzLzE1LDUxMCwxNDEgQiwgY2hlY2tlZCBhczkzMTYuIEF0IG1vc3Q2IG5ld2x5IGFkZGl0aXZlIHVzZWZ1bCBvcmlnaW5hbHMvNCwyOTksMzgzIEIgYmVmb3JlIGV4YWN0IGRlZHVwLjExNywyMzAgQiBzdXBwb3J0aW5nIG1ldGFkYXRhIHJlbWFpbnMgc2VwYXJhdGUuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMjYsCiAgICAgICJzZXF1ZW5jZSI6IDkyMzgsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIyNi1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzhmZS1mZDYyLTdhNjEtODlhZC00NjgwOGQ3ZGEzMzgiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWZlLTlkZTgtNzA3Zi04MjIwLTI4OTE5ZWZjNjdlYyIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDAtMmZlOC03MDViLThkZjItZDMwMTYyZTM2NWNmIiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTMvdGFzay0zL3JlcG9ydHMvY291bnRyeTI0OS1maXhlZDY0LXByaW9yaXR5L2RlbGl2ZXJhYmxlcy9vd25lci0yNi9yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItMjAyNjEwMTgvcmVzdWx0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiZDk0Yjg0MDJlYzU4NzY3NDMyZWFlZTI2MjAxN2ZlZTJjOWEzMDc0YzcwMzEwNTkxYWY2NDY0ZDhlZjY3ZmQzYSIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTI2L3JlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi0yMDI2MTAxOC92YWxpZGF0aW9uLXJlY2VpcHQuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogIjU4MjQ5ZDY0ZGNlNDU0NTc3YzZiYmI5ZGY4OWM1NjAxZmMyMTA3ODcxMGUwZjFhYWEzNzdiNWI3NWM5ZWEwYzciCiAgICAgICAgfQogICAgICBdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9MjZ8d29ya2VyMjYtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9ZDk0Yjg0MDJlYzU4NzY3NDMyZWFlZTI2MjAxN2ZlZTJjOWEzMDc0YzcwMzEwNTkxYWY2NDY0ZDhlZjY3ZmQzYSIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA5LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDI4MTI1OTc4LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJERSBCWmZFIG9yaWdpbmFsIGNvcHk6bm8sIG5vIGV4dHJhY3Rpb24uIEJDIHJldGFpbmVkIHBhcnRpYWwzMyw1MzgsMjY2IEI7IGFjdHVhbCByZWFkMzMsNTU0LDQzMyBCIGluY2x1ZGVzMTYsMTY3IEIgdW53cml0dGVuLiBaZXJvIHdob2xlLW9yaWdpbmFsIGNyZWRpdCBmb3IgcGFydGlhbDsgbm8gcmV0cnkvcmVzdW1lLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDI3LAogICAgICAic2VxdWVuY2UiOiBudWxsLAogICAgICAiZXZlbnRfaWQiOiAid29ya2VyMjctcmVjaXBlODk0Mi1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOGZmLTgxZmMtN2ZiMC1hN2Y5LTQ1MzUwMTRlMjg2OSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZi0wMmFlLTc2YzAtOTAwNC0yOTZhMzA5OWQ0YjgiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIyNy1yZWNpcGU4OTQyL3JlY2lwZS1pbmdyZWRpZW50LW1hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiODg1YzFhZWUwZGU2YTZlYjNjZDY3YmYwYzFjMDE4MmI4OGIwZDBhNDhkZWI2ZTQ5MGVmNTZhYWVmMGY3NmIzYyIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTI3fHdvcmtlcjI3LXJlY2lwZTg5NDItcmVzdWx0fHNoYTI1Nj04ODVjMWFlZTBkZTZhNmViM2NkNjdiZjBjMWMwMTgyYjg4YjBkMGE0OGRlYjZlNDkwZWY1NmFhZWYwZjc2YjNjIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDgsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMTMzMDQ5NzI0LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJPcmlnaW5hbCBsYW5ndWFnZSwgc291cmNlLXVzZSwgYXR0cmlidXRpb24sIGN1c3RvZHksIHR5cGUsIHJpZ2h0cyBhbmQgY292ZXJhZ2UgbGltaXRhdGlvbnMgcmV0YWluZWQ7IG5vIHJlY2lwZS1yZWNvcmQgb3IgY291bnRyeS1jb21wbGV0aW9uIGFjY2VwdGFuY2UuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMjgsCiAgICAgICJzZXF1ZW5jZSI6IDkzNTcsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIyOC1zZWxlY3RlZC1yZWNpcGUtdHJhbnNmZXItcmVzdWx0LTIwMjYxMDE4IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzhmZi1jNDFkLTc2NDAtODQ4MC1lZWU4MDdhMTBjNDciLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjA1LTdlYjAtNzU5Mi05YzVhLWUyMzkzNGIyZDlkYyIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMGEtMDc2Mi03NzE3LWFjN2ItODkzYTMwZjEwYTZhIiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyMjgtc2VsZWN0ZWQtcmVjaXBlLXRyYW5zZmVyL3RyYW5zZmVyLXJlc3VsdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjVhMDY2Y2IyNGFmODM4Mjg0N2QyODQ1ZTNlMjI0MzVlMTY5ZjE0MDAwOTJiZWFkZDM2OWEzNGRmNWRmMWJhYTMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyMjgtc2VsZWN0ZWQtcmVjaXBlLXRyYW5zZmVyL3RyYW5zZmVyLW1hbmlmZXN0Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICIwYWU3MzRkMGUwZTc2N2E4NDZiZTYxZWQ0NWM0ZDM3OTgzZWRlYzQwMmQ0YmQ4NDExNzNiZGMzZjk0OTFkYmUyIgogICAgICAgIH0KICAgICAgXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTI4fHdvcmtlcjI4LXNlbGVjdGVkLXJlY2lwZS10cmFuc2Zlci1yZXN1bHQtMjAyNjEwMTh8c2hhMjU2PTVhMDY2Y2IyNGFmODM4Mjg0N2QyODQ1ZTNlMjI0MzVlMTY5ZjE0MDAwOTJiZWFkZDM2OWEzNGRmNWRmMWJhYTMiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogOCwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiAxODY5ODIwNywKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiOCB3aG9sZSBFRSBQREZzLzExMyBwaHlzaWNhbHBhZ2VzOyBwcmV2aW91c2x5IHJldGFpbmVkMTEgUERGcyByZXVzZWQuIFByZXNlcnZlIGJsb2NrZWQ5MzA0IGFuZCBmbG9vci1pbmNsdXNpdmUgY29ycmVjdGlvbjkzNDEuIFByZXBhcmF0aW9uOTEzOSBhbmQgdHJhbnNmZXI5MzU3IGFyZSBub3QgYWRkaXRpdmUgY29waWVzLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDMxLAogICAgICAic2VxdWVuY2UiOiA5MjgwLAogICAgICAiZXZlbnRfaWQiOiAid29ya2VyMzEtcmVjaXBlLWluZ3JlZGllbnQtcmVmaWxsODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOTA1LWNlZTYtN2MwMS1iMmVkLTg4NTVhYTgwYzU4NCIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDEtNzQ3My03NjM3LTgxYTgtNDNiNjQ0ZTAwYzNhIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMS03YjUxLTcxMzgtOWYzYS1mMjgyMmFiM2U1MWMiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIzMS1yZWNpcGUtaW5ncmVkaWVudC1yZWZpbGw4OTQyL3Jlc3VsdC1yZWNlaXB0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiMmU0NjUwYTE1ZTFhNzQwMDJlYmM5OTkyOGFkNjA1OGRhMzI3NzUzZjBhZGVkZTA3ZDIyMjIzM2E5OTk2ZDFlNSIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIzMS1yZWNpcGUtaW5ncmVkaWVudC1yZWZpbGw4OTQyL2JhdGNoLW1hbmlmZXN0Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICI4M2RjMmNmMDY2N2U0MzVlODQ1MWEzZWRiMjNkNDIwNjc1YzY0Zjk0ZTI4OWQ2MGE3ZWI2Mjg0MjNkZDllMzBiIgogICAgICAgIH0sCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9taWdyYXRpb24tMjAyNjEwMTgvY291bnRyeS1yZWNpcGUtaW5ncmVkaWVudC1zdWJzdGFudGlhbC1yZWZpbGwtYWZ0ZXI4OTQyLmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICI4ZmM5YWEyYWQyYmQ5NGNhN2ZiYzA0MDY4M2Y3YmJkYjU2OTQ1MWM5M2E2MmRlZWZmOGRlOTFlN2I2Yjc0NGQ3IgogICAgICAgIH0KICAgICAgXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTMxfHdvcmtlcjMxLXJlY2lwZS1pbmdyZWRpZW50LXJlZmlsbDg5NDItcmVzdWx0LTIwMjYxMDE4fHNoYTI1Nj0yZTQ2NTBhMTVlMWE3NDAwMmViYzk5OTI4YWQ2MDU4ZGEzMjc3NTNmMGFkZWRlMDdkMjIyMjMzYTk5OTZkMWU1IiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDE0LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDkxNjc0MjgsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIjE0IGVsaWdpYmxlIG9yaWdpbmFscyByZW1haW4gcGVuZGluZyBleGFjdCBjaGVja3MuIFJlc3RyaWN0ZWQgSUNCRjIsMTg3LDI0NiBCIHBsdXMgZGVyaXZhdGl2ZSBoYXZlIHplcm8gdXNhYmxlIGNyZWRpdC4gcGRmdG90ZXh0NXBhZ2VzIGFmdGVyIGNvcHk6bm8gd2FzIGEgc291cmNlLXVzZSBnYXRlIGZhaWx1cmUsIG5vdCBwZXJtaXNzaW9uLiBNZXRhZGF0YSBob2xkIHByb3BhZ2F0aW9uIGFscmVhZHkgcmVjb3JkZWQ5MzM3OyBkbyBub3Qgb3Blbi9zdGF0L2hhc2ggdGhlIHJlc3RyaWN0ZWQgb3JpZ2luYWwgb3IgZGVyaXZhdGl2ZS4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiAzNCwKICAgICAgInNlcXVlbmNlIjogOTE1OCwKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjM0LXJlY2lwZS1pbmdyZWRpZW50ODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOTk3LTk0N2QtN2NlMS1iYjZhLWE2YzFkYzlkOGFhMyIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmItZGNjZi03MzlhLTk4NzQtYTc2NjE2OWMyNzZiIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZS0xMzFmLTc0NDItODZhNC1kMzBlNDJjM2VjZTEiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIzNC1yZWNpcGUtaW5ncmVkaWVudDg5NDIvZmluYWwtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICJhNDdkNDMzNDZlNzg2M2M2MTdiMmIwZTQzN2JhNzcyNTMzZDExMTk1YmU4MjFiNzNhZTE5OGMwNWY1ZmZmMWU4IgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9MzR8d29ya2VyMzQtcmVjaXBlLWluZ3JlZGllbnQ4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9YTQ3ZDQzMzQ2ZTc4NjNjNjE3YjJiMGU0MzdiYTc3MjUzM2QxMTE5NWJlODIxYjczYWUxOThjMDVmNWZmZjFlOCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAxMSwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiAyOTc4OTYwNCwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiMTEgc291cmNlLWNvbnRlbnQgb3JpZ2luYWxzID05IHJlY2lwZSBvYmplY3RzKzIgbGltaXRlZCBhbmFseXRpY2FsIHN0dWRpZXM7NTUsMzU1IEIgY2l0YXRpb24vYWJzdHJhY3QgbWV0YWRhdGEgZXhjbHVkZWQuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMzUsCiAgICAgICJzZXF1ZW5jZSI6IDkxOTEsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXIzNS1yZWNpcGU4OTQyLXJlc3VsdC0yMDI2MTAxOCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5OTgtNzBlNy03YTcxLTgwNjctMDQwZjk1Mzg3OWVlIiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmYi1kY2NmLTczOWEtOTg3NC1hNzY2MTY5YzI3NmIiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZlLTZhNGQtNzRmMS04YjkwLWJjYWFhMWUwODRhNyIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItMzUvTS1SRUNJUEUtSU5HUkVESUVOVC04OTQyLTIwMjYxMDE4L3JlY2lwZS1pbmdyZWRpZW50LXJlc3VsdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjg0MmY2NjI4MWQ0ODUwNmQ5MjM4NDE0NWJmMDRhZjg3YjVhNzUwZjllODQwZTg4MzIwOTA4YmYxYjU1MmFjYjYiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj0zNXx3b3JrZXIzNS1yZWNpcGU4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9ODQyZjY2MjgxZDQ4NTA2ZDkyMzg0MTQ1YmYwNGFmODdiNWE3NTBmOWU4NDBlODgzMjA5MDhiZjFiNTUyYWNiNiIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA1LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IG51bGwsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIjcgcmV0YWluZWRmaWxlcy8zMCw5NTEsMDY3IEIgaW5jbHVkZTIgbWV0YWRhdGEgSFRNTDs1IHNvdXJjZS1jb250ZW50IGZpbGVzLiBVc2VmdWwtb25seSBieXRlcyB1bnNwZWNpZmllZC4gV0ZQIHJlZ2lvbmFsIGNvb2tib29rIG9uY2UsIG5vdCBwZXItY291bnRyeS4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiAzNywKICAgICAgInNlcXVlbmNlIjogOTI4OCwKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjM3LXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOTlhLTA3ZGItNzgxMC04NjEyLWQ2MzcyMDQyYzBmZSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDItZTgyYS03NTc4LWE5YzgtMzk5MDI0MzI0Yjg3IiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMy0wYjU1LTczMTgtOTMyZS0yNjJiZjE2MmJkMDIiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTM3L3JlY2lwZS1pbmdyZWRpZW50LXJlZmlsbC1hZnRlcjg5NDIvcmVzdWx0LW1hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiNmRhYTQ0MjM3OTFjMGM5MGNjMDE3ZjY1ZTBmOGVlOTU3MGMzYjA2YmUwMTFiZGI1N2IxYmE4NWFlN2I3ODQ3NiIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTM3fHdvcmtlcjM3LXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1yZXN1bHR8c2hhMjU2PTZkYWE0NDIzNzkxYzBjOTBjYzAxN2Y2NWUwZjhlZTk1NzBjM2IwNmJlMDExYmRiNTdiMWJhODVhZTdiNzg0NzYiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogNSwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA2OTE3MjQ1NSwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiU0sgYXJjaGl2ZSBvbmUgb3JpZ2luYWw7MSwzNDYgUERGbWVtYmVycy8xLDM3MiBaSVBtZW1iZXJzIGFyZSBub3QgdmFsaWRhdGVkIHJlY2lwZSBjb3VudC4gT3duZXIwMiBSZWNpcGVzIGZvciBQZWFjZSBwcmV2aWV3IHJldXNlZCB3aXRoMCBuZXdjb3B5LiBBbGwgcmlnaHRzL2V4dGVudCBxdWFsaWZpY2F0aW9ucyByZXRhaW5lZC4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA0MCwKICAgICAgInNlcXVlbmNlIjogOTE4OSwKICAgICAgImV2ZW50X2lkIjogIlc0MC1yZWNpcGUtcmVmaWxsODk0Mi1tYXRlcmlhbC1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOTliLTU3OWMtNzIwMC1iNjc5LTBjNGRmOGNlNWFmYiIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZS1hZmQ5LTc2NzctYjExOC1hOWNhNzgyZTY0YjIiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXI0MC1yZWNpcGUtcmVmaWxsODk0Mi9iYXRjaC1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjg5M2Q4ZmY5M2YzODhiYWEwOTI3ZjU2OWI1ZDllYTgxZjc4NjYxOTUzMjY1ZWFiNWYyZmZhY2QzOWM2MWQ3YWMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj00MHxXNDAtcmVjaXBlLXJlZmlsbDg5NDItbWF0ZXJpYWwtcmVzdWx0fHNoYTI1Nj04OTNkOGZmOTNmMzg4YmFhMDkyN2Y1NjliNWQ5ZWE4MWY3ODY2MTk1MzI2NWVhYjVmMmZmYWNkMzljNjFkN2FjIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDMsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogNzgwMTU4OCwKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiT25lIG11bHRpbmF0aW9uYWwgSHVuZ2FyaWFuIGNvbGxlY3Rpb24gYW5kMiBIYWl0aSBhdXRob3J2YXJpYW50cy4gUHJvZ2FzIHJlcXVlc3QgYmVmb3JlIGRpc2NvdmVyeSBvZiBoaXN0b3JpY2FsIGhvbGQgcmVjb3JkZWQgYXMgZXhjZXB0aW9uOyB6ZXJvRm9vR0VUIGFuZCBubyBmdXJ0aGVyIGF0dGVtcHQuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNDIsCiAgICAgICJzZXF1ZW5jZSI6IDkzNDQsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXI0Mi1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzk5Yy05YjMyLTc0YTMtODY3ZS0xMWI3MGFkOTIyNmYiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjA1LTdlYjAtNzU5Mi05YzVhLWUyMzkzNGIyZDlkYyIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMGEtMGNmYi03M2M3LWIwYTEtYjk3ODY4NGUyMDI4IiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyNDItcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyL3NvdXJjZS1yZXN1bHQtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICI3ZDZiOGRkMWFhMDgyOGY0MjhjN2UzYTRjMGQxY2QwZjMzNzg3YmFhYWZiN2QxMGIwOTdiOTU4MDllY2MxNDM0IgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9NDJ8d29ya2VyNDItcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9N2Q2YjhkZDFhYTA4MjhmNDI4YzdlM2E0YzBkMWNkMGYzMzc4N2JhYWFmYjdkMTBiMDk3Yjk1ODA5ZWNjMTQzNCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAxNiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiAxMDIyOTE1MjQsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIjE2IFVOSVFVRSBvcmlnaW5hbHM6SU0xL0lOMS9JUTIvSU8xMi4xMyBJTyBwdWJsaXNoZXIgcGFnZXMgbGlua2VkMTIgdW5pcXVlUERGcy4gTW91Zi9NYXRvdWZ0d2Egc2FtZVVSTC9TSEE7IGV4dHJhNCw4NTYsNjcyIEIgYXJ0aWZhY3QgcmV0YWluZWQgYnV0IGV4Y2x1ZGVkLCBzZXBhcmF0ZSBNYXRvdWZ0d2EgdW5yZXNvbHZlZC4gU291cmNlLXN0YXR1cyBjbGFpbSBJRHMgcmF3LGNhbm9uaWNhbElEcyBudWxsLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDQ0LAogICAgICAic2VxdWVuY2UiOiA5MTg0LAogICAgICAiZXZlbnRfaWQiOiAid29ya2VyNDQtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXN1YnN0YW50aWFsLXJlc3VsdC0yMDI2MTAxOCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5OWUtMDhhYi03OTIxLTk4MGItYmNjZGExZDJkYjgwIiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmYi1kY2NmLTczOWEtOTg3NC1hNzY2MTY5YzI3NmIiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZkLWZlMWUtNzQ5Yi1hMmNmLTY4MTJlODAwNTUzNCIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItNDQvcmVjaXBlLXJlZmlsbC1hZnRlcjg5NDIvcmVjaXBlLWluZ3JlZGllbnQtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICI3NzZmMWZjZWVjZDZmMGNjODExYWIyNjA3NzQwNjZmMmQwODAxMGQzYzQwYWNjNmFiZTk3MWZhYjg5NTlmMWRmIgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9NDR8d29ya2VyNDQtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXN1YnN0YW50aWFsLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9Nzc2ZjFmY2VlY2Q2ZjBjYzgxMWFiMjYwNzc0MDY2ZjJkMDgwMTBkM2M0MGFjYzZhYmU5NzFmYWI4OTU5ZjFkZiIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA0LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDE4ODY5MTMzLAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJOQSBpZGVudGl0eS9wcmVwYXJhdGlvbiByZXBvcnQgaXMgbm90IGEgY29tcGxldGVkIG51dHJpZW50IHRhYmxlLiBPd25lcjU1IE5BIGNvb2tib29rIHJldXNlZCwgbm8gbmV3Y29weS4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA0NSwKICAgICAgInNlcXVlbmNlIjogOTI0NywKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjQ1LXJlY2lwZS1yZWZpbGw4OTQyLXJlc3VsdC0yMDI2MTAxOCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5YTEtZTkxNi03ZjgxLThmZDItNWE3ZWFhYzNhMWRlIiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjAwLWZmMDAtNzc3ZC1hYmI2LTM4MDJjNWM2OWRmOSIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjQ1LXJlY2lwZS1yZWZpbGw4OTQyL21hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiNjVkOWNiODZhYTM2ZTdmMmI3OWY3M2E3YmY4YWY1YzhiY2QyOTQ1NzIyOTBmMTZhNjY1Y2VjOTJkMTYwMmY1ZCIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTQ1fHdvcmtlcjQ1LXJlY2lwZS1yZWZpbGw4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9NjVkOWNiODZhYTM2ZTdmMmI3OWY3M2E3YmY4YWY1YzhiY2QyOTQ1NzIyOTBmMTZhNjY1Y2VjOTJkMTYwMmY1ZCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAxMywKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA0NzAzNDUwLAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJNYXTDrXMvTk9SQSBzaGFyZWQgTm9ydGhBdGxhbnRpYyByZXBvcnQgaXMgb25lIHJlZmVyZW5jZSwgbm90IMONU0dFTS9uYXRpb25hbCB0YWJsZTsgb3JpZ2luYWwgY291bnRyeSBhbmQgdHlwZSBxdWFsaWZpY2F0aW9ucyByZXRhaW5lZC4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA0NiwKICAgICAgInNlcXVlbmNlIjogOTE5MywKICAgICAgImV2ZW50X2lkIjogIndvcmtlcjQ2LXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOWEyLTU0ZGEtNzA2MC1hMWU1LWIxZWRmY2Y4OGJkNyIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZS1hNGQxLTcxNTctYmQ1OS1jMTcyYjVhNWMwMDEiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC9vd25lcjQ2LXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi9yZWNpcGUtaW5ncmVkaWVudC1yZXN1bHQuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICI5YzM1M2YxMmM5NDRiZWFmNjFlM2M4OWFjNzQ1N2M2MzRjZmQ5NTM5ZjIxOGQyNzZiOTRmM2QwYjg4ZWE1YzYwIgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFsKICAgICAgICB7CiAgICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL21pZ3JhdGlvbi0yMDI2MTAxOC9jb3VudHJ5LXJlY2lwZS1pbmdyZWRpZW50LXN1YnN0YW50aWFsLXJlZmlsbC1hZnRlcjg5NDIuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogIjhmYzlhYTJhZDJiZDk0Y2E3ZmJjMDQwNjgzZjdiYmRiNTY5NDUxYzkzYTYyZGVlZmY4ZGU5MWU3YjZiNzQ0ZDciCiAgICAgICAgfQogICAgICBdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9NDZ8d29ya2VyNDYtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9OWMzNTNmMTJjOTQ0YmVhZjYxZTNjODlhYzc0NTdjNjM0Y2ZkOTUzOWYyMThkMjc2Yjk0ZjNkMGI4OGVhNWM2MCIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAzLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDY3Mjg4Nzg0LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJBU0VBTiByZWdpb25hbCB0YWJsZSBhbmQgV2l0dGVuYmVyZyBtdWx0aW5hdGlvbmFsIGNvb2tib29rIGNvdW50IG9uY2UgZWFjaC4gVVNEQSBGTlMgY29va2Jvb2sgZGlzdGluY3QgZnJvbSByZXRhaW5lZCBVU0RBIEZEQyBhcmNoaXZlLiBObyBjb3VudHJ5IGZhbm91dCBvciByZWFjcXVpc2l0aW9uLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDQ4LAogICAgICAic2VxdWVuY2UiOiA5MTgyLAogICAgICAiZXZlbnRfaWQiOiAid29ya2VyNDgtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5YTMtMzhhYy03ZDQwLWE4ZmMtZjYxMWY0NzY1MTFkIiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmYi1kY2NmLTczOWEtOTg3NC1hNzY2MTY5YzI3NmIiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZkLWRiODQtNzAwMy05OTE4LWVhMTQ0ZDQ3ZmIzMyIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjQ4LXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi9zb3VyY2UtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICJhNDYyNzg4MTNlMjIwYjEwZjY3YjgzZjY0ZGNiMTM5NjNjNWY0ZDNhMmZmODNiMWJhZTE1ZWY5OTE3NjY3ZmFlIgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9NDh8d29ya2VyNDgtcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9YTQ2Mjc4ODEzZTIyMGIxMGY2N2I4M2Y2NGRjYjEzOTYzYzVmNGQzYTJmZjgzYjFiYWUxNWVmOTkxNzY2N2ZhZSIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAyLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDYyODgxODYsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIkVDIGltYWdlLW9ubHkgcmVjaXBlIHRoZXNpcyBwcml2YXRlIHJlc2VhcmNoIHJldGVudGlvbjsgbm8gT0NSL3RyYW5zY3JpcHRpb24uIFZVIGlzIHByZXNlcnZhdGlvbiBtYW51YWwsIG5vdCBjb21wbGV0ZSBjb29rYm9vay9uYXRpb25hbGNvbXBvc2l0aW9uLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDUxLAogICAgICAic2VxdWVuY2UiOiA5MzE3LAogICAgICAiZXZlbnRfaWQiOiAib3duZXI1MS1yZWNpcGUtaW5ncmVkaWVudC1yZWZpbGwtODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOWE2LTQyZjktN2RlMi1iYjI1LWMxZGNkN2VkNGI3YSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDMtZTY5Ni03N2RkLWE5ZjEtNmQ5MTU1NDY0ZTZhIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMy1lZDUyLTc1Y2MtOTk0NC01YWFlYTkyNTVkNDMiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTUxL1JFQ0lQRS1JTkdSRURJRU5ULVJFRklMTC04OTQyL2ZpbmFsLXNvdXJjZS1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjUzNmJmYzdhMmM0MTA4MWJhYmRjZmYxNmFhZDRiNjc3YTNlMzI0YzQwYTdjYWMzYWE0OTM5ZGY0ODk1YTU2ZjMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj01MXxvd25lcjUxLXJlY2lwZS1pbmdyZWRpZW50LXJlZmlsbC04OTQyLXJlc3VsdC0yMDI2MTAxOHxzaGEyNTY9NTM2YmZjN2EyYzQxMDgxYmFiZGNmZjE2YWFkNGI2NzdhM2UzMjRjNDBhN2NhYzNhYTQ5MzlkZjQ4OTVhNTZmMyIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiA3LAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IG51bGwsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIlNpeCByZWNpcGUgc291cmNlZmlsZXMgcGx1c01XIGFuYWx5dGljYWwgSFRNTCB3aXRoIFVTLXNvdXJjZWQgc2FtcGxlIGxpbWl0YXRpb24uIFR3byBzdXBwb3J0IGJvZGllcyBzZXBhcmF0ZTtQTUMgUE9XIGNoYWxsZW5nZSBleGNsdWRlZC4xMjEsMTExLDU2MyBCIGlzIHRyYW5zcG9ydC9hY2NvdW50aW5nIHRvdGFsLCBub3QgYSB2ZXJpZmllZCB1c2VmdWwtc291cmNlIGJ5dGUgdG90YWwuIEluaXRpYWwgZnVsbCBoYW5kb3ZlciBmYWlsZWQgdHVybi1hbHJlYWR5LWFjdGl2ZSBvbmNlIGFuZCBtdXN0IG5vdCBiZSByZXNlbnQuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNTIsCiAgICAgICJzZXF1ZW5jZSI6IDkyMDQsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXI1Mi1yZWNpcGUtaW5ncmVkaWVudC1yZWZpbGwtODk0Mi1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOWE2LWQzNGItNzA4My1iMWMxLTEzYTk3Mzc0Zjk2OCIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZi0xMDBkLTczMzctODBiNy1lODdjZjRhNjQxM2UiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXI1Mi1yZWNpcGUtaW5ncmVkaWVudC1yZWZpbGwtODk0Mi9SRVNVTFQuanNvbiIsCiAgICAgICAgInNoYTI1NiI6ICIxOTM2OGQ4YjQ3NTFkMTAyZDI2Njk2MTk1MGFiZjJmMmVmZWVkNTMzMGM2ZDNiZjI4ZjM5NWRhNGQ1ZDYyYzI3IgogICAgICB9LAogICAgICAib3RoZXJfZXhwbGljaXRfbWV0YWRhdGFfcGlucyI6IFtdLAogICAgICAiZGVkdXBfa2V5IjogIkNPVU5UUlktUVVFVUV8b3duZXI9NTJ8d29ya2VyNTItcmVjaXBlLWluZ3JlZGllbnQtcmVmaWxsLTg5NDItcmVzdWx0LTIwMjYxMDE4fHNoYTI1Nj0xOTM2OGQ4YjQ3NTFkMTAyZDI2Njk2MTk1MGFiZjJmMmVmZWVkNTMzMGM2ZDNiZjI4ZjM5NWRhNGQ1ZDYyYzI3IiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDQsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMjkwNDM2NDUsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIjQgcGh5c2ljYWwgb3JpZ2luYWxzLzI5LDA0Myw2NDUgQiBpbmNsdWRlcyByZXN0cmljdGVkIFVOQU00LDYxNCwxMTYgQiBjb3B5Om5vL3ByaW50Om5vL3JlcHJvZHVjdGlvbiByZXN0cmljdGlvbi4gUHJlY2xhc3NpZmljYXRpb24gdGV4dCBwcm9iZSBmcm96ZW4vcXVhcmFudGluZWQ7emVybyBhbmFseXRpY2FsLXVzZSBjcmVkaXQuIFJTNiwyOTEsNDU2IEIgcGFydGlhbCBoYXMgbm8gRU9GIGFuZCB6ZXJvIHdob2xlLW9yaWdpbmFsIGNyZWRpdC4gT3duZXIwNiBHSVogb3JpZ2luYWwgcmV1c2VkLiIKICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDUzLAogICAgICAic2VxdWVuY2UiOiA5MjQ2LAogICAgICAiZXZlbnRfaWQiOiAiVzUzLXJlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi1yZXN1bHQiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOWE3LWRlN2ItN2ZiMC05MjU5LTQzZDlmZjdjNmQ2YSIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMS0yNThjLTcyYzEtYTIzMC02YTQwMjE5OGY4MzkiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTUzL1JFQ0lQRS1JTkdSRURJRU5ULVJFRklMTC1BRlRFUjg5NDIvYmF0Y2gtcmVzdWx0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiMzljOWVhNjAxN2RjOTE5ZjQ1NDg1MzBhZThkMzJhYjE5ZGFmYTIxNGI2N2RhYjFhOWZlZDA4M2E3NjIzZjE3ZCIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTUzfFc1My1yZWNpcGUtaW5ncmVkaWVudC1hZnRlcjg5NDItcmVzdWx0fHNoYTI1Nj0zOWM5ZWE2MDE3ZGM5MTlmNDU0ODUzMGFlOGQzMmFiMTlkYWZhMjE0YjY3ZGFiMWE5ZmVkMDgzYTc2MjNmMTdkIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDUsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMTI1NjA4MDMsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIkZvdXIgcmVjaXBlIG9yaWdpbmFscyBwbHVzIG9uZSBhbmFseXRpY2FsIGluZ3JlZGllbnQgb3JpZ2luYWwuIFB1Ymxpc2hlcjUwIExUIHJlY2lwZXMgbm90IGluZGVwZW5kZW50bHkgdmFsaWRhdGVkIG9yIG11bHRpcGxpZWQgYnkgbGFuZ3VhZ2UuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNTUsCiAgICAgICJzZXF1ZW5jZSI6IDkyNzEsCiAgICAgICJldmVudF9pZCI6IG51bGwsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5YTgtYWM3MC03NDkzLWE0ZjQtOWNmMzRiYjE2Y2U3IiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjAxLTFiZjQtNzRmOS05NjM4LWJhMGMxNWZhMTcwYiIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItNTUvcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLTIwMjYxMDE4L21hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiOWEwYWI4MzFhNWIyMWRlODEwMmZlZTFlNGI3NTIzN2MxOGU0OWQyNzYzZTI4YzMzOGM2ZDBlYTAwZGY5NzVjOSIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTU1L3JlY2lwZS1pbmdyZWRpZW50LWFmdGVyODk0Mi0yMDI2MTAxOC9zb3VyY2UtY29udHJhY3RzLWFuZC1jb3B5LWluZGV4Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICI2ZmE3MTZiMGIxMWIyMDVjNDZjOGQ2NjkxNjU2Y2QyNDlkNjA5NmFjY2MwOTdhNjI1ODM2YTRkNDEwZDM1NmViIgogICAgICAgIH0KICAgICAgXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTU1fHNlcXVlbmNlPTkyNzF8c2hhMjU2PTlhMGFiODMxYTViMjFkZTgxMDJmZWUxZTRiNzUyMzdjMThlNDlkMjc2M2UyOGMzMzhjNmQwZWEwMGRmOTc1YzkiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogNCwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiAxMTQ4MzQ4MywKICAgICAgInZlcmlmaWNhdGlvbiI6ICJSZWNvcmRlZCBHYXRld2F5IHJlcG9ydCBvbmx5OyBubyBwaHlzaWNhbCB2ZXJpZmljYXRpb24gb3IgbGVkZ2VyIGludGFrZSBieSBjbG91ZC4iLAogICAgICAicXVhbGlmaWNhdGlvbnMiOiAiRm91ciB1c2VmdWwgb3JpZ2luYWxzID0zIHJlY2lwZSBQREZzK01ZIGFuYWx5dGljYWwgSFRNTC4gVGhyZWUgc3VwcGxlbWVudCByZXNwb25zZXM1LDQ0OSBCIGFyZSBub3QgWExTWDt6ZXJvIHJhd3dvcmtib29rcy4gRXhhY3QgZXZlbnRJRCBub3Qgc3VwcGxpZWQsIHVzZSBzZXF1ZW5jZTkyNzErc291cmNlU0hBIHBlbmRpbmcgbGVkZ2VyIHJlc29sdXRpb24uIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNTgsCiAgICAgICJzZXF1ZW5jZSI6IDkzNDAsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXI1OC1yZWFkeS1mb2xsb3dvbi1SVS1QRy1yZXN1bHQtMjAyNjEwMTgiLAogICAgICAicHJvZHVjZXJfdGhyZWFkX2lkIjogIjAxYTEzOWFhLWYyYzItNzNiMC1iNDVmLWNiYmFmZTJlMzI2YyIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDQtZDBlNy03NDU0LWExODctZmE3YmQ4MmJjYTQwIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwNC1kN2JiLTc1NjItYTg0NS1kMjZjZTcwNzVhZGEiLAogICAgICAgICJ0cnVuY2F0ZWQiOiBmYWxzZQogICAgICB9LAogICAgICAicHJpbWFyeV9tZXRhZGF0YV9waW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTU4L3JlYWR5LWZvbGxvd29uLVJVLVBHLTIwMjYxMDE4L3Jlc3VsdC1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogIjM0NmY1YzJiYzk1MjJlZTYzZTM3MGE1NmFmZmQ1NTExYTEwY2FkZjZjODMyNTM4ODkyNDAzMGE4MzViNDA2YWMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj01OHx3b3JrZXI1OC1yZWFkeS1mb2xsb3dvbi1SVS1QRy1yZXN1bHQtMjAyNjEwMTh8c2hhMjU2PTM0NmY1YzJiYzk1MjJlZTYzZTM3MGE1NmFmZmQ1NTExYTEwY2FkZjZjODMyNTM4ODkyNDAzMGE4MzViNDA2YWMiLAogICAgICAic3RhdHVzIjogIlJFU1VMVF9SRUNPUkRFRF81N19JTlRBS0VfVU5WRVJJRklFRCIsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2NvdW50IjogMiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfYnl0ZXMiOiA1MzcyNzQ4LAogICAgICAidmVyaWZpY2F0aW9uIjogIlJlY29yZGVkIEdhdGV3YXkgcmVwb3J0IG9ubHk7IG5vIHBoeXNpY2FsIHZlcmlmaWNhdGlvbiBvciBsZWRnZXIgaW50YWtlIGJ5IGNsb3VkLiIsCiAgICAgICJxdWFsaWZpY2F0aW9ucyI6ICJSVTk3NCw1MzkgQiBmaWxlIGlzIG9ubHk0IHBhZ2VzOiBGT1VSX1BBR0VfUFVCTElTSEVSX0ZJTEVfVU5RVUFMSUZJRURfQ09NUE9TSVRJT05fQ09OVEVOVC4gTm8gZnVsbDE5My8xOTItcGFnZSBjb21wb3NpdGlvbiBib29rL3RhYmxlIGNyZWRpdC4gUEc0LDM5OCwyMDkgQiBhbmFseXRpY2FsIGFydGljbGUgaXMgbm90IG5hdGlvbmFsZGF0YXNldC4iCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA1OSwKICAgICAgInNlcXVlbmNlIjogOTM0NSwKICAgICAgImV2ZW50X2lkIjogIm93bmVyNTktcmVhZHktZm9sbG93b25zLXByaXZhdGUtb3JpZ2luYWxzLWZpbmFsLXJlc3VsdCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5YWItZGRmMy03NDcxLThlNzktNmMzMjdkMTljMmQ3IiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwNS03ZWIwLTc1OTItOWM1YS1lMjM5MzRiMmQ5ZGMiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjA2LWMzMjctNzRmNS1iMzMyLTc4ZWQ3ZmZkYWJlNCIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjU5LWNvdW50cnktb3JpZ2luYWwtZm9sbG93b24vcmVzdWx0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiNDY4MWI5MDQ1YTA2ZGZhMGQ0MGViOTJkYTA5OGExY2JiZjZiODFkY2ZkOWVkMWE4NzhiOTRlNDI1YmRkMjlmYiIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTU5fG93bmVyNTktcmVhZHktZm9sbG93b25zLXByaXZhdGUtb3JpZ2luYWxzLWZpbmFsLXJlc3VsdHxzaGEyNTY9NDY4MWI5MDQ1YTA2ZGZhMGQ0MGViOTJkYTA5OGExY2JiZjZiODFkY2ZkOWVkMWE4NzhiOTRlNDI1YmRkMjlmYiIsCiAgICAgICJzdGF0dXMiOiAiUkVTVUxUX1JFQ09SREVEXzU3X0lOVEFLRV9VTlZFUklGSUVEIiwKICAgICAgInJlcG9ydGVkX2NvbnRlbnRfb3JpZ2luYWxfY291bnQiOiAyLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9ieXRlcyI6IDcyNjgwNzMsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIkxWIHJlY2lwZS1iZWFyaW5nIG1hbnVhbDtMWSBhbmFseXRpY2FsIGJhc3Npc3NhIGFydGljbGUuIExZIGludGVybmFsIENDIEJZLU5DLU5EIG92ZXJyaWRlcyBwZXJtaXNzaXZlIEhUTUwgY2xhaW0gZm9yIGNvbnNlcnZhdGl2ZSBkb3duc3RyZWFtaG9sZC4gU291cmNlLXNwZWNpZmljIGhlbGQgcm91dGVzIGFuZCBlYXJsaWVyIGxvY2FsIHByZWZsaWdodCBzdG9wcyBwcmVzZXJ2ZWQuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNjIsCiAgICAgICJzZXF1ZW5jZSI6IDkxOTQsCiAgICAgICJldmVudF9pZCI6ICJ3b3JrZXI2Mi1yZWNpcGUtYWZ0ZXI4OTQyLXJlc3VsdC0yMDI2MTAxOCIsCiAgICAgICJwcm9kdWNlcl90aHJlYWRfaWQiOiAiMDFhMTM5YjctZTlkNy03MTYxLWEzZWYtNTFlNmU5NjU4NjZiIiwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZlLWMxOGEtNzc1Mi1iNjg2LWZiYmY1ODJlNTE2ZCIsCiAgICAgICAgInRydW5jYXRlZCI6IGZhbHNlCiAgICAgIH0sCiAgICAgICJwcmltYXJ5X21ldGFkYXRhX3BpbiI6IHsKICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItNjIvcmVjaXBlLWluZ3JlZGllbnQtYWZ0ZXI4OTQyLTIwMjYxMDE4L21hbmlmZXN0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiZDVmODgwMjRjODkwODQyMTc3NmZiNzc4NTg1ZTllNTY1MjljMmQwZWZmZmU4MjJkNTA2YjQyM2Q0MjdiNDVmYSIKICAgICAgfSwKICAgICAgIm90aGVyX2V4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbXSwKICAgICAgImRlZHVwX2tleSI6ICJDT1VOVFJZLVFVRVVFfG93bmVyPTYyfHdvcmtlcjYyLXJlY2lwZS1hZnRlcjg5NDItcmVzdWx0LTIwMjYxMDE4fHNoYTI1Nj1kNWY4ODAyNGM4OTA4NDIxNzc2ZmI3Nzg1ODVlOWU1NjUyOWMyZDBlZmZmZTgyMmQ1MDZiNDIzZDQyN2I0NWZhIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDgsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMTEzNzg0NzgsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIjggbmV3ID1aQTJib29rcytHUjZIVE1MLiBPTSBhbHJlYWR5aGVsZGJvb2tsZXQgcmV1c2VkO25vIG5ldyBhbmFseXRpY2Fsb3JpZ2luYWwuIgogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNjMsCiAgICAgICJzZXF1ZW5jZSI6IG51bGwsCiAgICAgICJldmVudF9pZCI6ICJXNjMtUkVBRFktRk9MTE9XT04tMjAyNjEwMTgtc2VsZWN0ZWQtcmVzdWx0IiwKICAgICAgInByb2R1Y2VyX3RocmVhZF9pZCI6ICIwMWExMzliOC02MTg2LTc2MzMtOWFjMi0xZWE1YmYzYzg2NmYiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjA1LTdlYjAtNzU5Mi05YzVhLWUyMzkzNGIyZDlkYyIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDYtZGI5Zi03MGFjLTlkYzMtODQwOTdhMjYzNjMyIiwKICAgICAgICAidHJ1bmNhdGVkIjogZmFsc2UKICAgICAgfSwKICAgICAgInByaW1hcnlfbWV0YWRhdGFfcGluIjogewogICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyNjMtcmVhZHktZm9sbG93b24tZGlzay1nYXRlL2ZvbGxvd29uLXJlc3VsdC1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic2hhMjU2IjogImQ3YzAyODk4ODRhYjA3YjFhMGMxMmQ2MjNlOTBiZGIyOTMwODY3YmFiOGYzODRlODg4NmNjNjVmMTRiNDc3NjMiCiAgICAgIH0sCiAgICAgICJvdGhlcl9leHBsaWNpdF9tZXRhZGF0YV9waW5zIjogW10sCiAgICAgICJkZWR1cF9rZXkiOiAiQ09VTlRSWS1RVUVVRXxvd25lcj02M3xXNjMtUkVBRFktRk9MTE9XT04tMjAyNjEwMTgtc2VsZWN0ZWQtcmVzdWx0fHNoYTI1Nj1kN2MwMjg5ODg0YWIwN2IxYTBjMTJkNjIzZTkwYmRiMjkzMDg2N2JhYjhmMzg0ZTg4ODZjYzY1ZjE0YjQ3NzYzIiwKICAgICAgInN0YXR1cyI6ICJSRVNVTFRfUkVDT1JERURfNTdfSU5UQUtFX1VOVkVSSUZJRUQiLAogICAgICAicmVwb3J0ZWRfY29udGVudF9vcmlnaW5hbF9jb3VudCI6IDEsCiAgICAgICJyZXBvcnRlZF9jb250ZW50X29yaWdpbmFsX2J5dGVzIjogMjYzMDE1MDIsCiAgICAgICJ2ZXJpZmljYXRpb24iOiAiUmVjb3JkZWQgR2F0ZXdheSByZXBvcnQgb25seTsgbm8gcGh5c2ljYWwgdmVyaWZpY2F0aW9uIG9yIGxlZGdlciBpbnRha2UgYnkgY2xvdWQuIiwKICAgICAgInF1YWxpZmljYXRpb25zIjogIkdXMjYsMzAxLDUwMiBCLzM3cGFnZXMgY29tcGxldGVkLiBUaHJlZSBQRSBvcmlnaW5hbHMgZWFjaCBjb25kaXRpb25hbEhFQUQ0MTYsIG5vIFJhbmdlLDBhbGxvY2F0aW9uL0dFVC9ib2R5Ynl0ZXMuIEV4YWN0IGNhdXNlIHVua25vd24sIG5vIHJldHJ5L2FsaWFzL3NvdXJjZS1yaWdodHMgaW5mZXJlbmNlOyBvbGQgY2FwYWNpdHktYmxvY2tlZCByZWNlaXB0cyBwcmVzZXJ2ZWQuIgogICAgfQogIF0sCiAgInNjb3BlIjogewogICAgIm1ldGhvZCI6ICJSZWFkIHJlY29yZGVkIGNsb3VkX3RocmVhZHMgR2F0ZXdheSBtZXNzYWdlcyBvbmx5OyBubyBuYXRpdmUgc2VuZHMsIG5vIGRpcmVjdCBGb28gYWNjZXNzLCBubyByYXctc291cmNlIHJlYWRzLCBubyByZXBvL2NvbmZpZyBjaGFuZ2VzLiIsCiAgICAibm90X3BoeXNpY2FsX3ZlcmlmaWNhdGlvbiI6IHRydWUsCiAgICAibm90X2xlZGdlcl9jb25zdW1wdGlvbiI6IHRydWUsCiAgICAibm9fbmV3X2Nvb3JkaW5hdG9yIjogdHJ1ZSwKICAgICJzb3VyY2VfY3V0IjogIkxhdGVzdCBHYXRld2F5IG1lc3NhZ2VzIGF0IGZhaWxlZCB0dXJuMDFhMTRmMDUtN2ViMC03NTkyLTljNWEtZTIzOTM0YjJkOWRjOyBubyBjbGFpbSBvZiBsaXZlIGhvc3QgcHJvY2VzcyBvciBxdWV1ZSBzdGF0ZS4iLAogICAgImZhaWx1cmUiOiB7CiAgICAgICJ0aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgInR1cm5faWQiOiAiMDFhMTRmMDUtN2ViMC03NTkyLTljNWEtZTIzOTM0YjJkOWRjIiwKICAgICAgInN0YXR1cyI6ICJmYWlsZWQiLAogICAgICAicmVhc29uIjogIlVzYWdlIGxpbWl0IgogICAgfSwKICAgICJkaXJlY3Rfd29ya2VyNTdfcmVjb3JkX3JlYWQiOiB7CiAgICAgICJzdGF0dXMiOiAidW5hdmFpbGFibGUiLAogICAgICAicmVhc29uIjogIlVuc3VwcG9ydGVkIHBvc3QtY3V0b3ZlciBwbGFjZW1lbnQgZm9ybWF0IHZlcnNpb24zIiwKICAgICAgInBoeXNpY2FsX2FjY2Vzc19hdHRlbXB0ZWQiOiBmYWxzZQogICAgfQogIH0sCiAgImxhdGVzdF9yZXBvcnRlZF9jaGVja2VkXzU3IjogewogICAgImNvdW50cnlfcmVmZXJlbmNlX29iamVjdHMiOiA2NTksCiAgICAiY291bnRyeV9yZWZlcmVuY2VfYnl0ZXMiOiAyNTA0NjEzMDY3LAogICAgImdsb2JhbF9maWxlcyI6IDI3LAogICAgImdsb2JhbF9ieXRlcyI6IDEwMDI2NzAzNjgsCiAgICAiZWxldmVuX3BhY2tldF9pbmNyZW1lbnQiOiB7CiAgICAgICJvYmplY3RzIjogNzYsCiAgICAgICJjb3JyZWN0ZWRfYnl0ZXMiOiAzMTE3NjU0MDAsCiAgICAgICJjb3VudHJ5X2J5dGVzIjogMjg2NDAyMDU4LAogICAgICAiZ2xvYmFsX2J5dGVzIjogMjUzNjMzNDIsCiAgICAgICJ3cm9uZ19tZXNzYWdlX2J5dGVzX3N1cGVyc2VkZWQiOiA0MTE4NjE0MTcKICAgIH0sCiAgICAic3VtbWFyeSI6IHsKICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC9jb3VudHJ5LWNvbGxlY3Rpb24taW52ZW50b3J5L3dvcmtlcjU3L2xhdGVyLW5leHQtZWxldmVuLXJlZmlsbC1wYWNrZXRzL2VsZXZlbi1wYWNrZXQtc3VtbWFyeS5qc29uIiwKICAgICAgInNoYTI1NiI6ICI5YzJkYTAyYzQ1MWUyMWQzOTdiODU0ZmNiZTk5YzExNDJlNDNmY2I1ZmQ4MDFkMDZhMWRlYWY5MGIyNjU0YmM1IgogICAgfSwKICAgICJsYXRlc3RfaW5kZXgiOiB7CiAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvY291bnRyeS1jb2xsZWN0aW9uLWludmVudG9yeS93b3JrZXI1Ny9sYXRlci1uZXh0LWVsZXZlbi1yZWZpbGwtcGFja2V0cy9vd25lci0yOS9jdXJyZW50MjQ5LXNvdXJjZS10eXBlLWluZGV4Lmpzb24iLAogICAgICAic2hhMjU2IjogIjVjNzg2ZTRiODM5NDNlZjk3NDRmMDM4M2MwNjViNzAwNTYxMmRiYjU2ZmIxNWQzMWE3YmM5MGM3YzUzYzk3MjciLAogICAgICAicGF0aF9iaW5kaW5nIjogIlNhbWUgcmVwb3J0ZWQgc3VtbWFyeSByb290IHBsdXMgbGl0ZXJhbCBuZXN0ZWQgb3duZXItMjkgcGF0aDsgaG9zdCBtdXN0IGNvbmZpcm0uIgogICAgfSwKICAgICJjaGVja2VkX2ludGFrZXMiOiBbCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MzE1LAogICAgICAgICJvd25lciI6IDQzCiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MzE2LAogICAgICAgICJvd25lciI6IDIyLAogICAgICAgICJzdWJzZXQiOiAiOTEyMiBzdWJzZXQxIG9ubHkiCiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MzE4LAogICAgICAgICJvd25lciI6IDQ5CiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MzIxLAogICAgICAgICJvd25lciI6IDcKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkzMjMsCiAgICAgICAgIm93bmVyIjogMzYKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkzMjQsCiAgICAgICAgIm93bmVyIjogNjAKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkzMjYsCiAgICAgICAgIm93bmVyIjogMzkKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkzMjgsCiAgICAgICAgIm93bmVyIjogMjQKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkzMjksCiAgICAgICAgIm93bmVyIjogNgogICAgICB9LAogICAgICB7CiAgICAgICAgInNlcXVlbmNlIjogOTMzMCwKICAgICAgICAib3duZXIiOiA5CiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MzMxLAogICAgICAgICJvd25lciI6IDI5CiAgICAgIH0KICAgIF0sCiAgICAicHJldmlvdXNfc2V2ZW5faW50YWtlcyI6IFsKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkyMjksCiAgICAgICAgIm93bmVyIjogMjMKICAgICAgfSwKICAgICAgewogICAgICAgICJzZXF1ZW5jZSI6IDkyMzEsCiAgICAgICAgIm93bmVyIjogMgogICAgICB9LAogICAgICB7CiAgICAgICAgInNlcXVlbmNlIjogOTIzNywKICAgICAgICAib3duZXIiOiAxNwogICAgICB9LAogICAgICB7CiAgICAgICAgInNlcXVlbmNlIjogOTI0MywKICAgICAgICAib3duZXIiOiAyMQogICAgICB9LAogICAgICB7CiAgICAgICAgInNlcXVlbmNlIjogOTI0OSwKICAgICAgICAib3duZXIiOiAzCiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MjUxLAogICAgICAgICJvd25lciI6IDE1CiAgICAgIH0sCiAgICAgIHsKICAgICAgICAic2VxdWVuY2UiOiA5MjU3LAogICAgICAgICJvd25lciI6IDE5CiAgICAgIH0KICAgIF0sCiAgICAicHJldmlvdXMzMl9pbnRha2UiOiA5MTQxLAogICAgInByZXZpb3VzXzU4N18yM19zdXBlcnNlZGVkIjogdHJ1ZSwKICAgICJzb3VyY2VfcmVmcyI6IFsKICAgICAgewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjA0LWVhNzYtNzA3MC1hNGUyLTBmYTBhNjc2ODQ5ZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwNC1kMGU3LTc0NTQtYTE4Ny1mYTdiZDgyYmNhNDAiLAogICAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgICB9LAogICAgICB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDUtMjM5Zi03MDYxLWI2YWEtZTg1NGI1NjU5MDA1IiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjA0LWQwZTctNzQ1NC1hMTg3LWZhN2JkODJiY2E0MCIsCiAgICAgICAgInJlY29yZGVkX29ubHkiOiB0cnVlCiAgICAgIH0KICAgIF0sCiAgICAiY291bnRzX2FyZV9ub3RfZGF0YXNldHNfcmVjaXBlc19vcl9jb21wbGV0ZWRfY291bnRyaWVzIjogdHJ1ZQogIH0sCiAgImFkb3B0ZWRfbWV0YWRhdGEiOiB7CiAgICAiY29tbWl0IjogImIxNWRlOTU5M2QyNDJkMzZhNjNkMmIwMGRkNjA3OGQ1N2I0ZDgyYTMiLAogICAgImJyYW5jaCI6ICJpbnRlZ3JhdGlvbi9yZWdpc3RyeS1tZXRhZGF0YS1jYW5kaWRhdGUtMjAyNjEwMTgiLAogICAgImVudHJ5IjogImRvY3MvcmVnaXN0cnktY2FuZGlkYXRlLzIwMjYtMTAtMTgvQ1VSUkVOVDI0OS5qc29uIiwKICAgICJzb3VyY2Vfc25hcHNob3RfdXRjIjogIjIwMjYtMTAtMThUMTI6MDA6NDYuMzYxMTkzWiIsCiAgICAic291cmNlX3NuYXBzaG90X2xvY2FsIjogIjIwMjYtMTAtMThUMjM6MDA6NDYrMTE6MDAiLAogICAgImFkb3B0ZWRfbG9jYWwiOiAiMjAyNi0xMC0xOFQyMzozMzoxNCsxMTowMCIsCiAgICAibWV0YWRhdGFfb25seSI6IHRydWUsCiAgICAibGF0ZXJfY29sbGVjdGlvbl9ub3Rfc2lsZW50bHlfcmVwaW5uZWQiOiB0cnVlLAogICAgInF1YXJhbnRpbmVzX3JldGFpbmVkIjogNjAzLAogICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMy02NDY4LTcyNTktOTRiYi1iYzAzYmU0NzdkZTIiLAogICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZjAyLWU4MmEtNzU3OC1hOWM4LTM5OTAyNDMyNGI4NyIsCiAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgfSwKICAgICJsb29rdXBfY29ycmVjdGlvbiI6IHsKICAgICAgImNvbW1pdCI6ICI3NjlkZjRhOTU0NjVhYTkzOTZjM2Y1YTdiNWYzZGUzOTBmNmIwNzVkIiwKICAgICAgInBhdGgiOiAiZG9jcy9yZWdpc3RyeS1jYW5kaWRhdGUvMjAyNi0xMC0xOC9jb3VudHJ5LWxvb2t1cC1oYW5kb3Zlci8iLAogICAgICAicHJvdmVuYW5jZSI6ICJQYXJlbnQgYXNzaWdubWVudCBzdXBwbGllZCwgbm90IGluZGVwZW5kZW50bHkgaW5zcGVjdGVkIGhlcmUuIgogICAgfQogIH0sCiAgImhvbGRfcHJvcGFnYXRpb24iOiB7CiAgICAib3duZXIzMSI6IHsKICAgICAgInNlcXVlbmNlIjogOTMzNywKICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC9jb3VudHJ5LWNvbGxlY3Rpb24taW52ZW50b3J5L3dvcmtlcjU3L293bmVyMzEtc291cmNlLXVzZS1pbmNpZGVudC1yZXRhaW5lZC9ob2xkLXByb3BhZ2F0aW9uLXJlc3VsdC5qc29uIiwKICAgICAgInNoYTI1NiI6ICJlOGYxMDcyYWYzZmZkZGZiYzYyYmMxMDA5ZmVhODBmN2Y2NWFkYTc0NGJkNzJiNjExM2E5ZTFiZjgxMjg4OWM4IiwKICAgICAgInN0YXR1cyI6ICJSZXBvcnRlZCBtZXRhZGF0YS1vbmx5IGhvbGQgcHJvcGFnYXRpb24gY2hlY2tlZDsxNCBlbGlnaWJsZSBzb3VyY2VzIHNlcGFyYXRlbHkgcGVuZGluZyIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjA0LWVhNzYtNzA3MC1hNGUyLTBmYTBhNjc2ODQ5ZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwNC1kMGU3LTc0NTQtYTE4Ny1mYTdiZDgyYmNhNDAiLAogICAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgICB9CiAgICB9LAogICAgIm93bmVyNTIiOiB7CiAgICAgICJzdGF0dXMiOiAiU2VwYXJhdGUgc291cmNlLXVzZSBxdWFyYW50aW5lIHJlcG9ydGVkOyBubyBsYXRlcjU3IHByb3BhZ2F0aW9uIGNvbmZpcm1lZCIsCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWZmLTEwMGQtNzMzNy04MGI3LWU4N2NmNGE2NDEzZSIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiLAogICAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgICB9CiAgICB9CiAgfSwKICAicGgyMCI6IHsKICAgICJvd25lciI6IDIwLAogICAgInJlc3VsdF9zZXF1ZW5jZSI6IDg4MDUsCiAgICAic3RhdHVzIjogIkZBSUxFRF9QQVJUSUFMX1pFUk9fQ09NUExFVEUiLAogICAgInBhcnRpYWxfYnl0ZXMiOiAxOTY2MDgwMCwKICAgICJleHBlY3RlZF93aG9sZV9ieXRlcyI6IDE0NjYxNDI4NCwKICAgICJwcmVzZXJ2ZV9jbGFpbV9yZXNlcnZhdGlvbl9zZXF1ZW5jZSI6IDg0ODUsCiAgICAiY29uc2VydmF0aXZlX2d1YXJkX2J5dGVzIjogMTY3NzcyMTYwLAogICAgIm5vX3JldHJ5X3Jlc3VtZV9vcl9wcm9iZSI6IHRydWUsCiAgICAibWlzc2luZ19yZXN1bWVfcHJvb2YiOiBbCiAgICAgICJTdHJvbmcgcmVtb3RlIGlkZW50aXR5L0VUYWciLAogICAgICAiVmFsaWRhdGVkMjA2IG1hdGNoaW5nIG9mZnNldCBhbmQgd2hvbGUgdG90YWwiCiAgICBdLAogICAgInJlY292ZXJ5X3JlY2VpcHQiOiB7CiAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyNjQtYWNxdWlzaXRpb24tY29udGludWl0eS9uZXh0LXJlYWwtY29udGludWF0aW9uLWZvb2RibG9nLTIwMjYxMDE4L2FjdHVhbDg4MDUtY3VycmVudC1yZWNvdmVyeS5qc29uIiwKICAgICAgInNoYTI1NiI6ICJiNzA1MDU1ZDEzZWZlZjEyNWYyZDhmYTc1ZGY1OTBlNGRmYTY5NTY1ZjdjYTMzM2I1MDRhMzg5MWVmYTAwZjk5IgogICAgfSwKICAgICJyYXdfcGF0aCI6IG51bGwsCiAgICAiY2xhaW1fcGF0aCI6IG51bGwsCiAgICAicmVzZXJ2YXRpb25fcGF0aCI6IG51bGwsCiAgICAidW5rbm93bl9wYXRoX3J1bGUiOiAiRG8gbm90IGd1ZXNzIG9yIHNjYW4gZm9yIHJhdyBwYXJ0aWFsLiBSZXNvbHZlIG1ldGFkYXRhIHZpYSBleGlzdGluZyBsZWRnZXIvc291cmNlIHBpbnMuIiwKICAgICJzb3VyY2VfcmVmcyI6IFsKICAgICAgewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZWYwLWMyNTktNzZmMS1iZmQ0LWE1ZTRmMmFkZTJiZCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmMC1iYjlmLTc0MzYtYjA5Yy01Y2ZkNzY3OTFlNjkiLAogICAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgICB9LAogICAgICB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRlZmMtYmU2Ni03NzBkLTlmZjUtMTBiNjU4OWFjNTFjIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWZiLWRjY2YtNzM5YS05ODc0LWE3NjYxNjljMjc2YiIsCiAgICAgICAgInJlY29yZGVkX29ubHkiOiB0cnVlCiAgICAgIH0KICAgIF0KICB9LAogICJhY3RpdmVfb3JfdW5jZXJ0YWluIjogWwogICAgewogICAgICAib3duZXIiOiAxMiwKICAgICAgInN0YXR1cyI6ICJSZXBvcnRlZCBhY3RpdmUgTUwgdHJhbnNmZXIvTU0gcHJlcGFyYXRpb24gYmV5b25kIE1OIHN1YnNldDkyMTciLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZi1jODY4LTcxOWMtOWZiZi04MjNiNmEzZDIwMjgiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmUtOWRlOC03MDdmLTgyMjAtMjg5MTllZmM2N2VjIiwKICAgICAgICAicmVjb3JkZWRfb25seSI6IHRydWUKICAgICAgfSwKICAgICAgImRvX25vdF9kdXBsaWNhdGUiOiB0cnVlCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA1NiwKICAgICAgInN0YXR1cyI6ICJSZXBvcnRlZCBzZXF1ZW50aWFsIGFjcXVpc2l0aW9uIGFmdGVyIHBpY2t1cDkwNjcsIG5vIHRlcm1pbmFsIG1hbmlmZXN0IG9ic2VydmVkIiwKICAgICAgInJlcG9ydGVkX3Byb2dyZXNzIjogIjIgTkkgYW5hbHl0aWNhbCBQREZzNjQ5ODEyNUIsV0YrUG9seW5lc2lhIHJlY2lwZUhUTUwzMzQ0NkI7NTUgQUNTQSByZWNpcGVQREYgbGlua3MgdW5kZXIgcHJvdmlkZXItcm9ib3RzIHF1YWxpZmljYXRpb24iLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmZC1lZjNiLTc2ODEtOGVlNC0yNjAxNGIxMTJiM2IiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmItZGNjZi03MzlhLTk4NzQtYTc2NjE2OWMyNzZiIiwKICAgICAgICAicmVjb3JkZWRfb25seSI6IHRydWUKICAgICAgfSwKICAgICAgImRvX25vdF9kdXBsaWNhdGUiOiB0cnVlCiAgICB9LAogICAgewogICAgICAib3duZXIiOiA2MSwKICAgICAgInN0YXR1cyI6ICJQaWNrdXA5MDE4L3NvdXJjZS1wcmVwYXJhdGlvbiByZXBvcnRlZCwgbm8gbGF0ZXIgcmVzdWx0IG9ic2VydmVkIGluIGluc3BlY3RlZCBtZXNzYWdlcyIsCiAgICAgICJwaW4iOiB7CiAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTYxL3JlY2lwZS1yZWZpbGwtYWZ0ZXI4OTQyL3BpY2t1cC1hbmQtYnVkZ2V0Lmpzb24iLAogICAgICAgICJzaGEyNTYiOiAiZDI4NTZiMzBkMDhlZmFkN2EyMTliZWY4OThjNmIxNTdhYzIzMWZlYWJkY2EyZDY4YTkxYzNiNDg5Mjk3NDkzMyIKICAgICAgfSwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRlZjYtMThiMS03NDFhLWE5YTEtNzkyNDU3YWFmZWI4IiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWYwLWJiOWYtNzQzNi1iMDljLTVjZmQ3Njc5MWU2OSIsCiAgICAgICAgInJlY29yZGVkX29ubHkiOiB0cnVlCiAgICAgIH0sCiAgICAgICJkb19ub3RfZHVwbGljYXRlIjogdHJ1ZQogICAgfSwKICAgIHsKICAgICAgIm93bmVycyI6IFsKICAgICAgICAwLAogICAgICAgIDI1CiAgICAgIF0sCiAgICAgICJzdGF0dXMiOiAiR2F0ZXdheSByZXBvcnRzIGJvdGggUFI1MSBQMSBmaXhlcyBkaXNwYXRjaGVkIHRvMDAsMjUgYXNzaWduZWQgdXBjb21pbmcgaW1tdXRhYmxlIHJldmlldzsgYWN0dWFsIHJ1bm5pbmcvZml4L3JldmlldyBub3QgY29uZmlybWVkIGhlcmUiLAogICAgICAiZmluZGluZ3MiOiBbCiAgICAgICAgImh0dHBzOi8vZ2l0aHViLmNvbS9tYWxkb3VzL29mZm1lbnUvcHVsbC81MSNkaXNjdXNzaW9uX3I0MzA2ODUyNzk1IiwKICAgICAgICAiaHR0cHM6Ly9naXRodWIuY29tL21hbGRvdXMvb2ZmbWVudS9wdWxsLzUxI2Rpc2N1c3Npb25fcjQzMDY4NTI3OTgiCiAgICAgIF0sCiAgICAgICJob2xkIjogIk5ldyBsYXJnZSBhZmZlY3RlZCByZXRhaW5lZC1jb3B5IHJ1bnMgaGVsZCB1bnRpbCBjb3JyZWN0ZWQ7IGluZGVwZW5kZW50IGFjcXVpc2l0aW9uIHVuYWZmZWN0ZWQiLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICJtc2dfMDYyNDc0ODBjMDFmMDFiZDAxNmFkNGJlMGExMzhjODE5MWIwZTg1YzljNWM3ZjQ0M2UiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDUtN2ViMC03NTkyLTljNWEtZTIzOTM0YjJkOWRjIiwKICAgICAgICAicmVjb3JkZWRfb25seSI6IHRydWUKICAgICAgfSwKICAgICAgImRvX25vdF9kdXBsaWNhdGUiOiB0cnVlCiAgICB9CiAgXSwKICAidHJhbnNwb3J0X3VuY2VydGFpbnR5IjogewogICAgInByaW5jaXBsZSI6ICJBIHJlY29yZGVkIG5vdGlmaWNhdGlvbiwgc2VuZCBpbnRlbnQsIEdhdGV3YXkgcm91dGluZyBzdGF0ZW1lbnQgb3IgcmVwb3J0ZWQgcmVjZWlwdCBpcyBub3Qgb3duZXIgYWNrbm93bGVkZ21lbnQsIGxpdmUgcGlja3VwLCBsZWRnZXIgY29uc3VtcHRpb24sNTcgY2hlY2ssIG9yIGNhbm9uaWNhbCBhZG9wdGlvbi4iLAogICAgImtub3duX3NwZWNpZmljIjogWwogICAgICB7CiAgICAgICAgIm93bmVyIjogMTAsCiAgICAgICAgIm9sZF9zZXF1ZW5jZXMiOiBbCiAgICAgICAgICA0NTAwLAogICAgICAgICAgNTE0NywKICAgICAgICAgIDUyNjkKICAgICAgICBdLAogICAgICAgICJzdGF0dXMiOiAiSGlzdG9yaWNhbCBmYWlsZWQvdW5jZXJ0YWluIHNlbmRzIGV4cGxpY2l0bHkgbm90IHJldHJpZWQiLAogICAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMi05NjgwLTcwYWQtOGZlYS04MWJhYmJmYWE3MmEiLAogICAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwMi0wMDljLTcwNjctODY0ZS1mNWE1M2I2MzJhZjciLAogICAgICAgICAgInJlY29yZGVkX29ubHkiOiB0cnVlCiAgICAgICAgfQogICAgICB9LAogICAgICB7CiAgICAgICAgIm93bmVyIjogNTEsCiAgICAgICAgInN0YXR1cyI6ICJJbml0aWFsIGZ1bGwgaGFuZG92ZXIgZmFpbGVkIHR1cm4gYWxyZWFkeSBhY3RpdmUgb25jZTs5MzE3IGlzIGRpc3RpbmN0IG5ldyBtYXRlcmlhbCByZXN1bHQsIG5vdCByZXNlbmQiLAogICAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGYwMy1lZDUyLTc1Y2MtOTk0NC01YWFlYTkyNTVkNDMiLAogICAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwMy1lNjk2LTc3ZGQtYTlmMS02ZDkxNTU0NjRlNmEiLAogICAgICAgICAgInJlY29yZGVkX29ubHkiOiB0cnVlCiAgICAgICAgfQogICAgICB9LAogICAgICB7CiAgICAgICAgIm93bmVyIjogMjgsCiAgICAgICAgInNlbmRfaW50ZW50IjogOTM2NCwKICAgICAgICAiYWN0dWFsX3Jlc3VsdCI6IDkzNTcsCiAgICAgICAgInN0YXR1cyI6ICJOb3RpZmljYXRpb24gc2VwYXJhdGUgZnJvbSBhY2tub3dsZWRnbWVudCBhbmQ1NyBqb2luIiwKICAgICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMGEtMDc2Mi03NzE3LWFjN2ItODkzYTMwZjEwYTZhIiwKICAgICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRmMDUtN2ViMC03NTkyLTljNWEtZTIzOTM0YjJkOWRjIiwKICAgICAgICAgICJyZWNvcmRlZF9vbmx5IjogdHJ1ZQogICAgICAgIH0KICAgICAgfQogICAgXSwKICAgICJhbGxfb3RoZXJfdW5leHBvc2VkX3F1ZXVlcyI6ICJ1bmtub3duIgogIH0sCiAgImNhcGFjaXR5IjogewogICAgImhpc3RvcmljYWxfcGxhbm5pbmdfZ3VhcmRfNDlfYW5kX3ByZXAiOiA4ODI3MzMyMTk4NCwKICAgICJmb3VyX2ZvbGxvd29uX3BsYW5uaW5nX2d1YXJkIjogODg0MTgwMjU0NzIsCiAgICAiZmxvb3JfYnl0ZXMiOiAyMTQ3NDgzNjQ4MCwKICAgICJmbG9vcl9pbmNsdWRlZF9pbl9ndWFyZCI6IHRydWUsCiAgICAiY29ycmVjdGlvbl9zaGEyNTYiOiAiMGQwZThlMjE1MjNiYmI0ZjhmZDE2MjMyNmI3NzA2OGViZThjZjIwNTNlYTk3NjYyY2Q3ZTllMDViMjBjZmU2NyIsCiAgICAicmVzZXJ2YXRpb25fcmVsZWFzZV9hdXRob3JpemVkIjogZmFsc2UsCiAgICAidW5pdmVyc2FsX291dHN0YW5kaW5nX3RvdGFsIjogbnVsbCwKICAgICJydWxlIjogIlByZXNlcnZlIGhpc3RvcmljYWwgYmxvY2tlZCByZWNlaXB0cy4gRnJlc2ggYWN0dWFsIGNvbW1pdG1lbnRzL2ZyZWUvcGh5c2ljYWwgYWxsb2NhdGlvbiByZXF1aXJlZCBiZWZvcmUgYW55IGZ1dHVyZSBhdXRob3JpemVkIEdFVDsgcGxhbm5pbmcgZ3VhcmQgaXMgbm90IGEgdW5pdmVyc2FsIG1lYXN1cmVkIHJlc2VydmF0aW9uIHRvdGFsLiBEbyBub3QgZG91YmxlLWFkZCBmbG9vciBvciB6ZXJvIHVua25vd24gY29tbWl0bWVudHMuIgogIH0sCiAgIm9mZmxpbmVfcmVjb25jaWxpYXRpb24iOiB7CiAgICAiZXhpc3RpbmdfbGVkZ2VyX3BhdGhzIjogWwogICAgICAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvaW50ZXJpbS1vYmxpZ2F0aW9uLWluZGV4Lmpzb24iLAogICAgICAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcGVybWFuZW50LWxlZGdlci9ldmVudHMuanNvbmwiCiAgICBdLAogICAgInBhdGhfc291cmNlIjogewogICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDItOTY4MC03MGFkLThmZWEtODFiYWJiZmFhNzJhIiwKICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGYwMi0wMDljLTcwNjctODY0ZS1mNWE1M2I2MzJhZjciLAogICAgICAicmVjb3JkZWRfb25seSI6IHRydWUKICAgIH0sCiAgICAic291cmNlX2NsYWltX3Jvb3QiOiBudWxsLAogICAgImRvX25vdF9ndWVzc19zb3VyY2VfY2xhaW1zIjogdHJ1ZSwKICAgICJzdGVwcyI6IFsKICAgICAgIlJlYWQgb25seSBleGFjdCBzdXBwbGllZCBleGlzdGluZyBsZWRnZXIsIGhhbmRvdmVyIGFuZCBtZXRhZGF0YSBwaW5zLiIsCiAgICAgICJSZWNvbmNpbGUgdGVybWluYWwsIHF1ZXVlZCwgYWN0aXZlIGFuZCB1bmNlcnRhaW4gZWZmZWN0cyBiZWZvcmUgZGlzcGF0Y2hpbmcgYW55IHNvdXJjZSBqb2IuIiwKICAgICAgIlByZXNlcnZlIGV2ZW50IElEcywgcHJvZHVjZXIgb3duZXIvdGhyZWFkL3R1cm4gYW5kIG51bGwgbGluZWFnZTsgbmV2ZXIgYmFja2ZpbGwgY2Fub25pY2FsIGVsaWdpYmlsaXR5LiIsCiAgICAgICJEZWR1cGxpY2F0ZSBleGFjdCBpbW11dGFibGUgZXZlbnQrbWFuaWZlc3QgYW5kIHJhdyBzb3VyY2UgaWRlbnRpdHk7IHNoYXJlZCBnbG9iYWwgYm9kaWVzIG9uY2UsIHN1YnNldHMvZmluYWxzIGV4cGxpY2l0bHkgcmVsYXRlZC4iLAogICAgICAiTGVhdmUgbWlzc2luZy9zdGFsZS91bnJlYWRhYmxlIHBpbnMgdW5yZXNvbHZlZDsgbm8gbnVsbC10by16ZXJvIG9yIGFic2VuY2UgaW5mZXJlbmNlLiIsCiAgICAgICJPbmx5IGV4aXN0aW5nNTcgYWdncmVnYXRpb24vMDAgY2Fub25pY2FsIHJlc3BvbnNpYmlsaXRpZXMgcmVtYWluOyBubyByZXBsYWNlbWVudCBjb29yZGluYXRvciBvciBzb3VyY2UtY3VzdG9keSB0cmFuc2Zlci4iCiAgICBdCiAgfSwKICAiZ2xvYmFsX2hvbGRzIjogWwogICAgIkFsbCBvcmlnaW5hbCBzb3VyY2UgY29udHJhY3RzIGFuZCBzdHJpY3RlciBzb3VyY2Utc3BlY2lmaWMgcmlnaHRzIHByZXZhaWwgb3ZlciB0aGlzIHN1bW1hcnkuIiwKICAgICJSYXcgc291cmNlIG9yaWdpbmFscyBzdGF5IG9uIEZvbzsgbm8gcmF3IEdpdEh1YiB1cGxvYWRzLiIsCiAgICAiUHJpdmFjeSwgbWlub3JzLCBuby1yZWFkLCBzb3VyY2UtdXNlLCBkZW5pYWwvbm8tcmV0cnksIEZJL0ZyaWRhLCBuYXRpdmVOTy9GUiwgTk9fQlJJREdFLCBkZW5zaXR5IHJlcXVlc3QtYmFzZWQgcmV1c2UsIGN1c3RvZHkgYW5kIGNsb2NrIGxpbWl0YXRpb25zIHJlbWFpbi4iLAogICAgIlByb2R1Y3Rpb24sIENJWCwgREVWNzY0NSwgcnVudGltZS9VSSBhbmQgbm9ybWFsaXphdGlvbi90cmFuc2xhdGlvbi9nb2xkIGhvbGRzIHJlbWFpbjszMCBzdGF5cyBjbG9zZWQuIiwKICAgICJNYW5kYXRvcnkgYXV0b19yZXZpZXcgcmVtYWluczsgcGFzdCB0b29saW5nIHBlcm1pc3Npb24gbGFiZWxzIGRvIG5vdCBncmFudCBuZXcgYWNjZXNzLiIKICBdLAogICJ1bmtub3ducyI6IFsKICAgICJBY3R1YWwgY3VycmVudCBGb28gcHJvY2Vzc2VzLCBxdWV1ZWQgc2VuZHMgYW5kIG5hdGl2ZSB0aHJlYWQgc3RhdGVzIGFmdGVyIHVzYWdlIGZhaWx1cmUuIiwKICAgICJXaGV0aGVyNTcgY2hlY2tlZCBhbnkgbGlzdGVkIHBlbmRpbmcgcGFja2V0IGFmdGVyIGxhdGVzdCByZWNvcmRlZDY1OS8yNyByZXBvcnQuIiwKICAgICJFeGFjdCBwZXItb3JpZ2luYWwgaWRlbnRpdHkvVVJML2hhc2ggYW5kIGNsYWltIGZpbGVzIHJlcXVpcmUgcGlubmVkIG1hbmlmZXN0cywgbm90IGluZmVycmVkIGZyb20gdGhpcyBzdW1tYXJ5LiIsCiAgICAiRXhhY3QgcmVzdWx0IGV2ZW50IElEIGZvciBvd25lcjU1OyBzZXF1ZW5jZXMgZm9yIG93bmVyMTMsMjJmaW5hbCwyNyBhbmQ2M3NlbGVjdGVkIHJlc3VsdCBub3Qgc3RhdGVkIGluIGluc3BlY3RlZCByZXBvcnRzLiIsCiAgICAiTm8gZXhoYXVzdGl2ZSBhbGw2NCBvciBhbGw0OSBhY3RpdmUtb3duZXIgcm9zdGVyIGFzc2VydGVkOyB1bnJlcG9ydGVkIG93bmVycyBtYXkgcmVtYWluIGFjdGl2ZS4iLAogICAgIlBIMjAgcmF3L2NsYWltL3Jlc2VydmF0aW9uIHBhdGhzIGFuZCB1bml2ZXJzYWwgcmVzZXJ2YXRpb24gdG90YWwgcmVtYWluIHVua25vd24uIiwKICAgICJTb21lIG9sZGVyIEdhdGV3YXkgcGFnZXMgd2VyZSB0cnVuY2F0ZWQ7IGFsbDMwIHBlbmRpbmcgc291cmNlLW1lc3NhZ2UgcmVjb3JkcyB1c2VkIGhlcmUgd2VyZSByZWNvdmVyZWQgdW50cnVuY2F0ZWQuIgogIF0sCiAgInByZXBhcmF0aW9uX29ubHkiOiBbCiAgICB7CiAgICAgICJvd25lciI6IDUsCiAgICAgICJzZXF1ZW5jZSI6IDkyMTQsCiAgICAgICJzdGF0dXMiOiAiUFJFUEFSQVRJT05fT05MWV9OT1RfQUNRVUlSRUQiLAogICAgICAibm90ZSI6ICJQWTYgc291cmNlLXNpemVkIGNhbmRpZGF0ZXMrMSB1bmtub3duLWV4dGVudCBjYW5kaWRhdGU7IG5vIGJvZHkgdHJhbnNmZXIvY2xhaW0uIiwKICAgICAgImV4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xOC93b3JrZXIwNS1zb3VyY2UtcHJlcC1hZnRlcjg5NDIvcmVzdWx0LXJlY2VpcHQuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogImZlZmMwOWFhZTRkMTQ1ZDk0ODJmOWUwNDdiYTI5YjgwMGI0ZjU5MTA5OTAxOGYyYWFlOTdjYzMxYTgwNzc5OGMiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjA1LXNvdXJjZS1wcmVwLWFmdGVyODk0Mi9yZWFkeS1zb3VyY2UtcG9ydGZvbGlvLmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICI5NWJmNDRlMTc0N2FlMTQ2YTMwNDRjZjFhMmUwMDI4MDdlNmI3Y2Q5ZDI4OTk1YjY1ODQ3NDU0OTFiNzY3MmMyIgogICAgICAgIH0KICAgICAgXSwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRlZmYtYzg2Ny03MzFlLTliMTktNmFkOTE5N2ZmNDIyIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWZlLTlkZTgtNzA3Zi04MjIwLTI4OTE5ZWZjNjdlYyIKICAgICAgfQogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogOCwKICAgICAgInNlcXVlbmNlIjogOTIxOSwKICAgICAgInN0YXR1cyI6ICJQUkVQQVJBVElPTl9PTkxZX05PVF9BQ1FVSVJFRCIsCiAgICAgICJub3RlIjogIldITyBTYXJhamV2bytBbHRlcnVyYWwyIG9yaWdpbmFscyBwcm9wb3NlZDEyTWlCLCBubyBib2R5R0VUOyB1c2Ugb3duZXIwNiBzaGFyZWRHSVogZXhpc3Rpbmdjb3B5LiIsCiAgICAgICJleHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTMvdGFzay0zL3JlcG9ydHMvY291bnRyeTI0OS1maXhlZDY0LXByaW9yaXR5L2RlbGl2ZXJhYmxlcy9vd25lci0wOC9yZWNpcGUtaW5ncmVkaWVudC1wcmVwYXJhdGlvbi1hZnRlcjg5NDIvcHJlcGFyZWQtc291cmNlLXBvcnRmb2xpby5qc29uIiwKICAgICAgICAgICJzaGEyNTYiOiAiNWRjMGEzMzYwMWEzZmUxNmUzOWE4MTc4ODZmNzQzYjNhZmEwMGI3NGRlZDAxODM3MTNhMWNkNDI3NDFiMzllZSIKICAgICAgICB9LAogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvc3JjL29mZm1lbnUtZGF0YS9vcmlnaW5hbHMvY291bnRyeS1zb3VyY2UtY29weS0yMDI2MTAxOC9vd25lci0wNi9yZWNpcGVzLWFmdGVyODk0Mi9SRUdJT05BTC1HSVotRk9PRC1CRVlPTkQtQk9SREVSUy9yZWNlaXB0Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICJjZjY2ZThmNDI5YTBhNTFlOTIwYTQwN2JiYzg5NmY5NjlmOWZmYzU3OWZhMWIwOWY5YTA2OTRlMzUxMzgxYWY5IgogICAgICAgIH0KICAgICAgXSwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRlZmYtZGE4OS03NmNiLTljZjUtMDEwNTIyMGFhYTk2IiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWZlLTlkZTgtNzA3Zi04MjIwLTI4OTE5ZWZjNjdlYyIKICAgICAgfQogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogMjAsCiAgICAgICJzZXF1ZW5jZSI6IDkxMTYsCiAgICAgICJzdGF0dXMiOiAiUFJFUEFSQVRJT05fT05MWV9OT1RfQUNRVUlSRUQiLAogICAgICAibm90ZSI6ICJTQiBIZWx0aSBLYWlrYWkyNyw1NzgsNTkwIEIgcHJvc3BlY3Qgb25seSwgbm8gYm9keUdFVC4gUEggc2VwYXJhdGUgaG9sZCB1bmNoYW5nZWQuIiwKICAgICAgImV4cGxpY2l0X21ldGFkYXRhX3BpbnMiOiBbCiAgICAgICAgewogICAgICAgICAgInBhdGgiOiAiL2hvbWUvdXNlci9Eb2N1bWVudHMvQ29kZXgvMjAyNi0xMC0xMy90YXNrLTMvcmVwb3J0cy9jb3VudHJ5MjQ5LWZpeGVkNjQtcHJpb3JpdHkvZGVsaXZlcmFibGVzL293bmVyLTIwL3JlY2lwZS1zb3VyY2UtcHJlcGFyYXRpb24tMjAyNjEwMTgvcHJvc3BlY3RpdmUtYXNzZXQtbWFuaWZlc3QuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogImRjMzlkYTk1MDU3Y2FjMTM3MmQzYzAyZGQ2Nzc0ZTc0MjBjNjNjNTkzNjQ0ZDEyNzcwZjc2YjUwMGQyNzViMjYiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTEzL3Rhc2stMy9yZXBvcnRzL2NvdW50cnkyNDktZml4ZWQ2NC1wcmlvcml0eS9kZWxpdmVyYWJsZXMvb3duZXItMjAvcmVjaXBlLXNvdXJjZS1wcmVwYXJhdGlvbi0yMDI2MTAxOC9wcmVwYXJhdGlvbi1yZXN1bHQuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogIjMwODQyMDBkY2Q5ZDA0NWVlZTJkMGE1ZDg0NmE4ZDQzMmIxZjkzMTkzZjlhYTg0NmQ0NmE0ODg3OWUwOWI5OGUiCiAgICAgICAgfQogICAgICBdLAogICAgICAic291cmNlX3JlZiI6IHsKICAgICAgICAiZ2F0ZXdheV90aHJlYWRfaWQiOiAiMDFhMTMwY2QtOTFjMS03M2RhLTk5NzgtODg5MDE4YTEwMGRkIiwKICAgICAgICAibWVzc2FnZV9pZCI6ICIwMWExNGVmYy1iZTY2LTc3MGQtOWZmNS0xMGI2NTg5YWM1MWMiLAogICAgICAgICJnYXRld2F5X3R1cm5faWQiOiAiMDFhMTRlZmItZGNjZi03MzlhLTk4NzQtYTc2NjE2OWMyNzZiIgogICAgICB9CiAgICB9LAogICAgewogICAgICAib3duZXIiOiAzOCwKICAgICAgInNlcXVlbmNlIjogOTA4NSwKICAgICAgInN0YXR1cyI6ICJQUkVQQVJBVElPTl9PTkxZX05PVF9BQ1FVSVJFRCIsCiAgICAgICJub3RlIjogIk5vIHF1YWxpZmllZCByZWFkeSBvcmlnaW5hbDo2IFNDT1BFRF9OT05FKzJIRUxEX1NPVVJDRSwgbm90IGdsb2JhbCBhYnNlbmNlLiIsCiAgICAgICJleHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvc3JjL29mZm1lbnUtZGF0YS93b3JrZXItMzgtc291cmNlLXByZXBhcmF0aW9uLWFmdGVyODk0Mi0yMDI2MTAxOC9zb3VyY2UtcG9ydGZvbGlvLmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICI0NGJiYzYxNTZmOTZlYjZjM2YyYWFjMDM2YzZjNTcxNjgyYzY1YzU1YjRmZDdlY2NkMTgxNWY3ZWMyYjVlYTQ2IgogICAgICAgIH0KICAgICAgXSwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRlZmEtY2IyYS03MDU1LWIyODEtZGMxMDUwMzcyMTRiIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWYwLWJiOWYtNzQzNi1iMDljLTVjZmQ3Njc5MWU2OSIKICAgICAgfQogICAgfSwKICAgIHsKICAgICAgIm93bmVyIjogNDEsCiAgICAgICJzZXF1ZW5jZSI6IDkyNDUsCiAgICAgICJzdGF0dXMiOiAiUFJFUEFSQVRJT05fT05MWV9OT1RfQUNRVUlSRUQiLAogICAgICAibm90ZSI6ICJUVzMgb2ZmZXJlZCByZWdpb25hbCByZWNpcGVQREZzIHVua25vd25leHRlbnQsIHByb3Bvc2VkMTZNaUIgZWFjaC80OE1pQiBiYXRjaC4gTm8gR0VUL2NsYWltL3Jlc2VydmF0aW9uLiIsCiAgICAgICJleHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTMvdGFzay0zL3JlcG9ydHMvY291bnRyeTI0OS1maXhlZDY0LXByaW9yaXR5L2RlbGl2ZXJhYmxlcy9vd25lci00MS9yZWNpcGUtY29tcG9zaXRpb24tcHJlcC1hZnRlcjg5NDIvc291cmNlLXBvcnRmb2xpby5qc29uIiwKICAgICAgICAgICJzaGEyNTYiOiAiMjc4ODRjZjlkNzc4ZWI3ZjVlNDYwNDEzMDBjZDMzNmU5ZDIyYzc0YTYxMDA2ZTlmZjFjYjRkNDg2ZTE1ZmYyYiIKICAgICAgICB9CiAgICAgIF0sCiAgICAgICJzb3VyY2VfcmVmIjogewogICAgICAgICJnYXRld2F5X3RocmVhZF9pZCI6ICIwMWExMzBjZC05MWMxLTczZGEtOTk3OC04ODkwMThhMTAwZGQiLAogICAgICAgICJtZXNzYWdlX2lkIjogIjAxYTE0ZjAwLTQyYmUtNzU4Ni05ZjljLTFhNzBhOTdiZTk5MCIsCiAgICAgICAgImdhdGV3YXlfdHVybl9pZCI6ICIwMWExNGVmZS05ZGU4LTcwN2YtODIyMC0yODkxOWVmYzY3ZWMiCiAgICAgIH0KICAgIH0sCiAgICB7CiAgICAgICJvd25lciI6IDY0LAogICAgICAic2VxdWVuY2UiOiA5MjYxLAogICAgICAic3RhdHVzIjogIlBSRVBBUkFUSU9OX09OTFlfTk9UX0FDUVVJUkVEIiwKICAgICAgIm5vdGUiOiAiU0IyMCBwcm9zcGVjdGl2ZSBjb250cmFjdCBvbmx5LiBkcmFmdCBhdXRob3JpemVkPWZhbHNlL2h1bWFuT3JpZ2luQ29uZmlybWVkPWZhbHNlO25vIHNlbGVjdGlvbi9zZW5kL3BpY2t1cC9ib2R5R0VUL3B1YmxpY2F0aW9uLiIsCiAgICAgICJleHBsaWNpdF9tZXRhZGF0YV9waW5zIjogWwogICAgICAgIHsKICAgICAgICAgICJwYXRoIjogIi9ob21lL3VzZXIvRG9jdW1lbnRzL0NvZGV4LzIwMjYtMTAtMTgvd29ya2VyNjQtYWNxdWlzaXRpb24tY29udGludWl0eS9TQjIwLUhlbHRpLUthaWthaS1wcm9zcGVjdGl2ZS1jb250cmFjdC9jb250cmFjdC1wcmVwYXJhdGlvbi1yZXN1bHQuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogIjkzYTMyYWM1ZDdkZGE3NDEwOWQzNjU0OTkxOGM0OWI0YTFkZThkNzc1NWM4ODQwZTMyYmUxYTdmNTI0NWI3MDQiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjY0LWFjcXVpc2l0aW9uLWNvbnRpbnVpdHkvU0IyMC1IZWx0aS1LYWlrYWktcHJvc3BlY3RpdmUtY29udHJhY3QvYWNxdWlzaXRpb24tY29udHJhY3QuanNvbiIsCiAgICAgICAgICAic2hhMjU2IjogIjk0OTc0NTFhY2I1ZDhlYzc2MDUzYTgxMDdjYTdhM2Y2ZjkzMTBjYjQ0NzgyMjMzMmY4Y2ZjZDQzMDk2MTE3M2EiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAicGF0aCI6ICIvaG9tZS91c2VyL0RvY3VtZW50cy9Db2RleC8yMDI2LTEwLTE4L3dvcmtlcjY0LWFjcXVpc2l0aW9uLWNvbnRpbnVpdHkvU0IyMC1IZWx0aS1LYWlrYWktcHJvc3BlY3RpdmUtY29udHJhY3QvZXhlY3V0aW9uLWd1YXJkLWlucHV0Lmpzb24iLAogICAgICAgICAgInNoYTI1NiI6ICIxYTJiYjkyZDBkNjBiMjAzNjUyOWRhYWU3ZmYyMWE5OWI1MGJkYzRkYzEzYTI0YzdmYjhiNDUxYzhhYjVjMzFiIgogICAgICAgIH0KICAgICAgXSwKICAgICAgInNvdXJjZV9yZWYiOiB7CiAgICAgICAgImdhdGV3YXlfdGhyZWFkX2lkIjogIjAxYTEzMGNkLTkxYzEtNzNkYS05OTc4LTg4OTAxOGExMDBkZCIsCiAgICAgICAgIm1lc3NhZ2VfaWQiOiAiMDFhMTRmMDAtZGY4Ni03MGM0LTlkOWQtNzJlMmZiMDQwYjFiIiwKICAgICAgICAiZ2F0ZXdheV90dXJuX2lkIjogIjAxYTE0ZWZlLTlkZTgtNzA3Zi04MjIwLTI4OTE5ZWZjNjdlYyIKICAgICAgfQogICAgfQogIF0KfQo='

import base64
import shutil
import math
import selectors
import subprocess
import tempfile
import time

OWNER_SCHEMA = 'offmenu-owner-custody-snapshot/1'
BASE_SHA = 'ea3988b88bf33bbe288b974b94650b6e741f89cb'
REPOSITORY = 'maldous/offmenu'
REPOSITORY_ID = 1416253963
OWNER_ID = 6347545
DEST_BRANCH = 'integration/foo-owner-custody-snapshot-20261018'
DEST_ROOT = 'docs/handover/2026-10-18/foo-owner-custody'
MAX_SNAPSHOT = 512 * 1024
MAX_TOTAL_READ = 96 * 1024 * 1024
MAX_TARGETS = 80
MAX_DISCOVERY_ENTRIES = 2048
MAX_DISCOVERED_FILES = 24
MAX_API = 2 * 1024 * 1024
PROJECT = '/home/user/Documents/Codex/2026-10-13/task-3'
DISCOVERY_ROOTS = (
    PROJECT,
    PROJECT + '/permanent-ledger',
    '/home/user/Documents/Codex/2026-10-18/worker64-acquisition-continuity',
    '/home/user/src/offmenu-data/metadata',
)
DISCOVERY_DIRS = {'metadata', 'control', 'claims', 'source-claims', 'source_claims',
                  'reservations', 'disk-reservations', 'acquisition-control', 'permanent-ledger'}
CLAIM_NAMES = {'claims.json', 'claims.jsonl', 'source-claims.json', 'source-claims.jsonl',
               'source_claims.json', 'source_claims.jsonl', 'claim-registry.json'}
RESERVATION_NAMES = {'reservations.json', 'reservations.jsonl', 'disk-reservations.json',
                     'space-reservations.json', 'reservation-ledger.jsonl',
                     'source-reservations.json', 'storage-reservations.json'}
FIXED_CAPACITY = (('native-data', '/home/user/src/offmenu-data'),
                  ('native-originals', '/home/user/src/offmenu-data/originals'),
                  ('runner-output', '/srv/offmenu-refresh/outputs'))
FLAGS = {'snapshotIsLiveOwnershipClearance': False, 'nativeProcessesObserved': False,
         'sourceBodiesRead': False, 'sourceBodiesUploaded': False, 'sourceWrites': 0,
         'downloads': 0, 'sourceClaimsChanged': False, 'reservationsReleased': False,
         'canonicalAdoptionChanged': False, 'newCoordinatorCreated': False,
         'permissionsChanged': False, 'networkAcquisitionEnabled': False,
         'allSourceHoldsRetained': True, 'reservationTotalsAuthoritative': False}


class HandoverError(Exception):
    pass


def cutover():
    raw = base64.b64decode(CUTOVER_B64, validate=True)
    if hashlib.sha256(raw).hexdigest() != CUTOVER_SHA256:
        raise HandoverError('embedded-cutover-digest-mismatch')
    value = _json(raw)
    if len(value['pending_receipts']) != 30 or value['stage'] != 'COMPLETE_READ_ONLY_HANDOVER':
        raise HandoverError('embedded-cutover-invalid')
    return value


def exact_targets(baseline):
    rows = []
    def add(pin, label, owner=None):
        if not pin:
            return
        path, expected = pin['path'], pin.get('sha256')
        if not isinstance(path, str) or not path.startswith('/home/user/') or not path.endswith(('.json', '.jsonl', '.md')):
            raise HandoverError('embedded-target-invalid')
        if expected is not None and not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise HandoverError('embedded-pin-invalid')
        # Conservative source-use no-read handling: metadata paths retained,
        # bodies for the two quarantined owners are not opened by this script.
        held = owner in (31, 52)
        rows.append({'targetId': label, 'path': path, 'expectedSHA256': expected,
                     'mode': 'metadata-only' if held or path.endswith('.md') else 'jsonl-tail' if path.endswith('.jsonl') else 'json',
                     'owner': owner, 'heldBodyRead': held})
    for index, row in enumerate(baseline['pending_receipts']):
        add(row.get('primary_metadata_pin'), 'pending-%02d-primary' % index, row['owner'])
        for number, pin in enumerate(row.get('other_explicit_metadata_pins', [])):
            add(pin, 'pending-%02d-additional-%02d' % (index, number), row['owner'])
    for index, row in enumerate(baseline['preparation_only']):
        for number, pin in enumerate(row.get('explicit_metadata_pins', [])):
            add(pin, 'preparation-%02d-%02d' % (index, number), row['owner'])
    for label, pin in [('latest57-summary', baseline['latest_reported_checked_57']['summary']),
                       ('latest57-index', baseline['latest_reported_checked_57']['latest_index']),
                       ('ph20-recovery', baseline['ph20']['recovery_receipt'])]:
        add(pin, label)
    add(baseline['hold_propagation']['owner31'], 'owner31-hold-metadata', 31)
    for label, path in [('native-handover', PROJECT+'/permanent-ledger/handover.json'),
                        ('native-events', PROJECT+'/permanent-ledger/events.jsonl'),
                        ('interim-obligations', PROJECT+'/interim-obligation-index.json'),
                        ('operating-entrypoint', PROJECT+'/OFFMENU-OPERATING-ENTRYPOINT.md')]:
        add({'path': path}, label)
    if len(rows) > MAX_TARGETS:
        raise HandoverError('target-count-limit')
    return rows


CUSTODY_DETAILS = False
_base_summarize = summarize
_base_sanitize_summary = sanitize_summary
CUSTODY_SOURCE_FIELDS = ('sourceId', 'source_id', 'canonicalSourceId', 'sourceUrl', 'source_url', 'url')
CUSTODY_BYTE_FIELDS = RESERVATION_FIELDS | {'partialBytes', 'partial_bytes', 'downloadedBytes', 'downloaded_bytes', 'expectedBytes', 'expected_bytes', 'totalBytes', 'total_bytes'}


def summarize(records):
    result = _base_summarize(records)
    if not CUSTODY_DETAILS:
        return result
    projected, stack, truncated = [], list(records), False
    while stack:
        row = stack.pop()
        if isinstance(row, list):
            stack.extend(row)
        elif isinstance(row, dict):
            source = next(((k, row[k]) for k in CUSTODY_SOURCE_FIELDS if isinstance(row.get(k), str) and len(row[k]) <= 4096), None)
            owner = None
            for key in OWNER_FIELDS:
                item = row.get(key)
                if type(item) is int and 0 <= item <= 64:
                    owner = item
                    break
                if isinstance(item, str) and re.fullmatch(r'(?:worker[- ]?)?(?:0?[0-9]|[1-5][0-9]|6[0-4])', item):
                    owner = int(re.sub(r'^worker[- ]?', '', item))
                    break
            state = next((row[k] for k in sorted(STATUS_FIELDS) if isinstance(row.get(k), str) and row[k] in STATES), None)
            amounts = {k: row[k] for k in sorted(CUSTODY_BYTE_FIELDS) if type(row.get(k)) is int and 0 <= row[k] <= 2**63-1}
            if owner is not None or source is not None or amounts:
                if len(projected) == 32:
                    truncated = True
                    break
                projected.append({'sourceIdentitySHA256': None if source is None else hashlib.sha256(source[1].encode()).hexdigest(),
                                  'sourceIdentityBasis': None if source is None else source[0],
                                  'ownerObserved': owner, 'stateObserved': state, 'byteFieldsObserved': amounts})
            stack.extend(v for v in row.values() if isinstance(v, (dict, list)))
    result.update(custodyRecords=projected, custodyRecordsTruncated=truncated,
                  custodyRecordsAreCurrentClaims=False)
    return result


def sanitize_summary(value):
    extra = {'custodyRecords', 'custodyRecordsTruncated', 'custodyRecordsAreCurrentClaims'}
    if not set(value) & extra:
        return _base_sanitize_summary(value)
    if not extra <= set(value) or type(value['custodyRecordsTruncated']) is not bool or value['custodyRecordsAreCurrentClaims'] is not False:
        raise ValueError('invalid-custody-summary')
    result = _base_sanitize_summary({k: v for k, v in value.items() if k not in extra})
    records = value['custodyRecords']
    if not isinstance(records, list) or len(records) > 32:
        raise ValueError('invalid-custody-records')
    for row in records:
        if set(row) != {'sourceIdentitySHA256', 'sourceIdentityBasis', 'ownerObserved', 'stateObserved', 'byteFieldsObserved'}:
            raise ValueError('invalid-custody-record')
        digest, basis, owner = row['sourceIdentitySHA256'], row['sourceIdentityBasis'], row['ownerObserved']
        if (digest is None) != (basis is None) or digest is not None and (not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest) or basis not in CUSTODY_SOURCE_FIELDS):
            raise ValueError('invalid-custody-identity')
        if owner is not None and (type(owner) is not int or not 0 <= owner <= 64):
            raise ValueError('invalid-custody-owner')
        if row['stateObserved'] is not None and row['stateObserved'] not in STATES:
            raise ValueError('invalid-custody-state')
        if not isinstance(row['byteFieldsObserved'], dict) or not set(row['byteFieldsObserved']) <= CUSTODY_BYTE_FIELDS:
            raise ValueError('invalid-custody-bytes')
        for count in row['byteFieldsObserved'].values():
            _uint(count)
    result.update({key: value[key] for key in extra})
    return result


def observe_target(target):
    global CUSTODY_DETAILS
    CUSTODY_DETAILS = target.get('category') in ('claims', 'reservations')
    result = observe_file((target['targetId'], target['path'], target['mode']))
    expected = target['expectedSHA256']
    result.update(expectedSHA256=expected, owner=target['owner'], heldBodyRead=target['heldBodyRead'],
                  pinStatus='withheld-source-hold' if target['heldBodyRead'] else
                  'stat-only-observed' if result['readMode'] == 'metadata-only' and result['access'] == 'observed' else
                  'unavailable' if result['access'] != 'observed' or result['metadataSHA256'] is None else
                  'unpinned-current-observation' if expected is None else
                  'sample-cannot-verify-pin' if result['digestScope'] != 'whole-file' else
                  'match' if result['metadataSHA256'] == expected else 'mismatch')
    return result


def discover():
    """List only fixed project metadata roots and reviewed metadata subdirs.

    Never enter originals/raw/download/cache/source trees or echo a rejected name.
    At most depth two, 2,048 entries and 24 recognized exact filenames in total.
    """
    diagnostics, found, count, visited = [], [], 0, set()
    queue = [(path, 0, index) for index, path in enumerate(DISCOVERY_ROOTS)]
    while queue:
        path, depth, root_id = queue.pop(0)
        if path in visited:
            continue
        visited.add(path)
        fd = None
        state, examined = 'observed', 0
        try:
            fd = _open_exact(path, directory=True)
            with os.scandir(fd) as entries:
                for entry in entries:
                    count += 1
                    examined += 1
                    if count > MAX_DISCOVERY_ENTRIES:
                        state = 'entry-limit'
                        break
                    # Names are compared, never emitted unless in the closed set.
                    if entry.name in CLAIM_NAMES | RESERVATION_NAMES:
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISREG(info.st_mode):
                            candidate = path + '/' + entry.name
                            if candidate not in {v['path'] for v in found}:
                                if len(found) >= MAX_DISCOVERED_FILES:
                                    state = 'file-limit'
                                    break
                                found.append({'targetId': 'discovered-%02d' % len(found), 'path': candidate,
                                              'expectedSHA256': None, 'mode': 'jsonl-tail' if entry.name.endswith('.jsonl') else 'json',
                                              'owner': None, 'heldBodyRead': False,
                                              'category': 'claims' if entry.name in CLAIM_NAMES else 'reservations'})
                    elif depth < 2 and entry.name in DISCOVERY_DIRS and entry.is_dir(follow_symlinks=False):
                        queue.append((path + '/' + entry.name, depth + 1, root_id))
        except OSError as error:
            state = _error(error)
        finally:
            if fd is not None:
                os.close(fd)
        diagnostics.append({'rootId': root_id, 'path': path, 'depth': depth,
                            'state': state, 'entriesExamined': min(examined, MAX_DISCOVERY_ENTRIES + 1)})
        if state in ('entry-limit', 'file-limit'):
            break
    return found, {'roots': diagnostics, 'recognizedFiles': len(found),
                   'entriesExamined': min(count, MAX_DISCOVERY_ENTRIES + 1),
                   'scopeExhaustive': False,
                   'claimsCatalogIdentified': any(v['category'] == 'claims' for v in found),
                   'reservationsCatalogIdentified': any(v['category'] == 'reservations' for v in found),
                   'unidentifiedIsEmpty': False}


def step(label, code, started, reason):
    return {'stepId': label, 'exitCode': code,
            'status': 'passed' if code == 0 else 'blocked' if code == 2 else 'failed',
            'durationSeconds': round(time.monotonic() - started, 3), 'reason': reason}


def collect_snapshot(baseline):
    started = time.monotonic()
    observed_at = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    steps, observations, total = [], [], 0
    targets = exact_targets(baseline)
    for target in targets:
        if total >= MAX_TOTAL_READ:
            break
        row = observe_target(target)
        total += row['metadataBytesRead']
        observations.append(row)
    exact_ok = len(observations) == len(targets) and all(r['access'] == 'observed' and r['pinStatus'] in ('match', 'unpinned-current-observation', 'withheld-source-hold', 'stat-only-observed') and (r['readMode'] == 'metadata-only' or r['wholeFileObserved']) for r in observations)
    steps.append(step('exact-metadata', 0 if exact_ok else 2, started, 'registered-observations-complete' if exact_ok else 'inaccessible-changed-unverified-or-bounded-inputs'))
    begin = time.monotonic()
    found, discovery = discover()
    discovered = []
    for target in found:
        if total >= MAX_TOTAL_READ:
            break
        row = observe_target(target)
        total += row['metadataBytesRead']
        row['category'] = target['category']
        discovered.append(row)
    identified = (discovery['claimsCatalogIdentified'] and discovery['reservationsCatalogIdentified'] and
                  len(discovered) == len(found) and all(r['access'] == 'observed' and r['wholeFileObserved'] for r in discovered))
    steps.append(step('claims-and-reservations', 0 if identified else 2, begin, 'bounded-catalog-observations-only' if identified else 'catalogs-unidentified-inaccessible-or-partial'))
    begin = time.monotonic()
    spaces = [observe_space(t) for t in FIXED_CAPACITY]
    capacity_ok = all(r['access'] == 'observed' for r in spaces)
    steps.append(step('filesystem-capacity', 0 if capacity_ok else 2, begin, 'capacity-only-no-reservation-subtraction' if capacity_ok else 'capacity-partial-no-reservation-subtraction'))
    report = {'schemaVersion': OWNER_SCHEMA, 'observedAt': observed_at,
              'sourceBaseSHA': BASE_SHA, 'cutoverSHA256': CUTOVER_SHA256,
              'recordedCutUTC': baseline['generated_at_utc'], 'baseline': baseline,
              'metadata': observations, 'discoveredMetadata': discovered,
              'discovery': discovery, 'capacity': spaces, 'steps': steps,
              'totalMetadataBytesRead': total,
              'overallStatus': 'observations-complete' if all(s['exitCode'] == 0 for s in steps) else 'incomplete',
              **FLAGS}
    return validate_snapshot(report, baseline, targets, found)


def validate_observation(row, target):
    expected_keys = {'targetId', 'path', 'readMode', 'access', 'fileBytes', 'modifiedAtNs',
                     'metadataBytesRead', 'wholeFileObserved', 'metadataSHA256', 'digestScope',
                     'summary', 'expectedSHA256', 'owner', 'heldBodyRead', 'pinStatus'}
    if set(row) - {'category'} != expected_keys or row['targetId'] != target['targetId'] or row['path'] != target['path'] or row['readMode'] != target['mode']:
        raise HandoverError('observation-schema-invalid')
    if row['access'] not in ACCESS_STATES or row['expectedSHA256'] != target['expectedSHA256'] or row['owner'] != target['owner'] or row['heldBodyRead'] != target['heldBodyRead']:
        raise HandoverError('observation-binding-invalid')
    for key in ('fileBytes', 'modifiedAtNs'):
        if row[key] is not None:
            _uint(row[key])
    if _uint(row['metadataBytesRead']) > MAX_BYTES + 1 or type(row['wholeFileObserved']) is not bool:
        raise HandoverError('observation-bound-invalid')
    if row['metadataSHA256'] is not None and not re.fullmatch(r'[0-9a-f]{64}', row['metadataSHA256']):
        raise HandoverError('observation-digest-invalid')
    if row['digestScope'] not in (None, 'whole-file', 'bounded-tail'):
        raise HandoverError('observation-digest-scope-invalid')
    if row['summary'] is not None:
        if sanitize_summary(row['summary']) != row['summary']:
            raise HandoverError('observation-summary-invalid')
    if target['heldBodyRead'] and (row['metadataBytesRead'] or row['summary'] is not None):
        raise HandoverError('held-body-read')
    expected_pin = ('withheld-source-hold' if target['heldBodyRead'] else
                    'stat-only-observed' if row['readMode'] == 'metadata-only' and row['access'] == 'observed' else
                    'unavailable' if row['access'] != 'observed' or row['metadataSHA256'] is None else
                    'unpinned-current-observation' if target['expectedSHA256'] is None else
                    'sample-cannot-verify-pin' if row['digestScope'] != 'whole-file' else
                    'match' if row['metadataSHA256'] == target['expectedSHA256'] else 'mismatch')
    if row['pinStatus'] != expected_pin:
        raise HandoverError('pin-state-invalid')


def validate_snapshot(report, baseline, targets, discovered_targets):
    keys = {'schemaVersion', 'observedAt', 'sourceBaseSHA', 'cutoverSHA256', 'recordedCutUTC', 'baseline', 'metadata', 'discoveredMetadata', 'discovery', 'capacity', 'steps', 'totalMetadataBytesRead', 'overallStatus'} | set(FLAGS)
    if set(report) != keys or baseline != cutover() or report['schemaVersion'] != OWNER_SCHEMA or report['baseline'] != baseline or report['cutoverSHA256'] != CUTOVER_SHA256 or report['sourceBaseSHA'] != BASE_SHA:
        raise HandoverError('snapshot-binding-invalid')
    timestamp(report['observedAt'])
    if report['recordedCutUTC'] != baseline['generated_at_utc'] or targets != exact_targets(baseline):
        raise HandoverError('snapshot-target-binding-invalid')
    if not isinstance(report['metadata'], list) or len(report['metadata']) > len(targets) or not isinstance(report['discoveredMetadata'], list) or len(report['discoveredMetadata']) > len(discovered_targets):
        raise HandoverError('snapshot-target-count-invalid')
    for target in discovered_targets:
        path = Path(target['path'])
        valid = False
        for root in DISCOVERY_ROOTS:
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if len(relative.parts) <= 4 and all(p in DISCOVERY_DIRS for p in relative.parts[:-1]) and relative.name in CLAIM_NAMES | RESERVATION_NAMES:
                valid = True
        if not valid:
            raise HandoverError('discovered-target-outside-bounded-scope')
    if len(report['steps']) != 3 or [v['stepId'] for v in report['steps']] != ['exact-metadata', 'claims-and-reservations', 'filesystem-capacity']:
        raise HandoverError('snapshot-steps-invalid')
    reasons = {'registered-observations-complete', 'inaccessible-changed-unverified-or-bounded-inputs', 'bounded-catalog-observations-only', 'catalogs-unidentified-inaccessible-or-partial', 'capacity-only-no-reservation-subtraction', 'capacity-partial-no-reservation-subtraction'}
    for entry in report['steps']:
        if set(entry) != {'stepId', 'exitCode', 'status', 'durationSeconds', 'reason'} or type(entry['exitCode']) is not int or entry['exitCode'] not in (0, 2) or entry['status'] != ('passed' if entry['exitCode'] == 0 else 'blocked') or entry['reason'] not in reasons or type(entry['durationSeconds']) not in (int, float) or not math.isfinite(entry['durationSeconds']) or not 0 <= entry['durationSeconds'] <= 3600:
            raise HandoverError('snapshot-step-invalid')
    if report['overallStatus'] != ('observations-complete' if all(v['exitCode'] == 0 for v in report['steps']) else 'incomplete'):
        raise HandoverError('snapshot-status-invalid')
    if len(report['capacity']) != len(FIXED_CAPACITY):
        raise HandoverError('snapshot-capacity-invalid')
    for row, (label, path) in zip(report['capacity'], FIXED_CAPACITY):
        if set(row) != {'targetId', 'path', 'access', 'availableBytes', 'availableInodes', 'readOnly'} or row['targetId'] != label or row['path'] != path or row['access'] not in ACCESS_STATES:
            raise HandoverError('snapshot-capacity-binding-invalid')
        for key in ('availableBytes', 'availableInodes'):
            if row[key] is not None:
                _uint(row[key])
        if row['readOnly'] is not None and type(row['readOnly']) is not bool:
            raise HandoverError('snapshot-capacity-flag-invalid')
    discovery = report['discovery']
    if set(discovery) != {'roots', 'recognizedFiles', 'entriesExamined', 'scopeExhaustive', 'claimsCatalogIdentified', 'reservationsCatalogIdentified', 'unidentifiedIsEmpty'} or discovery['scopeExhaustive'] is not False or discovery['unidentifiedIsEmpty'] is not False or discovery['recognizedFiles'] != len(discovered_targets) or _uint(discovery['entriesExamined']) > MAX_DISCOVERY_ENTRIES + 1:
        raise HandoverError('snapshot-discovery-invalid')
    for row in discovery['roots']:
        if set(row) != {'rootId', 'path', 'depth', 'state', 'entriesExamined'} or type(row['rootId']) is not int or not 0 <= row['rootId'] < len(DISCOVERY_ROOTS) or type(row['depth']) is not int or not 0 <= row['depth'] <= 2 or row['state'] not in ACCESS_STATES | {'entry-limit', 'file-limit'}:
            raise HandoverError('snapshot-discovery-row-invalid')
        relative = Path(row['path']).relative_to(DISCOVERY_ROOTS[row['rootId']])
        if len(relative.parts) != row['depth'] or any(p not in DISCOVERY_DIRS for p in relative.parts):
            raise HandoverError('snapshot-discovery-path-invalid')
        _uint(row['entriesExamined'])
    for key, expected in FLAGS.items():
        if type(report.get(key)) is not type(expected) or report[key] != expected:
            raise HandoverError('snapshot-safety-flag-invalid')
    for row, target in zip(report['metadata'], targets):
        validate_observation(row, target)
    for row, target in zip(report['discoveredMetadata'], discovered_targets):
        validate_observation(row, target)
        if row['category'] != target['category']:
            raise HandoverError('discovery-category-invalid')
    if _uint(report['totalMetadataBytesRead']) > MAX_TOTAL_READ + MAX_BYTES + 1:
        raise HandoverError('total-read-limit')
    if len(canonical(report)) > MAX_SNAPSHOT:
        raise HandoverError('snapshot-size-limit')
    return report


# Revision 2: source-bound reconciliation, retaining the original publication protocol.
from urllib.parse import urlsplit

OWNER_SCHEMA = 'offmenu-owner-custody-snapshot/2'
MAX_SNAPSHOT = 8 * 1024 * 1024
MAX_API = 16 * 1024 * 1024
MAX_NODES = 1500000
INDEX_OBSERVED_BYTES = 14588360
MAX_LEDGER_BYTES = 64 * 1024 * 1024
MAX_RECORDS = 10000
MAX_REFERENCE_FILES = 128
MAX_REFERENCE_ENTRIES = 2048
READ_REMAINING = MAX_TOTAL_READ
TIME_FIELDS |= {'atUTC', 'createdUTC', 'recordedUTC', 'updatedUTC', 'observed_at_utc', 'created_at', 'updated_at'}
REFERENCE_ROOTS = ('/home/user/Documents/Codex/', '/home/user/src/offmenu-data/')
REFERENCE_ORIGINS = {'pending-01-primary', 'pending-03-primary', 'pending-05-primary', 'pending-14-primary'}
# The source owner check below, rather than positional labels, binds the four receipts.
REQUIRED_FIELDS = ('identity', 'owner', 'status', 'country', 'datatype', 'sha256', 'bytes', 'sourceUrl', 'release', 'holds', 'metadataReferences')
TOKEN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,191}')
SECRET_RE = re.compile(r'(?i)(?:gh[pousr]_|github_pat_|(?<![A-Za-z0-9])sk-[a-z0-9]|bearer|password|passwd|authorization|api[_-]?key|access[_-]?token|secret|credential|private[_-]?key)')
FIELD_MAP = {
 'assetId':'assetId','asset_id':'assetId','sourceId':'sourceId','source_id':'sourceId','canonicalSourceId':'sourceId',
 'sourceKey':'sourceKey','canonicalSourceKey':'sourceKey','eventId':'eventId','event_id':'eventId',
 'kind':'kind','recordedDatatype':'datatype','datatype':'datatype','dataType':'datatype',
 'status':'status','state':'state','claimStatus':'claimStatus','transferStatus':'transferStatus',
 'collectionStatus':'collectionStatus','outcome':'outcome','op':'operation','operation':'operation',
 'recordedExistenceState':'existenceState','existenceState':'existenceState','format':'format', 'releaseId':'release', 'release':'release',
 'custodian':'custodian', 'custodianId':'custodian',
}
BYTE_MAP = {'recordedBytes':'bytes','bytes':'bytes','sizeBytes':'bytes','byte_count':'bytes','size_bytes':'bytes',
 'reservedBytes':'reservedBytes','reserved_bytes':'reservedBytes','reservationBytes':'reservedBytes',
 'reservation_bytes':'reservedBytes','partialBytes':'partialBytes','partial_bytes':'partialBytes',
 'downloadedBytes':'downloadedBytes','downloaded_bytes':'downloadedBytes','expectedBytes':'expectedBytes',
 'expected_bytes':'expectedBytes','totalBytes':'totalBytes','total_bytes':'totalBytes'}
SHA_FIELDS = ('recordedSHA256','sha256','sha256Hex','fileSHA256','file_sha256','checksum_sha256')
URL_FIELDS = ('sourceUrl','sourceURL','source_url','canonicalUrl','canonicalURL','canonical_url','url')
SKIP_CONTAINERS = {'body','content','text','message','messages','raw','rawBody','rows','recipes','ingredients','instructions','directions','description','notes','logs','log','html','csv','password','credentials','secrets','environment','env'}
REFERENCE_FIELDS = {'claimPath':'claims','claim_path':'claims','claimsPath':'claims','claims_path':'claims',
 'claimFile':'claims','claim_file':'claims','claimsFile':'claims','claimRoot':'claims','claimsRoot':'claims',
 'sourceClaimRoot':'claims','sourceClaimsRoot':'claims','sourceClaimsPath':'claims','claimDir':'claims',
 'reservationPath':'reservations','reservation_path':'reservations','reservationsPath':'reservations',
 'reservationFile':'reservations','reservation_file':'reservations','reservationRoot':'reservations',
 'reservationsRoot':'reservations','reservationDir':'reservations','budgetLedger':'reservations'}
CONTEXT_FIELDS = {'claim':'claims','claims':'claims','sourceClaims':'claims','source_claims':'claims',
 'reservation':'reservations','reservations':'reservations','diskReservations':'reservations','budgetReservation':'reservations'}
PATH_FIELDS = {'path','file','root','directory','dir','ledger','ledgerPath','registryPath'}


def safe_token(value, release=False):
    if not isinstance(value, str) or SECRET_RE.search(value):
        return None
    if release:
        return value if len(value) <= 120 and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._:/()+,-]*', value) else None
    return value if TOKEN_RE.fullmatch(value) else None


def safe_url(value):
    if not isinstance(value,str) or len(value)>2048 or SECRET_RE.search(value) or any(ord(c)<33 for c in value):
        return None
    try:
        u=urlsplit(value)
        if u.scheme not in ('https','http') or not u.hostname or u.username or u.password or u.query or u.fragment or u.port not in (None,80,443):
            return None
        if not re.fullmatch(r'[A-Za-z0-9.-]+',u.hostname) or '%' in u.netloc or '\\' in value:
            return None
        # Reject encoded sensitive parameters or control characters as well.
        from urllib.parse import unquote
        decoded=unquote(u.path)
        if SECRET_RE.search(decoded) or '?' in decoded or '#' in decoded or any(ord(c)<32 for c in decoded):
            return None
        return value
    except ValueError:
        return None


def safe_owner(value):
    if type(value) is int and 0<=value<=64:return value
    if isinstance(value,str):
        m=re.fullmatch(r'(?:owner|worker|native)?[- ]?0?([0-9]|[1-5][0-9]|6[0-4])',value)
        if m:return int(m.group(1))
    return None


def metadata_reference_path(value, category, directory=None):
    if not isinstance(value,str) or len(value)>1024 or not value.startswith(REFERENCE_ROOTS) or SECRET_RE.search(value):return None
    p=Path(value)
    if any(x in ('.','..') or x.startswith('.') for x in p.parts[1:]) or '\\' in value or not re.fullmatch(r'[A-Za-z0-9_./ -]+',value):return None
    # No quarantined owner tree, raw body, or credential path can be followed.
    if re.search(r'(?i)(?:owner[-_]?0?(?:31|52)|worker[-_]?0?(?:31|52))(?:/|[-_])',value):return None
    markers=('claim','reservation','budget')
    if not any(m in p.name.lower() for m in markers) and not any(any(m in q.lower() for m in markers) for q in p.parts[-3:-1]):return None
    if directory is True:
        return value if not p.suffix and any(m in p.name.lower() for m in markers) else None
    if directory is False:
        return value if p.suffix in ('.json','.jsonl') else None
    return value if p.suffix in ('.json','.jsonl') or not p.suffix and any(m in p.name.lower() for m in markers) else None


def safe_record(row, event=False, inherited_id=None):
    out={}
    for key,target in FIELD_MAP.items():
        v=safe_token(row.get(key),release=target=='release')
        if v is not None:out[target]=v
    if inherited_id is not None and 'assetId' not in out:out['assetId']=inherited_id
    if event and safe_token(row.get('id')):out['eventId']=row['id']
    for key in sorted(OWNER_FIELDS | {'custodian','custodianId','claimOwner','claim_owner'}):
        owner=safe_owner(row.get(key))
        if owner is not None:out['owner']=owner;break
    for key,target in BYTE_MAP.items():
        if type(row.get(key)) is int and 0<=row[key]<=2**63-1:out[target]=row[key]
    for key in SHA_FIELDS:
        if isinstance(row.get(key),str) and re.fullmatch(r'[a-fA-F0-9]{64}',row[key]):out['sha256']=row[key].lower();break
    for key in URL_FIELDS:
        if safe_url(row.get(key)):out['sourceUrl']=row[key];break
    for key in ('country','countryCode','iso2'):
        if isinstance(row.get(key),str) and re.fullmatch('[A-Z]{2}',row[key]):out['country']=row[key];break
    for key in ('seq','sequence','journalSequence','eventSequence'):
        if type(row.get(key)) is int and 0<=row[key]<=2**63-1:out['sequence']=row[key];break
    for key in sorted(TIME_FIELDS):
        try:
            out['timestamp']=timestamp(row.get(key));break
        except (ValueError,TypeError):pass
    for key in ('typeHints','types','holds','holdCodes','unresolved','blockers'):
        if isinstance(row.get(key),list):
            values=[v for v in row[key][:64] if safe_token(v)]
            if values:out['holdCodes' if key=='holds' else key]=values
            if key in ('holds','holdCodes') and row[key]:out['holdsPresent']=True
    for key in ('holdsPresent','held','heldExistence','reportedPhysicalStatus','complete','countryComplete','active','released','authorized','humanOriginConfirmed'):
        if type(row.get(key)) is bool:out[key]=row[key]
    scope=row.get('recordedScope')
    if isinstance(scope,dict):
        out.update({k:v for k,v in safe_record({k:v for k,v in scope.items() if k in ('country','typeHints','countryComplete')}).items()})
    loc=row.get('locator')
    if isinstance(loc,dict) and isinstance(loc.get('path'),str) and re.fullmatch(r'assets/chunk-\d{3,5}\.json',loc['path']) and isinstance(loc.get('jsonPointer'),str) and re.fullmatch(r'/records/\d+',loc['jsonPointer']):
        out['locator']={'path':loc['path'],'jsonPointer':loc['jsonPointer']}
    return out


def project_metadata(records, target, event=False):
    projected=[];references=[];seen=set();stack=[(v,target.get('category'),None,0) for v in reversed(records)]
    nodes=0;observed=0;truncated=False
    can_refs=target.get('owner') in (4,11,13,35) and target['targetId'].endswith('-primary')
    while stack:
        row,context,inherited_id,depth=stack.pop();nodes+=1
        if nodes>MAX_NODES or depth>MAX_DEPTH:truncated=True;break
        if isinstance(row,list):
            stack.extend((v,context,None,depth+1) for v in reversed(row));continue
        if not isinstance(row,dict):continue
        record=safe_record(row,event=event,inherited_id=inherited_id)
        # Metadata identity or custody facts, never anonymous source data rows.
        identity=any(k in record for k in ('assetId','sourceId','sourceKey','eventId','sha256','sourceUrl','reservedBytes','partialBytes'))
        if identity or context in ('claims','reservations') and record:
            encoded=canonical(record)
            if encoded not in seen:
                seen.add(encoded);observed+=1
                if len(projected)<MAX_RECORDS:projected.append(record)
                else:truncated=True
        for key,value in row.items():
            if key in SKIP_CONTAINERS or SECRET_RE.search(key):continue
            purpose=REFERENCE_FIELDS.get(key) or (context if key in PATH_FIELDS else None)
            if can_refs and purpose and isinstance(value,str):
                path=metadata_reference_path(value,purpose)
                if path and not any(r['path']==path for r in references):
                    if len(references)<64:references.append({'path':path,'category':purpose,'sourceTargetId':target['targetId'],'sourceMetadataSHA256':target.get('expectedSHA256'),'field':key,'directory':Path(path).suffix not in ('.json','.jsonl')})
                    else:truncated=True
            if isinstance(value,(dict,list)):
                inherited=safe_token(key) if re.fullmatch(r'file:[a-f0-9]{16,64}',key) else None
                stack.append((value,CONTEXT_FIELDS.get(key,context),inherited,depth+1))
    present=set()
    for r in projected:
        if set(r)&{'assetId','sourceId','sourceKey','eventId'}:present.add('identity')
        present.update(set(r)&set(REQUIRED_FIELDS))
        if set(r)&{'state','claimStatus','transferStatus','outcome'}:present.add('status')
        if 'holdsPresent' in r or 'holdCodes' in r:present.add('holds')
    if references:present.add('metadataReferences')
    return {'records':projected,'recordsObserved':observed,'recordsTruncated':truncated,
            'metadataReferences':references,'unavailableFields':[k for k in REQUIRED_FIELDS if k not in present]}


def validate_projection(value):
    if set(value)!={'records','recordsObserved','recordsTruncated','metadataReferences','unavailableFields'} or type(value['recordsTruncated']) is not bool or len(value['records'])>MAX_RECORDS or _uint(value['recordsObserved'])<len(value['records']):raise HandoverError('projection-schema-invalid')
    allowed=set(FIELD_MAP.values())|set(BYTE_MAP.values())|{'owner','sha256','sourceUrl','country','sequence','timestamp','typeHints','types','holdCodes','unresolved','blockers','holdsPresent','held','heldExistence','reportedPhysicalStatus','complete','countryComplete','active','released','authorized','humanOriginConfirmed','locator'}
    tokenfields=set(FIELD_MAP.values())
    for row in value['records']:
        if not isinstance(row,dict) or not set(row)<=allowed:raise HandoverError('projection-record-invalid')
        for k,v in row.items():
            if k in tokenfields and safe_token(v,release=k=='release')!=v:raise HandoverError('projection-token-invalid')
            elif k in set(BYTE_MAP.values())|{'sequence'}:_uint(v)
            elif k=='owner' and safe_owner(v)!=v:raise HandoverError('projection-owner-invalid')
            elif k=='sha256' and not re.fullmatch('[a-f0-9]{64}',v):raise HandoverError('projection-sha-invalid')
            elif k=='sourceUrl' and safe_url(v)!=v:raise HandoverError('projection-url-invalid')
            elif k=='country' and not re.fullmatch('[A-Z]{2}',v):raise HandoverError('projection-country-invalid')
            elif k=='timestamp':timestamp(v)
            elif k in ('typeHints','types','holdCodes','unresolved','blockers') and (not isinstance(v,list) or len(v)>64 or any(safe_token(x)!=x for x in v)):raise HandoverError('projection-code-invalid')
            elif k=='locator' and safe_record({'locator':v}).get('locator')!=v:raise HandoverError('projection-locator-invalid')
            elif k not in tokenfields|set(BYTE_MAP.values())|{'sequence','owner','sha256','sourceUrl','country','timestamp','typeHints','types','holdCodes','unresolved','blockers','locator'} and type(v) is not bool:raise HandoverError('projection-boolean-invalid')
    if value['unavailableFields']!=[k for k in REQUIRED_FIELDS if k in value['unavailableFields']]:raise HandoverError('projection-gap-invalid')
    if len(value['metadataReferences'])>64:raise HandoverError('projection-ref-limit')
    for ref in value['metadataReferences']:
        if set(ref)!={'path','category','sourceTargetId','sourceMetadataSHA256','field','directory'} or ref['category'] not in ('claims','reservations') or metadata_reference_path(ref['path'],ref['category'],ref['directory'])!=ref['path'] or ref['field'] not in set(REFERENCE_FIELDS)|PATH_FIELDS or not re.fullmatch('[a-f0-9]{64}',ref['sourceMetadataSHA256'] or ''):raise HandoverError('projection-ref-invalid')
    return value


_v1_exact_targets=exact_targets
_v1_observe_target=observe_target
_v1_validate_observation=validate_observation
_v1_validate_snapshot=validate_snapshot

def exact_targets(baseline):
    targets=_v1_exact_targets(baseline)
    for t in targets:
        if t['targetId']=='owner31-hold-metadata':t.update(owner=57,heldBodyRead=False,mode='json')
        if t['targetId']=='native-events':t['mode']='jsonl-prefix'
    return targets


def file_limit(target):
    return INDEX_OBSERVED_BYTES if target['targetId']=='latest57-index' else MAX_LEDGER_BYTES if target['mode']=='jsonl-prefix' else MAX_BYTES


def observe_target(target):
    global CUSTODY_DETAILS
    CUSTODY_DETAILS=False
    if target['mode'] in ('metadata-only','jsonl-tail'):
        result=_v1_observe_target(target)
        result.update(reconciliation=None,prefixVerification=None)
        return result
    result={'targetId':target['targetId'],'path':target['path'],'readMode':target['mode'],'access':'read-failed',
            'fileBytes':None,'modifiedAtNs':None,'metadataBytesRead':0,'wholeFileObserved':False,'metadataSHA256':None,
            'digestScope':None,'summary':None,'reconciliation':None,'prefixVerification':None}
    fd=None
    try:
        fd=_open_exact(target['path']);before=os.fstat(fd)
        result.update(fileBytes=before.st_size,modifiedAtNs=before.st_mtime_ns)
        if not stat.S_ISREG(before.st_mode):result['access']='not-regular-file'
        elif before.st_size>file_limit(target) or before.st_size*(2 if target['mode']=='jsonl-prefix' else 1)>READ_REMAINING or target['targetId']=='latest57-index' and before.st_size!=INDEX_OBSERVED_BYTES:result['access']='size-limit'
        else:
            remaining=before.st_size;digest=hashlib.sha256();chunks=[];records=[];pending=b''
            event=target['mode']=='jsonl-prefix';native_events=target['targetId']=='native-events';event_count=0;selected=[];mandatory=[];owner_latest={};maxseq=None;latest=None;catalog_truncated=False
            pending_ids={r.get('event_id') for r in cutover()['pending_receipts']} if native_events else set()
            while remaining:
                chunk=os.read(fd,min(65536,remaining))
                if not chunk:raise ValueError('short-file')
                remaining-=len(chunk);result['metadataBytesRead']+=len(chunk);digest.update(chunk)
                if not event:chunks.append(chunk);continue
                pending+=chunk
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1)
                    if not line.strip():continue
                    if len(line)>MAX_BYTES:raise ValueError('line-limit')
                    row=_json(line);event_count+=1
                    if not isinstance(row,dict):raise ValueError('event-not-object')
                    safe=safe_record(row,event=True)
                    # Whitelisted fields in standard ledger payload/record wrappers.
                    for key in ('record','data','payload','details'):
                        if isinstance(row.get(key),dict):
                            for k,v in safe_record(row[key],event=True).items():safe.setdefault(k,v)
                    seq=safe.get('sequence')
                    if seq is not None:maxseq=seq if maxseq is None else max(maxseq,seq)
                    if 'timestamp' in safe:latest=max(latest or '',safe['timestamp'])
                    if native_events:
                        if safe.get('eventId') in pending_ids:mandatory.append(safe)
                        if seq is not None and seq>=8942:selected.append(safe)
                        owner=safe.get('owner')
                        if owner is not None:owner_latest[owner]=(owner_latest.get(owner,[])+[safe])[-3:]
                        if len(selected)>2000:selected=selected[-2000:]
                    else:
                        projected_line=project_metadata([row],target)
                        selected.extend(projected_line['records'][:max(0,MAX_RECORDS-len(selected))])
                        catalog_truncated |= projected_line['recordsTruncated'] or len(selected)>=MAX_RECORDS
                if len(pending)>MAX_BYTES:raise ValueError('line-limit')
            if event and pending.strip():raise ValueError('incomplete-final-event')
            after=os.fstat(fd)
            if event:
                os.lseek(fd,0,os.SEEK_SET);left=before.st_size;verify=hashlib.sha256()
                while left:
                    block=os.read(fd,min(65536,left))
                    if not block:raise ValueError('prefix-short-read')
                    left-=len(block);verify.update(block);result['metadataBytesRead']+=len(block)
                end=os.fstat(fd)
                stable=verify.digest()==digest.digest() and end.st_size>=before.st_size
                result['prefixVerification']={'initialBytes':before.st_size,'afterBytes':end.st_size,'prefixSHA256':digest.hexdigest(),'prefixRehashed':True,'stable':stable,'appendedDuringRead':end.st_size>before.st_size,'recordsParsed':event_count,'maximumSequenceObserved':maxseq}
                if not stable:result['access']='changed-during-read'
                else:
                    selected += mandatory+[r for rows in owner_latest.values() for r in rows]
                    records=list({canonical(r):r for r in selected}.values())
                    projection=project_metadata(records,target,event=True)
                    projection['recordsTruncated']=event_count>len(records) if native_events else catalog_truncated # Explicit selective projection; full prefix was hashed.
                    summary=_base_summarize([]);summary.update(recordsParsed=event_count,maximumSequenceObserved=maxseq,latestTimestampObserved=latest)
                    result.update(summary=summary,reconciliation=projection,access='observed',wholeFileObserved=end.st_size==before.st_size,
                                  metadataSHA256=digest.hexdigest(),digestScope='stable-open-prefix')
            elif (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):result['access']='changed-during-read'
            else:
                actual=digest.hexdigest();result.update(metadataSHA256=actual,digestScope='whole-file',wholeFileObserved=True,access='observed')
                # Parse and project only after exact expected hashes have matched.
                if target.get('expectedSHA256') in (None,actual):
                    records=[_json(b''.join(chunks))]
                    result.update(summary=_base_summarize(records),reconciliation=project_metadata(records,target))
    except OSError as e:result['access']=_error(e)
    except (ValueError,UnicodeError,RecursionError):
        result.update(access='invalid-metadata',summary=None,reconciliation=None,wholeFileObserved=False)
    finally:
        if fd is not None:os.close(fd)
    expected=target['expectedSHA256']
    result.update(expectedSHA256=expected,owner=target['owner'],heldBodyRead=target['heldBodyRead'],
        pinStatus='unavailable' if result['access']!='observed' or result['metadataSHA256'] is None else 'unpinned-current-observation' if expected is None else 'match' if result['digestScope']=='whole-file' and result['metadataSHA256']==expected else 'mismatch')
    return result


def referenced_catalogs(observations):
    found=[];roots=[];entries=0;refs=[]
    for row in observations:
        if row['pinStatus']=='match' and row['owner'] in (4,11,13,35) and row['targetId'].endswith('-primary') and row['reconciliation']:
            refs.extend(row['reconciliation']['metadataReferences'])
    for ref in refs:
        path=ref['path'];category=ref['category'];state='observed';examined=0;fd=None
        def add(p):
            if len(found)>=MAX_REFERENCE_FILES:return False
            if p not in {x['path'] for x in found}:
                found.append({'targetId':'referenced-%03d'%len(found),'path':p,'expectedSHA256':None,
                  'mode':'jsonl-prefix' if p.endswith('.jsonl') else 'json','owner':None,'heldBodyRead':False,
                  'category':category,'reference':ref})
            return True
        try:
            if ref['directory']:
                fd=_open_exact(path,directory=True)
                with os.scandir(fd) as listing:
                    for entry in listing:
                        examined+=1;entries+=1
                        if entries>MAX_REFERENCE_ENTRIES:state='entry-limit';break
                        candidate=path+'/'+entry.name
                        if metadata_reference_path(candidate,category,False) and entry.is_file(follow_symlinks=False):
                            if not add(candidate):state='file-limit';break
            else:add(path)
        except OSError as e:state=_error(e)
        finally:
            if fd is not None:os.close(fd)
        roots.append({'path':path,'category':category,'sourceTargetId':ref['sourceTargetId'],'sourceMetadataSHA256':ref['sourceMetadataSHA256'],'state':state,'entriesExamined':examined})
        if state in ('entry-limit','file-limit'):break
    return found,{'roots':roots,'recognizedFiles':len(found),'entriesExamined':entries,'scopeExhaustive':False,
       'claimsCatalogIdentified':any(t['category']=='claims' for t in found),'reservationsCatalogIdentified':any(t['category']=='reservations' for t in found),'unidentifiedIsEmpty':False}


def collect_snapshot(baseline):
    global READ_REMAINING
    started=time.monotonic();targets=exact_targets(baseline);observations=[];total=0
    for target in targets:
        READ_REMAINING=MAX_TOTAL_READ-total
        row=observe_target(target);observations.append(row);total+=row['metadataBytesRead']
    exact_ok=len(observations)==len(targets) and all(r['access']=='observed' and r['pinStatus'] in ('match','unpinned-current-observation','withheld-source-hold','stat-only-observed') and (r['readMode']=='metadata-only' or r['wholeFileObserved'] or r['prefixVerification'] and r['prefixVerification']['stable']) for r in observations)
    steps=[step('exact-metadata',0 if exact_ok else 2,started,'registered-observations-complete' if exact_ok else 'inaccessible-changed-unverified-or-bounded-inputs')]
    begin=time.monotonic();found,discovery=referenced_catalogs(observations);discovered=[]
    for target in found:
        if total>=MAX_TOTAL_READ:break
        READ_REMAINING=MAX_TOTAL_READ-total
        row=observe_target(target);total+=row['metadataBytesRead'];row['category']=target['category'];row['reference']=target['reference'];discovered.append(row)
    identified=discovery['claimsCatalogIdentified'] and discovery['reservationsCatalogIdentified'] and len(discovered)==len(found) and all(r['access']=='observed' for r in discovered)
    steps.append(step('claims-and-reservations',0 if identified else 2,begin,'bounded-catalog-observations-only' if identified else 'catalogs-unidentified-inaccessible-or-partial'))
    begin=time.monotonic();spaces=[observe_space(t) for t in FIXED_CAPACITY]
    capacity_ok=all(r['access']=='observed' for r in spaces if r['targetId']!='runner-output')
    steps.append(step('filesystem-capacity',0 if capacity_ok else 2,begin,'capacity-only-no-reservation-subtraction' if capacity_ok else 'capacity-partial-no-reservation-subtraction'))
    coverage={'previousSnapshotCommit':'24fc839d44b2e171fec08e3fe6d1622fd4d25a49','previousMatchedPins':49,'previousPendingPrimaryMatches':28,'previousMaximumLedgerSequence':9395,
      'matchedPins':sum(r['pinStatus']=='match' for r in observations),'pendingPrimaryMatches':sum(r['pinStatus']=='match' and r['targetId'].endswith('-primary') for r in observations),
      'requiredFields':list(REQUIRED_FIELDS),'projectionGaps':{r['targetId']:list(REQUIRED_FIELDS) if not r['reconciliation'] else r['reconciliation']['unavailableFields'] for r in observations},
      'catalogueScope':'explicit-references-from-four-hash-matched-receipts-only','ownershipClearance':False,'runnerOutputCapacityRequired':False}
    report={'schemaVersion':OWNER_SCHEMA,'observedAt':dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'sourceBaseSHA':BASE_SHA,'cutoverSHA256':CUTOVER_SHA256,'recordedCutUTC':baseline['generated_at_utc'],'baseline':baseline,'metadata':observations,'discoveredMetadata':discovered,'discovery':discovery,'capacity':spaces,'steps':steps,'totalMetadataBytesRead':total,'coverage':coverage,'overallStatus':'observations-complete' if all(s['exitCode']==0 for s in steps) else 'incomplete',**FLAGS}
    READ_REMAINING=MAX_TOTAL_READ
    return validate_snapshot(report,baseline,targets,found)


def validate_observation(row,target):
    legacy={k:v for k,v in row.items() if k not in ('reconciliation','prefixVerification','reference')}
    # Reuse the original closed-schema checks with exact revision-specific limits.
    global MAX_BYTES
    old=MAX_BYTES;MAX_BYTES=max(old,2*file_limit(target))
    prior_mode=legacy['readMode'];prior_scope=legacy['digestScope'];legacy_target=dict(target)
    if prior_mode=='jsonl-prefix':legacy['readMode']='jsonl-tail';legacy_target['mode']='jsonl-tail'
    if prior_scope=='stable-open-prefix':legacy['digestScope']='whole-file'
    try:_v1_validate_observation(legacy,legacy_target)
    finally:MAX_BYTES=old
    if set(row)-set(legacy) not in ({'reconciliation','prefixVerification'},{'reconciliation','prefixVerification','reference'}):raise HandoverError('revision-observation-schema-invalid')
    if row['reconciliation'] is not None and (row['access']!='observed' or row['pinStatus'] not in ('match','unpinned-current-observation') or target['heldBodyRead']):raise HandoverError('projection-without-observation')
    if row['reconciliation'] is not None:
        validate_projection(row['reconciliation'])
        for ref in row['reconciliation']['metadataReferences']:
            if ref['sourceTargetId']!=target['targetId'] or ref['sourceMetadataSHA256']!=target['expectedSHA256'] or row['pinStatus']!='match' or target['owner'] not in (4,11,13,35) or not target['targetId'].endswith('-primary'):raise HandoverError('reference-provenance-invalid')
    prefix=row['prefixVerification']
    if prefix is not None:
        if set(prefix)!={'initialBytes','afterBytes','prefixSHA256','prefixRehashed','stable','appendedDuringRead','recordsParsed','maximumSequenceObserved'} or prefix['initialBytes']!=row['fileBytes'] or prefix['prefixSHA256']!=row['metadataSHA256'] and row['access']=='observed' or prefix['prefixRehashed'] is not True:raise HandoverError('prefix-binding-invalid')
        for key in ('initialBytes','afterBytes','recordsParsed'):_uint(prefix[key])
        for key in ('stable','appendedDuringRead'):
            if type(prefix[key]) is not bool:raise HandoverError('prefix-flag-invalid')


def validate_snapshot(report,baseline,targets,discovered_targets):
    expected={'schemaVersion','observedAt','sourceBaseSHA','cutoverSHA256','recordedCutUTC','baseline','metadata','discoveredMetadata','discovery','capacity','steps','totalMetadataBytesRead','overallStatus','coverage'}|set(FLAGS)
    if set(report)!=expected or report['schemaVersion']!=OWNER_SCHEMA or report['baseline']!=cutover() or baseline!=cutover() or targets!=exact_targets(baseline) or report['sourceBaseSHA']!=BASE_SHA or report['cutoverSHA256']!=CUTOVER_SHA256 or report['recordedCutUTC']!=baseline['generated_at_utc']:raise HandoverError('snapshot-binding-invalid')
    timestamp(report['observedAt'])
    for key,v in FLAGS.items():
        if type(report.get(key)) is not type(v) or report[key]!=v:raise HandoverError('snapshot-safety-flag-invalid')
    if len(report['metadata'])>len(targets) or len(report['discoveredMetadata'])>len(discovered_targets):raise HandoverError('snapshot-count-invalid')
    for row,target in zip(report['metadata'],targets):validate_observation(row,target)
    for row,target in zip(report['discoveredMetadata'],discovered_targets):
        validate_observation(row,target)
        if row['category']!=target['category'] or row['reference']!=target['reference'] or metadata_reference_path(row['path'],row['category'],False)!=row['path']:raise HandoverError('reference-binding-invalid')
    found,discovery=referenced_catalogs_validation(report['metadata'],discovered_targets,report['discovery'])
    if [s['stepId'] for s in report['steps']]!=['exact-metadata','claims-and-reservations','filesystem-capacity']:raise HandoverError('steps-invalid')
    for s in report['steps']:
        if set(s)!={'stepId','exitCode','status','durationSeconds','reason'} or s['exitCode'] not in (0,2) or s['status']!=('passed' if s['exitCode']==0 else 'blocked') or not safe_token(s['reason']) or type(s['durationSeconds']) not in (int,float) or not math.isfinite(s['durationSeconds']) or not 0<=s['durationSeconds']<=3600:raise HandoverError('step-invalid')
    if report['overallStatus']!=('observations-complete' if all(s['exitCode']==0 for s in report['steps']) else 'incomplete'):raise HandoverError('overall-status-invalid')
    if len(report['capacity'])!=len(FIXED_CAPACITY):raise HandoverError('capacity-count-invalid')
    for row,(label,path) in zip(report['capacity'],FIXED_CAPACITY):
        if set(row)!={'targetId','path','access','availableBytes','availableInodes','readOnly'} or row['targetId']!=label or row['path']!=path or row['access'] not in ACCESS_STATES:raise HandoverError('capacity-invalid')
        for k in ('availableBytes','availableInodes'):
            if row[k] is not None:_uint(row[k])
        if row['readOnly'] is not None and type(row['readOnly']) is not bool:raise HandoverError('capacity-flag-invalid')
    cov=report['coverage']
    if set(cov)!={'previousSnapshotCommit','previousMatchedPins','previousPendingPrimaryMatches','previousMaximumLedgerSequence','matchedPins','pendingPrimaryMatches','requiredFields','projectionGaps','catalogueScope','ownershipClearance','runnerOutputCapacityRequired'} or cov['previousSnapshotCommit']!='24fc839d44b2e171fec08e3fe6d1622fd4d25a49' or cov['previousMatchedPins']!=49 or cov['previousPendingPrimaryMatches']!=28 or cov['previousMaximumLedgerSequence']!=9395 or cov['requiredFields']!=list(REQUIRED_FIELDS) or cov['ownershipClearance'] is not False or cov['runnerOutputCapacityRequired'] is not False or cov['catalogueScope']!='explicit-references-from-four-hash-matched-receipts-only':raise HandoverError('coverage-invalid')
    if cov['projectionGaps']!={r['targetId']:list(REQUIRED_FIELDS) if not r['reconciliation'] else r['reconciliation']['unavailableFields'] for r in report['metadata']}:raise HandoverError('coverage-gaps-invalid')
    for k in ('matchedPins','pendingPrimaryMatches'):_uint(cov[k])
    if report['totalMetadataBytesRead']!=sum(r['metadataBytesRead'] for r in report['metadata']+report['discoveredMetadata']) or report['totalMetadataBytesRead']>MAX_TOTAL_READ:raise HandoverError('read-budget-invalid')
    if len(canonical(report))>MAX_SNAPSHOT:raise HandoverError('snapshot-size-limit')
    return report


def referenced_catalogs_validation(observations,targets,discovery):
    references=[ref for r in observations if r['pinStatus']=='match' and r['owner'] in (4,11,13,35) and r['targetId'].endswith('-primary') and r['reconciliation'] for ref in r['reconciliation']['metadataReferences']]
    if set(discovery)!={'roots','recognizedFiles','entriesExamined','scopeExhaustive','claimsCatalogIdentified','reservationsCatalogIdentified','unidentifiedIsEmpty'} or discovery['scopeExhaustive'] is not False or discovery['unidentifiedIsEmpty'] is not False or discovery['recognizedFiles']!=len(targets) or len(targets)>MAX_REFERENCE_FILES or _uint(discovery['entriesExamined'])>MAX_REFERENCE_ENTRIES+1:raise HandoverError('reference-discovery-invalid')
    for target in targets:
        ref=target['reference']
        if ref not in references or not (target['path']==ref['path'] or ref['directory'] and str(Path(target['path']).parent)==ref['path']):raise HandoverError('unbound-reference')
    for row in discovery['roots']:
        if set(row)!={'path','category','sourceTargetId','sourceMetadataSHA256','state','entriesExamined'} or row['state'] not in ACCESS_STATES|{'entry-limit','file-limit'} or not any(all(row[k]==ref[k] for k in ('path','category','sourceTargetId','sourceMetadataSHA256')) for ref in references):raise HandoverError('reference-root-invalid')
        _uint(row['entriesExamined'])
    return targets,discovery


def validate_imported_snapshot(report):
    """Pure validation: no file, process, directory, or network access."""
    targets=[]
    for row in report.get('discoveredMetadata',[]):
        targets.append({k:row[k] for k in ('targetId','path','expectedSHA256','owner','heldBodyRead','category','reference')} | {'mode':row['readMode']})
    return validate_snapshot(report,cutover(),exact_targets(cutover()),targets)


def github_file_bytes(api, item, maximum):
    if item.get('type')!='file' or type(item.get('size')) is not int or not 0<=item['size']<=maximum or not re.fullmatch('[a-f0-9]{40}',item.get('sha','')):
        raise HandoverError('github-file-binding-invalid')
    encoded=item
    if item.get('encoding')=='none':
        encoded=api.call('GET','repos/'+REPOSITORY+'/git/blobs/'+item['sha'])
        if encoded.get('sha')!=item['sha'] or encoded.get('size')!=item['size']:raise HandoverError('github-blob-binding-invalid')
    if encoded.get('encoding')!='base64':raise HandoverError('github-file-encoding-invalid')
    raw=base64.b64decode(encoded.get('content','').replace('\n',''),validate=True)
    if len(raw)!=item['size'] or git_blob_sha(raw)!=item['sha']:raise HandoverError('github-file-bytes-invalid')
    return raw


def local_directory():
    # Newly created, private output directory only. Never chmod an existing path.
    home = Path.home()
    fd = _open_exact(str(home), directory=True)
    os.close(fd)
    return Path(tempfile.mkdtemp(prefix='offmenu-custody-', dir=home))


def save_local(directory, name, payload):
    if name not in {'snapshot.json', 'outcome.json'} or len(payload) > MAX_SNAPSHOT:
        raise HandoverError('local-output-invalid')
    fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def bounded_process(command, payload, env, timeout=25):
    """Bound both pipes while draining, and stop only this script's own child."""
    process = subprocess.Popen(command, stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    output, errors, position = bytearray(), bytearray(), 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for stream, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, label)
            if payload is not None:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                for key, _ in selector.select(min(remaining, 0.2)):
                    if key.data == 'stdin':
                        try:
                            sent = os.write(key.fileobj.fileno(), payload[position:position + 65536])
                            position += sent
                        except BrokenPipeError:
                            position = len(payload)
                        if position == len(payload):
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                    else:
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        target = output if key.data == 'stdout' else errors
                        if len(target) + len(data) > MAX_API:
                            raise HandoverError('github-response-bound')
                        target.extend(data)
        code = process.wait(timeout=max(0.01, deadline-time.monotonic()))
        return code, bytes(output), bytes(errors)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


class GitHub:
    def __init__(self):
        self.gh = shutil.which('gh')
        if not self.gh:
            raise HandoverError('gh-unavailable-local-snapshot-retained')
    def call(self, method, path, payload=None, absent=False):
        # gh resolves its existing auth internally. No auth status/token/login call.
        if not path.startswith(('repos/' + REPOSITORY + '/', 'repos/' + REPOSITORY)) and path != 'user':
            raise HandoverError('github-target-rejected')
        command = [self.gh, 'api', '--hostname', 'github.com', '--method', method, path]
        if payload is not None:
            command += ['--input', '-']
        env = os.environ.copy()
        env.update(GH_PROMPT_DISABLED='1', GIT_TERMINAL_PROMPT='0', GH_PAGER='cat')
        try:
            returncode, stdout, stderr = bounded_process(command, None if payload is None else canonical(payload), env)
        except (OSError, subprocess.TimeoutExpired):
            raise HandoverError('github-read-failed' if method == 'GET' else 'github-mutation-outcome-uncertain') from None
        try:
            data = _json(stdout)
        except (ValueError, UnicodeError):
            raise HandoverError('github-response-invalid') from None
        if returncode:
            if method == 'GET' and absent and isinstance(data, dict) and str(data.get('status')) == '404':
                return None
            # No mutation is blindly repeated, including a transport/timeout failure.
            raise HandoverError('github-read-failed' if method == 'GET' else 'github-mutation-outcome-uncertain')
        return data


def git_blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def publish(report, raw, api=None):
    api = api or GitHub()
    user = api.call('GET', 'user')
    repo = api.call('GET', 'repos/' + REPOSITORY)
    if user.get('id') != OWNER_ID or repo.get('id') != REPOSITORY_ID or repo.get('full_name') != REPOSITORY or repo.get('private') is not True or repo.get('owner', {}).get('id') != OWNER_ID or repo.get('permissions', {}).get('push') is not True:
        raise HandoverError('github-private-owner-repository-verification-failed')
    ref_path = 'repos/' + REPOSITORY + '/git/ref/heads/' + DEST_BRANCH
    ref = api.call('GET', ref_path, absent=True)
    head = BASE_SHA if ref is None else ref.get('object', {}).get('sha')
    if not isinstance(head, str) or not re.fullmatch(r'[0-9a-f]{40}', head):
        raise HandoverError('github-head-invalid')
    if ref is not None and head != BASE_SHA:
        compared = api.call('GET', 'repos/' + REPOSITORY + '/compare/' + BASE_SHA + '...' + head)
        if compared.get('status') not in ('ahead', 'identical'):
            raise HandoverError('snapshot-branch-unrelated')
    parent = api.call('GET', 'repos/' + REPOSITORY + '/git/commits/' + head)
    tree = parent.get('tree', {}).get('sha')
    if parent.get('sha') != head or not isinstance(tree, str) or not re.fullmatch(r'[0-9a-f]{40}', tree):
        raise HandoverError('github-parent-invalid')
    digest = hashlib.sha256(raw).hexdigest()
    stamp = report['observedAt'].replace('-', '').replace(':', '')
    snapshot_path = DEST_ROOT + '/snapshots/' + stamp + '-' + digest[:16] + '.json'
    pointer_path = DEST_ROOT + '/current.json'
    pointer = {'schemaVersion': 'offmenu-owner-custody-pointer/1', 'snapshotPath': snapshot_path,
               'snapshotSHA256': digest, 'observedAt': report['observedAt'],
               'cutoverSHA256': CUTOVER_SHA256, 'sourceBaseSHA': BASE_SHA,
               'snapshotIsLiveOwnershipClearance': False}
    old = api.call('GET', 'repos/' + REPOSITORY + '/contents/' + pointer_path + '?ref=' + head, absent=True)
    if old is not None:
        try:
            if old.get('type') != 'file' or old.get('encoding') != 'base64' or type(old.get('size')) is not int or old['size'] > 4096:
                raise ValueError()
            previous = _json(base64.b64decode(old['content'].replace('\n', ''), validate=True))
            if previous.get('schemaVersion') != pointer['schemaVersion'] or previous.get('cutoverSHA256') != CUTOVER_SHA256 or previous.get('sourceBaseSHA') != BASE_SHA or previous.get('snapshotIsLiveOwnershipClearance') is not False:
                raise ValueError()
            if timestamp(previous['observedAt']) > report['observedAt']:
                raise HandoverError('newer-snapshot-already-published')
            old_path = previous.get('snapshotPath')
            if not isinstance(old_path, str) or not re.fullmatch(re.escape(DEST_ROOT) + r'/snapshots/\d{8}T\d{6}Z-[a-f0-9]{16}\.json', old_path) or not re.fullmatch(r'[a-f0-9]{64}', previous.get('snapshotSHA256', '')):
                raise ValueError()
            prior_file = api.call('GET', 'repos/' + REPOSITORY + '/contents/' + old_path + '?ref=' + head)
            prior_raw = github_file_bytes(api, prior_file, MAX_SNAPSHOT)
            if hashlib.sha256(prior_raw).hexdigest() != previous['snapshotSHA256']:
                raise HandoverError('prior-publication-unverified-no-overwrite')
        except (KeyError, ValueError, TypeError):
            raise HandoverError('existing-pointer-unrecognized') from None
    existing = api.call('GET', 'repos/' + REPOSITORY + '/contents/' + snapshot_path + '?ref=' + head, absent=True)
    if existing is not None:
        if existing.get('sha') != git_blob_sha(raw) or existing.get('size') != len(raw):
            raise HandoverError('immutable-snapshot-path-collision')
        if old is not None and previous == pointer:
            return {'status': 'verified-existing', 'commit': head, 'snapshotPath': snapshot_path,
                    'snapshotSHA256': digest, 'url': 'https://github.com/' + REPOSITORY + '/blob/' + head + '/' + snapshot_path}
        raise HandoverError('existing-snapshot-pointer-differs-no-overwrite')
    tree_result = api.call('POST', 'repos/' + REPOSITORY + '/git/trees',
                           {'base_tree': tree, 'tree': [{'path': snapshot_path, 'mode': '100644', 'type': 'blob', 'content': raw.decode()},
                                                      {'path': pointer_path, 'mode': '100644', 'type': 'blob', 'content': canonical(pointer).decode() + '\n'}]})
    new_tree = tree_result.get('sha')
    if not isinstance(new_tree, str) or not re.fullmatch(r'[0-9a-f]{40}', new_tree):
        raise HandoverError('github-tree-unverified')
    commit = api.call('POST', 'repos/' + REPOSITORY + '/git/commits',
                      {'message': 'Retain bounded owner custody snapshot [skip ci]', 'tree': new_tree, 'parents': [head]})
    new_sha = commit.get('sha')
    if not isinstance(new_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', new_sha):
        raise HandoverError('github-commit-unverified')
    # Recheck the lease immediately before the only visible ref mutation.
    current = api.call('GET', ref_path, absent=True)
    if (current is None) != (ref is None) or current is not None and current.get('object', {}).get('sha') != head:
        raise HandoverError('snapshot-branch-changed-no-retry')
    if ref is None:
        api.call('POST', 'repos/' + REPOSITORY + '/git/refs', {'ref': 'refs/heads/' + DEST_BRANCH, 'sha': new_sha})
    else:
        # Parent=head and force=false make a concurrent sibling update fail closed.
        api.call('PATCH', 'repos/' + REPOSITORY + '/git/refs/heads/' + DEST_BRANCH, {'sha': new_sha, 'force': False})
    final = api.call('GET', ref_path)
    actual = api.call('GET', 'repos/' + REPOSITORY + '/contents/' + snapshot_path + '?ref=' + new_sha)
    current_pointer = api.call('GET', 'repos/' + REPOSITORY + '/contents/' + pointer_path + '?ref=' + new_sha)
    pointer_raw = canonical(pointer) + b'\n'
    if final.get('object', {}).get('sha') != new_sha or actual.get('sha') != git_blob_sha(raw) or actual.get('size') != len(raw) or current_pointer.get('sha') != git_blob_sha(pointer_raw):
        raise HandoverError('publication-readback-unverified')
    return {'status': 'published-and-verified', 'commit': new_sha, 'snapshotPath': snapshot_path,
            'snapshotSHA256': digest, 'url': 'https://github.com/' + REPOSITORY + '/blob/' + new_sha + '/' + snapshot_path}


def owner_main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-only', action='store_true', help='Retain the sanitized report locally without GitHub publication.')
    args = parser.parse_args(argv)
    if os.getuid() == 0 or os.geteuid() == 0:
        print('Run this with your normal account, without sudo. No work was performed.')
        return 3
    directory = None
    outcome = {'schemaVersion': 'offmenu-owner-handover-outcome/1', 'snapshotSaved': False,
               'publication': {'status': 'not-attempted'}, 'steps': [], 'exitCode': 3}
    try:
        baseline = cutover()
        directory = local_directory()
        report = collect_snapshot(baseline)
        raw = canonical(report) + b'\n'
        save_local(directory, 'snapshot.json', raw)
        outcome.update(snapshotSaved=True, snapshotSHA256=hashlib.sha256(raw).hexdigest(),
                       observedAt=report['observedAt'], observationStatus=report['overallStatus'], steps=report['steps'])
        begin = time.monotonic()
        if args.local_only:
            outcome['publication'] = {'status': 'local-only-requested'}
            outcome['steps'].append(step('github-publication', 2, begin, 'local-only-requested'))
        else:
            try:
                outcome['publication'] = publish(report, raw)
                outcome['steps'].append(step('github-publication', 0, begin, 'private-snapshot-readback-verified'))
            except HandoverError as error:
                outcome['publication'] = {'status': 'local-fallback', 'reason': str(error)}
                outcome['steps'].append(step('github-publication', 2, begin, str(error)))
        outcome['exitCode'] = 0 if all(s['exitCode'] == 0 for s in outcome['steps']) else 2
    except (HandoverError, OSError, ValueError, TypeError, KeyError, RecursionError):
        outcome['fatalReason'] = 'handover-incomplete-no-raw-error-disclosed'
        outcome['exitCode'] = 3
    if directory is not None:
        try:
            save_local(directory, 'outcome.json', canonical(outcome) + b'\n')
        except (OSError, HandoverError):
            print('Could not retain the full outcome. Existing files were not overwritten.')
            return 3
        print('Sanitized local report: ' + str(directory / 'snapshot.json') if outcome['snapshotSaved'] else 'Snapshot was not completed; diagnostics: ' + str(directory / 'outcome.json'))
        if outcome['publication']['status'] in ('published-and-verified', 'verified-existing'):
            print('Verified private snapshot: ' + outcome['publication']['url'])
        else:
            print('No GitHub publication was confirmed. Keep the local report and outcome.json.')
        print('Full batch exit code: ' + str(outcome['exitCode']) + '. This snapshot does not clear ownership, holds, or acquisition.')
    else:
        print('Handover could not create its private local report. No permissions or credentials were changed.')
    return outcome['exitCode']


if __name__ == '__main__':
    raise SystemExit(owner_main())
