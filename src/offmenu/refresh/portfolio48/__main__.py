"""Explicit offline receipt binding CLI. No raw-data or online execution mode."""
import argparse
import os
from pathlib import Path
import stat
import sys

from ..core import RefreshError, canonical, safe_path, strict_json, timestamp
from . import MAX_METADATA, assess_portfolio, candidate_bytes, replay


def _read_cli_input(path, limit):
    """Bounded regular-file ingress, without blocking open or path reopening."""
    path = safe_path(path)
    if not all(hasattr(os, name) for name in ('O_NONBLOCK', 'O_NOFOLLOW')):
        raise ValueError('regular-descriptor-ingress-unavailable')
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    descriptor = os.open(path, flags | getattr(os, 'O_CLOEXEC', 0))
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
            raise ValueError('cli-input-type-or-byte-limit')
        # closefd=False leaves exactly one descriptor owner in this finally.
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('cli-input-byte-limit')
        return raw
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-map', type=Path,
                        help='Explicit logical receipt filename -> JSON path; no defaults')
    parser.add_argument('--now', required=True, help='Explicit UTC diagnostic clock')
    parser.add_argument('--candidate-output', type=Path,
                        help='Exclusive metadata JSONL output; never source data or admission')
    parser.add_argument('--previous-candidate', type=Path)
    args = parser.parse_args(argv)
    try:
        paths = {}
        if args.metadata_map:
            path = safe_path(args.metadata_map)
            raw = _read_cli_input(path, 65536)
            paths = strict_json(raw)
            if not isinstance(paths, dict) or any(not isinstance(v, str) for v in paths.values()):
                raise ValueError('metadata-map-invalid')
            paths = {k: path.parent / v for k, v in paths.items()}
        report = assess_portfolio(paths, now=timestamp(args.now))
        previous = None
        if args.previous_candidate:
            previous = _read_cli_input(args.previous_candidate, 16 * MAX_METADATA)
        report['replay'] = replay(report, previous)
        if args.candidate_output:
            output = safe_path(args.candidate_output)
            if output in {safe_path(v) for v in paths.values()}:
                raise ValueError('output-input-overlap')
            with output.open('xb') as stream:
                stream.write(candidate_bytes(report))
        sys.stdout.buffer.write(canonical(report))
        return 0 if all(s['status'] == 'valid' for s in report['sources']) else 2
    except (OSError, ValueError, TypeError, RefreshError):
        sys.stdout.buffer.write(canonical({'status': 'failed',
            'diagnostics': ['portfolio48-command-input-invalid'],
            'sourceBodyAdmission': False, 'countryComplete': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
