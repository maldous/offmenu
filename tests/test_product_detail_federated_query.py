"""Synthetic databases and qualified-evidence stand-ins, never actual stores."""
import ast
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from offmenu.refresh import product_detail_federated_query as q
from offmenu.refresh import product_detail_query as old
from offmenu.refresh.core import canonical, RefreshError
from tests import test_product_detail_import as fixtures
from tests.test_product_detail_query import IDENTIFIER_SCHEMA


def ddl(name):
    tree=ast.parse(Path('offmenu/refresh/'+name+'.py').read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='DDL' for t in n.targets))

def insert(db,table,**values):
    db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))


class FederatedQueryTests(unittest.TestCase):
    def setUp(self):
        self.db={role:sqlite3.connect(':memory:') for role in ('identifier','usda-products','usda-profiles','off-subset')}
        for db in self.db.values():self.addCleanup(db.close)
        self.db['identifier'].executescript(IDENTIFIER_SCHEMA)
        self.db['usda-products'].executescript(ddl('ingredient_ingestion'))
        self.db['usda-profiles'].executescript(ddl('dietary_native_store'))
        self.f=fixtures.ProductDetailImportTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        def fail(asset,consume):
            if asset['sourceId']=='usda-files':raise RuntimeError('generated stop')
            return self.f.scan(asset,consume)
        with self.assertRaises(RuntimeError):self.f.load(self.db['off-subset'],fail)
        self.db['off-subset'].execute('UPDATE product_detail_generation SET expected_asset_count=257')
        self.db['off-subset'].commit()
        self.sha=q.USDA_CANDIDATE_SHA256;self.manifest_hash='1'*64;self.profile_manifest='2'*64
        self.u={'sourceId':'usda-files','releaseId':'2026-04-30','assetId':'fixture-asset',
            'candidateSha256':self.sha,'candidateBytes':12345,'products':2,'profiles':2,
            'identifierInputId':'selected-usda','candidateFetchedAt':'2026-10-21T00:00:00Z',
            'originalSha256':'a'*64,'qualificationSha256':'b'*64,'sourceContractSha256':'c'*64,
            'rightsReceiptSha256':'d'*64,'representation':'usda-native-jsonl','projectionVersion':'fixture-native/1'}
        self.asset={'asset_id':self.u['assetId'],'sha256':self.sha,'bytes':12345,'records':4,
            'source_id':'usda-files','release_id':self.u['releaseId'],'kind':'products','path':'/synthetic/unused'}
        meta={'state':'complete','specSha256':q._hash(self.asset),'asset':self.asset,
            'counts':{'products':2,'stored_source_records':2,'read':4,'unread':0}}
        insert(self.db['usda-products'],'sidecar_schema',version='asset:'+self.u['assetId'],created_at='fixture',meaning=canonical(meta).decode())
        insert(self.db['usda-profiles'],'dietary_load',load_id='selected-load',input_manifest_sha256=self.profile_manifest,
            parse_engine_id='fixture',parse_engine_version='fixture',parse_engine_sha256='1'*64,state='completed',
            expected_packets=4,expected_profile_packets=2,expected_other_packets=2,read_packets=4,unread_packets=0,created_at='fixture')
        insert(self.db['usda-profiles'],'dietary_input',input_id=self.sha,load_id='selected-load',source_id='usda-files',release_id=self.u['releaseId'],
            asset_id=self.u['assetId'],citation_state='unresolved-backfill',candidate_sha256=self.sha,candidate_bytes=12345,
            provenance_manifest_sha256='3'*64,operation_evidence_sha256='4'*64,qualification_sha256='b'*64,
            original_acquired_at=None,acquisition_clock_state='unknown-retained')
        self.observations=[];self.references=[];self.profile_ids=[]
        for number in range(2):
            pair=copy.deepcopy(self.f.native_rows);rid='fdc-'+str(number)
            for row,kind in zip(pair,('product','nutrientProfile')):
                row['provenance']['recordId']=rid;row['provenance']['releaseId']=self.u['releaseId'];row['id']='usda-files:'+kind+':'+rid
                row['data']['identifiers']=[{'system':'barcode','value':self.f.code}]
            pair[0]['data']['nutritionId']=pair[1]['id'];pair[0]['data']['extension']={'preserved':None,'number':1.25}
            pair[0]['data']['name']='Variant '+str(number)
            self.add_pair(pair,2*number+1,number+1)
        binding=json.loads(self.db['off-subset'].execute("SELECT source_binding_json FROM product_detail_projection WHERE record_kind='product' ORDER BY reference_record_id LIMIT 1").fetchone()[0])
        code=self.db['off-subset'].execute('SELECT lexical_value FROM product_detail_identifier WHERE reference_record_id=(SELECT reference_record_id FROM product_detail_projection WHERE record_kind=\'product\' ORDER BY reference_record_id LIMIT 1)').fetchone()[0]
        self.observations.append(dict(run_id='selected-run',assertion_id=3,disposition='source-asserted',input_id=binding['identifierInputId'],
            record_ordinal=binding['identifierRecordOrdinal'],namespace='barcode',lexical_value=code,source_id='off',release_id='fixture-r1',
            artifact_sha256=binding['identifierAssetSha256'],native_record_id=binding['identifierNativeRecordId'],source_record_id=binding['identifierSourceRecordId']))
        index=self.db['identifier'];insert(index,'fetch_asset',asset_id='identifier-fixture');insert(index,'identifier_load',run_id='selected-run',state='completed')
        for obs in self.observations:
            index.execute('INSERT OR IGNORE INTO identifier_input VALUES(?,?,?,?,?,?)',(obs['run_id'],obs['input_id'],obs['source_id'],obs['release_id'],obs['artifact_sha256'],'identifier-fixture'))
            insert(index,'identifier_source_record',run_id=obs['run_id'],input_id=obs['input_id'],record_ordinal=obs['record_ordinal'],source_record_id=obs['source_record_id'],native_record_id=obs['native_record_id'])
            insert(index,'identifier_assertion',assertion_id=obs['assertion_id'],run_id=obs['run_id'],input_id=obs['input_id'],record_ordinal=obs['record_ordinal'],namespace=obs['namespace'],lexical_value=obs['lexical_value'],disposition='source-asserted')
        self.m={'version':'retained-product-federation-manifest-v1','generationId':'federated-fixture','operationSelectionSha256':'9'*64,
            'identifierDatabaseSha256':'c'*64,'identifierRunId':'selected-run','identifierFiveTuple':[1,2,4096,3,4],
            'identifierLoadReceiptSha256':'6'*64,'identifierQualificationSha256':'7'*64,'usda':self.u,'roles':{}}
        self.stores=[]
        for n,role in enumerate(q.ROLES):
            sha=str(n+1)*64
            self.stores.append(q.FederatedStoreEvidence(role,self.db[role],sha,'5'*64,'6'*64))
            self.m['roles'][role]={'enabled':True,'qualificationState':'qualified','databaseSha256':sha,'loadReceiptSha256':'5'*64,
                'qualificationSha256':'6'*64,'fiveTuple':[1,n+2,4096,3,4],'countsEvidenceSha256':'7'*64,'rightsReceiptSha256':'8'*64,'operationEvidenceSha256':'4'*64,'countBasis':'independently-qualified',
                'sourceId':'usda-files','releaseId':self.u['releaseId'],'candidateSha256':self.sha,'assetId':self.u['assetId'],
                'manifestSha256':self.manifest_hash if role=='usda-products' else self.profile_manifest,'sourceAssetCount':1,
                'retainedProducts':2 if role=='usda-products' else 0,'retainedProfiles':2 if role=='usda-profiles' else 0}
        self.m['roles']['usda-products']['assetSpecSha256']=q._hash(self.asset)
        self.m['roles']['usda-profiles'].update(loadId='selected-load',provenanceManifestSha256='3'*64,operationEvidenceSha256='4'*64,originalAcquiredAt=None,acquisitionClockState='unknown-retained')
        coverage=json.loads(self.db['off-subset'].execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
        self.m['roles']['off-subset'].update(sourceId='off',releaseId='fixture-r1',generationId='fixture-gen',sourceManifestSha256=self.db['off-subset'].execute('SELECT input_manifest_sha256 FROM product_detail_generation').fetchone()[0],
            sourceOperationSha256='e'*64,coverageSha256=q._hash(coverage),subsetCertificateSha256='8'*64,
            assets=coverage['assets'],retainedProducts=2,retainedProfiles=2)
        self.stores=tuple(self.stores)
        self.evidence=q.FederatedIdentifierEvidence(index,'selected-run','c'*64)
        for db in self.db.values():db.commit();db.execute('PRAGMA query_only=ON')

    def add_pair(self,pair,p,assertion):
        product,profile=pair;ref='urn:offmenu:source-record:'+q._hash([self.u['assetId'],self.sha,p]);self.references.append(ref)
        parsed=q._hash(product);raw=canonical([product]).decode()
        self.db['usda-products'].execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(ref,'usda-files',self.u['releaseId'],self.u['assetId'],self.sha,p,product['id'],'/0','und',raw,parsed,None,'unresolved-backfill','fixture','fixture','processed'))
        insert(self.db['usda-products'],'product_processing_audit',processing_id=ref,input_asset_id=self.u['assetId'],input_manifest_sha256=self.manifest_hash,input_asset_sha256=self.sha,
            source_id='usda-files',release_id=self.u['releaseId'],source_ordinal=p,source_record_id=product['provenance']['recordId'],native_product_id=product['id'],
            declaration_state='present',processing_status='processed',semantic_mapping_status='pending',composition_state='unknown',source_record_sha256=parsed,
            source_pointer='/0/data/ingredientsText',evidence_pointer='generated',evidence_sha256=parsed,parse_engine_id='fixture',parse_engine_version='fixture',citation_status='unresolved-backfill')
        packet='packet:'+self.sha+':'+str(p+1);profile_id=packet+':profile';self.profile_ids.append(profile_id)
        raw=json.dumps([profile],ensure_ascii=False,indent=1)+'\n';digest=hashlib.sha256(raw.encode()).hexdigest()
        insert(self.db['usda-profiles'],'dietary_packet_audit',packet_id=packet,input_id=self.sha,packet_ordinal=p+1,native_kind='nutrientProfile',native_record_id=profile['id'],source_record_id=profile['provenance']['recordId'],packet_sha256=digest,source_pointer='/0',disposition='profile-stored')
        insert(self.db['usda-profiles'],'native_nutrient_profile',profile_id=profile_id,packet_id=packet,language_state='unknown',native_packet_json=raw,document_sha256=digest,
            field_states_json='{}',nutrients_state='object',observed_entry_count=1,semantic_link_status='pending',provenance_json=canonical(profile['provenance']).decode())
        self.observations.append(dict(run_id='selected-run',assertion_id=assertion,disposition='source-asserted',input_id='selected-usda',record_ordinal=p,namespace='barcode',lexical_value=self.f.code,
            source_id='usda-files',release_id=self.u['releaseId'],artifact_sha256=self.sha,native_record_id=product['id'],source_record_id=product['provenance']['recordId']))

    def call(self,observations=None,manifest=None,stores=None,**limits):
        m=manifest if manifest is not None else self.m
        selection=q.FederatedQuerySelection(m['generationId'],q._hash(m),m['operationSelectionSha256'],m['identifierDatabaseSha256'])
        return q.read_federated_product_details(self.observations if observations is None else observations,selection=selection,
            identifier_evidence=self.evidence,stores=self.stores if stores is None else stores,selected_manifest=m,**limits)

    def edit(self,role,sql,values=()):
        db=self.db[role];db.execute('PRAGMA query_only=OFF');db.execute(sql,values);db.commit();db.execute('PRAGMA query_only=ON')

    def cleanup_ok(self,old_limits=None):
        for role,db in self.db.items():
            self.assertFalse(db.in_transaction);self.assertEqual(db.execute('PRAGMA query_only').fetchone(),(1,))
            self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone(),(2001000,))
            if old_limits:self.assertEqual(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),old_limits[role])

    def test_full_variants_fields_coordinates_digests_and_honest_coverage(self):
        changes={k:db.total_changes for k,db in self.db.items()};out=self.call()
        self.assertEqual(len(out['sourceProducts']),3);self.assertEqual([p['state'] for p in out['productDetailAvailability']],['loaded']*3)
        a,b,off=out['sourceProducts'];self.assertNotEqual(a['referenceRecordId'],b['referenceRecordId'])
        self.assertEqual(a['fields']['brand']['state'],'null');self.assertEqual(a['fields']['categories']['state'],'not-loaded')
        self.assertEqual(a['records'][0]['data']['extension'],{'preserved':None,'number':1.25})
        self.assertEqual(a['sourceBinding']['recordPointers'],['jsonl:line:1/0','jsonl:line:2/0'])
        self.assertEqual(b['sourceBinding']['recordPointers'],['jsonl:line:3/0','jsonl:line:4/0'])
        self.assertEqual(a['sourceBinding']['recordSha256'],hashlib.sha256(old.readers.canonical(a['records'])).hexdigest())
        self.assertNotEqual(a['sourceBinding']['recordSha256'],q._hash(a['records']))
        self.assertEqual(a['sourceBinding']['pairEvidenceOrigin'],'verified-retained-components')
        self.assertEqual(off['sourceBinding']['operationReceiptSha256'],'e'*64)
        self.assertIsNone(out['coverage']['products']);self.assertFalse(out['coverage']['complete']);self.assertEqual(out['coverage']['target']['assets'],257)
        self.assertEqual(self.db['off-subset'].execute('SELECT state,expected_asset_count,processed_asset_count FROM product_detail_generation').fetchone(),('incomplete',257,1))
        self.assertEqual(changes,{k:db.total_changes for k,db in self.db.items()});self.cleanup_ok()

    def test_scoped_store_PASS_keeps_producer_population_counts_explicit(self):
        m=copy.deepcopy(self.m);m['roles']['usda-products']['countBasis']='producer-reported'
        out=self.call(manifest=m);coverage=out['coverage']['backends'][1]
        self.assertTrue(coverage['enabled']);self.assertEqual(coverage['countBasis'],'producer-reported')
        self.assertFalse(coverage['populationCountIndependentlyVerified'])
        self.assertIsNone(out['coverage']['products']);self.assertFalse(out['coverage']['complete'])
        m['roles']['usda-products']['qualificationState']='producer-only'
        with self.assertRaises(RefreshError):self.call(manifest=m)

    def test_OFF_projection_limitations_preserved_in_order_with_subset_caveat(self):
        obs=self.observations[2];db=self.db['off-subset']
        ref=db.execute(q.OFF_KEY_SQL,(obs['namespace'],obs['lexical_value'],'fixture-gen','product',100)).fetchone()[0]
        caveats=['generated only','61 additional duplicate bodies omitted','385 invalid rows omitted',
            'source name/null/quantity/country/basis conversion remains uncertain','名は不明','', 'generated only']
        stored=canonical(caveats).decode();self.edit('off-subset','UPDATE product_detail_projection SET projection_limitations_json=? WHERE reference_record_id=?',(stored,ref))
        before=db.total_changes;out=self.call([obs]);returned=out['sourceProducts'][0]['projectionLimitations']
        self.assertEqual(returned[:-1],caveats)
        self.assertEqual(returned[-1],'Independently qualified OFF subset only; original257 generation remains incomplete.')
        self.assertEqual(db.execute('SELECT projection_limitations_json FROM product_detail_projection WHERE reference_record_id=?',(ref,)).fetchone(),(stored,))
        self.assertEqual(db.total_changes,before)
        size=len(canonical(out));self.assertEqual(self.call([obs],max_result_bytes=size),out)
        with self.assertRaisesRegex(RefreshError,'result-bound'):self.call([obs],max_result_bytes=size-1)
        self.cleanup_ok()

    def test_OFF_projection_limitations_malformed_or_excess_are_typed_and_bounded(self):
        obs=self.observations[2];db=self.db['off-subset']
        ref=db.execute(q.OFF_KEY_SQL,(obs['namespace'],obs['lexical_value'],'fixture-gen','product',100)).fetchone()[0]
        limits={role:conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) for role,conn in self.db.items()}
        for raw,code in (('{','invalid-json'),('null','projection-limitations'),('{}','projection-limitations'),
                         ('["ok",1]','projection-limitations'),(canonical(['x'*262144]).decode(),'metadata-bound')):
            with self.subTest(code=code):
                self.edit('off-subset','UPDATE product_detail_projection SET projection_limitations_json=? WHERE reference_record_id=?',(raw,ref))
                with self.assertRaisesRegex(RefreshError,code):self.call([obs])
                self.cleanup_ok(limits)
        self.edit('off-subset','UPDATE product_detail_projection SET projection_limitations_json=? WHERE reference_record_id=?',(canonical(['x'*120000]).decode(),ref))
        trace=[];db.set_trace_callback(trace.append)
        with self.assertRaisesRegex(RefreshError,'result-bound'):self.call([obs],max_result_bytes=16384)
        db.set_trace_callback(None)
        self.assertFalse(any(sql.startswith('SELECT projection_limitations_json FROM') for sql in trace))
        self.cleanup_ok(limits)

    def rewrite_native_clock(self,value,omit=False):
        for ref in self.references:
            raw=self.db['usda-products'].execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(ref,)).fetchone()[0]
            product=json.loads(raw)[0]
            if omit:product['provenance'].pop('fetchedAt',None)
            else:product['provenance']['fetchedAt']=value
            digest=q._hash(product)
            self.edit('usda-products','UPDATE retained_reference_record SET source_payload_json=?,parsed_record_sha256=? WHERE reference_record_id=?',(canonical([product]).decode(),digest,ref))
            self.edit('usda-products','UPDATE product_processing_audit SET source_record_sha256=? WHERE processing_id=?',(digest,ref))
        for pid in self.profile_ids:
            raw=self.db['usda-profiles'].execute('SELECT native_packet_json FROM native_nutrient_profile WHERE profile_id=?',(pid,)).fetchone()[0]
            profile=json.loads(raw)[0]
            if omit:profile['provenance'].pop('fetchedAt',None)
            else:profile['provenance']['fetchedAt']=value
            raw=canonical([profile]).decode();digest=hashlib.sha256(raw.encode()).hexdigest()
            self.edit('usda-profiles','UPDATE native_nutrient_profile SET native_packet_json=?,document_sha256=?,provenance_json=? WHERE profile_id=?',(raw,digest,json.dumps(profile['provenance'],sort_keys=True,separators=(',',':')),pid))
            self.edit('usda-profiles','UPDATE dietary_packet_audit SET packet_sha256=? WHERE packet_id=?',(digest,pid[:-8]))

    def test_selected_null_clock_loads_exact_null_provenance_without_inventing_time(self):
        self.rewrite_native_clock(None);m=copy.deepcopy(self.m);m['usda']['candidateFetchedAt']=None
        changes={role:db.total_changes for role,db in self.db.items()};out=self.call(manifest=m)
        self.assertEqual(len(out['sourceProducts']),3)
        for product in out['sourceProducts'][:2]:
            self.assertIsNone(product['sourceBinding']['candidateFetchedAt'])
            self.assertIsNone(product['sourceBinding']['originalAcquiredAt'])
            self.assertEqual(product['sourceBinding']['acquisitionClockState'],'unknown-retained')
            self.assertTrue(all('fetchedAt' in record['provenance'] and record['provenance']['fetchedAt'] is None for record in product['records']))
        self.assertEqual({role:db.total_changes for role,db in self.db.items()},changes)
        self.cleanup_ok()

    def test_clock_missing_invalid_and_mismatched_values_fail_closed(self):
        m=copy.deepcopy(self.m);m['usda']['candidateFetchedAt']=None
        out=self.call([self.observations[0]],manifest=m)
        self.assertEqual(out['sourceProducts'],[]);self.assertEqual(out['productDetailAvailability'][0]['state'],'not-loaded')
        self.rewrite_native_clock(None)
        out=self.call([self.observations[0]])  # selected text differs from raw null
        self.assertEqual(out['sourceProducts'],[])
        for value in (False,0,[],{},'', 'not-a-clock','2026-10-21','2026-10-21T00:00:00+11:00'):
            with self.subTest(value=value):
                bad=copy.deepcopy(self.m);bad['usda']['candidateFetchedAt']=value
                with self.assertRaisesRegex(RefreshError,'usda-selection'):self.call([self.observations[0]],manifest=bad)
        missing=copy.deepcopy(m);missing['usda'].pop('candidateFetchedAt')
        with self.assertRaisesRegex(RefreshError,'usda-selection'):self.call([self.observations[0]],manifest=missing)
        self.rewrite_native_clock(None,omit=True)
        out=self.call([self.observations[0]],manifest=m)
        self.assertEqual(out['sourceProducts'],[])  # missing raw field is not null
        self.cleanup_ok()

    def off_lineage(self,attempts,operation=None):
        db=self.db['off-subset'];coverage=json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
        coverage['resumeAttempts']=copy.deepcopy(attempts)
        self.edit('off-subset','UPDATE product_detail_generation SET coverage_scope_json=?',(canonical(coverage).decode(),))
        if operation is not None:
            rows=db.execute('SELECT reference_record_id,source_binding_json FROM product_detail_projection').fetchall()
            for ref,encoded in rows:
                binding=json.loads(encoded);binding['operationReceiptSha256']=operation
                self.edit('off-subset','UPDATE product_detail_projection SET source_binding_json=? WHERE reference_record_id=?',(canonical(binding).decode(),ref))
        m=copy.deepcopy(self.m);m['roles']['off-subset']['coverageSha256']=q._hash(coverage)
        return m

    def test_OFF_operation_is_asset_position_specific_not_lineage_membership(self):
        obs=self.observations[2]
        later=[{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':1}]
        m=self.off_lineage(later);self.assertEqual(len(self.call([obs],manifest=m)['sourceProducts']),1)
        m=self.off_lineage(later,'f'*64)
        self.assertEqual(self.call([obs],manifest=m)['sourceProducts'],[])  # asset0 predates resume
        boundary=[{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':0},
                  {'operationSelectionSha256':'a'*64,'startedAfterAssetCount':1}]
        m=self.off_lineage(boundary,'f'*64)
        self.assertEqual(self.call([obs],manifest=m)['sourceProducts'][0]['sourceBinding']['operationReceiptSha256'],'f'*64)
        m=self.off_lineage(boundary,'a'*64)
        self.assertEqual(self.call([obs],manifest=m)['sourceProducts'],[])  # trailing empty attempt owns no rows
        same_start=[{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':0},
                    {'operationSelectionSha256':'a'*64,'startedAfterAssetCount':0}]
        m=self.off_lineage(same_start,'a'*64);self.assertEqual(len(self.call([obs],manifest=m)['sourceProducts']),1)
        m=self.off_lineage(same_start,'f'*64);self.assertEqual(self.call([obs],manifest=m)['sourceProducts'],[])
        self.cleanup_ok()

    def test_OFF_invalid_resume_boundaries_fail_closed(self):
        for boundary in (None,False,-1,2,0.0):
            with self.subTest(boundary=boundary):
                m=self.off_lineage([{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':boundary}])
                with self.assertRaisesRegex(RefreshError,'off-lineage'):self.call([self.observations[2]],manifest=m)
        for attempts in ([{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':1},{'operationSelectionSha256':'a'*64,'startedAfterAssetCount':0}],
                         [{'operationSelectionSha256':'e'*64,'startedAfterAssetCount':0}],
                         [{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':0},{'operationSelectionSha256':'f'*64,'startedAfterAssetCount':0}]):
            with self.subTest(attempts=attempts):
                m=self.off_lineage(attempts)
                with self.assertRaisesRegex(RefreshError,'off-lineage'):self.call([self.observations[2]],manifest=m)
        self.cleanup_ok()

    def test_disabled_USDA_pair_preserves_both_role_restrictions_and_reasons(self):
        for product_state,profile_state in (('not-qualified','restricted'),('restricted','not-qualified'),
                                            ('restricted','restricted'),('not-qualified','not-qualified')):
            with self.subTest(product=product_state,profile=profile_state):
                m=copy.deepcopy(self.m)
                m['roles']['usda-products']={'enabled':False,'qualificationState':product_state,'reasonCode':'product-proof-or-operation-held'}
                m['roles']['usda-profiles']={'enabled':False,'qualificationState':profile_state,'reasonCode':'profile-proof-or-operation-held'}
                stores=tuple(s for s in self.stores if s.role=='off-subset')
                out=self.call([self.observations[0]],manifest=m,stores=stores);availability=out['productDetailAvailability'][0]
                restricted='restricted' in (product_state,profile_state)
                self.assertEqual(availability['state'],'restricted' if restricted else 'not-loaded')
                expected=[{'role':role,'qualificationState':m['roles'][role]['qualificationState'],'reasonCode':m['roles'][role]['reasonCode']}
                          for role in ('usda-products','usda-profiles')]
                self.assertEqual(availability['roleReasons'],expected)
                primary=expected[0] if product_state=='restricted' or not restricted else expected[1]
                self.assertEqual(availability['reasonCode'],primary['reasonCode'])
                coverage=out['coverage']['backends'][1]
                self.assertEqual(coverage['qualificationState'],'restricted' if restricted else 'not-qualified')
                self.assertEqual(coverage['reasonCode'],primary['reasonCode']);self.assertEqual(coverage['roleReasons'],expected)
                cap=len(canonical(out));self.assertEqual(self.call([self.observations[0]],manifest=m,stores=stores,max_result_bytes=cap),out)
                with self.assertRaisesRegex(RefreshError,'result-bound'):self.call([self.observations[0]],manifest=m,stores=stores,max_result_bytes=cap-1)
        self.cleanup_ok()

    def test_exact_current_assertion_before_any_payload_and_known_identifier_preserved(self):
        for key,value in {'assertion_id':99,'run_id':'foreign','input_id':'foreign','record_ordinal':99,'namespace':'other','lexical_value':'bad',
            'source_id':'other','release_id':'other','artifact_sha256':'0'*64,'native_record_id':'bad','source_record_id':'bad','disposition':'unresolved'}.items():
            with self.subTest(key=key):
                obs=dict(self.observations[0],**{key:value});traces=[]
                self.db['usda-products'].set_trace_callback(traces.append)
                out=self.call([obs]);self.db['usda-products'].set_trace_callback(None)
                self.assertEqual(out['sourceProducts'],[]);self.assertEqual(out['productDetailAvailability'][0]['reasonCode'],'no-current-identifier-assertion')
                self.assertFalse(any('retained_reference_record' in sql for sql in traces));self.assertEqual(obs[key],value)
        self.cleanup_ok()

    def test_disabled_OFF_and_restricted_USDA_remain_explicit(self):
        m=copy.deepcopy(self.m);m['roles']['off-subset']={'enabled':False,'qualificationState':'not-qualified','reasonCode':'subset-qualification-pending'}
        out=self.call(manifest=m,stores=tuple(s for s in self.stores if s.role!='off-subset'))
        self.assertEqual(len(out['sourceProducts']),2);self.assertEqual(out['productDetailAvailability'][-1]['reasonCode'],'subset-qualification-pending')
        self.assertFalse(out['coverage']['backends'][0]['enabled'])
        for role in ('usda-products','usda-profiles'):m['roles'][role]={'enabled':False,'qualificationState':'restricted','reasonCode':'operation-held'}
        out=self.call(manifest=m,stores=());self.assertEqual(out['sourceProducts'],[])
        self.assertEqual(out['productDetailAvailability'][0]['state'],'restricted')

    def test_context_manifest_binding_and_wrong_qualification_fail_closed(self):
        for change in ('digest','receipt','role-pair','fiveTuple','rights','candidate','off-cert','old-type'):
            with self.subTest(change=change):
                m=copy.deepcopy(self.m);stores=self.stores
                if change=='digest':m['roles']['usda-products']['databaseSha256']='0'*64
                elif change=='receipt':m['roles']['usda-products']['loadReceiptSha256']='0'*64
                elif change=='role-pair':stores=stores[:-1]
                elif change=='fiveTuple':m['roles']['usda-products']['fiveTuple']=None
                elif change=='rights':m['usda']['rightsReceiptSha256']=None
                elif change=='candidate':m['roles']['usda-profiles']['candidateSha256']='0'*64
                elif change=='off-cert':m['roles']['off-subset']['subsetCertificateSha256']=None
                elif change=='old-type':stores=(object(),)
                with self.assertRaises(RefreshError):self.call(manifest=m,stores=stores)
        self.db['usda-products'].execute('PRAGMA query_only=OFF')
        with self.assertRaisesRegex(RefreshError,'read-only-required'):self.call()
        self.db['usda-products'].execute('PRAGMA query_only=ON');self.cleanup_ok()

    def test_missing_or_wrong_pair_unavailable_corrupt_digest_typed(self):
        self.edit('usda-profiles','DELETE FROM native_nutrient_profile WHERE profile_id=?',(self.profile_ids[0],))
        out=self.call();self.assertEqual(out['productDetailAvailability'][0]['state'],'not-loaded');self.assertEqual(len(out['sourceProducts']),2)
        self.edit('usda-products','UPDATE retained_reference_record SET parsed_record_sha256=? WHERE reference_record_id=?',('0'*64,self.references[1]))
        with self.assertRaisesRegex(RefreshError,'record-digest'):self.call([self.observations[1]])
        self.cleanup_ok()

    def test_complete_response_exact_cap_zero_match_metadata_and_large_payload(self):
        out=self.call();size=len(canonical(out));self.assertEqual(self.call(max_result_bytes=size),out)
        with self.assertRaisesRegex(RefreshError,'result-bound'):self.call(max_result_bytes=size-1)
        empty=self.call([]);empty_size=len(canonical(empty));self.assertEqual(self.call([],max_result_bytes=empty_size),empty)
        with self.assertRaisesRegex(RefreshError,'result-bound'):self.call([],max_result_bytes=empty_size-1)
        role='usda-products';raw=self.db[role].execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(self.references[0],)).fetchone()[0]
        p=json.loads(raw)[0];p['data']['name']='x'*200000;parsed=q._hash(p)
        self.edit(role,'UPDATE retained_reference_record SET source_payload_json=?,parsed_record_sha256=? WHERE reference_record_id=?',(canonical([p]).decode(),parsed,self.references[0]))
        self.edit(role,'UPDATE product_processing_audit SET source_record_sha256=? WHERE processing_id=?',(parsed,self.references[0]))
        with self.assertRaisesRegex(RefreshError,'result-bound'):self.call([self.observations[0]])
        self.cleanup_ok()

    def test_shared_candidate_step_time_budgets_and_cleanup_all_connections(self):
        limits={role:db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) for role,db in self.db.items()}
        with self.assertRaisesRegex(RefreshError,'candidate-bound'):self.call(max_candidates=1)
        self.cleanup_ok(limits)
        with self.assertRaisesRegex(RefreshError,'sql-bound-or-store'):self.call(max_steps=1)
        self.cleanup_ok(limits)
        with patch.object(q.time,'monotonic',side_effect=[100.0]+[200.0]*100):
            with self.assertRaisesRegex(RefreshError,'time-bound|sql-bound-or-store'):self.call()
        self.cleanup_ok(limits)

    def test_all_exact_OFF_variants_are_returned_or_candidate_error_never_first_winner(self):
        obs=self.observations[2];db=self.db['off-subset'];db.execute('PRAGMA query_only=OFF')
        ref,binding_json,paired=db.execute(q.OFF_KEY_SQL,(obs['namespace'],obs['lexical_value'],'fixture-gen','product',100)).fetchone()
        binding=json.loads(binding_json);newrefs=[ref+'-variant',paired+'-variant'];records=[]
        for oldref in (ref,paired):records.append(json.loads(db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(oldref,)).fetchone()[0]))
        records[0]['data']['name']='Second exact retained variant'
        pointers=['jsonl:packet:1/0','jsonl:packet:1/1'];binding.update(inputAssetSha256='0'*64,recordPointers=pointers,recordSha256=hashlib.sha256(old.readers.canonical(records)).hexdigest())
        for number,(oldref,newref,record) in enumerate(zip((ref,paired),newrefs,records)):
            row=list(db.execute('SELECT * FROM retained_reference_record WHERE reference_record_id=?',(oldref,)).fetchone())
            row[0]=newref;row[3]='variant-asset';row[4]='0'*64;row[5]=number+1;row[7]=pointers[number];row[9]=canonical(record).decode();row[10]=q._hash(record)
            db.execute('INSERT INTO retained_reference_record VALUES('+','.join('?'*16)+')',row)
        for number,(oldref,newref) in enumerate(zip((ref,paired),newrefs)):
            row=list(db.execute('SELECT * FROM product_detail_projection WHERE reference_record_id=?',(oldref,)).fetchone())
            row[0]=newref;row[3]=newrefs[1] if number==0 else None;row[4]=canonical(dict(binding,recordPointer=pointers[number])).decode()
            db.execute('INSERT INTO product_detail_projection VALUES('+','.join('?'*10)+')',row)
        db.execute('INSERT INTO product_detail_identifier SELECT ?,identifier_ordinal,namespace,lexical_value,disposition,source_pointer FROM product_detail_identifier WHERE reference_record_id=?',(newrefs[0],ref))
        coverage=json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
        coverage['assets'].append(dict(assetId='variant-asset',sourceId='off',inputSHA256='0'*64,products=1,profiles=1,identifierOccurrences=1,receiptSha256='2'*64))
        coverage['identifierOccurrences']+=1
        db.execute('UPDATE product_detail_generation SET coverage_scope_json=?,processed_asset_count=2,product_records=3,profile_records=3',(canonical(coverage).decode(),));db.commit();db.execute('PRAGMA query_only=ON')
        m=copy.deepcopy(self.m);m['roles']['off-subset'].update(assets=coverage['assets'],sourceAssetCount=2,retainedProducts=3,retainedProfiles=3,coverageSha256=q._hash(coverage))
        out=self.call([obs],manifest=m);self.assertEqual(len(out['sourceProducts']),2)
        self.assertEqual(out['productDetailAvailability'][0]['state'],'ambiguous')
        self.assertNotEqual(out['sourceProducts'][0]['referenceRecordId'],out['sourceProducts'][1]['referenceRecordId'])
        with self.assertRaisesRegex(RefreshError,'candidate-bound'):self.call([obs],manifest=m,max_candidates=1)
        self.cleanup_ok()

    def test_digest_encodings_never_substitute_packet_object_or_pair_hashes(self):
        ref=self.references[0];db=self.db['usda-products']
        raw=db.execute('SELECT source_payload_json FROM retained_reference_record WHERE reference_record_id=?',(ref,)).fetchone()[0]
        wrong=hashlib.sha256(raw.encode()).hexdigest()
        self.edit('usda-products','UPDATE retained_reference_record SET parsed_record_sha256=? WHERE reference_record_id=?',(wrong,ref))
        self.edit('usda-products','UPDATE product_processing_audit SET source_record_sha256=? WHERE processing_id=?',(wrong,ref))
        with self.assertRaisesRegex(RefreshError,'record-digest'):self.call([self.observations[0]])
        self.cleanup_ok()

    def test_joint_profile_predicates_and_even_ordinal_never_fabricate_pair(self):
        pid=self.profile_ids[0];packet=pid[:-8]
        original=self.db['usda-profiles'].execute('SELECT native_packet_json FROM native_nutrient_profile WHERE profile_id=?',(pid,)).fetchone()[0]
        for mode in ('nutrition-id','identifier-list','source-record','acquisition','countries'):
            with self.subTest(mode=mode):
                profile=json.loads(original)[0]
                if mode=='nutrition-id':profile['id']='usda-files:nutrientProfile:foreign'
                if mode=='identifier-list':profile['data']['identifiers']=[]
                if mode=='source-record':profile['provenance']['recordId']='foreign'
                if mode=='acquisition':profile['provenance']['fetchedAt']='foreign'
                if mode=='countries':profile['countries']=None
                raw=canonical([profile]).decode();digest=hashlib.sha256(raw.encode()).hexdigest()
                self.edit('usda-profiles','UPDATE native_nutrient_profile SET native_packet_json=?,document_sha256=? WHERE profile_id=?',(raw,digest,pid))
                self.edit('usda-profiles','UPDATE dietary_packet_audit SET packet_sha256=? WHERE packet_id=?',(digest,packet))
                out=self.call([self.observations[0]])
                self.assertEqual(out['sourceProducts'],[]);self.assertEqual(out['productDetailAvailability'][0]['state'],'not-loaded')
        self.edit('identifier','UPDATE identifier_source_record SET record_ordinal=2 WHERE record_ordinal=1')
        self.edit('identifier','UPDATE identifier_assertion SET record_ordinal=2 WHERE assertion_id=1')
        obs=dict(self.observations[0],record_ordinal=2);out=self.call([obs]);self.assertEqual(out['sourceProducts'],[])
        self.cleanup_ok()

    def test_exact_types_stale_manifest_context_alias_and_caller_transaction(self):
        selection=q.FederatedQuerySelection(self.m['generationId'],q._hash(self.m),self.m['operationSelectionSha256'],'c'*64)
        with self.assertRaises(RefreshError):q.read_federated_product_details([],selection=old.ProductDetailQuerySelection('x','a'*64,'b'*64,'c'*64),identifier_evidence=self.evidence,stores=self.stores,selected_manifest=self.m)
        stale=copy.deepcopy(self.m);stale['roles']['usda-products']['databaseSha256']='0'*64
        with self.assertRaisesRegex(RefreshError,'manifest'):q.read_federated_product_details([],selection=selection,identifier_evidence=self.evidence,stores=self.stores,selected_manifest=stale)
        evidence=replace(self.evidence,db=self.db['usda-products'])
        with self.assertRaisesRegex(RefreshError,'independent-contexts'):q.read_federated_product_details([],selection=selection,identifier_evidence=evidence,stores=self.stores,selected_manifest=self.m)
        db=self.db['usda-products'];db.execute('PRAGMA query_only=OFF');db.execute('CREATE TEMP TABLE caller(value)');db.execute('INSERT INTO caller VALUES(1)');db.execute('SAVEPOINT caller_savepoint')
        trace=[];db.set_trace_callback(trace.append)
        with self.assertRaisesRegex(RefreshError,'caller-transaction-active'):self.call()
        self.assertEqual(trace,[]);db.set_trace_callback(None);self.assertTrue(db.in_transaction)
        db.execute('ROLLBACK TO caller_savepoint');self.assertEqual(db.execute('SELECT * FROM caller').fetchall(),[(1,)])
        db.rollback();db.execute('PRAGMA query_only=ON');self.cleanup_ok()

    def test_profile_raw_digest_error_and_sql_error_codes_are_safe(self):
        self.edit('usda-profiles','UPDATE native_nutrient_profile SET document_sha256=? WHERE profile_id=?',('0'*64,self.profile_ids[0]))
        with self.assertRaisesRegex(RefreshError,'record-digest'):self.call([self.observations[0]])
        limits={role:db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) for role,db in self.db.items()}
        self.edit('usda-products','DROP TABLE product_processing_audit')
        with self.assertRaisesRegex(RefreshError,'sql-bound-or-store') as error:self.call([self.observations[0]])
        self.assertEqual(str(error.exception),'product-detail-federation-sql-bound-or-store');self.cleanup_ok(limits)

    def test_OFF_subset_metadata_does_not_upgrade_original_or_accept_stale_counts(self):
        self.edit('off-subset','UPDATE product_detail_generation SET state=?',('completed',))
        with self.assertRaisesRegex(RefreshError,'off-subset-state'):self.call()
        self.assertEqual(self.db['off-subset'].execute('SELECT state FROM product_detail_generation').fetchone(),('completed',))
        self.cleanup_ok()

    def test_query_plans_are_index_points_and_no_observation_reconstruction(self):
        product=self.db['usda-products'].execute('EXPLAIN QUERY PLAN '+q.PRODUCT_KEY_SQL,(self.u['assetId'],self.sha,1)).fetchall()
        profile=self.db['usda-profiles'].execute('EXPLAIN QUERY PLAN '+q.PROFILE_KEY_SQL,(self.profile_ids[0],self.profile_ids[0][:-8])).fetchall()
        current=self.db['identifier'].execute('EXPLAIN QUERY PLAN '+q.CURRENT_SQL,(1,'selected-run')).fetchall()
        for rows in (product,profile,current):
            self.assertFalse(any('SCAN ' in row[3] for row in rows),rows)
        traces=[];self.db['usda-profiles'].set_trace_callback(traces.append);self.call();self.db['usda-profiles'].set_trace_callback(None)
        self.assertFalse(any('native_nutrient_observation' in sql or 'count(*)' in sql.lower() for sql in traces))


if __name__=='__main__':unittest.main()
