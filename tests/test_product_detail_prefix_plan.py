"""Bounded generated SQLite plans/work only; no actual checkpoint or inputs."""
import ast
from contextlib import closing
import hashlib
import inspect
import sqlite3
import unittest

from offmenu.refresh import product_detail_import as store
from offmenu.refresh.core import canonical


SOURCE = ast.parse(inspect.getsource(store._checkpoint_prefix))
PREFIX_SQL = next(n.value for n in ast.walk(SOURCE) if isinstance(n, ast.Constant)
    and isinstance(n.value, str) and n.value.startswith('SELECT p.record_kind,count(*),sum('))
IDENTIFIER_SQL = next(n.value for n in ast.walk(SOURCE) if isinstance(n, ast.Constant)
    and isinstance(n.value, str) and n.value.startswith('SELECT count(*) FROM retained_reference_record r JOIN product_detail_identifier'))
BASELINE_SQL = PREFIX_SQL.replace('r CROSS JOIN product_detail_projection', 'r JOIN product_detail_projection')
OPERATION = 'e' * 64
ASSET_SHA = '1' * 64


def add_row(db, ref, asset, ordinal, kind, *, generation='generated', sha=ASSET_SHA,
            binding=None):
    db.execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (ref, 'fixture', 'fixture-release', asset, sha, ordinal, ref, '/generated', 'en', '{}',
         '3'*64, None, 'fixture', 'fixture', 'fixture', 'processed'))
    db.execute('INSERT INTO product_detail_projection VALUES(?,?,?,?,?,?,?,?,?,?)',
        (ref, generation, kind, None, canonical(binding if binding is not None else
         {'operationReceiptSha256': OPERATION}).decode(), None, '[]', None, 'pending', 'source-assertion'))
    if kind == 'product':
        db.execute('INSERT INTO product_detail_identifier VALUES(?,?,?,?,?,?)',
            (ref, 1, 'barcode', 'generated-'+ref, 'source-asserted', '/data/identifiers/0'))


def fixture(assets, pairs=200):
    db = sqlite3.connect(':memory:')
    db.execute('PRAGMA foreign_keys=ON'); db.executescript(store.DDL)
    db.execute('INSERT INTO product_detail_generation(generation_id,input_manifest_sha256,schema_version,projection_version,operation_selection_sha256,state,coverage_scope_json,exceptions_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
        ('generated', '2'*64, store.VERSION, 'source-native-full-payload/1', OPERATION, 'incomplete', '{}', '[]', 'generated-time'))
    for a in range(assets):
        for pair in range(pairs):
            for offset,kind in enumerate(('product','nutrientProfile'),1):
                add_row(db, f'{a}-{pair}-{kind}', 'asset-'+str(a), 2*pair+offset, kind)
    db.commit()
    return db


def plan(db, sql, params):
    return db.execute('EXPLAIN QUERY PLAN '+sql, params).fetchall()


def measure(db, sql, assets, pairs=200):
    ticks = [0]
    def progress():
        ticks[0] += 1
        return int(ticks[0] > 100000)  # 10M VM operations, generated fixture only
    db.set_progress_handler(progress,100)
    try:
        rows = [db.execute(sql,(OPERATION,'asset-'+str(a),ASSET_SHA,'generated')).fetchall()
                for a in range(assets)]
    finally:
        db.set_progress_handler(None,0)
    expected = {'product':(pairs,0),'nutrientProfile':(pairs,0)}
    if any({kind:(count,wrong) for kind,count,wrong in result} != expected for result in rows):
        raise AssertionError('generated counts/operation bindings differ')
    return {'approximateVMOperations':ticks[0]*100,'progressCallbacksEvery100VMOperations':ticks[0],
        'plan':plan(db,sql,(OPERATION,'asset-0',ASSET_SHA,'generated')),
        'resultSha256':hashlib.sha256(canonical(rows)).hexdigest()}


class ProductDetailPrefixPlanTests(unittest.TestCase):
    def assert_asset_search_first(self, rows):
        searches = [detail for _,_,_,detail in rows if 'SEARCH ' in detail or 'SCAN ' in detail]
        self.assertTrue(searches)
        self.assertTrue(searches[0].startswith('SEARCH r '), searches)
        self.assertIn('asset_id=? AND asset_sha256=?',searches[0])
        self.assertFalse(any('SCAN ' in step for step in searches),searches)

    def test_same_schema_asset_first_plan_and_bounded_linear_VM_work(self):
        observations=[]
        self.assertEqual(hashlib.sha256(store.DDL.encode()).hexdigest(),
            'f85e1696fa46d3c1b268d4969fa0569534ccaa8ade209c1c523c09bbd0046632')
        for assets in (8,16):
            with closing(fixture(assets)) as db:
                previous=measure(db,BASELINE_SQL,assets);current=measure(db,PREFIX_SQL,assets)
                self.assertEqual(current['resultSha256'],previous['resultSha256'])
                self.assert_asset_search_first(current['plan'])
                # The adjacent identifier count already selects the asset index.
                adjacent=plan(db,IDENTIFIER_SQL,('asset-0',ASSET_SHA))
                self.assert_asset_search_first(adjacent)
                self.assertEqual(db.execute(IDENTIFIER_SQL,('asset-0',ASSET_SHA)).fetchone(),(200,))
                self.assertLessEqual(current['approximateVMOperations'],previous['approximateVMOperations']*1.1)
                observations.append(current['approximateVMOperations'])
        self.assertLess(observations[1]/observations[0],2.3)

    def test_query_result_equality_with_wrong_missing_operations_and_other_scopes(self):
        with closing(fixture(3,pairs=3)) as db:
            db.execute('UPDATE product_detail_projection SET source_binding_json=? WHERE reference_record_id=?',
                (canonical({'operationReceiptSha256':'f'*64}).decode(),'0-0-product'))
            db.execute('UPDATE product_detail_projection SET source_binding_json=? WHERE reference_record_id=?',
                ('{}','0-0-nutrientProfile'))
            db.execute('INSERT INTO product_detail_generation SELECT ?,input_manifest_sha256,schema_version,projection_version,operation_selection_sha256,state,coverage_scope_json,expected_asset_count,processed_asset_count,product_records,profile_records,exceptions_json,created_at,modified_at,removed_at,created_by,owner_actor_reference,access_policy_reference FROM product_detail_generation',('other-generation',))
            add_row(db,'other-generation-record','asset-0',100,'product',generation='other-generation')
            add_row(db,'other-sha-record','asset-0',101,'product',sha='4'*64)
            db.commit()
            cases=((OPERATION,'asset-0',ASSET_SHA,'generated'),
                   ('f'*64,'asset-0',ASSET_SHA,'generated'),
                   (OPERATION,'asset-0',ASSET_SHA,'other-generation'),
                   (OPERATION,'asset-0','4'*64,'generated'),
                   (OPERATION,'not-selected',ASSET_SHA,'generated'))
            for params in cases:
                with self.subTest(params=params):
                    actual=db.execute(PREFIX_SQL,params).fetchall()
                    self.assertEqual(actual,db.execute(BASELINE_SQL,params).fetchall())
            self.assertEqual(db.execute(PREFIX_SQL,cases[0]).fetchall(),[('nutrientProfile',3,1),('product',3,1)])
            self.assertEqual(db.execute(PREFIX_SQL,cases[2]).fetchall(),[('product',1,0)])
            self.assertEqual(db.execute(PREFIX_SQL,cases[3]).fetchall(),[('product',1,0)])
            self.assertEqual(db.execute(PREFIX_SQL,cases[4]).fetchall(),[])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__ == '__main__':unittest.main()
