"""Freeze selected57checkedFD metadata; preserve prior exact guards and holds."""
import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_metadata_helpers', ROOT / 'build-current249-guarded-index-r3.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
SRC = Path('/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/checked-pending-FD-addenda')
view, receipt = SRC / 'current249-source-type-index.json', SRC / 'result.json'
assert h.pin(view)['sha256'] == '07febb0d1de8459d7b4d09037ff42a3e0ee0e78a81814c95d0aa777d535f0548'
assert h.pin(receipt)['sha256'] == 'c8a06839f31830d5eeec541f47f2ddcc78878359c16bcaad9f9794b681f35efb'
s = json.loads(view.read_text())
r = json.loads((ROOT / 'current249-rebase-result-r4.json').read_text())
reg = json.loads(Path(r['registry']['path']).read_text())
assets = {a['assetId']: a for a in reg['assetCatalog']['assets']}
added = []
for descriptor, item in s['sourceDescriptors'].items():
    key = 'file:' + descriptor
    if key in assets:
        assert (assets[key]['localEvidence'] or {}).get('declaredPath') == item['path']
        assert (assets[key]['integrity'] or {}).get('sha256') == item['sha256']
        continue
    q = item.get('originalHelperFindingRetained', item.get('qualifications'))
    assert isinstance(q, dict)
    pointer = q.get('actualOriginalPointer', q.get('path'))
    if isinstance(pointer, dict):
        assert all(pointer[field] == item[field] for field in ('path', 'sha256', 'bytes'))
        pointer = pointer['path']
    assert pointer == item['path']
    assert q.get('recordedSHA256', q.get('sha256')) == item['sha256']
    assert q.get('wholeOriginalBytes', q.get('bytes')) == item['bytes']
    country = q.get('country', q.get('countryOrExplicitUnknown', item['country']))
    assert country == item['country']
    # The selected57checked snapshot, not speculative producer totals, supplies
    # possession. Every original's literal schema remains linked by selector.
    assert item.get('recordedSourceUnit') in {
        None, 'complete-original', 'distinct-batch-original-proposal', 'new-distinct-source-original',
        'new-selected-whole-original', 'earlier-samebatch-DE-subset-carried-by-exact-final8728',
        'new-additive-exact-profile-continuation-prior-HIES-retained',
        'new-additive-household-followon-only-not-cumulative-six-originals'}
    assets[key] = {'assetId': key, 'kind': 'declared-source-object',
        'publisherCitation': {'citationAsReported': q.get('publisherCitation', q.get('sourceCitation')),
                              'qualification': 'Literal checked source metadata, not source-use/type acceptance'},
        'request': {'url': q.get('sourceURL', q.get('url')), 'method': None, 'body': None},
        'release': q.get('releaseOrPeriod', q.get('periodOrRelease')), 'datatype': item['literalSourceType'],
        'format': None, 'destination': None,
        'integrity': {'sha256': item['sha256'], 'bytes': item['bytes'], 'qualification': 'Exact57checked bounded original identity; no00rawbody/stat/hash'},
        'budget': None, 'holds': ['All source-use/privacy/access/denial/ownership holds retained; not selected for acquisition',
                                q.get('rights', q.get('rightsCoveragePeriodLanguageHolds', 'Current source rights unqualified; retain exact source contract by selector'))],
        'reuse': {'minimumDays': 30, 'originalAcquiredAt': q.get('originalAcquiredAt', q.get('originalAcquisitionClock'))},
        'purpose': 'Retain original source object; no recipe/composition equivalence from numeric/context references',
        'actualScope': {'country': item['country'], 'literalSourceType': item['literalSourceType'],
                       'sourceLanguage': q.get('sourceLanguage', q.get('sourceLanguageAsRecorded')),
                       'applicability': q.get('applicability', q.get('applicabilityQualification')),
                       'recordedSourceUnit': item.get('recordedSourceUnit'),
                       'countryComplete': False, 'allOriginalContractRestrictionsRetainedByEvidence': True},
        'localEvidence': {'declaredPath': item['path'], 'custodian': item['originalOwner'],
                          'existenceState': 'held-locally-with-evidence', 'receipt': h.pin(view),
                          'sourceSelector': item['sourceSelector'],
                          'existenceQualification': '57checked exact bounded original declaration; no new body verification'},
        'provenance': [h.pin(view), h.pin(receipt), item['sourceEvidence']], 'sourceKeys': [],
        'unresolved': ['Source-use/rights/privacy/access/denial/ownership qualification',
                       'Country/type/recipe/ingredient applicability unaccepted', 'Request/policy/budget/selection contract']}
    added.append(key)
