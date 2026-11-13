"""Private fixed-public-task batch control; no arbitrary prompts, keys or paths."""
import concurrent.futures
import json
import uuid
from datetime import datetime, timezone
import wmill
from wmill import client as sdk
PATH='u/admin/offmenu_public_development_batch_20261028'
REGISTRY='u/admin/offmenu_free_provider_registry_20261028'
BASE='https://windmill.aldous.info'
GROQ='u/admin/offmenu_groq_public_development_20261028'
GEMINI='u/admin/offmenu_gemini_public_development_20261028'
CATALOG={k:('groq',GROQ) for k in ['atomic_checkpoint_review','parallel_batch_test_design','exact_hash_custody_test_design','capacity_admission_invariants','checkpoint_cancellation_boundary']}
CATALOG['manifest_verification_tests']=('gemini',GEMINI)

def api(client, method, path, body=None, params=None):
    fn=client.get if method=='GET' else client.post
    kwargs={'raise_for_status':False}
    if body is not None:kwargs['json']=body
    if params is not None:kwargs['params']=params
    r=fn('/w/offmenu/'+path,**kwargs)
    if r.status_code<200 or r.status_code>=300:raise ValueError('windmill_api_unavailable')
    return r.json() if method=='GET' else None

def disposition(result):
    if not isinstance(result,dict):return 'not_a_structured_result'
    if result.get('http_status') in [401,403]:return 'auth_repair_deferred'
    if result.get('http_status')==429:return 'rate_limited_no_automatic_retry'
    if result.get('status')!='completed' or result.get('output_truncated'):return 'incomplete_or_failed_reject'
    return 'candidate_requires_human_or_deterministic_review_not_delivered'

def safe_result(result):
    if isinstance(result,str):
        try:result=json.loads(result)
        except ValueError:return {'disposition':'unparseable_result'}
    if not isinstance(result,dict):return {'disposition':'not_a_structured_result'}
    keys=('provider','model','task','status','http_status','finish_reason','output_truncated','prompt_tokens','completion_tokens','inference_calls')
    answer={k:(result[k][:160] if isinstance(result[k],str) else result[k]) for k in keys if k in result and isinstance(result[k],(str,int,float,bool,type(None)))}
    answer['output_is_untrusted']=True
    answer['disposition']=disposition(result)
    answer['output']=str(result.get('output',''))[:6000]
    return answer

def validate_tasks(tasks):
    if not isinstance(tasks,list) or not 1<=len(tasks)<=3 or any(not isinstance(t,str) or t not in CATALOG for t in tasks) or len(set(tasks))!=len(tasks):raise ValueError('select_1_to_3_unique_catalog_tasks')
    if sum(CATALOG[t][0]=='groq' for t in tasks)>2:raise ValueError('groq_per_batch_limit_2')
    return tasks

