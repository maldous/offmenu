"""Conservative recipe extraction: unknown measures stay unknown; original text retained."""
import fractions,html,json,re,unicodedata
from pathlib import Path
import mwparserfromhell
ALIASES=json.loads((Path(__file__).resolve().parents[2]/'apps/web/assets/recipe-ingredient-aliases.json').read_text())
FRACTIONS={'½':'1/2','⅓':'1/3','⅔':'2/3','¼':'1/4','¾':'3/4','⅕':'1/5','⅖':'2/5','⅗':'3/5','⅘':'4/5','⅙':'1/6','⅚':'5/6','⅛':'1/8','⅜':'3/8','⅝':'5/8','⅞':'7/8'}
UNITS={'mg':('g',0.001),'µg':('g',0.000001),'μg':('g',0.000001),'dkg':('g',10),'dag':('g',10),'কিলোগ্রাম':('g',1000),'মিলিলিটার':('ml',1),'লিটার':('ml',1000),'কেজি':('g',1000),'গ্রাম':('g',1),'ml':('ml',1),'g':('g',1),'gram':('g',1),'grams':('g',1),'gramme':('g',1),'grammes':('g',1),'gramos':('g',1),'grammi':('g',1),'гр':('g',1),'г':('g',1),'克':('g',1),'kg':('g',1000),'kilogram':('g',1000),'kilograms':('g',1000),'公斤':('g',1000),'千克':('g',1000),'ml':('ml',1),'millilitre':('ml',1),'milliliters':('ml',1),'毫升':('ml',1),'cl':('ml',10),'dl':('ml',100),'l':('ml',1000),'litre':('ml',1000),'litres':('ml',1000),'liter':('ml',1000),'liters':('ml',1000),'oz':('g',28.349523125),'ounce':('g',28.349523125),'ounces':('g',28.349523125),'lb':('g',453.59237),'lbs':('g',453.59237),'pound':('g',453.59237),'pounds':('g',453.59237),'piece':('count',1),'pieces':('count',1),'count':('count',1),'个':('count',1),'個':('count',1)}
OTHER_UNITS={'cup','cups','tsp','teaspoon','teaspoons','tbsp','tablespoon','tablespoons','cucharada','cucharadas','cucharadita','cucharaditas','tasse','tasses','cuillère','cuillerée','cuillere','esslöffel','teelöffel','el','tl','bunch','bunches','clove','cloves','can','cans','packet','packets','pinch','handful','pint','pints','quart','quarts','gallon','gallons','斤','两','勺','茶匙','汤匙','大匙','小匙','瓣','把','стакан','стакана','ложка','ложки','шт','šálka','gill','gills','dram','drachm','spoonful','spoonfuls','dessertspoon','dessertspoons','pfund','pfunde','szklanka','łyżka','ложек','ст','ч','ч.','ст.','কাপ','চামচ','ক্যান','カップ','片','大さじ','小さじ'}
ING_HEAD=['ingredients','ingredienti','ingrédients','ingredientes','zutaten','składniki','ингредиенты','состав','продукты','材料','原料','食材','必备原料','计算','מרכיבים','מצרכים','مكونات','المقادير','المكونات','مواد لازم','উপকরণ','উপকরন','सामग्री','bahan','malzemeler','재료','ainekset','aineet','ingrediënten','ingredienser','sestavine','sastojci','υλικά','συστατικά','інгредієнти','ingrediencoj','ingedientes','nguyên liệu','ส่วนผสม','hozzával','alapanyag','suroviny','suroviny','ingredients','सामाग्री','bahan-bahan','bahankeperluan']
DIR_HEAD=['directions','instructions','procedure','preparation','method','préparation','preparazione','preparación','preparacao','modo de preparo','modo de preparação','elaboración','procedimiento','zubereitung','przygotowanie','wykonanie','приготовление','способ приготовления','делаем','操作','做法','步骤','作り方','調理','הכנה','אופן ההכנה','طريقة','طرز تهیه','প্রণালী','विधि','caranya','cara membuat','cara memasak','yapılışı','hazırlanışı','조리','만드는','valmistus','bereiding','fremgang','tillagning','priprava','priprema','εκτέλεση','приготування','preparado','cách làm','วิธีทำ','elkészít','elkeszit','příprava','postup','основной рецепт','recept elkészít']
def norm(value):
 result=[];latin=False
 for c in unicodedata.normalize('NFKD',str(value).lower()):
  if unicodedata.combining(c) and latin:continue
  if not unicodedata.combining(c):latin='LATIN' in unicodedata.name(c,'')
  result.append(c)
 return unicodedata.normalize('NFC',''.join(result)).strip()
