#!/usr/bin/env python3
"""Restore missing typed fields from the SAME manifest-pinned native recipe.

This copies normalized input, not upstream knowledge. Never infers yield,
ingredient identity, nutritional totals, scaling safety or planning admission.
"""
import argparse
import copy
import gzip
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from inspect_north_star_sample import selected_file, sha
from north_star_derivations import canonical, digest, PROP, REL, TYPE, USABLE
from reconcile_recipe_fidelity import native_for_original

VERSION='recipe-normalized-field-restoration/1'


def derive(native, packet):
    indexes={}
    for name in ('resources','assertions','relations','citations'):
        indexes[name]={r['id']:r for r in packet[name]}
        if len(indexes[name])!=len(packet[name]):raise ValueError('duplicate graph identity')
    resources=indexes['resources'];facts=indexes['assertions'];citations=indexes['citations']
    original=[f for f in facts.values() if f['propertyId']==PROP+'originalSourceRecord'
              and resources.get(f['subjectId'],{}).get('type')==TYPE+'RecipeVariant']
    if len(original)!=1:raise ValueError('unique source recipe reference required')
    original=original[0];native_for_original({native['id']:native},original)
    rid=original['subjectId'];p=native['provenance'];d=native['data']
    out={'schemaVersion':'offmenu-recipe-context-derivations/1','rulesetVersion':VERSION,
         'inputNativeRecordCanonicalSha256':digest(native),'inputPacketCanonicalSha256':digest(packet),
         'status':'candidate-not-admitted','publicationEligible':False,'automaticPlanningEligible':False,
         'nutritionAggregationEligible':False,'identityEffect':'none',
         'confidence':{'status':'not-calibrated','probability':None},'assertions':[]}

    def evidence(inputs, subject):
        if any(i['status'] not in USABLE for i in inputs):raise ValueError('unusable input status')
        cids=sorted({c for i in inputs for c in i['citationIds']})
        if not cids or any(c not in citations for c in cids):raise ValueError('missing citation')
        scope=resources[subject]['scope']
        if scope.get('visibility')!='public':raise ValueError('only selected public native recipe inputs supported')
        involved=[resources[subject],resources[rid],*inputs,*[citations[c] for c in cids]]
        if any(i['scope']!=scope for i in involved):raise ValueError('mixed input scope')
        for cid in cids:
            c=citations[cid]
            expected={'sourceId':p['originSourceId'],'originalRecordId':p['recordId'],
                      'contentSha256':p.get('originalContentSha256',p.get('sourceDocumentSha256')),
                      'license':p['license'],'originalUrl':p['url']}
            if not expected['contentSha256'] or any(c.get(k)!=v for k,v in expected.items()):
                raise ValueError('native and graph citation identity differ')
            if 'sourceRevision' in p and c.get('revisionId')!=p['sourceRevision']:
                raise ValueError('native and graph revision differ')
        return cids,copy.deepcopy(scope)

    def restore(subject, prop, path, value, inputs):
        existing=[f for f in facts.values() if f['subjectId']==subject and f['propertyId']==PROP+prop]
        if len(existing)>1:raise ValueError('duplicate field context')
        if existing:return  # No replacement or reinterpretation of existing normalized assertions.
        cids,scope=evidence([original,*inputs],subject)
        inputs=[original,*inputs];input_ids=sorted({i['id'] for i in inputs})
        out['assertions'].append({'id':'urn:offmenu:derivation:'+digest([VERSION,digest(native),digest(packet),subject,path,value]),
            'subjectId':subject,'propertyId':PROP+prop,'sourcePath':path,'value':copy.deepcopy(value),
            'status':'candidate','evidenceKind':'copied-normalized-input-field','citationIds':cids,'scope':scope,
            'derivation':{'methodId':'urn:offmenu:method:'+VERSION,'reviewStatus':'candidate',
                'inputGraphIds':input_ids,'inputDigests':{i['id']:digest(i) for i in inputs},
                'inputNativeRecordCanonicalSha256':digest(native),'inputNativeFieldPath':path,
                'inputNativeFieldCanonicalSha256':digest(d['yield'] if path=='data.yield' else d['ingredients'][int(path.split('.')[2])]['scaling'])}})

    y=d['yield'];v=y['value']
    if y['unit']!='portion' or isinstance(v,bool) or (v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v) or v<0)):
        raise ValueError('unsupported native yield representation')
    restore(rid,'yield','data.yield',{'kind':'quantity','value':v,'unitId':'urn:offmenu:unit:portion','dimension':'count',
            'sourceValue':v,'sourceUnit':y['unit'],'qualifiers':['yield-unknown' if v is None else 'normalized-input-yield']},[])
    edges=[e for e in packet['relations'] if e['subjectId']==rid and e['predicateId']==REL+'usesIngredient']
    if len(edges)!=len(d['ingredients']) or len({e['objectId'] for e in edges})!=len(edges):raise ValueError('ingredient extent differs')
    for i,item in enumerate(d['ingredients']):
        path='data.ingredients.'+str(i);selected=[e for e in edges if e['sourcePath']==path]
        if len(selected)!=1 or resources.get(selected[0]['objectId'],{}).get('type')!=TYPE+'IngredientMention':
            raise ValueError('unique typed ingredient path required')
        if 'scaling' not in item:continue
        if item['scaling'] not in {'unknown','linear','to-taste','nonlinear','non-linear'}:raise ValueError('unsupported scaling code')
        restore(selected[0]['objectId'],'scalingRule',path+'.scaling',{'kind':'identifier','value':item['scaling']},selected)
    return out


