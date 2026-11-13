#!/usr/bin/env python3
"""Immutable sharded derivation and durable typed consumer index for common/1.

All source packets remain unchanged. A completed shard is reusable only with the
same input/code/contract pins and exact output digests. This is candidate data,
not canonical identity, source admission, or an application deployment.
"""
import argparse, collections, concurrent.futures, contextlib, gzip, hashlib, io
import json, os, shutil, sqlite3, sys, time, uuid, fcntl
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from north_star_derivations import digest, VERSION, PROP, REL, TYPE
from north_star_national_context import derive, VERSION as CONTEXT_VERSION

FORMAT = 'offmenu-north-star-full-derivation/1'
MANIFEST_SHA = 'c129dd58a917cf98721856f9094c724923f35ed14cefe2d9206c03db1fc6fcbb'
METADATA_ROOT = Path('/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/bulk-parallel')
SCHEMA_SHA = '89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c'
CONTRACT_SHA = 'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa'
USABLE_IDENTIFIERS = {'source-asserted','candidate','editor-authored','reviewed','verified'}
GIB = 1024**3

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def encoded(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
class TimeSliceComplete(Exception): pass

def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def live_storage(output,committed_bytes):
    # Committed shard data and receipts are counted once.
    # Only bounded live root files and SQLite scratch are scanned repeatedly.
    root_bytes=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
    scratch=output/'sqlite-temp'
    temp_bytes=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file()) if scratch.exists() else 0
    for directory in (output/'shards').glob('*.tmp-*'):
        for p in directory.rglob('*'):
            try:
                if p.is_file():temp_bytes+=p.stat().st_size
            except FileNotFoundError:pass  # A worker may atomically commit between observations.
    return committed_bytes+root_bytes+temp_bytes

def atomic_json(path,value):
    temp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    with temp.open('xb') as f: f.write(encoded(value));f.flush();os.fsync(f.fileno())
    os.replace(temp,path);fsync_dir(path.parent)
def asset_path(root,key):
    k=Path(key)
    if k.is_absolute() or '..' in k.parts or not k.parts: raise ValueError('UnsafeAssetKey')
    p=root/k
    if root.resolve() not in p.resolve().parents or any((root/Path(*k.parts[:n])).is_symlink() for n in range(1,len(k.parts)+1)):
        raise ValueError('UnsafeAssetSymlink')
    return p
def checked_asset(root,entry):
    p=asset_path(root,entry['key']);b=p.read_bytes()
    if len(b)!=entry['bytes'] or sha_bytes(b)!=entry['sha256']: raise ValueError('InputAssetDigestMismatch')
    return b
def source_binding(row,citations):
    cs=[citations[c] for c in row['citationIds'] if c in citations]
    if not cs or len(cs)!=len(row['citationIds']): raise ValueError('MissingCitation')
    if any(c['scope']!=row['scope'] for c in cs): raise ValueError('CitationScopeMismatch')
    if any(c.get('revisionId') in (None,'') for c in cs): return None
    return sorted({(c['sourceId'],str(c['revisionId'])) for c in cs})

