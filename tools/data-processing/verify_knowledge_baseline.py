#!/usr/bin/env python3
"""Verify bounded repository knowledge; never infer external inventory custody."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    'docs/consolidation/2026-10-18/artifact-dispositions.json': (176799, '8929ad02ce5bcfa12dd312965f50b122f2506d4a10c66fe6810b6d84ac5faf5b', 'f4d7e1c48d5f4e714c3b866a24bbd2e20565bc7e'),
    'docs/consolidation/2026-10-18/discovery-baseline.json': (2665376, '52f4579847e7eec1a746988892ad7525a32835aa46161e51bc433f75f2657a74', '0ba0442c3cbc15c8de04260762cbd00765b38ec2'),
    'docs/consolidation/2026-10-18/knowledge/artifact-dispositions.json': (1232931, 'b2acf68013edb8d0165c28f154981c65b26919ebedc7cf54efbda1bbbb7875a8', '111fc5d830b565de6f2ad384c1c451ba8ebed3da'),
}
DESIGNS = {'evidence.json': '22a2188c979372801001f250ac61c67766c02046', 'recommendation.md': '761bc5dc54462edef9271a35c735308e48071e9b'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-code-tree', action='store_true', help='Request legacy full-inventory coverage; reports incomplete because bulk inventory is excluded.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    errors = []
    docs = root / 'docs/consolidation/2026-10-18'
    try:
        refs = json.loads((docs / 'bulk-artifact-references.json').read_text())['artifacts']
        paths = [e['logicalArtifact'] for e in refs]
        if len(paths) != 3 or set(paths) != set(EXPECTED):
            errors.append('Bulk reference coverage or uniqueness changed')
        for e in refs:
            path = e['logicalArtifact']
            if (e['bytes'], e['sha256'], e['gitBlob']) != EXPECTED.get(path):
                errors.append('Bulk artifact pin changed: ' + path)
            if e['custody'].get('fooRetention') != 'unverified' or e['custody'].get('fooLocator') is not None:
                errors.append('Unreviewed Foo custody promotion: ' + path)
            if (root / path).exists():
                errors.append('Excluded bulk inventory present in repository tree: ' + path)
        paused = json.loads((docs / 'paused-work.json').read_text())['artifacts']
        if len(paused) != 49:
            errors.append('Paused record count changed')
        if any(e['acceptance'] not in ('already-pinned-baseline-copy', 'unfinished-not-accepted') or e['disposition'] == 'integrated' for e in paused):
            errors.append('Paused work promoted')
        for name, expected in DESIGNS.items():
            path = root / 'docs/handover/2026-10-17/corpus-refresh-design' / name
            if not path.is_file() or path.is_symlink():
                errors.append('Missing or symlink design: ' + name)
                continue
            raw = path.read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if actual != expected:
                errors.append('Design bytes changed: ' + name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(type(exc).__name__ + ': malformed or unavailable repository evidence')
    incomplete = args.check_code_tree
    print(json.dumps({'status': 'fail' if errors else ('incomplete-requested-coverage' if incomplete else 'pass-repository-scope-only'),
                      'externalInventoryVerification': 'unavailable: bulk bodies excluded; no Foo readback',
                      'fooCustody': 'unverified', 'fullDispositionCodeTreeCheck': 'unavailable',
                      'discoveryCountrySourceCountsRevalidated': False, 'errors': errors}, indent=2))
    return 1 if errors else (2 if incomplete else 0)


if __name__ == '__main__':
    raise SystemExit(main())
