"""Retained supplier, company/ownership and place readers; no acquisition or SQL.

This is an additive source-data adapter, not a canonical supplier/stock mapper.
The accepted PR83 organization packet contract is handled without executing its
independent schema/caller (or the unrelated supplier-review capsule). Original
payloads and explicit assertions survive; a food place is never a supplier,
owner, inventory item, price or offer merely because it was found in a file.
"""
from __future__ import annotations

import contextlib
import bz2
import csv
import gzip
import hashlib
import io
import json
import lzma
import math
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote

from ingest_api import BudgetExceeded, COUNTERS, SourceChanged, source_key

ADAPTER_VERSION = 1
MAX_ROW_BYTES = 4 * 1024 * 1024
CONTAINERS = frozenset(('records', 'rows', 'organizations', 'companies', 'entities',
                        'places', 'features', 'bindings', 'results', 'items'))
KNOWN_TABLES = frozenset(('suppliers', 'supplier', 'organizations', 'organization',
    'companies', 'company', 'ownership', 'company_ownership', 'companyownership',
    'places', 'place', 'entities', 'entity', 'records', 'normalized',
    'retained_reference_record', 'supplier_source_actor', 'locations'))
RELATION_PROPERTIES = {'P127': 'owned_by', 'P749': 'parent_organization',
                       'P355': 'subsidiary'}
RELATION_FIELDS = {'owner_id': 'owned_by', 'owned_by': 'owned_by',
    'parent_id': 'parent_organization', 'parent_company_id': 'parent_organization',
    'parent_organization': 'parent_organization', 'subsidiary_id': 'subsidiary'}


class MalformedSupplierRow(ValueError):
    pass


class UnsupportedSupplierSource(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise MalformedSupplierRow('duplicate_json_key')
        out[key] = value
    return out


def _nonfinite(value):
    raise MalformedSupplierRow('nonfinite_json_number')


DECODER = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_nonfinite)


def _strict(raw):
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    # JSON's exponent syntax can otherwise overflow to infinity.
    _json(value)
    return value


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextlib.contextmanager
def _binary(source):
    """Read a regular retained file only; do not follow links or accept mutation."""
    path = Path(source['path'])
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('symlink_source_refused')
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('source_not_regular_file')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(before):
            raise SourceChanged('source_changed_before_read')
        yield stream
        if (_identity(os.fstat(stream.fileno())) != _identity(before)
                or _identity(path.lstat()) != _identity(before)):
            raise SourceChanged('source_changed_during_read')


@contextlib.contextmanager
def _text(source):
    with _binary(source) as binary:
        compression = str(source.get('compression') or '').lower()
        if not compression:
            name = str(source['path']).lower()
            compression = next((suffix for suffix in ('gz', 'bz2', 'xz')
                                if name.endswith('.' + suffix)), '')
        if not compression and str(source.get('format', '')).lower().endswith(('.gz', '_gzip')):
            compression = 'gz'
        with contextlib.ExitStack() as stack:
            if compression in ('gz', 'gzip'):
                data = stack.enter_context(gzip.GzipFile(fileobj=binary))
            elif compression in ('bz2', 'bzip2'):
                data = stack.enter_context(bz2.BZ2File(binary))
            elif compression in ('xz', 'lzma'):
                data = stack.enter_context(lzma.LZMAFile(binary))
            elif compression:
                raise UnsupportedSupplierSource('unsupported_text_compression')
            else:
                data = binary
            text = io.TextIOWrapper(data, encoding='utf-8-sig', errors='strict', newline='')
            try:
                yield text
            finally:
                # Keep the pinned underlying FD open for the post-read identity check.
                text.detach()


