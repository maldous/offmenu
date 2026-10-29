"""Local immutable cache and resumable publication, with no acquisition path."""
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import uuid
import zlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'wikibooks'
RELEASE = '2024-07-31'
MAX_INPUT = 64 * 1024 * 1024
MAX_OUTPUT = 256 * 1024 * 1024
OUTPUT_FILES = ('manifest.json', 'normalized.jsonl.gz', 'quarantine.json')
HEX = re.compile(r'[0-9a-f]{64}')


class RefreshError(ValueError):
    """Messages are fixed error codes safe for a shareable receipt."""


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RefreshError('duplicate-json-key')
            result[key] = value
        return result
    def constant(_):
        raise RefreshError('nonfinite-json-number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise RefreshError('invalid-manifest-fields')


def timestamp(value):
    if not isinstance(value, str):
        raise RefreshError('invalid-acquisition-timestamp')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise RefreshError('invalid-acquisition-timestamp') from error
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise RefreshError('acquisition-timestamp-must-be-utc')
    return result


def load_manifest(path):
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size > 16384:
        raise RefreshError('manifest-missing-or-too-large')
    value = strict_json(path.read_bytes())
    exact_keys(value, ('schemaVersion', 'sourceId', 'releaseId', 'scope', 'input', 'acquiredAt', 'rights'))
    if value['schemaVersion'] != 'offmenu-refresh-input/1':
        raise RefreshError('unsupported-manifest-version')
    if value['sourceId'] != SOURCE or value['releaseId'] != RELEASE:
        raise RefreshError('adapter-not-implemented')
    if value['scope'] not in ('synthetic-fixture', 'historical-source-snapshot'):
        raise RefreshError('invalid-input-scope')
    exact_keys(value['input'], ('path', 'bytes', 'sha256'))
    item = value['input']
    if not isinstance(item['path'], str) or '\\' in item['path']:
        raise RefreshError('unsafe-input-path')
    parts = PurePosixPath(item['path'])
    if parts.is_absolute() or '..' in parts.parts or not parts.parts or str(parts) != item['path']:
        raise RefreshError('unsafe-input-path')
    if type(item['bytes']) is not int or not 1 <= item['bytes'] <= MAX_INPUT:
        raise RefreshError('input-exceeds-pilot-size-limit')
    if not isinstance(item['sha256'], str) or not HEX.fullmatch(item['sha256']):
        raise RefreshError('invalid-input-sha256')
    timestamp(value['acquiredAt'])
    exact_keys(value['rights'], ('status', 'license', 'attribution'))
    rights = value['rights']
    if rights['status'] != 'reviewed-local-use' or rights['license'] != 'CC BY-SA 4.0':
        raise RefreshError('source-rights-not-approved')
    expected = 'Wikibooks contributors; dataset Gosse Minnema, July 2024'
    if rights['attribution'] != expected:
        raise RefreshError('source-attribution-mismatch')
    return value


def public_pins(manifest):
    result = {k: v for k, v in manifest.items() if k != 'input'}
    result['input'] = {k: v for k, v in manifest['input'].items() if k != 'path'}
    return result


def cache_policy(manifest, now=None, force=False):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise RefreshError('policy-clock-must-be-aware')
    acquired = timestamp(manifest['acquiredAt'])
    age = (now - acquired).total_seconds()
    if age < 0:
        raise RefreshError('acquisition-timestamp-in-future')
    action = ('explicit-refresh-requested' if force else
              'reuse-verified-cache' if age < 30 * 86400 else 'conditional-revalidation-required')
    return {'schemaVersion': 'offmenu-refresh-policy/1', 'sourceId': SOURCE,
            'releaseId': RELEASE, 'inputSha256': manifest['input']['sha256'],
            'minimumReuseDays': 30, 'acquisitionAgeDays': int(age // 86400),
            'decision': action, 'identityScope': 'source-release-content-not-country',
            'mtimeUsedForFreshness': False, 'assetBytesVerifiedByThisPlan': False,
            'onlineAcquisition': 'not-implemented', 'networkRequests': 0,
            'nextOnlineStep': 'conditional-validator-check-before-any-download' if action != 'reuse-verified-cache' else 'none'}


def safe_path(path):
    """Reject symlink components, including existing ancestors of new paths."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RefreshError('symlink-path-rejected')
    return path


def digest(path, *, max_bytes=None):
    path = safe_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise RefreshError('regular-file-required')
    if max_bytes is not None and before.st_size > max_bytes:
        raise RefreshError('asset-size-limit-exceeded')
    value = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise RefreshError('input-changed-during-read')
        consumed = 0
        while True:
            limit = min(1024 * 1024, max_bytes - consumed + 1) if max_bytes is not None else 1024 * 1024
            block = stream.read(limit)
            if not block:
                break
            consumed += len(block)
            if max_bytes is not None and consumed > max_bytes:
                raise RefreshError('asset-size-limit-exceeded')
            value.update(block)
        after = os.fstat(stream.fileno())
    current = path.stat()
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if fields(before) != fields(after) or fields(after) != fields(current):
        raise RefreshError('input-changed-during-read')
    return {'bytes': after.st_size, 'sha256': value.hexdigest()}


def verify(path, expected):
    path = safe_path(path)
    if path.stat().st_size != expected['bytes']:
        raise RefreshError('asset-checksum-mismatch')
    actual = digest(path, max_bytes=expected['bytes'])
    if actual != {k: expected[k] for k in ('bytes', 'sha256')}:
        raise RefreshError('asset-checksum-mismatch')
    return actual


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path, value):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = safe_path(path.with_name(path.name + '.pending'))
    # Receipts are named by a validated persisted run ID and written under the
    # workspace lock. Only that run's own interrupted receipt is reclaimed.
    if temporary.exists():
        if not temporary.is_file():
            raise RefreshError('invalid-receipt-partial')
        temporary.unlink()
    try:
        with temporary.open('xb') as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()



@contextlib.contextmanager
def writer_lock(path):
    """Kernel ownership survives neither exit nor SIGKILL; keep the inode stable."""
    path = safe_path(path)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RefreshError('writer-lock-held') from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, canonical({'pid': os.getpid()}))
        os.fsync(descriptor)
        yield descriptor
    finally:
        # Never unlink a flock file: a new inode could allow simultaneous writers.
        os.close(descriptor)


def code_identity(*, extra_files=(), packaged=False):
    files = sorted((ROOT / 'offmenu/refresh').glob('*.py'))
    files += [ROOT / 'offmenu/__init__.py'] if packaged else [ROOT / 'scripts/collect-wikibooks.py']
    files += [ROOT / name for name in extra_files]
    pins = {str(p.relative_to(ROOT)): digest(p)['sha256'] for p in files}
    runtime = {'python': platform.python_version(), 'implementation': platform.python_implementation(),
               'zlib': zlib.ZLIB_RUNTIME_VERSION, 'sqlite': sqlite3.sqlite_version}
    code_digest = sha(canonical({'files': pins, 'runtime': runtime}))
    git = ['git', '-C', str(ROOT)]
    try:
        commit = subprocess.check_output(git + ['rev-parse', '--verify', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(git + ['status', '--porcelain', '--', 'offmenu/refresh', 'scripts/collect-wikibooks.py', *extra_files], stderr=subprocess.DEVNULL, text=True))
    except (subprocess.CalledProcessError, FileNotFoundError):
        if not packaged:
            raise RefreshError('git-code-identity-unavailable') from None
        commit, dirty = None, None
    if commit is not None and not re.fullmatch(r'[0-9a-f]{40,64}', commit):
        raise RefreshError('invalid-git-code-identity')
    return {'codeCommit': commit, 'codeDirty': dirty, 'codeFingerprint': code_digest, 'runtime': runtime}


class BoundedReader:
    """Limit bytes copied even if another process grows the source file."""
    def __init__(self, stream, limit):
        self.stream, self.remaining = stream, limit

    def read(self, size=-1):
        size = self.remaining + 1 if size < 0 else min(size, self.remaining + 1)
        result = self.stream.read(size)
        self.remaining -= len(result)
        if self.remaining < 0:
            raise RefreshError('asset-size-limit-exceeded')
        return result


def verify_source(source, expected):
    if isinstance(source, bytes):
        actual = {'bytes': len(source), 'sha256': sha(source)}
        if actual != {k: expected[k] for k in ('bytes', 'sha256')}:
            raise RefreshError('asset-checksum-mismatch')
        return actual
    return verify(source, expected)


def cache_input(source, target, expected, *, force=False, copy_id):
    # A persisted run owns exactly this temporary. Resume cleans only its own
    # uncommitted copy, never arbitrary glob-matched or legacy assets.
    temporary = safe_path(target.with_name(target.name + '.copy-' + copy_id))
    if temporary.exists():
        if not temporary.is_file():
            raise RefreshError('invalid-cache-copy-partial')
        temporary.unlink()
    if target.exists() and not force:
        verify(target, expected)
        return
    try:
        before = verify_source(source, expected)
        reader = io.BytesIO(source) if isinstance(source, bytes) else source.open('rb')
        with reader as src, temporary.open('xb') as out:
            shutil.copyfileobj(BoundedReader(src, expected['bytes']), out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        verify(temporary, expected)
        if verify_source(source, expected) != before:
            raise RefreshError('input-changed-during-copy')
        if target.exists():
            verify(target, expected)
        else:
            # Under the workspace-wide writer lock; never replace existing blobs.
            os.link(temporary, target)
            fsync_directory(target.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def artifact_inventory(directory, *, files=OUTPUT_FILES, maximum=MAX_OUTPUT):
    safe_path(directory)
    if {p.name for p in directory.iterdir()} != set(files):
        raise RefreshError('unexpected-output-assets')
    sizes = {name: safe_path(directory / name).stat().st_size for name in files}
    if sum(sizes.values()) > maximum:
        raise RefreshError('output-exceeds-pilot-size-limit')
    assets = {name: digest(directory / name, max_bytes=sizes[name]) for name in files}
    if sum(x['bytes'] for x in assets.values()) > maximum:
        raise RefreshError('output-exceeds-pilot-size-limit')
    return assets


def validate_artifacts(directory, assets, *, files=OUTPUT_FILES, maximum=MAX_OUTPUT):
    if artifact_inventory(directory, files=files, maximum=maximum) != assets:
        raise RefreshError('output-checksum-mismatch')


def transform(cache, destination, manifest, *, lock_fds=()):
    runner = ROOT / 'offmenu/refresh/runner.py'
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    result = subprocess.run([sys.executable, '-I', '-B', str(runner), str(cache), str(destination), manifest['acquiredAt']],
                            cwd=ROOT, env=environment, pass_fds=lock_fds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if result.returncode:
        raise RefreshError('adapter-failed-no-output-published')
    return artifact_inventory(destination)


def replay(manifest, input_root, workspace, *, resume=False, force=False, failpoint=None):
    return _replay(manifest, input_root, workspace, resume=resume, force=force, failpoint=failpoint)


def replay_fixture(name, workspace, *, resume=False, force=False, repin_runtime=False, failpoint=None):
    from .registry import fixture
    entry = fixture(name, repin_runtime=repin_runtime)
    return _replay(entry.lock, None, workspace, resume=resume, force=force,
                   failpoint=failpoint, fixture=entry)


def transform_bundle(caches, destination, entry, key, *, lock_fds=()):
    """Expose only the complete selected bundle; never invoke adapter publication."""
    from .registry import MAX_OUTPUT as maximum
    bundle = safe_path(destination.with_name(destination.name + '.bundle'))
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir()
    try:
        for item in entry.lock['inputs']:
            source = caches[item['path']]
            verify(source, item)
            os.link(source, bundle / item['path'])
        runner = ROOT / 'offmenu/refresh/runner.py'
        environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
        result = subprocess.run([sys.executable, '-I', '-B', str(runner), 'fixture', entry.name,
                                 str(bundle), str(destination), key, '1' if entry.repinned else '0'],
                                cwd=ROOT, env=environment, pass_fds=lock_fds,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if result.returncode:
            raise RefreshError('adapter-failed-no-output-published')
        return artifact_inventory(destination, files=entry.output_files, maximum=maximum)
    finally:
        if bundle.exists():
            shutil.rmtree(bundle)


def _replay(manifest, input_root, workspace, *, resume=False, force=False, failpoint=None, fixture=None):
    """A failpoint callback is test-only; it is never an input from manifests/CLI."""
    if resume and force:
        raise RefreshError('resume-and-force-are-exclusive')
    workspace = safe_path(workspace)
    if fixture is None:
        input_root = safe_path(input_root)
        source = safe_path(input_root / manifest['input']['path'])
        if not input_root.is_dir() or not source.is_relative_to(input_root):
            raise RefreshError('input-root-invalid')
        # Keep all source data outside the writable workspace, in both directions.
        if workspace == input_root or workspace.is_relative_to(input_root) or input_root.is_relative_to(workspace):
            raise RefreshError('input-workspace-overlap')
        inputs = [manifest['input']]
        sources = {manifest['input']['path']: source}
        source_id, release_id = SOURCE, RELEASE
        files, maximum = OUTPUT_FILES, MAX_OUTPUT
        identity_function = code_identity
        pins = public_pins(manifest)
    else:
        inputs = fixture.lock['inputs']
        sources = fixture.blobs
        source_id, release_id = fixture.source_id, fixture.lock['releaseId']
        files, maximum = fixture.output_files, MAX_OUTPUT
        identity_function = lambda: code_identity(extra_files=fixture.dependencies, packaged=True)
        pins = fixture.pins()
    if workspace == ROOT or ROOT.is_relative_to(workspace):
        raise RefreshError('workspace-must-not-contain-code')
    for item in inputs:
        verify_source(sources[item['path']], item)
    identity = identity_function()
    config_digest = sha(canonical(pins))
    key = sha(canonical({'pins': pins, 'codeFingerprint': identity['codeFingerprint']}))
    workspace.mkdir(parents=True, exist_ok=True)
    # Single writer for shared SQLite, CAS and publication, plus a named source lock.
    with writer_lock(workspace / 'workspace.lock') as workspace_lock:
        for part in ('cache/sha256', 'staging', 'releases', 'receipts', 'locks'):
            safe_path(workspace / part).mkdir(parents=True, exist_ok=True)
        with writer_lock(workspace / 'locks' / (source_id + '.lock')) as source_lock:
            if shutil.disk_usage(workspace).free < len(files) * maximum + 2 * sum(item['bytes'] for item in inputs) + 16 * 1024 * 1024:
                raise RefreshError('insufficient-staging-disk-space')
            database = safe_path(workspace / 'checkpoint.sqlite')
            db = sqlite3.connect(database)
            try:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, identity TEXT NOT NULL, pins TEXT NOT NULL, stage TEXT NOT NULL, artifacts TEXT)')
                db.commit()
                pending = db.execute("SELECT run_id, stage, artifacts FROM runs WHERE identity=? AND stage!='complete' ORDER BY rowid DESC LIMIT 1", (key,)).fetchone()
                if pending and not resume:
                    raise RefreshError('unfinished-run-requires-resume')
                if resume and not pending:
                    raise RefreshError('no-matching-run-to-resume')
                run_id = pending[0] if pending else uuid.uuid4().hex
                stage = pending[1] if pending else 'started'
                if not re.fullmatch(r'[0-9a-f]{32}', run_id) or stage not in ('started', 'cached', 'transformed', 'published'):
                    raise RefreshError('invalid-checkpoint-state')
                assets = strict_json(pending[2]) if pending and pending[2] else None
                if not pending:
                    db.execute('INSERT INTO runs VALUES (?,?,?,?,NULL)', (run_id, key, config_digest, stage))
                    db.commit()
                elif db.execute('SELECT pins FROM runs WHERE run_id=?', (run_id,)).fetchone()[0] != config_digest:
                    raise RefreshError('checkpoint-pins-mismatch')
                def checkpoint(next_stage, inventory=None):
                    nonlocal stage, assets
                    stage = next_stage
                    if inventory is not None:
                        assets = inventory
                    db.execute('UPDATE runs SET stage=?, artifacts=? WHERE run_id=?', (stage, canonical(assets).decode() if assets else None, run_id))
                    db.commit()
                    if failpoint:
                        failpoint(stage)
                caches = {}
                for item in inputs:
                    cache = safe_path(workspace / 'cache/sha256' / item['sha256'])
                    cache_input(sources[item['path']], cache, item, force=force, copy_id=run_id)
                    caches[item['path']] = cache
                # Never checkpoint a partially cached multi-file bundle.
                for item in inputs:
                    verify(caches[item['path']], item)
                final = safe_path(workspace / 'releases' / key)
                staging = safe_path(workspace / 'staging' / run_id)
                action = 'replayed'
                if final.exists() and not pending and not force:
                    previous = db.execute("SELECT artifacts FROM runs WHERE identity=? AND stage='complete' ORDER BY rowid DESC LIMIT 1", (key,)).fetchone()
                    if not previous:
                        raise RefreshError('uncheckpointed-release-requires-recovery')
                    assets = strict_json(previous[0])
                    validate_artifacts(final, assets, files=files, maximum=maximum)
                    action = 'verified-no-op'
                else:
                    if stage == 'started':
                        checkpoint('cached')
                    if stage == 'cached':
                        # A killed transform is never adopted as a valid checkpoint.
                        if staging.exists():
                            if staging.is_symlink():
                                raise RefreshError('symlink-path-rejected')
                            shutil.rmtree(staging)
                        if fixture is None:
                            assets = transform(cache, staging, manifest, lock_fds=(workspace_lock, source_lock))
                        else:
                            assets = transform_bundle(caches, staging, fixture, key,
                                                      lock_fds=(workspace_lock, source_lock))
                        if fixture is not None:
                            from .registry import validate_candidate
                            validate_candidate(staging, fixture, key)
                        for name in files:
                            with (staging / name).open('rb') as handle:
                                os.fsync(handle.fileno())
                        fsync_directory(staging)
                        checkpoint('transformed', assets)
                    if stage in ('transformed', 'published'):
                        if identity_function()['codeFingerprint'] != identity['codeFingerprint']:
                            raise RefreshError('code-changed-during-run')
                        if final.exists():
                            validate_artifacts(final, assets, files=files, maximum=maximum)
                            if staging.exists():
                                validate_artifacts(staging, assets, files=files, maximum=maximum)
                                shutil.rmtree(staging)
                            action = 'force-verified-identical' if force else 'resumed'
                        else:
                            if stage == 'published':
                                raise RefreshError('published-release-missing')
                            validate_artifacts(staging, assets, files=files, maximum=maximum)
                            if fixture is not None:
                                from .registry import validate_candidate
                                validate_candidate(staging, fixture, key)
                            os.rename(staging, final)
                            fsync_directory(final.parent)
                            if failpoint:
                                failpoint('renamed-before-checkpoint')
                        checkpoint('published', assets)
                for item in inputs:
                    verify(caches[item['path']], item)
                # Detect edits to pipeline/adapter while the subprocess was running.
                if identity_function()['codeFingerprint'] != identity['codeFingerprint']:
                    raise RefreshError('code-changed-during-run')
                if fixture is None:
                    summary = strict_json((final / 'manifest.json').read_bytes())
                    receipt = {'schemaVersion': 'offmenu-refresh-receipt/1', 'runId': run_id,
                               'sourceId': SOURCE, 'releaseId': RELEASE, 'scope': manifest['scope'],
                               'status': 'complete', 'action': action, 'identity': key,
                               'configFingerprint': config_digest, **identity,
                               'input': manifest['input'] | {'path': None},
                               'artifacts': assets, 'counts': summary['counts'],
                               'cachePolicy': {'minimumReuseDays': 30, 'mode': 'offline-pinned-replay', 'mtimeUsedForFreshness': False},
                               'network': {'acquisition': 'not-implemented', 'adapterGuard': 'python-audit-deny', 'externalPublication': False},
                               'countryCoverage': {'universeCount': 249, 'observedCountryCodes': [], 'status': 'not-assessed', 'complete': False}}
                    del receipt['input']['path']
                else:
                    from .registry import validate_candidate
                    summary, content_digest = validate_candidate(final, fixture, key)
                    receipt = {'schemaVersion': 'offmenu-refresh-receipt/2', 'runId': run_id,
                               'sourceId': source_id, 'releaseId': release_id, 'scope': manifest['scope'],
                               'status': 'complete', 'action': action, 'identity': key,
                               'configFingerprint': config_digest, **identity,
                               'inputBundleSha256': fixture.bundle_key(),
                               'inputs': inputs, 'artifacts': assets, 'counts': summary['counts'],
                               'canonicalContentSha256': content_digest,
                               'acceptance': 'not-performed', 'publicExport': 'not-enabled',
                               'runtimeRepinned': fixture.repinned,
                               'completedAt': datetime.now(timezone.utc).isoformat(),
                               'cachePolicy': {'minimumReuseDays': 30, 'mode': 'offline-pinned-replay',
                                               'mtimeUsedForFreshness': False,
                                               'acquisitionEvidenceInBuildKey': False},
                               'network': {'acquisition': 'not-implemented', 'adapterGuard': 'python-audit-deny',
                                           'osNetworkConfinementVerified': False, 'externalPublication': False},
                               'countryCoverage': {'universeCount': 249, 'observedCountryCodes': ['NO'],
                                                   'status': 'not-assessed', 'complete': False}}
                atomic_json(workspace / 'receipts' / (run_id + '.json'), receipt)
                checkpoint('complete', assets)
                return receipt
            except BaseException as error:
                # Only fixed identities and validated hashes cross into failure receipts.
                error.refresh_context = {'sourceId': source_id, 'releaseId': release_id,
                                         'configFingerprint': config_digest, **identity}
                if fixture is None:
                    error.refresh_context['input'] = {k: manifest['input'][k] for k in ('bytes', 'sha256')}
                else:
                    error.refresh_context['inputBundleSha256'] = fixture.bundle_key()
                if 'run_id' in locals():
                    error.refresh_context['runId'] = run_id
                raise
            finally:
                db.close()
