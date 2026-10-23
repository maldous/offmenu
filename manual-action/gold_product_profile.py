"""Pure, independently qualified source-reported product/nutrition projection.

This is a separate narrow application profile. It never weakens or invokes the
full recipe/canonical-network builder and owns no DB/network/model/filesystem I/O.
Qualification pins bind caller-selected review/rights, not independent truth.
"""
import copy
import json
from urllib.parse import urlsplit
from gold_builder import TABLE_COLUMNS, INSERT_ORDER, digest

PROFILE = 'offmenu.product-nutrition-profile/1'
OFFICIAL_TERMS_URL = 'https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/'
LICENCE_NOTICES = [
    {'name':'Open Database License (ODbL)','version':'1.0','uri':'https://opendatacommons.org/licenses/odbl/1-0/'},
    {'name':'Database Contents License (DbCL)','version':'1.0','uri':'https://opendatacommons.org/licenses/dbcl/1-0/'},
]
PURPOSE_LIMITS = {
    'privateInternalAppSampleOnly':True,
    'publicRedistributionQualified':False,
    'publicDeploymentQualified':False,
    'imagesOrMediaIncluded':False,
    'brandingClearanceClaimed':False,
    'accuracyWarrantyClaimed':False,
    'changedPurposeRequiresSeparateReview':True,
}
METRIC = 'source-report-proteinmass'
SOURCE_FIELDS = ('domain','source_key','source_version','record_id','content_sha256',
                 'normalized_artifact_sha256','committed_watermark')
FACT_POINTERS = ('/code','/product_name','/nutrition_data_per','/nutriments/proteins_value',
                 '/nutriments/proteins_unit','/nutriments/proteins_100g','/ingredients/0/id')
RIGHTS_SCOPE = {'profile': PROFILE, 'target_locale': 'en',
                'output': 'private-local-gold+app-dto', 'field_pointers': list(FACT_POINTERS)}
QUERIES = {
 'product_nutrition_citations': """SELECT DISTINCT p.entity_id,p.resource_id,o.observation_id,m.metric_id,o.context_json,o.original_json,s.citation_id,c.payload_json AS citation_json
 FROM gold_entities p JOIN gold_observations o ON o.entity_id=p.entity_id AND o.state='verified'
 JOIN gold_metrics m ON m.metric_id=o.metric_id AND m.state='verified'
 JOIN gold_claims a ON a.claim_id=o.claim_id AND a.entity_id=p.entity_id AND a.state='verified'
 JOIN gold_support s ON s.target_kind='assertion' AND s.target_id=a.assertion_id AND s.support_scope='field'
 JOIN gold_citations c ON c.citation_id=s.citation_id
 WHERE p.state='verified' AND p.entity_type='source-reported-barcode-product' AND m.metric_id='source-report-proteinmass'
 ORDER BY p.entity_id,o.observation_id,s.citation_id""",
 'product_source_lineage': """SELECT p.entity_id,r.occurrence_id,r.source_key,r.source_version,r.record_id,r.content_sha256,r.normalized_artifact_sha256,r.committed_watermark
 FROM gold_entities p JOIN gold_entity_occurrences b ON b.entity_id=p.entity_id
 JOIN gold_occurrences r ON r.occurrence_id=b.occurrence_id
 WHERE p.state='verified' AND r.state='verified' AND p.entity_type='source-reported-barcode-product'""",
 'holds': 'SELECT target_kind,target_id,reason FROM gold_holds ORDER BY target_kind,target_id,reason',
}

