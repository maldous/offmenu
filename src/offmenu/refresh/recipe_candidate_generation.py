"""Generated-fixture preparation only. No reader, fetcher, database or admission API.

Uses offmenu-common/1 unchanged. This adapter does not allocate food concepts,
infer aliases, convert quantities, resolve alternatives or establish source rights.
Real-input support requires a separately selected operation and source cut.
"""
import hashlib
import json
import re

CONTRACT_SHA256 = 'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa'
SCHEMA_SHA256 = 'f1968889c5e1500e841517bd7546af9c223bf97dce40bb68a3f584e93559298c'
NS = 'urn:offmenu:candidate:worker13:recipe-generation2:fixture:'
EXCLUDED_ASSETS = frozenset(('apps/web/assets/afcd-nutrient-details.json',
    'apps/web/src/off-photo-catalogue.js', 'apps/web/assets/recipe-ingredient-aliases.json'))
MAX_BYTES, MAX_RECIPES, MAX_MENTIONS = 65536, 8, 32


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _bounded(value, depth=0):
    if depth > 8:
        raise ValueError('fixture nesting exceeds eight')
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('string field names required')
        for item in value.values():
            _bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1)
    elif value is not None and type(value) not in (str, bool, int, float):
        raise ValueError('JSON values only')


def _nonempty(obj, name):
    value = obj.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing nonempty ' + name)
    return value


def _language(value):
    if not isinstance(value, str) or not re.fullmatch(
            '[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', value):
        raise ValueError('language must be an explicit code or absent')
    return value


