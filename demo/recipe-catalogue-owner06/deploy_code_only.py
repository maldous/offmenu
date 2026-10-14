#!/usr/bin/env python3
"""Explicitly authorized additive Netlify code-only deployment.
Reuses every existing production digest; uploads ONLY manifest-listed UI bytes.
CLI authentication is used internally; no credential file/value is read here.
"""
import hashlib,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
LOCAL=ROOT/'.local'
SITE='a1df1508-4bb9-4b55-ab1f-88611e456e61'
def api(method,data,label):
 path=LOCAL/(label+'-request.json');path.write_text(json.dumps(data,separators=(',',':')))
 r=subprocess.run(['node',str(LOCAL/'netlify-cli-file.mjs'),method,str(path)],capture_output=True,text=True,timeout=75)
 if r.returncode:raise RuntimeError(method+' failed: '+r.stderr[:1200])
 result=json.loads(r.stdout);(LOCAL/(label+'-response.json')).write_text(json.dumps(result,indent=2)+'\n');return result
phase=sys.argv[1];assert phase in ['draft','production']
if (ROOT/'cancellation-receipt.json').exists():raise RuntimeError('Production publication was explicitly cancelled. No API calls or writes are permitted by this candidate.')
m=json.loads((ROOT/'production-manifest.json').read_text());assert m['newRealRecipeRecordUploads']==0 and m['reuse']['everyExistingPathDigestPreserved']
site=api('getSite',{'site_id':SITE},phase+'-site-readback');assert site['published_deploy']['id']==m['destination']['baselinePublishedDeployId'],'Production changed: reconcile before adding anything'
baseline=json.loads((LOCAL/'existing-site-files.json').read_text());files={x['path']:x['sha'] for x in baseline};uploads={}
for item in m['newUploads']:
 p=pathlib.Path(item['localPath']);b=p.read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'] and hashlib.sha1(b).hexdigest()==item['sha1'];assert item['path']not in files
 files[item['path']]=item['sha1'];uploads[item['sha1']]=(item,b)
assert all(files[x['path']]==x['sha'] for x in baseline)
if phase=='production':
 proof=json.loads((LOCAL/'draft-browser-verification.json').read_text());assert proof['htmlAssetsAndCspPassed'] and proof['existingRootAndManifestHeadersPreserved'] and proof['browserCount']==25135 and proof['searchAndDetailRendered']
body={'site_id':SITE,'title':'OffMenu recipe catalogue — '+phase+' — additive UI, existing public recipes','body':{'files':files,'draft':phase=='draft','async':True,'functions':{}}}
if len(sys.argv)>2:
 id=sys.argv[2];d=api('getDeploy',{'deploy_id':id},phase+'-reconcile');assert d['site_id']==SITE and d.get('title')==body['title'],'Unowned deploy or phase mismatch';print(json.dumps({'resumingOwnedDeploy':id,'phase':phase,'state':d['state']}),flush=True)
else:
 d=api('createSiteDeploy',body,phase+'-create');id=d['id'];print(json.dumps({'createdDeploy':id,'phase':phase,'state':d['state'],'existingFilesReused':len(baseline),'realRecipeBytesUploaded':0}),flush=True)
for attempt in range(60):
 d=api('getDeploy',{'deploy_id':id},phase+'-poll')
 if d['state'] in ['prepared','ready','uploaded']:break
 if d['state']=='error':raise RuntimeError(d.get('error_message','Provider preparation failed'))
 time.sleep(2)
else:raise RuntimeError('Preparation timeout; no broad data upload permitted')
required=d.get('required')or[];assert set(required)<=set(uploads),'Provider requested non-UI digests: refuse corpus upload'
assert not d.get('required_functions') and not d.get('required_edge_functions') and not d.get('required_server')
for digest in required:
 item,b=uploads[digest];data={'deploy_id':id,'path':item['path'].lstrip('/'),'size':len(b),'body':b.decode('utf8')};api('uploadDeployFile',data,phase+'-upload-'+digest)
for attempt in range(90):
 d=api('getDeploy',{'deploy_id':id},phase+'-ready')
 if d['state']=='ready':break
 if d['state']=='error':raise RuntimeError(d.get('error_message','Provider deploy failed'))
 time.sleep(2)
else:raise RuntimeError('Readiness timeout; retained provider receipt for inspection')
receipt={'schema':'offmenu-code-only-deploy/1','phase':phase,'siteId':SITE,'deployId':id,'state':d['state'],'deployUrl':d.get('deploy_ssl_url')or d.get('deploy_url'),'productionUrl':'https://offmenu-corpus.netlify.app/recipes/','manifestSha256':hashlib.sha256((ROOT/'production-manifest.json').read_bytes()).hexdigest(),'newUploadBytes':sum(uploads[x][0]['bytes']for x in required),'uploadedPaths':[uploads[x][0]['path']for x in required],'existingFilesReused':len(baseline),'newRealRecipeBytesUploaded':0,'publishedAt':d.get('published_at'),'draft':phase=='draft'}
out=LOCAL/(phase+'-deploy-receipt.json');out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