UNITS={norm(k):v for k,v in UNITS.items()}
OTHER_UNITS={norm(k) for k in OTHER_UNITS}
def text(value,wiki=False):
 if wiki and re.match(r'^\s*\[\[(?:File|Image|Fichier|Datei|Súbor|Файл|ファイル|文件|קובץ|ملف|Fájl):',value,re.I):return ''
 value=re.sub(r'<ref\b[^>]*>.*?</ref>|<ref[^>]*/>','',value,flags=re.S|re.I)
 value=re.sub(r'\{\{(?:frac|fraction)\|(\d+)\|(\d+)\}\}',r'\1/\2',value,flags=re.I)
 value=re.sub(r'\*([^*]+)\*',r'\1',value) if not wiki else value
 if wiki:
  code=mwparserfromhell.parse(value)
  for template in list(code.filter_templates()):
   if norm(template.name) in {'i','ing','ingredient','ingrediente','ingredienti','סמ','מרכיב'}:
    values=[str(p.value).strip() for p in template.params if str(p.name).strip().isdigit()]
    if values:code.replace(template,values[-1])
  value=str(code)
 value=mwparserfromhell.parse(value).strip_code(normalize=True,collapse=True) if wiki else re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',value)
 return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',value)).replace('**','').replace('__','')).strip()
def number(value):
 value=''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value)
 for glyph,fraction in FRACTIONS.items():value=value.replace(glyph,(' ' if re.search(r'\d'+re.escape(glyph),value) else '')+fraction)
 value=value.strip()
 if re.search(r'[1-9]\d*[,.]\d{3}(?:\D|$)',value):return None
 value=value.replace(',','.')
 try:return float(sum((fractions.Fraction(x) for x in value.split()),fractions.Fraction(0)))
 except (ValueError,ZeroDivisionError):return None
ALIAS_LOOKUP={norm(alias):key for key,values in ALIASES.items() for alias in values}
def identity(name):
 value=norm(name).strip(' .;:')
 if re.search(r'\b(and|or|et|oder|ou)\b',value) or '/'in value:return None
 return ALIAS_LOOKUP.get(value.split(',')[0].split(' (')[0].strip())

def ingredient(line,wiki=False):
 if wiki and line.lstrip().startswith('|') and '||' in line:
  line=' '.join(c.strip() for c in line.strip().strip('|').split('||') if c.strip())
 original=text(re.sub(r'^\s*(?:[-*#•]|\d+[.)])\s*','',line),wiki)
 if not original or re.match(r'^[|!{}]',original) or re.match(r'^(?:for|per|pour)\s+\d+\s+(?:persons?|people|servings?|portions?|persone|personas)',original,re.I) or original.endswith(':') or re.fullmatch(r'\(\d+[^)]*\)',original):return None
 if re.search(r'^(平底锅|炒锅|烤箱|菜刀|砧板|锅铲|工具|碗|筷子|oven|skillet|equipment)\b',original):return None
 optional=bool(re.search(r'optional|可选|可選|facultatif|opcional|nach belieben',original,re.I));value=original
 for glyph,fraction in FRACTIONS.items():value=value.replace(glyph,(' ' if re.search(r'\d'+re.escape(glyph),value) else '')+fraction)
 for c in set(value):
  if c.isdecimal():value=value.replace(c,str(unicodedata.decimal(c)))
 value=value.replace('–','-').replace('—','-');quantity=None;unit=None;name=value;range_value=None
 pattern=r'(\d+(?:[.,]\d+)?(?:/\d+)?(?:\s+\d+/\d+)?)'
 leading=re.match(r'^'+pattern+r'(?:\s*-\s*'+pattern+r')?\s*(.*)$',value)
 trailing_value=re.sub(r'[（(][^）)]*[）)]','',value)
 trailing=re.match(r'^(.*?)\s*(?:[-:：]\s*)?'+pattern+r'\s*([^\s\d.,()（）]+)\.?$',trailing_value)
 if leading:
  quantity=number(leading[1]);name=leading[3];range_value={'min':quantity,'max':number(leading[2])} if leading[2] else None
  token=re.match(r'^([^\s.]+)\.?\s*(.*)$',name)
  if token and norm(token[1]) in set(UNITS)|OTHER_UNITS:unit=norm(token[1]);name=token[2]
  else:unit='count' if identity(name) else None
 elif trailing and norm(trailing[3]) in set(UNITS)|OTHER_UNITS:
  name=trailing[1].strip(' -:：');quantity=number(trailing[2]);unit=norm(trailing[3])
 name=re.sub(r'^(?:of|de|d[’\'])\s+','',name,flags=re.I);name=name.strip(' .;:-') or original
 amount=None;canonical=None
 if quantity is not None and not range_value and unit in UNITS and quantity>0:canonical,factor=UNITS[unit];amount=quantity*factor
 key=identity(name)
 if unit=='count' and key is None:amount=None;canonical=None
 return {'name':name,'ingredientId':key,'amount':amount,'unit':canonical,'optional':optional,'originalText':original,'foodMatchStatus':'candidate-alias' if key else 'unresolved','sourceQuantity':{'value':quantity if not range_value else None,'unit':unit,'range':range_value,'original':original,'status':'parsed' if quantity is not None and not range_value else 'range' if range_value else 'unspecified'},'quantityStatus':'standard-mass-volume-or-count' if amount is not None else 'source-measure-needs-review','scaling':'linear'}
