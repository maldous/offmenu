"""Authored metadata only: no historical originals or network access."""
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest
import zipfile
from unittest.mock import patch

from offmenu.refresh import portfolio05 as binding
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.serialization import encode_records
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify


NOW = '2026-10-18T00:00:00Z'


def authored():
    payload = canonical({'country': 'BB', 'edition': 'authored-fixture/1',
                         'role': 'authored-reference', 'access': 'authored-use-evidence',
                         'acquired': '2026-10-10T00:00:00Z',
                         'validated': '2026-10-17T00:00:00Z',
                         'secretUnselectedField': 'never-serialize-this'})
    spec = {'sourceId': 'authored05', 'country': 'BB', 'holds': [],
            'applicability': {'acceptedCountryTypes': [], 'fixture': True},
            'receipt': {'path': '/unused/authored.json', 'sha256': sha(payload), 'bytes': len(payload)},
            'fields': {'release': '/edition', 'documentRole': '/role', 'acquisitionBasis': '/access'},
            'acquisitionPointer': '/acquired', 'validationPointer': '/validated',
            'acquisitionMeaning': 'authored original acquisition'}
    return spec, payload


class Portfolio05Bindings(unittest.TestCase):
    def test_valid_deterministic_origins_and_noop(self):
        spec, payload = authored()
        first = binding.bind(spec, payload, now=NOW)
        self.assertEqual(first['status'], 'valid')
        self.assertEqual(first['fieldOriginErrors'], [])
        self.assertEqual(first['candidate']['data']['nativeUnit'], None)
        self.assertNotIn('never-serialize-this', json.dumps(first))
        self.assertEqual(first['cache']['acquisitionAgeDays'], 8)
        self.assertEqual(first['cache']['minimumReuseDaysRequired'], 30)
        self.assertEqual(first['cache']['freshness'], 'unknown')
        self.assertEqual(first['cache']['decision'], 'unsupported-real-source-cache-planner')
        self.assertFalse(first['cache']['sourceBodyCacheVerified'])
        self.assertEqual(first, binding.bind(spec, payload, now=NOW))
        replay = binding.bind(spec, payload, now=NOW, previous_candidate_sha256=first['candidateSha256'])
        self.assertTrue(replay['unchangedContentNoOp'])
        changed = copy.deepcopy(spec)
        changed['acquisitionMeaning'] += '-corrected-policy'
        self.assertNotEqual(first['candidateSha256'], binding.bind(changed, payload, now=NOW)['candidateSha256'])

    def test_missing_held_malformed_and_stale(self):
        spec, payload = authored()
        self.assertEqual(binding.bind(spec, None, now=NOW)['status'], 'missing')
        held = copy.deepcopy(spec)
        held['holds'] = ['http403-no-retry-no-body-processing']
        result = binding.bind(held, payload, now=NOW)
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['sourceOperationsAuthorized'], [])
        missing = copy.deepcopy(spec)
        missing['fields']['release'] = '/absent'
        self.assertEqual(binding.bind(missing, payload, now=NOW)['diagnostics'], ['metadata-selector-missing'])
        self.assertEqual(binding.bind(spec, payload+b' ', now=NOW)['diagnostics'], ['metadata-pin-mismatch'])
        for malformed in [b'{"country":"BB","country":"BB"}', b'{bad', b'[]']:
            bad = copy.deepcopy(spec)
            bad['receipt']['sha256'] = sha(malformed)
            self.assertEqual(binding.bind(bad, malformed, now=NOW)['status'], 'malformed')
        # Stale input means the caller's prior metadata candidate no longer
        # matches exact current content/policy. It is not a cache-age decision.
        stale = binding.bind(spec, payload, now=NOW, previous_candidate_sha256='0'*64)
        self.assertEqual(stale['status'], 'stale')
        self.assertEqual(stale['diagnostics'], ['previous-metadata-candidate-stale'])
        old = binding.bind(spec, payload, now='2026-11-09T00:00:00Z')
        self.assertEqual(old['cache']['acquisitionAgeDays'], 30)
        self.assertEqual(old['cache']['freshness'], 'unknown')
        self.assertEqual(old['cache']['decision'], 'unsupported-real-source-cache-planner')
        self.assertFalse(old['cache']['validationResetsAcquisitionAge'])
        self.assertFalse(old['cache']['conditionalDownloadEnabled'])
        self.assertEqual(binding.bind(held, payload, now='2026-11-09T00:00:00Z')['status'], 'held')

    def test_invalid_clock_order_and_field_type(self):
        spec, payload = authored()
        self.assertEqual(binding.bind(spec, payload, now='2026-10-09T00:00:00Z')['diagnostics'],
                         ['metadata-time-order-invalid'])
        self.assertEqual(binding.bind(spec, payload, now='2026-10-18')['status'], 'malformed')
        document = json.loads(payload)
        document['role'] = {'unsupported': 1}
        raw = canonical(document)
        spec['receipt']['sha256'] = sha(raw)
        self.assertEqual(binding.bind(spec, raw, now=NOW)['diagnostics'], ['metadata-field-invalid'])

    def test_isolated_file_diagnostics_and_no_raw_reads(self):
        spec, payload = authored()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'receipt.json'
            p.write_bytes(payload)
            spec['receipt']['path'] = str(p)
            good = copy.deepcopy(spec)
            missing = copy.deepcopy(spec)
            missing['sourceId'] = 'missing'
            missing['receipt']['path'] = str(Path(tmp)/'missing.json')
            bad = copy.deepcopy(spec)
            bad['sourceId'] = 'bad'
            bad['receipt']['sha256'] = '0'*64
            # This body path must never be followed; only receipt path is opened.
            good['rawBodyPinAsRecorded'] = {'path': '/must-not-open', 'sha256': '0'*64}
            with patch.object(binding, 'configuration', return_value={'sources': [missing, bad, good], 'evidencePins': []}):
                result = binding.inspect_portfolio(now=NOW)
            self.assertEqual([x['status'] for x in result['sources']], ['missing', 'malformed', 'valid'])
            self.assertEqual(result['sourceBodiesRead'], 0)
            self.assertEqual(result['networkRequests'], 0)

    def test_receipt_replacement_fifo_never_reopens_unbounded(self):
        spec, payload = authored()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root/'changed.json'
            target.write_bytes(payload)
            good = root/'good.json'
            good.write_bytes(payload)
            spec['receipt']['path'] = str(target)
            sibling = copy.deepcopy(spec)
            sibling['sourceId'] = 'sibling'
            sibling['receipt']['path'] = str(good)
            real_open = os.open
            swapped = False
            def raced_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if path == target.name and kwargs.get('dir_fd') is not None and not swapped:
                    self.assertTrue(flags & os.O_NONBLOCK, 'reject regression before FIFO could block')
                    self.assertTrue(flags & os.O_NOFOLLOW)
                    target.rename(root/'protected-original.json')
                    os.mkfifo(target)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)
            with patch.object(binding, 'configuration', return_value={'sources': [spec, sibling], 'evidencePins': []}), \
                 patch.object(binding.os, 'open', side_effect=raced_open), \
                 patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded path reopen')):
                result = binding.inspect_portfolio(now=NOW)
            self.assertTrue(swapped)
            self.assertEqual([x['status'] for x in result['sources']], ['malformed', 'valid'])
            self.assertEqual((root/'protected-original.json').read_bytes(), payload)

    def test_receipt_growth_read_is_capped_and_rejected(self):
        spec, payload = authored()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'receipt.json'
            target.write_bytes(payload)
            spec['receipt']['path'] = str(target)
            real_fdopen = os.fdopen
            sizes = []
            class GrowingStream:
                def __init__(self, stream): self.stream = stream
                def __enter__(self): self.stream.__enter__(); return self
                def __exit__(self, *args): return self.stream.__exit__(*args)
                def fileno(self): return self.stream.fileno()
                def read(self, size):
                    sizes.append(size)
                    with target.open('ab') as stream:
                        stream.write(b'x'*(binding.MAX_RECEIPT*2))
                    return self.stream.read(size)
            with patch.object(binding, 'configuration', return_value={'sources': [spec], 'evidencePins': []}), \
                 patch.object(binding.os, 'fdopen', side_effect=lambda *args, **kw: GrowingStream(real_fdopen(*args, **kw))), \
                 patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded path reopen')):
                result = binding.inspect_portfolio(now=NOW)
            self.assertEqual(sizes, [len(payload)+1])
            self.assertEqual(result['sources'][0]['status'], 'malformed')

    def test_production_configuration_keeps_every_source_held(self):
        config = binding.configuration()
        self.assertEqual(len(config['sources']), 8)
        self.assertEqual({s['country'] for s in config['sources']}, {'BB', 'JO', 'PY'})
        for spec in config['sources']:
            self.assertIn('source-body-operation-not-selected', spec['holds'])
            self.assertEqual(spec['applicability']['acceptedCountryTypes'], [])
            self.assertTrue(spec['receipt']['path'].endswith('/receipt.json'))
        self.assertTrue(any('http403-no-retry-no-body-processing' in s['holds'] for s in config['sources']))

    def test_no_pilot_planner_or_operational_acquirer(self):
        spec, payload = authored()
        with patch('offmenu.refresh.core.cache_policy', side_effect=AssertionError('pilot planner forbidden')), \
             patch('offmenu.refresh.policy.plan_fixture', side_effect=AssertionError('fixture spoof forbidden')), \
             patch('offmenu.refresh.acquisition.CachedAcquirer.acquire', side_effect=AssertionError('body acquisition forbidden')):
            row = binding.bind(spec, payload, now=NOW)
        self.assertEqual(row['status'], 'valid')
        self.assertEqual(row['cache']['decision'], 'unsupported-real-source-cache-planner')

    def test_shared_fixture_qualification_and_tampering(self):
        spec, payload = authored()
        result = binding.bind(spec, payload, now=NOW)
        row = result['candidate']
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root/'bundle'
            (bundle/'metadata').mkdir(parents=True)
            (bundle/'metadata/receipt.json').write_bytes(payload)
            # Both evidence documents are authored test-only decisions, not grants
            # for the retained publisher works in the production config.
            rights = canonical({'fixtureOnly': True, 'operations': ['retain', 'parse', 'transform']})
            scope = canonical({'fixtureOnly': True, 'rows': 1, 'countryComplete': False})
            (bundle/'rights.json').write_bytes(rights)
            (bundle/'scope.json').write_bytes(scope)
            assets = (Asset('metadata/receipt.json', len(payload), sha(payload)),
                      Asset('rights.json', len(rights), sha(rights)), Asset('scope.json', len(scope), sha(scope)))
            schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                      'properties': {'data': {'const': row['data']}, 'kind': {'const': row['kind']}}}
            schemas = {row['kind']: schema}
            def semantic(value):
                errors = binding.field_origin_errors(value, {'metadata/receipt.json': sha(payload)},
                                                     policy_pins=(result['policySha256'],))
                if value != row:
                    errors.append('authored-exact-metadata-mismatch')
                return errors
            contract = SourceContract(source_id=spec['sourceId'], release_id=result['releaseId'],
                scope_id='authored05-metadata-only', acquired_at=result['acquiredAt'], inputs=assets,
                expected_records=1, expected_ids_sha256=ids_digest([row['id']]), schemas=schemas,
                schemas_sha256=fingerprint(schemas), semantic_validator=semantic,
                policy_sha256=result['policySha256'], rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = root/'candidate.jsonl'
            raw = encode_records([row])
            candidate.write_bytes(raw)
            manifest = {'sourceId': spec['sourceId'], 'releaseId': result['releaseId'],
                'acquiredAt': result['acquiredAt'], 'normalizedRecords': 1,
                'candidateSha256': sha(raw), 'candidateBytes': len(raw),
                'rightsEvidenceSha256': sha(rights), 'scopeEvidenceSha256': sha(scope),
                'inputFiles': [vars(a) for a in assets]}
            qualified = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(qualified['qualified'], qualified)
            self.assertTrue(qualified['fixture'])
            (bundle/'metadata/receipt.json').write_bytes(b'changed')
            self.assertIn('input-custody-mismatch', qualify(contract, bundle, candidate, manifest)['errors'])

    def test_cli_without_explicit_time_fails_without_receipt_reads(self):
        run = subprocess.run([sys.executable, '-B', '-m', 'offmenu.refresh.portfolio05'], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(b'--now', run.stderr)

    def test_previous_regular_report_preserved_and_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'previous.json'
            raw = canonical({'sources': [{'sourceId': 'authored05', 'candidateSha256': 'a'*64}]})
            path.write_bytes(raw)
            before = (path.stat().st_mtime_ns, path.read_bytes())
            outputs = []
            for _ in range(2):
                output = io.StringIO()
                with patch.object(binding, 'inspect_portfolio', return_value={'authored': True}) as inspect, \
                     redirect_stdout(output):
                    status = binding.main(['--now', NOW, '--previous', str(path)])
                self.assertEqual(status, 0)
                inspect.assert_called_once_with(now=NOW, previous={'authored05': 'a'*64})
                outputs.append(output.getvalue())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual((path.stat().st_mtime_ns, path.read_bytes()), before)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Foo POSIX reader regression')
    def test_previous_fifo_rejected_before_metadata_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'previous.json'
            os.mkfifo(path)
            before = path.stat().st_mtime_ns
            code = '''import sys
from unittest.mock import patch
from offmenu.refresh import portfolio05 as module
with patch.object(module, 'inspect_portfolio', side_effect=AssertionError('receipt read forbidden')):
    status = module.main(['--now', sys.argv[1], '--previous', sys.argv[2]])
raise SystemExit(status)
'''
            run = subprocess.run([sys.executable, '-B', '-c', code, NOW, str(path)],
                                 capture_output=True, text=True, timeout=2)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stderr)['diagnostics'], ['previous-report-regular-file-required'])
            self.assertEqual(path.stat().st_mtime_ns, before)
            if Path('/proc/self/fd').exists():
                count = len(os.listdir('/proc/self/fd'))
                for _ in range(20):
                    with self.assertRaisesRegex(ValueError, 'previous-report-regular-file-required'):
                        binding.previous_candidates(path)
                self.assertEqual(len(os.listdir('/proc/self/fd')), count)

    def test_previous_raced_links_bounds_and_malformed_are_typed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root/'target.json'
            target.write_bytes(canonical({'sources': []}))
            link = root/'link.json'
            link.symlink_to(target)
            parent = root/'parent'
            parent.symlink_to(root, target_is_directory=True)
            for path in (link, parent/'target.json'):
                # Simulate link replacement after the preflight safe_path check.
                with patch.object(binding, 'safe_path', return_value=path):
                    with self.assertRaisesRegex(ValueError, 'previous-report-file-unavailable'):
                        binding.previous_candidates(path)
            target.write_bytes(b' '*(binding.MAX_PREVIOUS+1))
            with self.assertRaisesRegex(ValueError, 'previous-report-bound'):
                binding.previous_candidates(target)
            for raw in [b'{bad', b'{"sources":[],"sources":[]}',
                        canonical({'sources': [{'sourceId': []}]}),
                        canonical({'sources': [{'sourceId': 'x', 'candidateSha256': 'bad'}]})]:
                target.write_bytes(raw)
                error = io.StringIO()
                with patch.object(binding, 'inspect_portfolio', side_effect=AssertionError('receipt read forbidden')), \
                     redirect_stderr(error):
                    code = binding.main(['--now', NOW, '--previous', str(target)])
                self.assertEqual(code, 2)
                self.assertEqual(len(json.loads(error.getvalue())['diagnostics']), 1)

    def test_offline_installed_wheel_configuration(self):
        # Build only source code in scratch. No pip/install/network, shared
        # packaging edits, retained receipt reads or author-checkout build files.
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source'
            source.mkdir()
            shutil.copytree(repository/'offmenu', source/'offmenu',
                            ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(repository/'pyproject.toml', source/'pyproject.toml')
            wheels = root/'wheels'
            wheels.mkdir()
            build = subprocess.run([sys.executable, '-I', '-B', '-c',
                'from setuptools.build_meta import build_wheel, build_sdist; '
                'build_wheel('+repr(str(wheels))+'); build_sdist('+repr(str(wheels))+')'],
                cwd=source, capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            wheel, = wheels.glob('*.whl')
            sdist, = wheels.glob('*.tar.gz')
            with tarfile.open(sdist) as archive:
                names = archive.getnames()
                self.assertTrue(any(n.endswith('/offmenu/refresh/portfolio05_sources.py') for n in names))
                self.assertFalse(any(n.endswith('/offmenu/refresh/portfolio05_sources.json') for n in names))
            installed = root/'installed'
            with zipfile.ZipFile(wheel) as archive:
                self.assertIn('offmenu/refresh/portfolio05_sources.py', archive.namelist())
                self.assertNotIn('offmenu/refresh/portfolio05_sources.json', archive.namelist())
                archive.extractall(installed)
            script = '''import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from offmenu.refresh import portfolio05 as module
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
with patch.object(Path, 'read_bytes', side_effect=AssertionError('no receipt/resource reads')):
    config = module.configuration()
assert len(config['sources']) == 8
assert {row['country'] for row in config['sources']} == {'BB', 'JO', 'PY'}
assert all(row['holds'] for row in config['sources'])
config['sources'].clear()
assert len(module.configuration()['sources']) == 8
print('installed-config-smoke-pass; metadata-reads=0')
'''
            run = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(installed)],
                                 cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('installed-config-smoke-pass; metadata-reads=0', run.stdout)


if __name__ == '__main__':
    unittest.main()
