"""Detached real OpenSSH ingress tests with no host mutations."""

from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import native_harness_package as package
import native_harness_upgrade as upgrade
import offmenu_native_upgrade_ingress as ingress


class IngressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keydir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.keydir.cleanup)
        cls.key = Path(cls.keydir.name) / 'fixture'
        subprocess.run(['/usr/bin/ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                        '-f', str(cls.key)], check=True)
        cls.public = cls.key.with_suffix('.pub').read_bytes()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.operation = '1' * 64
        self.release = '2' * 64
        self.packet = self.root / self.operation
        self.packet.mkdir()
        (self.packet / 'package').mkdir()
        self.signers = self.root / 'allowed_signers'
        self.signers.write_bytes(b'owner-fixture ' + self.public)
        self.fields = dict(schema='offmenu.native-package-review/1', owner='owner-fixture',
                           head='3' * 40, tree='4' * 40, author='author-fixture',
                           reviewer='reviewer-fixture', verdict='accept')
        self.operation_record = dict(operation_id=self.operation, new={'publisher': {}},
                                     old={'publisher': {}}, legacy_receipts={})
        self.q = object()
        self.locks = 'fixture locks'
        self.publisher = 'fixture publisher'
        self.stage_lock = False
        self.staged = False
        self.observations = []
        self.files = {
            'package-review.json': ingress.encode(self.fields),
            'preflight.json': ingress.encode({'fixture': True}),
            'upgrade.json': ingress.encode(self.operation_record),
            'custody.json': ingress.encode({'fixture': True}),
        }
        for name, raw in self.files.items():
            (self.packet / name).write_bytes(raw)
        time_now = int(time.time())
        self.request = dict(schema='offmenu.foo-native-upgrade/1', action='replace',
                            repository=ingress.REPOSITORY, unit=ingress.SERVICE, target=ingress.TARGET,
                            owner='owner-fixture', operation_id=self.operation, package_sha256='5' * 64,
                            release_sha256=self.release, inputs={k: ingress.sha(v) for k, v in self.files.items()},
                            issued_at=time_now - 1, expires_at=time_now + 120)
        fixture = self

        class Host:
            @contextmanager
            def locks(self, custody):
                assert custody == fixture.locks and not fixture.stage_lock
                fixture.stage_lock = True
                self._lock_custody = custody
                try:
                    yield
                finally:
                    fixture.stage_lock = False

            @contextmanager
            def publisher_config(self, custody):
                assert custody == fixture.publisher and fixture.stage_lock
                yield

            def verify_locks(self):
                assert fixture.stage_lock

            def verify_publisher_custody(self):
                assert fixture.stage_lock

            def path(self, value):
                return fixture.root / Path(value).name

            def verify_role(self, role, path, closure):
                assert fixture.stage_lock
                fixture.observations.append((role, path, closure))

        self.package = SimpleNamespace(
            PackageAcceptance=package.PackageAcceptance, MaterializeAdmission=package.MaterializeAdmission,
            read_package=Mock(return_value=(dict(owner=self.fields['owner'], head=self.fields['head'],
                tree=self.fields['tree'], review={'path': 'package-review.json',
                'sha256': self.request['inputs']['package-review.json']},
                roles=self.operation_record['new']), {})),
            materialize=Mock(side_effect=self.materialize))
        self.upgrade = SimpleNamespace(
            **{k: getattr(upgrade, k) for k in ('STATE', 'OwnerAdmission', 'upgrade_digest')},
            Host=Host, asdict=lambda val: {'fixture_type': val}, TARGETS=('publisher',),
            qualify=Mock(return_value={'fixture': True}), qualify_lock_custody=Mock(),
            qualify_publisher_custody=Mock(), qualify_public_ca_pins=Mock(),
            locations=Mock(return_value=(ingress.TARGET, '/opt/stage', '/opt/backup')),
            stopped=Mock(side_effect=lambda *_: self.assertTrue(self.stage_lock)),
            execute=Mock(side_effect=self.execute))
        # Only host custody and the effect backend are fixture seams. Exact
        # request parsing, OpenSSH verification, durable receipt and entry
        # dispatch run through the maintained ingress.
        stack = [
            patch.object(ingress, 'STATE', self.root),
            patch.object(ingress, 'SIGNERS', self.signers),
            patch.object(ingress, 'protected_open', lambda path: path.open('rb')),
            patch.object(ingress, 'protected_dirs'),
            patch.object(ingress, 'pwd', SimpleNamespace(getpwnam=lambda _: SimpleNamespace(pw_uid=1000))),
            patch.object(ingress, 'custody_inputs', return_value=(self.q, self.locks, self.publisher, None)),
        ]
        for p in stack:
            p.start()
            self.addCleanup(p.stop)

    def sign(self, namespace=ingress.NAMESPACE):
        request = self.packet / 'request.json'
        request.write_bytes(ingress.encode(self.request))
        signature = self.packet / 'request.json.sig'
        signature.unlink(missing_ok=True)
        subprocess.run(['/usr/bin/ssh-keygen', '-Y', 'sign', '-f', str(self.key),
                        '-n', namespace, str(request)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)

    def materialize(self, stage, *, expected_sha256, admission):
        self.assertTrue(self.stage_lock)
        self.assertTrue((self.packet / 'ingress-intent.json').is_file())
        self.assertEqual(stage, self.packet / 'package')
        self.assertEqual((admission.owner, admission.operation_id, admission.package_sha256),
                         ('owner-fixture', self.operation, expected_sha256))
        self.staged = True

    def execute(self, plan, selection, *, admission, quiescence, lock_custody,
                publisher_config_custody, public_ca_pins, host):
        self.assertTrue(self.staged)
        with host.locks(lock_custody):
            self.assertEqual(selection['operation_id'], self.operation)
            self.assertEqual(admission.plan_sha256, ingress.sha(plan))
            self.assertEqual(admission.host_confirmation_sha256,
                             ingress.sha((self.packet / 'request.json').read_bytes()))
            self.assertIs(quiescence, self.q)
            self.assertIsNone(public_ca_pins)

    def invoke(self, action='replace'):
        return ingress.run(action, self.operation, self.release, self.package, self.upgrade)

    def test_signed_fixed_operation_reuses_existing_locks_and_recovers_one_result(self):
        self.sign()
        self.assertEqual(self.invoke('status')['state'], 'not_started')
        result = self.invoke()
        self.assertEqual(result['state'], 'installed')
        self.assertEqual(self.invoke('status'), result)
        self.assertEqual(self.invoke(), result)
        self.assertEqual(len(self.observations), 1)
        self.package.materialize.assert_called_once()
        self.upgrade.execute.assert_called_once()

    def test_interruption_retains_original_and_refuses_retry(self):
        self.sign()
        self.upgrade.execute.side_effect = OSError('fixture interruption')
        with self.assertRaises(OSError):
            self.invoke()
        self.assertEqual(self.invoke('status')['state'], 'reconcile')
        with self.assertRaisesRegex(ValueError, 'original_requires_reconciliation'):
            self.invoke()
        self.package.materialize.assert_called_once()
        self.upgrade.execute.assert_called_once()

    def test_wrong_signature_namespace_and_absent_enrollment_refuse(self):
        self.sign('wrong-purpose')
        with self.assertRaisesRegex(ValueError, 'owner_signature_refused'):
            self.invoke()
        self.signers.unlink()
        with self.assertRaises(FileNotFoundError):
            self.invoke()
        self.package.materialize.assert_not_called()

    def test_expired_confirmation_and_tampered_inputs_refuse(self):
        self.request['expires_at'] = self.request['issued_at'] + 1
        self.sign()
        with self.assertRaisesRegex(ValueError, 'owner_confirmation_expired'):
            self.invoke()
        self.request['expires_at'] += 120
        self.sign()
        (self.packet / 'custody.json').write_text('{}', encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'signed_inputs_changed'):
            self.invoke()
        self.package.materialize.assert_not_called()

    def test_failed_stopped_witness_does_not_consume_the_original(self):
        self.sign()
        self.upgrade.stopped.side_effect = ValueError('fixture unit still active')
        with self.assertRaisesRegex(ValueError, 'unit still active'):
            self.invoke()
        self.assertEqual(self.invoke('status')['state'], 'not_started')
        self.package.materialize.assert_not_called()
        self.upgrade.execute.assert_not_called()

    def test_fixed_target_and_wrong_release_refuse(self):
        self.request['target'] = '/opt/other'
        self.sign()
        with self.assertRaisesRegex(ValueError, 'fixed_scope_refused'):
            self.invoke()
        self.request['target'] = ingress.TARGET
        self.request['release_sha256'] = '6' * 64
        self.sign()
        with self.assertRaisesRegex(ValueError, 'reviewed_release_mismatch'):
            self.invoke()
        self.package.materialize.assert_not_called()

    def test_nonindependent_review_and_cross_operation_refuse(self):
        self.fields['reviewer'] = self.fields['author']
        changed = ingress.encode(self.fields)
        (self.packet / 'package-review.json').write_bytes(changed)
        self.request['inputs']['package-review.json'] = ingress.sha(changed)
        self.sign()
        with self.assertRaisesRegex(ValueError, 'independent_review_required'):
            self.invoke()
        (self.packet / 'package-review.json').write_bytes(self.files['package-review.json'])
        self.request['inputs']['package-review.json'] = ingress.sha(self.files['package-review.json'])
        self.operation_record['operation_id'] = '7' * 64
        changed = ingress.encode(self.operation_record)
        (self.packet / 'upgrade.json').write_bytes(changed)
        self.request['inputs']['upgrade.json'] = ingress.sha(changed)
        self.sign()
        with self.assertRaisesRegex(ValueError, 'reviewed_closure_mismatch'):
            self.invoke()
        self.package.materialize.assert_not_called()
