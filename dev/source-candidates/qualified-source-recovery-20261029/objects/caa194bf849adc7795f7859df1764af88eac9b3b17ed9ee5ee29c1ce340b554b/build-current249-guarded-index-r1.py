"""Bounded current249 metadata rebase; existing acquisition tooling is unchanged."""
from pathlib import Path
from copy import deepcopy
from collections import Counter, defaultdict
import hashlib
import json
import datetime

ROOT = Path(__file__).resolve().parent
SRC = Path('/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/checked-helper-merges')
BASE = ROOT / 'reviewed-asset-registry-v3-guarded-cloud-wiring-r1.json'
VIEW = SRC / 'country-row-view-after-D.json'
SUMMARY = SRC / 'seven-bundle-checked-merge-summary.json'
PINS = {BASE: 'b66fdc77ba82e27ed8788e240c6015bc2b7409180fa85c2bbadcbc26108bb3c7',
        VIEW: '4f319a53e231bf62e8fb9808b0aec1c9dc88ebad98ae2fe1b936de87e714442b',
        SUMMARY: '34c6d31fb459f06d096fad20c4814b2d2080fafd92a27bf952350b7952fad7c5'}


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save(name, obj):
    path = ROOT / name
    data = (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode()
    if path.exists() and path.read_bytes() != data:
        raise ValueError('immutable output already exists: ' + name)
    path.write_bytes(data)
    return pin(path)


def main():
    for p, expected in PINS.items():
        assert pin(p)['sha256'] == expected, str(p)
    before = json.loads(BASE.read_text())
    registry = deepcopy(before)
    source = json.loads(VIEW.read_text())
    catalog = registry['assetCatalog']
    assets = {a['assetId']: a for a in catalog['assets']}
    old_assets = {a['assetId']: a for a in before['assetCatalog']['assets']}
    old_rows = {(r['country'], r['type']): r for r in before['assetCatalog']['requirements']}
    source_rows = {(c['country'], r['type']): r for c in source['countries'] for r in c['requirements']}
    assert source_rows.keys() == old_rows.keys() and len(old_rows) == 3237
    residuals, findings, evidence_pins = [], [], [pin(VIEW), pin(SUMMARY)]
    quarantines = []
    for letter in 'CABFGEHD':
        name = 'bundle-C-checked-merge-result.json' if letter == 'C' else f'bundle-{letter}-checked-evidence-only-merge-result.json'
        p = SRC / name
        evidence_pins.append(pin(p))
        report = json.loads(p.read_text())
        scoped_residuals = report.get('scopeAndIdentityResiduals', report.get('identityResiduals', []))
        if isinstance(scoped_residuals, dict):
            scoped_residuals = [{'reportedResidualSummary': scoped_residuals}]
        residuals.extend({'bundle': letter, **r} for r in scoped_residuals)
        quarantines.extend({'bundle': letter, **q} for q in report.get('quarantinedCoreChanges', []))
        for index, item in enumerate(report.get('acceptedObservationFindings', report.get('evidenceFindings', []))):
            findings.append((letter, pin(p), index, item))
    excluded = {r.get('descriptorId') for r in residuals if r.get('descriptorId')}
    observed_findings, conflicts = [], []
    for letter, report_pin, index, item in findings:
        identity = item.get('identity', item)
        key = item.get('existingAssetId', item.get('canonicalIDAsProposed'))
        if key is None and item.get('descriptorId'):
            key = 'file:' + item['descriptorId']
        if key not in assets:
            conflicts.append({'bundle': letter, 'assetId': key, 'reason': 'unmatched-current-ID; retain reference only'})
            continue
        asset = assets[key]
        local, integrity = asset['localEvidence'] or {}, asset['integrity'] or {}
        item_sha = identity.get('sha256', identity.get('recordedSHA256'))
        if local.get('declaredPath') != identity.get('path') or integrity.get('sha256') != item_sha:
            conflicts.append({'bundle': letter, 'assetId': key, 'reason': 'current exact path/hash guard mismatch; no replacement'})
            continue
        if key.removeprefix('file:') in excluded:
            conflicts.append({'bundle': letter, 'assetId': key, 'reason': 'selector/country-scope residual; no typed enrichment'})
            continue
        local = deepcopy(local)
        observation = {'bundle': letter, 'source': report_pin,
                       'selector': ('/acceptedObservationFindings/' if letter == 'C' else '/evidenceFindings/') + str(index),
                       'recordedState': item.get('logicalSourcePresence', item.get('recordedPhysicalState')),
                       'qualification': 'Exact current ID/path/recorded hash joined to57-checked metadata; no new payload check, source-kind/type/rights admission or clock change.'}
        local.setdefault('checkedMetadataObservations', []).append(observation)
        asset['localEvidence'] = local
        observed_findings.append({'assetId': key, **observation})
    source_identity_matches, added = 0, []
    raw_roles = {'SOURCE_DATA_FILE', 'SOURCE_REFERENCE_DOCUMENT', 'SOURCE_NOTICE_OR_RECORD_PAGE', 'OWNER_EXPLICIT_FINITE_SOURCE_COPY'}
    held_pointers = defaultdict(list)
    for country in source['countries']:
        for pointer in country['countryAssetPointers']:
            descriptor = pointer['sourceDescriptorId']
            item = source['sourceFiles'][descriptor]
            if (pointer['localOriginalPointer'] != item['path'] or pointer['recordedSHA256'] != item.get('sha256')
                    or pointer['bytesDeclared'] != item.get('bytes')):
                conflicts.append({'assetId': 'file:' + descriptor, 'country': country['country'], 'reason': 'source57 pointer/sourceFiles identity disagreement'})
                continue
            if (pointer['existenceState'] == 'held-locally-with-evidence' and item['artifactRole'] in raw_roles
                    and descriptor not in excluded and item['country'] == country['country']):
                held_pointers['file:' + descriptor].append(pointer)
    for descriptor, item in source['sourceFiles'].items():
        key = 'file:' + descriptor
        if key in assets:
            local, integrity = assets[key]['localEvidence'] or {}, assets[key]['integrity'] or {}
            assert local.get('declaredPath') == item['path'] and integrity.get('sha256') == item.get('sha256'), key
            source_identity_matches += 1
        else:
            assert key not in old_assets and isinstance(item.get('sha256'), str) and len(item['sha256']) == 64
            assets[key] = {'assetId': key, 'kind': 'declared-source-object',
                'publisherCitation': None, 'request': {'url': item.get('url'), 'method': None, 'body': None},
                'release': item.get('release', item.get('version')), 'datatype': item['artifactRole'],
                'format': None, 'destination': None, 'integrity': {'sha256': item['sha256'], 'bytes': item.get('bytes'),
                    'qualification': 'Owner-recorded source-object extent/hash via exact57 metadata; no00rawbodycheck, not an independent food-record count'},
                'budget': None, 'holds': ['Not selected for acquisition; source-use/rights/privacy/access/claim holds remain', item.get('sourceUseAsReported', 'Current source use remains separately unqualified')],
                'reuse': {'minimumDays': 30, 'originalAcquiredAt': item.get('originalAcquiredAt')},
                'purpose': item.get('sourceScopeAsReported', item.get('coverage')),
                'actualScope': {'country': item['country'], 'sourceAssetKind': item.get('sourceAssetKind'), 'countryComplete': False,
                    'qualification': 'Retained source object only; no new type association or recipe/composition equivalence'},
                'localEvidence': {'declaredPath': item['path'], 'custodian': item.get('historicalSourceCustodian', item.get('recordedOwnerLabel')),
                    'reportingOwner': item.get('reportedByOwner')},
                'provenance': [pin(VIEW), item.get('sourceEvidence')], 'sourceKeys': [],
                'unresolved': ['source-use/rights/access/claim qualification', 'exact request/release/budget selection', 'country/type coverage; source object is not semantic food data']}
            added.append(key)
        # Physical possession is independent from kind/type. Preserve old clocks,
        # receipt pins, provenance, ownership, holds, and any existing stronger state.
        if held_pointers.get(key):
            local = deepcopy(assets[key]['localEvidence'] or {})
            if local.get('existenceState') not in (None, 'unknown-notyetfound', 'held-locally-with-evidence'):
                conflicts.append({'assetId': key, 'reason': 'current non-unknown state retained; possession proposal not applied'})
                continue
            local['existenceState'] = 'held-locally-with-evidence'
            local.setdefault('receipt', pin(VIEW))
            local.setdefault('existenceQualification', 'Exact57 sourceFiles/country-pointer identity with finite owner declaration; no00rawread/stat/hash; no source-use/type coverage admission')
            local['current57PointerEvidence'] = {'source': pin(VIEW), 'selector': '/sourceFiles/' + descriptor,
                'rightsAndUseQualification': held_pointers[key][0]['rightsAndUseQualification'],
                'coverageQualification': held_pointers[key][0]['coverageQualification']}
            assets[key]['localEvidence'] = local
    binding_changes = []
    for row in catalog['requirements']:
        # Evidence processing does not authorize rewriting canonical type IDs/status.
        latest = source_rows[(row['country'], row['type'])]
        if latest['status'] != row['status']:
            residuals.append({'country': row['country'], 'type': row['type'], 'reason': 'current status differs from57 proposal; current preserved',
                              'current': row['status'], 'proposed': latest['status']})
        row['evidence'] = pin(VIEW)
        for binding in row['bindings']:
            asset = assets.get(binding['assetId'])
            local = (asset or {}).get('localEvidence') or {}
            if local.get('existenceState') == 'held-locally-with-evidence' and binding['state'] == 'unknown-notyetfound':
                previous = deepcopy(binding)
                binding.update(state='held-locally-with-evidence', localPointer=local['declaredPath'], receipt=pin(VIEW),
                    nextAction='Reuse exact recorded held original; original custodian resolves missing provenance/rights/type coverage. No redownload from missing joins.')
                binding_changes.append({'country': row['country'], 'type': row['type'], 'assetId': binding['assetId'], 'before': previous, 'after': deepcopy(binding)})
    catalog['assets'] = sorted(assets.values(), key=lambda a: a['assetId'])
    for p in evidence_pins:
        if p not in catalog['evidence']:
            catalog['evidence'].append(p)
    catalog['version'] = 'current249-57-checked-eight-bundles-rebased-on-current00-r1'
    catalog['qualification'] = ('All249 country/type index,3237 canonical cells.218 legacy rows processed with identity/scope/type/rights residuals, not country acceptance. '
        'Exact existing ID/path/hash joins; new objects are metadata declarations only. Canonical type edges/status, source use, clocks, holds preserved. '
        'No quarantined G/H/E/D core/type proposals accepted, no new executable sources. SAME25 mapping review pending; all country-complete totals remain unknown.')
    for key, asset in old_assets.items():
        for field in set(asset) - {'localEvidence'}:
            assert assets[key][field] == asset[field], (key, field)
        for field, value in (asset['localEvidence'] or {}).items():
            if field == 'existenceState' and value == 'unknown-notyetfound':
                continue
            assert assets[key]['localEvidence'][field] == value, (key, field)
    for row in catalog['requirements']:
        old = old_rows[(row['country'], row['type'])]
        for field in set(row) - {'evidence', 'bindings'}:
            assert row[field] == old[field], (row['country'], row['type'], field)
    for field in ('sources', 'bindings', 'resources', 'evidence', 'schemaVersion'):
        assert registry[field] == before[field]
    registry_pin = save('current249-guarded-registry-r1.json', registry)
    country_status = []
    for country in source['countries']:
        rows = [r for r in catalog['requirements'] if r['country'] == country['country']]
        unmapped = []
        for p in country['unmappedHeldAssetPointers']:
            key = p['existingRegistryAssetId'] or 'file:' + p['sourceDescriptorId']
            unmapped.append({'assetId': key if key in assets else None, 'sourceDescriptorId': p['sourceDescriptorId'],
                             'state': p['existenceState'], 'typeAssociation': 'unmapped-no-type-inference'})
        country_status.append({'country': country['country'], 'name': country['name'], 'deliveryOwner': country['deliveryOwner'],
            'sourceReportState': country['status']['sourceCopyStatus'],
            'legacyEvidenceProcessing': country.get('legacyMetadataProcessingState', 'outside218-legacy-bundle-set; retained separately'),
            'canonicalTypeCells': len(rows), 'typeCellStates': dict(Counter(b['state'] for r in rows for b in r['bindings'])),
            'recordedSourceDescriptors': country['sourceDescriptorCount'], 'countryComplete': False, 'completeLocalCopyTotal': None,
            'unmappedHeldSourceReferences': unmapped, 'recipeIngredientPriority': 'Prioritize genuine recipe/ingredient originals at next selected source; price/health/provider references remain distinct',
            'nextAction': country['nextAction']})
    compact = {'schemaVersion': 'offmenu-current249-status/1', 'generatedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'registry': registry_pin, 'source57': pin(VIEW), 'sourceViewFrozenAtUTC': source['frozenAtUTC'],
        'legacyRowsProcessed': 218, 'legacyRowsUnprocessed': source['oldRowsNotYetProcessed'],
        'countries': country_status, 'countryCount': len(country_status), 'canonicalTypeCells': len(catalog['requirements']),
        'bindingStates': dict(Counter(b['state'] for r in catalog['requirements'] for b in r['bindings'])),
        'newTypeEdges': 0, 'newExecutableSources': 0, 'countryComplete': False, 'review': 'SAME25 exact mapping delta pending via Gateway',
        'qualification': catalog['qualification']}
    compact_pin = save('current249-compact-status-r1.json', compact)
    delta = {'schemaVersion': 'offmenu-guarded-registry-delta/1', 'base': pin(BASE), 'result': registry_pin,
        'assetChanges': [{'assetId': k, 'before': old_assets.get(k), 'after': assets[k]} for k in sorted(assets) if old_assets.get(k) != assets[k]],
        'requirementChanges': [{'country': r['country'], 'type': r['type'], 'before': old_rows[(r['country'], r['type'])], 'after': r}
                               for r in catalog['requirements'] if r != old_rows[(r['country'], r['type'])]],
        'newAssetIDs': added, 'bindingStateChanges': binding_changes,
        'quarantinedCoreProposalsNotApplied': quarantines, 'residuals': residuals, 'identityConflicts': conflicts,
        'qualification': 'Full exact before/after metadata; no raw payload rows. Substantive held-state changes require25independent review viaGateway, unchanged tooling already accepted.'}
    delta_pin = save('current249-guarded-delta-r1.json', delta)
    result = {'status': 'DONE_WITH_CONCERNS_MAPPING_REVIEW_PENDING', 'base': pin(BASE), 'source57': pin(VIEW),
        'registry': registry_pin, 'compactStatus': compact_pin, 'delta': delta_pin,
        'sourceIdentityMatches': source_identity_matches, 'newDisabledAssetDescriptors': len(added),
        'assetsBefore': len(old_assets), 'assetsAfter': len(assets), 'checkedHelperObservationsJoined': len(observed_findings),
        'existingEdgeHeldStateChanges': len(binding_changes), 'newTypeEdges': 0,
        'newExecutableSources': 0, 'quarantinedCoreProposalsNotApplied': len(quarantines),
        'residuals': residuals, 'identityConflicts': conflicts, 'rawBodyStatHashNetwork': 0,
        'parsedNormalizedGoldRows': 0, 'countryComplete': False,
        'nextAction': 'Validate adopted CLI against exact registry, publish versioned metadata through existing private transport, Gateway routes immutable substantive mapping delta toSAME25 and exact residuals tooriginalhelpers.'}
    print(json.dumps(save('current249-rebase-result-r1.json', result), indent=2))


if __name__ == '__main__':
    main()
