"""Finite offline adoption preflight. No installer, service or credential action.

Owner acceptance is supplied separately to prepare(), never inferred from JSON.
All references select bounded private metadata; never select secrets/raw logs.
Returned canonical bytes are pinned content, not permission to mutate a host.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time

from native_harness_contract import (
    fingerprint, load_release_policy, validate_handoff, validate_release_candidate,
)
import protected_owner_install as owner_install
import protected_publisher_install as publisher_install


COMPONENTS = tuple('UIF-' + str(number) for number in range(121, 130))
LIMIT = 262144
TARGETS = {
    'owner_source': str(owner_install.SOURCE),
    'owner_venv': str(owner_install.VENV),
    'owner_config': str(owner_install.CONFIG),
    'publisher': publisher_install.TARGET,
    'publisher_config': publisher_install.CONFIG_DIR,
}


class Refused(ValueError):
    """Fixed error codes only; no input content in errors."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'fields')


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value), 'identity')


def sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'sha256')


def refs(value, *, maximum=64):
    require(type(value) is list and 1 <= len(value) <= maximum, 'reference_count')
    for ref in value:
        fields(ref, 'path sha256')
        require(type(ref['path']) is str and len(ref['path']) <= 1024, 'reference_path')
        owner_install.relative(ref['path'])
        sha(ref['sha256'])
    require(len({ref['path'] for ref in value}) == len(value), 'duplicate_reference')


class Evidence:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.total = 0
        self.pins = {}

    def raw(self, ref, limit=LIMIT):
        refs([ref])
        # Descriptor-relative traversal refuses links even during parent drift.
        parts = owner_install.relative(ref['path']).parts
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            raw = owner_install.regular(parts[-1], limit, dir_fd=fd)
        finally:
            os.close(fd)
        require(owner_install.sha(raw) == ref['sha256'], 'evidence_pin')
        self.total += len(raw)
        require(self.total <= 64 * 1024 * 1024, 'evidence_total')
        previous = self.pins.setdefault(ref['path'], ref['sha256'])
        require(previous == ref['sha256'], 'conflicting_reference')
        return raw

    def record(self, ref):
        return owner_install.record(self.raw(ref))


