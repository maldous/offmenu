#!/usr/bin/env python3
"""Acquire a small, rights-qualified discovery bundle for future recipe work.

The output is deliberately source evidence only: it does not extract, publish,
or admit any individual recipe.  Source documents remain local until a later
recipe-boundary and rights review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path('/home/user/src/offmenu-data')
MAX_BYTES = 20 * 1024 * 1024
SOURCES = (
    {
        'id': 'wellcome-indian-cookery-book-1869',
        'workId': 'gu8n9ens', 'itemId': 'b2152824x',
        'workUrl': 'https://wellcomecollection.org/works/gu8n9ens',
        'context': {'sourceDeclaredSubject': 'Indian cooking', 'sourceDeclaredPublication': 'Calcutta : Wyman & Co., [1869?]',
                    'language': 'und', 'cultureInference': 'none'},
        'titleMustContain': 'Indian cookery book',
    },
    {
        'id': 'wellcome-english-chinese-cookery-book-1890',
        'workId': 'caqdp57k', 'itemId': 'b28079887',
        'workUrl': 'https://wellcomecollection.org/works/caqdp57k',
        'context': {'sourceDeclaredSubject': 'Cooking; China',
                    'sourceDeclaredPublication': '[Place of publication not identified] : [publisher not identified], 1890 (Hongkong : Kelly & Walsh.)',
                    'language': 'en and zh (declared by title only; manuscript/page-level verification required)',
                    'cultureInference': 'none'},
        'titleMustContain': 'English-Chinese cookery book',
    },
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'OffMenu-source-audit/1.0 (+https://offmenu.aldous.info)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        length = response.headers.get('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError(f'{url}: declared payload exceeds bounded acquisition limit')
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f'{url}: payload exceeds bounded acquisition limit')
    return data


def metadata_value(manifest: dict, label: str) -> list[str]:
    for entry in manifest.get('metadata', []):
        if entry.get('label', {}).get('en', [None])[0] == label:
            return next(iter(entry.get('value', {}).values()), [])
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'recipe-global-discovery-20261014')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f'immutable output already exists: {args.output}')
    args.output.mkdir(parents=True)
    records, files = [], []
    for source in SOURCES:
        metadata_url = f"https://api.wellcomecollection.org/catalogue/v2/works/{source['workId']}"
        iiif_url = f"https://iiif.wellcomecollection.org/presentation/v3/{source['itemId']}"
        metadata_bytes, manifest_bytes = fetch(metadata_url), fetch(iiif_url)
        metadata, iiif = json.loads(metadata_bytes), json.loads(manifest_bytes)
        title = iiif.get('label', {}).get('en', [''])[0]
        if source['titleMustContain'].lower() not in title.lower():
            raise ValueError(f"{source['id']}: unexpected IIIF title")
        if iiif.get('rights') != 'http://creativecommons.org/publicdomain/mark/1.0/':
            raise ValueError(f"{source['id']}: expected Wellcome Public Domain Mark is absent")
        usage = metadata_value(iiif, 'Attribution and usage')
        if not any('free of known restrictions' in item for item in usage):
            raise ValueError(f"{source['id']}: provider rights statement is absent")
        local_meta = f"{source['id']}.work.json"
        local_manifest = f"{source['id']}.iiif.json"
        (args.output / local_meta).write_bytes(metadata_bytes)
        (args.output / local_manifest).write_bytes(manifest_bytes)
        files.extend([
            {'key': local_meta, 'sourceUrl': metadata_url, 'bytes': len(metadata_bytes), 'sha256': digest(metadata_bytes)},
            {'key': local_manifest, 'sourceUrl': iiif_url, 'bytes': len(manifest_bytes), 'sha256': digest(manifest_bytes)},
        ])
        records.append({
            **source, 'title': title, 'provider': 'Wellcome Collection', 'workApiUrl': metadata_url,
            'iiifManifestUrl': iiif_url, 'canvasCount': len(iiif.get('items', [])),
            'rights': {'providerTerm': 'Public Domain Mark', 'rightsUrl': iiif['rights'],
                       'providerStatement': usage[-1],
                       'scope': 'Provider rights identification for this digitised work; preserve attribution and review local law/title-chain before any worldwide reuse claim.'},
            'sourceDeclaredMetadata': {'publication': metadata_value(iiif, 'Publication/creation'),
                                       'subjects': metadata_value(iiif, 'Subjects'),
                                       'type': metadata_value(iiif, 'Type/technique')},
            'acquisitionStatus': 'source-evidence-acquired; recipe extraction pending',
            'extractionBlocker': 'IIIF manifest has image canvases. Recipe boundaries, page OCR quality, recipe language per page, and a work-level reuse decision remain to be reviewed before recipe admission.',
        })
    (args.output / 'sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    sources_bytes = (args.output / 'sources.json').read_bytes()
    files.append({'key': 'sources.json', 'bytes': len(sources_bytes), 'sha256': digest(sources_bytes)})
    manifest = {
        'schemaVersion': 'offmenu-global-recipe-discovery/1', 'releaseId': 'recipe-global-discovery-20261014',
        'status': 'bounded-source-evidence-acquired-not-recipe-admitted',
        'complete': True, 'limit': None, 'sourceCount': len(records), 'rawRecipeRecords': 0,
        'acquisitionByteBudget': MAX_BYTES, 'acquiredBytes': sum(item['bytes'] for item in files),
        'duplicateCheck': 'No retained source ledger, recipe research report, or local dataset contained these Wellcome work/item identifiers at acquisition time.',
        'admissionBoundary': 'No recipe text, OCR, images, individual recipes, countries, dietary claims, quantities, or cultural origins are admitted by this discovery bundle.',
        'files': files, 'completedAt': datetime.now(timezone.utc).isoformat(),
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'output': str(args.output), 'sources': len(records), 'files': len(files), 'bytes': manifest['acquiredBytes']}))


if __name__ == '__main__':
    main()
