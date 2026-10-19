#!/usr/bin/env python3
"""Reconcile verified local OffMenu parse outputs into the origin/type register.

Reads local manifests and normalized JSONL.GZ outputs, validates record identity,
release, country evidence and source-file checksums where available, then writes
only sanitized metadata/record IDs into the register. Raw records and local paths
are never copied into generated artifacts.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get('OFFMENU_DATA_ROOT', Path.home() / 'src' / 'offmenu-data'))
REGISTER_DIR = ROOT / 'docs/coverage-register/2026-10-19'
BUILDER_PATH = ROOT / 'scripts/build-origin-type-register.py'

# These are existing source-faithful normalized outputs, not new downloads.
# The source ID and release ID are both required; URL equality never joins releases.
CORPORA = (
    ('mext-2023-main', 'food-composition', 'mext', '2023-corrected-20260327-main', 'mext-2023'),
    ('afcd-3', 'food-composition', 'afcd', '3', 'afcd'),
    ('cofid-2021', 'food-composition', 'cofid', '2021', 'cofid'),
    ('germany-bls-4.0', 'food-composition', 'germany-bls', '4.0', 'bls'),
    ('ciqual-2025', 'food-composition', 'ciqual', '2025', 'ciqual'),
    ('matvaretabellen-2026', 'food-composition', 'matvaretabellen', '2026', 'norway'),
    ('frida-5.5', 'food-composition', 'frida', '5.5', 'frida'),
    ('cnf-2015', 'food-composition', 'cnf', '2015', 'cnf-2015'),
    ('fineli-20.0', 'food-composition', 'fineli', '20.0', None),
    ('sweden-food-2026-07-01', 'food-composition', 'sweden-food', '2026-07-01', None),
    ('foodfiles-2024-v01', 'food-composition', 'foodfiles', '2024-v01', None),
    ('world-recipes-global-20261014', 'recipes', 'world-recipes', 'world-recipes-global-20261014', None),
)
LOCAL_PATH_RE = re.compile(r'(?:(?<![A-Za-z0-9+.-])(?:/home/|/srv/|/workspace/)[^\s\"\']+)')
VALID_ISO2 = re.compile(r'^[A-Z]{2}$')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')


def sanitize(value: Any) -> Any:
    """Redact local filesystem references recursively before publication."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in {'path', 'localPath', 'rawPath', 'originalPath'} and isinstance(item, str) and item.startswith('/'):
                continue
            out[key] = sanitize(item)
        return out
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return LOCAL_PATH_RE.sub('[private-local-path-omitted]', value)
    return value


def record_list(value: Any) -> list[dict]:
    if isinstance(value, list) and all(isinstance(row, dict) for row in value):
        return value
    if isinstance(value, dict):
        return [value]
    raise ValueError('normalized output line is not a record or record list')


def resolve_original(corpus_dir: Path, originals_subdir: str | None, key: str) -> Path | None:
    candidates = [corpus_dir / key]
    if originals_subdir:
        candidates.append(DATA_ROOT / 'national-originals' / originals_subdir / key)
    candidates.append(DATA_ROOT / 'national-originals' / key)
    return next((p for p in candidates if p.is_file()), None)


