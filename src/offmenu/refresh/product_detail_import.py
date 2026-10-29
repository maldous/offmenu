"""Pinned corrected product-detail import closure; no display/query/cache/label API.

Initial definitions/schema came verbatim from reviewed63dd92023. Both public
writer APIs enforce caller-idle/FK preflight; resume adds closed checkpoint and
committed-prefix qualification without changing the new-empty-store API.
This module provides no real-source factory, admission, job or activation.
"""

from contextlib import closing
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sqlite3
import stat
import time
from .core import canonical, strict_json, RefreshError
from . import product_detail_import_readers as readers


VERSION = 'offmenu-retained-product-detail-store/1'

_COVERAGE_WRITER_KEYS = frozenset(('identifierDatabaseSha256', 'assets', 'sourceFirst',
                                   'identifierOccurrences', 'resumeAttempts'))
_MAX_CONTROL_JSON_BYTES = 2 * 1024**2
_MAX_EXCEPTION_JSON_BYTES = 16384
_SQL_LENGTH_BUDGET = 32 * 1024**2


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


def _metadata_json(value, maximum):
    encoded = canonical(value)
    if len(encoded) > maximum: _fail('metadata-byte-bound')
    return encoded.decode()


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
    """Original new-empty-store API; existing stores always fail closed."""
    return _import_product_details(db, assets, scan_asset_once=scan_asset_once, limits=limits,
        generation_id=generation_id, input_manifest_sha256=input_manifest_sha256,
        operation_selection_sha256=operation_selection_sha256,
        identifier_database_sha256=identifier_database_sha256, coverage_scope=coverage_scope)


def resume_existing_product_details(db, assets, *, checkpoint_receipt, checkpoint_sha256,
                                    scan_asset_once, limits, generation_id, input_manifest_sha256,
                                    operation_selection_sha256, identifier_database_sha256, coverage_scope):
    """Resume a caller-selected closed, clean, independently verified checkpoint.

    checkpoint_sha256 pins canonical(checkpoint_receipt), including the new
    operation selection. It is supplied by trusted reviewed caller code, never
    derived from an untrusted store. No source body or whole DB hash is read here.
    Only incomplete generations are supported; loading/hot-journal recovery is
    deliberately outside this API. See the documented receipt contract.
    """
    if db.in_transaction: _fail('caller-transaction-active')
    if (type(checkpoint_receipt) is not dict or not _sha(checkpoint_sha256)
            or len(canonical(checkpoint_receipt)) > _MAX_CONTROL_JSON_BYTES
            or _hash(checkpoint_receipt) != checkpoint_sha256): _fail('checkpoint-selection')
    checkpoint = strict_json(canonical(checkpoint_receipt))
    if (checkpoint.get('version') != 'offmenu-product-detail-checkpoint/1'
            or checkpoint.get('generationId') != generation_id
            or checkpoint.get('inputManifestSha256') != input_manifest_sha256
            or checkpoint.get('identifierDatabaseSha256') != identifier_database_sha256
            or checkpoint.get('resumeOperationSelectionSha256') != operation_selection_sha256
            or any(not _sha(checkpoint.get(k)) for k in ('databaseSha256', 'coverageSha256', 'originalOperationSelectionSha256'))
            or any(checkpoint.get(k) is not True for k in ('producerTerminal', 'producerReaped', 'writableHandlesClosed',
                'cleanJournalVerified', 'integrityAndForeignKeysVerified'))
            or checkpoint.get('state') != 'incomplete'
            or type(checkpoint.get('committedReceipts')) is not list): _fail('checkpoint-selection')
    _checkpoint_identity(checkpoint)
    return _import_product_details(db, assets, scan_asset_once=scan_asset_once, limits=limits,
        generation_id=generation_id, input_manifest_sha256=input_manifest_sha256,
        operation_selection_sha256=operation_selection_sha256,
        identifier_database_sha256=identifier_database_sha256, coverage_scope=coverage_scope,
        _checkpoint=checkpoint, _checkpoint_sha256=checkpoint_sha256)


