import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from offmenu.portfolio40.binding import assess
from offmenu.refresh.adapter_mapping import retained_adapters
from offmenu.refresh.core import canonical, strict_json


def fixture():
    adapter = retained_adapters()[0]
    source, release = adapter['sourceId'], adapter['releaseId']
    pin = {'path': 'synthetic/evidence.json', 'sha256': 'a' * 64}
    binding = {'sourceId': source, 'releaseId': release, 'country': 'HT',
               'types': ['nutrition'], 'receipt': pin, 'qualification': pin,
               'scopeEvidence': pin, 'acquiredAt': '2026-10-01T00:00:00Z',
               'inputFiles': [{'path': 'synthetic/input.json', 'bytes': 3, 'sha256': 'b' * 64}],
               'sharedHandler': {'sourceId': source, 'releaseId': release},
               'holds': [], 'use': {'status': 'reviewed-private-transform',
                                    'decision': pin, 'attribution': 'Authored fixture only'},
               'fields': {'amount': {'nativeUnit': 'synthetic-unit',
                                     'nativeBasis': 'synthetic-basis',
                                     'origin': {'kind': 'source', 'sourceId': source,
                                                'releaseId': release,
                                                'inputPath': 'synthetic/input.json',
                                                'inputSha256': 'b' * 64,
                                                'sourceRecordId': '0001',
                                                'sourceField': 'synthetic/column-A'}}}}
    snap = {k: copy.deepcopy(binding[k]) for k in ('sourceId','releaseId','inputFiles','receipt','acquiredAt')}
    snap['validatedAt'] = '2026-10-17T00:00:00Z'
    return binding, {source: snap}


