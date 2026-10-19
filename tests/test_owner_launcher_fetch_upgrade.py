"""Offline exact 5e7f stage-launcher upgrades; no collection or source requests."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_owner_launcher as fixture
m=fixture.m

class FetchUpgradeTests(unittest.TestCase):
    setUp=fixture.LauncherTests.setUp
    tearDown=fixture.LauncherTests.tearDown
    installed_layout=fixture.LauncherTests.installed_layout

    def prior(self):
        root, old=self.installed_layout(m.FETCH_PARSE_PREDECESSOR['commit'])
        (old/'preserved').write_bytes(b'old source remains')
        (root/'pins'/(old.name+'.json')).write_text(json.dumps(m.FETCH_PARSE_PREDECESSOR))
        (root/'run').write_bytes(m.run_alias_bytes(root))
        for stage in ('fetch','parse'):
            (root/stage).write_bytes(m.stage_wrapper_bytes(old,stage))
        return root,old

    def test_immutable_baseline_identity_and_all_prior_maps_preserved(self):
        self.assertEqual(m.FETCH_PARSE_PREDECESSOR,{'commit':'5e7f4673e78b1f677c69a1ed48a36d24e2692a90','tree':'370ba0ac4422abcc5fdd8ae3519b7767117cc6d6'})
        self.assertEqual(m.FETCH_PARSE_PREDECESSOR_FILES['scripts/run-global-on-foo.py'],'46679de850ff85b9b258d6b10a8bb142b38a8e95d3286c322be7cca4929eb7fd')
        self.assertEqual(len(m.FETCH_PARSE_PREDECESSOR_FILES),132)
        for name in ('PREDECESSOR_FILES','VERSIONED_PREDECESSOR_FILES','COMPREHENSIVE_PREDECESSOR_FILES'):
            self.assertTrue(getattr(m,name))

    def test_exact_upgrade_preserves_source_pin_alias_and_manual_only(self):
        root,old=self.prior(); _,new=self.installed_layout()
        pin=root/'pins'/(old.name+'.json'); before=pin.read_bytes(); alias=(root/'run').read_bytes()
        with patch.object(m,'verify_source') as verify,patch.object(m,'git',side_effect=AssertionError('network forbidden')),patch.object(m.os,'execvpe',side_effect=AssertionError('execution forbidden')),redirect_stdout(io.StringIO()):
            m.install('a'*40,'b'*40)
        self.assertEqual(verify.call_args_list[0].args,(old,m.FETCH_PARSE_PREDECESSOR,m.clean_environment(),m.FETCH_PARSE_PREDECESSOR_FILES))
        self.assertEqual(verify.call_args_list[1].args[0],new)
        self.assertEqual(pin.read_bytes(),before);self.assertEqual((root/'run').read_bytes(),alias)
        self.assertEqual((old/'preserved').read_bytes(),b'old source remains')
        for stage in ('fetch','parse'):
            self.assertEqual((root/stage).read_bytes(),m.stage_wrapper_bytes(new,stage))
            self.assertEqual((root/stage).stat().st_mode&0o777,0o700)

    def test_partial_old_new_stage_combinations_retry(self):
        for retained in ('fetch','parse'):
            with self.subTest(retained=retained):
                root,old=self.prior();_,new=self.installed_layout()
                switched='parse' if retained=='fetch' else 'fetch'
                (root/switched).write_bytes(m.stage_wrapper_bytes(new,switched))
                with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):m.install('a'*40,'b'*40)
                self.assertEqual(verify.call_args_list[0].args[0],old)
                for stage in ('fetch','parse'):self.assertEqual((root/stage).read_bytes(),m.stage_wrapper_bytes(new,stage))

    def test_actual_interruption_then_retry(self):
        root,old=self.prior();_,new=self.installed_layout();replace=os.replace
        def interrupt(src,dst):
            if Path(dst)==root/'parse':raise OSError('synthetic interruption')
            return replace(src,dst)
        with patch.object(m,'verify_source'),patch.object(m.os,'replace',side_effect=interrupt),self.assertRaises(OSError):m.install('a'*40,'b'*40)
        self.assertEqual((root/'fetch').read_bytes(),m.stage_wrapper_bytes(new,'fetch'))
        self.assertEqual((root/'parse').read_bytes(),m.stage_wrapper_bytes(old,'parse'))
        with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):m.install('a'*40,'b'*40)
        self.assertEqual(verify.call_args_list[0].args[0],old)
        self.assertEqual((root/'parse').read_bytes(),m.stage_wrapper_bytes(new,'parse'))

    def test_changed_pin_stops_before_verification_fetch_or_pointer_write(self):
        root,old=self.prior();before={s:(root/s).read_bytes() for s in ('run','fetch','parse')}
        (root/'pins'/(old.name+'.json')).write_text(json.dumps(dict(m.FETCH_PARSE_PREDECESSOR,tree='f'*40)))
        with patch.object(m,'verify_source') as verify,patch.object(m,'git',side_effect=AssertionError('network forbidden')),self.assertRaisesRegex(ValueError,'unknown-install-predecessor'):m.install('a'*40,'b'*40)
        verify.assert_not_called()
        for s,b in before.items():self.assertEqual((root/s).read_bytes(),b)

    def test_real_verifier_rejects_old_commit_tree_dirty_and_file_tampering(self):
        root,old=self.prior();before={s:(root/s).read_bytes() for s in ('run','fetch','parse')}
        # Real verify_source exercises git identity, clean status and full file pins.
        cases=((['0'*40], 'source-pin-mismatch'),([old.name,'0'*40], 'source-pin-mismatch'),([old.name,m.FETCH_PARSE_PREDECESSOR['tree'],' M changed'], 'source-checkout-changed'))
        for replies,error in cases:
            with self.subTest(error=error,replies=replies),patch.object(m,'git',side_effect=replies),self.assertRaisesRegex(ValueError,error):m.install('a'*40,'b'*40)
        first=next(iter(m.FETCH_PARSE_PREDECESSOR_FILES));file=old/first;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'tampered')
        with patch.object(m,'git',side_effect=[old.name,m.FETCH_PARSE_PREDECESSOR['tree'],'']),self.assertRaisesRegex(ValueError,'source-file-pin-mismatch'):m.install('a'*40,'b'*40)
        for s,b in before.items():self.assertEqual((root/s).read_bytes(),b)

    def test_exact_whole_inventory_stage_predecessor_checks_immutable_git_identity(self):
        root,old=self.installed_layout(m.WHOLE_INVENTORY_PREDECESSOR['commit'])
        pin=root/'pins'/(old.name+'.json');pin.write_text(json.dumps(m.WHOLE_INVENTORY_PREDECESSOR))
        for stage in ('fetch','parse'):(root/stage).write_bytes(m.stage_wrapper_bytes(old,stage))
        _,new=self.installed_layout()
        with patch.object(m,'verify_source_identity') as verify_identity,patch.object(m,'verify_source') as verify_source,patch.object(m,'git',side_effect=AssertionError('network forbidden')),redirect_stdout(io.StringIO()):
            m.install('a'*40,'b'*40)
        verify_identity.assert_called_once_with(old,m.WHOLE_INVENTORY_PREDECESSOR,m.clean_environment())
        verify_source.assert_called_once_with(new,{'commit':'a'*40,'tree':'b'*40},m.clean_environment())
        for stage in ('fetch','parse'):self.assertEqual((root/stage).read_bytes(),m.stage_wrapper_bytes(new,stage))

    def test_changed_whole_inventory_stage_pin_stops_before_identity_check(self):
        root,old=self.installed_layout(m.WHOLE_INVENTORY_PREDECESSOR['commit'])
        (root/'pins'/(old.name+'.json')).write_text(json.dumps(dict(m.WHOLE_INVENTORY_PREDECESSOR,tree='f'*40)))
        (root/'fetch').write_bytes(m.stage_wrapper_bytes(old,'fetch'))
        _,new=self.installed_layout()
        before=(root/'fetch').read_bytes()
        with patch.object(m,'verify_source_identity') as verify_identity,patch.object(m,'git',side_effect=AssertionError('network forbidden')),self.assertRaisesRegex(ValueError,'unknown-install-predecessor'):
            m.install('a'*40,'b'*40)
        verify_identity.assert_not_called()
        self.assertEqual((root/'fetch').read_bytes(),before)

    def test_unknown_old_stage_target_is_rejected(self):
        root,old=self.prior();(root/'parse').write_bytes(m.stage_wrapper_bytes(root/'sources'/('f'*40),'parse'))
        with patch.object(m,'verify_source') as verify,patch.object(m,'git',side_effect=AssertionError('network forbidden')),self.assertRaisesRegex(ValueError,'unknown-install-stage-wrapper'):m.install('a'*40,'b'*40)
        verify.assert_not_called()

if __name__=='__main__':unittest.main()
