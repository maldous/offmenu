"""Protected provider selection shared by the coordinator and coding worker."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import time

from coding_child_launch import trusted_file
from stokowski_cloudflare_budget import PROJECTS, ProjectAccountRouter
from stokowski_cloudflare_client import MODEL, WorkersAIClient
from symphony_capacity import AdmissionError


POLICY = Path('/etc/offmenu/stokowski-cloudflare.json')
SECRETS = Path('/etc/offmenu/stokowski-cloudflare')
CODEX = 'codex-chatgpt'
CLOUDFLARE = 'cloudflare-workers-ai'
PROJECT_NAMES = {
    'ce60c1ab-a732-4a71-8471-14c9dc393886': 'OffMenu',
    'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0': 'UIF',
}


@dataclass(frozen=True)
class Provider:
    proof: dict
    cloudflare_policy: dict | None = None

    @property
    def route(self):
        return self.proof.get('route')

    def require_active(self, project_id):
        if self.route == CLOUDFLARE and PROJECT_NAMES.get(project_id) not in self.cloudflare_policy['active_projects']:
            raise AdmissionError('cloudflare_project_paused_or_unconfigured')

    def active_projects(self):
        config = load_policy()
        if (not config or config['mode'] == 'codex'
                or config['accounts'] != self.cloudflare_policy['accounts']
                or config.get('review_accounts') != self.cloudflare_policy.get('review_accounts')):
            return set()
        return set(config['active_projects'])


def load_policy():
    if not POLICY.exists():
        return None
    config = json.loads(trusted_file(POLICY).read_text())
    if (not isinstance(config, dict)
            or set(config) - {'mode', 'accounts', 'active_projects', 'review_accounts'}
            or not {'mode', 'accounts', 'active_projects'} <= set(config)
            or config['mode'] not in {'cloudflare', 'both', 'codex'}
            or not isinstance(config['accounts'], dict)
            or set(config['accounts']) != PROJECTS
            or not all(isinstance(account, str) and re.fullmatch('[0-9a-f]{32}', account)
                       for account in config['accounts'].values())
            or len(set(config['accounts'].values())) != len(PROJECTS)
            or not isinstance(config['active_projects'], list)
            or not all(isinstance(project, str) and project in PROJECTS
                       for project in config['active_projects'])
            or not isinstance(config.get('review_accounts', {}), dict)
            or not all(owner and isinstance(project, str) and project in PROJECTS
                       for owner, project in config.get('review_accounts', {}).items())):
        raise AdmissionError('invalid_stokowski_provider_policy')
    return config


def select_provider(proof, capacity):
    """Use the existing reviewed Codex proof, or Free Workers AI if enabled."""
    config = load_policy()
    if config is None or config['mode'] == 'codex':
        if proof.get('route') == CLOUDFLARE:
            raise AdmissionError('cloudflare_provider_disabled')
        return Provider(proof)
    now = time.time()
    checked = proof.get('checked_at')
    if (config['mode'] == 'both' and proof.get('route') == CODEX
            and proof.get('available') is True and type(checked) in {int, float}
            and 0 <= now - checked <= capacity['symphony']['provider_proof_ttl_seconds']):
        return Provider(proof)
    return Provider({
        'route': CLOUDFLARE, 'available': True, 'checked_at': now,
        'requested_model': MODEL,
        'session_ceiling': capacity['symphony']['provider_session_ceiling'],
    }, config)


def prepare_provider_proof(model, ceiling):
    """Skip even the Codex readiness probe in Cloudflare-only mode."""
    config = load_policy()
    capacity = {'symphony': {'provider_session_ceiling': ceiling, 'provider_proof_ttl_seconds': 60}}
    if config and (config['mode'] == 'cloudflare' or model == MODEL):
        if config['mode'] == 'codex':
            raise AdmissionError('cloudflare_provider_disabled')
        return select_provider({}, capacity).proof
    from symphony_launch import provider_proof
    try:
        proof = provider_proof(model, ceiling)
    except (OSError, subprocess.TimeoutExpired):
        if not config or config['mode'] != 'both':
            raise
        proof = {}
    return select_provider(proof, capacity).proof


def cloudflare_client(provider, pool_path):
    """Pass an account-bound credential only to the HTTPS client."""
    config = provider.cloudflare_policy
    accounts = config['accounts']
    router = ProjectAccountRouter(Path(pool_path) / 'workers-ai.sqlite', accounts)

    def credential(account_id):
        name = next(project for project, account in accounts.items() if account == account_id)
        record = json.loads(trusted_file(SECRETS / (name + '.json'), 0o640).read_text())
        if (not isinstance(record, dict) or set(record) != {'account_id', 'plan', 'token'}
                or (record['account_id'], record['plan']) != (account_id, 'free')):
            raise ValueError('Invalid Workers AI credential binding')
        return record['token']

    return WorkersAIClient(router, credential)
