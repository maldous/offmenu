"""Source-faithful retained recipe/menu and ingredient adapters.

This is an additive staging adapter, not a production-store migration or a claim
of corpus acceptance. No downloads, installs, translation, food matching or unit
conversion occur. Every projected record retains its original object; JSON input
also retains exact record JSON. Raw mentions are never normalized food entities.
"""
from __future__ import annotations

import csv
import ast
import gzip
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

from ingest_api import BudgetExceeded, COUNTERS, SourceChanged, source_key

VERSION = 'offmenu-retained-recipe-ingest/1'
HTML_PARSER_SHA256 = '843d7808881d39cfb65ad8db1bbc4604ea9706d54bc504854b88664e0c9887f2'
HTML_SCHEMA_SHA256 = '6c450429cea05a719bd367116cda978b465c44ab5f0e65c6fa0dc7a80ef57814'
CACHE_VERSION = 'offmenu-source-faithful-pdf-recipe-section-cache/1'
COLLECTIONS = frozenset(('recipes', 'records', 'items', 'data', 'results', 'foods',
                         'ingredients', 'menuItems', 'menus', '@graph', 'hits', 'pages', 'query'))
RECIPE_FIELDS = ('ingredientLines', 'recipeIngredient', 'ingredients', 'ingredient_list')
STEP_FIELDS = ('orderedSteps', 'recipeInstructions', 'instructions', 'directions',
               'steps', 'method', 'procedure')
MAX_RECORD = 8 * 1024 * 1024


class UnsupportedSource(ValueError):
    pass


class MalformedRecord(ValueError):
    pass


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(obj):
    return hashlib.sha256(_json(obj).encode('utf-8')).hexdigest()


