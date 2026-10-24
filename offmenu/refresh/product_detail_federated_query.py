"""Selected, held-RO federation only. No store factory, writer or activation.

Manifest/receipt qualification and held-file custody belong to native caller05;
this module performs bounded point validation, never per-request file hashes.
"""
from dataclasses import dataclass
import hashlib
import re
import sqlite3
import time
from .core import canonical, strict_json, timestamp, RefreshError
from . import product_detail_query as native


@dataclass(frozen=True)
class FederatedIdentifierEvidence:
    db: sqlite3.Connection
    run_id: str
    database_sha256: str


@dataclass(frozen=True)
class FederatedStoreEvidence:
    role: str
    db: sqlite3.Connection
    database_sha256: str
    load_receipt_sha256: str
    qualification_sha256: str


@dataclass(frozen=True)
class FederatedQuerySelection:
    generation_id: str
    input_manifest_sha256: str
    operation_selection_sha256: str
    identifier_database_sha256: str


ROLES = ('off-subset', 'usda-products', 'usda-profiles')
USDA_CANDIDATE_SHA256 = '706c767d47d0feebf64915c6f0d3aba45840b012ab07bb7a2d21915f303b06a3'
CURRENT_SQL = native.CURRENT_OBSERVATION_SQL
PRODUCT_KEY_SQL = ('SELECT reference_record_id,source_id,release_id,asset_id,asset_sha256,source_ordinal,'
    'native_record_id,source_pointer,parsed_record_sha256,citation_id,citation_binding_status,'
    'length(CAST(source_payload_json AS BLOB)) FROM retained_reference_record '
    'WHERE asset_id=? AND asset_sha256=? AND source_ordinal=?')
PROFILE_KEY_SQL = ('SELECT a.input_id,a.packet_ordinal,a.native_kind,a.native_record_id,a.source_record_id,'
    'a.packet_sha256,a.source_pointer,a.disposition,p.document_sha256,length(CAST(p.native_packet_json AS BLOB)) '
    'FROM native_nutrient_profile p CROSS JOIN dietary_packet_audit a ON a.packet_id=p.packet_id '
    'WHERE p.profile_id=? AND p.packet_id=?')
OFF_KEY_SQL = ('SELECT i.reference_record_id,p.source_binding_json,p.paired_profile_reference '
    'FROM product_detail_identifier i INDEXED BY product_detail_key_lookup CROSS JOIN product_detail_projection p '
    'ON p.reference_record_id=i.reference_record_id WHERE i.namespace=? AND i.lexical_value=? '
    'AND p.generation_id=? AND p.record_kind=? ORDER BY i.reference_record_id LIMIT ?')


def _fail(code): raise RefreshError('product-detail-federation-' + code) from None
def _require(value, code):
    if not value: _fail(code)
def _hash(value): return hashlib.sha256(canonical(value)).hexdigest()
def _text(value): return type(value) is str and 0 < len(value) <= 4096

def _clock(value):
    if value is None: return True
    if not _text(value): return False
    try: timestamp(value)
    except (RefreshError, ValueError, OverflowError): return False
    return True

def _json(value):
    try: return strict_json(value)
    except (ValueError, TypeError, RefreshError, UnicodeError, RecursionError): _fail('invalid-json')


