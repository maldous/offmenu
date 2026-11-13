import os,stat,json,hashlib,re,signal,collections,time
ROOT='/offmenu-corpus/'
HOST='/home/user/src/offmenu-data/'
NAMES=('common-data-reviewed-package-20261014','common-reference-delivery-final-20261014','common-national-semantic-final-20261014','measurement-terminology-final-qualified-20261014','recipe-expansion-final-qualified-20261014/common-graph','historical-recipe-quality-final-corrected-20261014')
COUNTS=('packets','resources','assertions','relations','translations')
SAFE=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,160}\Z')
SOURCE=re.compile(r'[a-z0-9][a-z0-9._-]{0,100}\Z')
SHA=re.compile(r'[0-9a-f]{64}\Z')
BYTES=0
START=time.monotonic()
def label(x):return x if isinstance(x,str) and SAFE.fullmatch(x) and '://' not in x else None
def integer(x):return type(x)is int and 0<=x<=10**18
def countmap(x):
    if not isinstance(x,dict) or len(x)>100 or not all(isinstance(k,str) and integer(v) for k,v in x.items()):raise ValueError('invalid_count_map_shape')
    return x
def read(path,ro=False):
    global BYTES
    if time.monotonic()-START>25:raise TimeoutError('time_budget')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        parts=path.strip('/').split('/')
        for i,part in enumerate(parts):
            nxt=os.open(part,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC|(os.O_DIRECTORY if i<len(parts)-1 else 0),dir_fd=fd);os.close(fd);fd=nxt
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size>4*1024*1024 or BYTES+a.st_size>16*1024*1024:raise ValueError('metadata_size_or_type')
        if ro and not os.fstatvfs(fd).f_flag&os.ST_RDONLY:raise ValueError('not_readonly')
        raw=b''
        while True:
            b=os.read(fd,65536)
            if not b:break
            raw+=b;BYTES+=len(b)
            if len(raw)>4*1024*1024 or BYTES>16*1024*1024:raise ValueError('metadata_growth')
        z=os.fstat(fd)
        if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns):raise ValueError('metadata_changed')
        obj=json.loads(raw)
        if not isinstance(obj,dict):raise ValueError('metadata_not_object')
        return obj,hashlib.sha256(raw).hexdigest()
    finally:os.close(fd)
def count_fields(d):return {k:d[k] for k in COUNTS if integer(d.get(k))} if isinstance(d,dict) else {}
def safe_keys(value):
    if isinstance(value,dict):return {(k if label(k) else 'key-sha256-'+hashlib.sha256(k.encode()).hexdigest()):safe_keys(v) for k,v in value.items()}
    if isinstance(value,list):return [safe_keys(v) for v in value]
    return value
