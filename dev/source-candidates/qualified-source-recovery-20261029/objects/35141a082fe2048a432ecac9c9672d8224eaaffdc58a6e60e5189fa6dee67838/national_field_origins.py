"""Exact AFCD/MEXT workbook origins for the pinned historical candidate adapters.

Call after release identity is stamped, before candidate serialization. This is
not admission, rights approval, source completeness, or canonical qualification.
Only these two reviewed projections are supported. Unmapped/drifted data fails.
"""
import copy
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from .field_provenance import datum_pointers, field_origin_errors

def _cells(sheet, min_row=1, max_row=None):
    """Retain physical positions even for openpyxl's coordinate-free EmptyCell."""
    from openpyxl.utils import get_column_letter
    for row_number, cells in enumerate(sheet.iter_rows(min_row=min_row, max_row=max_row), min_row):
        yield tuple(SimpleNamespace(value=cell.value, data_type=cell.data_type,
                    row=row_number, column=column,
                    coordinate=get_column_letter(column) + str(row_number))
                    for column, cell in enumerate(cells, 1))


MEXT_MAIN = '20260327-mxt_kagsei-mext-000029402_02.xlsx'


def policy_sha256():
    """Pin this exact emitter implementation in the caller's reviewed contract."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _same(left, right):
    return json.dumps(left, sort_keys=True, ensure_ascii=False, allow_nan=False) == json.dumps(right, sort_keys=True, ensure_ascii=False, allow_nan=False)


class NationalWorkbookOrigins:
    """Reusable index of verified source coordinates; annotate one output at a time.

