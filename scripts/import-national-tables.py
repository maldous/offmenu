#!/usr/bin/env python3
"""Normalize verified CC BY/OGL national workbooks into source-partitioned public D1 rows.
No household records are changed. Input files remain external licensed datasets.
"""
import argparse,datetime,hashlib,json,math,re,gzip,base64,unicodedata
from pathlib import Path
import openpyxl

def numeric(raw):
 if raw is None or str(raw).strip() in ('','-'):return {'value':None,'qualifier':'unknown'}
 s=str(raw).strip().replace(',','.')
 if s.upper() in ('TR','TRACE'):return {'value':None,'qualifier':'trace'}
 if s.upper()=='N':return {'value':None,'qualifier':'present-no-reliable-amount'}
 if s.upper() in ('ND','NOT DETECTED'):return {'value':None,'qualifier':'not-detected'}
 if s.upper() in ('NT','NOT TESTED'):return {'value':None,'qualifier':'not-tested'}
 m=re.match(r'^<\s*([\d.]+)$',s)
 if m:return {'value':None,'qualifier':'less-than','limit':float(m[1])}
 try:
  value=float(s)
  return {'value':value if math.isfinite(value) else None,'qualifier':'source'}
 except ValueError:return {'value':None,'qualifier':'source-text','originalText':str(raw)}

def wrap(source,code,country,data,url,license,credit,release):
 return {'schemaVersion':'1.0','kind':'nutrientProfile','id':source+':nutrientProfile:'+code,'countries':[country],'provenance':{'sourceId':source,'recordId':code,'url':url,'license':license,'attribution':credit,'fetchedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceDate':release,'visibility':'public','transform':'offmenu-national-tables/1.0','rights':'Original source terms govern reuse; normalization does not relicense the data.'},'data':data}

def ciqual(root):
 fr=openpyxl.load_workbook(root/'ciqual2025-fr.xlsx',read_only=True,data_only=True).worksheets[0]
 en=openpyxl.load_workbook(root/'ciqual2025-en.xlsx',read_only=True,data_only=True).worksheets[0]
 english={str(r[6]):r[7] for r in en.iter_rows(min_row=2,values_only=True) if r[6]}
 headers=next(fr.iter_rows(values_only=True));canonical={10:'energy',14:'protein',15:'proteinNx625',16:'carbohydrate',17:'fat',18:'sugars',26:'fibre',31:'saturatedFat',49:'salt',50:'calcium',53:'iron',58:'potassium',60:'sodium'}
 records=[]
 for row in fr.iter_rows(min_row=2,values_only=True):
  if not row[6]:continue
  code=str(row[6]);basis={'amount':100,'unit':'g','state':'as-described','portion':'source edible portion'};nutrients={}
  for i in range(9,83):
   header=' '.join(str(headers[i]).split());unit='µg' if 'µg' in header else 'mg' if '(mg' in header else 'kcal' if '(kcal' in header else 'kJ' if '(kJ' in header else 'g'
   key=canonical.get(i,'ciqual:column:'+str(i+1));nutrients[key]={**numeric(row[i]),'unit':unit,'name':header,'sourceColumn':i+1,'method':'ANSES CIQUAL 2025; original calculation definition retained'}
  records.append(wrap('ciqual',code,'FR',{'foodName':row[7],'names':{'fr':row[7],**({'en':english[code]} if english.get(code) else {})},'identifiers':[{'system':'ANSES-CIQUAL','value':code}],'basis':basis,'groups':[x for x in row[3:6] if x],'scientificName':row[8],'nutrients':nutrients},'https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2FRDMHWY','Etalab Licence Ouverte 2.0','ANSES — Table de composition nutritionnelle des aliments CIQUAL 2025','2025'))
 return records

def bls(root):
 sheet=openpyxl.load_workbook(root/'BLS_4_0_Daten_2025_DE.xlsx',read_only=True,data_only=True).worksheets[0]
 dictionary=openpyxl.load_workbook(root/'BLS_4_0_Components_DE_EN.xlsx',read_only=True,data_only=True).worksheets[0]
 components={r[1]:r for r in dictionary.iter_rows(min_row=2,values_only=True) if r[1]}
 headers=next(sheet.iter_rows(values_only=True));canonical={'ENERCC':'energy','PROT625':'protein','FAT':'fat','CHO':'carbohydrate','FIBT':'fibre','SUGAR':'sugars','SUGT':'sugars','NA':'sodium','CA':'calcium','FE':'iron','K':'potassium','FASAT':'saturatedFat','NACL':'salt'};records=[]
 for row in sheet.iter_rows(min_row=2,values_only=True):
  if not row[0]:continue
  code=str(row[0]);nutrients={}
  for i in range(3,len(headers),3):
   if not headers[i]:continue
   component=str(headers[i]).split()[0];meta=components.get(component);m=re.search(r'\[([^/]+)',str(headers[i]));unit=meta[4] if meta else m[1] if m else 'unknown';key=canonical.get(component,'bls:'+component)
   nutrients[key]={**numeric(row[i]),'unit':unit,'names':{'de':meta[2] if meta else str(headers[i]),'en':meta[3] if meta else component},'sourceComponent':component,'method':row[i+1] if i+1<len(row) else None,'reference':row[i+2] if i+2<len(row) else None}
   if meta and meta[7]:nutrients[key]['formula']=meta[7]
  records.append(wrap('germany-bls',code,'DE',{'foodName':row[1],'names':{'de':row[1],'en':row[2]},'identifiers':[{'system':'DE-BLS','value':code}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'source edible portion'},'nutrients':nutrients},'https://blsdb.de/download','CC BY 4.0','Max Rubner-Institut — Bundeslebensmittelschlüssel BLS 4.0 (2025)','2025'))
 return records

