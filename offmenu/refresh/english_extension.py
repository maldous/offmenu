"""Pure linked-evidence callback for the existing SourceContract boundary.

Reviewed callers supply the resolver/policy; source JSON cannot construct them.
No file/network/model IO, graph output, registry entry or admission is installed.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import date
import hashlib
import re
from typing import Protocol
from jsonschema import Draft202012Validator
from .acceptance import Asset, SourceContract, contract_fingerprint, fingerprint, canonical, _local_schema
from .core import strict_json


DIAGNOSTICS = frozenset((
    'english-ambiguity-reference-unresolved',
    'english-assertion-id-duplicate',
    'english-claim-evidence-unresolved',
    'english-claim-fixture-scope-mismatch',
    'english-claim-iri-unresolved',
    'english-claim-qualification-invalid',
    'english-claim-record-mismatch',
    'english-claim-role-invalid',
    'english-claim-source-mismatch',
    'english-conflict-decision-unqualified',
    'english-conflict-id-duplicate',
    'english-conflict-reference-unresolved',
    'english-effective-period-invalid',
    'english-effective-period-unresolved',
    'english-evidence-bound-exceeded',
    'english-evidence-work-bound-exceeded',
    'english-evidence-invalid',
    'english-evidence-pin-invalid',
    'english-evidence-pin-mismatch',
    'english-extension-schema-invalid',
    'english-food-form-mismatch',
    'english-food-form-unresolved',
    'english-formulation-unresolved',
    'english-identity-unresolved',
    'english-identity-state-inconsistent',
    'english-relationship-unqualified',
    'english-literal-zero-inconsistent',
    'english-native-line-mismatch',
    'english-native-page-unresolved',
    'english-native-range-invalid',
    'english-native-schema-mismatch',
    'english-native-span-mismatch',
    'english-normalization-permission-missing',
    'english-original-pin-mismatch',
    'english-parser-version-mismatch',
    'english-permission-contract-mismatch',
    'english-permission-unqualified',
    'english-pointer-invalid',
    'english-pointer-unresolved',
    'english-policy-binding-mismatch',
    'english-product-context-unresolved',
    'english-product-state-inconsistent',
    'english-quantity-binding-mismatch',
    'english-quantity-unqualified',
    'english-record-line-invalid',
    'english-schema-pin-mismatch',
    'english-selected-artifact-mismatch',
    'english-selected-record-mismatch',
    'english-source-contract-mismatch',
    'english-source-operation-unqualified',
    'english-source-record-mismatch',
    'english-subfield-locator-unqualified',
    'english-subfield-text-mismatch',
    'english-translation-permission-missing',
    'english-usability-predicate-unregistered',
    'english-use-context-mismatch',
    'english-use-scope-pin-mismatch',
    'english-use-scope-unresolved',
    'english-use-time-mismatch',
    'english-variant-record-duplicate',
))


class EvidenceError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise EvidenceError(code)


def pointer(value, path):
    """RFC6901 lookup only: no invalid escapes, append token or index coercion."""
    require(isinstance(path, str) and (path == '' or path.startswith('/'))
            and not re.search(r'~(?![01])', path), 'english-pointer-invalid')
    for token in path.split('/')[1:] if path else ():
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            require(bool(re.fullmatch(r'0|[1-9][0-9]*', token)), 'english-pointer-invalid')
            require(int(token) < len(value), 'english-pointer-unresolved')
            value = value[int(token)]
        else:
            require(isinstance(value, dict) and token in value, 'english-pointer-unresolved')
            value = value[token]
    return value


@dataclass(frozen=True)
class Grant:
    contract: SourceContract
    purposes: frozenset


@dataclass(frozen=True)
class ResolvedClaim:
    contract: SourceContract
    qualification: dict
    artifact: dict
    record_pointer: str
    line: int


@dataclass(frozen=True)
class ReviewedWitness:
    """A reviewed resolver decision, never created from a sidecar's evidence."""
    pin: dict
    scope: dict
    authority: str


