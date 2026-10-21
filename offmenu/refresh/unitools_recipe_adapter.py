"""Selected retained UniTools JSON only. No acquisition, SQL or implicit reads.

The custody caller supplies an already open descriptor. Qualification reads that
descriptor once; all subsequent parsing/projection uses its immutable buffer.
"""
from dataclasses import dataclass
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import fcntl

from .core import canonical

VERSION = 'offmenu-unitools-native-recipe/1'
RECIPE_TEMPLATE_VERSION = 'offmenu-source-recipe/2'
SOURCE = 'unitools'
REVISION = '2f554073f7e730b18d707fe1164d18308f6ec16c'
INPUT_PATH = '/home/user/src/offmenu-data/recipe-research-20261013/unitools.json'
INPUT_BYTES = 2733812
IDENTITY = (64512, 17097004, 2733812, 1791886765308244259, 1791886765308244259)
BLOB_SHA1 = '1bde24df4bc51d49b5fe16200e7f5b2712fa940e'
REPOSITORY = 'https://github.com/farcrak/unitools-recipes'
BLOB_URL = 'https://api.github.com/repos/farcrak/unitools-recipes/git/blobs/' + BLOB_SHA1
LICENSE_SHA256 = '28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5'
TEMPLATE_SHA256 = '6c450429cea05a719bd367116cda978b465c44ab5f0e65c6fa0dc7a80ef57814'
DECLARED_COUNT = 501
MAX_RAW_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 1024
MAX_FIELDS = 300000
MAX_PROJECTED_BYTES = 16 * 1024 * 1024
_SEAL = object()
_NUMBER = re.compile(rb'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')


class UnitoolsError(ValueError):
    def __init__(self, code, receipt=None):
        super().__init__('unitools-' + code)
        self.receipt = receipt


def _require(condition, code):
    if not condition:
        raise UnitoolsError(code)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


@dataclass(frozen=True)
class UnitoolsSelection:
    """Trusted operation metadata, not permission inferred from a licence.

    Each receipt pin is (absolute path, SHA256), qualified by the selecting
    operator. Coverage reconciliation includes the existing normalized subset.
    This module records the pins; it does not install a runtime/rights grant.
    """
    source_use_receipt: tuple
    custody_receipt: tuple
    operation_receipt: tuple
    coverage_receipt: tuple
    source_use_scope: str

    def validate(self):
        for pin in (self.source_use_receipt, self.custody_receipt,
                    self.operation_receipt, self.coverage_receipt):
            _require(type(pin) is tuple and len(pin) == 2 and type(pin[0]) is str
                and 0 < len(pin[0]) <= 4096 and Path(pin[0]).is_absolute()
                and _sha(pin[1]), 'selection-receipt')
        _require(type(self.source_use_scope) is str and 0 < len(self.source_use_scope) <= 4096,
                 'source-use-scope')


@dataclass(frozen=True)
class _Number:
    token: str


@dataclass(frozen=True)
class _Node:
    value: object
    start: int
    end: int


