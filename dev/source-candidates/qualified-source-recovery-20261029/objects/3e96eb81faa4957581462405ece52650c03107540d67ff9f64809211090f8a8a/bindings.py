"""Read pinned receipt metadata, never source bodies or manifest-supplied code.

The Binding objects are reviewed application configuration. A metadata-ready
result is not a parser, SourceContract, acquisition permission or STAGING pass.
"""
from dataclasses import dataclass
import argparse
from pathlib import Path

from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.core import HEX, RefreshError, canonical, sha, strict_json, timestamp, safe_path
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.global_run import StageResult

MAX_METADATA = 1024 * 1024
POLICY = sha(canonical({'owner': 50, 'scope': 'receipt-metadata-only',
                        'unknown': 'unresolved-not-imputed', 'version': 1}))


@dataclass(frozen=True)
class Binding:
    country: str
    source_id: str
    release_id: str
    receipt_path: str
    receipt_sha256: str
    fields: tuple  # (output name, exact receipt JSON pointer or None)
    holds: tuple
    dependencies: tuple
    fixture: bool = False
    data_types: tuple = ()  # Intended source/type applicability, never coverage acceptance.


def pointer(value, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('pointer-invalid')
    for token in path.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def read_receipt(binding):
    """Only the trusted binding's exact JSON receipt can be opened."""
    path = safe_path(Path(binding.receipt_path))
    if path.name != 'receipt.json':
        raise RefreshError('portfolio-receipt-name-invalid')
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_METADATA + 1)
    except FileNotFoundError:
        return None
    if len(raw) > MAX_METADATA:
        raise RefreshError('portfolio-metadata-limit')
    return raw


