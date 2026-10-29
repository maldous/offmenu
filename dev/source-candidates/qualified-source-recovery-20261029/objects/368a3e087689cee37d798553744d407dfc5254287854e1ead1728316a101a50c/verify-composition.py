import contextlib,copy,hashlib,importlib.util,importlib.metadata,io,json,platform,sys
from pathlib import Path
from unittest.mock import patch
import openpyxl,jsonschema_rs
ROOT=Path('/tmp/offmenu-dk-m002-922-20261017');OUT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
collector=load('m002collect',ROOT/'scripts/collect-national.py')
aligner=load('m002align',ROOT/'scripts/align-national-common.py')
curation=load('m002curation',ROOT/'corpus/curation.py')
schema=json.loads((ROOT/'corpus/common-data.schema.json').read_text());v=jsonschema_rs.Draft202012Validator(schema,validate_formats=True)
checks=[];graphs=[]
def passed(name,**kw):checks.append({'case':name,'passed':True,**kw})
def collect(parameters):
 w=openpyxl.Workbook();w.remove(w.active)
 f=w.create_sheet('Food');f.append(['da','en','id']);f.append(['syntetisk','Synthetic food',1])
 p=w.create_sheet('Parameter');p.append(['header']*11)
 d=w.create_sheet('Data_Normalised');d.append(['header']*14)
 for pid,unit,matrix,raw in parameters:
  a=[None]*11;a[1]='Synthetic '+str(pid);a[2]=unit;a[4]=pid;a[9]='kJ' if pid==137 else 'g';a[10]=matrix;p.append(a)
  a=[None]*14;a[0]=1;a[3]=pid;a[7]=raw;a[12]='synthetic';d.append(a)
 with patch.object(collector.openpyxl,'load_workbook',return_value=w) as read,contextlib.redirect_stdout(io.StringIO()):r=collector.frida(Path('/SYNTHETIC_NO_SOURCE_IO'))[0]
 assert read.call_count==1
 w.close();return r
pids=[(363,'g/ml'),(12,'RE (µg/100g)'),(135,'alfa-TE'),(203,'NE')]
for pid,literal in pids:
 for unit in [None,literal]:
  for matrix in ['W','SYNTHETIC_NON_W']:
   for raw in [None,0,'TRACE','<0.1','1,25']:
    r=collect([(pid,unit,matrix,raw)]);snapshot=copy.deepcopy(r);n=r['data']['nutrients']['frida:parameter:'+str(pid)]
    assert n['unit']==unit and 'basis' not in n and n['sourceMatrixUnitCode']==matrix
    numeric=collector.national.numeric(raw)
    assert all(n[k]==val for k,val in numeric.items())
    g=aligner.graph(r);v.validate(g)
    q=next(a['value'] for a in g['assertions'] if a['propertyId'].endswith(':metricValue'))
    assert q['value'] is None and 'basis' not in q and q['sourceValue']==numeric['value'] and q['sourceUnit']==unit
    assert 'basis-unresolved-no-profile-inheritance' in q['qualifiers']
    if unit is None:assert q['unitId'] is None
    assert snapshot==r
    passed(f'{pid}/{unit!r}/{matrix}/{raw!r}',schemaValid=True)
    if raw=='1,25' and matrix=='W':graphs.append(g)
# Legacy numeric records must also be held by definition, even with generic unit/basis.
basis={'kind':'quantity','value':100,'unitId':'urn:offmenu:unit:g','dimension':'mass','sourceValue':100,'sourceUnit':'g','qualifiers':['source-basis']}
for pid,_ in pids:
 q=aligner.quantity({'value':123.5,'unit':'g','definition':'Frida:'+str(pid)},'en','synthetic','synthetic',basis)
 assert q['value'] is None and 'basis' not in q and q['sourceValue']==123.5
 passed('legacy/'+str(pid))
# Unaffected definitions retain current numeric and basis behavior.
for definition in ['Frida:137','Other:363']:
 q=aligner.quantity({'value':12.5,'unit':'g','definition':definition},'en','synthetic','synthetic',basis)
 assert q['value']==12.5 and q['basis']==basis
 passed('unaffected/'+definition)
r=collect([(p,u,'W',1.25) for p,u in pids]+[(137,'kJ/100g','W',100)])
snapshot=copy.deepcopy(r);projected,held=curation.curate([r],'SYNTHETIC_ONLY')
assert snapshot==r and len(projected)==1 and not held
assert not any('frida:parameter:'+str(pid) in projected[0]['data']['nutrients'] for pid,_ in pids)
assert projected[0]['data']['nutrients']['energyKJ']['value']==100
v.validate(aligner.graph(projected[0]));passed('mixed-curation-four-withheld-energy-retained')
r=collect([(p,u,'W',1.25) for p,u in pids]);projected,held=curation.curate([r],'SYNTHETIC_ONLY')
assert not projected and len(held)==1 and held[0]['reason']=='no usable mapped composition facts';passed('affected-only-withheld')
# Actual Rust validator rejects prior nullable-basis encoding; omit is accepted.
bad=copy.deepcopy(graphs[0]);q=next(a['value'] for a in bad['assertions'] if a['propertyId'].endswith(':metricValue'));q['basis']=None
assert not v.is_valid(bad);passed('rust-validator-rejects-basis-null-negative-control')
(OUT/'synthetic-caller-input.json').write_text(json.dumps(graphs,ensure_ascii=False)+'\n')
environment={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':{p:importlib.metadata.version(p) for p in ['openpyxl','jsonschema','jsonschema-rs']},'modulePaths':{'collector':collector.__file__,'aligner':aligner.__file__,'national':collector.national.__file__,'afcd':collector.afcd.__file__,'curation':curation.__file__,'jsonschema_rs':jsonschema_rs.__file__,'openpyxl':openpyxl.__file__},'dependencyInventory':sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())}
(OUT/'runtime-evidence.json').write_text(json.dumps(environment,indent=2)+'\n')
(OUT/'focused-results.json').write_text(json.dumps({'status':'PASS','groups':len(checks),'checks':checks,'syntheticOnly':True,'realSourceRecordsRead':0,'actualModuleImports':True,'validator':'jsonschema-rs 0.58.6 Draft202012Validator(validate_formats=True)','openpyxl':'3.1.5 actual in-memory Workbook; only load_workbook is mocked; actual collector.frida/national.numeric/wrap/align.graph/curation.curate executed'},indent=2)+'\n')
print(json.dumps({'status':'PASS','groups':len(checks),'callerGraphs':len(graphs),'packages':environment['packages']}))
