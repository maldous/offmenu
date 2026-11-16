#!/usr/bin/env python3
"""Read-only, bounded platform metadata/integrity checks. No admission locks.
Never reads job logs, credentials, arbitrary datasets, or historical worktrees.
Verification hashes only canonical objects named by platform artifact manifests.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent / 'storage'))
import offmenu_storage as storage

ROOT = Path('/offmenu/data/.offmenu-platform')
MAX_BYTES = 64 * 1024 * 1024
MAX_SECONDS = 8
MAX_SCAN = 1000
HEX = re.compile(r'[0-9a-f]{64}\Z')
JOB = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
ACTIVE = {'starting', 'running', 'queued'}
TERMINAL = {'succeeded', 'failed', 'timed_out', 'cancelled', 'supervisor_error', 'blocked_reconciliation'}


class BudgetStop(Exception):
    def __init__(self, reason): self.reason = reason


class Budget:
    def __init__(self, byte_limit, seconds):
        self.limit = byte_limit; self.bytes = 0
        self.deadline = time.monotonic() + seconds
    def check(self):
        if time.monotonic() >= self.deadline: raise BudgetStop('deadline')
    def charge(self, size):
        if size > self.limit - self.bytes: raise BudgetStop('bytes')
        self.bytes += size
        self.check()


def audit(mode, max_items=100, root=ROOT, byte_limit=MAX_BYTES, seconds=MAX_SECONDS):
    if mode not in ('health', 'verify') or type(max_items) is not int or not 1 <= max_items <= 100:
        raise ValueError('Invalid bounded check')
    root = Path(root).absolute()
    budget = Budget(byte_limit, seconds)
    report = {'schema_version': 1, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'mode': mode, 'ok': True, 'findings': [],
              'counts': {'items_checked': 0, 'items_skipped': 0, 'entries_scanned': 0,
                         'jobs_checked': 0, 'markers_checked': 0, 'checkpoints_verified': 0,
                         'artifact_manifests_verified': 0, 'artifact_objects_hashed': 0},
              'budgets': {'max_items': max_items, 'max_bytes': byte_limit, 'max_seconds': seconds},
              'coverage': {'full_coverage': False, 'scope': 'recent job metadata and fixed in-flight markers' if mode == 'health' else 'selected current checkpoints and artifact manifests; no history/orphan scan',
                           'selection_truncated': False, 'stopped_reason': None}}
    def finding(code, severity='error', **identifiers):
        if len(report['findings']) < 110:
            report['findings'].append({'code': code, 'severity': severity, **identifiers})
        if severity == 'error': report['ok'] = False
    def bounded_read(path, limit=storage.MAX_JSON_BYTES):
        budget.check()
        remaining = budget.limit - budget.bytes
        if remaining <= 0: raise BudgetStop('bytes')
        p = Path(path).absolute()
        storage._no_symlink_components(p)
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode): raise storage.StorageError('Invalid metadata file')
            if before.st_size > limit: raise storage.StorageError('Metadata exceeds size limit')
            if before.st_size > remaining: raise BudgetStop('bytes')
            data = stream.read(min(limit + 1, remaining))
            budget.charge(len(data))  # Account even malformed/racing data before raising.
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns) or len(data) != before.st_size or len(data) > limit:
            raise storage.StorageError('Metadata changed during read')
        return data
    def metadata(path):
        def invalid_constant(value): raise ValueError('Non-finite metadata')
        return json.loads(bounded_read(path).decode('utf-8'), parse_constant=invalid_constant)
    def selected(directory, kind):
        if not directory.exists(): return []
        if directory.resolve() != directory or not directory.is_dir():
            finding('UNSAFE_COLLECTION'); return []
        candidates = []
        with os.scandir(directory) as entries:
            for index, entry in enumerate(entries):
                budget.check()
                if index >= MAX_SCAN:
                    report['coverage']['selection_truncated'] = True; break
                report['counts']['entries_scanned'] += 1
                if entry.is_symlink():
                    report['counts']['items_skipped'] += 1; finding('SYMLINK_ENTRY'); continue
                name = entry.name
                valid = JOB.fullmatch(name) if kind == 'job' else (HEX.fullmatch(name[:-5]) if kind == 'manifest' and name.endswith('.json') else HEX.fullmatch(name) if kind == 'checkpoint' else False)
                if not valid:
                    report['counts']['items_skipped'] += 1; continue
                p = Path(entry.path)
                if kind != 'manifest': p = p / ('receipt.json' if kind == 'job' else 'current.json')
                try:
                    if p.is_symlink(): raise ValueError('Symlink metadata')
                    modified = p.stat().st_mtime_ns
                except (OSError, ValueError):
                    report['counts']['items_skipped'] += 1; finding('MISSING_OR_UNSAFE_METADATA'); continue
                candidates.append((modified, name, p))
        candidates.sort(reverse=True)
        if len(candidates) > max_items: report['coverage']['selection_truncated'] = True
        return candidates[:max_items]
    def check_job(job_id, receipt, marker=False):
        if not isinstance(receipt, dict) or receipt.get('job_id') != job_id:
            finding('INVALID_JOB_RECEIPT', job_id=job_id); return
        state = receipt.get('status')
        if state in ACTIVE:
            heartbeat = receipt.get('heartbeat_at')
            if type(heartbeat) not in (int, float) or not math.isfinite(heartbeat) or not -30 <= time.time() - heartbeat <= 30:
                finding('STALE_ACTIVE_JOB', job_id=job_id)
            elif marker: finding('ACTIVE_INFLIGHT_JOB', 'info', job_id=job_id)
        elif state in TERMINAL:
            if marker or receipt.get('child_tree_gone') is not True:
                finding('UNRESOLVED_INFLIGHT_JOB', job_id=job_id)
            elif state in ('failed', 'timed_out', 'supervisor_error'):
                finding('COMPLETED_NON_SUCCESS', 'info', job_id=job_id, status=state)
        else: finding('UNKNOWN_JOB_STATE', job_id=job_id)

    original_read = storage.read_regular
    cache = {}
    class BoundedStore(storage.Store):
        def _verify_object(self, relative, sha, size):
            budget.check()
            path = self.path(relative)
            before = path.stat(follow_symlinks=False)
            identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            if cache.get((relative, sha, size)) == identity: return
            if type(size) is not int or size < 0: raise storage.StorageError('Invalid size')
            if before.st_size != size: raise storage.StorageError('Object length mismatch')
            if size > budget.limit - budget.bytes: raise BudgetStop('bytes')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            h = hashlib.sha256(); actual = 0
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise storage.StorageError('Invalid object')
                while actual < size:
                    budget.check()
                    chunk = stream.read(min(65536, size - actual, budget.limit - budget.bytes))
                    if not chunk: break
                    budget.charge(len(chunk)); actual += len(chunk); h.update(chunk)
                    if actual > size: raise storage.StorageError('Object length changed')
                after = os.fstat(stream.fileno())
            identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            if identity != identity_after or actual != size or h.hexdigest() != sha:
                raise storage.StorageError('Object integrity failure')
            cache[(relative, sha, size)] = identity
            report['counts']['artifact_objects_hashed'] += 1
    try:
        budget.check()
        if root.resolve() != root or not root.is_dir():
            finding('ROOT_UNAVAILABLE'); return report
        s = root.stat()
        if s.st_uid != os.getuid() or s.st_mode & 0o077:
            finding('ROOT_OWNERSHIP_OR_MODE'); return report
        storage.read_regular = bounded_read
        if mode == 'health':
            # Fixed markers are checked even if recent-job selection is full.
            for n in range(2):
                budget.check()
                marker = root / 'locks' / ('execution-slot-%s.inflight.json' % n)
                if not marker.exists() and not marker.is_symlink(): continue
                report['counts']['markers_checked'] += 1
                try:
                    data = metadata(marker); job_id = data.get('job_id')
                    if not isinstance(job_id, str) or not JOB.fullmatch(job_id): raise ValueError('Invalid id')
                    check_job(job_id, metadata(root / 'jobs' / job_id / 'receipt.json'), marker=True)
                except BudgetStop: raise
                except Exception: finding('INVALID_INFLIGHT_MARKER')
            for _, job_id, path in selected(root / 'jobs', 'job'):
                budget.check()
                try: check_job(job_id, metadata(path))
                except BudgetStop: raise
                except Exception: finding('INVALID_JOB_RECEIPT', job_id=job_id)
                report['counts']['jobs_checked'] += 1; report['counts']['items_checked'] += 1
        else:
            store = BoundedStore(root)
            for _, key_hash, path in selected(root / 'checkpoints', 'checkpoint'):
                budget.check()
                if report['counts']['items_checked'] >= max_items:
                    report['coverage']['selection_truncated'] = True; break
                try:
                    pointer = metadata(path)
                    if not isinstance(pointer,dict) or set(pointer)!={'key','version','sha256'}: raise storage.StorageError('Invalid pointer')
                    key = pointer['key']
                    storage.valid_key(key)
                    if hashlib.sha256(key.encode()).hexdigest() != key_hash: raise ValueError('Key mismatch')
                    verified = store.verify(key, version=pointer['version'])
                    if verified['sha256'] != pointer['sha256']: raise storage.StorageError('Pointer checksum mismatch')
                    after = metadata(path)
                    if (not isinstance(after,dict) or set(after)!={'key','version','sha256'}
                            or after['key'] != key or not isinstance(after['version'],str)
                            or not storage.VERSION.fullmatch(after['version'])
                            or not isinstance(after['sha256'],str) or not HEX.fullmatch(after['sha256'])):
                        raise storage.StorageError('Invalid advanced pointer')
                    if pointer != after and pointer['version'] == after['version']:
                        raise storage.StorageError('Same-version pointer changed')
                    if pointer != after:
                        report['counts']['items_skipped'] += 1
                        finding('CHECKPOINT_ADVANCED', 'warning', checkpoint_hash=key_hash)
                    else:
                        report['counts']['checkpoints_verified'] += 1
                except BudgetStop: raise
                except Exception: finding('CHECKPOINT_INTEGRITY_FAILED', checkpoint_hash=key_hash)
                report['counts']['items_checked'] += 1
            for _, name, path in selected(root / 'artifacts' / 'manifests', 'manifest'):
                budget.check()
                if report['counts']['items_checked'] >= max_items:
                    report['coverage']['selection_truncated'] = True; break
                try:
                    store.verify_artifact('artifacts/manifests/' + name)
                    report['counts']['artifact_manifests_verified'] += 1
                except BudgetStop: raise
                except Exception: finding('ARTIFACT_INTEGRITY_FAILED', manifest_hash=name[:-5])
                report['counts']['items_checked'] += 1
    except BudgetStop as stop:
        report['coverage']['stopped_reason'] = stop.reason
        report['counts']['items_skipped'] += 1
        finding('BUDGET_LIMIT_REACHED', 'warning')
    except Exception:
        finding('CHECK_UNAVAILABLE')
    finally:
        storage.read_regular = original_read
        report['budgets']['bytes_read'] = budget.bytes
        report['coverage']['selected_scope_complete'] = not (report['coverage']['selection_truncated'] or report['coverage']['stopped_reason'] or report['counts']['items_skipped'])
        report['status'] = 'incomplete' if not report['coverage']['selected_scope_complete'] else ('ok' if report['ok'] else 'findings')
        report['ok'] = report['ok'] and report['coverage']['selected_scope_complete']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('health', 'verify'), required=True)
    parser.add_argument('--max-items', type=int, default=100)
    args = parser.parse_args()
    def alarm(signum, frame): raise BudgetStop('deadline')
    signal.signal(signal.SIGALRM, alarm); signal.alarm(MAX_SECONDS)
    try: result = audit(args.mode, args.max_items)
    except Exception:
        result = {'schema_version': 1, 'mode': args.mode, 'ok': False,
                  'findings': [{'code': 'CHECK_REQUEST_FAILED', 'severity': 'error'}]}
    finally: signal.alarm(0)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['ok'] else 1

if __name__ == '__main__': sys.exit(main())
