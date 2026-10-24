#!/usr/bin/env python3
"""Fixed accepted retained USDA/OFF private read-only consumer; never a loader or SQL endpoint."""
import sys,json,hashlib,os
from pathlib import Path
ROOT=Path('/home/user/src/offmenu-worktrees/worker00-accepted-product-58f9a9c-20261025')
RECEIPT=Path('/home/user/src/offmenu-data/barcode-identifiers-worker57-full-retained-v1/load-receipt.json')
RECEIPT_SHA='186313b1aeac64b0b4c93cfa52fe567e5ba03baf89879f9d862bdf9306800edb'
DB_SHA='97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0'
HELPER_SHA='53d7aea20dde26f19e5176d2261d40a7d13e700396ac71036a96b61653995cb1'
FIELDS='assertion_id run_id input_id source_id release_id artifact_sha256 record_ordinal source_record_id native_record_id identity_state parse_job_id asset_id citation_id identifier_ordinal namespace lexical_value symbology source_pointer disposition reason_code input_manifest_sha256 load_state finalization_evidence_sha256 raw_sha256 raw_bytes'.split()
DETAIL_RECEIPT=Path('/home/user/Documents/Codex/2026-10-21/worker57-off-af-inspection-execution-v1/load-receipt.json')
DETAIL_SHA='10b70f8f1ee2240a5360d90b0ae182bba037641889771fe5d2fe06ff11f8be88'
DETAIL_IDENTITY=[64512,10238042,17677,1792560669708284508,1792560669708284508]
LABEL_SECTIONS=Path('/home/user/Documents/Codex/2026-10-21/worker26-product-detail-population/label-sections-v1/cached-source-label-sections.json')
LABEL_SECTIONS_SHA='26862c9773db1abc7408c84b6dcc905ca0bcd10bcb4e434ede01fbfb1322063e'
LABEL_SECTIONS_IDENTITY=[64512,10238459,14676,1792562869453096157,1792562869453096157]
def cached_label_sections(product):
 """Validate a cached annotation only. No extraction helper, parser or source scan."""
 fd=os.open(LABEL_SECTIONS,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  import stat
  before=os.fstat(fd);identity=lambda q:[q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_ctime_ns]
  assert stat.S_ISREG(before.st_mode) and identity(before)==LABEL_SECTIONS_IDENTITY and before.st_size<=262144
  b=os.read(fd,262145);assert len(b)==before.st_size and identity(os.fstat(fd))==LABEL_SECTIONS_IDENTITY
 finally:os.close(fd)
 assert hashlib.sha256(b).hexdigest()==LABEL_SECTIONS_SHA
 doc=json.loads(b)
 if doc['sourceObservation']!=product['sourceObservation'] or doc['sourceBinding']!=product['sourceBinding']:return {'state':'not-loaded'}
 raw=product['fields']['ingredientDeclaration']['value'];assert type(raw) is str and doc['rawText']==raw
 assert hashlib.sha256(raw.encode()).hexdigest()==doc['rawTextSHA256']
 cp=0;byte=0
 for section in doc['sections']:
  assert all(type(section[k]) is int for k in ('start','end','utf8Start','utf8End'))
  assert section['start']==cp and section['utf8Start']==byte and section['end']>=cp and section['utf8End']>=byte
  assert raw[cp:section['end']]==section['text'] and raw.encode()[byte:section['utf8End']].decode()==section['text']
  assert hashlib.sha256(section['text'].encode()).hexdigest()==section['textSHA256']
  cp=section['end'];byte=section['utf8End']
 assert cp==len(raw) and byte==len(raw.encode())
 assert doc['extractionVersion']=='offmenu-source-label-sections/1'
 return {'state':'cached-candidate','annotationSha256':LABEL_SECTIONS_SHA,'extractionVersion':doc['extractionVersion'],'rawTextSHA256':doc['rawTextSHA256'],'offsetUnit':doc['offsetUnit'],'sourceFieldPointer':doc['sourceArtifact']['fieldPointer'],'sourceArtifactSha256':doc['sourceArtifact']['sha256'],'independentOutputReviewSha256':doc['independentOutputReviewSha256'],'extractionSourceSha256':doc['extractionSource']['sha256'],'sections':doc['sections'],'assurance':doc['assurance'],'reviewStatus':'Cached candidate annotation; extraction helper not independently reviewed/integrated; no canonical mapping or certification'}
COMPONENT_TREE=Path('/home/user/Documents/Codex/2026-10-21/worker26-product-detail-population/label-components-v1/cached-source-ingredient-components.json')
COMPONENT_TREE_SHA='7dd0bcf752bb06128cd1994932c0524ca33cd2c07f955551beb825cc5c71b47a'
COMPONENT_TREE_IDENTITY=[64512,10238615,42308,1792564582205697122,1792564582205697122]
def cached_component_tree(product, label_sections):
 """Bind one immutable source-syntax annotation to the exact retained observation."""
 fd=os.open(COMPONENT_TREE,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  import stat
  before=os.fstat(fd);identity=lambda q:[q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_ctime_ns]
  assert stat.S_ISREG(before.st_mode) and identity(before)==COMPONENT_TREE_IDENTITY and before.st_size<=65536
  b=os.read(fd,65537);assert len(b)==before.st_size and identity(os.fstat(fd))==COMPONENT_TREE_IDENTITY
 finally:os.close(fd)
 assert hashlib.sha256(b).hexdigest()==COMPONENT_TREE_SHA
 doc=json.loads(b)
 if doc['sourceObservation']!=product['sourceObservation'] or doc['sourceBinding']!=product['sourceBinding']:return {'state':'not-loaded'}
 assert label_sections['state']=='cached-candidate' and doc['sectionArtifact']['sha256']==LABEL_SECTIONS_SHA
 assert doc['componentExtractionVersion']=='offmenu-source-ingredient-components/1'
 raw=product['fields']['ingredientDeclaration']['value'];assert type(raw) is str and raw==doc['rawText']
 assert hashlib.sha256(raw.encode()).hexdigest()==doc['rawTextSHA256']==label_sections['rawTextSHA256']
 ingredient=next(x for x in label_sections['sections'] if x['category']=='ingredient_list')
 assert doc['ingredientSpan']=={k:ingredient[k] for k in ('text','start','end','utf8Start','utf8End','textSHA256')}
 assert doc['sourceArtifact']['sha256']==label_sections['sourceArtifactSha256']
 seen=set();count=[0]
 def span(x,parent=None):
  assert all(type(x[k]) is int for k in ('start','end','utf8Start','utf8End'))
  start,end=x['start'],x['end'];bs,be=x['utf8Start'],x['utf8End']
  assert ingredient['start']<=start<end<=ingredient['end'] and raw[start:end]==x['text']
  assert raw.encode()[bs:be].decode()==x['text'] and hashlib.sha256(x['text'].encode()).hexdigest()==x['textSHA256']
  if parent is not None:assert parent['start']<=start<end<=parent['end']
 def visit(node,parent=None,depth=0):
  assert depth<=8 and node['parentComponentId']==(parent['componentId'] if parent else None)
  assert node['componentId'] not in seen and node['canonicalConceptId'] is None
  seen.add(node['componentId']);count[0]+=1;assert count[0]<=100
  span(node,parent)
  for item in node['nameSpans']+node['groups']+node['quantities']:span(item,node)
  for q in node['quantities']:assert q['basis'] is None and q['interpretedValue'] is None
  for child in node['children']:visit(child,node,depth+1)
 for root in doc['components']:visit(root)
 assert len(doc['components'])<=100 and count[0]==21
 assert sum(len(n['quantities']) for n in doc['components'])<=1
 return {'state':'cached-candidate','annotationSha256':COMPONENT_TREE_SHA,'extractionVersion':doc['componentExtractionVersion'],'rawTextSHA256':doc['rawTextSHA256'],'ingredientSpan':doc['ingredientSpan'],'components':doc['components'],'componentCount':count[0],'rootCount':len(doc['components']),'sourceGrammarMeaning':doc['sourceGrammarMeaning'],'reviewStatus':'Cached candidate syntax; extraction helper not independently reviewed/integrated; no canonical mapping, inferred quantity or certification'}
def selected_details(rows):
 """One qualified bounded output; full observation equality, never a barcode join."""
 fd=os.open(DETAIL_RECEIPT,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  import stat
  before=os.fstat(fd)
  identity=lambda q:[q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_ctime_ns]
  assert stat.S_ISREG(before.st_mode) and identity(before)==DETAIL_IDENTITY and before.st_size<=262144
  b=os.read(fd,262145);assert len(b)==before.st_size and identity(os.fstat(fd))==DETAIL_IDENTITY
 finally:os.close(fd)
 assert hashlib.sha256(b).hexdigest()==DETAIL_SHA
 doc=json.loads(b);assert doc['inspectionComplete'] is True
 products=doc['details']['sourceProducts'];assert type(products) is list
 selected=[]
 for product in products:
  key=product['observationKey'];obs=product['sourceObservation'];binding=product['sourceBinding']
  assert key['databaseSha256']==DB_SHA
  assert all(key[k]==obs[k] for k in ('run_id','input_id','record_ordinal','assertion_id'))
  assert binding['sourceId']==obs['source_id'] and binding['releaseId']==obs['release_id']
  assert binding['sourceOccurrence']==obs['record_ordinal'] and binding['occurrenceAssetSha256']==obs['artifact_sha256']
  assert binding['citationId']==obs['citation_id']
  for row in rows:
   if all(row.get(k)==v for k,v in obs.items()) and all(row.get(k)==key[k] for k in ('run_id','input_id','record_ordinal','assertion_id')):
    item={k:product[k] for k in ('observationKey','sourceBinding','sourceObservation','fields','canonicalIngredient','assurance')}
    try:item['labelSections']=cached_label_sections(product)
    except Exception:item['labelSections']={'state':'unavailable','reasonCode':'PINNED_LABEL_ANNOTATION_UNAVAILABLE'}
    try:item['ingredientComponents']=cached_component_tree(product,item['labelSections'])
    except Exception:item['ingredientComponents']={'state':'unavailable','reasonCode':'PINNED_COMPONENT_ANNOTATION_UNAVAILABLE'}
    selected.append(item)
 return {'state':'loaded' if selected else 'not-loaded','receiptSha256':DETAIL_SHA,'sourceProducts':selected,'accepted':False,'coverage':'selected output only; identifier-index coverage is separate','projectionLimitations':doc['details']['projectionLimitations']}
def output(x):
 wire=json.dumps(x,ensure_ascii=False,separators=(',',':'));assert len(wire.encode())<=262144;sys.stdout.write(wire)
def main():
 raw=sys.stdin.buffer.read(8193)
 if len(raw)>8192:raise ValueError('request-bound')
 request=json.loads(raw);assert type(request) is dict
 b=RECEIPT.read_bytes();assert hashlib.sha256(b).hexdigest()==RECEIPT_SHA
 receipt=json.loads(b);assert receipt['databaseSha256']==DB_SHA and receipt['loadComplete'] is True
 helper=ROOT/'offmenu/refresh/identifier_database.py';assert hashlib.sha256(helper.read_bytes()).hexdigest()==HELPER_SHA
 path=Path(receipt['database']);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd);assert [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns]==receipt['databaseIdentity']
 finally:os.close(fd)
 meta={'databaseLoaded':True,'queryAvailable':True,'databaseSha256':DB_SHA,'receiptSha256':RECEIPT_SHA,'runId':receipt['runId'],'schemaVersion':receipt['schemaVersion'],'loadComplete':True,'pointInTimeOnly':True,'scope':'complete listed retained USDA native + OFF occurrence inputs; not worldwide catalogue or canonical product acceptance','summary':receipt['summary'],'accepted':False,'assurance':'lexical-source-observations-only','limitMax':25,'queryMatchTotal':None}
 if request.get('action')=='status':output(meta);return
 if set(request)-{'action','namespace','lexical_value','after','limit','include','disposition'}:raise ValueError('request-shape')
 ns=request.get('namespace');lex=request.get('lexical_value');limit=request.get('limit',10);after=request.get('after',0);disposition=request.get('disposition','source-asserted')
 if disposition not in ('source-asserted','unresolved','invalid') or ns not in ('barcode','USDA-FDC') or type(lex) is not str or not 1<=len(lex)<=128 or type(limit) is not int or not 1<=limit<=25 or type(after) is not int or after<0:raise ValueError('query-input')
 sys.path.insert(0,str(ROOT))
 from offmenu.refresh.identifier_database import query_identifiers
 if Path(sys.modules[query_identifiers.__module__].__file__).resolve() != helper.resolve():raise ValueError('native-import-path')
 result=query_identifiers(receipt,namespace=ns,lexical_value=lex,disposition=disposition,after_assertion_id=after,limit=limit,max_steps=100000,max_seconds=5,max_result_bytes=262144)
 result['rows']=[{k:row.get(k) for k in FIELDS} for row in result['rows']]
 result.update({'metadata':meta,'queryMatchTotal':None})
 if request.get('include')==['source-native-product-details']:
  try:result['details']=selected_details(result['rows'])
  except Exception:result['details']={'state':'unavailable','reasonCode':'PINNED_DETAIL_RECEIPT_UNAVAILABLE','sourceProducts':[]}
  if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())>262144:result['details']={'state':'unavailable','reasonCode':'DETAIL_RESPONSE_BOUND','sourceProducts':[]}
 output(result)
try:main()
except (ValueError,TypeError,json.JSONDecodeError):output({'error':'INVALID_IDENTIFIER_QUERY','status':400})
except Exception:output({'error':'PINNED_PRIVATE_IDENTIFIER_QUERY_UNAVAILABLE','status':503})