def sections(content,wiki=False):
 ingredients=[];directions=[];mode='';heading='';current=[];direction_depth=None
 if not wiki and content.startswith('---'):
  parts=content.split('---',2)
  if len(parts)==3:content=parts[2]
 recipe_md=not wiki and not re.search(r'^#{2,6}\s*(?:Ingredients|Ingredientes|Ingredienti|必备原料)',content,re.M|re.I)
 for line in content.splitlines():
  if recipe_md and line.strip()=='---':mode='ingredients' if mode=='' else 'directions' if mode=='ingredients' else '';continue
  match=re.match(r'^\s*==+\s*(.*?)\s*==+\s*$',line) if wiki else re.match(r'^\s*#{1,6}\s+(.+?)\s*$',line)
  if not match:
   pseudo=re.match(r"^\s*(?:['*]{2,3}|;)\s*(.+?)(?:['*]{2,3})?\s*:??\s*$",line)
   bold=re.match(r"^\s*(?:'{2,3}|\*{2,3})(.+?)(?:'{2,3}|\*{2,3})(?:\s+.*)?$",line)
   if bold and any(norm(bold[1]).strip(': ').startswith(norm(v)) for v in ING_HEAD+DIR_HEAD):match=bold
   elif pseudo and any(norm(v)==norm(pseudo[1]).strip(': ') for v in ING_HEAD+DIR_HEAD):match=pseudo
  if match:
   heading=text(match[1] or (match[2] if match.lastindex and match.lastindex>=2 else ''),wiki);h=norm(heading)
   new_mode='' if any(v in h for v in ['器具','utensils','equipment']) else 'ingredients' if any(norm(v) in h for v in ING_HEAD) else 'directions' if any(norm(v) in h for v in DIR_HEAD) else ''
   depth=len(re.match(r'^\s*([=#]+)',line)[1]) if re.match(r'^\s*([=#]+)',line) else 2
   if not new_mode and mode=='directions' and direction_depth is not None and depth>direction_depth:directions.append(heading);continue
   mode=new_mode
   if mode=='directions':direction_depth=depth
   continue
  if mode=='ingredients' and line.strip() and not line.lstrip().startswith(('![','{{','[[Category:','[[Catégorie:','{|','|}')):
   values=re.split(r',\s*(?![0-9])',line) if not re.match(r'^\s*[-*#•]',line) and wiki else [line]
   for value in values:
    parsed=ingredient(value,wiki)
    if parsed:ingredients.append(parsed)
  elif mode=='directions' and line.strip() and not line.lstrip().startswith(('![','{{','[[Category:','[[Catégorie:','{|','|}')):
   step=text(re.sub(r'^\s*(?:[-*#•]|\d+[.)])\s*','',line),wiki)
   if step:directions.append(step)
 # A calculation section can supply a quantity for the same ingredient already listed.
 merged=[];positions={}
 for item in ingredients:
  key=item.get('ingredientId') or norm(item['name'])
  if key in positions and merged[positions[key]]['amount'] is None and item['amount'] is not None:merged[positions[key]]=item
  elif key not in positions:positions[key]=len(merged);merged.append(item)
  else:merged.append(item)
 servings=None
 match=re.search(r'(?:servings|portions|porciones|portionen|порции|人数|份数)\s*[=:|]\s*(\d+)\b',content,re.I)
 if not match:match=re.search(r'(\d+)\s*(?:servings|portions|porciones|人份|人食用|人分)\b',content,re.I)
 if match and int(match[1])>0 and not re.search(r'[0-9]\s*[-–]\s*$',content[max(0,match.start()-8):match.start()]) and not re.match(r'\s*[-–]\s*[0-9]',content[match.end():]):servings=int(match[1])
 return merged,directions,servings
