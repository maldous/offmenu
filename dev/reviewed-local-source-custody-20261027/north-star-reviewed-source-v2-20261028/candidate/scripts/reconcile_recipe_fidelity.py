#!/usr/bin/env python3
"""Compare manifest-listed pre-alignment normalized recipes to common packets.

No source prose is emitted. Unknown measurements remain unknown. This establishes
whether the common alignment lost a value already available in its own input;
it does not certify an earlier extractor or authorize additional source access.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path
from inspect_north_star_sample import selected_file, sha


def metadata_code(value, allowed):
    if value is None:return 'unknown'
    if isinstance(value,str) and value in allowed:return value
    return 'unrecognized-sha256:'+sha(json.dumps(value,sort_keys=True).encode())


def same_value(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return type(a) is type(b) and a==b
    return a==b


def native_for_original(rows, original):
    """Resolve only the producer-declared source field, not lexical identity."""
    path=original['sourcePath']; value=original['value']['value']
    if path=='id':matches=[r for r in rows.values() if r['id']==value]
    elif path=='provenance.recordId':matches=[r for r in rows.values() if r.get('provenance',{}).get('recordId')==value]
    else:raise ValueError('unsupported original recipe reference path')
    if len(matches)!=1:raise ValueError('unique exact native reference required')
    return matches[0]


def reconcile(package, manifest_sha, native_key, graph_key, output):
    b=(package/'manifest.json').read_bytes()
    if sha(b)!=manifest_sha: raise ValueError('manifest pin differs')
    m=json.loads(b);files={f['key']:f for f in m['files']}
    native=selected_file(package,files[native_key]);graph=selected_file(package,files[graph_key])
    rows={r['id']:r for r in map(json.loads,gzip.decompress(native).splitlines())}
    if len(rows)!=len(gzip.decompress(native).splitlines()):raise ValueError('duplicate native identity')
    count=collections.Counter();statuses=collections.Counter();source_units=collections.Counter();mismatches=[];seen=set()
    prop='urn:offmenu:property:'
    for p in map(json.loads,gzip.decompress(graph).splitlines()):
        for collection in ('resources','assertions','relations','citations'):
            ids=[r['id'] for r in p[collection]]
            if len(ids)!=len(set(ids)):raise ValueError('duplicate graph '+collection+' identity')
        fs=p['assertions'];resources={r['id']:r for r in p['resources']}
        recipes={r['id'] for r in p['resources'] if r['type']=='urn:offmenu:type:RecipeVariant'}
        original=[f for f in fs if f['propertyId']==prop+'originalSourceRecord' and f['subjectId'] in recipes]
        if len(original)!=1:raise ValueError('unique original recipe reference required')
        r=native_for_original(rows,original[0]);rid=r['id'];recipe_id=original[0]['subjectId']
        if rid in seen:raise ValueError('duplicate graph original recipe identity')
        d=r['data'];seen.add(rid);count['recipesCompared']+=1
        y=[f for f in fs if f['propertyId']==prop+'yield' and f['subjectId']==recipe_id]
        if len(y)>1:raise ValueError('unique recipe yield required')
        expected_yield={'value':d['yield']['value'],'unitId':'urn:offmenu:unit:portion','dimension':'count',
                        'sourceValue':d['yield']['value'],'sourceUnit':d['yield']['unit']}
        if not y:
            count['graphMissingYieldAssertions']+=1
            mismatches.append({'recordSha256':sha(rid.encode()),'field':'yield','difference':'missing-assertion'})
        else:
            for key,value in expected_yield.items():
                if key not in y[0]['value'] or not same_value(y[0]['value'][key],value):mismatches.append({'recordSha256':sha(rid.encode()),'field':'yield.'+key})
        ingredient_edges=[e for e in p['relations'] if e['subjectId']==recipe_id and e['predicateId']=='urn:offmenu:relation:usesIngredient']
        if len(ingredient_edges)!=len(d['ingredients']):raise ValueError('native/graph ingredient extent differs')
        mention_ids={e['objectId'] for e in ingredient_edges}
        if len(mention_ids)!=len(ingredient_edges) or any(resources.get(i,{}).get('type')!='urn:offmenu:type:IngredientMention' for i in mention_ids):
            raise ValueError('unique typed ingredient mentions required')
        quantities=[a for a in fs if a['propertyId']==prop+'requiredQuantity']
        if len(quantities)!=len(d['ingredients']) or any(a['subjectId'] not in mention_ids for a in quantities):
            raise ValueError('graph quantity extent/subject differs')
        count['nativeUnknownYields' if d['yield']['value'] is None else 'nativeKnownYields']+=1
        count['nativeAutomaticPlanningFalse' if d.get('automaticPlanningEligible') is False else 'nativeAutomaticPlanningOther']+=1
        for i,ingredient in enumerate(d['ingredients']):
            base_path='data.ingredients.'+str(i);path=base_path+'.sourceQuantity'
            edge=[e for e in ingredient_edges if e['sourcePath']==base_path]
            if len(edge)!=1:raise ValueError('unique recipe ingredient path required')
            q=[f for f in quantities if f['subjectId']==edge[0]['objectId'] and f['sourcePath']==path]
            count['ingredientsCompared']+=1
            if len(q)!=1:raise ValueError('unique original ingredient quantity required')
            q=q[0]['value'];sq=ingredient['sourceQuantity'];count['nativeCanonicalUnknownAmounts' if ingredient['amount'] is None else 'nativeCanonicalKnownAmounts']+=1
            count['nativeSourceUnknownAmounts' if sq.get('value') is None else 'nativeSourceKnownAmounts']+=1
            if ingredient['amount'] is None and sq.get('value') is not None:count['sourceAmountPresentButCanonicalUnresolved']+=1
            status_codes={'unknown','known','missing','unresolved','parsed','normalized','source-reported','source-asserted','candidate','reviewed','verified','unmeasured','not-supplied','source-measure','unsupported-unit','needs-review'}
            statuses[metadata_code(ingredient.get('quantityStatus'),status_codes)+' / '+metadata_code(sq.get('status'),status_codes)]+=1
            source_units[metadata_code(sq.get('unit'),{'g','kg','mg','ml','l','count','portion','cup','tsp','tbsp'})]+=1
            expected={'value':ingredient['amount'],'unitId':'urn:offmenu:unit:'+ingredient['unit'] if ingredient['unit'] else None,
                      'sourceValue':sq.get('value'),'sourceUnit':sq.get('unit')}
            for key,value in expected.items():
                if key not in q or not same_value(q[key],value):mismatches.append({'recordSha256':sha(rid.encode()),'ingredientOrdinal':i,'field':key})
            if not same_value(q.get('range'),sq.get('range')):mismatches.append({'recordSha256':sha(rid.encode()),'ingredientOrdinal':i,'field':'range'})
            if 'scaling' in ingredient:
                scaling=[f for f in fs if f['subjectId']==edge[0]['objectId'] and f['propertyId']==prop+'scalingRule']
                if len(scaling)>1:raise ValueError('unique scaling assertion required')
                if not scaling:
                    count['graphMissingScalingAssertions']+=1
                    mismatches.append({'recordSha256':sha(rid.encode()),'ingredientOrdinal':i,'field':'scaling','difference':'missing-assertion'})
                elif scaling[0]['sourcePath']!=base_path+'.scaling' or not same_value(scaling[0]['value'].get('value'),ingredient['scaling']):
                    mismatches.append({'recordSha256':sha(rid.encode()),'ingredientOrdinal':i,'field':'scaling'})
    if seen!=set(rows):raise ValueError('native/graph extent differs')
    result={'schemaVersion':'offmenu-recipe-alignment-fidelity/1','status':'exact-normalized-input-fields-preserved' if not mismatches else 'alignment-field-differences',
            'manifestByteSha256':manifest_sha,'releaseId':m['releaseId'],'nativeAsset':files[native_key],'graphAsset':files[graph_key],
            'counts':dict(count),'quantityStatuses':dict(statuses),'sourceUnitCounts':dict(source_units),'mismatches':mismatches,
            'sourceCodeSha256':sha(Path(__file__).read_bytes()),'originalSourceExtractionVerified':False,'originalsModified':False,
            'conclusion':'A null already present in pre-alignment normalized input cannot be repaired by the common aligner. Original extraction fidelity requires the exact earlier source material/decision; source numeric values with unsupported units remain distinguishable from genuinely absent source magnitudes.'}
    if output.exists():raise ValueError('immutable fidelity output exists')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'counts':result['counts'],'mismatchCount':len(mismatches)}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('manifest_sha');p.add_argument('native_key');p.add_argument('graph_key');p.add_argument('output',type=Path);a=p.parse_args();reconcile(a.package,a.manifest_sha,a.native_key,a.graph_key,a.output)
