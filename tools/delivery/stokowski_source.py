"""Private project source acquisition; installed controller pins stay separate.

The caller supplies owner-qualified acceptance. A Git branch tip, a clone and
this module's receipt never grant source acceptance or dispatch permission.
"""
import os
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import errno
import stat

from symphony_capacity import AdmissionError, valid_branch
from stokowski_adapter import clone_current_workspace
from stokowski_worker import child_environment


def _git(repository, *arguments):
    environment = child_environment(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    return subprocess.check_output(['git','-c','safe.directory='+str(repository),
        '-C',str(repository),*arguments],text=True,env=environment).strip()


def materialize_accepted_project_source(repository, destination, *, head, tree, branch):
    """Bundle only the immutable accepted ref; checkout its exact revision.

    No source checkout/HEAD changes; only the scoped immutable ref is used.
    The existing proven clone helper normalizes the final private workspace.
    """
    repository,destination = Path(repository),Path(destination)
    if (not repository.is_absolute() or repository != repository.resolve()
        or not destination.is_absolute() or destination != destination.resolve()
        or repository.is_relative_to(destination)
        or not re.fullmatch('[0-9a-f]{40}',str(head))
        or not re.fullmatch('[0-9a-f]{40}',str(tree)) or not valid_branch(branch)):
        raise AdmissionError('project_source_path_or_identity')
    if _git(repository,'rev-parse','--show-toplevel') != str(repository):
        raise AdmissionError('project_source_repository_root')
    if _git(repository,'rev-parse',head+'^{tree}') != tree:
        raise AdmissionError('project_source_tree')
    reference = 'refs/offmenu/accepted/'+head
    if _git(repository,'rev-parse',reference) != head:
        raise AdmissionError('project_source_accepted_ref')
    if destination.exists():
        clone_current_workspace(repository,destination,head,branch)
        return
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    preparation = Path(tempfile.mkdtemp(prefix='.'+destination.name+'-accepted-',
                                       dir=destination.parent))
    bundle = preparation/'develop.bundle'
    subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
        'bundle','create',str(bundle),reference],check=True,
        capture_output=True,env=child_environment(os.environ),timeout=90)
    selected = preparation/'selected'
    subprocess.run(['git','init','--quiet',str(selected)],
        check=True,capture_output=True,env=child_environment(os.environ),timeout=90)
    subprocess.run(['git','-C',str(selected),'fetch','--no-tags','--no-write-fetch-head',
        str(bundle),reference+':refs/heads/'+branch],check=True,capture_output=True,
        env=child_environment(os.environ),timeout=90)
    subprocess.run(['git','-C',str(selected),'-c','core.hooksPath=/dev/null',
        'checkout',branch],check=True,capture_output=True,
        env=child_environment(os.environ))
    clone_current_workspace(selected,destination,head,branch)
    if (_git(destination,'rev-parse','HEAD') != head
        or _git(destination,'rev-parse','HEAD^{tree}') != tree):
        raise AdmissionError('project_source_acquisition_drift')


