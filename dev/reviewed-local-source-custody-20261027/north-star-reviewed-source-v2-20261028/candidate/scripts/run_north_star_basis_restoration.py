#!/usr/bin/env python3
"""Confined two-phase same-source basis restoration; original packages immutable."""
import argparse,collections,concurrent.futures,contextlib,fcntl,gzip,hashlib,io,json,os,shutil,sqlite3,sys,time,uuid,zlib
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parent))
from derive_north_star_bulk import (sha_file,sha_bytes,encoded,atomic_json,fsync_dir,checked_asset,existing_shard,
                                   live_storage,validator_for,TimeSliceComplete,SCHEMA_SHA,CONTRACT_SHA,MANIFEST_SHA as BULK_SHA)
from north_star_derivations import digest
from north_star_basis_restoration import native_projection,restore,VERSION
NATIVE_SHA='312a7f5ce7c32b81d1eb02251303a000073eea2d0b46d9ac710e09ff89dee895'
SOURCES=('off','usda-files');GIB=1024**3
FORMAT='offmenu-same-source-basis-restoration/1'

def readonly(path):return sqlite3.connect('file:'+quote(str(path.resolve()),safe='/')+'?mode=ro&immutable=1',uri=True)
def write_db(path,output):
    new=not path.exists();db=sqlite3.connect(path,timeout=60,uri=True)
    if new:db.execute('PRAGMA page_size=16384')
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA cache_size=-65536')
    scratch=output/'sqlite-temp';scratch.mkdir(exist_ok=True);db.execute("PRAGMA temp_store_directory='"+str(scratch).replace("'","''")+"'");db.execute('PRAGMA temp_store=FILE')
    return db

def check_limits(output,deadline,budget,reserve,committed=0):
    if time.monotonic()>=deadline:raise TimeSliceComplete('self-deadline')
    if live_storage(output,committed)>=budget:raise ValueError('OwnedOutputBudgetExceeded')
    st=os.statvfs(output)
    if st.f_bavail*st.f_frsize<reserve:raise ValueError('SharedFreeReserveReached')

def load_inputs(native,bulk,native_sha,bulk_sha,schema_sha,contract_sha):
    nb=(native/'manifest.json').read_bytes();bb=(bulk/'manifest.json').read_bytes()
    if sha_bytes(nb)!=native_sha or sha_bytes(bb)!=bulk_sha:raise ValueError('SourceManifestPinMismatch')
    nm=json.loads(nb);bm=json.loads(bb)
    if nm.get('status')!='curated-release-ready' or nm.get('privateProviderData') is not False:raise ValueError('NativeReleaseNotSelectedPublic')
    if len({f['key'] for f in nm['files']})!=len(nm['files']):raise ValueError('DuplicateNativeManifestKey')
    selected=[]
    for source in SOURCES:
        entry=nm['sources'][source]
        if entry.get('sourceId')!=source or entry.get('rawSourcePayloadPublished') is not False or entry.get('independentlyAccepted') is not False:
            raise ValueError('NativeSourcePolicyMismatch')
        files=[f for f in nm['files'] if len(Path(f['key']).parts)==3 and Path(f['key']).parts[:2]==('records',source) and f['key'].endswith('.jsonl.gz')]
        if not files:raise ValueError('NativeSourceAssetsMissing')
        selected.extend((source,f,entry) for f in sorted(files,key=lambda x:x['key']))
    if len({f['key'] for f in bm['files']})!=len(bm['files']):raise ValueError('DuplicateBulkManifestKey')
    files={f['key']:f for f in bm['files']};sb=checked_asset(bulk,files['schema.json']);cb=checked_asset(bulk,files['contract.json'])
    if sha_bytes(sb)!=schema_sha or sha_bytes(cb)!=contract_sha:raise ValueError('SelectedSchemaContractMismatch')
    return nm,bm,selected,json.loads(sb)

