#!/usr/bin/env python3
"""Write deterministic .gz companions for the sanitized coverage-register artifacts.

Recovered from /tmp/gzip_coverage_artifacts.py (2026-10-19) into a durable location.
Compression is fixed (level 9, no embedded name, no mtime) so the same input always
yields the same bytes, and the gzip OS byte is set to 3 (Unix) so the output is
byte-identical to the .gz companions already published on the integration branch.
The compressed set is what gets published to stay inside the existing publisher
size budget; each .gz decompresses byte-for-byte to its uncompressed artifact.

Usage: python3 scripts/gzip-coverage-artifacts.py [register-directory]
"""
import gzip
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'docs/coverage-register/2026-10-19'
for p in sorted(root.iterdir()):
    if p.is_file() and not p.name.endswith('.gz'):
        out = p.with_name(p.name + '.gz')
        with p.open('rb') as source, out.open('wb') as target:
            with gzip.GzipFile(filename='', mode='wb', compresslevel=9, fileobj=target, mtime=0) as stream:
                while chunk := source.read(1024 * 1024):
                    stream.write(chunk)
        with out.open('r+b') as handle:
            handle.seek(9)
            handle.write(b'\x03')
        print(out.name, out.stat().st_size)