class PortfolioBindingTests(unittest.TestCase):
    def run_binding(self, b, snapshots, **kw):
        return assess([b], snapshots, now=kw.get('now', '2026-10-18T00:00:00Z'),
                      previous=kw.get('previous'))['reports'][0]

    def test_valid_metadata_cannot_authorize_body_or_gold(self):
        b, s = fixture(); r = self.run_binding(b,s)
        self.assertEqual(r['status'], 'metadata-ready')
        self.assertFalse(r['bodyExecutionAllowed']); self.assertFalse(r['stagingAccepted'])
        self.assertFalse(r['goldAdmitted'])

    def test_missing_snapshot_is_isolated(self):
        b,s=fixture(); self.assertEqual(self.run_binding(b,{})['status'],'missing')
        s[b['sourceId']] = []
        self.assertEqual(self.run_binding(b,s)['status'],'missing')

    def test_hold_precedes_missing_policy_and_staleness(self):
        b,s=fixture(); b['holds']=['actual-denied-operation']; b['use']['status']='unknown'
        r=self.run_binding(b,s,now='2026-12-01T00:00:00Z')
        self.assertEqual(r['status'],'held'); self.assertEqual(r['holds'],b['holds'])
        missing=self.run_binding(b,{})
        self.assertEqual(missing['status'],'held'); self.assertEqual(missing['holds'],b['holds'])

    def test_malformed_does_not_block_other_sources(self):
        b,s=fixture(); result=assess([None,b],s,now='2026-10-18T00:00:00Z')
        self.assertEqual([r['status'] for r in result['reports']],['malformed','metadata-ready'])

    def test_malformed_handler_preserves_valid_neighbor_report(self):
        good, snapshots = fixture()
        expected = self.run_binding(good, snapshots)
        for handler in [[], 42, 'handler', {}, {'sourceId': []}]:
            with self.subTest(handler=handler):
                bad = copy.deepcopy(good)
                bad['sourceId'] = 'authored-malformed-neighbor'
                bad['sharedHandler'] = handler
                bad_snap = copy.deepcopy(snapshots[good['sourceId']])
                bad_snap['sourceId'] = bad['sourceId']
                result = assess([bad, good], {bad['sourceId']: bad_snap, **snapshots},
                                now='2026-10-18T00:00:00Z')['reports']
                self.assertEqual(result[0]['status'], 'malformed')
                self.assertEqual(result[0]['diagnostics'], ['binding-shared-handler-invalid'])
                self.assertEqual(result[1], {**expected, 'bindingIndex': 1})

    def cli_metadata(self, root):
        b, snapshots = fixture()
        for name, value in [('bindings', {'bindings': [b]}),
                            ('snapshots', snapshots), ('previous', {})]:
            (root / name).write_bytes(canonical(value))
        return [sys.executable, '-m', 'offmenu.portfolio40.binding',
                '--bindings', str(root / 'bindings'), '--snapshots', str(root / 'snapshots'),
                '--previous', str(root / 'previous'), '--now', '2026-10-18T00:00:00Z']

    def test_cli_regular_metadata_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(self.cli_metadata(Path(tmp)), capture_output=True, timeout=3)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, b'')
        report = strict_json(proc.stdout)
        self.assertEqual(report['reports'][0]['status'], 'metadata-ready')
        self.assertEqual(report['acceptedRecords'], 0)

    def test_cli_fifo_metadata_is_rejected_without_writer(self):
        for name in ['bindings', 'snapshots', 'previous']:
            with self.subTest(argument=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                command = self.cli_metadata(root)
                (root / name).unlink()
                os.mkfifo(root / name)
                proc = subprocess.run(command, capture_output=True, timeout=3)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(strict_json(proc.stdout), {'error': 'portfolio-metadata-invalid'})
                self.assertEqual(proc.stderr, b'')

    def test_cli_metadata_size_bound_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = self.cli_metadata(root)
            (root / 'bindings').write_bytes(b' ' * (1024 * 1024 + 1))
            proc = subprocess.run(command, capture_output=True, timeout=3)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(strict_json(proc.stdout), {'error': 'portfolio-metadata-invalid'})
        self.assertEqual(proc.stderr, b'')

    def test_stale_acquisition_not_reset_by_recent_validation(self):
        b,s=fixture(); s[b['sourceId']]['validatedAt']='2026-11-01T00:00:00Z'
        r=self.run_binding(b,s,now='2026-11-01T00:00:00Z')
        self.assertEqual(r['status'],'stale-input')
        self.assertFalse(r['cache']['freshnessUsesValidationTime'])
        self.assertEqual(r['cache']['decision'],'conditional-revalidation-required')

    def test_under_30_days_and_exact_boundary(self):
        b,s=fixture()
        a=self.run_binding(b,s,now='2026-10-30T23:59:59Z')
        self.assertEqual(a['cache']['decision'],'reuse-recorded-cache-zero-download')
        self.assertEqual(self.run_binding(b,s,now='2026-10-31T00:00:00Z')['status'],'stale-input')

    def test_null_acquisition_is_not_validation_age(self):
        b,s=fixture(); b['acquiredAt']=None; s[b['sourceId']]['acquiredAt']=None
        r=self.run_binding(b,s); self.assertEqual(r['status'],'missing')
        self.assertIn('original-acquisition-time-missing',r['missing'])

    def test_literal_units_ids_and_input_are_unchanged(self):
        b,s=fixture(); before=canonical([b,s]); r=self.run_binding(b,s)
        self.assertEqual(canonical([b,s]),before)
        self.assertEqual(r['fieldDeclarations']['amount']['origin']['sourceRecordId'],'0001')

    def test_missing_native_basis_and_origin_are_named(self):
        b,s=fixture(); b['fields']['amount']['nativeBasis']=None; b['fields']['amount']['origin']=None
        r=self.run_binding(b,s); self.assertEqual(r['status'],'missing')
        self.assertIn('field-nativeBasis-unknown:/data/amount',r['missing'])
        self.assertIn('field-origin-unresolved:/data/amount',r['missing'])

    def test_foreign_origin_uses_shared_validator(self):
        b,s=fixture(); b['fields']['amount']['origin']['inputSha256']='c'*64
        self.assertIn('field-origin-input-pin-mismatch',self.run_binding(b,s)['diagnostics'])

    def test_snapshot_source_release_and_content_drift(self):
        for key,value in [('releaseId','wrong'),('sourceId','wrong'),('inputFiles',[])]:
            b,s=fixture(); s[b['sourceId']][key]=value
            self.assertEqual(self.run_binding(b,s)['status'],'malformed')

    def test_safe_relative_input_paths_and_digest_syntax(self):
        for path in ['/absolute','../parent','x//y','x\\y','x:stream']:
            b,s=fixture(); b['inputFiles'][0]['path']=path
            self.assertEqual(self.run_binding(b,s)['diagnostics'],['binding-input-pin-invalid'])
        b,s=fixture(); b['receipt']['sha256']='A'*64
        self.assertEqual(self.run_binding(b,s)['status'],'malformed')

    def test_noop_identity_ignores_validation_clock_but_detects_binding_change(self):
        b,s=fixture(); r=self.run_binding(b,s); previous={b['sourceId']:r['replayIdentity']}
        s[b['sourceId']]['validatedAt']='2026-10-18T00:00:00Z'
        self.assertEqual(self.run_binding(b,s,previous=previous)['artifactAction'],'no-op')
        b['fields']['amount']['nativeUnit']='different'
        self.assertEqual(self.run_binding(b,s,previous=previous)['artifactAction'],'binding-changed')

    def test_duplicate_source_rejected(self):
        b,s=fixture(); r=assess([b,b],s,now='2026-10-18T00:00:00Z')
        self.assertEqual(r['reports'][1]['diagnostics'],['binding-duplicate-source'])

    def test_no_actual_adapter_inferred_from_publisher_or_country(self):
        b,s=fixture(); b['sharedHandler']=None
        self.assertIn('shared-handler-unbound',self.run_binding(b,s)['missing'])
        b,s=fixture(); b['sharedHandler']['releaseId']='not-this-release'
        self.assertIn('shared-handler-source-mismatch',self.run_binding(b,s)['diagnostics'])

    def test_future_acquisition_and_bad_utc_clock_fail_closed(self):
        b,s=fixture(); b['acquiredAt']='2026-12-01T00:00:00Z'; s[b['sourceId']]['acquiredAt']=b['acquiredAt']
        self.assertIn('acquisition-in-future',self.run_binding(b,s)['diagnostics'])
        with self.assertRaises(ValueError): self.run_binding(b,s,now='2026-10-18')

    def test_no_io_or_network_during_assessment(self):
        b,s=fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')), patch('socket.socket',side_effect=AssertionError('unexpected network')):
            self.assertEqual(self.run_binding(b,s)['status'],'metadata-ready')

    def test_unknown_not_empty_string_and_nonfinite_never_coerced(self):
        b,s=fixture(); b['fields']['amount']['nativeUnit']=float('nan')
        self.assertEqual(self.run_binding(b,s)['status'],'malformed')

    def test_actual_portfolio_descriptors_remain_held_without_original_access(self):
        root=Path(__file__).resolve().parents[1]/'docs/research/portfolio40'
        bindings=strict_json((root/'bindings.json').read_bytes())['bindings']
        snapshots=strict_json((root/'snapshots.json').read_bytes())
        with patch('builtins.open',side_effect=AssertionError('original read')), patch('socket.socket',side_effect=AssertionError('network')):
            report=assess(bindings,snapshots,now='2026-10-18T00:00:00Z')
        self.assertEqual(len(report['reports']),9)
        self.assertTrue(all(r['status']=='held' for r in report['reports']))
        self.assertEqual({r['country'] for r in report['reports']},{'HT','HU','ID','IE'})
        self.assertEqual(report['acceptedRecords'],0)
        self.assertTrue(any('actual-FSAI-403-no-retry-or-reroute' in r['holds'] for r in report['reports']))

    def test_snapshot_bool_does_not_equal_integer_asset_size(self):
        b,s=fixture(); b['inputFiles'][0]['bytes']=1
        s[b['sourceId']]['inputFiles'][0]['bytes']=True
        self.assertEqual(self.run_binding(b,s)['status'],'malformed')


if __name__ == '__main__':
    unittest.main()
