"""Model/tool loop for a protected, attempt-bound Stokowski tool executor."""

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import time

from stokowski_cloudflare_client import WorkersAIClient, WorkersAIRequestError


@dataclass(frozen=True)
class Attempt:
    project: str
    id: str
    review_of: str | None = None
    reviewer_project: str | None = None


def repository_tools(workspace, tracked_paths, write_roots):
    """Expose only bounded text operations on the admitted checkout."""
    workspace = Path(workspace).resolve(strict=True)
    tracked = frozenset(tracked_paths)
    definitions = {'list_files': (), 'read_file': ('path',)}
    if write_roots:
        definitions['replace_text'] = ('path', 'old', 'replacement')
    tools = [
        {'type': 'function', 'function': {'name': name, 'parameters': {
            'type': 'object', 'properties': {key: {'type': 'string'} for key in keys},
            'required': list(keys), 'additionalProperties': False}}}
        for name, keys in definitions.items()
    ]

    def execute(name, arguments, remaining):
        if set(arguments) != set(definitions[name]) or not all(
                isinstance(value, str) for value in arguments.values()):
            raise WorkersAIRequestError('Invalid workspace tool arguments')
        if name == 'list_files':
            return '\n'.join(sorted(tracked))[:8000]
        relative = arguments['path']
        path = workspace / relative
        if relative not in tracked or path.resolve(strict=True) != path or not path.is_file():
            raise WorkersAIRequestError('Workspace file is outside the tracked scope')
        stat = path.stat()
        if stat.st_nlink != 1 or stat.st_size > 24_000:
            raise WorkersAIRequestError('Workspace file exceeds the tool size limit')
        content = path.read_text(encoding='utf-8')
        if name == 'read_file':
            return content
        if not any(relative == root or relative.startswith(root + '/') for root in write_roots):
            raise WorkersAIRequestError('Workspace file is outside the write scope')
        old = arguments['old']
        if not old or content.count(old) != 1:
            raise WorkersAIRequestError('Edit requires one unambiguous match')
        updated = content.replace(old, arguments['replacement'], 1)
        if len(updated.encode()) > 24_000:
            raise WorkersAIRequestError('Updated file exceeds the tool size limit')
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            staged = Path(stream.name)
            try:
                os.fchmod(stream.fileno(), stat.st_mode & 0o777)
                stream.write(updated)
                stream.flush()
                os.fsync(stream.fileno())
                staged.replace(path)
            finally:
                staged.unlink(missing_ok=True)
        return 'Updated tracked file'

    return tools, execute


def run_turn(client: WorkersAIClient, attempt: Attempt, prompt: str, *,
             tools: list[dict], execute_tool, active_projects, cancelled, timeout: int) -> str:
    """Execute only the tools that the protected owner bound to this attempt.

    The executor enforces workspace scope and applies the attempt's separate
    review or implementation authority. Tool arguments never select it.
    """
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError('Invalid turn timeout')
    tool_names = {tool['function']['name'] for tool in tools}
    messages = [{'role': 'user', 'content': prompt}]
    deadline = time.monotonic() + timeout
    for ordinal in range(1, 25):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or cancelled():
            raise WorkersAIRequestError('Workers AI turn stopped before completion')
        request_id = sha256(f'{attempt.id}:{ordinal}'.encode()).hexdigest()
        result = client.complete(
            project=attempt.project, attempt_id=attempt.id, request_id=request_id,
            active_projects=active_projects(), messages=messages, tools=tools,
            timeout=remaining, review_of=attempt.review_of, reviewer_project=attempt.reviewer_project)
        if cancelled() or time.monotonic() >= deadline or attempt.project not in active_projects():
            raise WorkersAIRequestError('Workers AI turn stopped before applying a response')

        choices = result.get('choices')
        message = choices[0]['message'] if choices else result
        content = message.get('content', message.get('response'))
        calls = message.get('tool_calls') or []
        if not calls:
            if not isinstance(content, str) or not content.strip():
                raise WorkersAIRequestError('Workers AI did not return a final message')
            return content

        messages.append({'role': 'assistant', 'content': content or '', 'tool_calls': calls})
        seen = set()
        for call in calls:
            function = call['function']
            name = function['name']
            call_id = call['id']
            args = function['arguments']
            if isinstance(args, str):
                args = json.loads(args)
            if (name not in tool_names or not isinstance(args, dict)
                    or not isinstance(call_id, str) or not call_id or call_id in seen):
                raise WorkersAIRequestError('Invalid or unapproved Workers AI tool call')
            seen.add(call_id)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or cancelled() or attempt.project not in active_projects():
                raise WorkersAIRequestError('Workers AI turn stopped before executing a tool')
            output = execute_tool(name, args, remaining)
            if not isinstance(output, str) or len(output.encode()) > 32_000:
                raise WorkersAIRequestError('Workspace tool response exceeded its text boundary')
            messages.append({'role': 'tool', 'tool_call_id': call_id, 'content': output})
    raise WorkersAIRequestError('Workers AI turn exhausted its request limit')
