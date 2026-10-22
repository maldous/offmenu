"""Generated error-isolation/skip fixtures only; no datasets, network, or Foo."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_recipes as recipes
import ingest_errors as errors
import ingest_store
from ingest_store import DomainStore
from ingest_engine import IngestContext
from ingest_acquired_recipes import MalformedAcquiredRecipe, REASONS as RECIPE_REASONS
from ingest_acquired_menus import REASONS as MENU_REASONS
from acquired_recipe_js import UnsupportedJavaScript


def recipe(title):
    return {'name': title, 'ingredients': ['beans'], 'instructions': ['Mix.']}


class ErrorIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {'reserve_bytes': 0, 'batch_size': 1}

    def source(self, name, raw):
        path = self.root / name
        path.write_text(raw)
        return {'id': name, 'path': str(path), 'format': path.suffix[1:],
                'domains': ['recipes', 'ingredients']}

    def ingest(self, source, config=None, domain='recipes'):
        config = config or self.config
        context = IngestContext(domain, self.root/'state', config,
                                threading.Event(), lambda *args: None, time.monotonic())
        with DomainStore(domain, self.root/'state', config) as store:
            context.store = store
            summary = recipes.run_domain(domain, [source], context)
            rows = [json.loads(x[0]) for x in store.db.execute('SELECT payload_json FROM records ORDER BY row_number')]
            error_rows = store.db.execute('SELECT row_number,error_class FROM source_errors ORDER BY row_number,error_class').fetchall()
            durable = store.db.execute('SELECT version,cursor,written,errors,status FROM sources').fetchall()
        return summary, rows, error_rows, durable

    def test_expected_leads_do_not_write_errors_or_fingerprint_each_record(self):
        source = self.source('leads.jsonl', '{"name":"Generated lead","url":"https://example.invalid"}\n' * 5000 + json.dumps(recipe('Good'))+'\n')
        with mock.patch.object(ingest_store, '_fingerprint', wraps=ingest_store._fingerprint) as fingerprints:
            summary, rows, error_rows, durable = self.ingest(source)
        self.assertEqual((summary['written'], summary['errors'], summary['skipped'], summary['status']), (1, 0, 5000, 'complete'))
        self.assertEqual(summary['sources'][0]['unsupported_reason_counts'], {'unrecognized_recipe_or_lead_only': 5000})
        self.assertEqual(error_rows, [])
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(fingerprints.call_count, 4)
        self.assertEqual(durable[0][1:], (1, 1, 0, 'complete'))

    def test_nonrecipe_text_is_skip_but_malformed_recipe_still_error(self):
        source = self.source('text.jsonl', '\n'.join(json.dumps(x) for x in [
            {'text': 'Not a recipe', 'title': 'A source note'},
            {'@type': 'Recipe', 'ingredients': ['beans'], 'instructions': ['Mix.']}, recipe('Good')])+'\n')
        summary, rows, error_rows, _ = self.ingest(source)
        self.assertEqual((summary['errors'], summary['skipped']), (1, 1))
        self.assertEqual(error_rows, [(-2, 'MalformedRecord')])
        self.assertEqual([r['title'] for r in rows], ['Good'])
        self.assertEqual(summary['sources'][0]['unsupported_reason_counts'], {'not_a_supported_recipe_record': 1})

    def test_legacy_partial_resume_keeps_error_ordinals_and_source_version(self):
        source = self.source('resume.jsonl', '\n'.join(json.dumps(x) for x in [
            {'lead': 1}, False, recipe('First'), {'lead': 2}, 19, recipe('Last')])+'\n')
        def legacy(context, source, exc, stats):
            stats['skipped'] += 1
            context.report_error(source, exc)
        with mock.patch.object(recipes, '_unsupported_record', side_effect=legacy):
            first = self.ingest(source, {**self.config, 'max_rows_per_source': 1})
        second = self.ingest(source)
        self.assertEqual(first[3][0][0], second[3][0][0])
        self.assertEqual(first[2], second[2])
        self.assertEqual(second[0]['sources'][0]['resumed_from'], 1)
        self.assertEqual([r['title'] for r in second[1]], ['First', 'Last'])
        self.assertEqual(second[3][0][1:4], (2, 2, 4))

    def test_legacy_complete_with_lead_errors_is_not_replayed_or_rewritten(self):
        source = self.source('legacy.jsonl', '{"lead":1}\n'+json.dumps(recipe('Good'))+'\n')
        def legacy(context, source, exc, stats):
            stats['skipped'] += 1
            context.report_error(source, exc)
        with mock.patch.object(recipes, '_unsupported_record', side_effect=legacy):
            first = self.ingest(source)
        with mock.patch.object(recipes, '_read_rows', side_effect=AssertionError('historical complete replay')):
            second = self.ingest(source)
        self.assertEqual(first[2:], second[2:])
        self.assertEqual(second[0]['written'], 0)
        self.assertEqual(second[0]['errors'], 1)

    def test_framed_array_strict_rejections_keep_later_members_and_pointers(self):
        source = self.source('array.json', '['+json.dumps(recipe('First'))+
            ',{"duplicate":1,"duplicate":2},{"bad":NaN},'+json.dumps(recipe('Last'))+']')
        result, rows, error_rows, _ = self.ingest(source)
        self.assertEqual(result['errors'], 2)
        self.assertEqual([r['title'] for r in rows], ['First', 'Last'])
        self.assertEqual([r['provenance']['pointer'] for r in rows], ['/0', '/3'])
        self.assertEqual(error_rows, [(-2, 'MalformedRecord'), (-1, 'MalformedRecord')])
        second = self.ingest(source)
        self.assertEqual(second[0]['written'], 0)
        self.assertEqual(second[2], error_rows)

    def test_framing_damage_still_terminates_source_without_guessing(self):
        source = self.source('broken.json', '['+json.dumps(recipe('First'))+', {broken},'+json.dumps(recipe('Last'))+']')
        result, rows, _, durable = self.ingest(source)
        self.assertEqual([r['title'] for r in rows], ['First'])
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(durable[0][1], 1)
        self.assertNotEqual(durable[0][-1], 'complete')

    def test_legacy_array_failure_resume_retains_prefix_and_recovers_tail(self):
        source = self.source('old-array.json', '['+json.dumps(recipe('First'))+',{"x":1,"x":2},'+json.dumps(recipe('Last'))+']')
        original = recipes._JSONStream.__init__
        def legacy(self, stream, check, limit, on_record_error=None):
            return original(self, stream, check, limit)
        with mock.patch.object(recipes._JSONStream, '__init__', legacy):
            first = self.ingest(source)
        second = self.ingest(source)
        self.assertEqual([r['title'] for r in first[1]], ['First'])
        self.assertEqual([r['title'] for r in second[1]], ['First', 'Last'])
        self.assertEqual(second[0]['sources'][0]['resumed_from'], 1)
        self.assertEqual(first[3][0][0], second[3][0][0])
        self.assertEqual(second[0]['written'], 1)

    def test_sqlite_bad_payload_isolated_and_source_unchanged(self):
        path = self.root/'payloads.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE recipes(id INTEGER PRIMARY KEY,payload_json TEXT)')
            db.executemany('INSERT INTO recipes VALUES(?,?)', [(1,json.dumps(recipe('First'))),(2,'{bad}'),(3,json.dumps(recipe('Last')))])
        before=path.read_bytes()
        source={'id':'sqlite','path':str(path),'format':'sqlite','domains':['recipes']}
        result,rows,error_rows,durable=self.ingest(source)
        self.assertEqual([r['title'] for r in rows],['First','Last'])
        self.assertEqual([r['provenance']['pointer'] for r in rows],['/table/recipes/1','/table/recipes/3'])
        self.assertEqual(result['errors'],1)
        self.assertEqual(error_rows,[(-1,'JSONDecodeError')])
        self.assertEqual(durable[0][1],2)
        self.assertEqual(path.read_bytes(),before)

    def test_sqlite_recovery_cursor_resume_does_not_lose_tail(self):
        path=self.root/'resume.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE recipes(payload_json TEXT)')
            db.executemany('INSERT INTO recipes VALUES(?)',[(json.dumps(recipe('First')),),('{bad}',),(json.dumps(recipe('Last')),), (json.dumps(recipe('Tail')), )])
        source={'id':'sqlite','path':str(path),'format':'sqlite','domains':['recipes']}
        first=self.ingest(source,{**self.config,'max_rows_per_source':1})
        second=self.ingest(source)
        self.assertEqual(first[3][0][0],second[3][0][0])
        self.assertEqual([r['title'] for r in second[1]],['First','Last','Tail'])
        self.assertEqual(second[0]['sources'][0]['resumed_from'],1)
        self.assertEqual(second[2],[(-1,'JSONDecodeError')])

    def test_acquired_vocabulary_exact_and_unknown_messages_private(self):
        self.assertTrue(RECIPE_REASONS | MENU_REASONS <= errors.ERROR_REASONS)
        self.assertEqual(errors.classify_error(MalformedAcquiredRecipe('foodista_sections_ambiguous')),
            ('MalformedAcquiredRecipe','foodista_sections_ambiguous'))
        self.assertEqual(errors.classify_error(UnsupportedJavaScript('javascript_nonliteral_value')),
            ('UnsupportedJavaScript','javascript_nonliteral_value'))
        for message in ('foodista_sections_ambiguous SECRET','/private/SECRET'):
            self.assertEqual(errors.classify_error(MalformedAcquiredRecipe(message))[1],'other_or_unavailable')
        self.assertEqual(errors.classify_error(json.JSONDecodeError('SECRET','SECRET',0))[1],'invalid_json')
        self.assertEqual(errors.classify_error(UnicodeDecodeError('utf8',b'\xff',0,1,'SECRET'))[1],'invalid_unicode')

    def test_new_reason_histogram_is_bounded_conservative_and_idempotent(self):
        counts={key:i+1 for i,key in enumerate(sorted(errors.ERROR_REASONS))}
        value={'status':'available','reason_counts':counts}
        safe=errors.sanitize_error_telemetry(value)
        self.assertLessEqual(len(json.dumps(safe['reason_counts'],separators=(',',':')).encode()), errors.MAX_CURRENT_REASON_BYTES)
        self.assertEqual(sum(safe['reason_counts'].values()),sum(counts.values()))
        self.assertEqual(errors.sanitize_error_telemetry(safe),safe)
        old={'status':'available','reason_counts':dict.fromkeys(errors.LEGACY_ERROR_REASONS,7)}
        self.assertEqual(errors.sanitize_error_telemetry(old)['reason_counts'],old['reason_counts'])


if __name__=='__main__':
    unittest.main()
