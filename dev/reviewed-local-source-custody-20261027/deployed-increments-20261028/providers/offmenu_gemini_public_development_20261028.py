from typing import TypedDict
import http.client,ssl,json
from datetime import datetime,timezone
class googleai(TypedDict):
    api_key:str
def main(connection:googleai):
    c=None;result={'provider':'gemini','model':'gemini-2.5-flash-lite','input_class':'fixed_public_synthetic','free_basis':'User no-payment APIaccount declaration; publishedfree model; notAntigravity','observed_at':datetime.now(timezone.utc).isoformat(),'inference_calls':0}
    try:
        c=http.client.HTTPSConnection('generativelanguage.googleapis.com',timeout=45,context=ssl.create_default_context());headers={'x-goog-api-key':connection['api_key'],'Content-Type':'application/json'}
        c.request('GET','/v1beta/models/gemini-2.5-flash-lite',headers=headers);r=c.getresponse()
        if r.status!=200:return dict(result,status='model_not_available',http_status=r.status)
        r.read(1048576)
        payload={'contents':[{'parts':[{'text':'For a hypothetical file manifest verifier, propose exactly3 concise tests as JSON array with name and expected. Cover changed content with unchanged filename, missing file, and correct SHA256. No real files or external lookup. Under120words.'}]}],'generationConfig':{'maxOutputTokens':500}}
        result['inference_calls']=1
        c.request('POST','/v1beta/models/gemini-2.5-flash-lite:generateContent',body=json.dumps(payload),headers=headers);r=c.getresponse();result.update(http_status=r.status,retry_after=r.getheader('Retry-After'))
        if r.status!=200:return dict(result,status='request_failed_no_retry')
        raw=r.read(1048577)
        if len(raw)>1048576:return dict(result,status='response_limit')
        d=json.loads(raw);cs=d.get('candidates') or [];out=''.join(x.get('text','') for x in cs[0].get('content',{}).get('parts',[])) if cs else '';finish=cs[0].get('finishReason') if cs else None
        return dict(result,status='completed' if out and finish=='STOP' else 'incomplete_completion',output=out[:6000],finish_reason=finish,output_is_untrusted=True)
    except Exception as e:return dict(result,status='request_failed_no_retry',error_type=type(e).__name__)
    finally:
        if c:c.close()
