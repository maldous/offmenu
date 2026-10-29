#!/usr/bin/env python3
"""Normalize the complete corrected Japanese main composition table locally.

Companion amino-acid/fat/carbohydrate files remain complete original workbooks;
their special denominator tables are not silently treated as per-100g foods.
"""
import argparse,datetime,gzip,hashlib,json,math,re
from pathlib import Path
import openpyxl
MAP={'ENERC_KCAL':'energy','ENERC':'energyKJ','PROT-':'protein','FAT-':'fat','CHOAVL':'carbohydrate','FIB-':'fibre','NA':'sodium','K':'potassium','CA':'calcium','FE':'iron','VITC':'vitaminC','NACL_EQ':'salt'}
def unit(column):
 if column==5:return 'kJ'
 if column==6:return 'kcal'
 if column==11 or 23<=column<=31 or 44<=column<=47 or 49<=column<=53 or column in [56,58]:return 'mg'
 if 33<=column<=43 or column in [48,54,55,57]:return 'µg'
 return 'g'
def numeric(value):
 if value is None or str(value).strip() in ['', '-','—']:return {'value':None,'qualifier':'unknown'}
 s=str(value).strip()
 if s.lower()=='tr':return {'value':None,'qualifier':'trace'}
 if s.startswith('(') and s.endswith(')'):return {'value':None,'qualifier':'source-parenthesized','originalText':s}
 try:
  n=float(s)
  if not math.isfinite(n) or n<0:raise ValueError('Invalid nutrient number')
  return {'value':n,'qualifier':'source-reported'}
 except ValueError:return {'value':None,'qualifier':'source-text','originalText':s}
def collect(originals,output):
 if output.exists():raise ValueError('Immutable output exists')
 main=originals/'20260327-mxt_kagsei-mext-000029402_02.xlsx';sheet=openpyxl.load_workbook(main,read_only=True,data_only=True).worksheets[0];head=list(sheet.iter_rows(max_row=12,values_only=True));components=head[11]
 if components[6]!='ENERC_KCAL' or components[9]!='PROT-' or components[58]!='VITC':raise ValueError('MEXT schema changed; review mappings')
 rows=[];seen=set();now=datetime.datetime.now(datetime.timezone.utc).isoformat();sha=hashlib.sha256(main.read_bytes()).hexdigest()
 for r in sheet.iter_rows(min_row=13,values_only=True):
  key=str(r[1])
  if not re.fullmatch(r'\d{5}',key):continue
  if not r[3] or key in seen:raise ValueError('Missing/duplicate MEXT food identity')
  seen.add(key);nutrients={}
  for col,component in enumerate(components):
   if col<5 or not component:continue
   component=str(component).strip();name=' / '.join(dict.fromkeys(str(h[col]).strip() for h in head[2:5] if h[col] is not None))
   nutrients[MAP.get(component,'mext:'+component)]={**numeric(r[col]),'unit':unit(col),'name':name,'sourceComponent':component,'sourceColumn':col+1,'definition':'MEXT-2023:'+component,'method':'source-derived sodium chloride equivalent' if component=='NACL_EQ' else 'MEXT source table; original preparation state and qualifier retained'}
  rows.append({'schemaVersion':'1.0','kind':'nutrientProfile','id':'mext:nutrientProfile:'+key,'countries':['JP'],'provenance':{'sourceId':'mext','recordId':key,'url':'https://www.mext.go.jp/a_menu/syokuhinseibun/mext_00001.html','license':'MEXT website content use rules, revised 2026-08-17; attribution and modification notice required','licenseUrl':'https://www.mext.go.jp/b_menu/1351168.htm','attribution':'Ministry of Education, Culture, Sports, Science and Technology, Japan — Standard Tables 2023, corrected 27 March 2026','visibility':'public','fetchedAt':now,'sourceDate':'2026-03-27','releaseId':'2023-corrected-20260327-main','archiveSha256':sha,'transform':'offmenu-mext/1','changes':'Main workbook normalized to source-qualified per-100g records; parenthesized values remain unresolved, source qualifiers retained.','countryNotice':'Japanese national composition reference; source food names and preparation states retained.'},'data':{'foodName':r[3],'names':{'ja':r[3]},'identifiers':[{'system':'JP-MEXT','value':key}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'edible portion'},'nutrients':nutrients,'foodGroup':r[0],'sourceIndex':r[2]}})
 output.mkdir(parents=True)
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for row in rows:f.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n')
 files=[{'key':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(originals.iterdir()) if p.is_file()]
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':'mext','releaseId':'2023-corrected-20260327-main','status':'normalized','normalizedRows':len(rows),'counts':{'raw':len(rows),'accepted':len(rows),'duplicates':0,'quarantined':0,'excluded':0,'records':len(rows)},'sourceFiles':files,'archiveSha256':sha,'scope':'Every food row and component in the complete main composition table, corrected 27 March 2026. All 17 publisher release files retained; special-denominator companion tables remain original files, outside this per-100g projection. Parenthesized values remain unresolved.','license':'MEXT website content use rules','attribution':'Ministry of Education, Culture, Sports, Science and Technology, Japan','publication':'local only','completedAt':now};(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'foodRows':len(rows),'sourceFiles':len(files),'release':manifest['releaseId']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.originals,a.output)
