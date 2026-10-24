"""Read-only, source-scoped relation lookup. No automatic nutrition/safety decision."""
import argparse
import json
from pathlib import Path
import sqlite3

from gold_builder import (_pin, _json, alternative_scope_valid,
                          alternative_group_valid, relation_condition)


def lookup_recipe_products(db, *, source, selections=()):
    """Return qualified source-structure paths with explicit alternative choices.

    source is the exact recipe occurrence plus source mention context. Unknown
    selection is represented separately, never an implicit union or first item.
    Product fit is held: no selected-tuple fit-proof contract is evaluated here.
    The caller owns the connection; this function issues SELECT statements only.
    """
    result = dict(paths=[], choices=[], errors=[], purpose='source-product-lookup-only',
                  automaticCooking=False, nutritionAcceptance=False, safetyAcceptance=False,
                  productFitAcceptance=False)
    if not alternative_scope_valid(source):
        result['errors'].append('invalid source scope'); return result
    if type(selections) not in (list, tuple) or len(selections) > 1000:
        result['errors'].append('invalid selections'); return result

    def query(sql, args=()):
        cur=db.execute(sql,args)
        return [dict(zip([c[0] for c in cur.description],r)) for r in cur.fetchall()]

    def supported(kind, payload, scopes):
        cids=payload.get('citationIds')
        if (payload.get('scope',{}).get('visibility')!='public'
            or type(cids) is not list or not cids or any(type(c) is not str for c in cids)):
            return False
        for cid in cids:
            evidence=query('SELECT s.evidence_sha256,c.payload_json FROM gold_support s '
                'JOIN gold_citations c ON c.citation_id=s.citation_id '
                'WHERE s.target_kind=? AND s.target_id=? AND s.citation_id=? AND s.support_scope IN ('+
                ','.join('?' for _ in scopes)+')',
                (kind,payload.get('id'),cid,*scopes))
            if not any(_pin(e['evidence_sha256']) and json.loads(e['payload_json']).get('scope',{}).get('visibility')=='public' for e in evidence):
                return False
        return True

    def entity(eid, domain, typ):
        rows=query('SELECT * FROM gold_entities WHERE entity_id=? AND state=\'verified\' AND domain=? AND entity_type=?',(eid,domain,typ))
        if len(rows)!=1: return None
        e=rows[0];p=json.loads(e['payload_json'])
        if p.get('id')!=e['resource_id'] or not supported('resource',p,('record','field')): return None
        owners=query('SELECT o.* FROM gold_occurrences o JOIN gold_entity_occurrences x '
                     'ON x.occurrence_id=o.occurrence_id WHERE x.entity_id=?',(eid,))
        if not owners or any(o['state']!='verified' for o in owners): return None
        e['payload']=p;e['owners']=owners;return e

    def edges(eid,predicate):
        out=[]
        for row in query('SELECT * FROM gold_edges WHERE subject_id=? AND predicate_id=?',(eid,predicate)):
            p=json.loads(row['payload_json']);row['payload']=p;out.append(row)
        return out

    def edge_ok(row, subject, obj, states=('verified',)):
        p=row['payload']
        return (row['state'] in states and p.get('id')==row['relation_id']
                and p.get('subjectId')==subject['resource_id'] and p.get('objectId')==obj['resource_id']
                and p.get('predicateId')==row['predicate_id'] and supported('relation',p,('relationship',)))

    recipes=query('SELECT entity_id FROM gold_entities WHERE resource_id=? AND domain=\'recipes\' AND entity_type=\'recipe\'',(source['recipeId'],))
    recipes=[e for r in recipes if (e:=entity(r['entity_id'],'recipes','recipe')) and any(
        all(o[k]==source[v] for k,v in [('source_key','sourceKey'),('source_version','sourceVersion'),
            ('record_id','recordId'),('content_sha256','contentSha256')]) for o in e['owners'])]
    if len(recipes)!=1:
        result['errors'].append('exact qualified recipe occurrence not found');return result
    recipe=recipes[0];mentions=edges(recipe['entity_id'],'mentions')
    # A declared source mention may be held because its application mapping is
    # invalid. It supplies context only, never eligibility for a returned path.
    def declared_context(edge):
        p=edge['payload']
        if (type(p) is not dict or p.get('objectId')!=source['mentionId']
            or p.get('subjectId')!=recipe['resource_id'] or p.get('id')!=edge['relation_id']
            or p.get('predicateId')!='mentions' or not supported('relation',p,('relationship',))):
            return False
        try:
            if relation_condition(p) is not None: return False
        except ValueError: return False
        return bool(query('SELECT 1 FROM gold_entities WHERE entity_id=? AND resource_id=? '
                          'AND domain=\'ingredients\' AND entity_type=\'ingredient-mention\'',
                          (edge['object_id'],source['mentionId'])))

    if not any(declared_context(e) for e in mentions):
        result['errors'].append('source mention not declared by recipe');return result
    selected={};invalid_selection=False
    for s in selections:
        if (type(s) is not dict or set(s)!={'groupId','branchId','sourceScope'}
            or any(type(s[k]) is not str or not s[k].strip() for k in ('groupId','branchId'))
            or not alternative_scope_valid(s['sourceScope'])):
            invalid_selection=True;continue
        key=(s['groupId'],_json(s['sourceScope']))
        selected.setdefault(key,[]).append(s['branchId'])
    consumed=set()
    for me in mentions:
        mention=entity(me['object_id'],'ingredients','ingredient-mention')
        if not mention or not edge_ok(me,recipe,mention):
            if declared_context(me):
                result['choices'].append(dict(mentionId=source['mentionId'],groupId=None,
                    sourceScope=source,status='held',branchId=None))
                result['errors'].append('requested source mention application qualification held')
            continue
        try:
            if relation_condition(me['payload']) is not None: continue
        except ValueError: continue
        candidates=edges(mention['entity_id'],'canonical_ingredient')
        payloads=[e['payload'] for e in candidates]
        valid=alternative_group_valid(payloads)
        conditional=any('condition' in p for p in payloads)
        chosen=None;conditions=[]
        if conditional:
            try: conditions=[relation_condition(p) for p in payloads]
            except ValueError: valid=False
            c=next((c for c in conditions if c),None)
            scope=c['sourceScope'] if c else None
            expected=dict(source,mentionId=mention['resource_id'])
            valid=valid and scope==expected and all(
                o['source_key']==source['sourceKey'] and o['source_version']==source['sourceVersion'] for o in mention['owners'])
            key=(c['groupId'],_json(scope)) if c else None
            values=selected.get(key,[]);consumed.add(key)
            branches={c['branchId'] for c in conditions if c}
            status='unknown'
            if not valid or invalid_selection or len(values)>1: status='invalid'
            elif values:
                if values[0] not in branches: status='unsupported'
                else: chosen=values[0];status='selected'
            result['choices'].append(dict(mentionId=mention['resource_id'],groupId=c['groupId'] if c else None,
                sourceScope=scope,status=status,branchId=chosen))
            if chosen is None: continue
        elif not valid:
            result['errors'].append('invalid alternative metadata: '+mention['resource_id']);continue
        for ce in candidates:
            try: condition=relation_condition(ce['payload'])
            except ValueError: continue
            if condition and (ce['state']!='conditional' or condition['branchId']!=chosen): continue
            if not condition and ce['state']!='verified': continue
            canonical=entity(ce['object_id'],'ingredients','ingredient')
            if not canonical or not edge_ok(ce,mention,canonical,('conditional',) if condition else ('verified',)): continue
            for pe in query("SELECT * FROM gold_edges WHERE object_id=? AND predicate_id IN ('represents','contains') AND state='verified'",(canonical['entity_id'],)):
                pe['payload']=json.loads(pe['payload_json'])
                product=entity(pe['subject_id'],'barcodes','barcode-product')
                if not product or not edge_ok(pe,product,canonical): continue
                try:
                    if relation_condition(pe['payload']) is not None: continue
                except ValueError: continue
                result['paths'].append(dict(recipeId=recipe['resource_id'],mentionId=mention['resource_id'],
                    canonicalId=canonical['resource_id'],productId=product['resource_id'],
                    sourceScope=dict(source,mentionId=mention['resource_id']),
                    productFitQualification=dict(state='held',reason='selected-tuple-fit-contract-not-evaluated'),
                    relations=[me['payload'],ce['payload'],pe['payload']]))
        if conditional and chosen is not None and not any(p['mentionId']==mention['resource_id'] for p in result['paths']):
            result['choices'][-1]['status']='unsupported'
    if invalid_selection or set(selected)-consumed:
        result['errors'].append('invalid or unmatched selection scope/group')
        # A malformed/stale request cannot grant conditional paths. Ordinary
        # independent source paths remain available.
        result['paths']=[p for p in result['paths'] if 'condition' not in p['relations'][1]]
        for choice in result['choices']:
            if choice['status']!='held': choice.update(status='invalid',branchId=None)
    result['paths'].sort(key=_json)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--source-json',required=True,help='Exact source scope JSON object')
    parser.add_argument('--selections-json',default='[]',help='Explicit selections JSON list')
    args=parser.parse_args()
    # URI encoding prevents file names from injecting SQLite URI options.
    with sqlite3.connect(Path(args.database).resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        print(json.dumps(lookup_recipe_products(db,source=json.loads(args.source_json),
                         selections=json.loads(args.selections_json)),ensure_ascii=False,sort_keys=True))


if __name__=='__main__': main()