def source_records(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        ordinal=0
        for line_ordinal,line in enumerate(stream):
            value=json.loads(line)
            records=value[1] if isinstance(value,list) and len(value)==2 and isinstance(value[1],list) else [value]
            for record_ordinal,record in enumerate(records):
                if not isinstance(record,dict):raise ValueError('NativeRecordShapeMismatch')
                yield ordinal,line_ordinal,record_ordinal,record;ordinal+=1

def selection_for(native_sha,bulk_sha,schema_sha,contract_sha):
    names=('run_north_star_basis_restoration.py','north_star_basis_restoration.py','north_star_derivations.py','derive_north_star_bulk.py')
    return {'nativeManifestByteSha256':native_sha,'normalizedManifestByteSha256':bulk_sha,'schemaByteSha256':schema_sha,'contractByteSha256':contract_sha,
            'rulesetVersion':VERSION,'codePins':{n:sha_file(Path(__file__).with_name(n)) for n in names},'selectedSources':list(SOURCES)}

def index_native(native,output,nm,selected,selection,deadline,budget,reserve):
    final=output/'native-index-manifest.json';path=output/'native-index.sqlite'
    if final.exists():
        m=json.loads(final.read_text())
        if m['selection']!=selection or sha_file(path)!=m['sqliteSha256']:raise ValueError('NativeIndexChanged')
        return m
    db=write_db(path,output)
    db.executescript('CREATE TABLE IF NOT EXISTS projections(resource_id TEXT PRIMARY KEY,source_id TEXT,payload_sha TEXT,payload BLOB,metrics INTEGER,unknown_states INTEGER) WITHOUT ROWID; CREATE TABLE IF NOT EXISTS imported(asset_key TEXT PRIMARY KEY,asset_sha TEXT,receipt_json TEXT) WITHOUT ROWID;')
    receipts={r[0]:json.loads(r[1]) for r in db.execute('SELECT asset_key,receipt_json FROM imported')}
    totals=collections.Counter();by_source={s:collections.Counter() for s in SOURCES}
    for r in receipts.values():totals.update(r['counts']);by_source[r['sourceId']].update(r['counts'])
    status='indexing-native'
    try:
        for source,entry,source_meta in selected:
            if entry['key'] in receipts:
                if receipts[entry['key']]['inputAsset']!=entry or receipts[entry['key']]['sourceEntryCanonicalSha256']!=digest(source_meta):raise ValueError('NativeCheckpointSelectionChanged')
                continue
            check_limits(output,deadline-15,budget,reserve);raw=checked_asset(native,entry);counts=collections.Counter()
            with db:
                for ordinal,line_ordinal,record_ordinal,record in source_records(raw):
                    if time.monotonic()>=deadline-15:raise TimeSliceComplete('native-asset-self-deadline')
                    counts['nativeRecords']+=1;p=native_projection(record,source,source_meta)
                    if p is None:continue
                    native_selection={'manifestByteSha256':selection['nativeManifestByteSha256'],'assetKey':entry['key'],'assetSha256':entry['sha256'],
                                      'assetRecordOrdinal':ordinal,'lineOrdinal':line_ordinal,'recordOrdinalInLine':record_ordinal}
                    p['inputNativeSelection']=native_selection;pb=encoded(p);compressed=zlib.compress(pb,1)
                    unknown=sum(v['sourceBasis']['state'] is None for v in p['metrics'].values())
                    db.execute('INSERT INTO projections VALUES (?,?,?,?,?,?)',(p['resourceId'],source,sha_bytes(pb),compressed,len(p['metrics']),unknown))
                    counts.update(nativeProfiles=1,ownStateMetrics=len(p['metrics']),unknownSourceStateMetrics=unknown,metricsWithoutOwnState=p['metricsWithoutOwnState'],compressedProjectionBytes=len(compressed))
                receipt={'sourceId':source,'inputAsset':entry,'sourceEntryCanonicalSha256':digest(source_meta),'counts':dict(counts)}
                db.execute('INSERT INTO imported VALUES (?,?,?)',(entry['key'],entry['sha256'],json.dumps(receipt,sort_keys=True,separators=(',',':'))))
            receipts[entry['key']]=receipt;totals.update(counts);by_source[source].update(counts)
            atomic_json(output/'native-progress.json',{'selection':selection,'status':status,'completedAssets':len(receipts),'expectedAssets':len(selected),'counts':dict(totals)})
        for source in SOURCES:
            if by_source[source]['nativeRecords']!=nm['sources'][source]['records']:raise ValueError('NativeSourceCountReconciliationMismatch')
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close();fsync_dir(output)
        result={'schemaVersion':FORMAT,'phase':'native-index','complete':True,'selection':selection,'counts':dict(totals),'sources':{s:dict(v) for s,v in by_source.items()},
                'completedAssets':len(receipts),'expectedAssets':len(selected),'sqliteSha256':sha_file(path),'sqliteBytes':path.stat().st_size,'rawNativeBodiesStored':False,'publicFiles':[]}
        atomic_json(final,result);return result
    except TimeSliceComplete:
        db.close();return {'schemaVersion':FORMAT,'phase':'native-index','complete':False,'status':'time-slice-complete','completedAssets':len(receipts),'counts':dict(totals)}
    finally:
        db.close()

def restore_shard(args):
    bulk,output,entry,ordinal,selection,schema,index_sha,deadline=args
    expected=dict(selection,inputAsset=entry,ordinal=ordinal,nativeIndexSha256=index_sha)
    target=output/'shards'/f'{ordinal:06d}';old=existing_shard(target,expected)
    if old:return old
    raw=checked_asset(bulk,entry);temp=target.with_name(target.name+'.tmp-'+uuid.uuid4().hex);temp.mkdir(parents=True)
    db=readonly(output/'native-index.sqlite');validator=validator_for(schema);counts=collections.Counter()
    try:
        with contextlib.ExitStack() as stack:
            sinks=[]
            for name in ('basis-restorations.jsonl.gz','matched-profiles.jsonl.gz','packet-locations.jsonl.gz'):
                f=stack.enter_context((temp/name).open('xb'));sinks.append(stack.enter_context(gzip.GzipFile(fileobj=f,mode='wb',mtime=0,compresslevel=1)))
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                for packet_ordinal,line in enumerate(stream):
                    if time.monotonic()>=deadline:raise TimeSliceComplete('normalized-shard-self-deadline')
                    packet=json.loads(line);validator.validate(packet);counts['packets']+=1
                    normalized_selection={'manifestByteSha256':selection['normalizedManifestByteSha256'],'assetKey':entry['key'],'assetSha256':entry['sha256'],'packetOrdinal':packet_ordinal}
                    for resource in packet['resources']:
                        sinks[2].write(encoded([resource['id'],entry['key'],packet_ordinal,entry['sha256']]))
                        counts['resourceLocators']+=1
                        row=db.execute('SELECT payload_sha,payload FROM projections WHERE resource_id=?',(resource['id'],)).fetchone()
                        if row is None:continue
                        pb=zlib.decompress(row[1])
                        if sha_bytes(pb)!=row[0]:raise ValueError('ProjectionBlobChanged')
                        p=json.loads(pb);side=restore(packet,p);counts['matchedNativeProfiles']+=1
                        counts['sourceMetricsWithoutOwnState']+=p['metricsWithoutOwnState']
                        unknown=sum(v['sourceBasis']['state'] is None for v in p['metrics'].values())
                        sinks[1].write(encoded([p['resourceId'],p['sourceId'],row[0],digest(packet),len(p['metrics']),unknown]))
                        if side:
                            side['inputNativeSelection']=p['inputNativeSelection'];side['inputNormalizedSelection']=normalized_selection
                            sinks[0].write(encoded(side));counts.update(sidecarPackets=1,restoredNutrientBasisTargets=side['matchedNutrientAssertions'],unknownSourceStateTargets=unknown)
        if counts['packets']!=entry['packets']:raise ValueError('NormalizedPacketCountMismatch')
        outputs=[]
        for name in ('basis-restorations.jsonl.gz','matched-profiles.jsonl.gz','packet-locations.jsonl.gz'):
            with (temp/name).open('rb') as f:os.fsync(f.fileno())
            outputs.append({'key':name,'bytes':(temp/name).stat().st_size,'sha256':sha_file(temp/name)})
        receipt={'schemaVersion':FORMAT,'selection':expected,'counts':dict(counts),'outputs':outputs}
        atomic_json(temp/'receipt.json',receipt);fsync_dir(temp);os.rename(temp,target);fsync_dir(target.parent);return receipt
    except BaseException:
        if temp.exists():shutil.rmtree(temp)
        raise
    finally:db.close()


def matched_proof(output,receipts,index_meta,deadline,budget,reserve,committed):
    db=write_db(output/'matched-proof.sqlite',output);reason={'value':None,'nextCheck':0}
    def progress():
        now=time.monotonic()
        if now>=deadline:reason['value']='deadline';return 1
        if now>=reason['nextCheck']:
            reason['nextCheck']=now+1
            try:check_limits(output,deadline,budget,reserve,committed)
            except (TimeSliceComplete,ValueError):reason['value']='budget';return 1
        return 0
    db.set_progress_handler(progress,10000)
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS matched(resource_id TEXT PRIMARY KEY,source_id TEXT,projection_sha TEXT,packet_sha TEXT,targets INTEGER,unknown_states INTEGER) WITHOUT ROWID;CREATE TABLE IF NOT EXISTS locations(resource_id TEXT PRIMARY KEY,asset_key TEXT,packet_ordinal INTEGER,asset_sha TEXT) WITHOUT ROWID;CREATE TABLE IF NOT EXISTS imported(shard INTEGER PRIMARY KEY,receipt_sha TEXT);')
        for n,r in sorted(receipts.items()):
            check_limits(output,deadline,budget,reserve,committed);pin=digest(r);old=db.execute('SELECT receipt_sha FROM imported WHERE shard=?',(n,)).fetchone()
            if old:
                if old[0]!=pin:raise ValueError('MatchedCheckpointChanged')
                continue
            with db:
                for name,table,width in [('matched-profiles.jsonl.gz','matched',6),('packet-locations.jsonl.gz','locations',4)]:
                    asset=next(a for a in r['outputs'] if a['key']==name);p=output/'shards'/f'{n:06d}'/asset['key']
                    if sha_file(p)!=asset['sha256']:raise ValueError('MatchedInputChanged')
                    with gzip.open(p,'rt',encoding='utf8') as f:
                        for line in f:db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in range(width))+')',json.loads(line))
                db.execute('INSERT INTO imported VALUES (?,?)',(n,pin))
        db.execute('ATTACH DATABASE ? AS source',('file:'+quote(str((output/'native-index.sqlite').resolve()),safe='/')+'?mode=ro&immutable=1',))
        queries={'normalizedResourceLocators':'SELECT count(*) FROM locations','nativeProfilesMatched':'SELECT count(*) FROM matched',
                 'matchedProfilesWithBasisTargets':'SELECT count(*) FROM matched WHERE targets>0',
                 'restoredNutrientBasisTargets':'SELECT coalesce(sum(targets),0) FROM matched',
                 'unknownSourceStateTargets':'SELECT coalesce(sum(unknown_states),0) FROM matched',
                 'nativeProfilesWithoutNormalizedMatch':'SELECT count(*) FROM source.projections p WHERE NOT EXISTS(SELECT 1 FROM matched m WHERE m.resource_id=p.resource_id)',
                 'projectionDigestMismatches':'SELECT count(*) FROM matched m JOIN source.projections p USING(resource_id) WHERE m.projection_sha<>p.payload_sha OR m.source_id<>p.source_id OR m.targets<>p.metrics OR m.unknown_states<>p.unknown_states'}
        result={name:{'sql':sql,'count':db.execute(sql).fetchone()[0]} for name,sql in queries.items()}
        if result['projectionDigestMismatches']['count']:raise ValueError('MatchedProjectionMismatch')
        if result['nativeProfilesMatched']['count']+result['nativeProfilesWithoutNormalizedMatch']['count']!=index_meta['counts']['nativeProfiles']:raise ValueError('MatchedNativeReconciliationMismatch')
        db.commit();db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close()
        return {'queries':result,'sqliteSha256':sha_file(output/'matched-proof.sqlite'),'acceptedIdentityJoins':0,'servedAppQueries':0}
    except TimeSliceComplete:return None
    except sqlite3.OperationalError:
        if reason['value']=='deadline':return None
        raise
    finally:db.close()


