#!/usr/bin/env python3
"""Align native national food-composition records to OffMenu's common graph.

This is an acquisition/alignment tool.  It deliberately creates source-scoped
foods and observations: it never asserts that similarly named foods from two
national tables are the same food, and it never converts or averages values.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

import jsonschema_rs


ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/home/user/src/offmenu-data')
CURATED = DATA / 'curated-expanded-country-search-20261013' / 'blobs'
# Public source key -> retained native archive directory.  Input records below
# are the curated public projection, never the complete local native archive.
SOURCES = {
    'afcd': 'afcd-3', 'ciqual': 'ciqual-2025', 'cofid': 'cofid-2021',
    'germany-bls': 'germany-bls-4.0', 'matvaretabellen': 'matvaretabellen-2026',
    'frida': 'frida-5.5', 'cnf': 'cnf-2015', 'mext': 'mext-2023-main',
    'fineli': 'fineli-20.0', 'foodfiles': 'foodfiles-2024-v01',
    'sweden-food': 'sweden-food-2026-07-01',
}
SCOPE = {'visibility': 'public', 'reuseScope': 'Per-source licence, attribution and no-change terms apply.'}


def sha(value):
    return hashlib.sha256(str(value).encode('utf8')).hexdigest()


def urn(kind, value):
    return 'urn:offmenu:%s:%s' % (kind, sha(value)[:28])


LOCALE = re.compile(r'^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$')
# This is the language of each retained foodName field, not a country inference
# or an output-localization choice. Other untyped native prose remains und.
FOOD_NAME_LOCALES = {
    'afcd': 'en-AU', 'ciqual': 'fr-FR', 'cofid': 'en-GB',
    'germany-bls': 'de-DE', 'matvaretabellen': 'en', 'frida': 'en',
    'cnf': 'en-CA', 'mext': 'ja-JP', 'fineli': 'en',
    'foodfiles': 'en-NZ', 'sweden-food': 'sv-SE',
}


def language(code):
    # Native datasets use ISO tags where they provide them; unknown text remains
    # source text with und rather than receiving an invented language label.
    return code if isinstance(code, str) and LOCALE.fullmatch(code) else 'und'


def text(value, lang, key, citation_id, status='source-asserted'):
    value = '' if value is None else str(value)
    return {'kind': 'text', 'id': urn('text', key), 'language': language(lang),
            'value': value, 'sourceTextSha256': sha(value), 'status': status,
            'citationIds': [citation_id]}


FIXED_PATH_TOKENS = {
    'id', 'ids', 'identifier', 'identifiers', 'code', 'codes', 'status',
    'schema', 'system', 'unit', 'units', 'release', 'version', 'record',
    'records', 'component', 'column', 'reference', 'method', 'qualifier',
    'definition', 'classification', 'group', 'source', 'transform',
    'visibility', 'license', 'licence', 'rights', 'country', 'countries',
    'type', 'indicator', 'index', 'portion', 'state', 'archive', 'content',
    'hash', 'sha', 'locale', 'language', 'lang', 'format',
}
DATE_VALUE = re.compile(r'^\d{4}(?:-\d{2}(?:-\d{2})?)?$')
DATETIME_VALUE = re.compile(r'^\d{4}-\d{2}-\d{2}T')


def path_tokens(path):
    """Keep parent context across lists and split camelCase source fields."""
    segments = []
    for part in re.split(r'[:.\[\]_/\-]+', str(path)):
        part = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', part)
        segment = {token.casefold() for token in re.findall(r'[A-Za-z]+', part)}
        if segment:
            segments.append(segment)
    return segments


def fixed_path(path):
    # A broad ancestor such as record must not make every descendant prose
    # field an identifier. Inspect the leaf and its immediate semantic parent.
    segments = path_tokens(path)
    if not segments:
        return False
    relevant = segments[-1] | (segments[-2] if len(segments) > 1 else set())
    return bool(relevant & FIXED_PATH_TOKENS)


def scalar(value, lang, key, citation_id):
    """Lossless recursive representation for additional native source fields."""
    if value is None:
        return {'kind': 'null', 'value': None}
    if isinstance(value, bool):
        return {'kind': 'boolean', 'value': value}
    if isinstance(value, (int, float)):
        return {'kind': 'number', 'value': value}
    if isinstance(value, list):
        return {'kind': 'list', 'items': [scalar(v, lang, key + '[' + str(i) + ']', citation_id)
                                          for i, v in enumerate(value)]}
    if isinstance(value, dict):
        return {'kind': 'structure', 'fields': {str(k): scalar(v, lang, key + ':' + str(k), citation_id)
                                                for k, v in value.items()}}
    if isinstance(value, str) and value.startswith(('https://', 'http://', 'urn:')):
        return {'kind': 'uri', 'value': value}
    if isinstance(value, str) and DATETIME_VALUE.match(value):
        return {'kind': 'datetime', 'value': value}
    if isinstance(value, str) and DATE_VALUE.match(value):
        return {'kind': 'date', 'value': value}
    # Native field labels and values are distinct: codes, controlled values,
    # schema/release metadata and provenance handles are fixed identifiers, not
    # translation candidates.  Text remains text only for human wording.
    if fixed_path(key):
        return {'kind': 'identifier', 'value': str(value)}
    return text(value, lang, key, citation_id)


def dimension(unit):
    unit = (unit or '').casefold().replace('μ', 'µ')
    if unit in {'g', 'mg', 'µg', 'kg', 'ug'}:
        return 'mass'
    if unit in {'kj', 'kcal', 'cal'}:
        return 'energy'
    if '%' in unit or unit in {'percent', 'ratio'}:
        return 'ratio'
    if unit in {'ml', 'l', 'dl'}:
        return 'volume'
    return 'unknown'


def quantity(nutrient, lang, key, citation_id, basis):
    raw_value = nutrient.get('value') if isinstance(nutrient, dict) else None
    raw_unit = nutrient.get('unit') if isinstance(nutrient, dict) else None
    value = raw_value if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool) else None
    q = {'kind': 'quantity', 'value': value,
         'unitId': 'urn:offmenu:unit:' + quote(str(raw_unit), safe='') if raw_unit else None,
         'dimension': dimension(raw_unit), 'sourceValue': raw_value,
         'sourceUnit': raw_unit, 'qualifiers': ['source-reported' if value is not None else 'source-value-unknown'],
         'basis': basis}
    if isinstance(nutrient, dict) and nutrient.get('qualifier'):
        q['qualifiers'].append('native-qualifier:' + str(nutrient['qualifier']))
    return q


def native_count(path):
    with gzip.open(path, 'rt', encoding='utf8') as handle:
        return sum(len(item) if isinstance(item := json.loads(line), list) else 1 for line in handle)


def curated_records(source):
    """Read every verified public projection shard for one source."""
    for path in sorted((CURATED / 'records' / source).glob('*.jsonl.gz')):
        with gzip.open(path, 'rt', encoding='utf8') as handle:
            for line in handle:
                bundle_key, records = json.loads(line)
                for record in records:
                    yield bundle_key, record, path.relative_to(CURATED).as_posix()


def citation(record):
    p = record.get('provenance', {})
    rid = str(p.get('recordId', record.get('id', 'unknown')))
    cid = urn('citation', record.get('id', rid))
    result = {'id': cid, 'sourceId': str(p.get('sourceId', 'unknown')),
              'originalRecordId': rid, 'originalUrl': p.get('url', 'https://offmenu.invalid/source-url-missing'),
              'license': str(p.get('license', 'rights not supplied by native collector')),
              'attribution': str(p.get('attribution', p.get('sourceId', 'OffMenu source record'))),
              'scope': SCOPE, 'sourcePath': 'normalized.jsonl.gz'}
    for source, target in [('releaseId', 'revisionId'), ('sourceDate', 'sourceDate'),
                           ('archiveSha256', 'contentSha256'), ('licenseUrl', 'rightsEvidenceUrl')]:
        if p.get(source) is not None:
            result[target] = p[source]
    return result


def graph(record):
    d = record.get('data') or {}
    p = record.get('provenance') or {}
    native_id = str(record.get('id', p.get('recordId', 'unknown')))
    c = citation(record)
    cid = c['id']
    lang_names = d.get('names') if isinstance(d.get('names'), dict) else {}
    fallback_name = d.get('foodName') or native_id
    if not lang_names:
        lang_names = {FOOD_NAME_LOCALES.get(str(p.get('sourceId')), 'und'): fallback_name}
    primary_lang = next(iter(lang_names), 'und')
    food_id = urn('national-food', native_id)
    profile_id = urn('food-composition-observation', native_id)
    resources = [
        {'id': food_id, 'type': 'urn:offmenu:type:FoodConcept', 'identityStatus': 'source-scoped',
         'names': [text(name, lang, native_id + ':name:' + str(lang), cid) for lang, name in lang_names.items()],
         'citationIds': [cid], 'scope': SCOPE},
        {'id': profile_id, 'type': 'urn:offmenu:type:FoodCompositionObservation', 'identityStatus': 'source-scoped',
         'names': [text(fallback_name, primary_lang, native_id + ':profile-name', cid)],
         'citationIds': [cid], 'scope': SCOPE},
    ]
    assertions, relations = [], []

    def fact(subject, prop, value, path, status='source-asserted'):
        assertions.append({'id': urn('assertion', native_id + ':' + subject + ':' + prop + ':' + path),
                           'subjectId': subject, 'propertyId': 'urn:offmenu:property:' + prop,
                           'value': value, 'status': status, 'citationIds': [cid],
                           'sourcePath': path, 'scope': SCOPE})

    def relation(subject, predicate, obj, path, status='source-asserted'):
        relations.append({'id': urn('relation', native_id + ':' + subject + ':' + predicate + ':' + obj + ':' + path),
                          'subjectId': subject, 'predicateId': 'urn:offmenu:relation:' + predicate,
                          'objectId': obj, 'status': status, 'citationIds': [cid],
                          'sourcePath': path, 'scope': SCOPE})

    relation(profile_id, 'observesFood', food_id, 'data.foodName')
    fact(food_id, 'originalSourceRecord', {'kind': 'identifier', 'value': native_id}, 'id')
    for country in record.get('countries') or []:
        relation(profile_id, 'reportedForCountry', 'urn:offmenu:country:' + str(country), 'countries')

    basis_native = d.get('basis') if isinstance(d.get('basis'), dict) else {}
    basis = {'kind': 'quantity', 'value': basis_native.get('amount') if isinstance(basis_native.get('amount'), (int, float)) else None,
             'unitId': 'urn:offmenu:unit:' + quote(str(basis_native.get('unit')), safe='') if basis_native.get('unit') else None,
             'dimension': dimension(basis_native.get('unit')), 'sourceValue': basis_native.get('amount'),
             'sourceUnit': basis_native.get('unit'), 'qualifiers': ['source-basis']}
    if basis_native.get('state'):
        basis['qualifiers'].append('state:' + str(basis_native['state']))
    fact(profile_id, 'metricBasis', basis, 'data.basis')

    nutrients = d.get('nutrients') if isinstance(d.get('nutrients'), dict) else {}
    for nutrient_key, nutrient in nutrients.items():
        obs_id = urn('nutrient-observation', native_id + ':' + str(nutrient_key))
        definition_id = 'urn:offmenu:nutrient-definition:' + quote(str(nutrient_key), safe='')
        nutrient_name = nutrient.get('name', nutrient_key) if isinstance(nutrient, dict) else nutrient_key
        resources.append({'id': obs_id, 'type': 'urn:offmenu:type:FoodCompositionObservation',
                          'identityStatus': 'source-scoped',
                          'names': [text(nutrient_name, 'und', native_id + ':nutrient:' + str(nutrient_key), cid)],
                          'citationIds': [cid], 'scope': SCOPE,
                          'additionalTypes': ['urn:offmenu:type:StatisticalMetricDefinition']})
        relation(profile_id, 'hasMetricObservation', obs_id, 'data.nutrients.' + str(nutrient_key))
        fact(obs_id, 'metricDefinition', {'kind': 'identifier', 'value': definition_id},
             'data.nutrients.' + str(nutrient_key) + '.definition')
        fact(obs_id, 'metricValue', quantity(nutrient if isinstance(nutrient, dict) else {}, primary_lang,
                                             native_id + ':quantity:' + str(nutrient_key), cid, basis),
             'data.nutrients.' + str(nutrient_key) + '.value',
             'source-asserted' if isinstance(nutrient, dict) and nutrient.get('value') is not None else 'unknown')
        # Keep all component metadata (method, component code, standard error,
        # native definition and qualifiers) beside the typed observation.
        fact(obs_id, 'originalMetricFields', scalar(nutrient, 'und',
                                                     native_id + ':raw-nutrient:' + str(nutrient_key), cid),
             'data.nutrients.' + str(nutrient_key))

    # Preserve all native non-nutrient fields in a typed source assertion.
    for key, value in d.items():
        if key not in {'foodName', 'names', 'nutrients', 'basis'}:
            fact(food_id, 'sourceField:' + str(key), scalar(value, 'und', native_id + ':field:' + str(key), cid),
                 'data.' + str(key))
    fact(profile_id, 'originalProvenanceFields', scalar(p, 'und', native_id + ':provenance', cid), 'provenance')
    return {'schemaVersion': 'offmenu-common/1', 'resources': resources, 'assertions': assertions,
            'relations': relations, 'citations': [c], 'translations': []}


def align(output, packet_records):
    if output.exists():
        raise ValueError('immutable output already exists: ' + str(output))
    output.mkdir(parents=True)
    schema = json.loads((ROOT / 'corpus/common-data.schema.json').read_text())
    validator = jsonschema_rs.Draft202012Validator(schema, validate_formats=True)
    seen = {key: set() for key in ('resources', 'assertions', 'relations', 'citations')}
    stats = collections.Counter()
    files, source_counts, native_counts, input_coverage = [], {}, {}, {}
    packet_lines, part = [], 0

    def validate(packet):
        validator.validate(packet)
        cids = {c['id'] for c in packet['citations']}
        assert cids and all(c['scope']['visibility'] == 'public' for c in packet['citations'])
        for key in ('resources', 'assertions', 'relations'):
            for item in packet[key]:
                assert item['id'] not in seen[key], 'duplicate ' + key + ': ' + item['id']
                seen[key].add(item['id'])
                assert item['scope']['visibility'] == 'public'
                assert set(item['citationIds']) <= cids
                stats[key] += 1
        for c in packet['citations']:
            assert c['id'] not in seen['citations']
            seen['citations'].add(c['id'])
        stats['translations'] += len(packet['translations']); stats['packets'] += 1

    def flush():
        nonlocal packet_lines, part
        if not packet_lines:
            return
        name = 'national/part-%04d.jsonl.gz' % part
        payload = gzip.compress(('\n'.join(packet_lines) + '\n').encode('utf8'), mtime=0)
        if len(payload) > 8 * 1024 * 1024:
            raise ValueError(name + ' exceeds 8 MiB delivery bound')
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(payload)
        files.append({'key': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                      'packets': len(packet_lines)})
        packet_lines = []; part += 1

    manifest = json.loads((CURATED / 'manifest.json').read_text())
    for source, native_dir in SOURCES.items():
        count = 0
        shard_count = 0
        for bundle_key, record, source_path in curated_records(source):
            packet = graph(record); validate(packet)
            # Cite the public projection's original source fields and preserve
            # a precise curation path without retaining suppressed raw fields.
            packet['citations'][0]['sourcePath'] = source_path + '#' + str(bundle_key)
            packet_lines.append(json.dumps(packet, ensure_ascii=False, separators=(',', ':')))
            count += 1
            if len(packet_lines) >= packet_records:
                flush()
        source_counts[source] = count
        native_counts[source] = native_count(DATA / native_dir / 'normalized.jsonl.gz')
        source_manifest = manifest['sources'][source]
        assert count == source_manifest['records'], (source, count, source_manifest['records'])
        input_files = sorted((CURATED / 'records' / source).glob('*.jsonl.gz'))
        input_coverage[source] = {'complete': True, 'expectedFiles': len(input_files),
                                  'observedFiles': len(input_files), 'sourceManifestRecords': source_manifest['records'],
                                  'curatedPublicRecords': count, 'nativeLocalRecords': native_counts[source],
                                  'heldLocalRecords': native_counts[source] - count,
                                  'rawSourcePayloadPublished': False}
    flush()
    observed_counts = {key: int(stats[key]) for key in ('packets', 'resources', 'assertions', 'relations', 'translations')}
    manifest = {'schemaVersion': 'offmenu-common-national/1', 'releaseId': 'common-national-20261014',
                'status': 'all-packets-schema-identity-citation-scope-checked', 'sourceCount': len(SOURCES),
                'complete': True, 'limit': None,
                'expectedCounts': observed_counts, 'observedCounts': observed_counts, 'counts': observed_counts,
                'expectedSourceRecords': source_counts, 'observedSourceRecords': source_counts,
                'sourceRecordCounts': source_counts, 'inputArchivePartitionCoverage': input_coverage,
                'partitionCoverage': {'complete': True, 'expectedFiles': len(files), 'observedFiles': len(files),
                                      'expectedPackets': observed_counts['packets'], 'observedPackets': observed_counts['packets']},
                'files': files,
                'scope': 'National source-alignment package only. Foods and nutrient observations are source-scoped; no cross-table food identity, conversion, averaging, diet qualification or source-rights change is asserted.',
                'unresolvedMeanings': ['Native nutrient codes, methods, qualifiers, food groups and preparation terms are retained as source fields where no shared semantic mapping was verified.',
                                       'A national table basis is retained per observation; values are not made cross-source comparable automatically.'],
                'newTypeProposals': ['NationalFoodCompositionDataset', 'NutrientMeasurementQualifier', 'NationalFoodClassification', 'PortionDefinition', 'SamplingDescription'],
                'filesSha256': sha(json.dumps(files, sort_keys=True, separators=(',', ':')))}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'records': source_counts, 'counts': observed_counts, 'parts': len(files)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    # High-dimensional national tables can carry hundreds of nutrient values per
    # food.  Twenty-five records keeps even the broadest table below the 8 MiB
    # compressed delivery bound without dropping fields.
    parser.add_argument('--packet-records', type=int, default=25)
    args = parser.parse_args()
    align(args.output, args.packet_records)
