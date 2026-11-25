"""Owner-contained private references; fixtures do not grant production authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import native_harness_package as pkg


class LocalOwnerComposition(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.paths = {}
        self.pins = {}
        for role in ('owner_current', 'owner_catalog', 'publisher_config'):
            member = self.root / role
            raw = ('fixture-private:' + role).encode()
            member.write_bytes(raw)
            self.paths[role] = str(member)
            self.pins[role] = pkg.sha(raw)
        self.acceptance = pkg.PackageAcceptance(
            'fixture-owner', 'a' * 40, 'b' * 40,
            {'path': 'package-review.json', 'sha256': 'c' * 64})
        self.stage = self.root / 'stage'
        self.result = {
            'path': 'fixture-private-stage',
            'sha256': 'd' * 64,
            'roles': {role: {'fixture-private-name': role} for role in pkg.ROLES},
        }

    def call(self, **settings):
        opts = dict(config_files=self.paths, config_pins=self.pins,
                    acceptance=self.acceptance, head=self.acceptance.head,
                    tree=self.acceptance.tree)
        opts.update(settings)
        return pkg.prepare_owner_local_package(self.stage, **opts)

    def test_private_inputs_fixed_projection(self):
        with patch.object(pkg.os, 'getuid', return_value=1000), \
             patch.object(pkg.os, 'geteuid', return_value=1000), \
             patch.object(pkg, 'prepare_coherent_package', return_value=self.result) as produce:
            receipt = self.call()
        self.assertEqual(set(receipt), {'schema', 'head', 'tree', 'package_sha256', 'role_sha256'})
        self.assertEqual(receipt['package_sha256'], 'd' * 64)
        self.assertEqual(set(receipt['role_sha256']), set(pkg.ROLES))
        self.assertEqual(receipt['role_sha256']['publisher'], pkg.sha(pkg.protected.encoded(
            self.result['roles']['publisher'])))
        self.assertNotIn('fixture-private', repr(receipt))
        produce.assert_called_once()
        self.assertIs(produce.call_args.kwargs['acceptance'], self.acceptance)
        self.assertEqual(produce.call_args.kwargs['publisher_config'],
                         b'fixture-private:publisher_config')

    def test_root_and_source_mismatch_refuse_before_input_read(self):
        with patch.object(pkg.os, 'getuid', return_value=0), \
             patch.object(pkg, 'nofollow') as read:
            with self.assertRaises((ValueError, RuntimeError)):
                self.call()
            read.assert_not_called()
        with patch.object(pkg.os, 'getuid', return_value=1000), \
             patch.object(pkg.os, 'geteuid', return_value=1000), \
             patch.object(pkg, 'nofollow') as read:
            with self.assertRaises((ValueError, RuntimeError)):
                self.call(head='e' * 40)
            read.assert_not_called()

    def test_unauthorized_digest_or_link_do_not_stage(self):
        with patch.object(pkg.os, 'getuid', return_value=1000), \
             patch.object(pkg.os, 'geteuid', return_value=1000), \
             patch.object(pkg, 'prepare_coherent_package') as produce:
            with self.assertRaises((ValueError, RuntimeError)):
                self.call(config_pins=dict(self.pins, owner_current='e' * 64))
            target = Path(self.paths['publisher_config'])
            victim = self.root / 'private-other'
            target.rename(victim)
            target.symlink_to(victim)
            with self.assertRaisesRegex(ValueError, 'local_config_input_unavailable:publisher_config'):
                self.call()
            produce.assert_not_called()
        self.assertFalse(self.stage.exists())


if __name__ == '__main__':
    unittest.main()
