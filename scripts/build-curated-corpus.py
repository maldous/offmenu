#!/usr/bin/env python3
"""Manually compile OffMenu public records into its own indexed serving format.

SQLite is a LOCAL build index, never the production/user database. The output
contains immutable gzip partitions, numeric posting lists and source manifests.
Netlify serves this curated result; it does not acquire or normalize upstreams.
"""
import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import unicodedata
import importlib.util
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = 1000
SHARD_LENGTH = 3
_spec = importlib.util.spec_from_file_location('curation', ROOT / 'corpus/curation.py')
curation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(curation)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def words(value):
    result = set(re.findall(r'[^\W_]+', normalized(value), re.UNICODE))
    for word in list(result):
        if re.search(r'[\u3040-\u30ff\u3400-\u9fff]', word):
            result.update(word[i:i + 2] for i in range(len(word) - 1))
    return sorted(result)


def shard(value):
    return hashlib.sha256(value.encode()).hexdigest()[:SHARD_LENGTH]


class Partitions:
    def __init__(self, root):
        self.root = root
        self.writers = {}

    def write(self, path, row):
        if path not in self.writers:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            self.writers[path] = gzip.open(target, 'wt', encoding='utf-8', compresslevel=1)
        self.writers[path].write(compact(row) + '\n')

    def close(self):
        for writer in self.writers.values():
            writer.close()
        self.writers.clear()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def compile_release(directories, output, version, policy_path):
    if output.exists():
        raise ValueError('Immutable release output exists; choose a new directory')
    policy = json.loads(policy_path.read_text())
    output.mkdir(parents=True)
    blobs = output / 'blobs'
    blobs.mkdir()
    db = sqlite3.connect(output / 'local-index.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE entries(id INTEGER PRIMARY KEY,source TEXT NOT NULL,bundle_key TEXT NOT NULL,shard TEXT NOT NULL,kinds TEXT NOT NULL,countries TEXT NOT NULL,search_name TEXT NOT NULL,UNIQUE(source,bundle_key))')
    db.execute('CREATE TABLE tokens(term TEXT NOT NULL,entry INTEGER NOT NULL)')
    db.execute('CREATE TABLE barcodes(code TEXT NOT NULL,entry INTEGER NOT NULL)')
    manifest = {'format': 'offmenu-curated/1', 'releaseId': version,
                'engineVersion': 'offmenu-local-engine/1', 'curationPolicy': policy,
                'entryPageSize': PAGE, 'shardLength': SHARD_LENGTH, 'sources': {},
                'status': 'building', 'privateProviderData': False, 'acquisitionAtRuntime': False}
    next_id = 0
    for directory in directories:
        upstream = json.loads((directory / 'manifest.json').read_text())
        source = upstream['sourceId']
        if source in manifest['sources']:
            raise ValueError('Exactly one version per source in a curated release')
        if source not in policy['publicSources'] or upstream['status'] != 'normalized':
            raise ValueError('Source not admitted and reconciled: ' + source)
        inputs = [directory / p['key'] for p in upstream.get('partitions', [])] or [directory / 'normalized.jsonl.gz']
        expected = upstream.get('normalizedRows', upstream.get('counts', {}).get('records'))
        record_shard_length = 1 if expected <= 5000 else 2 if expected <= 100000 else SHARD_LENGTH
        count, curated_count, start, bundles = 0, 0, next_id, 0
        withheld_reasons = defaultdict(int)
        records = Partitions(blobs)
        entry_batch, token_batch, barcode_batch = [], [], []
        def flush():
            db.executemany('INSERT INTO entries VALUES(?,?,?,?,?,?,?)', entry_batch)
            db.executemany('INSERT INTO tokens VALUES(?,?)', token_batch)
            db.executemany('INSERT INTO barcodes VALUES(?,?)', barcode_batch)
            db.commit()
            entry_batch.clear()
            token_batch.clear()
            barcode_batch.clear()
        for path in inputs:
            with gzip.open(path, 'rt', encoding='utf-8') as lines:
                for line in lines:
                    rows = json.loads(line)
                    if not rows:
                        raise ValueError('Empty record bundle')
                    for original in rows:
                        p = original.get('provenance', {})
                        if p.get('visibility') != 'public' or p.get('sourceId') != source or original.get('kind') in policy['privateKinds']:
                            raise ValueError('Private/mismatched input cannot be promoted through curation')
                    count += len(rows)
                    rows, withheld = curation.curate(rows, policy['version'])
                    for decision in withheld:
                        withheld_reasons[decision['reason']] += 1
                    if not rows:
                        continue
                    curated_count += len(rows)
                    key = rows[0]['id']
                    names, codes, countries, kinds = set(), set(), set(), set()
                    for row in rows:
                        p, data = row.get('provenance', {}), row['data']
                        if p.get('visibility') != 'public' or p.get('sourceId') != source or row['kind'] in policy['privateKinds']:
                            raise ValueError('Private/mismatched record cannot enter the public corpus')
                        if not p.get('license') or not p.get('attribution') or row['schemaVersion'] != '1.0':
                            raise ValueError('Missing schema or source rights')
                        if p.get('status') in ('withdrawn', 'quarantined'):
                            raise ValueError('Unavailable source record')
                        row['curation'] = {**row['curation'], 'policyVersion': policy['version'],
                                           'humanReviewed': False, 'automaticDietQualification': False}
                        if row['kind'] == 'recipe':
                            data['automaticPlanningEligible'] = False
                        name = data.get('name') or data.get('foodName') or data.get('title') or key
                        names.add(name)
                        names.update(str(v) for v in data.get('names', {}).values() if v)
                        for ident in data.get('identifiers', []):
                            if ident.get('system') == 'barcode':
                                codes.add(str(ident['value']))
                        countries.update(row.get('countries', []))
                        kinds.add(row['kind'])
                    record_shard = hashlib.sha256(key.encode()).hexdigest()[:record_shard_length]
                    records.write(f'records/{source}/{record_shard}.jsonl.gz', [key, rows])
                    search = normalized(' '.join(sorted(names)))
                    entry_batch.append((next_id, source, key, record_shard, compact(sorted(kinds)), compact(sorted(countries)), search))
                    token_batch.extend((word, next_id) for word in words(search))
                    barcode_batch.extend((code, next_id) for code in codes)
                    next_id += 1
                    bundles += 1
                    if bundles % 2000 == 0:
                        flush()
                    if bundles % 100000 == 0:
                        print(compact({'source': source, 'bundles': bundles, 'records': count}), flush=True)
        flush()
        records.close()
        if count != expected:
            raise ValueError('Full source reconciliation failed: ' + source)
        for notice in upstream.get('licenseDocuments', []):
            name = notice['key']
            if not re.fullmatch(r'[-A-Za-z0-9.]+\.txt', name):
                raise ValueError('Unsupported licence document name')
            original = directory / 'licenses' / name
            if digest(original) != notice['sha256'] or original.stat().st_size > 256 * 1024:
                raise ValueError('Licence document checksum/size mismatch')
            key = 'notices/' + source + '/' + str(upstream['releaseId']) + '/' + name
            destination = blobs / key
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(original.read_bytes())
            manifest.setdefault('notices', []).append({'sourceId': source, 'key': key, 'bytes': destination.stat().st_size, 'sha256': digest(destination), 'sourceUrl': notice['sourceUrl']})
        manifest['sources'][source] = {'sourceId': source, 'releaseId': upstream.get('releaseId', directory.name),
            'records': curated_count, 'normalizedLocalRecords': count, 'withheldRecords': count - curated_count,
            'withheldReasons': dict(withheld_reasons), 'bundles': bundles, 'recordShardLength': record_shard_length, 'entryRange': [start, next_id],
            'scope': upstream['scope'], 'license': upstream['license'], 'attribution': upstream.get('attribution', source),
            'archiveSha256': upstream['archiveSha256'], 'rawSourcePayloadPublished': False,
            'rights': 'Original source licence/attribution retained; no private provider results',
            'independentlyAccepted': False}
    print('Exporting entry pages and sorted posting lists', flush=True)
    db.execute('CREATE INDEX tokens_sorted ON tokens(term,entry)')
    db.execute('CREATE INDEX barcodes_sorted ON barcodes(code,entry)')
    db.commit()
    pages, page = 0, []
    for row in db.execute('SELECT * FROM entries ORDER BY id'):
        ident, source, key, bin_key, kinds, countries, name = row
        page.append({'id': ident, 'source': source, 'key': key, 'shard': bin_key,
                     'kinds': json.loads(kinds), 'countries': json.loads(countries), 'name': name})
        if len(page) == PAGE:
            with gzip.open(blobs / f'entries-{pages}.json.gz', 'wt', encoding='utf-8') as f:
                f.write(compact(page))
            pages += 1
            page = []
    if page:
        with gzip.open(blobs / f'entries-{pages}.json.gz', 'wt', encoding='utf-8') as f:
            f.write(compact(page))
        pages += 1
    source_ranges = [(s, v['entryRange']) for s, v in manifest['sources'].items()]
    for table, column, namespace in [('tokens', 'term', 'terms'), ('barcodes', 'code', 'barcodes')]:
        partitions = Partitions(blobs)
        previous, ids = None, defaultdict(list)
        def emit():
            if previous is not None:
                partitions.write(f'{namespace}/{shard(previous)}.jsonl.gz', [previous, dict(ids)])
        for token, ident in db.execute(f'SELECT {column},entry FROM {table} ORDER BY {column},entry'):
            if token != previous:
                emit()
                previous, ids = token, defaultdict(list)
            source = next(s for s, (low, high) in source_ranges if low <= ident < high)
            if not ids[source] or ids[source][-1] != ident:
                ids[source].append(ident)
        emit()
        partitions.close()
    manifest['entries'] = next_id
    manifest['records'] = sum(s['records'] for s in manifest['sources'].values())
    manifest['entryPages'] = pages
    manifest['files'] = []
    for path in sorted(blobs.rglob('*.gz')):
        manifest['files'].append({'key': str(path.relative_to(blobs)), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    # Manifest is last. Incomplete outputs have no accepted serving manifest.
    manifest['status'] = 'curated-release-ready'
    manifest['completedAt'] = datetime.now(timezone.utc).isoformat()
    body = compact(manifest)
    manifest['manifestSha256'] = hashlib.sha256(body.encode()).hexdigest()
    (blobs / 'manifest.json').write_text(compact(manifest) + '\n')
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    db.close()
    print(compact({'status': manifest['status'], 'records': manifest['records'], 'files': len(manifest['files'])}), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--policy', type=Path, default=ROOT / 'corpus/policy.json')
    args = parser.parse_args()
    compile_release(args.release_dir, args.output, args.version, args.policy)
