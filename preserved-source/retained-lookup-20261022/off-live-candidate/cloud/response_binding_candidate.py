"""Pure OFF-LIVE indexed envelope draft for soleUI/13 reconciliation.

Not a qualified output receipt or live source change. Native caller supplies
selected detail digest/generation; HTTP values cannot select them.
"""
import json


def compose_indexed_page(page, *, selected_detail_digest, selected_detail_generation,
                         store_result=None, detail_error=None):
    if not isinstance(page.get('rows'), list) or len(page['rows']) > 25:
        raise ValueError('identifier-page-required')
    out = dict(page)  # identifier rows, query generation and cursors unchanged
    details = {'detailDatabaseSha256': selected_detail_digest,
               'detailGenerationId': selected_detail_generation,
               'accepted': False}
    if detail_error is not None:
        if not isinstance(detail_error, dict) or not detail_error.get('reasonCode'):
            raise ValueError('typed-detail-error-required')
        details.update(state='unavailable', error=dict(detail_error),
                       sourceProducts=[], productDetailAvailability=[])
    else:
        r = store_result
        if (not isinstance(r, dict)
                or r.get('generationId') != selected_detail_generation
                or r.get('identifierDatabaseSha256') != page.get('databaseSha256')
                or not isinstance(r.get('sourceProducts'), list)
                or not isinstance(r.get('productDetailAvailability'), list)
                or not isinstance(r.get('coverage'), dict)):
            raise ValueError('selected-detail-response-binding')
        # No first-winner, field merge, row deduplication or availability rewrite.
        details.update(sourceProducts=r['sourceProducts'],
                       productDetailAvailability=r['productDetailAvailability'],
                       productDetailCoverage=r['coverage'],
                       inputManifestSha256=r['inputManifestSha256'],
                       operationSelectionSha256=r['operationSelectionSha256'])
        states = {a['state'] for a in r['productDetailAvailability']}
        details['state'] = ('ambiguous' if 'ambiguous' in states else
                            'partial' if 'loaded' in states and len(states) > 1 else
                            'loaded' if states == {'loaded'} else
                            'restricted' if states == {'restricted'} else 'not-loaded')
    out['details'] = details
    if len(json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode()) > 262144:
        # Keep known identifiers; never truncate fields or turn limits into miss.
        out['details'] = {'state': 'unavailable', 'error': {'reasonCode': 'DETAIL_RESPONSE_BOUND'},
                          'sourceProducts': [], 'productDetailAvailability': [],
                          'detailDatabaseSha256': selected_detail_digest,
                          'detailGenerationId': selected_detail_generation, 'accepted': False}
        if len(json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode()) > 262144:
            raise ValueError('identifier-response-bound')
    return out
