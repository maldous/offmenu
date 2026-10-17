import pathlib,sys,json,subprocess,os,hashlib
r=pathlib.Path(__file__).parent;sys.path.insert(0,str(r/'snapshot/tests-gitflow'))
from test_offmenu_gitflow import FlowTest,m,SCRIPT
results=[]
def raw(t,args,cwd=None,script=SCRIPT,extra=()):
 t.write_policy();cmd=['python3','-B',str(script),'--repo',str(t.repo),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev),*args,*extra];before=set(t.ev.glob('*.json'));p=subprocess.run(cmd,cwd=cwd,env=m.git_environment(),capture_output=True,text=True,timeout=30)
 try:body=json.loads(p.stdout)
 except ValueError:body=None
 record=json.loads(pathlib.Path(body['receipt']).read_text()) if body and 'receipt' in body else body
 return {'command':cmd,'exitCode':p.returncode,'stdoutJSON':body,'receipt':record,'newReceiptCount':len(set(t.ev.glob('*.json'))-before),'stderrLast':p.stderr[-500:]}
def isolated(fn):
 t=FlowTest('runTest');t.setUp()
 try:fn(t)
 finally:t.doCleanups()
def delivery_matrix(t):
 head,snapshot=t.delivery_fixture();t.policy['client_enforcement']={'accepted_by':'Matt','origin_protection':'unavailable','bypassable_outside_workflow':True,'evidence':t.reference()};snapshot['requirements_status']='origin-unavailable-client-enforced'
 baseline=json.loads(json.dumps(snapshot))
 cases=[('client-unavailable-authorized',lambda s:None,0),('required-review-pending',lambda s:s.update(required_reviews=[{'head':head,'state':'PENDING'}]),2),('required-check-failed',lambda s:s.update(required_checks=[{'head':head,'status':'completed','conclusion':'failure'}]),2),('known-advisory-finding',lambda s:s['advisory_reviews'][0].update(open_findings=1),2),('security-undisposed',lambda s:s.update(security_alerts=['synthetic-alert']),2),('security-disposed',lambda s:s.update(security_alerts=['synthetic-alert'],security_confirmation={'state':'confirmed','head':head,'base':t.base,'evidence':t.reference()}),0),('security-stale-base',lambda s:s.update(security_alerts=['synthetic-alert'],security_confirmation={'state':'confirmed','head':head,'base':head,'evidence':t.reference()}),2),('platform-unconfirmed',lambda s:s['platform_confirmation'].update(state='pending'),2),('independent-self-review',lambda s:s['independent_review'].update(reviewer=s['owner']),2)]
 for name,mutate,expected in cases:
  s=json.loads(json.dumps(baseline));mutate(s);p=t.root/'snapshot.json';p.write_text(json.dumps(s));got=raw(t,['delivery','--worker','9','--snapshot',str(p),'--head',head,'--base',t.base]);assert got['exitCode']==expected and got['newReceiptCount']==1,(name,got);results.append({'case':name,'expectedExit':expected,'actual':got,'passed':True})
 s=json.loads(json.dumps(baseline));s['required_reviews']=['invalid-record'];p.write_text(json.dumps(s));got=raw(t,['delivery','--worker','9','--snapshot',str(p),'--head',head,'--base',t.base]);results.append({'case':'malformed-required-review-entry','expectedExit':2,'expectedDurableBlockedReceipt':True,'actual':got,'passed':got['exitCode']==2 and got['newReceiptCount']==1})
def launcher_alias(t):
 current=t.root/'launcher-home/worker-09';current.mkdir(parents=True);# A separate disposable launcher cwd, never real pool.
 launcher=SCRIPT.with_name('offmenu-gitflow-launch.py');t.write_policy();args=['python3','-B',str(launcher),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev),'--rep',str(t.repo),'start','--kind','feature','--task','alias-path','--check-only']
 p=subprocess.run(args,cwd=current,env=m.git_environment(),capture_output=True,text=True,timeout=30)
 try:body=json.loads(p.stdout);receipt=json.loads(pathlib.Path(body['receipt']).read_text())
 except (ValueError,KeyError):body=None;receipt=None
 results.append({'case':'launcher-abbreviated-repo-override','expectedExit':2,'actualExit':p.returncode,'command':args,'launcherCwd':str(current),'requestedOtherRepo':str(t.repo),'receiptRepo':receipt.get('repo') if receipt else None,'receiptStatus':receipt.get('status') if receipt else None,'stderr':p.stderr,'passed':p.returncode==2})
 full=args.copy();full[full.index('--rep')]='--repo';p=subprocess.run(full,cwd=current,env=m.git_environment(),capture_output=True,text=True,timeout=30);assert p.returncode==2;results.append({'case':'launcher-explicit-repo-override-control','actualExit':p.returncode,'passed':True})
