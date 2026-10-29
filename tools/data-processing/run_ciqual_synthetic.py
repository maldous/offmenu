#!/usr/bin/env python3
"""Build only the checked-in, independently reviewed CIQUAL synthetic fixture.

No arbitrary source input, acquisition, historical scope, shared runner,
curation, acceptance, or publication is exposed by this repository entry point.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
from offmenu_ciqual import adapter

LOCK_PATH = ROOT / 'tests/fixtures/ciqual.lock.json'
INPUT_PATH = ROOT / 'tests/fixtures/ciqual'
LOCK_PIN = {'bytes': 1278, 'sha256': 'eed889c5ee6d4683cdfc3d410c497dcbc794712a42befa8217f46bdf502b7b19'}


def run(output, *, repin_synthetic_runtime=False):
    lock = adapter.strict_json(adapter.read_bytes(LOCK_PATH, 65536, LOCK_PIN))
    # This opt-in changes only the runtime identity. All three input pins and
    # all four implementation/contract pins remain fixed and are verified.
    changed_runtime = lock['runtime'] != adapter.runtime()
    if repin_synthetic_runtime:
        lock['runtime'] = adapter.runtime()
    result = adapter.build(INPUT_PATH, lock, output)
    return {'status': result['status'], 'buildKey': result['buildKey'],
            'inputBundleSha256': result['inputBundleSha256'],
            'normalized': result['counts']['normalized'], 'accepted': result['counts']['accepted'],
            'acceptance': result['acceptance'], 'syntheticOnly': True,
            'runtimeRepinned': repin_synthetic_runtime and changed_runtime}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repin-synthetic-runtime', action='store_true',
                        help='Explicitly bind the same pinned synthetic fixture/code to this runtime; the build key may change.')
    args = parser.parse_args(argv)
    try:
        result = run(args.output, repin_synthetic_runtime=args.repin_synthetic_runtime)
    except adapter.DataError as error:
        print(json.dumps({'status': 'held', 'code': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
