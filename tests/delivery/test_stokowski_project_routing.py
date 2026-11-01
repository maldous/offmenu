"""Finite sealed project routing using pinned native Stokowski, no live effects."""
import asyncio
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

import test_stokowski_current_dispatch as fixtures
import test_stokowski_replacement as replacement_fixtures
import protected_owner_install as ingress
import stokowski_adapter as adapter
from symphony_capacity import AdmissionError
from symphony_tasks import project_route

OFFMENU = project_route(adapter.PROJECT)
UIF = project_route('ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0')


class ProjectRoutingTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.CurrentDispatchTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def seal(self, grants=None, primary=OFFMENU):
        f = self.f
        config = copy.deepcopy(f.current.config)
        config.pop('normal_intake', None)
        config.update(project_route=primary, project_routes=grants or [
            dict(OFFMENU, normal_intake=None), dict(UIF, normal_intake=None)])
        sealed = f.root/'sealed-project-current.json'
        f.write(sealed, config)
        state = copy.deepcopy(f.current.state)
        state['config_sha256'] = adapter.file_sha(sealed)
        f.write(f.current.state_path, state)
        f.stack.enter_context(patch.object(adapter, 'current_config', side_effect=lambda r:
            (adapter.read_record(sealed), sealed, {'synthetic': 'root seal; no host changes'})))
        f.stack.enter_context(patch.object(adapter, 'PROTECTED_OWNER', f.root))
        f.stack.enter_context(patch.object(adapter, 'protected_owner_bytes', side_effect=lambda p: Path(p).read_bytes()))
        f.current = adapter.CurrentWork(f.runtime)
        return sealed

    def qualify(self, number, route):
        f = self.f
        issue, runtime = f.qualify(number)
        manifest = adapter.read_record(runtime/'manifest.json')
        manifest['project_id'] = route['project_id']
        f.write(runtime/'manifest.json', manifest)
        admission = adapter.read_record(runtime/'current-admission.json')
        admission['manifest_sha256'] = adapter.file_sha(runtime/'manifest.json')
        f.write(runtime/'current-admission.json', admission)
        entry = f.entries[-1]
        entry['admission_sha256'] = adapter.file_sha(runtime/'current-admission.json')
        for field in ('bindings', 'references', 'tasks'):
            f.current.state[field].pop(issue.identifier, None)
        f.publish()
        return issue, runtime

    def test_native_fetches_both_exact_projects_with_isolated_async_routes(self):
        """Run the actual upstream fetch/parser for each slug, not a fake fetch."""
        from stokowski.linear import LinearClient, CANDIDATE_QUERY
        a, _ = self.qualify(117, OFFMENU)
        b, _ = self.qualify(119, UIF)
        self.seal()
        f = self.f
        actual_fetch = LinearClient.fetch_candidate_issues
        _, linear, _ = f.adapted()
        # Restore real upstream behind the reviewed adapter wrapper.
        # adapted() captured a mock, so install once more after restoring it.
        linear.LinearClient.fetch_candidate_issues = actual_fetch
        adapter.install_adapters(f.runtime, None, 'synthetic-memory-only', f.current)
        observed = []
        async def graphql(query, variables):
            await asyncio.sleep(0)  # force interleaving at the project boundary
            observed.append((query, dict(variables)))
            if query == CANDIDATE_QUERY:
                issue = {OFFMENU['project_slug']: a, UIF['project_slug']: b}[variables['projectSlug']]
                return {'issues': {'nodes': [dict(id=issue.id, identifier=issue.identifier,
                    title=issue.title, state={'name': 'Todo'})], 'pageInfo': {'hasNextPage': False}}}
            issue = {a.id: (a, OFFMENU), b.id: (b, UIF)}[variables['id']]
            return {'issue': dict(id=issue[0].id, identifier=issue[0].identifier,
                project={'id': issue[1]['project_id']}, state={'name': 'Todo'})}
        client = LinearClient(endpoint='https://example.invalid/graphql', api_key='synthetic')
        async def run():
            with patch.object(client, '_graphql', side_effect=graphql):
                values = await asyncio.gather(*(client.fetch_candidate_issues(r['project_slug'], ['Todo'])
                    for r in (OFFMENU, UIF)))
                with self.assertRaisesRegex(AdmissionError, 'Wrong Linear project'):
                    await client.fetch_candidate_issues('unadmitted-cix', ['Todo'])
            await client.close()
            return values
        selected = asyncio.run(run())
        self.assertEqual([[i.identifier for i in group] for group in selected], [[a.identifier], [b.identifier]])
        fetches = [v for q, v in observed if q == CANDIDATE_QUERY]
        self.assertEqual({v['projectSlug'] for v in fetches}, {OFFMENU['project_slug'], UIF['project_slug']})
        self.assertTrue(all(v['states'] == ['Todo', 'In Progress'] for v in fetches))
        self.assertEqual(f.current.route, OFFMENU)
        self.assertEqual(f.current.config['owner'], 'existing-owner')

    def test_default_stays_single_route_and_unsealed_multi_route_refuses(self):
        f = self.f
        self.assertEqual(f.current.routes, [OFFMENU])
        config = dict(f.current.config, project_routes=[dict(OFFMENU, normal_intake=None), dict(UIF, normal_intake=None)])
        f.write(f.runtime/'current.json', config)
        with self.assertRaisesRegex(AdmissionError, 'current_project_routes_grant'):
            adapter.CurrentWork(f.runtime)

    def test_ingress_and_constructor_refuse_broad_or_ambiguous_routes(self):
        f = self.f
        self.seal()
        base = copy.deepcopy(f.current.config)
        ingress.validate_config(base, f.runtime)
        for grants in (None, [], [dict(OFFMENU, normal_intake=None)] * 2,
            [dict(UIF, project_slug=OFFMENU['project_slug'], normal_intake=None)],
            [dict(project_id='00000000-0000-4000-8000-000000000001', project_slug='foreign', normal_intake=None)],
            [dict(OFFMENU, normal_intake={'path': '/tmp/outside.json', 'sha256': 'a'*64})],
            [dict(OFFMENU, normal_intake=None, enabled=True)]):
            with self.subTest(grants=grants):
                bad = dict(base, project_routes=grants)
                with self.assertRaises((ingress.Refused, AdmissionError, FileNotFoundError)):
                    ingress.validate_config(bad, f.runtime)
                current = object.__new__(adapter.CurrentWork)
                current.config, current.root, current.owner_custody = bad, f.root, {'synthetic': True}
                with self.assertRaises((AdmissionError, FileNotFoundError)):
                    current._project_routes_config()
        for bad in (dict(base, normal_intake={'path': 'ambiguous'}),
                    dict(base, project_routes=[dict(UIF, normal_intake=None)])):
            with self.assertRaises(ingress.Refused):
                ingress.validate_config(bad, f.runtime)

    def test_wrong_project_uuid_and_scope_do_not_cross_intake_authority(self):
        f = self.f
        issue, client, authority, _ = f.intake_fixture()
        off_policy = copy.deepcopy(f.current._intake_policy())
        off_ref = f.current.config['normal_intake']
        uif_authority = dict(authority, issue='UIF-342', issue_id='00000000-0000-4000-8000-000000000342',
                             project_id=UIF['project_id'])
        uif_path = f.root/'uif-authority.json'
        f.write(uif_path, uif_authority)
        policy = dict(off_policy, project_route=UIF, references={'owner/finite-341': {
            'path': str(uif_path), 'sha256': adapter.file_sha(uif_path)}})
        uif_policy_path = f.root/'uif-policy.json'
        f.write(uif_policy_path, policy)
        self.seal([dict(OFFMENU, normal_intake=off_ref), dict(UIF, normal_intake={
            'path': str(uif_policy_path), 'sha256': adapter.file_sha(uif_policy_path)})])
        self.assertEqual(f.current._intake_authority('owner/finite-341', OFFMENU)[1], authority)
        self.assertEqual(f.current._intake_authority('owner/finite-341', UIF)[1], uif_authority)
        boundary = Mock()
        with patch.object(f.current, '_qualification_boundary', boundary):
            asyncio.run(f.current._intake(client, issue, OFFMENU))
            self.assertEqual(boundary.call_count, 1)
            boundary.reset_mock()
            asyncio.run(f.current._intake(client, issue, UIF))
            boundary.assert_not_called()
            remote = client._graphql.return_value['issue']
            remote['id'] = '00000000-0000-4000-8000-000000000999'
            asyncio.run(f.current._intake(client, issue, OFFMENU))
            boundary.assert_not_called()
            remote['id'] = issue.id
            remote['inverseRelations']['nodes'] = [dict(type='blocks', issue=dict(id='blocked', state={'name': 'In Progress'}))]
            asyncio.run(f.current._intake(client, issue, OFFMENU))
            boundary.assert_not_called()
            self.assertIn('dependency_drift', f.current.state['intake'][issue.identifier]['reason'])
            # A fresh root pin does not make an empty accepted scope valid.
            remote['inverseRelations']['nodes'] = []
            f.write(uif_path, dict(uif_authority, accepted_scope=[]))
            policy['references']['owner/finite-341']['sha256'] = adapter.file_sha(uif_path)
            f.write(uif_policy_path, policy)
            f.current.config['project_routes'][1]['normal_intake']['sha256'] = adapter.file_sha(uif_policy_path)
            with self.assertRaisesRegex(AdmissionError, 'intake_owner_scope_or_decision'):
                f.current._intake_authority('owner/finite-341', UIF)

    def test_secondary_project_handoff_checks_its_exact_scope_and_source(self):
        import time
        f = self.f
        issue, _, authority, _ = f.intake_fixture(decision='owner-qualified')
        policy = f.current._intake_policy()
        authority = dict(authority, project_id=UIF['project_id'],
            handoff={'path': str(f.root/'handoff.json'), 'sha256': 'f'*64})
        f.write(f.root/'intake-authority.json', authority)
        policy.update(project_route=UIF)
        policy['references']['owner/finite-341']['sha256'] = adapter.file_sha(f.root/'intake-authority.json')
        f.write(f.root/'intake-policy.json', policy)
        ref = dict(path=str(f.root/'intake-policy.json'), sha256=adapter.file_sha(f.root/'intake-policy.json'))
        self.seal([dict(OFFMENU, normal_intake=None), dict(UIF, normal_intake=ref)])
        f.current.state['intake'] = {issue.identifier: dict(status='qualified',
            handoff=authority['handoff'], reference='owner/finite-341', authority=authority, checked_at=time.time())}
        packet = dict(execution_outcome=dict(identifier=issue.identifier, uuid=issue.id, project_id=UIF['project_id']),
            scope=authority['accepted_scope'], acceptance=authority['acceptance'], source={'base': authority['source_head']})
        self.assertTrue(f.current._trusted_handoff(authority['handoff'], packet))
        self.assertFalse(f.current._trusted_handoff(authority['handoff'], dict(packet, scope=['unaccepted.py'])))
        self.assertFalse(f.current._trusted_handoff(authority['handoff'], dict(packet, source={'base': 'f'*40})))

    def test_successor_crosses_admitted_projects_preserving_original_trigger(self):
        f = self.f
        publication, issue, original, _, _, review, _, _ = f.successor_fixture()
        before = {p: p.read_bytes() for p in original.rglob('*') if p.is_file()}
        f.current.state.pop('successor_request')
        publication.manifest['tasks']['UIF-106'] = publication.manifest['tasks'].pop('UIF-231')
        publication.bind_successor(f.current, review, outcome=fixtures.CurrentDispatchTests.UIF119)
        import hashlib
        import stokowski_prepare as prepare
        after = adapter.read_record(f.catalog)
        after['entries'].append(f.current._successor_entry(publication.packet))
        f.current.config['catalog_versions'] = [dict(catalog=after,
            sha256=hashlib.sha256(prepare._publication_bytes(after)).hexdigest())]
        f.write(f.root/'binding.json', {'runtime': str(f.runtime)})
        self.seal()
        protected = f.root/'protected-projects'
        protected.mkdir()
        (protected/'catalog.json').write_bytes(f.catalog.read_bytes())
        f.write(protected/'binding.json', {'runtime': str(f.runtime)})
        f.stack.enter_context(patch.object(adapter, 'PROTECTED_OWNER', protected))
        self.assertEqual(f.current.state['successor_request']['status'], 'pending')
        self.assertEqual(publication.publish()['status'], 'published')
        f.current.refresh()
        self.assertEqual(f.current.gate_binding(issue)['project_id'], OFFMENU['project_id'])
        self.assertEqual(adapter.read_record(publication.runtime/'manifest.json')['project_id'], UIF['project_id'])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        publication.provider.assert_called_once()

    def multi_workflow(self):
        f = self.f
        workflow = json.loads((f.runtime/'workflow.yaml').read_text())
        project = {k: workflow.pop(k) for k in ('tracker', 'workspace', 'hooks', 'prompts', 'states') if k in workflow}
        workflow['projects'] = []
        for name, route in [('offmenu', OFFMENU), ('uif', UIF)]:
            selected = copy.deepcopy(project)
            selected.update(name=name)
            selected['tracker']['project_slug'] = route['project_slug']
            workflow['projects'].append(selected)
        f.write(f.runtime/'workflow.yaml', workflow)
        return workflow

    def test_native_workflow_one_pool_global_ceiling_and_all_project_guards(self):
        from stokowski.config import parse_workflow_file, validate_config
        import stokowski.orchestrator as native
        f = self.f
        self.multi_workflow()
        def validate():
            config = parse_workflow_file(f.runtime/'workflow.yaml').config
            adapter.validate_project_workflow(config, f.policy, [OFFMENU, UIF], validate_config(config))
            return config
        f.stack.enter_context(patch.dict('os.environ', OFFMENU_LINEAR_API_KEY='synthetic-memory-only'))
        config = validate()
        for mutate in (lambda c: setattr(c.projects[1].tracker, 'project_slug', 'cix'),
                       lambda c: setattr(c.projects[1].hooks, 'before_run', 'forbidden'),
                       lambda c: setattr(c.agent, 'max_concurrent_agents', 16)):
            c = copy.deepcopy(config)
            mutate(c)
            with self.assertRaisesRegex(AdmissionError, 'Workflow violates'):
                adapter.validate_project_workflow(c, f.policy, [OFFMENU, UIF], [])
        async def exercise():
            coordinator = native.MultiOrchestrator(f.runtime/'workflow.yaml')
            # Construct real per-project orchestrators; no polling or credentials.
            with patch.object(native.Orchestrator, 'start', new=AsyncMock()), \
                 patch.object(native.Orchestrator, 'stop', new=AsyncMock()):
                task = asyncio.create_task(coordinator.start())
                await asyncio.sleep(0)
                self.assertEqual(set(coordinator.orchestrators), {'offmenu', 'uif'})
                self.assertTrue(all(o.pool is coordinator.pool for o in coordinator.orchestrators.values()))
                self.assertEqual(coordinator.pool.global_cap, 8)
                for _ in range(8):
                    self.assertTrue(coordinator.pool.try_claim('offmenu'))
                self.assertFalse(coordinator.pool.try_claim('uif'))
                await coordinator.stop()
                await task
        with patch.dict('os.environ', OFFMENU_LINEAR_API_KEY='synthetic-memory-only'):
            asyncio.run(exercise())

    def test_two_project_ticks_serialize_shared_continuation_without_new_owner(self):
        import stokowski.orchestrator as native
        from types import SimpleNamespace
        f = self.f
        self.seal()
        active, peak = 0, 0
        async def continuation(*args, **kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
        with patch.object(native.Orchestrator, '_tick', new=AsyncMock()):
            installed, _, _ = f.adapted()
            with patch.object(f.current, 'continue_validation', side_effect=continuation), \
                 patch.object(f.current, 'continue_native_harness', new=AsyncMock()):
                async def ticks():
                    await asyncio.gather(*(installed.Orchestrator._tick(SimpleNamespace()) for _ in range(2)))
                asyncio.run(ticks())
        self.assertEqual(peak, 1)

    def test_run_entrypoint_fetches_every_admitted_native_project_once(self):
        from stokowski.linear import LinearClient
        import stokowski.orchestrator as native
        from contextlib import redirect_stdout
        import io
        f = self.f
        self.multi_workflow()
        f.current.config['workflow_sha256'] = adapter.file_sha(f.runtime/'workflow.yaml')
        self.seal()
        # Preserve and restore all adapter monkeypatches using the established fixture.
        f.adapted()
        fetch = AsyncMock(return_value=[])
        with patch.object(LinearClient, 'fetch_candidate_issues', new=fetch), \
             patch.object(adapter, 'credential', return_value='synthetic-memory-only'), \
             patch.object(native, 'MultiOrchestrator') as launch, redirect_stdout(io.StringIO()):
            asyncio.run(adapter.run(f.runtime, 1, dry_run=True, current_mode=True))
        self.assertEqual([call.args[1] for call in fetch.await_args_list],
                         [OFFMENU['project_slug'], UIF['project_slug']])
        launch.assert_not_called()
        self.assertEqual(adapter.read_record(f.runtime/'admission.json')['project_routes'], [OFFMENU, UIF])

    def test_original_offmenu_native_unit_remains_bound_under_uif_primary(self):
        f = self.f
        native = f.native_harness_fixture()
        self.seal(primary=UIF)
        before = {p: p.read_bytes() for p in native.runtime.rglob('*') if p.is_file()}
        asyncio.run(f.current.continue_native_harness(native.factory))
        native.step.assert_called_once()
        self.assertEqual(f.current.gate_binding(native.issue)['project_id'], OFFMENU['project_id'])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual(f.current.route, UIF)

    def test_admitted_project_cannot_relabel_original_native_unit(self):
        f = self.f
        native = f.native_harness_fixture()
        sealed = self.seal(primary=UIF)
        selection = adapter.read_record(native.selected)
        selection['binding']['project_id'] = UIF['project_id']
        f.write(native.selected, selection)
        config = adapter.read_record(sealed)
        config['native_harness_boundaries'][native.issue.identifier]['sha256'] = adapter.file_sha(native.selected)
        f.write(sealed, config)
        state = adapter.read_record(f.current.state_path)
        state['config_sha256'] = adapter.file_sha(sealed)
        f.write(f.current.state_path, state)
        f.current = adapter.CurrentWork(f.runtime)
        asyncio.run(f.current.continue_native_harness(native.factory))
        native.step.assert_not_called()
        self.assertEqual(f.current.state['tasks'][native.issue.identifier]['native_harness']['status'], 'held')

    def test_uif117_replacement_chain_retains_original_project_and_receipts(self):
        r = replacement_fixtures.ReplacementTests(methodName='runTest')
        r.setUp()
        self.addCleanup(r.doCleanups)
        current = r.current_fixture()
        current.config.update(project_route=OFFMENU, project_routes=[dict(OFFMENU, normal_intake=None), dict(UIF, normal_intake=None)])
        before = r.receipt_path.read_bytes()
        current.refresh()
        current.refresh()
        self.assertEqual(current.entries, {r.issue: r.next})
        self.assertEqual(len(current.state['replacement_history']), 1)
        history = current.state['replacement_history'][0]
        self.assertEqual(history['entry'], r.previous)
        self.assertEqual(history['refusal']['project_id'], UIF['project_id'])
        self.assertEqual(r.receipt_path.read_bytes(), before)
        manifest = adapter.read_record(Path(r.next['runtime'])/'manifest.json')
        self.assertEqual(manifest['project_id'], UIF['project_id'])
        with self.assertRaisesRegex(AdmissionError, 'replacement_new_identity'):
            current._replacement_witness(r.previous, r.next, manifest=dict(manifest, project_id=OFFMENU['project_id']), request_sha256='0'*64)


if __name__ == '__main__':
    unittest.main()
