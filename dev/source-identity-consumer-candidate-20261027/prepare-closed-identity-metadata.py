from pathlib import Path
import hashlib, json, sqlite3

R = Path(__file__).resolve().parent
BASE = Path('/home/user/src/offmenu-data/runtime/layout-migration/worker19/remaining-held-public-english-serving-20261026')
RIGHTS = Path('/home/user/src/offmenu-data/runtime/layout-migration/worker56/usda060-source-identity-rights-contract-20261027')
INPUTS = [
    ('retained-identity-only-cohort060-usda-chunk00006-20261027', '8a884f8c5c111485a93cd5c14e1c9223f58a16ffcfd914de6ecf4f98e776fdab', 75),
    ('retained-identity-only-cohort060-usda-chunk00005-20261027', 'b22d5e3d8cbafb3d0a9c495567ab0e4a429945ad38e971b7f220797bcc4b8058', 2499),
]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def ref(path):
    return {'path':str(path), 'sha256':sha(path.read_bytes())}

def put(name, value, compact=False):
    path = R / name
    data = json.dumps(value, separators=(',',':')) if compact else json.dumps(value, indent=2)
    with path.open('x') as output:
        output.write(data + '\n')
    return {**ref(path), 'bytes':path.stat().st_size}

rights_contract = ref(RIGHTS / 'source-rights-field-contract.json')
assert rights_contract['sha256'] == '56a7c4c323b41ec31b6d98531e29bff15917c802c51e7987fce66e7bb495ff9d'
records, source_indexes, reports = [], [], []
for directory, expected_hash, expected_count in INPUTS:
    path = BASE / directory / 'candidate-index.sqlite'
    assert sha(path.read_bytes()) == expected_hash
    source_indexes.append(expected_hash)
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute('SELECT * FROM candidates ORDER BY stage_id').fetchall()
        columns = {row[1] for row in database.execute('PRAGMA table_info(candidates)')}
        assert len(rows) == expected_count
        postings = {}
        if 'barcode_postings_json' not in columns:
            for posting in database.execute('SELECT code,stage_id,checksum_valid FROM barcodes ORDER BY stage_id,code'):
                assert posting['checksum_valid'] in (0, 1)
                postings.setdefault(posting['stage_id'], []).append({'checksumValid':bool(posting['checksum_valid']), 'lexicalCode':posting['code']})
        for row in rows:
            original_rights = json.loads(row['source_rights_json'])
            visibility_field = 'sourceVisibility' if 'sourceVisibility' in original_rights else 'visibility'
            assert set(original_rights) == {'attribution','license',visibility_field}
            rights = {key:original_rights[key] for key in ('attribution','license')}
            rights['sourceVisibility'] = original_rights[visibility_field]
            assert rights['sourceVisibility'] == 'source-staging'
            assert row['normalization_complete'] == row['gold_admitted'] == 0
            record = {
                'stageId':row['stage_id'], 'nativeId':row['native_id'], 'wireSha256':row['wire_sha'],
                'sourceInputIndexSha256':expected_hash, 'rightsVisibilityField':visibility_field,
                'sourceBinding':json.loads(row['source_binding_json']),
                'identifiers':json.loads(row['identifiers_json']),
                'barcodePostings':json.loads(row['barcode_postings_json']) if 'barcode_postings_json' in columns else postings.get(row['stage_id'], []),
                'sourceRights':rights, 'canonicalStatus':row['canonical_status'], 'englishStatus':row['english_status'],
                'normalizationComplete':False, 'goldAdmitted':False,
            }
            assert record['sourceBinding']['sourceId'] == 'usda-files'
            assert record['sourceBinding']['releaseId'] == '2026-04-30'
            records.append(record)
    reports.append({'sourceIndex':ref(path), 'records':expected_count, 'postingsSource':'barcode_postings_json' if 'barcode_postings_json' in columns else 'barcodes table', 'rightsVisibilityField':visibility_field})

records.sort(key=lambda record:record['stageId'])
assert len(records) == len({record['stageId'] for record in records}) == 2574
codes = {posting['lexicalCode'] for record in records for posting in record['barcodePostings']}
assert len(codes) == 2574
valid = sum(posting['checksumValid'] for record in records for posting in record['barcodePostings'])
invalid = sum(not posting['checksumValid'] for record in records for posting in record['barcodePostings'])
assert (valid, invalid) == (2559, 15)
input_set_hash = sha(json.dumps(source_indexes, separators=(',',':')).encode())
index = {'schema':'offmenu-source-identity-index/2', 'fieldSet':'source-identifier-claims-with-provenance/2', 'sourceId':'usda-files', 'releaseId':'2026-04-30', 'sourceIndexSha256':input_set_hash, 'records':records}
index_ref = put('prepared-identity-index.json', index, compact=True)
assert index_ref['bytes'] <= 8 * 1024 * 1024
manifest = {
    'schema':'offmenu-source-identity-manifest/2', 'status':'prepared', 'scope':'localhost-only',
    'fieldSet':index['fieldSet'], 'sourceId':index['sourceId'], 'releaseId':index['releaseId'],
    'sourceQualificationSha256':'e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9',
    'nativeRepresentationQualificationSha256':'5f45979fcdde581a62093c1c32fe047ef1e355416ff33c0128bace305c053553',
    'sourceRightsFieldContractSha256':rights_contract['sha256'],
    'sourceRights':records[0]['sourceRights'],
    'sourceURL':'https://fdc.nal.usda.gov/download-datasets/',
    'sourceIndex':{'sha256':input_set_hash}, 'selectedSourceIndexes':source_indexes,
    'index':{'sha256':index_ref['sha256'], 'bytes':index_ref['bytes']},
    'recordCount':2574, 'sourceDistinctLexicalKeys':2574,
    'checksumValidClaims':2559, 'checksumInvalidClaims':15,
    'publicPublicationAccepted':False, 'normalizationComplete':False, 'goldAdmitted':False,
    'runtimeActivation':False, 'servingAdmissions':0,
    'fieldScope':'Source identifier claims/native-stage-wire/source proof digests/notices only. Names, language, English, food type and nutrition remain unknown. Invalid source barcode strings stay invalid; valid native FDC identity remains available. No canonical/phase/Gold promotion.',
    'consumerCodeSha256':ref(R / 'source-identity-reader.mjs')['sha256'],
    'typedIdentifierCodeSha256':ref(R / 'typed-identifier-contract.mjs')['sha256'],
    'admission':'NOT_ISSUED_PENDING_EXACT_FOCUSED_REVIEW_AND_NEW_LOCAL_FIELD_OPERATION_BINDING',
}
manifest_ref = put('manifest.prepared.json', manifest)
custody = put('internal-source-custody.json', {
    'scope':'Internal metadata only; not a served envelope and no raw shard/nativeDB operation.',
    'sourceIndexes':reports, 'rightsContract':rights_contract,
    'rightsRequirements':ref(RIGHTS / 'outward-envelope-requirements.UNADMITTED.json'),
    'rightsOwnerResult':ref(RIGHTS / 'result.json'),
    'preparedManifest':manifest_ref, 'preparedIndex':index_ref,
    'originalNamesMaterialized':False, 'sourceRightsOperationAdmissionIssued':False,
})
print(json.dumps({'manifest':manifest_ref,'index':index_ref,'internalCustody':custody,'records':2574,'keys':2574,'valid':valid,'invalid':invalid,'servingAdmissions':0,'normalizedAssociations':0,'Gold':0}))
