#!/usr/bin/env python3
"""Inert, hash-pinned projection of the exact authored public landing asset table.
Never imports/evaluates JavaScript. Never decodes bodies outside the source allowlist.
"""
import argparse, base64, hashlib, json, re
from pathlib import Path

SOURCE_PATH='/home/user/src/offmenu-data/runtime/layout-migration/worker05/local-own-data-root14-successor-20261027/all15-ready-source-r1/root-static-assets.mjs'
SOURCE_SHA='1d16ed224861874bc1bcc51221eb04554308139e4a86048d20f177f70934dab6'
SOURCE_COMMIT='39396038705628dea85e165d5eab1b571d1bc353'
ALLOWED_EXTENSIONS={'.mjs','.js','.css','.html','.svg','.json'}

# Exact scene-JSON paths observed in current183 public scene descriptors and
# recovered39396038 asset-aliases-ready-r1 / scene-adapter source. This is not a
# wildcard for landing data. New scene JSON needs its own reviewed route evidence.
SCENE_JSON_ROUTES=frozenset(['/landing-motion-v12/assets/body-mesh.json', '/landing-motion-v12/assets/carton-path.json', '/landing-motion-v12/assets/hand-mesh.json', '/landing-motion-v12/assets/layers.json', '/landing-motion-v12/assets/room-surfaces.json', '/landing-world-actions/current180-mounts-r1-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/fridge-geometry.json', '/landing-world-actions/current180-mounts-r1-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/room-fridge-open.json', '/landing-world-actions/current180-mounts-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/bowl-scale-geometry.json', '/landing-world-actions/current180-mounts-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/room-counter-extended.json', '/landing-world-actions/current180-mounts-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/source-bounds.json', '/landing-world-actions/current180-pouring-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/bowl-scale-geometry.json', '/landing-world-actions/current180-pouring-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/room-counter-extended.json', '/landing-world-actions/current180-pouring-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/source-bounds.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/fridge-geometry.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/room-fridge-open.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/bowl-scale-geometry.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/room-counter-extended.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/source-bounds.json', '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/scene15-wide-world-adapter-r2/source-produce-region.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/fridge-geometry.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/fridge-support-r3/room-fridge-open.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/bowl-scale-geometry.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/room-counter-extended.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/pouring-world-r4/source-bounds.json', '/landing-world-actions/current183-wide15-r1-assets/native15-first-sequence-20261026/full15-master-r1/scene15-wide-world-adapter-r2/source-produce-region.json'])
FORBIDDEN_ROUTE_TOKEN=re.compile(r'(?:^|[/._-])(?:api|data|auth|state|config|corpus|products|datasets)(?:$|[/._-])',re.IGNORECASE)
DESCRIPTOR_FIELDS=frozenset({'sha256','bytes','mime'})


def digest(b): return hashlib.sha256(b).hexdigest()
def no_duplicates(items):
    out={}
    for k,v in items:
        if k in out: raise ValueError('Duplicate JSON key')
        out[k]=v
    return out

def literal_table(text,name):
    # The unbundled authored source has named literal exports. Dynamic/indirect
    # variants are deliberately refused, not evaluated or guessed.
    matches=list(re.finditer(r'\b(?:const|let|var)\s+'+re.escape(name)+r'\s*=\s*',text))
    if len(matches)!=1: raise ValueError('Exactly one declaration required: '+name)
    start=matches[0].end()
    frozen=re.match(r'Object\.freeze\(\s*',text[start:])
    if frozen: start+=frozen.end()
    if text[start:start+1]!='{': raise ValueError('Initializer must be JSON object: '+name)
    value,end=json.JSONDecoder(object_pairs_hook=no_duplicates).raw_decode(text,start)
    suffix=text[end:]
    if frozen:
        closing=re.match(r'\s*\)',suffix)
        if not closing: raise ValueError('Unsupported freeze wrapper')
        suffix=suffix[closing.end():]
    if not isinstance(value,dict) or not re.match(r'(?:\s*(?:;|$)|[ \t]*\r?\n[ \t]*(?:export\b|const\b|let\b|var\b))',suffix):
        raise ValueError('Unsupported initializer suffix: '+name)
    return value

