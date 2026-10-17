#!/usr/bin/env python3
"""Bounded, offline MEXT worksheet adapter. Emits staging proof, never admission.

Reads only the pinned retained main release, using Python's standard library.
Japanese display text excludes OOXML phonetic annotations. No translation,
food equivalence, code crosswalk, or nutrient alias is inferred.
"""
import argparse
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

WORKBOOK = Path('/home/user/src/offmenu-data/national-originals/mext-2023/20260327-mxt_kagsei-mext-000029402_02.xlsx')
SHA256 = '0d5a77077dd6cd91cbc2e6e317b8b218a38728c409eed452f1c10635a0d3099c'
RELEASE = '2023-corrected-20260327-main'
SOURCE_URL = 'https://www.mext.go.jp/content/20260327-mxt_kagsei-mext-000029402_02.xlsx'
SHEETS = ('1穀類', '6野菜類', '9藻類', '10魚介類', '11肉類', '13乳類')
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
MAX_RECORDS = 1000
MANIFEST = WORKBOOK.parents[2] / 'mext-2023-main/manifest.json'
MANIFEST_SHA256 = 'b6da8867f5606c64ac51b6d07be0cb8d2b7e4188f486d83a079c55833ce0b9f1'
ACQUISITION = WORKBOOK.parent / 'acquisition.json'
ACQUISITION_SHA256 = '086f45b4d68ae5696eb6af07e4247c762da96bc4fab909867af70059f5bbb7b5'


@lru_cache(maxsize=1)
def _trusted_workbook():
    """Build source provenance from exact retained bytes, never record metadata."""
    data = WORKBOOK.read_bytes()
    if digest(data) != SHA256:
        raise ValueError('Trusted workbook hash mismatch')
    manifest_bytes, acquisition_bytes = MANIFEST.read_bytes(), ACQUISITION.read_bytes()
    if digest(manifest_bytes) != MANIFEST_SHA256 or digest(acquisition_bytes) != ACQUISITION_SHA256:
        raise ValueError('Retained release/acquisition manifest changed')
    manifest, acquisition = json.loads(manifest_bytes), json.loads(acquisition_bytes)
    acquired = next((x for x in acquisition if x['file'] == WORKBOOK.name), None)
    if manifest['releaseId'] != RELEASE or manifest['archiveSha256'] != SHA256 or acquired != {
        'url': SOURCE_URL, 'file': WORKBOOK.name, 'bytes': len(data), 'sha256': SHA256
    }:
        raise ValueError('Release/workbook/publisher document reference conflict')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        strings = tuple(display_text(si) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS))
        relationships = {x.get('Id'): x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        index = {}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS):
            target = relationships[sheet.get(REL)]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            blob = z.read(member)
            index[sheet.get('name')] = (member, digest(blob), blob)
    return strings, index


@lru_cache(maxsize=19)
def _trusted_sheet(sheet):
    strings, index = _trusted_workbook()
    if sheet not in index:
        raise ValueError('Worksheet is not in pinned workbook')
    member, member_sha, blob = index[sheet]
    headers = {}
    for _, el in ET.iterparse(io.BytesIO(blob), events=('end',)):
        if el.tag == '{' + NS['s'] + '}row':
            row = int(el.get('r'))
            headers[row] = cells(el, strings)
            el.clear()
            if row == 12:
                break
    definitions = schema_from_headers(headers)
    return member, member_sha, digest(canonical(definitions).encode('utf-8')), headers[2]['D2']


def verify_provenance(record):
    source = record['source']
    expected = {'publisher': 'MEXT Japan', 'release': RELEASE, 'url': SOURCE_URL, 'workbookSha256': SHA256}
    if any(source.get(k) != v for k, v in expected.items()):
        raise ValueError('Conflicting source release/workbook/document provenance')
    member, member_sha, schema_sha, basis = _trusted_sheet(source.get('sheet'))
    expected = {'member': member, 'memberSha256': member_sha, 'componentSchemaSha256': schema_sha,
                'basisHeaderCell': 'D2', 'basisHeaderLexical': basis}
    if any(source.get(k) != v for k, v in expected.items()):
        raise ValueError('Conflicting worksheet/member/header provenance')


