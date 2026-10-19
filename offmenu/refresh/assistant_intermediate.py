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
TRANSFORM_VERSION = 'offmenu-assistant-intermediate-to-source-recipe/1.0.0'
CACHE_VERSION = 'offmenu-assistant-extraction-cache/1'
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
        soup = BeautifulSoup(raw.decode(encoding, errors='strict'), 'html.parser')
    except (LookupError, UnicodeDecodeError) as exc:
        raise IntermediateError('source-decode-failed') from exc
    return raw, soup, soup.get_text('\n', strip=False)


def _section_nodes(soup: BeautifulSoup, label: str) -> list:
    body = soup.select_one('.field--name-body') or soup.body or soup
    header = next((h for h in body.find_all(['h2', 'h3', 'h4'])
                   if _norm(h.get_text(' ', strip=True)).casefold() == label.casefold()), None)
    if header is None:
        raise IntermediateError('source-section-missing:' + label.casefold())
    nodes, node = [], header
    while True:
        node = node.find_next_sibling()
        if node is None or node.name in {'h2', 'h3', 'h4'}:
            break
        nodes.append(node)
    return nodes


def source_segments(soup: BeautifulSoup) -> dict:
    ingredients = []
    for node in _section_nodes(soup, 'Ingredients'):
        if node.name in {'ul', 'ol'}:
            ingredients.extend(li.get_text(' ', strip=True) for li in node.find_all('li', recursive=False)
                               if li.get_text(' ', strip=True))
        elif node.name == 'p' and node.get_text(' ', strip=True):
            ingredients.append(node.get_text(' ', strip=True))
    directions, yields = [], []
    for node in _section_nodes(soup, 'Method'):
        if node.name != 'p' or not node.get_text(' ', strip=True):
            continue
        text = node.get_text(' ', strip=True)
        full_yield = re.fullmatch(r'(?i)((?:serves?|makes?)\s+\d+(?:\s*[-–]\s*\d+)?(?:\s+[^.]+)?)[.]?', text)
        if full_yield:
            yields.append(full_yield.group(1))
            continue
        trailing_yield = re.search(r'(?i)\s+((?:serves?|makes?)\s+\d+(?:\s*[-–]\s*\d+)?(?:\s+[^.]+)?)[.]?$', text)
        if trailing_yield:
            yields.append(trailing_yield.group(1))
            text = text[:trailing_yield.start()].rstrip()
        if text:
            directions.append(text)
    variations = []
    body = soup.select_one('.field--name-body') or soup.body or soup
    for h in body.find_all(['h2', 'h3', 'h4']):
        label = _norm(h.get_text(' ', strip=True))
        if label.casefold() not in {'variation', 'variations', 'hint', 'notes', 'serving suggestion'}:
            continue
        node = h.find_next_sibling()
        while node is not None and node.name not in {'h2', 'h3', 'h4'}:
            if node.name == 'p' and node.get_text(' ', strip=True):
                variations.append({'section': label, 'text': node.get_text(' ', strip=True)})
            node = node.find_next_sibling()
    return {'ingredientLines': ingredients, 'directionParagraphs': directions,
            'yields': yields, 'variations': variations}


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
        pattern = re.compile(r'\\s+'.join(re.escape(part) for part in quote.split()))
        match = pattern.search(text)
        if not match:
            raise IntermediateError('source-quote-not-locatable')
        start, actual = match.start(), match.group(0)
    return _loc(text, actual, start)