def _manifest(selection, manifest, evidence, stores):
    _require(type(selection) is FederatedQuerySelection and _text(selection.generation_id)
        and all(native._sha(v) for v in (selection.input_manifest_sha256,selection.operation_selection_sha256,
            selection.identifier_database_sha256)), 'selection')
    _require(type(manifest) is dict and len(canonical(manifest)) <= 262144
        and _hash(manifest) == selection.input_manifest_sha256, 'manifest')
    m = _json(canonical(manifest))  # freeze caller's nested objects at admission
    _require(m.get('version') == 'retained-product-federation-manifest-v1'
        and m.get('generationId') == selection.generation_id
        and m.get('operationSelectionSha256') == selection.operation_selection_sha256
        and m.get('identifierDatabaseSha256') == selection.identifier_database_sha256
        and type(evidence) is FederatedIdentifierEvidence and _text(evidence.run_id)
        and evidence.run_id == m.get('identifierRunId')
        and evidence.database_sha256 == selection.identifier_database_sha256, 'identifier-context')
    _require(type(stores) is tuple and all(type(s) is FederatedStoreEvidence for s in stores)
        and len({s.role for s in stores}) == len(stores), 'store-context')
    _require(type(m.get('identifierFiveTuple')) is list and len(m['identifierFiveTuple']) == 5
        and all(type(n) is int and 0 <= n < 2**63 for n in m['identifierFiveTuple'])
        and m['identifierFiveTuple'][2] > 0
        and native._sha(m.get('identifierLoadReceiptSha256')) and native._sha(m.get('identifierQualificationSha256')), 'identifier-evidence')
    roles = m.get('roles'); _require(type(roles) is dict and set(roles) == set(ROLES), 'roles')
    contexts = {s.role:s for s in stores}; enabled = set()
    for role in ROLES:
        r=roles[role]; _require(type(r) is dict and type(r.get('enabled')) is bool, 'role')
        if not r['enabled']:
            _require(r.get('qualificationState') in ('not-qualified','restricted')
                and type(r.get('reasonCode')) is str and re.fullmatch('[a-z0-9-]{1,96}',r['reasonCode']), 'disabled-role')
            continue
        enabled.add(role); s=contexts.get(role)
        _require(r.get('qualificationState') == 'qualified' and s is not None
            and all(native._sha(r.get(k)) for k in ('databaseSha256','loadReceiptSha256','qualificationSha256',
                'countsEvidenceSha256','rightsReceiptSha256','operationEvidenceSha256')) and (s.database_sha256,s.load_receipt_sha256,s.qualification_sha256)
                == (r['databaseSha256'],r['loadReceiptSha256'],r['qualificationSha256'])
            and type(r.get('fiveTuple')) is list and len(r['fiveTuple']) == 5
            and all(type(n) is int and 0 <= n < 2**63 for n in r['fiveTuple']) and r['fiveTuple'][2] > 0
            and r.get('countBasis') in ('independently-qualified','producer-reported'), 'store-evidence')
    _require(set(contexts) == enabled and (('usda-products' in enabled) == ('usda-profiles' in enabled)), 'role-pair')
    connections=[evidence.db]+[s.db for s in stores]
    _require(all(isinstance(db,sqlite3.Connection) for db in connections)
        and len({id(db) for db in connections}) == len(connections), 'independent-contexts')
    _require(not any(db.in_transaction for db in connections), 'caller-transaction-active')
    if 'usda-products' in enabled:
        u=m.get('usda'); _require(type(u) is dict and u.get('sourceId') == 'usda-files'
            and all(_text(u.get(k)) for k in ('releaseId','assetId','identifierInputId','projectionVersion'))
            and 'candidateFetchedAt' in u and _clock(u['candidateFetchedAt'])
            and all(native._sha(u.get(k)) for k in ('candidateSha256','originalSha256','qualificationSha256',
                'sourceContractSha256','rightsReceiptSha256'))
            and all(type(u.get(k)) is int and 0 < u[k] < 2**63 for k in ('candidateBytes','products','profiles'))
            and u['products'] == u['profiles'] and u['candidateSha256'] == USDA_CANDIDATE_SHA256
            and u['releaseId'] == '2026-04-30' and u.get('representation') == 'usda-native-jsonl', 'usda-selection')
        for role in ('usda-products','usda-profiles'):
            r=roles[role]; _require(r.get('sourceId') == u['sourceId'] and r.get('releaseId') == u['releaseId']
                and r.get('candidateSha256') == u['candidateSha256'] and r.get('assetId') == u['assetId']
                and native._sha(r.get('manifestSha256'))
                and type(r.get('sourceAssetCount')) is int and r['sourceAssetCount'] == 1
                and type(r.get('retainedProducts')) is int and type(r.get('retainedProfiles')) is int
                and (r['retainedProducts'],r['retainedProfiles']) == ((u['products'],0) if role=='usda-products' else (0,u['profiles'])), 'same-candidate')
        _require(native._sha(roles['usda-products'].get('assetSpecSha256'))
            and all(_text(roles['usda-profiles'].get(k)) for k in ('loadId',))
            and all(native._sha(roles['usda-profiles'].get(k)) for k in ('provenanceManifestSha256','operationEvidenceSha256'))
            and 'originalAcquiredAt' in roles['usda-profiles']
            and (roles['usda-profiles']['originalAcquiredAt'] is None or _text(roles['usda-profiles']['originalAcquiredAt']))
            and _text(roles['usda-profiles'].get('acquisitionClockState')), 'load-selection')
    if 'off-subset' in enabled:
        r=roles['off-subset']; _require(r.get('sourceId') == 'off' and _text(r.get('releaseId'))
            and _text(r.get('generationId'))
            and all(native._sha(r.get(k)) for k in ('sourceManifestSha256','sourceOperationSha256','coverageSha256','subsetCertificateSha256'))
            and type(r.get('assets')) is list and 1 <= len(r['assets']) <= 256
            and type(r.get('sourceAssetCount')) is int and r['sourceAssetCount'] == len(r['assets'])
            and type(r.get('retainedProducts')) is int and r['retainedProducts'] > 0
            and type(r.get('retainedProfiles')) is int and r['retainedProfiles'] == r['retainedProducts'], 'subset-certificate')
        seen=set()
        for a in r['assets']:
            _require(type(a) is dict and _text(a.get('assetId')) and native._sha(a.get('inputSHA256'))
                and a.get('sourceId') == 'off' and a['assetId'] not in seen
                and all(type(a.get(k)) is int and a[k] >= 0 for k in ('products','profiles','identifierOccurrences'))
                and a['products'] > 0 and a['profiles'] == a['products']
                and native._sha(a.get('receiptSha256')), 'subset-assets')
            seen.add(a['assetId'])
        _require(sum(a['products'] for a in r['assets']) == r['retainedProducts']
            and sum(a['profiles'] for a in r['assets']) == r['retainedProfiles'], 'subset-counts')
    return m,contexts,connections


