"""CA/CY/CZ/DE metadata bindings; never read payloads or enable admissions.

Repository CLI: python -m offmenu.refresh.portfolio26 --now <UTC timestamp>.
Shared adapters own parsing, SourceContract owns qualification, and Morgan/00
own any future execution. This module only binds pinned JSON metadata.
"""
import argparse
import os
from pathlib import Path
import re
import stat

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .capabilities import RELEASES
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .execution import ADAPTERS
from .global_run import StageResult
from .field_provenance import field_origin_errors
from .national_tabular import national_semantic_errors

CONFIG = Path(__file__).resolve().parents[2] / 'config/portfolio26-bindings.json'
MAX_METADATA_BYTES = 128 * 1024
COUNTRIES = ('CA', 'CY', 'CZ', 'DE')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
HEX = re.compile('[0-9a-f]{64}')


def _read_metadata(reference):
    if (not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}
            or not isinstance(reference['path'], str)
            or not isinstance(reference['sha256'], str)
            or not HEX.fullmatch(reference['sha256'])
            or Path(reference['path']).suffix != '.json'):
        raise RefreshError('portfolio-metadata-pin-invalid')
    path = safe_path(reference['path'])
    # Authenticate only the bounded bytes read from this one regular descriptor.
    # Nonblocking open also makes a concurrent FIFO replacement fail promptly.
    before = path.lstat()
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise RefreshError('regular-file-required')
        if fields(before) != fields(opened):
            raise RefreshError('portfolio-metadata-stale')
        if opened.st_size > MAX_METADATA_BYTES:
            raise RefreshError('asset-size-limit-exceeded')
        blocks, consumed = [], 0
        while True:
            block = os.read(fd, min(65536, MAX_METADATA_BYTES + 1 - consumed))
            if not block:
                break
            consumed += len(block)
            if consumed > MAX_METADATA_BYTES:
                raise RefreshError('asset-size-limit-exceeded')
            blocks.append(block)
        after = os.fstat(fd)
        try:
            current = safe_path(path).lstat()
        except FileNotFoundError:
            raise RefreshError('portfolio-metadata-stale') from None
        if fields(opened) != fields(after) or fields(after) != fields(current):
            raise RefreshError('portfolio-metadata-stale')
        raw = b''.join(blocks)
    finally:
        os.close(fd)
    if sha(raw) != reference['sha256']:
        raise RefreshError('portfolio-metadata-stale')
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise RefreshError('portfolio-metadata-malformed')
    return value


def configuration(path=CONFIG):
    """Read reviewed repository configuration, not a SourceContract constructor."""
    path = safe_path(path)
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise RefreshError('portfolio-config-too-large')
    result = strict_json(path.read_bytes())
    if (not isinstance(result, dict) or result.get('schemaVersion') != 'portfolio26-bindings/1'
            or result.get('countries') != list(COUNTRIES)
            or not isinstance(result.get('bindings'), list)):
        raise RefreshError('portfolio-config-invalid')
    return result


def cache_metadata(binding, *, now):
    """Age observations only: no shared pure cache planner exists at this base.

    MIN_TTL and timestamp rules come from the shared acquisition/core contract.
    This does not recreate or invoke CachedAcquirer, including its explicit
    revalidate/force-download modes. Production transport is never supplied.
    """
    observed = timestamp(now)
    acquired = binding.get('originalAcquiredAt')
    validated = binding.get('validationObservedAt')
    if validated is not None and timestamp(validated) > observed:
        raise RefreshError('portfolio-validation-in-future')
    result = {'originalAcquiredAt': acquired, 'validationObservedAt': validated,
              'minimumReuseSeconds': MIN_TTL, 'minimumReuseDays': 30,
              'validationResetsAcquisitionAge': False, 'mtimeUsed': False,
              'networkRequests': 0, 'decision': 'unsupported-shared-cache-planner',
              'sharedPlanner': None, 'retentionWindow': 'unknown-acquisition-time',
              'runtimeReuseVerified': False}
    if acquired is not None:
        age = (observed - timestamp(acquired)).total_seconds()
        if age < 0:
            raise RefreshError('portfolio-acquisition-in-future')
        result.update(acquisitionAgeSeconds=int(age),
                      retentionWindow='under-30-days' if age < MIN_TTL
                      else '30-days-or-older')
    return result


