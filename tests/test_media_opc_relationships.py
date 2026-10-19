"""Authored synthetic OPC fixtures only; no production workbook bodies."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from xml.sax.saxutils import quoteattr
import zipfile

from offmenu.refresh import media_preparation as m


class OPCRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = self.root / 'original'
        self.output = self.root / 'prepared'
        m.configure_storage_lock(None)

    def tearDown(self):
        self.temp.cleanup()
        m.configure_storage_lock(None)

    def workbook(self, target, member='xl/worksheets/sheet1.xml', mode=None, extra_rels='', extra_members=None):
        mode_xml = '' if mode is None else ' TargetMode=' + quoteattr(mode)
        rel = '<Relationship Id="rId1" Target=' + quoteattr(target) + mode_xml + '/>'
        files = {'[Content_Types].xml': b'<Types/>',
                 'xl/workbook.xml': b'<workbook xmlns:r="urn:r"><sheets><sheet name="Private sheet" r:id="rId1"/></sheets></workbook>',
                 'xl/_rels/workbook.xml.rels': ('<Relationships>' + rel + extra_rels + '</Relationships>').encode(),
                 member: b'<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Private source value</t></is></c><c r="B1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>'}
        files.update(extra_members or {})
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        return stream.getvalue()

    def prepare(self, raw):
        self.original.write_bytes(raw)
        identity = self.original.stat()
        contract = {'schemaVersion': m.SCHEMA, 'assetId': 'synthetic.opc.v1',
                    'expectedSHA256': hashlib.sha256(raw).hexdigest(), 'expectedBytes': len(raw),
                    'expectedMediaTypes': [m.XLSX], 'permissions': {'read': True, 'extract': True, 'copy': True},
                    'holds': [], 'parameters': {}}
        result = m.prepare_asset(contract, self.original, self.output,
                                 time.monotonic() + 10, minimum_free_bytes=0)
        self.assertEqual(self.original.read_bytes(), raw)
        self.assertEqual(self.original.stat().st_mtime_ns, identity.st_mtime_ns)
        self.assertFalse(result['originalModified'])
        self.assertEqual(result['networkRequests'], 0)
        self.assertNotIn('Private', json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))
        return result

    def test_parent_component_resolution_prepares_workbook(self):
        result = self.prepare(self.workbook('../xl/worksheets/sheet1.xml'))
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['sheetCount'], 1)
        self.assertEqual(result['metrics']['cellCount'], 2)
        rows = [json.loads(x) for x in (self.output / result['outputs'][0]['outputId']).read_text().splitlines()]
        self.assertEqual(rows[0]['cells'][0]['sourceText'], 'Private source value')
        self.assertEqual(rows[0]['cells'][1]['formula'], '1+1')

    def test_relationship_base_is_source_part_not_rels_directory(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/sheet.xml': b'',
                   'xl/_rels/worksheets/sheet.xml': b''}
        self.assertEqual(m._opc_target_member('xl/workbook.xml', 'worksheets/sheet.xml', None, members),
                         'xl/worksheets/sheet.xml')

    def test_dot_parent_and_package_absolute_forms(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/sheet.xml': b'', 'parts/sheet.xml': b''}
        examples = {'worksheets/sheet.xml': 'xl/worksheets/sheet.xml',
                    './worksheets/sheet.xml': 'xl/worksheets/sheet.xml',
                    'worksheets/../worksheets/sheet.xml': 'xl/worksheets/sheet.xml',
                    '../xl/worksheets/sheet.xml': 'xl/worksheets/sheet.xml',
                    '/xl/worksheets/sheet.xml': 'xl/worksheets/sheet.xml',
                    '../parts/sheet.xml': 'parts/sheet.xml', '/parts/sheet.xml': 'parts/sheet.xml'}
        for target, expected in examples.items():
            with self.subTest(target=target):
                self.assertEqual(m._opc_target_member('xl/workbook.xml', target, 'Internal', members), expected)

    def test_contained_target_outside_xl_folder_prepares(self):
        result = self.prepare(self.workbook('../parts/sheet1.xml', 'parts/sheet1.xml'))
        self.assertEqual(result['status'], 'ready', result)

    def test_parent_target_on_non_sheet_relationship_is_validated(self):
        extra = '<Relationship Id="rId2" Target="../customXml/item1.xml"/>'
        result = self.prepare(self.workbook('worksheets/sheet1.xml', extra_rels=extra,
                                           extra_members={'customXml/item1.xml': b'<data/>'}))
        self.assertEqual(result['status'], 'ready', result)

    def test_attempted_escape_cannot_clamp_back_into_root(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/sheet.xml': b'', 'sheet.xml': b''}
        for target in ('../../sheet.xml', '../../xl/worksheets/sheet.xml', '/../sheet.xml',
                       '/xl/../../sheet.xml', '../parts/../../sheet.xml'):
            with self.subTest(target=target), self.assertRaises(m.PreparationError) as caught:
                m._opc_target_member('xl/workbook.xml', target, None, members)
            self.assertEqual(caught.exception.code, 'archive-unsafe')

    def test_external_ambiguous_and_malformed_targets_rejected(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/sheet.xml': b''}
        targets = ('https://example.invalid/sheet.xml', 'file:///etc/passwd', '//example.invalid/sheet.xml',
                   'C:/sheet.xml', 'worksheets\\sheet.xml', 'worksheets/sheet.xml?x=1',
                   'worksheets/sheet.xml#cell', 'worksheets/sheet.xml?', 'worksheets/sheet.xml#',
                   '', '/', 'worksheets/', 'worksheets/.', 'worksheets/..', 'worksheets//sheet.xml',
                   ' worksheets/sheet.xml', 'worksheets/sheet.xml\n', 'worksheets/\x00sheet.xml',
                   '%2e%2e/xl/worksheets/sheet.xml', '.%2e/xl/worksheets/sheet.xml',
                   'worksheets%2fsheet.xml', 'worksheets%5Csheet.xml', 'worksheets/%00sheet.xml',
                   'worksheets/%7fsheet.xml', 'worksheets/%', 'worksheets/%GG.xml', 'x' * 2049)
        for target in targets:
            with self.subTest(target=target), self.assertRaises(m.PreparationError) as caught:
                m._opc_target_member('xl/workbook.xml', target, None, members)
            self.assertEqual(caught.exception.code, 'archive-unsafe')
        for mode in ('External', 'external', '', 'Unexpected'):
            with self.subTest(mode=mode), self.assertRaises(m.PreparationError):
                m._opc_target_member('xl/workbook.xml', 'worksheets/sheet.xml', mode, members)

    def test_percent_escape_matches_exact_encoded_zip_name_without_decoding(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/source%20sheet.xml': b'',
                   'xl/worksheets/source sheet.xml': b''}
        self.assertEqual(m._opc_target_member('xl/workbook.xml', 'worksheets/source%20sheet.xml', None, members),
                         'xl/worksheets/source%20sheet.xml')
        del members['xl/worksheets/source%20sheet.xml']
        with self.assertRaises(m.PreparationError):
            m._opc_target_member('xl/workbook.xml', 'worksheets/source%20sheet.xml', None, members)

    def test_missing_or_case_mismatched_member_rejected(self):
        members = {'xl/workbook.xml': b'', 'xl/worksheets/Sheet.xml': b''}
        for target in ('worksheets/sheet.xml', '../missing.xml'):
            with self.subTest(target=target), self.assertRaises(m.PreparationError):
                m._opc_target_member('xl/workbook.xml', target, None, members)

    def test_external_relationship_still_rejected_end_to_end(self):
        result = self.prepare(self.workbook('worksheets/sheet1.xml', mode='External'))
        self.assertEqual(result['errorCode'], 'archive-unsafe')
        self.assertFalse(result['nextStageReady'])

    def test_duplicate_relationship_identity_is_rejected(self):
        result = self.prepare(self.workbook('worksheets/sheet1.xml',
            extra_rels='<Relationship Id="rId1" Target="../xl/worksheets/sheet1.xml"/>'))
        self.assertEqual(result['errorCode'], 'archive-unsafe')
        self.assertFalse(result['nextStageReady'])

    def test_archive_member_traversal_still_rejected(self):
        result = self.prepare(self.workbook('../xl/worksheets/sheet1.xml',
                                            extra_members={'xl/../escape.xml': b'<x/>'}))
        self.assertEqual(result['errorCode'], 'archive-unsafe')
        self.assertFalse(result['nextStageReady'])

    def test_existing_size_bounds_are_unchanged_and_enforced(self):
        self.assertEqual(m.MAX_MEMBER_BYTES, 32 * 1024 * 1024)
        self.assertEqual(m.MAX_ARCHIVE_BYTES, 128 * 1024 * 1024)
        self.assertEqual(m.MAX_MEMBERS, 512)
        self.assertEqual(m.MAX_RATIO, 200)
        self.assertGreater(99_582_537, m.MAX_MEMBER_BYTES)
        raw = self.workbook('../xl/worksheets/sheet1.xml')
        with patch.object(m, 'MAX_MEMBER_BYTES', 32):
            result = self.prepare(raw)
        self.assertEqual(result['errorCode'], 'archive-expansion-limit')
        self.assertFalse(result['nextStageReady'])

    def test_successful_old_form_and_new_form_have_identical_derivatives(self):
        old = self.prepare(self.workbook('worksheets/sheet1.xml'))
        new = self.prepare(self.workbook('../xl/worksheets/sheet1.xml'))
        self.assertEqual(old['status'], 'ready', old)
        self.assertEqual(new['status'], 'ready', new)
        self.assertEqual(old['outputs'], new['outputs'])
        self.assertEqual(old['parameters'], new['parameters'])
        self.assertEqual(old['metrics'], new['metrics'])


if __name__ == '__main__':
    unittest.main()