def _metadata(db, column, table, key, value, maximum=2*1024**2):
    # Identifiers here are source constants, never request/manifest values.
    size=db.execute(f'SELECT length(CAST({column} AS BLOB)) FROM {table} WHERE {key}=?',(value,)).fetchone()
    if size is None: _fail('load-selection')
    _require(type(size[0]) is int and 0 <= size[0] <= maximum, 'metadata-bound')
    return _json(db.execute(f'SELECT {column} FROM {table} WHERE {key}=?',(value,)).fetchone()[0])


def _loads(m,contexts):
    roles=m['roles']
    if 'usda-products' in contexts:
        u=m['usda']; r=roles['usda-products']; db=contexts['usda-products'].db
        meta=_metadata(db,'meaning','sidecar_schema','version','asset:'+u['assetId'])
        a=meta.get('asset',{}); c=meta.get('counts',{})
        _require(meta.get('state') == 'complete' and meta.get('specSha256') == r['assetSpecSha256'] == _hash(a)
            and (a.get('asset_id'),a.get('sha256'),a.get('source_id'),a.get('release_id'),a.get('kind'))
                == (u['assetId'],u['candidateSha256'],'usda-files',u['releaseId'],'products')
            and a.get('records') == 2*u['products'] and a.get('bytes') == u['candidateBytes']
            and all(type(c.get(k)) is int for k in ('products','stored_source_records','read','unread'))
            and (c['products'],c['stored_source_records'],c['read'],c['unread']) == (u['products'],u['products'],2*u['products'],0), 'product-load')
        r=roles['usda-profiles']; db=contexts['usda-profiles'].db
        row=db.execute('SELECT input_manifest_sha256,state,expected_packets,expected_profile_packets,expected_other_packets,read_packets,unread_packets FROM dietary_load WHERE load_id=?',(r['loadId'],)).fetchone()
        _require(row is not None and all(type(n) is int for n in row[2:])
            and row == (r['manifestSha256'],'completed',2*u['products'],u['profiles'],u['products'],2*u['products'],0), 'profile-load')
        row=db.execute('SELECT load_id,source_id,release_id,asset_id,candidate_sha256,candidate_bytes,provenance_manifest_sha256,operation_evidence_sha256,qualification_sha256,original_acquired_at,acquisition_clock_state FROM dietary_input WHERE input_id=?',(u['candidateSha256'],)).fetchone()
        _require(row == (r['loadId'],'usda-files',u['releaseId'],u['assetId'],u['candidateSha256'],u['candidateBytes'],r['provenanceManifestSha256'],r['operationEvidenceSha256'],u['qualificationSha256'],r['originalAcquiredAt'],r['acquisitionClockState']), 'profile-input')
    if 'off-subset' in contexts:
        r=roles['off-subset']; db=contexts['off-subset'].db
        coverage=_metadata(db,'coverage_scope_json','product_detail_generation','generation_id',r['generationId'])
        row=db.execute('SELECT input_manifest_sha256,operation_selection_sha256,state,expected_asset_count,processed_asset_count,product_records,profile_records FROM product_detail_generation WHERE generation_id=?',(r['generationId'],)).fetchone()
        _require(row is not None and row[:3] == (r['sourceManifestSha256'],r['sourceOperationSha256'],'incomplete')
            and all(type(n) is int for n in row[3:])
            and row[3:] == (257,len(r['assets']),r['retainedProducts'],r['retainedProfiles'])
            and _hash(coverage) == r['coverageSha256'] and coverage.get('assets') == r['assets']
            and coverage.get('identifierDatabaseSha256') == m['identifierDatabaseSha256'], 'off-subset-state')
        attempts=coverage.get('resumeAttempts',[])
        _require(type(attempts) is list and len(attempts) <= 1024, 'off-lineage')
        operations={r['sourceOperationSha256']};prior=0
        for attempt in attempts:
            _require(type(attempt) is dict and native._sha(attempt.get('operationSelectionSha256'))
                and attempt['operationSelectionSha256'] not in operations
                and type(attempt.get('startedAfterAssetCount')) is int
                and prior <= attempt['startedAfterAssetCount'] <= len(r['assets']), 'off-lineage')
            prior=attempt['startedAfterAssetCount'];operations.add(attempt['operationSelectionSha256'])
        r['_operationsByAsset']={}
        for index,asset in enumerate(r['assets']):
            operation=r['sourceOperationSha256']
            for attempt in attempts:
                if index >= attempt['startedAfterAssetCount']:operation=attempt['operationSelectionSha256']
            r['_operationsByAsset'][asset['assetId']]=operation


