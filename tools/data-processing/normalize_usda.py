#!/usr/bin/env python3
"""Project every FDC food and nutrient from a reconciled CSV release.

Original relational fields remain in source.sqlite and the original archive.
Streaming merge joins bound memory; no first-N-record stopping rule.
"""
import argparse
import gzip
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect_usda.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
CANONICAL = {'1008': ('energy', 'kcal'), '1003': ('protein', 'g'), '1004': ('fat', 'g'),
             '1005': ('carbohydrate', 'g'), '2000': ('sugars', 'g'), '1079': ('fibre', 'g'),
             '1093': ('sodium', 'mg'), '1258': ('saturatedFat', 'g'), '1087': ('calcium', 'mg'),
             '1089': ('iron', 'mg'), '1092': ('potassium', 'mg'), '1162': ('vitaminC', 'mg')}


def numeric(raw):
    if raw in ('', None):
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError('Non-finite source value')
    return value


def normalize(directory):
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['status'] not in ('full scope reconciled', 'normalized'):
        raise ValueError('Reconcile full source first')
    target = directory / 'normalized.jsonl.gz'
    if manifest['status'] == 'normalized' and target.exists():
        if collector.digest(target) != manifest['normalizedSha256']:
            raise ValueError('Normalized checksum mismatch')
        return manifest
    db = sqlite3.connect(directory / 'source.sqlite')
    db.row_factory = sqlite3.Row
    for table, column in [('food', 'fdc_id'), ('branded_food', 'fdc_id'), ('food_nutrient', 'fdc_id'),
                          ('nutrient', 'id'), ('food_nutrient_derivation', 'id'), ('food_portion', 'fdc_id')]:
        print('Indexing ' + table, flush=True)
        db.execute(f'CREATE INDEX IF NOT EXISTS "offmenu_{table}_{column}" ON "{table}"("{column}")')
        db.commit()
    definitions = {r['id']: dict(r) for r in db.execute('SELECT * FROM nutrient')}
    derivations = {r['id']: dict(r) for r in db.execute('SELECT * FROM food_nutrient_derivation')}
    foods = db.execute('SELECT f.*,b.brand_owner,b.brand_name,b.gtin_upc,b.ingredients,b.market_country,'
                       'b.serving_size,b.serving_size_unit,b.household_serving_fulltext,b.preparation_state_code '
                       'FROM food f LEFT JOIN branded_food b ON f.fdc_id=b.fdc_id ORDER BY f.fdc_id')
    nutrient_iterator = iter(db.execute('SELECT * FROM food_nutrient ORDER BY fdc_id,_ingestion_row'))
    current = next(nutrient_iterator, None)
    now = datetime.now(timezone.utc).isoformat()
    basis = {'amount': 100, 'unit': 'g', 'state': 'as-described'}
    pending = target.with_suffix('.partial')
    count = nutrients_count = duplicate_nutrients = orphan_nutrients = 0
    types = {}
    with gzip.open(pending, 'wt', encoding='utf-8', compresslevel=1) as out:
        for food in foods:
            key = food['fdc_id']
            nutrients = {}
            while current is not None and current['fdc_id'] < key:
                orphan_nutrients += 1
                current = next(nutrient_iterator, None)
            while current is not None and current['fdc_id'] == key:
                definition = definitions.get(current['nutrient_id'])
                if not definition:
                    raise ValueError('Unknown nutrient definition')
                nutrient_key, unit = CANONICAL.get(current['nutrient_id'], ('usda:' + current['nutrient_id'], definition['unit_name'].lower()))
                original_unit = definition['unit_name'].lower()
                value = numeric(current['amount'])
                if original_unit != unit and value is not None:
                    if original_unit == 'g' and unit == 'mg':
                        value *= 1000
                    elif original_unit == 'mg' and unit == 'g':
                        value /= 1000
                    else:
                        value = None
                n = {'value': value, 'unit': unit, 'basis': basis,
                     'method': derivations.get(current['derivation_id'], {}).get('description', 'source'),
                     'definition': 'USDA-FDC:' + current['nutrient_id'], 'sourceNutrientId': current['nutrient_id'],
                     'sourceName': definition['name'], 'sourceAmount': current['amount'], 'sourceUnit': original_unit,
                     'sourceRowId': current['id'], 'rawFields': dict(current)}
                # Preserve multiple observations; no last-write-wins nutrient loss.
                if nutrient_key in nutrients:
                    duplicate_nutrients += 1
                    nutrient_key = nutrient_key + ':observation:' + current['id']
                nutrients[nutrient_key] = n
                nutrients_count += 1
                current = next(nutrient_iterator, None)
            identifiers = [{'system': 'USDA-FDC', 'value': key}]
            if food['gtin_upc']:
                identifiers.append({'system': 'barcode', 'value': food['gtin_upc']})
            provenance = {'sourceId': 'usda-files', 'recordId': key, 'url': manifest['url'],
                'license': manifest['license'], 'attribution': manifest['attribution'], 'visibility': 'public',
                'fetchedAt': now, 'sourceDate': food['publication_date'] or None,
                'releaseId': directory.name, 'archiveSha256': manifest['archiveSha256'],
                'transform': 'offmenu-usda-csv/1', 'originalTables': 'source.sqlite',
                'rights': 'USDA FoodData Central public domain / CC0; independent source partition'}
            common = {'schemaVersion': '1.0', 'countries': ['US'], 'provenance': provenance}
            product = {**common, 'kind': 'product', 'id': 'usda-files:product:' + key,
                'data': {'name': food['description'], 'identifiers': identifiers, 'brand': food['brand_owner'] or food['brand_name'],
                'dataType': food['data_type'], 'marketCountry': food['market_country'], 'ingredientsText': food['ingredients'],
                'serving': {'amount': numeric(food['serving_size']), 'unit': food['serving_size_unit'], 'label': food['household_serving_fulltext']},
                'preparationState': food['preparation_state_code'], 'nutritionId': 'usda-files:nutrientProfile:' + key}}
            profile = {**common, 'kind': 'nutrientProfile', 'id': 'usda-files:nutrientProfile:' + key,
                'data': {'foodName': food['description'], 'identifiers': identifiers, 'basis': basis, 'nutrients': nutrients}}
            out.write(json.dumps([product, profile], ensure_ascii=False, separators=(',', ':')) + '\n')
            count += 1
            types[food['data_type']] = types.get(food['data_type'], 0) + 1
            if count % 100000 == 0:
                print(json.dumps({'foods': count, 'nutrients': nutrients_count}), flush=True)
        while current is not None:
            orphan_nutrients += 1
            current = next(nutrient_iterator, None)
    if count != manifest['tables']['food']['raw'] or nutrients_count + orphan_nutrients != manifest['tables']['food_nutrient']['raw']:
        raise ValueError('Projection reconciliation failed')
    if orphan_nutrients:
        raise ValueError('Orphan nutrients require review: ' + str(orphan_nutrients))
    pending.replace(target)
    manifest.update(status='normalized', normalizedRows=count * 2, foodsByType=types,
                    nutrientObservations=nutrients_count, duplicateNutrientObservationsPreserved=duplicate_nutrients,
                    normalizedSha256=collector.digest(target), normalizedBytes=target.stat().st_size)
    collector.save(manifest_path, manifest)
    db.close()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_directory', type=Path)
    result = normalize(parser.parse_args().release_directory)
    print(json.dumps({k: result[k] for k in ['status', 'normalizedRows', 'foodsByType', 'nutrientObservations']}))
