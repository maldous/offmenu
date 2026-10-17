"""Private places alignment custody state; never adopt unpinned legacy packets."""
import base64
import contextlib
import hashlib
import json
import os
import sqlite3
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_bytes(path, raw):
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
            if not partial.is_dir() or not path.is_file():
                raise ValueError('legacy partial has no pinned checkpoint; explicit recovery required')
        elif partial.exists() or path.exists():
            raise ValueError('partial or checkpoint already exists; explicit resume required')
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA synchronous=FULL')
        if not resume:
            self.db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
            self.db.execute('CREATE TABLE identities (source TEXT, record TEXT, PRIMARY KEY(source,record))')
            self.db.commit()
            self.value = {'version': 1, 'pins': pins, 'cursor': None, 'createdAt': pins.pop('createdAt'), 'input_counts': {}, 'source_counts': {}, 'type_counts': {}, 'sink': None}
            self.save()
        else:
            row = self.db.execute('SELECT payload FROM state WHERE id=1').fetchone()
            self.value = json.loads(row[0]) if row else {}
            pins.pop('createdAt')
            if self.value.get('version') != 1 or self.value.get('pins') != pins:
                self.db.close()
                raise ValueError('checkpoint pins mismatch')
            receipts = (self.value.get('sink') or {}).get('files', [])
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
        self.db.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (json.dumps(self.value),))
        self.db.commit()

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
