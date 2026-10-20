"""Invented in-memory qualification/witness fixtures only; no actual data IO."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import Asset, SourceContract, canonical, fingerprint, contract_fingerprint
from offmenu.refresh.english_extension import ResolvedClaim, ReviewedWitness
from offmenu.refresh.field_provenance import datum_pointers
from offmenu.refresh import usda_product_contract as usda
from offmenu.refresh import usda_native_relationships as native


def sha(raw): return hashlib.sha256(raw).hexdigest()


class Fixture:
    """Trusted synthetic application selection, NOT a production factory.

    Qualification snapshots model already qualified fixtures; this suite does
    not perform source qualification or treat a self-fingerprint as authority.
    """
    def __init__(self):
        self.blobs={};self.claims={};self.roles={};self.witnesses={}
        self.origin_policy='7'*64;self.authority='invented-review-authority'
        self.original=Asset('invented.zip',2,sha(b'{}'))
        self.rights=Asset('rights.json',2,sha(b'{}'));self.scope=Asset('scope.json',2,sha(b'{}'))
        self.clock=Asset('clock.json',2,sha(b'{}'))
        schemas=usda.native_schemas()
        # A synthetic contract pins its invented original, never pretends that
        # the real retained archive was read or qualified by this fixture.
        for schema in schemas.values():
            schema['properties']['provenance']['properties']['inputSha256']={'const':{'archive':self.original.sha256}}
        self.contract=SourceContract('usda-files',usda.RELEASE,'invented-native-scope',None,
            (self.original,self.rights,self.scope,self.clock),1,'a'*64,schemas,
            fingerprint(schemas),lambda row:(), 'b'*64,self.rights,self.scope,
            frozenset(('retain','parse','transform')),fixture=True,
            acquisition_clock_status='unknown-retained',clock_evidence=self.clock)
        self.record={'schemaVersion':'1.0','kind':'product','id':'usda-files:product:fixture-record',
          'countries':['US'],'data':{'name':'Invented beans','identifiers':[{'system':'USDA-FDC','value':'fixture-record'}],
            'brand':None,'dataType':'invented','ingredientsText':'Beans, water','marketCountry':None,
            'serving':{'amount':None,'unit':None,'label':None},'nutritionId':'usda-files:nutrientProfile:fixture-record'},
          'provenance':{'sourceId':'usda-files','releaseId':usda.RELEASE,'recordId':'fixture-record',
            'fetchedAt':None,'sourceDate':None,'acquisitionClock':{'status':'unknown-retained','evidenceSha256':self.clock.sha256},
            'license':usda.LICENSE,'attribution':usda.ATTRIBUTION,'rightsEvidenceSha256':self.rights.sha256,
            'scopeEvidenceSha256':self.scope.sha256,'transform':'offmenu-products-offline/2','visibility':'private-candidate',
            'rights':'Original source terms govern reuse; normalization does not relicense data.',
            'sourceRow':3,'inputSha256':{'archive':self.original.sha256}}}
        origins={p:{'kind':'constant','policySha256':self.origin_policy,'symbol':'invented-fixture-value'}
                 for p in datum_pointers(self.record['data'])}
        origins['/data/ingredientsText']={'kind':'source','sourceId':'usda-files','releaseId':usda.RELEASE,
            'inputPath':self.original.path,'inputSha256':self.original.sha256,
            'sourceRecordId':'invented/branded_food.csv:row:12','sourceField':'/ingredients',
            'archiveMember':'invented/branded_food.csv','table':'branded_food','row':12,
            'coordinateSystem':'csv-logical-data-row'}
        self.record['provenance']['fieldOrigins']=origins
        self.evidence=self.pin('invented-policy.json',{'synthetic':True})
        def dimension(name,role):
            iri='https://example.invalid/'+name;self.roles[iri]=role
            return {'state':'bound','iri':iri,'evidence':self.evidence}
        self.product={'role':'source-product-assignment','graphIri':'https://example.invalid/assignment',
            'foodProduct':dimension('product','FoodProduct'),
            'formulation':{**dimension('snapshot','SourceRecord'),'snapshotId':'invented-snapshot'},
            'package':dimension('package','Package'),'market':dimension('market','Market'),
            'effectivePeriod':{'state':'bound','from':'2026-01-01','to':'2026-12-31','evidence':self.evidence},
            'evidence':[self.evidence]}
        self.ingredient={'role':'ingredient-identity','graphIri':'https://example.invalid/ingredient',
            'foodForm':{'materialState':'cooked','part':'seed','preparation':'boiled'},'evidence':[self.evidence]}
        self.assertion={'assertionId':'invented-relation','productIdentityClaimId':'P','ingredientIdentityClaimId':'I',
            'relation':'declares-ingredient','state':'reviewed','evidence':[self.evidence]}
        self.refresh()

    def pin(self,name,value):
        raw=canonical(value);pin={'path':name,'sha256':sha(raw)};self.blobs[(name,pin['sha256'])]=raw;return pin

    def qualification(self,contract,raw):
        q={'schemaVersion':'offmenu-source-qualification/1','qualified':True,'status':'qualified','errors':[],
            'contractSha256':contract_fingerprint(contract),'sourceId':contract.source_id,
            'releaseId':contract.release_id,'scopeId':contract.scope_id,'outputScope':'native',
            'outputVisibility':'private','fixture':contract.fixture,'normalizedRecords':contract.expected_records,
            'candidateSha256':sha(raw)}
        q['qualificationSha256']=fingerprint(q);return q

    def claim(self,key,data):
        self.roles[data['graphIri']]=data['role']
        row={'id':key,'schemaVersion':'1.0','kind':'sourceAssertion','data':deepcopy(data),
             'provenance':{'sourceId':'invented-external-claims','releaseId':'invented-release'}}
        pin=self.pin('claim-'+key+'.json', [row])
        raw=self.blobs[(pin['path'],pin['sha256'])]
        contract=replace(self.contract,source_id='invented-external-claims',release_id='invented-release',
            scope_id='invented-claims',acquired_at='2026-01-01T00:00:00Z',acquisition_clock_status='known',
            clock_evidence=None,schemas={'sourceAssertion':{'type':'object'}},schemas_sha256=fingerprint({'sourceAssertion':{'type':'object'}}))
        self.claims[key]=ResolvedClaim(contract,self.qualification(contract,raw),pin,'/0',None)

    def version(self,key,data):
        c=self.claims[key]
        return {'claimId':key,'artifact':c.artifact,'recordPointer':c.record_pointer,'line':c.line,
            'qualificationSha256':c.qualification['qualificationSha256'],
            'contractSha256':contract_fingerprint(c.contract),'dataSha256':fingerprint(data)}

    def refresh(self):
        self.claim('P',self.product);self.claim('I',self.ingredient)
        q=self.qualification(self.contract,canonical([self.record])+b'\n');p=self.record['provenance']
        binding={'sourceId':'usda-files','releaseId':usda.RELEASE,'sourceRecordId':'fixture-record',
            'nativeProductId':self.record['id'],'originalSHA256':self.original.sha256,
            'candidateSha256':q['candidateSha256'],'candidateLine':1,'recordPointer':'/0',
            'nativeRecordSha256':fingerprint(self.record),'qualificationSha256':q['qualificationSha256'],
            'contractSha256':q['contractSha256'],'sourceRow':3,'transform':p['transform'],
            'rightsEvidenceSha256':self.rights.sha256,'scopeEvidenceSha256':self.scope.sha256,
            'acquisitionClock':p['acquisitionClock']}
        scope={'type':'usda-native-product-selection','inputBinding':binding,
            'fieldOriginsSha256':fingerprint(p['fieldOrigins']),'purpose':'private-native-relationship-validation',
            'decisionState':'affirmed','reviewStatus':'reviewed','reviewAuthority':self.authority}
        selection=ReviewedWitness(self.pin('selected-native.json',scope),scope,self.authority)
        self.policy=native.NativeProductPolicy(self.contract,q,q['qualificationSha256'],self.original,
            self.record['id'],fingerprint(self.record),1,selection,frozenset((self.origin_policy,)),frozenset((self.authority,)))
        scope={'type':'product-ingredient-relationship','assertionId':self.assertion['assertionId'],
            'assertionSha256':fingerprint(self.assertion),'relation':self.assertion['relation'],
            'inputBinding':binding,'decisionState':'affirmed','reviewStatus':'reviewed',
            'product':self.version('P',self.product),'ingredient':self.version('I',self.ingredient),
            'productContext':{k:self.product[k] for k in ('foodProduct','formulation','package','market','effectivePeriod')},
            'foodForm':self.ingredient['foodForm'],'sourceField':{'fieldPointer':'/data/ingredientsText',
                'fieldOriginSha256':fingerprint(p['fieldOrigins']['/data/ingredientsText']),
                'textSha256':sha(self.record['data']['ingredientsText'].encode())},'reviewAuthority':self.authority}
        self.witnesses[self.assertion['assertionId']]=ReviewedWitness(self.pin('relation.json',scope),scope,self.authority)

    def inventory(self):return native.ResolverInventory(evidence=self.blobs,claims=self.claims,roles=self.roles,relationships=self.witnesses)
    def errors(self,**kwargs):return native.native_product_relationship_errors(self.record,self.assertion,kwargs.get('policy',self.policy),kwargs.get('resolver',self.inventory()))


class NativeRelationshipTests(unittest.TestCase):
    def setUp(self):self.f=Fixture()
    def test_supported_native_case_no_recipe_wrapper_no_mutation(self):
        f=self.f;before=deepcopy((f.record,f.assertion));self.assertEqual(f.errors(),());self.assertEqual((f.record,f.assertion),before)
        self.assertNotIn('source',f.record);self.assertNotIn('recipeTemplate',f.record)
    def test_default_and_empty_authority_refuse(self):
        f=self.f;self.assertEqual(native.native_product_relationship_errors(f.record,f.assertion),('usda-relationship-unbound',))
        self.assertEqual(f.errors(policy=replace(f.policy,review_authorities=frozenset())),('usda-relationship-unbound',))
        self.assertEqual(f.errors(policy=replace(f.policy,origin_policy_pins=frozenset())),('usda-relationship-unbound',))
    def test_missing_input_review_and_relationship_are_distinct_refusals(self):
        f=self.f;self.assertEqual(f.errors(policy=replace(f.policy,selection_witness=None)),('usda-relationship-selection-unqualified',))
        f.witnesses.clear();self.assertEqual(f.errors(),('english-relationship-unqualified',))
    def test_input_selection_must_affirm_exact_native_binding(self):
        f=self.f;w=f.policy.selection_witness;w.scope['inputBinding']['candidateLine']=9
        f.policy=replace(f.policy,selection_witness=replace(w,pin=f.pin('wrong-native-selection.json',w.scope)))
        self.assertEqual(f.errors(),('usda-relationship-selection-unqualified',))
        f=Fixture();w=f.policy.selection_witness;w.scope['reviewAuthority']='foreign'
        f.policy=replace(f.policy,selection_witness=replace(w,pin=f.pin('foreign-native-selection.json',w.scope),authority='foreign'))
        self.assertEqual(f.errors(),('usda-relationship-selection-unqualified',))
    def test_relationship_cannot_move_to_another_input_or_source_field(self):
        for field in ('inputBinding','sourceField'):
            f=Fixture();w=f.witnesses['invented-relation'];w.scope[field]={}
            f.witnesses['invented-relation']=replace(w,pin=f.pin('wrong-context.json',w.scope))
            self.assertEqual(f.errors(),('english-relationship-unqualified',))
    def test_stale_native_record_line_and_qualification_refuse(self):
        f=self.f;f.record['data']['name']='modified';self.assertEqual(f.errors(),('usda-relationship-selected-record',))
        f=Fixture();self.assertEqual(f.errors(policy=replace(f.policy,candidate_line=2)),('usda-relationship-selected-record',))
        f.policy.qualification['status']='not-qualified';self.assertTrue(f.errors())
    def test_missing_and_wrong_source_origin_refuse(self):
        f=self.f;f.record['provenance']['fieldOrigins'].pop('/data/name');f.refresh()
        self.assertEqual(f.errors(),('usda-relationship-origins-unqualified',))
        f=Fixture();f.record['provenance']['fieldOrigins']['/data/ingredientsText']['table']='food';f.refresh()
        self.assertEqual(f.errors(),('usda-relationship-ingredient-origin-required',))
    def test_constant_or_wrong_source_field_cannot_support_ingredient(self):
        f=self.f;f.record['provenance']['fieldOrigins']['/data/ingredientsText']={'kind':'constant','policySha256':f.origin_policy,'symbol':'invented'};f.refresh()
        self.assertEqual(f.errors(),('usda-relationship-ingredient-origin-required',))
        f=Fixture();f.record['provenance']['fieldOrigins']['/data/ingredientsText']['sourceField']='/description';f.refresh()
        self.assertEqual(f.errors(),('usda-relationship-ingredient-origin-required',))
    def test_missing_product_or_ingredient_claim_refuses(self):
        for key in ('P','I'):
            f=Fixture();del f.claims[key];self.assertEqual(f.errors(),('english-identity-unresolved',))
    def test_product_context_and_food_form_reuse_existing_rules(self):
        f=self.f;f.product['formulation']['snapshotId']=None;f.refresh();self.assertEqual(f.errors(),('english-formulation-unresolved',))
        f=Fixture();f.product['effectivePeriod']['from']=None;f.refresh();self.assertEqual(f.errors(),('english-effective-period-unresolved',))
        f=Fixture();f.roles[f.product['package']['iri']]='Market';self.assertEqual(f.errors(),('english-product-context-unresolved',))
        f=Fixture();f.ingredient['foodForm']['part']='unknown';f.refresh();self.assertEqual(f.errors(),('english-food-form-unresolved',))
    def test_endpoint_versions_do_not_substitute_for_relationship(self):
        f=self.f;w=f.witnesses['invented-relation'];w.scope['product']['dataSha256']='0'*64
        f.witnesses['invented-relation']=replace(w,pin=f.pin('changed-witness.json',w.scope))
        self.assertEqual(f.errors(),('english-relationship-unqualified',))
    def test_opaque_claim_id_is_never_cast_to_graph_iri(self):
        f=self.f;f.roles.clear();self.assertEqual(f.errors(),('english-claim-role-invalid',))
    def test_non_affirmative_and_foreign_review_authority_refuse(self):
        for field,value in [('decisionState','rejected'),('reviewStatus','proposed'),('reviewAuthority','foreign')]:
            f=Fixture();w=f.witnesses['invented-relation'];w.scope[field]=value
            f.witnesses['invented-relation']=replace(w,pin=f.pin('bad-witness.json',w.scope));self.assertEqual(f.errors(),('english-relationship-unqualified',))
    def test_proposed_unresolved_and_extra_assertion_shapes_do_not_promote(self):
        for state in ('proposed','unresolved','rejected'):
            f=Fixture();f.assertion['state']=state;self.assertEqual(f.errors(),('usda-relationship-assertion-unqualified',))
        f=self.f;f.assertion['quantity']=0;self.assertEqual(f.errors(),('usda-relationship-assertion-unqualified',))
    def test_fixture_claim_cannot_satisfy_other_fixture_scope(self):
        f=self.f;c=f.claims['P'];f.claims['P']=replace(c,contract=replace(c.contract,fixture=False))
        # Rebind the qualification to this changed synthetic claim contract.
        c=f.claims['P'];raw=f.blobs[(c.artifact['path'],c.artifact['sha256'])]
        f.claims['P']=replace(c,qualification=f.qualification(c.contract,raw))
        self.assertEqual(f.errors(),('english-claim-fixture-scope-mismatch',))
    def test_selected_inventory_snapshot_is_not_mutated_by_callers(self):
        f=self.f;inventory=f.inventory();f.claims.clear();f.roles.clear();f.witnesses.clear();f.blobs.clear()
        self.assertEqual(f.errors(resolver=inventory),())
        returned=inventory.claim('P');returned.qualification['status']='changed';self.assertEqual(f.errors(resolver=inventory),())
    def test_evidence_budgets_fail_closed(self):
        f=self.f;self.assertTrue(f.errors(policy=replace(f.policy,max_evidence_bytes=1)))
        self.assertEqual(f.errors(policy=replace(f.policy,max_evidence_reads=1)),('english-evidence-work-bound-exceeded',))
        self.assertEqual(f.errors(policy=replace(f.policy,max_total_evidence_bytes=1)),('english-evidence-work-bound-exceeded',))
    def test_supported_check_is_pure_and_no_source_values_in_diagnostics(self):
        f=self.f
        with patch('builtins.open',side_effect=AssertionError('no IO')),patch('sqlite3.connect',side_effect=AssertionError('no DB')),patch('gzip.open',side_effect=AssertionError('no gzip')):
            self.assertEqual(f.errors(),())
        f.record['data']['name']='SECRET_SOURCE_VALUE';self.assertNotIn('SECRET_SOURCE_VALUE',str(f.errors()))

if __name__=='__main__':unittest.main()
