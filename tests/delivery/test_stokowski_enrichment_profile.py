"""One affected path: finished native -> distinct contribution -> fixed command.

Git, binding files and SQLite are real isolated fixtures. Node execution is an
explicit command-boundary double; this is not a live UIF-102 validation result.
"""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import stokowski_operations as operations
import stokowski_stage as stage
import windmill_dispatcher as dispatcher
from symphony_tasks import runtime_lease_ids


class EnrichmentProfileTests(unittest.TestCase):
    def test_finished_native_contribution_fixed_command_and_critical_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root/'original'
            repository.mkdir()
            def git(where, *args):
                return subprocess.check_output(['git','-C',str(where),'-c','user.name=Synthetic',
                    '-c','user.email=synthetic@example.invalid',*args],stderr=subprocess.PIPE).decode().strip()
            def write(path, value):
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(value,sort_keys=True)+'\n')
            git(repository,'init','-b','bugfix/original-native')
            write(repository/'repository-standard.json',{'runtime_hold_paths':[]})
            git(repository,'add','.')
            git(repository,'commit','-qm','original')
            base = git(repository,'rev-parse','HEAD')
            runtime = root/'runtime'
            workspace = runtime/'workspaces/UIF-102'
            workspace.parent.mkdir(parents=True)
            subprocess.run(['git','clone','--quiet',str(repository),str(workspace)],check=True)
            candidate = root/'candidate'
            subprocess.run(['git','clone','--quiet',str(repository),str(candidate)],check=True)
            git(candidate,'checkout','-qb','bugfix/reviewed-contribution')
            output = operations.ENRICHMENT_TEST
            for where in (workspace,candidate):
                path = where/output
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('// synthetic reviewed Node file; command execution doubled\n')
            git(candidate,'add','.')
            git(candidate,'commit','-qm','reviewed contribution')
            head = git(candidate,'rev-parse','HEAD')
            outputs = {output:hashlib.sha256((candidate/output).read_bytes()).hexdigest()}
            resources = dict(cpu_millis=1000,memory_bytes=1610612736,io_slots=1,output_bytes=536870912)
            task = dict(issue_id='418060d3-ef43-491d-ac8e-70747129b448',owner='synthetic-owner',
                purpose='synthetic enrichment unit',allowed_paths=[output],acceptance=['four consumer cases'],
                resources=resources,attempt_limit=1)
            manifest = dict(version=1,project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',
                branch='bugfix/original-native',base_revision=base,label='enrichment-fixture',tasks={'UIF-102':task})
            request = dict(prompt='synthetic only',timeout_seconds=600)
            write(runtime/'manifest.json',manifest)
            write(runtime/'requests/UIF-102.json',request)
            pool = root/'pool';pool.mkdir()
            write(runtime/'capacity-policy.json',{'symphony':{'pool_path':str(pool)}})
            write(runtime/'provider-proof.json',{'fixture_only':True})
            write(runtime/'current-admission.json',dict(manifest_sha256=stage.file_hash(runtime/'manifest.json'),
                request_sha256=stage.file_hash(runtime/'requests/UIF-102.json')))
            entry = dict(issue='UIF-102',issue_id=task['issue_id'],runtime=str(runtime),
                admission_sha256=stage.file_hash(runtime/'current-admission.json'))
            binding = dict(branch=manifest['branch'],head=base,owner=task['owner'],write_roots=[output],
                resources=resources,task_sha256=operations.digest(dict(runtime=str(runtime),
                    manifest=manifest,request=request)))
            lease = runtime_lease_ids(runtime,manifest)['UIF-102']
            attempt = runtime/'attempts/UIF-102'
            receipt = dict(status='succeeded',child_tree_gone=True,scope_violations=[],source_head=base,
                origin='native-coding',exit_code=0,turn_completed=True,session_id='synthetic-session',
                source_identity_changed=False,final_head=base,final_branch=manifest['branch'],
                parent_runtime=str(runtime),issue='UIF-102',parent_binding=binding,
                binding_sha256=operations.digest(binding),lease=lease,output_sha256=outputs)
            write(attempt/'receipt.json',receipt)
            write(attempt/'intent.json',dict(lease=lease,binding=binding))
            write(attempt/'dispatch-intent.json',dict(expected_lease=lease,owner=task['owner'],
                entry_sha256=operations.digest(entry),manifest_sha256=stage.file_hash(runtime/'manifest.json'),
                request_sha256=stage.file_hash(runtime/'requests/UIF-102.json'),
                provider_proof_sha256=stage.file_hash(runtime/'provider-proof.json')))
            database = pool/'state.sqlite'
            with sqlite3.connect(database) as db:
                db.execute('CREATE TABLE leases(id TEXT,status TEXT,outcome TEXT,binding TEXT,fingerprint TEXT)')
                db.execute('INSERT INTO leases VALUES(?,?,?,?,?)',(lease,'finished','succeeded',
                    json.dumps(binding),operations.digest(binding)))
            spec = dict(version=1,issue='UIF-102',issue_id=task['issue_id'],owner=task['owner'],
                stage='validate',head=head,base=base,branch='bugfix/reviewed-contribution',
                policy_sha256='a'*64,runner_sha256='b'*64,executor_sha256='c'*64,outputs=outputs,
                profile=operations.ENRICHMENT_PROFILE,acceptance_sha256=operations.digest(dict(
                    task=task,native_receipt_sha256=stage.file_hash(attempt/'receipt.json'),
                    profile=operations.ENRICHMENT_PROFILE)))
            native_before = {p:p.read_bytes() for p in (runtime/'manifest.json',runtime/'current-admission.json',
                attempt/'receipt.json',attempt/'intent.json',attempt/'dispatch-intent.json')}
            with patch.object(stage,'SOURCE',repository):
                key = stage.bind(runtime,spec,candidate_root=candidate)
            selected = json.loads((runtime/'validation-bindings.json').read_text())['issues']['UIF-102']
            self.assertEqual(selected['candidate_root'],str(candidate))
            self.assertEqual(selected['source_head'],head)
            self.assertEqual(selected['derivation'],{})
            self.assertEqual(key,operations.operation_key(spec))
            self.assertTrue(all(p.read_bytes()==raw for p,raw in native_before.items()))
            self.assertEqual(git(workspace,'rev-parse','HEAD'),base)
            args = operations.bridge_arguments(spec)
            self.assertEqual(dispatcher.validate_request(args),args)
            derived = '/offmenu/.delivery/stokowski/native-validation/'+head
            self.assertEqual(operations.enrichment_workspace(spec),derived)
            body = shlex.split(args['command'])[2]
            self.assertIn('root=pathlib.Path('+repr(derived)+')',body)
            for wrong in ('/offmenu','/offmenu/.delivery/stokowski/native-validation/'+'0'*40):
                changed = body.replace('root=pathlib.Path('+repr(derived)+')',
                                       'root=pathlib.Path('+repr(wrong)+')',1)
                with self.assertRaisesRegex(ValueError,'derived enrichment root'):
                    dispatcher.validate_request(dict(args,command=
                        '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(changed)))
            self.assertNotIn('ACCEPTED_CONTROL_VALIDATORS',args['command'])
            bad = dict(args,command=args['command'].replace("'--test-concurrency=1'","'--test-concurrency=2'"))
            with self.assertRaises(ValueError):
                dispatcher.validate_request(bad)
            real_run = subprocess.run
            calls = []
            def run(argv, **kwargs):
                if tuple(argv)==operations.ENRICHMENT_COMMAND:
                    calls.append(kwargs)
                    self.assertNotIn('NODE_TEST_CONTEXT',kwargs['env'])
                    self.assertNotIn('SECRET',kwargs['env'])
                    return subprocess.CompletedProcess(argv,0,
                        '# tests 4\n# suites 0\n# pass 4\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n','')
                return real_run(argv,**kwargs)
            with patch.dict(os.environ,{'NODE_TEST_CONTEXT':'inherited-test-child','SECRET':'synthetic'}), \
                    patch.object(subprocess,'run',side_effect=run), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exec(compile(operations.enrichment_validation_code(spec,candidate),'<profile>','exec'),{})
            self.assertEqual(len(calls),1)
            # A file-level pass must never be promoted to four actual cases.
            def file_only(argv, **kwargs):
                if tuple(argv)==operations.ENRICHMENT_COMMAND:
                    return subprocess.CompletedProcess(argv,0,
                        '# tests 1\n# suites 0\n# pass 1\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n','')
                return real_run(argv,**kwargs)
            with patch.object(subprocess,'run',side_effect=file_only), redirect_stdout(io.StringIO()), \
                    redirect_stderr(io.StringIO()), self.assertRaisesRegex(AssertionError,'TAP acceptance'):
                exec(compile(operations.enrichment_validation_code(spec,candidate),'<profile>','exec'),{})
            with sqlite3.connect(database) as db:
                db.execute("UPDATE leases SET status='running'")
            with self.assertRaisesRegex(operations.OperationError,'immutable finished native result'):
                stage.bind(runtime,spec,candidate_root=candidate)
            with self.assertRaisesRegex(operations.OperationError,'explicit native candidate root|Explicit native candidate root'):
                stage.bind(runtime,dict(spec,profile='delivery-suite'),candidate_root=candidate)


if __name__ == '__main__':
    unittest.main()
