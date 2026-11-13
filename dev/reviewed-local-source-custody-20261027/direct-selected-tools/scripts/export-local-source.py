#!/usr/bin/env python3
"""One-shot OffMenu source custody; never executes, edits, or pushes source files."""
from __future__ import annotations
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import resource
import stat
import sqlite3
import subprocess
import sys
import tempfile

SCHEMA = 'offmenu-local-source-packet/1'
SUMMARY = 'offmenu-local-source-summary/1'
CANONICAL = '/home/user/src/offmenu'
EXTERNAL = '/home/user/src/offmenu-data/runtime/layout-migration'
EXPLICIT_SOURCE_FILES = {'/home/user/src/offmenu-worktrees/worker00-generation2-code-batch-20261025/public/scanner-ui.js'}
STAGING = '/srv/offmenu-refresh/outputs/source-export'
MAX_FILE = 64 * 1024 * 1024
MAX_PACKET = 8 * 1024 * 1024
PART_BYTES = 512 * 1024
MAX_FILES = 50000
MAX_INDEX = 32 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
JOB = re.compile(r'[a-z0-9][a-z0-9-]{7,63}')
SHA = re.compile(r'[0-9a-f]{64}')
GIT_SHA = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
DENIED = {'.git', '.env', '.ssh', '.aws', '.codex', '.credentials', 'node_modules',
          '__pycache__', '.venv', 'venv', 'datasets', 'dataset', 'raw-data', 'raw_data',
          'rawdata', 'cache', 'caches', 'logs', 'log', 'secrets', 'credentials',
          'corpus', 'corpora', 'grants', '_diag'}
TEXT = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.html', '.css', '.scss',
        '.md', '.rst', '.txt', '.json', '.toml', '.yaml', '.yml', '.sql', '.sh', '.svg', '.patch', '.diff'}
ARTWORK = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.otf'}
ROOT_NAMES = {'Dockerfile', 'Makefile', 'LICENSE', 'NOTICE', '.gitignore', '.gitattributes'}
CORPUS_CODE = {'.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx'}
SECRET = re.compile(rb'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})|https?://[^\s/@]+:[^\s/@]+@')
ANCHORS = [
    {'sourcePath': EXTERNAL + '/worker13/local-foundation-consumer-contract2-20261027/confirmed-handoff-r1/named-r3/source-identity-client-r1/result.json', 'repositoryPath': 'metadata/client13-result.json', 'sha256': 'd608fe5f1a785df3dc7103e108aa9394ded7ea0b7685afd9df6df0baee06b7ac', 'kind': 'documentation', 'reviewRef': 'parent-provided-exact-anchor-20261027'},
    {'sourcePath': EXTERNAL + '/worker13/local-foundation-consumer-contract2-20261027/confirmed-handoff-r1/named-r3/source-identity-client-r1/source-and-import-closure.json', 'repositoryPath': 'metadata/client13-source-and-import-closure.json', 'sha256': 'c240c2937e5e6e44b12b2e8e7d9484ae927fce8c901374f6e57694be05f2278f', 'kind': 'documentation', 'reviewRef': 'parent-provided-exact-anchor-20261027'},
    {'sourcePath': EXTERNAL + '/native15-first-sequence-20261026/full15-master-r1/all-scenes-ready-20261027-r1/actual-delivery-accepted.json', 'repositoryPath': 'metadata/all15-actual-delivery-accepted.json', 'sha256': '11d639bf0fadbea92d34a20cecc43c442e0d313a8c7b1b0e817c841c8cbaa9c9', 'kind': 'documentation', 'reviewRef': 'parent-provided-exact-anchor-20261027'},
]

class Rejected(Exception):
    """Static codes only: never log source data or excluded paths."""

def require(ok, code):
    if not ok:
        raise Rejected(code)

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def strict(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'duplicate-json-key')
        result[k] = v
    return result

def decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=strict, parse_constant=lambda _: (_ for _ in ()).throw(Rejected('nonfinite-json')))
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected('invalid-json') from None

def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected), 'unexpected-schema-keys')

def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'integer-out-of-range')

def relative(value):
    require(type(value) is str and 0 < len(value) <= 1024 and '\\' not in value and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'invalid-relative-path')
    p = PurePosixPath(value)
    require(not p.is_absolute() and str(p) == value and all(x not in ('', '.', '..') for x in p.parts), 'invalid-relative-path')
    denied = DENIED - {'corpus', 'corpora'} if p.suffix.lower() in CORPUS_CODE else DENIED
    require(not any(x.lower() in denied or x.lower().startswith('.env') or x.lower().endswith(('.pem', '.key', '.p12', '.pfx')) for x in p.parts), 'excluded-path')
    require(all(not x.startswith('.') or x in ('.github', '.agents', '.gitignore', '.gitattributes') for x in p.parts), 'excluded-hidden-path')
    require(p.suffix.lower() in TEXT | ARTWORK or p.name in ROOT_NAMES, 'unsupported-file-kind')
    return p

