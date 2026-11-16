import hashlib,json,re

def main(rows:list,documents:list):
    if len(rows)>100 or len(documents)>40: raise ValueError('bounded metadata only')
    texts=[]
    for d in documents:
        raw=d['text'].encode()
        if len(raw)>300000 or hashlib.sha256(raw).hexdigest()!=d['sha256']: raise ValueError('source pin mismatch')
        obj=json.loads(d['text']); texts.append((d['name'],d['sha256'],obj))
    def leaves(o,p=''):
        if isinstance(o,dict):
            for k,v in o.items(): yield from leaves(v,p+'/'+str(k).replace('~','~0').replace('/','~1'))
        elif isinstance(o,list):
            for i,v in enumerate(o): yield from leaves(v,p+'/'+str(i))
        elif isinstance(o,str): yield p,o
    ix=[(name,sha,p,s) for name,sha,obj in texts for p,s in leaves(obj)]
    out=[]
    for r in rows:
        text=json.dumps(r['historical'],sort_keys=True)
        pins=sorted(set(re.findall(r'(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])',text)))
        threads=sorted(set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',text)))
        exact=[]
        for token in pins+threads:
            hits=[{'file':n,'file_sha256':sha,'pointer':p} for n,sha,p,s in ix if token in s]
            exact.append({'token':token,'kind':'sha256' if len(token)==64 else 'thread_id','references':hits,'artifact_or_review_verified':False})
        owner=r['historical'].get('owner')
        refs=[]
        for n,sha,obj in texts:
            if not isinstance(obj,list):continue
            for i,item in enumerate(obj):
                if not isinstance(item,dict):continue
                v=item.get('value',{})
                if isinstance(v,dict) and v.get('owner')==owner and owner is not None:
                    refs.append({'file':n,'file_sha256':sha,'pointer':'/'+str(i),'path':v.get('path'),'correlation':v.get('correlation'),'receipt_kind':'transport_admission_not_review_acceptance'})
        out.append({'id':r['id'],'historical_owner':owner,'exact_bindings':exact,'custody_recovery_pointers':refs,'completion_claimed':False,'next_required':'Retrieve referenced immutable artifact/review through existing permitted custodian; transport acknowledgements do not establish acceptance.'})
    return {'result_sha256':hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'recovery_pointer_count':sum(len(r['custody_recovery_pointers']) for r in out),'rows_with_recovery_pointers':[r['id'] for r in out if r['custody_recovery_pointers']],'exact_bindings':[{'id':r['id'],'bindings':r['exact_bindings']} for r in out if r['exact_bindings']],'schema':'offmenu-retained-custody-join/1','source_document_count':len(texts),'obligation_count':len(out),'completed_obligations':0,'no_raw_datasets':True,'no_network_or_host_write':True}
