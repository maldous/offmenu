"""Exact reference bridge and full-cardinality collector interception, no Foo reads."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from offmenu.refresh import taiwan_fetch_acceptance as t
import test_actual988_stages as full

ROOT=Path(__file__).resolve().parents[1]
SOURCES=json.loads((ROOT/'docs/collection-selections/global-comprehensive-selection.json').read_bytes())['sources']
_, MANIFEST=t.load_manifest(ROOT)


def writer_fixture(blocked=False, reused=False):
    class AcceptanceError(ValueError): pass
    def accept(raw,**kw):
        if blocked: raise AcceptanceError('acceptance-current-conflict')
        refs={'receiptSHA256':'d'*64,'items':[{'sourceKey':r['sourceKey'],'assetId':r['assetId'],
            'reference':r['proposedCustodyReference'],'downstreamHolds':r['preservedDownstreamHolds']}
            for r in MANIFEST['items']]}
        return {'status':'reused-accepted-reference' if reused else 'accepted-retained-reference',
            'dispositionApplied':not reused,'receiptSHA256':'d'*64,
            'acceptedAtUTC':'2026-10-19T00:00:00+00:00','originalAcquiredAt':None},SimpleNamespace(references=lambda:refs)
    return SimpleNamespace(AcceptanceError=AcceptanceError,ERRORS={'acceptance-current-conflict','acceptance-local-failure'},accept_selected=accept)


def report(blocked=False,reused=False):
    with patch.object(t,'_writer',return_value=writer_fixture(blocked,reused)):
        return t.perform(t.SELECTION,SOURCES,owner_runtime=object(),lease_fd=123,
            current_adverse_evidence=lambda:[],absolute_deadline=time.monotonic()+5,root=ROOT)


class BridgeTests(unittest.TestCase):
    def test_exact_three_reference_identities(self):
        r=report();self.assertEqual(len(r['items']),3);self.assertEqual(r['verifiedOriginalPayloadBytes'],6490476)
        self.assertEqual(r['maximumLocalOriginalReadBytes'],12980952);self.assertEqual(r['localOriginalReadBytes'],12980952)
        self.assertIsNone(r['originalAcquiredAt']);self.assertEqual(r['newOriginalCopies'],0)
        self.assertTrue(all(x['relativePath'].endswith('/original.partial')for x in r['items']))
        t.sanitize(r,t.SELECTION,SOURCES)
    def test_reuse_is_separate_from_new_acceptance(self):
        r=report(reused=True);self.assertFalse(r['dispositionApplied']);self.assertEqual(r['status'],'reused-accepted-reference')
    def test_failure_retains_bounded_unknown_read_accounting(self):
        r=report(blocked=True);self.assertEqual(r['items'],[]);self.assertIsNone(r['localOriginalReadBytes']);self.assertFalse(r['localOriginalReadAccountingComplete'])
    def test_no_source_request_implementation(self):
        with patch('socket.socket',side_effect=AssertionError('no network')):r=report()
        self.assertEqual(r['networkRequests'],0)
    def test_missing_selection_blocks_before_writer(self):
        with patch.object(t,'_writer',side_effect=AssertionError('writer not entered')):
            with self.assertRaises(t.RefreshError):t.perform(None,SOURCES,owner_runtime=None,lease_fd=None,current_adverse_evidence=None,absolute_deadline=0)
    def test_changed_source_contract_blocks(self):
        changed=deepcopy(SOURCES);changed[0]['url']+='?new=1'
        with self.assertRaises(t.RefreshError):t.validate_selection(t.SELECTION,changed)
    def test_no_generic_bom_allowance(self):
        r=report();r['items'][0]['originalSHA256']='a'*64
        with self.assertRaises(t.RefreshError):t.sanitize(r,t.SELECTION,SOURCES)
    def test_acquisition_timestamp_cannot_be_fabricated(self):
        r=report();r['originalAcquiredAt']='2026-10-19T00:00:00Z'
        with self.assertRaises(t.RefreshError):t.sanitize(r,t.SELECTION,SOURCES)
    def test_download_count_cannot_be_fabricated(self):
        r=report();r['networkRequests']=1
        with self.assertRaises(t.RefreshError):t.sanitize(r,t.SELECTION,SOURCES)
    def test_failed_intent_is_exact_and_unchanged(self):
        r=report();r['items'][0]['oldFailedIntentSHA256']='a'*64
        with self.assertRaises(t.RefreshError):t.sanitize(r,t.SELECTION,SOURCES)
    def test_raw_fields_rejected(self):
        r=report();r['headers']={'Cookie':'secret'}
        with self.assertRaises(t.RefreshError):t.sanitize(r,t.SELECTION,SOURCES)


class InterceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        full.Actual988Tests.setUpClass.__func__(cls)
    execution=full.Actual988Tests.execution
    publish_and_reload=full.Actual988Tests.publish_and_reload
    def execute(self,blocked=False):
        g=full.g;original=g.run_global;observed={};result=report(blocked=blocked)
        def run(*args,**kwargs):
            kwargs['retained_acceptance_selection']=t.SELECTION
            kwargs['current_adverse_evidence']=lambda:[]
            return original(*args,**kwargs)
        def perform(*args,**kwargs):
            self.assertIs(threading.current_thread(),threading.main_thread())
            self.assertIsInstance(kwargs['lease_fd'],int);observed['calls']=observed.get('calls',0)+1
            return deepcopy(result)
        with ExitStack() as stack:
            stack.enter_context(patch.object(g,'run_global',side_effect=run))
            stack.enter_context(patch.object(g.twaccept,'perform',side_effect=perform))
            stack.enter_context(patch.object(g,'fetch_reconciliation_selection',return_value=t.SELECTION))
            with self.execution('fetch') as (r,c,root):
                keys={x['sourceKey'] for x in MANIFEST['items']}
                self.assertEqual(observed['calls'],1)
                self.assertFalse(keys & {key for key,_ in c['acquire']})
                self.assertEqual(len(c['acquire']),12)
                self.assertEqual(r['networkRequests'],14) # synthetic remaining 12 source mocks; no live requests
                self.assertEqual(r['preparedBytes'],0);self.assertEqual(c['prepare'],[])
                outcomes=g.expand_outcomes(r['assetOutcomeGroups'],len(self.manifest['assets']))
                for item in MANIFEST['items']:
                    index=self.indices[item['assetId']]
                    self.assertEqual(outcomes[index]['stage'],'held' if blocked else 'retained')
                    if not blocked:self.assertEqual(outcomes[index]['custody'],'verified-original')
                    change=next(x for x in r['changes']if x['assetIndex']==index)
                    self.assertIsNone(change['acquisition']);self.assertIsNone(change['preparation'])
                self.publish_and_reload(r,root,988)
                return deepcopy(r)
    def test_success_intercepts_only_exact_three_and_publishes(self):self.execute()
    def test_blocked_writer_never_falls_back_to_get(self):self.execute(True)
    def test_stage_and_activation_selection_fail_closed(self):
        self.assertIsNone(full.g.fetch_reconciliation_selection('fetch'))
        self.assertIsNone(full.g.fetch_reconciliation_selection('parse'))
        with self.assertRaises(full.g.a.RefreshError):
            full.g._run_global_locked(self.manifest,self.selected,stage='parse',owner_runtime=object(),retained_acceptance_selection=t.SELECTION)

if __name__=='__main__':unittest.main()
