#!/usr/bin/env python3
"""Align pinned FoodOn definitions as source data; no application/ontology reasoning."""
import argparse,collections,gzip,hashlib,json,math,xml.etree.ElementTree as ET
import jsonschema_rs
from pathlib import Path
RDF='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}';XML='{http://www.w3.org/XML/1998/namespace}'
def sha(value):return hashlib.sha256(value.encode()).hexdigest()
def iri(tag):return tag[1:].replace('}', '') if tag.startswith('{') else tag

def collect(source,output):
 if output.exists():raise ValueError('Immutable output exists')
 output.mkdir();receipt=json.loads((source/'acquisition.json').read_text());document=next(f for f in receipt['files'] if f['key']=='foodon.owl');root=ET.parse(source/'foodon.owl').getroot();scope={'visibility':'public','reuseScope':'FoodOn own-namespace definitions CC-BY-4.0; imported concepts remain cited references'};counts=collections.Counter();languages=collections.Counter();schema_types=set();property_types=collections.Counter()
 iri_check=jsonschema_rs.Draft202012Validator({'type':'string','format':'iri'},validate_formats=True)
 metadata=[]
 for node in root:
  if node.tag.endswith('Ontology'):metadata=[{'predicate':iri(c.tag),'attributes':c.attrib,'value':c.text} for c in node]
 with gzip.open(output/'foodon-common.jsonl.gz','wt',encoding='utf8') as target:
  for node in root:
   id=node.get(RDF+'about','')
   if not node.tag.endswith('Class') or '/FOODON_' not in id:continue
   cid='urn:offmenu:citation:foodon:'+sha(id)[:24];citation={'id':cid,'sourceId':'foodon','originalRecordId':id,'originalUrl':document['url'],'revisionId':receipt['revision'],'contentSha256':document['sha256'],'license':'CC-BY-4.0','attribution':'FoodOn contributors; original class annotations and references retained','rightsEvidenceUrl':receipt['root']+'LICENSE.txt','sourcePath':id,'scope':scope};names=[];assertions=[];relations=[]
   for index,child in enumerate(node):
    predicate=iri(child.tag);path=id+'/'+predicate+'/'+str(index);rawtag=child.get(XML+'lang','und');lang=rawtag if rawtag not in ['jp','ge','cz','zh-tans','zh-tant','en-scotland','ykp'] else 'und';object_uri=child.get(RDF+'resource');lexical=child.text or '';aid='urn:offmenu:assertion:foodon:'+sha(path)[:24]
    malformed=bool(object_uri and not iri_check.is_valid(object_uri))
    if malformed:
     lexical=object_uri;object_uri=None;counts['malformedSourceResourceAttributes']+=1
    text={'kind':'text','id':'urn:offmenu:text:foodon:'+sha(path)[:24],'language':lang,'value':lexical,'sourceTextSha256':sha(lexical),'status':'source-asserted','citationIds':[cid]}
    if len(child):value={'kind':'expression','syntax':'rdf/xml','value':ET.tostring(child,encoding='unicode')};property_types['formal-rdf-expression']+=1
    elif object_uri:value={'kind':'uri','value':object_uri}
    else:
     datatype=child.get(RDF+'datatype','')
     try:
      if datatype.endswith(('boolean',)):value={'kind':'boolean','value':lexical.strip() in ['true','1']}
      elif datatype.endswith(('integer','int','long')):value={'kind':'number','value':int(lexical)}
      elif datatype.endswith(('dateTime',)):value={'kind':'datetime','value':lexical}
      elif datatype.endswith(('date',)):value={'kind':'date','value':lexical}
      elif datatype.endswith(('anyURI',)):
       if iri_check.is_valid(lexical):value={'kind':'uri','value':lexical}
       else:
        value=text;malformed=True;counts['malformedSourceUriLiterals']+=1
      elif child.tag.endswith('hasDbXref'):value={'kind':'identifier','value':lexical}
      elif datatype.endswith(('float','double','decimal')):
       number=float(lexical)
       if not math.isfinite(number):raise ValueError('Non-finite source literal')
       value={'kind':'number','value':number}
      else:value=text
     except (ValueError,OverflowError):value={'kind':'identifier','value':lexical}
    assertions.append({'id':aid,'subjectId':id,'propertyId':predicate,'value':value,'status':'candidate' if malformed else 'source-asserted','citationIds':[cid],'sourcePath':path,'scope':scope})
    if child.tag.endswith('label') and not object_uri:names.append(text);languages[rawtag]+=1
    if object_uri and child.tag.endswith('subClassOf'):relations.append({'id':'urn:offmenu:relation:foodon:'+sha(path+object_uri)[:24],'subjectId':id,'predicateId':predicate,'objectId':object_uri,'status':'source-asserted','citationIds':[cid],'sourcePath':path,'scope':scope})
    # Original RDF attributes and lexical forms survive even when a parsed value is available.
    original={'kind':'structure','fields':{'attributes':{'kind':'structure','fields':{k:{'kind':'identifier','value':v} for k,v in child.attrib.items()}},'lexicalValue':{'kind':'identifier','value':lexical}}}
    assertions.append({'id':aid+':source-notation','subjectId':id,'propertyId':'urn:offmenu:property:originalRdfNotation','value':original,'status':'source-asserted','citationIds':[cid],'sourcePath':path,'scope':scope})
   packet={'schemaVersion':'offmenu-common/1','resources':[{'id':id,'type':'urn:offmenu:type:OntologyClass','identityStatus':'identified','names':names,'citationIds':[cid],'scope':scope}],'assertions':assertions,'relations':relations,'citations':[citation],'translations':[]};target.write(json.dumps(packet,ensure_ascii=False,separators=(',',':'))+'\n');counts['classes']+=1;counts['assertions']+=len(assertions);counts['relations']+=len(relations)
 manifest={'schemaVersion':'offmenu-common-ontology/1','sourceId':'foodon','revision':receipt['revision'],'originalDocument':document,'licence':'CC-BY-4.0','counts':counts,'sourceLanguageTags':languages,'additionalValueTypes':property_types,'ontologyMetadata':metadata,'scope':'All named FOODON namespace classes in the complete pinned release. Every direct child assertion, original RDF attributes/lexical form and complex expression retained. Imported ontology identities remain references; no FoodOn-to-ingredient equivalence, nutrition, diet or stock qualification inferred.','files':[]}
 for f in output.iterdir():manifest['files'].append({'key':f.name,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'classes':counts['classes'],'assertions':counts['assertions'],'relations':counts['relations'],'formalExpressions':property_types['formal-rdf-expression']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.source,a.output)
