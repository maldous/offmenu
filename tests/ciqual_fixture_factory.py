"""Authored synthetic CIQUAL-shaped values, not a publisher excerpt."""
from __future__ import annotations
import io
import json
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

from offmenu_ciqual.adapter import BASIS, CANONICAL, DICTIONARY, IDENTITIES, WORKBOOK, canonical

HEADERS = ['Synthetic group code', 'Synthetic subgroup code', 'Synthetic subsubgroup code',
           'Synthetic group name', 'Synthetic subgroup name', 'Synthetic subsubgroup name',
           'alim_code', 'alim_nom_eng', 'Synthetic scientific name']
NAMES = {'energy': 'Energy', 'protein': 'Protein', 'proteinNx625': 'Protein N x 6.25',
         'carbohydrate': 'Carbohydrate', 'fat': 'Fat', 'sugars': 'Sugars', 'fibre': 'Fibre',
         'saturatedFat': 'Saturated fatty acids', 'salt': 'Salt', 'calcium': 'Calcium',
         'iron': 'Iron', 'potassium': 'Potassium', 'sodium': 'Sodium', 'vitaminC': 'Vitamin C'}
DEFINITIONS = []
for column in range(10, 74):
    key, unit = CANONICAL.get(column, ('ciqual:column:' + str(column), 'kJ' if column == 10 else 'µg' if column == 72 else 'g'))
    name = NAMES.get(key, 'Synthetic component ' + str(column))
    header = name + ' (' + unit + '/100g)'
    HEADERS.append(header)
    DEFINITIONS.append({'sourceColumn': column, 'header': header, 'key': key, 'unit': unit, 'basis': BASIS})
MAP = {'schemaVersion': 'offmenu-ciqual-column-map/1', 'sourceId': 'ciqual', 'releaseId': '2025',
       'scope': 'synthetic-fixture', 'basis': BASIS, 'headers': HEADERS, 'nutrients': DEFINITIONS}


def column_name(number):
    result = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def workbook_bytes(rows=None, shared_strings=False):
    if rows is None:
        first = [None] * 73
        first[6:9] = ['001', 'Synthetic apple', 'Synthetic species']
        for at, value in {9: 120, 10: 28.7, 11: None, 12: 'TR', 13: 'ND', 14: '0', 15: '1,25',
                          16: '<0,1', 17: '-', 18: 'NT', 19: 'N', 20: 'unquantified',
                          26: 3.5, 31: 0, 49: '< 0.01', 50: 10, 53: 0.3,
                          58: 100, 60: 0, 71: 1.25, 72: 7.5}.items():
            first[at] = value
        second = [None] * 73
        second[6:9] = [2, 'Synthetic pear', None]
        second[10] = 0
        third = [None] * 73
        third[6:9] = ['3', 'Synthetic food three', None]
        third[14] = '< 1.2'
        rows = [HEADERS, first, second, third]
    strings, row_xml = [], []
    for row_index, values in enumerate(rows, 1):
        cells = []
        for column, value in enumerate(values, 1):
            if value is None:
                continue
            ref = column_name(column) + str(row_index)
            if isinstance(value, str):
                if shared_strings:
                    index = len(strings)
                    strings.append(value)
                    cell = f'<c r="{ref}" t="s"><v>{index}</v></c>'
                else:
                    cell = f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'
            elif isinstance(value, bool):
                cell = f'<c r="{ref}" t="b"><v>{int(value)}</v></c>'
            else:
                cell = f'<c r="{ref}" t="n"><v>{value}</v></c>'
            cells.append(cell)
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    content_types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'''
    if shared_strings:
        content_types += '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    parts = {
        '[Content_Types].xml': content_types + '</Types>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Synthetic CIQUAL" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:BU' + str(len(rows)) + '"/><sheetData>' + ''.join(row_xml) + '</sheetData></worksheet>'}
    if shared_strings:
        parts['xl/_rels/workbook.xml.rels'] = parts['xl/_rels/workbook.xml.rels'].replace('</Relationships>', '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
        parts['xl/sharedStrings.xml'] = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + ''.join('<si><t xml:space="preserve">' + escape(s) + '</t></si>' for s in strings) + '</sst>'
    return archive_bytes(parts)


def archive_bytes(parts):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(parts.items()):
            info = zipfile.ZipInfo(name, date_time=(2025, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, raw)
    return output.getvalue()


XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<ALIMENTS>
  <ALIMENT><alim_code>001</alim_code><alim_nom_fr>Pomme synthetique</alim_nom_fr><alim_grp_nom_fr>Groupe fictif</alim_grp_nom_fr><alim_nom_sci>Species fictive</alim_nom_sci></ALIMENT>
  <ALIMENT><alim_code>2</alim_code><alim_nom_fr>Poire synthetique</alim_nom_fr></ALIMENT>
  <ALIMENT><alim_code>3</alim_code><alim_nom_fr>Aliment fictif trois</alim_nom_fr></ALIMENT>
</ALIMENTS>'''


def write_fixture(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / WORKBOOK).write_bytes(workbook_bytes())
    (root / IDENTITIES).write_bytes(XML)
    (root / DICTIONARY).write_bytes(canonical(MAP))


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    write_fixture(root / 'tests/fixtures/ciqual')
    (root / 'src/offmenu_ciqual/contract.json').write_bytes(canonical({
        'schemaVersion': 'offmenu-ciqual-contract/1', 'sourceId': 'ciqual', 'releaseId': '2025',
        'scope': 'synthetic-fixture', 'columnMap': MAP,
        'historicalInputsEnabled': False,
        'notice': 'Authored fixture contract, not publisher headers or proof of source origin.'}))