def _checkpoint_identity(checkpoint):
    path = checkpoint.get('databasePath'); identity = checkpoint.get('databaseIdentity')
    if (type(path) is not str or not Path(path).is_absolute()
            or type(identity) is not list or len(identity) != 5
            or any(type(v) is not int or v < 0 for v in identity)): _fail('checkpoint-identity')
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)): _fail('checkpoint-identity')
    try:
        actual = path.stat()
        if not stat.S_ISREG(actual.st_mode) or list(readers._identity(actual)) != identity: _fail('checkpoint-identity')
        # Even a cold/stale sidecar is unsupported: never auto-repair or delete it.
        if any(p.exists() or p.is_symlink() for p in (Path(str(path) + suffix) for suffix in ('-journal', '-wal', '-shm'))):
            _fail('checkpoint-journal')
    except OSError:
        _fail('checkpoint-identity')


def _checkpoint_prefix(db, manifest, checkpoint, coverage_scope, new_operation):
    """Read SQL metadata under the caller-idle writer lock, before any mutation."""
    databases = db.execute('PRAGMA database_list').fetchall()
    if len(databases) != 1 or databases[0][1:] != ('main', checkpoint['databasePath']): _fail('checkpoint-database')
    if db.execute('PRAGMA journal_mode').fetchone() != ('delete',): _fail('checkpoint-journal')
    # Match all tables, indexes and views, including FK/CHECK/index definitions.
    with closing(sqlite3.connect(':memory:')) as schema:
        schema.executescript(DDL)
        expected = schema.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    actual = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    if actual != expected: _fail('checkpoint-schema')
    if db.execute('SELECT count(*) FROM product_detail_generation').fetchone() != (1,): _fail('checkpoint-generation')
    sizes = db.execute('SELECT length(CAST(coverage_scope_json AS BLOB)),length(CAST(exceptions_json AS BLOB)) FROM product_detail_generation WHERE generation_id=?', (checkpoint['generationId'],)).fetchone()
    if sizes is None: _fail('checkpoint-generation')
    if any(type(n) is not int or not 0 <= n <= cap for n, cap in zip(sizes, (_MAX_CONTROL_JSON_BYTES, _MAX_EXCEPTION_JSON_BYTES))):
        _fail('checkpoint-metadata-bound')
    row = db.execute('SELECT input_manifest_sha256,schema_version,projection_version,operation_selection_sha256,state,coverage_scope_json,expected_asset_count,processed_asset_count,product_records,profile_records,removed_at,exceptions_json FROM product_detail_generation WHERE generation_id=?', (checkpoint['generationId'],)).fetchone()
    if (row is None or row[:5] != (checkpoint['inputManifestSha256'], VERSION, 'source-native-full-payload/1',
            checkpoint['originalOperationSelectionSha256'], 'incomplete') or row[10] is not None
            or any(type(n) is not int or n < 0 for n in row[6:10])
            or row[6] != len(manifest['assets']) or row[7] > row[6]): _fail('checkpoint-generation')
    coverage = strict_json(row[5]); previous_exceptions = strict_json(row[11])
    if type(previous_exceptions) is not list or len(canonical(previous_exceptions)) > _MAX_EXCEPTION_JSON_BYTES: _fail('checkpoint-lineage')
    if (type(coverage) is not dict or _hash(coverage) != checkpoint['coverageSha256']
            or coverage.get('identifierDatabaseSha256') != checkpoint['identifierDatabaseSha256']
            or coverage.get('sourceFirst') is not True or type(coverage.get('assets')) is not list
            or len(coverage['assets']) != row[7]
            or type(coverage.get('identifierOccurrences', 0)) is not int
            or coverage.get('identifierOccurrences', 0) < 0): _fail('checkpoint-coverage')
    if {k:v for k,v in coverage.items() if k not in _COVERAGE_WRITER_KEYS} != coverage_scope:
        _fail('checkpoint-coverage')
    attempts = coverage.get('resumeAttempts', [])
    if type(attempts) is not list or len(attempts) >= 1024: _fail('checkpoint-lineage')
    operations = {checkpoint['originalOperationSelectionSha256']}; prior = 0
    for attempt in attempts:
        if (type(attempt) is not dict or set(attempt) != {'operationSelectionSha256', 'checkpointSha256', 'previousCoverageSha256', 'startedAfterAssetCount', 'startedAt', 'previousExceptions'}
                or any(not _sha(attempt.get(k)) for k in ('operationSelectionSha256', 'checkpointSha256', 'previousCoverageSha256'))
                or attempt['operationSelectionSha256'] in operations
                or type(attempt.get('startedAfterAssetCount')) is not int
                or not prior <= attempt['startedAfterAssetCount'] <= row[7]
                or type(attempt.get('startedAt')) is not str or not attempt['startedAt']
                or type(attempt.get('previousExceptions')) is not list
                or len(canonical(attempt['previousExceptions'])) > _MAX_EXCEPTION_JSON_BYTES): _fail('checkpoint-lineage')
        prior = attempt['startedAfterAssetCount']; operations.add(attempt['operationSelectionSha256'])
    if new_operation in operations: _fail('checkpoint-operation-reuse')
    receipts = checkpoint['committedReceipts']; completed = coverage['assets']
    if len(receipts) != len(completed): _fail('checkpoint-receipt-lineage')
    products = profiles = identifiers = 0
    for index, (asset, committed, receipt) in enumerate(zip(manifest['assets'], completed, receipts)):
        if (type(committed) is not dict or set(committed) != {'assetId', 'sourceId', 'inputSHA256', 'products', 'profiles', 'identifierOccurrences', 'receiptSha256'}
                or any(committed.get(k) != asset[k] for k in ('assetId', 'sourceId', 'inputSHA256', 'products', 'profiles'))
                or any(type(committed.get(k)) is not int or committed[k] < 0 for k in ('products', 'profiles', 'identifierOccurrences'))
                or type(receipt) is not dict or _hash(receipt) != committed.get('receiptSha256')): _fail('checkpoint-receipt-lineage')
        _validate_asset_receipt(asset, receipt, [asset['products'], asset['profiles']])
        operation = checkpoint['originalOperationSelectionSha256']
        for attempt in attempts:
            if index >= attempt['startedAfterAssetCount']: operation = attempt['operationSelectionSha256']
        # SQL counts, not reader events, establish the committed prefix. Only
        # binding metadata is examined; source_payload_json is never selected.
        measured = db.execute("SELECT p.record_kind,count(*),sum(CASE WHEN json_extract(p.source_binding_json,'$.operationReceiptSha256')=? THEN 0 ELSE 1 END) FROM retained_reference_record r CROSS JOIN product_detail_projection p USING(reference_record_id) WHERE r.asset_id=? AND r.asset_sha256=? AND p.generation_id=? GROUP BY p.record_kind", (operation, asset['assetId'], asset['inputSHA256'], checkpoint['generationId'])).fetchall()
        if {kind:(count,wrong) for kind,count,wrong in measured} != dict([('product', (asset['products'], 0))] + ([('nutrientProfile', (asset['profiles'], 0))] if asset['profiles'] else [])):
            _fail('checkpoint-sql-prefix')
        count = db.execute('SELECT count(*) FROM retained_reference_record r JOIN product_detail_identifier i USING(reference_record_id) WHERE r.asset_id=? AND r.asset_sha256=?', (asset['assetId'], asset['inputSHA256'])).fetchone()[0]
        if count != committed['identifierOccurrences']: _fail('checkpoint-sql-prefix')
        products += asset['products']; profiles += asset['profiles']; identifiers += count
    if ((row[8], row[9], coverage.get('identifierOccurrences', 0)) != (products, profiles, identifiers)
            or db.execute('SELECT count(*) FROM retained_reference_record').fetchone() != (products + profiles,)
            or db.execute('SELECT count(*) FROM product_detail_projection').fetchone() != (products + profiles,)
            or db.execute('SELECT count(*) FROM product_detail_identifier').fetchone() != (identifiers,)
            or db.execute('SELECT count(*) FROM product_detail_observation_bridge').fetchone() != (0,)
            or db.execute('PRAGMA foreign_key_check').fetchone() is not None): _fail('checkpoint-sql-prefix')
    _checkpoint_identity(checkpoint)
    return coverage, completed, products, profiles, identifiers, previous_exceptions


