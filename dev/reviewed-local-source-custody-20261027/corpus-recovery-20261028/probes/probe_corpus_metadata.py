#!/usr/bin/env python3
"""Fixed-scope, bounded, read-only metadata inventory. Never reads packet payloads.

Run only after approved mounts are installed, through the existing Foo runner.
Historical package roles are hints, not current qualification assertions.
"""
import errno
import hashlib
import json
import os
import signal
import stat
import time

ROOT = '/offmenu-corpus'
PACKAGES = (
    'common-data-reviewed-package-20261014',
    'common-reference-delivery-final-20261014',
    'common-national-semantic-final-20261014',
    'measurement-terminology-final-qualified-20261014',
    'recipe-expansion-final-qualified-20261014/common-graph',
    'historical-recipe-quality-final-corrected-20261014',
    'common-bulk-food-semantic-final-20261014',
    'common-places-semantic-final-20261014.partial',
)
RECEIPTS = ('common-ready-six-package-global-20261014.json',
            'custody-positive-quiescence-20261014.json')
COUNT_KEYS = ('assets', 'packets', 'resources', 'assertions', 'relations',
              'translations', 'externalReferences', 'sourceCount',
              'sourceRecordTotal', 'recipeRecords', 'packageCount')
MAX_ENTRIES = 200000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_METADATA_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 16
MAX_SECONDS = 25


class BudgetStop(Exception):
    pass


class Budget:
    def __init__(self):
        self.deadline = time.monotonic() + MAX_SECONDS
        self.entries = 0
        self.bytes = 0

    def check(self):
        if time.monotonic() >= self.deadline:
            raise BudgetStop('time_budget')


def open_beneath(root_fd, name, directory=False):
    """Walk fixed relative paths without following any symbolic-link component."""
    parts = name.split('/')
    if any(p in ('', '.', '..') for p in parts) or name.startswith('/'):
        raise ValueError('not a fixed relative path')
    fd = os.dup(root_fd)
    try:
        for i, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if i < len(parts)-1 or directory:
                flags |= os.O_DIRECTORY
            nxt = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def numeric_fields(obj):
    if not isinstance(obj, dict):
        return {}
    return {k: obj[k] for k in COUNT_KEYS
            if type(obj.get(k)) is int and 0 <= obj[k] <= 10**18}


def metadata(fd, budget):
    """Only called for allowlisted manifest.json or the two custody receipts."""
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        return {'status': 'not_regular_no_read'}
    result = {'bytes': st.st_size}
    if st.st_size > MAX_FILE_BYTES or budget.bytes + st.st_size > MAX_METADATA_BYTES:
        return dict(result, status='metadata_byte_budget_no_read')
    chunks = []
    total = 0
    while True:
        budget.check()
        block = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - total))
        if not block:
            break
        total += len(block)
        budget.bytes += len(block)
        if total > MAX_FILE_BYTES or budget.bytes > MAX_METADATA_BYTES:
            return dict(result, status='metadata_grew_or_byte_budget')
        chunks.append(block)
    after = os.fstat(fd)
    if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        return dict(result, status='changed_during_read')
    raw = b''.join(chunks)
    result.update(status='hashed', sha256=hashlib.sha256(raw).hexdigest())
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            result['json_object'] = False
            return result
        result['json_object'] = True
        # No arbitrary strings, paths, source records or user-supplied keys emitted.
        result['declared_counts'] = numeric_fields(obj.get('counts'))
        result['declared_top_level_counts'] = numeric_fields(obj)
        for key in ('files', 'assets', 'packages'):
            if isinstance(obj.get(key), list):
                result['declared_' + key + '_entries'] = len(obj[key])
        if type(obj.get('complete')) is bool:
            result['declared_complete'] = obj['complete']
        if isinstance(obj.get('aggregateObservedCounts'), dict):
            result['declared_aggregate_counts'] = numeric_fields(obj['aggregateObservedCounts'])
    except (ValueError, UnicodeError, RecursionError):
        result['json_object'] = False
    return result


