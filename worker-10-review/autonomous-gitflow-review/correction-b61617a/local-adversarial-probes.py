import copy, hashlib, json, pathlib, subprocess, sys
r=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(r/'snapshot/tests-gitflow'))
from test_offmenu_gitflow import FlowTest,m,SCRIPT
results=[]
def write(path,value):path.write_text(json.dumps(value));return str(path)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def raw(t,args):
    t.write_policy();before=set(t.ev.glob('*.json'))
    p=subprocess.run(['python3','-B',str(SCRIPT),'--repo',str(t.repo),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev),*args],env=m.git_environment(),text=True,capture_output=True,timeout=30)
    try:body=json.loads(p.stdout);rec=json.loads(pathlib.Path(body['receipt']).read_text())
    except (ValueError,KeyError):body=None;rec=None
    return {'exitCode':p.returncode,'response':body,'receipt':rec,'newReceiptCount':len(set(t.ev.glob('*.json'))-before),'stderr':p.stderr[-300:]}
def record(name,got,expected=2,extra=None):
    good=got['exitCode']==expected and got['receipt'] is not None and (expected!=2 or got['receipt']['status']=='blocked' and got['newReceiptCount']==1)
    results.append({'case':name,'passed':good,'expectedExit':expected,'actual':got,**(extra or {})})
def isolated(fn):
    t=FlowTest('runTest');t.setUp()
    try:fn(t)
    finally:t.doCleanups()

def local_retirement(t):
    start,ready,integration,head=t.integrated_fixture();branch='feature/09/fixture'
    t.git('push','origin','develop');t.git('switch',branch)
    t.policy['lines']['develop']=t.verdict(line='develop',sha=head)
    t.policy['workers']['9'].update(active_task='fixture',ignored_custody='preserved',ignored_evidence=t.reference(),retirement=t.verdict(source=head,task='fixture',branch=branch,owner='fixture-worker09',repo=str(t.repo)))
    sd=json.loads(pathlib.Path(start['receipt']).read_text());rd=json.loads(pathlib.Path(ready['receipt']).read_text());original=json.loads(pathlib.Path(integration['receipt']).read_text())
    alias='feature/09/unrelated-same-head';t.git('branch',alias,head)
    def retire(s=start['receipt'],rr=ready['receipt'],ir=integration['receipt'],check=True):
        a=['retire','--worker','9','--start',s,'--ready',rr,'--integration',ir]
        return raw(t,a+(['--check-only'] if check else []))
    record('genuine-local-retirement-control',retire(),0)
    fields=['worker','owner','repo','task','source','source_branch','source_task_start','source_task_start_sha256','ready_receipt','ready_sha256','target_branch','line','head_before','base','candidate']
    for field in fields:
        d=copy.deepcopy(original);d.pop(field,None);p=t.ev/('missing-local-'+field+'.json');write(p,d);record('missing-legacy-local-'+field,retire(ir=str(p)))
    changes=[('source_branch',alias),('target_branch','main'),('task','other-task'),('source_task_start',str(t.ev/'missing-start.json')),('source_task_start_sha256','0'*64),('ready_receipt',str(t.ev/'missing-ready.json')),('ready_sha256','0'*64),('head_before',head),('base',head),('candidate',t.base),('source',t.base),('line','main'),('candidate','refs/heads/'+branch),('source_task_start',[]),('ready_receipt',[])]
    for i,(field,value) in enumerate(changes):
        d=copy.deepcopy(original);d[field]=value;p=t.ev/('changed-local-'+str(i)+'.json');write(p,d);record('changed-local-'+field+'-'+str(i),retire(ir=str(p)))
    d=copy.deepcopy(original);d.update(base=head,head_before=head);p=t.ev/'consistent-base-observation.json';write(p,d);record('consistent-new-base-and-observed-head-stale-Morgan-review',retire(ir=str(p)))
    rr=copy.deepcopy(rd);rr['branch']=alias;rp=t.ev/'redirected-ready.json';write(rp,rr)
    d=copy.deepcopy(original);d.update(source_branch=alias,ready_receipt=str(rp),ready_sha256=digest(rp));p=t.ev/'consistent-alias-local.json';write(p,d)
    record('consistent-ready-and-local-rehash-cannot-redirect-executing-retirement',retire(rr=str(rp),ir=str(p),check=False))
    ss=copy.deepcopy(sd);ss['branch']=alias;sp=t.ev/'alias-source-start.json';write(sp,ss)
    rr=copy.deepcopy(rd);rr.update(branch=alias,start_receipt=str(sp),start_sha256=digest(sp));rp=t.ev/'alias-source-ready.json';write(rp,rr)
    d=copy.deepcopy(original);d.update(source_branch=alias,source_task_start=str(sp),source_task_start_sha256=digest(sp),ready_receipt=str(rp),ready_sha256=digest(rp));p=t.ev/'all-alias-local.json';write(p,d)
    record('consistent-start-ready-local-alias-rehash-cannot-change-authored-task',retire(s=str(sp),rr=str(rp),ir=str(p)))
    clone=t.ev/'copied-authored-start.json';clone.write_bytes(pathlib.Path(start['receipt']).read_bytes());rr=copy.deepcopy(rd);rr.update(start_receipt=str(clone),start_sha256=digest(clone));rp=t.ev/'copied-start-ready.json';write(rp,rr)
    d=copy.deepcopy(original);d.update(source_task_start=str(clone),source_task_start_sha256=digest(clone),ready_receipt=str(rp),ready_sha256=digest(rp));p=t.ev/'copied-start-local.json';write(p,d)
    record('consistent-copied-start-ready-local-path-vs-explicit-authored-start',retire(rr=str(rp),ir=str(p)))
    record('genuine-local-retirement-after-negatives',retire(),0)
    got=retire(check=False);record('genuine-local-disposable-retirement',got,0,{'originalTaskBranchDeleted':not t.git('branch','--list',branch).strip(),'unrelatedAliasPreserved':t.git('rev-parse',alias).strip()==head,'permanentFixturePathPreserved':t.repo.is_dir()})
    t.policy['workers']['9']['active_task']=None;t.policy['routine_develop']={'reviewer':'Morgan','verdict':'reviewed-integration-line','sha':head,'evidence':t.reference()}
    record('fresh-dispatch-after-local-retirement',raw(t,['start','--worker','9','--kind','feature','--task','local-fresh-next']),0)

def target_checkout(t):
    start,sd=t.start();head=t.commit('exact-source');ready,rd=t.ready(start);t.review('develop',head,head)
    args=['integrate','--worker','9','--ready',ready['receipt'],'--candidate',head,'--check-only']
    record('integration-refuses-source-checkout-as-target',raw(t,args))
    t.git('switch','--detach',t.base);record('integration-refuses-detached-target-base',raw(t,args))
    t.git('switch','-c','develop-alias',t.base);record('integration-refuses-same-head-target-alias',raw(t,args))
    t.git('switch','develop');record('integration-accepts-exact-target-checkout',raw(t,args),0)

for fn in [local_retirement,target_checkout]:isolated(fn)
report={'candidate':'b61617a6d5896c2ea11bf81c4a3cfa4f93c130bf','cases':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'results':results}
(r/'local-adversarial-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}));print(json.dumps([x['case'] for x in results if not x['passed']]))
sys.exit(1 if report['failed'] else 0)
