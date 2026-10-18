"""Focused W32-W44-15CE-F1/F2 authored regressions; no retained data IO."""
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio44 as m
from tests.test_portfolio44 import fixture, NOW


class Portfolio44CorrectionTests(unittest.TestCase):
    def test_nonregular_ingress_and_replacement_are_bounded_in_child(self):
        child = r'''
from dataclasses import replace
import json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from offmenu.refresh import portfolio44 as m
from offmenu.refresh.portfolio44_catalog import BINDINGS
from tests.test_portfolio44 import fixture,NOW
mode=sys.argv[1]
with tempfile.TemporaryDirectory() as t:
 root=Path(t); source=root/'receipt.json'; b,raw=fixture(); source.write_bytes(raw)
 b=replace(b,metadata_path=str(source)); BINDINGS['authored']=b
 out=root/'out';out.mkdir()
 report,content=m.bind_receipt(b,raw,validated_at=NOW,now=NOW)
 if mode=='fifo-prior':os.mkfifo(out/'manifest.json')
 if mode in ('fifo-candidate','prior-replacement'):
  (out/'manifest.json').write_text(json.dumps(report['manifest']))
 if mode=='fifo-candidate':os.mkfifo(out/'candidate.jsonl')
 original=os.open
 target=source if mode=='metadata-replacement' else out/'manifest.json'
 changed=False
 def swap(path,flags,*args,**kwargs):
  global changed
  if mode in ('metadata-replacement','prior-replacement') and Path(path)==target and not changed:
   changed=True;target.unlink();os.mkfifo(target)
  return original(path,flags,*args,**kwargs)
 with patch.object(m.os,'open',swap):
  result=m.main(['--binding','authored','--validated-at',NOW,'--now',NOW,'--output',str(out)])
 raise SystemExit(result)
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for mode in ('fifo-prior', 'metadata-replacement', 'prior-replacement', 'fifo-candidate'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-B', '-c', child, mode],
                    cwd=Path(__file__).resolve().parents[1], env=env,
                    capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(json.loads(result.stdout)['errors'], ['metadata-io-or-output-invalid'])
                self.assertNotIn('Traceback', result.stderr)

    def test_same_descriptor_rejects_path_replacement_after_open(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'receipt.json'
            path.write_bytes(b'fixture')
            original, changed = os.read, False
            def replace_path(fd, size):
                nonlocal changed
                result = original(fd, size)
                if not changed:
                    changed = True
                    path.unlink()
                    path.write_bytes(b'other')
                return result
            with patch.object(m.os, 'read', replace_path):
                with self.assertRaisesRegex(m.RefreshError, 'metadata-changed-during-read'):
                    m._read_regular(path, 64)

    def test_regular_missing_and_oversize_controls(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'receipt.json'
            b, raw = fixture()
            b = replace(b, metadata_path=str(p))
            self.assertIsNone(m.read_metadata(b))
            p.write_bytes(raw)
            self.assertEqual(m.read_metadata(b), raw)
            with self.assertRaisesRegex(m.RefreshError, 'metadata-file-bound-or-type-invalid'):
                m._read_regular(p, len(raw) - 1)

    def test_selected_depth_fails_fixed_and_valid_peer_is_still_processed(self):
        for depth in (m.MAX_SELECTED_DEPTH + 1, 3000):
            with self.subTest(depth=depth):
                raw = b'{"unit":' + b'[' * depth + b'0' + b']' * depth + b'}'
                valid = b'{"unit":null}'
                def binding(key, payload):
                    return m.ReceiptBinding(key, 'NA', 'prices/baskets', 'not-opened.json',
                        hashlib.sha256(payload).hexdigest(), len(payload),
                        (('nativeUnit', '/unit'),), (), ('not-opened.pdf', '0' * 64), fixture=True)
                bindings = {'a-deep': binding('a-deep', raw), 'z-valid': binding('z-valid', valid)}
                result, content = m.bind_receipt(bindings['a-deep'], raw, validated_at=NOW, now=NOW)
                self.assertEqual(result['status'], 'malformed')
                self.assertEqual(result['errors'], ['metadata-or-binding-malformed'])
                self.assertEqual(content, b'')
                visited = []
                def load(b):
                    visited.append(b.key)
                    return raw if b.key == 'a-deep' else valid
                report = m.bind_many(bindings, load, validated_at=NOW, now=NOW)
                self.assertEqual(visited, ['a-deep', 'z-valid'])
                self.assertEqual([r['status'] for r in report['results']], ['malformed', 'ready'])

    def test_unused_nested_metadata_is_not_a_selected_depth_failure(self):
        depth = m.MAX_SELECTED_DEPTH + 1
        raw = b'{"unit":null,"unused":' + b'[' * depth + b'0' + b']' * depth + b'}'
        b, _ = fixture()
        b = replace(b, metadata_sha256=hashlib.sha256(raw).hexdigest(), metadata_bytes=len(raw),
                    fields=(('nativeUnit', '/unit'),))
        report, content = m.bind_receipt(b, raw, validated_at=NOW, now=NOW)
        self.assertEqual(report['status'], 'ready')
        self.assertTrue(content)


if __name__ == '__main__':
    unittest.main()