@dataclass(frozen=True)
class EnglishPolicy:
    schema: dict
    schema_sha256: str
    input_contract: SourceContract
    original_asset: Asset
    parsed_asset: Asset
    policy_pins: dict
    source_record_id: str
    record_format: str
    record_line: object
    record_pointer: str
    parser_version: str = 'offmenu-source-faithful-recipe-parser/1.3.2'
    transform_version: str = 'offmenu-assistant-intermediate-to-source-recipe/1.0.2'
    max_evidence_bytes: int = 8 * 1024 * 1024
    review_authorities: frozenset = frozenset()
    max_total_evidence_bytes: int = 32 * 1024 * 1024
    max_evidence_reads: int = 1024


class Resolver(Protocol):
    """Trusted code interface, never resolved through a source plugin/CLI flag.

    evidence returns already-selected bytes; page returns qualified native text.
    claim returns an existing source qualification, not an opaque-ID-to-IRI cast.
    use/record/subfield results and graph bindings belong to reviewed mappings.
    """
    def evidence(self, pin): ...
    def page(self, record_id, page): ...
    def grant(self, pin, purpose): ...
    def claim(self, lexical_id): ...
    def graph_role(self, iri): ...
    def graph_binding(self, relation): ...
    def use(self, assertion_id): ...
    def record(self, record_id): ...
    def subfield(self, record_id, field_pointer): ...
    def quantity(self, assertion_id): ...
    def decision(self, conflict_id): ...
    def relationship(self, assertion_id): ...