def _packet(raw,kind):
    _require(type(raw) is str and raw.endswith('\n'), 'packet-encoding')
    p=_json(raw); _require(type(p) is list and len(p) == 1 and type(p[0]) is dict and p[0].get('kind') == kind, 'packet-shape')
    return p[0]


def _native_pair(packet,u,obs):
    product,profile=packet
    for row,kind in zip(packet,('product','nutrientProfile')):
        p=row.get('provenance');data=row.get('data')
        if not (row.get('schemaVersion') == '1.0' and row.get('kind') == kind
            and type(p) is dict and 'fetchedAt' in p
            and (p.get('sourceId'),p.get('releaseId'),p.get('fetchedAt'),p.get('visibility'))
                == ('usda-files',u['releaseId'],u['candidateFetchedAt'],'private-candidate')
            and p.get('recordId') == obs.get('source_record_id') and _text(p.get('recordId'))
            and row.get('id') == 'usda-files:'+kind+':'+p['recordId']
            and type(data) is dict and type(data.get('identifiers')) is list and type(row.get('countries')) is list): return False
    return (product['id'] == obs.get('native_record_id') and product['data'].get('nutritionId') == profile['id']
        and product['data']['identifiers'] == profile['data']['identifiers']
        and type(profile['data'].get('basis')) is dict and type(profile['data'].get('nutrients')) is dict)


def _native_product(product,u,obs):
    """Product identity/provenance is independent of a nutrient-profile join."""
    p=product.get('provenance'); data=product.get('data')
    return (product.get('schemaVersion') == '1.0' and product.get('kind') == 'product'
        and type(p) is dict and 'fetchedAt' in p
        and (p.get('sourceId'),p.get('releaseId'),p.get('fetchedAt'),p.get('visibility'))
            == ('usda-files',u['releaseId'],u['candidateFetchedAt'],'private-candidate')
        and p.get('recordId') == obs.get('source_record_id') and _text(p.get('recordId'))
        and product.get('id') == obs.get('native_record_id') == 'usda-files:product:'+p['recordId']
        and type(data) is dict and type(data.get('identifiers')) is list
        and type(product.get('countries')) is list)


