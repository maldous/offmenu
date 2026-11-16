"""Finite in-memory storage estimate; never a corpus coverage/acceptance proof."""
import argparse,collections,contextlib,fcntl,gzip,hashlib,io,json,math,sqlite3,sys,time,zlib
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'candidate/scripts')]
import run_north_star_basis_restoration as R

def sized_db(ddl):
    db=sqlite3.connect(':memory:');db.execute('PRAGMA page_size=16384');db.execute(ddl)
    return db,db.execute('PRAGMA page_count').fetchone()[0]*16384

def measure(bulk,output,index_manifest_pin,seconds=600):
    if type(seconds) is not int or not 1<=seconds<=1200:raise ValueError('StrictMeasurementDeadlineRequired')
    deadline=time.monotonic()+seconds
    with (output/'.writer.lock').open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_SH|fcntl.LOCK_NB)
        raw=(output/'native-index-manifest.json').read_bytes()
        if R.sha_bytes(raw)!=index_manifest_pin:raise ValueError('NativeIndexManifestPinMismatch')
        meta=json.loads(raw)
        if meta.get('complete') is not True:raise ValueError('CompletedNativeIndexRequired')
        loaded={'run_north_star_basis_restoration.py':Path(R.__file__),'north_star_basis_restoration.py':Path(R.restore.__code__.co_filename),'derive_north_star_bulk.py':Path(R.encoded.__code__.co_filename),'north_star_derivations.py':Path(R.digest.__code__.co_filename)}
        loaded_pins={name:R.sha_file(path) for name,path in loaded.items()}
        if loaded_pins!=meta['selection']['codePins']:raise ValueError('LoadedDerivationCodePinMismatch')
        b=(bulk/'manifest.json').read_bytes()
        if R.sha_bytes(b)!=meta['selection']['normalizedManifestByteSha256']:raise ValueError('NormalizedManifestPinMismatch')
        bm=json.loads(b)
        if R.sha_file(output/'native-index.sqlite')!=meta['sqliteSha256']:raise ValueError('NativeIndexChanged')
        assets=[e for e in bm['files'] if e['key'].endswith('.jsonl.gz') and 'packets' in e]
        ordinals=sorted({(len(assets)-1)*n//5 for n in range(6)})
        counts=collections.Counter();file_sizes=collections.Counter();selected=[]
        with contextlib.ExitStack() as stack:
            db=R.readonly(output/'native-index.sqlite');stack.callback(db.close)
            loc,loc_base=sized_db('CREATE TABLE locations(resource_id TEXT PRIMARY KEY,asset_key TEXT,packet_ordinal INTEGER,asset_sha TEXT) WITHOUT ROWID')
            mat,mat_base=sized_db('CREATE TABLE matched(resource_id TEXT PRIMARY KEY,source_id TEXT,projection_sha TEXT,packet_sha TEXT,targets INTEGER,unknown_states INTEGER) WITHOUT ROWID')
            stack.callback(loc.close);stack.callback(mat.close)
            for ordinal in ordinals:
                if time.monotonic()>=deadline:raise TimeoutError('MeasurementDeadline')
                entry=assets[ordinal];sinks=[io.BytesIO() for _ in range(3)]
                with contextlib.ExitStack() as gzstack:
                    gz=[gzstack.enter_context(gzip.GzipFile(fileobj=s,mode='wb',mtime=0,compresslevel=1)) for s in sinks]
                    with gzip.GzipFile(fileobj=io.BytesIO(R.checked_asset(bulk,entry))) as stream:
                        packets=0
                        for packet_ordinal,line in enumerate(stream):
                            if time.monotonic()>=deadline:raise TimeoutError('MeasurementDeadline')
                            packet=json.loads(line);packets+=1;counts['packets']+=1
                            norm={'manifestByteSha256':meta['selection']['normalizedManifestByteSha256'],'assetKey':entry['key'],'assetSha256':entry['sha256'],'packetOrdinal':packet_ordinal}
                            for resource in packet['resources']:
                                location=[resource['id'],entry['key'],packet_ordinal,entry['sha256']]
                                gz[2].write(R.encoded(location));loc.execute('INSERT INTO locations VALUES (?,?,?,?)',location);counts['resources']+=1
                                row=db.execute('SELECT payload_sha,payload FROM projections WHERE resource_id=?',(resource['id'],)).fetchone()
                                if row is None:continue
                                pb=zlib.decompress(row[1])
                                if R.sha_bytes(pb)!=row[0]:raise ValueError('ProjectionBlobChanged')
                                projection=json.loads(pb);side=R.restore(packet,projection);counts['matchedProfiles']+=1
                                unknown=sum(x['sourceBasis']['state'] is None for x in projection['metrics'].values())
                                matched=[projection['resourceId'],projection['sourceId'],row[0],R.digest(packet),len(projection['metrics']),unknown]
                                gz[1].write(R.encoded(matched));mat.execute('INSERT INTO matched VALUES (?,?,?,?,?,?)',matched)
                                if side:
                                    side['inputNativeSelection']=projection['inputNativeSelection'];side['inputNormalizedSelection']=norm
                                    gz[0].write(R.encoded(side));counts['sidecars']+=1;counts['basisTargets']+=side['matchedNutrientAssertions']
                        if packets!=entry['packets']:raise ValueError('SelectedPacketCountMismatch')
                for name,sink in zip(('basisGzip','matchedGzip','locatorGzip'),sinks):file_sizes[name]+=len(sink.getvalue())
                selected.append({'ordinal':ordinal,'key':entry['key'],'bytes':entry['bytes'],'sha256':entry['sha256'],'packets':entry['packets']})
            sizes={'matchedSqliteIncrementBytes':mat.execute('PRAGMA page_count').fetchone()[0]*16384-mat_base,'locatorSqliteIncrementBytes':loc.execute('PRAGMA page_count').fetchone()[0]*16384-loc_base}
        if not counts['matchedProfiles'] or not counts['resources']:raise ValueError('RepresentativeMatchedProfilesRequired')
        profiles=meta['counts']['nativeProfiles'];resources=bm['counts']['resources']
        estimate={k:math.ceil(v*(resources/counts['resources'] if k=='locatorGzip' else profiles/counts['matchedProfiles'])) for k,v in file_sizes.items()}
        estimate.update(matchedSqlite=math.ceil(sizes['matchedSqliteIncrementBytes']*profiles/counts['matchedProfiles']),locatorSqlite=math.ceil(sizes['locatorSqliteIncrementBytes']*resources/counts['resources']))
        estimate['receiptAndFixedOverhead']=len(assets)*8192+1024**2
        growth=sum(estimate.values())
        if time.monotonic()>=deadline:raise TimeoutError('MeasurementDeadline')
        return {'schemaVersion':'offmenu-basis-phase2-storage-estimate/1','measurementVersion':'north-star-basis-phase2-storage/1','measurementHelperSha256':R.sha_file(Path(__file__)),'loadedDerivationCodePins':loaded_pins,'measurementOnly':True,'rawValuesExported':False,'newDataFilesWritten':False,
                'indexManifestSha256':index_manifest_pin,'nativeIndexSqliteSha256':meta['sqliteSha256'],'sourceSelection':meta['selection'],'selectedAssets':selected,
                'sampleCounts':dict(counts),'compressedSampleBytes':dict(file_sizes),'sampleSqliteIncrementBytes':sizes,'fullNativeProfiles':profiles,'fullNormalizedResources':resources,
                'estimatedAdditionalNamedBytes':estimate,'estimatedAdditionalNamedTotalBytes':growth,'retainedNativeIndexBytes':meta['sqliteBytes'],
                'suggestedAbsoluteTotalBudgetBytes':meta['sqliteBytes']+math.ceil(growth*1.35)+512*1024**2,
                'limits':'Six deterministic manifest-spaced assets; estimate only, not guaranteed storage or full coverage. Absolute producer cap, actual free reserve and ordinary aggregate admission remain required. Includes retained native index plus sidecars, local matched/locator shard files, final matched/locator SQLite and receipt overhead. SQLite transient unlinked files are not fully bounded by named-output accounting.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bulk',type=Path);p.add_argument('output',type=Path);p.add_argument('index_manifest_pin');a=p.parse_args()
    print(json.dumps(measure(a.bulk,a.output,a.index_manifest_pin),sort_keys=True))
