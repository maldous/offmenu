"""One bounded local metadata projection; no acquisition or canonical57 writes."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'reviewed-asset-registry-v3-r25-corrected.json'
BASE_SHA = 'cc83efedf959f4ad453dc7a93ca1afd24a8c71d4549b6c25a62b1bd150e29249'
HIST = ROOT / 'cloud-historical-339f4e38/historical-asset-bindings-patch.json'
NEW = ROOT / 'cloud-new-contracts-575d3caa/new-source-contracts-patch.json'
PINS = {BASE: BASE_SHA, HIST: '0d8324e0ebb3bcd2424a693978cc2f36255bd920ef866be913441f53144b3485',
        NEW: '23ecd6fd0bf3663795089190e3689df6c0369b2ebb5d66aab70d9fb2adc15c98'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    return {'path': str(path), 'sha256': sha(path.read_bytes())}


def save(name, obj):
    path = ROOT / name
    data = (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode()
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError('refuse overwrite of existing versioned receipt: ' + str(path))
    path.write_bytes(data)
    return pin(path)


def change_field(asset, change):
    """Exact before guard; request export is a subset of the full descriptor."""
    field = {'unresolvedReasons': 'unresolved'}.get(change['field'], change['field'])
    if field not in {'publisherCitation', 'format', 'unresolved', 'provenance', 'holds', 'request'}:
        raise ValueError('unsupported field: ' + field)
    before, after, current = change['before'], change['after'], asset[field]
    if field == 'request':
        if not isinstance(current, dict) or not isinstance(before, dict) or not isinstance(after, dict):
            return 'guard-conflict-current-preserved'
        if any(k not in current or current[k] != v for k, v in before.items()):
            return 'guard-conflict-current-preserved'
        # Do not overwrite any unrepresented current request field.
        delta = {k: v for k, v in after.items() if k not in before or before[k] != v}
        if any(k in current and current[k] != v for k, v in delta.items()):
            return 'guard-conflict-current-preserved'
        asset[field] = {**current, **deepcopy(delta)}
        return 'applied-export-subset-guard-additive-request-metadata'
    if current != before:
        return 'guard-conflict-current-preserved'
    if field in ('provenance', 'holds') and any(v not in after for v in current):
        raise ValueError('attempted removal from additive field')
    if field == 'unresolved' and (set(after) - set(current) or
                                 set(current) - set(after) - {'publisher-citation', 'format'}):
        raise ValueError('attempted source-use/custody hold removal')
    asset[field] = deepcopy(after)
    return 'applied-exact-before-guard'


def main():
    for path, expected in PINS.items():
        assert pin(path)['sha256'] == expected, str(path)
    base = json.loads(BASE.read_text())
    result = deepcopy(base)
    old = {a['assetId']: a for a in base['assetCatalog']['assets']}
    assets = {a['assetId']: a for a in result['assetCatalog']['assets']}
    history = json.loads(HIST.read_text())
    candidate = json.loads(NEW.read_text())
    dispositions = []
    for record in history['records']:
        asset = assets[record['assetId']]
        # All target IDs are retained; never apply an old positional export index.
        for change in record['fieldChanges']:
            status = change_field(asset, change)
            dispositions.append({'assetId': record['assetId'], 'field': change['field'],
                                 'disposition': status, 'beforeGuard': change['before'],
                                 'proposedAfter': change['after'],
                                 'currentAfter': deepcopy(asset[{'unresolvedReasons': 'unresolved'}.get(change['field'], change['field'])])})
    added, collisions = [], []
    for asset in candidate['assets']:
        assert not asset['sourceKeys'] and asset['destination'] is None and asset['holds'] and asset['unresolved']
        if asset['assetId'] in assets:
            collisions.append({'assetId': asset['assetId'], 'disposition': 'retained-current-descriptor-entirely; candidate unknown binding cannot replace current custody/holds',
                               'preservedLocalEvidence': deepcopy(assets[asset['assetId']]['localEvidence'])})
        else:
            assets[asset['assetId']] = deepcopy(asset)
            added.append(asset['assetId'])
    result['assetCatalog']['assets'] = sorted(assets.values(), key=lambda a: a['assetId'])
    result['assetCatalog']['version'] += '-guarded-historical-and-disabled-contract-metadata-r1'
    for path in (HIST, NEW):
        if pin(path) not in result['assetCatalog']['evidence']:
            result['assetCatalog']['evidence'].append(pin(path))
    result['assetCatalog']['qualification'] += (' Local versioned metadata projection of exact cc83 baseline: guarded historical metadata, disabled candidate descriptors only. '
        'Country edges and executable source selection unchanged; this historical baseline does not supersede newer57 reconciliation. '
        'No source-use/rights/custody/country completeness acceptance.')
    # Existing original identity, clocks, custody, scope, rights/holds and selections cannot regress.
    protected = ('integrity', 'reuse', 'localEvidence', 'actualScope', 'sourceKeys', 'destination', 'budget', 'release', 'datatype', 'kind', 'purpose')
    for key, asset in old.items():
        for field in protected:
            assert asset[field] == assets[key][field], (key, field)
        assert set(asset['holds']) <= set(assets[key]['holds'])
    for field in ('resources', 'sources', 'bindings', 'evidence'):
        assert result[field] == base[field], field
    assert result['assetCatalog']['requirements'] == base['assetCatalog']['requirements']
    assert len(added) == 38 and len(collisions) == 8
    # Negative guard checks: changed prior values cannot be overwritten.
    sample = next(c for r in history['records'] for c in r['fieldChanges'] if c['field'] == 'publisherCitation')
    negative = {'publisherCitation': {'newer': 'retained'}}
    assert change_field(negative, sample) == 'guard-conflict-current-preserved'
    assert negative == {'publisherCitation': {'newer': 'retained'}}
    request = next(c for r in history['records'] for c in r['fieldChanges'] if c['field'] == 'request')
    negative = {'request': {'url': 'https://example.invalid/newer'}}
    assert change_field(negative, request) == 'guard-conflict-current-preserved'
    assert negative == {'request': {'url': 'https://example.invalid/newer'}}
    output = save('reviewed-asset-registry-v3-guarded-cloud-wiring-r1.json', result)
    counts = Counter(d['disposition'] for d in dispositions)
    summary = {'status': 'DONE_WITH_CONCERNS_LOCAL_METADATA_WIRING',
               'worker': 0, 'inputs': [pin(p) for p in PINS], 'output': output,
               'historicalFieldDispositions': dispositions, 'fieldDispositionCounts': dict(counts),
               'historicalAssetIDsChanged': sum(old[k] != assets[k] for k in old),
               'addedDisabledCandidateIDs': added, 'currentIDCollisionsPreserved': collisions,
               'assetDescriptorsBefore': len(old), 'assetDescriptorsAfter': len(assets),
               'sourceSelectionUnchanged': True, 'countryRequirementEdgesUnchanged': True,
               'protectedOriginalFieldsUnchanged': list(protected), 'existingHoldsPreserved': True,
               'negativeGuardChecksPassed': 2, 'sourceRequests': 0, 'rawBodiesRead': 0,
               'parsedNormalizedGoldRows': 0, 'countryCompletionAsserted': False,
               'canonical57ReportUpdated': False,
               'nextAction': 'Qualify this pinned local metadata projection using adopted tooling; return exact conflicts/collisions to Gateway/57 for reconciliation against their newer report, without enabling sources or replacing canonical57 findings.'}
    receipt = save('guarded-registry-wiring-r1-result.json', summary)
    print(json.dumps({'receipt': receipt, 'output': output, 'historicalFieldCounts': dict(counts),
                      'changedHistoricalAssets': summary['historicalAssetIDsChanged'], 'addedDisabled': len(added),
                      'collisionsPreserved': len(collisions), 'descriptors': len(assets)}, indent=2))


if __name__ == '__main__':
    main()
