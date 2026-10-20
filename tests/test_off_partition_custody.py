"""Generated originals/evidence only; no retained corpus or live databases."""
from dataclasses import asdict, replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import off_partition_custody as c
from offmenu.refresh.acceptance import Asset
from offmenu.refresh.core import RefreshError, canonical


class PartitionCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root/'evidence'; self.evidence.mkdir()
        self.originals = self.root/'originals'; self.originals.mkdir()
        self.source = self.originals/'products.jsonl.gz'
        self.rows = [{'code':'0001','private':'DO_NOT_COPY'}, {'code':'0002'}, {'code':1234},
                     {'code':'0001','private':'changed'}, {'code':'9999'}, {'code':'0001','private':'changed'}]
        self.limits = c.CustodyLimits(1024**2, 30,
            c.partition_core.PartitionLimits(1000, 65536, 1024**2, 1024**2, 1024**2, 20))

    def asset(self, root, name, raw):
        (root/name).write_bytes(raw)
        return Asset(name, len(raw), hashlib.sha256(raw).hexdigest())

    def bind(self, *, compressed=None, expected_rows=6, scope_change=None, clock_change=None,
             selection_change=None, original_change=None, pins=None):
        raw = gzip.compress(b''.join(canonical(r) for r in self.rows), mtime=0) if compressed is None else compressed
        self.compressed = raw
        original = self.asset(self.originals, 'products.jsonl.gz', raw)
        if original_change: original = original_change(original)
        rights = self.asset(self.evidence, 'rights.txt', b'GENERATED FIXTURE TERMS; no real rights grant\n')
        identity = {'sourceId':'off', 'releaseId':'fixture-release', 'scopeId':'fixture-full-original'}
        clock = {**identity, 'schemaVersion':'offmenu-retained-clock-evidence/1',
            'status':'unknown-retained', 'originalAcquiredAt':None,
            'rightsEvidenceSha256':rights.sha256, 'inputFiles':[asdict(original)],
            'basisEvidenceSha256':'b'*64}
        if clock_change: clock_change(clock)
        clock_asset = self.asset(self.evidence, 'clock.json', canonical(clock))
        scope = {**identity, 'schemaVersion':'offmenu-off-partition-scope/1',
            'operation':'private-retained-off-full-occurrence-partition', 'original':asdict(original),
            'rightsEvidenceSha256':rights.sha256,
            'acquisitionClock':{'status':'unknown-retained','evidenceSha256':clock_asset.sha256},
            'denominator':'full-declared-original', 'table':'products', 'framing':'gzip-utf8-jsonl-lf',
            'expectedSourceRows':expected_rows, 'partitionPolicy':'full-original-ordinal-SCQ-no-primary/1',
            'cooperativeLimits':asdict(self.limits), 'executorRequirements':[
                'serialized-linux-default-sqlite-main-file-attribution',
                'external-os-wallclock-memory-file-storage-boundary',
                'retained-scratch-active-until-safe-owner-disposition']}
        if scope_change: scope_change(scope)
        scope_asset = self.asset(self.evidence, 'scope.json', canonical(scope))
        # Test-only independent application selection; no production factory.
        if pins is None:
            pins = c.ImplementationPins(*(hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in (c.__file__, c.partition_core.__file__, c.original_protocol.__file__)))
        selection = {**identity, 'schemaVersion':'offmenu-off-partition-selection/1',
            'operation':'private-retained-off-full-occurrence-partition', 'original':asdict(original),
            'scopeEvidenceSha256':scope_asset.sha256, 'rightsEvidenceSha256':rights.sha256,
            'clockEvidenceSha256':clock_asset.sha256, 'expectedSourceRows':expected_rows,
            'implementation':asdict(pins), 'permittedOperations':['parse','retain','transform'], 'fixture':True}
        if selection_change: selection_change(selection)
        selection_asset = self.asset(self.evidence, 'selection.json', canonical(selection))
        return c.PartitionOperation('fixture-release', 'fixture-full-original', original,
            rights, scope_asset, clock_asset, selection_asset, expected_rows,
            frozenset(('retain','parse','transform')), pins, fixture=True)

    def run_operation(self, operation, name='output'):
        return c.partition_retained_original(operation, self.evidence, self.originals,
                                             self.root/name, limits=self.limits)

    def assert_no_output(self):
        self.assertFalse((self.root/'output').exists())

    def test_full_original_partition_and_separate_nonadmitting_custody_receipt(self):
        op = self.bind(); result = self.run_operation(op); part = result['partition']
        self.assertEqual(part['counts'], {'S':2,'C':3,'Q':1})
        self.assertEqual(result['sourceRows'],6); self.assertTrue(result['originalFileCustodyVerified'])
        self.assertTrue(result['compressedPrePostSha256Verified']); self.assertTrue(result['fullGzipCRCAndEOF'])
        self.assertEqual(result['originalIdentityBefore'],result['originalIdentityAfter'])
        self.assertEqual(result['returnedPartitionResultSha256'],hashlib.sha256(canonical(part)).hexdigest())
        self.assertIsNone(result['originalAcquiredAt']); self.assertEqual(result['acquisitionClockStatus'],'unknown-retained')
        self.assertIsNone(result['expectedRecords']); self.assertIsNone(result['expectedSortedIdSha256'])
        for key in ('accepted','runtimeQualified','realResourcesAdmitted','eligibleCleanScopeWitness',
                    'countryComplete','durableCustodyReceiptPublished'): self.assertFalse(result[key])
        disk = json.loads((self.root/'output/result.json').read_bytes())
        self.assertFalse(disk['sourceCustodyVerified']); self.assertFalse(disk['accepted'])
        self.assertNotIn('originalFileCustodyVerified',disk)
        occurrences = [json.loads(x) for x in (self.root/'output/occurrences.jsonl').read_bytes().splitlines()]
        self.assertEqual([x['ordinal'] for x in occurrences],list(range(1,7)))
        self.assertEqual([x['status'] for x in occurrences],['C','S','Q','C','S','C'])
        for path in (self.root/'output').iterdir(): self.assertNotIn(b'DO_NOT_COPY',path.read_bytes())
        scratch = part['retainedScratch']; self.assertTrue(scratch['resourceObligationActive'])
        self.assertFalse(scratch['automaticDeletion']); self.assertTrue(scratch['databaseConnectionVerified'])

    def test_one_regular_source_descriptor_two_hash_passes_and_no_fd_leak(self):
        op = self.bind(); seen = []; real = c.original_protocol._VerifiedOriginal.verify
        def verify(source):
            seen.append((source.stream.fileno(),source.identity)); return real(source)
        before = len(os.listdir('/proc/self/fd'))
        with patch.object(c.original_protocol._VerifiedOriginal,'verify',verify): self.run_operation(op)
        self.assertEqual(len(seen),2); self.assertEqual(seen[0],seen[1])
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_operation_holds_and_missing_rights_fail_before_original_open(self):
        op = self.bind()
        for bad in (replace(op,holds=('source-use hold',)), replace(op,permitted_operations=frozenset(('retain',))),
                    asdict(op), replace(op,expected_rows=True)):
            with patch.object(c.original_protocol,'_VerifiedOriginal',side_effect=AssertionError('original must not open')):
                with self.assertRaises(RefreshError): self.run_operation(bad)
            self.assert_no_output()

    def test_exact_scope_denominator_original_and_selection_bindings(self):
        changes = [('denominator','filtered-singletons'), ('sourceId','other'), ('expectedSourceRows',5),
                   ('rightsEvidenceSha256','0'*64), ('table','filtered-products')]
        for key,value in changes:
            op = self.bind(scope_change=lambda s:s.update({key:value}))
            with patch.object(c.original_protocol,'_VerifiedOriginal',side_effect=AssertionError('original must not open')):
                with self.assertRaisesRegex(RefreshError,'selected-scope-mismatch'): self.run_operation(op)
        op = self.bind(selection_change=lambda s:s.update({'scopeEvidenceSha256':'0'*64}))
        with self.assertRaisesRegex(RefreshError,'selected-scope-mismatch'): self.run_operation(op)
        self.assert_no_output()

    def test_unknown_clock_never_replaced_with_an_invented_acquisition_time(self):
        for change in (lambda s:s.update({'originalAcquiredAt':'2026-10-21T00:00:00Z'}),
                       lambda s:s.update({'status':'known'}),lambda s:s.update({'basisEvidenceSha256':None}),
                       lambda s:s.update({'releaseId':'different-release'})):
            op = self.bind(clock_change=change)
            with patch.object(c.original_protocol,'_VerifiedOriginal',side_effect=AssertionError('original must not open')):
                with self.assertRaisesRegex(RefreshError,'clock-mismatch'): self.run_operation(op)
        self.assert_no_output()

    def test_metadata_tampering_and_extra_files_fail_before_original_open(self):
        op = self.bind(); (self.evidence/'rights.txt').write_bytes(b'changed')
        with patch.object(c.original_protocol,'_VerifiedOriginal',side_effect=AssertionError('original must not open')):
            with self.assertRaises(RefreshError): self.run_operation(op)
        op = self.bind(); (self.evidence/'undeclared').write_text('unselected')
        with self.assertRaises(RefreshError): self.run_operation(op)
        self.assert_no_output()

    def test_selected_implementation_pins_are_not_replaced_by_current_self_hash(self):
        pins = c.ImplementationPins('0'*64,'1'*64,'2'*64); op = self.bind(pins=pins)
        with patch.object(c.original_protocol,'_VerifiedOriginal',side_effect=AssertionError('original must not open')):
            with self.assertRaisesRegex(RefreshError,'implementation-mismatch'): self.run_operation(op)
        self.assert_no_output()

    def test_original_size_and_hash_must_match_independently_selected_assets(self):
        for change in (lambda a:replace(a,bytes=a.bytes+1),lambda a:replace(a,sha256='0'*64)):
            op = self.bind(original_change=change)
            with self.assertRaisesRegex(RefreshError,'original-custody-mismatch'): self.run_operation(op)
            self.assert_no_output()

    def test_original_symlink_and_fifo_are_rejected_without_blocking(self):
        op = self.bind(); self.source.rename(self.originals/'saved')
        self.source.symlink_to(self.originals/'saved')
        with self.assertRaises(RefreshError): self.run_operation(op)
        self.source.unlink(); os.mkfifo(self.source)
        with self.assertRaisesRegex(RefreshError,'original-custody-mismatch'): self.run_operation(op)
        self.assert_no_output()

    def test_original_replacement_during_stream_refuses_success_and_retains_scratch(self):
        op = self.bind(); real = c.partition_core.partition_stream
        def intercepted(lines,*args,**kwargs):
            def changed():
                for i,line in enumerate(lines):
                    yield line
                    if i == 0:
                        self.source.rename(self.originals/'relocated-original'); self.source.write_bytes(self.compressed)
            return real(changed(),*args,**kwargs)
        with patch.object(c.partition_core,'partition_stream',side_effect=intercepted):
            with self.assertRaisesRegex(RefreshError,'original-custody-mismatch') as failure: self.run_operation(op)
        self.assert_no_output(); self.assertFalse(failure.exception.partition_custody_state['custodyReceiptReturned'])
        self.assertTrue(failure.exception.partition_retained_state['resourceObligationActive'])
        self.assertTrue((self.originals/'relocated-original').exists())

    def test_in_place_original_write_during_stream_is_detected(self):
        op = self.bind(); real = c.partition_core.partition_stream
        def intercepted(lines,*args,**kwargs):
            def changed():
                for i,line in enumerate(lines):
                    yield line
                    if i == 0: self.source.write_bytes(self.compressed)
            return real(changed(),*args,**kwargs)
        with patch.object(c.partition_core,'partition_stream',side_effect=intercepted):
            with self.assertRaisesRegex(RefreshError,'original-custody-mismatch'): self.run_operation(op)
        self.assert_no_output()

    def test_late_source_failure_leaves_only_unqualified_core_output(self):
        op = self.bind(); real = c.partition_core.partition_stream
        def changed_after_core(*args,**kwargs):
            result = real(*args,**kwargs)
            self.source.rename(self.originals/'relocated-original'); self.source.write_bytes(self.compressed)
            return result
        with patch.object(c.partition_core,'partition_stream',side_effect=changed_after_core):
            with self.assertRaisesRegex(RefreshError,'original-custody-mismatch') as failure: self.run_operation(op)
        state = failure.exception.partition_custody_state
        self.assertTrue(state['coreReturned']); self.assertFalse(state['custodyReceiptReturned'])
        self.assertEqual(state['unqualifiedCoreOutputLocation'],str(self.root/'output'))
        disk = json.loads((self.root/'output/result.json').read_bytes())
        self.assertFalse(disk['sourceCustodyVerified']); self.assertFalse(disk['accepted'])
        self.assertTrue(failure.exception.partition_retained_state['resourceObligationActive'])

    def test_late_evidence_failure_cannot_return_a_custody_receipt(self):
        op = self.bind(); real = c.partition_core.partition_stream
        def changed_after_core(*args,**kwargs):
            result = real(*args,**kwargs); (self.evidence/'rights.txt').write_bytes(b'changed'); return result
        with patch.object(c.partition_core,'partition_stream',side_effect=changed_after_core):
            with self.assertRaises(RefreshError) as failure: self.run_operation(op)
        self.assertTrue(failure.exception.partition_custody_state['coreReturned'])
        self.assertFalse(failure.exception.partition_custody_state['custodyReceiptReturned'])
        self.assertFalse(json.loads((self.root/'output/result.json').read_bytes())['sourceCustodyVerified'])

    def test_core_publish_failure_preserves_its_actual_retained_objects(self):
        op = self.bind(); real = c.partition_core._rename_noreplace
        def swap(srcfd,src,dstfd,dst):
            os.rename(src,'held-evidence',src_dir_fd=srcfd,dst_dir_fd=srcfd)
            os.mkdir(src,dir_fd=srcfd)
            fd = os.open(src+'/KEEP',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=srcfd)
            os.write(fd,b'unrelated'); os.close(fd)
            return real(srcfd,src,dstfd,dst)
        with patch.object(c.partition_core,'_rename_noreplace',side_effect=swap):
            with self.assertRaisesRegex(RefreshError,'partition-published-identity-mismatch') as failure:
                self.run_operation(op)
        state = failure.exception.partition_custody_state
        self.assertFalse(state['coreReturned']); self.assertFalse(state['custodyReceiptReturned'])
        self.assertEqual(state['requestedCoreOutputLocation'],str(self.root/'output'))
        self.assertFalse(state['coreOutputPresenceVerified'])
        self.assertEqual((self.root/'output/KEEP').read_bytes(),b'unrelated')
        self.assertTrue((Path(failure.exception.partition_retained_state['evidenceLocation'])/'result.json').exists())
        self.assertEqual(failure.exception.preserved_publication_location,str(self.root/'output'))

    def test_crc_truncation_and_trailing_compressed_garbage_refuse_success(self):
        raw = gzip.compress(b'{"code":"0001"}\n',mtime=0)
        corrupt = bytearray(raw); corrupt[-8] ^= 1
        for compressed in (bytes(corrupt),raw[:-4],raw+b'bad trailing bytes'):
            op = self.bind(compressed=compressed,expected_rows=1)
            with self.assertRaises((OSError,EOFError,RefreshError)) as failure: self.run_operation(op)
            self.assert_no_output(); self.assertFalse(failure.exception.partition_custody_state['custodyReceiptReturned'])

    def test_multiple_gzip_members_are_fully_traversed(self):
        compressed = gzip.compress(b'{"code":"0001"}\n',mtime=0)+gzip.compress(b'{"code":"0001"}\n',mtime=0)
        result = self.run_operation(self.bind(compressed=compressed,expected_rows=2))
        self.assertTrue(result['fullGzipCRCAndEOF']); self.assertEqual(result['sourceRows'],2)
        self.assertEqual(result['partition']['counts'],{'S':0,'C':2,'Q':0})

    def test_malformed_json_missing_lf_and_denominator_mismatch_are_not_filtered(self):
        for raw,count in ((b'bad\n',1),(b'{"code":"0001"}',1),
                          (b'{"code":"0001"}\n',2),(b'\n',1),
                          (b'{"code":"0001","code":"0002"}\n',1)):
            op = self.bind(compressed=gzip.compress(raw,mtime=0),expected_rows=count)
            with self.assertRaises(RefreshError): self.run_operation(op)
            self.assert_no_output()

    def test_line_and_expanded_caps_are_bound_to_selected_operation(self):
        for partition in (replace(self.limits.partition,max_line_bytes=4),
                          replace(self.limits.partition,max_expanded_bytes=4)):
            self.limits = replace(self.limits,partition=partition)
            op = self.bind()
            with self.assertRaises(RefreshError): self.run_operation(op)
            self.assert_no_output()

    def test_late_deadline_refuses_receipt_even_after_core_returns(self):
        op = self.bind(); real = c.partition_core.partition_stream; current = [100.0]
        def expire(*args,**kwargs):
            result = real(*args,**kwargs); current[0] = 1000.0; return result
        with patch.object(c.time,'monotonic',side_effect=lambda:current[0]), \
             patch.object(c.partition_core,'partition_stream',side_effect=expire):
            with self.assertRaisesRegex(RefreshError,'duration-limit') as failure: self.run_operation(op)
        self.assertTrue(failure.exception.partition_custody_state['coreReturned'])
        self.assertFalse(failure.exception.partition_custody_state['custodyReceiptReturned'])

    def test_roots_and_destination_are_separate_and_existing_output_is_preserved(self):
        op = self.bind(); out = self.root/'output'; out.mkdir(); (out/'KEEP').write_bytes(b'keep')
        with self.assertRaisesRegex(RefreshError,'destination-exists'): self.run_operation(op)
        self.assertEqual((out/'KEEP').read_bytes(),b'keep')
        with self.assertRaisesRegex(RefreshError,'root-overlap'):
            c.partition_retained_original(op,self.evidence,self.originals,self.originals/'output',limits=self.limits)

    def test_no_original_root_inventory_or_automatic_deletion(self):
        op = self.bind(); real = c.bundle_files; calls = []
        (self.originals/'unrelated').write_bytes(b'NEVER SELECTED')
        def inventory(root,expected):
            calls.append(root); self.assertEqual(root,self.evidence); return real(root,expected)
        with patch.object(c,'bundle_files',side_effect=inventory), \
             patch.object(os,'unlink',side_effect=AssertionError('no core/adapter delete')) as unlink, \
             patch.object(os,'rmdir',side_effect=AssertionError('no core/adapter delete')) as rmdir:
            self.run_operation(op)
            unlink.assert_not_called(); rmdir.assert_not_called()
        self.assertEqual(len(calls),3)
        self.assertEqual((self.originals/'unrelated').read_bytes(),b'NEVER SELECTED')


if __name__ == '__main__': unittest.main()
