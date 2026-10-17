#!/usr/bin/env python3
"""Acquire every cookbook descendant in the publisher's interlanguage directory."""
import argparse,concurrent.futures,datetime,json,time,requests,hashlib
from pathlib import Path
UA={'User-Agent':'OffMenu-recipe-collector/1.0 (https://offmenu.aldous.info)'}
def collect(lang,title,root):
 out=root/lang;out.mkdir(parents=True,exist_ok=True);api='https://'+lang+'.wikibooks.org/w/api.php';session=requests.Session();session.headers.update(UA)
 def call(params):
  for attempt in range(4):
   time.sleep(1)
   try:
    query={'format':'json','formatversion':2,**params};response=session.get(api,params=query,timeout=45)
    if response.status_code==414:response=session.post(api,data=query,timeout=45)
    response.raise_for_status();value=response.json()
    if 'error'in value:raise ValueError(value['error'])
    return value
   except requests.HTTPError as e:
    if response.status_code not in [429,502,503,504] or attempt==3:raise
    time.sleep(min(30,max(3,int(response.headers.get('Retry-After','10')))))
 def cached(name,params):
  p=out/name
  if p.exists():return json.loads(p.read_text())
  value=call(params);p.write_text(json.dumps(value,ensure_ascii=False));return value
 try:
  info=cached('site-and-root.json',{'action':'query','titles':title,'prop':'info','redirects':1,'meta':'siteinfo','siprop':'namespaces|rightsinfo'});page=info['query']['pages'][0]
  if page.get('missing'):return {'language':lang,'status':'root-missing','title':title}
  ns=page['ns'];root_title=page['title'];namespace=info['query']['namespaces'].get(str(ns),{}).get('canonical','');dedicated=ns not in [0,4] and namespace not in ['Project','User','Help','Template']
  scope_ns=ns if dedicated else 0;prefix='' if dedicated else root_title.split('/')[0]+'/'
  # Russian recipe namespace is separate from its main-namespace index.
  if lang=='ru':scope_ns=104;prefix=''
  if ns==4:scope_ns=0;prefix=None
  members={page['pageid']:page};params={'action':'query','list':'allpages','apnamespace':scope_ns,'apprefix':prefix,'aplimit':500};batch=0
  while prefix is not None:
   data=cached('allpages-'+str(batch)+'.json',params)
   for member in data['query']['allpages']:members[member['pageid']]=member
   if not data.get('continue'):break
   params.update(data['continue']);batch+=1
  # Main-space recipes linked from the cookbook index cover books with flat titles.
  params={'action':'query','titles':root_title,'prop':'links','plnamespace':scope_ns,'pllimit':500};batch=0;linked_titles=set()
  while True:
   data=cached('root-links-'+str(batch)+'.json',params)
   for member in data['query']['pages'][0].get('links',[]):
    if member.get('title'):linked_titles.add(member['title'])
   if not data.get('continue'):break
   params.update(data['continue']);batch+=1
  linked_titles=sorted(linked_titles-set(m['title'] for m in members.values()))
  for start in range(0,len(linked_titles),50):
   data=cached('linked-page-info-'+str(start//50)+'.json',{'action':'query','titles':'|'.join(linked_titles[start:start+50]),'prop':'info'})
   for item in data['query']['pages']:
    if not item.get('missing'):members[item['pageid']]=item
  ids=sorted(members);(out/'members.json').write_text(json.dumps(list(members.values()),ensure_ascii=False))
  have=set()
  for original in list(out.glob('revisions-*.json'))+list(out.glob('linked-revisions-*.json')):
   data=json.loads(original.read_text())
   for item in data.get('query',{}).get('pages',[]):have.add(item['pageid'])
  remaining=[id for id in ids if id not in have]
  for start in range(0,len(remaining),50):
   params={'action':'query','pageids':'|'.join(map(str,remaining[start:start+50])),'prop':'revisions','rvprop':'ids|timestamp|content','rvslots':'main'}
   cached('linked-revisions-'+hashlib.sha256(params['pageids'].encode()).hexdigest()[:16]+'.json',params)
  result={'language':lang,'root':root_title,'namespace':scope_ns,'prefix':prefix,'pages':len(ids),'status':'complete','rights':info['query'].get('rightsinfo'),'scope':'All publisher cookbook-prefix pages or dedicated cookbook namespace, plus root; all API continuation exhausted. Ingredient/procedure classification occurs separately.'};(out/'acquisition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
 except Exception as e:
  result={'language':lang,'root':title,'status':'blocked','error':str(e)};(out/'acquisition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('language_links',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True);links=json.loads(a.language_links.read_text())['query']['pages'][0]['langlinks'];results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(collect,item['lang'],item['title'],a.directory):item for item in links}
  for future in concurrent.futures.as_completed(futures):result=future.result();results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
 (a.directory/'acquisition.json').write_text(json.dumps({'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'projects':results},ensure_ascii=False,indent=2))
