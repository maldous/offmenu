"""SAME45 F1/F2 regressions using only new, temporary authored objects."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio56 as m
from offmenu.refresh.core import RefreshError, canonical, sha

NOW = '2026-10-18T00:00:00Z'


def fixture(path):
    raw = canonical({'acquired': '2026-10-10T00:00:00Z', 'unit': 'mg/d', 'zero': 0, 'basis': None})
    binding = {'sourceId': 'reader-delta-authored', 'releaseId': 'only-fixture',
        'countries': ['WF'], 'domains': ['nutrition'],
        'metadata': {'path': str(path), 'sha256': sha(raw)},
        'acquiredAtSelector': '/acquired', 'fields': {'unit': '/unit', 'zero': '/zero', 'basis': '/basis'},
        'unknowns': [], 'holds': [], 'adapter': None}
    return binding, raw


def report_fixture():
    b, raw = fixture('/authored/metadata.json')
    return m.plan([b], now=NOW, reader=lambda _: raw)


def fifo_probe(which):
    """Child only: any regression blocks at most the parent's2second timeout."""
    with TemporaryDirectory() as t:
        root = Path(t)
        report, body = report_fixture()
        if which == 'config':
            path = root / 'config.json'; os.mkfifo(path)
            operation = lambda: m.main(['--config', str(path), '--now', NOW, '--output', str(root / 'out')])
        else:
            out = root / 'out'; out.mkdir()
            if which == 'metadata-candidates.jsonl':
                (out / 'plan.json').write_bytes(canonical(report))
            os.mkfifo(out / which)
            operation = lambda: m.write_plan(report, body, out)
        try:
            operation()
        except RefreshError:
            return
        raise AssertionError('FIFO was not rejected')


def swap_probe(kind):
    with TemporaryDirectory() as t:
        root = Path(t); p = root / 'metadata.json'; other = root / 'other.json'
        binding, raw = fixture(p); p.write_bytes(raw); other.write_bytes(b'{"unexpected":true}\n')
        original_open = os.open; swapped = []
        def race(name, flags, *args, **kwargs):
            if name == 'metadata.json' and kwargs.get('dir_fd') is not None:
                p.unlink()
                if kind == 'symlink': p.symlink_to(other)
                elif kind == 'regular': other.rename(p)
                elif kind == 'fifo': os.mkfifo(p)
                swapped.append(True)
            return original_open(name, flags, *args, **kwargs)
        with patch.object(m.os, 'open', race), patch.object(m.os, 'read', side_effect=AssertionError('replacement read')):
            try:
                m.read_metadata(binding)
            except RefreshError:
                pass
            else:
                raise AssertionError('replacement was accepted')
        assert swapped


