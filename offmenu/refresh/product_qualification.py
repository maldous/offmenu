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
                              attribution, limits=ProductLimits()):
    """Verify full retained bundle before parsing, then qualify exact candidate.

    roles maps parser roles to contract-relative asset paths (not evidence roles).
    The original normalization manifest is immutable. A separate evidence-inclusive
    qualification-manifest.json records the exact independently reviewed bundle.
    Returns qualification diagnostics without promoting native/curated/common state.
    """
    from .acceptance import qualify
    from .national_tabular import bundle_files, valid_input_name
    limits.validate()
    if contract.holds:
        raise RefreshError('product-source-held')
    if (not {'retain', 'parse', 'transform'} <= set(contract.required_operations)
            or not set(contract.required_operations) <= set(contract.permitted_operations)):
        raise RefreshError('product-operation-rights-missing')
    if contract.output_scope != 'native' or contract.output_visibility != 'private':
        raise RefreshError('product-native-contract-required')
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
    if bundle_files(root, assets) != set(assets):
        raise RefreshError('product-bundle-set-mismatch')
    for path, asset in assets.items():
        source = _safe(root / path)
        if source.stat().st_size != asset.bytes or _hash(source) != asset.sha256:
            raise RefreshError('product-input-pin-mismatch')
    if (len(set(roles.values())) != len(roles) or not set(roles.values()) <= set(assets)
            or {contract.rights_evidence.path, contract.scope_evidence.path} & set(roles.values())):
        raise RefreshError('product-invalid-role-map')
    # Every non-evidence asset must have an explicit parser role, no scope drift.
    if set(roles.values()) != set(assets) - {contract.rights_evidence.path, contract.scope_evidence.path}:
        raise RefreshError('product-unassigned-input')
    context = ProductContext(contract.source_id, contract.release_id, contract.acquired_at,
                             license, attribution, contract.rights_evidence.sha256,
                             contract.scope_evidence.sha256)
    destination = _safe(destination)
    if destination == root or root in destination.parents or destination in root.parents:
        raise RefreshError('product-output-overlaps-bundle')
    original = normalize_products(context, {role: root / path for role, path in roles.items()},
                                  destination, limits=limits)
    manifest = {**original, 'inputFiles': [asdict(a) for a in sorted(contract.inputs, key=lambda a: a.path)],
                'normalizationManifestSha256': _hash(destination / 'manifest.json'),
                'inputRoleMap': dict(roles)}
    # Qualification rechecks original/evidence pins after parsing to catch mutation.
    result = qualify(contract, root, destination / 'candidate.jsonl', manifest)
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
