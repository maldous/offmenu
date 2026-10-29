"""Versioned private normalization -> exact field origins -> qualification bridge.

Leaves the reviewed original candidate intact. No downloads, admissions, jobs or
remote writes. All inputs are the trusted source contract's immutable bundle.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

from . import acceptance, field_provenance, product_qualification, product_clock
from .acceptance import contract_fingerprint, fingerprint, qualify
from .core import RefreshError, canonical, strict_json
from .field_provenance import field_origin_errors
from .product_adapters import ProductContext, ProductLimits, _candidate_stats, _hash, _safe, _zip_metadata
from .product_field_origins import ProductOriginEmitter
from .product_qualification import qualify_product_candidate

VERSION = 'offmenu-product-origin-stage/2'


def _members(archive, limits):
    _zip_metadata(archive, limits)
    result = {}
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path = PurePosixPath(member.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in member.filename or member.flag_bits & 1:
                raise RefreshError('product-origin-unsafe-member')
            if member.is_dir() or path.suffix.lower() != '.csv':
                continue
            if path.stem in result:
                raise RefreshError('product-origin-duplicate-table')
            result[path.stem] = member.filename
    return result


def _stage_manifest(source_manifest, stage_contract, hashes, count, candidate_bytes, originals):
    return {**source_manifest, 'schemaVersion': VERSION, 'status': 'origin-enriched-candidate',
            'candidateSha256': hashes['candidate.jsonl'], 'candidateBytes': candidate_bytes,
            'normalizedRecords': count, 'outputHashes': hashes, 'originStageContract': stage_contract,
            'originCoverage': 'complete-data-scalars', 'accepted': False,
            'rawStorage': {'externalNormalization': True, 'sha256': originals['source.sqlite'],
                           'visibility': 'private', 'publishable': False}}


def qualify_product_origins(contract, bundle, roles, normalized_destination, destination,
                            *, license, attribution, limits=ProductLimits()):
    """Normalize verified bundle, emit candidate/sidecar, qualify both origin and
    original semantic contracts. Existing complete stages are hash-checked and
    requalified. Original normalization is retained separately and never patched.
    """
    limits.validate()
    root, normalized, destination = map(_safe, (bundle, normalized_destination, destination))
    for a, b in ((root, normalized), (root, destination), (normalized, destination)):
        if a == b or a in b.parents or b in a.parents:
            raise RefreshError('product-origin-stage-path-overlap')
    original = qualify_product_candidate(contract, root, roles, normalized,
                                         license=license, attribution=attribution, limits=limits)
    # The bridge above verifies original candidate + DB hashes even on retries.
    source_manifest = original['manifest']
    db_path = _safe(normalized / 'source.sqlite')
    candidate = _safe(normalized / 'candidate.jsonl')
    originals = {'source.sqlite': _hash(db_path, limits.max_database_bytes),
                 'candidate.jsonl': _hash(candidate, limits.max_output_bytes)}
    if originals != source_manifest['outputHashes']:
        raise RefreshError('product-origin-source-hash-mismatch')
    assets = {a.path: a for a in contract.inputs}
    pins = {role: {'path': path, 'sha256': assets[path].sha256} for role, path in roles.items()}
    members = _members(root / roles['archive'], limits) if contract.source_id == 'usda-files' else {}
    context = ProductContext(contract.source_id, contract.release_id, contract.acquired_at,
                             license, attribution, contract.rights_evidence.sha256, contract.scope_evidence.sha256,
                             acquisition_clock_status=contract.acquisition_clock_status,
                             clock_evidence_sha256=contract.clock_evidence.sha256 if contract.clock_evidence else None)
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro&immutable=1', uri=True)
    pending = None
    try:
        emitter = ProductOriginEmitter(context, db, pins, members=members, limits=limits)
        wrapper_pin = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        dependency_pins = {module.__name__.rsplit('.', 1)[-1]: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                           for module in (acceptance, field_provenance, product_qualification, product_clock)}
        policy = fingerprint({'baseSemanticPolicy': contract.policy_sha256,
                              'emitter': emitter.policy, 'wrapper': wrapper_pin, 'dependencies': dependency_pins})
        def semantic(row):
            return list(contract.semantic_validator(row)) + field_origin_errors(row, emitter.pins, policy_pins=[emitter.policy])
        enriched_contract = replace(contract, semantic_validator=semantic, policy_sha256=policy)
        stage_contract = {'version': VERSION, 'sourceContractSha256': contract_fingerprint(enriched_contract),
                          'sourceOutputHashes': originals, 'normalizationManifestSha256': _hash(normalized / 'manifest.json'),
                          'inputRoleMap': roles, 'inputPins': pins, 'archiveMembers': members,
                          'emitterPolicySha256': emitter.policy, 'wrapperPolicySha256': wrapper_pin, 'dependencyPolicyPins': dependency_pins,
                          'limits': vars(limits)}
        if destination.exists():
            manifest_path = _safe(destination / 'manifest.json')
            if manifest_path.stat().st_size > 1024 * 1024:
                raise RefreshError('product-origin-stage-manifest-bound')
            manifest = strict_json(manifest_path.read_bytes())
            if manifest.get('originStageContract') != stage_contract:
                raise RefreshError('product-origin-stage-contract-mismatch')
            if set(manifest.get('outputHashes', {})) != {'candidate.jsonl', 'field-origins.jsonl'}:
                raise RefreshError('product-origin-stage-output-set')
            for name, digest in manifest['outputHashes'].items():
                if _hash(_safe(destination / name), limits.max_output_bytes) != digest:
                    raise RefreshError('product-origin-stage-output-mismatch')
            count, candidate_bytes, _ = _candidate_stats(destination / 'candidate.jsonl', limits)
            expected = _stage_manifest(source_manifest, stage_contract, manifest['outputHashes'], count, candidate_bytes, originals)
            if canonical(manifest) != canonical(expected):
                raise RefreshError('product-origin-stage-manifest-mismatch')
            qualification = qualify(enriched_contract, root, destination / 'candidate.jsonl', manifest)
            return {'candidate': destination / 'candidate.jsonl', 'sidecar': destination / 'field-origins.jsonl',
                    'manifest': manifest, 'qualification': qualification}
        destination.parent.mkdir(parents=True, exist_ok=True)
        pending = Path(tempfile.mkdtemp(prefix='.product-origins-', dir=destination.parent))
        count = candidate_bytes = sidecar_bytes = 0
        with candidate.open('rb') as source, (pending / 'candidate.jsonl').open('wb') as output, (pending / 'field-origins.jsonl').open('wb') as sidecar:
            while True:
                line = source.readline(limits.max_line_bytes + 1)
                if not line:
                    break
                if len(line) > limits.max_line_bytes:
                    raise RefreshError('product-origin-stage-line-bound')
                batch = strict_json(line)
                if not isinstance(batch, list) or len(batch) != 1 or not isinstance(batch[0], dict):
                    raise RefreshError('product-origin-stage-record-shape')
                record = emitter.emit(batch[0])
                data = canonical([record])
                origins = canonical([{'id': record['id'], 'fieldOrigins': record['provenance']['fieldOrigins']}])
                count += 1
                candidate_bytes += len(data)
                sidecar_bytes += len(origins)
                if count > limits.max_rows or max(candidate_bytes, sidecar_bytes) > limits.max_output_bytes:
                    raise RefreshError('product-origin-stage-output-bound')
                output.write(data)
                sidecar.write(origins)
        if not count:
            raise RefreshError('product-origin-stage-empty')
        db.close()
        db = None
        # Detect input, original candidate or DB mutation while emission was running.
        for name, digest in originals.items():
            if _hash(_safe(normalized / name), limits.max_database_bytes if name == 'source.sqlite' else limits.max_output_bytes) != digest:
                raise RefreshError('product-origin-source-changed')
        for path, asset in assets.items():
            if (root / path).stat().st_size != asset.bytes or _hash(_safe(root / path)) != asset.sha256:
                raise RefreshError('product-origin-input-changed')
        hashes = {name: _hash(pending / name) for name in ('candidate.jsonl', 'field-origins.jsonl')}
        manifest = _stage_manifest(source_manifest, stage_contract, hashes, count, candidate_bytes, originals)
        qualification = qualify(enriched_contract, root, pending / 'candidate.jsonl', manifest)
        (pending / 'manifest.json').write_bytes(canonical(manifest))
        if destination.exists():
            raise RefreshError('product-origin-stage-destination-race')
        pending.rename(destination)
        return {'candidate': destination / 'candidate.jsonl', 'sidecar': destination / 'field-origins.jsonl',
                'manifest': manifest, 'qualification': qualification}
    finally:
        if db is not None:
            db.close()
        if pending is not None and pending.exists():
            shutil.rmtree(pending)
