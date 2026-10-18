"""Synthetic offline retained-byte diagnostics; never access the publisher or Foo."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('retained_tw_test', ROOT / 'scripts/diagnose-retained-taiwan.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BODY = b'%PDF-1.7\nprivate synthetic text\n%%EOF\n'


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        self.work = self.root / 'collection'
        self.work.mkdir(mode=0o700)
        (self.work / 'private-originals').mkdir(mode=0o700)
        self.stack.enter_context(patch.object(m, 'OUTPUT_ROOT', self.root))
        self.stack.enter_context(patch.object(m, 'EXPECTED_UID', os.getuid()))
        self.stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('no network')))
        self.stack.enter_context(patch.object(socket, 'create_connection', side_effect=AssertionError('no network')))
        self.install([BODY] * 3)

    def tearDown(self):
        self.stack.close()

    def write(self, path, raw):
        path.write_bytes(raw)
        path.chmod(0o600)

    def install(self, bodies):
        entries = []
        self.folders = []
        self.details = []
        for (number, contract, _, _), body in zip(m.ENTRIES, bodies):
            key = 'tw41-eastern-afa-' + number + '-regional-bento-original'
            detail = {'schemaVersion': 'offmenu-private-original-save-detail/1',
                'sourceKey': key, 'selectionSHA256': contract, 'status': 'failed',
                'errorCode': 'source-header-mismatch', 'privateSaveState': 'partial-retained',
                'localBodyBytes': len(body), 'network': {'requests': 1, 'bodyBytesRead': len(body)},
                'responseMetadata': {'httpStatus': 200, 'contentType': 'application/pdf'}}
            raw = m.canonical(detail)
            detail_sha = hashlib.sha256(raw).hexdigest()
            detail_path = self.work / ('private-original-result-' + detail_sha + '.json')
            self.write(detail_path, raw)
            folder = self.work / 'private-originals' / contract
            folder.mkdir(mode=0o700, exist_ok=True)
            intent = {'schemaVersion': 'offmenu-private-original-successor/1',
                'sourceKey': key, 'sourceContractSHA256': contract,
                'url': 'https://erb.afa.gov.tw/index.php?act=download&ids=' + number,
                'owner': os.getuid(), 'ownerHandover': m.HANDOVER,
                'state': 'failed-no-retry', 'errorCode': 'source-header-mismatch',
                'privateSaveState': 'partial-retained', 'localBodyBytes': len(body),
                'network': {'requests': 1, 'bodyBytesRead': len(body)}}
            self.write(folder / 'successor-intent.json', m.canonical(intent))
            self.write(folder / 'original.partial', body)
            entries.append((number, contract, detail_sha, len(body)))
            self.folders.append(folder)
            self.details.append(detail_path)
        self.stack.enter_context(patch.object(m, 'ENTRIES', tuple(entries)))

    def run_diagnostics(self, deadline=None):
        return m.run_diagnostics(self.root, time.monotonic() + 30 if deadline is None else deadline)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode,
            p.stat().st_ino, p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}

    def test_complete_no_source_writes_no_network_no_raw_bytes(self):
        before = self.snapshot()
        report = self.run_diagnostics()
        self.assertEqual(report['status'], 'complete', report)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(report['networkRequests'], 0)
        self.assertFalse(report['historicalBodyIdentityEstablished'])
        raw = m.canonical(report)
        self.assertLess(len(raw), 16384)
        self.assertNotIn(b'private synthetic text', raw)
        self.assertNotIn(str(self.root).encode(), raw)
        for item in report['items']:
            self.assertEqual(item['observedBodySHA256'], hashlib.sha256(BODY).hexdigest())
            self.assertEqual(item['boundaryFacts']['currentValidatorFailurePoint'], 'none')
        self.assertEqual(self.run_diagnostics(), report)

    def test_distinguishes_prefix_from_terminal_eof_without_acceptance(self):
        self.install([b'\xef\xbb\xbf' + BODY, BODY + b'trailing', b'<html>private synthetic text</html>'])
        report = self.run_diagnostics()
        self.assertEqual(report['status'], 'complete')
        facts = [item['boundaryFacts'] for item in report['items']]
        self.assertEqual([f['currentValidatorFailurePoint'] for f in facts], ['pdf-prefix', 'pdf-terminal-eof', 'pdf-prefix'])
        self.assertEqual(facts[0]['prefixClassification'], 'utf8-bom-before-pdf')
        self.assertEqual(facts[0]['pdfSignatureOffsetInFirst1024'], 3)
        self.assertEqual(facts[1]['bytesAfterLastEOF'], 9)
        self.assertEqual(facts[2]['prefixClassification'], 'html-like-prefix')
        self.assertFalse(report['acquisitionEnabled'])

    def test_whitespace_and_eof_window_match_current_strict_rules(self):
        self.install([b' \r\n' + BODY, BODY + b'\x00\t\x0c\r\n ', BODY + b' ' * 4096])
        report = self.run_diagnostics()
        facts = [item['boundaryFacts'] for item in report['items']]
        self.assertEqual(facts[0]['prefixClassification'], 'pdf-whitespace-before-pdf')
        self.assertTrue(facts[1]['terminalEOFMatchesCurrentRule'])
        self.assertFalse(facts[2]['terminalEOFMatchesCurrentRule'])
        self.assertIsNone(facts[2]['lastEOFOffsetFromEnd'])

    def test_full_hash_and_bounded_windows_for_actual_extent(self):
        self.install([BODY[:-6] + b'X' * 2290000 + b'%%EOF\n'] * 3)
        report = self.run_diagnostics()
        for item in report['items']:
            self.assertEqual(item['boundaryFacts']['prefixWindowBytes'], 1024)
            self.assertEqual(item['boundaryFacts']['tailWindowBytes'], 4096)
            self.assertEqual(item['localBodyBytesRead'], item['expectedLocalBytes'])

    def test_pinned_detail_mutation_blocks_body_read(self):
        self.write(self.details[0], b'{}')
        report = self.run_diagnostics()
        self.assertEqual(report['items'][0]['errorCode'], 'metadata-pin-mismatch')
        self.assertEqual(report['items'][0]['localBodyBytesRead'], 0)
        self.assertEqual(report['items'][1]['status'], 'observed')

    def test_detail_expected_fields_are_bound_even_if_hash_matches(self):
        raw = json.loads(self.details[0].read_bytes())
        raw['responseMetadata']['contentType'] = 'text/html'
        encoded = m.canonical(raw)
        digest = hashlib.sha256(encoded).hexdigest()
        self.write(self.work / ('private-original-result-' + digest + '.json'), encoded)
        entries = list(m.ENTRIES)
        number, contract, _, size = entries[0]
        entries[0] = (number, contract, digest, size)
        with patch.object(m, 'ENTRIES', tuple(entries)):
            self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'prior-failure-evidence-mismatch')

    def test_failed_intent_state_and_source_bindings(self):
        path = self.folders[0] / 'successor-intent.json'
        original = path.read_bytes()
        for key, value in [('state', 'verified'), ('sourceContractSHA256', 'a' * 64),
                ('url', 'https://other.example/'), ('owner', os.getuid() + 1), ('ownerHandover', {}),
                ('localBodyBytes', 0), ('network', {'requests': 0, 'bodyBytesRead': 0})]:
            with self.subTest(key=key):
                intent = json.loads(original)
                intent[key] = value
                self.write(path, m.canonical(intent))
                item = self.run_diagnostics()['items'][0]
                self.assertEqual(item['errorCode'], 'failed-intent-mismatch')
                self.assertEqual(item['localBodyBytesRead'], 0)
        self.write(path, original)

    def test_malformed_deep_intent_is_safe_per_item_failure(self):
        path = self.folders[0] / 'successor-intent.json'
        self.write(path, b'[' * 2000 + b'0' + b']' * 2000)
        report = self.run_diagnostics()
        self.assertIn(report['items'][0]['errorCode'], {'local-read-failed', 'metadata-pin-mismatch'})
        self.assertEqual(report['items'][0]['localBodyBytesRead'], 0)
        self.assertEqual(report['items'][1]['status'], 'observed')

    def test_boundary_predicates_match_unchanged_acquisition_validator(self):
        from types import SimpleNamespace
        spec = importlib.util.spec_from_file_location('taiwan_unchanged_validator', ROOT / 'scripts/acquire-fixed-zenodo.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        source = {'schemaVersion': 'offmenu-fixed-source-contract/1', 'sourceKey': 'synthetic',
            'url': 'https://example.invalid/no-network', 'expectedBytes': None,
            'hardTransferBytes': 16777216, 'wholeOperationSeconds': 30,
            'checksums': {}, 'validation': {'kind': 'pdf-original'}}
        cases = [BODY, b'\xef\xbb\xbf' + BODY, b' \r\n' + BODY, BODY + b'garbage',
            b'<html>denied</html>', BODY + b'\x00\t\x0c\r\n ', BODY + b' ' * 4096,
            b'%PDF-no-version\n%%EOF\n', b'%PDF-1.7\nno terminal marker', b'%%EOF\n']
        for index, body in enumerate(cases):
            with self.subTest(index=index):
                path = self.root / 'synthetic.pdf'
                self.write(path, body)
                result = SimpleNamespace(path=path, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                    provenance={'originalAcquiredAt': '2026-10-18T22:35:00+00:00'})
                facts = m.boundary_facts(body[:1024], body[-4096:], len(body))
                if facts['currentValidatorFailurePoint'] == 'none':
                    self.assertTrue(adapter.validate_original(result, source, time.monotonic() + 30)['headerVerified'])
                else:
                    with self.assertRaisesRegex(adapter.RefreshError, '^source-header-mismatch$'):
                        adapter.validate_original(result, source, time.monotonic() + 30)

    def test_missing_partial_and_changed_extent_are_blocked(self):
        (self.folders[0] / 'original.partial').unlink()
        self.write(self.folders[1] / 'original.partial', BODY + b'changed')
        report = self.run_diagnostics()
        self.assertEqual(report['items'][0]['errorCode'], 'local-read-failed')
        self.assertEqual(report['items'][1]['errorCode'], 'partial-extent-mismatch')
        self.assertEqual(report['items'][2]['status'], 'observed')

    def test_no_symlink_file_or_ancestor_and_no_alias_hardlinks(self):
        path = self.folders[0] / 'original.partial'
        path.unlink()
        path.symlink_to(self.folders[1] / 'original.partial')
        self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'local-read-failed')
        path.unlink()
        os.link(self.folders[1] / 'original.partial', path)
        self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'unsafe-custody-file')
        path.unlink()
        self.write(path, BODY)
        folder = self.folders[0]
        moved = folder.with_name('moved')
        folder.rename(moved)
        folder.symlink_to(moved, target_is_directory=True)
        self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'local-read-failed')

    def test_symlink_root_ancestor_rejected(self):
        link = self.root / 'alias'
        link.symlink_to(self.root, target_is_directory=True)
        with patch.object(m, 'OUTPUT_ROOT', link):
            report = m.run_diagnostics(link, time.monotonic() + 30)
        self.assertTrue(all(item['errorCode'] == 'root-unavailable' for item in report['items']))

    def test_world_readable_body_and_nonregular_body_rejected(self):
        path = self.folders[0] / 'original.partial'
        path.chmod(0o644)
        self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'unsafe-custody-file')
        path.unlink()
        os.mkfifo(path, 0o600)
        self.assertEqual(self.run_diagnostics()['items'][0]['errorCode'], 'unsafe-custody-file')

    def test_known_custody_conflicts_are_observed_without_modification(self):
        for name in ('original.pdf', 'provenance.json', 'reservation.bin'):
            path = self.folders[0] / name
            self.write(path, b'preserve')
            report = self.run_diagnostics()
            self.assertEqual(report['items'][0]['errorCode'], 'custody-state-conflict')
            self.assertEqual(path.read_bytes(), b'preserve')
            path.unlink()

    def test_owner_identity_and_wrong_root_are_rejected(self):
        with patch.object(m, 'EXPECTED_UID', os.getuid() + 1):
            report = self.run_diagnostics()
        self.assertTrue(all(i['errorCode'] == 'owner-identity-mismatch' for i in report['items']))
        report = m.run_diagnostics(self.root / 'other', time.monotonic() + 30)
        self.assertTrue(all(i['errorCode'] == 'unsafe-custody-path' for i in report['items']))

    def test_deadline_has_no_body_read(self):
        report = self.run_diagnostics(0)
        self.assertTrue(all(i['errorCode'] == 'diagnostic-deadline-exceeded' for i in report['items']))
        self.assertEqual(sum(i['localBodyBytesRead'] for i in report['items']), 0)

    def test_partial_change_during_read_drops_observations(self):
        real = m.os.read
        changed = False
        def read(fd, size):
            nonlocal changed
            raw = real(fd, size)
            if raw.startswith(b'%PDF-') and not changed:
                changed = True
                path = self.folders[0] / 'original.partial'
                self.write(path, b'%PDF-1.7\nchanged same-length contents')
            return raw
        with patch.object(m.os, 'read', side_effect=read):
            report = self.run_diagnostics()
        item = report['items'][0]
        self.assertEqual(item['errorCode'], 'custody-changed-during-read')
        self.assertIsNone(item['observedBodySHA256'])
        self.assertIsNone(item['boundaryFacts'])

    def test_closed_sanitizer_rejects_raw_fields_and_promoted_claims(self):
        report = self.run_diagnostics()
        for edit in [lambda r: r.update(raw='secret'),
                lambda r: r.update(networkRequests=1),
                lambda r: r.update(historicalBodyIdentityEstablished=True),
                lambda r: r['items'][0].update(raw='secret'),
                lambda r: r['items'][0]['boundaryFacts'].update(raw='secret'),
                lambda r: r['items'][0]['boundaryFacts'].update(currentValidatorFailurePoint='pdf-prefix'),
                lambda r: r['items'][0]['boundaryFacts'].update(pdfSignatureOffsetInFirst1024=5000),
                lambda r: r['items'][0].update(observedBodySHA256='secret'),
                lambda r: r['items'][0].update(sourceKey='unselected')]:
            with self.subTest(edit=edit):
                bad = deepcopy(report)
                edit(bad)
                with self.assertRaises(ValueError):
                    m.sanitize_diagnostics(bad)

    def test_no_transport_or_parser_import_or_file_mutation_api(self):
        import ast
        tree = ast.parse((ROOT / 'scripts/diagnose-retained-taiwan.py').read_text())
        imports = {n.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names}
        self.assertFalse(imports & {'socket', 'ssl', 'http', 'urllib', 'requests', 'subprocess', 'pypdf'})
        forbidden = {'write', 'write_bytes', 'write_text', 'unlink', 'remove', 'rename', 'replace', 'link', 'chmod', 'fchmod', 'ftruncate', 'truncate', 'mkdir', 'makedirs'}
        self.assertFalse({node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)} & forbidden)


if __name__ == '__main__':
    unittest.main()
