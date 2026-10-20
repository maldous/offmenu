"""Explicit retained-product clock protocol, independent of acquisition/cache TTL.

Only reviewed application SourceContracts select this protocol. A source manifest
or a proposal JSON document is never a contract constructor or permission grant.
"""
from dataclasses import asdict
from datetime import datetime
import hashlib
import os
from pathlib import PurePosixPath
import re
import stat

DIGEST = re.compile(r'[0-9a-f]{64}')
UNKNOWN = 'unknown-retained'
VERSION = 'offmenu-retained-product-clock/1'
MAX_EVIDENCE_BYTES = 1024 * 1024


def clock_marker(status, evidence_sha256):
    return {'status': UNKNOWN, 'evidenceSha256': evidence_sha256} if status == UNKNOWN else None


def validate_clock(source_id, acquired_at, status='known', evidence_sha256=None):
    if status == 'known':
        if evidence_sha256 is not None or not isinstance(acquired_at, str):
            raise ValueError('known-clock-required')
        acquired = datetime.fromisoformat(acquired_at.replace('Z', '+00:00'))
        if acquired.tzinfo is None or acquired.utcoffset() is None:
            raise ValueError('known-clock-timezone-required')
    elif (status != UNKNOWN or source_id not in ('off', 'usda-files')
          or acquired_at is not None or not isinstance(evidence_sha256, str)
          or not DIGEST.fullmatch(evidence_sha256)):
        raise ValueError('retained-clock-contract-invalid')


def validate_contract_clock(contract, bundle=None):
    """Preflight before payload parsing; verify clock/scope bytes when supplied.

Evidence has a small separate bound and is part of the exact immutable input set.
Scope declares the exact clock evidence; clock evidence binds all parser assets,
source/release/scope and rights. This does not qualify independent counts or rights.
"""
    evidence = contract.clock_evidence
    validate_clock(contract.source_id, contract.acquired_at, contract.acquisition_clock_status,
                   evidence.sha256 if evidence is not None else None)
    if contract.acquisition_clock_status == 'known':
        return
    from .acceptance import Asset, _safe, _valid_asset, canonical
    if (not isinstance(evidence, Asset) or not _valid_asset(evidence)
            or evidence not in contract.inputs
            or evidence.path in (contract.rights_evidence.path, contract.scope_evidence.path)
            or not 0 < evidence.bytes <= MAX_EVIDENCE_BYTES
            or not 0 < contract.scope_evidence.bytes <= MAX_EVIDENCE_BYTES
            or contract.output_scope != 'native' or contract.output_visibility != 'private'):
        raise ValueError('retained-clock-evidence-required')
    if bundle is None:
        return
    from .core import strict_json
    def read(asset):
        if not _valid_asset(asset) or not 0 < asset.bytes <= MAX_EVIDENCE_BYTES:
            raise ValueError('retained-clock-evidence-custody')
        p = _safe(_safe(bundle) / asset.path)
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        try:
            before = p.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_size != asset.bytes:
                raise ValueError('retained-clock-evidence-custody')
            fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or signature(before) != signature(opened):
                    raise ValueError('retained-clock-evidence-custody')
                chunks, size = [], 0
                while size <= asset.bytes:
                    block = os.read(fd, min(65536, asset.bytes - size + 1))
                    if not block:
                        break
                    chunks.append(block)
                    size += len(block)
                after = os.fstat(fd)
            finally:
                os.close(fd)
            current = _safe(p).lstat()
            raw = b''.join(chunks)
            if (not stat.S_ISREG(current.st_mode)
                    or signature(before) != signature(after) or signature(after) != signature(current)
                    or len(raw) != asset.bytes or hashlib.sha256(raw).hexdigest() != asset.sha256):
                raise ValueError('retained-clock-evidence-custody')
        except OSError:
            raise ValueError('retained-clock-evidence-custody') from None
        # Parse this exact verified buffer; never reopen the path for JSON.
        return strict_json(raw)
    clock, scope = read(evidence), read(contract.scope_evidence)
    identity = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                'scopeId': contract.scope_id}
    inputs = sorted((asdict(a) for a in contract.inputs
                     if a not in (evidence, contract.rights_evidence, contract.scope_evidence)),
                    key=lambda a: a['path'])
    expected = {**identity, 'schemaVersion': 'offmenu-retained-clock-evidence/1',
                'status': UNKNOWN, 'originalAcquiredAt': None,
                'rightsEvidenceSha256': contract.rights_evidence.sha256, 'inputFiles': inputs}
    if (not isinstance(clock, dict) or not isinstance(scope, dict) or not inputs
            or any(k not in clock or canonical(clock[k]) != canonical(v) for k, v in expected.items())
            or 'originalAcquiredAt' not in clock
            or not isinstance(clock.get('basisEvidenceSha256'), str)
            or not DIGEST.fullmatch(clock['basisEvidenceSha256'])
            or any(scope.get(k) != v for k, v in identity.items())
            or scope.get('acquisitionClock') != clock_marker(UNKNOWN, evidence.sha256)):
        raise ValueError('retained-clock-scope-binding-mismatch')


def resolve_retained_usda_release(alias, archive):
    """Resolve only the retained April artifact, using trusted metadata pins.

No IO, publisher authentication or broad month mapping. Call explicitly from a
reviewed binder before constructing a SourceContract; old receipts stay unchanged.
The normal qualification bridge must still verify the actual archive bytes.
"""
    from .acceptance import Asset, _valid_asset
    if (not isinstance(archive, Asset) or not _valid_asset(archive)
            or PurePosixPath(archive.path).name != 'FoodData_Central_csv_2026-04-30.zip'
            or archive.bytes != 481_517_495
            or archive.sha256 != 'c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01'
            or alias not in (None, 'usda-2026-04', '2026-04', '2026-04-30')):
        raise ValueError('usda-retained-release-alias-unbound')
    return '2026-04-30'
