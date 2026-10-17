"""Local, source-scoped ALDI/DoorDash snapshots; never a public or live feed."""
import gzip
import hashlib
import json
import math
import os
import sqlite3
from collections import Counter
from pathlib import Path

SOURCE = 'aldi-doordash-au'
LICENSE = 'Retailer/platform terms; republication rights not assessed'
SCOPE = {'visibility': 'local-restricted', 'reuseScope': LICENSE}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data_root():
    return Path(os.environ.get('OFFMENU_DATA_ROOT', Path(__file__).resolve().parents[2] / 'offmenu-data')).resolve()


def register_snapshot(directory, source=SOURCE):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest['sourceId'] != source or manifest['status'] != 'normalized-local-restricted':
        raise ValueError('Only the normalized local ALDI datasource may be registered')
    for name, meta in manifest['files'].items():
        if digest(directory / name) != meta['sha256']:
            raise ValueError('Datasource checksum mismatch: ' + name)
    pointer = data_root() / source / 'current.json'
    pointer.parent.mkdir(parents=True, exist_ok=True)
    temporary = pointer.with_suffix('.tmp')
    temporary.write_text(json.dumps({'sourceId': source, 'directory': str(directory),
                                    'manifestSha256': digest(directory / 'manifest.json'),
                                    'visibility': 'local-restricted'}, indent=2) + '\n')
    temporary.replace(pointer)
    return str(pointer)


def wrap(kind, key, data, raw, manifest, line):
    store = raw['source_store_id']
    return {
        'schemaVersion': '1.0', 'kind': kind, 'id': f'{SOURCE}:{kind}:{key}',
        'countries': ['AU'],
        'provenance': {
            'sourceId': SOURCE, 'recordId': f"{store}:{raw['source_item_id']}",
            'url': raw['source_category_urls'][0], 'license': LICENSE,
            'attribution': 'ALDI catalogue displayed by DoorDash',
            'fetchedAt': raw['last_observed_at'], 'sourceDate': None,
            'visibility': 'local-restricted', 'transform': 'offmenu-aldi-doordash/1',
            'releaseId': manifest['releaseId'],
            'rights': 'Local snapshot; no public redistribution or gold admission.',
            'sourceManifestSha256': manifest['upstreamManifestSha256'],
            'originalRecord': {'file': 'inventory.jsonl', 'line': line,
                               'sha256': manifest['upstreamInventorySha256']},
        }, 'data': data,
    }


def normalize(raw, manifest, line):
    if raw['source_store_id'] != manifest['sourceStoreId'] or raw['market'] != 'AU' or raw['currency'] != 'AUD':
        raise ValueError('Source store/market/currency mismatch')
    if not isinstance(raw['source_item_id'], str) or not raw['source_item_id'].isdigit():
        raise ValueError('Expected source item identifier, never a barcode')
    amount = raw['price_amount_aud']
    if isinstance(amount, bool) or not isinstance(amount, (float, int)) or not math.isfinite(amount) or amount < 0:
        raise ValueError('Invalid source price')
    key = f"{raw['source_store_id']}:{raw['source_item_id']}"
    product_id = f'{SOURCE}:product:{key}'
    retailer_id = f"{SOURCE}:retailer:{raw['source_store_id']}"
    identifiers = [{'system': 'DoorDash-store-item', 'value': key}]
    # Retain original package wording. No guessed units, GTIN or food identity.
    product = wrap('product', key, {
        'name': raw['name'], 'names': {'en-AU': raw['name']},
        'identifiers': identifiers, 'brand': None,
        'pack': {'value': None, 'unit': None, 'label': raw['pack_size_raw']},
        'categories': raw['categories'], 'categoryScope': raw['category_scope'],
        'marketCountry': 'AU', 'retailerId': retailer_id,
        'ingredientsText': None, 'nutritionId': None,
        'allergens': None, 'ingredientConcepts': [],
        'ingredientMappingStatus': 'unresolved',
        'qualificationStatus': 'unverified-source-assertions',
    }, raw, manifest, line)
    availability = {'many_in_stock': 'in-stock', 'out_of_stock': 'out-of-stock',
                    'not_stated': 'unknown'}[raw['stock_status']]
    price = wrap('priceObservation', key + ':' + manifest['releaseId'], {
        'name': raw['name'], 'productId': product_id, 'identifiers': identifiers,
        'categoryScope': raw['category_scope'],
        'amount': amount, 'currency': 'AUD',
        'observedAt': raw['last_observed_at'],
        'priceType': 'dated-catalogue-observation',
        'basis': {'sourceText': raw['price_display_raw'],
                  'per': raw['price_basis'], 'packLabel': raw['pack_size_raw'],
                  'estimatedWeight': raw['estimated_weight_price']},
        'unitPrice': None, 'unit': None, 'promotion': None,
        'availability': availability, 'sourceStockStatus': raw['stock_status'],
        'availabilityBasis': 'DoorDash display at capture time; physical stock not verified',
        'sourceAvailabilityBadges': raw['availability_badges_raw'],
        'retailer': {'id': retailer_id, 'name': 'ALDI',
                     'externalId': raw['source_store_id'],
                     'location': raw['store_address_public']},
    }, raw, manifest, line)
    return [product, price]