def main():
    proof,proofsha=read(ROOT+'common-ready-six-package-global-20261014.json',True)
    quiet,quietsha=read(ROOT+'custody-positive-quiescence-20261014.json',True)
    mapping,mapsha=read('/offmenu/corpus/common-source-mappings.json')
    contract,contractsha=read('/offmenu/corpus/common-data-contract.json')
    schema,schemas=read('/offmenu/corpus/common-data.schema.json')
    custody,custodysha=read('/offmenu/docs/OFFMENU_CUSTODY_HANDOVER_20261014.json')
    expected={s['sourceId']:s['sourceRecords'] for s in mapping['sources']};countmap(expected)
    pp=proof.get('packages',[])
    if not isinstance(pp,list) or len(pp)>20:raise ValueError('proof_packages_shape')
    bypath={p.get('directory'):p for p in pp if isinstance(p,dict) and isinstance(p.get('directory'),str)}
    out={'schema':'offmenu-corpus-metadata-reconciliation/1','qualification_rerun':False,'raw_payloads_read':False,'checks':{},'packages':[]}
    checks=out['checks'];checks['proof_exact_six_package_paths']=set(bypath)=={HOST+n for n in NAMES} and len(pp)==6
    checks['proof_package_count']=proof.get('packageCount')==6
    checks['proof_schema_hash_current']=proof.get('schemaByteSha256')==schemas
    checks['proof_contract_hash_current']=proof.get('contractByteSha256')==contractsha
    checks['mapping_contract_hash_current']=mapping.get('contractSha256')==contractsha
    checks['mapping_declared_counts_match']=mapping.get('sourceCount')==len(expected) and mapping.get('sourceRecordTotal')==sum(expected.values())
    checks['custody_exact_six_ready_paths']=custody.get('readyPackages')==list(NAMES)
    aggregate=collections.Counter();coverage={};declared_asset_count=0
    for index,n in enumerate(NAMES):
        m,h=read(ROOT+n+'/manifest.json',True);p=bypath.get(HOST+n,{})
        counts=count_fields(m.get('counts'));aggregate.update(counts)
        pc=count_fields(p.get('observedCounts'))
        if index==0:
            foodon,fsha=read(ROOT+n+'/foodon-source-manifest.json',True)
            admitted={'world-recipes':m.get('recipeRecords'),'foodon':foodon.get('counts',{}).get('classes')}
            countmap(admitted)
            source_id=None
        else:
            source=m.get('source',{})
            source_id=m.get('sourceId') or (source.get('id') if isinstance(source,dict) else None)
            obs=m.get('observedSourceRecords')
            admitted={source_id:obs} if integer(obs) else obs
            countmap(admitted)
        covered=dict(admitted)
        if source_id=='recipe-expansion-20261014':covered={source_id:sum(admitted.values())}
        if source_id=='smithsonian-archive':covered={}
        duplicates=sorted(set(covered)&set(coverage))
        coverage.update(covered)
        files=m.get('files',[])
        if not isinstance(files,list):raise ValueError('manifest_files_shape')
        declared_asset_count+=len(files)
        row={'package':n,'schemaVersion':label(m.get('schemaVersion')),'releaseId':label(m.get('releaseId')),'status':label(m.get('status')),'manifestByteSha256':h,'proof_manifest_hash_match':p.get('manifestByteSha256')==h,'proof_counts_match':pc==counts and len(counts)==5,'proof_admitted_records_match':p.get('admittedSourceRecords')==admitted,'counts':counts,'admittedSourceRecords':admitted,'mappingCoverage':covered,'duplicate_coverage_ids':duplicates,'declared_files':len(files),'producer_manifestSha256':m.get('manifestSha256') if isinstance(m.get('manifestSha256'),str) and SHA.fullmatch(m['manifestSha256']) else None}
        if index==0:row['grandfather_foodon_manifestSha256']=fsha
        else:
            row['declared_complete']=m.get('complete')is True
            row['expected_observed_records_equal']=m.get('expectedSourceRecords')==m.get('observedSourceRecords')
            row['expected_observed_counts_equal']=m.get('expectedCounts')==m.get('observedCounts')==m.get('counts')
        out['packages'].append(row)
    checks['proof_aggregate_graph_counts_match']=count_fields(proof.get('aggregateObservedCounts'))==dict(aggregate)
    checks['proof_declared_asset_count_match']=proof.get('aggregateObservedCounts',{}).get('assets')==declared_asset_count
    checks['custody_graph_counts_match']=count_fields(custody.get('readyCombinedCounts'))==dict(aggregate)
    checks['custody_asset_count_match']=custody.get('readyCombinedCounts',{}).get('assets')==declared_asset_count
    out['coverage']={'mapping_sources':len(expected),'mapping_records':sum(expected.values()),'six_package_sources':len(coverage),'six_package_records':sum(coverage.values()),'uncovered_mapping_sources':{k:v for k,v in expected.items() if k not in coverage},'covered_count_mismatches':{k:{'mapping':expected.get(k),'six_package':v} for k,v in coverage.items() if expected.get(k)!=v},'graph_counts':dict(aggregate),'manifest_listed_assets':declared_asset_count}
    out['proof']={'schemaVersion':label(proof.get('schemaVersion')),'status':label(proof.get('status')),'sha256':proofsha,'schemaByteSha256':proof.get('schemaByteSha256') if SHA.fullmatch(str(proof.get('schemaByteSha256'))) else None,'contractByteSha256':proof.get('contractByteSha256') if SHA.fullmatch(str(proof.get('contractByteSha256'))) else None}
    out['custody']={'sha256':custodysha,'status':label(custody.get('status')),'quiescence_receipt_sha256':quietsha,'quiescence_status':label(quiet.get('status')),'quiescence_schema':label(quiet.get('schemaVersion')),'current_process_quiescence_verified':False}
    out['current_definition_hashes']={'mapping':mapsha,'contract':contractsha,'schema':schemas}
    out['metadata_bytes_read']=BYTES
    return safe_keys(out)
if __name__=='__main__':
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('deadline')));signal.alarm(28)
    try:r=main()
    except Exception as e:r={'schema':'offmenu-corpus-metadata-reconciliation/1','error_class':type(e).__name__,'reason':str(e) if isinstance(e,(ValueError,TimeoutError)) and re.fullmatch('[a-z_]{1,80}',str(e)) else 'bounded_metadata_reconciliation_failed','qualification_rerun':False}
    signal.alarm(0);print(json.dumps(r,sort_keys=True,separators=(',',':')))
