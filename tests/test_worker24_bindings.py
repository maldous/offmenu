"""Authored synthetic metadata/cells only; no retained source bodies opened."""
from copy import deepcopy
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import worker24_bindings as binding
from offmenu.refresh.core import RefreshError
from offmenu.refresh.worker24_metadata_diagnostic import check_selector
from offmenu.refresh import worker24_metadata_diagnostic as diagnostic


def fixture():
    # Deliberately invented asset/selector/cells, never a publisher record.
    profile = {'country': 'PF', 'sourceId': 'authored-PF', 'releaseId': 'fixture-1',
               'holds': [], 'inputs': [{'path': 'authored.csv', 'sha256': 'a' * 64,
                   'bytes': 17, 'releaseId': 'fixture-1', 'headers': ['label', 'value']}],
               'acquisition': {'originalAcquiredAt': '2026-10-01T00:00:00Z',
                               'lastValidatedAt': '2026-10-17T00:00:00Z'}}
    return {'schemaVersion': 'offmenu-worker24-binding/1', 'profiles': [profile]}


class Worker24Bindings(unittest.TestCase):
    def test_authored_selectors_resolve_exact_metadata(self):
        root = Path(__file__).parent / 'fixtures/worker24-metadata'
        assets = json.loads((root / 'bindings.json').read_text())['inputs']
        raw = (root / 'evidence.json').read_bytes()
        self.assertEqual(len(assets), 2)
        for asset in assets:
            with self.subTest(asset=asset['path']):
                check_selector(asset, raw)

    def test_authored_wrong_selector_and_declaration_drift_fail(self):
        root = Path(__file__).parent / 'fixtures/worker24-metadata'
        asset = json.loads((root / 'bindings.json').read_text())['inputs'][0]
        raw = (root / 'evidence.json').read_bytes()
        wrong = deepcopy(asset)
        wrong['selector'] = '/members/0'
        with self.assertRaisesRegex(RefreshError, '^metadata-selector-unresolved$'):
            check_selector(wrong, raw)
        for key, value in [('path', 'wrong.csv'), ('sha256', 'f' * 64),
                           ('bytes', 99), ('headers', ['wrong']), ('releaseId', 'wrong')]:
            with self.subTest(field=key):
                wrong = deepcopy(asset)
                wrong[key] = value
                with self.assertRaisesRegex(RefreshError, '^metadata-selector-declaration-mismatch$'):
                    check_selector(wrong, raw)
        with self.assertRaisesRegex(RefreshError, '^metadata-evidence-hash-mismatch$'):
            check_selector(asset, raw + b' ')

    def test_valid_and_stable_replay(self):
        document = fixture()
        first = binding.plan(document, now='2026-10-18T00:00:00Z')
        replay = binding.plan(document, now='2026-10-18T00:00:00Z', previous_key=first['contentKey'])
        self.assertEqual(first['profiles'][0]['status'], 'reuse-metadata-only')
        self.assertEqual(first['profiles'][0]['acquisitionAgeDays'], 17)
        self.assertTrue(replay['metadataNoOp'])
        self.assertFalse(first['payloadBytesVerified'])
        self.assertEqual(first['acceptedRecords'], 0)
        self.assertEqual(document, fixture())

    def test_stale_boundary_and_revalidation_does_not_reset(self):
        document = fixture()
        old_key = binding.plan(document, now='2026-10-18T00:00:00Z')['contentKey']
        document['profiles'][0]['acquisition']['lastValidatedAt'] = '2026-10-31T00:00:00Z'
        result = binding.plan(document, now='2026-10-31T00:00:00Z', previous_key=old_key)
        self.assertEqual(result['profiles'][0]['status'], 'stale-review-required')
        self.assertEqual(result['profiles'][0]['acquisitionAgeDays'], 30)
        self.assertTrue(result['metadataNoOp'])
        self.assertEqual(result['networkRequests'], 0)
        self.assertEqual(result['nextOnlineStep'], 'none')

    def test_missing_held_malformed_are_isolated(self):
        document = fixture()
        for country in ('SL', 'TF', 'UY'):
            p = deepcopy(document['profiles'][0]); p['country'] = country
            document['profiles'].append(p)
        document['profiles'][1]['acquisition']['originalAcquiredAt'] = None
        document['profiles'][2]['holds'] = ['explicit-403-no-retry']
        document['profiles'][2]['inputs'] = None
        document['profiles'][3]['inputs'][0]['sha256'] = 'broken'
        result = binding.plan(document, now='2026-10-18T00:00:00Z')
        self.assertEqual([p['status'] for p in result['profiles']],
                         ['reuse-metadata-only', 'missing', 'held', 'malformed'])
        self.assertEqual(result['missingCountries'], [])

    def test_future_and_path_escape_fail_closed(self):
        document = fixture()
        document['profiles'][0]['inputs'][0]['path'] = '../raw.csv'
        self.assertEqual(binding.plan(document, now='2026-10-18T00:00:00Z')['profiles'][0]['status'], 'malformed')
        document = fixture()
        document['profiles'][0]['acquisition']['originalAcquiredAt'] = '2026-10-19T00:00:00Z'
        self.assertIn('acquisition-in-future', binding.plan(document, now='2026-10-18T00:00:00Z')['profiles'][0]['diagnostics'])

    def test_shared_provenance_validator_with_lexical_null_marker_and_zero(self):
        profile = fixture()['profiles'][0]
        row = {'data': {'cells': ['', '0']}, 'provenance': {
            'sourceId': profile['sourceId'], 'releaseId': 'fixture-1',
            'fieldOrigins': binding.origin_template(profile, 'authored.csv', 'authored-record-1')}}
        self.assertEqual(binding.authored_row_errors(profile, 'authored.csv', row), [])
        row['provenance']['fieldOrigins']['/data/cells/1']['inputSha256'] = 'b' * 64
        self.assertIn('field-origin-input-pin-mismatch', binding.authored_row_errors(profile, 'authored.csv', row))
        row['provenance']['fieldOrigins']['/data/cells/1']['sourceField'] = 'guessed-nutrient'
        self.assertIn('binding-selector-mismatch', binding.authored_row_errors(profile, 'authored.csv', row))

    def test_committed_metadata_no_payload_reads_and_expected_holds(self):
        document = binding.catalogue()
        # A planner attempting to follow embedded evidence/candidate/raw paths fails.
        with patch('pathlib.Path.open', side_effect=AssertionError('unexpected file read')):
            result = binding.plan(document, now='2026-10-18T00:00:00Z')
        self.assertEqual([(p['country'], p['status']) for p in result['profiles']],
                         [('PF', 'missing'), ('UY', 'missing'), ('SL', 'held'), ('TF', 'held')])
        self.assertEqual(result['sourceBodiesRead'], 0)
        self.assertEqual(result['candidateBodiesRead'], 0)

    def test_content_change_not_noop_and_duplicate_country_rejected(self):
        document = fixture()
        key = binding.plan(document, now='2026-10-18T00:00:00Z')['contentKey']
        document['profiles'][0]['inputs'][0]['sha256'] = 'b' * 64
        self.assertFalse(binding.plan(document, now='2026-10-18T00:00:00Z', previous_key=key)['metadataNoOp'])
        document['profiles'].append(deepcopy(document['profiles'][0]))
        self.assertEqual(binding.plan(document, now='2026-10-18T00:00:00Z')['profiles'][1]['diagnostics'], ['duplicate-country-binding'])


