"""Generated source fixtures/in-memory helper only; no Git, Foo or real DB writes."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_household_preparation as preparation
import plan_runner as runner


class HouseholdPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.configured_sources()

    def write(self, path, body):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    def configured_sources(self):
        sql = [b'-- Generated baseline schema only\n', b'-- Generated security schema only\n', b'-- Generated household schema only\n']
        for path, body in zip(preparation.SQL_PATHS, sql):
            self.write(path, body)
        self.sql_hashes = [hashlib.sha256(body).hexdigest() for body in sql]
        self.plan = {'schema': 'offmenu-household-schema-preparation-plan/1',
            'source_baseline': preparation.BASELINE, 'purpose': 'Generated schema fixture',
            'ordered_sql': [{'path': path, 'sha256': digest} for path, digest in zip(preparation.SQL_PATHS, self.sql_hashes)]}
        self.write(preparation.PLAN, json.dumps(self.plan).encode())
        self.helper_result = {'schema': 'offmenu-household-schema-readiness/1',
            'source_baseline': preparation.BASELINE, 'schema_status': 'schema_prepared_app_wiring_pending',
            'prepared_schema_version': 'offmenu-household-domain/1', 'security_schema_version': 'offmenu-byoc-security/1',
            'domain_table_count': 31, 'private_rows': 0, 'foreign_key_check': 'passed',
            'integrity_check': 'passed', 'sql_sha256': self.sql_hashes,
            **dict.fromkeys(preparation.FALSE_FIELDS, False)}
        self.write(preparation.HELPER, b'# Generated stdout fixture only\n')
        self.baseline = mock.patch.object(preparation, 'BASE_SQL_SHA256', self.sql_hashes[0])
        self.baseline.start()
        self.addCleanup(self.baseline.stop)

    def process(self, value=None, code=0):
        proc = mock.Mock(pid=123, returncode=code)
        proc.communicate.return_value = (json.dumps(self.helper_result if value is None else value).encode(), None)
        return proc

    def run_with(self, proc):
        with mock.patch.object(preparation.subprocess, 'Popen', return_value=proc) as launch:
            value = preparation.run_preparation(self.root)
        return value, launch

    def test_success_fixed_no_output_command_and_complete_source_binding(self):
        value, launch = self.run_with(self.process())
        self.assertEqual(value['status'], 'schema_prepared_app_wiring_pending')
        self.assertEqual(value['source_sha256']['sql'], self.sql_hashes)
        self.assertEqual(value['domain_table_count'], 31)
        self.assertFalse(value['deployment_performed'])
        command = launch.call_args.args[0]
        self.assertEqual(command, [sys.executable, '-I', '-B', str(self.root / preparation.HELPER)])
        self.assertNotIn('--output-dir', command)
        self.assertNotIn('shell', launch.call_args.kwargs)
        self.assertEqual(launch.call_args.kwargs['cwd'], self.root)
        self.assertEqual(launch.call_args.kwargs['env'], {})
        self.assertEqual(launch.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(launch.call_args.kwargs['stderr'], subprocess.DEVNULL)
        self.assertEqual(value, preparation.validate_preparation(copy.deepcopy(value)))
        self.assertNotIn(str(self.root), json.dumps(value))

    def test_missing_source_or_plan_mismatch_never_launches(self):
        (self.root / preparation.HELPER).unlink()
        with mock.patch.object(preparation.subprocess, 'Popen') as launch:
            result = preparation.run_preparation(self.root)
        launch.assert_not_called()
        self.assertEqual(result['status'], 'preparation_unavailable')
        self.assertEqual(result['reason'], 'sources_unavailable')
        self.write(preparation.HELPER, b'# Generated\n')
        self.plan['ordered_sql'][0]['path'] = '/private/not-authorized.sql'
        self.write(preparation.PLAN, json.dumps(self.plan).encode())
        with mock.patch.object(preparation.subprocess, 'Popen') as launch:
            result = preparation.run_preparation(self.root)
        launch.assert_not_called()
        self.assertEqual(result['reason'], 'dependency_mismatch')
        self.assertNotIn('/private', json.dumps(result))

    def test_unchanged_baseline_and_source_symlinks_are_enforced(self):
        with mock.patch.object(preparation, 'BASE_SQL_SHA256', 'f' * 64):
            result, launch = self.run_with(self.process())
        launch.assert_not_called()
        self.assertEqual(result['reason'], 'baseline_mismatch')
        (self.root / preparation.HELPER).unlink()
        (self.root / preparation.HELPER).symlink_to(self.root / preparation.PLAN)
        result, launch = self.run_with(self.process())
        launch.assert_not_called()
        self.assertEqual(result['reason'], 'unsafe_source')

    def test_timeout_kills_helper_and_is_finite_nonready(self):
        proc = self.process()
        proc.communicate.side_effect = [subprocess.TimeoutExpired('generated', 15), (b'', None)]
        with mock.patch.object(preparation.os, 'killpg') as kill:
            result, _ = self.run_with(proc)
        kill.assert_called_once_with(123, preparation.signal.SIGKILL)
        self.assertEqual(result['status'], 'preparation_failed')
        self.assertEqual(result['reason'], 'helper_timeout')
        self.assertIsNone(result['private_rows'])
        self.assertIsNone(result['domain_table_count'])

    def test_interrupt_propagates_even_if_cleanup_fails(self):
        proc = self.process()
        proc.communicate.side_effect = [KeyboardInterrupt(), OSError('Generated cleanup error')]
        with mock.patch.object(preparation.os, 'killpg') as kill, \
             mock.patch.object(preparation.subprocess, 'Popen', return_value=proc):
            with self.assertRaises(KeyboardInterrupt):
                preparation.run_preparation(self.root)
        kill.assert_called_once_with(123, preparation.signal.SIGKILL)

    def test_failed_and_unsafe_helper_outputs_do_not_leak_or_claim_preparation(self):
        result, _ = self.run_with(self.process({'private': '/not-public'}, code=1))
        self.assertEqual(result['reason'], 'helper_failed')
        for field, bad in (('artifact_written', True), ('private_rows', False),
                           ('deployment_performed', True), ('domain_table_count', 32),
                           ('sql_sha256', ['d' * 64] * 3), ('extra', '/not-public')):
            value = copy.deepcopy(self.helper_result)
            value[field] = bad
            result, _ = self.run_with(self.process(value))
            self.assertEqual(result['reason'], 'invalid_helper_result', field)
            self.assertNotIn('/not-public', json.dumps(result))
        proc = self.process()
        proc.communicate.return_value = (b'{"schema":1,"schema":2}', None)
        result, _ = self.run_with(proc)
        self.assertEqual(result['reason'], 'invalid_helper_result')

    def test_source_change_during_helper_invalidates_observation(self):
        proc = self.process()
        def changed(**kwargs):
            self.write(preparation.HELPER, b'# Different generated helper\n')
            return json.dumps(self.helper_result).encode(), None
        proc.communicate.side_effect = changed
        result, _ = self.run_with(proc)
        self.assertEqual(result['reason'], 'source_changed')
        self.assertEqual(result['status'], 'preparation_failed')

    def test_optional_companion_strict_and_old_canonical_bytes_unchanged(self):
        import ingest_evidence
        old = {'schema': 'offmenu-ingest-supplement/1', 'ingest_evidence': ingest_evidence.sanitize_evidence({})}
        raw = runner.canonical(old)
        runner.validate_supplement(old)
        self.assertEqual(runner.canonical(old), raw)
        result, _ = self.run_with(self.process())
        supplement = runner.build_supplement({'household_schema_preparation': result})
        runner.validate_supplement(supplement)
        for mutate in (lambda v: v.update(extra='/private'), lambda v: v.update(private_rows=False),
                       lambda v: v.update(application_wiring_verified=True),
                       lambda v: v['source_sha256'].update(extra='private')):
            bad = copy.deepcopy(supplement)
            mutate(bad['household_schema_preparation'])
            with self.assertRaises(runner.Stop):
                runner.validate_supplement(bad)

    def test_preparation_with_worst_finite_evidence_fits_existing_companion_limit(self):
        import ingest_evidence
        import ingest_relational_targets
        from test_ingest_evidence import EvidenceTests
        fixture = EvidenceTests('test_worst_finite_enum_supplement_is_bounded_without_count_loss')
        with mock.patch.object(ingest_evidence, 'validate_evidence', wraps=ingest_evidence.validate_evidence) as validate:
            fixture.test_worst_finite_enum_supplement_is_bounded_without_count_loss()
        evidence = validate.call_args.args[0]
        prepared, _ = self.run_with(self.process())
        supplement = {'schema': 'offmenu-ingest-supplement/1', 'ingest_evidence': evidence,
            'household_schema_preparation': prepared,
            'relational_targets': ingest_relational_targets.sanitize_relational_summary({})}
        runner.validate_supplement(supplement)
        self.assertLessEqual(len(runner.canonical(supplement)), 65536)

    def fixture_runner(self, preparation_result):
        instance = runner.Runner.__new__(runner.Runner)
        instance.root = self.root
        instance.state = self.root / 'state'
        instance.layout = runner.resolve_layout(instance.state / 'ingest')
        instance.receipt_transport = 'isolated-branch-v1'
        instance.preconditions = mock.Mock()
        instance.recovery_receipt = lambda: None
        instance.prepare_household_schema = mock.Mock(return_value=preparation_result)
        instance.materialize_ingest_receipt = mock.Mock()
        instance.materialize_ingest_receipts = mock.Mock()
        instance.git = mock.Mock(side_effect=AssertionError('Git is not authorized in this fixture'))
        self.write('run', b'# Generated run binding\n')
        self.write('manual-action/plan_runner.py', b'# Generated runner binding\n')
        self.write('manual-action/runner_paths.py', b'# Generated fixture layout binding\n')
        self.write('manual-action/ingest_household_preparation.py', b'# Generated helper binding\n')
        report = {'status': 'complete', 'domains': {}, 'pending_work': runner.unknown_pending_work()}
        for domain in runner.DOMAINS:
            report['domains'][domain] = {'status': 'schema_only' if domain in ('user_profiles','inventory') else 'complete'}
        def run(prepared, report_callback):
            report_callback(report)
            return report
        engine = types.SimpleNamespace(prepare_default=mock.Mock(return_value={'catalog_sha256': 'a' * 64}),
            pending_snapshot=mock.Mock(return_value=runner.unknown_pending_work()),
            completed_outputs_available=mock.Mock(return_value=False), run_prepared=mock.Mock(side_effect=run))
        instance.ingest_engine = lambda: engine
        plan = {'schema': 'offmenu-run-plan/2', 'receipt_transport': 'isolated-branch-v1', 'max_parallel': 2,
            'jobs': [{'id': 'retained-eight-domain-ingest', 'version': 2, 'operation': 'retained_ingest_all', 'depends_on': []}]}
        return instance, engine, plan

    def test_runner_orders_reconciliation_preparation_discovery_and_keeps_failure_nonblocking(self):
        failed = preparation.unavailable('sources_unavailable')
        instance, engine, plan = self.fixture_runner(failed)
        events = []
        instance.prepare_household_schema.side_effect = lambda: events.append('preparation') or failed
        engine.prepare_default.side_effect = lambda *args: events.append('discovery') or {'catalog_sha256': 'a' * 64}
        instance.recovery_receipt = lambda: events.append('reconciliation') or None
        old_report = {'domains': {domain: {'status': 'schema_only'} for domain in runner.DOMAINS}}
        old_receipt = {'schema': 'offmenu-run-receipt/2', 'job_id': plan['jobs'][0]['id'],
            'job_version': 2, 'operation': 'retained_ingest_all', 'job_key': 'b' * 64,
            'implementation_sha256': 'c' * 64, 'input_sha256': 'd' * 64,
            'observed_at': '2026-10-22T00:00:00Z', 'outcome': 'running',
            'ingest': instance.ingest_summary(old_report)}
        old_raw = runner.canonical(old_receipt)
        old_spool = instance.state / 'ingest-pending' / Path(runner.receipt_relpath(old_receipt)).name
        old_spool.parent.mkdir(parents=True)
        old_spool.write_bytes(runner.canonical({'sha256': runner.digest(old_raw), 'receipt': old_receipt}))
        def replay(values):
            events.append('old_spool')
            self.assertEqual(runner.canonical(values[0]), old_raw)
        instance.materialize_ingest_receipts.side_effect = replay
        with redirect_stdout(io.StringIO()):
            self.assertEqual(instance.run_ingest_plan(plan, plan['jobs'][0]), 0)
        self.assertEqual(events, ['reconciliation', 'old_spool', 'preparation', 'discovery'])
        self.assertFalse(old_spool.exists())
        instance.git.assert_not_called()
        engine.run_prepared.assert_called_once()
        receipt = instance.materialize_ingest_receipt.call_args.args[0]
        reference = receipt['ingest']['evidence_ref']
        supplement = json.loads((instance.state / 'ingest-evidence' / (reference['sha256'] + '.json')).read_text())
        self.assertEqual(supplement['household_schema_preparation'], failed)

    def test_runner_cancellation_before_discovery_and_unexpected_failure_projection(self):
        instance, engine, plan = self.fixture_runner(preparation.unavailable())
        instance.prepare_household_schema.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            instance.run_ingest_plan(plan, plan['jobs'][0])
        engine.prepare_default.assert_not_called()
        with mock.patch.object(preparation, 'run_preparation', side_effect=RuntimeError('PRIVATE')):
            result = runner.Runner.prepare_household_schema(instance)
        self.assertEqual(result['reason'], 'invocation_failed')
        self.assertEqual(result['status'], 'preparation_failed')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_preparation_source_hash_and_outcome_bind_job_identity(self):
        result, _ = self.run_with(self.process())
        instance, engine, plan = self.fixture_runner(result)
        with redirect_stdout(io.StringIO()):
            instance.run_ingest_plan(plan, plan['jobs'][0])
        first = instance.materialize_ingest_receipt.call_args.args[0]
        changed = copy.deepcopy(result)
        changed['source_sha256']['helper'] = 'e' * 64
        instance.prepare_household_schema.return_value = changed
        with redirect_stdout(io.StringIO()):
            instance.run_ingest_plan(plan, plan['jobs'][0])
        second = instance.materialize_ingest_receipt.call_args.args[0]
        self.assertNotEqual(first['implementation_sha256'], second['implementation_sha256'])
        self.assertNotEqual(first['job_key'], second['job_key'])
        unavailable = preparation.unavailable('helper_timeout')
        unavailable.update(status='preparation_failed', source_sha256=copy.deepcopy(changed['source_sha256']))
        instance.prepare_household_schema.return_value = unavailable
        with redirect_stdout(io.StringIO()):
            instance.run_ingest_plan(plan, plan['jobs'][0])
        third = instance.materialize_ingest_receipt.call_args.args[0]
        self.assertEqual(second['implementation_sha256'], third['implementation_sha256'])
        self.assertNotEqual(second['job_key'], third['job_key'])


if __name__ == '__main__':
    unittest.main()
