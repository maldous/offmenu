"""Deterministic cached-label sections; no identity, safety or runtime AI claims."""
import hashlib
import re

from .core import RefreshError

VERSION = 'offmenu-source-label-sections/1'
COMPONENT_VERSION = 'offmenu-source-ingredient-components/1'
_END_BOUNDARY = r'[.!?](?=\s|$)|(?=[\r\n]|$)'
_END = r'.*?(?:' + _END_BOUNDARY + r')'
_LINE_PREFIX = r'[^.!?\r\n]*'
_BATCH = r'(?-i:[0-9][A-Z0-9]{7,})'
_RULES = (
    ('allergen_statement', r'\b(?:MAY CONTAIN|CONTAINS)\b' + _END),
    ('storage', r'\b(?:Keep refrigerated|Keep frozen|Store\s+(?:below|at|in|away from))\b' + _END),
    ('origin_claim', r'\bMade in\s+.+?\s+from\s+at least\s+\d+(?:[.,]\d+)?%\s+.+?\s+ingredients\b'),
    ('company_address', r'\b' + _LINE_PREFIX + r'\bregistered trademark\b' + _END),
    ('company_address', r"\b[A-Z][A-Z &'\-]{2,40},\s*\d{1,5}\s+" + _LINE_PREFIX + r'?\b\d{4,6}\b(?:\s+www\.[A-Za-z0-9.\-]+\.[A-Za-z]{2,})?'),
    ('recycling', r'\b(?:Tub|Lid|Insert|Bottle|Jar|Sleeve|Box|Cap)(?:\s+(?:Tub|Lid|Insert|Bottle|Jar|Sleeve|Box|Cap))*(?:\s+\d{4,32})?\s+[a-z0-9.\-]+\.(?:org|com)(?:\.[a-z]{2})?\b'),
    ('marketing', r'\bContributes to\b' + _END),
    ('marketing', r'\b' + _LINE_PREFIX + r'\b(?:guarantees|quality specifications|full refund|replacement)\b' + _END),
    ('marketing', r'\b(?:No Artificial|Source of|Suitable for)\b.*?(?:' + _END_BOUNDARY + r'|(?=\s+(?:No Artificial|Source of|Suitable for)\b|\s+' + _BATCH + r'\b))'),
)


def extract_label_sections(text, *, max_text_bytes=262144, max_sections=1000):
    """Preserve all text and offsets; marker-based sections remain source claims.

    An unlabelled opening ingredient-like span before an explicit allergen marker
    is only a candidate. All gaps/uncertain material, including batch identifiers,
    remain unclassified. Character offsets are Unicode code points, not JS UTF16.
    """
    if (type(text) is not str or type(max_text_bytes) is not int or not 0 < max_text_bytes <= 1048576
            or type(max_sections) is not int or not 0 < max_sections <= 10000
            or len(text.encode('utf-8')) > max_text_bytes):
        raise RefreshError('label-sections-input-bound')
    selected = []
    def add(start, end, category, evidence):
        while start < end and text[start].isspace(): start += 1
        while end > start and text[end - 1].isspace(): end -= 1
        if start == end or any(start < b and a < end for a, b, *_ in selected): return
        if len(selected) >= max_sections: raise RefreshError('label-sections-count-bound')
        selected.append((start, end, category, evidence))
    for category, pattern in _RULES:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            add(match.start(), match.end(), category, 'explicit-source-marker; assertion unverified')
    allergens = sorted(a for a, _, category, _ in selected if category == 'allergen_statement')
    line_end = re.search(r'[\r\n]', text)
    opening_end = min(line_end.start() if line_end else len(text), min((a for a, *_ in selected), default=len(text)))
    if allergens and opening_end > 0 and ',' in text[:opening_end]:
        add(0, opening_end, 'ingredient_list', 'candidate opening span before explicit allergen marker; no ingredient identity inference')
    elif re.match(r'^\s*ingredients\s*:', text, flags=re.IGNORECASE):
        add(0, opening_end, 'ingredient_list', 'explicit source Ingredients header')
    spans = []; cursor = 0
    def emit(start, end, category, evidence):
        if len(spans) >= max_sections: raise RefreshError('label-sections-count-bound')
        value = text[start:end]
        spans.append({'category': category, 'text': value, 'start': start, 'end': end,
                      'utf8Start': len(text[:start].encode('utf-8')), 'utf8End': len(text[:end].encode('utf-8')),
                      'textSHA256': hashlib.sha256(value.encode('utf-8')).hexdigest(), 'evidence': evidence})
    for start, end, category, evidence in sorted(selected):
        if cursor < start: emit(cursor, start, 'unclassified', 'retained gap; no interpretation')
        emit(start, end, category, evidence); cursor = end
    if cursor < len(text): emit(cursor, len(text), 'unclassified', 'retained uncertain/source-code span')
    return {'extractionVersion': VERSION, 'rawText': text,
            'rawTextSHA256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'offsetUnit': 'Unicode code point; end exclusive; UTF8 byte offsets also supplied',
            'sections': spans, 'canonicalMapping': None, 'certification': None,
            'assurance': 'source label-section extraction only; not source factual truth, allergen safety or dietary suitability'}