class ReaderDeltaTests(unittest.TestCase):
    def child(self, function, argument):
        call = f'from tests.test_portfolio56_reader_delta import {function}; {function}({argument!r})'
        process = subprocess.Popen([sys.executable, '-B', '-c', call], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate()
            self.fail('authored child exceeded2seconds; killed/reaped')
        self.assertEqual(process.returncode, 0, stderr.decode())

    def test_F1_both_replay_fifos_rejected_without_block(self):
        for name in ['plan.json', 'metadata-candidates.jsonl']:
            with self.subTest(name=name): self.child('fifo_probe', name)

    def test_config_fifo_uses_same_bounded_ingress(self):
        self.child('fifo_probe', 'config')

    def test_F2_substituted_symlink_regular_and_fifo_never_read(self):
        for kind in ['symlink', 'regular', 'fifo']:
            with self.subTest(kind=kind): self.child('swap_probe', kind)

    def test_positive_metadata_and_clock_only_replay_controls(self):
        with TemporaryDirectory() as t:
            p = Path(t) / 'metadata.json'; b, raw = fixture(p); p.write_bytes(raw)
            self.assertEqual(m.read_metadata(b), raw)
            result = m.assess(b, raw, now=NOW)
            self.assertEqual(result['record']['data'], {'unit': 'mg/d', 'zero': 0, 'basis': None})
            self.assertFalse(result['stageExecutionAuthorized'])
            report, body = m.plan([b], now=NOW)
            out = Path(t) / 'out'; m.write_plan(report, body, out)
            original = (out / 'plan.json').read_bytes()
            later, later_body = m.plan([b], now='2026-10-19T00:00:00Z')
            self.assertEqual(m.write_plan(later, later_body, out), 'no-op-verified-metadata-cache')
            self.assertEqual(original, (out / 'plan.json').read_bytes())

    def test_oversized_replay_files_reject_and_never_overwrite(self):
        report, body = report_fixture()
        for name in ['plan.json', 'metadata-candidates.jsonl']:
            with self.subTest(name=name), TemporaryDirectory() as t:
                out = Path(t) / 'out'; m.write_plan(report, body, out)
                p = out / name
                p.write_bytes(b'x' * 16385)
                before = p.read_bytes()
                with patch.object(m, 'REPLAY_LIMIT', 16384):
                    with self.assertRaises(RefreshError): m.write_plan(report, body, out)
                self.assertEqual(p.read_bytes(), before)

    def test_malformed_and_changed_replay_are_fixed_rejections(self):
        report, body = report_fixture()
        for raw in [b'not json', b'null', b'{"results":null}']:
            with self.subTest(raw=raw), TemporaryDirectory() as t:
                out = Path(t) / 'out'; m.write_plan(report, body, out)
                (out / 'plan.json').write_bytes(raw)
                with self.assertRaisesRegex(RefreshError, '^replay-input-rejected$'):
                    m.write_plan(report, body, out)
        with TemporaryDirectory() as t:
            out = Path(t) / 'out'; m.write_plan(report, body, out)
            (out / 'metadata-candidates.jsonl').write_bytes(b'changed')
            with self.assertRaisesRegex(RefreshError, '^output-conflict-use-new-directory$'):
                m.write_plan(report, body, out)

    def test_replay_result_rows_reject_null_and_scalars_without_overwrite(self):
        report, body = report_fixture()
        for row in [None, False, 0, 1.5, 'row', []]:
            with self.subTest(row=row), TemporaryDirectory() as t:
                out = Path(t) / 'out'; m.write_plan(report, body, out)
                malformed = deepcopy(report)
                malformed['results'] = [report['results'][0], row]
                raw = canonical(malformed)
                (out / 'plan.json').write_bytes(raw)
                with self.assertRaisesRegex(RefreshError, '^replay-input-rejected$'):
                    m.write_plan(report, body, out)
                self.assertEqual((out / 'plan.json').read_bytes(), raw)
                self.assertEqual((out / 'metadata-candidates.jsonl').read_bytes(), body)

    def test_hardlinks_and_directory_objects_reject_before_read(self):
        with TemporaryDirectory() as t:
            p = Path(t) / 'metadata.json'; b, raw = fixture(p); p.write_bytes(raw)
            os.link(p, Path(t) / 'alias.json')
            with patch.object(m.os, 'read', side_effect=AssertionError('hardlink read')):
                with self.assertRaises(RefreshError): m.read_metadata(b)
            (Path(t) / 'alias.json').unlink(); p.unlink(); p.mkdir()
            with self.assertRaises(RefreshError): m.read_metadata(b)

    def test_in_place_growth_during_read_is_bounded(self):
        with TemporaryDirectory() as t:
            p = Path(t) / 'metadata.json'; p.write_bytes(b'12345678')
            original_read = os.read; calls = []
            def growing(fd, amount):
                calls.append(amount)
                block = original_read(fd, amount)
                if len(calls) == 1:
                    with p.open('ab') as out: out.write(b'9')
                return block
            with patch.object(m.os, 'read', growing):
                with self.assertRaises(RefreshError): m._read_regular(p, limit=8)
            self.assertLessEqual(max(calls), 9)

    def test_config_substitution_rejected_before_plan(self):
        with TemporaryDirectory() as t:
            root = Path(t); p = root / 'config.json'; other = root / 'other.json'
            p.write_bytes(b'{}'); other.write_bytes(b'{"unexpected":true}')
            original_open = os.open
            def race(name, flags, *args, **kwargs):
                if name == 'config.json' and kwargs.get('dir_fd') is not None:
                    p.unlink(); other.rename(p)
                return original_open(name, flags, *args, **kwargs)
            with patch.object(m.os, 'open', race), patch.object(m, 'plan', side_effect=AssertionError('unexpected plan')):
                with self.assertRaisesRegex(RefreshError, '^portfolio-config-read-rejected$'):
                    m.main(['--config', str(p), '--now', NOW, '--output', str(root / 'out')])

    def test_empty_held_cache_and_config_body_path(self):
        b, raw = fixture('/authored/metadata.json'); b['holds'] = ['source-no-read']
        report, body = m.plan([b], now=NOW, reader=lambda _: raw)
        self.assertEqual(body, b'')
        with TemporaryDirectory() as t:
            out = Path(t) / 'out'; m.write_plan(report, body, out)
            self.assertEqual(m.write_plan(report, body, out), 'no-op-verified-metadata-cache')
            with patch.object(m.os, 'open', side_effect=AssertionError('body opened')):
                with self.assertRaisesRegex(RefreshError, '^portfolio-config-json-only$'):
                    m.main(['--config', str(Path(t) / 'original.response'), '--now', NOW,
                            '--output', str(Path(t) / 'unused')])

    def test_peer_hold_missing_input_and_body_path_still_fail_closed(self):
        with TemporaryDirectory() as t:
            root = Path(t); p = root / 'metadata.json'; b, raw = fixture(p); p.write_bytes(raw)
            held = deepcopy(b); held['sourceId'] = 'held'; held['holds'] = ['retained-no-read']
            missing = deepcopy(b); missing['sourceId'] = 'missing'; missing['metadata']['path'] = str(root / 'absent.json')
            report, _ = m.plan([held, missing, b], now=NOW)
            self.assertEqual([r['status'] for r in report['results']], ['held', 'missing', 'ready-metadata-candidate'])
            b['metadata']['path'] = str(root / 'original.response')
            with patch.object(m.os, 'open', side_effect=AssertionError('body opened')):
                with self.assertRaisesRegex(RefreshError, '^metadata-json-only-no-source-body$'): m.read_metadata(b)


if __name__ == '__main__':
    unittest.main()