def restore_bulk(bulk,output,bm,schema,index_meta,selection,deadline,budget,reserve,workers):
    entries=[e for e in bm['files'] if e['key'].endswith('.jsonl.gz') and 'packets' in e];receipts={};remaining=[];committed=0
    (output/'shards').mkdir(exist_ok=True)
    for n,entry in enumerate(entries):
        expected=dict(selection,inputAsset=entry,ordinal=n,nativeIndexSha256=index_meta['sqliteSha256']);r=existing_shard(output/'shards'/f'{n:06d}',expected)
        if r:receipts[n]=r;committed+=sum(a['bytes'] for a in r['outputs'])+(output/'shards'/f'{n:06d}'/'receipt.json').stat().st_size
        else:remaining.append((n,entry))
    def summary(status):
        totals=collections.Counter()
        for r in receipts.values():totals.update(r['counts'])
        value={'schemaVersion':FORMAT,'phase':'restore-normalized','status':status,'complete':False,'selection':selection,'completedAssets':len(receipts),'expectedAssets':len(entries),'counts':dict(totals),'committedShardBytes':committed}
        atomic_json(output/'restore-progress.json',value);return value
    if (output/'manifest.json').exists():
        m=json.loads((output/'manifest.json').read_text())
        if m['selection']!=selection or remaining or sha_file(output/'matched-proof.sqlite')!=m['consumerProof']['sqliteSha256']:raise ValueError('FinalRestorationChanged')
        return m
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            pending={};cursor=0
            while cursor<len(remaining) or pending:
                while cursor<len(remaining) and len(pending)<workers and time.monotonic()<deadline-30:
                    check_limits(output,deadline-15,budget,reserve,committed);n,entry=remaining[cursor];cursor+=1
                    args=(bulk,output,entry,n,selection,schema,index_meta['sqliteSha256'],deadline-15);pending[pool.submit(restore_shard,args)]=n
                if not pending:break
                done,_=concurrent.futures.wait(pending,timeout=5,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in done:
                    n=pending.pop(f)
                    try:r=f.result()
                    except TimeSliceComplete:continue
                    receipts[n]=r;committed+=sum(a['bytes'] for a in r['outputs'])+(output/'shards'/f'{n:06d}'/'receipt.json').stat().st_size
                if done:summary('restoring-source-basis')
    except TimeSliceComplete:return summary('time-slice-complete')
    result=summary('time-slice-complete')
    if len(receipts)!=len(entries) or time.monotonic()>=deadline-30:return result
    if result['counts']['resourceLocators']!=bm['counts']['resources']:raise ValueError('FullResourceLocatorCountMismatch')
    if result['counts']['packets']!=bm['counts']['packets']:raise ValueError('FullNormalizedCountMismatch')
    proof=matched_proof(output,receipts,index_meta,deadline-15,budget,reserve,committed)
    if proof is None:return summary('proof-time-slice-complete')
    comparisons={'nativeProfilesMatched':'matchedNativeProfiles','matchedProfilesWithBasisTargets':'sidecarPackets','restoredNutrientBasisTargets':'restoredNutrientBasisTargets','unknownSourceStateTargets':'unknownSourceStateTargets','normalizedResourceLocators':'resourceLocators'}
    for query,counter in comparisons.items():
        if proof['queries'][query]['count']!=result['counts'].get(counter,0):raise ValueError('FinalShardQueryReconciliationMismatch')
    unmatched=proof['queries']['nativeProfilesWithoutNormalizedMatch']['count']
    coverage={'nativeProfilesSelected':index_meta['counts']['nativeProfiles'],'nativeProfilesMatched':proof['queries']['nativeProfilesMatched']['count'],
              'nativeProfilesUnmatched':unmatched,'normalizedPacketsScanned':result['counts']['packets'],'normalizedResourcesLocated':result['counts']['resourceLocators']}
    result.update(complete=True,status='full-selected-normalized-input-scanned-and-source-basis-candidates-materialized',consumerProof=proof,
                  allSelectedNativeProfilesMatched=unmatched==0,sourceCoverage=coverage,
                  nativeIndexBinding={'sqliteSha256':index_meta['sqliteSha256'],'manifestByteSha256':sha_file(output/'native-index-manifest.json')},
                  files=[{'key':f'shards/{n:06d}/'+a['key'],'bytes':a['bytes'],'sha256':a['sha256']} for n,r in sorted(receipts.items()) for a in r['outputs'] if a['key']=='basis-restorations.jsonl.gz'],
                  semanticStatus='candidate-not-admitted',publicationEligible=False,profileBasisUsed=False,originalsModified=False,
                  confidence={'status':'not-calibrated','probability':None},localOnlyArtifacts=['*.sqlite','shards/*/matched-profiles.jsonl.gz','shards/*/packet-locations.jsonl.gz','shards/*/receipt.json','selection.json','*-progress.json','native-index-manifest.json'])
    atomic_json(output/'manifest.json',result);return result


def run(phase,native,bulk,output,*,budget,seconds=1650,reserve=70*GIB,workers=1,native_sha=NATIVE_SHA,bulk_sha=BULK_SHA,schema_sha=SCHEMA_SHA,contract_sha=CONTRACT_SHA):
    deadline=time.monotonic()+seconds;nm,bm,selected,schema=load_inputs(native,bulk,native_sha,bulk_sha,schema_sha,contract_sha);selection=selection_for(native_sha,bulk_sha,schema_sha,contract_sha)
    output.mkdir(parents=True,exist_ok=True);fsync_dir(output.parent)
    with (output/'.writer.lock').open('a+b') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('OutputWriterAlreadyActive') from None
        config=output/'selection.json'
        if config.exists():
            if json.loads(config.read_text())!=selection:raise ValueError('OutputSelectionChanged')
        else:atomic_json(config,selection)
        if phase=='index':return index_native(native,output,nm,selected,selection,deadline,budget,reserve)
        path=output/'native-index-manifest.json'
        if not path.exists():raise ValueError('CompletedNativeIndexRequired')
        index_meta=json.loads(path.read_text())
        if not index_meta.get('complete') or index_meta['selection']!=selection or sha_file(output/'native-index.sqlite')!=index_meta['sqliteSha256']:raise ValueError('NativeIndexBindingMismatch')
        return restore_bulk(bulk,output,bm,schema,index_meta,selection,deadline,budget,reserve,workers)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['index','restore']);a.add_argument('native',type=Path);a.add_argument('bulk',type=Path);a.add_argument('output',type=Path);a.add_argument('--output-budget-bytes',type=int,required=True);a.add_argument('--workers',type=int,default=1);a.add_argument('--seconds',type=int,default=1650);args=a.parse_args()
    if not 1<=args.workers<=8 or not 30<=args.seconds<=1700 or args.output_budget_bytes<=0:raise ValueError('InvalidBounds')
    result=run(args.phase,args.native,args.bulk,args.output,budget=args.output_budget_bytes,seconds=args.seconds,workers=args.workers)
    print(json.dumps({k:v for k,v in result.items() if k!='files'},sort_keys=True))
