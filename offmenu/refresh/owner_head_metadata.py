"""Pure safe metadata projection for the separately gated owner HEAD diagnostic.

No runner, transport, filesystem access, logging, claim writer, or activation hook.
All input bytes are supplied by the caller. Passing a check never authorizes I/O.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import unquote_to_bytes, urlsplit

from .core import RefreshError, canonical, sha, strict_json
from .known_asset_intake import checked_headers

SCHEMA = 'offmenu-comprehensive-head-observation/1'
MAX_HEADER_BYTES = 65536
MAX_HEADERS = 100
MAX_VALUE_CHARS = 8192
MAX_METADATA_BYTES = 32 * 1024 * 1024
IGNORED = frozenset(('set-cookie', 'server-timing', 'content-security-policy',
                     'content-security-policy-report-only'))
KNOWN_HEADERS = frozenset(('content-length content-type content-encoding '
    'transfer-encoding connection location cache-control pragma vary expires age '
    'date etag last-modified retry-after set-cookie server-timing alt-svc '
    'content-disposition content-security-policy content-security-policy-report-only '
    'x-frame-options strict-transport-security x-content-type-options '
    'access-control-allow-origin access-control-allow-credentials accept-ranges '
    'server via x-cache').split())
KNOWN_QUERY_KEYS = frozenset(('id', 'type', 'download', 'X-Goog-Algorithm',
    'X-Goog-Credential', 'X-Goog-Date', 'X-Goog-Expires', 'X-Goog-Signature',
    'X-Goog-SignedHeaders', 'X-Amz-Algorithm', 'X-Amz-Credential', 'X-Amz-Date',
    'X-Amz-Expires', 'X-Amz-Signature', 'X-Amz-SignedHeaders', 'AWSAccessKeyId',
    'Signature', 'Expires'))
# Exact hosts already public in pinned source contracts. Other hosts are hashed.
PUBLIC_HOSTS = frozenset(('data.humdata.org', 'journals.plos.org', 'storage.googleapis.com'))
TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
CODES = frozenset(('proposal-input-invalid', 'proposal-pin-mismatch',
    'prior-failure-evidence-mismatch', 'failed-intent-mismatch',
    'owner-live-guards-unverified', 'header-envelope-exceeded',
    'header-input-invalid', 'media-intake-header-invalid',
    'media-intake-framing-invalid', 'invalid-response-headers',
    'head-observed', 'head-access-denied-held', 'head-rate-limited-held',
    'head-method-unsupported-held', 'head-status-unapproved-held',
    'head-transport-failed-held', 'head-deadline-exceeded-held'))
SAFETY = {
    'executionAuthorized': False, 'originalGETRetried': False,
    'priorGETCauseEstablished': False, 'acquisitionEnabled': False,
    'sourceClaimsChanged': False, 'custodyPromoted': False,
    'sourceAccessAndRateHoldsPreserved': True, 'downstreamHoldsPreserved': True,
    'methodSpecificOnly': True, 'redirectsFollowed': 0,
    'rawHeaderValuesEmitted': False, 'queryValuesEmitted': False,
    'rawPathsEmitted': False,
}


def fail(code):
    raise ValueError(code if code in CODES else 'proposal-input-invalid') from None


def _label(name, known):
    return name if name in known else 'sha256:' + hashlib.sha256(name.encode('utf-8')).hexdigest()


def redirect_shape(values, source_url):
    """No raw Location, userinfo, query value, fragment, or path is emitted."""
    if not values:
        return {'code': 'absent'}
    if len(values) != 1:
        return {'code': 'duplicate-location'}
    location = values[0]
    if (type(location) is not str or len(location) > MAX_VALUE_CHARS
            or any(ord(c) < 33 or ord(c) > 126 for c in location) or '\\' in location):
        return {'code': 'invalid-location'}
    try:
        parts, origin = urlsplit(location), urlsplit(source_url)
        if (parts.username is not None or parts.password is not None or parts.fragment
                or parts.port not in (None, 443) or parts.scheme not in ('', 'https')
                or (parts.scheme and not parts.netloc)
                or (parts.netloc and not parts.hostname)):
            return {'code': 'invalid-location'}
        host = parts.hostname if parts.netloc else origin.hostname
        if not host or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', host):
            return {'code': 'invalid-location'}
        names = []
        if parts.query:
            for pair in parts.query.split('&'):
                name = unquote_to_bytes(pair.partition('=')[0]).decode('utf-8', errors='strict')
                if not name or len(name) > 8192 or any(ord(c) < 32 or ord(c) == 127 for c in name):
                    return {'code': 'invalid-location-query'}
                names.append(_label(name, KNOWN_QUERY_KEYS))
        if len(names) > 100:
            return {'code': 'location-query-limit'}
        path = parts.path.encode('ascii')
        segments = [len(s) for s in parts.path.split('/') if s]
        public = host in PUBLIC_HOSTS
        return {'code': 'observed-shape-only',
            'referenceKind': 'absolute' if parts.scheme else 'network-path' if parts.netloc else 'relative',
            'originRelation': 'same-origin' if host == origin.hostname else 'cross-origin',
            'publicOrigin': 'https://' + host if public else None,
            'publicHost': host if public else None,
            'unreviewedHostSHA256': None if public else sha(host.encode()),
            'pathSHA256': sha(path), 'pathBytes': len(path), 'pathSegments': len(segments),
            'segmentLengths': segments[:100], 'segmentLengthsTruncated': len(segments) > 100,
            'absolutePath': parts.path.startswith('/'), 'queryPresent': bool(parts.query),
            'queryNameCounts': dict(sorted(Counter(names).items()))}
    except (ValueError, UnicodeError, OverflowError):
        return {'code': 'invalid-location'}


def _header_facts(raw, source, status):
    if (not isinstance(raw, list) or len(raw) > MAX_HEADERS
            or any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in raw)):
        fail('header-input-invalid')
    groups = {}
    total = 0
    invalid_names = invalid_values = 0
    first_generic_failure = 'none'
    for key, value in raw:
        if type(key) is not str or type(value) is not str:
            fail('header-input-invalid')
        try:
            octets = len(value.encode('latin-1'))
            total += len(key.encode('ascii')) + octets + 4
        except UnicodeError:
            fail('header-input-invalid')
        if total > MAX_HEADER_BYTES:
            fail('header-envelope-exceeded')
        valid_name = bool(TOKEN.fullmatch(key))
        invalid_names += not valid_name
        invalid_value = any(ord(c) < 32 or ord(c) == 127 for c in value)
        invalid_values += invalid_value
        if first_generic_failure == 'none':
            if not valid_name or invalid_value:
                first_generic_failure = 'syntax'
            elif len(value) > MAX_VALUE_CHARS:
                first_generic_failure = 'value-length'
        name = key.lower()
        label = _label(name, KNOWN_HEADERS) if valid_name else 'sha256:' + sha(key.encode())
        group = groups.setdefault(label, {'name': label, 'count': 0, 'valueCharacters': [],
            'valueBytes': [], 'ignoredByCurrentValidator': name in IGNORED,
            'oversizedValues': 0})
        group['count'] += 1
        group['valueCharacters'].append(len(value))
        group['valueBytes'].append(octets)
        group['oversizedValues'] += len(value) > MAX_VALUE_CHARS
    facts = list(sorted(groups.values(), key=lambda row: row['name']))
    duplicates = [r['name'] for r in facts if r['count'] > 1 and not r['ignoredByCurrentValidator']]
    oversized = [r['name'] for r in facts if r['oversizedValues']]
    failure_point = first_generic_failure
    if failure_point == 'none' and duplicates:
        failure_point = 'duplicate-nonignored'
    try:
        checked_headers(raw, source, redirect=bool(source['mediaIntake']['redirect']) or 300 <= status < 400)
        validator = 'accepted'
    except RefreshError as error:
        # Whitelist lookup only: no generic exception text is emitted.
        validator = error.args[0] if error.args and error.args[0] in {
            'media-intake-header-invalid', 'media-intake-framing-invalid', 'invalid-response-headers'
        } else 'header-input-invalid'
    vary = [v for k, v in raw if k.lower() == 'vary']
    encoding = [v for k, v in raw if k.lower() == 'content-encoding']
    return {'fieldCount': len(raw), 'reconstructedHeaderBytes': total,
        'headerGroups': facts, 'invalidNameCount': invalid_names, 'invalidValueCount': invalid_values,
        'duplicateNonignoredNames': duplicates, 'oversizedNames': oversized,
        'genericHeaderFailurePoint': failure_point, 'currentGETValidatorOnHEADHeaders': validator,
        'unsupportedVary': len(vary) == 1 and vary[0].lower() not in ('', 'accept-encoding'),
        'unsupportedEncoding': len(encoding) == 1 and encoding[0].lower() != 'identity',
        'redirect': redirect_shape([v for k, v in raw if k.lower() == 'location'], source['url'])}


def sanitize_response(source, status, headers, wire_header_bytes):
    entry, contract = source['entry'], source['contract']
    if (type(status) is not int or not 100 <= status <= 599
            or type(wire_header_bytes) is not int or not 0 <= wire_header_bytes <= MAX_HEADER_BYTES):
        fail('header-input-invalid')
    facts = _header_facts(headers, contract, status)
    if facts['reconstructedHeaderBytes'] > wire_header_bytes:
        fail('header-input-invalid')
    code = ('head-access-denied-held' if status in (401, 403, 407, 451) else
        'head-rate-limited-held' if status == 429 else
        'head-method-unsupported-held' if status in (405, 501) else
        'head-observed' if status in (200, 301, 302, 303, 307, 308) else
        'head-status-unapproved-held')
    result = {'schemaVersion': SCHEMA, 'method': 'HEAD', 'sourceKey': entry['sourceKey'],
        'sourceContractSHA256': entry['sourceContractSHA256'],
        'sourceURLSHA256': entry['sourceURLSHA256'], 'priorDetailSHA256': entry['priorDetailSHA256'],
        'freshFetchDetailSHA256': entry['freshFetchDetailSHA256'],
        'priorGETErrorCode': entry['priorErrorCode'], 'httpStatus': status, 'code': code,
        'wireHeaderBytes': wire_header_bytes, 'headerFacts': facts, **SAFETY}
    if len(canonical(result)) > 12000:
        fail('header-envelope-exceeded')
    return result


def validate_observation(value, source):
    """Revalidate the closed metadata schema before any parent persistence/output."""
    def check(condition):
        if not condition:
            fail('header-input-invalid')

    def integer(number, maximum=MAX_HEADER_BYTES):
        return type(number) is int and 0 <= number <= maximum

    def digest(text):
        return type(text) is str and re.fullmatch('[a-f0-9]{64}', text) is not None

    def label(text, known):
        return type(text) is str and (text in known or
            text.startswith('sha256:') and digest(text[7:]))

    check(type(value) is dict and len(canonical(value)) <= 12000)
    expected = {'schemaVersion': SCHEMA, 'method': 'HEAD',
        **{k: source['entry'][k] for k in ('sourceKey', 'sourceContractSHA256',
            'sourceURLSHA256', 'priorDetailSHA256', 'freshFetchDetailSHA256')},
        'priorGETErrorCode': source['entry']['priorErrorCode'], **SAFETY}
    check(set(value) == set(expected) | {'httpStatus', 'code', 'wireHeaderBytes', 'headerFacts'})
    check(canonical({k: value[k] for k in expected}) == canonical(expected))
    status = value['httpStatus']
    check(type(status) is int and 200 <= status <= 599)
    expected_code = ('head-access-denied-held' if status in (401, 403, 407, 451) else
        'head-rate-limited-held' if status == 429 else
        'head-method-unsupported-held' if status in (405, 501) else
        'head-observed' if status in (200, 301, 302, 303, 307, 308) else 'head-status-unapproved-held')
    check(value['code'] == expected_code and integer(value['wireHeaderBytes']))
    facts = value['headerFacts']
    check(type(facts) is dict and set(facts) == {'fieldCount', 'reconstructedHeaderBytes',
        'headerGroups', 'invalidNameCount', 'invalidValueCount', 'duplicateNonignoredNames',
        'oversizedNames', 'genericHeaderFailurePoint', 'currentGETValidatorOnHEADHeaders',
        'unsupportedVary', 'unsupportedEncoding', 'redirect'})
    check(integer(facts['fieldCount'], MAX_HEADERS) and
        integer(facts['reconstructedHeaderBytes'], value['wireHeaderBytes']))
    for name in ('invalidNameCount', 'invalidValueCount'):
        check(integer(facts[name], facts['fieldCount']))
    for name in ('unsupportedVary', 'unsupportedEncoding'):
        check(type(facts[name]) is bool)
    check(facts['genericHeaderFailurePoint'] in ('none', 'syntax', 'value-length', 'duplicate-nonignored'))
    check(facts['currentGETValidatorOnHEADHeaders'] in ('accepted', 'media-intake-header-invalid',
        'media-intake-framing-invalid', 'invalid-response-headers', 'header-input-invalid'))
    groups = facts['headerGroups']
    check(type(groups) is list and len(groups) <= MAX_HEADERS)
    names, count = [], 0
    for group in groups:
        check(type(group) is dict and set(group) == {'name', 'count', 'valueCharacters',
            'valueBytes', 'ignoredByCurrentValidator', 'oversizedValues'})
        check(label(group['name'], KNOWN_HEADERS) and integer(group['count'], MAX_HEADERS)
            and group['count'] > 0 and type(group['ignoredByCurrentValidator']) is bool)
        check(group['ignoredByCurrentValidator'] == (group['name'] in IGNORED))
        for key in ('valueCharacters', 'valueBytes'):
            check(type(group[key]) is list and len(group[key]) == group['count'] and
                all(integer(v) for v in group[key]))
        check(group['valueCharacters'] == group['valueBytes'])  # Latin-1 wire values.
        check(type(group['oversizedValues']) is int and group['oversizedValues'] ==
            sum(v > MAX_VALUE_CHARS for v in group['valueCharacters']))
        names.append(group['name']); count += group['count']
    check(names == sorted(set(names)) and count == facts['fieldCount'])
    check(facts['duplicateNonignoredNames'] == [g['name'] for g in groups
        if g['count'] > 1 and not g['ignoredByCurrentValidator']])
    check(facts['oversizedNames'] == [g['name'] for g in groups if g['oversizedValues']])
    redirect = facts['redirect']
    check(type(redirect) is dict and type(redirect.get('code')) is str)
    if redirect['code'] != 'observed-shape-only':
        check(set(redirect) == {'code'} and redirect['code'] in ('absent', 'duplicate-location',
            'invalid-location', 'invalid-location-query', 'location-query-limit'))
    else:
        check(set(redirect) == {'code', 'referenceKind', 'originRelation', 'publicOrigin',
            'publicHost', 'unreviewedHostSHA256', 'pathSHA256', 'pathBytes', 'pathSegments',
            'segmentLengths', 'segmentLengthsTruncated', 'absolutePath', 'queryPresent', 'queryNameCounts'})
        check(redirect['referenceKind'] in ('absolute', 'network-path', 'relative') and
            redirect['originRelation'] in ('same-origin', 'cross-origin'))
        host = redirect['publicHost']
        check((host in PUBLIC_HOSTS and redirect['publicOrigin'] == 'https://' + host and
            redirect['unreviewedHostSHA256'] is None) or
            (host is None and redirect['publicOrigin'] is None and digest(redirect['unreviewedHostSHA256'])))
        check(digest(redirect['pathSHA256']) and integer(redirect['pathBytes'], MAX_VALUE_CHARS)
            and integer(redirect['pathSegments'], MAX_VALUE_CHARS))
        segments = redirect['segmentLengths']
        check(type(segments) is list and len(segments) == min(100, redirect['pathSegments'])
            and all(integer(s, MAX_VALUE_CHARS) and s > 0 for s in segments))
        check(sum(segments) <= redirect['pathBytes'])
        for name in ('segmentLengthsTruncated', 'absolutePath', 'queryPresent'):
            check(type(redirect[name]) is bool)
        check(redirect['segmentLengthsTruncated'] == (redirect['pathSegments'] > 100))
        queries = redirect['queryNameCounts']
        check(type(queries) is dict and len(queries) <= 100 and
            all(label(k, KNOWN_QUERY_KEYS) and integer(v, 100) and v > 0 for k, v in queries.items())
            and sum(queries.values()) <= 100)
    return value
