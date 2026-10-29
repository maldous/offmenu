"""Pure paging of an already-permitted field; no store, network or permission API."""
from dataclasses import dataclass, asdict
import base64
import hashlib
import hmac
import json
import math
import re
import time

SCHEMA = 'offmenu-source-field-page/1'
STATES = {'present', 'null', 'missing', 'unknown', 'not-loaded', 'rights-held'}
ERROR_CODES = frozenset(('limits', 'work-bound', 'time-bound', 'snapshot-bound', 'json-value',
    'depth-bound', 'json-key', 'atomic-key-bound', 'cursor-invalid', 'cursor-key', 'delivery',
    'field-state', 'rights-held-value-supplied', 'rights-held-metadata', 'state-value-mismatch',
    'metadata-bound', 'binding', 'cursor-bound', 'cursor-binding-mismatch', 'page-bound',
    'invalid-error', 'presenter-request', 'presenter-binding-mismatch', 'request-bound',
    'node-request', 'internal'))
HELD_METADATA = frozenset(('state', 'value', 'reasonCode', 'fieldPointer', 'sourceFieldState',
    'valueOrigin', 'evidenceSha256', 'language', 'rightsState', 'accessState'))


class FieldPageError(ValueError):
    def __init__(self, code):
        code = code if type(code) is str and code in ERROR_CODES else 'internal'
        self.code = 'field-page-' + code
        super().__init__(self.code)


def fail(code):
    raise FieldPageError(code)


@dataclass(frozen=True)
class Limits:
    page_bytes: int = 16384
    snapshot_bytes: int = 262144
    metadata_bytes: int = 8192
    max_depth: int = 8
    max_nodes: int = 100000
    max_items: int = 32
    max_seconds: float = 5
    cursor_bytes: int = 4096

    def validate(self):
        caps = {'page_bytes': 262144, 'snapshot_bytes': 262144, 'metadata_bytes': 8192,
                'max_depth': 8, 'max_nodes': 100000, 'max_items': 1000, 'cursor_bytes': 4096}
        for name, cap in caps.items():
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= cap:
                fail('limits')
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 5:
            fail('limits')


class Budget:
    def __init__(self, limits, clock):
        self.limits, self.clock = limits, clock
        self.deadline, self.steps, self.bytes = clock() + limits.max_seconds, 0, 0

    def check(self, steps=1):
        self.steps += steps
        if self.steps > self.limits.max_nodes:
            fail('work-bound')
        if self.clock() >= self.deadline:
            fail('time-bound')

    def charge(self, size):
        self.bytes += size
        if self.bytes > self.limits.snapshot_bytes:
            fail('snapshot-bound')


def canonical(value):
    try:
        return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                           separators=(',', ':')) + '\n').encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        fail('json-value')


def clone(value, budget, depth=0):
    budget.check()
    if depth > budget.limits.max_depth:
        fail('depth-bound')
    kind = type(value)
    if kind is str:
        if len(value) > budget.limits.snapshot_bytes:
            fail('snapshot-bound')
        budget.charge(2)
        for start in range(0, len(value), 1024):
            budget.check()
            try:
                encoded = json.dumps(value[start:start + 1024], ensure_ascii=False).encode('utf-8')
            except UnicodeError:
                fail('json-value')
            budget.charge(len(encoded) - 2)
        return value
    if value is None or kind in (bool, int):
        budget.charge(len(canonical(value)) - 1)
        return value
    if kind is float:
        if not math.isfinite(value):
            fail('json-value')
        budget.charge(len(canonical(value)) - 1)
        return value
    if kind is list:
        budget.charge(2 + max(0, len(value) - 1))
        return [clone(item, budget, depth + 1) for item in value]
    if kind is dict:
        budget.charge(2 + len(value) + max(0, len(value) - 1))
        output = {}
        for key, item in value.items():
            if type(key) is not str:
                fail('json-key')
            clone(key, budget, depth)
            if len(key.encode('utf-8')) > 1024:
                fail('atomic-key-bound')
            output[key] = clone(item, budget, depth + 1)
        return output
    fail('json-value')


