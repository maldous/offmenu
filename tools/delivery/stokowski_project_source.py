"""Private project source acquisition; installed controller pins stay separate.

The caller supplies owner-qualified acceptance. A Git branch tip, a clone and
this module's receipt never grant source acceptance or dispatch permission.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

from symphony_capacity import AdmissionError, valid_branch
from stokowski_adapter import clone_current_workspace
from stokowski_worker import child_environment


def _git(repository, *arguments):
    environment = child_environment(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    return subprocess.check_output(['git','-c','safe.directory='+str(repository),
        '-C',str(repository),*arguments],text=True,env=environment).strip()


def materialize_accepted_project_source(repository, destination, *, head, tree, branch):
    """Bundle only develop's history; checkout only the accepted revision.

    No source checkout/HEAD/ref changes. The temporary acquisition can contain
    later Git objects, but no later file bytes are checked out or executed.
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
    # The accepted revision may precede an unreviewed local develop tip.
    # It must still belong to the selected develop history.
    subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
        'merge-base','--is-ancestor',head,'refs/heads/develop'],check=True,
        capture_output=True,env=child_environment(os.environ))
    if destination.exists():
        clone_current_workspace(repository,destination,head,branch)
        return
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    preparation = Path(tempfile.mkdtemp(prefix='.'+destination.name+'-accepted-',
                                       dir=destination.parent))
    bundle = preparation/'develop.bundle'
    subprocess.run(['git','-c','safe.directory='+str(repository),'-C',str(repository),
        'bundle','create',str(bundle),'refs/heads/develop'],check=True,
        capture_output=True,env=child_environment(os.environ),timeout=90)
    selected = preparation/'selected'
    subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(bundle),str(selected)],
        check=True,capture_output=True,env=child_environment(os.environ),timeout=90)
    subprocess.run(['git','-C',str(selected),'-c','core.hooksPath=/dev/null',
        'checkout','-b',branch,head],check=True,capture_output=True,
        env=child_environment(os.environ))
    clone_current_workspace(selected,destination,head,branch)
    if (_git(destination,'rev-parse','HEAD') != head
        or _git(destination,'rev-parse','HEAD^{tree}') != tree):
        raise AdmissionError('project_source_acquisition_drift')
