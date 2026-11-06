import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('places_batch', ROOT/'scripts/align-places-common.py')
places = importlib.util.module_from_spec(spec); spec.loader.exec_module(places)
import places_input_catalog as catalog

class Batches(unittest.TestCase):
    def row(self, source, n):
        return {'schemaVersion':'1.0','kind':'site' if source==catalog.SOURCES[0] else 'organization',
                'id':f'{source}:{n}', 'countries':['AU'],
                'provenance':{'sourceId':source,'recordId':str(n),'url':'https://example.org/record',
                              'license':'CC0 1.0','licenseUrl':'https://example.org/license','attribution':'Fixture',
                              'visibility':'public','releaseId':'fixture','sourceDate':'2026-10-14'},
                'data':{'name':f'Fixture {n}', 'nested':{'country':'AU','note':'human words'}}}
    def fixture(self, root):
        curated=root/'curated';files=[]
        for source in catalog.SOURCES:
            for i in range(2):
                p=curated/'records'/source/f'{i:02}.jsonl.gz';p.parent.mkdir(parents=True,exist_ok=True)
                raw=gzip.compress(('\n'.join(json.dumps([f'id{n}',[self.row(source,n)]]) for n in range(i*2,(i+1)*2))+'\n').encode(),mtime=0)
                p.write_bytes(raw);files.append({'key':p.relative_to(curated).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        p=curated/'notices/overture-food-places/fixture/NOTICE.txt';p.parent.mkdir(parents=True);p.write_bytes(b'Fixture public attribution\n')
        notices=[{'key':p.relative_to(curated).as_posix(),'bytes':p.stat().st_size,'sha256':places.digest(p)}]
        manifest={'format':'offmenu-curated/1','releaseId':'fixture','files':files,'notices':notices,
                  'sources':{s:{'releaseId':'fixture','records':4,'license':'CC0','attribution':'Fixture','rawSourcePayloadPublished':False} for s in catalog.SOURCES}}
        (curated/'manifest.json').write_text(json.dumps(manifest))
        return curated
    def run_align(self, src, out, **kw):
        options={'minimum_free_bytes':0, 'batch_records':10000, 'batch_seconds':300,
                 'records_per_packet':3,'expected_manifest_sha256':places.digest(src/'manifest.json')}
        options.update(kw)
        with contextlib.redirect_stdout(io.StringIO()):
            return places.align(src,out,**options)
    def allbytes(self, root):
        return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    def test_pause_mid_packet_does_not_finalize_then_exact_resume(self):
        for boundary in (1,2,3,4,7,8):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as t:
                root=Path(t);src=self.fixture(root);out=root/'out'
                result=self.run_align(src,out,batch_records=boundary)
                self.assertEqual(result['status'],'paused');self.assertFalse(out.exists())
                self.assertFalse((root/'out.partial/manifest.json').exists())
                with sqlite3.connect(root/'out.checkpoint.sqlite') as db:
                    state=json.loads(db.execute('SELECT payload FROM state').fetchone()[0])
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM identities').fetchone()[0],boundary)
                    created=state['createdAt'];self.assertNotIn('files',state['sink'])
                with patch.object(places.dt,'datetime') as clock:
                    clock.now.return_value.isoformat.return_value=created
                    expected=self.run_align(src,root/'expected')
                actual=self.run_align(src,out,resume=True)
                self.assertEqual(actual,expected)
                self.assertEqual(self.allbytes(out),self.allbytes(root/'expected'))
    def test_many_batches_preserve_source_boundaries(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out'
            result=self.run_align(src,out,batch_records=1)
            for _ in range(10):
                if result.get('complete'):break
                result=self.run_align(src,out,resume=True,batch_records=1)
            self.assertTrue(result['complete']);self.assertEqual(result['counts']['resources'],8)
            self.assertEqual(result['inputCoverage'],{'complete':True,'expectedFiles':4,'observedFiles':4})
    def test_time_pause_before_records_no_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out'
            result=self.run_align(src,out,batch_seconds=1e-9)
            self.assertEqual(result['reason'],'time-budget');self.assertFalse(out.exists())
            self.assertTrue(self.run_align(src,out,resume=True)['complete'])
    def test_storage_pause_no_finalization(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out'
            with patch.object(places.shutil,'disk_usage',return_value=type('U',(),{'free':0})()):
                result=self.run_align(src,out)
            self.assertEqual(result['reason'],'storage-reserve');self.assertFalse(out.exists())
            self.assertTrue(self.run_align(src,out,resume=True)['complete'])
    def test_source_mutation_after_pause_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out';self.run_align(src,out,batch_records=1)
            f=next(src.rglob('*.gz'));before=f.read_bytes();f.write_bytes(before)
            with self.assertRaisesRegex(ValueError,'catalog changed'):self.run_align(src,out,resume=True)
    def test_extra_missing_symlink_target_refused(self):
        for kind in ('extra','missing','symlink'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as t:
                root=Path(t);src=self.fixture(root);f=next(src.rglob('*.gz'))
                if kind=='extra':f.with_name('extra.jsonl.gz').write_bytes(f.read_bytes())
                if kind=='missing':f.unlink()
                if kind=='symlink':
                    dst=root/'outside';dst.write_bytes(f.read_bytes());f.unlink();f.symlink_to(dst)
                with self.assertRaises((ValueError,OSError)):self.run_align(src,root/'out')
                self.assertFalse((root/'out/manifest.json').exists())
    def test_bad_checksum_refused_before_source_admission(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);f=next(src.rglob('*.gz'));raw=f.read_bytes();f.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):self.run_align(src,root/'out')
    def test_duplicate_source_identity_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);f=src/'records/overture-food-places/01.jsonl.gz'
            f.write_bytes((src/'records/overture-food-places/00.jsonl.gz').read_bytes())
            m=json.loads((src/'manifest.json').read_text());entry=next(e for e in m['files'] if e['key']==f.relative_to(src).as_posix());entry.update(bytes=f.stat().st_size,sha256=places.digest(f));(src/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'duplicate normalized'):self.run_align(src,root/'out')
    def test_notice_checksum_checked_before_final(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);f=next(src.rglob('*.txt'));f.write_bytes(b'X'*f.stat().st_size)
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):self.run_align(src,root/'out')
            self.assertFalse((root/'out').exists())
    def test_wrong_expected_manifest_pin_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'manifest byte pin'):self.run_align(src,root/'out',expected_manifest_sha256='0'*64)
    def test_benchmark_limit_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'not a production'):self.run_align(src,root/'out',limit=1)
    def test_atomic_closed_orphan_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out';write=places.atomic_bytes
            def crash(path,raw):
                write(path,raw)
                if path.name=='part-00000.jsonl.gz':raise RuntimeError('after atomic close')
            with patch.object(places,'atomic_bytes',crash),self.assertRaises(RuntimeError):self.run_align(src,out)
            self.assertTrue(self.run_align(src,out,resume=True)['complete'])
    def test_semantic_transform_unchanged_from_recovered_source(self):
        spec=importlib.util.spec_from_file_location('old_places',ROOT/'tests/reference_transform.py')
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        for source in catalog.SOURCES:
            row=self.row(source,1)
            self.assertEqual(places.packet_record(row),old.packet_record(row))
    def test_real_validator_rejects_invalid_packet(self):
        schema=json.loads((ROOT/'corpus/common-data.schema.json').read_text())
        validator=places.jsonschema_rs.Draft202012Validator(schema,validate_formats=True)
        with self.assertRaises(Exception):validator.validate({'schemaVersion':'bad'})

    def test_fifo_rejected_without_block(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);os.mkfifo(root/'fifo')
            with self.assertRaisesRegex(ValueError,'not a regular'):
                catalog.open_regular(root,'fifo')
    def test_initial_committed_checkpoint_without_partial_can_resume(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out';save=places.Checkpoint.save
            def stop_initial(cp):
                save(cp)
                if cp.value['sink'] is None:
                    cp.close()
                    raise RuntimeError('initial checkpoint interruption')
            with patch.object(places.Checkpoint,'save',stop_initial),self.assertRaises(RuntimeError):
                self.run_align(src,out)
            self.assertFalse((root/'out.partial').exists())
            self.assertTrue(self.run_align(src,out,resume=True)['complete'])
    def test_temporary_write_failure_cleans_only_own_temp(self):
        import places_checkpoint
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'asset'
            with patch.object(places_checkpoint.os,'fsync',side_effect=OSError('fault')):
                with self.assertRaises(OSError):places_checkpoint.atomic_bytes(path,b'fixture')
            self.assertFalse(path.exists());self.assertFalse(path.with_name('asset.pending').exists())
            places_checkpoint.atomic_bytes(path,b'fixture')
            self.assertEqual(path.read_bytes(),b'fixture')
    def test_existing_unknown_pending_preserved_and_refused(self):
        import places_checkpoint
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'asset';pending=path.with_name('asset.pending');pending.write_bytes(b'prior interrupted bytes')
            with self.assertRaises(FileExistsError):places_checkpoint.atomic_bytes(path,b'new')
            self.assertEqual(pending.read_bytes(),b'prior interrupted bytes');self.assertFalse(path.exists())
    def test_line_limit_is_failure_not_silent_skip_or_complete(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out'
            with patch.object(catalog,'MAX_LINE',16),self.assertRaisesRegex(ValueError,'bounded size'):
                self.run_align(src,out)
            self.assertFalse(out.exists());self.assertFalse((root/'out.partial/manifest.json').exists())
    def test_runtime_change_refuses_checkpoint(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out';self.run_align(src,out,batch_records=1)
            with patch.object(places.importlib.metadata,'version',return_value='changed'),self.assertRaisesRegex(ValueError,'pins mismatch'):
                self.run_align(src,out,resume=True)
    def test_source_count_mismatch_never_finalizes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);out=root/'out';path=src/'manifest.json';m=json.loads(path.read_text());m['sources'][catalog.SOURCES[0]]['records']=5;path.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'source count mismatch'):self.run_align(src,out)
            self.assertFalse(out.exists());self.assertFalse((root/'out.partial/manifest.json').exists())
    def test_release_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root);path=src/'manifest.json';m=json.loads(path.read_text());m['sources'][catalog.SOURCES[0]]['releaseId']='../../outside';path.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'unsafe source release'):self.run_align(src,root/'out')

    def test_final_close_committed_before_manifest_can_resume_exactly(self):
        for after_write in (False,True):
            with self.subTest(after_write=after_write), tempfile.TemporaryDirectory() as t:
                root=Path(t);src=self.fixture(root);out=root/'out';write=places.atomic_bytes
                def interrupt_manifest(path,raw):
                    if path.name=='manifest.json':
                        if after_write:write(path,raw)
                        raise RuntimeError('manifest boundary interruption')
                    write(path,raw)
                with patch.object(places,'atomic_bytes',interrupt_manifest),self.assertRaises(RuntimeError):
                    self.run_align(src,out)
                with sqlite3.connect(root/'out.checkpoint.sqlite') as db:
                    created=json.loads(db.execute('SELECT payload FROM state').fetchone()[0])['createdAt']
                with patch.object(places.dt,'datetime') as clock:
                    clock.now.return_value.isoformat.return_value=created
                    self.run_align(src,root/'expected')
                self.assertTrue(self.run_align(src,out,resume=True)['complete'])
                self.assertEqual(self.allbytes(out),self.allbytes(root/'expected'))

