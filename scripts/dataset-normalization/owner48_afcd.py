#!/usr/bin/env python3
"""AFCD-A qualification delta; reuse normalized records and immutable XML reader.

No downloads, canonical writes, translations or semantic admission. Output is a
sidecar, not a replacement normalized corpus. Runtime dependencies are declared
beside this module; historical Git pins record lineage only.
"""
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import re
import types

XML_COMMIT = 'a8f23e73354043624de15081548972cde837a1e4'
XML_PATH = 'scripts/global-data-validation/worker-48.py'
XML_SHA = '4a4c22aae7ea395a4379ce47d537ac5417b6af2fc24077ab7fe04f92bbf554ec'
RIGHTS_COMMIT = '2bd5061f55979024cdc25626e500927daadeb9e0'
RIGHTS_PATH = 'docs/dataset-discovery/worker-06/receipt.json'
RIGHTS_SHA = '35e1cb8205a01750d6993da828f0391c97e0874a1bb31aa433f3cded60fced07'
INPUT_SHA = 'a9f139768cb6f3ae721ae384b147f4d3f2bb537d11bb2d29b20dd2bde813e2fe'
REPO = Path(__file__).resolve().parents[2]
DEPENDENCIES = Path(__file__).with_name('dependencies')
RIGHTS_DEPENDENCY_SHA = 'a8b30391c1cc4c181dd208cf44f26d188e965a54b51cc5ed52f05527c9e3128f'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def dependency_blob(name, expected):
    b = (DEPENDENCIES / name).read_bytes()
    if sha(b) != expected:
        raise ValueError('Declared dependency hash mismatch: ' + name)
    return b


def xml_reader():
    # Reuse the previously tested reader exactly; do not rebuild its normalizer.
    module = types.ModuleType('afcd_owner48_pinned_reader')
    exec(compile(dependency_blob('afcd_xml_reader.py', XML_SHA), str(DEPENDENCIES / 'afcd_xml_reader.py'), 'exec'), module.__dict__)
    return module


