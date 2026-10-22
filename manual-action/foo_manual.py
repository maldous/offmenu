#!/usr/bin/env python3
"""Bounded, offline Foo diagnostics and supplier source-review preparation.

Never imports OffMenu code, executes archive members, loads data or uses network.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import tarfile
import time
import zlib

SUPPLIER_ARCHIVE = Path('/home/user/Documents/Codex/2026-10-22/worker19-supplier11529-resolution/portable-supplier-review.tar.gz')
EXPECTED_SHA256_PREFIX = 'e2508555'
KNOWN_ROOTS = (Path('/home/user/src/offmenu-data'), SUPPLIER_ARCHIVE.parent)
MAX_COMPRESSED = 16 * 1024 * 1024
MAX_EXPANDED = 32 * 1024 * 1024
MAX_MEMBER = 2 * 1024 * 1024
MAX_MEMBERS = 256
MAX_SECONDS = 30
NAME_MATCH = re.compile(r'osm|openstreetmap|planet|recip|inventory|receipt|manifest|custody|acquisition|progress|cache', re.I)
SECRET_PATH = re.compile(r'(^|/)(\.git|\.ssh|\.aws|\.env(?:\..*)?|credentials?|secrets?|id_rsa|id_ed25519)(/|$)|\.(pem|key|p12|pfx|keystore)$', re.I)
DATA_PATH = re.compile(r'(^|/)(raw|datasets?|downloads?|retained|databases?)(/|$)|\.(db|sqlite3?|csv|tsv|parquet|pbf|osm|pdf|jsonl|ndjson|gz|bz2|zip|tar|xz|jpg|png|bin|part)$', re.I)
SOURCE_SUFFIXES = {'.py', '.md', '.rst', '.txt', '.sh', '.toml', '.yaml', '.yml', '.json', '.schema', '.js', '.mjs', '.ts'}
# Deliberately heuristic; a passing scan is NOT a proof that source contains no secrets.
SECRET_CONTENT = re.compile(r'(?im)-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{20,})\b|^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|SECRET|ACCESS_TOKEN|API_KEY)[A-Z0-9_]*\s*=\s*[\"\']?[^\s\"\'{}$]{8,}')


class Deadline(Exception):
    """Stops the action; not swallowed by per-path error handlers."""


class Refusal(Exception):
    """Fail closed without printing source content or private exception details."""


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def no_symlink_path(path):
    """Reject symlinks in every existing path component, not just the leaf."""
    p = Path(os.path.abspath(path))
    for node in (p, *p.parents):
        try:
            if stat.S_ISLNK(node.lstat().st_mode):
                raise Refusal('symlink_path_refused')
        except FileNotFoundError:
            continue
    return p


def open_dir(path):
    """Walk pinned directory FDs: no symlink-following race in path parents."""
    parts = Path(os.path.abspath(path)).parts
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def file_meta(path):
    result = {'path': str(path)}
    try:
        p = Path(os.path.abspath(path))
        parent = open_dir(p.parent)
        try:
            s = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(parent)
        if stat.S_ISLNK(s.st_mode):
            raise Refusal('symlink_path_refused')
        result.update(status='present', kind=('file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'special_refused'), bytes=s.st_size, mtime_ns=s.st_mtime_ns)
    except FileNotFoundError:
        result['status'] = 'missing'
    except PermissionError:
        result['status'] = 'unreadable'
    except (OSError, Refusal):
        result['status'] = 'refused_or_unreadable'
    return result


def open_regular(path):
    p = Path(os.path.abspath(path))
    parent = open_dir(p.parent)
    try:
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode):
            raise Refusal('not_regular_file')
        return os.fdopen(fd, 'rb'), s
    except BaseException:
        os.close(fd)
        raise


def fingerprint(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


class BoundedReader:
    def __init__(self, source, limit):
        self.source, self.remaining = source, limit

    def read(self, size=-1):
        if size < 0:
            size = self.remaining + 1
        data = self.source.read(min(size, self.remaining + 1))
        self.remaining -= len(data)
        if self.remaining < 0:
            raise Refusal('expanded_archive_limit')
        return data


def safe_member_name(name):
    if not name or len(name) > 240 or '\\' in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise Refusal('unsafe_member_name')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name:
        raise Refusal('unsafe_member_path')
    # GNU tar convention './' is allowed, but canonical collisions are rejected.
    clean = str(p)
    if clean in {'.', ''}:
        return '.'
    if SECRET_PATH.search(clean):
        raise Refusal('secret_looking_member_path')
    if DATA_PATH.search(clean):
        raise Refusal('dataset_looking_member_path')
    return clean


def source_content_allowed(name, data):
    if Path(name).suffix.lower() not in SOURCE_SUFFIXES and Path(name).name not in {'LICENSE', 'NOTICE', 'Makefile'}:
        raise Refusal('non_source_member_extension')
    try:
        body = data.decode('utf-8')
    except UnicodeDecodeError:
        raise Refusal('non_utf8_member') from None
    if '\x00' in body or SECRET_CONTENT.search(body):
        raise Refusal('binary_or_secret_looking_content')
    # JSON is restricted to small descriptive metadata/schema, not row payloads.
    if Path(name).suffix.lower() == '.json':
        if not re.search(r'manifest|schema|provenance|package|source.state|receipt|fixture', Path(name).name, re.I):
            raise Refusal('json_not_named_as_source_metadata')
        try:
            obj = json.loads(body)
        except (ValueError, RecursionError):
            raise Refusal('invalid_source_metadata_json') from None
        if not isinstance(obj, dict):
            raise Refusal('json_rows_refused')


def inspect_supplier(path=SUPPLIER_ARCHIVE, expected_prefix=EXPECTED_SHA256_PREFIX):
    """Internal parameters support generated tests; CLI exposes no archive override."""
    meta = file_meta(path)
    if meta['status'] != 'present':
        return {'status': 'blocked', 'reason': meta['status'], 'archive': meta}
    try:
        with open_regular(path)[0] as f:
            before = os.fstat(f.fileno())
            if before.st_size > MAX_COMPRESSED:
                raise Refusal('compressed_archive_limit')
            raw = f.read(MAX_COMPRESSED + 1)
            if len(raw) > MAX_COMPRESSED or len(raw) != before.st_size:
                raise Refusal('compressed_archive_changed_or_limit')
            if fingerprint(before) != fingerprint(os.fstat(f.fileno())):
                raise Refusal('archive_changed')
        digest = hashlib.sha256(raw).hexdigest()
        if not digest.startswith(expected_prefix):
            return {'status': 'blocked', 'reason': 'sha256_prefix_mismatch', 'archive': meta, 'expected_sha256_prefix': expected_prefix, 'observed_sha256': digest}
        manifest, seen, total = [], set(), 0
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode='rb') as gz:
            expanded = gz.read(MAX_EXPANDED + 1)
        if len(expanded) > MAX_EXPANDED:
            raise Refusal('expanded_archive_limit')
        with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as tf:
            for member in tf:
                if len(manifest) >= MAX_MEMBERS:
                    raise Refusal('archive_member_limit')
                name = safe_member_name(member.name)
                if name in seen:
                    raise Refusal('duplicate_member_path')
                seen.add(name)
                if member.issym() or member.islnk() or member.issparse() or not (member.isfile() or member.isdir()):
                    raise Refusal('unsafe_member_type')
                if member.size < 0 or member.size > MAX_MEMBER or (member.isdir() and member.size):
                    raise Refusal('member_size_limit')
                if member.pax_headers and set(member.pax_headers) - {'mtime', 'atime', 'ctime', 'path', 'size'}:
                    raise Refusal('unsupported_archive_metadata')
                row = {'path': name, 'kind': 'directory' if member.isdir() else 'file', 'bytes': member.size}
                if member.isfile():
                    stream = tf.extractfile(member)
                    data = stream.read(MAX_MEMBER + 1)
                    if len(data) != member.size:
                        raise Refusal('member_length_mismatch')
                    total += len(data)
                    source_content_allowed(name, data)
                    row['sha256'] = hashlib.sha256(data).hexdigest()
                manifest.append(row)
            if expanded[tf.offset:].strip(b'\0'):
                raise Refusal('trailing_archive_payload')
        if not any(x['kind'] == 'file' for x in manifest):
            raise Refusal('empty_source_archive')
        # Bytes inspected are the bytes checksummed; no extraction or rewrite occurs.
        return {'status': 'inspection_pass_manual_review_required', 'archive': meta, 'expected_sha256_prefix': expected_prefix, 'observed_sha256': digest, 'compressed_bytes': len(raw), 'source_bytes': total, 'manifest': sorted(manifest, key=lambda r: r['path']), 'transfer': 'NOT_UPLOADED', 'next': 'Review member list and source locally; manually attach only this unchanged archive and this manifest after confirming no secrets/raw data. Prefix match is a historical identity hint, not full-digest authentication.'}
    except (Refusal, OSError, EOFError, tarfile.TarError, ValueError, zlib.error) as error:
        reason = str(error) if isinstance(error, Refusal) else type(error).__name__
        return {'status': 'blocked', 'reason': reason, 'archive': meta}


def validate_root(root):
    p = no_symlink_path(root)
    # Never walk a whole host, home, /proc, mounts, or credential directory.
    if len(p.parts) < 5 or any(x in {'.ssh', '.aws', '.codex', '.git', 'proc', 'sys', 'dev'} for x in p.parts):
        raise Refusal('inventory_root_too_broad_or_sensitive')
    return p


def inventory(roots, max_entries=1000, max_depth=3, max_results=200):
    start = time.monotonic()
    result = {'mode': 'metadata_only_no_body_reads_no_hashing', 'roots': [], 'matches': [], 'entries_seen': 0, 'truncated': False, 'limits': {'entries': max_entries, 'depth': max_depth, 'results': max_results, 'seconds': 10}}
    for root in roots:
        try:
            root = validate_root(root)
        except Refusal as e:
            result['roots'].append({'path': str(root), 'status': str(e)})
            continue
        observed = file_meta(root)
        result['roots'].append(observed)
        if observed.get('kind') != 'directory':
            continue
        stack = [(root, 0)]
        while stack:
            parent, depth = stack.pop()
            try:
                directory_fd = open_dir(parent)
                try:
                    entries = os.scandir(directory_fd)
                finally:
                    os.close(directory_fd)
                with entries:
                    for entry in entries:
                        if result['entries_seen'] >= max_entries or len(result['matches']) >= max_results or time.monotonic() - start > 10:
                            result['truncated'] = True
                            return result
                        result['entries_seen'] += 1
                        if SECRET_PATH.search(entry.name) or entry.is_symlink():
                            continue
                        if NAME_MATCH.search(entry.name):
                            result['matches'].append(file_meta(parent / entry.name))
                        if depth < max_depth and entry.is_dir(follow_symlinks=False):
                            stack.append((parent / entry.name, depth + 1))
            except (OSError, Refusal):
                result.setdefault('unreadable_directories', 0)
                result['unreadable_directories'] += 1
    result['matches'].sort(key=lambda r: r['path'])
    return result


def jobs(proc=Path('/proc'), limit=4096):
    """Observe PID, short executable name and state only; never args/environ/fds."""
    out = {'scope': 'bounded Linux /proc metadata; no command lines/environment', 'jobs': [], 'entries_seen': 0, 'truncated': False}
    try:
        with os.scandir(proc) as entries:
            for entry in entries:
                if out['entries_seen'] >= limit:
                    out['truncated'] = True
                    break
                out['entries_seen'] += 1
                if not entry.name.isdecimal() or entry.is_symlink():
                    continue
                try:
                    with open_regular(Path(entry.path) / 'stat')[0] as f:
                        data = f.read(2048).decode('utf-8', errors='replace')
                    left, right = data.find('('), data.rfind(')')
                    if left < 0 or right <= left:
                        continue
                    comm = data[left + 1:right][:80]
                    state = data[right + 2:right + 3]
                    out['jobs'].append({'pid': int(entry.name), 'name': comm, 'state': state})
                except (OSError, Refusal):
                    continue
        out['jobs'].sort(key=lambda r: r['pid'])
    except OSError:
        out['status'] = 'unavailable'
    return out


def disk(paths):
    out = []
    for path in paths:
        try:
            fd = open_dir(path)
            try:
                s = os.fstatvfs(fd)
            finally:
                os.close(fd)
            out.append({'path': str(path), 'status': 'observed', 'total_bytes': s.f_blocks * s.f_frsize, 'available_bytes': s.f_bavail * s.f_frsize})
        except (OSError, Refusal):
            out.append({'path': str(path), 'status': 'unavailable'})
    return out


def preflight(roots):
    paths = list(dict.fromkeys([str(SUPPLIER_ARCHIVE), *(str(x) for x in roots)]))
    return {'known_paths': [file_meta(p) for p in paths], 'disk': disk(roots), 'processes': jobs(), 'loads': {'implemented': False, 'status': 'STOP', 'reason': 'No accepted exact caller/input/custody/resource contract; no HTML/PDF/UniTools/supplier load subcommand.'}}


def write_result(output, result):
    output = no_symlink_path(output)
    # Exclusive creation: never overwrite a receipt, source, database or another run.
    parent = open_dir(output.parent)
    try:
        fd = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=True, indent=2, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def public_summary(result):
    """No host paths, PIDs, executable names, member names or source bodies."""
    out = {'schema': 'offmenu-manual-action-return/1', 'observed_at': result['observed_at'], 'command': result['command'], 'data_loads': 'not_implemented', 'network': 'none', 'scope': 'bounded_snapshot_not_global_absence_or_completion', 'errors': []}
    if 'error' in result:
        out['errors'].append(result['error'])
    if 'preflight' in result:
        p = result['preflight']
        counts = {}
        for row in p['known_paths']:
            counts[row['status']] = counts.get(row['status'], 0) + 1
        out['preflight'] = {'path_status_counts': counts, 'processes_observed': len(p['processes']['jobs']), 'process_scan_truncated': p['processes']['truncated'], 'disks_observed': sum(x['status'] == 'observed' for x in p['disk']), 'loads': 'STOP_not_implemented'}
    if 'inventory' in result:
        inv = result['inventory']
        out['inventory'] = {'roots_checked': len(inv['roots']), 'entries_seen': inv['entries_seen'], 'matches_found': len(inv['matches']), 'truncated': inv['truncated'], 'mode': inv['mode'], 'unreadable_directories': inv.get('unreadable_directories', 0)}
    if 'supplier' in result:
        sup = result['supplier']
        out['supplier'] = {key: sup[key] for key in ('status', 'reason', 'expected_sha256_prefix', 'observed_sha256', 'compressed_bytes', 'source_bytes') if key in sup}
        out['supplier']['member_count'] = len(sup.get('manifest', []))
        out['supplier']['transfer'] = 'NOT_UPLOADED'
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preflight', 'inventory', 'supplier', 'collect'])
    parser.add_argument('--return-output', help='Optional new sanitized count/status/digest-only JSON, safe for explicit review and return')
    parser.add_argument('--output', required=True, help='New local JSON file; existing files are never overwritten')
    parser.add_argument('--inventory-root', action='append', default=[], help='Explicit narrow known directory, max 8; metadata only, no body reads')
    args = parser.parse_args(argv)
    if len(args.inventory_root) > 8:
        parser.error('at most eight explicit roots')
    roots = [Path(p) for p in args.inventory_root] or list(KNOWN_ROOTS)
    for root in roots:
        try:
            validate_root(root)
        except Refusal as e:
            parser.error(str(e))
    result = {'schema': 'offmenu-manual-action/1', 'observed_at': stamp(), 'command': args.command, 'writes': 'only exclusive requested local result JSON', 'network': 'none', 'data_loads': 'not_implemented', 'privacy': 'Local operational metadata. Review before sharing; do not commit this result.', 'scope_limit': 'No global absence/completion/custody conclusion; bounded snapshot only.'}
    def timeout(_signum, _frame):
        raise Deadline('wall_time_limit')
    if not hasattr(signal, 'SIGALRM'):
        parser.error('Linux/POSIX with SIGALRM required')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(MAX_SECONDS)
    exit_code = 0
    try:
        if args.command in {'preflight', 'collect'}:
            result['preflight'] = preflight(roots)
        if args.command in {'inventory', 'collect'}:
            result['inventory'] = inventory(roots)
        if args.command in {'supplier', 'collect'}:
            result['supplier'] = inspect_supplier()
            if result['supplier']['status'] == 'blocked':
                exit_code = 2
    except (Deadline, Refusal, OSError) as e:
        result['error'] = str(e) if isinstance(e, (Deadline, Refusal)) else type(e).__name__
        exit_code = 2
    finally:
        signal.alarm(0)
    try:
        write_result(args.output, result)
        if args.return_output:
            write_result(args.return_output, public_summary(result))
    except (OSError, Refusal) as e:
        print('Result not written: ' + (str(e) if isinstance(e, Refusal) else type(e).__name__), file=sys.stderr)
        return 2
    print('Saved local metadata result: ' + str(args.output))
    print('No upload, load, database change or job modification occurred. Only metadata and the fixed supplier capsule were inspected.')
    if exit_code:
        print('One or more checks were blocked; inspect the JSON. Existing data/jobs were preserved.')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
