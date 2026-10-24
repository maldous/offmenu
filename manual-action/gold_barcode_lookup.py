"""Bounded private-local query of an independently selected admitted GOLD snapshot."""
import argparse
from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from gold_builder import _pin, relation_condition, alternative_scope_valid
from gold_relation_lookup import lookup_recipe_products


class BarcodeQueryError(ValueError):
    pass


BARCODE_PROPERTIES=('usda:gtin-upc',)


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


@dataclass(frozen=True)
class SnapshotSelection:
    database_sha256: str
    admission_sha256: str


class _Budget:
    """SELECT-only connection adapter also bounds the existing recipe reader."""
    def __init__(self,db,rows,steps,seconds,barcode):
        self.db=db;self.remaining=rows;self.steps=steps;self.deadline=time.monotonic()+seconds
        self.ticks=0
        self.support_index=None;self.citation_rows={}
        self.bytes_read=0
        self.barcode=barcode;self.support_targets={}

    def load_supports(self):
        if self.support_index is not None:return
        # Recipe qualification uses resource/text/relation supports. Assertion
        # supports are needed only for the exact barcode's source products, not
        # unrelated source-reference nutrition. Keep all metric definition
        # metadata so separate definition rights cannot disappear.
        rows=self.query("SELECT support_id,target_kind,target_id,citation_id,support_scope,evidence_sha256 FROM gold_support "
            "WHERE target_kind IN ('resource','text','relation','metric') OR (target_kind='assertion' AND target_id IN "
            "(SELECT assertion_id FROM gold_claims WHERE entity_id IN (SELECT entity_id FROM gold_claims "
            "WHERE property_id='usda:gtin-upc' AND json_extract(payload_json,'$.value.kind')='identifier' "
            "AND json_type(payload_json,'$.value.value')='text' AND json_extract(payload_json,'$.value.value')=? COLLATE BINARY)))",(self.barcode,))
        self.support_index={}
        for row in rows:
            key=(row['target_kind'],row['target_id'],row['citation_id'])
            self.support_index.setdefault(key,[]).append(row)
            self.support_targets.setdefault(key[:2],[]).append(row)

    def metric_definitions(self,metric_id):
        self.load_supports()
        rows=[r for r in self.support_targets.get(('metric',metric_id),()) if r['support_scope']=='definition']
        self.consume(tuple(r.values()) for r in rows)
        return rows

    def consume(self,source):
        result=[]
        for row in source:
            if self.remaining<1:raise BarcodeQueryError('row-limit')
            self.bytes_read+=sum(len(v.encode('utf-8')) if type(v) is str else len(v) if type(v) is bytes else 8 for v in row)
            if self.bytes_read>8388608:raise BarcodeQueryError('source-byte-limit')
            self.remaining-=1;result.append(row)
        return result

    def progress(self):
        self.ticks+=1
        return self.ticks>self.steps or time.monotonic()>self.deadline

    def execute(self,sql,args=()):
        if not sql.lstrip().upper().startswith('SELECT '): raise BarcodeQueryError('select-only')
        if time.monotonic()>self.deadline: raise BarcodeQueryError('resource-limit')
        if 'FROM gold_support s JOIN gold_citations c' in sql:
            self.load_supports()
            key=tuple(args[:3]);cid=args[2]
            if cid not in self.citation_rows:
                self.citation_rows[cid]=self.query('SELECT payload_json FROM gold_citations WHERE citation_id=?',(cid,))
            values=[(r['evidence_sha256'],c['payload_json']) for r in self.support_index.get(key,())
                    if r['support_scope'] in args[3:] for c in self.citation_rows[cid]]
            class MetadataCursor:
                description=(('evidence_sha256',),('payload_json',))
                def fetchall(self):return self_budget.consume(values)
            self_budget=self
            return MetadataCursor()
        # Enforce the global row budget in SQL, including nested legacy calls.
        cur=self.db.execute('SELECT * FROM ('+sql+') LIMIT ?',(*args,self.remaining+1))
        budget=self
        class Cursor:
            description=cur.description
            def fetchall(self):
                return budget.consume(cur)
        return Cursor()

    def query(self,sql,args=()):
        cur=self.execute(sql,args)
        return [dict(zip([c[0] for c in cur.description],r)) for r in cur.fetchall()]


