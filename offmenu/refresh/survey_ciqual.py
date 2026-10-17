"""Read-only, bounded CIQUAL schema evidence. No acquisition or food export.

Inputs are bytes already pinned by the caller. This module neither opens files
nor fetches relationship targets. It never interprets styles or evaluates Excel
formulas. Names, identities and quantities are retained only transiently for
counts and set reconciliation. A survey is not a reviewed ingestion contract.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import posixpath
import re
import stat
import xml.etree.ElementTree as ET
import zipfile

WORKBOOK = 'Table Ciqual 2025_ENG_2025_11_03.xlsx'
IDENTITIES = 'alim_2025_11_03.xml'
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXPANDED = 96 * 1024 * 1024
MAX_XML = 32 * 1024 * 1024
MAX_MEMBERS = 128
MAX_ELEMENTS = 1_000_000
MAX_DEPTH = 40
MAX_ROWS = 10_000
MAX_COLUMNS = 128
MAX_TEXT = 4096
MAX_LABEL = 256
MAX_RESULT = 32 * 1024
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/package/2006/relationships}'
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
REL_PREFIX = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
CELL = re.compile(r'([A-Z]{1,3})([1-9][0-9]{0,6})\Z')
CODE = re.compile(r'[0-9]{1,12}\Z')
QUALIFIERS = ('zero', 'missing', 'blank', 'dash', 'trace', 'ND', 'NT', 'N',
              'bounds', 'numeric', 'unresolved', 'invalid')
CELL_TYPES = ('n', 's', 'inlineStr', 'str', 'b', 'e', 'd', 'other')
VALUE_TYPES = ('empty', 'integer', 'decimal', 'boolean', 'text', 'nested')
ROLES = ('workbook', 'worksheet', 'sharedStrings', 'styles', 'relationships',
         'contentTypes', 'theme', 'externalLink', 'macro', 'binary', 'otherXml')
REL_TYPES = ('officeDocument', 'worksheet', 'sharedStrings', 'styles', 'theme',
             'hyperlink', 'externalLink', 'drawing', 'table', 'comments',
             'vbaProject', 'calcChain', 'other')
FEATURES = ('formulas', 'externalReferences', 'extensions', 'mergedRanges',
            'hiddenRows', 'hiddenColumnRanges', 'hiddenColumns', 'hiddenSheets',
            'hyperlinks', 'definedNames', 'dataValidations', 'conditionalFormatting',
            'autoFilters', 'tables', 'drawings', 'macros', 'styledCells')
REASONS = frozenset((
    'invalid-input-set', 'invalid-input-bytes', 'archive-size-limit',
    'zip-member-limit', 'zip-member-name-rejected', 'zip-member-type-rejected',
    'zip-encryption-forbidden', 'zip-compression-unsupported', 'zip-member-bounds',
    'zip-expanded-size-limit', 'zip-member-size-mismatch', 'invalid-xlsx-archive',
    'xml-size-limit', 'xml-structure-limit', 'xml-attribute-limit',
    'xml-text-limit', 'xml-text-budget', 'xml-doctype-forbidden',
    'xml-processing-instruction-forbidden', 'invalid-xml', 'zip-xml-element-budget',
    'missing-workbook-part', 'invalid-workbook-envelope', 'invalid-relationship',
    'duplicate-relationship-id', 'external-or-unsafe-relationship',
    'unresolved-relationship', 'unsupported-workbook-feature',
    'additional-sheets-unreviewed', 'styles-present-unreviewed',
    'nondefault-number-format-unreviewed', 'invalid-style-dictionary',
    'invalid-shared-strings', 'unresolved-shared-string', 'invalid-cell',
    'invalid-row', 'worksheet-dimension-limit', 'invalid-worksheet-dimension',
    'invalid-worksheet-envelope', 'duplicate-row', 'unordered-row',
    'duplicate-cell', 'unordered-cell', 'missing-header-row', 'invalid-header',
    'structural-label-withheld', 'invalid-food-identity', 'duplicate-food-identity',
    'missing-english-name', 'identity-set-mismatch', 'invalid-identity-xml-envelope',
    'ambiguous-identity-xml-entries', 'missing-identity-field',
    'duplicate-identity-field', 'invalid-identity-field', 'empty-identity-table',
    'xml-entry-limit', 'schema-label-limit', 'result-size-limit',
))
OMISSIONS = ('xlsx', 'xml', 'worksheet-rows', 'worksheet-columns', 'schema-labels', 'report')


class SurveyError(ValueError):
    """Fixed non-sensitive failure code."""


class _Context:
    def __init__(self):
        self.reasons = set()
        self.omissions = set()

    def hold(self, reason, omission=None):
        assert reason in REASONS
        self.reasons.add(reason)
        if omission:
            self.omissions.add(omission)


class _BoundedTree(ET.TreeBuilder):
    """DTD and PI callbacks work for all XML encodings, including UTF-16."""
    def __init__(self):
        super().__init__()
        self.depth = self.elements = self.characters = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.elements += 1
        if self.depth > MAX_DEPTH or self.elements > MAX_ELEMENTS:
            raise SurveyError('xml-structure-limit')
        if len(tag) > MAX_TEXT or len(attrs) > 32 or any(
                len(k) + len(v) > MAX_TEXT for k, v in attrs.items()):
            raise SurveyError('xml-attribute-limit')
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        if len(result.text or '') > MAX_TEXT or any(len(x.tail or '') > MAX_TEXT for x in result):
            raise SurveyError('xml-text-limit')
        return result

    def data(self, data):
        self.characters += len(data)
        if self.characters > MAX_XML:
            raise SurveyError('xml-text-budget')
        return super().data(data)

    def doctype(self, name, pubid, system):
        raise SurveyError('xml-doctype-forbidden')

    def pi(self, target, data):
        raise SurveyError('xml-processing-instruction-forbidden')


def _xml(raw):
    if not 0 < len(raw) <= MAX_XML:
        raise SurveyError('xml-size-limit')
    target = _BoundedTree()
    try:
        parser = ET.XMLParser(target=target)
        for start in range(0, len(raw), 16384):
            parser.feed(raw[start:start + 16384])
        return parser.close(), target.elements
    except (ET.ParseError, UnicodeError, LookupError):
        raise SurveyError('invalid-xml') from None


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _label_ok(value):
    # Dictionary labels only. No arbitrary payloads, prose lines, paths or URLs.
    if not isinstance(value, str) or not 0 < len(value) <= MAX_LABEL:
        return False
    if not any(c.isalpha() for c in value) or value != value.strip():
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    if any(x in value for x in ('\\', '@', '://', 'www.', '../', './', '\x00')):
        return False
    if value.startswith(('/', '~')) or value.endswith(('.xml', '.xlsx', '.csv', '.json')):
        return False
    if any(not (c.isalnum() or c in " _-.,:;()[]%/+<>='µμ°βαγ×±*’–") for c in value):
        return False
    # Slashes are admitted only in parenthesized/bracketed dictionary unit suffixes.
    if '/' in value and not re.search(r'[\[(][^\[\]()]*\/[^\[\]()]*[\])]$', value):
        return False
    return True


def _label(value, ctx):
    if _label_ok(value):
        return value
    ctx.hold('structural-label-withheld', 'schema-labels')
    return None


def _tag_label(value, ctx):
    value = _local(value)
    if len(value) <= MAX_LABEL and re.fullmatch(r'[^\W\d][\w.-]*', value, re.UNICODE):
        return value
    ctx.hold('structural-label-withheld', 'schema-labels')
    return None


def _digest(values):
    # Unambiguous, order-independent digest of exact accepted lexical identities.
    raw = json.dumps(sorted(values), separators=(',', ':'), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _role(name):
    low = name.lower()
    if low.endswith('.rels'):
        return 'relationships'
    if name == '[Content_Types].xml':
        return 'contentTypes'
    if low.endswith('/workbook.xml'):
        return 'workbook'
    if '/worksheets/' in low and low.endswith('.xml'):
        return 'worksheet'
    if low.endswith('/sharedstrings.xml'):
        return 'sharedStrings'
    if low.endswith('/styles.xml'):
        return 'styles'
    if '/externallinks/' in low:
        return 'externalLink'
    if 'vbaproject' in low or low.endswith(('.vba', '.xlsm')):
        return 'macro'
    if '/theme/' in low:
        return 'theme'
    return 'otherXml' if low.endswith('.xml') else 'binary'


def _archive(raw):
    if not 0 < len(raw) <= MAX_ARCHIVE:
        raise SurveyError('archive-size-limit')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_MEMBERS:
                raise SurveyError('zip-member-limit')
            seen, total, roles = set(), 0, Counter()
            for item in infos:
                name = item.filename
                if (not name or name != item.orig_filename or len(name) > MAX_TEXT
                        or '\\' in name or '\x00' in name or ':' in name
                        or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))
                        or name in seen):
                    raise SurveyError('zip-member-name-rejected')
                seen.add(name)
                mode = item.external_attr >> 16
                if item.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise SurveyError('zip-member-type-rejected')
                if item.flag_bits & 1:
                    raise SurveyError('zip-encryption-forbidden')
                if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise SurveyError('zip-compression-unsupported')
                if not 0 <= item.file_size <= MAX_XML or item.file_size > max(1, item.compress_size) * 1000:
                    raise SurveyError('zip-member-bounds')
                total += item.file_size
                roles[_role(name)] += 1
                if total > MAX_EXPANDED:
                    raise SurveyError('zip-expanded-size-limit')
            members, elements = {}, 0
            for item in infos:
                if not item.filename.lower().endswith(('.xml', '.rels')):
                    continue  # No binary/macro extraction, execution or interpretation.
                with archive.open(item) as stream:
                    content = stream.read(item.file_size + 1)
                if len(content) != item.file_size:
                    raise SurveyError('zip-member-size-mismatch')
                root, count = _xml(content)
                elements += count
                if elements > MAX_ELEMENTS:
                    raise SurveyError('zip-xml-element-budget')
                members[item.filename] = root
            return members, seen, {'members': len(infos), 'archiveBytes': len(raw),
                'expandedBytes': total, 'xmlElements': elements, 'roles': dict(sorted(roles.items())),
                'securityInventoryComplete': True}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError, ValueError) as exc:
        if isinstance(exc, SurveyError):
            raise
        raise SurveyError('invalid-xlsx-archive') from None


def _rel_type(raw):
    kind = raw[len(REL_PREFIX):] if raw.startswith(REL_PREFIX) else 'other'
    return kind if kind in REL_TYPES else 'other'


def _target(relfile, target, external):
    if external:
        return None, 'external'
    if (not target or '\\' in target or ':' in target or '?' in target or '#' in target
            or target.startswith('//') or any(ord(c) < 32 for c in target)):
        return None, 'unsafe'
    if target.startswith('/'):
        resolved = posixpath.normpath(target[1:])
    else:
        base = '' if relfile == '_rels/.rels' else posixpath.dirname(posixpath.dirname(relfile))
        resolved = posixpath.normpath(posixpath.join(base, target))
    if resolved == '..' or resolved.startswith('../') or resolved.startswith('/'):
        return None, 'unsafe'
    return resolved, 'internal'


def _relationships(members, names, ctx):
    summary = {'total': 0, 'internal': 0, 'external': 0, 'unsafe': 0,
               'unresolved': 0, 'duplicateIds': 0, 'types': {}}
    tables, kinds = {}, Counter()
    for name, root in members.items():
        if not name.endswith('.rels'):
            continue
        table = {}
        if root.tag != R + 'Relationships':
            ctx.hold('invalid-relationship')
            tables[name] = table
            continue
        for index, rel in enumerate(root, 1):
            summary['total'] += 1
            if rel.tag != R + 'Relationship' or len(rel) or (rel.text or '').strip():
                ctx.hold('invalid-relationship')
                summary['unsafe'] += 1
                continue
            kind = _rel_type(rel.get('Type', ''))
            kinds[kind] += 1
            target, state = _target(name, rel.get('Target', ''), rel.get('TargetMode', 'Internal') != 'Internal')
            summary[state] += 1
            if state in ('external', 'unsafe'):
                ctx.hold('external-or-unsafe-relationship')
            elif target not in names:
                state = 'unresolved'
                summary['unresolved'] += 1
                ctx.hold('unresolved-relationship')
            rid = rel.get('Id')
            if not rid:
                ctx.hold('invalid-relationship')
                continue
            if rid in table:
                summary['duplicateIds'] += 1
                table[rid] = (index, kind, None, 'ambiguous')
                ctx.hold('duplicate-relationship-id')
            else:
                table[rid] = (index, kind, target, state)
        tables[name] = table
    summary['types'] = dict(sorted(kinds.items()))
    return summary, tables


def _text(item):
    if item is None:
        return None
    parts = []
    if (item.text or '').strip() or any((x.tail or '').strip() for x in item):
        return None
    for child in item:
        if child.tag == S + 't' and not len(child):
            parts.append(child.text or '')
        elif child.tag == S + 'r':
            ts = child.findall(S + 't')
            if len(ts) != 1 or len(ts[0]) or any(x.tag not in (S + 't', S + 'rPr') for x in child):
                return None
            parts.append(ts[0].text or '')
        else:
            return None
    if len(item.findall(S + 't')) > 1 or (item.find(S + 't') is not None and len(item) != 1):
        return None
    value = ''.join(parts)
    return value if len(value) <= MAX_TEXT else None


def _strings(members, ctx):
    roots = [x for x in members.values() if x.tag == S + 'sst']
    report = {'parts': len(roots), 'entries': 0, 'richTextEntries': 0, 'invalidEntries': 0}
    values = []
    for root in roots:
        for entry in root:
            report['entries'] += 1
            if entry.find(S + 'r') is not None:
                report['richTextEntries'] += 1
            value = _text(entry) if entry.tag == S + 'si' else None
            if value is None:
                report['invalidEntries'] += 1
                ctx.hold('invalid-shared-strings')
            values.append(value)
    if len(roots) > 1:
        ctx.hold('invalid-shared-strings')
        values = []
    return values, report


def _small_int(value, maximum=1_000_000):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,7}', value):
        return None
    number = int(value)
    return number if number <= maximum else None


def _styles(members, ctx):
    roots = [x for x in members.values() if x.tag == S + 'styleSheet']
    out = {'parts': len(roots), 'cellFormats': 0, 'customFormats': 0,
           'numFmtIds': [], 'customNumFmtIds': [], 'invalidIds': 0}
    ids, custom = set(), set()
    if roots:
        ctx.hold('styles-present-unreviewed')
    for root in roots:
        for xf in root.findall(S + 'cellXfs/' + S + 'xf'):
            out['cellFormats'] += 1
            value = _small_int(xf.get('numFmtId'), 65535)
            if value is None:
                out['invalidIds'] += 1
            else:
                ids.add(value)
        for fmt in root.findall(S + 'numFmts/' + S + 'numFmt'):
            out['customFormats'] += 1
            value = _small_int(fmt.get('numFmtId'), 65535)
            if value is None:
                out['invalidIds'] += 1
            else:
                custom.add(value)
    if out['invalidIds']:
        ctx.hold('invalid-style-dictionary')
    if custom or ids - {0}:
        ctx.hold('nondefault-number-format-unreviewed')
    if len(ids) > 256 or len(custom) > 256:
        ctx.hold('schema-label-limit', 'schema-labels')
    out['numFmtIds'], out['customNumFmtIds'] = sorted(ids)[:256], sorted(custom)[:256]
    return out


def _coordinate(raw):
    match = CELL.fullmatch(raw or '')
    if not match:
        return None
    col = 0
    for char in match[1]:
        col = col * 26 + ord(char) - 64
    return int(match[2]), col


def _dimension(sheet, ctx):
    values = sheet.findall(S + 'dimension')
    if not values:
        return None
    if len(values) != 1:
        ctx.hold('invalid-worksheet-dimension')
        return None
    bits = values[0].get('ref', '').split(':')
    coords = [_coordinate(x) for x in bits]
    if len(bits) not in (1, 2) or any(x is None for x in coords):
        ctx.hold('invalid-worksheet-dimension')
        return None
    first, last = coords[0], coords[-1]
    if first[0] > last[0] or first[1] > last[1]:
        ctx.hold('invalid-worksheet-dimension')
        return None
    if last[0] > MAX_ROWS or last[1] > MAX_COLUMNS:
        ctx.hold('worksheet-dimension-limit', 'worksheet-rows' if last[0] > MAX_ROWS else 'worksheet-columns')
    return {'firstRow': first[0], 'lastRow': last[0], 'firstColumn': first[1], 'lastColumn': last[1]}


def _cell(cell, strings, ctx):
    kind = cell.get('t', 'n')
    if kind not in CELL_TYPES:
        kind = 'other'
    if (cell.find(S + 'f') is not None or any(x.tag not in (S + 'v', S + 'is') for x in cell)
            or len(cell.findall(S + 'v')) > 1 or len(cell.findall(S + 'is')) > 1
            or (cell.text or '').strip() or any((x.tail or '').strip() for x in cell)):
        ctx.hold('invalid-cell')
        return kind, None, True
    v, inline = cell.find(S + 'v'), cell.find(S + 'is')
    if v is not None and (len(v) or v.attrib):
        ctx.hold('invalid-cell')
        return kind, None, True
    raw = None if v is None else v.text
    valid = True
    if kind == 'inlineStr':
        valid = v is None and inline is not None
        raw = _text(inline) if valid else None
        valid = valid and raw is not None
    elif kind == 's':
        index = _small_int(raw)
        valid = inline is None and index is not None and index < len(strings)
        raw = strings[index] if valid else None
        valid = valid and raw is not None
        if not valid:
            ctx.hold('unresolved-shared-string')
    elif kind in ('n', 'str'):
        valid = inline is None
        if kind == 'n' and raw is not None:
            valid = valid and _number(raw) is not None
    else:
        valid = False
    if not valid:
        ctx.hold('invalid-cell')
    return kind, raw, not valid


def _number(raw):
    if not isinstance(raw, str) or not DECIMAL.fullmatch(raw):
        return None
    try:
        value = Decimal(raw)
        # Avoid exponents outside a finite binary64-compatible observation range.
        if not value.is_finite() or (value and abs(value.adjusted()) > 308):
            return None
        return value
    except (InvalidOperation, ValueError, OverflowError):
        return None


def _qualifier(cell):
    if cell is None:
        return 'missing'
    kind, raw, invalid = cell
    if invalid:
        return 'invalid'
    if raw is None:
        return 'missing'
    text = raw.strip().replace(',', '.')
    if not text:
        return 'blank'
    if text == '-':
        return 'dash'
    token = text.upper()
    special = {'TR': 'trace', 'TRACE': 'trace', 'ND': 'ND', 'NOT DETECTED': 'ND',
               'NT': 'NT', 'NOT TESTED': 'NT', 'N': 'N'}
    if token in special:
        return special[token]
    if re.fullmatch(r'(?:<=|>=|<|>|≤|≥)\s*' + DECIMAL.pattern[:-2], text):
        val = re.sub(r'^(?:<=|>=|<|>|≤|≥)\s*', '', text)
        return 'bounds' if _number(val) is not None else 'invalid'
    value = _number(text)
    if value is not None:
        return 'zero' if value == 0 else 'numeric'
    if DECIMAL.fullmatch(text) or token.lstrip('+-') in ('NAN', 'INF', 'INFINITY'):
        return 'invalid'
    return 'unresolved'


def _identity_report():
    return {'text': 0, 'integer': 0, 'float': 0, 'leadingZero': 0, 'missing': 0,
            'invalid': 0, 'duplicates': 0, 'valid': 0, 'unique': 0, 'setSha256': _digest(set())}


def _identity(cell, report, codes, ctx):
    if cell is None or (not cell[2] and (cell[1] is None or not cell[1].strip())):
        report['missing'] += 1
        ctx.hold('invalid-food-identity')
        return
    kind, value, invalid = cell
    if kind in ('s', 'inlineStr', 'str'):
        report['text'] += 1
        code = value
    elif kind == 'n' and value is not None:
        if '.' in value or 'e' in value.lower():
            report['float'] += 1
            code = None
        else:
            report['integer'] += 1
            number = _number(value)
            code = str(int(number)) if number is not None and abs(number) < 10 ** 12 else None
    else:
        code = None
    if value and re.fullmatch(r'0[0-9]+', value):
        report['leadingZero'] += 1
    if invalid or code is None or not CODE.fullmatch(code):
        report['invalid'] += 1
        ctx.hold('invalid-food-identity')
        return
    report['valid'] += 1
    if code in codes:
        report['duplicates'] += 1
        ctx.hold('duplicate-food-identity')
    codes.add(code)


def _presence(cell):
    if cell is None or (not cell[2] and cell[1] is None):
        return 'missing'
    if cell[2] or cell[0] not in ('s', 'inlineStr', 'str'):
        return 'invalid'
    return 'present' if cell[1].strip() else 'blank'


def _sheet(root, strings, first, ctx):
    dimension = _dimension(root, ctx)
    data = root.findall(S + 'sheetData')
    if root.tag != S + 'worksheet' or len(data) != 1:
        raise SurveyError('invalid-worksheet-envelope')
    stats = {'dimension': dimension, 'rows': 0, 'dataRows': 0, 'cells': 0,
             'invalidRows': 0, 'invalidCells': 0, 'duplicateRows': 0, 'duplicateCells': 0,
             'maxRow': 0, 'maxColumn': 0, 'cellTypes': {}, 'rowWidths': []}
    types, widths, rows_seen = Counter(), Counter(), set()
    previous, header = 0, None
    qualifiers = [Counter() for _ in range(MAX_COLUMNS)]
    codes, identity, names = set(), _identity_report(), Counter()
    for row in data[0]:
        stats['rows'] += 1
        if stats['rows'] > MAX_ROWS:
            ctx.hold('worksheet-dimension-limit', 'worksheet-rows')
            break
        index = _small_int(row.get('r'), 9_999_999)
        if row.tag != S + 'row' or index is None or index == 0:
            stats['invalidRows'] += 1
            ctx.hold('invalid-row')
            continue
        if index > MAX_ROWS:
            ctx.hold('worksheet-dimension-limit', 'worksheet-rows')
            continue
        if index in rows_seen:
            stats['duplicateRows'] += 1
            ctx.hold('duplicate-row')
            continue
        if index < previous:
            ctx.hold('unordered-row')
        rows_seen.add(index)
        previous = index
        stats['maxRow'] = max(stats['maxRow'], index)
        cells, prior_col = {}, 0
        for cell in row:
            stats['cells'] += 1
            coord = _coordinate(cell.get('r'))
            if cell.tag != S + 'c' or coord is None or coord[0] != index:
                stats['invalidCells'] += 1
                ctx.hold('invalid-cell')
                continue
            col = coord[1]
            if col > MAX_COLUMNS:
                ctx.hold('worksheet-dimension-limit', 'worksheet-columns')
                continue
            if col in cells:
                stats['duplicateCells'] += 1
                ctx.hold('duplicate-cell')
                cells[col] = ('other', None, True)
                continue
            if col < prior_col:
                ctx.hold('unordered-cell')
            prior_col = col
            parsed = _cell(cell, strings, ctx)
            cells[col] = parsed
            types[parsed[0]] += 1
            stats['invalidCells'] += int(parsed[2])
            stats['maxColumn'] = max(stats['maxColumn'], col)
        widths[len(cells)] += 1
        if index == 1:
            header = cells
        else:
            stats['dataRows'] += 1
            if first:
                for col in range(1, MAX_COLUMNS + 1):
                    qualifiers[col - 1][_qualifier(cells.get(col))] += 1
                _identity(cells.get(7), identity, codes, ctx)
                names[_presence(cells.get(8))] += 1
    stats['cellTypes'] = dict(sorted(types.items()))
    stats['rowWidths'] = [{'columns': key, 'rows': val} for key, val in sorted(widths.items())]
    if not first:
        return stats, None, None
    if header is None:
        ctx.hold('missing-header-row', 'schema-labels')
        header = {}
    columns = max(stats['maxColumn'], min(MAX_COLUMNS, (dimension or {}).get('lastColumn', 0)))
    labels = []
    for col in range(1, columns + 1):
        value = header.get(col)
        label, suffix = None, None
        if value and not value[2] and value[0] in ('s', 'inlineStr', 'str') and value[1]:
            label = _label(value[1], ctx)
            if label:
                match = re.search(r'(\([^()]*\)|\[[^\[\]]*\])$', label)
                if match:
                    suffix = match[1]  # Preserve delimiters, whitespace and literal spelling.
        else:
            ctx.hold('invalid-header')
        labels.append({'column': col, 'label': label, 'literalUnitSuffix': suffix,
                       'rawHeaderSha256': hashlib.sha256(value[1].encode('utf-8')).hexdigest() if value and isinstance(value[1], str) else None,
                       'rawHeaderCharacters': len(value[1]) if value and isinstance(value[1], str) else 0,
                       'qualifiers': dict(sorted(qualifiers[col - 1].items()))})
    identity['unique'], identity['setSha256'] = len(codes), _digest(codes)
    if any(names[x] for x in ('missing', 'blank', 'invalid')):
        ctx.hold('missing-english-name')
    return stats, {'headerRow': 1, 'rawHeaderSequenceSha256': hashlib.sha256(_encode([header.get(col) for col in range(1, columns + 1)])).hexdigest(),
                   'headerHashSemantics': 'decoded-xml-text-utf8-no-normalization', 'unitSemantics': 'unverified-literal-header-suffix',
                   'qualifierCategories': list(QUALIFIERS), 'columns': labels,
                   'foodCodeColumn': 7, 'englishNameColumn': 8,
                   'foodCodes': identity, 'englishNamePresence': dict(sorted(names.items()))}, codes


def _features(members, archive):
    out = dict.fromkeys(FEATURES, 0)
    tags = {'f': 'formulas', 'externalReference': 'externalReferences', 'ext': 'extensions',
            'mergeCell': 'mergedRanges', 'hyperlink': 'hyperlinks', 'definedName': 'definedNames',
            'dataValidation': 'dataValidations', 'conditionalFormatting': 'conditionalFormatting',
            'autoFilter': 'autoFilters', 'tablePart': 'tables', 'drawing': 'drawings'}
    for root in members.values():
        for item in root.iter():
            if item.tag.startswith(S):
                name = _local(item.tag)
                if name in tags:
                    out[tags[name]] += 1
                if name == 'row' and item.get('hidden') in ('1', 'true'):
                    out['hiddenRows'] += 1
                if name == 'col' and item.get('hidden') in ('1', 'true'):
                    out['hiddenColumnRanges'] += 1
                    low, high = _small_int(item.get('min'), 16384), _small_int(item.get('max'), 16384)
                    if low and high and high >= low:
                        out['hiddenColumns'] += high - low + 1
                if name == 'sheet' and item.get('state') in ('hidden', 'veryHidden'):
                    out['hiddenSheets'] += 1
                if name == 'c' and item.get('s', '0') != '0':
                    out['styledCells'] += 1
    out['macros'] = archive['roles'].get('macro', 0)
    return out


def _workbook(raw, ctx):
    members, names, archive = _archive(raw)
    relationships, tables = _relationships(members, names, ctx)
    features = _features(members, archive)
    if any(features.values()) or archive['roles'].get('binary'):
        ctx.hold('unsupported-workbook-feature')
    strings, shared = _strings(members, ctx)
    styles = _styles(members, ctx)
    out = {'archive': archive, 'relationships': relationships, 'features': features,
           'sharedStrings': shared, 'styles': styles, 'sheets': [], 'firstSheet': None}
    required = ('xl/workbook.xml', '_rels/.rels', 'xl/_rels/workbook.xml.rels', '[Content_Types].xml')
    if any(x not in members for x in required):
        ctx.hold('missing-workbook-part', 'xlsx')
        return out, None
    root = members['xl/workbook.xml']
    lists = root.findall(S + 'sheets')
    if root.tag != S + 'workbook' or len(lists) != 1:
        ctx.hold('invalid-workbook-envelope', 'xlsx')
        return out, None
    roots = [v for v in tables.get('_rels/.rels', {}).values() if v[1] == 'officeDocument']
    if len(roots) != 1 or roots[0][2:] != ('xl/workbook.xml', 'internal'):
        ctx.hold('unresolved-relationship')
    sheets = list(lists[0])
    if len(sheets) != 1:
        ctx.hold('additional-sheets-unreviewed')
    if len(sheets) > MAX_MEMBERS:
        ctx.hold('schema-label-limit', 'schema-labels')
    codes = None
    for index, sheet in enumerate(sheets[:MAX_MEMBERS], 1):
        label = _label(sheet.get('name', ''), ctx)
        state = sheet.get('state', 'visible')
        if state not in ('visible', 'hidden', 'veryHidden'):
            state = 'invalid'
            ctx.hold('invalid-workbook-envelope')
        relation = tables.get('xl/_rels/workbook.xml.rels', {}).get(sheet.get(RID))
        number, kind, target, resolution = relation or (0, 'other', None, 'unresolved')
        item = {'index': index, 'label': label, 'state': state,
                'relationship': {'index': number, 'type': kind, 'resolution': resolution}, 'statistics': None}
        out['sheets'].append(item)
        if sheet.tag != S + 'sheet' or resolution != 'internal' or kind != 'worksheet' or target not in members:
            ctx.hold('unresolved-relationship', 'xlsx')
            continue
        try:
            stats, first, found = _sheet(members[target], strings, index == 1, ctx)
            item['statistics'] = stats
            if index == 1:
                out['firstSheet'], codes = first, found
        except SurveyError as exc:
            ctx.hold(str(exc), 'xlsx')
    if not sheets:
        ctx.hold('missing-header-row', 'xlsx')
    return out, codes


def _value_type(field):
    if len(field):
        return 'nested'
    text = (field.text or '').strip()
    if not text:
        return 'empty'
    if re.fullmatch(r'[+-]?[0-9]+', text):
        return 'integer'
    if _number(text) is not None:
        return 'decimal'
    if text in ('true', 'false'):
        return 'boolean'
    return 'text'


def _identities(raw, ctx):
    root, count = _xml(raw)
    parents, depths, stack = {}, {}, [(root, 0)]
    namespaces = Counter()
    while stack:
        item, depth = stack.pop()
        depths[item] = depth
        namespace = item.tag[1:].split('}', 1)[0] if item.tag.startswith('{') else ''
        namespaces[namespace] += 1
        for child in item:
            parents[child] = item
            stack.append((child, depth + 1))
    # Discover entry families from identity field names, then include all peers
    # with the same expanded tag, including peers missing BOTH required fields.
    seeds = [item for item in root.iter() if any(_local(x.tag) in ('alim_code', 'alim_nom_fr') for x in item)]
    families = {(parents.get(x), x.tag) for x in seeds}
    entries = [x for x in root.iter() if (parents.get(x), x.tag) in families]
    if len(families) > 1:
        ctx.hold('ambiguous-identity-xml-entries')
    if not entries:
        ctx.hold('empty-identity-table')
    if len(entries) > MAX_ROWS:
        ctx.hold('xml-entry-limit', 'xml')
    selected = entries[:MAX_ROWS]
    tags = Counter(x.tag for x in selected)
    fields = {}
    codes, identity, names = set(), _identity_report(), Counter()
    for entry in selected:
        by_name = {}
        for field in entry:
            name = field.tag
            if name not in fields:
                if len(fields) >= MAX_COLUMNS:
                    ctx.hold('schema-label-limit', 'schema-labels')
                    continue
                fields[name] = {'name': _tag_label(name, ctx), 'presentEntries': 0,
                                'occurrences': 0, 'missingEntries': 0, 'duplicateEntries': 0,
                                'attributeOccurrences': 0, 'types': Counter()}
            report = fields[name]
            report['occurrences'] += 1
            report['attributeOccurrences'] += len(field.attrib)
            report['types'][_value_type(field)] += 1
            by_name.setdefault(name, []).append(field)
        for name, items in by_name.items():
            fields[name]['presentEntries'] += 1
            if len(items) > 1:
                fields[name]['duplicateEntries'] += 1
                ctx.hold('duplicate-identity-field')
        matches = {key: [f for f in entry if _local(f.tag) == key]
                   for key in ('alim_code', 'alim_nom_fr')}
        code_fields, name_fields = matches['alim_code'], matches['alim_nom_fr']
        if len(code_fields) != 1 or len(name_fields) != 1:
            ctx.hold('missing-identity-field' if not code_fields or not name_fields else 'duplicate-identity-field')
        if len(code_fields) == 1 and not len(code_fields[0]) and not code_fields[0].attrib:
            _identity(('str', (code_fields[0].text or '').strip(), False), identity, codes, ctx)
        else:
            _identity(None if not code_fields else ('other', None, True), identity, codes, ctx)
        if len(name_fields) != 1:
            names['missing' if not name_fields else 'invalid'] += 1
        else:
            field = name_fields[0]
            if len(field) or field.attrib:
                names['invalid'] += 1
                ctx.hold('invalid-identity-field')
            else:
                names['present' if (field.text or '').strip() else 'blank'] += 1
    for item in fields.values():
        item['missingEntries'] = len(selected) - item['presentEntries']
        item['types'] = dict(sorted(item['types'].items()))
    if names['missing'] or names['blank'] or names['invalid']:
        ctx.hold('invalid-identity-field')
    identity['unique'], identity['setSha256'] = len(codes), _digest(codes)
    if len(namespaces) > MAX_COLUMNS or len(tags) > MAX_COLUMNS:
        ctx.hold('schema-label-limit', 'schema-labels')
    ns_out = []
    for ns, occurrences in sorted(namespaces.items())[:MAX_COLUMNS]:
        ns_out.append({'kind': 'none' if not ns else 'namespaced',
                       'sha256': hashlib.sha256(ns.encode()).hexdigest(), 'elements': occurrences})
    return {'rootTag': _tag_label(root.tag, ctx), 'rootAttributeCount': len(root.attrib),
            'elementCount': count, 'namespaces': ns_out,
            'rootChildTags': _tag_counts(Counter(x.tag for x in root), ctx),
            'entryTags': _tag_counts(tags, ctx), 'entryFamilies': len(families),
            'entryCount': len(entries), 'surveyedEntries': len(selected),
            'entryMinDepth': min((depths[x] for x in selected), default=0),
            'entryMaxDepth': max((depths[x] for x in selected), default=0),
            'fields': [fields[x] for x in sorted(fields)],
            'foodCodes': identity, 'frenchNamePresence': dict(sorted(names.items()))}, codes


def _tag_counts(counts, ctx):
    if len(counts) > MAX_COLUMNS:
        ctx.hold('schema-label-limit', 'schema-labels')
    return [{'name': _tag_label(key, ctx), 'count': value}
            for key, value in sorted(counts.items())[:MAX_COLUMNS]]


def _base():
    return {'schemaVersion': 'offmenu-ciqual-schema-survey/1', 'sourceId': 'ciqual',
            'status': 'surveyed', 'reasonCodes': [], 'candidateGenerationEnabled': False,
            'evidenceComplete': True, 'omissions': [], 'xlsx': None, 'xml': None,
            'reconciliation': None}


def survey(blobs: dict[str, bytes]) -> dict:
    """Produce redacted evidence in one pass over two already-pinned inputs."""
    ctx, out = _Context(), _base()
    if not isinstance(blobs, dict) or set(blobs) != {WORKBOOK, IDENTITIES}:
        ctx.hold('invalid-input-set')
        blobs = blobs if isinstance(blobs, dict) else {}
    identities = {}
    for name, section, reader in ((WORKBOOK, 'xlsx', _workbook), (IDENTITIES, 'xml', _identities)):
        raw = blobs.get(name)
        if not isinstance(raw, bytes):
            ctx.hold('invalid-input-bytes', section)
            continue
        try:
            out[section], identities[section] = reader(raw, ctx)
        except SurveyError as exc:
            ctx.hold(str(exc), section)
    left, right = identities.get('xlsx'), identities.get('xml')
    if left is not None and right is not None:
        out['reconciliation'] = {'xlsxUnique': len(left), 'xmlUnique': len(right),
            'intersection': len(left & right), 'xlsxOnly': len(left - right), 'xmlOnly': len(right - left),
            'exactMatch': left == right, 'comparisonComplete': not ctx.omissions}
        if left != right:
            ctx.hold('identity-set-mismatch')
    out.update(status='held' if ctx.reasons else 'surveyed', reasonCodes=sorted(ctx.reasons),
               evidenceComplete=not ctx.omissions, omissions=sorted(ctx.omissions))
    if len(_encode(out)) > MAX_RESULT:
        out = _base()
        out.update(status='held', reasonCodes=sorted(ctx.reasons | {'result-size-limit'}),
                   evidenceComplete=False, omissions=sorted(ctx.omissions | {'report'}))
    return sanitize_report(out)


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def sanitize_report(value) -> dict:
    """Closed-schema validator; no arbitrary source strings may pass through.

    Returns a detached JSON-compatible value. Invalid reports raise a fixed code.
    No food-value escape hatch or recursive arbitrary-dictionary pass-through is
    provided. Dictionary labels are allowed only in explicit schema-label slots.
    """
    try:
        _validate(value, _REPORT)
        if len(_encode(value)) > MAX_RESULT:
            raise ValueError()
        if (value['status'] == 'surveyed') != (not value['reasonCodes']):
            raise ValueError()
        if value['evidenceComplete'] != (not value['omissions']):
            raise ValueError()
        if value['status'] == 'surveyed' and (value['xlsx'] is None or value['xml'] is None or value['reconciliation'] is None):
            raise ValueError()
        return json.loads(_encode(value))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError('invalid-ciqual-survey-report') from None


# Tiny internal schema language. Every nested object has a closed field set.
_I = ('int', 0, 1_000_000_000)
_B = ('bool',)
_HASH = ('hash',)
_LABEL = ('nullable', ('label',))
_TAG = ('nullable', ('tag',))
_PRESENCE = ('hist', ('present', 'missing', 'blank', 'invalid'))
_IDENT = {key: _I for key in ('text', 'integer', 'float', 'leadingZero', 'missing', 'invalid', 'duplicates', 'valid', 'unique')}
_IDENT['setSha256'] = _HASH
_DIM = ('nullable', {key: _I for key in ('firstRow', 'lastRow', 'firstColumn', 'lastColumn')})
_STATS = {key: _I for key in ('rows', 'dataRows', 'cells', 'invalidRows', 'invalidCells', 'duplicateRows', 'duplicateCells', 'maxRow', 'maxColumn')}
_STATS.update(dimension=_DIM, cellTypes=('hist', CELL_TYPES), rowWidths=('list', {'columns': ('int', 0, 128), 'rows': _I}, 129))
_FIRST = {'headerRow': ('enum', (1,)), 'rawHeaderSequenceSha256': _HASH,
          'headerHashSemantics': ('enum', ('decoded-xml-text-utf8-no-normalization',)), 'unitSemantics': ('enum', ('unverified-literal-header-suffix',)),
          'qualifierCategories': ('exact', list(QUALIFIERS)),
          'columns': ('list', {'column': ('int', 1, 128), 'label': _LABEL,
                     'literalUnitSuffix': ('nullable', ('suffix',)), 'rawHeaderSha256': ('nullable', _HASH),
                     'rawHeaderCharacters': ('int', 0, MAX_TEXT), 'qualifiers': ('hist', QUALIFIERS)}, 128),
          'foodCodeColumn': ('enum', (7,)), 'englishNameColumn': ('enum', (8,)),
          'foodCodes': _IDENT, 'englishNamePresence': _PRESENCE}
_XLSX = {
    'archive': {'members': ('int', 1, 128), 'archiveBytes': ('int', 1, MAX_ARCHIVE),
                'expandedBytes': ('int', 0, MAX_EXPANDED), 'xmlElements': ('int', 0, MAX_ELEMENTS),
                'roles': ('hist', ROLES), 'securityInventoryComplete': ('enum', (True,))},
    'relationships': {**{x: _I for x in ('total', 'internal', 'external', 'unsafe', 'unresolved', 'duplicateIds')}, 'types': ('hist', REL_TYPES)},
    'features': {x: _I for x in FEATURES},
    'sharedStrings': {x: _I for x in ('parts', 'entries', 'richTextEntries', 'invalidEntries')},
    'styles': {**{x: _I for x in ('parts', 'cellFormats', 'customFormats', 'invalidIds')},
               'numFmtIds': ('list', ('int', 0, 65535), 256), 'customNumFmtIds': ('list', ('int', 0, 65535), 256)},
    'sheets': ('list', {'index': ('int', 1, 128), 'label': _LABEL,
                       'state': ('enum', ('visible', 'hidden', 'veryHidden', 'invalid')),
                       'relationship': {'index': _I, 'type': ('enum', REL_TYPES),
                                        'resolution': ('enum', ('internal', 'external', 'unsafe', 'unresolved', 'ambiguous'))},
                       'statistics': ('nullable', _STATS)}, 128),
    'firstSheet': ('nullable', _FIRST),
}
_XML = {'rootTag': _TAG, 'rootAttributeCount': _I, 'elementCount': ('int', 1, MAX_ELEMENTS),
        'namespaces': ('list', {'kind': ('enum', ('none', 'namespaced')), 'sha256': _HASH, 'elements': _I}, 128),
        'rootChildTags': ('list', {'name': _TAG, 'count': _I}, 128),
        'entryTags': ('list', {'name': _TAG, 'count': _I}, 128),
        **{x: _I for x in ('entryFamilies', 'entryCount', 'surveyedEntries', 'entryMinDepth', 'entryMaxDepth')},
        'fields': ('list', {'name': _TAG, **{x: _I for x in ('presentEntries', 'occurrences', 'missingEntries', 'duplicateEntries', 'attributeOccurrences')}, 'types': ('hist', VALUE_TYPES)}, 128),
        'foodCodes': _IDENT, 'frenchNamePresence': _PRESENCE}
_REPORT = {'schemaVersion': ('enum', ('offmenu-ciqual-schema-survey/1',)), 'sourceId': ('enum', ('ciqual',)),
           'status': ('enum', ('surveyed', 'held')), 'reasonCodes': ('list', ('enum', REASONS), len(REASONS)),
           'candidateGenerationEnabled': ('enum', (False,)), 'evidenceComplete': _B,
           'omissions': ('list', ('enum', OMISSIONS), len(OMISSIONS)),
           'xlsx': ('nullable', _XLSX), 'xml': ('nullable', _XML),
           'reconciliation': ('nullable', {**{x: _I for x in ('xlsxUnique', 'xmlUnique', 'intersection', 'xlsxOnly', 'xmlOnly')},
                                            'exactMatch': _B, 'comparisonComplete': _B})}


def _validate(value, schema):
    if isinstance(schema, dict):
        if not isinstance(value, dict) or set(value) != set(schema):
            raise ValueError()
        for key, item in schema.items():
            _validate(value[key], item)
        return
    kind = schema[0]
    if kind == 'nullable':
        if value is not None:
            _validate(value, schema[1])
    elif kind == 'int':
        if type(value) is not int or not schema[1] <= value <= schema[2]:
            raise ValueError()
    elif kind == 'bool':
        if type(value) is not bool:
            raise ValueError()
    elif kind == 'enum':
        if not any(type(value) is type(x) and value == x for x in schema[1]):
            raise ValueError()
    elif kind == 'exact':
        if value != schema[1] or type(value) is not type(schema[1]):
            raise ValueError()
    elif kind == 'hash':
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError()
    elif kind == 'label':
        if not _label_ok(value):
            raise ValueError()
    elif kind == 'tag':
        if not isinstance(value, str) or len(value) > 256 or not re.fullmatch(r'[^\W\d][\w.-]*', value, re.UNICODE):
            raise ValueError()
    elif kind == 'suffix':
        if not isinstance(value, str) or len(value) > 256 or not re.fullmatch(r'(?:\([^()]*\)|\[[^\[\]]*\])', value) or not _label_ok('Unit ' + value):
            raise ValueError()
    elif kind == 'list':
        if not isinstance(value, list) or len(value) > schema[2]:
            raise ValueError()
        for item in value:
            _validate(item, schema[1])
    elif kind == 'hist':
        if not isinstance(value, dict) or not set(value) <= set(schema[1]):
            raise ValueError()
        for item in value.values():
            _validate(item, _I)
    else:
        raise ValueError()
