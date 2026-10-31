"""Bounded, deterministic v1 source/evidence contracts; no execution authority.

Public API: fingerprint, load_release_policy, validate_handoff and
validate_release_candidate. Qualified values are detached JSON dictionaries.
Errors expose bounded field paths/codes, never input contents. References are
syntax checked only: validators never open evidence, inspect Git, claim work,
call a service or establish that referenced evidence is true or authorized.

For this NEW contract, source.policy_sha256 is fingerprint(policy): canonical
JSON SHA256, not a file-byte digest. Historical policy byte pins, origins and
receipts retain their original readers and interpretation, without migration.
The schema's $defs.releaseCandidate describes the separate release-cut value;
fingerprint(candidate) is its immutable identity. Moving develop observations
belong outside that value. No review/effect here grants release acceptance.
"""
import hashlib
import json
import math
from pathlib import Path
import re
from uuid import UUID

from jsonschema import Draft202012Validator


class ContractError(ValueError):
    """Bounded input-contract failure, not a transport or execution result."""


MAX_BYTES = 262144
MAX_NODES = 8192
MAX_DEPTH = 16
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / 'contracts/schemas/delivery-handoff-v1.schema.json'
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding='utf-8'))
_HANDOFF = Draft202012Validator(_SCHEMA)
_CANDIDATE = Draft202012Validator({'$ref': '#/$defs/releaseCandidate', '$defs': _SCHEMA['$defs']})


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _snapshot(value):
    """Bound traversal before encoding; reject non-JSON and oversized inputs."""
    count = 0

    def visit(item, depth):
        nonlocal count
        count += 1
        _require(count <= MAX_NODES and depth <= MAX_DEPTH, 'json_bounds')
        kind = type(item)
        if kind is dict:
            _require(len(item) <= 64, 'json_object_bounds')
            for key, child in item.items():
                _require(type(key) is str and len(key) <= 128, 'json_key')
                visit(child, depth + 1)
        elif kind is list:
            _require(len(item) <= 128, 'json_array_bounds')
            for child in item:
                visit(child, depth + 1)
        elif kind is str:
            _require(len(item) <= 4096, 'json_string_bounds')
        elif kind is float:
            _require(math.isfinite(item), 'json_number')
        elif kind is int:
            _require(item.bit_length() <= 64, 'json_integer_bounds')
        else:
            _require(kind is bool or item is None, 'json_type')

    visit(value, 0)
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    _require(len(encoded) <= MAX_BYTES, 'json_bytes_bounds')
    return encoded


def fingerprint(value):
    """SHA256 of bounded canonical JSON; does not hash referenced file bytes."""
    return hashlib.sha256(_snapshot(value)).hexdigest()


def _copy(value):
    return json.loads(_snapshot(value))


def _policy(value):
    p = _copy(value)
    _require(type(p) is dict and set(p) == {
        'version', 'repository', 'integration_branch', 'release_branch',
        'work_branch_prefixes', 'release_candidate', 'release', 'ownership',
        'recovery', 'activation'}, 'policy_fields')
    _require(type(p['version']) is int and p['version'] == 1, 'policy_version')
    for key, expected in (
        ('repository', 'maldous/offmenu'), ('integration_branch', 'develop'),
        ('release_branch', 'main'), ('work_branch_prefixes', ['feature/', 'bugfix/']),
        ('release_candidate', dict(immutable=True, required_source_facts=['base', 'head', 'tree', 'policy_sha256'], required_artifact_facts=['path', 'sha256'], develop_may_advance=True, repair_requires_new_candidate=True)),
        ('release', dict(promotion_target='main', requires_independent_review=True, requires_complete_validation=True, requires_canonical_tree_readback=True, requires_immutable_tag=True, main_changes_only_for_approved_release=True, tag_updates_allowed=False, automatic_product_deployment=False)),
        ('ownership', dict(work_authority='linear', coding_dispatch='stokowski', finite_decisions='langgraph', deterministic_execution='windmill', source_authority='github', integration_writers=1, activation_writers=1)),
        ('recovery', dict(unknown_effect_requires_reconciliation=True, retain_original_operation_identity=True, retain_legacy_evidence_readers=True, release_lease_requires_stopped_children=True)),
        ('activation', dict(delivery_bau_requires_coherent_reviewed_adoption=True, requires_actual_runtime_readback=True, requires_rollback_custody=True, product_deployment=False, cix_execution=False, github_actions=False, new_credentials_or_spend=False)),
    ):
        # Canonical JSON equality preserves boolean/integer distinctions.
        _require(_snapshot(p[key]) == _snapshot(expected), 'policy_' + key)
    return p


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'policy_duplicate_key')
        result[key] = value
    return result