def _bytes(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _record(path):
    if path != path.resolve() or not path.is_file() or path.stat().st_uid != os.getuid():
        raise AdmissionError('project_source_private_record')
    return json.loads(path.read_bytes())


def _immutable(path, value):
    raw = _bytes(value)
    if path.exists():
        if path != path.resolve() or path.read_bytes() != raw:
            raise AdmissionError('project_source_immutable_drift')
        return
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        os.fchmod(stream.fileno(),0o600)
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    directory = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


def _accepted(value):
    if (not isinstance(value,dict) or set(value) != {'repository','branch','head','tree','evidence'}
        or value['repository'] != 'maldous/offmenu' or value['branch'] != 'develop'
        or any(not re.fullmatch('[0-9a-f]{40}',str(value[k])) for k in ('head','tree'))
        or not isinstance(value['evidence'],dict) or set(value['evidence']) != {'path','sha256'}):
        raise AdmissionError('project_source_accepted_shape')
    evidence = value['evidence'];path = Path(evidence['path'])
    if (not path.is_absolute() or path != path.resolve() or not path.is_file()
        or not re.fullmatch('[0-9a-f]{64}',str(evidence['sha256']))
        or _sha(path) != evidence['sha256']):
        raise AdmissionError('project_source_accepted_evidence_drift')
    # Semantic acceptance is exclusively the trusted native accessor's job.
    return value


def _snapshot(repository):
    return dict(head=_git(repository,'rev-parse','HEAD'),
        branch=_git(repository,'branch','--show-current'),
        tracked_status=_git(repository,'--no-optional-locks','status','--porcelain','--untracked-files=no'))


def _source_paths(config, identifier, policy):
    if not re.fullmatch(r'UIF-[1-9][0-9]*',identifier):
        raise AdmissionError('project_source_issue')
    descriptor = policy.get('project_source',{})
    if (set(descriptor) != {'repository','branch','origin','source_repository','seed','accepted_facts_path'}
        or descriptor['repository'] != 'maldous/offmenu' or descriptor['branch'] != 'develop'
        or descriptor['origin'] != 'git@github.com:maldous/offmenu.git'
        or not isinstance(descriptor['seed'],dict) or set(descriptor['seed']) != {'head','tree'}
        or any(not re.fullmatch('[0-9a-f]{40}',str(descriptor['seed'][k])) for k in ('head','tree'))):
        raise AdmissionError('project_source_owner_policy')
    repository = Path(descriptor['source_repository'])
    if (not repository.is_absolute() or repository != repository.resolve()
        or _git(repository,'rev-parse','--show-toplevel') != str(repository)
        or _git(repository,'remote','get-url','origin') != descriptor['origin']):
        raise AdmissionError('project_source_repository_binding')
    private_root = Path(config['runtime_root'])
    root = private_root/'project-sources'
    selection_path = root/(identifier+'.json')
    facts = Path(descriptor['accepted_facts_path'])
    if (not private_root.is_absolute() or private_root != private_root.resolve()
        or any(path != path.resolve() or not path.is_relative_to(private_root)
               for path in (root,selection_path))
        or not facts.is_absolute() or facts != facts.resolve()
        or (facts != Path('/var/lib/offmenu-publisher/accepted-sources/latest.json')
            and not facts.is_relative_to(private_root))):
        raise AdmissionError('project_source_private_path')
    route = {k:descriptor[k] for k in ('repository','branch','origin','source_repository')}
    return descriptor,repository,root,selection_path,route


def _read_checkout(checkout, head, tree, branch):
    """Retained custody/identity checks without a creation-capable code path."""
    if checkout != checkout.resolve() or not checkout.is_dir():
        raise AdmissionError('project_source_not_materialized')
    fd = os.open(checkout,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for _,_,files,directory in os.fwalk('.',dir_fd=fd,follow_symlinks=False):
            info = os.fstat(directory)
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise AdmissionError('project_source_checkout_custody')
            try: os.getxattr(directory,'system.posix_acl_default')
            except OSError as error:
                if error.errno != errno.ENODATA: raise
            else: raise AdmissionError('project_source_checkout_custody')
            for name in files:
                info = os.stat(name,dir_fd=directory,follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode): continue
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or info.st_mode & 0o022):
                    raise AdmissionError('project_source_checkout_custody')
    finally: os.close(fd)
    if (_git(checkout,'rev-parse','HEAD') != head
        or _git(checkout,'rev-parse','HEAD^{tree}') != tree
        or _git(checkout,'branch','--show-current') != branch
        or _git(checkout,'--no-optional-locks','status','--porcelain','--untracked-files=all')
        or (checkout/'.git/objects/info/alternates').exists()):
        raise AdmissionError('project_source_checkout_drift')


def read_project_source(config, identifier, policy):
    """Read a frozen task source during protected configuration construction.

    The caller has qualified control policy; this cannot construct CurrentWork,
    choose a new accepted revision, create a lock/receipt, fetch or repair data.
    """
    _,repository,root,selection_path,route = _source_paths(config,identifier,policy)
    if not selection_path.exists():
        raise AdmissionError('project_source_not_materialized')
    selection = _record(selection_path)
    if (set(selection) != {'version','owner','issue','route','accepted','control_source_head','source_before'}
        or selection['version'] != 1 or selection['owner'] != config['owner']
        or selection['issue'] != identifier or selection['route'] != route):
        raise AdmissionError('project_source_selection_drift')
    selected = _accepted(selection['accepted'])
    directory = root/selected['head']/identifier
    checkout = directory/'checkout'
    path = directory/'acquisition.json'
    if directory != directory.resolve() or not path.exists():
        raise AdmissionError('project_source_not_materialized')
    branch = 'bugfix/owner-policy-'+identifier.lower()+'-'+selected['head'][:12]
    expected = dict(version=1,selection_sha256=hashlib.sha256(_bytes(selection)).hexdigest(),
        source_checkout=str(checkout),base=selected['head'],tree=selected['tree'],branch=branch,
        evidence=selected['evidence'],source_repository=str(repository),
        source_ref='refs/offmenu/accepted/'+selected['head'])
    if _record(path) != expected:
        raise AdmissionError('project_source_acquisition_receipt_drift')
    _read_checkout(checkout,selected['head'],selected['tree'],branch)
    return {k:expected[k] for k in ('source_checkout','base','branch','tree','evidence')} | dict(
        acquisition_ref=dict(path=str(path),sha256=_sha(path)))


def acquire_project_source(current, issue, policy, accepted):
    """Consume trusted accepted_project_source; never derive acceptance here.

    Only the existing guarded owner boundary calls this with an accessor result.
    Per-issue selection survives later accepted-source advancement. Network
    ambiguity retains one intent and never retries credentials or the fetch.
    """
    import fcntl
    current.guard()
    identifier = issue if isinstance(issue,str) else issue.identifier
    if not re.fullmatch(r'UIF-[1-9][0-9]*',identifier):
        raise AdmissionError('project_source_issue')
    descriptor,repository,root,selection_path,route = _source_paths(current.config,identifier,policy)
    if selection_path.exists():
        selection = _record(selection_path)
        if (set(selection) != {'version','owner','issue','route','accepted','control_source_head','source_before'}
            or selection['version'] != 1 or selection['owner'] != current.config['owner']
            or selection['issue'] != identifier or selection['route'] != route):
            raise AdmissionError('project_source_selection_drift')
        selected = _accepted(selection['accepted'])
    else:
        if (getattr(current,'read_only',False) or getattr(current,'stopping',False)
            or not getattr(current,'owner_custody',None)):
            raise AdmissionError('project_source_not_materialized')
        selected = _accepted(accepted)
        selection = dict(version=1,owner=current.config['owner'],issue=identifier,route=route,
            accepted=selected,control_source_head=current.config['source_head'],source_before=_snapshot(repository))
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        _immutable(selection_path,selection)
    directory = current.private(str(root/selected['head']/identifier))
    checkout = current.private(str(directory/'checkout'))
    receipt_path = current.private(str(directory/'acquisition.json'))
    branch = 'bugfix/owner-policy-'+identifier.lower()+'-'+selected['head'][:12]
    receipt = dict(version=1,selection_sha256=hashlib.sha256(_bytes(selection)).hexdigest(),
        source_checkout=str(checkout),base=selected['head'],tree=selected['tree'],branch=branch,
        evidence=selected['evidence'],source_repository=str(repository),
        source_ref='refs/offmenu/accepted/'+selected['head'])
    if getattr(current,'read_only',False) and not receipt_path.exists():
        raise AdmissionError('project_source_not_materialized')
    if not getattr(current,'read_only',False):
        directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    flags = os.O_RDONLY if getattr(current,'read_only',False) else os.O_CREAT|os.O_RDWR
    fd = os.open(directory/'acquisition.lock',flags|os.O_NOFOLLOW,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise AdmissionError('project_source_acquisition_owned') from None
        if receipt_path.exists():
            if _record(receipt_path) != receipt:
                raise AdmissionError('project_source_acquisition_receipt_drift')
            clone_current_workspace(repository,checkout,selected['head'],branch)
            if _git(checkout,'rev-parse','HEAD^{tree}') != selected['tree']:
                raise AdmissionError('project_source_tree')
        else:
            if getattr(current,'stopping',False) or not getattr(current,'owner_custody',None):
                raise AdmissionError('project_source_owner_required')
            before = _snapshot(repository)
            head = selected['head']
            present = subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
                'cat-file','-e',head+'^{commit}'],env=child_environment(os.environ),capture_output=True).returncode == 0
            fetch_intent = directory/'object-fetch-intent.json'
            if not present:
                if fetch_intent.exists():
                    raise AdmissionError('project_source_fetch_requires_reconciliation')
                _immutable(fetch_intent,dict(head=head,origin=descriptor['origin']))
                environment = child_environment(os.environ)
                environment.update(GIT_TERMINAL_PROMPT='0',GIT_SSH_COMMAND='ssh -o BatchMode=yes')
                subprocess.run(['git','-c','safe.directory='+str(repository),'-c','gc.auto=0',
                    '-c','maintenance.auto=false','-C',str(repository),'fetch','--no-tags',
                    '--no-write-fetch-head',descriptor['origin'],head],check=True,
                    capture_output=True,env=environment,timeout=90)
            if _git(repository,'rev-parse',head+'^{tree}') != selected['tree']:
                raise AdmissionError('project_source_tree')
            reference = receipt['source_ref']
            ref = subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
                'rev-parse','--verify','--quiet',reference],env=child_environment(os.environ),
                capture_output=True,text=True)
            if ref.returncode == 1:
                subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
                    'update-ref',reference,head,'0'*40],check=True,capture_output=True,
                    env=child_environment(os.environ))
            elif ref.returncode != 0 or ref.stdout.strip() != head:
                raise AdmissionError('project_source_accepted_ref_drift')
            materialize_accepted_project_source(repository,checkout,head=head,tree=selected['tree'],branch=branch)
            if _snapshot(repository) != before:
                raise AdmissionError('project_source_shared_checkout_changed')
            current.guard()
            _immutable(receipt_path,receipt)
        return {k:receipt[k] for k in ('source_checkout','base','branch','tree','evidence')} | dict(
            acquisition_ref=dict(path=str(receipt_path),sha256=_sha(receipt_path)))
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)
