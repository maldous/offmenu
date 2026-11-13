#!/usr/bin/env python3
"""Discover tracked architecture and enforce the versioned repository contract."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def tracked(root):
    return [p for p in git(root, 'ls-files', '-z').split('\0') if p]


def valid_name(path, naming=None):
    naming = naming or {}
    name = Path(path).name
    if name in set(naming.get('conventional_names', ['README.md', 'MANIFEST.in', 'LICENSE', 'NOTICE.md', 'SKILL.md', 'PROVENANCE.md'])):
        return True
    if name.endswith('.py'):
        return bool(re.fullmatch(naming.get('python_pattern', r'(?:[a-z][a-z0-9_]*|__init__|__main__)\.py'), name))
    return bool(re.fullmatch(naming.get('other_pattern', r'[a-z0-9_.-]+'), name))


def discover(root):
    paths = tracked(root)
    roots = {}
    for path in paths:
        key = path.split('/')[0]
        roots[key] = roots.get(key, 0) + 1
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
    return {'revision': git(root, 'rev-parse', 'HEAD'),
            'branch': git(root, 'branch', '--show-current'),
            'tracked_files': len(paths), 'roots': dict(sorted(roots.items())),
            'untracked_count': len([p for p in untracked if p]),
            'manifests': {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                          for p in ('pyproject.toml', 'package.json', 'repository-standard.json')
                          if (root / p).is_file()}}


def check(root):
    policy = json.loads((root / 'repository-standard.json').read_text())
    paths = tracked(root)
    # Include new source intended for integration; runtime/ignored data stays out.
    paths += [p for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
              if p and p not in set(policy.get('runtime_hold_paths', []))]
    errors = []
    legacy = set(policy['legacy_paths'])
    for path in sorted(set(paths)):
        if not (root / path).exists():  # pending tracked rename
            continue
        top = path.split('/')[0]
        if top not in policy['roots']:
            errors.append({'path': path, 'rule': 'unclassified-root'})
        if path not in legacy and not valid_name(path, policy.get('naming')):
            errors.append({'path': path, 'rule': 'filename'})
        if path.startswith(('tests-web/', 'tests-edge/', 'tests-compat/')):
            errors.append({'path': path, 'rule': 'retired-test-root'})
    return {'standard_version': policy['version'], 'status': 'passed' if not errors else 'failed',
            'checked_paths': len(set(paths)), 'legacy_exceptions': len(legacy), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--discover', action='store_true',
                        help='report tracked architecture and manifest hashes')
    args = parser.parse_args()
    report = discover(args.root) if args.discover else check(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if args.discover or report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
