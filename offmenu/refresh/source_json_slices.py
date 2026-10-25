"""Native-only bounded TEXT blob slices; no paths, writers, acquisition or parser.

An offset is not authority. The caller must independently qualify its exact held
connection, persisted row, operation and current rights before every range read.
The caller owns its read transaction, SQLite progress handler and aggregate VM
budget. This module never installs/replaces a handler or changes SQLite limits.
"""
from dataclasses import dataclass
import codecs
import json
import math
import re
import sqlite3
import time

SCHEMA = 'offmenu-source-json-slice/1'
CHUNK_BYTES = 16384
WIRE_BYTES = 262144
METADATA_BYTES = 8192
SOURCE_VALUE_BYTES = 16 * 1024 * 1024
IDENTITY_COLUMNS = ('rowid', 'reference_record_id', 'source_id', 'release_id',
    'asset_id', 'asset_sha256', 'source_ordinal', 'native_record_id', 'source_pointer',
    'original_language', 'parsed_record_sha256', 'citation_id', 'citation_binding_status',
    'parse_engine_id', 'parse_engine_version', 'processing_status')
_SELECT = ('SELECT ' + ','.join(IDENTITY_COLUMNS) + ',typeof(source_payload_json) '
           'FROM main.retained_reference_record WHERE reference_record_id=?')
_CODES = frozenset(('selection', 'metadata-bound', 'qualification-required',
    'qualification-unavailable', 'qualification-mismatch', 'access-revoked',
    'budget-required', 'budget-unavailable', 'budget-exhausted', 'deadline',
    'offset', 'chunk-bound', 'query-only-required', 'read-transaction-required',
    'connection-mode', 'encoding', 'row-missing', 'row-identity-mismatch',
    'payload-type', 'extent-bound', 'extent-mismatch', 'invalid-utf8',
    'offset-not-utf8-boundary', 'chunk-too-small', 'blob-short-read',
    'sqlite-failure', 'blob-api-unavailable', 'wire-bound', 'internal'))


class SourceJsonSliceError(ValueError):
    def __init__(self, code, *, sqlite_details=None):
        code = code if type(code) is str and code in _CODES else 'internal'
        self.code = 'source-json-slice-' + code
        self.sqlite_details = sqlite_details
        super().__init__(self.code)


def _fail(code):
    raise SourceJsonSliceError(code)


def canonical(value):
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        _fail('selection')


def _plain(value, depth=0, count=None):
    """Bound non-value metadata before canonical copying; no custom containers."""
    count = [0, 0] if count is None else count
    count[0] += 1
    if depth > 8 or count[0] > 4096:
        _fail('metadata-bound')
    kind = type(value)
    if kind in (str, int, bool, float, type(None)):
        if kind is str and len(value) > METADATA_BYTES:
            _fail('metadata-bound')
        count[1] += len(canonical(value)) - 1
    elif kind in (list, dict):
        count[1] += 2 + max(0, len(value) - 1) + (len(value) if kind is dict else 0)
    if count[1] > METADATA_BYTES:
        _fail('metadata-bound')
    if kind is str:
        if len(value) > METADATA_BYTES:
            _fail('metadata-bound')
        return
    if value is None or kind in (int, bool):
        return
    if kind is float and math.isfinite(value):
        return
    if kind is list:
        for child in value:
            _plain(child, depth + 1, count)
        return
    if kind is dict:
        for key, child in value.items():
            if type(key) is not str or len(key) > METADATA_BYTES:
                _fail('metadata-bound')
            _plain(key, depth + 1, count)
            _plain(child, depth + 1, count)
        return
    _fail('selection')


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


