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

    def file_fixture(self):
        selection = self.fixture()
        path = self.root / selection['NATIONAL_ACQUISITION'][0]
        records = json.loads(path.read_text())
        for n, item in enumerate(records):
            item.pop('key');item.pop('acquiredAt')
            item['file'] = '/DO-NOT-OPEN/CANARY-SECRET/../receipt-label-' + str(n)
            item['unknownMetadata'] = {'CANARY-SECRET':'uninterpreted'}
            item['otherUnknown'] = ['CANARY-SECRET']
        return selection, records

    def repin(self, selection, key, value):
        path = self.put(key, json.dumps(value).encode())
        selection[key] = (*selection[key][:2],hashlib.sha256(path.read_bytes()).hexdigest())

    def inspect_file_fixture(self, selection, records):
        self.repin(selection, 'NATIONAL_ACQUISITION', records)
        with patch.object(m,'SELECTION',selection), patch.object(m.os,'fstatvfs',return_value=type('V',(),{'f_flag':os.ST_RDONLY})()):
            return m.inspect(str(self.root))

    def test_file_receipt_binds_only_by_pinned_content_without_paths_or_timestamps(self):
        selection, records = self.file_fixture()
        for item in records:item.update(acquiredAt='2099-01-01T00:00:00Z',completedAt='2099-01-01T00:00:00Z')
        records.append({'file':'unrelated-large-file','bytes':m.MAX_RAW+1,'sha256':'a'*64,'url':'CANARY-SECRET'})
        with patch.object(m,'parent_fd',wraps=m.parent_fd) as opened:
            r = self.inspect_file_fixture(selection, records)
        self.assertTrue(r['completeReady'])
        self.assertTrue(all(call.args[1] in {v[0] for v in selection.values()} for call in opened.call_args_list))
        for country in ('NO','FR'):
            self.assertIsNone(r['sources'][country]['acquiredAt'])
            self.assertEqual('unknown',r['sources'][country]['freshness'])
            self.assertEqual('offline-only',r['sources'][country]['acquisitionPolicy'])
            for key in m.SOURCES[country][2]:
                self.assertEqual('match',r['assets'][key]['acquisitionMatch'])
                self.assertEqual('pinned-receipt-content',r['assets'][key]['acquisitionMatchBasis'])
                self.assertEqual('matched',r['assets'][key]['acquisitionReason'])
        self.assertEqual('metadata-only-held',r['sources']['FI']['status'])
        self.assertFalse(r['sources']['FI']['provenanceVerified'])
        self.assertEqual((0,0,0),(r['sourceBodiesParsed'],r['downloads'],r['originalBytesWritten']))
        self.assertNotIn('CANARY',json.dumps(r))
        self.assertLess(len(m.canonical(r)),m.MAX_REPORT)

    def test_file_receipt_unmatched_duplicate_and_reused_labels_fail_closed(self):
        for case, reason in [('unmatched','no-content-match'),('duplicate','duplicate-content-match'),('duplicate-label','duplicate-content-match'),('label-conflict','reused-file-label')]:
            with self.subTest(case=case):
                selection, records = self.file_fixture()
                if case == 'unmatched':records[0]['sha256'] = 'a'*64
                elif case.startswith('duplicate'):
                    records.append(dict(records[0]))
                    if case == 'duplicate':records[-1]['file'] += '-second'
                else:records.append({'file':records[0]['file'],'bytes':42,'sha256':'a'*64,'url':'CANARY-SECRET'})
                r = self.inspect_file_fixture(selection, records)
                self.assertFalse(r['completeReady'])
                self.assertEqual(reason,r['assets']['NO_EN_FOODS']['acquisitionReason'])
                self.assertEqual('unknown',r['assets']['NO_EN_FOODS']['acquisitionMatch'])
                self.assertNotIn('CANARY',json.dumps(r))

    def test_file_receipt_digest_size_conflict_rejects_entire_receipt(self):
        selection, records = self.file_fixture()
        records.append({**records[0],'file':'conflict','bytes':records[0]['bytes']+1})
        r = self.inspect_file_fixture(selection, records)
        self.assertEqual('unsupported-schema',r['assets']['NATIONAL_ACQUISITION']['status'])
        self.assertEqual('conflicting-digest-size',r['assets']['NATIONAL_ACQUISITION']['schemaReason'])
        self.assertFalse(r['completeReady'])

    def test_file_receipt_malformed_declarations_and_mixed_schema_rejected(self):
        edits = [lambda x:x.update(bytes=True),lambda x:x.update(bytes=-1),lambda x:x.update(bytes=2**63),
                 lambda x:x.update(sha256='not-a-hash'),lambda x:x.update(file=None),lambda x:x.update(url=None),
                 lambda x:x.update(key='norway/en-foods.json')]
        for edit in edits:
            selection, records = self.file_fixture();edit(records[0])
            r = self.inspect_file_fixture(selection, records)
            self.assertEqual('unsupported-schema',r['assets']['NATIONAL_ACQUISITION']['status'])
            self.assertEqual('malformed-national-declaration',r['assets']['NATIONAL_ACQUISITION']['schemaReason'])
            self.assertFalse(r['completeReady'])
        with self.assertRaises(ValueError):m.metadata_facts('FI_ACQUISITION', records[1:])

    def test_file_receipt_cross_asset_pair_ambiguity_is_not_identity(self):
        selection, records = self.file_fixture()
        first, other = 'NO_EN_FOODS', 'FR_WORKBOOK'
        raw = (self.root/selection[first][0]).read_bytes();self.put(other,raw)
        selection[other] = (*selection[other][:2],records[0]['sha256'])
        prior = json.loads((self.root/selection['FR_PRIOR_MANIFEST'][0]).read_text())
        prior['sourceFiles'][0].update(bytes=records[0]['bytes'],sha256=records[0]['sha256'])
        self.repin(selection,'FR_PRIOR_MANIFEST',prior)
        r = self.inspect_file_fixture(selection, records)
        for key in (first,other):
            self.assertEqual('ambiguous-prior-content',r['assets'][key]['acquisitionReason'])
            self.assertEqual('unknown',r['assets'][key]['acquisitionMatch'])
        self.assertFalse(r['completeReady'])

    def test_file_receipt_requires_all_independent_trust_gates(self):
        for case, reason in [('prior-pin','prior-manifest-untrusted'),('rights','rights-profile-unverified'),('declaration','prior-declaration-missing'),('raw','raw-receipt-mismatch')]:
            with self.subTest(case=case):
                selection, records = self.file_fixture()
                prior = json.loads((self.root/selection['NO_PRIOR_MANIFEST'][0]).read_text())
                if case == 'prior-pin':selection['NO_PRIOR_MANIFEST'] = (*selection['NO_PRIOR_MANIFEST'][:2],'a'*64)
                elif case == 'rights':prior['license'] = 'CANARY-SECRET';self.repin(selection,'NO_PRIOR_MANIFEST',prior)
                elif case == 'declaration':prior['sourceFiles'].pop(1);self.repin(selection,'NO_PRIOR_MANIFEST',prior)
                else:self.put('NO_NB_FOODS',b'changed raw')
                r = self.inspect_file_fixture(selection, records)
                self.assertEqual(reason,r['assets']['NO_NB_FOODS']['acquisitionReason'])
                self.assertFalse(r['completeReady'])
        selection, records = self.file_fixture()
        self.repin(selection,'NATIONAL_ACQUISITION',records)
        selection['NATIONAL_ACQUISITION'] = (*selection['NATIONAL_ACQUISITION'][:2],'a'*64)
        with patch.object(m,'SELECTION',selection):r = m.inspect(str(self.root))
        self.assertEqual('acquisition-receipt-untrusted',r['assets']['NO_EN_FOODS']['acquisitionReason'])
        self.assertFalse(r['completeReady'])

    def test_new_diagnostics_are_allowlisted_and_consistent(self):
        selection, records = self.file_fixture();base = self.inspect_file_fixture(selection, records)
        edits = [lambda r:r['assets']['NO_EN_FOODS'].update(acquisitionReason='CANARY-SECRET'),
                 lambda r:r['assets']['NO_EN_FOODS'].update(acquisitionMatchBasis='CANARY-SECRET'),
                 lambda r:r['assets']['NATIONAL_ACQUISITION'].update(schemaReason='CANARY-SECRET'),
                 lambda r:r['assets']['NO_EN_FOODS'].update(acquisitionMatch='unknown'),
                 lambda r:r['sources']['NO'].update(freshness='timestamp-known')]
        for edit in edits:
            r=copy.deepcopy(base);edit(r)
            with self.assertRaises(ValueError):m.sanitize_report(r)


if __name__=='__main__':unittest.main()
