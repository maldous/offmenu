"""Check an offline destination binding, not publication permission."""
from dataclasses import dataclass
import re

from native_harness_contract import fingerprint, validate_release_candidate
from release_qualification import SHA, fields, require

# Opaque metadata identifiers, not URLs, arguments or credential values.
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
DESTINATION_FIELDS = ('channel', 'environment', 'account_id', 'destination_id')
PROOF_FIELDS = (
    'destination', 'credential_binding', 'candidate_sha256', 'source_head',
    'source_tree', 'artifact', 'observed_at',
)


@dataclass(frozen=True)
class ObservationRequest:
    channel: str
    environment: str
    account_id: str
    destination_id: str
    candidate_sha256: str
    source_head: str
    source_tree: str
    artifact_path: str
    artifact_sha256: str


def _identity(metadata):
    fields(metadata, DESTINATION_FIELDS)
    require(all(isinstance(metadata[k], str) and IDENTIFIER.fullmatch(metadata[k])
                for k in DESTINATION_FIELDS), 'invalid destination identity metadata')
    return tuple(metadata[key] for key in DESTINATION_FIELDS)


def observe_candidate_destination(candidate, release_policy, *, destination, proof,
                                  now, max_age_seconds, reader):
    """Call an injected observation reader only after an exact binding check.

    The caller supplies the already selected destination and a clock/freshness
    limit. Inputs are non-secret metadata from an approved upstream authority.
    This function neither authenticates metadata nor owns connector execution.
    It has no default reader, network transport, or publication result.
    """
    candidate = validate_release_candidate(candidate, release_policy)
    identity = _identity(destination)
    fields(proof, PROOF_FIELDS)
    require(_identity(proof['destination']) == identity, 'destination mismatch')
    require(_identity(proof['credential_binding']) == identity, 'credential binding mismatch')
    source = candidate['source']
    candidate_sha256 = fingerprint(candidate)
    require(proof['candidate_sha256'] == candidate_sha256, 'candidate fingerprint mismatch')
    require(proof['source_head'] == source['head'] and proof['source_tree'] == source['tree'],
            'source revision mismatch')
    artifact = proof['artifact']
    fields(artifact, ('path', 'sha256'))
    require(isinstance(artifact['path'], str) and isinstance(artifact['sha256'], str)
            and SHA.fullmatch(artifact['sha256']), 'invalid artifact identity')
    require(artifact in candidate['artifacts'], 'artifact not in frozen candidate')
    observed_at = proof['observed_at']
    require(type(now) is int and type(observed_at) is int and type(max_age_seconds) is int
            and max_age_seconds > 0 and 0 <= observed_at <= now, 'invalid observation time')
    require(now - observed_at <= max_age_seconds, 'stale observation binding')
    require(callable(reader), 'observation reader required')
    request = ObservationRequest(*identity, candidate_sha256, source['head'], source['tree'],
                                 artifact['path'], artifact['sha256'])
    return reader(request)
