"""Versioned shared serialization policy; transport reproducibility is runtime-qualified."""
import gzip
import io
from .core import canonical, sha

CONTENT_POLICY = {
    'schemaVersion': 'offmenu-canonical-jsonl-policy/1',
    'json': 'utf8-sorted-keys-compact-finite-json-preserve-arrays-and-unicode-lf',
    'numbers': 'python-json-finite-number-representation-no-coercion',
    'nulls': 'explicit-json-null-no-imputation',
    'records': 'one-singleton-array-per-line-preserve-source-order',
}
POLICY = {
    'schemaVersion': 'offmenu-serialization-policy/1',
    'canonical': CONTENT_POLICY,
    'gzip': {'filename': '', 'mtime': 0, 'compresslevel': 1},
    'transportQualification': 'exact-python-and-zlib-runtime',
}


def encode_records(rows):
    return b''.join(canonical([row]) for row in rows)


def compress(raw):
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', **POLICY['gzip']) as writer:
        writer.write(raw)
    return stream.getvalue()


def asset(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}
