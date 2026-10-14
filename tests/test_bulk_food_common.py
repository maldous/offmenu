"""Regression coverage for common bulk food alignment fidelity boundaries."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('bulk_common', Path(__file__).parents[1] / 'scripts' / 'align-bulk-food-common.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

MANIFEST = {'releaseId':'fixture','archiveSha256':'a'*64,'license':'CC0','attribution':'Fixture'}

def profile(record_id, nutrients):
    return {'id':record_id,'kind':'nutrientProfile','provenance':{'recordId':record_id,'sourceId':'usda-files','url':'https://example.test/source','license':'CC0','attribution':'Fixture','visibility':'public'},'data':{'foodName':'Sample food','basis':{'amount':100,'unit':'g','state':'as-described'},'nutrients':nutrients}}

def facts(packet, suffix):
    return [x for x in packet['assertions'] if x['propertyId'].endswith(suffix)]

class BulkFoodCommonTests(unittest.TestCase):
  def test_nutrient_observations_keep_each_original_basis_and_definition_metadata(self):
    p=MOD.packet(profile('a',{
        'energy':{'value':10,'unit':'kcal','basis':{'amount':100,'unit':'g','state':'as-described'},'definition':'USDA-FDC:1008','method':'calculated','qualifier':'estimated'},
        'sodium':{'value':8,'unit':'mg','basis':{'amount':30,'unit':'g','state':'prepared'},'definition':'USDA-FDC:1093','method':'laboratory','qualifier':'source-reported','extraField':'kept'}
    }),'usda-files',MANIFEST)
    quantities={x['sourcePath'].split('.')[-1]:x['value'] for x in facts(p,'nutrientObservation')}
    self.assertEqual(quantities['energy']['basis']['value'],100)
    self.assertEqual(quantities['sodium']['basis']['value'],30)
    self.assertNotIn('definitionId',quantities['energy'])
    metadata={x['sourcePath'].split('.')[-2]:x['value']['fields'] for x in facts(p,'sourceNutrientMetadata')}
    self.assertEqual(metadata['energy']['definition'],{'kind':'identifier','value':'USDA-FDC:1008'})
    self.assertEqual(metadata['sodium']['definition'],{'kind':'identifier','value':'USDA-FDC:1093'})
    self.assertEqual(metadata['sodium']['method'],{'kind':'identifier','value':'laboratory'})
    self.assertEqual(metadata['sodium']['qualifier'],{'kind':'identifier','value':'source-reported'})
    self.assertEqual(metadata['sodium']['extraField']['value'],'kept')

  def test_source_strings_are_cited_text_but_fixed_code_date_and_uri_are_not_translatable(self):
    c='urn:offmenu:bulk:citation:test'
    value=MOD.typed({'name':'Crème brûlée','currency':'EUR','observedAt':'2026-10-14','url':'https://example.test/a'},c,'data')
    fields=value['fields']
    self.assertEqual((fields['name']['kind'],fields['name']['language'],fields['name']['citationIds']),('text','und',[c]))
    self.assertEqual(fields['currency'],{'kind':'identifier','value':'EUR'})
    self.assertEqual(fields['observedAt'],{'kind':'date','value':'2026-10-14'})
    self.assertEqual(fields['url'],{'kind':'uri','value':'https://example.test/a'})

  def test_same_source_text_from_different_records_has_distinct_cited_text_ids(self):
    a=MOD.packet(profile('a',{}),'usda-files',MANIFEST)
    b=MOD.packet(profile('b',{}),'usda-files',MANIFEST)
    self.assertEqual(a['resources'][0]['names'][0]['value'],b['resources'][0]['names'][0]['value'])
    self.assertEqual(a['resources'][0]['names'][0]['value'],'Sample food')
    self.assertNotEqual(a['resources'][0]['names'][0]['id'],b['resources'][0]['names'][0]['id'])
    self.assertNotEqual(a['resources'][0]['names'][0]['citationIds'],b['resources'][0]['names'][0]['citationIds'])

  def test_upstream_record_id_and_accepted_curation_envelope_are_retained(self):
    row=profile('offmenu:nutrientProfile:abc',{})
    row['provenance']['recordId']='4099200009834'
    row['countries']=['FR']
    row['curation']={'sourceRecordReference':'off:nutrientProfile:4099200009834','status':'selected-source-facts','humanReviewed':False,'automaticDietQualification':False,'rawSourcePayloadPublished':False}
    packet=MOD.packet(row,'usda-files',MANIFEST)
    citation=packet['citations'][0]
    self.assertEqual(citation['originalRecordId'],'4099200009834')
    self.assertEqual(citation['sourcePath'],'off:nutrientProfile:4099200009834')
    context=facts(packet,'curatedRecordContext')[0]['value']['fields']
    self.assertEqual(context['countries']['items'][0]['value'],'FR')
    self.assertEqual(context['curation']['fields']['humanReviewed'],{'kind':'boolean','value':False})
    self.assertEqual(context['curation']['fields']['sourceRecordReference']['value'],'off:nutrientProfile:4099200009834')

  def test_accepted_envelope_control_handles_are_fixed_and_uris_stay_uris(self):
    c='urn:offmenu:bulk:citation:controls'
    controls={'sourceId':'off','recordId':'4099200009834','schemaVersion':'1.0','schema':'offmenu-curation/1','policyVersion':'offmenu-curation/1','sourceRecordReference':'off:product:4099200009834','kind':'product','visibility':'public','archiveSha256':'a'*64,'languageTag':'fr','countries':['FR'],'ontology':'urn:foodon:0001','rights':'Human-readable licence notice'}
    fields=MOD.typed(controls,c,'context')['fields']
    for name in ('sourceId','recordId','schemaVersion','schema','policyVersion','sourceRecordReference','kind','visibility','archiveSha256','languageTag'):
      self.assertEqual(fields[name]['kind'],'identifier',name)
    self.assertEqual(fields['countries']['items'][0]['kind'],'identifier')
    self.assertEqual(fields['ontology'],{'kind':'uri','value':'urn:foodon:0001'})
    self.assertEqual(fields['rights']['kind'],'text')