def _validate(response: dict, *, soup: BeautifulSoup, page_text: str,
              parsed_record: dict) -> None:
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
    segments = source_segments(soup)
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
        name = item.get('nameText')
        if not isinstance(name, str) or not name.strip() or _norm(name).casefold() not in _norm(quote).casefold():
            raise IntermediateError('ingredient-name-unsupported')
        for field in ('quantityText', 'unitText', 'preparationText', 'optionalText'):
            value = item.get(field)
            if value is not None and (not isinstance(value, str) or _norm(value).casefold() not in _norm(quote).casefold()):
                raise IntermediateError('ingredient-' + field.casefold() + '-unsupported')
        alternatives = item.get('alternatives', [])
        if (not isinstance(alternatives, list) or
                any(not isinstance(value, str) or not value.strip() or _norm(value).casefold() not in _norm(quote).casefold() for value in alternatives)):
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
        for name in ('actionTerms', 'equipment'):
            values = step.get(name, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() or _norm(v).casefold() not in _norm(quote).casefold() for v in values):
                raise IntermediateError('unsupported-' + name.casefold())
        for name in ('timeText', 'temperatureText', 'targetState'):
            value = step.get(name)
            if value is not None and (not isinstance(value, str) or _norm(value).casefold() not in _norm(quote).casefold()):
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


def _record(response: dict, parsed_record: dict, page_text: str) -> dict:
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
    result['source']['extractionParser'] = parser.PARSER_VERSION + '+' + TRANSFORM_VERSION
    parser._validate_record(result)
    return result


def _key_inputs(raw_sha: str, segments: dict, model_identity: str,
                model_version: str, settings: dict) -> dict:
    return {'originalSHA256': raw_sha,
        'sourceSegmentSHA256': _sha(_canonical(segments)),
        'extractionSchemaVersion': SCHEMA_VERSION, 'promptVersion': PROMPT_VERSION,
        'modelIdentity': model_identity, 'modelVersion': model_version,
        'inferenceSettings': settings, 'transformVersion': TRANSFORM_VERSION,
        'recipeSchemaVersion': parser.RECIPE_TEMPLATE_VERSION,
        'parserVersion': parser.PARSER_VERSION}


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
        inference_settings: dict | None = None) -> dict:
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
    segments = source_segments(soup)
    key_inputs = _key_inputs(raw_sha, segments, model_identity, model_version, settings)
    cache_key = _sha(_canonical(key_inputs))
    response_sha = _sha(response_text.encode('utf-8'))
    try:
        response = json.loads(response_text)
        if not isinstance(response, dict):
            raise IntermediateError('response-root-invalid')
        _validate(response, soup=soup, page_text=page_text, parsed_record=parsed_record)
        response = copy.deepcopy(response)
        response['_rawResponseSHA256'] = response_sha
        record = _record(response, parsed_record, page_text)
        cache = {'cacheSchemaVersion': CACHE_VERSION, 'cacheKey': cache_key,
            'baseParsedRecord': parsed_record,
            'cacheKeyInputs': key_inputs,
            'source': {'sourceId': source_id, 'sourceRecordId': source_record_id,
                'releaseId': source.get('release'), 'language': language,
                'countryCode': country, 'originalSHA256': raw_sha,
                'sourceURL': source.get('citationUrl') or source.get('sourceURL'),
                'permissionEvidence': source.get('assistantExtractionPermissionEvidence')},
            'model': {'identity': model_identity, 'version': model_version,
                      'settings': settings,
                      'execution': 'assistant-authored intermediate; no external API call'},
            'extractedUTC': datetime.now(timezone.utc).isoformat(),
            'rawResponse': response_text, 'rawResponseSHA256': response_sha,
            'validation': {'status': 'valid', 'outcome': 'schema-replay-accepted', 'uncertainty': response.get('uncertainty', [])},
            'transformVersion': TRANSFORM_VERSION, 'parsedRecord': record,
            'normalization': {'status': 'not-run', 'englishGoldAdmission': 'held'}}
        cache_path = cache_root / (cache_key + '.json')
        hit = cache_path.exists()
        if hit:
            prior = json.loads(cache_path.read_text(encoding='utf-8'))
            if (prior.get('cacheKey') != cache_key or prior.get('cacheKeyInputs') != key_inputs or
                    prior.get('validation', {}).get('status') != 'valid' or
                    _sha(prior.get('rawResponse', '').encode('utf-8')) != prior.get('rawResponseSHA256')):
                raise IntermediateError('existing-cache-incompatible')
            prior_response = json.loads(prior['rawResponse'])
            _validate(prior_response, soup=soup, page_text=page_text, parsed_record=parsed_record)
            prior_response = copy.deepcopy(prior_response)
            prior_response['_rawResponseSHA256'] = prior['rawResponseSHA256']
            record = _record(prior_response, parsed_record, page_text)
            if _canonical(record) != _canonical(prior.get('parsedRecord')):
                raise IntermediateError('existing-cache-replay-mismatch')
            response_sha = prior['rawResponseSHA256']
        else:
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
        source: dict, model_identity: str = 'unknown',
        model_version: str = 'unknown',
        inference_settings: dict | None = None) -> Path | None:
    """Look up an exact compatible validated response before invoking AI."""
    raw, soup, _ = _load_source(input_path, source.get('encoding', 'utf-8'))
    raw_sha = _sha(raw)
    if source.get('originalSHA256') and source['originalSHA256'] != raw_sha:
        return None
    segments = source_segments(soup)
    if not _assistant_permission_allowed(source):
        return None
    settings = inference_settings or {'temperature': None, 'seed': None,
        'max_tokens': None, 'runtime_parameters': 'not-exposed'}
    key = _sha(_canonical(_key_inputs(raw_sha, segments, model_identity, model_version, settings)))
    path = cache_root / (key + '.json')
    if not path.is_file() or path.is_symlink():
        return None
    cache = json.loads(path.read_text(encoding='utf-8'))
    if not _assistant_permission_allowed(source):
        return None
    if (cache.get('cacheKey') != key or cache.get('validation', {}).get('status') != 'valid' or
            cache.get('source', {}).get('permissionEvidence') != source.get('assistantExtractionPermissionEvidence') or
            _sha(cache.get('rawResponse', '').encode('utf-8')) != cache.get('rawResponseSHA256')):
        return None
    return path


