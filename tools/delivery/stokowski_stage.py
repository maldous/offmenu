"""Bind Stokowski output to one reviewed candidate and tick durable validation.

No model calls, source publication or merge authority. This stage consumes
already-admitted coding output and hands deterministic checks to Windmill.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import time

from stokowski_adapter import SOURCE
from stokowski_operations import Journal, OperationError, TERMINAL, operation_key, validated, digest, candidate_check_code, workspace_path, ENRICHMENT_PROFILE, UNIT_PROFILE, unit_targets
from stokowski_mcp import WindmillMCP
from symphony_tasks import load_manifest, runtime_lease_ids
from symphony_workspace import checkpoint


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def completed_native(runtime, issue):
    """Read and qualify the original native result and finished lease only."""
    runtime = Path(runtime)
    if not runtime.is_absolute() or runtime != runtime.resolve():
        raise OperationError('Aliased native runtime')
    manifest = load_manifest(runtime/'manifest.json',expected_branch=None)
    if issue not in manifest['tasks'] or 'stage' in manifest['tasks'][issue]:
        raise OperationError('Expected an admitted coding task')
    paths = [runtime/name for name in ('manifest.json','current-admission.json',
        'capacity-policy.json','provider-proof.json')]
    paths += [runtime/'requests'/(issue+'.json')]
    paths += [runtime/'attempts'/issue/name for name in
              ('receipt.json','intent.json','dispatch-intent.json')]
    if any(path != path.resolve() or not path.is_file() for path in paths):
        raise OperationError('Aliased or missing native evidence')
    receipt_path = runtime/'attempts'/issue/'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    workspace = runtime/'workspaces'/issue
    original = receipt.get('output_sha256',{})
    if (workspace != workspace.resolve() or receipt.get('status') != 'succeeded'
        or receipt.get('child_tree_gone') is not True or receipt.get('scope_violations') != []
        or receipt.get('source_head') != manifest['base_revision']
        or git(workspace,'rev-parse','HEAD') != manifest['base_revision']
        or git(workspace,'branch','--show-current') != manifest['branch']):
        raise OperationError('Coding output is not reconciled against its admitted source')
    request_path = runtime/'requests'/(issue+'.json')
    request = json.loads(request_path.read_text())
    native_binding = dict(branch=manifest['branch'],head=manifest['base_revision'],
        owner=manifest['tasks'][issue]['owner'],write_roots=manifest['tasks'][issue]['allowed_paths'],
        resources=manifest['tasks'][issue]['resources'],
        task_sha256=digest(dict(runtime=str(runtime),manifest=manifest,request=request)))
    lease = runtime_lease_ids(runtime,manifest)[issue]
    intent = json.loads((runtime/'attempts'/issue/'intent.json').read_text())
    dispatch = json.loads((runtime/'attempts'/issue/'dispatch-intent.json').read_text())
    admission = json.loads((runtime/'current-admission.json').read_text())
    entry = dict(issue=issue,issue_id=manifest['tasks'][issue]['issue_id'],
                 runtime=str(runtime),admission_sha256=file_hash(runtime/'current-admission.json'))
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    database = Path(policy['symphony']['pool_path'])/'state.sqlite'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        row = db.execute('SELECT status,outcome,binding,fingerprint FROM leases WHERE id=?',(lease,)).fetchone()
    if (receipt.get('origin') != 'native-coding' or receipt.get('exit_code') != 0
        or receipt.get('turn_completed') is not True or not receipt.get('session_id')
        or receipt.get('source_identity_changed') is not False
        or receipt.get('final_head') != manifest['base_revision']
        or receipt.get('final_branch') != manifest['branch']
        or receipt.get('parent_runtime') != str(runtime) or receipt.get('issue') != issue
        or receipt.get('parent_binding') != native_binding
        or receipt.get('binding_sha256') != digest(native_binding) or receipt.get('lease') != lease
        or intent != dict(lease=lease,binding=native_binding)
        or dispatch.get('expected_lease') != lease or dispatch.get('owner') != native_binding['owner']
        or dispatch.get('entry_sha256') != digest(entry)
        or dispatch.get('manifest_sha256') != file_hash(runtime/'manifest.json')
        or dispatch.get('request_sha256') != file_hash(request_path)
        or dispatch.get('provider_proof_sha256') != file_hash(runtime/'provider-proof.json')
        or admission.get('manifest_sha256') != file_hash(runtime/'manifest.json')
        or admission.get('request_sha256') != file_hash(request_path)
        or row is None or row[:2] != ('finished','succeeded')
        or json.loads(row[2]) != native_binding or row[3] != digest(native_binding)
        or not original or not all(any(name == allowed or name.startswith(allowed+'/')
            for allowed in manifest['tasks'][issue]['allowed_paths']) for name in original)):
        raise OperationError('Origin is not an immutable finished native result')
    from stokowski_worker import changed_paths
    if set(changed_paths(workspace,manifest['base_revision'])) != set(original):
        raise OperationError('Native output scope changed')
    for name,sha in original.items():
        path = workspace/name
        if (path != path.resolve() or not path.is_file() or path.stat().st_nlink != 1
            or file_hash(path) != sha):
            raise OperationError('Coding output changed after its receipt')
    return manifest,receipt




def prepare_completed_native(runtime, issue, *, candidate_root, template):
    """Assemble exact native output once; bind existing Journal, never execute it."""
    import fcntl
    import tempfile
    import re
    runtime,candidate=Path(runtime),Path(candidate_root)
    manifest,receipt=completed_native(runtime,issue)
    fields={'profile','policy_sha256','runner_sha256','executor_sha256','git_author',
            'validation_targets','validation_scope','source_repository'}
    if set(template)!=fields or template['profile']!=UNIT_PROFILE:
        raise OperationError('Root-selected focused validation template required')
    unit_targets(template['validation_targets'],template['validation_scope'])
    author=template['git_author']
    if (set(author)!={'name','email'} or any(not isinstance(v,str) or not v.strip()
        or len(v)>256 or any(c in v for c in '\n\r<>') for v in author.values()) or '@' not in author['email']):
        raise OperationError('Root-approved Git identity required')
    repository=Path(template['source_repository'])
    if (not repository.is_absolute() or repository!=repository.resolve()
        or not candidate.is_absolute() or candidate!=candidate.resolve()
        or candidate==repository or candidate.is_relative_to(runtime/'workspaces')):
        raise OperationError('Private candidate and canonical object repository required')
    if git(repository,'rev-parse','--show-toplevel')!=str(repository):
        raise OperationError('Contribution object store is not project repository')
    task=manifest['tasks'][issue];sha=file_hash(runtime/'attempts'/issue/'receipt.json')
    branch='bugfix/native-'+issue.lower()+'-'+sha[:16]
    spec=dict(version=1,issue=issue,issue_id=task['issue_id'],owner=task['owner'],stage='validate',
        head=manifest['base_revision'],base=manifest['base_revision'],branch=branch,
        tree=git(repository,'rev-parse',manifest['base_revision']+'^{tree}'),native_receipt_sha256=sha,
        outputs=receipt['output_sha256'],acceptance_sha256=digest(dict(task=task,
            native_receipt_sha256=sha,profile=UNIT_PROFILE)),
        **{k:template[k] for k in fields-{'git_author','source_repository'}})
    validated(spec)
    directory=runtime/'contributions'/issue
    if directory!=directory.resolve(): raise OperationError('Aliased contribution preparation')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(directory/'producer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        intent=dict(runtime=str(runtime),issue=issue,candidate_root=str(candidate),template=template,native_receipt_sha256=sha)
        path=directory/'intent.json'
        if path.exists():
            if path!=path.resolve() or json.loads(path.read_bytes())!=intent:
                raise OperationError('Conflicting contribution intent')
        else:
            if candidate.exists(): raise OperationError('Unowned candidate needs reconciliation')
            checkpoint(path,intent)
        # A private index writes ordinary Git objects without touching any HEAD,
        # working tree, shared index or native receipt. Author is assembly owner.
        environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(directory),
            'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
            'GIT_AUTHOR_NAME':author['name'],'GIT_AUTHOR_EMAIL':author['email'],
            'GIT_COMMITTER_NAME':author['name'],'GIT_COMMITTER_EMAIL':author['email'],
            'GIT_AUTHOR_DATE':'2000-01-01T00:00:00+0000','GIT_COMMITTER_DATE':'2000-01-01T00:00:00+0000'}
        command=['git','-c','safe.directory='+str(repository),'-c','core.hooksPath=/dev/null','-C',str(repository)]
        with tempfile.TemporaryDirectory(prefix='index-',dir=directory) as temporary:
            environment['GIT_INDEX_FILE']=str(Path(temporary)/'index')
            def run(*args,data=None):
                return subprocess.check_output(command+list(args),input=data,env=environment).decode().strip()
            run('read-tree',spec['base'])
            workspace=runtime/'workspaces'/issue
            for name,expected in spec['outputs'].items():
                output=workspace/name;body=output.read_bytes()
                if hashlib.sha256(body).hexdigest()!=expected: raise OperationError('Native output drift')
                mode='100755' if output.stat().st_mode&0o100 else '100644'
                blob=run('hash-object','-w','--stdin',data=body)
                run('update-index','--add','--cacheinfo',mode,blob,name)
            tree=run('write-tree')
            message=(issue+': native coding contribution\n\nNative-Session: '+receipt['session_id']+
                     '\nNative-Receipt-SHA256: '+sha+'\n')
            head=run('commit-tree',tree,'-p',spec['base'],data=message.encode())
            ref='refs/heads/'+branch
            existing=subprocess.run(command+['rev-parse','--verify',ref],env=environment,capture_output=True,text=True)
            if existing.returncode==0 and existing.stdout.strip()!=head:
                raise OperationError('Conflicting immutable contribution ref')
            run('update-ref',ref,head,head if existing.returncode==0 else '0'*40)
            if not candidate.exists():
                bundle=Path(temporary)/'source.bundle'
                run('bundle','create',str(bundle),ref)
                clone=Path(temporary)/'candidate'
                subprocess.run(['git','clone','--no-hardlinks','--single-branch','--branch',branch,str(bundle),str(clone)],env={k:v for k,v in environment.items() if k!='GIT_INDEX_FILE'},check=True,capture_output=True)
                candidate.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                os.rename(clone,candidate)
        spec['head']=head
        spec['tree']=tree
        completed_native(runtime,issue)
        spec_path=directory/'spec.json'
        if spec_path.exists():
            if spec_path!=spec_path.resolve() or json.loads(spec_path.read_bytes())!=spec:
                raise OperationError('Immutable contribution spec drift')
        else: checkpoint(spec_path,spec)
        key=bind(runtime,spec,candidate_root=candidate)
        return dict(operation_key=key,candidate_root=str(candidate),source_head=head,
            spec_path=str(spec_path),spec_sha256=file_hash(spec_path))
    finally:
        os.close(fd)

def bind(runtime,spec,derivation_reason=None,*,candidate_root=None):
    runtime = runtime.resolve()
    manifest = load_manifest(runtime/'manifest.json',expected_branch=None)
    validated(spec)
    if spec['version'] != 1:
        raise OperationError('Reviewed extraction requires bind_extraction')
    enrichment = spec['profile'] in (ENRICHMENT_PROFILE,UNIT_PROFILE)
    if candidate_root is not None and not enrichment:
        raise OperationError('Explicit native candidate root requires enrichment profile')
    candidate = SOURCE
    if enrichment:
        if candidate_root is None:
            raise OperationError('Enrichment validation requires an explicit owner-selected candidate root')
        candidate = Path(candidate_root)
        if not candidate.is_absolute() or candidate != candidate.resolve():
            raise OperationError('Aliased candidate root')
        if spec['base'] != manifest['base_revision']:
            raise OperationError('Candidate base differs from original coding base')
    if not enrichment and spec.get('branch','feature/langgraph-delivery-standardization') != manifest['branch']:
        raise OperationError('Validation branch differs from admitted coding branch')
    issue = spec['issue']
    if issue not in manifest['tasks'] or spec['issue_id'] != manifest['tasks'][issue]['issue_id']:
        raise OperationError('Issue is not admitted to the selected Stokowski runtime')
    receipt_path = runtime/'attempts'/issue/'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    workspace = runtime/'workspaces'/issue
    if (receipt.get('status') != 'succeeded' or receipt.get('child_tree_gone') is not True
        or receipt.get('scope_violations') or receipt.get('source_head') != manifest['base_revision']
        or git(workspace,'rev-parse','HEAD') != manifest['base_revision']
        or git(workspace,'branch','--show-current') != manifest['branch']):
        raise OperationError('Coding output is not reconciled against its admitted source')
    original = receipt.get('output_sha256',{})
    if not original or not set(original).issubset(spec['outputs']):
        raise OperationError('Candidate must account for every coding output')
    expected_acceptance = digest({'task':manifest['tasks'][issue],
                                  'native_receipt_sha256':file_hash(receipt_path),
                                  'profile':spec['profile']})
    if spec['acceptance_sha256'] != expected_acceptance:
        raise OperationError('Acceptance is not bound to the admitted task/output receipt')
    for name,sha in original.items():
        if file_hash(workspace/name) != sha:
            raise OperationError('Coding output changed after its receipt')
    if enrichment:
        request_path = runtime/'requests'/(issue+'.json')
        request = json.loads(request_path.read_text())
        native_binding = dict(branch=manifest['branch'],head=manifest['base_revision'],
            owner=manifest['tasks'][issue]['owner'],write_roots=manifest['tasks'][issue]['allowed_paths'],
            resources=manifest['tasks'][issue]['resources'],
            task_sha256=digest(dict(runtime=str(runtime),manifest=manifest,request=request)))
        lease = runtime_lease_ids(runtime,manifest)[issue]
        intent = json.loads((runtime/'attempts'/issue/'intent.json').read_text())
        dispatch = json.loads((runtime/'attempts'/issue/'dispatch-intent.json').read_text())
        admission = json.loads((runtime/'current-admission.json').read_text())
        entry = dict(issue=issue,issue_id=manifest['tasks'][issue]['issue_id'],
                     runtime=str(runtime),admission_sha256=file_hash(runtime/'current-admission.json'))
        policy = json.loads((runtime/'capacity-policy.json').read_text())
        database = Path(policy['symphony']['pool_path'])/'state.sqlite'
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            row = db.execute('SELECT status,outcome,binding,fingerprint FROM leases WHERE id=?',(lease,)).fetchone()
        if (receipt.get('origin') != 'native-coding' or receipt.get('exit_code') != 0
            or receipt.get('turn_completed') is not True or not receipt.get('session_id')
            or receipt.get('source_identity_changed') is not False
            or receipt.get('final_head') != manifest['base_revision']
            or receipt.get('final_branch') != manifest['branch']
            or receipt.get('parent_runtime') != str(runtime) or receipt.get('issue') != issue
            or receipt.get('parent_binding') != native_binding
            or receipt.get('binding_sha256') != digest(native_binding) or receipt.get('lease') != lease
            or intent != dict(lease=lease,binding=native_binding)
            or dispatch.get('expected_lease') != lease or dispatch.get('owner') != native_binding['owner']
            or dispatch.get('entry_sha256') != digest(entry)
            or dispatch.get('manifest_sha256') != file_hash(runtime/'manifest.json')
            or dispatch.get('request_sha256') != file_hash(request_path)
            or dispatch.get('provider_proof_sha256') != file_hash(runtime/'provider-proof.json')
            or admission.get('manifest_sha256') != file_hash(runtime/'manifest.json')
            or admission.get('request_sha256') != file_hash(request_path)
            or row is None or row[:2] != ('finished','succeeded')
            or json.loads(row[2]) != native_binding or row[3] != digest(native_binding)
            or spec['outputs'] != original
            or (spec['profile'] == ENRICHMENT_PROFILE and set(original) != set(manifest['tasks'][issue]['allowed_paths']))):
            raise OperationError('Enrichment origin is not an immutable finished native result')
        if git(candidate,'rev-list','--parents','-n','1',spec['head']).split() != [spec['head'],spec['base']]:
            raise OperationError('Candidate must be the direct reviewed contribution')
        changed = set(filter(None,git(candidate,'diff','--no-renames','--name-only','-z',
                                    spec['base'],spec['head']).split('\0')))
        if changed != set(original):
            raise OperationError('Candidate has unrelated contribution paths')
    head = git(candidate,'rev-parse','HEAD')
    branch = spec['branch'] if enrichment else manifest['branch']
    if head != spec['head'] or git(candidate,'branch','--show-current') != branch:
        raise OperationError('Candidate branch/head differs from selected publication')
    subprocess.run(['git','-C',str(candidate),'merge-base','--is-ancestor',
                    manifest['base_revision'],head],check=True,capture_output=True)
    if git(candidate,'status','--porcelain','--untracked-files=no'):
        raise OperationError('Candidate tracked source is dirty')
    accepted_policy = json.loads(git(candidate,'show',spec['base']+':repository-standard.json'))
    untracked = set(filter(None,git(candidate,'ls-files','--others','--exclude-standard','-z').split('\0')))
    if untracked-set(accepted_policy.get('runtime_hold_paths',[])):
        raise OperationError('Uncommitted maintained source needs publication before validation')
    for name,sha in spec['outputs'].items():
        if file_hash(candidate/name) != sha:
            raise OperationError('Candidate output hash mismatch')
        if enrichment and (git(candidate,'ls-tree',head,'--',name).split()[:2]
                not in (['100644','blob'],['100755','blob'])
                or hashlib.sha256(subprocess.check_output(
                    ['git','-C',str(candidate),'show',head+':'+name])).hexdigest() != sha):
            raise OperationError('Candidate committed output hash mismatch')
    differences = {name:{'native':sha,'candidate':spec['outputs'][name]}
                   for name,sha in original.items() if sha != spec['outputs'][name]}
    if differences and (not isinstance(derivation_reason,str) or not derivation_reason.strip()):
        raise OperationError('Changed coding output needs an explicit reviewed derivation')
    journal = Journal(runtime/'operations')
    key = operation_key(spec)
    path = runtime/'validation-bindings.json'
    bindings = json.loads(path.read_text()) if path.exists() else {'version':1,'issues':{},'history':[]}
    previous = bindings['issues'].get(issue)
    if previous and previous['operation_key'] != key:
        _,state = journal.read(previous['operation_key'])
        if state['status'] not in ('succeeded','failed','cancelled'):
            raise OperationError('Previous operation must reconcile before a new candidate')
    key = journal.prepare(spec)
    selected = {'operation_key':key,'source_head':head,'native_receipt_sha256':file_hash(receipt_path),
                'native_output_sha256':original,'derivation':differences,
                'derivation_reason':derivation_reason if differences else None}
    if enrichment:
        selected['candidate_root'] = str(candidate)
    if previous == selected:
        return key
    if previous:
        bindings['history'].append({'issue':issue,**previous})
    bindings['issues'][issue] = selected
    checkpoint(path,bindings)
    return key


def bind_extraction(runtime, spec, admission_path, candidate_root=None):
    """Consume an owner-provisioned immutable admission; never create coding proof.

    admission_path is a trusted owner input, not a candidate-controlled report.
    Its exact bytes are pinned by acceptance_sha256. Review hashes use digest().
    """
    validated(spec)
    if spec['version'] != 2:
        raise OperationError('Extraction binding requires v2')
    runtime = Path(runtime).resolve()
    if admission_path is None:
        raise OperationError('Missing trusted extraction admission')
    path = Path(admission_path)
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():
        raise OperationError('Admission must be a regular trusted owner file')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec['origin']['admission_sha256']:
        raise OperationError('Extraction admission hash mismatch')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise OperationError('Duplicate admission field')
            result[key] = value
        return result
    admission = json.loads(raw, object_pairs_hook=unique)
    fields = {'version','issue','issue_id','owner','head','base','branch','workspace',
              'source_commit','mapping','outputs','author','review'}
    if not isinstance(admission,dict) or set(admission) != fields or type(admission['version']) is not int or admission['version'] != 1:
        raise OperationError('Invalid extraction admission')
    for name in ('issue','issue_id','owner','head','base','branch','workspace','outputs'):
        if admission[name] != spec[name]:
            raise OperationError('Extraction admission differs: '+name)
    for name in ('source_commit','mapping','author'):
        if admission[name] != spec['origin'][name]:
            raise OperationError('Extraction origin differs: '+name)
    review = admission['review']
    if (not isinstance(review,dict) or set(review) != {'record','reviewer','decision','head','base'} or
        not isinstance(review['record'],str) or not review['record'].strip() or
        not isinstance(review['reviewer'],str) or not review['reviewer'].strip() or
        review['reviewer'] == admission['author'] or review['decision'] != 'accepted' or
        review['head'] != spec['head'] or review['base'] != spec['base'] or
        digest(review) != spec['origin']['review_sha256']):
        raise OperationError('Missing, stale or rejected independent review')
    remote_root = workspace_path(spec['workspace'])
    root = Path(candidate_root) if candidate_root is not None else remote_root
    if (not root.is_absolute() or str(root) != str(candidate_root if candidate_root is not None else remote_root) or
        root.resolve() != root or any(p.is_symlink() for p in (root,*root.parents)) or
        not root.is_dir()):
        raise OperationError('Local source root must be an absolute canonical non-symlink directory')
    if any(path.resolve().is_relative_to(candidate) for candidate in (root,remote_root)):
        raise OperationError('Admission must be provided outside local and remote candidate source')
    try:
        subprocess.run([sys.executable,'-c',candidate_check_code(spec,root)],check=True,
                       env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
    except subprocess.CalledProcessError as error:
        raise OperationError('Exact candidate identity/mapping/output check failed') from error
    journal = Journal(runtime/'operations')
    key = operation_key(spec)
    path = runtime/'validation-bindings.json'
    bindings = json.loads(path.read_text()) if path.exists() else {'version':1,'issues':{},'history':[]}
    previous = bindings['issues'].get(spec['issue'])
    if previous and previous['operation_key'] != key:
        _,state = journal.read(previous['operation_key'])
        if state['status'] not in ('succeeded','failed','cancelled'):
            raise OperationError('Previous operation must reconcile before a new candidate')
    key = journal.prepare(spec)
    selected = {'operation_key':key,'source_head':spec['head'],
                'origin':'reviewed-extraction','admission_sha256':spec['origin']['admission_sha256'],
                'review_sha256':spec['origin']['review_sha256'],'workspace':str(remote_root),
                'local_source_root':str(root),
                'execution':spec['execution'],'merge_accepted':False}
    if previous != selected:
        if previous:
            bindings['history'].append({'issue':spec['issue'],**previous})
        bindings['issues'][spec['issue']] = selected
        checkpoint(path,bindings)
    return key


def qualify_reviewed_source(spec, admission_path, candidate_root=None):
    """Revalidate trusted present admission and historical facts, without writes."""
    from stokowski_operations import reviewed_check_code, canonical_derivations
    validated(spec)
    if spec['version'] != 3:
        raise OperationError('Reviewed source requires v3')
    def regular(value):
        path = Path(value)
        if (not path.is_absolute() or path != path.resolve() or
            any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file()):
            raise OperationError('Nonregular reviewed source artifact')
        return path
    path = regular(admission_path)
    if file_hash(path) != spec['origin']['admission_sha256']:
        raise OperationError('Reviewed source admission drift')
    from stokowski_adapter import read_record
    admission = read_record(path)
    fields = {'version','issue','issue_id','owner','head','base','branch','workspace','local_source_root',
              'outputs','author','authors','provenance','review','control_sha256','policy_sha256','runner_sha256','executor_sha256','execution'}
    if set(admission) != fields or type(admission['version']) is not int or admission['version'] != 1:
        raise OperationError('Invalid reviewed source admission')
    for name in fields-{'version','author','authors','provenance','review'}:
        if admission[name] != spec[name]:
            raise OperationError('Reviewed source admission differs: '+name)
    for name in ('author','authors','provenance'):
        if admission[name] != spec['origin'][name]:
            raise OperationError('Manual lineage drift')
    review = admission['review']
    if (set(review) != {'path','sha256','reviewer','decision','head','base','outputs','derivations'}
        or review['reviewer'] in admission['authors']
        or review['reviewer'] in {ref['owner'] for ref in admission['provenance']}
        or not review['reviewer']
        or review['decision'] != 'accepted' or any(review[k] != spec[k] for k in ('head','base','outputs'))
        or digest(review) != spec['origin']['review_sha256']):
        raise OperationError('Independent accepted exact-head review required')
    review_path = regular(review['path'])
    if file_hash(review_path) != review['sha256']:
        raise OperationError('Independent review artifact drift')
    evidence = read_record(review_path)
    if evidence != {k:v for k,v in review.items() if k not in ('path','sha256')}:
        raise OperationError('Independent review artifact mismatch')
    if review['derivations'] != canonical_derivations(spec['origin']['provenance']):
        raise OperationError('Independent derivation attestation mismatch')
    # Receipt custody stays local; the fixed service check consumes only the
    # immutable contribution proof in the spec and the selected Git repository.
    for ref in admission['provenance']:
        if ref['derivation'] is not None and ref['derivation']['review_sha256'] != digest(review):
            raise OperationError('Contribution derivation review mismatch')
        receipt = read_record(regular(ref['path']))
        if (file_hash(ref['path']) != ref['sha256'] or receipt.get('status') != 'succeeded'
            or receipt.get('child_tree_gone') is not True or receipt.get('scope_violations')
            or receipt.get('accepted_delivery') is not False
            or receipt.get('parent_binding',{}).get('owner') != ref['owner']
            or receipt.get('parent_binding',{}).get('head') != ref['source_head']
            or receipt.get('issue') != spec['issue']
            or digest(receipt.get('parent_binding',{})) != receipt.get('binding_sha256')
            or not receipt.get('lease')
            or any(receipt.get(k) != ref[v] for k,v in
                   [('session_id','session'),('source_head','source_head'),('output_sha256','outputs')])):
            raise OperationError('Historical manual receipt mismatch')
    root = Path(spec['local_source_root'] if candidate_root is None else candidate_root)
    if str(root) != spec['local_source_root'] and str(root) != spec['workspace']:
        raise OperationError('Unqualified source mirror')
    if any(path.is_relative_to(Path(spec[k])) for k in ('workspace','local_source_root')):
        raise OperationError('Admission inside candidate')
    try:
        subprocess.run([sys.executable,'-c',reviewed_check_code(spec,root)],check=True,capture_output=True,
                       env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    except subprocess.CalledProcessError as error:
        raise OperationError('Reviewed source identity/output check failed') from error
    return admission


def bind_reviewed_source(runtime, spec, admission_path):
    """Prepare only the new validation Journal; no coding admission or lease."""
    admission = qualify_reviewed_source(spec, admission_path)
    runtime = Path(runtime)
    if runtime != runtime.resolve() or any(p.is_symlink() for p in (runtime,*runtime.parents)):
        raise OperationError('Aliased reviewed validation runtime')
    path = runtime/'validation-bindings.json'
    selected = dict(operation_key=operation_key(spec),source_head=spec['head'],origin='reviewed-source-v1',
        admission_path=str(admission_path),admission_sha256=spec['origin']['admission_sha256'],
        local_source_root=spec['local_source_root'],workspace=spec['workspace'])
    bindings = dict(version=1,issues={spec['issue']:selected},history=[])
    if path.exists() and json.loads(path.read_text()) != bindings:
        raise OperationError('Immutable reviewed source selection conflict')
    key = Journal(runtime/'operations').prepare(spec)
    if not path.exists():
        checkpoint(path,bindings)
    return key


async def tick(runtime,transport=None):
    bindings = json.loads((runtime/'validation-bindings.json').read_text())
    journal = Journal(runtime/'operations')
    transport = transport or WindmillMCP()
    try:
        keys = [(issue,value['operation_key']) for issue,value in bindings['issues'].items()]
        results = await asyncio.gather(*(journal.tick(key,transport) for _,key in keys))
        projection = {'version':1,
            'dispatcher_mode':'explicit-draft-test' if getattr(transport,'preview',False) else 'deployed',
            'issues':{issue:{'operation_key':key,**state,
            'origin':bindings['issues'][issue].get('origin','native-coding'),
            'execution':bindings['issues'][issue].get('execution'),
            'stage':'validation-verified' if state['status']=='succeeded' else
                    ('repair-required' if state['status']=='failed' else 'validation-pending'),
            'merge_accepted':False} for (issue,key),state in zip(keys,results)}}
        from stokowski_refill import observe_refill
        boundary = digest({issue:{k:row.get(k) for k in ('operation_key','status','stage')}
                           for issue,row in projection['issues'].items()})
        prior_path = runtime/'validation-stage.json'
        prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
        projection['refill_boundary'] = boundary
        projection['refill'] = (prior['refill'] if prior.get('refill_boundary') == boundary
                                and 'refill' in prior else observe_refill(runtime, projection['issues']))
        checkpoint(runtime/'validation-stage.json',projection)
        return projection
    finally:
        await transport.close()


async def continue_stage(runtime,duration,preview=False):
    deadline = time.monotonic()+duration
    while True:
        result = await tick(runtime,WindmillMCP(preview=preview))
        result['dispatcher_mode'] = 'explicit-draft-test' if preview else 'deployed'
        if all(row['status'] in TERMINAL for row in result['issues'].values()):
            return result
        if time.monotonic() >= deadline:
            return result
        await asyncio.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['bind','bind-extraction','bind-reviewed-source','tick','run','cancel','status'])
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--spec',type=Path)
    parser.add_argument('--derivation-reason')
    parser.add_argument('--admission',type=Path)
    parser.add_argument('--candidate-root',type=Path)
    parser.add_argument('--issue')
    parser.add_argument('--duration',type=int,default=120)
    parser.add_argument('--preview-dispatch',action='store_true',help='Explicit draft testing; never a deployment fallback')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if not runtime.is_relative_to(SOURCE/'.delivery/stokowski'):
        raise OperationError('Use the existing private OffMenu runtime')
    if args.action == 'bind-reviewed-source':
        print(json.dumps({'operation_key':bind_reviewed_source(runtime,json.loads(args.spec.read_text()),args.admission)}))
    elif args.action == 'bind-extraction':
        print(json.dumps({'operation_key':bind_extraction(runtime,json.loads(args.spec.read_text()),args.admission,args.candidate_root)}))
    elif args.action == 'bind':
        print(json.dumps({'operation_key':bind(runtime,json.loads(args.spec.read_text()),args.derivation_reason,
                                             candidate_root=args.candidate_root)}))
    elif args.action in ('tick','run'):
        if not 1 <= args.duration <= 600:
            raise OperationError('Invalid finite stage duration')
        result = asyncio.run(tick(runtime,WindmillMCP(preview=args.preview_dispatch))
                    if args.action=='tick' else continue_stage(runtime,args.duration,args.preview_dispatch))
        print(json.dumps(result))
    else:
        bindings = json.loads((runtime/'validation-bindings.json').read_text())
        journal = Journal(runtime/'operations')
        if args.action == 'cancel':
            journal.cancel(bindings['issues'][args.issue]['operation_key'])
        print(json.dumps({issue:journal.read(value['operation_key'])[1]
                          for issue,value in bindings['issues'].items()}))


if __name__ == '__main__':
    main()