assert len(added) == 112
cat = reg['assetCatalog']
cat['assets'] = sorted(assets.values(), key=lambda a: a['assetId'])
cat['evidence'] += [h.pin(view), h.pin(receipt)]
cat['version'] = 'current249-selected57-checkedFD-rebased-current00-r5'
cat['qualification'] += ' Selected57checkedFD adds112 scoped source/reference objects;399bounded1781284958B total,global3separate,25frozenenvelopespending. Later snapshots require another explicit guarded cut.'
reg_pin = h.save('current249-guarded-registry-r5.json', reg)
compact = json.loads(Path(r['compactStatus']['path']).read_text())
compact.update(registry=reg_pin, generatedUTC=datetime.now(timezone.utc).isoformat(), full57View=h.pin(view),
               sourceSnapshotUTC=s['observedUTC'], checkedFDAddenda=h.pin(receipt), pendingFrozenEnvelopes=25,
               boundedRegionalOriginals=399, boundedRegionalBytes=1781284958,
               registryAssetDescriptorCountNotCopies=len(assets), sourceDescriptorCountNotCopies=len(s['sourceDescriptors']),
               countryPresenceAsReportedBy57=s['countryPresenceCounts'], literalTypeHintsAsReportedUnaccepted=s['typeSourcePresenceCounts'])
countries = {c['country']: c for c in s['countries']}
for c in compact['countries']:
    n = countries[c['country']]
    c.update(sourcePresence=n['countryState'], recordedDescriptorReferences=len(n['sourceDescriptorIds']),
             checkedBoundedOriginalReferences=len(n['checkedBoundedAcquisitionOriginalIds']))
compact_pin = h.save('current249-compact-status-r5.json', compact)
base = json.loads(Path(r['base']['path']).read_text())
original = {a['assetId']: a for a in base['assetCatalog']['assets']}
rows = {(x['country'], x['type']): x for x in base['assetCatalog']['requirements']}
for k, a in original.items():
    for field in set(a) - {'localEvidence'}:
        assert assets[k][field] == a[field], (k, field)
for row in cat['requirements']:
    for field in ('assetIds', 'status', 'coverageQualification'):
        assert row[field] == rows[(row['country'], row['type'])][field]
for field in ('sources', 'resources', 'bindings', 'evidence', 'schemaVersion'):
    assert reg[field] == base[field]
delta = {'schemaVersion': 'offmenu-guarded-registry-delta/5', 'base': r['base'], 'result': reg_pin, 'source57': h.pin(view),
         'assetChanges': [{'assetId': k, 'before': original.get(k), 'after': assets[k]} for k in sorted(assets) if original.get(k) != assets[k]],
         'requirementChanges': [{'country': x['country'], 'type': x['type'], 'before': rows[(x['country'], x['type'])], 'after': x} for x in cat['requirements']],
         'newTypeEdges': 0, 'newExecutableSources': 0,
         'qualification': 'Frozen currentb66 to r5 exact before/after; pendingSAME25 review of substantive physical evidence. Unchanged accepted tooling; no country/type/source-use acceptance.'}
delta_pin = h.save('current249-guarded-delta-r5.json', delta)
r.update(registry=reg_pin, compactStatus=compact_pin, delta=delta_pin, source57=h.pin(view), checkedFDAddenda=h.pin(receipt),
         selectedFD112Joins=112, newDescriptorsVsCurrentBaseline=len(assets)-len(original), sourceSnapshotPending=25,
         freeze='r5selectedcut; later snapshots need fresh guard checks, never silent repin')
print(json.dumps(h.save('current249-rebase-result-r5.json', r), indent=2))
