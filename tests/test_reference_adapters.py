"""Authored synthetic inputs only; no downloads or production fixtures."""
import copy
import importlib.util
import json
import hashlib
import jsonschema
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'offmenu/refresh/reference_adapters.py'
spec = importlib.util.spec_from_file_location('reference_adapters', PATH)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
STAMP = '2026-10-13T12:00:00Z'


def normalize(source, value):
    payload = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
    records = a.normalize_reference(source, a.CONTRACTS[source][0], payload, acquired_at=STAMP)
    schema = json.loads((PATH.parents[2] / 'schemas/reference-candidate.schema.json').read_text())
    for record in records:
        jsonschema.Draft202012Validator(schema).validate(record)
        assert a.reference_semantics(record) == []
    return records


def binding(q='Q1', kind='Q1252971', label='Example'):
    return {'entity': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/' + q},
            'type': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/' + kind},
            'entityLabel': {'type': 'literal', 'xml:lang': 'en', 'value': label}}


def place():
    return {'id': 'synthetic-place', 'names': {'primary': 'Example shop'},
            'taxonomy': {'hierarchy': ['food_and_beverage_store']},
            'sources': [{'dataset': 'provider-a', 'license': 'Apache-2.0'},
                        {'dataset': 'provider-b', 'license': 'CDLA-Permissive-2.0'}],
            'addresses': [{'country': 'GB', 'locality': 'Example'}]}


