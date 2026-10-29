"""Deterministic cached-label sections; no identity, safety or runtime AI claims."""
import hashlib
import re

from .core import RefreshError

VERSION = 'offmenu-source-label-sections/1'
_END = r'.*?(?:[.!?](?=\s|$)|$)'
_BATCH = r'(?-i:[0-9][A-Z0-9]{7,})'
_RULES = (
    ('allergen_statement', r'\b(?:MAY CONTAIN|CONTAINS)\b' + _END),
    ('storage', r'\b(?:Keep refrigerated|Keep frozen|Store\s+(?:below|at|in|away from))\b' + _END),
    ('origin_claim', r'\bMade in\s+.+?\s+from\s+at least\s+\d+(?:[.,]\d+)?%\s+.+?\s+ingredients\b'),
    ('company_address', r'\b[^.!?\n]*\bregistered trademark\b' + _END),
    ('company_address', r"\b[A-Z][A-Z &'\-]{2,40},\s*\d{1,5}\s+[^.!?\n]*?\b\d{4,6}\b(?:\s+www\.[A-Za-z0-9.\-]+\.[A-Za-z]{2,})?"),
    ('recycling', r'\b(?:Tub|Lid|Insert|Bottle|Jar|Sleeve|Box|Cap)(?:\s+(?:Tub|Lid|Insert|Bottle|Jar|Sleeve|Box|Cap))*(?:\s+\d{4,32})?\s+[a-z0-9.\-]+\.(?:org|com)(?:\.[a-z]{2})?\b'),
    ('marketing', r'\bContributes to\b' + _END),
    ('marketing', r'\b[^.!?\n]*\b(?:guarantees|quality specifications|full refund|replacement)\b' + _END),
    ('marketing', r'\b(?:No Artificial|Source of|Suitable for)\b.*?(?=\s+(?:No Artificial|Source of|Suitable for)\b|\s+' + _BATCH + r'\b|$)'),
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
    if allergens and allergens[0] > 0 and ',' in text[:allergens[0]]:
        add(0, allergens[0], 'ingredient_list', 'candidate opening span before explicit allergen marker; no ingredient identity inference')
    elif re.match(r'^\s*ingredients\s*:', text, flags=re.IGNORECASE):
        add(0, min((a for a, *_ in selected), default=len(text)), 'ingredient_list', 'explicit source Ingredients header')
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
