#!/usr/bin/env python3
"""Independently check packaged data references, text digests and quantity dimensions."""
import argparse,gzip,hashlib,json
from pathlib import Path
import jsonschema_rs

def verify(directory):
 m=json.loads((directory/'manifest.json').read_text());schema=json.loads((directory/'schema.json').read_text());validator=jsonschema_rs.Draft202012Validator(schema,validate_formats=True);resources=set();assertions=set();relations=set();texts={};citations={};refs=set();translation_checks=[];derivations=[];packets=0;quantity_count=0
 def walk(v):
  nonlocal quantity_count
  if isinstance(v,list):
   for child in v:walk(child)
  elif isinstance(v,dict):
   if v.get('kind')=='text':
    digest=hashlib.sha256(v['value'].encode()).hexdigest();assert digest==v['sourceTextSha256'],'Text digest mismatch';value=(v['language'],v['value'],digest);assert v['id'] not in texts or texts[v['id']]==value,'Text ID collision';texts[v['id']]=value
   if v.get('kind')=='reference':refs.add(v['id'])
   if v.get('kind')=='quantity':
    quantity_count+=1;unit=v.get('unitId');dimension={'urn:offmenu:unit:g':'mass','urn:offmenu:unit:ml':'volume','urn:offmenu:unit:count':'count','urn:offmenu:unit:portion':'count'}.get(unit)
    if dimension:assert v['dimension']==dimension,'Quantity dimension mismatch'
   refs.update(v.get('culturalRepresentationIds',[]))
   for child in v.values():walk(child)
 for f in m['files']:
  b=(directory/f['key']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
  if not f['key'].split('/')[0] in ['concepts','recipes','terminology','ontology']:continue
  for line in gzip.decompress(b).decode().split('\n'):
   if not line:continue
   p=json.loads(line);validator.validate(p);packets+=1;walk(p)
   for r in p['resources']:assert r['id'] not in resources;resources.add(r['id'])
   for a in p['assertions']:
    assert a['id'] not in assertions;assertions.add(a['id']);refs.add(a['subjectId']);derivations.extend(a.get('derivation',{}).get('inputAssertionIds',[]))
   for r in p['relations']:assert r['id'] not in relations;relations.add(r['id']);refs.update([r['subjectId'],r['objectId']])
   for c in p['citations']:
    assert c['id'] not in citations or citations[c['id']]==c,'Citation identity collision';citations[c['id']]=c
   for t in p['translations']:translation_checks.append((t['textId'],t['sourceTextSha256']));refs.update(t['terminologyResourceIds'])
 for id,digest in translation_checks:assert id in texts and texts[id][2]==digest,'Translation source mismatch'
 assert set(derivations)<=assertions,'Unresolved derivation'
 missing=refs-resources;assert all(id.startswith(('urn:offmenu:unit:','urn:offmenu:country:','http://','https://')) for id in missing),'Unresolved internal reference'
 result={'status':'independent-data-verification-passed','packets':packets,'resources':len(resources),'assertions':len(assertions),'relations':len(relations),'localizedSourceTexts':len(texts),'citations':len(citations),'translationsChecked':len(translation_checks),'quantitiesChecked':quantity_count,'externalReferences':len(missing),'allFileDigestsChecked':len(m['files'])};assert packets==m['counts']['packets'];print(json.dumps(result));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();verify(a.package)