def index_rows(packet,side):
    """Type/scope/source-bound IDs; no lexical identity merging or text match."""
    citations={c['id']:c for c in packet['citations']};resources={r['id']:r for r in packet['resources']}
    context_subjects=set()
    for a in side['assertions']:
        resource=resources.get(a['subjectId'])
        if resource and a['scope']==resource['scope']:
            binding=source_binding(a,citations)
            if binding and binding==source_binding(resource,citations):context_subjects.add(a['subjectId'])
    rows=[];rejected=collections.Counter()
    for r in resources.values():
        if r['type'] not in (TYPE+'FoodProduct',TYPE+'FoodConcept',TYPE+'FoodPreparation',TYPE+'FoodCompositionObservation'): continue
        binding=source_binding(r,citations)
        rows.append(['N',r['id'],r['type'],digest(r['scope']),digest(binding) if binding else None,int(r['id'] in context_subjects)])
    for a in packet['assertions']:
        if a['propertyId']!=PROP+'sourceIdentifier': continue
        r=resources.get(a['subjectId'])
        if r is None or r['type']!=TYPE+'FoodProduct': continue
        f=a['value'].get('fields',{});namespace=f.get('system',{}).get('value');lexical=f.get('value',{}).get('value')
        if a['status'] not in USABLE_IDENTIFIERS: rejected['input-status-not-usable']+=1;continue
        if not isinstance(namespace,str) or not namespace.strip() or not isinstance(lexical,str) or not lexical.strip():
            rejected['namespace-or-lexical-value-missing']+=1;continue
        binding=source_binding(a,citations);rbinding=source_binding(r,citations)
        if not binding: rejected['source-release-binding-missing']+=1;continue
        if a['scope']!=r['scope'] or binding!=rbinding: rejected['identifier-resource-evidence-mismatch']+=1;continue
        for source,release in binding:
            key=[source,release,namespace,lexical]
            rows.append(['I',digest(key),a['subjectId'],a['id'],digest(a),source,release,namespace,lexical])
    for edge in side['relations']:
        binding=source_binding(edge,citations)
        original=edge['derivation']['inputRelationIds']
        rows.append(['E',edge['id'],edge['subjectId'],edge['objectId'],digest(edge['scope']),digest(binding) if binding else None,
                     original[0],edge['derivation']['inputDigests'][original[0]],'|'+'|'.join(edge['expectedSubjectTypes'])+'|'])
    return rows,rejected

def validator_for(schema):
    try:
        import jsonschema_rs
        return jsonschema_rs.Draft202012Validator(schema,validate_formats=True)
    except ImportError:
        import jsonschema
        return jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())

def existing_shard(directory,expected):
    receipt_path=directory/'receipt.json'
    if not directory.exists(): return None
    if not receipt_path.is_file(): raise ValueError('IncompleteCommittedShard')
    receipt=json.loads(receipt_path.read_text())
    if receipt['selection']!=expected: raise ValueError('ShardSelectionMismatch')
    for asset in receipt['outputs']:
        p=asset_path(directory,asset['key'])
        if p.stat().st_size!=asset['bytes'] or sha_file(p)!=asset['sha256']: raise ValueError('ShardOutputDigestMismatch')
    return receipt

