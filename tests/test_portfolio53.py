import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout
import io

from offmenu.refresh import portfolio53 as p
from offmenu.refresh.acceptance import canonical, fingerprint


class Portfolio53Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = b'{"fields":{"price":"price","unit":"unit"}}'
        (self.root/'annotation.json').write_bytes(self.raw)
        self.now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        self.binding = {'country':'LR','sourceId':'authored-source',
            'releaseId':'authored-release','originalAcquiredAt':'2026-10-01T00:00:00Z',
            'metadataValidatedAt':'2026-10-17T00:00:00Z','holds':[],
            'stagingScopeAccepted':True, 'rawAssetReferences':[],
            'nativeUnitsAndBases':{'units':'KG','basis':None},'unknowns':['basis'],
            'applicability':{'dataTypes':['prices/baskets'],'accepted':False},
            'metadata':[{'path':str(self.root/'annotation.json'), 'bytes':len(self.raw),
                'sha256':hashlib.sha256(self.raw).hexdigest(),
                'role':'retained-annotation','selectors':['/fields/price']}],
            'fieldDeclarations':[{'target':'/data/priceLiteral',
                'sourceSelector':'CSV header price; authored row 1',
                'evidenceSelector':'/fields/price',
                'evidenceSha256':hashlib.sha256(self.raw).hexdigest()}]}

    def inspect(self, binding=None, now=None):
        return p.inspect_binding(binding or self.binding, now or self.now)

    def test_valid_metadata_is_not_data_acceptance(self):
        result=self.inspect()
        self.assertEqual(result['outcome'],'valid-metadata-binding')
        self.assertEqual(result['diagnostics'],[])
        self.assertFalse(result['stagingAccepted'])
        self.assertFalse(result['goldAdmitted'])
        self.assertIsNone(result['productionFactory'])
        self.assertEqual(result['nativeUnitsAndBases']['basis'],None)

    def test_all_five_outcomes_isolated_in_one_batch(self):
        good=copy.deepcopy(self.binding)
        missing=copy.deepcopy(good);missing['metadata'][0]['path']=str(self.root/'absent.json')
        held=copy.deepcopy(good);held['holds']=['no-body']
        malformed=copy.deepcopy(good);malformed['metadata'][0]['sha256']='bad'
        stale=copy.deepcopy(good);stale['originalAcquiredAt']='2026-08-01T00:00:00Z'
        result=p.plan([good,missing,held,malformed,stale],now=self.now)
        self.assertEqual([s['outcome'] for s in result['sources']],
                         ['valid-metadata-binding','missing','held','malformed','stale'])
        self.assertEqual(result['sourceBodyReads'],0)
        self.assertEqual(result['networkRequests'],0)

    def test_malformed_binding_object_is_isolated(self):
        result=p.plan([None,self.binding],now=self.now)
        self.assertEqual(result['sources'][0]['diagnostics'],['binding-not-object'])
        self.assertEqual(result['sources'][1]['outcome'],'valid-metadata-binding')

    def test_missing_selector_is_malformed_not_fabricated(self):
        self.binding['fieldDeclarations'][0]['evidenceSelector']='/absent'
        self.assertEqual(self.inspect()['outcome'],'malformed')

    def test_changed_metadata_fails_pin(self):
        (self.root/'annotation.json').write_bytes(b'{"changed":true}')
        result=self.inspect()
        self.assertEqual(result['outcome'],'malformed')
        self.assertNotIn('changed',json.dumps(result))

    def test_duplicate_json_keys_rejected(self):
        raw=b'{"fields":{},"fields":{"price":"price"}}'
        (self.root/'annotation.json').write_bytes(raw)
        self.binding['metadata'][0].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.inspect()['outcome'],'malformed')

    def test_symlink_metadata_rejected(self):
        link=self.root/'alias.json';link.symlink_to(self.root/'annotation.json')
        self.binding['metadata'][0]['path']=str(link)
        self.assertEqual(self.inspect()['outcome'],'malformed')

    def test_metadata_role_cannot_enable_original_body(self):
        self.binding['metadata'][0]['role']='original-csv'
        self.assertEqual(self.inspect()['outcome'],'malformed')

    def test_opaque_raw_reference_never_opened(self):
        self.binding['rawAssetReferences']=[{'path':'/absent/body.csv','sha256':'a'*64}]
        self.assertEqual(self.inspect()['outcome'],'valid-metadata-binding')
        self.assertEqual(self.inspect()['sourceBodyReads'],0)

    def test_validation_age_cannot_reset_original_age(self):
        self.binding['originalAcquiredAt']='2026-08-01T00:00:00Z'
        result=self.inspect()
        self.assertEqual(result['outcome'],'stale')
        self.assertEqual(result['cache']['originalAgeDays'],78)
        self.assertEqual(result['cache']['metadataValidatedAt'],'2026-10-17T00:00:00Z')
        self.assertIsNone(result['cache']['sourceBytesValidatedAt'])
        self.assertFalse(result['cache']['downloadPermitted'])

    def test_30_day_boundary_and_no_force_bypass(self):
        before=datetime(2026,10,30,23,59,59,tzinfo=timezone.utc)
        after=datetime(2026,10,31,tzinfo=timezone.utc)
        self.assertEqual(self.inspect(now=before)['cache']['intent'],'reuse-retained-cache-only')
        result=self.inspect(now=after)
        self.assertEqual(result['outcome'],'stale')
        self.assertFalse(result['cache']['forceSupported'])
        self.assertFalse(result['cache']['downloadPermitted'])

    def test_missing_time_never_uses_mtime(self):
        self.binding['originalAcquiredAt']=None
        self.assertEqual(self.inspect()['cache']['intent'],'unknown-no-download')

    def test_invalid_clock_and_validation_time(self):
        with self.assertRaises(p.RefreshError):p.plan([self.binding],now=datetime(2026,10,18))
        self.binding['metadataValidatedAt']='2026-11-01T00:00:00Z'
        self.assertEqual(self.inspect()['outcome'],'malformed')

    def test_unchanged_content_metadata_noop_across_clock_days(self):
        first=p.plan([self.binding],now=self.now)
        second=p.plan([self.binding],now=self.now+timedelta(days=1),previous=first)
        self.assertEqual(first['bindingSha256'],second['bindingSha256'])
        self.assertEqual(second['replay'],'verified-metadata-no-op')
        first['sources'][0]['declarations']=[]
        with self.assertRaises(p.RefreshError):p.plan([self.binding],now=self.now,previous=first)

    def fixture_bundle(self):
        bundle=self.root/'bundle';bundle.mkdir()
        for name,raw in [('fixture.json',b'{"price":"001.20","unit":"KG"}'),
                         ('rights.json',b'{"scope":"authored-fixture-only"}'),
                         ('scope.json',b'{"expectedRecords":1}')]:
            (bundle/name).write_bytes(raw)
        digest=hashlib.sha256((bundle/'fixture.json').read_bytes()).hexdigest()
        row=p.fixture_record(digest,'2026-10-01T00:00:00Z')
        candidate=self.root/'candidate.jsonl';candidate.write_bytes(canonical([row])+b'\n')
        pins=[{'path':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
              for f in sorted(bundle.iterdir())]
        manifest={'sourceId':'worker53-fixture','releaseId':'authored-v1',
            'acquiredAt':'2026-10-01T00:00:00Z','normalizedRecords':1,
            'candidateSha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
            'candidateBytes':candidate.stat().st_size,'inputFiles':pins,
            'rightsEvidenceSha256':next(x['sha256'] for x in pins if x['path']=='rights.json'),
            'scopeEvidenceSha256':next(x['sha256'] for x in pins if x['path']=='scope.json')}
        return bundle,candidate,manifest,row

    def test_shared_qualification_and_origin_validator_positive_fixture(self):
        bundle,candidate,manifest,row=self.fixture_bundle()
        result=p.qualify_authored_fixture(bundle,candidate,manifest)
        self.assertTrue(result['qualified'],result['errors'])
        self.assertTrue(result['fixture'])
        self.assertEqual(row['data']['priceLiteral'],'001.20')
        self.assertIsNone(row['data']['basis'])

    def test_shared_qualification_keeps_explicit_hold(self):
        bundle,candidate,manifest,_=self.fixture_bundle()
        result=p.qualify_authored_fixture(bundle,candidate,manifest,held=True)
        self.assertFalse(result['qualified'])
        self.assertIn('source-held',result['errors'])

    def test_fixture_input_is_independently_pinned_not_retrusted(self):
        bundle,candidate,manifest,_=self.fixture_bundle()
        (bundle/'fixture.json').write_bytes(b'{"price":"999.00","unit":"KG"}')
        result=p.qualify_authored_fixture(bundle,candidate,manifest)
        self.assertFalse(result['qualified'])
        self.assertIn('input-custody-mismatch',result['errors'])

    def test_actual_field_selector_and_literal_drift_fail(self):
        bundle,candidate,manifest,row=self.fixture_bundle()
        row['provenance']['fieldOrigins']['/data/priceLiteral']['sourceField']='usdprice'
        row['data']['priceLiteral']='1.2'
        candidate.write_bytes(canonical([row])+b'\n')
        manifest.update(candidateSha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                        candidateBytes=candidate.stat().st_size)
        result=p.qualify_authored_fixture(bundle,candidate,manifest)
        self.assertIn('fixture-literal-mismatch',result['errors'])
        self.assertIn('fixture-selector-mismatch',result['errors'])


class Portfolio53CorrectionTests(unittest.TestCase):
    def setUp(self):
        Portfolio53Tests.setUp(self)

    def cli(self, path):
        return subprocess.run([sys.executable, '-B', '-m',
            'offmenu.refresh.portfolio53', '--now', '2026-10-18T00:00:00Z',
            '--previous-report', str(path)], capture_output=True, timeout=3)

    def test_f1_fifo_without_writer_rejected_by_real_cli(self):
        fifo=self.root/'previous.json';os.mkfifo(fifo)
        result=self.cli(fifo)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr,b'previous-report-not-regular\n')
        self.assertEqual(result.stdout,b'')

    def test_f1_other_invalid_replay_ingress(self):
        large=self.root/'large.json';large.write_bytes(b'x'*(p.MAX_METADATA+1))
        link=self.root/'link.json';link.symlink_to(self.root/'annotation.json')
        for path,code in [(self.root,'previous-report-not-regular'),
                          (large,'previous-report-too-large'),
                          (link,'symlink-path-rejected')]:
            with self.subTest(code=code):
                result=self.cli(path)
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stderr,(code+'\n').encode())

    def test_f1_single_descriptor_and_metadata_pin_remain_checked(self):
        real_open=p.os.open
        expected=self.binding['metadata'][0]
        with mock.patch.object(p.os,'open',wraps=real_open) as opened:
            raw=p._read_regular(expected['path'],expected=expected)
        self.assertEqual(opened.call_count,1)
        self.assertEqual(raw,self.raw)
        with self.assertRaisesRegex(p.RefreshError,'metadata-pin-mismatch'):
            p._read_regular(expected['path'],expected={**expected,'sha256':'a'*64})

    def test_f1_file_replaced_after_read_is_rejected(self):
        path=self.root/'annotation.json';real_fdopen=p.os.fdopen
        class ReplacedOnRead:
            def __init__(self,fd,mode,**kwargs):self.stream=real_fdopen(fd,mode,**kwargs)
            def __enter__(self):return self
            def fileno(self):return self.stream.fileno()
            def read(self,limit):
                raw=self.stream.read(limit)
                replacement=path.with_name('replacement.json')
                replacement.write_bytes(raw);replacement.replace(path)
                return raw
            def __exit__(self,*args):self.stream.close()
        with mock.patch.object(p.os,'fdopen',side_effect=ReplacedOnRead):
            with self.assertRaisesRegex(p.RefreshError,'metadata-changed-during-read'):
                p._read_regular(path)

    def test_f1_valid_regular_replay_preserves_noop(self):
        config=self.root/'config.json';config.write_text(json.dumps({'sources':[self.binding]}))
        previous=p.plan([self.binding],now=self.now)
        path=self.root/'previous.json';path.write_text(json.dumps(previous))
        output=io.StringIO()
        with mock.patch.object(p,'load_catalogue',return_value={'sources':[self.binding]}),redirect_stdout(output):
            p.main(['--now','2026-10-18T00:00:00Z','--previous-report',str(path)])
        result=json.loads(output.getvalue())
        self.assertEqual(result['replay'],'verified-metadata-no-op')
        self.assertEqual(result['bindingSha256'],previous['bindingSha256'])

    def test_f2_exact_10000_depth_metadata_keeps_healthy_peer(self):
        raw=b'['*10000+b'0'+b']'*10000
        deep=self.root/'deep.json';deep.write_bytes(raw)
        bad=copy.deepcopy(self.binding)
        bad['metadata'][0].update(path=str(deep),bytes=len(raw),
                                  sha256=hashlib.sha256(raw).hexdigest())
        result=p.plan([bad,self.binding],now=self.now)
        self.assertEqual(result['sources'][0]['outcome'],'malformed')
        self.assertEqual(result['sources'][0]['diagnostics'],['metadata-json-depth-exceeded'])
        self.assertEqual(result['sources'][1]['outcome'],'valid-metadata-binding')
        self.assertEqual(result['sourceBodyReads'],0)

    def test_f2_deep_replay_input_has_fixed_cli_diagnostic(self):
        path=self.root/'previous.json';path.write_bytes(b'['*10000+b'0'+b']'*10000)
        result=self.cli(path)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr,b'previous-report-json-depth-exceeded\n')

    def test_p2_every_supplied_previous_report_is_validated_before_metadata_reads(self):
        bad_reports = ({}, [], [{}], {'sources': []}, 'previous', 1, False)
        with mock.patch.object(p, 'inspect_binding', side_effect=AssertionError('invalid previous report read metadata')):
            for previous in bad_reports:
                with self.subTest(previous=previous):
                    with self.assertRaisesRegex(p.RefreshError, '^previous-report-invalid$'):
                        p.plan([self.binding], now=self.now, previous=previous)

    def test_p2_malformed_previous_sources_and_cache_have_fixed_errors(self):
        previous = p.plan([self.binding], now=self.now)
        for mutate in (lambda v: v.update(sources={}),
                       lambda v: v.update(sources=[None]),
                       lambda v: v['sources'][0].update(cache=[])):
            bad = copy.deepcopy(previous)
            mutate(bad)
            with self.subTest(previous=bad):
                with self.assertRaisesRegex(p.RefreshError, '^previous-report-invalid$'):
                    p.plan([self.binding], now=self.now, previous=bad)

    def test_p2_cli_rejects_non_reports_without_traceback_or_metadata_reads(self):
        from contextlib import redirect_stderr
        path = self.root / 'previous.json'
        for raw in (b'null', b'{}', b'[]', b'[{}]', b'"previous"', b'false', b'{"sources":{}}'):
            path.write_bytes(raw)
            out, err = io.StringIO(), io.StringIO()
            with self.subTest(raw=raw), mock.patch.object(p, 'load_catalogue', return_value={'sources': []}), \
                    redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit) as stopped:
                    p.main(['--now', '2026-10-18T00:00:00Z', '--previous-report', str(path)])
                self.assertEqual(stopped.exception.code, 2)
            self.assertEqual(err.getvalue(), 'previous-report-invalid\n')
            self.assertEqual(out.getvalue(), '')

    def test_p2_decoded_json_depth_is_explicit_below_decoder_recursion_limit(self):
        for depth in (64, 65):
            raw = b'[' * depth + b'0' + b']' * depth
            path = self.root / 'bounded-depth.json'
            path.write_bytes(raw)
            bad = copy.deepcopy(self.binding)
            bad['metadata'][0].update(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            result = p.plan([bad, self.binding], now=self.now)
            if depth == 65:
                self.assertEqual(result['sources'][0]['diagnostics'], ['metadata-json-depth-exceeded'])
            else:
                self.assertNotIn('metadata-json-depth-exceeded', result['sources'][0]['diagnostics'])
            self.assertEqual(result['sources'][1]['outcome'], 'valid-metadata-binding')
            self.assertEqual(result['sourceBodyReads'], 0)

    def test_p2_deep_previous_has_fixed_depth_error(self):
        previous = p.plan([self.binding], now=self.now)
        nested = 0
        for _ in range(65): nested = [nested]
        previous['sources'][0]['extra'] = nested
        with self.assertRaisesRegex(p.RefreshError, '^previous-report-json-depth-exceeded$'):
            p.plan([self.binding], now=self.now, previous=previous)


if __name__=='__main__':unittest.main()