def read_barcode(db,barcode,*,selection,selections=(),selected_product_id=None,
                 requested_context=None,max_rows=10000,max_paths=50,max_bytes=262144,
                 max_steps=1000000,max_seconds=3):
    """Exact lexeme lookup; caller exclusively owns the selected RO connection.

    Returns source associations, never a barcode winner, recommendation, complete
    recipe or nutrition transfer. Errors do not masquerade as empty/truncated data.
    """
    if (type(selection) is not SnapshotSelection or not _pin(selection.database_sha256)
        or not _pin(selection.admission_sha256)): raise BarcodeQueryError('unselected-snapshot')
    if type(barcode) is not str or not 1<=len(barcode)<=64 or any(c not in '0123456789' for c in barcode):
        raise BarcodeQueryError('barcode-lexeme-required')
    for value,ceiling in [(max_rows,20000),(max_paths,100),(max_bytes,1048576),(max_steps,2000000)]:
        if type(value) is not int or not 1<=value<=ceiling: raise BarcodeQueryError('invalid-limit')
    if type(max_seconds) not in (int,float) or not 0<max_seconds<=10: raise BarcodeQueryError('invalid-limit')
    context={} if requested_context is None else requested_context
    if (type(context) is not dict or len(context)>16 or len(encoded(context))>4096
        or type(selections) not in (list,tuple) or len(selections)>100 or len(encoded(selections))>32768
        or selected_product_id is not None and (type(selected_product_id) is not str or not 1<=len(selected_product_id)<=2048)):
        raise BarcodeQueryError('invalid-selection-context')
    if any(type(s) is not dict or set(s)!={'groupId','branchId','sourceScope'}
           or any(type(s[k]) is not str or not s[k].strip() for k in ('groupId','branchId'))
           or not alternative_scope_valid(s['sourceScope']) for s in selections):
        raise BarcodeQueryError('invalid-selection-context')
    out=dict(schemaVersion='offmenu.admitted-barcode-consumer/1',barcodeLexeme=barcode,
        snapshot=dict(databaseSha256=selection.database_sha256,admissionSha256=selection.admission_sha256),
        availability='no-result',products=[],paths=[],menus=[],entities={},citations={},choices=[],held=[],
        menuData='unknown',nutritionState='unknown',selectedProductId=selected_product_id,
        purpose='private-local source-structure lookup; retain all source-use restrictions',
        identifierProperties=list(BARCODE_PROPERTIES),
        automaticProductSelection=False,universalIdentity=False,completeExecutableRecipe=False,
        recipeNutrientTotals=None,sourceReferenceNutritionTransfer=False,gs1Allocation='NOT_CHECKED')
    budget=_Budget(db,max_rows,max_steps,max_seconds,barcode);cache={};known_choices=set();path_keys=set()
    def size():
        if len(encoded(out))>max_bytes: raise BarcodeQueryError('output-limit')
    def hold(target,reason):
        item=dict(target=target,reason=reason)
        if item not in out['held']:out['held'].append(item)
    def support(kind,payload,scopes):
        if (type(payload) is not dict or payload.get('scope',{}).get('visibility')!='public'
            or type(payload.get('citationIds')) is not list or not payload['citationIds']): return False
        found={}
        for cid in payload['citationIds']:
            if type(cid) is not str:return False
            rows=budget.query('SELECT s.evidence_sha256,c.payload_json FROM gold_support s '
                'JOIN gold_citations c ON c.citation_id=s.citation_id '
                'WHERE s.target_kind=? AND s.target_id=? AND s.citation_id=? AND s.support_scope IN ('+
                ','.join('?' for _ in scopes)+')',(kind,payload.get('id'),cid,*scopes))
            valid=[json.loads(r['payload_json']) for r in rows if _pin(r['evidence_sha256'])
                   and json.loads(r['payload_json']).get('scope',{}).get('visibility')=='public']
            if not valid:return False
            found[cid]=valid[0]
        out['citations'].update(found);return True
    def occurrence_citations(origin):
        payload=json.loads(origin['payload_json'])
        ids=payload.get('citation_ids') if type(payload) is dict else None
        if type(ids) is not list or not ids or any(type(cid) is not str or not cid for cid in ids):return None
        found={}
        for cid in ids:
            value=out['citations'].get(cid)
            if value is None:
                if cid not in budget.citation_rows:
                    budget.citation_rows[cid]=budget.query('SELECT payload_json FROM gold_citations WHERE citation_id=?',(cid,))
                rows=budget.citation_rows[cid]
                if len(rows)!=1:return None
                value=json.loads(rows[0]['payload_json'])
            if (type(value) is not dict or value.get('id')!=cid
                or type(value.get('scope')) is not dict or value['scope'].get('visibility')!='public'
                or any(type(value.get(k)) is not str or not value[k].strip() for k in ('license','attribution'))):
                return None
            found[cid]=value
        return found
    def node(eid):
        if eid in cache:return cache[eid]
        rows=budget.query('SELECT * FROM gold_entities WHERE entity_id=?',(eid,))
        if len(rows)!=1:return None
        e=rows[0];p=json.loads(e['payload_json']);cache[eid]=None
        if e['state']!='verified' or p.get('id')!=e['resource_id'] or not support('resource',p,('record','field')):
            hold(eid,'entity qualification/public scoped support held');return None
        origins=budget.query('SELECT o.* FROM gold_occurrences o JOIN gold_entity_occurrences x '
                             'ON x.occurrence_id=o.occurrence_id WHERE x.entity_id=?',(eid,))
        if not origins or any(o['state']!='verified' for o in origins):
            hold(eid,'source occurrence qualification held');return None
        origin_citations={}
        for origin in origins:
            citations=occurrence_citations(origin)
            if citations is None:
                hold(origin['occurrence_id'],'source occurrence citation provenance held');return None
            origin_citations.update(citations)
        out['citations'].update(origin_citations)
        texts=budget.query('SELECT * FROM gold_texts WHERE entity_id=? AND state=\'verified\'',(eid,))
        names={n.get('id'):n for n in p.get('names',[]) if type(n) is dict}
        qualified=[]
        for text in texts:
            source=names.get(text['source_text_id'],{})
            if (source.get('value')==text['original_text'] and source.get('language')==text['language']
                and source.get('sourceTextSha256')==hashlib.sha256(text['original_text'].encode()).hexdigest()
                and support('text',dict(source,scope=p['scope']),('field','translation'))):qualified.append(text)
        english=[t['english_text'] for t in qualified if type(t['english_text']) is str and t['english_text'].strip()]
        e['payload']=p;e['origins']=origins
        out['entities'][eid]=dict(entityId=eid,resourceId=e['resource_id'],type=e['entity_type'],
            englishNames=english,nameState='present' if english else 'unknown',
            originalResource=p,textRecords=[dict({k:v for k,v in t.items() if k!='evidence_json'},
                                                evidence=json.loads(t['evidence_json'])) for t in qualified],
            sourceRecords=[dict({k:v for k,v in o.items() if k!='payload_json'},
                                payload=json.loads(o['payload_json'])) for o in origins],
            holds=budget.query('SELECT target_kind,target_id,reason FROM gold_holds WHERE target_id IN (?,?)',(eid,e['resource_id'])))
        cache[eid]=e;size();return e
    def relation(row,subject,obj):
        p=json.loads(row['payload_json'])
        try:c=relation_condition(p)
        except (ValueError,TypeError):return False
        return (c is None and row['state']=='verified' and p.get('id')==row['relation_id']
            and p.get('subjectId')==subject['resource_id'] and p.get('objectId')==obj['resource_id']
            and p.get('predicateId')==row['predicate_id'] and support('relation',p,('relationship',)))
    previous_length=db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),1048576))
    try:
        db.set_progress_handler(budget.progress,1)
        claims=budget.query("SELECT * FROM gold_claims WHERE property_id IN ('usda:gtin-upc') "
            "AND json_extract(payload_json,'$.value.kind')='identifier' "
            "AND json_type(payload_json,'$.value.value')='text' AND json_extract(payload_json,'$.value.value')=? COLLATE BINARY",(barcode,))
        matched=set()
        for claim in claims:
            payload=json.loads(claim['payload_json'])
            if selected_product_id is not None and payload.get('subjectId')!=selected_product_id:continue
            product=node(claim['entity_id'])
            if not product:continue
            if product['domain']!='barcodes' or product['entity_type'] not in ('barcode-product','source-reported-barcode-product'):
                hold(claim['assertion_id'],'identifier entity is not a source product');continue
            if selected_product_id is not None and product['resource_id']!=selected_product_id:continue
            if (claim['state']!='verified' or payload.get('subjectId')!=product['resource_id']
                or payload.get('id')!=claim['assertion_id'] or payload.get('propertyId')!=claim['property_id']
                or not support('assertion',payload,('field',))):
                hold(claim['assertion_id'],'identifier scoped assertion held');continue
            if product['entity_id'] in matched:continue
            matched.add(product['entity_id'])
            entry=dict(entityId=product['entity_id'],sourceProductId=product['resource_id'],identifier=payload,
                       nutrition=[],nutritionState='missing',classEdges=[])
            out['products'].append(entry)
            # Nutrition stays attached to this exact source product/claim/context.
            observations=budget.query('SELECT * FROM gold_observations WHERE entity_id=?',(product['entity_id'],))
            for observation in observations:
                if observation['state']!='verified' or observation['kind']!='observed':
                    hold(observation['observation_id'],'source nutrition held');continue
                obsclaims=budget.query('SELECT * FROM gold_claims WHERE claim_id=?',(observation['claim_id'],))
                if len(obsclaims)!=1:continue
                oc=obsclaims[0];op=json.loads(oc['payload_json'])
                metric=budget.query('SELECT * FROM gold_metrics WHERE metric_id=?',(observation['metric_id'],))
                if (oc['state']!='verified' or oc['entity_id']!=product['entity_id']
                    or op.get('subjectId')!=product['resource_id'] or op.get('id')!=oc['assertion_id']
                    or not metric or metric[0]['state']!='verified' or not support('assertion',op,('field',))):
                    hold(observation['observation_id'],'nutrition source claim/metric support held');continue
                definitions=budget.metric_definitions(observation['metric_id'])
                definition_ids=sorted({d['citation_id'] for d in definitions})
                definition_payload=dict(id=observation['metric_id'],citationIds=definition_ids,scope={'visibility':'public'})
                if not definition_ids or not support('metric',definition_payload,('definition',)):
                    hold(observation['observation_id'],'metric definition provenance held');continue
                qualified_definitions=[d for d in definitions if _pin(d['evidence_sha256'])]
                actual=json.loads(observation['context_json'])
                unknown=[k for k in context if actual.get(k) is None]
                mismatch=[k for k,v in context.items() if actual.get(k) is not None and actual[k]!=v]
                entry['nutrition'].append(dict(observation={k:v for k,v in observation.items()
                    if k not in ('context_json','original_json','payload_json')},sourceClaim=op,metric=metric[0],
                    metricDefinitionSupports=qualified_definitions,metricDefinitionCitationIds=definition_ids,
                    context=actual,original=json.loads(observation['original_json']),
                    sourcePayload=json.loads(observation['payload_json']),requestedContext=context,
                    contextState='unknown' if unknown else 'different' if mismatch else 'matches' if context else 'not-requested',
                    unknownContextFields=unknown,differentContextFields=mismatch,aggregation='none'))
            if entry['nutrition']:entry['nutritionState']='source-records-present'
            elif observations:entry['nutritionState']='held'
            classes=budget.query("SELECT * FROM gold_edges WHERE subject_id=? AND predicate_id IN ('represents','contains')",(product['entity_id'],))
            for pe in classes:
                canonical=node(pe['object_id'])
                if not canonical or (canonical['domain'],canonical['entity_type'])!=('ingredients','ingredient') or not relation(pe,product,canonical):
                    hold(pe['relation_id'],'source product/class association held');continue
                entry['classEdges'].append(json.loads(pe['payload_json']))
                maps=budget.query("SELECT * FROM gold_edges WHERE object_id=? AND predicate_id='canonical_ingredient'",(canonical['entity_id'],))
                for ce in maps:
                    mention=node(ce['subject_id'])
                    if not mention or (mention['domain'],mention['entity_type'])!=('ingredients','ingredient-mention'):continue
                    recipes=budget.query("SELECT e.* FROM gold_edges e WHERE object_id=? AND predicate_id='mentions'",(mention['entity_id'],))
                    for me in recipes:
                        recipe=node(me['subject_id'])
                        if not recipe or (recipe['domain'],recipe['entity_type'])!=('recipes','recipe') or not relation(me,recipe,mention):continue
                        scopes={}
                        for origin in recipe['origins']:
                            scope=dict(recipeId=recipe['resource_id'],mentionId=mention['resource_id'],sourceKey=origin['source_key'],
                                sourceVersion=origin['source_version'],recordId=origin['record_id'],contentSha256=origin['content_sha256'])
                            scopes[encoded(scope)]=scope
                        for scope in scopes.values():
                            chosen=[s for s in selections if type(s) is dict and type(s.get('sourceScope')) is dict
                                    and s['sourceScope'].get('recipeId')==recipe['resource_id']]
                            result=lookup_recipe_products(budget,source=scope,selections=chosen)
                            for choice in result['choices']:
                                key=encoded(choice)
                                if key not in known_choices:out['choices'].append(choice);known_choices.add(key)
                            for error in result['errors']:hold(recipe['resource_id'],error)
                            for path in result['paths']:
                                if (path['productId']!=product['resource_id'] or path['mentionId']!=mention['resource_id']
                                    or path['canonicalId']!=canonical['resource_id']):continue
                                if not all(support('relation',p,('relationship',)) for p in path['relations']):continue
                                key=(product['entity_id'],canonical['entity_id'],mention['entity_id'],recipe['entity_id'],encoded(scope))
                                if key in path_keys:continue
                                if len(out['paths'])>=max_paths:raise BarcodeQueryError('path-limit')
                                path_keys.add(key)
                                out['paths'].append(dict(productEntityId=product['entity_id'],canonicalEntityId=canonical['entity_id'],
                                    mentionEntityId=mention['entity_id'],recipeEntityId=recipe['entity_id'],
                                    sourceScope=scope,relations=path['relations']))
                                menu_edges=budget.query("SELECT e.*,m.entity_id menu_id FROM gold_edges e JOIN gold_entities m "
                                    "ON m.entity_id=CASE WHEN e.subject_id=? THEN e.object_id ELSE e.subject_id END "
                                    "WHERE (e.subject_id=? OR e.object_id=?) AND m.entity_type='menu'",(recipe['entity_id'],recipe['entity_id'],recipe['entity_id']))
                                for edge in menu_edges:
                                    menu=node(edge['menu_id'])
                                    if not menu:continue
                                    left,right=(recipe,menu) if edge['subject_id']==recipe['entity_id'] else (menu,recipe)
                                    if relation(edge,left,right):
                                        item=dict(menuEntityId=menu['entity_id'],recipeEntityId=recipe['entity_id'],relation=json.loads(edge['payload_json']))
                                        if item not in out['menus']:out['menus'].append(item)
                                size()
            size()
        out['availability']='ambiguous-source-products' if len(matched)>1 else 'source-product-found' if matched else 'held' if out['held'] else 'no-result'
        if selected_product_id is not None and not matched:hold(selected_product_id,'selected source product not matched; no fallback')
        out['menuData']='relationships-present' if out['menus'] else 'no-qualified-menu-relationships-found'
        out['nutritionState']='source-records-present' if any(p['nutrition'] for p in out['products']) else 'missing' if matched else 'unknown'
        if matched and not any(p['nutrition'] for p in out['products']) and any(p['nutritionState']=='held' for p in out['products']):
            out['nutritionState']='held'
        for product in out['products']:
            product['recipePathState']='qualified-paths-present' if any(p['productEntityId']==product['entityId'] for p in out['paths']) else 'no-qualified-paths'
        out['limits']=dict(maxRows=max_rows,maxPaths=max_paths,maxBytes=max_bytes,maxSteps=max_steps,maxSeconds=max_seconds,
                           rowsRead=max_rows-budget.remaining,sourceBytesRead=budget.bytes_read,maxSourceBytes=8388608,maxCellBytes=1048576)
        if time.monotonic()>budget.deadline:raise BarcodeQueryError('resource-limit')
        size();return out
    except sqlite3.DataError as error:
        raise BarcodeQueryError('source-payload-limit') from error
    except sqlite3.OperationalError as error:
        if 'interrupt' in str(error).lower():raise BarcodeQueryError('resource-limit') from error
        raise BarcodeQueryError('snapshot-query-error') from error
    finally:
        db.set_progress_handler(None,0)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,previous_length)


