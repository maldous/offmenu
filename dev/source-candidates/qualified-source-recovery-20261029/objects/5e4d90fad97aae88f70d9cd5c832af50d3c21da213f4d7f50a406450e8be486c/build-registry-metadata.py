"""Bounded metadata projection into the existing collection registry; no raw reads.

57 retains mapping authority. This materializes its pinned snapshot, preserves
unresolved provenance and never makes a descriptor an acquisition grant.
"""
import copy
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import re

OUT = Path(__file__).parent
INVENTORY = Path('/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/all249-source-collection-current-v3.json')
REGISTER = Path('/home/user/src/offmenu/research/OffMenu_Global_Data_Source_Register.json')
CAVEATS = INVENTORY.with_name('current-report-caveats.json')
ROOT = REGISTER.parents[1]
ENRICHMENT = ROOT / 'research/OffMenu_Enrichment_Source_Register_249.json'
BASKETS = ROOT / 'research/OffMenu_Country_Basket_Register.json'
NATIVE = ROOT / 'corpus/common-source-mappings.json'
OVERTURE = ROOT / 'docs/collections/overture-food-places-2026-09-23.1.json'
USDA = ROOT / 'docs/collections/usda-2026-04.json'
PERMISSIONS = Path('/tmp/offmenu-worker00-pr42-20261018/docs/source-release-permissions-evidence.json')


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def public_url(value):
    if not isinstance(value, str) or not value:
        return None
    p = urlsplit(value)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        return None
    query = parse_qsl(p.query, keep_blank_values=True)
    if any(re.search(r'token|api.?key|secret|pass|auth|credential|signature', k, re.I)
           or '[REDACTED]' in v for k, v in query):
        return None
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), ''))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    inventory = json.loads(INVENTORY.read_text())
    register = json.loads(REGISTER.read_text())
    selection = json.loads((OUT / 'representative-selection.json').read_text())
    metadata_pin = pin(INVENTORY)
    register_pin = pin(REGISTER)
    release_by_file = {}
    for key, release in inventory['sourceReleases'].items():
        for file_id in release['fileIds']:
            release_by_file.setdefault(file_id, []).append({'key': key, **release['identity']})
    assets = []
    roles = {'SOURCE_DATA_FILE', 'SOURCE_REFERENCE_DOCUMENT', 'SOURCE_NOTICE_OR_RECORD_PAGE'}
    for file_id, item in sorted(inventory['sourceFiles'].items()):
        release_refs = release_by_file.get(file_id, [])
        urls = set(filter(None, [public_url(item.get('url'))] +
                          [public_url(x.get('recordedURL')) for x in release_refs]))
        releases = {str(v) for v in (item.get('release'), item.get('version')) if v}
        releases.update(str(x['release']) for x in release_refs if x.get('release'))
        url = next(iter(urls)) if len(urls) == 1 else None
        release = next(iter(releases)) if len(releases) == 1 else None
        selected = (item.get('path') == selection['sources'][0]['retained']['path']
                    and item.get('sha256') == selection['sources'][0]['retained']['sha256'])
        asset = {'assetId': 'file:' + file_id,
                 'kind': 'declared-raw-original' if item['artifactRole'] in roles else 'supporting-or-unverified-descriptor',
                 'publisherCitation': None,
                 'request': {'url': url, 'method': item.get('recordedMethod'), 'body': None,
                             'parameters': None, 'recordedURLCandidates': sorted(urls)},
                 'release': release, 'datatype': item['artifactRole'], 'format': None,
                 'destination': None, 'integrity': {'sha256': item.get('sha256'), 'bytes': item.get('bytes'),
                     'extent': item.get('hashExtent'), 'actualRehashedByThisProjection': False},
                 'budget': None, 'holds': ['not-selected-for-acquisition; source-specific review/claims required'],
                 'reuse': {'minimumDays': 30, 'originalAcquiredAt': item.get('originalAcquiredAt', item.get('utc')),
                           'validators': None, 'qualification': 'recorded metadata only; no clock reset'},
                 'purpose': item.get('coverage'),
                 'actualScope': {'country': item.get('country'), 'typeHints': item.get('typeHints', []),
                                 'qualification': item.get('typeHintQualification'), 'countryComplete': False},
                 'localEvidence': {'declaredPath': item.get('path'), 'reportedStatus': item.get('reportedLocalStatus'),
                                   'custodian': item.get('recordedSourceCustodian', item.get('recordedOwnerLabel')),
                                   'qualification': '57 metadata descriptor; no current raw stat/hash in projection'},
                 'provenance': [metadata_pin, item.get('sourceEvidence')], 'sourceKeys': [],
                 'unresolved': ['publisher-citation', 'source-use-and-current-claim-review', 'format',
                                'destination', 'source-specific-budget', 'request-contract' ]}
        if not url:
            asset['unresolved'].append('exact-public-locator')
        if release is None:
            asset['unresolved'].append('exact-release')
        if not asset['reuse']['originalAcquiredAt']:
            asset['unresolved'].append('original-acquisition-clock')
        if item.get('country') in ('NZ', 'LK'):
            asset['holds'].append('current-NZ-LK-provenance-unresolved; no repin')
        if selected:
            source = selection['sources'][0]
            asset.update(publisherCitation={'publisher': 'World Food Programme via HDX',
                'url': source['spec']['url'], 'sourceUseEvidence': source['spec']['rights_reference']},
                request={'url': source['spec']['url'], 'method': 'GET', 'body': None, 'parameters': None},
                release=source['spec']['release'], format='CSV', budget=selection['resources'], holds=[],
                destination=selection['resources']['storageRoot'], sourceKeys=[source['spec']['source_key']],
                unresolved=[], localEvidence={'declaredPath': source['retained']['path'],
                    'custodian': 27, 'physicalVerification': pin(OUT / 'representative-verification.json')})
        assets.append(asset)
    # Preserve documentary citations separately; these are not downloaded assets.
    by_url = {}
    citations = [{**source, 'provenance': register_pin} for source in register['sources']]
    enrichment = json.loads(ENRICHMENT.read_text())
    citations += [{'id': s['source_id'], 'title': '; '.join(s['names']),
                   'url': s['canonical_url'], 'provenance': pin(ENRICHMENT)}
                  for s in enrichment['source_catalog']]
    baskets = json.loads(BASKETS.read_text())
    citations += [{'id': s.get('id'), 'title': s['title'], 'url': s['url'], 'provenance': pin(BASKETS)}
                  for s in baskets['core_sources'] + baskets['supporting_sources']]
    for source in citations:
        url = public_url(source.get('url'))
        if url:
            by_url.setdefault(url, []).append(source)
    for url, citations in sorted(by_url.items()):
        assets.append({'assetId': 'citation:' + hashlib.sha256(url.encode()).hexdigest()[:24],
            'kind': 'desired-source-citation', 'publisherCitation': {
                'titles': [x['title'] for x in citations], 'url': url,
                'sourceIds': [x['id'] for x in citations],
                'qualification': 'historical documentary discovery; not asset custody or rights'},
            'request': {'url': url, 'method': None, 'parameters': None, 'body': None},
            'release': None, 'datatype': None, 'format': None, 'destination': None,
            'integrity': None, 'budget': None, 'holds': ['discovery-only; acquisition not selected'],
            'reuse': {'minimumDays': 30, 'originalAcquiredAt': None, 'validators': None},
            'purpose': 'Retained historical source citation; precise asset contract pending',
            'actualScope': {'countryCoverageVerified': False}, 'localEvidence': None,
            'provenance': sorted({json.dumps(x['provenance'], sort_keys=True): x['provenance']
                                  for x in citations}.values(), key=lambda x: x['path']), 'sourceKeys': [],
            'unresolved': ['actual-original-asset', 'publisher-origin-qualification', 'release',
                           'request-contract', 'format', 'destination', 'integrity',
                           'budget', 'source-use-and-current-claim-review', 'coverage']})
    template = copy.deepcopy(assets[-1])
    native = json.loads(NATIVE.read_text())
    for source in native['sources']:
        item = copy.deepcopy(template)
        item.update(assetId='native:' + source['sourceId'] + ':' + source['releaseId'],
            kind='historical-native-mapping', publisherCitation={'publisher': source.get('attribution'),
                'qualification': 'Historical native mapping; not current physical custody or permission'},
            request={'url': public_url(source.get('sourceManifest')), 'method': None,
                     'locatorRole': 'manifest-not-original'}, release=source['releaseId'],
            datatype=source.get('canonicalTypes'), provenance=[pin(NATIVE), pin(PERMISSIONS)],
            purpose='Preserve native mapping identity; original asset/custody recovery pending',
            unresolved=['exact-original-asset', 'local-custody', 'original-acquisition-clock',
                        'request-contract', 'current-source-use-and-hold-review', 'destination', 'integrity', 'budget'])
        if source['sourceId'] == 'off':
            item['holds'].append('OldOct12OFFcounts superseded; Unicode line-separator issue; no oldcount acceptance')
        assets.append(item)
    overture = json.loads(OVERTURE.read_text())
    for source in overture['sourceFiles']:
        item = copy.deepcopy(template)
        item.update(assetId='overture-key:' + hashlib.sha256(source['key'].encode()).hexdigest()[:24],
            kind='historical-pinned-source-member', publisherCitation={'publisher': 'Overture Maps',
                'qualification': 'Exact source member key/hash in historical collection manifest'},
            request={'url': None, 'method': None, 'objectKey': source['key']},
            release=overture['releaseId'], datatype='place', format='Parquet',
            integrity={'sha256': source['sourceSha256'], 'bytes': None,
                       'qualification': 'Manifest-declared member hash; no current physical verification'},
            purpose='Historical explicit16member set; archiveSha is manifest hash, never concatenated member hash',
            provenance=[pin(OVERTURE)], unresolved=['local-custody', 'original-acquisition-clock',
                'exact-download-locator', 'current-source-use-and-hold-review', 'destination', 'budget'])
        assets.append(item)
    usda = json.loads(USDA.read_text())
    item = copy.deepcopy(template)
    item.update(assetId='usda-archive:2026-04', kind='historical-pinned-source-archive',
        publisherCitation={'publisher': usda.get('attribution'), 'url': public_url(usda.get('url'))},
        request={'url': None, 'method': None}, release='2026-04', datatype='food-composition', format='ZIP',
        integrity={'sha256': usda['archiveSha256'], 'bytes': None,
                   'qualification': 'Recorded full archive SHA;34CSVschemas and35members separately declared'},
        purpose='Preserve exact full archive contract; original copy/custody/directURL qualification pending',
        provenance=[pin(USDA)], unresolved=['local-custody', 'original-acquisition-clock', 'exact-download-locator',
            'current-source-use-and-hold-review', 'destination', 'budget'])
    assets.append(item)
    ids = {a['assetId'] for a in assets}
    requirements = []
    for country in inventory['countries']:
        for row in country['canonicalDomains']:
            requirements.append({'country': country['country'], 'type': row['type'],
                'assetIds': sorted('file:' + x for x in row['sourceFileIds'] if 'file:' + x in ids),
                'status': row['collectionStatus'], 'coverageQualification': row['coverage'], 'evidence': metadata_pin})
    result = copy.deepcopy(selection)
    result['schemaVersion'] = 'offmenu-acquisition-selection/2'
    result['assetCatalog'] = {'version': 'worker57-v3-plus-historical-registers-r2',
        'assets': assets, 'requirements': requirements,
        'evidence': [metadata_pin, register_pin, pin(CAVEATS), *[pin(p) for p in
            (ENRICHMENT, BASKETS, NATIVE, OVERTURE, USDA, PERMISSIONS)]],
        'qualification': 'Pinned57 snapshot plus historical discovery citations, NOT exhaustive verified originals. '
                         'Missing reports/provenance remain unknown. Descriptors include supporting/failed/derived files; '
                         'declared local counts are NOT fresh physical verification. No source automatically enabled. '
                         '57 owns authoritative mapping reconciliation; only one reviewed retained LY source selected.'}
    write(OUT / 'reviewed-asset-registry-v2.json', result)
    write(OUT / 'registry-projection-inputs.json', {'inputs': result['assetCatalog']['evidence'],
        'builder': pin(Path(__file__)), 'registry': pin(OUT / 'reviewed-asset-registry-v2.json')})
    print(json.dumps({'assets': len(assets), 'countryRequirements': len(requirements),
                      'selected': len(result['sources']), 'datasetBodiesRead': 0}))


