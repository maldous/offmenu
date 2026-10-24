"""Bounded Linux file-identity boundary for caller-selected sealed snapshots.

This verifies carrier bytes, not source rights or admission authority. No cache,
snapshot discovery, SQLite deserialization, database copy or write is performed.
The Linux descriptor check is deliberate: a pathname hash alone cannot bind the
file SQLite actually opened. Unsupported platforms/ambiguous opens fail closed.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time

MAX_DATABASE_BYTES = 1073741824  # Existing barcode carrier ceiling, not SQL bytes.
MAX_RECEIPT_BYTES = 1048576
CHUNK_BYTES = 1048576
MAX_VERIFICATION_SECONDS = 10
MAX_DESCRIPTOR_ENTRIES = 4096
_SUFFIXES = ('-wal', '-shm', '-journal')


class SnapshotAccessError(ValueError):
    pass


def _need(ok, code):
    if not ok:
        raise SnapshotAccessError(code)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def _same(path, fd, identity):
    _need(_identity(os.fstat(fd)) == identity
          and _identity(os.stat(path, follow_symlinks=False)) == identity,
          'snapshot-file-identity-changed')


def _sealed(path):
    _need(not any(os.path.lexists(str(path) + s) for s in _SUFFIXES),
          'sealed-snapshot-required')


def _open_regular(path, ceiling):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode), 'snapshot-regular-file-required')
        _need(0 < st.st_size <= ceiling, 'snapshot-file-byte-limit')
        identity = _identity(st)
        _same(path, fd, identity)
        return fd, identity
    except BaseException:
        os.close(fd)
        raise


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, 'admission-duplicate-json-key')
        out[key] = value
    return out


def _constant(_):
    raise SnapshotAccessError('admission-nonfinite-json')


class _Verification:
    def __init__(self):
        self.bytes = 0
        self.seconds = 0.0
        self.hash_passes = 0

    def digest(self, fd, size):
        start = time.monotonic()
        h, count = hashlib.sha256(), 0
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            while True:
                _need(self.seconds + time.monotonic() - start <= MAX_VERIFICATION_SECONDS,
                      'snapshot-verification-time-limit')
                # The extra byte detects growth without an unbounded read.
                block = os.read(fd, min(CHUNK_BYTES, size - count + 1))
                if not block:
                    break
                count += len(block)
                self.bytes += len(block)
                _need(count <= size and self.bytes <= 2 * MAX_DATABASE_BYTES,
                      'snapshot-verification-byte-limit')
                h.update(block)
            _need(count == size, 'snapshot-file-size-changed')
            _need(self.seconds + time.monotonic() - start <= MAX_VERIFICATION_SECONDS,
                  'snapshot-verification-time-limit')
            self.hash_passes += 1
            return h.hexdigest()
        finally:
            self.seconds += time.monotonic() - start

    def report(self, size):
        return {'databaseBytes': size, 'maxDatabaseBytes': MAX_DATABASE_BYTES,
                'verificationBytesRead': self.bytes, 'hashPasses': self.hash_passes,
                'maxChunkBytes': CHUNK_BYTES, 'verificationSeconds': self.seconds,
                'maxVerificationSeconds': MAX_VERIFICATION_SECONDS,
                'connectionIdentity': 'linux-open-descriptor-matches-held-file',
                'queryBudgets': 'separate; unchanged SQL VM/time/row/source/output limits'}


def _regular_descriptors():
    """Exclude transient readdir descriptors; inspect regular files only."""
    out = {}
    with os.scandir('/proc/self/fd') as entries:
        for index, entry in enumerate(entries):
            _need(index < MAX_DESCRIPTOR_ENTRIES, 'snapshot-descriptor-scan-limit')
            try:
                fd = int(entry.name)
                st = os.fstat(fd)
                if stat.S_ISREG(st.st_mode):
                    out[fd] = _identity(st)
            except OSError:
                continue
    return out


@dataclass
class SnapshotAccess:
    db: sqlite3.Connection
    receipt: dict
    database_sha256: str
    verification: dict


@contextmanager
def verified_snapshot(admission_path, admission_sha256):
    """Yield exclusively owned immutable RO connection; validate before release.

    The caller must not expose its result until this context exits successfully.
    Receipt parsing uses the exact hashed bounded buffer. The receipt remains
    held and is checked again, alongside both held and actual SQLite file FDs.
    Verification time excludes the independent consumer SQL execution interval.
    """
    receipt_fd = database_fd = None
    db = None
    consumer_failed = False
    try:
        _need(_sha(admission_sha256), 'admission-hash-mismatch')
        receipt_path = Path(admission_path).absolute()
        try:
            receipt_fd, receipt_identity = _open_regular(receipt_path, MAX_RECEIPT_BYTES)
        except SnapshotAccessError as error:
            if str(error) == 'snapshot-file-byte-limit':
                raise SnapshotAccessError('admission-hash-mismatch') from error
            raise
        raw = os.read(receipt_fd, MAX_RECEIPT_BYTES + 1)
        _need(len(raw) == receipt_identity[2] and len(raw) <= MAX_RECEIPT_BYTES
              and hashlib.sha256(raw).hexdigest() == admission_sha256,
              'admission-hash-mismatch')
        _same(receipt_path, receipt_fd, receipt_identity)
        receipt = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        _need(type(receipt) is dict and type(receipt.get('state')) is str
              and receipt['state'].startswith('ACCEPTED_'), 'accepted-admission-required')
        artifact = receipt.get('artifact')
        _need(type(artifact) is dict and type(artifact.get('path')) is str
              and Path(artifact['path']).is_absolute() and _sha(artifact.get('sha256')),
              'admission-artifact-required')
        path = Path(artifact['path'])
        _sealed(path)
        database_fd, identity = _open_regular(path, MAX_DATABASE_BYTES)
        verifier = _Verification()
        _need(verifier.digest(database_fd, identity[2]) == artifact['sha256'],
              'database-hash-mismatch')
        _same(path, database_fd, identity)
        _sealed(path)
        _need(Path('/proc/self/fd').is_dir(), 'snapshot-connection-identity-unavailable')
        before = _regular_descriptors()
        db = sqlite3.connect('file:/proc/self/fd/' + str(database_fd)
                             + '?mode=ro&immutable=1', uri=True)
        after = _regular_descriptors()
        opened = [fd for fd in after if fd not in before or before[fd] != after[fd]]
        _need(len(opened) == 1 and after[opened[0]] == identity,
              'snapshot-connection-identity-mismatch')
        sqlite_fd = opened[0]
        _need(fcntl.fcntl(sqlite_fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY,
              'snapshot-read-only-required')
        _same(path, database_fd, identity)
        _sealed(path)
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA temp_store=MEMORY')
        access = SnapshotAccess(db, receipt, artifact['sha256'], {})
        try:
            yield access
        except BaseException:
            consumer_failed = True
            raise
        _need(_identity(os.fstat(sqlite_fd)) == identity, 'snapshot-connection-identity-changed')
        _same(path, database_fd, identity)
        _sealed(path)
        db.close()
        db = None
        _need(verifier.digest(database_fd, identity[2]) == artifact['sha256'],
              'database-changed-during-query')
        _same(path, database_fd, identity)
        _sealed(path)
        _same(receipt_path, receipt_fd, receipt_identity)
        os.lseek(receipt_fd, 0, os.SEEK_SET)
        _need(os.read(receipt_fd, MAX_RECEIPT_BYTES + 1) == raw,
              'admission-changed-during-query')
        _same(receipt_path, receipt_fd, receipt_identity)
        access.verification.update(verifier.report(identity[2]))
    except SnapshotAccessError:
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError, RecursionError) as error:
        if consumer_failed:
            raise
        raise SnapshotAccessError('snapshot-access-invalid') from error
    finally:
        if db is not None:
            db.close()
        for fd in (database_fd, receipt_fd):
            if fd is not None:
                os.close(fd)
