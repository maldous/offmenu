#!/usr/bin/env python3
"""Bounded, read-only structural evidence for one immutable acquisition receipt."""
import hashlib
import json
import math
import os
import stat
import sys

PARTS = ('home','user','src','offmenu-data','national-originals','acquisition.json')
PIN = '654f91bd14d83b7b55a058777a0b8fd836674310e3dc38235638ec9435dc4edc'
CAP = 65536
KNOWN = {
 'norway/en-foods.json': ('NO_EN_FOODS',13690405,'89b8f5f494a79731bf7d8d98065ee66c55263ccdbb519e7c87941218be6c948d'),
 'norway/nb-foods.json': ('NO_NB_FOODS',13690645,'7c7ebb52109433ea15032a29f495843a5da229313bbcf4a4fe7ebcc45b9c9b33'),
 'norway/en-nutrients.json': ('NO_EN_NUTRIENTS',13081,'15a95f0ebd0682daa293685203dad9aaa28b07df4e9b943ca03269161fbefd91'),
 'norway/en-sources.json': ('NO_EN_SOURCES',97245,'71917dadc84a5218bb3a78327cda6945c48eb6b2e72e4ee7fbf0c23ab7f6778d'),
 'ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx': ('FR_WORKBOOK',1537602,'2c3495c8136d17356c50db410918da2102cb28096cb497c9cdf83c5f8ecb10ba'),
 'ciqual/alim_2025_11_03.xml': ('FR_IDENTITIES',1581031,'e0b1de25b3039028205e9d54a96892e403e1b313c2efeb41180fabe132627478'),
}
KEYS = frozenset(('key','path','file','filename','name','bytes','size','sizeBytes','sha256','acquiredAt','completedAt','files','sourceFiles','downloads','records','sources','acquisition','schemaVersion','status','error','url','method','license'))
IDENTITIES = ('key','path','file','filename','name')

class Refused(Exception):
    pass

