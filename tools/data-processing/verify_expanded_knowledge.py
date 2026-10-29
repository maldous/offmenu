#!/usr/bin/env python3
"""Verify documentary knowledge custody offline; never execute historical commands."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-other-lane', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    directory = root / 'docs/consolidation/2026-10-18/knowledge'
    manifest = json.loads((directory / 'document-hashes.json').read_text())
    artifacts = manifest['documents']
    other = manifest['otherLaneDocuments']
    errors = []
    def require(ok, reason):
        if not ok:
            errors.append(reason)
    def blob(raw):
        return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(len(artifacts) == 256, 'Selected document count changed')
    require(len(other) == 10, 'Other-lane document count changed')
    integrated = {x['gitBlob']: x for x in artifacts}
    require(len(integrated) == 256, 'Duplicate selected blob')
    allowed = {x['path'] for x in artifacts}
    require(len(allowed) == 256, 'Duplicate selected path')
    selected = artifacts + (other if args.check_other_lane else [])
    for entry in selected:
        target = entry['path']
        relative = Path(target)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe path')
        if relative.is_absolute() or '..' in relative.parts:
            continue
        path = root / relative
        require(path.is_file() and not path.is_symlink(), 'Missing or symlink: ' + target)
        if not path.is_file() or path.is_symlink():
            continue
        raw = path.read_bytes()
        require(blob(raw) == entry['gitBlob'], 'Blob changed: ' + target)
        require(len(raw) == entry['bytes'], 'Length changed: ' + target)
        if entry in artifacts:
            require(path.suffix in ('.md', '.json'), 'Executable document path: ' + target)
            require(bool(re.fullmatch(r'[0-9a-f]{40}', entry['sourceCommit'])), 'Invalid source commit')
            original = Path(entry['sourcePath'])
            require(not original.is_absolute() and '..' not in original.parts, 'Unsafe original path')
    actual = {p.relative_to(root).as_posix() for p in (directory / 'sources').iterdir() if p.is_file()}
    require(actual == allowed, 'Missing or unexpected source documents')
    mapping = json.loads((directory / 'requirements-map.json').read_text())['requirements']
    require(len(mapping) == 52, 'Requirement-ID navigation count changed')
    for entries in mapping.values():
        for entry in entries:
            require(entry['sourceBlob'] in integrated, 'Unresolved requirement document')
            require(entry['integrationPath'] in allowed, 'Unresolved requirement path')
    for name in ('README.md', 'CATALOGUE.md'):
        text = (directory / name).read_text()
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if not target.startswith(('http:', 'https:', '#')):
                require((directory / target).is_file(), 'Broken guide link: ' + target)
    print(json.dumps({'status': 'fail' if errors else 'pass-repository-scope-only', 'externalDispositionInventory': 'unavailable; Foo custody unverified',
                      'selectedDocumentsChecked': len(artifacts),
                      'integratedDocuments': len(integrated), 'requirementIds': len(mapping),
                      'otherLaneChecked': args.check_other_lane, 'errors': errors}, indent=2))
    return bool(errors)

if __name__ == '__main__':
    raise SystemExit(main())