def _file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def query_snapshot(admission_path,admission_sha256,barcode,**kwargs):
    """Caller selects the receipt/hash; never discover or silently choose a DB."""
    receipt_path=Path(admission_path)
    # Hash and parse one bounded byte buffer. A replaced path cannot switch the
    # selected artifact/notice between separate receipt opens.
    with receipt_path.open('rb') as stream:
        receipt_bytes=stream.read(1048577)
    if (not _pin(admission_sha256) or len(receipt_bytes)>1048576
        or hashlib.sha256(receipt_bytes).hexdigest()!=admission_sha256):
        raise BarcodeQueryError('admission-pin-mismatch')
    receipt=json.loads(receipt_bytes)
    if type(receipt) is not dict:raise BarcodeQueryError('admission-not-selected')
    artifact=receipt.get('artifact',{})
    if (type(artifact) is not dict or not str(receipt.get('state','')).startswith('ACCEPTED_')
        or not _pin(artifact.get('sha256')) or type(artifact.get('path')) is not str):
        raise BarcodeQueryError('admission-not-selected')
    path=Path(artifact.get('path',''))
    if not path.is_absolute() or path.stat().st_size>1073741824 or _file_sha(path)!=artifact['sha256']:raise BarcodeQueryError('database-pin-mismatch')
    before_sidecars={s:Path(str(path)+s).exists() for s in ('-wal','-shm','-journal')}
    if any(before_sidecars.values()):raise BarcodeQueryError('frozen-snapshot-required')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        result=read_barcode(db,barcode,selection=SnapshotSelection(artifact['sha256'],admission_sha256),**kwargs)
    result['admissionNotice']=receipt
    if len(encoded(result))>kwargs.get('max_bytes',262144):raise BarcodeQueryError('output-limit')
    if _file_sha(path)!=artifact['sha256'] or any(Path(str(path)+s).exists() for s in before_sidecars):
        raise BarcodeQueryError('snapshot-changed')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--admission',required=True);p.add_argument('--admission-sha256',required=True)
    p.add_argument('--barcode',required=True);p.add_argument('--selected-product-id')
    p.add_argument('--selections-json',default='[]');p.add_argument('--context-json',default='{}')
    p.add_argument('--max-rows',type=int,default=10000);p.add_argument('--max-paths',type=int,default=50)
    p.add_argument('--max-bytes',type=int,default=262144);p.add_argument('--max-steps',type=int,default=1000000)
    p.add_argument('--max-seconds',type=float,default=3)
    a=p.parse_args()
    try:
        result=query_snapshot(a.admission,a.admission_sha256,a.barcode,selections=json.loads(a.selections_json),
            requested_context=json.loads(a.context_json),selected_product_id=a.selected_product_id,
            max_rows=a.max_rows,max_paths=a.max_paths,max_bytes=a.max_bytes,max_steps=a.max_steps,max_seconds=a.max_seconds)
        print(encoded(result).decode())
    except (BarcodeQueryError,ValueError,OSError) as e:
        print(encoded(dict(error=str(e),status='error')).decode());return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
