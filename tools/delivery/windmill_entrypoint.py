"""On-demand Windmill entrypoint; no schedules or provider credentials.

Deploy only after source review. Requires a worker-local approved checkout and
its preinstalled delivery environment; MCP authentication is never forwarded.
Windmill must run this on the same host/mount as the checkout/checkpoints.
"""
# requirements:
# langgraph==1.2.18
# langgraph-checkpoint-sqlite==3.1.2

import json

CHECKOUT_ROOT = '/offmenu'
from pathlib import Path


def main(task_path: str, action: str = 'status') -> dict:
    from offmenu.delivery.engine import DeliveryError, Engine, digest, load_task, writer
    root = Path(CHECKOUT_ROOT).resolve()
    task_file = (root / task_path).resolve()
    approved = [root / 'tools' / 'delivery', root / '.delivery']
    if not any(task_file.is_relative_to(p) for p in approved) or task_file.suffix != '.json':
        raise ValueError('Only reviewed delivery task files are allowed')
    task = load_task(task_file)
    if action == 'status':
        directory = root / '.delivery' / task['id']
        binding = directory / 'binding.json'
        if binding.exists() and json.loads(binding.read_text())['task_sha256'] != digest(task):
            raise DeliveryError('Task binding mismatch')
        receipt = directory / 'accepted.json'
        return json.loads(receipt.read_text()) if receipt.exists() else {'status': 'not_accepted'}
    if action != 'run':
        raise ValueError('Only on-demand run/status are supported; cancellation is local CLI')
    with writer(root) as state:
        result = Engine(root, state, task).run()
    if result.get('status') != 'accepted':
        raise DeliveryError('Delivery not accepted')
    return result