def sig(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def read_receipt():
    handles=[];links=[]
    try:
        parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY);handles.append(parent)
        for part in PARTS[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            handles.append(child);links.append((parent,part,child,sig(os.fstat(child))))
            parent=child
        before=os.stat(PARTS[-1],dir_fd=parent,follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>CAP:raise Refused('unsafe-receipt')
        fd=os.open(PARTS[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);handles.append(fd)
        if sig(os.fstat(fd))!=sig(before):raise Refused('receipt-changed')
        body=bytearray()
        while len(body)<before.st_size:
            chunk=os.read(fd,min(8192,before.st_size-len(body)))
            if not chunk:raise Refused('receipt-changed')
            body.extend(chunk)
        if sig(os.fstat(fd))!=sig(before) or sig(os.stat(PARTS[-1],dir_fd=parent,follow_symlinks=False))!=sig(before):raise Refused('receipt-changed')
        for ancestor,name,child,original in links:
            if sig(os.fstat(child))!=original or sig(os.stat(name,dir_fd=ancestor,follow_symlinks=False))!=original:raise Refused('receipt-changed')
        if hashlib.sha256(body).hexdigest()!=PIN:raise Refused('historical-pin-mismatch')
        return bytes(body)
    finally:
        for fd in reversed(handles):os.close(fd)

def strict_json(body):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError()
            out[k]=v
        return out
    def finite(v):
        n=float(v)
        if not math.isfinite(n):raise ValueError()
        return n
    def invalid(v):raise ValueError()
    return json.loads(body.decode('utf-8'),object_pairs_hook=pairs,parse_float=finite,parse_constant=invalid)

def kind(v):
    return {dict:'object',list:'array',str:'string',int:'integer',float:'number',bool:'boolean',type(None):'null'}.get(type(v),'unknown')

def timestamp_valid(v):
    import datetime
    if not isinstance(v,str) or len(v)>32:return False
    try:
        d=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
        return d.tzinfo is not None and d.utcoffset()==datetime.timedelta(0)
    except ValueError:return False

def inspect(value):
    result={'rootType':kind(value),'rootCount':len(value) if type(value) in (dict,list) else None,'nodes':[],'selected':[],'unknownFieldOccurrences':0,'truncated':False}
    def walk(v,path,depth):
        if len(result['nodes'])>=160 or depth>4:
            result['truncated']=True;return
        if type(v) is dict:
            types={k:kind(v[k]) for k in sorted(KEYS) if k in v}
            result['nodes'].append({'position':path,'type':'object','count':len(v),'fieldTypes':types,'unknownFields':sum(k not in KEYS for k in v)})
            result['unknownFieldOccurrences']+=sum(k not in KEYS for k in v)
            for field in IDENTITIES:
                identity=v.get(field)
                if type(identity) is str and identity in KNOWN:
                    asset,size,digest=KNOWN[identity];item={'position':path,'identityField':field,'assetId':asset}
                    for k,expected in (('bytes',size),('size',size),('sizeBytes',size),('sha256',digest)):
                        if k in v:
                            actual=v[k];match=type(actual) is type(expected) and actual==expected
                            item[k]={'type':kind(actual),'matchesObservedRaw':match}
                            if match:item[k]['value']=expected
                    item['acquiredAt']={'type':kind(v['acquiredAt']) if 'acquiredAt' in v else 'absent','validUTC':timestamp_valid(v.get('acquiredAt'))}
                    result['selected'].append(item)
            for k in sorted(KEYS):
                if k in v and type(v[k]) in (dict,list):walk(v[k],path+[k],depth+1)
        elif type(v) is list:
            result['nodes'].append({'position':path,'type':'array','count':len(v)})
            for n,item in enumerate(v):
                if n>=128:result['truncated']=True;break
                walk(item,path+[n],depth+1)
        else:result['nodes'].append({'position':path,'type':kind(v)})
    walk(value,[],0)
    failures=[];seen=set()
    if type(value) is not list or len(value)>512:failures.append({'code':'root-not-supported-list'})
    else:
        for n,item in enumerate(value):
            if type(item) is not dict or type(item.get('key')) is not str:
                failures.append({'index':n,'code':'entry-not-object-or-key-not-string'});continue
            key=item['key']
            if key not in KNOWN:continue
            digest=item.get('sha256');size=item.get('bytes')
            if key in seen or type(size) is not int or not 0<=size<=64*1024*1024 or type(digest) is not str or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                failures.append({'index':n,'assetId':KNOWN[key][0],'code':'selected-declaration-invalid-or-duplicate'})
            seen.add(key)
    result['currentParserFailures']=failures[:64]
    result['currentParserFailureCount']=len(failures)
    result['currentParserFailuresOmitted']=max(0,len(failures)-64)
    result['currentParserWouldAccept']=not failures
    # Retain decision summaries if a hostile but pinned shape is verbose.
    while len(json.dumps(result,separators=(',',':')).encode())>14500:
        result['truncated']=True
        if result['nodes']:result['nodes'].pop()
        elif result['selected']:result['selected'].pop()
        else:break
    return result

def main():
    result={'schemaVersion':'offmenu-acquisition-shape/1','readOnly':True,'sourceBodiesParsed':0,'sourceBytesWritten':0}
    try:
        if os.geteuid()==0 or not sys.flags.isolated:raise Refused('normal-user-isolated-python-required')
        if len(sys.argv)!=1:raise Refused('arguments-not-allowed')
        body=read_receipt();result.update(status='inspected',bytes=len(body),historicalSha256=PIN,historicalMatch=True)
        result['structure']=inspect(strict_json(body))
        encoded=json.dumps(result,sort_keys=True,separators=(',',':'))
        if len(encoded.encode())>16384:raise Refused('structural-report-limit')
    except Refused as exc:
        result={'schemaVersion':'offmenu-acquisition-shape/1','status':'blocked','errorCode':str(exc),'readOnly':True}
    except (ValueError,UnicodeError,RecursionError):
        result={'schemaVersion':'offmenu-acquisition-shape/1','status':'blocked','errorCode':'invalid-json','readOnly':True}
    except OSError as exc:
        result={'schemaVersion':'offmenu-acquisition-shape/1','status':'blocked','errorCode':'receipt-unreadable','errno':exc.errno if type(exc.errno) is int and 0<exc.errno<4096 else None,'readOnly':True}
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0 if result['status']=='inspected' else 2

if __name__=='__main__':sys.exit(main())
