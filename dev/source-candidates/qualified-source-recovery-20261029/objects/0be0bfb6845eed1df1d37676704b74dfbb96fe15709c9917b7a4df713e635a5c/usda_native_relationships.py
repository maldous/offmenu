"""Pure USDA-native relationship validation; no factory, IO or edge emitter.

Application code must independently select input, origins, qualified claims and
affirmative witnesses. This module never constructs that authority from text.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import re
from types import MappingProxyType

from jsonschema import Draft202012Validator
from .acceptance import Asset, SourceContract, canonical, fingerprint, _local_schema
from .english_extension import ResolvedClaim, ReviewedWitness, EvidenceError, _Check, require
from .field_provenance import field_origin_errors
from .native_barcode_lookup import _binding

VERSION = 'offmenu-usda-native-relationship-validation/1'


@dataclass(frozen=True)
class NativeProductPolicy:
    input_contract: SourceContract
    qualification: dict
    qualification_sha256: str
    original_asset: Asset
    native_product_id: str
    native_record_sha256: str
    candidate_line: int
    selection_witness: ReviewedWitness | None = None
    origin_policy_pins: frozenset = frozenset()
    review_authorities: frozenset = frozenset()
    max_evidence_bytes: int = 8 * 1024 * 1024
    max_total_evidence_bytes: int = 32 * 1024 * 1024
    max_evidence_reads: int = 1024


class ResolverInventory:
    """Snapshots of already selected application objects, not a JSON loader.

    Exposes only the existing Resolver methods needed by the shared claim and
    relationship checks. No recipe/menu/page/grant/quantity provider is invented.
    Empty inventories and policy defaults carry no review authority.
    """
    def __init__(self, *, evidence=None, claims=None, roles=None, relationships=None):
        evidence, claims = evidence or {}, claims or {}
        roles, relationships = roles or {}, relationships or {}
        if (any(type(k) is not tuple or len(k) != 2 or any(type(s) is not str for s in k)
                or type(v) is not bytes for k, v in evidence.items())
                or any(type(k) is not str or type(v) is not ResolvedClaim for k, v in claims.items())
                or any(type(k) is not str or type(v) is not str for k, v in roles.items())
                or any(type(k) is not str or type(v) is not ReviewedWitness for k, v in relationships.items())):
            raise ValueError('usda-relationship-inventory-invalid')
        self._evidence = MappingProxyType(dict(evidence))
        self._claims = MappingProxyType(deepcopy(dict(claims)))
        self._roles = MappingProxyType(dict(roles))
        self._relationships = MappingProxyType(deepcopy(dict(relationships)))

    def evidence(self, pin): return self._evidence.get((pin['path'], pin['sha256']))
    def claim(self, claim_id): return deepcopy(self._claims.get(claim_id))
    def graph_role(self, iri): return self._roles.get(iri)
    def relationship(self, assertion_id): return deepcopy(self._relationships.get(assertion_id))


def _ingredient_source(origin):
    """Recognize the existing emitter coordinate, not infer an ingredient ID."""
    if origin.get('kind') == 'derived':
        return any(_ingredient_source(v) for v in origin['inputs'])
    if origin.get('kind') != 'source': return False
    member, row = origin.get('archiveMember'), origin.get('row')
    return (origin.get('table') == 'branded_food' and origin.get('sourceField') == '/ingredients'
            and origin.get('coordinateSystem') == 'csv-logical-data-row'
            and type(member) is str and not PurePosixPath(member).is_absolute()
            and '..' not in PurePosixPath(member).parts and '\\' not in member
            and PurePosixPath(member).stem == 'branded_food'
            and type(row) is int and row > 0
            and origin.get('sourceRecordId') == f'{member}:row:{row}')


def _input(record, policy, check):
    contract = policy.input_contract
    q = _binding(contract, policy.qualification, policy.qualification_sha256)
    require(contract.source_id == 'usda-files'
            and type(policy.original_asset) is Asset and policy.original_asset in contract.inputs
            and contract.acquired_at is None and contract.acquisition_clock_status == 'unknown-retained'
            and contract.clock_evidence is not None and contract.clock_evidence in contract.inputs,
            'usda-relationship-input-contract')
    require(type(record) is dict and record.get('kind') == 'product'
            and record.get('id') == policy.native_product_id
            and type(policy.native_record_sha256) is str
            and re.fullmatch('[0-9a-f]{64}', policy.native_record_sha256)
            and fingerprint(record) == policy.native_record_sha256
            and type(policy.candidate_line) is int and 1 <= policy.candidate_line <= q['normalizedRecords'],
            'usda-relationship-selected-record')
    require(len(canonical(record)) <= policy.max_evidence_bytes, 'usda-relationship-record-bound')
    schema = contract.schemas.get('product')
    require(type(schema) is dict and _local_schema(schema)
            and Draft202012Validator(schema).is_valid(record), 'usda-relationship-native-schema')
    p = record['provenance']; key = p['recordId']
    require(p['sourceId'] == contract.source_id and p['releaseId'] == contract.release_id
            and p['visibility'] == 'private-candidate' and p['fetchedAt'] is None
            and p['rightsEvidenceSha256'] == contract.rights_evidence.sha256
            and p['scopeEvidenceSha256'] == contract.scope_evidence.sha256
            and p['inputSha256'] == {'archive': policy.original_asset.sha256}
            and p['acquisitionClock'] == {'status':'unknown-retained', 'evidenceSha256':contract.clock_evidence.sha256}
            and type(p['sourceRow']) is int and p['sourceRow'] > 0
            and record['id'] == f'usda-files:product:{key}'
            and record['data']['nutritionId'] == f'usda-files:nutrientProfile:{key}',
            'usda-relationship-native-provenance')
    require(not field_origin_errors(record, {policy.original_asset.path:policy.original_asset.sha256},
                                    policy_pins=policy.origin_policy_pins),
            'usda-relationship-origins-unqualified')
    text = record['data']['ingredientsText']
    origin = p['fieldOrigins']['/data/ingredientsText']
    require(type(text) is str and bool(text) and _ingredient_source(origin),
            'usda-relationship-ingredient-origin-required')
    binding = {'sourceId':p['sourceId'], 'releaseId':p['releaseId'], 'sourceRecordId':key,
        'nativeProductId':record['id'], 'originalSHA256':policy.original_asset.sha256,
        'candidateSha256':q['candidateSha256'], 'candidateLine':policy.candidate_line,
        'recordPointer':'/0', 'nativeRecordSha256':policy.native_record_sha256,
        'qualificationSha256':q['qualificationSha256'], 'contractSha256':q['contractSha256'],
        'sourceRow':p['sourceRow'], 'transform':p['transform'],
        'rightsEvidenceSha256':p['rightsEvidenceSha256'], 'scopeEvidenceSha256':p['scopeEvidenceSha256'],
        'acquisitionClock':p['acquisitionClock']}
    check.reviewed(policy.selection_witness,
        {'type':'usda-native-product-selection', 'inputBinding':binding,
         'fieldOriginsSha256':fingerprint(p['fieldOrigins']),
         'purpose':'private-native-relationship-validation', 'decisionState':'affirmed', 'reviewStatus':'reviewed'},
        'usda-relationship-selection-unqualified')
    return binding, {'fieldPointer':'/data/ingredientsText', 'fieldOriginSha256':fingerprint(origin),
                     'textSha256':hashlib.sha256(text.encode('utf-8')).hexdigest()}


def _assertion_bound(assertion, policy):
    """Flat shape/count/character guards bound serialization before any copy.

    Cached duplicate pins still count as assertion items. Counting built-in
    strings is O(1); aggregate characters bound JSON's temporary escaping/UTF8
    expansion before its exact serialized-byte check.
    """
    fields = ('assertionId', 'productIdentityClaimId', 'ingredientIdentityClaimId', 'relation', 'state')
    require(type(assertion) is dict and len(assertion) == 6
            and set(assertion) == {*fields, 'evidence'}
            and all(type(assertion[k]) is str for k in fields)
            and type(assertion['evidence']) is list, 'usda-relationship-assertion-unqualified')
    require(len(assertion['evidence']) <= policy.max_evidence_reads,
            'usda-relationship-assertion-bound')
    characters = sum(len(assertion[k]) for k in fields)
    require(characters <= policy.max_evidence_bytes, 'usda-relationship-assertion-bound')
    for pin in assertion['evidence']:
        require(type(pin) is dict and len(pin) == 2 and set(pin) == {'path', 'sha256'}
                and type(pin['path']) is str and type(pin['sha256']) is str,
                'usda-relationship-assertion-unqualified')
        characters += len(pin['path']) + len(pin['sha256'])
        require(characters <= policy.max_evidence_bytes, 'usda-relationship-assertion-bound')
    require(len(canonical(assertion)) <= policy.max_evidence_bytes,
            'usda-relationship-assertion-bound')


def native_product_relationship_errors(record, assertion, policy=None, resolver=None):
    """Fixed diagnostics only. Never emits edges, constructs grants or performs IO.

    A reviewed assertion uses the existing productIngredientLinks shape. This is
    whole-field source support: narrower ingredient word/span claims require a
    separately qualified subfield interface, not fabricated recipe coordinates.
    """
    if (type(policy) is not NativeProductPolicy or type(resolver) is not ResolverInventory
            or type(policy.review_authorities) is not frozenset or not policy.review_authorities
            or any(type(a) is not str or not a for a in policy.review_authorities)
            or type(policy.origin_policy_pins) is not frozenset or not policy.origin_policy_pins
            or any(type(a) is not str or not re.fullmatch('[0-9a-f]{64}',a) for a in policy.origin_policy_pins)):
        return ('usda-relationship-unbound',)
    try:
        require(all(type(v) is int and v > 0 for v in (policy.max_evidence_bytes,
            policy.max_total_evidence_bytes, policy.max_evidence_reads)), 'usda-relationship-evidence-bounds')
        _assertion_bound(assertion, policy)
        record, assertion, policy = deepcopy(record), deepcopy(assertion), deepcopy(policy)
        check = _Check(policy, resolver)
        binding, source_field = _input(record, policy, check)
        require(type(assertion) is dict and set(assertion) == {'assertionId','productIdentityClaimId',
            'ingredientIdentityClaimId','relation','state','evidence'}
            and all(type(assertion[k]) is str and assertion[k] for k in
                    ('assertionId','productIdentityClaimId','ingredientIdentityClaimId'))
            and assertion['state'] == 'reviewed'
            and assertion['relation'] in ('declares-ingredient','refers-to-ingredient')
            and type(assertion['evidence']) is list and bool(assertion['evidence']),
            'usda-relationship-assertion-unqualified')
        for pin in assertion['evidence']: check.evidence(pin)
        product, product_version = check.claim_context(assertion['productIdentityClaimId'], 'source-product-assignment')
        ingredient, ingredient_version = check.claim_context(assertion['ingredientIdentityClaimId'], 'ingredient-identity')
        check.relationship(assertion, binding, 'product-ingredient-relationship',
            {'product':product_version, 'ingredient':ingredient_version,
             'productContext':{k:product[k] for k in ('foodProduct','formulation','package','market','effectivePeriod')},
             'foodForm':ingredient['foodForm'], 'sourceField':source_field})
        return ()
    except EvidenceError as error:
        return (str(error),)
    except Exception:
        return ('usda-relationship-invalid-input',)
