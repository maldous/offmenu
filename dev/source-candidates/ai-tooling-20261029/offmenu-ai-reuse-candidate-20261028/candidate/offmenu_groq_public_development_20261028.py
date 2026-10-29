from typing import TypedDict
import http.client,ssl,json
from datetime import datetime,timezone
import base64
import copy
import fcntl
import hashlib
import os
from pathlib import Path
import time
import uuid
class groq(TypedDict):
    api_key:str
TASKS={
'exact_hash_custody_test_design': 'Design unit tests for a generic evidence join using synthetic schema: obligations(id, expected_sha256); artifacts(sha256, transport_ack, acceptance_verified, source_revision); receipts(obligation_id, artifact_sha256, reviewer_acceptance). Exact hash and revision must match. Transport ACK is not acceptance. Unknown or conflicting evidence must stay unknown, never become delivered. Return compact JSON with exactly4 tests, each containing name, setup_summary, expected. Under220words total; do not include full fixture records. Cover hash mismatch, revision mismatch, ACK-only, conflicting receipts. Synthetic examples only; no external lookup.',
'atomic_checkpoint_review': 'Review this entirely synthetic Python snippet for crash consistency. Return JSON with keys defects (array), fixes (array), tests (array), maximum3 entries each. Do not execute code. Snippet: def save(path, data):\n    with open(path, "w") as f:\n        json.dump(data, f)\nContext: a process may crash during save; the previous valid JSON checkpoint must survive.',
'parallel_batch_test_design': 'Design unit tests for an entirely hypothetical bounded parallel batch processor that writes checkpoints after each completed batch, resumes after cancellation, and must never count unfinished records as completed. Return JSON with tests array, each having name, setup, expected. Maximum5 tests. No external lookups.'}

MODEL = 'openai/gpt-oss-20b'
SETTINGS = {'max_tokens': 768, 'stream': False}
VERSIONS = {'prompt': '1', 'schema': '1', 'validator': '1', 'policy': 'public-synthetic-1'}
RESPONSE_LIMIT = 1048576


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = item
        return result
    def constant(value):
        raise ValueError('non-finite JSON number')
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


def validate(task, result):
    """Structural acceptance only; generated advice remains untrusted."""
    if result.get('status') != 'completed' or result.get('finish_reason') != 'stop':
        return False, 'completion_not_stopped'
    if result.get('output_truncated') is not False:
        return False, 'truncated_output'
    try:
        output = strict_json(result['output'])
        if not isinstance(output, dict):
            return False, 'expected_object'
        if task == 'atomic_checkpoint_review':
            if set(output) != {'defects', 'fixes', 'tests'}:
                return False, 'unexpected_fields'
            for items in output.values():
                if not isinstance(items, list) or not 1 <= len(items) <= 3:
                    return False, 'invalid_array'
                if any(not isinstance(item, (str, dict)) or not item for item in items):
                    return False, 'invalid_array_item'
        else:
            if set(output) != {'tests'} or not isinstance(output['tests'], list):
                return False, 'expected_tests_array'
            tests = output['tests']
            exact = task == 'exact_hash_custody_test_design'
            if not (len(tests) == 4 if exact else 1 <= len(tests) <= 5):
                return False, 'invalid_test_count'
            fields = {'name', 'setup_summary' if exact else 'setup', 'expected'}
            for item in tests:
                if not isinstance(item, dict) or set(item) != fields:
                    return False, 'invalid_test_fields'
                if any(not isinstance(v, str) or not v.strip() for v in item.values()):
                    return False, 'invalid_test_text'
            if exact and len(result['output'].split()) >= 220:
                return False, 'word_limit'
        return True, None
    except (ValueError, TypeError, KeyError, RecursionError):
        return False, 'invalid_json'


def token_count(value):
    return value if type(value) is int and value >= 0 else None


def main(connection: groq, task: str = 'atomic_checkpoint_review'):
    """Original explicit provider entry point; no cache or automatic retries."""
    started = time.monotonic()
    result = {'provider': 'groq', 'model': MODEL, 'task': task,
              'input_class': 'fixed_public_synthetic_development_fixture',
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'inference_calls': 0, 'output_is_untrusted': True,
              'cache_hit': False, 'prompt_tokens': None, 'completion_tokens': None,
              'provider_cached_tokens': None}
    if task not in TASKS:
        result.update(status='unsupported_public_task', accepted=False,
                      new_accepted_outputs=0, elapsed_seconds=time.monotonic()-started)
        return result
    c = None
    try:
        c = http.client.HTTPSConnection('api.groq.com', timeout=45, context=ssl.create_default_context())
        payload = dict(SETTINGS, model=MODEL, messages=[{'role': 'user', 'content': TASKS[task]}])
        result['inference_calls'] = 1
        c.request('POST', '/openai/v1/chat/completions', body=json.dumps(payload),
                  headers={'Authorization': 'Bearer '+connection['api_key'], 'Content-Type': 'application/json'})
        r = c.getresponse()
        result['http_status'] = r.status
        raw = r.read(RESPONSE_LIMIT+1)
        # Preserve bounded exact bytes, including failed and malformed responses.
        result['response_body_base64'] = base64.b64encode(raw).decode('ascii')
        result['response_body_truncated'] = len(raw) > RESPONSE_LIMIT
        if r.status != 200:
            result['status'] = 'request_failed_no_retry'
        elif len(raw) > RESPONSE_LIMIT:
            result['status'] = 'response_limit'
        else:
            d = strict_json(raw)
            choices = d.get('choices') or []
            choice = choices[0] if choices else {}
            output = choice.get('message', {}).get('content') or ''
            usage = d.get('usage') or {}
            details = usage.get('prompt_tokens_details') or {}
            result.update(status='completed' if output and choice.get('finish_reason') != 'length' else 'incomplete_completion',
                          finish_reason=choice.get('finish_reason'), output=output,
                          output_truncated=choice.get('finish_reason') == 'length',
                          response_id=d.get('id'), response_model=d.get('model'),
                          prompt_tokens=token_count(usage.get('prompt_tokens')),
                          completion_tokens=token_count(usage.get('completion_tokens')),
                          provider_cached_tokens=token_count(details.get('cached_tokens')))
    except Exception as e:
        result.update(status='request_failed_no_retry', error_type=type(e).__name__)
    finally:
        if c:
            c.close()
    accepted, error = validate(task, result)
    result.update(accepted=accepted, validation_error=error,
                  new_accepted_outputs=int(accepted), elapsed_seconds=time.monotonic()-started)
    if accepted:
        result['accepted_artifact_id'] = str(uuid.uuid4())
    return result