The caller must first verify the historical handler/dependency pins and enforce
its normal bundle bounds. The constructor independently verifies workbook pins.
No workbook formulas are silently treated as blank cached values: formula cells
used by this mapping are rejected until a formula/cached-value policy is reviewed.
The module argument is the already verified historical handler, not a plugin.
"""
    def __init__(self, source_id, release_id, root, input_pins, module, *, policy_pin):
        if source_id not in ('afcd', 'mext') or not release_id:
            raise ValueError('national-origin-source-unsupported')
        if policy_pin != policy_sha256():
            raise ValueError('national-origin-policy-pin-mismatch')
        self.source = source_id
        self.release = release_id
        self.root = Path(root)
        self.pins = dict(input_pins)
        self.module = module
        self.policy = policy_pin
        self.books = {}
        self.tables = {}
        self.details = {}
        try:
            if source_id == 'afcd':
                self._open('Food-Details.xlsx')
                self._open('Nutrient-profiles.xlsx')
                self.details_header, self.details = self._afcd_table('Food-Details.xlsx', 'Food details')
                for sheet, basis in (('All solids & liquids per 100 g', 'g'), ('Liquids only per 100 mL', 'ml')):
                    self.tables[basis] = (sheet, *self._afcd_table('Nutrient-profiles.xlsx', sheet))
            else:
                book = self._open(MEXT_MAIN)
                sheet = book.worksheets[0]
                head = list(_cells(sheet, max_row=12))
                components = head[11]
                if components[6].value != 'ENERC_KCAL' or components[9].value != 'PROT-' or components[58].value != 'VITC':
                    raise ValueError('national-origin-mext-schema-drift')
                rows = {}
                for cells in _cells(sheet, min_row=13):
                    key = str(cells[1].value)
                    if not re.fullmatch(r'\d{5}', key):
                        continue
                    if key in rows:
                        raise ValueError('national-origin-duplicate-id')
                    rows[key] = cells
                self.tables['main'] = (sheet.title, head, rows)
        except Exception:
            self.close()
            raise

    def _open(self, name):
        import openpyxl
        path = self.root / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('national-origin-symlink-rejected')
        if name not in self.pins or _sha(path) != self.pins[name]:
            raise ValueError('national-origin-input-pin-mismatch')
        book = openpyxl.load_workbook(path, read_only=True, data_only=False)
        self.books[name] = book
        return book

    def close(self):
        for book in self.books.values():
            book.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _afcd_table(self, name, title):
        it = _cells(self.books[name][title])
        for cells in it:
            if cells[0].value == 'Public Food Key':
                header = cells
                break
        else:
            raise ValueError('national-origin-afcd-header-missing')
        rows = {}
        for cells in it:
            key = cells[0].value
            if not key or not str(key).startswith('F'):
                continue
            if str(key) in rows:
                raise ValueError('national-origin-duplicate-id')
            rows[str(key)] = cells
        return header, rows

    def _cell(self, file, sheet, cell, record, field):
        if cell.data_type == 'f' or not getattr(cell, 'coordinate', None):
            raise ValueError('national-origin-cell-unresolved')
        # Values must remain JSON scalars, exactly as read, with no text coercion.
        if type(cell.value) not in (str, int, float, bool, type(None)):
            raise ValueError('national-origin-cell-type-unsupported')
        json.dumps(cell.value, allow_nan=False)
        return {'kind': 'source', 'sourceId': self.source, 'releaseId': self.release,
                'inputPath': file, 'inputSha256': self.pins[file],
                'sourceRecordId': record, 'sourceField': field,
                'sheet': sheet, 'row': cell.row, 'column': cell.column,
                'cell': cell.coordinate, 'originalValue': cell.value,
                'originalType': cell.data_type}

    def _constant(self, symbol, value):
        return {'kind': 'constant', 'policySha256': self.policy,
                'symbol': symbol, 'value': value}

    def _derived(self, operation, *inputs):
        return {'kind': 'derived', 'policySha256': self.policy,
                'transform': operation, 'inputs': list(inputs)}

    def annotate(self, row):
        """Return a copy with exact origin coverage; never alter normalized values."""
        if row.get('provenance', {}).get('sourceId') != self.source or row['provenance'].get('releaseId') != self.release:
            raise ValueError('national-origin-release-mismatch')
        expected, origins = {}, {}
        def put(pointer, value, origin):
            if pointer in origins:
                raise ValueError('national-origin-field-collision')
            expected[pointer] = value
            origins[pointer] = origin
        def constant(pointer, value, symbol):
            put(pointer, value, self._constant(symbol, value))
        key = row['provenance']['recordId']
        if self.source == 'afcd':
            self._afcd(row, key, put, constant, expected, origins)
        else:
            self._mext(row, key, put, constant)
        pointers = set(datum_pointers(row['data']))
        if pointers != set(expected):
            raise ValueError('national-origin-unmapped-field')
        for pointer in pointers:
            value = row
            for part in pointer.split('/')[1:]:
                part = part.replace('~1', '/').replace('~0', '~')
                value = value[int(part)] if isinstance(value, list) else value[part]
            if not _same(value, expected[pointer]):
                raise ValueError('national-origin-output-drift:' + pointer)
        result = copy.deepcopy(row)
        result['provenance']['fieldOrigins'] = origins
        errors = field_origin_errors(result, self.pins, policy_pins=(self.policy,))
        if errors:
            raise ValueError('national-origin-invalid:' + ','.join(errors))
        return result

    def _numeric(self, path, raw, origin, parse, put):
        numeric = parse(raw)
        for field, value in numeric.items():
            inputs = [origin]
            if field == 'qualifier' or value is None:
                inputs.append(self._constant('numeric.' + field + '.' + str(value), value))
            put(path + '/' + field, value, self._derived(self.source + '.numeric.' + field, *inputs))
        return numeric

    @staticmethod
    def _path(key):
        return '/data/nutrients/' + key.replace('~', '~0').replace('/', '~1')

    def _afcd(self, output, key, put, constant, expected, origins):
        basis = output['data']['basis']['unit']
        if basis not in self.tables or output['id'] != 'afcd:nutrientProfile:' + key + ':' + basis:
            raise ValueError('national-origin-identity-mismatch')
        sheet, headers, rows = self.tables[basis]
        cells = rows[key]
        file = 'Nutrient-profiles.xlsx'
        def src(index):
            return self._cell(file, sheet, cells[index], key, str(headers[index].value))
        def hdr(index):
            return self._cell(file, sheet, headers[index], 'header', str(headers[index].value))
        for path in ('/data/foodName', '/data/names/en'):
            put(path, cells[3].value, src(3))
        put('/data/identifiers/0/value', str(cells[0].value), self._derived('string', src(0)))
        constant('/data/identifiers/0/system', 'AU-AFCD', 'afcd.identifier-system')
        for field, value in {'amount': 100, 'unit': basis, 'state': 'as-described', 'portion': 'source analysed edible portion'}.items():
            constant('/data/basis/' + field, value, 'afcd.basis.' + basis + '.' + field)
        put('/data/classification', str(cells[1].value), self._derived('string', src(1)))
        put('/data/derivation', cells[2].value, src(2))
        meta = self.details[key]
        labels = [c.value for c in self.details_header[:11]]
        for field, label in {'description':'Food Description', 'samplingDetails':'Sampling Details', 'specificGravity':'Specific Gravity', 'analysedPortion':'Analysed Portion', 'unanalysedPortion':'Unanalysed Portion'}.items():
            if labels.count(label) != 1:
                raise ValueError('national-origin-details-header-unresolved')
            index = labels.index(label)
            origin = self._cell('Food-Details.xlsx', 'Food details', meta[index], key, label)
            put('/data/' + field, meta[index].value, origin)
        nutrient_origins = {}
        for index, cell in enumerate(headers[4:], 4):
            if not cell.value:
                continue
            name = self.module.header(cell.value)
            match = re.search(r'\((kJ|kcal|mg|ug|g|%T|mg/gN)\)$', name)
            if not match:
                raise ValueError('national-origin-unit-unresolved')
            unit = match[1].replace('ug', 'µg')
            label = name[:match.start()].strip()
            component = self.module.CANONICAL.get(label, 'afcd:column:' + str(index + 1))
            path = self._path(component)
            self._numeric(path, cells[index].value, src(index), self.module.national.numeric, put)
            put(path + '/unit', unit, self._derived('afcd.header-unit', hdr(index)))
            put(path + '/name', name, self._derived('whitespace-normalize', hdr(index)))
            put(path + '/sourceColumn', index + 1, self._derived('cell-column-index', src(index)))
            put(path + '/definition', 'AFCD-3:' + label, self._derived('afcd.definition', hdr(index)))
            put(path + '/method', str(cells[2].value), self._derived('string', src(2)))
            constant(path + '/detailsRef', '/afcd-nutrient-details.json', 'afcd.details-ref')
            if unit in ('mg/gN', '%T'):
                amount, unit_basis = (1, 'g-nitrogen') if unit == 'mg/gN' else (100, 'g-total-fatty-acids')
                for field, value in (('amount', amount), ('unit', unit_basis)):
                    put(path + '/basis/' + field, value, self._derived('afcd.unit-basis.' + field, hdr(index), self._constant('afcd.unit-basis.' + unit + '.' + field, value)))
            if component == 'energyKJ':
                nutrient_origins['energyKJ'] = (path, cells[index].value, src(index))
        if 'energyKJ' in nutrient_origins:
            source_path, raw, energy_cell = nutrient_origins['energyKJ']
            numeric = self.module.national.numeric(raw)
            if numeric.get('value') is not None:
                # Copy every inherited leaf from the actual source nutrient, then
                # explicitly account for each overridden conversion field.
                for pointer in list(expected):
                    if not pointer.startswith(source_path + '/'):
                        continue
                    suffix = pointer[len(source_path):]
                    if suffix in ('/value', '/unit', '/method', '/definition'):
                        continue
                    put(self._path('energy') + suffix, expected[pointer], copy.deepcopy(origins[pointer]))
                put(self._path('energy') + '/value', numeric['value'] / 4.184, self._derived('divide', origins[source_path + '/value'], self._constant('afcd.kJ-per-kcal', 4.184)))
                for field, value in {'unit':'kcal', 'method':'unit-converted: source kJ / 4.184', 'definition':'AFCD-3:energy-with-fibre-kcal'}.items():
                    constant(self._path('energy') + '/' + field, value, 'afcd.converted-energy.' + field)

    def _mext(self, output, key, put, constant):
        if output['id'] != 'mext:nutrientProfile:' + key:
            raise ValueError('national-origin-identity-mismatch')
        sheet, head, rows = self.tables['main']
        cells = rows[key]
        def src(cell, field):
            return self._cell(MEXT_MAIN, sheet, cell, key, field)
        for path in ('/data/foodName', '/data/names/ja'):
            put(path, cells[3].value, src(cells[3], 'foodName'))
        for field, index in (('foodGroup', 0), ('sourceIndex', 2)):
            put('/data/' + field, cells[index].value, src(cells[index], field))
        put('/data/identifiers/0/value', str(cells[1].value), self._derived('string', src(cells[1], 'foodNumber')))
        constant('/data/identifiers/0/system', 'JP-MEXT', 'mext.identifier-system')
        for field, value in {'amount':100, 'unit':'g', 'state':'as-described', 'portion':'edible portion'}.items():
            constant('/data/basis/' + field, value, 'mext.basis.' + field)
        for index, component_cell in enumerate(head[11]):
            if index < 5 or not component_cell.value:
                continue
            component = str(component_cell.value).strip()
            component_origin = src(component_cell, 'component')
            path = self._path(self.module.MAP.get(component, 'mext:' + component))
            self._numeric(path, cells[index].value, src(cells[index], component), self.module.numeric, put)
            name_cells = [h[index] for h in head[2:5] if h[index].value is not None]
            name = ' / '.join(dict.fromkeys(str(c.value).strip() for c in name_cells))
            if name_cells:
                put(path + '/name', name, self._derived('mext.label-join-distinct', *(src(c, 'componentName') for c in name_cells)))
            else:
                constant(path + '/name', '', 'mext.empty-component-name')
            constant(path + '/unit', self.module.unit(index), 'mext.column-unit.' + str(index + 1))
            put(path + '/sourceComponent', component, self._derived('strip-string', component_origin))
            put(path + '/sourceColumn', index + 1, self._derived('cell-column-index', component_origin))
            put(path + '/definition', 'MEXT-2023:' + component, self._derived('mext.definition', component_origin))
            method = 'source-derived sodium chloride equivalent' if component == 'NACL_EQ' else 'MEXT source table; original preparation state and qualifier retained'
            constant(path + '/method', method, 'mext.method.' + ('salt-equivalent' if component == 'NACL_EQ' else 'source-table'))
