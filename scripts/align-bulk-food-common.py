#!/usr/bin/env python3
"""Stream source-faithful OFF, USDA FDC and Open Prices rows into common graph packets.

The program deliberately creates source-scoped resources only.  It does not
try to join barcodes, food names, retailers, countries, ingredients, nutrients
or dietary labels across publishers.  All normalized source fields remain in a
recursively typed ``sourceFields`` assertion so later mapping work can be
reviewed without returning to a lossy projection.
"""
import argparse, collections, gzip, hashlib, json, os, re, shutil, sys, time
from pathlib import Path

import jsonschema_rs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / 'offmenu-data'
CURATED = DATA / 'curated-expanded-country-search-20261013' / 'blobs'
SOURCES = {'off': None, 'usda-files': None, 'prices': None}
MAX_GZIP = 8 * 1024 * 1024

def digest(data): return hashlib.sha256(data).hexdigest()
def stable(*parts): return digest('\x1f'.join(map(str, parts)).encode())[:24]
def urn(kind, *parts): return f'urn:offmenu:bulk:{kind}:{stable(*parts)}'
def scope(): return {'visibility': 'public', 'reuseScope': 'Per-source licences and derivative requirements apply'}

def native_files(source):
    """Only accepted public curation blobs are input; raw archives are local evidence."""
    manifest=json.loads((CURATED/'manifest.json').read_text())
    entry=manifest['sources'][source]
    directory=CURATED/'records'/source
    files=sorted(directory.glob('*.jsonl.gz'))
    if not files: raise ValueError('missing accepted curated records for '+source)
    return files, entry, manifest

def typed(value, citation, path):
    """Preserve source values without guessing their natural language or ontology."""
    if value is None: return {'kind':'null','value':None}
    if isinstance(value, bool): return {'kind':'boolean','value':value}
    if isinstance(value, (int,float)) and not isinstance(value,bool): return {'kind':'number','value':value}
    # Curated payloads deliberately use source strings for names, labels, ingredient
    # declarations, locations and category labels.  Keep them localisable text,
    # not immutable identifiers. Structured codes retain their source key context.
    if isinstance(value, str):
        key=re.sub(r'\[\d+\]$','',path.rsplit('.',1)[-1])
        if value.startswith(('https://','http://','urn:')): return {'kind':'uri','value':value}
        if re.fullmatch(r'\d{4}-\d\d-\d\d',value): return {'kind':'date','value':value}
        if re.fullmatch(r'\d{4}-\d\d-\d\dT[^\s]+',value): return {'kind':'datetime','value':value}
        fixed={'system','value','unit','currency','nutritionId','sourceNutrientId','sourceMetricKey','definition','releaseId','sourceRow','proofId','availability','priceType','qualifier','method','state','preparationState','dataType','marketCountry','status','id','code','sourceId','recordId','schemaVersion','schema','policyVersion','sourceRecordReference','kind','visibility','archiveSha256','contentSha256','language','languageTag','countries'}
        if key in fixed or path.endswith(('.identifiers.system','.identifiers.value')): return {'kind':'identifier','value':value}
        return text(value, citation, path)
    if isinstance(value, list): return {'kind':'list','items':[typed(v,citation,path+f'[{i}]') for i,v in enumerate(value)]}
    if isinstance(value, dict): return {'kind':'structure','fields':{str(k):typed(v,citation,path+'.'+str(k)) for k,v in value.items()}}
    raise TypeError(type(value))

