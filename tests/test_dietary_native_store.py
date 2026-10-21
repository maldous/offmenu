"""Generated fixtures only: never open a retained corpus or source database."""
from dataclasses import replace
from contextlib import closing
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import dietary_native_store as s
from offmenu.refresh.acceptance import Asset, SourceContract, contract_fingerprint, fingerprint
from offmenu.refresh.core import canonical, RefreshError


class DietaryNativeStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.root.chmod(0o700)
        self.target = self.root/'dietary.sqlite'
        self.limits = s.DietaryLimits(4*1024**2, 1000, 1024**2, 1000, 1000, 1000,
                                     8*1024**2, 16*1024**2, 30, 2)

    def entry(self, **changes):
        return dict(value=1.25, unit='mg', sourceAmount='01.2500', sourceUnit='MG',
                    sourceName='Vitamin Ω', sourceNutrientId='007', sourceRowId='0001',
                    rawFields={'amount':'01.2500','unused':None},
                    basis={'amount':100,'unit':'g','state':'as-described'}, method='source', **changes)

    def row(self, key='1', kind='nutrientProfile', data=None):
        return {'id':'usda-files:'+kind+':'+key,'schemaVersion':'1.0','kind':kind,
                'provenance':{'sourceId':'usda-files','releaseId':'fixture-release',
                              'recordId':key,'fetchedAt':None,'sourceRow':{'unknown':None},
                              'visibility':'private-candidate','transform':'fixture/1'},
                'data': data if data is not None else {'foodName':'Öat','identifiers':[],
                    'basis':{'amount':100,'unit':'g','state':'as-described'},
                    'nutrients':{'vitamin/~Ω':self.entry()}}}

    def spec(self, rows=None, raw=None, profiles=None, products=None):
        rows = rows if rows is not None else [self.row(), self.row(kind='product')]
        raw = raw if raw is not None else b''.join(canonical([r]) for r in rows)
        path = self.root/'candidate.jsonl'; path.write_bytes(raw)
        profiles = sum(r.get('kind')=='nutrientProfile' for r in rows) if profiles is None else profiles
        products = sum(r.get('kind')=='product' for r in rows) if products is None else products
        assets = (Asset('original.zip',1,'a'*64),Asset('rights.json',1,'b'*64),Asset('scope.json',1,'c'*64))
        schemas = {'product':{'type':'object'},'nutrientProfile':{'type':'object'}}
        contract = SourceContract('usda-files','fixture-release','fixture-native',None,assets,
            profiles+products,'d'*64,schemas,fingerprint(schemas),lambda _:(),'e'*64,assets[1],assets[2],
            frozenset(('retain','parse','transform')), fixture=True, acquisition_clock_status='unknown-retained')
        q = {'schemaVersion':'offmenu-source-qualification/1','sourceId':contract.source_id,
             'releaseId':contract.release_id,'scopeId':contract.scope_id,'outputScope':'native',
             'outputVisibility':'private','fixture':True,'normalizedRecords':profiles+products,
             'candidateSha256':hashlib.sha256(raw).hexdigest(),'qualified':True,'status':'qualified',
             'errors':[],'contractSha256':contract_fingerprint(contract)}
        q['qualificationSha256'] = fingerprint(q)
        return s.DietaryInput(str(path),len(raw),s._identity(path.stat()),contract,q,
            q['qualificationSha256'],profiles,products,'f'*64,'0'*64)

    def build(self, spec=None, **changes):
        spec = spec or self.spec()
        args = dict(limits=self.limits,load_id='fixture-load',
            input_manifest_sha256=hashlib.sha256(canonical(s.prepare_dietary_manifest(spec))).hexdigest(),
            selection_receipt_sha256='1'*64)
        args.update(changes)
        return s.build_dietary_database(spec,self.target,**args)

    def query(self, sql):
        with closing(sqlite3.connect(self.target)) as db: return db.execute(sql).fetchall()

    def test_exact_schema_and_all_packet_accounting(self):
        self.assertEqual(hashlib.sha256(s.DDL.encode()).hexdigest(), s.SCHEMA_SHA256)
        result = self.build()
        self.assertTrue(result['loadComplete']); self.assertFalse(result['accepted'])
        self.assertFalse(result['goldAdmitted']); self.assertFalse(result['countryComplete'])
        self.assertFalse(result['runtimeOrResourcesAdmitted'])
        self.assertEqual(result['counts'],dict(dietary_packet_audit=2,native_nutrient_profile=1,
                                              native_nutrient_observation=1,dietary_exception=0))
        self.assertEqual(result['summary']['observationDispositions'],dict(stored=1,unresolved=0,quarantined=0))
        self.assertEqual(self.query('SELECT state,expected_packets,read_packets,unread_packets,observation_entries FROM dietary_load'),
                         [('completed',2,2,0,1)])
        self.assertEqual(self.query('SELECT disposition,count(*) FROM dietary_packet_audit GROUP BY disposition'),
                         [('other-kind',1),('profile-stored',1)])
        self.assertEqual(self.target.stat().st_mode & 0o777,0o600)
        self.assertEqual(hashlib.sha256(self.target.read_bytes()).hexdigest(),result['databaseSha256'])
        self.assertEqual(self.query('PRAGMA foreign_key_check'),[])

    def test_native_packet_original_bytes_lexemes_raw_fields_and_null_links(self):
        row = self.row(); raw = (json.dumps([row],ensure_ascii=False,indent=None)+'  \n').encode()
        self.build(self.spec([row],raw=raw))
        doc,digest,language,lang_state,food,ingredient,status = self.query(
            'SELECT native_packet_json,document_sha256,original_language,language_state,canonical_food_id,canonical_ingredient_id,semantic_link_status FROM native_nutrient_profile')[0]
        self.assertEqual(doc.encode(),raw); self.assertEqual(digest,hashlib.sha256(raw).hexdigest())
        self.assertEqual((language,lang_state,food,ingredient,status),(None,'unknown',None,None,'pending'))
        self.assertEqual(json.loads(doc)[0]['data']['nutrients']['vitamin/~Ω']['rawFields'],row['data']['nutrients']['vitamin/~Ω']['rawFields'])
        got = self.query('SELECT source_amount_json,source_unit_json,unit_json,method_json,entry_pointer,canonical_nutrient_id,canonical_unit_id,normalization_status FROM native_nutrient_observation')[0]
        self.assertEqual(got,('"01.2500"','"MG"','"mg"','"source"','/0/data/nutrients/vitamin~1~0Ω',None,None,'pending'))

    def test_explicit_language_preserved(self):
        row=self.row(); row['data']['language']='de-DE'
        self.build(self.spec([row])); self.assertEqual(self.query('SELECT original_language,language_state FROM native_nutrient_profile'),[('de-DE','source-explicit')])

    def test_observation_order_duplicates_source_keys_and_stable_ids(self):
        row=self.row(); row['data']['nutrients']={'z':self.entry(),'z:observation:2':self.entry(),'a':self.entry()}
        spec=self.spec([row]); self.build(spec)
        got=self.query('SELECT observation_id,entry_ordinal,original_entry_key FROM native_nutrient_observation ORDER BY entry_ordinal')
        self.assertEqual([r[2] for r in got],['a','z','z:observation:2']) # canonical fixture sorted; decoded order retained
        other=self.root/'other';other.mkdir(mode=0o700); target=self.target;self.target=other/'second.sqlite'
        self.build(spec); self.assertEqual(self.query('SELECT observation_id,entry_ordinal,original_entry_key FROM native_nutrient_observation ORDER BY entry_ordinal'),got)
        self.target=target

    def test_unsorted_input_entry_order_preserved(self):
        row=self.row(); row['data']['nutrients']={'z':self.entry(),'a':self.entry()}
        self.build(self.spec([row],raw=(json.dumps([row])+'\n').encode()))
        self.assertEqual(self.query('SELECT original_entry_key FROM native_nutrient_observation ORDER BY entry_ordinal'),[('z',),('a',)])

    def test_missing_null_invalid_empty_nutrients_profiles_retained(self):
        rows=[]
        for i,v in enumerate(('missing',None,[],{})):
            row=self.row(str(i)); row['data'].pop('nutrients')
            if v!='missing':row['data']['nutrients']=v
            rows.append(row)
        result=self.build(self.spec(rows))
        self.assertEqual(result['summary']['nutrientsStates'],dict(missing=1,null=1,invalid=1,empty=1))
        self.assertEqual(result['counts']['native_nutrient_profile'],4)
        self.assertEqual(result['counts']['native_nutrient_observation'],0)
        self.assertEqual(result['counts']['dietary_exception'],3)

    def test_missing_null_invalid_entry_fields_never_zero_filled(self):
        row=self.row(); e=self.entry();e.pop('sourceAmount');e['value']=None;e['unit']=False;e['basis']=[]
        row['data']['nutrients']={'one':e,'not-object':None}
        result=self.build(self.spec([row]));self.assertEqual(result['counts']['native_nutrient_observation'],2)
        values=self.query("SELECT source_amount_json,interpreted_value_json,unit_json,field_states_json,source_disposition FROM native_nutrient_observation WHERE original_entry_key='one'")[0]
        self.assertEqual(values[:3],(None,'null','false'))
        states=json.loads(values[3]);self.assertEqual((states['sourceAmount'],states['value'],states['unit'],states['basis']),('missing','null','invalid','invalid'))
        self.assertEqual(values[4],'quarantined')
        self.assertEqual(result['summary']['observationDispositions']['quarantined'],2)

    def test_null_value_is_unresolved_not_zero(self):
        row=self.row();row['data']['nutrients']['vitamin/~Ω']['value']=None
        self.build(self.spec([row]));self.assertEqual(self.query('SELECT interpreted_value_json,source_disposition FROM native_nutrient_observation'),[('null','unresolved')])

    def test_invalid_profile_data_preserved(self):
        row=self.row();row['data']=[]
        self.build(self.spec([row]));self.assertEqual(self.query('SELECT observed_entry_count,nutrients_state FROM native_nutrient_profile'),[(0,'missing')])
        self.assertEqual(json.loads(self.query('SELECT native_packet_json FROM native_nutrient_profile')[0][0])[0]['data'],[])

    def test_exact_decimal_large_exponent_and_negative_zero(self):
        row=self.row(); row['data']['nutrients']={'precise':self.entry(),'big':self.entry(),'negative':self.entry()}
        raw=(json.dumps([row])+'\n').encode().replace(b'"value": 1.25',b'"value": 0.12345678901234567890123456789',1).replace(b'"value": 1.25',b'"value": 1e400',1).replace(b'"value": 1.25',b'"value": -0.0',1)
        self.build(self.spec([row],raw=raw))
        values=dict(self.query('SELECT original_entry_key,interpreted_value_json FROM native_nutrient_observation'))
        self.assertEqual(values,dict(precise='0.12345678901234567890123456789',big='1E+400',negative='-0.0'))
        self.assertEqual(Decimal(values['big']),Decimal('1e400'))

    def test_single_candidate_open_no_preliminary_hash(self):
        spec=self.spec();opened=[];original=os.open
        def observe(path,*a,**kw):
            if str(path)==spec.candidate:opened.append(str(path))
            return original(path,*a,**kw)
        with patch.object(s.os,'open',side_effect=observe):self.build(spec)
        self.assertEqual(opened,[spec.candidate])

    def test_wrong_manifest_rejected_before_body_read_or_output(self):
        spec=self.spec()
        with patch.object(s.os,'open',side_effect=AssertionError('no open')):
            with self.assertRaisesRegex(RefreshError,'selected-manifest'):self.build(spec,input_manifest_sha256='0'*64)
        self.assertFalse(self.target.exists())

    def test_tampered_qualification_and_held_contract_fail_before_body(self):
        spec=self.spec();q=dict(spec.qualification,qualified=False)
        for bad in (replace(spec,qualification=q),replace(spec,contract=replace(spec.contract,holds=('fixture-hold',)))):
            with self.subTest(spec=bad.qualification.get('qualified')):
                with self.assertRaises(RefreshError):self.build(bad)
        self.assertFalse(self.target.exists())

    def test_candidate_identity_mismatch_and_symlink_rejected(self):
        spec=self.spec();identity=tuple([*spec.identity[:1],spec.identity[1]+1,*spec.identity[2:]])
        with self.assertRaisesRegex(RefreshError,'input-custody'):self.build(replace(spec,identity=identity))
        link=self.root/'link.jsonl';link.symlink_to(spec.candidate)
        with self.assertRaises(RefreshError):self.build(replace(spec,candidate=str(link)))
        self.assertFalse(self.target.exists())

    def test_hash_mismatch_retains_incomplete_checkpoint(self):
        spec=self.spec();q=dict(spec.qualification,candidateSha256='9'*64);q.pop('qualificationSha256');q['qualificationSha256']=fingerprint(q)
        with self.assertRaisesRegex(RefreshError,'input-hash') as caught:self.build(replace(spec,qualification=q,qualification_sha256=q['qualificationSha256']))
        retained=caught.exception.dietary_retained_state
        self.assertFalse(self.target.exists());self.assertFalse(retained['completeReceiptReturned'])
        with closing(sqlite3.connect(Path(retained['stage'])/'data.sqlite')) as db:
            self.assertEqual(db.execute('SELECT state,read_packets,unread_packets FROM dietary_load').fetchone(),('incomplete',2,0))

    def test_malformed_duplicate_key_nonfinite_and_wrong_source_are_audited(self):
        base=self.row(kind='product')
        raw_candidates=[b'[{}]\n',b'[{"id":1,"id":2}]\n',b'[NaN]\n',b'[Infinity]\n']
        wrong=self.row();wrong['provenance']['sourceId']='off';raw_candidates.append(canonical([wrong]))
        for i,bad in enumerate(raw_candidates):
            with self.subTest(i=i):
                spec=self.spec([self.row(),base],raw=bad+canonical([base]))
                with self.assertRaisesRegex(RefreshError,'partition-incomplete') as caught:self.build(spec,limits=replace(self.limits,commit_every_packets=1))
                with closing(sqlite3.connect(Path(caught.exception.dietary_retained_state['stage'])/'data.sqlite')) as db:
                    self.assertEqual(db.execute('SELECT disposition FROM dietary_packet_audit ORDER BY packet_ordinal').fetchall(),[('quarantined',),('other-kind',)])
                    self.assertEqual(db.execute('SELECT count(*) FROM dietary_exception').fetchone()[0],1)
        self.assertFalse(self.target.exists())

    def test_missing_final_lf_and_extra_packets_fail_not_truncate(self):
        for raw in (canonical([self.row()]).rstrip(b'\n'),canonical([self.row()])*2):
            spec=self.spec([self.row()],raw=raw)
            with self.assertRaisesRegex(RefreshError,'line-or-count-bound'):self.build(spec)
        self.assertFalse(self.target.exists())

    def test_short_scope_has_unread_count(self):
        spec=self.spec([self.row(),self.row(kind='product')],raw=canonical([self.row()]))
        with self.assertRaisesRegex(RefreshError,'partition-incomplete') as caught:self.build(spec,limits=replace(self.limits,commit_every_packets=1))
        with closing(sqlite3.connect(Path(caught.exception.dietary_retained_state['stage'])/'data.sqlite')) as db:
            self.assertEqual(db.execute('SELECT state,read_packets,unread_packets FROM dietary_load').fetchone(),('incomplete',1,1))

    def test_exception_cap_rolls_back_whole_current_packet(self):
        product=self.row(kind='product');row=self.row();row['data']['nutrients']={'a':{},'b':{}}
        with self.assertRaisesRegex(RefreshError,'exception-bound') as caught:
            self.build(self.spec([product,row]),limits=replace(self.limits,max_exceptions=1,commit_every_packets=1))
        with closing(sqlite3.connect(Path(caught.exception.dietary_retained_state['stage'])/'data.sqlite')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM native_nutrient_profile').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM native_nutrient_observation').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT state,read_packets,unread_packets FROM dietary_load').fetchone(),('incomplete',1,1))

    def test_entry_total_line_and_storage_bounds_fail_closed(self):
        row=self.row();row['data']['nutrients']={'a':self.entry(),'b':self.entry()}
        for limits in (replace(self.limits,max_entries_per_profile=1),replace(self.limits,max_observations=1),
                       replace(self.limits,max_line_bytes=100),replace(self.limits,max_database_bytes=4096),
                       replace(self.limits,max_storage_bytes=4096)):
            with self.subTest(limits=limits):
                with self.assertRaises((RefreshError,sqlite3.Error)):self.build(self.spec([row]),limits=limits)
                self.assertFalse(self.target.exists())

    def test_existing_destination_preserved_and_no_overwrite_race(self):
        spec=self.spec();self.target.write_bytes(b'KEEP')
        with self.assertRaisesRegex(RefreshError,'destination-exists'):self.build(spec)
        self.assertEqual(self.target.read_bytes(),b'KEEP');self.target.unlink()
        original=s._rename_noreplace
        def race(*args):
            self.target.write_bytes(b'RACER');return original(*args)
        with patch.object(s,'_rename_noreplace',side_effect=race):
            with self.assertRaises(Exception):self.build(spec)
        self.assertEqual(self.target.read_bytes(),b'RACER')

    def test_input_change_during_same_fd_pass_fails(self):
        spec=self.spec();original=s._packet;changed=[False]
        def mutate(*args):
            original(*args)
            if not changed[0]:
                path=Path(spec.candidate);raw=path.read_bytes();path.write_bytes(raw);changed[0]=True
        with patch.object(s,'_packet',side_effect=mutate):
            with self.assertRaisesRegex(RefreshError,'input-custody'):self.build(spec)
        self.assertFalse(self.target.exists())

    def test_deadline_never_returns_completed_target(self):
        spec=self.spec();clock=iter([0.0]+[100.0]*10000)
        with patch.object(s.time,'monotonic',side_effect=lambda:next(clock)):
            with self.assertRaises((RefreshError,sqlite3.Error)) as caught:
                self.build(spec,limits=replace(self.limits,max_seconds=1))
        self.assertFalse(self.target.exists())
        self.assertFalse(caught.exception.dietary_retained_state['completeReceiptReturned'])

    def test_progress_checkpoints_do_not_scan_growing_tables_per_packet(self):
        spec=self.spec([self.row(str(i)) for i in range(40)])
        statements=[];original=s.sqlite3.connect
        def traced(*a,**kw):
            db=original(*a,**kw);db.set_trace_callback(statements.append);return db
        with patch.object(s.sqlite3,'connect',side_effect=traced):
            self.build(spec,limits=replace(self.limits,commit_every_packets=1))
        self.assertLess(sum('SELECT count(*) FROM' in q for q in statements),20)


if __name__=='__main__': unittest.main()