class _JSON:
    """Bounded byte-token parser, solely for this selected native representation."""
    def __init__(self, raw):
        self.raw, self.pos, self.fields = raw, 0, 0

    def ws(self):
        while self.pos < len(self.raw) and self.raw[self.pos] in b' \r\n\t':
            self.pos += 1

    def node(self, depth=0):
        self.fields += 1
        _require(depth <= 64 and self.fields <= MAX_FIELDS, 'json-bound')
        self.ws()
        start = self.pos
        _require(start < len(self.raw), 'json-truncated')
        first = self.raw[start]
        if first in (123, 91):
            obj = first == 123
            value = {} if obj else []
            self.pos += 1
            self.ws()
            close = 125 if obj else 93
            if self.pos < len(self.raw) and self.raw[self.pos] == close:
                self.pos += 1
                return _Node(value, start, self.pos)
            while True:
                if obj:
                    key = self.node(depth + 1)
                    _require(type(key.value) is str and key.value not in value, 'json-key')
                    self.ws()
                    _require(self.raw[self.pos:self.pos + 1] == b':', 'json-colon')
                    self.pos += 1
                    value[key.value] = self.node(depth + 1)
                else:
                    value.append(self.node(depth + 1))
                self.ws()
                end = self.raw[self.pos:self.pos + 1]
                self.pos += 1
                if end == bytes([close]):
                    break
                _require(end == b',', 'json-delimiter')
            return _Node(value, start, self.pos)
        if first == 34:
            self.pos += 1
            while self.pos < len(self.raw):
                char = self.raw[self.pos]
                self.pos += 1
                if char == 92:
                    self.pos += 1
                elif char == 34:
                    try:
                        value = json.loads(self.raw[start:self.pos])
                        value.encode('utf-8', errors='strict')
                    except (ValueError, UnicodeError) as error:
                        raise UnitoolsError('json-string') from error
                    return _Node(value, start, self.pos)
            raise UnitoolsError('json-truncated')
        for token, value in ((b'null', None), (b'true', True), (b'false', False)):
            if self.raw.startswith(token, start):
                self.pos += len(token)
                return _Node(value, start, self.pos)
        match = _NUMBER.match(self.raw, start)
        _require(match is not None and len(match[0]) <= 128, 'json-number')
        self.pos += len(match[0])
        return _Node(_Number(match[0].decode('ascii')), start, self.pos)

    def parse(self):
        node = self.node()
        self.ws()
        _require(self.pos == len(self.raw), 'json-trailing')
        return node


@dataclass(frozen=True)
class VerifiedUnitoolsInput:
    raw: bytes
    source_sha256: str
    git_blob_sha1: str
    selection: UnitoolsSelection
    receipt: dict
    _root: _Node
    _seal: object


def _map(node):
    return type(node.value) is dict and all(type(x.value) is str for x in node.value.values())


def _classify(root):
    _require(type(root.value) is dict and 'recipes' in root.value
             and type(root.value['recipes'].value) is list, 'root-recipes')
    for field in ('attribution', 'licenseUrl'):
        _require(field in root.value and type(root.value[field].value) is str
                 and bool(root.value[field].value.strip()), 'root-metadata')
    _require(re.fullmatch(r'https://creativecommons.org/licenses/by-sa/4\.0/?',
                         root.value['licenseUrl'].value) is not None, 'licence-declaration')
    recipes = root.value['recipes'].value
    _require(0 < len(recipes) <= MAX_RECORDS, 'record-bound')
    rows, seen, duplicates = [], {}, []
    for index, recipe in enumerate(recipes):
        issues, slug = [], None
        obj = recipe.value
        if type(obj) is not dict:
            issues.append('record-not-object')
        else:
            slug = obj.get('slug')
            slug = slug.value if slug and type(slug.value) is str else None
            if not slug or not slug.strip():
                issues.append('slug-missing')
            if ('name' not in obj or not _map(obj['name']) or not any(
                    key in obj['name'].value and obj['name'].value[key].value.strip() for key in ('en', 'ru'))):
                issues.append('name-map-invalid')
            if 'baseServings' not in obj or type(obj['baseServings'].value) not in (_Number, str, type(None)):
                issues.append('base-servings-invalid')
            for field in ('ingredients', 'steps'):
                nodes = obj.get(field)
                if nodes is None or type(nodes.value) is not list or not 0 < len(nodes.value) <= 5000:
                    issues.append(field + '-array-invalid')
                    continue
                for child in nodes.value:
                    if type(child.value) is not dict:
                        issues.append(field + '-object-invalid')
                        continue
                    entry = child.value
                    label = 'name' if field == 'ingredients' else 'text'
                    if label not in entry or not _map(entry[label]):
                        issues.append(field + '-language-map-invalid')
                    if field == 'ingredients':
                        if 'quantity' in entry and type(entry['quantity'].value) not in (_Number, str, type(None)):
                            issues.append('quantity-type')
                        if 'unit' in entry and type(entry['unit'].value) not in (str, type(None)):
                            issues.append('unit-type')
        if slug is not None:
            if slug in seen:
                duplicates.append({'slug': slug, 'firstOrdinal': seen[slug], 'ordinal': index + 1})
            else:
                seen[slug] = index + 1
        rows.append({'ordinal': index + 1, 'pointer': f'/recipes/{index}', 'slug': slug,
                     'classification': 'held' if issues else 'source-recipe-occurrence',
                     'issues': sorted(set(issues))})
    holds = ([] if len(recipes) == DECLARED_COUNT else ['declared-count-mismatch'])
    if any(x['issues'] for x in rows):
        holds.append('held-native-occurrences')
    return {'producerDeclaredCount': DECLARED_COUNT, 'observedArrayCount': len(recipes),
        'distinctNativeSlugs': len(seen), 'duplicateSlugOccurrences': duplicates,
        'occurrences': rows, 'heldOccurrences': sum(bool(x['issues']) for x in rows),
        'loadHoldReasons': holds, 'publicationHoldReasons': holds + (['duplicate-native-slugs'] if duplicates else []),
        'historical499Proven': False, 'menus': 0}


