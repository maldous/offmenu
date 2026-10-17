#!/usr/bin/env python3
"""Normalize complete named national releases locally; originals stay outside Git."""
import argparse,datetime,gzip,hashlib,importlib.util,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
national=module('national',ROOT/'scripts/import-national-tables.py')
afcd=module('afcd',ROOT/'scripts/import-afcd.py')

def ciqual(directory):
 p=directory/'Table Ciqual 2025_ENG_2025_11_03.xlsx';sheet=openpyxl.load_workbook(p,read_only=True,data_only=True).worksheets[0];headers=next(sheet.iter_rows(values_only=True))
 names={e.findtext('alim_code').strip():{c.tag:(c.text or '').strip() for c in e} for e in ET.parse(directory/'alim_2025_11_03.xml').getroot()}
 canonical={10:'energy',14:'protein',15:'proteinNx625',16:'carbohydrate',17:'fat',18:'sugars',26:'fibre',31:'saturatedFat',49:'salt',50:'calcium',53:'iron',58:'potassium',60:'sodium',72:'vitaminC'}
 rows=[]
 for r in sheet.iter_rows(min_row=2,values_only=True):
  if r[6] is None:continue
  code=str(r[6]);name=names[code];nutrients={}
  for i in range(9,len(headers)):
   if not headers[i]:continue
   h=' '.join(str(headers[i]).split());unit='µg' if 'µg' in h else 'mg' if re.search(r'\bmg\b',h) else 'kcal' if 'kcal' in h else 'kJ' if 'kJ' in h else 'g'
   nutrients[canonical.get(i,'ciqual:column:'+str(i+1))]={**national.numeric(r[i]),'unit':unit,'name':h,'sourceColumn':i+1,'method':'ANSES CIQUAL 2025; source definition'}
  rows.append(national.wrap('ciqual',code,'FR',{'foodName':name['alim_nom_fr'],'names':{'fr':name['alim_nom_fr'],'en':r[7]},'identifiers':[{'system':'ANSES-CIQUAL','value':code}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'source edible portion'},'nutrients':nutrients},'https://zenodo.org/records/17550133','Etalab Licence Ouverte 2.0','Anses. 2025. Ciqual French food composition table.','2025'))
 if len(rows)!=len(names):raise ValueError('CIQUAL workbook/XML identities do not reconcile')
 return rows

def norway(directory):
 foods=json.loads((directory/'en-foods.json').read_text())['foods'];nb={f['foodId']:f for f in json.loads((directory/'nb-foods.json').read_text())['foods']};definitions={r['nutrientId']:r for r in json.loads((directory/'en-nutrients.json').read_text())['nutrients']};sources={r['sourceId']:r for r in json.loads((directory/'en-sources.json').read_text())['sources']}
 canonical={'PROT':'protein','FAT':'fat','CHO':'carbohydrate','FIBT':'fibre','SUGAR':'sugars','NA':'sodium','CA':'calcium','FE':'iron','K':'potassium','FASAT':'saturatedFat','NACL':'salt','VITC':'vitaminC'};rows=[]
 if len(foods)!=len(nb):raise ValueError('Norway locales do not reconcile')
 for food in foods:
  key=food['foodId'];nutrients={}
  for n in food['constituents']:
   definition=definitions.get(n['nutrientId'],{'name':n['nutrientId'],'unit':'unknown'});component=definition.get('euroFirId') or n['nutrientId'];unit=n.get('unit',definition['unit']);source_id=n.get('sourceId')
   # Preserve unresolved source IDs rather than invent analytical authority.
   nutrients[canonical.get(component,'matvaretabellen:'+component)]={**national.numeric(n.get('quantity')),'unit':unit,'name':definition['name'],'sourceComponent':component,'reference':source_id,'method':'source-reported; see retained nutrient source metadata'}
  nutrients['energy']={**national.numeric(food['calories'].get('quantity')),'unit':'kcal','method':'source-reported','reference':food['calories'].get('sourceId')}
  nutrients['energyKJ']={**national.numeric(food['energy'].get('quantity')),'unit':'kJ','method':'source-reported','reference':food['energy'].get('sourceId')}
  rows.append(national.wrap('matvaretabellen',key,'NO',{'foodName':food['foodName'],'names':{'en':food['foodName'],'nb':nb[key]['foodName']},'identifiers':[{'system':'NO-Matvaretabellen','value':key}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'edible portion'},'nutrients':nutrients,'portions':food['portions'],'langualCodes':food['langualCodes']},food['uri'],'Mattilsynet API reuse: source attribution required; see https://www.matvaretabellen.no/api/','Mattilsynet — Matvaretabellen 2026','2026'))
 return rows