def build(package, manifest_sha, native_key, graph_key, output):
    if output.exists():raise ValueError('immutable output exists')
    raw=(package/'manifest.json').read_bytes()
    if sha(raw)!=manifest_sha:raise ValueError('manifest pin differs')
    manifest=json.loads(raw);files={f['key']:f for f in manifest['files']}
    native=selected_file(package,files[native_key]);graph=selected_file(package,files[graph_key])
    rows={r['id']:r for r in map(json.loads,gzip.decompress(native).splitlines())}
    if len(rows)!=len(gzip.decompress(native).splitlines()):raise ValueError('duplicate native identity')
    seen=set();results=[];counts=Counter()
    for packet in map(json.loads,gzip.decompress(graph).splitlines()):
        recipes={r['id'] for r in packet['resources'] if r['type']==TYPE+'RecipeVariant'}
        original=[f for f in packet['assertions'] if f['propertyId']==PROP+'originalSourceRecord' and f['subjectId'] in recipes]
        if len(original)!=1:raise ValueError('unique source recipe reference required')
        row=native_for_original(rows,original[0])
        if row['id'] in seen:raise ValueError('duplicate graph recipe')
        seen.add(row['id']);result=derive(row,packet);results.append(result)
        counts['recipesExamined']+=1
        for f in result['assertions']:
            counts['restoredAssertions']+=1;counts[f['propertyId'].removeprefix(PROP)]+=1
            if f['propertyId']==PROP+'yield':counts['unknownYields' if f['value']['value'] is None else 'knownYields']+=1
    if seen!=set(rows):raise ValueError('native graph extent differs')
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=output.name+'.tmp-',dir=output.parent))
    body=gzip.compress(b''.join(canonical(r)+b'\n' for r in results),compresslevel=6,mtime=0)
    def durable_write(path, data):
        with path.open('xb') as handle:handle.write(data);handle.flush();os.fsync(handle.fileno())
    def sync_dir(path):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    key='recipe-context.jsonl.gz';durable_write(staging/key,body)
    report={'schemaVersion':'offmenu-recipe-context-release/1','rulesetVersion':VERSION,
        'releaseId':manifest['releaseId']+'-context-v1','complete':True,'status':'candidate-not-admitted',
        'files':[{'key':key,'bytes':len(body),'sha256':sha(body),'packets':len(results)}],
        'sourcePins':{'packagePath':str(package),'manifestByteSha256':manifest_sha,'releaseId':manifest['releaseId'],
                      'nativeAsset':files[native_key],'graphAsset':files[graph_key]},
        'sourceCodeSha256':sha(Path(__file__).read_bytes()),
        'helperSourceSha256':{Path(fn.__code__.co_filename).name:sha(Path(fn.__code__.co_filename).read_bytes())
                             for fn in (selected_file,canonical,native_for_original)},'counts':dict(counts),
        'assertedIdentityJoins':0,'servedApplicationQueries':0,'automaticPlanningEligible':False,
        'nutritionAggregationEligible':False,'publicationEligible':False,'originalsModified':False,
        'qualifications':['Exact copied native normalized field candidates, not new source facts.',
                          'Unknown yield remains unknown; scaling codes confer no calculation safety.',
                          'References require the exact base package and its original citations.']}
    durable_write(staging/'manifest.json',canonical(report)+b'\n');sync_dir(staging)
    # The caller holds the v3 exclusive output-root reservation. Never reuse or
    # remove an earlier staging directory or an existing final publication.
    if output.exists():raise ValueError('immutable output exists')
    os.rename(staging,output);sync_dir(output.parent)
    print(json.dumps({'releaseId':report['releaseId'],'counts':dict(counts),'manifestSha256':sha((output/'manifest.json').read_bytes())}))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('manifest_sha');p.add_argument('native_key');p.add_argument('graph_key');p.add_argument('output',type=Path);a=p.parse_args();build(a.package,a.manifest_sha,a.native_key,a.graph_key,a.output)
