"""Two selected metadata corrections only; no source, runtime or later-cut IO."""
from pathlib import Path
from functools import lru_cache
from copy import deepcopy
import json
import hashlib
import datetime

ROOT = Path(__file__).resolve().parent
REVIEW = Path('/home/user/.codex/visualizations/2026/10/14/01a138fe-af42-7ff1-8e37-f7ad5abf2671/M-CURRENT249-R5-METADATA-REVIEW-20261018-W25')


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


@lru_cache(None)
def document(path, sha):
    p = Path(path)
    assert p.suffix == '.json' and pin(p)['sha256'] == sha
    return json.loads(p.read_text())


def dereference(record, pointer):
    assert pointer.startswith('/')
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        record = record[int(token)] if isinstance(record, list) else record[token]
    return record


def identity(record):
    value = record.get('original', record.get('identity', record.get('actualOriginalPointer', record)))
    if not isinstance(value, dict):
        value = {'path': value}
    return {'path': value.get('path', record.get('actualOriginalPointer')),
            'sha256': value.get('sha256', record.get('recordedSHA256', record.get('sha256'))),
            'bytes': value.get('bytes', record.get('wholeOriginalBytes', record.get('bytes'))),
            'country': record.get('country', record.get('countryOrExplicitUnknown', (record.get('contract') or {}).get('country')))}


def save(name, value):
    path = ROOT / name
    data = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    if path.exists():
        assert path.read_bytes() == data, 'refuse changed immutable output'
    else:
        path.write_bytes(data)
    return pin(path)


