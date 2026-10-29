"""AU/IR/PN metadata preflight, not a payload reader or admission registry.

Trusted application code supplies a spec; manifests cannot release its holds.
Uses shared strict JSON, timestamps, provenance diagnostics and stage receipts.
No declared source path is opened. OS isolation remains the integrator's boundary.
"""
import argparse
import json
from pathlib import Path

from .acceptance import fingerprint
from .core import RefreshError, strict_json, timestamp
from .field_provenance import field_origin_errors
from .global_run import StageResult

CATALOGUE = Path(__file__).resolve().parents[2] / 'docs/operations/portfolio-au-ir-pn.json'
MAX_METADATA = 256 * 1024


def catalogue():
    return strict_json(CATALOGUE.read_bytes())


def origin_errors(row, input_pins, *, policy_pins=()):
    """Shared origin coverage check only; source-cell/transform fidelity separate."""
    return field_origin_errors(row, input_pins, policy_pins=policy_pins)


def inspect_metadata(spec, envelope, *, now, previous_key=None):
    """Pure bounded preflight; key permits caller-owned no-op, never cache writes.

    All output is metadata-only. Success does not prove any body exists or matches
    its declared digest. originalAcquiredAt controls the 30-day boundary; later
    validation must not reset it. At/after 30 days, require review, no download.
    """
    codes = set()
    key = None
    age = None
    try:
        if envelope is None:
            return {'schemaVersion': 'offmenu-au-ir-pn-metadata-preflight/1',
                    'bindingId': spec['bindingId'],
                    'stage': StageResult('unsupported', 'source-input-missing').receipt(),
                    'diagnostics': ['source-input-missing'], 'holds': list(spec.get('holds', ())),
                    'cacheDecision': 'unknown-no-download',
                    'plannerCapability': 'metadata-intent-only-generic-planner-unsupported',
                    'networkRequests': 0, 'sourceBodyReads': 0,
                    'inputBytesVerified': False, 'countryAccepted': False,
                    'productionAdmission': False}
        if not isinstance(envelope, dict):
            raise ValueError
        if len(json.dumps(envelope, allow_nan=False).encode()) > MAX_METADATA:
            raise ValueError
        required = {'sourceId', 'releaseId', 'country', 'dataType', 'inputs',
                    'evidenceSha256', 'originalAcquiredAt', 'validatedAt'}
        if set(envelope) != required:
            raise ValueError
        for name in ('sourceId', 'releaseId', 'country', 'dataType'):
            if envelope[name] != spec[name]:
                codes.add('binding-identity-mismatch')
        inputs = envelope['inputs']
        if not isinstance(inputs, dict):
            raise ValueError
        if not spec['inputs'] or not inputs:
            codes.add('source-input-missing')
        if inputs != spec['inputs']:
            codes.add('input-declaration-mismatch')
        if envelope['evidenceSha256'] != spec['metadataEvidence']['sha256']:
            codes.add('metadata-evidence-pin-mismatch')
        if envelope['originalAcquiredAt'] != spec['originalAcquiredAt']:
            codes.add('acquisition-evidence-mismatch')
        if spec['originalAcquiredAt'] is None:
            # Unknown acquisition is a held dependency, not a fabricated clock.
            acquired = None
        else:
            acquired = timestamp(envelope['originalAcquiredAt'])
        validated = timestamp(envelope['validatedAt'])
        if now.tzinfo is None or not validated <= now or (acquired is not None and acquired > validated):
            codes.add('metadata-clock-invalid')
        age = None if acquired is None else (now - acquired).total_seconds()
        if age is not None and age < 0:
            codes.add('metadata-clock-invalid')
        # Validation time excluded: a fresh check is not a fresh acquisition.
        key = fingerprint({'spec': spec, 'input': {
            k: v for k, v in envelope.items() if k != 'validatedAt'}})
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        codes.add('metadata-malformed')

    holds = list(spec.get('holds', ()))
    stale = age is not None and age >= 30 * 86400
    if codes:
        status, code = 'failed', sorted(codes)[0]
    elif holds:
        status, code = 'held', 'portfolio-source-held'
    elif stale:
        status, code = 'held', 'stale-input-review-required'
    else:
        status = 'reused' if previous_key == key else 'succeeded'
        code = 'metadata-no-op' if status == 'reused' else 'metadata-binding-ready'
    return {
        'schemaVersion': 'offmenu-au-ir-pn-metadata-preflight/1',
        'bindingId': spec['bindingId'],
        'stage': StageResult(status, code, (key,) if key else ()).receipt(),
        'diagnostics': sorted(codes), 'holds': holds,
        'bindingKey': key, 'minimumReuseDays': 30,
        'acquisitionAgeDays': None if age is None else int(age // 86400),
        'cacheDecision': ('unknown-no-download' if age is None else
                          'review-required-no-download' if stale else 'retained-input-only'),
        'plannerCapability': 'metadata-intent-only-generic-planner-unsupported',
        'inputBytesVerified': False, 'mtimeUsed': False,
        'validationResetsAcquisitionAge': False, 'networkRequests': 0,
        'sourceBodyReads': 0, 'countryAccepted': False,
        'productionAdmission': False,
    }


def inspect_batch(envelopes, *, now, previous_keys=None):
    """Each declared portfolio source receives its own isolated diagnostic."""
    if not isinstance(envelopes, dict):
        raise RefreshError('metadata-batch-invalid')
    known = {p['bindingId'] for p in catalogue()['profiles']}
    if not set(envelopes) <= known:
        raise RefreshError('unknown-portfolio-binding')
    return [inspect_metadata(p, envelopes.get(p['bindingId']), now=now,
                             previous_key=(previous_keys or {}).get(p['bindingId']))
            for p in catalogue()['profiles']]


def main(argv=None):
    parser = argparse.ArgumentParser(description='AU/IR/PN metadata only; no source reads/network.')
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--now', required=True, help='Explicit UTC timestamp for repeatable assessment')
    args = parser.parse_args(argv)
    try:
        # Read only the explicitly supplied small metadata envelope, not its paths.
        with open(args.metadata, 'rb') as stream:
            raw = stream.read(MAX_METADATA + 1)
        if len(raw) > MAX_METADATA:
            raise RefreshError('metadata-bound-exceeded')
        rows = inspect_batch(strict_json(raw), now=timestamp(args.now))
        result = {'sources': rows, 'networkRequests': 0, 'countryAccepted': False}
        exit_code = 0 if all(r['stage']['status'] in ('succeeded', 'reused') for r in rows) else 2
    except (OSError, ValueError, TypeError, RecursionError):
        result, exit_code = {'errorCode': 'portfolio-metadata-input-invalid', 'networkRequests': 0}, 2
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
