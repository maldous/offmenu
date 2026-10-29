"""Bounded private English-pivot generation from selected, already parsed assets.

The caller supplies exact authorized bytes. No source discovery, fetching, model,
existing-store access or admission occurs here. Output uses offmenu-common/1;
curation/index metadata describes that packet rather than another taxonomy.
Author candidates require independent review before registry/Gold/runtime adoption.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

VERSION = 'offmenu.ingredient-vocabulary-generation/2'
HISTORICAL_PINS = {'public/afcd-nutrient-details.json': ('d297aa8d3e7453d707d909b1eaab23337b559a80bf71dd11f348c6707e3220ca',
                                       63684),
 'public/off-photo-catalogue.js': ('f7e0b953c0f3c6609f8d72597de576d050df90ec16a65e99df84c4b936707e8b',
                                   3771),
 'public/recipe-ingredient-aliases.json': ('c2dbca1d379ce93fa4423993ed0d1ace7669447c7899be025b7af3a8855bb609',
                                           10156)}
CURATION_VERSION = 'english-pivot-selected-source-rules/1'
MAX_INPUT = 131072
MAX_OUTPUT = 16 * 1024 * 1024
PINS = {'apps/web/assets/afcd-nutrient-details.json': ('d297aa8d3e7453d707d909b1eaab23337b559a80bf71dd11f348c6707e3220ca',
                                                63684),
 'apps/web/assets/recipe-ingredient-aliases.json': ('c2dbca1d379ce93fa4423993ed0d1ace7669447c7899be025b7af3a8855bb609',
                                                    10156),
 'apps/web/src/off-photo-catalogue.js': ('991791f2b176c0e216cfe3d96c9e9d7daf86a3a2d89ab0b527d578098ebab430',
                                         4008)}
ALIAS = 'apps/web/assets/recipe-ingredient-aliases.json'
AFCD = 'apps/web/assets/afcd-nutrient-details.json'
PHOTO = 'apps/web/src/off-photo-catalogue.js'
# IDs bind explicit curation decisions, not translated spelling. Revisions retain
# these keys; semantic changes need an explicit versioned correction/redirect.
RULES = (
    ('i01', 'water', 'Water, source group', 'FoodIngredient', 'Water ingredient; source form and composition unspecified.'),
    ('i02', 'salt', 'Culinary salt family', 'FoodConcept', 'Source salt family; purity, additives and sodium content are not inferred.'),
    ('i03', 'rice', 'Rice family, form unspecified', 'FoodConcept', 'Grain/variety/preparation are unresolved; basmati and jasmine are not equivalent variants.'),
    ('i04', 'cooked rice', 'Cooked rice', 'FoodIngredient', 'Explicit cooked-rice source group; water uptake, variety and nutrients unknown.'),
    ('i05', 'wheat flour', 'Source wheat-flour family', 'FoodConcept', 'Source grouping only; generic flour, refined/whole grain and composition remain ambiguous.'),
    ('i06', 'sugar', 'Sugar family, source group', 'FoodConcept', 'Source sugar grouping; specific formulation and nutrient values unqualified.'),
    ('i07', 'milk', 'Milk family, composition unspecified', 'FoodConcept', 'Family only: cow/other source, whole/low-fat, composition and substitution constraints remain distinct.'),
    ('i08', 'milk', 'Cow milk, fat level unspecified', 'FoodIngredient', 'Explicit cow milk lexical item; whole/low-fat percentages and interchangeability not supplied.'),
    ('i09', 'butter', 'Butter, source group', 'FoodIngredient', 'Salt, fat fraction, softening and formulation are not inferred.'),
    ('i10', 'olive oil', 'Olive oil family', 'FoodConcept', 'Grade, processing and composition unresolved; source aliases are proposed matches.'),
    ('i11', 'coconut milk', 'Coconut milk', 'FoodIngredient', 'Distinct plant-derived source group, not an equivalent dairy-milk variant.'),
    ('i12', 'egg', 'Egg family, source unspecified', 'FoodConcept', 'Species, size, edible mass and preparation unknown.'),
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def _id(kind, key):
    return 'urn:offmenu:vocabulary:' + kind + ':' + key


def _pointer(key):
    return key.replace('~', '~0').replace('/', '~1')


def _photo_rows(raw):
    """Read the selected parsed JS data literal; never evaluate its functions."""
    text = raw.decode('utf-8')
    block = text.split('export const OFF_PHOTOS=Object.freeze([', 1)[1].split('\n]);', 1)[0]
    rows = []
    for body in re.findall(r'Object\.freeze\(\{(.*?)\}\)', block, re.S):
        row = dict(re.findall(r"(\w+)\s*:\s*'([^']*)'", body))
        if not {'key', 'sourceCode', 'sourcePage', 'license', 'licenseUrl', 'contributor'} <= row.keys():
            raise ValueError('selected photo metadata structure')
        rows.append(row)
    if len(rows) != 2:
        raise ValueError('selected photo metadata count')
    return rows


def build_generation(assets, contract_raw, *, generation_version, actor_reference):
    """Build one deterministic author-qualified candidate; rights are caller-owned.

    Matching pins establish the selected bytes, not new operation permission.
    Source alias groups are lexical evidence, not accepted semantic crosswalks.
    """
    if set(assets) != set(PINS):
        raise ValueError('exact three selected assets required')
    for path, (expected, size) in PINS.items():
        raw = assets[path]
        if type(raw) is not bytes or len(raw) > MAX_INPUT or len(raw) != size or sha256(raw).hexdigest() != expected:
            raise ValueError('selected asset pin mismatch: ' + path)
    if not all(type(v) is str and v.strip() and len(v) <= 2048 for v in (generation_version, actor_reference)):
        raise ValueError('explicit version and actor required')
    if type(contract_raw) is not bytes or len(contract_raw) > MAX_INPUT:
        raise ValueError('bounded existing contract bytes required')
    contract = _json(contract_raw)
    contract_sha = sha256(contract_raw).hexdigest()
    if contract_sha != 'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa' or len(contract.get('units', {})) != 14:
        raise ValueError('selected existing unit contract required')
    aliases, nutrients = _json(assets[ALIAS]), _json(assets[AFCD])
    photos = _photo_rows(assets[PHOTO])
    scope = {'visibility': 'private', 'ownerId': actor_reference,
             'reuseScope': 'selected-private-local-author-candidate; independent review before adoption'}
    packet = {'schemaVersion': 'offmenu-common/1', 'resources': [], 'assertions': [],
              'relations': [], 'citations': [], 'translations': []}
    observations, concepts, decisions, definition_rows = [], [], [], []

    def citation(path, pointer, *, metadata=None):
        cid = _id('citation', digest([path, PINS[path][0] if path in PINS else contract_sha, pointer]))
        if any(c['id'] == cid for c in packet['citations']):
            return cid
        source = metadata or {}
        packet['citations'].append({
            'id': cid, 'sourceId': source.get('sourceId', 'offmenu-parsed-repository-asset'),
            'originalRecordId': pointer, 'originalUrl': source.get('url', 'https://github.com/maldous/offmenu'),
            'revisionId': source.get('release', '0f518f5a75a30d1fd49aed8e524a751bc5ace941'),
            'contentSha256': PINS[path][0] if path in PINS else contract_sha,
            'license': source.get('license', 'Private-local owner-selected operation only; external licence not supplied'),
            'attribution': source.get('attribution', 'OffMenu retained parsed repository asset; original rights remain separate'),
            'sourcePath': path + '#' + pointer, 'scope': deepcopy(scope),
        })
        return cid

    def text(value, language, cid, key, status='candidate'):
        return {'kind': 'text', 'id': _id('text', digest(key)), 'language': language,
                'value': value, 'sourceTextSha256': sha256(value.encode()).hexdigest(),
                'status': status, 'citationIds': [cid]}

    def resource(identifier, typ, label, cid, context):
        packet['resources'].append({'id': identifier, 'type': 'urn:offmenu:type:' + typ,
            'identityStatus': 'candidate-join', 'names': [text(label, 'en', cid, [identifier, 'preferred'], 'editor-authored')],
            'citationIds': [cid], 'scope': deepcopy(scope)})
        concepts.append({'id': identifier, 'type': typ, 'preferredEnglish': label,
                         'definitionContext': context, 'state': 'author-qualified-review-candidate',
                         'existingGlobalMatch': 'unresolved', 'nutritionSubstitutionQualified': False})
        return packet['resources'][-1]

    def relation(subject, predicate, obj, cid, pointer, status='candidate'):
        if predicate not in contract['relationshipVocabulary']:
            raise ValueError('unregistered relation')
        packet['relations'].append({'id': _id('relation', digest([subject, predicate, obj, pointer])),
            'subjectId': subject, 'predicateId': contract['relationshipVocabulary'][predicate]['id'],
            'objectId': obj, 'status': status, 'citationIds': [cid], 'scope': deepcopy(scope), 'sourcePath': pointer})

    # A bounded selected slice, never all dictionary rows or an automatic semantic merge.
    for key, group, label, typ, context in RULES:
        identifier = _id('ingredient', key)
        indices = [i for i, value in enumerate(aliases[group]) if value == 'cow milk'] if key == 'i08' else list(range(min(12, len(aliases[group]))))
        if key == 'i07':
            indices = [i for i in indices if aliases[group][i] != 'cow milk']
        cid = citation(ALIAS, '/' + _pointer(group))
        node = resource(identifier, typ, label, cid, context)
        decisions.append({'decisionId': _id('decision', key), 'decisionVersion': CURATION_VERSION,
                          'action': 'propose-new-contextual-concept', 'conceptId': identifier,
                          'sourceGroup': group, 'reason': context, 'author': actor_reference,
                          'reviewer': None, 'admitted': False})
        for index in indices:
            if len(observations) >= 128:
                break
            original = aliases[group][index]
            pointer = '/' + _pointer(group) + '/' + str(index)
            ac = citation(ALIAS, pointer)
            original_text = text(original, 'und', ac, [ALIAS, pointer])
            node['names'].append(original_text)
            interpretation = {'id': _id('interpretation', digest([PINS[ALIAS][0], pointer, CURATION_VERSION])),
                'textId': original_text['id'], 'language': 'en', 'value': group,
                'sourceTextSha256': original_text['sourceTextSha256'],
                'translator': 'source-published English lexical-group key; deterministic curation ' + CURATION_VERSION,
                'method': 'source-published', 'status': 'draft', 'citationIds': [ac],
                'terminologyResourceIds': [identifier]}
            packet['translations'].append(interpretation)
            observations.append({'id': original_text['id'], 'sourcePath': ALIAS, 'pointer': pointer,
                'sourceSHA256': PINS[ALIAS][0], 'original': original, 'language': 'und',
                'sourceEnglishKey': group, 'englishInterpretationId': interpretation['id'],
                'interpretationScope': 'source grouping hypothesis, not an accepted standalone translation or exact semantic match',
                'conceptId': identifier, 'decisionId': _id('decision', key),
                'mappingState': 'proposed-contextual; not accepted exactMatch', 'citationId': ac})
    for child, parent in [('i04', 'i03'), ('i08', 'i07')]:
        relation(_id('ingredient', child), 'broaderMatch', _id('ingredient', parent),
                 citation(ALIAS, '/cooked rice' if child == 'i04' else '/milk'), ALIAS)

    unit_citation = citation('contracts/corpus/common-data-contract.json', '/units')
    for label, unit in contract['units'].items():
        resource(unit['id'], 'Unit', label, unit_citation,
                 unit['dimension'] + '; ' + unit['conversionPolicy'])
    # Basis is the workbook reporting-limit header, NOT a food measurement.
    basis = _id('quantity', 'afcd-reporting-reference-100g')
    metadata = {'sourceId': nutrients['sourceId'], 'release': nutrients['release'],
                'url': nutrients['licenseUrl'], 'license': nutrients['licenseUrl'],
                'attribution': 'Australian Food Composition Database Release 3; limitations and country notice retained'}
    bc = citation(AFCD, '/definitions/Proximates/2/4', metadata=metadata)
    resource(basis, 'Quantity', '100 g reporting-limit reference basis', bc,
             'Reporting-limit header only; no product nutrient amount or measured recipe basis.')
    relation(basis, 'hasUnit', contract['units']['g']['id'], bc, AFCD + '#/definitions/Proximates/2/4')
    for index in range(3, 11):
        row = nutrients['definitions']['Proximates'][index]
        pointer = '/definitions/Proximates/' + str(index)
        cid = citation(AFCD, pointer, metadata=metadata)
        identifier = _id('nutrient-definition', 'afcd-r3-proximates-row-' + str(index))
        resource(identifier, 'NutrientDefinition', row[0], cid,
                 'AFCD source definition; row/method/basis retained independently, not a food measurement.')
        native_unit = row[1]
        resolved = contract['units'].get(native_unit)
        if resolved:
            relation(identifier, 'hasUnit', resolved['id'], cid, AFCD + '#' + pointer + '/1', 'source-asserted')
        definition_rows.append({'conceptId': identifier, 'sourceId': nutrients['sourceId'],
            'release': nutrients['release'], 'sheet': 'Proximates', 'serializedRowIndex': index,
            'originalWorkbookRow': None, 'pointer': pointer, 'row': deepcopy(row),
            'cells': [{'pointer': pointer + '/' + str(i), 'value': value} for i, value in enumerate(row)],
            'nativeUnit': native_unit, 'unitId': resolved['id'] if resolved else None,
            'reportingLimitBasisId': basis, 'basisScope': 'reporting limit only',
            'citationId': cid, 'foodMeasurement': False})
    # One explicit preparation concept, distinct from the rice family/ingredient.
    pc = citation(ALIAS, '/cooked rice')
    preparation = _id('preparation', 'source-explicit-cooked')
    resource(preparation, 'PreparationState', 'Cooked, process unspecified', pc,
             'Explicit lexical cooked state; method, retention and yield unknown.')
    relation(_id('ingredient', 'i04'), 'hasPreparationState', preparation, pc, ALIAS + '#/cooked rice')

    product_observations = []
    for photo in photos:
        cid = citation(PHOTO, '/OFF_PHOTOS/' + photo['key'], metadata={
            'sourceId': 'off', 'url': photo['sourcePage'], 'license': photo['licenseUrl'],
            'attribution': 'Open Food Facts; publisher-reported contributor ' + photo['contributor']})
        identifier = _id('product-observation', photo['sourceCode'] + '-' + photo['revision'])
        resource(identifier, 'SourceRecord', 'Publisher product observation ' + photo['sourceCode'], cid,
                 'Photo/product metadata observation only; no food/nonfood, brand, manufacturer, ingredients or retained-image membership inference.')
        product_observations.append({'resourceId': identifier, **photo,
            'identity': 'source-asserted product/barcode observation, not universal physical product',
            'brand': None, 'manufacturer': None, 'componentIngredientIds': [],
            'mappingState': 'unknown', 'foodNonfood': 'unknown',
            'retainedSnapshotMembership': 'unverified', 'imageBytesRead': False,
            'contributorMeaning': 'publisher-reported uploader; not manufacturer/authorship proof', 'citationId': cid})

    alias_index = {}
    for obs in observations:
        # Exact spelling + supplied language only. No casefold/accent/AI dedup.
        alias_index.setdefault(obs['language'] + '\u0000' + obs['original'], []).append(obs['id'])
    interpretation_key = digest({'sources': {k: v[0] for k, v in PINS.items()},
        'curation': CURATION_VERSION, 'schema': 'offmenu-common/1', 'actor': actor_reference,
        'model': 'UNAVAILABLE', 'method': 'deterministic source-group and explicit context rules'})
    generation = {'common': packet, 'curation': {
        'generationVersion': generation_version, 'moduleVersion': VERSION, 'curationVersion': CURATION_VERSION,
        'actorReference': actor_reference, 'qualification': 'author-qualified bounded candidate; root independent review required',
        'modelVersion': 'UNAVAILABLE', 'externalModelCalls': 0, 'portableExactModelCacheQualified': False,
        'interpretationKey': interpretation_key, 'promptVersion': 'deterministic-curation-rules-in-module/1',
        'decisions': decisions, 'aliases': observations, 'concepts': concepts, 'definitions': definition_rows,
        'products': product_observations, 'aliasIndex': alias_index,
        'afcdNotices': {k: nutrients[k] for k in ('sourceId', 'release', 'licenseUrl', 'limitationStatement', 'countryNotice', 'changes')},
        'unpopulatedRequirements': ['whole/low-fat milk variants not supplied in selected rows: do not invent percentages',
            'brand/manufacturer/component membership not supplied by selected product metadata',
            'existing global registry match, real recipe fit/joins and product nutrition not selected/qualified'],
        'sources': {path: {'sha256': expected, 'bytes': size} for path, (expected, size) in PINS.items()},
        'commonContractSourceSHA256': contract_sha,
        'counts': {'foundAssets': 3, 'parsedAssets': 3, 'sourceAliasGroups': len(aliases),
            'selectedLexicalObservations': len(observations), 'englishInterpretations': len(observations),
            'ingredientConceptCandidates': len(RULES), 'unitConceptCandidates': 14,
            'nutrientDefinitionCandidates': 8, 'preparationCandidates': 1, 'quantityBasisCandidates': 1,
            'productObservations': len(photos), 'normalizedCandidateResources': len(packet['resources']),
            'proposedContextualMappings': len(observations), 'independentlyReviewed': 0,
            'rootAdmitted': 0, 'GoldAdmitted': 0},
        'holds': ['private local candidate only', 'original languages und where unspecified',
            'no new source/store/model permission', 'no actual ingredient fit/nutrition/recipe/country/runtime acceptance']}}
    if len(packet['resources']) > 64 or len(packet['relations']) > 256 or len(canonical(generation)) > MAX_OUTPUT:
        raise ValueError('generation bounds')
    generation['curation']['commonSHA256'] = digest(packet)
    return generation


def propose_revision(previous, *, version, decisions):
    """Preserve old identities; stage explicit versioned match/correct/merge/split.

    Proposed redirects are not activated by flags in source JSON. Existing caller
    review/00 custody must qualify and adopt a successor separately.
    """
    if len(canonical(previous)) > MAX_OUTPUT or len(canonical(decisions)) > MAX_INPUT:
        raise ValueError('revision bounds')
    if digest(previous['common']) != previous['curation']['commonSHA256']:
        raise ValueError('previous packet changed')
    if not isinstance(version, str) or not version.strip() or version == previous['curation']['generationVersion']:
        raise ValueError('new explicit generation version required')
    if type(decisions) is not list or len(decisions) > 32:
        raise ValueError('bounded explicit decisions required')
    known = {r['id'] for r in previous['common']['resources']}
    proposals = []
    for decision in decisions:
        if decision.get('action') not in ('existing-match', 'new-concept', 'correction', 'merge', 'split') or not decision.get('decisionId'):
            raise ValueError('explicit curation action/ID required')
        if any(i not in known for i in decision.get('sourceIds', [])):
            raise ValueError('unknown redirect source')
        if not decision.get('reason') or not decision.get('evidenceReference'):
            raise ValueError('decision evidence required')
        proposals.append({**deepcopy(decision), 'state': 'review-candidate-not-activated'})
    return {'previousCommonSHA256': digest(previous['common']), 'previousVersion': previous['curation']['generationVersion'],
            'version': version, 'decisions': proposals, 'originalResourcesUnchanged': True,
            'requiresIndependentReviewAnd00Adoption': True}


def inspect_generation(generation, *, alias=None, definition_id=None):
    """Bounded readback of the NEW caller-owned JSON, not any existing store."""
    c = generation['curation']
    if digest(generation['common']) != c['commonSHA256']:
        raise ValueError('common packet changed')
    if alias is not None:
        ids = set(c['aliasIndex'].get('und\u0000' + alias, []))
        selected = [r for r in c['aliases'] if r['id'] in ids]
        targets = {r['conceptId'] for r in selected}
        return {'sourceAliases': deepcopy(selected),
                'concepts': [deepcopy(r) for r in c['concepts'] if r['id'] in targets],
                'familyRelations': [deepcopy(r) for r in generation['common']['relations'] if r['subjectId'] in targets],
                'actualProductFit': False}
    return {'definitions': [deepcopy(r) for r in c['definitions'] if r['conceptId'] == definition_id],
            'unitRelations': [deepcopy(r) for r in generation['common']['relations'] if r['subjectId'] == definition_id],
            'foodMeasurement': False}


def persist_new_generation(directory, generation):
    """Exclusive new owned directory only; never overwrite/adopt an existing store."""
    raw = canonical(generation)
    if len(raw) > MAX_OUTPUT:
        raise ValueError('output bounds')
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    path = directory / 'generation.json'
    with path.open('xb') as handle:
        handle.write(raw + b'\n')
    manifest = {'generationVersion': generation['curation']['generationVersion'],
                'generationSHA256': sha256(raw + b'\n').hexdigest(),
                'commonSHA256': digest(generation['common']), 'counts': generation['curation']['counts'],
                'state': 'populated-private-author-candidate-not-00-admitted',
                'sources': deepcopy(generation['curation']['sources'])}
    with (directory / 'manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write('\n')
    return manifest