class ReferenceTests(unittest.TestCase):
    def test_wikidata_deterministic_aggregation_and_originals(self):
        document = {'results': {'bindings': [binding(), binding(kind='Q18043413')]}}
        original = copy.deepcopy(document)
        rows = normalize('wikidata-food-businesses', document)
        self.assertEqual(rows, normalize('wikidata-food-businesses', document))
        self.assertEqual(document, original)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['data']['roles'], ['food-manufacturer', 'supermarket-chain'])
        self.assertEqual(rows[0]['data']['originalBindings'], document['results']['bindings'])
        self.assertFalse(rows[0]['data']['ownershipVerified'])
        self.assertEqual(rows[0]['countries'], [])
        self.assertEqual(json.loads(a.candidate_bytes(rows)), rows)

    def test_wikidata_unknown_type_and_spoofed_uri(self):
        for item in [binding(kind='Q2'), {**binding(), 'entity': {'value': 'https://evil.test/Q1'}}]:
            with self.assertRaises(a.ReferenceFormatError):
                normalize('wikidata-food-businesses', {'results': {'bindings': [item]}})

    def test_wikibooks_revision_and_original_whitespace(self):
        text = '== Ingredients ==\r\n* 1½ cups flour\r\n\n'
        page = {'pageid': 1, 'title': 'Cookbook:Example', 'revisions': [
            {'revid': 7, 'timestamp': STAMP, 'slots': {'main': {'content': text}}}]}
        result = normalize('wikibooks', [page])[0]
        self.assertEqual(result['data']['originalText'], text)
        self.assertEqual(result['data']['originalSource'], page)
        self.assertFalse(result['data']['automaticPlanningEligible'])
        self.assertEqual(result['provenance']['licenses'], ['CC-BY-SA-4.0'])
        with self.assertRaises(a.ReferenceFormatError):
            normalize('wikibooks', [page, page])
        page['revisions'] = []
        with self.assertRaises(a.ReferenceFormatError):
            normalize('wikibooks', [page])

    def test_foodon_exact_lexical_source_and_namespace_filter(self):
        child = '<owl:Class rdf:about="http://purl.obolibrary.org/obo/FOODON_1"><p:value rdf:datatype="decimal">1.00000000000000000001</p:value><p:text>A &amp; B</p:text><p:expr><p:nested/></p:expr></owl:Class>'
        xml = ('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#" xmlns:p="urn:example:">' + child + '<owl:Class rdf:about="http://purl.obolibrary.org/obo/OTHER_1"/></rdf:RDF>').encode()
        rows = normalize('foodon', xml)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['data']['originalXml'], child)
        self.assertEqual(rows[0]['data']['namespaceDeclarations']['p'], 'urn:example:')
        self.assertFalse(rows[0]['data']['foodIdentityEquivalenceInferred'])
        for bad in [b'<!DOCTYPE x [<!ENTITY y "bad">]><x/>', b'<xml/>']:
            with self.assertRaises(a.ReferenceFormatError):
                normalize('foodon', bad)

    def test_foodon_self_closing(self):
        xml = b'<r:RDF xmlns:r="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:o="http://www.w3.org/2002/07/owl#"><o:Class r:about="http://purl.obolibrary.org/obo/FOODON_1"/></r:RDF>'
        row = normalize('foodon', xml)[0]
        self.assertEqual(row['data']['originalXml'], '<o:Class r:about="http://purl.obolibrary.org/obo/FOODON_1"/>')

    def test_qudt_bounded_lexical_preservation(self):
        ttl = b'@prefix unit: <http://qudt.org/vocab/unit/> .\n@prefix qudt: <http://qudt.org/schema/qudt/> .\nunit:GM qudt:conversionMultiplier 0.00100000000000000001 .\nunit:UNSELECTED qudt:conversionMultiplier 1 .\n'
        rows = normalize('qudt-measurement-definitions', ttl)
        self.assertEqual(len(rows), 1)
        self.assertIn('0.00100000000000000001', rows[0]['data']['originalTurtleBlock'])
        self.assertFalse(rows[0]['data']['densityOrYieldEquivalenceInferred'])
        with self.assertRaises(a.ReferenceFormatError):
            normalize('qudt-measurement-definitions', ttl.replace(b'unit:', b'u:'))

    def test_overture_mixed_provider_licenses_preserved(self):
        original = place()
        row = normalize('overture-food-places', [original])[0]
        self.assertEqual(row['data']['originalSource'], original)
        self.assertEqual(row['provenance']['licenses'], ['Apache-2.0', 'CDLA-Permissive-2.0'])
        self.assertEqual(row['data']['sourceProviders'], original['sources'])
        self.assertFalse(row['data']['menuCoverage'])
        self.assertEqual(row['countries'], [])

    def test_overture_rights_fail_closed(self):
        for sources in [[], [{'license': 'unknown'}], [{'dataset': 'no-license'}]]:
            item = place(); item['sources'] = sources
            with self.assertRaises(a.ReferenceFormatError):
                normalize('overture-food-places', [item])
        item = place(); item['geometry'] = {}
        with self.assertRaises(a.ReferenceFormatError):
            normalize('overture-food-places', [item])

    def test_overture_filters_do_not_claim_menu_coverage(self):
        excluded = place(); excluded['taxonomy']['hierarchy'].append('tobacco_shop')
        with self.assertRaises(a.ReferenceFormatError):
            normalize('overture-food-places', [excluded])

    def test_json_decimal_lexical_values_retained(self):
        data = json.dumps([place()]).replace('"id":', '"confidence": 0.123456789012345678901, "id":').encode()
        row = normalize('overture-food-places', data)[0]
        self.assertEqual(row['data']['originalSource']['confidence'], {'sourceNumberLexical': '0.123456789012345678901'})

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        for data in [b'{"results": {}, "results": {}}', b'{"x": NaN}']:
            with self.assertRaises(a.ReferenceFormatError):
                normalize('wikidata-food-businesses', data)

    def test_semantic_guard_rejects_inference_and_rights_promotion(self):
        row = normalize('overture-food-places', [place()])[0]
        row['data']['menuCoverage'] = True
        self.assertIn('reference-place-inference', a.reference_semantics(row))
        row['provenance']['authorizedOperations'] = ['export']
        self.assertIn('reference-self-authorized-rights', a.reference_semantics(row))
        row['provenance']['licenses'] = ['CC0-1.0']
        self.assertIn('reference-provider-rights-mismatch', a.reference_semantics(row))

    def test_output_and_record_limits(self):
        document = {'results': {'bindings': [binding()]}}
        for name, limit in [('MAX_RECORD_BYTES', 10), ('MAX_CANDIDATE_BYTES', 10), ('MAX_RECORDS', 0)]:
            with patch.object(a, name, limit), self.assertRaises(a.ReferenceFormatError):
                normalize('wikidata-food-businesses', document)

    def test_manifest_pins_and_candidate_digest(self):
        payload = json.dumps([place()]).encode()
        records = normalize('overture-food-places', payload)
        inputs = [{'path': 'projection/part.json', 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}]
        kwargs = {'acquired_at': STAMP, 'input_files': inputs, 'rights_evidence_sha256': 'a' * 64, 'scope_evidence_sha256': 'b' * 64}
        manifest = a.candidate_manifest('overture-food-places', a.CONTRACTS['overture-food-places'][0], records, **kwargs)
        self.assertEqual(manifest['candidateSha256'], hashlib.sha256(a.candidate_bytes(records)).hexdigest())
        self.assertFalse(manifest['productionAdmission'])
        inputs[0]['path'] = '../escape'
        with self.assertRaises(a.ReferenceFormatError):
            a.candidate_manifest('overture-food-places', a.CONTRACTS['overture-food-places'][0], records, **kwargs)
        inputs[0]['path'] = 'projection/part.json'; inputs[0]['sha256'] = 'c' * 64
        with self.assertRaises(a.ReferenceFormatError):
            a.candidate_manifest('overture-food-places', a.CONTRACTS['overture-food-places'][0], records, **kwargs)

    def test_unknown_release_source_time_fail_closed(self):
        for source, release, stamp in [('dietary-guidelines', 'fao-directory-20261013', STAMP),
                                       ('wikibooks', 'new-release', STAMP),
                                       ('wikibooks', a.CONTRACTS['wikibooks'][0], '2026-10-13')]:
            with self.assertRaises(a.ReferenceFormatError):
                a.normalize_reference(source, release, b'[]', acquired_at=stamp)


if __name__ == '__main__':
    unittest.main()
