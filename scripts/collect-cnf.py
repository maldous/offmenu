#!/usr/bin/env python3
"""Collect the complete CNF 2015 relational release locally, preserving source values."""
import argparse,csv,datetime,gzip,hashlib,json,io,sqlite3
from pathlib import Path
MAP={'203':'protein','204':'fat','205':'carbohydrate','208':'energy','269':'sugars','291':'fibre','606':'saturatedFat','307':'sodium','301':'calcium','303':'iron','306':'potassium','401':'vitaminC'}
def collect(originals,output):
 if output.exists():raise ValueError('Immutable output exists')
 tables={};files=[];raw_total=0
 for p in sorted((originals/'csv').glob('*.csv')):
  raw=p.read_bytes()
  try:text=raw.decode('utf-8-sig');encoding='utf-8'
  except UnicodeDecodeError:text=raw.decode('cp1252');encoding='cp1252'
  rows=list(csv.reader(io.StringIO(text,newline='')));header=rows.pop(0)
  if any(len(r)!=len(header) for r in rows):raise ValueError('Malformed source row in '+p.name)
  tables[p.stem]=[dict(zip(header,row)) for row in rows];raw_total+=len(rows);files.append({'key':str(p.relative_to(originals)),'rows':len(rows),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'encoding':encoding})
 if len(tables)!=12:raise ValueError('All 12 source CSV tables required')
 foods={r['FoodID']:r for r in tables['FOOD NAME']};definitions={r['NutrientID']:r for r in tables['NUTRIENT NAME']};sources={r['NutrientSourceID'] for r in tables['NUTRIENT SOURCE']};nutrients={k:{} for k in foods};seen=set();unresolved=[]
 if len(foods)!=len(tables['FOOD NAME']):raise ValueError('Duplicate food ID')
 for r in tables['NUTRIENT AMOUNT']:
  food_id,nutrient_id=r['FoodID'],r['NutrientID'];identity=(food_id,nutrient_id)
  if identity in seen:raise ValueError('Duplicate nutrient observation')
  seen.add(identity);definition=definitions.get(nutrient_id)
  if definition is None:
   unresolved.append({'foodId':food_id,'nutrientId':nutrient_id,'reason':'Unresolved source NutrientID; not equated to NutrientCode'})
   definition={'NutrientCode':None,'NutrientUnit':'unknown','NutrientName':'Unresolved CNF nutrient '+nutrient_id,'NutrientNameF':''}
  if r['NutrientSourceID'] not in sources:raise ValueError('Unresolved nutrient source')
  unit=definition['NutrientUnit'];unit='kcal' if unit.lower()=='kcal' else 'µg' if unit in ['ug','mcg'] else unit
  value=float(r['NutrientValue']) if r['NutrientValue'] else None
  nutrients[food_id][MAP.get(definition['NutrientCode'],'cnf:'+nutrient_id)]={'value':value,'unit':unit,'qualifier':'source-reported' if value is not None else 'unknown','name':definition['NutrientName'],'names':{'en':definition['NutrientName'],'fr':definition['NutrientNameF']},'sourceComponent':nutrient_id,'method':'CNF 2015; source values unchanged','reference':r['NutrientSourceID'],'observationCount':r['NumberofObservations'],'standardError':r['StandardError'],'sourceDate':r['NutrientDateOfEntry']}
 output.mkdir(parents=True);now=datetime.datetime.now(datetime.timezone.utc).isoformat();sha=hashlib.sha256((originals/'cnf-2015-csv.zip').read_bytes()).hexdigest();country_counts={}
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for key,food in foods.items():
   row={'schemaVersion':'1.0','kind':'nutrientProfile','id':'cnf:nutrientProfile:'+key,'countries':['CA'],'provenance':{'sourceId':'cnf','recordId':key,'url':'https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/nutrient-data/canadian-nutrient-file-2015-download-files.html','license':'Health Canada CNF 2015 copyright guidelines: commercial and non-commercial use without further permission','licenseUrl':'https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/nutrient-data/canadian-nutrient-file-compilation-canadian-food-composition-data-users-guide.html#copyright','attribution':'Canadian Nutrient File, Health Canada, 2015','visibility':'public','fetchedAt':now,'sourceDate':'2015','releaseId':'2015','archiveSha256':sha,'transform':'offmenu-cnf/1','changes':'Relational source fields normalized; source nutrient values retained unchanged.','limitationStatement':'CNF provided as is; reference tool only, without Health Canada endorsement or warranty.'},'data':{'foodName':food['FoodDescription'],'names':{'en':food['FoodDescription'],'fr':food['FoodDescriptionF']},'identifiers':[{'system':'CA-CNF','value':key}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'edible portion'},'nutrients':nutrients[key],'foodGroupId':food['FoodGroupID'],'foodSourceId':food['FoodSourceID'],'scientificName':food['ScientificName']}}
   f.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n')
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':'cnf','releaseId':'2015','status':'normalized','normalizedRows':len(foods),'counts':{'raw':len(foods),'accepted':len(foods),'duplicates':0,'quarantined':0,'excluded':0,'records':len(foods)},'rawRelationalRows':raw_total,'nutrientObservations':len(seen),'unresolvedNutrientReferences':unresolved,'sourceFiles':files,'archiveSha256':sha,'scope':'All 12 CSV relational tables in the complete CNF 2015 archive. Every food and nutrient observation parsed; original files and supporting guides retained locally.','license':'Health Canada CNF 2015 copyright guidelines','attribution':'Canadian Nutrient File, Health Canada, 2015','publication':'local only','completedAt':now};(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'foodRows':len(foods),'rawRelationalRows':raw_total,'nutrientObservations':len(seen),'sourceTables':len(tables)}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.originals,a.output)
