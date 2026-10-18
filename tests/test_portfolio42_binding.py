"""Authored metadata fixtures only; no retained release processing or sockets."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import io
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio42 as p
from offmenu.refresh import acceptance as q
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.serialization import encode_records

ACQUIRED = '2026-01-01T00:00:00Z'
NOW = '2026-01-02T00:00:00Z'


def fixture():
    # Invented strings/URLs, no copied food observations or national document.
    return {'country': 'IN', 'recordCount': 1,
            'source': {'path': 'authored/index.jsonl.gz', 'sha256': 'b' * 64},
            'selector': {'logicalLine': 47, 'index': 0},
            'record': {'schemaVersion': '1.0', 'kind': 'sourceAssertion',
                       'id': p.IDENTITY, 'countries': ['IN'],
                       'provenance': {'sourceId': p.SOURCE, 'recordId': 'IN',
                                      'releaseId': p.RELEASE, 'fetchedAt': ACQUIRED,
                                      'license': p.LICENCE, 'attribution': 'Authored test metadata',
                                      'rights': 'FAO says permission for further use of country materials must be obtained from the copyright holder.',
                                      'visibility': 'public', 'transform': 'offmenu-guideline-reference/1'},
                       'data': {'name': 'Authored reference',
                                'referenceType': 'national-dietary-guideline-directory-entry',
                                'referenceUrl': 'https://publisher.example.test/fixture',
                                'directoryUrl': 'https://publisher.example.test/index',
                                'reviewStatus': 'directory-entry-observed',
                                'contentPermission': p.PERMISSION,
                                'qualificationStatus': 'reference only; no personal diet recommendations or verified certification'}}}


RIGHTS = b'{"authoredFixtureOnly":true,"noRealSourceGrant":true}'
SCOPE = b'{"authoredExpectedId":"dietary-guidelines:sourceAssertion:IN","records":1}'


def bind(raw):
    return p.Binding(p.Pin('reference-wrapper.json', len(raw), sha(raw)),
                     p.Pin('rights.json', len(RIGHTS), sha(RIGHTS)),
                     p.Pin('scope.json', len(SCOPE), sha(SCOPE)), ACQUIRED,
                     upstream_sha256='b' * 64)


def run(value=None, **kwargs):
    raw = canonical(fixture() if value is None else value)
    return p.prepare(raw, binding=bind(raw), now=kwargs.pop('now', NOW), **kwargs)


class Portfolio42BindingTests(unittest.TestCase):
    def test_cli_preflight_rejects_without_touching_stdin(self):
        class ForbiddenInput:
            @property
            def buffer(self):
                raise AssertionError('preflight must not touch stdin')
        cases = [(['--country', country, '--now', 'invalid'], 'held')
                 for country in ('IM', 'IO', 'IQ', 'ZZ')]
        cases += [(['--now', 'invalid'], 'malformed'),
                  (['--now', '2026-10-12T00:00:00Z'], 'malformed'),
                  (['--now', '2026-10-18T00:00:00Z', '--validated-at',
                    '2026-10-19T00:00:00Z'], 'malformed')]
        for args, expected in cases:
            with self.subTest(args=args):
                output = io.StringIO()
                with patch.object(sys, 'argv', ['portfolio42', *args]), \
                     patch.object(sys, 'stdin', ForbiddenInput()), \
                     patch.object(sys, 'stdout', output):
                    self.assertEqual(p.main(), 2)
                result = json.loads(output.getvalue())
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['records'], [])
                self.assertFalse(result['admission'])

    def test_cli_active_input_keeps_bounded_read_after_preflight(self):
        class ObservedInput:
            def __init__(self):
                self.buffer = self
                self.reads = []
            def read(self, size):
                self.reads.append(size)
                return b''
        stdin = ObservedInput()
        output = io.StringIO()
        with patch.object(sys, 'argv', ['portfolio42', '--now', '2026-10-18T00:00:00Z']), \
             patch.object(sys, 'stdin', stdin), patch.object(sys, 'stdout', output):
            self.assertEqual(p.main(), 2)
        self.assertEqual(stdin.reads, [p.MAX_INPUT + 1])
        self.assertEqual(json.loads(output.getvalue())['status'], 'missing')

    def test_cli_held_country_exits_while_empty_input_pipe_stays_open(self):
        project = Path(__file__).resolve().parents[1]
        process = subprocess.Popen(
            [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio42',
             '--country', 'IQ', '--now', '2026-10-18T00:00:00Z'],
            cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            self.assertEqual(process.wait(timeout=3), 2)
            stdout, stderr = process.communicate(timeout=1)
            self.assertEqual(stderr, b'')
            result = json.loads(stdout)
            self.assertEqual(result['status'], 'held')
            self.assertEqual(result['diagnostics'],
                             ['derivative-use-not-held', 'source-custody-unestablished'])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_valid_preserves_exact_data_and_source_provenance(self):
        source = fixture(); before = deepcopy(source); result = run(source)
        self.assertEqual(result['status'], 'candidate-ready', result['diagnostics'])
        row = result['records'][0]
        self.assertEqual(row['data'], source['record']['data'])
        self.assertEqual({k: v for k, v in row['provenance'].items() if k != 'fieldOrigins'},
                         source['record']['provenance'])
        self.assertEqual(len(row['provenance']['fieldOrigins']), 7)
        self.assertEqual(p.semantics(row, bind(canonical(source))), [])
        self.assertEqual(source, before)
        self.assertFalse(result['admission']); self.assertFalse(result['goldAdmitted'])

    def test_five_typed_outcomes(self):
        raw = canonical(fixture()); binding = bind(raw)
        self.assertEqual(p.prepare(raw, binding=binding, now=NOW)['status'], 'candidate-ready')
        self.assertEqual(p.prepare(None, binding=binding, now=NOW)['status'], 'missing')
        self.assertEqual(p.prepare(raw, binding=replace(binding, holds=('source-specific',)), now=NOW)['status'], 'held')
        bad = b'{broken'; self.assertEqual(p.prepare(bad, binding=bind(bad), now=NOW)['status'], 'malformed')
        self.assertEqual(p.prepare(raw, binding=binding, now='2026-02-01T00:00:00Z')['status'], 'stale')

    def test_held_portfolios_do_not_parse_payload_or_waive_holds(self):
        with patch.object(p, 'strict_json', side_effect=AssertionError('must not parse held input')):
            for country in ['IM', 'IO', 'IQ', 'ZZ']:
                result = p.prepare(b'not source data', country=country, now=NOW)
                self.assertEqual(result['status'], 'held')
                self.assertEqual(result['records'], [])
                self.assertEqual(result['networkRequests'], 0)

    def test_30day_boundary_and_validation_age_are_separate(self):
        young = run(now='2026-01-30T23:59:59Z', validated_at='2026-01-30T00:00:00Z')
        self.assertEqual(young['status'], 'candidate-ready')
        self.assertEqual(young['cache']['acquisitionAgeSeconds'], p.MIN_TTL - 1)
        stale = run(now='2026-01-31T00:00:00Z', validated_at='2026-01-31T00:00:00Z')
        self.assertEqual(stale['status'], 'stale')
        self.assertEqual(stale['cache']['validationAgeSeconds'], 0)
        self.assertEqual(stale['cache']['decision'], 'conditional-review-required-no-download')
        self.assertEqual(stale['networkRequests'], 0)

    def test_replay_noop_excludes_validation_clock(self):
        first = run(); second = run(now='2026-01-03T00:00:00Z', validated_at=NOW,
                                  previous_build_key=first['buildKey'])
        self.assertEqual(first['manifest'], second['manifest'])
        self.assertEqual(first['buildKey'], second['buildKey'])
        self.assertEqual(second['cache']['decision'], 'verified-no-op')
        changed = fixture(); changed['record']['data']['name'] = 'Different authored label'
        self.assertNotEqual(run(changed)['buildKey'], first['buildKey'])

    def test_stale_pin_cannot_be_reused_even_inside_30days(self):
        raw = canonical(fixture()); result = p.prepare(raw+b' ', binding=bind(raw), now=NOW)
        self.assertEqual(result['status'], 'stale'); self.assertEqual(result['records'], [])
        self.assertEqual(result['diagnostics'], ['input-pin-mismatch'])

    def test_original_time_future_naive_and_validation_range_fail(self):
        for instant in ['bad', '2026-01-01', '2025-12-31T00:00:00Z']:
            self.assertEqual(run(now=instant)['status'], 'malformed')
        for stamp in ['2025-12-31T00:00:00Z', '2026-01-03T00:00:00Z']:
            self.assertEqual(run(validated_at=stamp)['status'], 'malformed')

    def test_duplicate_nonfinite_and_oversize_rejected(self):
        for raw in [b'{"country":"IN","country":"IN"}', b'{"n":NaN}', b'{"n":1e999}']:
            self.assertEqual(p.prepare(raw, binding=bind(raw), now=NOW)['status'], 'malformed')
        self.assertEqual(p.prepare(b'x'*(p.MAX_INPUT+1), now=NOW)['status'], 'malformed')

    def test_selector_and_upstream_pin_are_evidenced_not_inferred(self):
        for key, value in [('selector', {'logicalLine': 48, 'index': 0}), ('selector', {'logicalLine': 47, 'index': False}), ('source', {'sha256': 'c'*64})]:
            row = fixture(); row[key] = value
            self.assertEqual(run(row)['diagnostics'], ['upstream-selector-or-pin-mismatch'])

    def test_identity_scope_rights_and_shape_drift_rejected(self):
        for change in [lambda r:r['record'].update(countries=['IQ']),
                       lambda r:r['record']['provenance'].update(releaseId='other'),
                       lambda r:r['record']['provenance'].update(license='permission invented'),
                       lambda r:r['record']['provenance'].update(authorizedOperations=['transform']),
                       lambda r:r['record']['data'].update(contentPermission='document accepted'),
                       lambda r:r['record']['data'].update(name=2),
                       lambda r:r.update(recordCount=True)]:
            row=fixture();change(row);self.assertEqual(run(row)['status'],'malformed')

    def test_source_origins_not_silently_overwritten(self):
        row=fixture();row['record']['provenance']['fieldOrigins']={}
        self.assertEqual(run(row)['status'],'held')
        result=run();record=result['records'][0]
        pointer='/data/name';record['provenance']['fieldOrigins'][pointer]['sourceField']='/record/data/referenceUrl'
        self.assertIn('reference-selector-mismatch',p.semantics(record,bind(canonical(fixture()))))

    def test_manifest_returns_copies_not_mutable_binding_pins(self):
        raw=canonical(fixture());binding=bind(raw);result=p.prepare(raw,binding=binding,now=NOW)
        result['manifest']['inputFiles'][0]['sha256']='0'*64
        self.assertEqual(binding.input.sha256,sha(raw))

    def test_shared_qualification_fixture_and_hold(self):
        raw=canonical(fixture());binding=bind(raw);result=p.prepare(raw,binding=binding,now=NOW)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=root/'bundle';bundle.mkdir()
            for pin,data in [(binding.input,raw),(binding.rights,RIGHTS),(binding.scope,SCOPE)]:
                (bundle/pin.path).write_bytes(data)
            candidate=root/'candidate.jsonl';candidate.write_bytes(encode_records(result['records']))
            schemas={'sourceAssertion':p.RECORD_SCHEMA}
            contract=q.SourceContract(source_id=p.SOURCE,release_id=p.RELEASE,scope_id=p.SCOPE,
                acquired_at=ACQUIRED,inputs=tuple(q.Asset(**x) for x in binding.pins()),
                expected_records=1,expected_ids_sha256=q.ids_digest([p.IDENTITY]),
                schemas=schemas,schemas_sha256=q.fingerprint(schemas),
                semantic_validator=lambda row:p.semantics(row,binding),policy_sha256=p.POLICY_SHA256,
                rights_evidence=q.Asset(**vars(binding.rights)),scope_evidence=q.Asset(**vars(binding.scope)),
                permitted_operations=frozenset(('retain','parse','transform')),fixture=True)
            valid=q.qualify(contract,bundle,candidate,result['manifest'])
            self.assertTrue(valid['qualified'],valid['errors'])
            held=q.qualify(replace(contract,holds=('fixture-hold',)),bundle,candidate,result['manifest'])
            self.assertFalse(held['qualified']);self.assertIn('source-held',held['errors'])
            record=result['records'][0];record['provenance']['fieldOrigins']['/data/name']['sourceField']='/wrong'
            candidate.write_bytes(encode_records([record]))
            failed=q.qualify(contract,bundle,candidate,result['manifest'])
            self.assertFalse(failed['qualified'])

    def test_no_socket_or_transport_in_pure_binding(self):
        with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
            result=run()
            self.assertEqual(result['status'],'candidate-ready')
        self.assertEqual(result['networkRequests'],0)
        self.assertIsNone(p.describe()['nativeUnits']);self.assertIsNone(p.describe()['quantityBasis'])

    def test_cli_describe_and_missing_have_no_implicit_clock_or_download(self):
        command=[sys.executable,'-B','-m','offmenu.refresh.portfolio42']
        cli_now='2026-10-18T00:00:00Z'
        project=Path(__file__).resolve().parents[1]
        described=subprocess.run(command+['--describe'],capture_output=True,text=True,cwd=project)
        self.assertEqual(described.returncode,0,described.stderr)
        self.assertFalse(json.loads(described.stdout)['sourceAdmissionInstalled'])
        missing=subprocess.run(command+['--now',cli_now],input=b'',capture_output=True,cwd=project)
        self.assertEqual(missing.returncode,2);self.assertEqual(json.loads(missing.stdout)['status'],'missing')
        invalid=subprocess.run(command+['--now',cli_now,'--country','IQ'],input=b'opaque',capture_output=True,cwd=project)
        self.assertEqual(json.loads(invalid.stdout)['status'],'held')


if __name__=='__main__':
    unittest.main()