class _JSONStream:
    """Bounded token reader; large arrays/wrappers are traversed incrementally."""
    def __init__(self, stream, maximum):
        self.stream, self.maximum, self.buf, self.pos, self.eof = stream, maximum, '', 0, False

    def _fill(self):
        self.buf = self.buf[self.pos:]
        self.pos = 0
        chunk = self.stream.read(min(65536, self.maximum + 1))
        self.eof = not chunk
        self.buf += chunk

    def peek(self):
        while True:
            while self.pos < len(self.buf) and self.buf[self.pos].isspace():
                self.pos += 1
            if self.pos < len(self.buf):
                return self.buf[self.pos]
            if self.eof:
                return ''
            self._fill()

    def take(self, character):
        if self.peek() != character:
            raise MalformedSupplierRow('invalid_json_structure')
        self.pos += 1

    def value(self):
        self.peek()
        while True:
            try:
                value, end = DECODER.raw_decode(self.buf, self.pos)
                # A number may end exactly at a buffer boundary; fetch its delimiter.
                if end == len(self.buf) and not self.eof:
                    self._fill()
                    continue
                if len(self.buf[self.pos:end].encode('utf-8')) > self.maximum:
                    raise MalformedSupplierRow('json_value_size_cap')
                self.pos = end
                _json(value)
                return value
            except json.JSONDecodeError:
                if self.eof:
                    raise MalformedSupplierRow('invalid_json_value') from None
                if len(self.buf[self.pos:].encode('utf-8')) > self.maximum:
                    raise MalformedSupplierRow('json_value_size_cap') from None
                self._fill()

    def records(self, pointer='$', depth=0):
        if depth > 12:
            raise MalformedSupplierRow('json_wrapper_depth_cap')
        if self.peek() == '[':
            self.take('[')
            ordinal = 0
            if self.peek() != ']':
                while True:
                    ordinal += 1
                    value = self.value()
                    yield from _packets(value, pointer + '/' + str(ordinal - 1))
                    if self.peek() != ',':
                        break
                    self.take(',')
            self.take(']')
        elif self.peek() == '{':
            self.take('{')
            retained, seen, wrapper = {}, set(), False
            if self.peek() != '}':
                while True:
                    key = self.value()
                    if not isinstance(key, str) or key in seen:
                        raise MalformedSupplierRow('invalid_json_object_key')
                    seen.add(key)
                    self.take(':')
                    # Never treat an individual organization's data object as a wrapper.
                    if ((key in CONTAINERS and self.peek() in ('[', '{'))
                            or (key == 'data' and self.peek() == '[')):
                        wrapper = True
                        yield from self.records(pointer + '/' + key, depth + 1)
                    else:
                        retained[key] = self.value()
                        if len(_json(retained).encode('utf-8')) > self.maximum:
                            raise MalformedSupplierRow('json_record_size_cap')
                    if self.peek() != ',':
                        break
                    self.take(',')
            self.take('}')
            if not wrapper:
                yield retained, pointer
        else:
            yield from _packets(self.value(), pointer)


def _packets(value, pointer):
    if isinstance(value, list):
        for ordinal, item in enumerate(value):
            if not isinstance(item, dict):
                raise MalformedSupplierRow('packet_item_not_object')
            yield item, pointer + '/' + str(ordinal)
    elif isinstance(value, dict):
        yield value, pointer
    else:
        raise MalformedSupplierRow('record_not_object')


def _format(source):
    fmt = str(source.get('format', '')).lower().replace('_gzip', '')
    for suffix in ('.gz', '.bz2', '.xz'):
        fmt = fmt.removesuffix(suffix)
    aliases = {'ndjson': 'jsonl', 'jsonlines': 'jsonl', 'sqlite3': 'sqlite',
               'db': 'sqlite', 'geojson': 'json', 'zstd.parquet': 'parquet'}
    fmt = aliases.get(fmt, fmt)
    if fmt:
        return fmt
    name = str(source['path']).lower()
    for suffix in ('.gz', '.bz2', '.xz'):
        name = name.removesuffix(suffix)
    return aliases.get(name.rsplit('.', 1)[-1], name.rsplit('.', 1)[-1])


def _bounded_lines(stream, maximum):
    while True:
        line = stream.readline(maximum + 1)
        if not line:
            return
        if len(line.encode('utf-8')) > maximum:
            # A physical CSV line cannot safely be resynchronized inside quotes.
            # Refuse this source, retaining earlier batches and trying other files.
            raise MalformedSupplierRow('csv_physical_line_size_cap')
        yield line


