"""Strict sanitized-receipt Git branch, independent of the code checkout.

Only validated receipts enter its trees. Uses a private temporary Git index;
never changes the user's index, worktree, HEAD, code branch or existing commits.
No force/reset/stash/rebase/merge. Divergent receipt histories remain preserved.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import tempfile

BRANCH = 'integration/ingest-receipts-20261022'
LOCAL_REF = 'refs/heads/' + BRANCH
MAX_RECEIPTS = 8192
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_TREE_BYTES = 256 * 1024 * 1024
OID = re.compile(r'[0-9a-f]{40,64}\Z')


class ReceiptBranchPublisher:
    def __init__(self, runner, *, validate, relpath, canonical, fail, validate_supplement, supplement_relpath):
        self.runner, self.validate, self.relpath = runner, validate, relpath
        self.canonical, self.fail = canonical, fail
        self.validate_supplement, self.supplement_relpath = validate_supplement, supplement_relpath
        self.initialized = False
        self.validated = set()
        self.tree_sizes = {}

    def _oid(self, *args):
        code, raw = self.runner.git(*args, check=False)
        value = raw.decode('ascii').strip()
        return value if code == 0 and OID.fullmatch(value) else None

    def _validate_tree(self, commit):
        if commit in self.validated:
            return
        history = self.runner.textgit('rev-list', '--max-count=' + str(MAX_RECEIPTS + 1), commit).splitlines()
        if len(history) > MAX_RECEIPTS:
            raise self.fail('receipt_branch_history_limit_preserved')
        for revision in history:
            if len(self.runner.textgit('rev-list', '--parents', '-n', '1', revision).split()) > 2:
                raise self.fail('receipt_branch_merge_history_refused')
            if self.runner.textgit('show', '-s', '--format=%B', revision) != 'Return sanitized retained ingest checkpoint [skip ci]':
                raise self.fail('receipt_branch_nonreceipt_history_preserved')
            changes = self.runner.git('diff-tree', '--root', '--no-commit-id', '--name-status', '-r', '-z', revision)[1].split(b'\0')
            changes = [x for x in changes if x]
            if not changes or len(changes) % 2 or any(x != b'A' for x in changes[::2]):
                raise self.fail('receipt_branch_nonadditive_history_preserved')
        entries = self.runner.git('ls-tree', '-r', '-z', commit)[1].split(b'\0')
        entries = [entry for entry in entries if entry]
        if len(entries) > MAX_RECEIPTS:
            raise self.fail('receipt_branch_count_limit_preserved')
        total = 0
        references, supplements = {}, {}
        for entry in entries:
            try:
                metadata, path = entry.split(b'\t', 1)
                mode, kind, oid = metadata.decode('ascii').split()
                path = path.decode('utf-8')
            except (ValueError, UnicodeError):
                raise self.fail('receipt_branch_tree_refused_preserved') from None
            if mode != '100644' or kind != 'blob':
                raise self.fail('receipt_branch_tree_refused_preserved')
            size = int(self.runner.textgit('cat-file', '-s', oid))
            total += size
            if size > MAX_RECEIPT_BYTES or total > MAX_TREE_BYTES:
                raise self.fail('receipt_branch_size_limit_preserved')
            raw = self.runner.git('cat-file', 'blob', oid)[1]
            import json
            try:
                value = json.loads(raw)
                if value.get('schema') == 'offmenu-ingest-supplement/1':
                    value = self.validate_supplement(value)
                    import hashlib
                    ref = {'schema': 'offmenu-ingest-evidence-ref/1', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                    if self.supplement_relpath(ref) != path:
                        raise ValueError('invalid_supplement_path')
                    supplements[path] = ref
                else:
                    value = self.validate(value)
                    if self.relpath(value) != path:
                        raise ValueError('invalid_receipt_path')
                    reference = value['ingest'].get('evidence_ref')
                    if reference:
                        references[self.supplement_relpath(reference)] = reference
                if self.canonical(value) != raw:
                    raise ValueError('noncanonical')
            except Exception:
                raise self.fail('receipt_branch_unsanitized_tree_preserved') from None
        if references != supplements:
            raise self.fail('receipt_branch_supplement_missing_or_unbound_preserved')
        self.validated.add(commit)
        self.tree_sizes[commit] = total

    def initialize(self):
        if self.initialized:
            return
        self.runner.check_remote()
        if ('branch ' + LOCAL_REF) in self.runner.textgit('worktree', 'list', '--porcelain').splitlines():
            raise self.fail('receipt_branch_checked_out_elsewhere_preserved')
        remote_raw = self.runner.textgit('ls-remote', '--heads', 'origin', LOCAL_REF)
        remote = None
        if remote_raw:
            lines = remote_raw.splitlines()
            if len(lines) != 1 or lines[0].split()[1:] != [LOCAL_REF]:
                raise self.fail('receipt_branch_remote_ref_refused')
            remote = lines[0].split()[0]
            if not OID.fullmatch(remote):
                raise self.fail('receipt_branch_remote_ref_refused')
            self.runner.git('fetch', '--no-tags', '--no-recurse-submodules', 'origin', LOCAL_REF)
            fetched = self._oid('rev-parse', 'FETCH_HEAD')
            if fetched != remote:
                raise self.fail('receipt_branch_remote_changed_retry_preserved')
            self._validate_tree(remote)
        local = self._oid('rev-parse', '--verify', LOCAL_REF)
        if local:
            self._validate_tree(local)
        if remote and local and remote != local:
            if self.runner.git('merge-base', '--is-ancestor', remote, local, check=False)[0] == 0:
                pass  # Preserve and publish the existing local receipt commits.
            elif self.runner.git('merge-base', '--is-ancestor', local, remote, check=False)[0] == 0:
                self.runner.git('update-ref', LOCAL_REF, remote, local)
            else:
                raise self.fail('receipt_branch_diverged_local_commits_and_spool_preserved')
        elif remote and not local:
            self.runner.git('update-ref', LOCAL_REF, remote, '0' * len(remote))
        self.initialized = True

    def recover_supplement(self, reference):
        """Recover missing local evidence only from an already validated commit."""
        self.initialize()
        parent = self._oid('rev-parse', '--verify', LOCAL_REF)
        relative = self.supplement_relpath(reference)
        if not parent or self.runner.git('cat-file', '-e', parent + ':' + relative, check=False)[0]:
            raise self.fail('required_supplement_missing_spool_preserved')
        raw = self.runner.git('show', parent + ':' + relative)[1]
        import hashlib, json
        value = self.validate_supplement(json.loads(raw))
        if self.canonical(value) != raw or len(raw) != reference['bytes'] or hashlib.sha256(raw).hexdigest() != reference['sha256']:
            raise self.fail('required_supplement_changed_spool_preserved')
        return value

    def publish(self, value, supplement=None):
        self.validate(value)
        relative = self.relpath(value)
        raw = self.canonical(value)
        if len(raw) > MAX_RECEIPT_BYTES:
            raise self.fail('receipt_branch_receipt_size_limit_preserved')
        additions = {relative: raw}
        reference = value['ingest'].get('evidence_ref')
        if reference:
            import hashlib
            if supplement is None:
                raise self.fail('required_supplement_missing_spool_preserved')
            extra = self.canonical(self.validate_supplement(supplement))
            if hashlib.sha256(extra).hexdigest() != reference['sha256'] or len(extra) != reference['bytes']:
                raise self.fail('required_supplement_changed_spool_preserved')
            additions[self.supplement_relpath(reference)] = extra
        elif supplement is not None:
            raise self.fail('unbound_supplement_refused')
        self.initialize()
        parent = self._oid('rev-parse', '--verify', LOCAL_REF)
        missing = {}
        for path, content in additions.items():
            exists = self.runner.git('cat-file', '-e', parent + ':' + path, check=False)[0] == 0 if parent else False
            if exists:
                previous = self.runner.git('show', parent + ':' + path)[1]
                if previous != content:
                    if path != relative:
                        raise self.fail('receipt_branch_existing_supplement_changed_preserved')
                    # Preserve canonical timestamp of a prior identical-progress receipt.
                    import json
                    old = self.validate(json.loads(previous))
                    if self.relpath(old) != relative or self.canonical(old) != previous or old['ingest'] != value['ingest']:
                        raise self.fail('receipt_branch_existing_receipt_invalid_preserved')
            else:
                missing[path] = content
        if missing:
            total = self.tree_sizes.get(parent, 0) + sum(len(content) for content in missing.values())
            if total > MAX_TREE_BYTES:
                raise self.fail('receipt_branch_size_limit_preserved')
            state = self.runner.state
            state.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='receipt-index-', dir=state)
            os.close(fd)
            os.unlink(temporary)
            try:
                options = {'env_overrides': {'GIT_INDEX_FILE': temporary}}
                self.runner.git('read-tree', parent if parent else '--empty', **options)
                for path, content in missing.items():
                    blob = self.runner.git('hash-object', '-w', '--stdin', input_data=content)[1].decode('ascii').strip()
                    self.runner.git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + path, **options)
                tree = self.runner.git('write-tree', **options)[1].decode('ascii').strip()
                # A single tree/commit binds the receipt and its readable evidence.
                if len([x for x in self.runner.git('ls-tree','-r','-z',tree)[1].split(b'\0') if x]) > MAX_RECEIPTS:
                    raise self.fail('receipt_branch_count_limit_preserved')
                command = ['commit-tree', tree]
                if parent:
                    command += ['-p', parent]
                command += ['-m', 'Return sanitized retained ingest checkpoint [skip ci]']
                commit = self.runner.git(*command)[1].decode('ascii').strip()
                if not OID.fullmatch(commit):
                    raise self.fail('receipt_branch_commit_identity_invalid')
                self.runner.git('update-ref', LOCAL_REF, commit, parent or '0' * len(commit))
                self.validated.add(commit)
                self.tree_sizes[commit] = total
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
                if os.path.exists(temporary + '.lock'):
                    os.unlink(temporary + '.lock')
        self.runner.git('push', 'origin', LOCAL_REF + ':' + LOCAL_REF)
