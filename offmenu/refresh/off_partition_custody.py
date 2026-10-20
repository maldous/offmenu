"""Opt-in OFF gzip custody adapter; no real operation factory or admission.

The typed operation is selected by reviewed application code, never constructed
from source/cache JSON. Evidence hashes bind that selection; they do not grant
rights, establish independent review or qualify an executor by themselves.
"""
from dataclasses import asdict, dataclass
import gzip
import hashlib
from pathlib import Path
import re
import time

from .acceptance import Asset, _valid_asset
from .core import RefreshError, canonical, safe_path, strict_json
from .national_tabular import bundle_files, valid_input_name
from . import product_input_witness as original_protocol
from . import off_partition_witness as partition_core
from .product_clock import UNKNOWN, clock_marker, validate_clock

VERSION = 'offmenu-off-partition-custody/1'
OPERATION = 'private-retained-off-full-occurrence-partition'
PARTITION_POLICY = 'full-original-ordinal-SCQ-no-primary/1'
EXECUTOR_REQUIREMENTS = (
    'serialized-linux-default-sqlite-main-file-attribution',
    'external-os-wallclock-memory-file-storage-boundary',
    'retained-scratch-active-until-safe-owner-disposition',
)


@dataclass(frozen=True)
class ImplementationPins:
    adapter_sha256: str
    partition_core_sha256: str
    original_protocol_sha256: str


@dataclass(frozen=True)
class CustodyLimits:
    max_input_bytes: int
    max_seconds: int
    partition: partition_core.PartitionLimits

    @property
    def max_archive_members(self):
        # Only the reused regular-file protocol's unbounded-read ceiling uses
        # this property. Gzip reads are bounded; this adapter accepts no archive.
        return 1


@dataclass(frozen=True)
class PartitionOperation:
    release_id: str
    scope_id: str
    original: Asset
    rights_evidence: Asset
    scope_evidence: Asset
    clock_evidence: Asset
    selection_evidence: Asset
    expected_rows: int
    permitted_operations: frozenset
    implementation: ImplementationPins
    holds: tuple = ()
    fixture: bool = False


def _implementation_observation():
    # Entry/postcheck source-file observations, not proof of the loaded runtime.
    return ImplementationPins(*(hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in (__file__, partition_core.__file__, original_protocol.__file__)))


def _operation_value(operation):
    value = asdict(operation)
    value['permitted_operations'] = sorted(operation.permitted_operations)
    return value


def _assets(operation):
    return (operation.rights_evidence, operation.scope_evidence,
            operation.clock_evidence, operation.selection_evidence)


def _validate(operation, limits):
    try:
        if (type(operation) is not PartitionOperation or type(limits) is not CustodyLimits
                or type(limits.partition) is not partition_core.PartitionLimits
                or type(operation.implementation) is not ImplementationPins
                or type(operation.permitted_operations) is not frozenset
                or not {'retain', 'parse', 'transform'} <= operation.permitted_operations
                or any(type(v) is not str or not v for v in operation.permitted_operations)
                or type(operation.holds) is not tuple or operation.holds
                or type(operation.fixture) is not bool
                or any(type(s) is not str or not s for s in (operation.release_id, operation.scope_id))
                or type(operation.expected_rows) is not int
                or not 1 <= operation.expected_rows <= limits.partition.max_rows
                or any(type(v) is not int or not 0 < v < 2**63
                       for v in (limits.max_input_bytes, limits.max_seconds, *asdict(limits.partition).values()))
                or limits.partition.max_database_bytes < 65536
                or limits.partition.max_seconds > limits.max_seconds):
            raise ValueError()
        assets = (operation.original, *_assets(operation))
        if (any(type(a) is not Asset or not _valid_asset(a) or not valid_input_name(a.path)
                or a.bytes <= 0 for a in assets)
                or len({a.path for a in assets}) != len(assets)
                or operation.original.bytes > limits.max_input_bytes
                or any(a.bytes > 1024**2 for a in assets[1:])
                or any(type(s) is not str or not re.fullmatch('[0-9a-f]{64}', s)
                       for s in asdict(operation.implementation).values())):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise RefreshError('partition-custody-contract-invalid') from None