def inspect(binding, raw, *, now, validated_at=None, previous_key=None):
    """Deterministic, bounded metadata projection with isolated fixed codes.

    Time is explicit. Validation observations never reset original acquisition
    age, enter the replay key, or make a cached source body verified.
    """
    result = {'schemaVersion': 'offmenu-portfolio50-binding/1',
              'country': binding.country, 'sourceId': binding.source_id,
              'releaseId': binding.release_id, 'fixture': binding.fixture,
              'intendedDataTypes': list(binding.data_types),
              'applicabilityAccepted': False,
              'status': 'malformed', 'diagnostics': [], 'record': None,
              'bindingKey': None, 'replay': 'blocked', 'networkRequests': 0,
              'sourceBodyAccess': 'not-selected', 'stagingAccepted': False,
              'countryComplete': False,
              'interfaces': {'realSourceAdapter': 'unsupported',
                             'pureSharedCachePlanner': 'unsupported',
                             'plannerDependency': 'integrator00-proposal-only'}}
    errors = set()
    if raw is None:
        result.update(status='missing-input', diagnostics=['receipt-missing'])
        return result
    try:
        if not isinstance(binding, Binding) or not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            raise ValueError()
        if sha(raw) != binding.receipt_sha256:
            errors.add('receipt-pin-mismatch')
            raise ValueError()
        receipt = strict_json(raw)
        if not isinstance(receipt, dict):
            raise ValueError()
        clock = timestamp(now)
        observed = timestamp(validated_at or now)
        if observed > clock:
            errors.add('validation-time-in-future')
        data, origins = {}, {}
        field_names = [name for name, _ in binding.fields]
        if len(field_names) != len(set(field_names)):
            raise ValueError()
        for name, coordinate in binding.fields:
            missing = coordinate is None
            try:
                value = None if missing else pointer(receipt, coordinate)
            except (KeyError, IndexError, TypeError, ValueError):
                value, missing = None, True
            data[name] = value
            if missing:
                errors.add('metadata-field-unresolved-' + name.lower())
            escaped = name.replace('~', '~0').replace('/', '~1')
            for target in datum_pointers(value, '/data/' + escaped):
                suffix = target[len('/data/' + escaped):]
                origins[target] = ({'kind': 'constant', 'policySha256': POLICY,
                                    'symbol': 'unresolved-not-imputed'} if missing else
                                   {'kind': 'source', 'sourceId': binding.source_id,
                                    'releaseId': binding.release_id, 'inputPath': 'receipt.json',
                                    'inputSha256': binding.receipt_sha256,
                                    'sourceRecordId': 'receipt', 'sourceField': coordinate + suffix})
        if data.get('country') != binding.country or data.get('release') != binding.release_id:
            errors.add('source-release-or-country-mismatch')
        if (type(data.get('originalBytes')) is not int or data['originalBytes'] <= 0
                or not isinstance(data.get('originalSHA256'), str)
                or not HEX.fullmatch(data['originalSHA256'])):
            raise ValueError()
        acquired = timestamp(data.get('acquiredAt'))
        if not acquired <= observed <= clock:
            errors.add('acquisition-observation-order-invalid')
        age = (clock - acquired).total_seconds()
        row = {'id': binding.source_id + ':receipt', 'kind': 'sourceInputMetadata',
               'schemaVersion': '1.0', 'data': data,
               'provenance': {'sourceId': binding.source_id, 'releaseId': binding.release_id,
                              'fetchedAt': data.get('acquiredAt'), 'fieldOrigins': origins}}
        errors.update(field_origin_errors(row, {'receipt.json': binding.receipt_sha256},
                                         policy_pins=(POLICY,)))
        key = sha(canonical({'country': binding.country, 'sourceId': binding.source_id,
                             'releaseId': binding.release_id, 'receipt': binding.receipt_sha256,
                             'fields': binding.fields, 'holds': binding.holds,
                             'dependencies': binding.dependencies, 'fixture': binding.fixture,
                             'dataTypes': binding.data_types,
                             'policy': POLICY}))
        result.update(record=row, bindingKey=key,
                      originalAcquiredAt=data.get('acquiredAt'),
                      metadataValidatedAt=validated_at or now,
                      acquisitionAgeDays=int(age // 86400),
                      validationAgeDays=int((clock - observed).total_seconds() // 86400),
                      minimumReuseDays=MIN_TTL // 86400,
                      cache={'owner': 'offmenu.refresh.acquisition.CachedAcquirer',
                             'decision': 'retain-metadata-zero-download' if age < MIN_TTL
                             else 'revalidation-review-required-no-download',
                             'bodyVerified': False, 'mtimeUsed': False,
                             'revalidationResetsAcquisitionAge': False})
        if binding.holds:
            errors.update(binding.holds)
            status = 'held'
        elif errors:
            status = 'missing-input'
        elif age >= MIN_TTL:
            errors.add('original-input-stale')
            status = 'stale-input'
        else:
            status = 'metadata-ready'
        result.update(status=status, diagnostics=sorted(errors),
                      remainingDependencies=list(binding.dependencies),
                      replay=('unchanged-no-op' if previous_key == key else 'metadata-projection-ready')
                      if status == 'metadata-ready' else 'blocked')
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        result.update(status='malformed', diagnostics=sorted(errors | {'metadata-contract-invalid'}),
                      record=None, replay='blocked')
    return result


def assess_many(bindings, metadata, *, now, validated_at=None, previous_keys=None):
    """One malformed/missing country cannot suppress the other diagnostics."""
    previous_keys = previous_keys or {}
    return [inspect(b, metadata.get(b.country), now=now, validated_at=validated_at,
                    previous_key=previous_keys.get(b.country)) for b in bindings]


def stage_interface(report):
    """Use the shared stage envelope without claiming a source stage passed."""
    return StageResult('unsupported', 'portfolio-metadata-only',
                       evidence=(sha(canonical(report)),), observed_count=None)


def main(argv=None):
    from .profiles import bindings
    parser = argparse.ArgumentParser(description='Pinned receipt metadata only; no body/refresh path.')
    parser.add_argument('--now', required=True, help='UTC ISO timestamp, explicit for replay')
    args = parser.parse_args(argv)
    output = []
    for binding in bindings():
        try:
            report = inspect(binding, read_receipt(binding), now=args.now)
        except (OSError, RefreshError):
            report = inspect(binding, None, now=args.now)
            report['diagnostics'] = ['receipt-unavailable-or-unsafe']
        output.append(report)
    print(canonical({'schemaVersion': 'offmenu-portfolio50-report/1', 'bindings': output}).decode(), end='')
    return 0 if all(r['status'] == 'metadata-ready' for r in output) else 2


if __name__ == '__main__':
    # profiles imports the canonical Binding class. Running this file with -m
    # otherwise creates a second __main__.Binding type and rejects every profile.
    from offmenu.portfolio50.bindings import main as entrypoint
    raise SystemExit(entrypoint())