def frida(directory):
 workbook=openpyxl.load_workbook(directory/'Frida_5.5_Dataset.xlsx',read_only=True,data_only=True)
 foods={str(r[2]):r for r in workbook['Food'].iter_rows(min_row=2,values_only=True) if r[2] is not None};parameters={str(r[4]):r for r in workbook['Parameter'].iter_rows(min_row=2,values_only=True) if r[4] is not None};nutrients={k:{} for k in foods};seen=set();observations=0
 canonical={'137':'energyKJ','356':'energy','218':'protein','172':'carbohydrate','168':'fibre','141':'fat','327':'salt','47':'vitaminC','201':'sodium','165':'potassium','108':'calcium','162':'iron','245':'sugars','418':'freeSugars','248':'saturatedFat'}
 for r in workbook['Data_Normalised'].iter_rows(min_row=2,values_only=True):
  if r[0] is None:continue
  food_id,param=str(r[0]),str(r[3]);identity=(food_id,param)
  if identity in seen:raise ValueError('Duplicate Frida observation: '+str(identity))
  seen.add(identity);observations+=1;meta=parameters[param]
  unit=str(meta[9]).replace('ug','µg');amount=national.numeric(r[7]);key=canonical.get(param,'frida:parameter:'+param)
  nutrients[food_id][key]={**amount,'unit':unit,'name':meta[1],'sourceComponent':param,'definition':'Frida:'+param,'reference':str(r[12]),'method':'DTU Frida 5.5; source definition','sourceFood':r[13]}
  if meta[10]!='W':nutrients[food_id][key]['basis']={'amount':100,'unit':'source-matrix:'+str(meta[10])}
 rows=[]
 for key,food in foods.items():rows.append(national.wrap('frida',key,'DK',{'foodName':food[1],'names':{'da':food[0],'en':food[1]},'identifiers':[{'system':'DK-Frida','value':key}],'basis':{'amount':100,'unit':'g','state':'as-described','portion':'source edible portion'},'nutrients':nutrients[key]},'https://doi.org/10.11583/DTU.29500682','CC BY 4.0','National Food Institute, Technical University of Denmark — Frida 5.5','5.5'))
 print(json.dumps({'source':'frida','foodRows':len(foods),'parameterRows':len(parameters),'nutrientObservations':observations}),flush=True)
 return rows

def publish_local(source,rows,inputs,output,release):
 target=output/(source+'-'+release)
 if target.exists():raise ValueError('Immutable output exists: '+str(target))
 if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate normalized identity')
 target.mkdir(parents=True);digests=[]
 for p in sorted(inputs.rglob('*')):
  if p.is_file():digests.append({'key':str(p.relative_to(inputs)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 with gzip.open(target/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for row in rows:
   row['provenance']['releaseId']=release;row['provenance']['archiveSha256']=hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest();f.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n')
 manifest={'schemaVersion':'offmenu-collection/1','sourceId':source,'releaseId':release,'status':'normalized','normalizedRows':len(rows),'counts':{'raw':len(rows),'accepted':len(rows),'duplicates':0,'quarantined':0,'excluded':0,'records':len(rows)},'sourceFiles':digests,'archiveSha256':rows[0]['provenance']['archiveSha256'],'license':rows[0]['provenance']['license'],'attribution':rows[0]['provenance']['attribution'],'scope':'Complete named national food-composition release; all downloaded supporting files retained locally. Historical old-foods workbook is retained separately and not mixed into current CoFID.','publication':'local only','completedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'source':source,'records':len(rows),'directory':str(target)}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 for source,release,sub,fn in [('afcd','3','afcd',afcd.records),('ciqual','2025','ciqual',ciqual),('cofid','2021','cofid',national.cofid),('germany-bls','4.0','bls',lambda d:national.bls(d/'BLS_4_0_2025_DE')),('matvaretabellen','2026','norway',norway),('frida','5.5','frida',frida)]:
  target=a.output/(source+'-'+release)
  if target.exists():
   manifest=json.loads((target/'manifest.json').read_text());assert manifest['status']=='normalized'
   for item in manifest['sourceFiles']:
    original=a.originals/sub/item['key']
    if not original.exists() or hashlib.sha256(original.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Original release changed; choose a new output directory')
   print(json.dumps({'source':source,'resumed':True,'records':manifest['normalizedRows']}));continue
  publish_local(source,fn(a.originals/sub),a.originals/sub,a.output,release)
if __name__=='__main__':main()
