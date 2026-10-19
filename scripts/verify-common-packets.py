#!/usr/bin/env python3
"""Schema-validate every packet of a common-data release directory.

Recovered from /tmp/verify_common_packets.py (2026-10-19) into a durable location.

Usage: python3 scripts/verify-common-packets.py <release-directory>
Dependencies: jsonschema-rs (`pip install -e '.[test]'`), offline.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

import jsonschema_rs

p = argparse.ArgumentParser()
p.add_argument('directory', type=Path)
a = p.parse_args()
root = a.directory
m = json.loads((root / 'manifest.json').read_text())
schema_path = root / 'schema.json'
if not schema_path.exists():
    schema_path = Path(__file__).resolve().parents[1] / 'corpus/common-data.schema.json'
schema = json.loads(schema_path.read_text())
v = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
counts = collections.Counter()
sources = collections.Counter()
packet_files = 0
for meta in m['files']:
    f = root / meta['key']
    b = f.read_bytes()
    if len(b) != meta['bytes'] or hashlib.sha256(b).hexdigest() != meta['sha256']:
        raise ValueError('file hash/length mismatch: ' + meta['key'])
    if not meta['key'].endswith('.jsonl.gz'):
        continue
    packet_files += 1
    seen_file = 0
    with gzip.open(f, 'rt', encoding='utf8') as inp:
        for line in inp:
            if not line.strip():
                continue
            packet = json.loads(line)
            v.validate(packet)
            seen_file += 1
            counts['packets'] += 1
            for k in ('resources', 'assertions', 'relations', 'translations'):
                counts[k] += len(packet[k])
            if len(packet['citations']) != 1:
                raise ValueError('expected one citation per source packet ' + meta['key'])
            c = packet['citations'][0]
            sources[c['sourceId']] += 1
            if c['scope']['visibility'] != 'public':
                raise ValueError('non-public packet scope')
    if seen_file != meta['packets']:
        raise ValueError(f'packet count mismatch in {meta["key"]}: {seen_file}!={meta["packets"]}')
expected = m.get('counts', {})
for k, vv in expected.items():
    if counts[k] != vv:
        raise ValueError(f'{k} count mismatch: observed {counts[k]} expected {vv}')
expected_sources = m.get('observedSourceRecords', m.get('sourceRecordCounts', {}))
if expected_sources and dict(sources) != expected_sources:
    raise ValueError(f'source count mismatch: {dict(sources)} != {expected_sources}')
print(json.dumps({'status': 'all-output-packets-schema-validated', 'directory': str(root), 'packets': counts['packets'], 'resources': counts['resources'], 'assertions': counts['assertions'], 'relations': counts['relations'], 'translations': counts['translations'], 'packetsFiles': packet_files, 'sourceRecords': dict(sources)}, ensure_ascii=False))
