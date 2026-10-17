#!/usr/bin/env python3
"""Normalize the complete collected Wikidata direct-type food-business query."""
import argparse,datetime,gzip,hashlib,json,urllib.request,urllib.parse,urllib.error,time
from pathlib import Path
ROLES={'Q1252971':'food-manufacturer','Q18043413':'supermarket-chain','Q132777643':'grocery-store-chain'}
def api(req):
 for attempt in range(5):
  time.sleep(3)
  try:
   with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
  except urllib.error.HTTPError as e:
   if e.code not in [429,502,503,504] or attempt==4:raise
   delay=min(60,max(20,int(e.headers.get('Retry-After','30'))));print(json.dumps({'retry':e.code,'waitSeconds':delay}),flush=True);time.sleep(delay)
def collect(snapshot,output,countrymap=None):
 if output.exists():raise ValueError('Immutable output exists')
 raw=snapshot.read_bytes();bindings=json.loads(raw)['results']['bindings'];country_ids=sorted({r['country']['value'].rsplit('/',1)[-1] for r in bindings if 'country'in r});iso=json.loads(countrymap.read_text()) if countrymap else {}
 for start in range(0 if not countrymap else len(country_ids),len(country_ids),50):
  url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbgetentities','ids':'|'.join(country_ids[start:start+50]),'props':'claims','format':'json'})
  req=urllib.request.Request(url,headers={'User-Agent':'OffMenu-local-food-collection/1.0'})
  entities=api(req)['entities']
  for q,d in entities.items():
   codes={s['mainsnak'].get('datavalue',{}).get('value') for s in d.get('claims',{}).get('P297',[])};codes={x for x in codes if isinstance(x,str) and len(x)==2 and x.isupper()}
   if len(codes)==1:iso[q]=codes.pop()
 output.mkdir(parents=True);(output/'country-iso-evidence.json').write_text(json.dumps(iso,indent=2)+'\n');entities={};now=datetime.datetime.now(datetime.timezone.utc).isoformat();counts={'raw':len(bindings),'accepted':0,'duplicates':0,'quarantined':0,'excluded':0,'records':0};unresolved=[]
 for b in bindings:
  q=b['entity']['value'].rsplit('/',1)[-1];role=ROLES[b['type']['value'].rsplit('/',1)[-1]]
  e=entities.setdefault(q,{'name':b.get('entityLabel',{}).get('value',q),'roles':set(),'countries':set(),'websites':set(),'unresolvedCountries':set()});e['roles'].add(role)
  if 'country'in b:
   country=b['country']['value'].rsplit('/',1)[-1]
   if country in iso:e['countries'].add(iso[country])
   else:e['unresolvedCountries'].add(country)
  if 'website'in b and b['website']['value'].startswith('https://'):e['websites'].add(b['website']['value'])
 missing=[q for q,e in entities.items() if e['name']==q]
 for start in range(0,len(missing),50):
  url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbgetentities','ids':'|'.join(missing[start:start+50]),'props':'labels','format':'json'})
  req=urllib.request.Request(url,headers={'User-Agent':'OffMenu-local-food-collection/1.0'})
  labels=api(req)['entities']
  for q,d in labels.items():
   names={lang:item['value'] for lang,item in d.get('labels',{}).items()}
   if names:entities[q]['name']=names.get('mul') or names.get('en') or names[sorted(names)[0]]
   entities[q]['names']=names
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for q,e in sorted(entities.items()):
   if e['name']==q:counts['quarantined']+=1;unresolved.append({'id':q,'reason':'No usable source label in any language'});continue
   row={'schemaVersion':'1.0','kind':'organization','id':'wikidata-food-businesses:organization:'+q,'countries':sorted(e['countries']),'provenance':{'sourceId':'wikidata-food-businesses','recordId':q,'url':'https://www.wikidata.org/wiki/'+q,'license':'CC0 1.0','licenseUrl':'https://www.wikidata.org/wiki/Wikidata:Licensing','attribution':'Wikidata contributors','fetchedAt':now,'sourceDate':'2026-10-13','releaseId':'2026-10-13-direct-types','visibility':'public','transform':'offmenu-wikidata-business-reference/1'},'data':{'name':e['name'],'names':e.get('names',{}),'identifiers':[{'system':'Wikidata','value':q}],'roles':sorted(e['roles']),'websites':sorted(e['websites']),'countryBasis':'Wikidata P17 country assertion; not retail market or production-origin coverage','unresolvedCountryIds':sorted(e['unresolvedCountries']),'reviewStatus':'source-reference-unreviewed','ownershipVerified':False,'operationalCoverageVerified':False}}
   f.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n');counts['accepted']+=1;counts['records']+=1
 counts['duplicates']=len(bindings)-len(entities)
 assert counts['raw']==sum(counts[k] for k in ['accepted','duplicates','quarantined','excluded'])
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':'wikidata-food-businesses','releaseId':'2026-10-13-direct-types','status':'normalized','counts':counts,'normalizedRows':counts['records'],'archiveSha256':hashlib.sha256(raw).hexdigest(),'scope':'All results of the direct P31 food-manufacturer, supermarket-chain and grocery-store-chain query. Subclass query timed out; direct-type results are not all businesses or complete country registers.','license':'CC0 1.0','attribution':'Wikidata contributors','publication':'local only','completedAt':now};(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(output/'quarantine.json').write_text(json.dumps(unresolved,indent=2)+'\n');print(json.dumps(counts),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('output',type=Path);p.add_argument('--countrymap',type=Path);a=p.parse_args();collect(a.snapshot,a.output,a.countrymap)
