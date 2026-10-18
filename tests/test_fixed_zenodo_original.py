"""Synthetic fixtures only. No public source body or network access."""
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
m = module('fixed_zenodo_fixture', 'acquire-fixed-zenodo.py')
dispatch = module('fixed_zenodo_dispatch', 'dispatch-foo-job.py')

class Response:
    def __init__(self, body, status=200, headers=None, fail_after=None):
        self.body = io.BytesIO(body); self.status = status
        self.headers = headers or {'Content-Length': str(len(body))}
        self.closed = False; self.fail_after = fail_after; self.reads = 0
    def read(self, size):
        self.reads += 1
        if self.fail_after and self.reads > self.fail_after:
            raise TimeoutError('synthetic')
        return self.body.read(min(size, 10) if self.fail_after else size)
    def close(self): self.closed = True

class Transport:
    def __init__(self, response): self.response = response; self.calls = []
    def __call__(self, spec, headers, *, deadline):
        self.calls.append((spec, headers, deadline)); return self.response

class FixedOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.body = b'Name;Ingredients;Instructions\r\nsynthetic;fixture;only\r\n'
        self.selected = {'sourceKey': m.SOURCE_KEY, 'url': m.URL,
            'expectedMD5': hashlib.md5(self.body).hexdigest(),
            'aliases': ['https://zenodo.org/records/15169428/files/dataset.csv?download=1',
                        'next.culinary-recipes-zenodo-v1.1', '10.5281/zenodo.15169428'],
            'release': 'fixture-v1', 'headerFields': ['Name','Ingredients','Instructions'],
            'rightsReference': 'https://example.test/fixture-rights', 'downstreamHolds': ['fixture-private-only']}
        self.stack = ExitStack()
        for key, value in [('OUTPUT',self.root),('LEGACY_CACHE',self.root/'legacy-missing'),
                           ('EXPECTED_BYTES',len(self.body)),('EXPECTED_MD5',hashlib.md5(self.body).hexdigest()),
                           ('GUARD',0),('MAX_BYTES',1024)]:
            self.stack.enter_context(patch.object(m,key,value))
        self.stack.enter_context(patch('socket.create_connection', side_effect=AssertionError('live network forbidden')))
    def tearDown(self): self.stack.close(); self.temp.cleanup()
    def run_source(self, response=None):
        transport = Transport(response or Response(self.body))
        report = m.run_selected(self.selected, transport=transport)
        return report, transport
    def claim_path(self): return self.root/'collection/intents'/(m.sha(m.URL.encode())+'.json')
    def reservation_path(self): return self.root/'collection'/('reservation-'+m.sha(m.URL.encode())+'.bin')
    def current(self):
        return self.root/'collection/source-cache/requests'/m.sha(m.canonical(m.source_spec(self.selected).identity()))/'current.json'

    def test_one_get_existing_engine_and_complete_integrity(self):
        result, transport = self.run_source()
        self.assertEqual(result['status'],'verified-private-original')
        self.assertEqual(result['network'],{'requests':1,'bodyBytesRead':len(self.body)})
        self.assertEqual(len(transport.calls),1)
        self.assertEqual(transport.calls[0][1],{'Accept-Encoding':'identity'})
        self.assertGreater(transport.calls[0][2],time.monotonic())
        self.assertTrue(result['capacity']['physicalReservationEstablished'])
        self.assertFalse(self.reservation_path().exists())
        self.assertEqual(json.loads(self.claim_path().read_text())['state'],'verified')
        self.assertTrue(m.summary_report(result)['publisherMD5Verified'])

    def test_immediate_reuse_preserves_original_clock_and_zero_get(self):
        first, _ = self.run_source()
        second, transport = self.run_source()
        self.assertEqual(second['cacheStatus'],'reused-fresh')
        self.assertEqual(second['network'],{'requests':0,'bodyBytesRead':0})
        self.assertFalse(transport.calls)
        self.assertEqual(first['validation']['originalAcquiredAt'],second['validation']['originalAcquiredAt'])

    def test_cache_reuses_at_29_days_and_never_automatically_refetches_at_31(self):
        now=datetime.now(timezone.utc)
        class TimedEngine(m.CachedAcquirer):
            age=0
            def acquire(self,*args,**kwargs):
                return super().acquire(*args,now=now+timedelta(days=self.age),**kwargs)
        first=Transport(Response(self.body))
        result=m.run_selected(self.selected,engine=TimedEngine,transport=first)
        self.assertEqual(result['status'],'verified-private-original')
        TimedEngine.age=29; second=Transport(Response(self.body))
        result=m.run_selected(self.selected,engine=TimedEngine,transport=second)
        self.assertEqual(result['cacheStatus'],'reused-fresh'); self.assertFalse(second.calls)
        TimedEngine.age=31; third=Transport(Response(self.body))
        result=m.run_selected(self.selected,engine=TimedEngine,transport=third)
        self.assertEqual(result['errorCode'],'cache-stale'); self.assertFalse(third.calls)

    def test_post_transfer_deadline_failure_preserves_consumed_bytes(self):
        with patch.object(m,'validate_original',side_effect=m.RefreshError('operation-deadline-exceeded')):
            result,_=self.run_source()
        self.assertEqual(result['errorCode'],'operation-deadline-exceeded')
        self.assertEqual(m.summary_report(result)['networkBytesRead'],len(self.body))

    def test_denial_no_retry_and_sticky_failed_claim(self):
        result, transport = self.run_source(Response(b'',status=403,headers={'Content-Length':'0'}))
        self.assertEqual(result['errorCode'],'source-response-not-permitted')
        self.assertEqual(len(transport.calls),1)
        self.assertEqual(result['network']['bodyBytesRead'],0)
        again, second = self.run_source()
        self.assertEqual(again['errorCode'],'source-claim-uncertain')
        self.assertFalse(second.calls)

    def test_redirect_is_never_followed(self):
        result, transport = self.run_source(Response(b'',status=302,headers={'Location':'https://example.test/other'}))
        self.assertEqual(result['errorCode'],'source-response-not-permitted')
        self.assertEqual(len(transport.calls),1)

    def test_retryable_503_still_only_one_get(self):
        result, transport = self.run_source(Response(b'',status=503))
        self.assertEqual(result['errorCode'],'acquisition-retries-exhausted')
        self.assertEqual(len(transport.calls),1)

    def test_failure_retains_consumed_byte_count(self):
        result, transport = self.run_source(Response(self.body,fail_after=1))
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['network'],{'requests':1,'bodyBytesRead':10})
        self.assertEqual(m.summary_report(result)['networkBytesRead'],10)
        self.assertEqual(len(transport.calls),1)

    def test_publisher_no_store_wins(self):
        result, _ = self.run_source(Response(self.body,headers={'Cache-Control':'no-store'}))
        self.assertEqual(result['errorCode'],'response-retention-not-approved')
        self.assertEqual(result['network']['bodyBytesRead'],0)

    def test_length_mismatch_is_not_verified(self):
        result, _ = self.run_source(Response(self.body[:-2]))
        self.assertEqual(result['errorCode'],'source-length-mismatch')
        self.assertFalse(m.summary_report(result)['headerVerified'])

    def test_md5_mismatch_keeps_failed_custody_claim(self):
        altered = self.body.replace(b'fixture',b'changed')
        result, _ = self.run_source(Response(altered))
        self.assertEqual(result['errorCode'],'source-md5-mismatch')
        self.assertEqual(json.loads(self.claim_path().read_text())['state'],'failed-no-retry')

    def test_header_mismatch_is_not_semantic_acceptance(self):
        result, _ = self.run_source(Response(self.body.replace(b'Name',b'Fake')))
        self.assertEqual(result['errorCode'],'source-header-mismatch')
        self.assertFalse(m.summary_report(result)['normalizedOrGoldAdmitted'])

    def test_existing_uncertain_claim_is_not_overwritten(self):
        path=self.claim_path();path.parent.mkdir(parents=True);raw=b'{"owner":12,"state":"active"}\n';path.write_bytes(raw)
        result, transport=self.run_source()
        self.assertEqual(result['errorCode'],'source-claim-uncertain')
        self.assertEqual(path.read_bytes(),raw);self.assertFalse(transport.calls)

    def test_existing_partial_refuses_get(self):
        path=self.current().parent/'body.partial';path.parent.mkdir(parents=True);path.write_bytes(b'partial')
        result, transport=self.run_source()
        self.assertEqual(result['errorCode'],'source-partial-or-recovery-present')
        self.assertEqual(path.read_bytes(),b'partial');self.assertFalse(transport.calls)

    def test_existing_reservation_is_not_released(self):
        path=self.reservation_path();path.parent.mkdir(parents=True);path.write_bytes(b'unknown')
        result, transport=self.run_source()
        self.assertEqual(result['errorCode'],'reservation-already-present')
        self.assertEqual(path.read_bytes(),b'unknown');self.assertFalse(transport.calls)

    def test_alias_in_alternate_cache_blocks_duplicate_get(self):
        for alias in self.selected['aliases']+[m.URL,self.selected['expectedMD5'],'md5:'+self.selected['expectedMD5'],'15169428']:
            with self.subTest(alias=alias):
                root=self.root/'legacy-missing';root.mkdir(exist_ok=True)
                (root/'current.json').write_text(json.dumps({'source':alias}))
                result, transport=self.run_source()
                self.assertEqual(result['errorCode'],'known-exact-source-alternate-cache')
                self.assertFalse(transport.calls)

    def test_key_only_claim_registry_blocks_before_get_without_modification(self):
        for key in [m.SOURCE_KEY,m.URL,self.selected['expectedMD5'],*self.selected['aliases']]:
            with self.subTest(key=key):
                path=self.root/'legacy-missing/claims.json';path.parent.mkdir(exist_ok=True)
                raw=json.dumps({key:{'owner':12,'state':'active'}}).encode();path.write_bytes(raw)
                result,transport=self.run_source()
                self.assertEqual(result['errorCode'],'known-exact-source-alternate-cache')
                self.assertFalse(transport.calls);self.assertEqual(path.read_bytes(),raw)

    def test_recognized_top_level_source_claim_catalogue_blocks(self):
        path=self.root/'legacy-missing/source-claims.json';path.parent.mkdir(exist_ok=True)
        raw=json.dumps({'sourceKey':m.SOURCE_KEY,'owner':12,'state':'active'}).encode();path.write_bytes(raw)
        result,transport=self.run_source()
        self.assertEqual(result['errorCode'],'known-exact-source-alternate-cache')
        self.assertFalse(transport.calls);self.assertEqual(path.read_bytes(),raw)

    def test_unknown_native_scope_is_disclosed_without_invented_clearance(self):
        result, _=self.run_source()
        self.assertFalse(result['nativeClaimCoverageExhaustive'])
        self.assertFalse(result['unknownClaimsAssumedEmpty'])
        self.assertGreater(result['claimCoverage']['missingRoots'],0)

    def test_capacity_floor_is_not_double_added_or_unknowns_zeroed(self):
        with patch.object(m,'GUARD',100),patch.object(m,'capacity',return_value=100):
            result, transport=self.run_source()
        self.assertEqual(result['errorCode'],'capacity-planning-bound-not-protected')
        self.assertFalse(transport.calls)

    def test_physical_allocation_failure_stops_before_get(self):
        with patch.object(m.os,'posix_fallocate',side_effect=OSError('synthetic allocation')):
            result, transport=self.run_source()
        self.assertEqual(result['status'],'blocked');self.assertFalse(transport.calls)
        self.assertFalse(self.reservation_path().exists())

    def test_claim_write_failure_retains_network_meter(self):
        original=m.atomic_json
        def failed(path,value):
            if Path(path)==self.claim_path():raise OSError('synthetic claim failure')
            return original(path,value)
        with patch.object(m,'atomic_json',side_effect=failed):result,_=self.run_source()
        summary=m.summary_report(result)
        self.assertEqual(summary['networkRequests'],1)
        self.assertEqual(summary['networkBytesRead'],len(self.body))
        self.assertEqual(summary['errorCode'],'claim-state-write-failed')
        self.assertFalse(summary['publisherMD5Verified'])

    def test_reservation_release_failure_retains_network_meter(self):
        with patch.object(m,'release_own_reservation',side_effect=OSError('synthetic release failure')):
            result,_=self.run_source()
        summary=m.summary_report(result)
        self.assertEqual(summary['errorCode'],'reservation-release-failed')
        self.assertEqual(summary['networkBytesRead'],len(self.body))
        self.assertTrue(self.reservation_path().exists())

    def test_result_write_failure_retains_network_meter(self):
        with patch.object(m,'write_immutable',side_effect=OSError('synthetic receipt failure')):
            result,_=self.run_source()
        summary=m.summary_report(result)
        self.assertEqual(summary['errorCode'],'result-write-failed')
        self.assertEqual(summary['networkRequests'],1)
        self.assertEqual(summary['networkBytesRead'],len(self.body))
        self.assertFalse(summary['detailPersisted'])

    def test_shared_deadline_expiration_prevents_get(self):
        transport=Transport(Response(self.body))
        result=m.run_selected(self.selected,transport=transport,deadline=time.monotonic()-1)
        self.assertEqual(result['errorCode'],'operation-deadline-exceeded')
        self.assertFalse(transport.calls)

    def test_summary_is_closed_and_typed(self):
        result,_=self.run_source();summary=m.summary_report(result)
        for key,value in [('networkRequests',False),('nativeClaimCoverageExhaustive',True),
                          ('wholeOperationSeconds',901),('sourceKey','different'),('detailPersisted','yes')]:
            with self.assertRaises(ValueError):m.sanitize_report(dict(summary,**{key:value}))
        with self.assertRaises(ValueError):m.sanitize_report(dict(summary,privateText='bad'))

    def test_request_cannot_select_url_command_or_budget(self):
        req={'schemaVersion':1,'jobId':'fixture-zenodo','profile':'zenodo-private-original'}
        self.assertEqual(dispatch.parse_request(json.dumps(req).encode()),req)
        for key in ['url','command','budget','path']:
            with self.assertRaises(dispatch.JobError):dispatch.parse_request(json.dumps(dict(req,**{key:'bad'})).encode())
        steps=dispatch.profile_steps(req['profile'],ROOT)
        self.assertEqual([x[0] for x in steps],['readiness','zenodo-original-tests','zenodo-private-original'])

    def test_dispatch_has_fixed_930_second_outer_watchdog(self):
        detail,_=self.run_source();summary=m.summary_report(detail)
        summary.update(verifiedBytes=110013794,networkBytesRead=110013794)
        evidence=dispatch.safe_evidence(json.dumps(summary).encode())
        value={'status':'passed','exitCode':0,'durationSeconds':0,'evidence':evidence}
        with patch.object(dispatch,'run_child',return_value=value) as called:
            self.assertEqual(dispatch.run_step('zenodo-private-original',[],ROOT)['status'],'passed')
        called.assert_called_once_with([],ROOT,timeout=930)

    def test_unexpected_arguments_never_start_collection(self):
        with patch.object(m,'load_selection') as load,patch('sys.stdout',io.StringIO()):
            self.assertEqual(m.main(['--url','https://bad.test']),2)
        load.assert_not_called()

    def test_input_pins_and_existing_snapshot_validate_without_network(self):
        # Production metadata only, independent from reduced synthetic transfer bounds.
        with patch.object(m,'EXPECTED_BYTES',110013794),patch.object(m,'EXPECTED_MD5','986efafad65c7969fde13a46d2defba0'),\
             patch.object(m,'MAX_BYTES',134217728),patch.object(m,'GUARD',88418025472):
            selected=m.load_selection()
        self.assertEqual(selected['sourceKey'],m.SOURCE_KEY)
        self.assertFalse(selected['coordinatorIntent']['nativeClaimsExhaustive'])

if __name__=='__main__':unittest.main()
