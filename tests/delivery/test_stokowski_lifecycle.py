"""Pinned upstream adaptation checks, executed in the Stokowski environment."""
import asyncio
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_adapter as adapter
from stokowski_worker import MODEL


@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Use the pinned Stokowski environment')
class AdaptedLifecycleTests(unittest.TestCase):
    def adapted(self, runtime, stack, transition=None, manifest=None):
        import stokowski.config as config
        import stokowski.linear as linear
        import stokowski.orchestrator as orchestration
        import stokowski.workspace as workspace
        targets = [(config.ProjectConfig,'agent_env'),(config.ServiceConfig,'agent_env'),
                   (config.ProjectConfig,'resolved_api_key'),(config.ServiceConfig,'resolved_api_key'),
                   (linear.LinearClient,'fetch_candidate_issues'),(workspace,'run_hook')]
        targets += [(obj,name) for obj in (workspace,orchestration)
                    for name in ('ensure_workspace','remove_workspace')]
        targets += [(orchestration.Orchestrator,name) for name in
                    ('stop','start','_safe_transition','_publish_run_report')]
        targets += [(orchestration,'run_turn')]
        for owner,name in targets:
            stack.enter_context(patch.object(owner,name,getattr(owner,name)))
        if transition:
            stack.enter_context(patch.object(orchestration.Orchestrator,'_safe_transition',transition))
        return adapter.install_adapters(runtime,manifest or {'project_id':adapter.PROJECT,'tasks':{}},'coordinator-only-canary'),config

    def test_both_upstream_config_paths_keep_key_out_of_child_environment(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            _,config = self.adapted(Path(temp),stack)
            stack.enter_context(patch.dict(os.environ,{'LINEAR_API_KEY':'tracker-canary',
                                'CREDENTIALS_DIRECTORY':'/private/injected','OTHER_TOKEN':'secret-canary'}))
            project = config.ProjectConfig()
            for selected in (project,config.ServiceConfig(projects=[project])):
                self.assertEqual(selected.resolved_api_key(),'coordinator-only-canary')
                environment = selected.agent_env()
                for key in ('LINEAR_API_KEY','CREDENTIALS_DIRECTORY','OTHER_TOKEN'):
                    self.assertNotIn(key,environment)

    def test_failed_or_unenforced_shell_gate_is_rejected_before_spawn(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            runtime = Path(temp)
            # The real manifest reader precedes the hook guard. Supply its
            # admitted schema without bypassing that reader or invoking a worker.
            manifest = dict(version=1,branch='feature/test-lifecycle',base_revision='a'*40,
                project_id=adapter.PROJECT,label='offline-lifecycle',tasks={
                    'UIF-92':dict(issue_id='00000000-0000-4000-8000-000000000092',
                        owner='test-owner',purpose='Offline shell-hook refusal',
                        allowed_paths=['README.md'],acceptance=['Reject shell hooks before spawn'],
                        resources=dict(cpu_millis=1,memory_bytes=1024,io_slots=1,output_bytes=0),
                        attempt_limit=1)})
            manifest_path = runtime/'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            before = manifest_path.read_bytes()
            adapted,_ = self.adapted(runtime,stack,manifest=manifest)
            spawn = stack.enter_context(patch.object(adapter.asyncio,'create_subprocess_exec',new_callable=AsyncMock))
            with self.assertRaisesRegex(Exception,'Unenforced shell validation hook'):
                asyncio.run(adapted.run_turn('codex',SimpleNamespace(model=MODEL),
                    SimpleNamespace(after_run='exit 1'),'prompt',Path(temp),
                    SimpleNamespace(identifier='UIF-92'),SimpleNamespace()))
            spawn.assert_not_called()
            self.assertEqual(list(runtime.iterdir()),[manifest_path])
            self.assertEqual(manifest_path.read_bytes(),before)

    def test_stop_waits_for_inflight_transition_before_closing_tracker_client(self):
        async def scenario(runtime,stack):
            entered,release = asyncio.Event(),asyncio.Event()
            events = []
            async def transition(owner,*args):
                entered.set()
                await release.wait()
                events.append('transition-finished')
            adapted,_ = self.adapted(runtime,stack,transition)
            async def close():
                events.append('client-closed')
            owner = SimpleNamespace(_running=True,_stop_event=asyncio.Event(),
                                    _retry_timers={},_tasks={},_linear=SimpleNamespace(close=close))
            pending = asyncio.create_task(adapted.Orchestrator._safe_transition(owner,None,'complete'))
            await entered.wait()
            stopping = asyncio.create_task(adapted.Orchestrator.stop(owner))
            await asyncio.sleep(.02)
            self.assertNotIn('client-closed',events)
            release.set()
            await asyncio.gather(pending,stopping)
            self.assertEqual(events,['transition-finished','client-closed'])
            self.assertFalse(adapted._offmenu_pending_control)
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            asyncio.run(scenario(Path(temp),stack))


if __name__ == '__main__':
    unittest.main()