def qualify_unitools_once(selection: UnitoolsSelection, held_fd: int) -> VerifiedUnitoolsInput:
    """Future selected operation only: one descriptor pass, dual digest, same buffer."""
    _require(type(selection) is UnitoolsSelection, 'selection-type')
    selection.validate()
    path = Path(INPUT_PATH)
    _require(not any(p.is_symlink() for p in (path, *path.parents)), 'input-symlink')
    before = os.fstat(held_fd)
    flags = fcntl.fcntl(held_fd, fcntl.F_GETFL)
    _require(stat.S_ISREG(before.st_mode) and identity(before) == IDENTITY
        and identity(path.stat(follow_symlinks=False)) == IDENTITY
        and before.st_size == INPUT_BYTES <= MAX_RAW_BYTES
        and os.lseek(held_fd, 0, os.SEEK_CUR) == 0
        and flags & os.O_ACCMODE == os.O_RDONLY and flags & os.O_NOFOLLOW, 'input-custody')
    sha = hashlib.sha256()
    blob = hashlib.sha1(b'blob ' + str(INPUT_BYTES).encode() + b'\0')
    receipt = {'sourceId': SOURCE, 'revision': REVISION, 'inputPath': INPUT_PATH,
        'inputBytes': INPUT_BYTES, 'inputSHA256': None, 'gitBlobSHA1': None,
        'bodyPasses': 1, 'EOFFullyVerified': False, 'custodyVerified': False,
        'observedIdentity': list(IDENTITY), 'observedBytes': 0,
        'sourceUseReceipt': selection.source_use_receipt, 'custodyReceipt': selection.custody_receipt,
        'operationReceipt': selection.operation_receipt, 'coverageReceipt': selection.coverage_receipt,
        'sourceUseScope': selection.source_use_scope, 'licenceSHA256': LICENSE_SHA256,
        'repository': REPOSITORY, 'originalDownloadURL': None, 'acquiredAt': None,
        'provenanceLocator': BLOB_URL, 'parserVersion': VERSION}
    try:
        parts, remaining = [], INPUT_BYTES
        while remaining:
            block = os.read(held_fd, min(1048576, remaining))
            _require(bool(block), 'input-short')
            sha.update(block)
            blob.update(block)
            parts.append(block)
            remaining -= len(block)
            receipt['observedBytes'] += len(block)
        _require(not os.read(held_fd, 1), 'input-extra')
        receipt.update(inputSHA256=sha.hexdigest(), gitBlobSHA1=blob.hexdigest(), EOFFullyVerified=True)
        _require(identity(os.fstat(held_fd)) == identity(path.stat(follow_symlinks=False)) == IDENTITY,
                 'input-custody')
        receipt['custodyVerified'] = True
        _require(blob.hexdigest() == BLOB_SHA1, 'git-blob-mismatch')
        raw = b''.join(parts)
        del parts
        raw.decode('utf-8', errors='strict')
        root = _JSON(raw).parse()
        receipt.update(_classify(root))
    except (UnitoolsError, UnicodeError, OSError) as error:
        if isinstance(error, UnitoolsError):
            error.receipt = receipt
            raise
        raise UnitoolsError('input-custody' if isinstance(error, OSError) else 'utf8', receipt) from error
    return VerifiedUnitoolsInput(raw, sha.hexdigest(), blob.hexdigest(), selection, receipt, root, _SEAL)


def validate_verified(verified):
    _require(type(verified) is VerifiedUnitoolsInput and verified._seal is _SEAL
        and type(verified.raw) is bytes and len(verified.raw) == INPUT_BYTES
        and verified.git_blob_sha1 == BLOB_SHA1 and _sha(verified.source_sha256), 'verified-input')
    _require(not verified.receipt['loadHoldReasons'], 'load-held')


