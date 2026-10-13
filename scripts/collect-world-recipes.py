#!/usr/bin/env python3
"""Normalize licensed recipe contents; archives stay local, source rights stay attached."""
import argparse,collections,datetime,gzip,hashlib,json,re,urllib.parse
from pathlib import Path
import mwparserfromhell
from recipe_format import ingredient,sections,text,number,norm,ALIASES,ING_HEAD,DIR_HEAD
SOURCE='world-recipes';RELEASE='world-recipes-20261014'
def attach_licenses(research, output, manifest):
 documents=[]
 for repo, filename, url in [('farcrak--unitools-recipes','CC-BY-SA-4.0.txt','https://creativecommons.org/licenses/by-sa/4.0/legalcode'),('recipecommons--openrecipe-spec','CC0-1.0.txt','https://creativecommons.org/publicdomain/zero/1.0/legalcode'),('Anduin2017--HowToCook','Unlicense.txt','https://unlicense.org/')]:
  body=(research/repo/'LICENSE').read_bytes();(output/'licenses').mkdir(exist_ok=True);(output/'licenses'/filename).write_bytes(body)
  documents.append({'key':filename,'sha256':hashlib.sha256(body).hexdigest(),'sourceUrl':url})
 manifest['licenseDocuments']=documents

def collect(research,wikis,english,output):
 if output.exists():raise ValueError('Immutable output exists')
 rows=[];decisions=[];source_counts=collections.Counter();input_count=0;seen=set();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def add(publisher,key,title,body,language,license,license_url,url,credit,countries=None,extra=None,parsed=None):
  nonlocal input_count
  input_count+=1
  if (publisher,key) in seen:decisions.append({'source':publisher,'key':key,'reason':'duplicate-source-identity'});return
  seen.add((publisher,key));
  if not publisher.startswith('wikibooks:') and len(re.findall(r'^#\s+',body,re.M))>1:
   decisions.append({'source':publisher,'key':key,'reason':'multiple-source-recipes-require-boundary-review'});return
  headings=[norm(m[1]) for m in re.finditer(r'^\s*==+\s*(.*?)\s*==+\s*$',body,re.M)] if publisher.startswith('wikibooks:') else [norm(m[1]) for m in re.finditer(r'^\s*#{2,6}\s+(.+?)\s*$',body,re.M)]
  if parsed is None and sum(any(norm(x) in h for x in ING_HEAD) for h in headings)>1 and sum(any(norm(x) in h for x in DIR_HEAD) for h in headings)>1:
   decisions.append({'source':publisher,'key':key,'reason':'multiple-source-recipes-require-boundary-review'});return
  if publisher.startswith('wikibooks:') and re.search(r'(?:template|sjabloon|sablon|vorlage|modèle|modello|шаблон|テンプレート|תבנית|قالب)',title,re.I):
   decisions.append({'source':publisher,'key':key,'reason':'recipe-template-not-a-dish'});return
  ingredients,directions,yield_value=parsed or sections(body,publisher.startswith('wikibooks:'))
  if publisher.startswith('wikibooks:') and (not any(i['sourceQuantity'].get('value') is not None or i['sourceQuantity'].get('range') or i['ingredientId'] or any(c.isdecimal() for c in i['originalText']) for i in ingredients) or len(' '.join(directions))<30):
   decisions.append({'source':publisher,'key':key,'reason':'non-recipe-navigation-or-insufficient-food-and-procedure-evidence'});return
  if not title or not ingredients or not directions:
   decisions.append({'source':publisher,'key':key,'reason':'not-an-extractable-recipe-with-ingredients-and-directions'});return
  if re.search(r'arsenic|strychnine|mercuric|lead acetate|kill rats|boot polish|furniture polish|砒霜',title+' '+str(ingredients),re.I):decisions.append({'source':publisher,'key':key,'reason':'non-culinary-or-toxic-formula'});return
  id=SOURCE+':recipe:'+hashlib.sha256((publisher+'\0'+key).encode()).hexdigest()[:24]
  data={'recipeSchema':'offmenu-recipe/1','name':title,'languages':[language] if isinstance(language,str) else language,'yield':{'value':yield_value,'unit':'portion'},'ingredients':ingredients,'directions':directions,'automaticPlanningEligible':False,'reviewStatus':'source-recipe-needs-personal-quantity-and-food-review','qualificationStatus':'unknown','quantityCoverage':{'ingredients':len(ingredients),'standardQuantities':sum(i['amount'] is not None for i in ingredients),'sourceNumericQuantities':sum(i['sourceQuantity'].get('value') is not None for i in ingredients)},'sourcePublisher':publisher,'limitations':'Source recipe retained with attribution; unknown servings, alternative ingredients and nonstandard measures require review. Pantry matches do not establish diet qualification or food identity.'}
  p={'sourceId':SOURCE,'originSourceId':publisher,'recordId':key,'url':url,'license':license,'licenseUrl':license_url,'attribution':credit,'visibility':'public','fetchedAt':now,'releaseId':RELEASE,'transform':'offmenu-recipe-normalizer/1','originalContentSha256':hashlib.sha256(body.encode()).hexdigest(),'changes':'Recipe sections extracted; quantities parsed conservatively; original ingredient wording and source units retained; media and unrelated prose omitted.','recipeReuse':'licensed-full-recipe-content','sourceDate':None}
  if extra:
   data.update(extra.get('data',{}));p.update(extra.get('provenance',{}))
  rows.append({'schemaVersion':'1.0','kind':'recipe','id':id,'countries':countries or [],'provenance':p,'data':data});source_counts[publisher]+=1
 # English collection was already acquired with complete category continuation.
 for file in sorted((english/'originals').glob('revisions-*.json')):
  for page in json.loads(file.read_text()):
   if not page.get('revisions'):continue
   rev=page['revisions'][0];url='https://en.wikibooks.org/wiki/'+urllib.parse.quote(page['title'].replace(' ','_'),safe=':/');add('wikibooks:en',str(page['pageid']),page['title'].removeprefix('Cookbook:'),rev['slots']['main']['content'],'en','CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/',url,'English Wikibooks contributors',extra={'provenance':{'revisionId':rev['revid'],'historyUrl':url+'?action=history','sourceDate':rev['timestamp'],'rightsEvidenceUrl':'https://en.wikibooks.org/wiki/Wikibooks:Copyrights'}})
 for directory in sorted(wikis.iterdir()):
  if not directory.is_dir() or not (directory/'acquisition.json').exists():continue
  acquisition=json.loads((directory/'acquisition.json').read_text());language=directory.name
  if acquisition['status']!='complete':continue
  pages={}
  for file in sorted(list(directory.glob('revisions-*.json'))+list(directory.glob('linked-revisions-*.json'))):
   for page in json.loads(file.read_text()).get('query',{}).get('pages',[]):pages[page['pageid']]=page
  for page in pages.values():
   if not page.get('revisions'):continue
   if page['title']==acquisition.get('root'):input_count+=1;decisions.append({'source':'wikibooks:'+language,'key':str(page['pageid']),'reason':'cookbook-navigation-root'});continue
   rev=page['revisions'][0];body=rev['slots']['main']['content'];url='https://'+language+'.wikibooks.org/wiki/'+urllib.parse.quote(page['title'].replace(' ','_'),safe=':/');add('wikibooks:'+language,str(page['pageid']),page['title'].split('/')[-1],body,language,'CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/',url,language+' Wikibooks contributors',extra={'provenance':{'revisionId':rev['revid'],'historyUrl':url+'?action=history','sourceDate':rev['timestamp'],'rightsEvidenceUrl':acquisition['rights']['url']}})
 # First-party, structured bilingual recipe release; no photos or dietary/nutrition claims promoted.
 dataset=json.loads((research/'unitools.json').read_text())
 for recipe in dataset['recipes']:
  ingredients=[]
  for original in recipe['ingredients']:
   raw=str(original['quantity'])+' '+original['unit']+' '+original['name']['en'] if original['quantity'] is not None else original['name']['en'];item=ingredient(raw);item.update(name=original['name']['en'],names=original['name'],ingredientId=original['id'] if original['id'] in ALIASES else next((k for k,v in ALIASES.items() if norm(original['name']['en']) in [norm(x) for x in v]),None),sourceIngredientId=original['id'],scaling=original['scaling'],notes=original.get('note'))
   if original['quantity'] is None:item['amount']=None;item['unit']=None
   ingredients.append(item)
  directions=[s['text']['en'] for s in recipe['steps']];add('unitools',recipe['slug'],recipe['name']['en'],json.dumps(recipe,ensure_ascii=False),['en','ru'],'CC BY-SA 4.0',dataset['licenseUrl'],dataset.get('landingPage') or dataset['homepage'],dataset['attribution'],[recipe['country']],extra={'data':{'names':recipe['name'],'nativeName':recipe.get('nativeName'),'directionsByLanguage':{lang:[s['text'][lang] for s in recipe['steps']] for lang in ['en','ru']},'time':{'prepMinutes':recipe['prepMinutes'],'cookMinutes':recipe['cookMinutes']},'sourceCuisineCountry':recipe['country']},'provenance':{'sourceDate':dataset['generatedAt'],'rightsEvidenceUrl':'https://github.com/farcrak/unitools-recipes/blob/main/LICENSE'}},parsed=(ingredients,directions,recipe['baseServings']))
 for repo,language,license in [('Anduin2017/HowToCook','zh','Unlicense'),('LukeSmithxyz/based.cooking','en','Unlicense'),('sinker/tacofancy','en','Unlicense'),('recipecommons/openrecipe-spec','en','CC0-1.0')]:
  directory=research/repo.replace('/','--');m=json.loads((directory/'metadata.json').read_text());files=json.loads((directory/'content-files.json').read_text())
  for file in files:
   body=(directory/'content-originals'/file).read_text();title=next((text(re.sub(r'^#\s*','',line)) for line in body.splitlines() if re.match(r'^#\s+',line)),None)
   if not title:
    match=re.search(r'^title:\s*[\"\']?(.*?)[\"\']?\s*$',body,re.M);title=match[1] if match else Path(file).stem.replace('-',' ')
   add(repo,file,title,body,language,license,'https://unlicense.org/' if license=='Unlicense' else 'https://creativecommons.org/publicdomain/zero/1.0/','https://github.com/'+repo+'/blob/'+m['commit']+'/'+urllib.parse.quote(file),repo+' contributors',extra={'provenance':{'sourceRevision':m['commit'],'rightsEvidenceUrl':'https://github.com/'+repo+'/blob/'+m['commit']+'/LICENSE'+('.md' if (directory/'LICENSE.md').exists() else '')}})
 # Historical adaptations: original authors/translators must have verified old death dates;
 # the archive's own modifications are dedicated under its repository licence.
 books={str(b['id']):b for b in json.loads((research/'gutenberg-recipe-book-metadata.json').read_text())['results']};archive=research/'AdamBouhmad--open-recipe-archive';archive_meta=json.loads((archive/'metadata.json').read_text())
 for file in sorted(archive.glob('collections/*/recipes.jsonl')):
  for line in file.open():
   recipe=json.loads(line);match=re.search(r'gutenberg.org/ebooks/(\d+)',recipe.get('source_url',''));book=books.get(match[1]) if match else None;people=(book['authors']+book['translators']) if book else []
   eligible=book and book['copyright'] is False and people and all(p['death_year'] is not None and p['death_year']<=1925 for p in people) and recipe['source_year'].isdigit() and int(recipe['source_year'])<1900
   if not eligible:input_count+=1;decisions.append({'source':'historical-archive','key':recipe.get('slug'),'reason':'underlying-work-or-global-rights-not-yet-cleared'});continue
   add('historical-archive',recipe['collection']+'/'+recipe['slug'],recipe['title'],recipe['body'],'en','Unlicense adaptation; original work public domain','https://unlicense.org/',recipe['source_url'],recipe.get('author','')+'; Open Recipe Archive contributors',extra={'data':{'historical':True,'sourceBook':recipe['source_title'],'sourcePublicationYear':recipe['source_year'],'sourceCulture':recipe['culture'],'sourceOriginalLanguages':book['languages']},'provenance':{'sourceRevision':archive_meta['commit'],'rightsEvidenceUrl':'https://github.com/AdamBouhmad/open-recipe-archive/blob/'+archive_meta['commit']+'/LICENSE.md','originalAuthors':people,'rightsScope':'Original identified pre-1900 work with author/translator deaths no later than 1925; archive adaptation under its declared Unlicense. Metadata corroborated against the Gutenberg catalogue; not a blanket worldwide clearance of other historical works.'}})
 # Smithsonian provides explicit CC0 statements for selected original archived works.
 for acquisition_file in sorted((research/'smithsonian').glob('*/acquisition.json')):
  acquisition=json.loads(acquisition_file.read_text())
  if not acquisition.get('cc0') or not re.search(r'cook|baker|kochbuch|hausfrau|housewife|recipes for cooking',acquisition['title'],re.I):continue
  language='de' if str(acquisition.get('language','')).lower() in ['ger','german','de'] else 'en'
  for document in acquisition['files']:
   raw=(acquisition_file.parent/document['key']).read_text(errors='strict')
   blocks=re.split(r'\n\s*\n+',raw);headings=[]
   for index,block in enumerate(blocks):
    clean=text(block);words=re.findall(r'[A-Za-zÀ-ž]+',clean)
    if 1<len(words)<14 and len(clean)<100 and all(w[0].isupper() or w.lower() in ['of','the','and','to','a','or','mit','und','de','la','von'] for w in words) and not re.search(r'\b(contents|index|copyright|illustration|library|preface|introduction)\b',clean,re.I):headings.append(index)
   for pos,start in enumerate(headings):
    end=headings[pos+1] if pos+1<len(headings) else len(blocks);body='\n'.join(blocks[start+1:end]);title=text(blocks[start])
    if not 80<len(body)<12000 or not re.search(r'\b(cook|bake|boil|mix|stir|beat|pour|simmer|knead|backen|kochen|ruhren)\b',norm(body)):continue
    ingredients=[];seen_formula=set()
    # Only explicit numeric measure + named food spans; never invent quantities from prose.
    pattern=r'(\d+(?:[.,]\d+)?(?:/\d+)?(?:\s+\d+/\d+)?)\s*(grams?|grammes?|kg|g|ml|litres?|oz\.?|ounces?|lbs?\.?|pounds?|cups?|teaspoons?|tablespoons?|pfund)\s+(?:of\s+)?([A-Za-zÀ-ž][^.;,\n]{0,80})'
    for match in re.finditer(pattern,body,re.I):
     tail=match[3];food=None
     for key,aliases in ALIASES.items():
      for alias in aliases:
       if norm(tail)==norm(alias) or norm(tail).startswith(norm(alias)+' '):
        if food is None or len(alias)>len(food[1]):food=(key,alias)
     if food:
      line=match[1]+' '+match[2]+' '+food[1];item=ingredient(line)
      if line in seen_formula:continue
      seen_formula.add(line);ingredients.append(item)
    if not ingredients:continue
    add('smithsonian-archive',acquisition['archiveId']+':'+str(start),title,body,language,'CC0-1.0','https://creativecommons.org/publicdomain/zero/1.0/',acquisition['archiveLinks'][0],acquisition['title']+'; Smithsonian Libraries and Archives',extra={'data':{'historical':True,'sourceBook':acquisition['title'],'ingredientExtractionComplete':False,'sourceExtraction':'Uncorrected OCR; named culinary heading and explicit ingredient measures; partial ingredient extraction, complete transcription required','sourceParagraphRange':[start,end],'sourceDocument':document['url']},'provenance':{'rightsEvidenceUrl':acquisition['url'],'sourceDate':acquisition.get('date'),'sourceDocumentSha256':document['sha256']}},parsed=(ingredients,[text(body)],None))
 output.mkdir(parents=True);rawsha=hashlib.sha256()
 with gzip.open(output/'normalized.jsonl.gz','wt',encoding='utf8',compresslevel=1) as f:
  for row in rows:
   body=json.dumps([row],ensure_ascii=False,separators=(',',':'));rawsha.update(body.encode());f.write(body+'\n')
 (output/'decisions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in decisions));languages=collections.Counter(l for r in rows for l in r['data']['languages']);manifest={'schemaVersion':'offmenu-collection/1','sourceId':SOURCE,'releaseId':RELEASE,'status':'normalized','normalizedRows':len(rows),'counts':{'raw':input_count,'accepted':len(rows),'duplicates':sum(d['reason']=='duplicate-source-identity' for d in decisions),'quarantined':0,'excluded':input_count-len(rows)-sum(d['reason']=='duplicate-source-identity' for d in decisions),'records':len(rows)},'archiveSha256':rawsha.hexdigest(),'license':'Per-recipe CC BY-SA 4.0, CC0, Unlicense and documented historical original rights; attribution and share-alike retained','attribution':'Original recipe publishers and contributors; each record carries its own attribution','scope':'Complete acquired source files; only recipes with ingredient and instruction sections admitted. All source text remains locally retained. No inferred servings, density conversions, translations, country assignments or diet certifications. Historical rights-unresolved candidates retained separately.','sources':dict(source_counts),'languages':dict(languages),'standardQuantityIngredients':sum(r['data']['quantityCoverage']['standardQuantities'] for r in rows),'sourceNumericQuantityIngredients':sum(r['data']['quantityCoverage']['sourceNumericQuantities'] for r in rows),'publication':'local normalized recipe collection; separate checked curation follows','completedAt':now};attach_licenses(research,output,manifest);(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('research',type=Path);p.add_argument('wikis',type=Path);p.add_argument('english',type=Path);p.add_argument('output',type=Path);a=p.parse_args();collect(a.research,a.wikis,a.english,a.output)
