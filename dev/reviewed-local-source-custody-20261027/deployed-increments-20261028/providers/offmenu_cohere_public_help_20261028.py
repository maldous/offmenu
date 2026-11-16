from typing import TypedDict
import http.client,ssl,json
from datetime import datetime,timezone
class cohere(TypedDict):
    apiKey:str
def main(connection:cohere):
    result={'provider':'cohere','observed_at':datetime.now(timezone.utc).isoformat(),'input_class':'fixed_public_synthetic_development_fixture','inference_calls':0,'output_is_untrusted':True,'use_scope':'development_evaluation','free_basis':'User confirms no payment details; official free/trial mode'}
    c=None
    try:
        c=http.client.HTTPSConnection('api.cohere.com',timeout=45,context=ssl.create_default_context())
        headers={'Authorization':'Bearer '+connection['apiKey'],'Content-Type':'application/json'}
        c.request('GET','/v1/models?endpoint=chat',headers=headers);r=c.getresponse()
        if r.status!=200:return dict(result,status='catalog_failed',http_status=r.status)
        raw=r.read(4194305)
        if len(raw)>4194304:return dict(result,status='catalog_limit')
        d=json.loads(raw);models=d.get('data',d.get('models',[]))
        ids=[x.get('id',x.get('name')) for x in models]
        preferred=["command-r7b-12-2024","command-a-03-2025","command-a-plus-05-2026"]
        model=next((m for m in preferred if m in ids),None)
        if not model:return dict(result,status='preferred_model_not_available',catalog_ids=ids)
        result['model']=model
        payload={'model':model,'messages':[{'role':'user','content':"Write a concise user-facing help paragraph for a hypothetical batch processing tool. Facts: Submit returns child job IDs. The coordinator finishing does not mean children finished. Status reports each child. Cancel requests cancellation of selected children but cannot recall an external request already sent. Results require review before acceptance. Use plain English, under120words. Public synthetic software documentation only; no external lookup."}],'max_tokens':600,'stream':False}
        result['inference_calls']=1
        c.request('POST','/v2/chat',body=json.dumps(payload),headers=headers);r=c.getresponse()
        result['http_status']=r.status
        result['retry_after']=r.getheader('Retry-After')
        if r.status!=200:return dict(result,status='request_failed_no_retry')
        raw=r.read(1048577)
        if len(raw)>1048576:return dict(result,status='response_limit')
        d=json.loads(raw)
        output=''.join(x.get('text','') for x in d.get('message',{}).get('content',[]) if x.get('type')=='text');finish=d.get('finish_reason')
        truncated=finish in ('length','MAX_TOKENS') or len(output)>6000
        return dict(result,status='completed' if output and not truncated else 'incomplete_completion',output=output[:6000],finish_reason=finish,output_truncated=truncated)
    except Exception as e:return dict(result,status='request_failed_no_retry',error_type=type(e).__name__)
    finally:
        if c:c.close()
