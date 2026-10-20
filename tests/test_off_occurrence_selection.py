"""Fixed real selection without original IO; persistence uses generated data."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import off_occurrence_selection as s
from offmenu.refresh import off_partition_custody as c
from offmenu.refresh.core import RefreshError
import test_off_partition_custody as fixtures


class OccurrenceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parent_fd = os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self.addCleanup(os.close,self.parent_fd)
        self.target = self.target_named('custody-success.json')
        self.cached_receipt = None

    def target_named(self,name):
        fd = os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.parent_fd)
        self.addCleanup(os.close,fd)
        inode = lambda f:(os.fstat(f).st_dev,os.fstat(f).st_ino)
        return s.ReceiptTarget(fd,self.parent_fd,name,inode(fd),inode(self.parent_fd))

    def receipt(self):
        if self.cached_receipt is None:
            fixture = fixtures.PartitionCustodyTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
            self.cached_receipt = fixture.run_operation(fixture.bind())
        return self.cached_receipt

    def test_fixed_factory_performs_no_io_and_cannot_load_or_override_json(self):
        with patch.object(os,'open',side_effect=AssertionError('no IO')), \
             patch.object(os,'stat',side_effect=AssertionError('no IO')):
            operation = s.prepared_off_operation(); limits = s.prepared_off_limits()
        c._validate(operation,limits)
        self.assertEqual(operation.original.path,'off-2026-10-12.jsonl.gz')
        self.assertEqual(operation.original.bytes,13132516914)
        self.assertEqual(operation.expected_rows,4807663)
        self.assertEqual(operation.scope_id,'full-retained-occurrence-partition-v1')
        self.assertEqual(operation.permitted_operations,frozenset(('retain','parse','transform')))
        self.assertFalse(operation.fixture); self.assertEqual(operation.holds,())
        self.assertFalse(hasattr(operation,'expected_ids_sha256'))
        with self.assertRaises(TypeError): s.prepared_off_operation(expected_rows=4807217)
        with self.assertRaises(TypeError): s.prepared_off_operation({'accepted':True})

    def test_finite_caps_cover_full_denominator_without_inventing_fit_or_memberships(self):
        limits = s.prepared_off_limits()
        self.assertEqual(limits.max_input_bytes,13132516914)
        self.assertEqual(limits.partition.max_rows,s.prepared_off_operation().expected_rows)
        self.assertEqual(limits.partition.max_expanded_bytes,83278049962)
        self.assertEqual(limits.partition.max_database_bytes,8*s.GIB)
        self.assertGreater(limits.partition.max_output_bytes,3452950507)
        self.assertLess(limits.partition.max_seconds,limits.max_seconds)
        self.assertEqual(limits.partition.max_database_bytes+limits.partition.max_output_bytes+
                         s.SIDECAR_TEMP_BYTES+s.RECEIPT_BYTES+s.CONTROL_BYTES,13*s.GIB+2*1024**2)

    def test_selected_implementation_pins_match_accepted_source_observations(self):
        op = s.prepared_off_operation()
        observed = [hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in (c.__file__,c.partition_core.__file__,c.original_protocol.__file__)]
        self.assertEqual(observed,[op.implementation.adapter_sha256,
            op.implementation.partition_core_sha256,op.implementation.original_protocol_sha256])
        self.assertEqual(set(s.BASIS_SHA256),{9937,10481,10498,10450,10464})

    def test_direct_generated_success_is_fsynced_read_back_and_caller_handles_remain_open(self):
        self.assertTrue(s.check_receipt_target(self.target)['emptyTargetVerified'])
        receipt = self.receipt(); real = os.fsync
        with patch.object(os,'fsync',wraps=real) as fsync:
            observation = s.retain_success_receipt(self.target,receipt)
        self.assertEqual([call.args[0] for call in fsync.call_args_list],
                         [self.target.file_fd,self.target.parent_fd])
        raw = (self.root/self.target.name).read_bytes(); payload = json.loads(raw)
        self.assertEqual(observation['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(observation['bytes'],len(raw)); self.assertTrue(observation['readbackVerified'])
        self.assertTrue(observation['fileAndDirectoryFsyncCompleted'])
        self.assertFalse(observation['accepted']); self.assertTrue(observation['pointInTimeOnly'])
        self.assertFalse(payload['accepted']); self.assertTrue(payload['adapterReceipt']['fixture'])
        self.assertFalse(payload['adapterReceipt']['durableCustodyReceiptPublished'])
        os.fstat(self.target.file_fd); os.fstat(self.target.parent_fd)

    def test_nonempty_or_reused_receipt_target_is_not_overwritten(self):
        os.write(self.target.file_fd,b'KEEP'); os.lseek(self.target.file_fd,0,os.SEEK_SET)
        with self.assertRaises(RefreshError): s.retain_success_receipt(self.target,self.receipt())
        self.assertEqual((self.root/self.target.name).read_bytes(),b'KEEP')

    def test_wrong_name_identity_symlink_and_hardlink_refuse_before_writing(self):
        for target in (replace(self.target,file_identity=(0,0)),
                       replace(self.target,parent_identity=(0,0)),replace(self.target,name='../escape')):
            with self.assertRaises(RefreshError): s.check_receipt_target(target)
        (self.root/'symlink').symlink_to(self.root/self.target.name)
        with self.assertRaises(RefreshError): s.check_receipt_target(replace(self.target,name='symlink'))
        os.link(self.root/self.target.name,self.root/'hardlink')
        with self.assertRaises(RefreshError): s.check_receipt_target(self.target)
        self.assertEqual(os.fstat(self.target.file_fd).st_size,0)
        with self.assertRaises(RefreshError) as failure:
            s.retain_success_receipt(replace(self.target,file_fd='invalid'),self.receipt())
        self.assertIsNone(failure.exception.partition_receipt_retained_state['file'])

    def test_source_custody_failure_or_promoted_flags_cannot_be_retained_as_direct_success(self):
        receipt = self.receipt()
        for bad in ({},dict(receipt,accepted=True),dict(receipt,fullGzipCRCAndEOF=False),
                    dict(receipt,originalFileCustodyVerified=False),dict(receipt,runtimeQualified=True)):
            with self.assertRaisesRegex(RefreshError,'direct-success-required'):
                s.retain_success_receipt(self.target,bad)
            self.assertEqual(os.fstat(self.target.file_fd).st_size,0)

    def test_receipt_cap_fails_before_any_write(self):
        oversized = dict(self.receipt(),extra='x'*s.RECEIPT_BYTES)
        with self.assertRaisesRegex(RefreshError,'byte-bound'):
            s.retain_success_receipt(self.target,oversized)
        self.assertEqual(os.fstat(self.target.file_fd).st_size,0)

    def test_short_writes_are_completed_without_reopening_a_path(self):
        real = os.write
        with patch.object(os,'write',side_effect=lambda fd,raw:real(fd,raw[:37])):
            observation = s.retain_success_receipt(self.target,self.receipt())
        self.assertEqual(observation['bytes'],(self.root/self.target.name).stat().st_size)

    def test_write_failure_preserves_partial_file_and_refuses_automatic_resume(self):
        receipt = self.receipt(); real = os.write; calls = []
        def fail(fd,raw):
            if calls: raise OSError('generated disk failure')
            calls.append(fd); return real(fd,raw[:17])
        with patch.object(os,'write',side_effect=fail):
            with self.assertRaisesRegex(OSError,'generated disk failure') as failure:
                s.retain_success_receipt(self.target,receipt)
        state = failure.exception.partition_receipt_retained_state
        self.assertFalse(state['retentionCompleted']); self.assertFalse(state['automaticDeletion'])
        self.assertEqual(state['file']['bytes'],17)
        self.assertEqual((self.root/self.target.name).stat().st_size,17)
        with self.assertRaises(RefreshError): s.check_receipt_target(self.target)

    def test_file_or_directory_fsync_failure_never_returns_retention_success(self):
        receipt = self.receipt(); real = os.fsync
        for i,failed_fd in enumerate((self.target.file_fd,self.target.parent_fd)):
            target = self.target if i == 0 else self.target_named('second.json')
            def fail(fd):
                if fd == failed_fd: raise OSError('generated fsync failure')
                return real(fd)
            with patch.object(os,'fsync',side_effect=fail):
                with self.assertRaisesRegex(OSError,'generated fsync failure') as failure:
                    s.retain_success_receipt(target,receipt)
            self.assertFalse(failure.exception.partition_receipt_retained_state['retentionCompleted'])
            self.assertGreater(os.fstat(target.file_fd).st_size,0)

    def test_name_swap_after_write_preserves_replacement_and_relocated_receipt(self):
        receipt = self.receipt(); real = os.fsync; swapped = []
        def swap(fd):
            real(fd)
            if fd == self.target.file_fd and not swapped:
                os.rename(self.target.name,'held-receipt',src_dir_fd=self.parent_fd,dst_dir_fd=self.parent_fd)
                replacement = os.open(self.target.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=self.parent_fd)
                os.write(replacement,b'KEEP'); os.close(replacement); swapped.append(True)
        with patch.object(os,'fsync',side_effect=swap):
            with self.assertRaises(RefreshError) as failure:
                s.retain_success_receipt(self.target,receipt)
        self.assertEqual((self.root/self.target.name).read_bytes(),b'KEEP')
        self.assertTrue((self.root/'held-receipt').read_bytes().endswith(b'\n'))
        self.assertEqual(failure.exception.partition_receipt_retained_state['file']['location'],str(self.root/'held-receipt'))

    def test_readback_mutation_is_detected_without_rollback(self):
        receipt = self.receipt(); real = os.pread
        def mutate(fd,size,offset):
            data = real(fd,size,offset); os.pwrite(fd,b'!',0); return data
        with patch.object(os,'pread',side_effect=mutate):
            with self.assertRaisesRegex(RefreshError,'readback-mismatch'):
                s.retain_success_receipt(self.target,receipt)
        self.assertEqual((self.root/self.target.name).read_bytes()[:1],b'!')

    def test_retention_never_opens_replaces_or_deletes_names(self):
        receipt = self.receipt()
        with patch.object(os,'open',side_effect=AssertionError('no reopen')), \
             patch.object(os,'rename',side_effect=AssertionError('no rename')), \
             patch.object(os,'replace',side_effect=AssertionError('no replace')), \
             patch.object(os,'unlink',side_effect=AssertionError('no delete')), \
             patch.object(os,'rmdir',side_effect=AssertionError('no delete')):
            self.assertTrue(s.retain_success_receipt(self.target,receipt)['readbackVerified'])

    @unittest.skipUnless(hasattr(os,'O_PATH'),'Linux O_PATH descriptor required')
    def test_initial_opath_parent_rejected_before_source_access(self):
        fd = os.open(self.root,os.O_PATH|os.O_DIRECTORY); self.addCleanup(os.close,fd)
        target = replace(self.target,parent_fd=fd); source_access = []
        with self.assertRaises(OSError):
            s.check_receipt_target(target)
            source_access.append('SIMULATED_SOURCE_ACCESS_MUST_NOT_START')
        self.assertEqual(source_access,[])
        self.assertEqual(os.fstat(target.file_fd).st_size,0)

    def test_initial_valid_parent_is_fsynced_before_source_access(self):
        real = os.fsync; events = []
        def fsync(fd):
            events.append(('fsync',fd)); return real(fd)
        with patch.object(os,'fsync',side_effect=fsync):
            observation = s.check_receipt_target(self.target)
            events.append(('source-access','SIMULATED_ONLY'))
        self.assertEqual(events,[('fsync',self.target.parent_fd),('source-access','SIMULATED_ONLY')])
        self.assertTrue(observation['parentFsyncCompleted'])
        self.assertTrue(observation['emptyTargetVerified'])


if __name__ == '__main__': unittest.main()
