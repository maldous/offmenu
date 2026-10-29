"""Fixed portfolio binding of retained derived inputs; no acquisition or admission.

Only authored fixtures or the separately pinned private SB derivative are inputs.
No HTML/PDF parser, registry entry, dynamic plugin, writer or network client lives
here. Shared field-origin validation and canonical serialization remain owners of
their contracts. A caller must separately obtain review before materialization.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import stat
import sys

from .core import canonical, sha
from .field_provenance import field_origin_errors
from .serialization import encode_records

CONFIG = Path(__file__).with_name('owner20_bindings.json')
FIELDS = ('sourceItemId', 'sourceSelector', 'rawDisplay', 'amountDecimal',
          'currencySymbol', 'isoCurrency', 'effectiveDate', 'servingPackageQuantity', 'normalization')
UNKNOWN = ('isoCurrency', 'effectiveDate', 'servingPackageQuantity')
MAX_INPUT_BYTES = 2 * 1024**2
READ_ERRORS = frozenset(('derived-input-not-regular', 'derived-input-too-large',
                         'derived-input-changed-during-read', 'derived-input-unavailable',
                         'metadata-contract-invalid'))


class BindingError(ValueError):
    pass


def read_derived_input(path):
    """Bounded regular-file read on one nonblocking, no-follow descriptor.

    Walk directories by descriptors too: a renamed path cannot redirect a later
    reopen, and symlinks at any component cannot select another source body.
    """
    directory = descriptor = None
    try:
        parts = Path(os.path.abspath(path)).parts
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        directory = os.open('/', flags | os.O_DIRECTORY)
        for part in parts[1:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], flags, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BindingError('derived-input-not-regular')
        if before.st_size > MAX_INPUT_BYTES:
            raise BindingError('derived-input-too-large')
        blocks, consumed = [], 0
        while True:
            block = os.read(descriptor, min(65536, MAX_INPUT_BYTES + 1 - consumed))
            if not block:
                break
            blocks.append(block)
            consumed += len(block)
            if consumed > MAX_INPUT_BYTES:
                raise BindingError('derived-input-too-large')
        after = os.fstat(descriptor)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or consumed != before.st_size:
            raise BindingError('derived-input-changed-during-read')
        return b''.join(blocks)
    except OSError as exc:
        raise BindingError('derived-input-unavailable') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def candidate_depth_check(candidate):
    pending, visited = [(candidate, 0)], 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > 32 or visited > 100000:
            raise BindingError('candidate-structure-limit-exceeded')
        if isinstance(value, dict):
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value)


def country_id(binding):
    country = binding.get('country') if isinstance(binding, dict) else None
    if not isinstance(country, str) or country not in ('NG', 'PA', 'PH', 'SB'):
        raise BindingError('binding-country-invalid')
    return country


def malformed(country, code):
    return {'country': country, 'status': 'malformed', 'diagnostics': [code],
            'networkRequests': 0, 'sourceBodiesRead': 0, 'acceptedRecords': 0,
            'goldAdmitted': 0, 'countryComplete': False, 'nextOnlineStep': 'none'}


def utc(value):
    if not isinstance(value, str):
        raise BindingError('timestamp-invalid')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise BindingError('timestamp-invalid') from exc
    if result.tzinfo is None:
        raise BindingError('timestamp-invalid')
    return result.astimezone(timezone.utc)


def bind_sb(candidate, *, input_sha256, source_id, release_id):
    """Pure projection of a derived candidate, with pointers into that derivative.

    Original HTML coordinates are retained as literal data, not asserted to have
    been re-read or independently revalidated. Source selectors are never guessed.
    """
    candidate_depth_check(candidate)
    if not isinstance(candidate, dict) or candidate.get('country') != 'SB':
        raise BindingError('candidate-country-invalid')
    if candidate.get('schema') != 'offmenu-private-source-faithful-menu-normalized-candidate/2':
        raise BindingError('candidate-schema-invalid')
    items = candidate.get('records')
    observations = candidate.get('priceObservations')
    if not isinstance(items, list) or not items or not isinstance(observations, list) or not observations:
        raise BindingError('candidate-inventory-invalid')
    if len(items) > 1000 or len(observations) > 5000:
        raise BindingError('candidate-limit-exceeded')
    ids = [item.get('sourceItemId') for item in items if isinstance(item, dict)]
    if len(ids) != len(items) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise BindingError('candidate-item-identities-invalid')
    rows = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict) or any(key not in observation for key in FIELDS):
            raise BindingError('observation-fields-missing')
        if observation['sourceItemId'] not in ids:
            raise BindingError('observation-item-unresolved')
        if not isinstance(observation['normalization'], str) or not observation['normalization']:
            raise BindingError('observation-normalization-invalid')
        if any(observation[key] is not None for key in UNKNOWN):
            raise BindingError('unknown-marker-changed')
        if any(not isinstance(observation[key], str) or not observation[key]
               for key in ('sourceSelector', 'rawDisplay', 'currencySymbol')):
            raise BindingError('observation-source-coordinate-invalid')
        value = observation['amountDecimal']
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
            raise BindingError('display-decimal-invalid')
        try:
            if not Decimal(value).is_finite():
                raise BindingError('display-decimal-invalid')
        except InvalidOperation as exc:
            raise BindingError('display-decimal-invalid') from exc
        if 'variantLabel' in observation and observation['variantLabel'] is not None and not isinstance(observation['variantLabel'], str):
            raise BindingError('variant-label-invalid')
        fields = FIELDS + (('variantLabel',) if 'variantLabel' in observation else ())
        data = {key: observation[key] for key in fields}
        origins = {'/data/' + key: {
            'kind': 'source', 'sourceId': source_id, 'releaseId': release_id,
            'inputPath': 'menu-normalized-candidate.json', 'inputSha256': input_sha256,
            'sourceRecordId': observation['sourceItemId'],
            'sourceField': '/priceObservations/' + str(index) + '/' + key,
        } for key in fields}
        warnings = candidate.get('sourcePunctuationWarnings', [])
        if not isinstance(warnings, list) or any(not isinstance(w, dict) or not isinstance(w.get('issue'), str) for w in warnings):
            raise BindingError('source-warning-invalid')
        data['sourceWarnings'] = []
        for warning_index, warning in enumerate(warnings):
            if warning.get('sourceItemId') == observation['sourceItemId']:
                pointer = '/data/sourceWarnings/' + str(len(data['sourceWarnings']))
                data['sourceWarnings'].append(warning['issue'])
                origins[pointer] = dict(origins['/data/sourceItemId'], sourceField='/sourcePunctuationWarnings/' + str(warning_index) + '/issue')
        row = {'id': 'SB:display-price:' + str(index), 'data': data,
               'provenance': {'sourceId': source_id, 'releaseId': release_id,
                              'fieldOrigins': origins}}
        if field_origin_errors(row, {'menu-normalized-candidate.json': input_sha256}):
            raise BindingError('shared-field-origin-validation-failed')
        rows.append(row)
    return rows


def assess_country(binding, *, now, candidate_bytes=None, previous=None):
    """Return isolated fixed diagnostics and an evidence-only replay decision.

    No file/network access. Validation time never supplies acquisition time.
    Stale means review required, never permission to fetch or discard old data.
    """
    try:
        country = country_id(binding)
    except BindingError:
        return malformed(None, 'binding-country-invalid')
    result = {'country': country, 'status': 'missing', 'diagnostics': [],
              'networkRequests': 0, 'sourceBodiesRead': 0, 'acceptedRecords': 0,
              'goldAdmitted': 0, 'countryComplete': False, 'nextOnlineStep': 'none'}
    try:
        if binding.get('state') in ('held', 'missing'):
            result.update(status=binding['state'], diagnostics=binding['requirements'])
            return result
        if binding.get('country') != 'SB' or binding.get('state') != 'derived-input-only':
            raise BindingError('binding-state-invalid')
        instant = utc(now)
        acquired = utc(binding['originalAcquiredAt'])
        validated = utc(binding['metadataValidatedAt'])
        age = (instant - acquired).total_seconds()
        if age < 0 or validated < acquired or validated > instant:
            raise BindingError('evidence-chronology-invalid')
        result.update(acquisitionAgeDays=int(age // 86400),
                      metadataValidationAgeDays=int((instant - validated).total_seconds() // 86400),
                      minimumReuseDays=30, revalidationResetsAcquisitionAge=False)
        if age >= 30 * 86400:
            result.update(status='stale-input', diagnostics=['revalidation-review-required-no-download'])
            return result
        if candidate_bytes is None:
            result['diagnostics'] = ['derived-input-not-supplied']
            return result
        if len(candidate_bytes) > MAX_INPUT_BYTES:
            raise BindingError('derived-input-too-large')
        digest = sha(candidate_bytes)
        if digest != binding['input']['sha256']:
            raise BindingError('derived-input-pin-mismatch')
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise BindingError('duplicate-json-key')
                obj[key] = value
            return obj
        candidate = json.loads(candidate_bytes, object_pairs_hook=unique,
                               parse_constant=lambda _: (_ for _ in ()).throw(BindingError('nonfinite-json')))
        rows = bind_sb(candidate, input_sha256=digest, source_id=binding['sourceId'], release_id=binding['releaseId'])
        if len(candidate['records']) != binding['expectedItems'] or len(rows) != binding['expectedObservations']:
            raise BindingError('inventory-count-mismatch')
        content = sha(encode_records(rows))
        implementation = sha(Path(__file__).read_bytes())
        shared = {name: sha(Path(__file__).with_name(name).read_bytes()) for name in
                  ('core.py', 'field_provenance.py', 'serialization.py')}
        key = sha(canonical({'binding': binding, 'implementation': implementation, 'shared': shared,
                             'pythonRuntime': [sys.implementation.name, list(sys.version_info)]}))
        replay = {'bindingKey': key, 'contentSha256': content}
        result.update(status='valid', decision='no-op' if previous == replay else 'ready-for-independent-review',
                      derivedItems=len(candidate['records']), mappedObservations=len(rows),
                      fieldOriginErrors=0, replay=replay, materialized=False,
                      candidateAcceptance='not-performed', publicExport=False)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        result.update(status='malformed', diagnostics=[str(exc) if isinstance(exc, BindingError) else 'metadata-contract-invalid'])
    return result


def assess_portfolio(bindings, *, now, inputs=None, previous=None, input_errors=None):
    inputs, previous = inputs or {}, previous or {}
    input_errors = input_errors or {}
    results = []
    for binding in bindings:
        country = None
        try:
            country = country_id(binding)
            if country in input_errors:
                code = input_errors[country]
                raise BindingError(code if isinstance(code, str) and code in READ_ERRORS
                                   else 'metadata-contract-invalid')
            result = assess_country(binding, now=now, candidate_bytes=inputs.get(country),
                                    previous=previous.get(country))
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
            result = malformed(country, str(exc) if isinstance(exc, BindingError) else 'metadata-contract-invalid')
        results.append(result)
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Aware ISO timestamp; explicit reproducible evidence clock')
    parser.add_argument('--verify-retained-derived', action='store_true', help='Read only the fixed SB derived candidate; never raw HTML/PDF')
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    inputs, errors = {}, {}
    if args.verify_retained_derived:
        sb = next((b for b in config['bindings'] if isinstance(b, dict) and b.get('country') == 'SB'), None)
        if sb is not None:
            try:
                inputs['SB'] = read_derived_input(sb['input']['path'])
            except (ValueError, TypeError, KeyError) as exc:
                errors['SB'] = str(exc) if isinstance(exc, BindingError) else 'metadata-contract-invalid'
    print(json.dumps({'schemaVersion': 'offmenu-owner20-staging-binding-report/1',
                      'results': assess_portfolio(config['bindings'], now=args.now, inputs=inputs, input_errors=errors)},
                     sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
