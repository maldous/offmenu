"""Generated fixtures only. No retained corpus, profile or source DB is opened."""
from dataclasses import replace
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import identifier_database as s
from offmenu.refresh.acceptance import Asset,SourceContract,contract_fingerprint,fingerprint
from offmenu.refresh.core import canonical,RefreshError


class IdentifierDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.target=self.root/'identifiers.sqlite'
        self.limits=s.IdentifierLimits(1024**2,100,1024**2,4096,100,100,4*1024**2,8*1024**2,30)

    def row(self,key,identifiers=(),kind='product',name=None):
        return {'id':'fixture:'+kind+':'+key,'kind':kind,'schemaVersion':'fixture/1',
                'provenance':{'sourceId':'usda-files','releaseId':'fixture-release','recordId':key,
                              'fetchedAt':None,'visibility':'private-candidate'},
                'data':{'name':name or key,'identifiers':list(identifiers)}}

    def bind_lineage(self,spec):
        value={'citations':spec.citations,'assets':spec.assets,'producerJob':spec.producer_job,
               'namespaceRules':spec.namespace_rules,'namespaceRuleVersion':spec.namespace_rule_version,
               'representation':spec.representation,'selectedCount':spec.selected_count,
               'selectedReviewSha256':spec.selected_review_sha256,'assetBindings':spec.asset_bindings}
        return replace(spec,lineage_sha256=hashlib.sha256(canonical(value)).hexdigest())

    def fixture(self,rows=None,raw=None,name='candidate.jsonl'):
        rows=rows or [self.row('a',[{'system':'barcode','value':'00123'}])]
        raw=raw if raw is not None else b''.join(canonical([r]) for r in rows)
        path=self.root/name;path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
        assets=(Asset('original.zip',5,'a'*64),Asset('rights.json',1,'b'*64),Asset('scope.json',1,'c'*64))
        schemas={'product':{'type':'object'},'nutrientProfile':{'type':'object'}}
        contract=SourceContract('usda-files','fixture-release','fixture-native',None,assets,len(rows),'d'*64,
            schemas,fingerprint(schemas),lambda _:(),'e'*64,assets[1],assets[2],
            frozenset(('retain','parse','transform')),fixture=True,acquisition_clock_status='unknown-retained')
        q={'schemaVersion':'offmenu-source-qualification/1','sourceId':contract.source_id,'releaseId':contract.release_id,
           'scopeId':contract.scope_id,'outputScope':'native','outputVisibility':'private','fixture':True,
           'normalizedRecords':len(rows),'candidateSha256':sha,'qualified':True,'status':'qualified','errors':[],
           'contractSha256':contract_fingerprint(contract)}
        q['qualificationSha256']=fingerprint(q)
        citation={'id':'fixture-citation','source_url':'https://example.invalid/source','publisher':'fixture',
                  'release_id':'fixture-release','retrieved_at':None,'licence_evidence_url':None,
                  'restrictions':[],'unknowns':['retrieval clock'],'receipt':'fixture-only'}
        fetch=[{'id':'fixture-'+a.path,'citation_id':citation['id'],'logical_path':a.path,'bytes':a.bytes,
                'sha256':a.sha256,'parent_asset_ids':[],'custody_ref':'fixture-only'} for a in assets]
        fetch.append({'id':'fixture-candidate','citation_id':citation['id'],'logical_path':path.name,
                      'bytes':len(raw),'sha256':sha,'parent_asset_ids':[a['id'] for a in fetch],
                      'custody_ref':'generated-fixture'})
        spec=s.IdentifierInput(str(path),'fixture-candidate',(citation,),tuple(fetch),
            {'id':'fixture-producer','engine':'fixture-native','version':'1','receipt':'fixture-only','output_sha256':sha},
            '0'*64,contract,q,q['qualificationSha256'],s._identity(path.stat()),
            (('barcode','barcode'),('USDA-FDC','USDA-FDC')),'native-systems-exact/1')
        return self.bind_lineage(spec)

    def build(self,spec,**changes):
        inputs=changes.pop('inputs',(spec,));pending=changes.pop('pending_sources',({'sourceId':'off','status':'pending'},))
        manifest=s.prepare_identifier_manifest(inputs,pending_sources=pending)
        args=dict(limits=self.limits,run_id='fixture-run',input_manifest_pointer='fixture-manifest.json',
                  input_manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),selection_receipt_sha256='f'*64,
                  pending_sources=pending);args.update(changes)
        return s.build_identifier_database(inputs,self.target,**args)

    def off_rows(self):
        return [{'ordinal':i,'originalSha256':'a'*64,'table':'products','code':code,'status':status,
                 'rawLineSha256':hashlib.sha256(('line'+str(i)).encode()).hexdigest(),
                 'canonicalBodySha256':hashlib.sha256(('body'+str(i)).encode()).hexdigest(),
                 'reason':None if status=='S' else 'repeated-native-key' if status=='C' else 'native-code-invalid'}
                for i,(code,status) in enumerate((('00123','S'),('0001','S'),('0002','C'),('0002','C'),(None,'Q')),1)]

    def off_fixture(self,rows=None):
        rows=self.off_rows() if rows is None else rows
        native=self.fixture(raw=b''.join(canonical(r) for r in rows),name='off-occurrences.jsonl')
        q={'schemaVersion':'offmenu-off-occurrence-metadata-binding/1','sourceId':'off','releaseId':'2026-10-12',
           'scopeId':'fixture-off-audit','fixture':True,'normalizedRecords':5,
           'candidateSha256':native.qualification['candidateSha256'],'originalSha256':'a'*64,
           'metadataReviewSha256':'b'*64,'counts':{'S':2,'C':2,'Q':1},'groups':1,'distinctValidKeys':3,
           'originalInputs':[{'path':'original.zip','bytes':5,'sha256':'a'*64}]}
        citation=dict(native.citations[0],id='off-fixture-citation',release_id='2026-10-12',source_id='off')
        assets=tuple(dict(a,id='off-'+a['id'],citation_id=citation['id'],
                          parent_asset_ids=['off-'+p for p in a['parent_asset_ids']]) for a in native.assets)
        return self.bind_lineage(replace(native,contract=None,qualification=q,
            qualification_sha256=hashlib.sha256(canonical(q)).hexdigest(),citations=(citation,),
            assets=assets,asset_id='off-'+native.asset_id,
            namespace_rules=(('barcode','barcode'),),expected_products=0,
            representation='verified-off-occurrences-jsonl',identity=None))

    def test_full_native_and_off_audit_share_lexical_keys_preserve_all_occurrences(self):
        usda=self.fixture([self.row('a',[{'system':'barcode','value':'00123'}]),
                           self.row('b',[{'system':'USDA-FDC','value':'7'}]),
                           self.row('a',kind='nutrientProfile'),self.row('b',kind='nutrientProfile')],name='usda-full.jsonl')
        usda=replace(usda,expected_products=2,identity=None);off=self.off_fixture()
        opened=[];original_open=os.open
        def observe(path,*args,**kwargs):
            if str(path) in (usda.candidate,off.candidate):opened.append(str(path))
            return original_open(path,*args,**kwargs)
        with patch.object(os,'open',side_effect=observe):result=self.build(usda,inputs=(usda,off,off),pending_sources=())
        self.assertEqual(opened,[usda.candidate,off.candidate])
        uc,oc=result['summary']['inputs'][0]['counts'],result['summary']['inputs'][1]['counts']
        self.assertEqual((uc['read'],uc['products'],uc['non_product']),(4,2,2))
        self.assertEqual((oc['read'],oc['products'],oc['non_product']),(5,0,5))
        self.assertEqual((oc['valid_code_associations'],oc['distinct_input_keys'],oc['ambiguous_key_groups'],oc['invalid_code_audits']),(4,3,1,1))
        self.assertEqual((oc['new_identifiers'],oc['existing_exact_keys'],oc['selected_primary_count']),(2,1,0))
        self.assertTrue(result['summary']['inputs'][2]['reusedCompletedAsset'])
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_source_record').fetchone()[0],9)
            members=db.execute("SELECT a.lexical_value,a.disposition,a.reason_code,r.source_row,r.kind,r.identity_state FROM identifier_assertion a JOIN identifier_source_record r USING(run_id,input_id,record_ordinal) WHERE policy_disposition='off-C' ORDER BY r.source_row").fetchall()
            self.assertEqual(members,[('0002','unresolved','repeated-native-key',i,'sourceOccurrence','unresolved') for i in (3,4)])
            q=db.execute("SELECT lexical_value,raw_json,raw_sha256,raw_bytes,disposition FROM identifier_assertion WHERE policy_disposition='off-Q'").fetchone()
            self.assertIsNone(q)
            evidence=db.execute("SELECT raw_line_sha256,source_record_sha256,source_row FROM identifier_source_record WHERE kind='sourceOccurrence' AND source_row=5").fetchone()
            self.assertEqual(evidence,(self.off_rows()[4]['rawLineSha256'],self.off_rows()[4]['canonicalBodySha256'],5))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(result['summary']['physicalProducts'],'unknown')

    def test_off_q_is_record_audit_without_observed_identifier(self):
        off=self.off_fixture();result=self.build(off)
        counts=result['summary']['inputs'][0]['counts']
        self.assertEqual((counts['read'],counts['off_Q'],counts['invalid_code_audits']),(5,1,1))
        self.assertEqual((counts['identifier_occurrences'],counts['identifiers_eligible']),(4,4))
        self.assertEqual(counts['identifiers_other-invalid'],0)
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_source_record').fetchone()[0],5)
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_assertion').fetchone()[0],4)
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_assertion WHERE record_ordinal=5').fetchone()[0],0)
            row=db.execute('SELECT native_record_id,source_row,raw_line_sha256,source_record_sha256,identifier_state FROM identifier_source_record WHERE record_ordinal=5').fetchone()
            self.assertEqual(row,('off:sourceOccurrence:'+'a'*64+':5',5,self.off_rows()[4]['rawLineSha256'],self.off_rows()[4]['canonicalBodySha256'],'Q'))
            audit=db.execute("SELECT identifier_ordinal,disposition,reason_code,details_json FROM identifier_exception WHERE record_ordinal=5").fetchone()
            self.assertEqual(audit[:3],(None,'invalid','native-code-invalid'))
            details=json.loads(audit[3])
            self.assertEqual(details['originalSha256'],'a'*64)
            self.assertEqual(details['rawLineSha256'],self.off_rows()[4]['rawLineSha256'])
            self.assertEqual(details['canonicalBodySha256'],self.off_rows()[4]['canonicalBodySha256'])
            self.assertEqual(details['rawIdentifierPresence'],'unknown')
            self.assertEqual(details['rawIdentifierType'],'unknown')
            self.assertEqual(details['rawIdentifierEvidence'],'unavailable')

    def test_off_audit_refuses_partition_ordinal_code_and_digest_mismatches(self):
        for mode in ('duplicate-S','split-C','Q-code','ordinal','original-digest','extra-field'):
            with self.subTest(mode=mode):
                rows=self.off_rows()
                if mode=='duplicate-S':rows[1]['code']=rows[0]['code']
                elif mode=='split-C':rows[3]['code']='0003'
                elif mode=='Q-code':rows[4]['code']='0004'
                elif mode=='ordinal':rows[1]['ordinal']=True
                elif mode=='original-digest':rows[0]['originalSha256']='c'*64
                else:rows[0]['unexpected']='field'
                self.target=self.root/('held-'+mode+'.sqlite')
                with self.assertRaises(RefreshError) as error:self.build(self.off_fixture(rows))
                self.assertFalse(self.target.exists())
                self.assertFalse(error.exception.identifier_database_retained_state['completeReceiptReturned'])

    def test_full_stream_lexical_collisions_invalids_and_nonproducts_accounted(self):
        a=self.row('a',[{'system':'barcode','value':'00123'},{'system':'USDA-FDC','value':'a'}],name='First')
        b=self.row('b',[{'system':'barcode','value':'00123'},{'system':'USDA-FDC','value':'b'}],name='Competing')
        c=self.row('c',[{'system':'barcode','value':'123'}])
        values=[{'system':'barcode','value':v} for v in (123,True,None,'',' 00123 ','１２３')]
        values += [{'system':'unknown','value':'00123'},'not-object']
        d=self.row('d',values);missing=self.row('missing');del missing['data']['identifiers']
        profile=self.row('a',kind='nutrientProfile')
        spec=self.fixture([a,b,c,d,missing,profile]);result=self.build(spec)
        self.assertTrue(result['loadComplete']);self.assertFalse(result['accepted'])
        counts=result['summary']['inputs'][0]['counts']
        self.assertEqual((counts['read'],counts['products'],counts['non_product']),(6,5,1))
        self.assertEqual((counts['identifier_occurrences'],counts['identifiers_eligible'],counts['new_identifiers']),(13,7,6))
        self.assertEqual(counts['unread'],0);self.assertEqual(counts['products_no_identifiers'],1)
        rows=s.query_identifiers(result,namespace='barcode',lexical_value='00123')['rows']
        self.assertEqual(len(rows),2);self.assertEqual({r['source_record_id'] for r in rows},{'a','b'})
        self.assertEqual(len(s.query_identifiers(result,namespace='barcode',lexical_value='123')['rows']),1)
        self.assertEqual(len(s.query_identifiers(result,namespace='barcode',lexical_value=' 00123 ')['rows']),1)
        self.assertEqual(len(s.query_identifiers(result,namespace='barcode',lexical_value='１２３')['rows']),1)
        invalid=s.query_identifiers(result,disposition='invalid')['rows']
        self.assertTrue(any(r['lexical_value']=='' for r in invalid))
        self.assertTrue(any(type(json.loads(r['raw_json'])) is dict and
                            type(json.loads(r['raw_json']).get('value')) is int and
                            json.loads(r['raw_json'])['value']==123 for r in invalid))
        self.assertTrue(result['summary']['pendingSources']);self.assertEqual(result['summary']['physicalProducts'],'unknown')
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_source_record').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT count(*) FROM load_checkpoint').fetchone()[0],1)
            self.assertTrue(all(r[0]=='deterministic' for r in db.execute('SELECT interpretation_mode FROM parse_job')))

    def test_source_occurrences_repeated_conflicting_and_repeated_alternative_survive(self):
        a=self.row('a',[{'system':'barcode','value':'00123'}],name='A')
        b=self.row('a',[{'system':'barcode','value':'00123'}],name='B')
        result=self.build(self.fixture([a,a,b,b]))
        counts=result['summary']['inputs'][0]['counts']
        self.assertEqual([counts['source_'+k] for k in ('new','identical','conflicting','malformed')],[1,2,1,0])
        self.assertEqual(result['summary']['sourceOccurrences'],4)
        self.assertEqual(len(s.query_identifiers(result,namespace='barcode',lexical_value='00123')['rows']),4)

    def test_single_input_open_and_exact_completed_asset_reference_is_idempotent(self):
        spec=self.fixture();real=os.open;opens=[]
        def opened(path,*a,**kw):
            if str(path)==spec.candidate:opens.append(str(path))
            return real(path,*a,**kw)
        with patch.object(os,'open',side_effect=opened):result=self.build(spec,inputs=(spec,spec))
        self.assertEqual(opens,[spec.candidate]);self.assertEqual(result['summary']['sourceOccurrences'],1)
        self.assertTrue(result['summary']['inputs'][1]['reusedCompletedAsset'])

    def test_selected_lookup_scope_does_not_reduce_native_contract_or_scan_full_candidate(self):
        a=self.row('a',[{'system':'barcode','value':'00123'}]);b=self.row('b',[{'system':'barcode','value':'00123'}])
        native=self.fixture([a,b,self.row('c',kind='nutrientProfile')]);upstream=Path(native.candidate)
        wrapper={'sourceId':'usda-files','releaseId':'fixture-release','scopeId':native.contract.scope_id,
            'candidateSha256':native.qualification['candidateSha256'],'qualificationSha256':native.qualification_sha256,
            'visibility':'private','fixture':True,'status':'matched','barcode':'00123','matches':[
             {'record':r,'nativeProductId':r['id'],'sourceRecordId':r['provenance']['recordId'],'candidateLine':i+1}
             for i,r in enumerate([a,b])]}
        raw=canonical({'status':'PRIVATE_NATIVE_LOOKUP_VERIFIED','lookup':wrapper});path=self.root/'lookup.json';path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
        asset={'id':'fixture-lookup','citation_id':'fixture-citation','logical_path':path.name,'bytes':len(raw),
               'sha256':sha,'parent_asset_ids':[native.asset_id],'custody_ref':'fixture-selected-review'}
        spec=self.bind_lineage(replace(native,candidate=str(path),asset_id=asset['id'],assets=native.assets+(asset,),
            identity=None,producer_job=dict(native.producer_job,id='fixture-lookup',output_sha256=sha),
            representation='reviewed-native-lookup-json',selected_count=2,selected_review_sha256='9'*64))
        upstream.unlink()  # Generated upstream file unavailable: no fallback/full scan allowed.
        result=self.build(spec)
        self.assertEqual(native.contract.expected_records,3);self.assertEqual(result['summary']['sourceOccurrences'],2)
        rows=s.query_identifiers(result,namespace='barcode',lexical_value='00123')['rows']
        self.assertEqual(len(rows),2);self.assertTrue(rows[0]['source_pointer'].startswith('/lookup/matches/0/record/'))
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual(db.execute('SELECT native_candidate_ordinal FROM identifier_source_record ORDER BY record_ordinal').fetchall(),[(1,),(2,)])
            self.assertEqual(db.execute('SELECT raw_line_sha256 FROM identifier_source_record').fetchall(),[(None,),(None,)])

    def test_manifest_or_lineage_mismatch_refuses_before_any_output(self):
        spec=self.fixture()
        with self.assertRaises(RefreshError):self.build(replace(spec,lineage_sha256='0'*64))
        with self.assertRaisesRegex(RefreshError,'selected-input-manifest-mismatch'):self.build(spec,input_manifest_sha256='0'*64)
        self.assertFalse(self.target.exists());self.assertFalse(list(self.root.glob('.identifier-load-*')))

    def test_changed_input_hash_incomplete_eof_and_malformed_rows_hold_without_publication(self):
        for i,mode in enumerate(('hash','count','malformed')):
            with self.subTest(mode=mode):
                row=self.row(str(i),[{'system':'barcode','value':'00123'}])
                spec=self.fixture([row],raw=b'not-json\n' if mode=='malformed' else None,name=f'candidate-{i}.jsonl')
                if mode=='hash':
                    raw=Path(spec.candidate).read_bytes().replace(b'00123',b'99123');Path(spec.candidate).write_bytes(raw)
                    spec=replace(spec,identity=s._identity(Path(spec.candidate).stat()))
                if mode=='count':
                    c=replace(spec.contract,expected_records=2);q=dict(spec.qualification,normalizedRecords=2,contractSha256=contract_fingerprint(c));q.pop('qualificationSha256');q['qualificationSha256']=fingerprint(q)
                    spec=replace(spec,contract=c,qualification=q,qualification_sha256=q['qualificationSha256'])
                before=len(os.listdir('/proc/self/fd'))
                with self.assertRaises(RefreshError) as failure:self.build(spec)
                self.assertFalse(self.target.exists());self.assertFalse(failure.exception.identifier_database_retained_state['completeReceiptReturned'])
                self.assertTrue(Path(failure.exception.identifier_database_retained_state['stage']).exists())
                self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_no_overwrite_and_query_custody_mutation_refuses(self):
        spec=self.fixture();result=self.build(spec);before=self.target.read_bytes()
        with self.assertRaisesRegex(RefreshError,'destination-exists'):self.build(spec)
        self.assertEqual(self.target.read_bytes(),before)
        with self.target.open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(RefreshError,'query-custody'):s.query_identifiers(result)

    def test_keyset_pages_prefix_and_checksum_never_merge_source_rows(self):
        rows=[self.row(str(i),[{'system':'barcode','value':v}]) for i,v in enumerate(['00123','00124','123','00123'])]
        result=self.build(self.fixture(rows));page=s.query_identifiers(result,namespace='barcode',prefix='00',limit=1)
        seen=[page['rows'][0]['assertion_id']]
        while page['hasMore']:
            page=s.query_identifiers(result,namespace='barcode',prefix='00',limit=1,after_assertion_id=page['nextAssertionId'])
            seen.extend(r['assertion_id'] for r in page['rows'])
        self.assertEqual(len(set(seen)),3)
        self.assertEqual(s._assessment('barcode','036000291452'),('digits-supported-length','valid'))
        self.assertEqual(s._assessment('barcode','036000291453'),('digits-supported-length','invalid'))
        with self.assertRaises((sqlite3.OperationalError,RefreshError)):s.query_identifiers(result,max_steps=1)

    def test_v2_core_tables_and_legacy14_column_view_are_one_database(self):
        result=self.build(self.fixture())
        expected={'fetch_citation','fetch_asset','parse_job','identifier_load','identifier_input',
                  'identifier_source_record','identifier_assertion','identifier_exception','load_checkpoint'}
        with closing(sqlite3.connect(self.target)) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue(expected<=tables)
            self.assertEqual(len(db.execute('PRAGMA table_info(v_barcode_inspection)').fetchall()),14)
            self.assertEqual(db.execute('SELECT identity_state FROM fetch_citation').fetchone()[0],'unresolved-backfill')
            self.assertEqual(db.execute('SELECT product_id,symbology,recorded_context_links FROM v_barcode_inspection').fetchone(),(None,None,None))
        self.assertEqual(len(s.query_identifiers(result)['rows']),1)

    def test_initial_parent_fsync_and_sqlite_wrong_descriptor_refuse_before_source_read(self):
        spec=self.fixture();before=len(os.listdir('/proc/self/fd'))
        with patch.object(os,'fsync',side_effect=OSError('fixture parent sync')):
            with self.assertRaisesRegex(OSError,'fixture parent sync'):self.build(spec)
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        foreign=self.root/'foreign.sqlite';db=sqlite3.connect(foreign);db.execute('CREATE TABLE keep(x)');db.close()
        preserved=foreign.read_bytes();connect=sqlite3.connect
        with patch.object(s.sqlite3,'connect',side_effect=lambda *a,**kw:connect(foreign)):
            with self.assertRaisesRegex(RefreshError,'sqlite-descriptor-ambiguous'):self.build(spec)
        self.assertEqual(foreign.read_bytes(),preserved);self.assertFalse(self.target.exists())
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_twenty_two_generated_lookup_observations_one_barcode_key_not_products(self):
        products=[self.row(str(i),[{'system':'barcode','value':'00012345'},
                                 {'system':'USDA-FDC','value':str(i)}]) for i in range(22)]
        for i,row in enumerate(products):row['provenance']['sourceRow']=100+i
        native=self.fixture(products+[self.row(str(i),kind='nutrientProfile') for i in range(22)])
        wrapper={'sourceId':'usda-files','releaseId':'fixture-release','scopeId':native.contract.scope_id,
            'candidateSha256':native.qualification['candidateSha256'],'qualificationSha256':native.qualification_sha256,
            'visibility':'private','fixture':True,'status':'matched','barcode':'00012345','matches':[
             {'record':row,'nativeProductId':row['id'],'sourceRecordId':str(i),'candidateLine':i+1}
             for i,row in enumerate(products)]}
        raw=canonical({'status':'PRIVATE_NATIVE_LOOKUP_VERIFIED','lookup':wrapper});path=self.root/'lookup22.json';path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
        asset={'id':'fixture-lookup22','citation_id':'fixture-citation','logical_path':path.name,'bytes':len(raw),
               'sha256':sha,'parent_asset_ids':[native.asset_id],'custody_ref':'fixture-selected-review'}
        spec=self.bind_lineage(replace(native,candidate=str(path),asset_id=asset['id'],assets=native.assets+(asset,),
            identity=s._identity(path.stat()),producer_job=dict(native.producer_job,output_sha256=sha),
            representation='reviewed-native-lookup-json',selected_count=22,selected_review_sha256='9'*64))
        Path(native.candidate).unlink()
        result=self.build(spec)
        self.assertEqual(len(s.query_identifiers(result,namespace='barcode',limit=25)['rows']),22)
        self.assertEqual(result['summary']['physicalProducts'],'unknown')
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM identifier WHERE namespace='barcode'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM identifier_source_record').fetchone()[0],22)
            self.assertEqual(db.execute('SELECT source_row,native_candidate_ordinal,record_ordinal FROM identifier_source_record ORDER BY record_ordinal LIMIT 1').fetchone(),(100,1,1))

    def test_oversized_identifier_retains_only_hash_extent_and_locator(self):
        value='Z'*(60*1024);entry={'system':'barcode','value':value}
        encoded=canonical(entry);result=self.build(self.fixture([self.row('large',[entry])]))
        with closing(sqlite3.connect(self.target)) as db:
            row=db.execute('SELECT lexical_value,raw_json,raw_sha256,raw_bytes,source_pointer FROM identifier_assertion').fetchone()
            self.assertEqual(row,(None,None,hashlib.sha256(encoded).hexdigest(),len(encoded),'/0/data/identifiers/0'))
            self.assertEqual(db.execute('SELECT count(*) FROM identifier').fetchone()[0],0)
        query=s.query_identifiers(result,disposition='invalid')['rows']
        self.assertEqual(len(query),1);self.assertIsNone(query[0]['lexical_value'])
        self.assertIsNone(query[0]['raw_json']);self.assertNotIn(value.encode(),self.target.read_bytes())

    def test_identifier_exception_disposition_and_locator_match_assertion(self):
        entries=[{'system':'barcode','value':''},{'system':'barcode','value':123},
                 {'system':'barcode','value':'bad\x00value'},'not-object',
                 {'system':'barcode','value':False},{'system':'barcode','value':None},
                 {'system':'barcode'},{'system':'unknown','value':'00123'}]
        self.build(self.fixture([self.row('invalids',entries)]))
        with closing(sqlite3.connect(self.target)) as db:
            rows=db.execute('SELECT a.identifier_ordinal,a.disposition,e.disposition,a.source_pointer,e.source_pointer,e.details_json '
                'FROM identifier_assertion a JOIN identifier_exception e USING(run_id,input_id,record_ordinal,identifier_ordinal) '
                'ORDER BY a.identifier_ordinal').fetchall()
        self.assertEqual(len(rows),len(entries))
        for i,(ordinal,assertion,exception,pointer,exception_pointer,details) in enumerate(rows):
            with self.subTest(ordinal=ordinal):
                self.assertEqual(assertion,'invalid' if i<5 else 'unresolved')
                self.assertEqual(exception,assertion)
                self.assertEqual(exception_pointer,pointer)
                self.assertEqual(pointer,'/0/data/identifiers/'+str(i))
                self.assertEqual(json.loads(details)['rawSha256'],hashlib.sha256(canonical(entries[i])).hexdigest())
                self.assertEqual(json.loads(details)['bytes'],len(canonical(entries[i])))

    def test_asset_unknown_reasons_preserve_reviewer_objects_and_legacy_callers(self):
        # W64-IDB-001: both reason objects from the reviewer's reproduction.
        reasons=[
            {'download_url':'No direct asset download URL recorded; landing URL is not substituted.',
             'fetch_owned_asset_id':'No pre-existing fetch asset ID recorded; LOCAL deterministic backfill key remains unresolved.',
             'retrieved_at':'Unknown-retained acquisition clock; no local lifecycle/completion date substituted.'},
            {'download_url':'No direct asset download URL recorded; landing URL is not substituted.',
             'retrieved_at':'Unknown-retained acquisition clock; no local lifecycle/completion date substituted.'},
            ['legacy unknowns caller'],
            {'derived':'not a direct FETCH asset'}]
        spec=self.fixture();assets=[dict(a) for a in spec.assets]
        for i,asset in enumerate(assets):
            asset['unknown_fields_json']=json.dumps(reasons[i])
        assets[2]['unknowns']=reasons[2]
        # Existing unknowns-style callers retain precedence, as with citations.
        assets[2]['unknown_fields_json']='["unused fallback"]'
        spec=self.bind_lineage(replace(spec,assets=tuple(assets)))
        self.build(spec)
        with closing(sqlite3.connect(self.target)) as db:
            for asset,expected in zip(assets,reasons):
                with self.subTest(asset=asset['id']):
                    row=db.execute('SELECT unknown_fields_json,metadata_json FROM fetch_asset WHERE asset_id=?',
                                   (asset['id'],)).fetchone()
                    self.assertEqual(json.loads(row[0]),expected)
                    self.assertEqual(json.loads(row[1]),asset)

    def test_fixed_selected22_descriptor_uses_only_control_metadata(self):
        q={'schemaVersion':'offmenu-source-qualification/1','sourceId':'usda-files','releaseId':'2026-04-30',
           'scopeId':'usda-20260430-private-native-products-v1','outputScope':'native','outputVisibility':'private',
           'fixture':False,'normalizedRecords':4202558,'candidateSha256':'706c767d47d0feebf64915c6f0d3aba45840b012ab07bb7a2d21915f303b06a3',
           'manifestSha256':'02668436f698f5886253d6d360cd3d61bca2651152008e7c6b79bf433987adea',
           'policySha256':'ab6b9f9de7c1df60821e8c627b74bb25656aac12523e9728a0a009a139c3af12',
           'contractSha256':'67b5e257d288a29cfd96dfa1cb8faba1e661821257f415c93ac87edab2692164',
           'rightsEvidenceSha256':'da3bef50a8490d4ddc1d98db49b59f7af0fd9145a75a9249d9cc2a0a64f9137e',
           'scopeEvidenceSha256':'a96895c7481c08db3fc77beffcc92d80ebc4c8bfa87b98382dc7fcf8c16305f3',
           'qualified':True,'errors':[],'status':'qualified','qualificationSha256':s.NATIVE_QUALIFICATION_SHA256}
        citation={'citation_id':'fixture-citation','identity_state':'unresolved-backfill','source_url':None,
                  'publisher':None,'release_id':'2026-04-30','licence_evidence_url':None,
                  'restrictions_json':'[]','unknown_fields_json':'["metadata-only fixture"]','metadata_origin_pointer':'fixture'}
        assets=[{'asset_id':key,'citation_id':'fixture-citation','identity_state':'unresolved-backfill'}
                for key in ('usda-archive:2026-04',s.PARENT_NATIVE_ASSET_ID)]
        operation={'schemaVersion':'offmenu-selected22-identifier-operation/1','qualification':q,
           'fetch_citations':[citation],'fetch_assets':assets,'input_path':'/not-opened/lookup-result.json',
           'input_identity':[1,2,34844,3,4],
           'cached_lookup_job':{'id':'cached-fixture','engine':None,'version':None,
                                'unknowns':['engine','version'],'receipt':'fixture-only'}}
        with patch.object(os,'open',side_effect=AssertionError('no source open during preparation')):
            spec=s.selected22_input(operation);manifest=s.prepare_identifier_manifest((spec,))
        self.assertEqual(spec.contract.expected_records,4202558)
        self.assertEqual(manifest['inputs'][0]['expectedRecords'],22)
        self.assertEqual(manifest['inputs'][0]['candidateSha256'],s.SELECTED22_SHA256)

        full_usda=dict(operation,input_identity=None,native_candidate_job=operation['cached_lookup_job'])
        off_citation=dict(citation,citation_id='off-fixture-citation',release_id='2026-10-12',source_id='off')
        full={'schemaVersion':'offmenu-full-retained-identifier-operation/1','sources':['usda-files','off'],
              'usda-files':full_usda,'off':{'input_path':'/not-opened/occurrences.jsonl','input_identity':None,
                  'fetch_citations':[off_citation],
                  'fetch_assets':[{'asset_id':s.OFF_ORIGINAL_ASSET_ID,'citation_id':'off-fixture-citation',
                                   'identity_state':'unresolved-backfill','unknown_fields_json':'["fixture metadata"]'}],
                  'occurrence_job':operation['cached_lookup_job']},
              'limits':dict(max_scan_bytes=20081166515,max_records=9010221,max_line_bytes=8388608,
                  max_identifier_bytes=4096,max_identifiers_per_record=2,max_exceptions=1000,
                  max_database_bytes=64*1024**3,max_storage_bytes=128*1024**3,max_seconds=86400)}
        with patch.object(os,'open',side_effect=AssertionError('no body open')),patch.object(Path,'stat',side_effect=AssertionError('no body stat')):
            inputs=s.full_retained_inputs(full);s._full_limits(full,inputs)
            manifest=s.prepare_identifier_manifest(inputs)
        self.assertEqual([m['expectedRecords'] for m in manifest['inputs']],[4202558,4807663])
        self.assertEqual([m['expectedProducts'] for m in manifest['inputs']],[2101279,0])
        self.assertIsNone(manifest['inputs'][1]['contractSha256'])
        self.assertEqual(manifest['inputs'][1]['occurrenceAudit']['distinctValidKeys'],4807217)
        with self.assertRaises(RefreshError):s._full_limits(dict(full,limits=dict(full['limits'],max_seconds=0)),inputs)


if __name__=='__main__':unittest.main()
