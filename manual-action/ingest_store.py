"""Additive source-faithful SQLite staging; never opens canonical stores for writes."""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import itertools
import os
from pathlib import Path
import sqlite3
import stat
import time
import uuid
from ingest_api import DOMAINS, BudgetExceeded, SourceChanged, source_key

SCHEMA_VERSION = 1

SCHEMA = '''
CREATE TABLE IF NOT EXISTS ingest_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (
 source_key TEXT NOT NULL, version TEXT NOT NULL, path TEXT NOT NULL,
 format TEXT, provider TEXT, license TEXT, custody_json TEXT,
 fingerprint_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 cursor INTEGER NOT NULL DEFAULT 0, written INTEGER NOT NULL DEFAULT 0,
 errors INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL,
 PRIMARY KEY(source_key,version));
CREATE TABLE IF NOT EXISTS records (
 source_key TEXT NOT NULL, source_version TEXT NOT NULL, record_id TEXT NOT NULL,
 row_number INTEGER NOT NULL, content_sha256 TEXT NOT NULL,
 payload_json TEXT NOT NULL, updated_at REAL NOT NULL,
 PRIMARY KEY(source_key,source_version,record_id),
 FOREIGN KEY(source_key,source_version) REFERENCES sources(source_key,version));
CREATE INDEX IF NOT EXISTS records_source_row ON records(source_key,source_version,row_number);
CREATE TABLE IF NOT EXISTS record_fields (
 source_key TEXT NOT NULL, source_version TEXT NOT NULL, record_id TEXT NOT NULL,
 field_path TEXT NOT NULL, value_type TEXT NOT NULL,
 text_value TEXT, number_value REAL,
 PRIMARY KEY(source_key,source_version,record_id,field_path),
 FOREIGN KEY(source_key,source_version,record_id)
 REFERENCES records(source_key,source_version,record_id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS fields_lookup ON record_fields(field_path,text_value);
CREATE TABLE IF NOT EXISTS relations (
 source_key TEXT NOT NULL, source_version TEXT NOT NULL, record_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL, kind TEXT NOT NULL, target_domain TEXT, target_id TEXT,
 detail_json TEXT NOT NULL,
 PRIMARY KEY(source_key,source_version,record_id,ordinal),
 FOREIGN KEY(source_key,source_version,record_id)
 REFERENCES records(source_key,source_version,record_id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS relations_target ON relations(target_domain,target_id);
CREATE VIEW IF NOT EXISTS logical_records AS SELECT record_id, COUNT(*) AS provenance_rows FROM records GROUP BY record_id;
CREATE TABLE IF NOT EXISTS source_errors (
 source_key TEXT NOT NULL, source_version TEXT NOT NULL, row_number INTEGER NOT NULL,
 error_class TEXT NOT NULL, updated_at REAL NOT NULL,
 PRIMARY KEY(source_key,source_version,row_number,error_class));
'''


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _fingerprint(source):
    """Metadata identity, not an unearned claim of full content verification."""
    path = Path(source['path'])
    st = path.stat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError('source_not_regular_file')
    sidecars={}
    if source.get('format') == 'sqlite' or path.suffix.lower() in ('.sqlite','.sqlite3','.db'):
        wal=Path(str(path)+'-wal')
        try:
            ws=wal.lstat()
            if not stat.S_ISREG(ws.st_mode):
                raise ValueError('unsafe_sqlite_sidecar')
            sidecars['wal']={'size':ws.st_size,'mtime_ns':ws.st_mtime_ns,'inode':ws.st_ino}
        except FileNotFoundError:
            sidecars['wal']=None
    return {'path': str(path.resolve()), 'device': st.st_dev, 'inode': st.st_ino,
            'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
            'declared_sha256': source.get('sha256'),
            'format': source.get('format'), 'adapter_version': source.get('adapter_version', 1),
            'sidecars':sidecars,'table':source.get('table'),'tables':source.get('tables')}


