"""Independent private retained-input denominator/ID witness. No acquisition.

Reviewed Python contracts only, never JSON-to-contract loading. IDs come from
source fields, not product records or projection functions. Reuses custody/path
primitives and the bounded ZIP-directory reader, not candidate parsing/projection.
"""
from dataclasses import asdict, dataclass
from contextlib import nullcontext
from datetime import datetime
import csv
import gzip
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile
import time
import zipfile
import zlib

from .acceptance import Asset, _valid_asset, fingerprint
from .core import RefreshError, canonical, digest, safe_path, strict_json
from .national_tabular import bundle_files, valid_input_name
from .product_adapters import _zip_metadata

VERSION = 'offmenu-product-input-witness/1'
OPERATION = 'private-retained-source-count-id-witness'
CONTROL_SLACK = 1024**2


@dataclass(frozen=True)
class Table:
    member: str
    columns: tuple
    key: tuple = ()  # Explicitly keyless tables still contribute every row.
    references: tuple = ()  # (local columns tuple, target member), exact native keys


@dataclass(frozen=True)
class WitnessContract:
    source_id: str
    release_id: str
    scope_id: str
    original: Asset
    rights_evidence: Asset
    scope_evidence: Asset
    clock_evidence: Asset
    permitted_operations: frozenset
    tables: tuple = ()
    members: tuple = ()  # Every archive file, including non-CSV companions.
    holds: tuple = ()
    original_acquired_at: str | None = None
    fixture: bool = False


@dataclass(frozen=True)
class WitnessLimits:
    max_input_bytes: int = 64 * 1024**2
    max_expanded_bytes: int = 256 * 1024**2
    max_line_bytes: int = 8 * 1024**2
    max_id_bytes: int = 64
    max_rows: int = 1_000_000
    max_database_bytes: int = 64 * 1024**2
    max_diagnostic_bytes: int = 64 * 1024**2
    max_output_bytes: int = 1024**2
    max_archive_members: int = 64
    max_seconds: int = 3600
    min_free_bytes: int = 20 * 1024**3


class _Stop(Exception):
    pass


