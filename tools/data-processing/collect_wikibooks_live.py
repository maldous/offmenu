#!/usr/bin/env python3
"""Collect every page in Wikibooks' current Recipes category, with full continuation."""
import argparse,gzip,hashlib,json,re,urllib.request,urllib.parse,urllib.error,datetime,time
from pathlib import Path
API='https://en.wikibooks.org/w/api.php'
def request(params):
 url=API+'?'+urllib.parse.urlencode({'format':'json','formatversion':2,**params});req=urllib.request.Request(url,headers={'User-Agent':'OffMenu-local-cookbook-collector/1.0'})
 for attempt in range(5):
  time.sleep(2)
  try:
   with urllib.request.urlopen(req,timeout=60) as r:d=json.load(r)
   break
  except urllib.error.HTTPError as e:
   if e.code not in [429,502,503,504] or attempt==4:raise
   delay=min(60,max(15,int(e.headers.get('Retry-After','30'))));print(json.dumps({'apiRetry':e.code,'waitSeconds':delay}),flush=True);time.sleep(delay)
 if 'error' in d:raise ValueError(d['error'])
 return d

def collect(output,release):
 output.mkdir(parents=True,exist_ok=True);rawdir=output/'originals';rawdir.mkdir(exist_ok=True);index=rawdir/'category-members.json'
 if index.exists():members=json.loads(index.read_text())
 else:
  members=[];params={'action':'query','list':'categorymembers','cmtitle':'Category:Recipes','cmnamespace':102,'cmtype':'page','cmlimit':500}
  while True:
   d=request(params);members.extend(d['query']['categorymembers'])
   if not d.get('continue'):break
   params.update(d['continue'])
  index.write_text(json.dumps(members,ensure_ascii=False))
 if len({x['pageid'] for x in members})!=len(members):raise ValueError('Duplicate recipe page identity')
 print(json.dumps({'scope':'All pages in Category:Recipes, namespace Cookbook','pages':len(members)}),flush=True)
 for start in range(0,len(members),50):
  path=rawdir/f'revisions-{start//50}.json'
  if not path.exists():
   ids='|'.join(str(m['pageid']) for m in members[start:start+50]);params={'action':'query','pageids':ids,'prop':'revisions|categories','rvprop':'ids|timestamp|content','rvslots':'main','cllimit':'max'};pages={}
   while True:
    d=request(params)
    for p in d['query']['pages']:
     key=p['pageid'];previous=pages.get(key,{});categories=previous.get('categories',[])+p.get('categories',[]);pages[key]={**previous,**p,'categories':categories}
    if not d.get('continue'):break
    params.update(d['continue'])
   if len(pages)!=len(members[start:start+50]):raise ValueError('Recipe revision count disagrees with category batch')
   path.write_text(json.dumps(list(pages.values()),ensure_ascii=False))
  if start%500==0:print(json.dumps({'revisionsCollected':min(start+50,len(members)),'total':len(members)}),flush=True)
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();counts={'raw':len(members),'accepted':0,'duplicates':0,'quarantined':0,'excluded':0,'records':0};quarantine=[];digest=hashlib.sha256();countries={}
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as out:
  for file in sorted(rawdir.glob('revisions-*.json')):
   body=file.read_bytes();digest.update(body)
   for p in json.loads(body):
    if p.get('missing') or not p.get('revisions'):quarantine.append({'pageid':p['pageid'],'reason':'Page missing after category enumeration'});counts['quarantined']+=1;continue
    rev=p['revisions'][0];text=rev['slots']['main']['content'];url='https://en.wikibooks.org/wiki/'+urllib.parse.quote(p['title'].replace(' ','_'),safe=':()/');ingredients=[];directions=[];section=''
    for line in text.splitlines():
     match=re.match(r'^==+\s*(.*?)\s*==+\s*$',line)
     if match:section=match[1].strip().lower();continue
     if section=='ingredients' and line.startswith(('*','#')):ingredients.append({'name':line.lstrip('*# ').strip(),'amount':None,'unit':None,'originalText':line,'foodMatchStatus':'unreviewed'})
     elif section in ['procedure','preparation','directions','method','instructions'] and line.strip():directions.append(line)
    row={'schemaVersion':'1.0','kind':'recipe','id':'wikibooks:recipe:'+hashlib.sha256(url.encode()).hexdigest()[:24],'countries':[], 'provenance':{'sourceId':'wikibooks','recordId':str(p['pageid']),'url':url,'license':'CC BY-SA 4.0','licenseUrl':'https://en.wikibooks.org/wiki/Wikibooks:Copyrights','attribution':'Wikibooks contributors; page history linked from source','visibility':'public','fetchedAt':now,'sourceDate':rev['timestamp'],'releaseId':release,'revisionId':rev['revid'],'historyUrl':url+'?action=history','transform':'offmenu-wikibooks-api/1','changes':'Recipe discovery metadata; ingredient quantities and food matches remain unresolved'},'data':{'name':p['title'].removeprefix('Cookbook:'),'yield':{'value':None,'unit':'portion'},'ingredients':ingredients,'directions':directions,'sourceCategories':[c['title'] for c in p.get('categories',[])],'originalTextLines':text.splitlines(),'reviewStatus':'unreviewed','automaticPlanningEligible':False,'limitations':'Source recipe requires quantity, food-identity, yield and cooking review; category country association is not inferred'}}
    out.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n');counts['accepted']+=1;counts['records']+=1
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':'wikibooks','releaseId':release,'status':'normalized','counts':counts,'normalizedRows':counts['records'],'archiveSha256':digest.hexdigest(),'license':'CC BY-SA 4.0','attribution':'Wikibooks contributors','scope':'All current pages in English Wikibooks Category:Recipes, Cookbook namespace, collected with complete API continuation. A dated retrieval, not a transactionally frozen dump.','publication':'local only','completedAt':now}
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(output/'quarantine.json').write_text(json.dumps(quarantine,indent=2)+'\n');print(json.dumps(counts),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--release',default='2026-10-13-live');a=p.parse_args();collect(a.output,a.release)