def scan(fd, budget, result, depth=0):
    budget.check()
    if depth > MAX_DEPTH:
        result['complete'] = False
        result['depth_skips'] += 1
        return
    if not os.fstatvfs(fd).f_flag & os.ST_RDONLY:
        result['complete'] = False
        result['non_readonly_subtrees'] += 1
        return
    with os.scandir(fd) as entries:
        for entry in entries:
            budget.check()
            if budget.entries >= MAX_ENTRIES:
                raise BudgetStop('entry_budget')
            budget.entries += 1
            st = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                result['directories'] += 1
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                                os.O_CLOEXEC, dir_fd=fd)
                try:
                    scan(child, budget, result, depth + 1)
                finally:
                    os.close(child)
            elif stat.S_ISREG(st.st_mode):
                result['regular_files'] += 1
                result['regular_file_bytes_from_stat'] += st.st_size
            elif stat.S_ISLNK(st.st_mode):
                result['symlinks_not_followed'] += 1
                result['complete'] = False
            else:
                result['special_files_not_opened'] += 1
                result['complete'] = False


def run():
    budget = Budget()
    result = {'schema': 'offmenu-corpus-metadata-probe/1', 'read_only': True,
              'full_data_verification': False, 'qualification_established': False,
              'packages': [], 'receipts': [], 'stopped_reason': None}
    root_fd = None
    try:
        root_fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        for index, name in enumerate(PACKAGES):
            budget.check()
            row = {'package': name, 'historical_role': 'ready' if index < 6 else 'partial'}
            result['packages'].append(row)
            fd = None
            try:
                fd = open_beneath(root_fd, name, directory=True)
                row['exists'] = True
                row['mounted_readonly'] = bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY)
                if not row['mounted_readonly']:
                    row['status'] = 'not_readonly_no_inspection'
                    continue
                try:
                    mfd = open_beneath(fd, 'manifest.json')
                    try:
                        row['manifest.json'] = metadata(mfd, budget)
                    finally:
                        os.close(mfd)
                except OSError as exc:
                    row['manifest.json'] = {'status': 'absent' if exc.errno == errno.ENOENT else 'unreadable_or_unsafe', 'errno': exc.errno}
                counters = dict(complete=True, directories=0, regular_files=0,
                                regular_file_bytes_from_stat=0, symlinks_not_followed=0,
                                special_files_not_opened=0, non_readonly_subtrees=0, depth_skips=0)
                row['metadata_scan'] = counters
                try:
                    scan(fd, budget, counters)
                except BudgetStop:
                    counters['complete'] = False
                    raise
                except OSError as exc:
                    counters.update(complete=False, error_errno=exc.errno)
            except OSError as exc:
                row.update(exists=False if exc.errno == errno.ENOENT else None,
                           status='missing_or_inaccessible', error_errno=exc.errno)
            finally:
                if fd is not None:
                    os.close(fd)
        for name in RECEIPTS:
            budget.check()
            row = {'receipt': name}
            result['receipts'].append(row)
            fd = None
            try:
                fd = open_beneath(root_fd, name)
                row['mounted_readonly'] = bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY)
                row['metadata'] = metadata(fd, budget) if row['mounted_readonly'] else {'status': 'not_readonly_no_inspection'}
            except OSError as exc:
                row.update(status='missing_or_inaccessible', error_errno=exc.errno)
            finally:
                if fd is not None:
                    os.close(fd)
    except BudgetStop as exc:
        result['stopped_reason'] = str(exc)
    except OSError as exc:
        result['stopped_reason'] = 'mount_root_inaccessible'
        result['error_errno'] = exc.errno
    finally:
        if root_fd is not None:
            os.close(root_fd)
    result['budget_usage'] = {'entries': budget.entries, 'metadata_bytes_read': budget.bytes}
    result['scope_attempted_complete'] = (result['stopped_reason'] is None and
                                         len(result['packages']) == 8 and len(result['receipts']) == 2)
    return result


if __name__ == '__main__':
    def deadline(signum, frame):
        raise BudgetStop('hard_time_budget')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(28)
    outcome = run()
    signal.alarm(0)
    print(json.dumps(outcome, sort_keys=True, separators=(',', ':')))
