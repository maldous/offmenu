"""Bounded metadata-only worker, using the existing offline audit guard."""
import argparse
from pathlib import Path
import resource
import sys

# -I removes cwd: import only the exact source package containing this worker.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from offmenu.refresh.runner import deny_network
from offmenu.refresh.core import canonical, RefreshError


def main():
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024**2, 2 * 1024**2))
    sys.addaudithook(deny_network)
    from offmenu.portfolio60.bindings import assess, publish_metadata
    from offmenu.portfolio60.catalog import SOURCES
    from offmenu.portfolio60.fixtures import authored
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output-root')
    parser.add_argument('--fixture', choices=('valid', 'missing', 'held', 'malformed', 'stale-input'))
    args = parser.parse_args()
    try:
        if args.fixture:
            spec, loader = authored(args.fixture)
            result = assess((spec,), as_of=args.as_of, loader=loader)
        else:
            result = assess(SOURCES, as_of=args.as_of)
        if args.output_root:
            result['publication'] = publish_metadata(result, args.output_root)
        sys.stdout.buffer.write(canonical(result))
    except (RefreshError, ValueError, OSError):
        sys.stdout.buffer.write(canonical({'status': 'failed', 'code': 'metadata-worker-failed',
                                          'networkRequests': 0, 'sourcePayloadReads': 0}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
