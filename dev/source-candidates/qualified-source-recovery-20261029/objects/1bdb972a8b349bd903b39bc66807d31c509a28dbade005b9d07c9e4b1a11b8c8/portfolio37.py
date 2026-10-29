"""NP/PK/PS/SK metadata bindings. Never opens a source body or admits data.

The only filesystem inputs are this authored config and its exact allowlisted
small validation/acquisition receipts. Native selectors are declarations, not
executed source parsers. Shared provenance, serialization and pin checks are used.
"""
import argparse
from copy import deepcopy
import io
from pathlib import Path

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp, verify
from .field_provenance import datum_pointers, field_origin_errors
from .serialization import encode_records

CONFIG = Path(__file__).with_name('portfolio37_bindings.json')
COUNTRIES = ('NP', 'PK', 'PS', 'SK')
MAX_METADATA_BYTES = 256 * 1024


def bindings():
    """Reviewed-code configuration boundary, never a CLI-supplied admission."""
    raw = CONFIG.read_bytes()
    document = strict_json(raw)
    if (document['schemaVersion'] != 'offmenu-portfolio37-bindings/1'
            or tuple(row['country'] for row in document['rows']) != COUNTRIES):
        raise RefreshError('portfolio-config-invalid')
    return document, sha(raw)


def metadata_records():
    """Stage authored binding metadata, not retained dataset observations.

    Every datum points to the authored JSON config. Native source declarations
    separately name pinned evidence; these origins never claim source-body reads.
    """
    document, digest = bindings()
    rows = []
    for index, profile in enumerate(document['rows']):
        data = deepcopy(profile)
        origins = {pointer: {
            'kind': 'source', 'sourceId': profile['sourceId'],
            'releaseId': profile['releaseId'], 'inputPath': CONFIG.name,
            'inputSha256': digest, 'sourceRecordId': profile['country'],
            'sourceField': '/rows/' + str(index) + pointer[len('/data'):],
        } for pointer in datum_pointers(data)}
        row = {'id': profile['sourceId'] + ':metadata-binding',
               'kind': 'source-input-binding-metadata', 'schemaVersion': '1.0',
               'provenance': {'sourceId': profile['sourceId'],
                              'releaseId': profile['releaseId'],
                              'fetchedAt': document['authoredAt'],
                              'timestampMeaning': 'authored-binding-config-not-original-acquisition',
                              'inputSha256': digest, 'fieldOrigins': origins,
                              'scope': 'authored-metadata-not-source-data'},
               'data': data}
        if field_origin_errors(row, {CONFIG.name: digest}):
            raise RefreshError('portfolio-metadata-origin-invalid')
        rows.append(row)
    return rows


def observe_metadata(profile, *, checked_at):
    """Verify only two bounded metadata documents; original paths are inert.

    These allowlisted pins are authored configuration. No arbitrary path, raw
    payload, retained candidate body, parser execution or network route is taken.
    """
    documents = {}
    for key in ('validationReceipt', 'acquisitionReceipt'):
        pin = profile[key]
        path = safe_path(pin['path'])
        size = path.stat().st_size
        if not 0 < size <= MAX_METADATA_BYTES:
            raise RefreshError('portfolio-metadata-size-limit')
        raw = path.read_bytes()
        if len(raw) != size or sha(raw) != pin['sha256']:
            raise RefreshError('portfolio-metadata-pin-mismatch')
        # Recheck the exact bytes/pin with the shared race-aware verifier.
        verify(path, {'bytes': size, 'sha256': pin['sha256']})
        documents[key] = strict_json(raw)
    declaration = documents['validationReceipt']['actualSourceValidation']['input']
    if declaration != profile['original']:
        raise RefreshError('portfolio-original-declaration-mismatch')
    return {'sourceId': profile['sourceId'], 'releaseId': profile['releaseId'],
            'inputSha256': declaration['sha256'], 'inputBytes': declaration['bytes'],
            'metadataSha256': profile['validationReceipt']['sha256'],
            'acquisitionReceiptSha256': profile['acquisitionReceipt']['sha256'],
            'originalAcquiredAt': profile['originalAcquiredAt'],
            'metadataCheckedAt': checked_at, 'status': 'present'}