class SourceJsonSelection:
    """An immutable native selection, not a permission or HTTP input decoder.

    source_bytes is the independently selected exact extent. The 16MiB ceiling
    only bounds this NEW candidate slice operation; it grants no read admission
    and does not change the existing whole-query/source-payload cap of262144.
    """
    __slots__ = ('_json',)

    def __init__(self, *, record_id, row_identity, binding, source_bytes,
                 source_value_cap=SOURCE_VALUE_BYTES):
        if (type(record_id) is not str or not record_id or type(row_identity) is not dict
                or set(row_identity) != set(IDENTITY_COLUMNS)
                or row_identity.get('reference_record_id') != record_id
                or type(binding) is not dict or not {'store', 'operation', 'rights'} <= set(binding)
                or any(type(binding[name]) is not dict or not binding[name]
                       for name in ('store', 'operation', 'rights'))
                or type(source_value_cap) is not int or not 0 < source_value_cap <= SOURCE_VALUE_BYTES
                or type(source_bytes) is not int or not 0 <= source_bytes <= source_value_cap):
            _fail('selection')
        for name in IDENTITY_COLUMNS:
            value = row_identity[name]
            if name in ('rowid', 'source_ordinal'):
                if type(value) is not int or not 0 < value <= 9007199254740991:
                    _fail('selection')
            elif name in ('native_record_id', 'citation_id') and value is None:
                continue
            elif type(value) is not str or not value:
                _fail('selection')
        if (not _sha(row_identity['asset_sha256']) or not _sha(row_identity['parsed_record_sha256'])
                or not _sha(binding['store'].get('databaseSha256'))
                or not _sha(binding['store'].get('qualificationSha256'))
                or type(binding['store'].get('generationId')) is not str
                or not binding['store']['generationId']
                or not _sha(binding['operation'].get('receiptSha256'))
                or type(binding['operation'].get('operationId')) is not str
                or not binding['operation']['operationId']
                or not _sha(binding['rights'].get('receiptSha256'))
                or binding['rights'].get('state') != 'permitted'):
            _fail('selection')
        metadata = {'recordId': record_id, 'rowIdentity': row_identity, 'binding': binding,
                    'sourceBytes': source_bytes, 'candidateSourceValueCapBytes': source_value_cap}
        _plain(metadata)
        encoded = canonical(metadata)
        if len(encoded) > METADATA_BYTES:
            _fail('metadata-bound')
        object.__setattr__(self, '_json', encoded)

    def __setattr__(self, name, value):
        raise AttributeError('Native selection is immutable.')

    @property
    def metadata(self):
        return json.loads(self._json)


@dataclass(frozen=True)
class QualifiedRead:
    """Returned only by the trusted check after fresh independent qualification.

    The selected connection must already have query_only, a caller-owned read
    transaction and the caller's aggregate <=100000-VM-step/deadline guard.
    This structure does not independently prove any of these external facts.
    """
    connection: sqlite3.Connection
    selection: SourceJsonSelection


def _sqlite_failure(error, stage):
    name = getattr(error, 'sqlite_errorname', None)
    code = getattr(error, 'sqlite_errorcode', None)
    details = {'stage': stage,
               'sqliteErrorCode': code if type(code) is int else None,
               'sqliteErrorName': name if type(name) is str and re.fullmatch('SQLITE_[A-Z0-9_]{1,64}', name) else None}
    raise SourceJsonSliceError('sqlite-failure', sqlite_details=details) from None


