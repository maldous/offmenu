"""Real-schema-shaped authored fixtures only; no retained source bodies bundled."""
from copy import deepcopy
import gzip
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from offmenu.refresh import core, serialization, survey_ciqual as xml
from offmenu_ciqual import source_native as native


def ref(col, row):
    name = ''
    while col:
        col, digit = divmod(col - 1, 26)
        name = chr(65 + digit) + name
    return name + str(row)


def fixture():
    source = native.contract()
    members = {}
    def put(path, tree):
        members[path] = ET.tostring(tree)
    wb = ET.Element(xml.S + 'workbook')
    ss = ET.SubElement(wb, xml.S + 'sheets')
    for index, name in enumerate(('food composition', 'INFOODS codes'), 1):
        ET.SubElement(ss, xml.S + 'sheet', {'name': name, 'sheetId': str(index), xml.RID: 'r' + str(index)})
    put('xl/workbook.xml', wb)
    rootrels = ET.Element(xml.R + 'Relationships')
    ET.SubElement(rootrels, xml.R + 'Relationship', {'Id': 'office', 'Type': xml.REL_PREFIX + 'officeDocument', 'Target': 'xl/workbook.xml'})
    put('_rels/.rels', rootrels)
    rels = ET.Element(xml.R + 'Relationships')
    for index in (1, 2):
        ET.SubElement(rels, xml.R + 'Relationship', {'Id': 'r' + str(index), 'Type': xml.REL_PREFIX + 'worksheet', 'Target': 'worksheets/sheet' + str(index) + '.xml'})
    put('xl/_rels/workbook.xml.rels', rels)
    members['[Content_Types].xml'] = b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    strings = ET.Element(xml.S + 'sst')
    def cell(row, col, number, text, kind='s'):
        c = ET.SubElement(row, xml.S + 'c', {'r': ref(col, number), 't': kind, 's': '1'})
        if text is not None:
            if kind == 's':
                idx = len(strings)
                ET.SubElement(ET.SubElement(strings, xml.S + 'si'), xml.S + 't').text = text
                text = str(idx)
            ET.SubElement(c, xml.S + 'v').text = text
        return c
    main = ET.Element(xml.S + 'worksheet')
    ET.SubElement(main, xml.S + 'dimension', {'ref': 'A1:CF3'})
    data = ET.SubElement(main, xml.S + 'sheetData')
    header = ET.SubElement(data, xml.S + 'row', {'r': '1'})
    for col, definition in enumerate(source['survey']['xlsx']['firstSheet']['columns'], 1):
        label = definition['label']
        if col >= 10:
            label = label.replace(' (', '\n(', 1)
        cell(header, col, 1, label)
    for row_number, code in ((2, '1001'), (3, '1002')):
        row = ET.SubElement(data, xml.S + 'row', {'r': str(row_number)})
        values = {1: '1', 2: '10', 3: '100', 4: 'Authored group', 5: '-', 6: '',
                  7: code, 8: 'Authored food ' + code, 9: None,
                  10: '0', 11: 'TR', 12: '< 0,125', 13: 'ND', 14: 'NT',
                  15: 'N', 16: '-', 17: '', 18: 'trace?', 19: '>=2.50',
                  20: '0,12345678901234567890123456789', 21: 'NaN', 84: '6.25'}
        for col in range(1, 85):
            value = values.get(col, '1.125')
            cell(row, col, row_number, value, 'n' if col == 9 else 's')
    ET.SubElement(main, xml.S + 'autoFilter', {'ref': 'A1:CF3'})
    put('xl/worksheets/sheet1.xml', main)
    dictionary = ET.Element(xml.S + 'worksheet')
    ET.SubElement(dictionary, xml.S + 'dimension', {'ref': 'A1:C75'})
    data = ET.SubElement(dictionary, xml.S + 'sheetData')
    for n in range(1, 76):
        row = ET.SubElement(data, xml.S + 'row', {'r': str(n)})
        values = ['INFDSTAG', 'ORIGCPCD', 'Authored source label'] if n == 1 else ['ENERC', str(325 + n), 'Authored unreviewed meaning ' + str(n)]
        for col, value in enumerate(values, 1):
            cell(row, col, n, value, 'n' if col == 2 and n > 1 else 's')
    put('xl/worksheets/sheet2.xml', dictionary)
    put('xl/sharedStrings.xml', strings)
    style = ET.Element(xml.S + 'styleSheet')
    formats = ET.SubElement(style, xml.S + 'numFmts')
    ET.SubElement(formats, xml.S + 'numFmt', {'numFmtId': '164', 'formatCode': '0.000" not interpreted"'})
    xfs = ET.SubElement(style, xml.S + 'cellXfs')
    ET.SubElement(xfs, xml.S + 'xf', {'numFmtId': '0'})
    ET.SubElement(xfs, xml.S + 'xf', {'numFmtId': '164'})
    put('xl/styles.xml', style)
    members['docProps/thumbnail.bin'] = b'opaque authored test member'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, body in members.items():
            archive.writestr(path, body)
    identities = ET.Element('TABLE')
    for code in ('1001', '1002'):
        food = ET.SubElement(identities, 'ALIM')
        for tag, value in [('alim_code', code), ('alim_grp_code', '1'), ('alim_ssgrp_code', '10'),
                           ('alim_ssssgrp_code', '100'), ('alim_nom_fr', 'Aliment inventé ' + code),
                           ('alim_nom_eng', 'Authored food ' + code), ('alim_nom_sci', None), ('facteur_Jones', '6.25')]:
            child = ET.SubElement(food, tag)
            child.text = value
            if tag == 'alim_nom_sci':
                child.set('{http://www.w3.org/2001/XMLSchema-instance}nil', 'true')
    blobs = {'FR_WORKBOOK': output.getvalue(), 'FR_IDENTITIES': ET.tostring(identities)}
    for name in native._pins():
        blobs.setdefault(name, b'authored test corroboration ' + name.encode())
    spec = deepcopy(source)
    spec['inputPins'] = {name: serialization.asset(raw) for name, raw in blobs.items()}
    spec['survey'] = xml.survey({xml.WORKBOOK: blobs['FR_WORKBOOK'], xml.IDENTITIES: blobs['FR_IDENTITIES']})
    return blobs, spec


class SourceNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blobs, cls.spec = fixture()

    def render_fixture(self):
        # Only the test process substitutes the immutable nine-input contract.
        with patch.object(native, 'contract', return_value=deepcopy(self.spec)), patch.object(native, '_pins', return_value=deepcopy(self.spec['inputPins'])):
            return native.render_verified_bundle(self.blobs)

    def test_real_contract_exact_known_observations(self):
        contract = native.contract()
        self.assertEqual(contract['inputPins'], native._pins())
        self.assertEqual(len(contract['inputPins']), 9)
        report = contract['survey']
        self.assertEqual(report['xml']['rootTag'], 'TABLE')
        self.assertEqual(report['xml']['entryTags'], [{'count': 3484, 'name': 'ALIM'}])
        self.assertEqual(report['xlsx']['firstSheet']['rawHeaderSequenceSha256'], '056bbe18e52624ca89a81e96ed232c11f2102a5e7506fc4e7cc90c6cb26e569a')
        columns = report['xlsx']['firstSheet']['columns']
        self.assertEqual([x['column'] for x in columns], list(range(1, 85)))
        self.assertEqual(columns[-1]['label'], 'Jones factor')
        self.assertEqual(columns[-1]['literalUnitSuffix'], None)
        self.assertEqual(sum(x['literalUnitSuffix'] is not None for x in columns), 74)
        self.assertEqual([len(row) for row in report['xlsx']['infoodsDictionary']['rows']], [3] * 75)
        self.assertEqual(report['reconciliation']['intersection'], 3484)
        self.assertFalse(contract['policy']['canonicalNutrientMapping'])

    def test_authored_fixture_cannot_enter_real_public_renderer(self):
        with self.assertRaisesRegex(native.NativeError, 'native-selected-input-pin-mismatch'):
            native.render_verified_bundle(self.blobs)

    def test_missing_ninth_pin_is_not_admitted(self):
        with self.assertRaisesRegex(native.NativeError, 'nine-input-bundle-required'):
            native.render_verified_bundle({k: v for k, v in self.blobs.items() if k != 'NO_EN_SOURCES'})

    def test_exact_native_schema_preserves_cells_and_xml_attributes(self):
        rows, metadata, counts = native._extract(self.blobs, self.spec)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['kind'], 'sourceNativeFood')
        self.assertEqual(set(rows[0]['data']['cells']), {str(x) for x in range(1, 85)})
        cells = rows[0]['data']['cells']
        self.assertEqual(cells['10']['decimal'], '0')
        self.assertEqual(cells['11']['qualifier'], 'trace')
        self.assertEqual(cells['11']['decimal'], None)
        self.assertEqual(cells['12']['bound'], {'operator': '<', 'decimal': '0.125'})
        self.assertEqual(cells['12']['raw'], '< 0,125')
        self.assertEqual(cells['13']['qualifier'], 'ND')
        self.assertEqual(cells['14']['qualifier'], 'NT')
        self.assertEqual(cells['15']['qualifier'], 'N')
        self.assertEqual(cells['16']['qualifier'], 'dash')
        self.assertEqual(cells['17']['qualifier'], 'blank')
        self.assertEqual(cells['18']['qualifier'], 'unresolved')
        self.assertEqual(cells['19']['bound']['operator'], '>=')
        self.assertEqual(cells['20']['decimal'], '0.12345678901234567890123456789')
        self.assertEqual(cells['21']['qualifier'], 'invalid')
        self.assertEqual(cells['21']['decimal'], None)
        self.assertEqual(cells['9']['raw'], None)
        self.assertTrue(cells['9']['present'])
        self.assertEqual(rows[0]['data']['identityXml']['alim_nom_sci']['attributes'],
                         {'{http://www.w3.org/2001/XMLSchema-instance}nil': 'true'})
        self.assertEqual(sum(counts.values()), 2 * 74)
        self.assertEqual(metadata['columns'][9]['rawHeader'], 'Energy, Regulation EU No 1169 2011\n(kJ 100g)')
        self.assertEqual(metadata['presentation']['interpretation'], 'not-performed')

    def test_infoods_tags_never_merge_energy_definitions(self):
        _, metadata, _ = native._extract(self.blobs, self.spec)
        dictionary = metadata['infoods']
        self.assertEqual(dictionary['semanticMapping'], 'not-performed')
        self.assertEqual(dictionary['rows'][1]['1']['raw'], 'ENERC')
        self.assertEqual(dictionary['rows'][2]['1']['raw'], 'ENERC')
        self.assertEqual(dictionary['rows'][1]['2']['raw'], '327')
        self.assertEqual(dictionary['rows'][2]['2']['raw'], '328')
        self.assertEqual(dictionary['rows'][1]['3']['raw'], 'Authored unreviewed meaning 2')

    def test_xml_identity_whitespace_matches_survey_and_preserves_raw_text(self):
        blobs = dict(self.blobs)
        tree = ET.fromstring(blobs['FR_IDENTITIES'])
        original = [entry.find('alim_code').text for entry in tree]
        for entry in tree:
            field = entry.find('alim_code')
            field.text = '\n\t ' + field.text + ' \n'
        blobs['FR_IDENTITIES'] = ET.tostring(tree)
        # The exact existing survey contract already admits this XML spelling.
        observed = xml.survey({xml.WORKBOOK: blobs['FR_WORKBOOK'], xml.IDENTITIES: blobs['FR_IDENTITIES']})
        self.assertEqual(observed, self.spec['survey'])
        rows, _, _ = native._extract(blobs, self.spec)
        for row, code in zip(rows, original):
            self.assertEqual(row['id'], 'ciqual:2025:food:' + code)
            self.assertEqual(row['data']['identityXml']['alim_code']['raw'], '\n\t ' + code + ' \n')
        identities = native._xml_identities(blobs['FR_IDENTITIES'], self.spec['survey']['xml'])
        self.assertEqual(set(identities), set(original))

    def test_xml_identity_trim_keeps_grammar_duplicates_attributes_and_hash_strict(self):
        for invalid in ('1 001', '1001.0', '1e3', None):
            tree = ET.fromstring(self.blobs['FR_IDENTITIES'])
            tree[0].find('alim_code').text = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(native.NativeError, '^native-food-id$'):
                native._xml_identities(ET.tostring(tree), self.spec['survey']['xml'])
        tree = ET.fromstring(self.blobs['FR_IDENTITIES'])
        tree[0].find('alim_code').set('unreviewed', 'true')
        with self.assertRaisesRegex(native.NativeError, '^native-food-id$'):
            native._xml_identities(ET.tostring(tree), self.spec['survey']['xml'])
        tree = ET.fromstring(self.blobs['FR_IDENTITIES'])
        tree[1].find('alim_code').text = ' 1001\n'
        with self.assertRaisesRegex(native.NativeError, '^native-duplicate-food-id$'):
            native._xml_identities(ET.tostring(tree), self.spec['survey']['xml'])
        tree = ET.fromstring(self.blobs['FR_IDENTITIES'])
        tree[0].find('alim_code').text = '01001'
        with self.assertRaisesRegex(native.NativeError, '^native-identity-set-drift$'):
            native._xml_identities(ET.tostring(tree), self.spec['survey']['xml'])

    def test_missing_and_blank_remain_distinct(self):
        ctx = xml._Context()
        absent = native.lexical_cell(None, [], ctx)
        cell = ET.Element(xml.S + 'c', {'t': 'n'})
        present_empty = native.lexical_cell(cell, [], ctx)
        self.assertFalse(absent['present'])
        self.assertTrue(present_empty['present'])
        self.assertIsNone(absent['decimal'])
        self.assertIsNone(present_empty['decimal'])

    def test_header_hash_schema_and_id_set_drift_fail(self):
        for mutator in (lambda x: x['survey']['xlsx']['firstSheet']['columns'][9].update(rawHeaderSha256='0' * 64),
                        lambda x: x['survey']['xml'].update(rootTag='ALIMENTS'),
                        lambda x: x['survey']['reconciliation'].update(intersection=3)):
            spec = deepcopy(self.spec)
            mutator(spec)
            with self.assertRaisesRegex(native.NativeError, 'survey-contract-drift'):
                native._extract(self.blobs, spec)

    def test_render_deterministic_and_holds_explicit(self):
        one, two = self.render_fixture(), self.render_fixture()
        self.assertEqual(one, two)
        self.assertEqual(set(one), set(native.OUTPUT_FILES))
        content = core.strict_json(one['content-manifest.json'])
        build = core.strict_json(one['build-manifest.json'])
        self.assertEqual(content['counts']['extracted'], 2)
        self.assertIsNone(content['counts']['accepted'])
        self.assertFalse(content['completeness']['countryCoverageComplete'])
        self.assertEqual(content['publicExport'], 'not-enabled')
        self.assertEqual(content['freshness'], 'unknown')
        self.assertEqual(content['canonicalArtifacts']['normalized.jsonl'], serialization.asset(gzip.decompress(one['normalized.jsonl.gz'])))
        self.assertEqual(len(build['buildPins']['inputPins']), 9)
        self.assertIn('expat', build['buildPins']['runtime'])
        self.assertEqual(set(build['buildPins']['dependencies']), set(native.DEPENDENCIES))

    def test_existing_candidate_is_idempotent_and_conflicts_never_replaced(self):
        files = self.render_fixture()
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'result'
            self.assertTrue(native._publish(files, output))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertFalse(native._publish(files, output))
            changed = dict(files, **{'source-metadata.json': b'changed'})
            with self.assertRaisesRegex(native.NativeError, 'existing-candidate-conflict'):
                native._publish(changed, output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_atomic_failure_and_symlink_output(self):
        files = self.render_fixture()
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'result'
            with patch.object(native.os, 'rename', side_effect=OSError('authored interruption')):
                with self.assertRaises(OSError):
                    native._publish(files, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(root).glob('.ciqual-source-native-stage-*')))
            output.symlink_to(Path(root) / 'elsewhere')
            with self.assertRaisesRegex(core.RefreshError, 'symlink-path-rejected'):
                native._publish(files, output)

    def test_selected_receipt_contains_only_aggregate_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'ciqual-source-native-authored-test'
            assets = native.survey.ASSETS
            by_path = {item[0]: self.blobs[name] for name, item in assets.items()}
            def read_selected(cache, relative, size, digest):
                return by_path[relative]
            with patch.object(native.os, 'geteuid', return_value=1000), \
                 patch.object(native.survey, 'OUTPUT', Path(root)), \
                 patch.object(native.survey, '_read_asset', side_effect=read_selected) as read, \
                 patch.object(native, 'contract', return_value=deepcopy(self.spec)), \
                 patch.object(native, '_pins', return_value=deepcopy(self.spec['inputPins'])):
                receipt = native.build_selected(output)
                self.assertEqual(read.call_count, 9)
                for call in read.call_args_list:
                    self.assertEqual(call.args[0], native.survey.CACHE)
                self.assertTrue(receipt['created'])
                repeated = native.build_selected(output)
                self.assertFalse(repeated['created'])
            text = core.canonical(receipt).decode()
            self.assertNotIn('Authored food', text)
            self.assertNotIn('Aliment inventé', text)
            self.assertNotIn('recordId', receipt)
            self.assertNotIn('data', receipt)
            self.assertFalse(receipt['sourceContentsUploaded'])
            self.assertEqual(receipt['sourceCopies'], 0)
            self.assertEqual(receipt['counts']['extracted'], 2)
            self.assertEqual(set(receipt['artifacts']), set(native.OUTPUT_FILES))

    def test_source_verification_failure_creates_no_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'ciqual-source-native-authored-test'
            with patch.object(native.os, 'geteuid', return_value=1000), \
                 patch.object(native.survey, 'OUTPUT', Path(root)), \
                 patch.object(native.survey, '_read_asset', side_effect=native.survey.SurveyError('selected-hash-mismatch')):
                with self.assertRaisesRegex(native.survey.SurveyError, 'selected-hash-mismatch'):
                    native.build_selected(output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_selected_entrypoint_cannot_write_outside_foo_output(self):
        with patch.object(native.os, 'geteuid', return_value=1000):
            with self.assertRaisesRegex(native.NativeError, 'native-output-location'):
                native.build_selected('/tmp/ciqual-source-native-exfiltration')


if __name__ == '__main__':
    unittest.main()
