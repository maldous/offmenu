from pathlib import Path
import json, hashlib, gzip, base64
root=Path(__file__).resolve().parents[2]
def read(name):return json.loads((root/'docs/research'/name).read_text())
g=read('OffMenu_Global_Data_Source_Register.json');e=read('OffMenu_Enrichment_Source_Register_249.json');b=read('OffMenu_Country_Basket_Register.json');n=read('OffMenu_Basket_Normalization_Spec.json')
geo={x['code']:x for x in g['countries']};en={x['iso2']:x for x in e['countries']};ba={x['iso2']:x for x in b['countries']}
assert len(geo)==249 and set(geo)==set(en)==set(ba)
docs=[]
def add(kind,id,country,value):docs.append({'kind':kind,'id':id,'country':country,'value':value})
for code in sorted(geo):
 add('country',code,code,{'iso2':code,'name':geo[code]['name'],'region':geo[code]['region'],'discovery':geo[code],'enrichment':en[code],'basket':ba[code],'dataCompleteness':'research evidence; not complete live market data'})
 for track,key in [('editorial','demo_lines'),('published-example','normalized_published_examples')]:
  # Register calls published examples published_example_lines.
  lines=ba[code].get(key,ba[code].get('published_example_lines',[]) if track=='published-example' else [])
  for line in lines:add('basketLine',line.get('normalization',line)['line_id'],code,{'country':code,'track':track,**line})
for x in g['sources']:add('source','discovery:'+x['id'],'',{'id':'discovery:'+x['id'],'original':x,'accessState':'documented-lead','reuseApproved':False})
for x in e['source_catalog']:add('source',x['source_id'],'',{'id':x['source_id'],'original':x,'accessState':'documented-lead','reuseApproved':False})
for x in n['food_concepts']:add('foodConcept',x['concept_id'],'',x)
for x in n['metric_dictionary']:add('metric',x['metric_id'],'',x)
add('specification','basket-normalization','',n)
add('specification','enrichment-recommendations','',{'recommendations':e['report_recommendations'],'globalSources':e['global_sources']})
add('specification','global-providers','',{'providers':g['global_providers'],'legend':g['legend']})
counts={kind:sum(x['kind']==kind for x in docs) for kind in sorted({x['kind'] for x in docs})}
assert counts['basketLine']==3230,counts
manifest={'version':'2026-10-13.1','counts':counts,'countries':249,'sourceFiles':[{ 'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((root/'docs/research').glob('OffMenu*.json'))],'limits':b['important_limits'],'metrics':len(n['metric_dictionary'])}
(root/'docs/research'/'manifest.json').write_text(json.dumps(manifest,indent=2))
def quote(v):return "'"+str(v).replace("'","''")+"'"
out=root/'dist'/'catalogue.sql';out.parent.mkdir(exist_ok=True)
with out.open('w') as f:
 for x in docs:
  raw=json.dumps(x['value'],ensure_ascii=False,separators=(',',':'));doc='gz:'+base64.b64encode(gzip.compress(raw.encode(),mtime=0)).decode()
  search=(x['value'].get('name') or x['value'].get('canonical_label') or x['value'].get('label') or x['value'].get('original',{}).get('title') or ' '.join(x['value'].get('original',{}).get('names',[])) or x['id']).lower()
  search=' '.join(search.split())
  vals=[x['kind'],x['id'],x['country'],doc,search,manifest['version']]
  f.write('INSERT INTO catalogue(kind,id,country,document,search_text,version) VALUES('+','.join(map(quote,vals))+') ON CONFLICT(kind,id) DO UPDATE SET country=excluded.country,document=excluded.document,search_text=excluded.search_text,version=excluded.version;\n')
print(json.dumps(manifest))
