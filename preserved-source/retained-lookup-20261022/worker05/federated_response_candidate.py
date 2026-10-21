"""OFF-LIVE contract44ec federation branch; native c860 composer unchanged."""
import json
import re

BACKEND = 'retained-product-federation-v1'
CAP = 262144
STORE_KEYS = {'role', 'databaseSha256', 'loadReceiptSha256', 'qualificationSha256'}


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def store_pins(values):
    if not isinstance(values, (list, tuple)) or len(values) > 3:
        raise ValueError('federation-backing-pins')
    if any(type(v) is not dict or set(v) != STORE_KEYS for v in values):
        raise ValueError('federation-backing-pins')
    roles = [v['role'] for v in values]
    if len(set(roles)) != len(roles) or set(roles) - {'off-subset', 'usda-products', 'usda-profiles'}:
        raise ValueError('federation-backing-roles')
    if ('usda-products' in roles) != ('usda-profiles' in roles):
        raise ValueError('federation-usda-pair-required')
    return sorted(values, key=lambda v: v['role'])


def compose_federated_page(page, *, selected_generation, selected_manifest_sha256,
                           selected_operation_sha256, selected_backing_stores, selected_coverage,
                           result=None, detail_error=None):
    """All selected_* values are independently qualified native configuration.

    selected_coverage comes from the same qualified selection/coverage receipts.
    No paths, native handles, rights contents or manifest body go to HTTP.
    """
    if not isinstance(page.get('rows'), list) or len(page['rows']) > 25:
        raise ValueError('identifier-page-required')
    pins = store_pins(selected_backing_stores)
    identity = {'detailDatabaseSha256': None, 'detailBackend': BACKEND,
                'detailSelectionSha256': selected_manifest_sha256,
                'detailGenerationId': selected_generation, 'accepted': False}
    details = dict(identity, detailBackingStores=pins)
    if detail_error is not None:
        # Caller maps source failures to fixed safe codes before this boundary.
        if type(detail_error) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', detail_error):
            raise ValueError('fixed-safe-detail-error-required')
        details.update(state='unavailable', error={'reasonCode': detail_error},
                       sourceProducts=[], productDetailAvailability=[])
    else:
        r = result
        if (type(r) is not dict or r.get('backend') != BACKEND
                or r.get('generationId') != selected_generation
                or r.get('selectionManifestSha256') != selected_manifest_sha256
                or r.get('inputManifestSha256') != selected_manifest_sha256
                or r.get('operationSelectionSha256') != selected_operation_sha256
                or r.get('identifierDatabaseSha256') != page.get('databaseSha256')
                or store_pins(r.get('backingStores')) != pins
                or r.get('coverage') != selected_coverage
                or r.get('accepted') is not False):
            raise ValueError('federation-selected-response-binding')
        c = r['coverage']
        if (c.get('complete') is not False
                or c.get('coverageMode') != 'federated-source-retention'
                or c.get('identifierIndexCoverageSeparate') is not True
                or any(c.get(k, 'absent') is not None for k in
                       ('expectedAssets', 'processedAssets', 'products', 'profiles'))
                or not isinstance(r.get('sourceProducts'), list)
                or not isinstance(r.get('productDetailAvailability'), list)):
            raise ValueError('federation-coverage-or-envelope')
        details.update(sourceProducts=r['sourceProducts'],
                       productDetailAvailability=r['productDetailAvailability'],
                       productDetailCoverage=c,
                       inputManifestSha256=r['inputManifestSha256'],
                       operationSelectionSha256=r['operationSelectionSha256'])
        states = {a['state'] for a in r['productDetailAvailability']}
        details['state'] = ('ambiguous' if 'ambiguous' in states else
                            'partial' if 'loaded' in states and len(states) > 1 else
                            'loaded' if states == {'loaded'} else
                            'restricted' if 'restricted' in states else 'not-loaded')
    out = dict(page, details=details)
    if len(wire(out)) > CAP:
        out['details'] = dict(identity, state='unavailable',
                              error={'reasonCode': 'DETAIL_RESPONSE_BOUND'},
                              sourceProducts=[], productDetailAvailability=[])
        if len(wire(out)) > CAP:
            raise ValueError('identifier-response-bound')
    return out
