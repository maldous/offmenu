#!/usr/bin/env python3
"""Import AFCD Release 3 with separate mass/volume bases and source notices.

Normalized AFCD data remains under the FSANZ Data User Licence Agreement.
This does not relicense the application or other independent datasets.
"""
import argparse, base64, datetime, gzip, hashlib, importlib.util, json, re, unicodedata
from pathlib import Path
import openpyxl

spec = importlib.util.spec_from_file_location('national', Path(__file__).with_name('import_national_tables.py'))
national = importlib.util.module_from_spec(spec)
spec.loader.exec_module(national)
URL = 'https://www.foodstandards.gov.au/science-data/food-nutrient-databases/afcd/data-files'
LICENSE = 'https://www.foodstandards.gov.au/science-data/monitoringnutrients/afcd/datauserlicenceagreement'
LIMITATION = ('There are limitations associated with food composition databases. Food composition data used in the database or databases may represent an average of the nutrient content of a particular sample of foods and ingredients, determined at a particular time. The nutrient composition of foods and ingredients can vary substantially between batches and brands because of a number of factors, including changes in season, processing practices and ingredient source, and methods of calculation.')
CANONICAL = {'Energy with dietary fibre, equated': 'energyKJ', 'Protein': 'protein', 'Fat, total': 'fat',
             'Total dietary fibre': 'fibre', 'Available carbohydrate, without sugar alcohols': 'carbohydrate',
             'Total sugars': 'sugars', 'Added sugars': 'addedSugars', 'Free sugars': 'freeSugars',
             'Calcium (Ca)': 'calcium', 'Iron (Fe)': 'iron', 'Potassium (K)': 'potassium',
             'Sodium (Na)': 'sodium', 'Vitamin C': 'vitaminC',
             'Total saturated fatty acids, equated': 'saturatedFat'}

def header(value):
    return ' '.join(str(value).split())

def rows(sheet):
    it = sheet.iter_rows(values_only=True)
    for row in it:
        if row[0] == 'Public Food Key':
            return list(row), [r for r in it if r[0] and str(r[0]).startswith('F')]
    raise ValueError('Missing AFCD header')

