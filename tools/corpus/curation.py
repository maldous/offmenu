"""OffMenu publication projection. Original source bodies stay local.

This is deliberately separate from source normalization. Only selected facts,
review decisions and provenance references can enter the hosted release.
"""
import hashlib
import math
import json
from pathlib import Path
COUNTRY_CODES = frozenset(c["iso2"] for c in json.loads((Path(__file__).resolve().parents[2] / "docs/country-delivery-matrix.json").read_text())["countries"])

METRICS = {'energy': 'kcal', 'energyKJ': 'kJ', 'protein': 'g', 'carbohydrate': 'g',
           'fat': 'g', 'sugars': 'g', 'addedSugars': 'g', 'freeSugars': 'g', 'fibre': 'g',
           'saturatedFat': 'g', 'salt': 'g', 'sodium': 'mg', 'calcium': 'mg', 'iron': 'mg',
           'potassium': 'mg', 'vitaminC': 'mg'}


def entity_id(row):
    return 'offmenu:' + row['kind'] + ':' + hashlib.sha256(row['id'].encode()).hexdigest()[:24]


def finite(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def curate(rows, policy_version):
    ids = {row['id']: entity_id(row) for row in rows}
    result, withheld = [], []
    for row in rows:
        data, provenance, kind = row['data'], row['provenance'], row['kind']
        source = provenance['sourceId']
        common = {'schemaVersion': '1.0', 'id': ids[row['id']], 'kind': kind,
                  'countries': row.get('countries', []),
                  'provenance': {key: provenance.get(key) for key in
                     ['sourceId', 'recordId', 'url', 'license', 'licenseUrl', 'attribution', 'sourceDate', 'releaseId', 'limitationStatement', 'countryNotice', 'changes', 'rights', 'licenseNotices', 'copyright', 'originSourceId', 'revisionId', 'historyUrl', 'sourceRevision', 'rightsEvidenceUrl', 'recipeReuse', 'originalAuthors', 'rightsScope', 'originalContentSha256', 'sourceDocumentSha256'] if provenance.get(key) is not None},
                  'curation': {'schema': 'offmenu-curation/1', 'policyVersion': policy_version,
                     'sourceRecordReference': row['id'], 'status': 'selected-source-facts',
                     'humanReviewed': False, 'automaticDietQualification': False,
                     'rawSourcePayloadPublished': False}}
        common['provenance']['visibility'] = 'public'
        common['provenance']['transform'] = 'offmenu-curation/1'
        if kind == 'product':
            name = data.get('name')
            if not name or name == provenance.get('recordId') or name == 'Unnamed food':
                withheld.append({'id': row['id'], 'reason': 'usable food identity unresolved'})
                continue
            projected = {key: data[key] for key in ['name', 'names', 'brand', 'pack', 'identifiers', 'dataType', 'marketCountry', 'serving', 'preparationState'] if key in data}
            projected['nutritionId'] = ids.get(data.get('nutritionId'))
            projected['ingredientConcepts'] = []
            projected['ingredientMappingStatus'] = 'unresolved'
            projected['qualificationStatus'] = 'unknown'
            # No raw ingredient wording, crowdsourcing metadata, image objects,
            # rawNutriments or full upstream product document is published.
        elif kind == 'nutrientProfile':
            basis = data.get('basis', {})
            if basis.get('amount') != 100 or basis.get('unit') not in ('g', 'ml'):
                withheld.append({'id': row['id'], 'reason': 'unsupported quantity basis'})
                continue
            nutrients = {}
            for key, unit in METRICS.items():
                nutrient = data.get('nutrients', {}).get(key, {})
                value = finite(nutrient.get('value')) if nutrient.get('unit') == unit else None
                method = str(nutrient.get('method', 'unknown'))
                nutrients[key] = {'value': value, 'unit': unit, 'basis': basis,
                    'qualifier': nutrient.get('qualifier') or ('source-reported' if value is not None else 'unknown'),
                    'method': 'derived' if 'derived' in method or 'converted' in method else 'source-reported',
                    'definition': nutrient.get('definition') or source + ':' + key}
                if nutrient.get('limit') is not None and finite(nutrient['limit']) is not None:
                    nutrients[key]['limit'] = nutrient['limit']
            if not any(n['value'] is not None for n in nutrients.values()):
                withheld.append({'id': row['id'], 'reason': 'no usable mapped composition facts'})
                continue
            projected = {'foodName': data.get('foodName'), 'identifiers': data.get('identifiers', []),
                         'basis': basis, 'nutrients': nutrients, 'foodConceptId': None,
                         'foodMatchStatus': 'unresolved', 'qualificationStatus': 'unknown'}
        elif kind == 'priceObservation':
            retailer = data.get('retailer') or {}
            projected = {key: data.get(key) for key in ['identifiers', 'amount', 'currency', 'observedAt', 'unitPrice', 'unit', 'promotion', 'regularAmount']}
            projected.update(priceType='dated-observation', availability='unknown',
                             retailer={'name': retailer.get('name'), 'externalId': retailer.get('externalId')},
                             # The approved fields above do not establish matching
                             # product/variant/pack, tax, loyalty or fulfilment
                             # conditions. Amount/currency/date are dated facts,
                             # not comparison qualification (see the price import
                             # contract). No comparison review runs in this path.
                             comparable=False)
        elif kind == 'organization' and source == 'wikidata-food-businesses':
            projected = {key: data.get(key) for key in ['name', 'names', 'identifiers', 'roles', 'websites', 'countryBasis', 'reviewStatus']}
            projected.update(ownershipVerified=False, operationalCoverageVerified=False)
            common['curation']['status'] = 'organization-reference'
        elif kind == 'sourceAssertion' and source == 'dietary-guidelines':
            projected = {key: data.get(key) for key in ['name', 'referenceType', 'referenceUrl', 'directoryUrl', 'reviewStatus', 'contentPermission', 'qualificationStatus']}
            common['curation']['status'] = 'discovery-reference'
        elif kind in ('retailer', 'site') and source == 'overture-food-places':
            projected = {key: data.get(key) for key in ['name', 'names', 'identifiers', 'role', 'taxonomy', 'basicCategory', 'locations', 'countryBasis', 'sourceReportedOperatingStatus', 'existenceConfidence', 'sourceProviders', 'sourceLicenses', 'sourceVersion']}
            source_country_tags = row.get('countries', [])
            common['countries'] = sorted({('GB' if code == 'UK' else code) for code in source_country_tags if ('GB' if code == 'UK' else code) in COUNTRY_CODES})
            projected['sourceCountryTags'] = source_country_tags
            projected['countryMappingStatus'] = 'unallocated-source-tags-retained' if any(('GB' if code == 'UK' else code) not in COUNTRY_CODES for code in source_country_tags) else 'source-code-in-project-registry'
            projected.update(inventoryAvailability='unknown', ownershipVerified=False, dietQualification='unknown', reviewStatus='source-reference-unreviewed')
            common['curation']['status'] = 'place-reference'
            common['provenance']['licenseNotices'] = ['https://offmenu-corpus.netlify.app/notices/' + source + '/' + str(provenance['releaseId']) + '/' + name for name in provenance.get('licenseNotices', [])]
        elif kind == 'recipe':
            if source == 'world-recipes' and data.get('recipeSchema') == 'offmenu-recipe/1' and provenance.get('recipeReuse') == 'licensed-full-recipe-content':
                if not data.get('ingredients') or not data.get('directions'):
                    withheld.append({'id': row['id'], 'reason': 'recipe ingredients or instructions unavailable'})
                    continue
                projected = {key: data[key] for key in ['recipeSchema', 'name', 'names', 'nativeName', 'languages', 'yield', 'ingredients', 'directions', 'directionsByLanguage', 'time', 'quantityCoverage', 'sourcePublisher', 'historical', 'sourceBook', 'sourcePublicationYear', 'sourceCulture', 'sourceOriginalLanguages', 'sourceCuisineCountry', 'ingredientExtractionComplete', 'sourceExtraction', 'sourceParagraphRange', 'sourceDocument', 'limitations'] if key in data}
                projected.update(reviewStatus='source-recipe-needs-personal-quantity-and-food-review', automaticPlanningEligible=False, qualificationStatus='unknown')
                common['curation']['status'] = 'licensed-recipe-content'
                result.append({**common, 'data': projected})
                continue
            # Discovery references are OffMenu's curation; the complete source
            # recipe, wording and inferred quantities are retained only locally.
            projected = {'name': data.get('name'), 'yield': {'value': None, 'unit': 'portion'},
                         'ingredients': [], 'directions': [], 'reviewStatus': 'source-reference-needs-curation',
                         'automaticPlanningEligible': False,
                         'sourceIngredientCount': len(data.get('ingredients', [])),
                         'limitations': 'Original recipe is available at its source. OffMenu quantities and ingredient matches require review.'}
            common['curation']['status'] = 'discovery-reference'
        else:
            withheld.append({'id': row['id'], 'reason': 'kind requires an explicit publication projection'})
            continue
        result.append({**common, 'data': projected})
    # No dangling profile join if a profile failed curation.
    available = {record['id'] for record in result}
    for record in result:
        if record['kind'] == 'product' and record['data']['nutritionId'] not in available:
            record['data']['nutritionId'] = None
    return result, withheld
