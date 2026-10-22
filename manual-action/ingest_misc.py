"""Retained dietary facts and citation metadata adapters; no network or advice.

Contracts inspected at maldous/offmenu commit 8652b312ce7989c5e4f2d49ae765d5d8daf5841d:
collect-fineli-reference-tables.py, align-reference-common.py,
align-national-common.py and corpus/common-source-mappings.json. Native
``[record]`` and curated ``[key, [record, ...]]`` JSONL packets are supported.
Original values/units/qualifiers remain untouched. This additive index does not
qualify food suitability, equate foods, convert units, or bind application DBs.

Counters are intentionally distinct: source_files counts attempted files;
documents counts parsed JSON containers/JSONL lines/table rows; records counts
emitted domain facts. Unsupported records/sources never count as loaded facts.
Citation rows contain only reference metadata, never copies of dataset bodies.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

from ingest_api import BudgetExceeded, SourceChanged, source_key

ADAPTER_VERSION = 'offmenu-retained-misc/1'
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024


class UnsupportedSource(ValueError):
    pass


class DuplicateField(ValueError):
    pass


class DocumentTooLarge(ValueError):
    pass


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateField('duplicate_object_field')
        value[key] = item
    return value


def _constant(value):
    raise ValueError('nonfinite_number')


class SourceFloat(float):
    """JSON number plus its exact original token; never a unit conversion."""
    def __new__(cls, value):
        result = super().__new__(cls, value)
        result.lexeme = value
        return result


def _float(value):
    result = SourceFloat(value)
    if not math.isfinite(result):
        raise ValueError('nonfinite_number')
    return result


DECODER = json.JSONDecoder(object_pairs_hook=_object, parse_constant=_constant,
                           parse_float=_float)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _numeric_lexemes(value, prefix=''):
    """Retain decimal/exponent notation separately from the numeric index."""
    if isinstance(value, SourceFloat):
        yield prefix or '/', value.lexeme
    elif isinstance(value, dict):
        for key, item in value.items():
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            yield from _numeric_lexemes(item, prefix + '/' + escaped)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _numeric_lexemes(item, prefix + '/' + str(index))


def _canonical(key):
    return re.sub(r'[^a-z0-9]', '', str(key).casefold())


def _config(context):
    return getattr(context, 'config', {}) or {}


def _check(context):
    context.check_budget()
    cancelled = getattr(context, 'cancelled', None)
    if cancelled is not None and cancelled.is_set():
        raise BudgetExceeded('cancelled')


def _error(context, source, stats, exc):
    stats['parse_errors'] += 1
    context.report_error(source, exc)


def _format(source, path):
    value = str(source.get('format') or '').casefold().replace('.', '').replace('-', '')
    aliases = {'ndjson': 'jsonl', 'jsonlgz': 'jsonl', 'jsongz': 'json',
               'csvgz': 'csv', 'tsvgz': 'tsv', 'sqlite3': 'sqlite', 'db': 'sqlite',
               'pdfcache': 'json', 'parsedpdfcache': 'json', 'parsedpdf': 'json'}
    value = aliases.get(value, value)
    if value in {'jsonl', 'json', 'csv', 'tsv', 'sqlite'}:
        return value
    name = path.name.casefold()
    if name.endswith('.gz'):
        name = name[:-3]
    for suffix, kind in [('.jsonl', 'jsonl'), ('.ndjson', 'jsonl'), ('.json', 'json'),
                         ('.csv', 'csv'), ('.tsv', 'tsv'), ('.sqlite3', 'sqlite'),
                         ('.sqlite', 'sqlite'), ('.db', 'sqlite')]:
        if name.endswith(suffix):
            return kind
    raise UnsupportedSource('unsupported_retained_format')


def _stat_identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


@contextlib.contextmanager
def _binary(path):
    """Descriptor-anchored regular file open; reject every symlink component."""
    path = Path(os.path.abspath(path))
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('source_not_regular_file')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            yield stream
            after = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            if (_stat_identity(after) != _stat_identity(before) or
                    _stat_identity(os.fstat(stream.fileno())) != _stat_identity(before)):
                raise SourceChanged('source_changed_during_read')
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


@contextlib.contextmanager
def _text(path, source):
    # Only the catalog-selected local file is opened. No external references or
    # manifest child paths are followed and no archive/code execution occurs.
    encoding = source.get('encoding') or 'utf-8-sig'
    with _binary(path) as original:
        if path.name.casefold().endswith('.gz') or source.get('compression') == 'gz':
            with gzip.GzipFile(fileobj=original, mode='rb') as raw:
                with io.TextIOWrapper(raw, encoding=encoding, errors='strict', newline='') as stream:
                    yield stream
        else:
            stream = io.TextIOWrapper(original, encoding=encoding, errors='strict', newline='')
            try:
                yield stream
            finally:
                # The descriptor remains open for the source-change check.
                stream.detach()


def _json_documents(stream, context, limit):
    """Bounded standard-library reader, streaming top-level JSON array entries."""
    buffer, eof = '', False

    def read_more():
        nonlocal buffer, eof
        _check(context)
        chunk = stream.read(65536)
        if not chunk:
            eof = True
        else:
            buffer += chunk
        if len(buffer.encode('utf-8')) > limit:
            raise DocumentTooLarge('json_document_size_cap')

    def whitespace():
        nonlocal buffer
        while True:
            buffer = buffer.lstrip()
            if buffer or eof:
                return
            read_more()

    def value():
        nonlocal buffer
        while True:
            try:
                result, end = DECODER.raw_decode(buffer)
                # A scalar number can end at a chunk boundary mid-number.
                if end == len(buffer) and not eof and isinstance(result, (int, float)):
                    read_more()
                    continue
                buffer = buffer[end:]
                return result
            except json.JSONDecodeError:
                if eof:
                    raise
                read_more()

    whitespace()
    if not buffer:
        raise ValueError('empty_json_document')
    if buffer[0] != '[':
        yield value()
        whitespace()
        if buffer:
            raise ValueError('trailing_json_content')
        return
    buffer = buffer[1:]
    whitespace()
    if buffer.startswith(']'):
        buffer = buffer[1:]
    else:
        while True:
            whitespace()
            yield value()
            whitespace()
            if buffer.startswith(']'):
                buffer = buffer[1:]
                break
            if not buffer.startswith(','):
                raise ValueError('invalid_json_array_separator')
            buffer = buffer[1:]
    whitespace()
    if buffer:
        raise ValueError('trailing_json_content')


def _expand(value, depth=0, on_error=None):
    """Unwrap admitted native/curated packets, not arbitrary nested data trees."""
    if depth > 8:
        raise ValueError('packet_nesting_limit')
    if isinstance(value, dict):
        # A data-bearing native record is one record, not its nutrient children.
        if 'kind' in value or value.get('schemaVersion') == 'offmenu-common/1' or 'provenance' in value:
            yield value
        elif isinstance(value.get('records'), list):
            yield from _expand(value['records'], depth + 1, on_error)
        else:
            yield value
    elif isinstance(value, list):
        if len(value) == 2 and isinstance(value[0], (str, int)) and isinstance(value[1], list):
            yield from _expand(value[1], depth + 1, on_error)
        else:
            for item in value:
                try:
                    yield from _expand(item, depth + 1, on_error)
                except (ValueError, TypeError, RecursionError) as exc:
                    if on_error is None:
                        raise
                    on_error(exc)
    else:
        raise ValueError('source_record_not_object')


def _sql_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


def _sqlite_rows(path, source, context, stats):
    with _binary(path):
        yield from _sqlite_rows_checked(path, source, context, stats)


def _sqlite_rows_checked(path, source, context, stats):
    # Read-only URI and query_only prevent writes even if the caller supplied a
    # production DB. Views/triggers are not evaluated; arbitrary SQL is rejected.
    uri = 'file:' + quote(str(path.resolve()), safe='/') + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        budget_error = []

        def budget_progress():
            try:
                _check(context)
                return 0
            except BudgetExceeded as exc:
                budget_error.append(exc)
                return 1

        db.set_progress_handler(budget_progress, 10000)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        requested = source.get('tables') or ([source['table']] if source.get('table') else None)
        if requested is not None:
            if not isinstance(requested, (list, tuple)) or not all(isinstance(x, str) for x in requested):
                raise ValueError('invalid_table_selection')
            if any(name not in tables for name in requested):
                raise ValueError('table_missing')
            tables = sorted(set(requested))
        for table in tables:
            _check(context)
            columns = [r[1] for r in db.execute('PRAGMA table_info(' + _sql_identifier(table) + ')')]
            # A rowid/primary-key order is deterministic; virtual tables are not
            # queried because extension modules may involve external resources.
            ddl = db.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0] or ''
            if re.match(r'\s*CREATE\s+VIRTUAL\s+TABLE', ddl, re.I):
                stats['unsupported_tables'] += 1
                continue
            pk = [r[1] for r in sorted(db.execute('PRAGMA table_info(' + _sql_identifier(table) + ')'), key=lambda x: x[5]) if r[5]]
            order = ','.join(_sql_identifier(x) for x in pk) if pk else 'rowid'
            try:
                rows = db.execute('SELECT * FROM ' + _sql_identifier(table) + ' ORDER BY ' + order)
                for values in rows:
                    _check(context)
                    stats['documents'] += 1
                    row = dict(zip(columns, values))
                    if any(isinstance(v, bytes) for v in values):
                        _error(context, source, stats, UnsupportedSource('binary_table_row'))
                        continue
                    # Existing OffMenu stores commonly retain the original JSON.
                    payload_key = next((k for k in ('payload_json', 'record_json', 'json', 'data_json') if isinstance(row.get(k), str)), None)
                    if payload_key:
                        try:
                            payload = DECODER.decode(row[payload_key])
                            for item in _expand(payload, on_error=lambda exc: _error(context, source, stats, exc)):
                                yield item, table
                        except (ValueError, TypeError, RecursionError) as exc:
                            _error(context, source, stats, exc)
                    else:
                        yield row, table
            except sqlite3.Error as exc:
                if budget_error:
                    raise budget_error[-1]
                _error(context, source, stats, exc)


def iter_source_rows(source, context, stats):
    path = Path(source['path'])
    kind = _format(source, path)
    limit = int(_config(context).get('max_document_bytes', MAX_DOCUMENT_BYTES))
    if kind == 'sqlite':
        yield from _sqlite_rows(path, source, context, stats)
        return
    with _text(path, source) as stream:
        if kind == 'jsonl':
            while True:
                _check(context)
                line = stream.readline(limit + 1)
                if not line:
                    break
                if len(line.encode('utf-8')) > limit:
                    # Drain just this oversized line; subsequent records survive.
                    while line and not line.endswith('\n'):
                        _check(context)
                        line = stream.readline(65536)
                    _error(context, source, stats, DocumentTooLarge('jsonl_document_size_cap'))
                    continue
                if not line.strip():
                    continue
                stats['documents'] += 1
                try:
                    yield from ((row, None) for row in _expand(DECODER.decode(line), on_error=lambda exc: _error(context, source, stats, exc)))
                except (ValueError, TypeError, RecursionError) as exc:
                    _error(context, source, stats, exc)
        elif kind == 'json':
            for document in _json_documents(stream, context, limit):
                stats['documents'] += 1
                try:
                    yield from ((row, None) for row in _expand(document, on_error=lambda exc: _error(context, source, stats, exc)))
                except (ValueError, TypeError, RecursionError) as exc:
                    _error(context, source, stats, exc)
        else:
            delimiter = source.get('delimiter') or ('\t' if kind == 'tsv' else None)
            if delimiter is None:
                sample = stream.read(65536)
                stream.seek(0)
                try:
                    delimiter = csv.Sniffer().sniff(sample, delimiters=',;\t|').delimiter
                except csv.Error:
                    delimiter = ','
            csv.field_size_limit(max(csv.field_size_limit(), limit))
            if delimiter not in {',', '\t', ';', '|'}:
                raise UnsupportedSource('unsupported_delimiter')
            reader = csv.reader(stream, delimiter=delimiter, strict=True)
            headers = next(reader, None)
            if not headers or any(not name for name in headers):
                raise ValueError('missing_table_headers')
            # Never silently overwrite repeated unit/value columns.
            if len(set(headers)) != len(headers):
                raise DuplicateField('duplicate_table_header')
            for values in reader:
                _check(context)
                if not values:
                    continue
                stats['documents'] += 1
                if len(values) != len(headers):
                    _error(context, source, stats, ValueError('table_column_count'))
                    continue
                yield dict(zip(headers, values)), str(source.get('table') or path.stem)


_DIET_KINDS = {'nutrientprofile', 'foodcompositionobservation', 'nutrientdefinition',
               'dietaryguideline', 'dietaryreference', 'allergenmapping',
               'dietflagassertion', 'dietarytype', 'metricbasisdefinition'}
_PROVIDERS = {'afcd', 'ciqual', 'cofid', 'germany-bls', 'matvaretabellen', 'frida',
              'fineli', 'foodfiles', 'sweden-food', 'cnf', 'mext', 'usda',
              'usda-files', 'fooddata-central', 'opennutrition', 'dietary-guidelines'}


def _dietary_kind(row, source, table=None):
    kind = _canonical(row.get('kind') or row.get('type') or '')
    if kind.startswith('urnoffmenutype'):
        kind = kind[len('urnoffmenutype'):]
    data = row.get('data') if isinstance(row.get('data'), dict) else row
    provenance = row.get('provenance') if isinstance(row.get('provenance'), dict) else {}
    provider = str(provenance.get('sourceId') or source.get('provider') or '').casefold()
    if kind in _DIET_KINDS:
        return kind
    if kind == 'sourceassertion' and (
            provider == 'dietary-guidelines' or data.get('predicate') in {'source-diet-tag', 'allergen', 'contains-allergen'}
            or any(k in data for k in ('sourceFoodId', 'allergenCode', 'dietCode', 'referenceType'))):
        return 'source_assertion'
    if row.get('schemaVersion') == 'offmenu-common/1':
        resources = row.get('resources') or []
        if isinstance(resources, list) and any(isinstance(r, dict) and _canonical(str(r.get('type', '')).rsplit(':', 1)[-1]) in _DIET_KINDS for r in resources):
            return 'common_dietary_packet'
        # Guideline graph packets use SourceAssertion, not an invented diet rule.
        if provider == 'dietary-guidelines' or any(isinstance(c, dict) and c.get('sourceId') == 'dietary-guidelines' for c in row.get('citations', []) if isinstance(row.get('citations'), list)):
            return 'guideline_reference_packet'
    keys = {_canonical(k) for k in data}
    if ('nutrients' in keys or 'foodnutrients' in keys or 'nutriments' in keys) and keys.intersection({'foodname', 'description', 'name', 'fdcid', 'foodid', 'code'}):
        return 'nutrition_reference'
    signatures = [({'foodid', 'specdiet'}, 'source_diet_flag'),
                  ({'fdcid', 'nutrientid', 'amount'}, 'usda_nutrient_observation'),
                  ({'foodid', 'nutrientid', 'nutrientvalue'}, 'nutrient_observation'),
                  ({'foodid', 'nutrient', 'value'}, 'nutrient_observation'),
                  ({'nutrient', 'value', 'unit'}, 'nutrient_observation'),
                  ({'nutrientid', 'unitname', 'name'}, 'nutrient_definition'),
                  ({'foodid', 'allergen'}, 'source_allergen_mapping'),
                  ({'ingredient', 'allergen'}, 'source_allergen_mapping'),
                  ({'foodid', 'dietcode'}, 'source_diet_flag')]
    for signature, label in signatures:
        if signature <= keys:
            return label
    if provider == 'fineli' and {'thscode', 'descript'} <= keys and 'specdiet' in str(table or '').casefold():
        return 'diet_flag_definition'
    # Known providers' wide composition tables retain all supplied columns;
    # units inside labels remain labels and no numbers/units are synthesized.
    if provider in _PROVIDERS and keys.intersection({'foodid', 'foodcode', 'foodname', 'fooddescription', 'fdcid'}) and any(re.search(r'(energy|protein|nutrient|carbohydrat|lipid|vitamin|fibre|fiber)', k) for k in keys):
        return 'provider_composition_table'
    return None


def _identifier(domain, source, logical, facts):
    # Content participates so conflicting facts under the same provider identity
    # coexist rather than overwriting each other. Exact duplicate rows collapse.
    key = _json([domain, source_key(source), logical, facts])
    return 'urn:offmenu:retained:' + domain + ':' + hashlib.sha256(key.encode()).hexdigest()


def _dietary(row, source, table):
    kind = _dietary_kind(row, source, table)
    if not kind:
        return None
    data = row.get('data') if isinstance(row.get('data'), dict) else row
    logical = row.get('id', data.get('food_id', data.get('FOODID', data.get('fdc_id'))))
    lexemes = dict(_numeric_lexemes(row))
    return {'id': _identifier('dietary', source, [table, logical], [row, lexemes]),
            'record_type': kind, 'source_record_id': logical,
            'source_table': table, 'source_key': source_key(source),
            'fact_status': 'source_asserted_not_independently_qualified',
            'automatic_diet_qualification': False,
            'source_fields': row, 'source_numeric_lexemes': lexemes}


# Explicit metadata field projection: text bodies, nutrients, private personal
# fields and opaque nested payloads can never enter the citation DB by accident.
_REFERENCE_FIELDS = {
    'id', 'sourceId', 'source_id', 'recordId', 'record_id', 'originalRecordId',
    'title', 'name', 'url', 'sourceUrl', 'source_url', 'originalUrl', 'downloadUrl',
    'download_url', 'referenceUrl', 'directoryUrl', 'historyUrl', 'license',
    'licence', 'licenseUrl', 'license_url', 'rightsEvidenceUrl', 'attribution',
    'fetchedAt', 'downloadedAt', 'downloaded_at', 'downloadTime', 'downloaded', 'acquiredAt', 'retrievedAt',
    'completedAt', 'sourceDate', 'publishedAt', 'releaseId', 'revisionId',
    'sha256', 'archiveSha256', 'contentSha256', 'sourceTextSha256', 'checksum',
    'key', 'path', 'file', 'filename', 'bytes', 'size', 'format', 'mediaType',
    'schemaVersion', 'schema', 'provider', 'sourcePath', 'visibility', 'status',
    'publication', 'rights', 'copyright', 'version', 'language', 'country',
    'referenceType', 'contentPermission', 'qualificationStatus', 'reviewStatus',
}
_REFERENCE_NORMALIZED = {_canonical(k) for k in _REFERENCE_FIELDS}
_IDENTITY_KEYS = {_canonical(k) for k in (
    'sourceId', 'source_id', 'url', 'sourceUrl', 'originalUrl', 'referenceUrl',
    'downloadUrl', 'sha256', 'archiveSha256', 'contentSha256', 'license', 'licence',
    'attribution', 'sourcePath', 'releaseId')}
_CITATION_CHILDREN = ('sources', 'files', 'sourceFiles', 'source_files', 'documents', 'artifacts', 'downloads',
                      'acquisitions', 'references', 'citations', 'entries', 'items')


def _reference(row):
    projected = {}
    for key, value in row.items():
        if _canonical(key) in _REFERENCE_NORMALIZED and (
                value is None or isinstance(value, (str, bool, int, float))):
            projected[key] = value
        elif key == 'scope' and isinstance(value, dict):
            projected[key] = {k: v for k, v in value.items() if k in {'visibility', 'reuseScope'} and (v is None or isinstance(v, (str, bool, int, float)))}
    return projected


def _citation_rows(row, inherited=None, location='root', depth=0):
    if depth > 12:
        raise ValueError('citation_nesting_limit')
    if not isinstance(row, dict):
        return
    own = _reference(row)
    parent = dict(inherited or {})
    # Parent provenance is kept distinct; a child digest never inherits the
    # parent's digest as though it were a checksum of the child file.
    if own and (set(map(_canonical, own)) & _IDENTITY_KEYS or
                (inherited and any(k in own for k in ('key', 'file', 'filename', 'path', 'id', 'title', 'name')))):
        yield own, parent, location
    for child_key in ('provenance', 'source', 'metadata'):
        child = row.get(child_key)
        if isinstance(child, dict):
            yield from _citation_rows(child, own or parent, location + '.' + child_key, depth + 1)
    # Metadata from native records is useful, but never recurse into their data
    # body except explicitly named references/citations.
    if isinstance(row.get('data'), dict):
        data = row['data']
        if any(k in data for k in ('referenceUrl', 'directoryUrl')):
            yield from _citation_rows(data, own or parent, location + '.data', depth + 1)
    for key in _CITATION_CHILDREN:
        child = row.get(key)
        if isinstance(child, list):
            for index, item in enumerate(child):
                yield from _citation_rows(item, own or parent, location + '.' + key + '[' + str(index) + ']', depth + 1)
        elif isinstance(child, dict):
            for name, item in sorted(child.items()):
                if isinstance(item, dict):
                    # Named catalog sources carry their source identity in key.
                    field = 'sourceId' if key == 'sources' else 'key'
                    yield from _citation_rows({field: name, **item}, own or parent, location + '.' + key + '.' + name, depth + 1)
                elif isinstance(item, str) and re.fullmatch(r'[a-fA-F0-9]{64}', item):
                    yield {'key': name, 'sha256': item}, own or parent, location + '.' + key + '.' + name


def _citations(row, source, table):
    for reference, parent, location in _citation_rows(row):
        logical = reference.get('id', reference.get('sourceId', reference.get('key')))
        facts = {'reference': reference, 'parent_reference': parent}
        facts['source_numeric_lexemes'] = dict(_numeric_lexemes(facts))
        yield {'id': _identifier('citations', source, [table, logical], facts),
               'record_type': 'source_citation', 'source_key': source_key(source),
               'source_table': table, 'source_record_id': logical,
               # Keep the structural location as evidence, not identity: exact
               # duplicated metadata at different line positions deduplicates.
               **facts}


def _summary(source, **extra):
    result = dict(source_key=source_key(source), status='skipped', read=0,
                  written=0, unchanged=0, errors=0, skipped=0, completed=False)
    result.update(extra)
    return result


def run_domain(domain, sources, context):
    """Ingest every independent retained source despite individual failures."""
    if domain not in {'dietary', 'citations'}:
        raise ValueError('unsupported_misc_domain')
    results = []
    totals = {k: 0 for k in ('read', 'written', 'unchanged', 'errors', 'skipped',
                             'source_files', 'documents', 'records',
                             'unsupported_sources', 'unsupported_records')}
    for original in sources:
        _check(context)
        source = dict(original, adapter_version=ADAPTER_VERSION)
        totals['source_files'] += 1
        stats = dict(documents=0, records=0, parse_errors=0,
                     unsupported_records=0, unsupported_tables=0)
        if source.get('restricted') or source.get('loaded') or source.get('incomplete') or source.get('disposition') in {'restricted', 'skip', 'existing-loaded', 'already_loaded', 'restricted-held', 'blocked', 'existing-store', 'incomplete-hold', 'duplicate', 'documentation', 'excluded', 'historical-demo'}:
            result = _summary(source, skipped=1, reason='catalog_skip')
        else:
            try:
                _format(source, Path(source['path']))

                def records():
                    for row, table in iter_source_rows(source, context, stats):
                        _check(context)
                        try:
                            matched = [_dietary(row, source, table)] if domain == 'dietary' else list(_citations(row, source, table))
                            matched = [r for r in matched if r is not None]
                            if not matched:
                                stats['unsupported_records'] += 1
                            for record in matched:
                                stats['records'] += 1
                                yield record
                        except (ValueError, TypeError, RecursionError) as exc:
                            _error(context, source, stats, exc)

                ingest = getattr(context, 'ingest', None) or context.store.ingest
                result = ingest(source, records())
                if stats['parse_errors']:
                    # Context persists parser errors with this source version.
                    # Do not count those same errors twice in the adapter summary.
                    result['errors'] = max(result.get('errors', 0), stats['parse_errors'])
                    result.update(status='partial' if result.get('written') or result.get('resumed_from') else 'failed')
                if not stats['records'] and not result.get('already_complete') and not result.get('errors') and result.get('status') != 'partial':
                    result.update(status='skipped', skipped=result.get('skipped', 0) + 1, reason='no_recognized_records', completed=False)
                    totals['unsupported_sources'] += 1
            except BudgetExceeded:
                raise
            except UnsupportedSource as exc:
                result = _summary(source, skipped=1, reason='unsupported_source', error_class=type(exc).__name__)
                totals['unsupported_sources'] += 1
            except Exception as exc:
                context.report_error(source, exc)
                result = _summary(source, status='failed', errors=1, error_class=type(exc).__name__)
        result.update(documents=stats['documents'], records=stats['records'],
                      unsupported_records=stats['unsupported_records'],
                      unsupported_tables=stats['unsupported_tables'])
        for key in ('read', 'written', 'unchanged', 'errors', 'skipped'):
            totals[key] += result.get(key, 0)
        for key in ('documents', 'records', 'unsupported_records'):
            totals[key] += stats[key]
        results.append(result)
        context.progress(source_files=totals['source_files'], documents=totals['documents'],
                         records=totals['records'], errors=totals['errors'])
    status = 'partial' if totals['errors'] or any(r.get('status') == 'partial' for r in results) else 'complete'
    if not results or (totals['written'] == totals['unchanged'] == 0 and all(r.get('status') == 'skipped' for r in results)):
        status = 'skipped'
    return {'domain': domain, 'status': status, 'sources': results, **totals}
