"""Small authored workbooks only; never publisher datasets."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import openpyxl
import unittest
import tempfile
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def raises(error, match=None):
    with unittest.TestCase().assertRaisesRegex(error, match or ".*"):
        yield

from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.national_field_origins import NationalWorkbookOrigins, MEXT_MAIN, policy_sha256

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def close_legacy_workbooks():
    """Historical loaders omit close; test-owned handles are always released."""
    original = openpyxl.load_workbook
    opened = []
    def tracked(*args, **kwargs):
        book = original(*args, **kwargs)
        opened.append(book)
        return book
    try:
        with patch.object(openpyxl, 'load_workbook', tracked):
            yield
    finally:
        for book in opened:
            book.close()


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'tools/data-processing' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(root, name, sheets):
    book = openpyxl.Workbook()
    book.remove(book.active)
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        for row in rows:
            sheet.append(row)
    book.save(root / name)
    book.close()


def pins(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.xlsx')}


def afcd(root):
    save(root, 'Food-Details.xlsx', {'Food details': [
        ['Authored test preface'],
        ['Public Food Key', 'Food Description', 'Sampling Details', 'Specific Gravity', 'Analysed Portion', 'Unanalysed Portion', 'Unused7', 'Unused8', 'Unused9', 'Unused10', 'Unused11'],
        ['F001', 'Authored description', None, 1.02, 'edible', 'peel'],
    ]})
    header = ['Public Food Key', 'Classification', 'Derivation', 'Food Name',
              'Energy with dietary fibre, equated (kJ)', 'Protein (g)', 'Fat, total (g)',
              'Test nutrient (ug)', 'Fatty test (%T)', 'Nitrogen test (mg/gN)']
    save(root, 'Nutrient-profiles.xlsx', {title: [
        ['Authored title'], [], header,
        ['F001', 10, 'calculated', 'Authored food', 418.4, 'TR', '< 0.2', None, 3, 4],
    ] for title in ('All solids & liquids per 100 g', 'Liquids only per 100 mL')})
    module = load('import_afcd.py')
    with close_legacy_workbooks():
        rows = module.records(root)
    for row in rows:
        row['provenance']['releaseId'] = 'authored-afcd-test'
    return module, rows


def mext(root):
    rows = [[None] * 59 for _ in range(15)]
    components = {5:'ENERC', 6:'ENERC_KCAL', 9:'PROT-', 10:'FAT-', 12:'TEST', 58:'VITC'}
    for index, component in components.items():
        rows[2][index] = 'Authored ' + component
        rows[3][index] = 'label'
        rows[4][index] = 'label'
        rows[11][index] = component
    rows[12][:4] = [1, '00001', 2, 'Authored food']
    rows[12][5], rows[12][6], rows[12][9], rows[12][10], rows[12][12], rows[12][58] = 400, '(100)', 'Tr', None, 'text', 0
    rows[13][1] = 'ignored-note'
    rows[14][:4] = [2, '00002', 3, 'Second food']
    save(root, MEXT_MAIN, {'Authored main': rows})
    module = load('collect_mext.py')
    output = root / 'legacy-output'
    with close_legacy_workbooks():
        module.collect(root, output)
    with gzip.open(output / 'normalized.jsonl.gz', 'rt') as stream:
        result = [json.loads(line)[0] for line in stream]
    return module, result


def emitter(source, root, module, row):
    return NationalWorkbookOrigins(source, row['provenance']['releaseId'], root, pins(root), module, policy_pin=policy_sha256())


def test_actual_legacy_adapter_outputs_have_complete_nonmutating_origins(tmp_path, source, build):
    module, rows = build(tmp_path)
    originals = copy.deepcopy(rows)
    with emitter(source, tmp_path, module, rows[0]) as mapping:
        results = [mapping.annotate(row) for row in rows]
        assert results == [mapping.annotate(row) for row in rows]
    assert rows == originals
    for row in results:
        origins = row['provenance']['fieldOrigins']
        assert set(origins) == set(datum_pointers(row['data']))
        assert not field_origin_errors(row, pins(tmp_path), policy_pins=(policy_sha256(),))


def test_afcd_exact_rows_headers_and_joined_metadata(tmp_path):
    module, rows = afcd(tmp_path)
    with emitter('afcd', tmp_path, module, rows[0]) as mapping:
        result = mapping.annotate(rows[0])
    origins = result['provenance']['fieldOrigins']
    assert origins['/data/foodName']['cell'] == 'D4'
    assert origins['/data/description']['cell'] == 'B3'
    assert origins['/data/description']['inputPath'] == 'Food-Details.xlsx'
    assert origins['/data/samplingDetails']['originalValue'] is None
    assert origins['/data/samplingDetails']['cell'] == 'C3'
    name = origins['/data/nutrients/energyKJ/name']['inputs'][0]
    assert name['cell'] == 'E3'
    conversion = origins['/data/nutrients/energy/value']
    assert conversion['transform'] == 'divide'
    assert conversion['inputs'][0]['inputs'][0]['cell'] == 'E4'
    assert conversion['inputs'][0]['inputs'][0]['originalValue'] == 418.4
    assert conversion['inputs'][1]['kind'] == 'constant'
    assert conversion['inputs'][1]['value'] == 4.184
    assert origins['/data/nutrients/energy/detailsRef']['kind'] == 'constant'
    assert origins['/data/nutrients/afcd:column:8/value']['inputs'][0]['cell'] == 'H4'
    assert origins['/data/nutrients/afcd:column:8/qualifier']['inputs'][1]['kind'] == 'constant'


def test_mext_original_text_and_label_inputs(tmp_path):
    module, rows = mext(tmp_path)
    with emitter('mext', tmp_path, module, rows[0]) as mapping:
        result = mapping.annotate(rows[0])
    origins = result['provenance']['fieldOrigins']
    text = origins['/data/nutrients/energy/originalText']['inputs'][0]
    assert text['cell'] == 'G13' and text['originalValue'] == '(100)'
    assert text['sheet'] == 'Authored main'
    assert [x['cell'] for x in origins['/data/nutrients/energy/name']['inputs']] == ['G3', 'G4', 'G5']
    assert origins['/data/nutrients/energy/sourceComponent']['inputs'][0]['cell'] == 'G12'
    assert origins['/data/nutrients/fat/value']['inputs'][0]['cell'] == 'K13'
    assert origins['/data/nutrients/energy/unit']['kind'] == 'constant'
    assert result['data']['nutrients']['vitaminC']['value'] == 0.0


def test_fail_closed_for_unmapped_or_changed_output(tmp_path, source, build, change):
    module, rows = build(tmp_path)
    row = copy.deepcopy(rows[0])
    with emitter(source, tmp_path, module, row) as mapping:
        if change == 'extra': row['data']['invented'] = None
        if change == 'drift': row['data']['foodName'] = 'tampered'
        if change == 'identity': row['id'] += '-different'
        if change == 'release': row['provenance']['releaseId'] = 'wrong'
        with raises(ValueError): mapping.annotate(row)


def test_bad_input_and_policy_pins_rejected(tmp_path):
    module, rows = afcd(tmp_path)
    wrong = pins(tmp_path)
    wrong['Food-Details.xlsx'] = '0' * 64
    with raises(ValueError, match='input-pin'):
        NationalWorkbookOrigins('afcd', 'test', tmp_path, wrong, module, policy_pin=policy_sha256())
    with raises(ValueError, match='policy-pin'):
        NationalWorkbookOrigins('afcd', 'test', tmp_path, pins(tmp_path), module, policy_pin='0' * 64)


def test_formula_cells_fail_closed(tmp_path):
    module, rows = afcd(tmp_path)
    path = tmp_path / 'Nutrient-profiles.xlsx'
    book = openpyxl.load_workbook(path)
    book.worksheets[0]['F4'] = '=1+1'
    book.save(path)
    book.close()
    # Rebuild the historical row, which sees an absent cached result. The
    # provenance mapper must not falsely certify that as a source blank.
    with close_legacy_workbooks():
        rows = module.records(tmp_path)
    for row in rows: row['provenance']['releaseId'] = 'test'
    with emitter('afcd', tmp_path, module, rows[0]) as mapping:
        with raises(ValueError, match='cell-unresolved'): mapping.annotate(rows[0])


def test_duplicate_food_and_nutrient_mapping_fail_closed(tmp_path):
    module, rows = afcd(tmp_path)
    path = tmp_path / 'Nutrient-profiles.xlsx'
    book = openpyxl.load_workbook(path)
    book.worksheets[0].append(['F001', 1, 'method', 'Duplicate'])
    book.save(path)
    book.close()
    with raises(ValueError, match='duplicate-id'):
        emitter('afcd', tmp_path, module, rows[0])


def test_missing_afcd_metadata_header_is_not_fabricated(tmp_path):
    module, rows = afcd(tmp_path)
    path = tmp_path / 'Food-Details.xlsx'
    book = openpyxl.load_workbook(path)
    book.worksheets[0]['C2'] = 'Renamed field'
    book.save(path)
    book.close()
    with emitter('afcd', tmp_path, module, rows[0]) as mapping:
        with raises(ValueError, match='header-unresolved'): mapping.annotate(rows[0])


class NationalFieldOriginTests(unittest.TestCase):
    pass


def _case(function, arguments):
    def run(self):
        with tempfile.TemporaryDirectory() as directory:
            function(Path(directory), **arguments)
    return run

setattr(NationalFieldOriginTests, "test_actual_legacy_adapter_outputs_have_complete_nonmutating_origins_0", _case(test_actual_legacy_adapter_outputs_have_complete_nonmutating_origins, {'source': 'afcd', 'build': afcd}))
setattr(NationalFieldOriginTests, "test_actual_legacy_adapter_outputs_have_complete_nonmutating_origins_1", _case(test_actual_legacy_adapter_outputs_have_complete_nonmutating_origins, {'source': 'mext', 'build': mext}))
setattr(NationalFieldOriginTests, "test_afcd_exact_rows_headers_and_joined_metadata_0", _case(test_afcd_exact_rows_headers_and_joined_metadata, {}))
setattr(NationalFieldOriginTests, "test_mext_original_text_and_label_inputs_0", _case(test_mext_original_text_and_label_inputs, {}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_0", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'afcd', 'build': afcd, 'change': 'extra'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_1", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'afcd', 'build': afcd, 'change': 'drift'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_2", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'afcd', 'build': afcd, 'change': 'identity'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_3", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'afcd', 'build': afcd, 'change': 'release'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_4", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'mext', 'build': mext, 'change': 'extra'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_5", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'mext', 'build': mext, 'change': 'drift'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_6", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'mext', 'build': mext, 'change': 'identity'}))
setattr(NationalFieldOriginTests, "test_fail_closed_for_unmapped_or_changed_output_7", _case(test_fail_closed_for_unmapped_or_changed_output, {'source': 'mext', 'build': mext, 'change': 'release'}))
setattr(NationalFieldOriginTests, "test_bad_input_and_policy_pins_rejected_0", _case(test_bad_input_and_policy_pins_rejected, {}))
setattr(NationalFieldOriginTests, "test_formula_cells_fail_closed_0", _case(test_formula_cells_fail_closed, {}))
setattr(NationalFieldOriginTests, "test_duplicate_food_and_nutrient_mapping_fail_closed_0", _case(test_duplicate_food_and_nutrient_mapping_fail_closed, {}))
setattr(NationalFieldOriginTests, "test_missing_afcd_metadata_header_is_not_fabricated_0", _case(test_missing_afcd_metadata_header_is_not_fabricated, {}))


def test_duplicate_nutrient_projection_rejected(tmp_path):
    module, rows = afcd(tmp_path)
    path = tmp_path / 'Nutrient-profiles.xlsx'
    book = openpyxl.load_workbook(path)
    book.worksheets[0]['H3'] = 'Protein (g)'
    book.save(path)
    book.close()
    with close_legacy_workbooks():
        rows = module.records(tmp_path)
    for row in rows: row['provenance']['releaseId'] = 'test'
    with emitter('afcd', tmp_path, module, rows[0]) as mapping:
        with raises(ValueError, match='field-collision'): mapping.annotate(rows[0])


def test_mext_row_coordinates_skip_notes_without_renumbering(tmp_path):
    module, rows = mext(tmp_path)
    with emitter('mext', tmp_path, module, rows[0]) as mapping:
        result = mapping.annotate(rows[1])
    assert result['provenance']['fieldOrigins']['/data/foodName']['cell'] == 'D15'


def test_numeric_variants_preserve_exact_original(tmp_path, raw):
    module, rows = afcd(tmp_path)
    path = tmp_path / 'Nutrient-profiles.xlsx'
    book = openpyxl.load_workbook(path)
    book.worksheets[0]['F4'] = raw
    book.save(path)
    book.close()
    with close_legacy_workbooks():
        rows = module.records(tmp_path)
    for row in rows: row['provenance']['releaseId'] = 'test'
    with emitter('afcd', tmp_path, module, rows[0]) as mapping:
        result = mapping.annotate(rows[0])
    for pointer, origin in result['provenance']['fieldOrigins'].items():
        if pointer.startswith('/data/nutrients/protein/') and pointer.rsplit('/', 1)[-1] in ('value', 'qualifier', 'originalText', 'limit'):
            assert origin['inputs'][0]['originalValue'] == raw
            assert origin['inputs'][0]['cell'] == 'F4'

setattr(NationalFieldOriginTests, 'test_duplicate_nutrient_projection_rejected', _case(test_duplicate_nutrient_projection_rejected, {}))
setattr(NationalFieldOriginTests, 'test_mext_row_coordinates_skip_notes_without_renumbering', _case(test_mext_row_coordinates_skip_notes_without_renumbering, {}))
for index, raw in enumerate((None, 0, '-', 'TRACE', 'N', 'ND', 'NT', '< 0.01', '1,25', 'source note')):
    setattr(NationalFieldOriginTests, 'test_numeric_variants_' + str(index), _case(test_numeric_variants_preserve_exact_original, {'raw': raw}))