def graph_packet(row):
    """Existing offmenu-common/1 envelope, preserving recursively typed facts."""
    rid = 'urn:offmenu:source-record:' + hashlib.sha256(row['id'].encode()).hexdigest()
    cid = rid + ':citation'

    def text(value, path):
        return {'kind': 'text', 'id': rid + ':text:' + hashlib.sha256(path.encode()).hexdigest(),
                'language': row.get('language', 'und'), 'value': value,
                'sourceTextSha256': hashlib.sha256(value.encode()).hexdigest(),
                'status': 'source-asserted', 'citationIds': [cid]}

    def typed(value, path):
        if value is None: return {'kind': 'null', 'value': None}
        if isinstance(value, bool): return {'kind': 'boolean', 'value': value}
        if isinstance(value, (int, float)): return {'kind': 'number', 'value': value}
        if isinstance(value, list): return {'kind': 'list', 'items': [typed(v, path + '.' + str(i)) for i, v in enumerate(value)]}
        if isinstance(value, dict): return {'kind': 'structure', 'fields': {k: typed(v, path + '.' + k) for k, v in value.items()}}
        field = path.rsplit('.', 1)[-1]
        if field in {'id', 'kind', 'schemaVersion', 'recordId', 'sourceId', 'releaseId', 'currency', 'system', 'unit', 'visibility', 'transform', 'sha256', 'sourceManifestSha256'} or field.endswith('Id') or path.startswith('countries.') or '.identifiers.' in path:
            return {'kind': 'identifier', 'value': value}
        if field in {'fetchedAt', 'observedAt'}:
            return {'kind': 'datetime', 'value': value}
        if value.startswith(('https://', 'urn:')):
            return {'kind': 'uri', 'value': value}
        return text(value, path)

    p = row['provenance']
    return {'schemaVersion': 'offmenu-common/1',
            'resources': [{'id': rid, 'type': 'urn:offmenu:type:' + {'product': 'Product', 'priceObservation': 'PriceObservation', 'retailer': 'Retailer'}[row['kind']],
                           'identityStatus': 'source-scoped',
                           'names': [text(row['data'].get('name', row['id']), 'data.name')],
                           'citationIds': [cid], 'scope': SCOPE}],
            'assertions': [{'id': rid + ':fact:' + key, 'subjectId': rid,
                            'propertyId': 'urn:offmenu:property:source-field:' + key,
                            'value': typed(value, key), 'status': 'source-asserted',
                            'citationIds': [cid], 'sourcePath': key, 'scope': SCOPE}
                           for key, value in row.items()],
            'relations': [], 'translations': [],
            'citations': [{'id': cid, 'sourceId': p['sourceId'], 'originalRecordId': p['recordId'],
                           'originalUrl': p['url'], 'license': LICENSE,
                           'attribution': p['attribution'], 'scope': SCOPE,
                           'contentSha256': p['originalRecord']['sha256'],
                           'sourcePath': p['originalRecord']['file'] + ':line:' + str(p['originalRecord']['line'])}]}


