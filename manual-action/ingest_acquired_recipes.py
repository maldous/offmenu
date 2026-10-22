"""Offline adapters for the already-acquired Foodista, ForkRecipe and Medline files.

Only explicit ``acquired_adapter`` family selections are accepted. Original data
remains private/inert; no requests, source-code execution, archive extraction,
translation, food matching or acceptance/gold review is performed. Output uses
retained-recipe ingredient/step contracts and additive DomainStore checkpoints.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import PurePosixPath
import re
import tarfile
from urllib.parse import urlsplit

from ingest_api import BudgetExceeded, COUNTERS, SourceChanged, source_key
import ingest_recipes as retained

VERSION = 'offmenu-acquired-recipe-ingest/1'
ADAPTER_VERSION = VERSION
FAMILIES = frozenset(('foodista_common_pile', 'forkrecipe', 'medlineplus_healthy_recipes'))
DOMAINS = ('recipes', 'ingredients', 'citations')
MAX_RECORD = 2 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20000
# Bound structural amplification before constructing mention/step envelopes.
# A record exceeding these limits is quarantined whole, never truncated.
MAX_INGREDIENTS = 512
MAX_STEPS = 1024
MAX_PROCESS_NODES = 512
MAX_PROJECTION_BYTES = 4 * 1024 * 1024
TOAST_PATH = '/spanish/recetas/tostada-francesa-con-pure-de-manzana/'
REASONS = frozenset('''acquired_recipe_source_error acquired_recipe_ingredient_count_cap
    acquired_recipe_step_count_cap acquired_recipe_process_node_cap acquired_recipe_projection_size_cap
    acquisition_receipt_not_verified archive_member_count_cap archive_notice_size_cap
    archive_recipe_size_cap duplicate_archive_member_name duplicate_archive_notice
    expanded_byte_cap invalid_expansion_limit unsafe_archive_member unselected_acquired_adapter
    foodista_record_shape foodista_record_size_cap foodista_repeated_section
    foodista_sections_ambiguous foodista_step_number_sequence foodista_text_missing
    foodista_title_missing foodista_empty_or_ambiguous_sections forkrecipe_ingredient_shape
    forkrecipe_instruction_shape forkrecipe_missing_full_recipe_fields forkrecipe_process_node_shape
    html_structure_cap medline_headingless_ingredients_ambiguous medline_html_size_cap
    medline_ingredient_heading_missing medline_recipe_body_missing
    medline_recipe_sections_ambiguous medline_title_ambiguous
    javascript_depth_cap javascript_duplicate_key javascript_input_not_text
    javascript_invalid_binding javascript_invalid_parser_limit javascript_invalid_unicode
    javascript_invalid_unicode_escape javascript_legacy_octal_escape javascript_nonfinite_number
    javascript_nonliteral_value javascript_numeric_limit javascript_object_key_not_literal
    javascript_prototype_key javascript_recipe_root_not_object javascript_size_cap
    javascript_string_linebreak javascript_template_interpolation javascript_token_cap
    javascript_unpaired_surrogate javascript_unsupported_escape javascript_unsupported_export
    javascript_unsupported_structure javascript_unsupported_token javascript_unterminated_comment
    javascript_unterminated_string duplicate_json_key nonfinite_json invalid_json invalid_unicode
    archive_invalid compressed_source_invalid source_changed_during_read recipe_title_missing
    recipe_field_type ingredient_not_text_or_object instruction_depth_cap instruction_not_text
    wrong_acquired_recipe_domain'''.split())


class MalformedAcquiredRecipe(ValueError):
    """A data record is ambiguous/unsupported; never execute it to recover."""


class _SkipRecord(Exception):
    pass


def _stats():
    return dict(errors=0, skipped=0, documents_examined=0, non_recipe_documents=0,
                quarantined_records=0, projected_recipes=0, ingredient_mentions=0,
                citations=0, duplicate_records=0, archive_members=0,
                archive_non_recipe_members=0, template_members=0, reason_counts={})


def _note_reason(stats, exc):
    reason = exc.args[0] if len(exc.args) == 1 and isinstance(exc.args[0], str) else None
    if isinstance(exc, json.JSONDecodeError):
        reason = 'invalid_json'
    elif isinstance(exc, UnicodeError):
        reason = 'invalid_unicode'
    elif isinstance(exc, tarfile.TarError):
        reason = 'archive_invalid'
    elif isinstance(exc, EOFError):
        reason = 'compressed_source_invalid'
    if reason not in REASONS:
        reason = 'acquired_recipe_source_error'
    counts = stats['reason_counts']
    counts[reason] = counts.get(reason, 0) + 1


def _error(source, context, stats, exc):
    stats['errors'] += 1
    stats['quarantined_records'] += 1
    _note_reason(stats, exc)
    context.report_error(source, exc)


def _bounded_projection(value):
    """Measure incrementally; never allocate an oversized serialized envelope."""
    size = 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode('utf-8'))
        if size > MAX_PROJECTION_BYTES:
            raise MalformedAcquiredRecipe('acquired_recipe_projection_size_cap')


def _meta(source):
    return (source.get('metadata') or {}).get('acquisition') or {}


def _url(source):
    meta = _meta(source)
    return source.get('source_url') or meta.get('origin_url') or meta.get('url')


def _rights(source, document=None):
    """Snapshot/row terms never get overwritten by current website terms."""
    row = document or {}
    meta = row.get('metadata') if isinstance(row.get('metadata'), dict) else {}
    acquisition = _meta(source)
    return {'source_license': meta.get('license', row.get('license')),
            'catalog_license': source.get('license'),
            'license_evidence': acquisition.get('license_evidence', source.get('license_evidence')),
            'catalog_attribution': acquisition.get('attribution', source.get('attribution')),
            'authors': meta.get('authors', row.get('author')),
            'scope_note': acquisition.get('license_scope_note', source.get('license_scope_note')),
            'transformation': 'source-specific structural extraction; no translation or semantic normalization',
            'images_cleared': False}


class _LimitedReader:
    """Cap actual decompressed bytes, including tar headers and skipped members."""
    def __init__(self, stream, limit, check):
        self.stream, self.limit, self.check, self.count = stream, limit, check, 0
    def read(self, size=-1):
        self.check()
        if size < 0:
            size = self.limit - self.count + 1
        data = self.stream.read(min(size, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise MalformedAcquiredRecipe('expanded_byte_cap')
        return data
    def readline(self, size=-1):
        self.check()
        if size < 0:
            size = self.limit - self.count + 1
        data = self.stream.readline(min(size, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise MalformedAcquiredRecipe('expanded_byte_cap')
        return data


@contextmanager
def _input(source, context, compressed=False):
    # Reuse reviewed component-wise O_NOFOLLOW open; never follow a raw-cache link.
    spec = dict(source)
    if compressed:
        spec['compression'] = 'gzip'
    raw, stream, before = retained._open(spec)
    limit = min(MAX_EXPANDED, int(source.get('max_expanded_bytes') or MAX_EXPANDED))
    if limit <= 0:
        stream.close()
        raw.close()
        raise MalformedAcquiredRecipe('invalid_expansion_limit')
    try:
        reader = _LimitedReader(stream, limit, context.check_budget)
        yield reader
        if retained._identity(before) != retained._identity(os.fstat(raw.fileno())):
            raise SourceChanged('source_changed_during_read')
    finally:
        if stream is not raw:
            stream.close()
        raw.close()


def _foodista_sections(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get('metadata'), dict):
        raise MalformedAcquiredRecipe('foodista_record_shape')
    url = obj['metadata'].get('url')
    parts = urlsplit(url) if isinstance(url, str) else None
    if not parts or parts.hostname not in ('foodista.com', 'www.foodista.com') or not parts.path.startswith('/recipe/'):
        raise _SkipRecord('non_recipe_document')
    body = obj.get('text')
    if not isinstance(body, str) or not body.strip():
        raise MalformedAcquiredRecipe('foodista_text_missing')
    # Collector emits explicit pane headings, then separately appends Comments:.
    # Never use comments or prose from tools/about panels as directions.
    pattern = r'(?im)^[ \t]*(Ingredients|Preparation|Directions|Instructions|Tools|About|Information|Notes|Variations|Comments|Answers)[ \t]*:?[ \t]*$'
    headings = list(re.finditer(pattern, body))
    sections = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).casefold()
        if name in ('comments', 'answers'):
            break
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        if name in sections:
            raise MalformedAcquiredRecipe('foodista_repeated_section')
        sections[name] = body[heading.end():end].strip('\r\n')
    method_keys = [key for key in ('preparation', 'directions', 'instructions') if key in sections]
    if 'ingredients' not in sections or len(method_keys) != 1:
        raise MalformedAcquiredRecipe('foodista_sections_ambiguous')
    ingredient_text, method_text = sections['ingredients'], sections[method_keys[0]]
    ingredients = [line.strip() for line in ingredient_text.splitlines() if line.strip()]
    steps = [line.strip() for line in method_text.splitlines() if line.strip()]
    if len(ingredients) > MAX_INGREDIENTS:
        raise MalformedAcquiredRecipe('acquired_recipe_ingredient_count_cap')
    # Standalone numbers consume at most one extra line per procedural unit.
    if len(steps) > 2 * MAX_STEPS:
        raise MalformedAcquiredRecipe('acquired_recipe_step_count_cap')
    # Flattened numbered steps must have explicit, ordered standalone delimiters.
    # Do not invent ingredient boundaries from commas or digit/word guesses.
    if steps and all(re.fullmatch(r'\d+', line) for line in steps[::2]) and len(steps) % 2 == 0:
        numbers = [int(n) for n in steps[::2]]
        if numbers != list(range(1, len(numbers) + 1)):
            raise MalformedAcquiredRecipe('foodista_step_number_sequence')
        steps = [steps[i] + ' ' + steps[i + 1] for i in range(0, len(steps), 2)]
    if len(steps) > MAX_STEPS:
        raise MalformedAcquiredRecipe('acquired_recipe_step_count_cap')
    if not ingredients or not steps or any(re.fullmatch(r'\d+', s) for s in steps):
        raise MalformedAcquiredRecipe('foodista_empty_or_ambiguous_sections')
    prefix = body[:headings[0].start()].strip().splitlines() if headings else []
    title = next((line.strip() for line in prefix if line.strip()), None)
    if not title or title.startswith(('By:', 'Published:')):
        raise MalformedAcquiredRecipe('foodista_title_missing')
    quality = []
    for key in ('created', 'added'):
        value = obj.get(key)
        try:
            if not isinstance(value, str):
                raise ValueError()
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            quality.append('unparseable_or_missing_' + key + '_date')
    return {'title': title, 'url': url, 'language': 'en', 'ingredients': ingredients,
            'instructions': steps, 'source_sections': sections,
            'source_dates': {key: obj.get(key) for key in ('created', 'added')},
            'review_flags': quality, 'date_values_transformed': False,
            'published_author_text': next((line[3:].strip() for line in prefix if line.startswith('By:')), None)}


def _foodista_rows(source, context, stats):
    with _input(source, context, compressed=True) as stream:
        number = 0
        while True:
            line = stream.readline(MAX_RECORD + 1)
            if not line:
                break
            number += 1
            if not line.strip():
                continue
            stats['documents_examined'] += 1
            if len(line) > MAX_RECORD:
                while line and not line.endswith(b'\n'):
                    line = stream.readline(MAX_RECORD + 1)
                _error(source, context, stats, MalformedAcquiredRecipe('foodista_record_size_cap'))
                continue
            try:
                raw = line.decode('utf-8-sig')
                original = retained._strict(raw)
                selected = _foodista_sections(original)
                yield selected, original, '/line/' + str(number), raw, {}
            except _SkipRecord:
                stats['non_recipe_documents'] += 1
                stats['skipped'] += 1
            except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
                _error(source, context, stats, exc)


def _safe_member(member):
    # No extraction at all; reject dangerous names nevertheless for custody/IDs.
    name = member.name
    path = PurePosixPath(name)
    return (not path.is_absolute() and '..' not in path.parts and '\\' not in name
            and '\x00' not in name and not re.match(r'^[A-Za-z]:', name)
            and len(path.parts) <= 8 and len(name) <= 1024
            and (member.isfile() or member.isdir()) and not member.issparse())


def _archive(source, context):
    with _input(source, context, compressed=True) as stream:
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for index, member in enumerate(archive):
                context.check_budget()
                if index >= MAX_ARCHIVE_MEMBERS:
                    raise MalformedAcquiredRecipe('archive_member_count_cap')
                yield archive, member
            # Validate gzip footer/CRC and expansion cap beyond tar end markers.
            while stream.read(65536):
                pass


def _forkrecipe_rows(source, context, stats):
    from acquired_recipe_js import parse_recipe_javascript
    # Tiny source notices are collected in a bounded first streaming pass so
    # archive ordering cannot drop contributor/license evidence. Never run users.js.
    notices = {}
    total_notice_bytes = 0
    for archive, member in _archive(source, context):
        if not _safe_member(member) or not member.isfile():
            continue
        relative = '/'.join(PurePosixPath(member.name).parts[1:])
        if relative not in ('LICENSE', 'NOTICE', 'README.md', 'data/users.js'):
            continue
        try:
            if relative in notices:
                raise MalformedAcquiredRecipe('duplicate_archive_notice')
            if member.size > MAX_RECORD or total_notice_bytes + member.size > 4 * MAX_RECORD:
                raise MalformedAcquiredRecipe('archive_notice_size_cap')
            data = archive.extractfile(member).read(MAX_RECORD + 1)
            total_notice_bytes += len(data)
            notices[relative] = {'sha256': hashlib.sha256(data).hexdigest(),
                                 'source_text': data.decode('utf-8-sig')}
        except (ValueError, UnicodeError) as exc:
            _error(source, context, stats, exc)
    seen_members = set()
    for archive, member in _archive(source, context):
        stats['archive_members'] += 1
        if not _safe_member(member):
            _error(source, context, stats, MalformedAcquiredRecipe('unsafe_archive_member'))
            continue
        parts = PurePosixPath(member.name).parts
        if not member.isfile() or len(parts) != 3 or parts[1] != 'recipes' or not parts[2].endswith('.js'):
            stats['archive_non_recipe_members'] += 1
            continue
        if parts[2].startswith('_'):
            stats['template_members'] += 1
            stats['skipped'] += 1
            continue
        stats['documents_examined'] += 1
        if member.name in seen_members:
            _error(source, context, stats, MalformedAcquiredRecipe('duplicate_archive_member_name'))
            continue
        seen_members.add(member.name)
        try:
            if member.size > MAX_RECORD:
                raise MalformedAcquiredRecipe('archive_recipe_size_cap')
            raw = archive.extractfile(member).read(MAX_RECORD + 1).decode('utf-8-sig')
            original = parse_recipe_javascript(raw)
            ingredients = original.get('ingredients')
            nodes = original.get('processNodes')
            if not isinstance(ingredients, list) or not ingredients or not isinstance(nodes, list) or not nodes:
                raise MalformedAcquiredRecipe('forkrecipe_missing_full_recipe_fields')
            if len(ingredients) > MAX_INGREDIENTS:
                raise MalformedAcquiredRecipe('acquired_recipe_ingredient_count_cap')
            if len(nodes) > MAX_PROCESS_NODES:
                raise MalformedAcquiredRecipe('acquired_recipe_process_node_cap')
            if any(not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name'].strip() for row in ingredients):
                raise MalformedAcquiredRecipe('forkrecipe_ingredient_shape')
            steps = []
            step_count = 0
            for node in nodes:
                if not isinstance(node, dict):
                    raise MalformedAcquiredRecipe('forkrecipe_process_node_shape')
                instructions = node.get('instructions')
                if isinstance(instructions, str) and instructions.strip():
                    instructions = [instructions]
                if not isinstance(instructions, list) or not instructions or any(not isinstance(s, str) or not s.strip() for s in instructions):
                    raise MalformedAcquiredRecipe('forkrecipe_instruction_shape')
                step_count += len(instructions)
                if step_count > MAX_STEPS:
                    raise MalformedAcquiredRecipe('acquired_recipe_step_count_cap')
                steps.append({'name': node.get('title', node.get('name', node.get('action'))), 'itemListElement': instructions,
                              'source_process_node': node})
            selected = {'title': original.get('title'), 'ingredients': ingredients,
                        'instructions': steps, 'language': original.get('language') or 'en',
                        'slug': original.get('slug'), 'repoId': original.get('repoId'),
                        'parentRepoId': original.get('parentRepoId'),
                        'source_ingredient_quantity_kind': 'ratioValue/defaultUnit assertions; no mass or yield inference'}
            url = original.get('url')
            if not isinstance(url, str):
                revision = source.get('source_revision') or _meta(source).get('revision')
                url = 'https://github.com/futurechef/forkrecipe-recipes/blob/' + str(revision or 'unresolved-revision') + '/recipes/' + parts[2]
            selected['url'] = url
            yield selected, original, '/archive/' + member.name, raw, {'archive_notices': notices, 'archive_member': member.name}
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
            _error(source, context, stats, exc)


class _Node:
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs or []), parent, []
    def _text(self):
        if self.tag in ('script', 'style', 'noscript', 'svg') or 'hidden' in self.attrs or self.attrs.get('aria-hidden') == 'true':
            return ''
        if self.tag == 'br':
            return ' '
        return ''.join(child if isinstance(child, str) else child._text() for child in self.children)
    def text(self):
        return re.sub(r'\s+', ' ', self._text()).strip()


class _DOM(HTMLParser):
    VOID = frozenset(('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'))
    OMIT = frozenset(('script', 'style', 'nav', 'footer', 'aside', 'noscript', 'svg', 'form'))
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]
        self.nodes = []
    def handle_starttag(self, tag, attrs):
        if len(self.nodes) >= 100000 or len(self.stack) >= 128:
            raise MalformedAcquiredRecipe('html_structure_cap')
        # Handle optional list/paragraph end tags conservatively.
        if tag == 'li' and self.stack[-1].tag == 'li':
            self.stack.pop()
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for n in range(len(self.stack) - 1, 0, -1):
            if self.stack[n].tag == tag:
                del self.stack[n:]
                break
    def handle_data(self, data):
        self.stack[-1].children.append(data)
    def visible(self, node):
        while node is not None:
            if node.tag in self.OMIT or 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true':
                return False
            node = node.parent
        return True


def _ancestor(node, tag):
    node = node.parent
    while node:
        if node.tag == tag:
            return node
        node = node.parent
    return None


def _label(node):
    return node.text().strip().rstrip(':').strip().casefold()


def _is_heading(node):
    return node.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')


def _medline_html(body, source):
    parser = _DOM()
    parser.feed(body)
    parser.close()
    nodes = [node for node in parser.nodes if parser.visible(node)]
    titles = [node for node in nodes if node.tag == 'h1' and node.text()]
    if len(titles) != 1:
        raise MalformedAcquiredRecipe('medline_title_ambiguous')
    title = titles[0]
    nodes = nodes[nodes.index(title) + 1:]
    ih = [i for i, node in enumerate(nodes) if _is_heading(node) and _label(node) in ('ingredients', 'ingredientes')]
    dh = [i for i, node in enumerate(nodes) if _is_heading(node) and _label(node) in ('directions', 'instructions', 'preparación', 'direcciones')]
    if len(dh) != 1 or len(ih) > 1 or ih and ih[0] >= dh[0]:
        raise MalformedAcquiredRecipe('medline_recipe_sections_ambiguous')
    url = _url(source)
    if not ih:
        if not isinstance(url, str) or urlsplit(url).path != TOAST_PATH:
            raise MalformedAcquiredRecipe('medline_ingredient_heading_missing')
        lists = [node for node in nodes[:dh[0]] if node.tag == 'ul' and _ancestor(node, 'ul') is None]
        if len(lists) != 1:
            raise MalformedAcquiredRecipe('medline_headingless_ingredients_ambiguous')
        ingredient_nodes = [node for node in nodes[:dh[0]] if _ancestor(node, 'ul') is lists[0] or node is lists[0]]
    else:
        ingredient_nodes = nodes[ih[0] + 1:dh[0]]
    ingredients, groups, group = [], [], None
    for node in ingredient_nodes:
        if node.tag == 'li' and _ancestor(node, 'li') is None and _ancestor(node, 'ul') is not None:
            text = node.text()
            if text:
                ingredients.append({'originalExpression': text, 'source_section': group})
                if len(ingredients) > MAX_INGREDIENTS:
                    raise MalformedAcquiredRecipe('acquired_recipe_ingredient_count_cap')
        elif (_is_heading(node) or node.tag in ('p', 'strong', 'b')) and _ancestor(node, 'li') is None and node.text():
            label = node.text()
            if label != group:
                group = label
                groups.append(label)
    # Ordered list items are procedural units; notes/bullets are never steps.
    directions = []
    for node in nodes[dh[0] + 1:]:
        if _is_heading(node) or node.tag in ('p', 'strong', 'b') and _label(node) in ('notes', 'notas'):
            break
        if node.tag == 'li' and _ancestor(node, 'li') is None and _ancestor(node, 'ol') is not None and node.text():
            directions.append(node.text())
            if len(directions) > MAX_STEPS:
                raise MalformedAcquiredRecipe('acquired_recipe_step_count_cap')
    if not ingredients or not directions:
        raise MalformedAcquiredRecipe('medline_recipe_body_missing')
    language = source.get('language') or ('es' if isinstance(url, str) and '/spanish/' in url else 'en')
    # Only source-asserted time/yield text; no arithmetic, nutrient calculations,
    # or identification of counterpart variants as equivalent recipe objects.
    assertions = []
    for node in nodes:
        if node.tag in ('p', 'div', 'span', 'dt', 'dd') and not any(isinstance(c, _Node) and c.tag in ('p', 'div') for c in node.children):
            text = node.text()
            if re.match(r'^(Prep time|Cook time|Total time|Servings|Yield|Tiempo de preparación|Tiempo de cocción|Tiempo total|Porciones)\s*:', text, re.I):
                if text not in assertions:
                    assertions.append(text)
    credits = []
    for node in nodes:
        text = node.text() if node.tag in ('p', 'a') else ''
        if any(term in text.casefold() for term in ('foodhero', 'national heart, lung', 'nhlbi', 'instituto nacional del corazón')):
            item = {'text': text, 'url': node.attrs.get('href')}
            if item not in credits:
                credits.append(item)
    counterpart = source.get('counterpart_url') or _meta(source).get('counterpart_url')
    observed_counterparts = [node.attrs.get('href') for node in parser.nodes if node.tag == 'a' and node.attrs.get('href') == counterpart] if counterpart else []
    return {'title': title.text(), 'url': url, 'language': language,
            'ingredients': ingredients, 'instructions': directions,
            'ingredient_groups': groups, 'source_time_yield_assertions': assertions,
            'source_credits': credits,
            'variant_work_id_assertion': source.get('work_id') or _meta(source).get('work_id'),
            'counterpart_url_assertion': counterpart,
            'counterpart_link_observed': bool(observed_counterparts),
            'counterpart_equivalence_established': False,
            'review_flags': ['language_variant_not_independently_translation_reviewed'] +
                (['publisher_variant_quantity_mismatch_requires_review'] if 'waffles' in str(url) else [])}


def _medline_rows(source, context, stats):
    stats['documents_examined'] += 1
    with _input(source, context) as stream:
        raw = stream.read(MAX_RECORD + 1)
        if len(raw) > MAX_RECORD:
            raise MalformedAcquiredRecipe('medline_html_size_cap')
        body = raw.decode('utf-8-sig')
        selected = _medline_html(body, source)
        yield selected, {'source_document_html': body}, '/html', None, {}


def _project(selected, original, pointer, native, metadata, source):
    family = source['acquired_adapter']
    evidence = {'acquisition': _meta(source), **metadata, 'rights': _rights(source, original)}
    envelope = {'url': selected.get('url'), 'recipe': selected, 'source_payload': original}
    if family == 'forkrecipe':
        envelope['source_javascript'] = native  # inert original, never interpreted here
    # Identity hashing serializes this envelope, so bound it BEFORE the shared
    # retained projector constructs IDs or expanded mention dictionaries.
    _bounded_projection(envelope)
    _bounded_projection(evidence)
    record, mentions = retained._recipe(envelope, source, pointer, None, evidence)
    record['raw_source_json'] = native if family == 'foodista_common_pile' else None
    provenance = record['provenance']
    provenance['adapter_version'] = VERSION
    provenance['source_url'] = selected.get('url')
    provenance['rights'] = evidence['rights']
    record.update(acquired_source_family=family, qualification_status='unreviewed',
                  automaticPlanningEligible=False, gold_review_performed=False,
                  ingest_acceptance='source-faithful-staging-not-gold',
                  review_flags=selected.get('review_flags', []))
    record['source_ingredient_groups'] = selected.get('ingredient_groups')
    if family == 'forkrecipe':
        record['source_relationship_assertions'] = {
            'repoId': original.get('repoId'), 'parentRepoId': original.get('parentRepoId'),
            'resolution_status': 'source-native-fork-reference-not-canonical-identity'}
    for mention, value in zip(mentions, selected['ingredients']):
        if isinstance(value, dict):
            mention['source_section'] = value.get('source_section')
            if family == 'forkrecipe':
                mention['source_ratio_value'] = value.get('ratioValue')
                mention['source_default_unit'] = value.get('defaultUnit')
                mention['quantity_interpretation'] = 'source_ratio_not_mass_or_serving_quantity'
    citation_id = 'recipe-citation:' + retained._hash(record['id'])
    # Keep complete notices/rights/author arrays ONCE on recipe provenance.
    # Repeating that context inside every mention amplifies tiny source lists
    # into unbounded JSON; exact recipe/citation/hash references preserve lineage.
    mention_provenance = {key: provenance.get(key) for key in
        ('source_id', 'catalog_source_id', 'path', 'pointer', 'provider', 'adapter_version')}
    mention_provenance.update(recipe_id=record['id'], citation_id=citation_id,
        recipe_provenance_sha256=retained._hash(provenance),
        context_location='exact_recipe_provenance_and_citation_not_duplicated')
    record['relations'].append({'kind': 'cites', 'target_domain': 'citations', 'target_id': citation_id})
    for mention in mentions:
        mention['provenance'] = mention_provenance
        mention['relations'].append({'kind': 'cites', 'target_domain': 'citations', 'target_id': citation_id})
    citation = {'id': citation_id, 'kind': 'source_citation', 'record_type': 'source_citation',
                'recipe_id': record['id'], 'source_key': source_key(source),
                'reference': {'title': record['title'], 'url': selected.get('url'),
                              'language': record['language'], 'source_id': original.get('id'),
                              'license': evidence['rights']['source_license'],
                              'authors': evidence['rights']['authors'],
                              'published_author_text': selected.get('published_author_text'),
                              'created': original.get('created'), 'added': original.get('added'),
                              'source_sha256': hashlib.sha256((native or retained._json(original)).encode()).hexdigest()},
                'parent_reference': {'acquisition': _meta(source), 'rights': evidence['rights'],
                                     'archive_notice_sha256': {k: v['sha256'] for k, v in metadata.get('archive_notices', {}).items()}},
                'relations': [{'kind': 'cites_record', 'target_domain': 'recipes', 'target_id': record['id']}]}
    # Apply the same whole-recipe admission decision in all domain streams.
    # Each mention is already embedded in record, so no second body copy is
    # needed here. Citation metadata has an independent envelope bound.
    _bounded_projection(record)
    _bounded_projection(citation)
    return record, mentions, citation


def _iter_records(domain, source, context, stats):
    stats = stats if stats is not None else _stats()
    family = source.get('acquired_adapter')
    if _meta(source).get('verified') is not True:
        raise MalformedAcquiredRecipe('acquisition_receipt_not_verified')
    reader = {'foodista_common_pile': _foodista_rows, 'forkrecipe': _forkrecipe_rows,
              'medlineplus_healthy_recipes': _medline_rows}.get(family)
    if reader is None:
        raise MalformedAcquiredRecipe('unselected_acquired_adapter')
    seen = set()
    dedup_limit = max(1, min(100000, int(context.config.get('dedup_cache_entries', 100000))))
    for selected, original, pointer, native, metadata in reader(source, context, stats):
        context.check_budget()
        try:
            recipe, mentions, citation = _project(selected, original, pointer, native, metadata, source)
            if recipe['id'] in seen:
                stats['duplicate_records'] += 1
                stats['skipped'] += 1
                continue
            if len(seen) >= dedup_limit:
                seen.clear()
            seen.add(recipe['id'])
            if domain == 'recipes':
                stats['projected_recipes'] += 1
                yield recipe
            elif domain == 'ingredients':
                for mention in mentions:
                    stats['ingredient_mentions'] += 1
                    yield mention
            elif domain == 'citations':
                stats['citations'] += 1
                yield citation
            else:
                raise ValueError('wrong_acquired_recipe_domain')
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
            _error(source, context, stats, exc)


def iter_records(domain, source, context, stats=None):
    stats = stats if stats is not None else _stats()
    try:
        yield from _iter_records(domain, source, context, stats)
    except BudgetExceeded:
        raise
    except Exception as exc:
        # Store owns durable stream-error accounting. Preserve the sanitized
        # current-attempt reason without reporting/counting that error twice.
        _note_reason(stats, exc)
        raise


def run_domain(domain, sources, context):
    if domain not in DOMAINS:
        raise ValueError('wrong_acquired_recipe_domain')
    totals, summaries = dict.fromkeys(COUNTERS, 0), []
    holds = ('restricted', 'skip', 'existing-loaded', 'existing-store', 'already_loaded', 'unsupported',
             'metadata-only', 'incomplete-hold', 'duplicate', 'excluded', 'missing', 'unreadable', 'rights-hold', 'adapter-required')
    for original_source in sources:
        source = dict(original_source, adapter_version=VERSION)
        stats = _stats()
        if source.get('restricted') or source.get('loaded') or source.get('disposition') in holds:
            summary = dict(source_key=source_key(source), status='skipped', reason='catalog_skip',
                           read=0, written=0, unchanged=0, errors=0, skipped=1)
        else:
            try:
                context.check_budget()
                summary = context.ingest(source, iter_records(domain, source, context, stats))
            except BudgetExceeded:
                summaries.append(dict(source_key=source_key(source), status='partial', reason='resource_cap'))
                break
            except Exception as exc:
                context.report_error(source, exc)
                summary = dict(source_key=source_key(source), status='failed', read=0, written=0,
                               unchanged=0, errors=1, skipped=0, error_class=type(exc).__name__)
        summary['errors'] = max(summary.get('errors', 0), stats['errors'])
        summary['skipped'] = summary.get('skipped', 0) + stats['skipped']
        summary['record_kinds'] = {key: value for key, value in stats.items() if key not in ('errors', 'skipped', 'reason_counts')}
        summary['diagnostics'] = {'reason_counts': stats['reason_counts'],
            'reason_scope': 'current_attempt_adapter_observations_not_historical'}
        summary['counts_meaning'] = 'source_projections_not_unique_accepted_recipes'
        summary['actual_source_record_review'] = 'pending'
        if summary['errors'] and summary['status'] == 'complete':
            summary['status'] = 'partial'
        summaries.append(summary)
        for key in COUNTERS:
            totals[key] += summary.get(key, 0)
    return dict(domain=domain, adapter_version=VERSION,
                status='partial' if any(s['status'] in ('partial', 'failed') for s in summaries) else 'complete',
                sources=summaries, **totals)