def value_type(value):
    return {str: 'string', list: 'array', dict: 'object', bool: 'boolean',
            int: 'number', float: 'number', type(None): 'null'}[type(value)]


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def unb64(text):
    try:
        raw = base64.b64decode(text + '=' * (-len(text) % 4), altchars=b'-_', validate=True)
        if b64(raw) != text:
            fail('cursor-invalid')
        return raw
    except (ValueError, UnicodeError):
        fail('cursor-invalid')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('cursor-invalid')
        result[key] = value
    return result


class FieldReader:
    """Host constructs this from qualified values, never directly from HTTP input.

    cursor_key is supplied by the trusted host, not generated or provisioned here.
    A permitted flag/cursor is NOT evidence of source-use rights. All JSON values
    are privately copied and bounded before any page is issued.
    """
    def __init__(self, *, binding, field, delivery, cursor_key, limits=Limits(), clock=time.monotonic):
        if type(limits) is not Limits:
            fail('limits')
        limits.validate()
        if type(cursor_key) is not bytes or not 32 <= len(cursor_key) <= 64:
            fail('cursor-key')
        if type(delivery) is not str or delivery not in ('permitted', 'rights-held') or type(field) is not dict:
            fail('delivery')
        if type(field.get('state')) is not str or field['state'] not in STATES:
            fail('field-state')
        state = field['state']
        held = delivery == 'rights-held' or state == 'rights-held'
        if held and field.get('value') is not None:
            fail('rights-held-value-supplied')
        if held and set(field) - HELD_METADATA:
            # Reject, rather than discard unknown metadata or risk an alternate
            # key carrying a withheld body. Host must supply qualified metadata.
            fail('rights-held-metadata')
        if not held and state == 'present' and ('value' not in field or field['value'] is None):
            fail('state-value-mismatch')
        if state == 'null' and ('value' not in field or field['value'] is not None):
            fail('state-value-mismatch')
        if state not in ('present', 'null') and field.get('value') is not None:
            fail('state-value-mismatch')
        budget = Budget(limits, clock)
        context = clone(binding, budget)
        self._validate_binding(context)
        metadata = clone({key: value for key, value in field.items() if key != 'value'}, budget)
        effective = 'rights-held' if held else state
        metadata_bytes = canonical({'binding': context, 'field': metadata})
        if len(metadata_bytes) > limits.metadata_bytes:
            fail('metadata-bound')
        value = clone(field['value'], budget) if effective == 'present' else None
        snapshot = canonical({'binding': context, 'field': metadata, 'state': effective,
                              'value': value, 'limits': asdict(limits)})
        if len(snapshot) > limits.snapshot_bytes:
            fail('snapshot-bound')
        budget.check()
        self._metadata = metadata_bytes
        self._value, self._state = value, effective
        self._digest = hashlib.sha256(snapshot).hexdigest()
        self._key, self._limits, self._clock = cursor_key, limits, clock

    @staticmethod
    def _validate_binding(binding):
        sha = lambda value: type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None
        if type(binding) is not dict:
            fail('binding')
        ref = binding.get('sourceObservationReference')
        if (type(ref) is not dict or ref.get('schema') != 'offmenu-identifier-observation/2'
                or type(binding.get('sourceBinding')) is not dict or not binding['sourceBinding']
                or not sha(binding.get('revisionSha256'))
                or type(binding.get('fieldPath')) is not str
                or not binding['fieldPath'].startswith('/')
                or re.search(r'~(?![01])', binding['fieldPath'])
                or 'attribution' not in binding):
            fail('binding')
        if (type(binding.get('generation')) is not int or not 0 <= binding['generation'] <= 9007199254740991
                or binding.get('selectionRevision') != ref.get('detailSelectionSha256')):
            fail('binding')
        key = ref.get('observationKey')
        if (not sha(ref.get('databaseSha256'))
                or not sha(ref.get('detailSelectionSha256'))
                or type(key) is not dict or key.get('run_id') != ref.get('runId')
                or not isinstance(ref.get('runId'), str) or not ref['runId']
                or not isinstance(key.get('input_id'), str) or not key['input_id']
                or type(key.get('assertion_id')) is not int or not 0 < key['assertion_id'] <= 9007199254740991
                or type(key.get('record_ordinal')) is not int or not 0 <= key['record_ordinal'] <= 9007199254740991
                or ref.get('namespace') not in ('barcode', 'USDA-FDC')
                or type(ref.get('sourceId')) is not str or not ref['sourceId']
                or any(type(ref.get(name)) is not str or not ref[name]
                       for name in ('originalLexicalValue', 'sourceLexicalValue'))
                or any(name not in ref or ref[name] is not None and type(ref[name]) is not str
                       for name in ('releaseId', 'sourceRecordId'))):
            fail('binding')

    def _cursor(self, path, offset, mode='node'):
        payload = canonical({'v': 1, 'snapshot': self._digest, 'path': path, 'offset': offset, 'mode': mode})
        token = b64(payload) + '.' + b64(hmac.digest(self._key, payload, 'sha256'))
        if len(token) > self._limits.cursor_bytes:
            fail('cursor-bound')
        return token

    def _decode(self, cursor, mode='node'):
        if type(cursor) is not str or len(cursor) > self._limits.cursor_bytes:
            fail('cursor-invalid')
        try:
            encoded, signature = cursor.split('.')
            payload, signature = unb64(encoded), unb64(signature)
            if not hmac.compare_digest(signature, hmac.digest(self._key, payload, 'sha256')):
                fail('cursor-invalid')
            state = json.loads(payload, object_pairs_hook=unique_object)
        except (ValueError, TypeError, UnicodeError):
            fail('cursor-invalid')
        if (type(state) is not dict or set(state) != {'v', 'snapshot', 'path', 'offset', 'mode'}
                or type(state['v']) is not int or state['v'] != 1
                or state['mode'] != mode
                or state['snapshot'] != self._digest or type(state['path']) is not list
                or len(state['path']) > self._limits.max_depth
                or type(state['offset']) is not int or state['offset'] < 0):
            fail('cursor-binding-mismatch')
        return state['path'], state['offset']

    def read(self, cursor=None, *, _budget=None):
        budget = _budget if _budget is not None else Budget(self._limits, self._clock)
        path, offset = ([], 0) if cursor is None else self._decode(cursor)
        return self._read_node(path, offset, cursor, budget)

    def _read_node(self, path, offset, cursor, budget, advance=None, envelope=None):
        value = self._value
        for token in path:
            budget.check()
            if type(value) is list and type(token) is int and 0 <= token < len(value):
                value = value[token]
            elif type(value) is dict and type(token) is str and token in value:
                value = value[token]
            else:
                fail('cursor-binding-mismatch')
        base = json.loads(self._metadata)
        base.update(schema=SCHEMA, snapshotSha256=self._digest, path=path,
                    requestCursor=cursor, state=self._state if not path else ('null' if value is None else 'present'),
                    scope='node-page-only')

        def finish(content, next_offset=None, complete=False):
            next_cursor = (advance(next_offset) if advance is not None else
                           None if next_offset is None else self._cursor(path, next_offset))
            result = dict(base, content=content,
                          nextCursor=next_cursor,
                          nodeExhausted=next_offset is None, valueCompleteInThisPage=complete)
            if advance is not None:
                result.update(scope='depth-first-node-pages', traversalExhausted=next_cursor is None)
            budget.check()
            fits = len(canonical(result)) <= self._limits.page_bytes
            if fits and envelope is not None:
                fits = len(canonical(envelope(result))) <= self._limits.page_bytes
                budget.check()
            return result, fits

        if self._state != 'present' or value is None:
            if offset or self._state != 'present' and path:
                fail('cursor-binding-mismatch')
            result, fits = finish(None, complete=base['state'] == 'null')
        elif type(value) is str:
            if offset > len(value):
                fail('cursor-binding-mismatch')
            whole, whole_fits = finish({'kind': 'text', 'text': value[offset:],
                'offsetUnit': 'unicode-code-points', 'start': offset, 'end': len(value),
                'total': len(value)}, complete=offset == 0)
            # Terminal pages omit a cursor; their smaller envelope can fit even
            # when a shorter nonterminal chunk cannot. Check that case first.
            low, high, best = offset, len(value) - 1, (whole, len(value)) if whole_fits else None
            if whole_fits:
                low, high = 1, 0
            while low <= high:
                budget.check()
                end = (low + high) // 2
                result, fits = finish({'kind': 'text', 'text': value[offset:end],
                    'offsetUnit': 'unicode-code-points', 'start': offset, 'end': end,
                    'total': len(value)}, end if end < len(value) else None,
                    offset == 0 and end == len(value))
                if fits:
                    best, low = (result, end), end + 1
                else:
                    high = end - 1
            if best is None or best[1] == offset and offset < len(value):
                fail('page-bound')
            result, fits = best[0], True
        elif type(value) in (dict, list):
            keys = sorted(value) if type(value) is dict else range(len(value))
            if offset > len(keys):
                fail('cursor-binding-mismatch')
            children = []
            result, fits = finish({'kind': value_type(value), 'children': [], 'start': offset,
                'end': offset, 'total': len(keys), 'order': 'unicode-code-point-key' if type(value) is dict else 'array-index'},
                offset if offset < len(keys) else None, len(keys) == 0)
            for index in range(offset, min(len(keys), offset + self._limits.max_items)):
                budget.check()
                key = keys[index]
                child = {'key': key, 'valueType': value_type(value[key]),
                         'cursor': self._cursor(path + [key], 0)}
                candidate = children + [child]
                page, ok = finish({'kind': value_type(value), 'children': candidate,
                    'start': offset, 'end': index + 1, 'total': len(keys),
                    'order': 'unicode-code-point-key' if type(value) is dict else 'array-index'},
                    index + 1 if index + 1 < len(keys) else None)
                if not ok:
                    break
                children, result, fits = candidate, page, True
            if offset < len(keys) and not children:
                fail('page-bound')
        else:
            if offset:
                fail('cursor-binding-mismatch')
            content = {'kind': value_type(value)}
            if type(value) in (int, float):
                content.update(jsonNumber=canonical(value).decode().strip(),
                               numberKind='integer' if type(value) is int else 'float')
            else:
                content['value'] = value
            result, fits = finish(content, complete=True)
        if not fits:
            fail('page-bound')
        wire = envelope(result) if envelope is not None else result
        if len(canonical(wire)) > self._limits.page_bytes:
            fail('page-bound')
        budget.check()
        return wire

    def walk(self, cursor=None, *, envelope=None, _budget=None):
        """Preorder all node pages/descendants through one bounded continuation.

        Compact ordinal paths are safe only because they bind the exact immutable
        copied snapshot and sorted ordering. Node cursors cannot be used here.
        """
        budget = _budget if _budget is not None else Budget(self._limits, self._clock)
        indices, offset = ([], 0) if cursor is None else self._decode(cursor, 'walk')
        value, path, parents = self._value, [], []
        for index in indices:
            budget.check()
            if type(value) not in (dict, list) or type(index) is not int or not 0 <= index < len(value):
                fail('cursor-binding-mismatch')
            keys = sorted(value) if type(value) is dict else range(len(value))
            parents.append(len(keys))
            key = keys[index]
            path.append(key)
            value = value[key]

        def advance(next_offset):
            if next_offset is not None:
                return self._cursor(indices, next_offset, 'walk')
            if type(value) in (dict, list) and value:
                return self._cursor(indices + [0], 0, 'walk')
            for depth in range(len(indices) - 1, -1, -1):
                if indices[depth] + 1 < parents[depth]:
                    return self._cursor(indices[:depth] + [indices[depth] + 1], 0, 'walk')
            return None

        return self._read_node(path, offset, cursor, budget, advance, envelope)


def error_envelope(error):
    if type(error) is not FieldPageError or error.code not in {'field-page-' + code for code in ERROR_CODES}:
        fail('invalid-error')
    return {'schema': SCHEMA, 'state': 'unavailable', 'reasonCode': error.code,
            'nextCursor': None, 'nodeExhausted': False, 'valueCompleteInThisPage': False}
