#!/usr/bin/env python3
"""Explicit incremental storage arithmetic and bounded scratch writes.

This module accounts managed allocations, without a whole-filesystem reservation
or corpus-run authority. SQLite/temp/journal/importer writers remain refused until
controlled owner integration covers every allocation.
Unknown bounds are refused, never replaced by sample averages.
"""
import argparse
import contextlib
import fcntl
import datetime as dt
import json
import os
from pathlib import Path

MAX_PROBE_BYTES = 256 * 1024**2
COMPONENTS = ('output', 'checkpoint_with_journal', 'qualification_scratch', 'copies')


class BudgetRefusal(ValueError):
    pass


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise BudgetRefusal(f'{name} must be an integer >= {minimum}; unknown bounds refused')
    return value


def capacity(available_bytes, available_inodes, reserve_bytes, reserve_inodes,
             fixed_bytes, fixed_inodes, per_record_bytes, per_record_inodes,
             batch_cap_bytes, requested_records):
    """Count all simultaneous incremental allocations; no reclaim/link discount.

    Per-record values are caller-supplied conservative upper bounds, not inferred
    from measurements. Cap excludes untouched originals and retained reserve.
    """
    values = locals().copy()
    for name in ('available_bytes', 'available_inodes', 'reserve_bytes',
                 'reserve_inodes', 'fixed_bytes', 'fixed_inodes', 'requested_records'):
        integer(values[name], name)
    integer(reserve_bytes, 'reserve_bytes', 1)
    integer(reserve_inodes, 'reserve_inodes', 1)
    integer(batch_cap_bytes, 'batch_cap_bytes', 1)
    if batch_cap_bytes > MAX_PROBE_BYTES:
        raise BudgetRefusal('bounded batch cap exceeds 256 MiB')
    for name, mapping in (('per_record_bytes', per_record_bytes),
                          ('per_record_inodes', per_record_inodes)):
        if not isinstance(mapping, dict) or set(mapping) != set(COMPONENTS):
            raise BudgetRefusal(f'{name} requires all four explicit components')
        for key, value in mapping.items():
            integer(value, f'{name}.{key}')
    b = integer(sum(per_record_bytes.values()), 'total per-record bytes', 1)
    i = integer(sum(per_record_inodes.values()), 'total per-record inodes', 1)
    byte_headroom = min(available_bytes - reserve_bytes, batch_cap_bytes) - fixed_bytes
    inode_headroom = available_inodes - reserve_inodes - fixed_inodes
    maximum = max(0, min(byte_headroom // b, inode_headroom // i))
    required_b = fixed_bytes + requested_records * b
    required_i = fixed_inodes + requested_records * i
    fits = (requested_records > 0 and byte_headroom >= 0 and inode_headroom >= 0
            and requested_records <= maximum)
    return {'maximumRecordsArithmetic': maximum, 'requestedRecords': requested_records,
            'incrementalPeakBoundBytes': required_b, 'incrementalPeakBoundInodes': required_i,
            'reserveBytes': reserve_bytes, 'reserveInodes': reserve_inodes,
            'batchCapBytes': batch_cap_bytes, 'capacityPass': fits,
            'executionAuthorized': False, 'reservationEstablished': False,
            'unknownPeakAccepted': False}


def filesystem(target):
    """Bind an exact existing destination to current user-available capacity."""
    path = Path(target).resolve(strict=True)
    if not path.is_dir():
        raise BudgetRefusal('target must be an existing directory')
    st, fs = path.stat(), os.statvfs(path)
    return {'target': str(path), 'device': st.st_dev,
            'deviceMajorMinor': f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}',
            'inode': st.st_ino, 'fragmentBytes': fs.f_frsize,
            'availableBytes': fs.f_bavail * fs.f_frsize,
            'availableInodes': fs.f_favail,
            'measuredAtUtc': dt.datetime.now(dt.timezone.utc).isoformat()}


LEDGER_BYTES = 65536
BATCH_BYTES = 238354432
BATCH_INODES = 4016
BATCH_RECORDS = 1000
RESERVE_BYTES = 10 * 1024**3
RESERVE_INODES = 10000


class SharedBudget:
    """One flock-protected ledger for all cooperating processes/categories.

    Only managed preallocated direct-child files are supported. SQLite, temp,
    arbitrary subprocess and importer writers are refused. No cleanup discount;
    reservations remain charged even after failure. An interrupted operation
    poisons the ledger, so a restart cannot forget a pending allocation.
    """
    ledger_name = '.worker61-budget'

    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise BudgetRefusal('destination must be owned by caller and private (0700)')
        if not self.root.is_dir():
            raise BudgetRefusal('private existing directory required')
        self.path = self.root / self.ledger_name

    @classmethod
    def create(cls, root, cap_bytes=BATCH_BYTES, cap_inodes=BATCH_INODES,
               cap_records=BATCH_RECORDS, reserve_bytes=RESERVE_BYTES,
               reserve_inodes=RESERVE_INODES):
        for name, value, maximum in (('cap_bytes', cap_bytes, BATCH_BYTES),
                                    ('cap_inodes', cap_inodes, BATCH_INODES),
                                    ('cap_records', cap_records, BATCH_RECORDS)):
            integer(value, name, 1)
            if value > maximum:
                raise BudgetRefusal(f'{name} exceeds reviewed proposal ceiling')
        integer(reserve_bytes, 'reserve_bytes', RESERVE_BYTES)
        integer(reserve_inodes, 'reserve_inodes', RESERVE_INODES)
        budget = cls(root)
        if any(budget.root.iterdir()):
            raise BudgetRefusal('fresh empty private directory required')
        fs = filesystem(budget.root)
        # Root directory already exists, but it and the control ledger are charged.
        fixed = budget.root.stat().st_blocks * 512 + LEDGER_BYTES + 65536
        if fixed > cap_bytes or cap_inodes < 2:
            raise BudgetRefusal('control bytes/inodes exceed cap before ledger creation')
        if fs['availableBytes'] < reserve_bytes + fixed or fs['availableInodes'] < reserve_inodes + 1:
            raise BudgetRefusal('filesystem reserve unavailable before ledger creation')
        state = dict(version=1, device=fs['device'], root_inode=fs['inode'], root=str(budget.root),
                     cap_bytes=cap_bytes, cap_inodes=cap_inodes, cap_records=cap_records,
                     reserve_bytes=reserve_bytes, reserve_inodes=reserve_inodes,
                     charged_bytes=fixed, charged_inodes=2, charged_records=0,
                     active=False, blocked=False, files={})
        fd = os.open(budget.path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.posix_fallocate(fd, 0, LEDGER_BYTES)
            budget._save(fd, state)
            if os.fstat(fd).st_blocks * 512 > LEDGER_BYTES + 65536:
                state['blocked'] = True
                budget._save(fd, state)
                raise BudgetRefusal('control allocation exceeds reserved envelope')
        finally:
            os.close(fd)
        return budget

    def _save(self, fd, state):
        raw = json.dumps(state, separators=(',', ':')).encode()
        if len(raw) > LEDGER_BYTES:
            raise BudgetRefusal('ledger metadata capacity exhausted')
        os.pwrite(fd, raw.ljust(LEDGER_BYTES, b' '), 0)
        os.fsync(fd)

    @contextlib.contextmanager
    def locked(self):
        fd = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            if os.fstat(fd).st_ino != self.path.stat().st_ino:
                raise BudgetRefusal('ledger replaced')
            try:
                state = json.loads(os.pread(fd, LEDGER_BYTES, 0))
            except (ValueError, OSError) as error:
                raise BudgetRefusal('unreadable shared ledger') from error
            if state.get('version') != 1 or state.get('root') != str(self.root) or state.get('device') != self.root.stat().st_dev or state.get('root_inode') != self.root.stat().st_ino:
                raise BudgetRefusal('ledger target mismatch')
            if state.get('active') or state.get('blocked'):
                raise BudgetRefusal('failed/interrupted writer requires explicit reconciliation')
            actual_names = {p.name for p in self.root.iterdir()} - {self.ledger_name}
            if actual_names != set(state['files']):
                raise BudgetRefusal('unknown or missing allocation; uncontrolled writer refused')
            for name, receipt in state['files'].items():
                st = (self.root / name).lstat()
                if not (self.root / name).is_file() or (st.st_dev, st.st_ino) != tuple(receipt['identity']) or st.st_blocks * 512 > receipt['bound']:
                    raise BudgetRefusal('allocation identity/physical bound changed')
            yield fd, state
        finally:
            os.close(fd)

    def snapshot(self):
        with self.locked() as (_, state):
            return state

    def external_writer(self, *args, **kwargs):
        raise BudgetRefusal('uncontrolled SQLite/journal/temp/subprocess writer refused; managed writes only')

    def write(self, name, chunks, max_file_bytes, category, records=0):
        integer(max_file_bytes, 'max_file_bytes', 1)
        integer(records, 'records')
        if category not in COMPONENTS:
            raise BudgetRefusal('unknown allocation category')
        if not isinstance(name, str) or not name or len(name) > 80 or name.startswith('.') or Path(name).name != name:
            raise BudgetRefusal('direct private child filename required')
        with self.locked() as (ledger, state):
            fs = filesystem(self.root)
            block = fs['fragmentBytes']
            bound = ((max_file_bytes + block - 1) // block) * block + 65536
            # Whole-file physical envelope and one inode are charged BEFORE open.
            if state['charged_bytes'] + bound > state['cap_bytes'] or state['charged_inodes'] + 1 > state['cap_inodes'] or state['charged_records'] + records > state['cap_records']:
                raise BudgetRefusal('shared byte/inode/record cap refused before create')
            if fs['availableBytes'] < state['reserve_bytes'] + bound or fs['availableInodes'] < state['reserve_inodes'] + 1:
                raise BudgetRefusal('fresh filesystem reserve refused before create')
            if os.path.lexists(self.root / name):
                raise FileExistsError(name)
            if len(json.dumps(state).encode()) + len(name) + 512 > LEDGER_BYTES:
                raise BudgetRefusal('ledger receipt capacity refused before create')
            state['charged_bytes'] += bound
            state['charged_inodes'] += 1
            state['charged_records'] += records
            state['active'] = True
            self._save(ledger, state)
            fd = None
            try:
                fd = os.open(self.root / name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                # Real physical allocation, not logical length/sparse accounting.
                os.posix_fallocate(fd, 0, ((max_file_bytes + block - 1) // block) * block)
                if os.fstat(fd).st_blocks * 512 > bound:
                    raise BudgetRefusal('physical allocator exceeded reserved envelope')
                length = 0
                for chunk in chunks:
                    if length + len(chunk) > max_file_bytes:
                        raise BudgetRefusal('file ceiling refused before chunk write')
                    offset = 0
                    while offset < len(chunk):
                        written = os.pwrite(fd, chunk[offset:], length + offset)
                        if written <= 0:
                            raise OSError('short allocation write')
                        offset += written
                    length += len(chunk)
                os.fsync(fd)
                st = os.fstat(fd)
                if st.st_blocks * 512 > bound:
                    raise BudgetRefusal('physical file bound exceeded')
                fresh = filesystem(self.root)
                if fresh['availableBytes'] < state['reserve_bytes'] or fresh['availableInodes'] < state['reserve_inodes']:
                    raise BudgetRefusal('filesystem reserve changed during managed write')
                state['files'][name] = {'category':category, 'bound':bound,
                                        'identity':[st.st_dev, st.st_ino],
                                        'payloadBytes':length, 'allocatedBytes':st.st_blocks * 512}
                state['active'] = False
                self._save(ledger, state)
                return state['files'][name]
            except BaseException:
                state['blocked'] = True
                self._save(ledger, state)
                raise
            finally:
                if fd is not None:
                    os.close(fd)


class CappedWriter:
    """Compatibility entry point; unshared legacy guards now fail closed."""
    def __init__(self, cap_bytes=None, block_bytes=4096, fixed_bytes=0, *, budget=None,
                 category='qualification_scratch'):
        if not isinstance(budget, SharedBudget):
            raise BudgetRefusal('SharedBudget required; private per-writer counters refused')
        if cap_bytes is not None or block_bytes != 4096 or fixed_bytes != 0:
            raise BudgetRefusal('legacy private cap arguments refused; configure shared ledger')
        self.budget, self.category = budget, category

    def write(self, path, chunks, max_file_bytes, records=0):
        path = Path(path)
        if path.parent.resolve() != self.budget.root:
            raise BudgetRefusal('file outside shared-budget destination')
        return self.budget.write(path.name, chunks, max_file_bytes, self.category, records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    try:
        measured = filesystem(args.target)
        plan = json.loads(args.plan.read_text())
        result = capacity(measured['availableBytes'], measured['availableInodes'], **plan)
        print(json.dumps({'measuredFilesystem': measured, 'estimatedBounds': plan,
                          'decision': result}, indent=2))
        return 0 if result['capacityPass'] else 2
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({'capacityPass': False, 'executionAuthorized': False,
                          'refusal': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
