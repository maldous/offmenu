#!/usr/bin/env python3
"""Worker61 bounded storage experiment, not corpus qualification or recovery."""
import ast
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('budget61', HERE/'corpus_storage_budget_worker61.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
TARGET = Path('/home/user/src/offmenu-data')
E = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}


def git(*args):
    return subprocess.check_output(['git','--no-optional-locks',*args], env=E, text=True).strip()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()  # Only small explicitly selected implementation/manifest files.
    return {'path':str(path), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def primary():
    return {'main':git('rev-parse','main'), 'index':pin('/home/user/src/offmenu/.git/index')}


def chunks(stream):
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return
        yield chunk


def usage(root):
    paths = [root, *root.rglob('*')]
    return {'logicalBytes':sum(p.stat().st_size for p in paths if p.is_file()),
            'allocatedBytes':sum(p.stat().st_blocks*512 for p in paths),
            'inodes':len({(p.stat().st_dev,p.stat().st_ino) for p in paths})}


def main():
    raise b.BudgetRefusal('Historical measurement rerun disabled: SQLite/temp writers require controlled owner integration and exact review')
    before = primary()
    result = {'schema':'offmenu-worker61-bounded-storage/1',
              'measuredAtUtc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'threadId':os.environ.get('CODEX_THREAD_ID'),
              'freshBase':git('merge-base','HEAD','origin/develop'),
              'branch':git('branch','--show-current'),
              'retainedRefsAfterLockedFetch':git('show-ref'),
              'initialState':'clean detached 908ca373dfc918f2e33fd5e44260879577bed5c5; no prior Worker61 task branch',
              'filesystemBefore':b.filesystem(TARGET), 'primaryBefore':before,
              'report59':{'commit':'63fceac6563721c18f65a4790ff0a4df9a3a6148',
                          'reportSha256':hashlib.sha256(subprocess.check_output(['git','show','63fceac:docs/corpus-capacity-custody-reconciliation-20261014.json'],env=E)).hexdigest()},
              'review60':pin('/home/user/Documents/Codex/2026-10-14/worker60-capacity-review/63fceac6563721c18f65a4790ff0a4df9a3a6148-verdict.json')}
    owner=Path('/home/user/src/offmenu-workers/worker-01')
    result['owner01Head']=subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],env=E,text=True).strip()
    result['pins']=[pin(owner/'scripts'/name) for name in ('align-places-common.py','align-bulk-food-common.py','places_checkpoint.py','qualify-common-expansion.py')]
    result['pins'] += [pin(TARGET/name) for name in ('common-bulk-food-20261014/manifest.json','curated-expanded-country-search-20261013/blobs/manifest.json')]
    known=('common-bulk-food-semantic-final-20261014.repair.lock', 'common-places-semantic-final-20261014.alignment.lock','common-places-semantic-final-20261014.checkpoint.sqlite','common-places-semantic-final-20261014.partial/manifest.json')
    result['custodyPaths']=[{'path':str(TARGET/name),'exists':os.path.lexists(TARGET/name)} for name in known]
    jobs=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid(): continue
        try:
            argv=(proc/'cmdline').read_bytes().split(b'\0')
            command=[x.decode(errors='replace') for x in argv if x]
            if command and any('align-places-common.py' in x or 'align-bulk-food-common.py' in x or 'qualify-common-expansion.py' in x for x in command) and Path(command[0]).name.startswith(('python','uv')):
                jobs.append({'pid':int(proc.name),'argv':command[:15]})
        except (OSError,PermissionError): pass
    result['observedImporterJobs']=jobs
    result['singleWriterAccepted']=False
    result['custodyCaveat']='Process snapshot and absent locks do not prove quiescence; Worker01 retains importer custody. No writer lease assigned.'
    samples=[('food-source','common-bulk-food-20261014/packets/part-00000.jsonl.gz'),
             ('food-output','common-bulk-food-semantic-final-20261014/packets/part-00000.jsonl.gz'),
             ('places-output','common-places-semantic-final-20261014.partial/packets/part-00000.jsonl.gz')]
    result['limits']={'scratchCapBytes':256*1024**2,'compressedAssetCapBytes':4*1024**2,
                      'expandedAssetCapBytes':16*1024**2,'assetCount':3,
                      'sqliteMaxEachBytes':8*1024**2,'sqliteAndDirectoryReservedBytes':32*1024**2}
    result['samples']=[]
    with tempfile.TemporaryDirectory(prefix='worker61-storage-probe-',dir=TARGET) as td:
        root=Path(td)
        result['scratchDevice']=root.stat().st_dev
        writer=b.CappedWriter(256*1024**2, fixed_bytes=32*1024**2)
        for name,key in samples:
            source=TARGET/key
            st=source.stat()
            if st.st_size > 4*1024**2: raise b.BudgetRefusal('compressed sample exceeds 4MiB')
            with source.open('rb') as stream:
                compressed=writer.write(root/(name+'.gz'),chunks(stream),4*1024**2)
            digest=hashlib.sha256((root/(name+'.gz')).read_bytes()).hexdigest()
            with gzip.open(root/(name+'.gz'),'rb') as stream:
                expanded=writer.write(root/(name+'.jsonl'),chunks(stream),16*1024**2)
            copy=None
            if name.endswith('output'):
                with (root/(name+'.jsonl')).open('rb') as stream:
                    copy=writer.write(root/(name+'.publication-copy'),chunks(stream),16*1024**2)
            lines=0
            resources=0
            with (root/(name+'.jsonl')).open('rb') as stream:
                for line in stream:
                    lines+=1
                    packet=json.loads(line)
                    resources+=len(packet.get('resources',[]))
            after=source.stat()
            if (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
                raise b.BudgetRefusal('source changed during bounded sample')
            if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
                raise b.BudgetRefusal('source bytes changed during bounded sample')
            result['samples'].append({'label':name,'sourcePath':str(source),'sha256':digest,
                'sourceDevice':st.st_dev,'compressed':compressed,'expanded':expanded,
                'publicationCopy':copy,'jsonlLines':lines,'resources':resources,'sourceUnchanged':True,
                'expandedToCompressedRatio':expanded['logicalBytes']/compressed['logicalBytes']})
        # Synthetic fixed 10k identity/state fixture reproduces checkpoint schema.
        # Bounds reserve a full 8MiB rollback journal and another 8MiB qualification DB.
        db=sqlite3.connect(root/'checkpoint-fixture.sqlite')
        db.execute('PRAGMA page_size=4096'); db.execute('PRAGMA max_page_count=2048')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
        db.execute('CREATE TABLE identities (source TEXT, record TEXT, PRIMARY KEY(source,record))')
        for n in range(10000): db.execute('INSERT INTO identities VALUES (?,?)',('worker61-fixture',f'identity-{n:08d}'))
        db.execute('INSERT INTO state VALUES (1,?)',(json.dumps({'version':1,'fixtureOnly':True,'cursor':10000,'buffer':'x'*65536}),))
        journal=root/'checkpoint-fixture.sqlite-journal'
        result['checkpointFixtureJournalObservedBytes']=journal.stat().st_size if journal.exists() else 0
        db.commit();db.close()
        result['checkpointFixture']=pin(root/'checkpoint-fixture.sqlite')
        result['checkpointFixture']['identities']=10000
        result['checkpointFixture']['allocatedBytes']=(root/'checkpoint-fixture.sqlite').stat().st_blocks*512
        # Execute the pinned qualifier Database class only, not admission or a run.
        tree=ast.parse((owner/'scripts/qualify-common-expansion.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Database')
        namespace={'sqlite3':sqlite3}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<pinned-qualifier-Database>','exec'),namespace)
        qualifier=namespace['Database'](root/'qualifier-fixture.sqlite',8*1024**2)
        q=qualifier.connection
        q.execute('PRAGMA max_page_count=2048')
        for n in range(10000):
            h=hashlib.sha256(f'worker61-fixture-{n}'.encode()).digest()
            q.execute('INSERT INTO ids VALUES (?,?)',('resource',h))
            q.execute('INSERT INTO texts VALUES (?,?,?)',(h,h,h))
            q.execute('INSERT INTO citations VALUES (?,?)',(h,h))
            q.execute('INSERT INTO references_pending VALUES (?,?)',('resource',h))
            q.execute('INSERT INTO translation_sources VALUES (?,?)',(h,h))
        q.commit(); q.close()
        result['qualificationFixture']=pin(root/'qualifier-fixture.sqlite')
        result['qualificationFixture']['rowsPerTable']=10000
        result['qualificationFixture']['allocatedBytes']=(root/'qualifier-fixture.sqlite').stat().st_blocks*512
        result['qualificationFixture']['scope']='Actual pinned Database class/schema, synthetic hashes, no graph qualification or external temp/sort workload'
        result['scratchPeakObservedBeforeCleanup']=usage(root)
        result['scratchConservativeAccountedBytes']=writer.used
        result['scratchCapSatisfied']=writer.used<=256*1024**2 and usage(root)['allocatedBytes']<=256*1024**2
        assert result['scratchCapSatisfied']
    result['scratchRemoved']=not root.exists()
    result['filesystemAfter']=b.filesystem(TARGET)
    result['primaryAfter']=primary()
    result['primaryPreservedDuringMeasurement']=before==result['primaryAfter']
    result['controls']={'sandbox':'danger-full-access','filesystem':'unrestricted','network':'enabled',
       'mandatoryReviewer':'auto_review','approvalEscalationInterfaceAvailable':True,
       'separateApprovalPolicy':None,'userConfiguration':None,'CODEX_PERMISSION_PROFILE':os.environ.get('CODEX_PERMISSION_PROFILE')}
    result['limitations']=['Sample is three selected complete gzip assets, not random or worst-case corpus coverage.',
       'Food source/output ratio is byte measurement, not newly established source equivalence.',
       'Places sample is existing common output; normalized input-to-output expansion remains unmeasured.',
       'Synthetic checkpoint and qualifier identities are not production replay; full qualification graph/temp/journal peak remains unknown.',
       'No importer integration, corpus execution, checkpoint mutation, reservation or release acceptance.']
    # Proposed bounded next measurement, upper bounds must be enforced by owner01.
    plan={'reserve_bytes':10*1024**3,'reserve_inodes':10000,'fixed_bytes':32*1024**2,'fixed_inodes':16,
          'per_record_bytes':dict(zip(b.COMPONENTS,(65536,8192,65536,65536))),
          'per_record_inodes':dict(zip(b.COMPONENTS,(1,1,1,1))),
          'batch_cap_bytes':256*1024**2,'requested_records':1000}
    result['estimatedNextProbeBounds']=plan
    result['nextProbeArithmetic']=b.capacity(result['filesystemAfter']['availableBytes'],result['filesystemAfter']['availableInodes'],**plan)
    result['proposedTarget']=str(TARGET/'worker01-budget-fixture-20261014')
    result['proposal']='At most 1000 normalized records; new private destination, Worker01 sole writer, all output/checkpoint/journal/temp/copies guarded before writes. Byte and inode bounds are explicit estimates, not accepted peaks. No full-run launch.'
    Path('docs/corpus-storage-budget-worker61-20261014.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('filesystemAfter','samples','checkpointFixture','scratchPeakObservedBeforeCleanup','scratchConservativeAccountedBytes','nextProbeArithmetic','primaryPreservedDuringMeasurement')},indent=2))


if __name__=='__main__':main()
