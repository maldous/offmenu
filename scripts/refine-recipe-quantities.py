#!/usr/bin/env python3
"""Reapply conservative quantity/alias parsing to an acquired recipe release."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
from recipe_format import ingredient

def refine(source, output):
    if output.exists():raise ValueError('Immutable refinement output already exists')
    manifest=json.loads((source/'manifest.json').read_text());output.mkdir()
    digest=hashlib.sha256();standard=numeric=count=0
    with gzip.open(output/'normalized.jsonl.gz','wt',compresslevel=1,encoding='utf8') as target:
        for line in gzip.open(source/'normalized.jsonl.gz','rt',encoding='utf8'):
            rows=json.loads(line)
            for row in rows:
                data=row['data'];publisher=data['sourcePublisher']
                if publisher not in ['unitools','smithsonian-archive']:
                    data['ingredients']=[ingredient(i['originalText']) or i for i in data['ingredients']]
                coverage={'ingredients':len(data['ingredients']),'standardQuantities':sum(i['amount'] is not None for i in data['ingredients']),'sourceNumericQuantities':sum(i['sourceQuantity'].get('value') is not None for i in data['ingredients'])}
                data['quantityCoverage']=coverage;standard+=coverage['standardQuantities'];numeric+=coverage['sourceNumericQuantities'];count+=1
                row['provenance']['changes']+=' Unicode-preserving ingredient aliases and exact metric source units reapplied; no density or missing quantity inferred.'
            body=json.dumps(rows,ensure_ascii=False,separators=(',',':'));digest.update(body.encode());target.write(body+'\n')
    assert count==manifest['normalizedRows']
    manifest.update(archiveSha256=digest.hexdigest(),standardQuantityIngredients=standard,sourceNumericQuantityIngredients=numeric,quantityRefinement='offmenu-recipe-quantities/2; non-Latin combining marks retained')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    shutil.copytree(source/'licenses',output/'licenses');shutil.copyfile(source/'decisions.jsonl',output/'decisions.jsonl')
    print(json.dumps({'records':count,'standardQuantityIngredients':standard,'sourceNumericQuantityIngredients':numeric}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();refine(a.source,a.output)