def unit_quantity(value, unit, *, currency=None, basis=None):
    raw_unit = unit if isinstance(unit,str) and unit else None
    normalized = (raw_unit or '').lower()
    units={'g':('urn:offmenu:unit:g','mass'),'kg':('urn:offmenu:unit:kg','mass'),'mg':('urn:offmenu:unit:mg','mass'),
           'mcg':('urn:offmenu:unit:ug','mass'),'µg':('urn:offmenu:unit:ug','mass'),'ml':('urn:offmenu:unit:ml','volume'),
           'l':('urn:offmenu:unit:l','volume'),'kcal':('urn:offmenu:unit:kcal','energy'),'kj':('urn:offmenu:unit:kj','energy'),
           'oz':('urn:offmenu:unit:oz','mass'),'lb':('urn:offmenu:unit:lb','mass')}
    uid, dimension = units.get(normalized, (None, 'currency' if currency else 'unknown'))
    result={'kind':'quantity','value':value if isinstance(value,(int,float)) else None,'unitId':uid,'dimension':dimension,
            'sourceValue':value,'sourceUnit':raw_unit,'qualifiers':[]}
    if currency: result['currencyCode']=currency
    if basis: result['basis']=basis
    return result

def source_citation(record, source, source_manifest, record_id):
    p=record.get('provenance',{})
    curation=record.get('curation',{}) if isinstance(record.get('curation'),dict) else {}
    upstream_id=p.get('recordId') or record_id
    return {'id':urn('citation',source,record_id), 'sourceId':source, 'originalRecordId':str(upstream_id),
            'originalUrl':p.get('url') or 'https://offmenu-corpus.netlify.app/',
            'revisionId':p.get('releaseId') or source_manifest.get('releaseId'), 'sourceDate':p.get('sourceDate'),
            'contentSha256':p.get('archiveSha256') or source_manifest.get('archiveSha256'),
            'license':p.get('license') or source_manifest.get('license') or 'Unknown source licence',
            'attribution':p.get('attribution') or source_manifest.get('attribution') or source,
            'rightsEvidenceUrl':p.get('url') or 'https://offmenu-corpus.netlify.app/',
            'sourcePath':curation.get('sourceRecordReference') or record.get('id',''), 'scope':scope()}

def text(value, citation, identifier):
    return {'kind':'text','id':urn('text',citation,identifier,value),'language':'und','value':value,
            'sourceTextSha256':digest(value.encode()),'status':'source-asserted','citationIds':[citation]}

