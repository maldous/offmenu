#!/usr/bin/env python3
"""Validate only the Open Prices slice of the bulk food common-data release.

Recovered from /tmp/verify_bulk_prices_slice.py (2026-10-19) into a durable location.
The packet stream is source-ordered (off, usda-files, prices), so the prices slice
is read by ordinal without decompressing unrelated packets' identities twice.

Dependencies: jsonschema-rs (`pip install -e '.[test]'`), offline.
Data root comes from OFFMENU_DATA_ROOT (default ~/src/offmenu-data).
"""
import gzip
import hashlib
import json
import os
from pathlib import Path

import jsonschema_rs

root = Path(os.environ.get('OFFMENU_DATA_ROOT', Path.home() / 'src' / 'offmenu-data')) / 'common-bulk-food-20261014'
m = json.loads((root / 'manifest.json').read_text())
schema = json.loads((root / 'schema.json').read_text())
v = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
source = 'prices'
start = m['observedSourceRecords']['off'] + m['observedSourceRecords']['usda-files']
expected = m['observedSourceRecords']['prices']
seen = 0
ids = {k: set() for k in ('resources', 'assertions', 'relations', 'citations')}
counts = {k: 0 for k in ('resources', 'assertions', 'relations', 'translations')}
first = start // 1000
last = (start + expected - 1) // 1000
for i in range(first, last + 1):
    key = f'packets/part-{i:05d}.jsonl.gz'
    meta = next(x for x in m['files'] if x['key'] == key)
    b = (root / key).read_bytes()
    if len(b) != meta['bytes'] or hashlib.sha256(b).hexdigest() != meta['sha256']:
        raise ValueError('digest mismatch ' + key)
    with gzip.open(root / key, 'rt') as f:
        for line in f:
            packet = json.loads(line)
            if seen < start % 1000 and i == first:
                seen += 1
                continue
            v.validate(packet)
            c = packet['citations'][0]
            if c['sourceId'] != source:
                raise ValueError('source sequence mismatch ' + str(c['sourceId']))
            seen += 1
            for k in ('resources', 'assertions', 'relations', 'translations'):
                counts[k] += len(packet[k])
            for k in ('resources', 'assertions', 'relations'):
                for o in packet[k]:
                    if o['id'] in ids[k]:
                        raise ValueError('duplicate ' + k)
                    ids[k].add(o['id'])
            for c in packet['citations']:
                if c['id'] in ids['citations']:
                    raise ValueError('duplicate citation')
                ids['citations'].add(c['id'])
print(json.dumps({'status': 'schema-validation-passed', 'source': source, 'sourceRecordsValidated': expected, 'startPacketOrdinal': start, 'counts': counts, 'identities': {k: len(v) for k, v in ids.items()}, 'partitionFilesRead': last - first + 1}))
