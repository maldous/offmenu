import copy, hashlib, json, os, pathlib, subprocess, sys
r = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(r/'snapshot/tests-gitflow'))
from test_offmenu_gitflow import FlowTest, m, SCRIPT
results = []

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, data): p.write_text(json.dumps(data)); return str(p)
def raw(t, args):
    t.write_policy()
    before = set(t.ev.glob('*.json'))
    p = subprocess.run(['python3','-B',str(SCRIPT),'--repo',str(t.repo),'--policy',str(t.policy_path),'--evidence-dir',str(t.ev),*args], env=m.git_environment(),capture_output=True,text=True,timeout=30)
    try: body = json.loads(p.stdout); receipt = json.loads(pathlib.Path(body['receipt']).read_text())
    except (ValueError,KeyError): body = None; receipt = None
    return {'exitCode':p.returncode,'response':body,'receipt':receipt,'newReceiptCount':len(set(t.ev.glob('*.json'))-before),'stderr':p.stderr[-500:]}
def record(name, got, expected=2, extra=None):
    passed = got['exitCode']==expected and bool(got['receipt']) and (expected!=2 or got['receipt']['status']=='blocked' and got['newReceiptCount']==1)
    results.append({'case':name,'expectedExit':expected,'passed':passed,'actual':got,**(extra or {})})
def fixture(fn):
    t=FlowTest('runTest');t.setUp()
    try: fn(t)
    finally: t.doCleanups()

def normal(t):
    start,ready,gate,path,head,merged=t.normal_retirement_fixture()
    linked,normal=t.command('merge_receipt','--worker','9','--snapshot',str(path),'--preflight',gate['receipt'],'--ready',ready['receipt'])
    sp=pathlib.Path(start['receipt']);rp=pathlib.Path(ready['receipt'])
    sd=json.loads(sp.read_text());rd=json.loads(rp.read_text());gd=json.loads(pathlib.Path(gate['receipt']).read_text())
    branch=sd['branch'];alias='feature/09/independent-alias';t.git('branch',alias,head)
    def retire(s=start['receipt'], rr=ready['receipt'], n=linked['receipt'], check=True):
        args=['retire','--worker','9','--start',s,'--ready',rr,'--integration',n]
        if check: args+=['--check-only']
        return raw(t,args)
    record('normal-control',retire(),0)
    for field,value in [('worker',8),('owner','other-owner'),('repo',str(t.root/'other')),('branch',alias),('task','other-task'),('kind','hotfix'),('base',head),('base_line','main'),('start_receipt',str(t.ev/'missing-start.json')),('start_sha256','0'*64)]:
        rr=copy.deepcopy(rd);rr[field]=value;rp2=t.ev/('new-ready-'+field+'.json');write(rp2,rr)
        n=copy.deepcopy(normal);n['task_linkage'].update(ready_receipt=str(rp2),ready_sha256=sha(rp2))
        if field in n['task_linkage']: n['task_linkage'][field]=value
        np=t.ev/('new-normal-'+field+'.json');write(np,n)
        got=retire(rr=str(rp2),n=str(np));record('ready-'+field+'-consistent-link-rehash',got,extra={'sourceAndAliasPreserved':t.git('rev-parse',branch).strip()==head and t.git('rev-parse',alias).strip()==head})
    rr=copy.deepcopy(rd);rr['branch']=alias;rp2=t.ev/'execute-bad-ready.json';write(rp2,rr)
    n=copy.deepcopy(normal);n['task_linkage'].update(branch=alias,ready_receipt=str(rp2),ready_sha256=sha(rp2));np=t.ev/'execute-bad-normal.json';write(np,n)
    record('redirection-blocks-even-without-check-only',retire(rr=str(rp2),n=str(np),check=False),extra={'sourceAndAliasPreserved':t.git('rev-parse',branch).strip()==head and t.git('rev-parse',alias).strip()==head})
    for field,value in [('worker',8),('owner','other-owner'),('repo',str(t.root/'other')),('branch',alias),('source_task_start',str(t.ev/'missing-start.json')),('source_task_start_sha256','0'*64)]:
        n=copy.deepcopy(normal);n['task_linkage'][field]=value;np=t.ev/('link-'+field+'.json');write(np,n);record('normal-link-'+field,retire(n=str(np)))
    for field,value in [('worker',8),('owner','other-owner'),('source_branch',alias),('repo',str(t.root/'other'))]:
        g=copy.deepcopy(gd);g[field]=value;gp=t.ev/('gate-'+field+'.json');write(gp,g)
        n=copy.deepcopy(normal);n.update(preflight_receipt=str(gp),preflight_sha256=sha(gp));np=t.ev/('gate-link-'+field+'.json');write(np,n);record('preflight-'+field+'-consistent-digest',retire(n=str(np)))
    for field,value in [('branch',alias),('owner','other-owner'),('repo',str(t.root/'other')),('task','other-task'),('source',t.base)]:
        verdict=copy.deepcopy(t.policy['workers']['9']['retirement']);t.policy['workers']['9']['retirement'][field]=value
        record('retirement-verdict-'+field,retire());t.policy['workers']['9']['retirement']=verdict
    for field,value in [('owner','other-owner'),('active_task','other-task'),('path',str(t.root/'other')),('open_prs',['PR']),('recovery_dependencies',['dependency']),('evidence_dependencies',['receipt']),('ignored_custody','unknown')]:
        w=copy.deepcopy(t.policy['workers']['9']);t.policy['workers']['9'][field]=value;record('current-policy-'+field,retire());t.policy['workers']['9']=w
    t.git('switch',alias);record('same-head-current-checkout-alias',retire());t.git('switch','--detach',head);record('same-head-detached-checkout',retire());t.git('switch',branch)
    newer=t.commit('after ready');record('changed-authored-branch-head',retire());t.git('switch','--detach',head);t.git('branch','-f',branch,head);t.git('switch',branch)
    originalProvider=json.loads(path.read_text());provider=copy.deepcopy(originalProvider);provider['head_ref']=alias;write(path,provider)
    record('provider-snapshot-alias-vs-real-gate',raw(t,['merge_receipt','--worker','9','--snapshot',str(path),'--preflight',gate['receipt'],'--ready',ready['receipt']]))
    write(path,originalProvider)
    g=copy.deepcopy(gd);g['source_branch']=alias;gp=t.ev/'alias-provider-gate.json';write(gp,g);provider['head_ref']=alias;write(path,provider)
    record('provider-and-gate-alias-vs-authored-start',raw(t,['merge_receipt','--worker','9','--snapshot',str(path),'--preflight',str(gp),'--ready',ready['receipt']]))
    write(path,originalProvider)
    clone=t.ev/'copied-start.json';clone.write_bytes(sp.read_bytes());rr=copy.deepcopy(rd);rr.update(start_receipt=str(clone),start_sha256=sha(clone));rp2=t.ev/'copied-start-ready.json';write(rp2,rr)
    n=copy.deepcopy(normal);n['task_linkage'].update(ready_receipt=str(rp2),ready_sha256=sha(rp2));np=t.ev/'copied-start-normal.json';write(np,n)
    record('ready-copied-start-path-vs-explicit-original-start',retire(rr=str(rp2),n=str(np)))
    record('normal-control-after-all-negatives',retire(),0)

