"""Read-only adapters for the acquired CNOUS/Begles/Toulouse artifacts.

No network, source execution, linked-PDF loading, translation, food matching or
recipe inference. Municipal field IDs are documented in endpoint-ready.json.
CNOUS shape is supported by the pinned ESUP primary XML mapping and tested on
generated examples, never represented as reviewed raw-feed samples.
All source objects remain in private staging; diagnostics expose fixed codes only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
from xml.parsers import expat

from ingest_api import BudgetExceeded, COUNTERS, SourceChanged, source_key
from ingest_recipes import _open, _identity, _JSONStream, _strict, MalformedRecord, UnsupportedSource

VERSION = 'offmenu-acquired-menu-ingest/1'
ADAPTER_VERSION = VERSION
CNOUS_SCHEMA_URL = 'https://github.com/EsupPortail/esup-dining/blob/733e47d9365ab7f604c0085ed4dae4ef66e713c3/src/main/resources/schema/portlet.xsl'
FAMILIES = frozenset(('fr_cnous_menus', 'fr_begles_menus', 'fr_toulouse_menus'))
ROLES = frozenset(('menu', 'dish', 'ingredient', 'technical_sheet_reference'))
REASONS = frozenset(('acquired_menu_schema_unknown', 'acquired_menu_required_field_missing',
    'acquired_menu_record_not_object', 'acquired_menu_unsupported_role',
    'acquired_menu_unsupported_format', 'acquired_menu_csv_duplicate_header',
    'acquired_menu_csv_row_width', 'acquired_menu_xml_dtd_forbidden',
    'acquired_menu_xml_entity_forbidden', 'acquired_menu_xml_invalid',
    'acquired_menu_xml_depth_cap', 'acquired_menu_xml_record_cap',
    'acquired_menu_xml_no_menu_nodes', 'acquired_menu_ambiguous_join_scope',
    'acquired_menu_reference_without_native_id', 'acquired_menu_source_error',
    'acquired_menu_encoding_invalid', 'acquired_menu_csv_invalid',
    'acquired_menu_source_size_cap', 'acquired_menu_acquisition_unverified',
    'acquired_menu_json_record_invalid', 'acquired_menu_json_line_cap',
    'acquired_menu_json_framing_invalid'))
ALLERGEN_FIELDS = ('arachide', 'ovoproduit', 'lait', 'mollusques', 'gluten',
    'fruits_a_coque', 'sulfites', 'crustaces', 'sesame', 'lupin', 'poisson',
    'soja', 'celeri', 'moutarde')


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _present(value):
    return value is not None and value != ''


def _family(source):
    family = source.get('acquired_adapter')
    if family not in FAMILIES:
        raise UnsupportedSource('acquired_menu_schema_unknown')
    return family


def entity_id(source, kind, native_id, scope=None):
    """Exact, type-preserving, provider-scoped native relation target.

    No case folding, trimming, suffix stripping or numeric/string coercion.
    Scope is mandatory for publisher-local Bordeaux codes and CROUS feeds.
    """
    return kind + ':' + _hash([_family(source), scope, native_id])


def _scope(source, row):
    if _family(source) == 'fr_begles_menus':
        # Menu and composition prefixes differ, but the same two native SIRETs
        # establish the publication namespace. Missing scope is NOT a wildcard.
        prefix = 'menu' if source['acquired_role'] == 'menu' else 'plat'
        coll = row.get(prefix + 'collsiret')
        establishment = row.get(prefix + 'etablissementsiret')
        return [coll, establishment] if _present(coll) and _present(establishment) else None
    if _family(source) == 'fr_cnous_menus':
        return source.get('resource_id') or source.get('artifact_name') or source['id']
    return None


def _provenance(source, pointer):
    return {'source_id': _family(source), 'catalog_source_id': source['id'],
            'provider': source.get('provider'), 'source_url': source.get('source_url'),
            'source_revision': source.get('source_revision'), 'resource_id': source.get('resource_id'),
            'artifact_name': source.get('artifact_name'), 'sha256': source.get('sha256'),
            'license': source.get('license'), 'custody': source.get('custody'),
            'acquisition': (source.get('metadata') or {}).get('acquisition'),
            'pointer': pointer, 'adapter_version': VERSION,
            'schema_evidence': 'ESUP-Portail-primary-XML-mapping; generated-tests; Foo-full-snapshot-not-reviewed'
                if _family(source) == 'fr_cnous_menus' else 'primary-api-observed-field-ids'}


def _relation(kind, domain, target, **detail):
    return {'kind': kind, 'target_domain': domain, 'target_id': target, **detail}


def _native_relation(source, kind, domain, target_kind, native, scope=None):
    return _relation(kind, domain, entity_id(source,target_kind,native,scope),
        target_identity_kind='acquired_scoped_id', target_source_policy='selected_family',
        target_adapter=_family(source), target_scope=scope, target_native_id=native,
        join_status='exact-native-key-target-presence-not-verified')


def _base(source, row, pointer, kind, native=None, identity=None, raw_json=None):
    return {'id': identity or kind + ':' + _hash([_family(source), source.get('artifact_name'), pointer, row]),
            'kind': kind, 'source_native_id': native, 'source_family': _family(source), 'language': 'fr',
            'raw_source': row, 'raw_source_json': raw_json,
            'provenance': _provenance(source, pointer), 'relations': [],
            'normalization_performed': False, 'translation_performed': False}


def _anchor(source, kind, native, scope=None, **fields):
    # Anchors contain no row-specific state; every observation links separately.
    return {'id': entity_id(source, kind, native, scope), 'kind': kind,
            'source_native_id': native, 'source_family': _family(source),
            'source_scope': scope, 'relations': [], **fields}


def _citation(source, pointer, targets):
    return {'id': 'acquired-menu-citation:' + _hash([source['id'], pointer]),
            'kind': 'source_citation', 'record_type': 'source_citation',
            'source_key': source_key(source), 'provenance': _provenance(source, pointer),
            'relations': [_relation('cites_record', domain, record['id']) for domain, record in targets]}


def _require(row, fields):
    if not all(key in row for key in fields):
        raise UnsupportedSource('acquired_menu_schema_unknown')
    if not all(_present(row[key]) for key in fields):
        raise MalformedRecord('acquired_menu_required_field_missing')


def _begles(source, row, pointer, raw_json):
    role, scope = source['acquired_role'], _scope(source, row)
    records, needs = [], []
    if role == 'menu':
        _require(row, ('menudate', 'menurepastype', 'menuplattype', 'menuplatnom'))
        venue = [row.get('menurestaurantidtype'), row.get('menurestaurantid')]
        # If there is no native venue identity, preserve the row but don't group
        # unrelated venues through their names or null identifiers.
        grouping = [scope, venue, row['menudate'], row['menurepastype'], row.get('menurestaurantconvive')]
        if scope is None or not _present(venue[0]) or not _present(venue[1]):
            grouping.append(['unresolved-venue-row', pointer])
            needs.append('acquired_menu_ambiguous_join_scope')
        menu = _anchor(source, 'menu', grouping, title=None,
                       date=row['menudate'], daypart=row['menurepastype'],
                       audience=row.get('menurestaurantconvive'), venue_native_id=venue,
                       service_status='scheduled-not-confirmed-served', recipe_id=None)
        course = _anchor(source, 'menu_section', [menu['id'], row['menuplattype']],
                         title=row['menuplattype'], menu_id=menu['id'])
        course['relations'] = [_relation('section_of', 'recipes', menu['id'])]
        item = _base(source, row, pointer, 'menu_item', row.get('menuplatcode'), raw_json=raw_json)
        item.update(title=row['menuplatnom'], date=row['menudate'], daypart=row['menurepastype'],
                    audience=row.get('menurestaurantconvive'), menu_id=menu['id'],
                    section_id=course['id'], recipe_id=None, steps=None,
                    price=None, price_observations=[] if 'menuplatprix' not in row else [{
                        'kind': 'theoretical_production_cost', 'amount': row['menuplatprix'],
                        'currency': 'EUR', 'currency_basis': 'SCDL-menuPlatPrix-definition',
                        'date': row['menudate'], 'basis': 'source-field-no-serving-inference'}],
                    source_assertions={key: row[key] for key in ('menuplatsiqo','menuplatlabel',
                        'menuplatprecision','menuplatregime','menuplatallergene','menuplattexture',
                        'menuplatnutriscore') if key in row},
                    allergen_assertion_status='source-assertion-not-safety-guarantee')
        item['relations'] = [_relation('item_of', 'recipes', course['id'])]
        code = row.get('menuplatcode')
        if _present(code) and scope is not None:
            item['relations'].append(_native_relation(source,'source_dish_reference','recipes','dish_composition',code,scope))
        elif _present(code):
            needs.append('acquired_menu_ambiguous_join_scope')
        records = [('recipes', menu), ('recipes', course), ('recipes', item)]
    elif role == 'dish':
        _require(row, ('platcode', 'platnom', 'platproduitnom'))
        native = row['platcode']
        # Unscoped row identities cannot accidentally satisfy menu references.
        effective_scope = scope if scope is not None else ['unresolved-scope', source['id'], pointer]
        if scope is None:
            needs.append('acquired_menu_ambiguous_join_scope')
        dish = _anchor(source, 'dish_composition', native, effective_scope,
                       recipe_id=None, steps=None, classification='composition-not-cooking-recipe')
        observation = _base(source, row, pointer, 'dish_composition_observation', native, raw_json=raw_json)
        observation.update(title=row['platnom'], dish_id=dish['id'], recipe_id=None, steps=None)
        observation['relations'] = [_relation('observation_of', 'recipes', dish['id'])]
        ingredient = _base(source, row, pointer, 'ingredient_mention', raw_json=raw_json)
        ingredient.update(raw_text=row['platproduitnom'], source_name_text=row['platproduitnom'],
                          dish_id=dish['id'], recipe_id=None, quantity=None, unit=None,
                          normalized_ingredient_id=None, identity_status='source-composition-mention',
                          nutrition={'raw': row.get('platproduitnutriment'), 'basis': None},
                          allergens=row.get('platproduitallergene'),
                          allergen_assertion_status='source-assertion-not-safety-guarantee',
                          supplier_assertions={key:row[key] for key in ('platproduitfournisseurnom',
                            'platproduitfournisseursiret','platproduitfournisseurinsee') if key in row})
        ingredient['relations'] = [_relation('ingredient_of_dish', 'recipes', dish['id'])]
        observation['relations'].append(_relation('has_ingredient_mention', 'ingredients', ingredient['id']))
        records = [('recipes', dish), ('recipes', observation), ('ingredients', ingredient)]
    else:
        raise UnsupportedSource('acquired_menu_unsupported_role')
    return records, needs


def _toulouse(source, row, pointer, raw_json):
    role, records, needs = source['acquired_role'], [], []
    if role == 'menu':
        _require(row, ('datemenu','libelle_repas','libelle_ordre_plat','libelle_population_cible','libelle_plat'))
        native = [row['datemenu'], row['libelle_repas'], row['libelle_population_cible']]
        menu = _anchor(source, 'menu', native, title=None, date=row['datemenu'],
                       daypart=row['libelle_repas'], audience=row['libelle_population_cible'],
                       recipe_id=None, service_status='scheduled-not-confirmed-served')
        section = _anchor(source, 'menu_section', [menu['id'],row.get('ordre_plat'),row['libelle_ordre_plat']],
                          title=row['libelle_ordre_plat'], ordinal=row.get('ordre_plat'), menu_id=menu['id'])
        section['relations'] = [_relation('section_of','recipes',menu['id'])]
        item = _base(source,row,pointer,'menu_item',row.get('code_plat'),raw_json=raw_json)
        item.update(title=row['libelle_plat'],menu_id=menu['id'],section_id=section['id'],
                    recipe_id=None,steps=None,date=row['datemenu'],daypart=row['libelle_repas'],
                    audience=row['libelle_population_cible'],price=None,price_observations=[])
        item['relations'] = [_relation('item_of','recipes',section['id'])]
        if _present(row.get('code_plat')):
            item['relations'].append(_native_relation(source,'source_dish_reference','recipes','dish_composition',row['code_plat']))
        else:
            needs.append('acquired_menu_reference_without_native_id')
        records = [('recipes',menu),('recipes',section),('recipes',item)]
    elif role == 'dish':
        _require(row, ('code_plat','libelle_plat','code_recette'))
        dish = _anchor(source,'dish_composition',row['code_plat'],recipe_id=None,steps=None,
                       classification='composition-not-cooking-recipe')
        composition = _anchor(source,'composition_reference',row['code_recette'],recipe_id=None,
                              steps=None,classification='source-code-recette-not-cooking-recipe')
        observation = _base(source,row,pointer,'dish_composition_observation',row['code_plat'],raw_json=raw_json)
        observation.update(title=row['libelle_plat'],recipe_id=None,steps=None,
                           source_composition_id=row['code_recette'],source_order=row.get('numero'))
        observation['relations'] = [_relation('observation_of','recipes',dish['id']),
            _relation('has_source_composition','recipes',composition['id'],join_status='explicit-source-row')]
        records = [('recipes',dish),('recipes',composition),('recipes',observation)]
    elif role == 'ingredient':
        _require(row, ('code_denree','libelle_denree'))
        anchor = _anchor(source,'ingredient_source_entity',row['code_denree'],
                         normalized_ingredient_id=None,identity_status='source-native-not-normalized')
        observation = _base(source,row,pointer,'ingredient_source_observation',row['code_denree'],raw_json=raw_json)
        observation.update(name=row['libelle_denree'],long_name=row.get('libellelong_denree'),
                           normalized_ingredient_id=None,quantity=None,unit=None,
                           allergens={key:row[key] for key in ALLERGEN_FIELDS if key in row},
                           allergen_assertion_status='source-assertion-not-safety-guarantee',
                           source_labels={key:row[key] for key in ('code_label','label') if key in row},
                           linked_documents={key:row[key] for key in ('pdf','url') if key in row},
                           linked_documents_fetched=False)
        observation['relations'] = [_relation('observation_of','ingredients',anchor['id'])]
        if _present(row.get('code_recette')):
            observation['relations'].append(_native_relation(source,'ingredient_of_source_composition','recipes','composition_reference',row['code_recette']))
        records = [('ingredients',anchor),('ingredients',observation)]
    elif role == 'technical_sheet_reference':
        _require(row, ('code_denree',))
        if not any(key in row for key in ('filename','description')):
            raise UnsupportedSource('acquired_menu_schema_unknown')
        reference = _base(source,row,pointer,'technical_sheet_reference',row['code_denree'],raw_json=raw_json)
        reference.update(description=row.get('description'),filename=row.get('filename'),
                         linked_document_fetched=False,content_available=False,recipe_id=None)
        reference['relations'] = [_native_relation(source,'technical_sheet_for_source_ingredient','ingredients','ingredient_source_entity',row['code_denree'])]
        records = [('citations',reference)]
    else:
        raise UnsupportedSource('acquired_menu_unsupported_role')
    return records, needs


def project_row(source, row, locator='', raw_json=None):
    """Return ([(target_domain,envelope),...], fixed_schema_need_codes)."""
    if not isinstance(row,dict):
        raise MalformedRecord('acquired_menu_record_not_object')
    family = _family(source)
    # ODS v1 cached wrappers are admitted explicitly, not arbitrary unwrapping.
    original = row
    if isinstance(row.get('fields'),dict) and ('recordid' in row or 'datasetid' in row):
        row = row['fields']
    if family == 'fr_begles_menus':
        records, needs = _begles(source,row,locator,raw_json)
    elif family == 'fr_toulouse_menus':
        records, needs = _toulouse(source,row,locator,raw_json)
    else:
        records, needs = _cnous(source,row,locator)
    citation = _citation(source,locator,records)
    for _, record in records:
        if 'raw_source' in record:
            if original is not row:
                record['raw_source'] = original
                record['source_record_id'] = original.get('recordid')
            record['relations'].append(_relation('cites','citations',citation['id']))
    records.append(('citations',citation))
    return records, needs


def _local(tag):
    return str(tag).rsplit(':',1)[-1].lower()


def _xml_values(node):
    values = dict(node.get('attributes',{}))
    for child in node.get('content',[]):
        if isinstance(child,dict) and child.get('tag') and all(isinstance(x,str) for x in child.get('content',[])):
            values.setdefault(_local(child['tag']), ''.join(child['content']))
    return values


def _first(values, names):
    return next((values[key] for key in names if key in values and _present(values[key])),None)


def _cnous(source, packet, pointer):
    node = packet.get('xml_menu')
    if not isinstance(node,dict) or _local(node.get('tag')) != 'menu':
        raise UnsupportedSource('acquired_menu_schema_unknown')
    ancestry = packet.get('xml_ancestors',[])
    values = _xml_values(node)
    venue = _first(values,('id_resto','id_restaurant','restoid','restaurant'))
    for parent in reversed(ancestry):
        if _local(parent.get('tag')) in ('resto','restaurant','restauration'):
            venue = venue if venue is not None else _first(_xml_values(parent),('id','id_resto','id_restaurant'))
            break
    date = _first(values,('date','jour','datemenu'))
    daypart = _first(values,('moment','repas','type','service'))
    native = _first(values,('id','id_menu'))
    # Raw hierarchy is always preserved. Missing documented context is an honest
    # schema need, never filled with current date or a guessed venue.
    needs = [] if date is not None and venue is not None else ['acquired_menu_schema_unknown']
    menu_id = entity_id(source,'menu',[native,venue,date,pointer],_scope(source,{}))
    menu = _base(source,packet,pointer,'menu',native,identity=menu_id)
    menu.update(title=_first(values,('nom','name','libelle')),date=date,daypart=daypart,
                venue_native_id=venue,recipe_id=None,service_status='scheduled-not-confirmed-served',
                xml_hierarchy=node,xml_context=ancestry,schema_validation='primary-ESUP-XML-mapping; full-snapshot-not-reviewed',schema_documentation=CNOUS_SCHEMA_URL)
    records = [('recipes',menu)]
    node_records = {menu_id:menu}
    kinds = {'repas':'menu_section','service':'menu_section','categorie':'menu_section',
             'category':'menu_section','plats':'menu_section','plat':'menu_item','dish':'menu_item'}
    def visit(parent, parent_id, path, depth=0, inherited_daypart=None):
        if depth > 64:
            raise MalformedRecord('acquired_menu_xml_depth_cap')
        ordinal = 0
        for index, child in enumerate(parent.get('content',[])):
            if not isinstance(child,dict) or 'tag' not in child:
                continue
            tag = _local(child['tag'])
            child_path = path + '/content/' + str(index)
            kind = kinds.get(tag)
            next_parent = parent_id
            next_daypart = inherited_daypart
            if kind:
                fields = _xml_values(child)
                native_id = _first(fields,('id','code','id_plat'))
                text = ''.join(v for v in child.get('content',[]) if isinstance(v,str))
                record = _base(source,child,child_path,kind,native_id,
                    identity=entity_id(source,kind,[menu_id,child_path],_scope(source,{})))
                if tag in ('repas','service'):
                    next_daypart=_first(fields,('nom','name','type','moment'))
                record.update(date=date,daypart=next_daypart,venue_native_id=venue,
                              title=_first(fields,('nom','name','libelle','label','type')) or (text if text.strip() else None),
                              ordinal=ordinal,menu_id=menu_id,parent_id=parent_id,recipe_id=None,
                              steps=None,price=None,source_attributes=child.get('attributes',{}))
                record['relations'] = [_relation('item_of' if kind=='menu_item' else 'section_of','recipes',parent_id)]
                records.append(('recipes',record))
                node_records[parent_id]['relations'].append(_relation('contains_menu_entry','recipes',record['id']))
                node_records[record['id']]=record
                if kind=='menu_item':
                    record['source_codes']=[v.get('attributes',{}).get('valeur') for v in child.get('content',[]) if isinstance(v,dict) and _local(v.get('tag'))=='code']
                    statement=fields.get('ingredients')
                    record['ingredient_statement']=statement
                    if _present(statement):
                        mention=_base(source,{'ingredients':statement},child_path+'/ingredients','ingredient_label_mention')
                        mention.update(raw_text=statement,menu_item_id=record['id'],recipe_id=None,quantity=None,unit=None,normalized_ingredient_id=None,identity_status='unsplit-source-ingredient-statement')
                        mention['relations']=[_relation('ingredient_of_menu_item','recipes',record['id'])]
                        record['relations'].append(_relation('has_ingredient_mention','ingredients',mention['id']))
                        records.append(('ingredients',mention))
                next_parent = record['id']
                ordinal += 1
            visit(child,next_parent,child_path,depth+1,next_daypart)
    visit(node,menu_id,pointer+'/xml_menu',inherited_daypart=daypart)
    return records, needs


def _xml_rows(source, context):
    """Streaming Expat, bounded per menu; all DTDs/entities explicitly refused."""
    raw, stream, before = _open(source)
    parser = expat.ParserCreate()
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    stack, queue = [], []
    capturing = None
    record_size = 0
    ordinal = 0
    total = 0
    max_record = min(int(source.get('max_record_bytes',4*1024*1024)),16*1024*1024)
    max_source = int(source.get('max_expanded_bytes',16*1024*1024))
    def forbidden_dtd(*_):
        raise MalformedRecord('acquired_menu_xml_dtd_forbidden')
    def forbidden_entity(*_):
        raise MalformedRecord('acquired_menu_xml_entity_forbidden')
    parser.StartDoctypeDeclHandler = forbidden_dtd
    parser.EntityDeclHandler = forbidden_entity
    parser.ExternalEntityRefHandler = forbidden_entity
    def start(tag, attrs):
        nonlocal capturing, record_size
        if len(stack) >= 64:
            raise MalformedRecord('acquired_menu_xml_depth_cap')
        node = {'tag':tag,'attributes':dict(attrs),'content':[]}
        if capturing is not None:
            stack[-1]['content'].append(node)
        elif _local(tag)=='menu':
            capturing = len(stack)
            record_size = 0
        stack.append(node)
        record_size += len(tag) + sum(len(k)+len(v) for k,v in attrs.items())
        if record_size > max_record:
            raise MalformedRecord('acquired_menu_xml_record_cap')
    def chars(value):
        nonlocal record_size
        if not stack:
            return
        if capturing is not None or len(stack[-1]['content']) < 32:
            parts=stack[-1]['content']
            if parts and isinstance(parts[-1],str):
                parts[-1] += value
            else:
                parts.append(value)
            record_size += len(value.encode('utf-8'))
            if record_size > max_record:
                raise MalformedRecord('acquired_menu_xml_record_cap')
    def end(tag):
        nonlocal capturing, ordinal, record_size
        node = stack.pop()
        if capturing == len(stack):
            ancestors = json.loads(_json(stack))
            queue.append(({'xml_menu':node,'xml_ancestors':ancestors},'/xml/menu/'+str(ordinal),None,{}))
            ordinal += 1
            capturing = None
            record_size = 0
        elif capturing is None and stack and all(isinstance(v,str) for v in node['content']):
            # Preserve direct scalar venue/context values, but never accumulate
            # entire sibling menu trees or unbounded repeated metadata.
            if len(stack[-1]['content']) < 32 and sum(len(str(v)) for v in stack[-1]['content']) < 65536:
                stack[-1]['content'].append(node)
    parser.StartElementHandler=start
    parser.EndElementHandler=end
    parser.CharacterDataHandler=chars
    try:
        while True:
            context.check_budget()
            chunk=stream.read(65536)
            total += len(chunk)
            if total > max_source:
                raise MalformedRecord('acquired_menu_source_size_cap')
            try:
                parser.Parse(chunk,not chunk)
            except expat.ExpatError:
                # Any already framed menu is independent of a later broken tail.
                yield from queue
                queue.clear()
                raise MalformedRecord('acquired_menu_xml_invalid') from None
            yield from queue
            queue.clear()
            if not chunk:
                break
        if not ordinal:
            raise UnsupportedSource('acquired_menu_xml_no_menu_nodes')
        if _identity(before) != _identity(os.fstat(raw.fileno())):
            raise SourceChanged('source_changed_during_read')
    finally:
        if stream is not raw:
            stream.close()
        raw.close()


def _csv_rows(source, context):
    raw, stream, before = _open(source)
    text = io.TextIOWrapper(stream,encoding=source.get('encoding') or 'utf-8-sig',errors='strict',newline='')
    try:
        # Peek through a separate text prefix is unnecessary: first logical CSV
        # header suffices to identify the documented separators. No encoding guess.
        header = text.readline(65537)
        if len(header)>65536:
            raise MalformedRecord('acquired_menu_csv_invalid')
        delimiter = source.get('delimiter') or ('\t' if source.get('format')=='tsv' else None)
        if delimiter is None:
            try:
                delimiter=csv.Sniffer().sniff(header,delimiters=',;\t').delimiter
            except csv.Error:
                delimiter=','
        import itertools
        reader=csv.reader(itertools.chain([header],text),delimiter=delimiter,strict=True)
        fields=next(reader,[])
        if not fields:
            raise UnsupportedSource('csv_no_header')
        if len(fields)!=len(set(fields)):
            raise MalformedRecord('acquired_menu_csv_duplicate_header')
        for number, values in enumerate(reader,2):
            context.check_budget()
            if len(values)!=len(fields):
                yield None,'/csv/'+str(number),None,{'row_error':'acquired_menu_csv_row_width'}
                continue
            # Strings (including empty, decimal comma, 'null', and leading zeros)
            # remain strings. Only actual JSON null becomes null.
            yield dict(zip(fields,values)),'/csv/'+str(number),None,{}
        if _identity(before)!=_identity(os.fstat(raw.fileno())):
            raise SourceChanged('source_changed_during_read')
    finally:
        text.detach()
        if stream is not raw:
            stream.close()
        raw.close()


class _InvalidJSONRecord:
    pass


class _MenuJSONStream(_JSONStream):
    """Separate valid JSON framing from strict per-member data validation.

    Duplicate keys/non-finite numbers reject that framed object only. Invalid
    framing is never guessed or repaired and terminates the current source.
    """
    def value(self):
        self.space()
        while True:
            try:
                _,end=self.decoder.raw_decode(self.buffer)
                if end==len(self.buffer) and not self.eof:
                    self.fill()
                    continue
                if end>self.limit:
                    raise MalformedRecord('acquired_menu_json_record_invalid')
                native=self.buffer[:end]
                self.buffer=self.buffer[end:]
                try:
                    return _strict(native),native
                except (ValueError,RecursionError):
                    return _InvalidJSONRecord(),None
            except json.JSONDecodeError:
                if self.eof or len(self.buffer)>self.limit:
                    raise MalformedRecord('acquired_menu_json_framing_invalid') from None
                self.fill()


def _json_rows(source,context):
    raw,stream,before=_open(source)
    text=io.TextIOWrapper(stream,encoding=source.get('encoding') or 'utf-8-sig',errors='strict',newline='')
    limit=min(int(source.get('max_record_bytes',4*1024*1024)),16*1024*1024)
    try:
        if source['format'] in ('jsonl','ndjson'):
            number=0
            while True:
                context.check_budget()
                line=text.readline(limit+1)
                if not line:
                    break
                number+=1
                if len(line)>limit:
                    while line and not line.endswith('\n'):
                        line=text.readline(limit+1)
                    yield None,'/line/'+str(number),None,{'row_error':'acquired_menu_json_line_cap'}
                    continue
                if not line.strip():
                    continue
                try:
                    row=_strict(line)
                    error={}
                except (ValueError,RecursionError):
                    row=None
                    error={'row_error':'acquired_menu_json_record_invalid'}
                yield row,'/line/'+str(number),line,error
        else:
            for value in _MenuJSONStream(text,context.check_budget,limit).rows():
                row,pointer,native=value[:3]
                metadata=value[3] if len(value)==4 else {}
                if isinstance(row,_InvalidJSONRecord):
                    yield None,pointer,None,{'row_error':'acquired_menu_json_record_invalid'}
                else:
                    yield row,pointer,native,metadata
        if _identity(before)!=_identity(os.fstat(raw.fileno())):
            raise SourceChanged('source_changed_during_read')
    finally:
        text.detach()
        if stream is not raw:
            stream.close()
        raw.close()


def _note(stats, reason, error=False):
    reason=reason if reason in REASONS else 'acquired_menu_source_error'
    stats['reason_counts'][reason]=stats['reason_counts'].get(reason,0)+1
    if error:
        stats['errors']+=1
    if reason in ('acquired_menu_schema_unknown','acquired_menu_xml_no_menu_nodes',
                  'acquired_menu_required_field_missing','acquired_menu_ambiguous_join_scope',
                  'acquired_menu_reference_without_native_id'):
        stats['schema_needs'][reason]=stats['schema_needs'].get(reason,0)+1


def new_stats():
    return dict(errors=0,skipped=0,input_records=0,emitted_records=0,
                record_kinds={},reason_counts={},schema_needs={})


def iter_records(domain,source,context,stats=None):
    stats=stats if stats is not None else new_stats()
    verified=isinstance(source.get('metadata'),dict) and isinstance(source['metadata'].get('acquisition'),dict) and source['metadata']['acquisition'].get('verified') is True
    if not verified or source.get('disposition')!='candidate' or source.get('restricted') or source.get('loaded'):
        raise UnsupportedSource('acquired_menu_acquisition_unverified')
    try:
        fmt=str(source.get('format','')).lower()
        if source.get('acquired_role') not in ROLES:
            raise UnsupportedSource('acquired_menu_unsupported_role')
        family=_family(source)
        if family=='fr_cnous_menus' and fmt=='xml':
            rows=_xml_rows(source,context)
        elif fmt in ('csv','tsv'):
            rows=_csv_rows(source,context)
        elif fmt in ('json','jsonl','ndjson'):
            rows=_json_rows(source,context)
        else:
            raise UnsupportedSource('acquired_menu_unsupported_format')
        seen=set()
        for row,pointer,raw_json,metadata in rows:
            context.check_budget()
            stats['input_records']+=1
            try:
                if metadata.get('row_error'):
                    raise MalformedRecord(metadata['row_error'])
                if isinstance(row,dict) and '__ingest_collection_metadata__' in row:
                    # Source wrapper metadata is citation material, not a menu.
                    projected=[('citations',_base(source,row,pointer,'source_collection_metadata'))]
                    needs=[]
                else:
                    projected,needs=project_row(source,row,pointer,raw_json)
                for reason in set(needs):
                    _note(stats,reason)
                for target,record in projected:
                    if target!=domain:
                        continue
                    if record['id'] in seen:
                        stats['skipped']+=1
                        continue
                    if len(seen)>=100000:
                        seen.clear()
                    seen.add(record['id'])
                    stats['emitted_records']+=1
                    kind=record['kind']
                    stats['record_kinds'][kind]=stats['record_kinds'].get(kind,0)+1
                    yield record
            except (ValueError,TypeError,KeyError,UnicodeError) as exc:
                reason=exc.args[0] if len(exc.args)==1 and isinstance(exc.args[0],str) else None
                _note(stats,reason,True)
                context.report_error(source,exc)
    except BudgetExceeded:
        raise
    except (ValueError,TypeError,KeyError,UnicodeError,csv.Error) as exc:
        reason='acquired_menu_encoding_invalid' if isinstance(exc,UnicodeError) else 'acquired_menu_csv_invalid' if isinstance(exc,csv.Error) else exc.args[0] if len(exc.args)==1 and isinstance(exc.args[0],str) else None
        _note(stats,reason,True)
        context.report_error(source,MalformedRecord(reason if reason in REASONS else 'acquired_menu_source_error'))


def run_domain(domain,sources,context):
    if domain not in ('recipes','ingredients','citations'):
        raise ValueError('wrong_acquired_menu_adapter_domain')
    totals=dict.fromkeys(COUNTERS,0)
    summaries=[]
    for original in sources:
        source=dict(original,adapter_version=VERSION)
        stats=new_stats()
        verified=isinstance(source.get('metadata'),dict) and isinstance(source['metadata'].get('acquisition'),dict) and source['metadata']['acquisition'].get('verified') is True
        if not verified:
            summary=dict(source_key=source_key(source),status='skipped',reason='acquired_menu_acquisition_unverified',skipped=1)
        elif source.get('restricted') or source.get('loaded') or source.get('disposition') != 'candidate':
            summary=dict(source_key=source_key(source),status='skipped',reason='catalog_skip',skipped=1)
        else:
            try:
                summary=context.ingest(source,iter_records(domain,source,context,stats))
            except BudgetExceeded:
                summary=dict(source_key=source_key(source),status='partial',reason='resource_cap')
            except Exception as exc:
                context.report_error(source,exc)
                _note(stats,'acquired_menu_source_error',True)
                summary=dict(source_key=source_key(source),status='failed')
        summary['errors']=max(summary.get('errors',0),stats['errors'])
        summary['skipped']=summary.get('skipped',0)+stats['skipped']
        summary['diagnostics']={key:stats[key] for key in ('input_records','emitted_records','record_kinds','reason_counts','schema_needs')}
        summary['diagnostics']['projection_status']='source_schema_or_exact_join_evidence_needed' if stats['schema_needs'] else 'source_fields_projected' if stats['emitted_records'] else 'not_observed_this_invocation'
        if summary['errors'] and summary.get('status')=='complete':
            summary['status']='partial'
        summaries.append(summary)
        for key in COUNTERS:
            totals[key]+=summary.get(key,0)
    return dict(domain=domain,adapter_version=VERSION,
                status='partial' if any(s.get('status') in ('partial','failed') for s in summaries) else 'complete',
                sources=summaries,**totals)
