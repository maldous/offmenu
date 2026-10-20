"""Pure selection among reviewed productIngredientLinks; no graph or IO.

The application must independently select qualified input/endpoint inventories
and authorities. Pinned JSON cannot construct that authority or a source grant.
"""
from copy import deepcopy
from dataclasses import dataclass

from .acceptance import SourceContract, fingerprint
from .core import strict_json
from .english_extension import _Check, EvidenceError, ReviewedWitness, require, DIAGNOSTICS

VERSION = 'offmenu-deterministic-association/1'
METRICS_VERSION = 'offmenu-association-uncertainty-draft/1'
CATEGORIES = ('confirmed-specific', 'broader-only', 'ambiguous/conflicting',
              'unmapped/missing-evidence')
INVENTORIES = ('dictionary', 'rules', 'adjudications')
_CODES = frozenset(('selection-inventory-invalid', 'selection-inventory-version-or-bound',
    'selection-inventory-duplicate', 'selection-input-scope-mismatch', 'selection-input-unqualified',
    'selection-evidence-bounds', 'selection-inventory-unqualified', 'selection-dictionary-invalid',
    'selection-rule-invalid', 'selection-assertion-duplicate', 'selection-assertion-unqualified',
    'selection-endpoint-version', 'selection-adjudication-stale')) | DIAGNOSTICS


def _code(error):
    return str(error) if str(error) in _CODES else 'selection-invalid-evidence'


@dataclass(frozen=True)
class SelectionPolicy:
    input_contract: SourceContract
    expected_input: dict
    product_claim_id: str
    inventory_pins: dict
    inventory_versions: dict
    input_witness: ReviewedWitness | None = None
    inventory_witness: ReviewedWitness | None = None
    review_authorities: frozenset = frozenset()
    max_entries: int = 256
    max_evidence_bytes: int = 8 * 1024 * 1024
    max_total_evidence_bytes: int = 32 * 1024 * 1024
    max_evidence_reads: int = 1024


def _keys(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'selection-inventory-invalid')


def _text(value):
    require(type(value) is str and bool(value), 'selection-inventory-invalid')


def _rows(check, pin, version, id_key, keys):
    doc = strict_json(check.evidence(pin))
    _keys(doc, ('version', 'entries'))
    require(doc['version'] == version and type(doc['entries']) is list
            and len(doc['entries']) <= check.p.max_entries, 'selection-inventory-version-or-bound')
    result = {}
    for row in doc['entries']:
        _keys(row, keys); _text(row[id_key])
        require(row[id_key] not in result, 'selection-inventory-duplicate')
        result[row[id_key]] = row
    return result


def _out(category, reasons, *, binding=None, inventories=None, alternatives=(),
         assertions=(), adjudications=()):
    return {'methodVersion': VERSION, 'inputBinding': binding,
            'inventories': inventories, 'state': 'reviewed' if assertions else 'unresolved',
            'category': category, 'reasons': sorted(set(reasons)),
            'selectedAssertions': sorted(assertions, key=lambda a: a['assertionId']),
            'alternatives': sorted(alternatives, key=lambda a: a['ruleId']),
            'adjudicationIds': sorted(adjudications)}