def build_country_index():
    import sys
    import datetime
    import stat
    sys.path.insert(0, '/tmp/offmenu-worker00-pr42-20261018')
    from offmenu.refresh.core import timestamp, RefreshError
    from offmenu.refresh.acquisition import describe_collection_registry, lookup_country_sources
    original = OUT / 'reviewed-asset-registry-v2.json'
    assert pin(original)['sha256'] == '379cdbf66e751b3124396044d974ae6c6bf9ef03ae9f2780a6e4e085a5702fe8'
    current = INVENTORY.with_name('all249-country-report-corrected-20261018-v2.json')
    assert pin(current)['sha256'] == '2a1dae4b7f6968d7fe34959bc3c2813f68cec4fc78231046504269002834ffbd'
    source = json.loads(current.read_text())
    registry = json.loads(original.read_text())
    catalog = registry['assetCatalog']
    assets = {a['assetId']: a for a in catalog['assets']}
    raw_roles = {'SOURCE_DATA_FILE', 'SOURCE_REFERENCE_DOCUMENT', 'SOURCE_NOTICE_OR_RECORD_PAGE'}
    def receipt_pin(value):
        return {k: value[k] for k in ('path', 'sha256')}
    for file_id, item in source['sourceFiles'].items():
        key = 'file:' + file_id
        if key not in assets:
            assets[key] = {'assetId': key,
                'kind': 'declared-raw-original' if item['artifactRole'] in raw_roles else 'supporting-or-unverified-descriptor',
                'publisherCitation': None, 'request': {'url': public_url(item.get('url')),
                    'method': item.get('recordedMethod'), 'body': None},
                'release': item.get('release', item.get('version')), 'datatype': item['artifactRole'],
                'format': None, 'destination': None,
                'integrity': {'sha256': item.get('sha256'), 'bytes': item.get('bytes'),
                              'qualification': 'Recorded metadata only; no current raw rehash'},
                'budget': None, 'holds': ['Not selected for acquisition; existing source/use/claims retained'],
                'reuse': {'minimumDays': 30, 'originalAcquiredAt': item.get('originalAcquiredAt', item.get('utc'))},
                'purpose': item.get('coverage'), 'actualScope': {'country': item.get('country'),
                    'typeHints': item.get('typeHints', []), 'countryComplete': False},
                'localEvidence': {'declaredPath': item.get('path'),
                    'custodian': item.get('recordedSourceCustodian', item.get('recordedOwnerLabel'))},
                'provenance': [pin(current), item.get('sourceEvidence')], 'sourceKeys': [],
                'unresolved': ['Current source-use/claim review', 'Full request/release/budget contract',
                               'Exact country/type coverage; not whole country acceptance']}
        asset = assets[key]
        # Only an actual recorded original/custody report can supply this state.
        # Supporting, derived, failed or unqualified JSON/HTML descriptors stay unknown.
        verification = item.get('ownerVerification', '') or ''
        if (item['artifactRole'] in raw_roles and item.get('path') and item.get('sha256')
                and isinstance(item.get('sourceEvidence'), dict)
                and (verification == 'CURRENT_OWNER_REPORT' or verification.startswith('ACTUAL'))):
            local = asset['localEvidence'] or {}
            local.update(declaredPath=item['path'], existenceState='held-locally-with-evidence',
                receipt=receipt_pin(item['sourceEvidence']), existenceQualification=
                'Owner receipt/57 metadata evidence; not a fresh stat/hash by00 unless separately noted')
            asset['localEvidence'] = local
    # Targeted AU/BE checks use the exact named originals, never a filesystem census.
    observations = []
    for country in source['countries']:
        if country['country'] not in ('AU', 'BE'):
            continue
        for file_id in country['sourceFileIds']:
            item = source['sourceFiles'][file_id]
            if item['artifactRole'] not in raw_roles:
                continue
            path = Path(item['path'])
            observed = path.lstat()
            if not stat.S_ISREG(observed.st_mode) or stat.S_ISLNK(observed.st_mode) or observed.st_size != item['bytes']:
                raise ValueError('Targeted held original stat/size mismatch: ' + str(path))
            key = 'file:' + file_id
            assets[key]['localEvidence'].update(existenceState='held-locally-with-evidence',
                declaredPath=str(path), receipt=receipt_pin(item['sourceEvidence']),
                observedBytes=observed.st_size, existenceQualification='Targeted regular-file lstat/size by00; no raw body read/hash')
            observations.append({'assetId': key, 'country': country['country'],
                'path': str(path), 'bytes': observed.st_size, 'payloadRead': False})
    us_path = OUT / 'US-actual-held-source-evidence.json'
    us = json.loads(us_path.read_text())
    for item in us['assets']:
        key = item['assetId']
        if key not in assets:
            assets[key] = copy.deepcopy(assets['usda-archive:2026-04'])
            assets[key]['assetId'] = key
            assets[key]['sourceKeys'] = []
        asset = assets[key]
        asset.update(publisherCitation={'publisher': item['publisher'],
                'url': item.get('publisherURL', item.get('publisherURLCandidate')),
                'qualification': item.get('publisherURLQualification', 'Retained source metadata; rights/admission separate')},
            release=item['release'], integrity={'sha256': item['recordedSHA256'],
                'bytes': item['local']['observedBytes'], 'qualification': 'Recorded source hash plus actual lstat; no current raw rehash'},
            localEvidence={'declaredPath': item['local']['path'], 'observedBytes': item['local']['observedBytes'],
                'existenceState': 'held-locally-with-evidence', 'custodian': item.get('historicalAcquisitionCustodian'),
                'receipt': item['evidence'][0], 'existenceObservedAt': us['observedUTC'],
                'existenceQualification': item['local']['observation']},
            reuse={'minimumDays': 30, 'originalAcquiredAt': item.get('originalAcquiredAt')},
            actualScope={'sourceScope': item.get('scope', item.get('qualification', item.get('receiptScope'))),
                'countryComplete': False, 'coverageQualified': False},
            provenance=item['evidence'] + [pin(us_path)],
            holds=item.get('holds', ['Existing rights/coverage/actual request contract remain separately qualified']),
            unresolved=item.get('provenanceGaps', ['Exact coverage/current rights/runtime admission separate from held existence']))
        if key == 'shared-off-original:2026-10-12':
            asset['kind'] = 'shared-global-original'
            asset['format'] = 'GZIP JSONL'
        elif key == 'us-openfda-food-enforcement:2026-10-14':
            asset['kind'] = 'declared-raw-original'
            asset['format'] = 'ZIP'
    def clock(value):
        try:
            if value:
                timestamp(value)
                return value
        except (RefreshError, ValueError, TypeError):
            pass
        return None
    requirements = []
    for country in source['countries']:
        for raw in country['requirements']:
            keys = sorted('file:' + x for x in raw['fileIds'] if 'file:' + x in assets)
            # These are source-reference uses backed by the actual targeted US result.
            # Global OFF remains one asset with unqualified exact US coverage.
            if country['country'] == 'US':
                overrides = {'food_composition': 'usda-archive:2026-04',
                    'recalls_regulation': 'us-openfda-food-enforcement:2026-10-14',
                    'barcodes_products': 'shared-off-original:2026-10-12',
                    'recipes': next(a['assetId'] for a in us['assets'] if a['type'] == 'recipes')}
                if raw['type'] in overrides:
                    keys = sorted(set(keys + [overrides[raw['type']]]))
            bindings = []
            for key in keys or [None]:
                asset = assets.get(key, {})
                local = asset.get('localEvidence') or {}
                held = local.get('existenceState') == 'held-locally-with-evidence'
                bindings.append({'assetId': key, 'state': 'held-locally-with-evidence' if held else 'unknown-notyetfound',
                    'owner': country['deliveryOwner'], 'citation': asset.get('publisherCitation'),
                    'release': asset.get('release'), 'localPointer': local.get('declaredPath') if held else None,
                    'receipt': local.get('receipt') if held else None,
                    'receiptDate': clock((asset.get('reuse') or {}).get('originalAcquiredAt')),
                    'nextAction': 'Reuse known held original; original custodian qualifies missing provenance/rights/coverage, no redownload from join gaps.' if held else
                        'Existing owner locates exact source/receipt or qualifies current declared pointer; unknown is not absence or N/A.',
                    'pointerScope': 'shared' if key and key.startswith('shared-') else 'direct' if key else 'unknown',
                    'rights': {'status': 'separate-current-source-use-assessment', 'holds': asset.get('holds', []),
                               'lookupDoesNotEnableSource': True},
                    'coverage': {'status': 'unassessed', 'sourceQualification': raw['scope'],
                                 'completeCountryOrType': False,
                                 'ownerQualification': 'Current country delivery owner; original source custodian separate in asset localEvidence'},
                    'blockedReason': None})
            requirements.append({'country': country['country'], 'type': raw['type'], 'assetIds': keys,
                'status': raw['status'], 'coverageQualification': raw['scope'], 'evidence': pin(current),
                'bindings': bindings})
    registry['schemaVersion'] = 'offmenu-acquisition-selection/3'
    catalog.update(version='country-index-v3-partially-reconciled57-plus-targeted-US-AU-BE',
        assets=list(assets.values()), requirements=requirements,
        evidence=catalog['evidence'] + [pin(current), pin(us_path)],
        qualification='PARTIALLY RECONCILED249metadata;225reportrowsnotfullyreconciled/all249completetotalsnull. '
        'Held existence separate from provenance/rights/coverage. Source references/type joins remain unassessed; '
        'no SourceSpec admission, N/A inference, source acquisition or runtime adoption from lookup. '
        'Owner57 remains country-mapping authority,00 executable contract owner.')
    describe_collection_registry(registry)
    assert len(requirements) == 3237 and len({r['country'] for r in requirements}) == 249
    output = OUT / 'reviewed-asset-registry-v3.json'
    write(output, registry)
    for code in ('US', 'AU', 'BE'):
        write(OUT / ('country-' + code + '-lookup.json'), lookup_country_sources(registry, code))
    report = {'registry': pin(output), 'source57': pin(current), 'sourceUS': pin(us_path),
        'targetedAU_BEObservations': observations, 'requirements': 3237, 'countries': 249,
        'assets': len(assets), 'rawPayloadBytesRead': 0, 'sourcePayloadHashesRecomputed': 0,
        'admittedSources': len(registry['sources']), 'newSourceAdmissions': 0,
        'bindings': dict(__import__('collections').Counter(b['state'] for r in requirements for b in r['bindings'])),
        'countryComplete': False, 'runtimeAdopted': False, 'lookupScope': 'SAME registry input to CLI collect/describe/lookup',
        'sourceQualification': catalog['qualification']}
    write(OUT / 'country-index-build-result.json', report)
    print(json.dumps({k: report[k] for k in ('registry', 'countries', 'requirements', 'assets', 'bindings', 'newSourceAdmissions')}))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--country-index']:
        build_country_index()
    else:
        main()
