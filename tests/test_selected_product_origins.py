"""Generated SQLite rows and application proof fixtures; no private22 access."""
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import selected_product_origins as s
from offmenu.refresh import product_adapters as adapters
from offmenu.refresh import product_field_origins as origins
from offmenu.refresh.acceptance import Asset, SourceContract, contract_fingerprint, fingerprint, ids_digest
from offmenu.refresh.core import RefreshError, canonical
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors


class SelectedProductOriginsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.path = self.root/'source.sqlite'
        self.context = adapters.ProductContext('usda-files','fixture-release',None,
            'fixture terms','fixture source','a'*64,'b'*64,
            acquisition_clock_status='unknown-retained',clock_evidence_sha256='c'*64)
        self.archive = Asset('retained/synthetic.zip',1234,'d'*64)  # Never created/opened.
        self.raw = {}
        self.records = []
        entries = []
        for index,key in enumerate(('101','202')):
            food = {'fdc_id':key,'description':'Name '+key,'data_type':'branded_food','publication_date':None}
            brand = {'fdc_id':key,'gtin_upc':'00012345','ingredients':'Milk, oats\nand "x"' if index == 0 else '',
                'brand_owner':'' if index == 0 else None,'brand_name':'Brand' if index == 0 else None,
                'market_country':'US','serving_size':'0' if index == 0 else None,
                'serving_size_unit':'g','household_serving_fulltext':None}
            food_row,brand_row = 7+index,91+2*index
            self.raw['food',food_row] = key,json.dumps(food,sort_keys=True)
            self.raw['branded_food',brand_row] = key,json.dumps(brand,sort_keys=True)
            data = {'name':food['description'],'identifiers':[{'system':'USDA-FDC','value':key},
                {'system':'barcode','value':'00012345'}], 'brand':brand['brand_owner'] or brand['brand_name'],
                'dataType':'branded_food','ingredientsText':brand['ingredients'],'marketCountry':'US',
                'serving':{'amount':0.0 if index == 0 else None,'unit':'g','label':None},
                'nutritionId':'usda-files:nutrientProfile:'+key}
            record = adapters._record(self.context,'product',key,data,('US',),None)
            record['provenance'].update(sourceRow=food_row,inputSha256={'archive':self.archive.sha256})
            self.records.append(record)
            rowpin = lambda table,ordinal:s.RowPin(ordinal,hashlib.sha256(self.raw[table,ordinal][1].encode()).hexdigest())
            entries.append(s.SelectedProduct(record['id'],key,2*food_row-1,hashlib.sha256(canonical(record)).hexdigest(),
                rowpin('food',food_row),rowpin('branded_food',brand_row)))
        self.records = tuple(self.records)
        # Oversized unselected row proves that a table/body scan is not required.
        for ordinal in range(1,100):
            if ('food',ordinal) not in self.raw:
                key = str(10000+ordinal)
                self.raw['food',ordinal] = key,json.dumps({'fdc_id':key,'description':'Unselected','data_type':'survey_food'})
        key = self.raw['food',99][0]
        self.raw['food',99] = key,json.dumps({'fdc_id':key,'description':'Unselected','data_type':'survey_food',
                                            'private':'UNSELECTED'*20000})
        other_keys = iter([value[0] for (table,_),value in self.raw.items()
                          if table == 'food' and value[0] not in ('101','202')])
        for ordinal in range(1,94):
            if ('branded_food',ordinal) not in self.raw:
                key = next(other_keys); self.raw['branded_food',ordinal] = key,json.dumps({'fdc_id':key,'gtin_upc':None})
        self.make_database()
        rights,scope,clock = Asset('rights.json',1,'a'*64),Asset('scope.json',1,'b'*64),Asset('clock.json',1,'c'*64)
        def forbidden_semantic(_): raise AssertionError('no requalification callback')
        schemas = {'product':{'type':'object'},'nutrientProfile':{'type':'object'}}
        self.contract = SourceContract('usda-files','fixture-release','full-native-fixture',None,
            (self.archive,rights,scope,clock),198,
            ids_digest(['usda-files:'+kind+':'+value[0] for (table,_),value in self.raw.items()
                        if table == 'food' for kind in ('product','nutrientProfile')]),
            schemas,fingerprint(schemas),forbidden_semantic,'e'*64,rights,scope,
            frozenset(('retain','parse','transform')),fixture=True,
            acquisition_clock_status='unknown-retained',clock_evidence=clock)
        self.candidate_sha = 'f'*64  # Independently authored fixture qualification root, no candidate file.
        q = {'schemaVersion':'offmenu-source-qualification/1','qualified':True,'status':'qualified','errors':[],
            'sourceId':'usda-files','releaseId':'fixture-release','scopeId':'full-native-fixture',
            'outputScope':'native','outputVisibility':'private','fixture':True,'normalizedRecords':198,
            'contractSha256':contract_fingerprint(self.contract),'candidateSha256':self.candidate_sha}
        self.qualification = dict(q,qualificationSha256=fingerprint(q))
        self.limits = s.SelectedOriginLimits(10,1024**2,1024**2,65536,262144,65536,1024**2,4*1024**2,100000,30)
        self.manifest = self.manifest_bytes()
        database = Asset('source.sqlite',self.path.stat().st_size,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.scope = s.SelectedOriginScope('two-selected-origin-fixture',self.context,self.archive,database,
            Asset('manifest.json',len(self.manifest),hashlib.sha256(self.manifest).hexdigest()),
            s._signature(self.path.stat()),contract_fingerprint(self.contract),self.qualification['qualificationSha256'],
            self.candidate_sha,'1'*64,'2'*64,'3'*64,'4'*64,'0'*64,
            hashlib.sha256(Path(origins.__file__).read_bytes()).hexdigest(),
            hashlib.sha256(Path(s.__file__).read_bytes()).hexdigest(),
            (('food','Exact_Release/food.csv'),('branded_food','Different_Exact_Part/branded_food.csv')),
            tuple(entries),ids_digest(r['id'] for r in self.records))
        self.rebind()

    def make_database(self,indexed=True):
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE raw(tab TEXT,ordinal INTEGER,identity TEXT,parent TEXT,body TEXT NOT NULL'+
                       (',PRIMARY KEY(tab,ordinal))' if indexed else ')'))
            if indexed: db.execute('CREATE UNIQUE INDEX identity_idx ON raw(tab,identity)')
            for (table,ordinal),(key,body) in self.raw.items():
                db.execute('INSERT INTO raw VALUES(?,?,?,?,?)',(table,ordinal,key,None,body))
        db.close()

    def manifest_bytes(self):
        archive = {**asdict(self.archive),'path':'synthetic.zip','role':'archive'}
        return canonical({'schemaVersion':'offmenu-product-candidate/2','status':'normalized-candidate',
            'sourceId':'usda-files','releaseId':'fixture-release','normalizedRecords':198,
            'candidateSha256':self.candidate_sha,'inputFiles':[archive],
            'outputHashes':{'source.sqlite':hashlib.sha256(self.path.read_bytes()).hexdigest(),
                            'candidate.jsonl':self.candidate_sha},
            'contract':{'context':asdict(self.context),'inputFiles':[archive],'adapterVersion':adapters.VERSION}})

    def rebind(self):
        value = asdict(self.scope); del value['operation_evidence_sha256']
        self.binding = canonical({'schemaVersion':'offmenu-selected-origin-binding/1',
                                  'scope':value,'limits':asdict(self.limits)})
        self.scope = replace(self.scope,operation_evidence_sha256=hashlib.sha256(self.binding).hexdigest())

    def run_selected(self,**changes):
        args = dict(scope=self.scope,limits=self.limits,contract=self.contract,qualification=self.qualification,
                    normalization_manifest=self.manifest,binding_evidence=self.binding,database_root=self.root)
        records = changes.pop('records',self.records); args.update(changes)
        return s.emit_selected_usda_product_origins(records,**args)

    def test_all_selected_products_complete_origins_unchanged_values_and_distinct_coordinates(self):
        before = canonical(self.records); full_contract = contract_fingerprint(self.contract)
        result = self.run_selected(); self.assertEqual(result['selectedCount'],2)
        self.assertEqual([r['id'] for r in result['records']],[r['id'] for r in self.records])
        self.assertEqual(canonical(self.records),before); self.assertEqual(contract_fingerprint(self.contract),full_contract)
        self.assertEqual(self.contract.expected_records,198)
        self.assertEqual(result['measurements']['pointRowsRead'],4)
        self.assertLess(result['measurements']['sourceRowBytes'],65536)
        for old,new in zip(self.records,result['records']):
            self.assertEqual(canonical(old['data']),canonical(new['data']))
            p = new['provenance']; self.assertEqual(set(p['fieldOrigins']),set(datum_pointers(new['data'])))
            self.assertEqual(field_origin_errors(new,{self.archive.path:self.archive.sha256},
                                                policy_pins=[self.scope.emitter_policy_sha256]),[])
        origin = result['records'][0]['provenance']['fieldOrigins']
        self.assertEqual(origin['/data/name']['row'],7)
        ingredients = origin['/data/ingredientsText']['inputs']
        self.assertEqual([o['row'] for o in ingredients],[7,91,91])
        self.assertEqual(ingredients[-1]['archiveMember'],'Different_Exact_Part/branded_food.csv')
        self.assertEqual(ingredients[-1]['sourceField'],'/ingredients')
        self.assertEqual(origin['/data/identifiers/1/value']['inputs'][-1]['sourceField'],'/gtin_upc')
        self.assertEqual(origin['/data/nutritionId']['inputs'][0]['row'],7)
        self.assertEqual(origin['/data/nutritionId']['inputs'][0]['table'],'food')
        self.assertEqual(result['records'][0]['data']['serving']['amount'],0)
        self.assertEqual(result['records'][1]['data']['ingredientsText'],'')
        for flag in ('accepted','qualified','originalArchiveRead','candidateScanPerformed',
                     'fullDatabaseHashPerformed','runtimeOrResourcesAdmitted'): self.assertFalse(result[flag])
        self.assertEqual(result['identityOrIngredientEdges'],0)

    def test_full_stage_normalization_lookup_and_archive_are_never_called(self):
        from offmenu.refresh import product_origin_stage,product_qualification,native_barcode_lookup
        import zipfile
        with patch.object(product_origin_stage,'qualify_product_origins',side_effect=AssertionError('full stage')), \
             patch.object(product_qualification,'qualify_product_candidate',side_effect=AssertionError('full qualify')), \
             patch.object(adapters,'normalize_products',side_effect=AssertionError('normalize')), \
             patch.object(native_barcode_lookup,'lookup_native_barcode',side_effect=AssertionError('full scan')), \
             patch.object(zipfile,'ZipFile',side_effect=AssertionError('archive open')):
            self.assertEqual(self.run_selected()['selectedCount'],2)
        self.assertFalse((self.root/'candidate.jsonl').exists()); self.assertFalse((self.root/self.archive.path).exists())

    def test_unbound_selection_derivation_review_member_and_custody_inputs_refuse_before_db(self):
        bad = [None,replace(self.scope,derivation_review_sha256=None),replace(self.scope,custody_review_sha256=None),
               replace(self.scope,lookup_review_sha256=None),replace(self.scope,database_identity=()),
               replace(self.scope,members=()),replace(self.scope,expected_ids_sha256=None)]
        for scope in bad:
            with patch.object(s,'_open_database',side_effect=AssertionError('DB must not open')):
                with self.assertRaises(RefreshError): self.run_selected(scope=scope)

    def test_member_row_or_limits_cannot_change_under_same_independent_binding_pin(self):
        bad = replace(self.scope,members=(('food','Other/food.csv'),('branded_food','Other/branded_food.csv')))
        with self.assertRaisesRegex(RefreshError,'operation-binding-mismatch'): self.run_selected(scope=bad)
        with self.assertRaisesRegex(RefreshError,'operation-binding-mismatch'):
            self.run_selected(limits=replace(self.limits,max_records=100))
        with self.assertRaisesRegex(RefreshError,'operation-evidence-required'): self.run_selected(binding_evidence=b'{}')

    def test_qualified_context_and_full_factory_counts_cannot_be_rewritten_to_selected_count(self):
        with patch.object(s,'_open_database',side_effect=AssertionError('DB must not open')):
            with self.assertRaises(RefreshError): self.run_selected(contract=replace(self.contract,expected_records=2))
            with self.assertRaises(RefreshError): self.run_selected(contract=replace(self.contract,holds=('hold',)))
            with self.assertRaises(RefreshError): self.run_selected(normalization_manifest=b'{}')
            with self.assertRaises(RefreshError): self.run_selected(qualification={})

    def test_selected_record_count_ids_order_hash_and_kind_are_exact(self):
        variants = [self.records[:1],self.records+self.records[:1],tuple(reversed(self.records))]
        wrong = json.loads(canonical(self.records)); wrong[0]['data']['name'] = 'changed'; variants.append(tuple(wrong))
        wrong = json.loads(canonical(self.records)); wrong[0]['kind'] = 'nutrientProfile'; variants.append(tuple(wrong))
        for records in variants:
            with patch.object(s,'_open_database',side_effect=AssertionError('DB must not open')):
                with self.assertRaises(RefreshError): self.run_selected(records=records)
        def forbidden_generator(): raise AssertionError('hidden scan'); yield
        with self.assertRaisesRegex(RefreshError,'bounded-selected-buffer-required'):
            self.run_selected(records=forbidden_generator())

    def test_changed_or_partial_data_even_with_new_input_pin_fails_source_projection(self):
        original = canonical(self.records)
        for partial in (False,True):
            records = json.loads(original)
            if partial: records[0]['data'] = {'ingredientsText':records[0]['data']['ingredientsText']}
            else: records[0]['data']['ingredientsText'] = 'invented value'
            self.records = tuple(records)
            first = replace(self.scope.products[0],record_sha256=hashlib.sha256(canonical(records[0])).hexdigest())
            self.scope = replace(self.scope,products=(first,self.scope.products[1])); self.rebind()
            with self.assertRaisesRegex(RefreshError,'projection-mismatch'): self.run_selected()

    def test_no_branded_coordinate_can_be_inferred_from_primary_food_row(self):
        item = replace(self.scope.products[0],branded_food=replace(self.scope.products[0].branded_food,ordinal=7))
        self.scope = replace(self.scope,products=(item,self.scope.products[1])); self.rebind()
        with self.assertRaisesRegex(RefreshError,'source-row-derivation-mismatch'): self.run_selected()

    def test_actual_row_must_match_independently_selected_body_pin(self):
        item = replace(self.scope.products[0],food=replace(self.scope.products[0].food,body_sha256='0'*64))
        self.scope = replace(self.scope,products=(item,self.scope.products[1])); self.rebind()
        with self.assertRaisesRegex(RefreshError,'source-row-derivation-mismatch'): self.run_selected()

    def test_database_identity_sidecars_and_actual_sqlite_connection_agreement(self):
        stale = replace(self.scope,database_identity=(0,0,*self.scope.database_identity[2:]))
        self.scope = stale; self.rebind()
        with self.assertRaisesRegex(RefreshError,'database-custody-changed'): self.run_selected()
        self.scope = replace(self.scope,database_identity=s._signature(self.path.stat())); self.rebind()
        (self.root/'source.sqlite-wal').write_bytes(b'not eligible immutable input')
        with self.assertRaisesRegex(RefreshError,'database-sidecar-present'): self.run_selected()
        (self.root/'source.sqlite-wal').unlink()
        alternate = self.root/'alternate.sqlite'
        with sqlite3.connect(alternate) as db: db.execute('CREATE TABLE different(x)')
        db.close(); real = sqlite3.connect; before = len(os.listdir('/proc/self/fd'))
        with patch.object(s.sqlite3,'connect',side_effect=lambda *a,**kw:real(alternate.as_uri()+'?mode=ro&immutable=1',uri=True)):
            with self.assertRaisesRegex(RefreshError,'database-custody-changed'): self.run_selected()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_unindexed_database_refuses_table_scan(self):
        self.path.unlink(); self.make_database(indexed=False)
        self.manifest = self.manifest_bytes()
        self.scope = replace(self.scope,database=Asset('source.sqlite',self.path.stat().st_size,
            hashlib.sha256(self.path.read_bytes()).hexdigest()),database_identity=s._signature(self.path.stat()),
            normalization_manifest=Asset('manifest.json',len(self.manifest),hashlib.sha256(self.manifest).hexdigest()))
        self.rebind()
        with self.assertRaisesRegex(RefreshError,'unbounded-source-query'): self.run_selected()

    def test_explicit_input_row_and_output_bounds(self):
        original = self.limits
        for name in ('max_input_bytes','max_row_bytes','max_source_row_bytes','max_record_bytes','max_output_bytes'):
            self.limits = replace(original,**{name:1}); self.rebind()
            with self.assertRaises(RefreshError): self.run_selected()
        with self.assertRaisesRegex(RefreshError,'explicit-limits-required'): self.run_selected(limits=None)

    def test_post_read_database_change_refuses_entire_result(self):
        real = s.ProductOriginEmitter.emit; emitted = []
        def changed(emitter,record):
            enriched = real(emitter,record); emitted.append(record['id'])
            if len(emitted) == len(self.records):
                with sqlite3.connect(self.path) as db:
                    db.execute('UPDATE raw SET body=? WHERE tab=? AND ordinal=?',('{"fdc_id":"10099"}','food',99))
                db.close()
            return enriched
        with patch.object(s.ProductOriginEmitter,'emit',changed):
            with self.assertRaisesRegex(RefreshError,'database-custody-changed'): self.run_selected()

    def test_no_source_write_or_fd_leak_on_success(self):
        before = len(os.listdir('/proc/self/fd')); signature = s._signature(self.path.stat())
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.run_selected()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
        self.assertEqual(s._signature(self.path.stat()),signature)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),digest)

    def test_no_full_database_hash_and_only_selected_ordinal_queries(self):
        real_read = Path.read_bytes; real_connect = sqlite3.connect; queries = []
        def read(path):
            self.assertNotEqual(path,self.path,'caller must not hash the full DB')
            return real_read(path)
        def connect(*args,**kwargs):
            db = real_connect(*args,**kwargs); db.set_trace_callback(queries.append); return db
        with patch.object(Path,'read_bytes',read),patch.object(s.sqlite3,'connect',side_effect=connect):
            result = self.run_selected()
        points = [q for q in queries if q.startswith('SELECT ordinal,identity,body')]
        self.assertEqual(len(points),4)
        self.assertTrue(all('ordinal=' in q and 'LIMIT 2' in q for q in points))
        self.assertFalse(any('COUNT(' in q.upper() or 'food_nutrient' in q for q in queries))
        self.assertFalse(result['fullDatabaseHashPerformed'])

    def test_partial_three_field_inventory_cannot_pass_as_complete(self):
        real = s.ProductOriginEmitter.emit
        def partial(emitter,record):
            result = real(emitter,record)
            result['provenance']['fieldOrigins'] = {k:v for k,v in result['provenance']['fieldOrigins'].items()
                if k in ('/data/ingredientsText','/data/nutritionId','/data/identifiers/1/value')}
            return result
        with patch.object(s.ProductOriginEmitter,'emit',partial):
            with self.assertRaisesRegex(RefreshError,'complete-origin-inventory-required'): self.run_selected()

    def test_concurrent_or_ambiguous_database_setup_refuses(self):
        with patch.object(s.threading,'active_count',return_value=2):
            with self.assertRaisesRegex(RefreshError,'serialized-database-setup-required'): self.run_selected()
        extra = []; real = sqlite3.connect; before = len(os.listdir('/proc/self/fd'))
        def ambiguous(*args,**kwargs):
            db = real(*args,**kwargs); db.execute('PRAGMA user_version').fetchone()
            extra.append(os.open(self.root/'extra',os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)); return db
        try:
            with patch.object(s.sqlite3,'connect',side_effect=ambiguous):
                with self.assertRaisesRegex(RefreshError,'database-descriptor-ambiguous'): self.run_selected()
        finally:
            for fd in extra: os.close(fd)
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_late_deadline_never_returns_partial_selected_records(self):
        real = s.ProductOriginEmitter.emit; now = [100.0]
        def expire(emitter,record):
            result = real(emitter,record); now[0] = 1000.0; return result
        before = len(os.listdir('/proc/self/fd'))
        with patch.object(s.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(s.ProductOriginEmitter,'emit',expire):
            with self.assertRaisesRegex(RefreshError,'duration-bound'): self.run_selected()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_sqlite_step_bound_refuses_before_return_and_closes_handles(self):
        self.limits = replace(self.limits,max_sqlite_steps=1); self.rebind()
        before = len(os.listdir('/proc/self/fd'))
        with self.assertRaisesRegex(sqlite3.OperationalError,'interrupted'): self.run_selected()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def index_fixture(self,columns):
        self.path.unlink(); self.make_database(indexed=False)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE INDEX fixture_index ON raw('+columns+')')
        db.close()
        self.manifest = self.manifest_bytes()
        self.scope = replace(self.scope,database=Asset('source.sqlite',self.path.stat().st_size,
            hashlib.sha256(self.path.read_bytes()).hexdigest()),database_identity=s._signature(self.path.stat()),
            normalization_manifest=Asset('manifest.json',len(self.manifest),hashlib.sha256(self.manifest).hexdigest()))
        self.rebind()

    def test_tab_only_search_index_refused_before_selected_body_fetch(self):
        self.index_fixture('tab')
        with sqlite3.connect(self.path) as db:
            plan = db.execute('EXPLAIN QUERY PLAN SELECT ordinal,identity,body FROM raw '
                              'WHERE tab=? AND ordinal=? LIMIT 2',('food',7)).fetchall()
        db.close()
        self.assertIn('(tab=?)',plan[0][3]); self.assertNotIn('ordinal=?',plan[0][3])
        with self.assertRaisesRegex(RefreshError,'composite-point-index-required'): self.run_selected()

    def test_composite_search_index_uses_both_equalities_and_preserves_origins(self):
        self.index_fixture('tab,ordinal')
        with sqlite3.connect(self.path) as db:
            plan = db.execute('EXPLAIN QUERY PLAN SELECT ordinal,identity,body FROM raw '
                              'WHERE tab=? AND ordinal=? LIMIT 2',('food',7)).fetchall()
        db.close()
        self.assertIn('(tab=? AND ordinal=?)',plan[0][3])
        result = self.run_selected(); self.assertEqual(result['measurements']['pointRowsRead'],4)
        for old,new in zip(self.records,result['records']):
            self.assertEqual(canonical(old['data']),canonical(new['data']))
            self.assertEqual(set(new['provenance']['fieldOrigins']),set(datum_pointers(new['data'])))


if __name__ == '__main__': unittest.main()