def _descriptor_errors(binding):
    if not isinstance(binding, dict):
        return ['portfolio-binding-invalid']
    errors = []
    for key in ('bindingId', 'sourceId', 'releaseId'):
        if not isinstance(binding.get(key), str) or not binding[key]:
            errors.append('portfolio-identity-missing')
    if binding.get('country') not in COUNTRIES:
        errors.append('portfolio-country-invalid')
    if (not isinstance(binding.get('types'), list) or not binding['types']
            or any(t not in TYPES for t in binding['types'])):
        errors.append('portfolio-type-invalid')
    if not isinstance(binding.get('holds'), list) or any(not isinstance(x, str) or not x for x in binding['holds']):
        errors.append('portfolio-holds-invalid')
    if not isinstance(binding.get('origins'), list) or not isinstance(binding.get('unknowns'), list):
        errors.append('portfolio-field-declarations-invalid')
    elif (any(not isinstance(x, dict) or not isinstance(x.get('field'), str)
              or not isinstance(x.get('sourceSelector'), str) for x in binding['origins'])
          or any(not isinstance(x, str) for x in binding['unknowns'])):
        errors.append('portfolio-field-declarations-invalid')
    if not isinstance(binding.get('provenanceEvidence', []), list):
        errors.append('portfolio-evidence-list-invalid')
    return sorted(set(errors))


def inspect_binding(binding, *, now, previous_key=None):
    """Non-mutating metadata inspection. Held descriptors perform no file I/O.

    A successful stage means metadata references bound, never data qualification,
    source-body permission, acquired bytes, accepted rows or country completion.
    """
    errors = _descriptor_errors(binding)
    if errors:
        return {'stage': StageResult('failed', errors[0]).receipt(), 'errors': errors}
    result = {k: binding[k] for k in ('bindingId', 'sourceId', 'releaseId', 'country', 'types', 'origins', 'unknowns')}
    result.update(bodyOperations=[], acceptedRecords=None, countryComplete=False,
                  metadataBytesVerified=False, payloadBytesVerified=False,
                  fieldOriginsStatus='declared-not-row-verified',
                  rightsOperationsReviewedByThisTool=False,
                  qualificationContract=None, processingAdmission='not-installed')
    if binding['holds']:
        result.update(stage=StageResult('held', 'source-held').receipt(),
                      holds=binding['holds'], errors=[], packageAction='held-no-read')
        return result
    reference = binding.get('manifest')
    if reference is None:
        result.update(stage=StageResult('unsupported', 'portfolio-manifest-missing').receipt(),
                      errors=['portfolio-manifest-missing'], packageAction='missing-no-read')
        return result
    try:
        cache = cache_metadata(binding, now=now)
        manifest = _read_metadata(reference)
        identity = binding.get('manifestIdentity')
        if (not isinstance(identity, dict) or not identity
                or any(manifest.get(k) != v for k, v in identity.items())):
            raise RefreshError('portfolio-source-release-mismatch')
        adapter = binding.get('sharedAdapter')
        if adapter is not None:
            release = next((r for r in RELEASES if r['sourceId'] == adapter), None)
            if adapter not in ADAPTERS or release is None or release['releaseId'] != binding['releaseId']:
                raise RefreshError('portfolio-shared-adapter-mismatch')
            if (manifest.get('sourceId') != adapter or binding['sourceId'] != adapter
                    or manifest.get('releaseId') != binding['releaseId']):
                raise RefreshError('portfolio-source-release-mismatch')
        references = binding.get('provenanceEvidence', []) + [
            x['evidence'] for x in binding['origins'] if 'evidence' in x]
        seen_evidence = set()
        for evidence in references:
            # Different pins for the same locator must not silently collapse.
            identity = fingerprint(evidence)
            if identity not in seen_evidence:
                _read_metadata(evidence)
                seen_evidence.add(identity)
        # This is a descriptor identity, not an admission/cache-payload digest.
        key = fingerprint({k: v for k, v in binding.items()
                           if k not in ('validationObservedAt', 'originalAcquiredAt')})
        result.update(stage=StageResult('succeeded', 'portfolio-metadata-bound',
                                       (reference['sha256'], key)).receipt(),
                      errors=[], cache=cache, bindingKey=key,
                      packageAction='metadata-no-op' if previous_key == key else 'metadata-reference-bound',
                      metadataBytesVerified=True, manifest=reference,
                      metadataEvidencePinsVerified=len(seen_evidence),
                      sharedAdapter=adapter,
                      adapterStatus='available-not-admitted' if adapter else 'shared-adapter-not-bound',
                      dependencies=binding.get('dependencies', []),
                      provenanceEvidence=binding.get('provenanceEvidence', []))
    except (OSError, ValueError, TypeError, OverflowError) as error:
        code = str(error) if isinstance(error, RefreshError) else 'portfolio-metadata-malformed'
        # Never expose filesystem paths, source values or exception strings.
        if not re.fullmatch('[a-z][a-z0-9-]{0,95}', code):
            code = 'portfolio-metadata-malformed'
        status = 'quarantined' if code == 'portfolio-metadata-stale' else 'failed'
        if isinstance(error, FileNotFoundError):
            status, code = 'unsupported', 'portfolio-manifest-missing'
        result.update(stage=StageResult(status, code).receipt(), errors=[code], packageAction='not-bound')
    return result


