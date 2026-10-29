"""Deterministic, offline receipt binding CLI. No source-processing command."""
import argparse
import re
from offmenu.refresh.core import canonical, strict_json, safe_path
from .binding import bindings, read_retained_metadata, read_metadata_json, run_portfolio


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC observation time')
    parser.add_argument('--previous', help='Previous metadata plan; no validation is skipped')
    parser.add_argument('--output', help='New output file; never overwrites an existing result')
    args = parser.parse_args(argv)
    try:
        keys = {}
        if args.previous:
            prior = strict_json(read_metadata_json(args.previous))
            if (not isinstance(prior, dict) or prior.get('schemaVersion') != 'offmenu-portfolio39-plan/1'
                    or prior.get('scope') != 'receipt-metadata-only'
                    or not isinstance(prior.get('bindings'), list) or len(prior['bindings']) > 32):
                raise ValueError()
            for row in prior['bindings']:
                source, key = row['sourceId'], row.get('buildKey')
                if (not isinstance(source, str) or source in keys
                        or (key is not None and not re.fullmatch('[0-9a-f]{64}', key))):
                    raise ValueError()
                keys[source] = key
        report = run_portfolio(bindings(), read_retained_metadata, now=args.now, previous=keys)
        raw = canonical(report)
        if args.output:
            with safe_path(args.output).open('xb') as stream:
                stream.write(raw)
        else:
            print(raw.decode(), end='')
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print(canonical({'status': 'failed', 'code': 'binding-cli-input-invalid',
                         'networkRequests': 0, 'datasetAccepted': False}).decode(), end='')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
