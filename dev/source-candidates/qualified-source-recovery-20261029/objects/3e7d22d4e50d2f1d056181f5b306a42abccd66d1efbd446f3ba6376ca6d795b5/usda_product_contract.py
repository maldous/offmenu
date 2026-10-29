"""Reviewed-code inputs for one private native FDC release, never a JSON loader.

Counts/IDs are the actual independent full witness9995, reviewed64/9993.
This native preservation policy does not establish canonical nutrient semantics,
GTIN validity, English output, field-origin coverage, Gold or country completeness.
Originals are never opened here. An explicit qualification context reads only the
verified private normalization DB; no admission, run or resource selection occurs.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import sqlite3

from .acceptance import Asset, SourceContract, canonical, fingerprint
from . import product_adapters as adapters
from .core import RefreshError

SOURCE = Asset('FoodData_Central_csv_2026-04-30.zip', 481517495,
    'c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01')
RIGHTS = Asset('rights.json', 1995,
    'da3bef50a8490d4ddc1d98db49b59f7af0fd9145a75a9249d9cc2a0a64f9137e')
WITNESS_SHA256 = '711e36b7cf72622ec850588f56c6e0d7244b7cddbf1c24c1d8f326756903901c'
WITNESS_REVIEW_SHA256 = 'b0c4b52d078a6bc50e49d578e0ebef27535083a6cd9e12c3d670998df17b29d7'
EXPECTED_RECORDS = 4202558
EXPECTED_IDS_SHA256 = '2d5be06c4e3be042b4bed583a5ada885066188b901aa3b23f7a9dc48a1472f0f'
RAW_ROWS = 36049091
EXPANDED_BYTES = 3264203789
RELEASE = '2026-04-30'
SCOPE = 'usda-20260430-private-native-products-v1'
LICENSE = 'USDA FoodData Central public domain / CC0 (retained declaration)'
ATTRIBUTION = 'USDA Agricultural Research Service FoodData Central'
ADAPTER_SHA256 = 'a41e3bb77fcc6a32a98837cdc74fd0f4653cfc809070283c53dc900098c70a4d'


def _object(properties):
    return {'type': 'object', 'required': list(properties),
            'properties': properties, 'additionalProperties': False}


def native_schemas():
    """Complete projector record shapes; retain native strings/unknowns as-is."""
    text = {'type': 'string'}
    nullable_text = {'type': ['string', 'null']}
    number = {'type': ['number', 'null']}
    digest = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    identifiers = {'type': 'array', 'minItems': 1, 'maxItems': 2,
        'items': _object({'system': {'enum': ['USDA-FDC', 'barcode']},
                          'value': {'type': 'string', 'minLength': 1}})}
    basis = _object({'amount': {'const': 100}, 'unit': {'const': 'g'},
                     'state': {'const': 'as-described'}})
    raw = {'type': 'object', 'required': ['id', 'fdc_id', 'nutrient_id', 'amount'],
           'additionalProperties': text}
    observation = _object({'value': number, 'unit': text, 'sourceAmount': text,
        'sourceUnit': text, 'sourceName': text, 'sourceNutrientId': text,
        'sourceRowId': text, 'rawFields': raw, 'basis': basis, 'method': {'const': 'source'}})
    data = {
        'product': _object({'name': text, 'identifiers': identifiers,
            'brand': nullable_text, 'dataType': text, 'ingredientsText': nullable_text,
            'marketCountry': nullable_text,
            'serving': _object({'amount': number, 'unit': nullable_text, 'label': nullable_text}),
            'nutritionId': text}),
        'nutrientProfile': _object({'foodName': text, 'identifiers': identifiers,
            'basis': basis, 'nutrients': {'type': 'object', 'additionalProperties': observation}})}
    provenance = _object({'sourceId': {'const': 'usda-files'}, 'releaseId': {'const': RELEASE},
        'recordId': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'fetchedAt': {'type': 'null'},
        'sourceDate': nullable_text,
        'acquisitionClock': _object({'status': {'const': 'unknown-retained'}, 'evidenceSha256': digest}),
        'license': {'const': LICENSE}, 'attribution': {'const': ATTRIBUTION},
        'rightsEvidenceSha256': digest, 'scopeEvidenceSha256': digest,
        'sourceRow': {'type': 'integer', 'minimum': 1, 'maximum': 2101279},
        'inputSha256': {'const': {'archive': SOURCE.sha256}},
        'transform': {'const': adapters.VERSION}, 'visibility': {'const': 'private-candidate'},
        'rights': {'const': 'Original source terms govern reuse; normalization does not relicense data.'}})
    # Origin enrichment preserves the same data/IDs. Its wrapper independently
    # checks every datum's origin against the source DB; this is no origin grant.
    provenance['properties']['fieldOrigins'] = {'type': 'object', 'additionalProperties': {'type': 'object'}}
    return {kind: {'$schema': 'https://json-schema.org/draft/2020-12/schema',
                  **_object({'schemaVersion': {'const': '1.0'}, 'kind': {'const': kind},
                     'id': text, 'countries': {'const': ['US']}, 'data': shape,
                     'provenance': provenance})} for kind, shape in data.items()}


def native_semantic_errors(record, *, scope_sha256, clock_sha256, source_rows=None,
                           source_sha256=SOURCE.sha256, rights_sha256=RIGHTS.sha256):
    """All-record identity, source-observation, numeric/unit/basis consistency.

    Unknown source units/data types remain native assertions, not conversions.
    Schema validation handles shape. Missing/invalid structure still fails here.
    The pure checker reads no files. source_rows must come from the verified
    normalization context; missing authority holds every nutrient profile.
    """
    errors = set()
    try:
        p, d, kind = record['provenance'], record['data'], record['kind']
        key = p['recordId']
        if (not isinstance(key, str) or not key.strip() or len(key.encode('utf-8')) > 64
                or kind not in ('product', 'nutrientProfile')
                or record['id'] != f'usda-files:{kind}:{key}'):
            errors.add('usda-native-identity')
        if (p['sourceId'] != 'usda-files' or p['releaseId'] != RELEASE or p['fetchedAt'] is not None
                or p['rightsEvidenceSha256'] != rights_sha256 or p['scopeEvidenceSha256'] != scope_sha256
                or p['acquisitionClock'] != {'status': 'unknown-retained', 'evidenceSha256': clock_sha256}
                or p['license'] != LICENSE or p['attribution'] != ATTRIBUTION
                or p['transform'] != adapters.VERSION or p['visibility'] != 'private-candidate'
                or record['countries'] != ['US'] or p['inputSha256'] != {'archive': source_sha256}
                or type(p['sourceRow']) is not int or not 1 <= p['sourceRow'] <= 2101279):
            errors.add('usda-native-provenance')
        ids = d['identifiers']
        if (not 1 <= len(ids) <= 2 or ids[0] != {'system': 'USDA-FDC', 'value': key}
                or (len(ids) == 2 and (ids[1]['system'] != 'barcode'
                                     or not isinstance(ids[1]['value'], str) or not ids[1]['value']))):
            errors.add('usda-native-identifiers')
        if kind == 'product':
            if d['nutritionId'] != 'usda-files:nutrientProfile:' + key:
                errors.add('usda-native-nutrition-reference')
            value = d['serving']['amount']
            if value is not None and (isinstance(value, bool) or adapters._number(value) != value):
                errors.add('usda-native-serving-number')
        elif kind == 'nutrientProfile':
            if source_rows is None:
                errors.add('usda-native-source-order-authority-required')
            else:
                expected_rows, previous = {}, 0
                for ordinal, raw_source in source_rows:
                    if type(ordinal) is not int or ordinal <= previous:
                        errors.add('usda-native-source-order-invalid')
                    previous = ordinal
                    base = adapters._USDA_NUTRIENTS.get(raw_source['nutrient_id'],
                                                       'usda:' + raw_source['nutrient_id'])
                    name = base if base not in expected_rows else base + ':observation:' + raw_source['id']
                    if name in expected_rows or raw_source['fdc_id'] != key:
                        errors.add('usda-native-source-order-invalid')
                    expected_rows[name] = raw_source
                if set(d['nutrients']) != set(expected_rows):
                    errors.add('usda-native-observation-source-order')
                for name in set(d['nutrients']) & set(expected_rows):
                    n, raw_source = d['nutrients'][name], expected_rows[name]
                    if n['sourceRowId'] != raw_source['id'] or n['rawFields'] != raw_source:
                        errors.add('usda-native-observation-source-lineage')
            basis = {'amount': 100, 'unit': 'g', 'state': 'as-described'}
            if d['basis'] != basis:
                errors.add('usda-native-basis')
            seen = set()
            for name, n in d['nutrients'].items():
                raw, row_id, nutrient_id = n['rawFields'], n['sourceRowId'], n['sourceNutrientId']
                base = adapters._USDA_NUTRIENTS.get(nutrient_id, 'usda:' + nutrient_id)
                if (name not in (base, base + ':observation:' + row_id) or row_id in seen
                        or not row_id or not nutrient_id):
                    errors.add('usda-native-observation-identity')
                seen.add(row_id)
                if (raw['id'] != row_id or raw['fdc_id'] != key
                        or raw['nutrient_id'] != nutrient_id or raw['amount'] != n['sourceAmount']):
                    errors.add('usda-native-observation-lineage')
                if n['unit'] != n['sourceUnit'].lower():
                    errors.add('usda-native-source-unit')
                expected = adapters._number(n['sourceAmount'])
                if isinstance(n['value'], bool) or n['value'] != expected:
                    errors.add('usda-native-source-number')
                if n['basis'] != basis or n['method'] != 'source':
                    errors.add('usda-native-observation-basis')
    except (KeyError, TypeError, ValueError, AttributeError, RefreshError):
        errors.add('usda-native-record-invalid')
    return sorted(errors)


@dataclass(frozen=True)
class _NativeUsdaSemantics:
    scope_sha256: str
    clock_sha256: str
    source: Asset
    rights: Asset

    def __call__(self, row):
        # Direct qualify/accept without a verified producer DB cannot authorize
        # primary observations. Product bridges bind the authority below.
        return native_semantic_errors(row, scope_sha256=self.scope_sha256,
            clock_sha256=self.clock_sha256, source_sha256=self.source.sha256,
            rights_sha256=self.rights.sha256)


@contextmanager
def bind_normalized_semantics(contract, normalized, manifest, limits):
    """Bind this fixed policy to the SAME verified normalization source.sqlite.

    Nothing is inferred from native row IDs, candidate order or discovery JSON.
    Legacy reviewed semantic callables retain their existing behavior. Callers
    must use the verified product bridge, or the same context for explicit accept.
    """
    policy = contract.semantic_validator
    if not isinstance(policy, _NativeUsdaSemantics):
        yield contract
        return
    from .acceptance import _hash_file
    if (contract.holds or contract.output_scope != 'native' or contract.output_visibility != 'private'
            or not {'retain', 'parse', 'transform'} <= set(contract.required_operations)
            or not set(contract.required_operations) <= set(contract.permitted_operations)):
        raise RefreshError('usda-source-order-authority-held')
    limits.validate()
    context = adapters.ProductContext(contract.source_id, contract.release_id, contract.acquired_at,
        LICENSE, ATTRIBUTION, policy.rights.sha256, policy.scope_sha256,
        acquisition_clock_status=contract.acquisition_clock_status,
        clock_evidence_sha256=policy.clock_sha256)
    raw_pin = {**asdict(policy.source), 'path': Path(policy.source.path).name, 'role': 'archive'}
    if (contract.source_id != 'usda-files' or contract.release_id != RELEASE
            or policy.source not in contract.inputs or policy.rights != contract.rights_evidence
            or policy.scope_sha256 != contract.scope_evidence.sha256
            or contract.clock_evidence is None or policy.clock_sha256 != contract.clock_evidence.sha256
            or manifest.get('sourceId') != contract.source_id or manifest.get('releaseId') != RELEASE
            or manifest.get('contract', {}).get('context') != asdict(context)
            or manifest.get('contract', {}).get('adapterVersion') != adapters.VERSION
            or manifest.get('contract', {}).get('limits') != asdict(limits)
            or manifest.get('contract', {}).get('inputFiles') != [raw_pin]):
        raise RefreshError('usda-source-order-authority-contract')
    path = adapters._safe(Path(normalized) / 'source.sqlite')
    manifest_path = adapters._safe(Path(normalized) / 'manifest.json')
    if _hash_file(manifest_path, 1024**2)[1] != manifest.get('normalizationManifestSha256'):
        raise RefreshError('usda-source-order-normalization-pin')
    expected = manifest.get('outputHashes', {}).get('source.sqlite')
    def identity():
        info = path.stat()
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    before = identity()
    if not isinstance(expected, str) or _hash_file(path, limits.max_database_bytes)[1] != expected:
        raise RefreshError('usda-source-order-authority-pin')
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    def semantic(row):
        rows = None
        if row.get('kind') == 'nutrientProfile':
            rows, size = [], 0
            try:
                cursor = db.execute('SELECT ordinal,body FROM raw WHERE tab=? AND parent=? '
                                    'ORDER BY ordinal LIMIT ?',
                                    ('food_nutrient', row['provenance']['recordId'], limits.max_nutrients_per_food+1))
                try:
                    for ordinal, body in cursor:
                        size += len(body.encode('utf-8'))
                        if len(rows) >= limits.max_nutrients_per_food or size > limits.max_line_bytes:
                            return ['usda-native-source-order-bound']
                        rows.append((ordinal, json.loads(body)))
                finally:
                    cursor.close()
            except (KeyError, TypeError, ValueError, sqlite3.Error):
                return ['usda-native-source-order-invalid']
        return native_semantic_errors(row, scope_sha256=policy.scope_sha256,
            clock_sha256=policy.clock_sha256, source_rows=rows,
            source_sha256=policy.source.sha256, rights_sha256=policy.rights.sha256)
    try:
        yield replace(contract, semantic_validator=semantic)
    finally:
        db.close()
        if identity() != before or _hash_file(path, limits.max_database_bytes)[1] != expected:
            raise RefreshError('usda-source-order-authority-changed')


def policy_sha256():
    adapter = hashlib.sha256(Path(adapters.__file__).read_bytes()).hexdigest()
    if adapter != ADAPTER_SHA256:
        raise ValueError('usda-product-adapter-pin-mismatch')
    return fingerprint({'policy': 'usda-private-native-preservation/2',
        'sourceOrderAuthority': 'verified-normalization-source-sqlite/1',
        'sourceFileSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapterSha256': adapter, 'schemasSha256': fingerprint(native_schemas()),
        'independentWitnessSha256': WITNESS_SHA256, 'reviewSha256': WITNESS_REVIEW_SHA256})


def evidence_documents():
    """Deterministic new metadata; callers preserve the old witness evidence."""
    clock = {'schemaVersion': 'offmenu-retained-clock-evidence/1', 'sourceId': 'usda-files',
        'releaseId': RELEASE, 'scopeId': SCOPE, 'status': 'unknown-retained',
        'originalAcquiredAt': None, 'originalDownloader': None,
        'basisEvidenceSha256': '9517038522568c0c2a24f5520f3e325293fbc27bb823307ccaed68d977438f80',
        'rightsEvidenceSha256': RIGHTS.sha256, 'inputFiles': [asdict(SOURCE)]}
    clock_sha = fingerprint(clock)
    scope = {'sourceId': 'usda-files', 'releaseId': RELEASE, 'scopeId': SCOPE,
        'operation': 'private-native-product-normalization-qualification',
        'outputScope': 'native', 'outputVisibility': 'private',
        'original': asdict(SOURCE), 'roles': {'archive': SOURCE.path},
        'rightsEvidenceSha256': RIGHTS.sha256,
        'acquisitionClock': {'status': 'unknown-retained', 'evidenceSha256': clock_sha},
        'expectedRecords': EXPECTED_RECORDS, 'expectedSortedIdSha256': EXPECTED_IDS_SHA256,
        'independentWitnessSha256': WITNESS_SHA256, 'independentReviewSha256': WITNESS_REVIEW_SHA256,
        'schemasSha256': fingerprint(native_schemas()), 'semanticPolicySha256': policy_sha256(),
        'purpose': 'native source preservation with independent count/ID and schema/semantic qualification',
        'countMeaning': 'product+nutrientProfile native IDs, not raw rows/GTINs/actual normalized output',
        'canonicalNutrientSemantics': False, 'englishAccepted': False,
        'fieldOriginMaterializationSelected': False,
        'goldAdmitted': False, 'countryComplete': False, 'publicOperations': False}
    return {'usda-product-clock.json': clock, 'usda-product-scope.json': scope}


def usda_20260430_contract(*, limits):
    """Fixed trusted application factory; limits supplied by separately reviewed57.

    No caller-supplied counts, source identities, JSON schemas or callbacks.
    Code selection, resources, source operation and runtime admission stay separate.
    """
    if not isinstance(limits, adapters.ProductLimits):
        raise ValueError('usda-product-reviewed-limits-required')
    limits.validate()
    docs = evidence_documents()
    assets = {name: Asset(name, len(canonical(doc)), fingerprint(doc)) for name, doc in docs.items()}
    clock, scope = assets['usda-product-clock.json'], assets['usda-product-scope.json']
    inputs = (SOURCE, RIGHTS, clock, scope)
    if (limits.max_input_bytes < sum(a.bytes for a in inputs)
            or limits.max_expanded_bytes < EXPANDED_BYTES or limits.max_rows < RAW_ROWS):
        raise ValueError('usda-product-full-source-limits-too-small')
    schemas = native_schemas()
    semantic = _NativeUsdaSemantics(scope.sha256, clock.sha256, SOURCE, RIGHTS)
    return SourceContract('usda-files', RELEASE, SCOPE, None, inputs,
        EXPECTED_RECORDS, EXPECTED_IDS_SHA256, schemas, fingerprint(schemas), semantic,
        policy_sha256(), RIGHTS, scope, frozenset(('retain', 'parse', 'transform')),
        max_input_bytes=limits.max_input_bytes, max_output_bytes=limits.max_output_bytes,
        max_records=EXPECTED_RECORDS, acquisition_clock_status='unknown-retained', clock_evidence=clock)