def packet(record, source, source_manifest):
    data=record.get('data',{}); record_id=record.get('id') or record.get('provenance',{}).get('recordId')
    if record_id is None: raise ValueError('native row has no identity')
    citation=source_citation(record,source,source_manifest,record_id); cid=citation['id']; kind=record.get('kind','unknown')
    type_name={'product':'FoodProduct','nutrientProfile':'FoodCompositionObservation','priceObservation':'PriceObservation'}.get(kind,'UnmappedSourceFact')
    rid=urn('resource',source,record_id); name=data.get('name') or data.get('foodName')
    names=[text(name,cid,rid)] if isinstance(name,str) and name else []
    resource={'id':rid,'type':'urn:offmenu:type:'+type_name,'identityStatus':'source-scoped','names':names,'citationIds':[cid],'scope':scope()}
    assertions=[]; relations=[]
    def fact(property_name,value,path):
        assertions.append({'id':urn('assertion',rid,property_name,path),'subjectId':rid,'propertyId':'urn:offmenu:property:'+property_name,
                           'value':value,'status':'source-asserted','citationIds':[cid],'sourcePath':path,'scope':scope()})
    fact('originalSourceRecord',{'kind':'identifier','value':str(record_id)},'id')
    # The accepted curation envelope is public evidence too: retain country,
    # provenance, original source reference and curation policy/status without
    # reopening withheld raw fields or private contributors.
    context={k:v for k,v in record.items() if k!='data'}
    fact('curatedRecordContext',typed(context,cid,'context'),'')
    # Nutrient numeric values are emitted below as typed quantity observations.
    # Excluding their duplicate raw tree keeps the complete accepted package
    # within its disk budget while retaining source value, unit, basis and
    # definition in every observation.
    source_fields={k:v for k,v in data.items() if not (kind=='nutrientProfile' and k=='nutrients')}
    fact('sourceFields',typed(source_fields,cid,'data'),'data')
    for pos, identifier in enumerate(data.get('identifiers',[]) if isinstance(data.get('identifiers'),list) else []):
        # The namespace/value pair is preserved fixed; it is not an inferred
        # global identity and does not imply that matching barcodes are joined.
        fact('sourceIdentifier',{'kind':'structure','fields':{'system':{'kind':'identifier','value':str(identifier.get('system',''))},'value':{'kind':'identifier','value':str(identifier.get('value',''))}}},f'data.identifiers[{pos}]')
    if kind == 'priceObservation':
        fact('priceAmount',unit_quantity(data.get('amount'), data.get('unit'), currency=data.get('currency')),'data.amount')
        if data.get('observedAt') is not None: fact('observedAt',{'kind':'date','value':str(data['observedAt'])},'data.observedAt')
    if kind == 'nutrientProfile':
        for key,n in (data.get('nutrients') or {}).items():
            if not isinstance(n,dict): continue
            # Each source nutrient carries its own denominator/state.  A
            # profile-wide basis is only a presentation default and must not
            # overwrite the source observation basis.
            basis=n.get('basis') if isinstance(n.get('basis'),dict) else (data.get('basis') if isinstance(data.get('basis'),dict) else {})
            basisq=unit_quantity(basis.get('amount'),basis.get('unit'))
            q=unit_quantity(n.get('value'),n.get('unit'),basis=basisq)
            fact('nutrientObservation',q,'data.nutrients.'+str(key))
            # Preserve the exact source metric key, definition, qualifier,
            # method and every additional source-specific field with named
            # roles.  Do not mint an external nutrient URL from a local code.
            metadata={'sourceMetricKey':key, **{k:v for k,v in n.items() if k not in {'value','unit','basis'}}}
            fact('sourceNutrientMetadata',typed(metadata,cid,'data.nutrients.'+str(key)+'.metadata'),'data.nutrients.'+str(key)+'.metadata')
    # Native paired product/profile IDs are source-scoped references, never a cross-source join.
    other=data.get('nutritionId')
    if kind=='product' and isinstance(other,str):
        profile=urn('resource',source,other)
        relations.append({'id':urn('relation',rid,'hasCompositionObservation',profile),'subjectId':rid,'predicateId':'urn:offmenu:relation:hasCompositionObservation',
                          'objectId':profile,'status':'source-asserted','citationIds':[cid],'scope':scope(),'sourcePath':'data.nutritionId'})
    return {'schemaVersion':'offmenu-common/1','resources':[resource],'assertions':assertions,'relations':relations,'citations':[citation],'translations':[]}

class Writer:
    def __init__(self, output, validator):
        self.output=output; self.validator=validator; self.index=0; self.batch=[]; self.files=[]; self.counts=collections.Counter({'translations':0})
    def add(self,p):
        self.validator.validate(p)
        # IDs include source namespace + retained source record identity.  This
        # keeps full-stream memory bounded; root's global SQLite pass checks all
        # resource/assertion/relation/citation identities independently.
        self.batch.append(json.dumps(p,ensure_ascii=False,separators=(',',':')))
        self.counts['packets']+=1;self.counts['resources']+=len(p['resources']);self.counts['assertions']+=len(p['assertions']);self.counts['relations']+=len(p['relations'])
        if len(self.batch)>=1000:self.flush()
    def flush(self):
        if not self.batch:return
        raw=('\n'.join(self.batch)+'\n').encode(); compressed=gzip.compress(raw,compresslevel=1)
        if len(compressed)>MAX_GZIP:
            if len(self.batch)==1: raise ValueError('one packet exceeds gzip delivery bound')
            last=self.batch.pop(); self.counts['packets']-=1;self.flush(); self.batch=[last];self.counts['packets']+=1;return
        key='packets/part-'+str(self.index).zfill(5)+'.jsonl.gz'; path=self.output/key;path.parent.mkdir(exist_ok=True)
        path.write_bytes(compressed);self.files.append({'key':key,'bytes':len(compressed),'sha256':digest(compressed),'packets':len(self.batch)})
        self.index+=1;self.batch=[]