def _usda(obs,m,contexts,charge,candidate_charge):
    u=m['usda']; p=obs['record_ordinal']
    if (obs['artifact_sha256'],obs['input_id'],obs['release_id']) != (u['candidateSha256'],u['identifierInputId'],u['releaseId']): return []
    if p % 2 != 1 or p > 2*u['products']-1: return []
    product_db=contexts['usda-products'].db; profile_db=contexts['usda-profiles'].db
    meta=product_db.execute(PRODUCT_KEY_SQL,(u['assetId'],u['candidateSha256'],p)).fetchone()
    if meta is None:return []
    candidate_charge(1)
    ref,source,release,asset,sha,ordinal,native_id,pointer,parsed,citation,citation_state,size=meta
    audit=product_db.execute('SELECT input_asset_id,input_manifest_sha256,input_asset_sha256,source_id,release_id,source_ordinal,source_record_id,native_product_id,source_record_sha256 FROM product_processing_audit WHERE processing_id=?',(ref,)).fetchone()
    expected_ref='urn:offmenu:source-record:'+_hash([u['assetId'],u['candidateSha256'],p])
    if (ref != expected_ref or (source,release,asset,sha,ordinal,native_id,pointer) != ('usda-files',u['releaseId'],u['assetId'],u['candidateSha256'],p,obs.get('native_record_id'),'/0')
        or audit is None or audit[:-1] != (u['assetId'],m['roles']['usda-products']['manifestSha256'],u['candidateSha256'],'usda-files',u['releaseId'],p,obs.get('source_record_id'),obs.get('native_record_id'))):return []
    _require(audit[-1] == parsed,'record-digest')
    charge(size)
    raw_product=product_db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(ref,)).fetchone()[0]
    product=_packet(raw_product,'product'); _require(_hash(product) == parsed,'record-digest')
    if not _native_product(product,u,obs):return []
    records=[product]; profile_ref=None; profile_digest=None
    gap='nutrient-profile-not-retained'
    packet_id='packet:'+u['candidateSha256']+':'+str(p+1); expected_profile=packet_id+':profile'
    prof=profile_db.execute(PROFILE_KEY_SQL,(expected_profile,packet_id)).fetchone()
    if prof is not None:
        input_id,ordinal,kind,native_id,source_id,packet_sha,source_pointer,disposition,document_sha,profile_size=prof
        gap='nutrient-profile-binding-unavailable'
        if (input_id,ordinal,kind,native_id,source_id,source_pointer,disposition) == (u['candidateSha256'],p+1,'nutrientProfile','usda-files:nutrientProfile:'+str(obs.get('source_record_id')),obs.get('source_record_id'),'/0','profile-stored'):
            charge(profile_size)
            raw_profile=profile_db.execute('SELECT native_packet_json FROM native_nutrient_profile WHERE profile_id=?',(expected_profile,)).fetchone()[0]
            profile_digest=hashlib.sha256(raw_profile.encode('utf-8')).hexdigest()
            if profile_digest == document_sha == packet_sha:
                try:profile=_packet(raw_profile,'nutrientProfile')
                except RefreshError:gap='nutrient-profile-invalid'
                else:
                    if _native_pair([product,profile],u,obs):records.append(profile);profile_ref=expected_profile;gap=None
            else:gap='nutrient-profile-digest-unavailable'
    binding={'sourceId':'usda-files','releaseId':u['releaseId'],'originalSha256':u['originalSha256'],
        'inputAssetSha256':u['candidateSha256'],'identifierAssetSha256':u['candidateSha256'],
        'identifierInputId':u['identifierInputId'],'identifierRecordOrdinal':p,
        'identifierNativeRecordId':obs['native_record_id'],'identifierSourceRecordId':obs['source_record_id'],
        'representation':'usda-native-jsonl','projectionVersion':u['projectionVersion'],
        'recordPointers':['jsonl:line:'+str(p)+'/0']+(['jsonl:line:'+str(p+1)+'/0'] if profile_ref else []),
        'recordPointer':'jsonl:line:'+str(p)+'/0','recordSha256':hashlib.sha256(native.readers.canonical(records)).hexdigest(),
        'rightsReceiptSha256':u['rightsReceiptSha256'],'operationReceiptSha256':m['operationSelectionSha256'],
        'citationId':citation,'citationState':citation_state,'backingRole':['usda-products']+(['usda-profiles'] if profile_ref else []),
        'productReference':ref,'profileReference':profile_ref,
        'pairEvidenceOrigin':'verified-retained-components' if profile_ref else 'verified-retained-product',
        'originalAcquiredAt':m['roles']['usda-profiles']['originalAcquiredAt'],
        'acquisitionClockState':m['roles']['usda-profiles']['acquisitionClockState'],
        'candidateFetchedAt':u['candidateFetchedAt'],
        'backingStoreSha256':{role:contexts[role].database_sha256 for role in ('usda-products','usda-profiles') if role=='usda-products' or profile_ref},
        'componentDigests':{'productParsedRecordSha256':parsed,**({'profileRawPacketSha256':profile_digest} if profile_ref else {})},
        'nutrientProfileAvailability':{'state':'loaded' if profile_ref else 'not-loaded','reasonCode':gap}}
    virtual='urn:offmenu:federated-product:'+_hash([m['generationId'],contexts['usda-products'].database_sha256,
        contexts['usda-profiles'].database_sha256,u['candidateSha256'],p])
    limits=['Qualified source-native retention; selected components validated on query.']
    if gap:limits.append('Product retained independently; nutrient profile unavailable: '+gap)
    return [(virtual,records,binding,limits)]


