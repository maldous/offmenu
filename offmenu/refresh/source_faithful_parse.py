"""Source-faithful parsing for retained recipe/menu documents.

The semantic parsers consume locally retained, receipt-pinned originals only;
they never acquire sources or normalize identities.  Recipe/menu fields that
cannot be read directly from source remain null or explicitly unclassified.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from bs4 import BeautifulSoup

PARSER_VERSION = 'offmenu-source-faithful-recipe-parser/1.3.0'
DICTIONARY_VERSION = 'offmenu-data-dictionary/1'
RECIPE_TEMPLATE_VERSION = 'offmenu-source-recipe/2'
MENU_TEMPLATE_VERSION = 'offmenu-source-menu-item/1'
MAPPING_VERSION = 'offmenu-source-field-mappings/1'
MAX_INPUT_BYTES = 128 * 1024 * 1024
MAX_RECORDS = 100_000


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


class ParseError(ValueError):
    """Fixed, safe parse error codes."""


def _read_original(path: Path, *, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ParseError('input-not-regular-file')
    size = path.stat().st_size
    if size <= 0:
        raise ParseError('input-empty')
    if size > max_bytes:
        raise ParseError('input-size-limit')
    raw = path.read_bytes()
    if len(raw) != size:
        raise ParseError('input-changed-during-read')
    return raw


def _location(text: str, start: int, end: int, *, page: int = 1,
              line_start: int | None = None, line_end: int | None = None) -> dict:
    before = text[:start]
    snippet = text[start:end]
    line_start = line_start or (before.count('\n') + 1)
    line_end = line_end or (line_start + snippet.count('\n'))
    return {'page': page, 'lineStart': line_start, 'lineEnd': line_end,
            'utf8ByteRange': [len(before.encode('utf-8')),
                              len((before + snippet).encode('utf-8'))],
            'pageTextSHA256': sha256(text.encode('utf-8')),
            'sourceSpanSHA256': sha256(snippet.encode('utf-8'))}


def _heading(soup: BeautifulSoup) -> str | None:
    for selector in ('h1', 'meta[property="og:title"]', 'meta[name="dcterms.title"]'):
        node = soup.select_one(selector)
        if node:
            value = node.get('content') if node.name == 'meta' else node.get_text(' ', strip=True)
            if value:
                return str(value).strip()
    return None


def _citation(source: dict, source_id: str, record_id: str, language: str,
              country: str | None, original_sha: str, extraction_sha: str,
              attribution: str | None) -> dict:
    return {'sourceId': source_id, 'sourceRecordId': record_id,
            'releaseId': source.get('release'), 'countryCode': country,
            'language': language, 'citationUrl': source.get('citationUrl') or source.get('sourceURL') or '',
            'attribution': attribution or source.get('attribution') or 'Attribution not supplied in local receipt',
            'licenseStatus': source.get('licenseStatus', 'unverified; retained private reference only'),
            'originalSHA256': original_sha, 'extractionSHA256': extraction_sha,
            'extractionParser': PARSER_VERSION,
            'scope': 'local-private-only; downstream reuse remains held'}


def _schema_path() -> Path:
    return Path(__file__).with_name('source_recipe_template.schema.json')


def _validate_record(record: dict) -> None:
    try:
        import jsonschema
        schema = json.loads(_schema_path().read_text(encoding='utf-8'))
        jsonschema.validate(record, schema)
    except ImportError as error:
        raise ParseError('jsonschema-dependency-unavailable') from error
    except Exception as error:
        raise ParseError('record-schema-invalid') from error


def _quantity(line: str) -> dict:
    """Capture source numeric lexeme and explicit unit without conversion."""
    number = r'(?:\d+(?:[.,]\d+)?(?:\s+\d+/\d+)?|\d+/\d+|[½¼¾⅓⅔])(?:\s*[½¼¾⅓⅔])?'
    unit = r'(?:kilograms?|kg|grams?|g|milligrams?|mg|millilit(?:er|re)s?|ml|lit(?:er|re)s?|l|decilit(?:er|re)s?|dl|centilit(?:er|re)s?|cups?|tablespoons?|tbsp\.?|teaspoons?|tsp\.?|cloves?|pinches?|bunch(?:es)?|slices?|pieces?|cans?|tins?|sprigs?|stalks?|heads?|leaves?|c\.?\s*à\.?\s*[cs])'
    match = re.match(r'^\s*(' + number + r'(?:\s*[-–]\s*' + number + r')?)(?:\s+(' + unit + r'))?(?=\s|$)', line, re.I)
    if not match:
        return {'rawExpression': None, 'rawValueLexeme': None, 'rawUnitLexeme': None,
                'interpretedValue': None, 'interpretedUnit': None,
                'interpretationStatus': 'not-interpreted'}
    value, raw_unit = match.groups()
    expression = value + ((' ' + raw_unit) if raw_unit else '')
    return {'rawExpression': expression.strip(), 'rawValueLexeme': value.strip(),
            'rawUnitLexeme': raw_unit, 'interpretedValue': None,
            'interpretedUnit': None, 'interpretationStatus': 'not-interpreted'}


def _ingredient_name(line: str, quantity: dict) -> str:
    expression = quantity.get('rawExpression')
    if expression:
        remainder = re.sub(r'^\s*' + re.escape(expression) + r'(?=\s|$)\s*', '', line, count=1)
        remainder = remainder.strip(' ,:;') or line.strip()
    else:
        remainder = line.strip()
    return remainder


def _ingredient_details(text: str) -> dict:
    """Separate explicit parenthetical/cut descriptors without translating them."""
    substitution = None
    match = re.search(r'(?i)\b(substitute|instead of|or use|alternatively)\b.*$', text)
    if match:
        substitution = match.group(0).strip()
        text = text[:match.start()].strip(' ,;')
    preparation = re.findall(r'\(([^()]*)\)', text)
    name = re.sub(r'\s*\([^()]*\)', '', text).strip(' ,;') or text
    return {'name':name,'preparation':preparation,'substitution':substitution}


def parse_html_recipe(raw: bytes, *, source: dict, source_id: str,
                      source_record_id: str, country: str | None,
                      language: str, attribution: str | None = None) -> dict:
    """Extract a single recipe from a receipt-pinned HTML source snapshot."""
    try:
        html = raw.decode(source.get('encoding', 'utf-8'), errors='strict')
    except (LookupError, UnicodeDecodeError) as error:
        raise ParseError('html-encoding-invalid') from error
    soup = BeautifulSoup(html, 'html.parser')
    title = _heading(soup)
    if not title:
        raise ParseError('recipe-title-missing')
    # Prefer source-published JSON-LD: it retains its own ingredient/step structure.
    ld = None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = value if isinstance(value, list) else value.get('@graph', [value]) if isinstance(value, dict) else []
        for candidate in candidates:
            if isinstance(candidate, dict) and 'Recipe' in str(candidate.get('@type', '')):
                ld = candidate
                break
        if ld:
            break
    text = soup.get_text('\n', strip=False)
    extraction_sha = sha256(text.encode('utf-8'))
    ingredients: list[dict] = []
    steps: list[dict] = []
    if ld:
        raw_ingredients = ld.get('recipeIngredient') or []
        instructions = ld.get('recipeInstructions') or []
        if isinstance(instructions, str):
            instructions = [instructions]
        for i, expression in enumerate(raw_ingredients, 1):
            if not isinstance(expression, str) or not expression.strip():
                continue
            original = expression.strip()
            quantity = _quantity(original)
            details = _ingredient_details(_ingredient_name(original, quantity))
            ingredients.append({'ingredientLineId': f'{source_id}:{source_record_id}:i{i}',
                'order': i, 'componentIndex': 1,
                'sourceNameText': details['name'], 'preparationDescriptors': details['preparation'],
                'substitutionText': details['substitution'],
                'originalExpression': original, 'quantity': quantity,
                'foodIdentity': None, 'foodMatchStatus': 'unmatched-source-text',
                'location': _location(text, max(0, text.find(original)), max(0, text.find(original)) + len(original))})
        for i, instruction in enumerate(instructions, 1):
            if isinstance(instruction, dict):
                original = instruction.get('text') or instruction.get('name')
            else:
                original = instruction
            if not isinstance(original, str) or not original.strip():
                continue
            original = original.strip()
            start = text.find(original)
            steps.append({'order': i, 'componentIndex': 1, 'originalText': original,
                'actionTerms': [], 'equipment': [], 'time': None, 'temperature': None,
                'targetState': None,
                'location': _location(text, max(0, start), max(0, start) + len(original))})
        yield_value = ld.get('recipeYield')
        yield_text = str(yield_value).strip() if yield_value is not None else None
        yield_match = re.match(r'^\s*(\d+(?:[.,]\d+)?)\s*(.*)$', yield_text or '')
        yield_record = ({'rawText': yield_text,
            'rawValueLexeme': yield_match.group(1) if yield_match else None,
            'rawUnitLexeme': yield_match.group(2) if yield_match and yield_match.group(2) else None,
            'interpretedValue': None, 'interpretedUnit': None,
            'interpretationStatus': 'not-interpreted',
            'location': _location(text, max(0, text.find(yield_text)), max(0, text.find(yield_text)) + len(yield_text))}
            if yield_text else None)
    else:
        # Extract explicit source sections only; subgroup headings and notes
        # remain source-scoped and no canonical ingredient identity is assigned.
        headers = soup.find_all(['h2', 'h3', 'h4'])
        ingredient_header = next((h for h in headers if h.get_text(' ', strip=True).casefold() in {'ingredients', 'ingredienti'}), None)
        method_header = next((h for h in headers if h.get_text(' ', strip=True).casefold() in {'method', 'directions', 'instructions', 'preparation'}), None)
        yield_record = None
        if ingredient_header and method_header and ingredient_header.parent is method_header.parent:
            siblings = list(ingredient_header.parent.children)
            i = 0
            subgroup = 1
            active = False
            for node in siblings:
                if node is ingredient_header:
                    active = True
                    continue
                if node is method_header:
                    active = False
                    break
                if not active or getattr(node, 'name', None) is None:
                    continue
                if node.name in {'h2', 'h3', 'h4'}:
                    label = node.get_text(' ', strip=True).casefold()
                    if label in {'dressing', 'sauce', 'topping', 'for the dressing', 'for the sauce'}:
                        subgroup += 1
                elif node.name in {'ul', 'ol'}:
                    for li in node.find_all('li', recursive=False):
                        original = li.get_text(' ', strip=True)
                        if not original:
                            continue
                        i += 1
                        quantity = _quantity(original)
                        start_at = text.find(original)
                        details = _ingredient_details(_ingredient_name(original, quantity))
                        ingredients.append({'ingredientLineId': f'{source_id}:{source_record_id}:i{i}',
                            'order': i, 'componentIndex': subgroup,
                            'sourceNameText': details['name'], 'preparationDescriptors': details['preparation'],
                            'substitutionText': details['substitution'],
                            'originalExpression': original, 'quantity': quantity,
                            'foodIdentity': None, 'foodMatchStatus': 'unmatched-source-text',
                            'location': _location(text, max(0, start_at), max(0, start_at) + len(original))})
            siblings = list(method_header.parent.children)
            active = False
            for node in siblings:
                if node is method_header:
                    active = True
                    continue
                if active and getattr(node, 'name', None) in {'h2', 'h3', 'h4'}:
                    break
                if not active or getattr(node, 'name', None) not in {'p', 'ol', 'ul'}:
                    continue
                if node.name in {'ol', 'ul'}:
                    phrases = [li.get_text(' ', strip=True) for li in node.find_all('li', recursive=False)]
                else:
                    phrases = [node.get_text(' ', strip=True)]
                for original in phrases:
                    if not original or re.match(r'(?i)^\d+(?:[.,]\d+)?\s+minutes?\s+(?:preparation|prep)', original):
                        continue
                    ym = re.search(r'(?i)\b(serves?\s+\d+(?:[.,]\d+)?(?:\s+[^.]+)?)\s*\.?$', original)
                    if ym:
                        raw_yield = ym.group(1).strip()
                        parsed_yield = re.match(r'(?i)serves?\s+(\d+(?:[.,]\d+)?)\s*(.*)', raw_yield)
                        ys = text.find(raw_yield)
                        yield_record = {'rawText': raw_yield,
                            'rawValueLexeme': parsed_yield.group(1) if parsed_yield else None,
                            'rawUnitLexeme': parsed_yield.group(2) if parsed_yield and parsed_yield.group(2) else None,
                            'interpretedValue': None, 'interpretedUnit': None,
                            'interpretationStatus': 'not-interpreted',
                            'location': _location(text, max(0, ys), max(0, ys) + len(raw_yield))}
                        original = original[:ym.start()].strip()
                    if original:
                        start_at = text.find(original)
                        steps.append({'order': len(steps) + 1, 'componentIndex': 1,
                            'originalText': original, 'actionTerms': [], 'equipment': [],
                            'time': None, 'temperature': None, 'targetState': None,
                            'location': _location(text, max(0, start_at), max(0, start_at) + len(original))})
    if not ingredients or not steps:
        raise ParseError('recipe-ingredients-or-steps-not-supported')
    title_start = text.find(title)
    nutrition = _nutrition_assertions(soup, text, language)
    record = {'recipeTemplate': RECIPE_TEMPLATE_VERSION,
        'dictionaryVersion': DICTIONARY_VERSION, 'mappingVersion': MAPPING_VERSION,
        'source': _citation(source, source_id, source_record_id, language, country,
                            source.get('originalSHA256') or sha256(raw), extraction_sha, attribution),
        'originalTitle': title, 'originalHeadingLines': [title], 'aliases': [],
        'language': language, 'region': source.get('region'), 'yield': yield_record,
        'ingredientLines': ingredients, 'orderedSteps': steps,
        'components': _components(ingredients, steps),
        'sourceNotes': _source_notes(soup, text), 'nutritionAssertions': nutrition,
        'equipment': [], 'time': _time_observations(text), 'temperature': None,
        'sourceLocation': _location(text, max(0, title_start), max(0, title_start) + len(title)),
        'identity': {'canonicalDishId': None, 'mergePerformed': False,
                     'identityStatus': 'source-scoped-distinct-record'}}
    _validate_record(record)
    return record


def _nutrition_assertions(soup: BeautifulSoup, text: str, language: str) -> list[dict]:
    assertions = []
    for table in soup.find_all('table'):
        rows = [[cell.get_text(' ', strip=True) for cell in row.find_all(['th', 'td'])]
                for row in table.find_all('tr')]
        headers = next((row for row in rows if any('quantity per serving' in x.casefold() for x in row)), None)
        if not headers:
            continue
        basis_row = next((row for row in rows if any(x.casefold().startswith('serve size:') for x in row)), [])
        basis = next((x.split(':', 1)[1].strip() for x in basis_row if x.casefold().startswith('serve size:')), None)
        if basis:
            basis = 'per serving; source serve size ' + basis
        colnames = headers[1:]
        for row in rows[rows.index(headers) + 1:]:
            if len(row) < 2 or not row[0]:
                continue
            source_name = row[0]
            for index, raw in enumerate(row[1:]):
                if index >= len(colnames):
                    continue
                match = re.fullmatch(r'\s*([-+]?\d+(?:[.,]\d+)?)\s*([A-Za-zµμ]+)?\s*', raw)
                raw_value, raw_unit = (match.group(1), match.group(2)) if match else (raw or None, None)
                heading = colnames[index]
                assertions.append({'sourceFieldName':source_name,
                    'sourceLanguage':language, 'meaning':'Source-labelled nutrient value; source name retained without canonical equivalence claim',
                    'rawDatatype':'string lexical table cell','rawValue':raw_value,'rawUnit':raw_unit,
                    'sourceBasis':heading + (('; ' + basis) if basis and 'serving' in heading.casefold() else ''),
                    'interpretedValue':None,'interpretedUnit':None,
                    'missingValueStatus':'reported' if raw not in {'', '-', '—'} else 'source-cell-missing',
                    'location':_location(text, max(0,text.find(source_name)), max(0,text.find(source_name))+len(source_name))})
    return assertions


def _components(ingredients: list[dict], steps: list[dict]) -> list[dict]:
    indices = sorted({x['componentIndex'] for x in ingredients} | {x['componentIndex'] for x in steps}) or [1]
    return [{'componentIndex': index, 'title': None, 'titleLocation': None,
             'ingredients': [x for x in ingredients if x['componentIndex'] == index],
             'steps': [x for x in steps if x['componentIndex'] == index]} for index in indices]


def _source_notes(soup: BeautifulSoup, text: str) -> list[dict]:
    notes = []
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        label = heading.get_text(' ', strip=True)
        if label.casefold() not in {'variation', 'variations', 'notes', 'nutrition information'}:
            continue
        node = heading.find_next_sibling()
        while node and node.name not in {'h2', 'h3', 'h4'}:
            if node.name == 'p':
                original = node.get_text(' ', strip=True)
                if original:
                    start = text.find(original)
                    notes.append({'originalText': original, 'location': _location(text, max(0,start), max(0,start)+len(original)), 'sourceSection': label})
            node = node.find_next_sibling()
    return notes


def _time_observations(text: str) -> dict | None:
    match = re.search(r'(?i)(\d+(?:[.,]\d+)?\s*(?:minutes?|mins?|hours?|hrs?))\s+(?:preparation|prep)', text)
    if not match:
        return None
    return {'rawText': match.group(0), 'rawValueLexeme': match.group(1),
            'interpretedValue': None, 'interpretedUnit': None,
            'interpretationStatus': 'source-time-label-preserved'}


def _menu_price(item_text: str) -> tuple[dict | None, str | None]:
    # Money is preserved lexically; this is only a syntactic parse with currency
    # code unknown if the source uses a symbol rather than an explicit ISO code.
    m = re.search(r'(?<!\w)(\d+(?:[,.]\d{1,2})?)\s*(€|EUR|\$|USD|£)', item_text, re.I)
    if not m:
        return None, None
    symbol = m.group(2)
    currency = {'€': 'EUR', 'EUR': 'EUR', '$': None, 'USD': 'USD', '£': 'GBP'}[symbol.upper() if symbol.isalpha() else symbol]
    return {'rawValue': m.group(1), 'rawCurrency': symbol,
            'interpretedValue': None, 'interpretedCurrency': currency,
            'interpretationStatus': 'symbol-to-currency-code' if currency else 'currency-code-unknown'}, currency


def parse_html_menu(raw: bytes, *, source: dict, source_id: str,
                    country: str | None, language: str,
                    attribution: str | None = None) -> list[dict]:
    """Extract primary-menu cards from known retained menu DOM structures."""
    try:
        html = raw.decode(source.get('encoding', 'utf-8'), errors='strict')
    except (LookupError, UnicodeDecodeError) as error:
        raise ParseError('html-encoding-invalid') from error
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text('\n', strip=False)
    extraction_sha = sha256(text.encode('utf-8'))
    entries = []
    if source.get('adapter') == 'calmos-menu-v1':
        for index, card in enumerate(soup.select('.menuItemBox'), 1):
            name_node = card.select_one('.menuItemName')
            if not name_node:
                continue
            name = name_node.get_text(' ', strip=True)
            desc_node = card.select_one('.menuItemDesc, .menuItemDescription')
            description = desc_node.get_text(' ', strip=True) if desc_node else None
            section = card.find_parent(class_='menuCategory')
            category = section.find(['h2', 'h3']) if section else None
            category_name = category.get_text(' ', strip=True) if category else None
            original = card.get_text(' ', strip=True)
            start = text.find(name)
            location = _location(text, max(0, start), max(0, start) + len(name))
            entry_id = str(card.get('id') or f'{source_id}:menu:{index}')
            price, currency = _menu_price(original)
            entries.append((entry_id, name, description, category_name, price, currency, location))
    elif source.get('adapter') == 'ocean82-menu-v1':
        for index, card in enumerate(soup.select('li.food-element'), 1):
            name_node = card.select_one('.food-item-title')
            if not name_node:
                continue
            name = name_node.get_text(' ', strip=True)
            desc_node = card.select_one('.food-item-description, .food-item-content, .food-item-desc')
            description = desc_node.get_text(' ', strip=True) if desc_node else None
            group = card.find_parent(class_='food-section')
            category_node = group.select_one('.food-section-title, h2') if group else None
            category = category_node.get_text(' ', strip=True) if category_node else None
            original = card.get_text(' ', strip=True)
            start = text.find(name)
            location = _location(text, max(0, start), max(0, start) + len(name))
            entry_id = str(card.get('data-food') or card.get('id') or f'{source_id}:menu:{index}')
            price, currency = _menu_price(original)
            entries.append((entry_id, name, description, category, price, currency, location))
    else:
        raise ParseError('menu-adapter-unsupported')
    if not entries:
        raise ParseError('menu-items-not-supported')
    records = []
    for entry_id, name, desc, category, price, currency, location in entries:
        record = {'menuTemplate': MENU_TEMPLATE_VERSION,
            'dictionaryVersion': DICTIONARY_VERSION, 'mappingVersion': MAPPING_VERSION,
            'source': _citation(source, source_id, entry_id, language, country,
                source.get('originalSHA256') or sha256(raw), extraction_sha, attribution),
            'originalItemName': name, 'originalDescription': desc,
            'venue': source.get('venue') if isinstance(source.get('venue'), dict) else ({'sourceName': source.get('venue')} if source.get('venue') else None), 'price': price, 'currency': currency,
            'language': language, 'recipeCandidates': [], 'location': location,
            'sourceCategory': category}
        _validate_record(record)
        records.append(record)
    return records


def atomic_jsonl(path: Path, records: list[dict]) -> str:
    blob = b''.join(canonical(record) for record in records)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != blob:
            raise ParseError('output-conflict')
        return sha256(blob)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob); stream.flush(); os.fsync(stream.fileno())
        os.link(name, path)
        os.unlink(name)
        dfd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(name): os.unlink(name)
    return sha256(blob)


def run_html_asset(*, input_path: Path, output_root: Path, source: dict,
                   source_id: str, kind: str, country: str | None,
                   language: str, attribution: str | None = None,
                   source_record_id: str | None = None) -> dict:
    raw = _read_original(input_path)
    original_sha = sha256(raw)
    expected = source.get('originalSHA256')
    if expected and expected != original_sha:
        raise ParseError('original-hash-mismatch')
    source = dict(source, originalSHA256=original_sha)
    if kind == 'recipe':
        record = parse_html_recipe(raw, source=source, source_id=source_id,
            source_record_id=source_record_id or input_path.stem,
            country=country, language=language, attribution=attribution)
        records = [record]
        data_type = 'recipes'
    elif kind == 'menu':
        records = parse_html_menu(raw, source=source, source_id=source_id,
            country=country, language=language, attribution=attribution)
        data_type = 'menuItems'
    else:
        raise ParseError('unsupported-html-kind')
    identity = {'sourceId': source_id, 'sourceRecordId': source_record_id or input_path.stem,
        'originalSHA256': original_sha, 'parserVersion': PARSER_VERSION,
        'dictionaryVersion': DICTIONARY_VERSION, 'templateVersion':
            RECIPE_TEMPLATE_VERSION if kind == 'recipe' else MENU_TEMPLATE_VERSION,
        'mappingVersion': MAPPING_VERSION}
    run_key = sha256(canonical(identity))
    target = output_root / data_type / source_id / run_key
    target.mkdir(parents=True, exist_ok=True)
    data_path = target / (('recipes' if kind == 'recipe' else 'menu-items') + '.jsonl')
    output_sha = atomic_jsonl(data_path, records)
    demo_path = target / 'demonstration.json'
    demo_blob = canonical(records[0])
    if demo_path.exists() and demo_path.read_bytes() != demo_blob:
        raise ParseError('output-conflict')
    if not demo_path.exists():
        fd, tmp = tempfile.mkstemp(prefix='.pending-', dir=target)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(demo_blob); stream.flush(); os.fsync(stream.fileno())
        os.link(tmp, demo_path); os.unlink(tmp)
    summary = {'schemaVersion': 'offmenu-source-parse-summary/1',
        'sourceId': source_id, 'sourceScope': country or source.get('scope') or 'unknown',
        'dataType': data_type, 'inputBytes': len(raw), 'acceptedRecords': len(records),
        'rejectedRecords': 0, 'ingredientLines': sum(len(r.get('ingredientLines', [])) for r in records),
        'orderedSteps': sum(len(r.get('orderedSteps', [])) for r in records),
        'normalizationPerformed': False, 'translationPerformed': False,
        'sourceCoverageComplete': False}
    manifest = {'schemaVersion': 'offmenu-source-parse-manifest/1', 'status': 'complete',
        'runKey': run_key, 'identity': identity, 'inputPath': str(input_path),
        'inputBytes': len(raw), 'inputSHA256': original_sha, 'acceptedRecords': len(records),
        'rejectedRecords': 0, 'exitState': 'success', 'networkRequests': 0,
        'artifacts': {data_path.name: {'bytes': data_path.stat().st_size, 'sha256': output_sha},
                      'demonstration.json': {'bytes': demo_path.stat().st_size, 'sha256': sha256(demo_path.read_bytes())}},
        'summary': summary}
    manifest_path = target / 'manifest.json'
    blob = canonical(manifest)
    if manifest_path.exists() and manifest_path.read_bytes() != blob:
        raise ParseError('manifest-conflict')
    if not manifest_path.exists():
        fd, tmp = tempfile.mkstemp(prefix='.pending-', dir=target)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob); stream.flush(); os.fsync(stream.fileno())
        os.link(tmp, manifest_path); os.unlink(tmp)
    return manifest
