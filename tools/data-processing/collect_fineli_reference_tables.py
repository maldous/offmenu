#!/usr/bin/env python3
"""Retain complete Finnish recipe formulae and diet tags as unreviewed local records."""
import argparse,collections,datetime,gzip,hashlib,importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('national_files',Path(__file__).with_name('collect_next_national.py'));national=importlib.util.module_from_spec(spec);spec.loader.exec_module(national)
def collect(root,output):
 if output.exists():raise ValueError('Immutable output exists')
 base=root/'fineli-basic2';names={r['FOODID']:r['FOODNAME'] for r in national.table(base/'foodname_EN.csv')};labels={r['THSCODE']:r['DESCRIPT'] for r in national.table(base/'specdiet_EN.csv')};formulae=national.table(base/'contribfood.csv');tags=national.table(base/'specdiet.csv');groups=collections.defaultdict(list)
 for row in formulae:groups[row['FOODID']].append(row)
 receipt=next(r for r in json.loads((root/'acquisition.json').read_text()) if r['key']=='fineli-basic2.zip');now=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[];seen=set();unresolved=set()
 def record(kind,key,data):return {'schemaVersion':'1.0','kind':kind,'id':'fineli:'+kind+':'+key,'countries':['FI'],'provenance':{'sourceId':'fineli','recordId':key,'url':'https://fineli.fi/fineli/fi/avoin-data','license':'CC BY 4.0','licenseUrl':'https://creativecommons.org/licenses/by/4.0/','attribution':'National Institute for Health and Welfare (THL), Fineli Release 20.0','visibility':'public','sourceDate':'20.0','releaseId':'20.0-reference-tables','archiveSha256':receipt['sha256'],'fetchedAt':now,'transform':'offmenu-fineli-references/1','changes':'Source formula fields and diet labels retained as unreviewed references; no dietary qualification or automatic planning.'},'data':data}
 for food,components in groups.items():
  if food not in names:raise ValueError('Unresolved formula identity')
  ingredients=[]
  for c in components:
   ingredient=c['CONFDID']
   if ingredient not in names:unresolved.add(ingredient)
   ingredients.append({'name':names.get(ingredient,'Unresolved Fineli ingredient '+ingredient),'sourceFoodId':ingredient,'foodMatchStatus':'unreviewed','amount':national.numeric(c['MASS'].replace(',','.'))['value'],'unit':'g','quantityMethod':'Source formula ingredient mass, not independently verified preparation or serving quantity','sourceFields':c})
  rows.append(record('recipe',food,{'name':names[food],'yield':{'value':None,'unit':'portion'},'ingredients':ingredients,'directions':[],'automaticPlanningEligible':False,'reviewStatus':'source-formula-needs-quantity-and-cooking-review','limitations':'Source recipe composition calculation; serving yield, ingredient identity and evaporation/cooking factors require review.'}))
 for tag in tags:
  food,code=tag['FOODID'],tag['SPECDIET'];key=food+':'+code
  if key in seen:raise ValueError('Duplicate source dietary flag')
  seen.add(key)
  if food not in names or code not in labels:raise ValueError('Unresolved dietary flag reference')
  rows.append(record('sourceAssertion',key,{'name':names[food]+' — '+labels[code],'predicate':'source-diet-tag','value':code,'sourceLabel':labels[code],'sourceFoodId':food,'reviewStatus':'unreviewed-source-assertion','qualificationStatus':'unknown','automaticDietQualification':False,'sourceFields':tag}))
 output.mkdir(parents=True)
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for row in rows:f.write(json.dumps([row],ensure_ascii=False,separators=(',',':'))+'\n')
 m={'schemaVersion':'offmenu-collection/1','sourceId':'fineli','releaseId':'20.0-reference-tables','status':'normalized','normalizedRows':len(rows),'counts':{'raw':len(rows),'accepted':len(rows),'duplicates':0,'quarantined':0,'records':len(rows)},'sourceFormulaComponentRows':len(formulae),'recipeFormulae':len(groups),'sourceDietaryFlags':len(tags),'unresolvedIngredientSourceIds':sorted(unresolved),'scope':'All recipe component and dietary-flag rows in the complete Fineli Release 20.0 archive. Formula rows grouped by source food ID; source amounts and cooking-factor fields retained without treating them as independently quantified recipes. Diet labels remain source assertions, not verified qualifications.','license':'CC BY 4.0','attribution':'THL Fineli Release 20.0','archiveSha256':receipt['sha256'],'publication':'local only; separate unreviewed reference tables, not part of hosted curation','completedAt':now};(output/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('originals',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.originals,a.output)
