"""Finite integration decisions for the authenticated cloud connector owner.

The model/coding child never supplies authority. The publisher obtains GitHub
and Linear observations through its existing authenticated connectors, and
relays only the typed action returned here. No credentials or API grants live
in this module. Normal GitHub protection applies; no review approval is emitted.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from typing import TypedDict
from uuid import UUID

from .engine import atomic, DeliveryError


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def read_claim(path, root):
    """Read ownership without following symlinks or accepting partial pointers."""
    try:
        if path.is_symlink():
            raise ValueError('symlink claim')
        claim = json.loads(path.read_text())
        if set(claim) != {'binding_sha256','directory','owner'}:
            raise ValueError('claim fields')
        directory = Path(claim['directory'])
        if (not directory.is_absolute() or directory == root
            or not directory.is_relative_to(root) or directory.resolve() != directory
            or any(p.is_symlink() for p in (directory,*directory.parents))):
            raise ValueError('claim directory')
        binding_path = directory/'binding.json'
        if binding_path.is_symlink():
            raise ValueError('symlink binding')
        binding = json.loads(binding_path.read_text())
        if claim != dict(binding_sha256=fingerprint(binding),directory=str(directory),owner=binding['owner']):
            raise ValueError('claim binding')
        return claim
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise DeliveryError('Invalid integration claim') from exc


class IntegrationState(TypedDict, total=False):
    observation: dict
    result: dict


class Controller:
    def __init__(self,directory,binding,claim_root=None):
        required = {'version','repository','pr_number','issue_id','owner','head','base','tree',
                    'policy_sha256','capacity_policy_sha256','validation_operation_key','outputs','head_branch'}
        version = binding.get('version')
        if version == 2:
            required = required | {'publication'}
        if (set(binding) not in (required, required | {'project_id', 'full_issue_acceptance_sha256'})
            or type(version) is not int or version not in (1, 2)):
            raise DeliveryError('Invalid integration binding')
        valid_pr = (type(binding['pr_number']) is int and binding['pr_number'] > 0) if version == 1 else binding['pr_number'] is None
        if (binding['repository'] != 'maldous/offmenu' or not valid_pr
            or not binding['owner'] or not binding['outputs']):
            raise DeliveryError('Invalid integration identity')
        if not re.fullmatch(r'(?:feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}',str(binding['head_branch'])) or binding['head_branch'].endswith('/') or '//' in binding['head_branch']:
            raise DeliveryError('Invalid exact selected branch')
        UUID(binding['issue_id'])
        if 'project_id' in binding:
            try:
                if str(UUID(binding['project_id'])) != binding['project_id']:
                    raise ValueError('noncanonical project')
            except (ValueError, TypeError, AttributeError) as exc:
                raise DeliveryError('Invalid integration project') from exc
            if (not isinstance(binding['full_issue_acceptance_sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', binding['full_issue_acceptance_sha256'])):
                raise DeliveryError('Invalid full issue acceptance pin')
        for key in ('head','base','tree','policy_sha256','capacity_policy_sha256','validation_operation_key'):
            if not re.fullmatch('[0-9a-f]{'+str(40 if key in ('head','base','tree') else 64)+'}',binding[key]):
                raise DeliveryError('Invalid '+key)
        if version == 2:
            publication = binding['publication']
            if (not isinstance(publication, dict)
                or set(publication) != {'plan_sha256', 'qualification_sha256'}
                or any(not re.fullmatch('[0-9a-f]{64}', str(v)) for v in publication.values())):
                raise DeliveryError('Invalid publication binding')
        self._bind_state(directory, binding, claim_root)

    def _bind_state(self, directory, binding, claim_root):
        self.directory = Path(directory).absolute()
        self.claim_root = Path(claim_root).absolute() if claim_root else self.directory.parent
        if self.directory == self.claim_root or not self.directory.is_relative_to(self.claim_root):
            raise DeliveryError('Integration state outside repository claim root')
        for part in (self.directory,*self.directory.parents):
            if part.is_symlink():
                raise DeliveryError('Symlink integration state')
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.binding = binding
        self.key = fingerprint(binding)
        path = self.directory/'binding.json'
        if path.exists() and json.loads(path.read_text()) != binding:
            raise DeliveryError('Immutable integration binding conflict')
        if not path.exists():
            atomic(path,binding)

    @contextmanager
    def ownership(self):
        self.claim_root.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd = os.open(self.claim_root/'repository-owner.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            legacy = self.claim_root/'repository-claim.json'
            active = self.claim_root/'active-owner.json'
            path = active if active.exists() or active.is_symlink() else legacy
            old = read_claim(path,self.claim_root) if path.exists() or path.is_symlink() else None
            evidence = self.directory/'repository-claim.json'
            claim = dict(binding_sha256=self.key,directory=str(self.directory),owner=self.binding['owner'])
            if evidence.exists() or evidence.is_symlink():
                if read_claim(evidence,self.claim_root) != claim:
                    raise DeliveryError('Immutable integration claim conflict')
            if old and (old['binding_sha256'] != self.key or old['directory'] != str(self.directory)):
                if evidence.exists() and self.status().get('merge_effect') != 'verified':
                    raise DeliveryError('Superseded transaction cannot reacquire repository ownership')
                previous = Path(old['directory'])
                if not previous.is_relative_to(self.claim_root):
                    raise DeliveryError('Invalid previous integration claim')
                if (previous/'state.json').is_symlink():
                    raise DeliveryError('Symlink previous integration state')
                state = json.loads((previous/'state.json').read_text())
                if (state.get('merge_effect') in ('pending','unknown')
                    or state.get('publication', {}).get('effect') in ('pending','unknown')
                    or state.get('release_effect') in ('pending','unknown')
                    or state.get('tag_effect') in ('pending','unknown')):
                    raise DeliveryError('Repository integration outcome must reconcile before another owner')
                safe_repair = state['status']=='repair-required' and (not state.get('qualification_sha256')
                    or (state.get('canonical_effect_verified') is True and state.get('merge_commit_sha')))
                metadata_only = state.get('merge_effect')=='verified' and state.get('merge_commit_sha')
                if not safe_repair and not metadata_only and state['status'] not in ('prepared','awaiting-independent-review','awaiting-validation',
                        'awaiting-fresh-observation','awaiting-mergeability','stale-candidate','disabled','accepted','cancelled','release-verified'):
                    raise DeliveryError('Repository integration outcome must reconcile before another owner')
            if not evidence.exists():
                atomic(evidence,claim)
            # Published legacy evidence is never rewritten. Only the active
            # pointer moves, under the original repository-wide owner lock.
            if not legacy.exists() and not legacy.is_symlink():
                atomic(legacy,claim)
            atomic(active,claim)
            yield
        finally:
            os.close(fd)

    def status(self):
        path = self.directory/'state.json'
        return json.loads(path.read_text()) if path.exists() else {'status':'prepared','action':None}

    def result(self,status,action=None,**extra):
        return {'status':status,'action':action,'binding_sha256':self.key,**extra}

    def decide(self,snapshot):
        b = dict(self.binding)
        if b['version'] == 2:
            publication = self.status().get('publication', {})
            if publication.get('effect') != 'verified' or type(publication.get('pr_number')) is not int:
                return self.result('publication-reconciliation-required')
            b['pr_number'] = publication['pr_number']
        prior = self.status()
        if prior['status'] == 'accepted':
            return prior
        # Observation time is issued by the trusted connector owner, not by a
        # worker report. New source/readback needs a fresh observation, while
        # content-bound review evidence does not expire merely with wall time.
        at = snapshot.get('observed_at')
        if type(at) not in (int,float) or not math.isfinite(at) or at > time.time()+5 or time.time()-at > 60:
            return self.result('awaiting-fresh-observation')
        if snapshot.get('publisher_owner') != b['owner']:
            return self.result('quarantined',reason='publisher-owner-mismatch')
        pr = snapshot.get('github',{})
        if pr.get('repository') != b['repository'] or pr.get('number') != b['pr_number']:
            return self.result('quarantined',reason='wrong-pr')
        if pr.get('merged'):
            if not prior.get('qualification_sha256'):
                return self.result('repair-required',reason='merge-without-admitted-integration-intent')
            commit = snapshot.get('merge_commit',{})
            if not re.fullmatch('[0-9a-f]{40}',str(pr.get('merge_commit_sha',''))):
                return self.result('merged-unverified',reason='awaiting-canonical-merge-id')
            if (commit.get('sha') != pr.get('merge_commit_sha')
                or snapshot.get('develop_contains_merge') is not True):
                return self.result('merged-unverified',reason='awaiting-canonical-commit-and-develop-ancestry')
            if (commit.get('parents') != [b['base'],b['head']] or commit.get('tree') != b['tree']):
                return self.result('repair-required',reason='merged-tree-or-parent-readback-mismatch',
                    merge_commit_sha=commit['sha'],canonical_effect_verified=True,merge_effect='verified',
                    action={'kind':'prepare-corrective-candidate','repository':b['repository'],
                            'merge_commit_sha':pr.get('merge_commit_sha'),'force':False})
            def merged_result(status,action=None,**extra):
                return self.result(status,action,merge_effect='verified',merge_commit_sha=commit['sha'],**extra)
            linear = snapshot.get('linear',{})
            project = b.get('project_id')
            if not project:
                return merged_result('merge-verified',reason='full-issue-project-and-acceptance-unbound')
            if linear.get('id') != b['issue_id'] or linear.get('project_id') != project:
                return merged_result('merge-verified',reason='awaiting-linear-readback')
            acceptance = snapshot.get('full_issue_acceptance')
            if (not isinstance(acceptance, dict)
                or set(acceptance) != {'version', 'issue_id', 'project_id', 'owner', 'decision', 'scope', 'evidence_id'}
                or type(acceptance['version']) is not int or acceptance['version'] != 1
                or acceptance['issue_id'] != b['issue_id'] or acceptance['project_id'] != project
                or acceptance['owner'] != b['owner'] or acceptance['decision'] != 'accepted'
                or acceptance['scope'] != 'full-issue' or not isinstance(acceptance['evidence_id'], str)
                or not acceptance['evidence_id'].strip()
                or fingerprint(acceptance) != b['full_issue_acceptance_sha256']):
                return merged_result('merge-verified',reason='full-issue-acceptance-unqualified')
            if linear.get('state') == 'Done':
                return merged_result('accepted',tree=commit['tree'])
            if snapshot.get('cancel_requested'):
                return merged_result('merge-verified',reason='cancelled-after-confirmed-merge-no-new-metadata-mutation')
            if prior.get('linear_exhausted'):
                return merged_result('metadata-repair-required')
            if prior.get('linear_effect')=='refused':
                return merged_result('authority-refused',refused_kind='linear')
            retries = prior.get('linear_retry_count',0)
            if prior.get('linear_effect') in ('pending','unknown'):
                if at-prior.get('linear_requested_at',at) < 10:
                    return merged_result('linear-reconciliation-required')
                if retries >= 2:
                    return merged_result('metadata-repair-required',linear_exhausted=True)
                retries += 1
            return merged_result('linear-intent',linear_effect='pending',action={
                'kind':'update-linear','issue_id':b['issue_id'],'state':'Done',
                'merge_commit_sha':commit['sha'],'validation_operation_key':b['validation_operation_key']},
                linear_retry_count=retries,linear_requested_at=time.time())
        if prior.get('merge_effect') in ('pending','unknown'):
            # An open PR after an uncertain request is not proof of nonexecution.
            # The API owner must reconcile that immutable action explicitly.
            return self.result('reconciliation-required')
        if snapshot.get('cancel_requested'):
            return self.result('cancelled')
        if prior.get('merge_effect')=='refused':
            return self.result('authority-refused',refused_kind='merge')
        if prior['status']=='repair-required':
            return prior
        if (pr.get('state') != 'open' or pr.get('draft') is not False
            or pr.get('head') != b['head'] or pr.get('base') != b['base']
            or pr.get('head_branch') != b['head_branch']
            or pr.get('base_branch') != 'develop'):
            return self.result('stale-candidate')
        if pr.get('mergeable') is not True:
            return self.result('awaiting-mergeability')
        if (snapshot.get('policy_sha256') != b['policy_sha256']
            or snapshot.get('capacity_policy_sha256') != b['capacity_policy_sha256']):
            return self.result('quarantined',reason='policy-drift')
        validation = snapshot.get('validation',{})
        if (validation.get('operation_key') != b['validation_operation_key']
            or validation.get('status') != 'succeeded' or validation.get('head') != b['head']
            or validation.get('base') != b['base']
            or validation.get('capacity_policy_sha256') != b['capacity_policy_sha256']
            or validation.get('outputs') != b['outputs']
            or validation.get('child_tree_gone') is not True
            or validation.get('reconcile_required') is not False):
            return self.result('awaiting-validation')
        review = snapshot.get('review',{})
        if (review.get('head') != b['head'] or review.get('base') != b['base']
            or review.get('independent') is not True or not review.get('evidence_id')):
            return self.result('awaiting-independent-review')
        if review.get('findings') or snapshot.get('unresolved_findings'):
            return self.result('repair-required',reason='independent-review-findings',
                action={'kind':'repair','head':b['head'],'review_evidence_id':review['evidence_id']})
        if review.get('verdict') != 'accept':
            return self.result('awaiting-independent-review')
        if (snapshot.get('source_tree') != b['tree'] or snapshot.get('source_clean') is not True
            or snapshot.get('publication_triggers_actions') is not False):
            return self.result('quarantined',reason='source-or-trigger-mismatch')
        if snapshot.get('automatic_integration_enabled') is not True:
            return self.result('disabled')
        return self.result('merge-intent',merge_effect='pending',qualification_sha256=fingerprint({
            'validation':validation,'review':review,'tree':b['tree'],'policy':b['policy_sha256']}),
            action={'kind':'merge-pr','repository':b['repository'],
            'pr_number':b['pr_number'],'expected_head_sha':b['head'],'expected_head_branch':b['head_branch'],
            'expected_base_sha':b['base'],'merge_method':'merge','bypass_protection':False,
            'operation_key':fingerprint({'binding':self.key,'action':'merge'})})

    def run(self,observation):
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.sqlite import SqliteSaver
        os.environ['LANGCHAIN_TRACING_V2'] = 'false'
        os.environ['LANGSMITH_TRACING'] = 'false'
        with self.ownership():
            graph = StateGraph(IntegrationState)
            graph.add_node('decide',lambda state:{'result':self.decide(state['observation'])})
            def persist(state):
                # Durable intent exists before the API gateway receives action.
                previous = self.status()
                for field in ('qualification_sha256','authority_receipts','linear_retry_count','linear_requested_at','merge_effect','linear_effect','linear_exhausted','merge_commit_sha','canonical_effect_verified','publication','helper_consumed'):
                    if field in previous:
                        state['result'].setdefault(field,previous[field])
                atomic(self.directory/'state.json',state['result'])
                return state
            graph.add_node('persist',persist)
            graph.add_edge(START,'decide');graph.add_edge('decide','persist');graph.add_edge('persist',END)
            with SqliteSaver.from_conn_string(str(self.directory/'graph.sqlite')) as saver:
                result = graph.compile(checkpointer=saver).invoke({'observation':observation},
                    {'configurable':{'thread_id':self.key},'recursion_limit':8})
            return result['result']

    def record_api_outcome(self,kind,outcome):
        with self.ownership():
            current = self.status()
            if kind not in ('merge','linear') or current.get(kind+'_effect') != 'pending':
                raise DeliveryError('No matching durable API intent')
            if outcome == 'not-issued':
                current.update(status='stale-candidate' if kind=='merge' else 'merge-verified',action=None)
                current[kind+'_effect']='not-issued'
            elif outcome == 'refused':
                current.update(status='authority-refused',action=None,refused_kind=kind)
                current[kind+'_effect']='refused'
            elif outcome in ('uncertain','succeeded'):
                # Even API success requires canonical commit/ref or Linear
                # readback. Never repeat the mutation to recover metadata.
                current.update(status='merge-unknown' if kind=='merge' else 'linear-unknown',action=None)
                current[kind+'_effect']='unknown'
            else:
                raise DeliveryError('Invalid API outcome')
            atomic(self.directory/'state.json',current)
            return current

    def reauthorize_known_refusal(self,authority_receipt_sha256):
        with self.ownership():
            current = self.status()
            used = current.get('authority_receipts',[])
            if (current['status'] != 'authority-refused'
                or not re.fullmatch('[0-9a-f]{64}',str(authority_receipt_sha256))
                or authority_receipt_sha256 in used):
                raise DeliveryError('A new trusted authority receipt and known refusal are required')
            current[current['refused_kind']+'_effect']='not-issued'
            current.update(status='prepared',action=None,
                           authority_receipts=[*used,authority_receipt_sha256])
            atomic(self.directory/'state.json',current)
            return current


    def _publication_checkpoint(self, state):
        """Use the original graph/checkpoint and state file, never a side ledger."""
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.sqlite import SqliteSaver
        os.environ['LANGCHAIN_TRACING_V2'] = 'false'
        os.environ['LANGSMITH_TRACING'] = 'false'
        graph = StateGraph(IntegrationState)
        def persist(_):
            atomic(self.directory/'state.json', state)
            return {'result': state}
        graph.add_node('persist-publication', persist)
        graph.add_edge(START, 'persist-publication')
        graph.add_edge('persist-publication', END)
        with SqliteSaver.from_conn_string(str(self.directory/'graph.sqlite')) as saver:
            return graph.compile(checkpointer=saver).invoke({},
                {'configurable': {'thread_id': self.key}, 'recursion_limit': 4})['result']

    def prepare_publication(self, plan, snapshot):
        """Authenticated owner admission; no fabricated PR or merge qualification.

        The fixed helper pins the immutable binding and this entire owner-issued
        source qualification in protected configuration. JSON from coding children
        is never an authenticated invocation of this method.
        """
        with self.ownership():
            b = self.binding
            if b['version'] != 2:
                raise DeliveryError('Publication requires version 2 binding')
            pins = b['publication']
            if fingerprint(plan) != pins['plan_sha256'] or fingerprint(snapshot) != pins['qualification_sha256']:
                raise DeliveryError('Publication admission pin mismatch')
            validation, review = snapshot.get('validation', {}), snapshot.get('review', {})
            if (snapshot.get('publisher_owner') != b['owner'] or snapshot.get('cancel_requested')
                or snapshot.get('policy_sha256') != b['policy_sha256']
                or snapshot.get('capacity_policy_sha256') != b['capacity_policy_sha256']
                or validation.get('operation_key') != b['validation_operation_key']
                or validation.get('status') != 'succeeded' or validation.get('head') != b['head']
                or validation.get('base') != b['base'] or validation.get('outputs') != b['outputs']
                or validation.get('capacity_policy_sha256') != b['capacity_policy_sha256']
                or validation.get('child_tree_gone') is not True
                or validation.get('reconcile_required') is not False
                or review.get('head') != b['head'] or review.get('base') != b['base']
                or review.get('independent') is not True or not review.get('evidence_id')
                or review.get('verdict') != 'accept' or review.get('findings') != []
                or snapshot.get('unresolved_findings') != []
                or snapshot.get('source_tree') != b['tree'] or snapshot.get('source_clean') is not True
                or snapshot.get('publication_triggers_actions') is not False):
                raise DeliveryError('Unqualified publication evidence')
            current = self.status()
            if current.get('publication'):
                return current
            if current['status'] != 'prepared' or current.get('merge_effect'):
                raise DeliveryError('Existing integration state cannot become publication')
            current.update(status='publication-ready', publication={
                'plan_sha256': pins['plan_sha256'], 'qualification_sha256': pins['qualification_sha256'],
                'next': 0, 'effect': 'ready', 'action': None, 'pr_number': None})
            return self._publication_checkpoint(current)

    def publication_intent(self, index, action):
        """Persist exact typed request before the fixed helper can consume it."""
        with self.ownership():
            current = self.status()
            pub = current.get('publication', {})
            if (self.binding['version'] != 2 or type(index) is not int or index != pub.get('next')
                or pub.get('effect') != 'ready' or not isinstance(action, dict)
                or action.get('kind') not in ('blob', 'tree', 'commit', 'ref', 'create-pr', 'update-pr')):
                raise DeliveryError('Publication intent is not ready')
            pub.update(effect='pending', action=action, intent_sha256=fingerprint(action))
            current.update(status='publication-intent', action=None)
            return self._publication_checkpoint(current)

    def consume_publisher_intent(self, expected_binding, intent, plan=None):
        """Reserve once under repository-owner.lock BEFORE HTTP; crash stays held.

        Protected helper admission pins expected_binding out of band. A matching
        active claim, exact durable action, plan/evidence and fresh source checks
        are required; UID alone is never sufficient. Normal callers cannot select
        this method, binding or plan through argv/stdin/config callbacks.
        """
        with self.ownership():
            current = self.status()
            if expected_binding != self.key:
                raise DeliveryError('Publisher binding mismatch')
            active = read_claim(self.claim_root/'active-owner.json', self.claim_root)
            if active['binding_sha256'] != self.key or current.get('binding_sha256', self.key) != self.key:
                raise DeliveryError('Publisher active claim mismatch')
            if intent.get('kind') == 'merge-pr':
                action = current.get('action')
                if (current.get('merge_effect') != 'pending' or not current.get('qualification_sha256')
                    or not action or action.get('kind') != 'merge-pr'
                    or intent != dict(kind='merge-pr', repository=action['repository'],
                        pr_number=action['pr_number'], expected_head_sha=action['expected_head_sha'],
                        expected_base_sha=action['expected_base_sha'],
                        expected_head_branch=action['expected_head_branch'], merge_method='merge',
                        intent_sha256=fingerprint(action))
                    or current.get('helper_consumed') == fingerprint(action)):
                    raise DeliveryError('No unconsumed durable merge intent')
                current['helper_consumed'] = fingerprint(action)
            else:
                pub = current.get('publication', {})
                if (self.binding['version'] != 2 or plan is None
                    or fingerprint(plan) != self.binding['publication']['plan_sha256']
                    or pub.get('qualification_sha256') != self.binding['publication']['qualification_sha256']
                    or pub.get('effect') != 'pending' or intent != pub.get('action')
                    or fingerprint(intent) != pub.get('intent_sha256')):
                    raise DeliveryError('No unconsumed durable publication intent')
                pub['effect'] = 'unknown'
                current['status'] = 'publication-reconciliation-required'
            self._publication_checkpoint(current)
            return True

    def reconcile_publication(self, index, action, canonical, final=False):
        """Only fixed helper canonical GET readback, never a caller success flag.

        Normal helper validates canonical response against exact admitted objects,
        ref/head/base/metadata before entering this trusted seam. An absent PR or
        ref after a lost reply does NOT grant another mutation.
        """
        with self.ownership():
            current = self.status()
            pub = current.get('publication', {})
            if (self.binding['version'] != 2 or pub.get('effect') not in ('pending','unknown')
                or pub.get('next') != index or pub.get('action') != action
                or canonical != fingerprint(action)):
                raise DeliveryError('Publication canonical readback mismatch')
            if action['kind'] == 'create-pr':
                # The number is set by freeze_publication_pr after canonical GET;
                # never allocated by the candidate binding or a create reply.
                if not pub.get('pr_number'):
                    raise DeliveryError('Canonical PR number is not frozen')
            pub.update(next=index+1, effect='verified' if final else 'ready', action=None)
            current.update(status='publication-verified' if final else 'publication-ready')
            return self._publication_checkpoint(current)

    def freeze_publication_pr(self, index, action, number):
        with self.ownership():
            current = self.status()
            pub = current.get('publication', {})
            if (pub.get('effect') not in ('pending','unknown') or pub.get('next') != index
                or pub.get('action') != action or action.get('kind') != 'create-pr'
                or type(number) is not int or number < 1
                or pub.get('pr_number') not in (None, number)):
                raise DeliveryError('Canonical PR binding conflict')
            pub['pr_number'] = number
            return self._publication_checkpoint(current)


class ReleaseController(Controller):
    """Separate owner-admitted main promotion; no coding or issue completion.

    The protected binding pins the reviewed aggregator qualification. Its schema
    remains owned by the release component; this controller binds that exact
    accepted result rather than reimplementing the profile evidence reader.
    """
    def __init__(self, directory, binding, claim_root=None):
        from native_harness_contract import validate_release_candidate, fingerprint as native_fingerprint
        required = {'version','kind','repository','owner','candidate','policy','qualification',
                    'authority','pr_number','main_base','tag','issue_id','project_id'}
        if (set(binding) != required or type(binding['version']) is not int or binding['version'] != 3
            or binding['kind'] != 'release-promotion-v1'
            or binding['repository'] != 'maldous/offmenu'
            or not isinstance(binding['owner'], str) or not binding['owner']
            or type(binding['pr_number']) is not int or binding['pr_number'] <= 0
            or not re.fullmatch('[0-9a-f]{40}', str(binding['main_base']))
            or not re.fullmatch(r'release/[a-z0-9][a-z0-9.-]{0,79}', str(binding['tag']))):
            raise DeliveryError('Invalid release promotion binding')
        candidate = validate_release_candidate(binding['candidate'], binding['policy'])
        candidate_id = native_fingerprint(candidate)
        authority = binding['authority']
        expected = dict(version=1, kind='release-promotion-authority-v1', owner=binding['owner'],
                        issue_id=binding['issue_id'], project_id=binding['project_id'],
                        candidate_sha256=candidate_id,
                        qualification_sha256=native_fingerprint(binding['qualification']),
                        pr_number=binding['pr_number'], main_base=binding['main_base'], tag=binding['tag'])
        if authority != expected:
            raise DeliveryError('Release authority is not bound to exact candidate and qualification')
        for key in ('issue_id','project_id'):
            if str(UUID(binding[key])) != binding[key]:
                raise DeliveryError('Invalid release issue/project identity')
        from release_qualification import validate_qualification
        q = binding['qualification']
        if not isinstance(q, dict) or set(q) != {'summary','plan','results','catalog','evidence_root'}:
            raise DeliveryError('Release qualification inputs required')
        if q['plan'].get('candidate') != candidate:
            raise DeliveryError('Release qualification candidate mismatch')
        validate_qualification(q['summary'], q['plan'], q['results'], binding['policy'],
                               q['catalog'], q['evidence_root'])
        self.candidate_id = candidate_id
        self._bind_state(directory, binding, claim_root)

    def run(self, observation):
        with self.ownership():
            current = self.status()
            b, s = self.binding, self.binding['candidate']['source']
            if current['status'] == 'release-verified':
                return current
            def save(status, action=None, **extra):
                current.update(status=status, action=action, binding_sha256=self.key, **extra)
                return self._publication_checkpoint(current)
            at = observation.get('observed_at')
            if (type(at) not in (int, float) or not math.isfinite(at)
                or at > time.time()+5 or time.time()-at > 60):
                return save('awaiting-fresh-observation')
            if observation.get('publisher_owner') != b['owner']:
                return save('quarantined', reason='publisher-owner-mismatch')
            pr = observation.get('github', {})
            if (pr.get('repository') != b['repository'] or pr.get('number') != b['pr_number']
                or pr.get('head') != s['head'] or pr.get('head_branch') != 'release/candidate-'+self.candidate_id
                or pr.get('base_branch') != 'main'):
                return save('stale-candidate')
            # A matching tag is only accepted after canonical promotion readback.
            if pr.get('merged'):
                commit = observation.get('merge_commit', {})
                if (current.get('release_effect') not in ('pending','unknown','verified')
                    or commit.get('sha') != pr.get('merge_commit_sha')
                    or not re.fullmatch('[0-9a-f]{40}', str(commit.get('sha')))
                    or observation.get('main_contains_merge') is not True):
                    return save('release-reconciliation-required')
                if commit.get('parents') != [b['main_base'],s['head']] or commit.get('tree') != s['tree']:
                    return save('release-readback-mismatch', release_effect='unknown')
                current.update(release_effect='verified', merge_commit_sha=commit['sha'])
                tag = observation.get('tag')
                expected = {'ref':'refs/tags/'+b['tag'], 'object':{'type':'commit','sha':commit['sha']}}
                if tag == expected:
                    return save('release-verified', tag_effect='verified')
                if tag is not None:
                    return save('immutable-tag-conflict')
                if current.get('tag_effect') in ('pending','unknown'):
                    return save('tag-reconciliation-required')
                action = dict(kind='create-release-tag', repository=b['repository'], tag=b['tag'],
                              commit_sha=commit['sha'], candidate_sha256=self.candidate_id,
                              authority_sha256=fingerprint(b['authority']))
                return save('release-tag-intent', action, tag_effect='pending')
            if current.get('release_effect') in ('pending','unknown','verified'):
                return save('release-reconciliation-required')
            if (observation.get('cancel_requested') or pr.get('base') != b['main_base']
                or pr.get('state') != 'open' or pr.get('draft') is not False
                or pr.get('mergeable') is not True or observation.get('tag') is not None):
                return save('release-held')
            if (observation.get('qualification_sha256') != fingerprint(b['qualification'])
                or observation.get('review', {}).get('verdict') != 'accept'
                or observation['review'].get('independent') is not True
                or observation['review'].get('head') != s['head']
                or observation['review'].get('base') != b['main_base']
                or not observation['review'].get('evidence_id')
                or observation['review'].get('findings') != []
                or observation.get('unresolved_findings') != []
                or observation.get('publication_triggers_actions') is not False):
                return save('release-held')
            action = dict(kind='promote-release', repository=b['repository'], pr_number=b['pr_number'],
                          expected_head_sha=s['head'], expected_base_sha=b['main_base'],
                          expected_head_branch='release/candidate-'+self.candidate_id, candidate_sha256=self.candidate_id,
                          authority_sha256=fingerprint(b['authority']), tag=b['tag'])
            return save('release-intent', action, release_effect='pending')

    def consume_release_intent(self, action):
        with self.ownership():
            current = self.status()
            kind = action.get('kind')
            field = {'promote-release':'release_effect','create-release-tag':'tag_effect'}.get(kind)
            if (not field or current.get(field) != 'pending' or current.get('action') != action):
                raise DeliveryError('No matching unconsumed release intent')
            current.update(action=None, status='release-reconciliation-required')
            current[field] = 'unknown'
            self._publication_checkpoint(current)
            return True


def publisher_directory(root, binding):
    """Resume the exact historical transaction; fresh admissions get fresh state."""
    root = Path(root)
    legacy = root/'current'
    path = legacy/'binding.json'
    if legacy.is_symlink() or path.is_symlink():
        raise DeliveryError('Symlink historical publisher binding')
    if path.exists():
        try:
            if not path.is_file() or path.stat().st_size > 1048576:
                raise ValueError('Invalid legacy binding size/type')
            previous = json.loads(path.read_text())
            if previous == binding:
                return legacy
        except (OSError, ValueError) as exc:
            raise DeliveryError('Invalid historical publisher binding') from exc
    return root/('transaction-'+fingerprint(binding))


def publisher_request(config, request):
    """Fixed publisher RPC implementation; config is protected owner admission.

    Test callers may inject synthetic protected configuration. The executable
    entry below obtains it only at the fixed root-owned path, checks identity,
    and never accepts a config/path/key/action selector on the wire.
    """
    binding = config['binding']
    root = Path('/var/lib/offmenu-publisher/integration')
    directory = publisher_directory(root, binding)
    # A trusted in-process test boundary can construct a Controller directly;
    # runtime directories cannot be selected in this JSON protocol.
    controller = (ReleaseController if binding['version'] == 3 else Controller)(directory, binding, root)
    return _publisher_request(controller, config, request)


def _publisher_request(controller, config, request):
    if not isinstance(request, dict) or not isinstance(request.get('op'), str):
        raise DeliveryError('Invalid publisher request')
    operation = request['op']
    shapes = {'prepare': {'op'}, 'intent': {'op','index','action'},
        'consume': {'op','intent'}, 'freeze-pr': {'op','index','action','number'},
        'reconcile': {'op','index','action','canonical','final'},
        'step': {'op','observation'}, 'outcome': {'op','kind','outcome'}, 'status': {'op'}}
    if operation not in shapes or set(request) != shapes[operation]:
        raise DeliveryError('Unsupported publisher request field')
    if isinstance(controller, ReleaseController):
        if (config.get('version') != 2 or controller.binding['owner'] != config.get('logicalOwner')
            or fingerprint(controller.binding) != fingerprint(config['binding'])):
            raise DeliveryError('Release admission changed')
        if operation == 'status':
            with controller.ownership():
                return controller.status()
        if operation == 'step':
            observation = request['observation']
            for name in ('qualification_sha256','review','unresolved_findings','publication_triggers_actions','publisher_owner'):
                if observation.get(name) != config['snapshot'].get(name):
                    raise DeliveryError('Release qualified observation changed')
            return controller.run(observation)
        if operation == 'consume':
            return {'authorized': controller.consume_release_intent(request['intent'])}
        raise DeliveryError('Unsupported release operation')
    binding, plan = controller.binding, config['plan']
    if (fingerprint(binding) != fingerprint(config['binding'])
        or binding['owner'] != config['logicalOwner']
        or fingerprint(plan) != binding['publication']['plan_sha256']
        or fingerprint(config['snapshot']) != binding['publication']['qualification_sha256']):
        raise DeliveryError('Publisher admission changed')
    state = controller.status()
    pub = state.get('publication', {})
    index = pub.get('next', 0)
    expected = None
    if index < len(plan['operations']):
        expected = dict(plan['operations'][index])
        if expected['kind'] == 'update-pr':
            number = pub.get('pr_number')
            if type(number) is not int or number < 1:
                raise DeliveryError('Canonical PR number unavailable')
            expected['path'] = expected['path'].replace('{canonical}', str(number))
            expected['readPath'] = expected['readPath'].replace('{canonical}', str(number))
    if operation in ('intent','freeze-pr','reconcile'):
        if request['index'] != index or request['action'] != expected:
            raise DeliveryError('Publisher exact admitted action mismatch')
    if operation == 'prepare':
        return controller.prepare_publication(plan, config['snapshot'])
    if operation == 'status':
        with controller.ownership():
            return controller.status()
    if operation == 'intent':
        return controller.publication_intent(index, expected)
    if operation == 'consume':
        intent = request['intent']
        if intent.get('kind') != 'merge-pr' and intent != expected:
            raise DeliveryError('Publisher exact consume mismatch')
        return {'authorized': controller.consume_publisher_intent(fingerprint(binding), intent, plan)}
    if operation == 'freeze-pr':
        return controller.freeze_publication_pr(index, expected, request['number'])
    if operation == 'reconcile':
        if request['final'] is not (index == len(plan['operations'])-1):
            raise DeliveryError('Publisher final phase mismatch')
        return controller.reconcile_publication(index, expected, request['canonical'], request['final'])
    if operation == 'step':
        observation = request['observation']
        # Remote facts may change. Static validation/review/source/policy facts
        # must remain the exact root-admitted evidence, never arbitrary JSON true.
        for name in ('validation','review','source_tree','source_clean','policy_sha256',
                     'capacity_policy_sha256','publication_triggers_actions','publisher_owner'):
            if observation.get(name) != config['snapshot'].get(name):
                raise DeliveryError('Publisher qualified observation changed')
        return controller.run(observation)
    if operation == 'outcome':
        if request['kind'] != 'merge':
            raise DeliveryError('Publisher does not own Linear effects')
        return controller.record_api_outcome('merge', request['outcome'])
    raise DeliveryError('Unsupported publisher request')


def publisher_main():
    """Isolated Python bridge. No keys, HTTP, general runner or auth API."""
    import stat
    import sys
    try:
        os.umask(0o077)
        uid, gid = os.getuid(), os.getgid()
        if uid in (0, 1000) or uid != os.geteuid() or gid != os.getegid():
            raise DeliveryError('Publisher identity held')
        path = Path('/etc/offmenu-publisher/config.json')
        for parent in path.parents:
            entry = parent.lstat()
            if not stat.S_ISDIR(entry.st_mode) or entry.st_uid != 0 or entry.st_mode & 0o022:
                raise DeliveryError('Publisher configuration custody held')
        fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            entry = os.fstat(fd)
            if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != 0 or entry.st_gid != gid
                or stat.S_IMODE(entry.st_mode) != 0o440 or entry.st_nlink != 1
                or not 0 < entry.st_size <= 1048576):
                raise DeliveryError('Publisher configuration custody held')
            with os.fdopen(fd, 'r', closefd=False) as stream:
                config = json.loads(stream.read(1048577))
        finally:
            os.close(fd)
        directory = path.parent.stat()
        if (stat.S_IMODE(directory.st_mode) != 0o750 or directory.st_gid != gid
            or config['publisherUid'] != uid or config['publisherGid'] != gid):
            raise DeliveryError('Publisher configuration identity held')
        root = Path('/var/lib/offmenu-publisher/integration')
        for part in root.parents:
            entry = part.lstat()
            if (not stat.S_ISDIR(entry.st_mode) or entry.st_uid != 0 or entry.st_mode & 0o022):
                raise DeliveryError('Publisher state ancestry held')
        entry = root.lstat()
        if (root.resolve() != root or not stat.S_ISDIR(entry.st_mode) or entry.st_uid != uid
            or entry.st_gid != gid or stat.S_IMODE(entry.st_mode) != 0o700):
            raise DeliveryError('Publisher state custody held')
        selected = publisher_directory(root, config['binding'])
        # Creation is publisher-only beneath the already checked custody root.
        selected.mkdir(mode=0o700, exist_ok=True)
        for part in (root, selected):
            entry = part.lstat()
            if (part.resolve() != part or not stat.S_ISDIR(entry.st_mode) or entry.st_uid != uid
                or entry.st_gid != gid or stat.S_IMODE(entry.st_mode) != 0o700):
                raise DeliveryError('Publisher state custody held')
        # State and immutable bindings may be modified only by the publisher.
        # No symlink/hardlink/special file can redirect a privileged bridge read.
        for directory in (root, selected):
            for part in directory.iterdir():
                entry = part.lstat()
                if directory == root and (part.name == 'current' or re.fullmatch(r'transaction-[0-9a-f]{64}', part.name)):
                    if (not stat.S_ISDIR(entry.st_mode) or part.resolve() != part
                        or entry.st_uid != uid or entry.st_gid != gid or stat.S_IMODE(entry.st_mode) != 0o700):
                        raise DeliveryError('Publisher transaction custody held')
                    continue
                if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != uid or entry.st_gid != gid
                    or entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) != 0o600
                    or entry.st_size > (67108864 if part.name == 'graph.sqlite' else 1048576)):
                    raise DeliveryError('Publisher state file custody held')
        raw = sys.stdin.buffer.read(1048577)
        if len(raw) > 1048576:
            raise DeliveryError('Publisher request too large')
        result = publisher_request(config, json.loads(raw))
        output = json.dumps(result)
        if len(output.encode()) > 1048576:
            raise DeliveryError('Publisher result too large')
        print(output)
    except Exception:
        print('publisher-held', file=sys.stderr)
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['step','status','api-outcome','reauthorize'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--observation',type=Path)
    parser.add_argument('--kind',choices=['merge','linear'])
    parser.add_argument('--outcome',choices=['succeeded','uncertain','refused','not-issued'])
    parser.add_argument('--authority-receipt-sha256')
    parser.add_argument('--claim-root',type=Path)
    args = parser.parse_args()
    controller = Controller(args.directory,json.loads(args.binding.read_text()),args.claim_root)
    if args.action=='step':
        result = controller.run(json.loads(args.observation.read_text()))
    elif args.action=='api-outcome':
        result = controller.record_api_outcome(args.kind,args.outcome)
    elif args.action=='reauthorize':
        result = controller.reauthorize_known_refusal(args.authority_receipt_sha256)
    else:
        result = controller.status()
    print(json.dumps(result))


if __name__ == '__main__':
    main()
