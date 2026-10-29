"""Explicit local metadata audit only; no network or production stage switch."""
import argparse
from .bindings import audit_metadata, write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-root', required=True)
    parser.add_argument('--as-of', required=True, help='UTC ISO timestamp, explicit for deterministic replay')
    parser.add_argument('--output', required=True, help='New metadata report or exact existing replay')
    args = parser.parse_args()
    report = audit_metadata(args.metadata_root, as_of=args.as_of)
    print(write_report(report, args.output))


if __name__ == '__main__':
    main()
