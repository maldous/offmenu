#!/usr/bin/env python3
"""Stage and verify a private, content-pinned Windmill runtime. Never cut over.

No execution, permission expansion, service changes, cleanup, or publication.
Preserves relative paths and opaque metadata bytes; excludes all runtime datasets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import re
import tempfile

VERSION = 1
RUNTIME = Path('.delivery/windmill-runtime')
RUNNER = 'tools/delivery/windmill_runner.py'
POLICY = 'tools/delivery/capacity-policy.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    path = Path(path).absolute()
    for component in [*reversed(path.parents), path]:
        if component.is_symlink():
            raise ValueError('Symlink input refused')
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('Nonregular input refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Nonregular input refused')
        if before.st_size > 16 * 1024**2:
            raise ValueError('Input exceeds bounded size')
        data = stream.read(16 * 1024**2 + 1)
        after = os.fstat(stream.fileno())
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('Input changed during read')
    return data


def relative(value):
    if not isinstance(value, str):
        raise ValueError('Invalid path type')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) != value:
        raise ValueError('Noncanonical manifest path')
    if not (value.startswith('scripts/windmill/') or value in (RUNNER, POLICY)):
        raise ValueError('Unselected manifest path')
    return value


def payload(source, candidate):
    source, candidate = Path(source).absolute(), Path(candidate).absolute()
    standard = json.loads(regular(candidate / 'repository-standard.json'))
    held = standard['runtime_hold_paths']
    if not held or len(held) != len(set(held)):
        raise ValueError('Invalid runtime hold inventory')
    if any(not relative(p).startswith('scripts/windmill/') for p in held):
        raise ValueError('Invalid runtime hold path')
    files = {p: regular(source / p) for p in held}
    files[POLICY] = regular(source / POLICY)
    files[RUNNER] = regular(candidate / RUNNER)
    policy = json.loads(files[POLICY])
    if policy.get('resource_accounting', 'reserved-maxima-v1') not in (
            'reserved-maxima-v1', 'observed-host-v1'):
        raise ValueError('Unrecognized accounting mode')
    return files


def records(files):
    return [{'path': p, 'bytes': len(b), 'sha256': digest(b)} for p, b in sorted(files.items())]


def fingerprint(rows):
    return digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


def verify(directory, expected_paths):
    directory = Path(directory).absolute()
    manifest = json.loads(regular(directory / 'manifest.json'))
    if (set(manifest) != {'version', 'fingerprint', 'files', 'cutover', 'state_root_unchanged', 'reader_access_qualified'}
            or manifest.get('version') != VERSION or manifest.get('cutover') is not False
            or manifest.get('reader_access_qualified') is not False
            or manifest.get('state_root_unchanged') != '/offmenu/data/.offmenu-platform'):
        raise ValueError('Invalid manifest contract')
    rows = manifest['files']
    if not isinstance(rows, list) or any(not isinstance(r, dict) or set(r) != {'path', 'bytes', 'sha256'}
            or type(r['bytes']) is not int or not 0 <= r['bytes'] <= 16 * 1024**2
            or not isinstance(r['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', r['sha256'])
            for r in rows):
        raise ValueError('Invalid manifest records')
    for row in rows:
        relative(row['path'])
    if {r['path'] for r in rows} != set(expected_paths) or not {RUNNER, POLICY} <= set(expected_paths):
        raise ValueError('Expected inventory mismatch')
    if not rows or len(rows) != len({r['path'] for r in rows}):
        raise ValueError('Invalid manifest inventory')
    if fingerprint(rows) != manifest['fingerprint'] or directory.name != manifest['fingerprint']:
        raise ValueError('Manifest identity mismatch')
    for row in rows:
        data = regular(directory / relative(row['path']))
        if len(data) != row['bytes'] or digest(data) != row['sha256']:
            raise ValueError('Runtime content mismatch')
    expected_directories = {directory}
    for row in rows:
        expected_directories.update(p for p in (directory / row['path']).parents
                                    if p == directory or directory in p.parents)
    observed = set()
    for path in [directory, *directory.rglob('*')]:
        info = path.lstat()
        if info.st_uid != os.getuid():
            raise ValueError('Runtime owner mismatch')
        if stat.S_ISDIR(info.st_mode):
            if path not in expected_directories:
                raise ValueError('Unexpected runtime directory')
            if stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError('Private runtime directory mode mismatch')
        elif stat.S_ISREG(info.st_mode):
            if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                raise ValueError('Private runtime file mode or links mismatch')
            observed.add(str(path.relative_to(directory)))
        else:
            raise ValueError('Nonregular runtime entry refused')
    if observed != {r['path'] for r in rows} | {'manifest.json'}:
        raise ValueError('Unexpected runtime files')
    return manifest


def stage(source, candidate, destination):
    files = payload(source, candidate)
    rows = records(files)
    identity = fingerprint(rows)
    destination = Path(destination).absolute()
    for component in [*reversed(destination.parents), destination]:
        if component.is_symlink():
            raise ValueError('Symlink destination refused')
    parent = destination / RUNTIME
    for component in (destination / '.delivery', parent):
        if component.is_symlink():
            raise ValueError('Symlink destination refused')
        component.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(component.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    final = parent / identity
    if final.exists():
        return verify(final, files)
    pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=parent))
    for name, data in files.items():
        path = pending / name
        for component in reversed(path.parent.parents):
            if component == pending or pending in component.parents:
                component.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(component.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    manifest = {'version': VERSION, 'fingerprint': identity, 'files': rows,
                'cutover': False, 'state_root_unchanged': '/offmenu/data/.offmenu-platform',
                'reader_access_qualified': False}
    fd = os.open(pending / 'manifest.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    for directory in sorted([pending, *(p for p in pending.rglob('*') if p.is_dir())],
                            key=lambda p: len(p.parts), reverse=True):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    # Trusted owner is the sole staging writer. Never merge into an existing tree.
    if final.exists():
        raise ValueError('Concurrent staging requires reconciliation')
    os.rename(pending, final)
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return verify(final, files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    make = sub.add_parser('stage')
    for name in ('source', 'candidate', 'destination'):
        make.add_argument('--' + name, required=True)
    check = sub.add_parser('verify'); check.add_argument('directory')
    check.add_argument('--candidate', required=True)
    args = parser.parse_args()
    if args.action == 'stage':
        result = stage(args.source, args.candidate, args.destination)
    else:
        expected = json.loads(regular(Path(args.candidate) / 'repository-standard.json'))['runtime_hold_paths']
        result = verify(args.directory, [*expected, RUNNER, POLICY])
    # No opaque metadata contents or source bodies are emitted.
    print(json.dumps({'fingerprint': result['fingerprint'], 'file_count': len(result['files']),
                      'verified': True, 'cutover': False, 'reader_access_qualified': False}))


if __name__ == '__main__':
    main()
