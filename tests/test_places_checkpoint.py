import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_places_common
places = test_places_common.places

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).parents[1] / 'scripts/places-recovery-preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PlacesCheckpointTests(unittest.TestCase):
    def fixture(self, root, duplicate=False):
        curated = root / 'curated'
        builder = test_places_common.PlacesCommonTests()
        for source, kind in [('overture-food-places', 'site'), ('wikidata-food-businesses', 'organization')]:
            builder.normalized(curated, source, '1', kind, {'name': 'Fixture'})
            path = curated / 'records' / source / '00.jsonl.gz'
            row = json.loads(gzip.decompress(path.read_bytes()))
            second = json.loads(json.dumps(row))
            if not duplicate:
                second[1][0]['provenance']['recordId'] = '2'
                second[1][0]['id'] += '2'
            path.write_bytes(gzip.compress(('\n'.join(json.dumps(x) for x in [row, second]) + '\n').encode(), mtime=0))
        files = [{'key': str(p.relative_to(curated)), 'bytes': p.stat().st_size, 'sha256': places.digest(p)} for p in sorted(curated.rglob('*.gz'))]
        (curated / 'manifest.json').write_text(json.dumps({'releaseId': 'fixture', 'files': files, 'sources': {s: {'releaseId': 'fixture', 'records': 2, 'license': 'CC0', 'attribution': 'Fixture', 'rawSourcePayloadPublished': False} for s in ['overture-food-places', 'wikidata-food-businesses']}}))
        return curated

    def interrupt(self, curated, output, packets_per_file=1):
        original = places.Checkpoint.save
        def save(checkpoint):
            original(checkpoint)
            if sum(checkpoint.value['input_counts'].values()) == 2:
                raise RuntimeError('synthetic interruption')
        with patch.object(places.Checkpoint, 'save', save):
            with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
                places.align(curated, output, records_per_packet=1, packets_per_file=packets_per_file)

    def test_interrupted_resume_equals_uninterrupted_with_buffered_files(self):
        for grouping in [1, 3]:
            with self.subTest(grouping=grouping), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); source = self.fixture(root); out = root / 'out'
                self.interrupt(source, out, grouping)
                with patch.object(places.dt, 'datetime') as clock:
                    # Reuse checkpoint's creation timestamp for exact manifest comparison.
                    import sqlite3
                    with sqlite3.connect(root / 'out.checkpoint.sqlite') as db:
                        created = json.loads(db.execute('SELECT payload FROM state').fetchone()[0])['createdAt']
                    clock.now.return_value.isoformat.return_value = created
                    expected = places.align(source, root / 'expected', records_per_packet=1, packets_per_file=grouping)
                actual = places.align(source, out, records_per_packet=1, packets_per_file=grouping, resume=True)
                self.assertEqual(actual, expected)
                self.assertEqual({p.name:p.read_bytes() for p in out.rglob('*.gz')}, {p.name:p.read_bytes() for p in (root/'expected').rglob('*.gz')})

    def test_atomic_close_before_checkpoint_commit_is_recovered(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=self.fixture(root);out=root/'out'
            original=places.atomic_bytes
            def write_then_interrupt(path, raw):
                original(path, raw)
                if path.name == 'part-00000.jsonl.gz':
                    raise RuntimeError('crash after atomic rename')
            with patch.object(places, 'atomic_bytes', write_then_interrupt):
                with self.assertRaisesRegex(RuntimeError, 'crash after atomic rename'):
                    places.align(source,out,records_per_packet=1)
            actual=places.align(source,out,records_per_packet=1,resume=True)
            self.assertEqual(actual['counts']['resources'],4)

    def test_mid_packet_failure_rolls_back_cursor_and_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=self.fixture(root);out=root/'out'
            original=places.PacketSink.add
            calls=0
            def fail(sink,row):
                nonlocal calls
                calls+=1
                if calls==2:raise RuntimeError('mid-packet interruption')
                original(sink,row)
            with patch.object(places.PacketSink,'add',fail):
                with self.assertRaises(RuntimeError):places.align(source,out,records_per_packet=3)
            actual=places.align(source,out,records_per_packet=3,resume=True)
            self.assertEqual(actual['counts']['resources'],4)

    def test_pin_output_corruption_and_stale_lock_refused(self):
        for failure in ['source', 'options', 'truncation', 'lock', 'extra', 'output']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); source=self.fixture(root); out=root/'out'
                self.interrupt(source,out)
                kwargs={}
                if failure=='source': (source/'manifest.json').write_text('{}')
                if failure=='options': kwargs['max_asset_bytes']=10000
                if failure=='truncation': next((root/'out.partial'/'packets').glob('*.gz')).write_bytes(b'bad')
                if failure=='lock': (root/'out.alignment.lock').write_text('historical owner')
                if failure=='extra': (root/'out.partial'/'packets'/'part-99999.jsonl.gz').write_bytes(b'bad')
                if failure=='output': out.mkdir()
                with self.assertRaises(ValueError): places.align(source,out,records_per_packet=1,resume=True,**kwargs)

    def test_duplicate_identity_survives_resume_and_uncommitted_rows_roll_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=self.fixture(root);out=root/'out'
            self.interrupt(source,out)
            original=places.Checkpoint.add_identity
            def duplicate(checkpoint,source,record):
                original(checkpoint, 'overture-food-places', '1')
            with patch.object(places.Checkpoint,'add_identity',duplicate):
                with self.assertRaisesRegex(ValueError,'duplicate'):places.align(source,out,records_per_packet=1,resume=True)
            places.align(source,out,records_per_packet=1,resume=True)

    def test_pinned_duplicate_and_truncated_gzip_fail_on_read(self):
        for failure in ['duplicate', 'gzip']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root=Path(temp);source=self.fixture(root,duplicate=failure=='duplicate');out=root/'out'
                if failure=='gzip':
                    path=next(source.rglob('*.gz'));path.write_bytes(path.read_bytes()[:-8])
                    manifest=json.loads((source/'manifest.json').read_text())
                    entry=next(e for e in manifest['files'] if e['key']==str(path.relative_to(source)))
                    entry.update(bytes=path.stat().st_size,sha256=places.digest(path))
                    (source/'manifest.json').write_text(json.dumps(manifest))
                    with self.assertRaises(EOFError):places.align(source,out,records_per_packet=1)
                else:
                    original=places.Checkpoint.save
                    def stop(checkpoint):
                        original(checkpoint)
                        if sum(checkpoint.value['input_counts'].values())==1:raise RuntimeError('stop')
                    with patch.object(places.Checkpoint,'save',stop):
                        with self.assertRaises(RuntimeError):places.align(source,out,records_per_packet=1)
                    with self.assertRaisesRegex(ValueError,'duplicate'):
                        places.align(source,out,records_per_packet=1,resume=True)

    def test_legacy_and_truncated_input_refused_without_adoption(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=self.fixture(root);out=root/'out'
            (root/'out.partial').mkdir()
            with self.assertRaisesRegex(ValueError,'legacy'):places.align(source,out,resume=True)
            p=next(source.rglob('*.gz'));p.write_bytes(p.read_bytes()[:-8])
            with self.assertRaisesRegex(ValueError,'input bytes'):places.align(source,root/'new',records_per_packet=1)

    def test_inventory_and_storage_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'packets').mkdir()
            for i in range(3):(root/'packets'/f'{i}.jsonl.gz').write_bytes(b'retained')
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result=preflight.inventory(root,2,hash_limit=1)
            self.assertEqual(result['countDifference'],1)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertFalse(preflight.storage_preflight(99,20,10,60,10)['capacityPass'])
        self.assertTrue(preflight.storage_preflight(100,20,10,60,10)['capacityPass'])
        for bad in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):preflight.storage_preflight(100,20,10,bad,10)
