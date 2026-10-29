from __future__ import annotations
import ast
import copy
import datetime
import gzip
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from offmenu_ciqual import adapter as a
from offmenu_ciqual import xmlxlsx as x
from ciqual_fixture_factory import HEADERS, MAP, XML, archive_bytes, workbook_bytes, write_fixture


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        write_fixture(self.inputs)
        self.lock = a.fixture_lock(self.inputs)

    def render(self):
        return a.render(self.inputs, a.fixture_lock(self.inputs))

    def manifest(self):
        return a.strict_json(self.render()['content-manifest.json'])

    def rows(self):
        return [json.loads(line)[0] for line in gzip.decompress(self.render()['normalized.jsonl.gz']).splitlines()]

    def workbook_parts(self):
        with zipfile.ZipFile(self.inputs / a.WORKBOOK) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def change_part(self, name, transform):
        parts = self.workbook_parts()
        parts[name] = transform(parts[name])
        (self.inputs / a.WORKBOOK).write_bytes(archive_bytes(parts))

    def change_sheet(self, old, new):
        self.change_part('xl/worksheets/sheet1.xml', lambda raw: raw.replace(old, new))

    def held(self, code):
        return self.assertRaisesRegex(a.DataError, '^' + re.escape(code) + '$')

    def test_pinned_legacy_parity(self):
        # Execute only pinned functions, not unrelated AFCD or collector main.
        try:
            import openpyxl
        except ImportError:
            self.fail('Legacy parity needs the repository existing test dependency openpyxl==3.1.5')
        self.assertEqual(openpyxl.__version__, '3.1.5')
        def functions(path, names, namespace):
            tree = ast.parse(path.read_text())
            tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
            exec(compile(tree, str(path), 'exec'), namespace)
        reference = a.ROOT / 'tests/fixtures/ciqual-reference'
        expected = {'collect-national.py': '3f1140b6809d4909a8be415ad51a67ee6677ad57c17d580ec5fbda57edc196e5',
                    'import-national-tables.py': '99216f9ed0aa279b0e15b194c2782dcd8548b86362ea9c55038ad287162cf6c8'}
        for file, digest in expected.items():
            self.assertEqual(a.sha((reference / file).read_bytes()), digest)
        helper = {'datetime': datetime, 'math': math, 're': re}
        functions(reference / 'import-national-tables.py', {'numeric', 'wrap'}, helper)
        namespace = {'national': types.SimpleNamespace(**helper), 'openpyxl': openpyxl, 'ET': ET, 're': re}
        functions(reference / 'collect-national.py', {'ciqual'}, namespace)
        legacy = namespace['ciqual'](self.inputs)
        actual = self.rows()
        self.assertEqual(len(legacy), 3)
        for old, new in zip(legacy, actual):
            for field in ('id', 'kind', 'countries', 'schemaVersion', 'data'):
                self.assertEqual(old[field], new[field])
            for field in ('sourceId', 'recordId', 'url', 'license', 'attribution', 'sourceDate', 'rights'):
                self.assertEqual(old['provenance'][field], new['provenance'][field])

    def test_truthful_candidate_counts(self):
        result = self.manifest()
        self.assertEqual(result['counts']['normalized'], 3)
        self.assertIsNone(result['counts']['accepted'])
        self.assertEqual(result['acceptance'], 'not-performed')
        self.assertFalse(result['completeness']['countryCoverageComplete'])
        self.assertFalse(result['completeness']['selectedScopeComplete'])
        self.assertIn('production-and-cix-unchanged', result['holds'])

    def test_quantity_distinctions(self):
        expected = {None: 'unknown', '': 'unknown', '-': 'unknown', 'TR': 'trace', 'Trace': 'trace',
                    'ND': 'not-detected', 'NOT DETECTED': 'not-detected', 'NT': 'not-tested',
                    'N': 'present-no-reliable-amount', 'unknown': 'source-text'}
        for raw, qualifier in expected.items():
            with self.subTest(raw=raw):
                self.assertEqual(a.numeric(raw)['qualifier'], qualifier)
                self.assertIsNone(a.numeric(raw)['value'])
        self.assertEqual(a.numeric('0'), {'value': 0.0, 'qualifier': 'source'})
        self.assertEqual(a.numeric('1,25')['value'], 1.25)
        self.assertEqual(a.numeric('< 0,01'), {'value': None, 'qualifier': 'less-than', 'limit': 0.01})

    def test_unresolved_text_and_malformed_qualifiers(self):
        for raw in ('1_000', '<1.2.3', '<1e-20', '<-1', '≤0.1', '10 mg', '=1+1'):
            with self.subTest(raw=raw):
                self.assertEqual(a.numeric(raw), {'value': None, 'qualifier': 'source-text', 'originalText': raw})

    def test_nonfinite_underflow_and_shapes_held(self):
        for value in (float('nan'), float('inf'), '-Infinity', '1e309', '1e-9999', True, [], {}):
            with self.subTest(value=value), self.assertRaises(a.DataError):
                a.numeric(value)
        self.assertGreater(a.numeric('5e-324')['value'], 0)
        with self.held('quantity-underflow-held'):
            a.numeric('<0.' + '0' * 400 + '1')

    def test_source_numeric_cell_underflow_held_before_float(self):
        self.change_sheet(b'<v>28.7</v>', b'<v>1e-9999</v>')
        with self.held('quantity-underflow-held'):
            self.render()

    def test_source_numeric_nonfinite_held(self):
        self.change_sheet(b'<v>28.7</v>', b'<v>1e9999</v>')
        with self.held('nonfinite-quantity'):
            self.render()

    def test_boolean_cell_held(self):
        self.change_sheet(b'<c r="K2" t="n"><v>28.7</v>', b'<c r="K2" t="b"><v>1</v>')
        with self.held('unsupported-cell-type'):
            self.render()

    def test_identity_leading_zero_and_native_dictionary_retained(self):
        rows = self.rows()
        self.assertEqual(rows[0]['id'], 'ciqual:nutrientProfile:001')
        self.assertEqual(rows[1]['id'], 'ciqual:nutrientProfile:2')
        metadata = a.strict_json(self.render()['source-metadata.json'])
        self.assertEqual(metadata['identityDictionary']['001']['alim_grp_nom_fr'], 'Groupe fictif')
        self.assertEqual(metadata['columnDictionary'], MAP)

    def test_duplicate_xml_identity_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'</ALIMENTS>', b'<ALIMENT><alim_code>001</alim_code><alim_nom_fr>Another</alim_nom_fr></ALIMENT></ALIMENTS>'))
        with self.held('duplicate-xml-identity'):
            self.render()

    def test_duplicate_workbook_identity_held(self):
        self.change_sheet(b'<c r="G3" t="n"><v>2</v>', b'<c r="G3" t="n"><v>3</v>')
        with self.held('duplicate-workbook-identity'):
            self.render()

    def test_equal_count_different_identity_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'<alim_code>3</alim_code>', b'<alim_code>4</alim_code>'))
        with self.held('workbook-xml-identity-mismatch'):
            self.render()

    def test_missing_identity_or_name_held(self):
        for old, new, code in [(b'<c r="G3" t="n"><v>2</v></c>', b'', 'invalid-native-food-identity'),
                               (b'Synthetic pear', b' ', 'invalid-source-text')]:
            with self.subTest(code=code):
                write_fixture(self.inputs)
                self.change_sheet(old, new)
                with self.held(code):
                    self.render()

    def test_extra_xml_identity_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'</ALIMENTS>', b'<ALIMENT><alim_code>4</alim_code><alim_nom_fr>Extra</alim_nom_fr></ALIMENT></ALIMENTS>'))
        with self.held('workbook-xml-identity-mismatch'):
            self.render()

    def test_ambiguous_xml_field_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'<alim_code>2</alim_code>', b'<alim_code>2</alim_code><alim_code>2</alim_code>'))
        with self.held('ambiguous-identity-field'):
            self.render()

    def test_unreviewed_xml_schema_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'<ALIMENTS>', b'<ALIMENTS xmlns="urn:changed">'))
        with self.held('unreviewed-identity-xml-envelope'):
            self.render()

    def test_header_reorder_drift_held(self):
        self.change_sheet(b'Protein (g/100g)', b'Fat (g/100g)')
        with self.held('workbook-header-drift'):
            self.render()

    def test_header_unit_and_basis_drift_held(self):
        for old, new in [(b'Protein (g/100g)', b'Protein (mg/100g)'), (b'/100g)', b'/100ml)')]:
            with self.subTest(new=new):
                write_fixture(self.inputs)
                self.change_sheet(old, new)
                with self.held('workbook-header-drift'):
                    self.render()

    def test_dictionary_drift_even_if_rehashed_held(self):
        dictionary = copy.deepcopy(MAP)
        dictionary['basis']['unit'] = 'ml'
        (self.inputs / a.DICTIONARY).write_bytes(a.canonical(dictionary))
        with self.held('dictionary-contract-drift'):
            self.render()

    def test_missing_dictionary_and_pin_dependency_held(self):
        for name in a.INPUTS:
            with self.subTest(name=name):
                lock = copy.deepcopy(self.lock)
                lock['inputs'] = [p for p in lock['inputs'] if p['path'] != name]
                with self.held('dependency-set-mismatch'):
                    a.render(self.inputs, lock)

    def test_each_source_hash_and_size_checked(self):
        for name in a.INPUTS:
            with self.subTest(name=name):
                write_fixture(self.inputs)
                path = self.inputs / name
                raw = path.read_bytes()
                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                with self.held('asset-sha256-mismatch'):
                    a.render(self.inputs, self.lock)
                path.write_bytes(raw + b' ')
                with self.held('asset-size-mismatch'):
                    a.render(self.inputs, self.lock)

    def test_asset_release_and_role_held(self):
        for key, value in [('releaseId', '2026'), ('role', 'other')]:
            lock = copy.deepcopy(self.lock)
            lock['inputs'][0][key] = value
            with self.held('input-release-or-role-mismatch'):
                a.render(self.inputs, lock)

    def test_code_contract_runtime_dependency_pins(self):
        for item in self.lock['dependencies']:
            with self.subTest(path=item['path']):
                lock = copy.deepcopy(self.lock)
                next(p for p in lock['dependencies'] if p['path'] == item['path'])['sha256'] = '0' * 64
                with self.held('asset-sha256-mismatch'):
                    a.render(self.inputs, lock)
        lock = copy.deepcopy(self.lock)
        lock['runtime']['expat'] = 'other'
        with self.held('runtime-pin-mismatch'):
            a.render(self.inputs, lock)

    def test_historical_scope_rejected_before_reads(self):
        lock = copy.deepcopy(self.lock)
        lock['scope'] = 'historical-source'
        with patch.object(a, 'read_bytes', side_effect=AssertionError('no reads')), self.held('historical-source-input-not-enabled'):
            a.render('/unreadable', lock)

    def test_input_paths_cannot_escape_inventory(self):
        for path in ('../escape', '/etc/passwd', 'other.json'):
            lock = copy.deepcopy(self.lock)
            lock['inputs'][0]['path'] = path
            with self.held('dependency-set-mismatch'):
                a.render(self.inputs, lock)

    def test_source_symlinks_and_parent_symlinks_held(self):
        target = self.inputs / a.IDENTITIES
        target.unlink()
        target.symlink_to(self.root / 'nope')
        with self.held('input-unavailable-or-symlink'):
            a.render(self.inputs, self.lock)
        link = self.root / 'link'
        link.symlink_to(self.inputs, target_is_directory=True)
        with self.held('directory-unavailable-or-symlink'):
            a.render(link, self.lock)

    def test_source_fifo_rejected_without_wait(self):
        target = self.inputs / a.IDENTITIES
        target.unlink()
        os.mkfifo(target)
        with self.held('regular-file-required'):
            a.render(self.inputs, self.lock)

    def test_strict_json_duplicate_and_nonfinite(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":1e-999}'):
            with self.subTest(raw=raw), self.assertRaises(a.DataError):
                a.strict_json(raw)

    def test_xml_entities_forbidden_in_both_encodings(self):
        text = '<!DOCTYPE ALIMENTS [<!ENTITY x SYSTEM "file:///etc/passwd">]><ALIMENTS>&x;</ALIMENTS>'
        for encoding in ('utf-8', 'utf-16'):
            with self.subTest(encoding=encoding), self.held('xml-doctype-forbidden'):
                x.parse_xml(text.encode(encoding))

    def test_xml_internal_entity_expansion_forbidden(self):
        with self.held('xml-doctype-forbidden'):
            x.parse_xml(b'<!DOCTYPE x [<!ENTITY a "abcdefgh"><!ENTITY b "&a;&a;&a;">]><x>&b;</x>')

    def test_xlsx_xml_doctype_forbidden(self):
        self.change_part('xl/workbook.xml', lambda raw: b'<!DOCTYPE workbook [<!ENTITY x SYSTEM "https://example.invalid/x">]>' + raw)
        with self.held('xml-doctype-forbidden'):
            self.render()

    def test_xml_depth_and_size_bounded(self):
        with self.held('xml-structure-limit'):
            x.parse_xml(b'<a>' * 41 + b'</a>' * 41)
        with patch.object(x, 'MAX_XML', 10), self.held('xml-size-limit'):
            x.parse_xml(b'<a>1234567</a>')

    def test_zip_member_traversal_duplicate_and_binary_held(self):
        for name, code in [('../escape.xml', 'zip-member-name-rejected'), ('/absolute.xml', 'zip-member-name-rejected'),
                           ('xl/macros.bin', 'unsupported-workbook-member')]:
            with self.subTest(name=name):
                parts = self.workbook_parts()
                parts[name] = b'<x/>'
                with self.held(code):
                    x.read_workbook(archive_bytes(parts))
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as z:
            z.writestr('same.xml', b'<x/>')
            with self.assertWarns(UserWarning):
                z.writestr('same.xml', b'<x/>')
        with self.held('zip-member-name-rejected'):
            x.read_workbook(raw.getvalue())

    def test_zip_count_member_expansion_and_ratio_bounded(self):
        raw = (self.inputs / a.WORKBOOK).read_bytes()
        with patch.object(x, 'MAX_ARCHIVE', 100), self.held('archive-size-limit'):
            x.read_workbook(raw)
        with patch.object(x, 'MAX_MEMBERS', 1), self.held('zip-member-limit'):
            x.read_workbook(raw)
        with patch.object(x, 'MAX_XML', 100), self.held('zip-member-bounds'):
            x.read_workbook(raw)
        with patch.object(x, 'MAX_EXPANDED', 100), self.held('zip-expanded-size-limit'):
            x.read_workbook(raw)
        with self.held('zip-member-bounds'):
            x.read_workbook(archive_bytes({'x.xml': '<x>' + 'a' * 5_000_000 + '</x>'}))

    def test_zip_symlink_held(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as z:
            info = zipfile.ZipInfo('x.xml')
            info.external_attr = 0o120777 << 16
            z.writestr(info, b'<x/>')
        with self.held('zip-member-type-rejected'):
            x.read_workbook(raw.getvalue())

    def test_external_relationships_held(self):
        for target in ('https://example.invalid/data', '//example.invalid/data', '../outside.xml'):
            with self.subTest(target=target):
                write_fixture(self.inputs)
                self.change_part('xl/_rels/workbook.xml.rels', lambda raw: raw.replace(b'Target="worksheets/sheet1.xml"', ('Target="' + target + '"').encode()))
                with self.held('external-or-unsafe-relationship'):
                    self.render()

    def test_undeclared_worksheet_and_extra_declared_sheet_held(self):
        parts = self.workbook_parts()
        parts['xl/worksheets/sheet2.xml'] = parts['xl/worksheets/sheet1.xml']
        with self.held('undeclared-worksheet'):
            x.read_workbook(archive_bytes(parts))
        self.change_part('xl/workbook.xml', lambda raw: raw.replace(b'</sheets>', b'<sheet name="extra" sheetId="2" r:id="rId2"/></sheets>'))
        with self.held('single-worksheet-required'):
            self.render()

    def test_duplicate_semantic_containers_held(self):
        cases = [
            ('xl/workbook.xml', b'</workbook>', b'<sheets/></workbook>', 'ambiguous-workbook-sheets'),
            ('xl/worksheets/sheet1.xml', b'</worksheet>', b'<sheetData/></worksheet>', 'ambiguous-worksheet-container'),
            ('xl/worksheets/sheet1.xml', b'</worksheet>', b'<dimension ref="A1"/></worksheet>', 'ambiguous-worksheet-container')]
        for name, old, new, code in cases:
            with self.subTest(code=code, new=new):
                write_fixture(self.inputs)
                self.change_part(name, lambda raw: raw.replace(old, new))
                with self.held(code):
                    self.render()

    def test_nested_numeric_and_text_values_held(self):
        for old, new, code in [
            (b'<v>28.7</v>', b'<v>28.7<extra>999</extra></v>', 'nested-or-unsupported-numeric-content'),
            (b'Synthetic pear</t>', b'Synthetic pear<extra>other</extra></t>', 'nested-or-unsupported-text-content')]:
            with self.subTest(code=code):
                write_fixture(self.inputs)
                self.change_sheet(old, new)
                with self.held(code):
                    self.render()

    def test_ambiguous_plain_or_rich_strings_held(self):
        namespace = ' xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        for inner in ('<t>a</t><t>b</t>', '<t>a</t><r><t>b</t></r>', '<r><t>a</t><t>b</t></r>'):
            with self.subTest(inner=inner), self.held('ambiguous-string-content'):
                x._string(x.parse_xml(('<is' + namespace + '>' + inner + '</is>').encode()))

    def test_mixed_cell_container_value_text_held(self):
        self.change_sheet(b'<c r="K2" t="n"><v>28.7</v></c>', b'<c r="K2" t="n">99<v>28.7</v>77</c>')
        with self.held('mixed-structural-content'):
            self.render()

    def test_mixed_rich_run_value_text_held(self):
        self.change_sheet(b'<is><t xml:space="preserve">Synthetic apple</t></is>', b'<is><r>discarded<t>Synthetic apple</t>also discarded</r></is>')
        with self.held('ambiguous-string-content'):
            self.render()

    def test_invalid_content_type_envelope_or_type_held(self):
        self.change_part('[Content_Types].xml', lambda raw: b'<ignored/>')
        with self.held('invalid-content-types-envelope'):
            self.render()
        write_fixture(self.inputs)
        self.change_part('[Content_Types].xml', lambda raw: raw.replace(b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml', b'application/vnd.ms-excel.sheet.macroEnabled.main+xml'))
        with self.held('unreviewed-workbook-content-type'):
            self.render()

    def test_root_workbook_relationship_cannot_disagree(self):
        self.change_part('_rels/.rels', lambda raw: raw.replace(b'xl/workbook.xml', b'xl/not-the-workbook.xml'))
        with self.held('unresolved-root-workbook-relationship'):
            self.render()

    def test_shared_string_dependency_relationship_required(self):
        (self.inputs / a.WORKBOOK).write_bytes(workbook_bytes(shared_strings=True))
        self.change_part('xl/_rels/workbook.xml.rels', lambda raw: raw.replace(b'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>', b''))
        with self.held('unresolved-workbook-dictionary-relationship'):
            self.render()

    def test_malformed_bound_and_xml_envelope_held(self):
        (self.inputs / a.IDENTITIES).write_bytes(XML.replace(b'<ALIMENTS>', b'<ALIMENTS>unrecognized content'))
        with self.held('unreviewed-identity-xml-envelope'):
            self.render()

    def test_formula_cached_values_forbidden(self):
        self.change_sheet(b'<v>28.7</v>', b'<f>1+1</f><v>28.7</v>')
        with self.held('formula-or-extension-forbidden'):
            self.render()

    def test_unreviewed_date_style_held(self):
        self.change_sheet(b'<c r="K2"', b'<c s="1" r="K2"')
        with self.held('unreviewed-number-style'):
            self.render()

    def test_inflated_dimensions_and_rows_held(self):
        self.change_sheet(b'A1:BU4', b'A1:XFD1048576')
        with self.held('worksheet-dimension-limit'):
            self.render()

    def test_duplicate_row_and_cell_held(self):
        self.change_sheet(b'<row r="3">', b'<row r="2">')
        with self.held('duplicate-or-unordered-row'):
            self.render()
        write_fixture(self.inputs)
        self.change_sheet(b'<c r="K2"', b'<c r="J2"')
        with self.held('duplicate-or-unordered-cell'):
            self.render()

    def test_shared_strings_match_inline(self):
        before = self.rows()
        (self.inputs / a.WORKBOOK).write_bytes(workbook_bytes(shared_strings=True))
        after = self.rows()
        for row in before + after:
            row['provenance'].pop('inputBundleSha256')
        self.assertEqual(before, after)

    def test_unresolved_shared_string_held(self):
        (self.inputs / a.WORKBOOK).write_bytes(workbook_bytes(shared_strings=True))
        self.change_sheet(b'<v>0</v>', b'<v>999999</v>')
        with self.held('unresolved-shared-string'):
            self.render()

    def test_deterministic_paths_mtimes_and_inventory_order(self):
        baseline = a.render(self.inputs, self.lock)
        other = self.root / 'elsewhere'
        shutil.copytree(self.inputs, other)
        for path in other.iterdir():
            os.utime(path, (100000, 100000))
        lock = copy.deepcopy(self.lock)
        lock['inputs'].reverse()
        lock['dependencies'].reverse()
        self.assertEqual(baseline, a.render(other, lock))

    def test_canonical_gzip_header(self):
        raw = self.render()['normalized.jsonl.gz']
        self.assertEqual(raw[:4], b'\x1f\x8b\x08\x00')
        self.assertEqual(raw[4:8], b'\x00' * 4)
        self.assertEqual(raw[9], 255)

    def test_adjacent_files_not_discovered(self):
        before = self.render()
        (self.inputs / 'secret.txt').write_text('not read')
        self.assertEqual(before, self.render())

    def test_immutable_build_retry_and_tamper(self):
        output = self.root / 'candidate'
        first = a.build(self.inputs, self.lock, output)
        self.assertEqual(first, a.build(self.inputs, self.lock, output))
        (output / 'source-metadata.json').write_text('tampered')
        with self.held('existing-candidate-conflict'):
            a.build(self.inputs, self.lock, output)

    def test_failed_input_does_not_create_candidate(self):
        output = self.root / 'candidate'
        (self.inputs / a.IDENTITIES).write_bytes(b'invalid')
        with self.assertRaises(a.DataError):
            a.build(self.inputs, self.lock, output)
        self.assertFalse(output.exists())

    def test_interrupted_before_rename_leaves_no_candidate(self):
        output = self.root / 'candidate'
        with patch.object(a.os, 'rename', side_effect=OSError('simulated interruption')), self.assertRaises(OSError):
            a.build(self.inputs, self.lock, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob('.ciqual-stage-*')), [])

    def test_reuse_30_day_policy_no_timestamp_content_key(self):
        bundle = self.manifest()['inputBundleSha256']
        before = self.render()
        evidence = {'scope': 'synthetic-fixture', 'inputBundleSha256': bundle,
                    'acquiredAt': '2026-09-01T00:00:00Z', 'revalidations': []}
        at = '2026-09-30T23:59:59Z'
        self.assertEqual(a.plan_reuse(evidence, bundle, at)['action'], 'reuse-verified-retained-input')
        self.assertEqual(a.plan_reuse(evidence, bundle, '2026-10-01T00:00:00Z')['action'], 'revalidation-review-needed')
        evidence['revalidations'].append({'at': '2026-09-30T00:00:00Z', 'result': '304', 'inputBundleSha256': bundle})
        self.assertEqual(a.plan_reuse(evidence, bundle, '2026-10-01T00:00:00Z')['ageSeconds'], 30 * 86400)
        self.assertEqual(before, self.render())

    def test_evidence_cannot_confer_rights_or_rebase_acquisition(self):
        bundle = self.manifest()['inputBundleSha256']
        evidence = {'scope': 'synthetic-fixture', 'inputBundleSha256': bundle,
                    'acquiredAt': '2026-09-01T00:00:00Z', 'revalidations': [
                        {'at': '2026-09-30T00:00:00Z', 'result': '200-identical', 'inputBundleSha256': bundle}]}
        result = a.plan_reuse(evidence, bundle, '2026-10-02T00:00:00Z')
        self.assertEqual(result['sourceUsePermission'], 'not-established')
        self.assertFalse(result['acquisitionAllowed'])
        self.assertEqual(result['ageSeconds'], 31 * 86400)

    def test_cli_offline_python_audit(self):
        lock_path = self.root / 'lock.json'
        lock_path.write_bytes(a.canonical(self.lock))
        code = '''import sys
def deny(event, args):
    if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in ('os.system', 'os.posix_spawn'):
        raise RuntimeError('network or process forbidden by test')
sys.addaudithook(deny)
from offmenu_ciqual.adapter import main
raise SystemExit(main(sys.argv[1:]))
'''
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(a.ROOT)}
        result = subprocess.run([sys.executable, '-c', code, '--inputs', str(self.inputs),
            '--lock', str(lock_path), '--output', str(self.root / 'cli-output')],
            capture_output=True, text=True, env=env, timeout=15, cwd=a.ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['normalized'], 3)


if __name__ == '__main__':
    unittest.main()
