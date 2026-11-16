import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

P = Path(__file__).with_name('probe_corpus_metadata.py')
spec = importlib.util.spec_from_file_location('probe', P)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def openfile(self, name, content):
        p = self.root / name
        p.write_bytes(content)
        return os.open(p, os.O_RDONLY)

    def test_metadata_whitelist_no_records_strings(self):
        raw=json.dumps({'counts': {'packets': 3, 'secret': 44, 'resources':True},
                        'files':[{'key':'PRIVATE'}], 'records':['SECRET'],
                        'status':'SECRET', 'complete':False}).encode()
        fd=self.openfile('manifest.json',raw)
        try: got=probe.metadata(fd,probe.Budget())
        finally:os.close(fd)
        self.assertEqual(got['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(got['declared_counts'],{'packets':3})
        self.assertEqual(got['declared_files_entries'],1)
        self.assertNotIn('SECRET',json.dumps(got));self.assertNotIn('PRIVATE',json.dumps(got))

    def test_huge_metadata_not_read(self):
        fd=self.openfile('manifest.json',b'x'*10)
        try:
            with patch.object(probe,'MAX_FILE_BYTES',2):
                got=probe.metadata(fd,probe.Budget())
            self.assertEqual(got['status'],'metadata_byte_budget_no_read')
            self.assertEqual(os.lseek(fd,0,os.SEEK_CUR),0)
        finally:os.close(fd)

    def test_no_symlink_component(self):
        (self.root/'link').symlink_to('/tmp',target_is_directory=True)
        fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(OSError):probe.open_beneath(fd,'link',True)
        finally:os.close(fd)

    def test_scope_no_extra_inputs(self):
        self.assertEqual(len(probe.PACKAGES),8);self.assertEqual(len(probe.RECEIPTS),2)
        self.assertNotIn('common-bulk-food-20261014',probe.PACKAGES)
        self.assertNotIn('curated-expanded-country-search-20261013/blobs',probe.PACKAGES)

    def test_complete_fixture_not_qualification(self):
        for i,name in enumerate(probe.PACKAGES):
            p=self.root/name;p.mkdir(parents=True)
            if i<6:(p/'manifest.json').write_text('{"counts":{"packets":12},"complete":true}')
            (p/'packet.bin').write_bytes(b'DO NOT READ RAW')
        for name in probe.RECEIPTS:(self.root/name).write_text('{"packageCount":6}')
        with patch.object(probe,'ROOT',str(self.root)), patch.object(probe.os,'fstatvfs',return_value=types.SimpleNamespace(f_flag=os.ST_RDONLY)):
            got=probe.run()
        self.assertTrue(got['scope_attempted_complete'])
        self.assertFalse(got['qualification_established'])
        self.assertFalse(got['full_data_verification'])
        self.assertEqual(got['packages'][6]['manifest.json']['status'],'absent')
        self.assertEqual(got['packages'][0]['metadata_scan']['regular_files'],2)
        self.assertNotIn('DO NOT READ RAW',json.dumps(got))
        self.assertLess(len(json.dumps(got)),12000)

    def test_not_readonly_no_manifest_inspection(self):
        for name in probe.PACKAGES:(self.root/name).mkdir(parents=True)
        with patch.object(probe,'ROOT',str(self.root)),patch.object(probe.os,'fstatvfs',return_value=types.SimpleNamespace(f_flag=0)):
            got=probe.run()
        self.assertEqual(got['budget_usage']['metadata_bytes_read'],0)
        self.assertEqual(got['packages'][0]['status'],'not_readonly_no_inspection')

    def test_entry_budget_incomplete(self):
        p=self.root/probe.PACKAGES[0];p.mkdir(parents=True)
        for i in range(4):(p/str(i)).write_bytes(b'raw')
        with patch.object(probe,'ROOT',str(self.root)),patch.object(probe,'MAX_ENTRIES',2),patch.object(probe.os,'fstatvfs',return_value=types.SimpleNamespace(f_flag=os.ST_RDONLY)):
            got=probe.run()
        self.assertEqual(got['stopped_reason'],'entry_budget')
        self.assertFalse(got['packages'][0]['metadata_scan']['complete'])

    def test_receipt_symlink_not_followed(self):
        for name in probe.PACKAGES:(self.root/name).mkdir(parents=True)
        secret=self.root/'outside';secret.write_text('secret')
        (self.root/probe.RECEIPTS[0]).symlink_to(secret)
        with patch.object(probe,'ROOT',str(self.root)),patch.object(probe.os,'fstatvfs',return_value=types.SimpleNamespace(f_flag=os.ST_RDONLY)):
            got=probe.run()
        self.assertEqual(got['receipts'][0]['status'],'missing_or_inaccessible')
        self.assertEqual(got['budget_usage']['metadata_bytes_read'],0)

if __name__=='__main__':unittest.main()