def _validate_asset_receipt(asset, receipt, counts):
    if (type(receipt) is not dict or receipt.get('assetSha256') != asset['inputSHA256']
            or receipt.get('sourceId') != asset['sourceId'] or receipt.get('releaseId') != asset['releaseId']
            or receipt.get('identifierAssetSha256') != asset['identifierAssetSHA256']
            or type(receipt.get('scannedBytes')) is not int or receipt['scannedBytes'] != asset['inputBytes']
            or receipt.get('EOFFullyVerified') is not True
            or type(receipt.get('bodyPasses')) is not int or receipt['bodyPasses'] != 1
            or any(type(receipt.get(k)) is not int for k in ('scannedProducts', 'scannedProfiles', 'scannedRecords'))
            or [receipt['scannedProducts'], receipt['scannedProfiles']] != counts[:2]
            or counts[:2] != [asset['products'], asset['profiles']] or receipt['scannedRecords'] != sum(counts[:2])): _fail('asset-receipt')
    if asset['representation'] == 'usda-native-jsonl':
        if (receipt.get('qualificationSha256') != asset['qualificationSHA256']
                or asset['originalSHA256'] not in receipt.get('originalAssetSHA256s', [])): _fail('asset-source-receipt')
    elif receipt.get('originalSha256') != asset['originalSHA256']: _fail('asset-source-receipt')
    if asset['representation'] in ('off-cached-qualified-pair', 'usda-reviewed-lookup-products-json') and receipt.get('cacheReviewSha256') != asset['cacheReviewSHA256']: _fail('cached-review-receipt')


