"""Partner-neutral local price evidence. Discovery never implies captured coverage."""
import gzip
import json
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from .aldi_datasource import digest, graph_packet, register_snapshot, read_page, LICENSE

SOURCE = 'delivery-retail-global'
REGISTRY = Path(__file__).resolve().parents[1] / 'corpus' / 'delivery-partners.json'


def registry():
    return json.loads(REGISTRY.read_text())


def required_text(row, field):
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing nonempty string: ' + field)
    return value


def normalize(row, line, raw_hash, release):
    if not isinstance(row, dict):
        raise ValueError('Observation must be an object')
    for field in ('partnerId', 'storeId', 'itemId', 'observationId', 'name', 'retailerName',
                  'country', 'currency', 'observedAt', 'sourceUrl', 'priceDisplay', 'priceBasis'):
        required_text(row, field)
    if not re.fullmatch('[a-z0-9][a-z0-9-]*', row['partnerId']):
        raise ValueError('Invalid partner ID')
    if not re.fullmatch('[A-Z]{2}', row['country']) or not re.fullmatch('[A-Z]{3}', row['currency']):
        raise ValueError('Use uppercase country/currency codes')
    stamp = datetime.fromisoformat(row['observedAt'].replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Observation timestamp must include timezone')
    url = urlsplit(row['sourceUrl'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Expected public HTTPS source URL without credentials')
    amount = row.get('amount')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
        raise ValueError('Expected finite nonnegative observed price')
    if row['priceBasis'] not in ('per-pack', 'per-unit', 'per-weight', 'estimated-weight', 'unknown'):
        raise ValueError('Unrecognized price basis')
    if row.get('categoryScope', 'unknown') not in ('food_or_beverage', 'mixed', 'non_food', 'unknown', 'non_food_department', 'mixed_department_requires_item_review'):
        raise ValueError('Invalid category scope')
    for field in ('packLabel', 'language', 'brand', 'availability', 'availabilityText'):
        if row.get(field) is not None and not isinstance(row[field], str):
            raise ValueError('Expected string or null: ' + field)
    for field in ('promotion', 'membership', 'tax', 'fees', 'unitPrice'):
        if row.get(field) is not None and not isinstance(row[field], dict):
            raise ValueError('Expected observed object or null: ' + field)
    # JSON tuple hashing prevents delimiter collisions and does not turn SKUs into GTINs.
    def key(parts):
        import hashlib
        return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()
    store_key = key([row['partnerId'], row['country'], row['storeId']])
    item_key = key([row['partnerId'], row['country'], row['storeId'], row['itemId']])
    price_key = key([row['partnerId'], row['country'], row['storeId'], row['itemId'], row['observationId']])
    retailer_id = SOURCE + ':retailer:' + store_key
    product_id = SOURCE + ':product:' + item_key
    provenance = {'sourceId': SOURCE, 'recordId': row['observationId'], 'url': row['sourceUrl'],
                  'license': LICENSE, 'attribution': row['retailerName'] + ' via ' + row['partnerId'],
                  'fetchedAt': row['observedAt'], 'sourceDate': None, 'visibility': 'local-restricted',
                  'transform': 'offmenu-delivery-pricing/1', 'releaseId': release,
                  'upstreamEvidence': row.get('upstreamEvidence'),
                  'originalRecord': {'file': 'observations.jsonl', 'line': line, 'sha256': raw_hash}}
    def wrap(kind, ident, data):
        return {'schemaVersion': '1.0', 'kind': kind, 'id': SOURCE + ':' + kind + ':' + ident,
                'language': row.get('language') or 'und', 'countries': [row['country']],
                'provenance': dict(provenance), 'data': data}
    identity = {'partnerId': row['partnerId'], 'sourceStoreId': row['storeId'], 'sourceItemId': row['itemId']}
    product = wrap('product', item_key, dict(identity, name=row['name'], brand=row.get('brand'),
        pack={'label': row.get('packLabel'), 'value': None, 'unit': None},
        retailerId=retailer_id, categoryScope=row.get('categoryScope', 'unknown'),
        ingredientConcepts=[], ingredientMappingStatus='unresolved', identifiers=[
            {'system': row['partnerId'] + '-store-item', 'value': json.dumps([row['storeId'], row['itemId']])}]))
    price = wrap('priceObservation', price_key, dict(identity, name=row['name'], productId=product_id,
        retailerId=retailer_id, amount=amount, currency=row['currency'], observedAt=row['observedAt'],
        priceType='dated-delivery-catalogue-observation', categoryScope=row.get('categoryScope', 'unknown'),
        basis={'per': row['priceBasis'], 'sourceText': row['priceDisplay'], 'packLabel': row.get('packLabel')},
        unitPrice=row.get('unitPrice'), promotion=row.get('promotion'), membership=row.get('membership'),
        tax=row.get('tax'), fees=row.get('fees'), availability=row.get('availability', 'unknown'),
        availabilityText=row.get('availabilityText'), shelfPriceEquivalence='unknown',
        checkoutTotal=None, currencyConversion=None))
    retailer = wrap('retailer', store_key, {'name': row['retailerName'], 'partnerId': row['partnerId'],
        'sourceStoreId': row['storeId'], 'marketCountry': row['country'], 'ownershipVerified': False})
    return product, price, retailer


def import_observations(path, output):
    path, output = Path(path).resolve(), Path(output).resolve()
    # Preserve the exact imported evidence beside its normalized derivatives.
    raw_bytes = path.read_bytes()
    import hashlib
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    release = 'delivery-' + raw_hash[:20]
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    rows = [json.loads(line, parse_constant=invalid_constant) for line in raw_bytes.decode('utf-8').splitlines()]
    if not rows:
        raise ValueError('Empty observations')
    records, seen_prices = {}, set()
    for line, row in enumerate(rows, 1):
        product, price, retailer = normalize(row, line, raw_hash, release)
        if price['id'] in seen_prices:
            raise ValueError('Duplicate partner/store/item observation ID')
        seen_prices.add(price['id'])
        for record in (product, price, retailer):
            prior = records.get(record['id'])
            if prior and prior['data'] != record['data']:
                raise ValueError('Conflicting identity within snapshot; split captures by product version')
            records.setdefault(record['id'], record)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'observations.jsonl').write_bytes(raw_bytes)
    with gzip.open(output / 'normalized.jsonl.gz', 'wt', encoding='utf-8') as normal, gzip.open(output / 'common.jsonl.gz', 'wt', encoding='utf-8') as common, sqlite3.connect(output / 'records.sqlite') as db:
        db.execute('CREATE TABLE records (ordinal INTEGER PRIMARY KEY, id TEXT UNIQUE, kind TEXT, name TEXT, category_scope TEXT, document TEXT)')
        db.execute('CREATE INDEX records_kind ON records(kind, ordinal)')
        for i, record in enumerate(records.values()):
            document = json.dumps(record, ensure_ascii=False)
            normal.write(document + '\n')
            common.write(json.dumps(graph_packet(record), ensure_ascii=False) + '\n')
            db.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', (i, record['id'], record['kind'], record['data']['name'], record['data'].get('categoryScope'), document))
        db.commit()
    manifest = {'sourceId': SOURCE, 'releaseId': release, 'status': 'normalized-local-restricted',
        'visibility': 'local-restricted', 'publicationEligible': False, 'license': LICENSE,
        'scope': 'Dated delivery-platform retail observations; no live, shelf-price or worldwide-completeness claim.',
        'counts': dict(Counter(r['kind'] for r in records.values())), 'normalizedRows': len(records),
        'countries': sorted({r['country'] for r in rows}), 'currencies': sorted({r['currency'] for r in rows}),
        'partners': sorted({r['partnerId'] for r in rows}), 'sourceObservations': len(rows),
        'files': {p.name: {'sha256': digest(p), 'bytes': p.stat().st_size} for p in sorted(output.iterdir())}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def register(directory):
    return register_snapshot(directory, source=SOURCE)


def page(directory, **kwargs):
    return read_page(directory, source=SOURCE, **kwargs)