def load_release_policy(path):
    """Read the selected local policy (bounded); pin using fingerprint(result).

    Only this loader performs file I/O. It does not load referenced evidence.
    Legacy policy/file digests must continue through their original readers.
    """
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        _require(len(raw) <= MAX_BYTES, 'policy_bytes_bounds')
        return _policy(json.loads(raw, object_pairs_hook=_unique_object))
    except ContractError:
        raise
    except (OSError, ValueError, TypeError, RecursionError):
        raise ContractError('policy_read') from None


def _shape(value, validator):
    v = _copy(value)
    error = next(validator.iter_errors(v), None)
    if error is not None:
        # Do not reflect untrusted keys, values, exception messages or transcripts.
        raise ContractError('schema_' + str(error.validator)[:32])
    _require(type(v['version']) is int, 'version_type')
    return v


def _path(value, relative=False):
    _require(value == value.strip() and '\\' not in value
             and not any(ord(c) < 32 or ord(c) == 127 for c in value)
             and not any(c in value for c in ':?#~'), 'local_path')
    _require(not relative or not value.startswith('/'), 'relative_output_path')
    parts = value.split('/')
    if value.startswith('/'):
        parts = parts[1:]
    _require(bool(parts) and all(part not in ('', '.', '..') for part in parts), 'canonical_path')


def _identity(value):
    _require(bool(value.strip()) and value == value.strip(), 'identity_whitespace')


def _refs(refs, relative=False):
    seen = set()
    for item in refs:
        _path(item['path'], relative)
        _require(item['path'] not in seen, 'duplicate_path')
        seen.add(item['path'])


def _source(source, policy, release=False):
    _require(source['repository'] == policy['repository'], 'source_repository')
    _require(source['policy_sha256'] == fingerprint(policy), 'source_policy')
    target = source['target']
    branch = source['branch']
    if release or target == policy['release_branch']:
        _require(branch == policy['integration_branch'] and target == policy['release_branch'], 'release_source')
    else:
        _require(target == policy['integration_branch'] and any(branch.startswith(p) for p in policy['work_branch_prefixes']), 'work_source')
        _require(re.fullmatch(r'(?:feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}', branch)
                 and not branch.endswith('/') and '//' not in branch, 'source_branch')


def validate_handoff(value, policy):
    """Qualify v1 shape/bindings, including honest pending/unknown observations.

    An unknown effect remains unknown and retains the original operation ID.
    Qualification never permits retry or asserts independent acceptance. Noncoding
    origins omit attempt; any supplied historical evidence stays an opaque ref.
    Operation policy_sha256 is its original executor policy pin, distinct from
    source.policy_sha256 (the canonical NEW release policy fingerprint).
    """
    p = _policy(policy)
    v = _shape(value, _HANDOFF)
    for key in ('issue_id', 'project_id'):
        _require(str(UUID(v[key])) == v[key] and UUID(v[key]).int != 0, key)
    _source(v['source'], p)
    _refs(v['outputs'], relative=True)
    _refs(v['evidence'])
    _refs([v['origin']['evidence']])
    _identity(v['owner'])
    if 'attempt' in v:
        _identity(v['attempt']['id'])
        _identity(v['attempt']['lease_id'])
        _refs([v['attempt']['admission']])
    if 'operation' in v:
        _identity(v['operation']['id'])
        _identity(v['operation']['job_id'])
        _refs([v['operation']['receipt']])
    if 'review' in v:
        review = v['review']
        _identity(review['reviewer'])
        _identity(review['author'])
        _refs([review['evidence']])
        _require(review['reviewer'].strip().casefold() != review['author'].strip().casefold()
                 and review['reviewer'].strip().casefold() != v['owner'].strip().casefold(), 'independent_reviewer')
        _require(review['source_sha256'] == fingerprint(v['source']), 'review_source')
        _require(review['outputs_sha256'] == fingerprint(v['outputs']), 'review_outputs')
    if 'effect' in v:
        effect, operation = v['effect'], v['operation']
        _require(effect['operation_id'] == operation['id'], 'effect_operation_identity')
        compatible = {
            'not-attempted': {'planned'}, 'pending': {'submitted', 'running'},
            'unknown': {'submitted', 'running', 'unknown'},
            'verified': {'succeeded'}, 'failed': {'failed', 'cancelled'},
        }
        _require(operation['status'] in compatible[effect['status']], 'effect_status')
        if 'reconciliation' in effect:
            _refs([effect['reconciliation']])
    return v


def validate_release_candidate(value, policy):
    """Freeze source/profiles/artifact identities; not release-check acceptance.

    No moving branch tip, mutable candidate ID, test success, promotion or tag
    assertion is embedded here. Consumers bind these separately to fingerprint(v).
    Changed source, profiles or artifacts necessarily produce a new identity.
    """
    p = _policy(policy)
    v = _shape(value, _CANDIDATE)
    _source(v['source'], p, release=True)
    _refs(v['artifacts'], relative=True)
    for profile in v['required_profiles']:
        _require(re.fullmatch('[a-z0-9][a-z0-9-]{0,79}', profile) is not None, 'profile_id')
    return v
