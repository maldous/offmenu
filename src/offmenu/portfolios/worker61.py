"""Offline GP/NU/TO/YT receipt binding. Never opens declared source assets.

Only explicitly pinned JSON metadata is read. No fetch/import/parser selection,
country acceptance, rights activation or shared-core edits occur here.
"""
import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

from jsonschema import Draft202012Validator

from offmenu.refresh.core import canonical, safe_path, strict_json, timestamp
from offmenu.refresh.acceptance import fingerprint
from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.adapter_mapping import retained_adapters
from offmenu.refresh.field_provenance import field_origin_errors

COUNTRIES = ('GP', 'NU', 'TO', 'YT')
DOMAINS = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
           'prices/baskets', 'dietary references')
HEX = r'^[0-9a-f]{64}$'
PIN = {'type': 'object', 'additionalProperties': False,
       'required': ['path', 'sha256', 'bytes'], 'properties': {
           'path': {'type': 'string', 'minLength': 1},
           'sha256': {'type': 'string', 'pattern': HEX},
           'bytes': {'type': 'integer', 'minimum': 1, 'maximum': 262144}}}
FIELD = {'type': 'object', 'additionalProperties': False,
         'required': ['selector', 'unit', 'basis'], 'properties': {
             'selector': {'type': ['string', 'null'], 'pattern': '^/'},
             'unit': {'type': ['string', 'null']},
             'basis': {'type': ['string', 'null']}}}
ENTRY = {'type': 'object', 'additionalProperties': False,
         'required': ['sourceId', 'releaseId', 'country', 'role', 'domains',
                      'manifest', 'fields', 'acquiredSelector',
                      'validatedAt', 'holds', 'missing', 'rightsStatus',
                      'adapterSourceId'], 'properties': {
             **{k: {'type': 'string', 'minLength': 1}
                for k in ('sourceId', 'releaseId', 'role')},
             'country': {'enum': list(COUNTRIES)},
             'domains': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                         'items': {'enum': list(DOMAINS)}},
             'manifest': {'anyOf': [PIN, {'type': 'null'}]},
             'fields': {'type': 'object', 'minProperties': 1, 'maxProperties': 32,
                        'additionalProperties': FIELD},
             'acquiredSelector': {'type': ['string', 'null'], 'pattern': '^/'},
             'validatedAt': {'type': ['string', 'null']},
             'holds': {'type': 'array', 'uniqueItems': True,
                       'items': {'type': 'string', 'minLength': 1}},
             'missing': {'type': 'array', 'uniqueItems': True,
                         'items': {'type': 'string', 'minLength': 1}},
             'rightsStatus': {'enum': ['metadata-reference-only', 'unknown', 'held']},
             'adapterSourceId': {'type': ['string', 'null']}}}