class PackagedCatalogueTests(unittest.TestCase):
    def test_literal_equivalence_and_copy_isolation(self):
        frozen = json.loads((Path(__file__).parents[1] /
                             'docs/operations/worker24/bindings.json').read_text())
        source = Path(binding.__file__).with_name('worker24_catalogue.py')
        tree = ast.parse(source.read_text())
        self.assertEqual(len(tree.body), 2)  # docstring + inert literal assignment
        self.assertIsInstance(tree.body[1], ast.Assign)
        self.assertEqual(tree.body[1].targets[0].id, 'BINDINGS')
        self.assertEqual(ast.literal_eval(tree.body[1].value), frozen)
        first = binding.catalogue()
        self.assertEqual(first, frozen)
        first['profiles'][0]['inputs'][0]['sha256'] = 'changed-only-in-copy'
        self.assertEqual(binding.catalogue(), frozen)
        self.assertEqual(binding.plan(binding.catalogue(), now='2026-10-18T00:00:00Z'),
                         binding.plan(frozen, now='2026-10-18T00:00:00Z'))

    def test_diagnostic_catalogue_needs_no_repository_resource(self):
        output = io.StringIO()
        with patch('pathlib.Path.open', side_effect=AssertionError('no repository resource')):
            with patch.object(diagnostic, 'read_metadata_evidence',
                              side_effect=RefreshError('metadata-evidence-unavailable')):
                with contextlib.redirect_stdout(output):
                    code = diagnostic.main(['--foo-metadata'])
        self.assertEqual(code, 2)
        rows = json.loads(output.getvalue())['results']
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(r['code'] == 'metadata-evidence-unavailable' for r in rows))