def derive_shard(args):
    package,output,entry,number,selection,contract,schema,deadline=args
    target=output/'shards'/f'{number:06d}'
    previous=existing_shard(target,selection)
    if previous is not None: return previous
    source=checked_asset(package,entry);validator=validator_for(schema)
    temp=target.with_name(target.name+'.tmp-'+uuid.uuid4().hex);temp.mkdir(parents=True)
    counts=collections.Counter();issues=collections.Counter();types=collections.Counter();sources=collections.Counter();rejected=collections.Counter()
    try:
        with contextlib.ExitStack() as stack:
            sinks=[]
            for name in ('derivations.jsonl.gz','query-index.jsonl.gz'):
                handle=stack.enter_context((temp/name).open('xb'))
                sinks.append(stack.enter_context(gzip.GzipFile(fileobj=handle,mode='wb',mtime=0,compresslevel=1)))
            with gzip.GzipFile(fileobj=io.BytesIO(source)) as stream:
                for ordinal,line in enumerate(stream):
                    if time.monotonic()>=deadline:raise TimeSliceComplete('shard-self-deadline')
                    packet=json.loads(line);validator.validate(packet);side=derive(packet,contract)
                    for bucket in ('resources','assertions','relations','citations'):
                        if any(row['scope'].get('visibility')!='public' for row in packet[bucket]):
                            raise ValueError('NonPublicInputExcluded')
                    side['inputSelection']={'manifestByteSha256':selection['manifestByteSha256'],'assetKey':entry['key'],'assetSha256':entry['sha256'],'packetOrdinal':ordinal}
                    rows,bad=index_rows(packet,side);rejected.update(bad)
                    for row in rows:sinks[1].write(encoded(row))
                    counts.update(packets=1,resources=len(packet['resources']),assertions=len(packet['assertions']),relations=len(packet['relations']),translations=len(packet['translations']),
                                  derivedAssertions=len(side['assertions']),derivedRelations=len(side['relations']),indexRows=len(rows))
                    types.update(r['type'] for r in packet['resources']);sources.update(c['sourceId'] for c in packet['citations']);issues.update(i['code'] for i in side['issues'])
                    if side['assertions'] or side['relations'] or side['issues']:
                        sinks[0].write(encoded(side));counts['sidecarPackets']+=1
                    for a in side['assertions']:
                        f=a['value'].get('fields',{})
                        counts['canonicalUnitCandidates']+=int('canonicalUnitCandidate' in f)
                        counts['profileReportedBasisContexts']+=int('profileReportedBasis' in f)
        if counts['packets']!=entry['packets']:raise ValueError('PacketReconciliationMismatch')
        for name in ('derivations.jsonl.gz','query-index.jsonl.gz'):
            with (temp/name).open('rb') as handle:os.fsync(handle.fileno())
        outputs=[{'key':name,'bytes':(temp/name).stat().st_size,'sha256':sha_file(temp/name)} for name in ('derivations.jsonl.gz','query-index.jsonl.gz')]
        receipt={'schemaVersion':FORMAT,'selection':selection,'counts':dict(counts),'resourceTypes':dict(types),'sourceCitationCounts':dict(sources),
                 'issues':dict(issues),'rejectedIdentifiers':dict(rejected),'outputs':outputs,'candidateOnly':True,'originalsModified':False}
        atomic_json(temp/'receipt.json',receipt);fsync_dir(temp);os.rename(temp,target);fsync_dir(target.parent)
        return receipt
    except BaseException:
        # Only this invocation's unique uncommitted output is removed.
        if temp.exists():shutil.rmtree(temp)
        raise

