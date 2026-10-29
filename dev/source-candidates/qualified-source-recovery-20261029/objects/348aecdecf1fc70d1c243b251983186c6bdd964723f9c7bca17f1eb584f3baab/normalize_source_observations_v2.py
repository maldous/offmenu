#!/usr/bin/env python3
"""Versioned private source normalization, never package admission or old-output mutation.

Consumes one bounded source-evidence object on stdin and emits one v2 object to
stdout. No discovery, acquisition, filesystem writes or graph publication.
"""
import argparse
import copy
import hashlib
import json
import math
import sys

VERSION = 'offmenu-source-observations/2'
QUALIFIED_ADAPTERS = {
    'fdc': '12a557de0fb9d25040d139d292baadec91dc60e2',
    'ciqual': 'cb3a05581c88ffa3025e7426a4f2d50f5ae0326b',
    'bls': '94a45cc275879f869ceae9508679307f9ba4b99f',
    'cofid': '38f8aedee9c8d30950db1b6d2ae5e82b520e894b',
    'off': '0fa3614f5a7b85a5d3b95999d15c7e168bbc1837',
    'prices': '9450bb7ade9ba0110290b23e071cc03a83b11ee3',
    'recipes': '88e3ca4164c82d8da06d51d8a6265beb0a0cbf31',
    'businesses': 'bf63dd2f0f88928de31ec35eff93e16765f4c6a5',
}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def observation(component, metric, quarantined=False):
    # No unit conversion, denominator fallback, zero coercion or qualifier loss.
    raw = copy.deepcopy(metric)
    value = metric.get('value')
    qualifier = metric.get('qualifier')
    if qualifier not in {'source', 'numeric', 'numeric-zero', None}:
        value = None
    if not numeric(value):
        value = None
    return {'component': component, 'value': value, 'unitExpression': metric.get('unit'),
            'basis': copy.deepcopy(metric.get('basis')), 'qualifier': qualifier,
            'limit': metric.get('limit'), 'original': metric.get('original', metric.get('originalText', metric.get('rawValue'))),
            'zeroIsAbsence': False, 'quarantined': quarantined,
            'conversionEligible': False, 'sourceObservation': raw}