def provenance(task, account_namespace, model_version):
    if task not in TASKS:
        raise ValueError('unsupported public task')
    if not isinstance(account_namespace, str) or not account_namespace.strip():
        raise ValueError('explicit non-secret provider account namespace required')
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError('explicit operator model version/epoch required')
    return {'provider': 'groq', 'account_namespace': account_namespace,
            'model': MODEL, 'model_version': model_version, 'task': task,
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256': digest(TASKS[task]), 'versions': dict(VERSIONS),
            'generation_settings': copy.deepcopy(SETTINGS)}


def atomic_json(path, value):
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            os.chmod(temp, 0o600)
            stream.write(canonical(value)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp.exists():
            temp.unlink()


def run_cached(connection, task, *, cache_dir, account_namespace, model_version):
    """Opt-in local POSIX store. Shared directory is required across processes.

    Never derive the account namespace from credentials. The owner must rotate the
    model epoch if a provider alias changes; an unversioned alias cannot prove that.
    Receipts retain full bounded public responses and must be retained by the owner.
    """
    started = time.monotonic()
    started_ns = time.time_ns()
    prov = provenance(task, account_namespace, model_version)
    key = digest(canonical(prov))
    root = Path(cache_dir)
    for directory in (root, root/'accepted', root/'receipts', root/'locks', root/'artifacts', root/'rejected', root/'attempts'):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    invalidation = None
    # Kernel releases flock on crash. Lock covers validation, request and commit;
    # independent exact keys do not serialize behind each other.
    with (root/'locks'/key).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root/'accepted'/(key+'.json')
        entry = None
        if path.exists():
            try:
                candidate = strict_json(path.read_text(encoding='utf-8'))
                stored = candidate['result']
                valid, reason = validate(task, stored)
                if (candidate['provenance'] != prov or candidate['key'] != key or
                        candidate['result_sha256'] != digest(canonical(stored)) or
                        not valid or stored.get('accepted') is not True or not stored.get('accepted_artifact_id')):
                    raise ValueError(reason or 'provenance_or_integrity')
                entry = candidate
            except (ValueError, KeyError, TypeError, RecursionError) as error:
                invalidation = type(error).__name__
                os.replace(path, root/'rejected'/(key+'.'+uuid.uuid4().hex+'.json'))
        shared_attempt = None
        attempt_path = root/'attempts'/(key+'.json')
        if not entry and attempt_path.exists():
            try:
                attempt = strict_json(attempt_path.read_text(encoding='utf-8'))
                if (attempt['completed_ns'] >= started_ns and attempt['provenance'] == prov
                        and attempt['result'].get('accepted') is False):
                    shared_attempt = attempt
            except (ValueError, KeyError, TypeError, RecursionError):
                pass
        if entry or shared_attempt:
            original = (entry or shared_attempt)['result']
            result = copy.deepcopy(original)
            # Original token usage belongs to the accepted artifact, not this call.
            result['origin_usage'] = {k: original.get(k) for k in
                                      ('prompt_tokens', 'completion_tokens', 'provider_cached_tokens', 'elapsed_seconds')}
            result.update(inference_calls=0, prompt_tokens=0, completion_tokens=0,
                          provider_cached_tokens=None, cache_hit=bool(entry), shared_inflight=bool(shared_attempt), new_accepted_outputs=0,
                          observed_at=datetime.now(timezone.utc).isoformat())
        else:
            result = main(connection, task)
            # Fail closed even if the entry point is replaced or accidentally relaxed.
            valid, reason = validate(task, result)
            result.update(accepted=valid, validation_error=reason, new_accepted_outputs=int(valid))
            if valid:
                result['accepted_artifact_id'] = digest(canonical({'provenance': prov, 'output': result['output']}))
                artifact_path = root/'artifacts'/(result['accepted_artifact_id']+'.json')
                result['new_accepted_outputs'] = int(not artifact_path.exists())
                if not artifact_path.exists():
                    atomic_json(artifact_path, {'provenance': prov, 'result': result})
                entry = {'key': key, 'provenance': prov, 'result': result,
                         'result_sha256': digest(canonical(result))}
                atomic_json(path, entry)
            else:
                atomic_json(attempt_path, {'provenance': prov, 'result': result,
                                           'completed_ns': time.time_ns()})
        result.update(cache_key=key, cache_invalidation=invalidation,
                      elapsed_seconds=time.monotonic()-started)
        receipt_id = str(uuid.uuid4())
        result['receipt_id'] = receipt_id
        result['receipt_path'] = str(root/'receipts'/(receipt_id+'.json'))
        atomic_json(Path(result['receipt_path']), {'provenance': prov, 'result': result})
        return result
