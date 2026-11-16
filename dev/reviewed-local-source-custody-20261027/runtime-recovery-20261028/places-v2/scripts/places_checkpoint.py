"""Private places alignment custody state; never adopt unpinned legacy packets."""
import base64
import contextlib
import hashlib
import json
import os
import sqlite3
import signal
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_bytes(path, raw):
    temporary = path.with_name(path.name + '.pending')
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    identity = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        # Only our incomplete temporary; SIGKILL remains an explicit reconciliation.
        try:
            current = temporary.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                temporary.unlink()
        except FileNotFoundError:
            pass


@contextlib.contextmanager
def writer_lock(output):
    path = output.with_name(output.name + '.alignment.lock')
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError('writer lock exists; reconcile stale/live ownership explicitly') from error
    identity = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'output': str(output.resolve())}))
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        if path.exists() and (path.stat().st_dev, path.stat().st_ino) == (identity.st_dev, identity.st_ino):
            path.unlink()


class Checkpoint:
    def __init__(self, output, partial, pins, resume):
        path = output.with_name(output.name + '.checkpoint.sqlite')
        if resume:
            if not path.is_file():
                raise ValueError('legacy partial has no pinned checkpoint; explicit recovery required')
        elif partial.exists() or path.exists():
            raise ValueError('partial or checkpoint already exists; explicit resume required')
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA synchronous=FULL')
        if not resume:
            self.db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
            self.db.execute('CREATE TABLE identities (source TEXT, record TEXT, PRIMARY KEY(source,record))')
            self.db.execute('CREATE TABLE assets (idx INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
            self.db.execute('CREATE TABLE completed (key TEXT PRIMARY KEY)')
            self.saved_asset_count = 0
            self.saved_completed = set()
            self.db.commit()
            self.value = {'version': 2, 'pins': pins, 'cursor': None, 'createdAt': pins.pop('createdAt'), 'input_counts': {}, 'source_counts': {}, 'type_counts': {}, 'sink': None}
            self.save()
        else:
            row = self.db.execute('SELECT payload FROM state WHERE id=1').fetchone()
            self.value = json.loads(row[0]) if row else {}
            pins.pop('createdAt')
            if self.value.get('version') != 2 or self.value.get('pins') != pins:
                self.db.close()
                raise ValueError('checkpoint pins mismatch')
            if not partial.exists():
                if self.value.get('cursor') is not None or self.value.get('sink') is not None or self.value.get('input_counts'):
                    raise ValueError('checkpoint partial directory missing after progress')
                (partial / 'packets').mkdir(parents=True)
            receipts = [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM assets ORDER BY idx')]
            self.saved_asset_count = len(receipts)
            self.saved_completed = {r[0] for r in self.db.execute('SELECT key FROM completed')}
            self.value['completedFiles'] = sorted(self.saved_completed)
            if self.value.get('sink') is not None:
                self.value['sink']['files'] = receipts
            actual = {str(p.relative_to(partial)) for p in (partial / 'packets').iterdir() if p.is_file()}
            expected_keys = {r['key'] for r in receipts}
            sink = self.value.get('sink') or {}
            buffered = base64.b64decode(sink.get('buffer', ''), validate=True)
            orphan_key = f"packets/part-{sink.get('file_index', 0):05d}.jsonl.gz"
            # A crash after atomic rename but before SQLite commit can leave the
            # exact already-checkpointed buffer closed on disk. Reuse only those
            # pinned bytes, never arbitrary unjournaled or legacy output.
            allowed_orphan = {orphan_key} if buffered and (partial / orphan_key).is_file() and (partial / orphan_key).read_bytes() == buffered else set()
            if not expected_keys <= actual or actual - expected_keys != allowed_orphan:
                self.db.close()
                raise ValueError('uncheckpointed/missing output assets; explicit recovery required')
            for r in receipts:
                p = partial / r['key']
                if p.stat().st_size != r['bytes'] or digest(p) != r['sha256']:
                    self.db.close()
                    raise ValueError('checkpoint output mismatch/truncation')
            count = self.db.execute('SELECT COUNT(*) FROM identities').fetchone()[0]
            if count != sum(self.value['input_counts'].values()):
                self.db.close()
                raise ValueError('checkpoint identity/cursor count mismatch')

    def add_identity(self, source, record):
        try:
            self.db.execute('INSERT INTO identities VALUES (?,?)', (source, record))
        except sqlite3.IntegrityError as error:
            raise ValueError(f'duplicate normalized source identity: {(source, record)}') from error

    def save(self):
        # Grow relational receipts/coverage once, not a full JSON copy per packet.
        sink = self.value.get('sink')
        receipts = sink.get('files', []) if sink else []
        if len(receipts) < self.saved_asset_count:
            raise ValueError('checkpoint asset receipt regression')
        for idx in range(self.saved_asset_count, len(receipts)):
            self.db.execute('INSERT INTO assets VALUES (?,?)', (idx, json.dumps(receipts[idx])))
        completed = set(self.value.get('completedFiles', []))
        if not self.saved_completed <= completed:
            raise ValueError('checkpoint input coverage regression')
        for key in sorted(completed - self.saved_completed):
            self.db.execute('INSERT INTO completed VALUES (?)', (key,))
        small = dict(self.value)
        small.pop('completedFiles', None)
        if sink is not None:
            small['sink'] = dict(sink)
            small['sink'].pop('files', None)
        self.db.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (json.dumps(small),))
        self.db.commit()
        self.saved_asset_count = len(receipts)
        self.saved_completed = completed

    def close(self):
        self.db.close()  # Uncheckpointed identities roll back with their cursor.


def sink_state(sink):
    return {'file_index': sink.file_index, 'current': sink.current, 'files': sink.files,
            'counts': dict(sink.counts), 'buffer': base64.b64encode(sink.buffer).decode(),
            'file_packets': sink.file_packets}


def restore_sink(sink, state):
    from collections import Counter
    sink.file_index = state['file_index']
    sink.current = state['current']
    sink.files = state['files']
    sink.counts = Counter(state['counts'])
    sink.buffer = base64.b64decode(state['buffer'], validate=True)
    sink.file_packets = state['file_packets']
    sink.closed_bytes = sum(r['bytes'] for r in sink.files)
    sink.current_bytes = sum(len(json.dumps(r, ensure_ascii=False, separators=(',', ':')).encode()) for r in sink.current)

