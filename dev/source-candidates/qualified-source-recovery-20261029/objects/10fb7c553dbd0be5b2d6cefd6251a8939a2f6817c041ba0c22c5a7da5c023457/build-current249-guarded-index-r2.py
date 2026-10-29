"""Incorporate the selected full249 + checked pendingC snapshot; metadata only."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from functools import lru_cache
import json
import hashlib
import datetime

ROOT = Path(__file__).resolve().parent
SRC = Path('/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57')
BASE = ROOT / 'reviewed-asset-registry-v3-guarded-cloud-wiring-r1.json'
VIEW = SRC / 'checked-pending-envelope-C/current249-source-type-index-after-pending-C.json'
RESIDUAL = SRC / 'current249-after-helper-merges/residual-manifest.json'
C_RESULT = SRC / 'checked-pending-envelope-C/result.json'


@lru_cache(None)
def pin(p):
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def save(name, value):
    p = ROOT / name
    data = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    if p.exists() and p.read_bytes() != data:
        raise ValueError('refuse changed immutable output: ' + name)
    p.write_bytes(data)
    return pin(p)


def main():
    assert pin(BASE)['sha256'] == 'b66fdc77ba82e27ed8788e240c6015bc2b7409180fa85c2bbadcbc26108bb3c7'
    assert pin(VIEW)['sha256'] == '031eaa49c3278486d5fb3b427821970a135fb88d8287264d8cc9d87916af47e8'
    assert pin(RESIDUAL)['sha256'] == 'f2265c72a23d8b3430f10815e2877eb2e76b4b55a25542796bd142c3bae58d65'
    assert pin(C_RESULT)['sha256'] == 'eee1020834f51d517c88312ca94f7a0a5790f30df72d8226cdb7d12f2b594c28'
    old = json.loads(BASE.read_text())
    r1 = ROOT / 'current249-guarded-registry-r1.json'
    r1_receipt = json.loads((ROOT / 'current249-rebase-result-r1.json').read_text())
    assert pin(r1) == r1_receipt['registry']
    registry = json.loads(r1.read_text())
    catalog = registry['assetCatalog']
    assets = {a['assetId']: a for a in catalog['assets']}
    original_assets = {a['assetId']: a for a in old['assetCatalog']['assets']}
    source = json.loads(VIEW.read_text())
    pending = json.loads(C_RESULT.read_text())
    identity_checks, additions, residuals = [], [], []
    for descriptor, item in source['sourceDescriptors'].items():
        key = 'file:' + descriptor
        if key in assets:
            local, integrity = assets[key]['localEvidence'] or {}, assets[key]['integrity'] or {}
            if local.get('declaredPath') != item['path'] or integrity.get('sha256') != item.get('sha256'):
                residuals.append({'assetId': key, 'reason': 'selected full249 current path/hash conflict; existing retained'})
                continue
            identity_checks.append(key)
        else:
            evidence = item.get('currentBoundedAcquisitionEvidence')
            if not isinstance(evidence, dict) or any(evidence.get(f) != item.get(f) for f in ('path', 'sha256', 'bytes', 'country')):
                residuals.append({'assetId': key, 'reason': 'no exact checked bounded original identity; metadata retained only in57view'})
                continue
            assert isinstance(item['sha256'], str) and len(item['sha256']) == 64
            assets[key] = {'assetId': key, 'kind': 'declared-source-object',
                'publisherCitation': None, 'request': {'url': evidence.get('sourceURL'), 'method': None, 'body': None},
                'release': evidence.get('release'), 'datatype': item.get('sourceRoleAsReported', evidence.get('category')),
                'format': None, 'destination': None,
                'integrity': {'sha256': item['sha256'], 'bytes': item['bytes'], 'qualification': 'Recorded exact bounded-original identity; no00payload read/stat/hash'},
                'budget': None, 'holds': ['Not selected for acquisition; all existing source-use/privacy/access/denial/ownership holds preserved', evidence.get('rightsAndCoverageHold')],
                'reuse': {'minimumDays': 30, 'originalAcquiredAt': evidence.get('originalAcquiredAt')},
                'purpose': 'Retain actual source object and scope, without semantic recipe/ingredient/type equivalence',
                'actualScope': {'country': item['country'], 'publisherScope': evidence.get('publisherScope'), 'countryComplete': False,
                    'qualification': evidence.get('typeCoverage', 'unqualified')},
                'localEvidence': {'declaredPath': item['path'], 'custodian': evidence.get('owner'),
                    'existenceState': 'held-locally-with-evidence', 'receipt': pin(VIEW),
                    'existenceQualification': '57-checked bounded owner original declaration; no new body verification'},
                'provenance': [pin(VIEW), evidence.get('sourceEvidence')], 'sourceKeys': [],
                'unresolved': ['Exact source-use/rights/access/privacy/denial/owner qualification', 'Country/type applicability and semantic coverage', 'Request/policy/budget/selection contract']}
            additions.append(key)
        asset = assets[key]
        local = deepcopy(asset['localEvidence'] or {})
        local['selectedCurrent249Evidence'] = {'source': pin(VIEW), 'selector': '/sourceDescriptors/' + descriptor,
            'qualification': 'Literal metadata source evidence; canonical kind/type/rights/clocks unchanged'}
        asset['localEvidence'] = local
    source_countries = {c['country']: c for c in source['countries']}
    for row in catalog['requirements']:
        evidence_row = next(v for v in source_countries[row['country']]['requirements'] if v['type'] == row['type'])
        row['evidence'] = pin(VIEW)
        # Retain every canonical type edge. Literal hints remain explicitly unaccepted.
        for binding in row['bindings']:
            binding['coverage']['current57LiteralHintEvidence'] = {
                'source': pin(VIEW), 'country': row['country'], 'type': row['type'],
                'hintState': evidence_row['sourcePresenceState'],
                'newTypeBindingAccepted': False, 'actualApplicableSourceCount': None}
    for p in (VIEW, RESIDUAL, C_RESULT):
        if pin(p) not in catalog['evidence']:
            catalog['evidence'].append(pin(p))
    catalog['assets'] = sorted(assets.values(), key=lambda a: a['assetId'])
    catalog['version'] = 'current249-selected57-pendingC-rebased-current00-r2'
    catalog['qualification'] = ('Current source-bound249country/3237canonical type-cell index.218 historical rows processed with residuals;287 bounded regional originals/1361612513B and3global originals are separate scoped source counts, not accepted food records. '
        'Existing canonical type edges/status/rights/clocks/holds preserved; literal57type hints unaccepted. Quarantined core/type proposals not applied; no new executable sources. SAME25 exact mapping delta review pending; country/type completeness remains unknown.')
    for key, asset in original_assets.items():
        for field in set(asset) - {'localEvidence'}:
            assert assets[key][field] == asset[field], (key, field)
    old_rows = {(r['country'], r['type']): r for r in old['assetCatalog']['requirements']}
    for row in catalog['requirements']:
        for field in ('assetIds', 'status', 'coverageQualification'):
            assert row[field] == old_rows[(row['country'], row['type'])][field]
    for field in ('sources', 'bindings', 'resources', 'evidence', 'schemaVersion'):
        assert registry[field] == old[field]
    registry_pin = save('current249-guarded-registry-r2.json', registry)
    country_status = []
    for country in source['countries']:
        rows = [r for r in catalog['requirements'] if r['country'] == country['country']]
        country_status.append({'country': country['country'], 'name': country['name'], 'deliveryOwner': country['deliveryOwner'],
            'sourcePresence': country['countryState'], 'wholeCountryOriginalCount': None, 'countryComplete': False,
            'recordedDescriptorReferences': len(country['sourceDescriptorIds']),
            'checkedBoundedOriginalReferences': len(country['checkedBoundedAcquisitionOriginalIds']),
            'typeHintCountsUnaccepted': dict(Counter(r['sourcePresenceState'] for r in country['requirements'])),
            'registryReferenceBindingStates': dict(Counter(b['state'] for r in rows for b in r['bindings'])),
            'typeCellCount': len(rows), 'metadataProcessing': country['metadataProcessing'],
            'nextAction': 'Reuse exact held originals; reconcile residual identity/scope/type/rights with original owners; prioritize genuine recipe/ingredient source gaps only when selected.'})
    compact = {'schemaVersion': 'offmenu-current249-usable-status/2', 'generatedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceSnapshotUTC': source['observedUTC'], 'sourceCut': source['sourceCut'], 'registry': registry_pin,
        'full57View': pin(VIEW), 'residualManifest': pin(RESIDUAL), 'checkedPendingC': pin(C_RESULT),
        'historicalRowsProcessed': 218, 'historicalRowsUnprocessed': 0, 'pendingFrozenEnvelopes': pending['pendingFrozenEnvelopesRemaining'],
        'boundedRegionalOriginals': 287, 'boundedRegionalBytes': 1361612513,
        'globalOriginalsSeparateNoCountryCredit': 3, 'globalOriginalBytes': 438917370,
        'sourceDescriptorCountNotCopies': len(source['sourceDescriptors']), 'registryAssetDescriptorCountNotCopies': len(assets),
        'countryPresenceAsReportedBy57': source['countryPresenceCounts'],
        'literalTypeHintsAsReportedUnaccepted': source['typeSourcePresenceCounts'],
        'literalTypeHintCountsQualification': source.get('typeSourcePresenceCountsQualification'),
        'countryCount': 249, 'typeCellCount': 3237, 'newTypeEdges': 0, 'newExecutableSources': 0,
        'parsedNormalizedMappedReviewedGoldAcceptedFoodRecords': 0, 'reviewState': 'SAME25 exact current00 mapping delta pending',
        'countries': country_status, 'sourceUseAdmission': False, 'countryComplete': False,
        'scope': 'Usable adoptedCLI metadata index; country source possession, literal type hints and canonical references are separate. No country/type acceptance; primary recipe/ingredient coverage not inflated by supporting references.'}
    compact_pin = save('current249-compact-status-r2.json', compact)
    delta = {'schemaVersion': 'offmenu-guarded-registry-delta/2', 'base': pin(BASE), 'result': registry_pin,
        'source57': pin(VIEW), 'r1RebaseReceipt': pin(ROOT / 'current249-rebase-result-r1.json'),
        'assetChanges': [{'assetId': k, 'before': original_assets.get(k), 'after': assets[k]} for k in sorted(assets) if original_assets.get(k) != assets[k]],
        'requirementChanges': [{'country': row['country'], 'type': row['type'], 'before': old_rows[(row['country'], row['type'])], 'after': row} for row in catalog['requirements']],
        'newTypeEdges': 0, 'newExecutableSources': 0, 'qualification': 'Exact before and after relative to currentb66 baseline. Local evidence, held-state and metadata hint changes are reviewable; tool code unchanged; no raw rows.'}
    delta_pin = save('current249-guarded-delta-r2.json', delta)
    result = {'status': 'DONE_WITH_CONCERNS_SUBSTANTIVE_MAPPING_REVIEW_PENDING', 'registry': registry_pin, 'compactStatus': compact_pin,
        'delta': delta_pin, 'source57': pin(VIEW), 'base': pin(BASE), 'identityChecksAgainstR1': len(identity_checks),
        'addedAfterR1': len(additions), 'newDescriptorsVsCurrentBaseline': len(assets)-len(original_assets),
        'heldStateChangesVsCurrentBaseline': r1_receipt['existingEdgeHeldStateChanges'],
        'helperObservationsJoined': r1_receipt['checkedHelperObservationsJoined'],
        'quarantinesNotApplied': r1_receipt['quarantinedCoreProposalsNotApplied'],
        'residuals': r1_receipt['residuals'] + residuals,
        'identityConflicts': r1_receipt['identityConflicts'],
        'correctionPackagesForGatewayOriginalHelpers': json.loads(RESIDUAL.read_text())['correctionPackages'],
        'sourceSnapshotPending': 59, 'noSourceRawBodyIO': True, 'newTypeEdges': 0, 'newExecutableSources': 0,
        'sourceRightsClocksOwnershipHoldsPreserved': True, 'countryComplete': False,
        'nextAction': 'Actual adoptedCLI validation, existing private versioned metadata transport, exact immutable delta toSAME25 throughGateway; no tooling re-review. Route exact correction packages/residuals tooriginalhelpers.'}
    print(json.dumps(save('current249-rebase-result-r2.json', result), indent=2))


if __name__ == '__main__':
    main()
