#!/usr/bin/env python3
"""Landing access evidence, or explicitly pinned reviewed raw collection.

Legacy mode is landing metadata only. Collection mode uses CachedAcquirer;
discovery URLs never become approved download selections automatically.
"""
import argparse,concurrent.futures,datetime,hashlib,json,re,urllib.request,urllib.parse
from pathlib import Path

def collect(source,output):
 key=source['sourceId'];saved=output/(hashlib.sha256(key.encode()).hexdigest()[:24]+'.json')
 if saved.exists():return json.loads(saved.read_text())
 url=source['url']; result={'sourceId':key,'requestedUrl':url,'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'landing-page access metadata only','datasetCollected':False,'rightsDecision':'requires primary licence review'}
 try:
  parsed=urllib.parse.urlsplit(url)
  if parsed.scheme not in ['http','https'] or not parsed.hostname or parsed.username:raise ValueError('Unsupported source URL')
  req=urllib.request.Request(url,headers={'User-Agent':'OffMenu-source-discovery/1.0'})
  with urllib.request.urlopen(req,timeout=20) as response:
   kind=response.headers.get('Content-Type','');result.update(httpStatus=response.status,finalUrl=response.url,contentType=kind)
   if 'html' in kind or 'text' in kind or 'json' in kind:
    body=response.read(1024*1024+1);result['landingPageTruncated']=len(body)>1024*1024;body=body[:1024*1024]
    text=body.decode('utf-8',errors='replace');result['landingPageSha256']=hashlib.sha256(body).hexdigest(); (saved.with_suffix('.html')).write_bytes(body)
    title=re.search(r'<title[^>]*>(.*?)</title>',text,re.I|re.S);result['title']=re.sub(r'\s+',' ',title[1]).strip() if title else None
    links=re.findall(r'href\s*=\s*["\']([^"\']+)["\']',text,re.I)
    result['downloadCandidates']=list(dict.fromkeys(urllib.parse.urljoin(response.url,x) for x in links if re.search(r'\.(csv|tsv|json|jsonl|xlsx?|zip|gz|xml)(?:[?#]|$)',x,re.I)))
    result['rightsLinks']=list(dict.fromkeys(urllib.parse.urljoin(response.url,x) for x in links if re.search(r'licen[cs]e|copyright|terms|reuse|legal',x,re.I)))
   else:result['bodyDownloaded']=False
 except Exception as e:result['error']=str(e)[:300];result['httpStatus']=getattr(e,'code',None)
 saved.write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path)
 p.add_argument('--collection-registry',type=Path)
 p.add_argument('--registry-sha256')
 p.add_argument('--describe-registry',action='store_true',help='Metadata-only catalog summary and unresolved descriptors; no acquisition')
 p.add_argument('--country',help='Read-only exact country source lookup from the same v3 registry, e.g. US')
 p.add_argument('--required-type',help='Optional exact canonical type for --country')
 a=p.parse_args()
 if bool(a.collection_registry)!=bool(a.registry_sha256):p.error('Collection requires exact registry path and SHA-256')
 if a.describe_registry and not a.collection_registry:p.error('Describe requires a pinned collection registry')
 if a.country and not a.collection_registry:p.error('Country lookup requires a pinned collection registry')
 if a.country and a.describe_registry:p.error('Select country lookup or describe')
 if a.required_type and not a.country:p.error('Required type needs country lookup')
 if a.collection_registry:
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from offmenu.refresh.acquisition import collect_registry,describe_collection_registry,lookup_country_sources,MAX_REGISTRY_METADATA
  from offmenu.refresh.core import RefreshError,digest,strict_json,safe_path,atomic_json
  try:
   if a.describe_registry or a.country:
    path=safe_path(a.collection_registry)
    if digest(path,max_bytes=MAX_REGISTRY_METADATA)['sha256']!=a.registry_sha256:raise RefreshError('collection-registry-pin-mismatch')
    registry=strict_json(path.read_bytes());report=describe_collection_registry(registry)
    output=safe_path(a.output);output.mkdir(parents=True,exist_ok=True)
    if a.country:
     report=lookup_country_sources(registry,a.country,a.required_type)
     atomic_json(output/('country-'+a.country+'-sources.json'),report)
     print(json.dumps({'status':'country-source-lookup','country':a.country,'requirements':len(report['requirements']),'acquisitionEnabledByLookup':False}));return 0
    atomic_json(output/'unresolved-descriptors.json',{'scope':'sanitized metadata-only descriptors; no dataset bodies or acquisition','assets':report.pop('unresolved')})
    atomic_json(output/'registry-summary.json',report)
    print(json.dumps(report));return 0
   report=collect_registry(a.collection_registry,a.registry_sha256,a.output)
  except (RefreshError,OSError,ValueError,TypeError,KeyError) as error:
   print(json.dumps({'status':'collection-rejected','error':str(error) if isinstance(error,RefreshError) else type(error).__name__}));return 2
  print(json.dumps({'status':'collection-reported','verifiedSources':report['verifiedSources'],'failedSources':report['failedSources'],'network':report['network'],'countryComplete':False}))
  return 1 if report['failedSources'] else 0
 a.output.mkdir(parents=True,exist_ok=True)
 root=Path(__file__).resolve().parents[1];sources=json.loads((root/'docs/source-delivery-ledger.json').read_text())['sources'];results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for f in concurrent.futures.as_completed([pool.submit(collect,s,a.output) for s in sources]):
   results.append(f.result())
   if len(results)%50==0:print(json.dumps({'sourcesChecked':len(results),'total':len(sources)}),flush=True)
 report={'schema':'offmenu-source-access/1','checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':sorted(results,key=lambda x:x['sourceId']),'sourceCount':len(sources),'scope':'All registered landing-page access checks; download/rights links are candidates, not licence or data acceptance.'};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'complete','sourcesChecked':len(results)}))
if __name__=='__main__':raise SystemExit(main())
