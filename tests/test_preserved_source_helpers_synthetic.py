"""Synthetic code-boundary tests only: no publisher rows, fixtures, or source acceptance.

These tests do not run a full-data builder, read Foo paths, fetch data, execute
historical Git dependencies, or replace the preserved source-validation suites.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

A = module('preserved_afcd', 'tools/data-processing/dataset-normalization/owner48_afcd.py')
C = module('preserved_conflicts', 'tools/data-processing/dataset-normalization/owner48_afcd_conflicts.py')
V = module('preserved_verify', 'tools/data-processing/dataset-normalization/owner48_verify_packets.py')
J = module('preserved_japan', 'tools/data-processing/owner51-normalization/japan_a.py')
S = module('preserved_six', 'tools/data-processing/owner51-normalization/apply_six_v2.py')
L = module('preserved_lookup', 'tools/data-processing/source_proposal_lookup_owner56.py')

class AFCDSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.reader = A.xml_reader()

    def test_dependency_hashes_and_tamper_fail_closed(self):
        self.assertEqual(A.sha(A.dependency_blob('afcd_xml_reader.py', A.XML_SHA)), A.XML_SHA)
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            A.dependency_blob('afcd_xml_reader.py', '0' * 64)
        notices = json.loads(A.dependency_blob('afcd_rights_evidence.json', A.RIGHTS_DEPENDENCY_SHA))
        self.assertEqual(notices['historical_receipt_sha256'], A.RIGHTS_SHA)
        self.assertIn('licenceUrl', notices['sourceNotices'])

    def test_unknown_zero_formula_and_text_stay_distinct(self):
        def cell(value, formula=None):
            return {'value': value, 'formula': formula, 'original_lexeme': str(value)}
        for value, status, expected in [(0, 'source-zero', 0), (2.5, 'source-number', 2.5),
                                        (None, 'missing', None), ('<0.1', 'source-text-or-qualifier', None)]:
            result = self.reader.observation(cell(value))
            self.assertEqual((result['status'], result['value']), (status, expected))
        self.assertIsNone(self.reader.observation(cell(9, '1+8'))['value'])
        self.assertEqual(self.reader.observation(None)['status'], 'missing')

    def test_denominators_not_coalesced(self):
        row = {'cells': {'E': {'value': 0, 'formula': None}}}
        for header, amount, unit in [('Synthetic (%T)',100,'g total fatty acids'),
                                     ('Synthetic (mg/gN)',1,'g nitrogen'), ('Synthetic (mg)',100,'ml')]:
            result = A.typed_source_observation(self.reader, row, 'E', header, 'ml', {})
            self.assertEqual((result['basis']['amount'], result['basis']['unit']), (amount,unit))
            self.assertEqual(result['observation']['value'], 0)
        with self.assertRaises(ValueError):
            A.typed_source_observation(self.reader,row,'E','Unknown (untrusted-unit)','g',{})

    def test_qualify_preserves_source_and_blocks_conflicts(self):
        record = {'id':'synthetic:example', 'countries':['AU'], 'provenance':{
            'sourceId':'afcd','recordId':'SYNTHETIC','license':'test-placeholder',
            'licenseUrl':self.reader.LICENCE,'attribution':'synthetic test only'},
            'data':{'foodName':'Synthetic example','basis':{'amount':100,'unit':'g'},'nutrients':{}}}
        row = {'number':4,'xml_sha256':'a'*64,'cells':{'A':{'value':'SYNTHETIC'},
               'D':{'value':'Synthetic example'},'E':{'value':0,'formula':None}}}
        detail = {'fields':{'Food Name':'Synthetic example'},'row':4,'xml_sha256':'b'*64}
        original = copy.deepcopy(record)
        result, reason = A.qualify(record,self.reader,{'E':'Synthetic (mg)'},row,'g',detail,{})
        self.assertIsNone(reason)
        self.assertEqual(record,original)
        self.assertFalse(result['semantic_gold'])
        self.assertFalse(result['translated_acceptance'])
        self.assertEqual(result['original_zero_observations'],1)
        self.assertEqual(len(result['recovered_source_columns']),1)
        for change in [{'blocked':True},{'license':''},{'recordId':'DIFFERENT'}]:
            changed=copy.deepcopy(record);changed['provenance'].update(change)
            self.assertIsNone(A.qualify(changed,self.reader,{'E':'Synthetic (mg)'},row,'g',detail,{})[0])
        changed=copy.deepcopy(record);changed['data']['nutrients']={'x':{'sourceColumn':5,'value':1,'unit':'mg'}}
        self.assertIsNone(A.qualify(changed,self.reader,{'E':'Synthetic (mg)'},row,'g',detail,{})[0])

    def test_conflict_requires_explicit_location_and_pin(self):
        with self.assertRaisesRegex(ValueError,'explicit evidence'):
            C.evidence()
        with self.assertRaisesRegex(ValueError,'Missing declared'):
            C.load_pin('historical-only','0'*64,{})
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'synthetic.json';path.write_text('{}')
            self.assertEqual(C.load_pin('historical-only',hashlib.sha256(b'{}').hexdigest(),{'historical-only':str(path)}),{})
            with self.assertRaises(ValueError): C.load_pin('historical-only','0'*64,{'historical-only':str(path)})

    def test_conflict_carries_unresolved_and_rejects_changed_coordinates(self):
        before={'source_sheet':'Synthetic profile','source_row':4,'source_row_xml_sha256':'a'*64,
                'food_detail_xml_sha256':'b'*64,'derivation':'synthetic old label',
                'recovered_source_columns':[{'value':0}]}
        case={'labels':[{'sheet':'Synthetic profile','row':4,'raw_row_sha256':'a'*64,'label':'synthetic old label'},
                        {'sheet':'Food details','raw_row_sha256':'b'*64,'label':'different synthetic label'}]}
        original=copy.deepcopy(before);result=C.carry_conflict(before,case)
        self.assertEqual(before,original)
        self.assertIsNone(result['derivation'])
        self.assertEqual(result['derivation_resolution']['status'],'UNRESOLVED')
        self.assertTrue(all(result['derivation_resolution'][k] is None for k in ['preferred_label','preferred_source','unified_nutrient_method_authority']))
        self.assertEqual(result['recovered_source_columns'],before['recovered_source_columns'])
        changed=copy.deepcopy(case);changed['labels'][0]['row']=5
        with self.assertRaises(ValueError):C.carry_conflict(before,changed)

    def test_packet_count_and_acceptance_guards(self):
        r={'original_normalized_id':'synthetic','food_basis':{'unit':'g'},'recovered_source_columns':[{}],
           'semantic_gold':False,'translated_acceptance':False}
        V.verify_normalization([r],expected=1,mass=1,volume=0,recovered=1)
        for key,value in [('semantic_gold',True),('translated_acceptance',True),('food_basis',{'unit':'ml'})]:
            changed=copy.deepcopy(r);changed[key]=value
            with self.assertRaises(ValueError):V.verify_normalization([changed],expected=1,mass=1,volume=0,recovered=1)
        with self.assertRaises(ValueError):V.verify_normalization([r,r],expected=2,mass=2,volume=0,recovered=2)

class JapanSyntheticTests(unittest.TestCase):
    def test_provenance_gate_exact_release_basis_and_identity(self):
        adapter=types.SimpleNamespace(RELEASE='synthetic-release',SHA256='a'*64)
        record={'id':'synthetic:01','countries':['JP'],'provenance':{'sourceId':'mext','releaseId':adapter.RELEASE,
            'archiveSha256':adapter.SHA256,'recordId':'01'},'data':{'identifiers':[{'system':'JP-MEXT','value':'01'}],
            'basis':{'amount':100,'unit':'g','state':'as-described','portion':'edible portion'}}}
        self.assertTrue(J.provenance_ok(record,adapter))
        for field,value in [('releaseId','other'),('archiveSha256','0'*64),('recordId','02'),('sourceId','other')]:
            changed=copy.deepcopy(record);changed['provenance'][field]=value
            self.assertFalse(J.provenance_ok(changed,adapter))
        changed=copy.deepcopy(record);changed['data']['basis']['unit']='ml'
        self.assertFalse(J.provenance_ok(changed,adapter))

    def make_case(self,annotation='†'):
        basis={'amount':100,'unit':'g'}
        value='2.0' if annotation=='†' else None
        lexical='2.0†' if annotation=='†' else '*'
        record={'sourceId':'mext','release':'synthetic-release','sourceCode':'SYNTHETIC',
            'provenance':{'sheet':'synthetic','member':'synthetic.xml','row':2,'memberSha256':'a'*64},
            'labels':{'ja':'合成テスト'},'observations':[{'sourceCell':'E2','sourceComponent':'synthetic-component',
            'sourceLexical':lexical,'qualifier':'uninterpreted-source-text','valueDecimal':None,'sourceUnit':'mg','basis':basis}]}
        eligibility={k:False for k in ['nutritionCalculationEligible','unqualifiedNutritionCalculationEligible',
            'conversionPerformed','fallbackToZeroAllowed','referenceSampleSubstitutionAllowed']}
        eligibility.update(calculationValueDecimal=None,basis=copy.deepcopy(basis),unit='mg')
        decision={'observationKey':{'sourceId':'mext','release':'synthetic-release','sourceCode':'SYNTHETIC','sheet':'synthetic',
            'member':'synthetic.xml','row':2,'cell':'E2','sourceComponent':'synthetic-component'},
            'sourceEvidence':{'originalJapaneseLabel':'合成テスト','memberSha256':'a'*64,'originalLexical':lexical},
            'sourceQualifiedCandidate':{'unit':'mg','basis':copy.deepcopy(basis),'annotation':annotation,'valueDecimal':value,
            'qualifier':'source-measured-prescribed-method' if annotation=='†' else 'standard-value-deliberately-withheld',
            'method':'synthetic test only'},'calculationEligibility':eligibility}
        return record,decision

    def test_annotations_preserve_calculation_exclusion(self):
        for annotation in ['*','†']:
            record,decision=self.make_case(annotation);before=copy.deepcopy(record)
            S.apply(record,decision);o=record['observations'][0]
            self.assertEqual(o['annotation'],annotation)
            self.assertFalse(o['nutritionCalculationEligible'])
            self.assertFalse(o['unqualifiedNutritionCalculationEligible'])
            self.assertIsNone(o['calculationValueDecimal'])
            self.assertEqual(record['labels'],before['labels'])
            self.assertEqual(record['provenance'],before['provenance'])

    def test_annotation_rejects_unit_basis_coordinates_and_authority_changes(self):
        mutations=[('sourceQualifiedCandidate','unit','g'),('sourceQualifiedCandidate','basis',{'amount':1,'unit':'g'}),
            ('calculationEligibility','fallbackToZeroAllowed',True),('calculationEligibility','calculationValueDecimal','0'),
            ('observationKey','row',3),('sourceEvidence','memberSha256','b'*64),('sourceQualifiedCandidate','annotation','?')]
        for section,key,value in mutations:
            with self.subTest(section=section,key=key):
                record,decision=self.make_case();decision[section][key]=value;before=copy.deepcopy(record)
                with self.assertRaises(ValueError):S.apply(record,decision)
                self.assertEqual(record,before)

    def test_duplicate_or_absent_observation_rejected(self):
        for size in [0,2]:
            record,decision=self.make_case();record['observations']*=size
            with self.assertRaises(ValueError):S.apply(record,decision)

    def test_build_refuses_existing_output_before_historical_access(self):
        with tempfile.TemporaryDirectory() as t,patch.object(J,'adapter',side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(ValueError,'Existing packet'):J.build(t)
            with self.assertRaisesRegex(ValueError,'existing output'):S.build(t)

class LookupSyntheticTests(unittest.TestCase):
    def make_lookup(self):
        proposal={'identity':{'sourceId':'synthetic','code':'01','releaseBinding':'r1'},'proposalId':'synthetic-proposal',
            'originalProposal':{'language':'zz','label':'Synthetic label','evidence':{'url':'https://example.invalid/synthetic'},
                                'rights':{'status':'synthetic-only'}},
            'sourceReview':{},'sourceReviewScope':'synthetic-only','bundleStatus':'proposal'}
        manifest={'sources':[]};bundle={'frozenMaster':{'sha256':L.FREEZE_SHA256},'proposals':[proposal],'exactLiteralCollisions':[]}
        # Constructor's byte pin is tested separately. This narrowly substitutes
        # in-memory synthetic input for lookup behavior, not a source acceptance.
        with patch.object(L,'pinned_json',side_effect=[manifest,bundle]):
            return L.SourceProposalLookup('synthetic-manifest','synthetic-bundle')

    def test_exact_language_release_and_detached_results(self):
        lookup=self.make_lookup();result=lookup.lookup('synthetic','01','zz','r1')
        self.assertEqual(result['label'],'Synthetic label');self.assertEqual(result['status'],'source-proposal')
        for key in ['canonicalAccepted','semanticGold','translationAccepted']:self.assertFalse(result[key])
        self.assertIsNone(result['crossSourceEquivalence'])
        result['rights']['status']='changed';result['identity']['code']='changed'
        self.assertEqual(lookup.lookup('synthetic','01','zz','r1')['rights']['status'],'synthetic-only')
        for args in [('synthetic','01','en','r1'),('synthetic','01','zz','other'),('other','01','zz','r1')]:
            result=lookup.lookup(*args);self.assertEqual(result['status'],'unknown');self.assertIsNone(result['label'])
        lookup._index[('synthetic','01')].append(copy.deepcopy(lookup._index[('synthetic','01')][0]))
        self.assertIn('ambiguous',lookup.lookup('synthetic','01','zz')['reason'])

    def test_nonempty_exact_strings_required(self):
        lookup=self.make_lookup()
        for args in [('', '01','zz'),('synthetic',True,'zz'),('synthetic','01',None),('synthetic','01','zz','')]:
            with self.assertRaises(ValueError):lookup.lookup(*args)

    def test_pin_and_freeze_tampering_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'synthetic.json';p.write_bytes(b'{}')
            self.assertEqual(L.pinned_json(p,hashlib.sha256(b'{}').hexdigest()),{})
            with self.assertRaises(ValueError):L.pinned_json(p,'0'*64)
        with patch.object(L,'pinned_json',side_effect=[{}, {'frozenMaster':{'sha256':'0'*64}}]):
            with self.assertRaises(ValueError):L.SourceProposalLookup('synthetic','synthetic')

if __name__ == '__main__':
    unittest.main()