def _json(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def _bounded(value):
    stack=[(value,0)];nodes=chars=0
    while stack:
        item,depth=stack.pop();nodes+=1
        if nodes>20000 or depth>24:raise ValueError('profile JSON complexity cap')
        kind=type(item)
        if kind is dict:
            if len(item)>20000:raise ValueError('profile JSON complexity cap')
            if any(type(k) is not str for k in item):raise ValueError('native JSON keys only')
            chars+=sum(len(k) for k in item);stack.extend((v,depth+1) for v in item.values())
        elif kind is list:
            if len(item)>20000:raise ValueError('profile JSON complexity cap')
            stack.extend((v,depth+1) for v in item)
        elif kind is str:chars+=len(item)
        elif kind not in (int,float,bool,type(None)):raise ValueError('native JSON only')
        if chars>1048576:raise ValueError('profile JSON size cap')
    if len(_json(value).encode())>1048576:raise ValueError('profile JSON size cap')

def _pin(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)

def _url(value):
    if type(value) is not str:return False
    parts=urlsplit(value)
    return parts.scheme=='https' and bool(parts.hostname) and parts.hostname!='localhost' and '.' in parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment

def _pointer(value,pointer):
    for key in pointer.split('/')[1:]:
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if type(value) is list else value[key]
    return value

def build_product_profile(packet, *, qualification):
    """packet: source/payload/citations. qualification: selected source+field+rights.

    Missing review/field/operation evidence returns held, with zero verified
    rows and an empty app profile. Explicit binding mismatches raise ValueError.
    Real writes/admission and actual source/rights acceptance belong00/56.
    """
    _bounded(packet);_bounded(qualification)
    if packet.get('schema_version')!='offmenu.product-profile-input/1':raise ValueError('input version')
    if qualification.get('schema_version')!='offmenu.product-profile-qualification/1':raise ValueError('qualification version')
    if packet.get('data_class') not in ('synthetic','real-qualified'):raise ValueError('data class')
    source=packet['source'];payload=packet['payload']
    if set(source)!=set(SOURCE_FIELDS) or source['domain']!='barcodes':raise ValueError('source shape/domain')
    if any(type(source[k]) is not str or not source[k] or len(source[k])>4096 for k in SOURCE_FIELDS):raise ValueError('source identity')
    if any(not _pin(source[k]) for k in ('content_sha256','normalized_artifact_sha256')):raise ValueError('source pins')
    if packet.get('payload_sha256')!=digest(payload) or qualification.get('payload_sha256')!=packet.get('payload_sha256'):raise ValueError('payload hash mismatch')
    if qualification.get('packet_sha256')!=digest(packet) or qualification.get('selected_source')!=source:raise ValueError('selected packet/source mismatch')
    code=payload.get('code')
    if type(code) is not str or len(code)!=13 or not code.isascii() or not code.isdigit() or code!=source['record_id']:raise ValueError('source barcode/record mismatch')
    if packet['data_class']=='real-qualified' and code!='0000417012009':raise ValueError('outside selected real product')
    eid=digest(['product-profile',*[source[k] for k in ('domain','source_key','source_version','record_id','content_sha256')]]);oid=digest(['occurrence',source]);aid=digest(['assertion',eid,METRIC]);obsid=digest(['observation',aid]);tid=digest(['text',eid])
    citations={}
    for c in packet.get('citations',[]):
        cid=c['citation_id']
        if type(cid) is not str or not cid.strip():raise ValueError('invalid citation id')
        if cid in citations:raise ValueError('duplicate citation')
        if c.get('source_binding')!=source or (c.get('url') is not None and not _url(c.get('url'))) or c.get('attribution')!='Open Food Facts':raise ValueError('citation source/url/attribution mismatch')
        citations[cid]=c
    reasons=[]
    if not _pin(qualification.get('facts_review_sha256')):reasons.append('independent facts review missing')
    proofs={pointer:[] for pointer in FACT_POINTERS}
    for proof in qualification.get('field_proofs',[]):
        pointer=proof.get('pointer');cid=proof.get('citation_id')
        if pointer not in proofs or cid not in citations or proof.get('source_binding')!=source:raise ValueError('field citation/source mismatch')
        try:value=_pointer(payload,pointer)
        except (KeyError,IndexError,TypeError,ValueError):raise ValueError('field pointer missing') from None
        if proof.get('value_sha256')!=digest(value):raise ValueError('field value hash mismatch')
        if _pin(proof.get('evidence_sha256')):proofs[pointer].append(proof)
    for pointer,matches in proofs.items():
        if not matches:reasons.append('field proof missing: '+pointer)
    rights=qualification.get('rights',{})
    terms=rights.get('terms_url')
    official_terms=terms==OFFICIAL_TERMS_URL
    if rights.get('licence_notices')!=LICENCE_NOTICES or rights.get('purpose_limits')!=PURPOSE_LIMITS:
        reasons.append('required selected licence notices/private-purpose limits missing or changed')
    if rights.get('state')!='permitted' or rights.get('operation')!='private-local-product-profile' or rights.get('source_binding')!=source or rights.get('scope')!=RIGHTS_SCOPE or not official_terms or not _pin(rights.get('terms_evidence_sha256')) or not _pin(rights.get('operation_evidence_sha256')):
        reasons.append('selected product-profile operation rights/official terms unqualified')
    name=payload.get('product_name');nutriments=payload.get('nutriments',{})
    if type(nutriments) is not dict:nutriments={}
    if qualification.get('english_name_language')!='en' or type(name) is not str or not name.strip() or len(name)>512:reasons.append('source English name missing')
    value=nutriments.get('proteins_value');unit=nutriments.get('proteins_unit')
    if type(value) not in (int,float) or value<0 or unit!='g':reasons.append('source protein mass/unit unsupported')
    if payload.get('nutrition_data_per')!='100g' or type(nutriments.get('proteins_100g')) not in (int,float) or nutriments.get('proteins_100g')!=value:reasons.append('source 100g basis ambiguous or inconsistent')
    ingredients=payload.get('ingredients',[])
    tag=ingredients[0].get('id') if type(ingredients) is list and ingredients and type(ingredients[0]) is dict else None
    if tag!='en:sugar':reasons.append('selected native English ingredient tag missing')
    qualified=not reasons;state='verified' if qualified else 'held'
    rows={table:[] for table in TABLE_COLUMNS}
    def add(table,**row):
        if set(row)!=set(TABLE_COLUMNS[table]):raise ValueError('row contract')
        rows[table].append(row)
    runid=digest([digest(packet),digest(qualification)])
    add('gold_runs',run_id=runid,packet_sha256=digest(packet),qualification_sha256=digest(qualification),data_class=packet['data_class'],watermark_json=_json({'profile':PROFILE,'source':source}))
    for cid,c in sorted(citations.items()):add('gold_citations',citation_id=cid,payload_json=_json(c))
    add('gold_entities',entity_id=eid,resource_id='source-barcode:'+code,domain='barcodes',entity_type='source-reported-barcode-product',state=state,payload_json=_json({'barcode':code,'identity':'source-asserted-not-GS1-verified','profile':PROFILE}))
    add('gold_occurrences',occurrence_id=oid,domain='barcodes',source_key=source['source_key'],source_version=source['source_version'],record_id=source['record_id'],content_sha256=source['content_sha256'],normalized_artifact_sha256=source['normalized_artifact_sha256'],committed_watermark=source['committed_watermark'],state=state,payload_json=_json(source))
    add('gold_entity_occurrences',entity_id=eid,occurrence_id=oid)
    add('gold_texts',text_id=tid,source_text_id=tid,entity_id=eid,occurrence_id=oid,language=qualification.get('english_name_language'),original_text=name if type(name) is str else '',english_text=name if type(name) is str and qualification.get('english_name_language')=='en' else None,state=state,evidence_json=_json(proofs['/product_name']))
    original={'value':value,'unit':unit,'basis':'100g','source_per100g_alias':nutriments.get('proteins_100g'),'reported_value_count':1,'independent_measurement_count':None}
    context={'country':None,'cut':None,'fat':None,'preparation':None,'raw_cooked':None,'basis':'100g','source_date':None,'method':None,'uncertainty':'source-reported; method/date/context unknown'}
    add('gold_claims',claim_id=aid,assertion_id=aid,entity_id=eid,property_id=METRIC,state=state,payload_json=_json({'value':original,'source':source,'field':'/nutriments/proteins_value'}))
    add('gold_metrics',metric_id=METRIC,name_en='Source-reported protein',dimension='mass',canonical_unit_id='g',state=state)
    add('gold_observations',observation_id=obsid,claim_id=aid,metric_id=METRIC,entity_id=eid,kind='observed',state=state,context_json=_json(context),original_json=_json(original),comparable_json='null',payload_json=_json({'profile':PROFILE,'source':source}))
    for pointer,matches in proofs.items():
        target_kind,target_id=('assertion',aid) if pointer.startswith('/nutriments/') or pointer=='/nutrition_data_per' else ('text',tid) if pointer=='/product_name' else ('resource','source-barcode:'+code)
        for proof in matches:
            sid=digest([target_kind,target_id,proof['citation_id'],proof['evidence_sha256'],pointer])
            if not any(r['support_id']==sid for r in rows['gold_support']):add('gold_support',support_id=sid,target_kind=target_kind,target_id=target_id,citation_id=proof['citation_id'],support_scope='field',evidence_sha256=proof['evidence_sha256'])
    used={s['citation_id'] for s in rows['gold_support']} if qualified else set()
    for cid in citations.keys()-used:
        add('gold_holds',hold_id=digest(['citation',cid]),target_kind='citation',target_id=cid,reason='citation retained without qualified profile support')
    for reason in sorted(set(reasons)):
        add('gold_holds',hold_id=digest([eid,reason]),target_kind='product-profile',target_id=eid,reason=reason)
    citation_dto=[{'id':cid,'url':c.get('url'),'attribution':c['attribution'],'sourceRecordId':code,'fieldPointers':sorted(k for k,matches in proofs.items() if any(p['citation_id']==cid for p in matches))} for cid,c in sorted(citations.items()) if cid in used]
    dto={'schema_version':PROFILE,'profile':'source-reported-product-nutrition-only','status':'qualified-candidate' if qualified else 'held','product':{'id':eid,'barcode':code,'barcodeStatus':'source-asserted-not-GS1-verified','nameEn':name,'sourceIngredientTags':[{'tag':tag,'namespace':'open-food-facts/product.ingredients.id','relation':'source-contains-tag','canonicalIngredientId':None}]} if qualified else None,'nutrientObservations':[{'id':obsid,'metricId':METRIC,'value':value,'unit':'g','basis':'100g','kind':'source-reported','context':context,'sourcePer100gIsIndependentMeasurement':False,'reportedValueCount':1,'independentMeasurementCount':None,'citationIds':sorted({p['citation_id'] for k in ('/nutriments/proteins_value','/nutriments/proteins_unit','/nutriments/proteins_100g','/nutrition_data_per') for p in proofs[k]})}] if qualified else [],'citations':citation_dto,'source':{'name':'Open Food Facts','recordId':code,'contentSHA256':source['content_sha256'],'qualificationSHA256':digest(qualification)},'rights':{'state':'permitted' if qualified else 'unqualified','termsUrl':terms if qualified else None,'licenceNotices':copy.deepcopy(LICENCE_NOTICES) if qualified else [],'purposeLimits':copy.deepcopy(PURPOSE_LIMITS),'legalComplianceClaim':False,'scope':'source-reported-product-nutrition-only','operationEvidenceSHA256':rights.get('operation_evidence_sha256') if qualified else None},'extensions':{'recipe':'HELD_NOT_QUALIFIED','canonicalIngredient':'HELD_NOT_QUALIFIED','recallCoverage':'NOT_CHECKED','manufacturer':None,'parent':None,'retailer':None,'brandLabel':None},'admission':{'actualGoldAdmitted':False,'requires':'00 actual write and56 readback after64 source review'}}
    for table in rows:rows[table].sort(key=_json)
    return {'schema_version':'offmenu.product-profile-proposal/1','profile':PROFILE,'status':'qualified-candidate' if qualified else 'held','data_class':packet['data_class'],'rows':rows,'dto':dto,'holds':sorted(set(reasons)),'counts':{'qualifiedProducts':int(qualified),'qualifiedObservations':int(qualified),'actualGoldAdmitted':0,'usableCitations':len(used),'heldCitations':len(citations)-len(used)},'pins':{'packet_sha256':digest(packet),'qualification_sha256':digest(qualification)},'privateCustodyOriginal':copy.deepcopy(payload)}
