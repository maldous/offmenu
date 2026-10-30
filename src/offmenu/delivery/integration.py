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
        if set(binding) != required or type(binding['version']) is not int or binding['version'] != 1:
            raise DeliveryError('Invalid integration binding')
        if (binding['repository'] != 'maldous/offmenu' or type(binding['pr_number']) is not int
            or binding['pr_number'] < 1 or not binding['owner'] or not binding['outputs']):
            raise DeliveryError('Invalid integration identity')
        if not re.fullmatch(r'(?:feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}',str(binding['head_branch'])) or binding['head_branch'].endswith('/') or '//' in binding['head_branch']:
            raise DeliveryError('Invalid exact selected branch')
        UUID(binding['issue_id'])
        for key in ('head','base','tree','policy_sha256','capacity_policy_sha256','validation_operation_key'):
            if not re.fullmatch('[0-9a-f]{'+str(40 if key in ('head','base','tree') else 64)+'}',binding[key]):
                raise DeliveryError('Invalid '+key)
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
                previous = Path(old['directory'])
                if not previous.is_relative_to(self.claim_root):
                    raise DeliveryError('Invalid previous integration claim')
                if (previous/'state.json').is_symlink():
                    raise DeliveryError('Symlink previous integration state')
                state = json.loads((previous/'state.json').read_text())
                if state.get('merge_effect') in ('pending','unknown'):
                    raise DeliveryError('Repository integration outcome must reconcile before another owner')
                safe_repair = state['status']=='repair-required' and (not state.get('qualification_sha256')
                    or (state.get('canonical_effect_verified') is True and state.get('merge_commit_sha')))
                metadata_only = state.get('merge_effect')=='verified' and state.get('merge_commit_sha')
                if not safe_repair and not metadata_only and state['status'] not in ('prepared','awaiting-independent-review','awaiting-validation',
                        'awaiting-fresh-observation','awaiting-mergeability','stale-candidate','disabled','accepted','cancelled'):
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
        b = self.binding
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
            if linear.get('id') != b['issue_id'] or linear.get('project_id') != 'ce60c1ab-a732-4a71-8471-14c9dc393886':
                return merged_result('merge-verified',reason='awaiting-linear-readback')
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
                for field in ('qualification_sha256','authority_receipts','linear_retry_count','linear_requested_at','merge_effect','linear_effect','linear_exhausted','merge_commit_sha','canonical_effect_verified'):
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
