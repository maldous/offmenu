#!/usr/bin/env python3
"""One local held-recipe catalogue: metadata index + read-only source references.
Never publishes, admits, or changes source data. No recipe body corpus is copied.
"""
import argparse, datetime, gzip, hashlib, json, os, pathlib, sqlite3, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
ROOT=pathlib.Path(__file__).resolve().parent
LOCAL=ROOT/'.local'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bundles(value):
 if isinstance(value,list):return [r for r in value if isinstance(r,dict)]
 if isinstance(value,dict):return [value]
 return []
def data_of(r):return r.get('data',r)
def identity(r,collection):
 p=r.get('provenance',{});origin=p.get('originSourceId') or p.get('sourceId') or collection['id']
 if origin=='wikibooks' and p.get('url'):
  host=urlparse(p['url']).hostname or ''
  if host.endswith('.wikibooks.org'):origin='wikibooks:'+host.split('.')[0]
 sourceid=str(p.get('recordId') or r.get('id') or '')
 if not sourceid:raise ValueError('Missing source identity; no title-based equivalence inferred')
 return origin,sourceid

def build(config):
 LOCAL.mkdir(exist_ok=True);dbpath=LOCAL/'index.sqlite'
 if dbpath.exists():raise RuntimeError('Index exists; preserve prior receipt and choose a new index filename for a changed inventory')
 db=sqlite3.connect(dbpath)
 db.executescript('''CREATE TABLE records(key TEXT PRIMARY KEY, title TEXT, origin TEXT, language TEXT, licence TEXT, review TEXT, ingredients INTEGER, directions INTEGER, priority INTEGER, collection TEXT, file TEXT, offset INTEGER, item INTEGER, private INTEGER, search TEXT);
 CREATE TABLE refs(key TEXT,collection TEXT,file TEXT,offset INTEGER,item INTEGER,source_id TEXT,record_id TEXT);
 CREATE INDEX records_title ON records(title); CREATE INDEX refs_key ON refs(key);''')
 inventories=[]
 for c in config['collections']:
  path=pathlib.Path(c['path']);before=path.stat();count=0
  def add(r,offset,item):
   nonlocal count
   if r.get('kind') not in [None,'recipe','recipeCandidate']:return
   d=data_of(r);p=r.get('provenance',{});origin,sourceid=identity(r,c);key=hashlib.sha256((origin+'\0'+sourceid).encode()).hexdigest();count+=1
   title=d.get('name') or d.get('title') or 'Untitled source record';title=title.get('value','Untitled') if isinstance(title,dict) else str(title)
   languages=d.get('languages') or ([d['language']] if d.get('language') else []);language=','.join(languages) if isinstance(languages,list) else str(languages)
   ingredients=d.get('ingredients') or [];directions=d.get('directions') or d.get('instructions') or [];licence=p.get('license') or d.get('license') or 'unknown';review=d.get('reviewStatus') or d.get('reviewState') or d.get('qualificationStatus') or 'unknown'
   private=int(p.get('visibility','public' if c['format']=='json-array' else 'unknown')!='public');search=' '.join([title,origin,language,licence,str(review)]).casefold()
   if private:title='Restricted or unclassified source record';search=(title+' '+origin).casefold()
   db.execute('INSERT INTO refs VALUES(?,?,?,?,?,?,?)',(key,c['id'],str(path),offset,item,origin,sourceid))
   old=db.execute('SELECT priority FROM records WHERE key=?',(key,)).fetchone()
   if old is None or c['priority']>old[0]:
    db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,title,origin,language,licence,str(review),len(ingredients),len(directions),c['priority'],c['id'],str(path),offset,item,private,search))
  if c['format']=='json-array':
   for item,r in enumerate(json.loads(path.read_text())):add(r,0,item)
  else:
   with gzip.open(path,'rb') as f:
    while True:
     offset=f.tell();line=f.readline()
     if not line:break
     for item,r in enumerate(bundles(json.loads(line))):add(r,offset,item)
  after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Source changed during index read'
  inventories.append({**c,'actualRecipeRecordsRead':count,'bytes':after.st_size,'sha256':sha(path),'gzipEOFValidated':c['format']=='jsonl-gzip'})
 db.commit();selected=db.execute('SELECT count(*) FROM records').fetchone()[0];refs=db.execute('SELECT count(*) FROM refs').fetchone()[0]
 facets={k:[{'value':r[0] or 'unknown','count':r[1]} for r in db.execute('SELECT '+col+',count(*) FROM records GROUP BY '+col+' ORDER BY count(*) DESC')] for k,col in [('sources','origin'),('languages','language'),('licences','licence'),('collections','collection')]}
 db.close()
 receipt={'schema':'offmenu-held-recipe-local-index/1','createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':config['scope'],'completeHeldInventory':False,'selectedSourceIdentities':selected,'sourceOccurrences':refs,'overlapOccurrences':refs-selected,'dedupPolicy':'Source origin + original source record ID; Wikibooks language scope from source URL; preferred configured snapshot priority, all occurrences retained; no title or dish equivalence claim','collections':inventories,'facets':facets,'index':{'path':str(dbpath),'bytes':dbpath.stat().st_size,'sha256':sha(dbpath)},'payloadClassification':'LOCAL/private preparation only; no new real-record publication permission','copies':'Thin metadata/pointers only. No directions/ingredient corpus copied.'}
 (LOCAL/'inventory.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'index':str(dbpath),'inventory':str(LOCAL/'inventory.json'),'selectedSourceIdentities':selected,'sourceOccurrences':refs,'completeHeldInventory':False}))
 return receipt

def serve(port):
 index=json.loads((LOCAL/'inventory.json').read_text());dbpath=LOCAL/'index.sqlite';runid=uuid.uuid4().hex
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def respond(self,value,status=200,ctype='application/json'):
   b=(json.dumps(value,ensure_ascii=False).encode() if ctype=='application/json' else value);self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
  def do_GET(self):
   if self.headers.get('Host')!='127.0.0.1:'+str(port):return self.respond({'error':'Host refused'},403)
   u=urlparse(self.path);q=parse_qs(u.query);db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
   try:
    if u.path=='/api/inventory':return self.respond({k:v for k,v in index.items() if k not in ['collections','index']}|{'runId':runid,'sourceEvidence':[{k:v for k,v in c.items() if k not in ['path']} for c in index['collections']]})
    if u.path=='/api/recipes':
     term=q.get('q',[''])[0][:200].casefold();page=max(0,min(10000,int(q.get('page',['0'])[0])));clauses=[];params=[]
     if term:clauses.append('instr(search,?)>0');params.append(term)
     for param,col in [('source','origin'),('language','language'),('licence','licence'),('collection','collection')]:
      val=q.get(param,[''])[0]
      if val:clauses.append(col+'=?');params.append('' if val=='unknown' else val)
     where=' WHERE '+' AND '.join(clauses) if clauses else '';total=db.execute('SELECT count(*) FROM records'+where,params).fetchone()[0]
     rows=[dict(r) for r in db.execute('SELECT key,title,origin,language,licence,review,ingredients,directions,collection,private FROM records'+where+' ORDER BY title COLLATE NOCASE,key LIMIT 48 OFFSET ?',params+[page*48])];return self.respond({'items':rows,'total':total,'page':page,'pageSize':48,'completeHeldInventory':False})
    if u.path=='/api/recipe':
     key=q.get('id',[''])[0];r=db.execute('SELECT * FROM records WHERE key=?',(key,)).fetchone()
     if r is None:return self.respond({'error':'Source identity not indexed'},404)
     if r['private']:return self.respond({'error':'Restricted/unclassified content withheld'},403)
     path=pathlib.Path(r['file'])
     if path.suffix=='.gz':
      with gzip.open(path,'rb') as f:f.seek(r['offset']);record=bundles(json.loads(f.readline()))[r['item']]
     else:record=json.loads(path.read_text())[r['item']]
     origin,sourceid=identity(record,{'id':r['collection']});actual=hashlib.sha256((origin+'\0'+sourceid).encode()).hexdigest()
     if actual!=key:return self.respond({'error':'Source reference changed; rebuild inventory'},409)
     versions=[dict(x) for x in db.execute('SELECT collection,source_id,record_id FROM refs WHERE key=?',(key,))];return self.respond({'record':record,'sourceIdentity':key,'occurrences':versions,'detailMode':'read-only reference to held source; no new qualification'})
    if u.path=='/shutdown':return self.respond({'error':'GET cannot stop catalogue'},405)
    allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
    if u.path in allowed:return self.respond((ROOT/allowed[u.path]).read_bytes(),ctype={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[allowed[u.path]])
    return self.respond({'error':'Unknown route'},404)
   except (ValueError,KeyError):return self.respond({'error':'Invalid query or source shape'},400)
   finally:db.close()
  def do_POST(self):
   if urlparse(self.path).path!='/shutdown' or self.headers.get('X-Catalogue-Run')!=runid:return self.respond({'error':'Run ownership required'},403)
   self.respond({'stopping':True});threading.Thread(target=server.shutdown,daemon=True).start()
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
 stat=pathlib.Path('/proc/self/stat').read_text();birth=stat[stat.rfind(')')+2:].split()[19];record={'schema':'offmenu-private-catalogue-run/1','runId':runid,'ownerThread':os.environ.get('CODEX_THREAD_ID'),'pid':os.getpid(),'bootId':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'birthTicks':birth,'cwd':str(pathlib.Path.cwd()),'port':port,'baseUrl':'http://127.0.0.1:'+str(port),'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'private catalogue preparation; not deployed','indexSha256':index['index']['sha256']}
 receipt=LOCAL/('run-'+runid+'.json');receipt.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
 try:server.serve_forever()
 finally:server.server_close();record['stoppedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();(LOCAL/('stopped-'+runid+'.json')).write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['index','serve']);p.add_argument('--port',type=int,default=19166);a=p.parse_args()
 if a.command=='index':build(json.loads((ROOT/'collections.json').read_text()))
 else:serve(a.port)