def build_generated_fixture(records, contract_raw, schema_raw, *, actor):
    """Project generated already-parsed envelopes, never actual corpus bodies.

    The fixture namespace and strict generated sourceId prefix deliberately
    prevent this preparation entrypoint from masquerading as a data operation.
    Every optional source field, including null/empty values, remains separate.
    """
    if digest(contract_raw) != CONTRACT_SHA256 or digest(schema_raw) != SCHEMA_SHA256:
        raise ValueError('shared contract/schema pin mismatch')
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError('actor required')
    if not isinstance(records, list) or not records or len(records) > MAX_RECIPES:
        raise ValueError('fixture requires one to eight recipes')
    _bounded(records)
    if len(canonical(records)) > MAX_BYTES:
        raise ValueError('fixture input exceeds 64KiB')
    contract = json.loads(contract_raw)
    scope = {'visibility': 'private', 'ownerId': actor,
             'reuseScope': 'generated-fixture-only; not corpus or admission evidence'}
    out = {'schemaVersion': 'offmenu-common/1', 'resources': [], 'assertions': [],
           'relations': [], 'citations': [], 'translations': []}
    seen = set()
    mention_count = 0

    def ident(kind, context):
        return NS + kind + ':' + digest(canonical(context))

    def text(value, language, citation, context):
        return {'kind': 'text', 'id': ident('text', context), 'language': language,
                'value': value, 'sourceTextSha256': digest(value.encode()),
                'status': 'candidate', 'citationIds': [citation]}

    def typed(value, language, citation, context):
        if value is None:
            return {'kind': 'null', 'value': None}
        if type(value) is bool:
            return {'kind': 'boolean', 'value': value}
        if type(value) in (int, float):
            return {'kind': 'number', 'value': value}
        if isinstance(value, str):
            return text(value, language, citation, context)
        if isinstance(value, list):
            return {'kind': 'list', 'items': [typed(v, language, citation,
                    context + [i]) for i, v in enumerate(value)]}
        return {'kind': 'structure', 'fields': {k: typed(v, language, citation,
                context + [k]) for k, v in sorted(value.items())}}

    def resource(kind, context, citation, names=()):
        rid = ident(kind, context)
        out['resources'].append({'id': rid, 'type': contract['types'][kind]['id'],
            'identityStatus': 'source-scoped', 'names': list(names),
            'citationIds': [citation], 'scope': scope.copy()})
        return rid

    def assertion(subject, prop, value, path, context, citation):
        out['assertions'].append({'id': ident('assertion', context),
            'subjectId': subject, 'propertyId': prop, 'value': value,
            'status': 'candidate', 'citationIds': [citation], 'sourcePath': path,
            'scope': scope.copy()})

    for record in records:
        if not isinstance(record, dict):
            raise ValueError('recipe must be an object')
        source = _nonempty(record, 'sourceId')
        if not source.startswith('urn:offmenu:generated:'):
            raise ValueError('actual source inputs are not admitted')
        if record.get('assetPath') in EXCLUDED_ASSETS:
            raise ValueError('first-generation asset excluded')
        for key in ('recordId', 'revision', 'pointer'):
            _nonempty(record, key)
        if not record['pointer'].startswith('/'):
            raise ValueError('source JSON pointer required')
        if not re.fullmatch('[a-f0-9]{64}', record.get('contentSha256', '')):
            raise ValueError('source content hash required')
        context = [source, record['revision'], record['recordId'],
                   record['contentSha256'], record['pointer']]
        key = tuple(context)
        if key in seen:
            raise ValueError('duplicate recipe occurrence; reconcile outside adapter')
        seen.add(key)
        language = _language(record.get('language', 'und'))
        mentions = record.get('mentions')
        if not isinstance(mentions, list):
            raise ValueError('mentions list required')
        mention_count += len(mentions)
        if mention_count > MAX_MENTIONS:
            raise ValueError('fixture exceeds 32 mentions')
        citation = ident('citation', context)
        out['citations'].append({'id': citation, 'sourceId': source,
            'originalRecordId': record['recordId'], 'originalUrl': source,
            'revisionId': record['revision'], 'contentSha256': record['contentSha256'],
            'license': 'generated-test-fixture-only', 'attribution': actor,
            'sourcePath': record['pointer'], 'scope': scope.copy()})
        recipe = resource('RecipeDiscoveryReference', context, citation)
        assertion(recipe, contract['sharedProperties']['automaticPlanningEligible']['id'],
                  {'kind': 'boolean', 'value': False}, record['pointer'],
                  context + ['planning'], citation)
        for field, value in sorted(record.items()):
            if field == 'mentions':
                continue
            prop = contract['sourcePropertyExtensions']['namespace'] + 'recipe-envelope-' + field.encode().hex()
            assertion(recipe, prop, typed(value, language, citation, context + ['envelope', field]),
                      record['pointer'], context + ['field', field], citation)
        pointers = set()
        for mention in mentions:
            if not isinstance(mention, dict):
                raise ValueError('mention object required')
            path = _nonempty(mention, 'pointer')
            if not path.startswith(record['pointer'] + '/') or path in pointers:
                raise ValueError('mention pointer must be unique within recipe')
            pointers.add(path)
            wording = mention.get('text')
            if not isinstance(wording, str):
                raise ValueError('source wording string required')
            # Edition/envelope language is not occurrence-language evidence.
            # An explicit occurrence wins; absent occurrence evidence stays und.
            occurrence_language = _language(mention.get('language', 'und'))
            mc = context + [path]
            name = text(wording, occurrence_language, citation, mc + ['text'])
            mid = resource('IngredientMention', mc, citation, [name])
            assertion(mid, contract['sharedProperties']['originalIngredientStatement']['id'],
                      name, path, mc + ['original'], citation)
            out['relations'].append({'id': ident('relation', mc), 'subjectId': recipe,
                'predicateId': contract['relationshipVocabulary']['mentionsIngredient']['id'],
                'objectId': mid, 'status': 'candidate', 'citationIds': [citation],
                'sourcePath': path, 'scope': scope.copy()})
            # Raw alias/preparation/quantity/basis/alternatives are source fields.
            # Their names never become semantic predicates or canonical matches.
            for field, value in sorted(mention.items()):
                if field in ('text', 'pointer'):
                    continue
                prop = contract['sourcePropertyExtensions']['namespace'] + 'recipe-' + field.encode().hex()
                assertion(mid, prop, typed(value, occurrence_language, citation, mc + [field]),
                          path, mc + ['field', field], citation)
    for key in ('resources', 'assertions', 'relations', 'citations'):
        out[key].sort(key=lambda obj: obj['id'])
    if len(canonical(out)) > 1024 * 1024:
        raise ValueError('fixture output exceeds 1MiB')
    return out