def _scalar_fields(value, prefix='', depth=0):
    # Preserve structure as JSON, index source fields including nested nutrient data.
    # Bound expansion of very large ingredient arrays; payload is never truncated.
    if depth > 8:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ('relations', 'raw_source', 'raw_source_json', 'source_payload', 'source_payload_json', 'source_record', 'raw_payload', 'original_record'):
                continue
            key = str(k).replace('~', '~0').replace('/', '~1')
            yield from _scalar_fields(v, prefix + '/' + key, depth + 1)
    elif isinstance(value, list):
        for i, v in enumerate(value[:64]):
            yield from _scalar_fields(v, prefix + '/' + str(i), depth + 1)
    elif value is None:
        yield prefix, 'null', None, None
    elif isinstance(value, bool):
        yield prefix, 'boolean', 'true' if value else 'false', int(value)
    elif isinstance(value, (float, int)):
        # Text retains exact integer/decimal representation; REAL supports filters.
        try:
            number = float(value)
        except OverflowError:
            number = None
        yield prefix, 'number', str(value), number
    else:
        yield prefix, 'string', str(value), None


class DomainStore:
    """A store is owned by one domain worker/thread; lock excludes other processes."""
    def __init__(self, domain, state_dir, config=None, check_budget=None, progress=None):
        if domain not in DOMAINS:
            raise ValueError('unknown_domain')
        self.domain = domain
        self._error_occurrences = {}
        self.config = config or {}
        self.check_budget = check_budget or (lambda: None)
        self.progress = progress or (lambda **kw: None)
        self.directory = Path(state_dir).absolute() / ('private-household' if domain in ('user_profiles', 'inventory') else '.') / 'staging'
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.directory / (domain + '.sqlite3')
        if self.directory.is_symlink() or self.path.is_symlink():
            raise ValueError('symlink_target_refused')
        self.lock_path = self.directory / (domain + '.writer.lock')
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        self.lock_fd = os.open(self.lock_path, flags, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.lock_fd)
            self.lock_fd = None
            raise RuntimeError('domain_writer_already_active') from None
        try:
            self.check_budget()
            if self.path.exists() and self.path.stat().st_size:
                check = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
                try:
                    owned = check.execute("SELECT value FROM ingest_meta WHERE key='binding'").fetchone()
                    schema = check.execute("SELECT value FROM ingest_meta WHERE key='schema_version'").fetchone()
                    if owned != ('additive_staging_not_app_bound',) or schema != (str(SCHEMA_VERSION),):
                        raise ValueError('non_owned_or_incompatible_database_refused')
                finally:
                    check.close()
            fd = os.open(self.path, flags, 0o600)
            os.close(fd)
            self.db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript(SCHEMA)
            existing = self.db.execute("SELECT value FROM ingest_meta WHERE key='domain'").fetchone()
            if existing and existing[0] != domain:
                raise ValueError('domain_mismatch')
            self.db.execute("INSERT OR IGNORE INTO ingest_meta VALUES('domain',?)", (domain,))
            self.db.execute("INSERT OR IGNORE INTO ingest_meta VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
            self.db.execute("INSERT OR IGNORE INTO ingest_meta VALUES('binding','additive_staging_not_app_bound')")
            self.db.execute("INSERT OR IGNORE INTO ingest_meta VALUES('database_id',?)", (uuid.uuid4().hex,))
            self.db.execute("INSERT OR IGNORE INTO ingest_meta VALUES('record_count','0')")
        except BaseException:
            self.close()
            raise

    def close(self):
        if getattr(self, 'db', None) is not None:
            self.db.close()
            self.db = None
        if getattr(self, 'lock_fd', None) is not None:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            os.close(self.lock_fd)
            self.lock_fd = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _error(self, key, version, row, exc):
        return self.db.execute('INSERT OR IGNORE INTO source_errors VALUES(?,?,?,?,?)',
                        (key, version, row, type(exc).__name__, time.time())).rowcount

    def record_error(self, source, exc):
        """Persist adapter parse failures without storing exception text or payload."""
        fp = _fingerprint(source)
        version = hashlib.sha256(_json(fp).encode()).hexdigest()
        key = source_key(source)
        prior = self.db.execute('SELECT cursor FROM sources WHERE source_key=? AND version=?', (key,version)).fetchone()
        if prior is None:
            return False
        # Negative ordinals distinguish adapter errors from physical record errors.
        count = self._error_occurrences.get((key,version),0)
        self._error_occurrences[(key,version)]=count+1
        inserted=self._error(key, version, -count-1, exc)
        if inserted:
            self.db.execute("UPDATE sources SET errors=errors+1,status='partial',updated_at=? WHERE source_key=? AND version=?", (time.time(),key,version))
        return True

    def _commit_batch(self, source, fp, version, batch, cursor, totals):
        self.check_budget()
        if _fingerprint(source) != fp:
            raise SourceChanged('source_changed_during_ingestion')
        key = source_key(source)
        written = unchanged = errors = created = 0
        self.db.execute('BEGIN IMMEDIATE')
        try:
            for row, record in batch:
                self.db.execute('SAVEPOINT one_row')
                try:
                    if not isinstance(record, dict):
                        raise TypeError('record_must_be_object')
                    encoded = _json(record)
                    if len(encoded.encode('utf-8')) > int(self.config.get('max_record_bytes', 4 * 1024 * 1024)):
                        raise ValueError('record_size_cap')
                    digest = hashlib.sha256(encoded.encode()).hexdigest()
                    raw_id = record.get('id', record.get('source_id'))
                    rid = str(raw_id) if raw_id is not None else 'row:' + str(row)
                    prior = self.db.execute('SELECT content_sha256 FROM records WHERE source_key=? AND source_version=? AND record_id=?', (key, version, rid)).fetchone()
                    if prior and prior[0] == digest:
                        unchanged += 1
                    else:
                        self.db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_key,source_version,record_id) DO UPDATE SET row_number=excluded.row_number, content_sha256=excluded.content_sha256,payload_json=excluded.payload_json,updated_at=excluded.updated_at', (key, version, rid, row, digest, encoded, time.time()))
                        self.db.execute('DELETE FROM record_fields WHERE source_key=? AND source_version=? AND record_id=?', (key, version, rid))
                        self.db.execute('DELETE FROM relations WHERE source_key=? AND source_version=? AND record_id=?', (key, version, rid))
                        self.db.executemany('INSERT INTO record_fields VALUES(?,?,?,?,?,?,?)',
                            ((key, version, rid, *field) for field in itertools.islice(_scalar_fields(record), max(1,int(self.config.get('max_indexed_fields',128))))))
                        links = record.get('relations') or []
                        if not isinstance(links, list):
                            raise TypeError('relations_must_be_list')
                        for n, link in enumerate(links):
                            if not isinstance(link, dict):
                                raise TypeError('relation_must_be_object')
                            self.db.execute('INSERT INTO relations VALUES(?,?,?,?,?,?,?,?)',
                                (key, version, rid, n, str(link.get('kind', 'related')),
                                 link.get('target_domain'), str(link['target_id']) if link.get('target_id') is not None else None, _json(link)))
                        written += 1
                        created += not bool(prior)
                    self.db.execute('RELEASE one_row')
                except (TypeError, ValueError, OverflowError, sqlite3.IntegrityError) as exc:
                    self.db.execute('ROLLBACK TO one_row')
                    self.db.execute('RELEASE one_row')
                    self._error(key, version, row, exc)
                    errors += 1
            self.db.execute("UPDATE sources SET cursor=?, written=written+?, errors=errors+?, status='partial',updated_at=? WHERE source_key=? AND version=?", (cursor, written, errors, time.time(), key, version))
            self.db.execute("UPDATE ingest_meta SET value=CAST(value AS INTEGER)+? WHERE key='record_count'", (created,))
            self.db.execute('COMMIT')
        except BaseException:
            with contextlib.suppress(sqlite3.Error):
                self.db.execute('ROLLBACK')
            raise
        totals['written'] += written
        totals['unchanged'] += unchanged
        totals['errors'] += errors
        totals['read'] += len(batch)
        self.progress(source_key=key, event='batch', **{k: (0 if source.get('reference_only') and k in ('read','written','unchanged') else totals[k]) for k in ('read','written','unchanged','errors','skipped')})

    def ingest(self, source, records):
        key = source_key(source)
        summary = dict(source_key=key, status='partial', read=0, written=0,
                       unchanged=0, errors=0, skipped=0, resumed_from=0, completed=False)
        if source.get('restricted') or source.get('loaded') or source.get('disposition') in ('restricted','skip','existing-loaded','already_loaded'):
            summary.update(status='skipped', skipped=1,
                           reason='restricted_input' if source.get('restricted') else 'catalog_skip')
            return summary
        fp = _fingerprint(source)
        version = hashlib.sha256(_json(fp).encode()).hexdigest()
        summary['source_version'] = version
        self._error_occurrences[(key,version)]=0
        prior = self.db.execute('SELECT cursor,status,written,errors FROM sources WHERE source_key=? AND version=?', (key, version)).fetchone()
        if prior and prior[1] in ('complete', 'complete_with_errors'):
            summary.update(status='partial' if prior[3] else 'complete', unchanged=prior[2], errors=prior[3], resumed_from=prior[0], completed=True, already_complete=True)
            return summary
        cursor = prior[0] if prior else 0
        summary['resumed_from'] = cursor
        self.db.execute('INSERT OR IGNORE INTO sources(source_key,version,path,format,provider,license,custody_json,fingerprint_json,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
            (key, version, str(Path(source['path']).resolve()), str(source.get('format','unknown')), str(source.get('provider','unknown')), str(source.get('license','unknown')), _json(source.get('custody')), _json(fp), 'partial', time.time()))
        batch = []
        batch_bytes = 0
        batch_size = max(1, int(self.config.get('batch_size', 500)))
        max_batch_bytes = max(4096, int(self.config.get('max_batch_bytes', 16 * 1024 * 1024)))
        row_limit = max(0, int(self.config.get('max_rows_per_source', 0)))
        seen = cursor
        try:
            self.progress(source_key=key, event='source_started', resumed_from=cursor)
            iterator = iter(records)
            # Replaying a streaming reader is safe for every supported format.
            # No seek offsets are assumed across gzip/JSON/CSV adapters.
            for n, record in enumerate(iterator, 1):
                if n <= cursor:
                    if n % batch_size == 0:
                        self.check_budget()
                    continue
                if row_limit and summary['read'] + len(batch) >= row_limit:
                    if batch:
                        self._commit_batch(source, fp, version, batch, seen, summary)
                        batch = []
                    raise BudgetExceeded('per_source_row_cap')
                if not batch:
                    self.check_budget()
                batch.append((n, record))
                seen = n
                # repr is bounded by input object already yielded; JSON validation is row-isolated.
                try:
                    batch_bytes += len(_json(record).encode('utf-8'))
                except (TypeError, ValueError, OverflowError):
                    batch_bytes += 1024
                if len(batch) >= batch_size or batch_bytes >= max_batch_bytes:
                    self._commit_batch(source, fp, version, batch, seen, summary)
                    batch, batch_bytes = [], 0
            if batch:
                self._commit_batch(source, fp, version, batch, seen, summary)
            if _fingerprint(source) != fp:
                raise SourceChanged('source_changed_during_ingestion')
            durable_errors = self.db.execute('SELECT errors FROM sources WHERE source_key=? AND version=?', (key,version)).fetchone()[0]
            summary['errors'] = durable_errors
            self.db.execute("UPDATE sources SET status=?,updated_at=? WHERE source_key=? AND version=?", ('complete_with_errors' if durable_errors else 'complete',time.time(),key,version))
            summary.update(status='complete' if not durable_errors else 'partial', completed=True)
        except BudgetExceeded:
            summary.update(status='partial', reason='resource_cap')
        except Exception as exc:
            # Keep an accepted prefix even if a later record fails to parse.
            if batch:
                try:
                    self._commit_batch(source, fp, version, batch, seen, summary)
                except Exception:
                    pass
            inserted = self._error(key, version, seen + 1, exc)
            summary['errors'] += 1
            summary.update(status='partial' if summary['written'] or cursor else 'failed', error_class=type(exc).__name__)
            self.db.execute('UPDATE sources SET errors=errors+?,status=?,updated_at=? WHERE source_key=? AND version=?',
                            (inserted, summary['status'], time.time(), key, version))
        finally:
            with contextlib.suppress(Exception):
                close = getattr(locals().get('iterator'), 'close', None)
                if close:
                    close()
        self.progress(source_key=key, event='source_finished', **{k: (0 if source.get('reference_only') and k in ('read','written','unchanged') else summary[k]) for k in ('read','written','unchanged','errors','skipped')})
        return summary