def _pointer(base, key):
    return base + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _strict(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise MalformedRecord('duplicate_json_key')
            result[key] = value
        return result
    def nonfinite(_):
        raise MalformedRecord('nonfinite_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _error(context, source, exc, stats):
    stats['errors'] += 1
    context.report_error(source, exc)


def _open(source):
    """Held read-only regular file, no symlink components; gzip stays streaming."""
    path = Path(os.path.abspath(source['path']))
    # Traverse exact known paths without requesting directory listing access.
    # O_PATH retains descriptor anchoring and O_NOFOLLOW on Linux; no ACL change.
    parent_flags = getattr(os, 'O_PATH', os.O_RDONLY) | os.O_DIRECTORY
    parent_fd = os.open('/', parent_flags)
    fd = None
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, parent_flags | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise UnsupportedSource('not_regular_file')
        raw = os.fdopen(fd, 'rb')
        fd = None
        stream = gzip.GzipFile(fileobj=raw) if source.get('compression') == 'gzip' or path.suffix.lower() == '.gz' else raw
        return raw, stream, before
    finally:
        os.close(parent_fd)
        if fd is not None:
            os.close(fd)


def _identity(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


class _JSONStream:
    """Incremental JSON framing; memory bounded by one object, not the collection.

    Array members are yielded before their siblings. Wrapper objects are visited
    a field at a time. Malformed JSON framing cannot be guessed/repaired.
    """
    def __init__(self, stream, check, limit):
        self.stream, self.check, self.limit = stream, check, limit
        self.buffer, self.eof = '', False
        self.decoder = json.JSONDecoder()

    def fill(self):
        self.check()
        part = self.stream.read(65536)
        self.eof = not part
        self.buffer += part

    def space(self):
        while True:
            self.buffer = self.buffer.lstrip()
            if self.buffer or self.eof:
                return
            self.fill()

    def peek(self):
        self.space()
        return self.buffer[:1]

    def take(self, char):
        if self.peek() != char:
            raise MalformedRecord('json_framing')
        self.buffer = self.buffer[1:]

    def value(self):
        self.space()
        while True:
            if len(self.buffer) > self.limit:
                # Decoder may already have a small first value followed by more.
                try:
                    _, end = self.decoder.raw_decode(self.buffer)
                except ValueError:
                    raise MalformedRecord('json_record_size_cap') from None
                if end > self.limit:
                    raise MalformedRecord('json_record_size_cap')
            try:
                _, end = self.decoder.raw_decode(self.buffer)
                # A number at a chunk boundary may not be the full token yet.
                if end == len(self.buffer) and not self.eof:
                    self.fill()
                    continue
                raw = self.buffer[:end]
                obj = _strict(raw)
                self.buffer = self.buffer[end:]
                return obj, raw
            except json.JSONDecodeError:
                if self.eof:
                    raise MalformedRecord('invalid_json') from None
                self.fill()

    def array(self, pointer):
        self.take('[')
        ordinal = 0
        if self.peek() != ']':
            while True:
                obj, raw = self.value()
                yield obj, _pointer(pointer, ordinal), raw
                ordinal += 1
                if self.peek() == ']':
                    break
                self.take(',')
        self.take(']')

    def rows(self):
        if self.peek() == '[':
            yield from self.array('')
        elif self.peek() == '{':
            # Stream recognized collection wrappers; retain metadata for children
            # as encountered. Trailing metadata is not silently claimed known.
            self.take('{')
            root, seen, collection = {}, set(), False
            if self.peek() != '}':
                while True:
                    key, _ = self.value()
                    if not isinstance(key, str) or key in seen:
                        raise MalformedRecord('json_root_key')
                    seen.add(key)
                    self.take(':')
                    if key in COLLECTIONS and self.peek() == '[' and key not in ('ingredients',):
                        # Native recipe ingredients are not a collection wrapper.
                        collection = True
                        for obj, pointer, raw in self.array(_pointer('', key)):
                            yield obj, pointer, raw, dict(root)
                    else:
                        obj, _ = self.value()
                        root[key] = obj
                    if self.peek() == '}':
                        break
                    self.take(',')
            self.take('}')
            if not collection:
                yield root, '', None
            elif root:
                # Metadata may follow the streamed array. Keep it as a related
                # source-level row rather than silently discarding attribution.
                yield {'__ingest_collection_metadata__': root}, '/collection-metadata', None
        else:
            raise MalformedRecord('json_root_not_object_or_array')
        if self.peek():
            raise MalformedRecord('json_trailing_data')


def _csv_value(value):
    if isinstance(value, str) and value.lstrip().startswith(('[', '{')):
        try:
            return _strict(value)
        except (ValueError, UnicodeError):
            # Several retained public recipe CSVs encode Python list literals.
            # literal_eval parses data only; it never executes source code.
            if len(value) <= MAX_RECORD:
                try:
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, (list, dict)):
                        return parsed
                except (ValueError, SyntaxError, TypeError, RecursionError):
                    pass
    return value


def _read_rows(source, context, stats):
    fmt = str(source.get('format', Path(source['path']).suffix.lstrip('.'))).lower()
    if fmt in ('sqlite', 'sqlite3', 'db'):
        yield from _sqlite_rows(source, context)
        return
    raw, stream, before = _open(source)
    try:
        text = io.TextIOWrapper(stream, encoding=source.get('encoding') or 'utf-8-sig', errors='strict', newline='')
        try:
            if fmt in ('jsonl', 'ndjson'):
                number = 0
                while True:
                    context.check_budget()
                    line = text.readline(MAX_RECORD + 1)
                    if not line:
                        break
                    number += 1
                    if len(line) > MAX_RECORD:
                        # Drain this line only, then continue later records.
                        while line and not line.endswith('\n'):
                            line = text.readline(MAX_RECORD + 1)
                        _error(context, source, MalformedRecord('jsonl_line_size_cap'), stats)
                        continue
                    if not line.strip():
                        continue
                    try:
                        yield _strict(line), '/line/' + str(number), line, {}
                    except (ValueError, UnicodeError) as exc:
                        _error(context, source, exc, stats)
            elif fmt in ('json', 'jsonld', 'json-ld'):
                for item in _JSONStream(text, context.check_budget, MAX_RECORD).rows():
                    obj, pointer, native = item[:3]
                    yield obj, pointer, native, item[3] if len(item) == 4 else {}
            elif fmt in ('csv', 'tsv'):
                reader = csv.DictReader(text, delimiter='\t' if fmt == 'tsv' else ',')
                if not reader.fieldnames:
                    raise UnsupportedSource('csv_no_header')
                for number, obj in enumerate(reader, 2):
                    context.check_budget()
                    yield {key: _csv_value(value) for key, value in obj.items() if key is not None}, '/row/' + str(number), None, {}
            elif fmt in ('html', 'htm'):
                body = text.read(MAX_RECORD + 1)
                if len(body) > MAX_RECORD:
                    raise UnsupportedSource('html_size_cap')
                yield from _html_rows(body, source, context, stats)
            elif fmt in ('text', 'txt', 'wikitext', 'md', 'markdown'):
                body = text.read(MAX_RECORD + 1)
                if len(body) > MAX_RECORD:
                    raise UnsupportedSource('text_size_cap')
                record = _section_text(body, source.get('title'))
                if record is None:
                    raise UnsupportedSource('text_recipe_sections_unknown')
                yield record, '/text', body, {}
            elif fmt == 'pdf':
                # Generic PDFs cannot establish source section/recipe boundaries.
                # Independently catalogued parsed caches are ingested instead.
                raise UnsupportedSource('raw_pdf_requires_supported_parsed_cache')
            else:
                raise UnsupportedSource('unsupported_recipe_format')
        finally:
            # Detach so the held file can be checked before it closes.
            text.detach()
        if _identity(before) != _identity(os.fstat(raw.fileno())):
            raise SourceChanged('source_changed_during_read')
    finally:
        if stream is not raw:
            stream.close()
        raw.close()


def _sqlite_rows(source, context):
    # Probe with held nofollow FD, then read SQLite URI; never migrate/repair it.
    raw, stream, before = _open(source)
    try:
        if stream is not raw:
            raise UnsupportedSource('compressed_sqlite_unsupported')
        from ingest_existing import _fingerprint
        snapshot = _fingerprint(Path(source['path']))
        db = sqlite3.connect('file:' + quote(str(Path(source['path']).resolve())) + '?mode=ro', uri=True)
        try:
            db.execute('PRAGMA query_only=ON')
            db.row_factory = sqlite3.Row
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            db.execute('PRAGMA trusted_schema=OFF')
            def budget():
                try:
                    context.check_budget()
                    return 0
                except BudgetExceeded:
                    return 1
            db.set_progress_handler(budget, 100000)
            db.execute('BEGIN')
            selected = source.get('table') or (source.get('metadata') or {}).get('table')
            candidates = [selected] if selected else [t for t in ('recipes', 'recipe', 'menu_items', 'ingredients', 'foods', 'food', 'products', 'source_records', 'source_data', 'recipe_source_record', 'records') if t in tables]
            if not candidates:
                raise UnsupportedSource('sqlite_recipe_schema_unknown')
            for table in candidates:
                if table not in tables:
                    raise UnsupportedSource('sqlite_table_unknown')
                ident = '"' + table.replace('"', '""') + '"'
                for number, row in enumerate(db.execute('SELECT * FROM ' + ident), 1):
                    context.check_budget()
                    obj = dict(row)
                    for key in ('source_payload_json', 'payload_json', 'recipe_json', 'data_json', 'record_json', 'raw_json', 'source_json', 'payload', 'data', 'json'):
                        if isinstance(obj.get(key), str):
                            parsed = _strict(obj[key])
                            if isinstance(parsed, dict):
                                obj = parsed
                                break
                    yield obj, '/table/' + table + '/' + str(number), None, {}
            db.execute('COMMIT')
        finally:
            db.close()
        if _identity(before) != _identity(os.fstat(raw.fileno())) or _fingerprint(Path(source['path'])) != snapshot:
            raise SourceChanged('source_changed_during_read')
    finally:
        raw.close()


class _LD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active, self.parts, self.scripts = False, [], []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.active = dict(attrs).get('type', '').split(';')[0].strip().lower() == 'application/ld+json'
            self.parts = []
    def handle_data(self, data):
        if self.active:
            self.parts.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.active:
            self.scripts.append(''.join(self.parts))
            self.active = False


def _html_rows(body, source, context, stats):
    adapter = source.get('adapter')
    if adapter:
        root = Path(__file__).with_name('reviewed_recipe_sources')
        for file, expected in (('source_faithful_parse.py', HTML_PARSER_SHA256), ('source_recipe_template.schema.json', HTML_SCHEMA_SHA256)):
            if hashlib.sha256((root / file).read_bytes()).hexdigest() != expected:
                raise UnsupportedSource('reviewed_html_parser_pin_mismatch')
        try:
            from reviewed_recipe_sources import source_faithful_parse as parser
        except ImportError:
            # This source still has a chance through independently identified LD.
            _error(context, source, UnsupportedSource('optional_html_dependencies_missing'), stats)
        else:
            kwargs = dict(source=source, source_id=str(source.get('source_id') or source['id']),
                          country=source.get('country'), language=source.get('language') or 'und')
            if adapter in ('calmos-menu-v1', 'ocean82-menu-v1'):
                rows = parser.parse_html_menu(body.encode('utf-8'), **kwargs)
            else:
                rows = parser.parse_html_recipes(body.encode('utf-8'), source_record_id=source.get('source_record_id') or source['id'], **kwargs)
            for number, obj in enumerate(rows):
                yield obj, '/selected-html/' + str(number), None, {}
            return
    extractor = _LD()
    extractor.feed(body)
    found = False
    for number, native in enumerate(extractor.scripts):
        try:
            obj = _strict(native)
        except ValueError as exc:
            _error(context, source, exc, stats)
            continue
        for row, pointer in _expand(obj, '/script/' + str(number)):
            if _looks_recipe(row) or _looks_menu(row):
                found = True
                yield row, pointer, _json(row), {'representation': 'html-jsonld-source-script', 'scriptSHA256': hashlib.sha256(native.encode()).hexdigest()}
    if found:
        return
    # The proven generic visible HTML parser handles explicit section headings.
    # No install and no arbitrary page-text heuristic when bs4 is unavailable.
    try:
        from reviewed_recipe_sources import source_faithful_parse as parser
    except ImportError:
        raise UnsupportedSource('html_no_supported_jsonld_or_parser') from None
    rows = parser.parse_html_recipes(body.encode(), source=source,
        source_id=str(source.get('source_id') or source['id']), source_record_id=str(source.get('source_record_id') or source['id']),
        country=source.get('country'), language=source.get('language') or 'und')
    for number, obj in enumerate(rows):
        yield obj, '/html/' + str(number), None, {}


def _types(obj):
    value = obj.get('@type', obj.get('type', []))
    return [value.rsplit('/', 1)[-1]] if isinstance(value, str) else value if isinstance(value, list) else []


def _direct_recipe(obj):
    return isinstance(obj, dict) and (obj.get('cacheVersion') == CACHE_VERSION or
        'Recipe' in _types(obj) or 'recipeTemplate' in obj or
        any(key in obj for key in RECIPE_FIELDS) and any(key in obj for key in STEP_FIELDS))


def _looks_recipe(obj):
    return _direct_recipe(obj) or isinstance(obj, dict) and any(
        _direct_recipe(obj.get(key)) for key in ('recipe', 'record', 'payload', 'data'))


def _looks_menu(obj):
    return isinstance(obj, dict) and ('menuTemplate' in obj or 'originalItemName' in obj or
        any(t in _types(obj) for t in ('Menu', 'MenuItem', 'MenuSection')))


def _expand(obj, pointer='', depth=0):
    if depth > 32:
        raise MalformedRecord('wrapper_depth_cap')
    if isinstance(obj, list):
        for number, child in enumerate(obj):
            yield from _expand(child, _pointer(pointer, number), depth + 1)
    elif isinstance(obj, dict):
        if _looks_recipe(obj) or _looks_menu(obj):
            yield obj, pointer
            return
        for key in ('recipe', 'record', 'payload', 'data'):
            child = obj.get(key)
            if isinstance(child, dict) and (_looks_recipe(child) or _looks_menu(child)):
                # Keep the envelope: normalized OffMenu packets carry their
                # source identity/country/provenance outside the recipe body.
                yield obj, pointer
                return
        keys = [key for key in COLLECTIONS if isinstance(obj.get(key), (list, dict)) and key != 'ingredients']
        if keys:
            for key in sorted(keys):
                value = obj[key]
                if key == 'pages' and isinstance(value, dict):
                    for page_id, page in value.items():
                        yield from _expand(page, _pointer(_pointer(pointer, key), page_id), depth + 1)
                else:
                    yield from _expand(value, _pointer(pointer, key), depth + 1)
        else:
            yield obj, pointer
    else:
        # Yield malformed leaves so the caller can isolate them without losing
        # later siblings in the same JSON-LD/container array.
        yield obj, pointer


def _first(obj, fields):
    for name in fields:
        if name in obj and obj[name] is not None:
            return obj[name]
    return None


def _text(value, language=None):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if language and isinstance(value.get(language), str):
            return value[language]
        for key in ('text', 'name', 'originalText', 'originalExpression', 'en', 'ru'):
            if isinstance(value.get(key), str):
                return value[key]
        # Unknown language keys are preserved, not translated or relabelled.
        if value and all(isinstance(x, str) for x in value.values()):
            return next(iter(value.values()))
    return None


def _list(value):
    if value is None:
        return None
    if isinstance(value, str):
        parsed = _csv_value(value)
        if isinstance(parsed, list):
            return parsed
        # Do not split comma-delimited ingredients: commas can be preparation.
        return [line for line in value.splitlines() if line.strip()] or []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise MalformedRecord('recipe_field_type')


def _section_text(body, title=None):
    """Only explicit cached/wikitext ingredient+method headings, no PDF guessing."""
    headings = list(re.finditer(r'(?im)^[ \t]*(?:={2,6}[ \t]*([^=\n]+?)[ \t]*={2,6}|#{2,6}[ \t]+([^\n]+?)|(?:Ingredients|Method|Directions|Instructions|Preparation|Procedure|Notes|Variations)[ \t]*:?)[ \t]*$', body))
    ingredients, steps = None, None
    for n, match in enumerate(headings):
        end = headings[n + 1].start() if n + 1 < len(headings) else len(body)
        lines = [line for line in body[match.end():end].splitlines() if line.strip()]
        label = (match.group(1) or match.group(2) or match.group()).strip().rstrip(':').strip().casefold()
        if label == 'ingredients':
            ingredients = lines
        elif label in ('method', 'directions', 'instructions', 'preparation', 'procedure'):
            steps = lines
    if ingredients is None or steps is None:
        return None
    if not title:
        preamble = body[:headings[0].start()].strip().splitlines()
        markdown_title = next((line[2:].strip() for line in preamble if line.startswith('# ')), None)
        title = markdown_title or (preamble[0] if len(preamble) == 1 else None)
    if not title:
        return None
    return {'title': title, 'ingredients': ingredients, 'instructions': steps,
            'sourceText': body, 'extractionState': 'explicit-text-sections; no-semantic-normalization'}


def _provenance(source, obj, pointer, metadata):
    native = obj.get('source') if isinstance(obj.get('source'), dict) else {}
    return {'source_id': native.get('sourceId') or source.get('source_id') or source.get('provider') or source['id'],
            'catalog_source_id': source['id'], 'path': source['path'], 'pointer': pointer,
            'provider': source.get('provider'), 'license': source.get('license'),
            'custody': source.get('custody'), 'source_metadata': native,
            'source_provenance': obj.get('provenance'),
            'container_metadata': metadata, 'adapter_version': VERSION}


def _identity_record(obj, kind, source):
    native = obj.get('source') if isinstance(obj.get('source'), dict) else {}
    identity = _first(obj, ('url', '@id', 'sourceUrl', 'source_url', 'link'))
    if identity is None:
        native_id = native.get('sourceRecordId') or _first(obj, ('slug', 'recipeId', 'recordId', 'id'))
        if native_id is not None:
            identity = [native.get('sourceId') or source.get('provider') or 'source-native', native_id]
    # Include content to preserve distinct versions/duplicate native IDs with
    # different payloads. Exact duplicate copies get identical entity IDs.
    return kind + ':' + _hash([identity, obj])


def _mention(recipe_id, index, value, language, provenance, lexical=None):
    raw_text = value if isinstance(value, str) else _text(_first(value, ('originalExpression', 'text', 'raw', 'originalText')), language) if isinstance(value, dict) else None
    name = _text(_first(value, ('sourceNameText', 'name', 'ingredient', 'food')), language) if isinstance(value, dict) else None
    if raw_text is None and isinstance(value, dict):
        # Native object is the source expression; do not fabricate "100 g beans".
        raw_text = _json(value)
    if raw_text is None:
        raise MalformedRecord('ingredient_not_text_or_object')
    quantity = _first(value, ('quantity', 'sourceQuantity', 'amount')) if isinstance(value, dict) else None
    source_quantity = value.get('sourceQuantity') if isinstance(value, dict) else None
    unit = source_quantity.get('unit') if isinstance(source_quantity, dict) else value.get('unit') if isinstance(value, dict) else None
    explicit_identity = _first(value, ('foodIdentity', 'ingredientId')) if isinstance(value, dict) else None
    quantity_lexeme = lexical.get('quantity') if isinstance(lexical, dict) else None
    return {'id': recipe_id + ':ingredient:' + str(index), 'kind': 'ingredient_mention',
            'recipe_id': recipe_id, 'ordinal': index, 'raw_text': raw_text,
            'source_name_text': name, 'source_language': language,
            'quantity': quantity, 'unit': unit, 'quantity_lexeme': quantity_lexeme,
            'quantity_interpretation': 'upstream-source-quantity-preserved; no-new-interpretation',
            'source_normalized_assertions': {key:value[key] for key in ('ingredientId','amount','unit','foodMatchStatus','quantityStatus') if key in value} if isinstance(value, dict) else None,
            'normalized_ingredient_id': None, 'reported_food_identity': explicit_identity,
            'identity_status': 'raw-source-mention-not-normalized-entity',
            'raw_source': value, 'provenance': provenance,
            'relations': [{'kind': 'ingredient_of', 'target_domain': 'recipes', 'target_id': recipe_id}]}


def _steps(value, language):
    out = []
    def visit(item, section=None, depth=0):
        if depth > 32:
            raise MalformedRecord('instruction_depth_cap')
        if isinstance(item, list):
            for child in item:
                visit(child, section, depth + 1)
        elif isinstance(item, dict) and 'itemListElement' in item:
            visit(item['itemListElement'], item.get('name'), depth + 1)
        else:
            text = _text(item, language)
            if text is None and isinstance(item, dict):
                text = _text(item.get('text'), language)
            if text is None:
                raise MalformedRecord('instruction_not_text')
            out.append({'ordinal': len(out), 'raw_text': text, 'source_section': section, 'raw_source': item})
    if value is not None:
        visit(value)
    return out if value is not None else None


def _recipe(obj, source, pointer, native, metadata):
    original = obj
    if not _direct_recipe(obj):
        for key in ('recipe', 'record', 'payload', 'data'):
            if _direct_recipe(obj.get(key)):
                obj = obj[key]
                pointer = _pointer(pointer, key)
                break
    if not _looks_recipe(obj):
        # Wikibooks cached pages are source text, not URL-only discovery leads.
        body = _first(obj, ('wikitext', 'text', 'content'))
        if body is None and isinstance(obj.get('revisions'), list) and obj['revisions']:
            revision = obj['revisions'][0]
            if isinstance(revision, dict):
                slots = revision.get('slots')
                main = slots.get('main') if isinstance(slots, dict) else None
                body = _first(main, ('*', 'content')) if isinstance(main, dict) else revision.get('*')
        if isinstance(body, str):
            parsed = _section_text(body, _text(_first(obj, ('title', 'name'))))
            if parsed:
                obj = dict(obj, **parsed)
    if not _looks_recipe(obj):
        raise UnsupportedSource('not_a_supported_recipe_record')
    title = _text(_first(obj, ('originalTitle', 'title', 'name', 'recipeName')))
    language = _first(obj, ('language', 'inLanguage', 'sourceDocumentLanguage'))
    languages = obj.get('languages')
    if language is None and isinstance(languages, list) and len(languages) == 1:
        language = languages[0]
    names = obj.get('name')
    if isinstance(names, dict) and title is not None:
        language = next((key for key, text in names.items() if text == title), language)
    provenance = _provenance(source, original, pointer, metadata)
    partial = obj.get('cacheVersion') == CACHE_VERSION
    if partial:
        sections = obj.get('sections')
        if not isinstance(sections, list):
            raise MalformedRecord('pdf_cache_sections_missing')
        title = next((x.get('text') for x in sections if isinstance(x, dict) and x.get('kind') == 'title'), None)
        if obj.get('ingredientLines') is not None or obj.get('orderedSteps') is not None:
            raise MalformedRecord('pdf_cache_grain_conflict')
    if not isinstance(title, str) or not title.strip():
        raise MalformedRecord('recipe_title_missing')
    record_id = _identity_record(original, 'recipe', source)
    values = None if partial else _list(_first(obj, RECIPE_FIELDS))
    lexical = None
    if native:
        try:
            lexical = json.loads(native, parse_int=str, parse_float=str)
        except ValueError:
            pass
    lex_ingredients = lexical.get('ingredients') if isinstance(lexical, dict) else None
    ingredients = [] if values is not None else None
    if values is not None:
        for index, value in enumerate(values):
            lex = lex_ingredients[index] if isinstance(lex_ingredients, list) and index < len(lex_ingredients) else None
            ingredients.append(_mention(record_id, index, value, language, provenance, lex))
    steps = None if partial else _steps(_first(obj, STEP_FIELDS), language)
    record = {'id': record_id, 'kind': 'recipe', 'title': title,
              'language': language, 'title_languages': names if isinstance(names, dict) else None,
              'source_languages': languages, 'source_country_assertions': original.get('countries'),
              'yield': _first(obj, ('yield', 'recipeYield', 'baseServings', 'servings')),
              'ingredients': ingredients, 'steps': steps,
              'ingredient_count': len(ingredients) if ingredients is not None else None,
              'step_count': len(steps) if steps is not None else None,
              'extraction_state': 'partial-raw-section-retained; granularity-unknown' if partial else 'source-fields-preserved',
              'normalization_performed': False, 'translation_performed': False,
              'nutrition': _first(obj, ('nutritionAssertions', 'nutrition', 'nutrients', 'nutritionalInformation')),
              'raw_source': original, 'raw_source_json': native, 'provenance': provenance,
              'relations': [{'kind': 'has_ingredient_mention', 'target_domain': 'ingredients', 'target_id': row['id']} for row in ingredients or []]}
    return record, ingredients or []


def _menus(obj, source, pointer, native, metadata):
    """Flatten schema.org menu/section/item relationships without dish matching."""
    if not _looks_menu(obj):
        raise UnsupportedSource('not_a_supported_menu_record')
    kind = 'menu_item' if 'MenuItem' in _types(obj) or 'originalItemName' in obj or 'menuTemplate' in obj else 'menu'
    name = _text(_first(obj, ('originalItemName', 'originalTitle', 'name', 'title')))
    if not name:
        raise MalformedRecord('menu_name_missing')
    identity = _identity_record(obj, kind, source)
    relations, children = [], []
    for field in ('hasMenuItem', 'hasMenuSection', 'menuItems'):
        values = obj.get(field)
        if values is None:
            continue
        for index, child in enumerate(values if isinstance(values, list) else [values]):
            if not isinstance(child, dict):
                raise MalformedRecord('menu_child_not_object')
            child = dict(child)
            child.setdefault('@type', 'MenuSection' if field == 'hasMenuSection' else 'MenuItem')
            projected = list(_menus(child, source, _pointer(_pointer(pointer, field), index), None, metadata))
            relations.append({'kind': 'contains_menu_entry', 'target_domain': 'recipes', 'target_id': projected[0]['id']})
            children.extend(projected)
    yield {'id': identity, 'kind': kind, 'title': name, 'description': _first(obj, ('originalDescription', 'description')),
           'price': _first(obj, ('price', 'offers')), 'currency': obj.get('currency'),
           'language': _first(obj, ('language', 'inLanguage')), 'raw_source': obj,
           'raw_source_json': native, 'provenance': _provenance(source, obj, pointer, metadata),
           'relations': relations}
    yield from children


def _direct_ingredient(obj, source, pointer, native, metadata):
    name = _text(_first(obj, ('name', 'description', 'foodName', 'food_name', 'ingredientName', 'ingredient_name', 'product_name', 'originalName')))
    if not name:
        raise UnsupportedSource('ingredient_name_missing')
    # Registry codes may be asserted by the source, but are never invented from
    # recipe text. A named source food is still not a global canonical match.
    code = _first(obj, ('fdcId', 'fdc_id', 'foodCode', 'food_code', 'ingredientId', 'id', 'code'))
    return {'id': _identity_record(obj, 'ingredient-source-entity', source),
            'kind': 'ingredient_source_entity', 'name': name, 'source_native_id': code,
            'normalized_ingredient_id': None, 'identity_status': 'source-native-entity; cross-source-normalization-unverified',
            'nutrition': _first(obj, ('foodNutrients', 'nutrients', 'nutriments', 'nutrition', 'nutritionAssertions')),
            'raw_source': obj, 'raw_source_json': native,
            'provenance': _provenance(source, obj, pointer, metadata), 'relations': []}


def _direct_source(source, obj):
    domains = source.get('domains', source.get('domain', []))
    domains = [domains] if isinstance(domains, str) else domains
    if 'recipes' in domains:
        return False
    return 'ingredients' in domains or any(key in obj for key in ('fdcId', 'fdc_id', 'foodNutrients', 'foodCode'))


def _product_source(source):
    domains = source.get('domains', source.get('domain', []))
    domains = [domains] if isinstance(domains, str) else domains
    provider = str(source.get('provider', '')).lower()
    return 'barcodes' in domains or provider in ('off', 'openfoodfacts', 'open_food_facts', 'usda', 'fdc', 'usda_fdc')


def _product_ingredients(obj, source, pointer, native, metadata):
    """Product labels remain unsplit; structured assertions retain source IDs."""
    code = _first(obj, ('code', 'barcode', 'gtin', 'fdcId', 'fdc_id', 'id'))
    product_id = 'source-product:' + _hash([source.get('provider'), code, None if code is not None else obj])
    provenance = _provenance(source, obj, pointer, metadata)
    relation = {'kind': 'ingredient_of_product', 'target_domain': 'barcodes',
                'target_id': product_id, 'source_native_product_id': code,
                'relationship_status': 'source-native-reference; target-resolution-unverified'}
    fields = [key for key in obj if key == 'ingredients_text' or key.startswith('ingredients_text_') or key in ('ingredients', 'ingredientStatement', 'ingredient_statement')]
    for field in fields:
        value = obj[field]
        if value is None or value == '' or value == []:
            continue
        entries = value if isinstance(value, list) else [value]
        for index, entry in enumerate(entries):
            if not isinstance(entry, (str, dict)):
                raise MalformedRecord('product_ingredient_type')
            text = entry if isinstance(entry, str) else _text(_first(entry, ('text', 'name')))
            yield {'id': 'product-ingredient:' + _hash([product_id, field, index, entry]),
                   'kind': 'ingredient_label_mention' if isinstance(entry, str) else 'ingredient_source_assertion',
                   'product_id': product_id, 'source_field': field, 'ordinal': index,
                   'raw_text': text, 'raw_source': entry,
                   'source_asserted_ingredient_id': entry.get('id') if isinstance(entry, dict) else None,
                   'normalized_ingredient_id': None,
                   'identity_status': 'source-label-or-assertion; not-canonicalized',
                   'provenance': provenance, 'relations': [relation]}


def iter_records(domain, source, context, stats=None):
    """One source stream, isolating semantically bad records and JSONL lines."""
    stats = stats if stats is not None else dict(errors=0, skipped=0, recipes=0, menus=0, ingredient_mentions=0, ingredient_entities=0, partial_recipes=0)
    seen = set()
    dedup_limit = max(1, min(100000, int(context.config.get('dedup_cache_entries', 100000))))
    for obj, pointer, native, metadata in _read_rows(source, context, stats):
        context.check_budget()
        try:
            rows = _expand(obj, pointer)
            for row, subpointer in rows:
                try:
                    if not isinstance(row, dict):
                        raise MalformedRecord('record_not_object')
                    if '__ingest_collection_metadata__' in row:
                        projected = [{'id': 'source-metadata:' + source_key(source), 'kind': 'source_metadata',
                                      'raw_source': row['__ingest_collection_metadata__'],
                                      'provenance': _provenance(source, row, subpointer, {}), 'relations': []}]
                    elif _looks_menu(row):
                        projected = _menus(row, source, subpointer, native, metadata) if domain == 'recipes' else []
                    elif _looks_recipe(row) or any(key in row for key in ('wikitext', 'text', 'content', 'revisions')):
                        recipe, mentions = _recipe(row, source, subpointer, native, metadata)
                        if domain == 'ingredients' and recipe['ingredient_count'] is None:
                            raise UnsupportedSource('recipe_ingredient_grain_unknown')
                        projected = [recipe] if domain == 'recipes' else mentions
                    elif domain == 'ingredients' and _product_source(source) and any(k == 'ingredients' or k.startswith('ingredients_text') or k in ('ingredientStatement', 'ingredient_statement') for k in row):
                        projected = _product_ingredients(row, source, subpointer, native, metadata)
                    elif domain == 'ingredients' and _direct_source(source, row):
                        projected = [_direct_ingredient(row, source, subpointer, native, metadata)]
                    else:
                        raise UnsupportedSource('unrecognized_recipe_or_lead_only')
                    for result in projected:
                        # Duplicate objects in a repeated wrapper/file do not grow
                        # this source's entity/mention population.
                        if result['id'] in seen:
                            stats['skipped'] += 1
                            continue
                        if len(seen) >= dedup_limit:
                            # Persistent SQLite IDs still make later repeats
                            # idempotent after this bounded in-memory cache rolls.
                            seen.clear()
                        seen.add(result['id'])
                        kind = result['kind']
                        if kind == 'recipe':
                            stats['recipes'] += 1
                            stats['partial_recipes'] += result['ingredient_count'] is None
                        elif kind in ('menu', 'menu_item'):
                            stats['menus'] += 1
                        elif kind in ('ingredient_mention', 'ingredient_label_mention', 'ingredient_source_assertion'):
                            stats['ingredient_mentions'] += 1
                        elif kind == 'ingredient_source_entity':
                            stats['ingredient_entities'] += 1
                        yield result
                except UnsupportedSource as exc:
                    stats['skipped'] += 1
                    context.report_error(source, exc)
                except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                    _error(context, source, exc, stats)
        except (ValueError, TypeError, KeyError) as exc:
            _error(context, source, exc, stats)


def run_domain(domain, sources, context):
    if domain not in ('recipes', 'ingredients'):
        raise ValueError('wrong_recipe_adapter_domain')
    totals = dict.fromkeys(COUNTERS, 0)
    summaries = []
    for original_source in sources:
        source = dict(original_source, adapter_version=VERSION)
        reusable = source.get('disposition') in (None, 'candidate', 'existing-store', 'existing-loaded', 'already_loaded', 'existing_loaded', 'reuse-reference')
        if domain == 'ingredients' and _product_source(source) and reusable and (source.get('loaded') or source.get('disposition') == 'existing-store') and not source.get('restricted'):
            # This is a new derived-ingredient stream, not a product re-import or
            # an override of a restriction. Original SQLite remains read-only.
            source = dict(source, id=str(source['id']) + ':ingredient-derivation',
                          loaded=False, disposition='derive-ingredients-readonly')
        stats = dict(errors=0, skipped=0, recipes=0, menus=0, ingredient_mentions=0, ingredient_entities=0, partial_recipes=0)
        if source.get('restricted') or source.get('loaded') or source.get('disposition') in ('restricted', 'skip', 'existing-loaded', 'existing-store', 'already_loaded', 'unsupported', 'metadata-only', 'incomplete-hold', 'duplicate', 'excluded', 'documentation', 'historical-demo', 'missing', 'unreadable'):
            reason = 'restricted_input' if source.get('restricted') else 'existing_loaded' if source.get('loaded') else source.get('disposition', 'catalog_skip')
            summary = dict(source_key=source_key(source), status='skipped', reason=reason, skipped=1, read=0, written=0, unchanged=0, errors=0)
        else:
            try:
                context.check_budget()
                summary = context.ingest(source, iter_records(domain, source, context, stats))
            except BudgetExceeded:
                summaries.append(dict(source_key=source_key(source), status='partial', reason='resource_cap'))
                break
            except Exception as exc:
                context.report_error(source, exc)
                summary = dict(source_key=source_key(source), status='failed', read=0, written=0, unchanged=0, errors=1, skipped=0, error_class=type(exc).__name__)
        summary['errors'] = max(summary.get('errors', 0), stats['errors'])
        summary['skipped'] = summary.get('skipped', 0) + stats['skipped']
        summary['record_kinds'] = {key: value for key, value in stats.items() if key not in ('errors', 'skipped')}
        if summary.get('errors') and summary.get('status') in ('complete', 'completed'):
            summary['status'] = 'partial'
        summaries.append(summary)
        for key in COUNTERS:
            totals[key] += summary.get(key, 0)
    status = 'partial' if any(row.get('status') in ('partial', 'failed') for row in summaries) else 'complete'
    return dict(domain=domain, adapter_version=VERSION, status=status, sources=summaries, **totals)
