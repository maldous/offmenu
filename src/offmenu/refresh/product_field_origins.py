"""Fail-closed per-datum origins for the pinned private product projector.

Consumes one record and its existing disk-backed raw database. It neither reads
new datasets nor invents coordinates. USDA callers must retain ZIP member names.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .core import RefreshError, canonical
from .field_provenance import datum_pointers, field_origin_errors
from . import product_adapters as adapters

ADAPTER_SHA256 = 'e8f223cb8a9cbe78a13f5630b4cb060a410f4cb4fa42b10875941edab46d1341'


@dataclass(frozen=True)
class Datum:
    value: object
    origin: dict


class ProductOriginEmitter:
    """Inputs: role -> {'path': cache-relative path, 'sha256': immutable pin}.

    members maps USDA table names to exact ZIP member paths, recorded during
    ingestion, not guessed from table names. CSV rows are logical data rows
    (one-based, excluding headers), not physical line numbers.
    """
    def __init__(self, context, db, inputs, *, members=None, limits=None):
        context.validate()
        self.context, self.db, self.inputs = context, db, inputs
        self.members = members or {}
        self.limits = limits or adapters.ProductLimits()
        self.limits.validate()
        if hashlib.sha256(Path(adapters.__file__).read_bytes()).hexdigest() != ADAPTER_SHA256:
            raise RefreshError('product-origin-adapter-pin-mismatch')
        self.policy = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        roles = {'off': {'products'}, 'prices': {'prices', 'locations', 'proofs'}, 'usda-files': {'archive'}}[context.source_id]
        if set(inputs) != roles:
            raise RefreshError('product-origin-input-set-mismatch')
        paths = []
        for item in inputs.values():
            path, pin = item.get('path'), item.get('sha256')
            if (not isinstance(path, str) or not path or PurePosixPath(path).is_absolute()
                    or '..' in path.split('/') or '\\' in path or PurePosixPath(path).as_posix() != path
                    or not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin)):
                raise RefreshError('product-origin-input-contract-invalid')
            paths.append(path)
        if len(set(paths)) != len(paths):
            raise RefreshError('product-origin-input-path-collision')
        self.pins = {item['path']: item['sha256'] for item in inputs.values()}

    def constant(self, value, symbol):
        return Datum(value, {'kind': 'constant', 'policySha256': self.policy, 'symbol': symbol})

    def derived(self, value, transform, *inputs):
        if not inputs:
            raise RefreshError('product-origin-derived-input-required')
        return Datum(value, {'kind': 'derived', 'policySha256': self.policy,
                             'transform': transform, 'inputs': [item.origin for item in inputs]})

    def row(self, table, key):
        found = self.db.execute('SELECT ordinal,body FROM raw WHERE tab=? AND identity=?', (table, str(key))).fetchone()
        if found is None:
            raise RefreshError('product-origin-source-row-missing')
        ordinal, body = found
        if len(body.encode()) > self.limits.max_line_bytes:
            raise RefreshError('product-origin-row-bound')
        return SourceRow(self, table, ordinal, json.loads(body))

    def optional(self, table, key):
        if key is None:
            return None
        return self.row(table, key)

    def emit(self, record):
        """Return a copy with complete fieldOrigins or reject unsupported/drifted data."""
        if record.get('provenance', {}).get('sourceId') != self.context.source_id or record['provenance'].get('releaseId') != self.context.release_id:
            raise RefreshError('product-origin-record-context-mismatch')
        key = record['provenance']['recordId']
        source = self.context.source_id
        if source == 'off':
            raw = self.row('products', key)
            tree = self.off(record['kind'], raw)
            if (record['kind'] == 'product'
                    and canonical(record['provenance'].get('sourceCategoryFields'))
                    != canonical(adapters._off_category_fields(raw.raw)[1])):
                raise RefreshError('product-origin-category-evidence-mismatch')
        elif source == 'prices':
            if record['kind'] != 'priceObservation':
                raise RefreshError('product-origin-unsupported-kind')
            tree = self.price(self.row('prices', key))
        else:
            tree = self.usda(record['kind'], self.row('food', key))
        origins = {}
        emitted_bytes = 0
        def visit(node, pointer):
            nonlocal emitted_bytes
            if isinstance(node, Datum):
                emitted_bytes += len(canonical(node.origin)) + len(pointer.encode())
                if emitted_bytes > self.limits.max_line_bytes:
                    raise RefreshError('product-origin-output-bound')
                origins[pointer] = node.origin
            elif isinstance(node, dict):
                for field, value in node.items():
                    visit(value, pointer + '/' + escape(field))
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    visit(value, pointer + '/' + str(i))
            else:
                raise RefreshError('product-origin-unmapped-datum')
        visit(tree, '/data')
        def materialize(node):
            if isinstance(node, Datum):
                return node.value
            if isinstance(node, dict):
                return {k: materialize(v) for k, v in node.items()}
            return [materialize(v) for v in node]
        if canonical(materialize(tree)) != canonical(record['data']):
            raise RefreshError('product-origin-projection-mismatch')
        result = dict(record, provenance=dict(record['provenance'], fieldOrigins=origins))
        if len(canonical(result)) > self.limits.max_line_bytes:
            raise RefreshError('product-origin-output-bound')
        if field_origin_errors(result, self.pins, policy_pins=[self.policy]):
            raise RefreshError('product-origin-coverage-invalid')
        return result

    def off(self, kind, r):
        c, d = self.constant, self.derived
        code = r.get('code')
        name = r.get('product_name') if r.raw.get('product_name') else r.get('product_name_en') if r.raw.get('product_name_en') else d(str(code.value), 'string-barcode-name-fallback', code)
        ids = [{'system': c('barcode', 'identifier-system-barcode'), 'value': d(str(code.value), 'string-barcode', code)}]
        per = r.get('nutrition_data_per')
        source_per = r.tree('nutrition_data_per', None) if 'nutrition_data_per' in r.raw else per
        numeric, unknowns, raw_basis = adapters._off_nutrient_projection(r.raw)
        basis = (d(None, 'off-basis-unestablished', per) if raw_basis is None else
                 {'amount': c(100, 'off-basis-amount'),
                  'unit': d(raw_basis['unit'], 'off-explicit-basis-unit', per),
                  'state': c('as-sold', 'off-basis-state'),
                  'qualificationStatus': c('unverified-source-assertions', 'off-unverified')})
        if kind == 'product':
            names = {key[len('product_name_'):]: r.tree(key, None) for key in r.raw
                     if re.fullmatch(r'product_name_[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*', key)}
            if 'product_name' in r.raw:
                language = r.raw.get('lang') or r.raw.get('lc')
                names.setdefault(language if isinstance(language, str) and language else 'und',
                                 r.tree('product_name', None))
            name_language = (d(r.raw.get('lang') or r.raw.get('lc'),
                               'off-name-language-source-fallback', r.get('lang'), r.get('lc'))
                             if r.raw.get('product_name') else
                             d('en', 'off-name-language-from-field-key', r.get('product_name_en'))
                             if r.raw.get('product_name_en') else c(None, 'off-name-language-unestablished'))
            if isinstance(name_language.value, (dict, list)):
                language_field = 'lang' if r.raw.get('lang') else 'lc'
                name_language = r.tree(language_field, None)
            raw_nutrients = (r.tree('nutriments', None) if 'nutriments' in r.raw else
                             c(None, 'missing-source-field:products/nutriments'))
            return {'name': name, 'names': names, 'nameLanguage': name_language,
                    'identifiers': ids, 'brand': r.get('brands'),
                    'ingredientsText': r.get('ingredients_text'), 'sourceCountryTags': r.tree('countries_tags', []),
                    'rawNutriments': raw_nutrients, 'nutritionSourceBasis': source_per,
                    'qualificationStatus': c('unverified-source-assertions', 'off-unverified'),
                    'sourceCategoryFields': {key: r.tree(key, None)
                        for key in adapters._off_category_fields(r.raw)[0]},
                    'nutritionId': d('off:nutrientProfile:' + str(code.value), 'off-nutrition-id', code)}
        if kind != 'nutrientProfile':
            raise RefreshError('product-origin-unsupported-kind')
        nutrients, dispositions = {}, {}
        raw_tree = r.tree('nutriments', None) if 'nutriments' in r.raw else c(None, 'missing-source-field:products/nutriments')
        for field, (name_key, unit) in adapters._OFF_NUTRIENTS.items():
            if name_key in numeric:
                amount = r.get('nutriments', field)
                nutrients[name_key] = {'value': d(numeric[name_key]['value'], 'finite-nonnegative-number-explicit-basis', amount, per),
                    'unit': c(unit, 'off-nutrient-unit:' + field), 'basis': basis,
                    'sourceAmount': amount, 'sourceField': c(field, 'off-nutrient-field:' + field),
                    'method': c('source', 'nutrient-method')}
            if field in unknowns:
                amount = r.get('nutriments', field)
                dispositions[field] = {
                    'state': c('unknown', 'off-optional-nutrient-unknown'),
                    'reason': d(unknowns[field]['reason'], 'off-optional-nutrient-disposition', amount, per),
                    'sourceAmount': raw_tree[field], 'sourceUnit': c(unit, 'off-nutrient-unit:' + field),
                    'sourceBasis': source_per, 'sourceField': c(field, 'off-nutrient-field:' + field)}
        if '$nutriments' in unknowns:
            dispositions['$nutriments'] = {
                'state': c('unknown', 'off-optional-nutriments-unknown'),
                'reason': d(unknowns['$nutriments']['reason'], 'off-nutriments-object-disposition', r.get('nutriments')),
                'sourceAmount': raw_tree}
        return {'foodName': name, 'identifiers': ids, 'basis': basis, 'nutrients': nutrients,
                'nutrientDispositions': dispositions, 'nutritionSourceBasis': source_per}

    def price(self, r):
        c, d = self.constant, self.derived
        location = self.optional('locations', r.raw.get('location_id'))
        join = [r.get('location_id')]
        if location:
            join.append(location.get('id'))
        def loc(field):
            v = location.get(field) if location else c(None, 'absent-location:' + field)
            return d(v.value, 'price-location-left-join:' + field, *join, v)
        tree = {'identifiers': [{'system': c('barcode', 'identifier-system-barcode'), 'value': d(str(r.raw['product_code']), 'string-barcode', r.get('product_code'))}] if r.raw.get('product_code') else [],
            'retailer': {'name': loc('osm_name'), 'externalId': d(str(r.raw.get('location_id', '')), 'price-location-id-string', r.get('location_id', default='')), 'location': loc('osm_display_name')},
            'availability': c('unknown', 'price-availability-unknown'), 'priceType': c('dated-observation', 'price-dated-observation')}
        for target, field in {'amount': 'price', 'unitPrice': 'price_per_unit', 'regularAmount': 'price_without_discount'}.items():
            n = r.get(field)
            tree[target] = d(adapters._number(n.value), 'finite-number-or-null', n)
        for target, field in {'sourceAmount': 'price', 'sourceUnitPrice': 'price_per_unit', 'sourceRegularAmount': 'price_without_discount', 'currency': 'currency', 'observedAt': 'date', 'unit': 'price_per', 'proofId': 'proof_id', 'duplicateOf': 'duplicate_of'}.items():
            tree[target] = r.get(field)
        n = r.get('price_is_discounted')
        tree['promotion'] = d(n.value if isinstance(n.value, bool) else None, 'boolean-or-null', n)
        return tree

    def usda(self, kind, r):
        c, d = self.constant, self.derived
        key = r.raw['fdc_id']
        found = self.db.execute('SELECT 1 FROM raw WHERE tab="branded_food" AND identity=?', (key,)).fetchone()
        brand = self.row('branded_food', key) if found else None
        def b(field):
            n = brand.get(field) if brand else c(None, 'absent-branded-food:' + field)
            inputs = [r.get('fdc_id')]
            if brand:
                inputs.append(brand.get('fdc_id'))
            return d(n.value, 'usda-brand-left-join:' + field, *inputs, n)
        ids = [{'system': c('USDA-FDC', 'identifier-system-usda'), 'value': r.get('fdc_id')}]
        if brand and brand.raw.get('gtin_upc'):
            ids.append({'system': c('barcode', 'identifier-system-barcode'), 'value': b('gtin_upc')})
        basis = {'amount': c(100, 'usda-basis-amount'), 'unit': c('g', 'usda-basis-unit'), 'state': c('as-described', 'usda-basis-state')}
        if kind == 'product':
            owner, name = b('brand_owner'), b('brand_name')
            serving = b('serving_size')
            return {'name': r.get('description'), 'identifiers': ids, 'brand': d(owner.value or name.value, 'usda-brand-name-fallback', owner, name),
                'dataType': r.get('data_type'), 'ingredientsText': b('ingredients'), 'marketCountry': b('market_country'),
                'serving': {'amount': d(adapters._number(serving.value), 'finite-number-or-null', serving), 'unit': b('serving_size_unit'), 'label': b('household_serving_fulltext')},
                'nutritionId': d('usda-files:nutrientProfile:' + key, 'usda-nutrition-id', r.get('fdc_id'))}
        if kind != 'nutrientProfile':
            raise RefreshError('product-origin-unsupported-kind')
        nutrients = {}
        consumed = 0
        for count, (ordinal, body) in enumerate(self.db.execute('SELECT ordinal,body FROM raw WHERE tab="food_nutrient" AND parent=? ORDER BY ordinal', (key,)), 1):
            consumed += len(body.encode())
            if count > self.limits.max_nutrients_per_food or consumed > self.limits.max_line_bytes:
                raise RefreshError('product-origin-nutrient-bound')
            n = SourceRow(self, 'food_nutrient', ordinal, json.loads(body))
            definition = self.row('nutrient', n.raw['nutrient_id'])
            joins = [r.get('fdc_id'), n.get('fdc_id'), n.get('nutrient_id'), definition.get('id')]
            def joined(value, transform='usda-nutrient-join'):
                return d(value.value, transform, *joins, value)
            name = adapters._USDA_NUTRIENTS.get(n.raw['nutrient_id'], 'usda:' + n.raw['nutrient_id'])
            if name in nutrients:
                name += ':observation:' + n.raw['id']
            amount, unit = n.get('amount'), definition.get('unit_name')
            raw = {field: joined(n.get(field)) for field in n.raw}
            nutrients[name] = {'value': d(adapters._number(amount.value), 'usda-number-joined', *joins, amount),
                'unit': d(unit.value.lower(), 'usda-unit-lowercase-joined', *joins, unit),
                'sourceAmount': joined(amount), 'sourceUnit': joined(unit), 'sourceName': joined(definition.get('name')),
                'sourceNutrientId': joined(n.get('nutrient_id')), 'sourceRowId': joined(n.get('id')), 'rawFields': raw,
                'basis': basis, 'method': c('source', 'nutrient-method')}
        return {'foodName': r.get('description'), 'identifiers': ids, 'basis': basis, 'nutrients': nutrients}


def escape(value):
    return str(value).replace('~', '~0').replace('/', '~1')


class SourceRow:
    def __init__(self, emitter, table, ordinal, raw):
        if type(ordinal) is not int or ordinal < 1 or not isinstance(raw, dict):
            raise RefreshError('product-origin-source-coordinate-invalid')
        self.e, self.table, self.ordinal, self.raw = emitter, table, ordinal, raw

    def get(self, *fields, default=None):
        value = self.raw
        pointer = ''
        for field in fields:
            pointer += '/' + escape(field)
            if not isinstance(value, dict) or field not in value:
                return self.e.constant(default, 'missing-source-field:' + self.table + pointer)
            value = value[field]
        return self.leaf(value, pointer)

    def leaf(self, value, pointer):
        usda = self.e.context.source_id == 'usda-files'
        role = 'archive' if usda else self.table
        pin = self.e.inputs[role]
        origin = {'kind': 'source', 'sourceId': self.e.context.source_id,
            'releaseId': self.e.context.release_id, 'inputPath': pin['path'], 'inputSha256': pin['sha256'],
            'sourceRecordId': str(self.ordinal), 'sourceField': pointer}
        if usda:
            member = self.e.members.get(self.table)
            if (not isinstance(member, str) or not member or PurePosixPath(member).is_absolute()
                    or '..' in member.split('/') or '\\' in member or PurePosixPath(member).stem != self.table):
                raise RefreshError('product-origin-archive-member-required')
            origin.update(sourceRecordId=member + ':row:' + str(self.ordinal),
                          archiveMember=member, table=self.table, row=self.ordinal, coordinateSystem='csv-logical-data-row')
        else:
            origin.update(sourceRecordId='line:' + str(self.ordinal), line=self.ordinal, coordinateSystem='jsonl-line-json-pointer')
        return Datum(value, origin)

    def tree(self, field, default, *, truthy=False):
        if field not in self.raw or (truthy and not self.raw[field]):
            value = default
        else:
            value = self.raw[field]
        def walk(value, pointer):
            if isinstance(value, dict):
                return {k: walk(v, pointer + '/' + escape(k)) for k, v in value.items()}
            if isinstance(value, list):
                return [walk(v, pointer + '/' + str(i)) for i, v in enumerate(value)]
            return self.leaf(value, pointer)
        return walk(value, '/' + escape(field))
