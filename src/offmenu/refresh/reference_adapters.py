"""Offline reference candidates, never production admission or rights approval.

Inputs are small retained-format buffers supplied by the bounded execution layer.
No fetching, source-code execution, clock reads, inference or publication occurs.
Original JSON objects and RDF/Turtle lexical source remain in candidate data.
"""
import copy
from datetime import datetime
import hashlib
import json
import re
import xml.etree.ElementTree as ET

CONTRACTS = {
    'wikidata-food-businesses': ('2026-10-13-direct-types', 'sparql-results-json', 'f5ea7f7675dd31edef2a3b65122f1853f0c2e486'),
    'wikibooks': ('2026-10-13-live', 'wikibooks-revisions-json', '5542c028f49ba35da2171809ee74f7a64cb3e9da'),
    'foodon': ('2026-09-20', 'foodon-rdf-xml', 'fa232aabeb8162e2bbbd51ef71775e4b46193cb2'),
    'qudt-measurement-definitions': ('qudt-measurement-definitions-3.5.2-20261014', 'qudt-unit-turtle-blocks', '73a0dcbeea567f478fcf394870bc03ebbd728127'),
    'overture-food-places': ('2026-09-23.1', 'overture-place-json-projection', '831a3123936c88a6dcddffdf12486bbd83477797'),
}
UNSUPPORTED = {'dietary-guidelines': 'No reviewed retained directory parser or record schema; no certification inferred.'}
ROLES = {'Q1252971': 'food-manufacturer', 'Q18043413': 'supermarket-chain', 'Q132777643': 'grocery-store-chain'}
QUDT_UNITS = frozenset('GM KiloGM MilliGM MicroGM LB OZ L MilliL SEC MIN HR DAY M CentiM IN FT DEG_C K J KiloJ CAL_15DEG_C CAL_15_DEG_C CAL_20DEG_C CAL_IT CAL_MEAN CAL_TH KiloCAL KiloCAL_IT KiloCAL_Mean KiloCAL_TH COUNT NUM ONE PERCENT CUP CUP_US TBSP TSP OZ_VOL_UK OZ_VOL_US GAL_IMP GAL_UK GAL_US GAL_US_DRY PINT PINT_UK PINT_US PINT_US_DRY QT_UK QT_US QT_US_DRY BU_UK BU_US BU_US_DRY PK_UK PK_US_DRY'.split())
RDF = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
OWL = '{http://www.w3.org/2002/07/owl#}'
MAX_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 8 * 1024 * 1024
MAX_CANDIDATE_BYTES = 64 * 1024 * 1024
MAX_RECORDS = 100_000


class ReferenceFormatError(ValueError):
    """Unsupported/malformed source must not produce accepted candidates."""


def _require(condition, reason):
    if not condition:
        raise ReferenceFormatError(reason)


def _text(value, name):
    _require(isinstance(value, str) and bool(value.strip()), 'missing-or-invalid-' + name)
    return value


