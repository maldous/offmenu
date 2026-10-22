"""Synthetic SQLite contract tests, not deployed D1/API/food-safety acceptance."""
import json
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / 'cloud/migrations/20261022-household-domain-v1.sql'
BINDINGS = json.loads((ROOT / 'docs/schema/household-envelope-bindings-v1.json').read_text())

class HouseholdSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript((ROOT / 'cloud/schema.sql').read_text())
        self.db.execute("INSERT INTO user_state VALUES('legacy',4,'{\"preserve\":true}','old')")
        self.db.execute("INSERT INTO provider_connections VALUES('legacy','provider','label','legacy-sealed','old')")
        self.db.executescript((ROOT / 'cloud/migrations/20261022-byoc-security-v1.sql').read_text())
        self.db.executescript(MIGRATION.read_text())
        self.seq = 0
        for k,u in [('k1','u1'),('k2','u2')]:
            self.db.execute('INSERT INTO kitchens VALUES(?,?,1,?,?)',(k,k,'{}','now'))
            self.db.execute('INSERT INTO kitchen_members VALUES(?,?,?)',(k,u,'owner'))
            self.put('sec_key_references',id='key-'+u,owner_user_id=u,custody='server-envelope',external_key_ref='test-only-'+u,key_version=1,algorithm='AES-256-GCM',status='active',created_at=1,expires_at=9999999999)
    def tearDown(self): self.db.close()
    def put(self, table, **values):
        columns=','.join(values); params=','.join('?' for _ in values)
        return self.db.execute(f'INSERT INTO {table}({columns}) VALUES({params})',tuple(values.values()))
    def envelope(self,table,ident,k='k1',u='u1'):
        self.seq+=1; eid=f'e{self.seq}'; b=BINDINGS[table]
        self.put('sec_envelopes',id=eid,owner_user_id=u,kitchen_id=k if b['scope']=='kitchen' else None,object_type=table,object_id=ident,purpose=b['purpose'],provider_id='',format_version=1,custody='server-envelope',key_ref_id='key-'+u,key_version=1,algorithm='AES-256-GCM',nonce=self.seq.to_bytes(12,'big'),ciphertext=b'SYNTHETIC-NOT-CRYPTO',created_at=1,retain_until=9999999999,revision=1)
        return eid
    def item(self,k='k1',u='u1',ident='item'):
        self.put('stock_items',kitchen_id=k,id=ident,owner_user_id=u,envelope_id=self.envelope('stock_items',ident,k,u),kind='product',identity_status='unresolved',revision=1,created_at='now')
    def location(self,k='k1',u='u1',ident='loc'):
        self.put('stock_locations',kitchen_id=k,id=ident,owner_user_id=u,envelope_id=self.envelope('stock_locations',ident,k,u),storage_kind='ambient',revision=1)
    def lot(self,k='k1',u='u1',ident='lot',unit='g',**extra):
        self.put('stock_lots',kitchen_id=k,id=ident,item_id='item',location_id='loc',owner_user_id=u,envelope_id=self.envelope('stock_lots',ident,k,u),unit_id=unit,amount_basis='measured',review_status='reviewed',physical_state='unopened',revision=1,created_at='now',**extra)
    def stock(self): self.item(); self.location(); self.lot()
    def command(self,ident='cmd',key=None):
        self.put('stock_commands',kitchen_id='k1',id=ident,actor_user_id='u1',idempotency_key=key or ident,request_hmac='synthetic-hmac',kind='adjust',created_at='now')
    def movement(self,ident,delta,kind='acquire',unit='g',**extra):
        self.put('stock_movements',kitchen_id='k1',id=ident,command_id='cmd',lot_id='lot',unit_id=unit,delta_micros=delta,kind=kind,occurred_at='now',**extra)
    def balance(self): return self.db.execute("SELECT quantity_micros FROM stock_lot_balances WHERE kitchen_id='k1' AND lot_id='lot'").fetchone()[0]
    def meal(self):
        self.put('household_meal_plans',kitchen_id='k1',id='plan',owner_user_id='u1',envelope_id=self.envelope('household_meal_plans','plan'),status='active',revision=1,created_at='now')
        self.put('household_plan_meals',kitchen_id='k1',plan_id='plan',id='meal',owner_user_id='u1',envelope_id=self.envelope('household_plan_meals','meal'),planned_date='2026-10-22',time_zone='UTC',meal_slot='Dinner',servings_micros=2000000,status='planned',revision=1)
    def receipt(self,ident='receipt',digest='synthetic-digest'):
        self.put('stock_receipts',kitchen_id='k1',id=ident,owner_user_id='u1',envelope_id=self.envelope('stock_receipts',ident),mode='receipt_ocr',status='needs_review',source_id='manual',content_digest=digest,started_at='now',retain_until=9999999999,revision=1)
    def test_legacy_rows_unchanged_and_new_private_domain_empty(self):
        self.assertEqual(self.db.execute('SELECT * FROM user_state').fetchall(), [('legacy',4,'{"preserve":true}','old')])
        self.assertEqual(self.db.execute('SELECT sealed FROM provider_connections').fetchone()[0], 'legacy-sealed')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM household_profiles').fetchone()[0],0)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(self.db.execute('SELECT version FROM household_schema_versions').fetchone()[0],'offmenu-household-domain/1')
    def test_migration_reapplication_fails_without_rewriting(self):
        with self.assertRaises(sqlite3.OperationalError): self.db.executescript(MIGRATION.read_text())
        self.assertEqual(self.db.execute('SELECT revision FROM user_state').fetchone()[0],4)
    def test_cross_tenant_lot_and_envelope_rejected(self):
        self.item('k2','u2'); self.location()
        with self.assertRaises(sqlite3.IntegrityError): self.lot()
        self.item()
        other=self.envelope('stock_lots','lot','k2','u2')
        with self.assertRaises(sqlite3.IntegrityError):
            self.put('stock_lots',kitchen_id='k1',id='lot',item_id='item',location_id='loc',owner_user_id='u1',envelope_id=other,unit_id='g',amount_basis='unknown',review_status='needs_review',physical_state='unknown',revision=1,created_at='now')
    def test_private_profile_rejects_shared_envelope_and_wrong_object(self):
        e=self.envelope('household_profiles','p')
        self.put('household_profiles',owner_user_id='u1',id='p',envelope_id=e,status='active',created_at='now',updated_at='now')
        with self.assertRaises(sqlite3.IntegrityError): self.put('household_profiles',owner_user_id='u2',id='p',envelope_id=e,status='active',created_at='now',updated_at='now')
        with self.assertRaises(sqlite3.IntegrityError): self.put('household_profiles',owner_user_id='u1',id='q',envelope_id=e,status='active',created_at='now',updated_at='now')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM household_profile_grants').fetchone()[0],0)
    def test_ledger_atomic_arithmetic_units_bounds_and_undo(self):
        self.stock(); self.command(); self.movement('a',5000000); self.movement('b',-2000000,'consume')
        self.assertEqual(self.balance(),3000000)
        for ident,delta,kind,unit in [('over',-4000000,'waste','g'),('float',0.1,'acquire','g'),('unit',1,'acquire','ml'),('sign',-1,'acquire','g')]:
            with self.subTest(ident=ident),self.assertRaises(sqlite3.IntegrityError): self.movement(ident,delta,kind,unit)
        self.movement('undo',2000000,'undo',reversal_of='b');self.assertEqual(self.balance(),5000000)
        with self.assertRaises(sqlite3.IntegrityError):self.movement('undo2',2000000,'undo',reversal_of='b')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_movements SET delta_micros=7 WHERE id='a'")
    def test_retry_key_cannot_double_apply(self):
        self.command(key='retry')
        with self.assertRaises(sqlite3.IntegrityError):self.command('other',key='retry')
    def test_same_lot_two_home_reservation_and_balance_guard(self):
        self.stock();self.command();self.movement('a',5000000);self.meal()
        self.put('stock_reservations',kitchen_id='k1',id='r',lot_id='lot',meal_id='meal',unit_id='g',quantity_micros=4000000,status='active',needed_on='2026-10-22',revision=1)
        with self.assertRaises(sqlite3.IntegrityError):self.put('stock_reservations',kitchen_id='k1',id='r2',lot_id='lot',meal_id='meal',unit_id='g',quantity_micros=2000000,status='active',needed_on='2026-10-22',revision=1)
        with self.assertRaises(sqlite3.IntegrityError):self.movement('b',-2000000,'consume')
        self.db.execute("UPDATE stock_reservations SET status='consumed' WHERE id='r'")
        self.movement('b',-2000000,'consume');self.assertEqual(self.balance(),3000000)
    def test_shared_ownership_sum_and_cross_kitchen_member(self):
        self.stock();self.db.execute("INSERT INTO kitchen_members VALUES('k1','u3','editor')")
        self.put('stock_lot_ownership',kitchen_id='k1',lot_id='lot',user_id='u1',share_ppm=600000)
        with self.assertRaises(sqlite3.IntegrityError):self.put('stock_lot_ownership',kitchen_id='k1',lot_id='lot',user_id='u3',share_ppm=600000)
        with self.assertRaises(sqlite3.IntegrityError):self.put('stock_lot_ownership',kitchen_id='k1',lot_id='lot',user_id='u2',share_ppm=100000)
    def test_receipt_review_all_lines_and_tenant_dedup(self):
        self.receipt()
        with self.assertRaises(sqlite3.IntegrityError):self.receipt('duplicate')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_receipts SET status='committed',reviewed_at='now' WHERE id='receipt'")
        self.put('stock_receipt_lines',kitchen_id='k1',receipt_id='receipt',id='line',ordinal=0,owner_user_id='u1',envelope_id=self.envelope('stock_receipt_lines',json.dumps(['receipt','line'],separators=(',',':'))),review_decision='pending')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_receipts SET status='reviewed',reviewed_at='now' WHERE id='receipt'")
        self.db.execute("UPDATE stock_receipt_lines SET review_decision='exclude' WHERE id='line'")
        self.db.execute("UPDATE stock_receipts SET status='reviewed',reviewed_at='now' WHERE id='receipt'")
    def test_dates_remain_distinct_unknown_is_not_zero(self):
        self.item();self.location();self.lot(use_by='2026-10-23',best_before='2026-10-24',review_on='2026-10-22')
        self.assertEqual(self.db.execute('SELECT use_by,best_before,review_on,produced_on FROM stock_lots').fetchone(),('2026-10-23','2026-10-24','2026-10-22',None))
        self.assertEqual(self.balance(),0)
    def test_waste_measured_cannot_exceed_confirmed_discard(self):
        self.stock();self.command();self.movement('a',5000000);self.movement('w',-2000000,'waste')
        args=dict(kitchen_id='k1',id='obs',movement_id='w',owner_user_id='u1',envelope_id=self.envelope('stock_waste_observations','obs'),measurement_status='measured',quantity_micros=3000000,unit_id='g',observed_at='now')
        with self.assertRaises(sqlite3.IntegrityError):self.put('stock_waste_observations',**args)
        args.update(quantity_micros=1000000);self.put('stock_waste_observations',**args)
    def test_transaction_rollback_preserves_quantities(self):
        self.stock();self.command();self.movement('a',5000000);self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.movement('good',-1000000,'consume')
                self.movement('bad',-5000000,'consume')
        self.assertEqual(self.balance(),5000000)
    def test_profile_grant_needs_exact_owner_object_and_audience_consent(self):
        self.put('household_profiles',owner_user_id='u1',id='p',envelope_id=self.envelope('household_profiles','p'),status='active',created_at='now',updated_at='now')
        self.put('sec_consents',id='consent',owner_user_id='u1',actor_user_id='u1',object_type='household_profile',object_id='different-profile',purpose='profile_share',grantee_user_id='u1',audience_kitchen_id='k1',notice_version='1',choice='granted',revision=1,valid_from=1,expires_at=9999999999,updated_at=1)
        row=dict(owner_user_id='u1',profile_id='p',id='grant',kitchen_id='k1',grantee_user_id='u1',consent_id='consent',purpose='meal-planning',expires_at=9999999999)
        with self.assertRaises(sqlite3.IntegrityError):self.put('household_profile_grants',**row)
        self.put('sec_consents',id='right-consent',owner_user_id='u1',actor_user_id='u1',object_type='household_profile',object_id='p',purpose='profile_share',grantee_user_id='u1',audience_kitchen_id='k1',notice_version='1',choice='granted',revision=1,valid_from=1,expires_at=9999999999,updated_at=1)
        row['consent_id']='right-consent'
        self.put('household_profile_grants',**row)
    def test_private_profile_shared_envelope_is_rejected(self):
        self.put('sec_envelopes',id='bad',owner_user_id='u1',kitchen_id='k1',object_type='household_profiles',object_id='p',purpose='household-profile/1',provider_id='',format_version=1,custody='server-envelope',key_ref_id='key-u1',key_version=1,algorithm='AES-256-GCM',nonce=b'x'*12,ciphertext=b'SYNTHETIC-NOT-CRYPTO',created_at=1,retain_until=9999999999,revision=1)
        with self.assertRaises(sqlite3.IntegrityError):self.put('household_profiles',owner_user_id='u1',id='p',envelope_id='bad',status='active',created_at='now',updated_at='now')
    def test_final_receipt_cannot_be_reopened_or_lines_changed(self):
        self.receipt()
        self.put('stock_receipt_lines',kitchen_id='k1',receipt_id='receipt',id='line',ordinal=0,owner_user_id='u1',envelope_id=self.envelope('stock_receipt_lines',json.dumps(['receipt','line'],separators=(',',':'))),review_decision='exclude')
        self.db.execute("UPDATE stock_receipts SET status='reviewed',reviewed_at='now' WHERE id='receipt'")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_receipt_lines SET review_decision='include' WHERE id='line'")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_receipts SET status='draft' WHERE id='receipt'")
    def test_unknown_quantity_and_waste_remain_null(self):
        self.stock();self.command();self.movement('a',5000000);self.movement('w',-1000000,'waste')
        self.put('stock_waste_observations',kitchen_id='k1',id='obs',movement_id='w',owner_user_id='u1',envelope_id=self.envelope('stock_waste_observations','obs'),measurement_status='unknown',quantity_micros=None,unit_id=None,observed_at='now')
        self.assertEqual(self.db.execute('SELECT quantity_micros,unit_id FROM stock_waste_observations').fetchone(),(None,None))
    def test_offline_preparer_is_repeatable_without_files(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('household_prep',ROOT/'scripts/prepare_household_schema.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        a=module.prepare();b=module.prepare()
        self.assertEqual(a,b)
        self.assertEqual(a['schema_status'],'schema_prepared_app_wiring_pending')
        self.assertEqual(a['domain_table_count'],31)
        self.assertEqual(a['private_rows'],0)
        self.assertFalse(a['artifact_written'])
        self.assertFalse(a['existing_database_opened'])
    def test_offline_preparer_refuses_existing_output_directory(self):
        import importlib.util,tempfile
        spec=importlib.util.spec_from_file_location('household_prep',ROOT/'scripts/prepare_household_schema.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):module.prepare(d)
            out=Path(d)/'fresh';report=module.prepare(out)
            before=(out/'household-empty-template.sqlite3').read_bytes()
            with self.assertRaises(FileExistsError):module.prepare(out)
            self.assertEqual((out/'household-empty-template.sqlite3').read_bytes(),before)
            self.assertTrue(report['artifact_written'])
    def test_all_known_requirement_ids_reconciled_without_runtime_claims(self):
        matrix=json.loads((ROOT/'docs/schema/household-requirements-matrix-v1.json').read_text())
        self.assertEqual(matrix['register_count'],105)
        self.assertEqual(len({x['id'] for x in matrix['requirements']}),105)
        self.assertTrue(all(not x['production_implemented_by_this_batch'] for x in matrix['requirements']))
    def test_composite_receipt_envelope_identity_is_injective(self):
        self.receipt('a/b','digest1');self.receipt('a','digest2')
        e=self.envelope('stock_receipt_lines',json.dumps(['a/b','c'],separators=(',',':')))
        self.put('stock_receipt_lines',kitchen_id='k1',receipt_id='a/b',id='c',ordinal=0,owner_user_id='u1',envelope_id=e,review_decision='pending')
        with self.assertRaises(sqlite3.IntegrityError):self.put('stock_receipt_lines',kitchen_id='k1',receipt_id='a',id='b/c',ordinal=0,owner_user_id='u1',envelope_id=e,review_decision='pending')
    def test_private_attendance_envelope_binds_kitchen_as_well_as_meal_profile(self):
        self.meal()
        self.put('household_meal_plans',kitchen_id='k2',id='plan',owner_user_id='u2',envelope_id=self.envelope('household_meal_plans','plan','k2','u2'),status='active',revision=1,created_at='now')
        self.put('household_plan_meals',kitchen_id='k2',plan_id='plan',id='meal',owner_user_id='u2',envelope_id=self.envelope('household_plan_meals','meal','k2','u2'),planned_date='2026-10-22',time_zone='UTC',meal_slot='Dinner',servings_micros=1000000,status='planned',revision=1)
        self.put('household_profiles',owner_user_id='u1',id='p',envelope_id=self.envelope('household_profiles','p'),status='active',created_at='now',updated_at='now')
        self.put('sec_consents',id='c',owner_user_id='u1',actor_user_id='u1',object_type='household_profile',object_id='p',purpose='private_use',notice_version='1',choice='granted',revision=1,valid_from=1,expires_at=9999999999,updated_at=1)
        e=self.envelope('household_meal_attendance',json.dumps(['k1','meal','p'],separators=(',',':')))
        self.put('household_meal_attendance',owner_user_id='u1',profile_id='p',kitchen_id='k1',meal_id='meal',envelope_id=e,consent_id='c')
        with self.assertRaises(sqlite3.IntegrityError):self.put('household_meal_attendance',owner_user_id='u1',profile_id='p',kitchen_id='k2',meal_id='meal',envelope_id=e,consent_id='c')
    def test_ownership_update_cannot_move_identity_around_share_guard(self):
        self.stock();self.lot(ident='lot2');self.db.execute("INSERT INTO kitchen_members VALUES('k1','u3','editor')")
        self.put('stock_lot_ownership',kitchen_id='k1',lot_id='lot',user_id='u1',share_ppm=600000)
        self.put('stock_lot_ownership',kitchen_id='k1',lot_id='lot2',user_id='u1',share_ppm=600000)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_lot_ownership SET lot_id='lot2',user_id='u3' WHERE lot_id='lot'")
    def test_waste_observation_cannot_be_updated_past_discard_bound(self):
        self.stock();self.command();self.movement('a',5000000);self.movement('w',-2000000,'waste')
        self.put('stock_waste_observations',kitchen_id='k1',id='obs',movement_id='w',owner_user_id='u1',envelope_id=self.envelope('stock_waste_observations','obs'),measurement_status='measured',quantity_micros=1000000,unit_id='g',observed_at='now')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_waste_observations SET quantity_micros=3000000 WHERE id='obs'")
    def test_reservation_update_cannot_move_scoped_identity_around_cap(self):
        self.stock();self.command();self.movement('a',5000000);self.meal()
        self.put('stock_reservations',kitchen_id='k1',id='r',lot_id='lot',meal_id='meal',unit_id='g',quantity_micros=4000000,status='active',needed_on='2026-10-22',revision=1)
        self.item('k2','u2');self.location('k2','u2');self.lot('k2','u2')
        self.put('stock_commands',kitchen_id='k2',id='cmd2',actor_user_id='u2',idempotency_key='cmd2',request_hmac='synthetic-hmac',kind='adjust',created_at='now')
        self.put('stock_movements',kitchen_id='k2',id='a',command_id='cmd2',lot_id='lot',unit_id='g',delta_micros=5000000,kind='acquire',occurred_at='now')
        self.put('household_meal_plans',kitchen_id='k2',id='plan',owner_user_id='u2',envelope_id=self.envelope('household_meal_plans','plan','k2','u2'),status='active',revision=1,created_at='now')
        self.put('household_plan_meals',kitchen_id='k2',plan_id='plan',id='meal',owner_user_id='u2',envelope_id=self.envelope('household_plan_meals','meal','k2','u2'),planned_date='2026-10-22',time_zone='UTC',meal_slot='Dinner',servings_micros=2000000,status='planned',revision=1)
        self.put('stock_reservations',kitchen_id='k2',id='r',lot_id='lot',meal_id='meal',unit_id='g',quantity_micros=4000000,status='active',needed_on='2026-10-22',revision=1)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE stock_reservations SET kitchen_id='k2',id='new' WHERE kitchen_id='k1' AND id='r'")
        self.assertEqual(self.db.execute("SELECT SUM(quantity_micros) FROM stock_reservations WHERE kitchen_id='k2'").fetchone()[0],4000000)
    def test_vendor_record_can_hold_distinct_metrics_without_false_dedup(self):
        self.put('household_profiles',owner_user_id='u1',id='p',envelope_id=self.envelope('household_profiles','p'),status='active',created_at='now',updated_at='now')
        self.put('sec_consents',id='c',owner_user_id='u1',actor_user_id='u1',object_type='household_profile',object_id='p',purpose='private_use',notice_version='1',choice='granted',revision=1,valid_from=1,expires_at=9999999999,updated_at=1)
        common=dict(owner_user_id='u1',profile_id='p',consent_id='c',source_id='vendor',source_record_id='native-shared-record',observed_at='now',recorded_at='now',retain_until=9999999999)
        self.put('household_profile_observations',id='o1',envelope_id=self.envelope('household_profile_observations','o1'),source_observation_hmac='a'*64,**common)
        self.put('household_profile_observations',id='o2',envelope_id=self.envelope('household_profile_observations','o2'),source_observation_hmac='b'*64,**common)
        with self.assertRaises(sqlite3.IntegrityError):self.put('household_profile_observations',id='duplicate',envelope_id=self.envelope('household_profile_observations','duplicate'),source_observation_hmac='a'*64,**common)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM household_profile_observations').fetchone()[0],2)
    def test_typed_payload_contract_no_secret_fields_or_numeric_barcodes(self):
        import jsonschema
        schema=json.loads((ROOT/'schemas/household-private-payloads-v1.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        v=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
        row={'schema_version':'offmenu-household-location/1','area':'Pantry','shelf':'1','label':None}
        self.assertFalse(list(v.iter_errors(row)))
        self.assertTrue(list(v.iter_errors(dict(row,api_key='synthetic-secret'))))
        identifier=jsonschema.Draft202012Validator(schema['$defs']['identifier'])
        self.assertFalse(list(identifier.iter_errors({'scheme':'GTIN','namespace':'global','value':'00012345','validation_status':'unverified'})))
        self.assertTrue(list(identifier.iter_errors({'scheme':'GTIN','namespace':'global','value':12345,'validation_status':'unverified'})))
        self.assertEqual(set(BINDINGS[x]['payload_type'] for x in BINDINGS),set(y['$ref'].rsplit('/',1)[1] for y in schema['oneOf']))

if __name__=='__main__': unittest.main()
