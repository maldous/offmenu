"""Finite root-sealed association tests; only temporary synthetic fixture bytes."""
import copy
import json
import unittest

import test_publisher_source_target as fixtures


class IntegrationAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PublisherSourceTargetTests(methodName='runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config=self.fixture.config;self.codec=self.fixture.codec
        s=self.config['snapshot'];b=self.config['binding'];p=b['source_projection']
        s['review']['evidence_source']=dict(path='/private/original-typed-review.json',sha256=p['review_sha256'])
        s['review']['qualification_source']=dict(path='/private/original-qualified-packet.json',sha256='d'*64)
        b['publication']['qualification_sha256']=self.codec._hash(self.codec._wire(s))
        self.config['integration_admission']=dict(version=1,kind='native-reviewed-integration-v1',
            binding_sha256=self.codec._hash(self.codec._wire(b)),unit_sha256=p['unit_sha256'],
            review_sha256=p['review_sha256'],permission_sha256='e'*64,automatic_integration_enabled=True)
        self.continuation=dict(version=1,operation_id=self.codec._hash(self.codec._wire(b)),
            unit_sha256=s['native_runtime']['unit_sha256'],packet_sha256=s['native_runtime']['packet_sha256'],
            claim_sha256='1'*64,previous_selection_sha256='2'*64,previous_record_sha256='3'*64,
            previous_capability=dict(version=1,closure_sha256='4'*64,host_confirmation_sha256='5'*64),
            receipts=[dict(invocation_id='12345678-1234-4234-8234-123456789abc',
                closure_sha256='4'*64,receipt_sha256='6'*64)])

    def qualify(self):
        raw=json.dumps(self.config).encode()
        return self.codec._config(raw,self.codec._hash(raw),self.fixture.pins,self.fixture.fixture.dependency_pins)

    def test_root_permission_and_continuation_do_not_change_original_snapshot_or_binding(self):
        before=copy.deepcopy(self.config)
        self.config['nativeContinuation']=self.continuation
        self.assertEqual(self.qualify(),self.config)
        self.assertEqual(self.config['snapshot'],before['snapshot'])
        self.assertEqual(self.config['binding'],before['binding'])
        del self.config['integration_admission']
        self.assertEqual(self.qualify(),self.config)  # continuity is not merge permission

    def test_permission_requires_original_typed_review_unit_and_binding(self):
        original=copy.deepcopy(self.config)
        for change in (
            lambda c:c['integration_admission'].update(automatic_integration_enabled=False),
            lambda c:c['integration_admission'].update(binding_sha256='0'*64),
            lambda c:c['integration_admission'].update(unit_sha256='0'*64),
            lambda c:c['integration_admission'].update(review_sha256=c['snapshot']['review']['qualification_source']['sha256']),
            lambda c:c['integration_admission'].update(permission_sha256='not-a-pin'),
            lambda c:c['integration_admission'].update(command='not-allowed')):
            with self.subTest(change=change):
                self.config=copy.deepcopy(original);change(self.config)
                with self.assertRaises(self.codec.InstallError):self.qualify()

    def test_continuation_is_finite_exact_and_cannot_rebind_or_add_a_new_closure(self):
        for change in (
            lambda a:a.update(operation_id='0'*64),lambda a:a.update(packet_sha256='0'*64),
            lambda a:a.update(receipts=[]),lambda a:a['receipts'].append(copy.deepcopy(a['receipts'][0])),
            lambda a:a['receipts'][0].update(invocation_id='not-canonical'),
            lambda a:a['previous_capability'].update(version=True),
            lambda a:a.update(new_closure_sha256='0'*64)):
            with self.subTest(change=change):
                a=copy.deepcopy(self.continuation);change(a);self.config['nativeContinuation']=a
                with self.assertRaises(self.codec.InstallError):self.qualify()

    def test_unprojected_native_origin_requires_exact_original_receipt_review_and_source(self):
        c=self.config;b=c['binding'];s=c['snapshot'];n=s['native_runtime']
        del b['source_projection'];b['base']=n['source']['base']
        del c['codePins']['src/offmenu/delivery/identity_source_projection.py']
        del self.fixture.pins['src/offmenu/delivery/identity_source_projection.py']
        n['source']['policy_sha256']='f'*64  # Native source/release policy is a separate domain.
        r=s['review'];r.update(outputs=b['outputs'],author=b['owner'],reviewer='independent-reviewer',
            model='unknown',provider='unknown',requested_model='unknown',requested_provider='unknown',
            resolved_model=None,resolution_status='unknown')
        r['evidence_sha256']=self.codec._hash(self.codec._wire(r))
        s['native_receipt_source']=dict(path='/private/original/attempts/UIF-102/receipt.json',sha256='1'*64)
        s['validation_receipt_source']=dict(path='/private/original/validation-receipt.json',sha256='2'*64)
        b['publication']['qualification_sha256']=self.codec._hash(self.codec._wire(s))
        a=c['integration_admission'];a.update(kind='native-source-reviewed-integration-v1',
            binding_sha256=self.codec._hash(self.codec._wire(b)),native_origin=dict(version=1,kind='native-v1',
            profile='enrichment-resilience-focused',source_sha256=self.codec._hash(self.codec._wire(n['source'])),
            packet_sha256=n['packet_sha256'],validation_operation_key=b['validation_operation_key'],outputs=b['outputs'],
            native_receipt=s['native_receipt_source'],validation_receipt=s['validation_receipt_source']))
        self.assertEqual(self.qualify(),c)
        original=copy.deepcopy(c)
        for change in (
            lambda c:c['integration_admission']['native_origin'].update(profile='identity-client-focused'),
            lambda c:c['integration_admission'].update(kind='native-reviewed-integration-v1'),
            lambda c:c['integration_admission']['native_origin'].update(packet_sha256='0'*64),
            lambda c:c['integration_admission']['native_origin'].update(source_sha256='0'*64),
            lambda c:c['integration_admission']['native_origin'].update(native_receipt=dict(path='/other.json',sha256='0'*64)),
            lambda c:c['snapshot']['review'].update(evidence_sha256='0'*64),
            lambda c:c['snapshot']['native_runtime']['source'].update(base='0'*40),
            lambda c:c['integration_admission'].update(permission_sha256='not-a-pin')):
            self.config=copy.deepcopy(original);change(self.config)
            with self.subTest(change=change):
                with self.assertRaises(self.codec.InstallError):self.qualify()


if __name__=='__main__':unittest.main()
