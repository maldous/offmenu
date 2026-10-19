#!/usr/bin/env python3
"""Build source-faithful Open Prices common-data packets from the retained original.

Recovered from /tmp/align_prices_common.py (2026-10-19) into a durable location.

Dependencies: jsonschema-rs (`pip install -e '.[test]'`), no network access.
Data root comes from OFFMENU_DATA_ROOT (default ~/src/offmenu-data).
Re-runnable only when the output directory does not already exist: the script
creates `common-alignment-20261019/prices` with exist_ok=False so a published
release is never silently overwritten.
"""
import collections
import gzip
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import jsonschema_rs

repo = Path(__file__).resolve().parents[1]
data_root = Path(os.environ.get('OFFMENU_DATA_ROOT', Path.home() / 'src' / 'offmenu-data'))
spec = importlib.util.spec_from_file_location('bulk_common', repo / 'scripts/align-bulk-food-common.py')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
schema = json.loads((repo / 'corpus/common-data.schema.json').read_text())
validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
src = data_root / 'prices-2026-10-12'
manifest = json.loads((src / 'manifest.json').read_text())
original = data_root / 'originals/prices-2026-10-12.jsonl.gz'
asset = json.loads((repo / 'docs/collection-selections/global-comprehensive-manifest.json').read_text())
a = next(x for x in asset['assets'] if x['assetId'] == 'file:c82823748e38c1c8ec486217')
if a['preparationContract']['permissions'] != {'copy': False, 'extract': False, 'read': True}:
    raise SystemExit('source contract does not authorize extraction')
if a['holds'] or a['sourceStageHolds'] or a['bindings'] or a['missingContractFields']:
    raise SystemExit('source asset currently held/unbound; no extraction authorized')
if not original.is_file() or original.stat().st_size != a['retainedOriginal']['bytes']:
    raise SystemExit('original custody absent or byte mismatch')
h = hashlib.sha256()
with original.open('rb') as f:
    for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
        h.update(b)
if h.hexdigest() != a['retainedOriginal']['sha256']:
    raise SystemExit('retained original digest mismatch')
# Restrict inputs to the selected root Open Prices price rows; locations and
# proofs are deliberately not emitted.
files = []
for part in manifest['partitions']:
    f = src / part['key']
    b = f.read_bytes()
    if len(b) != part['bytes'] or hashlib.sha256(b).hexdigest() != part['sha256']:
        raise ValueError('partition digest mismatch ' + part['key'])
    files.append(f)
if sum(x['records'] for x in manifest['partitions']) != manifest['counts']['records']:
    raise ValueError('partition records mismatch')
out = data_root / 'common-alignment-20261019' / 'prices'
out.mkdir(parents=True, exist_ok=False)
counts = collections.Counter(translations=0)
batch = []
parts = []
seen = collections.defaultdict(set)
source_records = 0
for f in files:
    with gzip.open(f, 'rt', encoding='utf8') as handle:
        for line in handle:
            row = json.loads(line)
            if isinstance(row, list):
                if len(row) != 1:
                    raise ValueError('unexpected bundle multiplicity in prices input')
                row = row[0]
            packet = mod.packet(row, 'prices', manifest)
            validator.validate(packet)
            for k in ('resources', 'assertions', 'relations'):
                for item in packet[k]:
                    if item['id'] in seen[k]:
                        raise ValueError('duplicate ' + k + ' ' + item['id'])
                    seen[k].add(item['id'])
            for c in packet['citations']:
                if c['id'] in seen['citations']:
                    raise ValueError('duplicate citation ' + c['id'])
                seen['citations'].add(c['id'])
            batch.append(json.dumps(packet, ensure_ascii=False, separators=(',', ':')))
            source_records += 1
            counts['packets'] += 1
            counts['resources'] += len(packet['resources'])
            counts['assertions'] += len(packet['assertions'])
            counts['relations'] += len(packet['relations'])
            if len(batch) == 1000:
                payload = gzip.compress(('\n'.join(batch) + '\n').encode(), compresslevel=1)
                key = f'packets/part-{len(parts):05d}.jsonl.gz'
                (out / key).parent.mkdir(parents=True, exist_ok=True)
                (out / key).write_bytes(payload)
                parts.append({'key': key, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'packets': len(batch)})
                batch = []
if batch:
    payload = gzip.compress(('\n'.join(batch) + '\n').encode(), compresslevel=1)
    key = f'packets/part-{len(parts):05d}.jsonl.gz'
    (out / key).parent.mkdir(parents=True, exist_ok=True)
    (out / key).write_bytes(payload)
    parts.append({'key': key, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'packets': len(batch)})
if source_records != manifest['counts']['records']:
    raise ValueError(f'count {source_records} != {manifest["counts"]["records"]}')
for name, dest in [('common-data.schema.json', 'schema.json'), ('common-data-contract.json', 'contract.json'), ('common-source-mappings.json', 'source-mappings.json')]:
    b = (repo / 'corpus' / name).read_bytes()
    (out / dest).write_bytes(b)
    parts.append({'key': dest, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
release = {
    'schemaVersion': 'offmenu-common-bulk-food/1',
    'releaseId': 'prices-common-20261019',
    'status': 'full-schema-identity-citation-public-scope-checked',
    'complete': True,
    'sources': ['prices'],
    'sourceManifest': {'path': str(src / 'manifest.json'), 'sha256': hashlib.sha256((src / 'manifest.json').read_bytes()).hexdigest()},
    'sourceAssetId': a['assetId'],
    'sourceOriginalSHA256': h.hexdigest(),
    'counts': dict(counts),
    'expectedCounts': dict(counts),
    'observedCounts': dict(counts),
    'expectedSourceRecords': {'prices': manifest['counts']['records']},
    'observedSourceRecords': {'prices': source_records},
    'inputCoverage': {'prices': {'expectedFiles': len(files), 'observedFiles': len(files), 'expectedSourceRecords': manifest['counts']['records'], 'observedSourceRecords': source_records, 'complete': True}},
    'files': parts,
    'partitionCoverage': {'complete': True, 'expectedFiles': len(parts) - 3, 'observedFiles': len(parts) - 3, 'expectedPackets': counts['packets'], 'observedPackets': counts['packets']},
    'scope': 'Open Prices historical price observations only, all source rows. Locations/proofs are not emitted; no contributor, stock, country fanout or present-day availability inference. Source-scoped identities and ODbL attribution retained.',
    'license': manifest['license'],
    'attribution': manifest['attribution'],
}
release['manifestSha256'] = hashlib.sha256(json.dumps(release, separators=(',', ':')).encode()).hexdigest()
(out / 'manifest.json').write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'output': str(out), 'sourceRecords': source_records, 'counts': dict(counts), 'partitions': len(parts) - 3, 'idCounts': {k: len(v) for k, v in seen.items()}}, ensure_ascii=False))
