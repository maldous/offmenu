"""Pure retained-input planning; no cache, file, network or admission actions.

Callers still verify the actual input and satisfy their source contracts. Cache
age and unchanged-content replay are separate observations: a later validation
does not reset original acquisition, and an elapsed window does not change the
content key. Neither observation grants permission to process a source.
"""
from .acquisition import MIN_TTL
from .core import HEX, RefreshError, canonical, sha, timestamp

SCHEMA = 'offmenu-retained-input-plan/1'


def _digest(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def _clock(value):
    try:
        return timestamp(value)
    except (ValueError, TypeError):
        raise RefreshError('retained-plan-invalid-time') from None


def plan_retained_input(*, source_id, release_id, input_pins, policy_sha256,
                        scope_sha256, original_acquired_at, now,
                        validated_at=None, previous_key=None,
                        ttl_seconds=MIN_TTL, holds=()):
    """Plan from declarations only; input pins map logical names to hash/bytes.

    Identity includes source, release, exact input pins, reviewed policy/scope,
    original acquisition, TTL and holds. Current and validation clocks are
    observations, never identity. ``unchanged-no-op`` describes identity only;
    it does not assert freshness, input verification, rights or acceptance.
    """
    if (not isinstance(source_id, str) or not source_id.strip()
            or not isinstance(release_id, str) or not release_id.strip()
            or not _digest(policy_sha256) or not _digest(scope_sha256)):
        raise RefreshError('retained-plan-invalid-identity')
    if type(ttl_seconds) is not int or ttl_seconds < MIN_TTL:
        raise RefreshError('retained-plan-invalid-ttl')
    if previous_key is not None and not _digest(previous_key):
        raise RefreshError('retained-plan-invalid-previous-key')
    if (not isinstance(holds, (list, tuple))
            or any(not isinstance(h, str) or not h.strip() for h in holds)):
        raise RefreshError('retained-plan-invalid-holds')
    if (not isinstance(input_pins, dict) or not input_pins
            or any(not isinstance(k, str) or not k.strip() for k in input_pins)):
        raise RefreshError('retained-plan-invalid-input-pins')
    pins = {}
    for name, pin in input_pins.items():
        if (not isinstance(pin, dict) or set(pin) != {'sha256', 'bytes'}
                or not _digest(pin['sha256']) or type(pin['bytes']) is not int
                or pin['bytes'] <= 0):
            raise RefreshError('retained-plan-invalid-input-pins')
        pins[name] = {'sha256': pin['sha256'], 'bytes': pin['bytes']}

    current = _clock(now)
    original = None if original_acquired_at is None else _clock(original_acquired_at)
    validated = None if validated_at is None else _clock(validated_at)
    if (original is not None and original > current
            or validated is not None and validated > current
            or original is not None and validated is not None and validated < original):
        raise RefreshError('retained-plan-invalid-clock-order')
    identity = {'schemaVersion': SCHEMA, 'sourceId': source_id,
                'releaseId': release_id, 'inputPins': pins,
                'policySha256': policy_sha256, 'scopeSha256': scope_sha256,
                'originalAcquiredAt': original.isoformat() if original else None,
                'ttlSeconds': ttl_seconds, 'holds': sorted(set(holds))}
    key = sha(canonical(identity))
    age = (current - original).total_seconds() if original else None
    cache = ('held' if holds else 'original-acquisition-time-missing' if original is None
             else 'reuse-retained' if age < ttl_seconds else 'revalidation-required')
    replay = ('held' if holds else 'first-plan' if previous_key is None
              else 'unchanged-no-op' if previous_key == key else 'changed')
    return {'schemaVersion': SCHEMA, 'identity': identity, 'key': key,
            'cacheDecision': cache, 'replayDecision': replay,
            'acquisitionAgeSeconds': age,
            'validatedAt': validated.isoformat() if validated else None,
            'validationAgeSeconds': (current - validated).total_seconds() if validated else None,
            'requiresInputVerification': True, 'networkAllowed': False,
            'dataAdmissionAllowed': False}