def verify_source_rows(records):
    """One bounded source pass per requested sheet; reject self-rehashed rows."""
    strings, index = _trusted_workbook()
    requested = {}
    for record in records:
        sheet, row = record['source']['sheet'], record['source']['row']
        if isinstance(row, bool) or not isinstance(row, int) or row < 13:
            raise ValueError('Invalid source row locator')
        if row in requested.setdefault(sheet, {}):
            raise ValueError('Duplicate source row')
        requested[sheet][row] = record
    scanned = 0
    for sheet, wanted in requested.items():
        for _, el in ET.iterparse(io.BytesIO(index[sheet][2]), events=('end',)):
            if el.tag != '{' + NS['s'] + '}row':
                continue
            row = int(el.get('r'))
            values = cells(el, strings)
            if row >= 13 and re.fullmatch(r'\d{5}', values.get('B' + str(row)) or ''):
                scanned += 1
                if scanned > MAX_RECORDS:
                    raise ValueError('Source proof exceeds bounded row-scan limit')
            if row in wanted:
                record = wanted.pop(row)
                if values != record['rawCellsForRoundtrip']:
                    raise ValueError('Record cells differ from pinned worksheet row')
            el.clear()
            if not wanted:
                break
        if wanted:
            raise ValueError('Source row absent from pinned worksheet')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def display_text(element):
    """OOXML rPh text is a reading annotation, not part of the food label."""
    return ''.join(t.text or '' for t in element.findall('s:t', NS) + element.findall('s:r/s:t', NS))


def cells(row, strings):
    result = {}
    for c in row.findall('s:c', NS):
        if c.find('s:f', NS) is not None:
            raise ValueError('Formula cell requires separate cached-value review')
        value = c.find('s:v', NS)
        kind = c.get('t')
        if kind == 's':
            text = strings[int(value.text)] if value is not None else None
        elif kind == 'inlineStr':
            text = display_text(c.find('s:is', NS))
        else:
            text = value.text if value is not None else None
        result[c.get('r')] = text
    return result


def numeric(text):
    """Exact decimal string, or explicit unknown. No parenthesis/trace to zero."""
    result = {'sourceLexical': text, 'valueDecimal': None}
    s = (text or '').strip()
    if s in ('', '-', '—'):
        result['qualifier'] = 'unknown'
    elif s.lower() == 'tr':
        result['qualifier'] = 'trace'
    elif s.startswith('(') and s.endswith(')'):
        result['qualifier'] = 'source-parenthesized-unresolved'
    else:
        try:
            n = Decimal(s)
            if not n.is_finite() or n < 0:
                raise InvalidOperation
            result.update(valueDecimal=str(n), qualifier='source-reported')
        except InvalidOperation:
            result['qualifier'] = 'uninterpreted-source-text'
    return result


def unit_from_header(text):
    if not text:
        return None
    match = re.search(r'(?<![A-Za-z])(kcal|kJ|[μµ]g|mg|g|%)(?![A-Za-z])', text)
    return match.group(1).replace('μ', 'µ') if match else None


def col_number(col):
    n = 0
    for char in col:
        n = n * 26 + ord(char) - ord('A') + 1
    return n


def schema_from_headers(headers):
    codes = headers[12]
    components = []
    active_unit = None
    active_unit_cell = None
    columns = sorted((re.sub(r'\d+', '', c) for c in codes), key=col_number)
    for col in columns:
        raw_unit = headers[11].get(col + '11')
        if unit_from_header(raw_unit):
            active_unit = unit_from_header(raw_unit)
            active_unit_cell = col + '11'
        raw_code = codes[col + '12']
        if not raw_code or col_number(col) < 5:
            continue
        if active_unit is None:
            raise ValueError('Unknown source unit for ' + raw_code)
        components.append({'column': col, 'componentCode': raw_code.strip(), 'componentCodeLexical': raw_code,
                           'unit': active_unit, 'unitHeaderCell': active_unit_cell,
                           'unitHeaderLexical': headers[11][active_unit_cell],
                           'labelCellsJapanese': {col + str(i): headers[i].get(col + str(i)) for i in range(3, 8)}})
    by_code = {x['componentCode']: x for x in components}
    if len(by_code) != len(components):
        raise ValueError('Duplicate component code')
    for code, unit in {'ENERC': 'kJ', 'ENERC_KCAL': 'kcal', 'ID': 'µg', 'RETOL': 'µg', 'VITA_RAE': 'µg', 'NA': 'mg'}.items():
        if by_code.get(code, {}).get('unit') != unit:
            raise ValueError('Source header/unit drift: ' + code)
    basis_text = headers[2].get('D2', '')
    if '100' not in basis_text or '可' not in basis_text:
        raise ValueError('Unverified edible-portion basis')
    return components


