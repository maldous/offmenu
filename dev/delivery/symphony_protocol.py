"""Bounded native Codex app-server readiness probe; never starts a thread/turn."""
import json
import os
import tempfile
import queue
import subprocess
import threading
import time

BINARY = '/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex'


def probe(binary=BINARY, timeout=25):
    state = tempfile.TemporaryDirectory(prefix='offmenu-codex-state-')
    environment = os.environ.copy()
    environment['CODEX_SQLITE_HOME'] = state.name
    from pathlib import Path
    original_home = Path(environment.get('CODEX_HOME', str(Path.home()/'.codex')))
    original_auth = original_home/'auth.json'
    if original_auth.is_file():
        (Path(state.name)/'auth.json').symlink_to(original_auth)
        environment['CODEX_HOME'] = state.name
    process = subprocess.Popen([binary, 'app-server'], env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    messages = queue.Queue()
    def receive():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        messages.put(None)
    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    sequence = 0
    stage = "initialize"
    def request(method, params):
        nonlocal sequence, stage
        stage = method
        sequence += 1
        process.stdin.write(json.dumps({'id': sequence, 'method': method, 'params': params}) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            message = messages.get(timeout=max(0.01, deadline-time.monotonic()))
            if message is None:
                raise RuntimeError('app-server closed before response')
            if message.get('id') == sequence:
                if 'error' in message:
                    return {'probe_error': True, 'error_code': message['error'].get('code'), 'method_unavailable': 'not supported' in message['error'].get('message', '').lower() or 'unknown' in message['error'].get('message', '').lower(), 'login_required': 'login' in message['error'].get('message', '').lower() or 'auth' in message['error'].get('message', '').lower()}
                return message.get('result', {})
            if time.monotonic() >= deadline:
                raise TimeoutError('app-server probe timed out')
    try:
        initialized = request('initialize', {'clientInfo': {'name': 'offmenu-readiness', 'version': '1.0.0'}, 'capabilities': {'experimentalApi': True}})
        if initialized.get('probe_error'):
            return {'initialized': False, 'model_calls': False}
        process.stdin.write(json.dumps({'method': 'initialized', 'params': {}})+'\n')
        process.stdin.flush()
        account = request('account/read', {'refreshToken': False})
        models = request('model/list', {'limit': 100})
        quotas = request('account/rateLimits/read', {})
        identity = account.get('account') or {}
        return {'initialized': True, 'account_type': identity.get('type'), 'plan_type': identity.get('planType'), 'authentication_required': account.get('requiresOpenaiAuth'), 'models': [{'id': m.get('id'), 'is_default': m.get('isDefault', False), 'reasoning_efforts': [e.get('reasoningEffort') for e in m.get('supportedReasoningEfforts', [])]} for m in models.get('data', [])], 'quota_response_present': not quotas.get('probe_error') and bool(quotas), 'account_probe_error': bool(account.get('probe_error')), 'account_error_code': account.get('error_code'), 'account_method_unavailable': account.get('method_unavailable'), 'account_login_required': account.get('login_required'), 'model_probe_error': bool(models.get('probe_error')), 'quota_probe_error': bool(quotas.get('probe_error')), 'quota_error_code': quotas.get('error_code'), 'quota_method_unavailable': quotas.get('method_unavailable'), 'quota_login_required': quotas.get('login_required'), 'thread_started': False, 'turn_started': False, 'model_calls': False}
    except Exception as error:
        return {'probe_error_type': type(error).__name__, 'stage': stage, 'thread_started': False, 'turn_started': False, 'model_calls': False}
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        process.stdout.close()
        state.cleanup()


if __name__ == '__main__':
    try:
        print(json.dumps(probe()))
    except Exception as error:
        print(json.dumps({'probe_error_type': type(error).__name__, 'model_calls': False}))
        raise SystemExit(2)
