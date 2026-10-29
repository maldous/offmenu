"""Resolve selected pendingC's alternate typed metadata schema without body IO."""
from pathlib import Path
from copy import deepcopy
from functools import lru_cache
import json
import hashlib
import datetime

ROOT = Path(__file__).resolve().parent
SRC = Path('/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/checked-pending-envelope-C')


@lru_cache(None)
def pin(p):
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


@lru_cache(None)
def metadata(path, expected):
    p = Path(path)
    assert p.suffix == '.json' and pin(p)['sha256'] == expected
    return json.loads(p.read_text())


def resolve(obj, selector):
    for token in selector.lstrip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        obj = obj[int(token)] if isinstance(obj, list) else obj[token]
    return obj


def save(name, obj):
    p = ROOT / name
    b = (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode()
    if p.exists() and p.read_bytes() != b:
        raise ValueError('immutable output exists: ' + name)
    p.write_bytes(b)
    return pin(p)


def main():
    holding = SRC / 'consumed-bounded-originals-287.json'
    assert pin(holding)['sha256'] == 'd835bdede5a85d9a39f44ac35ad748e876a14622026dc9f475f3a5646d5e3c7c'
    items = json.loads(holding.read_text())['checkedAdditionalOriginals32']
    assert len(items) == 32
    previous = json.loads((ROOT / 'current249-rebase-result-r2.json').read_text())
    p2 = Path(previous['registry']['path'])
    assert pin(p2) == previous['registry']
    registry = json.loads(p2.read_text())
    catalog = registry['assetCatalog']
    assets = {a['assetId']: a for a in catalog['assets']}
    selected = metadata(previous['source57']['path'], previous['source57']['sha256'])
    eligible_identities = [(k, v) for k, v in selected['sourceDescriptors'].items() if all(f in v for f in ('path', 'sha256', 'bytes', 'country'))]
    identity_map = {(v['path'], v['sha256'], v['bytes'], v['country']): k for k, v in eligible_identities}
    assert len(identity_map) == len(eligible_identities)
    checks, added = 0, []
    for item in items:
        descriptor = identity_map[(item['path'], item['sha256'], item['bytes'], item['country'])]
        key = 'file:' + descriptor
        assert key not in assets, key
        matched = selected['sourceDescriptors'][descriptor]
        assert matched['sourcePresence'] == 'held-locally-with-evidence'
        values = {}
        for field, binding in item['fieldBindings'].items():
            if binding is None:
                values[field] = None
                continue
            actual = resolve(metadata(binding['source']['path'], binding['source']['sha256']), binding['selector'])
            assert actual == binding['value'], (key, field)
            values[field] = deepcopy(actual)
            checks += 1
        owner = values.get('originalOwner')
        assert owner is None or owner == item['originalOwner']
        assets[key] = {'assetId': key, 'kind': 'declared-source-object',
            'publisherCitation': {'citation': values.get('citation'), 'attribution': values.get('attribution'),
                'qualification': 'Exact checked metadata literal; not publisher identity/rights acceptance'},
            'request': {'url': values.get('citation'), 'method': None, 'body': None},
            'release': values.get('release'), 'datatype': item['literalSourceType'], 'format': None,
            'destination': None, 'integrity': {'sha256': item['sha256'], 'bytes': item['bytes'],
                'qualification': 'Exact32selected checked pendingC source declarations; no00body/stat/hash'},
            'budget': None, 'holds': [item['rightsCoverageHolds'], 'Not selected for acquisition; all source/ownership/privacy/access/denial holds remain'],
            'reuse': {'minimumDays': 30, 'originalAcquiredAt': values.get('clock')},
            'purpose': values.get('intendedUse'), 'actualScope': {'country': item['country'],
                'literalSourceType': item['literalSourceType'], 'sourceLanguage': values.get('sourceLanguage'),
                'rightsLiteralUnapproved': values.get('rights'), 'periodCoverage': values.get('periodCoverage'),
                'countryComplete': False, 'qualification': item['applicabilityQualification']},
            'localEvidence': {'declaredPath': item['path'], 'custodian': item['originalOwner'],
                'existenceState': 'held-locally-with-evidence', 'receipt': pin(holding),
                'sourceSelector': item['sourceSelector'], 'existenceQualification': 'Exact57checked bounded declaration; fields dereferenced against pinned sanitized metadata, no new source acquisition or body validation'},
            'provenance': [pin(holding), previous['source57'], item['sourceEvidence']], 'sourceKeys': [],
            'unresolved': ['Exact current source-use/rights/privacy/access/denial/ownership qualification', 'Country/type/recipe/ingredient applicability not accepted', 'Full request/policy/budget/selection contract']}
        added.append(key)
    assert len(added) == 32
    catalog['assets'] = sorted(assets.values(), key=lambda a: a['assetId'])
    catalog['evidence'].append(pin(holding))
    catalog['version'] = 'current249-selected57-pendingC-rebased-current00-r3'
    catalog['qualification'] += ' Selected pendingC32alternate-schema originals now joined by exact identity and individually checked literal metadata fields; no new type edges.'
    registry_pin = save('current249-guarded-registry-r3.json', registry)
    compact = json.loads((ROOT / 'current249-compact-status-r2.json').read_text())
    compact.update(registry=registry_pin, generatedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   registryAssetDescriptorCountNotCopies=len(assets), selectedPendingC32Joined=True)
    compact_pin = save('current249-compact-status-r3.json', compact)
    base = metadata(previous['base']['path'], previous['base']['sha256'])
    original = {a['assetId']: a for a in base['assetCatalog']['assets']}
    old_rows = {(r['country'], r['type']): r for r in base['assetCatalog']['requirements']}
    delta = {'schemaVersion': 'offmenu-guarded-registry-delta/3', 'base': previous['base'], 'result': registry_pin,
        'source57': previous['source57'], 'assetChanges': [{'assetId': k, 'before': original.get(k), 'after': assets[k]} for k in sorted(assets) if original.get(k) != assets[k]],
        'requirementChanges': [{'country': r['country'], 'type': r['type'], 'before': old_rows[(r['country'], r['type'])], 'after': r} for r in catalog['requirements']],
        'newTypeEdges': 0, 'newExecutableSources': 0, 'qualification': 'Exact immutable currentb66 before/after; substantive physical held-state metadata review throughGateway toSAME25. All existing core fields/type links/rights/clocks/holds preserved, tool code unchanged.'}
    delta_pin = save('current249-guarded-delta-r3.json', delta)
    previous.update(registry=registry_pin, compactStatus=compact_pin, delta=delta_pin,
        newDescriptorsVsCurrentBaseline=len(assets)-len(original),
        selectedPendingC32IdentityJoins=len(added), selectedPendingCFieldBindingsChecked=checks,
        residuals=[r for r in previous['residuals'] if r.get('assetId') not in added],
        alternateSchemaJoin='32selected records resolved by exact source identity and pinned typed metadata, not speculative locator inference')
    print(json.dumps(save('current249-rebase-result-r3.json', previous), indent=2))


if __name__ == '__main__':
    main()