def load_builder():
    spec = importlib.util.spec_from_file_location('origin_type_register_builder', BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('could not load origin/type register builder')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_corpus(entry: tuple[str, str, str, str, str | None], countries: set[str],
                   originals_subdir: str | None, asset_hash_index: dict[str, list[str]]) -> dict:
    dirname, family, source_id, release_id, default_originals = entry
    corpus_dir = DATA_ROOT / dirname
    manifest_path = corpus_dir / 'manifest.json'
    output_path = corpus_dir / 'normalized.jsonl.gz'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get('sourceId') != source_id or str(manifest.get('releaseId')) != release_id:
        raise ValueError(f'{dirname}: manifest source/release mismatch')
    if manifest.get('status') != 'normalized':
        raise ValueError(f'{dirname}: output is not marked normalized')
    output_sha = sha256_file(output_path)
    records_by_origin: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    seen_ids: set[str] = set()
    record_count = 0
    bad_country_records = 0
    missing_identity_records = 0
    urls: set[str] = set()
    original_results: list[dict] = []
    source_files = manifest.get('sourceFiles')
    originals_dir = originals_subdir if originals_subdir is not None else default_originals
    if isinstance(source_files, list):
        for item in source_files:
            if not isinstance(item, dict) or not isinstance(item.get('key'), str):
                raise ValueError(f'{dirname}: malformed sourceFiles entry')
            path = resolve_original(corpus_dir, originals_dir, item['key'])
            if path is None:
                original_results.append({'key': item['key'], 'status': 'unavailable', 'sha256': item.get('sha256')})
                continue
            actual = sha256_file(path)
            expected = item.get('sha256')
            # A changed acquisition note is reported as a mismatch; it never
            # invalidates independently matching publisher data-file hashes.
            original_results.append({'key': item['key'], 'status': 'verified' if actual == expected else 'checksum-mismatch',
                                     'sha256': actual, 'expectedSHA256': expected, 'bytes': path.stat().st_size})
    elif source_files is not None:
        raise ValueError(f'{dirname}: sourceFiles must be an array when present')

    with gzip.open(output_path, 'rt', encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                rows = record_list(json.loads(line))
            except Exception as exc:
                raise ValueError(f'{dirname}: invalid JSONL line {line_number}: {exc}') from exc
            for record in rows:
                record_count += 1
                rid = record.get('id')
                provenance = record.get('provenance') or {}
                data = record.get('data') or {}
                if not isinstance(rid, str) or not rid or rid in seen_ids:
                    raise ValueError(f'{dirname}: missing or duplicate record ID at line {line_number}')
                seen_ids.add(rid)
                if provenance.get('sourceId') != source_id or str(provenance.get('releaseId')) != release_id:
                    raise ValueError(f'{dirname}: record provenance source/release mismatch for {rid}')
                countries_field = record.get('countries')
                if not isinstance(countries_field, list):
                    bad_country_records += 1
                    continue
                explicit_countries = sorted({c for c in countries_field if isinstance(c, str) and VALID_ISO2.fullmatch(c) and c in countries})
                if len(explicit_countries) != len(set(countries_field)):
                    bad_country_records += 1
                if family == 'food-composition':
                    if record.get('kind') != 'nutrientProfile':
                        raise ValueError(f'{dirname}: unexpected composition record kind for {rid}')
                    if not data.get('foodName') or not data.get('identifiers'):
                        missing_identity_records += 1
                    eligible_types = ['food_composition']
                    if data.get('foodName') and data.get('identifiers'):
                        eligible_types.append('food_identity')
                else:
                    if record.get('kind') != 'recipe':
                        raise ValueError(f'{dirname}: unexpected recipe record kind for {rid}')
                    # Only explicit country codes that agree with the source's
                    # declared cuisine-country field are accepted for country links.
                    cuisine_country = data.get('sourceCuisineCountry')
                    if explicit_countries and (not isinstance(cuisine_country, str) or explicit_countries != [cuisine_country]):
                        explicit_countries = []
                        bad_country_records += 1
                    eligible_types = ['recipes']
                url = provenance.get('url')
                if isinstance(url, str) and url.startswith(('http://', 'https://')):
                    urls.add(url)
                for origin in explicit_countries:
                    for kind in eligible_types:
                        records_by_origin[(origin, kind)].append({
                            'recordId': rid,
                            'citation': {'url': url, 'sourceId': source_id, 'releaseId': release_id,
                                         'attribution': provenance.get('attribution') or manifest.get('attribution'),
                                         'license': provenance.get('license') or manifest.get('license')},
                        })
    expected_count = manifest.get('normalizedRows')
    if expected_count is None:
        expected_count = (manifest.get('counts') or {}).get('records')
    if expected_count is not None and record_count != expected_count:
        raise ValueError(f'{dirname}: manifest row count {expected_count} != parsed JSONL count {record_count}')
    if record_count != len(seen_ids):
        raise ValueError(f'{dirname}: record count/unique ID mismatch')
    if not record_count:
        raise ValueError(f'{dirname}: empty normalized output')
    input_verified = sum(x['status'] == 'verified' for x in original_results)
    input_mismatches = [x for x in original_results if x['status'] == 'checksum-mismatch']
    input_unavailable = [x for x in original_results if x['status'] == 'unavailable']
    return {
        'directory': dirname, 'family': family, 'sourceId': source_id, 'releaseId': release_id,
        'manifest': manifest, 'manifestSHA256': hashlib.sha256(manifest_bytes).hexdigest(),
        'outputSHA256': output_sha, 'outputBytes': output_path.stat().st_size,
        'recordCount': record_count, 'recordIds': sorted(seen_ids),
        'countries': sorted({origin for origin, _ in records_by_origin}),
        'recordLinks': records_by_origin, 'sourceURLs': sorted(urls),
        'sourceFiles': original_results,
        'verifiedSourceFileCount': input_verified, 'sourceFileCount': len(original_results),
        'sourceFileMismatches': input_mismatches, 'sourceFilesUnavailable': input_unavailable,
        'badCountryRecords': bad_country_records, 'missingIdentityRecords': missing_identity_records,
        'manifestOriginalInputVerification': ('all-source-files-verified' if original_results and input_verified == len(original_results)
                                              else 'source-inputs-partially-verified' if input_verified
                                              else 'source-input-hashes-not-pinned'),
    }


def apply(report: dict, datasets: list[dict]) -> dict:
    cells = {(row['origin'], row['type']): row for row in report['coverage']}
    assets = {row['assetId']: row for row in report['assets']}
    by_type: dict[str, set[str]] = collections.defaultdict(set)
    distinct_record_links = 0
    for dataset in datasets:
        manifest = dataset['manifest']
        asset_id = 'parsed-release:' + dataset['sourceId'] + ':' + dataset['releaseId'] + ':' + dataset['outputSHA256'][:16]
        linked_cells = []
        records_by_cell = dataset['recordLinks']
        for (origin, kind), records in sorted(records_by_cell.items()):
            key = (origin, kind)
            if key not in cells:
                raise ValueError(f'parsed link falls outside required matrix: {origin}/{kind}')
            row = cells[key]
            existing = set(row.get('parsedRecordIds') or [])
            additions = [r['recordId'] for r in records if r['recordId'] not in existing]
            if len(additions) != len(records):
                raise ValueError(f'duplicate parsed record link in {origin}/{kind}')
            row['parsedRecordIds'].extend(additions)
            row['parsedRecordIds'].sort()
            row['parseStatus'] = 'parsed-usable'
            row.setdefault('evidence', {}).setdefault('parsedOutputs', []).append(asset_id)
            row['evidence']['explicitRecordCountryEvidence'] = ('source record countries[]; recipe origin also agrees with sourceCuisineCountry'
                                                                  if dataset['family'] == 'recipes'
                                                                  else 'source record countries[] from the national composition reference; this is availability/reference scope, not food origin')
            row['sources']['parsedOutputAssetIds'] = sorted(set(row['sources'].get('parsedOutputAssetIds', [])) | {asset_id})
            row['sources']['allSourceAssetIds'] = sorted(set(row['sources'].get('allSourceAssetIds', [])) | {asset_id})
            if asset_id not in row['sources']['boundAssetIds']:
                row['sources'].setdefault('parsedOutputAssetIds', [])
            row['gaps'] = [gap for gap in row.get('gaps', []) if 'actual parsed records' not in gap]
            row['gaps'] = sorted(set(row.get('gaps', [])) | {'Coverage is partial to the source release and explicit record scope; this does not establish exhaustive origin/type coverage.'})
            linked_cells.append(f'{origin}/{kind}')
            by_type[kind].add(asset_id)
            distinct_record_links += len(records)
        raw_sources = manifest.get('sourceFiles') if isinstance(manifest.get('sourceFiles'), list) else []
        member_ids = sorted({aid for source in raw_sources for aid in dataset.get('assetHashIndex', {}).get(source.get('sha256'), [])})
        pub = manifest.get('attribution') or manifest.get('sourceId')
        credit = manifest.get('license') or 'See publisher source terms; no new permissions are inferred.'
        output_url = dataset['sourceURLs'][:50]
        citation_groups: dict[tuple[str, str, str, str, str], int] = collections.Counter()
        record_country_counts = collections.Counter()
        for (origin, kind), records in records_by_cell.items():
            record_country_counts[origin] += len(records)
            for record in records:
                citation = record['citation']
                citation_groups[(citation.get('url') or '', citation.get('sourceId') or '', citation.get('releaseId') or '', citation.get('attribution') or '', citation.get('license') or '')] += 1
        source_citations = [
            {'url': url or None, 'sourceId': sid or None, 'releaseId': rel or None,
             'attribution': attribution or None, 'license': license or None, 'linkedRecordCount': count}
            for (url, sid, rel, attribution, license), count in sorted(citation_groups.items())
        ]
        unique_citation_count = len(source_citations)
        citation_group_truncated = len(source_citations) > 50
        source_citations = source_citations[:50]
        row = {
            'assetId': asset_id,
            'identityBasis': 'sourceId+exact releaseId+verified normalized-output SHA256; different releases remain distinct',
            'aliases': [], 'publisher': pub,
            'citation': {'name': pub, 'sourceId': dataset['sourceId'], 'releaseId': dataset['releaseId'],
                         'license': manifest.get('license'), 'attribution': manifest.get('attribution'),
                         'sourceURLs': output_url, 'citationCount': unique_citation_count,
                         'recordCitationGroups': source_citations, 'citationGroupsTruncated': citation_group_truncated,
                         'recordCitationEvidence': 'Each linked record retains its own provenance URL, release ID, license and attribution in the existing private-local corpus.'},
            'sourceURLs': output_url,
            'assetIdentity': {'publisherSourceIds': [dataset['sourceId']], 'releaseKeys': [dataset['releaseId']],
                              'requestVariants': [], 'contentHashes': sorted({dataset['outputSHA256'], *[x['sha256'] for x in dataset['sourceFiles'] if x.get('sha256')]}),
                              'identityCaveat': 'Exact release and output digest are recorded; source-file hashes are included where source manifest and local bytes were verified.'},
            'release': [{'releaseId': dataset['releaseId'], 'sourceId': dataset['sourceId']}],
            'format': ['gzip-compressed JSON Lines'],
            'accessConditions': {'accessLabel': 'publisher source terms retained in the manifest; review status is not broadened by parsing',
                                 'sourceUseDisposition': 'local-normalized-output; source licence remains applicable',
                                 'holds': [], 'researchReuseClearance': 'not-reassessed-by-this-local-integrity-check'},
            'downloadMethod': {'method': 'reused-existing-local-corpus', 'evidence': 'Existing source-release manifest plus verified normalized output hash; no network request in this reconciliation.',
                               'nextAction': 'Source-specific currentness, reuse permissions and full product acceptance remain separate review gates.'},
            'custody': {'state': 'verified-local-normalized-output', 'localStorage': 'Foo; raw originals and parsed corpus remain local',
                        'outputSHA256': dataset['outputSHA256'], 'outputBytes': dataset['outputBytes'],
                        'originalInputVerification': dataset['manifestOriginalInputVerification'],
                        'sourceFilesVerified': dataset['verifiedSourceFileCount'], 'sourceFilesDeclared': dataset['sourceFileCount'],
                        'sourceFileMismatchCount': len(dataset['sourceFileMismatches']), 'sourceFilesUnavailableCount': len(dataset['sourceFilesUnavailable']),
                        'privateLocalPathsPublished': False},
            'manifestDisposition': 'existing-normalized-source-release',
            'manifestBindings': {'sourceManifestAssetIds': member_ids},
            'countryHints': dataset['countries'], 'typeHints': [dataset['family']], 'proposedTypes': sorted({k for _, k in records_by_cell}),
            'scope': 'explicit-record-country-scopes-only', 'countryFanoutAllowed': False,
            'sourceStatus': 'verified-parsed-output-reused-local',
            'evidence': {'manifestSHA256': dataset['manifestSHA256'], 'normalizedOutputSHA256': dataset['outputSHA256'],
                         'recordCount': dataset['recordCount'], 'countryRecordCounts': dict(sorted(record_country_counts.items())),
                         'memberSourceAssetIds': member_ids, 'recordCitationCount': unique_citation_count,
                         'countryAssignmentPolicy': ('Only top-level countries[] that agrees with data.sourceCuisineCountry is linked; absent country remains unknown.'
                                                     if dataset['family'] == 'recipes' else
                                                     'Only the source record countries[] field is linked; country is reference availability, not ingredient origin.'),
                         'sourceFileSHA256s': dataset['sourceFiles']},
            'gaps': ['This release is a verified parse output, not proof of all applicable sources, country-origin evidence, normalized semantics or complete product coverage.'],
            'nextAction': 'Review source applicability, permissions, other required datasets and product-specific acceptance; do not infer country scope beyond explicit record fields.',
            'parsedRecordCount': dataset['recordCount'], 'parsedOutputRecordCitations': source_citations,
            'parsedOutputRecordCitationGroupsTruncated': citation_group_truncated,
            'parsedSourceFileAssetIds': member_ids, 'coverageLinks': sorted(set(linked_cells)),
        }
        assets[asset_id] = row
        for member_id in member_ids:
            if member_id in assets:
                asset = assets[member_id]
                asset.setdefault('parsedOutputLinks', []).append(asset_id)
                asset['parsedOutputLinks'] = sorted(set(asset['parsedOutputLinks']))
    report['assets'] = sorted(assets.values(), key=lambda x: x['assetId'])
    # Keep every existing rights/custody blocker; parsing does not clear holds.
    # Do not publish any private machine-local path from the source inventory.
    report = sanitize(report)
    report['taxonomyReconciliation'] = {
        'ingredients': {'representedBy': ['food_identity', 'food_composition', 'recipes'],
                        'evidence': 'Food-composition records carry source food names and identifiers; recipe records carry source ingredient expressions. These roles are not asserted equivalent and recipe strings are not canonical ingredient IDs.'},
        'recipes': {'representedBy': 'recipes', 'evidence': 'Source-faithful recipe records; only source cuisine-country records with explicit country metadata are linked to country cells.'},
        'otherTypes': 'The remaining 10 taxonomy categories are maintained as separate product requirements and are not satisfied by food composition/recipe corpora.'},
    existing_counts = report['counts']
    existing_counts['uniqueAssetsInRegister'] = len(report['assets'])
    existing_counts['uniqueAssetsParsedWithUsableRecords'] = len(datasets)
    existing_counts['uniqueAssetsReusedAndVerified'] = len(datasets)
    existing_counts['uniqueAssetsFetchedAndVerified'] = 0
    existing_counts['uniqueAssetsNewlyDownloaded'] = 0
    existing_counts['uniqueParsedRecordLinks'] = distinct_record_links
    existing_counts['entriesWithParsedRecords'] = sum(bool(row['parsedRecordIds']) for row in report['coverage'])
    existing_counts['entriesComplete'] = 0
    existing_counts['manyToManyCoverageLinks'] = sum(len(a.get('coverageLinks') or []) for a in report['assets'])
    existing_counts['parsedOutputAssets'] = len(datasets)
    existing_counts['sourceFilesIndependentlyVerified'] = sum(d['verifiedSourceFileCount'] for d in datasets)
    existing_counts['sourceFileChecksumMismatches'] = sum(len(d['sourceFileMismatches']) for d in datasets)
    existing_counts['sourceFilesUnavailable'] = sum(len(d['sourceFilesUnavailable']) for d in datasets)
    existing_counts['uniqueSourceURLs'] = len({url for a in report['assets'] for url in a.get('sourceURLs', [])})
    counts_by_status = collections.Counter(a['sourceStatus'] for a in report['assets'])
    existing_counts['assetsByStatus'] = dict(sorted(counts_by_status.items()))
    for kind, entry in report['coverageByType'].items():
        cells_of_type = [r for r in report['coverage'] if r['type'] == kind]
        entry['entriesWithParsedRecords'] = sum(bool(r['parsedRecordIds']) for r in cells_of_type)
        entry['parsedRecordLinks'] = sum(len(r['parsedRecordIds']) for r in cells_of_type)
        entry['parsedOutputAssets'] = len(by_type[kind])
        entry['complete'] = 0
    report['sourceParseReconciliation'] = {
        'schemaVersion': 'offmenu-source-parse-reconciliation/1',
        'uniqueParsedOutputReleases': [{k: d[k] for k in ['directory', 'sourceId', 'releaseId', 'recordCount', 'manifestSHA256', 'outputSHA256', 'outputBytes', 'countries', 'manifestOriginalInputVerification', 'verifiedSourceFileCount', 'sourceFileCount', 'badCountryRecords', 'missingIdentityRecords']} for d in datasets],
        'integrityPolicy': 'Each normalized gzip JSONL was fully decompressed and every record JSON/provenance/release/unique ID checked; declared original source-file hashes were rechecked where manifest entries and local inputs were available.',
        'geographicPolicy': 'No record was assigned to GLOBAL or a country from collection name, URL host, publisher location or absent country metadata. Country links use explicit per-record ISO codes; recipe country scope must also equal sourceCuisineCountry.',
        'rawOriginalsPublished': False, 'normalizedBodiesPublished': False, 'networkRequests': 0,
    }
    report['status'] = '250x13-matrix-complete-local-parsed-evidence-reconciled-coverage-partial'
    report['limitations'] = list(report.get('limitations', [])) + [
        'This reconciliation reuses existing local normalized release outputs; it performs no network acquisition and does not prove currentness or legal reuse beyond the retained manifests.',
        'Only explicit record country evidence is linked. National composition country codes describe reference-table scope, not the origin of each food.',
        'Recipes without explicit source country metadata remain unassigned; no global or country fan-out is inferred.',
        'Source coverage is partial; unsupported required information types and countries remain discovery gaps. No origin/type entry is claimed complete.',
        'Private original paths, normalized corpus paths and raw source bodies are omitted from this sanitized register.',
    ]
    return report


def verify_no_private_paths(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values(): verify_no_private_paths(item)
    elif isinstance(value, list):
        for item in value: verify_no_private_paths(item)
    elif isinstance(value, str) and LOCAL_PATH_RE.search(value):
        raise ValueError('sanitized output contains a private local path')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=REGISTER_DIR)
    parser.add_argument('--originals-subdir', action='append', default=[], metavar='CORPUS=SUBDIR')
    args = parser.parse_args(argv)
    overrides = {}
    for item in args.originals_subdir:
        if '=' not in item: raise SystemExit('--originals-subdir must be CORPUS=SUBDIR')
        key, value = item.split('=', 1); overrides[key] = value
    builder = load_builder()
    report = builder.build()
    original_assets = {a['assetId']: a for a in report['assets']}
    hash_index: dict[str, list[str]] = collections.defaultdict(list)
    for asset in original_assets.values():
        for digest in asset.get('assetIdentity', {}).get('contentHashes', []): hash_index[digest].append(asset['assetId'])
    datasets = [inspect_corpus(spec, set(report['origins']) - {'GLOBAL'}, overrides.get(spec[0], spec[4]), hash_index) for spec in CORPORA]
    for dataset in datasets: dataset['assetHashIndex'] = hash_index
    report = apply(report, datasets)
    builder.validate(report)
    verify_no_private_paths(report)
    # Stable and independently consumable sanitized outputs.
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / 'coverage-register.json').write_bytes(canonical(report))
    (out / 'origin-type-coverage.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in report['coverage']), encoding='utf-8')
    (out / 'unique-assets.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in report['assets']), encoding='utf-8')
    (out / 'source-blockers.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in report['blockers']), encoding='utf-8')
    result = {'status': report['status'], 'counts': report['counts'], 'coverageByType': report['coverageByType'],
              'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha256_file(p)} for p in sorted(out.iterdir()) if p.is_file()}}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'parsed-coverage-reconcile-failed: {exc}', file=sys.stderr)
        raise SystemExit(2)
