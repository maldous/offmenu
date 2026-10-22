"""Generated retained-format fixtures only; no real personal or retained data."""
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_misc as m
from ingest_api import BudgetExceeded
from ingest_store import DomainStore


class Context:
    def __init__(self, store):
        self.store = store
        self.config = {}
        self.cancelled = threading.Event()
        self.errors = []
        self.events = []

    def check_budget(self):
        if self.cancelled.is_set():
            raise BudgetExceeded('cancelled')

    def report_error(self, source, exc):
        self.errors.append(type(exc).__name__)
        if hasattr(self.store, 'record_error'):
            self.store.record_error(source, exc)

    def progress(self, **counts):
        self.events.append(counts)

    def ingest(self, source, records):
        return self.store.ingest(source, records)


class MiscIngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'

    def tearDown(self):
        self.temp.cleanup()

    def source(self, name, body, **kwargs):
        path = self.root / name
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding='utf-8')
        return dict(id=name, path=str(path), **kwargs)

    def run_adapter(self, domain, sources, config=None):
        with DomainStore(domain, self.state, {'batch_size': 2, **(config or {})}) as store:
            context = Context(store)
            context.config = config or {}
            result = m.run_domain(domain, sources, context)
            rows = [json.loads(r[0]) for r in store.db.execute('SELECT payload_json FROM records ORDER BY row_number,record_id')]
            return result, rows, context

    @staticmethod
    def nutrient(identifier='food:1', value=None, unit='mg'):
        return {'schemaVersion': '1.0', 'kind': 'nutrientProfile', 'id': identifier,
                'provenance': {'sourceId': 'cnf', 'license': 'Generated fixture',
                               'url': 'https://example.invalid/fixture'},
                'data': {'foodName': 'Generated food', 'basis': {'amount': 100, 'unit': 'g'},
                         'nutrients': {'iron': {'value': value, 'unit': unit,
                                               'qualifier': 'unknown' if value is None else 'source'}}}}

    def test_native_gzip_mixed_lines_duplicate_unknown_and_conflicting_units(self):
        row = self.nutrient()
        other = self.nutrient(value='<0.3', unit='µg')
        lines = [json.dumps([row]), '{invalid}', json.dumps([row]),
                 '{"kind":"nutrientProfile","unit":"mg","unit":"g"}',
                 json.dumps(['generated-partition', [other]])]
        source = self.source('normalized.jsonl.gz', gzip.compress(('\n'.join(lines) + '\n').encode()))
        result, rows, context = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 2)
        self.assertEqual(result['unchanged'], 1)
        self.assertEqual(result['errors'], 2)
        self.assertEqual(result['source_files'], 1)
        self.assertEqual(result['documents'], 5)
        self.assertEqual(result['records'], 3)
        self.assertEqual(len(rows), 2)
        facts = [r['source_fields']['data']['nutrients']['iron'] for r in rows]
        self.assertIn({'value': None, 'unit': 'mg', 'qualifier': 'unknown'}, facts)
        self.assertIn({'value': '<0.3', 'unit': 'µg', 'qualifier': 'source'}, facts)
        self.assertTrue(all(r['automatic_diet_qualification'] is False for r in rows))
        self.assertEqual(sorted(context.errors), ['DuplicateField', 'JSONDecodeError'])
        self.assertNotIn('Generated food', json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_bad_file_does_not_stop_other_files_and_unknown_rows_not_loaded(self):
        broken = self.source('bad.json', '{bad')
        unsupported = self.source('opaque.pdf', b'%PDF-not-an-actual-document')
        unknown = self.source('unknown.json', '{"patient_id":"synthetic","diagnosis":"synthetic"}')
        good = self.source('good.json', json.dumps([self.nutrient()]))
        result, rows, context = self.run_adapter('dietary', [broken, unsupported, unknown, good])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['source_files'], 4)
        self.assertEqual(result['unsupported_sources'], 2)
        self.assertGreaterEqual(result['errors'], 1)
        self.assertEqual(result['sources'][-1]['status'], 'complete')

    def test_csv_missing_values_stay_empty_bad_width_skipped_duplicate_header_rejected(self):
        good = self.source('nutrients.csv', 'food_id,nutrient,value,unit\n001,protein,,g\nwrong,width\n002,iron,<0.3,mg\n')
        bad = self.source('duplicate.csv', 'nutrient,value,unit,unit\nprotein,4,g,mg\n')
        result, rows, context = self.run_adapter('dietary', [good, bad])
        self.assertEqual(len(rows), 2)
        self.assertEqual(result['errors'], 2)
        self.assertEqual(rows[0]['source_fields']['food_id'], '001')
        self.assertEqual(rows[0]['source_fields']['value'], '')
        self.assertEqual(rows[1]['source_fields']['value'], '<0.3')

    def test_fineli_raw_and_native_flags_do_not_become_qualifications(self):
        raw = self.source('specdiet.tsv', 'FOODID\tSPECDIET\n001\tGLUTFREE\n', provider='fineli')
        definition = self.source('specdiet_EN.csv', 'THSCODE;DESCRIPT\nGLUTFREE;Generated label\n', provider='fineli', delimiter=';')
        native = {'kind': 'sourceAssertion', 'id': 'fineli:sourceAssertion:1:x',
                  'provenance': {'sourceId': 'fineli'},
                  'data': {'predicate': 'source-diet-tag', 'value': 'x',
                           'sourceLabel': 'Generated label', 'qualificationStatus': 'unknown'}}
        norm = self.source('flags.jsonl', json.dumps([native]) + '\n')
        result, rows, _ = self.run_adapter('dietary', [raw, definition, norm])
        self.assertEqual(result['written'], 3)
        self.assertTrue(all(r['automatic_diet_qualification'] is False for r in rows))
        self.assertEqual(rows[-1]['source_fields']['data']['qualificationStatus'], 'unknown')

    def test_common_graph_keeps_asserted_units_citations_and_no_conversion(self):
        packet = {'schemaVersion': 'offmenu-common/1',
                  'resources': [{'id': 'generated:food', 'type': 'urn:offmenu:type:FoodCompositionObservation'}],
                  'assertions': [{'value': {'kind': 'quantity', 'sourceUnit': 'kJ', 'value': None}}],
                  'relations': [], 'citations': [{'id': 'generated:cite', 'sourceId': 'mext', 'license': 'fixture'}],
                  'translations': []}
        source = self.source('graph.jsonl', json.dumps(packet) + '\n')
        dietary, facts, _ = self.run_adapter('dietary', [source])
        citations, refs, _ = self.run_adapter('citations', [source])
        self.assertEqual(dietary['written'], 1)
        self.assertEqual(facts[0]['source_fields'], packet)
        self.assertEqual(citations['written'], 1)
        self.assertNotIn('assertions', refs[0]['reference'])

    def test_manifest_reference_metadata_only_with_parent_digest_separate(self):
        manifest = {'schemaVersion': 'offmenu-collection/1', 'sourceId': 'generated',
                    'releaseId': 'fixture-1', 'license': 'Fixture-only',
                    'archiveSha256': 'a' * 64, 'completedAt': '2026-01-01T00:00:00Z',
                    'files': [{'key': 'part.jsonl.gz', 'sha256': 'b' * 64, 'bytes': 30,
                               'data': {'nutrients': {'iron': 999}}, 'raw_text': 'never-copy'}],
                    'sources': {'publisher': {'title': 'Synthetic publisher',
                                             'url': 'https://example.invalid/publisher'}},
                    'data': {'credentials': 'not-a-real-credential'}}
        source = self.source('manifest.json', json.dumps(manifest))
        result, rows, _ = self.run_adapter('citations', [source])
        self.assertEqual(result['written'], 3)
        self.assertEqual(result['documents'], 1)
        child = next(r for r in rows if r['reference'].get('key') == 'part.jsonl.gz')
        self.assertEqual(child['reference']['sha256'], 'b' * 64)
        self.assertNotIn('archiveSha256', child['reference'])
        self.assertEqual(child['parent_reference']['archiveSha256'], 'a' * 64)
        self.assertNotIn('never-copy', json.dumps(rows))
        self.assertNotIn('credentials', json.dumps(rows))
        self.assertNotIn('nutrients', json.dumps(rows))

    def test_citation_provenance_from_native_record_without_raw_fact_duplication(self):
        source = self.source('records.jsonl', json.dumps([self.nutrient()]) + '\n')
        result, rows, _ = self.run_adapter('citations', [source])
        self.assertEqual(result['written'], 1)
        self.assertEqual(rows[0]['reference']['sourceId'], 'cnf')
        self.assertNotIn('nutrients', json.dumps(rows))
        self.assertNotIn('foodName', json.dumps(rows))

    def test_readonly_sqlite_tables_json_payload_and_resume(self):
        path = self.root / 'retained.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE nutrients(id INTEGER PRIMARY KEY, food_id TEXT, nutrient TEXT, value TEXT, unit TEXT)')
            db.execute("INSERT INTO nutrients VALUES(1,'001','iron',NULL,'mg')")
            db.execute('CREATE TABLE records(id TEXT PRIMARY KEY, payload_json TEXT)')
            db.execute('INSERT INTO records VALUES(?,?)', ('fixture', json.dumps(self.nutrient('fixture:2', 0))))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        source = dict(id='db', path=str(path), format='sqlite')
        result, rows, _ = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 2)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        again, rows2, _ = self.run_adapter('dietary', [source])
        self.assertEqual(again['written'], 0)
        self.assertEqual(again['unchanged'], 2)
        self.assertEqual(len(rows2), 2)
        self.assertTrue(again['sources'][0]['already_complete'])

    def test_restricted_and_loaded_are_never_read(self):
        sources = [dict(id='restricted', path=str(self.root / 'absent'), restricted=True),
                   dict(id='loaded', path=str(self.root / 'absent2'), loaded=True)]
        result, rows, _ = self.run_adapter('dietary', sources)
        self.assertEqual(result['skipped'], 2)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(rows, [])

    def test_cancellation_propagates(self):
        with DomainStore('dietary', self.state) as store:
            context = Context(store)
            context.cancelled.set()
            with self.assertRaises(BudgetExceeded):
                m.run_domain('dietary', [dict(id='absent', path='absent')], context)

    def test_large_json_array_streams_and_trailing_data_rejected(self):
        array = [self.nutrient(str(n), n) for n in range(300)]
        source = self.source('large.json', json.dumps(array))
        result, rows, _ = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 300)
        self.assertEqual(result['documents'], 300)
        extra = self.source('trailing.json', json.dumps(array[:1]) + 'NOT_JSON')
        result2, _, _ = self.run_adapter('dietary', [extra])
        self.assertEqual(result2['errors'], 1)
        self.assertEqual(result2['written'], 1)

    def test_nonfinite_is_not_silently_promoted(self):
        source = self.source('nonfinite.jsonl', '{"kind":"nutrientProfile","value":NaN}\n' +
                             '{"kind":"nutrientProfile","value":1e999}\n' + json.dumps(self.nutrient()) + '\n')
        result, rows, _ = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 1)
        self.assertEqual(result['errors'], 2)


    def test_complete_with_parse_errors_keeps_same_counts_on_resume(self):
        source = self.source('parse-error.jsonl', '{invalid}\n' + json.dumps(self.nutrient()) + '\n')
        first, rows, _ = self.run_adapter('dietary', [source])
        again, rows2, _ = self.run_adapter('dietary', [source])
        self.assertEqual(first['errors'], 1)
        self.assertEqual(again['errors'], 1)
        self.assertEqual(again['written'], 0)
        self.assertEqual(again['unchanged'], 1)
        self.assertEqual(again['status'], 'partial')
        self.assertEqual(rows, rows2)

    def test_catalog_holds_do_not_open_missing_paths(self):
        dispositions = ['existing-store', 'incomplete-hold', 'duplicate',
                        'documentation', 'excluded', 'historical-demo']
        sources = [dict(id=value, path=str(self.root / value), disposition=value)
                   for value in dispositions]
        result, rows, _ = self.run_adapter('dietary', sources)
        self.assertEqual(result['skipped'], len(dispositions))
        self.assertEqual(result['errors'], 0)
        self.assertEqual(rows, [])

    def test_cached_structured_records_and_autodetected_semicolon(self):
        cache = self.source('parsed-cache.json', json.dumps({'schemaVersion': 'fixture-parsed-cache/1',
                                                          'records': [self.nutrient()]}))
        raw = self.source('specdiet.csv', 'FOODID;SPECDIET\n001;GENERATED\n', provider='fineli')
        result, rows, _ = self.run_adapter('dietary', [cache, raw])
        self.assertEqual(result['written'], 2)
        self.assertEqual(len(rows), 2)



    def test_malformed_packet_member_keeps_following_sibling(self):
        source = self.source('siblings.jsonl', json.dumps([self.nutrient('one'),
                                                         'not-a-record', self.nutrient('two')]) + '\n')
        result, rows, _ = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 2)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(len(rows), 2)

    def test_decimal_lexeme_is_exact_even_when_numeric_index_is_rounded(self):
        source = self.source('precision.jsonl', '{"kind":"nutrientProfile","id":"fixture",'
                             '"data":{"foodName":"Generated","nutrients":{"iron":'
                             '{"value":0.123456789012345678901,"unit":"mg"}}}}\n')
        result, rows, _ = self.run_adapter('dietary', [source])
        self.assertEqual(result['written'], 1)
        self.assertEqual(rows[0]['source_numeric_lexemes']['/data/nutrients/iron/value'],
                         '0.123456789012345678901')

    def test_symlink_leaf_and_parent_refused_without_blocking_good_file(self):
        good = self.source('good.jsonl', json.dumps(self.nutrient()) + '\n')
        leaf = self.root / 'link.jsonl'
        leaf.symlink_to(good['path'])
        parent = self.root / 'alias'
        parent.symlink_to(self.root, target_is_directory=True)
        result, rows, _ = self.run_adapter('dietary', [dict(id='leaf', path=str(leaf)),
            dict(id='parent', path=str(parent / 'good.jsonl')), good])
        self.assertEqual(result['errors'], 2)
        self.assertEqual(result['written'], 1)
        self.assertEqual(len(rows), 1)

    def test_parse_error_before_row_cap_is_not_counted_again_on_resume(self):
        source = self.source('capped.jsonl', '{bad}\n' + json.dumps(self.nutrient('one')) +
                             '\n' + json.dumps(self.nutrient('two')) + '\n')
        first, rows, _ = self.run_adapter('dietary', [source], {'max_rows_per_source': 1})
        second, rows2, _ = self.run_adapter('dietary', [source])
        self.assertEqual(first['written'], 1)
        self.assertEqual(second['written'], 1)
        self.assertEqual(second['errors'], 1)
        self.assertEqual(len(rows2), 2)


if __name__ == '__main__':
    unittest.main()
