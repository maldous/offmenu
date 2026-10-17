import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/inspect-selected-datasets.py'
spec = importlib.util.spec_from_file_location('selected_datasets', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SelectedMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, asset_id, body):
        p = self.root / m.SELECTION[asset_id][0]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        return p

    def fixture(self):
        selection = dict(m.SELECTION)
        for key, (_, kind, _) in selection.items():
            if kind == 'raw':
                self.put(key, b'not a parseable source: CANARY-SECRET\n' + key.encode())
        acquisition = []
        for country, (source, release, assets, manifest, _) in m.SOURCES.items():
            declared = []
            for key in assets:
                data = (self.root / selection[key][0]).read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                declared.append({'key':selection[key][0].split('/')[-1], 'bytes':len(data), 'sha256':digest})
                acquisition.append({'key':selection[key][0], 'bytes':len(data), 'sha256':digest, 'url':'https://CANARY-SECRET.invalid', 'acquiredAt':'2026-10-12T00:00:00Z'})
                selection[key] = (*selection[key][:2],digest if selection[key][2] else None)
            self.put(manifest, json.dumps({'schemaVersion':'offmenu-collection/1','sourceId':source,'releaseId':release,'status':'normalized','sourceFiles':declared,'license':m.LICENSES[country],'completedAt':'2099-01-01T00:00:00Z','attribution':'CANARY-SECRET'}).encode())
        self.put('NATIONAL_ACQUISITION', json.dumps(acquisition).encode())
        self.put('FI_ACQUISITION', b'[{"key":"fineli-basic2.zip","bytes":42,"sha256":"'+b'a'*64+b'","method":"CANARY-SECRET"}]')
        for key, (relative, kind, pin) in selection.items():
            if kind == 'metadata':
                selection[key] = (relative,kind,hashlib.sha256((self.root/relative).read_bytes()).hexdigest())
        return selection

    def test_empty_mount_is_incomplete(self):
        r = m.inspect(str(self.root))
        self.assertEqual('incomplete', r['status'])
        self.assertFalse(r['completeReady'])
        self.assertTrue(all(a['status']=='missing' for a in r['assets'].values()))
        self.assertEqual(0,r['selectedBytesHashed'])

    def test_valid_fixture_readonly_ready_no_source_parsing(self):
        selection = self.fixture()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(m,'SELECTION',selection), patch.object(m.os,'fstatvfs',return_value=type('V',(),{'f_flag':os.ST_RDONLY})()):
            r = m.inspect(str(self.root))
        self.assertTrue(r['completeReady'])
        self.assertEqual('metadata-only-held',r['sources']['FI']['status'])
        self.assertEqual('not-performed',r['sources']['NO']['acceptance'])
        self.assertEqual('2026-10-12T00:00:00Z',r['sources']['NO']['acquiredAt'])
        self.assertEqual(0,r['sourceBodiesParsed'])
        self.assertNotIn('CANARY',json.dumps(r))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_rw_mount_never_ready(self):
        with patch.object(m,'SELECTION',self.fixture()):
            self.assertFalse(m.inspect(str(self.root))['completeReady'])

    def test_raw_oversize_not_opened(self):
        p = self.put('NO_EN_FOODS',b'')
        with p.open('r+b') as out:
            out.truncate(m.MAX_RAW+1)
        with patch.object(m,'read_selected',side_effect=AssertionError('opened')):
            r = m.inspect(str(self.root))
        self.assertEqual('oversized',r['assets']['NO_EN_FOODS']['status'])
        self.assertEqual(0,r['selectedBytesHashed'])

    def test_aggregate_limit_no_raw_open(self):
        for key, (_,kind,_) in m.SELECTION.items():
            if kind == 'raw':
                p = self.put(key,b'')
                with p.open('r+b') as out:
                    out.truncate(m.MAX_RAW)
        with patch.object(m,'read_selected',side_effect=AssertionError('opened')):
            r = m.inspect(str(self.root))
        self.assertTrue(all(r['assets'][k]['status']=='aggregate-limit' for k,v in m.SELECTION.items() if v[1]=='raw'))

    def test_symlink_file_and_parent_rejected(self):
        secret = self.root/'CANARY-SECRET'
        secret.write_text('CANARY-SECRET')
        (self.root/'norway').mkdir()
        (self.root/m.SELECTION['NO_EN_FOODS'][0]).symlink_to(secret)
        (self.root/'ciqual').symlink_to(self.root,target_is_directory=True)
        r = m.inspect(str(self.root))
        self.assertEqual('unsafe-path',r['assets']['NO_EN_FOODS']['status'])
        self.assertEqual('unsafe-path',r['assets']['FR_WORKBOOK']['status'])
        self.assertNotIn('CANARY',json.dumps(r))
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        self.assertTrue(all(a['status']=='unsafe-path' for a in m.inspect(str(alias))['assets'].values()))

    def test_fifo_and_hardlink_rejected(self):
        (self.root/'norway').mkdir()
        os.mkfifo(self.root/m.SELECTION['NO_EN_FOODS'][0])
        p=self.put('NO_NB_FOODS',b'CANARY-SECRET');os.link(p,self.root/'another')
        r=m.inspect(str(self.root))
        self.assertEqual('not-regular',r['assets']['NO_EN_FOODS']['status'])
        self.assertEqual('multiple-links',r['assets']['NO_NB_FOODS']['status'])

    def test_strict_metadata_json(self):
        for body in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":[{"y":1e9999}]}',b'not-json CANARY-SECRET'):
            self.put('NATIONAL_ACQUISITION',body)
            r=m.inspect(str(self.root))
            self.assertEqual('invalid-json',r['assets']['NATIONAL_ACQUISITION']['status'])
            self.assertNotIn('CANARY',json.dumps(r))

    def test_unknown_schema_and_license_not_promoted(self):
        selection=self.fixture()
        p=self.root/selection['NO_PRIOR_MANIFEST'][0]
        data=json.loads(p.read_text());data['schemaVersion']='unknown';p.write_text(json.dumps(data))
        selection['NO_PRIOR_MANIFEST']=(*selection['NO_PRIOR_MANIFEST'][:2],hashlib.sha256(p.read_bytes()).hexdigest())
        with patch.object(m,'SELECTION',selection):r=m.inspect(str(self.root))
        self.assertEqual('unsupported-schema',r['assets']['NO_PRIOR_MANIFEST']['status'])
        self.assertEqual('unknown',r['sources']['NO']['historicalRightsProfile'])
        data['schemaVersion']='offmenu-collection/1';data['license']='CANARY-SECRET';p.write_text(json.dumps(data))
        selection['NO_PRIOR_MANIFEST']=(*selection['NO_PRIOR_MANIFEST'][:2],hashlib.sha256(p.read_bytes()).hexdigest())
        with patch.object(m,'SELECTION',selection):r=m.inspect(str(self.root))
        self.assertEqual('unknown',r['sources']['NO']['historicalRightsProfile'])
        self.assertFalse(r['completeReady'])

    def test_receipt_mutation_not_trusted(self):
        selection=self.fixture()
        self.put('NO_PRIOR_MANIFEST',b'[]')
        with patch.object(m,'SELECTION',selection):r=m.inspect(str(self.root))
        self.assertEqual('mismatch',r['assets']['NO_PRIOR_MANIFEST']['historicalMatch'])
        self.assertEqual('unknown',r['assets']['NO_NB_FOODS']['receiptMatch'])

    def test_changed_during_read_rejected(self):
        p=self.put('NO_EN_FOODS',b'abc')
        original=m.os.read
        def read(fd,n):
            chunk=original(fd,n)
            # Grow the file: mtime/ctime may share a coarse filesystem tick.
            p.write_bytes(b'defg')
            return chunk
        # Deliberately suppress clock fields to prove this is portable to
        # filesystems whose timestamps do not change within one write tick.
        def coarse_signature(info):
            return (info.st_dev,info.st_ino,info.st_size,info.st_mode,info.st_nlink)
        with patch.object(m.os,'read',side_effect=read), patch.object(m,'signature',side_effect=coarse_signature):
            r=m.inspect(str(self.root))
        self.assertEqual('changed',r['assets']['NO_EN_FOODS']['status'])
        self.assertNotIn('sha256',r['assets']['NO_EN_FOODS'])

    def test_sanitizer_drops_unknown_fields(self):
        r=m.inspect(str(self.root));r['secret']='CANARY-SECRET'
        r['assets']['NO_EN_FOODS']['path']='CANARY-SECRET'
        r['sources']['NO']['license']='CANARY-SECRET'
        clean=m.sanitize_report(r)
        self.assertNotIn('CANARY',json.dumps(clean))
        self.assertLess(len(m.canonical(clean)),m.MAX_REPORT)

    def test_sanitizer_rejects_malformed_values(self):
        base=m.inspect(str(self.root))
        edits=[lambda r:r.update(schemaVersion='unknown'),lambda r:r.update(status='CANARY-SECRET'),lambda r:r.update(selectedBytesHashed=2**100),lambda r:r.update(inspectorSha256='a'*65000),lambda r:r['assets']['NO_EN_FOODS'].update(status='CANARY-SECRET'),lambda r:r['assets']['NO_EN_FOODS'].update(bytes=True),lambda r:r['assets']['NO_EN_FOODS'].update(sha256='CANARY-SECRET'),lambda r:r['sources']['NO'].update(acquiredAt='CANARY-SECRET'),lambda r:r['sources']['NO'].update(historicalRightsProfile='CANARY-SECRET'),lambda r:r['assets'].update(NO_EN_FOODS=None),lambda r:r['sources'].update(NO=None)]
        for edit in edits:
            r=copy.deepcopy(base);edit(r)
            with self.assertRaises((ValueError,TypeError,AttributeError)):
                m.sanitize_report(r)

    def test_no_mtime_or_completed_at_freshness(self):
        selection=self.fixture()
        self.put('NATIONAL_ACQUISITION',b'[]')
        selection['NATIONAL_ACQUISITION']=(*selection['NATIONAL_ACQUISITION'][:2],hashlib.sha256(b'[]').hexdigest())
        with patch.object(m,'SELECTION',selection):r=m.inspect(str(self.root))
        self.assertIsNone(r['sources']['NO']['acquiredAt'])
        self.assertEqual('unknown',r['sources']['NO']['freshness'])
        self.assertFalse(r['sources']['NO']['provenanceVerified'])
        self.assertEqual('unknown',r['assets']['NO_EN_FOODS']['acquisitionMatch'])

    def test_cli_empty_emits_one_bounded_report(self):
        p=subprocess.run([sys.executable,'-B',str(SCRIPT),'--cache-root',str(self.root)],capture_output=True)
        self.assertEqual(2,p.returncode)
        self.assertEqual(b'',p.stderr)
        r=json.loads(p.stdout);self.assertEqual(m.SCHEMA,r['schemaVersion'])
        self.assertLess(len(p.stdout),m.MAX_REPORT)
        self.assertNotIn(str(self.root),p.stdout.decode())


if __name__=='__main__':unittest.main()