def prepare(request, policy, *, evidence_root, accepted=None, now=None):
    """Return canonical immutable packet bytes for the sole adoption owner.

    accepted is trusted owner context, not request content: exact latest accepted
    component reference triples and coherent_validation ref. A matching digest
    proves selected bytes, never independent authority or current host state.
    This function never calls prepare/install on either protected installer.
    """
    # Shared canonical serializer bounds JSON before any traversal/file reads.
    fingerprint(request)
    if accepted is not None:
        fingerprint(accepted)
        fields(accepted, 'components coherent_validation')
    request = json.loads(json.dumps(request, allow_nan=False))
    fields(request, 'version kind owner candidate components coherent_validation legacy_snapshot stop_witness rollback target credential_references effects readback')
    require(type(request['version']) is int and request['version'] == 1
            and request['kind'] == 'native-harness-adoption-request-v1', 'version')
    identifier(request['owner'])
    evidence = Evidence(evidence_root)
    candidate = validate_release_candidate(evidence.record(request['candidate']), policy)
    candidate_id = fingerprint(candidate)
    source = candidate['source']
    fields(request['components'], ' '.join(COMPONENTS))
    for component in request['components'].values():
        fields(component, 'source tests review')
        for ref in component.values():
            evidence.raw(ref)
    validation = validate_handoff(evidence.record(request['coherent_validation']), policy)
    require(validation['source'] == source and validation['outputs'] == candidate['artifacts'],
            'coherent_validation_binding')
    validation_ok = (validation.get('review', {}).get('verdict') == 'accept'
                     and validation.get('operation', {}).get('status') == 'succeeded'
                     and validation.get('effect', {}).get('status') == 'verified')
    for ref in validation['evidence'] + [validation['origin']['evidence']]:
        evidence.raw(ref)
    if 'review' in validation:
        evidence.raw(validation['review']['evidence'])
    if 'operation' in validation:
        evidence.raw(validation['operation']['receipt'])

    snapshot = evidence.record(request['legacy_snapshot'])
    fields(snapshot, 'version kind runtime_path source_head source_tree config_sha256 runtime_sha256 source_sha256 install_receipts')
    require(type(snapshot['version']) is int and snapshot['version'] == 1
            and snapshot['kind'] == 'native-legacy-snapshot-v1', 'snapshot_version')
    require(type(snapshot['runtime_path']) is str
            and snapshot['runtime_path'].startswith('/')
            and str(Path(snapshot['runtime_path'])) == snapshot['runtime_path']
            and '..' not in Path(snapshot['runtime_path']).parts, 'runtime_path')
    owner_install.relative(snapshot['runtime_path'][1:])
    for name in ('source_head', 'source_tree'):
        require(type(snapshot[name]) is str and re.fullmatch('[0-9a-f]{40}', snapshot[name]), 'legacy_source')
    for name in ('config_sha256', 'runtime_sha256', 'source_sha256'):
        sha(snapshot[name])
    refs(snapshot['install_receipts'])
    for ref in snapshot['install_receipts']:
        evidence.raw(ref)

    witness = evidence.record(request['stop_witness'])
    fields(witness, 'version kind snapshot_sha256 observed_at stopped inflight children_gone operation_ids')
    require(type(witness['version']) is int and witness['version'] == 1
            and witness['kind'] == 'native-stop-witness-v1', 'stop_version')
    require(witness['snapshot_sha256'] == request['legacy_snapshot']['sha256'], 'stop_snapshot')
    require(type(witness['stopped']) is bool or witness['stopped'] is None, 'stop_state')
    require(type(witness['children_gone']) is bool or witness['children_gone'] is None, 'child_state')
    require(witness['inflight'] is None or (type(witness['inflight']) is int
            and 0 <= witness['inflight'] <= 65536), 'inflight')
    require(type(witness['operation_ids']) is list and len(witness['operation_ids']) <= 64, 'operations')
    for operation_id in witness['operation_ids']:
        identifier(operation_id)
    current = time.time() if now is None else now
    require(type(current) in (int, float) and 0 <= current <= 10**12, 'clock')
    require(type(witness['observed_at']) in (int, float)
            and 0 <= witness['observed_at'] <= 10**12, 'witness_clock')
    stop_ok = (witness['stopped'] is True and witness['children_gone'] is True
               and witness['inflight'] == 0 and not witness['operation_ids']
               and 0 <= current - witness['observed_at'] <= 300)

    rollback = evidence.record(request['rollback'])
    fields(rollback, 'version kind snapshot_sha256 custodian artifacts verification')
    require(type(rollback['version']) is int and rollback['version'] == 1
            and rollback['kind'] == 'native-rollback-custody-v1', 'rollback_version')
    identifier(rollback['custodian'])
    require(rollback['snapshot_sha256'] == request['legacy_snapshot']['sha256'], 'rollback_snapshot')
    fields(rollback['artifacts'], 'source config runtime')
    for name, ref in rollback['artifacts'].items():
        refs([ref])
        require(ref.get('sha256') == snapshot[name + '_sha256'], 'rollback_artifact_binding')
        evidence.raw(ref)
    evidence.raw(rollback['verification'])

    target = request['target']
    fields(target, 'source_head source_tree policy_sha256 paths files dependencies config owner_manifest publisher_manifest')
    require((target['source_head'], target['source_tree'], target['policy_sha256'])
            == (source['head'], source['tree'], source['policy_sha256']), 'target_source')
    require(target['paths'] == TARGETS, 'fixed_targets')
    require(target['files'] == candidate['artifacts'], 'target_artifacts')
    refs(target['files'], maximum=128)
    for ref in target['files']:
        evidence.raw(ref)
    # Existing prepared manifests have their own larger, finite metadata bounds.
    evidence.raw(target['dependencies'], 8 * 1024 * 1024)
    evidence.raw(target['config'])
    evidence.raw(target['owner_manifest'], 8 * 1024 * 1024)
    evidence.raw(target['publisher_manifest'], publisher_install.MAX_MANIFEST)
    names = request['credential_references']
    require(type(names) is list and 1 <= len(names) <= 16, 'credential_names')
    for name in names:
        require(type(name) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}', name), 'credential_name')
    require(len(set(names)) == len(names), 'duplicate_credential_name')
    fields(request['readback'], 'source_head source_tree policy_sha256 closure_sha256 config_sha256 dependencies_sha256')
    require(request['readback'] == dict(source_head=source['head'], source_tree=source['tree'],
            policy_sha256=source['policy_sha256'], closure_sha256=fingerprint(target),
            config_sha256=target['config']['sha256'],
            dependencies_sha256=target['dependencies']['sha256']), 'readback_expectations')

    require(type(request['effects']) is list and len(request['effects']) <= 64, 'effect_count')
    uncertain = []
    for ref in request['effects']:
        handoff = validate_handoff(evidence.record(ref), policy)
        operation = handoff.get('operation')
        require(operation is not None, 'effect_operation_required')
        if (operation['status'] in ('submitted', 'running', 'unknown')
                or handoff.get('effect', {}).get('status') in (None, 'pending', 'unknown')):
            uncertain.append(dict(reference=ref, attempt=handoff.get('attempt'),
                                  operation=operation, effect=handoff.get('effect')))

    acceptance = accepted or {}
    source_ready = acceptance.get('components') == request['components']
    coherent_ready = (source_ready and validation_ok
                      and acceptance.get('coherent_validation') == request['coherent_validation'])
    holds = []
    if not source_ready:
        holds.append('LATEST_INDEPENDENT_COMPONENT_ACCEPTANCE_REQUIRED')
    if not coherent_ready:
        holds.append('EXACT_COHERENT_VALIDATION_ACCEPTANCE_REQUIRED')
    if not stop_ok:
        holds.append('FRESH_STOPPED_ZERO_INFLIGHT_WITNESS_REQUIRED')
    if uncertain:
        holds.append('RECONCILE_ORIGINAL_EFFECTS_NO_RETRY')
    # Neither legacy installer implements reviewed replacement of an installed
    # closure. An input boolean/receipt may never waive these permanent fences.
    holds.extend(('REVIEWED_TYPED_UPGRADE_ROUTE_REQUIRED',
                  'ACTUAL_HOST_CONFIRMATIONS_AND_READBACK_REQUIRED'))
    packet = dict(version=1, kind='native-harness-adoption-plan-v1',
        authority='preflight-only', host_mutation_authorized=False,
        request=request, candidate_sha256=candidate_id,
        evaluated_at=current, stop_witness_expires_at=witness['observed_at'] + 300,
        acceptance_context_sha256=fingerprint(acceptance),
        milestones=dict(source_ready=source_ready, coherent_validation_accepted=coherent_ready,
                        released_source='unknown', installed_adopted='unknown',
                        active_observed='unknown', legacy_retired='unknown'),
        evidence_pins=[dict(path=path, sha256=pin) for path, pin in sorted(evidence.pins.items())],
        legacy_snapshot=snapshot, stop_witness_qualified=stop_ok,
        unresolved_effects=uncertain, holds=holds,
        installer_constraints=dict(owner_receipt=str(owner_install.RECEIPT),
            publisher_receipt=publisher_install.STATE + '/' + publisher_install.RECEIPT,
            publisher_source_head=publisher_install.SOURCE_HEAD,
            owner_no_overwrite=True, publisher_no_overwrite=True, permanent_no_replay=True),
        next_action='reconcile-original-effects' if uncertain else 'owner-review-typed-upgrade-route')
    fingerprint(packet)
    return owner_install.encoded(packet)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = owner_install.record(owner_install.regular(args.request, LIMIT))
        packet = prepare(request, load_release_policy(args.policy), evidence_root=args.evidence_root)
    except (OSError, ValueError, TypeError, RecursionError):
        parser.exit(2, 'adoption preflight rejected\n')
    print(packet.decode('ascii'), end='')
    # Zero means a bounded packet was produced, never readiness or permission.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