def extract_ingredient_components(text, *, start, end, max_nodes=1000, max_depth=20):
    """Source-only comma/bracket tree with explicit quantity lexemes, no concepts.

    Caller selects an evidenced/candidate ingredient span. Delimiters establish
    syntactic grouping only. Bare additive numbers are not quantities; unknown
    percentage bases, qualifiers and malformed groups remain explicit.
    """
    if (type(text) is not str or len(text.encode()) > 262144 or type(start) is not int or type(end) is not int
            or not 0 <= start <= end <= len(text) or type(max_nodes) is not int or not 0 < max_nodes <= 10000
            or type(max_depth) is not int or not 0 < max_depth <= 50): raise RefreshError('ingredient-components-input-bound')
    digest = hashlib.sha256(text.encode()).hexdigest(); count = [0]
    quantity = re.compile(r'(?<![\w/])(?P<value>\d+(?:[.,]\d+)?(?:\s*[-–—]\s*\d+(?:[.,]\d+)?)?|[¼½¾⅓⅔⅛⅜⅝⅞])\s*(?P<unit>%|kg|mg|g|ml|l|oz|lb|tsp|tbsp|cups?|teaspoons?|tablespoons?)(?!\w)', re.IGNORECASE)
    def span(a, b):
        return {'text': text[a:b], 'start': a, 'end': b,
                'utf8Start': len(text[:a].encode()), 'utf8End': len(text[:b].encode()),
                'textSHA256': hashlib.sha256(text[a:b].encode()).hexdigest()}
    def tick():
        count[0] += 1
        if count[0] > max_nodes: raise RefreshError('ingredient-components-node-bound')
    def trim(a, b):
        while a < b and text[a].isspace(): a += 1
        while b > a and text[b - 1].isspace(): b -= 1
        return a, b
    def delimiters(a, b, depth):
        stack = []; groups = []; cuts = []; uncertainty = []
        for position in range(a, b):
            character = text[position]
            if character in '([':
                if depth + len(stack) >= max_depth: raise RefreshError('ingredient-components-depth-bound')
                stack.append((character, position))
            elif character in ')]':
                if not stack or {'(': ')', '[': ']'}[stack[-1][0]] != character:
                    uncertainty.append({'reason': 'unmatched-close-delimiter', 'offset': position})
                else:
                    _, opening = stack.pop()
                    if not stack: groups.append((opening, position + 1))
            elif character in ',;' and not stack: cuts.append(position)
        uncertainty += [{'reason': 'unclosed-delimiter', 'offset': position} for _, position in stack]
        return groups, cuts, uncertainty
    def quantities(a, b, attachment):
        result = []
        for match in quantity.finditer(text, a, b):
            result.append({**span(match.start(), match.end()),
                'valueLexeme': match.group('value'), 'unitLexeme': match.group('unit'),
                'attachment': attachment, 'basis': None, 'interpretedValue': None,
                'meaning': 'explicit source quantity/percentage lexeme; basis and factual truth unverified'})
        return result
    def forest(a, b, parent, depth):
        groups, cuts, uncertainty = delimiters(a, b, depth)
        bounds = [a] + [p + 1 for p in cuts]; ends = cuts + [b]
        nodes = []
        for left, right in zip(bounds, ends):
            left, right = trim(left, right)
            if left == right: continue
            tick(); node_id = 'source-component:' + digest + ':' + str(left) + ':' + str(right)
            node_groups, _, local_uncertainty = delimiters(left, right, depth)
            node = {**span(left, right), 'componentId': node_id, 'parentComponentId': parent,
                    'nameSpans': [], 'groups': [], 'children': [], 'quantities': [],
                    'uncertainty': local_uncertainty, 'canonicalConceptId': None,
                    'meaning': 'syntactic source ingredient fragment; no canonical identity or composition truth'}
            cursor = left
            for opening, closing in node_groups:
                name_start, name_end = trim(cursor, opening)
                if name_start < name_end:
                    node['nameSpans'].append(span(name_start, name_end))
                    node['quantities'] += quantities(name_start, name_end, 'explicit in source fragment')
                tick(); inner_start, inner_end = trim(opening + 1, closing - 1)
                qs = quantities(inner_start, inner_end, 'source-parenthetical attached to preceding fragment')
                only_quantity = len(qs) == 1 and qs[0]['start'] == inner_start and qs[0]['end'] == inner_end
                group = {**span(opening, closing), 'openDelimiter': text[opening], 'closeDelimiter': text[closing - 1],
                         'kind': 'quantity-statement' if only_quantity else 'source-component-group'}
                if only_quantity:
                    node['quantities'] += qs
                else:
                    nested = forest(inner_start, inner_end, node_id, depth + 1)
                    node['children'] += nested['components']; group['separators'] = nested['separators']
                    group['uncertainty'] = nested['uncertainty']
                node['groups'].append(group); cursor = closing
            name_start, name_end = trim(cursor, right)
            if name_start < name_end:
                node['nameSpans'].append(span(name_start, name_end))
                node['quantities'] += quantities(name_start, name_end, 'explicit in source fragment')
            if re.fullmatch(r'\d+[A-Za-z]?', text[left:right]):
                node['uncertainty'].append({'reason': 'bare numeric/code fragment; no quantity unit or canonical additive identity inferred', 'offset': left})
            nodes.append(node)
        separators = []
        for one, two in zip(nodes, nodes[1:]): separators.append(span(one['end'], two['start']))
        return {'components': nodes, 'separators': separators, 'uncertainty': uncertainty}
    result = forest(start, end, None, 0)
    return {'componentExtractionVersion': COMPONENT_VERSION, 'rawTextSHA256': digest,
            'ingredientSpan': span(start, end), **result, 'quantityInterpretation': 'source lexemes only; never percentages inferred from order or sums',
            'canonicalMapping': None, 'certification': None}