def _json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate-json-key')
            result[key] = value
        return result
    try:
        return json.loads(payload, object_pairs_hook=pairs,
                          parse_float=lambda value: {"sourceNumberLexical": value},
                          parse_constant=lambda _: (_ for _ in ()).throw(ReferenceFormatError('nonfinite-json-number')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceFormatError('invalid-source-json') from exc


def _binding(row, key, required=True):
    value = row.get(key)
    if value is None and not required:
        return None
    _require(isinstance(value, dict), 'invalid-sparql-binding-' + key)
    return _text(value.get('value'), key)



def _namespace_declarations(payload):
    from xml.parsers import expat
    parser = expat.ParserCreate(namespace_separator='}')
    namespaces = {}
    parser.StartNamespaceDeclHandler = lambda prefix, uri: namespaces.setdefault(prefix or '', uri)
    parser.Parse(payload, True)
    return namespaces


def _xml_children(payload):
    """Exact byte spans of root element children, without XML reserialization."""
    from xml.parsers import expat
    parser = expat.ParserCreate()
    depth = 0
    start = 0
    spans = []

    def begin(name, attrs):
        nonlocal depth, start
        depth += 1
        if depth == 2:
            start = parser.CurrentByteIndex

    def end(name):
        nonlocal depth
        if depth == 2:
            position = parser.CurrentByteIndex
            closing = ('</' + name).encode()
            actual_close = payload.startswith(closing, position) and payload[position + len(closing):position + len(closing) + 1] in (b'>', b' ', b'\t', b'\n', b'\r')
            finish = payload.index(b'>', position) + 1 if actual_close else position
            spans.append(payload[start:finish])
        depth -= 1

    parser.StartElementHandler = begin
    parser.EndElementHandler = end
    parser.Parse(payload, True)
    return spans


def normalize_reference(source_id, release_id, payload, *, acquired_at):
    """Return deterministic reference candidates for one explicit retained format.

The caller must separately verify input hashes, custody, rights, source scope,
completeness and expected counts. No output here is automatically qualified.
"""
    _require(source_id in CONTRACTS, 'unsupported-reference-source')
    _require(release_id == CONTRACTS[source_id][0], 'unsupported-reference-release')
    _require(isinstance(payload, bytes) and len(payload) <= MAX_BYTES, 'reference-input-limit-or-type')
    try:
        stamp = datetime.fromisoformat(acquired_at.replace('Z', '+00:00'))
        _require(stamp.tzinfo is not None, 'acquisition-time-zone-required')
    except (ValueError, AttributeError, TypeError) as exc:
        raise ReferenceFormatError('invalid-acquisition-time') from exc
    sha = hashlib.sha256(payload).hexdigest()
    rows = []
    output_bytes = 0

    def emit(key, kind, data, licenses, url, rights_url, source_path):
        nonlocal output_bytes
        key = _text(key, 'record-id')
        record = {'schemaVersion': '1.0', 'kind': kind,
                     'id': source_id + ':' + kind + ':' + key,
                     'countries': [],
                     'provenance': {'sourceId': source_id, 'recordId': key,
                                    'releaseId': release_id, 'fetchedAt': acquired_at,
                                    'archiveSha256': sha, 'sourcePath': source_path,
                                    'sourceFormat': CONTRACTS[source_id][1],
                                    'historicalHandlerGitBlob': CONTRACTS[source_id][2],
                                    'licenses': sorted(set(licenses)), 'url': url,
                                    'licenseUrl': rights_url,
                                    'transform': 'offmenu-offline-reference/1',
                                    'rightsEvidenceStatus': 'requires-operation-specific-review',
                                    'authorizedOperations': []},
                     'data': {**data, 'reviewStatus': 'source-reference-unreviewed',
                              'automaticPlanningEligible': False}}
        encoded_size = len(candidate_bytes([record]))
        _require(encoded_size <= MAX_RECORD_BYTES, 'reference-record-output-limit')
        output_bytes += encoded_size
        _require(output_bytes <= MAX_CANDIDATE_BYTES and len(rows) < MAX_RECORDS, 'reference-total-output-limit')
        rows.append(record)

    if source_id == 'wikidata-food-businesses':
        document = _json(payload)
        _require(isinstance(document, dict) and isinstance(document.get('results'), dict), 'invalid-sparql-results')
        bindings = document['results'].get('bindings')
        _require(isinstance(bindings, list), 'invalid-sparql-bindings')
        grouped = {}
        for index, binding in enumerate(bindings):
            _require(isinstance(binding, dict), 'invalid-sparql-row')
            uri = _binding(binding, 'entity')
            _require(bool(re.fullmatch(r'https?://www\.wikidata\.org/entity/Q[1-9][0-9]*', uri)), 'invalid-wikidata-entity')
            role_uri = _binding(binding, 'type')
            _require(bool(re.fullmatch(r'https?://www\.wikidata\.org/entity/Q[1-9][0-9]*', role_uri)), 'invalid-wikidata-type')
            role = ROLES.get(role_uri.rsplit('/', 1)[-1])
            _require(role is not None, 'unsupported-business-type')
            label = _binding(binding, 'entityLabel', False)
            entry = grouped.setdefault(uri.rsplit('/', 1)[-1], {'roles': set(), 'names': set(), 'originalBindings': [], 'sourceRows': []})
            entry['roles'].add(role)
            if label:
                entry['names'].add(label)
            entry['originalBindings'].append(copy.deepcopy(binding))
            entry['sourceRows'].append(index)
        for key, data in sorted(grouped.items()):
            data['roles'] = sorted(data['roles'])
            data['names'] = sorted(data['names'])
            data['ownershipVerified'] = False
            data['countryBasis'] = 'Original P17 references retained; no country/market mapping inferred.'
            emit(key, 'organization', data, ['CC0-1.0'], 'https://www.wikidata.org/wiki/' + key,
                 'https://www.wikidata.org/wiki/Wikidata:Licensing', 'results.bindings')
    elif source_id == 'wikibooks':
        pages = _json(payload)
        _require(isinstance(pages, list), 'expected-retained-wikibooks-page-array')
        for index, page in enumerate(pages):
            _require(isinstance(page, dict) and type(page.get('pageid')) is int and page['pageid'] > 0, 'invalid-wikibooks-page')
            _require(not page.get('missing') and isinstance(page.get('revisions'), list) and len(page['revisions']) == 1, 'missing-or-ambiguous-wikibooks-revision')
            title = _text(page.get('title'), 'page-title')
            _require(title.startswith('Cookbook:'), 'unsupported-wikibooks-namespace')
            revision = page['revisions'][0]
            _require(isinstance(revision, dict) and type(revision.get('revid')) is int and revision['revid'] > 0, 'invalid-wikibooks-revision')
            main = (revision.get('slots') or {}).get('main')
            _require(isinstance(main, dict) and isinstance(main.get('content'), str), 'missing-wikibooks-content')
            from urllib.parse import quote
            url = 'https://en.wikibooks.org/wiki/' + quote(title.replace(' ', '_'), safe=':()/')
            emit(str(page['pageid']), 'recipe-discovery-reference',
                 {'name': title.removeprefix('Cookbook:'), 'originalSource': copy.deepcopy(page),
                  'originalText': main['content'], 'revisionId': revision['revid'],
                  'historyUrl': url + '?action=history', 'quantitiesResolved': False},
                 ['CC-BY-SA-4.0'], url, 'https://en.wikibooks.org/wiki/Wikibooks:Copyrights', str(index))
    elif source_id == 'foodon':
        _require(b'<!DOCTYPE' not in payload.upper() and b'<!ENTITY' not in payload.upper(), 'xml-declaration-rejected')
        try:
            text = payload.decode('utf-8')
            root = ET.fromstring(text)
        except (UnicodeError, ET.ParseError) as exc:
            raise ReferenceFormatError('invalid-foodon-rdf-xml') from exc
        _require(root.tag == RDF + 'RDF', 'expected-rdf-root')
        spans = _xml_children(payload)
        namespaces = _namespace_declarations(payload)
        for index, node in enumerate(root):
            identity = node.get(RDF + 'about', '')
            if node.tag != OWL + 'Class' or not re.fullmatch(r'https?://purl\.obolibrary\.org/obo/FOODON_[0-9]+', identity):
                continue
            # Exact child bytes retain entities, number spelling, whitespace and nested expressions.
            emit(identity, 'ontology-class', {'originalXml': spans[index].decode('utf-8'),
                 'namespaceDeclarations': namespaces,
                 'elementIndex': index, 'originalAttributes': dict(node.attrib),
                 'definitionXml': ET.tostring(node, encoding='unicode'),
                 'reuseScope': 'FoodOn own namespace only; imported classes remain references.',
                 'foodIdentityEquivalenceInferred': False}, ['CC-BY-4.0'], identity,
                 'https://github.com/FoodOntology/foodon/blob/master/LICENSE.txt', str(index))
    elif source_id == 'qudt-measurement-definitions':
        try:
            text = payload.decode('utf-8')
        except UnicodeError as exc:
            raise ReferenceFormatError('invalid-qudt-encoding') from exc
        _require(bool(re.search(r'@prefix\s+unit:\s*<http://qudt.org/vocab/unit/>\s*\.', text)), 'qudt-unit-prefix-required')
        pattern = re.compile(r'(?ms)^unit:([A-Za-z0-9_-]+)\s+(.*?)(?=^unit:[A-Za-z0-9_-]+\s|\Z)')
        matches = list(pattern.finditer(text))
        _require(bool(matches), 'unsupported-qudt-turtle-layout')
        preamble = text[:matches[0].start()]
        for match in matches:
            token = match.group(1)
            if token not in QUDT_UNITS:
                continue
            block = match.group(0)
            _require(block.rstrip().endswith('.'), 'unterminated-qudt-unit-block')
            emit(token, 'unit-reference', {'originalTurtleBlock': block,
                 'originalTurtlePreamble': preamble,
                 'interpretation': 'Bounded named-unit lexical reference only; no conversion execution or RDF reasoning.',
                 'densityOrYieldEquivalenceInferred': False}, ['CC-BY-4.0'],
                 'http://qudt.org/vocab/unit/' + token,
                 'https://github.com/qudt/qudt-public-repo/blob/v3.5.2/LICENSE.md', token)
    else:
        places = _json(payload)
        _require(isinstance(places, list), 'expected-overture-projection-array')
        allowed = {'id', 'names', 'taxonomy', 'basic_category', 'sources', 'addresses', 'confidence', 'operating_status', 'version'}
        for index, place in enumerate(places):
            _require(isinstance(place, dict) and set(place) <= allowed, 'unsupported-overture-projection-fields')
            taxonomy = place.get('taxonomy') or {}
            _require(isinstance(taxonomy, dict) and isinstance(taxonomy.get('hierarchy'), list), 'invalid-overture-taxonomy')
            hierarchy = taxonomy['hierarchy']
            _require(all(isinstance(x, str) for x in hierarchy), 'invalid-overture-taxonomy-value')
            if not set(hierarchy) & {'food_and_drink', 'food_and_beverage_store', 'farmers_market', 'farm'} or set(hierarchy) & {'tobacco_shop', 'vape_shop', 'e-cigarette_shop', 'smoke_shop'}:
                continue
            names = place.get('names')
            _require(isinstance(names, dict), 'invalid-overture-names')
            name = _text(names.get('primary'), 'place-name')
            sources = place.get('sources')
            _require(isinstance(sources, list) and bool(sources), 'missing-overture-provider-rights')
            licenses = []
            for provider in sources:
                _require(isinstance(provider, dict) and provider.get('license') in {'CDLA-Permissive-2.0', 'Apache-2.0', 'CC0-1.0'}, 'unreviewed-overture-provider-rights')
                licenses.append(provider['license'])
            emit(place.get('id'), 'place-reference', {'name': name, 'originalSource': copy.deepcopy(place),
                 'sourceProviders': copy.deepcopy(sources), 'ownershipVerified': False,
                 'inventoryAvailability': 'unknown', 'menuCoverage': False}, licenses,
                 'https://docs.overturemaps.org/guides/places/',
                 'https://docs.overturemaps.org/attribution/#places', str(index))
    identities = [row['id'] for row in rows]
    _require(len(identities) == len(set(identities)), 'duplicate-reference-identity')
    _require(bool(rows), 'no-supported-reference-records')
    return sorted(rows, key=lambda row: row['id'])


def candidate_bytes(records):
    """Shared offline candidate.jsonl singleton-packet serialization."""
    return b''.join((json.dumps([row], ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8') for row in records)


def candidate_manifest(source_id, release_id, records, *, acquired_at, input_files,
                       rights_evidence_sha256, scope_evidence_sha256):
    """Describe candidates using external evidence pins; this grants no rights."""
    _require(source_id in CONTRACTS and release_id == CONTRACTS[source_id][0], 'unsupported-reference-release')
    _require(bool(records), 'no-supported-reference-records')
    _require(isinstance(input_files, list) and bool(input_files), 'reference-input-pins-required')
    names = set()
    for item in input_files:
        _require(isinstance(item, dict) and set(item) == {'path', 'bytes', 'sha256'}, 'invalid-reference-input-pin')
        path = item['path']
        _require(isinstance(path, str) and bool(path) and not path.startswith('/') and '\\' not in path and all(x not in ('', '.', '..') for x in path.split('/')), 'invalid-reference-input-path')
        _require(path not in names, 'duplicate-reference-input-path')
        names.add(path)
        _require(type(item['bytes']) is int and 0 <= item['bytes'] <= MAX_BYTES, 'invalid-reference-input-size')
        _require(isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'invalid-reference-input-hash')
    _require(sum(x['bytes'] for x in input_files) <= MAX_BYTES, 'reference-input-limit')
    for digest in (rights_evidence_sha256, scope_evidence_sha256):
        _require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'reference-review-evidence-pin-required')
    for row in records:
        provenance = row.get('provenance', {})
        _require(provenance.get('sourceId') == source_id and provenance.get('releaseId') == release_id and provenance.get('fetchedAt') == acquired_at, 'reference-record-manifest-mismatch')
        _require(provenance.get('archiveSha256') in {item['sha256'] for item in input_files}, 'reference-record-input-pin-mismatch')
    _require(len({row['id'] for row in records}) == len(records), 'duplicate-reference-identity')
    content = candidate_bytes(records)
    return {'sourceId': source_id, 'releaseId': release_id, 'acquiredAt': acquired_at,
            'candidateSha256': hashlib.sha256(content).hexdigest(), 'candidateBytes': len(content),
            'normalizedRecords': len(records), 'inputFiles': sorted(copy.deepcopy(input_files), key=lambda x: x['path']),
            'rightsEvidenceSha256': rights_evidence_sha256, 'scopeEvidenceSha256': scope_evidence_sha256,
            'schemaVersion': 'offmenu-reference-candidates/1', 'status': 'candidate-only',
            'productionAdmission': False}


def reference_semantics(record):
    """Reviewed native-reference guard; never a curated/common completion claim."""
    errors = []
    provenance = record.get('provenance', {})
    data = record.get('data', {})
    source = provenance.get('sourceId')
    expected = {'wikidata-food-businesses': 'organization',
                'wikibooks': 'recipe-discovery-reference', 'foodon': 'ontology-class',
                'qudt-measurement-definitions': 'unit-reference', 'overture-food-places': 'place-reference'}
    if source not in CONTRACTS or record.get('kind') != expected.get(source):
        return ['reference-source-kind-invalid']
    if provenance.get('releaseId') != CONTRACTS[source][0] or provenance.get('sourceFormat') != CONTRACTS[source][1] or provenance.get('historicalHandlerGitBlob') != CONTRACTS[source][2]:
        errors.append('reference-release-format-pin-mismatch')
    if provenance.get('authorizedOperations') != [] or provenance.get('rightsEvidenceStatus') != 'requires-operation-specific-review':
        errors.append('reference-self-authorized-rights')
    if data.get('automaticPlanningEligible') is not False or data.get('reviewStatus') != 'source-reference-unreviewed' or record.get('countries') != []:
        errors.append('reference-inferred-qualification')
    if record.get('id') != source + ':' + expected[source] + ':' + str(provenance.get('recordId')):
        errors.append('reference-identity-mismatch')
    exact_licenses = {'wikidata-food-businesses': ['CC0-1.0'], 'wikibooks': ['CC-BY-SA-4.0'], 'foodon': ['CC-BY-4.0'], 'qudt-measurement-definitions': ['CC-BY-4.0']}
    if source in exact_licenses and provenance.get('licenses') != exact_licenses[source]:
        errors.append('reference-license-mismatch')
    if source == 'wikidata-food-businesses' and (data.get('ownershipVerified') is not False or not data.get('roles') or any(x not in ROLES.values() for x in data.get('roles', []))):
        errors.append('reference-business-roles-invalid')
    if source == 'wikibooks' and data.get('quantitiesResolved') is not False:
        errors.append('reference-recipe-unresolved-quantities')
    if source == 'foodon' and data.get('foodIdentityEquivalenceInferred') is not False:
        errors.append('reference-ontology-equivalence-inferred')
    if source == 'qudt-measurement-definitions' and data.get('densityOrYieldEquivalenceInferred') is not False:
        errors.append('reference-unit-equivalence-inferred')
    if source == 'overture-food-places':
        providers = data.get('sourceProviders')
        if not isinstance(providers, list) or not providers or any(not isinstance(p, dict) or p.get('license') not in {'CDLA-Permissive-2.0', 'Apache-2.0', 'CC0-1.0'} for p in providers):
            errors.append('reference-provider-rights-invalid')
        elif provenance.get('licenses') != sorted({p['license'] for p in providers}) or (data.get('originalSource') or {}).get('sources') != providers:
            errors.append('reference-provider-rights-mismatch')
        if data.get('ownershipVerified') is not False or data.get('inventoryAvailability') != 'unknown' or data.get('menuCoverage') is not False:
            errors.append('reference-place-inference')
    return sorted(set(errors))
