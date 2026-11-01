"""Explicit local read-only native handoff projection; no service clients."""
import argparse
import json
from pathlib import Path

from native_harness_contract import ContractError, load_release_policy
from offmenu.delivery.engine import DeliveryError
from offmenu.delivery.status import project_native_handoff


def read_bounded(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(262145)
    if len(raw) > 262144:
        raise ValueError('observation_input_too_large')
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('handoff', type=Path)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--native-receipt', type=Path)
    args = parser.parse_args(argv)
    try:
        result = project_native_handoff(
            json.loads(read_bounded(args.handoff)), load_release_policy(args.policy),
            native_receipt_bytes=(read_bounded(args.native_receipt)
                                  if args.native_receipt else None))
    except (OSError, ValueError, RecursionError, ContractError, DeliveryError):
        # Never echo input, credential-bearing paths or raw parse errors.
        parser.exit(2, 'native observation input rejected\n')
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