def select_association(input_binding, policy=None, resolver=None):
    """Select existing reviewed assertions, never promote an unreviewed proposal.

    Rules match an exact qualified input binding hash, not free text. Dictionary
    specificity is independently reviewed metadata, not an inferred graph edge.
    The resolver uses only existing evidence/claim/graph_role/relationship calls.
    """
    if (type(policy) is not SelectionPolicy or resolver is None
            or type(policy.review_authorities) is not frozenset or not policy.review_authorities
            or any(type(a) is not str or not a for a in policy.review_authorities)):
        return _out(CATEGORIES[3], ['selection-unbound'])
    binding, inventories, alternatives = None, None, []
    try:
        binding, p = deepcopy(input_binding), deepcopy(policy)
        require(type(binding) is dict and binding == p.expected_input,
                'selection-input-scope-mismatch')
        require(type(p.input_contract) is SourceContract, 'selection-input-unqualified')
        for k in ('sourceId', 'releaseId', 'sourceRecordId', 'originalSHA256',
                  'qualificationSha256', 'fieldOriginsSha256'):
            require(type(binding.get(k)) is str and bool(binding[k]), 'selection-input-unqualified')
        require(all(type(v) is int and v > 0 for v in (p.max_entries, p.max_evidence_bytes,
                    p.max_total_evidence_bytes, p.max_evidence_reads)), 'selection-evidence-bounds')
        _keys(p.inventory_pins, INVENTORIES); _keys(p.inventory_versions, INVENTORIES)
        _text(p.product_claim_id)
        for v in p.inventory_versions.values(): _text(v)
        check = _Check(p, resolver)
        check.contract(p.input_contract, binding['sourceId'], binding['releaseId'])
        check.reviewed(p.input_witness,
            {'type': 'deterministic-association-input', 'inputBinding': binding,
             'purpose': 'private-relationship-selection', 'decisionState': 'affirmed',
             'reviewStatus': 'reviewed'}, 'selection-input-unqualified')
        inventories = {k: {'pin': p.inventory_pins[k], 'version': p.inventory_versions[k]}
                       for k in INVENTORIES}
        check.reviewed(p.inventory_witness,
            {'type': 'deterministic-association-inventories', 'methodVersion': VERSION,
             'inputBinding': binding, 'productClaimId': p.product_claim_id,
             'inventories': inventories, 'decisionState': 'affirmed', 'reviewStatus': 'reviewed'},
            'selection-inventory-unqualified')
        dictionary = _rows(check, p.inventory_pins['dictionary'], p.inventory_versions['dictionary'],
            'entryId', ('entryId', 'ingredientIdentityClaimId', 'ingredientVersion', 'specificity'))
        rules = _rows(check, p.inventory_pins['rules'], p.inventory_versions['rules'],
            'ruleId', ('ruleId', 'inputSha256', 'entryId', 'assertion'))
        decisions = _rows(check, p.inventory_pins['adjudications'], p.inventory_versions['adjudications'],
            'adjudicationId', ('adjudicationId', 'inputSha256', 'candidateRuleIds',
                               'selectedRuleId', 'state', 'evidence'))
        for row in dictionary.values():
            _text(row['ingredientIdentityClaimId'])
            require(row['specificity'] in ('specific', 'broader')
                    and type(row['ingredientVersion']) is dict, 'selection-dictionary-invalid')
        for rule in rules.values():
            require(rule['entryId'] in dictionary and type(rule['inputSha256']) is str,
                    'selection-rule-invalid')
        input_hash = fingerprint(binding)
        applicable = sorted(k for k, v in rules.items() if v['inputSha256'] == input_hash)
        if not applicable:
            return _out(CATEGORIES[3], ['selection-no-applicable-rule'], binding=binding,
                        inventories=inventories)
        product, product_version = check.claim_context(p.product_claim_id, 'source-product-assignment')
        alternatives, eligible, assertion_ids = [], {}, set()
        for rule_id in applicable:
            rule = rules[rule_id]; entry = dictionary[rule['entryId']]; assertion = rule['assertion']
            alternative = {'ruleId': rule_id, 'entryId': rule['entryId'],
                           'ingredientIdentityClaimId': entry['ingredientIdentityClaimId'],
                           'specificity': entry['specificity'], 'eligible': False, 'reasons': []}
            alternatives.append(alternative)
            try:
                _keys(assertion, ('assertionId', 'productIdentityClaimId', 'ingredientIdentityClaimId',
                                  'relation', 'state', 'evidence'))
                _text(assertion['assertionId'])
                require(assertion['assertionId'] not in assertion_ids, 'selection-assertion-duplicate')
                assertion_ids.add(assertion['assertionId'])
                require(assertion['productIdentityClaimId'] == p.product_claim_id
                        and assertion['ingredientIdentityClaimId'] == entry['ingredientIdentityClaimId']
                        and assertion['state'] == 'reviewed'
                        and assertion['relation'] in ('declares-ingredient', 'refers-to-ingredient')
                        and type(assertion['evidence']) is list and bool(assertion['evidence']),
                        'selection-assertion-unqualified')
                for pin in assertion['evidence']: check.evidence(pin)
                ingredient, ingredient_version = check.claim_context(entry['ingredientIdentityClaimId'],
                                                                      'ingredient-identity')
                require(ingredient_version == entry['ingredientVersion'], 'selection-endpoint-version')
                check.relationship(assertion, binding, 'product-ingredient-relationship',
                    {'product': product_version, 'ingredient': ingredient_version,
                     'productContext': {k: product[k] for k in
                                       ('foodProduct', 'formulation', 'package', 'market', 'effectivePeriod')},
                     'foodForm': ingredient['foodForm']})
                outcome = fingerprint({'graphIri': ingredient['graphIri'],
                                       'foodForm': ingredient['foodForm'],
                                       'specificity': entry['specificity'], 'relation': assertion['relation']})
                eligible[rule_id] = (outcome, assertion, entry['specificity'])
                alternative['eligible'] = True
            except EvidenceError as error:
                alternative['reasons'] = [_code(error)]
        # An unknown candidate cannot silently lose to the surviving candidate.
        if len(eligible) != len(applicable):
            return _out(CATEGORIES[3], ['selection-candidate-evidence-missing'], binding=binding,
                        inventories=inventories, alternatives=alternatives)
        matched = sorted(k for k, v in decisions.items() if v['inputSha256'] == input_hash)
        for decision_id in matched:
            d = decisions[decision_id]
            require(type(d['candidateRuleIds']) is list and sorted(d['candidateRuleIds']) == applicable
                    and len(d['candidateRuleIds']) == len(set(d['candidateRuleIds']))
                    and d['state'] in ('affirmed', 'unresolved')
                    and (d['selectedRuleId'] in eligible if d['state'] == 'affirmed'
                         else d['selectedRuleId'] is None)
                    and type(d['evidence']) is list and bool(d['evidence']), 'selection-adjudication-stale')
            for pin in d['evidence']: check.evidence(pin)
        if len(matched) > 1 or (matched and decisions[matched[0]]['state'] == 'unresolved'):
            return _out(CATEGORIES[2], ['selection-competing-or-unresolved-adjudication'], binding=binding,
                        inventories=inventories, alternatives=alternatives, adjudications=matched)
        outcomes = {v[0] for v in eligible.values()}
        if matched:
            chosen = eligible[decisions[matched[0]]['selectedRuleId']][0]
        elif len(outcomes) == 1:
            chosen = next(iter(outcomes))
        else:
            return _out(CATEGORIES[2], ['selection-competing-outcomes'], binding=binding,
                        inventories=inventories, alternatives=alternatives)
        selected = [v for v in eligible.values() if v[0] == chosen]
        for a in alternatives:
            a['reasons'] = ['selection-selected' if eligible[a['ruleId']][0] == chosen
                            else 'selection-not-selected-by-adjudication']
        return _out(CATEGORIES[0] if selected[0][2] == 'specific' else CATEGORIES[1],
                    ['selection-adjudicated' if matched else 'selection-single-qualified-outcome'],
                    binding=binding, inventories=inventories, alternatives=alternatives,
                    assertions=[v[1] for v in selected], adjudications=matched)
    except EvidenceError as error:
        return _out(CATEGORIES[3], [_code(error)], binding=binding,
                    inventories=inventories, alternatives=alternatives)
    except Exception:
        return _out(CATEGORIES[3], ['selection-invalid-input'], binding=binding,
                    inventories=inventories, alternatives=alternatives)


def uncertainty_metrics(category_counts, *, assessed_denominator, unassessed=None, excluded=None):
    """Arithmetic for one explicitly named cohort/axis/unit; no dedup or inference.

    An unknown denominator retains observed counts but no total numerator/rate.
    An empty assessed set has a zero numerator and unavailable percentage.
    """
    if (type(category_counts) is not dict or set(category_counts) != set(CATEGORIES)
            or any(type(v) is not int or v < 0 for v in category_counts.values())
            or any(v is not None and (type(v) is not int or v < 0)
                   for v in (assessed_denominator, unassessed, excluded))
            or (assessed_denominator is not None and sum(category_counts.values()) != assessed_denominator)):
        raise ValueError('selection-metrics-invalid')
    unclear = sum(category_counts[k] for k in CATEGORIES[1:])
    return {'definitionVersion': METRICS_VERSION, 'categories': dict(category_counts),
            'assessedDenominator': assessed_denominator, 'observedUnclearCount': unclear,
            'unclearNumerator': unclear if assessed_denominator is not None else None,
            'unclearPercent': (100 * unclear / assessed_denominator) if assessed_denominator else None,
            'unassessed': unassessed, 'excluded': excluded}
