#!/usr/bin/env python3
"""Stream licensed JSONL product dumps or offmenu recipes into D1-compatible SQL."""
import argparse,gzip,json,time
p=argparse.ArgumentParser();p.add_argument('kind',choices=['products','recipes']);p.add_argument('source');p.add_argument('--country',help='OFF country tag, e.g. en:australia');args=p.parse_args()
def quote(value):return "'"+str(value).replace("'","''")+"'"
opened=gzip.open(args.source,'rt',encoding='utf8') if args.source.endswith('.gz') else open(args.source,encoding='utf8')
with opened as stream:
 records=(json.loads(line) for line in stream if line.strip()) if args.kind=='products' else iter(json.load(stream))
 for record in records:
  if args.kind=='products':
   if args.country and args.country not in record.get('countries_tags',[]):continue
   code=str(record.get('code',''))
   if not code.isdigit() or not 4<=len(code)<=32:continue
   doc=json.dumps({'status':1,'code':code,'product':record},ensure_ascii=False,separators=(',',':'))
   print('INSERT INTO products(barcode,data,source,license,checked_at) VALUES('+','.join(map(quote,[code,doc,'Open Food Facts','ODbL / DbCL',int(time.time()*1000)]))+') ON CONFLICT(barcode) DO UPDATE SET data=excluded.data,checked_at=excluded.checked_at;')
  else:
   if not all(record.get(k) for k in ['id','title','source','license']):raise ValueError('Recipes need id, title, source and license')
   print('INSERT INTO recipes(id,title,doc) VALUES('+','.join(map(quote,[record['id'],record['title'],json.dumps(record,ensure_ascii=False,separators=(',',':'))]))+') ON CONFLICT(id) DO UPDATE SET title=excluded.title,doc=excluded.doc;')
