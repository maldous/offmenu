"""Pinned, bounded reads of exactly the accepted places partitions and notices."""
import gzip
import hashlib
import io
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

SOURCES = ('overture-food-places', 'wikidata-food-businesses')
MAX_COMPRESSED = 128 * 1024 * 1024
MAX_LINE = 8 * 1024 * 1024
MAX_DECODED_FILE = 512 * 1024 * 1024

def signature(s):
    return [s.st_dev, s.st_ino, stat.S_IFMT(s.st_mode), s.st_uid, s.st_gid,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]

def safe_key(key):
    if not isinstance(key, str) or not key or '\\' in key or '\x00' in key:
        raise ValueError('invalid input key')
    p = PurePosixPath(key)
    if p.is_absolute() or str(p) != key or any(x in ('', '.', '..') for x in p.parts):
        raise ValueError('unsafe input key')
    return p

def open_regular(root, key):
    parts = safe_key(key).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if i < len(parts) - 1:
                flags |= os.O_DIRECTORY
            nxt = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nxt
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('input is not a regular file')
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)

def file_signature(root, key):
    fd = open_regular(root, key)
    try:
        return signature(os.fstat(fd))
    finally:
        os.close(fd)

def read_pinned(root, key, entry, cap=MAX_COMPRESSED):
    if type(entry['bytes']) is not int or not 0 <= entry['bytes'] <= cap:
        raise ValueError('input asset exceeds bounded read size')
    fd = open_regular(root, key)
    with os.fdopen(fd, 'rb') as stream:
        before = signature(os.fstat(stream.fileno()))
        if before != entry['identity']:
            raise ValueError('input identity changed')
        raw = stream.read(cap + 1)
        after = signature(os.fstat(stream.fileno()))
    if before != after or len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('input bytes or SHA-256 mismatch')
    return raw

def inventory(root, expected_manifest_sha256=None):
    root = Path(root)
    ident = file_signature(root, 'manifest.json')
    manifest_entry = {'bytes': ident[5], 'identity': ident, 'sha256': expected_manifest_sha256}
    if ident[5] > 32 * 1024 * 1024:
        raise ValueError('curated manifest too large')
    fd = open_regular(root, 'manifest.json')
    with os.fdopen(fd, 'rb') as f:
        raw = f.read(32 * 1024 * 1024 + 1)
        if signature(os.fstat(f.fileno())) != ident:
            raise ValueError('manifest changed during read')
    sha = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None and sha != expected_manifest_sha256:
        raise ValueError('accepted manifest byte pin mismatch')
    manifest_entry['sha256'] = sha
    manifest = json.loads(raw)
    if manifest.get('format') != 'offmenu-curated/1':
        raise ValueError('unexpected curated manifest schema')
    for source in SOURCES:
        item = manifest['sources'][source]
        if not isinstance(item.get('releaseId'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', item['releaseId']):
            raise ValueError('unsafe source release identifier')
        if type(item.get('records')) is not int or item['records'] < 1 or item.get('rawSourcePayloadPublished') is not False:
            raise ValueError('invalid admitted source count/publication controls')
    notice_prefix = 'notices/overture-food-places/' + manifest['sources']['overture-food-places']['releaseId'] + '/'
    targets = {}
    for item in list(manifest.get('files', [])) + list(manifest.get('notices', [])):
        key = item.get('key')
        safe_key(key)
        relevant = any(key.startswith('records/' + source + '/') for source in SOURCES) or key.startswith(notice_prefix)
        if not relevant:
            continue
        if key in targets:
            raise ValueError('duplicate target asset in manifest')
        if key.startswith('records/') and (len(PurePosixPath(key).parts) != 3 or not key.endswith('.jsonl.gz')):
            raise ValueError('unexpected record partition path')
        if key.startswith('notices/') and (len(PurePosixPath(key).parts) != 4 or not key.endswith('.txt')):
            raise ValueError('unexpected licence notice path')
        if type(item.get('bytes')) is not int or not 0 <= item['bytes'] <= MAX_COMPRESSED or not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256'))):
            raise ValueError('invalid target asset receipt')
        identity = file_signature(root, key)
        if identity[5] != item['bytes']:
            raise ValueError('manifest asset size mismatch')
        targets[key] = {'bytes': item['bytes'], 'sha256': item['sha256'], 'identity': identity}
    actual = set()
    for prefix in [*(f'records/{s}' for s in SOURCES), notice_prefix.rstrip('/')]:
        directory = root / prefix
        if not directory.exists() and prefix.startswith('notices/'):
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('source partition missing or symlinked')
        for p in directory.rglob('*'):
            if p.is_symlink():
                raise ValueError('source subtree contains symlink')
            if p.is_file():
                key = p.relative_to(root).as_posix()
                if key not in targets:
                    raise ValueError('undeclared target file')
                actual.add(key)
            elif not p.is_dir():
                raise ValueError('source subtree contains special file')
    if actual != set(targets):
        raise ValueError('manifest-listed target file set does not match actual files')
    for source in SOURCES:
        if not any(k.startswith(f'records/{source}/') for k in targets):
            raise ValueError('source has no declared record files')
    catalog = {'schema': 'offmenu-places-input-catalog/1', 'manifest': manifest_entry, 'assets': targets}
    return manifest, catalog

def catalog_bytes(catalog):
    return (json.dumps(catalog, sort_keys=True, separators=(',', ':')) + '\n').encode()

def rows(root, source_id, catalog, cursor=None, completed_files=None):
    for key, entry in sorted(catalog['assets'].items()):
        if not key.startswith(f'records/{source_id}/'):
            continue
        if cursor and key < cursor['file']:
            continue
        raw = read_pinned(root, key, entry)
        decoded = 0
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
            line_number = 0
            while True:
                line = f.readline(MAX_LINE + 1)
                if not line:
                    break
                line_number += 1
                decoded += len(line)
                if len(line) > MAX_LINE or decoded > MAX_DECODED_FILE:
                    raise ValueError('decoded source exceeds bounded size')
                if cursor and key == cursor['file'] and line_number <= cursor['line']:
                    continue
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, list) or len(value) != 2 or not isinstance(value[1], list) or len(value[1]) != 1:
                    raise ValueError('invalid normalized source row envelope')
                yield value[1][0], {'source': source_id, 'file': key, 'line': line_number}
        if completed_files is not None:
            completed_files.add(key)