class _Check:
    def __init__(self, policy, resolver):
        self.p, self.r = policy, resolver
        self.verified_evidence = {}
        self.evidence_bytes = 0
        self.evidence_reads = 0

    def evidence(self, pin):
        require(isinstance(pin, dict) and set(pin) == {'path', 'sha256'}
                and isinstance(pin['path'], str) and isinstance(pin['sha256'], str),
                'english-evidence-pin-invalid')
        key = (pin['path'], pin['sha256'])
        if key in self.verified_evidence:
            return self.verified_evidence[key]
        # Bound dispatches before invoking trusted resolver code, and hash each
        # selected immutable byte snapshot only once during this validation.
        require(self.evidence_reads < self.p.max_evidence_reads,
                'english-evidence-work-bound-exceeded')
        self.evidence_reads += 1
        raw = self.r.evidence(pin)
        require(isinstance(raw, bytes) and len(raw) <= self.p.max_evidence_bytes,
                'english-evidence-pin-mismatch')
        require(len(raw) <= self.p.max_total_evidence_bytes - self.evidence_bytes,
                'english-evidence-work-bound-exceeded')
        self.evidence_bytes += len(raw)
        require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'english-evidence-pin-mismatch')
        self.verified_evidence[key] = raw
        return raw

    def record(self, pin, line, path):
        raw = self.evidence(pin)
        if line is not None:
            require(type(line) is int and line >= 1, 'english-record-line-invalid')
            lines = raw.split(b'\n')
            require(line < len(lines), 'english-record-line-invalid')
            raw = lines[line - 1]
        return pointer(strict_json(raw), path)

    def contract(self, contract, source, release):
        require(isinstance(contract, SourceContract) and not contract.holds
                and {'retain', 'parse', 'transform'} <= contract.required_operations
                and {'retain', 'parse', 'transform'} <= contract.permitted_operations
                and contract.required_operations <= contract.permitted_operations
                and contract.rights_evidence in contract.inputs
                and contract.scope_evidence in contract.inputs,
                'english-source-operation-unqualified')
        require((contract.source_id, contract.release_id) == (source, release),
                'english-source-contract-mismatch')

    def reviewed(self, witness, expected, code):
        require(isinstance(witness, ReviewedWitness)
                and witness.authority in self.p.review_authorities, code)
        require(strict_json(self.evidence(witness.pin)) == witness.scope
                and witness.scope == {**expected, 'reviewAuthority': witness.authority}, code)

    def claim_context(self, lexical_id, role, resolved=None):
        resolved = self.r.claim(lexical_id) if resolved is None else resolved
        data = self.claim(lexical_id, role, resolved)
        return data, {'claimId': lexical_id, 'artifact': resolved.artifact,
                      'recordPointer': resolved.record_pointer, 'line': resolved.line,
                      'qualificationSha256': resolved.qualification['qualificationSha256'],
                      'contractSha256': contract_fingerprint(resolved.contract),
                      'dataSha256': fingerprint(data)}

    def relationship(self, assertion, inp, kind, context):
        self.reviewed(self.r.relationship(assertion['assertionId']),
                      {'type': kind, 'assertionId': assertion['assertionId'],
                       'assertionSha256': fingerprint(assertion), 'relation': assertion['relation'],
                       'inputBinding': inp, 'decisionState': 'affirmed',
                       'reviewStatus': 'reviewed', **context}, 'english-relationship-unqualified')

    def anchor(self, record, field):
        target = pointer(record, field['fieldPointer'])
        if isinstance(target, dict) and 'location' in target:
            loc = target['location']
        else:
            # A word/subfield cannot silently inherit the whole ingredient line.
            locator = self.r.subfield(record['source']['sourceRecordId'], field['fieldPointer'])
            require(isinstance(locator, dict) and set(locator) == {'pin', 'recordId', 'fieldPointer', 'location'}, 'english-subfield-locator-unqualified')
            require(locator['recordId'] == record['source']['sourceRecordId'] and locator['fieldPointer'] == field['fieldPointer'] and strict_json(self.evidence(locator['pin'])) == {k: v for k, v in locator.items() if k != 'pin'}, 'english-subfield-locator-unqualified')
            loc = locator['location']
        require(type(loc.get('page')) is int and loc['page'] >= 1, 'english-native-page-unresolved')
        text = self.r.page(record['source']['sourceRecordId'], loc['page'])
        require(isinstance(text, str), 'english-native-page-unresolved')
        raw = text.encode('utf-8')
        start, end = loc['utf8ByteRange']
        require(type(start) is int and type(end) is int and 0 <= start < end <= len(raw),
                'english-native-range-invalid')
        # A byte range must end on UTF8 boundaries, not inside a multibyte scalar.
        raw[:start].decode('utf-8'); span = raw[start:end]; span.decode('utf-8')
        require(type(loc.get('lineStart')) is int and type(loc.get('lineEnd')) is int and loc.get('lineStart') == raw[:start].count(b'\n') + 1 and loc.get('lineEnd') == raw[:end-1].count(b'\n') + 1, 'english-native-line-mismatch')
        require(hashlib.sha256(raw).hexdigest() == loc['pageTextSHA256'] == field['pageTextSHA256']
                and hashlib.sha256(span).hexdigest() == loc['sourceSpanSHA256'] == field['sourceSpanSHA256'],
                'english-native-span-mismatch')
        if not isinstance(target, dict):
            require(isinstance(target, str) and span.decode('utf-8') == target, 'english-subfield-text-mismatch')
        return target

    def claim(self, lexical_id, role, resolved=None):
        resolved = self.r.claim(lexical_id) if resolved is None else resolved
        require(isinstance(resolved, ResolvedClaim), 'english-identity-unresolved')
        q, c = resolved.qualification, resolved.contract
        require(isinstance(c, SourceContract) and q.get('qualified') is True and q.get('errors') == []
                and q.get('status') == 'qualified'
                and q.get('contractSha256') == contract_fingerprint(c)
                and q.get('qualificationSha256') == fingerprint({k: v for k, v in q.items()
                                                               if k != 'qualificationSha256'}),
                'english-claim-qualification-invalid')
        require(c.fixture == self.p.input_contract.fixture, 'english-claim-fixture-scope-mismatch')
        raw = self.evidence(resolved.artifact)
        require(q.get('candidateSha256') == hashlib.sha256(raw).hexdigest()
                and (q.get('sourceId'), q.get('releaseId'), q.get('scopeId'))
                == (c.source_id, c.release_id, c.scope_id), 'english-claim-source-mismatch')
        row = self.record(resolved.artifact, resolved.line, resolved.record_pointer)
        require(row.get('id') == lexical_id, 'english-claim-record-mismatch')
        provenance = row.get('provenance', {})
        self.contract(c, provenance.get('sourceId'), provenance.get('releaseId'))
        data = row['data']
        require(data.get('role') == role and self.r.graph_role(data.get('graphIri')) == role,
                'english-claim-role-invalid')
        # This IRI is resolved independently; lexical_id itself need not be an IRI.
        require(bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9+.-]*:[^\s]+', data.get('graphIri', ''))),
                'english-claim-iri-unresolved')
        for pin in data.get('evidence', []):
            self.evidence(pin)
        require(bool(data.get('evidence')), 'english-claim-evidence-unresolved')
        if role == 'source-product-assignment':
            for name, expected in [('foodProduct', 'FoodProduct'), ('formulation', 'SourceRecord'),
                                   ('package', 'Package'), ('market', 'Market')]:
                dimension = data.get(name, {})
                self.evidence(dimension.get('evidence'))
                if name in ('package', 'market') and dimension.get('state') == 'not-applicable':
                    require(dimension.get('iri') is None, 'english-product-context-unresolved')
                else:
                    require(dimension.get('state') == 'bound'
                            and self.r.graph_role(dimension.get('iri')) == expected,
                            'english-product-context-unresolved')
            require(bool(data['formulation'].get('snapshotId')), 'english-formulation-unresolved')
            period = data.get('effectivePeriod', {})
            self.evidence(period.get('evidence'))
            require(period.get('state') == 'bound' and period.get('from') and period.get('to'),
                    'english-effective-period-unresolved')
            require(date.fromisoformat(period['from']) <= date.fromisoformat(period['to']),
                    'english-effective-period-invalid')
        elif role == 'ingredient-identity':
            form = data.get('foodForm', {})
            require(all(isinstance(form.get(k), str) and form[k] not in ('', 'unknown')
                        for k in ('materialState', 'part', 'preparation')),
                    'english-food-form-unresolved')
        return data

    def check(self, extension):
        require(all(type(value) is int and value > 0 for value in
                    (self.p.max_total_evidence_bytes, self.p.max_evidence_reads)),
                'english-evidence-work-bound-exceeded')
        require(len(canonical(extension)) <= self.p.max_evidence_bytes, 'english-evidence-bound-exceeded')
        require(_local_schema(self.p.schema) and fingerprint(self.p.schema) == self.p.schema_sha256,
                'english-schema-pin-mismatch')
        require(Draft202012Validator(self.p.schema).is_valid(extension), 'english-extension-schema-invalid')
        inp = extension['input']; asset = self.p.parsed_asset
        require(inp['parsedArtifact'] == {'path': asset.path, 'sha256': asset.sha256},
                'english-selected-artifact-mismatch')
        require(len(self.evidence(inp['parsedArtifact'])) == asset.bytes, 'english-selected-artifact-mismatch')
        require(inp['sourceRecordId'] == self.p.source_record_id, 'english-source-record-mismatch')
        require((inp['format'], inp['recordLine'], inp['recordPointer']) == (self.p.record_format, self.p.record_line, self.p.record_pointer), 'english-selected-record-mismatch')
        self.contract(self.p.input_contract, inp['sourceId'], inp['releaseId'])
        require(self.p.original_asset in self.p.input_contract.inputs
                and inp['originalSHA256'] == self.p.original_asset.sha256,
                'english-original-pin-mismatch')
        require(inp['parserVersion'] == self.p.parser_version
                and inp['transformVersion'] in (None, self.p.transform_version),
                'english-parser-version-mismatch')
        require(extension['policies'] == self.p.policy_pins, 'english-policy-binding-mismatch')
        for pin in extension['policies'].values():
            if pin is not None: self.evidence(pin)
        record = self.record(inp['parsedArtifact'], inp['recordLine'], inp['recordPointer'])
        src = record['source']
        require((src.get('sourceId'), src.get('releaseId'), src.get('sourceRecordId'), src.get('originalSHA256'))
                == (inp['sourceId'], inp['releaseId'], inp['sourceRecordId'], inp['originalSHA256']),
                'english-source-record-mismatch')
        require(record.get('recipeTemplate', record.get('menuTemplate')) == inp['extractionSchema'],
                'english-native-schema-mismatch')
        for perm in extension['permissions']:
            for pin in perm['evidence']: self.evidence(pin)
            if perm['state'] == 'permitted':
                self.evidence(perm['reviewedContractPin'])
                grant = self.r.grant(perm['reviewedContractPin'], perm['purpose'])
                require(isinstance(grant, Grant) and perm['purpose'] in grant.purposes,
                        'english-permission-unqualified')
                self.contract(grant.contract, inp['sourceId'], inp['releaseId'])
                require(contract_fingerprint(grant.contract) == contract_fingerprint(self.p.input_contract),
                        'english-permission-contract-mismatch')
        purposes = {p['purpose']: p['state'] for p in extension['permissions']}
        if extension['translations']:
            require(purposes['translation'] == 'permitted', 'english-translation-permission-missing')
        if any(extension[k] for k in ('quantityNormalizations', 'ingredientIdentityAssertions',
                                      'variantAssertions', 'productIngredientLinks', 'usableAsAssertions')):
            require(purposes['normalization'] == 'permitted', 'english-normalization-permission-missing')
        sections = ('translations', 'quantityNormalizations', 'ingredientIdentityAssertions',
                    'variantAssertions', 'productIngredientLinks', 'usableAsAssertions')
        assertions = [a for name in sections for a in extension[name]]
        ids = [a['assertionId'] for a in assertions]
        require(len(ids) == len(set(ids)), 'english-assertion-id-duplicate')
        conflict_ids = [c['conflictId'] for c in extension['conflicts']]
        require(len(conflict_ids) == len(set(conflict_ids)), 'english-conflict-id-duplicate')
        for a in assertions:
            for pin in a['evidence']: self.evidence(pin)
            if 'target' in a: self.anchor(record, a['target'])
        for t in extension['translations']:
            require(set(t['ambiguityIds']) <= set(conflict_ids), 'english-ambiguity-reference-unresolved')
        for q in extension['quantityNormalizations']:
            node = self.anchor(record, q['target'])
            if q['sourceValueState'] == 'literal-zero':
                lexical = node.get('quantity', {}).get('rawValueLexeme') if isinstance(node, dict) else None
                require(lexical is not None and Decimal(lexical) == 0
                        and (q['normalizedValue'] is None or Decimal(q['normalizedValue']) == 0),
                        'english-literal-zero-inconsistent')
            for key in ('factorPin', 'basisPin'):
                if q[key] is not None: self.evidence(q[key])
            if q['sourceValueState'] != 'unresolved' or q['normalizedValue'] is not None or q['boundValue'] is not None:
                binding = self.r.quantity(q['assertionId'])
                require(isinstance(binding, dict) and strict_json(self.evidence(binding['pin'])) == binding['scope'], 'english-quantity-unqualified')
                require(binding['scope'] == {'sourceRecordId': inp['sourceRecordId'], 'originalSHA256': inp['originalSHA256'], 'target': q['target'], **{k: q[k] for k in ('sourceValueState', 'normalizedValue', 'normalizedUnit', 'sourceBasis', 'normalizedBasis', 'comparison', 'boundValue', 'conversionKind', 'factorPin', 'basisPin')}}, 'english-quantity-binding-mismatch')
        for a in extension['ingredientIdentityAssertions']:
            require((a['state'] == 'unresolved') == (a['relation'] == 'unresolved')
                    and (a['ingredientIdentityClaimId'] is not None or a['state'] == 'unresolved'),
                    'english-identity-state-inconsistent')
            if a['ingredientIdentityClaimId'] is not None:
                ingredient, ingredient_version = self.claim_context(a['ingredientIdentityClaimId'], 'ingredient-identity')
                require(a['foodForm'] == ingredient['foodForm'], 'english-food-form-mismatch')
                if a['state'] == 'reviewed':
                    self.relationship(a, inp, 'native-ingredient-identity',
                                      {'target': a['target'], 'ingredient': ingredient_version,
                                       'foodForm': ingredient['foodForm']})
        for a in extension['variantAssertions']:
            require(len(a['sourceRecordRefs']) == len(set(a['sourceRecordRefs'])),
                    'english-variant-record-duplicate')
            source_records = []
            for ref in a['sourceRecordRefs']:
                if ref == inp['sourceRecordId']:
                    source_records.append({'sourceRecordId': ref, 'inputBinding': inp})
                else:
                    resolved = self.r.record(ref)
                    require(isinstance(resolved, ResolvedClaim), 'english-identity-unresolved')
                    _, version = self.claim_context(ref, 'recipe-source-record', resolved)
                    source_records.append(version)
            if a['state'] == 'reviewed':
                self.relationship(a, inp, 'recipe-variant-relationship',
                                  {'region': a['region'], 'sourceRecords': source_records})
        for a in extension['productIngredientLinks']:
            require((a['state'] == 'unresolved') == (a['relation'] == 'unresolved'),
                    'english-product-state-inconsistent')
            product, product_version = self.claim_context(a['productIdentityClaimId'], 'source-product-assignment')
            ingredient, ingredient_version = self.claim_context(a['ingredientIdentityClaimId'], 'ingredient-identity')
            if a['state'] == 'reviewed':
                self.relationship(a, inp, 'product-ingredient-relationship',
                                  {'product': product_version, 'ingredient': ingredient_version,
                                   'productContext': {k: product[k] for k in
                                                      ('foodProduct', 'formulation', 'package', 'market', 'effectivePeriod')},
                                   'foodForm': ingredient['foodForm']})
        for a in extension['usableAsAssertions']:
            if a['state'] == 'unresolved': continue  # Neither positive nor negative is inferred.
            product = self.claim(a['productIdentityClaimId'], 'source-product-assignment')
            ingredient = self.claim(a['ingredientIdentityClaimId'], 'ingredient-identity')
            binding = self.r.use(a['assertionId'])
            require(isinstance(binding, dict), 'english-use-scope-unresolved')
            raw = self.evidence(binding['pin'])
            require(strict_json(raw) == binding['scope'], 'english-use-scope-pin-mismatch')
            use = binding['scope']; registered = self.r.graph_binding('usableAs')
            require(use.get('inputBinding') == {k: inp[k] for k in ('sourceId', 'releaseId', 'sourceRecordId', 'originalSHA256', 'parsedArtifact')}, 'english-use-context-mismatch')
            require(registered is not None and use.get('predicate') == registered,
                    'english-usability-predicate-unregistered')
            require(use.get('decisionState') == a['state']
                    and use.get('productClaim') == a['productIdentityClaimId']
                    and use.get('ingredientClaim') == a['ingredientIdentityClaimId']
                    and use.get('formulationSnapshot') == product['formulation']['snapshotId']
                    and use.get('package') == product['package']['iri']
                    and use.get('market') == product['market']['iri']
                    and use.get('foodForm') == ingredient['foodForm']
                    and use.get('requiredFoodForm') == a['requiredFoodForm']
                    and use.get('conditions') == a['useConditions'], 'english-use-context-mismatch')
            require(date.fromisoformat(product['effectivePeriod']['from']) <= date.fromisoformat(use.get('effectiveAt', ''))
                    <= date.fromisoformat(product['effectivePeriod']['to']), 'english-use-time-mismatch')
            if a['recipeRecordRef'] is None:
                require(use.get('recipeRecordRef') is None and bool(use.get('alternativeScope')), 'english-use-scope-unresolved')
                self.claim(use['alternativeScope'], 'reviewed-use-scope', self.r.record(use['alternativeScope']))
            else:
                require(use.get('recipeRecordRef') == a['recipeRecordRef'], 'english-use-scope-unresolved')
                if a['recipeRecordRef'] != inp['sourceRecordId']:
                    self.claim(a['recipeRecordRef'], 'recipe-source-record', self.r.record(a['recipeRecordRef']))
        for c in extension['conflicts']:
            require(set(c['competingAssertionIds']) <= set(ids), 'english-conflict-reference-unresolved')
            if c['decisionPin'] is not None:
                decision = self.r.decision(c['conflictId'])
                require(isinstance(decision, ReviewedWitness) and decision.pin == c['decisionPin'],
                        'english-conflict-decision-unqualified')
                versions = {a['assertionId']: fingerprint(a) for a in assertions}
                self.reviewed(decision,
                              {'type': 'conflict-resolution', 'conflictId': c['conflictId'],
                               'conflictSha256': fingerprint({k: v for k, v in c.items() if k != 'decisionPin'}),
                               'inputBinding': inp,
                               'competingAssertions': [{'assertionId': key, 'sha256': versions[key]}
                                                       for key in c['competingAssertionIds']],
                               'decisionState': c['state'], 'reviewStatus': 'reviewed',
                               'outcome': 'resolution-affirmed' if c['state'] == 'resolved' else 'unresolved-retained'},
                              'english-conflict-decision-unqualified')
        return ()


def validate_extension(extension, policy, resolver):
    """Fixed diagnostics, no source values/exception text and no mutation."""
    try:
        return _Check(policy, resolver).check(extension)
    except EvidenceError as error:
        return (str(error) if str(error) in DIAGNOSTICS else 'english-evidence-invalid',)
    except Exception:
        return ('english-evidence-invalid',)


def semantic_validator(policy, resolver):
    """Compose with existing reviewed SourceContract.semantic_validator(row)."""
    return lambda row: validate_extension(row.get('data'), policy, resolver)