def plan(config, *, now, previous_keys=None):
    previous_keys = previous_keys or {}
    rows = []
    for binding in config['bindings']:
        identity = binding.get('bindingId') if isinstance(binding, dict) else None
        previous = previous_keys.get(identity) if isinstance(identity, str) and identity else None
        rows.append(inspect_binding(binding, now=now, previous_key=previous))
    cells = []
    for country in COUNTRIES:
        for category in TYPES:
            ids = [b['bindingId'] for b in config['bindings']
                   if isinstance(b, dict) and isinstance(b.get('bindingId'), str)
                   and b['bindingId'] and b.get('country') == country
                   and isinstance(b.get('types'), list) and category in b['types']]
            cells.append({'country': country, 'type': category, 'bindings': ids,
                          'status': 'candidate-binding-only' if ids else 'missing-source-binding',
                          'accepted': False})
    return {'schemaVersion': 'portfolio26-plan/1', 'bindings': rows, 'countryTypes': cells,
            'sourceBodyReads': 0, 'networkRequests': 0, 'acceptedCountryTypes': 0,
            'scope': 'metadata-only; no parse, refresh, staging data or acceptance executed'}


def diagnose_authored_profile(source, row):
    """Opt-in test/diagnostic interface for SMALL AUTHORED fixtures only.

    No file reader and no production all-record semantic callback is installed.
    These two unit allowlists exercise shared machinery, not real-release review.
    """
    if source not in ('cnf', 'germany-bls'):
        return ['portfolio-fixture-source-unsupported']
    return national_semantic_errors(source, row, allowed_units=('g', 'mg', 'µg', 'kcal', 'kJ'),
                                    basis_units=('g',))


def diagnose_authored_origins(row, input_pins, *, policy_pins=()):
    """Shared per-datum origin interface, for small authored fixture diagnostics.

    Portfolio selector declarations are not expanded into fake per-record origins.
    Real emission requires a separately reviewed source-coordinate serializer.
    """
    return field_origin_errors(row, input_pins, policy_pins=policy_pins)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC assessment time for deterministic output')
    args = parser.parse_args(argv)
    timestamp(args.now)
    print(canonical(plan(configuration(), now=args.now)).decode(), end='')


if __name__ == '__main__':
    main()
