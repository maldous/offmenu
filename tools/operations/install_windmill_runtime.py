#!/usr/bin/env python3
"""Install only four selected runtime dependencies with explicit reader ACLs.

Invocation requires action-time authorization for the concrete new runtime and
UID985 read/traverse grant. Never changes existing .delivery or launcher access.
No service/caller changes, source cleanup, jobs, mounts, or credential operations.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

spec = importlib.util.spec_from_file_location('runtime_prepare', Path(__file__).with_name('prepare_windmill_runtime.py'))
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)
SELECTED = (prepare.RUNNER, prepare.POLICY, 'scripts/windmill/platform_check_capacity64.py',
            'scripts/windmill/storage/offmenu_storage.py')
LOCATION = '.offmenu-runtime'
READER_UID = 985


def plan(staged, candidate, expected_fingerprint):
    expected = json.loads(prepare.regular(Path(candidate) / 'repository-standard.json'))['runtime_hold_paths']
    manifest = prepare.verify(staged, [*expected, prepare.RUNNER, prepare.POLICY])
    if manifest['fingerprint'] != expected_fingerprint:
        raise ValueError('Selected staging fingerprint changed')
    files = {p: prepare.regular(Path(staged) / p) for p in SELECTED}
    bound = {row['path']: row for row in manifest['files']}
    for name, data in files.items():
        if len(data) != bound[name]['bytes'] or prepare.digest(data) != bound[name]['sha256']:
            raise ValueError('Selected source changed after verification')
    rows = prepare.records(files)
    return {'version': 1, 'fingerprint': prepare.fingerprint(rows), 'files': rows,
            'source_fingerprint': expected_fingerprint, 'reader_uid': READER_UID,
            'owner_uid': os.getuid(), 'state_root': '/offmenu/data/.offmenu-platform',
            'consumer_cutover': False}, files


def acl(path, directory):
    # Only newly created files/directories; caller checks that no existing target
    # is replaced. Remove inherited grants before adding the one approved reader.
    subprocess.run(['setfacl', '-b', str(path)], check=True)
    if directory:
        subprocess.run(['setfacl', '-k', str(path)], check=True)
    access = 'r-x' if directory else 'r--'
    owner = 'rwx' if directory else 'rw-'
    subprocess.run(['setfacl', '--set', f'u::{owner},u:{READER_UID}:{access},g::---,m::{access},o::---', str(path)], check=True)


def inspect_acl(path, directory):
    result = subprocess.check_output(['getfacl', '-cpn', str(path)], text=True)
    rows = {line.split('#', 1)[0].strip() for line in result.splitlines() if line.strip()}
    access = 'r-x' if directory else 'r--'
    owner = 'rwx' if directory else 'rw-'
    if rows != {f'user::{owner}', f'user:{READER_UID}:{access}', 'group::---', f'mask::{access}', 'other::---'}:
        raise ValueError('Runtime ACL differs from selected least-access contract')


def verify(directory, expected):
    directory = Path(directory).absolute()
    manifest = json.loads(prepare.regular(directory / 'installation.json'))
    if manifest != expected:
        raise ValueError('Installation identity mismatch')
    if directory.name != expected['fingerprint']:
        raise ValueError('Installation directory identity mismatch')
    allowed_files = {*SELECTED, 'installation.json'}
    allowed_dirs = {directory}
    for relative in SELECTED:
        allowed_dirs.update(p for p in (directory / relative).parents if p == directory or directory in p.parents)
    observed = set()
    for p in [directory, *directory.rglob('*')]:
        info = p.lstat()
        if info.st_mode & 0o7000:
            raise ValueError('Special installation permission bits refused')
        if info.st_uid != expected['owner_uid']:
            raise ValueError('Installation owner mismatch')
        if stat.S_ISDIR(info.st_mode):
            if p not in allowed_dirs: raise ValueError('Unexpected installation directory')
            inspect_acl(p, True)
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            observed.add(str(p.relative_to(directory))); inspect_acl(p, False)
        else:
            raise ValueError('Invalid installation entry')
    if observed != allowed_files:
        raise ValueError('Installation inventory mismatch')
    for row in expected['files']:
        data = prepare.regular(directory / row['path'])
        if len(data) != row['bytes'] or prepare.digest(data) != row['sha256']:
            raise ValueError('Installed content mismatch')
    return expected


def install(staged, candidate, destination, expected_fingerprint):
    if os.getuid() != 1000:
        raise ValueError('Run installation as the verified trusted checkout owner UID1000')
    expected, files = plan(staged, candidate, expected_fingerprint)
    destination = Path(destination).absolute()
    for p in [*reversed(destination.parents), destination]:
        if p.is_symlink(): raise ValueError('Symlink destination refused')
    if not destination.is_dir() or destination.stat().st_uid != os.getuid():
        raise ValueError('Destination ownership mismatch')
    root = destination / LOCATION
    if root.exists():
        if root.is_symlink() or root.stat().st_uid != os.getuid(): raise ValueError('Runtime root mismatch')
        inspect_acl(root, True)
    else:
        root.mkdir(mode=0o700); acl(root, True)
    final = root / expected['fingerprint']
    if final.exists(): return verify(final, expected)
    # Create-only. Any interruption leaves a partial installation that verify
    # refuses; no caller changes occur until a separate successful cutover.
    final.mkdir(mode=0o700)
    for name, data in {**files, 'installation.json': (json.dumps(expected, indent=2, sort_keys=True)+'\n').encode()}.items():
        path = final / name
        for p in reversed(path.parent.parents):
            if p == final or final in p.parents: p.mkdir(mode=0o700, exist_ok=True)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); acl(path, False); os.fsync(stream.fileno())
    for p in sorted([final, *(p for p in final.rglob('*') if p.is_dir())], key=lambda p:len(p.parts), reverse=True):
        acl(p, True)
        fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    for p in (root, destination):
        fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return verify(final, expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'install'])
    for key in ('staged', 'candidate', 'expected-fingerprint'):
        parser.add_argument('--'+key, required=True)
    parser.add_argument('--destination')
    args = parser.parse_args()
    if args.action == 'install':
        if not args.destination: parser.error('--destination required for install')
        result = install(args.staged, args.candidate, args.destination, args.expected_fingerprint)
    else:
        result, _ = plan(args.staged, args.candidate, args.expected_fingerprint)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
