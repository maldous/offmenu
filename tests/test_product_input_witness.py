"""Generated raw fixtures, independent of all candidate adapters and outputs."""
from dataclasses import asdict, replace
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from offmenu.refresh.acceptance import Asset, ids_digest
from offmenu.refresh.core import RefreshError, canonical
from offmenu.refresh.product_input_witness import (OPERATION, Table, WitnessContract,
                                                  WitnessLimits, witness_retained_input)


class ProductInputWitnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root/'bundle'
        self.bundle.mkdir()
        self.limits = WitnessLimits(min_free_bytes=1)

    def asset(self, name, data):
        (self.bundle/name).write_bytes(data)
        return Asset(name, len(data), hashlib.sha256(data).hexdigest())

    def bind(self, source, body, tables=(), members=()):
        original = self.asset('source.bin', body)
        rights = self.asset('rights.json', canonical({'fixturePermit': ['retain','parse','transform']}))
        clock = self.asset('clock.json', canonical({'sources': [{'sourceId': source,
            'originalSha256': original.sha256, 'originalBytes': original.bytes, 'originalAcquiredAt': None}]}))
        scope = self.asset('scope.json', canonical({'operation': OPERATION, 'sourceId': source,
            'releaseId': 'fixture-release', 'scopeId': 'full-fixture', 'original': asdict(original),
            'rightsEvidenceSha256': rights.sha256, 'clockEvidenceSha256': clock.sha256,
            'originalAcquiredAt': None, 'denominator': 'full-declared-input',
            'tables': [asdict(t) for t in tables], 'members': list(members)}))
        return WitnessContract(source, 'fixture-release', 'full-fixture', original, rights, scope,
            clock, frozenset(('retain','parse','transform')), tables, members, fixture=True)

    def off(self, rows=None, raw=None):
        if raw is None:
            rows = [{'code':'0001','private':'raw-one'}, {'code':'0002'}] if rows is None else rows
            raw = b''.join(canonical(row) for row in rows)
        return self.bind('off', gzip.compress(raw, mtime=0))

    def usda(self, change=None, extra=None):
        data = {
            'food.csv': [('fdc_id','description'), [('1','One'),('2','Two')]],
            'nutrient.csv': [('id','name'), [('1003','Protein')]],
            'branded_food.csv': [('fdc_id','gtin_upc'), [('1','00123')]],
            'food_nutrient.csv': [('id','fdc_id','nutrient_id'), [('10','1','1003')]],
            'support.csv': [('fdc_id','note'), [('1','same'),('1','same')]]}
        if change:
            change(data)
        members = ['FDC/'+n for n in data] + ['FDC/companion.bin']
        food, nutrient = 'FDC/food.csv', 'FDC/nutrient.csv'
        tables = []
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, (columns, rows) in data.items():
                member = 'FDC/'+name
                key = ('id',) if name in ('nutrient.csv','food_nutrient.csv') else ('fdc_id',) if name in ('food.csv','branded_food.csv') else ()
                refs = ((('fdc_id',), food),) if name in ('branded_food.csv','food_nutrient.csv') else ()
                if name == 'food_nutrient.csv':
                    refs += ((('nutrient_id',), nutrient),)
                tables.append(Table(member, tuple(columns), key, refs))
                text = io.StringIO(newline='')
                writer = csv.writer(text);writer.writerow(columns);writer.writerows(rows)
                archive.writestr(member, text.getvalue())
            archive.writestr('FDC/companion.bin', b'\x00support bytes\xff')
            if extra:
                archive.writestr(*extra)
        return self.bind('usda-files', buffer.getvalue(), tuple(tables), tuple(members))

    def run_witness(self, contract, *, name='output', limits=None):
        return witness_retained_input(contract, self.bundle, self.root/name, limits=limits or self.limits)

    def assert_clean(self, result, source, keys):
        self.assertTrue(result['fullDenominatorTraversed'], result)
        self.assertTrue(result['eligibleCleanScopeWitness'], result)
        expected = [source+':'+kind+':'+key for key in keys for kind in ('product','nutrientProfile')]
        self.assertEqual(result['expectedRecords'], len(expected))
        self.assertEqual(result['expectedSortedIdSha256'], ids_digest(expected))
        self.assertFalse(result['accepted'])
        self.assertFalse(result['countryComplete'])

    def test_off_full_native_ids_and_deterministic_retry_new_destination(self):
        c = self.off()
        first = self.run_witness(c)
        self.assert_clean(first, 'off', ['0001','0002'])
        self.assertEqual(first, self.run_witness(c, name='second'))
        self.assertEqual(set(p.name for p in (self.root/'output').iterdir()), {'result.json','diagnostics.jsonl'})
        self.assertNotIn('raw-one', (self.root/'output/result.json').read_text())
        with self.assertRaises(RefreshError):
            self.run_witness(c)

    def test_off_duplicate_conflict_invalid_and_quarantine_lossless(self):
        raw = (b'{"code":"0001"}\n{"code":"0001"}\n{"code":"0001","x":1}\n'
               b'invalid\n{"code":"bad"}\n{"code":1234}\n{"code":"0002"}\n')
        result = self.run_witness(self.off(raw=raw))
        self.assertTrue(result['fullDenominatorTraversed'])
        self.assertFalse(result['eligibleCleanScopeWitness'])
        self.assertEqual(result['tables']['products'], {'rows':7,'valid':2,'duplicate':2,'invalid':1,
            'quarantined':2,'keyless':0,'conflictingDuplicate':1,'joinFailures':0,'unclassifiedRows':0})
        self.assertIsNone(result['expectedRecords'])
        self.assertEqual(len((self.root/'output/diagnostics.jsonl').read_text().splitlines()),5)

    def test_blank_invalid_utf8_and_duplicate_json_keys_are_not_dropped(self):
        r = self.run_witness(self.off(raw=b'\n\xff\n{"code":"0001","code":"0002"}\n'))
        self.assertEqual(r['rowsObserved'],3)
        self.assertEqual(r['tables']['products']['invalid'],3)
        self.assertTrue(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedSortedIdSha256'])

    def test_row_limit_is_incomplete(self):
        r = self.run_witness(self.off(), limits=replace(self.limits,max_rows=1))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertEqual(r['rowsObserved'],1)
        self.assertIn('row-limit',r['errors'])

    def test_id_limit_is_incomplete(self):
        r = self.run_witness(self.off(), limits=replace(self.limits,max_id_bytes=3))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIn('native-id-byte-limit',r['errors'])
        self.assertEqual(r['tables']['products']['unclassifiedRows'],1)
        self.assertTrue(r['unparsedTailPossible'])

    def test_expansion_limit_is_incomplete(self):
        r = self.run_witness(self.off(),limits=replace(self.limits,max_expanded_bytes=2))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedRecords'])

    def test_diagnostic_limit_is_incomplete(self):
        r = self.run_witness(self.off(raw=b'bad\nbad\n'),limits=replace(self.limits,max_diagnostic_bytes=1))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIn('diagnostic-byte-limit',r['errors'])
        self.assertLessEqual(r['diagnosticBytes'],1)

    def test_corrupt_compressed_input_retained_as_incomplete(self):
        r = self.run_witness(self.bind('off',b'not gzip'))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedRecords'])

    def test_database_full_fails_incomplete(self):
        c = self.off([{'code':str(100000+i)} for i in range(3000)])
        r = self.run_witness(c,limits=replace(self.limits,max_database_bytes=65536))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedRecords'])

    def test_rights_and_holds_fail_before_any_digest(self):
        c = self.off()
        for altered in (replace(c,holds=('held',)),replace(c,permitted_operations=frozenset(('retain',)))):
            with patch('offmenu.refresh.product_input_witness.digest') as read:
                with self.assertRaises(RefreshError):self.run_witness(altered)
                read.assert_not_called()

    def test_pinned_original_and_extra_bundle_member_rejected(self):
        c = self.off()
        (self.bundle/'source.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(RefreshError,'custody-mismatch'):self.run_witness(c)
        (self.bundle/'extra').write_text('not selected')
        with self.assertRaises(RefreshError):self.run_witness(c)
        self.assertFalse((self.root/'output').exists())

    def test_bad_scope_and_clock_are_not_permission(self):
        c = self.off()
        for changed in (replace(c,scope_id='other'), replace(c,original_acquired_at='2026-10-12T00:00:00Z')):
            with self.assertRaises(RefreshError):self.run_witness(changed)

    def test_low_free_space_refuses_without_allocation(self):
        c = self.off()
        with patch('offmenu.refresh.product_input_witness.shutil.disk_usage') as disk:
            disk.return_value.free=0
            with self.assertRaisesRegex(RefreshError,'free-space'):self.run_witness(c)
        self.assertFalse((self.root/'output').exists())

    def test_usda_all_members_keyless_rows_and_independent_ids(self):
        r = self.run_witness(self.usda())
        self.assert_clean(r,'usda-files',['1','2'])
        self.assertEqual(r['rowsObserved'],7)
        self.assertEqual(r['tables']['FDC/support.csv']['keyless'],2)
        self.assertEqual(r['tables']['FDC/food.csv']['rows'],2)

    def test_usda_orphan_joins_counted_without_dropping_rows(self):
        def change(d):d['food_nutrient.csv'][1].append(('11','999','999'))
        r = self.run_witness(self.usda(change))
        self.assertTrue(r['fullDenominatorTraversed'])
        self.assertEqual(r['tables']['FDC/food_nutrient.csv']['joinFailures'],2)
        self.assertIsNone(r['expectedRecords'])

    def test_usda_width_missing_key_and_duplicate_are_reported(self):
        def change(d):d['food.csv'][1].extend([('1','Different'),('','Missing'),('4',)])
        r = self.run_witness(self.usda(change))
        self.assertTrue(r['fullDenominatorTraversed'])
        counts=r['tables']['FDC/food.csv']
        self.assertEqual((counts['duplicate'],counts['quarantined'],counts['invalid']),(1,1,1))
        self.assertIsNone(r['expectedSortedIdSha256'])

    def test_usda_multiline_csv_is_one_logical_row(self):
        def change(d):d['food.csv'][1][0]=('1','One\nsecond line')
        r=self.run_witness(self.usda(change))
        self.assert_clean(r,'usda-files',['1','2'])

    def test_usda_undeclared_archive_member_fails_incomplete(self):
        r=self.run_witness(self.usda(extra=('extra.csv','id\n1\n')))
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIn('archive-inventory-or-expansion-mismatch',r['errors'])

    def test_missing_declared_join_refused_by_trusted_contract_preflight(self):
        c=self.usda()
        # Rebinding scope cannot bypass the required food/nutrient references.
        tables=tuple(replace(t,references=()) if t.member.endswith('food_nutrient.csv') else t for t in c.tables)
        c=self.bind('usda-files',(self.bundle/'source.bin').read_bytes(),tables,c.members)
        with self.assertRaisesRegex(RefreshError,'required-join'):self.run_witness(c)

    def test_timeout_after_start_is_incomplete(self):
        c=self.off()
        from offmenu.refresh.product_input_witness import _Run, _Stop
        with patch.object(_Run,'guard',side_effect=_Stop('duration-limit')):
            r=self.run_witness(c)
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedRecords'])

    def test_destination_cannot_overlap_originals_or_follow_symlinks(self):
        c=self.off()
        with self.assertRaises(RefreshError):witness_retained_input(c,self.bundle,self.bundle/'out',limits=self.limits)
        (self.root/'link').symlink_to(self.bundle,target_is_directory=True)
        with self.assertRaises(RefreshError):witness_retained_input(c,self.root/'link',self.root/'out',limits=self.limits)

    def test_read_original_in_place_without_copy_or_directory_census(self):
        c=self.off()
        originals=self.root/'originals';originals.mkdir()
        (self.bundle/'source.bin').rename(originals/'source.bin')
        (originals/'unrelated.bin').write_bytes(b'not selected; never opened')
        r=witness_retained_input(c,self.bundle,self.root/'output',input_root=originals,limits=self.limits)
        self.assert_clean(r,'off',['0001','0002'])
        self.assertEqual((originals/'unrelated.bin').read_bytes(),b'not selected; never opened')

    def test_postparse_mutation_is_incomplete(self):
        c=self.off()
        from offmenu.refresh import product_input_witness as module
        original=module._off
        def mutate(*args):
            original(*args)
            (self.bundle/'source.bin').write_bytes(b'changed after parse')
        with patch.object(module,'_off',side_effect=mutate):r=self.run_witness(c)
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedRecords'])

    def test_source_binding_metadata_and_caps(self):
        from offmenu.refresh.product_witness_bindings import retained_witness_contract, retained_witness_limits
        asset=Asset('fixture',1,'a'*64)
        c=retained_witness_contract('usda-files',asset,asset,asset)
        self.assertEqual(len(c.tables),34)
        self.assertEqual(len(c.members),35)
        self.assertEqual(c.release_id,'2026-04-30')
        for source,gib in (('off',10),('usda-files',28)):
            limits=retained_witness_limits(source,protected_bytes_including_floor=20*1024**3)
            self.assertEqual(limits.max_database_bytes+limits.max_diagnostic_bytes+limits.max_output_bytes+1024**2,gib*1024**3)
        with self.assertRaises(ValueError):retained_witness_limits('off',protected_bytes_including_floor=1)

    def test_utf8_csv_corruption_does_not_claim_full_denominator(self):
        c=self.usda()
        # Re-pin a corrupt synthetic CSV archive: custody success is not parsing success.
        raw=io.BytesIO((self.bundle/'source.bin').read_bytes());changed=io.BytesIO()
        with zipfile.ZipFile(raw) as src,zipfile.ZipFile(changed,'w') as dst:
            for name in src.namelist():dst.writestr(name,b'fdc_id,description\n1,\xff\n' if name=='FDC/food.csv' else src.read(name))
        c=self.bind('usda-files',changed.getvalue(),c.tables,c.members)
        r=self.run_witness(c)
        self.assertFalse(r['fullDenominatorTraversed'])
        self.assertIsNone(r['expectedSortedIdSha256'])

    def test_racing_destination_is_never_overwritten(self):
        c=self.off()
        from offmenu.refresh import product_input_witness as module
        original=module._off
        def race(*args):
            original(*args)
            (self.root/'output').mkdir()
            (self.root/'output/other-owner').write_bytes(b'preserved')
        with patch.object(module,'_off',side_effect=race):
            with self.assertRaises(FileExistsError):self.run_witness(c)
        self.assertEqual((self.root/'output/other-owner').read_bytes(),b'preserved')
        self.assertFalse((self.root/'output/result.json').exists())

    def test_diagnostic_digest_matches_exact_retained_bytes(self):
        r=self.run_witness(self.off(raw=b'bad\n'))
        self.assertEqual(r['diagnosticsSha256'],hashlib.sha256((self.root/'output/diagnostics.jsonl').read_bytes()).hexdigest())

    def assert_metadata_mutation_rejected(self, field, mode):
        from offmenu.refresh import product_input_witness as w
        c=self.off()
        target=self.bundle/getattr(c,field).path
        original=target.read_bytes();inode=target.stat().st_ino
        replacement=self.root/'replacement.json';replacement.write_bytes(original)
        real_read=os.read;changed=False
        def mutate(fd,size):
            nonlocal changed
            data=real_read(fd,size)
            if os.fstat(fd).st_ino==inode and not changed:
                changed=True
                if mode=='grow':target.write_bytes(original+b' '*(2*1024**2))
                elif mode=='replace':os.replace(replacement,target)
                else:
                    target.unlink();target.symlink_to(replacement)
            return data
        with patch.object(w.os,'read',side_effect=mutate),patch.object(w,'strict_json') as parse, \
                patch.object(w,'digest',side_effect=AssertionError('original must not be read')) as original_read:
            with self.assertRaises(RefreshError):self.run_witness(c)
            parse.assert_not_called();original_read.assert_not_called()
        self.assertTrue(changed)
        self.assertFalse((self.root/'output').exists())

    def test_scope_growth_at_actual_read_rejected_before_original(self):
        self.assert_metadata_mutation_rejected('scope_evidence','grow')

    def test_clock_growth_at_actual_read_rejected_before_original(self):
        self.assert_metadata_mutation_rejected('clock_evidence','grow')

    def test_metadata_same_byte_inode_replacement_rejected_before_original(self):
        self.assert_metadata_mutation_rejected('clock_evidence','replace')

    def test_metadata_symlink_swap_rejected_before_original(self):
        self.assert_metadata_mutation_rejected('scope_evidence','symlink')

    def test_metadata_deadline_after_read_rejects_before_parse_or_original(self):
        from offmenu.refresh import product_input_witness as w
        c=self.off();expired=False;real_read=os.read
        def read(fd,size):
            nonlocal expired
            data=real_read(fd,size);expired=True;return data
        with patch.object(w.time,'monotonic',side_effect=lambda:4000 if expired else 0), \
                patch.object(w.os,'read',side_effect=read),patch.object(w,'strict_json') as parse, \
                patch.object(w,'digest',side_effect=AssertionError('no original read')) as original_read:
            with self.assertRaisesRegex(RefreshError,'evidence-duration-limit'):self.run_witness(c)
            parse.assert_not_called();original_read.assert_not_called()

    def test_nonregular_symlink_and_oversize_metadata_never_parse(self):
        from offmenu.refresh import product_input_witness as w
        c=self.off();target=self.bundle/c.rights_evidence.path;original=target.read_bytes()
        replacement=self.root/'replacement.json';replacement.write_bytes(original)
        for mode in ('directory','fifo','symlink','oversize'):
            with self.subTest(mode=mode):
                target.unlink()
                if mode=='directory':target.mkdir()
                elif mode=='fifo':os.mkfifo(target)
                elif mode=='symlink':target.symlink_to(replacement)
                else:target.write_bytes(b'x'*(1024**2+1))
                with patch.object(w,'strict_json') as parse,patch.object(w,'digest') as original_read:
                    with self.assertRaises(RefreshError):self.run_witness(c)
                    parse.assert_not_called();original_read.assert_not_called()
                target.rmdir() if mode=='directory' else target.unlink()
                target.write_bytes(original)

    def test_same_size_wrong_hash_metadata_never_parsed(self):
        from offmenu.refresh import product_input_witness as w
        c=self.off();target=self.bundle/c.clock_evidence.path;original=target.read_bytes()
        target.write_bytes(b'['+original[1:])
        with patch.object(w,'strict_json') as parse,patch.object(w,'digest') as original_read:
            with self.assertRaises(RefreshError):self.run_witness(c)
            parse.assert_not_called();original_read.assert_not_called()

    def test_maximum_scope_buffer_and_read_requests_bounded(self):
        from offmenu.refresh import product_input_witness as w
        c=self.off();scope=json.loads((self.bundle/c.scope_evidence.path).read_bytes())
        scope['syntheticPadding']='';scope['syntheticPadding']='x'*(1024**2-len(canonical(scope)))
        asset=self.asset(c.scope_evidence.path,canonical(scope));c=replace(c,scope_evidence=asset)
        self.assertEqual(asset.bytes,1024**2)
        real_read,real_json=os.read,w.strict_json;requests=[];parsed=[]
        def read(fd,size):requests.append(size);return real_read(fd,size)
        def parse(raw):parsed.append(raw);return real_json(raw)
        with patch.object(w.os,'read',side_effect=read),patch.object(w,'strict_json',side_effect=parse):
            w._preflight(c,self.bundle,self.limits,time.monotonic()+10)
        self.assertEqual([len(raw) for raw in parsed],[1024**2,c.clock_evidence.bytes])
        self.assertTrue(all(0<size<=65536 for size in requests))
        self.assertEqual(hashlib.sha256(parsed[0]).hexdigest(),asset.sha256)
