"""Synthetic-only tests: never obtain or read production source bodies."""
import hashlib
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import signal
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

from offmenu.refresh import media_preparation as m


def _spawn_prepare(payload):
    contract, original, output = payload
    return m.prepare_asset(contract, original, output, time.monotonic() + 10,
                           maximum_output_bytes=128 * m.MiB, minimum_free_bytes=0)


def _abandon_storage_lock(lock, ready):
    lock.acquire()
    ready.set()
    os._exit(0)


def _spawn_terminable_prepare(payload, pid_path, block_handshake=False):
    def fake_parser(*args):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        Path(pid_path).write_text(str(child.pid))
        time.sleep(30)
    m._prepare = fake_parser
    if block_handshake:
        original_json = m.strict_json
        def delayed_handshake(raw):
            value = original_json(raw)
            if isinstance(value, dict) and value.get('phase') == 'session-ready':
                Path(pid_path + '.handshake').write_text('received-not-consumed')
                time.sleep(30)
            return value
        m.strict_json = delayed_handshake
    _spawn_prepare(payload)


def _initialize_overlap_probe(lock, active, peak, barrier):
    m.configure_storage_lock(lock)
    original_prepare = m._prepare
    def measured_prepare(*args):
        with active.get_lock():
            active.value += 1
            peak.value = max(peak.value, active.value)
        try:
            barrier.wait(timeout=5)
            return original_prepare(*args)
        finally:
            with active.get_lock():
                active.value -= 1
    m._prepare = measured_prepare


class _TrackingRLock:
    def __init__(self, lock, active, maximum):
        self.lock, self.active, self.maximum = lock, active, maximum
        self.depth = 0

    def acquire(self, timeout):
        acquired = self.lock.acquire(timeout=timeout)
        if acquired:
            if self.depth == 0:
                with self.active.get_lock():
                    self.active.value += 1
                    self.maximum.value = max(self.maximum.value, self.active.value)
            self.depth += 1
        return acquired

    def release(self):
        self.depth -= 1
        if self.depth == 0:
            with self.active.get_lock():
                self.active.value -= 1
        self.lock.release()


