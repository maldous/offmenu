#!/usr/bin/env python3
"""Bounded, offline AFCD-3 staging adapter. Never writes source or admits data.

Uses stdlib OOXML reading so validation adds no dependencies. XML hashes refer
to exact original ZIP member/row/cell bytes; absent cells have no invented hash.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

SOURCE = 'https://www.foodstandards.gov.au/science-data/food-nutrient-databases/afcd/data-files'
LICENCE = 'https://www.foodstandards.gov.au/science-data/monitoringnutrients/afcd/datauserlicenceagreement'
LIMITATION = ('There are limitations associated with food composition databases. Food composition data used in the database or databases may represent an average of the nutrient content of a particular sample of foods and ingredients, determined at a particular time. The nutrient composition of foods and ingredients can vary substantially between batches and brands because of a number of factors, including changes in season, processing practices and ingredient source, and methods of calculation.')
PINS = {
    'Food-Details.xlsx': '69aa096c45cb0699db60a9c544442312e9ff09af587b99c42dc78bc26f689629',
    'Nutrient-profiles.xlsx': '14cb3e73dbf58987b440e6299624c0fefd7a4e61591fc1f753995d9534e0efc9',
    'Nutrient-details.xlsx': '7c455129a90e65d29840ecd188fa223cca8bdf0729b21efebc286884d69fafaa',
}
DEFAULT_IDS = ('F002258', 'F000050', 'F000061', 'F001919', 'F001918',
               'F006038', 'F006066', 'F006067', 'F006497', 'F008936')
ROW = re.compile(rb'<row\b[^>]*>.*?</row>', re.S)
CELL = re.compile(rb'<c\b[^>]*?(?:/>|>.*?</c>)', re.S)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode())


def key(value):
    return re.sub(r'[^a-z0-9%]', '', str(value).lower().replace('equated', ''))


class Workbook:
    """Only the named sheets are decompressed once per adapter invocation."""
    def __init__(self, path):
        self.path = Path(path)
        self.archive = zipfile.ZipFile(path)
        self.strings = []
        if 'xl/sharedStrings.xml' in self.archive.namelist():
            root = ET.fromstring(self.archive.read('xl/sharedStrings.xml'))
            self.strings = [''.join(n.itertext()) for n in root]
        rels = ET.fromstring(self.archive.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        self.sheets = {}
        for s in ET.fromstring(self.archive.read('xl/workbook.xml')).iter():
            if s.tag.endswith('}sheet'):
                rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                target = targets[rid]
                self.sheets[s.attrib['name']] = (target.lstrip('/') if target.startswith('/')
                                                else posixpath.normpath('xl/' + target))
        self.members = {}

    def close(self):
        self.archive.close()

    def rows(self, sheet):
        member = self.sheets[sheet]
        data = self.archive.read(member)
        self.members[sheet] = {'member': member, 'sha256': sha(data)}
        # Excel's row/cell attributes may use prefixes declared on worksheet.
        # Parse in that namespace context while hashing untouched original bytes.
        worksheet_tag = re.search(rb'<worksheet\b[^>]*>', data).group()
        namespaces = b' '.join(re.findall(rb'xmlns:[\w]+="[^"]*"', worksheet_tag))
        def parse(fragment):
            return ET.fromstring(b'<wrapper ' + namespaces + b'>' + fragment + b'</wrapper>')[0]
        for match in ROW.finditer(data):
            raw = match.group()
            root = parse(raw)
            cells = {}
            for cm in CELL.finditer(raw):
                original = cm.group()
                c = parse(original)
                address = c.attrib['r']
                kind = c.attrib.get('t', 'n')
                v = c.find('v')
                lexeme = v.text if v is not None else None
                if kind == 's':
                    value = self.strings[int(lexeme)]
                elif kind == 'inlineStr':
                    value = ''.join(c.find('is').itertext())
                elif kind in ('str', 'e', 'b'):
                    value = lexeme
                elif lexeme is None:
                    value = None
                else:
                    value = float(lexeme)
                    if not math.isfinite(value):
                        raise ValueError('Non-finite source value')
                cells[re.sub(r'\d', '', address)] = {
                    'address': address, 'value': value, 'storage_type': kind,
                    'original_lexeme': lexeme, 'xml_sha256': sha(original),
                    'formula': c.findtext('f'),
                }
            yield {'number': int(root.attrib['r']), 'xml_sha256': sha(raw), 'cells': cells}


def value(row, column):
    return row['cells'].get(column, {}).get('value')


def food_rows(book, sheet, budget):
    headers = None
    seen = 0
    for row in book.rows(sheet):
        if value(row, 'A') == 'Public Food Key':
            headers = {col: cell['value'] for col, cell in row['cells'].items() if cell['value'] is not None}
            continue
        if headers is not None and str(value(row, 'A')).startswith('F'):
            if seen == budget:
                break
            seen += 1
            yield headers, row


def definitions(book):
    result = {}
    for sheet in book.sheets:
        if sheet in ('Contents', 'Core nutrients'):
            continue
        columns = None
        for index, row in enumerate(book.rows(sheet)):
            if index >= 512:
                raise ValueError('Definition sheet exceeds bound')
            if value(row, 'A') == 'Component':
                columns = {col: cell['value'] for col, cell in row['cells'].items()}
            elif columns and value(row, 'A'):
                fields = {label: value(row, col) for col, label in columns.items() if label}
                component, unit = fields['Component'], fields.get('Units')
                if unit:
                    result.setdefault((key(component), key(unit)), []).append({
                        'sheet': sheet, 'row': row['number'], 'xml_sha256': row['xml_sha256'],
                        'fields': fields,
                    })
    return result


def observation(cell):
    if cell and cell['formula'] is not None:
        return {'value': None, 'status': 'formula-unresolved', 'source': cell}
    if not cell or cell['value'] is None:
        return {'value': None, 'status': 'missing', 'source': cell}
    raw = cell['value']
    if isinstance(raw, (float, int)):
        return {'value': raw, 'status': 'source-zero' if raw == 0 else 'source-number', 'source': cell}
    # Do not coerce trace/less-than/text/error into analytical zero.
    return {'value': None, 'status': 'source-text-or-qualifier', 'source': cell}


def adapt(directory, food_ids=DEFAULT_IDS, scan_limit=750):
    if not 1 <= scan_limit <= 750 or not 1 <= len(food_ids) <= 1000:
        raise ValueError('Bounded adapter: 1..750 mass rows; 250 volume rows; <=1000 requested IDs')
    if len(set(food_ids)) != len(food_ids):
        raise ValueError('Duplicate requested food identifiers')
    directory = Path(directory)
    files = {}
    for name, expected in PINS.items():
        actual = sha((directory / name).read_bytes())
        if actual != expected:
            raise ValueError('AFCD-3 source hash mismatch: ' + name)
        files[name] = {'path': str(directory / name), 'sha256': actual}
    books = {name: Workbook(directory / name) for name in PINS}
    wanted = set(food_ids)
    try:
        detail_book = books['Food-Details.xlsx']
        details = {value(row, 'A'): (headers, row) for headers, row in
                   food_rows(detail_book, 'Food details', scan_limit) if value(row, 'A') in wanted}
        defs = definitions(books['Nutrient-details.xlsx'])
        profiles = books['Nutrient-profiles.xlsx']
        records = []
        scanned = 0
        for sheet, unit, budget in [('All solids & liquids per 100 g', 'g', scan_limit),
                                    ('Liquids only per 100 mL', 'mL', 250)]:
            for headers, row in food_rows(profiles, sheet, budget):
                scanned += 1
                food_id = value(row, 'A')
                if food_id not in wanted:
                    continue
                if food_id not in details:
                    raise ValueError('Food details outside bounded window: ' + food_id)
                dh, detail_row = details[food_id]
                detail = {h: value(detail_row, col) for col, h in dh.items()}
                if detail['Food Name'] != value(row, 'D'):
                    raise ValueError('Food details/profile identity conflict: ' + food_id)
                nutrients = []
                for col, label in headers.items():
                    if col in ('A', 'B', 'C', 'D'):
                        continue
                    match = re.fullmatch(r'(.*?)\s*\((kJ|kcal|mg/gN|mg|ug|g|%T)\)', ' '.join(str(label).split()))
                    if not match:
                        raise ValueError('Unknown AFCD nutrient header: ' + str(label))
                    name, nutrient_unit = match.groups()
                    basis = {'amount': 100, 'unit': unit, 'scope': 'source edible food'}
                    if nutrient_unit == '%T':
                        basis = {'amount': 100, 'unit': 'g total fatty acids', 'scope': 'total fatty acids, not food mass'}
                    elif nutrient_unit == 'mg/gN':
                        basis = {'amount': 1, 'unit': 'g nitrogen', 'scope': 'nitrogen, not food mass'}
                    candidates = defs.get((key(name), key(nutrient_unit)), [])
                    nutrients.append({
                        'source_header': label, 'source_column': col,
                        'name': name, 'unit': nutrient_unit, 'basis': basis,
                        'observation': observation(row['cells'].get(col)),
                        'definition_candidates': candidates,
                        'definition_status': 'source-definition-linked' if len(candidates) == 1 else 'unresolved',
                        'method_scope': 'definition-level method and food-level derivation; not per-cell analytical certification',
                    })
                record = {
                    'id': 'afcd:3:' + food_id + ':' + unit, 'food_id': food_id,
                    'food_name': value(row, 'D'), 'classification': value(row, 'B'),
                    'derivation': value(row, 'C'), 'basis': {'amount': 100, 'unit': unit},
                    'form_source_text': value(row, 'D'),
                    'form_inference': None, 'form_crosswalk_status': 'source wording only; no equivalence asserted',
                    'food_details': detail, 'details_row': detail_row,
                    'source_row': {'sheet': sheet, 'row': row['number'], 'xml_sha256': row['xml_sha256']},
                    'nutrients': nutrients, 'curated_or_admitted': False,
                }
                record['output_sha256'] = digest(record)
                records.append(record)
        missing = wanted - {r['food_id'] for r in records}
        if missing:
            raise ValueError('Requested IDs absent from bounded window: ' + ','.join(sorted(missing)))
        return {
            'adapter': 'offmenu-worker48-afcd-readonly/1', 'release': 'AFCD Release 3',
            'publication_date': None, 'date_status': 'release identity verified; exact publication date not independently verified',
            'source_url': SOURCE, 'licence_url': LICENCE,
            'licence': 'FSANZ Data User Licence Agreement (CC BY-SA 3.0 AU based); not application relicensing',
            'attribution': '© Food Standards Australia New Zealand — Australian Food Composition Database Release 3',
            'rights_scope': 'Local qualification staging only; preserve FSANZ derivative obligations before publication',
            'country_notice': 'This work is based on Australian data. Australian data may not be appropriate for use in other countries.',
            'limitations': LIMITATION,
            'suitability': 'Generic composition is not product-specific or allergen suitability evidence.',
            'changes': 'Read original workbook cells; preserve units/bases/definitions and hashes; no derived conversions or identity equivalence',
            'source_files': files, 'sheet_members': {name: b.members for name, b in books.items()},
            'profile_rows_examined': scanned, 'records': records,
            'admission': 'pending independent source rights/mapping review',
        }
    finally:
        for book in books.values():
            book.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--food-id', action='append', dest='ids')
    args = parser.parse_args()
    result = adapt(args.directory, tuple(args.ids) if args.ids else DEFAULT_IDS)
    # Summary only: no corpus/sample export on the command line.
    print(json.dumps({'adapter': result['adapter'], 'source_files': result['source_files'],
                      'profile_rows_examined': result['profile_rows_examined'],
                      'records': [{'id': r['id'], 'output_sha256': r['output_sha256'],
                                   'source_row': r['source_row']} for r in result['records']],
                      'admission': result['admission']}, indent=2))


if __name__ == '__main__':
    main()
