#!/usr/bin/env python3
"""Reconcile a local parse run with an inventory without forcing fuzzy joins."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit

HEX64 = re.compile(r'^[0-9a-f]{64}$')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    host = (parts.hostname or '').casefold()
    port = parts.port
    netloc = host + (f':{port}' if port and port not in (80, 443) else '')
    path = parts.path or '/'
    if path != '/':
        path = path.rstrip('/')
    return urlunsplit((parts.scheme.casefold(), netloc, path, parts.query, ''))


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield None, item
            else:
                yield from _walk(item)


def _urls(record: dict) -> set[str]:
    urls = set()
    for key, value in _walk(record):
        if isinstance(value, str) and value.startswith(('http://', 'https://')):
            urls.add(normalize_url(value))
        elif isinstance(value, str) and key == 'requestVariants':
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            for _, nested in _walk(parsed):
                if isinstance(nested, str) and nested.startswith(('http://', 'https://')):
                    urls.add(normalize_url(nested))
    return urls


def _original_hashes(record: dict) -> set[str]:
    hashes = set()
    identity = record.get('assetIdentity') or {}
    hashes.update(x for x in identity.get('contentHashes', []) if isinstance(x, str) and HEX64.fullmatch(x))
    custody = record.get('custody') or {}
    for item in custody.get('retainedOriginals', []) or []:
        if isinstance(item, dict) and isinstance(item.get('sha256'), str) and HEX64.fullmatch(item['sha256']):
            hashes.add(item['sha256'])
    single = custody.get('retainedOriginal')
    if isinstance(single, dict) and isinstance(single.get('sha256'), str) and HEX64.fullmatch(single['sha256']):
        hashes.add(single['sha256'])
    return hashes


def _release_values(record: dict) -> set[str]:
    values = set()
    release = record.get('release')
    if isinstance(release, str):
        values.add(release)
    elif isinstance(release, list):
        values.update(x for x in release if isinstance(x, str))
    for item in (record.get('assetIdentity') or {}).get('releaseKeys', []) or []:
        if isinstance(item, str):
            values.add(item)
        elif isinstance(item, dict):
            for key in ('publisherRelease', 'observationPeriod'):
                if isinstance(item.get(key), str):
                    values.add(item[key])
    return values


def _family_key(url: str) -> tuple[str, str] | None:
    parts = urlsplit(url)
    path = parts.path.casefold()
    if parts.hostname and parts.hostname.casefold() == 'www.eatforhealth.gov.au' and path.startswith('/eating-well/healthy-recipes/'):
        return ('www.eatforhealth.gov.au', '/eating-well/healthy-recipes')
    return None


def _inventory_matches_url(asset: dict, normalized_source: str | None) -> list[dict]:
    matches = []
    for candidate in asset.get('sourceURLs') or []:
        if isinstance(candidate, str) and normalized_source and normalize_url(candidate) == normalized_source:
            matches.append({'field': 'sourceURLs', 'url': candidate})
    for variant in (asset.get('assetIdentity') or {}).get('requestVariants', []) or []:
        if not isinstance(variant, str):
            continue
        try:
            parsed = json.loads(variant)
        except json.JSONDecodeError:
            continue
        for key, value in _walk(parsed):
            if key == 'url' and isinstance(value, str) and normalized_source and normalize_url(value) == normalized_source:
                matches.append({'field': 'assetIdentity.requestVariants', 'url': value})
    return matches


def _receipt_entries(label: str, receipt: dict) -> list[dict]:
    entries = receipt.get('files')
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    if isinstance(receipt.get('path'), str):
        return [receipt]
    return []


def _find_receipt(run_item: dict, receipts: list[tuple[str, dict]]) -> tuple[str, dict, dict] | None:
    run_path = Path(run_item.get('inputPath', ''))
    run_hash = run_item.get('inputSHA256')
    matches = []
    for label, receipt in receipts:
        for entry in _receipt_entries(label, receipt):
            entry_path = entry.get('path')
            # Use exact resolved receipt paths where possible; filename equality
            # is insufficient for archives with repeated member names.
            same_path = bool(entry_path and run_path and
                             Path(entry_path).resolve() == run_path.resolve())
            same_hash = bool(run_hash and entry.get('sha256') == run_hash)
            if same_hash or same_path:
                matches.append((label, receipt, entry))
    # Ambiguous receipt ties remain unresolved rather than taking the first.
    return matches[0] if len(matches) == 1 else None


def _selection_lineage(run_item: dict, receipts: list[tuple[str, dict]]) -> list[dict]:
    """Join receipt-selectedFrom references to their exact parent receipt files."""
    run_path = Path(run_item.get('inputPath', ''))
    child_receipts = []
    for label, receipt in receipts:
        for entry in _receipt_entries(label, receipt):
            path = entry.get('path')
            if path and Path(path).resolve() == run_path.resolve():
                child_receipts.append((label, receipt, entry))
    lineage = []
    for label, receipt, entry in child_receipts:
        selected = entry.get('selectedFrom')
        if not isinstance(selected, dict):
            continue
        selected_path = selected.get('path')
        selected_sha = selected.get('sha256')
        parent_matches = []
        for parent_label, parent_receipt in receipts:
            for parent_entry in _receipt_entries(parent_label, parent_receipt):
                if not selected_path or not parent_entry.get('path'):
                    continue
                exact_path = Path(parent_entry['path']).resolve() == Path(selected_path).resolve()
                hash_match = bool(selected_sha and parent_entry.get('sha256') == selected_sha)
                if exact_path and (not selected_sha or hash_match):
                    parent_matches.append({'receiptName': parent_label,
                        'sourceURL': parent_entry.get('url') or parent_entry.get('sourceURL'),
                        'release': parent_entry.get('release'),
                        'kind': parent_entry.get('kind'), 'pathBasename': Path(selected_path).name,
                        'sha256': parent_entry.get('sha256'),
                        'selectedFromChecksumMatchesParentReceipt': hash_match})
        lineage.append({'relation': 'receipt-selectedFrom-lineage',
            'childReceiptName': label,
            'selectionEvidence': {'pathBasename': Path(selected_path).name if selected_path else None,
                                  'sha256': selected_sha},
            'parentReceiptCandidates': parent_matches,
            'parentReceiptMatchCount': len(parent_matches)})
    return lineage


def _receipt_url(receipt: dict, entry: dict) -> str | None:
    return (entry.get('sourceURL') or entry.get('url') or
            receipt.get('sourceURL') or receipt.get('url'))


def _receipt_release(receipt: dict, entry: dict):
    return entry.get('release') or receipt.get('release')


def _inventory_relation_for_url_release(exact_hits: list[dict]) -> str | None:
    if not exact_hits:
        return None
    if any(hit.get('releaseMatch') for hit in exact_hits):
        return 'exact-source-url-and-release'
    return 'same-exact-source-url-release-not-established'


def _url_release_candidates(source_url: str | None, release, inventory_assets: list[dict]) -> list[dict]:
    """Report same exact source URL even if checksums differ or release is unresolved."""
    normalized = normalize_url(source_url) if source_url else None
    requested_releases = set(release) if isinstance(release, list) else ({release} if isinstance(release, str) else set())
    candidates = []
    for asset in inventory_assets:
        refs = _inventory_matches_url(asset, normalized)
        if not refs:
            continue
        releases = _release_values(asset)
        candidates.append({'assetId': asset.get('assetId'), 'urlEvidence': refs,
            'releaseMatch': bool(requested_releases & releases),
            'requestedRelease': release, 'inventoryReleases': sorted(releases),
            'sourceStatus': asset.get('sourceStatus'),
            'custodyState': (asset.get('custody') or {}).get('state'),
            'contentChecksumMatch': bool(_original_hashes(asset))})
    return candidates


def _family_only(source_url: str | None, inventory_assets: list[dict]) -> list[dict]:
    family = _family_key(normalize_url(source_url)) if source_url else None
    candidates = []
    if family is None:
        return candidates
    for asset in inventory_assets:
        urls = _urls(asset)
        if any(_family_key(url) == family for url in urls):
            candidates.append({'assetId': asset.get('assetId'),
                'sourceURLs': sorted(urls), 'inventoryReleases': sorted(_release_values(asset)),
                'sourceStatus': asset.get('sourceStatus'),
                'custodyState': (asset.get('custody') or {}).get('state')})
    return candidates


def _find_claim_sha256(claim_path: str | None) -> str | None:
    if not claim_path:
        return None
    path = Path(claim_path)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        claim = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    for key in ('sha256', 'bodySHA256', 'sourceSHA256', 'contentSHA256'):
        value = claim.get(key) if isinstance(claim, dict) else None
        if isinstance(value, str) and HEX64.fullmatch(value):
            return value
    return None


def _find_parent_by_receipt_selection(parent: dict | None,
        receipts: list[tuple[str, dict]], inventory_assets: list[dict]) -> list[dict]:
    if not isinstance(parent, dict):
        return []
    path = parent.get('path')
    digest = parent.get('sha256')
    if not path:
        return []
    candidates = []
    for label, receipt in receipts:
        for entry in _receipt_entries(label, receipt):
            entry_path = entry.get('path')
            if entry_path and Path(entry_path).resolve() == Path(path).resolve():
                match = bool(digest and entry.get('sha256') == digest)
                candidates.append({'relation':'exact-parent-path-and-recorded-checksum' if match else 'exact-parent-path-checksum-not-confirmed',
                    'receiptName': label, 'sourceURL': entry.get('url') or entry.get('sourceURL'),
                    'release': entry.get('release'), 'kind': entry.get('kind'),
                    'parentChecksumMatch': match})
    for asset in inventory_assets:
        checksums = _original_hashes(asset)
        if digest and digest in checksums:
            candidates.append({'relation':'exact-parent-original-checksum',
                'assetId':asset.get('assetId'),'sourceURLs':sorted(_urls(asset)),
                'sourceStatus':asset.get('sourceStatus')})
    return candidates


def _inventory_match_groups(run_item: dict, receipt_match,
                            receipts: list[tuple[str, dict]],
                            inventory_assets: list[dict]) -> dict:
    """Reconcile receipt URL/release, claim lineage, and inventory checksum separately."""
    exact_url_release, checksum_hits, family_hits, parent_hits = [], [], [], []
    entry = receipt_match[2] if receipt_match else None
    receipt = receipt_match[1] if receipt_match else None
    source_url = _receipt_url(receipt, entry) if entry is not None else None
    release = _receipt_release(receipt, entry) if entry is not None else None
    claim_path = (entry.get('claimPath') or receipt.get('claim')) if entry is not None else None
    claim_sha = _find_claim_sha256(claim_path)
    parent = entry.get('selectedFrom') if entry is not None else None
    input_sha = run_item.get('inputSHA256')
    for asset in inventory_assets:
        refs = _inventory_matches_url(asset, normalize_url(source_url) if source_url else None)
        releases = _release_values(asset)
        hashes = _original_hashes(asset)
        release_match = bool(release and release in releases)
        checksum_hit = bool(input_sha and input_sha in hashes)
        claim_hit = bool(claim_sha and claim_sha in hashes)
        parent_sha = parent.get('sha256') if isinstance(parent, dict) else None
        parent_hit = bool(parent_sha and parent_sha in hashes)
        if refs:
            exact_url_release.append({'assetId':asset.get('assetId'),'urlEvidence':refs,
                'releaseMatch':release_match,'inventoryReleases':sorted(releases),
                'contentChecksumMatch':checksum_hit,'sourceStatus':asset.get('sourceStatus'),
                'custodyState':(asset.get('custody') or {}).get('state')})
        if checksum_hit or claim_hit:
            checksum_hits.append({'assetId':asset.get('assetId'),
                'localInputChecksumMatch':checksum_hit,'receiptClaimChecksumMatch':claim_hit,
                'sourceURLs':sorted(_urls(asset)),'inventoryReleases':sorted(releases),
                'sourceStatus':asset.get('sourceStatus')})
        if parent_hit:
            parent_hits.append({'assetId':asset.get('assetId'),
                'relation':'exact-recorded-parent-original-checksum',
                'sourceURLs':sorted(_urls(asset))})
        if not refs and not checksum_hit and not claim_hit and not parent_hit and _family_key(normalize_url(source_url)) if source_url else False:
            family = _family_key(normalize_url(source_url))
            if any(_family_key(url)==family for url in _urls(asset)):
                family_hits.append({'assetId':asset.get('assetId'),
                    'relation':'same-publisher-recipe-path-family-only',
                    'sourceURLs':sorted(_urls(asset)),'inventoryReleases':sorted(releases),
                    'sourceStatus':asset.get('sourceStatus'),
                    'custodyState':(asset.get('custody') or {}).get('state')})
    return {'sourceURL':source_url,'release':release,'claimPath':claim_path,
        'claimSHA256':claim_sha,'parent':parent,
        'exactURLRelease':exact_url_release,'checksum':checksum_hits,
        'family':family_hits,'parentInventory':parent_hits}


def reconcile(run_manifest: Path, inventory_path: Path,
              receipt_paths: list[Path]) -> dict:
    run_manifest = run_manifest.resolve(strict=True)
    inventory_path = inventory_path.resolve(strict=True)
    run = json.loads(run_manifest.read_text(encoding='utf-8'))
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    if run.get('schemaVersion') != 'offmenu-source-parse-run/1':
        raise ValueError('unsupported-run-manifest-schema')
    if inventory.get('schemaVersion') != 'offmenu-origin-type-coverage-register/1':
        raise ValueError('unsupported-inventory-schema')
    receipts = [(path.name, json.loads(path.read_text(encoding='utf-8')))
                for path in receipt_paths]
    inventory_assets = inventory.get('assets', [])
    report_assets = []
    for item in run.get('assets', []):
        run_path = Path(item.get('inputPath', ''))
        input_sha = item.get('inputSHA256')
        receipt_match = _find_receipt(item, receipts)
        source_url = None
        release = None
        claim = None
        parent = None
        receipt_label = None
        receipt_file_match = False
        source_id = None
        if receipt_match:
            receipt_label, receipt, entry = receipt_match
            source_id = receipt.get('id')
            source_url = entry.get('sourceURL') or entry.get('url') or receipt.get('url')
            release = entry.get('release') or receipt.get('release')
            claim_path = entry.get('claimPath') or receipt.get('claim')
            if claim_path:
                claim = Path(claim_path).stem
            parent = entry.get('selectedFrom')
            receipt_file_match = entry.get('sha256') == input_sha
            if not source_id:
                source_id = receipt.get('id') or receipt.get('owner')
        actual_hash = sha256_file(run_path) if run_path.is_file() and not run_path.is_symlink() else None
        exact_hits, checksum_hits, family_hits = [], [], []
        normalized_source = normalize_url(source_url) if source_url else None
        local_family = _family_key(normalized_source) if normalized_source else None
        for asset in inventory_assets:
            urls = _urls(asset)
            exact_url_refs = _inventory_matches_url(asset, normalized_source)
            hashes = _original_hashes(asset)
            releases = _release_values(asset)
            exact_url = bool(exact_url_refs)
            exact_sha = bool(input_sha and input_sha in hashes)
            exact_release = bool(release and release in releases)
            if exact_url:
                exact_hits.append({'assetId': asset.get('assetId'),
                    'urlMatch': True, 'urlEvidence': exact_url_refs,
                    'releaseMatch': exact_release,
                    'inventoryReleases': sorted(releases),
                    'contentChecksumMatch': exact_sha,
                    'sourceStatus': asset.get('sourceStatus'),
                    'custodyState': (asset.get('custody') or {}).get('state')})
            elif exact_sha:
                checksum_hits.append({'assetId': asset.get('assetId'),
                    'urlMatch': False, 'releaseMatch': exact_release,
                    'sourceURLs': sorted(urls), 'inventoryReleases': sorted(releases),
                    'sourceStatus': asset.get('sourceStatus')})
            if not exact_url and not exact_sha and local_family and local_family in {_family_key(u) for u in urls}:
                family_hits.append({'assetId': asset.get('assetId'),
                    'relation': 'same-publisher-recipe-path-family-only',
                    'sourceURLs': sorted(urls), 'inventoryReleases': sorted(releases),
                    'sourceStatus': asset.get('sourceStatus'),
                    'custodyState': (asset.get('custody') or {}).get('state')})
        parent_sha = parent.get('sha256') if isinstance(parent, dict) else None
        parent_lineage_hits = []
        if parent_sha:
            for asset in inventory_assets:
                if parent_sha in _original_hashes(asset):
                    parent_lineage_hits.append({'assetId': asset.get('assetId'),
                        'relation': 'exact-parent-original-checksum',
                        'sourceURLs': sorted(_urls(asset))})
        exact_match = any(h['releaseMatch'] for h in exact_hits)
        if exact_match:
            relation = 'exact-source-url-and-release'
        elif exact_hits:
            relation = 'same-exact-source-url-release-not-established'
        elif checksum_hits:
            relation = 'exact-content-checksum-url-or-release-not-established'
        elif parent_lineage_hits:
            relation = 'exact-recorded-parent-lineage-only'
        elif family_hits:
            relation = 'same-source-family-only-no-asset-match'
        else:
            relation = 'no-supported-inventory-relationship-found'
        report_assets.append({
            'assetId': f"{item.get('sourceId')}:{item.get('sourceRecordId')}",
            'sourceRecordId': item.get('sourceRecordId'),
            'sourceId': item.get('sourceId'),
            'kind': item.get('kind'),
            'inputBasename': run_path.name,
            'inputSHA256': input_sha,
            'inputBytesPresentAndHashVerified': actual_hash == input_sha,
            'receipt': {'name': receipt_label, 'sourceId': source_id,
                'inputChecksumMatchesReceipt': receipt_file_match,
                'sourceURL': source_url, 'release': release,
                'claimReference': claim,
                'parentSelectionReference': ({'sha256': parent_sha,
                    'basename': Path(parent.get('path', '')).name if parent.get('path') else None}
                    if isinstance(parent, dict) else None)},
            'inventoryRelation': relation,
            'exactURLCandidates': exact_hits,
            'exactChecksumCandidates': checksum_hits,
            'parentLineageCandidates': parent_lineage_hits,
            'sameFamilyOnlyCandidates': family_hits,
        })
    counts = {
        'inputs': len(report_assets),
        'receiptChecksumVerified': sum(x['receipt']['inputChecksumMatchesReceipt'] for x in report_assets),
        'localBytesHashVerified': sum(x['inputBytesPresentAndHashVerified'] for x in report_assets),
        'exactURLAndReleaseMatches': sum(x['inventoryRelation'] == 'exact-source-url-and-release' for x in report_assets),
        'exactURLButReleaseUnknownOrDifferent': sum(x['inventoryRelation'] == 'same-exact-source-url-release-not-established' for x in report_assets),
        'exactChecksumCandidates': sum(bool(x['exactChecksumCandidates']) for x in report_assets),
        'parentLineageCandidates': sum(bool(x['parentLineageCandidates']) for x in report_assets),
        'sameFamilyOnly': sum(x['inventoryRelation'] == 'same-source-family-only-no-asset-match' for x in report_assets),
        'noSupportedRelationship': sum(x['inventoryRelation'] == 'no-supported-inventory-relationship-found' for x in report_assets),
    }
    return {
        'schemaVersion': 'offmenu-source-inventory-lineage-reconciliation/1',
        'method': 'Exact canonical source URL, exact recorded release, exact original SHA-256, and exact recorded parent-source SHA-256; family relation is reported separately and never promoted to asset identity.',
        'inventory': {'schemaVersion': inventory.get('schemaVersion'),
                      'assetCount': len(inventory_assets),
                      'snapshotStatus': inventory.get('status')},
        'run': {'schemaVersion': run.get('schemaVersion'),
                'parserVersion': run.get('parserVersion'),
                'assetCount': len(run.get('assets', []))},
        'counts': counts,
        'assets': report_assets,
        'limitations': [
            'A source URL plus release can establish a candidate relationship when checksums differ; no checksum mismatch is treated as disproof.',
            'Same publisher/domain/path family is not an asset match.',
            'Archive-member/transformed lineage is asserted only when a recorded parent/source checksum or receipt explicitly establishes it.',
            'Inventory rows are the pinned snapshot; absent URL or lineage evidence means unresolved, not proof that no other inventory relationship exists.'
        ]
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-manifest', required=True, type=Path)
    ap.add_argument('--inventory', required=True, type=Path)
    ap.add_argument('--receipt', action='append', default=[], type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        report = reconcile(args.run_manifest, args.inventory, args.receipt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
        if args.output.exists():
            raise ValueError('output-already-exists')
        args.output.write_bytes(data)
        print(json.dumps({'status': 'complete', 'counts': report['counts'],
                          'sha256': hashlib.sha256(data).hexdigest()}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f'inventory-lineage-reconciliation-failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