class MetadataReaderTests(unittest.TestCase):
    def test_regular_metadata_is_preserved_and_limits_are_typed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / 'metadata.json'
            raw = b'{"authored":"metadata only"}\n'
            regular.write_bytes(raw)
            self.assertEqual(diagnostic.read_metadata_evidence(regular), raw)
            self.assertEqual(regular.read_bytes(), raw)
            with self.assertRaisesRegex(RefreshError, '^metadata-evidence-unavailable$'):
                diagnostic.read_metadata_evidence(root / 'missing')
            with self.assertRaisesRegex(RefreshError, '^metadata-evidence-not-regular$'):
                diagnostic.read_metadata_evidence(root)
            link = root / 'link'; link.symlink_to(regular)
            with self.assertRaisesRegex(RefreshError, '^metadata-evidence-not-regular$'):
                diagnostic.read_metadata_evidence(link)
            regular.write_bytes(b'x' * (diagnostic.MAX_EVIDENCE_BYTES + 1))
            with self.assertRaisesRegex(RefreshError, '^metadata-evidence-too-large$'):
                diagnostic.read_metadata_evidence(regular)

    def test_path_replacement_during_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            original = b'{"authored":"original"}\n'
            path.write_bytes(original)
            old = path.with_name('original.json')
            read = os.read
            replaced = False
            def replace_during_read(fd, count):
                nonlocal replaced
                if not replaced:
                    path.rename(old)
                    path.write_bytes(b'{"authored":"replacement"}\n')
                    replaced = True
                return read(fd, count)
            with patch.object(diagnostic.os, 'read', side_effect=replace_during_read):
                with self.assertRaisesRegex(RefreshError, '^metadata-evidence-changed$'):
                    diagnostic.read_metadata_evidence(path)
            self.assertEqual(old.read_bytes(), original)

    def test_successor_entrypoint_rejects_fifo_without_blocking_peer(self):
        root_fixture = Path(__file__).parent / 'fixtures/worker24-metadata'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / 'evidence.json'
            raw = (root_fixture / 'evidence.json').read_bytes()
            regular.write_bytes(raw)
            fifo = root / 'no-writer.fifo'; os.mkfifo(fifo)
            asset = json.loads((root_fixture / 'bindings.json').read_text())['inputs'][0]
            inputs = []
            for path in (fifo, regular):
                item = deepcopy(asset)
                item['selectorEvidence']['path'] = str(path)
                inputs.append(item)
            document = {'profiles': [{'country': 'PF', 'inputs': inputs,
                                     'evidence': [x['selectorEvidence'] for x in inputs]}]}
            config = root / 'config.json'
            config.write_text(json.dumps(document))
            before = config.read_bytes()
            # Test only the successor. Timeout prevents a regression hanging CI.
            code = ('from pathlib import Path; import sys; '
                    'from offmenu.refresh import worker24_metadata_diagnostic as d; '
                    'import json; d.catalogue=lambda:json.loads(d.read_metadata_evidence(sys.argv[1])); '
                    'raise SystemExit(d.main(["--foo-metadata"]))')
            run = subprocess.run([sys.executable, '-B', '-c', code, str(config)],
                                 capture_output=True, timeout=3)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(run.stderr, b'')
            report = json.loads(run.stdout)
            self.assertEqual([x['code'] for x in report['results']],
                             ['metadata-evidence-not-regular', 'metadata-selector-matched'])
            self.assertEqual(regular.read_bytes(), raw)
            self.assertEqual(config.read_bytes(), before)
            # Test-only authored catalogue injection exercises the reader too;
            # the real catalogue is an inert module with no config-path read.
            run = subprocess.run([sys.executable, '-B', '-c', code, str(fifo)],
                                 capture_output=True, timeout=3)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(json.loads(run.stdout)['errorCode'], 'metadata-evidence-not-regular')


if __name__ == '__main__':
    unittest.main()
