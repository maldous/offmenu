#!/usr/bin/env python3
"""Human-operated local preview/confirm queue tool. Never run by an agent to submit."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

RESULT = {'status': 'not-submitted', 'attempts': [], 'execution_confirmed': False, 'approval_cleared': False}

def ui(*args, **kwargs):
    kwargs['file'] = sys.stderr
    kwargs['flush'] = True
    print(*args, **kwargs)

def prompt(text):
    ui(text, end='')
    return input()

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def command(executable, item):
    return [executable, 'queue', '--thread', item['thread_id'], '--message', item['message']]

def classify(rc, output):
    match = re.search(r'Queued message ([0-9a-f-]{36}) for thread ([0-9a-f-]{36})', output)
    return ('admitted', match.groups()) if rc == 0 and match else ('unconfirmed-stop', None)

def self_test():
    item={'thread_id':'a', 'message':'literal $(touch nope); quote\' text'}
    assert command('/bin/codex', item)==['/bin/codex','queue','--thread','a','--message',item['message']]
    m='11111111-1111-1111-1111-111111111111';t='22222222-2222-2222-2222-222222222222'
    assert classify(0, f'Queued message {m} for thread {t}')[0]=='admitted'
    assert classify(1,'denied')[0]=='unconfirmed-stop'
    assert classify(0,'')[0]=='unconfirmed-stop'
    assert digest('a') != digest('b')
    ui('5 local pure checks PASS; no subprocess or queue invoked.')

def main():
    class Parser(argparse.ArgumentParser):
        def _print_message(self, message, file=None):
            if message: sys.stderr.write(message)
    parser=Parser(description=__doc__)
    parser.add_argument('--preview-only',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        self_test();RESULT['status']='self-test-pass';return 0
    plan=json.loads((ROOT/'instructions.json').read_text())
    ui('LOCAL HUMAN REVIEW ONLY. Queue admission is not execution or approval.')
    ui('Do not use to bypass a denial. Native approvals remain separate. No auto retries/wake.')
    for item in plan['items']:
        if item['host']!='local':raise ValueError('Nonlocal route refused')
        ui('\n'+'='*72+'\nWorker '+str(item['worker'])+' | '+item['title'])
        ui('Exact session:',item['thread_id'])
        ui('Hold:',item['platform_hold'])
        ui('Selectable:',item['queue_eligible'])
        ui('Authorization loci:',json.dumps(item['authorization_locus'],indent=2))
        if not item['queue_eligible']:ui('DRAFT ONLY:',item['draft_message_not_authorization'])
        ui(item['message'])
    ui('\nEXCLUDED:')
    for reason in plan['excluded']:ui('-',reason)
    if args.preview_only or not sys.stdin.isatty():
        ui('\nPreview complete; no submission. Interactive terminal required to select.');RESULT['status']='preview-only';return 0
    chosen=prompt('\nEnter worker numbers separated by spaces, or press Enter to exit: ').split()
    if not chosen:RESULT['status']='cancelled';return 0
    if len(set(chosen))!=len(chosen):raise ValueError('Duplicate selection')
    known={str(i['worker']):i for i in plan['items'] if i.get('queue_eligible') is True}
    if any(n not in known for n in chosen):raise ValueError('Unknown or non-executable worker; Gateway/native authority unresolved')
    selected=[known[n] for n in chosen]
    ui('\nSELECTED EXACT MESSAGES:')
    for item in selected:ui('\nWorker',item['worker'],item['thread_id'],'\n'+item['message'])
    phrase='QUEUE '+','.join(chosen)
    if prompt('\nTo personally submit only these messages, type '+repr(phrase)+': ')!=phrase:
        ui('Cancelled; nothing queued.');RESULT['status']='cancelled';return 0
    exe=shutil.which('codex')
    if not exe:raise RuntimeError('codex not on PATH')
    logdir=ROOT/'queue-log';logdir.mkdir(mode=0o700,exist_ok=True)
    lock=logdir/'active.lock'
    try:lock.mkdir()
    except FileExistsError:raise RuntimeError('Another or interrupted run exists; inspect logs manually. No retry.')
    try:
        for item in selected:
            key=str(item['worker'])+'-'+digest(item['thread_id']+'\n'+item['message'])
            path=logdir/(key+'.json')
            if path.exists():
                RESULT.update(status='prior-attempt-stop', prior_attempt=str(path));ui('Prior attempt exists for worker',item['worker'],'STOP; no resend.');return 2
            for pin in item['input_pins']:
                if hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()!=pin['sha256']:
                    raise RuntimeError('Input pin changed; STOP: '+pin['path'])
            record={'worker':item['worker'],'thread_id':item['thread_id'],'message_sha256':digest(item['message']),
                    'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'attempt-started-outcome-unknown',
                    'execution_confirmed':False,'approval_cleared':False}
            RESULT['attempts'].append(record)
            RESULT['status']='submission-started-outcome-unknown'
            with path.open('x') as f:
                json.dump(record,f,indent=2);f.flush();os.fsync(f.fileno())
            try:
                r=subprocess.run(command(exe,item),stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30,shell=False)
                output=r.stdout+'\n'+r.stderr
                status,ids=classify(r.returncode,output)
                if ids and ids[1]!=item['thread_id']:status='target-mismatch-stop'
                record.update(status=status,returncode=r.returncode,queue_message_id=ids[0] if ids else None,
                              output=output[:16384],output_truncated=len(output)>16384)
            except subprocess.TimeoutExpired:
                record.update(status='uncertain-timeout-stop')
            except Exception as exc:
                record.update(status='uncertain-error-stop',error_type=type(exc).__name__)
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2)+'\n');tmp.replace(path)
            RESULT['status']=record['status']
            ui('Worker',item['worker'],record['status'],'queue ID',record.get('queue_message_id'))
            if record['status']!='admitted':
                ui('STOP. Inspect outcome; do not retry uncertain/denied sends.');return 2
            ui('Admission only. If this exact local session needs manual activation, you may run:')
            ui('codex resume '+item['thread_id'])
            ui('No prompt or policy override. Do not requeue. Observe actual response separately.')
    finally:lock.rmdir()
    return 0

def entrypoint():
    code = 2
    try:
        code = main()
    except (EOFError, KeyboardInterrupt):
        RESULT['status'] = 'interrupted-outcome-unknown' if RESULT['attempts'] else 'cancelled-before-submission'
        code = 130
    except (OSError, ValueError, RuntimeError) as exc:
        RESULT.update(status='stopped', error=str(exc))
        ui('STOP:', exc)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        RESULT['status'] = 'help' if code == 0 else 'argument-error'
    RESULT['exit_code'] = code
    json.dump(RESULT, sys.stdout, indent=2)
    sys.stdout.write('\n');sys.stdout.flush()
    return code

if __name__=='__main__':
    sys.exit(entrypoint())