def asset_from_verified(verified):
    validate_verified(verified)
    return {'sourceId': SOURCE, 'sourceRecordId': 'unitools-native-collection', 'recordKind': 'recipe',
        'inputPath': INPUT_PATH, 'inputBytes': INPUT_BYTES, 'inputSHA256': verified.source_sha256,
        'release': REVISION, 'gitBlobSHA1': BLOB_SHA1, 'sourceUseScope': verified.selection.source_use_scope}


def _pointer(parent, key):
    return parent + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _location(verified, node, pointer, record_pointer):
    return {'kind': 'native-json', 'sourceSHA256': verified.source_sha256,
        'jsonPointer': pointer, 'sourceRecordPointer': record_pointer,
        'utf8ByteRange': [node.start, node.end],
        'sourceSpanSHA256': hashlib.sha256(verified.raw[node.start:node.end]).hexdigest()}


def native_recipe_schema():
    """Selected profile overlay only; the accepted HTML/PDF schema stays untouched."""
    path = Path(__file__).with_name('source_recipe_template.schema.json')
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == TEMPLATE_SHA256, 'template-pin')
    schema = copy.deepcopy(json.loads(raw))
    schema['$defs']['location'] = {'oneOf': [schema['$defs']['location'], {
        'type': 'object', 'required': ['kind', 'sourceSHA256', 'jsonPointer', 'sourceRecordPointer',
            'utf8ByteRange', 'sourceSpanSHA256'], 'additionalProperties': False,
        'properties': {'kind': {'const': 'native-json'},
            'sourceSHA256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
            'jsonPointer': {'type': 'string', 'pattern': '^/'},
            'sourceRecordPointer': {'type': 'string', 'pattern': '^/recipes/[0-9]+$'},
            'utf8ByteRange': {'type': 'array', 'minItems': 2, 'maxItems': 2,
                'items': {'type': 'integer', 'minimum': 0}},
            'sourceSpanSHA256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}}}]}
    # These fields describe semantic transformations, absent in a native source projection.
    for field in ('dictionaryVersion', 'mappingVersion'):
        schema['$defs']['recipe']['properties'][field] = {'const': None}
    return schema


def project_unitools_source(verified, source_language_policy=('en', 'ru')):
    """Project every valid occurrence, retaining native raw objects and both languages."""
    validate_verified(verified)
    _require(source_language_policy in (('en', 'ru'), ('ru', 'en')), 'language-policy')
    import jsonschema
    validator = jsonschema.Draft202012Validator(native_recipe_schema())
    root = verified._root.value
    records = []
    def require_field(condition, code, pointer, ordinal):
        if not condition:
            raise UnitoolsError(code, dict(verified.receipt,
                projectionHold={'code': code, 'jsonPointer': pointer, 'sourceOrdinal': ordinal}))
    for index, node in enumerate(root['recipes'].value):
        obj, rp = node.value, f'/recipes/{index}'
        names = obj['name'].value
        language = next((x for x in source_language_policy if x in names and names[x].value.strip()), None)
        require_field(language is not None, 'title-language-held', rp + '/name', index + 1)
        raw_record = verified.raw[node.start:node.end].decode('utf-8')
        notes = [{'originalText': raw_record, 'location': _location(verified, node, rp, rp),
            'provenanceRole': 'rawNativeRecord', 'originalExpressionRepresentation': 'native-json-object',
            'yieldRepresentation': 'native-json-scalar', 'sourceCountryTagIsOrigin': False}]
        for key, value in root.items():
            if key != 'recipes':
                notes.append({'originalText': verified.raw[value.start:value.end].decode('utf-8'),
                    'location': _location(verified, value, _pointer('', key), rp),
                    'provenanceRole': 'nativeRootField', 'field': key})
        ingredients, steps = [], []
        for j, ingredient in enumerate(obj['ingredients'].value):
            entry, pointer = ingredient.value, f'{rp}/ingredients/{j}'
            require_field(language in entry['name'].value and bool(entry['name'].value[language].value.strip()),
                     'ingredient-language-held', pointer + '/name/' + language, index + 1)
            quantity, unit = entry.get('quantity'), entry.get('unit')
            token = verified.raw[quantity.start:quantity.end].decode('utf-8') if quantity else None
            expression = verified.raw[ingredient.start:ingredient.end].decode('utf-8')
            ingredients.append({'ingredientLineId': f'unitools:r{index + 1}:i{j + 1}', 'order': j + 1,
                'componentIndex': 1, 'sourceNameText': entry['name'].value[language].value,
                'originalExpression': expression, 'preparationDescriptors': [], 'substitutionText': None,
                'quantity': {'rawExpression': token,
                    'rawValueLexeme': token if quantity and quantity.value is not None else None,
                    'rawUnitLexeme': unit.value if unit else None, 'interpretedValue': None,
                    'interpretedUnit': None, 'interpretationStatus': 'source-native-uninterpreted'},
                'foodIdentity': None, 'foodMatchStatus': 'unmatched-source-text',
                'location': _location(verified, ingredient, pointer, rp)})
        for k, step in enumerate(obj['steps'].value):
            values = step.value['text'].value
            require_field(language in values and bool(values[language].value.strip()),
                          'step-language-held', f'{rp}/steps/{k}/text/{language}', index + 1)
            steps.append({'order': k + 1, 'componentIndex': 1, 'originalText': values[language].value,
                'actionTerms': [], 'equipment': [], 'time': None, 'temperature': None, 'targetState': None,
                'location': _location(verified, values[language], f'{rp}/steps/{k}/text/{language}', rp)})
        servings = obj['baseServings']
        yield_record = None if servings.value is None else {
            'rawText': verified.raw[servings.start:servings.end].decode('utf-8'),
            'rawValueLexeme': verified.raw[servings.start:servings.end].decode('utf-8'),
            'rawUnitLexeme': None, 'interpretedValue': None, 'interpretedUnit': None,
            'interpretationStatus': 'source-native-uninterpreted',
            'location': _location(verified, servings, rp + '/baseServings', rp)}
        record = {'recipeTemplate': RECIPE_TEMPLATE_VERSION, 'dictionaryVersion': None, 'mappingVersion': None,
            'source': {'sourceId': SOURCE, 'sourceRecordId': obj['slug'].value, 'releaseId': REVISION,
                'countryCode': None, 'language': language, 'citationUrl': BLOB_URL,
                'attribution': root['attribution'].value,
                'licenseStatus': 'CC BY-SA 4.0; attribution/revision/share-alike; private selected operation only',
                'originalSHA256': verified.source_sha256, 'extractionSHA256': verified.source_sha256,
                'extractionParser': VERSION, 'scope': verified.selection.source_use_scope},
            'originalTitle': names[language].value, 'originalHeadingLines': [names[language].value],
            'aliases': [], 'language': language, 'region': None, 'yield': yield_record,
            'ingredientLines': ingredients, 'orderedSteps': steps,
            'components': [{'componentIndex': 1, 'title': None, 'titleLocation': None,
                            'ingredients': ingredients, 'steps': steps}],
            'sourceNotes': notes, 'nutritionAssertions': [], 'equipment': [], 'time': None,
            'temperature': None, 'sourceLocation': _location(verified, node, rp, rp),
            'identity': {'canonicalDishId': None, 'mergePerformed': False,
                         'identityStatus': 'source-scoped-distinct-record'}}
        _require(not list(validator.iter_errors(record)), 'projection-schema')
        records.append(record)
    _require(len(canonical(records)) <= MAX_PROJECTED_BYTES, 'projected-byte-bound')
    receipt = dict(verified.receipt, records=len(records), declaredDocumentLanguage=None,
        languageEvidence='per-occurrence supplied name/ingredient/step field keys only',
        sourceLanguagePolicy=list(source_language_policy), changeStatement='Native source JSON projected into source-only SQL fields; no normalization or translation')
    return records, receipt


def validate_projected_binding(verified, record, ordinal):
    node = verified._root.value['recipes'].value[ordinal - 1]
    rp = f'/recipes/{ordinal - 1}'
    _require(record['source']['sourceRecordId'] == node.value['slug'].value
        and record['sourceLocation'] == _location(verified, node, rp, rp), 'record-binding')