def integrated(t):
    start,ready,integrated,head=t.integrated_fixture()
    branch='feature/09/fixture';t.git('push','origin','develop');t.git('switch',branch)
    t.policy['lines']['develop']=t.verdict(line='develop',sha=head)
    t.policy['workers']['9'].update(active_task='fixture',ignored_custody='preserved',ignored_evidence=t.reference(),retirement=t.verdict(source=head,task='fixture',branch=branch,owner='fixture-worker09',repo=str(t.repo)))
    args=['retire','--worker','9','--start',start['receipt'],'--ready',ready['receipt'],'--integration']
    record('local-integrate-control',raw(t,args+[integrated['receipt'],'--check-only']),0)
    data=json.loads(pathlib.Path(integrated['receipt']).read_text())
    for field,value in [('worker',8),('owner','different-owner')]:
        d=copy.deepcopy(data);d[field]=value;p=t.ev/('different-integrator-'+field+'.json');write(p,d)
        record('local-integrate-receipt-'+field+'-mismatch',raw(t,args+[str(p),'--check-only']),extra={'branchPreserved':t.git('rev-parse',branch).strip()==head,'originalIntegrationReceipt':data,'suppliedIntegrationReceipt':d})
    t.git('switch','develop')
    # Prepare a new fixture to exercise pre-integration owner/task binding at
    # the original canonical base; this avoids changing any actual refs.

def integrate_bindings(t):
    start,sd=t.start();head=t.commit('binding source');ready,rd=t.ready(start)
    branch=sd['branch'];alias='feature/09/not-authored-task';t.git('branch',alias,head)
    t.git('switch','develop');t.review('develop',head,head)
    args=['integrate','--worker','9','--ready']
    tail=['--candidate',head,'--check-only']
    record('local-integration-readiness-control',raw(t,args+[ready['receipt']]+tail),0)
    for field,value in [('owner','different-owner')]:
        rr=copy.deepcopy(rd);rr[field]=value;rp=t.ev/('integration-ready-'+field+'.json');write(rp,rr)
        record('local-integrate-ready-'+field+'-mismatch',raw(t,args+[str(rp)]+tail),extra={'suppliedReady':rr,'originalStart':sd,'checkOnly':True})
    ss=copy.deepcopy(sd);ss['branch']=alias;sp=t.ev/'integration-start-alias.json';write(sp,ss)
    rr=copy.deepcopy(rd);rr.update(branch=alias,start_receipt=str(sp),start_sha256=sha(sp));rp=t.ev/'integration-ready-alias.json';write(rp,rr)
    record('local-integrate-rehashed-start-alias-task-mismatch',raw(t,args+[str(rp)]+tail),extra={'suppliedStart':ss,'suppliedReady':rr,'originalStart':sd,'checkOnly':True})

for fn in [normal,integrated,integrate_bindings]:fixture(fn)
report={'candidate':'58c5f051d037eb02582a83a0e7107d907b1f401e','cases':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'results':results}
(r/'binding-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}));print(json.dumps([{'case':x['case'],'error':x['actual']['receipt'].get('error'),'status':x['actual']['receipt']['status']} for x in results if not x['passed']]))
sys.exit(1 if report['failed'] else 0)
