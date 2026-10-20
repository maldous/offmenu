"""Prepared OFF full-occurrence selection and executor-owned receipt retention.

No source opener, CLI, executor or admission. Factory constants require exact
independent source review/integration; runtime/resource admission stays external.
"""
from dataclasses import dataclass
import fcntl
import hashlib
import os
import stat

from .acceptance import Asset
from .core import RefreshError, canonical
from .national_tabular import valid_input_name
from .off_partition_custody import CustodyLimits, ImplementationPins, PartitionOperation, VERSION
from .off_partition_witness import PartitionLimits

GIB = 1024**3
RECEIPT_BYTES = 1024**2
SIDECAR_TEMP_BYTES = GIB
CONTROL_BYTES = 1024**2

# Existing externally reviewed/selected basis, not verdicts manufactured here.
BASIS_SHA256 = {
    9937: 'c9e3019d17531351833e7fb748f989b8859cb689966a4dfac645a5114d3450d9',
    10481: 'e729ce5524d400602c98d1e9ac94852ccc8ba0343974dfc671a5e3f5d9f499c4',
    10498: 'a7a3f2d25b7bacca283ad4cf1e9e8b8258502dda1d774292e0b037dd276b2586',
    10450: '933350ff60214517facc9ae4c21d80950ba32abc1c198b4890cca5c7dc945703',
    10464: 'b30d0f375df10cd90307807ba7a8d02a186ce19370d3346043819c0e44fc2e54',
}


def prepared_off_limits():
    """Finite stop caps, NOT measured sufficiency/capacity or a resource charge."""
    return CustodyLimits(13132516914, 86400,
        PartitionLimits(4807663, 8*1024**2, 83278049962, 8*GIB, 4*GIB, 82800))


def prepared_off_operation():
    """Reviewed-code selection; no arguments, JSON loading, IO or grant toggle.

    Only the full original denominator is fixed. Actual partition group/member/
    S/C/Q/product counts and IDs remain outputs for separate independent review.
    The existing rights bytes are unchanged; the new clock explicitly derives
    its unknown status from the pinned9937 clock, never filesystem/run time.
    """
    return PartitionOperation('2026-10-12', 'full-retained-occurrence-partition-v1',
        Asset('off-2026-10-12.jsonl.gz', 13132516914,
              '11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e'),
        Asset('rights.json', 2031, '80ff1f6f5c52beadaf4f460c03ebc381bdcf542ab417c554c595ed73feae8549'),
        Asset('scope.json', 1179, '1093fe6c8ceb89659e38563efb4f305293f3f0e55c31245c2623a840adee2aeb'),
        Asset('clock.json', 525, '1b7de3e34280fa685fe6b1e6e7c16e40bddf2128806e71a78233bfac4963ace0'),
        Asset('selection.json', 1003, '1689635544d53824407b6c617e60731bdfa6ba8fe2af94a262312beb10e58036'),
        4807663, frozenset(('retain', 'parse', 'transform')),
        ImplementationPins(
            '1e20db873b4be99d3ddfd6a47f1299a6c3f73a65e89c35ad43db85e364941382',
            '35dcbbeb17d1a593b6fe34a383c01c83417a74f3aa3f42d61f42e063aa0917a4',
            'c6732ad4154dd8fcba989911c003110061f661175144b4bb735041114befe6cb'))


@dataclass(frozen=True)
class ReceiptTarget:
    file_fd: int
    parent_fd: int
    name: str
    file_identity: tuple
    parent_identity: tuple


def _inode(info):
    return info.st_dev, info.st_ino