def _guard(deadline):
    if time.monotonic() >= deadline:
        raise RefreshError('partition-custody-duration-bound')


def _metadata(operation, root, deadline):
    assets = _assets(operation)
    expected = {a.path for a in assets}
    if bundle_files(root, expected) != expected:
        raise RefreshError('partition-custody-evidence-set-mismatch')
    return {a.path: original_protocol._verified_metadata_bytes(a, root, deadline) for a in assets}


def _preflight(operation, root, limits, deadline):
    metadata = _metadata(operation, root, deadline)
    identity = {'sourceId': 'off', 'releaseId': operation.release_id, 'scopeId': operation.scope_id}
    scope = {**identity, 'schemaVersion': 'offmenu-off-partition-scope/1',
        'operation': OPERATION, 'original': asdict(operation.original),
        'rightsEvidenceSha256': operation.rights_evidence.sha256,
        'acquisitionClock': clock_marker(UNKNOWN, operation.clock_evidence.sha256),
        'denominator': 'full-declared-original', 'table': 'products',
        'framing': 'gzip-utf8-jsonl-lf', 'expectedSourceRows': operation.expected_rows,
        'partitionPolicy': PARTITION_POLICY, 'cooperativeLimits': asdict(limits),
        'executorRequirements': list(EXECUTOR_REQUIREMENTS)}
    selection = {**identity, 'schemaVersion': 'offmenu-off-partition-selection/1',
        'operation': OPERATION, 'original': asdict(operation.original),
        'scopeEvidenceSha256': operation.scope_evidence.sha256,
        'rightsEvidenceSha256': operation.rights_evidence.sha256,
        'clockEvidenceSha256': operation.clock_evidence.sha256,
        'expectedSourceRows': operation.expected_rows,
        'implementation': asdict(operation.implementation),
        'permittedOperations': sorted(operation.permitted_operations), 'fixture': operation.fixture}
    for asset, expected in ((operation.scope_evidence, scope), (operation.selection_evidence, selection)):
        if canonical(strict_json(metadata[asset.path])) != canonical(expected):
            raise RefreshError('partition-custody-selected-scope-mismatch')
    clock = strict_json(metadata[operation.clock_evidence.path])
    expected_clock = {**identity, 'schemaVersion': 'offmenu-retained-clock-evidence/1',
        'status': UNKNOWN, 'originalAcquiredAt': None,
        'rightsEvidenceSha256': operation.rights_evidence.sha256,
        'inputFiles': [asdict(operation.original)]}
    validate_clock('off', None, UNKNOWN, operation.clock_evidence.sha256)
    if (type(clock) is not dict or set(clock) != {*expected_clock, 'basisEvidenceSha256'}
            or any(canonical(clock[k]) != canonical(v) for k, v in expected_clock.items())
            or type(clock['basisEvidenceSha256']) is not str
            or not re.fullmatch('[0-9a-f]{64}', clock['basisEvidenceSha256'])):
        raise RefreshError('partition-custody-clock-mismatch')
    if operation.implementation != _implementation_observation():
        raise RefreshError('partition-custody-implementation-mismatch')
    _guard(deadline)


