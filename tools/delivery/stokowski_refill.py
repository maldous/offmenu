"""One provisional refill observation. Pool.admit remains the sole authority.

Reads existing state without opening Pool (which creates/mutates storage). No
reservation, credential refresh, dispatch, queue, or background execution.
"""
import json
import math
from pathlib import Path
import sqlite3
import time

from symphony_capacity import AdmissionError, host_snapshot, overlap
from symphony_tasks import load_manifest, runtime_lease_ids


def ready_refill(manifest, provider, rows, host, policy, retained=(), cancelled=False, now=None):
    now = time.time() if now is None else now
    result = {'status':'no-ready-work','provisional':True,'authority':'Pool.admit',
              'issue':None,'dispatch':False}
    if cancelled:
        return dict(result,reason='runtime-cancelled')
    checked = provider.get('checked_at') if isinstance(provider,dict) else None
    if (not isinstance(provider,dict) or provider.get('route') != 'codex-chatgpt' or
        provider.get('available') is not True or type(checked) not in (int,float) or
        not math.isfinite(checked) or checked > now+5 or
        now-checked > policy['symphony']['provider_proof_ttl_seconds'] or
        type(provider.get('session_ceiling')) is not int or provider['session_ceiling'] < 1):
        return dict(result,status='deferred',reason='provider-proof-missing-or-stale')
    active = [r for r in rows if r['status'] in ('running','cancel_requested','uncertain')]
    p,h = policy['symphony'],policy['host']
    if len(active) >= min(p['max_concurrent_agents'],p['provider_session_ceiling'],provider['session_ceiling']):
        return dict(result,reason='capacity-sessions')
    if not manifest['tasks']:
        return result
    ceilings = {'cpu_millis':min(p['cpu_budget_millis'],host['cpu_millis']-h['cpu_reserve']*1000),
                'memory_bytes':min(p['memory_budget_bytes'],host['available_memory_bytes']-h['memory_reserve_bytes']),
                'io_slots':p['io_slots'],
                'output_bytes':host['available_disk_bytes']-h['disk_reserve_bytes']}
    for issue,task in sorted(manifest['tasks'].items()):
        if issue in retained:
            continue
        if any(overlap(a,b) for a in task['allowed_paths'] for r in active for b in r['binding']['write_roots']):
            continue
        if any(task['resources'][key]+sum(r['binding']['resources'][key] for r in active)>limit
               for key,limit in ceilings.items()):
            continue
        return dict(result,status='ready-refill',issue=issue,write_roots=task['allowed_paths'],
                    resources=task['resources'],provider_checked_at=checked,
                    reason='provisional-disjoint-scope-and-capacity')
    return result


def observe_refill(runtime, phases):
    """Called at existing terminal/dependency phase boundaries; never polls."""
    runtime = Path(runtime)
    if not any(row.get('status') in ('succeeded','failed','cancelled','refused','quarantined') or
               row.get('stage') == 'dependency-ready' for row in phases.values()):
        return {'status':'deferred','reason':'awaiting-phase-boundary','dispatch':False}
    try:
        manifest = load_manifest(runtime/'manifest.json',expected_branch=None)
        policy = json.loads((runtime/'capacity-policy.json').read_text())
        proof_path = runtime/'provider-proof.json'
        provider = json.loads(proof_path.read_text()) if proof_path.exists() else None
        provider_check = ready_refill({'tasks':{}},provider,[],{},policy,cancelled=(runtime/'cancel.json').exists())
        if provider_check['status'] == 'deferred' or (runtime/'cancel.json').exists():
            return provider_check
        pool_path = Path(policy['symphony']['pool_path'])/'state.sqlite'
        if not pool_path.is_file() or any(p.is_symlink() for p in (pool_path,*pool_path.parents)):
            return {'status':'deferred','reason':'shared-pool-unavailable','dispatch':False}
        with sqlite3.connect(pool_path.as_uri()+'?mode=ro',uri=True) as db:
            rows = [{'id':r[0],'binding':json.loads(r[1]),'status':r[2]}
                    for r in db.execute('SELECT id,binding,status FROM leases')]
        retained = {issue for issue,lease in runtime_lease_ids(runtime,manifest).items()
                    if any(r['id']==lease for r in rows) or
                    (runtime/'attempts'/issue/'intent.json').exists() or
                    (runtime/'attempts'/issue/'receipt.json').exists() or issue in phases}
        return ready_refill(manifest,provider,rows,host_snapshot(runtime),policy,retained,
                            (runtime/'cancel.json').exists())
    except (OSError,ValueError,KeyError,AdmissionError,sqlite3.Error):
        return {'status':'deferred','reason':'refill-evidence-unavailable','dispatch':False}