def replay_cached_intermediate(*, cache_path: Path, input_path: Path,
        parsed_record: dict | None = None, output_root: Path) -> dict:
    """Deterministically replay a compatible valid cache; never re-infer."""
    cache = json.loads(cache_path.read_text(encoding='utf-8'))
    if cache.get('validation', {}).get('status') != 'valid':
        raise IntermediateError('cache-not-validated')
    ki = cache.get('cacheKeyInputs', {})
    if (ki.get('extractionSchemaVersion') != SCHEMA_VERSION or
            ki.get('promptVersion') != PROMPT_VERSION or
            ki.get('transformVersion') != TRANSFORM_VERSION or
            ki.get('recipeSchemaVersion') != parser.RECIPE_TEMPLATE_VERSION):
        raise IntermediateError('cache-contract-incompatible')
    if _sha(cache.get('rawResponse', '').encode('utf-8')) != cache.get('rawResponseSHA256'):
        raise IntermediateError('cached-response-checksum-invalid')
    raw, soup, page_text = _load_source(input_path)
    if _sha(raw) != ki.get('originalSHA256'):
        raise IntermediateError('cache-source-incompatible')

    segments = source_segments(soup)
    if _sha(_canonical(segments)) != ki.get('sourceSegmentSHA256'):
        raise IntermediateError('cache-segment-incompatible')
    response = json.loads(cache['rawResponse'])
    response['_rawResponseSHA256'] = cache['rawResponseSHA256']
    base_record = cache.get('baseParsedRecord')
    if parsed_record is not None and _canonical(parsed_record) != _canonical(base_record):
        raise IntermediateError('cache-base-record-mismatch')
    if not isinstance(base_record, dict):
        raise IntermediateError('cache-base-record-missing')
    _validate(response, soup=soup, page_text=page_text, parsed_record=base_record)
    record = _record(response, base_record, page_text)
    if _canonical(record) != _canonical(cache.get('parsedRecord')):
        raise IntermediateError('cache-replay-nondeterministic')
    path = output_root / 'assistant-assisted' / 'recipes' / cache['source']['sourceId'] / (cache['source']['sourceRecordId'] + '.json')
    _atomic(path, _canonical(record))
    return {'status': 'replayed', 'cacheKey': cache['cacheKey'],
            'rawResponseSHA256': cache['rawResponseSHA256'], 'recordPath': str(path),
            'acceptedRecords': 1}
