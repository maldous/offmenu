#!/usr/bin/env python3
"""One approved named-user read handoff; default is read-only planning.

Fixed source-cache scope only. No fetching, copies of source bytes, ingestion,
code execution, chmod, sudo, service/mount changes, package installs or network.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import time
import uuid

SCHEMA = 'offmenu-source-access-handoff/1'
SNAPSHOT_SCHEMA = 'offmenu-source-access-acl-snapshot/1'
CACHE = Path('/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache')
STATE = CACHE.parent / 'access-handoff'
REPORT = CACHE.parent / 'receipts' / 'access-handoff-summary.json'
MANIFEST = Path(__file__).with_name('fetch-sources.json')
MANIFEST_SHA = '637bfeba82177e44a87080ca6be217c475cc02917848730762d9f1949e69ebec'
SCOPE_PLAN = Path(__file__).with_name('source-access-handoff-plan.json')
SCOPE_PLAN_SHA = 'c9b2a39a54b5131b207c224fbfdea5803f6f08154688925f541ebc12947411e9'
EXPECTED_BYTES = 108318002
ACTOR = 'offmenu-runner'
TARGET = 'user'
FAMILY_COUNTS = {'foodista_common_pile': 5, 'forkrecipe': 1,
    'medlineplus_healthy_recipes': 12, 'fr_cnous_menus': 26,
    'fr_begles_menus': 2, 'fr_toulouse_menus': 4}
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
CODES = frozenset(('none', 'account_missing', 'wrong_actor', 'invalid_target',
    'libacl_unavailable', 'acl_operation_failed', 'invalid_acl', 'manifest_identity_mismatch',
    'scope_mismatch', 'unsafe_path', 'ownership_mismatch', 'source_not_regular',
    'source_executable', 'unexpected_hardlink', 'receipt_mismatch', 'receipt_schema_unreviewed',
    'checksum_mismatch', 'size_mismatch', 'source_changed', 'time_budget',
    'target_existing_permissions_exceed_scope', 'acl_mask_expansion_would_broaden_others',
    'outside_ancestor_not_traversable', 'concurrent_acl_change', 'readback_mismatch',
    'default_acl_changed', 'snapshot_write_failed', 'rollback_incomplete',
    'access_denied', 'source_missing', 'lock_busy', 'unlisted_sibling_exposure', 'sibling_metadata_budget', 'unexpected_error'))
# Linux libacl tags; numeric qualifiers avoid resolving arbitrary source names.
USER_OBJ, USER, GROUP_OBJ, GROUP, MASK, OTHER = 1, 2, 4, 8, 16, 32
BASE = ((USER_OBJ, None), (GROUP_OBJ, None), (OTHER, None))
GROUP_CLASS = (USER, GROUP_OBJ, GROUP)
ALLOWED_RECEIPT_KEYS = frozenset(('schema', 'source_id', 'artifact', 'artifact_key',
    'source_revision', 'origin_url', 'license', 'license_evidence', 'attribution',
    'license_scope_note', 'artifact_metadata_evidence', 'catalog_resource_id',
    'artifact_license_evidence', 'transport_integrity', 'acquisition_only',
    'ingested', 'raw_data_uploaded', 'etag', 'last_modified', 'final_url', 'redirects',
    'content_type', 'response_observed_at', 'status', 'bytes', 'sha256', 'completed_at',
    'expected_sha256', 'expected_bytes', 'checksum_basis'))


class Refusal(RuntimeError):
    def __init__(self, code):
        self.code = code if code in CODES else 'unexpected_error'
        super().__init__(self.code)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def signature(st):
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def data_identity(st):
    # ACL changes legitimately update ctime, not file data size/mtime or inode.
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]


def open_directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('unsafe_path')
    flags = getattr(os, 'O_PATH', os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def hold_path(path, directory=False):
    path = Path(path)
    if path == Path('/') and directory:
        return os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parent = open_directory(path.parent)
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        fd = os.open(path.name, flags, dir_fd=parent)
    finally:
        os.close(parent)
    st = os.fstat(fd)
    if not (stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)):
        os.close(fd)
        raise Refusal('source_not_regular')
    return fd


def path_stat(path):
    parent = open_directory(Path(path).parent)
    try:
        return os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
    finally:
        os.close(parent)


def read_fd_json(fd, maximum=4 * 1024**2):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks, length = [], 0
    while length <= maximum:
        block = os.read(fd, min(65536, maximum + 1 - length))
        if not block:
            break
        chunks.append(block)
        length += len(block)
    if length > maximum:
        raise Refusal('receipt_mismatch')
    value = json.loads(b''.join(chunks))
    if not isinstance(value, dict):
        raise Refusal('receipt_mismatch')
    return value


def validate_acl(acl):
    if any(key not in acl for key in BASE) or len(acl) > 1024:
        raise Refusal('invalid_acl')
    for (tag, qualifier), perms in acl.items():
        if tag not in (USER_OBJ, USER, GROUP_OBJ, GROUP, MASK, OTHER) or type(perms) is not int or not 0 <= perms <= 7:
            raise Refusal('invalid_acl')
        if (tag in (USER, GROUP)) != (type(qualifier) is int and qualifier >= 0):
            if not (tag not in (USER, GROUP) and qualifier is None):
                raise Refusal('invalid_acl')
    if any(tag in (USER, GROUP) for tag, _ in acl) and (MASK, None) not in acl:
        raise Refusal('invalid_acl')
    return acl


def acl_text(acl):
    validate_acl(acl)
    tags = {USER_OBJ: 'user', USER: 'user', GROUP_OBJ: 'group', GROUP: 'group', MASK: 'mask', OTHER: 'other'}
    def perms(bits):
        return ''.join(letter if bits & bit else '-' for bit, letter in ((4, 'r'), (2, 'w'), (1, 'x')))
    return ''.join(f'{tags[tag]}:{"" if qualifier is None else qualifier}:{perms(bits)}\n'
        for (tag, qualifier), bits in sorted(acl.items(), key=lambda item: (item[0][0], -1 if item[0][1] is None else item[0][1])))


def effective_acl_entries(acl):
    mask = acl.get((MASK, None), 7)
    return {key: (bits & mask if key[0] in GROUP_CLASS else bits)
            for key, bits in acl.items() if key[0] != MASK}


def target_access(acl, st, uid, groups):
    if st.st_uid == uid:
        return acl[(USER_OBJ, None)]
    mask = acl.get((MASK, None), 7)
    if (USER, uid) in acl:
        return acl[(USER, uid)] & mask
    matched = []
    if st.st_gid in groups:
        matched.append(acl[(GROUP_OBJ, None)])
    matched.extend(bits for (tag, qualifier), bits in acl.items() if tag == GROUP and qualifier in groups)
    if matched:
        result = 0
        for bits in matched:
            result |= bits
        return result & mask
    return acl[(OTHER, None)]


def plan_acl(original, uid, required, st, groups):
    """Only add target r-- or --x. Never blindly recalculate an ACL mask."""
    validate_acl(original)
    if required not in (1, 4) or uid == st.st_uid:
        raise Refusal('invalid_target')
    current = target_access(original, st, uid, groups)
    if current & 2 or required == 4 and current & 1 or required == 1 and current & 4:
        raise Refusal('target_existing_permissions_exceed_scope')
    desired = dict(original)
    target = (USER, uid)
    desired[target] = current | required
    desired[(MASK, None)] = original.get((MASK, None), original[(GROUP_OBJ, None)]) | current | required
    before, after = effective_acl_entries(original), effective_acl_entries(desired)
    if any(after.get(key) != value for key, value in before.items() if key != target):
        raise Refusal('acl_mask_expansion_would_broaden_others')
    if target_access(desired, st, uid, groups) != current | required:
        raise Refusal('invalid_acl')
    return validate_acl(desired)


class LibACL:
    """Existing Linux libacl only; no installation or external command execution."""
    def __init__(self):
        try:
            # Linux ABI soname; avoid find_library's implicit external-command lookup.
            self.lib = ctypes.CDLL('libacl.so.1', use_errno=True)
            spec = {'acl_get_fd': ([ctypes.c_int], ctypes.c_void_p),
                'acl_set_fd': ([ctypes.c_int, ctypes.c_void_p], ctypes.c_int),
                'acl_from_text': ([ctypes.c_char_p], ctypes.c_void_p),
                'acl_valid': ([ctypes.c_void_p], ctypes.c_int),
                'acl_free': ([ctypes.c_void_p], ctypes.c_int),
                'acl_get_entry': ([ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int),
                'acl_get_tag_type': ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)], ctypes.c_int),
                'acl_get_qualifier': ([ctypes.c_void_p], ctypes.c_void_p),
                'acl_get_permset': ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int),
                'acl_get_perm': ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int)}
            for function, (args, restype) in spec.items():
                fn = getattr(self.lib, function)
                fn.argtypes, fn.restype = args, restype
        except (OSError, AttributeError):
            raise Refusal('libacl_unavailable') from None

    def get(self, fd):
        acl = self.lib.acl_get_fd(fd)
        if not acl:
            raise Refusal('acl_operation_failed')
        result = {}
        try:
            entry = ctypes.c_void_p()
            first = 0
            while True:
                status = self.lib.acl_get_entry(acl, first, ctypes.byref(entry))
                first = 1
                if status == 0:
                    break
                if status != 1:
                    raise Refusal('acl_operation_failed')
                tag, permset = ctypes.c_int(), ctypes.c_void_p()
                if self.lib.acl_get_tag_type(entry, ctypes.byref(tag)) or self.lib.acl_get_permset(entry, ctypes.byref(permset)):
                    raise Refusal('acl_operation_failed')
                qualifier = None
                if tag.value in (USER, GROUP):
                    pointer = self.lib.acl_get_qualifier(entry)
                    if not pointer:
                        raise Refusal('acl_operation_failed')
                    try:
                        qualifier = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint)).contents.value
                    finally:
                        self.lib.acl_free(pointer)
                bits = 0
                for bit in (4, 2, 1):
                    present = self.lib.acl_get_perm(permset, bit)
                    if present not in (0, 1):
                        raise Refusal('acl_operation_failed')
                    if present:
                        bits |= bit
                key = (tag.value, qualifier)
                if key in result:
                    raise Refusal('invalid_acl')
                result[key] = bits
            return validate_acl(result)
        finally:
            self.lib.acl_free(acl)

    def set(self, fd, value):
        acl = self.lib.acl_from_text(acl_text(value).encode('ascii'))
        if not acl:
            raise Refusal('invalid_acl')
        try:
            if self.lib.acl_valid(acl) != 0 or self.lib.acl_set_fd(fd, acl) != 0:
                raise Refusal('acl_operation_failed')
        finally:
            self.lib.acl_free(acl)


def default_acl(fd):
    try:
        return os.getxattr(fd, 'system.posix_acl_default').hex()
    except OSError as exc:
        if exc.errno in (errno.ENODATA, errno.ENOTSUP):
            return None
        raise


def read_manifest():
    fd = hold_path(MANIFEST)
    try:
        manifest = read_fd_json(fd)
    finally:
        os.close(fd)
    if hashlib.sha256(canonical(manifest)).hexdigest() != MANIFEST_SHA:
        raise Refusal('manifest_identity_mismatch')
    return manifest


def selected_artifacts(manifest):
    selected = []
    counts = {}
    for source in manifest['sources']:
        if source.get('production_enabled') is not True:
            continue
        sid = source['id']
        if sid not in FAMILY_COUNTS:
            raise Refusal('scope_mismatch')
        counts[sid] = len(source['artifacts'])
        for artifact in source['artifacts']:
            if not SAFE_NAME.fullmatch(artifact['name']):
                raise Refusal('scope_mismatch')
            selected.append((source, artifact))
    if counts != FAMILY_COUNTS or len(selected) != 50 or len({(s['id'], a['name']) for s, a in selected}) != 50:
        raise Refusal('scope_mismatch')
    return selected


def receipt_matches(receipt, source, artifact):
    if set(receipt) - ALLOWED_RECEIPT_KEYS:
        raise Refusal('receipt_schema_unreviewed')
    expected = {'schema': 'offmenu-source-fetch/1', 'source_id': source['id'], 'artifact': artifact['name'],
        'artifact_key': hashlib.sha256(canonical({'source': source['id'], 'revision': source['revision'], 'artifact': artifact})).hexdigest(),
        'source_revision': source['revision'], 'origin_url': artifact['url'], 'license': source['license'],
        'license_evidence': source['license_evidence'], 'attribution': source['attribution'],
        'license_scope_note': source.get('license_scope_note'),
        'artifact_metadata_evidence': source.get('artifact_metadata_evidence'),
        'catalog_resource_id': artifact.get('resource_id'), 'artifact_license_evidence': artifact.get('license_evidence'),
        'transport_integrity': artifact.get('transport_integrity', 'https'),
        'acquisition_only': True, 'ingested': False, 'raw_data_uploaded': False, 'status': 'complete',
        'expected_sha256': artifact.get('sha256'), 'expected_bytes': artifact.get('expected_bytes'),
        'checksum_basis': 'publisher_sha256_verified' if artifact.get('sha256') else 'locally_observed_not_publisher_authenticated'}
    if any(receipt.get(key) != value or isinstance(value, bool) and type(receipt.get(key)) is not bool for key, value in expected.items()):
        raise Refusal('receipt_mismatch')
    size, digest = receipt.get('bytes'), receipt.get('sha256')
    if type(size) is not int or not 1 <= size <= artifact['max_bytes'] or not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise Refusal('receipt_mismatch')
    if artifact.get('expected_bytes') is not None and size != artifact['expected_bytes']:
        raise Refusal('size_mismatch')
    if artifact.get('sha256') is not None and digest != artifact['sha256']:
        raise Refusal('checksum_mismatch')


def verify_bytes(fd, receipt, deadline):
    before = os.fstat(fd)
    if before.st_size != receipt['bytes']:
        raise Refusal('size_mismatch')
    os.lseek(fd, 0, os.SEEK_SET)
    digest, total = hashlib.sha256(), 0
    while True:
        if time.monotonic() >= deadline:
            raise Refusal('time_budget')
        block = os.read(fd, min(1024**2, before.st_size - total + 1))
        if not block:
            break
        total += len(block)
        if total > before.st_size:
            raise Refusal('source_changed')
        digest.update(block)
    if signature(before) != signature(os.fstat(fd)):
        raise Refusal('source_changed')
    if total != receipt['bytes'] or digest.hexdigest() != receipt['sha256']:
        raise Refusal('checksum_mismatch')


def resolve_accounts():
    try:
        actor, target = pwd.getpwnam(ACTOR), pwd.getpwnam(TARGET)
    except KeyError:
        raise Refusal('account_missing') from None
    if actor.pw_uid == 0 or os.getuid() != actor.pw_uid or os.geteuid() != actor.pw_uid:
        raise Refusal('wrong_actor')
    if target.pw_uid == 0 or target.pw_uid == actor.pw_uid:
        raise Refusal('invalid_target')
    return actor, target, set(os.getgrouplist(TARGET, target.pw_gid))


def read_scope_plan(manifest):
    fd = hold_path(SCOPE_PLAN)
    try:
        value = read_fd_json(fd)
    finally:
        os.close(fd)
    if hashlib.sha256(canonical(value)).hexdigest() != SCOPE_PLAN_SHA:
        raise Refusal('scope_mismatch')
    expected = {(source['id'], artifact['name']) for source, artifact in selected_artifacts(manifest)}
    hashes = {(row['source_id'], row['artifact']): row['sha256'] for row in value['artifacts']}
    if len(value['artifacts']) != 50 or set(hashes) != expected or value['manifest_sha256'] != MANIFEST_SHA:
        raise Refusal('scope_mismatch')
    return hashes


def make_plan(manifest, actor, target, groups, backend, root=CACHE, observed_hashes=None):
    """Owned held descriptors; caller closes even after a refused plan."""
    selected = selected_artifacts(manifest)
    if observed_hashes is None:
        observed_hashes = read_scope_plan(manifest)
    directories = [root.parent.parent, root.parent, root] + [root / sid for sid in FAMILY_COUNTS]
    entries, held = [], []
    deadline = time.monotonic() + 120
    try:
        # Ancestors outside the grant scope must already be traversable. Never
        # edit root-owned /, /srv or /srv/offmenu-refresh to manufacture access.
        for path in reversed(root.parent.parent.parents):
            fd = hold_path(path, directory=True)
            try:
                if not target_access(backend.get(fd), os.fstat(fd), target.pw_uid, groups) & 1:
                    raise Refusal('outside_ancestor_not_traversable')
            finally:
                os.close(fd)
        by_path = {}
        paths = [(path, True) for path in directories]
        for source, artifact in selected:
            path = root / source['id'] / artifact['name']
            paths.extend(((path, False), (Path(str(path) + '.receipt.json'), False)))
        for path, directory in paths:
            fd = hold_path(path, directory)
            held.append(fd)
            st = os.fstat(fd)
            if st.st_uid != actor.pw_uid or st.st_gid != actor.pw_gid:
                raise Refusal('ownership_mismatch')
            if not directory and st.st_mode & 0o111:
                raise Refusal('source_executable')
            if not directory and st.st_nlink != 1:
                raise Refusal('unexpected_hardlink')
            original = backend.get(fd)
            desired = plan_acl(original, target.pw_uid, 1 if directory else 4, st, groups)
            entry = {'path': str(path), 'directory': directory, 'fd': fd,
                'identity': data_identity(st), 'original_signature': signature(st), 'expected_signature': signature(st),
                'owner_uid': st.st_uid, 'owner_gid': st.st_gid, 'nlink': st.st_nlink,
                'original': original, 'desired': desired,
                'default_acl': default_acl(fd) if directory else None}
            entries.append(entry)
            by_path[str(path)] = entry
        verification_inputs = []
        total = 0
        for source, artifact in selected:
            path = root / source['id'] / artifact['name']
            file_entry = by_path[str(path)]
            receipt_entry = by_path[str(path) + '.receipt.json']
            receipt = read_fd_json(receipt_entry['fd'])
            receipt_matches(receipt, source, artifact)
            if receipt['sha256'] != observed_hashes.get((source['id'], artifact['name'])):
                raise Refusal('checksum_mismatch')
            verify_bytes(file_entry['fd'], receipt, deadline)
            total += receipt['bytes']
            verification_inputs.append({'source': source, 'artifact': artifact,
                'file_fd': file_entry['fd'], 'receipt_fd': receipt_entry['fd'],
                'observed_sha256': observed_hashes[(source['id'], artifact['name'])]})
        if total != EXPECTED_BYTES:
            raise Refusal('size_mismatch')
        for entry in entries:
            if (signature(os.fstat(entry['fd'])) != entry['original_signature']
                    or signature(path_stat(entry['path'])) != entry['original_signature']):
                raise Refusal('source_changed')
        plan = {'entries': entries, 'held': held, 'target_uid': target.pw_uid,
            'target_groups': sorted(groups), 'verification_inputs': verification_inputs,
            'actor_uid': actor.pw_uid, 'manifest_sha256': MANIFEST_SHA, 'source_bytes': total}
        check_sibling_exposure(plan, backend)
        return plan
    except BaseException:
        for fd in held:
            os.close(fd)
        raise


def snapshot_value(plan):
    return {'schema': SNAPSHOT_SCHEMA, 'manifest_sha256': MANIFEST_SHA,
        'target_account': TARGET, 'target_uid': plan['target_uid'], 'actor_uid': plan['actor_uid'],
        'entries': [{**{key: entry[key] for key in ('path', 'directory', 'identity', 'owner_uid', 'owner_gid', 'nlink', 'default_acl')},
            'original_acl': acl_text(entry['original']), 'planned_acl': acl_text(entry['desired'])}
            for entry in plan['entries']]}


def atomic_private(path, value, exclusive=False):
    parent = open_directory(path.parent)
    temporary = '.' + path.name + '.' + uuid.uuid4().hex + '.tmp'
    fd = None
    try:
        if exclusive:
            try:
                os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise Refusal('snapshot_write_failed')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            fd = None
            stream.write(canonical(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        # O_PATH cannot fsync; owner-open the known directory for durability.
        directory = hold_path(path.parent, True)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


def unchanged_data(entry):
    st = os.fstat(entry['fd'])
    return (data_identity(st) == entry['identity']
        and data_identity(path_stat(entry['path'])) == entry['identity']
        and st.st_uid == entry['owner_uid'] and st.st_gid == entry['owner_gid']
        and (entry['directory'] or st.st_nlink == entry['nlink'])
        and (not entry.get('expected_signature') or
             signature(st) == entry['expected_signature'] == signature(path_stat(entry['path']))))


def refresh_signature(entry):
    if 'expected_signature' in entry:
        entry['expected_signature'] = signature(os.fstat(entry['fd']))


def check_sibling_exposure(plan, backend):
    # Granting traversal must not make unselected siblings newly accessible.
    # Stop at an inaccessible child boundary: no recursive scan or payload read.
    allowed = {entry['path'] for entry in plan['entries']}
    uid, groups = plan['target_uid'], set(plan.get('target_groups', []))
    for entry in plan['entries']:
        if not entry['directory']:
            continue
        owner = os.fstat(entry['fd'])
        if target_access(entry['original'], owner, uid, groups) & 1:
            continue
        inspected = 0
        with os.scandir(entry['fd']) as children:
            for child in children:
                inspected += 1
                if inspected > 4096:
                    raise Refusal('sibling_metadata_budget')
                path = Path(entry['path']) / child.name
                if str(path) in allowed:
                    continue
                info = child.stat(follow_symlinks=False)
                if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    raise Refusal('unlisted_sibling_exposure')
                fd = hold_path(path, stat.S_ISDIR(info.st_mode))
                try:
                    if signature(info) != signature(os.fstat(fd)):
                        raise Refusal('source_changed')
                    if target_access(backend.get(fd), info, uid, groups):
                        raise Refusal('unlisted_sibling_exposure')
                finally:
                    os.close(fd)


def reverify_custody(plan):
    deadline = time.monotonic() + 120
    for item in plan.get('verification_inputs', []):
        receipt = read_fd_json(item['receipt_fd'])
        receipt_matches(receipt, item['source'], item['artifact'])
        if receipt['sha256'] != item['observed_sha256']:
            raise Refusal('checksum_mismatch')
        verify_bytes(item['file_fd'], receipt, deadline)


def apply_plan(plan, backend, snapshot_writer):
    """Snapshot first; fd-only ACL writes; exact conflict-aware rollback."""
    snapshot_writer(snapshot_value(plan))
    changed = []
    # Grant data/receipts first, then deepest directories, output traversal last.
    ordered = sorted(plan['entries'], key=lambda row: (row['directory'], -len(Path(row['path']).parts)))
    try:
        for entry in ordered:
            if not unchanged_data(entry):
                raise Refusal('source_changed')
            if backend.get(entry['fd']) != entry['original']:
                raise Refusal('concurrent_acl_change')
            if not unchanged_data(entry):
                raise Refusal('source_changed')
            if entry['directory'] and default_acl(entry['fd']) != entry['default_acl']:
                raise Refusal('default_acl_changed')
            if entry['desired'] != entry['original']:
                # Track before set: even a failing backend must be treated as
                # potentially partially applied until readback proves otherwise.
                changed.append(entry)
                backend.set(entry['fd'], entry['desired'])
                refresh_signature(entry)
            if backend.get(entry['fd']) != entry['desired']:
                raise Refusal('readback_mismatch')
        reverify_custody(plan)
        if 'target_groups' in plan:
            check_sibling_exposure(plan, backend)
        for entry in ordered:
            if not unchanged_data(entry) or backend.get(entry['fd']) != entry['desired']:
                raise Refusal('readback_mismatch')
            if entry['directory'] and default_acl(entry['fd']) != entry['default_acl']:
                raise Refusal('default_acl_changed')
        return {'status': 'complete', 'outcome': 'applied' if changed else 'already_accessible',
                'changed_acls': len(changed), 'rollback_complete': False, 'error_code': 'none'}
    except BaseException as exc:
        rollback_ok = True
        for entry in reversed(changed):
            try:
                if not unchanged_data(entry):
                    rollback_ok = False
                    continue
                current = backend.get(entry['fd'])
                if not unchanged_data(entry):
                    rollback_ok = False
                    continue
                if current == entry['original']:
                    continue
                if current != entry['desired']:
                    rollback_ok = False
                    continue
                backend.set(entry['fd'], entry['original'])
                refresh_signature(entry)
                if backend.get(entry['fd']) != entry['original']:
                    rollback_ok = False
            except Exception:
                rollback_ok = False
        return {'status': 'failed' if rollback_ok else 'partial',
            'outcome': 'rolled_back' if rollback_ok else 'rollback_incomplete',
            'changed_acls': len(changed), 'rollback_complete': rollback_ok,
            'error_code': error_code(exc) if rollback_ok else 'rollback_incomplete'}


def error_code(exc):
    if isinstance(exc, Refusal):
        return exc.code
    if isinstance(exc, PermissionError):
        return 'access_denied'
    if isinstance(exc, FileNotFoundError):
        return 'source_missing'
    return 'unexpected_error'


def sanitize_report(value):
    """Only fixed enums, booleans and counts; never paths, ACLs or source payload."""
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA:
        raise ValueError('invalid_access_handoff_report')
    if value.get('status') not in {'complete', 'blocked', 'failed', 'partial', 'planned'}:
        raise ValueError('invalid_access_handoff_status')
    if value['status'] == 'complete':
        expected = {'mode': 'apply', 'target_account': TARGET, 'manifest_sha256': MANIFEST_SHA, 'scope_plan_sha256': SCOPE_PLAN_SHA,
            'source_artifacts': 50, 'provenance_receipts': 50, 'traversal_directories': 9,
            'source_artifacts_verified': 50, 'provenance_receipts_verified': 50,
            'traversal_directories_verified': 9, 'source_bytes_verified': EXPECTED_BYTES,
            'read_only_scope_verified': True, 'other_effective_permissions_preserved': True,
            'raw_data_uploaded': False, 'source_bytes_modified': False, 'default_acls_modified': False}
        if any(value.get(key) != expected_value or type(value.get(key)) is not type(expected_value)
               for key, expected_value in expected.items()):
            raise ValueError('inconsistent_access_handoff_success')
        if type(value.get('changed_acls')) is not int or not 0 <= value['changed_acls'] <= 109:
            raise ValueError('inconsistent_access_handoff_success')
    result = {'schemaVersion': SCHEMA, 'status': value['status'],
        'mode': 'apply' if value.get('mode') == 'apply' else 'plan',
        'target_account': TARGET, 'manifest_sha256': MANIFEST_SHA, 'scope_plan_sha256': SCOPE_PLAN_SHA,
        'outcome': value.get('outcome') if value.get('outcome') in {'applied', 'already_accessible', 'planned', 'not_applied', 'rolled_back', 'rollback_incomplete'} else 'not_applied',
        'error_code': value.get('error_code') if value.get('error_code') in CODES else 'unexpected_error',
        'source_artifacts': 50, 'provenance_receipts': 50, 'traversal_directories': 9}
    for key in ('changed_acls', 'source_bytes_verified', 'source_artifacts_verified',
                'provenance_receipts_verified', 'traversal_directories_verified'):
        result[key] = value.get(key) if type(value.get(key)) is int and value[key] >= 0 else 0
    for key in ('read_only_scope_verified', 'other_effective_permissions_preserved', 'rollback_complete',
                'raw_data_uploaded', 'source_bytes_modified', 'default_acls_modified'):
        result[key] = value.get(key) is True
    if result['status'] == 'complete' and (result['mode'] != 'apply' or result['error_code'] != 'none'
            or result['source_artifacts_verified'] != 50 or result['provenance_receipts_verified'] != 50
            or result['traversal_directories_verified'] != 9
            or result['outcome'] not in {'applied', 'already_accessible'}
            or result['source_bytes_verified'] != EXPECTED_BYTES
            or not result['read_only_scope_verified'] or not result['other_effective_permissions_preserved']
            or any(result[key] for key in ('raw_data_uploaded', 'source_bytes_modified', 'default_acls_modified'))):
        raise ValueError('inconsistent_access_handoff_success')
    return result


def prepare_state(actor):
    parent = open_directory(STATE.parent)
    try:
        try:
            os.mkdir(STATE.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
    finally:
        os.close(parent)
    fd = hold_path(STATE, True)
    st = os.fstat(fd)
    os.close(fd)
    if st.st_uid != actor.pw_uid or stat.S_IMODE(st.st_mode) != 0o700:
        raise Refusal('snapshot_write_failed')
    parent = open_directory(STATE)
    try:
        lock = os.open('handoff.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != actor.pw_uid or stat.S_IMODE(info.st_mode) != 0o600:
            raise Refusal('snapshot_write_failed')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock)
        raise Refusal('lock_busy') from None
    except BaseException:
        os.close(lock)
        raise
    return lock


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply only the fixed approved named-user grant')
    args = parser.parse_args(argv)
    result = {'schemaVersion': SCHEMA, 'mode': 'apply' if args.apply else 'plan', 'status': 'blocked', 'outcome': 'not_applied', 'error_code': 'none',
              'raw_data_uploaded': False, 'source_bytes_modified': False, 'default_acls_modified': False,
              'target_account': TARGET, 'manifest_sha256': MANIFEST_SHA, 'scope_plan_sha256': SCOPE_PLAN_SHA, 'source_artifacts': 50,
              'provenance_receipts': 50, 'traversal_directories': 9}
    plan, lock = None, None
    try:
        actor, target, groups = resolve_accounts()
        backend = LibACL()
        manifest = read_manifest()
        # Plan mode has no filesystem mutations at all.
        if args.apply:
            lock = prepare_state(actor)
        plan = make_plan(manifest, actor, target, groups, backend)
        result['source_bytes_verified'] = plan['source_bytes']
        result.update(source_artifacts_verified=50, provenance_receipts_verified=50, traversal_directories_verified=9)
        if args.apply:
            snapshot = STATE / ('acl-before-' + uuid.uuid4().hex + '.private.json')
            result.update(apply_plan(plan, backend, lambda data: atomic_private(snapshot, data, exclusive=True)))
        else:
            result.update(status='planned', outcome='planned', error_code='none', changed_acls=0)
        result['read_only_scope_verified'] = result['status'] in {'complete', 'planned'}
        result['other_effective_permissions_preserved'] = result['status'] in {'complete', 'planned'}
    except Exception as exc:
        result['error_code'] = error_code(exc)
    finally:
        if plan:
            for fd in plan['held']:
                os.close(fd)
    clean = sanitize_report(result)
    # Public summary is a fixed projection only, in the existing private receipt
    # directory. The exact private ACL snapshot is never uploaded.
    if args.apply and lock is not None:
        try:
            atomic_private(REPORT, clean)
        except Exception:
            # A missing summary cannot establish success to the dispatcher.
            clean.update(status='partial' if clean['status'] == 'complete' else clean['status'],
                         error_code='snapshot_write_failed')
    try:
        print(json.dumps(clean, sort_keys=True), flush=True)
    finally:
        if lock is not None:
            os.close(lock)
    return 0 if clean['status'] in {'complete', 'planned'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
