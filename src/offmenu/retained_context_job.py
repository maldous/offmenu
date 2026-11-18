"""Offline, bounded effect boundary for one retained-context shard on Linux.

No default issuer, process launcher or production CLI. The owner supplies private
directory descriptors and an independently verified, *held* authority guard
for each effect. Existing helpers' files and cursors are never repaired in place.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import os
import re
import stat
import time
from uuid import uuid4


class Refused(ValueError):
    """An unresolved input, authority or output requires owner reconciliation."""


def need(ok, why):
    if not ok:
        raise Refused(why)


def wire(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def pairs(items):
        d = dict(items)
        need(len(d) == len(items), 'duplicate JSON key')
        return d
    def no_constant(_):
        raise Refused('nonfinite JSON number')
    return json.loads(data, object_pairs_hook=pairs, parse_constant=no_constant)


HASH = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,159}')
SHARD = re.compile(r'cohort-[0-9]{3,}/chunk-[0-9]{5,}')
DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
READ = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


@dataclass(frozen=True)
class Unit:
    provider: str
    release: str
    queue: str
    shard: str
    operation: str
    generation: int
    queue_sha256: str
    assignment_sha256: str
    rights_sha256: str
    parser_sha256: str
    inputs_sha256: str
    destination_device: int
    destination_inode: int
    max_rows: int
    max_output_bytes: int
    batch_rows: int

    def check(self):
        need(self.provider in ('off', 'usda-files'), 'unrecognised provider')
        need(all(isinstance(v, str) and NAME.fullmatch(v) for v in
                 (self.release, self.queue, self.operation)), 'identity')
        need(isinstance(self.shard, str) and SHARD.fullmatch(self.shard), 'shard')
        need(all(isinstance(v, str) and HASH.fullmatch(v) for v in
                 (self.queue_sha256, self.assignment_sha256, self.rights_sha256,
                  self.parser_sha256, self.inputs_sha256)), 'pins')
        for n, ceiling in ((self.generation, 2**63-1), (self.max_rows, 5000),
                           (self.batch_rows, 250), (self.max_output_bytes, 128*1024**2)):
            need(type(n) is int and 0 < n <= ceiling, 'bound')
        need(self.batch_rows <= self.max_rows, 'batch size')
        need(all(type(n) is int and n >= 0 for n in
                 (self.destination_device, self.destination_inode)), 'destination identity')

    @property
    def key(self):
        return digest(wire(asdict(self)))

    @property
    def namespace(self):
        # Exclude operation, generation, queue version and hashes: a second
        # writer cannot escape the original source/release/shard exclusion.
        return 'context-' + digest(wire([self.provider, self.release, self.shard]))


def _read(fd, name, cap):
    with os.fdopen(os.open(name, READ, dir_fd=fd), 'rb') as f:
        a = os.fstat(f.fileno())
        need(stat.S_ISREG(a.st_mode) and a.st_size <= cap, 'output shape or size')
        data = f.read(cap+1)
        b = os.fstat(f.fileno())
        need(len(data) == a.st_size and (a.st_mtime_ns, a.st_ctime_ns) ==
             (b.st_mtime_ns, b.st_ctime_ns), 'output changed')
        return data


def _maybe(fd, name, cap):
    try:
        return _read(fd, name, cap)
    except FileNotFoundError:
        return None


def _install(fd, name, data, crash):
    """Durably install immutable bytes; never truncate, replace or adopt a conflicting file."""
    tmp = '.pending-' + uuid4().hex
    with os.fdopen(os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                           0o600, dir_fd=fd), 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        crash('before-link:' + name)
        try:
            os.link(tmp, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        except FileExistsError:
            need(_read(fd, name, len(data)) == data, 'immutable destination conflict')
        os.fsync(fd)
        crash('after-link:' + name)
    finally:
        # Only this invocation's own temporary name. After power loss an
        # orphan remains unadmitted; never delete or recover another writer's files.
        os.unlink(tmp, dir_fd=fd)
        os.fsync(fd)


@contextmanager
def _hold(issuer, unit, purpose):
    """Trusted deployment adapter holds authority until context exit, not just at lookup.

    The claim store and its fencing mechanism are external to this package. A
    serialized document, a PID, an old receipt, or a no-op context is not a guard.
    """
    need(callable(getattr(issuer, 'hold', None)), 'no current claim issuer')
    with issuer.hold(unit.key, purpose) as grant:
        need(isinstance(grant,dict) and grant.get('unit')==unit.key and
             grant.get('generation')==unit.generation and grant.get('operation')==unit.operation
             and grant.get('purpose')==purpose and grant.get('effect_fenced') is True and
             grant.get('prior_effects_reconciled') is True and grant.get('rights_verified') is True
             and grant.get('resources_reserved') is True and grant.get('offline_only') is True and
             type(grant.get('valid_until')) in (float,int) and grant['valid_until']>time.time(),
             'missing/stale scope, predecessor, rights or admission')
        yield


@contextmanager
def _workspace(parent, unit, guard):
    p = os.fstat(parent)
    need((p.st_dev, p.st_ino) == (unit.destination_device, unit.destination_inode),
         'wrong destination')
    need(stat.S_ISDIR(p.st_mode) and p.st_uid == os.geteuid() and not p.st_mode & 0o077,
         'destination must be an owner-private directory')
    with _hold(guard, unit, 'open-workspace'):
        try:
            os.mkdir(unit.namespace, 0o700, dir_fd=parent)
            os.fsync(parent)
        except FileExistsError:
            pass
        fd = os.open(unit.namespace, DIR, dir_fd=parent)
    try:
        inside = os.fstat(fd)
        need(inside.st_uid == os.geteuid() and inside.st_mode & 0o077 == 0,
             'workspace is not private')
        # Directory lock has stable identity; no unlinkable/recreated lock file.
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused('writer already active') from None
        yield fd
    finally:
        os.close(fd)


def execute(unit, *, destination_fd, guard, produce, crash=lambda _: None):
    """Execute the admitted shard or return an exactly verified terminal receipt.

    The issuer.hold(unit.key, purpose) context must hold the real claim/epoch, policy, output/resource
    admission through the operation. produce(start) yields already verified
    semantic results starting at that input ordinal; it must not mutate state.
    """
    unit.check()
    need(callable(getattr(guard,'hold',None)) and callable(produce), 'missing authority/producer')
    with _workspace(destination_fd, unit, guard) as fd:
        binding = wire({'schema':'offmenu-retained-shard/1', 'unit':asdict(unit)})
        first = _maybe(fd, 'binding.json', 8192)
        if first is None:
            need(not [n for n in os.listdir(fd) if not re.fullmatch(r'\.pending-[0-9a-f]{32}', n)],
                 'unbound workspace contains effects')
            with _hold(guard, unit, 'bind-operation'):
                _install(fd, 'binding.json', binding, crash)
        else:
            need(first == binding, 'existing operation or generation differs')
        names = os.listdir(fd)
        orphans = [n for n in names if re.fullmatch(r'\.pending-[0-9a-f]{32}',n)]
        need(len(orphans) <= 8, 'unadmitted temporary files require reconciliation')
        for n in orphans:
            orphan = os.stat(n,dir_fd=fd,follow_symlinks=False)
            need(stat.S_ISREG(orphan.st_mode) and orphan.st_size <= unit.max_output_bytes+8192,
                 'unadmitted object exceeds bound')
        part_names = sorted(n for n in names if re.fullmatch(r'part-[0-9]{5}\.json', n))
        allowed = set(part_names) | {'binding.json', 'receipt.json'}
        need(all(n in allowed or re.fullmatch(r'\.pending-[0-9a-f]{32}', n) for n in names),
             'unreconciled workspace file')
        pos = 0
        seq = 0
        used = 0
        chain = unit.key
        cap = unit.max_output_bytes + 1024
        def part(payload, before):
            need(isinstance(payload, list) and 1 <= len(payload) <= unit.batch_rows
                 and all(isinstance(v, dict) for v in payload), 'invalid output batch')
            data = wire(payload)
            body = {'unit':unit.key,'from':before,'previous':chain,
                    'payload_sha256':digest(data),'rows':payload}
            return wire(body), len(data)
        for index,name in enumerate(part_names):
            need(name == f'part-{index:05d}.json', 'checkpoint gap')
            raw = _read(fd, name, cap)
            obj = decode(raw)
            expected, nbytes = part(obj['rows'], pos)
            need(raw == expected, 'checkpoint integrity or binding')
            need(index == len(part_names)-1 or len(obj['rows']) == unit.batch_rows,
                 'nonfinal short checkpoint')
            pos += len(obj['rows']); used += nbytes; chain = digest(raw); seq += 1
            need(pos <= unit.max_rows and used <= unit.max_output_bytes, 'checkpoint bounds')
        def receipt():
            return wire({'schema':'offmenu-retained-terminal/1','unit':unit.key,
                         'rows':pos,'segments':seq,'payload_bytes':used,'chain':chain,
                         'published':False,'canonical_acceptance':False})
        done = _maybe(fd, 'receipt.json', 8192)
        if done is not None:
            need(done == receipt() and pos == unit.max_rows, 'terminal integrity')
            with _hold(guard, unit, 'observe-terminal'):
                return decode(done)
        def commit(batch):
            nonlocal pos, seq, used, chain
            raw,nbytes = part(batch, pos)
            need(pos+len(batch) <= unit.max_rows and used+nbytes <= unit.max_output_bytes,
                 'output exceeds admission')
            with _hold(guard, unit, 'commit-segment'):
                _install(fd, f'part-{seq:05d}.json', raw, crash)
            seq += 1; pos += len(batch); used += nbytes; chain=digest(raw)
        # Scope opening, reads and each batch of computation under the issuer;
        # keep the guard simple/non-reentrant, recheck it before every effect.
        if pos < unit.max_rows:
            with _hold(guard, unit, 'open-input'):
                rows = iter(produce(pos))
            try:
                while pos < unit.max_rows:
                    with _hold(guard, unit, 'consume-input'):
                        batch = []
                        batch_bytes = 0
                        for _ in range(min(unit.batch_rows, unit.max_rows-pos)):
                            try: row=next(rows)
                            except StopIteration: raise Refused('source ended before admitted count') from None
                            need(isinstance(row, dict), 'invalid row')
                            # Bound each buffered batch before serializing the rest.
                            batch_bytes += len(wire(row))+1
                            need(used+batch_bytes <= unit.max_output_bytes, 'output exceeds admission')
                            batch.append(row)
                        # Before recording the final segment, prove exact EOF. A
                        # crash after its link may safely finalize without replay.
                        if pos + len(batch) == unit.max_rows:
                            try: next(rows)
                            except StopIteration: pass
                            else: raise Refused('source exceeds admitted count')
                    commit(batch)
            finally:
                if hasattr(rows, 'close'):
                    rows.close()
        with _hold(guard, unit, 'commit-terminal'):
            data = receipt()
            _install(fd, 'receipt.json', data, crash)
        return decode(data)
