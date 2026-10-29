"""Reviewed eight-task manifests and native configuration; no provider calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID
from tools.delivery import symphony_launch as launch
from tools.delivery.symphony_tasks import load_manifest, task_for_workspace
from tools.delivery.symphony_capacity import AdmissionError


class ManifestContracts(unittest.TestCase):
    def manifest(self):
        d=launch.default_manifest('a'*40);prototype=d['tasks'].pop('UIF-90')
        for n in range(1,9):
            task=copy.deepcopy(prototype);task['issue_id']=str(UUID(int=n));task['owner']='lane-'+str(n);task['allowed_paths']=['tests/lane-'+str(n)]
            d['tasks']['UIF-'+str(n)]=task
        return d

    def test_eight_tasks_prepare_with_eight_native_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'reviewed.json';p.write_text(json.dumps(self.manifest()))
            manifest=load_manifest(p,expected_head='a'*40)
            self.assertEqual(len(manifest['tasks']),8)
            self.assertEqual(task_for_workspace(manifest,'UIF-8')['owner'],'lane-8')
            facts={'source_branch':launch.BRANCH,'source_head':'a'*40,'tracked_source_clean':True,'native_bundle_hash_matches':True,'vendor_codex_exists':True}
            with patch.object(launch,'prerequisite',return_value=facts):
                workflow,receipt=launch.prepare(root/'runtime','gpt-6.1-sol',p)
                config=json.loads(workflow.read_text().split('---',2)[1]);self.assertEqual(config['agent']['max_concurrent_agents'],8)
                self.assertEqual(len(receipt['admitted_issue_names']),8)
                self.assertIn('--manifest',config['hooks']['before_run'])
                with self.assertRaisesRegex(RuntimeError,'already prepared'):launch.prepare(root/'runtime','gpt-6.1-sol',p)

    def test_source_paths_and_duplicate_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'manifest.json'
            for mutate in [lambda d:d.update(branch='feature/other'),lambda d:d['tasks']['UIF-1'].update(allowed_paths=['../outside']),lambda d:d['tasks']['UIF-1'].update(resources={'cpu_millis':True,'memory_bytes':1,'io_slots':1,'output_bytes':0})]:
                d=self.manifest();mutate(d);p.write_text(json.dumps(d))
                with self.assertRaises(AdmissionError):load_manifest(p,expected_head='a'*40)
            p.write_text('{"version":1,"version":1}')
            with self.assertRaisesRegex(AdmissionError,'duplicate'):load_manifest(p)


if __name__=='__main__':unittest.main()
