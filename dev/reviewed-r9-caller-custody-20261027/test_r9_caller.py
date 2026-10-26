import unittest
import copy
import hashlib
import json
from r9_caller import R9Caller

C = R9Caller()
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
NEW=[r for r in C.gate.engine.rules if r['ruleId'] in C.gated_rules]
class CallerTests(unittest.TestCase):
    def test_all_five_exact_current_gate_and_links(self):
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
            self.assertFalse(any(c['ruleId'] in C.gated_rules for c in out['wholeProductContextResolution']['candidateTargets']))
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
    def test_all_five_use_current_gate_with_diagnostics_false(self):
        self.assertEqual(len(C.gated_rules),5)
        self.assertEqual(len(C.gate.engine.accepted),88)
        self.assertEqual(len(C.types['acceptedConditionalRelations']),18)
        cut=C.input['requiredCut']
        self.assertEqual(cut['qualifiedGateMandatoryForFiveWholeFamilies']['sha256'],'88007f14c10aa9366e361f3cddf002bb3cdf52bdbc58af916952c2acf8ced157')
        original=C.gate.evaluate;seen=[]
        def traced(record,diagnostics=False):
            seen.append(diagnostics);return original(record,diagnostics=diagnostics)
        C.gate.evaluate=traced
        try:
            for rule in NEW:
                C.map_record(fixture(rule))
                for change in ('native','barcode','dual-array'):
                    row=fixture(rule)
                    if change=='native':row['sourceBinding']['nativeRecordId']='off:product:DIFFERENT'
                    elif change=='barcode':row['sourceAdapterInput']['identifiers'][0]['value']='DIFFERENT'
                    else:row['sourceAdapterInput']['fieldEvidence']['categories']['categories']['evidenceBytes']=999
                    out=C.map_record(row)
                    self.assertEqual(out['qualifiedWholeFamilyResolution']['qualification'],'failed')
                    self.assertNotIn('qualifiedWholeFamilyTypeRelations',out)
        finally:C.gate.evaluate=original
        self.assertEqual(seen,[False]*20)
    def test_dependency_missing_or_changed_bytes_refused(self):
        from r9_caller import FrozenModules
        from unittest.mock import patch
        from pathlib import Path
        path=C.frozen.engine_path;digest=hashlib.sha256(C.frozen.bytes[path]).hexdigest()
        with patch.object(Path,'read_bytes',return_value=b'CHANGED'):
            with self.assertRaises(ValueError):FrozenModules({path:digest})
            # Existing snapshot still returns exact previously verified bytes.
            self.assertEqual(C.frozen.path_type(path).read_bytes(),C.frozen.bytes[path])
        with patch.object(Path,'read_bytes',side_effect=FileNotFoundError('generated missing dependency')):
            with self.assertRaises(FileNotFoundError):FrozenModules({path:digest})
    def test_frozen_dependency_reads_and_module_isolation(self):
        import sys
        before=sys.modules.get('context_rules')
        other=R9Caller()
        self.assertIs(sys.modules.get('context_rules'),before)
        with self.assertRaises(ValueError):other.frozen.path_type('/unlisted/source.json').read_bytes()
        engine=other.frozen.engine_path
        self.assertEqual(other.frozen.path_type(engine).read_bytes(),other.frozen.bytes[engine])
        self.assertIsNot(other.gate.engine,C.gate.engine)
if __name__=='__main__':unittest.main()
