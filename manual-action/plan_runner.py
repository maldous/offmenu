#!/usr/bin/env python3
"""Finite, supplier-only checkout/pull/check/return loop; standard library only.

No shell from plans, inventory, imports, archive execution or source upload.
Git output and private supplier details are never echoed or persisted.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile

BRANCH = 'integration/manual-actions-20261022'
REMOTE_URLS = {'git@github.com:maldous/offmenu.git', 'https://github.com/maldous/offmenu.git',
               'ssh://git@github.com/maldous/offmenu.git'}
RETURN_DIR = 'manual-action/returns/run'
RECEIPT_SCHEMA = 'offmenu-run-receipt/1'
COMMIT_MESSAGE = 'Return sanitized supplier check [skip ci]'
HEX = re.compile(r'[0-9a-f]{64}\Z')
RECEIPT_NAME = re.compile(r'[0-9a-f]{64}-(?:completed|blocked-[0-9a-f]{16})\.json\Z')
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z')
REASONS = frozenset('missing unreadable refused_or_unreadable sha256_prefix_mismatch '
    'compressed_archive_limit compressed_archive_changed_or_limit archive_changed '
    'expanded_archive_limit archive_member_limit unsafe_member_name unsafe_member_path '
    'secret_looking_member_path dataset_looking_member_path duplicate_member_path '
    'unsafe_member_type member_size_limit unsupported_archive_metadata member_length_mismatch '
    'non_source_member_extension non_utf8_member binary_or_secret_looking_content '
    'json_not_named_as_source_metadata invalid_source_metadata_json json_rows_refused '
    'trailing_archive_payload empty_source_archive symlink_path_refused not_regular_file '
    'wall_time_limit inspection_error OSError EOFError ReadError CompressionError '
    'HeaderError ExtractError ValueError error BadGzipFile PermissionError '
    'FileNotFoundError'.split())


class Stop(Exception):
    pass


def announce(message):
    print(message, flush=True)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise Stop('invalid_sanitized_schema')


def safe_path(path):
    path = Path(os.path.abspath(path))
    for node in (path, *path.parents):
        try:
            if stat.S_ISLNK(node.lstat().st_mode):
                raise Stop('symlink_path_refused')
        except FileNotFoundError:
            pass
    return path


def read_json(path):
    path = safe_path(path)
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise Stop('json_size_limit')
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        raise Stop('invalid_json') from None


def validate_plan(plan):
    exact_keys(plan, {'schema', 'max_parallel', 'jobs'})
    if plan['schema'] != 'offmenu-run-plan/1' or type(plan['max_parallel']) is not int or plan['max_parallel'] != 1:
        raise Stop('unsupported_plan')
    # Deliberately one reviewed read-only job, not an arbitrary workflow engine.
    if not isinstance(plan['jobs'], list) or len(plan['jobs']) != 1:
        raise Stop('unsupported_jobs')
    job = plan['jobs'][0]
    exact_keys(job, {'id', 'version', 'operation', 'depends_on'})
    if (job['id'] != 'supplier-source-inspection' or job['operation'] != 'supplier_inspect'
            or type(job['version']) is not int or not 1 <= job['version'] <= 1000000
            or job['depends_on'] != []):
        raise Stop('unsupported_job')
    return job


def validate_receipt(value):
    exact_keys(value, {'schema', 'job_id', 'job_version', 'operation', 'job_key',
        'implementation_sha256', 'input_sha256', 'observed_at', 'outcome', 'supplier',
        'data_loads', 'source_review', 'source_upload'})
    if (value['schema'] != RECEIPT_SCHEMA or value['job_id'] != 'supplier-source-inspection'
            or value['operation'] != 'supplier_inspect' or type(value['job_version']) is not int
            or not 1 <= value['job_version'] <= 1000000 or value['data_loads'] != 'not_implemented'
            or value['source_review'] != 'manual_review_required' or value['source_upload'] != 'NOT_UPLOADED'
            or not isinstance(value['observed_at'], str) or not STAMP.fullmatch(value['observed_at'])):
        raise Stop('invalid_sanitized_schema')
    for key in ('job_key', 'implementation_sha256'):
        if not isinstance(value[key], str) or not HEX.fullmatch(value[key]):
            raise Stop('invalid_sanitized_digest')
    if value['input_sha256'] is not None and (not isinstance(value['input_sha256'], str) or not HEX.fullmatch(value['input_sha256'])):
        raise Stop('invalid_sanitized_digest')
    sup = value['supplier']
    exact_keys(sup, {'status', 'member_count', 'transfer'}, {'reason', 'expected_sha256_prefix', 'observed_sha256', 'compressed_bytes', 'source_bytes'})
    if sup['transfer'] != 'NOT_UPLOADED' or type(sup['member_count']) is not int or not 0 <= sup['member_count'] <= 256:
        raise Stop('invalid_sanitized_schema')
    if 'reason' in sup and sup['reason'] not in REASONS:
        raise Stop('invalid_sanitized_reason')
    if 'expected_sha256_prefix' in sup and sup['expected_sha256_prefix'] != 'e2508555':
        raise Stop('invalid_sanitized_digest')
    if 'observed_sha256' in sup and (not isinstance(sup['observed_sha256'], str) or not HEX.fullmatch(sup['observed_sha256'])):
        raise Stop('invalid_sanitized_digest')
    for key, maximum in (('compressed_bytes', 16 * 1024 * 1024), ('source_bytes', 32 * 1024 * 1024)):
        if key in sup and (type(sup[key]) is not int or not 0 <= sup[key] <= maximum):
            raise Stop('invalid_sanitized_count')
    if value['outcome'] == 'completed':
        if (sup['status'] != 'inspection_pass_manual_review_required' or 'reason' in sup
                or not {'observed_sha256', 'expected_sha256_prefix', 'compressed_bytes', 'source_bytes'} <= set(sup)
                or sup['observed_sha256'] != value['input_sha256']):
            raise Stop('invalid_completion')
    elif value['outcome'] != 'blocked' or sup['status'] != 'blocked' or 'reason' not in sup:
        raise Stop('invalid_outcome')
    return value


def receipt_relpath(value):
    validate_receipt(value)
    suffix = 'completed' if value['outcome'] == 'completed' else 'blocked-' + digest(canonical(value['supplier']))[:16]
    return f"{RETURN_DIR}/{value['job_key']}-{suffix}.json"


def validate_return_path(path):
    if not isinstance(path, str) or str(Path(path).parent) != RETURN_DIR or not RECEIPT_NAME.fullmatch(Path(path).name):
        raise Stop('non_receipt_path_refused')


class Runner:
    def __init__(self, root):
        self.root = safe_path(root)
        self.gitdir = safe_path(self.root / '.git')
        self.state = self.gitdir / 'offmenu-runner'
        self.lock = None
        self.remote_head = None

    def git(self, *args, check=True):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
        command = ['git', '-C', str(self.root), '-c', 'core.hooksPath=/dev/null',
            '-c', 'core.fsmonitor=false', '-c', 'submodule.recurse=false',
            '-c', 'commit.gpgsign=false', '-c', 'push.followTags=false',
            '-c', 'push.recurseSubmodules=no', '-c', 'remote.origin.mirror=false', *args]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=120)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise Stop('git_timeout_local_work_preserved') from None
        if check and proc.returncode:
            raise Stop('git_' + args[0].replace('-', '_') + '_failed_local_work_preserved')
        return proc.returncode, out

    def textgit(self, *args):
        return self.git(*args)[1].decode('utf-8').strip()

    def check_remote(self):
        # Test harness subclasses this method for generated local bare remotes only.
        urls = self.textgit('remote', 'get-url', '--all', 'origin').splitlines()
        pushes = self.textgit('remote', 'get-url', '--push', '--all', 'origin').splitlines()
        if len(urls) != 1 or len(pushes) != 1 or urls[0] not in REMOTE_URLS or pushes[0] not in REMOTE_URLS:
            raise Stop('expected_private_offmenu_remote_required')

    def preconditions(self):
        if any(key in os.environ for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES')):
            raise Stop('git_environment_override_refused')
        if not self.gitdir.is_dir() or self.textgit('rev-parse', '--show-toplevel') != str(self.root):
            raise Stop('isolated_repository_root_required')
        if self.textgit('symbolic-ref', '--short', 'HEAD') != BRANCH:
            raise Stop('expected_manual_action_branch_required')
        self.check_remote()
        if self.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--quiet', check=False)[0] != 0:
            raise Stop('preexisting_staged_changes_preserved_unstage_manually')
        if any((self.gitdir / name).exists() for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'BISECT_LOG')):
            raise Stop('git_operation_in_progress')
        if self.git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', 'run', 'manual-action', '.github/workflows/manual-action-fixtures.yml')[1]:
            raise Stop('runner_or_plan_paths_dirty_preserved')
        for relative in ('run', 'manual-action', 'manual-action/plan_runner.py', 'manual-action/foo_manual.py', 'manual-action/plan.json', RETURN_DIR):
            safe_path(self.root / relative)

    def acquire(self, inherited=None):
        self.preconditions()
        path = self.gitdir / 'offmenu-run.lock'
        if inherited is None:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        else:
            fd = int(inherited)
            existing = os.stat(path, follow_symlinks=False)
            actual = os.fstat(fd)
            if (existing.st_dev, existing.st_ino) != (actual.st_dev, actual.st_ino) or not stat.S_ISREG(actual.st_mode):
                raise Stop('invalid_inherited_lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise Stop('another_run_is_active') from None
        self.lock = fd
        self.preconditions()

    def pull(self):
        announce('[1/4] Pulling the reviewed manual-action branch (fast-forward only).')
        self.git('pull', '--ff-only', '--no-rebase', '--no-autostash', '--no-recurse-submodules', 'origin', BRANCH)
        self.remote_head = self.textgit('rev-parse', 'FETCH_HEAD')
        self.preconditions()
        self.check_outgoing()

    def reexec(self):
        os.set_inheritable(self.lock, True)
        env = dict(os.environ, OFFMENU_RUN_FD=str(self.lock), OFFMENU_RUN_HEAD=self.textgit('rev-parse', 'HEAD'), OFFMENU_RUN_REMOTE=self.remote_head)
        os.execve(sys.executable, [sys.executable, '-B', str(self.root / 'manual-action/plan_runner.py')], env)

    def check_outgoing(self):
        if not self.remote_head or not re.fullmatch(r'[0-9a-f]{40,64}', self.remote_head):
            raise Stop('missing_pulled_revision')
        if self.git('merge-base', '--is-ancestor', self.remote_head, 'HEAD', check=False)[0]:
            raise Stop('remote_diverged_local_work_preserved_no_force')
        commits = self.textgit('rev-list', self.remote_head + '..HEAD').splitlines()
        for commit in commits:
            if self.textgit('show', '-s', '--format=%B', commit) != COMMIT_MESSAGE:
                raise Stop('non_runner_commit_message_preserved')
            if len(self.textgit('rev-list', '--parents', '-n', '1', commit).split()) != 2:
                raise Stop('non_runner_commit_pending_preserved')
            changes = self.git('diff-tree', '--no-commit-id', '--name-status', '-r', '-z', commit)[1].decode().split('\0')
            changes = changes[:-1] if changes and changes[-1] == '' else changes
            if not changes or len(changes) % 2:
                raise Stop('non_runner_commit_pending_preserved')
            for status_code, path in zip(changes[::2], changes[1::2]):
                if status_code != 'A':
                    raise Stop('non_runner_commit_pending_preserved')
                validate_return_path(path)
                raw = self.git('show', commit + ':' + path)[1]
                value = validate_receipt(json.loads(raw))
                if receipt_relpath(value) != path or canonical(value) != raw:
                    raise Stop('non_sanitized_commit_pending_preserved')
        return bool(commits)

    def checkpoint(self, phase, job_key=None, relative=None, sha256=None):
        # A small local crash-recovery record; never staged or pushed.
        self.state = safe_path(self.state)
        self.state.mkdir(mode=0o700, exist_ok=True)
        value = {'schema': 'offmenu-run-checkpoint/1', 'phase': phase, 'job_key': job_key, 'receipt': relative, 'sha256': sha256}
        if phase not in {'checking', 'receipt_ready', 'committed', 'published', 'blocked'}:
            raise Stop('invalid_checkpoint')
        if job_key is not None and not HEX.fullmatch(job_key):
            raise Stop('invalid_checkpoint')
        if relative is not None:
            validate_return_path(relative)
        if sha256 is not None and not HEX.fullmatch(sha256):
            raise Stop('invalid_checkpoint')
        fd, temp = tempfile.mkstemp(prefix='.checkpoint-', dir=self.state)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, self.state / 'checkpoint.json')
            directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def owned_receipt(self, relative, raw):
        path = self.state / 'checkpoint.json'
        if not path.exists():
            return False
        value = read_json(path)
        return (isinstance(value, dict) and value.get('schema') == 'offmenu-run-checkpoint/1'
                and value.get('receipt') == relative and value.get('sha256') == digest(raw)
                and value.get('phase') in {'receipt_ready', 'committed', 'published', 'blocked'})

    def tracked(self, relative):
        return self.git('ls-files', '--error-unmatch', '--', relative, check=False)[0] == 0

    def publish(self, relative=None, raw=None):
        self.preconditions()
        value = validate_receipt(json.loads(raw)) if relative is not None else None
        if relative is not None and not self.tracked(relative):
            validate_return_path(relative)
            if not self.owned_receipt(relative, raw) or (safe_path(self.root / relative)).read_bytes() != raw:
                raise Stop('receipt_ownership_or_digest_mismatch_preserved')
            value = validate_receipt(json.loads(raw))
            if receipt_relpath(value) != relative or canonical(value) != raw:
                raise Stop('invalid_receipt_preserved')
            attributes = self.git('check-attr', '-z', 'filter', '--', relative)[1].split(b'\0')
            if attributes != [relative.encode(), b'filter', b'unspecified', b''] and attributes != [relative.encode(), b'filter', b'unset', b'']:
                raise Stop('receipt_clean_filter_refused_preserved')
            self.git('add', '-f', '--', relative)
            staged = self.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z')[1]
            if staged != relative.encode() + b'\0' or self.git('show', ':' + relative)[1] != raw:
                raise Stop('staged_content_changed_preserved_review_index')
            self.git('commit', '-m', COMMIT_MESSAGE)
            self.checkpoint('committed', value['job_key'], relative, digest(raw))
        if self.check_outgoing():
            announce('[4/4] Pushing sanitized receipts (no force).')
            self.git('push', 'origin', 'HEAD:refs/heads/' + BRANCH)
            if relative is not None:
                self.checkpoint('published', value['job_key'], relative, digest(raw))
        else:
            announce('[4/4] No unpublished receipt commits.')

    def inspector(self):
        spec = importlib.util.spec_from_file_location('offmenu_reviewed_foo_manual', self.root / 'manual-action/foo_manual.py')
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return foo

    def run_plan(self):
        self.preconditions()
        job = validate_plan(read_json(self.root / 'manual-action/plan.json'))
        foo = self.inspector()
        implementation = digest(b''.join((self.root / path).read_bytes() for path in ('run', 'manual-action/plan_runner.py', 'manual-action/foo_manual.py')))
        input_sha = None
        try:
            with foo.open_regular(foo.SUPPLIER_ARCHIVE)[0] as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read(foo.MAX_COMPRESSED + 1)
                if len(raw) <= foo.MAX_COMPRESSED and len(raw) == before.st_size and foo.fingerprint(before) == foo.fingerprint(os.fstat(stream.fileno())):
                    input_sha = digest(raw)
        except (OSError, foo.Refusal):
            pass
        job_key = digest(canonical({'job': job, 'implementation': implementation, 'input': input_sha}))
        completed = f'{RETURN_DIR}/{job_key}-completed.json'
        if (self.root / completed).exists():
            existing = validate_receipt(read_json(self.root / completed))
            if existing['job_key'] != job_key or existing['outcome'] != 'completed':
                raise Stop('existing_receipt_identity_mismatch')
            raw = canonical(existing)
            if not self.tracked(completed) and not self.owned_receipt(completed, raw):
                raise Stop('unowned_existing_receipt_preserved')
            announce('[2/4] This supplier check is already complete; no inspection repeated.')
            announce('[3/4] Existing sanitized receipt retained; source review remains required.')
            self.publish(completed, raw)
            return 0
        announce('[2/4] Inspecting only the fixed supplier source capsule (30-second bound).')
        # Keep a recoverable receipt_ready record until a new receipt is durable.
        if not (self.state / 'checkpoint.json').exists():
            self.checkpoint('checking', job_key)
        old_handler = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(foo.Deadline('wall_time_limit')))
        signal.alarm(foo.MAX_SECONDS)
        try:
            result = foo.inspect_supplier()
        except foo.Deadline:
            result = {'status': 'blocked', 'reason': 'wall_time_limit'}
        except (OSError, foo.Refusal, ValueError):
            result = {'status': 'blocked', 'reason': 'inspection_error'}
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        supplier = {key: result[key] for key in ('status', 'expected_sha256_prefix', 'observed_sha256', 'compressed_bytes', 'source_bytes') if key in result}
        supplier.update(member_count=len(result.get('manifest', [])), transfer='NOT_UPLOADED')
        if result.get('status') == 'blocked':
            supplier['reason'] = result.get('reason') if result.get('reason') in REASONS else 'inspection_error'
        if result.get('status') != 'blocked' and result.get('observed_sha256') != input_sha:
            supplier = {'status': 'blocked', 'reason': 'archive_changed', 'member_count': 0, 'transfer': 'NOT_UPLOADED'}
        outcome = 'completed' if supplier['status'] == 'inspection_pass_manual_review_required' else 'blocked'
        receipt = {'schema': RECEIPT_SCHEMA, 'job_id': job['id'], 'job_version': job['version'],
            'operation': job['operation'], 'job_key': job_key, 'implementation_sha256': implementation,
            'input_sha256': input_sha, 'observed_at': foo.stamp(), 'outcome': outcome,
            'supplier': supplier, 'data_loads': 'not_implemented', 'source_review': 'manual_review_required', 'source_upload': 'NOT_UPLOADED'}
        relative = receipt_relpath(receipt)
        raw = canonical(receipt)
        destination = safe_path(self.root / relative)
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if destination.exists():
            prior = validate_receipt(read_json(destination))
            if receipt_relpath(prior) != relative:
                raise Stop('existing_receipt_identity_mismatch')
            raw = canonical(prior)
            if not self.tracked(relative) and not self.owned_receipt(relative, raw):
                raise Stop('unowned_existing_receipt_preserved')
        else:
            foo.write_result(destination, receipt)
            self.checkpoint('receipt_ready', job_key, relative, digest(raw))
        announce('[3/4] Sanitized supplier receipt: ' + outcome + '. No inventory, source upload or data load.')
        self.publish(relative, raw)
        return 0 if outcome == 'completed' else 2


def main():
    runner = Runner(Path(__file__).resolve().parents[1])
    try:
        if len(sys.argv) != 1:
            raise Stop('no_arguments_supported_edit_reviewed_plan_for_reruns')
        inherited = os.environ.pop('OFFMENU_RUN_FD', None)
        inherited_head = os.environ.pop('OFFMENU_RUN_HEAD', None)
        inherited_remote = os.environ.pop('OFFMENU_RUN_REMOTE', None)
        runner.acquire(inherited)
        if inherited is None:
            runner.pull()
            runner.reexec()  # Updated implementation, same exclusive lock; exactly one pull.
        if not inherited_head or runner.textgit('rev-parse', 'HEAD') != inherited_head:
            raise Stop('checkout_changed_during_reexec')
        runner.remote_head = inherited_remote
        runner.check_outgoing()
        code = runner.run_plan()
        announce('Done. Inspection is not source-review acceptance or import readiness.' if code == 0 else 'Blocked result returned; job remains pending. Existing data/jobs unchanged.')
        return code
    except KeyboardInterrupt:
        announce('STOP: interrupted; local work preserved.')
        return 130
    except Exception as error:
        reason = str(error) if isinstance(error, Stop) else 'local_runner_error'
        announce('STOP: ' + reason + '. No reset, stash, clean or force-push was performed.')
        return 2
    finally:
        if runner.lock is not None:
            os.close(runner.lock)


if __name__ == '__main__':
    raise SystemExit(main())
