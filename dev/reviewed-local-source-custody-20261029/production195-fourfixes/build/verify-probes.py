import subprocess,json,hashlib,pathlib,concurrent.futures,tempfile
root=pathlib.Path('offmenu-production-fourfix195-20261029'); paths=['/app.js','/','/auth.html','/kitchen.html','/shelf-scanner.html','/api/kitchens','/api/product?barcode=0000000000000','/api/prices','/landing-static-15/story.js']
def check(path):
 with tempfile.TemporaryDirectory() as td:
  b=pathlib.Path(td)/'body';h=pathlib.Path(td)/'headers';p=subprocess.run(['curl','-sS','--max-time','30','-o',str(b),'-D',str(h),'-w','%{http_code}\n%{content_type}','https://offmenu.aldous.info'+path],capture_output=True,text=True);body=b.read_bytes() if b.exists() else b'';headers=h.read_text() if h.exists() else '';selected=[x for x in headers.splitlines() if x.lower().startswith(('content-type:','cache-control:','vary:','location:'))];return {'path':path,'status':p.stdout.splitlines()[0] if p.stdout else '', 'headers':selected,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'curlExit':p.returncode}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(check,paths))
(root/'served-probes.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
