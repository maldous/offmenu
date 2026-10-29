"""Deterministic discovery/retained-format evidence, never executable admission.

The pinned inventories are metadata, not source payloads. Exact discovery IDs and
retained releases are the only joins; publisher domains and names are not rules.
"""
from copy import deepcopy
from . import coverage
from .capabilities import RELEASES

# Values describe reviewed local input contracts, not discovery endpoint formats.
FORMATS = {
    'afcd': ('national', 'three-xlsx-workbooks'),
    'mext': ('national', 'corrected-main-xlsx'),
    'cofid': ('national', 'cofid2021-xlsx'),
    'germany-bls': ('national', 'bls4-two-xlsx-workbooks'),
    'sweden-food': ('national', 'sweden20260701-xlsx-and-receipt'),
    'cnf': ('national', 'cnf2015-zip-and-twelve-extracted-csv'),
    'foodfiles': ('national', 'foodfiles2024-msi-and-reviewed-extracted-projection'),
    'off': ('product', 'products-gzip-jsonl'),
    'prices': ('product', 'prices-locations-proofs-gzip-jsonl'),
    'usda-files': ('product', 'relational-csv-zip'),
    'wikidata-food-businesses': ('reference', 'sparql-results-json'),
    'wikibooks': ('reference', 'wikibooks-revisions-json'),
    'foodon': ('reference', 'foodon-rdf-xml'),
    'qudt-measurement-definitions': ('reference', 'qudt-unit-turtle-blocks'),
    'overture-food-places': ('reference', 'overture-place-json-projection'),
}
# These three documents are present in the exact original 1,303-source ledger.
# They supply context only: no extra payload-family or compatible-release claim.
SUPPORT_DOCUMENTS = {
    'discovery:S045': ('overture-food-places', 'rights-document'),
    'discovery:S049': ('wikibooks', 'rights-document'),
    'src-24921f46d04f': ('usda-files', 'schema-document'),
}


def retained_adapters():
    """Return one descriptor per source release, never one adapter per country."""
    result = []
    for release in sorted(RELEASES, key=lambda r: r['sourceId']):
        source_id = release['sourceId']
        if source_id not in FORMATS:
            continue
        family, input_format = FORMATS[source_id]
        result.append({
            'sourceId': source_id, 'releaseId': release['releaseId'],
            'adapterFamily': family, 'inputFormat': input_format,
            'domains': list(release['domains']),
            'countryScopeEvidence': list(release['countries']),
            'discoveryIds': list(release['discoveryIds']),
            'historicalHandlerEvidence': deepcopy(release['handler']),
            'scope': release['scope'],
            'supportLevel': 'retained-input-candidate-only',
            'discoveryReleaseMatch': release['releaseMatch'],
            'productionAdmission': False, 'acceptedRecords': 0,
        })
    return result


def assess(matrix_path, ledger_path):
    """Assess exact inventory bytes, retaining every coverage blocker and hold.

This read-only report does not execute any adapter or certify current publisher
terms. A support document has no payload route, regardless of its HTTP status.
"""
    report = coverage.assess(matrix_path, ledger_path)
    ledger = coverage._read(ledger_path, 'ledger')
    return _annotate(report, ledger)


def _annotate(report, ledger):
    result = deepcopy(report)
    originals = {s['sourceId']: s for s in ledger['sources']}
    if not set(SUPPORT_DOCUMENTS) <= set(originals):
        raise coverage.CoverageError('support-document-discovery-reference-missing')
    adapters = {r['sourceId']: r for r in retained_adapters()}
    for row in result['sources']:
        historical = row['historicalCapability']
        family = historical['sourceId'] if historical else None
        role = 'source-family' if historical else None
        if row['sourceId'] in SUPPORT_DOCUMENTS:
            family, role = SUPPORT_DOCUMENTS[row['sourceId']]
        adapter = adapters.get(family)
        status = 'unsupported'
        if row['holds']:
            status = 'held'
        elif adapter and role != 'source-family':
            status = 'support-document-only'
        elif adapter and historical['releaseMatch'] == 'different-release':
            status = 'discovery-release-mismatch'
        elif adapter:
            status = 'retained-format-available-discovery-compatibility-unverified'
        source = originals[row['sourceId']]
        row['adapterMapping'] = {
            'sourceFamily': family, 'evidenceRole': role, 'status': status,
            'retainedAdapter': deepcopy(adapter),
            'discoveryEvidence': {'inventoryPin': deepcopy(coverage.PINS['ledger']),
                                  'sourceId': row['sourceId'],
                                  'url': source.get('url'),
                                  'researchReference': deepcopy(source.get('researchReference'))},
            'payloadRouteAuthorized': False, 'discoveryFormatCompatible': False,
            'countryAcceptanceGranted': False,
        }
    result['retainedAdapterCapabilities'] = list(adapters.values())
    result['adapterMappingPolicy'] = {
        'minimumRefreshSeconds': 30 * 86400,
        'refreshMode': 'explicit-reviewed-evidence-only', 'aiRefreshAllowed': False,
        'globalRoutesImplyCountryCoverage': False,
        'rightsInheritedFromDocuments': False,
        'executionAuthorized': False,
    }
    result['adapterMappingSummary'] = {
        'retainedCandidateAdapters': len(adapters),
        'supportOnlyDiscoveryLinks': sum(r['adapterMapping']['status'] == 'support-document-only' for r in result['sources']),
        'sourceFamilyDiscoveriesWithRetainedAdapter': sum(r['adapterMapping']['evidenceRole'] == 'source-family' and r['adapterMapping']['retainedAdapter'] is not None for r in result['sources']),
        'compatibleDiscoveryPayloadBindings': 0, 'productionAdmissions': 0,
        'acceptedRecords': 0, 'wholeCountryAcceptances': 0,
    }
    return result