def records(directory):
    details_header, details_rows = rows(openpyxl.load_workbook(directory / 'Food-Details.xlsx', read_only=True, data_only=True)['Food details'])
    details = {r[0]: dict(zip(details_header[:11], r[:11])) for r in details_rows}
    workbook = openpyxl.load_workbook(directory / 'Nutrient-profiles.xlsx', read_only=True, data_only=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    output = []
    for sheet_name, basis_unit in [('All solids & liquids per 100 g', 'g'), ('Liquids only per 100 mL', 'ml')]:
        headers, values = rows(workbook[sheet_name])
        for row in values:
            nutrients = {}
            for i, raw_name in enumerate(headers[4:], 4):
                if not raw_name:
                    continue
                name = header(raw_name)
                unit_match = re.search(r'\((kJ|kcal|mg|ug|g|%T|mg/gN)\)$', name)
                if not unit_match:
                    raise ValueError('Unknown nutrient unit: ' + name)
                unit = unit_match[1].replace('ug', 'µg')
                label = name[:unit_match.start()].strip()
                key = CANONICAL.get(label, 'afcd:column:' + str(i + 1))
                nutrients[key] = {**national.numeric(row[i]), 'unit': unit, 'name': name,
                                  'sourceColumn': i + 1, 'definition': 'AFCD-3:' + label,
                                  'method': str(row[2]), 'detailsRef': '/afcd-nutrient-details.json'}
                if unit == 'mg/gN':
                    nutrients[key]['basis'] = {'amount': 1, 'unit': 'g-nitrogen'}
                if unit == '%T':
                    nutrients[key]['basis'] = {'amount': 100, 'unit': 'g-total-fatty-acids'}
            if nutrients.get('energyKJ', {}).get('value') is not None:
                nutrients['energy'] = {**nutrients['energyKJ'], 'value': nutrients['energyKJ']['value'] / 4.184,
                                       'unit': 'kcal', 'method': 'unit-converted: source kJ / 4.184',
                                       'definition': 'AFCD-3:energy-with-fibre-kcal'}
            code = str(row[0]) + ':' + basis_unit
            meta = details[str(row[0])]
            output.append({'schemaVersion': '1.0', 'kind': 'nutrientProfile', 'id': 'afcd:nutrientProfile:' + code,
                'countries': ['AU'], 'provenance': {'sourceId': 'afcd', 'recordId': str(row[0]), 'url': URL,
                    'license': 'FSANZ Data User Licence Agreement (CC BY-SA 3.0 AU based)', 'licenseUrl': LICENSE,
                    'attribution': 'Food Standards Australia New Zealand — Australian Food Composition Database Release 3',
                    'visibility': 'public', 'fetchedAt': now, 'sourceDate': '2025-12',
                    'transform': 'offmenu-afcd/1.0', 'changes': 'Converted workbook rows to the OffMenu schema; energy kcal derived from source kJ.',
                    'limitationStatement': LIMITATION, 'countryNotice': 'This work is based on Australian data. Australian data may not be appropriate for use in other countries.',
                    'rights': 'Normalized AFCD derivative data is distributed under the FSANZ Data User Licence Agreement.'},
                'data': {'foodName': row[3], 'names': {'en': row[3]}, 'identifiers': [{'system': 'AU-AFCD', 'value': str(row[0])}],
                    'basis': {'amount': 100, 'unit': basis_unit, 'state': 'as-described', 'portion': 'source analysed edible portion'},
                    'description': meta.get('Food Description'), 'samplingDetails': meta.get('Sampling Details'),
                    'classification': str(row[1]), 'derivation': row[2],
                    'specificGravity': meta.get('Specific Gravity'), 'analysedPortion': meta.get('Analysed Portion'),
                    'unanalysedPortion': meta.get('Unanalysed Portion'), 'nutrients': nutrients}})
    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = records(args.directory)
    assert len(data) == 1801 and len({r['id'] for r in data}) == 1801
    lines = []
    for record in data:
        packed = 'gz:' + base64.b64encode(gzip.compress(json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0)).decode()
        search = ''.join(c for c in unicodedata.normalize('NFKD', record['data']['foodName'].casefold()) if not unicodedata.combining(c))
        values = ['public:afcd', record['id'], 'nutrientProfile', 'afcd', '["AU"]', packed, record['provenance']['fetchedAt'], search]
        lines.append('INSERT INTO unified_records(owner,id,kind,source_id,countries,document,updated_at,search_text) VALUES(' + ','.join(national.sqltext(v) for v in values) + ') ON CONFLICT(owner,id) DO UPDATE SET document=excluded.document,updated_at=excluded.updated_at,search_text=excluded.search_text;')
    args.output.write_text('\n'.join(lines))
    manifest = {'source': 'afcd', 'release': 3, 'uniqueFoods': 1588, 'massBasisRecords': 1588,
                'volumeBasisRecords': 213, 'records': len(data), 'sqlMD5': hashlib.md5(args.output.read_bytes()).hexdigest(),
                'sourceFiles': [{'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(args.directory.glob('*.xlsx'))]}
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2))
    metadata = openpyxl.load_workbook(args.directory / 'Nutrient-details.xlsx', read_only=True, data_only=True)
    definitions = {s.title: [[x for x in row[:9]] for row in s.iter_rows(values_only=True) if any(v is not None for v in row[:9])] for s in metadata if s.title != 'Contents'}
    (Path(__file__).resolve().parents[2] / 'apps/web/assets/afcd-nutrient-details.json').write_text(json.dumps({'sourceId': 'afcd', 'release': 3, 'licenseUrl': LICENSE, 'limitationStatement': LIMITATION, 'countryNotice': 'Australian data may not be appropriate for use in other countries.', 'changes': 'Workbook rows serialized to JSON.', 'definitions': definitions}, ensure_ascii=False))
    print(json.dumps(manifest))

if __name__ == '__main__':
    main()