def normal_retirement(t):
 task='normal-delivery-cycle';start,_=t.start(task=task);head=t.commit('reviewer normal path');ready,_=t.ready(start);branch='feature/09/'+task;t.git('push','origin',branch)
 t.policy['routine_delivery']={'authorizer':'Matt','project':'OffMenu','scope':'normal-qualified-gitflow','evidence':t.reference()};t.policy['reviews']=[t.verdict(operation='deliver-develop',candidate=head,base=t.base,source=head)]
 snapshot={'state':'open','base_ref':'develop','head_ref':branch,'head':head,'base':t.base,'owner':'worker09','url':'https://example.invalid/reviewer-pr','independent_review':{'state':'passed','reviewer':'worker13','head':head,'base':t.base,'evidence':t.reference()},'requirements_status':'known','required_reviews':[],'required_checks':[],'advisory_reviews':[],'security_alerts':[],'platform_confirmation':{'state':'confirmed','head':head,'base':t.base,'evidence':t.reference()}}
 gate,_=t.delivery_command(head,snapshot);t.git('switch','develop');t.git('merge','--no-ff',head,'-m','reviewer provider-style merge');merged=t.git('rev-parse','HEAD').strip();t.git('push','origin','develop')
 post=t.root/'merged.json';post.write_text(json.dumps({'url':snapshot['url'],'state':'merged','base_ref':'develop','head':head,'base':t.base,'merge_sha':merged,'normal_merge':True,'merged_at':m.utc(),'provider_evidence':t.reference()}));mr,receipt=t.command('merge_receipt','--worker','9','--snapshot',str(post),'--preflight',gate['receipt']);assert receipt['merge_parents']==[t.base,head]
 t.policy['lines']['develop']=t.verdict(line='develop',sha=merged);t.policy['reviews'].append(t.verdict(operation='integrate-develop',candidate=merged,base=t.base,source=head));t.policy['workers']['9'].update(active_task=task,ignored_custody='preserved',ignored_evidence=t.reference(),retirement=t.verdict(source=head,task=task))
 got=raw(t,['retire','--worker','9','--start',start['receipt'],'--ready',ready['receipt'],'--integration',mr['receipt'],'--check-only']);results.append({'case':'normal-merge-receipt-to-retirement','expectedExit':0,'actual':got,'mergeReceiptOperation':receipt['operation'],'normalMergeParents':receipt['merge_parents'],'normalMergeTree':receipt['tree'],'readySHA':json.loads(pathlib.Path(ready['receipt']).read_text())['candidate'],'source':head,'passed':got['exitCode']==0,'qualification':'All release baseline/line/Morgan/ignored/dependency fixtures were explicitly synthetically qualified to isolate receipt compatibility; no real certification implied.'})
 # Receipt history also prevents a next managed claim while no completed retirement exists.
 t.policy['workers']['9']['active_task']=None;t.policy['routine_develop']={'reviewer':'Morgan','verdict':'reviewed-integration-line','sha':merged,'evidence':t.reference()};got=raw(t,['start','--worker','9','--kind','feature','--task','next-normal-task','--check-only']);assert got['exitCode']==2 and 'active task' in got['receipt']['error'];results.append({'case':'normal-merge-does-not-silently-retire-or-free-next-task','actual':got,'passed':True})
def invalid_merge_shape(t):
 head,snapshot=t.delivery_fixture();gate,_=t.delivery_command(head,snapshot);baseTree=t.git('show','-s','--format=%T',t.base).strip();bad=t.git('commit-tree',baseTree,'-p',t.base,'-p',head,'-m','reviewer invalid merge tree').strip();t.git('switch','--detach',bad);t.git('push','origin',bad+':refs/heads/develop')
 p=t.root/'bad-merged.json';p.write_text(json.dumps({'url':snapshot['url'],'state':'merged','base_ref':'develop','head':head,'base':t.base,'merge_sha':bad,'normal_merge':True,'merged_at':m.utc(),'provider_evidence':t.reference()}));got=raw(t,['merge_receipt','--worker','9','--snapshot',str(p),'--preflight',gate['receipt']]);assert got['exitCode']==2 and 'tree differs' in got['receipt']['error'];results.append({'case':'normal-parents-but-different-tree-rejected','actual':got,'passed':True})
for fn in [delivery_matrix,launcher_alias,normal_retirement,invalid_merge_shape]:isolated(fn)
report={'candidate':'e9f6eec4ea9de6b9a5b27bcd325183d0ca50b442','cases':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'results':results};(r/'independent-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':report['cases'],'passed':report['passed'],'failed':report['failed'],'failedCases':[x for x in results if not x['passed']]},indent=2));sys.exit(1 if report['failed'] else 0)
