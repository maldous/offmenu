"""Pure bounded nutrient/reference candidates in the existing offmenu-common/1.

Caller supplies already permitted source rows and exact partition provenance.
No dataset discovery, source reads, SQLite, models or source permission occurs.
Scientific source records stay distinct; names never establish nutrient identity.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import quote

VERSION = 'offmenu.nutrient-reference-generation/2'
COMMON = 'offmenu-common/1'
PREFIX = 'urn:offmenu:candidate:generation2:worker64:'
CONTRACT_SHA = 'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa'
MAX_ROWS, MAX_INPUT, MAX_ROW, MAX_OUTPUT = 10000, 16*1024**2, 65536, 64*1024**2
EXCLUDED_ASSETS = frozenset(('d297aa8d3e7453d707d909b1eaab23337b559a80bf71dd11f348c6707e3220ca',
    'f7e0b953c0f3c6609f8d72597de576d050df90ec16a65e99df84c4b936707e8b',
    'c2dbca1d379ce93fa4423993ed0d1ace7669447c7899be025b7af3a8855bb609'))
KINDS = frozenset(('NutrientDefinition','Unit','Quantity','MeasurementMethod','FoodCompositionObservation'))
DIMENSIONS = frozenset(('mass','volume','count','energy','time','length','temperature','currency','ratio','concentration','unknown'))


def canonical(value):
    try:
        return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (TypeError,ValueError,UnicodeError,RecursionError):
        raise ValueError('nutrient-generation-json') from None


def digest(value): return sha256(canonical(value)).hexdigest()
def _id(kind,value): return PREFIX+kind+':'+digest(value)
def _sha(value): return type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None
def _string(value): return type(value) is str and bool(value) and len(value)<=4096
def _pointer(value): return str(value).replace('~','~0').replace('/','~1')


def _plain(value,depth=0,count=None):
    count=[0] if count is None else count;count[0]+=1
    if depth>12 or count[0]>100000: raise ValueError('nutrient-generation-structure')
    if value is None or type(value) in (str,bool,int): return
    if type(value) is float and math.isfinite(value): return
    if type(value) is list:
        for item in value:_plain(item,depth+1,count)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():_plain(item,depth+1,count)
        return
    raise ValueError('nutrient-generation-structure')


def _point(value):
    """Preserve lexical source separately; nonpoints/large or lossy numbers stay null."""
    if type(value) in (int,float):
        if abs(value)>9007199254740991 or not math.isfinite(value):return None
        return value
    if type(value) is not str or len(value)>128 or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',value):return None
    try:
        d=Decimal(value)
        if not d.is_finite() or abs(d)>9007199254740991:return None
        if d==d.to_integral_value():return int(d)
        f=float(d)
        return f if math.isfinite(f) and Decimal(str(f))==d else None
    except (InvalidOperation,OverflowError,ValueError):return None


def build_generation(rows, contract_raw, *, partitions, generation_version,
                     actor_reference, protected_ids, external_reference_ids=()):
    """Transform supplied rows, never read sources; provenance pins are not grants.

    Rows are explicit adapter records, not inferred from filenames/English labels.
    Source-specific adapters must preserve all original columns in sourceFields.
    Whole-source eligibility, source read budgets and privacy are caller-owned.
    """
    if type(contract_raw) is not bytes or len(contract_raw)>131072 or sha256(contract_raw).hexdigest()!=CONTRACT_SHA:
        raise ValueError('nutrient-generation-contract')
    contract=json.loads(contract_raw)
    if not _string(generation_version) or not _string(actor_reference):raise ValueError('nutrient-generation-actor-version')
    if type(rows) is not list or len(rows)>MAX_ROWS or type(partitions) is not dict or not partitions:
        raise ValueError('nutrient-generation-input-bound')
    _plain(rows);_plain(partitions)
    if len(canonical(rows))+len(canonical(partitions))>MAX_INPUT:raise ValueError('nutrient-generation-input-bound')
    protected=set(protected_ids);food_externals=set(external_reference_ids);externals=set(food_externals)
    units={v['id']:v for v in contract['units'].values()};externals.update(units)
    for key,p in partitions.items():
        if (not _string(key) or type(p) is not dict or
            not all(_string(p.get(k)) for k in ('sourceId','releaseId','originalUrl','license','attribution')) or
            not _sha(p.get('assetSha256')) or not _sha(p.get('operationReceiptSha256'))):
            raise ValueError('nutrient-generation-partition')
        if p['assetSha256'] in EXCLUDED_ASSETS:raise ValueError('nutrient-generation-protected-source')
    scope={'visibility':'private','ownerId':actor_reference,'reuseScope':'source-scoped-generation2-author-candidate; no registry/Gold admission'}
    packet={'schemaVersion':COMMON,'resources':[],'assertions':[],'relations':[],'citations':[],'translations':[]}
    conflicts=[];seen={};emitted=set();source_index={};input_bytes=0

    def add(collection,obj):
        if obj['id'] in protected or obj['id'] in emitted:raise ValueError('nutrient-generation-protected-or-duplicate-id')
        emitted.add(obj['id']);packet[collection].append(obj)

    def text(value,cid,key,language='und'):
        return {'kind':'text','id':_id('text',[key,value,language,cid]),'language':language,'value':value,
                'sourceTextSha256':sha256(value.encode('utf-8')).hexdigest(),'status':'source-asserted','citationIds':[cid]}

    def typed(value,cid,key,language):
        if value is None:return {'kind':'null','value':None}
        if type(value) is bool:return {'kind':'boolean','value':value}
        if type(value) in (int,float):return {'kind':'number','value':value}
        if type(value) is str:return text(value,cid,key,language)
        if type(value) is list:return {'kind':'list','items':[typed(v,cid,[key,i],language) for i,v in enumerate(value)]}
        return {'kind':'structure','fields':{k:typed(v,cid,[key,k],language) for k,v in value.items()}}

    def assertion(rid,cid,source_path,name,value,status='candidate'):
        add('assertions',{'id':_id('assertion',[rid,name,value,status,cid]),'subjectId':rid,
            'propertyId':contract['sourcePropertyExtensions']['namespace']+quote(name,safe=''),
            'value':value,'status':status,'citationIds':[cid],'sourcePath':source_path,'scope':deepcopy(scope)})

    def quantity(q,cid,key):
        if type(q) is not dict or set(q)-{'sourceValue','sourceUnit','unitId','dimension','range','basis','qualifiers'}:
            raise ValueError('nutrient-generation-quantity')
        value=q.get('sourceValue');symbol=q.get('sourceUnit');uid=q.get('unitId')
        if value is not None and type(value) not in (str,int,float):raise ValueError('nutrient-generation-quantity')
        if symbol is not None and type(symbol) is not str:raise ValueError('nutrient-generation-quantity')
        if uid is not None and uid not in units:raise ValueError('nutrient-generation-unit-reference')
        dimension=q.get('dimension','unknown')
        if type(dimension) is not str or dimension not in DIMENSIONS or uid is not None and units[uid]['dimension']!=dimension:
            raise ValueError('nutrient-generation-unit-dimension')
        if type(q.get('qualifiers',[])) is not list:raise ValueError('nutrient-generation-quantity')
        qualifiers=list(q.get('qualifiers',[]))
        if any(type(x) is not str for x in qualifiers):raise ValueError('nutrient-generation-quantity')
        point=_point(value)
        if value is None:qualifiers.append('source-value-unavailable')
        elif point is None:qualifiers.append('source-notation-not-a-qualified-point')
        if uid is None:qualifiers.append('unit-definition-unresolved')
        if q.get('basis') is None:qualifiers.append('basis-not-provided')
        out={'kind':'quantity','value':point,'unitId':uid,'dimension':dimension,'sourceValue':value,
             'sourceUnit':symbol,'qualifiers':sorted(set(qualifiers))}
        if 'range' in q:
            rg=q['range']
            if type(rg) is not dict or set(rg)!= {'min','max'}:raise ValueError('nutrient-generation-range')
            lo,hi=_point(rg['min']),_point(rg['max']);out['range']={'min':lo,'max':hi}
            if lo is not None and hi is not None and lo>hi:
                out['value']=None;out['qualifiers'].append('source-range-conflicting')
                conflicts.append({'kind':'range-order','sourceKey':key,'state':'unresolved-no-reordering'})
        if q.get('basis') is not None:
            if type(q['basis']) is not dict:raise ValueError('nutrient-generation-basis-depth')
            if 'basis' in q['basis']:raise ValueError('nutrient-generation-basis-depth')
            out['basis']=quantity(q['basis'],cid,[key,'basis'])
        return out

    for row in rows:
        if type(row) is not dict or set(row)-{'partitionId','nativeRecordId','sourcePath','kind','name','language','sourceFields',
                'definition','method','quantity','unitId','foodReferenceId','definitionReference'}:
            raise ValueError('nutrient-generation-row')
        if (row.get('partitionId') not in partitions or row.get('kind') not in KINDS or
            not all(_string(row.get(k)) for k in ('nativeRecordId','sourcePath','name')) or
            type(row.get('sourceFields')) is not dict):raise ValueError('nutrient-generation-row')
        if row.get('foodReferenceId') is not None and row['kind']!='FoodCompositionObservation':
            raise ValueError('nutrient-generation-food-reference-role')
        if row.get('definitionReference') is not None and row['kind']!='FoodCompositionObservation':
            raise ValueError('nutrient-generation-definition-reference-role')
        raw=canonical(row);input_bytes+=len(raw)
        if len(raw)>MAX_ROW or input_bytes>MAX_INPUT:raise ValueError('nutrient-generation-input-bound')
        p=partitions[row['partitionId']];language=row.get('language','und')
        if type(language) is not str or not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*',language):raise ValueError('nutrient-generation-language')
        key=[p['sourceId'],p['releaseId'],row['partitionId'],p['assetSha256'],row['nativeRecordId'],row['sourcePath'],row['kind']]
        rid=_id('resource',key);row_sha=sha256(raw).hexdigest()
        if rid in seen:
            if seen[rid]!=row_sha:raise ValueError('nutrient-generation-source-key-conflict')
            continue  # Exact same source occurrence replay, not semantic deduplication.
        seen[rid]=row_sha
        cid=_id('citation',key)
        add('citations',{'id':cid,'sourceId':p['sourceId'],'originalRecordId':row['nativeRecordId'],
            'originalUrl':p['originalUrl'],'revisionId':p['releaseId'],'contentSha256':p['assetSha256'],
            'license':p['license'],'attribution':p['attribution'],'sourcePath':row['sourcePath'],'scope':deepcopy(scope)})
        add('resources',{'id':rid,'type':contract['types'][row['kind']]['id'],'identityStatus':'source-scoped',
            'names':[text(row['name'],cid,[rid,'name'],language)],'citationIds':[cid],'scope':deepcopy(scope)})
        assertion(rid,cid,row['sourcePath'],'original-fields',typed(row['sourceFields'],cid,[rid,'fields'],language),'source-asserted')
        assertion(rid,cid,row['sourcePath'],'operation-receipt',{'kind':'identifier','value':p['operationReceiptSha256']},'candidate')
        for field in ('definition','method'):
            val=row.get(field)
            if val is not None and type(val) is not str:raise ValueError('nutrient-generation-row')
            assertion(rid,cid,row['sourcePath'],field,text(val,cid,[rid,field],language) if val is not None else {'kind':'null','value':None},
                      'source-asserted' if val is not None else 'unknown')
        if 'quantity' in row:
            assertion(rid,cid,row['sourcePath'],'original-quantity-input',typed(row['quantity'],cid,[rid,'quantity-input'],language),'candidate')
            assertion(rid,cid,row['sourcePath'],'quantity',quantity(row['quantity'],cid,rid),'candidate')
        else:assertion(rid,cid,row['sourcePath'],'quantity',{'kind':'null','value':None},'unknown')
        uid=row.get('unitId')
        if uid is not None:
            if uid not in units:raise ValueError('nutrient-generation-unit-reference')
            add('relations',{'id':_id('relation',[rid,'unit',uid]),'subjectId':rid,
                'predicateId':contract['relationshipVocabulary']['candidateMatch' if row['kind']=='Unit' else 'hasUnit']['id'],
                'objectId':uid,'status':'candidate','citationIds':[cid],'scope':deepcopy(scope),'sourcePath':row['sourcePath']})
        food=row.get('foodReferenceId')
        if food is not None:
            if food not in food_externals or food in units:raise ValueError('nutrient-generation-external-reference')
            add('relations',{'id':_id('relation',[food,'nutrient-observation',rid]),'subjectId':food,
                'predicateId':contract['relationshipVocabulary']['hasNutrientObservation']['id'],'objectId':rid,
                'status':'candidate','citationIds':[cid],'scope':deepcopy(scope),'sourcePath':row['sourcePath']})
        locator=(row['partitionId'],row['nativeRecordId'],row['sourcePath'])
        if locator in source_index:raise ValueError('nutrient-generation-source-key-conflict')
        source_index[locator]=(rid,cid,row)
    for rid,cid,row in source_index.values():
        ref=row.get('definitionReference')
        if ref is None:continue
        if type(ref) is not dict or set(ref)!= {'partitionId','nativeRecordId','sourcePath'}:raise ValueError('nutrient-generation-definition-reference')
        target=source_index.get((ref['partitionId'],ref['nativeRecordId'],ref['sourcePath']))
        if target is None:
            conflicts.append({'kind':'definition-reference-unresolved','sourceKey':rid,'reference':deepcopy(ref)})
            assertion(rid,cid,row['sourcePath'],'unresolved-definition-reference',typed(ref,cid,[rid,'definition-ref'],'und'),'unknown')
        else:
            if target[2]['kind']!='NutrientDefinition':raise ValueError('nutrient-generation-definition-reference')
            add('relations',{'id':_id('relation',[rid,'definition',target[0]]),'subjectId':rid,
                'predicateId':contract['relationshipVocabulary']['hasMetricDefinition']['id'],'objectId':target[0],
                'status':'candidate','citationIds':[cid],'scope':deepcopy(scope),'sourcePath':row['sourcePath']})
    for collection in ('resources','assertions','relations','citations'):packet[collection].sort(key=lambda x:x['id'])
    resources={x['id'] for x in packet['resources']}
    for relation in packet['relations']:
        if relation['subjectId'] not in resources|externals or relation['objectId'] not in resources|externals:
            raise ValueError('nutrient-generation-reference-closure')
    output={'moduleVersion':VERSION,'commonSchemaVersion':COMMON,'generationVersion':generation_version,
        'actorReference':actor_reference,'contractSha256':CONTRACT_SHA,'packet':packet,
        'sourcePartitions':deepcopy(partitions),'inputKey':digest([VERSION,CONTRACT_SHA,generation_version,actor_reference,
            partitions,sorted(seen.items()),len(rows),sorted(externals),digest(sorted(protected))]),
        'protectedIdsDigest':digest(sorted(protected)),'conflicts':sorted(conflicts,key=canonical),
        'counts':{'providedRows':len(rows),'uniqueSourceOccurrences':len(seen),'resources':len(resources),
                  'sourceFieldSetsPreserved':len(seen),'semanticMerges':0,'reviewed':0,'GoldAdmitted':0},
        'externalReferenceIds':sorted(externals),'qualification':'author-candidate; source eligibility/admission remains caller-owned'}
    if len(canonical(output))>MAX_OUTPUT:raise ValueError('nutrient-generation-output-bound')
    return output


def persist_cut(root, cut_key, output, *, custody_root):
    """Exclusive caller-selected custody; this boundary does not grant permission."""
    root=Path(os.path.abspath(root))
    custody=Path(os.path.abspath(custody_root))
    if not root.is_relative_to(custody) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,95}',cut_key):
        raise ValueError('nutrient-generation-custody')
    if any(p.is_symlink() for p in (root,*root.parents)) or not root.is_dir():raise ValueError('nutrient-generation-custody')
    raw=canonical(output)+b'\n'
    if len(raw)>MAX_OUTPUT:raise ValueError('nutrient-generation-output-bound')
    target=root/cut_key
    receipt={'moduleVersion':VERSION,'inputKey':output['inputKey'],'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
             'state':'owned-source-scoped-candidate-not-admitted','checkpoint':'complete-owned-cut-only-no-held-source-resume'}
    if target.exists():
        if target.is_symlink() or not target.is_dir():raise ValueError('nutrient-generation-output-held')
        for path in (target/'generation.json',target/'receipt.json'):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1 or path.stat().st_size>MAX_OUTPUT:
                raise ValueError('nutrient-generation-output-held')
        if (target/'generation.json').read_bytes()!=raw or (target/'receipt.json').read_bytes()!=canonical(receipt)+b'\n':
            raise ValueError('nutrient-generation-output-held')
        return receipt
    target.mkdir(mode=0o700)
    for name,data in [('generation.json',raw),('receipt.json',canonical(receipt)+b'\n')]:
        fd=os.open(target/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    directory=os.open(target,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(directory)
    finally:os.close(directory)
    return receipt
