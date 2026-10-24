"""Generated fixtures only; SQLite stays in memory, no corpus/cache reads."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gold_builder', ROOT / 'gold_builder.py')
gold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gold)
PIN = 'a' * 64
PUBLIC = {'visibility': 'public'}


def fixture():
    packet = {'schema_version': 'offmenu.gold-input/1', 'data_class': 'synthetic',
              'watermark': {'eligible_manifest_sha256': PIN, 'domains': []},
              'common': {'schemaVersion': 'offmenu-common/1', 'resources': [], 'assertions': [], 'relations': [], 'citations': [], 'translations': []},
              'occurrences': [], 'metrics': [], 'observations': [], 'english_bindings': []}
    q = {'schema_version': 'offmenu.gold-qualification/1', 'policy_sha256': PIN, 'records': [], 'supports': [], 'cache_entries': [], 'comparisons': []}
    def support(kind, identity, scope, cids=('cite',)):
        for cid in cids:
            q['supports'].append({'target_kind': kind, 'target_id': identity, 'citation_id': cid, 'support_scope': scope, 'evidence_sha256': PIN})
    for domain in gold.DOMAINS:
        packet['watermark']['domains'].append({'domain': domain, 'snapshot_id': 'generated-'+domain, 'committed_watermark': 'generated-1', 'manifest_sha256': PIN})
    for cid in ('cite', 'cite2'):
        packet['common']['citations'].append({'id': cid, 'sourceId': 'generated', 'originalRecordId': cid, 'originalUrl': 'https://example.invalid/'+cid, 'license': 'generated fixture', 'attribution': 'synthetic', 'scope': PUBLIC})
    for identity, domain, typ in [('recipe','recipes','recipe'),('mention','ingredients','ingredient-mention'),('canonical','ingredients','ingredient'),('product','barcodes','barcode-product'),('supplier','suppliers','supplier'),('recall','dietary','recall')]:
        text = {'kind': 'text', 'id': identity+'-text', 'language': 'en', 'value': identity, 'sourceTextSha256': hashlib.sha256(identity.encode()).hexdigest(), 'status': 'source-asserted', 'citationIds': ['cite']}
        packet['common']['resources'].append({'id': identity, 'type': typ, 'identityStatus': 'source-asserted', 'names': [text], 'citationIds': ['cite'], 'scope': PUBLIC})
        occurrence = {'occurrence_id': identity+'-occ', 'domain': domain, 'source_key': 'generated-source', 'source_version': 'generated-v1', 'record_id': identity, 'content_sha256': PIN, 'normalized_artifact_sha256': PIN, 'committed_watermark': 'generated-1', 'resource_ids': [identity], 'citation_ids': ['cite']}
        packet['occurrences'].append(occurrence)
        q['records'].append({**{k: occurrence[k] for k in ('occurrence_id','content_sha256','normalized_artifact_sha256','committed_watermark')}, 'operation_evidence_sha256': PIN, 'review_evidence_sha256': PIN, 'rights_state': 'permitted', 'reason': 'generated only'})
        support('resource', identity, 'record'); support('text', identity+'-text', 'field')
    for identity, subject, predicate, obj in [('mentions','recipe','mentions','mention'),('maps','mention','canonical_ingredient','canonical'),('represents','product','represents','canonical'),('maker','product','manufacturer','supplier')]:
        packet['common']['relations'].append({'id': identity, 'subjectId': subject, 'predicateId': predicate, 'objectId': obj, 'status': 'source-asserted', 'citationIds': ['cite'], 'scope': PUBLIC, 'sourcePath': '/generated/'+identity})
        support('relation', identity, 'relationship')
    packet['metrics'] = [{'metric_id': 'protein', 'name_en': 'Protein', 'dimension': 'mass', 'canonical_unit_id': 'g', 'citation_ids': ['cite']}]
    support('metric', 'protein', 'definition')
    contexts = [{'country':'A','cut':'whole','fat':'standard','preparation':'none','raw_cooked':'raw','basis':'100 g','source_date':'2026-01-01','method':'generated','uncertainty':'generated exact'}, {'country':'B','raw_cooked':'cooked','basis':'portion, mass unknown'}, {'country':'A','cut':'whole','fat':'standard','preparation':'none','raw_cooked':'raw','basis':'100 g','source_date':'2026-01-01','method':'generated','uncertainty':'generated exact'}]
    for i, context in enumerate(contexts):
        aid = 'protein-'+str(i)
        packet['common']['assertions'].append({'id': aid, 'subjectId': 'product', 'propertyId': 'protein', 'value': {'kind':'quantity','value':10+i,'unitId':'g','dimension':'mass','sourceValue':str(10+i),'sourceUnit':'g','qualifiers':[], 'basis': {'kind':'quantity','value':100 if i!=1 else None,'unitId':'g' if i!=1 else None,'dimension':'mass','sourceValue':'100' if i!=1 else 'portion','sourceUnit':'g' if i!=1 else None,'qualifiers':[]}}, 'status':'source-asserted','citationIds':['cite','cite2'],'sourcePath':'/generated/protein','scope':PUBLIC})
        support('assertion', aid, 'field', ('cite','cite2'))
        packet['observations'].append({'observation_id':'obs'+str(i),'assertion_id':aid,'metric_id':'protein','kind':'observed','context':context,'comparable':None,'input_assertion_ids':[],'cache_request_key':None})
    q['packet_sha256'] = gold.digest(packet)
    return packet, q


def build(packet, q):
    q['packet_sha256'] = gold.digest(packet)
    return gold.build_gold_slice(packet, qualifications=q)


def sqlite_proposal(proposal):
    db = sqlite3.connect(':memory:')
    db.executescript((ROOT/'gold.schema.sql').read_text())
    for table in gold.INSERT_ORDER:
        cols = gold.TABLE_COLUMNS[table]
        for row in proposal['rows'][table]:
            db.execute('INSERT INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')', [row[k] for k in cols])
    return db


def product_subset_fixture():
    p,q=fixture()
    p['watermark']['domains']=[x for x in p['watermark']['domains'] if x['domain'] in ('barcodes','ingredients')]
    p['common']['resources']=[x for x in p['common']['resources'] if x['id'] in ('product','canonical')]
    p['occurrences']=[x for x in p['occurrences'] if x['resource_ids'][0] in ('product','canonical')]
    p['common']['relations']=[x for x in p['common']['relations'] if x['id']=='represents']
    p['common']['assertions']=p['common']['assertions'][:1]
    p['observations']=p['observations'][:1]
    p['observations'][0]['context']['basis']=copy.deepcopy(p['common']['assertions'][0]['value']['basis'])
    identifier={'id':'product-code','subjectId':'product','propertyId':'generated:source-code',
                'value':{'kind':'identifier','value':'generated-product-123'},'status':'source-asserted',
                'citationIds':['cite'],'sourcePath':'/generated/code','scope':PUBLIC}
    p['common']['assertions'].append(identifier)
    q['supports'].append({'target_kind':'assertion','target_id':'product-code','citation_id':'cite',
                          'support_scope':'field','evidence_sha256':PIN})
    q['product_identifier_bindings']=[{'resource_id':'product','assertion_id':'product-code','evidence_sha256':PIN}]
    q['observation_basis_bindings']=[{'observation_id':'obs0','basis':copy.deepcopy(p['observations'][0]['context']['basis']),'evidence_sha256':PIN}]
    q['packet_sha256']=gold.digest(p)
    return p,q


class ProductSourceSubsetTests(unittest.TestCase):
    def build(self,p,q):
        q['packet_sha256']=gold.digest(p)
        return gold.build_product_source_subset(p,qualifications=q)

    def test_identifier_lookup_does_not_claim_recipe_chain_or_actual_admission(self):
        p,q=product_subset_fixture();before=copy.deepcopy((p,q))
        default=gold.build_gold_slice(p,qualifications=q)
        self.assertTrue(all(e['state']=='held' for e in default['rows']['gold_entities']))
        r=self.build(p,q)
        self.assertEqual({'product','canonical'},{e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
        self.assertEqual('verified',r['rows']['gold_observations'][0]['state'])
        self.assertEqual('product-source-subset/1',r['admission_profile'])
        self.assertEqual('product-source-subset/1',json.loads(r['rows']['gold_runs'][0]['watermark_json'])['admission_profile'])
        self.assertNotEqual(default['slice_id'],r['slice_id'])
        self.assertEqual(0,r['metrics']['connectivity']['core_chain_seeds'])
        self.assertEqual(1,r['metrics']['connectivity']['source_product_seeds'])
        self.assertEqual(0,r['metrics']['actual_gold_admitted'])
        self.assertEqual(before,(p,q))
        with sqlite_proposal(r) as db:self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

    def test_identifier_only_lookup_without_nutrition_or_class(self):
        p,q=product_subset_fixture()
        p['common']['resources']=[r for r in p['common']['resources'] if r['id']=='product']
        p['occurrences']=[o for o in p['occurrences'] if o['resource_ids']==['product']]
        p['common']['relations']=[];p['common']['assertions']=[a for a in p['common']['assertions'] if a['id']=='product-code']
        p['metrics']=[];p['observations']=[];q['observation_basis_bindings']=[]
        r=self.build(p,q)
        self.assertEqual('verified',r['rows']['gold_entities'][0]['state'])

    def test_unqualified_or_misbound_identifier_cannot_seed_lookup(self):
        for failure in ('no-selection','wrong-subject','no-evidence','missing-support','wrong-kind','empty-code','rights','english'):
            with self.subTest(failure=failure):
                p,q=product_subset_fixture();a=p['common']['assertions'][-1]
                if failure=='no-selection':q['product_identifier_bindings']=[]
                elif failure=='wrong-subject':q['product_identifier_bindings'][0]['resource_id']='canonical'
                elif failure=='no-evidence':q['product_identifier_bindings'][0]['evidence_sha256']=None
                elif failure=='missing-support':q['supports']=[s for s in q['supports'] if s['target_id']!='product-code']
                elif failure=='wrong-kind':a['value']={'kind':'expression','syntax':'generated','value':'123'}
                elif failure=='empty-code':a['value']['value']=' '
                elif failure=='rights':next(x for x in q['records'] if x['occurrence_id']=='product-occ')['rights_state']='held'
                else:next(r for r in p['common']['resources'] if r['id']=='product')['names'][0]['language']='es'
                r=self.build(p,q)
                self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_entities']))
                self.assertEqual(0,r['metrics']['connectivity']['source_product_seeds'])

    def test_shared_class_cannot_revive_an_unidentified_product(self):
        p,q=product_subset_fixture()
        GoldBuilderTests.add_subset_resource(self,p,q,'product','unidentified')
        p['common']['relations'].append({'id':'unidentified-represents','subjectId':'unidentified','predicateId':'represents','objectId':'canonical','citationIds':['cite'],'scope':PUBLIC})
        q['supports'].append({'target_kind':'relation','target_id':'unidentified-represents','citation_id':'cite','support_scope':'relationship','evidence_sha256':PIN})
        r=self.build(p,q)
        self.assertEqual({'product','canonical'},{e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
        self.assertEqual('held',next(e['state'] for e in r['rows']['gold_edges'] if e['relation_id']=='unidentified-represents'))
        self.assertEqual('held',next(o['state'] for o in r['rows']['gold_occurrences'] if o['occurrence_id']=='unidentified-occ'))

    def test_class_and_relationship_need_their_own_qualification(self):
        for failure in ('class-rights','relationship-support'):
            p,q=product_subset_fixture()
            if failure=='class-rights':next(x for x in q['records'] if x['occurrence_id']=='canonical-occ')['rights_state']='held'
            else:q['supports']=[s for s in q['supports'] if s['target_kind']!='relation']
            r=self.build(p,q)
            self.assertEqual({'product'},{e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
            self.assertEqual('held',r['rows']['gold_edges'][0]['state'])

    def test_source_numeric_values_require_bound_basis_and_product_subject(self):
        for failure in ('missing','different','no-evidence','unknown-unit','wrong-subject','unknown-value'):
            with self.subTest(failure=failure):
                p,q=product_subset_fixture();obs=p['observations'][0];value=p['common']['assertions'][0]['value']
                if failure=='missing':q['observation_basis_bindings']=[]
                elif failure=='different':q['observation_basis_bindings'][0]['basis']['value']=1
                elif failure=='no-evidence':q['observation_basis_bindings'][0]['evidence_sha256']=None
                elif failure=='unknown-unit':value['basis']['unitId']=None
                elif failure=='wrong-subject':p['common']['assertions'][0]['subjectId']='canonical'
                else:value['basis']['value']=None
                r=self.build(p,q)
                self.assertEqual('held',r['rows']['gold_observations'][0]['state'])
                self.assertEqual({'product','canonical'},{e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})

    def test_profile_rejects_other_domains_relations_comparisons_and_private_data(self):
        for failure in ('domain','resource','relation','comparison','private'):
            with self.subTest(failure=failure):
                p,q=product_subset_fixture()
                if failure=='domain':p['watermark']['domains'][0]['domain']='recipes'
                elif failure=='resource':p['common']['resources'][0]['type']='supplier'
                elif failure=='relation':p['common']['relations'][0]['predicateId']='contains'
                elif failure=='comparison':q['comparisons']=[{'observation_ids':['obs0']}]
                else:p['common']['resources'][0]['scope']={'visibility':'private','ownerId':'generated'}
                with self.assertRaises(ValueError):self.build(p,q)

    def test_packet_cannot_select_the_product_profile(self):
        p,q=product_subset_fixture();p['product_source_only']=True
        q['packet_sha256']=gold.digest(p)
        r=gold.build_gold_slice(p,qualifications=q)
        self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_entities']))
        self.assertNotIn('admission_profile',r)


class GoldBuilderTests(unittest.TestCase):
    def add_subset_resource(self, packet, q, source_id, identity):
        resource = copy.deepcopy(next(x for x in packet['common']['resources'] if x['id'] == source_id))
        resource['id'] = identity
        resource['names'][0].update(id=identity+'-text', value=identity,
                                   sourceTextSha256=hashlib.sha256(identity.encode()).hexdigest())
        packet['common']['resources'].append(resource)
        occurrence = copy.deepcopy(next(x for x in packet['occurrences'] if x['resource_ids'] == [source_id]))
        original_occurrence = occurrence['occurrence_id']
        occurrence.update(occurrence_id=identity+'-occ', record_id=identity, resource_ids=[identity])
        packet['occurrences'].append(occurrence)
        rights = copy.deepcopy(next(x for x in q['records'] if x['occurrence_id'] == original_occurrence))
        rights['occurrence_id'] = identity+'-occ'
        q['records'].append(rights)
        for kind, target, scope in [('resource', identity, 'record'), ('text', identity+'-text', 'field')]:
            q['supports'].append({'target_kind':kind,'target_id':target,'citation_id':'cite',
                                  'support_scope':scope,'evidence_sha256':PIN})

    def add_subset_edge(self, packet, q, identity, subject, obj, *, supported=True):
        packet['common']['relations'].append({'id':identity,'subjectId':subject,'predicateId':'mentions',
            'objectId':obj,'status':'source-asserted','citationIds':['cite'],'scope':PUBLIC,
            'sourcePath':'/generated/'+identity})
        if supported:
            q['supports'].append({'target_kind':'relation','target_id':identity,'citation_id':'cite',
                                  'support_scope':'relationship','evidence_sha256':PIN})

    def source_subset(self):
        packet, q = fixture()
        packet['watermark']['domains'] = [x for x in packet['watermark']['domains'] if x['domain'] in ('recipes','ingredients')]
        packet['common']['resources'] = [x for x in packet['common']['resources'] if x['id'] in ('recipe','mention')]
        packet['occurrences'] = [x for x in packet['occurrences'] if x['resource_ids'][0] in ('recipe','mention')]
        packet['common']['relations'] = [x for x in packet['common']['relations'] if x['id']=='mentions']
        packet['common']['assertions'] = []; packet['observations'] = []; packet['metrics'] = []
        q['packet_sha256'] = gold.digest(packet)
        return packet, q

    def test_source_subset_preserves_facts_without_claiming_application_chain(self):
        p,q=self.source_subset()
        default=gold.build_gold_slice(p,qualifications=q)
        self.assertTrue(all(x['state']=='held' for x in default['rows']['gold_entities']))
        result=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertEqual({'recipe','mention'},{x['resource_id'] for x in result['rows']['gold_entities'] if x['state']=='verified'})
        self.assertEqual(1,len([x for x in result['rows']['gold_edges'] if x['state']=='verified']))
        self.assertEqual('recipe-source-subset/1',result['admission_profile'])
        self.assertNotEqual(default['slice_id'],result['slice_id'])
        self.assertEqual('recipe-source-subset/1',json.loads(result['rows']['gold_runs'][0]['watermark_json'])['admission_profile'])
        self.assertEqual(0,result['metrics']['connectivity']['core_chain_seeds'])
        self.assertEqual(1,result['metrics']['connectivity']['source_recipe_seeds'])
        self.assertEqual(0,result['metrics']['actual_gold_admitted'])
        with sqlite_proposal(result) as db:self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

    def test_source_subset_still_requires_own_rights_english_and_relationship_support(self):
        for failure in ('rights','english','relation'):
            with self.subTest(failure=failure):
                p,q=self.source_subset()
                if failure=='rights':next(x for x in q['records'] if x['occurrence_id']=='mention-occ')['rights_state']='held'
                elif failure=='english':next(x for x in p['common']['resources'] if x['id']=='mention')['names'][0]['language']='es'
                else:q['supports']=[x for x in q['supports'] if x['target_kind']!='relation']
                q['packet_sha256']=gold.digest(p)
                r=gold.build_recipe_source_subset(p,qualifications=q)
                self.assertTrue(all(x['state']=='held' for x in r['rows']['gold_entities']))
                self.assertEqual(0,r['metrics']['connectivity']['source_recipe_seeds'])

    def test_source_subset_rejects_full_network_inputs_and_private_data(self):
        p,q=fixture()
        with self.assertRaises(ValueError):gold.build_recipe_source_subset(p,qualifications=q)
        p,q=self.source_subset();p['common']['resources'][0]['scope']={'visibility':'private','ownerId':'generated'}
        q['packet_sha256']=gold.digest(p)
        with self.assertRaises(ValueError):gold.build_recipe_source_subset(p,qualifications=q)
        p,q=self.source_subset();p['common']['resources'][1]['type']='ingredient';q['packet_sha256']=gold.digest(p)
        with self.assertRaises(ValueError):gold.build_recipe_source_subset(p,qualifications=q)

    def test_source_subset_cannot_hide_an_unqualified_declared_branch(self):
        p,q=self.source_subset();bad=copy.deepcopy(p['common']['resources'][1]);bad['id']='unsupported-mention'
        bad['names'][0]['id']='unsupported-name';p['common']['resources'].append(bad)
        p['common']['relations'].append({'id':'unsupported-edge','subjectId':'recipe','predicateId':'mentions','objectId':'unsupported-mention','citationIds':['cite'],'scope':PUBLIC})
        q['packet_sha256']=gold.digest(p)
        r=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertEqual(0,r['metrics']['connectivity']['source_recipe_seeds'])
        self.assertTrue(all(x['state']=='held' for x in r['rows']['gold_entities']))

    def test_source_subset_shared_mention_cannot_revive_incomplete_recipe(self):
        p,q=self.source_subset()
        self.add_subset_resource(p,q,'recipe','incomplete')
        self.add_subset_edge(p,q,'shared','incomplete','mention')
        self.add_subset_edge(p,q,'missing','incomplete','missing-mention',supported=False)
        q['packet_sha256']=gold.digest(p)
        r=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertEqual({'recipe','mention'},{e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
        self.assertEqual({'mentions'},{e['relation_id'] for e in r['rows']['gold_edges'] if e['state']=='verified'})
        self.assertEqual('held',next(e['state'] for e in r['rows']['gold_occurrences'] if e['occurrence_id']=='incomplete-occ'))
        self.assertEqual('held',next(t['state'] for t in r['rows']['gold_texts'] if t['source_text_id']=='incomplete-text'))
        self.assertEqual(1,r['metrics']['connectivity']['source_recipe_seeds'])
        self.assertEqual(2,r['metrics']['connectivity']['reachable_entities'])

    def test_source_subset_shared_cycle_preserves_only_complete_siblings(self):
        p,q=self.source_subset()
        self.add_subset_resource(p,q,'recipe','sibling')
        self.add_subset_resource(p,q,'mention','sibling-mention')
        self.add_subset_edge(p,q,'sibling-edge','sibling','sibling-mention')
        for identity in ['incomplete-a','incomplete-b']:
            self.add_subset_resource(p,q,'recipe',identity)
            self.add_subset_edge(p,q,identity+'-left',identity,'mention')
            self.add_subset_edge(p,q,identity+'-right',identity,'sibling-mention')
            self.add_subset_edge(p,q,identity+'-missing',identity,'missing-mention',supported=False)
        q['packet_sha256']=gold.digest(p)
        r=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertEqual({'recipe','mention','sibling','sibling-mention'},
                         {e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
        self.assertEqual({'mentions','sibling-edge'},
                         {e['relation_id'] for e in r['rows']['gold_edges'] if e['state']=='verified'})
        self.assertEqual(2,r['metrics']['connectivity']['source_recipe_seeds'])
        with sqlite_proposal(r) as db:self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

    def test_source_subset_cycle_without_complete_recipe_stays_held(self):
        p,q=self.source_subset()
        self.add_subset_resource(p,q,'recipe','second')
        self.add_subset_resource(p,q,'mention','second-mention')
        self.add_subset_edge(p,q,'first-right','recipe','second-mention')
        self.add_subset_edge(p,q,'second-left','second','mention')
        self.add_subset_edge(p,q,'second-right','second','second-mention')
        for identity in ['recipe','second']:
            self.add_subset_edge(p,q,identity+'-missing',identity,'missing-mention',supported=False)
        q['packet_sha256']=gold.digest(p)
        r=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_entities']))
        self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_edges']))
        self.assertEqual(0,r['metrics']['connectivity']['reachable_entities'])

    def test_source_subset_recipe_chain_cannot_inherit_complete_sibling_qualification(self):
        p,q=self.source_subset()
        for identity in ['incomplete','sibling']:
            self.add_subset_resource(p,q,'recipe',identity)
            self.add_subset_edge(p,q,identity+'-shared',identity,'mention')
        self.add_subset_edge(p,q,'recipe-chain','incomplete','sibling')
        q['packet_sha256']=gold.digest(p)
        r=gold.build_recipe_source_subset(p,qualifications=q)
        self.assertEqual({'recipe','mention','sibling'},
                         {e['resource_id'] for e in r['rows']['gold_entities'] if e['state']=='verified'})
        self.assertEqual({'mentions','sibling-shared'},
                         {e['relation_id'] for e in r['rows']['gold_edges'] if e['state']=='verified'})

    def test_source_data_cannot_select_subset_admission_profile(self):
        p,q=self.source_subset();p['admission_profile']='recipe-source-subset/1';q['packet_sha256']=gold.digest(p)
        result=gold.build_gold_slice(p,qualifications=q)
        self.assertTrue(all(x['state']=='held' for x in result['rows']['gold_entities']))
        self.assertNotIn('admission_profile',result)

    def test_joined_recipe_canonical_product_nutrition_many_citations(self):
        p,q=fixture(); result=build(p,q)
        with sqlite_proposal(result) as db:
            query = '''SELECT mention.object_id, canonical.object_id, product.subject_id, o.observation_id, s.citation_id
            FROM gold_edges mention
            JOIN gold_edges canonical ON canonical.subject_id=mention.object_id AND canonical.predicate_id='canonical_ingredient'
            JOIN gold_edges product ON product.object_id=canonical.object_id AND product.predicate_id='represents'
            JOIN gold_observations o ON o.entity_id=product.subject_id
            JOIN gold_claims c ON c.claim_id=o.claim_id
            JOIN gold_support s ON s.target_kind='assertion' AND s.target_id=c.assertion_id
            WHERE mention.predicate_id='mentions' AND mention.state='verified' AND canonical.state='verified' AND product.state='verified' AND o.state='verified' '''
            self.assertEqual(6,len(db.execute(query).fetchall()))
            self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(1,db.execute("SELECT count(*) FROM gold_edges WHERE predicate_id='manufacturer'").fetchone()[0])
        self.assertEqual(0,result['metrics']['actual_gold_admitted'])
        self.assertEqual('NOT_CHECKED',result['metrics']['recall_coverage'])
    def test_missing_rights_holds_endpoints(self):
        p,q=fixture();q['records'][0]['rights_state']='held'
        r=build(p,q);self.assertTrue(any(x['state']=='held' for x in r['rows']['gold_edges']))
    def test_record_citation_cannot_support_relationship(self):
        p,q=fixture();next(s for s in q['supports'] if s['target_kind']=='relation')['support_scope']='record'
        r=build(p,q);self.assertTrue(r['rows']['gold_unbound_support'])
    def test_missing_citation_retained_unbound(self):
        p,q=fixture();p['common']['assertions'][0]['citationIds'].append('missing')
        r=build(p,q);self.assertTrue(any(x['citation_id']=='missing' for x in r['rows']['gold_unbound_support']))
    def test_context_alternatives_original_values_no_average(self):
        p,q=fixture();r=build(p,q);s=gold.select_observations(r,metric_id='protein',requested_context={'country':'A','raw_cooked':'raw'})
        self.assertEqual(3,len(s['alternatives']));self.assertEqual(2,len(s['preferred_ids']));self.assertEqual('none',s['aggregation'])
        self.assertEqual({'10','11','12'},{json.loads(x['original_json'])['sourceValue'] for x in r['rows']['gold_observations']})
    def test_reviewed_contradiction_not_automatic(self):
        p,q=fixture();q['comparisons']=[{'observation_ids':['obs0','obs2'],'disposition':'contradiction','reason':'generated review','evidence_sha256':PIN}]
        r=build(p,q);self.assertEqual(1,len(r['rows']['gold_comparisons']))
        q['comparisons'][0]['observation_ids']=['obs0','obs1']
        with self.assertRaises(ValueError):build(p,q)
    def test_conversion_and_ai_held(self):
        p,q=fixture();p['observations'][0]['comparable']={'value_lexeme':'0.01','unit_id':'kg','basis':'100 g','rule_id':'unqualified'};p['observations'][1]['kind']='AI_inferred'
        r=build(p,q);self.assertEqual(2,sum(x['state']=='held' for x in r['rows']['gold_observations']))
    def test_nonenglish_not_source_english(self):
        p,q=fixture();p['common']['resources'][0]['names'][0]['language']='es'
        r=build(p,q);self.assertTrue(any(x['english_text'] is None and x['state']=='held' for x in r['rows']['gold_texts']))
    def test_ambiguous_identity_held_no_merge(self):
        p,q=fixture();o=copy.deepcopy(p['occurrences'][0]);o.update(occurrence_id='other',source_key='other-source');p['occurrences'].append(o)
        r=build(p,q);self.assertFalse(any(x['resource_id']=='recipe' for x in r['rows']['gold_entities']))
    def test_private_rejected(self):
        p,q=fixture();p['common']['resources'][0]['scope']={'visibility':'private','ownerId':'synthetic'}
        with self.assertRaises(ValueError):build(p,q)
    def test_watermark_and_qualification_binding(self):
        p,q=fixture();q['packet_sha256']='b'*64
        with self.assertRaises(ValueError):gold.build_gold_slice(p,qualifications=q)
        p['occurrences'][0]['committed_watermark']='wrong'
        with self.assertRaises(ValueError):build(p,q)
    def test_deterministic_pure_and_bounded(self):
        p,q=fixture();before=copy.deepcopy((p,q));self.assertEqual(build(p,q),build(p,q));self.assertEqual(before,(p,q))
        p['extra']='x'*4194304
        with self.assertRaises(ValueError):build(p,q)
        a=[];b=a
        for _ in range(34):n=[];b.append(n);b=n
        with self.assertRaises(ValueError):gold.digest(a)
    def test_foreign_keys_reject_orphan(self):
        p,q=fixture()
        with sqlite_proposal(build(p,q)) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("INSERT INTO gold_entity_occurrences VALUES('missing','missing')")
    def test_exact_rational_conversion_preserves_basis_and_original(self):
        p,q=fixture();original=p['common']['assertions'][0]['value']
        p['metrics'][0]['canonical_unit_id']='mg'
        p['observations'][0]['comparable']={'value_lexeme':'10000','unit_id':'mg','basis':copy.deepcopy(original['basis']),'rule_id':'g-mg'}
        q['unit_rules']=[{'rule_id':'g-mg','from_unit_id':'g','to_unit_id':'mg','dimension':'mass','numerator':1000,'denominator':1,'evidence_sha256':PIN}]
        r=build(p,q);self.assertEqual('verified',next(x for x in r['rows']['gold_observations'] if x['observation_id']=='obs0')['state'])
        p['observations'][0]['comparable']['basis']['value']=1
        r=build(p,q);self.assertEqual('held',next(x for x in r['rows']['gold_observations'] if x['observation_id']=='obs0')['state'])
    def test_typed_endpoint_rejects_product_as_canonical_food(self):
        p,q=fixture();p['common']['relations'][1]['objectId']='product'
        r=build(p,q);self.assertEqual('held',next(x for x in r['rows']['gold_edges'] if x['relation_id']=='maps')['state'])
    def test_unknown_context_cannot_be_reviewed_contradiction(self):
        p,q=fixture();p['observations'][2]['context']=copy.deepcopy(p['observations'][1]['context'])
        q['comparisons']=[{'observation_ids':['obs1','obs2'],'disposition':'contradiction','reason':'unknown context','evidence_sha256':PIN}]
        with self.assertRaises(ValueError):build(p,q)
    def test_citation_only_island_held_and_missing_chain_not_complete(self):
        p,q=fixture();r=build(p,q)
        self.assertEqual('held',next(e for e in r['rows']['gold_entities'] if e['resource_id']=='recall')['state'])
        self.assertEqual(1,r['metrics']['connectivity']['held_islands'])
        p['common']['relations']=[e for e in p['common']['relations'] if e['predicateId']!='canonical_ingredient']
        r=build(p,q)
        self.assertEqual(0,r['metrics']['connectivity']['core_chain_seeds'])
        self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_entities']))
        self.assertTrue(all(e['state']=='held' for e in r['rows']['gold_observations']))
    def test_unmapped_mention_branch_held_without_disabling_mapped_sibling(self):
        p,q=fixture()
        resource=copy.deepcopy(p['common']['resources'][1]);resource['id']='second-mention';resource['names'][0]['id']='second-text'
        p['common']['resources'].append(resource)
        occurrence=copy.deepcopy(p['occurrences'][1]);occurrence.update(occurrence_id='second-occ',record_id='second-row',resource_ids=['second-mention']);p['occurrences'].append(occurrence)
        record=copy.deepcopy(q['records'][1]);record['occurrence_id']='second-occ';q['records'].append(record)
        for kind,identity,scope in [('resource','second-mention','record'),('text','second-text','field'),('relation','second-edge','relationship')]:
            q['supports'].append({'target_kind':kind,'target_id':identity,'citation_id':'cite','support_scope':scope,'evidence_sha256':PIN})
        edge=copy.deepcopy(p['common']['relations'][0]);edge.update(id='second-edge',objectId='second-mention');p['common']['relations'].append(edge)
        r=build(p,q)
        self.assertEqual('held',next(e for e in r['rows']['gold_entities'] if e['resource_id']=='second-mention')['state'])
        self.assertEqual('held',next(e for e in r['rows']['gold_occurrences'] if e['occurrence_id']=='second-occ')['state'])
        self.assertEqual('held',next(e for e in r['rows']['gold_edges'] if e['relation_id']=='second-edge')['state'])
        self.assertEqual(1,r['metrics']['connectivity']['missing_required_associations'])
        self.assertEqual('verified',next(e for e in r['rows']['gold_entities'] if e['resource_id']=='mention')['state'])
        self.assertTrue(all(o['state']=='verified' for o in r['rows']['gold_observations']))
        mapped=copy.deepcopy(p['common']['relations'][1]);mapped.update(id='second-map',subjectId='second-mention');p['common']['relations'].append(mapped)
        q['supports'].append({'target_kind':'relation','target_id':'second-map','citation_id':'cite','support_scope':'relationship','evidence_sha256':PIN})
        r=build(p,q);self.assertEqual('verified',next(e for e in r['rows']['gold_entities'] if e['resource_id']=='second-mention')['state'])
        self.assertEqual(0,r['metrics']['connectivity']['missing_required_associations'])
    def test_wrong_property_and_dimension_cannot_seed_chain(self):
        for change in ('property','dimension'):
            p,q=fixture()
            for a in p['common']['assertions']:
                if change=='property':a['propertyId']='sodium'
                else:a['value'].update(dimension='energy',unitId='kJ',sourceUnit='kJ')
            r=build(p,q)
            self.assertTrue(all(o['state']=='held' for o in r['rows']['gold_observations']))
            self.assertEqual(0,r['metrics']['connectivity']['core_chain_seeds'])
            with sqlite_proposal(r) as db:self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
    def test_evidenced_property_mapping_and_valid_native_units(self):
        p,q=fixture()
        for a in p['common']['assertions']:
            a['propertyId']='source-protein';a['value'].update(unitId='mg',sourceUnit='mg')
        q['metric_bindings']=[{'property_id':'source-protein','metric_id':'protein','evidence_sha256':PIN}]
        r=build(p,q);self.assertTrue(all(o['state']=='verified' for o in r['rows']['gold_observations']))
        self.assertTrue(all(json.loads(o['original_json'])['unitId']=='mg' and json.loads(o['comparable_json']) is None for o in r['rows']['gold_observations']))
        q['metric_bindings'][0]['evidence_sha256']='unqualified'
        r=build(p,q);self.assertTrue(all(o['state']=='held' for o in r['rows']['gold_observations']))
    def test_unused_and_held_only_citations_retained_with_disposition(self):
        for held_only in (False,True):
            p,q=fixture();citation=copy.deepcopy(p['common']['citations'][0]);citation.update(id='unused-citation',originalRecordId='unused-row',originalUrl='https://example.invalid/unused');p['common']['citations'].append(citation)
            if held_only:
                resource=next(e for e in p['common']['resources'] if e['id']=='recall')
                resource['citationIds']=['unused-citation'];resource['names'][0]['citationIds']=['unused-citation']
                for kind,identity,scope in [('resource','recall','record'),('text','recall-text','field')]:
                    q['supports'].append({'target_kind':kind,'target_id':identity,'citation_id':'unused-citation','support_scope':scope,'evidence_sha256':PIN})
            r=build(p,q)
            self.assertEqual({'total':3,'usable':2,'held':1},r['metrics']['citations'])
            self.assertTrue(any(h['target_kind']=='citation' and h['target_id']=='unused-citation' and 'retained provenance' in h['reason'] for h in r['rows']['gold_holds']))
            self.assertEqual(citation,json.loads(next(c['payload_json'] for c in r['rows']['gold_citations'] if c['citation_id']=='unused-citation')))
            self.assertTrue(all(o['state']=='verified' for o in r['rows']['gold_observations']))
            with sqlite_proposal(r) as db:self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
    def test_recall_missing_scope_is_held(self):
        p,q=fixture();p['common']['relations'].append({'id':'recall-link','subjectId':'recall','predicateId':'recall_applies_to','objectId':'product','citationIds':['cite'],'scope':PUBLIC,'sourcePath':'/generated/recall','status':'source-asserted'})
        q['supports'].append({'target_kind':'relation','target_id':'recall-link','citation_id':'cite','support_scope':'relationship','evidence_sha256':PIN})
        r=build(p,q);self.assertEqual('held',next(x for x in r['rows']['gold_edges'] if x['relation_id']=='recall-link')['state'])

if __name__=='__main__':unittest.main()
