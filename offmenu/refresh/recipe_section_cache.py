"""Cache-only partial recipe writer. No PDF, parser, model or file-body access.

The native caller qualifies and holds the cache/receipt/operation evidence. This
module validates supplied immutable bytes and reuses the existing recipe DDL.
Full-template/HTML ingestion remains in recipe_menu_store.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import sqlite3
import time
from datetime import datetime, timezone

from . import recipe_menu_store as store
from .core import canonical, strict_json, RefreshError

VERSION = 'offmenu-recipe-section-cache-store/1'
CACHE_VERSION = 'offmenu-source-faithful-pdf-recipe-section-cache/1'
PARTIAL = 'partial-raw-section-retained; granularity-unknown'


@dataclass(frozen=True)
class CacheSelection:
    run_id: str
    records_path: str
    records_sha256: str
    contract_sha256: str
    review_sha256: str
    operation_sha256: str
    adapter_sha256: str
    expected_records: int
    expected_sections: int


@dataclass(frozen=True)
class SourcePin:
    source_id: str
    release: str
    pdf_sha256: str
    receipt_sha256: str
    expected_records: int


@dataclass(frozen=True)
class PageCache:
    source_id: str
    pdf_page: int
    path: str
    sha256: str
    raw: bytes


@dataclass(frozen=True)
class CacheLimits:
    max_records_bytes: int = 8 * 1024**2
    max_page_bytes: int = 16 * 1024**2
    max_records: int = 256
    max_sections: int = 4096
    max_database_bytes: int = 32 * 1024**2
    max_seconds: int = 30
    max_steps: int = 1000000


def _fail(code):
    raise RefreshError('recipe-section-cache-' + code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _positive(value):
    return type(value) is int and value > 0


def _rows(raw, contract_raw, selection, sources, pages, limits, check):
    if (type(raw) is not bytes or type(contract_raw) is not bytes
            or len(raw) > limits.max_records_bytes or len(contract_raw) > 65536
            or _sha(raw) != selection.records_sha256
            or _sha(contract_raw) != selection.contract_sha256):
        _fail('input-binding')
    contract = strict_json(contract_raw)
    if (type(contract) is not dict or contract.get('version') != CACHE_VERSION
            or contract.get('recordsSHA256') != selection.records_sha256
            or type(contract.get('records')) is not int
            or contract['records'] != selection.expected_records):
        _fail('contract-binding')
    if type(sources) is not tuple or type(pages) is not tuple:
        _fail('selected-evidence')
    source_map = {}
    for pin in sources:
        if (type(pin) is not SourcePin or type(pin.source_id) is not str or not pin.source_id
                or type(pin.release) is not str or not pin.release
                or not store._sha(pin.pdf_sha256) or not store._sha(pin.receipt_sha256)
                or not _positive(pin.expected_records) or pin.source_id in source_map):
            _fail('source-pins')
        source_map[pin.source_id] = pin
    if sum(p.expected_records for p in sources) != selection.expected_records:
        _fail('source-count')
    page_map = {}
    total = 0
    for page in pages:
        check()
        if (type(page) is not PageCache or type(page.path) is not str or not page.path
                or page.source_id not in source_map or not _positive(page.pdf_page)
                or type(page.raw) is not bytes or page.path in page_map):
            _fail('page-selection')
        total += len(page.raw)
        if total > limits.max_page_bytes or _sha(page.raw) != page.sha256:
            _fail('page-bound-or-hash')
        try:
            text = page.raw.decode('utf-8')
        except UnicodeError:
            _fail('page-encoding')
        page_map[page.path] = (page, text)
    result = []
    ordinal = Counter()
    seen = set()
    offset = sections_count = 0
    if not raw.endswith(b'\n'):
        _fail('jsonl-framing')
    for line_no, line in enumerate(raw.splitlines(keepends=True), 1):
        check()
        if line_no > limits.max_records:
            _fail('record-bound')
        r = strict_json(line)
        if (type(r) is not dict or r.get('cacheVersion') != CACHE_VERSION
                or r.get('importReady') is not False
                or any(k not in r or r[k] is not None for k in
                       ('ingredientLines', 'orderedSteps', 'quantityInterpretations'))):
            _fail('raw-grain-required')
        pin = source_map.get(r.get('sourceId'))
        if (pin is None or r.get('release') != pin.release
                or r.get('sourceSHA256') != pin.pdf_sha256
                or type(r.get('sourceReceipt')) is not dict
                or r['sourceReceipt'].get('sha256') != pin.receipt_sha256):
            _fail('source-binding')
        record_id = r.get('recordId')
        if type(record_id) is not str or not record_id or record_id in seen:
            _fail('record-identity')
        seen.add(record_id)
        pdf_pages = r.get('pdfPages')
        if (type(pdf_pages) is not list or len(pdf_pages) != 2
                or not all(_positive(p) for p in pdf_pages)
                or pdf_pages[1] != pdf_pages[0]+1):
            _fail('record-pages')
        ordinal[pin.source_id] += 1
        if ordinal[pin.source_id] > pin.expected_records:
            _fail('source-count')
        by_kind = {}
        anchors = []
        sections = r.get('sections')
        if type(sections) is not list:
            _fail('sections')
        for section in sections:
            check()
            sections_count += 1
            if sections_count > limits.max_sections or type(section) is not dict:
                _fail('section-bound')
            kind = section.get('kind')
            if (kind not in ('title', 'yield-source-text', 'ingredients-section', 'method-section')
                    or kind in by_kind):
                _fail('section-kind')
            by_kind[kind] = section
            item = page_map.get(section.get('textCachePath'))
            if item is None:
                _fail('unselected-page')
            page, text = item
            if (section.get('textCacheSHA256') != page.sha256
                    or page.source_id != pin.source_id
                    or type(section.get('pdfPage')) is not int
                    or section['pdfPage'] != page.pdf_page or page.pdf_page not in pdf_pages):
                _fail('page-binding')
            a, z = section.get('charStart'), section.get('charEnd')
            first, last = section.get('lineStart'), section.get('lineEnd')
            if (type(a) is not int or type(z) is not int or not 0 <= a <= z <= len(text)
                    or not _positive(first) or not _positive(last)):
                _fail('span')
            lines = text.splitlines(keepends=True)
            if (not first <= last <= len(lines)
                    or a != sum(map(len, lines[:first-1])) or z != sum(map(len, lines[:last]))):
                _fail('line-span')
            u, v = len(text[:a].encode('utf-8')), len(text[:z].encode('utf-8'))
            if (section.get('text') != text[a:z]
                    or section.get('textSHA256') != _sha(page.raw[u:v])):
                _fail('section-hash')
            anchors.append(dict(section, utf8ByteRange=[u, v],
                                coordinateSpace='cached UTF8 page; not original PDF bytes'))
        if not {'title', 'ingredients-section', 'method-section'} <= by_kind.keys():
            _fail('required-section')
        ordinal_value = ordinal[pin.source_id]
        key = store._id('raw-section-source', pin.source_id, pin.release,
                        pin.pdf_sha256, record_id, ordinal_value)
        pointer = {'path': selection.records_path, 'sha256': selection.records_sha256, 'line': line_no,
                   'utf8ByteRange': [offset, offset+len(line)],
                   'rawJSONLLineSHA256': _sha(line)}
        source = dict(source_record_key=key, store_release_id=selection.run_id,
                      source_id=pin.source_id, release_id=pin.release, native_record_id=None,
                      source_ordinal=ordinal_value, source_asset_sha256=pin.pdf_sha256,
                      parsed_record_sha256=store._hash(r), record_pointer=canonical(pointer).decode(),
                      citation_id=None, source_payload_json=line.decode('utf-8'), operation_state=PARTIAL)
        yield_text = by_kind.get('yield-source-text', {}).get('text')
        language = r.get('sourceDocumentLanguage')
        if language is not None and type(language) is not str:
            _fail('language')
        variant = dict(recipe_variant_id=store._id('source-recipe', key), source_record_key=key,
                       dish_concept_id=None, original_title=by_kind['title']['text'],
                       language=language or 'und', language_state='source-document-declaration; content-unverified',
                       yield_raw_text=yield_text, yield_value_lexeme=None, yield_unit_lexeme=None,
                       yield_interpreted_value=None, yield_interpreted_unit=None,
                       yield_interpretation_status='raw-source-section; interpretation-unknown' if yield_text is not None else 'not-present-in-selected-cache',
                       dictionary_version=None, mapping_version=None, ingredient_extraction_state=PARTIAL,
                       step_extraction_state=PARTIAL,
                       source_location_json=canonical({'pdfPages': r.get('pdfPages'), 'anchors': anchors}).decode())
        result.append((source, variant))
        offset += len(line)
    if (len(result) != selection.expected_records or sections_count != selection.expected_sections
            or any(ordinal[p.source_id] != p.expected_records for p in sources)):
        _fail('accounting')
    return result, sections_count


def load_cached_recipe_sections(db, raw_records, contract_raw, *, selection, sources, pages,
                               limits=CacheLimits()):
    """Populate a NEW caller-owned DB at raw-section grain, never full-template grain.

    Caller independently binds adapter code, review, source/rights/operation and
    immutable cache custody. Pins are evidence bindings, not permission grants.
    No source/cache file is opened here. All input bytes are supplied explicitly.
    """
    if (type(selection) is not CacheSelection or type(limits) is not CacheLimits
            or type(db) is not sqlite3.Connection or db.in_transaction
            or type(selection.run_id) is not str or not 0 < len(selection.run_id) <= 256
            or type(selection.records_path) is not str or not selection.records_path.startswith('/')
            or not selection.records_path.endswith('.jsonl')
            or any(not store._sha(getattr(selection, k)) for k in
                   ('records_sha256', 'contract_sha256', 'review_sha256', 'operation_sha256', 'adapter_sha256'))
            or not _positive(selection.expected_records) or not _positive(selection.expected_sections)
            or any(not _positive(v) for v in vars(limits).values())
            or selection.expected_records > limits.max_records
            or selection.expected_sections > limits.max_sections
            or limits.max_records_bytes > 8*1024**2 or limits.max_page_bytes > 16*1024**2
            or limits.max_records > 256 or limits.max_sections > 4096
            or limits.max_database_bytes > 32*1024**2
            or limits.max_seconds > 900 or limits.max_steps > 1000000):
        _fail('selection')
    if ([r[1] for r in db.execute('PRAGMA database_list')] != ['main']
            or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') LIMIT 1").fetchone()
            or db.execute('SELECT 1 FROM sqlite_temp_master LIMIT 1').fetchone()):
        _fail('new-empty-store-required')
    # DROP can leave allocated free pages despite an empty schema. SQLite will
    # not lower max_page_count below those pages, so inspect both constraints.
    page_size = db.execute('PRAGMA page_size').fetchone()[0]
    page_count = db.execute('PRAGMA page_count').fetchone()[0]
    max_pages = limits.max_database_bytes // page_size
    if max_pages < 1 or page_count > max_pages:
        _fail('database-size-bound')
    existing_cap = db.execute('PRAGMA max_page_count').fetchone()[0]
    requested_pages = min(max_pages, existing_cap)
    effective_pages = db.execute('PRAGMA max_page_count='+str(requested_pages)).fetchone()[0]
    if not max(1, page_count) <= effective_pages <= requested_pages:
        _fail('database-page-limit')
    started = time.monotonic()
    def check():
        if time.monotonic()-started >= limits.max_seconds:
            _fail('time-bound')
    rows, anchors = _rows(raw_records, contract_raw, selection, sources, pages, limits, check)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=DELETE')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA temp_store=MEMORY')
    db.execute('PRAGMA cache_size=-8192')
    db.execute('PRAGMA mmap_size=0')
    old_length = db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, limits.max_records_bytes+limits.max_page_bytes)
    steps = [0]
    def progress():
        steps[0] += 100
        return int(steps[0] > limits.max_steps or time.monotonic()-started >= limits.max_seconds)
    db.set_progress_handler(progress, 100)
    try:
        db.executescript(store.DDL)
        # Python commit()/rollback() are no-ops with autocommit=True. Own the
        # native SQL transaction explicitly for every accepted idle connection.
        db.execute('BEGIN IMMEDIATE')
        now = datetime.now(timezone.utc).isoformat()
        store._put(db, 'recipe_store_release', dict(store_release_id=selection.run_id,
            input_manifest_sha256=store._hash({'recordsPath': selection.records_path,
                'recordsSha256': selection.records_sha256,
                'contractSha256': selection.contract_sha256, 'reviewSha256': selection.review_sha256,
                'operationSha256': selection.operation_sha256, 'adapterSha256': selection.adapter_sha256,
                'sources': [vars(s) for s in sources]}), parser_id=VERSION, parser_version=VERSION,
            parser_code_sha256=selection.adapter_sha256, state='loading',
            expected_records=selection.expected_records, observed_records=0, exception_count=0,
            created_at=now, completed_at=None))
        for source, variant in rows:
            check()
            store._put(db, 'recipe_source_record', source)
            store._put(db, 'source_recipe_variant', variant)
        if db.execute('PRAGMA foreign_key_check').fetchone():
            _fail('foreign-key')
        check()
        db.execute('UPDATE recipe_store_release SET state=?,observed_records=?,completed_at=? WHERE store_release_id=?',
                   ('completed', len(rows), datetime.now(timezone.utc).isoformat(), selection.run_id))
        db.execute('COMMIT')
        return {'adapterVersion': VERSION, 'cacheGrainComplete': True, 'fullTemplateComplete': False,
                'sourceRows': len(rows), 'partialVariantRows': len(rows), 'anchoredSections': anchors,
                'ingredientRows': 0, 'stepRows': 0, 'logicalIngredientLineCount': None,
                'logicalOrderedStepCount': None, 'importReady': False, 'accepted': False,
                'recordsSha256': selection.records_sha256, 'contractSha256': selection.contract_sha256,
                'reviewSha256': selection.review_sha256, 'operationSha256': selection.operation_sha256,
                'PDFReads': 0, 'modelCalls': 0, 'publication': 'caller closes/fsyncs/qualifies new output separately'}
    except BaseException:
        db.set_progress_handler(None, 0)
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise
    finally:
        db.set_progress_handler(None, 0)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, old_length)