def _off(obs,m,context,remaining,charge,candidate_charge):
    r=m['roles']['off-subset']; db=context.db
    if obs['release_id'] != r['releaseId']:return []
    rows=db.execute(OFF_KEY_SQL,(obs['namespace'],obs['lexical_value'],r['generationId'],'product',remaining+1)).fetchall()
    _require(len(rows) <= remaining,'candidate-bound');candidate_charge(len(rows))
    result=[]; seen=set(); allowed={(a['assetId'],a['inputSHA256']) for a in r['assets']}
    meta_sql='SELECT asset_id,asset_sha256,source_pointer,parsed_record_sha256,length(CAST(source_payload_json AS BLOB)),source_id,release_id,native_record_id,source_ordinal FROM retained_reference_record WHERE reference_record_id=?'
    for ref,encoded,paired in rows:
        if ref in seen:continue
        seen.add(ref)
        _require(type(encoded) is str and len(encoded.encode()) <= 262144,'metadata-bound')
        b=_json(encoded)
        keys=(('source_id','sourceId'),('release_id','releaseId'),('input_id','identifierInputId'),
            ('artifact_sha256','identifierAssetSha256'),('record_ordinal','identifierRecordOrdinal'),
            ('native_record_id','identifierNativeRecordId'),('source_record_id','identifierSourceRecordId'))
        if any(obs.get(a) != b.get(c) for a,c in keys):continue
        if b.get('representation') != 'off-legacy-paired-gzip':continue
        meta=db.execute(meta_sql,(ref,)).fetchone()
        if meta is None or meta[:2] not in allowed:continue
        if (b.get('inputAssetSha256') != meta[1] or not native._sha(b.get('originalSha256'))
            or b.get('operationReceiptSha256') != r['_operationsByAsset'].get(meta[0])):continue
        charge(meta[4])
        product=_json(db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(ref,)).fetchone()[0])
        _require(_hash(product) == meta[3],'record-digest')
        if not (type(product) is dict and product.get('schemaVersion') == '1.0'
            and type(product.get('provenance')) is dict and type(product.get('data')) is dict
            and type(product.get('countries')) is list):continue
        code=product['provenance'].get('recordId');ordinal=meta[8]
        if (type(code) is not str or code != obs['lexical_value'] or type(ordinal) is not int or ordinal % 2 != 1
            or meta[2] != 'jsonl:packet:'+str((ordinal+1)//2)+'/0' or b.get('recordPointer') != meta[2]
            or obs.get('native_record_id') != 'off:sourceOccurrence:'+str(b.get('originalSha256'))+':'+str(obs['record_ordinal'])
            or (product['provenance'].get('sourceId'),product['provenance'].get('releaseId'),product['provenance'].get('recordId'),
                product['provenance'].get('archiveSha256'),product['provenance'].get('sourceRow'))
                != ('off',r['releaseId'],code,b.get('originalSha256'),obs['record_ordinal'])
            or (meta[5],meta[6],meta[7]) != ('off',r['releaseId'],product.get('id'))
            or product.get('kind') != 'product' or product.get('id') != 'off:product:'+code):continue
        records=[product]; profile_ref=None; profile_meta=None; gap='nutrient-profile-not-retained'
        if paired is not None:
            profile_meta=db.execute(meta_sql,(paired,)).fetchone()
            if profile_meta is not None:
                gap='nutrient-profile-binding-unavailable'
                projection=db.execute('SELECT generation_id,record_kind FROM product_detail_projection WHERE reference_record_id=?',(paired,)).fetchone()
                if (profile_meta[:2] == meta[:2] and profile_meta[:2] in allowed and profile_meta[8] == ordinal+1
                    and profile_meta[2] == 'jsonl:packet:'+str((ordinal+1)//2)+'/1'
                    and projection == (r['generationId'],'nutrientProfile')):
                    charge(profile_meta[4])
                    raw=db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(paired,)).fetchone()[0]
                    try:profile=_json(raw)
                    except RefreshError:gap='nutrient-profile-invalid'
                    else:
                        valid=(type(profile) is dict and profile.get('schemaVersion') == '1.0'
                            and profile.get('kind') == 'nutrientProfile' and profile.get('id') == 'off:nutrientProfile:'+code
                            and type(profile.get('data')) is dict and type(profile.get('provenance')) is dict
                            and type(profile.get('countries')) is list
                            and product['data'].get('nutritionId') == profile.get('id')
                            and type(profile['data'].get('basis')) is dict and type(profile['data'].get('nutrients')) is dict
                            and (profile['provenance'].get('sourceId'),profile['provenance'].get('releaseId'),profile['provenance'].get('recordId'),
                                profile['provenance'].get('archiveSha256'),profile['provenance'].get('sourceRow'))
                                == ('off',r['releaseId'],code,b.get('originalSha256'),obs['record_ordinal'])
                            and (profile_meta[5],profile_meta[6],profile_meta[7]) == ('off',r['releaseId'],profile.get('id')))
                        if valid:
                            if (_hash(profile) == profile_meta[3]
                                and hashlib.sha256(native.readers.canonical([product,profile])).hexdigest() == b.get('recordSha256')
                                and b.get('recordPointers') == [meta[2],profile_meta[2]]):
                                records.append(profile);profile_ref=paired;gap=None
                            else:gap='nutrient-profile-digest-unavailable'
        binding=dict(b,backingRole=['off-subset'],productReference=ref,profileReference=profile_ref,
            subsetCertificateSha256=r['subsetCertificateSha256'],backingStoreSha256={'off-subset':context.database_sha256},
            recordPointer=meta[2],recordPointers=[meta[2]]+([profile_meta[2]] if profile_ref else []),
            recordSha256=hashlib.sha256(native.readers.canonical(records)).hexdigest(),
            componentDigests={'productParsedRecordSha256':meta[3],**({'profileParsedRecordSha256':profile_meta[3]} if profile_ref else {})},
            nutrientProfileAvailability={'state':'loaded' if profile_ref else 'not-loaded','reasonCode':gap})
        if gap:
            binding['declaredPairedSourceBinding']={'recordSha256':b.get('recordSha256'),'recordPointers':b.get('recordPointers'),
                'pairedProfileReference':paired,'state':'not-validated-as-pair'}
        size=db.execute('SELECT length(CAST(projection_limitations_json AS BLOB)) FROM product_detail_projection WHERE reference_record_id=?',(ref,)).fetchone()
        _require(size is not None and type(size[0]) is int and 0 <= size[0] <= 262144,'metadata-bound');charge(size[0])
        limitations=_json(db.execute('SELECT projection_limitations_json FROM product_detail_projection WHERE reference_record_id=?',(ref,)).fetchone()[0])
        _require(type(limitations) is list and all(type(item) is str for item in limitations),'projection-limitations')
        virtual='urn:offmenu:federated-product:'+_hash([m['generationId'],context.database_sha256,ref])
        caveats=limitations+['Independently qualified OFF subset only; original257 generation remains incomplete.']
        if gap:caveats.append('Product retained independently; nutrient profile unavailable: '+gap)
        result.append((virtual,records,binding,caveats))
    return result


def _disabled_roles(m,roles):
    reasons=[{'role':role,'qualificationState':m['roles'][role]['qualificationState'],
        'reasonCode':m['roles'][role]['reasonCode']} for role in roles]
    primary=next((reason for reason in reasons if reason['qualificationState']=='restricted'),reasons[0])
    return primary,reasons


def _coverage(m):
    backends=[]
    for roles,source in ((['off-subset'],'off'),(['usda-products','usda-profiles'],'usda-files')):
        r=m['roles'][roles[0]];enabled=r['enabled'];u=m.get('usda',{}) if source=='usda-files' else r
        primary,reasons=({'qualificationState':'qualified','reasonCode':None},[]) if enabled else _disabled_roles(m,roles)
        backends.append({'roles':roles,'enabled':enabled,'qualificationState':primary['qualificationState'],
            'sourceId':source,'releaseId':u.get('releaseId'),'sourceAssetCount':(1 if source=='usda-files' else r['sourceAssetCount']) if enabled else None,
            'retainedProducts':(u['products'] if source=='usda-files' else r['retainedProducts']) if enabled else None,
            'retainedProfiles':(u['profiles'] if source=='usda-files' else r['retainedProfiles']) if enabled else None,
            'countsEvidenceSha256':[m['roles'][role]['countsEvidenceSha256'] for role in roles] if enabled else [],
            'countBasis':('producer-reported' if any(m['roles'][role]['countBasis']=='producer-reported' for role in roles) else 'independently-qualified') if enabled else 'not-qualified',
            'populationCountIndependentlyVerified':enabled and all(m['roles'][role]['countBasis']=='independently-qualified' for role in roles),
            'pairValidationScope':'selected-pairs-validated-on-query' if enabled else 'not-enabled',
            'reasonCode':primary['reasonCode'],'roleReasons':reasons,
            **({'originalTargetAssets':257,'subsetOnly':True} if source=='off' else {})})
    return {'expectedAssets':None,'processedAssets':None,'products':None,'profiles':None,
        'coverageMode':'federated-source-retention','complete':False,'identifierIndexCoverageSeparate':True,
        'target':{'assets':257,'products':6908496,'profiles':6908496},'backends':backends}


def read_federated_product_details(current_identifier_rows, *, selection, identifier_evidence, stores, selected_manifest,
                                   max_candidates=100,max_result_bytes=262144,max_steps=100000,max_seconds=5):
    try:
        _require(type(current_identifier_rows) is list and len(current_identifier_rows) <= 25
            and all(type(n) is int and n > 0 for n in (max_candidates,max_result_bytes,max_steps,max_seconds))
            and max_candidates <= 1000 and max_result_bytes <= 262144 and max_steps <= 1000000 and max_seconds <= 60
            and len(canonical(current_identifier_rows)) <= max_result_bytes,'request-bound')
        m,contexts,dbs=_manifest(selection,selected_manifest,identifier_evidence,stores)
    except RefreshError:raise
    except (ValueError,TypeError,UnicodeError,RecursionError,AttributeError,sqlite3.Error):_fail('selection')
    start=time.monotonic(); steps=[0];payload=[0];candidates=[0];installed=[]
    def check():_require(time.monotonic()-start < max_seconds,'time-bound')
    def progress():
        steps[0]+=100
        return int(steps[0] > max_steps or time.monotonic()-start >= max_seconds)
    def candidate_charge(n):
        candidates[0]+=n;_require(candidates[0] <= max_candidates,'candidate-bound')
    def charge(n):
        _require(type(n) is int and n >= 0,'payload-bound');payload[0]+=n
        _require(payload[0] <= max_result_bytes,'result-bound');check()
    try:
        for db in dbs:
            old=db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH);installed.append((db,old))
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(old,4*1024**2));db.set_progress_handler(progress,100)
            _require(db.execute('PRAGMA query_only').fetchone() == (1,),'read-only-required')
            databases=db.execute('PRAGMA database_list').fetchall()
            _require(len(databases) == 1 and databases[0][1] == 'main','independent-main-context')
        _loads(m,contexts);check();products=[];availability=[]
        for obs in current_identifier_rows:
            check()
            _require(type(obs) is dict and type(obs.get('assertion_id')) is int and obs['assertion_id']>0
                and type(obs.get('record_ordinal')) is int and obs['record_ordinal']>0
                and all(type(obs.get(k)) is str for k in ('namespace','lexical_value','source_id','release_id','run_id','input_id'))
                and native._sha(obs.get('artifact_sha256')),'observation')
            key={k:obs[k] for k in ('run_id','input_id','assertion_id','record_ordinal')};key['databaseSha256']=selection.identifier_database_sha256
            current=identifier_evidence.db.execute(CURRENT_SQL,(obs['assertion_id'],identifier_evidence.run_id)).fetchone()
            if (current is None or current[-1] not in ('completed','completed-with-exceptions') or current[2] != 'source-asserted'
                or any(obs.get(k) != v for k,v in zip(native.CURRENT_OBSERVATION_COLUMNS,current))):
                availability.append(dict(observationKey=key,state='not-loaded',eligibleProjections=0,reasonCode='no-current-identifier-assertion'));continue
            role='off-subset' if obs['source_id']=='off' else 'usda-products' if obs['source_id']=='usda-files' else None
            if role is None or role not in contexts:
                if role is None:primary,reasons={'qualificationState':'not-qualified','reasonCode':'source-not-selected'},[]
                else:primary,reasons=_disabled_roles(m,('usda-products','usda-profiles') if role=='usda-products' else (role,))
                availability.append(dict(observationKey=key,state='restricted' if primary['qualificationState']=='restricted' else 'not-loaded',eligibleProjections=0,reasonCode=primary['reasonCode'],roleReasons=reasons));continue
            found=_usda(obs,m,contexts,charge,candidate_charge) if role=='usda-products' else _off(obs,m,contexts[role],max_candidates-candidates[0],charge,candidate_charge)
            for ref,records,binding,limitations in found:
                _require(any(type(i) is dict and i.get('system') == obs['namespace'] and i.get('value') == obs['lexical_value'] for i in records[0]['data']['identifiers']),'identifier-binding')
                products.append({'observationKey':key,'sourceObservation':obs,'sourceBinding':binding,
                    'referenceRecordId':ref,'records':records,'fields':native._fields(records,binding['representation']),
                    'projectionLimitations':limitations,'exactObservationBridge':{'state':'matched','key':key,'evidence':binding,
                        'persisted':False,'assertionEvidence':{'kind':'persisted-identifier-observation','databaseSha256':identifier_evidence.database_sha256,**dict(zip(native.CURRENT_OBSERVATION_COLUMNS,current))}},
                    'canonicalIngredient':{'conceptId':None,'status':'unmapped'},
                    'ingredientUsability':{'status':'unclassified','conceptId':None,
                        'reasonCode':'no-qualified-ingredient-classification','classificationEvidence':None},'assurance':'Source-native retained components only; no canonical/English/gold/dietary certification.'})
            availability.append(dict(observationKey=key,state='ambiguous' if len(found)>1 else 'loaded' if found else 'not-loaded',eligibleProjections=len(found),reasonCode=None if found else 'no-exact-source-observation-bridge'))
            _require(len(canonical(products)) <= max_result_bytes,'result-bound')
        output={'sourceProducts':products,'productDetailAvailability':availability,'generationId':selection.generation_id,
            'identifierDatabaseSha256':selection.identifier_database_sha256,'inputManifestSha256':selection.input_manifest_sha256,
            'operationSelectionSha256':selection.operation_selection_sha256,'backend':'retained-product-federation-v1',
            'selectionManifestSha256':selection.input_manifest_sha256,'backingStores':[{'role':s.role,'databaseSha256':s.database_sha256,
                'loadReceiptSha256':s.load_receipt_sha256,'qualificationSha256':s.qualification_sha256} for s in (contexts[role] for role in ROLES if role in contexts)],
            'coverage':_coverage(m),'accepted':False}
        _require(len(canonical(output)) <= max_result_bytes,'result-bound');check();return output
    except sqlite3.Error:_fail('sql-bound-or-store')
    except RefreshError:raise
    except (KeyError,TypeError,ValueError,UnicodeError,RecursionError,AttributeError):_fail('invalid-data')
    finally:
        for db,old in installed:
            db.set_progress_handler(None,0);db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,old)
