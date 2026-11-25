"""Detached real OpenSSH ingress tests with no host mutations."""

from contextlib import contextmanager
from dataclasses import replace
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
        self.state = self.root / 'ingress'
        self.state.mkdir()
        self.fence = self.state / ingress.FENCE
        self.fence.mkdir()
        self.canonical_state = self.root / 'canonical'
        self.canonical_state.mkdir()
        self.packet = self.state / self.operation
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
                return fixture.canonical_state / Path(value).name

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
            **{k: getattr(upgrade, k) for k in ('OwnerAdmission', 'upgrade_digest')},
            STATE=str(self.canonical_state),
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
            patch.object(ingress, 'STATE', self.state),
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
            installed = self.canonical_state / f'native-upgrade-{self.operation}.installed.json'
            installed.write_bytes(ingress.encode(dict(kind='native-upgrade-installed-v1',
                upgrade_sha256=admission.upgrade_sha256, readback=dict(installed_verified=True,
                rollback_verified=True))))

    def invoke(self, action='replace'):
        return ingress.run(action, self.operation, self.release, self.package, self.upgrade)

    def runner_evidence(self):
        manifest = ingress.encode(dict(owner=self.fields['owner'], head=self.fields['head'],
            tree=self.fields['tree'], review={'path': 'package-review.json',
            'sha256': self.request['inputs']['package-review.json']}))
        (self.packet / 'package' / 'manifest.json').write_bytes(manifest)
        self.request['package_sha256'] = ingress.sha(manifest)
        raw = ingress.encode(self.request)
        (self.packet / 'request.json').write_bytes(raw)
        return ingress.VerifiedFooRun('foo', 'u/admin/foo_root_jobs',
            '79b70b57-12a2-4d09-946f-54d45910a65b', 'fixture-platform-actor',
            self.fields['owner'], self.operation, ingress.sha(raw), ingress.sha(manifest),
            self.release, self.fields['head'], self.fields['tree'],
            self.request['issued_at'], self.request['expires_at'])

    def runner_audit(self, authenticate=None):
        return ingress.audit_runner_request(self.operation, self.release,
                                            self.canonical_state, authenticate)

    def test_runner_audit_accepts_exact_verified_provenance_without_effect(self):
        attested = self.runner_evidence()
        result = self.runner_audit(lambda: attested)
        self.assertEqual(result['state'], 'not_started')
        self.assertTrue(result['runner_provenance_verified'])
        self.assertFalse(result['effect_authorized'])
        self.assertFalse((self.fence / self.operation).exists())
        self.package.materialize.assert_not_called()
        self.upgrade.execute.assert_not_called()

    def test_runner_audit_refuses_missing_untyped_wrong_and_expired_provenance(self):
        attested = self.runner_evidence()
        with self.assertRaisesRegex(ValueError, 'authenticated_runner_job_provenance_unavailable'):
            self.runner_audit()
        for claims, problem in [
            (vars(attested), 'authenticated_runner_job_provenance_required'),
            (replace(attested, runnable='u/admin/other'), 'runner_binding_mismatch'),
            (replace(attested, operation_id='8' * 64), 'runner_request_mismatch'),
            (replace(attested, expires_at=attested.issued_at), 'runner_attestation_window'),
            (replace(attested, source_tree='8' * 40), 'runner_source_review_binding'),
        ]:
            with self.subTest(problem=problem), self.assertRaisesRegex(ValueError, problem):
                self.runner_audit(lambda: claims)
        self.package.materialize.assert_not_called()
        self.upgrade.execute.assert_not_called()

    def test_runner_audit_preserves_uncertain_original_for_reconciliation(self):
        attested = self.runner_evidence()
        retained = dict(operation_id=self.operation, confirmation_sha256=attested.request_sha256)
        raw = ingress.encode(retained)
        fence = self.fence / self.operation
        fence.write_bytes(raw)
        result = self.runner_audit(lambda: attested)
        self.assertEqual(result['state'], 'reconcile')
        self.assertFalse(result['effect_authorized'])
        self.assertEqual(fence.read_bytes(), raw)
        self.assertFalse((self.packet / 'ingress-intent.json').exists())
        self.package.materialize.assert_not_called()
        self.upgrade.execute.assert_not_called()

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

    def test_interrupted_publisher_fences_a_different_signed_operation(self):
        self.sign()
        self.upgrade.execute.side_effect = OSError('fixture interruption')
        with self.assertRaises(OSError):
            self.invoke()
        first_fence = self.fence / self.operation
        first_intent = self.packet / 'ingress-intent.json'
        original_bytes = first_intent.read_bytes()
        self.assertEqual(self.invoke('status')['state'], 'reconcile')
        self.assertEqual(first_fence.read_bytes(), original_bytes)

        self.operation = '8' * 64
        self.packet = self.state / self.operation
        self.packet.mkdir()
        (self.packet / 'package').mkdir()
        later = dict(self.operation_record, operation_id=self.operation)
        for name, data in self.files.items():
            (self.packet / name).write_bytes(ingress.encode(later) if name == 'upgrade.json' else data)
        self.request['operation_id'] = self.operation
        self.request['inputs']['upgrade.json'] = ingress.sha(ingress.encode(later))
        self.sign()
        with self.assertRaisesRegex(ValueError, 'publisher_original_requires_reconciliation'):
            self.invoke()
        self.assertFalse((self.packet / 'ingress-intent.json').exists())
        self.assertFalse((self.fence / self.operation).exists())
        # A crash after the publisher intent, or loss of the per-operation
        # intent, still fences the later request from staging.
        first_intent.unlink()
        with self.assertRaisesRegex(ValueError, 'publisher_original_requires_reconciliation'):
            self.invoke()
        first_intent.write_bytes(original_bytes)
        first_fence.unlink()
        with self.assertRaisesRegex(ValueError, 'publisher_intent_missing'):
            self.invoke()
        self.package.materialize.assert_called_once()
        self.upgrade.execute.assert_called_once()
        self.assertEqual(first_intent.read_bytes(), original_bytes)

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
