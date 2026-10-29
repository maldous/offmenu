"""Review-bound multi-issue task contracts; no network or execution."""
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID
try:
    from .symphony_capacity import AdmissionError, BRANCH, positive, scope
except ImportError:
    from symphony_capacity import AdmissionError, BRANCH, positive, scope

PROJECT_ID='ce60c1ab-a732-4a71-8471-14c9dc393886'


def manifest_digest(manifest):
    return hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load_manifest(path,expected_head=None,expected_branch=BRANCH):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise AdmissionError('duplicate_manifest_key')
            d[k]=v
        return d
    d=json.loads(Path(path).read_text(),object_pairs_hook=unique)
    if not isinstance(d,dict) or set(d)!={'version','branch','base_revision','project_id','label','tasks'}:raise AdmissionError('manifest_fields')
    if type(d['version']) is not int or d['version']!=1 or d['project_id']!=PROJECT_ID:raise AdmissionError('manifest_identity')
    if d['branch']!=expected_branch or not isinstance(d['base_revision'],str) or not re.fullmatch(r'[0-9a-f]{40}',d['base_revision']):raise AdmissionError('manifest_source')
    if expected_head is not None and d['base_revision']!=expected_head:raise AdmissionError('manifest_source')
    if not isinstance(d['label'],str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}',d['label']):raise AdmissionError('manifest_label')
    if not isinstance(d['tasks'],dict) or not 1<=len(d['tasks'])<=256:raise AdmissionError('manifest_tasks')
    ids=set()
    for name,t in d['tasks'].items():
        if not re.fullmatch(r'UIF-[1-9][0-9]*',name) or not isinstance(t,dict):raise AdmissionError('task_identity')
        if set(t)!={'issue_id','owner','purpose','allowed_paths','acceptance','resources','attempt_limit'}:raise AdmissionError('task_fields')
        try:uid=str(UUID(t['issue_id']))
        except (ValueError,TypeError,AttributeError):raise AdmissionError('task_issue_uuid') from None
        if uid!=t['issue_id'] or uid in ids:raise AdmissionError('task_issue_uuid')
        ids.add(uid)
        for field in ('owner','purpose'):
            if not isinstance(t[field],str) or not t[field].strip():raise AdmissionError('task_'+field)
        paths=t['allowed_paths']
        if not isinstance(paths,list) or not paths or len(paths)>64 or not all(isinstance(p,str) for p in paths) or len(set(paths))!=len(paths):raise AdmissionError('task_paths')
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
