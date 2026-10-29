"""Cache and replay assistant-authored extraction intermediates.

No model call or network access is implemented here. The assistant response is
supplied by the caller, then source-checked and replayed through the existing
OffMenu recipe schema. Originals and cache envelopes belong on Foo, not Git.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
import fcntl

from bs4 import BeautifulSoup

try:
    from . import source_faithful_parse as parser
except ImportError:  # direct-file loading used by focused scripts/tests
    import sys
    _ROOT = Path(__file__).resolve().parents[2]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from offmenu.refresh import source_faithful_parse as parser

SCHEMA_VERSION = 'offmenu-assistant-recipe-intermediate/1'
PROMPT_VERSION = 'offmenu-assistant-source-faithful-extraction/1.0.0'
TRANSFORM_VERSION = 'offmenu-assistant-intermediate-to-source-recipe/1.0.2'
CACHE_VERSION = 'offmenu-assistant-extraction-cache/2'
MAX_RESPONSE_BYTES = 1_000_000


class IntermediateError(ValueError):
    """Rejected extraction or cache; never a usable parsed record."""


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _canonical(value: object) -> bytes:
    return parser.canonical(value)


def _norm(text: str) -> str:
    return ' '.join(text.split())


def _assistant_permission_allowed(source: dict) -> bool:
    evidence = source.get('assistantExtractionPermissionEvidence')
    return (source.get('assistantExtractionAllowed') is True and
            isinstance(evidence, str) and bool(evidence.strip()))


def _load_source(input_path: Path, encoding: str = 'utf-8') -> tuple[bytes, BeautifulSoup, str]:
    raw = parser._read_original(input_path)
    try:
        decoded = raw.decode(encoding, errors='strict')
        if input_path.suffix.casefold() in {'.wikitext', '.wiki'}:
            return raw, BeautifulSoup('', 'html.parser'), decoded
        soup = BeautifulSoup(decoded, 'html.parser')
    except (LookupError, UnicodeDecodeError) as exc:
        raise IntermediateError('source-decode-failed') from exc
    return raw, soup, soup.get_text('\n', strip=False)


def _header_label(header) -> str:
    return _norm(header.get_text(' ', strip=True)).casefold()


def _section_nodes(soup: BeautifulSoup, label: str) -> list:
    body = soup.select_one('.field--name-body') or soup.body or soup
    aliases = {'method': {'method', 'directions', 'instructions', 'preparation',
                          'procedure', 'procedure (brief)', 'procedure (detailed)'},
               'ingredients': {'ingredients', 'ingredienti'}}
    accepted = aliases.get(label.casefold(), {label.casefold()})
    headers = body.find_all(['h2', 'h3', 'h4'])
    header = next((h for h in headers if _header_label(h) in accepted), None)
    if header is None:
        raise IntermediateError('source-section-missing:' + label.casefold())
    level = int(header.name[1])
    nodes, node = [], header
    while True:
        node = node.find_next_sibling()
        if node is None:
            break
        if node.name in {'h2', 'h3', 'h4'} and (
                int(node.name[1]) <= level or
                (label.casefold() == 'method' and _header_label(node) in {
                    'variation', 'variations', 'hint', 'notes', 'serving suggestion'})):
            break
        nodes.append(node)
    return nodes


def _wiki_nodes(soup: BeautifulSoup, label: str) -> list:
    """Read retained MediaWiki section nodes for the explicit bounded adapter."""
    body = soup.select_one('.field--name-body') or soup.body or soup
    headers = body.find_all(['h2', 'h3', 'h4'])
    wanted = {'ingredients': {'ingredients', 'ingredienti'},
              'method': {'method', 'procedure', 'procedure (brief)',
                         'procedure (detailed)', 'directions', 'instructions',
                         'preparation'}}[label]
    header = next((h for h in headers if _header_label(h) in wanted), None)
    if header is None:
        return []
    level = int(header.name[1])
    nodes, node = [], header
    while True:
        node = node.find_next_sibling()
        if node is None or (node.name in {'h2', 'h3', 'h4'} and int(node.name[1]) <= level):
            break
        nodes.append(node)
    return nodes


def _ingredients_from_nodes(nodes: list) -> list[str]:
    lines = []
    for node in nodes:
        if node.name in {'ul', 'ol'}:
            lines.extend(li.get_text(' ', strip=True) for li in node.find_all('li', recursive=False)
                         if li.get_text(' ', strip=True))
        elif node.name == 'p' and node.get_text(' ', strip=True):
            lines.append(node.get_text(' ', strip=True))
    return lines


def _source_lines(soup: BeautifulSoup, raw_lines: list[str],
                  page_text: str) -> list[str]:
    """Map displayed wiki text back to unique, exact source-page line text."""
    if not raw_lines:
        return []
    mapped = []
    for raw in raw_lines:
        candidates = [line.strip() for line in page_text.splitlines()
                      if line.strip() and _wiki_plain_text(line) == _wiki_plain_text(raw)]
        if len(candidates) != 1:
            raise IntermediateError('wiki-source-line-not-unique')
        mapped.append(candidates[0])
    return mapped


def _wiki_plain_text(text: str) -> str:
    """Expose link display text and remove markup without rewriting source lexemes."""
    text = re.sub(r'^\s*[#*;:]+\s*', '', text)
    text = re.sub(r'<ref\b[^>]*>.*?</ref>|<ref[^>]*/>', '', text,
                  flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^]]+)\]\]', r'\1', text)
    text = re.sub(r"'{2,5}", '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return _norm(text)


def _wiki_method_text(soup: BeautifulSoup) -> list[str]:
    body = soup.select_one('.field--name-body') or soup.body or soup
    headers = body.find_all(['h2', 'h3', 'h4'])
    instructions = []
    for header in headers:
        if _header_label(header) not in {'procedure (brief)', 'method', 'directions',
                                          'instructions', 'preparation'}:
            continue
        level = int(header.name[1])
        node = header
        while True:
            node = node.find_next_sibling()
            if node is None or (node.name in {'h2', 'h3', 'h4'} and int(node.name[1]) <= level):
                break
            if node.name in {'ol', 'ul'}:
                instructions.extend(_wiki_plain_text(li.get_text(' ', strip=True))
                                    for li in node.find_all('li', recursive=False)
                                    if li.get_text(' ', strip=True))
            elif node.name == 'p' and node.get_text(' ', strip=True):
                instructions.append(_wiki_plain_text(node.get_text(' ', strip=True)))
    return [text for text in instructions if text]


def _yield_lines(soup: BeautifulSoup) -> list[str]:
    body = soup.select_one('.field--name-body') or soup.body or soup
    summary = next((node for node in body.find_all()
                    if node.name in {'div', 'table'} and
                    ('recipesummary' in ' '.join(node.get('class', [])).casefold() or
                     'servings' in node.get_text(' ', strip=True).casefold())), None)
    candidates = []
    if summary is not None:
        candidates.extend(node.get_text(' ', strip=True) for node in summary.find_all(['td', 'th', 'li']))
        candidates.append(summary.get_text(' ', strip=True))
    for text in candidates:
        match = re.search(r'(?i)(?:servings?|serves?)\s*[=:|]?\s*(\d+\s*[-–]\s*\d+|\d+)', text)
        if match:
            return [match.group(1).replace(' ', '')]
    return []


def _wikitext_recipe_segments(text: str) -> dict | None:
    """Segment only explicit ingredient and brief-procedure sections in wiki text."""
    lines = text.splitlines()
    if not any(re.fullmatch(r'\s*=+\s*Ingredients\s*=+\s*', line, re.I) for line in lines):
        return None
    ingredients, directions = [], []
    section = None
    for line in lines:
        heading = re.fullmatch(r'\s*(=+)\s*(.*?)\s*\1\s*', line)
        if heading:
            label = _norm(heading.group(2)).casefold()
            section = (('ingredients' if label == 'ingredients' else
                        'brief' if label == 'procedure (brief)' else None), len(heading.group(1)))
            continue
        if section is None or not line.strip():
            continue
        mode, level = section
        if mode == 'ingredients' and len(line) - len(line.lstrip('*')) >= 1:
            ingredients.append(re.sub(r'^\s*\*+\s*', '', line).strip())
        elif mode == 'brief' and len(line) - len(line.lstrip('#')) >= 1:
            directions.append(re.sub(r'^\s*#+\s*', '', line).strip())
    summary = re.search(r'(?im)^\s*\{\{recipesummary\b([^}]*(?:\}[^}]*)?)', text)
    yield_lines = []
    if summary:
        serving = re.search(r'(?i)servings\s*=\s*(\d+\s*[-–]\s*\d+|\d+)', summary.group(1))
        if serving:
            yield_lines.append(re.sub(r'\s+', '', serving.group(1)))
    return {'ingredientLines': ingredients, 'directionParagraphs': directions,
            'yields': yield_lines, 'variations': []}


def _recipe_sections(soup: BeautifulSoup, page_text: str | None = None) -> dict:
    text = page_text if page_text is not None else soup.get_text('\n', strip=False)
    wiki = _wikitext_recipe_segments(text)
    if wiki is not None:
        wiki['ingredientLines'] = _source_lines(soup, wiki['ingredientLines'], text)
        wiki['directionParagraphs'] = _source_lines(soup, wiki['directionParagraphs'], text)
        return wiki
    body = soup.select_one('.field--name-body') or soup.body or soup
    wiki_markup = any(re.fullmatch(r'\s*=+\s*[^=]+\s*=+\s*', line) for line in text.splitlines())
    ingredients = _ingredients_from_nodes(_section_nodes(soup, 'Ingredients'))
    directions, yields = [], []
    for node in _section_nodes(soup, 'Method'):
        if node.name not in {'p', 'ol', 'ul'} or not node.get_text(' ', strip=True):
            continue
        texts = ([li.get_text(' ', strip=True) for li in node.find_all('li', recursive=False)]
                 if node.name in {'ol', 'ul'} else [node.get_text(' ', strip=True)])
        for value in texts:
            value = value.strip()
            if not value:
                continue
            full_yield = re.fullmatch(r'(?i)((?:serves?|makes?)\s+\d+(?:\s*[-–]\s*\d+)?(?:\s+[^.]+)?)[.]?', value)
            if full_yield:
                yields.append(full_yield.group(1))
                continue
            trailing_yield = re.search(r'(?i)\s+((?:serves?|makes?)\s+\d+(?:\s*[-–]\s*\d+)?(?:\s+[^.]+)?)[.]?$', value)
            if trailing_yield:
                yields.append(trailing_yield.group(1))
                value = value[:trailing_yield.start()].rstrip()
            if value:
                directions.append(value)
    variations = []
    for header in body.find_all(['h2', 'h3', 'h4']):
        label = _header_label(header)
        if label not in {'variation', 'variations', 'hint', 'notes', 'serving suggestion'}:
            continue
        display_label = _norm(header.get_text(' ', strip=True))
        level = int(header.name[1])
        node = header
        while True:
            node = node.find_next_sibling()
            if node is None or (node.name in {'h2', 'h3', 'h4'} and int(node.name[1]) <= level):
                break
            if (not wiki_markup and node.name == 'p' and
                    node.get_text(' ', strip=True)):
                variations.append({'section': display_label, 'text': node.get_text(' ', strip=True)})
    return {'ingredientLines': ingredients, 'directionParagraphs': directions,
            'yields': yields, 'variations': variations}



def source_segments(soup: BeautifulSoup, page_text: str | None = None) -> dict:
    return _recipe_sections(soup, page_text)


def _loc(text: str, quote: str, start: int) -> dict:
    end = start + len(quote)
    before = text[:start]
    return {'page': 1, 'lineStart': before.count('\n') + 1,
            'lineEnd': before.count('\n') + 1 + quote.count('\n'),
            'utf8ByteRange': [len(before.encode('utf-8')),
                              len(text[:end].encode('utf-8'))],
            'pageTextSHA256': _sha(text.encode('utf-8')),
            'sourceSpanSHA256': _sha(quote.encode('utf-8'))}


def _loc_quote(text: str, quote: str) -> dict:
    start = text.find(quote)
    actual = quote
    if start < 0:
        pattern = re.compile(r'\s+'.join(re.escape(part) for part in quote.split()))
        match = pattern.search(text)
        if not match:
            raise IntermediateError('source-quote-not-locatable')
        start, actual = match.start(), match.group(0)
    return _loc(text, actual, start)


def _validate(response: dict, *, soup: BeautifulSoup, page_text: str,
              parsed_record: dict, source_segments_value: dict | None = None) -> None:
    if not isinstance(response, dict) or response.get('schemaVersion') != SCHEMA_VERSION:
        raise IntermediateError('intermediate-schema-version-invalid')
    if not isinstance(response.get('uncertainty'), list) or not isinstance(response.get('ambiguities'), list):
        raise IntermediateError('uncertainty-or-ambiguity-list-missing')
    if any(not isinstance(x, str) or not x.strip() for x in response['uncertainty']):
        raise IntermediateError('uncertainty-entry-invalid')
    for item in response['ambiguities']:
        if not isinstance(item, dict) or not isinstance(item.get('sourceText'), str) or not item['sourceText']:
            raise IntermediateError('ambiguity-source-reference-invalid')
        if item['sourceText'] not in response.get('ingredientCoverage', []) and item['sourceText'] not in response.get('directionCoverage', []):
            raise IntermediateError('ambiguity-source-reference-unmatched')
        if not all(isinstance(item.get(k), str) and item[k].strip() for k in ('field', 'interpretation', 'reason')):
            raise IntermediateError('ambiguity-explanation-incomplete')
        _loc_quote(page_text, item['sourceText'])
    segments = source_segments(soup, page_text) if source_segments_value is None else source_segments_value
    if response.get('ingredientCoverage') != segments['ingredientLines']:
        raise IntermediateError('ingredient-coverage-does-not-match-source')
    if response.get('directionCoverage') != segments['directionParagraphs']:
        raise IntermediateError('direction-coverage-does-not-match-source')
    if response.get('yieldCoverage') != segments['yields']:
        raise IntermediateError('yield-coverage-does-not-match-source')
    parsed_yield = parsed_record.get('yield') or {}
    if segments['yields'] and _norm(parsed_yield.get('rawText', '')).casefold() not in {_norm(y).casefold() for y in segments['yields']}:
        raise IntermediateError('deterministic-yield-source-mismatch')
    extracted_ingredients = response.get('ingredients')
    source_ingredients = parsed_record.get('ingredientLines', [])
    if not isinstance(extracted_ingredients, list) or len(extracted_ingredients) != len(source_ingredients):
        raise IntermediateError('ingredient-record-count-mismatch')
    for index, (item, parsed) in enumerate(zip(extracted_ingredients, source_ingredients), 1):
        if not isinstance(item, dict) or item.get('order') != index:
            raise IntermediateError('ingredient-order-invalid')
        quote = item.get('sourceText')
        if quote != parsed.get('originalExpression') or quote != segments['ingredientLines'][index - 1]:
            raise IntermediateError('ingredient-source-span-mismatch')
        semantic_quote = _wiki_plain_text(quote)
        name = item.get('nameText')
        if not isinstance(name, str) or not name.strip() or _norm(name).casefold() not in _norm(semantic_quote).casefold():
            raise IntermediateError('ingredient-name-unsupported')
        for field in ('quantityText', 'unitText', 'preparationText', 'optionalText'):
            value = item.get(field)
            if value is not None and (not isinstance(value, str) or _norm(value).casefold() not in _norm(semantic_quote).casefold()):
                raise IntermediateError('ingredient-' + field.casefold() + '-unsupported')
        alternatives = item.get('alternatives', [])
        if (not isinstance(alternatives, list) or
                any(not isinstance(value, str) or not value.strip() or _norm(value).casefold() not in _norm(semantic_quote).casefold() for value in alternatives)):
            raise IntermediateError('ingredient-alternative-unsupported')
        if alternatives and len(alternatives) < 2:
            raise IntermediateError('ingredient-alternative-incomplete')
        optional = item.get('optionalText')
        if optional is not None and (not isinstance(optional, str) or _norm(optional).casefold() not in _norm(quote).casefold()):
            raise IntermediateError('ingredient-optional-text-unsupported')
    dirs = response.get('directions')
    if not isinstance(dirs, list) or not dirs:
        raise IntermediateError('direction-steps-missing')
    by_paragraph = {i: [] for i in range(1, len(segments['directionParagraphs']) + 1)}
    for order, step in enumerate(dirs, 1):
        if not isinstance(step, dict) or step.get('order') != order:
            raise IntermediateError('direction-order-invalid')
        pi, quote = step.get('paragraphIndex'), step.get('sourceText')
        if not isinstance(pi, int) or pi not in by_paragraph or not isinstance(quote, str) or not quote:
            raise IntermediateError('direction-source-reference-invalid')
        source_paragraph = segments['directionParagraphs'][pi - 1]
        offset = step.get('paragraphCharRange')
        if (not isinstance(offset, list) or len(offset) != 2 or
                not all(isinstance(n, int) for n in offset) or offset[0] < 0 or
                offset[1] <= offset[0] or source_paragraph[offset[0]:offset[1]] != quote):
            raise IntermediateError('direction-source-span-mismatch')
        by_paragraph[pi].append((offset[0], offset[1]))
        semantic_quote = _wiki_plain_text(quote)
        for name in ('actionTerms', 'equipment'):
            values = step.get(name, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() or _norm(v).casefold() not in _norm(semantic_quote).casefold() for v in values):
                raise IntermediateError('unsupported-' + name.casefold())
        for name in ('timeText', 'temperatureText', 'targetState'):
            value = step.get(name)
            if value is not None and (not isinstance(value, str) or _norm(value).casefold() not in _norm(semantic_quote).casefold()):
                raise IntermediateError('unsupported-' + name.casefold())
    for pi, paragraph in enumerate(segments['directionParagraphs'], 1):
        spans = sorted(by_paragraph[pi])
        cursor = 0
        if not spans:
            raise IntermediateError('direction-paragraph-uncovered')
        for start, end in spans:
            if start != cursor:
                raise IntermediateError('direction-coverage-gap-or-overlap')
            cursor = end
        if cursor != len(paragraph):
            raise IntermediateError('direction-paragraph-incomplete')
    variation_response = response.get('variations', [])
    if not isinstance(variation_response, list):
        raise IntermediateError('variation-list-invalid')
    if [{'section': x.get('section'), 'text': x.get('sourceText')} for x in variation_response] != segments['variations']:
        raise IntermediateError('variation-coverage-does-not-match-source')
    for item in variation_response:
        if not isinstance(item.get('sourceText'), str):
            raise IntermediateError('variation-source-reference-invalid')


def _record(response: dict, parsed_record: dict, page_text: str,
            tooling: dict | None = None) -> dict:
    result = copy.deepcopy(parsed_record)
    steps = []
    paragraph_text = response['directionCoverage']
    for item in response['directions']:
        pi = item['paragraphIndex']
        paragraph = paragraph_text[pi - 1]
        start, end = item['paragraphCharRange']
        quote = item['sourceText']
        absolute = page_text.find(quote)
        if absolute < 0:
            # Whitespace in HTML text nodes can differ from paragraph display text;
            # normalized matching is permitted only to locate, never alter, text.
            pattern = re.compile(r'\s+'.join(re.escape(x) for x in quote.split()))
            match = pattern.search(page_text)
            if not match:
                raise IntermediateError('direction-not-locatable-in-page-text')
            absolute, quote = match.start(), match.group(0)
        step = {'order': item['order'], 'componentIndex': 1,
                'originalText': item['sourceText'],
                'actionTerms': item.get('actionTerms', []),
                'equipment': item.get('equipment', []),
                'time': ({'rawText': item['timeText'], 'interpretedValue': None,
                          'interpretationStatus': 'source-lexeme-preserved'} if item.get('timeText') else None),
                'temperature': ({'rawText': item['temperatureText'], 'interpretedValue': None,
                                 'interpretationStatus': 'source-lexeme-preserved'} if item.get('temperatureText') else None),
                'targetState': item.get('targetState'),
                'location': _loc(page_text, quote, absolute)}
        steps.append(step)
    for item, parsed in zip(response['ingredients'], result['ingredientLines']):
        parsed['location'] = _loc_quote(page_text, item['sourceText'])
        parsed['sourceNameText'] = item['nameText']
        parsed['preparationDescriptors'] = [item['preparationText']] if item.get('preparationText') else []
        parsed['alternatives'] = item.get('alternatives', [])
        parsed['optionalText'] = item.get('optionalText')
        parsed['substitutionText'] = ' or '.join(item.get('alternatives', [])) or None
        quantity = parsed['quantity']
        if item.get('quantityText'):
            existing = quantity.get('rawValueLexeme')
            if existing is not None and _norm(existing) != _norm(item['quantityText']):
                raise IntermediateError('quantity-disagreement-with-deterministic-parser')
            quantity['rawValueLexeme'] = item['quantityText']
        if item.get('unitText'):
            existing = quantity.get('rawUnitLexeme')
            if existing is not None and _norm(existing).casefold() != _norm(item['unitText']).casefold():
                raise IntermediateError('unit-disagreement-with-deterministic-parser')
            quantity['rawUnitLexeme'] = item['unitText']
        if item.get('quantityText') or item.get('unitText'):
            quantity['rawExpression'] = ' '.join(v for v in (quantity.get('rawValueLexeme'), quantity.get('rawUnitLexeme')) if v)
            quantity['interpretationStatus'] = 'assistant-structured-source-lexeme; not-normalized'
        # AI extraction does not convert quantities or assign canonical food identities.
    result['orderedSteps'] = steps
    result['components'] = parser._components(result['ingredientLines'], steps)
    result['sourceNotes'] = list(result.get('sourceNotes', [])) + [
        {'originalText': item['sourceText'], 'sourceSection': item['section'],
         'location': _loc_quote(page_text, item['sourceText'])}
        for item in response.get('variations', [])]
    result['assistantInterpretation'] = {'schemaVersion': SCHEMA_VERSION,
        'promptVersion': PROMPT_VERSION, 'transformVersion': TRANSFORM_VERSION,
        'rawResponseSHA256': response['_rawResponseSHA256'],
        'uncertainty': response['uncertainty'],
        'ambiguities': [{**item, 'location': _loc_quote(page_text, item['sourceText'])}
                        for item in response['ambiguities']],
        'notes': response.get('notes', [])}
    if tooling is not None:
        result['assistantInterpretation']['tooling'] = tooling
    result['source']['extractionParser'] = parser.PARSER_VERSION + '+' + TRANSFORM_VERSION
    parser._validate_record(result)
    return result


def _tooling_manifest(tooling_artifacts: list[dict] | None) -> dict | None:
    """Describe only tooling that actually participated in this derivation.

    Each artifact is an explicit caller-supplied local file with a stable logical
    name. No placeholder/tooling record is emitted when the derivation used none.
    """
    if not tooling_artifacts:
        return None
    entries = []
    names = set()
    for artifact in tooling_artifacts:
        if not isinstance(artifact, dict):
            raise IntermediateError('tooling-artifact-invalid')
        name, location = artifact.get('name'), artifact.get('path')
        if (not isinstance(name, str) or not name.strip() or name in names or
                not isinstance(location, (str, Path)) or
                (artifact.get('version') is not None and not isinstance(artifact.get('version'), str))):
            raise IntermediateError('tooling-artifact-invalid')
        names.add(name)
        path = Path(location)
        if path.is_symlink() or not path.is_file():
            raise IntermediateError('tooling-artifact-not-regular-file')
        blob = path.read_bytes()
        digest = _sha(blob)
        stored_path = f'tooling/{digest}.bin'
        entries.append({'name': name, 'sha256': digest, 'bytes': len(blob),
                        'version': artifact.get('version'), 'cachePath': stored_path})
    entries.sort(key=lambda item: (item['name'], item['sha256']))
    return {'schemaVersion': 'offmenu-ai-derivation-tooling/1',
            'artifacts': entries}


def _source_binding(source: dict, parsed_record: dict, raw_sha: str,
                    input_path: Path) -> dict:
    provenance = parsed_record.get('source')
    if (not isinstance(provenance, dict) or
            not all(isinstance(provenance.get(k), str) and provenance[k]
                    for k in ('sourceId', 'sourceRecordId')) or
            provenance.get('originalSHA256') != raw_sha or
            provenance.get('releaseId') != source.get('release') or
            provenance.get('citationUrl') != (source.get('citationUrl') or source.get('sourceURL') or '')):
        raise IntermediateError('current-source-record-provenance-mismatch')
    return {'provenance': copy.deepcopy(provenance),
            'sourcePolicySHA256': _sha(_canonical(source)),
            'permissionEvidence': source.get('assistantExtractionPermissionEvidence'),
            'encoding': source.get('encoding', 'utf-8'),
            'representation': input_path.suffix.casefold(),
            'baseParsedRecordSHA256': _sha(_canonical(parsed_record))}


def _key_inputs(raw_sha: str, segments: dict, model_identity: str,
                model_version: str, settings: dict,
                source_binding: dict,
                tooling: dict | None = None) -> dict:
    result = {'originalSHA256': raw_sha,
        'sourceSegmentSHA256': _sha(_canonical(segments)),
        'extractionSchemaVersion': SCHEMA_VERSION, 'promptVersion': PROMPT_VERSION,
        'modelIdentity': model_identity, 'modelVersion': model_version,
        'inferenceSettings': settings, 'transformVersion': TRANSFORM_VERSION,
        'recipeSchemaVersion': parser.RECIPE_TEMPLATE_VERSION,
        'parserVersion': parser.PARSER_VERSION,
        'sourceBinding': source_binding}
    if tooling is not None:
        result['tooling'] = tooling
    return result


def _capture_tooling(cache_root: Path, tooling_artifacts: list[dict] | None,
                     tooling: dict | None) -> None:
    if tooling is None:
        return
    by_name = {item['name']: item for item in tooling['artifacts']}
    for artifact in tooling_artifacts or []:
        item = by_name[artifact['name']]
        destination = cache_root / item['cachePath']
        _atomic(destination, Path(artifact['path']).read_bytes())


def _validate_tooling_files(cache_root: Path, tooling: dict | None,
                            tooling_artifacts: list[dict] | None) -> bool:
    """Verify archived tool bytes, and any caller-supplied tool identity."""
    if tooling is None:
        return not tooling_artifacts
    if not isinstance(tooling, dict) or tooling.get('schemaVersion') != 'offmenu-ai-derivation-tooling/1':
        return False
    for item in tooling.get('artifacts', []):
        relative = Path(item.get('cachePath', ''))
        if relative.is_absolute() or '..' in relative.parts:
            return False
        path = cache_root / relative
        if path.is_symlink() or not path.is_file():
            return False
        blob = path.read_bytes()
        if len(blob) != item.get('bytes') or _sha(blob) != item.get('sha256'):
            return False
    if tooling_artifacts is not None:
        return _tooling_manifest(tooling_artifacts) == tooling
    return True


def _atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / '.cache-writer.lock'
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                raise IntermediateError('immutable-output-conflict')
            return
        fd, tmp = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            os.link(tmp, path); os.unlink(tmp)
            dfd = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    finally:
        try: fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally: os.close(lock_fd)


def cache_assistant_intermediate(*, input_path: Path, parsed_record: dict,
        response_text: str, cache_root: Path, output_root: Path,
        source: dict, source_id: str, source_record_id: str,
        country: str | None, language: str, attribution: str | None = None,
        model_identity: str = 'unknown', model_version: str = 'unknown',
        inference_settings: dict | None = None,
        tooling_artifacts: list[dict] | None = None) -> dict:
    """Validate an assistant JSON response, persist it and schema-replay output."""
    if not _assistant_permission_allowed(source):
        raise IntermediateError('source-specific-assistant-extraction-permission-required')
    if len(response_text.encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise IntermediateError('response-size-limit')
    settings = inference_settings or {'temperature': None, 'seed': None,
        'max_tokens': None, 'runtime_parameters': 'not-exposed'}

    raw, soup, page_text = _load_source(input_path, source.get('encoding', 'utf-8'))
    raw_sha = _sha(raw)
    if source.get('originalSHA256') and source['originalSHA256'] != raw_sha:
        raise IntermediateError('original-hash-mismatch')
    segments = source_segments(soup, page_text)
    binding = _source_binding(source, parsed_record, raw_sha, input_path)
    if any(parsed_record['source'].get(k) != v for k, v in
           (('sourceId', source_id), ('sourceRecordId', source_record_id),
            ('countryCode', country), ('language', language))):
        raise IntermediateError('current-source-record-provenance-mismatch')
    current_source = {**binding['provenance'],
                      'permissionEvidence': binding['permissionEvidence'],
                      'encoding': binding['encoding'], 'representation': binding['representation']}
    tooling = _tooling_manifest(tooling_artifacts)
    key_inputs = _key_inputs(raw_sha, segments, model_identity, model_version,
                             settings, binding, tooling)
    cache_key = _sha(_canonical(key_inputs))
    response_sha = _sha(response_text.encode('utf-8'))
    try:
        response = json.loads(response_text)
        if not isinstance(response, dict):
            raise IntermediateError('response-root-invalid')
        _validate(response, soup=soup, page_text=page_text, parsed_record=parsed_record,
                  source_segments_value=segments)
        response = copy.deepcopy(response)
        response['_rawResponseSHA256'] = response_sha
        record = _record(response, parsed_record, page_text, tooling)
        cache = {'cacheSchemaVersion': CACHE_VERSION, 'cacheKey': cache_key,
            'baseParsedRecord': parsed_record,
            'cacheKeyInputs': key_inputs,
            'source': current_source,
            'model': {'identity': model_identity, 'version': model_version,
                      'settings': settings,
                      'execution': 'assistant-authored intermediate; no external API call'},
            'extractedUTC': datetime.now(timezone.utc).isoformat(),
            'rawResponse': response_text, 'rawResponseSHA256': response_sha,
            'validation': {'status': 'valid', 'outcome': 'schema-replay-accepted', 'uncertainty': response.get('uncertainty', [])},
            'transformVersion': TRANSFORM_VERSION, 'parsedRecord': record,
            'normalization': {'status': 'not-run', 'englishGoldAdmission': 'held'}}
        if tooling is not None:
            cache['tooling'] = tooling
        cache_path = cache_root / (cache_key + '.json')
        hit = cache_path.exists()
        if hit:
            prior = json.loads(cache_path.read_text(encoding='utf-8'))
            if (prior.get('cacheKey') != cache_key or prior.get('cacheKeyInputs') != key_inputs or
                    prior.get('cacheSchemaVersion') != CACHE_VERSION or
                    prior.get('source') != current_source or
                    prior.get('baseParsedRecord') != parsed_record or
                    prior.get('validation', {}).get('status') != 'valid' or
                    prior.get('tooling') != tooling or
                    not _validate_tooling_files(cache_root, tooling, tooling_artifacts) or
                    _sha(prior.get('rawResponse', '').encode('utf-8')) != prior.get('rawResponseSHA256')):
                raise IntermediateError('existing-cache-incompatible')
            prior_response = json.loads(prior['rawResponse'])
            _validate(prior_response, soup=soup, page_text=page_text,
                      parsed_record=parsed_record, source_segments_value=segments)
            prior_response = copy.deepcopy(prior_response)
            prior_response['_rawResponseSHA256'] = prior['rawResponseSHA256']
            record = _record(prior_response, parsed_record, page_text, tooling)
            if _canonical(record) != _canonical(prior.get('parsedRecord')):
                raise IntermediateError('existing-cache-replay-mismatch')
            response_sha = prior['rawResponseSHA256']
        else:
            _capture_tooling(cache_root, tooling_artifacts, tooling)
            if not _validate_tooling_files(cache_root, tooling, tooling_artifacts):
                raise IntermediateError('tooling-capture-verification-failed')
            _atomic(cache_path, _canonical(cache))
        record_path = output_root / 'assistant-assisted' / 'recipes' / source_id / (source_record_id + '.json')
        _atomic(record_path, _canonical(record))
        return {'status': 'accepted', 'cacheHit': hit, 'cacheKey': cache_key,
                'cachePath': str(cache_path), 'recordPath': str(record_path),
                'rawResponseSHA256': response_sha, 'originalSHA256': raw_sha,
                'acceptedRecords': 1, 'normalization': 'not-run'}
    except Exception as exc:
        reason = str(exc) if isinstance(exc, IntermediateError) else 'json-or-schema-validation-failed'
        attempt = _sha(_canonical({'sourceSHA256': raw_sha, 'responseSHA256': response_sha,
            'schemaVersion': SCHEMA_VERSION, 'promptVersion': PROMPT_VERSION,
            'modelIdentity': model_identity, 'modelVersion': model_version}))
        rejected = {'cacheSchemaVersion': CACHE_VERSION, 'status': 'rejected',
            'attemptId': attempt, 'source': {'sourceId': source_id,
                'sourceRecordId': source_record_id, 'originalSHA256': raw_sha},
            'model': {'identity': model_identity, 'version': model_version},
            'rawResponse': response_text, 'rawResponseSHA256': response_sha,
            'validation': {'status': 'invalid', 'failureReasons': [reason]}}
        _atomic(cache_root / 'rejected' / (attempt + '.json'), _canonical(rejected))
        if isinstance(exc, IntermediateError):
            raise
        raise IntermediateError(reason) from exc


def find_compatible_intermediate(*, cache_root: Path, input_path: Path,
        source: dict, parsed_record: dict | None = None, model_identity: str = 'unknown',
        model_version: str = 'unknown',
        inference_settings: dict | None = None,
        tooling_artifacts: list[dict] | None = None) -> Path | None:
    """Look up an exact compatible validated response before invoking AI."""
    if not isinstance(parsed_record, dict) or not _assistant_permission_allowed(source):
        return None
    raw, soup, page_text = _load_source(input_path, source.get('encoding', 'utf-8'))
    raw_sha = _sha(raw)
    if source.get('originalSHA256') and source['originalSHA256'] != raw_sha:
        return None
    segments = source_segments(soup, page_text)
    try:
        binding = _source_binding(source, parsed_record, raw_sha, input_path)
    except IntermediateError:
        return None
    current_source = {**binding['provenance'],
                      'permissionEvidence': binding['permissionEvidence'],
                      'encoding': binding['encoding'], 'representation': binding['representation']}
    settings = inference_settings or {'temperature': None, 'seed': None,
        'max_tokens': None, 'runtime_parameters': 'not-exposed'}
    tooling = _tooling_manifest(tooling_artifacts)
    expected = _key_inputs(raw_sha, segments, model_identity, model_version,
                           settings, binding, tooling)
    base_expected = {key: value for key, value in expected.items() if key != 'tooling'}
    exact_path = cache_root / (_sha(_canonical(expected)) + '.json')
    candidates = ([exact_path] if exact_path.is_file() else [])
    if tooling_artifacts is None and cache_root.is_dir():
        candidates.extend(path for path in sorted(cache_root.glob('*.json'))
                          if path != exact_path)
    for path in candidates:
        if path.is_symlink() or not path.is_file():
            continue
        try:
            cache = json.loads(path.read_text(encoding='utf-8'))
            key_inputs = cache.get('cacheKeyInputs', {})
            base_actual = {key: value for key, value in key_inputs.items() if key != 'tooling'}
            recorded_tooling = cache.get('tooling')
            if (cache.get('cacheKey') != _sha(_canonical(key_inputs)) or
                    cache.get('cacheSchemaVersion') != CACHE_VERSION or
                    cache.get('source') != current_source or
                    cache.get('baseParsedRecord') != parsed_record or
                    base_actual != base_expected or
                    cache.get('validation', {}).get('status') != 'valid' or
                    cache.get('source', {}).get('permissionEvidence') != source.get('assistantExtractionPermissionEvidence') or
                    cache.get('tooling') != key_inputs.get('tooling') or
                    not _validate_tooling_files(cache_root, recorded_tooling, tooling_artifacts) or
                    _sha(cache.get('rawResponse', '').encode('utf-8')) != cache.get('rawResponseSHA256')):
                continue
            return path
        except (OSError, ValueError, TypeError, IntermediateError):
            continue
    return None


def replay_cached_intermediate(*, cache_path: Path, input_path: Path,
        parsed_record: dict | None = None, output_root: Path,
        source: dict | None = None,
        tooling_artifacts: list[dict] | None = None) -> dict:
    """Deterministically replay a compatible valid cache; never re-infer."""
    if not isinstance(source, dict) or not isinstance(parsed_record, dict):
        raise IntermediateError('cache-current-source-and-record-required')
    if not _assistant_permission_allowed(source):
        raise IntermediateError('source-specific-assistant-extraction-permission-required')
    cache = json.loads(cache_path.read_text(encoding='utf-8'))
    if cache.get('validation', {}).get('status') != 'valid':
        raise IntermediateError('cache-not-validated')
    ki = cache.get('cacheKeyInputs', {})
    if (cache.get('cacheSchemaVersion') != CACHE_VERSION or
            cache.get('cacheKey') != _sha(_canonical(ki)) or
            ki.get('extractionSchemaVersion') != SCHEMA_VERSION or
            ki.get('promptVersion') != PROMPT_VERSION or
            ki.get('transformVersion') != TRANSFORM_VERSION or
            ki.get('recipeSchemaVersion') != parser.RECIPE_TEMPLATE_VERSION or
            ki.get('parserVersion') != parser.PARSER_VERSION):
        raise IntermediateError('cache-contract-incompatible')
    if _sha(cache.get('rawResponse', '').encode('utf-8')) != cache.get('rawResponseSHA256'):
        raise IntermediateError('cached-response-checksum-invalid')
    if not _validate_tooling_files(cache_path.parent, cache.get('tooling'), tooling_artifacts):
        raise IntermediateError('cache-tooling-incompatible')
    raw, soup, page_text = _load_source(input_path, source.get('encoding', 'utf-8'))
    if _sha(raw) != ki.get('originalSHA256'):
        raise IntermediateError('cache-source-incompatible')
    binding = _source_binding(source, parsed_record, _sha(raw), input_path)
    current_source = {**binding['provenance'],
                      'permissionEvidence': binding['permissionEvidence'],
                      'encoding': binding['encoding'], 'representation': binding['representation']}
    if ki.get('sourceBinding') != binding or cache.get('source') != current_source:
        raise IntermediateError('cache-current-source-binding-mismatch')

    segments = source_segments(soup, page_text)
    if _sha(_canonical(segments)) != ki.get('sourceSegmentSHA256'):
        raise IntermediateError('cache-segment-incompatible')
    response = json.loads(cache['rawResponse'])
    response['_rawResponseSHA256'] = cache['rawResponseSHA256']
    base_record = cache.get('baseParsedRecord')
    if parsed_record is not None and _canonical(parsed_record) != _canonical(base_record):
        raise IntermediateError('cache-base-record-mismatch')
    if not isinstance(base_record, dict):
        raise IntermediateError('cache-base-record-missing')
    _validate(response, soup=soup, page_text=page_text, parsed_record=base_record,
              source_segments_value=segments)
    record = _record(response, base_record, page_text, cache.get('tooling'))
    if _canonical(record) != _canonical(cache.get('parsedRecord')):
        raise IntermediateError('cache-replay-nondeterministic')
    path = output_root / 'assistant-assisted' / 'recipes' / current_source['sourceId'] / (current_source['sourceRecordId'] + '.json')
    _atomic(path, _canonical(record))
    return {'status': 'replayed', 'cacheKey': cache['cacheKey'],
            'rawResponseSHA256': cache['rawResponseSHA256'], 'recordPath': str(path),
            'acceptedRecords': 1}
