"""Opt-in private lexical identifier loader. No real-source factory or service.

FETCH supplies citation/asset metadata; trusted application code selects its
qualified native inputs. Input verification shares the single parsing pass.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import threading
import time

from .acceptance import SourceContract, contract_fingerprint
from .core import RefreshError, strict_json, canonical
from .native_barcode_lookup import _binding, _identity
from .off_partition_witness import _descriptor_snapshot
from .product_input_witness import _rename_noreplace
from .product_adapters import _safe

VERSION = 'offmenu-identifier-sqlite/1'
SCHEMA_INTERFACE_SHA256 = '4b57b279d8643dd2b99da48b95b559ae358b613ed2a6a9401e759d5fa099e937'


@dataclass(frozen=True)
class IdentifierInput:
    candidate: str
    asset_id: str
    citations: tuple
    assets: tuple
    producer_job: dict
    lineage_sha256: str
    contract: SourceContract | None
    qualification: dict
    qualification_sha256: str
    identity: tuple | None
    namespace_rules: tuple
    namespace_rule_version: str
    expected_products: int | None = None
    representation: str = 'native-jsonl'
    selected_count: int | None = None
    selected_review_sha256: str | None = None
    asset_bindings: tuple = ()


@dataclass(frozen=True)
class IdentifierLimits:
    max_scan_bytes: int
    max_records: int
    max_line_bytes: int
    max_identifier_bytes: int
    max_identifiers_per_record: int
    max_exceptions: int
    max_database_bytes: int
    max_storage_bytes: int
    max_seconds: int


DDL = """
PRAGMA foreign_keys=ON;
-- Citation/parse additions v2: SOURCE REVIEW ONLY, not executed/migrated.
CREATE TABLE fetch_citation (
 citation_id TEXT PRIMARY KEY NOT NULL,
 fetch_owned_citation_id TEXT,
 identity_state TEXT NOT NULL CHECK(identity_state IN ('fetch-bound','unresolved-backfill')),
 source_id TEXT,
 publisher TEXT,
 release_id TEXT,
 source_url TEXT,
 licence_evidence_url TEXT,
 restrictions_json TEXT,
 unknown_fields_json TEXT NOT NULL,
 fetch_receipt_sha256 TEXT,
 metadata_origin_pointer TEXT NOT NULL,
 CHECK(identity_state<>'fetch-bound' OR fetch_owned_citation_id IS NOT NULL)
);
CREATE TABLE fetch_asset (
 asset_id TEXT PRIMARY KEY NOT NULL,
 fetch_owned_asset_id TEXT,
 citation_id TEXT NOT NULL REFERENCES fetch_citation(citation_id),
 identity_state TEXT NOT NULL CHECK(identity_state IN ('fetch-bound','unresolved-backfill')),
 download_url TEXT,
 original_sha256 TEXT,
 original_bytes INTEGER CHECK(original_bytes>=0),
 retrieved_at TEXT,
 retrieval_clock_state TEXT NOT NULL,
 custody_pointer TEXT,
 custody_receipt_sha256 TEXT,
 unknown_fields_json TEXT NOT NULL,
 CHECK(identity_state<>'fetch-bound' OR fetch_owned_asset_id IS NOT NULL)
);
CREATE TABLE parse_job (
 parse_job_id TEXT PRIMARY KEY NOT NULL,
 input_manifest_sha256 TEXT NOT NULL,
 engine_id TEXT NOT NULL,
 engine_version TEXT NOT NULL,
 engine_code_sha256 TEXT NOT NULL,
 interpretation_mode TEXT NOT NULL CHECK(interpretation_mode IN ('deterministic','cached-interpretation')),
 interpretation_cache_sha256 TEXT,
 input_assets_manifest_sha256 TEXT NOT NULL,
 output_logical_records_sha256 TEXT,
 state TEXT NOT NULL CHECK(state IN ('prepared','running','incomplete','completed','failed')),
 database_created_at TEXT NOT NULL,
 database_completed_at TEXT,
 CHECK(interpretation_mode<>'cached-interpretation' OR interpretation_cache_sha256 IS NOT NULL)
);
-- Minimal private identifier storage contract v1. REVIEW SOURCE ONLY.
-- Not executed, not a migration, not a loader; no actual database path allocated.
-- Apply only in a later selected NEW private database under26/57/64/00 scope.
-- Connection owner must enable/verify foreign_keys; schema alone is no custody proof.
CREATE TABLE identifier_load (
  run_id TEXT PRIMARY KEY NOT NULL,
  input_manifest_sha256 TEXT NOT NULL,
  parse_job_id TEXT NOT NULL REFERENCES parse_job(parse_job_id),
  input_manifest_pointer TEXT NOT NULL,
  loader_version TEXT NOT NULL,
  selection_receipt_sha256 TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('loading','incomplete','completed','completed-with-exceptions','failed')),
  expected_records INTEGER CHECK(expected_records>=0),
  observed_records INTEGER CHECK(observed_records>=0),
  stored_records INTEGER CHECK(stored_records>=0),
  unparsed_record_dispositions INTEGER CHECK(unparsed_record_dispositions>=0),
  identifier_assertions INTEGER CHECK(identifier_assertions>=0),
  invalid_identifiers INTEGER CHECK(invalid_identifiers>=0),
  unresolved_identifiers INTEGER CHECK(unresolved_identifiers>=0),
  exception_count INTEGER CHECK(exception_count>=0),
  finalization_evidence_sha256 TEXT,
  database_created_at TEXT NOT NULL,
  database_completed_at TEXT,
  CHECK(state NOT IN ('completed','completed-with-exceptions') OR finalization_evidence_sha256 IS NOT NULL)
);
CREATE TABLE identifier_input (
  run_id TEXT NOT NULL REFERENCES identifier_load(run_id),
  input_id TEXT NOT NULL,
  asset_id TEXT NOT NULL REFERENCES fetch_asset(asset_id),
  source_id TEXT NOT NULL,
  release_id TEXT NOT NULL,
  artifact_sha256 TEXT NOT NULL,
  artifact_bytes INTEGER NOT NULL CHECK(artifact_bytes>=0),
  original_acquired_at TEXT,
  acquisition_clock_state TEXT NOT NULL,
  operation_evidence_sha256 TEXT NOT NULL,
  PRIMARY KEY(run_id,input_id)
);
CREATE TABLE identifier_source_record (
  run_id TEXT NOT NULL,
  input_id TEXT NOT NULL,
  record_ordinal INTEGER NOT NULL CHECK(record_ordinal>=1),
  source_record_id TEXT,
  native_record_id TEXT,
  source_pointer TEXT NOT NULL,
  parse_job_id TEXT NOT NULL REFERENCES parse_job(parse_job_id),
  source_row INTEGER CHECK(source_row>=1),
  source_page INTEGER CHECK(source_page>=1),
  source_cell TEXT,
  source_record_sha256 TEXT,
  identity_state TEXT NOT NULL CHECK(identity_state IN ('source-asserted','unresolved')),
  PRIMARY KEY(run_id,input_id,record_ordinal),
  FOREIGN KEY(run_id,input_id) REFERENCES identifier_input(run_id,input_id)
);
CREATE TABLE identifier_assertion (
  assertion_id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL,
  input_id TEXT NOT NULL,
  record_ordinal INTEGER NOT NULL,
  identifier_ordinal INTEGER NOT NULL CHECK(identifier_ordinal>=1),
  namespace TEXT COLLATE BINARY,
  lexical_value TEXT COLLATE BINARY,
  symbology TEXT,
  source_pointer TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK(disposition IN ('source-asserted','invalid','unresolved')),
  reason_code TEXT,
  UNIQUE(run_id,input_id,record_ordinal,identifier_ordinal),
  FOREIGN KEY(run_id,input_id,record_ordinal)
    REFERENCES identifier_source_record(run_id,input_id,record_ordinal),
  CHECK(disposition<>'source-asserted' OR
        (typeof(namespace)='text' AND length(namespace)>0 AND
         typeof(lexical_value)='text' AND length(lexical_value)>0)),
  CHECK(disposition='source-asserted' OR reason_code IS NOT NULL)
);
-- Deliberately NONUNIQUE namespace/value: preserve all assertions and collisions.
CREATE INDEX identifier_lookup ON identifier_assertion
  (run_id,namespace,lexical_value,disposition,assertion_id);
CREATE INDEX identifier_source_crosswalk ON identifier_source_record
  (run_id,input_id,source_record_id,record_ordinal);
CREATE TABLE identifier_exception (
  run_id TEXT NOT NULL REFERENCES identifier_load(run_id),
  exception_ordinal INTEGER NOT NULL CHECK(exception_ordinal>=1),
  input_id TEXT,
  record_ordinal INTEGER,
  identifier_ordinal INTEGER,
  source_pointer TEXT,
  reason_code TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK(disposition IN ('invalid','unresolved','unparsed','fatal')),
  PRIMARY KEY(run_id,exception_ordinal),
  FOREIGN KEY(run_id,input_id) REFERENCES identifier_input(run_id,input_id)
);
-- Source ordinal identity retained; no canonical product/formulation/lot joins.
CREATE VIEW barcode_identifier_inspection AS
SELECT a.assertion_id,a.run_id,a.input_id,i.source_id,i.release_id,
       i.artifact_sha256,r.record_ordinal,r.source_record_id,r.native_record_id,
       r.identity_state,r.parse_job_id,i.asset_id,fa.citation_id,
       a.identifier_ordinal,a.namespace,a.lexical_value,
       a.symbology,a.source_pointer,a.disposition,a.reason_code,
       l.input_manifest_sha256,l.state AS load_state,l.finalization_evidence_sha256
FROM identifier_assertion a
JOIN identifier_source_record r ON r.run_id=a.run_id AND r.input_id=a.input_id
 AND r.record_ordinal=a.record_ordinal
