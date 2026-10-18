"""Offline, bounded candidate projection of retained OFF, Prices and USDA files.

No network, admissions, acceptance or publication. Large/raw custody stays on
the separately authorized Foo runner; synthetic/small metadata placement follows
the reviewed runner capacity/locality/latency policy. Countries never create another download
or change source rights. Originals stay in the immutable cache; source.sqlite is
PRIVATE staging, not a public artifact (it can contain contributor metadata).
Malformed releases fail atomically; retry the same immutable inputs in a fresh
staging directory. A completed identical contract is checksum-verified and reused.
"""
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import struct
import tempfile
import zipfile
import zlib

from .core import RefreshError, canonical, strict_json

MIN_CACHE_SECONDS = 30 * 86400
VERSION = 'offmenu-products-offline/1'


@dataclass(frozen=True)
class ProductLimits:
    max_input_bytes: int = 64 * 1024**2
    max_expanded_bytes: int = 256 * 1024**2
    max_line_bytes: int = 4 * 1024**2
    max_rows: int = 1_000_000
    max_output_bytes: int = 256 * 1024**2
    max_database_bytes: int = 512 * 1024**2
    max_archive_members: int = 256
    max_nutrients_per_food: int = 4096

    def validate(self):
        if any(type(v) is not int or v <= 0 for v in asdict(self).values()):
            raise RefreshError('product-invalid-limits')


@dataclass(frozen=True)
class ProductContext:
    source_id: str
    release_id: str
    acquired_at: str
    license: str
    attribution: str
    rights_evidence_sha256: str
    scope_evidence_sha256: str
    cache_seconds: int = MIN_CACHE_SECONDS

    def validate(self):
        if self.source_id not in ('off', 'prices', 'usda-files'):
            raise RefreshError('product-unsupported-source')
        if not all(isinstance(v, str) and v for v in (self.release_id, self.license, self.attribution)):
            raise RefreshError('product-context-required')
        try:
            date = datetime.fromisoformat(self.acquired_at.replace('Z', '+00:00'))
            if date.tzinfo is None:
                raise ValueError()
        except (ValueError, AttributeError):
            raise RefreshError('product-acquisition-time-required') from None
        if any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v)
               for v in (self.rights_evidence_sha256, self.scope_evidence_sha256)):
            raise RefreshError('product-evidence-required')
        if type(self.cache_seconds) is not int or self.cache_seconds < MIN_CACHE_SECONDS:
            raise RefreshError('product-cache-too-short')


def _safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RefreshError('product-symlink-rejected')
    return path


def _hash(path, limit=None):
    size = path.stat().st_size
    if limit is not None and size > limit:
        raise RefreshError('product-file-bound-exceeded')
    h = hashlib.sha256()
    consumed = 0
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            consumed += len(block)
            if consumed > size:
                raise RefreshError('product-file-changed')
            h.update(block)
    if consumed != size:
        raise RefreshError('product-file-changed')
    return h.hexdigest()


class _Budget:
    def __init__(self, limits):
        self.limits, self.expanded, self.rows = limits, 0, 0
        self.csv_record_bytes = None

    def lines(self, stream):
        first = True
        while True:
            line = stream.readline(self.limits.max_line_bytes + 1)
            if not line:
                return
            self.expanded += len(line)
            if self.csv_record_bytes is not None:
                self.csv_record_bytes += len(line)
                if self.csv_record_bytes > self.limits.max_line_bytes:
                    raise RefreshError('product-csv-record-limit')
            if len(line) > self.limits.max_line_bytes or self.expanded > self.limits.max_expanded_bytes:
                raise RefreshError('product-expanded-limit')
            yield line.decode('utf-8-sig' if first else 'utf-8')
            first = False

    def row(self):
        self.rows += 1
        if self.rows > self.limits.max_rows:
            raise RefreshError('product-row-limit')