class PreparationTests(unittest.TestCase):
    def setUp(self):
        m.configure_storage_lock(None)
        self.guard_patch = patch.object(m, 'PLANNING_GUARD_BYTES', 0)
        self.guard_patch.start()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = self.root / 'original'
        self.output = self.root / 'prepared'

    def tearDown(self):
        self.temp.cleanup()
        self.guard_patch.stop()
        m.configure_storage_lock(None)

    def contract(self, data, mime, params=None):
        return {'schemaVersion': m.SCHEMA, 'assetId': 'synthetic.asset.v1',
                'expectedSHA256': hashlib.sha256(data).hexdigest(), 'expectedBytes': len(data),
                'expectedMediaTypes': [mime], 'permissions': {'read': True, 'extract': True, 'copy': True},
                'holds': [], 'parameters': params or {}}

    def prepare(self, data, mime, params=None, change=None):
        self.original.write_bytes(data)
        before = self.original.stat()
        contract = self.contract(data, mime, params)
        if change:
            change(contract)
        result = m.prepare_asset(contract, self.original, self.output, time.monotonic() + 15)
        self.assertEqual(data, self.original.read_bytes())
        self.assertEqual((before.st_mtime_ns, before.st_ino),
                         (self.original.stat().st_mtime_ns, self.original.stat().st_ino))
        self.assertEqual(result['networkRequests'], 0)
        self.assertFalse(result['sourceContentsInReport'])
        self.assertFalse(result['normalizationPerformed'])
        self.assertFalse(result['translationPerformed'])
        for output in result['outputs']:
            raw = (self.output / output['outputId']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), output['sha256'])
            self.assertEqual(len(raw), output['bytes'])
            self.assertEqual((self.output / output['outputId']).stat().st_mode & 0o077, 0)
        self.assertNotIn(str(self.root), json.dumps(result))
        return result

    def zip(self, files, compression=zipfile.ZIP_DEFLATED):
        target = io.BytesIO()
        with zipfile.ZipFile(target, 'w', compression=compression) as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        return target.getvalue()

    def assert_failed(self, result, code):
        self.assertEqual(result['errorCode'], code, result)
        self.assertFalse(result['nextStageReady'])
        self.assertEqual(result['outputs'], [])

    def test_csv_preserves_strings_and_counts(self):
        raw = b'name,value\nSecret source title,"001"\nsecond,"a,b"\n'
        result = self.prepare(raw, 'text/csv', {'encoding': 'utf-8', 'delimiter': ',', 'hasHeader': True})
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['recordCount'], 2)
        self.assertNotIn('Secret source', json.dumps(result))
        rows = [json.loads(x) for x in (self.output / result['outputs'][0]['outputId']).read_text().splitlines()]
        self.assertEqual(rows[1]['cells'], ['Secret source title', '001'])

    def test_tsv_explicit_encoding(self):
        data = 'name\tvalue\ncaf\xe9\t2\n'.encode('cp1252')
        result = self.prepare(data, 'text/tab-separated-values',
                              {'encoding': 'cp1252', 'delimiter': '\t', 'hasHeader': True})
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['recordCount'], 1)

    def test_csv_requires_parameters(self):
        self.assert_failed(self.prepare(b'a,b\n1,2\n', 'text/csv'), 'parameters-required')

    def test_inconsistent_csv_fails(self):
        self.assert_failed(self.prepare(b'a,b\n1,2,3\n', 'text/csv',
             {'encoding': 'utf-8', 'delimiter': ',', 'hasHeader': True}), 'parser-invalid-input')

    def test_failed_parser_unremoved_scratch_marks_accounting_uncertain(self):
        raw = b'a,b\n1,2\n1,2,3\n'
        with patch.object(m.shutil, 'rmtree', return_value=None):
            result = self.prepare(raw, 'text/csv',
                 {'encoding': 'utf-8', 'delimiter': ',', 'hasHeader': True})
        self.assert_failed(result, 'parser-invalid-input')
        self.assertEqual(result['outputs'], [])
        self.assertFalse(result['storageAccountingComplete'])
        self.assertTrue(list(self.output.glob('.preparing-*')))
        self.assertEqual(self.original.read_bytes(), raw)

    def test_json_byte_preserved(self):
        data = b'{ "items": [ {"secret": 1.2345678901234567890}, {"x": 2} ] }\n'
        result = self.prepare(data, 'application/json', {'jsonRecordPath': ['items']})
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['recordCount'], 2)
        self.assertEqual((self.output / result['outputs'][0]['outputId']).read_bytes(), data)
        self.assertNotIn('secret', json.dumps(result))

    def test_json_duplicate_key_rejected(self):
        self.assert_failed(self.prepare(b'{"a":1,"a":2}', 'application/json', {'jsonRecordPath': []}),
                           'parser-invalid-input')

    def test_json_nonfinite_rejected(self):
        self.assert_failed(self.prepare(b'[NaN]', 'application/json', {'jsonRecordPath': []}),
                           'parser-invalid-input')

    def test_xml_counts_and_preserves(self):
        data = b'<?xml version="1.0"?><root><item x="source"/><item/></root>'
        result = self.prepare(data, 'application/xml', {'xmlRecordTag': 'item'})
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['recordCount'], 2)
        self.assertEqual((self.output / result['outputs'][0]['outputId']).read_bytes(), data)

    def test_xml_entity_bomb_rejected(self):
        data = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "secret">]><r>&x;</r>'
        self.assert_failed(self.prepare(data, 'application/xml', {'xmlRecordTag': 'r'}), 'xml-unsafe')

    def test_utf16_xml_entity_rejected(self):
        data = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "secret">]><r>&x;</r>'.encode('utf-16')
        self.assert_failed(self.prepare(data, 'application/xml', {'xmlRecordTag': 'r'}), 'xml-unsafe')

    def test_xml_depth_limit(self):
        data = ('<a>' * 129 + '</a>' * 129).encode()
        self.assert_failed(self.prepare(data, 'application/xml', {'xmlRecordTag': 'a'}), 'xml-structure-limit')

    def test_html_ignores_scripts_never_fetches(self):
        data = b'<!doctype html><html><body>Visible secret<script>fetch("https://bad.invalid")</script><img src="https://bad.invalid/image">end</body></html>'
        result = self.prepare(data, 'text/html')
        self.assertEqual(result['status'], 'ready', result)
        output = (self.output / result['outputs'][0]['outputId']).read_text()
        self.assertNotIn('fetch(', output)
        self.assertIn('Visible secret', output)
        self.assertNotIn('Visible secret', json.dumps(result))

    def test_html_error_disguised_as_pdf(self):
        self.assert_failed(self.prepare(b'<!DOCTYPE html><html><title>Access denied</title></html>',
                                       'application/pdf'), 'html-error-response')

    def test_media_mismatch(self):
        self.assert_failed(self.prepare(b'<!doctype html><html><p>ordinary page</p></html>',
                                       'text/csv'), 'media-mismatch')

    def test_no_read_permission_never_opens(self):
        contract = self.contract(b'anything', 'text/plain')
        contract['permissions']['read'] = False
        with patch.object(m, '_read_original', side_effect=AssertionError('must not read')):
            result = m.prepare_asset(contract, '/path/never/open', self.output, time.monotonic() + 1)
        self.assertEqual(result['status'], 'held')
        self.assert_failed(result, 'read-permission-held')
        self.assertFalse(self.output.exists())

    def test_read_hold_never_opens(self):
        contract = self.contract(b'anything', 'text/plain')
        contract['holds'] = ['read']
        with patch.object(m, '_read_original', side_effect=AssertionError('must not read')):
            result = m.prepare_asset(contract, '/path/never/open', self.output, time.monotonic() + 1)
        self.assertEqual(result['status'], 'held')
        self.assert_failed(result, 'read-permission-held')

    def test_extraction_hold_preserves_integrity_stage(self):
        result = self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []},
                              lambda c: c['holds'].append('extract'))
        self.assertEqual(result['stages']['integrity'], 'passed')
        self.assertEqual(result['stages']['media'], 'passed')
        self.assert_failed(result, 'extract-permission-held')
        self.assertFalse(self.output.exists())

    def test_copy_denial_preserves_integrity_stage(self):
        result = self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []},
                              lambda c: c['permissions'].update(copy=False))
        self.assertEqual(result['stages']['integrity'], 'passed')
        self.assert_failed(result, 'copy-permission-held')
        self.assertFalse(self.output.exists())

    def test_hash_mismatch(self):
        self.assert_failed(self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []},
                            lambda c: c.update(expectedSHA256='0' * 64)), 'original-identity-mismatch')

    def test_symlink_original_rejected(self):
        raw = b'[1]'
        actual = self.root / 'actual'
        actual.write_bytes(raw)
        self.original.symlink_to(actual)
        result = m.prepare_asset(self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                                 self.original, self.output, time.monotonic() + 3)
        self.assert_failed(result, 'original-unavailable')

    def test_deadline_exceeded_before_read(self):
        contract = self.contract(b'[1]', 'application/json', {'jsonRecordPath': []})
        with patch.object(m, '_read_original', side_effect=AssertionError('must not read')):
            result = m.prepare_asset(contract, '/never', self.output, time.monotonic() - 1)
        self.assert_failed(result, 'deadline-exceeded')

    def test_zip_unpacks_with_member_contracts_explicitly_pending(self):
        result = self.prepare(self.zip({'path/source.csv': b'a,b\n1,2\n'}), 'application/zip')
        self.assertEqual(result['status'], 'unsupported', result)
        self.assertEqual(result['errorCode'], 'member-contracts-required')
        self.assertEqual(result['stages']['extraction'], 'passed')
        self.assertFalse(result['nextStageReady'])
        self.assertEqual(result['metrics']['archiveMemberCount'], 1)
        self.assertNotIn('source.csv', json.dumps(result))

    def test_zip_traversal_rejected(self):
        self.assert_failed(self.prepare(self.zip({'../secret': b'x'}), 'application/zip'), 'archive-unsafe')

    def test_zip_absolute_rejected(self):
        self.assert_failed(self.prepare(self.zip({'/secret': b'x'}), 'application/zip'), 'archive-unsafe')

    def test_zip_windows_path_rejected(self):
        self.assert_failed(self.prepare(self.zip({'C:\\secret': b'x'}), 'application/zip'), 'archive-unsafe')

    def test_zip_symlink_rejected(self):
        target = io.BytesIO()
        with zipfile.ZipFile(target, 'w') as archive:
            item = zipfile.ZipInfo('link')
            item.create_system = 3
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(item, '/etc/passwd')
        self.assert_failed(self.prepare(target.getvalue(), 'application/zip'), 'archive-unsafe')

    def test_zip_expansion_ratio_rejected(self):
        self.assert_failed(self.prepare(self.zip({'data.txt': b'a' * 1000000}), 'application/zip'),
                           'archive-expansion-limit')

    def test_zip_max_members_plus_private_index_output_bound(self):
        data = self.zip({f'{x}.txt': str(x).encode() for x in range(m.MAX_MEMBERS)})
        result = self.prepare(data, 'application/zip')
        self.assertEqual(result['errorCode'], 'member-contracts-required', result)
        self.assertEqual(len(result['outputs']), m.MAX_OUTPUT_FILES)
        self.assertEqual(result['metrics']['archiveMemberCount'], m.MAX_MEMBERS)

    def test_zip_member_count_rejected(self):
        self.assert_failed(self.prepare(self.zip({f'{x}.txt': b'x' for x in range(513)}), 'application/zip'),
                           'archive-expansion-limit')

    def test_zip_duplicate_casefold_names_rejected(self):
        self.assert_failed(self.prepare(self.zip({'File': b'a', 'file': b'b'}), 'application/zip'),
                           'archive-unsafe')

    def test_zip_unsafe_code_never_written(self):
        self.assert_failed(self.prepare(self.zip({'code.js': b'fetch("bad")'}), 'application/zip'),
                           'archive-unsafe')
        self.assertFalse(self.output.exists())

    def test_docx_paragraphs(self):
        data = self.zip({'[Content_Types].xml': b'<Types/>',
                         'word/document.xml': b'<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Secret text</w:t></w:r></w:p></w:body></w:document>'})
        result = self.prepare(data, m.DOCX)
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['recordCount'], 1)
        self.assertNotIn('Secret text', json.dumps(result))

    def xlsx(self, external=False):
        rel = b'<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
        if external:
            rel = b'<Relationship Id="rId1" Target="https://bad.invalid" TargetMode="External"/>'
        return self.zip({'[Content_Types].xml': b'<Types/>',
                         'xl/workbook.xml': b'<workbook xmlns:r="urn:r"><sheets><sheet name="Secret name" r:id="rId1"/></sheets></workbook>',
                         'xl/_rels/workbook.xml.rels': b'<Relationships>' + rel + b'</Relationships>',
                         'xl/sharedStrings.xml': b'<sst><si><t>Secret cell</t></si></sst>',
                         'xl/worksheets/sheet1.xml': b'<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>'})

    def test_xlsx_preserves_formula_without_evaluation(self):
        result = self.prepare(self.xlsx(), m.XLSX)
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['sheetCount'], 1)
        self.assertEqual(result['metrics']['cellCount'], 2)
        self.assertNotIn('Secret', json.dumps(result))
        rows = [json.loads(x) for x in (self.output / result['outputs'][0]['outputId']).read_text().splitlines()]
        self.assertEqual(rows[0]['cells'][0]['sourceText'], 'Secret cell')
        self.assertEqual(rows[0]['cells'][1]['formula'], '1+1')

    def test_xlsx_external_relationship_rejected(self):
        self.assert_failed(self.prepare(self.xlsx(external=True), m.XLSX), 'archive-unsafe')

    def test_xlsx_invalid_sheet_index(self):
        self.assert_failed(self.prepare(self.xlsx(), m.XLSX, {'sheetIndexes': [3]}), 'parameters-invalid')

    def test_unsupported_compression_explicit(self):
        self.assert_failed(self.prepare(b'\x1f\x8bnot a gzip body', 'application/gzip'), 'unsupported-media')

    def test_missing_pdf_parser_explicit(self):
        caps = m.capabilities()
        caps['optionalParsers']['pypdf'] = {'available': False, 'version': None}
        caps['optionalParsers']['poppler'] = {'available': False, 'version': None}
        with patch.object(m, 'capabilities', return_value=caps):
            result = self.prepare(b'%PDF-1.4\n%%EOF\n', 'application/pdf')
        self.assert_failed(result, 'parser-unavailable')
        self.assertEqual(result['status'], 'unsupported')

    def test_blank_pdf_ocr_needed_explicit(self):
        try:
            from pypdf import PdfWriter
        except ImportError:
            self.skipTest('Optional installed pypdf unavailable')
        data = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(data)
        result = self.prepare(data.getvalue(), 'application/pdf')
        if result['errorCode'] == 'parser-unavailable':
            self.assertFalse(result['nextStageReady'])
            return
        self.assertEqual(result['status'], 'unsupported', result)
        self.assertEqual(result['errorCode'], 'pdf-ocr-required')
        self.assertEqual(result['metrics']['pageCount'], 1)
        self.assertEqual(result['metrics']['ocrNeeded'], 'possible')
        self.assertEqual(result['stages']['extraction'], 'passed')

    def test_invalid_pdf_never_ready(self):
        result = self.prepare(b'%PDF-1.4\ninvalid\n%%EOF\n', 'application/pdf')
        self.assertIn(result['status'], ('failed', 'unsupported'), result)
        if result['status'] == 'unsupported':
            self.assertEqual(result['errorCode'], 'parser-unavailable')
        self.assertFalse(result['nextStageReady'])

    def test_repeat_reuses_identical_outputs(self):
        data = b'[1,2]'
        first = self.prepare(data, 'application/json', {'jsonRecordPath': []})
        second = self.prepare(data, 'application/json', {'jsonRecordPath': []})
        self.assertEqual(first['outputs'], second['outputs'])
        self.assertEqual(len([p for p in self.output.iterdir() if not p.name.startswith('.')]), 1)
        self.assertTrue(second['preparationReused'])

    def test_permissive_output_directory_rejected(self):
        self.output.mkdir(mode=0o755)
        self.output.chmod(0o755)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o755)
        self.assert_failed(self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []}), 'output-unavailable')

    def test_unrecognized_parameters_rejected(self):
        self.assert_failed(self.prepare(b'[1]', 'application/json', {'jsonRecordPath': [], 'url': 'https://bad'}),
                           'contract-invalid')

    def test_bad_permission_type_rejected(self):
        self.assert_failed(self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []},
                            lambda c: c['permissions'].update(extract='yes')), 'contract-invalid')

    def pdf_text(self, pages=1):
        # Minimal original synthetic PDF; no optional generator dependency.
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        page_ids = []
        for number in range(pages):
            page_id = len(objects) + 1
            content_id = page_id + 1
            page_ids.append(page_id)
            objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
            content = f'BT /F1 12 Tf 72 720 Td (Synthetic secret page {number + 1}) Tj ET'.encode()
            objects.append(b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream')
        objects[1] = f'<< /Type /Pages /Kids [{" ".join(str(x) + " 0 R" for x in page_ids)}] /Count {pages} >>'.encode()
        raw = b'%PDF-1.4\n'
        offsets = [0]
        for number, item in enumerate(objects, 1):
            offsets.append(len(raw))
            raw += f'{number} 0 obj\n'.encode() + item + b'\nendobj\n'
        offset = len(raw)
        raw += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
        raw += b''.join(f'{x:010d} 00000 n \n'.encode() for x in offsets[1:])
        raw += f'trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{offset}\n%%EOF\n'.encode()
        return raw

    def test_pdf_text_all_discovered_pages(self):
        result = self.prepare(self.pdf_text(2), 'application/pdf')
        available = m.capabilities()['optionalParsers']
        if not (available['pypdf']['available'] or available['poppler']['available']):
            self.assertEqual(result['errorCode'], 'parser-unavailable')
            return
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['metrics']['pageCount'], 2)
        self.assertEqual(result['metrics']['selectedPageCount'], 2)
        self.assertTrue(result['metrics']['selectedExtentComplete'])
        self.assertNotIn('Synthetic secret', json.dumps(result))

    def test_poppler_fallback_without_pypdf(self):
        caps = m.capabilities()
        if not caps['optionalParsers']['poppler']['available']:
            self.skipTest('Installed Poppler capability unavailable')
        caps['optionalParsers']['pypdf'] = {'available': False, 'version': None}
        with patch.object(m, 'capabilities', return_value=caps):
            result = self.prepare(self.pdf_text(2), 'application/pdf')
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['parser']['name'], 'poppler-pdftotext')
        self.assertEqual(result['metrics']['selectedPageCount'], 2)

    def test_pdf_partial_page_selection_non_ready(self):
        result = self.prepare(self.pdf_text(2), 'application/pdf', {'pageStart': 1, 'pageEnd': 1})
        if result['errorCode'] == 'parser-unavailable':
            return
        self.assertFalse(result['nextStageReady'])
        self.assertEqual(result['errorCode'], 'selection-partial', result)
        self.assertFalse(result['metrics']['selectedExtentComplete'])

    def test_capacity_floor_before_writing(self):
        with patch.object(m.os, 'statvfs', return_value=SimpleNamespace(f_bavail=0, f_frsize=1)):
            result = self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []})
        self.assert_failed(result, 'capacity-floor-protected')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_global_remaining_output_budget_honored(self):
        raw = b'[1,2,3]'
        self.original.write_bytes(raw)
        result = m.prepare_asset(self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                                 self.original, self.output, time.monotonic() + 2,
                                 maximum_output_bytes=3, minimum_free_bytes=0)
        self.assert_failed(result, 'output-limit')
        self.assertEqual(self.original.read_bytes(), raw)

    def test_worker_deadline_kills_and_cleans(self):
        raw = b'[1]'
        self.original.write_bytes(raw)
        def sleepy(*args, **kwargs):
            time.sleep(5)
        with patch.object(m, '_prepare', sleepy):
            result = m.prepare_asset(self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                                     self.original, self.output, time.monotonic() + 0.05)
        self.assert_failed(result, 'deadline-exceeded')
        self.assertEqual(self.original.read_bytes(), raw)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_slow_final_original_read_fails_deadline(self):
        raw = b'[1]'
        self.original.write_bytes(raw)
        original_fdopen = os.fdopen
        class SlowEOF:
            def __init__(self, wrapped): self.wrapped = wrapped
            def __enter__(self): return self
            def __exit__(self, *args): self.wrapped.close()
            def fileno(self): return self.wrapped.fileno()
            def read(self, count):
                data = self.wrapped.read(count)
                if not data: time.sleep(0.02)
                return data
        with patch.object(m.os, 'fdopen', side_effect=lambda *args, **kwargs: SlowEOF(original_fdopen(*args, **kwargs))):
            with self.assertRaises(m.PreparationError) as error:
                m._read_original(self.original, self.contract(raw, 'application/json'), time.monotonic() + 0.01, True)
        self.assertEqual(error.exception.code, 'deadline-exceeded')

    def test_slow_final_output_read_fails_deadline(self):
        raw = b'[1]'
        self.original.write_bytes(raw)
        original_fdopen = os.fdopen
        class SlowEOF:
            def __init__(self, wrapped): self.wrapped = wrapped
            def __enter__(self): return self
            def __exit__(self, *args): self.wrapped.close()
            def fileno(self): return self.wrapped.fileno()
            def read(self, count):
                data = self.wrapped.read(count)
                if not data: time.sleep(0.02)
                return data
        with patch.object(m.os, 'fdopen', side_effect=lambda *args, **kwargs: SlowEOF(original_fdopen(*args, **kwargs))):
            with self.assertRaises(m.PreparationError) as error:
                m._file_hash(self.original, time.monotonic() + 0.01)
        self.assertEqual(error.exception.code, 'deadline-exceeded')

    def test_poppler_capture_stops_at_effective_budget_without_stdin_deadlock(self):
        with patch.dict(m.POPPLER_PATHS, {'pdftotext': sys.executable}):
            with self.assertRaises(m.PreparationError) as error:
                m._poppler('pdftotext', ['-c', 'import sys; sys.stdout.buffer.write(b"x"*100000); sys.stdout.flush(); sys.stdin.buffer.read()'],
                           b'y' * 1000000, time.monotonic() + 2, 7)
        self.assertEqual(error.exception.code, 'output-limit')

    def test_dead_worker_cleans_owned_poppler_process_group(self):
        raw = b'[1]'
        self.original.write_bytes(raw)
        pid_path = self.root / 'synthetic-child-pid'
        def orphan(*args, **kwargs):
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            pid_path.write_text(str(child.pid))
            os.kill(os.getpid(), signal.SIGKILL)
        with patch.object(m, '_prepare', orphan):
            result = m.prepare_asset(self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                                     self.original, self.output, time.monotonic() + 2)
        self.assert_failed(result, 'parser-resource-limit')
        child_pid = int(pid_path.read_text())
        for _ in range(50):
            status = Path(f'/proc/{child_pid}/stat')
            if not status.exists() or status.read_text().split()[2] == 'Z':
                break
            time.sleep(0.01)
        else:
            os.kill(child_pid, signal.SIGKILL)
            self.fail('Owned parser descendant survived worker leader death')

    def test_ready_receipt_reuses_without_parser(self):
        raw = b'[1,2]'
        first = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assertEqual(first['receiptDisposition'], 'written')
        self.assertGreater(first['receiptBytes'], 0)
        with patch.object(m, 'capabilities', side_effect=AssertionError('reuse must not invoke parser')):
            second = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assertTrue(second['preparationReused'])
        self.assertEqual(second['receiptDisposition'], 'verified-reused')
        self.assertEqual(first['outputs'], second['outputs'])
        self.assertEqual(first['receiptSHA256'], second['receiptSHA256'])

    def test_ready_receipt_no_read_hold_wins_before_reuse(self):
        raw = b'[1]'
        first = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        contract = self.contract(raw, 'application/json', {'jsonRecordPath': []})
        contract['holds'] = ['read']
        with patch.object(m, '_read_original', side_effect=AssertionError('held original must not be opened')):
            result = m.prepare_asset(contract, self.original, self.output, time.monotonic() + 1)
        self.assertEqual(result['status'], 'held')
        self.assertFalse(result['preparationReused'])
        self.assertTrue((self.output / first['outputs'][0]['outputId']).exists())

    def test_ready_receipt_extract_hold_wins_before_reuse(self):
        raw = b'[1]'
        self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        with patch.object(m, '_read_ready_receipt', side_effect=AssertionError('hold before receipt')):
            result = self.prepare(raw, 'application/json', {'jsonRecordPath': []},
                                  lambda c: c['holds'].append('extract'))
        self.assert_failed(result, 'extract-permission-held')

    def test_ready_receipt_changed_output_invalidates(self):
        raw = b'[1]'
        first = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        (self.output / first['outputs'][0]['outputId']).write_bytes(b'[9]')
        result = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assert_failed(result, 'receipt-invalid')
        self.assertFalse(result['preparationReused'])
        self.assertEqual(self.original.read_bytes(), raw)

    def test_ready_receipt_wrong_version_invalidates(self):
        raw = b'[1]'
        first = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        path = self.output / '.ready-receipts' / (first['contractSHA256'] + '.json')
        receipt = json.loads(path.read_bytes())
        receipt['result']['handlerVersion'] = 'bounded-structural-preparation/1'
        path.write_text(json.dumps(receipt))
        result = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assert_failed(result, 'receipt-invalid')

    def test_ready_receipt_unknown_metadata_never_echoes(self):
        raw = b'[1]'
        first = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        path = self.output / '.ready-receipts' / (first['contractSHA256'] + '.json')
        receipt = json.loads(path.read_bytes())
        receipt['result']['metrics']['unexpected'] = 'SECRET-RAW-SOURCE'
        path.write_text(json.dumps(receipt))
        result = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assert_failed(result, 'receipt-invalid')
        self.assertNotIn('SECRET-RAW-SOURCE', json.dumps(result))

    def test_receipt_failure_preserves_verified_outputs_and_charges_bytes(self):
        raw = b'[1]'
        with patch.object(m, '_write_ready_receipt', side_effect=m.PreparationError('receipt-write-failed')):
            result = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errorCode'], 'receipt-write-failed')
        self.assertEqual(result['receiptDisposition'], 'write-failed')
        self.assertFalse(result['nextStageReady'])
        self.assertFalse(result['preparationReused'])
        self.assertEqual(sum(x['bytes'] for x in result['outputs']), len(raw))
        self.assertTrue((self.output / result['outputs'][0]['outputId']).exists())

    def test_linked_receipt_durability_failure_keeps_its_bytes_charged(self):
        raw = b'[1]'
        original_fsync = os.fsync
        def fail_receipt_directory(fd):
            path = os.readlink(f'/proc/self/fd/{fd}')
            if path.endswith('/.ready-receipts'):
                raise OSError('synthetic-directory-fsync-failure')
            return original_fsync(fd)
        with patch.object(m.os, 'fsync', side_effect=fail_receipt_directory):
            result = self.prepare(raw, 'application/json', {'jsonRecordPath': []})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errorCode'], 'receipt-write-failed')
        self.assertFalse(result['nextStageReady'])
        receipt = self.output / '.ready-receipts' / (result['contractSHA256'] + '.json')
        self.assertEqual(result['receiptBytes'], receipt.stat().st_size)
        self.assertEqual(result['receiptSHA256'], hashlib.sha256(receipt.read_bytes()).hexdigest())
        self.assertGreater(sum(x['bytes'] for x in result['outputs']), 0)

    def test_receipt_within_worker_storage_grant(self):
        result = self.prepare(b'[1]', 'application/json', {'jsonRecordPath': []})
        used = result['receiptBytes'] + sum(x['bytes'] for x in result['outputs'])
        self.assertLessEqual(used, result['outputBudget']['maximumOutputBytes'])
        receipt = self.output / '.ready-receipts' / (result['contractSHA256'] + '.json')
        self.assertEqual(hashlib.sha256(receipt.read_bytes()).hexdigest(), result['receiptSHA256'])
        self.assertEqual(receipt.stat().st_mode & 0o077, 0)

    def test_spawn_pool_shared_storage_lock_and_reuse(self):
        ctx = multiprocessing.get_context('spawn')
        active, maximum = ctx.Value('i', 0), ctx.Value('i', 0)
        lock = _TrackingRLock(ctx.RLock(), active, maximum)
        payloads = []
        for index in range(3):
            raw = json.dumps([{'n': index}] * 100).encode()
            original, output = self.root / f'original-{index}', self.root / f'prepared-{index}'
            original.write_bytes(raw)
            contract = self.contract(raw, 'application/json', {'jsonRecordPath': []})
            contract['assetId'] = f'synthetic.asset.{index}'
            payloads.append((contract, str(original), str(output)))
        with ProcessPoolExecutor(max_workers=2, mp_context=ctx, initializer=m.configure_storage_lock,
                                 initargs=(lock,)) as pool:
            first = list(pool.map(_spawn_prepare, payloads))
            second = list(pool.map(_spawn_prepare, payloads))
        self.assertTrue(all(x['status'] == 'ready' for x in first), first)
        self.assertTrue(all(x['preparationReused'] for x in second), second)
        self.assertEqual(maximum.value, 1)
        self.assertEqual(active.value, 0)
        self.assertEqual([x['assetId'] for x in first], [p[0]['assetId'] for p in payloads])

    def test_real_spawn_preparation_workers_overlap(self):
        ctx = multiprocessing.get_context('spawn')
        active, peak = ctx.Value('i', 0), ctx.Value('i', 0)
        lock, barrier = ctx.RLock(), ctx.Barrier(2)
        payloads = []
        for index in range(2):
            raw = json.dumps([{'n': index}] * 500).encode()
            original, output = self.root / f'overlap-original-{index}', self.root / f'overlap-prepared-{index}'
            original.write_bytes(raw)
            contract = self.contract(raw, 'application/json', {'jsonRecordPath': []})
            contract['assetId'] = f'synthetic.overlap.{index}'
            payloads.append((contract, str(original), str(output)))
        with ProcessPoolExecutor(max_workers=2, mp_context=ctx, initializer=_initialize_overlap_probe,
                                 initargs=(lock, active, peak, barrier)) as pool:
            results = list(pool.map(_spawn_prepare, payloads))
        self.assertTrue(all(x['status'] == 'ready' for x in results), results)
        self.assertEqual(peak.value, 2)
        self.assertEqual(active.value, 0)

    def test_abandoned_shared_lock_exits_by_deadline(self):
        ctx = multiprocessing.get_context('spawn')
        lock, ready = ctx.RLock(), ctx.Event()
        child = ctx.Process(target=_abandon_storage_lock, args=(lock, ready))
        child.start()
        self.assertTrue(ready.wait(3))
        child.join(3)
        self.assertFalse(child.is_alive())
        m.configure_storage_lock(lock)
        raw = b'[1]'
        self.original.write_bytes(raw)
        start = time.monotonic()
        result = m.prepare_asset(self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                                 self.original, self.output, start + 0.15, minimum_free_bytes=0)
        self.assert_failed(result, 'deadline-exceeded')
        self.assertLess(time.monotonic() - start, 2)

    def test_outer_spawn_sigterm_cleans_inner_parser_group(self):
        ctx = multiprocessing.get_context('spawn')
        raw = b'[1]'
        self.original.write_bytes(raw)
        payload = (self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                   str(self.original), str(self.output))
        pid_path = self.root / 'descendant-pid'
        outer = ctx.Process(target=_spawn_terminable_prepare, args=(payload, str(pid_path)))
        outer.start()
        try:
            for _ in range(300):
                if pid_path.exists():
                    break
                time.sleep(0.01)
            else:
                self.fail('Parser descendant did not start')
            child_pid = int(pid_path.read_text())
            outer.terminate()
            outer.join(3)
            self.assertFalse(outer.is_alive())
            for _ in range(100):
                status = Path(f'/proc/{child_pid}/stat')
                if not status.exists() or status.read_text().split()[2] == 'Z':
                    break
                time.sleep(0.01)
            else:
                os.kill(child_pid, signal.SIGKILL)
                self.fail('Inner parser descendant survived outer SIGTERM')
        finally:
            if outer.is_alive():
                outer.kill()
                outer.join()
        self.assertEqual(self.original.read_bytes(), raw)

    def test_outer_sigterm_before_handshake_consumption_cleans_group(self):
        ctx = multiprocessing.get_context('spawn')
        raw = b'[1]'
        self.original.write_bytes(raw)
        payload = (self.contract(raw, 'application/json', {'jsonRecordPath': []}),
                   str(self.original), str(self.output))
        pid_path = self.root / 'early-descendant-pid'
        marker = Path(str(pid_path) + '.handshake')
        outer = ctx.Process(target=_spawn_terminable_prepare, args=(payload, str(pid_path), True))
        outer.start()
        try:
            for _ in range(300):
                if pid_path.exists() and marker.exists():
                    break
                time.sleep(0.01)
            else:
                self.fail('Pre-consumption handshake window did not start')
            child_pid = int(pid_path.read_text())
            outer.terminate()
            outer.join(3)
            self.assertFalse(outer.is_alive())
            for _ in range(100):
                status = Path(f'/proc/{child_pid}/stat')
                if not status.exists() or status.read_text().split()[2] == 'Z':
                    break
                time.sleep(0.01)
            else:
                os.kill(child_pid, signal.SIGKILL)
                self.fail('Parser descendant survived pre-handshake SIGTERM')
        finally:
            if outer.is_alive():
                outer.kill()
                outer.join()
        self.assertEqual(self.original.read_bytes(), raw)

    def test_sanitized_untrusted_exception(self):
        with patch.object(m, '_read_original', side_effect=OSError('SECRET /private/path')):
            result = m.prepare_asset(self.contract(b'[1]', 'application/json', {'jsonRecordPath': []}),
                                     self.original, self.output, time.monotonic() + 1)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('/private', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