if __name__=='__main__':unittest.main()

class AcceptedFormatTests(Batches):
    def test_actual_format_key_is_required_not_legacy_schema_version(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root)
            m=json.loads((src/'manifest.json').read_text());m['schemaVersion']=m.pop('format');(src/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'unexpected curated manifest schema'):
                catalog.inventory(src,places.digest(src/'manifest.json'))
    def test_wrong_format_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root)
            m=json.loads((src/'manifest.json').read_text());m['format']='offmenu-curated/2';(src/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'unexpected curated manifest schema'):
                catalog.inventory(src,places.digest(src/'manifest.json'))
    def test_real_release_and_integer_count_shapes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=self.fixture(root)
            m=json.loads((src/'manifest.json').read_text());m['releaseId']='expanded-country-search-20261013'
            for source,release,count in [('overture-food-places','2026-09-23.1',12681108),('wikidata-food-businesses','2026-10-13-direct-types',1505)]:
                m['sources'][source].update(releaseId=release,records=count,rawSourcePayloadPublished=False)
            notice=m['notices'][0];old=src/notice['key'];newkey=notice['key'].replace('/fixture/','/2026-09-23.1/');new=src/newkey;new.parent.mkdir(parents=True);old.rename(new);notice['key']=newkey
            (src/'manifest.json').write_text(json.dumps(m));manifest,cat=catalog.inventory(src,places.digest(src/'manifest.json'))
            self.assertEqual(manifest['sources']['overture-food-places']['records'],12681108)
            self.assertEqual(len(cat['assets']),5)
