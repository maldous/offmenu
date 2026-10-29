from pathlib import Path
import json,hashlib,datetime,sys,re
root=Path(__file__).resolve().parent
base=root.parent/'native15-landing-integration-20261026/production-v12-firstpair-20261026'
current=base/'r3-final/landing-only.mjs'
sha=lambda b:hashlib.sha256(b).hexdigest()
pin=lambda p:{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
# The selected file is a Root-owned, source-pinned list of author outputs.
# No source/provider factory, DB, network or runtime constructor is invoked.
if len(sys.argv)!=3:raise SystemExit('usage: build-scoped-package.py SELECTED_INPUT_JSON NEW_OUTPUT_DIRECTORY')
selection=Path(sys.argv[1]).resolve();spec=json.loads(selection.read_text());target=Path(sys.argv[2]).resolve()
assert target.parent==root and not target.exists(),'New owned output directory required'
assert pin(current)['sha256']=='f2897a2ba05a017b2ac107f5098e89fdb8ecf2c51120119ae4794f6e69402f59'
assert spec['baseVersion']=='7efbc8be-c699-43b3-a0db-a31048422f7d'
assert spec['sourceSelection']=='EXACT_SOURCE_PINS_SELECTED'
assert spec['overrides'] and len({r['route'] for r in spec['overrides']})==len(spec['overrides'])
code=current.read_text();start=code.index('const assets=')+13;end=code.index(';\nObject.assign(assets,',start)
assets=json.loads(code[start:end]);old=json.loads(code[start:end])
previous=json.loads((base/'candidate-v14-final/manifest.json').read_text())
allowedLanding={'/','/landing.html','/landing-static-15/story.css','/landing-static-15/story.js','/landing-static-15/release.json'}
allowedDemo=lambda r:r.startswith('/demo/') and r!='/demo/api/product'
for row in spec['overrides']:
 assert row['route'] in allowedLanding or allowedDemo(row['route']),'Scoped public assets only'
 assert row['route'] not in ['/auth.js','/auth.html','/kitchen.html']
 p=Path(row['path']);assert p.is_absolute() and p.is_file() and sha(p.read_bytes())==row['sha256']
 assert row['mime'] in ['text/html; charset=utf-8','text/css; charset=utf-8','application/javascript; charset=utf-8','application/wasm','application/json','text/plain; charset=utf-8','image/svg+xml','font/ttf','image/png']
target.mkdir();parts=[];bindings={};routes={};imports=[];used=set()
for index,row in enumerate(spec['overrides']):
 route=row['route'];data=Path(row['path']).read_bytes();chunks=[]
 for offset in range(0,len(data),600000):
  part=data[offset:offset+600000];module='public-fix-'+sha(data)[:16]+'-'+str(offset//600000+1).zfill(2)+'.bin'
  # Same exact bytes may be shared by two routes, e.g. root and landing.html.
  if module not in used:
   used.add(module);dest=target/module;dest.write_bytes(part);variable='publicFixPart'+str(len(imports))
   imports.append((module,variable));parts.append({'module':module,**pin(dest),'offset':offset,'source':pin(Path(row['path']))})
  variable=next(v for m,v in imports if m==module);chunks.append(variable)
 bindings[route]='{mime:'+json.dumps(row['mime'])+',parts:['+','.join(chunks)+']}'
 assets.pop(route,None);routes[route]={**row,'bytes':len(data)}
prefix=''.join("import "+v+" from './"+m+"';\n" for m,v in imports)
binding='Object.assign(assets,{'+','.join(json.dumps(r)+':'+v for r,v in bindings.items())+'});\n'
suffix=code[end:];assert suffix.count('const headers=')==1;suffix=suffix.replace('const headers=',binding+'const headers=',1)
new=prefix+code[:start]+json.dumps(assets,ensure_ascii=False,separators=(',',':'))+suffix
assert suffix.replace(binding,'',1)==code[end:],'Original public handler/private dispatcher/security headers must be byte-identical'
assert all(assets[k]==v for k,v in old.items() if k not in routes)
entry=target/'landing-only.mjs';entry.write_text(new)
manifestRoutes=[routes.pop(r['route'],r) for r in previous['routes']];manifestRoutes.extend(routes.values())
headers=json.loads(code.split('const headers=')[1].split(';\nasync function publicDemoProduct')[0])
manifest={'id':spec['id'],'atUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'module':pin(entry),'baseVersion':spec['baseVersion'],'baseModule':pin(current),'selection':pin(selection),'sourceEvidence':spec['sourceEvidence'],'binaryParts':parts,'routes':manifestRoutes,'routeCount':len(manifestRoutes),'overriddenRoutes':[r['route'] for r in spec['overrides']],'headers':headers,'preservation':{'allUnselectedTextAssets':True,'originalSuffixIncludingLookupPrivateGuardsAndHeadersByteIdentical':True,'original30BinaryImportsAndPreviousDelegationPreserved':True},'scope':'LOCAL_IMMUTABLE_PACKAGE_ONLY_NO_PROVIDER_WRITES; requires exactexecutablequalification/64actualvertical+fullscannerproof and applicable scopedreleaseauthority'}
(target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(target/'binary-transfer-plan.json').write_text(json.dumps({'parts':parts},indent=2)+'\n')
print(json.dumps({'module':manifest['module'],'manifest':pin(target/'manifest.json'),'routes':len(manifestRoutes),'newBinaryParts':len(parts),'newProviderWrites':0}))