def business_packet(record):
    """Carry original public RDF assertions into the actual common packet path."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('v2_places', Path(__file__).with_name('align-places-common.py'))
    places = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(places)
    bindings = record['localValidationEvidence']['queryBindings']
    if not isinstance(bindings, list):
        raise ValueError('original RDF binding list required')
    row = copy.deepcopy(record)
    if row.get('kind') != 'organization':
        raise ValueError('business rows must remain organizations')
    places.validate_row(row)
    row['data']['sourceQueryBindings'] = copy.deepcopy(bindings)
    resource, assertions, citation = places.packet_record(row)
    # Keep names derived from actual language-tagged source literals, not a
    # fabricated translation. Original RDF term metadata remains in assertions.
    for index, binding in enumerate(bindings):
        term = binding.get('entityLabel', {})
        value, language = term.get('value'), term.get('xml:lang')
        if term.get('type') != 'literal' or not isinstance(value, str) or not value or not isinstance(language, str) or not language:
            continue
        resource['names'].append({'kind': 'text', 'id': places.stable_id('query-label', row['provenance']['sourceId'],
            row['provenance']['recordId'], index, language, value), 'language': language, 'value': value,
            'sourceTextSha256': places.sha256_bytes(value.encode()), 'status': 'source-asserted',
            'citationIds': [citation['id']]})
    # SPARQL JSON term controls have declared machine semantics. Correct only
    # this retained RDF subtree, not the shared producer's generic text rules.
    source_record = next(a['value'] for a in assertions if a['sourcePath'] == '$.sourceRecord')
    terms = source_record['fields']['data']['fields']['sourceQueryBindings']['items']
    for index, (node, binding) in enumerate(zip(terms, bindings)):
        for key, raw_term in binding.items():
            if not isinstance(raw_term, dict):
                continue
            fields = node['fields'][key]['fields']
            for control in ('type', 'xml:lang'):
                if isinstance(raw_term.get(control), str):
                    fields[control] = {'kind': 'identifier', 'value': raw_term[control]}
            if isinstance(raw_term.get('datatype'), str):
                fields['datatype'] = {'kind': 'uri', 'value': raw_term['datatype']}
            value = raw_term.get('value')
            if not isinstance(value, str):
                continue  # Preserve non-string/unknown source evidence as supplied.
            if raw_term.get('type') == 'uri':
                fields['value'] = {'kind': 'uri', 'value': value}
            elif raw_term.get('type') in {'literal', 'typed-literal'}:
                text = places.text_value(value, places.stable_id('source-rdf-literal', row['provenance']['sourceId'],
                    row['provenance']['recordId'], index, key, value))
                text['language'] = raw_term.get('xml:lang') or 'und'
                text['citationIds'] = [citation['id']]
                fields['value'] = text
            elif raw_term.get('type') == 'bnode':
                fields['value'] = {'kind': 'identifier', 'value': value}
    return {'schemaVersion': places.SCHEMA_VERSION, 'resources': [resource],
            'assertions': assertions, 'relations': [], 'citations': [citation], 'translations': []}


def candidate_evidence_scope(record, requested=None):
    """Contain unadmitted evidence; source tags never authorize public output."""
    if requested is not None and (not isinstance(requested, dict) or requested.get('visibility') not in {'private', 'local-restricted'}):
        raise ValueError('explicit private/local candidate scope required; public denied')
    if requested is not None and 'ownerId' in requested and (not isinstance(requested['ownerId'], str) or not requested['ownerId']):
        raise ValueError('candidate owner must be a nonempty identity')
    provenance = record.get('provenance', {})
    declarations = [record.get('scope'), provenance.get('scope')]
    if provenance.get('visibility') is not None:
        declarations.append({'visibility': provenance['visibility'], 'ownerId': provenance.get('ownerId')})
    owners = set()
    private_declared = False
    for scope in declarations:
        if scope is None:
            continue
        if not isinstance(scope, dict) or scope.get('visibility') not in {'public', 'private', 'local-restricted'}:
            raise ValueError('unsupported source scope')
        if scope['visibility'] == 'private':
            private_declared = True
            if scope.get('ownerId'):
                owners.add(scope['ownerId'])
    if len(owners) > 1:
        raise ValueError('conflicting source owners')
    result = copy.deepcopy(requested) if requested is not None else {'visibility': 'local-restricted'}
    if private_declared:
        owner = next(iter(owners), result.get('ownerId'))
        if not isinstance(owner, str) or not owner or result.get('ownerId', owner) != owner:
            raise ValueError('private source owner unavailable/mismatch')
        result.update(visibility='private', ownerId=owner)
    if result['visibility'] == 'private' and (not isinstance(result.get('ownerId'), str) or not result['ownerId']):
        raise ValueError('private candidate owner required')
    if set(result) - {'visibility', 'ownerId', 'reuseScope'}:
        raise ValueError('unsupported candidate scope fields')
    result['reuseScope'] = 'Unadmitted local candidate; no publication or rights grant'
    return result


def valid_source_date(value):
    import datetime
    if not isinstance(value, str):
        return False
    try:
        return datetime.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def recipe_audit_record(row):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('v2_recipe_format', Path(__file__).with_name('recipe_format.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ingredient = module.ingredient
    'Preserve identity; compare retained parsing with the current parser, without replacement.'
    provenance = row.get('provenance', {})
    data = row.get('data', {})
    issues = []
    for key in ('originSourceId', 'recordId', 'url', 'originalContentSha256', 'license'):
        if not provenance.get(key):
            issues.append({'kind': 'missing_identity', 'field': 'provenance.' + key})
    if not (provenance.get('revisionId') or provenance.get('sourceRevision')):
        issues.append({'kind': 'missing_revision'})
    if data.get('automaticPlanningEligible') is not False:
        issues.append({'kind': 'planning_not_explicitly_withheld'})
    unresolved = 0
    for index, item in enumerate(data.get('ingredients', [])):
        original = item.get('originalText')
        source = item.get('sourceQuantity', {})
        if item.get('amount') is None:
            unresolved += 1
        if not original or source.get('original') != original:
            issues.append({'kind': 'original_notation_mismatch', 'ingredient_index': index})
        if not original:
            continue
        parsed = ingredient(original)
        if parsed is None:
            issues.append({'kind': 'current_parser_drops_ingredient', 'ingredient_index': index})
            continue
        fields = [key for key in ('amount', 'unit', 'sourceQuantity') if parsed.get(key) != item.get(key)]
        if fields:
            issues.append({'kind': 'parser_divergence', 'ingredient_index': index, 'fields': fields, 'original_text': original, 'retained': {k: item.get(k) for k in fields}, 'candidate_reparse': {k: parsed.get(k) for k in fields}, 'status': 'needs-source-review; no replacement'})
        extras = sorted(set(source) - {'value', 'unit', 'range', 'original', 'status'})
        if extras:
            issues.append({'kind': 'unprojected_source_quantity_fields', 'ingredient_index': index, 'fields': extras})
    return {'id': row.get('id'), 'provenance': provenance, 'unresolved_amounts': unresolved, 'issues': issues, 'automaticPlanningEligible': False, 'qualification': 'audit-only; source and planning acceptance withheld'}


def price_audit_record(raw, reference):
    import datetime
    import decimal
    FIELDS = 'id product_id product location_id location proof_id proof type product_code product_name category_tag labels_tags origins_tags price price_is_discounted price_without_discount discount_type price_per price_per_unit currency date receipt_quantity created updated duplicate_of'.split()

    def valid_decimal(value):
        if value is None or isinstance(value, bool):
            return False
        try:
            d = decimal.Decimal(str(value))
            return d.is_finite() and d >= 0
        except decimal.InvalidOperation:
            return False
    'Keep source lexical values; receipt count is never package size/mass.'
    source = {k: raw[k] for k in FIELDS if k in raw}
    flags = []
    for key in ('id', 'price', 'currency', 'date'):
        if raw.get(key) in (None, ''):
            flags.append('missing:' + key)
    if not valid_decimal(raw.get('price')):
        flags.append('invalid:price')
    currency = raw.get('currency')
    if currency is not None and (not isinstance(currency, str) or len(currency) != 3 or (not currency.isascii()) or (not currency.isalpha()) or (currency != currency.upper())):
        flags.append('invalid:currency-syntax')
    try:
        if datetime.date.fromisoformat(raw.get('date', '')).isoformat() != raw['date']:
            flags.append('invalid:date')
    except (ValueError, TypeError):
        flags.append('invalid:date')
    code = raw.get('product_code')
    if code is not None and (not isinstance(code, str) or not code.isascii() or (not code.isdigit()) or (not 4 <= len(code) <= 32)):
        flags.append('invalid:barcode')
    if not code:
        flags.append('unknown:product-barcode')
    if raw.get('product_id') is not None and raw.get('product') is not None and (raw['product_id'] != raw['product']):
        flags.append('conflict:source-product-reference')
    if raw.get('duplicate_of') is not None:
        flags.append('duplicate-source-observation')
    if raw.get('price_per') is None:
        flags.append('unknown:price-basis')
    flags.append('unknown:pack-size')
    return {'observationId': None if raw.get('id') is None else 'open-prices:' + str(raw['id']), 'reference': reference, 'sourceValues': source, 'productBinding': {'sourceProductId': raw.get('product_id'), 'sourceProductReference': raw.get('product'), 'barcode': code, 'category': raw.get('category_tag'), 'canonicalProductId': None, 'verified': False}, 'quantity': {'amountLexical': raw.get('price'), 'currency': currency, 'sourcePriceBasis': raw.get('price_per'), 'sourceUnitPrice': raw.get('price_per_unit'), 'receiptQuantityLexical': raw.get('receipt_quantity'), 'packSize': None, 'comparable': False}, 'observedAt': raw.get('date'), 'availability': 'unknown', 'priceType': 'dated-observation', 'currentOffer': False, 'qualification': 'candidate-only; independent review required', 'flags': flags}


def evidence_packet(candidate, manifest=None):
    """Carry selected OFF/price/recipe facts into typed canonical assertions.

    This deliberately adds no serving conversion, product join or recipe plan.
    """
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('v2_evidence', Path(__file__).with_name('align-bulk-food-common.py'))
    bulk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bulk)
    source = candidate['source']
    expected_source = {'off': 'off', 'prices': 'prices', 'recipes': 'world-recipes'}[source]
    if not isinstance(manifest, dict) or manifest.get('sourceId') != expected_source:
        raise ValueError('source manifest identity mismatch')
    if source == 'recipes':
        original = candidate['sourceEvidence']['record']
        row = copy.deepcopy(original)
        row['data'].update(automaticPlanningEligible=False, sourceParserIssues=candidate['parserIssues'],
                          sourceNormalizationVersion=VERSION, sourceAudit=copy.deepcopy(candidate['sourceEvidence']['audit']))
        source_id = row['provenance']['sourceId']
    else:
        source_id = 'off' if source == 'off' else 'prices'
        values = candidate['sourceEvidence'].get('source_values', candidate['sourceEvidence'].get('sourceValues'))
        row = {'id': source_id + ':v2:' + str(candidate['recordId']), 'kind': 'product' if source == 'off' else 'priceObservation',
               'provenance': {'sourceId': source_id, 'recordId': str(candidate['recordId'])},
               'data': {'sourceValues': copy.deepcopy(values), 'sourceNormalizationVersion': VERSION,
                        'qualificationStatus': 'source-asserted-unverified', 'automaticPlanningEligible': False}}
        if source == 'off':
            # Publisher product revisions, export releases and future registry
            # revisions are distinct namespaces. Never use the export as rev.
            from datetime import datetime, timezone
            revision = values.get('rev')
            revision_id = str(revision) if (
                isinstance(revision, int) and not isinstance(revision, bool) and revision > 0
            ) else None
            modified = values.get('last_modified_t')
            source_date = None
            if isinstance(modified, int) and not isinstance(modified, bool) and modified >= 0:
                try:
                    source_date = datetime.fromtimestamp(modified, timezone.utc).isoformat().replace('+00:00', 'Z')
                except (ValueError, OverflowError, OSError):
                    pass
            publisher_url = manifest.get('url')
            if not isinstance(publisher_url, str) or not publisher_url.startswith(('https://', 'http://')):
                raise ValueError('OFF original publisher URL unavailable')
            row['provenance'].update(url=publisher_url, sourceDate=source_date)
            row['data'].update(sourceRevision=candidate['revision'], nutritionContext=candidate['nutritionContext'],
                               rawNutriments=candidate['nutriments'], basisStatus=candidate['basisStatus'],
                               servingConversionEligible=False, suitability='unknown',
                               sourceCitationContext={
                                   'revisionNamespace': 'off-product-rev',
                                   'revisionId': revision_id,
                                   'sourceDateField': 'last_modified_t',
                                   'sourceDate': source_date,
                                   'releaseId': manifest.get('releaseId'),
                                   'archiveSha256': manifest.get('archiveSha256'),
                                   'archiveDigestStatus': 'supplied-manifest-claim-not-record-byte-digest',
                                   'registryRevisionStatus': 'unbound'})
        else:
            q = candidate['quantity']
            reference = candidate['sourceEvidence']['reference']
            flags = list(candidate['sourceEvidence']['flags'])
            observed = candidate['observedAt']
            if not valid_source_date(observed) and 'invalid:date' not in flags:
                flags.append('invalid:date')
            if not manifest.get('rightsEvidenceUrl') and not manifest.get('licenseUrl'):
                flags.append('source-rights-link-unavailable')
            row['data'].update(priceContext=copy.deepcopy(q), comparable=False, currentOffer=False,
                               currency=q.get('currency'), sourceReference=copy.deepcopy(reference),
                               qualificationFlags=flags, originalObservedAt=observed)
            if valid_source_date(observed):
                row['data']['observedAt'] = observed
    packet = bulk.packet(row, source_id, manifest or {})
    if source == 'off':
        citation = packet['citations'][0]
        citation.update(revisionId=revision_id, sourceDate=source_date,
                        originalUrl=publisher_url, contentSha256=None)
        # No original-record byte digest or rights URL is established by the
        # adapter. Keep the claimed archive digest in its explicit context.
        rights_url = manifest.get('rightsEvidenceUrl') or manifest.get('licenseUrl')
        if rights_url:
            citation['rightsEvidenceUrl'] = rights_url
        else:
            citation.pop('rightsEvidenceUrl', None)
    # Prices remain source lexical assertions. The old amount path has no
    # denominator; do not emit a misleading numeric priceAmount alongside them.
    if source == 'prices':
        packet['assertions'] = [a for a in packet['assertions'] if a['propertyId'] != 'urn:offmenu:property:priceAmount']
        reference = candidate['sourceEvidence']['reference']
        url = manifest.get('url')
        if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
            raise ValueError('original publisher URL unavailable')
        citation = packet['citations'][0]
        citation.update(originalRecordId=str(values['id']), originalUrl=url,
                        contentSha256=reference['lineSha256'], sourcePath='JSONL line ' + str(reference['line']))
        rights_url = manifest.get('rightsEvidenceUrl') or manifest.get('licenseUrl')
        if rights_url:
            citation['rightsEvidenceUrl'] = rights_url
        else:
            citation.pop('rightsEvidenceUrl', None)
        if not valid_source_date(candidate['observedAt']):
            # Legacy typing guesses dates by shape. Preserve malformed notation
            # explicitly as text in every detached canonical source-field tree.
            def lexical(node):
                if isinstance(node, dict):
                    if node.get('kind') == 'date' and node.get('value') == candidate['observedAt']:
                        return bulk.text(node['value'], citation['id'], 'invalid-source-date')
                    return {k: lexical(v) for k, v in node.items()}
                if isinstance(node, list):
                    return [lexical(v) for v in node]
                return node
            packet['assertions'] = [lexical(a) for a in packet['assertions']]
    scope = candidate['candidateScope']
    for section in ('resources', 'assertions', 'relations', 'citations', 'translations'):
        for item in packet[section]:
            if 'scope' in item:
                item['scope'] = copy.deepcopy(scope)
    return packet


def fdc_packet(record, manifest):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('v2_bulk', Path(__file__).with_name('align-bulk-food-common.py'))
    bulk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bulk)
    metrics = {}
    for n in record['nutrients']:
        if n['row_id'] in metrics:
            raise ValueError('duplicate FDC observation identity')
        metrics[n['row_id']] = {**copy.deepcopy(n),
            'value': float(n['amount']['decimal']) if n['amount']['state'] in {'numeric', 'numeric-zero'} else None}
    row = {'id': 'fdc:profile:' + str(record['fdc_id']), 'kind': 'nutrientProfile',
           'provenance': {'sourceId': 'usda-files', 'recordId': str(record['fdc_id']),
                          'releaseId': manifest.get('releaseId'), 'archiveSha256': manifest.get('archiveSha256'),
                          'url': manifest.get('url'), 'license': manifest.get('license'), 'attribution': manifest.get('attribution')},
           'data': {'nutrients': metrics, 'sourceNormalizationVersion': VERSION,
                    'sourceEvidence': copy.deepcopy(record)}}
    packet = bulk.packet(row, 'usda-files', manifest)
    for assertion in packet['assertions']:
        if assertion['propertyId'] != 'urn:offmenu:property:nutrientObservation':
            continue
        n = metrics[assertion['sourcePath'][len('data.nutrients.'):]]
        q = assertion['value']
        q['sourceValue'] = n['amount']['source']
        q['qualifiers'] = list(n['qualifiers'])
        if n['basis'].get('amount') == '100' and n['basis'].get('unit') == 'g':
            q['basis']['value'] = 100
            q['basis']['sourceValue'] = '100'
        if n['unit'] == 'UG' and n['definition'].get('unit_name') == 'UG':
            q.update(unitId='urn:offmenu:unit:ug', dimension='mass')
        if n['basis'].get('status') == 'component-specific-basis-unresolved':
            q['basis']['qualifiers'].append('component-specific-basis-unresolved')
    return packet


def national_packet(candidate, base_record):
    """Project corrected source metrics through the existing common graph builder.

    This creates a versioned candidate in memory; it never changes an old graph.
    """
    import importlib.util
    from pathlib import Path
    from urllib.parse import quote
    spec = importlib.util.spec_from_file_location('v2_national', Path(__file__).with_name('align-national-common.py'))
    national = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(national)
    expected = {'ciqual': 'ciqual', 'cofid': 'cofid', 'bls': 'germany-bls'}[candidate['source']]
    provenance = base_record.get('provenance', {})
    if provenance.get('sourceId') != expected or str(provenance.get('recordId')) != str(candidate['recordId']):
        raise ValueError('base-record source identity mismatch')
    row = copy.deepcopy(base_record)
    metrics, observations_by_key, definition_ids = {}, {}, {}
    for metric in candidate['observations']:
        original = metric['sourceObservation']
        component = str(metric['component'])
        definition_context = [expected, provenance.get('releaseId'), component]
        coordinates = [original.get('sheet'), original.get('row'), original.get('column')] if candidate['source'] == 'cofid' else None
        # No dictionary/list ordinal participates in source identity. CoFID
        # genuinely has multiple source cells for one component.
        key = component + ':' + hashlib.sha256(encoded([definition_context, coordinates])).hexdigest()
        if key in observations_by_key:
            raise ValueError('duplicate immutable metric observation identity')
        observations_by_key[key] = metric
        definition_ids[key] = 'urn:offmenu:nutrient-definition:' + hashlib.sha256(encoded(definition_context)).hexdigest()
        names = original.get('names', {})
        metrics[key] = {**copy.deepcopy(original), 'value': None if metric['quarantined'] else metric['value'],
                        'unit': metric['unitExpression'], 'name': names.get('en', names.get('fr', str(metric['component'])))}
    row['data'].update(nutrients=metrics, basis={}, sourceNormalizationVersion=VERSION,
                       selectedSourceEvidence=candidate['sourceEvidence'])
    if candidate['source'] == 'bls':
        row['data']['notes'] = copy.deepcopy(candidate['notes'])
    packet = national.graph(row)
    resources = {resource['id']: resource for resource in packet['resources']}
    citation_id = packet['citations'][0]['id']
    for assertion in packet['assertions']:
        if assertion['propertyId'] == 'urn:offmenu:property:metricDefinition':
            key = assertion['sourcePath'][len('data.nutrients.'):-len('.definition')]
            assertion['value']['value'] = definition_ids[key]
            if candidate['source'] == 'bls':
                definition = observations_by_key[key]['sourceObservation']['componentDefinition']
                labels = {'de': definition.get('Nährstoffbezeichnung'), 'en': definition.get('Component name')}
                resource = resources[assertion['subjectId']]
                resource['names'] = [national.text(label, lang, resource['id'] + ':source-label:' + lang, citation_id)
                                     for lang, label in labels.items() if isinstance(label, str) and label]
            continue
        if assertion['propertyId'] != 'urn:offmenu:property:metricValue':
            continue
        key = assertion['sourcePath'][len('data.nutrients.'):-len('.value')]
        metric = observations_by_key[key]
        quantity = assertion['value']
        basis = metric['basis'] or {}
        unit = basis.get('unit')
        quantity['basis'] = {'kind': 'quantity', 'value': basis.get('amount') if numeric(basis.get('amount')) else None,
            'unitId': 'urn:offmenu:unit:' + quote(str(unit), safe='') if unit else None,
            'dimension': national.dimension(unit), 'sourceValue': basis.get('amount'), 'sourceUnit': unit,
            'qualifiers': ['source-metric-specific-basis']}
        quantity['sourceValue'] = metric['original']
        quantity['qualifiers'].append('numeric-zero-is-not-absence')
        if metric['quarantined']:
            quantity['qualifiers'].append('quarantined-source-definition')
        if metric['qualifier'] == 'less-than' and numeric(metric['limit']):
            quantity['range'] = {'min': None, 'max': metric['limit']}
            quantity['qualifiers'].append('censored-upper-bound-exclusive')
    return packet


def normalize(source, record, *, adapter_commit, component_dictionary=None, headers=None, base_record=None, source_manifest=None, candidate_scope=None, source_record_bytes=None):
    if source not in QUALIFIED_ADAPTERS or adapter_commit != QUALIFIED_ADAPTERS[source]:
        raise ValueError('unselected source/adapter pin')
    if not isinstance(record, dict):
        raise ValueError('source record must be an object')
    raw = copy.deepcopy(record)
    result = {'schemaVersion': VERSION, 'source': source, 'adapterCommit': adapter_commit,
              'sourceEvidence': raw, 'sourceEvidenceSha256': hashlib.sha256(encoded(raw)).hexdigest(),
              'digestSemantics': 'canonical selected adapter JSON, not original publisher record bytes',
              'status': 'bounded-normalization-candidate', 'packageAdmitted': False,
              'automaticPlanningEligible': False, 'conversionEligible': False}
    if source == 'fdc':
        result['recordId'] = str(record['fdc_id'])
        if not source_manifest or source_manifest.get('sourceId') != 'usda-files':
            raise ValueError('pinned FDC source manifest required')
        result['canonicalPacket'] = fdc_packet(record, source_manifest)
    elif source in {'ciqual', 'bls', 'cofid'}:
        if source == 'ciqual':
            if record.get('sourceId') != 'ciqual':
                raise ValueError('CIQUAL source identity mismatch')
            metrics = [(m['sourceComponent'], m) for m in record['observations']]
            result['recordId'] = record['sourceFoodId']
        elif source == 'cofid':
            metrics = [(m['component'], m) for m in record['metrics']]
            result['recordId'] = record['recordId']
        else:
            if record.get('sourceId') != 'germany-bls' or not component_dictionary or not headers:
                raise ValueError('complete BLS dictionary and original headers required')
            # A missing dictionary entry must fail, rather than turning a metric
            # into a note. All measurement triples must reconcile exactly.
            declared = {str(h).removesuffix(' Datenherkunft') for h in headers if str(h).endswith(' Datenherkunft')}
            if not declared or not declared <= set(component_dictionary) or declared != set(record['nutrients']):
                raise ValueError('BLS complete dictionary/header reconciliation failed')
            metrics = list(record['nutrients'].items())
            if any(m.get('componentDefinition') != component_dictionary[k] for k, m in metrics):
                raise ValueError('BLS component definition mismatch')
            result.update(recordId=record['recordId'], notes=copy.deepcopy(record['notes']),
                          componentDictionarySha256=hashlib.sha256(encoded(component_dictionary)).hexdigest())
        result['observations'] = [observation(k, m, source == 'ciqual' and str(k) == '51104') for k, m in metrics]
        identities = [(m['component'], m['sourceObservation'].get('sheet'), m['sourceObservation'].get('column')) for m in result['observations']]
        if len(identities) != len(set(identities)):
            raise ValueError('duplicate metric identity requires explicit source reconciliation')
        # Metric-specific basis always wins; never substitute a food default.
        for metric in result['observations']:
            if metric['basis'] is None:
                metric['quarantined'] = True
    elif source == 'off':
        result['candidateScope'] = candidate_evidence_scope(record, candidate_scope)
        values = record['source_values']
        result['recordId'] = values.get('code', values.get('_id'))
        result['revision'] = {k: values[k] for k in ('rev', 'last_modified_t', 'last_updated_t') if k in values}
        result['nutritionContext'] = {k: values[k] for k in ('nutrition_data_per', 'nutrition_data_prepared_per',
            'nutrition_data', 'nutrition_data_prepared', 'serving_size', 'serving_quantity', 'serving_quantity_unit') if k in values}
        result['nutriments'] = copy.deepcopy(values.get('nutriments'))
        result['basisStatus'] = 'source-declared-unconverted' if values.get('nutrition_data_per') in {'100g', '100ml', 'serving'} else 'unknown'
        result['servingConversionEligible'] = False
        result['suitability'] = 'unknown'
    elif source == 'prices':
        result['candidateScope'] = candidate_evidence_scope(record, candidate_scope)
        values = record.get('sourceValues', {})
        expected_price = price_audit_record(values, record.get('reference'))
        if any(encoded(record.get(key)) != encoded(value) for key, value in expected_price.items()):
            raise ValueError('price qualification/context binding mismatch')
        identifier = values.get('id')
        if isinstance(identifier, bool) or not isinstance(identifier, (str, int)) or not str(identifier):
            raise ValueError('price source observation ID required')
        if record.get('observationId') != 'open-prices:' + str(identifier):
            raise ValueError('price observation identity mismatch')
        if record.get('observedAt') != values.get('date'):
            raise ValueError('price date binding mismatch')
        if source_manifest is not None:
            import re
            reference = record.get('reference', {})
            if (type(reference.get('line')) is not int or reference['line'] < 1
                    or not re.fullmatch('[a-f0-9]{64}', str(reference.get('lineSha256', '')))
                    or not re.fullmatch('[a-f0-9]{64}', str(reference.get('archiveSha256', '')))
                    or reference.get('archiveSha256') != source_manifest.get('archiveSha256')
                    or reference.get('releaseId') != source_manifest.get('releaseId')):
                raise ValueError('price source reference/manifest binding mismatch')
            if isinstance(source_record_bytes, str):
                source_record_bytes = source_record_bytes.encode('utf-8')
            if (not isinstance(source_record_bytes, bytes) or len(source_record_bytes) > 1024 * 1024
                    or hashlib.sha256(source_record_bytes).hexdigest() != reference['lineSha256']):
                raise ValueError('exact supplied price source-line bytes required')
            source_row = json.loads(source_record_bytes, parse_float=str)
            fields = ('id product_id product location_id location proof_id proof type product_code product_name category_tag labels_tags origins_tags price price_is_discounted price_without_discount discount_type price_per price_per_unit currency date receipt_quantity created updated duplicate_of').split()
            if {key: source_row[key] for key in fields if key in source_row} != values:
                raise ValueError('price source-line/selected-fields mismatch')
            result['candidateScope'] = candidate_evidence_scope(source_row, result['candidateScope'])
        result['recordId'] = record['observationId']
        result['quantity'] = copy.deepcopy(record['quantity'])
        # No selected adapter establishes an actual package size or product join.
        result['quantity'].update(packSize=None, comparable=False)
        result['currentOffer'] = False
        result['observedAt'] = record['observedAt']
    elif source == 'businesses':
        if record.get('provenance', {}).get('sourceId') != 'wikidata-food-businesses':
            raise ValueError('business source identity mismatch')
        result['recordId'] = record['provenance']['recordId']
        result['canonicalPacket'] = business_packet(record)
        result['legalIdentityVerified'] = False
        result['productionOrigin'] = 'unknown'
    else:
        row = record['record']
        audit = record['audit']
        provenance = row.get('provenance', {})
        if (row.get('kind') != 'recipe' or provenance.get('sourceId') != 'world-recipes'
                or not isinstance(provenance.get('recordId'), str) or not provenance['recordId']
                or not isinstance(row.get('data', {}).get('ingredients'), list)):
            raise ValueError('recipe source identity/shape mismatch')
        publisher = provenance.get('originSourceId')
        if not isinstance(publisher, str) or not publisher:
            raise ValueError('recipe publisher identity required')
        expected_id = 'world-recipes:recipe:' + hashlib.sha256((publisher + '\0' + provenance['recordId']).encode()).hexdigest()[:24]
        if row.get('id') != expected_id:
            raise ValueError('recipe record/provenance identity mismatch')
        result['candidateScope'] = candidate_evidence_scope(row, candidate_scope)
        expected_audit = recipe_audit_record(row)
        if encoded(audit) != encoded(expected_audit):
            raise ValueError('recipe audit provenance/count/diagnostic binding mismatch')
        result['recordId'] = row.get('id')
        result['ingredients'] = copy.deepcopy(row.get('data', {}).get('ingredients', []))
        result['parserIssues'] = copy.deepcopy(audit['issues'])
        result['unresolvedAmounts'] = audit['unresolved_amounts']
        # Divergences are retained diagnostics; never replace source text/parse.
    if not result.get('recordId'):
        raise ValueError('stable source record identity required')
    if source in {'off', 'prices', 'recipes'} and source_manifest is not None:
        result['canonicalPacket'] = evidence_packet(result, source_manifest)
    if source in {'ciqual', 'cofid', 'bls'} and base_record is not None:
        result['canonicalPacket'] = national_packet(result, base_record)
    encoded(result)  # Reject nonfinite/non-JSON evidence before emitting.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=QUALIFIED_ADAPTERS, required=True)
    parser.add_argument('--adapter-commit', required=True)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('selected evidence exceeds 2 MiB bound')
    request = json.loads(raw)
    result = normalize(args.source, request['record'], adapter_commit=args.adapter_commit,
                       component_dictionary=request.get('componentDictionary'), headers=request.get('headers'),
                       base_record=request.get('baseRecord'), source_manifest=request.get('sourceManifest'),
                       candidate_scope=request.get('candidateScope'),
                       source_record_bytes=request.get('sourceRecordText'))
    output = encoded(result)
    if len(output) > 2 * 1024 * 1024:
        raise ValueError('normalized candidate exceeds 2 MiB bound')
    sys.stdout.buffer.write(output + b'\n')


if __name__ == '__main__':
    main()