JOIN identifier_input i ON i.run_id=a.run_id AND i.input_id=a.input_id
JOIN identifier_load l ON l.run_id=a.run_id
JOIN fetch_asset fa ON fa.asset_id=i.asset_id;
CREATE INDEX identifier_disposition_page ON identifier_assertion
  (run_id,disposition,assertion_id);

CREATE TABLE load_checkpoint (
 run_id TEXT NOT NULL,
 checkpoint_ordinal INTEGER NOT NULL CHECK(checkpoint_ordinal>=1),
 parse_job_id TEXT NOT NULL REFERENCES parse_job(parse_job_id),
 input_id TEXT NOT NULL,
 last_committed_record_ordinal INTEGER CHECK(last_committed_record_ordinal>=0),
 examined_record_occurrences INTEGER NOT NULL CHECK(examined_record_occurrences>=0),
 examined_identifier_occurrences INTEGER NOT NULL CHECK(examined_identifier_occurrences>=0),
 accounting_sha256 TEXT NOT NULL,
 source_position_json TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('committed','incomplete','failed')),
 database_checkpoint_at TEXT NOT NULL,
 PRIMARY KEY(run_id,checkpoint_ordinal),
 FOREIGN KEY(run_id,input_id) REFERENCES identifier_input(run_id,input_id)
);
CREATE INDEX asset_citation ON fetch_asset(citation_id,asset_id);
CREATE INDEX record_parse_job ON identifier_source_record(parse_job_id,run_id,input_id,record_ordinal);
CREATE INDEX checkpoint_input ON load_checkpoint(run_id,input_id,checkpoint_ordinal);

-- Loader metadata extensions; the nine13v2 core tables/constraints above remain intact.
CREATE TABLE identifier(identifier_id INTEGER PRIMARY KEY,namespace TEXT COLLATE BINARY NOT NULL,
 lexical_value TEXT COLLATE BINARY NOT NULL,syntax_assessment TEXT NOT NULL,checksum_assessment TEXT NOT NULL,
 UNIQUE(namespace,lexical_value));
CREATE TABLE asset_lineage(asset_id TEXT REFERENCES fetch_asset,parent_asset_id TEXT REFERENCES fetch_asset,
 PRIMARY KEY(asset_id,parent_asset_id));
ALTER TABLE fetch_citation ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE fetch_asset ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE identifier_input ADD COLUMN spec_sha256 TEXT;
ALTER TABLE identifier_input ADD COLUMN expected_records INTEGER;
ALTER TABLE identifier_input ADD COLUMN status TEXT NOT NULL DEFAULT 'loading';
ALTER TABLE identifier_input ADD COLUMN counts_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE identifier_input ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE parse_job ADD COLUMN producer_job_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE parse_job ADD COLUMN checkpoint_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE identifier_source_record ADD COLUMN raw_line_sha256 TEXT;
ALTER TABLE identifier_source_record ADD COLUMN kind TEXT;
ALTER TABLE identifier_source_record ADD COLUMN verbatim_name TEXT;
ALTER TABLE identifier_source_record ADD COLUMN name_language TEXT;
ALTER TABLE identifier_source_record ADD COLUMN source_disposition TEXT;
ALTER TABLE identifier_source_record ADD COLUMN identifier_state TEXT;
ALTER TABLE identifier_source_record ADD COLUMN native_candidate_ordinal INTEGER;
ALTER TABLE identifier_assertion ADD COLUMN identifier_id INTEGER REFERENCES identifier(identifier_id);
ALTER TABLE identifier_assertion ADD COLUMN raw_json TEXT;
ALTER TABLE identifier_assertion ADD COLUMN raw_sha256 TEXT;
ALTER TABLE identifier_assertion ADD COLUMN raw_bytes INTEGER;
ALTER TABLE identifier_assertion ADD COLUMN reasons_json TEXT;
ALTER TABLE identifier_assertion ADD COLUMN policy_disposition TEXT;
ALTER TABLE identifier_exception ADD COLUMN details_json TEXT;
ALTER TABLE identifier_load ADD COLUMN pending_sources_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE identifier_load ADD COLUMN summary_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE identifier_load ADD COLUMN schema_interface_sha256 TEXT;
CREATE INDEX native_source_lookup ON identifier_source_record(native_record_id,source_record_sha256);
CREATE INDEX identifier_pool_assertion ON identifier_assertion(identifier_id,assertion_id);
CREATE INDEX identifier_input_key_accounting ON identifier_assertion(run_id,input_id,identifier_id);
CREATE VIEW v_barcode_inspection AS SELECT CAST(a.assertion_id AS TEXT) AS identifier_assertion_id,
 a.namespace,a.lexical_value,a.symbology,r.input_id||':row:'||r.record_ordinal AS source_record_key,
 r.source_record_id,r.verbatim_name AS scanned_product_name,NULL AS product_id,i.source_id,i.release_id,
 i.asset_id||':record:'||r.record_ordinal||':identifier:'||a.identifier_ordinal AS evidence_id,
 a.disposition AS assertion_status,l.loader_version AS decision_version,NULL AS recorded_context_links
 FROM identifier_assertion a JOIN identifier_source_record r USING(run_id,input_id,record_ordinal)
 JOIN identifier_input i USING(run_id,input_id) JOIN identifier_load l USING(run_id);
