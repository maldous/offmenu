"""Exact retained CIQUAL 2025, private source-native extraction, version 1.

This is deliberately separate from adapter.py's synthetic nutrient crosswalk.
Public entry points admit only the nine surveyed input pins. Source cells remain
lexical strings; styles and INFOODS are retained without semantic interpretation.
No network, source copy, accepted pointer, corpus import or public export exists.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import os
import re
import shutil
import tempfile

from offmenu.refresh import core, serialization, survey, survey_ciqual as xml
from .adapter import read_bytes, runtime as parser_runtime

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = 'offmenu_ciqual/native-contract-v1.json'
SCHEMA = 'offmenu-ciqual-source-native-candidate/1'
RECORD_SCHEMA = 'offmenu-ciqual-source-native-food/1'
DEPENDENCIES = (
    'offmenu/__init__.py', 'offmenu/refresh/__init__.py',
    'offmenu/refresh/core.py', 'offmenu/refresh/serialization.py',
    'offmenu/refresh/survey.py', 'offmenu/refresh/survey_ciqual.py',
    'offmenu_ciqual/__init__.py', 'offmenu_ciqual/adapter.py',
    'offmenu_ciqual/xmlxlsx.py', 'offmenu_ciqual/source_native.py', CONTRACT_PATH,
)
OUTPUT_FILES = ('normalized.jsonl.gz', 'source-metadata.json',
                'content-manifest.json', 'build-manifest.json')
MAX_OUTPUT = 256 * 1024 * 1024
HOLDS = ('canonical-nutrient-mapping-not-performed',
         'infoods-semantic-mapping-not-performed',
         'presentation-formats-not-interpreted',
         'corpus-acceptance-not-performed', 'public-export-not-enabled',
         'country-coverage-unassessed', 'acquisition-time-unknown')


class NativeError(core.RefreshError):
    """Fixed, non-sensitive codes only."""


def _require(condition, code):
    if not condition:
        raise NativeError(code)


def contract():
    value = core.strict_json(read_bytes(ROOT / CONTRACT_PATH, 128 * 1024))
    _require(value.get('schemaVersion') == 'offmenu-ciqual-source-native-contract/1',
             'native-contract-version')
    return value


def _pins():
    return {name: {'bytes': entry[1], 'sha256': entry[2]}
            for name, entry in sorted(survey.ASSETS.items())}


def _build_pins():
    """Runtime and code changes create a different immutable build identity."""
    return {'schemaVersion': SCHEMA, 'inputPins': _pins(),
            'dependencies': {name: serialization.asset(read_bytes(ROOT / name))
                             for name in DEPENDENCIES},
            'runtime': parser_runtime(), 'serializationPolicy': serialization.POLICY}


def lexical_cell(cell, strings, ctx):
    """Retain exact decoded lexical text, cell type, presence and presentation ID.

    Numeric observations are decimal strings, not binary floats. A classifier is
    an observation of spelling; it does not assert a concentration or detection
    limit. Source-text, missing, blank, dash, ND, NT and trace stay distinct.
    """
    if cell is None:
        return {'present': False, 'cellType': None, 'raw': None,
                'styleId': None, 'qualifier': 'missing', 'decimal': None}
    kind, raw, invalid = xml._cell(cell, strings, ctx)
    _require(not invalid, 'native-invalid-cell')
    style = cell.get('s')
    _require(style is None or re.fullmatch(r'[0-9]{1,5}', style) is not None,
             'native-invalid-style-id')
    qualifier = xml._qualifier((kind, raw, False))
    result = {'present': True, 'cellType': kind, 'raw': raw, 'styleId': style,
              'qualifier': qualifier, 'decimal': None}
    if qualifier in ('numeric', 'zero'):
        result['decimal'] = raw.strip().replace(',', '.')
    elif qualifier == 'bounds':
        match = re.fullmatch(r'(<=|>=|<|>|≤|≥)\s*(.*)', raw.strip().replace(',', '.'))
        result['bound'] = {'operator': match[1], 'decimal': match[2]}
    # Invalid numeric spelling remains evidence rather than silently becoming 0.
    # OOXML numeric cells were checked by _cell; this affects text cells only.
    return result


def _sheet_rows(root, strings, expected_rows, expected_columns, ctx):
    _require(root.tag == xml.S + 'worksheet', 'native-worksheet-envelope')
    data = root.findall(xml.S + 'sheetData')
    _require(len(data) == 1 and len(data[0]) == expected_rows, 'native-row-count-drift')
    rows = []
    for row_number, row in enumerate(data[0], 1):
        _require(row.tag == xml.S + 'row' and row.get('r') == str(row_number),
                 'native-row-sequence-drift')
        cells = {}
        for cell in row:
            position = xml._coordinate(cell.get('r'))
            _require(cell.tag == xml.S + 'c' and position is not None,
                     'native-cell-position')
            r, col = position
            _require(r == row_number and 1 <= col <= expected_columns and col not in cells,
                     'native-cell-position')
            cells[col] = lexical_cell(cell, strings, ctx)
        _require(set(cells) == set(range(1, expected_columns + 1)),
                 'native-cell-shape-drift')
        rows.append(cells)
    return rows


def _xml_identities(raw, expected):
    root, _ = xml._xml(raw)
    _require(root.tag == 'TABLE' and not root.attrib and not (root.text or '').strip(),
             'native-identity-envelope')
    wanted = {x['name'] for x in expected['fields']}
    identities = {}
    for entry in root:
        _require(entry.tag == 'ALIM' and not entry.attrib and not (entry.text or '').strip()
                 and not (entry.tail or '').strip(), 'native-identity-entry')
        fields = {}
        for child in entry:
            _require(child.tag in wanted and child.tag not in fields and not len(child)
                     and not (child.tail or '').strip(), 'native-identity-field')
            # The real XML has 2,764 attributed empty scientific-name cells.
            # Preserve attributes without guessing whether they mean null/empty.
            fields[child.tag] = {'raw': child.text, 'attributes': dict(child.attrib)}
        _require(set(fields) == wanted, 'native-identity-field-set')
        raw_code = fields['alim_code']['raw']
        # Match the already verified survey's XML identity semantics exactly.
        # Keep the unmodified XML text in fields; only the join key is trimmed.
        code = raw_code.strip() if isinstance(raw_code, str) else None
        _require(code is not None and xml.CODE.fullmatch(code) is not None
                 and not fields['alim_code']['attributes'], 'native-food-id')
        _require(code not in identities, 'native-duplicate-food-id')
        _require(bool(fields['alim_nom_fr']['raw']), 'native-french-name-missing')
        identities[code] = fields
    _require(len(identities) == expected['entryCount']
             and xml._digest(identities) == expected['foodCodes']['setSha256'],
             'native-identity-set-drift')
    return identities


def _element_record(element):
    # Prefix registration is process-global in ElementTree. Store expanded
    # names and lexical attributes directly so unrelated imports cannot alter
    # candidate bytes by registering a different presentation prefix.
    return {'tag': element.tag, 'attributes': dict(element.attrib),
            'text': element.text, 'tail': element.tail,
            'children': [_element_record(child) for child in element]}


def _extract(blobs, specification):
    """Pure internal extraction. Public callers cannot supply a replacement spec."""
    expected = specification['survey']
    source_blobs = {xml.WORKBOOK: blobs['FR_WORKBOOK'], xml.IDENTITIES: blobs['FR_IDENTITIES']}
    observed = xml.survey(source_blobs)
    _require(observed == expected, 'native-survey-contract-drift')
    # Existing survey holds describe absent semantic/presentation review. The
    # exact pinned profile permits preservation of these bytes, not execution
    # or interpretation of extensions, binary members, formatting or INFOODS.
    permitted_holds = {'additional-sheets-unreviewed', 'infoods-dictionary-cell-held',
                       'nondefault-number-format-unreviewed', 'styles-present-unreviewed',
                       'unsupported-workbook-feature'}
    _require(set(observed['reasonCodes']) <= permitted_holds, 'native-unreviewed-structure')
    _require(observed['reconciliation']['exactMatch'], 'native-identity-join-drift')
    members, names, archive = xml._archive(blobs['FR_WORKBOOK'])
    ctx = xml._Context()
    relationships, tables = xml._relationships(members, names, ctx)
    strings, _ = xml._strings(members, ctx)
    _require(not ctx.reasons, 'native-unsafe-workbook')
    work = members['xl/workbook.xml']
    sheets = list(work.find(xml.S + 'sheets'))
    _require(len(sheets) == 2, 'native-sheet-count-drift')
    sheet_rows = []
    for index, sheet in enumerate(sheets):
        schema = expected['xlsx']['sheets'][index]
        _require(sheet.get('name') == schema['label'], 'native-sheet-name-drift')
        relation = tables['xl/_rels/workbook.xml.rels'][sheet.get(xml.RID)]
        _require(relation[1] == 'worksheet' and relation[3] == 'internal', 'native-sheet-target')
        stats = schema['statistics']
        sheet_rows.append(_sheet_rows(members[relation[2]], strings,
                                      stats['rows'], stats['maxColumn'], ctx))
    header = sheet_rows[0][0]
    columns = expected['xlsx']['firstSheet']['columns']
    for column in columns:
        raw = header[column['column']]['raw']
        _require(isinstance(raw, str) and core.sha(raw.encode()) == column['rawHeaderSha256']
                 and len(raw) == column['rawHeaderCharacters'], 'native-header-hash-drift')
    identities = _xml_identities(blobs['FR_IDENTITIES'], expected['xml'])
    rows, seen, counts = [], set(), Counter()
    for row_number, cells in enumerate(sheet_rows[0][1:], 2):
        code = cells[7]['raw']
        _require(isinstance(code, str) and xml.CODE.fullmatch(code) is not None,
                 'native-food-id')
        _require(code not in seen and code in identities, 'native-identity-join-drift')
        seen.add(code)
        counts.update(cell['qualifier'] for col, cell in cells.items() if 10 <= col <= 83)
        rows.append({'schemaVersion': RECORD_SCHEMA, 'kind': 'sourceNativeFood',
            'id': 'ciqual:2025:food:' + code,
            'provenance': {'sourceId': 'ciqual', 'releaseId': '2025', 'recordId': code,
                           'visibility': 'private-source-native-candidate',
                           'sourceSheet': sheets[0].get('name'), 'sourceRow': row_number},
            'data': {'cells': {str(col): value for col, value in cells.items()},
                     'identityXml': identities[code]}})
    _require(seen == set(identities), 'native-identity-join-drift')
    style_roots = [root for root in members.values() if root.tag == xml.S + 'styleSheet']
    metadata = {'schemaVersion': 'offmenu-ciqual-source-native-metadata/1',
                'sourceNotice': specification['sourceNotice'], 'policy': specification['policy'],
                'columns': [{**column, 'rawHeader': header[column['column']]['raw']}
                            for column in columns],
                'infoods': {'sheet': sheets[1].get('name'), 'semanticMapping': 'not-performed',
                            'rows': [{str(col): cell for col, cell in row.items()}
                                     for row in sheet_rows[1]]},
                'presentation': {'interpretation': 'not-performed',
                                 'styleElements': [_element_record(root) for root in style_roots],
                                 'features': expected['xlsx']['features'],
                                 'archiveRoles': archive['roles']},
                'structuralSurvey': observed}
    return rows, metadata, dict(sorted(counts.items()))


def _verify_bundle(blobs, specification):
    _require(specification['inputPins'] == _pins(), 'native-selected-pin-contract-drift')
    _require(set(blobs) == set(specification['inputPins']), 'native-nine-input-bundle-required')
    for name, pin in specification['inputPins'].items():
        _require(isinstance(blobs[name], bytes) and serialization.asset(blobs[name]) == pin,
                 'native-selected-input-pin-mismatch')


def render_verified_bundle(blobs):
    """Render exact nine-input bundle in memory. Never acquire or publish inputs."""
    specification = contract()
    _verify_bundle(blobs, specification)
    before = _build_pins()
    rows, metadata, qualifiers = _extract(blobs, specification)
    bundle_hash = core.sha(core.canonical(specification['inputPins']))
    for row in rows:
        row['provenance']['inputBundleSha256'] = bundle_hash
        row['provenance']['contractSha256'] = before['dependencies'][CONTRACT_PATH]['sha256']
    records = serialization.encode_records(rows)
    native_metadata = core.canonical(metadata)
    _require(len(records) + len(native_metadata) <= MAX_OUTPUT, 'native-output-limit')
    content = {'schemaVersion': SCHEMA, 'sourceId': 'ciqual', 'releaseId': '2025',
        'scope': 'private-source-native-candidate', 'status': 'private-source-native-extracted',
        'inputBundleSha256': bundle_hash, 'contractSha256': before['dependencies'][CONTRACT_PATH]['sha256'],
        'serializationPolicy': serialization.CONTENT_POLICY,
        'counts': {'raw': len(rows), 'extracted': len(rows), 'accepted': None,
                   'sourceColumns': len(metadata['columns']), 'sourceQuantityColumns': 74,
                   'infoodsRows': len(metadata['infoods']['rows']),
                   'qualifiers': qualifiers, 'duplicates': 0, 'excluded': 0, 'quarantined': 0},
        'canonicalArtifacts': {'normalized.jsonl': serialization.asset(records),
                               'source-metadata.json': serialization.asset(native_metadata)},
        'sourceNotice': specification['sourceNotice'], 'holds': list(HOLDS),
        'acceptance': 'not-performed', 'publicExport': 'not-enabled',
        'completeness': {'executionComplete': True, 'selectedInputSetComplete': True,
                         'selectedScopeComplete': False, 'countryCoverageComplete': False,
                         'countryCoverage': 'unassessed', 'registryComplete': False},
        'sourceCopies': 0, 'downloads': 0, 'sourceWrites': 0,
        'freshness': 'unknown', 'originalAcquiredAt': None, 'minimumReuseDays': 30}
    files = {'normalized.jsonl.gz': serialization.compress(records),
             'source-metadata.json': native_metadata, 'content-manifest.json': core.canonical(content)}
    _require(_build_pins() == before, 'native-code-changed-during-build')
    build = {'schemaVersion': 'offmenu-ciqual-source-native-build/1',
             'buildKey': core.sha(core.canonical(before)), 'buildPins': before,
             'canonicalContentSha256': core.sha(files['content-manifest.json']),
             'transportArtifacts': {name: serialization.asset(raw) for name, raw in files.items()}}
    files['build-manifest.json'] = core.canonical(build)
    return files


def _publish(files, output):
    """Use existing refresh lock, path and fsync primitives for an immutable commit.

    The adapter never replaces an existing candidate. A repeated identical build
    validates every byte and is a no-op; conflict or interrupted staging cannot
    produce a complete candidate. Staging is on the destination filesystem.
    """
    output = core.safe_path(output)
    _require(output.parent.is_dir(), 'native-output-parent-required')
    _require(set(files) == set(OUTPUT_FILES) and sum(map(len, files.values())) <= MAX_OUTPUT,
             'native-output-set-or-size')
    with core.writer_lock(output.parent / '.ciqual-source-native.lock'):
        if output.exists():
            _require(output.is_dir() and {p.name for p in output.iterdir()} == set(files),
                     'native-existing-candidate-conflict')
            for name, raw in files.items():
                _require(read_bytes(output / name, MAX_OUTPUT) == raw, 'native-existing-candidate-conflict')
            return False
        stage = Path(tempfile.mkdtemp(prefix='.ciqual-source-native-stage-', dir=output.parent))
        try:
            for name, raw in files.items():
                with (stage / name).open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            core.fsync_directory(stage)
            core.artifact_inventory(stage, files=OUTPUT_FILES, maximum=MAX_OUTPUT)
            os.rename(stage, output)
            core.fsync_directory(output.parent)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return True


def build_selected(output):
    """Local entry point, fixed read-only cache and fixed output-root boundary.

    Call from the trusted runner's normal non-root account. Only aggregate pins
    and counts leave this function; food records and dictionary stay in private local storage.
    """
    _require(os.geteuid() != 0, 'normal-user-required')
    output = core.safe_path(output)
    _require(output.parent == survey.OUTPUT and output.name.startswith('ciqual-source-native-')
             and re.fullmatch(r'ciqual-source-native-[a-zA-Z0-9_-]{1,80}', output.name) is not None,
             'native-output-location')
    specification = contract()
    _require(specification['inputPins'] == _pins(), 'native-selected-pin-contract-drift')
    blobs = {name: survey._read_asset(survey.CACHE, *entry)
             for name, entry in sorted(survey.ASSETS.items())}
    files = render_verified_bundle(blobs)
    published = _publish(files, output)
    content = core.strict_json(files['content-manifest.json'])
    build = core.strict_json(files['build-manifest.json'])
    return {'schemaVersion': 'offmenu-ciqual-source-native-receipt/1',
            'status': content['status'], 'buildKey': build['buildKey'],
            'inputBundleSha256': content['inputBundleSha256'],
            'counts': content['counts'], 'created': published,
            'artifacts': {name: serialization.asset(raw) for name, raw in files.items()},
            'inputPinsVerified': True, 'readOnlyViewVerified': True,
            'sourceContentsUploaded': False, 'sourceCopies': 0, 'downloads': 0,
            'sourceWrites': 0, 'acceptance': 'not-performed', 'publicExport': 'not-enabled',
            'countryCoverageComplete': False, 'freshness': 'unknown',
            'originalAcquiredAt': None, 'minimumReuseDays': 30}
