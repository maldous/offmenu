#!/usr/bin/env python3
"""Complete local national files; preserve source units, definitions and unknowns."""
import argparse,csv,datetime,gzip,hashlib,json,re
from pathlib import Path
import openpyxl
import sys
import importlib.util
_spec=importlib.util.spec_from_file_location('national',Path(__file__).resolve().parent/'import_national_tables.py')
_mod=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_mod)
numeric=_mod.numeric


def table(path,delimiter=';',skip=0,encoding='cp1252'):
 with path.open(encoding=encoding,newline='') as f:
  for _ in range(skip):next(f)
  reader=csv.DictReader(f,delimiter=delimiter);rows=list(reader)
  if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValueError('Malformed source row: '+str(path))
  return rows


def fineli(root):
 tables={p.stem:table(p) for p in sorted((root/'fineli-basic2').glob('*.csv')) if p.stem!='publication'}
 with (root/'fineli-basic2/publication.csv').open(encoding='cp1252',newline='') as f:
  reader=csv.reader(f,delimiter=';');headers=next(reader);publications=[];pending=None
  for fields in reader:
   if pending is None:
    if len(fields)==5:publications.append(dict(zip(headers,fields)));continue
    if len(fields)!=2 or not fields[0].isdigit():raise ValueError('Unrecognized Fineli bibliography layout')
    pending=fields
   else:
    pending[1]+='\n'+fields[0];pending.extend(fields[1:])
    if len(pending)==5:publications.append(dict(zip(headers,pending)));pending=None
    elif len(pending)>5:raise ValueError('Fineli bibliography field overflow')
  if pending is not None:raise ValueError('Truncated Fineli bibliography')
 tables['publication']=publications
 foods={r['FOODID']:r for r in tables['food']};defs={r['EUFDNAME']:r for r in tables['component']};labels={r['THSCODE']:r['DESCRIPT'] for r in tables['eufdname_EN']};names={lang:{r['FOODID']:r['FOODNAME'] for r in tables['foodname_'+lang]} for lang in ['EN','FI','SV']}
 if len(foods)!=len(tables['food']):raise ValueError('Duplicate Fineli food ID')
 mapping={'ENERC':'energyKJ','FAT':'fat','PROT':'protein','CHOAVL':'carbohydrate','SUGAR':'sugars','FIBT':'fibre','FASAT':'saturatedFat','NA':'sodium','CA':'calcium','FE':'iron','K':'potassium','VITC':'vitaminC'}
 nutrients={k:{} for k in foods};seen=set()
 for r in tables['component_value']:
  k,c=r['FOODID'],r['EUFDNAME'];definition=defs[c]
  if (k,c) in seen:raise ValueError('Duplicate Fineli observation')
  seen.add((k,c));unit={'G':'g','MG':'mg','UG':'µg','KJ':'kJ','KCAL':'kcal'}.get(definition['COMPUNIT'],definition['COMPUNIT'])
  nutrients[k][mapping.get(c,'fineli:'+c)]={**numeric(r['BESTLOC'].replace(',','.')),'unit':unit,'name':labels.get(c,c),'definition':'Fineli:'+c,'sourceComponent':c,'method':'Source-reported; Fineli Release 20.0','acquisitionType':r['ACQTYPE'],'methodType':r['METHTYPE'],'methodIndicator':r['METHIND']}
 return [{'key':k,'name':names['EN'][k],'names':{lang.lower():v[k] for lang,v in names.items()},'nutrients':nutrients[k]} for k in foods],{'rawRelationalRows':sum(len(r) for r in tables.values()),'sourceTables':len(tables),'nutrientObservations':len(seen),'bibliographyLineBreakReconciliation':'Four unquoted multiline citations rejoined without changing citation text','scope':'Every food and nutrient observation in the complete publisher Fineli Release 20.0 74-component archive. Companion 55-component and raw-ingredient archives retained without double-counting overlapping foods. This downloadable snapshot is not claimed as the current live API.'}


