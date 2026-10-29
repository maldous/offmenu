"""13's separate private detail read model; source records first, no identity gate.

Caller57 supplies a NEW empty held SQLite connection and selected one-pass source
readers. This module never opens the identifier DB, corpus originals or a server.
Streamed rows are provisional until each reader's full integrity receipt returns.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from types import SimpleNamespace

from .core import canonical, strict_json, RefreshError
from .acceptance import SourceContract, contract_fingerprint
from . import native_barcode_lookup as readers

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


def scan_cached_product_detail_asset(asset, *, identity, consume, native_lookup_metadata=None,
                                    native_lookup_contract=None):
    """Reuse exactly one already reviewed <=1MiB saved pair/product-only wrapper.

    Trusted caller binds current rights/custody/operation and the existing review;
    this byte/identity check is not new permission. No parent/shard/index reads.
    """
    if (asset.get('representation') not in ('off-cached-qualified-pair', 'usda-reviewed-lookup-products-json')
            or not _sha(asset.get('cacheReviewSHA256')) or not callable(consume)
            or type(identity) is not tuple or len(identity) != 5
            or any(type(n) is not int or n < 0 for n in identity)
            or type(asset.get('inputBytes')) is not int or not 0 < asset['inputBytes'] <= 1048576
            or identity[2] != asset['inputBytes']): _fail('cached-selection')
    if asset['representation'] == 'usda-reviewed-lookup-products-json':
        from .identifier_database import _lookup_records
        m = native_lookup_metadata
        contract = native_lookup_contract
        if (not isinstance(contract, SourceContract) or contract.source_id != 'usda-files'
                or contract.output_scope != 'native' or contract.output_visibility != 'private'
                or contract.holds or not {'retain', 'parse', 'transform'} <= contract.required_operations
                or not contract.required_operations <= contract.permitted_operations): _fail('cached-native-contract')
        evidence_paths = {contract.rights_evidence.path, contract.scope_evidence.path}
        if contract.clock_evidence is not None: evidence_paths.add(contract.clock_evidence.path)
        source_inputs = [a for a in contract.inputs if a.path not in evidence_paths]
        if (type(m) is not dict or len(canonical(m)) > 1048576 or m.get('sourceId') != asset['sourceId']
                or m.get('releaseId') != asset['releaseId'] or m.get('candidateSha256') != asset['inputSHA256']
                or (m.get('sourceId'), m.get('releaseId'), m.get('scopeId'))
                    != (contract.source_id, contract.release_id, contract.scope_id)
                or m.get('contractSha256') != contract_fingerprint(contract)
                or m.get('originalContractInputs') != [vars(a) for a in contract.inputs]
                or m.get('upstreamCandidateSha256') != asset['identifierAssetSHA256']
                or m.get('qualificationSha256') != asset.get('qualificationSHA256')
                or m.get('expectedRecords') != asset['products']
                or asset['originalSHA256'] not in [a.sha256 for a in source_inputs]): _fail('cached-native-metadata')
    path = readers._safe(Path(asset['inputPath'])); before = path.stat()
    if not stat.S_ISREG(before.st_mode) or readers._identity(before) != identity: _fail('cached-custody')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if readers._identity(os.fstat(stream.fileno())) != identity: _fail('cached-custody')
        raw = stream.read(asset['inputBytes'] + 1)
        if (len(raw) != asset['inputBytes'] or stream.read(1) != b''
                or hashlib.sha256(raw).hexdigest() != asset['inputSHA256']
                or readers._identity(os.fstat(stream.fileno())) != identity): _fail('cached-hash-or-custody')
    if readers._identity(readers._safe(path).stat()) != identity: _fail('cached-custody')
    products = 0; profiles = 0
    if asset['representation'] == 'off-cached-qualified-pair':
        document = strict_json(raw); binding = document.get('sourceBinding', {}) if type(document) is dict else {}
        if (type(binding) is not dict or (binding.get('sourceId'), binding.get('releaseId'), binding.get('originalSha256'), binding.get('occurrenceAssetSha256'))
                != (asset['sourceId'], asset['releaseId'], asset['originalSHA256'], asset['identifierAssetSHA256'])
                or binding.get('inputAssetSha256') != asset.get('upstreamAssetSHA256')
                or type(document.get('records')) is not list): _fail('cached-source-binding')
        packet = document['records']; code = packet[0].get('provenance', {}).get('recordId') if packet and type(packet[0]) is dict else None
        if type(code) is not str: _fail('cached-source-binding')
        _, ordinal = readers._retained_packet(packet, SimpleNamespace(release_id=asset['releaseId'], original_sha256=asset['originalSHA256'], shard_key=hashlib.sha256(code.encode()).hexdigest()[:2]))
        if (ordinal != binding.get('sourceOccurrence')
                or hashlib.sha256(readers.canonical(packet)).hexdigest() != binding.get('recordSha256')): _fail('cached-record-binding')
        consume(packet, 1, 2, ordinal, '/records'); products = 1; profiles = 1
    else:
        for index, (encoded, location) in enumerate(_lookup_records(raw, m), 1):
            packet = strict_json(encoded)
            consume(packet, index, None, location['nativeCandidateOrdinal'], location['pointer']); products += 1
    return {'assetSha256': asset['inputSHA256'], 'scannedBytes': len(raw), 'scannedRecords': products + profiles,
            'scannedProducts': products, 'scannedProfiles': profiles, 'EOFFullyVerified': True, 'bodyPasses': 1,
            'sourceId': asset['sourceId'], 'releaseId': asset['releaseId'], 'originalSha256': asset['originalSHA256'],
            'identifierAssetSha256': asset['identifierAssetSHA256'], 'cacheReviewSha256': asset['cacheReviewSHA256']}


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


# Exact retained projector capabilities, not the unrelated Python OFF-native
# policy: collect-jsonl.mjs uses apps/web/src/unified-data.js normalizeOFF. USDA uses
# usda_product_contract.native_schemas()['product'].data (closed properties).
OFF_LEGACY_PRODUCT_KEYS = frozenset(('name', 'names', 'identifiers', 'brand', 'pack',
    'ingredientsText', 'allergens', 'traces', 'labels', 'categories', 'origins',
    'manufacturingPlaces', 'nutritionSourceBasis', 'rawNutriments',
    'qualificationStatus', 'nutritionId', 'sourceCategoryFields', 'categoryDisposition'))
USDA_NATIVE_PRODUCT_KEYS = frozenset(('name', 'identifiers', 'brand', 'dataType',
    'ingredientsText', 'marketCountry', 'serving', 'nutritionId'))
PRODUCT_KEYS_BY_REPRESENTATION = {
    'off-legacy-paired-gzip': OFF_LEGACY_PRODUCT_KEYS,
    'off-cached-qualified-pair': OFF_LEGACY_PRODUCT_KEYS,
    'usda-native-jsonl': USDA_NATIVE_PRODUCT_KEYS,
    'usda-reviewed-lookup-products-json': USDA_NATIVE_PRODUCT_KEYS,
}


def _fields(packet, representation):
    """Keep selected representation values; never upgrade publisher field states."""
    product = packet[0]; profile = packet[1] if len(packet) == 2 else None
    mappings = {'name': ('name',), 'names': ('names',), 'brand': ('brand',), 'packageQuantity': ('pack',),
        'servingQuantity': ('serving',), 'dataType': ('dataType',), 'ingredientDeclaration': ('ingredientsText',),
        'categories': ('categories',), 'sourceAllergenClaims': ('allergens',), 'sourceTraceClaims': ('traces',),
        'sourceDietaryLabelClaims': ('labels',), 'origins': ('origins',), 'manufacturingPlaces': ('manufacturingPlaces',),
        'rawNutriments': ('rawNutriments',), 'nutritionSourceBasis': ('nutritionSourceBasis',),
        'sourceCategoryFields': ('sourceCategoryFields',), 'categoryDisposition': ('categoryDisposition',)}
    evidence = hashlib.sha256(readers.canonical(packet)).hexdigest(); result = {}
    def field(value, present, pointer, available=True):
        state = ('present' if value is not None else 'null') if present else ('missing' if available else 'not-loaded')
        return {'state': state, 'value': value, 'reasonCode': None if state == 'present' else
            'explicit-projected-null' if state == 'null' else 'projection-field-absent' if state == 'missing' else 'representation-not-provided',
            'fieldPointer': pointer if present else None, 'evidenceSha256': evidence if available else None,
            'valueOrigin': 'upstream-projection' if available else 'unknown', 'sourceFieldState': 'unknown', 'language': None}
    data = product['data']
    if representation not in PRODUCT_KEYS_BY_REPRESENTATION: _fail('field-representation')
    supported = PRODUCT_KEYS_BY_REPRESENTATION[representation]
    for name, path in mappings.items():
        # Only a supported key's absence is evidenced by a loaded projection.
        # Unknown extension values remain in the complete raw record.
        key = path[0]; available = key in supported
        result[name] = field(data.get(key) if available else None, available and key in data,
            '/0/data/' + key, available)
    market_key = 'marketCountry' if 'marketCountry' in supported else None
    result['markets'] = field(data.get(market_key), market_key in data, '/0/data/' + str(market_key)) if market_key else field(product.get('countries'), 'countries' in product, '/0/countries')
    result['nutrientProfile'] = field(profile['data'] if profile else None, profile is not None, '/1/data', profile is not None)
    result['sourceProvenance'] = field(product['provenance'], True, '/0/provenance')
    result['imageUrlReferences'] = field(None, False, None, False)
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
    db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA journal_mode=DELETE'); db.execute('PRAGMA synchronous=FULL')
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


@dataclass(frozen=True)
class ProductDetailQuerySelection:
    generation_id: str
    input_manifest_sha256: str
    operation_selection_sha256: str
    identifier_database_sha256: str


@dataclass(frozen=True)
class CurrentIdentifierEvidence:
    """Trusted caller's independently selected, held RO identifier generation.

    Connection custody and database digest selection belong to caller05/57, just
    like the detail-store connection. Never construct this from request rows.
    The selected run is independent of the requested observation's run_id.
    """
    db: sqlite3.Connection
    run_id: str
    database_sha256: str


CURRENT_OBSERVATION_COLUMNS = ('run_id', 'assertion_id', 'disposition', 'input_id',
    'record_ordinal', 'namespace', 'lexical_value', 'source_id', 'release_id',
    'artifact_sha256', 'native_record_id', 'source_record_id')
CURRENT_OBSERVATION_SQL = ('SELECT ' + ','.join(CURRENT_OBSERVATION_COLUMNS) +
    ',load_state FROM barcode_identifier_inspection WHERE assertion_id=? AND run_id=?')


def read_product_details(db, observations, *, selection, identifier_evidence=None, max_candidates=100,
                         max_result_bytes=262144, max_steps=100000, max_seconds=5):
    """Private caller-selected RO store; exact indexed source bridges, no scan.

    Caller05 validates the external detail receipt/held DB custody once per
    selected generation. This reads no files and computes no full DB hash.
    Each requested assertion is checked by PK against independently selected
    persisted identifier evidence. No assertion replay or HTTP-side DB writes.
    """
    if (type(selection) is not ProductDetailQuerySelection
            or any(not _sha(v) for k, v in asdict(selection).items() if k != 'generation_id')
            or type(observations) is not list or len(observations) > 25
            or any(type(v) is not int or v <= 0 for v in (max_candidates, max_result_bytes, max_steps, max_seconds))
            or max_candidates > 1000 or max_result_bytes > 262144
            or len(canonical(observations)) > max_result_bytes): _fail('query-selection-or-bound')
    if (type(identifier_evidence) is not CurrentIdentifierEvidence
            or not isinstance(identifier_evidence.db, sqlite3.Connection)
            or identifier_evidence.db is db
            or type(identifier_evidence.run_id) is not str or not identifier_evidence.run_id
            or identifier_evidence.database_sha256 != selection.identifier_database_sha256): _fail('query-identifier-evidence')
    start = time.monotonic(); steps = [0]; result = []; availability = []
    def progress():
        steps[0] += 100
        return int(steps[0] > max_steps or time.monotonic() - start >= max_seconds)
    db.set_progress_handler(progress, 100)
    try:
        identifier_evidence.db.set_progress_handler(progress, 100)
        generation = db.execute('SELECT input_manifest_sha256,operation_selection_sha256,state,coverage_scope_json,expected_asset_count,processed_asset_count,product_records,profile_records FROM product_detail_generation WHERE generation_id=?', (selection.generation_id,)).fetchone()
        if (generation is None or generation[:3] != (selection.input_manifest_sha256, selection.operation_selection_sha256, 'completed')
                or generation[4] != generation[5]
                or strict_json(generation[3]).get('identifierDatabaseSha256') != selection.identifier_database_sha256): _fail('query-unselected-generation')
        for observation in observations:
            if (type(observation) is not dict or type(observation.get('assertion_id')) is not int or observation['assertion_id'] < 1
                    or type(observation.get('record_ordinal')) is not int or observation['record_ordinal'] < 1
                    or any(type(observation.get(k)) is not str for k in ('namespace', 'lexical_value', 'source_id', 'release_id', 'run_id', 'input_id'))
                    or not _sha(observation.get('artifact_sha256'))): _fail('query-observation')
            key = {name: observation[name] for name in ('run_id', 'input_id', 'assertion_id', 'record_ordinal')}
            key['databaseSha256'] = selection.identifier_database_sha256
            current = identifier_evidence.db.execute(CURRENT_OBSERVATION_SQL,
                (observation['assertion_id'], identifier_evidence.run_id)).fetchone()
            if (current is None or current[-1] not in ('completed', 'completed-with-exceptions')
                    or current[2] != 'source-asserted'
                    or any(observation.get(name) != value for name, value in zip(CURRENT_OBSERVATION_COLUMNS, current))):
                availability.append({'observationKey': key, 'state': 'not-loaded', 'eligibleProjections': 0,
                    'reasonCode': 'no-current-identifier-assertion'})
                continue
            rows = db.execute('SELECT i.reference_record_id,p.source_binding_json,coalesce(length(CAST(p.fields_json AS BLOB)),0),p.paired_profile_reference '
                'FROM product_detail_identifier i INDEXED BY product_detail_key_lookup CROSS JOIN product_detail_projection p ON p.reference_record_id=i.reference_record_id '
                'WHERE i.namespace=? AND i.lexical_value=? AND p.generation_id=? AND p.record_kind=? ORDER BY i.reference_record_id LIMIT ?',
                (observation['namespace'], observation['lexical_value'], selection.generation_id, 'product', max_candidates + 1)).fetchall()
            if len(rows) > max_candidates: _fail('query-candidate-bound')
            matched = set()
            for ref, encoded_binding, field_bytes, paired in rows:
                if ref in matched: continue
                binding = strict_json(encoded_binding)
                pairs = (('source_id', 'sourceId'), ('release_id', 'releaseId'), ('input_id', 'identifierInputId'),
                    ('artifact_sha256', 'identifierAssetSha256'), ('record_ordinal', 'identifierRecordOrdinal'),
                    ('native_record_id', 'identifierNativeRecordId'), ('source_record_id', 'identifierSourceRecordId'))
                if any(observation.get(a) != binding.get(b) for a, b in pairs): continue
                sizes = db.execute('SELECT length(CAST(source_payload_json AS BLOB)) FROM retained_reference_record WHERE reference_record_id IN (?,?)', (ref, paired)).fetchall()
                if not sizes or field_bytes is None or sum(n[0] for n in sizes) + field_bytes > max_result_bytes: _fail('query-result-bound')
                product = strict_json(db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?', (ref,)).fetchone()[0])
                profile = strict_json(db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?', (paired,)).fetchone()[0]) if paired else None
                encoded_fields = db.execute('SELECT fields_json FROM product_detail_projection WHERE reference_record_id=?', (ref,)).fetchone()[0]
                limitations = strict_json(db.execute('SELECT projection_limitations_json FROM product_detail_projection WHERE reference_record_id=?', (ref,)).fetchone()[0])
                records = [product] + ([profile] if profile else [])
                fields = strict_json(encoded_fields) if encoded_fields is not None else _fields(records, binding['representation'])
                if (hashlib.sha256(readers.canonical(records)).hexdigest() != binding['recordSha256']
                        or not any(type(i) is dict and i.get('system') == observation['namespace'] and i.get('value') == observation['lexical_value'] for i in product['data']['identifiers'])): _fail('query-record-binding')
                matched.add(ref)
                result.append({'observationKey': key, 'sourceObservation': observation, 'sourceBinding': binding,
                    'referenceRecordId': ref, 'records': records, 'fields': fields, 'projectionLimitations': limitations,
                    'exactObservationBridge': {'state': 'matched', 'key': key, 'evidence': binding, 'persisted': False,
                        'assertionEvidence': {'kind': 'persisted-identifier-observation',
                            'databaseSha256': identifier_evidence.database_sha256,
                            **dict(zip(CURRENT_OBSERVATION_COLUMNS, current))}},
                    'canonicalIngredient': {'conceptId': None, 'status': 'unmapped'},
                    'assurance': 'source-native retained projection only; no canonical/English/gold/dietary certification'})
                if len(canonical(result)) > max_result_bytes: _fail('query-result-bound')
            availability.append({'observationKey': key, 'state': 'ambiguous' if len(matched) > 1 else 'loaded' if matched else 'not-loaded',
                                 'eligibleProjections': len(matched), 'reasonCode': None if matched else 'no-exact-source-observation-bridge'})
        output = {'sourceProducts': result, 'productDetailAvailability': availability, 'generationId': selection.generation_id,
                  'identifierDatabaseSha256': selection.identifier_database_sha256,
                  'inputManifestSha256': selection.input_manifest_sha256,
                  'operationSelectionSha256': selection.operation_selection_sha256,
                  'coverage': {'expectedAssets': generation[4], 'processedAssets': generation[5],
                    'products': generation[6], 'profiles': generation[7],
                    'scope': {k: v for k, v in strict_json(generation[3]).items() if k != 'assets'},
                    'identifierIndexCoverageSeparate': True}, 'accepted': False}
        if len(canonical(output)) > max_result_bytes: _fail('query-result-bound')
        if time.monotonic() - start >= max_seconds: _fail('query-time-bound')
        return output
    finally:
        db.set_progress_handler(None, 0)
        identifier_evidence.db.set_progress_handler(None, 0)