def _signature(info):
    return (*_inode(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _check_target(target, *, empty=False):
    if (type(target) is not ReceiptTarget
            or any(type(fd) is not int or fd < 0 for fd in (target.file_fd, target.parent_fd))
            or not valid_input_name(target.name) or '/' in target.name
            or any(type(v) is not tuple or len(v) != 2
                   or any(type(n) is not int or n < 0 for n in v)
                   for v in (target.file_identity, target.parent_identity))):
        raise RefreshError('partition-receipt-target-invalid')
    file = os.fstat(target.file_fd)
    parent = os.fstat(target.parent_fd)
    entry = os.stat(target.name, dir_fd=target.parent_fd, follow_symlinks=False)
    flags = fcntl.fcntl(target.file_fd, fcntl.F_GETFL)
    if (not stat.S_ISREG(file.st_mode) or not stat.S_ISDIR(parent.st_mode)
            or _inode(file) != target.file_identity or _inode(parent) != target.parent_identity
            or _inode(entry) != target.file_identity or not stat.S_ISREG(entry.st_mode)
            or file.st_uid != os.getuid() or parent.st_uid != os.getuid()
            or stat.S_IMODE(file.st_mode) != 0o600 or stat.S_IMODE(parent.st_mode) != 0o700
            or file.st_nlink != 1 or flags & os.O_ACCMODE != os.O_RDWR or flags & os.O_APPEND
            or (empty and (file.st_size != 0 or os.lseek(target.file_fd, 0, os.SEEK_CUR) != 0))):
        raise RefreshError('partition-receipt-target-custody-mismatch')
    return file


def check_receipt_target(target):
    """Executor calls before source IO with its exclusively created empty target.

    This observes descriptor/name custody; O_EXCL creation and private operation
    directory ownership are executor obligations, not inferred from descriptor
    flags. Prove parent fsync capability here, before the source pass; O_PATH
    directory handles support stat but cannot satisfy this durability operation.
    Supplied descriptors remain owned/opened by the caller throughout.
    """
    _check_target(target, empty=True)
    os.fsync(target.parent_fd)
    info = _check_target(target, empty=True)
    return {'identity': _inode(info), 'bytes': info.st_size, 'emptyTargetVerified': True,
            'parentFsyncCompleted': True}


def retain_success_receipt(target, receipt):
    """Persist the direct adapter return to a caller-owned empty FD, no reopen.

    No names are created/replaced/deleted; no retry or partial-file reclamation.
    Success records file+directory fsync and readback only, never data/runtime
    admission or continuous path custody. Caller records this return separately
    in its terminal evidence; the adapter receipt's original flags stay intact.
    """
    raw = None
    try:
        _check_target(target, empty=True)
        if (type(receipt) is not dict or receipt.get('schemaVersion') != VERSION
                or any(receipt.get(k) is not True for k in
                       ('originalFileCustodyVerified', 'compressedPrePostSha256Verified', 'fullGzipCRCAndEOF'))
                or any(receipt.get(k) is not False for k in
                       ('accepted', 'runtimeQualified', 'realResourcesAdmitted', 'countryComplete',
                        'eligibleCleanScopeWitness', 'durableCustodyReceiptPublished'))):
            raise RefreshError('partition-receipt-direct-success-required')
        raw = canonical({'schemaVersion': 'offmenu-partition-custody-retention/1',
                         'accepted': False, 'adapterReceipt': receipt})
        if len(raw) > RECEIPT_BYTES:
            raise RefreshError('partition-receipt-byte-bound')
        offset = 0
        while offset < len(raw):
            count = os.write(target.file_fd, raw[offset:offset+65536])
            if count <= 0:
                raise RefreshError('partition-receipt-incomplete-write')
            offset += count
        os.fsync(target.file_fd)
        os.fsync(target.parent_fd)
        before = _check_target(target)
        chunks, offset = [], 0
        while offset < len(raw)+1:
            block = os.pread(target.file_fd, len(raw)+1-offset, offset)
            if not block:
                break
            chunks.append(block)
            offset += len(block)
        observed = b''.join(chunks)
        after = _check_target(target)
        if (observed != raw or before.st_size != len(raw)
                or _signature(before) != _signature(after)):
            raise RefreshError('partition-receipt-readback-mismatch')
        return {'schemaVersion': 'offmenu-partition-custody-retention-observation/1',
            'identity': _inode(after), 'parentIdentity': target.parent_identity,
            'location': os.readlink(f'/proc/self/fd/{target.file_fd}'),
            'bytes': len(observed), 'sha256': hashlib.sha256(observed).hexdigest(),
            'fileAndDirectoryFsyncCompleted': True, 'readbackVerified': True,
            'accepted': False, 'pointInTimeOnly': True, 'automaticDeletion': False}
    except BaseException as error:
        def observation():
            try:
                info = os.fstat(target.file_fd)
                return {'identity': _inode(info), 'bytes': info.st_size,
                        'location': os.readlink(f'/proc/self/fd/{target.file_fd}')}
            except (OSError, AttributeError, TypeError):
                return None
        error.partition_receipt_retained_state = {
            'file': observation(), 'intendedSha256': hashlib.sha256(raw).hexdigest() if raw else None,
            'retentionCompleted': False, 'automaticDeletion': False,
            'nextAction': 'Reconcile retained core/scratch/receipt; no automatic retry or overwrite.'}
        raise
