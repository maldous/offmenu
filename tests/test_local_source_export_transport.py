"""Generated transport tests; no live runner, workflow, or network invocation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('export_transport_dispatcher', ROOT/'scripts/dispatch-foo-job.py')
jobs = importlib.util.module_from_spec(spec); spec.loader.exec_module(jobs)

class Transport(unittest.TestCase):
    def request(self): return {'schemaVersion':1,'jobId':'foo-export-fixture-001','profile':'local-source-export'}
    def evidence(self, raw=b'{}\n'):
        import hashlib
        return {'schemaVersion':'offmenu-local-source-summary/1','phase':'inventory','packetBytes':len(raw),
                'packetSha256':hashlib.sha256(raw).hexdigest(),'selectionSha256':'a'*64,
                'batchIndex':1,'batchCount':1,'totalFiles':0,'totalBytes':0,'itemCount':0,'sourceContentsIncluded':False}
    def test_profile_is_fixed_and_binds_validated_job_only(self):
        with patch.object(jobs,'source_export_artifact',return_value=Path('/tmp/fixed-artifact.json')):
            steps=jobs.profile_steps('local-source-export',ROOT,'a'*40,'foo-export-fixture-001')
            self.assertEqual([x[0] for x in steps],['readiness','local-source-export-tests','local-source-export'])
            self.assertEqual(steps[-1][2][-4:],['--job-id','foo-export-fixture-001','--artifact','/tmp/fixed-artifact.json'])
            for bad in ('../escape','x;echo secret',None):
                with self.assertRaises(jobs.JobError):jobs.profile_steps('local-source-export',ROOT,'a'*40,bad)
    def test_summary_sanitizer_excludes_source_and_unknown_keys(self):
        result=jobs.safe_evidence(json.dumps(self.evidence()).encode())
        self.assertIn('localSourceExport',result)
        self.assertNotIn('localSourceExport',jobs.safe_evidence(json.dumps(self.evidence()|{'body':'private'}).encode()))
    def test_success_without_valid_summary_fails(self):
        fake={'status':'passed','exitCode':0,'durationSeconds':0,'evidence':{}}
        with patch.object(jobs,'run_child',return_value=fake):
            result=jobs.run_step('local-source-export',['python','fixed'],ROOT)
        self.assertEqual(result['status'],'failed')
    def test_artifact_ready_requires_exact_digest_and_closed_real_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'artifact.json';path.write_bytes(b'{}\n'); output=Path(temp)/'output'
            report={'steps':[{'stepId':'local-source-export','evidence':{'localSourceExport':self.evidence()}}]}
            with patch.object(jobs,'source_export_artifact',return_value=path),patch.dict(os.environ,{'GITHUB_OUTPUT':str(output)}):
                jobs.mark_source_export_ready(report)
                self.assertEqual(output.read_text(),'source_export_ready=true\n')
                path.write_bytes(b'changed')
                with self.assertRaises(jobs.JobError):jobs.mark_source_export_ready(report)
    def test_current_run_attempt_is_bound_to_artifact_name(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'RUNNER_TEMP':temp,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2'}):
            self.assertEqual(jobs.source_export_artifact().relative_to(temp),Path('offmenu-source-export-123-2/source-export.json'))
    def test_workflow_keeps_read_only_foo_and_profile_guarded_artifact(self):
        workflow=(ROOT/'.github/workflows/foo-runner.yml').read_text()
        run=workflow.split('  publish_receipt:')[0]
        self.assertNotIn('contents: write',run)
        self.assertIn("if: steps.batch.outputs.source_export_ready == 'true'",run)
        self.assertIn('path: ${{ runner.temp }}/offmenu-source-export-${{ github.run_id }}-${{ github.run_attempt }}/source-export.json',run)
        self.assertIn('TRUSTED_CODE_SHA: REPLACE_WITH_REVIEWED_40_CHARACTER_COMMIT_SHA',run)
        self.assertIn('branches: [offmenu-runner-jobs]',run)
    def test_staged_export_retry_revalidates_instead_of_claiming_old_computation(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(jobs,'OUTPUT',Path(temp)):
            def run(request,sha,code,run_id,attempt):
                return {'status':'passed','steps':[{'stepId':'local-source-export','evidence':{'localSourceExport':self.evidence()}}], 'githubRunId':run_id,'githubRunAttempt':attempt}
            with patch.object(jobs,'run_profile',side_effect=run) as mocked:
                first=jobs.execute(self.request(),'a'*40,ROOT,'123','1')
                second=jobs.execute(self.request(),'a'*40,ROOT,'124','1')
            self.assertEqual(mocked.call_count,2)
            self.assertEqual(second['githubRunId'],'124')
            self.assertNotIn('delivery',second)
    def test_retry_changed_packet_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(jobs,'OUTPUT',Path(temp)):
            first={'status':'passed','steps':[{'stepId':'local-source-export','evidence':{'localSourceExport':self.evidence()}}]}
            changed={'status':'passed','steps':[{'stepId':'local-source-export','evidence':{'localSourceExport':self.evidence(b'changed')}}]}
            with patch.object(jobs,'run_profile',side_effect=[first,changed]):
                jobs.execute(self.request(),'a'*40,ROOT,'123','1')
                with self.assertRaisesRegex(jobs.JobError,'changed-between-attempts'):jobs.execute(self.request(),'a'*40,ROOT,'124','1')

if __name__=='__main__': unittest.main()