def source_path(value):
    require(type(value) is str, 'invalid-source-path')
    if value in EXPLICIT_SOURCE_FILES:
        return value
    for root in (CANONICAL, EXTERNAL):
        if value.startswith(root + '/'):
            relative(value[len(root) + 1:])
            return value
    raise Rejected('source-outside-selected-roots')

def open_absolute(path, flags=os.O_RDONLY):
    """No symlink ancestor/final path; returns a descriptor, not a reopened name."""
    require(type(path) is str and path.startswith('/') and str(PurePosixPath(path)) == path and '..' not in PurePosixPath(path).parts, 'invalid-absolute-path')
    parts = PurePosixPath(path).parts[1:]
    require(bool(parts), 'invalid-absolute-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        out = os.open(parts[-1], flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        return out
    finally:
        os.close(fd)

def read_regular(path, maximum=MAX_FILE):
    fd = open_absolute(path)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'not-single-regular-file')
        require(before.st_size <= maximum, 'file-too-large-no-export')
        parts = []; total = 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - total))
            if not chunk: break
            parts.append(chunk); total += len(chunk)
            require(total <= maximum, 'file-too-large-no-export')
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(identity(before) == identity(after) and total == before.st_size, 'file-changed-during-read')
        raw = b''.join(parts)
        # Same-length rewrites can share a filesystem timestamp tick. Recheck
        # bounded bytes on this descriptor rather than relying on metadata alone.
        os.lseek(fd, 0, os.SEEK_SET)
        verified = 0
        while True:
            chunk = os.read(fd, min(65536, len(raw) + 1 - verified))
            if not chunk: break
            require(chunk == raw[verified:verified + len(chunk)], 'file-changed-during-read')
            verified += len(chunk)
        require(verified == len(raw) and identity(before) == identity(os.fstat(fd)), 'file-changed-during-read')
        return raw, before
    finally:
        os.close(fd)

def check_body(raw, kind):
    require(not SECRET.search(raw), 'secret-pattern-rejected')
    if kind != 'artwork':
        try: text = raw.decode('utf-8')
        except UnicodeError: raise Rejected('source-not-utf8') from None
        require('\x00' not in text, 'source-not-text')

def safe_git(root, args):
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
           'GIT_OPTIONAL_LOCKS': '0', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_TERMINAL_PROMPT': '0'}
    # These fixed operations read refs/index only. Never status/diff/hash-object,
    # checkout, submodule, fetch, remote/config output, clean filters or fsmonitor.
    cmd = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
           '-c', 'submodule.recurse=false', '-C', root, *args]
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(cmd, env=env, stdout=output, stderr=error,
                                   preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_INDEX, MAX_INDEX)))
        try: code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(); raise Rejected('git-metadata-timeout') from None
        require(code == 0, 'git-metadata-unavailable')
        require(output.tell() <= MAX_INDEX and error.tell() <= 65536, 'git-metadata-too-large')
        output.seek(0); return output.read()

