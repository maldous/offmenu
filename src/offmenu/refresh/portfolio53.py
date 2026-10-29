"""Worker53 metadata bindings. No downloader, source parser or admission factory.

Only the bundled reviewed-as-code configuration selects readable metadata. Raw
asset references are opaque; this module never opens them. Fixture qualification
reuses the shared source contract and field-origin validator.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .core import canonical, strict_json, timestamp, safe_path, RefreshError
from .acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from .field_provenance import field_origin_errors
from .portfolio53_catalogue import CATALOGUE

CONFIG = Path(__file__).resolve().parents[3] / 'config/portfolios/worker53-staging.json'
MAX_METADATA = 1024 * 1024
MAX_JSON_DEPTH = 64
DIGEST = re.compile(r'[0-9a-f]{64}')
POLICY = fingerprint({'worker': 53, 'scope': 'source-native-authored-fixture-v1',
                      'unknownBasis': None, 'noConversion': True})
FIXTURE_INPUTS = {'fixture.json': b'{"price":"001.20","unit":"KG"}',
                  'rights.json': b'{"scope":"authored-fixture-only"}',
                  'scope.json': b'{"expectedRecords":1}'}


def load_catalogue():
    """Copy packaged inert declarations; CONFIG is the unchanged source JSON mirror."""
    return deepcopy(CATALOGUE)


class _JsonDepthExceeded(ValueError):
    pass


def _check_json_depth(value):
    """Bound decoded nesting without Python recursion or a breadth-sized stack."""
    stack = [(iter((value,)), 0)]
    while stack:
        values, depth = stack[-1]
        try:
            item = next(values)
        except StopIteration:
            stack.pop()
            continue
        if depth > MAX_JSON_DEPTH:
            raise _JsonDepthExceeded()
        if isinstance(item, dict):
            stack.append((iter(item.values()), depth + 1))
        elif isinstance(item, list):
            stack.append((iter(item), depth + 1))


def _decode_json(raw):
    try:
        value = strict_json(raw)
    except RecursionError as error:
        raise _JsonDepthExceeded() from error
    _check_json_depth(value)
    return value


def _read_regular(path, *, limit=MAX_METADATA, expected=None, label='metadata'):
    """Bound a nonblocking read to one regular-file descriptor, with no reopen."""
    path = safe_path(path)
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError(label + '-not-regular')
        if before.st_size > limit:
            raise RefreshError(label + '-too-large')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
            after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                              value.st_mtime_ns, value.st_ctime_ns)
    if (not stat.S_ISREG(current.st_mode) or identity(before) != identity(after)
            or identity(after) != identity(current) or len(raw) != after.st_size
            or len(raw) > limit):
        raise RefreshError(label + '-changed-during-read')
    if expected is not None and (len(raw) != expected['bytes'] or
            hashlib.sha256(raw).hexdigest() != expected['sha256']):
        raise RefreshError(label + '-pin-mismatch')
    return raw


def resolve_pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('metadata-selector-invalid')
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def inspect_binding(binding, now):
    """Pure report plus exact, bounded JSON metadata readback; no asset I/O.

    `binding` is application configuration, never a source manifest/CLI plugin.
    Pin/read failures are isolated to this binding and never disclose contents.
    Metadata verification is not source-byte validation or a rights decision.
    """
    if not isinstance(binding, dict):
        return {'sourceId': None, 'country': None, 'releaseId': None,
                'outcome': 'malformed', 'diagnostics': ['binding-not-object'],
                'networkRequests': 0, 'sourceBodyReads': 0,
                'stagingAccepted': False, 'goldAdmitted': False}
    result = {'sourceId': binding.get('sourceId'), 'country': binding.get('country'),
              'releaseId': binding.get('releaseId'), 'outcome': 'malformed',
              'diagnostics': [], 'networkRequests': 0, 'sourceBodyReads': 0,
              'stagingAccepted': False, 'goldAdmitted': False}
    errors = set()
    try:
        if (binding['country'] not in ('LK', 'LR', 'LS', 'LT')
                or not all(isinstance(binding[k], str) and binding[k]
                           for k in ('sourceId', 'releaseId'))
                or not isinstance(binding['metadata'], list) or not binding['metadata']
                or not isinstance(binding['holds'], list)
                or not isinstance(binding['fieldDeclarations'], list)):
            raise ValueError('binding-invalid')
        # Original source age never uses mtime, metadata verification or publication.
        acquired = binding.get('originalAcquiredAt')
        result['cache'] = {'minimumReuseDays': 30, 'originalAcquiredAt': acquired,
                           'metadataValidatedAt': binding.get('metadataValidatedAt'),
                           'sourceBytesValidatedAt': None, 'sourceBytesVerified': False,
                           'downloadPermitted': False, 'forceSupported': False}
        if acquired is None:
            result['cache']['intent'] = 'unknown-no-download'
            errors.add('acquisition-time-missing')
        else:
            age = (now - timestamp(acquired)).total_seconds()
            if age < 0:
                raise ValueError('acquisition-time-future')
            result['cache']['originalAgeDays'] = int(age // 86400)
            result['cache']['intent'] = ('reuse-retained-cache-only' if age < 30 * 86400
                                         else 'revalidation-evidence-required-no-download')
            if age >= 30 * 86400:
                errors.add('source-validation-stale')
        if binding.get('metadataValidatedAt') is not None:
            validated = timestamp(binding['metadataValidatedAt'])
            if validated > now or (acquired and validated < timestamp(acquired)):
                raise ValueError('metadata-validation-time-invalid')
        result['verifiedMetadata'] = []
        metadata_values = {}
        for evidence in binding['metadata']:
            if (evidence['role'] not in ('receipt-metadata', 'publisher-metadata',
                                        'retained-annotation', 'review-receipt')
                    or not DIGEST.fullmatch(evidence['sha256'])
                    or type(evidence['bytes']) is not int
                    or not 0 < evidence['bytes'] <= MAX_METADATA):
                raise ValueError('metadata-contract-invalid')
            raw = _read_regular(evidence['path'], limit=evidence['bytes'],
                                expected=evidence)
            value = _decode_json(raw)
            metadata_values[evidence['sha256']] = value
            for selector in evidence['selectors']:
                resolve_pointer(value, selector)
            result['verifiedMetadata'].append({k: evidence[k] for k in
                                               ('sha256', 'bytes', 'role', 'selectors')})
        if binding['holds']:
            errors.add('source-held')
        if binding.get('stagingScopeAccepted') is not True:
            errors.add('staging-scope-not-accepted')
        for declaration in binding['fieldDeclarations']:
            if (not all(isinstance(declaration[k], str) and declaration[k]
                        for k in ('target', 'sourceSelector', 'evidenceSelector', 'evidenceSha256'))
                    or declaration['evidenceSha256'] not in
                    {e['sha256'] for e in binding['metadata']}):
                raise ValueError('field-declaration-invalid')
            resolve_pointer(metadata_values[declaration['evidenceSha256']],
                            declaration['evidenceSelector'])
        result['declarations'] = binding['fieldDeclarations']
        result['nativeUnitsAndBases'] = binding['nativeUnitsAndBases']
        result['unknowns'] = binding['unknowns']
        result['blockers'] = binding.get('blockers', [])
        result['applicability'] = binding['applicability']
        result['rawAssetReferences'] = binding['rawAssetReferences']
        result['sharedInterfaces'] = ['offmenu.refresh.acceptance.SourceContract',
                                      'offmenu.refresh.acceptance.qualify',
                                      'offmenu.refresh.field_provenance.field_origin_errors']
        result['productionFactory'] = None
        result['outcome'] = ('held' if 'source-held' in errors or
                             'staging-scope-not-accepted' in errors else
                             'stale' if 'source-validation-stale' in errors else
                             'missing' if errors else 'valid-metadata-binding')
    except FileNotFoundError:
        errors.add('metadata-missing'); result['outcome'] = 'missing'
    except (_JsonDepthExceeded, RecursionError):
        errors.add('metadata-json-depth-exceeded'); result['outcome'] = 'malformed'
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        errors.add('metadata-or-binding-malformed'); result['outcome'] = 'malformed'
    result['diagnostics'] = sorted(errors)
    return result


def _identity(report):
    content = {k: v for k, v in report.items() if k not in ('bindingSha256', 'replay')}
    content = json.loads(canonical(content))
    for source in content['sources']:
        source.get('cache', {}).pop('originalAgeDays', None)
    return fingerprint(content)


def _validate_previous(report):
    fields = {'schemaVersion', 'sources', 'stagingAccepted', 'goldAdmitted',
              'networkRequests', 'sourceBodyReads', 'bindingSha256', 'replay'}
    if not isinstance(report, dict) or set(report) != fields:
        raise RefreshError('previous-report-invalid')
    try:
        _check_json_depth(report)
    except _JsonDepthExceeded as error:
        raise RefreshError('previous-report-json-depth-exceeded') from error
    if (report['schemaVersion'] != 'offmenu-worker53-staging-binding/1'
            or not isinstance(report['sources'], list)
            or report['stagingAccepted'] is not False or report['goldAdmitted'] is not False
            or any(type(report[k]) is not int or report[k] != 0 for k in ('networkRequests', 'sourceBodyReads'))
            or not isinstance(report['bindingSha256'], str) or not DIGEST.fullmatch(report['bindingSha256'])
            or report['replay'] not in ('metadata-binding-report', 'verified-metadata-no-op')):
        raise RefreshError('previous-report-invalid')
    required = {'sourceId', 'country', 'releaseId', 'outcome', 'diagnostics',
                'networkRequests', 'sourceBodyReads', 'stagingAccepted', 'goldAdmitted'}
    for source in report['sources']:
        if (not isinstance(source, dict) or not required <= set(source)
                or not isinstance(source.get('cache', {}), dict)
                or source['outcome'] not in ('valid-metadata-binding', 'held', 'stale', 'missing', 'malformed')
                or not isinstance(source['diagnostics'], list)
                or any(not isinstance(code, str) for code in source['diagnostics'])
                or source['stagingAccepted'] is not False or source['goldAdmitted'] is not False
                or any(type(source[k]) is not int or source[k] != 0 for k in ('networkRequests', 'sourceBodyReads'))):
            raise RefreshError('previous-report-invalid')
    try:
        identity = _identity(report)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise RefreshError('previous-report-invalid') from error
    if report['bindingSha256'] != identity:
        raise RefreshError('previous-report-identity-invalid')


def plan(bindings, *, now, previous=None):
    if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
        raise RefreshError('policy-clock-must-be-utc')
    if previous is not None:
        _validate_previous(previous)
    sources = [inspect_binding(binding, now) for binding in bindings]
    content = {'schemaVersion': 'offmenu-worker53-staging-binding/1',
               'sources': sources, 'stagingAccepted': False, 'goldAdmitted': False,
               'networkRequests': 0, 'sourceBodyReads': 0}
    identity = _identity(content)
    return {**content, 'bindingSha256': identity,
            'replay': 'verified-metadata-no-op' if previous is not None and
            previous.get('bindingSha256') == identity else 'metadata-binding-report'}


def fixture_record(input_sha, acquired_at):
    """One authored nonproduction source-cell example; no real payload argument."""
    origin = lambda field: {'kind': 'source', 'sourceId': 'worker53-fixture',
        'releaseId': 'authored-v1', 'inputPath': 'fixture.json',
        'inputSha256': input_sha, 'sourceRecordId': 'authored-row-1', 'sourceField': field}
    return {'id': 'worker53-fixture:1', 'kind': 'worker53-native-price-fixture',
        'schemaVersion': '1', 'data': {'priceLiteral': '001.20', 'unitLiteral': 'KG',
                                      'basis': None},
        'provenance': {'sourceId': 'worker53-fixture', 'releaseId': 'authored-v1',
            'fetchedAt': acquired_at, 'fieldOrigins': {
                '/data/priceLiteral': origin('price'), '/data/unitLiteral': origin('unit'),
                '/data/basis': {'kind': 'constant', 'policySha256': POLICY,
                                'symbol': 'unknown-source-basis'}}}}


def qualify_authored_fixture(bundle, candidate, manifest, *, held=False):
    """Trusted authored fixture contract, always fixture=True, never real admission."""
    acquired_at = '2026-10-01T00:00:00Z'
    assets = tuple(Asset(name, len(raw), hashlib.sha256(raw).hexdigest())
                   for name, raw in FIXTURE_INPUTS.items())
    pins = {a.path: a.sha256 for a in assets}
    schema = {'type': 'object', 'required': ['id','kind','schemaVersion','data','provenance'],
        'additionalProperties': False, 'properties': {
            'id': {'const': 'worker53-fixture:1'},
            'kind': {'const': 'worker53-native-price-fixture'},
            'schemaVersion': {'const': '1'}, 'provenance': {'type': 'object'},
            'data': {'type': 'object', 'additionalProperties': False,
                'required': ['priceLiteral','unitLiteral','basis'], 'properties': {
                    'priceLiteral': {'type': 'string'}, 'unitLiteral': {'type': 'string'},
                    'basis': {'type': 'null'}}}}}
    schemas = {'worker53-native-price-fixture': schema}
    def semantics(row):
        errors = field_origin_errors(row, pins, policy_pins=(POLICY,))
        expected = fixture_record(pins['fixture.json'], acquired_at)
        if row.get('data') != expected['data']:
            errors.append('fixture-literal-mismatch')
        if row.get('provenance', {}).get('fieldOrigins') != expected['provenance']['fieldOrigins']:
            errors.append('fixture-selector-mismatch')
        return errors
    contract = SourceContract('worker53-fixture', 'authored-v1', 'authored-native-only',
        acquired_at, assets, 1, ids_digest(['worker53-fixture:1']), schemas,
        fingerprint(schemas), semantics, POLICY, assets[1], assets[2],
        frozenset(('retain','parse','transform')), fixture=True,
        holds=('authored-test-hold',) if held else ())
    return qualify(contract, bundle, candidate, manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC planning clock')
    parser.add_argument('--previous-report', type=Path)
    args = parser.parse_args(argv)
    bindings = load_catalogue()['sources']
    previous = None
    if args.previous_report:
        try:
            previous = _decode_json(_read_regular(args.previous_report,
                                                 label='previous-report'))
            _validate_previous(previous)
        except RefreshError as error:
            parser.exit(2, str(error) + '\n')
        except (_JsonDepthExceeded, RecursionError):
            parser.exit(2, 'previous-report-json-depth-exceeded\n')
        except (OSError, ValueError):
            parser.exit(2, 'previous-report-invalid\n')
    try:
        report = plan(bindings, now=timestamp(args.now), previous=previous)
    except RefreshError as error:
        parser.exit(2, str(error) + '\n')
    print(canonical(report).decode(), end='')


if __name__ == '__main__':
    main()