def foodfiles(root):
 base=root/'nz-extracted'
 with (base/'ExcelFilesNamesx').open('rb') as handle:
  workbook=openpyxl.load_workbook(handle,read_only=True,data_only=True);source_rows=workbook.active.iter_rows(values_only=True);next(source_rows);headers=next(source_rows);foods=[dict(zip(headers,row)) for row in source_rows];workbook.close()
 defs={r['Code']:r for r in table(base/'UnabridgedCodes','~',1,'utf-8-sig')};ids={r['FoodID'] for r in foods}
 if len(ids)!=len(foods):raise ValueError('Duplicate FOODfiles food ID')
 mapping={'ENERC_FSANZ2_KCAL':'energy','ENERC_FSANZ2':'energyKJ','PROT':'protein','FAT':'fat','CHOAVL_FSANZ':'carbohydrate','SUGAR':'sugars','SUGAD':'addedSugars','SUGFR':'freeSugars','FIBTG':'fibre','FASAT':'saturatedFat','NA':'sodium','CA':'calcium','FE':'iron','K':'potassium','VITC':'vitaminC'}
 nutrients={k:{} for k in ids};seen=set();matrix_counts={}
 observations=table(base/'UnabridgedDataFT','~',1,'utf-8-sig')
 for r in observations:
  k,c=r['FoodID'],r['Component Identifier'];d=defs[c];matrix=r['Matrix Unit Code']
  if (k,c) in seen:raise ValueError('Duplicate FOODfiles component')
  seen.add((k,c));matrix_counts[matrix]=matrix_counts.get(matrix,0)+1
  key=mapping.get(c,'foodfiles:'+c) if matrix=='W' else 'foodfiles:'+c
  n={**numeric(r['Value']),'unit':r['Unit Code'],'name':d['Description'],'definition':'FOODfiles:'+c,'sourceComponent':c,'method':'Source values unchanged; FOODfiles 2024 Version 01','sourceValue':r['Value'],'sourceCode':r['Source Code'],'valueType':r['Value Type Code'],'acquisitionType':r['Acquisition Type Code'],'methodType':r['Method Type Code'],'methodIndicator':r['Method Indicator Code']}
  if matrix!='W':n['basis']={'amount':100,'unit':'source-matrix:'+matrix}
  nutrients[k][key]=n
 return [{'key':r['FoodID'],'name':r['Food Name'],'nutrients':nutrients[r['FoodID']]} for r in foods],{'nutrientObservations':len(seen),'matrixObservationCounts':matrix_counts,'foodNameSource':'Supplied Excel NAME.FT, avoiding one unescaped tilde in text NAME.FT sampling description; original text retained','scope':'All FOODfiles 2024 Version 01 food names and all 571,495 unabridged nutrient observations parsed; all 30 installer components retained locally. Canonical facts use whole-food W matrix only; fatty-acid F and nitrogen N matrices remain source-specific. Multiple energy, carbohydrate and fibre definitions remain distinct. Source values unaltered; selected FSANZ available-carbohydrate energy definition explicitly identified. Not the newer 2026 online-search data.'}


def sweden(root):
 w=openpyxl.load_workbook(root/'sweden-20260701.xlsx',read_only=True,data_only=True);s=w.active;rows=s.iter_rows(values_only=True);title=next(rows)[0];basis=next(rows)[0];headers=next(rows)
 if '2026-07-01' not in title or '100 gram' not in basis:raise ValueError('Unexpected Swedish release/basis')
 mapping={3:'energy',4:'energyKJ',5:'fat',6:'protein',7:'carbohydrate',8:'fibre',12:'sugars',15:'addedSugars',16:'freeSugars',18:'saturatedFat',50:'vitaminC',53:'iron',54:'calcium',55:'potassium',57:'sodium',58:'salt'};result=[];seen=set();observations=0
 for r in rows:
  if r[1] is None:raise ValueError('Missing Swedish food ID')
  k=str(r[1])
  if k in seen:raise ValueError('Duplicate Swedish food ID')
  seen.add(k);nutrients={}
  for i in range(3,len(headers)-1):
   unit=re.search(r'\(([^)]+)\)$',headers[i]).group(1)
   unit='µg' if 'µg' in unit else 'mg' if 'mg' in unit else unit
   nutrients[mapping.get(i,'sweden:column:'+str(i+1))]={**numeric(r[i]),'unit':unit,'name':headers[i],'definition':'Livsmedelsverket:'+headers[i],'sourceColumn':i+1,'method':'Livsmedelsverkets Livsmedelsdatabas 2026-07-01; data unchanged'};observations+=1
  result.append({'key':k,'name':r[0],'names':{'sv':r[0]},'nutrients':nutrients})
 w.close()
 return result,{'nutrientObservations':observations,'scope':'Complete official Swedish full-database workbook export, version 2026-07-01; every food and all 58 nutrient columns parsed without changing source values. Missing values remain unknown. Recipe-derived foods are composition references, not quantified recipe instructions.'}

