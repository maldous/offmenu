"""Closed native source-JSON-slice operation; no mount or authority constructor.

The native owner supplies the held connection, immutable selection and three
real callbacks. qualify(selection) freshly checks that exact connection and
current principal/account/context/generation, operation, privacy and rights.
check_budget() owns the caller's aggregate <=100000-VM-step budget and returns
None on success. deadline() supplies its current absolute monotonic deadline.
No callback, principal, selection, connection, path or SQL comes from request.

Returns canonical UTF-8 JSON plus LF, already bounded to262144 bytes. The caller
must preserve those bytes and freshly qualify its actual transport boundary.
This operation changes no SQLite limits, handlers, transactions or ownership.
"""
import math
import sqlite3
import time

from . import source_json_slices as _slices

SCHEMA = 'offmenu-source-field-operation/1'
_REQUEST_KEYS = frozenset(('selectedRecordId', 'offsetBytes', 'chunkBytes'))
_REQUIRED_KEYS = frozenset(('selectedRecordId', 'offsetBytes'))
_OP_CODES = frozenset(('request', 'request-bound', 'record-mismatch',
                       'deadline-required', 'internal'))


class _Unavailable(ValueError):
    def __init__(self, code):
        self.code = code if code in _OP_CODES else 'internal'
        super().__init__(self.code)


def _error_wire(code, sqlite=None):
    value = {'schema': SCHEMA, 'state': 'unavailable', 'reasonCode': code,
             'nextOffsetBytes': None, 'valueCompleteInThisSlice': False}
    if sqlite is not None:
        value['sqlite'] = sqlite
    return _slices.canonical(value)


def read_source_field_operation(connection, selection, request, *, qualify,
                                check_budget, deadline, clock=time.monotonic):
    """Read one actual bounded slice using trusted native owner callbacks only.

    request is exactly a plain dict containing selectedRecordId, offsetBytes,
    and optionally chunkBytes (default16384). offsetBytes is a UTF8 byte offset,
    never an HMAC FieldReader cursor. Missing real owner callbacks block mounting;
    a generic administrator role or an echo of request flags is not authority.
    """
    try:
        if (not isinstance(connection, sqlite3.Connection)
                or type(selection) is not _slices.SourceJsonSelection):
            raise _slices.SourceJsonSliceError('selection')
        if (type(request) is not dict or not _REQUIRED_KEYS <= request.keys()
                or not request.keys() <= _REQUEST_KEYS
                or type(request['selectedRecordId']) is not str
                or not request['selectedRecordId']):
            raise _Unavailable('request')
        if len(request['selectedRecordId']) > _slices.METADATA_BYTES:
            raise _Unavailable('request-bound')
        offset, chunk = request['offsetBytes'], request.get('chunkBytes', _slices.CHUNK_BYTES)
        if type(offset) is not int or not 0 <= offset <= _slices.SOURCE_VALUE_BYTES:
            raise _slices.SourceJsonSliceError('offset')
        if type(chunk) is not int or not 0 < chunk <= _slices.CHUNK_BYTES:
            raise _slices.SourceJsonSliceError('chunk-bound')
        if len(_slices.canonical(request)) > _slices.METADATA_BYTES:
            raise _Unavailable('request-bound')
        metadata = selection.metadata
        if request['selectedRecordId'] != metadata['recordId']:
            raise _Unavailable('record-mismatch')
        if offset > metadata['sourceBytes']:
            raise _slices.SourceJsonSliceError('offset')
        if not callable(qualify):
            raise _slices.SourceJsonSliceError('qualification-required')
        if not callable(check_budget):
            raise _slices.SourceJsonSliceError('budget-required')
        if not callable(deadline):
            raise _Unavailable('deadline-required')
        expected = _slices.canonical(metadata)

        def native_time():
            try:
                value = clock()
            except Exception:
                raise _slices.SourceJsonSliceError('deadline') from None
            if type(value) not in (int, float) or not math.isfinite(value):
                raise _slices.SourceJsonSliceError('deadline')
            return value

        def native_deadline():
            try:
                value = deadline()
            except Exception:
                raise _slices.SourceJsonSliceError('deadline') from None
            if type(value) not in (int, float) or not math.isfinite(value):
                raise _slices.SourceJsonSliceError('deadline')
            return value

        stop = min(native_time() + 5, native_deadline())

        def guard():
            if native_time() >= min(stop, native_deadline()):
                raise _slices.SourceJsonSliceError('deadline')
            try:
                result = check_budget()
            except _slices.SourceJsonSliceError:
                raise
            except Exception:
                raise _slices.SourceJsonSliceError('budget-unavailable') from None
            if result is not None:
                raise _slices.SourceJsonSliceError('budget-exhausted')
            if native_time() >= min(stop, native_deadline()):
                raise _slices.SourceJsonSliceError('deadline')

        def fresh(candidate):
            guard()
            if candidate is not selection:
                raise _slices.SourceJsonSliceError('qualification-mismatch')
            try:
                current = qualify(candidate)
            except _slices.SourceJsonSliceError:
                raise
            except Exception:
                raise _slices.SourceJsonSliceError('qualification-unavailable') from None
            guard()
            if (type(current) is not _slices.QualifiedRead
                    or current.connection is not connection
                    or type(current.selection) is not _slices.SourceJsonSelection
                    or _slices.canonical(current.selection.metadata) != expected):
                raise _slices.SourceJsonSliceError('qualification-mismatch')
            return current

        fresh(selection)
        value = _slices.read_source_json_slice(connection, selection, offset=offset,
            qualify=fresh, check_budget=guard, deadline=stop, chunk_bytes=chunk, clock=clock)
        wire = _slices.canonical({'schema': SCHEMA, 'state': 'slice-available', 'slice': value})
        if len(wire) > _slices.WIRE_BYTES:
            raise _slices.SourceJsonSliceError('wire-bound')
        # Requalify after encoding: a value prepared before revocation is not released.
        fresh(selection)
        return wire
    except _Unavailable as error:
        return _error_wire('source-field-operation-' + error.code)
    except _slices.SourceJsonSliceError as error:
        try:
            safe = _slices.error_envelope(error)
            return _error_wire(safe['reasonCode'], safe.get('sqlite'))
        except Exception:
            return _error_wire('source-field-operation-internal')
    except Exception:
        return _error_wire('source-field-operation-internal')
