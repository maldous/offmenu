"""Detached state-preserving production-protocol tests, no real host effects."""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import test_native_harness_upgrade as fixtures
import native_harness_adoption as adoption
from native_harness_contract import fingerprint
import native_harness_upgrade as u

p = u.protected


class RuntimeUpgrade(unittest.TestCase):
    def setUp(self):
        self.f = f = fixtures.UpgradeTests()
        self.addCleanup(f.doCleanups)
        f.setUp()
        head = ('1' * 40, 'b' * 40)
        self.old_policy, self.new_policy = b'{"ceiling":4}\n', b'{"ceiling":8}\n'
        catalog = b'{"entries":[],"version":1}\n'
        python = b'detached interpreter fixture, never executed'
        cfg = dict(owner='root-owner', runtime_root=f.runtime_root,
            catalog='/etc/offmenu-stokowski-current/catalog.json', grants={'preserve': [1,2]},
            workflow_sha256='1'*64, installation_sha256='2'*64)
        self.before,self.after = tuple(p.encoded(dict(cfg, source_head=pin, policy_sha256=p.sha(policy)))
            for pin,policy in zip(head,(self.old_policy,self.new_policy)))
        self.state = dict(owner='root-owner', config_sha256=p.sha(self.before),
             bindings={'a': {'id': 'retained'}}, tasks={'task': {'state':'held','attempts':['original'],
              'historical_policy_sha256':p.sha(self.old_policy)}}, unknown={'nested':[True,None]})
        self.old_state = p.encoded(self.state)
        self.new_state = p.encoded(dict(self.state, config_sha256=p.sha(self.after)))
        self.runtime = f.root / f.runtime[1:]

        def write(path, raw, mode=0o444):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(mode)

        for side,config in enumerate((self.before,self.after)):
            owner = f.root / u.locations('owner_config',f.operation)[side][1:]
            deps = f.root / u.locations('owner_venv',f.operation)[side][1:]
            write(owner/'current.json', config)
            write(owner/'catalog.json', catalog)
            write(owner/'binding.json', p.encoded(dict(schema='protected-current-owner-v1',
                   runtime=f.runtime, source_root=u.TARGETS['owner_source'],
                   config_sha256=p.sha(config),catalog_sha256=p.sha(catalog),python_sha256=p.sha(python))))
            write(deps/'bin/python', python,0o555)
        source = f.root/u.locations('owner_source', f.operation)[1][1:]
        write(source/'tools/delivery/capacity-policy.json', self.new_policy)
        write(self.runtime/'capacity-policy.json',self.old_policy,0o600)
        write(self.runtime/'current-owner.json',self.old_state,0o600)
        for role in ('owner_config','owner_source','owner_venv'):
            stage = f.root/u.locations(role, f.operation)[1][1:]
            f.manifest['new'][role] = fixtures.closure(stage)

        target = f.source.request['target']
        target['config'] = f.source.write(p.encoded(f.manifest['new']['owner_config']))
        target['dependencies'] = f.source.write(p.encoded(f.manifest['new']['owner_venv']))
        f.source.request['readback'].update(closure_sha256=fingerprint(target),
            config_sha256=target['config']['sha256'], dependencies_sha256=target['dependencies']['sha256'])
        f.plan = adoption.prepare(f.source.request,f.source.policy,
             evidence_root=f.source.root,accepted=f.source.accepted)
        f.manifest['preflight_sha256'] = p.sha(f.plan)
        f.manifest['runtime_transition'] = dict(
              old_config_sha256=p.sha(self.before),new_config_sha256=p.sha(self.after),
              old_policy_sha256=p.sha(self.old_policy),new_policy_sha256=p.sha(self.new_policy),
              old_state_sha256=p.sha(self.old_state),new_state_sha256=p.sha(self.new_state))
        f.admission = replace(f.admission,plan_sha256=p.sha(f.plan),
                              upgrade_sha256=u.upgrade_digest(f.manifest))

    def observation(self):
        return u.observe(self.f.manifest,host=self.f.host,publisher_config_custody=self.f.pub_custody)

    def cutover(self):
        f=self.f
        receipt=f.root / f'{u.STATE[1:]}/native-upgrade-{f.operation}.installed.json'
        return receipt

    def test_runtime_name_changed_during_guard_refuses_before_exchange(self):
        f = self.f
        path = self.runtime/'capacity-policy.json'
        original_exchange = u.exchange_runtime
        def race(host,fd,operation,name,old,new,metadata,guard):
            def mutate():
                guard()
                alias=self.runtime/'changed-by-fixture'
                alias.write_bytes(self.old_policy+b' ')
                alias.chmod(0o600)
                alias.replace(path)
            return original_exchange(host,fd,operation,name,old,new,metadata,mutate)
        with patch.object(u,'exchange_runtime',side_effect=race):
            with self.assertRaisesRegex(ValueError,'runtime_exact_image'):
                f.execute()
        self.assertEqual(path.read_bytes(),self.old_policy+b' ')
        self.assertEqual((self.runtime/u.runtime_side(f.operation,'capacity-policy.json')).read_bytes(),self.new_policy)
        self.assertFalse(self.observation()['installed_verified'])

    def test_exact_cutover_and_future_active_state(self):
        old_interpreter = self.f.root/u.locations('owner_venv',self.f.operation)[0][1:]/'bin/python'
        old_interpreter.chmod(0o755)  # Old venv is retained opaque, not read or run.
        result=self.f.execute()
        self.assertTrue(result['installed_verified'])
        self.assertEqual((self.runtime/'current-owner.json').read_bytes(),self.new_state)
        self.assertEqual((self.runtime/u.runtime_side(self.f.operation,'current-owner.json')).read_bytes(),self.old_state)
        self.assertEqual((self.runtime/u.runtime_side(self.f.operation,'capacity-policy.json')).read_bytes(),self.old_policy)
        self.assertTrue(self.observation()['runtime_transition']['canonical_cutover_receipt_verified'])
        (self.runtime/'current-owner.json').write_bytes(p.encoded(dict(
            p.record(self.new_state), legitimate_progress=True)))
        self.f.host.state = dict(ActiveState='active',SubState='running',MainPID='1')
        self.assertTrue(u.verify_active(self.f.manifest,host=self.f.host,
                       publisher_config_custody=self.f.pub_custody)['active_observed'])
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.f.execute()

    def test_tampered_old_state_refuses_before_intent(self):
        (self.runtime/'current-owner.json').write_bytes(self.old_state + b' ')
        with self.assertRaisesRegex(ValueError,'runtime_transition_saved_state'):
            self.f.execute()
        self.assertFalse(self.cutover().exists())
        self.assertFalse(self.observation()['intent_verified'])

    def test_interruption_before_any_runtime_exchange(self):
        with patch.object(u,'exchange_runtime',side_effect=OSError('before effect')):
            with self.assertRaisesRegex(OSError,'before effect'):
                self.f.execute()
        self.assertEqual(self.observation()['runtime_transition']['files'],
                         dict.fromkeys(u.RUNTIME_FILES,'not-applied'))
        self.assertFalse(self.observation()['installed_verified'])
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.f.execute()

    def test_interruption_after_policy_only(self):
        original=u.exchange_runtime
        def stop(*args, **kwargs):
            if args[3]=='current-owner.json':
                raise OSError('after policy')
            return original(*args,**kwargs)
        with patch.object(u,'exchange_runtime',side_effect=stop):
            with self.assertRaisesRegex(OSError,'after policy'):
                self.f.execute()
        result=self.observation()
        self.assertEqual(result['runtime_transition']['files'],
                         {'capacity-policy.json':'applied','current-owner.json':'not-applied'})
        self.assertFalse(result['installed_verified'])
        self.assertFalse(self.cutover().exists())
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.f.execute()

    def test_both_exchanged_without_receipt_is_not_success(self):
        original=self.f.host.create
        def stop(path,value):
            if path.endswith('.installed.json'):
                raise OSError('before receipt')
            return original(path,value)
        with patch.object(self.f.host,'create',side_effect=stop):
            with self.assertRaisesRegex(OSError,'before receipt'):
                self.f.execute()
        result=self.observation()
        self.assertEqual(result['runtime_transition']['files'],dict.fromkeys(u.RUNTIME_FILES,'applied'))
        self.assertFalse(result['installed_verified'])
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.f.execute()

    def test_lost_acknowledgement_after_receipt(self):
        original=self.f.host.create
        def stop(path,value):
            result=original(path,value)
            if path.endswith('.installed.json'):
                raise OSError('lost acknowledgement')
            return result
        with patch.object(self.f.host,'create',side_effect=stop):
            with self.assertRaisesRegex(OSError,'lost acknowledgement'):
                self.f.execute()
        self.assertTrue(self.observation()['installed_verified'])
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.f.execute()