def _identity(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise RefreshError('product-source-identity-required')
    return str(value)


def _number(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise RefreshError('product-invalid-number')
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise RefreshError('product-invalid-number') from None
    if not math.isfinite(n):
        raise RefreshError('product-invalid-number')
    return n


def _put(db, table, ordinal, row, key=None, parent=None):
    db.execute('INSERT INTO raw VALUES (?,?,?,?,?)',
               (table, ordinal, key, parent, canonical(row).decode()))


def _get(db, table, key):
    row = db.execute('SELECT body FROM raw WHERE tab=? AND identity=?', (table, str(key))).fetchone()
    return json.loads(row[0]) if row else None


def _jsonl(db, table, path, budget, code=False):
    count = 0
    with gzip.open(path, 'rb') as stream:
        for line in budget.lines(stream):
            budget.row()
            row = strict_json(line)
            if not isinstance(row, dict):
                raise RefreshError('product-object-required')
            key = _identity(row.get('code' if code else 'id'))
            if code and not re.fullmatch('[0-9]{4,32}', key):
                raise RefreshError('product-invalid-barcode')
            count += 1
            _put(db, table, count, row, key)
    return count


def _zip_metadata(path, limits):
    # ZipFile reads the entire central directory at open. Bound it beforehand,
    # including ZIP64 exports, so member-count checking is not too late.
    with path.open('rb') as stream:
        size = path.stat().st_size
        stream.seek(max(0, size - 65557))
        tail = stream.read(65557)
        offset = tail.rfind(b'PK\x05\x06')
        if offset < 0 or len(tail) - offset < 22:
            raise RefreshError('product-invalid-zip-directory')
        _, disk, directory_disk, disk_entries, entries, directory_bytes, directory_offset, comment = struct.unpack_from('<4s4H2LH', tail, offset)
        if disk or directory_disk or len(tail) - offset != 22 + comment:
            raise RefreshError('product-invalid-zip-directory')
        if entries == 65535 or directory_bytes == 0xffffffff or directory_offset == 0xffffffff:
            eocd = size - len(tail) + offset
            if eocd < 20:
                raise RefreshError('product-invalid-zip-directory')
            stream.seek(eocd - 20)
            signature, disk, location, disks = struct.unpack('<4sLQL', stream.read(20))
            if signature != b'PK\x06\x07' or disk or disks != 1:
                raise RefreshError('product-invalid-zip-directory')
            stream.seek(location)
            raw = stream.read(56)
            if len(raw) != 56 or raw[:4] != b'PK\x06\x06':
                raise RefreshError('product-invalid-zip-directory')
            _, record_size, _, _, disk, directory_disk, disk_entries, entries, directory_bytes, directory_offset = struct.unpack('<4sQ2H2L4Q', raw)
            if disk or directory_disk or disk_entries != entries or record_size < 44:
                raise RefreshError('product-invalid-zip-directory')
        if entries > limits.max_archive_members or directory_bytes > limits.max_archive_members * 65536:
            raise RefreshError('product-archive-member-limit')
        if directory_offset + directory_bytes > size:
            raise RefreshError('product-invalid-zip-directory')


def _usda(db, path, budget):
    seen = set()
    required = {'food': {'fdc_id', 'description', 'data_type'},
                'food_nutrient': {'id', 'fdc_id', 'nutrient_id', 'amount'},
                'nutrient': {'id', 'name', 'unit_name'}}
    _zip_metadata(path, budget.limits)
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > budget.limits.max_archive_members:
            raise RefreshError('product-archive-member-limit')
        if sum(m.file_size for m in members) > budget.limits.max_expanded_bytes:
            raise RefreshError('product-expanded-limit')
        for member in members:
            name = PurePosixPath(member.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in member.filename or member.flag_bits & 1:
                raise RefreshError('product-unsafe-archive-member')
            if member.is_dir() or name.suffix.lower() != '.csv':
                continue  # Supporting assets remain in the pinned original ZIP.
            table = name.stem
            if not re.fullmatch('[a-z][a-z_]*', table) or table in seen:
                raise RefreshError('product-duplicate-or-invalid-table')
            seen.add(table)
            with archive.open(member) as stream:
                budget.csv_record_bytes = 0
                reader = csv.reader(budget.lines(stream), strict=True)
                headers = next(reader, None)
                if (not headers or len(headers) != len(set(headers)) or
                        any(not h or '\x00' in h for h in headers) or
                        not required.get(table, set()) <= set(headers)):
                    raise RefreshError('product-invalid-csv-columns')
                budget.csv_record_bytes = 0
                for ordinal, cells in enumerate(reader, 1):
                    budget.csv_record_bytes = 0
                    budget.row()
                    if len(cells) != len(headers) or sum(len(s.encode()) for s in cells) > budget.limits.max_line_bytes:
                        raise RefreshError('product-invalid-csv-row')
                    row = dict(zip(headers, cells))
                    key = row.get('fdc_id') if table in ('food', 'branded_food') else row.get('id')
                    if table in required or table == 'branded_food':
                        key = _identity(key)
                    else:
                        key = None  # Supporting tables retain duplicate raw IDs losslessly.
                    _put(db, table, ordinal, row, key, row.get('fdc_id') if table == 'food_nutrient' else None)
    if not set(required) <= seen:
        raise RefreshError('product-missing-usda-tables')
    for table in ('branded_food', 'food_nutrient'):
        column = 'identity' if table == 'branded_food' else 'parent'
        orphan = db.execute(f'SELECT 1 FROM raw a WHERE a.tab=? AND NOT EXISTS '
                            f'(SELECT 1 FROM raw b WHERE b.tab="food" AND b.identity=a.{column}) LIMIT 1', (table,)).fetchone()
        if orphan:
            raise RefreshError('product-orphan-food-reference')


def _record(context, kind, key, data, countries=(), source_date=None):
    return {'schemaVersion': '1.0', 'kind': kind,
            'id': f'{context.source_id}:{kind}:{key}', 'countries': list(countries),
            'data': data, 'provenance': {'sourceId': context.source_id,
            'releaseId': context.release_id, 'recordId': str(key),
            'fetchedAt': context.acquired_at, 'sourceDate': source_date,
            'license': context.license, 'attribution': context.attribution,
            'rightsEvidenceSha256': context.rights_evidence_sha256,
            'scopeEvidenceSha256': context.scope_evidence_sha256,
            'transform': VERSION, 'visibility': 'private-candidate',
            'rights': 'Original source terms govern reuse; normalization does not relicense data.'}}


_OFF_NUTRIENTS = {'energy-kcal_100g': ('energy', 'kcal'), 'proteins_100g': ('protein', 'g'),
    'fat_100g': ('fat', 'g'), 'carbohydrates_100g': ('carbohydrate', 'g'),
    'sugars_100g': ('sugars', 'g'), 'fiber_100g': ('fibre', 'g'),
    'sodium_100g': ('sodium', 'g'), 'salt_100g': ('salt', 'g'),
    'saturated-fat_100g': ('saturatedFat', 'g')}
_USDA_NUTRIENTS = {'1008': 'energy', '1003': 'protein', '1004': 'fat',
    '1005': 'carbohydrate', '2000': 'sugars', '1079': 'fibre', '1093': 'sodium',
    '1258': 'saturatedFat', '1087': 'calcium', '1089': 'iron', '1092': 'potassium', '1162': 'vitaminC'}


def _off(context, row):
    key = str(row['code'])
    identifiers = [{'system': 'barcode', 'value': key}]
    # Country names/tags remain unmodified. No guessed name-to-ISO translation.
    countries = []  # Resolve source tags only through a separately reviewed country mapping.
    basis = {'amount': 100, 'unit': 'ml' if row.get('nutrition_data_per') == '100ml' else 'g',
             'state': 'as-sold', 'qualificationStatus': 'unverified-source-assertions'}
    raw_nutrients = row.get('nutriments') or {}
    if not isinstance(raw_nutrients, dict):
        raise RefreshError('product-invalid-nutriments')
    nutrients = {name: {'value': _number(raw_nutrients[field]), 'unit': unit, 'basis': basis,
                       'sourceAmount': raw_nutrients[field], 'sourceField': field, 'method': 'source'}
                 for field, (name, unit) in _OFF_NUTRIENTS.items() if field in raw_nutrients}
    name = row.get('product_name') or row.get('product_name_en') or key
    yield _record(context, 'product', key, {'name': name, 'identifiers': identifiers,
        'brand': row.get('brands'), 'ingredientsText': row.get('ingredients_text'),
        'sourceCountryTags': row.get('countries_tags', []), 'rawNutriments': raw_nutrients,
        'nutritionSourceBasis': row.get('nutrition_data_per'),
        'qualificationStatus': 'unverified-source-assertions',
        'nutritionId': f'off:nutrientProfile:{key}'}, countries)
    yield _record(context, 'nutrientProfile', key, {'foodName': name, 'identifiers': identifiers,
                  'basis': basis, 'nutrients': nutrients}, countries)


def _price(context, db, row):
    location = _get(db, 'locations', row['location_id']) if row.get('location_id') is not None else {}
    if location is None or (row.get('proof_id') is not None and _get(db, 'proofs', row['proof_id']) is None):
        raise RefreshError('product-unresolved-price-reference')
    code = location.get('osm_address_country_code')
    countries = [code.upper()] if isinstance(code, str) and re.fullmatch('[a-zA-Z]{2}', code) else []
    # Whitelist projection: never leak contributor identity, proof images or comments.
    yield _record(context, 'priceObservation', row['id'], {
        'identifiers': [{'system': 'barcode', 'value': str(row['product_code'])}] if row.get('product_code') else [],
        'amount': _number(row.get('price')), 'sourceAmount': row.get('price'),
        'currency': row.get('currency'), 'observedAt': row.get('date'),
        'unitPrice': _number(row.get('price_per_unit')), 'sourceUnitPrice': row.get('price_per_unit'),
        'unit': row.get('price_per'), 'regularAmount': _number(row.get('price_without_discount')),
        'sourceRegularAmount': row.get('price_without_discount'),
        'promotion': row.get('price_is_discounted') if isinstance(row.get('price_is_discounted'), bool) else None,
        'proofId': row.get('proof_id'), 'duplicateOf': row.get('duplicate_of'),
        'retailer': {'name': location.get('osm_name'), 'externalId': str(row.get('location_id', '')),
                     'location': location.get('osm_display_name')},
        'availability': 'unknown', 'priceType': 'dated-observation'}, countries, row.get('date'))


def _food(context, db, row, limits):
    key = row['fdc_id']
    brand = _get(db, 'branded_food', key) or {}
    identifiers = [{'system': 'USDA-FDC', 'value': key}]
    if brand.get('gtin_upc'):
        identifiers.append({'system': 'barcode', 'value': brand['gtin_upc']})
    basis = {'amount': 100, 'unit': 'g', 'state': 'as-described'}
    nutrients = {}
    nutrient_bytes = 0
    for ordinal, (body,) in enumerate(db.execute('SELECT body FROM raw WHERE tab="food_nutrient" AND parent=? ORDER BY ordinal', (key,)), 1):
        if ordinal > limits.max_nutrients_per_food:
            raise RefreshError('product-nutrient-limit')
        n = json.loads(body)
        definition = _get(db, 'nutrient', n['nutrient_id'])
        if definition is None:
            raise RefreshError('product-unknown-nutrient')
        name = _USDA_NUTRIENTS.get(n['nutrient_id'], 'usda:' + n['nutrient_id'])
        if name in nutrients:
            name += ':observation:' + n['id']
        observation = {'value': _number(n['amount']), 'unit': definition['unit_name'].lower(),
            'sourceAmount': n['amount'], 'sourceUnit': definition['unit_name'],
            'sourceName': definition['name'], 'sourceNutrientId': n['nutrient_id'],
            'sourceRowId': n['id'], 'rawFields': n, 'basis': basis, 'method': 'source'}
        nutrient_bytes += len(canonical(observation)) + len(name.encode('utf-8'))
        if nutrient_bytes > limits.max_line_bytes:
            raise RefreshError('product-nutrient-byte-limit')
        nutrients[name] = observation
    yield _record(context, 'product', key, {'name': row['description'], 'identifiers': identifiers,
        'brand': brand.get('brand_owner') or brand.get('brand_name'), 'dataType': row['data_type'],
        'ingredientsText': brand.get('ingredients'), 'marketCountry': brand.get('market_country'),
        'serving': {'amount': _number(brand.get('serving_size')), 'unit': brand.get('serving_size_unit'),
                    'label': brand.get('household_serving_fulltext')},
        'nutritionId': f'usda-files:nutrientProfile:{key}'}, ('US',), row.get('publication_date'))
    yield _record(context, 'nutrientProfile', key, {'foodName': row['description'],
                  'identifiers': identifiers, 'basis': basis, 'nutrients': nutrients}, ('US',), row.get('publication_date'))


def _candidate_stats(path, limits):
    """Recompute displayed metadata from the verified bounded candidate bytes."""
    count = total = 0
    kinds = {}
    with path.open('rb') as source:
        while True:
            line = source.readline(limits.max_line_bytes + 1)
            if not line:
                break
            total += len(line)
            if len(line) > limits.max_line_bytes or total > limits.max_output_bytes:
                raise RefreshError('product-retry-candidate-bound')
            packet = strict_json(line)
            if (not isinstance(packet, list) or len(packet) != 1
                    or not isinstance(packet[0], dict) or not isinstance(packet[0].get('kind'), str)):
                raise RefreshError('product-retry-candidate-shape')
            kind = packet[0]['kind']
            kinds[kind] = kinds.get(kind, 0) + 1
            count += 1
    return count, total, kinds


def _candidate_manifest(context, files, contract, hashes, raw_rows, count, kinds, output_bytes):
    return {'schemaVersion': 'offmenu-product-candidate/1', 'status': 'normalized-candidate',
        'sourceId': context.source_id, 'releaseId': context.release_id,
        'acquiredAt': context.acquired_at, 'cacheSeconds': context.cache_seconds,
        'rightsEvidenceSha256': context.rights_evidence_sha256,
        'scopeEvidenceSha256': context.scope_evidence_sha256,
        'inputFiles': files, 'rawRows': raw_rows, 'normalizedRecords': count, 'kinds': kinds,
        'candidateSha256': hashes['candidate.jsonl'], 'candidateBytes': output_bytes,
        'outputHashes': hashes, 'contract': contract,
        'sharedSourceKey': hashlib.sha256(canonical(contract)).hexdigest(),
        'rawStorage': {'path': 'source.sqlite', 'visibility': 'private', 'publishable': False},
        'accepted': False}


def normalize_products(context, inputs, destination, *, limits=ProductLimits()):
    """Make private candidate files, never an admission. inputs are role -> Path:

    off: products; prices: prices, locations, proofs; usda-files: archive.
    Existing complete matching output is verified/reused; changed contract or
    corrupted output fails closed. Failures clean only this call's staging tree.
    Rights evidence strings are attribution, NOT proof of permission to execute.
    Caller must enforce reviewed input pins, Foo custody and operation authority.
    """
    context.validate()
    limits.validate()
    roles = {'off': {'products'}, 'prices': {'prices', 'locations', 'proofs'}, 'usda-files': {'archive'}}[context.source_id]
    if set(inputs) != roles:
        raise RefreshError('product-input-set-mismatch')
    paths = {role: _safe(path) for role, path in inputs.items()}
    if any(not path.is_file() for path in paths.values()):
        raise RefreshError('product-input-missing')
    if sum(path.stat().st_size for path in paths.values()) > limits.max_input_bytes:
        raise RefreshError('product-input-limit')
    files = [{'role': role, 'path': path.name, 'bytes': path.stat().st_size, 'sha256': _hash(path)}
             for role, path in sorted(paths.items())]
    contract = {'context': asdict(context), 'limits': asdict(limits), 'inputFiles': files, 'adapterVersion': VERSION}
    destination = _safe(destination)
    if destination.exists():
        manifest_path = _safe(destination / 'manifest.json')
        if manifest_path.stat().st_size > 1024 * 1024:
            raise RefreshError('product-retry-manifest-limit')
        manifest = strict_json(manifest_path.read_bytes())
        if manifest.get('contract') != contract:
            raise RefreshError('product-retry-contract-mismatch')
        hashes = manifest.get('outputHashes')
        if not isinstance(hashes, dict) or set(hashes) != {'candidate.jsonl', 'source.sqlite'}:
            raise RefreshError('product-retry-output-mismatch')
        for name, checksum in hashes.items():
            if _hash(_safe(destination / name), limits.max_output_bytes if name == 'candidate.jsonl' else limits.max_database_bytes) != checksum:
                raise RefreshError('product-retry-output-mismatch')
        count, output_bytes, kinds = _candidate_stats(destination / 'candidate.jsonl', limits)
        with closing(sqlite3.connect((destination / 'source.sqlite').as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
            raw_rows = db.execute('SELECT COUNT(*) FROM raw').fetchone()[0]
        expected = _candidate_manifest(context, files, contract, hashes, raw_rows, count, kinds, output_bytes)
        # Canonical bytes also distinguish JSON false from numeric zero.
        if canonical(manifest) != canonical(expected):
            raise RefreshError('product-retry-manifest-mismatch')
        return manifest
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix='.products-', dir=destination.parent))
    db = None
    try:
        db = sqlite3.connect(pending / 'source.sqlite')
        db.execute('PRAGMA page_size=4096')
        db.execute('PRAGMA cache_size=-2048')
        db.execute('PRAGMA temp_store=FILE')
        db.execute('PRAGMA journal_mode=OFF')  # staging discarded on any failure
        db.execute(f'PRAGMA max_page_count={max(1, limits.max_database_bytes // 4096)}')
        db.execute('CREATE TABLE raw(tab TEXT, ordinal INTEGER, identity TEXT, parent TEXT, body TEXT NOT NULL, PRIMARY KEY(tab,ordinal))')
        db.execute('CREATE UNIQUE INDEX identity_idx ON raw(tab,identity)')
        db.execute('CREATE INDEX parent_idx ON raw(tab,parent,ordinal)')
        budget = _Budget(limits)
        if context.source_id == 'usda-files':
            _usda(db, paths['archive'], budget)
            table = 'food'
        else:
            for role in sorted(paths):
                _jsonl(db, role, paths[role], budget, code=context.source_id == 'off')
            table = 'products' if context.source_id == 'off' else 'prices'
        db.commit()
        count = output_bytes = 0
        kinds = {}
        with (pending / 'candidate.jsonl').open('wb') as output:
            for source_row, body in db.execute('SELECT ordinal,body FROM raw WHERE tab=? ORDER BY ordinal', (table,)):
                row = json.loads(body)
                records = (_off(context, row) if table == 'products' else
                           _price(context, db, row) if table == 'prices' else _food(context, db, row, limits))
                for record in records:
                    record['provenance']['sourceRow'] = source_row
                    if table == 'products':
                        record['provenance']['sourceRevision'] = row.get('rev')
                        record['provenance']['sourceLastModified'] = row.get('last_modified_t')
                        record['provenance']['sourceLastUpdated'] = row.get('last_updated_t')
                    record['provenance']['inputSha256'] = {pin['role']: pin['sha256'] for pin in files}
                    data = canonical([record])
                    output_bytes += len(data)
                    if len(data) > limits.max_line_bytes or output_bytes > limits.max_output_bytes:
                        raise RefreshError('product-output-limit')
                    output.write(data)
                    count += 1
                    kinds[record['kind']] = kinds.get(record['kind'], 0) + 1
        if not count:
            raise RefreshError('product-empty-candidate')
        db.close()
        db = None
        # Guard cache mutations during ingestion; no retry can mix releases.
        if any(path.stat().st_size != pin['bytes'] or _hash(path) != pin['sha256']
               for pin in files for role, path in paths.items() if role == pin['role']):
            raise RefreshError('product-input-changed')
        hashes = {name: _hash(pending / name) for name in ('candidate.jsonl', 'source.sqlite')}
        manifest = _candidate_manifest(context, files, contract, hashes, budget.rows, count, kinds, output_bytes)
        (pending / 'manifest.json').write_bytes(canonical(manifest))
        if destination.exists():
            raise RefreshError('product-destination-race')
        pending.rename(destination)
        return manifest
    except RefreshError:
        raise
    except (ValueError, csv.Error, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, EOFError,
            sqlite3.DatabaseError, OSError, TypeError, KeyError, RecursionError, struct.error, zlib.error) as exc:
        raise RefreshError('product-invalid-or-unreadable-release') from exc
    finally:
        if db is not None:
            db.close()
        if pending.exists():
            shutil.rmtree(pending)
