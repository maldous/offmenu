#!/usr/bin/env python3
"""Selected private witness only; no acquisition or arbitrary contract plugins.

Run only after Gateway selects the reviewed operation/evidence/capacity binding.
JSON evidence never supplies source IDs, permissions, limits or executable code.
"""
import argparse
import json
from pathlib import Path
import re
import sys

from offmenu.refresh.acceptance import Asset
from offmenu.refresh.national_tabular import valid_input_name
from offmenu.refresh.product_input_witness import witness_retained_input
from offmenu.refresh.product_witness_bindings import retained_witness_contract, retained_witness_limits


def evidence_asset(value):
    try:
        path, size, sha = value.split(':')
        size = int(size)
        if not valid_input_name(path) or not 0 < size <= 1024**2 or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError()
        return Asset(path, size, sha)
    except ValueError:
        raise argparse.ArgumentTypeError('evidence pin must be relative-path:positive-bytes:sha256') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, choices=('off','usda-files'))
    parser.add_argument('--evidence-bundle', required=True, type=Path)
    parser.add_argument('--originals-root', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    for name in ('rights','scope','clock'):
        parser.add_argument('--'+name, required=True, type=evidence_asset)
    parser.add_argument('--protected-bytes-including-floor', required=True, type=int)
    args = parser.parse_args(argv)
    contract = retained_witness_contract(args.source, args.rights, args.scope, args.clock)
    limits = retained_witness_limits(args.source,
        protected_bytes_including_floor=args.protected_bytes_including_floor)
    result = witness_retained_input(contract, args.evidence_bundle, args.destination,
        input_root=args.originals_root, limits=limits)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['eligibleCleanScopeWitness'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