def adapt(raw_cells, row_number, sheet, member, components, member_sha):
    def at(col):
        return raw_cells.get(col + str(row_number))
    code, name = at('B'), at('D')
    if not code or not re.fullmatch(r'\d{5}', code) or not name:
        raise ValueError('Missing source code/name')
    form_tokens = [s for s in re.split(r'[\u3000\s]+', name) if s]
    states = [s for s in form_tokens if s in {'生', 'ゆで', '蒸し', '焼き', '乾', '干し', '水煮', 'めし', '油いため', '油揚げ'}]
    observed = []
    for component in components:
        col = component['column']
        observed.append({**component, **numeric(at(col)), 'sourceCell': col + str(row_number),
                         'basis': 'whole-food discard percentage; not edible portion nutrient' if component['componentCode'] == 'REFUSE' else '100 g edible portion as described',
                         'method': 'source sodium chloride equivalent' if component['componentCode'] == 'NACL_EQ' else 'not independently resolved from workbook value'})
    raw_pin = digest(canonical(raw_cells).encode('utf-8'))
    return {'source': {'publisher': 'MEXT Japan', 'release': RELEASE, 'url': SOURCE_URL, 'workbookSha256': SHA256,
                       'sheet': sheet, 'member': member, 'memberSha256': member_sha, 'row': row_number,
                       'recordCellsSha256': raw_pin, 'componentSchemaSha256': digest(canonical(components).encode('utf-8')),
                       'rightsStatus': 'retained manifest claims MEXT use rules; licence capture independent review pending'},
            'foodCode': code, 'sourceIndex': at('C'), 'foodGroup': at('A'),
            'labels': {'ja': name}, 'englishLabelStatus': 'not supplied in inspected Japanese workbook; no translation invented',
            'form': {'originalLabel': name, 'sourceTokens': form_tokens, 'cookingStateTokensJapanese': states,
                     'canonicalCookingState': None, 'status': 'source lexical evidence; semantic mapping review required'},
            'basis': {'amount': 100, 'unit': 'g', 'portion': 'edible', 'preparation': 'as source label describes'},
            'components': observed, 'unmappedCells': {k: v for k, v in raw_cells.items() if re.sub(r'\d+', '', k) not in {x['column'] for x in components} | {'A', 'B', 'C', 'D'}},
            'rawCellsForRoundtrip': raw_cells, 'status': 'unadmitted-source-staging',
            'equivalence': 'none; identical code/name across releases or forms is not nutrient equivalence'}


def roundtrip(record):
    verify_provenance(record)
    raw = record['rawCellsForRoundtrip']
    if digest(canonical(raw).encode('utf-8')) != record['source']['recordCellsSha256']:
        raise ValueError('Record source cells changed')
    row = record['source']['row']
    if raw.get('B' + str(row)) != record['foodCode'] or raw.get('D' + str(row)) != record['labels']['ja']:
        raise ValueError('Identity or label changed')
    if set(record['labels']) != {'ja'} or record['basis'] != {'amount': 100, 'unit': 'g', 'portion': 'edible', 'preparation': 'as source label describes'}:
        raise ValueError('Unsourced label or basis change')
    if record['form']['originalLabel'] != record['labels']['ja'] or record['form']['canonicalCookingState'] is not None:
        raise ValueError('Preparation inference or source form changed')
    schema_keys = ('column', 'componentCode', 'componentCodeLexical', 'unit', 'unitHeaderCell', 'unitHeaderLexical', 'labelCellsJapanese')
    definitions = [{k: c[k] for k in schema_keys} for c in record['components']]
    if digest(canonical(definitions).encode('utf-8')) != record['source']['componentSchemaSha256']:
        raise ValueError('Component definition/unit changed or missing')
    for c in record['components']:
        if c['sourceCell'] != c['column'] + str(row):
            raise ValueError('Component cell locator changed')
        expected_basis = 'whole-food discard percentage; not edible portion nutrient' if c['componentCode'] == 'REFUSE' else '100 g edible portion as described'
        if c['basis'] != expected_basis:
            raise ValueError('Component quantity basis changed')
        expected = numeric(raw.get(c['sourceCell']))
        if any(c[k] != expected[k] for k in expected):
            raise ValueError('Component value/qualifier changed')
    return dict(raw)


