"""Prepare exact reviewed metadata on the existing private transport only."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib

ROOT = Path(__file__).resolve().parent
REPO = Path('/tmp/offmenu-worker00-registry-metadata-20261018')
PARENT = REPO / 'docs/registry-candidate/2026-10-18'
DEST = PARENT / 'current249-r6'
REGISTRY = ROOT / 'current249-guarded-registry-r6-two-P2-corrected.json'
REVIEW = Path('/home/user/.codex/visualizations/2026/10/14/01a138fe-af42-7ff1-8e37-f7ad5abf2671/M-CURRENT249-R6-TWO-P2-DELTA-REVIEW-20261018-W25/review-receipt.json')


def pin(p):
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def encode(o):
    return (json.dumps(o, indent=2, ensure_ascii=False) + '\n').encode()


def main():
    assert pin(REGISTRY)['sha256'] == 'c24dbcb802d1f0d8fe617f08de42c28a60c216a1f136614509b990d7d1d63bab'
    assert pin(REVIEW)['sha256'] == '1f3f3b7981f66dcadc7a03567ea294fd0b339bd8f5734d0ecbf510d2d80acd02'
    author = ROOT / 'current249-r6-two-P2-review-packet.json'
    assert pin(author)['sha256'] == 'a91e79e1f112dd3c1e3fcc86b9d09458f511217d67fa2a92c8f18ef1e5336749'
    assert not DEST.exists()
    DEST.mkdir()
    files = []
    def write(name, obj=None, source=None):
        p = DEST / name
        p.parent.mkdir(parents=True, exist_ok=True)
        b = source.read_bytes() if source else encode(obj)
        assert len(b) < 500000, (name, len(b))
        p.write_bytes(b)
        item = {'path': name, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
        files.append(item)
        return item
    def split(records, stem):
        chunks, batch, start = [], [], 0
        for rec in records:
            if batch and len(encode({'startIndex': start, 'records': batch + [rec]})) > 450000:
                chunks.append(write(f'{stem}-{len(chunks)+1:03d}.json', {'startIndex': start, 'records': batch}))
                start += len(batch)
                batch = []
            batch.append(rec)
        if batch:
            chunks.append(write(f'{stem}-{len(chunks)+1:03d}.json', {'startIndex': start, 'records': batch}))
        assert [r for c in chunks for r in json.loads((DEST / c['path']).read_text())['records']] == records
        return chunks
    registry = json.loads(REGISTRY.read_text())
    skeleton = deepcopy(registry)
    assets = skeleton['assetCatalog'].pop('assets')
    requirements = skeleton['assetCatalog'].pop('requirements')
    skeleton_file = write('registry-skeleton.json', skeleton)
    asset_chunks = split(assets, 'assets/chunk')
    requirement_chunks = split(requirements, 'requirements/chunk')
    reconstructed = deepcopy(skeleton)
    reconstructed['assetCatalog']['assets'] = [r for c in asset_chunks for r in json.loads((DEST / c['path']).read_text())['records']]
    reconstructed['assetCatalog']['requirements'] = [r for c in requirement_chunks for r in json.loads((DEST / c['path']).read_text())['records']]
    reconstructed['assetCatalog'] = {k: reconstructed['assetCatalog'][k] for k in registry['assetCatalog']}
    assert encode(reconstructed) == REGISTRY.read_bytes()
    review_file = write('review-receipt.json', source=REVIEW)
    author_file = write('author-packet.json', source=author)
    cli_file = write('adopted-cli-receipt.json', source=ROOT / 'current249-r6-adopted-cli-receipt.json')
    validation_file = write('author-correction-validation.json', source=ROOT / 'current249-r6-two-P2-author-validation.json')
    adopted = datetime.now(timezone.utc).isoformat()
    adoption = {'status': 'REVIEWED_AND_ADOPTED_METADATA_ONLY', 'adoptedAtUTC': adopted,
        'registry': pin(REGISTRY), 'authorPacket': pin(author), 'review': pin(REVIEW), 'reviewSequence': 9156,
        'verdict': 'SCOPED_PASS_EXACT_R5_TO_R6_TWO_P2_DELTA', 'priorPositiveReviewSequence': 8971,
        'selection': 'Morgan explicit routine reviewed adoption/private-publication selection relayed through Gateway; exact bytes only',
        'sourceCut': 'Frozen selected57checkedFD r5 cut with reviewed two-P2 correction, no later-ingress repin',
        'sourceSnapshotUTC': '2026-10-18T12:00:46.361193+00:00',
        'counts': {'countries': 249, 'typeCells': 3237, 'assetDescriptorsNotDatasets': 3603, 'canonicalReferenceEdges': 299,
                   'frozenRegionalSourceReferenceObjects': 399, 'frozenRegionalBytes': 1781284958,
                   'frozenGlobalFilesSeparate': 3, 'frozenPendingEnvelopes': 25, 'quarantinesRetained': 603},
        'residuals': {'unresolvedDescriptors': 3602, 'identityScopeReferenceConflicts': 28,
                      'kindTypeRightsCountryAcceptance': False, 'countryComplete': False},
        'embeddedRegistryLabels': 'Reviewed bytes preserve historical r5 catalog/version/pending-review text. This separate author-review adoption wrapper supplies current metadata-review status; no frozen-byte relabeling.',
        'runtimeAdoption': False, 'sourceActivation': False, 'sourceUsePermissionUpgrade': False,
        'rawUpload': False, 'actionsRequested': False, 'productionCIX': False}
    adoption_file = write('adoption.json', adoption)
    status = json.loads((ROOT / 'current249-compact-status-r5.json').read_text())
    status.update(registry=pin(REGISTRY), generatedUTC=adopted, reviewState='REVIEWED_AND_ADOPTED_METADATA_ONLY',
                  authorReviewPair={'author': pin(author), 'review': pin(REVIEW), 'sequence': 9156},
                  adoptedAtUTC=adopted, embeddedRegistryHistoricalLabelsPreserved=True,
                  laterFinal57={'path': '/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/final-cut8822-reconciliation/current249-source-type-index.json',
                      'sha256': '47c78074b145959bda5a117bc6cdc890263c79cffe1af64036e83ce0a15a6d30',
                      'disposition': 'Separate later ingress, not this reviewed/adopted cut; next explicit guarded update required'})
    status_file = write('status.json', status)
    status_text = (DEST / 'status.json').read_text()
    type_selectors = {}
    for chunk in requirement_chunks:
        text = (DEST / chunk['path']).read_text()
        for i, row in enumerate(json.loads(text)['records']):
            marker = '      "country": ' + json.dumps(row['country']) + ',\n      "type": ' + json.dumps(row['type']) + ','
            assert text.count(marker) == 1
            type_selectors[(row['country'], row['type'])] = {'type': row['type'], 'path': chunk['path'],
                'jsonPointer': '/records/' + str(i), 'line': text[:text.index(marker)].count('\n') + 1}
    selectors = []
    for i, country in enumerate(status['countries']):
        marker = '      "country": ' + json.dumps(country['country']) + ','
        assert status_text.count(marker) == 1
        cells = [v for (cc, _), v in type_selectors.items() if cc == country['country']]
        assert len(cells) == 13
        selectors.append({'country': country['country'], 'name': country['name'],
            'statusPath': 'status.json', 'statusPointer': '/countries/' + str(i),
            'statusLine': status_text[:status_text.index(marker)].count('\n') + 1, 'typeSelectors': cells})
    selector_chunks = split(selectors, 'country-selectors/chunk')
    manifest = {'schemaVersion': 'offmenu-reviewed-current249-private-transport/1',
        'status': 'REVIEWED_AND_ADOPTED_METADATA_ONLY', 'registry': pin(REGISTRY),
        'adoption': adoption_file, 'statusArtifact': status_file, 'authorPacket': author_file,
        'review': review_file, 'adoptedCLI': cli_file, 'validation': validation_file,
        'registrySkeleton': skeleton_file, 'assetChunks': asset_chunks, 'requirementChunks': requirement_chunks,
        'registryAssetKeyOrder': list(registry['assetCatalog']), 'countrySelectorChunks': selector_chunks,
        'files': list(files), 'exactRegistryBytesReassembled': True,
        'reassembly': 'Concatenate chunk.records in startIndex order into skeleton assetCatalog.assets/requirements. Restore registryAssetKeyOrder, JSON ensure_ascii=False indent=2 plus newline; SHA256 must match registry. Existing Foo metadata evidence custody is required for local CLI; no access/provisioning grant.',
        'lookup': 'Read status.countries by exact country code, or use country-selector chunk records for exact JSON pointers and line anchors. All paths are relative to this immutable commit directory. Source possession is not accepted type/country coverage.',
        'cut': adoption['sourceSnapshotUTC'], 'adoptedAtUTC': adopted,
        'noRawRows': True, 'sourceUsePermissionUpgrade': False, 'laterIngressAdopted': False}
    write('index.json', manifest)
    pointer = {'path': 'current249-r6/index.json', 'statusPath': 'current249-r6/status.json',
        'adoptionPath': 'current249-r6/adoption.json', 'status': 'REVIEWED_AND_ADOPTED_METADATA_ONLY',
        'registrySHA256': pin(REGISTRY)['sha256'], 'reviewSHA256': pin(REVIEW)['sha256'],
        'priorR5': {'path': 'current249-r5/index.json', 'status': 'REVIEW_FAILED_NOT_ADOPTED_HISTORICAL'},
        'laterFinal57NotIncluded': True, 'countryTypeScientificSourceUseAcceptance': False}
    (PARENT / 'CURRENT249.json').write_bytes(encode(pointer))
    preflight = {'at': adopted, 'repository': 'maldous/offmenu',
        'branch': 'integration/registry-metadata-candidate-20261018', 'priorHead': '423ca79ef748bd64cdbb85d745cd01c6fc1e5fa7',
        'reviewedRegistry': pin(REGISTRY), 'review': pin(REVIEW), 'authorPacket': pin(author),
        'destination': str(DEST), 'fileCountIncludingCurrentPointer': len(files) + 1,
        'maximumFileBytes': max(p.stat().st_size for p in DEST.rglob('*.json')),
        'allFilesBelow500000B': all(p.stat().st_size < 500000 for p in DEST.rglob('*.json')),
        'exactReviewedRegistryReassembled': True, 'countries': 249, 'typeCells': 3237,
        'sourceCutUnchanged': True, 'quarantinesRetained': 603, 'rawRowsUploaded': 0,
        'actionsRequested': False, 'runtimeProductionCIX': False,
        'nextAction': 'Record publication intent; normal existing-private-branch commit/push with skipCI; verify refs/content and return immutable reviewed/adopted references.'}
    p = ROOT / 'current249-r6-reviewed-publication-preflight.json'
    p.write_bytes(encode(preflight))
    print(json.dumps({'preflight': pin(p), 'files': preflight['fileCountIncludingCurrentPointer'],
                      'maximumBytes': preflight['maximumFileBytes']}, indent=2))


if __name__ == '__main__':
    main()
