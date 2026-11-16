from typing import TypedDict
import http.client,ssl,json
from datetime import datetime,timezone
class groq(TypedDict):
    api_key:str
TASKS={
'exact_hash_custody_test_design': 'Design unit tests for a generic evidence join using synthetic schema: obligations(id, expected_sha256); artifacts(sha256, transport_ack, acceptance_verified, source_revision); receipts(obligation_id, artifact_sha256, reviewer_acceptance). Exact hash and revision must match. Transport ACK is not acceptance. Unknown or conflicting evidence must stay unknown, never become delivered. Return compact JSON with exactly4 tests, each containing name, setup_summary, expected. Under220words total; do not include full fixture records. Cover hash mismatch, revision mismatch, ACK-only, conflicting receipts. Synthetic examples only; no external lookup.',
'atomic_checkpoint_review': 'Review this entirely synthetic Python snippet for crash consistency. Return JSON with keys defects (array), fixes (array), tests (array), maximum3 entries each. Do not execute code. Snippet: def save(path, data):\n    with open(path, "w") as f:\n        json.dump(data, f)\nContext: a process may crash during save; the previous valid JSON checkpoint must survive.',
'parallel_batch_test_design': 'Design unit tests for an entirely hypothetical bounded parallel batch processor that writes checkpoints after each completed batch, resumes after cancellation, and must never count unfinished records as completed. Return JSON with tests array, each having name, setup, expected. Maximum5 tests. No external lookups.'}
def main(connection:groq, task:str='atomic_checkpoint_review'):
    if task not in TASKS: return {'status':'unsupported_public_task','inference_calls':0}
    c=None
    result={'provider':'groq','model':'openai/gpt-oss-20b','task':task,'input_class':'fixed_public_synthetic_development_fixture','observed_at':datetime.now(timezone.utc).isoformat(),'inference_calls':0,'output_is_untrusted':True}
    try:
        c=http.client.HTTPSConnection('api.groq.com',timeout=45,context=ssl.create_default_context())
        payload={'model':'openai/gpt-oss-20b','messages':[{'role':'user','content':TASKS[task]}],'max_tokens':768,'stream':False}
        result['inference_calls']=1
        c.request('POST','/openai/v1/chat/completions',body=json.dumps(payload),headers={'Authorization':'Bearer '+connection['api_key'],'Content-Type':'application/json'})
        r=c.getresponse();result['http_status']=r.status
        if r.status!=200:return dict(result,status='request_failed_no_retry')
        raw=r.read(1048577)
        if len(raw)>1048576:return dict(result,status='response_limit')
        d=json.loads(raw);choices=d.get('choices') or []
        output=(choices[0].get('message',{}).get('content') or '') if choices else ''
        usage=d.get('usage') or {}
        return dict(result,status='completed' if output and choices[0].get('finish_reason')!='length' else 'incomplete_completion',finish_reason=choices[0].get('finish_reason') if choices else None,output=output[:6000],output_truncated=len(output)>6000 or bool(choices and choices[0].get('finish_reason')=='length'),prompt_tokens=usage.get('prompt_tokens'),completion_tokens=usage.get('completion_tokens'))
    except Exception as e:return dict(result,status='request_failed_no_retry',error_type=type(e).__name__)
    finally:
        if c:c.close()

