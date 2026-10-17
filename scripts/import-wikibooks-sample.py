"""Conservative ingredient adapter; preserve original words and source attribution."""
import json,re,hashlib,argparse
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('dataset',help='Path to recipes_parsed.mini.json from gossminn/wikibooks-cookbook');args=parser.parse_args();raw=json.loads(Path(args.dataset).read_text())
terms=['chickpea flour','beef broth','beef stock','tomato sauce','pizza dough','bread flour','coconut milk','coconut cream','cooked rice','olive oil','vegetable oil','black beans','kidney beans','green beans','chicken broth','vegetable stock','chicken stock','garlic powder','tomato paste','brown sugar','lemon juice','lime juice','soy sauce','plain flour','wheat flour','baking powder','ground cumin','garlic','onion','tomato','potato','carrot','lentil','chickpea','spinach','rice','pasta','egg','milk','butter','water','salt','sugar','chicken','beef','salmon','tuna','pepper','coriander','coconut','yoghurt','cheese']
source=[]
for record in raw:
 d=record.get('recipe_data')or{}; info=d.get('infobox')or{};title=d.get('title')or'';lines=d.get('text_lines')or[];ing=[x['text']for x in lines if x.get('section')=='Ingredients' and x.get('line_type')=='ul'];instructions=[x['text']for x in lines if x.get('section')in ['Procedure','Preparation','Directions','Method','Instructions'] and x.get('line_type')in ['ol','p']];sv=str(info.get('servings')or'').strip()
 if not ing or not instructions or len(ing)>18 or len(instructions)>25 or not re.fullmatch(r'\d+',sv) or not 1<=int(sv)<=20:continue
 if not any(k in title.lower()for k in ['rice','soup','pasta','salad','egg','curry','chicken','bean','potato','fish','salmon','stew','lentil','pizza']):continue
 ingredients=[]
 for text in ing:
  clean=text.lower();matches=[(m.start(),-len(t),t) for t in terms for m in [re.search(r'\b'+re.escape(t)+r'(?:es|s)?\b',clean)] if m];name=min(matches)[2] if matches else None
  if name=='rice' and any(word in clean for word in ['cooked','boiled']):name='cooked rice'
  optional='optional' in clean
  amount=None;unit=None
  metric=re.findall(r'(?<![\d.–—-])(\d+(?:\.\d+)?)\s*(kg|ml|g|l)\b',clean)
  if len(metric)==1 and not re.search(r'\d\s*[–—-]\s*\d',clean):
   amount=float(metric[0][0]);unit=metric[0][1]
   if unit=='kg':amount*=1000;unit='g'
   if unit=='l':amount*=1000;unit='ml'
   if amount>10000:amount=None;unit=None
  if name in ['egg','onion','potato','carrot'] and re.match(r'^\d+\s+(?:large |small |medium )?'+name+r's?\b',clean):amount=float(re.match(r'\d+',clean)[0]);unit='count'
  if ' or ' in clean or name is None:amount=None;unit=None;name='review: '+re.sub(r'\s+',' ',clean)[:150]
  if 'flavored with' in clean or 'flavoured with' in clean:amount=None;unit=None
  ingredients.append({'ingredient':name,'quantity':amount,'unit':unit,'raw':text,'optional':optional})
 rid='wikibooks-'+hashlib.sha256(d['url'].encode()).hexdigest()[:12]
 source.append({'id':rid,'title':title,'servings':int(sv),'source':d['url'],'license':'CC-BY-SA-4.0','attribution':'Wikibooks contributors. Dataset by Gosse Minnema (July 2024). Adapted for offmenu; original ingredient text retained.','time':info.get('time'),'ingredients':ingredients,'instructions':instructions})
# A varied, bounded starting collection; full corpus import remains a separate operation.
chosen=[];seen=set()
for category in ['rice','soup','pasta','salad','egg','curry','chicken','bean','potato','fish','salmon','stew','lentil','pizza']:
 for r in [r for r in source if category in r['title'].lower()][:3]:
  if r['id'] not in seen:chosen.append(r);seen.add(r['id'])
recipes=json.loads(Path('examples/recipes.json').read_text())+chosen
Path('public/recipes.json').write_text(json.dumps(recipes,ensure_ascii=False,indent=2))
print(f'{len(chosen)} attributed Wikibooks recipes + authored demonstration')
