"""Bounded, deliberately small OOXML value reader; no formula or network engine.

All ZIP members are inspected in memory before interpretation. Unsupported
features fail closed. This is not a replacement for a general Excel library.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import io
import math
from pathlib import PurePosixPath
import re
import stat
import xml.etree.ElementTree as ET
import zipfile

MAX_XML = 32 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 96 * 1024 * 1024
MAX_MEMBERS = 128
MAX_ELEMENTS = 1_000_000
MAX_DEPTH = 40
MAX_ROWS = 10_000
MAX_COLUMNS = 128
MAX_TEXT = 4096
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/package/2006/relationships}'
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
C = '{http://schemas.openxmlformats.org/package/2006/content-types}'
CELL = re.compile(r'([A-Z]{1,3})([1-9][0-9]{0,6})')
DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')


class DataError(ValueError):
    """Non-sensitive diagnostic codes only."""


class BoundedTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = self.elements = self.characters = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.elements += 1
        if self.depth > MAX_DEPTH or self.elements > MAX_ELEMENTS:
            raise DataError('xml-structure-limit')
        if len(attrs) > 32 or any(len(k) + len(v) > MAX_TEXT for k, v in attrs.items()):
            raise DataError('xml-attribute-limit')
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        if result.text and len(result.text) > MAX_TEXT:
            raise DataError('xml-text-limit')
        return result

    def data(self, data):
        self.characters += len(data)
        if self.characters > MAX_XML:
            raise DataError('xml-text-budget')
        return super().data(data)

    def doctype(self, name, pubid, system):
        raise DataError('xml-doctype-forbidden')

    def pi(self, target, data):
        raise DataError('xml-processing-instruction-forbidden')


def parse_xml(raw):
    if not raw or len(raw) > MAX_XML:
        raise DataError('xml-size-limit')
    try:
        parser = ET.XMLParser(target=BoundedTree())
        for at in range(0, len(raw), 16_384):
            parser.feed(raw[at:at + 16_384])
        return parser.close()
    except (ET.ParseError, UnicodeError, LookupError):
        raise DataError('invalid-xml') from None


def finite_decimal(raw):
    if not isinstance(raw, str) or len(raw) > MAX_TEXT or not DECIMAL.fullmatch(raw):
        raise DataError('invalid-numeric-cell')
    try:
        value = Decimal(raw)
        number = float(value)
    except (ValueError, InvalidOperation, OverflowError):
        raise DataError('invalid-numeric-cell') from None
    if not value.is_finite() or not math.isfinite(number):
        raise DataError('nonfinite-quantity')
    if value != 0 and number == 0:
        raise DataError('quantity-underflow-held')
    return value, number


def coordinates(ref):
    match = CELL.fullmatch(ref or '')
    if not match:
        raise DataError('invalid-cell-reference')
    col = 0
    for char in match[1]:
        col = col * 26 + ord(char) - ord('A') + 1
    row = int(match[2])
    if col > MAX_COLUMNS or row > MAX_ROWS:
        raise DataError('worksheet-dimension-limit')
    return row, col


def structural(element, error='mixed-structural-content'):
    """Consumed containers may have indentation, never discarded value text."""
    if (element.text or '').strip() or any((child.tail or '').strip() for child in element):
        raise DataError(error)


def _archive(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ARCHIVE:
        raise DataError('archive-size-limit')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_MEMBERS:
                raise DataError('zip-member-limit')
            members, total, total_elements = {}, 0, 0
            for item in infos:
                name = item.filename
                path = PurePosixPath(name)
                if (not name or item.orig_filename != name or '\\' in name or '\x00' in name or path.is_absolute()
                        or any(part in ('', '.', '..') for part in name.split('/'))
                        or name in members):
                    raise DataError('zip-member-name-rejected')
                mode = item.external_attr >> 16
                if item.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                    raise DataError('zip-member-type-rejected')
                if (item.flag_bits & 1 or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or not 0 < item.file_size <= MAX_XML
                        or item.file_size > max(1, item.compress_size) * 1000):
                    raise DataError('zip-member-bounds')
                if not (name.endswith('.xml') or name.endswith('.rels')):
                    raise DataError('unsupported-workbook-member')
                total += item.file_size
                if total > MAX_EXPANDED:
                    raise DataError('zip-expanded-size-limit')
                with archive.open(item) as stream:
                    content = stream.read(item.file_size + 1)
                if len(content) != item.file_size:
                    raise DataError('zip-member-size-mismatch')
                root = parse_xml(content)
                total_elements += sum(1 for _ in root.iter())
                if total_elements > MAX_ELEMENTS:
                    raise DataError('zip-xml-element-budget')
                # No external relationships, including hyperlinks, data links,
                # templates or external workbooks. XML is never extracted.
                if name.endswith('.rels'):
                    if root.tag != R + 'Relationships':
                        raise DataError('invalid-relationship-root')
                    structural(root)
                    seen = set()
                    for relation in root:
                        if relation.tag != R + 'Relationship':
                            raise DataError('invalid-relationship')
                        structural(relation)
                        if len(relation):
                            raise DataError('invalid-relationship')
                        target = relation.get('Target', '')
                        rid = relation.get('Id')
                        if not rid or rid in seen:
                            raise DataError('duplicate-relationship-id')
                        seen.add(rid)
                        if (relation.get('TargetMode', 'Internal') != 'Internal'
                                or not target or '\\' in target or ':' in target
                                or target.startswith('//') or '?' in target or '#' in target
                                or any(p in ('.', '..') for p in target.split('/'))):
                            raise DataError('external-or-unsafe-relationship')
                members[name] = root
            return members
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError):
        raise DataError('invalid-xlsx-archive') from None


def _string(element):
    # Only standard plain/rich text. Phonetic or extension content is not folded
    # into the value. Preserve source whitespace exactly, as the legacy reader.
    children = list(element)
    if any(x.tag not in (S + 't', S + 'r') for x in children):
        raise DataError('unsupported-shared-string')
    if (element.text or '').strip() or any((x.tail or '').strip() for x in children):
        raise DataError('ambiguous-string-content')
    direct = [x for x in children if x.tag == S + 't']
    if len(direct) > 1 or (direct and len(children) != 1):
        raise DataError('ambiguous-string-content')
    def scalar_text(item):
        if len(item) or any(k != '{http://www.w3.org/XML/1998/namespace}space' for k in item.attrib):
            raise DataError('nested-or-unsupported-text-content')
        return item.text or ''
    values = []
    for item in children:
        if item.tag == S + 't':
            values.append(scalar_text(item))
        else:
            structural(item, 'ambiguous-string-content')
            if any(x.tag not in (S + 'rPr', S + 't') for x in item):
                raise DataError('unsupported-rich-string')
            if len(item.findall(S + 't')) != 1 or len(item.findall(S + 'rPr')) > 1:
                raise DataError('ambiguous-string-content')
            values.extend(scalar_text(x) for x in item if x.tag == S + 't')
    value = ''.join(values)
    if len(value) > MAX_TEXT:
        raise DataError('source-text-limit')
    return value


def read_workbook(raw):
    members = _archive(raw)
    required = ('[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels')
    if any(name not in members for name in required):
        raise DataError('missing-workbook-part')
    office = [item for item in members['_rels/.rels'] if item.get('Type') ==
              'http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument']
    if len(office) != 1 or office[0].get('Target') not in ('xl/workbook.xml', '/xl/workbook.xml'):
        raise DataError('unresolved-root-workbook-relationship')
    for item in members['_rels/.rels']:
        if item.get('Target', '').lstrip('/') not in members:
            raise DataError('unresolved-root-package-relationship')
    content_types = members['[Content_Types].xml']
    if content_types.tag != C + 'Types' or content_types.attrib:
        raise DataError('invalid-content-types-envelope')
    structural(content_types)
    defaults, overrides = {}, {}
    for item in content_types:
        if len(item) or (item.text or '').strip():
            raise DataError('invalid-content-types-entry')
        if item.tag == C + 'Default' and set(item.attrib) == {'Extension', 'ContentType'}:
            key, table = item.get('Extension'), defaults
            if (key, item.get('ContentType')) not in (('xml', 'application/xml'), ('rels', 'application/vnd.openxmlformats-package.relationships+xml')):
                raise DataError('unsupported-default-content-type')
        elif item.tag == C + 'Override' and set(item.attrib) == {'PartName', 'ContentType'}:
            key, table = item.get('PartName'), overrides
            if not key.startswith('/') or key[1:] not in members:
                raise DataError('unresolved-content-type-part')
        else:
            raise DataError('invalid-content-types-entry')
        if key in table:
            raise DataError('duplicate-content-type-entry')
        table[key] = item.get('ContentType')
    required_types = {'/xl/workbook.xml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'}
    if any(overrides.get(key) != value for key, value in required_types.items()):
        raise DataError('unreviewed-workbook-content-type')
    workbook = members['xl/workbook.xml']
    if workbook.tag != S + 'workbook':
        raise DataError('unsupported-workbook-namespace')
    structural(workbook)
    if len(workbook.findall(S + 'sheets')) != 1:
        raise DataError('ambiguous-workbook-sheets')
    sheets = workbook.find(S + 'sheets')
    # The legacy reads only the first sheet. This synthetic slice requires a
    # single declared sheet rather than silently ignoring unreviewed others.
    if sheets is None or len(sheets) != 1 or sheets[0].tag != S + 'sheet':
        raise DataError('single-worksheet-required')
    structural(sheets)
    structural(sheets[0])
    relations = {x.get('Id'): x for x in members['xl/_rels/workbook.xml.rels']}
    dependent_parts = {}
    for item in relations.values():
        relation_target = item.get('Target')
        absolute_target = relation_target[1:] if relation_target.startswith('/') else 'xl/' + relation_target
        if absolute_target not in members:
            raise DataError('unresolved-workbook-part-relationship')
        suffix = item.get('Type', '').removeprefix('http://schemas.openxmlformats.org/officeDocument/2006/relationships/')
        if suffix not in ('worksheet', 'sharedStrings', 'styles', 'theme'):
            raise DataError('unreviewed-workbook-relationship')
        if suffix in dependent_parts:
            raise DataError('duplicate-workbook-part-relationship')
        dependent_parts[suffix] = absolute_target
    for name, role in [('xl/sharedStrings.xml', 'sharedStrings'), ('xl/styles.xml', 'styles')]:
        if (name in members) != (role in dependent_parts) or (role in dependent_parts and dependent_parts[role] != name):
            raise DataError('unresolved-workbook-dictionary-relationship')
    relation = relations.get(sheets[0].get(RID))
    if relation is None or relation.get('Type') != 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet':
        raise DataError('unresolved-worksheet-relationship')
    target = relation.get('Target')
    target = target[1:] if target.startswith('/') else 'xl/' + target
    if target not in members or not target.startswith('xl/worksheets/'):
        raise DataError('missing-worksheet')
    if {name for name in members if name.startswith('xl/worksheets/') and name.endswith('.xml')} != {target}:
        raise DataError('undeclared-worksheet')
    if overrides.get('/' + target) != 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml':
        raise DataError('unreviewed-worksheet-content-type')
    sheet = members[target]
    if sheet.tag != S + 'worksheet':
        raise DataError('unsupported-worksheet-namespace')
    structural(sheet)
    # No Excel date/percentage/display conversions are guessed. Only the
    # reviewed general/default style is permitted in this synthetic contract.
    if 'xl/styles.xml' in members:
        styles = members['xl/styles.xml']
        xfs = styles.find(S + 'cellXfs')
        if styles.tag != S + 'styleSheet' or len(styles.findall(S + 'cellXfs')) != 1 or xfs is None or not len(xfs) or xfs[0].get('numFmtId') != '0':
            raise DataError('unreviewed-default-number-format')
        structural(styles)
        structural(xfs)
    for element in sheet.iter():
        if element.get('s', '0') != '0' or element.get('style', '0') != '0':
            raise DataError('unreviewed-number-style')
    if len(sheet.findall(S + 'dimension')) > 1 or len(sheet.findall(S + 'sheetData')) != 1:
        raise DataError('ambiguous-worksheet-container')
    dimensions = sheet.find(S + 'dimension')
    if dimensions is not None:
        structural(dimensions)
        parts = dimensions.get('ref', '').split(':')
        if len(parts) > 2:
            raise DataError('invalid-worksheet-dimension')
        for part in parts:
            coordinates(part)
    strings = []
    if 'xl/sharedStrings.xml' in members:
        root = members['xl/sharedStrings.xml']
        if root.tag != S + 'sst' or any(x.tag != S + 'si' for x in root):
            raise DataError('invalid-shared-strings')
        structural(root)
        strings = [_string(x) for x in root]
    # Reject formulas everywhere, even ignored parts. Cached values must never
    # masquerade as observations after a formula/definition change.
    for root in members.values():
        for item in root.iter():
            if item.tag in (S + 'f', S + 'externalReferences', S + 'extLst'):
                raise DataError('formula-or-extension-forbidden')
    data = sheet.find(S + 'sheetData')
    if data is None:
        raise DataError('missing-sheet-data')
    structural(data)
    rows, previous = [], 0
    for row in data:
        if row.tag != S + 'row' or not re.fullmatch(r'[1-9][0-9]*', row.get('r', '')):
            raise DataError('invalid-row')
        structural(row)
        index = int(row.get('r'))
        if not previous < index <= MAX_ROWS:
            raise DataError('duplicate-or-unordered-row')
        previous = index
        cells, last_column = {}, 0
        for cell in row:
            if cell.tag != S + 'c':
                raise DataError('unsupported-row-child')
            structural(cell)
            r, column = coordinates(cell.get('r'))
            if r != index or column <= last_column:
                raise DataError('duplicate-or-unordered-cell')
            last_column = column
            if any(x.tag not in (S + 'v', S + 'is') for x in cell):
                raise DataError('unsupported-cell-content')
            if len(cell.findall(S + 'v')) > 1 or len(cell.findall(S + 'is')) > 1:
                raise DataError('duplicate-cell-value')
            kind = cell.get('t', 'n')
            v = cell.find(S + 'v')
            inline = cell.find(S + 'is')
            if v is not None and (len(v) or v.attrib):
                raise DataError('nested-or-unsupported-numeric-content')
            if kind == 'inlineStr':
                if v is not None:
                    raise DataError('ambiguous-cell-value')
                value = _string(inline) if inline is not None else None
            elif kind == 's':
                if inline is not None or v is None or not re.fullmatch(r'0|[1-9][0-9]*', v.text or ''):
                    raise DataError('invalid-shared-string-index')
                at = int(v.text)
                if at >= len(strings):
                    raise DataError('unresolved-shared-string')
                value = strings[at]
            elif kind == 'n':
                if inline is not None:
                    raise DataError('ambiguous-cell-value')
                if v is None or not v.text:
                    value = None
                else:
                    exact, number = finite_decimal(v.text)
                    # Match openpyxl's integer-vs-float convention while testing
                    # the original lexical value before binary conversion.
                    value = int(exact) if '.' not in v.text and 'e' not in v.text.lower() else number
            else:
                raise DataError('unsupported-cell-type')
            cells[column] = value
        rows.append((index, cells))
    if not rows or rows[0][0] != 1:
        raise DataError('first-row-header-required')
    return rows