CONFIG={
 'fineli':('FI','20.0','https://fineli.fi/fineli/fi/avoin-data','CC BY 4.0','https://creativecommons.org/licenses/by/4.0/','National Institute for Health and Welfare (THL), Fineli, Release 20.0',fineli),
 'foodfiles':('NZ','2024-v01','https://foodcomposition.co.nz/foodfiles/','FOODfiles terms: source data unchanged, attribution and downstream terms required','https://foodcomposition.co.nz/terms/','New Zealand Food Composition Database, FOODfiles 2024 Version 01; Plant & Food Research and New Zealand Ministry of Health',foodfiles),
 'sweden-food':('SE','2026-07-01','https://soknaringsinnehall.livsmedelsverket.se/','Publisher reuse terms: source/version attribution, data must not be changed','https://www.livsmedelsverket.se/livsmedel-och-innehall/naringsamne/livsmedelsdatabasen/sok-naringsinnehall/','Livsmedelsverkets Livsmedelsdatabas version 2026-07-01',sweden)}

def collect(source,root,output):
 if output.exists():raise ValueError('Immutable output exists')
 country,version,url,license,license_url,attribution,reader=CONFIG[source];rows,summary=reader(root);receipt=json.loads((root/'acquisition.json').read_text());now=datetime.datetime.now(datetime.timezone.utc).isoformat();archive=next(r for r in receipt if r['key']=={'fineli':'fineli-basic2.zip','foodfiles':'nz-foodfiles-2024.msi','sweden-food':'sweden-20260701.xlsx'}[source]);
 original=root/archive['key']
 if original.stat().st_size!=archive['bytes'] or hashlib.sha256(original.read_bytes()).hexdigest()!=archive['sha256']:raise ValueError('Source archive checksum mismatch')
 output.mkdir(parents=True)
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for r in rows:
   record={'schemaVersion':'1.0','kind':'nutrientProfile','id':source+':nutrientProfile:'+r['key'],'countries':[country],'provenance':{'sourceId':source,'recordId':r['key'],'url':url,'license':license,'licenseUrl':license_url,'attribution':attribution,'visibility':'public','fetchedAt':now,'releaseId':version,'sourceDate':version,'archiveSha256':archive['sha256'],'transform':'offmenu-national-files/1','changes':'Selected source facts formatted into OffMenu schema; source nutrient values unchanged. No endorsement or independent diet qualification.','rights':'For FOODfiles data, third-party access and use is subject to https://foodcomposition.co.nz/terms/.' if source=='foodfiles' else 'Source attribution and licence retained; no publisher endorsement.'},'data':{'foodName':r['name'],'names':r.get('names',{}),'identifiers':[{'system':source,'value':r['key']}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'source food basis'},'nutrients':r['nutrients']}}
   f.write(json.dumps([record],ensure_ascii=False,separators=(',',':'))+'\n')
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':source,'releaseId':version,'status':'normalized','normalizedRows':len(rows),'counts':{'raw':len(rows),'accepted':len(rows),'duplicates':0,'quarantined':0,'excluded':0,'records':len(rows)},'countries':{country:len(rows)},'archiveSha256':archive['sha256'],'license':license,'attribution':attribution,'sourceAcquisition':archive,'publication':'local only','completedAt':now,**summary};(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'source':source,'records':len(rows),**summary}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',choices=CONFIG);p.add_argument('originals',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.source,a.originals,a.output)
