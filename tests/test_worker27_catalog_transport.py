"""Code-catalogue transport only; no source metadata or bodies are accessed."""
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio_worker27 as binding
from offmenu.refresh._worker27_catalog import JSON_MIRROR_SHA256
from offmenu.refresh.core import canonical, sha, strict_json


class Worker27CatalogTransportTests(unittest.TestCase):
    def test_literal_matches_exact_json_code_mirror_and_copies_deeply(self):
        raw = binding.CATALOG.read_bytes()  # Fixed code artifact, not source data.
        self.assertEqual(sha(raw), JSON_MIRROR_SHA256)
        mirror = strict_json(raw)
        first = binding.load_catalog()
        self.assertEqual(canonical(first), canonical(mirror))
        first['bindings'][0]['declaredFields'].clear()
        first['bindings'][-1]['holds'].append('authored-mutation')
        first['countryRequirements'].clear()
        self.assertEqual(canonical(binding.load_catalog()), canonical(mirror))

    def test_default_loader_and_assessment_do_not_read_any_references(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected read')), \
                patch('io.open', side_effect=AssertionError('unexpected read')), \
                patch('socket.socket', side_effect=AssertionError('unexpected network')):
            catalog = binding.load_catalog()
            report = binding.assess(catalog, {'observations': []}, '2026-10-18T05:00:00Z')
        self.assertEqual(len(report['bindings']), 13)
        self.assertEqual(len(report['countryRequirements']), 24)
        self.assertEqual(sum(r['status'] == 'held' for r in report['bindings']), 1)
        self.assertEqual(report['acceptedRecords'], 0)

    def test_cli_default_loads_literal_and_reads_only_explicit_request(self):
        request = Path('/authored/request.json')
        output = io.StringIO()
        argv = ['worker27', '--request', str(request), '--as-of',
                '2026-10-18T05:00:00Z', '--output', '/authored/report.json']
        def authored_request(path):
            self.assertEqual(path, request)
            return {'observations': []}
        with patch('sys.argv', argv), patch.object(binding, 'read_metadata', side_effect=authored_request) as read, \
                patch.object(binding, 'write_report', return_value='created') as write, \
                patch('builtins.open', side_effect=AssertionError('unexpected read')), \
                patch('io.open', side_effect=AssertionError('unexpected read')), \
                patch('socket.socket', side_effect=AssertionError('unexpected network')), \
                contextlib.redirect_stdout(output):
            self.assertEqual(binding.main(), 0)
        read.assert_called_once_with(request)
        self.assertEqual(len(write.call_args.args[1]['bindings']), 13)
        self.assertEqual(strict_json(output.getvalue())['bindingCount'], 13)


if __name__ == '__main__':
    unittest.main()