def input_records(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            decoded = json.loads(line)
            records = decoded if isinstance(decoded, list) else [decoded]
            for offset, record in enumerate(records):
                yield line_number, offset, record


def provenance_problem(record, food_id):
    p = record.get('provenance', {})
    if p.get('sourceId') != 'afcd' or p.get('recordId') != food_id:
        return 'source-or-original-ID-mismatch'
    if not p.get('license') or not p.get('licenseUrl') or not p.get('attribution'):
        return 'missing-rights-provenance'
    if p.get('licenseUrl') != 'https://www.foodstandards.gov.au/science-data/monitoringnutrients/afcd/datauserlicenceagreement':
        return 'unbound-rights-provenance'
    if any(p.get(k) or record.get(k) for k in ('blocked', 'provenanceBlocked', 'withdrawn')):
        return 'provenance-blocked-or-withdrawn'
    return None


def typed_source_observation(reader, row, column, header, food_unit, definitions):
    text = ' '.join(header.split())
    match = re.fullmatch(r'(.*?)\s*\((kJ|kcal|mg/gN|mg|ug|g|%T)\)', text)
    if not match:
        raise ValueError('Unknown source nutrient header: ' + header)
    label, unit = match.groups()
    basis = {'amount': 100, 'unit': food_unit, 'scope': 'source edible food'}
    if unit == '%T':
        basis = {'amount': 100, 'unit': 'g total fatty acids', 'scope': 'total fatty acids, not food mass'}
    elif unit == 'mg/gN':
        basis = {'amount': 1, 'unit': 'g nitrogen', 'scope': 'nitrogen, not food mass'}
    candidates = definitions.get((reader.key(label), reader.key(unit)), [])
    return {'source_header': header, 'source_column': column,
            'unit': unit, 'basis': basis,
            'observation': reader.observation(row['cells'].get(column)),
            'definition_candidates': candidates,
            'mapping_status': 'English-source-specific-proposal; independent acceptance pending'}


def qualify(record, reader, headers, row, food_unit, detail, definitions):
    food_id = reader.value(row, 'A')
    problem = provenance_problem(record, food_id)
    if problem:
        return None, problem
    data = record.get('data', {})
    if (data.get('foodName') != reader.value(row, 'D') or data.get('basis', {}).get('unit') != food_unit
            or data.get('basis', {}).get('amount') != 100 or record.get('countries') != ['AU']):
        return None, 'food-name-or-basis-mismatch'
    if detail['fields'].get('Food Name') != data['foodName']:
        return None, 'details-profile-identity-conflict'
    # Only source observations participate: the derived kcal entry shares its
    # source kJ column but must not overwrite that column in this comparison.
    source_columns = {}
    derived = []
    for key, item in data.get('nutrients', {}).items():
        if str(item.get('method', '')).startswith('unit-converted:'):
            derived.append({'legacy_key': key, 'definition': item.get('definition'), 'method': item.get('method')})
        else:
            source_columns[item.get('sourceColumn')] = item
    missing = []
    mismatches = []
    unknown = 0
    zero = 0
    for column, header in headers.items():
        if column in ('A', 'B', 'C', 'D'):
            continue
        # Excel column number, independent of sparse header ordering.
        number = 0
        for letter in column:
            number = number * 26 + ord(letter) - 64
        original = typed_source_observation(reader, row, column, header, food_unit, definitions)
        actual = original['observation']['value']
        unknown += actual is None
        zero += actual == 0 if actual is not None else 0
        legacy = source_columns.get(number)
        if legacy is None:
            missing.append(original)
        elif (legacy.get('value') != actual
              or str(legacy.get('unit', '')).replace('µg', 'ug') != original['unit']):
            mismatches.append({'column': column, 'legacy': legacy, 'source': original})
    if mismatches:
        return None, {'source-value-mismatch': mismatches}
    delta = {'sourceId': 'afcd', 'release': '3', 'country': 'AU',
             'category': 'generic-ingredient-composition', 'original_normalized_id': record['id'],
             'original_food_id': food_id, 'input_record_sha256': sha(encode(record)),
             'source_sheet': 'All solids & liquids per 100 g' if food_unit == 'g' else 'Liquids only per 100 mL',
             'source_row': row['number'], 'source_row_xml_sha256': row['xml_sha256'],
             'food_basis': data['basis'], 'form_source_text': data['foodName'],
             'analysed_portion': data.get('analysedPortion'), 'unanalysed_portion': data.get('unanalysedPortion'),
             'derivation': data.get('derivation'), 'sampling_details_reference': 'parent input record/data/samplingDetails',
             'food_detail_row': detail['row'], 'food_detail_xml_sha256': detail['xml_sha256'],
             'recovered_source_columns': missing,
             'derived_legacy_series_reused_without_recalculation': derived,
             'original_unknown_observations': unknown, 'original_zero_observations': zero,
             'source_method_scope': 'Food derivation and definition-level methods; no per-cell analytical method inferred',
             'original_source_date': record['provenance'].get('sourceDate'),
             'publication_date_qualification': 'Legacy sourceDate retained literally; month/path is not independent exact publication-date proof',
             'english_mapping_proposal': {'types': ['FoodPreparation', 'FoodCompositionObservation'],
                                          'recovered_property_namespace': 'urn:offmenu:property:source-field:afcd:3:column:',
                                          'identity': 'source-scoped; no ingredient/product equivalence'},
             'semantic_gold': False, 'translated_acceptance': False, 'independent_semantic_acceptance': None}
    return delta, None


def run(input_path, originals, output):
    if sha(input_path.read_bytes()) != INPUT_SHA:
        raise ValueError('Retained normalization pin mismatch')
    rights_bytes = dependency_blob('afcd_rights_evidence.json', RIGHTS_DEPENDENCY_SHA)
    rights = json.loads(rights_bytes)
    if rights['historical_receipt_sha256'] != RIGHTS_SHA:
        raise ValueError('Declared rights evidence lineage mismatch')
    reader = xml_reader()
    manifest_path = input_path.parent / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    inputs = []
    for item in manifest['sourceFiles']:
        p = originals / item['key']
        actual = sha(p.read_bytes())
        if actual != item['sha256']:
            raise ValueError('Original pin mismatch: ' + str(p))
        inputs.append({'path': str(p), 'sha256': actual, 'bytes': p.stat().st_size})
    # New namespace must be unoccupied: never overwrite earlier results.
    output.mkdir(parents=True, exist_ok=False)
    books = {n: reader.Workbook(originals / n) for n in reader.PINS}
    try:
        details = {}
        for headers, row in reader.food_rows(books['Food-Details.xlsx'], 'Food details', 2000):
            details[reader.value(row, 'A')] = {'fields': {label: reader.value(row, col) for col, label in headers.items()},
                                                       'row': row['number'], 'xml_sha256': row['xml_sha256']}
        defs = reader.definitions(books['Nutrient-details.xlsx'])
        def profiles():
            for sheet, unit in [('All solids & liquids per 100 g', 'g'), ('Liquids only per 100 mL', 'ml')]:
                for headers, row in reader.food_rows(books['Nutrient-profiles.xlsx'], sheet, 2000):
                    yield headers, row, unit
        accepted = rejected = recovered = nulls = zeros = 0
        seen = set()
        target = output / 'normalization-delta.jsonl'
        bad = output / 'excluded.jsonl'
        with target.open('wb') as good, bad.open('wb') as failures:
            for parent, original in itertools.zip_longest(input_records(input_path), profiles()):
                if parent is None or original is None:
                    raise ValueError('Retained/source row count mismatch')
                line, offset, record = parent
                headers, row, unit = original
                food_id = reader.value(row, 'A')
                if record['id'] in seen:
                    raise ValueError('Duplicate input identifier')
                seen.add(record['id'])
                delta, reason = qualify(record, reader, headers, row, unit, details[food_id], defs)
                if reason:
                    rejected += 1
                    failures.write(encode({'id': record.get('id'), 'line': line, 'reason': reason}) + b'\n')
                else:
                    delta['input_reference'] = {'path': str(input_path), 'sha256': INPUT_SHA, 'line': line, 'offset': offset}
                    good.write(encode(delta) + b'\n')
                    accepted += 1
                    recovered += len(delta['recovered_source_columns'])
                    nulls += delta['original_unknown_observations']
                    zeros += delta['original_zero_observations']
        if accepted + rejected != manifest['normalizedRows']:
            raise ValueError('Manifest count mismatch')
        ontology = {str(p.relative_to(REPO)): sha(p.read_bytes()) for p in [REPO / 'corpus/common-data-contract.json', REPO / 'corpus/common-data.schema.json', REPO / 'corpus/common-source-mappings.json']}
        report = {'packet': 'DATA-NORMALIZE-20261015-A-OWNER48', 'sourceId': 'afcd', 'release': '3', 'country': 'AU',
                  'category': 'generic-ingredient-composition', 'input': {'path': str(input_path), 'sha256': INPUT_SHA},
                  'originals': inputs, 'manifest_sha256': sha(manifest_path.read_bytes()),
                  'manifest_archiveSha256': manifest.get('archiveSha256'),
                  'manifest_digest_note': 'archiveSha256 differs from actual gzip digest; actual bytes are independently pinned by immutable worker06 receipt. No silent manifest repair.',
                  'rights': {'commit': RIGHTS_COMMIT, 'path': RIGHTS_PATH, 'sha256': RIGHTS_SHA,
                             'interpretation': rights['sourceEvidence']['licenceInterpretation'],
                             'historical_discovery_notices': rights['sourceNotices'],
                             'notices': {'licenceUrl': rights['sourceNotices']['licenceUrl'],
                                         'attribution': '© Food Standards Australia New Zealand — Australian Food Composition Database Release 3',
                                         'limitationStatement': rights['sourceNotices']['limitationStatement'],
                                         'countryNotice': rights['sourceNotices']['countryNotice'],
                                         'changes': 'Retained normalization reused by reference; missing original source columns restored in a separate English qualification sidecar. No nutrient conversion or identity equivalence accepted.'},
                             'qualification': 'local derivative/source-column staging only; no redistribution or admission approval'},
                  'reader_dependency': {'commit': XML_COMMIT, 'path': XML_PATH, 'sha256': XML_SHA},
                  'declared_dependencies': {'xml_reader': 'dependencies/afcd_xml_reader.py',
                                            'rights_evidence': 'dependencies/afcd_rights_evidence.json',
                                            'rights_evidence_sha256': RIGHTS_DEPENDENCY_SHA},
                  'counts': {'reused_input_records': accepted + rejected, 'qualified_delta_records': accepted,
                             'excluded_provenance_or_value_conflicts': rejected, 'recovered_source_observations': recovered,
                             'original_unknown_observations': nulls, 'original_zero_observations': zeros},
                  'ontology_hashes': ontology, 'ontology_status': 'selected local baseline; not owner56 frozen acceptance',
                  'owner56_frozen_hash': None, 'independent_semantic_acceptance': None,
                  'semantic_gold': False, 'translated_acceptance': False,
                  'outputs': [{'path': str(p), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size} for p in [target, bad]],
                  'worksheet_hashes': {name: book.members for name, book in books.items()},
                  'blockers': ['Owner56 exact frozen ontology hash and independent semantic acceptance required before semantic-gold or translations.',
                               'Source-column definition candidates require independent meaning/quantity/rights review; no cross-source equivalence accepted.']}
        (output / 'manifest.json').write_bytes(encode(report) + b'\n')
        return report
    finally:
        for book in books.values():
            book.close()


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, required=True)
    cli.add_argument('--originals', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    print(json.dumps(run(args.input, args.originals, args.output), indent=2))
