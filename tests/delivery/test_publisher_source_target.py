"""Synthetic protected DATA associations only; no installed publisher or effects."""
import copy
import json
import unittest

import native_publisher_invocation as invocation
import test_protected_publisher_install as fixtures


class PublisherSourceTargetTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.InstallTests(methodName='runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.codec=fixtures.p
        self.config=copy.deepcopy(self.fixture.config)
        b=self.config['binding'];s=self.config['snapshot'];original_base=b['base']
        self.projection=dict(version=1,profile='identity-client-focused',
            source=dict(head=b['head'],base=original_base,tree=b['tree'],branch=b['head_branch']),
            target=dict(base='5'*40,tree='6'*40),merge_tree='7'*40,outputs=b['outputs'],
            unit_sha256='8'*64,operation_key=b['validation_operation_key'],
            receipt=dict(path='/private/original.json',sha256='9'*64),review_sha256='a'*64)
        b['source_projection']=self.projection;b['base']=self.projection['target']['base']
        s['native_runtime']=dict(issue_id=b['issue_id'],project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',
            owner=b['owner'],unit_sha256=self.projection['unit_sha256'],packet_sha256='b'*64,
            source=dict(repository=b['repository'],branch=b['head_branch'],base=original_base,
                head=b['head'],tree=b['tree'],target='develop',policy_sha256=b['policy_sha256']))
        helper='src/offmenu/delivery/identity_source_projection.py'
        self.pins=dict(self.fixture.source_pins);self.pins[helper]='c'*64
        self.config['codePins'][helper]=self.pins[helper]
        b['publication']['qualification_sha256']=self.codec._hash(self.codec._wire(s))

    def qualify(self):
        raw=json.dumps(self.config).encode()
        return self.codec._config(raw,self.codec._hash(raw),self.pins,self.fixture.dependency_pins)

    def request(self):
        n=self.config['snapshot']['native_runtime'];b=self.config['binding']
        return dict(version=1,mode='step',operation_id=invocation.fingerprint(b),
            issue_id=n['issue_id'],project_id=n['project_id'],owner=n['owner'],
            unit_sha256=n['unit_sha256'],packet_sha256=n['packet_sha256'],
            source_sha256=invocation.fingerprint(n['source']))

    def test_protected_codec_and_fixed_helper_keep_original_source_and_new_api_target(self):
        before=copy.deepcopy(self.config['snapshot'])
        self.assertEqual(self.qualify(),self.config)
        self.assertEqual(invocation.association(self.config,self.request()),'integration')
        self.assertEqual(self.config['snapshot'],before)
        commit=self.config['plan']['operations'][0]
        self.assertEqual(commit['body']['parents'],[self.projection['source']['base']])
        self.assertNotEqual(commit['body']['parents'],[self.config['binding']['base']])

    def test_projection_mismatches_cannot_rebind_native_unit_or_original_parent(self):
        original=copy.deepcopy(self.config)
        for change in (
            lambda c:c['snapshot']['native_runtime']['source'].update(base=c['binding']['base']),
            lambda c:c['binding']['source_projection'].update(unit_sha256='0'*64),
            lambda c:c['binding']['source_projection'].update(profile='other'),
            lambda c:c['binding']['source_projection']['source'].update(head='0'*40)):
            with self.subTest(change=change):
                self.config=copy.deepcopy(original);change(self.config)
                with self.assertRaises(invocation.InvocationHold):
                    invocation.association(self.config,self.request())
                with self.assertRaises(self.codec.InstallError):self.qualify()

    def test_projected_config_requires_existing_source_pin_rule_for_lazy_helper(self):
        del self.config['codePins']['src/offmenu/delivery/identity_source_projection.py']
        with self.assertRaises(self.codec.InstallError):self.qualify()
        with self.assertRaises(invocation.InvocationHold):invocation.association(self.config,self.request())

    def test_projected_prepare_captures_the_same_pinned_lazy_helper(self):
        helper='src/offmenu/delivery/identity_source_projection.py'
        raw=b'synthetic trusted helper source; never imported\n'
        self.fixture.put(self.codec.SOURCE+'/'+helper,raw)
        self.pins[helper]=self.config['codePins'][helper]=self.codec._hash(raw)
        config=json.dumps(self.config).encode()
        prepared=self.codec.prepare(config,config_sha256=self.codec._hash(config),
            source_pins=self.pins,dependency_pins=self.fixture.dependency_pins,_host=self.fixture.host)
        self.assertEqual(json.loads(prepared)['files'][helper]['sha256'],self.pins[helper])

    def test_unprojected_current_target_cannot_relabel_original_parent_or_native_source(self):
        del self.config['binding']['source_projection']
        with self.assertRaises(invocation.InvocationHold):invocation.association(self.config,self.request())
        with self.assertRaises(self.codec.InstallError):self.qualify()


if __name__=='__main__':unittest.main()