"""


def _fail(code):
    raise RefreshError('identifier-db-'+code)


def _sha(value):
    return type(value) is str and bool(re.fullmatch('[0-9a-f]{64}',value))


def _off_binding(spec):
    """Metadata-audit binding, deliberately not a product SourceContract."""
    q=strict_json(canonical(spec.qualification))
    if (spec.contract is not None or hashlib.sha256(canonical(q)).hexdigest()!=spec.qualification_sha256
            or q.get('schemaVersion')!='offmenu-off-occurrence-metadata-binding/1'
            or (q.get('sourceId'),q.get('releaseId'))!=('off','2026-10-12')
            or type(q.get('fixture')) is not bool or not _sha(q.get('candidateSha256'))
            or not _sha(q.get('originalSha256')) or not _sha(q.get('metadataReviewSha256'))
            or type(q.get('scopeId')) is not str or not q['scopeId']):_fail('off-metadata-binding')
    counts=q.get('counts',{})
    if (set(counts)!={'S','C','Q'} or any(type(v) is not int or v<0 for v in counts.values())
            or type(q.get('normalizedRecords')) is not int or q['normalizedRecords']<=0
            or sum(counts.values())!=q['normalizedRecords'] or type(q.get('groups')) is not int
            or not 0<=q['groups']<=counts['C']//2
            or q.get('distinctValidKeys')!=counts['S']+q['groups']):_fail('off-metadata-counts')
    originals=q.get('originalInputs')
    if (type(originals) is not list or len(originals)!=1 or originals[0].get('sha256')!=q['originalSha256']
            or type(originals[0].get('bytes')) is not int or originals[0]['bytes']<=0
            or type(originals[0].get('path')) is not str):_fail('off-original-binding')
    if not q['fixture'] and (q['normalizedRecords']!=4807663 or counts!={'S':4807156,'C':122,'Q':385}
            or q['groups']!=61 or q['candidateSha256']!=OFF_OCCURRENCES_SHA256
            or q['originalSha256']!=OFF_ORIGINAL_SHA256 or q['metadataReviewSha256']!=OFF_METADATA_REVIEW_SHA256
            or originals!=[{'path':'off-2026-10-12.jsonl.gz','bytes':13132516914,'sha256':OFF_ORIGINAL_SHA256}]):_fail('off-known-release-binding')
    return q


def _prepare(spec):
    if type(spec) is not IdentifierInput: _fail('input-descriptor')
    off=spec.representation=='verified-off-occurrences-jsonl'
    q = _off_binding(spec) if off else _binding(spec.contract,spec.qualification,spec.qualification_sha256)
    lineage = {'citations':spec.citations,'assets':spec.assets,'producerJob':spec.producer_job,
               'namespaceRules':spec.namespace_rules,'namespaceRuleVersion':spec.namespace_rule_version,
               'representation':spec.representation,'selectedCount':spec.selected_count,
               'selectedReviewSha256':spec.selected_review_sha256,'assetBindings':spec.asset_bindings}
    raw = canonical(lineage)
    if len(raw)>1024**2 or hashlib.sha256(raw).hexdigest()!=spec.lineage_sha256: _fail('lineage-binding')
    data = strict_json(raw)  # Freeze mutable caller metadata before any source IO.
    citations=[];assets=[]
    bindings={b['id']:b for b in data['assetBindings']}
    for original in data['citations']:
        c=dict(original);c['fetch_metadata']=original;c['id']=c.get('id',c.get('citation_id'))
        c.setdefault('retrieved_at',None);c.setdefault('restrictions',c.get('restrictions_json'))
        c.setdefault('unknowns',c.get('unknown_fields_json',[]));c.setdefault('receipt',c.get('metadata_origin_pointer','unresolved-backfill'))
        for field in ('restrictions','unknowns'):
            if type(c[field]) is str:c[field]=strict_json(c[field])
        citations.append(c)
    for original in data['assets']:
        a=dict(original);a['fetch_metadata']=original;a['id']=a.get('id',a.get('asset_id'))
        a.setdefault('unknowns',a.get('unknown_fields_json',[]))
        if type(a['unknowns']) is str:a['unknowns']=strict_json(a['unknowns'])
        a.update(bindings.get(a['id'],{}));assets.append(a)
    data['citations']=citations;data['assets']=assets
    if not 1<=len(citations)<=64 or not 1<=len(assets)<=64: _fail('lineage-inventory')
    ids = [a.get('id') for a in assets]; cids = [c.get('id') for c in citations]
    if (any(type(x) is not str or not x for x in ids+cids)
            or len(set(ids))!=len(ids) or len(set(cids))!=len(cids)): _fail('fetch-ids')
    for citation in citations:
        if not {'id','source_url','publisher','release_id','retrieved_at','licence_evidence_url',
                'restrictions','unknowns','receipt'}<=set(citation): _fail('citation-metadata-required')
    for asset in assets:
        if (asset.get('citation_id') not in cids or type(asset.get('logical_path')) is not str
                or type(asset.get('bytes')) is not int or asset['bytes']<=0 or not _sha(asset.get('sha256'))
                or type(asset.get('parent_asset_ids')) is not list
                or any(p not in ids or p==asset['id'] for p in asset['parent_asset_ids'])
                or 'custody_ref' not in asset): _fail('asset-metadata-required')
    byid = {a['id']:a for a in assets}
    def ancestors(key,seen):
        if key in seen: _fail('lineage-cycle')
        parents = byid[key]['parent_asset_ids']
        return set(parents).union(*(ancestors(p,seen|{key}) for p in parents))
    if spec.asset_id not in byid: _fail('candidate-asset-required')
    candidate = byid[spec.asset_id]
    if spec.representation=='native-jsonl':
        if candidate['sha256']!=q['candidateSha256'] or spec.selected_count is not None: _fail('candidate-pin')
        expected=q['normalizedRecords']
    elif spec.representation=='reviewed-native-lookup-json':
        if (q['sourceId']!='usda-files' or type(spec.selected_count) is not int or not 1<=spec.selected_count<=1000
                or not _sha(spec.selected_review_sha256) or candidate['bytes']>1024**2): _fail('selected-lookup-binding')
        expected=spec.selected_count
    elif off:
        if (candidate['sha256']!=q['candidateSha256'] or spec.selected_count is not None
                or spec.expected_products!=0 or spec.namespace_rules!=(('barcode','barcode'),)
                or (not q['fixture'] and candidate['bytes']!=1656721116)):_fail('off-candidate-binding')
        expected=q['normalizedRecords']
    else: _fail('input-representation')
    original = ancestors(spec.asset_id,set())
    if off:
        original_inputs=q['originalInputs'];required_originals=original_inputs
    else:
        original_inputs=[vars(a) for a in spec.contract.inputs]
        evidence={spec.contract.rights_evidence.path,spec.contract.scope_evidence.path}
        if spec.contract.clock_evidence:evidence.add(spec.contract.clock_evidence.path)
        required_originals=[a for a in original_inputs if a['path'] not in evidence]
    for asset in required_originals:
        if not any(byid[p]['logical_path']==asset['path'] and byid[p]['bytes']==asset['bytes']
                   and byid[p]['sha256']==asset['sha256'] for p in original): _fail('original-lineage-required')
    producer = data['producerJob']
    if (not all(type(producer.get(k)) is str and producer[k] for k in ('id','receipt'))
            or any(not (type(producer.get(k)) is str and producer[k]) and k not in producer.get('unknowns',[]) for k in ('engine','version'))
            or producer.get('output_sha256')!=candidate['sha256']): _fail('producer-job-required')
    rules = data['namespaceRules']
    if (not 1<=len(rules)<=64 or any(type(p) is not list or len(p)!=2
            or any(type(s) is not str or not 0<len(s)<=256 for s in p) for p in rules)
            or len(dict(rules))!=len(rules) or not data['namespaceRuleVersion']): _fail('namespace-rules')
    if ((spec.identity is not None and (type(spec.identity) is not tuple or len(spec.identity)!=5
                 or any(type(v) is not int or v<0 for v in spec.identity) or spec.identity[2]!=candidate['bytes']))
            or (spec.expected_products is not None and (type(spec.expected_products) is not int
                  or not 0<=spec.expected_products<=expected))): _fail('input-identity-or-count')
    data.update(candidate=spec.candidate,assetId=spec.asset_id,identity=spec.identity,
                sourceId=q['sourceId'],releaseId=q['releaseId'],scopeId=q['scopeId'],
                qualificationSha256=spec.qualification_sha256,contractSha256=None if off else contract_fingerprint(spec.contract),
                expectedRecords=expected,expectedProducts=spec.expected_products,
                upstreamExpectedRecords=q['normalizedRecords'],upstreamCandidateSha256=q['candidateSha256'],
                originalContractInputs=original_inputs,
                acquiredAt=None if off else spec.contract.acquired_at,acquisitionClockStatus='unknown-retained' if off else spec.contract.acquisition_clock_status,
                candidateBytes=candidate['bytes'],candidateSha256=candidate['sha256'],fixture=q['fixture'])
    if off:data['occurrenceAudit']=q
    data['specSha256'] = hashlib.sha256(canonical(data)).hexdigest()
    return data


def _assessment(namespace,value):
    if namespace!='barcode': return 'source-lexical','not-assessed-other-namespace'
    if not re.fullmatch('[0-9]+',value): return 'not-ascii-digits','not-assessed'
    if len(value) not in (8,12,13,14): return 'unsupported-checksum-length','not-assessed'
    total = sum(int(v)*(3 if i%2==0 else 1) for i,v in enumerate(reversed(value[:-1])))
    return 'digits-supported-length',('valid' if int(value[-1])==(10-total%10)%10 else 'invalid')


def _identifier(value,rules,max_bytes):
    raw = canonical(value); reasons=[]
    if type(value) is not dict: return 'other-invalid',None,None,raw,['not-object']
    system = value.get('system'); lexical = value.get('value')
    if 'value' not in value or lexical is None: reasons.append('missing-or-null-value')
    elif type(lexical) is not str: reasons.append('nonstring-value')
    elif lexical=='': reasons.append('empty-value')
    if type(system) is not str or system not in rules: reasons.append('unknown-namespace')
    if len(raw)>max_bytes: reasons.append('identifier-byte-bound')
    if type(lexical) is str and '\x00' in lexical:reasons.append('nul-in-lexical-value')
    if reasons:
        first=reasons[0]
        return ({'missing-or-null-value':'missing-null','nonstring-value':'invalid-nonstring',
                 'empty-value':'empty','unknown-namespace':'unknown-namespace'}.get(first,'other-invalid'),
                rules.get(system) if type(system) is str else None,
                lexical if type(lexical) is str and len(raw)<=max_bytes else None,raw,reasons)
    return 'eligible',rules[system],lexical,raw,[]


def _insert_metadata(db,table,key,value):
    encoded=canonical(value.get('fetch_metadata',value)).decode()
    old=db.execute(f'SELECT metadata_json FROM {table} WHERE {key}=?',(value['id'],)).fetchone()
    if old:
        if old[0]!=encoded: _fail('fetch-metadata-conflict')
        return
    if table=='fetch_citation':
        db.execute('INSERT INTO fetch_citation(citation_id,fetch_owned_citation_id,identity_state,source_id,publisher,release_id,source_url,licence_evidence_url,restrictions_json,unknown_fields_json,fetch_receipt_sha256,metadata_origin_pointer,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
          (value['id'],value.get('fetch_owned_citation_id'),value.get('identity_state','unresolved-backfill'),
           value.get('source_id'),value.get('publisher'),value.get('release_id'),value.get('source_url'),
           value.get('licence_evidence_url'),canonical(value.get('restrictions')).decode(),
           canonical(value.get('unknowns',[])).decode(),value.get('fetch_receipt_sha256'),
           value.get('metadata_origin_pointer',value.get('receipt','unresolved-backfill')),encoded))
    else:
        db.execute('INSERT INTO fetch_asset(asset_id,fetch_owned_asset_id,citation_id,identity_state,download_url,original_sha256,original_bytes,retrieved_at,retrieval_clock_state,custody_pointer,custody_receipt_sha256,unknown_fields_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
          (value['id'],value.get('fetch_owned_asset_id'),value['citation_id'],value.get('identity_state','unresolved-backfill'),
           value.get('download_url'),value.get('original_sha256'),value.get('original_bytes'),value.get('retrieved_at'),
           value.get('retrieval_clock_state','unknown-retained'),value.get('custody_pointer',value.get('custody_ref')),
           value.get('custody_receipt_sha256'),canonical(value.get('unknowns',[])).decode(),encoded))


def _exception(db,counts,m,ordinal,field,code,details,limits,*,disposition='unresolved'):
    counts['exceptions']+=1
    last=db.execute('SELECT coalesce(max(exception_ordinal),0) FROM identifier_exception WHERE run_id=?',(m['runId'],)).fetchone()[0]
    if last>=limits.max_exceptions: _fail('exception-bound')
    db.execute('INSERT INTO identifier_exception(run_id,exception_ordinal,input_id,record_ordinal,identifier_ordinal,source_pointer,reason_code,disposition,details_json) VALUES(?,?,?,?,?,?,?,?,?)',
       (m['runId'],last+1,m['inputId'],ordinal,field+1 if field is not None else None,
        details.get('sourcePointer'),code,'fatal' if code=='malformed-or-wrong-scope' else disposition,canonical(details).decode()))


def _entity(db,namespace,lexical,counts):
    syntax,checksum=_assessment(namespace,lexical)
    inserted=db.execute('INSERT OR IGNORE INTO identifier(namespace,lexical_value,syntax_assessment,checksum_assessment) VALUES(?,?,?,?)',(namespace,lexical,syntax,checksum))
    counts['new_identifiers']+=inserted.rowcount
    return db.execute('SELECT identifier_id FROM identifier WHERE namespace=? AND lexical_value=?',(namespace,lexical)).fetchone()[0]


def _assertion(db,m,ordinal,index,namespace,lexical,pointer,primary,reason,identifier,encoded,reasons,status,limits,projection):
    raw_hash=hashlib.sha256(encoded).hexdigest() if encoded is not None else None
    raw_bytes=len(encoded) if encoded is not None else None
    db.execute('INSERT INTO identifier_assertion(run_id,input_id,record_ordinal,identifier_ordinal,namespace,lexical_value,source_pointer,disposition,reason_code,identifier_id,raw_json,raw_sha256,raw_bytes,reasons_json,policy_disposition) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (m['runId'],m['inputId'],ordinal,index+1,namespace,lexical,pointer,primary,reason,identifier,
       encoded.decode() if encoded is not None and len(encoded)<=limits.max_identifier_bytes else None,
       raw_hash,raw_bytes,canonical(reasons).decode(),status))
    projection.update(canonical(['identifier',ordinal,index+1,status,raw_hash]))
    return raw_hash


def _record_off(db,m,job,ordinal,raw,counts,limits,projection):
    row=strict_json(raw);q=m['occurrenceAudit']
    if (type(row) is not dict or set(row)!={'ordinal','originalSha256','table','code','status','rawLineSha256','canonicalBodySha256','reason'}
            or canonical(row)!=raw or type(row['ordinal']) is not int or row['ordinal']!=ordinal
            or row['originalSha256']!=q['originalSha256'] or row['table']!='products'
            or not _sha(row['rawLineSha256']) or not _sha(row['canonicalBodySha256'])):_fail('off-occurrence-identity')
    status=row['status'];code=row['code']
    if status not in ('S','C','Q'):_fail('off-occurrence-status')
    if status=='Q':
        if code is not None or row['reason']!='native-code-invalid':_fail('off-quarantine')
    elif (type(code) is not str or re.fullmatch('[0-9]{4,32}',code) is None
            or row['reason']!=(None if status=='S' else 'repeated-native-key')):_fail('off-occurrence-code')
    counts['off_'+status]=counts.get('off_'+status,0)+1
    if counts['off_'+status]>q['counts'][status]:_fail('off-partition-count')
    counts['source_new']+=1;counts['non_product']+=1;counts['identifier_occurrences']+=1
    # This is a source occurrence, never a manufactured product or profile.
    native='off:sourceOccurrence:'+q['originalSha256']+':'+str(ordinal)
    db.execute('INSERT INTO identifier_source_record(run_id,input_id,record_ordinal,source_record_id,native_record_id,source_pointer,parse_job_id,source_row,source_record_sha256,identity_state,raw_line_sha256,kind,source_disposition,identifier_state,native_candidate_ordinal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (m['runId'],m['inputId'],ordinal,str(ordinal),native,'/code',job,ordinal,row['canonicalBodySha256'],
       'source-asserted' if status=='S' else 'unresolved',row['rawLineSha256'],'sourceOccurrence','new',status,ordinal))
    primary='source-asserted' if status=='S' else 'unresolved' if status=='C' else 'invalid'
    identifier=None;encoded=None
    if status!='Q':
        counts['identifiers_eligible']+=1;identifier=_entity(db,'barcode',code,counts)
        # The actual metadata code field, not an invented native identifier object.
        encoded=canonical(code)
    else:counts['identifiers_other-invalid']+=1
    reasons=[] if status=='S' else [row['reason']]
    raw_hash=_assertion(db,m,ordinal,0,'barcode',code,'/code',primary,row['reason'],identifier,encoded,reasons,
                       'off-'+status,limits,projection)
    projection.update(canonical(['off-occurrence',ordinal,status,row['rawLineSha256'],row['canonicalBodySha256']]))
    if status!='S':_exception(db,counts,m,ordinal,0,row['reason'],
        {'sourcePointer':'/code','originalOrdinal':ordinal,'rawLineSha256':row['rawLineSha256'],
         'canonicalBodySha256':row['canonicalBodySha256'],'rawSha256':raw_hash,
         'bytes':len(encoded) if encoded is not None else None,'rawIdentifierEvidence':'unavailable' if status=='Q' else 'metadata-code-field',
         'selectedPrimary':None,'reasons':reasons},limits,disposition=primary)
    return True


def _record(db,m,job,ordinal,raw,counts,limits,projection,locator=None):
    raw_sha=hashlib.sha256(raw).hexdigest() if locator is None else None
    pointer='/0' if locator is None else locator['pointer']
    native_ordinal=ordinal if locator is None else locator['nativeCandidateOrdinal']
    row=None;error=None
    try:
        packet=strict_json(raw)
        if type(packet) is not list or len(packet)!=1 or type(packet[0]) is not dict: raise ValueError()
        row=packet[0];p=row.get('provenance');kind=row.get('kind');native=row.get('id')
        if (type(p) is not dict or (p.get('sourceId'),p.get('releaseId'))!=(m['sourceId'],m['releaseId'])
             or p.get('visibility')!='private-candidate' or type(native) is not str or not native
             or type(p.get('recordId')) is not str or not p['recordId'] or type(kind) is not str):raise ValueError()
        content_sha=hashlib.sha256(canonical(row)).hexdigest()
    except (ValueError,TypeError,UnicodeError,OverflowError,RefreshError):error='malformed-or-wrong-scope'
    key=(m['runId'],m['inputId'],ordinal)
    if error:
        counts['source_malformed']+=1
        db.execute('INSERT INTO identifier_source_record(run_id,input_id,record_ordinal,source_pointer,parse_job_id,identity_state,raw_line_sha256,source_disposition,identifier_state,native_candidate_ordinal) VALUES(?,?,?,?,?,?,?,?,?,?)',
            key+(pointer,job,'unresolved',raw_sha,'malformed','unread',native_ordinal))
        _exception(db,counts,m,ordinal,None,error,{'rawLineSha256':raw_sha,'sourcePointer':pointer},limits)
        return False
    source_query=('SELECT r.source_record_sha256 FROM identifier_source_record r JOIN identifier_input i USING(run_id,input_id) '
        'WHERE i.source_id=? AND i.release_id=? AND r.native_record_id=? ')
    args=(m['sourceId'],m['releaseId'],native)
    previous=db.execute(source_query+'LIMIT 1',args).fetchone()
    identical=db.execute(source_query+'AND r.source_record_sha256=? LIMIT 1',args+(content_sha,)).fetchone() if previous else None
    disposition='new' if not previous else 'identical' if identical else 'conflicting'
    counts['source_'+disposition]+=1
    data=row.get('data');data=data if type(data) is dict else {}
    name=data.get('name');language=data.get('language');values=data.get('identifiers')
    state=('not-product' if kind!='product' else 'missing' if 'identifiers' not in data else 'null' if values is None
           else 'invalid-container' if type(values) is not list else 'empty' if not values else 'list')
    source_row=p.get('sourceRow');source_row=source_row if type(source_row) is int and source_row>0 else None
    db.execute('INSERT INTO identifier_source_record(run_id,input_id,record_ordinal,source_record_id,native_record_id,source_pointer,parse_job_id,source_row,source_record_sha256,identity_state,raw_line_sha256,kind,verbatim_name,name_language,source_disposition,identifier_state,native_candidate_ordinal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
       key+(p['recordId'],native,pointer,job,source_row,content_sha,'source-asserted',raw_sha,kind,
            name if type(name) is str else None,language if type(language) is str else None,disposition,state,native_ordinal))
    projection.update(canonical(['record',ordinal,native,p['recordId'],kind,raw_sha,content_sha,disposition,state,pointer,native_ordinal]))
    if disposition=='conflicting':_exception(db,counts,m,ordinal,None,'same-source-key-conflict',{'recordSha256':content_sha},limits)
    if kind!='product':counts['non_product']+=1;return True
    counts['products']+=1
    if state!='list':
        counts['products_no_identifiers']+=1
        _exception(db,counts,m,ordinal,None,'identifier-container-'+state,{'state':state},limits)
        return True
    if len(values)>limits.max_identifiers_per_record:_fail('identifier-list-bound')
    eligible=0;barcode_seen=False
    for index,value in enumerate(values):
        status,namespace,lexical,encoded,reasons=_identifier(value,dict(m['namespaceRules']),limits.max_identifier_bytes)
        counts['identifier_occurrences']+=1;counts['identifiers_'+status]+=1
        if type(value) is dict and value.get('system')=='barcode':barcode_seen=True
        identifier=None
        if status=='eligible':
            eligible+=1;identifier=_entity(db,namespace,lexical,counts)
        primary='source-asserted' if status=='eligible' else 'unresolved' if status in ('missing-null','unknown-namespace') else 'invalid'
        raw_hash=_assertion(db,m,ordinal,index,namespace,lexical,pointer+'/data/identifiers/'+str(index),primary,
            None if status=='eligible' else status,identifier,encoded,reasons,status,limits,projection)
        if status!='eligible':_exception(db,counts,m,ordinal,index,status,{'rawSha256':raw_hash,'bytes':len(encoded),'reasons':reasons,
            'sourcePointer':pointer+'/data/identifiers/'+str(index)},limits,disposition=primary)
    counts['products_with_eligible' if eligible else 'products_only_unresolved']+=1
    counts['products_missing_barcode_entry']+=int(not barcode_seen)
    return True


def _counts():
    keys=('read','bytes','products','non_product','source_new','source_identical','source_conflicting','source_malformed',
          'identifier_occurrences','new_identifiers','exceptions','products_no_identifiers',
          'products_with_eligible','products_only_unresolved','products_missing_barcode_entry')
    result=dict.fromkeys(keys,0)
    result.update({'identifiers_'+k:0 for k in ('eligible','invalid-nonstring','empty','missing-null','unknown-namespace','other-invalid')})
    return result


def _lookup_records(raw,m):
    document=strict_json(raw)
    base='/lookup' if type(document) is dict and type(document.get('lookup')) is dict else ''
    wrapper=document['lookup'] if base else document
    if base and document.get('status')!='PRIVATE_NATIVE_LOOKUP_VERIFIED':_fail('lookup-envelope-status')
    if (type(wrapper) is not dict or (wrapper.get('sourceId'),wrapper.get('releaseId'),wrapper.get('scopeId'))
            !=(m['sourceId'],m['releaseId'],m['scopeId']) or wrapper.get('candidateSha256')!=m['upstreamCandidateSha256']
            or wrapper.get('qualificationSha256')!=m['qualificationSha256'] or wrapper.get('visibility')!='private'
            or type(wrapper.get('fixture')) is not bool or wrapper['fixture']!=m['fixture']
            or wrapper.get('status')!='matched' or type(wrapper.get('matches')) is not list
            or len(wrapper['matches'])!=m['expectedRecords'] or type(wrapper.get('barcode')) is not str): _fail('lookup-wrapper-binding')
    native_ids=set();source_ids=set();previous=0
    for index,match in enumerate(wrapper['matches']):
        if type(match) is not dict or type(match.get('record')) is not dict: _fail('lookup-match-binding')
        row=match['record'];p=row.get('provenance',{});line=match.get('candidateLine')
        ids=row.get('data',{}).get('identifiers')
        if (type(p) is not dict or match.get('nativeProductId')!=row.get('id')
                or match.get('sourceRecordId')!=p.get('recordId') or row.get('kind')!='product'
                or type(line) is not int or not previous<line<=m['upstreamExpectedRecords'] or type(ids) is not list
                or not any(type(i) is dict and i.get('system')=='barcode' and type(i.get('value')) is str
                           and i['value']==wrapper['barcode'] for i in ids)): _fail('lookup-match-binding')
        if row['id'] in native_ids or p['recordId'] in source_ids:_fail('lookup-duplicate-observation')
        native_ids.add(row['id']);source_ids.add(p['recordId']);previous=line
        yield canonical([row]),{'pointer':f'{base}/matches/{index}/record','nativeCandidateOrdinal':line}


def _new_job(db,job,manifest_sha,producer):
    db.execute('INSERT INTO parse_job(parse_job_id,input_manifest_sha256,engine_id,engine_version,engine_code_sha256,interpretation_mode,input_assets_manifest_sha256,state,database_created_at,producer_job_json) VALUES(?,?,?,?,?,?,?,?,?,?)',
      (job,manifest_sha,'deterministic-native-identifier-projection',VERSION,hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'deterministic',manifest_sha,'running',datetime.now(timezone.utc).isoformat(),canonical(producer).decode()))


def _load_asset(db,m,limits,check):
    run=m['runId'];input_id=m['assetId'];m=dict(m,inputId=input_id)
    old=db.execute('SELECT spec_sha256,status,counts_json FROM identifier_input WHERE run_id=? AND input_id=?',(run,input_id)).fetchone()
    if old:
        if old[0]!=m['specSha256'] or old[1]!='complete':_fail('asset-replay-mismatch-or-held')
        counts=strict_json(old[2])
        if db.execute('SELECT count(*) FROM identifier_source_record WHERE run_id=? AND input_id=?',(run,input_id)).fetchone()[0]!=counts['read']:_fail('asset-checkpoint-mismatch')
        return counts,True
    for c in m['citations']:_insert_metadata(db,'fetch_citation','citation_id',c)
    for a in m['assets']:_insert_metadata(db,'fetch_asset','asset_id',a)
    for a in m['assets']:
        for parent in a['parent_asset_ids']:db.execute('INSERT OR IGNORE INTO asset_lineage VALUES(?,?)',(a['id'],parent))
    db.execute('INSERT INTO identifier_input(run_id,input_id,asset_id,source_id,release_id,artifact_sha256,artifact_bytes,original_acquired_at,acquisition_clock_state,operation_evidence_sha256,spec_sha256,expected_records,status,counts_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (run,input_id,m['assetId'],m['sourceId'],m['releaseId'],m['candidateSha256'],m['candidateBytes'],m.get('acquiredAt'),m.get('acquisitionClockStatus','unknown-retained'),m['specSha256'],m['specSha256'],m['expectedRecords'],'loading','{}',canonical(m).decode()))
    job=run+'/asset/'+hashlib.sha256(input_id.encode()).hexdigest()[:24]
    _new_job(db,job,m['manifestSha'],m['producerJob'])
    db.commit();counts=_counts();digest=hashlib.sha256();projection=hashlib.sha256();fd=None
    previous_identifier_max=db.execute('SELECT coalesce(max(identifier_id),0) FROM identifier').fetchone()[0]
    try:
        db.execute('BEGIN IMMEDIATE')
        path=_safe(Path(m['candidate'])); before=path.stat()
        expected_identity=tuple(m['identity']) if m['identity'] is not None else _identity(before)
        if (not stat.S_ISREG(before.st_mode) or before.st_size!=m['candidateBytes']
                or _identity(before)!=expected_identity): _fail('input-custody')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        if _identity(os.fstat(fd))!=expected_identity: _fail('input-custody')
        counts['observed_input_identity']=expected_identity
        fatal=False
        with os.fdopen(fd,'rb',closefd=False) as stream:
            if m['representation']=='reviewed-native-lookup-json':
                raw=stream.read(min(limits.max_line_bytes,m['candidateBytes'])+1)
                counts['bytes']=len(raw);digest.update(raw)
                if len(raw)!=m['candidateBytes'] or stream.read(1): _fail('lookup-document-bound')
                for row,locator in _lookup_records(raw,m):
                    check();counts['read']+=1
                    fatal=not _record(db,m,job,counts['read'],row,counts,limits,projection,locator) or fatal
            else:
                while True:
                    check(); raw=stream.readline(limits.max_line_bytes+1)
                    if not raw: break
                    counts['read']+=1; counts['bytes']+=len(raw); digest.update(raw)
                    if (len(raw)>limits.max_line_bytes or not raw.endswith(b'\n')
                            or counts['read']>m['expectedRecords'] or counts['bytes']>m['candidateBytes']): _fail('input-framing-or-bound')
                    record=_record_off if m['representation']=='verified-off-occurrences-jsonl' else _record
                    fatal=not record(db,m,job,counts['read'],raw,counts,limits,projection) or fatal
        if (_identity(os.fstat(fd))!=expected_identity or _identity(_safe(path).stat())!=expected_identity): _fail('input-custody')
        if counts['bytes']!=m['candidateBytes'] or counts['read']!=m['expectedRecords'] or digest.hexdigest()!=m['candidateSha256']: _fail('input-eof-hash-count')
        if m['expectedProducts'] is not None and counts['products']!=m['expectedProducts']: _fail('product-count')
        if fatal: _fail('malformed-records-held')
        key_query=('SELECT count(*) FROM (SELECT identifier_id FROM identifier_assertion '
                   'INDEXED BY identifier_input_key_accounting WHERE run_id=? AND input_id=? '
                   'AND identifier_id IS NOT NULL ')
        distinct=db.execute(key_query+'GROUP BY identifier_id)',(run,input_id)).fetchone()[0]
        existing=db.execute(key_query+'AND identifier_id<=? GROUP BY identifier_id)',(run,input_id,previous_identifier_max)).fetchone()[0]
        counts.update(distinct_input_keys=distinct,existing_exact_keys=existing,
                      repeated_key_occurrences=counts['identifiers_eligible']-distinct)
        if distinct!=counts['new_identifiers']+existing:_fail('identifier-key-conservation')
        if m['representation']=='verified-off-occurrences-jsonl':
            q=m['occurrenceAudit']
            actual={k:counts.get('off_'+k,0) for k in ('S','C','Q')}
            measured=db.execute('SELECT count(*),coalesce(sum(c>0),0),coalesce(sum(NOT((s=1 AND c=0) OR (s=0 AND c>=2))),0),coalesce(sum(p),0) FROM '
                '(SELECT sum(policy_disposition=?) s,sum(policy_disposition=?) c,sum(policy_disposition=? AND disposition<>?) p FROM identifier_assertion '
                'WHERE run_id=? AND input_id=? AND identifier_id IS NOT NULL GROUP BY identifier_id)',
                ('off-S','off-C','off-C','unresolved',run,input_id)).fetchone()
            if (actual!=q['counts'] or distinct!=q['distinctValidKeys'] or measured!=(distinct,q['groups'],0,0)
                    or counts['identifiers_eligible']!=actual['S']+actual['C']
                    or counts['identifiers_other-invalid']!=actual['Q']):_fail('off-audit-conservation')
            counts.update(valid_code_associations=actual['S']+actual['C'],ambiguous_key_groups=measured[1],
                          invalid_code_audits=actual['Q'],selected_primary_count=measured[3])
        if (sum(counts['source_'+k] for k in ('new','identical','conflicting','malformed'))!=counts['read']
                or sum(counts['identifiers_'+k] for k in ('eligible','invalid-nonstring','empty','missing-null','unknown-namespace','other-invalid'))!=counts['identifier_occurrences']): _fail('conservation')
        counts.update(expected=m['expectedRecords'],unread=0,rejected=counts['source_malformed'],dependency=0)
        db.execute('UPDATE identifier_input SET status=?,counts_json=? WHERE run_id=? AND input_id=?',('complete',canonical(counts).decode(),run,input_id))
        db.execute('UPDATE parse_job SET state=?,output_logical_records_sha256=?,checkpoint_json=?,database_completed_at=? WHERE parse_job_id=?',
          ('completed',projection.hexdigest(),canonical(counts).decode(),datetime.now(timezone.utc).isoformat(),job))
        _checkpoint(db,m,job,counts,'committed');db.commit();check()
        return counts,False
    except BaseException as error:
        counts.update(expected=m['expectedRecords'],unread=max(0,m['expectedRecords']-counts['read']),rejected=counts['source_malformed'],observedInputSha256=digest.hexdigest(),error=type(error).__name__)
        try:
            db.execute('UPDATE identifier_input SET status=?,counts_json=? WHERE run_id=? AND input_id=?',('held',canonical(counts).decode(),run,input_id))
            db.execute('UPDATE parse_job SET state=?,checkpoint_json=? WHERE parse_job_id=?',('incomplete',canonical(counts).decode(),job))
            db.execute('UPDATE identifier_load SET state=? WHERE run_id=?',('incomplete',run))
            _checkpoint(db,m,job,counts,'incomplete');db.commit()
        except sqlite3.Error:db.rollback()
        error.identifier_input_checkpoint=counts
        raise
    finally:
        if fd is not None:os.close(fd)


def _checkpoint(db,m,job,counts,state):
    encoded=canonical(counts)
    ordinal=db.execute('SELECT coalesce(max(checkpoint_ordinal),0)+1 FROM load_checkpoint WHERE run_id=?',(m['runId'],)).fetchone()[0]
    db.execute('INSERT INTO load_checkpoint(run_id,checkpoint_ordinal,parse_job_id,input_id,last_committed_record_ordinal,examined_record_occurrences,examined_identifier_occurrences,accounting_sha256,source_position_json,state,database_checkpoint_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
      (m['runId'],ordinal,job,m['inputId'],counts['read'],counts['read'],counts['identifier_occurrences'],hashlib.sha256(encoded).hexdigest(),
       canonical({'representation':m['representation'],'logicalRecordOrdinal':counts['read'],'inputBytesRead':counts['bytes']}).decode(),state,datetime.now(timezone.utc).isoformat()))


def prepare_identifier_manifest(inputs, *, pending_sources=()):
    """Pure descriptor only; no source stat/open/hash. Not authority selection."""
    if type(inputs) is not tuple or not 1<=len(inputs)<=64: _fail('input-inventory')
    prepared=[_prepare(s) for s in inputs]; unique={}
    for m in prepared:
        if m['assetId'] in unique and unique[m['assetId']]['specSha256']!=m['specSha256']: _fail('duplicate-asset-conflict')
        unique[m['assetId']]=m
    return {'version':VERSION,'inputs':list(unique.values()),'pendingSources':strict_json(canonical(pending_sources))}


def build_identifier_database(inputs, destination, *, limits, run_id, input_manifest_pointer,
                              input_manifest_sha256, selection_receipt_sha256, pending_sources=()):
    """Exclusive LOCAL output; no CLI/automatic retry/overwrite/cleanup.

    Explicit trusted input/lineage selection and a qualified external runtime
    are mandatory for real data. This function itself grants neither.
    """
    if (type(inputs) is not tuple or not 1<=len(inputs)<=64 or type(limits) is not IdentifierLimits
            or any(type(v) is not int or not 0<v<2**63 for v in limits.__dict__.values())
            or limits.max_line_bytes>64*1024**2 or limits.max_identifier_bytes>limits.max_line_bytes): _fail('limits')
    if (type(run_id) is not str or not 0<len(run_id)<=256 or type(input_manifest_pointer) is not str
            or not 0<len(input_manifest_pointer)<=4096 or not _sha(selection_receipt_sha256)
            or not _sha(input_manifest_sha256)): _fail('load-selection-required')
    prepared=[_prepare(s) for s in inputs]
    unique={}
    for m in prepared:
        if m['assetId'] in unique and unique[m['assetId']]['specSha256']!=m['specSha256']: _fail('duplicate-asset-conflict')
        unique[m['assetId']]=m
    manifest=prepare_identifier_manifest(inputs,pending_sources=pending_sources)
    manifest_sha=hashlib.sha256(canonical(manifest)).hexdigest()
    if manifest_sha!=input_manifest_sha256: _fail('selected-input-manifest-mismatch')
    if (sum(m['candidateBytes'] for m in unique.values())>limits.max_scan_bytes
            or sum(m['expectedRecords'] for m in unique.values())>limits.max_records): _fail('manifest-bound')
    pending=canonical(pending_sources)
    if len(pending)>1024**2: _fail('pending-manifest-bound')
    target=Path(destination)
    if target.name in ('','.','..') or target.name!=str(target.name) or target.suffix!='.sqlite': _fail('destination')
    parent=_safe(target.parent); parent_fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    stage_fd=file_fd=held=None; db=None; published=False; stage=None; start=time.monotonic()
    try:
        if stat.S_IMODE(os.fstat(parent_fd).st_mode)!=0o700: _fail('private-parent-required')
        parent_identity=(os.fstat(parent_fd).st_dev,os.fstat(parent_fd).st_ino)
        os.fsync(parent_fd)
        try: os.stat(target.name,dir_fd=parent_fd,follow_symlinks=False)
        except FileNotFoundError: pass
        else: _fail('destination-exists')
        stage='.identifier-load-'+secrets.token_hex(16);os.mkdir(stage,0o700,dir_fd=parent_fd)
        stage_fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        stage_identity=(os.fstat(stage_fd).st_dev,os.fstat(stage_fd).st_ino)
        file_fd=os.open('data.sqlite',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=stage_fd)
        inode=(os.fstat(file_fd).st_dev,os.fstat(file_fd).st_ino)
        checks=[0]
        def check(force=False):
            if time.monotonic()-start>=limits.max_seconds: _fail('time-bound')
            checks[0]+=1
            if not force and checks[0]%256: return
            if ((os.stat(parent).st_dev,os.stat(parent).st_ino)!=parent_identity
                    or (os.stat(stage,dir_fd=parent_fd,follow_symlinks=False).st_dev,os.stat(stage,dir_fd=parent_fd,follow_symlinks=False).st_ino)!=stage_identity): _fail('output-custody')
            if not published:
                info=os.stat('data.sqlite',dir_fd=stage_fd,follow_symlinks=False)
                if (info.st_dev,info.st_ino)!=inode or not stat.S_ISREG(info.st_mode): _fail('output-custody')
            size=0
            for name in os.listdir(stage_fd):
                info=os.stat(name,dir_fd=stage_fd,follow_symlinks=False)
                if name not in ('data.sqlite','data.sqlite-journal') or not stat.S_ISREG(info.st_mode): _fail('unexpected-stage-entry')
                size+=info.st_blocks*512
            if size>limits.max_storage_bytes or os.fstat(file_fd).st_size>limits.max_database_bytes: _fail('storage-bound')
        if threading.active_count()!=1 or len(os.listdir('/proc/self/task'))!=1: _fail('serialized-default-sqlite-required')
        before=_descriptor_snapshot();db=sqlite3.connect(f'/proc/self/fd/{stage_fd}/data.sqlite')
        after=_descriptor_snapshot();new=[fd for fd,i in after.items() if fd not in before or (i.st_dev,i.st_ino)!=(before[fd].st_dev,before[fd].st_ino)]
        if len(new)!=1 or (after[new[0]].st_dev,after[new[0]].st_ino)!=inode: _fail('sqlite-descriptor-ambiguous')
        held=os.dup(new[0]);db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA temp_store=MEMORY')
        db.execute('PRAGMA cache_size=-8192');db.execute('PRAGMA mmap_size=0');db.execute('PRAGMA synchronous=FULL')
        page=db.execute('PRAGMA page_size').fetchone()[0]
        db.execute('PRAGMA max_page_count='+str(max(1,limits.max_database_bytes//page)))
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(2**31-1,limits.max_line_bytes*4))
        db.set_progress_handler(lambda:int(time.monotonic()-start>=limits.max_seconds),1000)
        db.executescript(DDL)
        coordinator=run_id+'/load'
        _new_job(db,coordinator,manifest_sha,{'purpose':'selected identifier inputs; no runtime AI'})
        db.execute('INSERT INTO identifier_load(run_id,input_manifest_sha256,parse_job_id,input_manifest_pointer,loader_version,selection_receipt_sha256,state,expected_records,database_created_at,pending_sources_json,summary_json,schema_interface_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
          (run_id,manifest_sha,coordinator,input_manifest_pointer,VERSION,selection_receipt_sha256,'loading',
           sum(m['expectedRecords'] for m in unique.values()),datetime.now(timezone.utc).isoformat(),pending.decode(),'{}',SCHEMA_INTERFACE_SHA256));db.commit()
        results=[]
        for m in prepared:
            counts,reused=_load_asset(db,dict(m,runId=run_id,manifestSha=manifest_sha),limits,check)
            results.append({'assetId':m['assetId'],'counts':counts,'reusedCompletedAsset':reused})
        check(True)
        if db.execute('PRAGMA foreign_key_check').fetchone() or db.execute('PRAGMA quick_check').fetchone()!=('ok',): _fail('database-reconciliation')
        if db.execute('SELECT count(*) FROM identifier_input WHERE status<>?',('complete',)).fetchone()[0]: _fail('incomplete-inputs')
        summary={'inputs':results,'pendingSources':strict_json(pending),'scope':'selected-native-inputs-only',
                 'distinctIdentifiers':db.execute('SELECT count(*) FROM identifier').fetchone()[0],
                 'identifierAssertions':db.execute('SELECT count(*) FROM identifier_assertion').fetchone()[0],
                 'sourceOccurrences':db.execute('SELECT count(*) FROM identifier_source_record').fetchone()[0],
                 'physicalProducts':'unknown','qualifiedIngredientLinks':0,
                 'distinctKeysByNamespace':dict(db.execute('SELECT namespace,count(*) FROM identifier GROUP BY namespace')),
                 'assertionDispositions':dict(db.execute('SELECT disposition,count(*) FROM identifier_assertion GROUP BY disposition'))}
        finalization_sha=hashlib.sha256(canonical(summary)).hexdigest()
        exceptions=db.execute('SELECT count(*) FROM identifier_exception').fetchone()[0]
        now=datetime.now(timezone.utc).isoformat()
        db.execute('UPDATE identifier_load SET state=?,summary_json=?,finalization_evidence_sha256=?,database_completed_at=?,observed_records=?,stored_records=?,identifier_assertions=?,exception_count=?,invalid_identifiers=?,unresolved_identifiers=?,unparsed_record_dispositions=? WHERE run_id=?',
          ('completed-with-exceptions' if exceptions else 'completed',canonical(summary).decode(),finalization_sha,now,
           summary['sourceOccurrences'],summary['sourceOccurrences'],summary['identifierAssertions'],exceptions,
           summary['assertionDispositions'].get('invalid',0),summary['assertionDispositions'].get('unresolved',0),0,run_id))
        db.execute('UPDATE parse_job SET state=?,output_logical_records_sha256=?,database_completed_at=? WHERE parse_job_id=?',
                   ('completed',finalization_sha,now,coordinator));db.commit()
        db.close();db=None;check(True);os.fsync(file_fd)
        before_hash=_identity(os.fstat(file_fd));digest=hashlib.sha256();offset=0
        while True:
            check(True);block=os.pread(file_fd,1024**2,offset)
            if not block:break
            digest.update(block);offset+=len(block)
        signature=_identity(os.fstat(file_fd));check(True)
        if signature!=before_hash or offset!=before_hash[2]:_fail('database-hash-custody')
        _rename_noreplace(stage_fd,'data.sqlite',parent_fd,target.name);published=True
        observed=os.stat(target.name,dir_fd=parent_fd,follow_symlinks=False)
        if not stat.S_ISREG(observed.st_mode) or _identity(observed)[:4]!=signature[:4]: _fail('published-custody')
        signature=_identity(os.fstat(file_fd))
        if _identity(observed)!=signature: _fail('published-custody')
        os.fsync(parent_fd)
        if _identity(os.stat(target.name,dir_fd=parent_fd,follow_symlinks=False))!=signature: _fail('published-custody')
        return {'schemaVersion':VERSION,'database':str(parent/target.name),'databaseSha256':digest.hexdigest(),
                'databaseIdentity':signature,'databaseBytes':offset,'loadComplete':True,'summary':summary,
                'runId':run_id,'inputManifestSha256':manifest_sha,'schemaInterfaceSha256':SCHEMA_INTERFACE_SHA256,
                'accepted':False,'runtimeOrResourcesAdmitted':False,'pointInTimeOnly':True,
                'retainedStage':str(parent/stage),'automaticDeletion':False}
    except BaseException as error:
        error.identifier_database_retained_state={'destination':str(target),'stage':str(parent/stage) if stage else None,
            'published':published,'completeReceiptReturned':False,'automaticDeletion':False,
            'nextAction':'Retain and reconcile database/journal/checkpoint; no automatic retry/overwrite/cleanup.'}
        raise
    finally:
        if db is not None: db.close()
        for fd in (held,file_fd,stage_fd,parent_fd):
            if fd is not None:os.close(fd)


def query_identifiers(receipt, *, namespace=None, lexical_value=None, prefix=None, disposition='source-asserted',
                      after_assertion_id=0, limit=100, max_steps=100000, max_seconds=5,
                      max_result_bytes=1024**2):
    """Private read-only keyset pages; receipt must be independently selected.

    Syntax/checksum and lexical key equality never assert physical identity.
    """
    if (type(receipt) is not dict or receipt.get('schemaVersion')!=VERSION or receipt.get('loadComplete') is not True
            or type(limit) is not int or not 1<=limit<=500 or type(after_assertion_id) is not int or after_assertion_id<0
            or any(type(v) is not int or v<=0 for v in (max_steps,max_seconds,max_result_bytes))
            or any(v is not None and (type(v) is not str or len(v)>4096) for v in (namespace,lexical_value,prefix))
            or (lexical_value is not None and prefix is not None)
            or disposition not in ('source-asserted','invalid','unresolved')): _fail('query-input')
    path=_safe(Path(receipt['database']));expected=tuple(receipt['databaseIdentity']);fd=None;db=None
    start=time.monotonic();steps=[0]
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        if _identity(os.fstat(fd))!=expected or _identity(path.stat())!=expected: _fail('query-custody')
        db=sqlite3.connect(f'file:/proc/self/fd/{fd}?mode=ro&immutable=1',uri=True)
        def progress():
            steps[0]+=100;return int(steps[0]>max_steps or time.monotonic()-start>=max_seconds)
        db.set_progress_handler(progress,100)
        status=db.execute('SELECT loader_version,state FROM identifier_load WHERE run_id=?',(receipt['runId'],)).fetchall()
        if len(status)!=1 or status[0][0]!=VERSION or status[0][1] not in ('completed','completed-with-exceptions'): _fail('query-held')
        where=['v.assertion_id>?','v.run_id=?','v.disposition=?'];params=[after_assertion_id,receipt['runId'],disposition]
        for column,value in [('namespace',namespace),('lexical_value',lexical_value)]:
            if value is not None:where.append('v.'+column+'=?');params.append(value)
        if prefix is not None:
            where.append('v.lexical_value>=? AND substr(v.lexical_value,1,length(?))=?');params.extend([prefix,prefix,prefix])
        cursor=db.execute('SELECT v.*,a.raw_json,a.raw_sha256,a.raw_bytes,a.reasons_json FROM barcode_identifier_inspection v JOIN identifier_assertion a ON a.assertion_id=v.assertion_id WHERE '
                          +' AND '.join(where)
                          +' ORDER BY v.assertion_id LIMIT ?',params+[limit+1])
        names=[c[0] for c in cursor.description];rows=[];size=0
        for values in cursor:
            row=dict(zip(names,values));size+=len(canonical(row))
            if size>max_result_bytes: _fail('query-result-bound')
            rows.append(row)
        if _identity(os.fstat(fd))!=expected or _identity(_safe(path).stat())!=expected: _fail('query-custody')
        if time.monotonic()-start>=max_seconds: _fail('query-time-bound')
        more=len(rows)>limit;rows=rows[:limit]
        return {'rows':rows,'hasMore':more,'nextAssertionId':rows[-1]['assertion_id'] if more else None,
                'databaseSha256':receipt['databaseSha256'],'assurance':'lexical-source-observations-only'}
    finally:
        if db is not None:db.close()
        if fd is not None:os.close(fd)


SELECTED22_SHA256 = 'd69ea04ee0e973305be25ad560f2a1e89debadf18b9e0f373a3f788fd7ba91e8'
SELECTED22_REVIEW_SHA256 = 'ad4017a9453f3dfa5ee7e97d31086eea0f75140dc20896a76cae5a9509572b9f'
NATIVE_QUALIFICATION_SHA256 = '5f45979fcdde581a62093c1c32fe047ef1e355416ff33c0128bace305c053553'
PARENT_NATIVE_ASSET_ID = 'local-backfill:v1:asset:usda-files:99573c6ecbf7fe11d2f1064c7babeeee9fc017af66981247fb193eae48df90e2'
OFF_OCCURRENCES_SHA256 = 'ae30ad627dd4f5febb2b230dee1ce0b9d41937cc19f5e73dd829aaf6ca442e41'
OFF_ORIGINAL_SHA256 = '11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e'
OFF_METADATA_REVIEW_SHA256 = 'af6c1ae92dfa1872a47caa6c59191b54888574fb9aa21ea669fe43bd07491f46'
OFF_ORIGINAL_ASSET_ID = 'local-backfill:v1:asset:off:d1239890836e077b6e5acbb2a774dcb5dd654b5c4c5307ffa964f012c13d8fad'


def selected22_input(operation):
    """Fixed existing cached lookup adapter; pure source/control metadata only.

    Caller supplies current input identity and19-owned citation/asset rows.
    The PARSE-derived asset below is explicitly not a new FETCH identity.
    No corpus fallback, AI, arbitrary registry or SourceContract JSON loader.
    """
    from .product_adapters import ProductLimits
    from .usda_product_contract import usda_20260430_contract, SOURCE
    if type(operation) is not dict or operation.get('schemaVersion')!='offmenu-selected22-identifier-operation/1':_fail('selected22-operation')
    contract=usda_20260430_contract(limits=ProductLimits(536870912,4294967296,8388608,36049091,68719476736,103079215104,36,27195013))
    if contract_fingerprint(contract)!='67b5e257d288a29cfd96dfa1cb8faba1e661821257f415c93ac87edab2692164':_fail('selected22-native-code-binding')
    q=operation['qualification'];_binding(contract,q,NATIVE_QUALIFICATION_SHA256)
    citations=tuple(operation['fetch_citations']);assets=tuple(operation['fetch_assets'])
    byid={a.get('asset_id',a.get('id')):a for a in assets}
    if 'usda-archive:2026-04' not in byid or PARENT_NATIVE_ASSET_ID not in byid:_fail('selected22-parent-asset-ids')
    citation_id=byid[PARENT_NATIVE_ASSET_ID]['citation_id']
    derived_id='parse-derived:lookup:'+SELECTED22_SHA256
    if derived_id in byid:_fail('selected22-derived-asset-already-supplied')
    derived={'asset_id':derived_id,'fetch_owned_asset_id':None,'citation_id':citation_id,
             'identity_state':'unresolved-backfill','retrieval_clock_state':'unknown-retained',
             'metadata_origin_pointer':'PARSE-derived cached lookup; independent review10737, no FETCH/publisher authority',
             'unknown_fields_json':'["not a direct FETCH asset; cached lookup derivation"]'}
    bindings=(
        {'id':'usda-archive:2026-04','logical_path':SOURCE.path,'bytes':SOURCE.bytes,'sha256':SOURCE.sha256,
         'parent_asset_ids':[],'custody_ref':'retained original metadata; no original body read'},
        {'id':PARENT_NATIVE_ASSET_ID,'logical_path':'candidate.jsonl','bytes':18424445399,
         'sha256':q['candidateSha256'],'parent_asset_ids':['usda-archive:2026-04'],
         'custody_ref':'native qualification10660/review10672; no parent candidate read in this operation'},
        {'id':derived_id,'logical_path':'lookup-result.json','bytes':34844,'sha256':SELECTED22_SHA256,
         'parent_asset_ids':[PARENT_NATIVE_ASSET_ID],'custody_ref':'selected lookup review10737; current FD identity supplied by57'})
    producer=dict(operation['cached_lookup_job'],output_sha256=SELECTED22_SHA256)
    spec=IdentifierInput(operation['input_path'],derived_id,citations,assets+(derived,),producer,'0'*64,
        contract,q,NATIVE_QUALIFICATION_SHA256,tuple(operation['input_identity']) if operation.get('input_identity') is not None else None,
        (('barcode','barcode'),('USDA-FDC','USDA-FDC')),'native-systems-exact/1',22,
        'reviewed-native-lookup-json',22,SELECTED22_REVIEW_SHA256,bindings)
    lineage={'citations':spec.citations,'assets':spec.assets,'producerJob':spec.producer_job,
             'namespaceRules':spec.namespace_rules,'namespaceRuleVersion':spec.namespace_rule_version,
             'representation':spec.representation,'selectedCount':spec.selected_count,
             'selectedReviewSha256':spec.selected_review_sha256,'assetBindings':spec.asset_bindings}
    from dataclasses import replace
    return replace(spec,lineage_sha256=hashlib.sha256(canonical(lineage)).hexdigest())


def _bind_lineage(spec):
    from dataclasses import replace
    lineage={'citations':spec.citations,'assets':spec.assets,'producerJob':spec.producer_job,
             'namespaceRules':spec.namespace_rules,'namespaceRuleVersion':spec.namespace_rule_version,
             'representation':spec.representation,'selectedCount':spec.selected_count,
             'selectedReviewSha256':spec.selected_review_sha256,'assetBindings':spec.asset_bindings}
    return replace(spec,lineage_sha256=hashlib.sha256(canonical(lineage)).hexdigest())


def usda_full_input(operation):
    """Use the accepted native contract and full candidate, without opening it."""
    from dataclasses import replace
    template=selected22_input(dict(operation,schemaVersion='offmenu-selected22-identifier-operation/1',
                                  cached_lookup_job=operation['native_candidate_job']))
    return _bind_lineage(replace(template,asset_id=PARENT_NATIVE_ASSET_ID,assets=tuple(operation['fetch_assets']),
        producer_job=dict(operation['native_candidate_job'],output_sha256=operation['qualification']['candidateSha256']),
        expected_products=2101279,representation='native-jsonl',selected_count=None,selected_review_sha256=None,
        asset_bindings=template.asset_bindings[:2]))


def off_occurrence_input(operation):
    """Exact reviewed OFF metadata audit; no product qualification is fabricated."""
    originals=tuple(operation['fetch_assets']);byid={a.get('asset_id',a.get('id')):a for a in originals}
    if OFF_ORIGINAL_ASSET_ID not in byid:_fail('off-fetch-original-required')
    citation_id=byid[OFF_ORIGINAL_ASSET_ID]['citation_id'];derived='parse-derived:off-occurrences:'+OFF_OCCURRENCES_SHA256
    q={'schemaVersion':'offmenu-off-occurrence-metadata-binding/1','sourceId':'off','releaseId':'2026-10-12',
       'scopeId':'off-20261012-verified-source-occurrence-audit-v1','fixture':False,
       'normalizedRecords':4807663,'candidateSha256':OFF_OCCURRENCES_SHA256,'originalSha256':OFF_ORIGINAL_SHA256,
       'counts':{'S':4807156,'C':122,'Q':385},'groups':61,'distinctValidKeys':4807217,
       'metadataReviewSha256':OFF_METADATA_REVIEW_SHA256,
       'metadataVerificationResultSha256':'5c37b1e4afb803371016a9b6b76b78f2062a96a245d6edfd3a2da43868c728bd',
       'verificationManifestSha256':'4a95665d8940aff3176cd1ae0abc762e45e914674c7e57ad135010d4e81fd12b',
       'originalInputs':[{'path':'off-2026-10-12.jsonl.gz','bytes':13132516914,'sha256':OFF_ORIGINAL_SHA256}]}
    asset={'asset_id':derived,'citation_id':citation_id,'fetch_owned_asset_id':None,
           'identity_state':'unresolved-backfill','retrieval_clock_state':'unknown-retained',
           'metadata_origin_pointer':'PARSE-derived occurrence metadata; terminal11122/review11201, not direct FETCH',
           'unknown_fields_json':'["not a direct FETCH asset; verified private occurrence audit"]'}
    bindings=({'id':OFF_ORIGINAL_ASSET_ID,'logical_path':'off-2026-10-12.jsonl.gz','bytes':13132516914,
               'sha256':OFF_ORIGINAL_SHA256,'parent_asset_ids':[],'custody_ref':'retained original metadata only; no original replay'},
              {'id':derived,'logical_path':'occurrences.jsonl','bytes':1656721116,'sha256':OFF_OCCURRENCES_SHA256,
               'parent_asset_ids':[OFF_ORIGINAL_ASSET_ID],'custody_ref':'full emitted metadata review11201/11204'})
    spec=IdentifierInput(operation['input_path'],derived,tuple(operation['fetch_citations']),originals+(asset,),
        dict(operation['occurrence_job'],output_sha256=OFF_OCCURRENCES_SHA256),'0'*64,None,q,
        hashlib.sha256(canonical(q)).hexdigest(),tuple(operation['input_identity']) if operation.get('input_identity') is not None else None,
        (('barcode','barcode'),),'native-systems-exact/1',0,'verified-off-occurrences-jsonl',asset_bindings=bindings)
    return _bind_lineage(spec)


def full_retained_inputs(operation):
    if (type(operation) is not dict or operation.get('schemaVersion')!='offmenu-full-retained-identifier-operation/1'
            or type(operation.get('sources')) is not list or not 1<=len(operation['sources'])<=2
            or len(set(operation['sources']))!=len(operation['sources'])
            or any(s not in ('usda-files','off') for s in operation['sources'])):_fail('full-operation')
    factories={'usda-files':usda_full_input,'off':off_occurrence_input}
    return tuple(factories[source](operation[source]) for source in operation['sources'])


def _full_limits(operation,inputs):
    values=operation.get('limits')
    if (type(values) is not dict or set(values)!=set(IdentifierLimits.__dataclass_fields__)
            or any(type(v) is not int or not 0<v<2**63 for v in values.values())):_fail('full-finite-limits')
    limits=IdentifierLimits(**values);manifest=prepare_identifier_manifest(inputs)
    if (limits.max_line_bytes>64*1024**2 or limits.max_identifier_bytes>limits.max_line_bytes
            or sum(m['candidateBytes'] for m in manifest['inputs'])>limits.max_scan_bytes
            or sum(m['expectedRecords'] for m in manifest['inputs'])>limits.max_records):_fail('full-input-limits')
    return limits


def _read_control(path,expected):
    if not _sha(expected):_fail('control-pin-required')
    path=_safe(Path(path));fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        before=_identity(os.fstat(fd))
        if before[2]>1024**2:_fail('control-bound')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(1024**2+1)
        if (len(raw)!=before[2] or hashlib.sha256(raw).hexdigest()!=expected
                or _identity(os.fstat(fd))!=before or _identity(path.stat())!=before):_fail('control-pin-or-custody')
        return strict_json(raw)
    finally:os.close(fd)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare-selected22','load-selected22','prepare-full','load-full','query'))
    parser.add_argument('--operation',required=True)
    parser.add_argument('--operation-sha256',required=True)
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--namespace',default='barcode')
    parser.add_argument('--after',type=int,default=0)
    parser.add_argument('--limit',type=int,default=25)
    args=parser.parse_args();operation=_read_control(args.operation,args.operation_sha256)
    if args.command=='query':
        result=query_identifiers(operation,namespace=args.namespace,after_assertion_id=args.after,limit=args.limit)
    elif args.command in ('prepare-full','load-full'):
        inputs=full_retained_inputs(operation);limits=_full_limits(operation,inputs)
        pending=tuple(operation.get('pending_sources',[]))
        manifest=prepare_identifier_manifest(inputs,pending_sources=pending)
        manifest_sha=hashlib.sha256(canonical(manifest)).hexdigest()
        if args.command=='prepare-full':
            result={'inputManifest':manifest,'inputManifestSha256':manifest_sha,'sourceBodyRead':False,
                    'limits':vars(limits),'callable':'offmenu.refresh.identifier_database.build_identifier_database'}
        else:
            result=build_identifier_database(inputs,operation['destination'],limits=limits,
                run_id=operation['run_id'],input_manifest_pointer=args.operation,input_manifest_sha256=args.manifest_sha256,
                selection_receipt_sha256=operation['selection_receipt_sha256'],pending_sources=pending)
    else:
        spec=selected22_input(operation)
        pending=({'sourceId':'usda-files','scope':'complete-native-candidate','status':'not-loaded-by-selected22-operation',
                  'upstreamRecords':4202558,'upstreamBytes':18424445399},
                 {'sourceId':'off','scope':'full-source-identifier-occurrence-audit','status':'not-loaded-by-selected22-operation'})
        pending+=tuple(operation.get('pending_sources',[]))
        manifest=prepare_identifier_manifest((spec,),pending_sources=pending)
        manifest_sha=hashlib.sha256(canonical(manifest)).hexdigest()
        if args.command=='prepare-selected22':
            result={'inputManifest':manifest,'inputManifestSha256':manifest_sha,'sourceBodyRead':False,
                    'callable':'offmenu.refresh.identifier_database.build_identifier_database'}
        else:
            result=build_identifier_database((spec,),operation['destination'],
                limits=IdentifierLimits(34844,22,65536,4096,2,256,16*1024**2,64*1024**2,300),
                run_id=operation['run_id'],input_manifest_pointer=args.operation,
                input_manifest_sha256=args.manifest_sha256,selection_receipt_sha256=operation['selection_receipt_sha256'],
                pending_sources=pending)
    print(canonical(result).decode(),end='')


if __name__=='__main__':main()
