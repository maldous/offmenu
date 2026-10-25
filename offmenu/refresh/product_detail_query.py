"""Private product-detail query closure; no writer/scanner/label/cache API.

The caller independently selects both held RO contexts and generation evidence.
Packet canonical bytes come from acceptance; response bytes retain core canonical.
"""

from dataclasses import dataclass, asdict
import hashlib
import re
import sqlite3
import time
from .core import canonical, strict_json, RefreshError
from . import acceptance as readers


def _fail(code): raise RefreshError('product-detail-' + code)


def _sha(value): return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


OFF_LEGACY_PRODUCT_KEYS = frozenset(('name', 'names', 'identifiers', 'brand', 'pack',
    'ingredientsText', 'allergens', 'traces', 'labels', 'categories', 'origins',
    'manufacturingPlaces', 'nutritionSourceBasis', 'rawNutriments',
    'qualificationStatus', 'nutritionId', 'sourceCategoryClaims'))


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
        'sourceCategoryClaims': ('sourceCategoryClaims',)}
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
                or any(type(n) is not int or n < 0 for n in generation[4:6])
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
