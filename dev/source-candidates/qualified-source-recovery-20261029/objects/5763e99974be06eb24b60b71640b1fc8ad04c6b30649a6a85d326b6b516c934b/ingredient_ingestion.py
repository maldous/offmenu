"""Local source-faithful ingredient import into13's separate managed sidecar.

No fetching, runtime AI, canonical identity selection or existing DB mutation.
Raw product/dictionary records import independently of deferred semantic mapping.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import gzip
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import stat
import time

from .core import canonical, strict_json, RefreshError
from .native_barcode_lookup import _identity
from .product_adapters import _safe

VERSION='offmenu-ingredient-source-import/1'
# Exact existing13 base + product audit + shared raw-reference table. No new DDL lane.
SCHEMA_PINS={'base': '126018fab8546e875a4c2773887f6960e8826f8a926d4b52e6d7cc07fa25dd37', 'audit': '760020aa12dccc21349718a465739587e3fa67a39bb3cc460c8e320c1484bd48', 'referenceFile': '1a0bb6cbec8e1477d8d51cac30bb8cd1c8e100125f56bdb0b82339cb59ba293d', 'selectedReferenceTable': '7a1a195a98a88de6607ff526043ff5fbb7e6291b6209e98722475bbcaadaebba'}
DDL="PRAGMA foreign_keys=ON;\n-- New separate PRIVATE sidecar only. Never apply to the validated identifier DB.\nCREATE TABLE sidecar_schema(version TEXT PRIMARY KEY NOT NULL, created_at TEXT NOT NULL, meaning TEXT NOT NULL);\nCREATE TABLE declaration_source(\n source_database_sha256 TEXT PRIMARY KEY NOT NULL,\n source_database_pointer TEXT NOT NULL,\n original_selected_input_sha256 TEXT NOT NULL,\n source_owner INTEGER NOT NULL CHECK(source_owner=56),\n review_state TEXT NOT NULL\n);\nCREATE TABLE ingredient_concept(\n concept_id TEXT PRIMARY KEY NOT NULL,\n logical_type TEXT NOT NULL CHECK(logical_type IN ('urn:offmenu:type:FoodIngredient','urn:offmenu:type:FoodConcept')),\n identity_status TEXT NOT NULL CHECK(identity_status IN ('source-scoped','candidate-join','curated-concept','identified')),\n preferred_label TEXT,\n label_language TEXT,\n decision_id TEXT NOT NULL,\n decision_version TEXT NOT NULL,\n evidence_pointer TEXT NOT NULL,\n evidence_sha256 TEXT NOT NULL,\n database_created_at TEXT,\n database_modified_at TEXT,\n database_deleted_at TEXT\n);\nCREATE TABLE ingredient_hierarchy_assertion(\n assertion_id TEXT PRIMARY KEY NOT NULL,\n child_concept_id TEXT NOT NULL REFERENCES ingredient_concept(concept_id),\n parent_concept_id TEXT NOT NULL REFERENCES ingredient_concept(concept_id),\n relationship_kind TEXT NOT NULL CHECK(relationship_kind='broaderMatch'),\n decision_status TEXT NOT NULL,\n decision_version TEXT NOT NULL,\n evidence_pointer TEXT NOT NULL,\n evidence_sha256 TEXT NOT NULL,\n CHECK(child_concept_id<>parent_concept_id)\n);\nCREATE TABLE ingredient_declaration_ref(\n declaration_id TEXT PRIMARY KEY NOT NULL,\n source_database_sha256 TEXT NOT NULL REFERENCES declaration_source(source_database_sha256),\n declaration_no INTEGER NOT NULL CHECK(declaration_no>=1),\n source_id TEXT NOT NULL,\n release_id TEXT NOT NULL,\n source_record_id TEXT NOT NULL,\n native_product_id TEXT NOT NULL,\n original_candidate_line INTEGER NOT NULL CHECK(original_candidate_line>0),\n source_record_sha256 TEXT NOT NULL,\n source_field_pointer TEXT NOT NULL,\n declaration_text_sha256 TEXT NOT NULL,\n language_status TEXT NOT NULL,\n citation_id TEXT,\n citation_status TEXT NOT NULL,\n UNIQUE(source_database_sha256,declaration_no)\n);\nCREATE TABLE product_ingredient_assertion(\n assertion_id TEXT PRIMARY KEY NOT NULL,\n declaration_id TEXT NOT NULL REFERENCES ingredient_declaration_ref(declaration_id),\n concept_id TEXT REFERENCES ingredient_concept(concept_id),\n relationship_kind TEXT NOT NULL CHECK(relationship_kind IN ('declaration-only','contains','usable_as','candidateMatch','exactMatch','broaderMatch')),\n common_predicate_id TEXT,\n mapping_status TEXT NOT NULL CHECK(mapping_status IN ('unmapped','candidate','broader','confirmed')),\n decision_id TEXT,\n decision_version TEXT,\n evidence_pointer TEXT NOT NULL,\n evidence_sha256 TEXT NOT NULL,\n unknown_reason TEXT,\n CHECK((concept_id IS NULL AND mapping_status='unmapped') OR\n       (concept_id IS NOT NULL AND decision_id IS NOT NULL AND decision_version IS NOT NULL)),\n CHECK(relationship_kind='declaration-only' OR common_predicate_id IS NOT NULL)\n);\nCREATE INDEX ingredient_source_crosswalk ON ingredient_declaration_ref(source_id,release_id,native_product_id,source_record_id);\nCREATE INDEX ingredient_assertion_declaration ON product_ingredient_assertion(declaration_id,assertion_id);\nCREATE INDEX ingredient_assertion_concept ON product_ingredient_assertion(concept_id,mapping_status,assertion_id);\nCREATE INDEX ingredient_hierarchy_parent ON ingredient_hierarchy_assertion(parent_concept_id,child_concept_id);\nCREATE VIEW v_ingredient_concepts AS SELECT * FROM ingredient_concept;\nCREATE VIEW v_product_ingredient_inspection AS\nSELECT a.assertion_id,d.declaration_id,d.source_id,d.release_id,d.source_record_id,\n d.native_product_id,d.original_candidate_line,d.source_record_sha256,\n d.source_field_pointer,d.declaration_text_sha256,\n a.concept_id,c.preferred_label AS offmenu_ingredient,c.label_language,\n a.relationship_kind,a.common_predicate_id,a.mapping_status,\n a.decision_id,a.decision_version,a.evidence_pointer,a.evidence_sha256,a.unknown_reason,\n d.citation_id,d.citation_status\nFROM ingredient_declaration_ref d\nJOIN product_ingredient_assertion a ON a.declaration_id=d.declaration_id\nLEFT JOIN ingredient_concept c ON c.concept_id=a.concept_id;\n\n-- Additive extension to13actual6-table sidecar in a NEW successor only.\n-- Existing declarations are OPTIONAL for processing an eligible product.\nCREATE TABLE product_processing_audit (\n processing_id TEXT PRIMARY KEY NOT NULL,\n input_asset_id TEXT NOT NULL,\n input_manifest_sha256 TEXT NOT NULL,\n input_asset_sha256 TEXT NOT NULL,\n source_id TEXT NOT NULL, release_id TEXT NOT NULL,\n source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),\n source_record_id TEXT, native_product_id TEXT,\n group_key TEXT,\n declaration_id TEXT REFERENCES ingredient_declaration_ref(declaration_id),\n declaration_state TEXT NOT NULL CHECK(declaration_state IN ('present','empty','null','missing','invalid-type','unread','unknown')),\n processing_status TEXT NOT NULL CHECK(processing_status IN ('processed','quarantined','failed','unread')),\n semantic_mapping_status TEXT NOT NULL CHECK(semantic_mapping_status IN ('pending','unmapped','candidate','broader','confirmed','not-assessed')),\n semantic_decision_category TEXT,\n semantic_decision_vocabulary_sha256 TEXT,\n composition_state TEXT NOT NULL CHECK(composition_state IN ('unknown','single','composite')),\n decision_id TEXT, decision_version TEXT,\n registry_manifest_sha256 TEXT,\n source_record_sha256 TEXT,\n source_pointer TEXT NOT NULL,\n evidence_pointer TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,\n parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL,\n citation_id TEXT, citation_status TEXT NOT NULL,\n reason_code TEXT,\n UNIQUE(input_asset_id,input_asset_sha256,source_ordinal),\n CHECK(declaration_id IS NULL OR declaration_state='present'),\n CHECK(semantic_decision_category IS NULL OR semantic_decision_vocabulary_sha256 IS NOT NULL),\n CHECK((decision_id IS NULL)=(decision_version IS NULL))\n);\nCREATE INDEX product_processing_asset ON product_processing_audit(input_asset_id,processing_status,source_ordinal);\nCREATE INDEX product_processing_group ON product_processing_audit(input_asset_id,group_key,processing_id);\nCREATE INDEX product_processing_source ON product_processing_audit(source_id,release_id,native_product_id,source_ordinal);\nCREATE VIEW v_product_processing_inspection AS\nSELECT p.*,a.concept_id,a.relationship_kind,a.mapping_status AS relation_mapping_status\nFROM product_processing_audit p\nLEFT JOIN ingredient_declaration_ref d ON d.declaration_id=p.declaration_id\nLEFT JOIN product_ingredient_assertion a ON a.declaration_id=d.declaration_id;\n-- Count products from product_processing_audit, NEVER from the optional-join view.\n-- Relation fanout in view is explicit association grain, not a product denominator.\n\nCREATE TABLE retained_reference_record(\n reference_record_id TEXT PRIMARY KEY NOT NULL,\n source_id TEXT NOT NULL, release_id TEXT NOT NULL,\n asset_id TEXT NOT NULL, asset_sha256 TEXT NOT NULL,\n source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),\n native_record_id TEXT, source_pointer TEXT NOT NULL,\n original_language TEXT NOT NULL, source_payload_json TEXT NOT NULL,\n parsed_record_sha256 TEXT NOT NULL,\n citation_id TEXT, citation_binding_status TEXT NOT NULL,\n parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL,\n processing_status TEXT NOT NULL,\n UNIQUE(asset_id,asset_sha256,source_ordinal)\n);\n"


@dataclass(frozen=True)
class SourceAsset:
    asset_id: str
    path: str
    bytes: int
    sha256: str
    records: int
    source_id: str
    release_id: str
    kind: str  # products or registry: source-native records, never canonical acceptance
    products: int | None = None
    compression: str = 'none'
    language: str = 'und'
    citation_id: str | None = None
    citation_status: str = 'pending'
    lineage: tuple = ()


@dataclass(frozen=True)
class ImportLimits:
    max_input_bytes: int
    max_records: int
    max_expanded_bytes: int
    max_line_bytes: int
    max_database_bytes: int
    max_storage_bytes: int
    max_seconds: int


def _fail(reason):raise RefreshError('ingredient-import-'+reason)
def _sha(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def prepare_source_import(assets):
    """Code/control-only preparation; no source open/stat/hash or semantic gate."""
    if type(assets) is not tuple or not 1<=len(assets)<=256:_fail('asset-inventory')
    unique={}
    for a in assets:
        if (type(a) is not SourceAsset or any(type(v) is not str or not v for v in
                (a.asset_id,a.path,a.source_id,a.release_id,a.language,a.citation_status))
                or not Path(a.path).is_absolute() or a.kind not in ('products','registry')
                or a.compression not in ('none','gzip') or not _sha(a.sha256)
                or any(type(v) is not int or not 0<v<2**63 for v in (a.bytes,a.records))
                or (a.kind=='products' and (type(a.products) is not int or not 0<=a.products<=a.records))
                or (a.citation_id is not None and (type(a.citation_id) is not str or not a.citation_id))):_fail('asset-descriptor')
        row=strict_json(canonical(asdict(a)))
        if a.asset_id in unique and unique[a.asset_id]!=row:_fail('asset-conflict')
        unique[a.asset_id]=row
    result={'version':VERSION,'schemaPins':SCHEMA_PINS,'assets':list(unique.values()),
            'normalization':'pending; canonical and cross-domain relationships deferred',
            'groupDefinition':'exact source/release/native record key; source groups, not barcode or canonical product identity'}
    if len(canonical(result))>1024**2:_fail('manifest-bound')
    return result


class _Input(io.RawIOBase):
    def __init__(self,fd,expected,check):self.fd=fd;self.expected=expected;self.check=check;self.bytes=0;self.digest=hashlib.sha256()
    def readable(self):return True
    def readinto(self,b):
        self.check();block=os.read(self.fd,min(len(b),65536,self.expected-self.bytes+1))
        self.bytes+=len(block);self.digest.update(block)
        if self.bytes>self.expected:_fail('input-byte-bound')
        b[:len(block)]=block;return len(block)


def _source_row(db,a,ordinal,raw,manifest_sha,counts):
    payload=strict_json(raw)
    pointer='/0' if type(payload) is list and len(payload)==1 and type(payload[0]) is dict else ''
    record=payload[0] if pointer else payload
    if a['kind']=='products':
        if type(record) is not dict:_fail('product-packet')
        if record.get('kind')=='nutrientProfile':counts['non_product']+=1;return
        p=record.get('provenance');data=record.get('data')
        if (record.get('kind')!='product' or type(p) is not dict or type(data) is not dict
                or (p.get('sourceId'),p.get('releaseId'))!=(a['source_id'],a['release_id'])
                or type(p.get('recordId')) is not str or not p['recordId']
                or type(record.get('id')) is not str or not record['id']):_fail('product-source-crosswalk')
        native=record['id'];source_key=p['recordId'];counts['products']+=1
        value=data.get('ingredientsText')
        state=('missing' if 'ingredientsText' not in data else 'null' if value is None else
               'invalid-type' if type(value) is not str else 'empty' if value=='' else 'present')
        language=data.get('language') if type(data.get('language')) is str and data['language'] else a['language']
        status='quarantined' if state=='invalid-type' else 'processed'
    else:
        native=record.get('id') if type(record) is dict and type(record.get('id')) is str else None
        source_key=native;language=record.get('language') if type(record) is dict and type(record.get('language')) is str and record['language'] else a['language']
        state=None;status='processed';counts['registry_records']+=1
    stable='urn:offmenu:source-record:'+_digest([a['asset_id'],a['sha256'],ordinal])
    parsed_sha=_digest(record)
    # Store the exact original JSON line, preserving text/language/number/unit lexemes.
    db.execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
       (stable,a['source_id'],a['release_id'],a['asset_id'],a['sha256'],ordinal,native,pointer,language,
        raw.decode('utf-8'),parsed_sha,a['citation_id'],a['citation_status'],VERSION,VERSION,status))
    counts['stored_source_records']+=1
    if a['kind']=='products':
        counts['declaration_'+state]+=1;counts[status]+=1
        group=canonical([a['source_id'],a['release_id'],source_key]).decode()
        evidence='sqlite:retained_reference_record:'+stable
        db.execute('INSERT INTO product_processing_audit VALUES('+','.join('?'*29)+')',
            (stable,a['asset_id'],manifest_sha,a['sha256'],a['source_id'],a['release_id'],ordinal,
             source_key,native,group,None,state,status,'pending',None,None,'unknown',None,None,None,
             parsed_sha,pointer+'/data/ingredientsText',evidence,parsed_sha,VERSION,VERSION,a['citation_id'],a['citation_status'],
             'source-imported-normalization-pending' if state=='present' else 'source-declaration-'+state))


def _load_asset(db,a,manifest_sha,limits,check):
    key='asset:'+a['asset_id'];spec=_digest(a)
    old=db.execute('SELECT meaning FROM sidecar_schema WHERE version=?',(key,)).fetchone()
    if old:
        old=strict_json(old[0])
        if old.get('specSha256')!=spec or old.get('state')!='complete':_fail('asset-replay-held-or-mismatch')
        return dict(old['counts'],reused=True)
    def checkpoint(state,counts):
        meaning=canonical({'specSha256':spec,'state':state,'asset':a,'counts':counts}).decode()
        db.execute('INSERT INTO sidecar_schema VALUES(?,?,?) ON CONFLICT(version) DO UPDATE SET meaning=excluded.meaning',
                   (key,datetime.now(timezone.utc).isoformat(),meaning))
    counts=dict.fromkeys(('read','bytes','expanded_bytes','products','non_product','registry_records','stored_source_records',
        'processed','quarantined','declaration_present','declaration_missing','declaration_null','declaration_empty','declaration_invalid-type'),0)
    fd=None;reader=None;buffer=None;stream=None
    try:
        checkpoint('loading',counts);db.commit();db.execute('BEGIN IMMEDIATE')
        path=_safe(Path(a['path']));before=path.stat();identity=_identity(before)
        if not stat.S_ISREG(before.st_mode) or before.st_size!=a['bytes']:_fail('input-custody')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        if _identity(os.fstat(fd))!=identity:_fail('input-custody')
        reader=_Input(fd,a['bytes'],check);buffer=io.BufferedReader(reader,65536)
        stream=gzip.GzipFile(fileobj=buffer,mode='rb') if a['compression']=='gzip' else buffer
        while True:
            check();raw=stream.readline(limits.max_line_bytes+1)
            if not raw:break
            counts['read']+=1;counts['expanded_bytes']+=len(raw)
            if (len(raw)>limits.max_line_bytes or not raw.endswith(b'\n') or counts['read']>a['records']
                    or counts['expanded_bytes']>limits.max_expanded_bytes):_fail('record-or-expanded-bound')
            _source_row(db,a,counts['read'],raw,manifest_sha,counts)
        if buffer.read(1):_fail('trailing-input')
        counts['bytes']=reader.bytes
        if (reader.bytes!=a['bytes'] or counts['read']!=a['records'] or reader.digest.hexdigest()!=a['sha256']
                or _identity(os.fstat(fd))!=identity or _identity(_safe(path).stat())!=identity):_fail('input-eof-hash-count-custody')
        if a['kind']=='products' and (counts['products']!=a['products'] or counts['read']!=counts['products']+counts['non_product']):_fail('product-conservation')
        if counts['stored_source_records']!=counts['products']+counts['registry_records']:_fail('source-conservation')
        audit_count=db.execute('SELECT count(*) FROM product_processing_audit WHERE input_asset_id=?',(a['asset_id'],)).fetchone()[0]
        if audit_count!=counts['products']:_fail('product-audit-conservation')
        if counts['processed']+counts['quarantined']!=counts['products']:_fail('processing-conservation')
        counts['groups']=db.execute('SELECT count(DISTINCT group_key) FROM product_processing_audit WHERE input_asset_id=?',(a['asset_id'],)).fetchone()[0]
        counts['unread']=0;checkpoint('complete',counts);db.commit();check();return counts
    except BaseException as error:
        counts['bytes']=reader.bytes if reader is not None else 0
        counts['unread']=max(0,a['records']-counts['read']);counts['error']=type(error).__name__
        try:checkpoint('held',counts);db.commit()
        except sqlite3.Error:db.rollback()
        raise
    finally:
        if stream is not None and stream is not buffer:stream.close()
        if buffer is not None:buffer.close()
        if fd is not None:os.close(fd)


def ingest_source_assets(db,assets,*,limits,input_manifest_sha256,selection_receipt_sha256):
    """Populate a NEW caller-owned private store;57 owns custody/publication/runtime.

    No canonical registry/selector/context witness is needed for raw source import.
    The caller must independently select eligible LOCAL inputs and actual resources.
    """
    manifest=prepare_source_import(assets)
    if (type(db) is not sqlite3.Connection or type(limits) is not ImportLimits
            or any(type(v) is not int or not 0<v<2**63 for v in asdict(limits).values())
            or limits.max_line_bytes>64*1024**2 or not _sha(selection_receipt_sha256)
            or input_manifest_sha256!=_digest(manifest)):_fail('selection-or-limits')
    if (sum(a['bytes'] for a in manifest['assets'])>limits.max_input_bytes
            or sum(a['records'] for a in manifest['assets'])>limits.max_records):_fail('manifest-bound')
    if db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') LIMIT 1").fetchone():_fail('new-empty-store-required')
    db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA temp_store=MEMORY')
    db.execute('PRAGMA cache_size=-8192');db.execute('PRAGMA mmap_size=0');db.execute('PRAGMA synchronous=FULL')
    page=db.execute('PRAGMA page_size').fetchone()[0];db.execute('PRAGMA max_page_count='+str(max(1,limits.max_database_bytes//page)))
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(2**31-1,limits.max_line_bytes*4))
    start=time.monotonic()
    def check():
        if time.monotonic()-start>=limits.max_seconds:_fail('time-bound')
        if db.execute('PRAGMA page_count').fetchone()[0]*page>limits.max_database_bytes:_fail('database-bound')
    db.set_progress_handler(lambda:int(time.monotonic()-start>=limits.max_seconds),1000)
    try:
        db.executescript(DDL)
        db.execute('INSERT INTO sidecar_schema VALUES(?,?,?)',(VERSION,datetime.now(timezone.utc).isoformat(),
            canonical({'manifest':manifest,'inputManifestSha256':input_manifest_sha256,
                       'selectionReceiptSha256':selection_receipt_sha256,'semanticRelationships':'pending'}).decode()));db.commit()
        from dataclasses import replace
        results=[];expanded=0
        for a in manifest['assets']:
            if expanded>=limits.max_expanded_bytes:_fail('expanded-bound')
            counts=_load_asset(db,a,input_manifest_sha256,replace(limits,max_expanded_bytes=limits.max_expanded_bytes-expanded),check)
            expanded+=counts['expanded_bytes'];results.append({'assetId':a['asset_id'],'counts':counts})
        if db.execute('PRAGMA quick_check').fetchone()!=('ok',) or db.execute('PRAGMA foreign_key_check').fetchone():_fail('database-reconciliation')
        tables=('retained_reference_record','product_processing_audit','ingredient_declaration_ref','ingredient_concept','product_ingredient_assertion')
        counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}
        if counts['retained_reference_record']!=sum(r['counts']['stored_source_records'] for r in results):_fail('source-row-conservation')
        if counts['product_processing_audit']!=sum(r['counts']['products'] for r in results):_fail('product-audit-conservation')
        return {'version':VERSION,'inputManifestSha256':input_manifest_sha256,'assets':results,'tableCounts':counts,
                'sourceImportComplete':True,'semanticRelationships':'pending','normalizedConceptFK':'NULL',
                'schemaOnly':False,'runtimeOrResourcesAdmitted':False,'publication':'caller57 must retain/fsync/hash/check custody and publish once; no automatic retry'}
    finally:
        db.set_progress_handler(None,0)
