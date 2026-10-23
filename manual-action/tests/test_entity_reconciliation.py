"""Independent generated acceptance for the bounded pure reconciliation API.

No real source, rights, identity, household or country admission is represented.
Worker19 owns only this file; Worker13 owns the module and schema.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from entity_reconciliation import (ReconciliationError, digest, history_digest,
                                   registry_digest, validate_reconciliation)


def independent_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def independent_history_digest(history):
    value = copy.deepcopy(history)
    value['entries'].sort(key=lambda row: row['entry_id'])
    return independent_digest(value)


def independent_registry_digest(registry):
    value = copy.deepcopy(registry)
    value['entities'].sort(key=lambda row: row['entity_id'])
    value['active_entity_ids'].sort()
    value['memberships'].sort(key=lambda row: (row['entity_id'], row['occurrence_id']))
    return independent_digest(value)


def entity(identifier='entity-one', **changes):
    return {'entity_id': identifier, 'domain': 'barcodes', 'entity_type': 'product',
            'household_scope': None, 'user_scope': None, **changes}


def decision(occurrence, number, disposition, target=None, *, previous=None,
             action='assign', evidence=None, entry_id=None):
    return {'entry_id': entry_id or 'd-'+occurrence+'-'+str(number),
            'kind': 'decision', 'occurrence_id': occurrence, 'sequence': number,
            'action': action, 'disposition': disposition, 'entity_id': target,
            'reason': 'generated fixture '+disposition,
            'identity_evidence_id': evidence, 'supersedes': previous}


def membership(dec, previous=None):
    return {'entry_id': 'm-'+dec['entry_id'], 'kind': 'membership',
            'decision_id': dec['entry_id'], 'occurrence_id': dec['occurrence_id'],
            'entity_id': dec['entity_id'], 'supersedes': previous}


def generated_case():
    """Six occurrences; 3 mapped to 1 entity, 2 held, 1 excluded.

    a and a-copy share one source record/representation content but remain two
    occurrences. a/b claims conflict; citations stay attached to EACH occurrence.
    The missing relationship citation is retained explicitly unresolved.
    """
    identifier={'namespace': 'fixture:sku', 'provider': 'generated-provider',
                'value_type': 'string', 'lexical_value': '000123'}
    occurrences=[]
    for oid, source, record, version, value in (
        ('a', 'source-A', '001', 'release-A1', 10),
        ('b', 'source-B', 'different-id', 'release-B1', 12),
        ('a-copy', 'source-A', '001', 'release-A1', 10),
        ('ingredient', 'source-C', 'ingredient-1', 'release-C1', None),
        ('missing-id', 'source-D', 'missing', 'release-D1', None),
        ('excluded', 'source-E', 'restricted', 'release-E1', None)):
        raw={'name':'Generated name', 'value':value, 'explicit_null':None,
             'explicit_empty':'', 'unknown':{'state':'unknown','raw_lexeme':'ND'},
             'numeric_lexeme':'001.00', 'missing_barcode':None}
        occurrences.append({'occurrence_id':oid,
            'source':{'domain':'ingredients' if oid=='ingredient' else 'barcodes',
                      'source_key':source, 'source_version':version,
                      'record_id':record,'content_sha256':independent_digest(raw),
                      'adapter_occurrence_id':'adapter-'+oid,
                      'physical_representation_id':'representation-'+oid},
            'entity_type':'ingredient' if oid=='ingredient' else 'product',
            'household_scope':None,'user_scope':None,
            'identifiers':[copy.deepcopy(identifier)] if oid in ('a','b','a-copy') else [],
            'raw':raw})
    citations=[{'citation_id':cid,'raw':{'publisher':'synthetic','release':'fixture-1',
                 'uri':'https://fixture.invalid/'+cid}} for cid in ('ca','cb','unbound')]
    claims=[{'claim_id':'claim-'+o['occurrence_id'],'occurrence_id':o['occurrence_id'],
             'path':'/value','raw':{'value':o['raw']['value'],'basis':'per100g',
                                  'unit':'g','raw_lexeme':str(o['raw']['value'])}}
            for o in occurrences]
    attachments=[{'attachment_id':'record-'+oid,'owner_kind':'occurrence',
                  'owner_id':oid,'citation_id':cid,'support_scope':'record',
                  'raw':{'pointer':'/record'}}
                 for oid,cid in (('a','ca'),('b','cb'),('a-copy','ca'))]
    attachments += [
        {'attachment_id':'claim-a','owner_kind':'claim','owner_id':'claim-a',
         'citation_id':'ca','support_scope':'field','raw':{'pointer':'/value'}},
        {'attachment_id':'relationship-a','owner_kind':'relationship','owner_id':'r-a-b',
         'citation_id':'dangling-raw-citation','support_scope':'relationship',
         'raw':{'original_reference':'dangling-raw-citation'}}]
    selection={'schema_version':'offmenu.entity-reconciliation/1',
        'snapshot_id':'selected-generated-snapshot-1','scope_id':'public-generated-scope',
        'occurrences':occurrences,'claims':claims,
        'relationships':[{'relationship_id':'r-a-b','occurrence_id':'a',
                          'target_occurrence_id':'b','raw':{'kind':'fixture-relation'}}],
        'citations':citations,'attachments':attachments,
        'conflicts':[{'conflict_id':'conflicting-values','claim_ids':['claim-a','claim-b'],
                      'raw':{'status':'unresolved','values':[10,12]}}],
        'upstream':{'expected_occurrences':None,
                    'reason':'Earlier upstream occurrences are unavailable in this generated selection'}}
    entries=[]
    for oid in ('a','b','a-copy','ingredient','missing-id','excluded'):
        mapped=oid in ('a','b','a-copy')
        dec=decision(oid,1,'mapped' if mapped else ('excluded' if oid=='excluded' else 'held'),
                     'entity-one' if mapped else None,evidence='identity-one' if mapped else None)
        entries.append(dec)
        if mapped:entries.append(membership(dec))
    proposal={'schema_version':'offmenu.entity-proposal/1','entities':[entity()],
        'history':{'schema_version':'offmenu.entity-history/1','version':'mapping-1',
                   'previous_version':None,'scope_id':selection['scope_id'],'entries':entries},
        'citation_resolutions':[{'attachment_id':x['attachment_id'],
            'disposition':'qualified' if x['owner_kind']=='occurrence' else 'unresolved',
            'reason':'Generated selected record support' if x['owner_kind']=='occurrence'
                     else 'No selected field/relationship support evidence',
            'evidence_id':'record-support' if x['owner_kind']=='occurrence' else None}
            for x in attachments],
        'unbound_citations':[{'citation_id':'unbound','reason':'No selected attachment'}],
        'relationship_resolutions':[{'relationship_id':'r-a-b','disposition':'unresolved',
                                     'reason':'No qualified relationship citation'}]}
    selected=independent_digest(selection)
    authority={'schema_version':'offmenu.entity-authority/1','selection_sha256':selected,
        'policy_id':'fixture-policy-v1','policy_sha256':'1'*64,
        'identity_evidence':[{'evidence_id':'identity-one','kind':'exact_identifier',
            'selection_sha256':selected,'scope_id':selection['scope_id'],'domain':'barcodes',
            'entity_type':'product','household_scope':None,'user_scope':None,
            'members':['a','b','a-copy'],'identifier':copy.deepcopy(identifier),
            'evidence_sha256':'2'*64,'source_contract_sha256':'3'*64,
            'operation_evidence_id':'operation-one','review_receipt_sha256':None}],
        'operation_evidence':[{'evidence_id':'operation-one','selection_sha256':selected,
            'scope_id':selection['scope_id'],'operation':'entity_reconciliation',
            'members':['a','b','a-copy'],'evidence_sha256':'4'*64,'source_contract_sha256':'3'*64}],
        'citation_evidence':[{'evidence_id':'record-support','selection_sha256':selected,
            'scope_id':selection['scope_id'],'attachment_ids':['record-a','record-b','record-a-copy'],
            'support_scope':'record','evidence_sha256':'5'*64,'source_contract_sha256':'3'*64}],
        'prior_history':None,'prior_registry':None,'upstream_evidence':None}
    return selection,proposal,authority


def rebind_selection(selection, authority):
    """Rebind a generated caller selection, without inventing new authority."""
    selected=independent_digest(selection)
    authority['selection_sha256']=selected
    for kind in ('identity_evidence','operation_evidence','citation_evidence'):
        for row in authority[kind]:row['selection_sha256']=selected
    if authority['upstream_evidence'] is not None:
        authority['upstream_evidence']['selection_sha256']=selected


def all_held_case():
    selection,proposal,authority=generated_case()
    proposal['entities']=[]
    proposal['history']['entries']=[decision(o['occurrence_id'],1,'held')
                                   for o in selection['occurrences']]
    authority['identity_evidence']=[]
    authority['operation_evidence']=[]
    return selection,proposal,authority


def with_prior_history():
    selection,proposal,authority=generated_case()
    prior=copy.deepcopy(proposal['history'])
    proposal['history']['version']='mapping-2'
    proposal['history']['previous_version']=prior['version']
    old='d-b-1'
    proposal['history']['entries'].append(decision('b',2,'held',previous=old,action='revoke'))
    authority['prior_history']={'version':prior['version'],'scope_id':prior['scope_id'],
                                'sha256':independent_history_digest(prior)}
    return selection,proposal,authority,prior


def with_registry():
    selection,proposal,authority=generated_case()
    registry={'schema_version':'offmenu.entity-registry/1','version':'registry-1',
        'scope_id':selection['scope_id'],'entities':[entity('old-A'),entity('old-B')],
        'active_entity_ids':['old-A','old-B'],
        'memberships':[{'entity_id':'old-A','occurrence_id':'a'},
                       {'entity_id':'old-A','occurrence_id':'a-copy'},
                       {'entity_id':'old-B','occurrence_id':'b'}]}
    authority['prior_registry']={'version':registry['version'],'scope_id':registry['scope_id'],
                                'sha256':independent_registry_digest(registry)}
    proposal['entities'].extend(copy.deepcopy(registry['entities']))
    proposal['history']['entries'].extend([
        {'entry_id':'alias-'+old,'kind':'alias','from_entity_id':old,'to_entity_id':'entity-one',
         'decision_id':'d-'+oid+'-1','supersedes':None}
        for old,oid in (('old-A','a'),('old-B','b'))])
    return selection,proposal,authority,registry


class ReconciliationAcceptanceTests(unittest.TestCase):
    def run_case(self, selection, proposal, authority, **prior):
        before=copy.deepcopy((selection,proposal,authority,prior))
        result=validate_reconciliation(selection,proposal,authority=authority,**prior)
        self.assertEqual((selection,proposal,authority,prior),before,'Pure validator mutated an input')
        return result

    def reject(self, selection, proposal, authority, **prior):
        before=copy.deepcopy((selection,proposal,authority,prior))
        with self.assertRaises(ReconciliationError) as caught:
            validate_reconciliation(selection,proposal,authority=authority,**prior)
        self.assertIsInstance(caught.exception.code,str)
        self.assertTrue(caught.exception.code)
        self.assertEqual((selection,proposal,authority,prior),before,'Rejected input was mutated')

    def test_valid_many_to_one_preserves_every_selected_manifest(self):
        selection,proposal,authority=generated_case()
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['schema_version'],'offmenu.entity-receipt/1')
        self.assertEqual(result['preserved'],selection)
        expected=copy.deepcopy(proposal)
        expected['history']['entries'].sort(key=lambda e:e['entry_id'])
        self.assertEqual(result['validated_proposal'],expected)
        self.assertEqual(len(result['effective_decisions']),6)
        self.assertEqual(sum(d['disposition']=='mapped' for d in result['effective_decisions']),3)
        self.assertEqual(sum(d['disposition']=='held' for d in result['effective_decisions']),2)
        self.assertEqual(sum(d['disposition']=='excluded' for d in result['effective_decisions']),1)
        self.assertEqual(result,self.run_case(selection,proposal,authority))
        self.assertEqual(result['metrics'],{
            'selected_occurrences':6,'distinct_source_record_keys':5,'extra_representation_occurrences':1,
            'mapped_occurrences':3,'held_occurrences':2,'excluded_occurrences':1,
            'mapped_entities':1,'duplicate_mapped_occurrences':2,
            'entities_before':None,'entities_after':None,
            'registry_unavailable_reason':'qualified_prior_registry_unavailable',
            'upstream_occurrences':None,'upstream_unavailable_reason':'upstream_occurrence_coverage_unavailable',
            'mapped_record_citation_coverage':{'covered':3,'total':3},
            'all_record_citation_coverage':{'covered':3,'total':6},
            'claim_field_citation_coverage':{'covered':0,'total':6},
            'citation_count':3,'attachment_count':5,'unbound_citations':1,
            'unresolved_citation_support':2,'dangling_citation_references':1,
            'unresolved_conflicts':1,'unresolved_relationship_support':1,
            'orphan_citation_loss':0,'unaccounted_occurrences':0})
        self.assertEqual(result['pins']['selection_sha256'],independent_digest(selection))
        self.assertEqual(result['pins']['claims_sha256'],independent_digest(selection['claims']))
        self.assertEqual(result['pins']['citations_sha256'],independent_digest(selection['citations']))
        without_output_pin=copy.deepcopy(result)
        output_pin=without_output_pin['pins'].pop('output_sha256')
        self.assertEqual(output_pin,independent_digest(without_output_pin))

    def test_all_held_without_identity_or_operation_evidence_is_valid(self):
        selection,proposal,authority=all_held_case()
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved'],selection)
        self.assertTrue(all(d['disposition']=='held' for d in result['effective_decisions']))
        self.assertEqual(result['metrics']['mapped_occurrences'],0)
        self.assertEqual(result['metrics']['held_occurrences'],6)
        self.assertEqual(result['metrics']['mapped_entities'],0)
        self.assertIsNone(result['metrics']['entities_before'])
        self.assertIsNone(result['metrics']['entities_after'])

    def test_raw_missing_null_blank_and_unknown_claims_are_not_rewritten(self):
        selection,proposal,authority=generated_case()
        raw=selection['occurrences'][0]['raw']
        self.assertNotIn('absent_field',raw)
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved']['occurrences'][0]['raw'],raw)
        self.assertIsNone(raw['explicit_null'])
        self.assertEqual(raw['explicit_empty'],'')
        self.assertEqual(raw['numeric_lexeme'],'001.00')

    def test_dangling_relationship_citation_remains_explicitly_unresolved(self):
        selection,proposal,authority=generated_case()
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved']['attachments'][-1]['citation_id'],'dangling-raw-citation')
        self.assertEqual(result['validated_proposal']['citation_resolutions'][-1]['disposition'],'unresolved')
        self.assertEqual(result['preserved']['conflicts'],selection['conflicts'])

    def test_invalid_lexical_identifiers_cannot_be_self_admitted(self):
        for value in (None,'',' ','None','null',123,True,[],{}):
            with self.subTest(value=value):
                selection,proposal,authority=generated_case()
                for row in selection['occurrences'][:3]:
                    row['identifiers'][0]['lexical_value']=copy.deepcopy(value)
                authority['identity_evidence'][0]['identifier']['lexical_value']=copy.deepcopy(value)
                rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)

    def test_missing_identifier_keys_cannot_be_qualified(self):
        for key in ('namespace','provider','value_type','lexical_value'):
            with self.subTest(key=key):
                selection,proposal,authority=generated_case()
                for row in selection['occurrences'][:3]:del row['identifiers'][0][key]
                del authority['identity_evidence'][0]['identifier'][key]
                rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)

    def test_bad_namespace_provider_and_value_type_do_not_qualify(self):
        for key in ('namespace','provider','value_type'):
            for value in (None,'',' ','None',True):
                with self.subTest(key=key,value=value):
                    selection,proposal,authority=generated_case()
                    for row in selection['occurrences'][:3]:row['identifiers'][0][key]=value
                    authority['identity_evidence'][0]['identifier'][key]=value
                    rebind_selection(selection,authority)
                    self.reject(selection,proposal,authority)

    def test_invalid_identifiers_may_be_preserved_held(self):
        for value in (None,'','None'):
            with self.subTest(value=value):
                selection,proposal,authority=all_held_case()
                selection['occurrences'][0]['identifiers'][0]['lexical_value']=value
                rebind_selection(selection,authority)
                result=self.run_case(selection,proposal,authority)
                self.assertEqual(result['preserved'],selection)

    def test_no_identity_authority_hash_path_or_producer_claim(self):
        for kind in ('missing','hash-only','path-only','producer-flag','gtin-syntax'):
            with self.subTest(kind=kind):
                selection,proposal,authority=generated_case()
                authority['identity_evidence']=[]
                selection['occurrences'][0]['raw']['self_admitted_proof']={'kind':kind,'sha256':'2'*64,
                    'path':'/fixture/retained/source','admitted':True,'gtin_syntax_valid':True}
                rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)

    def test_operation_evidence_required_and_operation_specific(self):
        for change in ('missing','wrong-operation','missing-member','wrong-scope','wrong-snapshot'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case()
                if change=='missing':authority['operation_evidence']=[]
                elif change=='wrong-operation':authority['operation_evidence'][0]['operation']='retain'
                elif change=='missing-member':authority['operation_evidence'][0]['members'].remove('b')
                elif change=='wrong-scope':authority['operation_evidence'][0]['scope_id']='other-scope'
                else:authority['operation_evidence'][0]['selection_sha256']='f'*64
                self.reject(selection,proposal,authority)

    def test_identity_evidence_context_and_members_are_bound(self):
        for key,value in (('scope_id','other'),('domain','ingredients'),('entity_type','recipe'),
                          ('household_scope','household-other'),('user_scope','user-other'),
                          ('selection_sha256','f'*64),('members',['a','b']),
                          ('operation_evidence_id','unknown-operation')):
            with self.subTest(key=key):
                selection,proposal,authority=generated_case()
                authority['identity_evidence'][0][key]=value
                self.reject(selection,proposal,authority)

    def test_reviewed_equivalence_requires_selected_review_receipt(self):
        selection,proposal,authority=generated_case()
        evidence=authority['identity_evidence'][0]
        evidence['kind']='reviewed_equivalence';evidence['identifier']=None
        self.reject(selection,proposal,authority)
        evidence['review_receipt_sha256']='6'*64
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved'],selection)

    def test_lexical_leading_zero_is_not_silently_erased(self):
        selection,proposal,authority=generated_case()
        selection['occurrences'][1]['identifiers'][0]['lexical_value']='123'
        rebind_selection(selection,authority)
        self.reject(selection,proposal,authority)

    def test_mixed_transitive_evidence_cannot_form_one_entity_component(self):
        selection,proposal,authority=generated_case()
        first=authority['identity_evidence'][0];first['members']=['a','b']
        second=copy.deepcopy(first);second['evidence_id']='identity-two';second['members']=['b','a-copy']
        authority['identity_evidence'].append(second)
        next(d for d in proposal['history']['entries'] if d['entry_id']=='d-a-copy-1')['identity_evidence_id']='identity-two'
        self.reject(selection,proposal,authority)

    def test_private_user_type_and_domain_scopes_cannot_cross_merge(self):
        for key,value in (('household_scope','household-B'),('user_scope','user-B'),('entity_type','ingredient')):
            with self.subTest(key=key):
                selection,proposal,authority=generated_case()
                selection['occurrences'][1][key]=value;rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)
        selection,proposal,authority=generated_case()
        selection['occurrences'][1]['source']['domain']='ingredients';rebind_selection(selection,authority)
        self.reject(selection,proposal,authority)

    def test_dangling_citations_cannot_be_qualified_for_any_owner_kind(self):
        for owner_kind in ('occurrence','claim','relationship'):
            with self.subTest(owner_kind=owner_kind):
                selection,proposal,authority=generated_case()
                attachment=next(a for a in selection['attachments'] if a['owner_kind']==owner_kind)
                attachment['citation_id']='unknown-selected-reference'
                rebind_selection(selection,authority)
                authority['citation_evidence'].append({'evidence_id':'bad-support',
                    'selection_sha256':independent_digest(selection),'scope_id':selection['scope_id'],
                    'attachment_ids':[attachment['attachment_id']],'support_scope':attachment['support_scope'],
                    'evidence_sha256':'7'*64,'source_contract_sha256':'3'*64})
                resolution=next(r for r in proposal['citation_resolutions'] if r['attachment_id']==attachment['attachment_id'])
                resolution.update(disposition='qualified',evidence_id='bad-support')
                self.reject(selection,proposal,authority)

    def test_record_support_does_not_qualify_a_field(self):
        selection,proposal,authority=generated_case()
        row=next(r for r in proposal['citation_resolutions'] if r['attachment_id']=='claim-a')
        row.update(disposition='qualified',evidence_id='record-support')
        self.reject(selection,proposal,authority)

    def test_explicit_selected_field_support_is_separate_and_valid(self):
        selection,proposal,authority=generated_case()
        evidence=copy.deepcopy(authority['citation_evidence'][0])
        evidence.update(evidence_id='field-support',attachment_ids=['claim-a'],support_scope='field')
        authority['citation_evidence'].append(evidence)
        row=next(r for r in proposal['citation_resolutions'] if r['attachment_id']=='claim-a')
        row.update(disposition='qualified',evidence_id='field-support')
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved'],selection)
        self.assertEqual(result['metrics']['claim_field_citation_coverage'],{'covered':1,'total':6})

    def test_missing_or_duplicate_citation_dispositions_are_rejected(self):
        for change in ('missing','duplicate','unknown-attachment'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case()
                if change=='missing':proposal['citation_resolutions'].pop()
                elif change=='duplicate':proposal['citation_resolutions'].append(copy.deepcopy(proposal['citation_resolutions'][0]))
                else:proposal['citation_resolutions'][0]['attachment_id']='invented-attachment'
                self.reject(selection,proposal,authority)

    def test_repeated_occurrence_requires_its_own_qualified_record_attachment(self):
        selection,proposal,authority=generated_case()
        row=next(r for r in proposal['citation_resolutions'] if r['attachment_id']=='record-a-copy')
        row.update(disposition='unresolved',evidence_id=None,reason='Missing repeat support')
        self.reject(selection,proposal,authority)

    def test_unbound_citation_must_not_disappear_or_be_double_counted(self):
        for change in ('missing','duplicate','unknown','blank-reason'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case()
                if change=='missing':proposal['unbound_citations']=[]
                elif change=='duplicate':proposal['unbound_citations']*=2
                elif change=='unknown':proposal['unbound_citations'][0]['citation_id']='made-up'
                else:proposal['unbound_citations'][0]['reason']=''
                self.reject(selection,proposal,authority)

    def test_relationship_requires_explicit_disposition(self):
        for change in ('missing','duplicate','unknown'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case()
                if change=='missing':proposal['relationship_resolutions']=[]
                elif change=='duplicate':proposal['relationship_resolutions']*=2
                else:proposal['relationship_resolutions'][0]['relationship_id']='unknown'
                self.reject(selection,proposal,authority)

    def test_claim_relationship_conflict_and_citation_references_are_validated(self):
        changes=(('claim-owner',lambda s:s['claims'][0].update(occurrence_id='unknown')),
                 ('relationship-source',lambda s:s['relationships'][0].update(occurrence_id='unknown')),
                 ('conflict-claim',lambda s:s['conflicts'][0]['claim_ids'].append('unknown')),
                 ('attachment-owner',lambda s:s['attachments'][0].update(owner_id='unknown')))
        for name,change in changes:
            with self.subTest(name=name):
                selection,proposal,authority=generated_case();change(selection);rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)

    def test_unknown_relationship_endpoint_is_preserved_unresolved_not_mapped(self):
        selection,proposal,authority=generated_case()
        selection['relationships'][0]['target_occurrence_id']='unknown-generated-endpoint'
        rebind_selection(selection,authority)
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved']['relationships'],selection['relationships'])
        self.assertEqual(result['relationship_support'][0]['disposition'],'unresolved')
        proposal['relationship_resolutions'][0]['disposition']='mapped'
        self.reject(selection,proposal,authority)

    def test_prior_history_revoke_appends_and_preserves_all_old_entries(self):
        selection,proposal,authority,prior=with_prior_history()
        result=self.run_case(selection,proposal,authority,prior_history=prior)
        prior_ids={e['entry_id'] for e in prior['entries']}
        returned={e['entry_id']:e for e in result['validated_proposal']['history']['entries']}
        self.assertTrue(prior_ids<=returned.keys())
        for entry in prior['entries']:self.assertEqual(returned[entry['entry_id']],entry)
        self.assertEqual(next(d for d in result['effective_decisions'] if d['occurrence_id']=='b')['disposition'],'held')

    def test_prior_history_deletion_and_content_or_sequence_rewrites_rejected(self):
        for change in ('delete-decision','delete-membership','rewrite-sequence','rewrite-entity','rewrite-reason','rewrite-evidence'):
            with self.subTest(change=change):
                selection,proposal,authority,prior=with_prior_history()
                entries=proposal['history']['entries']
                if change=='delete-decision':entries[:]=[e for e in entries if e['entry_id']!='d-b-1']
                elif change=='delete-membership':entries[:]=[e for e in entries if e['entry_id']!='m-d-b-1']
                else:
                    row=next(e for e in entries if e['entry_id']=='d-b-1')
                    key,value={'rewrite-sequence':('sequence',9),'rewrite-entity':('entity_id','other'),
                               'rewrite-reason':('reason','new reason'),'rewrite-evidence':('identity_evidence_id','other')}[change]
                    row[key]=value
                self.reject(selection,proposal,authority,prior_history=prior)

    def test_prior_history_bindings_and_version_are_required(self):
        for change in ('digest','version','scope','missing-binding','missing-input','previous-version','same-version'):
            with self.subTest(change=change):
                selection,proposal,authority,prior=with_prior_history()
                if change=='digest':authority['prior_history']['sha256']='f'*64
                elif change=='version':authority['prior_history']['version']='other'
                elif change=='scope':authority['prior_history']['scope_id']='other'
                elif change=='missing-binding':authority['prior_history']=None
                elif change=='previous-version':proposal['history']['previous_version']='other'
                elif change=='same-version':proposal['history']['version']=prior['version']
                self.reject(selection,proposal,authority,prior_history=None if change=='missing-input' else prior)

    def test_history_order_independent_digest_and_replay(self):
        selection,proposal,authority,prior=with_prior_history()
        first=self.run_case(selection,proposal,authority,prior_history=prior)
        prior['entries'].reverse();proposal['history']['entries'].reverse()
        self.assertEqual(history_digest(prior),independent_history_digest(prior))
        second=self.run_case(selection,proposal,authority,prior_history=prior)
        self.assertEqual(first['metrics'],second['metrics'])
        self.assertEqual(first['effective_decisions'],second['effective_decisions'])
        self.assertEqual(first['pins'],second['pins'])

    def test_history_invalid_supersedes_sequence_and_duplicate_heads(self):
        for change in ('missing-reference','other-occurrence','self-cycle','sequence-gap','duplicate-decision','fork'):
            with self.subTest(change=change):
                selection,proposal,authority,prior=with_prior_history()
                row=proposal['history']['entries'][-1]
                if change=='missing-reference':row['supersedes']='not-a-decision'
                elif change=='other-occurrence':row['supersedes']='d-a-1'
                elif change=='self-cycle':row['supersedes']=row['entry_id']
                elif change=='sequence-gap':row['sequence']=3
                elif change=='duplicate-decision':proposal['history']['entries'].append(copy.deepcopy(row))
                else:proposal['history']['entries'].append({**row,'entry_id':'fork'})
                self.reject(selection,proposal,authority,prior_history=prior)

    def test_split_adds_new_mapping_and_membership_without_erasing_old(self):
        selection,proposal,authority=generated_case();prior=copy.deepcopy(proposal['history'])
        proposal['entities'].append(entity('entity-split'))
        proposal['history'].update(version='mapping-2',previous_version='mapping-1')
        other=copy.deepcopy(authority['identity_evidence'][0])
        other.update(evidence_id='identity-split',members=['b'])
        authority['identity_evidence'][0]['members']=['a','a-copy']
        authority['identity_evidence'].append(other)
        dec=decision('b',2,'mapped','entity-split',previous='d-b-1',action='split',evidence='identity-split')
        proposal['history']['entries'].extend([dec,membership(dec,'m-d-b-1')])
        authority['prior_history']={'version':prior['version'],'scope_id':prior['scope_id'],
                                    'sha256':independent_history_digest(prior)}
        result=self.run_case(selection,proposal,authority,prior_history=prior)
        self.assertEqual(len(result['preserved']['occurrences']),6)
        self.assertEqual(len(result['validated_proposal']['history']['entries']),len(prior['entries'])+2)

    def test_missing_duplicate_or_dangling_membership_rejected(self):
        for change in ('missing','duplicate','unknown-decision','wrong-occurrence','wrong-entity'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case();entries=proposal['history']['entries']
                row=next(e for e in entries if e['kind']=='membership')
                if change=='missing':entries.remove(row)
                elif change=='duplicate':entries.append({**row,'entry_id':'duplicate-member'})
                elif change=='unknown-decision':row['decision_id']='unknown'
                elif change=='wrong-occurrence':row['occurrence_id']='b'
                else:row['entity_id']='unknown'
                self.reject(selection,proposal,authority)

    def test_registry_unique_ids_and_qualified_bindings(self):
        selection,proposal,authority,registry=with_registry()
        result=self.run_case(selection,proposal,authority,prior_registry=registry)
        self.assertEqual(registry_digest(registry),independent_registry_digest(registry))
        self.assertEqual(result['preserved'],selection)
        self.assertEqual(result['metrics']['entities_before'],2)
        self.assertEqual(result['metrics']['entities_after'],1)

    def test_registry_duplicate_untyped_or_empty_ids_rejected_even_if_rehashed(self):
        for value in ('old-A','',None,True,123):
            with self.subTest(value=value):
                selection,proposal,authority,registry=with_registry()
                registry['active_entity_ids'].append(value)
                # Keep selection authority pinned to precisely the malformed input;
                # a matching hash cannot make malformed registry IDs admissible.
                try:authority['prior_registry']['sha256']=independent_registry_digest(registry)
                except TypeError:pass
                self.reject(selection,proposal,authority,prior_registry=registry)

    def test_registry_descriptor_membership_scope_and_pin_failures(self):
        for change in ('duplicate-descriptor','unknown-active-id','unknown-member-entity','unknown-occurrence',
                       'duplicate-membership','scope','entity-scope','version','digest','missing-input'):
            with self.subTest(change=change):
                selection,proposal,authority,registry=with_registry()
                if change=='duplicate-descriptor':registry['entities'].append(copy.deepcopy(registry['entities'][0]))
                elif change=='unknown-active-id':registry['active_entity_ids'].append('unknown')
                elif change=='unknown-member-entity':registry['memberships'][0]['entity_id']='unknown'
                elif change=='unknown-occurrence':registry['memberships'][0]['occurrence_id']='unknown'
                elif change=='duplicate-membership':registry['memberships'].append(copy.deepcopy(registry['memberships'][0]))
                elif change=='scope':registry['scope_id']='other'
                elif change=='entity-scope':registry['entities'][0]['household_scope']='other-household'
                elif change=='version':authority['prior_registry']['version']='other'
                elif change=='digest':authority['prior_registry']['sha256']='f'*64
                if change not in ('version','digest'):authority['prior_registry']['sha256']=independent_registry_digest(registry)
                self.reject(selection,proposal,authority,prior_registry=None if change=='missing-input' else registry)

    def test_held_input_does_not_force_registry_reduction(self):
        selection,proposal,authority,registry=with_registry()
        proposal['entities']=copy.deepcopy(registry['entities'])
        proposal['history']['entries']=[decision(o['occurrence_id'],1,'held') for o in selection['occurrences']]
        result=self.run_case(selection,proposal,authority,prior_registry=registry)
        self.assertTrue(all(d['disposition']=='held' for d in result['effective_decisions']))
        self.assertEqual(result['metrics']['entities_before'],2)
        self.assertEqual(result['metrics']['entities_after'],2)

    def test_registry_presentation_order_does_not_change_pin_or_counts(self):
        selection,proposal,authority,registry=with_registry()
        first=self.run_case(selection,proposal,authority,prior_registry=registry)
        for key in ('entities','active_entity_ids','memberships'):registry[key].reverse()
        self.assertEqual(registry_digest(registry),independent_registry_digest(registry))
        second=self.run_case(selection,proposal,authority,prior_registry=registry)
        self.assertEqual(first['metrics'],second['metrics'])
        self.assertEqual(first['pins'],second['pins'])

    def test_valid_but_unqualified_registry_never_supplies_entity_denominators(self):
        selection,proposal,authority,registry=with_registry()
        proposal['history']['entries']=[e for e in proposal['history']['entries'] if e['kind']!='alias']
        authority['prior_registry']=None
        result=self.run_case(selection,proposal,authority,prior_registry=registry)
        self.assertIsNone(result['metrics']['entities_before'])
        self.assertIsNone(result['metrics']['entities_after'])
        self.assertEqual(result['metrics']['registry_unavailable_reason'],'qualified_prior_registry_unavailable')
        self.assertEqual(result['metrics']['selected_occurrences'],6)
        self.assertEqual(result['metrics']['mapped_entities'],1)

    def test_alias_retirement_needs_qualified_registry_and_all_prior_members(self):
        for change in ('no-qualified-registry','held-member','unknown-target','wrong-decision','duplicate-alias-root'):
            with self.subTest(change=change):
                selection,proposal,authority,registry=with_registry()
                alias=next(e for e in proposal['history']['entries'] if e['kind']=='alias')
                if change=='no-qualified-registry':authority['prior_registry']=None
                elif change=='held-member':
                    proposal['history']['entries'].append(decision('a-copy',2,'held',previous='d-a-copy-1',action='revoke'))
                elif change=='unknown-target':alias['to_entity_id']='unknown'
                elif change=='wrong-decision':alias['decision_id']='d-missing-id-1'
                else:proposal['history']['entries'].append({**alias,'entry_id':'another-alias-root'})
                self.reject(selection,proposal,authority,prior_registry=registry)

    def test_prior_alias_rows_are_immutable_even_after_registry_retirement(self):
        selection,proposal,authority,registry=with_registry()
        prior=copy.deepcopy(proposal['history'])
        # The subsequent independently selected registry reflects the first merge,
        # retaining old descriptors and inactive memberships rather than deleting.
        registry['version']='registry-2'
        registry['entities'].append(entity())
        registry['active_entity_ids']=['entity-one']
        registry['memberships'].extend({'entity_id':'entity-one','occurrence_id':oid}
                                      for oid in ('a','b','a-copy'))
        authority['prior_registry']={'version':registry['version'],'scope_id':registry['scope_id'],
                                    'sha256':independent_registry_digest(registry)}
        authority['prior_history']={'version':prior['version'],'scope_id':prior['scope_id'],
                                   'sha256':independent_history_digest(prior)}
        baseline=self.run_case(selection,proposal,authority,prior_history=prior,prior_registry=registry)
        self.assertEqual(baseline['metrics']['entities_before'],1)
        self.assertEqual(baseline['metrics']['entities_after'],1)
        for change in ('delete','rewrite-target','rewrite-decision','rewrite-supersedes'):
            with self.subTest(change=change):
                changed=copy.deepcopy(proposal)
                alias=next(e for e in changed['history']['entries'] if e['kind']=='alias')
                if change=='delete':changed['history']['entries'].remove(alias)
                elif change=='rewrite-target':alias['to_entity_id']='old-B'
                elif change=='rewrite-decision':alias['decision_id']='d-b-1'
                else:alias['supersedes']='invented-old-alias'
                self.reject(selection,changed,authority,prior_history=prior,prior_registry=registry)

    def test_upstream_count_requires_separate_selected_evidence(self):
        selection,proposal,authority=generated_case()
        selection['upstream']['expected_occurrences']=6
        rebind_selection(selection,authority)
        result=self.run_case(selection,proposal,authority)
        self.assertIsNone(result['metrics']['upstream_occurrences'])
        self.assertTrue(result['metrics']['upstream_unavailable_reason'])
        authority['upstream_evidence']={'selection_sha256':independent_digest(selection),
            'scope_id':selection['scope_id'],'expected_occurrences':6,'evidence_sha256':'8'*64}
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['metrics']['upstream_occurrences'],6)
        self.assertIsNone(result['metrics']['upstream_unavailable_reason'])
        authority['upstream_evidence']['expected_occurrences']=7
        self.reject(selection,proposal,authority)

    def test_citation_endpoint_mapping_is_distinct_from_citation_support(self):
        selection,proposal,authority=generated_case()
        proposal['relationship_resolutions'][0]['disposition']='mapped'
        result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['relationship_support'][0]['disposition'],'mapped')
        self.assertEqual(result['relationship_support'][0]['citation_support'],'unresolved')
        self.assertEqual(result['metrics']['dangling_citation_references'],1)
        self.assertEqual(result['metrics']['orphan_citation_loss'],0)
        self.assertEqual(result['metrics']['claim_field_citation_coverage'],{'covered':0,'total':6})

    def test_schema_is_local_and_accepts_generated_input_wrapper(self):
        import jsonschema  # Already a declared project dependency; never installed here.
        schema=json.loads(Path(__file__).resolve().parents[1].joinpath('entity-reconciliation.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        def local_refs(value):
            if isinstance(value,dict):
                if '$ref' in value:self.assertTrue(value['$ref'].startswith('#/'))
                for child in value.values():local_refs(child)
            elif isinstance(value,list):
                for child in value:local_refs(child)
        local_refs(schema)
        selection,proposal,authority=generated_case()
        wrapper={'selection':selection,'proposal':proposal,'authority':authority,
                 'prior_history':None,'prior_registry':None}
        self.assertEqual(list(jsonschema.Draft202012Validator(schema).iter_errors(wrapper)),[])
        output_schema={'$schema':schema['$schema'],'$defs':schema['$defs'],'$ref':'#/$defs/Receipt'}
        receipt=self.run_case(selection,proposal,authority)
        self.assertEqual(list(jsonschema.Draft202012Validator(output_schema).iter_errors(receipt)),[])

    def test_nonfinite_and_overdeep_json_inputs_fail_closed(self):
        for value in (float('nan'),float('inf'),float('-inf')):
            with self.subTest(value=value):
                selection,proposal,authority=generated_case()
                selection['occurrences'][0]['raw']['invalid-number']=value
                with self.assertRaises(ReconciliationError):
                    validate_reconciliation(selection,proposal,authority=authority)
        selection,proposal,authority=generated_case()
        deep=None
        for _ in range(40):deep=[deep]
        selection['occurrences'][0]['raw']['overdeep']=deep
        self.reject(selection,proposal,authority)

    def test_every_occurrence_has_exactly_one_current_disposition(self):
        for change in ('missing','duplicate','unknown-occurrence','wrong-target','empty-held-reason','held-with-entity'):
            with self.subTest(change=change):
                selection,proposal,authority=generated_case();entries=proposal['history']['entries']
                if change=='missing':entries[:]=[d for d in entries if d.get('occurrence_id')!='missing-id']
                elif change=='duplicate':entries.append(copy.deepcopy(entries[0]))
                elif change=='unknown-occurrence':entries[-1]['occurrence_id']='unknown'
                elif change=='wrong-target':entries[0]['entity_id']='unknown'
                elif change=='empty-held-reason':next(d for d in entries if d.get('occurrence_id')=='missing-id')['reason']=''
                else:next(d for d in entries if d.get('occurrence_id')=='missing-id')['entity_id']='entity-one'
                self.reject(selection,proposal,authority)

    def test_duplicate_selected_occurrence_claim_citation_and_attachment_ids_reject(self):
        for key in ('occurrences','claims','citations','attachments','relationships','conflicts'):
            with self.subTest(key=key):
                selection,proposal,authority=generated_case()
                selection[key].append(copy.deepcopy(selection[key][0]));rebind_selection(selection,authority)
                self.reject(selection,proposal,authority)

    def test_receipt_binds_changed_raw_claim_citation_conflict_and_source_release(self):
        selection,proposal,authority=generated_case()
        for field in ('claims','citations','conflicts','occurrences'):
            with self.subTest(field=field):
                changed=copy.deepcopy(selection)
                if field=='occurrences':changed[field][0]['source']['source_version']='rewritten-release'
                else:changed[field][0]['raw']['changed']='true'
                self.reject(changed,proposal,authority)

    def test_canonical_digest_and_pure_validation_do_no_io(self):
        selection,proposal,authority=generated_case()
        self.assertEqual(digest(selection),independent_digest(selection))
        with mock.patch.object(io,'open',side_effect=AssertionError('filesystem forbidden')), \
             mock.patch('builtins.open',side_effect=AssertionError('filesystem forbidden')), \
             mock.patch.object(os,'open',side_effect=AssertionError('filesystem forbidden')), \
             mock.patch.object(socket,'socket',side_effect=AssertionError('network forbidden')), \
             mock.patch.object(sqlite3,'connect',side_effect=AssertionError('database forbidden')), \
             mock.patch.object(subprocess,'Popen',side_effect=AssertionError('subprocess forbidden')):
            result=self.run_case(selection,proposal,authority)
        self.assertEqual(result['preserved'],selection)


if __name__=='__main__':
    unittest.main()
