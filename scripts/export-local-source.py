#!/usr/bin/env python3
"""One-shot OffMenu source custody; never executes, edits, or pushes source files."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import resource
import stat
import subprocess
import sys
import tempfile

SCHEMA = 'offmenu-local-source-packet/1'
SUMMARY = 'offmenu-local-source-summary/1'
CANONICAL = '/home/user/src/offmenu'
EXTERNAL = '/home/user/src/offmenu-data/runtime/layout-migration'
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
        '.md', '.rst', '.txt', '.json', '.toml', '.yaml', '.yml', '.sql', '.sh', '.svg'}
ARTWORK = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.otf'}
ROOT_NAMES = {'Dockerfile', 'Makefile', 'LICENSE', 'NOTICE', '.gitignore', '.gitattributes'}
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
    require(not any(x.lower() in DENIED or x.lower().startswith('.env') or x.lower().endswith(('.pem', '.key', '.p12', '.pfx')) for x in p.parts), 'excluded-path')
    require(all(not x.startswith('.') or x in ('.github', '.agents', '.gitignore', '.gitattributes') for x in p.parts), 'excluded-hidden-path')
    require(p.suffix.lower() in TEXT | ARTWORK or p.name in ROOT_NAMES, 'unsupported-file-kind')
    return p

def source_path(value):
    require(type(value) is str, 'invalid-source-path')
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

def inventory(root=CANONICAL):
    root_fd = open_absolute(root, os.O_RDONLY | os.O_DIRECTORY)
    os.close(root_fd)
    before = repo_metadata(root)
    entries = {}
    raw_index = safe_git(root, ['ls-files', '--stage', '-z'])
    for entry in raw_index.split(b'\0'):
        if not entry: continue
        try:
            meta, raw_path = entry.split(b'\t', 1)
            mode, object_id, stage = meta.decode('ascii').split(' ')
            path = raw_path.decode('utf-8')
        except (ValueError, UnicodeError): raise Rejected('invalid-git-index') from None
        require(stage == '0', 'unmerged-index-needs-owner-review')
        entries[path] = {'indexObject': object_id, 'indexMode': mode}
    require(len(entries) <= MAX_FILES, 'inventory-entry-limit-no-truncation')
    excluded = 0; visited = 0; hashed_bytes = 0; candidates = set(entries)
    # Descriptor walk, without symlink ancestors or directory reopens. Only the
    # canonical checkout is enumerated; external runtime is never traversed.
    def walk(fd, prefix='', depth=0):
        nonlocal excluded, visited
        require(depth <= 64, 'inventory-depth-limit-no-truncation')
        for name in sorted(os.listdir(fd)):
            visited += 1
            require(visited <= 200000, 'inventory-entry-limit-no-truncation')
            rel = prefix + name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                if name.lower() in DENIED or name.startswith('.') and name not in {'.github', '.agents'}:
                    excluded += 1; continue
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try: walk(child, rel + '/', depth + 1)
                finally: os.close(child)
            elif stat.S_ISLNK(info.st_mode):
                excluded += 1
            else: candidates.add(rel)
            require(len(candidates) <= MAX_FILES, 'inventory-entry-limit-no-truncation')
    root_fd = open_absolute(root, os.O_RDONLY | os.O_DIRECTORY)
    try: walk(root_fd)
    finally: os.close(root_fd)
    items = []
    for path in sorted(candidates):
        try: p = relative(path)
        except Rejected: excluded += 1; continue
        source = root + '/' + path
        tracked = entries.get(path)
        item = {'sourcePath': source, 'repositoryPath': path,
                'kind': 'artwork' if p.suffix.lower() in ARTWORK else 'source-text',
                'indexObject': tracked['indexObject'] if tracked else None,
                'indexMode': tracked['indexMode'] if tracked else None,
                'bytes': None, 'sha256': None, 'state': 'uninspected'}
        if tracked and tracked['indexMode'] not in ('100644', '100755'):
            item['state'] = 'excluded-nonregular-index'; items.append(item); continue
        try:
            fd = open_absolute(source)
            try: info = os.fstat(fd)
            finally: os.close(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'not-single-regular-file')
            if info.st_size > MAX_FILE or hashed_bytes + info.st_size > MAX_TOTAL:
                # Keep every eligible metadata entry; only checksum work is
                # bounded. Oversized/unhashed candidates are NOT export-ready.
                item.update(bytes=info.st_size, sha256=None, state='present-unhashed')
            else:
                raw, info = read_regular(source)
                hashed_bytes += len(raw)
                item.update(bytes=len(raw), sha256=digest(raw), state='present')
        except FileNotFoundError: item['state'] = 'missing'
        except Rejected:
            item['state'] = 'unreadable-or-excluded'
        except OSError: item['state'] = 'unreadable-or-excluded'
        items.append(item)
    require(repo_metadata(root) == before and safe_git(root, ['ls-files', '--stage', '-z']) == raw_index,
            'repository-metadata-changed-retry-inventory')
    return before, items, excluded

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
    integer(packet['batch']['count'], 1, 9999); integer(packet['batch']['index'], 1, packet['batch']['count'])
    keys(packet['repository'], {'head', 'branch'})
    require(type(packet['repository']['head']) is str and GIT_SHA.fullmatch(packet['repository']['head']), 'invalid-head')
    require(type(packet['repository']['branch']) is str and re.fullmatch(r'[A-Za-z0-9._/-]{1,256}', packet['repository']['branch']), 'invalid-branch')
    keys(packet['custody'], {'selectionSha256', 'totalFiles', 'totalBytes', 'totalParts', 'excludedEntries'})
    require(type(packet['custody']['selectionSha256']) is str and SHA.fullmatch(packet['custody']['selectionSha256']), 'invalid-custody-digest')
    for key in ('totalFiles', 'totalParts', 'excludedEntries'): integer(packet['custody'][key], 0, 1000000)
    integer(packet['custody']['totalBytes'], 0, MAX_TOTAL if packet['phase'] == 'selected' else 2**63 - 1)
    require(type(packet['items']) is list and len(packet['items']) <= MAX_FILES, 'invalid-packet-items')
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
    require(type(prepared) is list and 0 < len(prepared) <= 9999, 'invalid-packet-set-count')
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
    integer(value['packetBytes'], 1, MAX_PACKET); integer(value['batchCount'], 1, 9999); integer(value['batchIndex'], 1, value['batchCount'])
    integer(value['totalFiles'], 0, MAX_FILES); integer(value['totalBytes'], 0, MAX_TOTAL if value['phase'] == 'selected' else 2**63 - 1); integer(value['itemCount'], 0, MAX_FILES)
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
            repository, items, excluded = inventory()
            prepared = packets('inventory', args.job_prefix, repository, [], items, excluded)
            if args.include_pinned_anchor_docs:
                selection = []
                for anchor in ANCHORS:
                    raw, _ = read_regular(anchor['sourcePath'])
                    require(digest(raw) == anchor['sha256'], 'pinned-anchor-mismatch')
                    selection.append(dict(anchor, bytes=len(raw)))
                prepared += packets('selected', args.job_prefix + '-a', repository, selection, selected_parts(selection))
            result = private_output(args.output_directory, prepared)
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
