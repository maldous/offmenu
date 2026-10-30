"""Review-bound multi-issue task contracts; no network or execution.

Legacy v1 task dictionaries are returned unchanged. Explicit validation/review
stages add input_paths and stage_binding, and require empty allowed_paths.
The owner-pinned binding selects the original catalog entry, continuation identity
and transitive input hashes; CurrentWork reuses its native v1 qualifier at every
consumption boundary. These references never grant implementation authority.
"""
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID
try:
    from .symphony_capacity import AdmissionError, BRANCH, positive, scope, valid_branch
except ImportError:
    from symphony_capacity import AdmissionError, BRANCH, positive, scope, valid_branch

PROJECT_ID='ce60c1ab-a732-4a71-8471-14c9dc393886'
PROJECT_ROUTES = {
    PROJECT_ID: 'ccd080f4f6f0',
    'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0': '21558318e036',
}


def project_route(project_id):
    """Only the two reviewed UUID/slug pairs, never a tracker-wide allowlist."""
    if not isinstance(project_id, str) or project_id not in PROJECT_ROUTES:
        raise AdmissionError('project_route_identity')
    return dict(project_id=project_id, project_slug=PROJECT_ROUTES[project_id])


def validated_project_route(route):
    if (not isinstance(route, dict) or set(route) != {'project_id', 'project_slug'}
        or route != project_route(route['project_id'])):
        raise AdmissionError('project_route_pair')
    return dict(route)



def manifest_digest(manifest):
    return hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def runtime_lease_ids(runtime, manifest):
    """Select only exact manifest issues in this canonical runtime directory."""
    identity = {'runtime': str(Path(runtime).resolve()),
                'manifest_sha256': manifest_digest(manifest)}
    return {name: 'rt-' + manifest_digest(dict(identity, issue=name))
            for name in manifest['tasks']}


def load_manifest(path,expected_head=None,expected_branch=BRANCH):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise AdmissionError('duplicate_manifest_key')
            d[k]=v
        return d
    d=json.loads(Path(path).read_text(),object_pairs_hook=unique)
    if not isinstance(d,dict) or set(d)!={'version','branch','base_revision','project_id','label','tasks'}:raise AdmissionError('manifest_fields')
    if type(d['version']) is not int or d['version']!=1 or not isinstance(d['project_id'],str) or d['project_id'] not in PROJECT_ROUTES:raise AdmissionError('manifest_identity')
    if (d['branch']!=expected_branch if expected_branch is not None else not valid_branch(d['branch'])) or not isinstance(d['base_revision'],str) or not re.fullmatch(r'[0-9a-f]{40}',d['base_revision']):raise AdmissionError('manifest_source')
    if expected_head is not None and d['base_revision']!=expected_head:raise AdmissionError('manifest_source')
    if not isinstance(d['label'],str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}',d['label']):raise AdmissionError('manifest_label')
    if not isinstance(d['tasks'],dict) or not 1<=len(d['tasks'])<=256:raise AdmissionError('manifest_tasks')
    ids=set()
    for name,t in d['tasks'].items():
        if not re.fullmatch(r'UIF-[1-9][0-9]*',name) or not isinstance(t,dict):raise AdmissionError('task_identity')
        fields={'issue_id','owner','purpose','allowed_paths','acceptance','resources','attempt_limit'}
        staged = 'stage' in t
        if set(t) != fields | ({'stage','input_paths','stage_binding'} if staged else set()):raise AdmissionError('task_fields')
        if staged:
            if t['stage'] not in ('validation','review') or t['allowed_paths'] != []:raise AdmissionError('task_stage_authority')
            binding=t['stage_binding']
            if not isinstance(binding,dict) or set(binding)!={'entry','identity','inputs'}:raise AdmissionError('task_stage_binding')
            if not isinstance(binding['identity'],str) or not re.fullmatch('[0-9a-f]{64}',binding['identity']):raise AdmissionError('task_stage_binding')
            origin=binding['entry'].get('origin')
            if origin is not None and origin != 'reviewed-source-v1':raise AdmissionError('task_stage_origin')
            inputs=t['input_paths']
            if not isinstance(inputs,list) or not inputs or len(inputs)>64 or not all(isinstance(p,str) for p in inputs) or len(set(inputs))!=len(inputs):raise AdmissionError('task_stage_inputs')
            for p in inputs:scope(p)

        try:uid=str(UUID(t['issue_id']))
        except (ValueError,TypeError,AttributeError):raise AdmissionError('task_issue_uuid') from None
        if uid!=t['issue_id'] or uid in ids:raise AdmissionError('task_issue_uuid')
        ids.add(uid)
        for field in ('owner','purpose'):
            if not isinstance(t[field],str) or not t[field].strip():raise AdmissionError('task_'+field)
        paths=t['allowed_paths']
        if not isinstance(paths,list) or (not paths and not staged) or len(paths)>64 or not all(isinstance(p,str) for p in paths) or len(set(paths))!=len(paths):raise AdmissionError('task_paths')
        for p in paths:scope(p)
        if not isinstance(t['acceptance'],list) or not t['acceptance'] or not all(isinstance(v,str) and v.strip() for v in t['acceptance']):raise AdmissionError('task_acceptance')
        if type(t['attempt_limit']) is not int or not 1<=t['attempt_limit']<=3:raise AdmissionError('task_attempts')
        resources=t['resources']
        if not isinstance(resources,dict) or set(resources)!={'cpu_millis','memory_bytes','io_slots','output_bytes'}:raise AdmissionError('task_resources')
        for k,v in resources.items():positive(v,k,k=='output_bytes')
    return d


def task_for_workspace(manifest,workspace_name):
    if workspace_name not in manifest['tasks']:raise AdmissionError('workspace_not_admitted')
    return manifest['tasks'][workspace_name]
