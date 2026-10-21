"""Generated cache bytes/SQLite only; no retained cache, PDF, model or network."""
from contextlib import closing
from dataclasses import replace
import copy
import hashlib
import json
import sqlite3
import unittest
from unittest.mock import patch

from offmenu.refresh import recipe_section_cache as c
from offmenu.refresh.core import canonical, RefreshError


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class RecipeSectionCacheTests(unittest.TestCase):
    def fixture(self):
        records, pages = [], []
        sources = (c.SourcePin('source-a', 'fixture-release', 'a'*64, 'c'*64, 2),
                   c.SourcePin('source-b', 'fixture-release', 'b'*64, 'd'*64, 1))
        for i, sid in enumerate(('source-a', 'source-a', 'source-b')):
            pin = next(p for p in sources if p.source_id == sid)
            p1, p2 = 2+i*2, 3+i*2
            text = 'préface\n  Crème & 油  \nIngredients\n1½ spoon, raw\n'
            method = 'Method\n1. Keep exact.\n'
            path1, path2 = '/selected/'+sid+'/'+str(p1)+'.txt', '/selected/'+sid+'/'+str(p2)+'.txt'
            pages.extend((c.PageCache(sid, p1, path1, sha(text.encode()), text.encode()),
                          c.PageCache(sid, p2, path2, sha(method.encode()), method.encode())))
            def section(kind, page, path, content, start, end):
                lines = content.splitlines(keepends=True)
                a, z = sum(map(len, lines[:start-1])), sum(map(len, lines[:end]))
                return dict(kind=kind, pdfPage=page, textCachePath=path,
                            textCacheSHA256=sha(content.encode()), lineStart=start, lineEnd=end,
                            charStart=a, charEnd=z, text=content[a:z], textSHA256=sha(content[a:z].encode()))
            records.append(dict(cacheVersion=c.CACHE_VERSION, recordId='fixture-cache-'+str(i),
                sourceId=sid, release=pin.release, sourceSHA256=pin.pdf_sha256,
                sourceReceipt={'sha256':pin.receipt_sha256}, importReady=False,
                ingredientLines=None, orderedSteps=None, quantityInterpretations=None,
                pdfPages=[p1,p2], sourceDocumentLanguage='en; declared only',
                titleDisplay='DERIVATIVE MUST NOT REPLACE RAW TITLE',
                sections=[section('title',p1,path1,text,2,2),
                          section('ingredients-section',p1,path1,text,3,4),
                          section('method-section',p2,path2,method,1,2)],
                extension={'unknown':None,'text':'keep exact'}))
        return self.pack(records, sources, tuple(pages))

    def pack(self, records, sources, pages):
        raw = ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in records).encode()
        contract = canonical({'version':c.CACHE_VERSION,'recordsSHA256':sha(raw),'records':len(records)})
        selection = c.CacheSelection('fixture-new-run','/selected/generated-records.jsonl',sha(raw),sha(contract),'e'*64,'f'*64,'9'*64,
                                     len(records),sum(len(r['sections']) for r in records))
        return raw, contract, selection, sources, pages

    def load(self, db, fixture, **kw):
        raw, contract, selection, sources, pages = fixture
        return c.load_cached_recipe_sections(db,raw,contract,selection=selection,sources=sources,pages=pages,**kw)

    def test_raw_rows_unknowns_all_anchors_unicode_and_source_ordinals(self):
        fixture = self.fixture()
        with closing(sqlite3.connect(':memory:')) as db:
            result = self.load(db,fixture)
            self.assertEqual((result['sourceRows'],result['partialVariantRows'],result['anchoredSections']),(3,3,9))
            self.assertIsNone(result['logicalIngredientLineCount'])
            self.assertIsNone(result['logicalOrderedStepCount'])
            self.assertFalse(result['fullTemplateComplete'])
            self.assertFalse(result['importReady'])
            rows = db.execute('SELECT source_id,source_ordinal,native_record_id,citation_id,source_asset_sha256,source_payload_json FROM recipe_source_record ORDER BY source_id,source_ordinal').fetchall()
            self.assertEqual([(r[0],r[1]) for r in rows],[('source-a',1),('source-a',2),('source-b',1)])
            for row, line in zip(rows,fixture[0].splitlines(keepends=True)):
                self.assertEqual(row[2:4],(None,None))
                self.assertEqual(row[5].encode(),line)
                self.assertIsNone(json.loads(row[5])['ingredientLines'])
            title, concept, value, state, location = db.execute('SELECT original_title,dish_concept_id,yield_value_lexeme,ingredient_extraction_state,source_location_json FROM source_recipe_variant LIMIT 1').fetchone()
            self.assertEqual(title,'  Crème & 油  \n')
            self.assertEqual((concept,value,state),(None,None,c.PARTIAL))
            anchor = json.loads(location)['anchors'][0]
            self.assertNotEqual(anchor['charStart'],anchor['utf8ByteRange'][0])
            for table in ('recipe_ingredient_line','recipe_ordered_step','recipe_citation_ref','dish_concept_ref','recipe_region_assertion','source_menu','source_menu_item','menu_entry'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT state,observed_records FROM recipe_store_release').fetchone(),('completed',3))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_nulls_not_empty_or_full_template_and_prevalidation_no_mutation(self):
        fixture = self.fixture()
        for field,value in [('ingredientLines',[]),('orderedSteps',[]),('quantityInterpretations',{}),('importReady',True)]:
            records = [json.loads(l) for l in fixture[0].splitlines()]
            records[0][field] = value
            changed = self.pack(records,fixture[3],fixture[4])
            with self.subTest(field=field), closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaisesRegex(RefreshError,'raw-grain-required'):
                    self.load(db,changed)
                self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(),[])

    def test_page_hash_foreign_source_unicode_byte_confusion_and_locator_tamper(self):
        fixture = self.fixture()
        cases = []
        pages = list(fixture[4]);pages[0] = replace(pages[0],raw=b'changed');cases.append((*fixture[:4],tuple(pages)))
        pages = list(fixture[4]);pages[0] = replace(pages[0],source_id='source-b');cases.append((*fixture[:4],tuple(pages)))
        for mode in ('char','line','text','pdfPage','duplicate-kind'):
            records = [json.loads(l) for l in fixture[0].splitlines()]
            section = records[0]['sections'][0]
            if mode=='char':section['charStart'] += 1
            elif mode=='line':section['lineStart'] = 1
            elif mode=='text':section['text'] = 'wrong'
            elif mode=='pdfPage':section['pdfPage'] = 90
            else:records[0]['sections'].append(copy.deepcopy(section))
            cases.append(self.pack(records,fixture[3],fixture[4]))
        for changed in cases:
            with closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaises(RefreshError):self.load(db,changed)
                self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(),[])

    def test_pins_source_count_and_duplicate_record_identity(self):
        f=self.fixture()
        changes=[(f[0]+b' ',*f[1:]),(f[0],f[1]+b' ',*f[2:]),
                 (f[0],f[1],replace(f[2],expected_records=4),*f[3:])]
        for field,value in [('sourceSHA256','1'*64),('recordId','fixture-cache-1')]:
            records=[json.loads(l) for l in f[0].splitlines()];records[0][field]=value
            changes.append(self.pack(records,f[3],f[4]))
        for changed in changes:
            with closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaises(RefreshError):self.load(db,changed)

    def test_existing_transaction_attached_or_existing_store_never_modified(self):
        for mode in ('existing','transaction','attached'):
            with self.subTest(mode=mode), closing(sqlite3.connect(':memory:')) as db:
                if mode=='existing':db.execute('CREATE TABLE existing(value)');db.execute('INSERT INTO existing VALUES(7)');db.commit()
                elif mode=='transaction':db.execute('BEGIN')
                else:db.execute("ATTACH ':memory:' AS other")
                with self.assertRaises(RefreshError):self.load(db,self.fixture())
                if mode=='existing':self.assertEqual(db.execute('SELECT value FROM existing').fetchone(),(7,))

    def test_injected_write_failure_rolls_back_rows_and_restores_handler_limit(self):
        original=c.store._put
        def failed(db,table,row):
            if table=='source_recipe_variant':raise RuntimeError('generated-failure')
            return original(db,table,row)
        with closing(sqlite3.connect(':memory:')) as db:
            length=db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
            with patch.object(c.store,'_put',side_effect=failed), self.assertRaisesRegex(RuntimeError,'generated-failure'):
                self.load(db,self.fixture())
            self.assertEqual(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),length)
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('SELECT count(*) FROM recipe_source_record').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM source_recipe_variant').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT 1').fetchone(),(1,))

    def test_input_record_section_database_and_time_bounds(self):
        f=self.fixture()
        for limits in (replace(c.CacheLimits(),max_records_bytes=1),replace(c.CacheLimits(),max_page_bytes=1),
                       replace(c.CacheLimits(),max_records=1),replace(c.CacheLimits(),max_sections=1),
                       replace(c.CacheLimits(),max_steps=True),replace(c.CacheLimits(),max_seconds=901)):
            with closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaises(RefreshError):self.load(db,f,limits=limits)
        with closing(sqlite3.connect(':memory:')) as db:
            with patch.object(c.time,'monotonic',side_effect=[0,100]),self.assertRaisesRegex(RefreshError,'time-bound'):
                self.load(db,f)

    def test_explicit_row_transaction_for_isolation_none_and_python_autocommit_modes(self):
        modes = [('legacy-default', {}), ('legacy-none', {'isolation_level':None})]
        if hasattr(sqlite3.Connection,'autocommit'):
            modes.extend([('python-true', {'autocommit':True}),
                          ('python-false', {'autocommit':False}),
                          ('python-false-native-idle', {'autocommit':False})])
        original = c.store._put
        def fail_first_variant(db,table,row):
            if table=='source_recipe_variant':raise RuntimeError('generated-variant-failure')
            return original(db,table,row)
        for name, kwargs in modes:
            for failure in (True, False):
                with self.subTest(mode=name,failure=failure), closing(sqlite3.connect(':memory:',**kwargs)) as db:
                    if name=='python-false-native-idle':
                        db.execute('COMMIT')
                        self.assertFalse(db.in_transaction)
                    if db.in_transaction:
                        # PEP249 mode normally starts a caller-owned transaction.
                        # Reject it before DDL without committing/rolling it back.
                        with self.assertRaisesRegex(RefreshError,'selection'):
                            self.load(db,self.fixture())
                        self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(),[])
                        self.assertTrue(db.in_transaction)
                        continue
                    old_length = db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
                    if failure:
                        with patch.object(c.store,'_put',side_effect=fail_first_variant), self.assertRaisesRegex(RuntimeError,'generated-variant-failure'):
                            self.load(db,self.fixture())
                    else:
                        self.load(db,self.fixture())
                    counts = [db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                              for table in ('recipe_store_release','recipe_source_record','source_recipe_variant')]
                    self.assertEqual(counts, [0,0,0] if failure else [1,3,3])
                    self.assertFalse(db.in_transaction)
                    self.assertEqual(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),old_length)
                    self.assertEqual(db.execute('SELECT 1').fetchone(),(1,))


if __name__=='__main__':
    unittest.main()