def cofid(root):
 w=openpyxl.load_workbook(root/'cofid2021.xlsx',read_only=True,data_only=True);foods={};canonical={'PROT':'protein','FAT':'fat','CHO':'carbohydrate','KCALS':'energy','TOTSUG':'sugars','AOACFIB':'fibre','SATFOD':'saturatedFat','NA':'sodium','K':'potassium','CA':'calcium','FE':'iron'}
 for name in ['1.3 Proximates','1.4 Inorganics','1.5 Vitamins']:
  rows=list(w[name].iter_rows(values_only=True));headers,codes,descriptions=rows[:3]
  for r in rows[3:]:
   if not r[0] or not r[1]:continue
   identity=(str(r[0]),r[1]);food=foods.setdefault(identity,{'foodName':r[1],'names':{'en':r[1]},'identifiers':[{'system':'UK-CoFID','value':str(r[0])}],'basis':{'amount':100,'unit':'ml' if str(r[3]).startswith('Q') else 'g','state':'as-described','note':'Alcoholic beverages per 100 ml; other foods per 100 g per CoFID notes.'},'description':r[2],'group':r[3],'references':r[5],'footnote':r[6],'nutrients':{}})
   for i in range(7,len(codes)):
    if not codes[i]:continue
    code=str(codes[i]);header=str(headers[i]);m=re.search(r'\(([^)]+)\)',header);unit=m[1] if m else 'unknown';nutrient={**numeric(r[i]),'unit':unit,'name':str(descriptions[i]),'sourceComponent':code,'method':'CoFID 2021; source definition'}
    if '/100g FA' in header or '/ 100g FA' in header or '/100gFA' in header:nutrient['basis']={'amount':100,'unit':'g-fatty-acids'}
    food['nutrients'][canonical.get(code,'cofid:'+code)]=nutrient
 result=[]
 for (code,name),food in foods.items():
  # Source contains a duplicated food code: retain both foods instead of overwriting either.
  stable=code+':'+hashlib.sha256(name.encode()).hexdigest()[:10]
  result.append(wrap('cofid',stable,'GB',food,'https://www.gov.uk/government/publications/composition-of-foods-integrated-dataset-cofid','Open Government Licence 3.0','Public Health England — McCance and Widdowson\'s CoFID 2021','2021'))
 return result

def sqltext(value):return "'"+str(value).replace("'","''")+"'"
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
 records=ciqual(args.directory)+bls(args.directory)+cofid(args.directory)
 assert len({r['id'] for r in records})==len(records)
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with args.output.open('w') as f:
  f.write('CREATE TABLE IF NOT EXISTS unified_records (owner TEXT NOT NULL,id TEXT NOT NULL,kind TEXT NOT NULL,source_id TEXT NOT NULL,countries TEXT NOT NULL,document TEXT NOT NULL,updated_at TEXT NOT NULL,search_text TEXT NOT NULL DEFAULT \'\',PRIMARY KEY(owner,id));\nCREATE INDEX IF NOT EXISTS unified_records_owner_kind ON unified_records(owner,kind);\n')
  for record in records:
   source=record['provenance']['sourceId'];document=json.dumps(record,ensure_ascii=False,separators=(',',':'));packed='gz:'+base64.b64encode(gzip.compress(document.encode(),mtime=0)).decode();search=' '.join(str(v) for v in record['data'].get('names',{}).values() if v);search=''.join(c for c in unicodedata.normalize('NFKD',search.casefold()) if not unicodedata.combining(c));values=['public:'+source,record['id'],record['kind'],source,json.dumps(record['countries']),packed,now,search]
   f.write('INSERT INTO unified_records(owner,id,kind,source_id,countries,document,updated_at,search_text) VALUES('+','.join(sqltext(v) for v in values)+') ON CONFLICT(owner,id) DO UPDATE SET document=excluded.document,countries=excluded.countries,updated_at=excluded.updated_at,search_text=excluded.search_text;\n')
 manifest={'counts':{s:sum(r['provenance']['sourceId']==s for r in records) for s in ['ciqual','germany-bls','cofid']},'records':len(records),'maxRecordBytes':max(len(json.dumps(r,ensure_ascii=False).encode()) for r in records),'sqlBytes':args.output.stat().st_size,'sqlMD5':hashlib.md5(args.output.read_bytes()).hexdigest()}
 args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
