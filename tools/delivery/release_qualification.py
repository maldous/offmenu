#!/usr/bin/env python3
"""Finite release-cut planning and exact-result aggregation; never dispatch/promote."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

from native_harness_contract import (
    ContractError, fingerprint, load_release_policy, validate_handoff,
    validate_release_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 1024 * 1024
ID = re.compile(r'[a-z][a-z0-9-]{0,47}')
SHA = re.compile(r'[0-9a-f]{64}')


def require(condition, message):
    if not condition:
        raise ContractError(message)


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, 'JSON exceeds release bound')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON field')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, 'nonfinite JSON'))


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fields(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), 'unexpected fields')


def profile_catalog(value):
    """Validate execution declarations; commands are reviewed code, not a sandbox."""
    fields(value, ('version', 'profiles'))
    require(type(value['version']) is int and value['version'] == 1, 'catalog version')
    require(isinstance(value['profiles'], dict) and 1 <= len(value['profiles']) <= 16,
            'profile count')
    for name, profile in value['profiles'].items():
        require(isinstance(name, str) and ID.fullmatch(name), 'profile identity')
        fields(profile, ('purpose', 'checks'))
        require(isinstance(profile['purpose'], str) and profile['purpose'].strip(), 'purpose')
        checks = profile['checks']
        require(isinstance(checks, list) and 1 <= len(checks) <= 32, 'check count')
        seen = set()
        for check in checks:
            fields(check, ('id', 'argv', 'timeout_seconds', 'resources', 'acceptance'))
            require(isinstance(check['id'], str) and ID.fullmatch(check['id'])
                    and check['id'] not in seen, 'check identity')
            seen.add(check['id'])
            require(isinstance(check['argv'], list) and 1 <= len(check['argv']) <= 64
                    and all(isinstance(a, str) and a and '\0' not in a and len(a) <= 4096
                            for a in check['argv']), 'command array')
            require(type(check['timeout_seconds']) is int
                    and 1 <= check['timeout_seconds'] <= 1800, 'timeout')
            require(check['acceptance'] == 'exit-zero-complete-outputs', 'acceptance criterion')
            resources = check['resources']
            fields(resources, ('workers', 'overhead_processes', 'cpu_millis',
                               'memory_bytes', 'output_bytes', 'io_slots'))
            bounds = {'workers': (1, 64), 'overhead_processes': (1, 8),
                      'cpu_millis': (1, 27000), 'memory_bytes': (1048576, 42 * 1024**3),
                      'output_bytes': (0, 64 * 1024**3), 'io_slots': (1, 32)}
            for key, (low, high) in bounds.items():
                require(type(resources[key]) is int and low <= resources[key] <= high,
                        'resource range: ' + key)
    return json.loads(json.dumps(value, allow_nan=False))


def cut(source, artifacts, policy, catalog, profile='release'):
    catalog = profile_catalog(catalog)
    require(profile == 'release' and profile in catalog['profiles'], 'release cut requires release profile')
    return validate_release_candidate({
        'version': 1, 'kind': 'release-candidate-v1', 'source': source,
        'required_profiles': [profile], 'artifacts': artifacts,
    }, policy)


def plan(candidate, policy, catalog, runner_sha256, capacity_policy_sha256):
    """An immutable graph input. Fresh shared Windmill admission is still required."""
    candidate = validate_release_candidate(candidate, policy)
    catalog = profile_catalog(catalog)
    require('release' in candidate['required_profiles'], 'release profile required')
    for pin in (runner_sha256, capacity_policy_sha256):
        require(isinstance(pin, str) and SHA.fullmatch(pin), 'runner/capacity pin')
    identity = fingerprint(candidate)
    checks = []
    for profile in candidate['required_profiles']:
        require(profile in catalog['profiles'], 'unknown required profile')
        for check in catalog['profiles'][profile]['checks']:
            key = profile + ':' + check['id']
            # Distinct candidate workspaces permit parallel builds without shared writes.
            workspace = '/offmenu/data/release-candidates/' + identity + '/' + profile + '/' + check['id']
            guard = ('test "$(git rev-parse HEAD)" = ' + candidate['source']['head']
                     + ' && test "$(git rev-parse HEAD^{tree})" = ' + candidate['source']['tree']
                     + ' && git diff --quiet HEAD --')
            command = ('cd ' + shlex.quote(workspace) + ' && ' + guard
                       + ' && ' + shlex.join(check['argv']) + ' && ' + guard)
            require(len(command.encode()) <= 32000, 'command exceeds native runner bound')
            checks.append(dict(check, key=key, profile=profile, workspace=workspace,
                               command=command,
                               command_sha256=hashlib.sha256(command.encode()).hexdigest(),
                               resources=dict(check['resources'], read_roots=[workspace],
                                              write_roots=[workspace])))
    require(1 <= len(checks) <= 64, 'total check count')
    return {'version': 1, 'kind': 'release-qualification-plan-v1',
            'candidate': candidate, 'candidate_sha256': identity,
            'catalog_sha256': fingerprint(catalog), 'runner_sha256': runner_sha256,
            'capacity_policy_sha256': capacity_policy_sha256, 'checks': checks}


def validate_plan(value, policy, catalog):
    fields(value, ('version', 'kind', 'candidate', 'candidate_sha256',
                   'catalog_sha256', 'runner_sha256', 'capacity_policy_sha256', 'checks'))
    expected = plan(value['candidate'], policy, catalog, value['runner_sha256'],
                    value['capacity_policy_sha256'])
    require(fingerprint(value) == fingerprint(expected), 'plan mismatch')
    return expected


def bridge_request(value, check_key, policy, catalog):
    """Arguments for the existing Windmill bridge, not dispatch authorization.

    Reuse this original job identity on unknown outcomes; status/cancel use it too.
    The caller must stage the exact candidate and obtain fresh shared admission.
    """
    value = validate_plan(value, policy, catalog)
    matches = [c for c in value['checks'] if c['key'] == check_key]
    require(len(matches) == 1, 'unknown check')
    check = matches[0]
    job_id = 'release-' + fingerprint({'plan': fingerprint(value), 'check': check_key})
    return {'action': 'run', 'job_id': job_id, 'command': check['command'],
            'mode': 'write', 'timeout_seconds': check['timeout_seconds'],
            'resources': check['resources'], 'receipt_projection': 'resources-v1'}


def verified_ref(ref, evidence_root):
    fields(ref, ('path', 'sha256'))
    name = ref['path']
    require(isinstance(name, str) and name and len(name) <= 4096
            and not name.startswith('/') and '\\' not in name
            and all(p not in ('', '.', '..') for p in name.split('/')), 'local relative reference')
    require(isinstance(ref['sha256'], str) and SHA.fullmatch(ref['sha256']), 'reference hash')
    root = Path(evidence_root).resolve(strict=True)
    path = root / name
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root
                    and root in p.parents), 'symlink evidence')
    require(path.is_file() and path.resolve().is_relative_to(root), 'evidence scope')
    require(file_sha(path) == ref['sha256'], 'evidence bytes mismatch')
    return path


def aggregate(value, results, policy, catalog, evidence_root):
    """Single deterministic aggregator. Existing legacy receipt readers stay unchanged."""
    value = validate_plan(value, policy, catalog)
    require(isinstance(results, list) and len(results) <= 64, 'result bound')
    checks = {c['key']: c for c in value['checks']}
    seen, accepted, incomplete = set(), [], []
    plan_sha = fingerprint(value)
    for result in results:
        fields(result, ('check', 'plan_sha256', 'coverage', 'handoff'))
        key = result['check']
        require(isinstance(key, str) and key in checks and key not in seen, 'unexpected/duplicate check')
        seen.add(key)
        require(result['plan_sha256'] == plan_sha, 'wrong result plan')
        handoff = validate_handoff(result['handoff'], policy)
        require(handoff['source'] == value['candidate']['source'], 'wrong result source')
        require(handoff['origin']['kind'] == 'completed-native-validation-v1', 'result origin')
        require(handoff['outputs'] == value['candidate']['artifacts'], 'wrong result outputs')
        operation = handoff.get('operation')
        require(isinstance(operation, dict) and operation.get('backend') == 'windmill', 'missing Windmill operation')
        check = checks[key]
        request = bridge_request(value, key, policy, catalog)
        require(operation['job_id'] == request['job_id'], 'wrong check job identity')
        require(operation['command_sha256'] == check['command_sha256']
                and operation['runner_sha256'] == value['runner_sha256']
                and operation['policy_sha256'] == value['capacity_policy_sha256'], 'execution pins')
        receipt_path = verified_ref(operation['receipt'], evidence_root)
        receipt = read_json(receipt_path)
        # Historical windmill_runner.run hashes this exact spec with default
        # JSON spaces/ASCII escaping; this is NOT the new canonical fingerprint.
        spec = dict(command_sha256=check['command_sha256'], mode=request['mode'],
                    timeout_seconds=request['timeout_seconds'],
                    runner_sha256=value['runner_sha256'],
                    capacity_policy_sha256=value['capacity_policy_sha256'],
                    resources=request['resources'])
        request_sha = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        require(isinstance(receipt, dict) and receipt.get('job_id') == operation['job_id']
                and receipt.get('mode') == request['mode']
                and type(receipt.get('timeout_seconds')) is int
                and receipt['timeout_seconds'] == request['timeout_seconds']
                and receipt.get('request_sha256') == request_sha
                and receipt.get('command_sha256') == check['command_sha256']
                and receipt.get('runner_sha256') == value['runner_sha256']
                and receipt.get('capacity_policy_sha256') == value['capacity_policy_sha256']
                and fingerprint(receipt.get('resources')) == fingerprint(check['resources']), 'runner receipt mismatch')
        for ref in handoff['outputs'] + handoff['evidence'] + [handoff['origin']['evidence']]:
            verified_ref(ref, evidence_root)
        success = (operation['status'] == 'succeeded' and receipt.get('status') == 'succeeded'
                   and receipt.get('exit_code') == 0 and type(receipt.get('exit_code')) is int
                   and receipt.get('child_tree_gone') is True
                   and receipt.get('reconcile_required') is False
                   and result['coverage'] == 'complete'
                   and handoff.get('effect', {}).get('status', 'verified') == 'verified')
        (accepted if success else incomplete).append(key)
    missing = sorted(set(checks) - seen)
    return {'version': 1, 'kind': 'release-qualification-result-v1',
            'candidate_sha256': value['candidate_sha256'], 'plan_sha256': plan_sha,
            'source_sha256': fingerprint(value['candidate']['source']),
            'outputs_sha256': fingerprint(value['candidate']['artifacts']),
            'required_profiles': value['candidate']['required_profiles'],
            'status': 'qualified' if not missing and not incomplete else 'incomplete',
            'accepted': sorted(accepted), 'missing': missing, 'incomplete': sorted(incomplete),
            'results_sha256': fingerprint(results)}


def validate_qualification(summary, value, results, policy, catalog, evidence_root):
    """Publisher gate: reaggregate exact evidence rather than trust a success label.

    Independent source/release review and provider contexts remain publisher gates.
    """
    expected = aggregate(value, results, policy, catalog, evidence_root)
    require(fingerprint(summary) == fingerprint(expected)
            and expected['status'] == 'qualified', 'release not qualified')
    return expected


def reusable_result(value, result, policy, catalog, evidence_root):
    """Cache hits reverify the same plan, source, commands and actual evidence bytes."""
    aggregate_result = aggregate(value, [result], policy, catalog, evidence_root)
    return result['check'] in aggregate_result['accepted']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', default=str(ROOT / 'config/delivery-release-policy.json'))
    parser.add_argument('--catalog', default=str(ROOT / 'config/release-validation-profile.json'))
    subs = parser.add_subparsers(dest='action', required=True)
    sub = subs.add_parser('cut')
    sub.add_argument('--source', required=True)
    sub.add_argument('--artifacts', required=True)
    sub.add_argument('--profile', default='release')
    sub = subs.add_parser('plan')
    sub.add_argument('--candidate', required=True)
    sub.add_argument('--runner', default=str(ROOT / 'tools/delivery/windmill_runner.py'))
    sub.add_argument('--capacity-policy', default=str(ROOT / 'tools/delivery/capacity-policy.json'))
    sub = subs.add_parser('request')
    sub.add_argument('--plan', required=True)
    sub.add_argument('--check', required=True)
    sub = subs.add_parser('aggregate')
    sub.add_argument('--plan', required=True)
    sub.add_argument('--results', required=True)
    sub.add_argument('--evidence-root', required=True)
    args = parser.parse_args(argv)
    try:
        policy = load_release_policy(args.policy)
        catalog = read_json(args.catalog)
        if args.action == 'cut':
            result = cut(read_json(args.source), read_json(args.artifacts), policy, catalog, args.profile)
        elif args.action == 'plan':
            result = plan(read_json(args.candidate), policy, catalog,
                          file_sha(args.runner), file_sha(args.capacity_policy))
        elif args.action == 'request':
            result = bridge_request(read_json(args.plan), args.check, policy, catalog)
        else:
            result = aggregate(read_json(args.plan), read_json(args.results), policy,
                               catalog, args.evidence_root)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 1 if result.get('status') == 'incomplete' else 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        print(json.dumps({'status': 'rejected', 'reason': 'invalid release input or evidence'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
