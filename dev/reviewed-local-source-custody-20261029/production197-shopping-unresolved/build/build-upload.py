import pathlib,json,hashlib,gzip,base64,re
r=pathlib.Path(__file__).resolve().parent;old=r.parent/'offmenu-production-lot196-20261029';b=(old/'deployed-application.mjs').read_bytes();c=(r/'deployed-application.mjs').read_bytes();h=lambda x:hashlib.sha256(x).hexdigest();assert h(b)=='965d7eaff351e9aec7278fdd5db0f6ab6ccfbcf3748a30611a57ce47772c4a6d';assert h(c)=='08f5ae17eec6b5bede7c746391952cd3f8190507c7ebccd6abb6cb0c66d3d4a4'
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


s=(old/'upload-template.js').read_text()
m={'8db6b5c4-2e5f-483f-90ea-de0260733526':'abead872-5f5e-48f8-96f8-7cb96446fbbe','1e0e079a-8468-4454-8427-70c789787253':'5cea3fd9-8738-4ab7-a186-e72b96797c48','9a9a15c6da6c12e98c2b9683839da509060cb21e9974b6a562f78d5ebdfddd7d':h(b),'965d7eaff351e9aec7278fdd5db0f6ab6ccfbcf3748a30611a57ce47772c4a6d':h(c),'2507864':str(len(b)),'2570478':str(len(c))}
s=re.sub('|'.join(map(re.escape,m)),lambda x:m[x[0]],s)
s=s.replace('OffMenu reviewed exact-lot nutrient profile selection, planner and cooking consumption, server persistence parity. Prior195 fixes retained, other211 modules and settings unchanged; no automatic identity joins.','OffMenu reviewed shopping unresolved required-demand visibility. No invented purchase quantities; prior196 lot nutrition and server fixes retained; other211 modules/settings unchanged.')
(r/'upload-template.js').write_text(s)
s=s.replace('__DELTA_GZIP__',base64.b64encode(gz).decode()).replace('__GZIP_SHA__',h(gz));(r/'upload-inactive.js').write_text(s);print(json.dumps({'codeBytes':len(s),'gzipBytes':len(gz),'module':h(c)}))
