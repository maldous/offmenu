"""Generated-only bounded GOLD reader tests; actual demo is separately pinned."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gold_barcode_lookup as reader
import test_gold_builder as base
import test_gold_relation_lookup as alternatives

CODE='000123'
SELECTED=reader.SnapshotSelection(base.PIN,base.PIN)


def barcode(p,q,product='product',identity='barcode'):
    p['common']['assertions'].append(dict(id=identity,subjectId=product,propertyId='usda:gtin-upc',
        value=dict(kind='identifier',value=CODE),citationIds=['cite'],scope=base.PUBLIC,
        sourcePath='/generated/barcode',status='source-asserted'))
    q['supports'].append(dict(target_kind='assertion',target_id=identity,citation_id='cite',
                              support_scope='field',evidence_sha256=base.PIN))


def fixture(conditional=False):
    if conditional:p,q,scope=alternatives.alternative_fixture()
    else:p,q=base.fixture();scope=None
    barcode(p,q)
    return p,q,scope


class GoldBarcodeLookupTests(unittest.TestCase):
    def test_product_filter_keeps_structural_paths_without_granting_fit(self):
        p, q, source = alternatives.two_member_fixture()
        barcode(p, q)
        barcode(p, q, product='other-member', identity='other-barcode')
        with base.sqlite_proposal(base.build(p, q)) as db:
            before = db.total_changes
            for selected, expected in ((None, {'product', 'other-member'}),
                                       ('product', {'product'}), ('other-member', {'other-member'})):
                result = reader.read_barcode(db, CODE, selection=SELECTED, selected_product_id=selected)
                self.assertEqual(expected, {p['sourceProductId'] for p in result['products']})
                self.assertEqual(len(expected), len(result['paths']))
                self.assertFalse(result['productFitAcceptance'])
                self.assertFalse(result['automaticProductSelection'])
                self.assertFalse(result['sourceReferenceNutritionTransfer'])
                self.assertIsNone(result['recipeNutrientTotals'])
                for path in result['paths']:
                    self.assertEqual(source, path['sourceScope'])
                    self.assertEqual(dict(state='held', reason='selected-tuple-fit-contract-not-evaluated'),
                                     path['productFitQualification'])
                    self.assertIn('Selected product only', path['relations'][1]['scope']['reuseScope'])
            self.assertEqual(before, db.total_changes)

    def test_no_result_or_exact_wrong_filter_never_claims_product_fit(self):
        p, q, _ = fixture()
        with base.sqlite_proposal(base.build(p, q)) as db:
            for code, selected in (('999999', None), (CODE, 'absent-product')):
                result = reader.read_barcode(db, code, selection=SELECTED, selected_product_id=selected)
                self.assertFalse(result['productFitAcceptance'])
                self.assertEqual([], result['paths'])

    def test_complete_structural_source_path_and_context_without_transfer(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            before=db.total_changes;r=reader.read_barcode(db,CODE,selection=SELECTED,requested_context={'country':'A','cut':'whole'})
            self.assertEqual(before,db.total_changes)
            self.assertEqual('source-product-found',r['availability']);self.assertEqual(CODE,r['barcodeLexeme'])
            self.assertEqual(1,len(r['paths']));self.assertEqual('no-qualified-menu-relationships-found',r['menuData'])
            self.assertEqual(3,len(r['products'][0]['nutrition']))
            self.assertIn('unknown',{o['contextState'] for o in r['products'][0]['nutrition']})
            self.assertIn('matches',{o['contextState'] for o in r['products'][0]['nutrition']})
            self.assertIsNone(r['recipeNutrientTotals']);self.assertFalse(r['sourceReferenceNutritionTransfer'])
            self.assertFalse(r['completeExecutableRecipe']);self.assertFalse(r['automaticProductSelection'])
            entity=r['entities'][r['products'][0]['entityId']]
            self.assertTrue(entity['englishNames']);self.assertTrue(entity['originalResource']['names'])
            self.assertTrue(entity['sourceRecords']);self.assertTrue(r['citations'])
            for origin in entity['sourceRecords']:
                raw=db.execute('SELECT payload_json FROM gold_occurrences WHERE occurrence_id=?',(origin['occurrence_id'],)).fetchone()[0]
                self.assertEqual(json.loads(raw),origin['payload'])

    def test_exact_lexeme_and_absent_barcode(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            for lexeme in ('123','0001230','999999'):
                r=reader.read_barcode(db,lexeme,selection=SELECTED)
                self.assertEqual('no-result',r['availability']);self.assertEqual([],r['products'])
            for lexeme in (123,' 000123','０００１２３',''):
                with self.assertRaises(reader.BarcodeQueryError): reader.read_barcode(db,lexeme,selection=SELECTED)

    def test_missing_nutrition_keeps_structural_recipe_path(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            db.execute('DELETE FROM gold_observations')
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual('missing',r['nutritionState']);self.assertEqual(1,len(r['paths']))

    def test_class_reference_nutrition_never_transfers_to_product(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            canonical=db.execute("SELECT entity_id FROM gold_entities WHERE resource_id='canonical'").fetchone()[0]
            db.execute('UPDATE gold_observations SET entity_id=?',(canonical,))
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual([],r['products'][0]['nutrition']);self.assertEqual('missing',r['nutritionState'])

    def test_held_identifier_support_or_source_is_not_a_match(self):
        for failure in ('identifier','resource','rights','citation'):
            p,q,_=fixture()
            with base.sqlite_proposal(base.build(p,q)) as db:
                if failure=='identifier':db.execute("DELETE FROM gold_support WHERE target_kind='assertion' AND target_id='barcode'")
                elif failure=='resource':db.execute("DELETE FROM gold_support WHERE target_kind='resource' AND target_id='product'")
                elif failure=='rights':db.execute("UPDATE gold_occurrences SET state='held' WHERE record_id='product'")
                else:db.execute("UPDATE gold_citations SET payload_json=json_set(payload_json,'$.scope.visibility','private')")
                r=reader.read_barcode(db,CODE,selection=SELECTED)
                self.assertEqual([],r['products']);self.assertEqual([],r['paths']);self.assertTrue(r['held'])

    def test_conditional_scope_selection_reuses_existing_reader(self):
        p,q,scope=fixture(conditional=True)
        with base.sqlite_proposal(base.build(p,q)) as db:
            unknown=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual(1,len(unknown['paths'])) # Independent water only.
            chosen=dict(groupId='sugar',branchId='white',sourceScope=scope)
            yes=reader.read_barcode(db,CODE,selection=SELECTED,selections=[chosen])
            self.assertEqual(2,len(yes['paths']))
            for selections in ([dict(chosen,branchId='absent')],[chosen,chosen],
                               [dict(chosen,sourceScope=dict(scope,sourceVersion='stale'))]):
                no=reader.read_barcode(db,CODE,selection=SELECTED,selections=selections)
                self.assertEqual(1,len(no['paths']))
            with self.assertRaises(reader.BarcodeQueryError):reader.read_barcode(db,CODE,selection=SELECTED,selections=[{}])

    def test_multiple_products_preserved_and_explicit_scope_never_falls_back(self):
        p,q,_=fixture();base.GoldBuilderTests.add_subset_resource(None,p,q,'product','product2')
        edge=copy.deepcopy(next(e for e in p['common']['relations'] if e['id']=='represents'))
        edge.update(id='represents2',subjectId='product2');p['common']['relations'].append(edge)
        q['supports'].append(dict(target_kind='relation',target_id='represents2',citation_id='cite',support_scope='relationship',evidence_sha256=base.PIN))
        barcode(p,q,'product2','barcode2')
        with base.sqlite_proposal(base.build(p,q)) as db:
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual('ambiguous-source-products',r['availability']);self.assertEqual(2,len(r['products']))
            r=reader.read_barcode(db,CODE,selection=SELECTED,selected_product_id='product2')
            self.assertEqual(['product2'],[p['sourceProductId'] for p in r['products']])
            r=reader.read_barcode(db,CODE,selection=SELECTED,selected_product_id='not-this-product')
            self.assertEqual([],r['products']);self.assertEqual([],r['paths']);self.assertTrue(r['held'])

    def test_numeric_source_identifier_is_not_string_coerced(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            db.execute("UPDATE gold_claims SET payload_json=json_set(payload_json,'$.value.value',123) WHERE assertion_id='barcode'")
            self.assertEqual([],reader.read_barcode(db,'123',selection=SELECTED)['products'])

    def test_non_barcode_numeric_identifier_is_not_a_barcode_match(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            db.execute("UPDATE gold_claims SET property_id='source:sku',payload_json=json_set(payload_json,'$.propertyId','source:sku') WHERE assertion_id='barcode'")
            result=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual([],result['products']);self.assertEqual(['usda:gtin-upc'],result['identifierProperties'])

    def test_existing_menu_relationship_only_when_actually_qualified(self):
        p,q,_=fixture();proposal=base.build(p,q)
        resource=copy.deepcopy(next(r for r in p['common']['resources'] if r['id']=='recipe'))
        resource.update(id='generated-menu',type='menu')
        recipe=next(e for e in proposal['rows']['gold_entities'] if e['resource_id']=='recipe')
        with base.sqlite_proposal(proposal) as db:
            db.execute('INSERT INTO gold_entities VALUES(?,?,?,?,?,?)',('menu-entity','generated-menu','recipes','menu','verified',json.dumps(resource)))
            occurrence=copy.deepcopy(next(o for o in proposal['rows']['gold_occurrences'] if o['record_id']=='recipe'))
            occurrence.update(occurrence_id='menu-occ',record_id='generated-menu')
            body=json.loads(occurrence['payload_json']);body.update(occurrence_id='menu-occ',record_id='generated-menu',resource_ids=['generated-menu'])
            occurrence['payload_json']=json.dumps(body)
            cols=base.gold.TABLE_COLUMNS['gold_occurrences']
            db.execute('INSERT INTO gold_occurrences('+','.join(cols)+')VALUES('+','.join('?'for _ in cols)+')',[occurrence[c]for c in cols])
            db.execute('INSERT INTO gold_entity_occurrences VALUES(?,?)',('menu-entity','menu-occ'))
            relation=dict(id='actual-menu-link',subjectId='generated-menu',predicateId='menu_contains_recipe',
                objectId='recipe',citationIds=['cite'],scope=base.PUBLIC,sourcePath='/generated/menu')
            db.execute('INSERT INTO gold_edges VALUES(?,?,?,?,?,?,?)',('menu-edge','actual-menu-link','menu-entity','menu_contains_recipe',recipe['entity_id'],'verified',json.dumps(relation)))
            for kind,target,scope in [('resource','generated-menu','record'),('relation','actual-menu-link','relationship')]:
                db.execute('INSERT INTO gold_support VALUES(?,?,?,?,?,?)',(kind+'-menu-support',kind,target,'cite',scope,base.PIN))
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual('relationships-present',r['menuData']);self.assertEqual(1,len(r['menus']))
            self.assertEqual(relation,r['menus'][0]['relation'])
            db.execute("DELETE FROM gold_support WHERE target_id='actual-menu-link'")
            self.assertEqual([],reader.read_barcode(db,CODE,selection=SELECTED)['menus'])

    def test_original_names_preserved_without_outward_translation(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            db.execute("DELETE FROM gold_support WHERE target_kind='text' AND target_id='product-text'")
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            node=r['entities'][r['products'][0]['entityId']]
            self.assertEqual([],node['englishNames']);self.assertEqual('unknown',node['nameState'])
            self.assertEqual('product',node['originalResource']['names'][0]['value'])
            self.assertEqual(1,len(r['paths']))

    def test_large_source_cell_and_held_nutrition_are_explicit(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            db.execute("UPDATE gold_observations SET state='held'")
            r=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual('held',r['nutritionState']);self.assertTrue(r['held'])
            original_limit=db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
            db.execute("UPDATE gold_entities SET payload_json=json_set(payload_json,'$.generatedLarge','"+'x'*1048576+"') WHERE resource_id='product'")
            with self.assertRaises(reader.BarcodeQueryError):reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual(original_limit,db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH))

    def test_limits_error_and_cleanup_do_not_return_truncated_success(self):
        p,q,_=fixture(conditional=True)
        with base.sqlite_proposal(base.build(p,q)) as db:
            for limits in ({'max_rows':1},{'max_bytes':10},{'max_steps':1},
                           {'max_paths':1,'selections':[dict(groupId='sugar',branchId='white',sourceScope=fixture(True)[2])]}):
                with self.assertRaises(reader.BarcodeQueryError):reader.read_barcode(db,CODE,selection=SELECTED,**limits)
                self.assertEqual((1,),db.execute('SELECT 1').fetchone())
            for bad in ({'max_rows':0},{'max_bytes':1048577},{'max_seconds':float('nan')}):
                with self.assertRaises(reader.BarcodeQueryError):reader.read_barcode(db,CODE,selection=SELECTED,**bad)
            with self.assertRaises(reader.BarcodeQueryError):reader.read_barcode(db,CODE,selection=None)

    def test_complete_response_exact_byte_cap_and_one_byte_less(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            result=reader.read_barcode(db,CODE,selection=SELECTED)
            cap=len(reader.encoded(result))
            for _ in range(3):
                result=reader.read_barcode(db,CODE,selection=SELECTED,max_bytes=cap)
                actual=len(reader.encoded(result))
                if actual==cap:break
                cap=actual
            self.assertEqual(cap,len(reader.encoded(result)))
            with self.assertRaisesRegex(reader.BarcodeQueryError,'output-limit'):
                reader.read_barcode(db,CODE,selection=SELECTED,max_bytes=cap-1)

    def test_frozen_snapshot_cli_bytes_sidecars_and_pin_failures(self):
        p,q,_=fixture()
        with tempfile.TemporaryDirectory(prefix='offmenu-barcode-generated-') as folder:
            path=Path(folder)/'generated.sqlite'
            with base.sqlite_proposal(base.build(p,q)) as db:
                db.commit()
                with sqlite3.connect(path) as target:db.backup(target)
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            receipt=Path(folder)/'admission.json';receipt.write_text(json.dumps(dict(state='ACCEPTED_GENERATED_FIXTURE',artifact=dict(path=str(path),sha256=sha(path)))))
            before=path.read_bytes()
            result=reader.query_snapshot(receipt,sha(receipt),CODE)
            self.assertEqual(1,len(result['paths']));self.assertEqual(before,path.read_bytes())
            cmd=[sys.executable,'-B',str(ROOT/'gold_barcode_lookup.py'),'--admission',str(receipt),
                 '--admission-sha256',sha(receipt),'--barcode',CODE]
            cli=subprocess.run(cmd,capture_output=True,text=True,check=True)
            self.assertEqual(CODE,json.loads(cli.stdout)['barcodeLexeme'])
            self.assertEqual({'generated.sqlite','admission.json'},{p.name for p in Path(folder).iterdir()})
            with self.assertRaises(reader.BarcodeQueryError):reader.query_snapshot(receipt,'b'*64,CODE)
            Path(str(path)+'-wal').write_text('generated test sidecar')
            with self.assertRaises(reader.BarcodeQueryError):reader.query_snapshot(receipt,sha(receipt),CODE)

    def test_receipt_replacement_after_single_read_cannot_change_selection(self):
        p,q,_=fixture()
        with tempfile.TemporaryDirectory(prefix='offmenu-receipt-generated-') as folder:
            folder=Path(folder);a=folder/'a.sqlite';b=folder/'b.sqlite';receipt=folder/'receipt.json'
            for path in (a,b):
                with base.sqlite_proposal(base.build(p,q)) as db:
                    if path==b:db.execute("UPDATE gold_citations SET payload_json=json_set(payload_json,'$.attribution','Distinct generated B')")
                    db.commit()
                    with sqlite3.connect(path) as target:db.backup(target)
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            selected=dict(state='ACCEPTED_GENERATED_A',artifact=dict(path=str(a),sha256=sha(a)))
            replacement=dict(state='ACCEPTED_GENERATED_B',artifact=dict(path=str(b),sha256=sha(b)))
            receipt.write_text(json.dumps(selected));selected_sha=sha(receipt)
            original_read=reader.read_barcode
            def interleaved(*args,**kwargs):
                # Selected receipt bytes were already verified. A same-path
                # replacement must now reject the whole result on exit.
                receipt.write_text(json.dumps(replacement))
                return original_read(*args,**kwargs)
            with patch.object(reader,'read_barcode',interleaved):
                with self.assertRaisesRegex(reader.BarcodeQueryError,'identity-changed|admission-changed-during-query'):
                    reader.query_snapshot(receipt,selected_sha,CODE)
            self.assertNotEqual(selected_sha,sha(receipt))
            self.assertEqual(replacement,json.loads(receipt.read_text()))

    def test_receipt_buffer_hard_cap_rejects_oversized_input(self):
        with tempfile.TemporaryDirectory(prefix='offmenu-receipt-size-') as folder:
            receipt=Path(folder)/'oversized.json';receipt.write_bytes(b' ' * 1048577)
            with self.assertRaisesRegex(reader.BarcodeQueryError,'admission-pin-mismatch'):
                reader.query_snapshot(receipt,hashlib.sha256(receipt.read_bytes()).hexdigest(),CODE)

    def test_separate_metric_definition_citation_rights_and_supports_returned(self):
        p,q,_=fixture();citation=copy.deepcopy(p['common']['citations'][0])
        citation.update(id='definition-only',license='Generated separate definition license',
                        attribution='Generated separate definition attribution')
        p['common']['citations'].append(citation);p['metrics'][0]['citation_ids']=['definition-only']
        for support in q['supports']:
            if support['target_kind']=='metric':support['citation_id']='definition-only'
        proposal=base.build(p,q)
        for failure in (None,'missing','invalid-pin','wrong-scope','private'):
            with self.subTest(failure=failure):
                with base.sqlite_proposal(proposal) as db:
                    if failure=='missing':db.execute("DELETE FROM gold_support WHERE target_kind='metric'")
                    elif failure=='invalid-pin':db.execute("UPDATE gold_support SET evidence_sha256='invalid' WHERE target_kind='metric'")
                    elif failure=='wrong-scope':db.execute("UPDATE gold_support SET support_scope='field' WHERE target_kind='metric'")
                    elif failure=='private':db.execute("UPDATE gold_citations SET payload_json=json_set(payload_json,'$.scope.visibility','private') WHERE citation_id='definition-only'")
                    result=reader.read_barcode(db,CODE,selection=SELECTED)
                    self.assertEqual(1,len(result['paths']))
                    if failure is None:
                        self.assertEqual(citation,result['citations']['definition-only'])
                        self.assertEqual(3,len(result['products'][0]['nutrition']))
                        for record in result['products'][0]['nutrition']:
                            self.assertEqual(['definition-only'],record['metricDefinitionCitationIds'])
                            self.assertEqual('definition',record['metricDefinitionSupports'][0]['support_scope'])
                    else:
                        self.assertEqual([],result['products'][0]['nutrition'])
                        self.assertEqual('held',result['nutritionState'])
                        self.assertTrue(any(h['reason']=='metric definition provenance held' for h in result['held']))

    def test_large_unrelated_reference_assertions_do_not_fill_support_index(self):
        p,q,_=fixture()
        with base.sqlite_proposal(base.build(p,q)) as db:
            canonical=db.execute("SELECT entity_id FROM gold_entities WHERE resource_id='canonical'").fetchone()[0]
            claims=[];supports=[]
            for index in range(12000):
                identity='generated-reference-'+str(index)
                payload=dict(id=identity,subjectId='canonical',propertyId='source:reference-nutrition',
                    value=dict(kind='quantity',value=1,unitId='g',dimension='mass'),citationIds=['cite'],scope=base.PUBLIC)
                claims.append((identity,identity,canonical,payload['propertyId'],'verified',json.dumps(payload)))
                supports.append((identity,'assertion',identity,'cite','field',base.PIN))
            db.executemany('INSERT INTO gold_claims VALUES(?,?,?,?,?,?)',claims)
            db.executemany('INSERT INTO gold_support VALUES(?,?,?,?,?,?)',supports)
            result=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual(1,len(result['paths']));self.assertEqual(3,len(result['products'][0]['nutrition']))
            self.assertLess(result['limits']['rowsRead'],10000)
            self.assertFalse(result['sourceReferenceNutritionTransfer'])

    def test_distinct_occurrence_only_citation_is_returned_with_rights(self):
        p,q,_=fixture();citation=copy.deepcopy(p['common']['citations'][0])
        citation.update(id='occurrence-only',license='Generated occurrence-only license',
                        attribution='Generated occurrence-only attribution')
        p['common']['citations'].append(citation)
        next(o for o in p['occurrences'] if o['occurrence_id']=='product-occ')['citation_ids'].append('occurrence-only')
        proposal=base.build(p,q)
        self.assertEqual('verified',next(o for o in proposal['rows']['gold_occurrences'] if o['occurrence_id']=='product-occ')['state'])
        with base.sqlite_proposal(proposal) as db:
            result=reader.read_barcode(db,CODE,selection=SELECTED)
            self.assertEqual(1,len(result['paths']))
            self.assertEqual(citation,result['citations']['occurrence-only'])
            for node in result['entities'].values():
                for occurrence in node['sourceRecords']:
                    for cid in occurrence['payload']['citation_ids']:
                        self.assertIn(cid,result['citations'])

    def test_bad_occurrence_provenance_holds_only_affected_sugar_sibling(self):
        for failure in ('missing','private','license','attribution','wrong-id','empty-ids','wrong-ids-type','rights','support'):
            with self.subTest(failure=failure):
                p,q,scope=fixture(conditional=True);citation=copy.deepcopy(p['common']['citations'][0])
                citation['id']='sugar-occurrence-only';p['common']['citations'].append(citation)
                next(o for o in p['occurrences'] if o['occurrence_id']=='mention-occ')['citation_ids']=['cite','sugar-occurrence-only']
                if failure=='rights':next(r for r in q['records'] if r['occurrence_id']=='mention-occ')['rights_state']='held'
                if failure=='support':q['supports']=[s for s in q['supports'] if not(s['target_kind']=='resource' and s['target_id']=='mention')]
                with base.sqlite_proposal(base.build(p,q)) as db:
                    if failure=='missing':db.execute("DELETE FROM gold_citations WHERE citation_id='sugar-occurrence-only'")
                    elif failure=='private':db.execute("UPDATE gold_citations SET payload_json=json_set(payload_json,'$.scope.visibility','private') WHERE citation_id='sugar-occurrence-only'")
                    elif failure in ('license','attribution'):
                        db.execute("UPDATE gold_citations SET payload_json=json_remove(payload_json,?) WHERE citation_id='sugar-occurrence-only'",('$.'+failure,))
                    elif failure=='wrong-id':db.execute("UPDATE gold_citations SET payload_json=json_set(payload_json,'$.id','other-citation') WHERE citation_id='sugar-occurrence-only'")
                    elif failure in ('empty-ids','wrong-ids-type'):
                        value=[] if failure=='empty-ids' else 'sugar-occurrence-only'
                        row=json.loads(db.execute("SELECT payload_json FROM gold_occurrences WHERE occurrence_id='mention-occ'").fetchone()[0])
                        row['citation_ids']=value
                        db.execute("UPDATE gold_occurrences SET payload_json=? WHERE occurrence_id='mention-occ'",(json.dumps(row),))
                    result=reader.read_barcode(db,CODE,selection=SELECTED,
                        selections=[dict(groupId='sugar',branchId='white',sourceScope=scope)])
                    self.assertEqual(1,len(result['paths']))
                    self.assertEqual('water-mention',result['entities'][result['paths'][0]['mentionEntityId']]['resourceId'])
                    self.assertTrue(result['held'])
                    self.assertFalse(any(n['resourceId']=='mention' for n in result['entities'].values()))
                    for node in result['entities'].values():
                        for occurrence in node['sourceRecords']:
                            for cid in occurrence['payload']['citation_ids']:self.assertIn(cid,result['citations'])


if __name__=='__main__':unittest.main()
