"""Read-only qualification of a root-granted, refused prelaunch replacement.

This module neither grants replacement authority nor changes a lease or attempt.
The current owner must separately bind the exact next catalog edge and handoff.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from symphony_capacity import AdmissionError, digest
from symphony_tasks import runtime_lease_ids

SCHEMA = 'confirmed-prelaunch-replacement-v1'
ENTRY_FIELDS = {'issue', 'issue_id', 'runtime', 'admission_sha256'}


def require(condition, reason):
    if not condition:
        raise AdmissionError('replacement_' + reason)


def record(path, root, expected=None):
    """Read one canonical private regular file and qualify the captured bytes."""
    path, root = Path(path), Path(root)
    require(path.is_absolute() and path == path.resolve() and path.is_relative_to(root), 'path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and 0 < info.st_size <= 2 * 1024 * 1024, 'file')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        require(len(raw) == info.st_size, 'size')
    finally:
        os.close(fd)
    if expected is not None:
        require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected)
                and hashlib.sha256(raw).hexdigest() == expected, 'digest')

    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate_key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'record')
    return value


def refusal_witness(previous, relation, *, root, owner, policy, policy_sha256):
    """Prove a known failed binder refusal, never a started/unknown attempt."""
    require(isinstance(relation, dict) and set(relation) == {
        'schema', 'entry_sha256', 'receipt', 'lease', 'binding_sha256'}
        and relation['schema'] == SCHEMA and relation['entry_sha256'] == digest(previous), 'relation')
    require(isinstance(previous, dict) and set(previous) in (ENTRY_FIELDS, ENTRY_FIELDS | {'replacement_of'}), 'entry')
    runtime = Path(previous['runtime'])
    require(runtime.is_absolute() and runtime == runtime.resolve()
            and runtime.is_relative_to(root), 'runtime')
    issue = previous['issue']
    ref = relation['receipt']
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}
            and ref['path'] == str(runtime/'attempts'/issue/'receipt.json'), 'receipt_path')
    receipt = record(ref['path'], root, ref['sha256'])
    require(receipt.get('status') == 'failed' and receipt.get('child_started') is False
            and receipt.get('child_tree_gone') is True
            and receipt.get('launch_classification') == 'confinement-prelaunch-refusal'
            and receipt.get('exit_code') is None and receipt.get('scope_violations') == []
            and receipt.get('output_sha256') == {} and not receipt.get('session_id')
            and receipt.get('source_identity_changed') is False
            and receipt.get('origin') == 'native-coding'
            and receipt.get('issue') == issue and receipt.get('parent_runtime') == str(runtime), 'refusal')
    admission = record(runtime/'current-admission.json', root, previous['admission_sha256'])
    require(admission['owner'] == owner and admission['issue'] == issue
            and admission['issue_id'] == previous['issue_id']
            and admission['policy_sha256'] == policy_sha256, 'admission')
    manifest = record(runtime/'manifest.json', root, admission['manifest_sha256'])
    request = record(runtime/'requests'/f'{issue}.json', root, admission['request_sha256'])
    require(record(runtime/'capacity-policy.json', root, policy_sha256) == policy, 'policy')
    require(set(manifest['tasks']) == {issue}, 'manifest')
    task = manifest['tasks'][issue]
    require('stage' not in task and task['owner'] == owner
            and task['issue_id'] == previous['issue_id'], 'task')
    binding = dict(branch=manifest['branch'], head=manifest['base_revision'], owner=owner,
        write_roots=task['allowed_paths'], resources=task['resources'],
        task_sha256=digest(dict(runtime=str(runtime), manifest=manifest, request=request)))
    fingerprint = digest(binding)
    lease = runtime_lease_ids(runtime, manifest)[issue]
    require(relation['lease'] == receipt.get('lease') == lease
            and relation['binding_sha256'] == receipt.get('binding_sha256') == fingerprint
            and receipt.get('parent_binding') == binding
            and receipt.get('source_head') == receipt.get('final_head') == manifest['base_revision']
            and receipt.get('final_branch') == manifest['branch'], 'binding')
    intent = record(runtime/'attempts'/issue/'intent.json', root)
    dispatch = record(runtime/'attempts'/issue/'dispatch-intent.json', root)
    require(intent == dict(lease=lease, binding=binding)
            and dispatch.get('entry_sha256') == digest(previous)
            and dispatch.get('expected_lease') == lease and dispatch.get('owner') == owner
            and dispatch.get('request_sha256') == admission['request_sha256']
            and dispatch.get('manifest_sha256') == admission['manifest_sha256'], 'intent')
    database = Path(policy['symphony']['pool_path'])/'state.sqlite'
    require(database == database.resolve() and database.is_file(), 'pool_path')
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        row = db.execute('SELECT binding,fingerprint,status,outcome FROM leases WHERE id=?', (lease,)).fetchone()
    require(row is not None and row[1:] == (fingerprint, 'failed', 'failed')
            and json.loads(row[0]) == binding, 'pool')
    return dict(entry_sha256=digest(previous), receipt=ref, lease=lease,
                binding_sha256=fingerprint, project_id=manifest['project_id'],
                manifest_sha256=admission['manifest_sha256'], request_sha256=admission['request_sha256'])


def active_entries(catalog, qualify):
    """Fold only explicit immediate replacement chains; raw history stays intact."""
    require(isinstance(catalog, dict) and set(catalog) == {'version', 'entries'}
            and type(catalog['version']) is int and catalog['version'] == 1
            and isinstance(catalog['entries'], list), 'catalog')
    active, identities, runtimes = {}, {}, set()
    for entry in catalog['entries']:
        require(isinstance(entry, dict) and set(entry) in (
            ENTRY_FIELDS, ENTRY_FIELDS | {'replacement_of'}), 'entry')
        issue = entry['issue']
        require(entry['runtime'] not in runtimes, 'runtime_reuse')
        if 'replacement_of' in entry:
            previous = active.get(issue)
            require(previous is not None and isinstance(entry['replacement_of'], dict)
                    and previous['issue_id'] == entry['issue_id']
                    and entry['replacement_of'].get('entry_sha256') == digest(previous), 'chain')
            qualify(previous, entry)
        else:
            require(issue not in active and entry['issue_id'] not in identities, 'identity_rebind')
        require(identities.get(entry['issue_id'], issue) == issue, 'identity_rebind')
        active[issue] = entry
        identities[entry['issue_id']] = issue
        runtimes.add(entry['runtime'])
    return active