def import_snapshot(capture, output):
    capture, output = Path(capture).resolve(), Path(output).resolve()
    upstream = json.loads((capture / 'manifest.json').read_text())
    for name in ('inventory.jsonl', 'category-coverage.json'):
        if digest(capture / name) != upstream['files'][name]['sha256']:
            raise ValueError('Capture checksum mismatch: ' + name)
    manifest = {'sourceId': SOURCE, 'releaseId': 'aldi-doordash-' + digest(capture / 'inventory.jsonl')[:16],
                'sourceStoreId': upstream['source_store_id'], 'status': 'normalized-local-restricted',
                'schemaVersion': '1.0', 'commonSchemaVersion': 'offmenu-common/1',
                'visibility': 'local-restricted', 'license': LICENSE,
                'upstreamManifest': str(capture / 'manifest.json'),
                'upstreamManifestSha256': digest(capture / 'manifest.json'),
                'upstreamInventorySha256': digest(capture / 'inventory.jsonl'),
                'sourceDate': None, 'capturedAt': upstream['capture_ended_utc'],
                'scope': 'Single ALDI store DoorDash snapshot; source-scoped products and dated prices, no ingredient equivalence or nutrition.',
                'publicationEligible': False}
    raw_rows = [json.loads(line) for line in (capture / 'inventory.jsonl').read_text().splitlines()]
    if len(raw_rows) != upstream['products'] or not raw_rows:
        raise ValueError('Capture product count mismatch')
    if len({(r['source_store_id'], r['source_item_id']) for r in raw_rows}) != len(raw_rows):
        raise ValueError('Duplicate capture source identity')
    observed = Counter(category for r in raw_rows for category in r['categories'])
    coverage = json.loads((capture / 'category-coverage.json').read_text())
    expected = {c['name']: c['displayed_result_counts'][0] for c in coverage}
    if dict(observed) != expected:
        raise ValueError('Category coverage mismatch')
    # Validate every source row before creating an immutable output.
    records = [record for line, raw in enumerate(raw_rows, 1) for record in normalize(raw, manifest, line)]
    retailer = wrap('retailer', manifest['sourceStoreId'], {
        'name': 'ALDI', 'identifiers': [{'system': 'DoorDash-store', 'value': manifest['sourceStoreId']}],
        'locations': [{'address': raw_rows[0]['store_address_public'], 'country': 'AU'}],
        'role': 'source-listed-retailer', 'ownershipVerified': False,
        'inventoryAvailability': 'unknown',
    }, raw_rows[0], manifest, 1)
    retailer['provenance']['recordId'] = manifest['sourceStoreId']
    records.append(retailer)
    output.mkdir(parents=True, exist_ok=False)
    with gzip.open(output / 'normalized.jsonl.gz', 'wt', encoding='utf-8') as normalized, gzip.open(output / 'common.jsonl.gz', 'wt', encoding='utf-8') as common, sqlite3.connect(output / 'records.sqlite') as db:
        db.execute('CREATE TABLE records (ordinal INTEGER PRIMARY KEY, id TEXT UNIQUE, kind TEXT, name TEXT, category_scope TEXT, document TEXT)')
        db.execute('CREATE INDEX records_kind ON records(kind, ordinal)')
        for ordinal, row in enumerate(records):
            document = json.dumps(row, ensure_ascii=False, separators=(',', ':'))
            normalized.write(document + '\n')
            common.write(json.dumps(graph_packet(row), ensure_ascii=False, separators=(',', ':')) + '\n')
            db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', (ordinal, row['id'], row['kind'], row['data'].get('name', ''), row['data'].get('categoryScope'), document))
        db.commit()
    manifest.update(normalizedRows=len(records), counts=dict(Counter(r['kind'] for r in records)),
                    sourceListings=len(raw_rows), departments=len(coverage),
                    scopeCounts=dict(Counter(r['category_scope'] for r in raw_rows)))
    manifest['files'] = {p.name: {'sha256': digest(p), 'bytes': p.stat().st_size} for p in sorted(output.iterdir())}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


def read_page(directory, kind='product', query='', offset=0, limit=25, food_only=False, source=SOURCE):
    if kind not in ('product', 'priceObservation', 'retailer') or not 0 <= offset or not 1 <= limit <= 25:
        raise ValueError('Invalid kind/page bounds (maximum 25)')
    if str(directory) == source:
        pointer = json.loads((data_root() / source / 'current.json').read_text())
        directory = Path(pointer['directory']).resolve()
        if pointer['sourceId'] != source or digest(directory / 'manifest.json') != pointer['manifestSha256']:
            raise ValueError('Registered datasource manifest changed')
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest['sourceId'] != source or manifest['visibility'] != 'local-restricted':
        raise ValueError('Not a registered local ALDI datasource')
    if digest(directory / 'records.sqlite') != manifest['files']['records.sqlite']['sha256']:
        raise ValueError('Datasource snapshot changed')
    where, params = 'kind=?', [kind]
    if query:
        where += ' AND instr(lower(name),lower(?))>0'
        params.append(query)
    if food_only:
        where += " AND category_scope='food_or_beverage'"
    with sqlite3.connect((directory / 'records.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        total = db.execute('SELECT COUNT(*) FROM records WHERE ' + where, params).fetchone()[0]
        rows = db.execute('SELECT document FROM records WHERE ' + where + ' ORDER BY ordinal LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
    records = [json.loads(row[0]) for row in rows]
    return {'schema': 'offmenu-data-type-page/1', 'collection': kind + ':' + source,
            'snapshot': manifest['releaseId'], 'records': records,
            'pagination': {'offset': offset, 'limit': limit, 'returned': len(records), 'total': total,
                           'nextOffset': offset + len(records) if offset + len(records) < total else None},
            'scope': {'visibility': 'local-restricted', 'meaning': manifest['scope'],
                      'sourceManifestSHA256': digest(directory / 'manifest.json')}}
