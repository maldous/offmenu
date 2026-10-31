"""Completed-evidence fixtures: no provider, Engine, Journal or external calls."""
from pathlib import Path
from types import SimpleNamespace
import copy
import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import ormsgpack
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_completed as completed
from symphony_capacity import AdmissionError,digest


class CompletedNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)/'repo';self.repo.mkdir()
        def git(*a):
            return subprocess.check_output(['git','-c','user.name=Fixture','-c','user.email=fixture@invalid','-C',str(self.repo),*a],stderr=subprocess.DEVNULL).decode().strip()
        self.git=git;git('init','-b','fixture');(self.repo/'.gitignore').write_text('.delivery/\n')
        (self.repo/'tools').mkdir();(self.repo/'tools/worker.py').write_text('before\n');git('add','.');git('commit','-m','native base');a=git('rev-parse','HEAD')
        (self.repo/'control.txt').write_text('disjoint\n');git('add','.');git('commit','-m','integration base');base=git('rev-parse','HEAD')
        (self.repo/'tools/worker.py').write_text('after\n');(self.repo/'tools/performance.py').write_text('projection\n');(self.repo/'tests').mkdir();(self.repo/'tests/test_performance.py').write_text('test\n');git('add','.');git('commit','-m','candidate');head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
        git('checkout','-b','develop',base);git('merge','--no-ff',head,'-m','reviewed integration');merge=git('rev-parse','HEAD')
        self.root=self.repo/'.delivery/stokowski';self.runtime=self.root/'native';self.runtime.mkdir(parents=True);self.evidence_dir=self.root/'owner-evidence';self.evidence_dir.mkdir();self.pool=self.root/'pool';self.pool.mkdir();self.outputs={p:hashlib.sha256((self.repo/p).read_bytes()).hexdigest() for p in ['tools/worker.py','tools/performance.py','tests/test_performance.py']}
        for p in self.outputs:
            f=self.runtime/'workspaces/UIF-119'/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((self.repo/p).read_bytes())
        self.owner='authenticated-fixture-owner';self.binding={'owner':self.owner,'head':a};self.lease='fixture-lease';self.unit={'issue_id':'fixture-unit','native_receipt_sha256':'native-pin','admission_sha256':'admission-pin'}
        native=dict(exit_code=0,turn_completed=True,session_id='fixture-native-session',status='succeeded',child_tree_gone=True,scope_violations=[],source_identity_changed=False,final_head=a,source_head=a,final_branch='bugfix/native',accepted_delivery=False,output_sha256=self.outputs,lease=self.lease,binding_sha256=digest(self.binding));self.native_path=self.runtime/'attempts/UIF-119/receipt.json';self.write(self.native_path,native);self.unit['native_receipt_sha256']=completed.file_sha(self.native_path)
        self.write(self.runtime/'capacity-policy.json',{'symphony':{'pool_path':str(self.pool)}})
        with sqlite3.connect(self.pool/'state.sqlite') as db:
            db.execute('CREATE TABLE leases(id TEXT,status TEXT,binding TEXT,outcome TEXT)');db.execute('INSERT INTO leases VALUES(?,?,?,?)',(self.lease,'finished',json.dumps(self.binding),'succeeded'))
        self.manifest={'base_revision':a,'branch':'bugfix/native','tasks':{'UIF-119':{'owner':self.owner,'allowed_paths':list(self.outputs)}}};self.entry={'issue_id':'fixture-unit'}
        policy='a'*64;runner=hashlib.sha256(b'fixture source pin; never executed').hexdigest();command='owner-reviewed fixture command; never executed';command_hash=hashlib.sha256(command.encode()).hexdigest()
        b=dict(pr_number=181,owner=self.owner,issue_id='fixture-unit',repository='maldous/offmenu',head=head,base=base,tree=tree,head_branch='bugfix/integration',outputs=self.outputs,validation_operation_key=command_hash,policy_sha256='c'*64,capacity_policy_sha256=policy)
        review=dict(verdict='accepted',findings=[],reviewed_outputs=self.outputs,integration_head=head,integration_base=base,integration_tree=tree,native_receipt_sha256=self.unit['native_receipt_sha256'],reviewer=dict(identity='independent-fixture-reviewer',role='independent source reviewer; not coding author or integration writer',requested_model=None,requested_effort=None,requested_provider=None,observed_model=None,observed_provider=None,resolution_status='unobserved'))
        request=dict(command=command,job_id='fixture-job',mode='write',timeout_seconds=180,resources={'cpu_millis':1000})
        receipt=dict(status='succeeded',exit_code=0,child_tree_gone=True,reconcile_required=False,job_id='fixture-job',command_sha256=command_hash,runner_sha256=runner,capacity_policy_sha256=policy)
        expected=dict(command_sha256=command_hash,mode='write',timeout_seconds=180,runner_sha256=runner,capacity_policy_sha256=policy,resources=request['resources']);receipt['request_sha256']=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()
        result=dict(isError=False,content=[dict(type='text',text='Result\n'+json.dumps(dict(receipt=receipt,admitted=True,job_succeeded=True,job_id='fixture-job'))+'\njob=12345678-1234-1234-1234-123456789abc tag=fixture')])
        engine=dict(base_revision=head,branch=b['head_branch'],accepted_outputs=self.outputs,checks=[{'id':'first'},{'id':'second'}]);self.evidence={'version':1,'kind':completed.KIND,'issue':'UIF-119','unit_binding':self.unit,'repository':str(self.repo),'windmill_job_id':'12345678-1234-1234-1234-123456789abc'}
        values={'integration_binding':b,'independent_review':review,'validation_request':request,'validation_receipt':receipt,'validation_result':result,'engine_task':engine}
        for k,v in values.items():self.evidence[k]=self.ref(k,v)
        observation=dict(publisher_owner=self.owner,github=dict(repository='maldous/offmenu',number=181,merged=True,merge_commit_sha=merge,head=head,base=base),source_tree=tree,source_clean=True,publication_triggers_actions=False,unresolved_findings=[],merge_commit=dict(sha=merge,tree=tree,parents=[base,head]),policy_sha256=b['policy_sha256'],capacity_policy_sha256=policy,develop_contains_merge=True,validation=dict(operation_key=command_hash,status='succeeded',head=head,base=base,capacity_policy_sha256=policy,outputs=self.outputs,child_tree_gone=True,reconcile_required=False),review=dict(reviewer='independent-fixture-reviewer',author='native Codex session fixture-native-session',independent=True,verdict='accept',findings=[],evidence_id='sha256:'+self.evidence['independent_review']['sha256']))
        state=dict(status='merge-verified',merge_effect='verified',action=None,binding_sha256=digest(b),merge_commit_sha=merge,qualification_sha256=digest(dict(validation=observation['validation'],review=observation['review'],tree=tree,policy=b['policy_sha256'])))
        self.evidence['controller_observation']=self.ref('controller_observation',observation);self.evidence['controller_state']=self.ref('controller_state',state)
        self.evidence['controller_claim']=self.ref('controller_claim',dict(owner=self.owner,directory=str(self.repo/'.delivery/integration/completed'),binding_sha256=digest(b)))
        database=self.evidence_dir/'controller.sqlite'
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE checkpoints(thread_id TEXT,checkpoint_ns TEXT,checkpoint_id TEXT,type TEXT,checkpoint BLOB)')
            db.execute('INSERT INTO checkpoints VALUES(?,?,?,?,?)',(digest(b),'','1','msgpack',ormsgpack.packb({'channel_values':{'result':state,'observation':observation}})))
        database.chmod(0o600);self.evidence['controller_checkpoint']={'path':str(database),'sha256':completed.file_sha(database)}

        self.config={'source_head':merge,'owner':self.owner,'policy_sha256':policy,'source_sha256':{'tools/delivery/windmill_runner.py':runner,'tools/delivery/stokowski_completed.py':completed.file_sha(completed.__file__)},'completed_native_validations':{}}
        self.current=SimpleNamespace(root=self.root,runtime=self.root/'coordinator',config=self.config,entries={'UIF-119':self.entry},guard=lambda:None,context=lambda *a,**k:(self.runtime,self.manifest,self.repo),gate_binding=lambda *a:self.unit)
        self.repin()

    def write(self,p,value):
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,sort_keys=True)+'\n');p.chmod(0o600)
    def ref(self,name,value):
        p=self.evidence_dir/(name+'.json');self.write(p,value);return {'path':str(p),'sha256':completed.file_sha(p)}
    def repin(self):
        self.config['completed_native_validations']['UIF-119']=self.ref('evidence',self.evidence)
    def mutate(self,key,change):
        p=Path(self.evidence[key]['path']);v=json.loads(p.read_bytes());change(v);self.write(p,v) # Do not alter owner-admitted immutable ref.
    def test_completed_packet_no_dispatch_and_truthful_distinct_bases(self):
        packet=completed.qualify(self.current,'UIF-119');self.assertEqual(packet['decision']['kind'],completed.KIND);self.assertIsNone(packet['decision']['action']);self.assertEqual(packet['unit_binding'],self.unit);self.assertNotEqual(packet['integration_binding']['base'],self.manifest['base_revision']);self.assertNotEqual(packet['integration_binding']['head_branch'],self.manifest['branch']);self.assertFalse((self.runtime/'operations').exists())
    def test_native_binding_change_refused(self):
        self.evidence['unit_binding']=dict(self.unit,admission_sha256='wrong');self.repin()
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
    def test_changed_admitted_artifacts_refused(self):
        for key in ['integration_binding','independent_review','validation_request','validation_receipt','validation_result','engine_task','controller_observation','controller_state']:
            with self.subTest(key=key):
                p=Path(self.evidence[key]['path']);original=p.read_bytes();p.write_bytes(original+b' ')
                with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
                p.write_bytes(original)
    def test_unknown_or_running_lease_refused(self):
        with sqlite3.connect(self.pool/'state.sqlite') as db:db.execute("UPDATE leases SET status='running'")
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
    def test_uncertain_native_receipt_refused(self):
        p=json.loads(self.native_path.read_bytes());p['child_tree_gone']=False;self.write(self.native_path,p)
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
    def test_changed_native_outputs_refused(self):
        (self.runtime/'workspaces/UIF-119/tools/worker.py').write_text('changed')
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
    def test_unqualified_other_repository_refused(self):
        self.evidence['repository']=str(self.repo.parent);self.repin()
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
    def test_arbitrary_source_owner_refused(self):
        self.config['owner']='another-owner'
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')

    def test_semantically_wrong_rebound_engine_evidence_refused(self):
        mutations=[('validation_request',lambda x:x.update(command='different command')),
                   ('validation_receipt',lambda x:x.update(child_tree_gone=False)),
                   ('validation_receipt',lambda x:x.update(job_id='different job')),
                   ('engine_task',lambda x:x.update(branch='feature/wrong')),
                   ('independent_review',lambda x:x['reviewer'].update(identity=self.owner)),
                   ('controller_state',lambda x:x.update(merge_commit_sha='0'*40))]
        original=copy.deepcopy(self.evidence)
        for key,change in mutations:
            with self.subTest(key=key):
                self.evidence=copy.deepcopy(original);value=json.loads(Path(original[key]['path']).read_bytes());change(value)
                self.evidence[key]=self.ref('altered-'+key,value);self.repin()
                with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')
        self.evidence=original;self.repin()
    def test_checkpoint_disagreement_refused(self):
        ref=self.evidence['controller_checkpoint'];p=Path(ref['path'])
        with sqlite3.connect(p) as db:db.execute("UPDATE checkpoints SET checkpoint=?",(ormsgpack.packb({'channel_values':{'result':{},'observation':{}}}),))
        ref['sha256']=completed.file_sha(p);self.repin()
        with self.assertRaises(AdmissionError):completed.qualify(self.current,'UIF-119')

    def test_normal_continuation_projects_completed_result_without_tick(self):
        from stokowski_adapter import CurrentWork
        import stokowski_stage
        c=self.current;c.stopping=False;c.state={'tasks':{}};c.save=lambda:None
        with patch.object(stokowski_stage,'tick',side_effect=AssertionError('must not submit/tick completed work')) as tick:
            asyncio.run(CurrentWork.continue_validation(c))
        self.assertEqual(c.state['tasks']['UIF-119']['validation']['status'],'succeeded');tick.assert_not_called()
        self.assertFalse((self.runtime/'operations').exists())

    def test_fixed_v2_transport_completed_source_separate_from_current_claim(self):
        import types
        import stokowski_unit_review as transport
        from stokowski_adapter import CurrentWork
        c=self.current;c.runtime.mkdir(mode=0o700);self.root.chmod(0o700);self.runtime.chmod(0o700);self.repo.chmod(0o700)
        c.catalog=self.root/'catalog.json';self.write(c.catalog,{'version':1,'entries':[self.entry]})
        for n in ['current.json','current-owner.json','installation.json','workflow.yaml','capacity-policy.json']:
            self.write(c.runtime/n,{'fixture':True})
        for n in ['current-admission.json','manifest.json','installation.json','provider-proof.json','requests/UIF-119.json','attempts/UIF-119/intent.json','attempts/UIF-119/dispatch-intent.json']:
            self.write(self.runtime/n,{'fixture':True})
        c.state={'tasks':{'UIF-119':{'unit_gate':{'binding':self.unit,'disposition':'waiting'}}}}
        c._check_unit_review=types.MethodType(CurrentWork._check_unit_review,c)
        c.unit_review_writer=types.MethodType(CurrentWork.unit_review_writer,c)
        pins={}
        for n in transport.REQUIRED|{'tools/delivery/stokowski_completed.py','tools/delivery/windmill_runner.py'}:
            p=self.repo/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path(completed.__file__).read_bytes() if n=='tools/delivery/stokowski_completed.py' else b'fixture source pin; never executed');p.chmod(0o600);pins[n]=completed.file_sha(p)
        c.config.update(source_sha256=pins)
        claim=self.repo/'.delivery/integration';claim.mkdir(mode=0o700);directory=claim/'actual-owner-current';directory.mkdir(mode=0o700)
        current_binding={'owner':self.owner,'issue_id':'unrelated-actual-owner-claim','head':'e'*40}
        self.write(directory/'binding.json',current_binding);owner_claim={'owner':self.owner,'directory':str(directory),'binding_sha256':digest(current_binding)}
        self.write(claim/'active-owner.json',owner_claim);self.write(directory/'repository-claim.json',owner_claim)
        for n in self.outputs:(self.runtime/'workspaces/UIF-119'/n).chmod(0o600)
        receipt_copy=self.runtime/'original-engine-validation-receipt.json'
        receipt_copy.write_bytes(Path(self.evidence['validation_receipt']['path']).read_bytes());receipt_copy.chmod(0o600)
        self.evidence['validation_receipt']={'path':str(receipt_copy),'sha256':completed.file_sha(receipt_copy)};self.repin()
        packet=completed.qualify(c,'UIF-119')
        context=dict(source_head=c.config['source_head'],source_sha256=pins,python_sha256=completed.file_sha(Path(sys.executable).resolve()),actor_uid=os.getuid(),runtime=str(c.runtime),runtime_root=str(self.root),workspace_roots=[str(self.repo)],claim_root=str(claim),controller_directory=str(directory),issue='UIF-119',unit_binding=self.unit,validation_receipt=packet['validation_receipt'],validation_receipt_source=self.evidence['validation_receipt'],completed_native_source=c.config['completed_native_validations']['UIF-119'])
        envelope={'snapshot':packet['snapshot'],'decision':packet['decision']};payload=json.dumps({'context':context,'envelope':envelope});evidence=json.dumps(packet)
        with patch.object(transport,'CurrentWork',return_value=c),patch.object(transport,'SOURCE',self.repo),patch.object(transport,'PYTHON',Path(sys.executable)):
            request={'version':2,'mode':'status','payload':payload,'evidence':evidence}
            self.assertEqual(transport.handle(request)['status'],'absent')
            request['mode']='write';self.assertEqual(transport.handle(request)['status'],'retained')
            incoming=c.runtime/'unit-review-UIF-119.json';before=incoming.stat();self.assertEqual(transport.handle(request)['status'],'retained');self.assertEqual(incoming.stat().st_ino,before.st_ino)
            altered=copy.deepcopy(packet);altered['validation_receipt']['job_id']='foreign';request['evidence']=json.dumps(altered)
            with self.assertRaises(AdmissionError):transport.handle(request)
        self.assertFalse((self.runtime/'operations').exists());self.assertFalse((directory/'graph.sqlite').exists())


if __name__=='__main__':unittest.main()
