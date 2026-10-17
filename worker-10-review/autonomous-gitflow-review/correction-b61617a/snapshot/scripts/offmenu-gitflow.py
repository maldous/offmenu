#!/usr/bin/env python3
"""Local managed Gitflow gates; no push, reset, rebase, worktree removal or certification."""
import argparse
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4


class GateError(Exception):
    pass


def need(condition, message):
    if not condition:
        raise GateError(message)


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def git_environment():
    # Bind child Git commands to --repo/-C, never inherited alternate custody.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    return env


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Gitflow:
    def __init__(self, repo, policy, evidence):
        self.repo = Path(repo).resolve()
        self.policy_path = Path(policy).resolve()
        self.policy = json.loads(self.policy_path.read_text())
        need(isinstance(self.policy, dict), 'policy must be a JSON object')
        self.evidence = Path(evidence).resolve()
        need(not self.evidence.is_relative_to(self.repo), 'receipts must be outside the tracked worker checkout')
        self.receipt = {'schema': 'offmenu-gitflow-receipt/1', 'utc': utc(),
                        'repo': str(self.repo), 'policy_sha256': digest(self.policy_path),
                        'fetches': [], 'status': 'blocked'}

    def git(self, *args, check=True):
        env = git_environment()
        try:
            p = subprocess.run(['git', '-C', str(self.repo), *args], env=env,
                               text=True, capture_output=True, timeout=45)
        except subprocess.TimeoutExpired as e:
            raise GateError('Git command timed out; no successful fetch receipt') from e
        if check:
            need(p.returncode == 0, f'git {args[0]} failed ({p.returncode}): {p.stderr.strip()}')
        return p

    def sha(self, ref):
        value = self.git('rev-parse', '--verify', ref + '^{commit}').stdout.strip()
        need(bool(re.fullmatch(r'[0-9a-f]{40}', value)), 'expected full immutable SHA')
        return value

    def ancestor(self, a, b):
        return self.git('merge-base', '--is-ancestor', a, b, check=False).returncode == 0

    def clean(self):
        status = self.git('status', '--porcelain=v1', '--untracked-files=all').stdout
        need(not status, 'dirty or untracked custody: preserve evidence and clean explicitly before proceeding')

    def proof(self, value):
        need(isinstance(value, dict), 'missing preserved evidence reference')
        need(isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str)
             and re.fullmatch(r'[0-9a-f]{64}', value['sha256']), 'malformed evidence path/digest')
        path = Path(value['path'])
        need(path.is_absolute() and path.is_file(), 'evidence must be an existing absolute file')
        need(digest(path) == value.get('sha256'), 'evidence digest mismatch')

    def verdict(self, record, **exact):
        need(isinstance(record, dict), 'missing Morgan verdict')
        need(record.get('reviewer') == 'Morgan' and record.get('verdict') == 'accepted',
             'Morgan accepted verdict required')
        need(record.get('qualification') == 'qualified', 'unqualified baseline/candidate')
        try:
            need(isinstance(record.get('utc'), str), 'verdict UTC must be text')
            stamp = datetime.fromisoformat(record['utc'].replace('Z', '+00:00'))
            need(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc), 'invalid verdict UTC')
        except (KeyError, ValueError, TypeError) as e:
            raise GateError('verdict requires a valid UTC receipt') from e
        for key, val in exact.items():
            need(record.get(key) == val, f'Morgan verdict does not match exact {key}')
        self.proof(record.get('evidence'))

    def context(self, worker):
        p = self.policy
        need(p.get('evidence_dir') == str(self.evidence), 'use the canonical preserved receipt directory')
        need(p.get('schema') == 'offmenu-gitflow-policy/1' and p.get('pool_limit') == 32,
             'policy schema/fixed ceiling32 required')
        need(1 <= worker <= 32, 'worker outside fixed ceiling32')
        common = Path(self.git('rev-parse', '--git-common-dir').stdout.strip())
        if not common.is_absolute():
            common = self.repo / common
        need(str(common.resolve()) == p.get('common_dir'), 'wrong repository common-dir')
        need(self.git('remote', 'get-url', 'origin').stdout.strip() == p.get('origin'),
             'canonical origin mismatch')
        w = p.get('workers', {}).get(str(worker), {})
        need(w.get('path') == str(self.repo), 'must use the SAME registered permanent worker path')
        inventory = self.git('worktree', 'list', '--porcelain').stdout
        need(f'worktree {self.repo}\n' in inventory, 'worker path is not registered')
        need(w.get('owner') and w.get('custody') == 'clear', 'ambiguous or outstanding custody')
        self.proof(w.get('evidence'))
        for field in ('open_prs', 'recovery_dependencies', 'evidence_dependencies'):
            need(w.get(field) == [], f'outstanding or unspecified {field}')
        self.clean()
        self.receipt['worker'] = worker
        self.receipt['owner'] = w['owner']
        self.receipt['head_before'] = self.sha('HEAD')
        return w

    def fetch(self, line):
        need(line in ('develop', 'main'), 'unsupported canonical line')
        command = ['fetch', '--no-tags', '--no-write-fetch-head', 'origin',
                   f'refs/heads/{line}:refs/remotes/origin/{line}']
        # Disposable local bare origins get a per-origin lock, keeping fixtures
        # out of the real pool's fetch coordination. Network origin uses the
        # fixed shared OffMenu lock, with no environment/policy override.
        origin_path = Path(self.policy.get('origin', ''))
        lock_path = origin_path / 'offmenu-fetch.lock' if (origin_path.is_absolute()
            and (origin_path / 'HEAD').is_file() and (origin_path / 'objects').is_dir()) else Path('/tmp/offmenu-develop-fetch.lock')
        r = {'command': ['git', *command], 'started_utc': utc(), 'line': line,
             'lock': str(lock_path), 'exit_code': None, 'sha': None}
        self.receipt['fetches'].append(r)
        with Path(r['lock']).open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise GateError('shared canonical fetch lock is busy; no cached-base fallback') from e
            try:
                p = self.git(*command, check=False)
            except GateError:
                r.update(completed_utc=utc(), error='timeout; exit unavailable')
                raise
            r.update(exit_code=p.returncode, completed_utc=utc(), stdout=p.stdout, stderr=p.stderr)
            need(p.returncode == 0, f'canonical {line} fetch failed ({p.returncode}): {p.stderr.strip()}')
            # Capture the explicitly fetched tracking line while holding the shared
            # lock. Never rely on the shared FETCH_HEAD or a cached local branch.
            sha = self.sha(f'refs/remotes/origin/{line}')
            r['sha'] = sha
            return sha

    def routine_authority(self):
        authority = self.policy.get('routine_delivery', {})
        need(authority.get('authorizer') == 'Matt'
             and authority.get('scope') == 'normal-qualified-gitflow'
             and authority.get('project') == 'OffMenu', 'Matt routine Gitflow authority required')
        self.proof(authority.get('evidence'))
        self.receipt['routine_authority'] = authority

    def delivery(self, a):
        self.context(a.worker)
        self.routine_authority()
        snapshot_path = Path(a.snapshot)
        snapshot = json.loads(snapshot_path.read_text())
        need(isinstance(snapshot, dict), 'PR snapshot must be a JSON object')
        self.receipt['snapshot_sha256'] = digest(snapshot_path)
        need(snapshot.get('base_ref') == 'develop' and snapshot.get('state') == 'open',
             'routine delivery requires an open develop PR; historical merge is not a new approval')
        head, base = snapshot.get('head'), snapshot.get('base')
        need(head == a.head == self.sha(a.head) and base == a.base == self.sha(a.base),
             'PR head/base differs from exact immutable candidate')
        head_ref = snapshot.get('head_ref', '')
        need(self.git('check-ref-format', 'refs/heads/' + head_ref, check=False).returncode == 0, 'explicit PR head ref required')
        remote = self.git('ls-remote', '--exit-code', '--heads', 'origin', 'refs/heads/' + head_ref, check=False)
        need(remote.returncode == 0 and remote.stdout.split() == [head, 'refs/heads/' + head_ref],
             'live PR head changed or unavailable; collect a fresh snapshot')
        self.receipt['live_head_readback'] = remote.stdout
        current = self.fetch('develop')
        need(current == base, 'develop advanced; reconcile and review a new exact candidate')
        need(self.ancestor(base, head), 'candidate must contain freshly fetched develop')
        review = snapshot.get('independent_review', {})
        need(isinstance(review, dict), 'independent review must be a JSON object')
        need(review.get('state') == 'passed' and review.get('head') == head and review.get('base') == base
             and review.get('reviewer') and review.get('reviewer') != snapshot.get('owner'),
             'independent review of exact head/base is pending or stale')
        self.proof(review.get('evidence'))
        self.exact_review('deliver-develop', head, base, head)
        if snapshot.get('requirements_status') != 'known':
            controls = self.policy.get('client_enforcement', {})
            need(snapshot.get('requirements_status') == 'origin-unavailable-client-enforced'
                 and controls.get('accepted_by') == 'Matt' and controls.get('origin_protection') == 'unavailable'
                 and controls.get('bypassable_outside_workflow') is True,
                 'platform requirements unavailable without explicit Matt client-enforcement authority')
            self.proof(controls.get('evidence'))
            self.receipt['enforcement'] = controls
            self.receipt['origin_protected'] = False
        for field in ('required_reviews', 'required_checks', 'advisory_reviews'):
            need(isinstance(snapshot.get(field), list) and all(isinstance(x, dict) for x in snapshot[field]),
                 f'explicit {field} list of objects required')
        for r in snapshot['required_reviews']:
            need(r.get('head') == head and r.get('state') == 'APPROVED', 'required review pending/failed/stale')
        for c in snapshot['required_checks']:
            need(c.get('head') == head and c.get('status') == 'completed' and c.get('conclusion') == 'success',
                 'required check pending/failed/stale')
        advisory = snapshot['advisory_reviews']
        need(all(r.get('open_findings') == 0 for r in advisory), 'known later findings require normal correction and re-review')
        self.receipt['advisory_disclosures'] = advisory
        need(isinstance(snapshot.get('security_alerts'), list), 'explicit security alert inventory required')
        if snapshot['security_alerts']:
            security = snapshot.get('security_confirmation', {})
            need(security.get('state') == 'confirmed' and security.get('head') == head
                 and security.get('base') == base, 'mandatory security disposition pending/stale')
            self.proof(security.get('evidence'))
            self.receipt['security_confirmation'] = security
        confirmation = snapshot.get('platform_confirmation', {})
        need(confirmation.get('state') == 'confirmed' and confirmation.get('head') == head
             and confirmation.get('base') == base, 'mandatory platform confirmation pending/stale')
        self.proof(confirmation.get('evidence'))
        self.receipt.update(candidate=head, base=base, source_branch=head_ref, pr=snapshot.get('url'),
                            next_action='normal provider merge with expected head; re-read exact base immediately before call',
                            meaning='preflight allowed only; no PR creation/push/merge performed')
        return 'allowed'

    def merge_receipt(self, a):
        self.context(a.worker)
        self.routine_authority()
        preflight_path = Path(a.preflight).resolve()
        need(preflight_path.parent == self.evidence, 'retain the actual pre-merge gate in canonical receipts')
        gate = json.loads(preflight_path.read_text())
        need(isinstance(gate, dict), 'preflight must be a JSON object')
        need(gate.get('schema') == 'offmenu-gitflow-receipt/1' and gate.get('operation') == 'delivery'
             and gate.get('status') == 'allowed' and gate.get('repo') == str(self.repo),
             'actual allowed pre-merge gate required; never fabricate historical approval')
        snapshot = json.loads(Path(a.snapshot).read_text())
        need(isinstance(snapshot, dict), 'merge snapshot must be a JSON object')
        head, base, merged = snapshot.get('head'), snapshot.get('base'), snapshot.get('merge_sha')
        need(snapshot.get('state') == 'merged' and snapshot.get('base_ref') == 'develop'
             and snapshot.get('url') == gate.get('pr') and snapshot.get('normal_merge') is True
             and snapshot.get('head_ref') == gate.get('source_branch'),
             'actual normal merged develop PR required')
        need(head == gate.get('candidate') and base == gate.get('base'), 'merged head/base differs from preflight')
        self.proof(snapshot.get('provider_evidence'))
        try:
            merge_time = datetime.fromisoformat(snapshot['merged_at'].replace('Z', '+00:00'))
            gate_time = datetime.fromisoformat(gate['utc'].replace('Z', '+00:00'))
            need(merge_time.tzinfo is not None and gate_time <= merge_time <= datetime.now(timezone.utc),
                 'preflight must precede actual merge; no posthoc acceptance')
        except (KeyError, ValueError, TypeError) as e:
            raise GateError('normal merge UTC evidence required') from e
        self.exact_review('deliver-develop', head, base, head)
        current = self.fetch('develop')
        need(merged == self.sha(merged) and self.ancestor(merged, current), 'normal merge absent from canonical develop')
        parents = self.git('show', '-s', '--format=%P', merged).stdout.strip().split()
        need(parents == [base, head], 'normal merge parents differ; preserve state and block cleanup')
        tree = self.git('show', '-s', '--format=%T', merged).stdout.strip()
        need(tree == self.git('show', '-s', '--format=%T', head).stdout.strip(),
             'merged tree differs from exact reviewed candidate; incident, no automatic reset')
        linkage = {}
        if a.ready is not None:
            ready = self.read_receipt(a.ready, 'ready')
            need(ready.get('worker') == a.worker and ready.get('candidate') == head,
                 'normal merge task readiness owner/head mismatch')
            start = self.read_receipt(ready.get('start_receipt', ''), 'start')
            self.task_ready_binding(start, ready, ready['start_receipt'], a.worker)
            need(gate.get('source_branch') == start['branch'], 'provider PR branch differs from authored source task')
            self.proof(ready.get('checks'))
            linkage = {'worker': a.worker, 'owner': start['owner'], 'repo': start['repo'],
                       'branch': start['branch'], 'source_task_start': str(Path(ready['start_receipt']).resolve()),
                       'source_task_start_sha256': digest(ready['start_receipt']),
                       'task': ready['task'], 'source': head,
                       'ready_sha256': digest(a.ready), 'ready_receipt': str(Path(a.ready).resolve())}
        self.receipt.update(candidate=head, base=base, merge_sha=merged, merge_parents=parents, tree=tree,
                            merged_at=snapshot['merged_at'], preflight_receipt=str(preflight_path),
                            task_linkage=linkage,
                            preflight_sha256=digest(preflight_path), provider_evidence=snapshot['provider_evidence'],
                            meaning='normal merge witnessed; retirement still requires owner/custody/dependency/PR checks')
        return 'completed'

    def released_tag(self, record, sha):
        tag = record.get('tag', '')
        need(self.git('check-ref-format', 'refs/tags/' + tag, check=False).returncode == 0, 'invalid accepted release tag')
        need(self.sha('refs/tags/' + tag) == sha, 'accepted immutable release tag missing/mismatch')
        tag_object = self.git('rev-parse', '--verify', 'refs/tags/' + tag).stdout.strip()
        need(record.get('tag_object') == tag_object, 'accepted tag object not pinned/mismatch')
        p = self.git('ls-remote', '--exit-code', '--tags', 'origin', 'refs/tags/' + tag, 'refs/tags/' + tag + '^{}', check=False)
        self.receipt.setdefault('tag_checks', []).append({'tag': tag, 'exit_code': p.returncode,
                                                        'utc': utc(), 'stdout': p.stdout, 'stderr': p.stderr})
        need(p.returncode == 0, 'canonical accepted release tag unavailable')
        refs = dict((ref, value) for value, ref in (line.split() for line in p.stdout.splitlines()))
        need(refs.get('refs/tags/' + tag) == tag_object, 'canonical release tag object changed')
        need(refs.get('refs/tags/' + tag + '^{}', tag_object) == sha, 'canonical release tag commit mismatch')

    def baseline(self):
        b = self.policy.get('baseline', {})
        sha = b.get('sha', '')
        need(bool(re.fullmatch(r'[0-9a-f]{40}', sha)), 'no accepted release baseline')
        self.verdict(b, sha=sha)
        self.released_tag(b, sha)
        return sha

    def qualified(self, line, sha):
        baseline = self.baseline()
        self.verdict(self.policy.get('lines', {}).get(line), sha=sha, line=line)
        need(self.ancestor(baseline, sha), 'canonical line does not descend from accepted baseline')
        if line == 'main':
            release = self.policy.get('released_main', {})
            self.verdict(release, sha=sha)
            self.released_tag(release, sha)

    def dispatch_base(self, kind, line, sha):
        if kind in ('feature', 'bugfix') and self.policy.get('routine_delivery') is not None:
            self.routine_authority()
            record = self.policy.get('routine_develop', {})
            need(record.get('reviewer') == 'Morgan' and record.get('verdict') == 'reviewed-integration-line'
                 and record.get('sha') == sha and line == 'develop',
                 'fresh develop integration-line custody is missing or stale')
            self.proof(record.get('evidence'))
            self.receipt.update(dispatch_base=sha, dispatch_qualification='reviewed-integration-line; release uncertified')
            return
        provisional = self.policy.get('provisional_bootstrap')
        if kind not in ('feature', 'bugfix') or provisional is None:
            self.qualified(line, sha)
            self.receipt['dispatch_qualification'] = 'qualified'
            return
        need(isinstance(provisional, dict), 'invalid provisional bootstrap record')
        need(line == 'develop' and self.policy.get('develop_initialized') is True,
             'provisional exception requires persistent initialized develop')
        need(provisional.get('reviewer') == 'Morgan'
             and provisional.get('authorization') == 'ordinary-development-start'
             and provisional.get('verdict') == 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE'
             and provisional.get('qualification') == 'unqualified',
             'explicit Morgan provisional development authorization required')
        need(provisional.get('line') == line and provisional.get('sha') == sha,
             'stale provisional baseline: freshly fetched develop SHA differs')
        try:
            stamp = datetime.fromisoformat(provisional['utc'].replace('Z', '+00:00'))
            need(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc), 'invalid provisional authorization UTC')
        except (KeyError, ValueError, TypeError) as e:
            raise GateError('provisional authorization requires a valid UTC receipt') from e
        self.proof(provisional.get('evidence'))
        bootstrap = json.loads(Path(provisional['evidence']['path']).read_text())
        need(bootstrap.get('schema') == 'offmenu-provisional-develop/1'
             and bootstrap.get('verdict') == 'PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE'
             and bootstrap.get('seed') == sha and bootstrap.get('localDevelop') == sha
             and bootstrap.get('fetchedDevelop') == sha,
             'provisional bootstrap receipt does not match exact dispatched SHA')
        need(bootstrap.get('releaseCertified') is False and bootstrap.get('tagCreated') is False
             and bootstrap.get('mainChanged') is False,
             'provisional bootstrap must not claim release/tag/main promotion')
        self.receipt.update(dispatch_qualification='PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE',
                            dispatch_base=sha, provisional_authorization=provisional)

    def read_receipt(self, path, operation):
        need(Path(path).resolve().parent == self.evidence, 'receipt must be retained in canonical evidence directory')
        r = json.loads(Path(path).read_text())
        need(isinstance(r, dict), 'receipt must be a JSON object')
        need(r.get('schema') == 'offmenu-gitflow-receipt/1' and r.get('operation') == operation
             and r.get('status') == 'completed' and r.get('repo') == str(self.repo),
             'missing completed receipt for this permanent worker')
        return r

    def task_start_binding(self, start, worker):
        need(start.get('worker') == worker and start.get('repo') == str(self.repo)
             and isinstance(start.get('owner'), str) and start['owner'] == self.receipt.get('owner'),
             'authored task start owner/worktree mismatch')
        task, kind = start.get('task'), start.get('kind')
        need(isinstance(task, str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', task)
             and kind in ('feature', 'bugfix', 'release', 'hotfix'), 'malformed authored task identity')
        if start.get('exception') is True:
            exception = self.policy.get('base_exceptions', {}).get(str(worker), {})
            need(isinstance(exception, dict) and exception.get('branch') == start.get('branch')
                 and exception.get('task') == task and exception.get('base') == start.get('base')
                 and exception.get('authorization') in ('Matt', 'Morgan'), 'exception authored branch custody mismatch')
            self.proof(exception.get('evidence'))
        else:
            need(start.get('branch') == f'{kind}/{worker:02d}/{task}', 'branch does not match authored source task identity')

    def task_ready_binding(self, start, ready, start_path, worker, current_task=False):
        self.task_start_binding(start, worker)
        need(all(ready.get(k) == start.get(k) for k in
                 ('worker', 'owner', 'repo', 'branch', 'task', 'kind', 'base', 'base_line')),
             'ready metadata differs from authored source task start')
        need(Path(ready.get('start_receipt', '')).resolve() == Path(start_path).resolve()
             and ready.get('start_sha256') == digest(start_path), 'canonical authored start/ready custody mismatch')
        need(self.sha('refs/heads/' + start['branch']) == ready.get('candidate'), 'authored task branch changed after readiness')
        if current_task:
            need(self.git('branch', '--show-current').stdout.strip() == start['branch']
                 and self.sha('HEAD') == ready['candidate'], 'current worktree is not on its authored task branch')

    def start(self, a):
        self.context(a.worker)
        line = 'main' if a.kind == 'hotfix' else 'develop'
        sha = self.fetch(line)
        self.dispatch_base(a.kind, line, sha)
        w = self.policy['workers'][str(a.worker)]
        need(w.get('active_task') is None, 'previous task must be reviewed/integrated/retired before reuse')
        need(bool(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', a.task)), 'invalid unique task identifier')
        branch = f'{a.kind}/{a.worker:02d}/{a.task}'
        need(self.git('check-ref-format', '--branch', branch, check=False).returncode == 0, 'invalid branch')
        need(self.git('show-ref', '--quiet', '--verify', f'refs/heads/{branch}', check=False).returncode == 1,
             'task branch already exists; never reuse/reset')
        history = [json.loads(path.read_text()) for path in self.evidence.glob('*.json')]
        starts = [r for r in history if r.get('operation') == 'start' and r.get('status') == 'completed']
        retired = {r.get('task') for r in history if r.get('operation') == 'retire' and r.get('status') == 'completed'}
        need(not any(r.get('task') == a.task for r in starts), 'task identifier already used; never reuse')
        need(not any(r.get('worker') == a.worker and r.get('task') not in retired for r in starts),
             'retained receipt history has an active task; review/integrate/retire before reuse')
        self.receipt.update(task=a.task, branch=branch, kind=a.kind, base=sha, base_line=line)
        if not a.check_only:
            # Git refuses unsafe switch; no reset, stash or forced checkout fallback.
            self.git('switch', '--no-overwrite-ignore', '-c', branch, sha)
            need(self.sha('HEAD') == sha, 'created branch SHA mismatch')
        return 'allowed' if a.check_only else 'completed'

    def exception(self, a):
        self.context(a.worker)
        exception = self.policy.get('base_exceptions', {}).get(str(a.worker), {})
        need(exception.get('authorization') in ('Matt', 'Morgan'), 'explicit preserved base exception authorization required')
        self.proof(exception.get('evidence'))
        branch = self.git('branch', '--show-current').stdout.strip()
        need(exception.get('branch') == branch and exception.get('task') == a.task, 'exception branch/task mismatch')
        base = exception.get('base', '')
        need(base == self.sha(base) and self.ancestor(base, self.sha('HEAD')), 'exception base custody mismatch')
        need(exception.get('kind') in ('feature', 'bugfix'), 'exception cannot imply released main or release qualification')
        history = [json.loads(path.read_text()) for path in self.evidence.glob('*.json')]
        need(not any(r.get('operation') == 'start' and r.get('status') == 'completed'
                     and r.get('worker') == a.worker for r in history), 'exception already recorded or worker already managed')
        need(self.policy['workers'][str(a.worker)].get('active_task') == a.task, 'exception active-task custody required')
        self.receipt.update(operation='start', task=a.task, branch=branch, kind=exception['kind'],
                            base=base, base_line='preserved-exception', exception=True,
                            qualification='unqualified-base-exception', authorization=exception['authorization'])
        return 'completed'

    def ready(self, a):
        self.context(a.worker)
        start = self.read_receipt(a.start, 'start')
        self.task_start_binding(start, a.worker)
        need(self.git('branch', '--show-current').stdout.strip() == start['branch'], 'wrong task branch')
        sha = self.sha('HEAD')
        need(self.ancestor(start['base'], sha), 'task lost original base custody')
        self.proof(json.loads(Path(a.checks).read_text()))
        self.receipt.update(task=start['task'], branch=start['branch'], candidate=sha,
                            base=start['base'], kind=start['kind'], base_line=start['base_line'], checks=json.loads(Path(a.checks).read_text()),
                            start_sha256=digest(a.start), start_receipt=str(Path(a.start).resolve()),
                            exception=start.get('exception', False),
                            dispatch_qualification=start.get('dispatch_qualification', 'unqualified-base-exception'),
                            provisional_authorization=start.get('provisional_authorization'), completion='ready_for_Morgan_review')
        return 'completed'

    def exact_review(self, operation, candidate, base, source):
        reviews = self.policy.get('reviews', [])
        need(isinstance(reviews, list) and all(isinstance(r, dict) for r in reviews),
             'reviews must be a list of JSON objects')
        matches = [r for r in reviews if
                   (r.get('operation'), r.get('candidate'), r.get('base'), r.get('source')) ==
                   (operation, candidate, base, source)]
        need(len(matches) == 1, 'one Morgan exact candidate/base/source verdict required')
        self.verdict(matches[0], candidate=candidate, base=base, source=source, operation=operation)

    def reconcile(self, source, base):
        exceptions = self.policy.get('base_exceptions', {})
        need(set(str(i) for i in range(1, 9)).issubset(exceptions), '01–08 transition exceptions must be recorded')
        if not self.ancestor(base, source):
            records = self.policy.get('reconciliations', [])
            matches = [r for r in records if r.get('source') == source and r.get('develop') == base]
            need(len(matches) == 1, 'develop advanced or exceptional base: exact reconciliation required')
            self.verdict(matches[0], source=source, develop=base)

    def integrate(self, a):
        self.context(a.worker)
        ready = self.read_receipt(a.ready, 'ready')
        need(ready.get('worker') == a.worker, 'wrong ready receipt owner')
        start = self.read_receipt(ready.get('start_receipt', ''), 'start')
        self.task_ready_binding(start, ready, ready['start_receipt'], a.worker)
        source = ready['candidate']
        need(a.line != 'main' or ready.get('kind') == 'hotfix', 'only reviewed hotfixes integrate directly to main; releases use promote')
        need(self.sha('refs/heads/' + ready['branch']) == source, 'task changed after review readiness')
        self.proof(ready['checks'])
        base = self.fetch(a.line)
        self.qualified(a.line, base)
        candidate = self.sha(a.candidate)
        need(a.candidate == candidate, 'candidate must be full immutable SHA')
        need(self.ancestor(base, candidate) and self.ancestor(source, candidate), 'candidate loses target/source history')
        if a.line == 'develop':
            self.reconcile(source, base)
        self.exact_review('integrate-' + a.line, candidate, base, source)
        # Integration must operate on an explicitly owned checkout of the target line.
        need(self.git('branch', '--show-current').stdout.strip() == a.line, 'target line must be explicitly checked out')
        need(self.sha('HEAD') == base, 'local target differs from freshly fetched canonical line')
        self.receipt.update(candidate=candidate, source=source, base=base, line=a.line,
                            task=ready['task'], source_branch=start['branch'], target_branch=a.line,
                            source_task_start=str(Path(ready['start_receipt']).resolve()),
                            source_task_start_sha256=digest(ready['start_receipt']),
                            ready_receipt=str(Path(a.ready).resolve()), ready_sha256=digest(a.ready))
        if not a.check_only:
            self.git('merge', '--no-overwrite-ignore', '--ff-only', candidate)
        return 'allowed' if a.check_only else 'completed'

    def initialize(self, a):
        self.context(a.worker)
        main = self.fetch('main')
        baseline = self.baseline()
        need(main == baseline, 'initialize only from exact freshly fetched accepted release')
        # Confirm absence remotely; failure is never interpreted as absence.
        p = self.git('ls-remote', '--exit-code', '--heads', 'origin', 'refs/heads/develop', check=False)
        need(p.returncode == 2 and not p.stdout, 'develop exists or remote absence was not established')
        need(self.policy.get('develop_initialized') is False, 'develop initialization must be explicitly one-time; no recreation')
        need(self.git('show-ref', '--quiet', '--verify', 'refs/remotes/origin/develop', check=False).returncode == 1,
             'persistent develop tracking history exists; never recreate it')
        need(self.git('show-ref', '--quiet', '--verify', 'refs/heads/develop', check=False).returncode == 1,
             'persistent develop already exists; never recreate it')
        history = [json.loads(path.read_text()) for path in self.evidence.glob('*.json')]
        need(not any(r.get('operation') == 'initialize' and r.get('status') == 'completed' for r in history),
             'preserved initialization receipt exists; persistent develop cannot be recreated')
        self.exact_review('initialize-develop', baseline, main, baseline)
        self.receipt.update(candidate=baseline, base=main, line='develop')
        if not a.check_only:
            self.git('branch', 'develop', baseline)
        return 'allowed' if a.check_only else 'completed'

    def promote(self, a):
        self.context(a.worker)
        develop, main = self.fetch('develop'), self.fetch('main')
        self.qualified('develop', develop)
        self.qualified('main', main)
        candidate = self.sha(a.candidate)
        need(candidate == a.candidate, 'candidate must be full immutable SHA')
        start = self.read_receipt(a.start, 'start')
        need(start.get('kind') == 'release' and start.get('worker') == a.worker, 'release start receipt required')
        need(self.sha('refs/heads/' + start['branch']) == candidate, 'release branch/candidate mismatch')
        need(self.ancestor(start['base'], candidate) and self.ancestor(main, candidate), 'release lineage mismatch')
        # Any release fixes must already be back-merged into the current qualified develop.
        need(self.ancestor(candidate, develop), 'release fixes must be reviewed and back-merged into develop')
        self.exact_review('promote-release', candidate, main, develop)
        need(re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?', a.tag), 'invalid immutable release tag')
        need(self.git('show-ref', '--quiet', '--verify', 'refs/tags/' + a.tag, check=False).returncode == 1, 'tag already exists')
        remote = self.git('ls-remote', '--exit-code', '--tags', 'origin', 'refs/tags/' + a.tag, check=False)
        need(remote.returncode == 2 and not remote.stdout, 'remote tag exists or absence unproven')
        need(self.git('branch', '--show-current').stdout.strip() == 'main' and self.sha('HEAD') == main,
             'main must be explicitly checked out at fetched SHA')
        self.receipt.update(candidate=candidate, base=main, develop=develop, tag=a.tag)
        if not a.check_only:
            self.git('merge', '--no-overwrite-ignore', '--ff-only', candidate)
            self.receipt['main_promoted'] = candidate
            self.git('tag', '-a', a.tag, candidate, '-m', f'Morgan accepted release {candidate}')
            self.receipt['tag_created'] = a.tag
        return 'allowed' if a.check_only else 'completed'

    def retirement_integration(self, path, start, ready, ready_path):
        self.task_ready_binding(start, ready, ready['start_receipt'], start['worker'])
        raw_path = Path(path).resolve()
        need(raw_path.parent == self.evidence, 'integration receipt outside canonical custody')
        raw = json.loads(raw_path.read_text())
        need(isinstance(raw, dict), 'integration receipt must be a JSON object')
        if raw.get('operation') == 'integrate':
            local = self.read_receipt(path, 'integrate')
            need(local.get('worker') == start['worker'] == ready['worker']
                 and local.get('owner') == start['owner'] == ready['owner']
                 and local.get('repo') == start['repo'], 'local integration worker/owner/worktree binding mismatch')
            need(local.get('task') == start['task'] and local.get('source_branch') == start['branch']
                 and local.get('source') == ready['candidate']
                 and Path(local.get('source_task_start', '')).resolve() == Path(ready['start_receipt']).resolve()
                 and local.get('source_task_start_sha256') == ready['start_sha256']
                 and Path(local.get('ready_receipt', '')).resolve() == Path(ready_path).resolve()
                 and local.get('ready_sha256') == digest(ready_path), 'local integration authored start/ready/task binding mismatch')
            line = local.get('line')
            need(line in ('develop', 'main') and local.get('target_branch') == line
                 and local.get('head_before') == local.get('base')
                 and (line != 'main' or start['kind'] == 'hotfix'), 'local integration target checkout binding mismatch')
            candidate, base, source = local.get('candidate'), local.get('base'), local['source']
            need(candidate == self.sha(candidate) and base == self.sha(base)
                 and self.ancestor(base, candidate) and self.ancestor(source, candidate),
                 'local integration actual candidate/base/source facts mismatch')
            return local, 'integrate-' + line
        normal = self.read_receipt(path, 'merge_receipt')
        link = normal.get('task_linkage', {})
        need(isinstance(link, dict) and normal.get('worker') == link.get('worker') == start.get('worker') == ready.get('worker')
             and link.get('owner') == normal.get('owner') == start.get('owner')
             and link.get('repo') == start.get('repo') and link.get('branch') == start.get('branch')
             and Path(link.get('source_task_start', '')).resolve() == Path(ready['start_receipt']).resolve()
             and link.get('source_task_start_sha256') == ready.get('start_sha256')
             and link.get('task') == start.get('task') == ready.get('task')
             and link.get('source') == ready.get('candidate')
             and link.get('ready_sha256') == digest(ready_path)
             and Path(link.get('ready_receipt', '')).resolve() == Path(ready_path).resolve(),
             'normal merge receipt lacks exact owner/task/ready custody; cannot launder integration')
        gate_path = Path(normal.get('preflight_receipt', '')).resolve()
        need(gate_path.parent == self.evidence and digest(gate_path) == normal.get('preflight_sha256'),
             'normal merge preflight custody mismatch')
        gate = json.loads(gate_path.read_text())
        need(isinstance(gate, dict) and gate.get('schema') == 'offmenu-gitflow-receipt/1'
             and gate.get('operation') == 'delivery' and gate.get('status') == 'allowed'
             and gate.get('repo') == str(self.repo) and gate.get('worker') == link['worker']
             and gate.get('owner') == start.get('owner') and gate.get('source_branch') == start.get('branch')
             and gate.get('candidate') == link['source']
             and gate.get('base') == normal.get('base'), 'normal merge preflight facts mismatch')
        self.proof(normal.get('provider_evidence'))
        try:
            gate_time = datetime.fromisoformat(gate['utc'].replace('Z', '+00:00'))
            merge_time = datetime.fromisoformat(normal['merged_at'].replace('Z', '+00:00'))
            need(gate_time.tzinfo is not None and merge_time.tzinfo is not None
                 and gate_time <= merge_time <= datetime.now(timezone.utc), 'normal merge chronology mismatch')
        except (KeyError, ValueError, TypeError) as e:
            raise GateError('normal merge chronology malformed') from e
        source, base, merged = link['source'], normal['base'], normal['merge_sha']
        need(normal.get('candidate') == source and normal.get('merge_parents') == [base, source],
             'normal receipt source/parent claims mismatch')
        need(merged == self.sha(merged) and self.git('show', '-s', '--format=%P', merged).stdout.strip().split() == [base, source],
             'normal merge actual parents differ from receipt')
        tree = self.git('show', '-s', '--format=%T', merged).stdout.strip()
        need(tree == normal.get('tree') == self.git('show', '-s', '--format=%T', source).stdout.strip(),
             'normal merge actual tree differs from reviewed source')
        return {'source': source, 'candidate': merged, 'base': base, 'line': 'develop',
                'task': link['task'], 'ready_sha256': link['ready_sha256']}, 'deliver-develop'

    def retire(self, a):
        w = self.context(a.worker)
        start = self.read_receipt(a.start, 'start')
        ready = self.read_receipt(a.ready, 'ready')
        need(start.get('worker') == a.worker == ready.get('worker') and start['task'] == ready['task'], 'wrong retirement task')
        self.task_ready_binding(start, ready, a.start, a.worker, current_task=True)
        need(w.get('active_task') == start['task'], 'retirement owner/task not established')
        need(w.get('ignored_custody') == 'preserved', 'ignored-file custody must be explicitly preserved')
        self.proof(w.get('ignored_evidence'))
        source = ready['candidate']
        branch = start['branch']
        need(self.sha('refs/heads/' + branch) == source, 'branch changed after review')
        self.proof(ready['checks'])
        target = self.fetch('develop')
        if self.policy.get('routine_develop') is not None and start['kind'] in ('feature', 'bugfix'):
            self.dispatch_base(start['kind'], 'develop', target)
        else:
            self.qualified('develop', target)
        need(self.ancestor(source, target), 'task not integrated into canonical develop')
        if start['kind'] in ('hotfix', 'release'):
            main = self.fetch('main')
            self.qualified('main', main)
            need(self.ancestor(source, main), 'hotfix/release must return to both lines')
        integration, review_operation = self.retirement_integration(a.integration, start, ready, a.ready)
        need(integration.get('source') == source and integration.get('task') == start['task']
             and integration.get('ready_sha256') == digest(a.ready), 'integration proof mismatch')
        need(self.ancestor(integration['candidate'], target), 'integration receipt absent from develop')
        reviewed_candidate = source if review_operation == 'deliver-develop' else integration['candidate']
        self.exact_review(review_operation, reviewed_candidate, integration['base'], source)
        retirement = w.get('retirement', {})
        self.verdict(retirement, source=source, task=start['task'], branch=start['branch'],
                     owner=start['owner'], repo=str(self.repo))
        inventory = self.git('worktree', 'list', '--porcelain').stdout.split('\n\n')
        for entry in inventory:
            if f'branch refs/heads/{branch}\n' in entry + '\n':
                need(entry.startswith(f'worktree {self.repo}\n'), 'branch has another worktree owner')
        self.receipt.update(task=start['task'], branch=branch, source=source, develop=target,
                            integration_sha256=digest(a.integration))
        if not a.check_only:
            if self.git('branch', '--show-current').stdout.strip() == branch:
                self.git('switch', '--no-overwrite-ignore', '--detach', target)
            self.git('branch', '-d', branch)
        return 'allowed' if a.check_only else 'completed'

    def save(self):
        self.evidence.mkdir(parents=True, exist_ok=True)
        name = f"{self.receipt.get('task', 'gate')}-{self.receipt['operation']}-{uuid4().hex}.json"
        path = self.evidence / name
        # Exclusive creation: never overwrite an earlier receipt, including failed attempts.
        with path.open('x') as f:
            json.dump(self.receipt, f, indent=2)
            f.write('\n')
        return path


def parser():
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument('--repo', default='.')
    p.add_argument('--policy', required=True, help='Morgan-controlled explicit qualification/custody JSON')
    p.add_argument('--evidence-dir', required=True, help='retained receipts outside tracked checkout')
    sub = p.add_subparsers(dest='operation', required=True)
    for name in ('start', 'exception', 'ready', 'delivery', 'merge_receipt', 'integrate', 'initialize', 'promote', 'retire'):
        s = sub.add_parser(name, allow_abbrev=False)
        s.add_argument('--worker', required=True, type=int)
        if name not in ('ready', 'exception', 'delivery', 'merge_receipt'):
            s.add_argument('--check-only', action='store_true')
        if name == 'merge_receipt':
            s.add_argument('--ready', help='exact completed owner task readiness; required for later retirement')
            s.add_argument('--snapshot', required=True)
            s.add_argument('--preflight', required=True)
        if name == 'delivery':
            s.add_argument('--snapshot', required=True)
            s.add_argument('--head', required=True)
            s.add_argument('--base', required=True)
        if name == 'exception':
            s.add_argument('--task', required=True)
        if name == 'start':
            s.add_argument('--kind', choices=['feature', 'bugfix', 'release', 'hotfix'], required=True)
            s.add_argument('--task', required=True)
        if name in ('ready', 'promote', 'retire'):
            s.add_argument('--start', required=True)
        if name == 'ready':
            s.add_argument('--checks', required=True, help='JSON file containing path+sha256 of actual check receipt')
        if name in ('integrate', 'retire'):
            s.add_argument('--ready', required=True)
        if name == 'integrate':
            s.add_argument('--line', choices=['develop', 'main'], default='develop')
        if name in ('integrate', 'promote'):
            s.add_argument('--candidate', required=True)
        if name == 'promote':
            s.add_argument('--tag', required=True)
        if name == 'retire':
            s.add_argument('--integration', required=True)
    return p


def main():
    a = parser().parse_args()
    g = None
    try:
        g = Gitflow(a.repo, a.policy, a.evidence_dir)
        g.receipt['operation'] = a.operation
        g.evidence.mkdir(parents=True, exist_ok=True)
        # One managed operation per canonical receipt directory. Lock lives outside Git.
        with (g.evidence / '.managed.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise GateError('another managed operation owns the custody lock') from e
            g.receipt['status'] = getattr(g, a.operation)(a)
            path = g.save()
        code = 0
    except (GateError, OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        code = 2
        if g is None:
            print(json.dumps({'status': 'blocked', 'error': str(e)}))
            return code
        g.receipt['status'] = 'blocked'
        g.receipt['error'] = str(e)
    if code:
        path = g.save()
    print(json.dumps({'status': g.receipt['status'], 'receipt': str(path),
                      'error': g.receipt.get('error')}))
    return code


if __name__ == '__main__':
    sys.exit(main())
