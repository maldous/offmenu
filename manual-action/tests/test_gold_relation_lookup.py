"""Generated alternative graph; no retained corpus or actual GOLD is opened."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import test_gold_builder as fixtures
import gold_relation_lookup as lookup


def alternative_fixture():
    p, q = fixtures.fixture()
    add = fixtures.GoldBuilderTests.add_subset_resource
    for old, new in [('canonical', 'turbinado'), ('product', 'brown-product'),
                     ('mention', 'water-mention')]:
        add(None, p, q, old, new)
    source = dict(recipeId='recipe', mentionId='mention', sourceKey='generated-source',
                  sourceVersion='generated-v1', recordId='recipe', contentSha256=fixtures.PIN)
    white = next(e for e in p['common']['relations'] if e['id'] == 'maps')
    white['condition'] = dict(kind='selected-alternative', groupId='sugar', branchId='white', sourceScope=source)
    brown = copy.deepcopy(white)
    brown.update(id='brown-map', objectId='turbinado')
    brown['condition']['branchId'] = 'turbinado'
    edges = [brown,
             dict(id='brown-represents', subjectId='brown-product', predicateId='represents', objectId='turbinado'),
             dict(id='water-mentions', subjectId='recipe', predicateId='mentions', objectId='water-mention'),
             dict(id='water-map', subjectId='water-mention', predicateId='canonical_ingredient', objectId='canonical')]
    for e in edges:
        e.update(status='source-asserted', citationIds=['cite'], scope=fixtures.PUBLIC, sourcePath='/generated/'+e['id'])
        p['common']['relations'].append(e)
        q['supports'].append(dict(target_kind='relation', target_id=e['id'], citation_id='cite', support_scope='relationship', evidence_sha256=fixtures.PIN))
    # Retain the expression as source text, never parse it into a selected branch.
    next(o for o in p['occurrences'] if o['occurrence_id']=='mention-occ')['original'] = 'white OR turbinado'
    claim = copy.deepcopy(p['common']['assertions'][0])
    claim.update(id='brown-protein', subjectId='brown-product')
    p['common']['assertions'].append(claim)
    obs = copy.deepcopy(p['observations'][0])
    obs.update(observation_id='brown-obs', assertion_id='brown-protein')
    p['observations'].append(obs)
    for cid in claim['citationIds']:
        q['supports'].append(dict(target_kind='assertion', target_id=claim['id'], citation_id=cid, support_scope='field', evidence_sha256=fixtures.PIN))
    return p, q, source


class AlternativeLookupTests(unittest.TestCase):
    def run_lookup(self, p, q, source, branch=None, selections=None):
        proposal = fixtures.build(p, q)
        with fixtures.sqlite_proposal(proposal) as db:
            return lookup.lookup_recipe_products(db, source=source,
                selections=selections if selections is not None else
                ([] if branch is None else [dict(groupId='sugar', branchId=branch, sourceScope=source)]))

    def test_unknown_preserves_unconditional_sibling_and_original(self):
        p,q,s=alternative_fixture()
        r=self.run_lookup(p,q,s)
        self.assertEqual({'water-mention'}, {x['mentionId'] for x in r['paths']})
        self.assertEqual('unknown', r['choices'][0]['status'])
        proposal=fixtures.build(p,q)
        self.assertEqual(2, sum(e['state']=='conditional' for e in proposal['rows']['gold_edges']))
        self.assertIn('white OR turbinado', json.dumps(proposal))
        with fixtures.sqlite_proposal(proposal) as db:
            self.assertEqual(0, db.execute("SELECT count(*) FROM gold_edges WHERE predicate_id='canonical_ingredient' AND state='verified' AND relation_id IN ('maps','brown-map')").fetchone()[0])

    def test_explicit_branch_returns_only_that_branch(self):
        for branch, product in [('white','product'),('turbinado','brown-product')]:
            p,q,s=alternative_fixture();r=self.run_lookup(p,q,s,branch)
            sugar=[x for x in r['paths'] if x['mentionId']=='mention']
            self.assertEqual([product], [x['productId'] for x in sugar])
            self.assertTrue(sugar[0]['relations'][1]['condition'])
            self.assertEqual('selected',r['choices'][0]['status'])

    def test_conditional_only_graph_retains_qualification_without_claiming_selection(self):
        p,q,s=alternative_fixture()
        p['common']['relations']=[e for e in p['common']['relations'] if not e['id'].startswith('water-')]
        proposal=fixtures.build(p,q)
        connectivity=proposal['metrics']['connectivity']
        self.assertEqual(0,connectivity['core_chain_seeds'])
        self.assertEqual(1,connectivity['source_qualified_potential_seeds'])
        self.assertTrue(connectivity['selection_required'])
        self.assertEqual([],self.run_lookup(p,q,s)['paths'])
        self.assertEqual(['brown-product'],[p['productId'] for p in self.run_lookup(p,q,s,'turbinado')['paths']])

    def test_order_independence_and_immutable_inputs(self):
        p,q,s=alternative_fixture();before=copy.deepcopy((p,q))
        first=fixtures.build(p,q)
        # build only refreshes the packet digest in its qualification fixture.
        before[1]['packet_sha256']=q['packet_sha256']
        self.assertEqual(before,(p,q))
        p['common']['relations'].reverse()
        second=fixtures.build(p,q)
        self.assertEqual(first['rows']['gold_edges'],second['rows']['gold_edges'])

    def test_bad_selections_never_fallback(self):
        p,q,s=alternative_fixture(); valid=dict(groupId='sugar',branchId='white',sourceScope=s)
        bad=[[], [dict(valid,branchId='absent')], [valid,valid],
             [valid,dict(valid,branchId='turbinado')], [dict(valid,extra=True)],
             [dict(valid,sourceScope=dict(s,sourceVersion='wrong'))], [dict(valid,branchId=True)]]
        for selections in bad:
            with self.subTest(selections=selections):
                r=self.run_lookup(p,q,s,selections=selections)
                self.assertFalse(any(x['mentionId']=='mention' for x in r['paths']))

    def test_source_mismatch_and_malformed_conditions_fail_closed(self):
        for change in [None, {}, {'kind':'expression'}, 'white',
                       dict(kind='selected-alternative',groupId='sugar',branchId='white',sourceScope={})]:
            p,q,s=alternative_fixture()
            next(e for e in p['common']['relations'] if e['id']=='maps')['condition']=change
            r=self.run_lookup(p,q,s,'turbinado')
            self.assertFalse(any(x['mentionId']=='mention' for x in r['paths']))
        for key in ['recipeId','mentionId','sourceKey','sourceVersion','recordId','contentSha256']:
            p,q,s=alternative_fixture(); wrong=dict(s);wrong[key]='b'*64 if key=='contentSha256' else 'wrong'
            self.assertEqual([],self.run_lookup(p,q,wrong,'white')['paths'])

    def test_missing_condition_and_duplicate_branch_fail_closed(self):
        for failure in ['missing','all-missing','duplicate','scope']:
            p,q,s=alternative_fixture(); e=next(e for e in p['common']['relations'] if e['id']=='brown-map')
            if failure=='missing': del e['condition']
            elif failure=='all-missing':
                for edge in p['common']['relations']: edge.pop('condition',None)
            elif failure=='duplicate': e['condition']['branchId']='white'
            else: e['condition']['sourceScope']['recordId']='wrong'
            self.assertFalse(any(x['mentionId']=='mention' for x in self.run_lookup(p,q,s,'white')['paths']))

    def test_unsupported_branch_does_not_select_other_branch(self):
        p,q,s=alternative_fixture();q['supports']=[x for x in q['supports'] if x['target_id']!='brown-map']
        self.assertFalse(any(x['mentionId']=='mention' for x in self.run_lookup(p,q,s,'turbinado')['paths']))
        self.assertEqual(['product'],[x['productId'] for x in self.run_lookup(p,q,s,'white')['paths'] if x['mentionId']=='mention'])

    def test_sql_rejects_promoting_condition_and_unqualified_endpoints(self):
        p,q,s=alternative_fixture()
        with fixtures.sqlite_proposal(fixtures.build(p,q)) as db:
            for sql in ["UPDATE gold_edges SET state='verified' WHERE relation_id='maps'",
                        "UPDATE gold_edges SET state='verified',payload_json=json_remove(payload_json,'$.condition') WHERE relation_id='maps'",
                        "UPDATE gold_edges SET subject_id=NULL WHERE relation_id='maps'"]:
                with self.assertRaises(sqlite3.IntegrityError): db.execute(sql)

    def test_existing_unconditional_lookup(self):
        p,q=fixtures.fixture();_,_,s=alternative_fixture()
        with fixtures.sqlite_proposal(fixtures.build(p,q)) as db:
            r=lookup.lookup_recipe_products(db,source=s)
            self.assertEqual(['product'],[x['productId'] for x in r['paths']])
            self.assertEqual([],r['choices'])

    def test_schema_accepts_only_typed_canonical_conditions(self):
        import jsonschema
        schema=json.loads((ROOT.parent/'corpus/common-data.schema.json').read_text())
        validator=jsonschema.Draft202012Validator({'$ref':'#/$defs/relation','$defs':schema['$defs']})
        p,q,s=alternative_fixture();edge=next(e for e in p['common']['relations'] if e['id']=='maps')
        validator.validate(edge)
        plain=copy.deepcopy(edge);del plain['condition'];validator.validate(plain)
        for condition in [None,{},'white',dict(edge['condition'],extra=True),
                          dict(edge['condition'],branchId=False),dict(edge['condition'],groupId='  ')]:
            bad=dict(edge,condition=condition)
            self.assertTrue(list(validator.iter_errors(bad)))
        self.assertTrue(list(validator.iter_errors(dict(edge,predicateId='mentions'))))

    def test_cli_is_read_only_and_matches_actual_sql_lookup(self):
        p,q,s=alternative_fixture()
        with tempfile.TemporaryDirectory(prefix='offmenu-generated-alternatives-') as directory:
            path=Path(directory)/'generated.sqlite'
            with fixtures.sqlite_proposal(fixtures.build(p,q)) as db:
                db.commit()
                with sqlite3.connect(path) as target: db.backup(target)
            before=path.read_bytes()
            request=[dict(groupId='sugar',branchId='turbinado',sourceScope=s)]
            run=subprocess.run([sys.executable,'-B',str(ROOT/'gold_relation_lookup.py'),
                '--database',str(path),'--source-json',json.dumps(s),'--selections-json',json.dumps(request)],
                capture_output=True,text=True,check=True)
            r=json.loads(run.stdout)
            self.assertEqual(['brown-product'],[x['productId'] for x in r['paths'] if x['mentionId']=='mention'])
            self.assertEqual(before,path.read_bytes())
            self.assertEqual(['generated.sqlite'],[p.name for p in Path(directory).iterdir()])

    def test_direct_malformed_conditional_rows_never_traverse(self):
        p,q,s=alternative_fixture()
        proposal=fixtures.build(p,q)
        for edge in proposal['rows']['gold_edges']:
            if edge['relation_id']=='maps':
                payload=json.loads(edge['payload_json']);del payload['condition']['branchId']
                edge['payload_json']=json.dumps(payload)
        with fixtures.sqlite_proposal(proposal) as db:
            r=lookup.lookup_recipe_products(db,source=s,selections=[dict(groupId='sugar',branchId='turbinado',sourceScope=s)])
            self.assertFalse(any(x['mentionId']=='mention' for x in r['paths']))

    def test_held_state_cannot_launder_a_conditional_payload(self):
        p,q,s=alternative_fixture()
        with fixtures.sqlite_proposal(fixtures.build(p,q)) as db:
            db.execute("UPDATE gold_edges SET state='held' WHERE relation_id='maps'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE gold_edges SET state='verified',payload_json=json_remove(payload_json,'$.condition') WHERE relation_id='maps'")

    def test_missing_branch_product_or_citation_fails_without_fallback(self):
        for failure in ['rights','citation','endpoint']:
            p,q,s=alternative_fixture()
            if failure=='rights': next(x for x in q['records'] if x['occurrence_id']=='brown-product-occ')['rights_state']='held'
            elif failure=='citation': q['supports']=[x for x in q['supports'] if x['target_id']!='brown-represents']
            else: next(x for x in p['common']['relations'] if x['id']=='brown-map')['objectId']='absent'
            self.assertFalse(any(x['mentionId']=='mention' for x in self.run_lookup(p,q,s,'turbinado')['paths']))


if __name__=='__main__': unittest.main()