def read_records(workbook=WORKBOOK, per_sheet=32, sheets=SHEETS):
    if isinstance(per_sheet, bool) or not isinstance(per_sheet, int) or not 1 <= per_sheet <= MAX_RECORDS:
        raise ValueError('Invalid bounded sample size')
    if not sheets or len(set(sheets)) != len(sheets) or len(sheets) * per_sheet > MAX_RECORDS:
        raise ValueError('At most 1000 records, no duplicate worksheet sampling')
    data = Path(workbook).read_bytes()
    if digest(data) != SHA256:
        raise ValueError('Workbook hash mismatch; source revision review required')
    records = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        strings = [display_text(si) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        relationships = {x.get('Id'): x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        mapping = {s.get('name'): relationships[s.get(REL)] for s in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)}
        for sheet in sheets:
            if sheet not in mapping:
                raise ValueError('Unknown worksheet')
            target = mapping[sheet]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            blob = z.read(member)
            member_sha = digest(blob)
            header, components, count = {}, None, 0
            for _, el in ET.iterparse(io.BytesIO(blob), events=('end',)):
                if el.tag != '{' + NS['s'] + '}row':
                    continue
                row = int(el.get('r'))
                values = cells(el, strings)
                if row <= 12:
                    header[row] = values
                    if row == 12:
                        components = schema_from_headers(header)
                elif re.fullmatch(r'\d{5}', values.get('B' + str(row)) or ''):
                    if components is None:
                        raise ValueError('Missing headers')
                    record = adapt(values, row, sheet, member, components, member_sha)
                    record['source']['basisHeaderCell'] = 'D2'
                    record['source']['basisHeaderLexical'] = header[2]['D2']
                    records.append(record)
                    count += 1
                el.clear()
                if count == per_sheet:
                    break
            if count != per_sheet:
                raise ValueError('Insufficient source records in requested bounded worksheet')
    identities = [(x['source']['release'], x['foodCode']) for x in records]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate source record code in selected sheets')
    return records


def proof(records):
    if not isinstance(records, (list, tuple)) or not 1 <= len(records) <= MAX_RECORDS:
        raise ValueError('Proof requires 1 to 1000 actual source records')
    for record in records:
        roundtrip(record)
    verify_source_rows(records)
    pins = [{'code': r['foodCode'], 'sheet': r['source']['sheet'], 'row': r['source']['row'],
             'sourceCellsSha256': r['source']['recordCellsSha256'], 'memberSha256': r['source']['memberSha256'],
             'adaptedSha256': digest(canonical(r).encode('utf-8'))} for r in records]
    qualifiers = {}
    for r in records:
        for c in r['components']:
            qualifiers[c['qualifier']] = qualifiers.get(c['qualifier'], 0) + 1
    return {'schema': 'offmenu-global-japan-proof/1', 'workbookSha256': SHA256, 'release': RELEASE,
            'sourceUrl': SOURCE_URL, 'sourceManifestSha256': MANIFEST_SHA256,
            'acquisitionSha256': ACQUISITION_SHA256,
            'recordCount': len(records), 'recordPins': pins, 'qualifierCounts': qualifiers,
            'japaneseLabels': len(records), 'englishLabels': 0, 'roundtrip': 'passed exact source-cell lexical/digest checks',
            'recordSetSha256': digest(canonical(pins).encode('utf-8')), 'networkBytes': 0, 'admitted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook', type=Path, default=WORKBOOK)
    parser.add_argument('--per-sheet', type=int, default=32)
    parser.add_argument('--records', action='store_true', help='Emit bounded staging JSON to stdout; no corpus writes')
    args = parser.parse_args()
    records = read_records(args.workbook, args.per_sheet)
    print(json.dumps(records if args.records else proof(records), ensure_ascii=False, indent=2))
