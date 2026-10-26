import unittest
import copy
import hashlib
import json
from r8_caller import R8Caller

C = R8Caller()
CODEC = 'typed-exact-decimal-json/1; not an original byte-span hash'
def fixture(rule, declaration=None):
    name = rule['nameExactValues'][0]
    prefix='/0/data/' if rule['sourceScope']['sourceId']=='usda-files' else '/data/'
    binding = {**rule['sourceScope'], 'recordId':'0000000000000',
               'sourceObservationSha256':'a'*64, 'sourceDocumentSha256':'b'*64,
               'inputDatabaseSha256':'c'*64, 'stageRecordId':'generated:stage',
               'stageRecordWireSha256':'d'*64}
    values = {'name':name,'names':{'en':name},'ingredientDeclaration':declaration,
              'categories':rule['requiredCategories'], 'dataType':rule.get('allowedDataTypes',[None])[0]}
    fields, secondary, originals = {}, {}, {}
    slots = {'name':'name','names':'names','ingredientDeclaration':'ingredientsText','categories':'categories','dataType':'dataType'}
    for role,value in values.items():
        suffix=slots[role];raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        state='null' if value is None else 'empty' if value in ('',[],{}) else 'present'
        fields[role]={'state':state,'originalValue':copy.deepcopy(value),'sourcePointer':prefix+suffix,'valueSha256':hashlib.sha256(raw).hexdigest(),'evidenceBytes':len(raw),'evidenceEncoding':CODEC}
        cell={'state':state,'pointer':prefix+suffix,'parsedValueEvidenceSha256':hashlib.sha256(raw).hexdigest(),'evidenceBytes':len(raw),'evidenceEncoding':CODEC}
        if role=='names':secondary.setdefault('languages',{})['names']=cell
        elif role in ('categories','dataType'):secondary.setdefault('categories',{})[role]=cell
        else:secondary[role]=cell
        originals[suffix]=copy.deepcopy(value)
    inner={'sourceBinding':copy.deepcopy(binding),'identifiers':[{'system':'barcode','value':binding['recordId']}],
           'sourceProductContext':{'schema':'offmenu-source-product-context/1','sourceEvidence':copy.deepcopy(binding),'fields':fields},
           'fieldEvidence':copy.deepcopy(secondary),'categories':copy.deepcopy(values['categories'])}
    return {'sourceBinding':{**binding,'nativeRecordId':'off:product:'+binding['recordId']},
            'sourceAdapterInput':inner,'sourceProvenance':{'visibility':'source-staging',**{k:binding[k] for k in ('sourceId','releaseId','recordId','sourceDocumentSha256')}},
            'sourceFieldStates':copy.deepcopy(secondary),'originalFields':originals,
            'stageRecordId':binding['stageRecordId'],'evidenceSource':{'recordWireSha256':binding['stageRecordWireSha256']}}
NEW=[r for r in C.gate.engine.rules if r['ruleId'] in C.new_rules]
class CallerTests(unittest.TestCase):
    def test_new_three_exact_gate_and_links(self):
        for rule in NEW:
            row=fixture(rule);before=copy.deepcopy(row);gate=C.gate.evaluate(row,diagnostics=False)
            self.assertEqual(gate['qualification'],'passed',gate)
            out=C.map_record(row);self.assertEqual(out['wholeProductContextResolution'],gate['engineResolution'])
            self.assertTrue(out['classificationAccepted']);self.assertEqual(len(out['qualifiedWholeFamilyTypeRelations']),1)
            self.assertEqual(out['qualifiedWholeFamilyTypeRelations'][0]['relation']['sourceRuleId'],rule['ruleId'])
            legacy=C.legacy.map_record(row)
            for key in legacy.keys()-{'wholeProductContextResolution','classificationAccepted','productTypeAccepted','wholeProductClassificationDisposition','contextMappingRevision'}:
                self.assertEqual(out[key],legacy[key],key)
            self.assertEqual(row,before);self.assertFalse(out['normalizationComplete'])
    def test_null_empty_compatible_declarations(self):
        for rule in NEW:
            for declaration in (None,'',rule['nameExactValues'][0]):
                self.assertTrue(C.map_record(fixture(rule,declaration))['classificationAccepted'])
    def test_conflict_has_no_new_targets_or_type(self):
        for rule in NEW:
            row=fixture(rule,rule['wholeContextConflictPolicy']['declarationConflictTerms'][0])
            out=C.map_record(row)
            self.assertEqual(out['wholeProductClassificationDisposition'],'whole-context-conflict-abstain')
            self.assertFalse(out['classificationAccepted']);self.assertFalse(out['productTypeAccepted'])
            self.assertEqual(out['wholeProductContextResolution']['candidateTargets'],[])
            self.assertEqual(out['qualifiedWholeFamilyTypeRelations'],[])
            self.assertIsNone(out['qualifiedWholeFamilyResolution']['engineResolution'])
    def test_failed_privacy_and_commitment_never_consumes_new_targets(self):
        for mutation in ('private','wire','field'):
            row=fixture(NEW[0])
            if mutation=='private':row['sourceAdapterInput']['sourceProductContext']['sourceEvidence']['visibility']='private'
            elif mutation=='wire':row['evidenceSource']['recordWireSha256']='e'*64
            else:row['originalFields']['name']='CONTRADICTORY'
            out=C.map_record(row)
            self.assertEqual(out['qualifiedWholeFamilyResolution']['qualification'],'failed')
            self.assertNotIn('qualifiedWholeFamilyTypeRelations',out)
            self.assertFalse(any(c['ruleId'] in C.new_rules for c in out['wholeProductContextResolution']['candidateTargets']))
    def test_legacy_off_unrelated_and_usda_unchanged(self):
        row=fixture(NEW[0]);row['sourceBinding']['sourceId']='usda-files'
        self.assertEqual(C.map_record(row),C.legacy.map_record(row))
        row=fixture(NEW[0]);row['sourceBinding']['sourceId']='generated-other'
        self.assertEqual(C.map_record(row),C.legacy.map_record(row))
        # A qualified OFF envelope without any new rule match stays exact83.
        row=fixture(NEW[0]);row['sourceAdapterInput']['sourceProductContext']['fields']['name']['originalValue']='unrelated'
        # Use generated valid fixture, replacing all names via another rule's context.
        unrelated=copy.deepcopy(NEW[0]);unrelated['nameExactValues']=['Unrelated generated product'];unrelated['requiredCategories']=[]
        row=fixture(unrelated)
        self.assertEqual(C.map_record(row),C.legacy.map_record(row))
    def test_accepted_usda_legacy_positive_unchanged(self):
        rule=next(r for r in C.legacy.REVIEWED.engine.rules if r['sourceScope']['sourceId']=='usda-files' and r.get('nameExactValues'))
        row=fixture(rule,rule['declarations'][0]);expected=C.legacy.map_record(row)
        self.assertTrue(expected['classificationAccepted'])
        self.assertEqual(C.map_record(row),expected)
    def test_frozen_dependency_reads_and_module_isolation(self):
        import sys
        before=sys.modules.get('context_rules')
        other=R8Caller()
        self.assertIs(sys.modules.get('context_rules'),before)
        with self.assertRaises(ValueError):other.frozen.path_type('/unlisted/source.json').read_bytes()
        engine=other.frozen.engine_path
        self.assertEqual(other.frozen.path_type(engine).read_bytes(),other.frozen.bytes[engine])
        self.assertIsNot(other.gate.engine,C.gate.engine)
if __name__=='__main__':unittest.main()
