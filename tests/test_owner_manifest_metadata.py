"""All service/privileged operations are mocked; never run the admin CLI here."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
import tempfile

PATH = Path(__file__).resolve().parents[1] / 'tools/data-processing/collect_owner_manifest_metadata.py'
spec = importlib.util.spec_from_file_location('metadata_view', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class MetadataTests(unittest.TestCase):
    def test_exact_scope(self):
        self.assertEqual(len(m.CANDIDATES), 16)
        self.assertEqual(len(set(m.CANDIDATES)), 16)
        self.assertNotIn('matvaretabellen-2026', m.CANDIDATES)
        self.assertNotIn('ciqual-2025', m.CANDIDATES)
        self.assertEqual(m.REUSED, ('metadata/no-prior-manifest.json', 'metadata/fr-prior-manifest.json'))

    def test_sanitizes_secrets_rows_paths(self):
        body = json.dumps({'rows': [{'password': 'canary'}], 'token': 'canary',
                           'url': 'https://fdc.usda.gov/canary?token=canary#canary',
                           'path': '/home/user/canary', 'source': {'secret': 'canary'},
                           'sha256': 'a'*64, 'bytes': 10, 'license': 'CC0-1.0'}).encode()
        out = m.sanitize(body, 'usda-2026-04')
        self.assertNotIn('canary', json.dumps(out))
        self.assertEqual(out['originalDownloadMetadata'], {'sha256':'a'*64, 'bytes':10})
        self.assertEqual(out['provenance']['url_origin'], 'https://usda.gov')
        self.assertFalse(out['provenanceVerified'])
        self.assertEqual(out['manifestBytes'], len(body))

    def test_origin_restricts_untrusted_domains(self):
        for url in ('http://usda.gov', 'https://user:pass@usda.gov', 'https://127.0.0.1',
                    'https://secret.evil.test', 'https://usda.gov.evil.test',
                    'https://usda.gov:8443', 'https://[::1]', 'not a url'):
            self.assertIsNone(m.public_origin(url), url)
        self.assertEqual(m.public_origin('https://secret.usda.gov/private'), 'https://usda.gov')

    def test_duplicate_invalid_and_deep_json(self):
        for body in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'\xff', b'['*2000):
            with self.assertRaises(m.Blocked): m.sanitize(body, 'usda-2026-04')

    def test_fixed_field_types(self):
        out = m.sanitize(b'{"bytes":true,"size_bytes":-1,"download_bytes":1e20,"sha256":"secret","license":"secret","downloaded_at":"secret"}', 'x')
        self.assertEqual(out['originalDownloadMetadata'], {})
        self.assertEqual(out['provenance'], {})

    def test_repository_collector_manifest_shapes(self):
        # Exact top-level field shapes emitted by collect-jsonl.mjs/collect-national.py.
        for raw in (
            {'schemaVersion':'offmenu-collection/1','sourceId':'off','releaseId':'r',
             'archiveSha256':'A'*64,'status':'normalized','completedAt':'2026-10-12T01:02:03.456Z',
             'partitions':[{'key':'private','sha256':'b'*64}], 'counts':{'raw':10}},
            {'schemaVersion':'offmenu-collection/1','sourceId':'cofid','releaseId':'r',
             'archiveSha256':'c'*64,'status':'normalized','completedAt':'2026-10-12T01:02:03.456789+00:00',
             'sourceFiles':[{'path':'private','sha256':'d'*64}], 'normalizedRows':10}):
            out=m.sanitize(json.dumps(raw).encode(),'x')
            self.assertEqual(out['collectionMetadata'],{'archiveSha256':raw['archiveSha256'].lower(),'completedAt':raw['completedAt']})
            self.assertEqual(out['originalDownloadMetadata'],{})
            self.assertFalse(out['provenanceVerified'])
            self.assertIn('not acquisition or freshness',out['collectionMetadataMeaning'])
            self.assertNotIn('private',json.dumps(out))
            self.assertNotIn('sourceFiles',out)

    def test_collection_metadata_rejects_invalid_values(self):
        for value in (None,True,123,{},[], 'secret', '2026-99-99T01:02:03Z', '2026-10-12'):
            out=m.sanitize(json.dumps({'archiveSha256':value,'completedAt':value}).encode(),'x')
            self.assertEqual(out['collectionMetadata'],{})
            self.assertEqual(out['originalDownloadMetadata'],{})

    def test_collect_only_exact_paths(self):
        paths = []
        def read(path, owner):
            paths.append(path); return b'{}'
        with patch.object(m, 'read_source', side_effect=read):
            outputs, statuses, total = m.collect(None)
        self.assertEqual(paths, [m.ROOT / c / 'manifest.json' for c in m.CANDIDATES])
        self.assertEqual(len(outputs), 16)
        self.assertEqual(total, 32)
        self.assertEqual(set(statuses.values()), {'sanitized'})

    def test_collect_skips_missing_unsafe_and_oversize(self):
        with patch.object(m, 'read_source', side_effect=[FileNotFoundError(), m.Blocked('oversized'), OSError()] + [b'{}']*13):
            outputs, statuses, total = m.collect(None)
        self.assertEqual(len(outputs), 13)
        self.assertEqual(list(statuses.values())[:3], ['missing','oversized','unsafe-or-unreadable'])

    def test_aggregate_bound(self):
        with patch.object(m, 'TOTAL', 3), patch.object(m, 'read_source', return_value=b'{}'):
            outputs, statuses, total = m.collect(None)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(list(statuses.values())[1:], ['aggregate-limit']*15)

    def test_owner_read_denied(self):
        # Real descriptor operations, with only ACL and parent identity checks simulated.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'manifest.json'; p.write_bytes(b'{}'); p.chmod(0o600)
            owner = SimpleNamespace(pw_uid=12345, pw_gid=12345)
            with self.assertRaises(m.Blocked): m.read_source(p, owner)

    def test_symlink_and_oversize_rejected(self):
        # /tmp is world-writable, so test anchored traversal with patched stat
        # observations only for that known test ancestor; leaves stay real.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / 'manifest.json'; p.write_bytes(b'{}')
            link = root / 'link.json'; link.symlink_to(p)
            real_fstat = os.fstat
            def fstat(fd):
                st = real_fstat(fd)
                if __import__('stat').S_ISDIR(st.st_mode):
                    vals = list(st); vals[0] &= ~0o002
                    return os.stat_result(vals)
                return st
            owner = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
            with patch.object(m.os, 'fstat', side_effect=fstat), patch.object(m, 'no_acl'):
                with self.assertRaises(m.Blocked): m.read_source(link, owner)
                p.write_bytes(b'x'*(m.CAP+1))
                with self.assertRaisesRegex(m.Blocked, 'oversized'): m.read_source(p, owner)

class ReceiptTests(unittest.TestCase):
    def owner_context(self):
        from contextlib import ExitStack
        stack=ExitStack(); self.addCleanup(stack.close)
        owner=SimpleNamespace(pw_uid=1000,pw_gid=1000)
        stack.enter_context(patch.object(m.pwd,'getpwnam',return_value=owner))
        stack.enter_context(patch.object(m.os,'getuid',return_value=1000))
        stack.enter_context(patch.object(m.os,'geteuid',return_value=1000))
        stack.enter_context(patch.object(m.sys,'flags',SimpleNamespace(isolated=1)))
        return stack

    def test_normal_owner_receipt_and_canonical_digest(self):
        stack=self.owner_context()
        stack.enter_context(patch.object(m,'read_source',return_value=b'{"bytes":123,"rows":["secret"]}'))
        report=m.run()
        self.assertEqual(report['status'],'collected')
        self.assertEqual(report['selectedCount'],16)
        self.assertNotIn('secret',json.dumps(report))
        digest=report.pop('receiptSha256')
        self.assertEqual(digest,m.hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        self.assertFalse(report['runnerAccessChanged']); self.assertFalse(report['published'])

    def test_root_or_other_user_refused_before_reads(self):
        stack=self.owner_context()
        for uid in (0,1001):
            with patch.object(m.os,'geteuid',return_value=uid),patch.object(m,'collect') as collect:
                self.assertEqual(m.run()['errorCode'],'normal-owner-identity-required')
                collect.assert_not_called()

    def test_no_safe_files_reports_every_candidate(self):
        stack=self.owner_context()
        stack.enter_context(patch.object(m,'read_source',side_effect=FileNotFoundError()))
        report=m.run()
        self.assertEqual(report['status'],'no-safe-manifest')
        self.assertEqual(len(report['candidates']),16)
        self.assertEqual(set(report['candidates'].values()),{'missing'})

    def test_receipt_is_bounded(self):
        stack=self.owner_context()
        stack.enter_context(patch.object(m,'collect',return_value=({}, {'x':'a'*70000},0)))
        report=m.run()
        self.assertEqual(report['errorCode'],'receipt-limit')
        self.assertLess(len(json.dumps(report)),1024)

    def test_original_hash_does_not_claim_provenance(self):
        stack=self.owner_context()
        body=b'{"downloaded_at":"not recorded","license":"unknown"}'
        stack.enter_context(patch.object(m,'read_source',return_value=body))
        report=m.run()
        row=next(iter(report['metadata'].values()))
        self.assertEqual(row['manifestSha256'],m.hashlib.sha256(body).hexdigest())
        self.assertFalse(row['provenanceVerified'])
        self.assertEqual(row['originalDownloadMetadata'],{})
        self.assertEqual(row['provenance'],{})

if __name__ == '__main__': unittest.main()