def make_index(output,receipts,deadline,output_budget,committed_bytes,reserve):
    path=output/'consumer-index.sqlite';db=sqlite3.connect(path,timeout=60)
    interrupted={'reason':None,'nextDiskCheck':0.0}
    def bounded_progress():
        now=time.monotonic()
        if now>=deadline:interrupted['reason']='deadline';return 1
        if now>=interrupted['nextDiskCheck']:
            interrupted['nextDiskCheck']=now+1
            storage=live_storage(output,committed_bytes)
            free=os.statvfs(output).f_bavail*os.statvfs(output).f_frsize
            if storage>=output_budget or free<reserve:interrupted['reason']='budget';return 1
        return 0
    db.set_progress_handler(bounded_progress,10000)
    try:
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA cache_size=-65536')
        scratch=output/'sqlite-temp';scratch.mkdir(exist_ok=True)
        db.execute("PRAGMA temp_store_directory='"+str(scratch).replace("'","''")+"'")
        db.execute('PRAGMA temp_store=FILE')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,type TEXT,scope_sha TEXT,source_sha TEXT,has_context INTEGER) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS identifiers(key_sha TEXT,subject TEXT,assertion_id TEXT,assertion_sha TEXT,source TEXT,release TEXT,namespace TEXT,lexical TEXT,PRIMARY KEY(key_sha,subject,assertion_id)) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY,subject TEXT,object TEXT,scope_sha TEXT,source_sha TEXT,source_edge_id TEXT,source_edge_sha TEXT,allowed_subject_types TEXT) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS imported(shard INTEGER PRIMARY KEY,receipt_sha TEXT);
        ''')
        for number,receipt in receipts.items():
            if time.monotonic()>=deadline:db.close();return None
            storage=live_storage(output,committed_bytes)
            free=os.statvfs(output).f_bavail*os.statvfs(output).f_frsize
            if storage>=output_budget or free<reserve:db.close();raise ValueError('ConsumerIndexBudgetExceeded')
            receipt_sha=digest(receipt);old=db.execute('SELECT receipt_sha FROM imported WHERE shard=?',(number,)).fetchone()
            if old:
                if old[0]!=receipt_sha:raise ValueError('IndexReceiptChanged')
                continue
            entry=next(x for x in receipt['outputs'] if x['key']=='query-index.jsonl.gz')
            p=output/'shards'/f'{number:06d}'/entry['key']
            if sha_file(p)!=entry['sha256']:raise ValueError('IndexInputChanged')
            with db:
                with gzip.open(p,'rt',encoding='utf8') as stream:
                    for line in stream:
                        row=json.loads(line);table={'N':'nodes','I':'identifiers','E':'edges'}[row[0]]
                        db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in row[1:])+')',row[1:])
                db.execute('INSERT INTO imported VALUES (?,?)',(number,receipt_sha))
        db.execute('CREATE INDEX IF NOT EXISTS edge_subject ON edges(subject)');db.execute('CREATE INDEX IF NOT EXISTS edge_object ON edges(object)')
        db.execute('CREATE INDEX IF NOT EXISTS identifier_subject ON identifiers(subject)')
        db.executescript('''DROP TABLE IF EXISTS resolved_edges;
        CREATE TABLE resolved_edges AS SELECT e.id,e.subject,e.object,p.type AS subject_type,n.has_context FROM edges e
        JOIN nodes p ON p.id=e.subject JOIN nodes n ON n.id=e.object
        WHERE instr(e.allowed_subject_types,'|'||p.type||'|')>0 AND n.type='urn:offmenu:type:FoodCompositionObservation'
        AND e.scope_sha=p.scope_sha AND p.scope_sha=n.scope_sha
        AND e.source_sha IS NOT NULL AND e.source_sha=p.source_sha AND p.source_sha=n.source_sha;
        CREATE INDEX resolved_subject ON resolved_edges(subject);
        DROP TABLE IF EXISTS unique_product_keys;
        CREATE TABLE unique_product_keys AS SELECT key_sha,min(subject) AS subject FROM identifiers GROUP BY key_sha HAVING count(DISTINCT subject)=1;
        CREATE INDEX unique_product_subject ON unique_product_keys(subject);
        ''')
        queries={
            'foodProfileEdgesResolved':"SELECT count(*) FROM resolved_edges WHERE subject_type IN ('urn:offmenu:type:FoodConcept','urn:offmenu:type:FoodPreparation')",
            'profileMetricEdgesResolved':"SELECT count(*) FROM resolved_edges WHERE subject_type='urn:offmenu:type:FoodCompositionObservation'",
            'profileMetricContextJoins':"SELECT count(*) FROM resolved_edges WHERE subject_type='urn:offmenu:type:FoodCompositionObservation' AND has_context=1",
            'foodProfileMetricPaths':"SELECT count(*) FROM resolved_edges f JOIN resolved_edges m ON f.object=m.subject WHERE f.subject_type IN ('urn:offmenu:type:FoodConcept','urn:offmenu:type:FoodPreparation') AND m.subject_type='urn:offmenu:type:FoodCompositionObservation'",
            'foodProfileMetricContextPaths':"SELECT count(*) FROM resolved_edges f JOIN resolved_edges m ON f.object=m.subject WHERE f.subject_type IN ('urn:offmenu:type:FoodConcept','urn:offmenu:type:FoodPreparation') AND m.subject_type='urn:offmenu:type:FoodCompositionObservation' AND m.has_context=1",
            'foodsWithMetricContext':"SELECT count(DISTINCT f.subject) FROM resolved_edges f JOIN resolved_edges m ON f.object=m.subject WHERE f.subject_type IN ('urn:offmenu:type:FoodConcept','urn:offmenu:type:FoodPreparation') AND m.subject_type='urn:offmenu:type:FoodCompositionObservation' AND m.has_context=1",
            'unresolvedOrIncompatibleStructuralEdges':'SELECT (SELECT count(*) FROM edges)-(SELECT count(*) FROM resolved_edges)',
        }
        results={name:{'sql':sql,'count':db.execute(sql).fetchone()[0]} for name,sql in queries.items()}
        db.commit();db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close()
        return {'queries':results,'sqliteSha256':sha_file(path),'sqliteBytes':path.stat().st_size,'acceptedIdentityJoins':0,'servedAppQueries':0}
    except sqlite3.OperationalError:
        if interrupted['reason']=='deadline':return None
        if interrupted['reason']=='budget':raise ValueError('ConsumerIndexBudgetExceeded') from None
        raise
    finally:
        db.close()

def _run(package,output,manifest_sha=MANIFEST_SHA,workers=4,seconds=1650,output_budget=4*GIB,reserve=70*GIB, schema_sha=SCHEMA_SHA,contract_sha=CONTRACT_SHA,metadata_root=METADATA_ROOT):
    started=time.monotonic();deadline=started+seconds
    mb=(package/'manifest.json').read_bytes()
    if sha_bytes(mb)!=manifest_sha:raise ValueError('ManifestPinMismatch')
    manifest=json.loads(mb);files={x['key']:x for x in manifest['files']}
    if len(files)!=len(manifest['files']):raise ValueError('DuplicateManifestKey')
    sb=(metadata_root/'schema.json').read_bytes();cb=(metadata_root/'contract.json').read_bytes()
    if sha_bytes(sb)!=schema_sha or sha_bytes(cb)!=contract_sha:raise ValueError('ContractSchemaPinMismatch')
    entries=[x for x in manifest['files'] if x['key'].endswith('.jsonl.gz') and 'packets' in x]
    codepins={n:sha_file(Path(__file__).with_name(n)) for n in ('derive_north_star_national.py','north_star_derivations.py','north_star_national_context.py')}
    selection={'manifestByteSha256':manifest_sha,'schemaByteSha256':schema_sha,'contractByteSha256':contract_sha,'rulesetVersion':VERSION,'additionalRulesetVersions':[CONTEXT_VERSION],'codePins':codepins}
    output.mkdir(parents=True,exist_ok=True);(output/'shards').mkdir(exist_ok=True)
    config=output/'selection.json'
    if config.exists():
        if json.loads(config.read_text())!=selection:raise ValueError('OutputSelectionChanged')
    else:atomic_json(config,selection)
    receipts={};remaining=[];committed_bytes=0
    def expected(n,entry):return dict(selection,asset=entry,ordinal=n)
    for n,entry in enumerate(entries):
        old=existing_shard(output/'shards'/f'{n:06d}',expected(n,entry))
        if old:receipts[n]=old;committed_bytes+=sum(x['bytes'] for x in old['outputs'])+(output/'shards'/f'{n:06d}'/'receipt.json').stat().st_size
        else:remaining.append((n,entry))
    if (output/'manifest.json').exists():
        completed=json.loads((output/'manifest.json').read_text())
        if completed.get('complete') is not True or completed['selection']!=selection or remaining:
            raise ValueError('FinalManifestMismatch')
        if sha_file(output/'consumer-index.sqlite')!=completed['consumerIndex']['sqliteSha256']:
            raise ValueError('FinalConsumerIndexChanged')
        return {k:v for k,v in completed.items() if k!='immutableShardInventory'}
    def summary(status):
        totals=collections.Counter();issues=collections.Counter();rejected=collections.Counter()
        for r in receipts.values():totals.update(r['counts']);issues.update(r['issues']);rejected.update(r['rejectedIdentifiers'])
        value={'schemaVersion':FORMAT,'status':status,'selection':selection,'expectedAssets':len(entries),'completedAssets':len(receipts),'counts':dict(totals),'issues':dict(issues),'rejectedIdentifiers':dict(rejected),'committedShardBytes':committed_bytes,
               'complete':False,'candidateOnly':True,'originalsModified':False,'publicAdmissionGranted':False,'globalQualificationBinding':'pending separate owner proof','elapsedSeconds':round(time.monotonic()-started,3)}
        atomic_json(output/'progress.json',value);return value
    summary('deriving')
    status='time-slice-complete'
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        pending={};cursor=0
        while cursor<len(remaining) or pending:
            while cursor<len(remaining) and len(pending)<workers and time.monotonic()<deadline-30:
                free=os.statvfs(output).f_bavail*os.statvfs(output).f_frsize
                if free<reserve or live_storage(output,committed_bytes)>output_budget-2*GIB:status='budget-blocked';break
                n,entry=remaining[cursor];cursor+=1
                args=(package,output,entry,n,expected(n,entry),json.loads(cb),json.loads(sb),deadline-15)
                pending[pool.submit(derive_shard,args)]=n
            if not pending:break
            done,_=concurrent.futures.wait(pending,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                n=pending.pop(future)
                try:r=future.result()
                except TimeSliceComplete:continue
                receipts[n]=r;committed_bytes+=sum(x['bytes'] for x in r['outputs'])+(output/'shards'/f'{n:06d}'/'receipt.json').stat().st_size
            if done:summary('deriving' if status!='budget-blocked' else status)
            if status=='budget-blocked' and not pending:break
    result=summary(status)
    if len(receipts)==len(entries) and time.monotonic()<deadline-30:
        for k in ('packets','resources','assertions','relations','translations'):
            if result['counts'].get(k,0)!=manifest['counts'].get(k,0):raise ValueError('FullCountReconciliationMismatch')
        summary('building-consumer-index')
        index=make_index(output,dict(sorted(receipts.items())),deadline-15,output_budget,committed_bytes,reserve)
        if index is not None:
            result=summary('all-selected-packets-derived-and-consumer-queries-exercised');result['complete']=True;result['consumerIndex']=index
            result['immutableShardInventory']=[{'ordinal':n,'receiptSha256':digest(r),'outputs':r['outputs']} for n,r in sorted(receipts.items())]
            result['files']=[{'key':f'shards/{n:06d}/'+a['key'],'bytes':a['bytes'],'sha256':a['sha256'],'sidecarPackets':r['counts'].get('sidecarPackets',0)}
                             for n,r in sorted(receipts.items()) for a in r['outputs'] if a['key']=='derivations.jsonl.gz']
            result['publicationEligible']=False;result['semanticStatus']='candidate-not-admitted'
            result['confidence']={'status':'not-calibrated','probability':None}
            result['baseDependencies']={'manifestByteSha256':manifest_sha,'schemaByteSha256':schema_sha,'contractByteSha256':contract_sha,
                                        'resolver':'Original citation and resource IDs resolve only against the exact selected immutable input graph; no copied rights grant or identity admission.'}
            result['localOnlyArtifacts']=['consumer-index.sqlite','shards/*/query-index.jsonl.gz','shards/*/receipt.json','selection.json','progress.json']
            atomic_json(output/'manifest.json',result)
            progress={k:v for k,v in result.items() if k!='immutableShardInventory'};atomic_json(output/'progress.json',progress)
            return progress
    return result

def run(package,output,manifest_sha=MANIFEST_SHA,**kwargs):
    # Preflight pin prevents creating an output for a different source selection.
    if sha_file(package/'manifest.json')!=manifest_sha:raise ValueError('ManifestPinMismatch')
    output.mkdir(parents=True,exist_ok=True);fsync_dir(output.parent)
    with (output/'.writer.lock').open('a+b') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('OutputWriterAlreadyActive') from None
        try:return _run(package,output,manifest_sha,**kwargs)
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('package',type=Path);a.add_argument('output',type=Path);a.add_argument('--workers',type=int,default=4);a.add_argument('--seconds',type=int,default=1650);args=a.parse_args()
    if not 1<=args.workers<=32 or not 1<=args.seconds<=1700:raise ValueError('InvalidRunBounds')
    result=run(args.package,args.output,workers=args.workers,seconds=args.seconds)
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','immutableShardInventory')},sort_keys=True))
