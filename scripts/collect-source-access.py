#!/usr/bin/env python3
"""Collect access evidence for every registered source; this is not dataset ingestion."""
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
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 root=Path(__file__).resolve().parents[1];sources=json.loads((root/'docs/source-delivery-ledger.json').read_text())['sources'];results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for f in concurrent.futures.as_completed([pool.submit(collect,s,a.output) for s in sources]):
   results.append(f.result())
   if len(results)%50==0:print(json.dumps({'sourcesChecked':len(results),'total':len(sources)}),flush=True)
 report={'schema':'offmenu-source-access/1','checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':sorted(results,key=lambda x:x['sourceId']),'sourceCount':len(sources),'scope':'All registered landing-page access checks; download/rights links are candidates, not licence or data acceptance.'};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'complete','sourcesChecked':len(results)}))
if __name__=='__main__':main()
