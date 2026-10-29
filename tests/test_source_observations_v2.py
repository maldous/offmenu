import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('v2', Path(__file__).parents[1] / 'tools/data-processing/normalize_source_observations_v2.py')
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)


class SourceObservationTests(unittest.TestCase):
    def normalize(self, source, record, **kwargs):
        before = copy.deepcopy(record)
        result = v2.normalize(source, record, adapter_commit=v2.QUALIFIED_ADAPTERS[source], **kwargs)
        self.assertEqual(record, before)
        self.assertEqual(result['sourceEvidence'], before)
        self.assertFalse(result['packageAdmitted'])
        self.assertFalse(result['automaticPlanningEligible'])
        return result

    def test_metric_basis_zero_and_qualifiers(self):
        metrics = [{'component': 'fatty', 'value': 4.3, 'unit': 'g', 'basis': {'amount':100,'unit':'g-fatty-acids'}, 'original':'4.30','qualifier':'source'},
                   {'component': 'zero', 'value': 0, 'unit':'mg','basis':{'amount':100,'unit':'ml'},'original':0,'qualifier':'source'},
                   {'component': 'trace', 'value':None,'unit':'g','basis':{'amount':100,'unit':'g'},'original':'Tr','qualifier':'trace'}]
        result = self.normalize('cofid', {'recordId':'food','basis':{'amount':100,'unit':'g'},'metrics':metrics})
        self.assertEqual(result['observations'][0]['basis']['unit'],'g-fatty-acids')
        self.assertEqual(result['observations'][1]['value'],0)
        self.assertEqual(result['observations'][1]['basis']['unit'],'ml')
        self.assertEqual(result['observations'][2]['qualifier'],'trace')

    def test_ciqual_censor_and_retinol_quarantine(self):
        metrics=[{'sourceComponent':'51104','value':3,'unit':'µg','basis':{'amount':100,'unit':'mg'},'qualifier':'source'},
                 {'sourceComponent':'other','value':None,'unit':'mg','basis':{'amount':100,'unit':'g'},'limit':0.1,'original':'<0.1','qualifier':'less-than'}]
        result=self.normalize('ciqual',{'sourceId':'ciqual','sourceFoodId':'food','observations':metrics})
        self.assertTrue(result['observations'][0]['quarantined'])
        self.assertEqual(result['observations'][0]['basis']['unit'],'mg')
        self.assertEqual(result['observations'][1]['limit'],0.1)
        self.assertIsNone(result['observations'][1]['value'])

    def test_bls_dictionary_completeness_notes_and_definitions(self):
        definition={'name':'Energy','application':'always calculated'}
        record={'sourceId':'germany-bls','recordId':'food','notes':{'Hinweis':'source note'},'nutrients':{'ENERCC':{'value':0,'unit':'kJ','basis':{'amount':100,'unit':'g'},'componentDefinition':definition}}}
        headers=['ENERCC [kJ/100g]','ENERCC Datenherkunft','ENERCC Referenz','Hinweis']
        result=self.normalize('bls',record,component_dictionary={'ENERCC':definition},headers=headers)
        self.assertEqual(result['notes'],record['notes'])
        self.assertEqual(result['observations'][0]['sourceObservation']['componentDefinition'],definition)
        for dictionary in [{},{'OTHER':definition}]:
            with self.assertRaises(ValueError):self.normalize('bls',record,component_dictionary=dictionary,headers=headers)

    def test_off_context_unknown_and_price_noncomparability(self):
        result=self.normalize('off',{'source_values':{'code':'123','rev':2,'serving_quantity':None,'nutrition_data_prepared_per':'serving','nutriments':{'fat_100g':0}}})
        self.assertEqual(result['basisStatus'],'unknown')
        self.assertEqual(result['revision']['rev'],2)
        self.assertIsNone(result['nutritionContext']['serving_quantity'])
        price_record=v2.price_audit_record({'id':1,'date':'2026-01-01','receipt_quantity':'2'}, {'fixture':True})
        prices=self.normalize('prices',price_record)
        self.assertFalse(prices['quantity']['comparable'])
        self.assertIsNone(prices['quantity']['packSize'])
        self.assertEqual(prices['quantity']['receiptQuantityLexical'],'2')

    def test_recipe_diagnostics_are_not_replacement(self):
        row={'id':'recipe:1','kind':'recipe','provenance':{'sourceId':'world-recipes','originSourceId':'fixture','recordId':'fixture'},'data':{'ingredients':[{'originalText':'pinch of salt','amount':None}]}}
        import hashlib
        row['id']='world-recipes:recipe:'+hashlib.sha256((row['provenance']['originSourceId']+'\0'+row['provenance']['recordId']).encode()).hexdigest()[:24]
        audit=v2.recipe_audit_record(row)
        result=self.normalize('recipes',{'record':row,'audit':audit})
        self.assertEqual(result['ingredients'],row['data']['ingredients'])
        self.assertEqual(result['parserIssues'],audit['issues'])

    def test_off_citation_uses_product_revision_and_modified_time_not_export(self):
        manifest={'sourceId':'off','releaseId':'export-2026','archiveSha256':'a'*64,
                  'url':'https://world.openfoodfacts.org','license':'ODbL / DbCL'}
        values={'code':'0000101209159','rev':20,'last_modified_t':1781851567,
                'last_updated_t':1790086163,'nutriments':{'fat_100g':0}}
        out=self.normalize('off',{'source_values':values},source_manifest=manifest)
        citation=out['canonicalPacket']['citations'][0]
        from datetime import datetime,timezone
        self.assertEqual(citation['revisionId'],'20')
        self.assertEqual(citation['sourceDate'],datetime.fromtimestamp(values['last_modified_t'],timezone.utc).isoformat().replace('+00:00','Z'))
        self.assertEqual(citation['originalUrl'],manifest['url'])
        self.assertIsNone(citation['contentSha256'])
        self.assertNotIn('rightsEvidenceUrl',citation)
        self.assertIn('export-2026',v2.encoded(out['canonicalPacket']).decode())
        changed=copy.deepcopy(values);changed['rev']=21
        other=self.normalize('off',{'source_values':changed},source_manifest=manifest)
        self.assertEqual(other['canonicalPacket']['citations'][0]['revisionId'],'21')
        self.assertEqual(out['revision']['last_updated_t'],values['last_updated_t'])
        self.assertTrue(all(i['scope']['visibility']=='local-restricted' for section in ('resources','assertions','citations') for i in out['canonicalPacket'][section]))

    def test_off_missing_invalid_revision_time_remain_unknown(self):
        manifest={'sourceId':'off','releaseId':'export','url':'https://world.openfoodfacts.org'}
        for bad in [None,True,0,-1,'20',1.5]:
            out=self.normalize('off',{'source_values':{'code':'001','rev':bad,'last_modified_t':None,'last_updated_t':1790086163}},source_manifest=manifest)
            self.assertIsNone(out['canonicalPacket']['citations'][0]['revisionId'])
            self.assertIsNone(out['canonicalPacket']['citations'][0]['sourceDate'])
        for bad in [None,True,-1,'1781851567',1.5,10**30]:
            out=self.normalize('off',{'source_values':{'code':'001','rev':1,'last_modified_t':bad}},source_manifest=manifest)
            self.assertIsNone(out['canonicalPacket']['citations'][0]['sourceDate'])
        with self.assertRaises(ValueError):
            self.normalize('off',{'source_values':{'code':'001','rev':1}},source_manifest={**manifest,'url':None})

    def test_national_actual_graph_path_preserves_metric_basis_and_censor(self):
        record={'sourceId':'ciqual','sourceFoodId':'food','observations':[
            {'sourceComponent':'51104','value':3,'unit':'µg','basis':{'amount':100,'unit':'mg'},'qualifier':'source','originalText':'3'},
            {'sourceComponent':'other','value':None,'unit':'mg','basis':{'amount':100,'unit':'g'},'limit':0.1,'qualifier':'less-than','originalText':'<0.1'}]}
        base={'id':'ciqual:food','provenance':{'sourceId':'ciqual','recordId':'food','url':'https://example.org','license':'CC0'},'data':{'foodName':'Food','basis':{'amount':100,'unit':'g'}}}
        result=self.normalize('ciqual',record,base_record=base)
        values=[a['value'] for a in result['canonicalPacket']['assertions'] if a['propertyId']=='urn:offmenu:property:metricValue']
        self.assertIsNone(values[0]['value'])
        self.assertEqual(values[0]['basis']['sourceUnit'],'mg')
        self.assertEqual(values[1]['range'],{'min':None,'max':0.1})
        self.assertIn('censored-upper-bound-exclusive',values[1]['qualifiers'])
        self.assertEqual(base['data']['basis']['unit'],'g')

    def test_business_rdf_and_label_language_reach_canonical_assertions(self):
        row={'schemaVersion':'1.0','kind':'organization','id':'wikidata:Q1','data':{'name':'Label','names':{'fr':'Nom'}},
             'provenance':{'sourceId':'wikidata-food-businesses','recordId':'Q1','url':'https://example.org','license':'CC0','attribution':'Example','visibility':'public'},
             'localValidationEvidence':{'queryBindings':[{'entityLabel':{'type':'literal','value':'Label','xml:lang':'en'},'website':{'type':'uri','value':'http://example.org'}}]}}
        result=self.normalize('businesses',row)
        packet=result['canonicalPacket']
        self.assertEqual(packet['resources'][0]['type'],'urn:offmenu:type:Organization')
        self.assertTrue(any(n['language']=='en' and n['value']=='Label' for n in packet['resources'][0]['names']))
        self.assertIn('sourceQueryBindings',v2.encoded(packet).decode())
        self.assertEqual(result['productionOrigin'],'unknown')
        row['provenance']['visibility']='private'
        with self.assertRaises(ValueError):self.normalize('businesses',row)

    def test_fdc_source_unit_basis_and_null_loq_are_preserved(self):
        metrics=[{'row_id':'ug','unit':'UG','definition':{'unit_name':'UG'},'amount':{'source':'258.0','decimal':'258.0','state':'numeric'},
                  'basis':{'amount':'100','unit':'g'},'loq':{'source':None,'decimal':None,'state':'missing'},'qualifiers':[]},
                 {'row_id':'gravity','unit':'SP_GR','definition':{'unit_name':'SP_GR'},'amount':{'source':'1.04','decimal':'1.04','state':'numeric'},
                  'basis':{'amount':None,'unit':None,'status':'component-specific-basis-unresolved'},
                  'loq':{'source':None,'decimal':None,'state':'missing'},'qualifiers':['component-specific-basis-unresolved']},
                 {'row_id':'zero','unit':'G','definition':{'unit_name':'G'},'amount':{'source':'0.0','decimal':'0.0','state':'numeric-zero'},
                  'basis':{'amount':'100','unit':'g'},'loq':{'source':None,'decimal':None,'state':'missing'},'qualifiers':['zero-is-not-proof-of-absence']}]
        result=self.normalize('fdc',{'fdc_id':'food','nutrients':metrics},source_manifest={'sourceId':'usda-files','releaseId':'fixture'})
        quantities=[a['value'] for a in result['canonicalPacket']['assertions'] if a['propertyId']=='urn:offmenu:property:nutrientObservation']
        self.assertEqual(quantities[0]['unitId'],'urn:offmenu:unit:ug')
        self.assertEqual(quantities[0]['sourceUnit'],'UG')
        self.assertIsNone(quantities[1]['basis']['value'])
        self.assertIsNone(quantities[1]['unitId'])
        self.assertEqual(quantities[2]['value'],0)
        self.assertTrue(all('source-loq-reported' not in q['qualifiers'] for q in quantities))

    def test_bls_identity_order_serialization_and_actual_language_columns(self):
        definitions={'ENERCC':{'Nährstoffbezeichnung':'Energie (Kilokalorien)','Component name':'Energy (kilocalorie)'},
                     'WATER':{'Nährstoffbezeichnung':'Wasser','Component name':'Water'}}
        record={'sourceId':'germany-bls','recordId':'food','notes':{'Hinweis':'note'},'nutrients':{
            key:{'value':0,'unit':'g','basis':{'amount':100,'unit':'g'},'componentDefinition':definition}
            for key,definition in definitions.items()}}
        headers=['ENERCC [kcal/100g]','ENERCC Datenherkunft','ENERCC Referenz','WATER [g/100g]','WATER Datenherkunft','WATER Referenz']
        base={'id':'germany-bls:food','provenance':{'sourceId':'germany-bls','recordId':'food','releaseId':'4.0'},'data':{'foodName':'Food'}}
        def normalized(raw):
            return self.normalize('bls',raw,component_dictionary=definitions,headers=headers,base_record=base)
        def identity(out):
            assertions=[a for a in out['canonicalPacket']['assertions'] if a['propertyId']=='urn:offmenu:property:metricDefinition']
            return {obs['component']:(a['subjectId'],a['value']['value']) for obs,a in zip(out['observations'],assertions)}
        original=normalized(record)
        reversed_record=copy.deepcopy(record)
        reversed_record['nutrients']=dict(reversed(list(record['nutrients'].items())))
        reordered=normalized(reversed_record)
        import json
        serialized=normalized(json.loads(json.dumps(record,sort_keys=True)))
        self.assertEqual(identity(original),identity(reordered))
        self.assertEqual(identity(original),identity(serialized))
        self.assertEqual(original['sourceEvidenceSha256'],reordered['sourceEvidenceSha256'])
        subset=copy.deepcopy(original)
        subset['observations']=[o for o in original['observations'] if o['component']=='ENERCC']
        subset['canonicalPacket']=v2.national_packet(subset,base)
        self.assertEqual(identity(original)['ENERCC'],identity(subset)['ENERCC'])
        resource=next(r for r in original['canonicalPacket']['resources'] if r['id']==identity(original)['ENERCC'][0])
        self.assertEqual({n['language']:n['value'] for n in resource['names']},
                         {'de':'Energie (Kilokalorien)','en':'Energy (kilocalorie)'})

    def test_cofid_coordinate_observations_share_stable_component_definition(self):
        metrics=[{'component':'X','sheet':'FA','row':4,'column':8,'value':4.3,'unit':'g','basis':{'amount':100,'unit':'g-fatty-acids'},'qualifier':'source'},
                 {'component':'X','sheet':'food','row':4,'column':9,'value':1.2,'unit':'g','basis':{'amount':100,'unit':'g'},'qualifier':'source'}]
        record={'recordId':'food','metrics':metrics}
        base={'id':'cofid:food','provenance':{'sourceId':'cofid','recordId':'food','releaseId':'2021'},'data':{'foodName':'Food'}}
        original=self.normalize('cofid',record,base_record=base)
        reversed_record=copy.deepcopy(record);reversed_record['metrics'].reverse()
        changed=self.normalize('cofid',reversed_record,base_record=base)
        def ids(out):return {(a['subjectId'],a['value']['value']) for a in out['canonicalPacket']['assertions'] if a['propertyId']=='urn:offmenu:property:metricDefinition'}
        self.assertEqual(ids(original),ids(changed))
        self.assertEqual(len({subject for subject,definition in ids(original)}),2)
        self.assertEqual(len({definition for subject,definition in ids(original)}),1)
        subset=copy.deepcopy(original);subset['observations']=subset['observations'][:1];subset['canonicalPacket']=v2.national_packet(subset,base)
        self.assertTrue(ids(subset)<=ids(original))

    def test_recipe_bound_audit_scope_and_manifest_fail_closed(self):
        row={'id':'world-recipes:recipe:fixture','kind':'recipe',
             'scope':{'visibility':'private','ownerId':'alice'},
             'provenance':{'sourceId':'world-recipes','recordId':'original','url':'https://example.org/recipe','license':'CC0','originSourceId':'fixture'},
             'data':{'ingredients':[{'originalText':'salt','amount':None}],'automaticPlanningEligible':False}}
        import hashlib
        row['id']='world-recipes:recipe:'+hashlib.sha256((row['provenance']['originSourceId']+'\0'+row['provenance']['recordId']).encode()).hexdigest()[:24]
        audit=v2.recipe_audit_record(row)
        manifest={'sourceId':'world-recipes','releaseId':'fixture'}
        out=self.normalize('recipes',{'record':row,'audit':audit},source_manifest=manifest)
        for section in ('resources','assertions','citations'):
            self.assertTrue(all(x['scope']['visibility']=='private' and x['scope']['ownerId']=='alice' for x in out['canonicalPacket'][section]))
        for field,value in [('provenance',{'recordId':'wrong'}),('unresolved_amounts',0),('issues',[])]:
            changed=copy.deepcopy(audit);changed[field]=value
            with self.assertRaises(ValueError):self.normalize('recipes',{'record':row,'audit':changed},source_manifest=manifest)
        with self.assertRaises(ValueError):self.normalize('recipes',{'record':row,'audit':audit},source_manifest={'sourceId':'prices'})
        with self.assertRaises(ValueError):self.normalize('recipes',{'record':row,'audit':audit},source_manifest=manifest,candidate_scope={'visibility':'private','ownerId':'bob'})
        with self.assertRaises(ValueError):self.normalize('recipes',{'record':row,'audit':audit},source_manifest=manifest,candidate_scope={'visibility':'public'})

    def test_price_packet_captures_reference_flags_and_invalid_date_as_text(self):
        import json,hashlib
        raw={'id':1,'date':'2024-02-30','price':'2.300','receipt_quantity':'3.000'}
        line=(json.dumps(raw)+'\n').encode()
        reference={'archiveSha256':'a'*64,'line':1,'lineSha256':hashlib.sha256(line).hexdigest(),'releaseId':'fixture'}
        record=v2.price_audit_record(raw,reference)
        manifest={'sourceId':'prices','archiveSha256':'a'*64,'releaseId':'fixture','url':'https://example.org/prices','license':'ODbL'}
        out=self.normalize('prices',record,source_manifest=manifest,source_record_bytes=line)
        packet=out['canonicalPacket'];citation=packet['citations'][0]
        self.assertEqual(citation['originalUrl'],manifest['url'])
        self.assertEqual(citation['contentSha256'],reference['lineSha256'])
        self.assertEqual(citation['originalRecordId'],'1')
        self.assertNotIn('rightsEvidenceUrl',citation)
        self.assertFalse(any(a['propertyId'].endswith(':observedAt') for a in packet['assertions']))
        self.assertIn('invalid:date',v2.encoded(packet).decode())
        self.assertIn('lineSha256',v2.encoded(packet).decode())
        self.assertTrue(all(x['scope']['visibility']=='local-restricted' for section in ('resources','assertions','citations') for x in packet[section]))
        def date_nodes(value):
            if isinstance(value,dict):return [value] if value.get('kind')=='date' else sum((date_nodes(x) for x in value.values()),[])
            if isinstance(value,list):return sum((date_nodes(x) for x in value),[])
            return []
        self.assertFalse(any(x.get('value')==raw['date'] for x in date_nodes(packet)))
        for wrong in [None,b'{}',line+b' ']:
            with self.assertRaises(ValueError):self.normalize('prices',record,source_manifest=manifest,source_record_bytes=wrong)
        altered=copy.deepcopy(record);altered['sourceValues']['receipt_quantity']='9.000'
        with self.assertRaises(ValueError):self.normalize('prices',altered,source_manifest=manifest,source_record_bytes=line)
        with self.assertRaises(ValueError):self.normalize('prices',record,source_manifest={**manifest,'sourceId':'off'},source_record_bytes=line)

    def test_business_rdf_controls_are_fixed_and_literals_keep_source_language(self):
        bindings=[{'entity':{'type':'uri','value':'https://example.org/Q1'},
                   'entityLabel':{'type':'literal','value':'https://example.org/quoted-label','xml:lang':'en'},
                   'number':{'type':'typed-literal','value':'001.20','datatype':'http://www.w3.org/2001/XMLSchema#decimal'},
                   'blank':{'type':'bnode','value':'source-blank'}}]
        row={'schemaVersion':'1.0','kind':'organization','id':'wikidata:Q1','data':{'name':'Source label'},
             'provenance':{'sourceId':'wikidata-food-businesses','recordId':'Q1','url':'https://example.org','license':'CC0','attribution':'Fixture','visibility':'public'},
             'localValidationEvidence':{'queryBindings':bindings}}
        out=self.normalize('businesses',row);packet=out['canonicalPacket']
        source=next(a['value'] for a in packet['assertions'] if a['sourcePath']=='$.sourceRecord')
        fields=source['fields']['data']['fields']['sourceQueryBindings']['items'][0]['fields']
        self.assertEqual(fields['entityLabel']['fields']['xml:lang'],{'kind':'identifier','value':'en'})
        self.assertEqual(fields['entityLabel']['fields']['type'],{'kind':'identifier','value':'literal'})
        literal=fields['entityLabel']['fields']['value']
        self.assertEqual(literal['kind'],'text')
        self.assertEqual(literal['language'],'en')
        self.assertEqual(literal['value'],bindings[0]['entityLabel']['value'])
        self.assertEqual(fields['number']['fields']['datatype']['kind'],'uri')
        self.assertEqual(fields['number']['fields']['value']['value'],'001.20')
        self.assertEqual(fields['number']['fields']['value']['language'],'und')
        self.assertEqual(fields['blank']['fields']['value'],{'kind':'identifier','value':'source-blank'})
        self.assertEqual(fields['entity']['fields']['value']['kind'],'uri')
        self.assertEqual(packet['relations'],[])

    def test_unselected_pin_and_source_refused(self):
        for source,pin in [('cofid','bad'),('fdc','bad'),('businesses','bad')]:
            with self.assertRaises(ValueError):v2.normalize(source,{},adapter_commit=pin)
