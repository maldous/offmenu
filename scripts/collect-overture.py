#!/usr/bin/env python3
"""Reconcile all pinned Overture place files and normalize food-related sites locally."""
import argparse,collections,datetime,gzip,hashlib,json,re,shutil
from pathlib import Path
FOOD_ROOTS={'food_and_drink','food_and_beverage_store','farmers_market','farm'}
NON_FOOD={'tobacco_shop','vape_shop','e-cigarette_shop','smoke_shop'}
LICENSES={'CDLA-Permissive-2.0','Apache-2.0','CC0-1.0'}
SOURCE='overture-food-places'

def eligible(row):
 hierarchy=set((row.get('taxonomy') or {}).get('hierarchy') or [])
 return bool(hierarchy & FOOD_ROOTS) and not bool(hierarchy & NON_FOOD)

def normalize(row,release,checksum,fetched_at):
 key=row.get('id');names=row.get('names') or {};name=names.get('primary');taxonomy=row.get('taxonomy') or {};hierarchy=taxonomy.get('hierarchy') or []
 if not key or not isinstance(name,str) or not name.strip():raise ValueError('Missing place identity or primary name')
 sources=row.get('sources') or [];licenses=sorted({s.get('license') for s in sources if s.get('license')});datasets=sorted({s.get('dataset') for s in sources if s.get('dataset')})
 if not licenses or any(x not in LICENSES for x in licenses) or any(not s.get('license') for s in sources):raise ValueError('Missing or unreviewed source licence')
 countries=sorted({a.get('country') for a in row.get('addresses') or [] if isinstance(a.get('country'),str) and re.fullmatch('[A-Z]{2}',a['country'])})
 if 'food_and_beverage_store' in hierarchy or 'farmers_market' in hierarchy:kind='retailer';role='source-described-food-retailer'
 elif 'farm' in hierarchy:kind='site';role='source-described-agricultural-site; food production unverified'
 else:kind='site';role='source-described-food-venue'
 common=names.get('common') or {};common=dict(common) if isinstance(common,list) else common
 language_names={k:v for k,v in common.items() if isinstance(k,str) and isinstance(v,str) and k not in ['__proto__','constructor','prototype']}
 dates=sorted({s.get('update_time') for s in sources if s.get('update_time')});locations=[{k:a.get(k) for k in ['locality','region','country'] if a.get(k)} for a in row.get('addresses') or []]
 return {'schemaVersion':'1.0','kind':kind,'id':SOURCE+':'+kind+':'+key,'countries':countries,
  'provenance':{'sourceId':SOURCE,'recordId':key,'url':'https://docs.overturemaps.org/guides/places/','license':' / '.join(licenses),'licenseUrl':'https://docs.overturemaps.org/attribution/#places','attribution':'Overture Maps Foundation; '+', '.join(datasets),'visibility':'public','fetchedAt':fetched_at,'sourceDate':dates[-1] if dates else release,'releaseId':release,'archiveSha256':checksum,'transform':'offmenu-overture/1','changes':'Selected food-related place metadata; source names and taxonomy retained, contacts/street addresses/geometry omitted, ownership and inventory unverified.','licenseNotices':['CDLA-Permissive-2.0.txt','Apache-2.0.txt','FOURSQUARE-NOTICE.txt'],'copyright':'Foursquare source data: Copyright 2024 Foursquare Labs, Inc.; full publisher NOTICE retained.' if 'Apache-2.0' in licenses else 'Original provider notices retained.'},
  'data':{'name':name,'names':language_names,'identifiers':[{'system':'Overture-GERS','value':key}],'role':role,'taxonomy':taxonomy,'basicCategory':row.get('basic_category'),'locations':locations,'countryBasis':'Source address country, not independent territorial/market verification','sourceReportedOperatingStatus':row.get('operating_status'),'existenceConfidence':row.get('confidence'),'sourceProviders':datasets,'sourceLicenses':licenses,'inventoryAvailability':'unknown','ownershipVerified':False,'dietQualification':'unknown','reviewStatus':'source-reference-unreviewed','sourceVersion':row.get('version')}}

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def collect(originals,output,license_dir):
 import duckdb
 import pyarrow.parquet as pq
 if output.exists():raise ValueError('Immutable output exists')
 license_documents=json.loads((license_dir/'manifest.json').read_text())
 for document in license_documents:
  key=document['key']
  if not re.fullmatch(r'[-A-Za-z0-9.]+\.txt',key):raise ValueError('Invalid licence filename')
  path=license_dir/key
  if path.stat().st_size!=document['bytes'] or digest(path)!=document['sha256']:raise ValueError('Licence checksum mismatch')
 acquisition=json.loads((originals/'acquisition-complete.json').read_text());release=acquisition['releaseId'];files=acquisition['files'];pending=output.with_name(output.name+'.partial');pending.mkdir(parents=True,exist_ok=True);projection=pending/'source-projection';projection.mkdir(exist_ok=True)
 db=duckdb.connect(str(pending/'source-index.duckdb'));db.execute("SET memory_limit='4GB'");db.execute('SET threads=4');
 counts={'raw':0,'eligible':0,'accepted':0,'duplicates':0,'quarantined':0,'excludedOutsideFoodTaxonomyScope':0,'records':0};country_counts=collections.Counter();kind_counts=collections.Counter();license_counts=collections.Counter();source_counts=collections.Counter();reconciled=[];writers={};quarantine=(pending/'quarantine.jsonl').open('w');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 paths=[item['path'] for item in files]
 predicate="(list_contains(taxonomy.hierarchy,'food_and_drink') OR list_contains(taxonomy.hierarchy,'food_and_beverage_store') OR list_contains(taxonomy.hierarchy,'farmers_market') OR list_contains(taxonomy.hierarchy,'farm')) AND NOT (list_contains(taxonomy.hierarchy,'tobacco_shop') OR list_contains(taxonomy.hierarchy,'vape_shop') OR list_contains(taxonomy.hierarchy,'e-cigarette_shop') OR list_contains(taxonomy.hierarchy,'smoke_shop'))"
 total,missing,distinct=db.execute('SELECT count(*),count(*) FILTER (WHERE id IS NULL),count(DISTINCT id) FROM read_parquet(?) WHERE '+predicate,[paths]).fetchone()
 if total-missing!=distinct:raise ValueError('Duplicate GERS IDs require explicit source reconciliation')
 print(json.dumps({'eligibleRowsPreflight':total,'missingIds':missing,'distinctIds':distinct}),flush=True)
 for index,item in enumerate(files):
  path=Path(item['path'])
  if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:raise ValueError('Original parquet checksum mismatch')
  parquet=pq.ParquetFile(path);raw_count=parquet.metadata.num_rows;selected=projection/(str(index)+'.parquet');literal="'"+str(path).replace("'","''")+"'";target="'"+str(selected).replace("'","''")+"'"
  predicate="(list_contains(taxonomy.hierarchy,'food_and_drink') OR list_contains(taxonomy.hierarchy,'food_and_beverage_store') OR list_contains(taxonomy.hierarchy,'farmers_market') OR list_contains(taxonomy.hierarchy,'farm')) AND NOT (list_contains(taxonomy.hierarchy,'tobacco_shop') OR list_contains(taxonomy.hierarchy,'vape_shop') OR list_contains(taxonomy.hierarchy,'e-cigarette_shop') OR list_contains(taxonomy.hierarchy,'smoke_shop'))"
  db.execute('COPY (SELECT id,names,taxonomy,basic_category,sources,addresses,confidence,operating_status,version FROM read_parquet('+literal+') WHERE '+predicate+') TO '+target+' (FORMAT PARQUET,COMPRESSION ZSTD)')
  accepted_input=pq.ParquetFile(selected);eligible_count=accepted_input.metadata.num_rows;counts['raw']+=raw_count;counts['eligible']+=eligible_count;counts['excludedOutsideFoodTaxonomyScope']+=raw_count-eligible_count
  for batch in accepted_input.iter_batches(batch_size=10000):
   candidates=batch.to_pylist()
   for row in candidates:
    key=row.get('id')
    try:
     if not eligible(row):raise ValueError('SQL/Python eligibility disagreement')
     record=normalize(row,release,item['sha256'],now);shard=hashlib.sha256(key.encode()).hexdigest()[:2]
     if shard not in writers:writers[shard]=gzip.open(pending/(shard+'.jsonl.gz'),'wt',encoding='utf8',compresslevel=1)
     writers[shard].write(json.dumps([record],ensure_ascii=False,separators=(',',':'))+'\n');counts['accepted']+=1;counts['records']+=1;kind_counts[record['kind']]+=1
     for country in record['countries']:country_counts[country]+=1
     for licence in record['data']['sourceLicenses']:license_counts[licence]+=1
     for provider in record['data']['sourceProviders']:source_counts[provider]+=1
    except Exception as e:counts['quarantined']+=1;quarantine.write(json.dumps({'id':key,'reason':str(e)})+'\n')
   if counts['eligible'] and counts['records']%100000<len(candidates):print(json.dumps({'normalizedRecords':counts['records'],'countries':len(country_counts),'part':index}),flush=True)
  reconciled.append({'key':item['key'],'rawRows':raw_count,'eligibleRows':eligible_count,'sourceSha256':item['sha256']});print(json.dumps({'partComplete':index,'parts':len(files),'rawRows':counts['raw'],'records':counts['records'],'quarantined':counts['quarantined']}),flush=True)
 for writer in writers.values():writer.close()
 quarantine.close();db.close()
 if counts['raw']!=counts['accepted']+counts['duplicates']+counts['quarantined']+counts['excludedOutsideFoodTaxonomyScope']:raise ValueError('Full place reconciliation failed')
 partitions=[{'key':p.name,'records':None,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(pending.glob('*.jsonl.gz'))]
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':SOURCE,'releaseId':release,'status':'normalized','counts':counts,'normalizedRows':counts['records'],'countries':dict(country_counts),'kinds':dict(kind_counts),'licenses':dict(license_counts),'sourceProviders':dict(source_counts),'sourceFiles':reconciled,'partitions':partitions,'archiveSha256':hashlib.sha256(json.dumps(acquisition,sort_keys=True).encode()).hexdigest(),'license':'Per-record CDLA-Permissive-2.0 / Apache-2.0 / CC0-1.0; notices retained','attribution':'Overture Maps Foundation and original providers','scope':'Every row in all 16 pinned place Parquet files examined. All food/drink venues, non-tobacco food/beverage stores, farmers markets and agricultural farm references selected. No confidence or first-N truncation; unrelated categories explicitly excluded. Place category, operation and country remain source assertions.','publication':'local only','completedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 manifest['licenseDocuments']=license_documents
 (pending/'licenses').mkdir(exist_ok=True)
 for document in license_documents:shutil.copyfile(license_dir/document['key'],pending/'licenses'/document['key'])
 manifest['selectionCriteria']={'includeHierarchy':sorted(FOOD_ROOTS),'excludeHierarchy':sorted(NON_FOOD),'confidenceThreshold':None,'recordLimit':None}
 (pending/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');pending.rename(output);print(json.dumps({'status':'normalized',**counts,'countryCount':len(country_counts)}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('output',type=Path);p.add_argument('--license-dir',type=Path,required=True);a=p.parse_args();collect(a.originals,a.output,a.license_dir)
