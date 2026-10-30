"""Finite, data-only external-effect and selected-phase projection (schema 1).

The authenticated connector owner supplies immutable expected bindings, approved
observer identity, exact observation digest, separate acceptance evidence and a
trusted clock. Untrusted JSON cannot grant authority. Validation is neither
authentication nor independent evidence issuance: callers must establish those
facts outside this module. No credentials, paths, logs, graph writes, integration
actions, Windmill success or umbrella Done state are consumed or produced.

Deployment/byte evidence does not establish source acceptance, functionality or
owner/child completion. The gateway remains the connector owner's context, not
a deployed Windmill publisher. All references here are detached metadata only.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Literal


Axis = Literal['source_acceptance', 'candidate_binding', 'deployment',
               'served_bytes', 'functional_acceptance', 'lifecycle']
AXES = ('source_acceptance', 'candidate_binding', 'deployment', 'served_bytes',
        'functional_acceptance', 'lifecycle')


def _text(value, pattern, limit):
    if type(value) is not str or len(value) > limit or not re.fullmatch(pattern, value):
        raise ValueError('Invalid bounded identity or hash')


def _hash(value, size=64):
    _text(value, '[0-9a-f]{%d}' % size, size)


def _time(value):
    if type(value) not in (int, float) or not 0 <= value <= 10**12 or not math.isfinite(value):
        raise ValueError('Invalid timestamp')


def _fields(value, names):
    if type(value) is not dict or value.keys() != set(names):
        raise ValueError('Unexpected or missing fields')


@dataclass(frozen=True)
class AssetPin:
    name: str
    sha256: str

    def __post_init__(self):
        _text(self.name, r'/[A-Za-z0-9_-]+(?:[./-][A-Za-z0-9_-]+)*', 128)
        _hash(self.sha256)


@dataclass(frozen=True)
class EffectBinding:
    request_id: str
    owner: str
    source_commit: str
    package_sha256: str
    version_number: int
    version_id: str
    deployment_id: str
    assets: tuple[AssetPin, ...]

    def __post_init__(self):
        for value in (self.request_id, self.owner):
            _text(value, r'[A-Za-z0-9][A-Za-z0-9_.:-]*', 128)
        _hash(self.source_commit, 40)
        _hash(self.package_sha256)
        if type(self.version_number) is not int or not 1 <= self.version_number <= 10**9:
            raise ValueError('Invalid version number')
        for value in (self.version_id, self.deployment_id):
            _text(value, r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', 36)
        if (type(self.assets) is not tuple or not 1 <= len(self.assets) <= 16
                or any(type(pin) is not AssetPin for pin in self.assets)
                or len({pin.name for pin in self.assets}) != len(self.assets)):
            raise ValueError('Expected asset pins must be nonempty, unique and immutable')


@dataclass(frozen=True)
class TrustedEvidence:
    """Owner-attested reference, never parsed from the untrusted observation.

    sha256 binds the entire canonical JSON observation for deployment evidence.
    Other axes reference separate independently established evidence. Lifecycle
    requires explicit owner/child states; neither is inferred from effect-known.
    """
    axis: Axis
    binding: EffectBinding
    observer: str
    sha256: str
    owner_state: Literal['unknown', 'terminal'] = 'unknown'
    child_state: Literal['unknown', 'gone'] = 'unknown'

    def __post_init__(self):
        if type(self.axis) is not str or self.axis not in AXES or type(self.binding) is not EffectBinding:
            raise ValueError('Invalid evidence binding or axis')
        _text(self.observer, r'[A-Za-z0-9][A-Za-z0-9_.:-]*', 128)
        _hash(self.sha256)
        if (type(self.owner_state) is not str or self.owner_state not in ('unknown', 'terminal')
                or type(self.child_state) is not str or self.child_state not in ('unknown', 'gone')):
            raise ValueError('Invalid lifecycle state')
        if self.axis != 'lifecycle' and (self.owner_state, self.child_state) != ('unknown', 'unknown'):
            raise ValueError('Lifecycle evidence must be separate')


@dataclass(frozen=True)
class EffectContext:
    """Trusted caller context; absence of an approved observer grants no trust.

    Freshness is caller-controlled (1..3600 seconds), never record-controlled.
    Evidence tuples and bindings contain only frozen, bounded scalar metadata.
    """
    expected: EffectBinding
    now: float
    max_age_seconds: int
    approved_observer: str | None = None
    evidence: tuple[TrustedEvidence, ...] = ()

    def __post_init__(self):
        if type(self.expected) is not EffectBinding:
            raise ValueError('Invalid expected binding')
        _time(self.now)
        if type(self.max_age_seconds) is not int or not 1 <= self.max_age_seconds <= 3600:
            raise ValueError('Invalid freshness bound')
        if self.approved_observer is not None:
            _text(self.approved_observer, r'[A-Za-z0-9][A-Za-z0-9_.:-]*', 128)
        if (type(self.evidence) is not tuple or len(self.evidence) > 4
                or any(type(item) is not TrustedEvidence for item in self.evidence)):
            raise ValueError('Invalid trusted evidence')
        axes, digests = set(), set()
        for item in self.evidence:
            if (item.axis not in ('deployment', 'source_acceptance', 'functional_acceptance', 'lifecycle')
                    or item.binding != self.expected or item.observer != self.approved_observer
                    or item.axis in axes or item.sha256 in digests):
                raise ValueError('Conflicting, reused or unrelated trusted evidence')
            axes.add(item.axis)
            digests.add(item.sha256)


def observation_digest(observation: dict) -> str:
    """Canonical ordinary-JSON digest; call only after bounded shape validation.

    The owner must obtain this digest independently, not echo candidate claims.
    """
    return hashlib.sha256(json.dumps(observation, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def project_effect(observation: dict, context: EffectContext,
                   phases: tuple[Axis, ...] = ()) -> dict:
    """Validate one observation and close only explicitly selected supported phases.

    Input fields are exact: schema_version, binding (identity scalars excluding
    expected assets), observed_at (Unix seconds), receipt_sha256, assets (list of
    name/sha256/raw_sha256/status). Normalized hashes never prove raw equality.
    Missing raw_sha256 uses JSON null and leaves served-byte acceptance unknown.
    Returns fresh ordinary JSON, without retaining caller-owned containers.
    """
    if type(context) is not EffectContext:
        raise ValueError('Expected separate caller trust context')
    if (type(phases) is not tuple or len(phases) > len(AXES)
            or any(type(phase) is not str or phase not in AXES for phase in phases)
            or len(set(phases)) != len(phases)):
        raise ValueError('Invalid selected phases')
    _fields(observation, ('schema_version', 'binding', 'observed_at', 'receipt_sha256', 'assets'))
    if type(observation['schema_version']) is not int or observation['schema_version'] != 1:
        raise ValueError('Invalid schema version')
    expected = asdict(context.expected)
    expected.pop('assets')
    binding = observation['binding']
    _fields(binding, expected)
    # Strict scalar types reject bool/int aliasing and nested arbitrary objects.
    if any(type(binding[key]) is not type(value) or binding[key] != value
           for key, value in expected.items()):
        raise ValueError('Observation binding mismatch')
    _hash(observation['receipt_sha256'])
    observed_at = observation['observed_at']
    _time(observed_at)
    if not 0 <= context.now - observed_at <= context.max_age_seconds:
        raise ValueError('Stale or future observation')
    assets = observation['assets']
    if type(assets) is not list or len(assets) != len(context.expected.assets):
        raise ValueError('Missing or extra asset pins')
    pins = {pin.name: pin.sha256 for pin in context.expected.assets}
    normalized, raw, seen = True, True, set()
    for asset in assets:
        _fields(asset, ('name', 'sha256', 'raw_sha256', 'status'))
        name = asset['name']
        if type(name) is not str or name not in pins or name in seen:
            raise ValueError('Unexpected or duplicate asset pin')
        seen.add(name)
        _hash(asset['sha256'])
        if asset['sha256'] != pins[name]:
            raise ValueError('Asset pin mismatch')
        if asset['raw_sha256'] is not None:
            _hash(asset['raw_sha256'])
        if type(asset['status']) is not int or not 100 <= asset['status'] <= 599:
            raise ValueError('Invalid asset status')
        normalized &= asset['sha256'] == pins[name] and asset['status'] == 200
        raw &= asset['raw_sha256'] == pins[name] and asset['status'] == 200
    evidence = {item.axis: item for item in context.evidence}
    deployed = evidence.get('deployment')
    if deployed and deployed.sha256 != observation_digest(observation):
        raise ValueError('Observation digest mismatch')
    axes = {axis: 'unknown' for axis in AXES}
    axes['lifecycle'] = {'owner': 'unknown', 'child': 'unknown'}
    if deployed:
        axes.update(candidate_binding='bound', deployment='observed',
                    served_bytes='equal' if raw else 'unknown')
    for axis in ('source_acceptance', 'functional_acceptance'):
        if axis in evidence:
            axes[axis] = 'accepted'
    if 'lifecycle' in evidence:
        item = evidence['lifecycle']
        axes['lifecycle'] = {'owner': item.owner_state, 'child': item.child_state}
    supported = {axis: value != 'unknown' for axis, value in axes.items() if axis != 'lifecycle'}
    supported['lifecycle'] = axes['lifecycle'] == {'owner': 'terminal', 'child': 'gone'}
    projected_binding = asdict(context.expected)
    projected_binding['assets'] = list(projected_binding['assets'])
    return {'schema_version': 1, 'binding': projected_binding,
            'receipt_sha256': observation['receipt_sha256'], 'axes': axes,
            'normalized_pins_match': bool(deployed and normalized),
            'phases': {axis: ('closed' if axis in phases and supported[axis] else 'open')
                       for axis in AXES},
            'evidence': {axis: item.sha256 for axis, item in evidence.items()},
            'authority': 'observation_only'}