def assess_input(profile, observation, *, now):
    """Pure metadata/cache plan; checking metadata never resets acquisition age.

    No age or supplied observation authorizes a source-body action. A stale item
    requests review only, while an unchanged metadata build can still be reused.
    Missing custody alone is never represented as a legal prohibition.
    """
    result = {'country': profile['country'], 'sourceId': profile['sourceId'],
              'outcome': 'valid', 'diagnostics': [],
              'blockers': deepcopy(profile['blockers']),
              'additionalInputBindings': deepcopy(profile['additionalInputBindings']),
              'minimumReuseDays': MIN_TTL // 86400,
              'originalAcquiredAt': profile['originalAcquiredAt'],
              'metadataCheckedAt': None, 'acquisitionAgeDays': None,
              'cacheDecision': 'acquisition-time-unestablished-no-download',
              'cachePlannerCapability': 'portfolio-metadata-intent-only',
              'sharedPurePlanner': 'unavailable-at-pinned-develop',
              'bodyBytesVerified': False, 'bodyProcessingAuthorized': False,
              'acceptedRecords': 0, 'goldAdmitted': False, 'networkRequests': 0}
    diagnostics = result['diagnostics']
    if observation is None:
        result.update(outcome='missing')
        diagnostics.append('metadata-input-missing')
        return result
    if not isinstance(observation, dict):
        result.update(outcome='malformed')
        diagnostics.append('metadata-input-malformed')
        return result
    expected = {'sourceId': profile['sourceId'], 'releaseId': profile['releaseId'],
                'inputSha256': profile['original']['sha256'],
                'inputBytes': profile['original']['bytes'],
                'metadataSha256': profile['validationReceipt']['sha256'],
                'acquisitionReceiptSha256': profile['acquisitionReceipt']['sha256'],
                'originalAcquiredAt': profile['originalAcquiredAt']}
    if (any(observation.get(k) != v or type(observation.get(k)) is not type(v)
            for k, v in expected.items())
            or set(observation) != set(expected) | {'metadataCheckedAt', 'status'}
            or observation.get('status') not in ('present', 'held')):
        diagnostics.append('metadata-binding-mismatch')
    try:
        current = timestamp(now)
        checked = timestamp(observation.get('metadataCheckedAt'))
        if checked > current:
            raise RefreshError('metadata-check-in-future')
        result['metadataCheckedAt'] = observation['metadataCheckedAt']
        acquired = profile['originalAcquiredAt']
        if acquired is None:
            diagnostics.append('original-acquisition-time-unestablished')
        else:
            original = timestamp(acquired)
            age = (current - original).total_seconds()
            if age < 0 or checked < original:
                raise RefreshError('invalid-acquisition-order')
            result['acquisitionAgeDays'] = int(age // 86400)
            result['cacheDecision'] = ('reuse-retained-input-no-download' if age < MIN_TTL
                                       else 'conditional-refresh-review-no-download')
            if age >= MIN_TTL:
                diagnostics.append('retained-input-stale-review-required')
    except (ValueError, TypeError, OverflowError):
        diagnostics.append('metadata-time-invalid')
    invalid = set(diagnostics) - {'original-acquisition-time-unestablished',
                                  'retained-input-stale-review-required'}
    result['outcome'] = ('malformed' if invalid else
                         'held' if observation.get('status') == 'held' else
                         'missing' if profile['originalAcquiredAt'] is None else
                         'stale' if result['acquisitionAgeDays'] >= MIN_TTL // 86400 else 'valid')
    result['diagnostics'] = sorted(set(diagnostics))
    return result


def assess_portfolio(observations, *, now):
    """All four independent results survive peer failure, with fixed diagnostics."""
    document, config_digest = bindings()
    results = []
    for profile in document['rows']:
        try:
            row = assess_input(profile, observations.get(profile['country']), now=now)
        except Exception:
            # Do not copy exception text, paths, response content or credentials.
            row = {'country': profile['country'], 'sourceId': profile['sourceId'],
                   'outcome': 'malformed', 'diagnostics': ['metadata-contract-invalid'],
                   'bodyProcessingAuthorized': False, 'acceptedRecords': 0}
        results.append(row)
    return {'schemaVersion': 'offmenu-portfolio37-plan/1', 'configSha256': config_digest,
            'scope': 'metadata-only', 'sources': results, 'networkRequests': 0,
            'acceptedCountryDomainCells': 0, 'countryComplete': False}


def publish_metadata(path):
    """One deterministic metadata artifact; identical replay leaves it untouched.

    Changed output uses a new caller-selected location; frozen artifacts are never
    replaced. This is local metadata publication, not source/data acceptance.
    """
    from .global_run import stream_report, write_report
    path = safe_path(path)
    report = {'schemaVersion': 'offmenu-portfolio37-metadata/1',
              'records': metadata_records()}
    stream = io.BytesIO()
    digest, size = stream_report(report, stream)
    payload = stream.getvalue()
    if path.exists():
        if path.stat().st_size == len(payload) and path.read_bytes() == payload:
            return {'decision': 'reused-noop', 'sha256': sha(payload), 'bytes': len(payload)}
        raise RefreshError('portfolio-output-conflict')
    # Reuse the existing exclusive metadata report publisher. JSONL packet
    # serialization remains available separately through the shared encoder.
    digest, size = write_report(report, path)
    return {'decision': 'written', 'sha256': digest, 'bytes': size}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Metadata-only NP/PK/PS/SK bindings; no source bodies or network.')
    parser.add_argument('--now', required=True, help='Explicit UTC validation clock; not acquisition time.')
    parser.add_argument('--verify-retained-metadata', action='store_true')
    parser.add_argument('--output-metadata', help='Exclusive local authored-metadata report; identical replay is a no-op.')
    args = parser.parse_args(argv)
    try:
        timestamp(args.now)
        document, _ = bindings()
        observations = {}
        if args.verify_retained_metadata:
            for profile in document['rows']:
                try:
                    observations[profile['country']] = observe_metadata(profile, checked_at=args.now)
                except (OSError, ValueError, KeyError):
                    observations[profile['country']] = {'status': 'unavailable-or-invalid'}
        report = assess_portfolio(observations, now=args.now)
        report['metadataCandidateSha256'] = sha(encode_records(metadata_records()))
        if args.output_metadata:
            report['publication'] = publish_metadata(args.output_metadata)
    except (OSError, ValueError, KeyError):
        report = {'schemaVersion': 'offmenu-portfolio37-error/1',
                  'diagnostics': ['portfolio-metadata-invalid'], 'networkRequests': 0}
    print(canonical(report).decode(), end='')
    return 0 if report.get('sources') and all(
        row['outcome'] != 'malformed' for row in report['sources']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
