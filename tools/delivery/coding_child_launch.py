"""Fixed installed confinement binding; never read authentication contents.

This is source-only until independently reviewed service adoption. Policy absence
is a proven prelaunch refusal, never permission to use the old host route.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from symphony_protocol import BINARY

POLICY = Path('/etc/offmenu/coding-confinement.json')
DROPPER = '/usr/local/libexec/offmenu-coding-dropper'
GUARD = '/usr/local/libexec/offmenu-coding-guard'
RUNTIME = Path('/home/user/src/offmenu/.delivery/stokowski')


class ConfinementError(ValueError):
    """No child has been started by the launch binder."""


def trusted_file(path, mode=None):
    path = Path(path)
    if not path.is_absolute():
        raise ConfinementError('confinement_absolute_path')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if (info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode)
                or (part != path and not stat.S_ISDIR(info.st_mode))):
            raise ConfinementError('confinement_root_control')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o6000:
        raise ConfinementError('confinement_regular_file')
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ConfinementError('confinement_mode')
    return path


def installed_policy():
    trusted_file(POLICY, 0o644)
    policy = json.loads(POLICY.read_text())
    if (set(policy) != {'schema', 'sha256'} or policy['schema'] != 'coding-confinement-v1'
            or not isinstance(policy['sha256'], dict)
            or set(policy['sha256']) != {DROPPER, GUARD, BINARY}):
        raise ConfinementError('confinement_policy')
    for name, expected in policy['sha256'].items():
        path = trusted_file(name)
        if (not isinstance(expected, str) or len(expected) != 64
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ConfinementError('confinement_hash')
    return policy


def owned_path(value, *, missing=False):
    path = Path(value)
    if (not path.is_absolute() or not path.is_relative_to(RUNTIME)
            or '..' in path.parts or len(str(path)) > 4095):
        raise ConfinementError('confinement_runtime_path')
    target = path.parent if missing and not os.path.lexists(path) else path
    if target.resolve(strict=True) != target:
        raise ConfinementError('confinement_symlink')
    for part in [target, *target.parents]:
        if part == RUNTIME.parent:
            break
        info = part.lstat()
        if info.st_uid != 1000 or info.st_mode & 0o022:
            raise ConfinementError('confinement_runtime_owner')
    return str(path)


def bind_native(command, workspace, environment):
    """Accept only the exact reviewed native argv; no path/policy override API."""
    installed_policy()
    if len(command) != 17 or command[0] != BINARY:
        raise ConfinementError('confinement_native_argv')
    mode = command[5]
    expected = [BINARY, 'exec', '--json', '--ignore-user-config', '--sandbox',
                mode, '-c', 'approval_policy="never"', '-c',
                'model_reasoning_effort="medium"', '--model', 'gpt-6.1-sol',
                '--cd', str(workspace), '--output-last-message', command[-2], '-']
    # Keep this comparison exact; arbitrary executable/options are not forwarded.
    if mode not in {'read-only', 'workspace-write'} or command != expected:
        raise ConfinementError('confinement_native_argv')
    root = owned_path(workspace)
    output = owned_path(command[-2], missing=True)
    home = owned_path(environment.get('CODEX_HOME', ''))
    state = owned_path(environment.get('CODEX_SQLITE_HOME', ''), missing=True)
    if (
            '/workspaces/' not in root or '/attempts/' not in output
            or Path(output).name != 'final-message.txt'
            or not Path(home).name.startswith('codex-home-')
            or Path(state).name != 'codex-state'
            or Path(home).parent != Path(output).parent
            or Path(state).parent != Path(output).parent):
        raise ConfinementError('confinement_attempt_paths')
    auth = Path(home)/'auth.json'
    if (stat.S_IMODE(Path(home).stat().st_mode) != 0o700
            or not auth.is_symlink() or os.readlink(auth) != '/home/user/.codex/auth.json'):
        raise ConfinementError('confinement_auth_reference')
    return (['/usr/bin/sudo', '-n', '--', DROPPER, mode, root, output, home, state],
            {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
