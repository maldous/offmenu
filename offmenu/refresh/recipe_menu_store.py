"""Bounded LOCAL source-faithful recipe/menu writer for13's exact schema.

57 supplies the pinned existing parser1.3.3 and held-FD onepass caller.
No fetching, new parser, semantic normalization or existing-store mutation.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, math, re, sqlite3, time
from pathlib import Path
from .core import canonical, strict_json, RefreshError
VERSION='offmenu-recipe-menu-source-store/1'
PARSER_VERSION='offmenu-source-faithful-recipe-parser/1.3.3'
PARSER_SHA256='b6b86c9ec8c4cb7446229ead1bf1ae00136631c82e492445505a574b2203658d'
SCHEMA_SHA256='9a863b44edc8a829c988304c284fe017cb916513f20249f5c5b08423e738198c'
DDL="-- Import key clarification11502: same13tables, asset-scoped ordinal uniqueness; NEW STORE ONLY.\n-- SOURCE-ONLY contract for NEW separate private recipe/menu store; NOT executed.\n-- No changes to existing identifier/ingredient/account DBs. No meal-plan mutation.\nCREATE TABLE recipe_store_release(\n store_release_id TEXT PRIMARY KEY NOT NULL,\n input_manifest_sha256 TEXT NOT NULL,\n parser_id TEXT NOT NULL, parser_version TEXT NOT NULL, parser_code_sha256 TEXT NOT NULL,\n state TEXT NOT NULL CHECK(state IN ('prepared','loading','incomplete','completed','failed')),\n expected_records INTEGER CHECK(expected_records>=0),\n observed_records INTEGER CHECK(observed_records>=0),\n exception_count INTEGER CHECK(exception_count>=0),\n created_at TEXT NOT NULL, completed_at TEXT\n);\nCREATE TABLE recipe_citation_ref(\n citation_id TEXT PRIMARY KEY NOT NULL, asset_id TEXT,\n identity_state TEXT NOT NULL, owner19_receipt_pointer TEXT,\n owner19_receipt_sha256 TEXT, unknown_reason TEXT\n);\nCREATE TABLE recipe_source_record(\n source_record_key TEXT PRIMARY KEY NOT NULL,\n store_release_id TEXT NOT NULL REFERENCES recipe_store_release(store_release_id),\n source_id TEXT NOT NULL, release_id TEXT NOT NULL, native_record_id TEXT,\n source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),\n source_asset_sha256 TEXT NOT NULL, parsed_record_sha256 TEXT NOT NULL,\n record_pointer TEXT NOT NULL, citation_id TEXT REFERENCES recipe_citation_ref(citation_id),\n source_payload_json TEXT NOT NULL,\n operation_state TEXT NOT NULL,\n UNIQUE(store_release_id,source_id,release_id,source_asset_sha256,source_ordinal)\n);\nCREATE TABLE dish_concept_ref(\n dish_concept_id TEXT PRIMARY KEY NOT NULL, identity_state TEXT NOT NULL,\n evidence_pointer TEXT NOT NULL, evidence_sha256 TEXT NOT NULL\n);\nCREATE TABLE source_recipe_variant(\n recipe_variant_id TEXT PRIMARY KEY NOT NULL,\n source_record_key TEXT NOT NULL REFERENCES recipe_source_record(source_record_key),\n dish_concept_id TEXT REFERENCES dish_concept_ref(dish_concept_id),\n original_title TEXT, language TEXT NOT NULL, language_state TEXT NOT NULL,\n yield_raw_text TEXT, yield_value_lexeme TEXT, yield_unit_lexeme TEXT,\n yield_interpreted_value REAL, yield_interpreted_unit TEXT, yield_interpretation_status TEXT NOT NULL,\n dictionary_version TEXT, mapping_version TEXT,\n ingredient_extraction_state TEXT NOT NULL,\n step_extraction_state TEXT NOT NULL, source_location_json TEXT NOT NULL\n);\nCREATE TABLE recipe_region_assertion(\n assertion_id TEXT PRIMARY KEY NOT NULL,\n recipe_variant_id TEXT NOT NULL REFERENCES source_recipe_variant(recipe_variant_id),\n region_identifier TEXT, original_region_text TEXT, assertion_state TEXT NOT NULL,\n source_pointer TEXT NOT NULL, evidence_sha256 TEXT NOT NULL\n);\nCREATE TABLE recipe_ingredient_line(\n ingredient_line_id TEXT PRIMARY KEY NOT NULL,\n recipe_variant_id TEXT NOT NULL REFERENCES source_recipe_variant(recipe_variant_id),\n line_order INTEGER NOT NULL CHECK(line_order>=0), component_index INTEGER,\n source_name_text TEXT, original_expression TEXT NOT NULL,\n raw_value_lexeme TEXT, raw_unit_lexeme TEXT,\n interpreted_value REAL, interpreted_unit TEXT, interpretation_status TEXT NOT NULL,\n preparation_descriptors_json TEXT NOT NULL, substitution_text TEXT,\n alternatives_json TEXT NOT NULL, optional_text TEXT,\n ingredient_concept_id TEXT, ingredient_registry_sha256 TEXT,\n food_match_status TEXT NOT NULL, mapping_decision_id TEXT, mapping_decision_version TEXT,\n source_location_json TEXT NOT NULL,\n UNIQUE(recipe_variant_id,line_order)\n);\nCREATE TABLE recipe_ordered_step(\n step_id TEXT PRIMARY KEY NOT NULL,\n recipe_variant_id TEXT NOT NULL REFERENCES source_recipe_variant(recipe_variant_id),\n step_order INTEGER NOT NULL CHECK(step_order>=0), component_index INTEGER,\n original_text TEXT NOT NULL,\n action_terms_json TEXT NOT NULL, equipment_json TEXT NOT NULL,\n time_json TEXT NOT NULL, temperature_json TEXT NOT NULL, target_state_json TEXT NOT NULL,\n source_location_json TEXT NOT NULL,\n UNIQUE(recipe_variant_id,step_order)\n);\nCREATE TABLE source_menu(\n menu_id TEXT PRIMARY KEY NOT NULL,\n source_record_key TEXT NOT NULL REFERENCES recipe_source_record(source_record_key),\n original_title TEXT, language TEXT NOT NULL,\n venue_source_reference TEXT, observed_at TEXT,\n observation_state TEXT NOT NULL, source_location_json TEXT NOT NULL\n);\nCREATE TABLE source_menu_item(\n menu_item_id TEXT PRIMARY KEY NOT NULL,\n source_record_key TEXT NOT NULL REFERENCES recipe_source_record(source_record_key),\n original_item_name TEXT NOT NULL, original_description TEXT,\n language TEXT NOT NULL, venue_source_reference TEXT,\n price_lexeme TEXT, price_value REAL, currency TEXT, price_state TEXT NOT NULL,\n source_category_text TEXT, source_location_json TEXT NOT NULL\n);\nCREATE TABLE menu_entry(\n menu_id TEXT NOT NULL REFERENCES source_menu(menu_id),\n menu_item_id TEXT NOT NULL REFERENCES source_menu_item(menu_item_id),\n entry_order INTEGER NOT NULL CHECK(entry_order>=0),\n PRIMARY KEY(menu_id,entry_order)\n);\nCREATE TABLE menu_recipe_candidate(\n menu_item_id TEXT NOT NULL REFERENCES source_menu_item(menu_item_id),\n recipe_variant_id TEXT NOT NULL REFERENCES source_recipe_variant(recipe_variant_id),\n relationship_status TEXT NOT NULL,\n decision_id TEXT NOT NULL, decision_version TEXT NOT NULL,\n evidence_pointer TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,\n PRIMARY KEY(menu_item_id,recipe_variant_id,decision_id,decision_version)\n);\nCREATE TABLE recipe_store_exception(\n store_release_id TEXT NOT NULL REFERENCES recipe_store_release(store_release_id),\n exception_ordinal INTEGER NOT NULL CHECK(exception_ordinal>=1),\n source_record_key TEXT REFERENCES recipe_source_record(source_record_key),\n source_pointer TEXT, reason_code TEXT NOT NULL, disposition TEXT NOT NULL,\n PRIMARY KEY(store_release_id,exception_ordinal)\n);\nCREATE INDEX recipe_source_lookup ON recipe_source_record(source_id,release_id,native_record_id);\nCREATE INDEX recipe_title_page ON source_recipe_variant(original_title COLLATE BINARY,recipe_variant_id);\nCREATE INDEX recipe_line_order ON recipe_ingredient_line(recipe_variant_id,line_order);\nCREATE INDEX recipe_step_order ON recipe_ordered_step(recipe_variant_id,step_order);\nCREATE INDEX recipe_concept_usage ON recipe_ingredient_line(ingredient_concept_id,recipe_variant_id);\nCREATE INDEX menu_item_name ON source_menu_item(original_item_name COLLATE BINARY,menu_item_id);\nCREATE VIEW v_recipe_inspection AS\nSELECT r.recipe_variant_id,r.original_title,r.language,r.language_state,\n r.dish_concept_id,r.yield_raw_text,r.yield_value_lexeme,r.yield_unit_lexeme,\n r.yield_interpreted_value,r.yield_interpreted_unit,r.yield_interpretation_status,\n r.ingredient_extraction_state,r.step_extraction_state,\n s.source_id,s.release_id,s.native_record_id,s.source_ordinal,s.citation_id,\n s.source_asset_sha256,s.parsed_record_sha256,s.record_pointer,s.operation_state\nFROM source_recipe_variant r JOIN recipe_source_record s USING(source_record_key);\nCREATE VIEW v_menu_item_inspection AS\nSELECT m.menu_item_id,m.original_item_name,m.original_description,m.language,\n m.venue_source_reference,m.price_lexeme,m.price_value,m.currency,m.price_state,\n m.source_category_text,s.source_id,s.release_id,s.citation_id,s.record_pointer\nFROM source_menu_item m JOIN recipe_source_record s USING(source_record_key);\n"

@dataclass(frozen=True)
class StoreLimits:
    max_input_bytes:int
    max_assets:int
    max_records_per_asset:int
    max_parsed_bytes:int
    max_lines_per_record:int
    max_steps_per_record:int
    max_database_bytes:int
    max_storage_bytes:int
    max_seconds:int


def _fail(code):raise RefreshError('recipe-store-'+code)
def _sha(v):return type(v)is str and re.fullmatch('[0-9a-f]{64}',v)is not None
def _hash(v):return hashlib.sha256(canonical(v)).hexdigest()
def _id(kind,*v):return 'urn:offmenu:'+kind+':'+_hash(list(v))
def _text(v):
    if v is not None and type(v)is not str:_fail('text-type')
    return v
def _number(v):
    if v is not None and (type(v)not in(int,float) or not math.isfinite(v)):_fail('number-type')
    return v
def _put(db,table,row):
    # Table/column names below are fixed author code, never source SQL.
    db.execute('INSERT INTO '+table+'('+','.join(row)+') VALUES('+','.join('?'*len(row))+')',tuple(row.values()))


def prepare_recipe_menu(assets):
    if type(assets)not in(tuple,list) or not 1<=len(assets)<=256:_fail('asset-inventory')
    rows=[];seen=set()
    for asset in assets:
        a=strict_json(canonical(asset))
        if (type(a)is not dict or any(type(a.get(k))is not str or not a[k] for k in
                ('sourceId','sourceRecordId','inputPath','release')) or a.get('recordKind')not in('recipe','menuItem')
                or not Path(a['inputPath']).is_absolute() or not _sha(a.get('inputSHA256'))
                or type(a.get('inputBytes'))is not int or not 0<a['inputBytes']<=2097152):_fail('asset-binding')
        # Match13's persisted asset/ordinal uniqueness; aliases or kinds cannot
        # select the same source/release/blob twice in one store generation.
        key=_id('asset',a['sourceId'],a['release'],a['inputSHA256'])
        if key in seen:_fail('duplicate-selected-asset')
        seen.add(key);rows.append(a)
    result={'version':VERSION,'schemaSha256':SCHEMA_SHA256,'parserVersion':PARSER_VERSION,
            'parserCodeSha256':PARSER_SHA256,'assets':rows,'scope':'exact selected LOCAL assets; source-faithful only'}
    if len(canonical(result))>1024**2:_fail('manifest-bound')
    return result


def _exception(db,run,key,pointer,code,disposition='unresolved'):
    ordinal=db.execute('SELECT coalesce(max(exception_ordinal),0)+1 FROM recipe_store_exception WHERE store_release_id=?',(run,)).fetchone()[0]
    _put(db,'recipe_store_exception',dict(store_release_id=run,exception_ordinal=ordinal,source_record_key=key,source_pointer=pointer,reason_code=code,disposition=disposition))


def _project_recipe(db,key,record,limits,run):
    lines=record.get('ingredientLines',[]);steps=record.get('orderedSteps',[])
    if (type(lines)is not list or type(steps)is not list or len(lines)>limits.max_lines_per_record
            or len(steps)>limits.max_steps_per_record):_fail('record-collection-bound')
    variant=_id('source-recipe',key);language=_text(record.get('language'))or'und';y=record.get('yield')
    if y is not None and type(y)is not dict:_fail('yield-type')
    y=y or{}
    _put(db,'source_recipe_variant',dict(recipe_variant_id=variant,source_record_key=key,dish_concept_id=None,
        original_title=_text(record.get('originalTitle')),language=language,language_state='unknown'if language=='und'else'source-parser-language; content-unverified',
        yield_raw_text=_text(y.get('rawText')),yield_value_lexeme=_text(y.get('rawValueLexeme')),yield_unit_lexeme=_text(y.get('rawUnitLexeme')),
        yield_interpreted_value=_number(y.get('interpretedValue')),yield_interpreted_unit=_text(y.get('interpretedUnit')),
        yield_interpretation_status=y.get('interpretationStatus','missing'),dictionary_version=_text(record.get('dictionaryVersion')),
        mapping_version=_text(record.get('mappingVersion')),ingredient_extraction_state='parsed'if lines else'missing',
        step_extraction_state='parsed'if steps else'missing',source_location_json=canonical(record.get('sourceLocation')).decode()))
    region=record.get('region')
    if region is not None:_put(db,'recipe_region_assertion',dict(assertion_id=_id('source-recipe-region',key),recipe_variant_id=variant,
        region_identifier=None,original_region_text=region if type(region)is str else canonical(region).decode(),
        assertion_state='source-asserted; identifier-unresolved',source_pointer='/region',evidence_sha256=_hash(record)))
    if not lines:_exception(db,run,key,'/ingredientLines','ingredient-lines-missing')
    if not steps:_exception(db,run,key,'/orderedSteps','directions-missing')
    line_orders=[line.get('order')if type(line)is dict else None for line in lines]
    step_orders=[step.get('order')if type(step)is dict else None for step in steps]
    keep_line_orders=all(type(o)is int and o>=0 for o in line_orders)and len(set(line_orders))==len(line_orders)
    keep_step_orders=all(type(o)is int and o>=0 for o in step_orders)and len(set(step_orders))==len(step_orders)
    for index,line in enumerate(lines,1):
        if type(line)is not dict or type(line.get('originalExpression'))is not str:_fail('ingredient-line-type')
        q=line.get('quantity')or{}
        if type(q)is not dict:_fail('quantity-type')
        _put(db,'recipe_ingredient_line',dict(ingredient_line_id=_id('source-recipe-line',variant,line.get('ingredientLineId'),index),
            recipe_variant_id=variant,line_order=line_orders[index-1]if keep_line_orders else index,component_index=line.get('componentIndex'),source_name_text=_text(line.get('sourceNameText')),
            original_expression=line['originalExpression'],raw_value_lexeme=_text(q.get('rawValueLexeme')),raw_unit_lexeme=_text(q.get('rawUnitLexeme')),
            interpreted_value=_number(q.get('interpretedValue')),interpreted_unit=_text(q.get('interpretedUnit')),
            interpretation_status=q.get('interpretationStatus','missing'),preparation_descriptors_json=canonical(line.get('preparationDescriptors',[])).decode(),
            substitution_text=_text(line.get('substitutionText')),alternatives_json=canonical(line.get('alternatives',[])).decode(),optional_text=_text(line.get('optionalText')),
            ingredient_concept_id=None,ingredient_registry_sha256=None,food_match_status='pending',mapping_decision_id=None,mapping_decision_version=None,
            source_location_json=canonical({'location':line.get('location'),'parserOrder':line.get('order'),'componentIndex':line.get('componentIndex'),'ingredientLineId':line.get('ingredientLineId')}).decode()))
    for index,step in enumerate(steps,1):
        if type(step)is not dict or type(step.get('originalText'))is not str:_fail('step-type')
        _put(db,'recipe_ordered_step',dict(step_id=_id('source-recipe-step',variant,step.get('componentIndex'),index),recipe_variant_id=variant,
            step_order=step_orders[index-1]if keep_step_orders else index,component_index=step.get('componentIndex'),original_text=step['originalText'],action_terms_json=canonical(step.get('actionTerms',[])).decode(),
            equipment_json=canonical(step.get('equipment',[])).decode(),time_json=canonical(step.get('time')).decode(),temperature_json=canonical(step.get('temperature')).decode(),
            target_state_json=canonical(step.get('targetState')).decode(),source_location_json=canonical({'location':step.get('location'),'parserOrder':step.get('order'),'componentIndex':step.get('componentIndex')}).decode()))
    return variant


def _project_menu_item(db,key,record):
    name=record.get('originalItemName')
    if type(name)is not str or not name:_fail('menu-name')
    price=record.get('price')or{}
    if type(price)is not dict:_fail('price-type')
    item=_id('source-menu-item',key)
    _put(db,'source_menu_item',dict(menu_item_id=item,source_record_key=key,original_item_name=name,
        original_description=_text(record.get('originalDescription')),language=_text(record.get('language'))or'und',
        venue_source_reference=canonical(record.get('venue')).decode()if record.get('venue')is not None else None,
        price_lexeme=_text(price.get('rawValue')),price_value=_number(price.get('interpretedValue')),currency=_text(record.get('currency')),
        price_state=price.get('interpretationStatus','missing'),source_category_text=_text(record.get('sourceCategory')),
        source_location_json=canonical(record.get('location')).decode()))
    return item


def _citation(db,asset):
    binding=asset.get('citationBinding')
    if not binding:return None
    citation=binding['fetch_citation'];a=binding['fetch_asset'];key=citation['citation_id']
    if (a['original_sha256']!=asset['inputSHA256'] or a['original_bytes']!=asset['inputBytes']or a['citation_id']!=key):_fail('citation-asset-binding')
    row=dict(citation_id=key,asset_id=a['asset_id'],identity_state=citation['identity_state'],
             owner19_receipt_pointer=citation.get('metadata_origin_pointer'),owner19_receipt_sha256=citation.get('fetch_receipt_sha256'),
             unknown_reason=citation.get('unknown_fields_json'))
    old=db.execute('SELECT * FROM recipe_citation_ref WHERE citation_id=?',(key,)).fetchone()
    if old is None:_put(db,'recipe_citation_ref',row)
    elif tuple(row.values())!=tuple(old):_fail('citation-conflict')
    return key


def ingest_recipe_menu(db,assets,*,parser_module,parse_asset_once,limits,run_id,input_manifest_sha256,selection_receipt_sha256):
    """Runnable source import;57's actual held-FD callback alone opens originals."""
    manifest=prepare_recipe_menu(assets)
    if (type(db)is not sqlite3.Connection or type(limits)is not StoreLimits
            or any(type(v)is not int or not 0<v<2**63 for v in asdict(limits).values())
            or not _sha(selection_receipt_sha256)or input_manifest_sha256!=_hash(manifest)
            or type(run_id)is not str or not 0<len(run_id)<=256 or not callable(parse_asset_once)):_fail('selection-or-limits')
    if len(assets)>limits.max_assets or sum(a['inputBytes']for a in assets)>limits.max_input_bytes:_fail('input-manifest-bound')
    if getattr(parser_module,'PARSER_VERSION',None)!=PARSER_VERSION or hashlib.sha256(Path(parser_module.__file__).read_bytes()).hexdigest()!=PARSER_SHA256:_fail('parser-code-pin')
    if db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') LIMIT 1").fetchone():_fail('new-empty-store-required')
    started=time.monotonic()
    def check():
        if time.monotonic()-started>=limits.max_seconds:_fail('time-bound')
    db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA temp_store=MEMORY');db.execute('PRAGMA cache_size=-8192');db.execute('PRAGMA mmap_size=0');db.execute('PRAGMA synchronous=FULL')
    page=db.execute('PRAGMA page_size').fetchone()[0];db.execute('PRAGMA max_page_count='+str(max(1,limits.max_database_bytes//page)))
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,min(2**31-1,limits.max_parsed_bytes));db.set_progress_handler(lambda:int(time.monotonic()-started>=limits.max_seconds),1000)
    results=[];total_bytes=0;initialized=False
    try:
        db.executescript(DDL);now=datetime.now(timezone.utc).isoformat()
        _put(db,'recipe_store_release',dict(store_release_id=run_id,input_manifest_sha256=input_manifest_sha256,parser_id=PARSER_VERSION,
            parser_version=PARSER_VERSION,parser_code_sha256=PARSER_SHA256,state='loading',expected_records=None,observed_records=0,exception_count=0,created_at=now,completed_at=None));db.commit()
        initialized=True
        for asset in manifest['assets']:
            verified=False
            try:
                check();records,receipt=parse_asset_once(asset,parser_module);check()
                if (type(records)is not list or not 1<=len(records)<=limits.max_records_per_asset or type(receipt)is not dict
                        or receipt.get('inputSHA256')!=asset['inputSHA256']or receipt.get('inputBytes')!=asset['inputBytes']
                        or receipt.get('parserVersion')!=PARSER_VERSION or receipt.get('EOFFullyVerified')is not True
                        or type(receipt.get('bodyPasses'))is not int or receipt['bodyPasses']!=1
                        or type(receipt.get('records'))is not int or receipt['records']!=len(records)):_fail('parser-receipt')
                verified=True;encoded=canonical(records);total_bytes+=len(encoded)
                if total_bytes>limits.max_parsed_bytes:_fail('parsed-byte-bound')
                db.execute('BEGIN IMMEDIATE');citation=_citation(db,asset);menu=None
                for index,record in enumerate(records,1):
                    check();source=record.get('source',{})if type(record)is dict else{}
                    template,version,other=('recipeTemplate',parser_module.RECIPE_TEMPLATE_VERSION,'menuTemplate')if asset['recordKind']=='recipe'else('menuTemplate',parser_module.MENU_TEMPLATE_VERSION,'recipeTemplate')
                    if type(record)is not dict or record.get(template)!=version or other in record:_fail('parsed-record-kind')
                    if (source.get('sourceId')!=asset['sourceId']or source.get('releaseId')!=asset['release']
                            or(asset['recordKind']=='recipe'and source.get('sourceRecordId')!=asset['sourceRecordId'])
                            or source.get('originalSHA256')!=asset['inputSHA256']or source.get('extractionParser')!=PARSER_VERSION):_fail('parsed-source-binding')
                    native=_text(source.get('sourceRecordId'));key=_id('recipe-source',asset['sourceId'],asset['release'],asset['inputSHA256'],asset['recordKind'],native,index)
                    _put(db,'recipe_source_record',dict(source_record_key=key,store_release_id=run_id,source_id=asset['sourceId'],release_id=asset['release'],native_record_id=native,
                        source_ordinal=index,source_asset_sha256=asset['inputSHA256'],parsed_record_sha256=_hash(record),record_pointer='',citation_id=citation,
                        source_payload_json=canonical(record).decode(),operation_state='local-private-source-faithful; semantic-links-pending'))
                    if asset['recordKind']=='recipe':_project_recipe(db,key,record,limits,run_id)
                    else:
                        item=_project_menu_item(db,key,record)
                        if menu is None:
                            menu=_id('source-menu',asset['sourceId'],asset['release'],asset['inputSHA256'])
                            _put(db,'source_menu',dict(menu_id=menu,source_record_key=key,original_title=None,language=_text(record.get('language'))or'und',
                                venue_source_reference=canonical(record.get('venue')).decode()if record.get('venue')is not None else None,
                                observed_at=None,observation_state='source-asset parser-item collection; observation-date unknown',
                                source_location_json=canonical({'assetSHA256':asset['inputSHA256'],'scope':'selected source parser menu-item collection'}).decode()))
                        _put(db,'menu_entry',dict(menu_id=menu,menu_item_id=item,entry_order=index))
                if db.execute('PRAGMA foreign_key_check').fetchone():_fail('foreign-key')
                asset_exceptions=db.execute('SELECT count(*) FROM recipe_store_exception e JOIN recipe_source_record s USING(source_record_key) WHERE s.source_id=? AND s.release_id=? AND s.source_asset_sha256=?',
                    (asset['sourceId'],asset['release'],asset['inputSHA256'])).fetchone()[0]
                db.commit()
                results.append({'sourceId':asset['sourceId'],'sourceRecordId':asset['sourceRecordId'],'inputSHA256':asset['inputSHA256'],
                    'inputBytes':asset['inputBytes'],'recordKind':asset['recordKind'],'parsedRecords':len(records),'loadedRecords':len(records),'exceptions':asset_exceptions,'receipt':receipt})
            except BaseException as error:
                # Failure bookkeeping must work even when this deadline expired.
                db.set_progress_handler(None,0)
                db.rollback();code=str(error)if type(error)is RefreshError and re.fullmatch('[a-z0-9-]+',str(error))else'parser-or-projection-failure'
                _exception(db,run_id,None,'asset:'+asset['inputSHA256'],code,'held')
                observed=db.execute('SELECT count(*) FROM recipe_source_record').fetchone()[0];exceptions=db.execute('SELECT count(*) FROM recipe_store_exception').fetchone()[0]
                db.execute('UPDATE recipe_store_release SET state=?,observed_records=?,exception_count=? WHERE store_release_id=?',('incomplete',observed,exceptions,run_id));db.commit()
                error.recipe_store_retained_state={'completeReceiptReturned':False,'assetSHA256':asset['inputSHA256'],'assetEOFVerified':verified,
                    'completedAssets':results,'sourceRowsRetained':observed,'automaticRetry':False,'automaticDeletion':False}
                raise
        check()
        tables=('recipe_source_record','source_recipe_variant','recipe_ingredient_line','recipe_ordered_step','source_menu','source_menu_item','menu_entry','recipe_region_assertion','recipe_store_exception','dish_concept_ref','menu_recipe_candidate')
        counts={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0]for table in tables}
        if (counts['recipe_source_record']!=sum(r['loadedRecords']for r in results)or counts['recipe_source_record']!=counts['source_recipe_variant']+counts['source_menu_item']
                or db.execute('PRAGMA quick_check').fetchone()!=('ok',)or db.execute('PRAGMA foreign_key_check').fetchone()):_fail('final-reconciliation')
        db.execute('UPDATE recipe_store_release SET state=?,observed_records=?,exception_count=?,completed_at=? WHERE store_release_id=?',
            ('completed',counts['recipe_source_record'],counts['recipe_store_exception'],datetime.now(timezone.utc).isoformat(),run_id));db.commit()
        check()
        return {'version':VERSION,'inputManifestSha256':input_manifest_sha256,'assets':results,'tableCounts':counts,
                'expectedAssets':len(assets),'verifiedAssets':len(results),'unreadAssets':0,'parsedBytes':total_bytes,
                'sourceImportComplete':True,'canonicalIngredientLinks':'NULL/pending','accepted':False,'runtimeOrResourcesAdmitted':False,
                'publication':'caller57 must close/fsync/hash/check custody and select output receipt; source load is not a release/country completion'}
    except BaseException as error:
        db.set_progress_handler(None,0)
        if not hasattr(error,'recipe_store_retained_state'):
            db.rollback();observed=0;committed=[]
            if initialized:
                code=str(error)if type(error)is RefreshError and re.fullmatch('[a-z0-9-]+',str(error))else'finalization-failure'
                _exception(db,run_id,None,'store:'+run_id,code,'held')
                observed=db.execute('SELECT count(*) FROM recipe_source_record').fetchone()[0]
                exceptions=db.execute('SELECT count(*) FROM recipe_store_exception').fetchone()[0]
                committed=[dict(sourceId=r[0],releaseId=r[1],inputSHA256=r[2],records=r[3])for r in db.execute(
                    'SELECT source_id,release_id,source_asset_sha256,count(*) FROM recipe_source_record GROUP BY source_id,release_id,source_asset_sha256')]
                db.execute('UPDATE recipe_store_release SET state=?,observed_records=?,exception_count=?,completed_at=NULL WHERE store_release_id=?',
                    ('incomplete',observed,exceptions,run_id));db.commit()
            error.recipe_store_retained_state={'completeReceiptReturned':False,'failurePhase':'finalization'if initialized else'initialization',
                'assetSHA256':None,'assetEOFVerified':None,
                'completedAssets':results,'committedAssetCounts':committed,'sourceRowsRetained':observed,'automaticRetry':False,'automaticDeletion':False}
        raise
    finally:
        db.set_progress_handler(None,0)
