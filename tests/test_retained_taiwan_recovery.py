"""Inactive recovery-proposal tests: synthetic bytes and local installed parsers."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch
import test_retained_taiwan_diagnostic as fixture_module

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('retained_tw_recovery_test', ROOT / 'scripts/validate-retained-taiwan.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def pdf(bom=True):
    parts = [b'%PDF-1.4\n']
    offsets = []
    text = b'BT /F1 12 Tf 10 100 Td (Synthetic private text) Tj ET\n'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length ' + str(len(text)).encode() + b' >>\nstream\n' + text + b'endstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for number, obj in enumerate(objects, 1):
        offsets.append(sum(map(len, parts)))
        parts.append(str(number).encode() + b' 0 obj\n' + obj + b'\nendobj\n')
    xref = sum(map(len, parts))
    parts.append(b'xref\n0 6\n0000000000 65535 f \n' +
        b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets) +
        b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + str(xref).encode() + b'\n%%EOF\r\n')
    return (b'\xef\xbb\xbf' if bom else b'') + b''.join(parts)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.DiagnosticTests()
        self.fixture.setUp()
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(r, 'd', fixture_module.m))
        self.sources = [s for s in json.loads((ROOT / 'docs/collection-selections/global-original-selection.json').read_bytes())['sources']
            if s['sourceKey'] in r.PINS]
        self.sources.sort(key=lambda s: s['sourceKey'])
        self.install([pdf()] * 3)

    def tearDown(self):
        self.stack.close()
        self.fixture.tearDown()

    def install(self, bodies):
        self.fixture.install(bodies)
        pins = {source['sourceKey']: {'bodySHA256': hashlib.sha256(body).hexdigest(),
            'intentSHA256': hashlib.sha256((folder / 'successor-intent.json').read_bytes()).hexdigest()}
            for source, body, folder in zip(self.sources, bodies, self.fixture.folders)}
        self.stack.enter_context(patch.object(r, 'PINS', pins))

    def validate(self, index=0):
        return r.validate_selected(self.sources[index], self.fixture.root, time.monotonic() + 30)

    def test_actual_source_contract_serialization_matches_all_three_pins(self):
        for source in self.sources:
            entry = r.selected_entry(source)
            self.assertEqual(source['sourceKey'], r.d.item_template(entry)['sourceKey'])

    def test_each_exact_source_is_independently_bound_and_validated(self):
        for index in range(3):
            result = self.validate(index)
            self.assertEqual(result['status'], 'validated-proposal', result)
            self.assertEqual(result['sourceKey'], self.sources[index]['sourceKey'])

    def test_valid_bom_pdf_proposal_preserves_every_custody_byte(self):
        before = self.fixture.snapshot()
        result = self.validate()
        self.assertEqual(result['status'], 'validated-proposal', result)
        self.assertEqual(self.fixture.snapshot(), before)
        self.assertFalse(result['dispositionApplied'])
        self.assertFalse(result['strictISOConformanceEstablished'])
        self.assertFalse(result['publisherChecksumEstablished'])
        self.assertIsNone(result['proposedDisposition']['originalAcquiredAt'])
        self.assertEqual(result['parser']['pageCount'], 1)
        self.assertTrue(result['parser']['allPagesTraversed'])
        self.assertEqual(result['parser']['diagnosticBytes'], 0)
        self.assertNotIn('Synthetic private text', json.dumps(result))
        self.assertEqual(self.validate(), result)

    def test_exact_exception_excludes_unselected_source_or_changed_contract(self):
        source = deepcopy(self.sources[0])
        source['sourceKey'] = 'other-source'
        self.assertEqual(r.validate_selected(source, self.fixture.root, time.monotonic() + 30)['errorCode'], 'recovery-source-unselected')
        source = deepcopy(self.sources[0])
        source['url'] += '&other=1'
        self.assertEqual(r.validate_selected(source, self.fixture.root, time.monotonic() + 30)['errorCode'], 'recovery-source-unselected')

    def test_same_length_body_change_or_new_intent_digest_is_blocked(self):
        path = self.fixture.folders[0] / 'original.partial'
        raw = path.read_bytes()
        self.fixture.write(path, raw.replace(b'Synthetic', b'Different'))
        self.assertEqual(self.validate()['errorCode'], 'recovery-identity-mismatch')
        self.fixture.write(path, raw)
        intent = self.fixture.folders[0] / 'successor-intent.json'
        value = json.loads(intent.read_bytes())
        value['unselectedAddition'] = True
        self.fixture.write(intent, r.d.canonical(value))
        self.assertEqual(self.validate()['errorCode'], 'recovery-identity-mismatch')

    def test_signature_only_malformed_pdf_cannot_be_promoted(self):
        self.install([b'\xef\xbb\xbf%PDF-1.7\nprivate invalid object\n%%EOF\r\n'] * 3)
        result = self.validate()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['errorCode'], 'parser-invalid-input')
        self.assertGreater(result['parser']['diagnosticBytes'], 0)
        self.assertIsNone(result['proposedDisposition'])
        self.assertNotIn('private invalid object', json.dumps(result))

    def test_no_generic_preamble_or_bom_normalization(self):
        for body in (pdf(False), b' ' + pdf(False), b'\xef\xbb\xbf\xef\xbb\xbf' + pdf(False), pdf() + b'trailer-garbage'):
            with self.subTest(prefix=body[:8]):
                self.install([body] * 3)
                result = self.validate()
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['errorCode'], 'recovery-boundary-mismatch')

    def test_parser_unavailable_is_explicit_not_a_pass(self):
        with patch.dict(r.TOOLS, {'pdfinfo': '/nonexistent/offmenu-no-parser'}):
            result = self.validate()
        self.assertEqual(result['errorCode'], 'parser-unavailable')
        self.assertIsNone(result['proposedDisposition'])

    def test_missing_resource_limit_tool_blocks(self):
        with patch.dict(r.TOOLS, {'limit': '/nonexistent/offmenu-no-limit-tool'}):
            result = self.validate()
        self.assertEqual(result['errorCode'], 'parser-isolation-unavailable')

    def test_encrypted_pdf_and_page_limits_do_not_request_passwords(self):
        real = r.run_tool
        for encrypted, pages, expected in [(b'yes', 1, 'pdf-encrypted'), (b'no', 2001, 'pdf-page-limit')]:
            def tool(*args, **kwargs):
                if args[1] == ['-v']:
                    return real(*args, **kwargs)
                return {'returnCode': 0, 'stdout': b'Encrypted: ' + encrypted + b'\nPages: ' + str(pages).encode() + b'\n',
                    'stdoutBytes': 40, 'diagnosticBytes': 0}
            with patch.object(r, 'run_tool', side_effect=tool) as call:
                result = self.validate()
            self.assertEqual(result['errorCode'], expected)
            self.assertEqual(call.call_count, 3)

    def test_parser_warning_is_not_silently_accepted(self):
        real = r.run_tool
        def tool(*args, **kwargs):
            if args[1] == ['-v']:
                return real(*args, **kwargs)
            return {'returnCode': 0, 'stdout': b'Encrypted: no\nPages: 1\n', 'stdoutBytes': 23, 'diagnosticBytes': 5}
        with patch.object(r, 'run_tool', side_effect=tool):
            result = self.validate()
        self.assertEqual(result['errorCode'], 'parser-diagnostic-present')

    def test_unchanged_check_after_parser_catches_mutation(self):
        real = r.parser_check
        def parser(data, deadline):
            result = real(data, deadline)
            path = self.fixture.folders[0] / 'original.partial'
            self.fixture.write(path, path.read_bytes().replace(b'Synthetic', b'Different'))
            return result
        with patch.object(r, 'parser_check', side_effect=parser):
            result = self.validate()
        self.assertEqual(result['errorCode'], 'custody-changed-during-read')
        self.assertIsNone(result['proposedDisposition'])

    def test_parent_path_replacement_after_parser_is_blocked(self):
        real = r.parser_check
        def parser(data, deadline):
            result = real(data, deadline)
            folder = self.fixture.folders[0]
            folder.rename(folder.with_name('retained-orphan'))
            folder.mkdir(mode=0o700)
            return result
        with patch.object(r, 'parser_check', side_effect=parser):
            result = self.validate()
        self.assertEqual(result['errorCode'], 'custody-changed-during-read')
        self.assertIsNone(result['proposedDisposition'])

    def test_parser_environment_excludes_credentials_and_uses_fixed_tools(self):
        real = r.subprocess.Popen
        seen = []
        def launch(*args, **kwargs):
            seen.append((args, kwargs))
            return real(*args, **kwargs)
        with patch.dict(os.environ, {'GH_TOKEN': 'never-inherit-this'}), patch.object(r.subprocess, 'Popen', side_effect=launch):
            result = self.validate()
        self.assertEqual(result['status'], 'validated-proposal')
        self.assertEqual(len(seen), 4)
        for args, kwargs in seen:
            self.assertNotIn('GH_TOKEN', kwargs['env'])
            self.assertNotIn('never-inherit-this', str(args))
            self.assertFalse(kwargs.get('shell', False))
        for args, kwargs in seen:
            self.assertEqual(args[0][0], '/usr/bin/prlimit')
            self.assertIn('--fsize=0', args[0])
            self.assertTrue(kwargs['start_new_session'])

    def test_output_limit_is_bounded(self):
        with self.assertRaisesRegex(ValueError, 'parser-output-limit'):
            r.run_tool('pdfinfo', ['-'], pdf(), time.monotonic() + 10, 1)

    def test_deadline_is_explicit(self):
        result = r.validate_selected(self.sources[0], self.fixture.root, 0)
        self.assertEqual(result['errorCode'], 'diagnostic-deadline-exceeded')

    def test_closed_report_forbids_unselected_promotions_and_raw_diagnostics(self):
        result = self.validate()
        for edit in (lambda r: r.update(dispositionApplied=True), lambda r: r.update(raw='private'),
                lambda r: r['parser'].update(raw='private'), lambda r: r['proposedDisposition'].update(relativePath='/other'),
                lambda r: r.update(retainedSHA256='f' * 64), lambda r: r.update(strictISOConformanceEstablished=True),
                lambda r: r['parser'].update(allPagesTraversed=False)):
            changed = deepcopy(result)
            edit(changed)
            with self.assertRaises(ValueError):
                r.sanitize_report(changed)


class ParserLifecycleTests(unittest.TestCase):
    def owner_termination_probe(self, mode, signum=signal.SIGTERM):
        """A separate owner uses only a synthetic local sleep process."""
        with tempfile.TemporaryDirectory() as folder:
            pid_path = Path(folder) / 'child-pid'
            program = textwrap.dedent('''
                import importlib.util, os, pathlib, signal, sys, time
                spec = importlib.util.spec_from_file_location('signal_probe', sys.argv[1])
                r = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(r)
                mode, signum = sys.argv[3], int(sys.argv[4])
                real = r.subprocess.Popen
                def launch(command, **kwargs):
                    if mode == 'before-spawn':
                        os.kill(os.getpid(), signum)
                    if mode == 'version-probe':
                        command = command[:command.index('--') + 1] + ['/usr/bin/python3', '-c', 'import time; time.sleep(30)']
                    child = real(command, **kwargs)
                    pathlib.Path(sys.argv[2]).write_text(str(child.pid))
                    if mode == 'assignment-race':
                        os.kill(os.getpid(), signum)
                    return child
                r.subprocess.Popen = launch
                r.TOOLS['pdfinfo'] = '/usr/bin/python3'
                if mode == 'version-probe':
                    r.parser_check(b'', time.monotonic() + 30)
                else:
                    r.run_tool('pdfinfo', ['-c', 'import time; time.sleep(30)'], b'', time.monotonic() + 30, 100)
            ''')
            owner = subprocess.Popen([sys.executable, '-c', program,
                str(ROOT / 'scripts/validate-retained-taiwan.py'), str(pid_path), mode, str(signum)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child_pid = None
            try:
                until = time.monotonic() + 5
                while time.monotonic() < until:
                    if pid_path.exists() and pid_path.read_text():
                        child_pid = int(pid_path.read_text())
                        break
                    if owner.poll() is not None:
                        break
                    time.sleep(0.01)
                self.assertIsNotNone(child_pid, owner.communicate(timeout=2) if owner.poll() is not None else 'no child pid')
                if mode in ('running', 'version-probe'):
                    owner.send_signal(signum)
                stdout, stderr = owner.communicate(timeout=5)
                self.assertEqual(owner.returncode, -signum, (stdout, stderr))
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)
                return {'mode': mode, 'ownerExit': owner.returncode,
                    'parserStillExistsAfterOwnerSignal': False, 'signal': signum}
            finally:
                if owner.poll() is None:
                    owner.kill()
                    owner.wait()
                if child_pid is not None:
                    try:
                        os.killpg(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                for stream in (owner.stdout, owner.stderr):
                    stream.close()

    def test_owner_sigterm_kills_and_reaps_running_parser(self):
        self.owner_termination_probe('running')

    def test_owner_sigterm_during_popen_assignment_kills_and_reaps_parser(self):
        self.owner_termination_probe('assignment-race')

    def test_owner_sigterm_before_spawn_still_registers_and_reaps_parser(self):
        self.owner_termination_probe('before-spawn')

    def test_owner_sigterm_also_cleans_up_version_probe(self):
        self.owner_termination_probe('version-probe')

    def test_owner_sighup_kills_and_reaps_running_parser(self):
        self.owner_termination_probe('running', signal.SIGHUP)

    def test_prior_handlers_restored_after_success_and_deadline(self):
        signals = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        before = {signum: signal.getsignal(signum) for signum in signals}
        r.run_tool('pdfinfo', ['-'], pdf(), time.monotonic() + 10, 65536)
        self.assertEqual({signum: signal.getsignal(signum) for signum in signals}, before)
        with patch.dict(r.TOOLS, {'pdfinfo': '/usr/bin/python3'}):
            with self.assertRaisesRegex(ValueError, 'diagnostic-deadline-exceeded'):
                r.run_tool('pdfinfo', ['-c', 'import time; time.sleep(30)'], b'', time.monotonic() + 0.1, 100)
        self.assertEqual({signum: signal.getsignal(signum) for signum in signals}, before)

    def test_custom_handler_runs_only_after_cleanup_and_restoration(self):
        signals = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        before = {signum: signal.getsignal(signum) for signum in signals}
        children, delivered = [], []
        real = r.subprocess.Popen
        def previous(signum, frame):
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)
            self.assertEqual(signal.getsignal(signal.SIGINT), before[signal.SIGINT])
            self.assertEqual(signal.getsignal(signal.SIGHUP), before[signal.SIGHUP])
            self.assertIsNotNone(children[0].returncode)
            with self.assertRaises(ProcessLookupError):
                os.kill(children[0].pid, 0)
            delivered.append(signum)
        def launch(*args, **kwargs):
            child = real(*args, **kwargs)
            children.append(child)
            os.kill(os.getpid(), signal.SIGTERM)
            return child
        try:
            signal.signal(signal.SIGTERM, previous)
            with patch.object(r.subprocess, 'Popen', side_effect=launch):
                with self.assertRaisesRegex(ValueError, 'parser-interrupted'):
                    r.run_tool('pdfinfo', ['-'], pdf(), time.monotonic() + 10, 65536)
            self.assertEqual(delivered, [signal.SIGTERM])
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)
        finally:
            for signum, handler in before.items():
                signal.signal(signum, handler)

    def test_non_main_thread_blocks_before_child_launch(self):
        failures = []
        def worker():
            try:
                r.run_tool('pdfinfo', ['-'], pdf(), time.monotonic() + 10, 65536)
            except ValueError as error:
                failures.append(str(error))
        with patch.object(r.subprocess, 'Popen') as launch:
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, ['parser-isolation-unavailable'])
        launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
