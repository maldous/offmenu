"""CF/BY/CC/CD metadata bindings only; never open or admit source payloads.

Run: python -m offmenu.refresh.portfolio22 CF evidence.json --now UTC_TIMESTAMP
Configuration is reviewed code, not a manifest-installed source admission.
"""
from copy import deepcopy
import argparse
import os
from pathlib import Path
import stat

from .core import RefreshError, canonical, safe_path, strict_json, timestamp
from .acquisition import MIN_TTL
from .acceptance import fingerprint
from .global_run import StageResult
from .serialization import encode_records
from .field_provenance import datum_pointers, field_origin_errors
from ._portfolio22_catalogue import CATALOGUE, CONFIG_SHA256


# Documentary checkout mirror; installed defaults use the inert catalogue.
CONFIG = Path(__file__).resolve().parents[2] / 'config/source-bindings/portfolio22.json'
MAX_METADATA = 128 * 1024
EVIDENCE_KEYS = {'schemaVersion', 'country', 'sourceId', 'releaseId', 'assets',
                 'originalAcquiredAt', 'lastValidatedAt', 'fieldOrigins', 'held'}


def profiles():
    """Fixed shipped configuration; cannot install an ADMISSIONS entry."""
    return deepcopy(CATALOGUE['profiles'])


def expected_evidence(country):
    """Metadata template, not proof the declared files exist or were validated."""
    p = profiles()[country]
    return {'schemaVersion':'portfolio22-input-evidence/1', 'country':country,
            'sourceId':p['sourceId'], 'releaseId':p['releaseId'],
            'assets':deepcopy(p['assets']), 'originalAcquiredAt':p['originalAcquiredAt'],
            'lastValidatedAt':None, 'fieldOrigins':deepcopy(p['fieldOrigins']), 'held':False}


def _report(state, code, *, key=None, record=None, cache=None, blockers=()):
    status = {'ready':'succeeded', 'no-op':'reused', 'missing':'unsupported',
              'held':'held', 'malformed':'failed', 'stale':'quarantined'}[state]
    evidence = (key,) if key else ()
    # Shared StageResult checks status, fixed code and evidence shape.
    stage = StageResult(status, code, evidence).receipt()
    return {'schemaVersion':'portfolio22-staging-binding/1', 'state':state,
            'stage':stage, 'bindingKey':key, 'record':record, 'cache':cache,
            'remainingBlockers':list(blockers), 'networkRequests':0,
            'sourceBytesVerified':False, 'sourceProcessingAllowed':False,
            'datasetAccepted':False, 'goldAdmitted':False}