def align(sources, output, limit=0):
    if output.exists(): raise ValueError('immutable output already exists')
    output.mkdir(parents=True); schema=json.loads((ROOT/'corpus/common-data.schema.json').read_text());validator=jsonschema_rs.Draft202012Validator(schema,validate_formats=True);writer=Writer(output,validator);started=time.time();input_counts={};done=0
    input_coverage={}; observed_source={}
    for source in sources:
        files,source_manifest,curated_manifest=native_files(source); rows=0; expected=source_manifest['records']; observed_files=0
        accepted={x['key']:x for x in curated_manifest['files']}
        for path in files:
            relative=str(path.relative_to(CURATED))
            meta=accepted.get(relative)
            if meta is None: raise ValueError('curated manifest missing '+relative)
            raw=path.read_bytes()
            if len(raw)!=meta['bytes'] or digest(raw)!=meta['sha256']: raise ValueError('curated input digest mismatch '+relative)
            observed_files+=1
            with gzip.open(path,'rt',encoding='utf8') as handle:
                for line in handle:
                    native=json.loads(line)
                    rows_to_process=native[1] if isinstance(native,list) and len(native)==2 and isinstance(native[1],list) else [native]
                    for row in rows_to_process:
                        rows+=1; writer.add(packet(row,source,source_manifest));done+=1
                        if limit and done>=limit: break
                    if limit and done>=limit: break
            if limit and done>=limit: break
        observed_source[source]=rows
        input_coverage[source]={'expectedFiles':len(files),'observedFiles':observed_files,'expectedSourceRecords':expected,'observedSourceRecords':rows,'complete':not bool(limit)}
        if not limit and rows != expected: raise ValueError(f'{source} curated reconciliation {rows} != {expected}')
        if limit and done>=limit: break
    writer.flush()
    for source_name, output_name in [('common-data.schema.json','schema.json'),('common-data-contract.json','contract.json'),('common-source-mappings.json','source-mappings.json')]:
        b=(ROOT/'corpus'/source_name).read_bytes();(output/output_name).write_bytes(b);writer.files.append({'key':output_name,'bytes':len(b),'sha256':digest(b)})
    complete=not bool(limit)
    manifest={'schemaVersion':'offmenu-common-bulk-food/1','releaseId':'bulk-food-common-20261014','status':'full-schema-identity-citation-public-scope-checked' if complete else 'benchmark-not-for-admission',
              'complete':complete,'sources':sources,'curatedInputDirectory':str(CURATED),'counts':dict(writer.counts),'expectedCounts':dict(writer.counts),'observedCounts':dict(writer.counts),'files':writer.files,
              'expectedSourceRecords':{s:int(native_files(s)[1]['records']) for s in sources},'observedSourceRecords':observed_source,'inputCoverage':input_coverage,
              'partitionCoverage':{'complete':complete,'expectedFiles':len([x for x in writer.files if x['key'].endswith('.gz')]),'observedFiles':len([x for x in writer.files if x['key'].endswith('.gz')]),'expectedPackets':writer.counts['packets'],'observedPackets':writer.counts['packets']},
              'scope':'Complete selected native source rows or explicit bounded benchmark. Source-scoped resources only; no cross-source identity, nutrient, ingredient, retailer, country, origin, or dietary eligibility inference. Original normalized fields are retained as typed sourceFields assertions.',
              'completedAtUnix':time.time(),'seconds':time.time()-started,'limit':None if complete else limit}
    manifest['manifestSha256']=digest(json.dumps(manifest,separators=(',',':')).encode());(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('output',type=Path);a.add_argument('--sources',nargs='+',choices=SOURCES,default=list(SOURCES));a.add_argument('--limit',type=int,default=0);args=a.parse_args()
    print(json.dumps(align(args.sources,args.output,args.limit),ensure_ascii=False))
