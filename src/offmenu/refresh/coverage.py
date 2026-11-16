"""Metadata-only reconciliation of the frozen global inventory retained in private local storage.

This module never downloads, parses a dataset, invokes an adapter or grants rights.
The two large inventories are deliberately not packaged or copied into GitHub.
"""
import copy
import hashlib
import json
from pathlib import Path
from .capabilities import RELEASES, MAPPING_EVIDENCE, BASELINE_COMMIT, SUPPORTING_HANDLERS

COUNTRIES = tuple('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split())
DOMAINS = ('barcodes_products', 'food_composition', 'food_identity', 'recipes',
           'menus_venues', 'retailers_prices', 'companies_ownership',
           'origin_supply_chain', 'diet_certification', 'recalls_regulation',
           'baskets', 'health_integrations', 'locale_accessibility')
PINS = {
    'matrix': {'bytes': 133210, 'sha256': '894e05f09744c76b790f8e5f159141bed6c308a9af3d90c3c82aa79105cf5ea8'},
    'ledger': {'bytes': 1701843, 'sha256': '2f3c917a6463153824b8c807b41707870e7f763c65b5ff7957ec4988cd96bfcf'},
}
# Exact discovery identifiers; these are restrictions, never execution routes.
HOLDS = {
    'discovery:S357': ['fineli-force-download-prohibited', 'fineli-zero-interpretation-held'],
    'discovery:S060': ['france-native-replay-crash-restriction'],
    'discovery:S061': ['norway-native-replay-crash-restriction'],
    'discovery:S087': ['frida-four-definition-basis-and-curation-boundary'],
}


class CoverageError(ValueError):
    """Inventory is absent, altered, malformed or internally inconsistent."""


def _read(path, kind):
    path = Path(path)
    # Reject symlink components, not merely the final path.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CoverageError(f'{kind}-inventory-symlink')
    try:
        with path.open('rb') as stream:
            body = stream.read(PINS[kind]['bytes'] + 1)
    except OSError as error:
        raise CoverageError(f'{kind}-inventory-unavailable') from error
    observed = {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    if observed != PINS[kind]:
        raise CoverageError(f'{kind}-inventory-pin-mismatch')
    try:
        return json.loads(body)
    except (UnicodeError, ValueError) as error:
        raise CoverageError(f'{kind}-inventory-invalid-json') from error


def assess(matrix_path, ledger_path):
    """Load exact retained inventory pins and return exhaustive discovery coverage.

Missing inventory is a blocker, never substituted with generated source URLs.
Result is deterministic, contains no raw payload, and is intended to stay in private local storage.
Global routes are listed separately: they do not establish every country's scope.
"""
    return _reconcile(_read(matrix_path, 'matrix'), _read(ledger_path, 'ledger'))


def _reconcile(matrix, ledger):
    countries = matrix.get('countries', [])
    sources = ledger.get('sources', [])
    codes = [c['iso2'] for c in countries]
    ids = [s['sourceId'] for s in sources]
    if len(codes) != 249 or set(codes) != set(COUNTRIES):
        raise CoverageError('country-set-mismatch')
    if set(matrix.get('domainDefaults', {})) != set(DOMAINS):
        raise CoverageError('required-domain-set-mismatch')
    if len(ids) != 1303 or len(set(ids)) != 1303 or ledger.get('sourceCount') != 1303:
        raise CoverageError('source-set-mismatch')
    known = set(ids)
    global_ids = sorted(set(matrix.get('globalSourceIds', [])))
    if not set(global_ids) <= known:
        raise CoverageError('unresolved-global-source')
    associations = {sid: set() for sid in ids}
    bindings = {sid: release for release in RELEASES for sid in release['discoveryIds']}
    if not set(bindings) <= known:
        raise CoverageError('capability-discovery-reference-missing')
    country_rows = []
    for country in sorted(countries, key=lambda c: c['iso2']):
        linked = sorted(set(country.get('sourceIds', [])))
        if not set(linked) <= known:
            raise CoverageError('unresolved-country-source')
        for sid in linked:
            associations[sid].add(country['iso2'])
        domain_rows = {}
        for domain in DOMAINS:
            mapped = [sid for sid in linked if sid in bindings
                      and domain in bindings[sid]['domains']
                      and country['iso2'] in bindings[sid]['countries']]
            domain_rows[domain] = {
                'status': 'unassessed', 'sourceIds': mapped,
                'mappingEvidenceOnly': bool(mapped),
                'blockers': ['payload-cache-and-rights-evidence-missing'] if mapped else
                            ['reviewed-source-domain-scope-mapping-missing']}
        country_rows.append({
            'iso2': country['iso2'], 'sourceIds': linked,
            'globalSourceIds': global_ids.copy(),
            'specialProvisioning': bool(country.get('specialProvisioning')),
            'domains': domain_rows,
            'countryCoverageComplete': False,
        })
    rows = []
    for source in sorted(sources, key=lambda s: s['sourceId']):
        sid = source['sourceId']
        evidence = source.get('accessEvidence', {})
        holds = HOLDS.get(sid, [])
        binding = bindings.get(sid)
        handler = binding and binding['handler']
        compatible = binding and binding['releaseMatch'] != 'different-release'
        blockers = ['payload-cache-and-rights-evidence-missing', 'reviewed-executable-binding-missing']
        if not binding:
            blockers += ['reviewed-release-and-handler-binding-missing', 'source-domain-scope-mapping-missing']
        elif not compatible:
            blockers += ['discovery-release-differs-from-retained-handler-release']
        elif not handler:
            blockers += ['historical-collector-unresolved']
        rows.append({
            'sourceId': sid, 'countries': sorted(associations[sid]),
            'declaredCountries': sorted(source.get('countries', [])),
            'globalRoute': sid in global_ids, 'domains': list(binding['domains']) if binding else [],
            'status': 'held' if holds else 'historical_handler_mapped' if handler else 'discovery_only',
            'normalizationStatus': 'held' if holds else 'legacy_handler_available' if handler and compatible else 'unsupported',
            'handlerBinding': None, 'historicalCapability': binding, 'holds': list(holds),
            'rightsStatus': 'unassessed', 'cacheStatus': 'unassessed',
            'cacheAgeSeconds': None, 'downloadReused': None,
            'normalizationResult': 'not-run', 'errors': [],
            'blockers': blockers,
            'historicalLandingEvidence': {
                'checkedAt': evidence.get('checkedAt'),
                'httpStatus': evidence.get('httpStatus'),
                'downloadCandidateCount': len(evidence.get('downloadCandidates', [])),
                'rightsLinkCount': len(evidence.get('rightsLinks', [])),
                'payloadVerified': False,
            },
        })
    return copy.deepcopy({
        'schemaVersion': 'offmenu-global-discovery-coverage/1',
        'inventoryPins': PINS, 'domainNames': list(DOMAINS),
        'capabilityEvidence': {'commit': BASELINE_COMMIT, **MAPPING_EVIDENCE},
        'retainedReleases': list(RELEASES),
        'supportingHandlers': list(SUPPORTING_HANDLERS),
        'countries': country_rows, 'sources': rows,
        'summary': {
            'countries': 249, 'requiredCountryDomainCells': 249 * len(DOMAINS),
            'registeredDiscoverySources': len(rows),
            'historicalHttp200': sum(r['historicalLandingEvidence']['httpStatus'] == 200 for r in rows),
            'sourcesWithDownloadCandidates': sum(r['historicalLandingEvidence']['downloadCandidateCount'] > 0 for r in rows),
            'sourcesWithRightsLinks': sum(r['historicalLandingEvidence']['rightsLinkCount'] > 0 for r in rows),
            'heldSources': sum(r['status'] == 'held' for r in rows),
            'unboundSources': len(rows),
            'sourceFamilyMappings': len(bindings),
            'sourcesWithHistoricalHandlers': sum(bool(r['historicalCapability'] and r['historicalCapability']['handler']) for r in rows),
            'sourcesWithoutHistoricalHandlers': sum(not(r['historicalCapability'] and r['historicalCapability']['handler']) for r in rows),
            'retainedReleasesWithHandlers': sum(bool(r['handler']) for r in RELEASES),
            'wholeCountryAcceptances': 0,
            'retainedReleaseClaims': ledger.get('developmentExpansion', {}).get('mappedCollectionCount'),
            'retainedReleasePayloadsReverified': False,
        },
        'countryCoverageComplete': False, 'payloadsRead': False,
        'executionAuthorized': False, 'networkRequests': 0,
        'globalRestrictions': ['production-paused', 'cix-paused'],
    })
