"""Pinned corrected product-detail import closure; no display/query/cache/label API.

Initial definitions/schema came verbatim from reviewed63dd92023; the writer now
adds explicit caller-transaction rejection and foreign-key enforcement preflight.
This module provides no real-source factory, admission, job or activation.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sqlite3
import time
from .core import canonical, strict_json, RefreshError
from . import product_detail_import_readers as readers


VERSION = 'offmenu-retained-product-detail-store/1'


DDL = "-- SOURCE CONTRACT ONLY, not executed.5tables/1view;26owns implementation.\nCREATE TABLE retained_reference_record(\n reference_record_id TEXT PRIMARY KEY NOT NULL,\n source_id TEXT NOT NULL, release_id TEXT NOT NULL,\n asset_id TEXT NOT NULL, asset_sha256 TEXT NOT NULL,\n source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),\n native_record_id TEXT, source_pointer TEXT NOT NULL,\n original_language TEXT NOT NULL, source_payload_json TEXT NOT NULL,\n parsed_record_sha256 TEXT NOT NULL,\n citation_id TEXT, citation_binding_status TEXT NOT NULL,\n parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL,\n processing_status TEXT NOT NULL,\n UNIQUE(asset_id,asset_sha256,source_ordinal)\n);\n-- NEW separate private product-detail generation only. Reference-record table reused exactly.\n-- No validated identifier DB mutation, scanner11986 change or source body access by13.\nCREATE TABLE product_detail_generation(\n generation_id TEXT PRIMARY KEY NOT NULL,\n input_manifest_sha256 TEXT NOT NULL,\n schema_version TEXT NOT NULL,\n projection_version TEXT NOT NULL,\n operation_selection_sha256 TEXT NOT NULL,\n state TEXT NOT NULL CHECK(state IN ('loading','incomplete','completed','failed')),\n coverage_scope_json TEXT NOT NULL,\n expected_asset_count INTEGER CHECK(expected_asset_count>=0),\n processed_asset_count INTEGER CHECK(processed_asset_count>=0),\n product_records INTEGER CHECK(product_records>=0),\n profile_records INTEGER CHECK(profile_records>=0),\n exceptions_json TEXT NOT NULL,\n created_at TEXT NOT NULL, modified_at TEXT, removed_at TEXT, created_by TEXT,\n owner_actor_reference TEXT, access_policy_reference TEXT\n);\nCREATE TABLE product_detail_projection(\n reference_record_id TEXT PRIMARY KEY NOT NULL REFERENCES retained_reference_record(reference_record_id),\n generation_id TEXT NOT NULL REFERENCES product_detail_generation(generation_id),\n record_kind TEXT NOT NULL CHECK(record_kind IN ('product','nutrientProfile')),\n paired_profile_reference TEXT REFERENCES retained_reference_record(reference_record_id),\n source_binding_json TEXT NOT NULL,\n fields_json TEXT,\n projection_limitations_json TEXT NOT NULL,\n canonical_ingredient_id TEXT,\n semantic_mapping_status TEXT NOT NULL,\n record_disposition TEXT NOT NULL\n);\nCREATE TABLE product_detail_identifier(\n reference_record_id TEXT NOT NULL REFERENCES retained_reference_record(reference_record_id),\n identifier_ordinal INTEGER NOT NULL CHECK(identifier_ordinal>=1),\n namespace TEXT COLLATE BINARY,\n lexical_value TEXT COLLATE BINARY,\n disposition TEXT NOT NULL,\n source_pointer TEXT NOT NULL,\n PRIMARY KEY(reference_record_id,identifier_ordinal)\n);\nCREATE TABLE product_detail_observation_bridge(\n bridge_id TEXT PRIMARY KEY NOT NULL,\n identifier_database_sha256 TEXT NOT NULL,\n identifier_run_id TEXT NOT NULL,\n identifier_input_id TEXT NOT NULL,\n identifier_record_ordinal INTEGER NOT NULL CHECK(identifier_record_ordinal>=1),\n identifier_assertion_id INTEGER NOT NULL CHECK(identifier_assertion_id>=1),\n reference_record_id TEXT REFERENCES retained_reference_record(reference_record_id),\n bridge_state TEXT NOT NULL CHECK(bridge_state IN ('matched','not-loaded','ambiguous','restricted')),\n exact_link_evidence_json TEXT NOT NULL,\n CHECK(bridge_state<>'matched' OR reference_record_id IS NOT NULL)\n);\nCREATE INDEX product_detail_key_lookup ON product_detail_identifier(namespace,lexical_value,reference_record_id);\nCREATE INDEX product_detail_generation_records ON product_detail_projection(generation_id,record_kind,reference_record_id);\nCREATE INDEX product_detail_exact_observation ON product_detail_observation_bridge(identifier_database_sha256,identifier_run_id,identifier_input_id,identifier_record_ordinal,identifier_assertion_id,bridge_id);\nCREATE INDEX product_detail_source ON retained_reference_record(source_id,release_id,native_record_id,source_ordinal);\nCREATE VIEW v_source_product_details AS\nSELECT p.generation_id,r.reference_record_id,r.source_id,r.release_id,r.native_record_id,\n r.asset_id,r.asset_sha256,r.source_ordinal,r.source_pointer,r.parsed_record_sha256,\n r.original_language,r.citation_id,r.citation_binding_status,\n p.record_kind,p.paired_profile_reference,p.source_binding_json,p.fields_json,\n p.projection_limitations_json,p.canonical_ingredient_id,p.semantic_mapping_status,p.record_disposition\nFROM retained_reference_record r JOIN product_detail_projection p USING(reference_record_id);\n"


@dataclass(frozen=True)
class ProductDetailStoreLimits:
    max_assets: int
    max_input_bytes: int
    max_records: int
    max_record_bytes: int
    max_database_bytes: int
    max_seconds: int


def _fail(code): raise RefreshError('product-detail-' + code)


def _sha(value): return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def _hash(value): return hashlib.sha256(canonical(value)).hexdigest()


def _id(*values): return 'urn:offmenu:product-detail:' + _hash(list(values))


def prepare_product_detail_manifest(assets):
    """Pure finite metadata; no path stat/open or source-use authority inference."""
    if type(assets) not in (list, tuple) or not 1 <= len(assets) <= 1024: _fail('asset-bound')
    selected = []; seen = set()
    for original in assets:
        a = strict_json(canonical(original))
        if type(a) is not dict: _fail('asset-schema')
        for name in ('assetId', 'sourceId', 'releaseId', 'inputPath', 'identifierInputId', 'projectionVersion', 'citationStatus'):
            if type(a.get(name)) is not str or not 0 < len(a[name]) <= 4096: _fail('asset-schema')
        if (a['sourceId'] not in ('off', 'usda-files') or not Path(a['inputPath']).is_absolute()
                or any(not _sha(a.get(k)) for k in ('inputSHA256', 'identifierAssetSHA256', 'originalSHA256'))
                or type(a.get('inputBytes')) is not int or not 0 < a['inputBytes'] <= 1024**4
                or type(a.get('products')) is not int or a['products'] <= 0
                or type(a.get('profiles')) is not int or not 0 <= a['profiles'] <= a['products']
                or a.get('representation') not in ('off-legacy-paired-gzip', 'usda-native-jsonl', 'off-cached-qualified-pair', 'usda-reviewed-lookup-products-json')
                or (a['representation'].startswith('off-') != (a['sourceId'] == 'off'))): _fail('asset-schema')
        for name in ('rightsReceiptSHA256', 'custodyReceiptSHA256'):
            if a.get(name) is not None and not _sha(a[name]): _fail('asset-evidence')
        if a.get('citationId') is not None and type(a['citationId']) is not str: _fail('asset-evidence')
        key = (a['sourceId'], a['releaseId'], a['inputSHA256'])
        if key in seen or any(row['assetId'] == a['assetId'] for row in selected): _fail('duplicate-asset')
        seen.add(key); selected.append(a)
    result = {'version': VERSION, 'schemaSha256': hashlib.sha256(DDL.encode()).hexdigest(), 'assets': selected}
    if len(canonical(result)) > 2 * 1024**2: _fail('manifest-bound')
    return result


def _record_source_pointers(representation, pair_index, product_ordinal, profile_ordinal, pointer):
    """Resolve the selected source representation, not the in-memory pair shape."""
    if representation in ('off-legacy-paired-gzip', 'usda-native-jsonl'):
        if (product_ordinal != 2 * pair_index - 1 or profile_ordinal != 2 * pair_index
                or pointer != ('jsonl:packet:' + str(pair_index) if representation.startswith('off-')
                               else 'jsonl:line:' + str(product_ordinal))): _fail('pair-source-coordinate')
        if representation == 'usda-native-jsonl':
            return (pointer + '/0', 'jsonl:line:' + str(profile_ordinal) + '/0')
        return (pointer + '/0', pointer + '/1')
    if representation == 'off-cached-qualified-pair':
        if (pair_index, product_ordinal, profile_ordinal, pointer) != (1, 1, 2, '/records'): _fail('pair-source-coordinate')
        return ('/records/0', '/records/1')
    if representation == 'usda-reviewed-lookup-products-json':
        if (product_ordinal != pair_index or profile_ordinal is not None
                or pointer not in ('/matches/' + str(pair_index - 1) + '/record',
                                   '/lookup/matches/' + str(pair_index - 1) + '/record')): _fail('pair-source-coordinate')
        return (pointer,)
    _fail('pair-source-coordinate')


def ingest_product_details(db, assets, *, scan_asset_once, limits, generation_id, input_manifest_sha256,
                           operation_selection_sha256, identifier_database_sha256, coverage_scope):
    """Import provisional pairs; commit each asset only after its EOF/hash receipt.

    scan_asset_once(asset, consume) calls consume(packet, productOrdinal,
    profileOrdinalOrNone, identifierRecordOrdinal, pointer) provisionally. The
    representation-specific base pointer (line/packet/pair) or cached record
    pointer is validated and resolved separately for each source record. The
    scanner returns the reader's scannedBytes/Records/Products/Profiles/assetSha256,
    EOFFullyVerified=True/bodyPasses=1 receipt. No arbitrary JSON reader factory.
    """
    if db.in_transaction: _fail('caller-transaction-active')
    manifest = prepare_product_detail_manifest(assets)
    if (type(limits) is not ProductDetailStoreLimits or any(type(v) is not int or v <= 0 for v in asdict(limits).values())
            or len(assets) > limits.max_assets or sum(a['inputBytes'] for a in assets) > limits.max_input_bytes
            or sum(a['products'] + a['profiles'] for a in assets) > limits.max_records
            or limits.max_record_bytes > 16 * 1024**2 or not callable(scan_asset_once)
            or not _sha(operation_selection_sha256) or not _sha(identifier_database_sha256)
            or input_manifest_sha256 != _hash(manifest)
            or type(generation_id) is not str or not 0 < len(generation_id) <= 256
            or type(coverage_scope) is not dict or len(canonical(coverage_scope)) > 262144
            or any(not _sha(a.get(k)) for a in assets for k in ('rightsReceiptSHA256', 'custodyReceiptSHA256'))
            or any(a['representation'] == 'usda-native-jsonl' and not _sha(a.get('qualificationSHA256')) for a in assets)
            or any(a['representation'] in ('off-cached-qualified-pair', 'usda-reviewed-lookup-products-json') and not _sha(a.get('cacheReviewSHA256')) for a in assets)): _fail('selection-or-limits')
    if db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') LIMIT 1").fetchone(): _fail('new-empty-store-required')
    start = time.monotonic(); completed = []; products = 0; profiles = 0; identifiers = 0; initialized = False
    def check():
        if time.monotonic() - start >= limits.max_seconds: _fail('time-bound')
    coverage = dict(coverage_scope, identifierDatabaseSha256=identifier_database_sha256, assets=[], sourceFirst=True)
    db.execute('PRAGMA foreign_keys=ON')
    foreign_keys = db.execute('PRAGMA foreign_keys').fetchone()
    if foreign_keys is None or foreign_keys[0] != 1: _fail('foreign-keys-required')
    db.execute('PRAGMA journal_mode=DELETE'); db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA temp_store=MEMORY'); db.execute('PRAGMA cache_size=-8192'); db.execute('PRAGMA mmap_size=0')
    page = db.execute('PRAGMA page_size').fetchone()[0]; db.execute('PRAGMA max_page_count=' + str(max(1, limits.max_database_bytes // page)))
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, limits.max_record_bytes)
    db.set_progress_handler(lambda: int(time.monotonic() - start >= limits.max_seconds), 1000)
    current = None
    try:
        db.executescript(DDL); now = datetime.now(timezone.utc).isoformat()
        db.execute('INSERT INTO product_detail_generation VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (generation_id, input_manifest_sha256, VERSION, 'source-native-full-payload/1', operation_selection_sha256, 'loading', canonical(coverage).decode(),
             len(assets), 0, 0, 0, '[]', now, now, None, 'worker26-source-via-selected57', None, 'private-local-scanner-7645'))
        db.commit(); initialized = True
        for asset in manifest['assets']:
            current = asset; counts = [0, 0, 0]; last = [0]
            check(); db.execute('BEGIN IMMEDIATE')
            def consume(packet, product_ordinal, profile_ordinal, identifier_ordinal, pointer):
                check()
                if (type(packet) is not list or len(packet) not in (1, 2) or any(type(r) is not dict for r in packet)
                        or type(product_ordinal) is not int or product_ordinal <= last[0]
                        or type(identifier_ordinal) is not int or identifier_ordinal < 1
                        or type(pointer) is not str or not 0 < len(pointer) <= 4096
                        or (len(packet) == 2 and (type(profile_ordinal) is not int or profile_ordinal <= product_ordinal))
                        or (len(packet) == 1 and profile_ordinal is not None)): _fail('pair-coordinate')
                product = packet[0]; profile = packet[1] if len(packet) == 2 else None
                p = product.get('provenance'); data = product.get('data')
                if (type(p) is not dict or (p.get('sourceId'), p.get('releaseId')) != (asset['sourceId'], asset['releaseId'])
                        or product.get('kind') != 'product' or type(data) is not dict
                        or type(product.get('id')) is not str or type(p.get('recordId')) is not str
                        or not p['recordId'] or product['id'] != asset['sourceId'] + ':product:' + p['recordId']
                        or type(data.get('identifiers')) is not list): _fail('product-binding')
                if asset['sourceId'] == 'off':
                    if p.get('archiveSha256') != asset['originalSHA256'] or p.get('sourceRow') != identifier_ordinal: _fail('off-coordinate-binding')
                    native = 'off:sourceOccurrence:' + asset['originalSHA256'] + ':' + str(identifier_ordinal)
                    source_record_id = str(identifier_ordinal)
                else:
                    if asset['representation'] == 'usda-native-jsonl' and identifier_ordinal != product_ordinal: _fail('native-coordinate-binding')
                    native = product['id']; source_record_id = p['recordId']
                if profile is not None:
                    q = profile.get('provenance')
                    if (profile.get('kind') != 'nutrientProfile' or type(q) is not dict or type(profile.get('data')) is not dict
                            or (q.get('sourceId'), q.get('releaseId'), q.get('recordId')) != (asset['sourceId'], asset['releaseId'], p['recordId'])
                            or data.get('nutritionId') != profile.get('id')
                            or profile.get('id') != asset['sourceId'] + ':nutrientProfile:' + p['recordId']): _fail('profile-binding')
                    if asset['sourceId'] == 'off' and (q.get('archiveSha256') != asset['originalSHA256'] or q.get('sourceRow') != identifier_ordinal): _fail('profile-coordinate-binding')
                ordinals = [product_ordinal] + ([profile_ordinal] if profile is not None else [])
                record_pointers = _record_source_pointers(asset['representation'], counts[0] + 1,
                    product_ordinal, profile_ordinal, pointer)
                if len(record_pointers) != len(packet): _fail('pair-source-coordinate')
                ids = [_id(asset['sourceId'], asset['releaseId'], asset['inputSHA256'], ordinal, row.get('id')) for ordinal, row in zip(ordinals, packet)]
                pair_sha = hashlib.sha256(readers.canonical(packet)).hexdigest()
                binding = {'sourceId': asset['sourceId'], 'releaseId': asset['releaseId'], 'originalSha256': asset['originalSHA256'],
                    'inputAssetSha256': asset['inputSHA256'], 'identifierAssetSha256': asset['identifierAssetSHA256'],
                    'identifierInputId': asset['identifierInputId'], 'identifierRecordOrdinal': identifier_ordinal,
                    'identifierNativeRecordId': native, 'identifierSourceRecordId': source_record_id,
                    'recordPointers': list(record_pointers), 'recordSha256': pair_sha, 'projectionVersion': asset['projectionVersion'],
                    'rightsReceiptSha256': asset['rightsReceiptSHA256'], 'custodyReceiptSha256': asset['custodyReceiptSHA256'],
                    'operationReceiptSha256': operation_selection_sha256, 'citationId': asset.get('citationId'), 'representation': asset['representation']}
                for index, (row, ordinal, ref) in enumerate(zip(packet, ordinals, ids)):
                    encoded = canonical(row)
                    if len(encoded) > limits.max_record_bytes: _fail('record-byte-bound')
                    db.execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (ref, asset['sourceId'], asset['releaseId'], asset['assetId'], asset['inputSHA256'], ordinal, row.get('id'),
                         record_pointers[index], row.get('language') if type(row.get('language')) is str else 'und', encoded.decode(), _hash(row),
                         asset.get('citationId'), asset['citationStatus'], 'offmenu-product-detail-stream', VERSION, 'processed'))
                for index in reversed(range(len(packet))):
                    db.execute('INSERT INTO product_detail_projection VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (ids[index], generation_id, packet[index]['kind'], ids[1] if index == 0 and profile is not None else None,
                         canonical(dict(binding, recordPointer=record_pointers[index])).decode(), None,
                         canonical(asset.get('projectionLimitations', [])).decode(), None, 'pending', 'source-assertion'))
                for index, identifier in enumerate(data['identifiers'], 1):
                    valid = type(identifier) is dict and type(identifier.get('system')) is str and type(identifier.get('value')) is str
                    db.execute('INSERT INTO product_detail_identifier VALUES(?,?,?,?,?,?)',
                        (ids[0], index, identifier['system'] if valid else None, identifier['value'] if valid else None,
                         'source-asserted' if valid else 'unresolved', '/data/identifiers/' + str(index - 1)))
                counts[0] += 1; counts[1] += int(profile is not None); last[0] = ordinals[-1]
                counts[2] += len(data['identifiers'])
                if counts[0] > asset['products'] or counts[1] > asset['profiles']: _fail('asset-record-bound')
            receipt = scan_asset_once(asset, consume); check()
            if (type(receipt) is not dict or receipt.get('assetSha256') != asset['inputSHA256']
                    or receipt.get('sourceId') != asset['sourceId'] or receipt.get('releaseId') != asset['releaseId']
                    or receipt.get('identifierAssetSha256') != asset['identifierAssetSHA256']
                    or receipt.get('scannedBytes') != asset['inputBytes'] or receipt.get('EOFFullyVerified') is not True
                    or type(receipt.get('bodyPasses')) is not int or receipt['bodyPasses'] != 1
                    or any(type(receipt.get(k)) is not int for k in ('scannedProducts', 'scannedProfiles', 'scannedRecords'))
                    or [receipt['scannedProducts'], receipt['scannedProfiles']] != counts[:2]
                    or counts[:2] != [asset['products'], asset['profiles']] or receipt['scannedRecords'] != sum(counts[:2])): _fail('asset-receipt')
            if asset['representation'] == 'usda-native-jsonl':
                if (receipt.get('qualificationSha256') != asset['qualificationSHA256']
                        or asset['originalSHA256'] not in receipt.get('originalAssetSHA256s', [])): _fail('asset-source-receipt')
            elif receipt.get('originalSha256') != asset['originalSHA256']: _fail('asset-source-receipt')
            if asset['representation'] in ('off-cached-qualified-pair', 'usda-reviewed-lookup-products-json') and receipt.get('cacheReviewSha256') != asset['cacheReviewSHA256']: _fail('cached-review-receipt')
            next_assets = completed + [{'assetId': asset['assetId'], 'sourceId': asset['sourceId'], 'inputSHA256': asset['inputSHA256'], 'products': counts[0], 'profiles': counts[1], 'identifierOccurrences': counts[2], 'receiptSha256': _hash(receipt)}]
            coverage['assets'] = next_assets
            coverage['identifierOccurrences'] = identifiers + counts[2]
            db.execute('UPDATE product_detail_generation SET coverage_scope_json=?,processed_asset_count=?,product_records=?,profile_records=?,modified_at=? WHERE generation_id=?',
                (canonical(coverage).decode(), len(next_assets), products + counts[0], profiles + counts[1], datetime.now(timezone.utc).isoformat(), generation_id))
            db.commit(); completed = next_assets; products += counts[0]; profiles += counts[1]; identifiers += counts[2]
        current = None; check()
        measured = dict(db.execute('SELECT record_kind,count(*) FROM product_detail_projection WHERE generation_id=? GROUP BY record_kind', (generation_id,)))
        if (measured.get('product', 0) != products or measured.get('nutrientProfile', 0) != profiles
                or db.execute('SELECT count(*) FROM product_detail_identifier').fetchone()[0] != identifiers): _fail('final-reconciliation')
        db.execute('UPDATE product_detail_generation SET state=?,modified_at=? WHERE generation_id=?', ('completed', datetime.now(timezone.utc).isoformat(), generation_id)); db.commit(); check()
        return {'version': VERSION, 'generationId': generation_id, 'inputManifestSha256': input_manifest_sha256,
            'completedAssets': completed, 'products': products, 'profiles': profiles, 'unreadAssets': 0,
            'identifierOccurrences': identifiers, 'persistedObservationBridges': 0, 'exceptions': 0,
            'accepted': False, 'publication': 'caller57 must close/fsync/hash/custody/review/select; no activation by writer'}
    except BaseException as error:
        db.set_progress_handler(None, 0); db.rollback()
        if initialized:
            measured = dict(db.execute('SELECT record_kind,count(*) FROM product_detail_projection WHERE generation_id=? GROUP BY record_kind', (generation_id,)))
            code = str(error) if isinstance(error, RefreshError) and re.fullmatch('[a-z0-9-]{1,128}', str(error)) else 'source-or-store-failure'
            db.execute('UPDATE product_detail_generation SET state=?,product_records=?,profile_records=?,exceptions_json=?,modified_at=? WHERE generation_id=?',
                ('incomplete', measured.get('product', 0), measured.get('nutrientProfile', 0), canonical([{'assetId': current['assetId'] if current else None, 'reason': code}]).decode(), datetime.now(timezone.utc).isoformat(), generation_id)); db.commit()
        error.product_detail_retained_state = {'completedAssets': completed, 'productsRetained': measured.get('product', 0) if initialized else 0,
            'profilesRetained': measured.get('nutrientProfile', 0) if initialized else 0, 'completeReceiptReturned': False, 'automaticRetry': False, 'automaticDeletion': False}
        raise
    finally:
        db.set_progress_handler(None, 0)