def repo_metadata(root):
    head = safe_git(root, ['rev-parse', '--verify', 'HEAD']).decode().strip()
    require(bool(GIT_SHA.fullmatch(head)), 'invalid-head')
    branch = safe_git(root, ['rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
    require(bool(re.fullmatch(r'[A-Za-z0-9._/-]{1,256}', branch)), 'invalid-branch')
    return {'head': head, 'branch': branch}

@contextmanager
def index_snapshot(root):
    """Fixed passive index command; disk-backed output, not a record/byte cap."""
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
           'GIT_OPTIONAL_LOCKS': '0', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_TERMINAL_PROMPT': '0'}
    command = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
               '-c', 'submodule.recurse=false', '-C', root, 'ls-files', '--stage', '-z']
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(command, env=env, stdout=output, stderr=error)
        try: code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(); raise Rejected('git-metadata-timeout') from None
        require(code == 0, 'git-metadata-unavailable')
        require(error.tell() <= 65536, 'git-metadata-error-too-large')
        output.seek(0)
        yield output


def stream_digest(stream):
    result = hashlib.sha256()
    while True:
        chunk = stream.read(65536)
        if not chunk: break
        result.update(chunk)
    return result.hexdigest()


def index_records(stream):
    pending = b''
    while True:
        chunk = stream.read(65536)
        if not chunk: break
        parts = (pending + chunk).split(b'\0')
        pending = parts.pop()
        for record in parts:
            if record: yield record
    require(not pending, 'invalid-git-index')


@contextmanager
def inventory_stream(root=CANONICAL):
    """Complete eligible metadata, disk-backed sorting and directory queue."""
    root_fd = open_absolute(root, os.O_RDONLY | os.O_DIRECTORY)
    os.close(root_fd)
    before = repo_metadata(root)
    with tempfile.TemporaryDirectory(prefix='offmenu-inventory-private-') as working:
        database = sqlite3.connect(os.path.join(working, 'metadata.sqlite'))
        try:
            database.execute('PRAGMA temp_store=FILE')
            database.execute('CREATE TABLE entries (path TEXT PRIMARY KEY, object_id TEXT, mode TEXT)')
            database.execute('CREATE TABLE directories (number INTEGER PRIMARY KEY, path TEXT)')
            excluded = 0
            with index_snapshot(root) as snapshot:
                index_identity = stream_digest(snapshot); snapshot.seek(0)
                for entry in index_records(snapshot):
                    try:
                        meta, raw_path = entry.split(b'\t', 1)
                        mode, object_id, stage = meta.decode('ascii').split(' ')
                        path = raw_path.decode('utf-8')
                    except (ValueError, UnicodeError): raise Rejected('invalid-git-index') from None
                    require(stage == '0', 'unmerged-index-needs-owner-review')
                    try: relative(path)
                    except Rejected: excluded += 1; continue
                    database.execute('INSERT INTO entries VALUES (?, ?, ?)', (path, object_id, mode))
            database.execute('INSERT INTO directories(path) VALUES (?)', ('',))
            position = 0
            while True:
                row = database.execute('SELECT number,path FROM directories WHERE number>? ORDER BY number LIMIT 1', (position,)).fetchone()
                if row is None: break
                position, prefix = row
                directory = root if not prefix else root + '/' + prefix[:-1]
                fd = open_absolute(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    with os.scandir(fd) as children:
                        for child in children:
                            name = child.name; path = prefix + name
                            info = child.stat(follow_symlinks=False)
                            if stat.S_ISDIR(info.st_mode):
                                if name.lower() in DENIED - {'corpus', 'corpora'} or name.startswith('.') and name not in {'.github', '.agents'}:
                                    excluded += 1; continue
                                database.execute('INSERT INTO directories(path) VALUES (?)', (path + '/',))
                            elif stat.S_ISLNK(info.st_mode): excluded += 1
                            else:
                                try: relative(path)
                                except Rejected: excluded += 1; continue
                                database.execute('INSERT OR IGNORE INTO entries VALUES (?, NULL, NULL)', (path,))
                finally: os.close(fd)
            database.commit()

            def items():
                hashed_bytes = 0
                for path, object_id, mode in database.execute('SELECT path,object_id,mode FROM entries ORDER BY path'):
                    p = relative(path); source = root + '/' + path
                    item = {'sourcePath': source, 'repositoryPath': path,
                            'kind': 'artwork' if p.suffix.lower() in ARTWORK else 'source-text',
                            'indexObject': object_id, 'indexMode': mode,
                            'bytes': None, 'sha256': None, 'state': 'uninspected'}
                    if mode and mode not in ('100644', '100755'):
                        item['state'] = 'excluded-nonregular-index'; yield item; continue
                    try:
                        fd = open_absolute(source)
                        try: info = os.fstat(fd)
                        finally: os.close(fd)
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'not-single-regular-file')
                        if info.st_size > MAX_FILE or hashed_bytes + info.st_size > MAX_TOTAL:
                            item.update(bytes=info.st_size, sha256=None, state='present-unhashed')
                        else:
                            raw, info = read_regular(source)
                            hashed_bytes += len(raw)
                            item.update(bytes=len(raw), sha256=digest(raw), state='present')
                    except FileNotFoundError: item['state'] = 'missing'
                    except (Rejected, OSError): item['state'] = 'unreadable-or-excluded'
                    yield item

            yield before, items(), excluded
            require(repo_metadata(root) == before, 'repository-metadata-changed-retry-inventory')
            with index_snapshot(root) as snapshot:
                require(stream_digest(snapshot) == index_identity, 'repository-metadata-changed-retry-inventory')
        finally: database.close()


def inventory(root=CANONICAL):
    # Small in-process compatibility API; the CLI uses inventory_output streaming.
    with inventory_stream(root) as (repository, items, excluded):
        result = list(items)
    return repository, result, excluded


def inventory_output(prefix, directory, root=CANONICAL, include_anchors=False):
    """Byte-batched metadata with complete custody; never stages or uploads."""
    require(JOB.fullmatch(prefix) and len(prefix) <= 44, 'invalid-job-prefix')
    with tempfile.TemporaryDirectory(prefix='offmenu-inventory-packets-') as working:
        groups = []; current = []; current_bytes = 2
        total_files = 0; total_bytes = 0; identity = hashlib.sha256(); identity.update(b'[')
        def flush():
            nonlocal current, current_bytes
            filename = os.path.join(working, str(len(groups)) + '.json')
            with open(filename, 'xb') as output: output.write(canonical(current))
            groups.append(filename); current = []; current_bytes = 2
        with inventory_stream(root) as (repository, items, excluded):
            for item in items:
                encoded = canonical(item)[:-1]
                if current and current_bytes + len(encoded) + 1 > 512 * 1024:
                    flush()
                if total_files: identity.update(b',')
                identity.update(encoded)
                total_files += 1; total_bytes += item['bytes'] or 0
                current.append(item); current_bytes += len(encoded) + 1
            if current or not groups: flush()
        identity.update(b']\n')
        custody = {'selectionSha256': identity.hexdigest(), 'totalFiles': total_files,
                   'totalBytes': total_bytes, 'totalParts': total_files, 'excludedEntries': excluded}
        # The completion manifest is written last, after both index/HEAD checks.
        os.mkdir(directory, 0o700)
        receipts = []
        def write(packet):
            validate_packet(packet)
            raw = canonical(packet); job_id = packet['jobId']
            fd = os.open(os.path.join(directory, job_id + '.json'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as output: output.write(raw); output.flush(); os.fsync(output.fileno())
            receipts.append({'jobId': job_id, 'phase': packet['phase'], 'bytes': len(raw), 'sha256': digest(raw),
                             'batch': packet['batch'], 'custody': packet['custody']})
        for index, filename in enumerate(groups, 1):
            with open(filename, 'rb') as source: group = decode(source.read())
            write({'schemaVersion': SCHEMA, 'jobId': f'{prefix}-{index:04d}', 'phase': 'inventory',
                   'batch': {'index': index, 'count': len(groups)}, 'custody': custody,
                   'repository': repository, 'selection': [], 'items': group})
        if include_anchors:
            selection = []
            for anchor in ANCHORS:
                raw, _ = read_regular(anchor['sourcePath'])
                require(digest(raw) == anchor['sha256'], 'pinned-anchor-mismatch')
                selection.append(dict(anchor, bytes=len(raw)))
            for packet in packets('selected', prefix + '-a', repository, selection, selected_parts(selection)):
                write(packet)
        manifest = {'schemaVersion': 'offmenu-local-source-packet-set/1', 'packets': receipts}
        fd = os.open(os.path.join(directory, 'packet-set.json'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as output: output.write(canonical(manifest)); output.flush(); os.fsync(output.fileno())
        return manifest

def validate_selection(selection):
    require(type(selection) is list and 0 < len(selection) <= MAX_FILES, 'invalid-selection-count')
    seen_sources = set(); seen_targets = set(); total = 0
    for item in selection:
        keys(item, {'sourcePath', 'repositoryPath', 'bytes', 'sha256', 'kind', 'reviewRef'})
        source_path(item['sourcePath']); p = relative(item['repositoryPath'])
        integer(item['bytes'], 0, MAX_FILE)
        require(type(item['sha256']) is str and SHA.fullmatch(item['sha256']), 'invalid-source-digest')
        require(item['kind'] in {'source', 'test', 'documentation', 'artwork'}, 'invalid-source-kind')
        require((p.suffix.lower() in ARTWORK) == (item['kind'] == 'artwork'), 'file-kind-mismatch')
        require(type(item['reviewRef']) is str and re.fullmatch(r'[A-Za-z0-9._:/# -]{1,256}', item['reviewRef']), 'invalid-review-reference')
        require(item['sourcePath'] not in seen_sources and item['repositoryPath'] not in seen_targets, 'duplicate-selected-path')
        seen_sources.add(item['sourcePath']); seen_targets.add(item['repositoryPath']); total += item['bytes']
    require(total <= MAX_TOTAL, 'selection-total-limit-split-manifest-explicitly')
    return total

def selected_parts(selection):
    validate_selection(selection)
    parts = []
    for index, item in enumerate(selection):
        raw, _ = read_regular(item['sourcePath'])
        require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'selected-source-pin-mismatch')
        check_body(raw, item['kind'])
        offsets = range(0, len(raw), PART_BYTES) if raw else [0]
        for offset in offsets:
            part = raw[offset:offset + PART_BYTES]
            parts.append({'fileIndex': index, 'offset': offset, 'bytes': len(part),
                          'sha256': digest(part), 'contentBase64': base64.b64encode(part).decode('ascii')})
    return parts

def packets(phase, prefix, repository, selection, items, excluded=0):
    require(JOB.fullmatch(prefix) and len(prefix) <= 59, 'invalid-job-prefix')
    groups = []; current = []
    # Actual serialized packet size is checked as well. No silent omissions.
    for item in items:
        if current and len(canonical(current + [item])) > MAX_PACKET // 2:
            groups.append(current); current = []
        current.append(item)
    if current or not groups: groups.append(current)
    require(len(groups) <= 9999, 'too-many-packets')
    custody = {'selectionSha256': digest(canonical(selection if phase == 'selected' else items)),
               'totalFiles': len(selection) if phase == 'selected' else len(items),
               'totalBytes': sum(x['bytes'] for x in selection) if phase == 'selected' else sum(x['bytes'] or 0 for x in items),
               'totalParts': len(items), 'excludedEntries': excluded}
    result = []
    for index, group in enumerate(groups, 1):
        packet = {'schemaVersion': SCHEMA, 'jobId': f'{prefix}-{index:04d}', 'phase': phase,
                  'batch': {'index': index, 'count': len(groups)}, 'custody': custody,
                  'repository': repository, 'selection': selection, 'items': group}
        require(len(canonical(packet)) <= MAX_PACKET, 'packet-too-large-no-export')
        validate_packet(packet)
        result.append(packet)
    return result

def validate_packet(packet, job_id=None):
    keys(packet, {'schemaVersion', 'jobId', 'phase', 'batch', 'custody', 'repository', 'selection', 'items'})
    require(packet['schemaVersion'] == SCHEMA and type(packet['jobId']) is str and JOB.fullmatch(packet['jobId']), 'packet-identity-invalid')
    require(job_id is None or packet['jobId'] == job_id, 'job-id-mismatch')
    require(packet['phase'] in {'inventory', 'selected'}, 'invalid-phase')
    keys(packet['batch'], {'index', 'count'})
    integer(packet['batch']['count'], 1, 2**63 - 1 if packet['phase'] == 'inventory' else 9999); integer(packet['batch']['index'], 1, packet['batch']['count'])
    keys(packet['repository'], {'head', 'branch'})
    require(type(packet['repository']['head']) is str and GIT_SHA.fullmatch(packet['repository']['head']), 'invalid-head')
    require(type(packet['repository']['branch']) is str and re.fullmatch(r'[A-Za-z0-9._/-]{1,256}', packet['repository']['branch']), 'invalid-branch')
    keys(packet['custody'], {'selectionSha256', 'totalFiles', 'totalBytes', 'totalParts', 'excludedEntries'})
    require(type(packet['custody']['selectionSha256']) is str and SHA.fullmatch(packet['custody']['selectionSha256']), 'invalid-custody-digest')
    for key in ('totalFiles', 'totalParts', 'excludedEntries'): integer(packet['custody'][key], 0, 2**63 - 1 if packet['phase'] == 'inventory' else 1000000)
    integer(packet['custody']['totalBytes'], 0, MAX_TOTAL if packet['phase'] == 'selected' else 2**63 - 1)
    require(type(packet['items']) is list and len(packet['items']) <= (MAX_PACKET if packet['phase'] == 'inventory' else MAX_FILES), 'invalid-packet-items')
    if packet['phase'] == 'selected':
        total = validate_selection(packet['selection'])
        require(packet['custody']['selectionSha256'] == digest(canonical(packet['selection'])) and packet['custody']['totalFiles'] == len(packet['selection']) and packet['custody']['totalBytes'] == total, 'selection-custody-mismatch')
        seen = set()
        for item in packet['items']:
            keys(item, {'fileIndex', 'offset', 'bytes', 'sha256', 'contentBase64'})
            integer(item['fileIndex'], 0, len(packet['selection']) - 1)
            chosen = packet['selection'][item['fileIndex']]
            integer(item['offset'], 0, chosen['bytes']); integer(item['bytes'], 0, PART_BYTES)
            require(item['offset'] < chosen['bytes'] or chosen['bytes'] == 0 and item['offset'] == 0, 'trailing-empty-part-rejected')
            require(item['offset'] % PART_BYTES == 0 and item['bytes'] == min(PART_BYTES, chosen['bytes'] - item['offset']), 'invalid-part-range')
            require((item['fileIndex'], item['offset']) not in seen, 'duplicate-part')
            seen.add((item['fileIndex'], item['offset']))
            require(type(item['contentBase64']) is str and len(item['contentBase64']) <= PART_BYTES * 2, 'invalid-part-encoding')
            try: raw = base64.b64decode(item['contentBase64'], validate=True)
            except (ValueError, UnicodeError): raise Rejected('invalid-part-encoding') from None
            require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'part-digest-mismatch')
            require(not SECRET.search(raw), 'secret-pattern-rejected')
        expected_parts = sum(max(1, (x['bytes'] + PART_BYTES - 1) // PART_BYTES) for x in packet['selection'])
        require(packet['custody']['totalParts'] == expected_parts, 'part-count-mismatch')
    else:
        require(packet['selection'] == [], 'inventory-cannot-select-content')
        for item in packet['items']:
            keys(item, {'sourcePath', 'repositoryPath', 'kind', 'indexObject', 'indexMode', 'bytes', 'sha256', 'state'})
            source_path(item['sourcePath']); relative(item['repositoryPath'])
            require(item['sourcePath'] == CANONICAL + '/' + item['repositoryPath'], 'inventory-path-mismatch')
            require(item['kind'] in {'source-text', 'artwork'}, 'invalid-inventory-kind')
            require(item['state'] in {'present', 'present-unhashed', 'missing', 'uninspected', 'unreadable-or-excluded', 'excluded-nonregular-index'}, 'invalid-inventory-state')
            require(item['indexObject'] is None or type(item['indexObject']) is str and GIT_SHA.fullmatch(item['indexObject']), 'invalid-index-object')
            require(item['indexMode'] is None or item['indexMode'] in {'100644', '100755', '120000', '160000'}, 'invalid-index-mode')
            if item['state'] == 'present':
                integer(item['bytes'], 0, MAX_FILE)
                require(type(item['sha256']) is str and SHA.fullmatch(item['sha256']), 'invalid-inventory-digest')
            elif item['state'] == 'present-unhashed':
                integer(item['bytes'], 0, 2**63 - 1)
                require(item['sha256'] is None, 'unhashed-metadata-must-not-claim-digest')
            else: require(item['bytes'] is None and item['sha256'] is None, 'invalid-missing-metadata')
    require(len(canonical(packet)) <= MAX_PACKET, 'packet-too-large')
    return packet

def validate_packet_set(prepared):
    """Whole-set custody and full-file checks before any root-owned deposit."""
    require(type(prepared) is list and 0 < len(prepared) <= 2**63 - 1, 'invalid-packet-set-count')
    jobs = set(); groups = {}
    for packet in prepared:
        validate_packet(packet)
        require(packet['jobId'] not in jobs, 'duplicate-job-id'); jobs.add(packet['jobId'])
        key = (packet['phase'], packet['custody']['selectionSha256'])
        groups.setdefault(key, []).append(packet)
    for (phase, _), group in groups.items():
        first = group[0]
        require(len(group) == first['batch']['count'] and {p['batch']['index'] for p in group} == set(range(1, len(group) + 1)), 'incomplete-packet-set')
        require(all(p['batch']['count'] == len(group) and p['custody'] == first['custody'] and p['repository'] == first['repository'] and p['selection'] == first['selection'] for p in group), 'mixed-packet-set')
        all_items = [item for packet in sorted(group, key=lambda p: p['batch']['index']) for item in packet['items']]
        require(len(all_items) == first['custody']['totalParts'], 'incomplete-item-set')
        if phase == 'inventory':
            require(len(all_items) == first['custody']['totalFiles'] and digest(canonical(all_items)) == first['custody']['selectionSha256'], 'inventory-custody-mismatch')
            require(sum(x['bytes'] or 0 for x in all_items) == first['custody']['totalBytes'], 'inventory-byte-count-mismatch')
            require(len({x['sourcePath'] for x in all_items}) == len(all_items), 'duplicate-inventory-path')
        else:
            for index, chosen in enumerate(first['selection']):
                chunks = sorted([x for x in all_items if x['fileIndex'] == index], key=lambda x: x['offset'])
                require(bool(chunks), 'selected-file-missing')
                result = bytearray(); offset = 0
                for chunk in chunks:
                    require(chunk['offset'] == offset, 'noncontiguous-file-parts')
                    raw = base64.b64decode(chunk['contentBase64'], validate=True)
                    result.extend(raw); offset += len(raw)
                require(len(result) == chosen['bytes'] and digest(result) == chosen['sha256'], 'whole-source-pin-mismatch')
                check_body(bytes(result), chosen['kind'])
    return prepared


def private_output(directory, prepared):
    validate_packet_set(prepared)
    os.mkdir(directory, 0o700)
    for packet in prepared:
        path = os.path.join(directory, packet['jobId'] + '.json')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out: out.write(canonical(packet)); out.flush(); os.fsync(out.fileno())
    manifest = {'schemaVersion': 'offmenu-local-source-packet-set/1', 'packets': [
        {'jobId': x['jobId'], 'phase': x['phase'], 'bytes': len(canonical(x)), 'sha256': digest(canonical(x)), 'batch': x['batch'], 'custody': x['custody']} for x in prepared]}
    fd = os.open(os.path.join(directory, 'packet-set.json'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out: out.write(canonical(manifest))
    return manifest

def validate_packet_directory(directory):
    """Validate direct-transfer custody without loading all inventory items."""
    raw, _ = read_regular(os.path.join(directory, 'packet-set.json'), 2**63 - 1)
    manifest = decode(raw)
    keys(manifest, {'schemaVersion', 'packets'})
    require(manifest['schemaVersion'] == 'offmenu-local-source-packet-set/1'
            and type(manifest['packets']) is list and bool(manifest['packets']), 'invalid-packet-set')
    groups = {}; jobs = set()
    for receipt in manifest['packets']:
        keys(receipt, {'jobId', 'phase', 'bytes', 'sha256', 'batch', 'custody'})
        require(type(receipt['jobId']) is str and JOB.fullmatch(receipt['jobId']), 'invalid-job-id')
        require(receipt['jobId'] not in jobs, 'duplicate-job-id'); jobs.add(receipt['jobId'])
        require(receipt['phase'] in {'inventory', 'selected'}, 'invalid-phase')
        integer(receipt['bytes'], 1, MAX_PACKET)
        require(type(receipt['sha256']) is str and SHA.fullmatch(receipt['sha256']), 'invalid-packet-digest')
        keys(receipt['batch'], {'index', 'count'})
        integer(receipt['batch']['count'], 1, 2**63 - 1)
        integer(receipt['batch']['index'], 1, receipt['batch']['count'])
        require(type(receipt['custody']) is dict and type(receipt['custody'].get('selectionSha256')) is str,
                'invalid-custody-digest')
        groups.setdefault((receipt['phase'], receipt['custody']['selectionSha256']), []).append(receipt)
    for (phase, _), receipts in groups.items():
        receipts.sort(key=lambda x: x['batch']['index'])
        first = None; selected = []; total = 0; size = 0; previous_path = None
        identity = hashlib.sha256(); identity.update(b'[')
        for number, receipt in enumerate(receipts, 1):
            require(receipt['batch'] == {'index': number, 'count': len(receipts)}, 'incomplete-packet-set')
            raw, _ = read_regular(os.path.join(directory, receipt['jobId'] + '.json'), MAX_PACKET)
            require(len(raw) == receipt['bytes'] and digest(raw) == receipt['sha256'], 'packet-set-pin-mismatch')
            packet = validate_packet(decode(raw), receipt['jobId'])
            require(packet['phase'] == receipt['phase'] and packet['batch'] == receipt['batch']
                    and packet['custody'] == receipt['custody'], 'packet-set-metadata-mismatch')
            if first is None:
                first = {key: packet[key] for key in ('repository', 'selection', 'custody')}
            else:
                require(all(packet[key] == first[key] for key in first), 'mixed-packet-set')
            if phase == 'selected': selected.append(packet); continue
            for item in packet['items']:
                path = item['repositoryPath']
                require(previous_path is None or previous_path < path, 'inventory-order-or-duplicate-path')
                previous_path = path
                if total: identity.update(b',')
                identity.update(canonical(item)[:-1]); total += 1; size += item['bytes'] or 0
        if phase == 'selected': validate_packet_set(selected)
        else:
            identity.update(b']\n')
            require(total == first['custody']['totalFiles'] == first['custody']['totalParts'], 'incomplete-item-set')
            require(size == first['custody']['totalBytes'], 'inventory-byte-count-mismatch')
            require(identity.hexdigest() == first['custody']['selectionSha256'], 'inventory-custody-mismatch')
    return manifest

def stage(directory):
    require(os.geteuid() == 0, 'stage-requires-explicit-owner-sudo')
    account = pwd.getpwnam('offmenu-runner')
    output = os.path.dirname(STAGING)
    parent_fd = open_absolute(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        parent = os.fstat(parent_fd)
        require(parent.st_uid == account.pw_uid and stat.S_IMODE(parent.st_mode) == 0o700, 'unexpected-output-directory-owner-mode')
        created = False
        try:
            os.mkdir('source-export', 0o750, dir_fd=parent_fd); created = True
        except FileExistsError: pass
        dest_fd = os.open('source-export', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            if created:
                os.fchmod(dest_fd, 0o750); os.fchown(dest_fd, 0, account.pw_gid)
            info = os.fstat(dest_fd)
            require(info.st_gid == account.pw_gid, 'unexpected-staging-directory-group')
            require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o750, 'unexpected-staging-directory-owner-mode')
            manifest_raw, _ = read_regular(os.path.join(directory, 'packet-set.json'), MAX_PACKET)
            manifest = decode(manifest_raw); keys(manifest, {'schemaVersion', 'packets'})
            require(manifest['schemaVersion'] == 'offmenu-local-source-packet-set/1' and type(manifest['packets']) is list and len(manifest['packets']) <= 9999, 'invalid-packet-set')
            # Validate all inputs before any publication. Never overwrite a job.
            prepared = []; decoded = []
            for item in manifest['packets']:
                keys(item, {'jobId', 'phase', 'bytes', 'sha256', 'batch', 'custody'})
                require(type(item['jobId']) is str and JOB.fullmatch(item['jobId']), 'invalid-job-id')
                raw, _ = read_regular(os.path.join(directory, item['jobId'] + '.json'), MAX_PACKET)
                packet = validate_packet(decode(raw), item['jobId']); raw = canonical(packet)
                require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'packet-set-pin-mismatch')
                require(packet['phase'] == item['phase'] and packet['batch'] == item['batch'] and packet['custody'] == item['custody'], 'packet-set-metadata-mismatch')
                try: os.stat(item['jobId'] + '.json', dir_fd=dest_fd, follow_symlinks=False)
                except FileNotFoundError: pass
                else: raise Rejected('staged-job-already-exists-no-overwrite')
                prepared.append((item['jobId'], raw)); decoded.append(packet)
            validate_packet_set(decoded)
            for job_id, raw in prepared:
                fd = os.open(job_id + '.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o440, dir_fd=dest_fd)
                with os.fdopen(fd, 'wb') as out:
                    os.fchmod(out.fileno(), 0o440); os.fchown(out.fileno(), 0, account.pw_gid); out.write(raw); out.flush(); os.fsync(out.fileno())
        finally: os.close(dest_fd)
    finally: os.close(parent_fd)
    return {'schemaVersion': 'offmenu-local-source-stage/1', 'packetCount': len(prepared), 'overwrites': False, 'serviceChanged': False}

def receive(job_id, artifact):
    require(JOB.fullmatch(job_id), 'invalid-job-id')
    raw, info = read_regular(STAGING + '/' + job_id + '.json', MAX_PACKET)
    require(info.st_uid == 0 and info.st_gid == os.getgid() and stat.S_IMODE(info.st_mode) == 0o440, 'staged-packet-not-owner-approved')
    packet = validate_packet(decode(raw), job_id)
    raw = canonical(packet)
    # Artifact destination is supplied solely by the reviewed workflow through
    # RUNNER_TEMP, never by packet/request paths. No uploaded code is executed.
    fd = os.open(artifact, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out: out.write(raw); out.flush(); os.fsync(out.fileno())
    return {'schemaVersion': SUMMARY, 'phase': packet['phase'], 'packetBytes': len(raw),
            'packetSha256': digest(raw), 'selectionSha256': packet['custody']['selectionSha256'],
            'batchIndex': packet['batch']['index'], 'batchCount': packet['batch']['count'],
            'totalFiles': packet['custody']['totalFiles'], 'totalBytes': packet['custody']['totalBytes'],
            'itemCount': len(packet['items']), 'sourceContentsIncluded': packet['phase'] == 'selected'}

def sanitize_report(value):
    keys(value, {'schemaVersion', 'phase', 'packetBytes', 'packetSha256', 'selectionSha256', 'batchIndex', 'batchCount', 'totalFiles', 'totalBytes', 'itemCount', 'sourceContentsIncluded'})
    require(value['schemaVersion'] == SUMMARY and value['phase'] in {'inventory', 'selected'}, 'invalid-summary')
    require(type(value['sourceContentsIncluded']) is bool and value['sourceContentsIncluded'] == (value['phase'] == 'selected'), 'invalid-summary')
    for key in ('packetSha256', 'selectionSha256'): require(type(value[key]) is str and SHA.fullmatch(value[key]), 'invalid-summary')
    integer(value['packetBytes'], 1, MAX_PACKET); integer(value['batchCount'], 1, 2**63 - 1 if value['phase'] == 'inventory' else 9999); integer(value['batchIndex'], 1, value['batchCount'])
    integer(value['totalFiles'], 0, 2**63 - 1 if value['phase'] == 'inventory' else MAX_FILES); integer(value['totalBytes'], 0, MAX_TOTAL if value['phase'] == 'selected' else 2**63 - 1); integer(value['itemCount'], 0, MAX_PACKET if value['phase'] == 'inventory' else MAX_FILES)
    return dict(value)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory'); inv.add_argument('--job-prefix', required=True); inv.add_argument('--output-directory', required=True)
    inv.add_argument('--include-pinned-anchor-docs', action='store_true')
    sel = sub.add_parser('select'); sel.add_argument('--job-prefix', required=True); sel.add_argument('--selection', required=True); sel.add_argument('--output-directory', required=True)
    sta = sub.add_parser('stage'); sta.add_argument('--packet-directory', required=True)
    rec = sub.add_parser('receive'); rec.add_argument('--job-id', required=True); rec.add_argument('--artifact', required=True)
    args = p.parse_args(argv); os.umask(0o077)
    try:
        if args.command == 'inventory':
            require(os.geteuid() != 0, 'inventory-must-run-as-normal-owner')
            result = inventory_output(args.job_prefix, args.output_directory, include_anchors=args.include_pinned_anchor_docs)
        elif args.command == 'select':
            require(os.geteuid() != 0, 'selection-must-run-as-normal-owner')
            manifest_raw, _ = read_regular(args.selection, MAX_PACKET)
            manifest = decode(manifest_raw); keys(manifest, {'repository', 'selection'})
            require(repo_metadata(CANONICAL) == manifest['repository'], 'repository-head-changed-reselect')
            selection = manifest['selection']; pieces = selected_parts(selection)
            require(repo_metadata(CANONICAL) == manifest['repository'], 'repository-head-changed-during-selection')
            result = private_output(args.output_directory, packets('selected', args.job_prefix, manifest['repository'], selection, pieces))
        elif args.command == 'stage': result = stage(args.packet_directory)
        else: result = receive(args.job_id, args.artifact)
        print(json.dumps(result, sort_keys=True)); return 0
    except (Rejected, OSError, ValueError, KeyError, UnicodeError) as error:
        print(json.dumps({'schemaVersion': 'offmenu-local-source-error/1', 'errorCode': str(error) if isinstance(error, Rejected) else 'operation-failed-no-private-details'}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
