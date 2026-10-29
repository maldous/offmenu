#!/usr/bin/env python3
"""Verify an existing tracker credential can read only the selected project.

Use existing environment or a systemd-injected credential directory. Never copy
credentials into the checkout, command line, output, or source configuration.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-id', default='ce60c1ab-a732-4a71-8471-14c9dc393886')
    args = parser.parse_args()
    key = os.environ.get('OFFMENU_LINEAR_API_KEY') or os.environ.get('LINEAR_API_KEY')
    if not key and os.environ.get('CREDENTIALS_DIRECTORY'):
        key = (Path(os.environ['CREDENTIALS_DIRECTORY']) / 'linear-api-key').read_text().strip()
    if not key:
        print(json.dumps({'status': 'credential_not_injected'}))
        return 2
    payload = {'query': 'query($id: String!) { project(id: $id) { id slugId name } }',
               'variables': {'id': args.project_id}}
    request = Request('https://api.linear.app/graphql', data=json.dumps(payload).encode(),
                      headers={'Authorization': key, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=15) as response:
            value = json.load(response)
        project = (value.get('data') or {}).get('project')
        passed = bool(project and project.get('id') == args.project_id)
        print(json.dumps({'status': 'passed' if passed else 'project_access_not_verified',
                          'project_id': args.project_id, 'credential_exported': False}))
        return 0 if passed else 2
    except Exception as exc:
        print(json.dumps({'status': 'probe_failed', 'error_type': type(exc).__name__,
                          'credential_exported': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
