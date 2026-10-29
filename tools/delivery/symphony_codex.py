"""OffMenu-owned Codex configuration isolation, without credential copying."""
from contextlib import contextmanager
from pathlib import Path
import tempfile


@contextmanager
def isolated_codex_environment(base_environment, runtime):
    """Reference existing file-backed auth while excluding workstation config.

    Caller must reap its owned process group before leaving this context. Nothing
    is read from auth.json; only its existing path is referenced by a symlink.
    """
    environment = base_environment.copy()
    original_home = Path(environment.get('CODEX_HOME', str(Path.home()/'.codex')))
    existing_auth = original_home/'auth.json'
    if not existing_auth.is_file():
        raise RuntimeError('Existing file-backed Codex authentication is unavailable')
    with tempfile.TemporaryDirectory(prefix='codex-home-', dir=runtime) as directory:
        home = Path(directory)
        home.chmod(0o700)
        (home/'auth.json').symlink_to(existing_auth.resolve())
        environment['CODEX_HOME'] = str(home)
        environment['CODEX_SQLITE_HOME'] = str(Path(runtime)/'codex-state')
        yield environment