def main():
    receipt = REVIEW / 'review-receipt.json'
    affected_path = REVIEW / 'finding-affected-identities.json'
    original_path = ROOT / 'current249-guarded-registry-r5.json'
    assert pin(receipt)['sha256'] == '8331ac123be6bd0e8e66293a5389f29834259dbbd8166536a40a2d43e8826210'
    assert pin(affected_path)['sha256'] == '596702a12cc05beace8a08e3041f7633a137ec6817a66536231cb044927f820d'
    assert pin(original_path)['sha256'] == 'd469b477ce83a4464bc38bd5601843a31a2cce85a8e289b2e0379faac33c925e'
    original = json.loads(original_path.read_text())
    result = deepcopy(original)
    before = {a['assetId']: a for a in original['assetCatalog']['assets']}
    assets = {a['assetId']: a for a in result['assetCatalog']['assets']}
    affected = json.loads(affected_path.read_text())
    selector_checks, release_checks = [], []
    for finding in affected['W00-R25-R5-P2-001']:
        key = finding['assetId']
        asset = assets[key]
        local = asset['localEvidence']
        source = local['receipt']
        assert source == finding['source'] and local['sourceSelector'] == finding['selector']
        aggregate = document(source['path'], source['sha256'])
        expected = {'path': local['declaredPath'], 'sha256': asset['integrity']['sha256'],
                    'bytes': asset['integrity']['bytes'], 'country': asset['actualScope']['country']}
        if 'sourceDescriptors' in aggregate:
            new_selector = '/sourceDescriptors/' + key.removeprefix('file:')
        else:
            matches = [i for i, row in enumerate(aggregate['checkedAdditionalOriginals32']) if identity(row) == expected]
            assert len(matches) == 1, key
            new_selector = '/checkedAdditionalOriginals32/' + str(matches[0])
        row = dereference(aggregate, new_selector)
        assert identity(row) == expected, key
        # Keep the original helper's locator paired with its actual helper pin.
        helper_pin, helper_selector = row['sourceEvidence'], local['sourceSelector']
        helper_row = dereference(document(helper_pin['path'], helper_pin['sha256']), helper_selector)
        assert identity(helper_row) == expected, ('original-helper', key)
        local['sourceSelector'] = new_selector
        local['originalHelperLocator'] = {'source': deepcopy(helper_pin), 'selector': helper_selector,
                                          'qualification': 'Exact same-document original helper locator retained; identity checked, no new source-body verification'}
        selector_checks.append({'assetId': key, 'receipt': deepcopy(source), 'selector': new_selector,
                                'identity': expected, 'originalHelperLocator': deepcopy(local['originalHelperLocator']),
                                'aggregateIdentityDereferenced': True, 'originalHelperIdentityDereferenced': True})
    assert len(selector_checks) == 144
    for finding in affected['W00-R25-R5-P2-002']:
        asset = assets[finding['assetId']]
        assert asset['release'] is None
        source = finding['source']
        literal = dereference(document(source['path'], source['sha256']), finding['sourceJSONPointer'])
        assert literal == finding['sourceLiteralValue'] and literal is not None
        assert asset['localEvidence']['declaredPath'] == finding['actualPointer']
        assert asset['integrity']['sha256'] == finding['recordedSHA256']
        asset['release'] = deepcopy(literal)
        asset['localEvidence']['releaseLiteralEvidence'] = {'source': deepcopy(source), 'selector': finding['sourceJSONPointer'],
            'qualification': 'Exact source-reported literal release/period retained; not publisher currentness, policy, type, rights or source-use acceptance'}
        release_checks.append({'assetId': asset['assetId'], 'source': deepcopy(source), 'selector': finding['sourceJSONPointer'],
                               'literalValue': literal, 'valueEqualsPinnedSource': True})
    assert len(release_checks) == 27
    selector_ids = {r['assetId'] for r in selector_checks}
    release_ids = {r['assetId'] for r in release_checks}
    field_changes = []
    for key, old in before.items():
        new = assets[key]
        for field in set(old) - {'localEvidence', 'release'}:
            assert old[field] == new[field], (key, field)
        assert key in release_ids or old['release'] == new['release']
        old_local = deepcopy(old['localEvidence'])
        new_local = deepcopy(new['localEvidence'])
        if key in selector_ids:
            assert new_local.pop('sourceSelector') != old_local.pop('sourceSelector')
            new_local.pop('originalHelperLocator')
        if key in release_ids:
            new_local.pop('releaseLiteralEvidence')
        assert old_local == new_local, key
        if new != old:
            field_changes.append({'assetId': key, 'before': old, 'after': new})
    assert len(field_changes) == 144 and release_ids <= selector_ids
    for field in set(original) - {'assetCatalog'}:
        assert result[field] == original[field]
    for field in set(original['assetCatalog']) - {'assets'}:
        assert result['assetCatalog'][field] == original['assetCatalog'][field]
    # No version-label or qualification rewrite: this successor changes exactly
    # the two selected findings, including no country/type/binding/core changes.
    result_pin = save('current249-guarded-registry-r6-two-P2-corrected.json', result)
    negative_guards = []
    for check in selector_checks:
        doc = document(check['receipt']['path'], check['receipt']['sha256'])
        assert identity(dereference(doc, check['selector'])) == check['identity']
        bad = dict(check['identity'], sha256='0' * 64)
        assert identity(dereference(doc, check['selector'])) != bad
        negative_guards.append(check['assetId'])
    delta = {'schemaVersion': 'offmenu-current249-two-P2-delta/1', 'base': pin(original_path), 'result': result_pin,
             'review': pin(receipt), 'affected': pin(affected_path), 'assetChanges': field_changes,
             'unchangedOutsideAssetLocalEvidenceAnd27ReleaseFields': True,
             'newAssets': 0, 'typeEdgeChanges': 0, 'sourceSelectionChanges': 0, 'laterIngressRepins': 0}
    delta_pin = save('current249-r5-to-r6-two-P2-delta.json', delta)
    # Reconstruct exact successor bytes from guarded144before/after records.
    rebuilt = deepcopy(original)
    positions = {a['assetId']: i for i, a in enumerate(rebuilt['assetCatalog']['assets'])}
    for change in field_changes:
        i = positions[change['assetId']]
        assert rebuilt['assetCatalog']['assets'][i] == change['before']
        rebuilt['assetCatalog']['assets'][i] = change['after']
    assert (json.dumps(rebuilt, indent=2, ensure_ascii=False) + '\n').encode() == Path(result_pin['path']).read_bytes()
    validation = {'status': 'AUTHOR_SCOPED_PASS_TWO_P2_CORRECTIONS_REVIEW_PENDING',
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base': pin(original_path), 'result': result_pin, 'delta': delta_pin,
        'review': pin(receipt), 'selectorPairsChecked': selector_checks, 'releaseValuesChecked': release_checks,
        'aggregateSelectorIdentityChecksPassed': 144, 'originalHelperSelectorIdentityChecksPassed': 144,
        'wrongIdentityNegativeChecksPassed': len(negative_guards), 'releaseLiteralEqualityChecksPassed': 27,
        'genuinelyMissingReleasesUnchanged': True, 'exactGuardedDeltaReconstructsResult': True,
        'countryTypeBindingsSourceRightsClocksCoreUnchanged': True, 'rawBodyStatHashNetwork': 0,
        'laterIngressRepins': 0, 'frozenR5UnchangedAndReviewFailed': True,
        'nextAction': 'Adopted CLI qualification then return exact immutable successor/delta to Gateway for SAME25 scoped metadata rereview; no private reference adoption claim before pass/selection.'}
    validation_pin = save('current249-r6-two-P2-author-validation.json', validation)
    print(json.dumps({'registry': result_pin, 'delta': delta_pin, 'validation': validation_pin,
                      'selectorPairs': 144, 'originalHelperPairs': 144, 'literalReleaseValues': 27}, indent=2))


if __name__ == '__main__':
    main()
