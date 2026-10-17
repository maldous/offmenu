import pathlib,sys,subprocess,json,os,hashlib,copy
r=pathlib.Path(__file__).parent;sys.path.insert(0,str(r/'snapshot/tests-gitflow'))
from test_offmenu_gitflow import FlowTest,m,SCRIPT
results=[]
def raw(t,args):
 t.write_policy();cmd=['python3','-B',str(SCRIPT),'--repo',str(t.repo),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev),*args];old=set(t.ev.glob('*.json'));p=subprocess.run(cmd,env=m.git_environment(),capture_output=True,text=True,timeout=30)
 try:body=json.loads(p.stdout)
 except ValueError:body=None
 receipt=json.loads(pathlib.Path(body['receipt']).read_text()) if body and 'receipt' in body else None
 return {'command':cmd,'exitCode':p.returncode,'stdoutJSON':body,'receipt':receipt,'newReceiptCount':len(set(t.ev.glob('*.json'))-old),'stderr':p.stderr[-400:]}
def put(name,got,expected=2):
 good=got['exitCode']==expected and (expected!=2 or got['newReceiptCount']==1 and got['receipt']['status']=='blocked');results.append({'case':name,'expectedExit':expected,'actual':got,'passed':good})
def isolated(fn):
 t=FlowTest('runTest');t.setUp()
 try:fn(t)
 finally:t.doCleanups()
def prefixes(t):
 launcher=SCRIPT.with_name('offmenu-gitflow-launch.py');t.write_policy();prefix=['python3','-B',str(launcher),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev)]
 for flag,value in [('--'+x,str(t.repo)) for x in ['r','re','rep','repo']]+[('--'+x,'2') for x in ['w','wo','wor','work','worke','worker']]:
  for form in [[flag,value],[flag+'='+value]]:
   before=set(t.ev.glob('*.json'));p=subprocess.run(prefix+form+['start','--kind','feature','--task','prefix-reject','--check-only'],cwd=t.repo,env=m.git_environment(),capture_output=True,text=True,timeout=30);results.append({'case':'launcher-'+form[0],'expectedExit':2,'exitCode':p.returncode,'noHelperReceiptCreated':set(t.ev.glob('*.json'))==before,'passed':p.returncode==2 and set(t.ev.glob('*.json'))==before})
 for flag in ['--','--?']:
  p=subprocess.run(prefix+[flag,'start'],cwd=t.repo,env=m.git_environment(),capture_output=True,text=True,timeout=30);results.append({'case':'launcher-separator-'+flag,'exitCode':p.returncode,'passed':p.returncode==2})
 p=subprocess.run(prefix+['start','--kind','feature','--task','legitimate-bound','--check-only'],cwd=t.repo,env=m.git_environment(),capture_output=True,text=True,timeout=30);body=json.loads(p.stdout);receipt=json.loads(pathlib.Path(body['receipt']).read_text());results.append({'case':'launcher-legitimate-control','exitCode':p.returncode,'repo':receipt['repo'],'passed':p.returncode==0 and receipt['repo']==str(t.repo)})
def malformed(t):
 head,base=t.delivery_fixture()
 mutations=[('required-review-string',lambda s:s.update(required_reviews=['invalid-record'])),('required-review-null',lambda s:s.update(required_reviews=[None])),('required-check-string',lambda s:s.update(required_checks=['invalid-record'])),('advisory-null',lambda s:s.update(advisory_reviews=[None])),('independent-review-list',lambda s:s.update(independent_review=[])),('platform-confirmation-null',lambda s:s.update(platform_confirmation=None)),('proof-path-list',lambda s:s['independent_review'].update(evidence={'path':[],'sha256':'0'*64}))]
 for name,mutate in mutations:
  s=copy.deepcopy(base);mutate(s);path=t.root/'malformed.json';path.write_text(json.dumps(s));put(name,raw(t,['delivery','--worker','9','--snapshot',str(path),'--head',head,'--base',t.base]))