def assess(country, evidence, *, now, previous_key=None):
    """Deterministic binding/age plan; validates metadata without dereferencing pins.

    Freshness uses original acquisition, never a file mtime or validation-age reset.
    The key excludes clocks; unchanged pins/semantics permit an explicit no-op.
    A stale input requires a separately selected conditional review, never download.
    """
    try:
        config_pin = CONFIG_SHA256
        p = profiles().get(country)
        if p is None:
            return _report('malformed', 'portfolio-country-unsupported')
        # JSON round trip refuses nonfinite/non-JSON values; no coercion or mutation.
        e = strict_json(canonical(evidence))
        if not isinstance(e, dict) or set(e) != EVIDENCE_KEYS:
            return _report('malformed', 'metadata-fields-invalid')
        if (e['schemaVersion'] != 'portfolio22-input-evidence/1'
                or type(e['held']) is not bool
                or e['country'] != country
                or e['sourceId'] != p['sourceId'] or e['releaseId'] != p['releaseId']):
            return _report('malformed', 'source-release-or-gate-mismatch')
        if e['held']:
            return _report('held', 'metadata-source-held', blockers=p['dataBlockers'])
        if p['originalAcquiredAt'] is None:
            return _report('missing', 'retained-original-or-use-binding-missing', blockers=p['dataBlockers'])
        if not isinstance(e['assets'], list):
            return _report('malformed', 'metadata-assets-invalid')
        if not e['assets'] or e['fieldOrigins'] is None or e['lastValidatedAt'] is None:
            return _report('missing', 'metadata-evidence-missing')
        if (e['assets'] != p['assets'] or e['fieldOrigins'] != p['fieldOrigins']
                or e['originalAcquiredAt'] != p['originalAcquiredAt']):
            return _report('malformed', 'pin-selector-or-acquisition-mismatch')
        current = timestamp(now)
        acquired = timestamp(e['originalAcquiredAt'])
        validated = timestamp(e['lastValidatedAt'])
        if not acquired <= validated <= current:
            return _report('malformed', 'metadata-clock-order-invalid')
        if previous_key is not None and (not isinstance(previous_key, str)
                or len(previous_key) != 64 or any(c not in '0123456789abcdef' for c in previous_key)):
            return _report('malformed', 'previous-binding-key-invalid')
        key = fingerprint({'bindingVersion':'portfolio22/1', 'profile':p,
                           'configSha256':config_pin})
        age = (current-acquired).total_seconds()
        cache = {'minimumReuseDays':MIN_TTL//86400,
                 'originalAcquisitionAgeDays':int(age//86400),
                 'validationAgeDays':int((current-validated).total_seconds()//86400),
                 'validationResetsAcquisitionAge':False, 'mtimeUsed':False,
                 'automaticDownloadAllowed':False, 'aiRefreshAllowed':False,
                 'decision':'reuse-declared-retained-input' if age < MIN_TTL
                            else 'conditional-review-required-no-download'}
        if age >= MIN_TTL:
            return _report('stale', 'source-cache-revalidation-required', key=key,
                           cache=cache, blockers=p['dataBlockers'])
        record = {'id':'portfolio22-binding:'+country, 'schemaVersion':'1.0',
                  'kind':'source-input-binding',
                  'provenance':{'sourceId':p['sourceId'], 'releaseId':p['releaseId'],
                                'fetchedAt':p['originalAcquiredAt']},
                  'data':deepcopy(p)}
        # Every metadata datum originates in the exact shipped configuration.
        # This does NOT authenticate the underlying CSV selector declarations.
        record['provenance']['fieldOrigins'] = {
            pointer:{'kind':'source', 'sourceId':p['sourceId'], 'releaseId':p['releaseId'],
                     'inputPath':'portfolio22.json', 'inputSha256':config_pin,
                     'sourceRecordId':'profiles/'+country,
                     'sourceField':'/profiles/'+country+pointer[len('/data'):]}
            for pointer in datum_pointers(record['data'])}
        record['provenance']['fieldOriginScope'] = 'binding-config-metadata-only'
        if field_origin_errors(record, {'portfolio22.json':config_pin}):
            return _report('malformed', 'metadata-field-origin-invalid')
        return _report('no-op' if previous_key == key else 'ready',
                       'binding-unchanged' if previous_key == key else 'metadata-binding-ready',
                       key=key, record=record, cache=cache, blockers=p['dataBlockers'])
    except (ValueError, TypeError, OverflowError, KeyError):
        return _report('malformed', 'metadata-invalid')


def candidate_bytes(report):
    """Shared singleton-array JSONL framing, for this METADATA record only."""
    if report['state'] not in ('ready', 'no-op') or report['record'] is None:
        raise RefreshError('metadata-binding-not-ready')
    return encode_records([report['record']])


def _read_metadata(path):
    """Read only one regular descriptor, capped even if the file grows."""
    path = safe_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_METADATA:
            raise RefreshError('metadata-bound')
        raw = bytearray()
        while len(raw) <= MAX_METADATA:
            chunk = os.read(descriptor, MAX_METADATA + 1 - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > MAX_METADATA:
            raise RefreshError('metadata-bound')
        return bytes(raw)
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('country', choices=('CF','BY','CC','CD'))
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--now', required=True, help='Explicit UTC timestamp')
    parser.add_argument('--previous-key')
    args = parser.parse_args()
    try:
        raw = _read_metadata(args.evidence)
        result = assess(args.country, strict_json(raw), now=args.now,
                        previous_key=args.previous_key)
    except (OSError, ValueError, TypeError):
        result = _report('malformed', 'metadata-input-unreadable')
    print(canonical(result).decode(), end='')
    return 0 if result['state'] in ('ready', 'no-op') else 2


if __name__ == '__main__':
    raise SystemExit(main())
