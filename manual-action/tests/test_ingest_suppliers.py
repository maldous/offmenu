"""Generated fixture-only supplier/place tests; never read live retained sources."""
import csv
import bz2
import gzip
import io
import json
import lzma
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from ingest_api import BudgetExceeded
from ingest_store import DomainStore
import ingest_suppliers as suppliers


class Context:
    def __init__(self, root, config=None):
        self.config = {'batch_size': 2, 'reserve_bytes': 0, **(config or {})}
        self.state_dir = root
        self.cancelled = threading.Event()
        self.errors = []
        self.store = DomainStore('suppliers', root, self.config)

    def check_budget(self):
        pass

    def ingest(self, source, records):
        return self.store.ingest(source, records)

    def report_error(self, source, exc):
        self.errors.append(type(exc).__name__)
        self.store.record_error(source, exc)


def native(index=1):
    return {'schemaVersion': '1.0', 'kind': 'organization',
            'id': 'wikidata-food-businesses:organization:Q' + str(index),
            'countries': ['ZZ'],
            'provenance': {'sourceId': 'wikidata-food-businesses',
                           'releaseId': '2026-10-13-direct-types',
                           'recordId': 'Q' + str(index), 'license': 'CC0 1.0',
                           'visibility': 'public'},
            'data': {'name': '  Generated Ω organization  ',
                     'roles': ['supermarket-chain'],
                     'countryBasis': 'Fixture assertion, not a location',
                     'identifiers': [{'system': 'Wikidata', 'value': 'Q' + str(index)}],
                     'unmapped': {'preserve': ['unknown source field']}}}


class SupplierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = Context(self.root / 'state')

    def tearDown(self):
        self.context.store.close()
        self.temp.cleanup()

    def source(self, name, payload, **kwargs):
        path = self.root / name
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        elif isinstance(payload, str):
            path.write_text(payload, encoding='utf-8')
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return {'id': name, 'path': str(path), 'format': name.split('.')[1],
                'domain': 'suppliers', **kwargs}

    def run_sources(self, sources):
        return suppliers.run_domain('suppliers', sources, self.context)

    def records(self):
        return [json.loads(row[0]) for row in self.context.store.db.execute(
            'SELECT payload_json FROM records ORDER BY row_number,record_id')]

    def test_native_singleton_gzip_preserves_assertions_and_repeated_ids(self):
        row = native()
        source = self.source('native.jsonl.gz', gzip.compress(
            (json.dumps([row]) + '\n' + json.dumps([row]) + '\n').encode()), provider='wikidata')
        report = self.run_sources([source])
        self.assertEqual((report['status'], report['written']), ('complete', 2))
        records = self.records()
        self.assertEqual(records[0]['source_payload'], row)
        self.assertEqual(records[0]['name'], '  Generated Ω organization  ')
        self.assertEqual(records[0]['type'], 'organization')
        self.assertEqual(records[0]['entity_id'], 'Q1')
        self.assertEqual(records[0]['country_basis'], row['data']['countryBasis'])
        self.assertIsNone(records[0]['legal_name'])
        self.assertIsNone(records[0]['address'])
        self.assertEqual(records[0]['relations'], [])
        self.assertNotIn('stock', records[0])
        repeat = self.run_sources([source])
        self.assertEqual((repeat['written'], repeat['unchanged']), (0, 2))
        self.assertEqual(len(self.records()), 2)

    def test_mixed_sources_places_never_become_suppliers_or_owners(self):
        organization = self.source('companies.csv',
            'entity_id,name,legal_name,website,country\nC1,Shop,Shop Limited,https://example.invalid,ZZ\n',
            provider='company-registry')
        places = self.source('places.json', {'places': [
            {'id': 'p1', 'type': 'place', 'names': {'primary': 'Fixture restaurant'},
             'websites': ['https://place.invalid'],
             'addresses': [{'freeform': '1 Fixture Road', 'country': 'ZZ'}],
             'categories': {'primary': 'restaurant'}, 'brand': 'Not proof of ownership'}]},
            provider='overture')
        ownership = self.source('ownership.tsv',
            'subject_id\tpredicate\tobject_id\nC1\tP127\tC2\n', kind='company_ownership')
        report = self.run_sources([organization, places, ownership])
        self.assertEqual(report['written'], 3)
        by_type = {row['type']: row for row in self.records()}
        self.assertEqual(by_type['food_place']['relations'], [])
        self.assertEqual(by_type['food_place']['address'], '1 Fixture Road')
        self.assertEqual(by_type['organization']['legal_name'], 'Shop Limited')
        self.assertEqual(by_type['company_ownership']['relations'][0]['target_id'], 'C2')
        links = self.context.store.db.execute('SELECT kind,target_id FROM relations').fetchall()
        self.assertEqual(links, [('owned_by', 'C2')])

    def test_deprecated_records_and_claims_not_asserted_as_active(self):
        row = {'id': 'Q1', 'labels': {'en': {'value': 'Fixture'}}, 'claims': {
            'P127': [
                {'rank': 'deprecated', 'mainsnak': {'datavalue': {'value': {'id': 'Q2'}}}},
                {'rank': 'normal', 'mainsnak': {'datavalue': {'value': {'id': 'Q3'}}}},
                {'rank': 'normal', 'mainsnak': {'snaktype': 'novalue'}}],
            'P856': [{'mainsnak': {'datavalue': {'value': 'https://example.invalid'}}}]}}
        source = self.source('claims.jsonl', '\n'.join(map(json.dumps, [
            {'id': 'Q9', 'deprecated': True}, row])) + '\n', provider='wikidata')
        report = self.run_sources([source])
        self.assertEqual((report['written'], report['skipped']), (1, 1))
        record = self.records()[0]
        self.assertEqual([link['target_id'] for link in record['relations']], ['Q3'])
        self.assertEqual(record['source_payload'], row)
        self.assertEqual(record['website'], 'https://example.invalid')

    def test_malformed_row_and_file_are_isolated_and_errors_durable(self):
        mixed = self.source('mixed.jsonl',
            '{"id":"Q1","name":"Good"}\nnot-json\n'
            '{"id":"Q2","name":"Also good"}\n')
        broken = self.source('broken.json', '{"companies": [ invalid ]}')
        final = self.source('final.json', [{'id': 'Q3', 'name': 'Later file'}])
        report = self.run_sources([mixed, broken, final])
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['written'], 3)
        self.assertEqual(report['errors'], 2)
        self.assertEqual(report['sources'][0]['status'], 'partial')
        repeat = self.run_sources([mixed])
        self.assertEqual(repeat['written'], 0)
        self.assertEqual(repeat['status'], 'partial')
        self.assertEqual(repeat['errors'], 1)

    def test_incomplete_planet_loaded_and_restricted_never_opened(self):
        sources = [
            {'id': 'planet', 'path': '/nonexistent/planet.osm.pbf.part', 'format': 'pbf',
             'provider': 'osm', 'incomplete': True},
            {'id': 'loaded', 'path': '/nonexistent/loaded.jsonl', 'format': 'jsonl',
             'provider': 'wikidata', 'loaded': True},
            {'id': 'private', 'path': '/nonexistent/restricted.jsonl', 'format': 'jsonl',
             'restricted': True}]
        with mock.patch.object(suppliers, '_binary', side_effect=AssertionError('must not read')):
            report = self.run_sources(sources)
        self.assertEqual([x['reason'] for x in report['sources']],
                         ['incomplete_source', 'already_loaded', 'restricted_input'])
        self.assertEqual(report['written'], 0)

    def test_loaded_only_is_complete_without_reimport(self):
        report = self.run_sources([{'id': 'loaded', 'path': '/not/opened',
                                   'format': 'parquet', 'loaded': True}])
        self.assertEqual(report['status'], 'complete')

    def test_sqlite_reads_original_packet_not_duplicate_actor_and_never_writes(self):
        path = self.root / 'native.sqlite'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE retained_reference_record(source_payload_json TEXT)')
        db.execute('INSERT INTO retained_reference_record VALUES(?)', (json.dumps([native()]),))
        db.execute('CREATE TABLE supplier_source_actor(name TEXT)')
        db.execute('INSERT INTO supplier_source_actor VALUES("derived copy")')
        db.commit()
        db.close()
        before = path.read_bytes()
        report = self.run_sources([{'id': 'sqlite', 'path': str(path), 'format': 'sqlite'}])
        self.assertEqual(report['written'], 1)
        self.assertEqual(self.records()[0]['entity_id'], 'Q1')
        self.assertEqual(path.read_bytes(), before)

    def test_sqlite_explicit_table_identifier_is_quoted_not_executed(self):
        path = self.root / 'quoted.sqlite'
        table = 'companies"; DROP TABLE companies;--'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE "' + table.replace('"', '""') + '" (id TEXT,name TEXT)')
        db.execute('INSERT INTO "' + table.replace('"', '""') + '" VALUES("C1","Fixture")')
        db.commit()
        db.close()
        report = self.run_sources([{'id': 'quoted', 'path': str(path), 'format': 'sqlite', 'table': table}])
        self.assertEqual(report['written'], 1)

    def test_json_wrapper_streams_large_array_larger_than_row_limit(self):
        source = self.source('wrapped.json', {'results': {'bindings': [
            {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q' + str(i)},
             'itemLabel': {'value': 'Generated ' + 'x' * 100}} for i in range(200)]}})
        self.context.config['max_record_bytes'] = 2048
        self.assertGreater(Path(source['path']).stat().st_size, 2048)
        report = self.run_sources([source])
        self.assertEqual(report['written'], 200)
        self.assertEqual(report['errors'], 0)

    def test_json_data_array_wrapper_and_geojson_properties(self):
        source = self.source('data.json', {'data': [{'id': 'C1', 'name': 'Fixture'}]})
        geo = self.source('geo.json', {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'id': 'p1', 'properties': {'name': 'Place'},
             'geometry': {'type': 'Point', 'coordinates': [0, 1]}}]}, provider='overture')
        report = self.run_sources([source, geo])
        self.assertEqual(report['written'], 2)
        self.assertEqual({record['name'] for record in self.records()}, {'Fixture', 'Place'})

    def test_oversized_line_is_drained_and_later_row_survives(self):
        self.context.config['max_record_bytes'] = 1024
        source = self.source('large.jsonl',
            json.dumps({'id': 'large', 'name': 'x' * 3000}) + '\n' +
            json.dumps({'id': 'small', 'name': 'Fits'}) + '\n')
        report = self.run_sources([source])
        self.assertEqual((report['written'], report['errors']), (1, 1))
        self.assertEqual(self.records()[0]['name'], 'Fits')

    def test_duplicate_keys_nonfinite_and_wrong_shape_are_row_errors(self):
        source = self.source('invalid.jsonl',
            '{"id":"a","id":"b"}\n{"id":"a","value":NaN}\n'
            '{"id":"a","value":1e999}\n42\n{"id":"good"}\n')
        report = self.run_sources([source])
        self.assertEqual((report['written'], report['errors']), (1, 4))

    def test_bad_csv_row_does_not_block_later_row(self):
        source = self.source('columns.csv', 'id,name\nbad,too,many\ngood,Fixture\n')
        report = self.run_sources([source])
        self.assertEqual((report['written'], report['errors']), (1, 1))

    def test_missing_parquet_dependency_is_explicit_skip_and_next_source_runs(self):
        source = self.source('places.parquet', b'not read without dependency', provider='overture')
        good = self.source('good.json', [{'id': 'Q1'}])
        with mock.patch.dict(sys.modules, {'pyarrow': None, 'pyarrow.parquet': None}):
            report = self.run_sources([source, good])
        self.assertEqual(report['sources'][0]['reason'], 'parquet_dependency_unavailable')
        self.assertEqual(report['written'], 1)

    def test_installed_parquet_can_preserve_wkb_and_place_kind(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest('optional installed-only pyarrow unavailable')
        path = self.root / 'places.parquet'
        pq.write_table(pa.Table.from_pylist([{'id': 'p1', 'name': 'Fixture', 'geometry': b'\x00\x01'}]), path)
        report = self.run_sources([{'id': 'pq', 'path': str(path), 'format': 'parquet', 'provider': 'overture'}])
        self.assertEqual(report['written'], 1)
        self.assertEqual(self.records()[0]['type'], 'food_place')
        self.assertEqual(self.records()[0]['source_payload']['geometry'], {'encoding': 'hex', 'value': '0001'})

    def test_symlink_refusal_does_not_block_next_source(self):
        good = self.source('good.json', [{'id': 'C1'}])
        link = self.root / 'link.json'
        link.symlink_to(good['path'])
        report = self.run_sources([{'id': 'link', 'path': str(link), 'format': 'json'}, good])
        self.assertEqual(report['sources'][0]['status'], 'failed')
        self.assertEqual(report['written'], 1)

    def test_cancelled_respects_budget_without_accepting_record(self):
        self.context.cancelled.set()
        source = self.source('cancel.json', [{'id': 'C1'}])
        report = self.run_sources([source])
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['written'], 0)

    def test_no_owner_inference_from_organization_name_brand_or_roles(self):
        row = {'id': 'Q1', 'name': 'Owned By Fictional Holding',
               'brand': {'name': 'Fixture Parent'}, 'roles': ['manufacturer']}
        normalized = suppliers.normalize_record(row, {'id': 'fixture'}, 'row:1')
        self.assertEqual(normalized['relations'], [])
        self.assertIsNone(normalized['legal_name'])

    def test_price_observations_not_organizations_live_offers_or_inventory(self):
        row = {'id': 'obs1', 'product_code': '00123', 'price': 2.5,
               'currency': 'ZZZ', 'date': '2000-01-01', 'location_id': 'place1'}
        source = self.source('prices.jsonl', json.dumps(row) + '\n',
                             provider='open-prices', kind='price_observation')
        report = self.run_sources([source])
        self.assertEqual(report['written'], 1)
        record = self.records()[0]
        self.assertEqual(record['type'], 'price_observation')
        self.assertEqual(record['observed_price'], '2.5')
        self.assertEqual(record['observation_status'], 'source_observation_not_live_offer')
        self.assertEqual(record['relations'], [])
        self.assertNotIn('stock', record)
        self.assertEqual(record['source_payload'], row)

    def test_ownership_edge_id_never_substituted_for_missing_subject(self):
        source = self.source('edge.jsonl', json.dumps(
            {'id': 'edge-1', 'predicate': 'P127', 'object_id': 'Q2'}) + '\n',
            kind='company_ownership')
        report = self.run_sources([source])
        self.assertEqual((report['written'], report['errors']), (0, 1))

    def test_stdlib_compressed_text_formats(self):
        raw = (json.dumps({'id': 'Q1'}) + '\n').encode()
        bzip = self.source('bzip.jsonl.bz2', bz2.compress(raw), compression='bz2')
        xzip = self.source('xzip.jsonl.xz', lzma.compress(raw), compression='xz')
        report = self.run_sources([bzip, xzip])
        self.assertEqual((report['written'], report['errors']), (2, 0))

    def test_truncated_gzip_never_reports_complete_and_other_provider_continues(self):
        raw = (json.dumps({'id': 'Q1'}) + '\n').encode()
        bad = self.source('bad.jsonl.gz', gzip.compress(raw)[:-6])
        good = self.source('good.json', [{'id': 'Q2'}])
        report = self.run_sources([bad, good])
        self.assertNotEqual(report['sources'][0]['status'], 'complete')
        self.assertFalse(report['sources'][0]['completed'])
        self.assertEqual(report['sources'][1]['written'], 1)

    def test_csv_multiline_fields_are_preserved(self):
        source = self.source('multiline.csv', 'id,name\nQ1,"Line 1\nLine 2"\n')
        report = self.run_sources([source])
        self.assertEqual(report['written'], 1)
        self.assertEqual(self.records()[0]['name'], 'Line 1\nLine 2')


if __name__ == '__main__':
    unittest.main()