def normal(t):
 start,ready,gate,path,head,merged=t.normal_retirement_fixture();linked,linkedData=t.command('merge_receipt','--worker','9','--snapshot',str(path),'--preflight',gate['receipt'],'--ready',ready['receipt']);unlinked,_=t.command('merge_receipt','--worker','9','--snapshot',str(path),'--preflight',gate['receipt']);readyPath=pathlib.Path(ready['receipt']);readyBytes=readyPath.read_bytes()
 args=['retire','--worker','9','--start',start['receipt'],'--ready',ready['receipt'],'--integration'];put('original-unlinked-normal-receipt-still-cannot-retire',raw(t,args+[unlinked['receipt'],'--check-only']))
 outside=t.root/'outside-gate.json';outside.write_bytes(pathlib.Path(gate['receipt']).read_bytes())
 variants=[('missing-linkage',lambda x:x.update(task_linkage={})),('wrong-owner',lambda x:x['task_linkage'].update(worker=8)),('wrong-task',lambda x:x['task_linkage'].update(task='wrong')),('wrong-source',lambda x:x['task_linkage'].update(source=t.base)),('wrong-ready-hash',lambda x:x['task_linkage'].update(ready_sha256='0'*64)),('wrong-ready-path',lambda x:x['task_linkage'].update(ready_receipt=str(t.root/'other-ready.json'))),('wrong-preflight-digest',lambda x:x.update(preflight_sha256='0'*64)),('preflight-outside-custody',lambda x:x.update(preflight_receipt=str(outside))),('wrong-parent-claim',lambda x:x.update(merge_parents=[head,t.base])),('wrong-tree-claim',lambda x:x.update(tree='0'*40)),('wrong-provider-hash',lambda x:x['provider_evidence'].update(sha256='0'*64)),('posthoc-preflight-time',lambda x:x.update(merged_at='2000-01-01T00:00:00Z'))]
 for name,mutate in variants:
  x=copy.deepcopy(linkedData);mutate(x);forged=t.ev/('probe-'+name+'.json');forged.write_text(json.dumps(x));put('normal-'+name,raw(t,args+[str(forged),'--check-only']))
 # Revalidate actual Git objects as well as JSON parent/tree claims.
 sourceTree=t.git('show','-s','--format=%T',head).strip();baseTree=t.git('show','-s','--format=%T',t.base).strip()
 for name,tree,parents in [('actual-reversed-parents',sourceTree,[head,t.base]),('actual-wrong-tree',baseTree,[t.base,head])]:
  bad=t.git('commit-tree',tree,'-p',parents[0],'-p',parents[1],'-m','reviewer forged actual merge').strip();x=copy.deepcopy(linkedData);x['merge_sha']=bad;forged=t.ev/(name+'.json');forged.write_text(json.dumps(x));put(name,raw(t,args+[str(forged),'--check-only']))
 # Preserve a start/ready semantic invariant even if someone updates JSON digests together.
 alternate='feature/09/not-the-start-task';t.git('branch',alternate,head);forgedReady=json.loads(readyBytes);forgedReady['branch']=alternate;readyPath.write_text(json.dumps(forgedReady));x=copy.deepcopy(linkedData);x['task_linkage']['ready_sha256']=hashlib.sha256(readyPath.read_bytes()).hexdigest();forged=t.ev/'forged-ready-branch.json';forged.write_text(json.dumps(x));got=raw(t,args+[str(forged),'--check-only']);put('forged-ready-branch-vs-start-with-updated-hash',got);results[-1].update(startBranch=json.loads(pathlib.Path(start['receipt']).read_text())['branch'],readyBranch=alternate,checkOnly=True,branchWasNotDeleted=True);readyPath.write_bytes(readyBytes)
 # Demonstrate the complete supported linked cycle in this disposable fixture only.
 put('linked-normal-retirement-check-only',raw(t,args+[linked['receipt'],'--check-only']),0);ret=raw(t,args+[linked['receipt']]);put('linked-normal-retirement-executes-only-temp-task',ret,0);exists=t.git('branch','--list','feature/09/fixture').strip();results[-1].update(taskBranchDeleted=exists=='',permanentFixturePathSurvives=t.repo.is_dir())
 t.policy['workers']['9']['active_task']=None;t.policy['routine_develop']={'reviewer':'Morgan','verdict':'reviewed-integration-line','sha':merged,'evidence':t.reference()};got=raw(t,['start','--worker','9','--kind','feature','--task','fresh-after-normal-merge']);put('fresh-next-claim-after-retirement',got,0);results[-1]['fetchedBaseEqualsActualMerged']=got['receipt']['base']==merged
for fn in [prefixes,malformed,normal]:isolated(fn)
report={'candidate':'58c5f051d037eb02582a83a0e7107d907b1f401e','cases':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'results':results};(r/'independent-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':report['cases'],'passed':report['passed'],'failed':report['failed'],'failedCases':[x for x in results if not x['passed']]},indent=2));sys.exit(1 if report['failed'] else 0)