def read_source_json_slice(connection, selection, *, offset, qualify, check_budget,
                           deadline, chunk_bytes=CHUNK_BYTES, clock=time.monotonic):
    """One fixed-table, read-only, UTF8-safe range of already admitted TEXT.

    qualify(selection) must freshly return QualifiedRead for this exact held
    connection/context, never echo authority from HTTP. It is called before
    metadata, before opening, immediately before reading, and before release.
    check_budget() is mandatory and owns the host's remaining VM/resource guard;
    the module preserves all existing limits/progress handlers/transactions.
    """
    if not isinstance(connection, sqlite3.Connection) or type(selection) is not SourceJsonSelection:
        _fail('selection')
    if not callable(getattr(connection, 'blobopen', None)):
        _fail('blob-api-unavailable')
    if not callable(qualify):
        _fail('qualification-required')
    if not callable(check_budget):
        _fail('budget-required')
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        _fail('deadline')
    if type(chunk_bytes) is not int or not 0 < chunk_bytes <= CHUNK_BYTES:
        _fail('chunk-bound')
    metadata = selection.metadata
    if type(offset) is not int or not 0 <= offset <= metadata['sourceBytes']:
        _fail('offset')
    stop = min(deadline, clock() + 5)

    def guard():
        if clock() >= stop:
            _fail('deadline')
        try:
            if check_budget() is not None:
                _fail('budget-exhausted')
        except SourceJsonSliceError:
            raise
        except Exception:
            _fail('budget-unavailable')
        if clock() >= stop:
            _fail('deadline')

    def fresh():
        guard()
        try:
            current = qualify(selection)
        except SourceJsonSliceError:
            raise
        except Exception:
            _fail('qualification-unavailable')
        guard()
        if (type(current) is not QualifiedRead or current.connection is not connection
                or type(current.selection) is not SourceJsonSelection
                or current.selection._json != selection._json):
            _fail('qualification-mismatch')

    def query(sql, parameters=(), stage='metadata'):
        guard()
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.row_factory = None
            row = cursor.execute(sql, parameters).fetchone()
        except sqlite3.Error as error:
            _sqlite_failure(error, stage)
        finally:
            if cursor is not None:
                cursor.close()
        guard()
        return row

    def mode():
        if query('PRAGMA query_only', stage='query-only') != (1,):
            _fail('query-only-required')
        if not connection.in_transaction:
            _fail('read-transaction-required')
        if connection.text_factory is not str:
            _fail('connection-mode')
        if query('PRAGMA main.encoding', stage='encoding') != ('UTF-8',):
            _fail('encoding')

    fresh()
    mode()
    row = query(_SELECT, (metadata['recordId'],))
    if row is None:
        _fail('row-missing')
    expected = tuple(metadata['rowIdentity'][name] for name in IDENTITY_COLUMNS)
    if row[:-1] != expected:
        _fail('row-identity-mismatch')
    if row[-1] != 'text':
        _fail('payload-type')
    fresh()
    mode()
    blob = None
    try:
        try:
            blob = connection.blobopen('retained_reference_record', 'source_payload_json',
                metadata['rowIdentity']['rowid'], readonly=True, name='main')
            extent = len(blob)
        except sqlite3.Error as error:
            _sqlite_failure(error, 'blob-open')
        guard()
        if extent > metadata['candidateSourceValueCapBytes']:
            _fail('extent-bound')
        if extent != metadata['sourceBytes']:
            _fail('extent-mismatch')
        fresh()
        mode()
        size = min(chunk_bytes, extent - offset)
        try:
            blob.seek(offset)
            raw = blob.read(size) if size else b''
        except sqlite3.Error as error:
            _sqlite_failure(error, 'blob-read')
        guard()
        if len(raw) != size:
            _fail('blob-short-read')
        if offset and raw and 0x80 <= raw[0] <= 0xBF:
            _fail('offset-not-utf8-boundary')
        decoder = codecs.getincrementaldecoder('utf-8')('strict')
        try:
            text = decoder.decode(raw, final=offset + size == extent)
            tail, _ = decoder.getstate()
        except UnicodeError:
            _fail('invalid-utf8')
        consumed = len(raw) - len(tail)
        if size and not consumed:
            _fail('chunk-too-small')
        end = offset + consumed
        fresh()
        mode()
        output = {'schema': SCHEMA, 'state': 'slice-available',
            'scope': 'selected-record-json-byte-slice', 'selection': metadata,
            'encoding': 'utf-8', 'offsetUnit': 'utf-8-bytes', 'offsetBytes': offset,
            'endOffsetBytes': end, 'extentBytes': extent, 'jsonText': text,
            'hasMore': end < extent, 'nextOffsetBytes': end if end < extent else None,
            'valueCompleteInThisSlice': offset == 0 and end == extent}
        if len(canonical(output)) > WIRE_BYTES:
            _fail('wire-bound')
        guard()
        return output
    finally:
        if blob is not None:
            try:
                blob.close()
            except sqlite3.Error as error:
                _sqlite_failure(error, 'blob-close')


def error_envelope(error):
    if type(error) is not SourceJsonSliceError:
        _fail('internal')
    reason = error.code if error.code in {'source-json-slice-' + code for code in _CODES} else 'source-json-slice-internal'
    result = {'schema': SCHEMA, 'state': 'unavailable', 'reasonCode': reason,
              'nextOffsetBytes': None, 'valueCompleteInThisSlice': False}
    if error.sqlite_details is not None:
        details = error.sqlite_details
        if (type(details) is dict and set(details) == {'stage', 'sqliteErrorCode', 'sqliteErrorName'}
                and details['stage'] in ('metadata', 'query-only', 'encoding', 'blob-open', 'blob-read', 'blob-close')
                and (details['sqliteErrorCode'] is None or type(details['sqliteErrorCode']) is int)
                and (details['sqliteErrorName'] is None or type(details['sqliteErrorName']) is str
                     and re.fullmatch('SQLITE_[A-Z0-9_]{1,64}', details['sqliteErrorName']))):
            result['sqlite'] = details.copy()
    return result
