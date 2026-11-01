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


if __name__=='__main__':unittest.main()