def project(raw,expected_sha=SOURCE_SHA):
    if digest(raw)!=expected_sha: raise ValueError('Exact source preimage mismatch')
    text=raw.decode('utf-8',errors='strict')
    routes=literal_table(text,'ROOT14_ROUTES')
    bodies=literal_table(text,'ROOT14_BODIES')
    selected={}
    for route,d in routes.items():
        if not isinstance(route,str) or not isinstance(d,dict): raise ValueError('Invalid route descriptor')
        if set(d)!=DESCRIPTOR_FIELDS: raise ValueError('Descriptor fields must be only sha256/bytes/mime')
        sha=d.get('sha256');size=d.get('bytes');mime=d.get('mime')
        if not isinstance(sha,str) or not re.fullmatch(r'[0-9a-f]{64}',sha) or type(size) is not int or size<0 or not isinstance(mime,str): raise ValueError('Invalid descriptor pin')
        if not route.startswith('/landing-') or Path(route).suffix not in ALLOWED_EXTENSIONS: continue
        if any(c in route for c in ('?', '#', '%', '\\', '\0')) or '..' in route.split('/'): raise ValueError('Unsafe source route')
        if FORBIDDEN_ROUTE_TOKEN.search(route): continue
        if Path(route).suffix=='.json' and route not in SCENE_JSON_ROUTES: continue
        encoded=bodies.get(sha)
        if not isinstance(encoded,str): raise ValueError('Missing literal source body')
        body=base64.b64decode(encoded,validate=True)
        if len(body)!=size or digest(body)!=sha: raise ValueError('Body pin mismatch')
        source=body.decode('utf-8',errors='strict')
        if '\0' in source: raise ValueError('Not text source')
        # A landing source projection is not authority to export embedded food
        # corpora, API payload tables, credentials or runtime launch material.
        if 'bodyBase64' in source or re.search(r'/products/[^\s"\']*\.json\.gz',source): raise ValueError('Embedded product payload indicator')
        item=selected.setdefault(sha,{'bytes':body,'routes':[]})
        item['routes'].append(route)
    return routes,selected

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default=SOURCE_PATH);ap.add_argument('--output',required=True);args=ap.parse_args()
    raw=Path(args.input).read_bytes();routes,selected=project(raw)
    out=Path(args.output)
    if out.exists() and any(out.iterdir()): raise ValueError('Output directory must be empty')
    (out/'source-bodies').mkdir(parents=True,exist_ok=True)
    entries=[]
    for sha,item in sorted(selected.items()):
        relative='source-bodies/'+sha+'.source';(out/relative).write_bytes(item['bytes'])
        entries.append({'path':relative,'sha256':sha,'bytes':len(item['bytes']),'routes':sorted(item['routes'])})
    table={'schemaVersion':'offmenu-public-landing-route-projection/1','parentSourcePath':SOURCE_PATH,'parentSHA256':SOURCE_SHA,'sourceCommit':SOURCE_COMMIT,'routes':routes}
    (out/'public-landing-route-manifest.json').write_text(json.dumps(table,sort_keys=True,indent=2)+'\n')
    receipt={'schemaVersion':'offmenu-inert-landing-source-extraction/1','parentSourcePath':SOURCE_PATH,'parentSHA256':SOURCE_SHA,'sourceCommit':SOURCE_COMMIT,'sourceBytes':len(raw),'routeCount':len(routes),'sourceBodies':entries,'excluded':'No opaque image/binary body decoded or exported; no non-landing source, API, data, state, config, runtime action or full parent file exported. JavaScript never executed.'}
    (out/'extraction-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'routeCount':len(routes),'sourceBodyCount':len(entries),'sourceBytes':sum(e['bytes'] for e in entries),'output':str(out)}))

if __name__=='__main__': main()