def partition_retained_original(operation, evidence_root, original_root, destination, *, limits):
    """Return a separate custody receipt only after the complete adapter succeeds.

    No CLI, source factory, publication wrapper, cleanup or executor admission.
    A late error may leave core evidence with its original unqualified flags;
    that core result alone is never an adapter custody/acceptance receipt.
    """
    _validate(operation, limits)
    deadline = time.monotonic() + limits.max_seconds
    evidence, originals, destination = map(safe_path, (evidence_root, original_root, destination))
    roots = (evidence, originals, destination)
    if any(a == b or a in b.parents or b in a.parents
           for i, a in enumerate(roots) for b in roots[i+1:]):
        raise RefreshError('partition-custody-root-overlap')
    if destination.exists():
        raise RefreshError('partition-custody-destination-exists')
    _preflight(operation, evidence, limits, deadline)
    source = None
    stream = None
    result = None
    rows = expanded = 0
    pre_hash = post_hash = full_eof = False

    def lines():
        nonlocal rows, expanded, post_hash, full_eof
        with gzip.GzipFile(fileobj=source, mode='rb') as gzip_stream:
            while True:
                _guard(deadline)
                raw = gzip_stream.readline(limits.partition.max_line_bytes + 1)
                _guard(deadline)
                if not raw:
                    break
                rows += 1
                expanded += len(raw)
                # No filtering/coercion/reframing; the accepted core owns JSON,
                # LF, row/expanded caps and exact all-occurrence classification.
                yield raw
        source.verify()
        post_hash = True
        _metadata(operation, evidence, deadline)
        _guard(deadline)
        full_eof = True

    try:
        source = original_protocol._VerifiedOriginal(originals / operation.original.path,
                                                       operation.original, limits, deadline)
        source.verify()
        pre_hash = True
        initial_identity = source.identity
        stream = lines()
        result = partition_core.partition_stream(stream, destination,
            original_sha256=operation.original.sha256, expected_rows=operation.expected_rows,
            limits=limits.partition)
        source.check()
        _metadata(operation, evidence, deadline)
        if operation.implementation != _implementation_observation():
            raise RefreshError('partition-custody-implementation-mismatch')
        _guard(deadline)
        if (not full_eof or not post_hash or rows != operation.expected_rows
                or result['inputStreamRows'] != rows or result['inputExpandedBytes'] != expanded
                or result['streamEOF'] is not True):
            raise RefreshError('partition-custody-incomplete-stream')
        return {'schemaVersion': VERSION, 'operation': _operation_value(operation),
            'operationSha256': hashlib.sha256(canonical(_operation_value(operation))).hexdigest(),
            'fixture': operation.fixture, 'originalFileCustodyVerified': True,
            'originalIdentityBefore': initial_identity, 'originalIdentityAfter': source.identity,
            'compressedPrePostSha256Verified': True, 'fullGzipCRCAndEOF': True,
            'originalAcquiredAt': None, 'acquisitionClockStatus': UNKNOWN,
            'sourceRows': rows, 'expandedBytes': expanded, 'cooperativeLimits': asdict(limits),
            'returnedPartitionResultSha256': hashlib.sha256(canonical(result)).hexdigest(),
            'partition': result, 'executorRequirements': list(EXECUTOR_REQUIREMENTS),
            'runtimeQualified': False, 'realResourcesAdmitted': False,
            'accepted': False, 'eligibleCleanScopeWitness': False,
            'expectedRecords': None, 'expectedSortedIdSha256': None,
            'countryComplete': False, 'durableCustodyReceiptPublished': False}
    except BaseException as error:
        error.partition_custody_state = {
            'compressedPreHashVerified': pre_hash, 'compressedPostHashVerified': post_hash,
            'fullGzipCRCAndEOF': full_eof, 'rowsForwarded': rows, 'expandedBytesForwarded': expanded,
            'coreReturned': result is not None,
            'requestedCoreOutputLocation': str(destination),
            'coreOutputPresenceVerified': False,
            'unqualifiedCoreOutputLocation': str(destination) if result is not None else None,
            'returnedCoreDirectoryIdentity': result['publicationDirectoryIdentity'] if result is not None else None,
            'returnedCoreResultSha256': hashlib.sha256(canonical(result)).hexdigest() if result is not None else None,
            'custodyReceiptReturned': False, 'accepted': False}
        if result is not None and not hasattr(error, 'partition_retained_state'):
            error.partition_retained_state = result['retainedScratch']
        raise
    finally:
        if stream is not None:
            stream.close()
        if source is not None:
            source.close()