def pointer(value, selector):
    """Literal RFC6901 locator; never interpret a value as a filesystem path."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-missing')
    for part in selector.split('/')[1:]:
        if re.search(r'~(?![01])', part):
            raise ValueError('selector-malformed')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part):
                raise ValueError('selector-malformed')
            value = value[int(part)]
        else:
            value = value[part]
    return value


def _metadata(root, pin):
    relative = PurePosixPath(pin['path'])
    if (relative.is_absolute() or '..' in relative.parts
            or str(relative) != pin['path'] or '\\' in pin['path']
            or relative.suffix != '.json'):
        raise ValueError('unsafe-metadata-path')
    path = safe_path(root / pin['path'])
    if not path.is_relative_to(root):
        raise ValueError('unsafe-metadata-path')
    raw = read_regular(path, 262144)
    if len(raw) != pin['bytes'] or fingerprint_bytes(raw) != pin['sha256']:
        raise ValueError('stale-input-pin')
    return strict_json(raw)


def read_regular(path, limit):
    """Read bounded bytes from one nonblocking, verified regular descriptor.

    Parent descriptors prevent symlink substitution during pathname traversal.
    A renamed path is never reopened after validation; hash and parse use these
    same returned bytes. Nonregular objects are rejected before their first read.
    """
    path = safe_path(path)
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open('/', flags | os.O_DIRECTORY)
    descriptor = None
    try:
        for part in path.parts[1:-1]:
            next_directory = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(path.name, flags, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('regular-file-required')
        if before.st_size > limit:
            raise ValueError('runtime-input-too-large')
        chunks, consumed = [], 0
        while consumed <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - consumed))
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > limit:
                raise ValueError('runtime-input-too-large')
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError('runtime-input-changed-during-read')
        return b''.join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def fingerprint_bytes(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def metadata_reference(entry, fields):
    """Receipt scalar origins plus explicit config constants, never PDF cells."""
    data, origins = {}, {}
    policy = fingerprint(entry)
    for name, field in fields.items():
        escaped = name.replace('~', '~0').replace('/', '~1')
        prefix = '/data/' + escaped
        data[name] = {'value': field['value'], 'nativeUnit': field['unit'],
                      'nativeBasis': field['basis']}
        origins[prefix + '/value'] = {
            'kind': 'source', 'sourceId': entry['sourceId'],
            'releaseId': entry['releaseId'], 'inputPath': entry['manifest']['path'],
            'inputSha256': entry['manifest']['sha256'],
            'sourceRecordId': 'receipt:' + entry['sourceId'],
            'sourceField': field['selector']}
        for key in ('nativeUnit', 'nativeBasis'):
            origins[prefix + '/' + key] = {
                'kind': 'constant', 'policySha256': policy,
                'symbol': key + ('-explicit-unknown' if data[name][key] is None
                                  else '-authored-declaration')}
    return {'id': 'metadata:' + entry['sourceId'], 'kind': 'sourceInputBinding',
            'schemaVersion': '1', 'data': data,
            'provenance': {'sourceId': entry['sourceId'], 'releaseId': entry['releaseId'],
                           'fieldOrigins': origins}}


def bind(entry, metadata_root, now):
    result = {'sourceId': entry.get('sourceId'), 'country': entry.get('country'),
              'status': 'malformed', 'diagnostics': [], 'fields': {},
              'metadataBound': False, 'sourceProcessingAuthorized': False,
              'accepted': False, 'sourceAssetBytesVerified': False}
    if list(Draft202012Validator(ENTRY).iter_errors(entry)):
        result['diagnostics'] = ['binding-schema-invalid']
        return result
    result.update(releaseId=entry['releaseId'], role=entry['role'],
                  domains=entry['domains'], holds=entry['holds'],
                  missing=entry['missing'], rightsStatus=entry['rightsStatus'],
                  bindingKey=fingerprint(entry))
    result['metadataSourceKey'] = fingerprint({k: entry[k] for k in
        ('sourceId', 'releaseId', 'manifest')})
    result['fields'] = {name: {**declaration, 'manifest': entry['manifest'], 'value': None}
                        for name, declaration in sorted(entry['fields'].items())}
    errors = result['diagnostics']
    if entry['holds']:
        errors.append('source-held')
    if entry['missing']:
        errors.append('source-inputs-missing')
    if entry['rightsStatus'] != 'metadata-reference-only':
        errors.append('metadata-use-unresolved')
    if entry['manifest'] is None:
        errors.append('manifest-missing')
    else:
        try:
            data = _metadata(metadata_root, entry['manifest'])
            result['metadataBound'] = True
            resolved = {}
            for name, declaration in sorted(entry['fields'].items()):
                item = {**declaration, 'manifest': entry['manifest'], 'value': None}
                try:
                    item['value'] = pointer(data, declaration['selector'])
                    if isinstance(item['value'], (dict, list)):
                        raise ValueError('scalar-selector-required')
                    if isinstance(item['value'], str) and len(item['value']) > 8192:
                        raise ValueError('scalar-size-limit')
                    if isinstance(item['value'], float) and not math.isfinite(item['value']):
                        raise ValueError('nonfinite-scalar')
                    resolved[name] = item
                except (KeyError, IndexError, TypeError, ValueError):
                    item['value'] = None
                    errors.append('field-selector-missing:' + name)
                result['fields'][name] = item
            if resolved:
                reference = metadata_reference(entry, resolved)
                result['stagingReference'] = reference
                result['fieldOriginErrors'] = field_origin_errors(reference,
                    {entry['manifest']['path']: entry['manifest']['sha256']},
                    policy_pins=(result['bindingKey'],))
                errors.extend(result['fieldOriginErrors'])
            result['cache'] = {'originalAcquiredAt': None,
                               'validatedAt': None,
                               'validationAgeSeconds': None,
                               'minimumReuseSeconds': MIN_TTL,
                               'networkRequests': 0, 'mtimeUsed': False,
                               'plannerCapability': 'metadata-intent-only-shared-pure-planner-absent',
                               'revalidationResetsAcquisitionAge': False,
                               'decision': 'acquisition-time-unknown'}
            acquired = (pointer(data, entry['acquiredSelector'])
                        if entry['acquiredSelector'] is not None else None)
            if acquired is not None:
                if not isinstance(acquired, str) or len(acquired) > 64:
                    raise ValueError('acquisition-time-invalid')
                age = (now - timestamp(acquired)).total_seconds()
                if age < 0:
                    raise ValueError('acquisition-time-in-future')
                result['cache'].update(originalAcquiredAt=acquired, acquisitionAgeSeconds=age,
                    decision='reuse-retained-metadata-no-download' if age < MIN_TTL
                    else 'revalidation-review-required-no-download')
            else:
                errors.append('acquisition-time-unknown')
            if entry['validatedAt'] is not None:
                if len(entry['validatedAt']) > 64:
                    raise ValueError('validation-time-invalid')
                validated = timestamp(entry['validatedAt'])
                if validated > now:
                    raise ValueError('validation-time-in-future')
                result['cache'].update(validatedAt=entry['validatedAt'],
                                      validationAgeSeconds=(now - validated).total_seconds())
            result['retainedAdapter'] = next((a for a in retained_adapters()
                if a['sourceId'] == entry['adapterSourceId']
                and a['releaseId'] == entry['releaseId']), None)
            # A metadata match is never a route for PDF/HTML body processing.
        except FileNotFoundError:
            errors.append('metadata-file-missing')
        except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
            # Fixed diagnostics only: no raw receipt, filesystem path or secret.
            errors.append('stale-input-pin' if error.args == ('stale-input-pin',)
                          else 'metadata-invalid')
    errors[:] = sorted(set(errors))
    result['status'] = ('held' if entry['holds'] else
        'missing' if entry['manifest'] is None or 'metadata-file-missing' in errors else
        'stale-input' if 'stale-input-pin' in errors else
        'invalid' if 'metadata-invalid' in errors else
        'needs-input' if errors else 'metadata-bound')
    return result


def assess(config, metadata_root, *, now):
    """Isolated per-source diagnostics. Caller supplies clock; no AI/network."""
    root = safe_path(metadata_root)
    clock = timestamp(now)
    if (not isinstance(config, dict) or set(config) != {'schemaVersion', 'sources'}
            or config['schemaVersion'] != 'offmenu-worker61-bindings/1'
            or not isinstance(config['sources'], list) or len(config['sources']) > 32):
        raise ValueError('portfolio-config-invalid')
    results = []
    seen = set()
    for entry in config['sources']:
        if not isinstance(entry, dict):
            results.append({'status': 'malformed', 'diagnostics': ['binding-schema-invalid']})
            continue
        result = bind(entry, root, clock)
        if result['status'] == 'malformed':
            results.append(result)
            continue
        identity = (result.get('sourceId'), result.get('releaseId'))
        if identity in seen:
            result.update(status='invalid')
            result['diagnostics'].append('duplicate-source-release-binding')
        seen.add(identity)
        results.append(result)
    return {'schemaVersion': 'offmenu-worker61-binding-report/1',
            'configSha256': fingerprint(config), 'evaluatedAt': now,
            'results': results, 'networkRequests': 0, 'sourceBodyReads': 0,
            'countryAccepted': False, 'goldAccepted': False,
            'requiredCountryTypes': {country: {domain: 'not-accepted'
                                    for domain in DOMAINS} for country in COUNTRIES},
            'sharedInterfaces': ['core.strict_json', 'core.timestamp',
                                 'acceptance.fingerprint', 'adapter_mapping.retained_adapters',
                                 'field_provenance.field_origin_errors'],
            'nextStage': 'Morgan selects source-qualified shared adapter/validator; no automatic execution'}


def write_report(path, report):
    """Identical report is a byte-preserving no-op; changed report needs new path."""
    path = safe_path(path)
    body = canonical(report)
    if path.exists():
        if read_regular(path, len(body)) != body:
            raise ValueError('report-exists-with-different-input-or-clock')
        return 'no-op'
    with path.open('xb') as stream:
        stream.write(body)
    return 'written'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--metadata-root', required=True, type=Path)
    parser.add_argument('--now', required=True, help='Explicit UTC clock; never file mtime')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = read_regular(args.config, 262144)
    except (OSError, ValueError):
        parser.error('config-not-bounded-regular-file')
    report = assess(strict_json(raw), args.metadata_root, now=args.now)
    outcome = write_report(args.output, report)
    print(json.dumps({'outcome': outcome, 'reportSha256': fingerprint_bytes(canonical(report)),
                      'sourceBodyReads': 0, 'countryAccepted': False}, sort_keys=True))


if __name__ == '__main__':
    main()
