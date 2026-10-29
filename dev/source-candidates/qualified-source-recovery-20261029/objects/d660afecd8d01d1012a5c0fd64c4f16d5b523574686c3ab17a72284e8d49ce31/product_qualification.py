"""Evidence-pinned bridge from product candidates to offline qualification.

Trusted contracts come from reviewed application code, never source documents.
This bridge does not install admissions, publish, or accept any output scope.
"""
from dataclasses import asdict
from pathlib import Path, PurePosixPath
import re

from .core import RefreshError, canonical
from .product_adapters import ProductContext, ProductLimits, _safe, _hash, normalize_products


def qualify_product_candidate(contract, bundle, roles, destination, *, license,
                              attribution, limits=ProductLimits(), input_root=None):
    """Verify full retained bundle before parsing, then qualify exact candidate.

    roles maps parser roles to contract-relative asset paths (not evidence roles).
    With input_root, private OFF/USDA parser assets remain there in place while
    bundle contains exactly evidence assets; unrelated originals are not scanned.
    The original normalization manifest is immutable. A separate evidence-inclusive
    qualification-manifest.json records the exact independently reviewed bundle.
    Returns qualification diagnostics without promoting native/curated/common state.
    """
    from .acceptance import qualify, _input_paths, _hash_file
    from .national_tabular import bundle_files, valid_input_name
    limits.validate()
    if contract.holds:
        raise RefreshError('product-source-held')
    if (not {'retain', 'parse', 'transform'} <= set(contract.required_operations)
            or not set(contract.required_operations) <= set(contract.permitted_operations)):
        raise RefreshError('product-operation-rights-missing')
    if contract.output_scope != 'native' or contract.output_visibility != 'private':
        raise RefreshError('product-native-contract-required')
    from .product_clock import validate_contract_clock
    try:
        validate_contract_clock(contract, bundle)
    except (ValueError, TypeError, AttributeError, OSError):
        raise RefreshError('product-clock-contract-invalid') from None
    root = _safe(bundle)
    assets = {}
    for asset in contract.inputs:
        relative = PurePosixPath(asset.path)
        if (not valid_input_name(asset.path) or relative.is_absolute() or '..' in relative.parts or not relative.parts
                or relative.as_posix() != asset.path or '\\' in asset.path
                or asset.path in assets or type(asset.bytes) is not int or asset.bytes < 0
                or not re.fullmatch('[0-9a-f]{64}', asset.sha256)):
            raise RefreshError('product-invalid-input-pin')
        assets[asset.path] = asset
    if (not assets or len(assets) > 256 or sum(a.bytes for a in assets.values()) > limits.max_input_bytes
            or contract.rights_evidence not in contract.inputs or contract.scope_evidence not in contract.inputs):
        raise RefreshError('product-input-contract-incomplete')
    try:
        paths, bundle_names = _input_paths(contract, root, input_root)
    except ValueError:
        raise RefreshError('product-input-roots-invalid') from None
    if bundle_files(root, bundle_names) != bundle_names:
        raise RefreshError('product-bundle-set-mismatch')
    evidence_paths = {contract.rights_evidence.path, contract.scope_evidence.path}
    if contract.clock_evidence is not None:
        evidence_paths.add(contract.clock_evidence.path)
    if (len(set(roles.values())) != len(roles) or not set(roles.values()) <= set(assets)
            or evidence_paths & set(roles.values())):
        raise RefreshError('product-invalid-role-map')
    # Every non-evidence asset must have an explicit parser role, no scope drift.
    if set(roles.values()) != set(assets) - evidence_paths:
        raise RefreshError('product-unassigned-input')
    for path, asset in sorted(assets.items(), key=lambda item: item[0] not in evidence_paths):
        try:
            if _hash_file(paths[path], limits.max_input_bytes) != (asset.bytes, asset.sha256):
                raise ValueError('input-pin-mismatch')
        except (ValueError, OSError):
            raise RefreshError('product-input-pin-mismatch') from None
    context = ProductContext(contract.source_id, contract.release_id, contract.acquired_at,
                             license, attribution, contract.rights_evidence.sha256,
                             contract.scope_evidence.sha256,
                             acquisition_clock_status=contract.acquisition_clock_status,
                             clock_evidence_sha256=contract.clock_evidence.sha256 if contract.clock_evidence else None)
    destination = _safe(destination)
    for source_root in (root,) if input_root is None else (root, _safe(input_root)):
        if destination == source_root or source_root in destination.parents or destination in source_root.parents:
            raise RefreshError('product-output-overlaps-bundle')
    original = normalize_products(context, {role: paths[path] for role, path in roles.items()},
                                  destination, limits=limits)
    manifest = {**original, 'inputFiles': [asdict(a) for a in sorted(contract.inputs, key=lambda a: a.path)],
                'normalizationManifestSha256': _hash(destination / 'manifest.json'),
                'inputRoleMap': dict(roles)}
    # Qualification rechecks original/evidence pins after parsing to catch mutation.
    result = qualify(contract, root, destination / 'candidate.jsonl', manifest, input_root=input_root)
    path = _safe(destination / 'qualification-manifest.json')
    encoded = canonical(manifest)
    if path.exists():
        if path.stat().st_size != len(encoded) or path.read_bytes() != encoded:
            raise RefreshError('product-qualification-manifest-mismatch')
    else:
        with path.open('xb') as output:
            output.write(encoded)
    return {'candidate': destination / 'candidate.jsonl', 'manifest': manifest,
            'qualification': result}
