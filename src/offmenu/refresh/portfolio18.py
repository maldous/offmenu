"""Worker18 metadata bindings. No acquisition, parser, writer or admission path.

The bundled catalogue is reviewed application configuration, never a discovery
manifest supplied by a caller. Diagnostics verify metadata assertions only;
input hashes below are declarations, not a claim to have verified source bytes.
"""
import argparse
import sys

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .global_run import StageResult
from .national_tabular import valid_input_name
from .field_provenance import field_origin_errors

MAX_METADATA = 65536
from .portfolio18_catalogue import BINDINGS
FIELDS = {'schemaVersion', 'bindingId', 'sourceId', 'releaseId', 'inputs',
          'originalAcquiredAt', 'validatedAt'}


def catalogue():
    """Only the installed, code-reviewed catalogue; no caller-selected policy."""
    return strict_json(canonical(BINDINGS))


def request_for(binding_id, validated_at):
    """Prepare metadata assertions; validated_at never re-ages an acquisition."""
    spec = catalogue()['bindings'][binding_id]
    return {'schemaVersion': 'offmenu-portfolio18-metadata/1',
            'bindingId': binding_id, 'sourceId': spec['sourceId'],
            'releaseId': spec['releaseId'], 'inputs': spec['inputs'],
            'originalAcquiredAt': spec['originalAcquiredAt'],
            'validatedAt': validated_at}


def _inspect(spec, raw, *, now, previous_plan=None):
    """Bounded pure diagnostic; private spec parameter supports authored tests.

Returns the shared StageResult receipt but never installs a GlobalRun Binding
or SourceContract. 'ready' means metadata shape only, never dataset acceptance.
"""
    def result(state, code, *, plan=None, age=None, validation_age=None):
        status = {'ready': 'succeeded', 'no-op': 'reused', 'missing': 'unsupported',
                  'held': 'held', 'stale': 'held', 'malformed': 'failed'}[state]
        return {'schemaVersion': 'offmenu-portfolio18-diagnostic/1',
                'bindingId': spec['bindingId'], 'state': state,
                'stage': StageResult(status, code, (plan,) if plan else ()).receipt(),
                'planSha256': plan, 'holds': spec['holds'],
                'dependencies': spec['dependencies'],
                'inputAgeSeconds': age, 'metadataValidationAgeSeconds': validation_age,
                'minimumReuseSeconds': MIN_TTL,
                'sourceBytesVerified': False, 'admission': 'not-assessed',
                'sourceProcessingDispatched': False, 'countryComplete': False}

    if raw is None:
        return result('missing', 'metadata-input-missing')
    if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
        return result('malformed', 'metadata-input-invalid')
    try:
        current = timestamp(now)
        manifest = strict_json(raw)
        canonical(manifest)  # Also rejects overflowing/nonfinite JSON numbers.
        if not isinstance(manifest, dict) or set(manifest) != FIELDS:
            raise ValueError()
        expected = {'schemaVersion': 'offmenu-portfolio18-metadata/1',
                    'bindingId': spec['bindingId'], 'sourceId': spec['sourceId'],
                    'releaseId': spec['releaseId'], 'inputs': spec['inputs'],
                    'originalAcquiredAt': spec['originalAcquiredAt']}
        if any(manifest[key] != value for key, value in expected.items()):
            raise ValueError()
        if (not spec['inputs'] or any(not valid_input_name(name) for name in spec['inputs'])
                or any(not isinstance(pin, str) or len(pin) != 64
                       or any(c not in '0123456789abcdef' for c in pin)
                       for pin in spec['inputs'].values())):
            raise ValueError()
        checked = timestamp(manifest['validatedAt'])
        original = manifest['originalAcquiredAt']
        acquired = timestamp(original) if original is not None else None
        if checked > current or (acquired is not None and (acquired > checked)):
            raise ValueError()
        validation_age = int((current - checked).total_seconds())
        age = int((current - acquired).total_seconds()) if acquired else None
        # Validation time is observational and deliberately excluded from replay
        # identity. Scope, rights/holds, field declarations and pins are included.
        plan = sha(canonical({'contract': spec, 'input': expected}))
        if previous_plan is not None and (not isinstance(previous_plan, str)
                or len(previous_plan) != 64
                or any(c not in '0123456789abcdef' for c in previous_plan)):
            raise ValueError()
    except (RefreshError, ValueError, TypeError, KeyError, UnicodeError, OverflowError,
            RecursionError):
        return result('malformed', 'metadata-contract-invalid')
    if spec['holds']:
        return result('held', 'portfolio-source-held', plan=plan, age=age,
                      validation_age=validation_age)
    if acquired is None:
        return result('missing', 'original-acquisition-time-missing', plan=plan,
                      validation_age=validation_age)
    if age >= MIN_TTL:
        return result('stale', 'input-revalidation-required', plan=plan, age=age,
                      validation_age=validation_age)
    if spec['dependencies']:
        return result('missing', 'staging-dependency-missing', plan=plan, age=age,
                      validation_age=validation_age)
    return result('no-op' if previous_plan == plan else 'ready',
                  'metadata-plan-unchanged' if previous_plan == plan else 'metadata-binding-valid',
                  plan=plan, age=age, validation_age=validation_age)


def inspect(binding_id, raw, *, now, previous_plan=None):
    """Public route selects a fixed portfolio binding, never caller policy."""
    spec = catalogue()['bindings'][binding_id]
    return _inspect(spec, raw, now=now, previous_plan=previous_plan)


def origin_diagnostics(binding_id, row):
    """Shared structural coverage checks, never a real selector/value verdict.

Future reviewed projections can consume the declared input pins/selectors. Their
semantic callback must additionally verify the actual cells. The current task
does not execute this against retained rows and installs no production callback.
"""
    spec = catalogue()['bindings'][binding_id]
    return {'structuralErrors': field_origin_errors(row, spec['inputs']),
            'selectorSemantics': 'unsupported-until-reviewed-projection',
            'sourceAccepted': False, 'holds': spec['holds']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', required=True, choices=sorted(catalogue()['bindings']))
    parser.add_argument('--now', required=True, help='Explicit UTC diagnostic time')
    parser.add_argument('--previous-plan')
    args = parser.parse_args(argv)
    # Pipe only the bounded metadata envelope on stdin. No user-selected file,
    # source path, URL, command, dynamic plugin or output-directory capability.
    raw = sys.stdin.buffer.read(MAX_METADATA + 1)
    receipt = inspect(args.binding, raw or None, now=args.now,
                      previous_plan=args.previous_plan)
    sys.stdout.buffer.write(canonical(receipt))
    return 0 if receipt['state'] in ('ready', 'no-op') else 2


if __name__ == '__main__':
    raise SystemExit(main())
