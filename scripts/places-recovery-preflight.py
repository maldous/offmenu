#!/usr/bin/env python3
"""Read-only inventory and explicit incremental peak-storage gate; never runs alignment."""
import argparse
import json
import math
import shutil
from pathlib import Path
from places_checkpoint import digest


def storage_preflight(available, output, checkpoint, scratch, reserve):
    values = [available, output, checkpoint, scratch, reserve]
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in values):
        raise ValueError('byte budgets must be nonnegative integers')
    if any(v <= 0 for v in [output, checkpoint, scratch, reserve]):
        raise ValueError('explicit positive output/checkpoint/scratch/reserve budgets required')
    peak = output + checkpoint + scratch + reserve
    return {'availableBytes': available, 'additionalOutputBytes': output,
            'checkpointBytes': checkpoint, 'scratchBytes': scratch, 'reserveBytes': reserve,
            'requiredBytes': peak, 'headroomBytes': available - peak,
            'capacityPass': available >= peak, 'executionAuthorized': False,
            'rule': 'Incremental peak includes retained originals, no reclaim or hardlink discount; allocation/recovery/qualification approval remains required.'}


def inventory(root, historical_count, hash_limit=14):
    if historical_count < 0 or not 0 <= hash_limit <= 32 or not root.is_dir():
        raise ValueError('existing root, nonnegative historical count and bounded hash limit required')
    paths = sorted((root / 'packets').glob('*.jsonl.gz'))
    listing = [{'key': str(p.relative_to(root)), 'bytes': p.stat().st_size} for p in paths]
    import hashlib
    return {'root': str(root.resolve()), 'historicalCount': historical_count, 'currentCount': len(paths),
            'countDifference': len(paths) - historical_count,
            'listingSha256': hashlib.sha256(json.dumps(listing, sort_keys=True).encode()).hexdigest(),
            'retainedBytes': sum(r['bytes'] for r in listing),
            'manifestExists': (root / 'manifest.json').exists(),
            'checkpointExists': (root / 'checkpoint.json').exists(),
            'boundedTailReceipts': [{'key': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in paths[-hash_limit:]] if hash_limit else [],
            'classification': 'Count-only historical evidence cannot identify which files were added; tail receipts are candidates, not proven additions. No source comparison/adoption performed.'}


def gib_bytes(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('budget must be finite and positive')
    return math.ceil(number * 1024 ** 3)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--legacy-partial', type=Path, required=True)
    p.add_argument('--historical-count', type=int, required=True)
    p.add_argument('--output-gib', type=gib_bytes, required=True)
    p.add_argument('--checkpoint-gib', type=gib_bytes, required=True)
    p.add_argument('--scratch-gib', type=gib_bytes, required=True)
    p.add_argument('--reserve-gib', type=gib_bytes, required=True)
    a = p.parse_args()
    result = {'inventory': inventory(a.legacy_partial, a.historical_count),
              'storage': storage_preflight(shutil.disk_usage(a.data_root).free, a.output_gib, a.checkpoint_gib, a.scratch_gib, a.reserve_gib)}
    print(json.dumps(result, indent=2))
    return 0 if result['storage']['capacityPass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
