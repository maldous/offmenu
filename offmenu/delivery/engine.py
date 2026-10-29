"""One cooperative writer, durable graph state, and explicit effect reconciliation.

Task files are reviewed executable code, not untrusted prompts. This runner is
not a sandbox. Checkpoints and logs are local private data, not backups.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import time
from typing import TypedDict
import uuid

from .standards import check, discover, git, tracked

ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')


class DeliveryError(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def atomic(path, value):
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with open(tmp, 'x', encoding='utf8') as stream:
        os.chmod(tmp, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load_task(path):
    task = json.loads(Path(path).read_text())
    if task.get('version') != 1 or not ID.fullmatch(task.get('id', '')):
        raise DeliveryError('Invalid task version/id')
    if not task.get('owner') or not task.get('purpose'):
        raise DeliveryError('Task owner and purpose are required')
    if not re.fullmatch(r'[0-9a-f]{40}', task.get('base_revision', '')):
        raise DeliveryError('Immutable base_revision is required')
    if not task.get('checks') or len(task['checks']) > 32:
        raise DeliveryError('Require 1..32 checks')
    ids = set()
    for step in task['checks']:
        if not ID.fullmatch(step.get('id', '')) or step['id'] in ids:
            raise DeliveryError('Invalid/duplicate check id')
        ids.add(step['id'])
        if not step.get('argv') or not all(isinstance(x, str) for x in step['argv']):
            raise DeliveryError('argv must be a nonempty string list')
        if not 1 <= step.get('timeout', 60) <= 600:
            raise DeliveryError('Timeout must be 1..600 seconds')
        if not 1 <= step.get('attempts', 1) <= 3:
            raise DeliveryError('Attempts must be 1..3')
        if step.get('attempts', 1) > 1 and not step.get('retry_safe', False):
            raise DeliveryError('Retry requires explicit retry_safe declaration')
    if not task.get('accepted_outputs'):
        raise DeliveryError('Explicit accepted output hashes are required')
    for path, sha in task['accepted_outputs'].items():
        if Path(path).is_absolute() or '..' in Path(path).parts or not re.fullmatch('[0-9a-f]{64}', sha):
            raise DeliveryError('Invalid accepted output path/hash')
    return task


@contextmanager
def writer(root, reconciliation=False):
    directory = root / '.delivery'
    directory.mkdir(mode=0o700, exist_ok=True)
    with open(directory / 'writer.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DeliveryError('busy: another delivery writer owns this checkout') from exc
        if not reconciliation:
            for receipt in directory.glob('*/*.json'):
                record = json.loads(receipt.read_text())
                if 'argv_sha256' in record and record.get('status') in {
                        'running', 'uncertain', 'timed_out', 'cancelled'}:
                    raise DeliveryError('blocked_reconciliation: unresolved command in ' + receipt.parent.name)
        yield directory


def verify_outputs(root, task):
    result = {}
    for name, expected in task['accepted_outputs'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise DeliveryError('Accepted output missing/outside checkout: ' + name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise DeliveryError('Accepted output hash mismatch: ' + name)
        result[name] = actual
    return result


class State(TypedDict, total=False):
    task: dict
    discovery: dict
    standards: dict
    checks: dict
    outputs: dict
    status: str


class Engine:
    def __init__(self, root, directory, task):
        self.root = root
        self.task = task
        self.directory = directory / task['id']
        self.directory.mkdir(mode=0o700, exist_ok=True)
        binding = self.directory / 'binding.json'
        value = {'task_sha256': digest(task), 'root': str(root), 'owner': task['owner'],
                 'source_sha256': self.source_digest()}
        if binding.exists() and json.loads(binding.read_text()) != value:
            raise DeliveryError('Task ID already bound to different input/owner/root')
        if not binding.exists():
            atomic(binding, value)

    def source_digest(self):
        paths = tracked(self.root)
        policy = json.loads((self.root / 'repository-standard.json').read_text())
        paths += [p for p in git(self.root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
                  if p and p not in set(policy.get('runtime_hold_paths', []))]
        values = {}
        for name in sorted(set(paths) - set(self.task['accepted_outputs'])):
            path = self.root / name
            if path.is_file():
                values[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest(values)

    def verify_source(self):
        binding = json.loads((self.directory / 'binding.json').read_text())
        if self.source_digest() != binding['source_sha256']:
            raise DeliveryError('Source changed: cached checks cannot be reused')
        if git(self.root, 'rev-parse', 'HEAD') != self.task['base_revision']:
            raise DeliveryError('Revision changed: cached checks cannot be reused')
        if not git(self.root, 'branch', '--show-current').startswith(('feature/', 'bugfix/')):
            raise DeliveryError('Delivery requires a feature/ or bugfix/ branch')

    def event(self, name, detail):
        # Each event is immutable; private logs are never copied into receipts.
        atomic(self.directory / f'event-{time.time_ns()}-{uuid.uuid4().hex}.json',
               {'event': name, 'at': time.time(), 'task_sha256': digest(self.task), **detail})

    def cancelled(self):
        if (self.directory / 'cancel.json').exists():
            raise DeliveryError('cancelled: stop requested; inspect partial effects before retry')

    def discovery(self, state):
        self.cancelled()
        actual = git(self.root, 'rev-parse', 'HEAD')
        if actual != self.task['base_revision']:
            raise DeliveryError('Revision changed: create a reviewed new task, not a relabelled retry')
        branch = git(self.root, 'branch', '--show-current')
        if not branch.startswith(('feature/', 'bugfix/')):
            raise DeliveryError('Delivery requires a feature/ or bugfix/ branch')
        result = discover(self.root)
        self.event('discovered', {'revision': actual, 'tracked_files': result['tracked_files']})
        return {'discovery': result, 'status': 'discovered'}

    def standards(self, state):
        self.cancelled()
        result = check(self.root)
        if result['status'] != 'passed':
            raise DeliveryError('Repository standard failed; run discover/check for exact violations')
        self.event('standards-verified', {'version': result['standard_version']})
        return {'standards': result}

    def execute(self, state):
        self.verify_source()
        receipts = {}
        for step in self.task['checks']:
            self.cancelled()
            receipt_path = self.directory / (step['id'] + '.json')
            previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
            if previous and previous['status'] == 'succeeded':
                receipts[step['id']] = previous
                continue
            if previous and previous['status'] in {'running', 'uncertain', 'timed_out', 'cancelled'}:
                raise DeliveryError('blocked_reconciliation: ' + step['id'])
            attempts_done = previous['attempt'] if previous else 0
            max_attempts = step.get('attempts', 1)
            if attempts_done >= max_attempts:
                raise DeliveryError('Check attempts exhausted: ' + step['id'])
            for attempt in range(attempts_done + 1, max_attempts + 1):
                record = {'check': step['id'], 'status': 'running', 'attempt': attempt,
                          'argv_sha256': digest(step['argv']), 'started_at': time.time()}
                atomic(receipt_path, record)
                self.event('check-started', {'check': step['id'], 'attempt': attempt})
                env = {**os.environ, 'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}
                log = self.directory / (step['id'] + f'-{attempt}.log')
                # Use a pipe and drain into a bounded log; never retain unlimited output.
                proc = subprocess.Popen(step['argv'], cwd=self.root, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                import selectors
                selector = selectors.DefaultSelector()
                selector.register(proc.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + step.get('timeout', 60)
                reason = None
                size = 0
                try:
                    with open(log, 'wb') as stream:
                        os.chmod(log, 0o600)
                        while True:
                            if (self.directory / 'cancel.json').exists():
                                reason = 'cancelled'
                            elif time.monotonic() >= deadline:
                                reason = 'timed_out'
                            if reason:
                                os.killpg(proc.pid, signal.SIGKILL)
                                break
                            for key, _ in selector.select(timeout=0.1):
                                chunk = os.read(key.fileobj.fileno(), 65536)
                                if chunk:
                                    stream.write(chunk[:max(0, 1048576 - size)])
                                    size += len(chunk)
                                else:
                                    selector.unregister(key.fileobj)
                            if proc.poll() is not None and not selector.get_map():
                                break
                    proc.wait()
                finally:
                    selector.close()
                    proc.stdout.close()
                    # Stop same-process-group descendants even after leader exit.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                record.update(status=reason or ('succeeded' if proc.returncode == 0 else 'failed'),
                              returncode=proc.returncode, ended_at=time.time(),
                              log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                              log_truncated=size > 1048576)
                atomic(receipt_path, record)
                self.event('check-finished', {'check': step['id'], 'status': record['status']})
                if record['status'] == 'succeeded':
                    receipts[step['id']] = record
                    break
                if reason or attempt == max_attempts:
                    raise DeliveryError('Check ' + record['status'] + ': ' + step['id'])
        return {'checks': receipts, 'status': 'checked'}

    def verify(self, state):
        self.cancelled()
        self.verify_source()
        if git(self.root, 'rev-parse', 'HEAD') != self.task['base_revision']:
            raise DeliveryError('Revision drift during execution')
        outputs = verify_outputs(self.root, self.task)
        return {'outputs': outputs}

    def accept(self, state):
        self.cancelled()
        self.verify_source()
        outputs = verify_outputs(self.root, self.task)
        record = {'status': 'accepted', 'task_id': self.task['id'], 'owner': self.task['owner'],
                  'revision': self.task['base_revision'], 'task_sha256': digest(self.task),
                  'standard_version': state['standards']['standard_version'],
                  'outputs': outputs, 'checks': list(state['checks']), 'at': time.time()}
        atomic(self.directory / 'accepted.json', record)
        self.event('accepted', {'outputs': len(outputs)})
        return {'status': 'accepted'}

    def run(self, pause_after=None):
        self.verify_source()
        # LangChain integrations are available via langchain-core, but discovery
        # is deterministic and needs no paid model or telemetry.
        os.environ['LANGCHAIN_TRACING_V2'] = 'false'
        os.environ['LANGSMITH_TRACING'] = 'false'
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.sqlite import SqliteSaver
        graph = StateGraph(State)
        names = ['discovery', 'standards', 'execute', 'verify', 'accept']
        for name in names:
            graph.add_node(name, getattr(self, name))
        for source, target in zip([START, *names], [*names, END]):
            graph.add_edge(source, target)
        with SqliteSaver.from_conn_string(str(self.directory / 'graph.sqlite')) as saver:
            compiled = graph.compile(checkpointer=saver,
                                     interrupt_after=[pause_after] if pause_after else [])
            config = {'configurable': {'thread_id': self.task['id']}, 'recursion_limit': 16}
            prior = compiled.get_state(config)
            if prior.values.get('status') == 'accepted' and not prior.next:
                # Accepted receipts never excuse changed output bytes.
                verify_outputs(self.root, self.task)
                return json.loads((self.directory / 'accepted.json').read_text())
            self.cancelled()
            result = compiled.invoke(None if prior.values else {'task': self.task}, config)
            snapshot = compiled.get_state(config)
            return {'task_id': self.task['id'], 'status': result.get('status'),
                    'next': list(snapshot.next), 'task_sha256': digest(self.task)}