def _import_product_details(db, assets, *, scan_asset_once, limits, generation_id, input_manifest_sha256,
                            operation_selection_sha256, identifier_database_sha256, coverage_scope,
                            _checkpoint=None, _checkpoint_sha256=None):
    """Import provisional pairs; commit each asset only after its EOF/hash receipt.

    scan_asset_once(asset, consume) calls consume(packet, productOrdinal,
    profileOrdinalOrNone, identifierRecordOrdinal, pointer) provisionally. The
    representation-specific base pointer (line/packet/pair) or cached record
    pointer is validated and resolved separately for each source record. The
    scanner returns the reader's scannedBytes/Records/Products/Profiles/assetSha256,
    EOFFullyVerified=True/bodyPasses=1 receipt. No arbitrary JSON reader factory.
    """
    if db.in_transaction: _fail('caller-transaction-active')
    if type(coverage_scope) is dict and not _COVERAGE_WRITER_KEYS.isdisjoint(coverage_scope):
        _fail('coverage-reserved-key')
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
    if _checkpoint is None and db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') LIMIT 1").fetchone(): _fail('new-empty-store-required')
    start = time.monotonic(); completed = []; products = 0; profiles = 0; identifiers = 0; initialized = False
    def check():
        if time.monotonic() - start >= limits.max_seconds: _fail('time-bound')
    coverage = dict(coverage_scope, identifierDatabaseSha256=identifier_database_sha256, assets=[], sourceFirst=True)
    db.execute('PRAGMA foreign_keys=ON')
    foreign_keys = db.execute('PRAGMA foreign_keys').fetchone()
    if foreign_keys is None or foreign_keys[0] != 1: _fail('foreign-keys-required')
    if _checkpoint is not None and db.execute('PRAGMA journal_mode').fetchone() != ('delete',): _fail('checkpoint-journal')
    db.execute('PRAGMA journal_mode=DELETE'); db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA temp_store=MEMORY'); db.execute('PRAGMA cache_size=-8192'); db.execute('PRAGMA mmap_size=0')
    page = db.execute('PRAGMA page_size').fetchone()[0]
    if _checkpoint is None: db.execute('PRAGMA max_page_count=' + str(max(1, limits.max_database_bytes // page)))
    previous_sql_length = db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, min(previous_sql_length, _SQL_LENGTH_BUDGET))
    db.set_progress_handler(lambda: int(time.monotonic() - start >= limits.max_seconds), 1000)
    current = None
    try:
        now = datetime.now(timezone.utc).isoformat()
        if _checkpoint is None:
            db.executescript(DDL)
            db.execute('INSERT INTO product_detail_generation VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (generation_id, input_manifest_sha256, VERSION, 'source-native-full-payload/1', operation_selection_sha256, 'loading', _metadata_json(coverage, _MAX_CONTROL_JSON_BYTES),
                 len(assets), 0, 0, 0, '[]', now, now, None, 'worker26-source-via-selected57', None, 'private-local-scanner-7645'))
        else:
            db.execute('BEGIN IMMEDIATE')
            coverage, completed, products, profiles, identifiers, previous_exceptions = _checkpoint_prefix(
                db, manifest, _checkpoint, coverage_scope, operation_selection_sha256)
            if db.execute('PRAGMA page_count').fetchone()[0] * page > limits.max_database_bytes: _fail('database-byte-bound')
            maximum = max(1, limits.max_database_bytes // page)
            if db.execute('PRAGMA max_page_count=' + str(maximum)).fetchone()[0] > maximum: _fail('database-byte-bound')
            coverage['resumeAttempts'] = coverage.get('resumeAttempts', []) + [{
                'operationSelectionSha256': operation_selection_sha256, 'checkpointSha256': _checkpoint_sha256,
                'previousCoverageSha256': _checkpoint['coverageSha256'],
                'startedAfterAssetCount': len(completed), 'startedAt': now, 'previousExceptions': previous_exceptions}]
            db.execute('UPDATE product_detail_generation SET state=?,coverage_scope_json=?,exceptions_json=?,modified_at=? WHERE generation_id=?',
                ('loading', _metadata_json(coverage, _MAX_CONTROL_JSON_BYTES), '[]', now, generation_id))
        db.commit(); initialized = True
        previous_count = len(completed)
        for asset in manifest['assets'][previous_count:]:
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
            _validate_asset_receipt(asset, receipt, counts)
            next_assets = completed + [{'assetId': asset['assetId'], 'sourceId': asset['sourceId'], 'inputSHA256': asset['inputSHA256'], 'products': counts[0], 'profiles': counts[1], 'identifierOccurrences': counts[2], 'receiptSha256': _hash(receipt)}]
            coverage['assets'] = next_assets
            coverage['identifierOccurrences'] = identifiers + counts[2]
            db.execute('UPDATE product_detail_generation SET coverage_scope_json=?,processed_asset_count=?,product_records=?,profile_records=?,modified_at=? WHERE generation_id=?',
                (_metadata_json(coverage, _MAX_CONTROL_JSON_BYTES), len(next_assets), products + counts[0], profiles + counts[1], datetime.now(timezone.utc).isoformat(), generation_id))
            db.commit(); completed = next_assets; products += counts[0]; profiles += counts[1]; identifiers += counts[2]
        current = None; check()
        measured = dict(db.execute('SELECT record_kind,count(*) FROM product_detail_projection WHERE generation_id=? GROUP BY record_kind', (generation_id,)))
        if (measured.get('product', 0) != products or measured.get('nutrientProfile', 0) != profiles
                or db.execute('SELECT count(*) FROM product_detail_identifier').fetchone()[0] != identifiers): _fail('final-reconciliation')
        db.execute('UPDATE product_detail_generation SET state=?,modified_at=? WHERE generation_id=?', ('completed', datetime.now(timezone.utc).isoformat(), generation_id)); db.commit(); check()
        result = {'version': VERSION, 'generationId': generation_id, 'inputManifestSha256': input_manifest_sha256,
            'completedAssets': completed, 'products': products, 'profiles': profiles, 'unreadAssets': 0,
            'identifierOccurrences': identifiers, 'persistedObservationBridges': 0, 'exceptions': 0,
            'accepted': False, 'publication': 'caller57 must close/fsync/hash/custody/review/select; no activation by writer'}
        if _checkpoint is not None:
            result.update(previouslyCompletedAssets=previous_count, checkpointSha256=_checkpoint_sha256,
                originalOperationSelectionSha256=_checkpoint['originalOperationSelectionSha256'],
                operationSelectionSha256=operation_selection_sha256, resumeAttempts=coverage['resumeAttempts'])
        return result
    except BaseException as error:
        db.set_progress_handler(None, 0); db.rollback()
        if initialized:
            measured = dict(db.execute('SELECT record_kind,count(*) FROM product_detail_projection WHERE generation_id=? GROUP BY record_kind', (generation_id,)))
            code = str(error) if isinstance(error, RefreshError) and re.fullmatch('[a-z0-9-]{1,128}', str(error)) else 'source-or-store-failure'
            db.execute('UPDATE product_detail_generation SET state=?,product_records=?,profile_records=?,exceptions_json=?,modified_at=? WHERE generation_id=?',
                ('incomplete', measured.get('product', 0), measured.get('nutrientProfile', 0), _metadata_json([{'assetId': current['assetId'] if current else None, 'reason': code}], _MAX_EXCEPTION_JSON_BYTES), datetime.now(timezone.utc).isoformat(), generation_id)); db.commit()
        error.product_detail_retained_state = {'completedAssets': completed, 'productsRetained': measured.get('product', 0) if initialized else 0,
            'profilesRetained': measured.get('nutrientProfile', 0) if initialized else 0, 'completeReceiptReturned': False, 'automaticRetry': False, 'automaticDeletion': False}
        raise
    finally:
        db.set_progress_handler(None, 0)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, previous_sql_length)