def _rows(source, maximum, on_error, check_budget):
    fmt = _format(source)
    if fmt in ('json', 'jsonl', 'csv', 'tsv'):
        with _text(source) as stream:
            if fmt == 'jsonl':
                ordinal = 0
                while True:
                    check_budget()
                    line = stream.readline(maximum + 1)
                    if not line:
                        break
                    ordinal += 1
                    if len(line.encode('utf-8')) > maximum:
                        # Drain one bad row in bounded pieces, then resume the next line.
                        while line and not line.endswith('\n'):
                            line = stream.readline(maximum + 1)
                            check_budget()
                        on_error(MalformedSupplierRow('line_size_cap'))
                        continue
                    if not line.strip():
                        continue
                    try:
                        yield from _packets(_strict(line), 'line:' + str(ordinal))
                    except (ValueError, TypeError, OverflowError) as exc:
                        on_error(exc)
            elif fmt == 'json':
                reader = _JSONStream(stream, maximum)
                yield from reader.records()
                if reader.peek():
                    raise MalformedSupplierRow('trailing_json_content')
            else:
                # csv's process-global field cap is left unchanged: adapters run in threads.
                reader = csv.DictReader(_bounded_lines(stream, maximum),
                                        delimiter='\t' if fmt == 'tsv' else ',', strict=True)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                    raise MalformedSupplierRow('invalid_csv_header')
                while True:
                    check_budget()
                    try:
                        row = next(reader)
                    except StopIteration:
                        break
                    except csv.Error as exc:
                        on_error(exc)
                        continue
                    if None in row or any(value is None for value in row.values()):
                        on_error(MalformedSupplierRow('csv_column_count'))
                        continue
                    if len(_json(row).encode('utf-8')) > maximum:
                        on_error(MalformedSupplierRow('csv_row_size_cap'))
                        continue
                    yield row, 'row:' + str(reader.line_num)
    elif fmt == 'sqlite':
        # Pin/validate regular file; SQL is fixed SELECT over actual table names.
        with _binary(source):
            uri = 'file:' + quote(str(Path(source['path']).resolve()), safe='/') + '?mode=ro'
            with contextlib.closing(sqlite3.connect(uri, uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                db.execute('PRAGMA trusted_schema=OFF')
                db.row_factory = sqlite3.Row
                tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                requested = source.get('table') or source.get('tables')
                if isinstance(requested, str):
                    requested = [requested]
                selected = [t for t in tables if t in requested] if requested else [t for t in tables if t.lower() in KNOWN_TABLES]
                # PR83 retains the original packet; don't additionally import derived actor copies.
                if not requested and 'retained_reference_record' in selected:
                    selected = ['retained_reference_record']
                if not selected:
                    raise UnsupportedSupplierSource('no_supported_supplier_table')
                for table in selected:
                    quoted = '"' + table.replace('"', '""') + '"'
                    for ordinal, row in enumerate(db.execute('SELECT * FROM ' + quoted), 1):
                        check_budget()
                        row = _json_safe(dict(row))
                        try:
                            for key in ('source_payload_json', 'record_json', 'payload_json', 'data_json'):
                                if isinstance(row.get(key), str):
                                    if len(row[key].encode('utf-8')) > maximum:
                                        raise MalformedSupplierRow('sqlite_row_size_cap')
                                    row = _strict(row[key])
                                    break
                            if len(_json(row).encode('utf-8')) > maximum:
                                raise MalformedSupplierRow('sqlite_row_size_cap')
                            yield from _packets(row, table + ':' + str(ordinal))
                        except (ValueError, TypeError, OverflowError) as exc:
                            on_error(exc)
    elif fmt == 'parquet':
        try:
            import pyarrow.parquet as parquet
        except ImportError:
            raise UnsupportedSupplierSource('parquet_dependency_unavailable') from None
        with _binary(source) as binary:
            reader = parquet.ParquetFile(binary)
            ordinal = 0
            for batch in reader.iter_batches(batch_size=32):
                check_budget()
                for row in batch.to_pylist():
                    ordinal += 1
                    try:
                        # WKB geometry is retained losslessly as hex, not discarded.
                        row = _json_safe(row)
                        if len(_json(row).encode('utf-8')) > maximum:
                            raise MalformedSupplierRow('parquet_row_size_cap')
                        yield row, 'row:' + str(ordinal)
                    except (ValueError, TypeError, OverflowError) as exc:
                        on_error(exc)
    else:
        raise UnsupportedSupplierSource('unsupported_supplier_format')


def _json_safe(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'encoding': 'hex', 'value': bytes(value).hex()}
    if isinstance(value, dict):
        return {key: _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(child) for child in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MalformedSupplierRow('nonfinite_parquet_number')
        return value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    # Decimal from Arrow is exact as text, not a lossy binary float.
    import decimal
    if isinstance(value, decimal.Decimal):
        return str(value)
    raise MalformedSupplierRow('unsupported_parquet_scalar')


def _scalar(value):
    if isinstance(value, dict):
        for key in ('value', 'primary', 'name', 'url', 'id', 'text'):
            if key in value:
                return _scalar(value[key])
        return None
    if isinstance(value, list):
        return next((item for item in (_scalar(x) for x in value) if item is not None), None)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value) if str(value).strip() else None
    return None


def _first(data, *keys):
    return next((value for value in (_scalar(data.get(key)) for key in keys) if value is not None), None)


def _entity_id(value):
    value = _scalar(value)
    if value and value.startswith(('https://www.wikidata.org/entity/', 'http://www.wikidata.org/entity/')):
        return value.rsplit('/', 1)[-1]
    return value


def _deprecated(data):
    return (data.get('deprecated') is True or data.get('deleted') is True
            or str(data.get('rank', '')).lower() == 'deprecated'
            or str(data.get('status', '')).lower() in ('deprecated', 'deleted', 'removed'))


def _claim_values(data, prop):
    claims = data.get('claims', {}).get(prop, []) if isinstance(data.get('claims'), dict) else []
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict) or _deprecated(claim):
            continue
        snak = claim.get('mainsnak', {})
        if not isinstance(snak, dict) or snak.get('snaktype', 'value') != 'value':
            continue
        value = snak.get('datavalue', {}).get('value') if isinstance(snak.get('datavalue'), dict) else None
        if isinstance(value, dict) and 'numeric-id' in value and 'id' not in value:
            value = 'Q' + str(value['numeric-id'])
        if _scalar(value):
            yield _scalar(value), claim


def _relations(data, entity_id):
    links = []
    for prop, kind in RELATION_PROPERTIES.items():
        for value, claim in _claim_values(data, prop):
            links.append({'kind': kind, 'target_domain': 'suppliers', 'target_id': _entity_id(value),
                          'subject_id': entity_id, 'source_property': prop,
                          'source_assertion': claim, 'canonical_link_status': 'unresolved'})
    for field, kind in RELATION_FIELDS.items():
        values = data.get(field, [])
        values = values if isinstance(values, list) else [values]
        for value in values:
            if isinstance(value, dict) and _deprecated(value):
                continue
            target = _entity_id(value)
            if target:
                links.append({'kind': kind, 'target_domain': 'suppliers', 'target_id': target,
                              'subject_id': entity_id, 'source_property': field,
                              'canonical_link_status': 'unresolved'})
    for link in data.get('relations', []) if isinstance(data.get('relations'), list) else []:
        if not isinstance(link, dict) or _deprecated(link):
            continue
        target = _entity_id(link.get('target_id') or link.get('object_id') or link.get('target'))
        kind = _first(link, 'kind', 'predicate', 'relationship', 'type')
        if target and kind:
            links.append({**link, 'kind': kind, 'target_id': target,
                          'target_domain': 'suppliers', 'canonical_link_status': 'unresolved'})
    return links


def normalize_record(row, source, pointer):
    """Map explicit native assertions, not ontology guesses or name-based joins."""
    if not isinstance(row, dict) or not row:
        raise MalformedSupplierRow('empty_or_nonobject_record')
    if _deprecated(row):
        return None
    payload = row
    provenance = row.get('provenance') if isinstance(row.get('provenance'), dict) else {}
    data = row.get('data') if isinstance(row.get('data'), dict) else row
    if row.get('type') == 'Feature' and isinstance(row.get('properties'), dict):
        data = row['properties']
    elif source.get('provider') == 'osm' and isinstance(row.get('tags'), dict):
        data = row['tags']
    if _deprecated(data):
        return None
    provider = str(source.get('provider') or provenance.get('sourceId') or 'retained')
    entity = _entity_id(provenance.get('recordId')) or _entity_id(
        _first(data, 'entity_id', 'entityid', 'wikidata_id', 'qid', 'company_id',
               'supplier_id', 'place_id', 'subject_id', 'company', 'item', 'entity', 'id'))
    for identifier in data.get('identifiers', []) if isinstance(data.get('identifiers'), list) else []:
        if not entity and isinstance(identifier, dict) and str(identifier.get('system', '')).lower() == 'wikidata':
            entity = _entity_id(identifier.get('value'))
    entity = entity or _entity_id(row.get('id'))
    declared = str(source.get('kind') or source.get('source_type') or row.get('kind') or '').lower()
    row_type = str(data.get('type', '')).lower()
    if provider.lower() in ('overture', 'osm') or declared in ('place', 'places', 'food_place', 'foodplaces', 'location', 'locations') or row_type == 'place':
        kind = 'food_place' if provider.lower() == 'overture' or 'food' in declared else 'place'
    elif declared in ('price', 'price_observation', 'price-observation', 'price_observations'):
        kind = 'price_observation'
    elif any(word in declared for word in ('ownership', 'relationship')):
        kind = 'company_ownership'
    elif declared in ('supplier', 'suppliers', 'supplier_entity'):
        kind = 'supplier_entity'
    else:
        # Wikidata direct food-business type assertions establish organizations,
        # not an actual business relationship with the user.
        kind = 'organization'
    name = _first(data, 'name', 'label', 'companyLabel', 'itemLabel', 'entityLabel', 'names')
    if not name and isinstance(data.get('labels'), dict):
        labels = data['labels']
        name = _scalar(labels.get('en')) or next((_scalar(v) for v in labels.values() if _scalar(v)), None)
    legal = _first(data, 'legal_name', 'legalname', 'legalName', 'registered_name')
    website = _first(data, 'website', 'websites', 'official_website', 'url')
    website = website or next((value for value, _ in _claim_values(data, 'P856')), None)
    country = _first(data, 'country', 'countries', 'country_code', 'countryCode', 'addr:country')
    country = country or _first(row, 'country', 'countries')
    country = country or next((value for value, _ in _claim_values(data, 'P17')), None)
    address = _first(data, 'address', 'street_address', 'streetAddress', 'addr:full')
    addresses = data.get('addresses')
    if isinstance(addresses, list) and addresses and isinstance(addresses[0], dict):
        country = country or _first(addresses[0], 'country', 'country_code')
        address = address or _first(addresses[0], 'freeform', 'formatted', 'street')
    links = _relations(data, entity)
    if kind == 'company_ownership':
        # An edge record's own ID is not its subject organization.
        subject = _entity_id(_first(data, 'subject_id', 'subject', 'company_id',
                                    'company', 'entity_id', 'source_entity_id'))
        if subject:
            entity = subject
            for link in links:
                link['subject_id'] = subject
        target = _entity_id(_first(data, 'object_id', 'target_id', 'owner_id', 'parent_id', 'owner', 'parent'))
        target = target or _entity_id(data.get('object'))
        predicate = _first(data, 'predicate', 'relationship', 'relation', 'property')
        if not predicate and _first(data, 'owner_id', 'owner'):
            predicate = 'owned_by'
        elif not predicate and _first(data, 'parent_id', 'parent'):
            predicate = 'parent_organization'
        if target and predicate:
            links.append({'kind': RELATION_PROPERTIES.get(predicate, predicate),
                          'subject_id': entity, 'target_id': target,
                          'target_domain': 'suppliers', 'canonical_link_status': 'unresolved'})
        if not subject or not links:
            raise MalformedSupplierRow('ownership_requires_explicit_subject_and_relation')
    if not entity and not name and not legal and kind != 'price_observation':
        raise MalformedSupplierRow('missing_entity_identity')
    # Ordinal/pointer preserves repeated native IDs instead of silently collapsing
    # different retained occurrences. DomainStore fingerprints provide idempotency.
    record_id = hashlib.sha256(_json([source_key(source), pointer]).encode()).hexdigest()
    record = {'id': record_id, 'entity_id': entity, 'name': name, 'legal_name': legal,
            'website': website, 'address': address, 'country': country,
            'country_basis': _first(data, 'countryBasis', 'country_basis'),
            'provider': provider, 'type': kind, 'source_kind': row.get('kind'),
            'roles': data.get('roles', []), 'relations': links,
            'provenance': {'source_key': source_key(source), 'source_pointer': pointer,
                           'license': source.get('license') or provenance.get('license'),
                           'source_provenance': provenance,
                           'canonical_mapping_status': 'unresolved'},
            'source_payload': payload}
    if kind == 'price_observation':
        record.update(observed_price=_first(data, 'price', 'amount', 'value'),
                      currency=_first(data, 'currency'),
                      observed_at=_first(data, 'date', 'observed_at', 'observedAt'),
                      observation_status='source_observation_not_live_offer')
    return record


def _summary(source, status='skipped', reason=None):
    result = dict(source_key=source_key(source), status=status,
                  resumed_from=0, completed=False, **{key: 0 for key in COUNTERS})
    if reason:
        result['reason'] = reason
    if status == 'skipped':
        result['skipped'] = 1
    return result


def _skip_reason(source):
    if source.get('restricted') or source.get('disposition') == 'restricted':
        return 'restricted_input'
    if source.get('loaded') or source.get('disposition') in ('existing-loaded', 'already_loaded'):
        return 'already_loaded'
    name = str(source.get('path', '')).lower()
    if (source.get('incomplete') or source.get('complete') is False
            or source.get('disposition') in ('incomplete-hold', 'incomplete', 'partial')
            or name.endswith(('.part', '.partial', '.incomplete', '.download'))):
        return 'incomplete_source'
    if source.get('disposition') == 'skip':
        return 'catalog_skip'
    if _format(source) not in ('json', 'jsonl', 'csv', 'tsv', 'sqlite', 'parquet'):
        return 'unsupported_supplier_format'
    if (_format(source) in ('json', 'jsonl', 'csv', 'tsv') and
            str(source.get('compression') or '').lower() not in ('', 'gz', 'gzip', 'bz2', 'bzip2', 'xz', 'lzma')):
        return 'unsupported_text_compression'
    if _format(source) == 'parquet':
        try:
            import pyarrow.parquet  # Only an already-installed optional reader.
        except ImportError:
            return 'parquet_dependency_unavailable'
    return None


def run_domain(domain, sources, context):
    if domain != 'suppliers':
        raise ValueError('supplier_adapter_domain_mismatch')
    summaries = []
    config = context.config
    maximum = min(MAX_ROW_BYTES, max(1024, int(config.get('max_record_bytes', MAX_ROW_BYTES))))
    for original in sources:
        source = {**original, 'adapter_version': ADAPTER_VERSION}
        skip = _skip_reason(source)
        if skip:
            summaries.append(_summary(source, reason=skip))
            continue
        extra = {'errors': 0, 'skipped': 0}

        def error(exc):
            extra['errors'] += 1
            context.report_error(source, exc)

        def records():
            for row, pointer in _rows(source, maximum, error, context.check_budget):
                context.check_budget()
                if context.cancelled.is_set():
                    raise BudgetExceeded('cancelled')
                try:
                    record = normalize_record(row, source, pointer)
                    if record is None:
                        extra['skipped'] += 1
                    else:
                        yield record
                except (ValueError, TypeError, OverflowError) as exc:
                    error(exc)

        try:
            ingest = getattr(context, 'ingest', context.store.ingest)
            summary = ingest(source, records())
            # The engine persists report_error() counts; simple contexts may not.
            summary['errors'] = max(summary['errors'], extra['errors'])
            summary['skipped'] += extra['skipped']
            summary['read'] += extra['errors'] + extra['skipped']
            if extra['errors']:
                summary['status'] = 'partial'
        except UnsupportedSupplierSource as exc:
            summary = _summary(source, reason=str(exc))
        except BudgetExceeded:
            summary = _summary(source, status='partial', reason='resource_budget')
        except Exception as exc:
            error(exc)
            summary = _summary(source, status='failed', reason='source_error')
            summary['errors'] = extra['errors']
        summaries.append(summary)
    totals = {key: sum(item.get(key, 0) for item in summaries) for key in COUNTERS}
    status = ('no_inputs' if not summaries else
              'partial' if any(x['status'] in ('failed', 'partial')
                               or (x['status'] == 'skipped' and x.get('reason') != 'already_loaded')
                               for x in summaries)
              else 'complete')
    return {'status': status, 'sources': summaries, **totals}