def main(action:str='plan', tasks:list[str]=[], job_ids:list[str]=[], input_class:str='fixed_public_synthetic'):
    if action not in ('plan','check','submit','status','results','cancel'):return {'status':'invalid_action'}
    if input_class!='fixed_public_synthetic':return {'status':'unsupported_data_class_no_dispatch'}
    if action=='plan':
        return {'status':'ready','catalog':{k:{'provider':v[0],'script':v[1]} for k,v in CATALOG.items()},'max_tasks_per_batch':3,'max_groq_per_batch':2,'max_gemini_per_batch':1,'arbitrary_prompts_accepted':False,'private_data_allowed':False,'automatic_retry':False,'paid_fallback':False,'global_lease':False,'result_disposition':'candidate_not_delivered_until_review','actions':['check','submit','status','results','cancel'],'cancel_caveat':'Cancel children by returned IDs; cancelling the short-lived submitter alone does not cancel them. A provider request already sent cannot be recalled.'}
    client=sdk.Windmill()
    if action in ('check','submit'):
        try:validate_tasks(tasks)
        except ValueError as e:return {'status':str(e),'submitted':0}
        try:
            registry=wmill.get_resource(REGISTRY)
            states={p['provider']:p for p in registry.get('providers',[])}
            for provider in {CATALOG[t][0] for t in tasks}:
                state=states.get(provider,{})
                if state.get('free_eligible') is not True or state.get('enabled') != 'fixed_public_synthetic_development_tasks':return {'status':'provider_not_eligible','provider':provider,'submitted':0}
                path=GROQ if provider=='groq' else GEMINI
                # Inspect recent completed outcomes, not raw arguments/logs. A 429/auth failure
                # holds this provider for operator reconciliation; never rotate credentials.
                recent=api(client,'GET','jobs/list',params={'script_path_exact':path,'per_page':10})
                for item in recent:
                    if item.get('success') is None:continue
                    detail=api(client,'GET','jobs_u/get/'+str(uuid.UUID(item['id'])))
                    result=detail.get('result') or {}
                    if isinstance(result,str):result=json.loads(result)
                    code=result.get('http_status') if isinstance(result,dict) else None
                    if code in (401,403,429):return {'status':'provider_hold_reconcile_required','provider':provider,'http_status':code,'job_id':item['id'],'submitted':0}
                    break
        except Exception as e:return {'status':'preflight_unavailable_no_dispatch','error_type':type(e).__name__,'submitted':0}
        if action=='check':return {'status':'preflight_passed_no_dispatch','tasks':tasks,'submitted':0}
        def launch(task):
            provider,path=CATALOG[task]
            args={'connection':'$res:u/admin/offmenu_provider_'+provider+'_20261028'}
            if provider=='groq':args['task']=task
            try:
                jid=str(uuid.UUID(str(wmill.run_script_async(path,args=args))))
                return {'task':task,'provider':provider,'job_id':jid,'run_url':BASE+'/run/'+jid+'?workspace=offmenu','status':'enqueued'}
            except Exception as e:return {'task':task,'status':'enqueue_failed','error_type':type(e).__name__}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as pool:receipts=list(pool.map(launch,tasks))
        return {'status':'submitted','observed_at':datetime.now(timezone.utc).isoformat(),'jobs':receipts,'productive_count_excludes_this_coordinator':True,'automatic_retry':False,'next_action':'results with returned job_ids; cancel uses same IDs'}
    if not isinstance(job_ids,list) or not 1<=len(job_ids)<=3:return {'status':'select_1_to_3_job_ids'}
    try:ids=[str(uuid.UUID(j)) for j in job_ids]
    except (ValueError,TypeError,AttributeError):return {'status':'invalid_job_id'}
    output=[]
    for jid in ids:
        try:
            detail=api(client,'GET','jobs_u/get/'+jid)
            if detail.get('script_path') not in (GROQ,GEMINI):output.append({'job_id':jid,'status':'outside_task_allowlist'});continue
            row={'job_id':jid,'run_url':BASE+'/run/'+jid+'?workspace=offmenu','started_at':detail.get('started_at'),'duration_ms':detail.get('duration_ms'),'success':detail.get('success'),'running':detail.get('running')}
            if action=='cancel':
                parent=detail.get('parent_job')
                parent_detail=api(client,'GET','jobs_u/get/'+str(uuid.UUID(parent))) if parent else {}
                if parent_detail.get('script_path')!=PATH:row['status']='not_created_by_this_entrypoint'
                elif detail.get('success') is not None:row['status']='already_completed_no_cancel'
                else:
                    api(client,'POST','jobs_u/queue/cancel/'+jid,body={'reason':'User requested public development batch cancellation'})
                    row['status']='cancel_requested_not_yet_verified'
            elif action=='results':row['result']=safe_result(detail.get('result'))
            output.append(row)
        except Exception as e:output.append({'job_id':jid,'status':'inspection_failed','error_type':type(e).__name__})
    return {'status':'observed','jobs':output,'no_inference_performed_by_this_action':True}
