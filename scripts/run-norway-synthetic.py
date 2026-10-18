#!/usr/bin/env python3
"""Build only the checked-in, independently reviewed Norway synthetic fixture.

No arbitrary input path, source acquisition, historical scope, shared runner,
curation, acceptance, or publication is exposed by this repository entry point.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from offmenu_norway import adapter

LOCK_PATH = ROOT / 'tests/fixtures/norway.lock.json'
INPUT_PATH = ROOT / 'tests/fixtures/norway'
LOCK_PIN = {'bytes': 1066, 'sha256': '0e39e65eb38e0353abbf54514c8e163a347f5945f2357420f13a233ddf1e3d28'}


def run(output, *, repin_synthetic_runtime=False):
    lock = adapter.strict_json(adapter.read_bytes(LOCK_PATH, 65536, LOCK_PIN))
    # This opt-in changes only the interpreter/zlib identity. The frozen lock,
    # four fixture hashes, and three implementation hashes stay untouched.
    changed_runtime = lock['runtime'] != adapter.runtime()
    if repin_synthetic_runtime:
        lock['runtime'] = adapter.runtime()
    result = adapter.build(lock, INPUT_PATH, output)
    return {**result, 'syntheticOnly': True,
            'runtimeRepinned': repin_synthetic_runtime and changed_runtime}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repin-synthetic-runtime', action='store_true',
                        help='Explicitly bind the same pinned synthetic fixture/code to this runtime; the build key may change.')
    args = parser.parse_args(argv)
    try:
        result = run(args.output, repin_synthetic_runtime=args.repin_synthetic_runtime)
    except adapter.AdapterError as error:
        print(json.dumps({'status': 'failed', 'code': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
