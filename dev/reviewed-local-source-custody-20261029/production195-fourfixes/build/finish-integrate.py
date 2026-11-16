import pathlib,json,hashlib,shutil
r=pathlib.Path(__file__).resolve().parent;e=r/'export';a=r/'candidate-source-root/candidate-source/app';p=a/'public/scanner-ui.js';s=p.read_text()
# Only rejected context hunks: existing production short status strings are retained.
old='    } catch {\n      if(sessionToken!==token) return;\n      if(native)';new='    } catch {\n      if(!currentAccess(sessionToken)) return;\n      if(native)';assert s.count(old)==1;s=s.replace(old,new)
start=s.index('  async function start()');end=s.index('\n  }',start)+4;part=s[start:end]
old="if(error.name!=='OverconstrainedError' || sessionToken!==token) throw error;";assert part.count(old)==1;part=part.replace(old,"if(error.name!=='OverconstrainedError' || !currentAccess(sessionToken)) throw error;")
old='if(sessionToken!==token) { acquired.getTracks().forEach(t=>t.stop()); return; }';assert part.count(old)==1;part=part.replace(old,'if(sessionToken!==token || !canScan()) { acquired.getTracks().forEach(t=>t.stop()); if(sessionToken===token) stop(); return; }')
assert part.count('if(sessionToken!==token) return;')==4;part=part.replace('if(sessionToken!==token) return;','if(!currentAccess(sessionToken)) return;');s=s[:start]+part+s[end:];p.write_text(s)
for suffix in ['.rej','.orig']:
 q=pathlib.Path(str(p)+suffix)
 if q.exists():q.unlink()
changes=['public/scanner-ui.js']
for d in ['cook-retry-contract-20261029','history-zero-roundtrip-20261029','pantry-required-demand-20261029']:
 x=json.loads((e/d/('predicate-replacement.json' if d.startswith('pantry') else 'replacement.json')).read_text());p=a/x['path'];s=p.read_text();assert s.count(x['old'])==1,x['path'];p.write_text(s.replace(x['old'],x['new']));changes.append(x['path'])
for d in e.iterdir():
 if d.is_dir():
  for test in (d/'tests-web').glob('*'):shutil.copyfile(test,a/'tests-web'/test.name)
m=r/'candidate-source-root/candidate-source-manifest.json';data=json.loads(m.read_text())
for path in changes:
 item=next(x for x in data['files'] if x['group']=='app' and x['path']==path);b=(a/path).read_bytes();item.update(afterSha256=hashlib.sha256(b).hexdigest(),bytes=len(b),integrationReason='Approved exact function-local four-fix integration; preserve production194 status strings and expiry/date correction')
m.write_text(json.dumps(data,indent=2)+'\n');(r/'integration-changed-paths.json').write_text(json.dumps(changes,indent=2)+'\n')