class _VerifiedOriginal:
    """Keep the verified regular descriptor for both hashing and parsing."""
    def __init__(self, path, asset, limits, deadline):
        self.path, self.asset, self.limits, self.deadline = safe_path(path), asset, limits, deadline
        self.stream = None
        self._deadline()
        before = self.path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size != asset.bytes:
            raise RefreshError('witness-original-custody-mismatch')
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or self._signature(before) != self._signature(opened):
                raise RefreshError('witness-original-custody-mismatch')
            self.identity = self._signature(opened)
            self.stream = os.fdopen(fd, 'rb')
        except BaseException:
            os.close(fd)
            raise

    @staticmethod
    def _signature(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def _deadline(self):
        if time.monotonic() >= self.deadline:
            raise RefreshError('witness-original-duration-limit')

    def check(self):
        self._deadline()
        current = safe_path(self.path).lstat()
        opened = os.fstat(self.stream.fileno())
        if (not stat.S_ISREG(current.st_mode) or self._signature(current) != self.identity
                or self._signature(opened) != self.identity):
            raise RefreshError('witness-original-custody-mismatch')

    def read(self, size=-1):
        self.check()
        if size < 0:
            size = self.asset.bytes - self.stream.tell()
            if size > self.limits.max_archive_members * 65536:
                raise RefreshError('witness-original-unbounded-read')
        data = self.stream.read(size)
        self.check()
        return data

    def seek(self, *args):
        self.check()
        return self.stream.seek(*args)

    def tell(self):
        return self.stream.tell()

    def seekable(self):
        return True

    def stat(self):
        self.check()
        return os.fstat(self.stream.fileno())

    def open(self, mode):
        if mode != 'rb':
            raise RefreshError('witness-original-readonly-required')
        self.check()
        return nullcontext(self)  # ZIP-directory helper borrows this descriptor.

    def verify(self):
        self.seek(0)
        h, size = hashlib.sha256(), 0
        while True:
            block = self.read(min(1024**2, self.asset.bytes - size + 1))
            if not block:
                break
            size += len(block)
            if size > self.asset.bytes or size > self.limits.max_input_bytes:
                raise RefreshError('witness-original-custody-mismatch')
            h.update(block)
        if size != self.asset.bytes or h.hexdigest() != self.asset.sha256:
            raise RefreshError('witness-original-custody-mismatch')
        self.seek(0)

    def close(self):
        self.stream.close()


def _publish_output(pending, destination):
    """Rollback only links and directory still belonging to this invocation."""
    destination.mkdir(mode=0o700)
    claimed = destination.lstat()
    identity = (claimed.st_dev, claimed.st_ino)
    directory = None
    names = ('diagnostics.jsonl', 'result.json')
    own = {}
    try:
        directory = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened = os.fstat(directory)
        if (opened.st_dev, opened.st_ino) != identity:
            raise RefreshError('witness-publication-custody-changed')
        for name in names:
            info = (pending/name).lstat()
            if not stat.S_ISREG(info.st_mode):
                raise RefreshError('witness-publication-custody-changed')
            own[name] = (info.st_dev, info.st_ino)
        for name in names:
            current = safe_path(destination).lstat()
            if (current.st_dev, current.st_ino) != identity:
                raise RefreshError('witness-publication-custody-changed')
            os.link(pending/name, name, dst_dir_fd=directory, follow_symlinks=False)
            linked = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if not stat.S_ISREG(linked.st_mode) or (linked.st_dev, linked.st_ino) != own[name]:
                raise RefreshError('witness-publication-custody-changed')
        current = safe_path(destination).lstat()
        if (current.st_dev, current.st_ino) != identity:
            raise RefreshError('witness-publication-custody-changed')
    except BaseException:
        if directory is not None:
            for name in names:
                try:
                    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                    if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == own.get(name):
                        os.unlink(name, dir_fd=directory)
                except OSError:
                    pass  # Never broaden cleanup when custody or IO is uncertain.
        try:
            current = destination.lstat()
            if stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == identity:
                destination.rmdir()  # Refuses any foreign/unknown child.
        except OSError:
            pass
        raise
    finally:
        if directory is not None:
            os.close(directory)


def _indexed(db, sql, parameters=()):
    # All ordering is supplied by the bounded on-disk primary-key indexes.
    # Refuse a planner change that would introduce unbudgeted sort scratch/RAM.
    if any('TEMP B-TREE' in row[3] for row in db.execute('EXPLAIN QUERY PLAN ' + sql, parameters)):
        raise _Stop('unexpected-sort-scratch')
    return db.execute(sql, parameters)


def _contract_value(contract):
    value = asdict(contract)
    value['permitted_operations'] = sorted(contract.permitted_operations)
    return value


def _metadata_deadline(deadline):
    if time.monotonic() >= deadline:
        raise RefreshError('witness-evidence-duration-limit')


def _verified_metadata_bytes(asset, root, deadline):
    """Verify one bounded descriptor buffer; never reopen it for JSON parsing."""
    _metadata_deadline(deadline)
    if not _valid_asset(asset) or not 0 < asset.bytes <= 1024**2:
        raise RefreshError('witness-evidence-custody-mismatch')
    path = safe_path(root / asset.path)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size != asset.bytes:
            raise RefreshError('witness-evidence-custody-mismatch')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            _metadata_deadline(deadline)
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or signature(before) != signature(opened):
                raise RefreshError('witness-evidence-custody-mismatch')
            chunks, size = [], 0
            while size <= asset.bytes:
                _metadata_deadline(deadline)
                block = os.read(fd, min(65536, asset.bytes - size + 1))
                _metadata_deadline(deadline)
                if not block:
                    break
                chunks.append(block)
                size += len(block)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        current = safe_path(path).lstat()
        raw = b''.join(chunks)
        if (not stat.S_ISREG(current.st_mode)
                or signature(before) != signature(after) or signature(after) != signature(current)
                or len(raw) != asset.bytes or hashlib.sha256(raw).hexdigest() != asset.sha256):
            raise RefreshError('witness-evidence-custody-mismatch')
        _metadata_deadline(deadline)
        return raw
    except OSError:
        raise RefreshError('witness-evidence-custody-mismatch') from None


def _preflight(contract, root, limits, deadline, external_original=False):
    if (contract.source_id not in ('off', 'usda-files')
            or not all(isinstance(s, str) and s for s in (contract.release_id, contract.scope_id))
            or type(contract.fixture) is not bool or contract.holds
            or not {'retain', 'parse', 'transform'} <= contract.permitted_operations
            or any(type(v) is not int or v <= 0 for v in asdict(limits).values())
            or limits.max_database_bytes < 65536 or limits.max_output_bytes < 65536):
        raise RefreshError('witness-contract-or-rights-invalid')
    if not contract.fixture:
        gib = 1024**3
        off = contract.source_id == 'off'
        if (limits.min_free_bytes < 20*gib or limits.max_id_bytes > 64
                or limits.max_database_bytes > (8 if off else 24)*gib
                or limits.max_diagnostic_bytes > (2 if off else 4)*gib - 2*1024**2
                or limits.max_output_bytes > 1024**2
                or limits.max_archive_members > 64
                or limits.max_database_bytes + limits.max_diagnostic_bytes + limits.max_output_bytes + CONTROL_SLACK > (10 if off else 28)*gib
                or limits.max_rows > (6_000_000 if off else 40_000_000)
                or limits.max_seconds > (24 if off else 12)*3600
                or limits.max_line_bytes > 8*1024**2
                or limits.max_expanded_bytes > (192 if off else 4)*gib
                or limits.max_input_bytes > (14*gib if off else 512*1024**2)):
            raise RefreshError('witness-real-scope-budget-exceeded')
    assets = (contract.original, contract.rights_evidence, contract.scope_evidence, contract.clock_evidence)
    if (any(not isinstance(a, Asset) or not _valid_asset(a) for a in assets)
            or len({a.path for a in assets}) != 4
            or contract.original.bytes > limits.max_input_bytes
            or any(a.bytes > 1024**2 for a in assets[1:])):
        raise RefreshError('witness-assets-invalid')
    evidence_assets = assets[1:] if external_original else assets
    if bundle_files(root, {a.path for a in evidence_assets}) != {a.path for a in evidence_assets}:
        raise RefreshError('witness-bundle-set-mismatch')
    # Verify bounded evidence first; never use source JSON as an operation grant.
    metadata = {a.path: _verified_metadata_bytes(a, root, deadline) for a in assets[1:]}
    _metadata_deadline(deadline)
    scope = strict_json(metadata[contract.scope_evidence.path])
    _metadata_deadline(deadline)
    expected = {'operation': OPERATION, 'sourceId': contract.source_id,
                'releaseId': contract.release_id, 'scopeId': contract.scope_id,
                'original': asdict(contract.original),
                'rightsEvidenceSha256': contract.rights_evidence.sha256,
                'clockEvidenceSha256': contract.clock_evidence.sha256,
                'originalAcquiredAt': contract.original_acquired_at,
                'denominator': 'full-declared-input',
                'tables': [asdict(t) for t in contract.tables], 'members': list(contract.members)}
    if not isinstance(scope, dict) or any(k not in scope or canonical(scope[k]) != canonical(v) for k, v in expected.items()):
        raise RefreshError('witness-scope-binding-mismatch')
    clock = strict_json(metadata[contract.clock_evidence.path])
    _metadata_deadline(deadline)
    sources = clock.get('sources', []) if isinstance(clock, dict) else []
    matching = [s for s in sources if isinstance(s, dict) and s.get('sourceId') == contract.source_id
                and s.get('originalSha256') == contract.original.sha256
                and s.get('originalBytes') == contract.original.bytes]
    if (len(matching) != 1 or 'originalAcquiredAt' not in matching[0]
            or matching[0]['originalAcquiredAt'] != contract.original_acquired_at):
        raise RefreshError('witness-clock-evidence-mismatch')
    if contract.original_acquired_at is not None:
        date = datetime.fromisoformat(contract.original_acquired_at.replace('Z', '+00:00'))
        if date.utcoffset() is None:
            raise RefreshError('witness-clock-timezone-required')
    if contract.source_id == 'off':
        if contract.tables or contract.members:
            raise RefreshError('witness-off-scope-invalid')
    else:
        if (not contract.tables or len(contract.members) > limits.max_archive_members
                or len(set(contract.members)) != len(contract.members)
                or any(not valid_input_name(m) for m in contract.members)
                or len({t.member for t in contract.tables}) != len(contract.tables)
                or {t.member for t in contract.tables} != {m for m in contract.members if m.endswith('.csv')}
                or not {'food', 'nutrient', 'food_nutrient', 'branded_food'} <= {PurePosixPath(t.member).stem for t in contract.tables}):
            raise RefreshError('witness-usda-scope-invalid')
        by_member = {t.member: t for t in contract.tables}
        for t in contract.tables:
            if (not t.columns or len(set(t.columns)) != len(t.columns)
                    or any(not isinstance(s, str) or not s for s in t.columns)
                    or len(set(t.key)) != len(t.key) or not set(t.key) <= set(t.columns)
                    or any(not fields or not set(fields) <= set(t.columns) or target not in by_member
                           or len(fields) != len(by_member[target].key) for fields, target in t.references)):
                raise RefreshError('witness-table-contract-invalid')
        for name, key in (('food', ('fdc_id',)), ('branded_food', ('fdc_id',)), ('nutrient', ('id',)), ('food_nutrient', ('id',))):
            selected = [t for t in contract.tables if PurePosixPath(t.member).stem == name]
            if len(selected) != 1 or selected[0].key != key:
                raise RefreshError('witness-required-native-key-missing')
        food = next(t.member for t in contract.tables if PurePosixPath(t.member).stem == 'food')
        nutrient = next(t.member for t in contract.tables if PurePosixPath(t.member).stem == 'nutrient')
        for t in contract.tables:
            if PurePosixPath(t.member).stem in ('branded_food', 'food_nutrient'):
                required = {(('fdc_id',), food)}
                if PurePosixPath(t.member).stem == 'food_nutrient':
                    required.add((('nutrient_id',), nutrient))
                if not required <= set(t.references):
                    raise RefreshError('witness-required-join-missing')
    _metadata_deadline(deadline)
    return assets


class _Run:
    def __init__(self, limits, deadline, db, diagnostic, scratch):
        self.limits, self.deadline, self.db = limits, deadline, db
        self.diagnostic, self.scratch = diagnostic, scratch
        self.expanded = self.rows = self.diagnostic_bytes = 0
        self.diagnostic_hash = hashlib.sha256()
        self.tables = {}

    def guard(self):
        if time.monotonic() >= self.deadline:
            raise _Stop('duration-limit')
        if shutil.disk_usage(self.scratch).free < self.limits.min_free_bytes:
            raise _Stop('filesystem-floor')
        if os.statvfs(self.scratch).f_favail < 10000:
            raise _Stop('filesystem-inode-floor')

    def note(self, table, row, category, code):
        data = canonical({'table': table, 'row': row, 'category': category, 'code': code})
        if self.diagnostic_bytes + len(data) > self.limits.max_diagnostic_bytes:
            raise _Stop('diagnostic-byte-limit')
        self.diagnostic.write(data)
        self.diagnostic_hash.update(data)
        self.diagnostic_bytes += len(data)

    def lines(self, stream):
        while True:
            self.guard()
            raw = stream.readline(self.limits.max_line_bytes + 1)
            self.guard()
            if not raw:
                return
            self.expanded += len(raw)
            if len(raw) > self.limits.max_line_bytes or self.expanded > self.limits.max_expanded_bytes:
                raise _Stop('expanded-or-line-limit')
            yield raw

    def start(self, table):
        self.tables[table] = {k: 0 for k in ('rows', 'valid', 'duplicate', 'invalid', 'quarantined',
                                            'keyless', 'conflictingDuplicate', 'joinFailures')}

    def row(self, table):
        self.guard()
        if self.rows >= self.limits.max_rows:
            raise _Stop('row-limit')
        self.rows += 1
        self.tables[table]['rows'] += 1
        return self.tables[table]['rows']

    def bad(self, table, ordinal, category, code):
        self.tables[table][category] += 1
        self.note(table, ordinal, category, code)

    def identity(self, values):
        if any(not isinstance(v, str) or not v or v != v.strip() for v in values):
            return None
        key = values[0] if len(values) == 1 else canonical(values).decode().rstrip('\n')
        if len(key.encode()) > self.limits.max_id_bytes:
            raise _Stop('native-id-byte-limit')
        return key

    def put(self, table, ordinal, body, key, references=()):
        counts = self.tables[table]
        if key is None:
            counts['keyless'] += 1
        else:
            body_hash = hashlib.sha256(body).hexdigest()
            old = self.db.execute('SELECT body_hash FROM ids WHERE tab=? AND key=?', (table, key)).fetchone()
            if old:
                counts['duplicate'] += 1
                conflict = old[0] != body_hash
                counts['conflictingDuplicate'] += int(conflict)
                self.note(table, ordinal, 'duplicate', 'conflicting-native-id' if conflict else 'repeated-native-id')
            else:
                self.db.execute('INSERT INTO ids VALUES (?,?,?)', (table, key, body_hash))
                counts['valid'] += 1
        if key is None:
            counts['valid'] += 1
        for index, (target, value) in enumerate(references):
            self.db.execute('INSERT INTO refs VALUES (?,?,?,?,?)', (table, ordinal, index, target, value))


def _off(run, source):
    run.start('products')
    with gzip.GzipFile(fileobj=source, mode='rb') as stream:
        for raw in run.lines(stream):
            ordinal = run.row('products')
            try:
                row = strict_json(raw.decode('utf-8'))
                if not isinstance(row, dict):
                    raise ValueError()
                canonical(row)  # Detect numeric overflow without retaining any body.
            except (ValueError, UnicodeError, RecursionError, OverflowError):
                run.bad('products', ordinal, 'invalid', 'json-or-utf8-invalid')
                continue
            code = row.get('code')
            if not isinstance(code, str) or not re.fullmatch('[0-9]{4,32}', code):
                run.bad('products', ordinal, 'quarantined', 'native-code-invalid')
                continue
            run.put('products', ordinal, canonical(row), run.identity([code]))


def _usda(run, source, contract):
    _zip_metadata(source, run.limits)
    specs = {t.member: t for t in contract.tables}
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        names = [m.filename for m in infos if not m.is_dir()]
        if (len(infos) > run.limits.max_archive_members or len(set(names)) != len(names)
                or set(names) != set(contract.members)
                or any(not valid_input_name(m.filename.rstrip('/')) or m.flag_bits & 1 for m in infos)
                or sum(m.file_size for m in infos) > run.limits.max_expanded_bytes):
            raise _Stop('archive-inventory-or-expansion-mismatch')
        for name in sorted(names):
            run.guard()
            with archive.open(name) as stream:
                if name not in specs:
                    # Include CRC/integrity/byte traversal of every non-CSV companion.
                    while True:
                        run.guard()
                        block = stream.read(1024 * 1024)
                        run.guard()
                        if not block:
                            break
                        run.expanded += len(block)
                        if run.expanded > run.limits.max_expanded_bytes:
                            raise _Stop('expanded-byte-limit')
                    continue
                spec = specs[name]
                run.start(name)
                record_bytes = 0
                first_line = True
                def lines():
                    nonlocal record_bytes, first_line
                    for raw in run.lines(stream):
                        record_bytes += len(raw)
                        if record_bytes > run.limits.max_line_bytes:
                            raise _Stop('csv-logical-record-byte-limit')
                        decoded = raw.decode('utf-8-sig' if first_line else 'utf-8')
                        first_line = False
                        yield decoded
                reader = csv.reader(lines(), strict=True)
                if next(reader, None) != list(spec.columns):
                    raise _Stop('csv-header-mismatch')
                while True:
                    record_bytes = 0
                    row = next(reader, None)
                    if row is None:
                        break
                    ordinal = run.row(name)
                    if len(row) != len(spec.columns):
                        run.bad(name, ordinal, 'invalid', 'csv-row-width')
                        continue
                    values = dict(zip(spec.columns, row))
                    key = run.identity([values[k] for k in spec.key]) if spec.key else None
                    if spec.key and key is None:
                        run.bad(name, ordinal, 'quarantined', 'native-key-missing')
                        continue
                    references = []
                    for fields, target in spec.references:
                        reference = run.identity([values[k] for k in fields])
                        references.append((target, reference))
                    run.put(name, ordinal, canonical(row), key, references)
    for table, ordinal, target, key in _indexed(run.db,
            'SELECT r.tab,r.row,r.target,r.key FROM refs r LEFT JOIN ids i '
            'ON i.tab=r.target AND i.key=r.key WHERE i.key IS NULL ORDER BY r.tab,r.row,r.n'):
        run.guard()
        run.tables[table]['joinFailures'] += 1
        run.note(table, ordinal, 'join', 'native-reference-missing')


def witness_retained_input(contract, bundle, destination, *, limits=WitnessLimits(), input_root=None):
    """Execute one exact reviewed private source witness; no candidate or activation.

    Preflight failures leave no output. Once started, terminal incomplete outputs
    retain diagnostics; only this call's private scratch DB is removed. Existing
    destinations are never changed/reused. Caller supplies a reconciled free-space
    floor including other outstanding commitments, and serial source admission.
    """
    root, destination = safe_path(bundle), safe_path(destination)
    originals = safe_path(input_root) if input_root is not None else root
    if (any(a == destination or a in destination.parents or destination in a.parents for a in (root, originals))
            or destination.exists()):
        raise RefreshError('witness-output-overlap-or-exists')
    if any(type(v) is not int or v <= 0 for v in asdict(limits).values()):
        raise RefreshError('witness-invalid-limits')
    deadline = time.monotonic() + limits.max_seconds
    assets = _preflight(contract, root, limits, deadline, input_root is not None)
    if (shutil.disk_usage(destination.parent).free < limits.min_free_bytes + limits.max_database_bytes + limits.max_diagnostic_bytes + limits.max_output_bytes + CONTROL_SLACK
            or os.statvfs(destination.parent).f_favail < 10000):
        raise RefreshError('witness-free-space-not-admitted')
    verified_original = _VerifiedOriginal(originals / contract.original.path, contract.original, limits, deadline)
    pending = None
    db = None
    try:
        verified_original.verify()
        pending = Path(tempfile.mkdtemp(prefix='.input-witness-', dir=destination.parent))
        db = sqlite3.connect(pending / 'keys.sqlite')
        db.execute('PRAGMA page_size=4096')
        db.execute('PRAGMA cache_size=-16384')
        db.execute('PRAGMA journal_mode=OFF')
        db.execute('PRAGMA temp_store=MEMORY')
        db.execute(f'PRAGMA max_page_count={limits.max_database_bytes // 4096}')
        db.execute('CREATE TABLE ids(tab TEXT,key TEXT,body_hash TEXT,PRIMARY KEY(tab,key)) WITHOUT ROWID')
        db.execute('CREATE TABLE refs(tab TEXT,row INTEGER,n INTEGER,target TEXT,key TEXT,PRIMARY KEY(tab,row,n)) WITHOUT ROWID')
        errors = set()
        complete = False
        with (pending / 'diagnostics.jsonl').open('xb') as diagnostic:
            run = _Run(limits, deadline, db, diagnostic, pending)
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
            try:
                if contract.source_id == 'off':
                    _off(run, verified_original)
                else:
                    _usda(run, verified_original, contract)
                db.commit()
                run.guard()
                verified_original.verify()
                for a in assets[1:]:
                    _verified_metadata_bytes(a, root, deadline)
                complete = True
            except _Stop as exc:
                errors.add(str(exc))
            except (ValueError, UnicodeError, OSError, EOFError, csv.Error, sqlite3.Error, zipfile.BadZipFile,
                    zlib.error, NotImplementedError, RuntimeError):
                errors.add('source-parser-storage-or-custody-failure')
            table_digests = {}
            expected_records = expected_ids = None
            eligible = complete and all(not sum(v[k] for k in ('duplicate', 'invalid', 'quarantined', 'joinFailures')) for v in run.tables.values())
            try:
                for table in sorted(run.tables):
                    h = hashlib.sha256()
                    for (key,) in _indexed(db, 'SELECT key FROM ids WHERE tab=? ORDER BY key COLLATE BINARY', (table,)):
                        run.guard()
                        h.update(canonical(key))
                    table_digests[table] = h.hexdigest()
                if eligible:
                    selected = 'products' if contract.source_id == 'off' else next(t.member for t in contract.tables if PurePosixPath(t.member).stem == 'food')
                    h, count = hashlib.sha256(), 0
                    for kind in ('nutrientProfile', 'product'):
                        for (key,) in _indexed(db, 'SELECT key FROM ids WHERE tab=? ORDER BY key COLLATE BINARY', (selected,)):
                            run.guard()
                            h.update(canonical(f'{contract.source_id}:{kind}:{key}'))
                            count += 1
                    expected_records, expected_ids = count, h.hexdigest()
            except (_Stop, sqlite3.Error):
                errors.add('digest-duration-or-storage-limit')
                complete = eligible = False
                expected_records = expected_ids = None
            if not eligible:
                expected_records = expected_ids = None
        db.close()
        db = None
        for name in ('keys.sqlite', 'keys.sqlite-journal'):
            (pending / name).unlink(missing_ok=True)
        for counts in run.tables.values():
            counts['unclassifiedRows'] = counts['rows'] - sum(counts[k] for k in ('valid', 'duplicate', 'invalid', 'quarantined'))
            if counts['unclassifiedRows']:
                complete = eligible = False
                expected_records = expected_ids = None
                errors.add('observed-row-disposition-incomplete')
        result = {'schemaVersion': VERSION, 'sourceId': contract.source_id, 'releaseId': contract.release_id,
                  'scopeId': contract.scope_id, 'contractSha256': fingerprint(_contract_value(contract)),
                  'original': asdict(contract.original),
                  'rightsEvidenceSha256': contract.rights_evidence.sha256,
                  'scopeEvidenceSha256': contract.scope_evidence.sha256,
                  'policySha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'limits': asdict(limits), 'fixture': contract.fixture,
                  'fullDenominatorTraversed': complete, 'eligibleCleanScopeWitness': eligible,
                  'unparsedTailPossible': not complete,
                  'rowsObserved': run.rows, 'expandedBytesObserved': run.expanded,
                  'tables': dict(sorted(run.tables.items())), 'tableNativeIdDigests': table_digests,
                  'expectedRecords': expected_records, 'expectedSortedIdSha256': expected_ids,
                  'diagnosticsSha256': run.diagnostic_hash.hexdigest(),
                  'diagnosticBytes': run.diagnostic_bytes, 'errors': sorted(errors),
                  'denominatorPolicy': 'valid/duplicate/invalid/quarantined are disjoint; keyless is a valid subset; joins orthogonal; incomplete digests are not admission evidence',
                  'nativeIdDigestPolicy': 'unique native keys, SQLite BINARY order, canonical JSON string plus LF; duplicate rows counted separately',
                  'csvFieldLimit': csv.field_size_limit(),
                  'accepted': False, 'countryComplete': False, 'publication': 'not-enabled',
                  'originalAcquiredAt': contract.original_acquired_at,
                  'clockEvidenceSha256': contract.clock_evidence.sha256,
                  'scratchLifecycle': 'private DB deleted after terminal result; diagnostics retained; no overwrite/reuse'}
        data = canonical(result)
        if len(data) > limits.max_output_bytes:
            raise RefreshError('witness-result-byte-limit')
        (pending / 'result.json').write_bytes(data)
        # Exclusive directory claim also handles a destination created during the
        # run. Publish the terminal receipt last; links cannot replace a file.
        _publish_output(pending, destination)
        shutil.rmtree(pending)
        pending = None
        return result
    finally:
        verified_original.close()
        if db is not None:
            db.close()
        if pending is not None:
            shutil.rmtree(pending)  # Only this call's fresh, private staging tree.
