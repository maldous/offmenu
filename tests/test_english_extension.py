"""Invented evidence only; existing offline qualify is exercised, not accept."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.english_extension import (EnglishPolicy, Grant, ResolvedClaim, EvidenceError,
                                             pointer, semantic_validator, validate_extension)
ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'synthetic-runs'
WORK.mkdir(exist_ok=True)
SCHEMA = json.loads((ROOT / 'offmenu/refresh/english_extension.schema.json').read_text())
def digest(raw): return hashlib.sha256(raw).hexdigest()
def encode(obj): return json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()


class Fixture:
    def __init__(self, root):
        self.root = root; self.blobs = {}; self.grants = {}; self.claims = {}
        self.roles = {}; self.uses = {}; self.quantities = {}; self.decisions = {}
        self.records = {}; self.subfields = {}; self.bindings = {}
        self.text = '0 g 豆腐 é\n'
        raw = self.text.encode(); span = raw.rstrip(b'\n')
        self.loc = {'page': 1, 'lineStart': 1, 'lineEnd': 1, 'utf8ByteRange': [0, len(span)],
                    'pageTextSHA256': digest(raw), 'sourceSpanSHA256': digest(span)}
        self.original = Asset('original.txt', len(raw), digest(raw))
        self.original_contract = self.contract('recipe-source', 'recipe-release', [self.original])
        self.native = {'recipeTemplate': 'offmenu-source-recipe/2',
                       'source': {'sourceId': 'recipe-source', 'releaseId': 'recipe-release',
                                  'sourceRecordId': 'native-recipe', 'originalSHA256': self.original.sha256},
                       'ingredientLines': [{'sourceNameText': '豆腐', 'originalExpression': '0 g 豆腐 é',
                                            'quantity': {'rawValueLexeme': '0'}, 'location': self.loc}]}
        parsed = self.pin('parsed.jsonl', encode([self.native]) + b'\n')
        policies = {k: self.pin(k+'.json', encode({'syntheticPolicy': k}))
                    for k in ['normalization', 'translation', 'units', 'identity', 'variants']}
        self.grant_pin = self.pin('grant.json', b'"synthetic reviewed code binding"')
        for purpose in ['normalization', 'translation']:
            self.grants[(self.grant_pin['path'], self.grant_pin['sha256'], purpose)] = Grant(self.original_contract, frozenset([purpose]))
        self.policy = EnglishPolicy(SCHEMA, fingerprint(SCHEMA), self.original_contract,
                                    self.original, Asset(parsed['path'], len(self.blobs[parsed['path']]), parsed['sha256']), policies, 'native-recipe', 'jsonl', 1, '/0')
        anchor = {'fieldPointer': '/ingredientLines/0', 'sourceSpanSHA256': self.loc['sourceSpanSHA256'],
                  'pageTextSHA256': self.loc['pageTextSHA256']}
        self.q = {'assertionId': 'q', 'target': anchor, 'sourceValueState': 'literal-zero',
                  'normalizedValue': '0', 'normalizedUnit': 'g', 'sourceBasis': 'as stated',
                  'normalizedBasis': 'as stated', 'comparison': None, 'boundValue': None,
                  'conversionKind': 'none', 'factorPin': None, 'basisPin': policies['units'],
                  'state': 'proposed', 'evidence': [policies['normalization']]}
        self.bind_quantity(self.q)
        self.t = {'assertionId': 't', 'target': anchor, 'englishText': 'synthetic tofu',
                  'origin': 'human-proposal', 'methodVersion': 'synthetic-only', 'state': 'proposed',
                  'evidence': [policies['translation']], 'ambiguityIds': []}
        self.ext = {'schemaVersion': 'offmenu-english-gold-extension/proposal-2',
                    'activation': 'not-authorized-by-artifact',
                    'input': {'sourceId': 'recipe-source', 'releaseId': 'recipe-release', 'sourceRecordId': 'native-recipe',
                              'originalSHA256': self.original.sha256, 'parsedArtifact': parsed, 'recordPointer': '/0',
                              'format': 'jsonl', 'recordLine': 1, 'extractionSchema': 'offmenu-source-recipe/2',
                              'parserVersion': self.policy.parser_version, 'transformVersion': self.policy.transform_version},
                    'policies': policies,
                    'permissions': [{'operation': 'transform', 'purpose': p, 'state': 'permitted',
                                     'reviewedContractPin': self.grant_pin, 'evidence': [self.grant_pin], 'reason': 'Synthetic-only trusted code'}
                                    for p in ['normalization', 'translation']],
                    'translations': [self.t], 'quantityNormalizations': [self.q],
                    'ingredientIdentityAssertions': [], 'variantAssertions': [],
                    'productIngredientLinks': [], 'usableAsAssertions': [], 'conflicts': [],
                    'statuses': {'normalization': 'proposed', 'translation': 'proposed', 'ingredientIdentity': 'unassessed',
                                 'dietary': 'not-assessed', 'englishConsumer': 'held', 'goldAdmission': 'not-admitted'}}
        form = {'materialState': 'raw', 'part': 'whole', 'preparation': 'uncooked'}
        witness = policies['identity']
        def dim(iri, typ):
            self.roles[iri] = typ
            return {'state': 'bound', 'iri': iri, 'evidence': witness}
        product = {'role': 'source-product-assignment', 'graphIri': 'https://example.invalid/assignment',
                   'foodProduct': dim('https://example.invalid/product', 'FoodProduct'),
                   'formulation': {**dim('https://example.invalid/source-snapshot', 'SourceRecord'), 'snapshotId': 'source-item-r1'},
                   'package': dim('https://example.invalid/package', 'Package'),
                   'market': dim('https://example.invalid/market', 'Market'),
                   'effectivePeriod': {'state': 'bound', 'from': '2026-01-01', 'to': '2026-12-31', 'evidence': witness},
                   'evidence': [witness]}
        ingredient = {'role': 'ingredient-identity', 'graphIri': 'https://example.invalid/ingredient',
                      'foodForm': form, 'evidence': [witness]}
        self.product_data, self.ingredient_data = product, ingredient
        self.set_claim('P', product); self.set_claim('I', ingredient)

    def pin(self, path, raw):
        self.blobs[path] = raw
        return {'path': path, 'sha256': digest(raw)}
    def evidence(self, pin): return self.blobs[pin['path']]
    def page(self, record_id, page): return self.text if (record_id, page) == ('native-recipe', 1) else None
    def grant(self, pin, purpose): return self.grants.get((pin['path'], pin['sha256'], purpose))
    def claim(self, identity): return self.claims.get(identity)
    def graph_role(self, iri): return self.roles.get(iri)
    def graph_binding(self, relation): return self.bindings.get(relation)
    def use(self, identity): return self.uses.get(identity)
    def record(self, identity): return self.records.get(identity)
    def subfield(self, record, path): return self.subfields.get((record, path))
    def quantity(self, identity): return self.quantities.get(identity)
    def decision(self, identity): return self.decisions.get(identity)
    def bind_quantity(self, q):
        scope = {'sourceRecordId': 'native-recipe', 'originalSHA256': self.original.sha256, 'target': copy.deepcopy(q['target']), **{k: copy.deepcopy(q[k]) for k in ('sourceValueState','normalizedValue','normalizedUnit','sourceBasis','normalizedBasis','comparison','boundValue','conversionKind','factorPin','basisPin')}}
        self.quantities[q['assertionId']] = {'pin': self.pin('quantity-'+q['assertionId']+'.json', encode(scope)), 'scope': scope}
    def contract(self, source, release, extra=()):
        rights = Asset('rights.json', 2, digest(b'{}')); scope = Asset('scope.json', 2, digest(b'{}'))
        schema = {'type': 'object', 'required': ['id','kind','schemaVersion','provenance','data']}
        schemas = {'sourceAssertion': schema}
        return SourceContract(source, release, 'synthetic-native', '2026-10-20T00:00:00Z',
                              tuple(extra)+(rights, scope), 1, ids_digest([source]), schemas, fingerprint(schemas),
                              lambda row: (), digest(b'reviewed synthetic policy'), rights, scope,
                              frozenset(['retain','parse','transform']), fixture=True)
    def set_claim(self, identity, data, source='external-product-source'):
        # External claims use their OWN exact source/release/qualification, not recipe provenance.
        data = copy.deepcopy(data); self.roles.setdefault(data['graphIri'], data['role'])
        row = {'schemaVersion': '1.0', 'kind': 'sourceAssertion', 'id': identity,
               'provenance': {'sourceId': source, 'releaseId': 'external-r1', 'fetchedAt': '2026-10-20T00:00:00Z'}, 'data': data}
        raw = encode([row])+b'\n'; pin = self.pin('claim-'+identity+'.jsonl', raw)
        bundle = self.root/('claim-'+identity); bundle.mkdir(exist_ok=True)
        for name in ['rights.json','scope.json']: (bundle/name).write_bytes(b'{}')
        (bundle/'input.json').write_bytes(b'{}')
        c = self.contract(source, 'external-r1', [Asset('input.json', 2, digest(b'{}'))])
        c = replace(c, expected_ids_sha256=ids_digest([identity]))
        candidate=bundle/'candidate.jsonl'; candidate.write_bytes(raw)
        # Candidate/output stays outside bundle inventory, per the existing boundary.
        outside=self.root/('candidate-'+identity+'.jsonl'); outside.write_bytes(raw); candidate.unlink()
        manifest={'sourceId':source,'releaseId':'external-r1','acquiredAt':c.acquired_at,
                  'normalizedRecords':1,'rightsEvidenceSha256':c.rights_evidence.sha256,
                  'scopeEvidenceSha256':c.scope_evidence.sha256,
                  'candidateBytes':len(raw),'candidateSha256':digest(raw),
                  'inputFiles':[vars(a) for a in c.inputs]}
        q=qualify(c,bundle,outside,manifest,scratch_root=self.root)
        assert q['qualified'], q['errors']
        self.claims[identity]=ResolvedClaim(c,q,pin,'/0',1)
    def product_link(self):
        self.ext['productIngredientLinks']=[{'assertionId':'p','productIdentityClaimId':'P','ingredientIdentityClaimId':'I',
                                           'relation':'declares-ingredient','state':'proposed','evidence':[self.ext['policies']['identity']]}]
    def supported_use(self, registered=False):
        pin=self.ext['policies']['identity']
        a={'assertionId':'u','productIdentityClaimId':'P','ingredientIdentityClaimId':'I','recipeRecordRef':'native-recipe',
           'requiredFoodForm':'raw','useConditions':'synthetic exact use','state':'supported','evidence':[pin]}
        self.ext['usableAsAssertions']=[a]
        scope={'decisionState': 'supported', 'inputBinding': {k: copy.deepcopy(self.ext['input'][k]) for k in ('sourceId','releaseId','sourceRecordId','originalSHA256','parsedArtifact')}, 'productClaim':'P','ingredientClaim':'I','formulationSnapshot':'source-item-r1',
               'package':self.product_data['package']['iri'],'market':self.product_data['market']['iri'],
               'foodForm':self.ingredient_data['foodForm'],'requiredFoodForm':'raw','conditions':a['useConditions'],
               'effectiveAt':'2026-05-01','recipeRecordRef':'native-recipe','alternativeScope':None,
               'predicate':'https://example.invalid/synthetic-reviewed-property'}
        self.uses['u']={'scope':scope,'pin':self.pin('use-u.json',encode(scope))}
        if registered:self.bindings['usableAs']=scope['predicate']  # Synthetic binding only, no vocabulary installation.
    def rebind_use(self):
        scope=self.uses['u']['scope'];self.uses['u']['pin']=self.pin('use-u.json',encode(scope))
    def rebind_native(self):
        raw=encode([self.native])+b'\n';pin=self.pin('parsed.jsonl',raw)
        self.ext['input']['parsedArtifact']=pin
        self.policy=replace(self.policy,parsed_asset=Asset(pin['path'],len(raw),pin['sha256']))


class EnglishExtensionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=WORK);self.addCleanup(self.temp.cleanup)
        self.f=Fixture(Path(self.temp.name))
    def check(self, expected=()):
        f=self.f; before=copy.deepcopy(f.ext);actual=validate_extension(f.ext,f.policy,f)
        self.assertEqual(actual,expected);self.assertEqual(f.ext,before)
    def test_positive_native_utf8_unknowns_preserved(self): self.check()
    def test_external_product_source_not_recipe_source(self): self.f.product_link();self.check()
    def test_wrong_product_role(self):
        f=self.f;f.product_link();f.ext['productIngredientLinks'][0]['productIdentityClaimId']='I';self.check(('english-claim-role-invalid',))
    def test_opaque_id_not_automatically_iri(self):
        f=self.f;f.product_link();self.assertEqual(f.ext['productIngredientLinks'][0]['productIdentityClaimId'],'P');self.check()
    def test_unresolved_claim(self):
        f=self.f;f.product_link();del f.claims['P'];self.check(('english-identity-unresolved',))
    def test_claim_receipt_substitution(self):
        f=self.f;f.product_link();f.claims['P'].qualification['candidateSha256']='0'*64;self.check(('english-claim-qualification-invalid',))
    def test_claim_record_substitution(self):
        f=self.f;f.product_link();f.claims['P']=f.claims['I'];self.check(('english-claim-record-mismatch',))
    def test_package_wrong_role(self):
        f=self.f;f.product_link();p=copy.deepcopy(f.product_data);p['package']['iri']=p['market']['iri'];f.set_claim('P',p);self.check(('english-product-context-unresolved',))
    def test_formulation_missing(self):
        f=self.f;f.product_link();p=copy.deepcopy(f.product_data);p['formulation']['snapshotId']=None;f.set_claim('P',p);self.check(('english-formulation-unresolved',))
    def test_effective_time_unknown(self):
        f=self.f;f.product_link();p=copy.deepcopy(f.product_data);p['effectivePeriod']['from']=None;f.set_claim('P',p);self.check(('english-effective-period-unresolved',))
    def test_ingredient_form_unknown(self):
        f=self.f;f.product_link();i=copy.deepcopy(f.ingredient_data);i['foodForm']['materialState']='unknown';f.set_claim('I',i);self.check(('english-food-form-unresolved',))
    def test_release_substitution(self): self.f.ext['input']['releaseId']='substituted';self.check(('english-source-contract-mismatch',))
    def test_source_substitution(self): self.f.ext['input']['sourceId']='substituted';self.check(('english-source-contract-mismatch',))
    def test_record_substitution(self): self.f.ext['input']['sourceRecordId']='substituted';self.check(('english-source-record-mismatch',))
    def test_original_hash_substitution(self): self.f.ext['input']['originalSHA256']='0'*64;self.check(('english-original-pin-mismatch',))
    def test_selected_artifact_substitution(self): self.f.ext['input']['parsedArtifact']['sha256']='0'*64;self.check(('english-selected-artifact-mismatch',))
    def test_actual_artifact_bytes_substitution(self): self.f.blobs['parsed.jsonl']+=b' ';self.check(('english-evidence-pin-mismatch',))
    def test_invalid_pointer_escape(self): self.f.t['target']['fieldPointer']='/ingredientLines/~2';self.check(('english-pointer-invalid',))
    def test_invalid_array_index(self): self.f.t['target']['fieldPointer']='/ingredientLines/00';self.check(('english-pointer-invalid',))
    def test_valid_json_pointer_escapes(self): self.assertEqual(pointer({'a/b':{'~x':7}},'/a~1b/~0x'),7)
    def test_jsonl_line_binding(self): self.f.ext['input']['recordLine']=2;self.check(('english-selected-record-mismatch',))
    def test_span_hash_substitution(self): self.f.t['target']['sourceSpanSHA256']='0'*64;self.check(('english-native-span-mismatch',))
    def test_no_subfield_whole_line_inheritance(self): self.f.t['target']['fieldPointer']='/ingredientLines/0/sourceNameText';self.check(('english-subfield-locator-unqualified',))
    def test_native_line_mismatch(self): self.f.loc['lineStart']=2;self.f.rebind_native();self.check(('english-native-line-mismatch',))
    def test_split_utf8_range(self): self.f.loc['utf8ByteRange'][1]=5;self.f.rebind_native();self.check(('english-evidence-invalid',))
    def test_duplicate_assertion_ids(self): self.f.t['assertionId']='q';self.check(('english-assertion-id-duplicate',))
    def test_unknown_ambiguity_reference(self): self.f.t['ambiguityIds']=['missing'];self.check(('english-ambiguity-reference-unresolved',))
    def test_unknown_variant_reference(self):
        self.f.ext['variantAssertions']=[{'assertionId':'v','sourceRecordRefs':['native-recipe','missing'],'relation':'regional-variant','region':None,'state':'unresolved','mergePerformed':False,'evidence':[]}];self.check(('english-identity-unresolved',))
    def test_invented_permission_pin_even_with_matching_bytes(self):
        f=self.f;pin=f.pin('invented.json',b'{}');f.ext['permissions'][1]['reviewedContractPin']=pin;self.check(('english-permission-unqualified',))
    def test_denied_translation_does_not_inherit_normalization(self): self.f.ext['permissions'][1]['state']='denied';self.check(('english-translation-permission-missing',))
    def test_source_hold_blocks(self): self.f.policy=replace(self.f.policy,input_contract=replace(self.f.original_contract,holds=('held',)));self.check(('english-source-operation-unqualified',))
    def test_literal_zero_nonzero(self): self.f.q['normalizedValue']='1';self.check(('english-literal-zero-inconsistent',))
    def test_literal_zero_wrong_native_lexeme(self): self.f.native['ingredientLines'][0]['quantity']['rawValueLexeme']='2';self.f.rebind_native();self.check(('english-literal-zero-inconsistent',))
    def test_arbitrary_numeric_conversion_not_evidence(self): self.f.q['normalizedUnit']='kg';self.check(('english-quantity-binding-mismatch',))
    def test_unregistered_supported_usable_as(self): self.f.supported_use();self.check(('english-usability-predicate-unregistered',))
    def test_explicit_synthetic_usable_binding(self): self.f.supported_use(registered=True);self.check()
    def test_supported_without_scope(self): self.f.supported_use(registered=True);self.f.uses.clear();self.check(('english-use-scope-unresolved',))
    def test_null_recipe_without_qualified_alternative(self):
        f=self.f;f.supported_use(registered=True);f.ext['usableAsAssertions'][0]['recipeRecordRef']=None;f.uses['u']['scope']['recipeRecordRef']=None;f.rebind_use();self.check(('english-use-scope-unresolved',))
    def test_cross_formulation_use(self): self.f.supported_use(registered=True);self.f.uses['u']['scope']['formulationSnapshot']='other';self.f.rebind_use();self.check(('english-use-context-mismatch',))
    def test_cross_package_use(self): self.f.supported_use(registered=True);self.f.uses['u']['scope']['package']='other';self.f.rebind_use();self.check(('english-use-context-mismatch',))
    def test_cross_market_use(self): self.f.supported_use(registered=True);self.f.uses['u']['scope']['market']='other';self.f.rebind_use();self.check(('english-use-context-mismatch',))
    def test_cross_time_use(self): self.f.supported_use(registered=True);self.f.uses['u']['scope']['effectiveAt']='2027-05-01';self.f.rebind_use();self.check(('english-use-time-mismatch',))
    def test_arbitrary_use_evidence_pin(self): self.f.supported_use(registered=True);self.f.uses['u']['pin']=self.f.ext['policies']['identity'];self.check(('english-use-scope-pin-mismatch',))
    def test_unresolved_usability_stays_unpromoted(self):
        f=self.f;f.supported_use();f.ext['usableAsAssertions'][0]['state']='unresolved';f.ext['usableAsAssertions'][0]['recipeRecordRef']=None;f.uses.clear();self.check();self.assertEqual(f.ext['statuses']['goldAdmission'],'not-admitted')
    def test_duplicate_conflict_ids(self):
        c={'conflictId':'c','competingAssertionIds':['t','q'],'state':'unresolved','decisionPin':None,'reason':'synthetic'};self.f.ext['conflicts']=[c,copy.deepcopy(c)];self.check(('english-conflict-id-duplicate',))
    def test_unknown_conflicting_assertion(self): self.f.ext['conflicts']=[{'conflictId':'c','competingAssertionIds':['t','absent'],'state':'unresolved','decisionPin':None,'reason':'synthetic'}];self.check(('english-conflict-reference-unresolved',))
    def test_arbitrary_decision_pin(self): self.f.ext['conflicts']=[{'conflictId':'c','competingAssertionIds':['t','q'],'state':'resolved','decisionPin':self.f.grant_pin,'reason':'synthetic'}];self.check(('english-conflict-decision-unqualified',))
    def test_evidence_bound(self): self.f.policy=replace(self.f.policy,max_evidence_bytes=16);self.check(('english-evidence-bound-exceeded',))
    def test_selected_record_pointer_is_pinned(self): self.f.ext['input']['recordPointer']='/1';self.check(('english-selected-record-mismatch',))
    def test_selected_artifact_length_is_pinned(self): self.f.policy=replace(self.f.policy,parsed_asset=replace(self.f.policy.parsed_asset,bytes=1));self.check(('english-selected-artifact-mismatch',))
    def test_stale_parser_pin_rejected(self): self.f.ext['input']['parserVersion']='offmenu-source-faithful-recipe-parser/1.3.1';self.check(('english-extension-schema-invalid',))
    def test_valid_qualified_subfield_locator(self):
        f=self.f;pointer_path='/ingredientLines/0/sourceNameText';loc=copy.deepcopy(f.loc);loc['utf8ByteRange']=[4,10];loc['sourceSpanSHA256']=digest(f.text.encode()[4:10])
        scope={'recordId':'native-recipe','fieldPointer':pointer_path,'location':loc};pin=f.pin('word-locator.json',encode(scope));f.subfields[('native-recipe',pointer_path)]={**scope,'pin':pin}
        f.t['target']={'fieldPointer':pointer_path,'sourceSpanSHA256':loc['sourceSpanSHA256'],'pageTextSHA256':loc['pageTextSHA256']};self.check()
    def test_unqualified_subfield_locator_rejected(self):
        f=self.f;path='/ingredientLines/0/sourceNameText';f.t['target']['fieldPointer']=path;f.subfields[('native-recipe',path)]=f.loc;self.check(('english-subfield-locator-unqualified',))
    def test_unresolved_quantity_is_preserved(self):
        f=self.f;f.q.update(sourceValueState='unresolved',normalizedValue=None,normalizedUnit=None,sourceBasis=None,normalizedBasis=None,state='unresolved');f.quantities.clear();self.check()
    def test_changed_source_qualifier_requires_binding(self): self.f.q.update(sourceValueState='not-detected',normalizedValue=None);self.check(('english-quantity-binding-mismatch',))
    def test_use_recipe_version_binding(self): self.f.supported_use(registered=True);self.f.uses['u']['scope']['inputBinding']['originalSHA256']='0'*64;self.f.rebind_use();self.check(('english-use-context-mismatch',))
    def test_incomplete_required_operations_cannot_grant(self):
        f=self.f;f.policy=replace(f.policy,input_contract=replace(f.original_contract,required_operations=frozenset()));self.check(('english-source-operation-unqualified',))
    def test_resolver_exception_cannot_leak_source_text(self):
        def bad(pin): raise EvidenceError('invented-private-source-text')
        self.f.evidence=bad;self.check(('english-evidence-invalid',))
    def test_boolean_native_line_is_not_integer(self): self.f.loc['lineStart']=True;self.f.rebind_native();self.check(('english-native-line-mismatch',))
    def test_fixture_claim_cannot_qualify_nonfixture_scope(self):
        f=self.f;f.product_link();contract=replace(f.original_contract,fixture=False);f.policy=replace(f.policy,input_contract=contract)
        for key in list(f.grants):f.grants[key]=Grant(contract,f.grants[key].purposes)
        self.check(('english-claim-fixture-scope-mismatch',))
    def test_negative_usability_requires_scope_too(self):
        f=self.f;f.supported_use(registered=True);f.ext['usableAsAssertions'][0]['state']='unsupported';f.uses.clear();self.check(('english-use-scope-unresolved',))
    def test_explicit_negative_uses_its_own_decision(self):
        f=self.f;f.supported_use(registered=True);f.ext['usableAsAssertions'][0]['state']='unsupported';self.check(('english-use-context-mismatch',))
        f.uses['u']['scope']['decisionState']='unsupported';f.rebind_use();self.check()
    def test_existing_qualification_boundary_uses_callback(self):
        f=self.f;self.f.product_link();root=Path(self.temp.name);bundle=root/'whole';bundle.mkdir()
        for name,raw in [('original.txt',f.text.encode()),('rights.json',b'{}'),('scope.json',b'{}')]: (bundle/name).write_bytes(raw)
        row={'id':'extension-row','kind':'sourceAssertion','schemaVersion':'1.0','provenance':{'sourceId':'recipe-source','releaseId':'recipe-release','fetchedAt':'2026-10-20T00:00:00Z'},'data':f.ext}
        callback=semantic_validator(f.policy,f)
        c=replace(f.original_contract,expected_ids_sha256=ids_digest(['extension-row']),semantic_validator=callback)
        candidate=root/'whole-candidate.jsonl'
        def run():
            raw=encode([row])+b'\n';candidate.write_bytes(raw)
            m={'sourceId':c.source_id,'releaseId':c.release_id,'acquiredAt':c.acquired_at,'normalizedRecords':1,'rightsEvidenceSha256':c.rights_evidence.sha256,'scopeEvidenceSha256':c.scope_evidence.sha256,'candidateBytes':len(raw),'candidateSha256':digest(raw),'inputFiles':[vars(a) for a in c.inputs]}
            return qualify(c,bundle,candidate,m,scratch_root=root)
        good=run();self.assertTrue(good['qualified'],good['errors']);self.assertTrue(good['fixture']);self.assertNotIn('accepted',good)
        f.ext['input']['sourceRecordId']='wrong';bad=run();self.assertFalse(bad['qualified']);self.assertIn('english-source-record-mismatch',bad['errors'])


if __name__ == '__main__': unittest.main()
