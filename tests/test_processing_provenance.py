import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    'build_processing_provenance', ROOT / 'scripts/build-processing-provenance.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ProcessingProvenanceTests(unittest.TestCase):
    def test_stages_are_separate_and_missing_engine_dates_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = root / 'original.html'
            original.write_bytes(b'<html>fixture</html>')
            output = root / 'output.jsonl'
            output.write_bytes(b'{"synthetic":true}\n')
            artifact_sha = hashlib.sha256(output.read_bytes()).hexdigest()
            asset_manifest = root / 'asset-manifest.json'
            asset_manifest.write_text(json.dumps({
                'status': 'complete',
                'inputSHA256': hashlib.sha256(original.read_bytes()).hexdigest(),
                'identity': {'parserVersion': 'test-parser/2.3'},
                'artifacts': {'output.jsonl': {'bytes': output.stat().st_size,
                                               'sha256': artifact_sha}},
            }))
            run = root / 'run.json'
            run.write_text(json.dumps({
                'schemaVersion': 'offmenu-source-parse-run/1',
                'assets': [{'sourceId': 'TEST', 'sourceRecordId': 'one',
                    'kind': 'recipe', 'country': 'ZZ', 'status': 'complete',
                    'inputPath': str(original),
                    'inputSHA256': hashlib.sha256(original.read_bytes()).hexdigest(),
                    'manifestPath': str(asset_manifest), 'parserVersion': 'test-parser/2.3'}],
            }))
            ledger = BUILDER.build_ledger(run)
            asset = ledger['assets'][0]
            self.assertEqual(set(asset['stages']), {'parse', 'normalize', 'englishTranslation'})
            parse = asset['stages']['parse']
            self.assertEqual(parse['method'], 'code')
            self.assertEqual(parse['engine']['identity'], 'test-parser/2.3')
            self.assertEqual(parse['engine']['scriptLocation'], 'offmenu/refresh/source_faithful_parse.py')
            self.assertEqual(parse['validation']['status'], 'passed')
            self.assertEqual(parse['input']['sha256'], hashlib.sha256(original.read_bytes()).hexdigest())
            self.assertEqual(parse['cachedOutput'][0]['sha256'], artifact_sha)
            self.assertIsNone(parse['processingDate']['value'])
            self.assertEqual(parse['processingDate']['status'], 'unknown')
            self.assertEqual(asset['stages']['normalize']['status'], 'not-run')
            self.assertEqual(asset['stages']['normalize']['method'], None)
            self.assertEqual(asset['stages']['englishTranslation']['status'], 'not-run')
            self.assertEqual(asset['stages']['englishTranslation']['engine']['identity'], 'not-run')

    def test_artifact_checksum_mismatch_fails_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = root / 'original'
            original.write_bytes(b'raw')
            output = root / 'out'
            output.write_bytes(b'actual')
            asset_manifest = root / 'asset.json'
            asset_manifest.write_text(json.dumps({
                'status': 'complete', 'inputSHA256': hashlib.sha256(b'raw').hexdigest(),
                'identity': {'parserVersion': 'parser/1'},
                'artifacts': {'out': {'bytes': 6, 'sha256': '0' * 64}},
            }))
            run = root / 'run.json'
            run.write_text(json.dumps({'schemaVersion': 'offmenu-source-parse-run/1',
                'assets': [{'sourceId': 'T', 'sourceRecordId': 'r', 'status': 'complete',
                    'kind': 'recipe', 'inputPath': str(original),
                    'inputSHA256': hashlib.sha256(b'raw').hexdigest(),
                    'manifestPath': str(asset_manifest), 'parserVersion': 'parser/1'}]}))
            ledger = BUILDER.build_ledger(run)
            parse = ledger['assets'][0]['stages']['parse']
            self.assertEqual(parse['validation']['status'], 'failed')
            self.assertTrue(any('checksum/size mismatch' in x
                                for x in parse['validation']['unresolvedIssues']))
            self.assertEqual(ledger['assets'][0]['stages']['normalize']['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
