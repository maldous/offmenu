import pathlib,json,hashlib,gzip,base64,re
r=pathlib.Path(__file__).resolve().parent;old=r.parent/'offmenu-production-household194-20261028';b=(old/'deployed-application.mjs').read_bytes();c=(r/'deployed-application.mjs').read_bytes();h=lambda x:hashlib.sha256(x).hexdigest();assert h(b)=='7ef438457349a113e48a3c3546b8ac268fb5756d6b25f1ec47c4cb934a090fcc';assert h(c)=='9a9a15c6da6c12e98c2b9683839da509060cb21e9974b6a562f78d5ebdfddd7d'
ops=[];at=0
for start in range(0,len(b),16384):
 block=b[start:start+16384]
 if len(block)<256:continue
 found=c.find(block,at)
 if found<0:continue
 if found>at:ops.append({'insert':base64.b64encode(c[at:found]).decode()})
 if ops and 'copy' in ops[-1] and sum(ops[-1]['copy'])==start:ops[-1]['copy'][1]+=len(block)
 else:ops.append({'copy':[start,len(block)]})
 at=found+len(block)
if at<len(c):ops.append({'insert':base64.b64encode(c[at:]).decode()})
delta={'schema':'offmenu-exact-module-delta/1','before':{'bytes':len(b),'sha256':h(b)},'after':{'bytes':len(c),'sha256':h(c)},'operations':ops}
assert b''.join(b[x['copy'][0]:sum(x['copy'])] if 'copy' in x else base64.b64decode(x['insert']) for x in ops)==c
gz=gzip.compress(json.dumps(delta).encode(),mtime=0);(r/'delta.gz').write_bytes(gz)
s=(old/'upload-template.js').read_text();m={'d572a1e0-f43d-432b-8033-fc78564ef7c9':'40a3e73d-6aac-45ea-b7e4-8d529376c812','acff5306-b021-42fb-9a2e-92ef7618b5fa':'554724b3-a638-4f81-8c34-bcc52214806f','0e4420ef0152586a80cf982d7084582180b9e8798d9dd87cb6aae304da305a34':h(b),'7ef438457349a113e48a3c3546b8ac268fb5756d6b25f1ec47c4cb934a090fcc':h(c),'2507100':str(len(b)),'2507611':str(len(c)),'OffMenu reviewed shopping canWrite guards, unknown intake CSV blanks, stale household editor scope guard. App asset only; prior fixes and other211 modules/settings preserved. No held shopping-deficit adoption.':'OffMenu reviewed scanner access recheck, measured pantry demand, cooking retry contract and history zero roundtrip including server parity; prior194 fixes retained; other211 modules and settings unchanged.'}
s=re.sub('|'.join(map(re.escape,m)),lambda x:m[x[0]],s);(r/'upload-template.js').write_text(s);s=s.replace('__DELTA_GZIP__',base64.b64encode(gz).decode()).replace('__GZIP_SHA__',h(gz));(r/'upload-inactive.js').write_text(s);print(json.dumps({'codeBytes':len(s),'gzipBytes':len(gz),'module':h(c)}))
