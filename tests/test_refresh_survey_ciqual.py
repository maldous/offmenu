"""Schema survey tests use only synthetic, non-production bytes."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import warnings
import xml.etree.ElementTree as ET
import zipfile

from offmenu.refresh import survey_ciqual as ciqual

FIXTURES = Path(__file__).parent / 'fixtures' / 'ciqual'


def fixtures():
    return {name: (FIXTURES / name).read_bytes() for name in (ciqual.WORKBOOK, ciqual.IDENTITIES)}


def parts(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def archive(values):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as target:
        for name, value in values.items():
            target.writestr(name, value)
    return output.getvalue()


def edit_sheet(blobs, edit):
    members = parts(blobs[ciqual.WORKBOOK])
    root = ET.fromstring(members['xl/worksheets/sheet1.xml'])
    edit(root)
    members['xl/worksheets/sheet1.xml'] = ET.tostring(root)
    blobs[ciqual.WORKBOOK] = archive(members)


def inline(ref, text):
    cell = ET.Element(ciqual.S + 'c', {'r': ref, 't': 'inlineStr'})
    ET.SubElement(ET.SubElement(cell, ciqual.S + 'is'), ciqual.S + 't').text = text
    return cell


class CiqualSurveyTests(unittest.TestCase):
    def test_fatty_acid_dictionary_colons_remain_visible(self):
        blobs = fixtures()
        def change(root):
            cell = root.find(S + 'sheetData').find(S + 'row').findall(S + 'c')[9]
            cell.find('.//' + S + 't').text = 'FA 18:2 n-6 (g/100g)'
        S = ciqual.S
        edit_sheet(blobs, change)
        report = ciqual.survey(blobs)
        self.assertTrue(report['evidenceComplete'])
        self.assertEqual(report['xlsx']['firstSheet']['columns'][9]['label'], 'FA 18:2 n-6 (g/100g)')
        self.assertEqual(ciqual.sanitize_report(report), report)

    def test_fixture_complete_exact_identity_reconciliation(self):
        report = ciqual.survey(fixtures())
        self.assertEqual(report['status'], 'surveyed')
        self.assertTrue(report['evidenceComplete'])
        self.assertFalse(report['candidateGenerationEnabled'])
        self.assertEqual(report['reasonCodes'], [])
        self.assertEqual(report['reconciliation'], dict(comparisonComplete=True, exactMatch=True,
            intersection=3, xlsxOnly=0, xmlOnly=0, xlsxUnique=3, xmlUnique=3))
        first = report['xlsx']['firstSheet']
        self.assertEqual(len(first['columns']), 73)
        self.assertEqual(first['columns'][10]['label'], 'Energy (kcal/100g)')
        self.assertEqual(first['columns'][10]['literalUnitSuffix'], '(kcal/100g)')
        self.assertEqual(first['foodCodes']['leadingZero'], 1)
        self.assertEqual(first['foodCodes']['integer'], 1)
        self.assertEqual(first['foodCodes']['text'], 2)
        self.assertEqual(first['foodCodes']['setSha256'], report['xml']['foodCodes']['setSha256'])
        self.assertEqual(ciqual.sanitize_report(report), report)
        self.assertLessEqual(len(ciqual._encode(report)), 32768)

    def test_extra_sheet_styles_and_discovered_xml_envelope_preserve_evidence(self):
        blobs = fixtures()
        members = parts(blobs[ciqual.WORKBOOK])
        workbook = ET.fromstring(members['xl/workbook.xml'])
        ET.SubElement(workbook.find(ciqual.S + 'sheets'), ciqual.S + 'sheet',
                      {'name': 'Dictionary', 'sheetId': '2', ciqual.RID: 'rId2', 'state': 'hidden'})
        members['xl/workbook.xml'] = ET.tostring(workbook)
        relations = ET.fromstring(members['xl/_rels/workbook.xml.rels'])
        ET.SubElement(relations, ciqual.R + 'Relationship', {'Id': 'rId2',
                      'Type': ciqual.REL_PREFIX + 'worksheet', 'Target': 'worksheets/sheet2.xml'})
        ET.SubElement(relations, ciqual.R + 'Relationship', {'Id': 'rId3',
                      'Type': ciqual.REL_PREFIX + 'styles', 'Target': 'styles.xml'})
        members['xl/_rels/workbook.xml.rels'] = ET.tostring(relations)
        members['xl/worksheets/sheet2.xml'] = members['xl/worksheets/sheet1.xml']
        members['xl/styles.xml'] = ('<styleSheet xmlns="' + ciqual.S[1:-1] + '"><numFmts>'
            '<numFmt numFmtId="164" formatCode="SECRET FORMAT"/></numFmts><cellXfs>'
            '<xf numFmtId="0"/><xf numFmtId="164"/></cellXfs></styleSheet>').encode()
        blobs[ciqual.WORKBOOK] = archive(members)
        blobs[ciqual.IDENTITIES] = b'<Export xmlns="urn:private-schema"><Foods><Food><alim_code>001</alim_code><alim_nom_fr>SECRET FOOD</alim_nom_fr></Food><Food><alim_code>2</alim_code><alim_nom_fr>SECRET FOOD</alim_nom_fr></Food><Food><alim_code>3</alim_code><alim_nom_fr>SECRET FOOD</alim_nom_fr></Food></Foods></Export>'
        report = ciqual.survey(blobs)
        self.assertEqual(report['status'], 'held')
        self.assertTrue(report['evidenceComplete'])
        self.assertEqual(len(report['xlsx']['sheets']), 2)
        self.assertEqual(report['xlsx']['styles']['numFmtIds'], [0, 164])
        self.assertEqual(report['xlsx']['features']['hiddenSheets'], 1)
        self.assertEqual(report['xml']['rootTag'], 'Export')
        self.assertEqual(report['xml']['entryTags'], [{'name': 'Food', 'count': 3}])
        self.assertTrue(report['reconciliation']['exactMatch'])
        serialized = json.dumps(report)
        self.assertNotIn('SECRET', serialized)
        self.assertNotIn('urn:private-schema', serialized)
        self.assertNotIn('formatCode', serialized)

    def test_all_qualifier_categories_and_no_value_export(self):
        blobs = fixtures()
        values = ['0', None, '', '-', 'Tr', 'ND', 'NT', 'N', '< 0,5', '9.25', 'SECRET FOOD', 'NaN']
        def edit(root):
            data = root.find(ciqual.S + 'sheetData')
            for old in list(data)[1:]:
                data.remove(old)
            for index, value in enumerate(values, 2):
                row = ET.SubElement(data, ciqual.S + 'row', {'r': str(index)})
                row.append(inline('G' + str(index), str(index)))
                row.append(inline('H' + str(index), 'SECRET FOOD'))
                if value is not None:
                    row.append(inline('K' + str(index), value))
        edit_sheet(blobs, edit)
        report = ciqual.survey(blobs)
        self.assertEqual(report['xlsx']['firstSheet']['columns'][10]['qualifiers'], dict.fromkeys(ciqual.QUALIFIERS, 1))
        self.assertNotIn('SECRET FOOD', json.dumps(report))
        self.assertNotIn('9.25', json.dumps(report))

    def test_xml_missing_duplicate_nested_fields_and_identities(self):
        blobs = fixtures()
        blobs[ciqual.IDENTITIES] = b'<ROOT><items><entry><alim_code>001</alim_code><alim_nom_fr>SECRET</alim_nom_fr><extra>true</extra></entry><entry><alim_code>001</alim_code><alim_nom_fr>A</alim_nom_fr><alim_nom_fr>B</alim_nom_fr><extra><nested/></extra></entry><entry><extra/></entry></items></ROOT>'
        report = ciqual.survey(blobs)
        self.assertEqual(report['xml']['entryCount'], 3)
        self.assertEqual(report['xml']['foodCodes']['duplicates'], 1)
        self.assertEqual(report['xml']['foodCodes']['missing'], 1)
        fields = {x['name']: x for x in report['xml']['fields']}
        self.assertEqual(fields['alim_nom_fr']['duplicateEntries'], 1)
        self.assertEqual(fields['alim_nom_fr']['missingEntries'], 1)
        self.assertEqual(fields['extra']['types'], {'boolean': 1, 'nested': 1, 'empty': 1})
        self.assertNotIn('SECRET', json.dumps(report))

    def test_invalid_float_identity_and_formula_are_diagnostic_only(self):
        blobs = fixtures()
        def edit(root):
            row = root.find(ciqual.S + 'sheetData')[1]
            cell = next(x for x in row if x.get('r') == 'G2')
            cell.clear()
            cell.set('r', 'G2')
            ET.SubElement(cell, ciqual.S + 'v').text = '1.0'
            formula = ET.SubElement(row, ciqual.S + 'c', {'r': 'L2'})
            ET.SubElement(formula, ciqual.S + 'f').text = 'WEBSERVICE("https://secret.invalid")'
            ET.SubElement(formula, ciqual.S + 'v').text = '932001'
        edit_sheet(blobs, edit)
        report = ciqual.survey(blobs)
        self.assertEqual(report['xlsx']['firstSheet']['foodCodes']['float'], 1)
        self.assertGreaterEqual(report['xlsx']['firstSheet']['foodCodes']['invalid'], 1)
        self.assertEqual(report['xlsx']['features']['formulas'], 1)
        self.assertNotIn('secret.invalid', json.dumps(report))
        self.assertNotIn('932001', json.dumps(report))

    def test_shared_string_dictionary_is_private_and_index_checked(self):
        blobs = fixtures()
        members = parts(blobs[ciqual.WORKBOOK])
        members['xl/sharedStrings.xml'] = ('<sst xmlns="' + ciqual.S[1:-1] + '"><si><t>SECRET FOOD</t></si></sst>').encode()
        blobs[ciqual.WORKBOOK] = archive(members)
        def edit(root):
            row = root.find(ciqual.S + 'sheetData')[1]
            cell = next(x for x in row if x.get('r') == 'H2')
            cell.clear()
            cell.attrib.update(r='H2', t='s')
            ET.SubElement(cell, ciqual.S + 'v').text = '99'
        edit_sheet(blobs, edit)
        report = ciqual.survey(blobs)
        self.assertEqual(report['xlsx']['sharedStrings']['entries'], 1)
        self.assertIn('unresolved-shared-string', report['reasonCodes'])
        self.assertNotIn('SECRET FOOD', json.dumps(report))

    def test_external_relationship_not_followed_or_exported(self):
        blobs = fixtures()
        members = parts(blobs[ciqual.WORKBOOK])
        root = ET.fromstring(members['xl/_rels/workbook.xml.rels'])
        ET.SubElement(root, ciqual.R + 'Relationship', {'Id': 'external', 'Type': ciqual.REL_PREFIX + 'hyperlink',
                      'TargetMode': 'External', 'Target': 'https://secret.invalid/private-food'})
        members['xl/_rels/workbook.xml.rels'] = ET.tostring(root)
        blobs[ciqual.WORKBOOK] = archive(members)
        report = ciqual.survey(blobs)
        self.assertEqual(report['xlsx']['relationships']['external'], 1)
        self.assertIn('external-or-unsafe-relationship', report['reasonCodes'])
        self.assertNotIn('https:', json.dumps(report))

    def test_dtd_pi_and_entity_payloads_rejected_including_utf16(self):
        payloads = [b'<!DOCTYPE ROOT [<!ENTITY secret "VALUE">]><ROOT>&secret;</ROOT>',
                    b'<?danger external?><ROOT/>',
                    '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE ROOT SYSTEM "https://secret.invalid"><ROOT/>'.encode('utf-16')]
        for raw in payloads:
            with self.subTest(raw=raw[:20]):
                blobs = fixtures()
                blobs[ciqual.IDENTITIES] = raw
                report = ciqual.survey(blobs)
                self.assertEqual(report['status'], 'held')
                self.assertFalse(report['evidenceComplete'])
                self.assertIsNone(report['xml'])
                self.assertIsNotNone(report['xlsx'])
                self.assertNotIn('secret.invalid', json.dumps(report))

    def test_unsafe_and_duplicate_zip_names_rejected(self):
        for name in ('../secret.xml', '/private.xml', 'a\\b.xml'):
            blobs = fixtures()
            members = parts(blobs[ciqual.WORKBOOK])
            members[name] = b'<ROOT/>'
            blobs[ciqual.WORKBOOK] = archive(members)
            report = ciqual.survey(blobs)
            self.assertIn('zip-member-name-rejected', report['reasonCodes'])
            self.assertIsNotNone(report['xml'])
        output = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(output, 'w') as target:
                target.writestr('same.xml', b'<A/>')
                target.writestr('same.xml', b'<B/>')
        blobs[ciqual.WORKBOOK] = output.getvalue()
        self.assertIn('zip-member-name-rejected', ciqual.survey(blobs)['reasonCodes'])

    def test_encrypted_flag_and_bomb_caps_rejected(self):
        blobs = fixtures()
        raw = bytearray(blobs[ciqual.WORKBOOK])
        start = raw.find(b'PK\x01\x02')
        flags = struct.unpack_from('<H', raw, start + 8)[0]
        struct.pack_into('<H', raw, start + 8, flags | 1)
        blobs[ciqual.WORKBOOK] = bytes(raw)
        self.assertIn('zip-encryption-forbidden', ciqual.survey(blobs)['reasonCodes'])
        blobs[ciqual.WORKBOOK] = archive({'huge.xml': b'<ROOT>' + b' ' * 2_000_000 + b'</ROOT>'})
        self.assertIn('zip-member-bounds', ciqual.survey(blobs)['reasonCodes'])

    def test_headers_preserve_whitespace_and_hash_sequence_changes(self):
        original = ciqual.survey(fixtures())
        blobs = fixtures()
        def edit(root):
            cell = root.find(ciqual.S + 'sheetData')[0][10]
            cell.find(ciqual.S + 'is/' + ciqual.S + 't').text = 'Energy  (kcal/100g)'
        edit_sheet(blobs, edit)
        changed = ciqual.survey(blobs)
        a, b = original['xlsx']['firstSheet'], changed['xlsx']['firstSheet']
        self.assertNotEqual(a['rawHeaderSequenceSha256'], b['rawHeaderSequenceSha256'])
        self.assertNotEqual(a['columns'][10]['rawHeaderSha256'], b['columns'][10]['rawHeaderSha256'])
        self.assertEqual(b['columns'][10]['label'], 'Energy  (kcal/100g)')

    def test_closed_schema_rejects_extra_strings_and_wrong_types(self):
        report = ciqual.survey(fixtures())
        mutations = [lambda r: r.update(foodRows=['SECRET']),
            lambda r: r['xlsx']['firstSheet']['columns'][0].update(rawValue='SECRET'),
            lambda r: r['xlsx']['firstSheet']['columns'][0].update(label='https://secret.invalid'),
            lambda r: r['xlsx']['archive'].update(members=1.0),
            lambda r: r.update(candidateGenerationEnabled=True),
            lambda r: r['reasonCodes'].append('SECRET')]
        for mutation in mutations:
            changed = deepcopy(report)
            mutation(changed)
            with self.assertRaisesRegex(ValueError, '^invalid-ciqual-survey-report$'):
                ciqual.sanitize_report(changed)

    def test_result_cap_is_explicit_hold_and_never_completeness(self):
        with patch.object(ciqual, 'MAX_RESULT', 1024):
            report = ciqual.survey(fixtures())
        self.assertEqual(report['status'], 'held')
        self.assertIn('result-size-limit', report['reasonCodes'])
        self.assertFalse(report['evidenceComplete'])
        self.assertIn('report', report['omissions'])
        self.assertIsNone(report['xlsx'])


if __name__ == '__main__':
    unittest.main()
