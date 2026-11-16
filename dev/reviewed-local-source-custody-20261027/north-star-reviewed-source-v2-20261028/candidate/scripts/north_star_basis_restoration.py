"""Exact same-source recovery of per-nutrient basis discarded by bulk aligner.

Inputs are already-curated public records and immutable normalized common
packets. Nothing here acquires originals or accepts culinary/health identity.
The original quantity is never modified, nor is a profile basis substituted.
"""
import copy
import hashlib
from north_star_derivations import canonical,digest,PROP,TYPE

VERSION='north-star-per-nutrient-basis-restoration/1'
SCOPE={'visibility':'public','reuseScope':'Per-source licences and derivative requirements apply'}


def urn(kind,*parts):
    return 'urn:offmenu:bulk:'+kind+':'+hashlib.sha256('\x1f'.join(map(str,parts)).encode()).hexdigest()[:24]


def old_quantity(value,unit,basis=None):
    """Exact selected align-bulk-food-common.py quantity projection, not repair."""
    raw=unit if isinstance(unit,str) and unit else None
    units={'g':('g','mass'),'kg':('kg','mass'),'mg':('mg','mass'),'mcg':('ug','mass'),'µg':('ug','mass'),
           'ml':('ml','volume'),'l':('l','volume'),'kcal':('kcal','energy'),'kj':('kj','energy'),
           'oz':('oz','mass'),'lb':('lb','mass')}
    uid,dimension=units.get((raw or '').lower(),(None,'unknown'))
    out={'kind':'quantity','value':value if isinstance(value,(int,float)) else None,
         'unitId':'urn:offmenu:unit:'+uid if uid else None,'dimension':dimension,
         'sourceValue':value,'sourceUnit':raw,'qualifiers':[]}
    if basis:out['basis']=basis
    return out


def native_projection(record,source,entry):
    """Return minimal local-only evidence, or None for a non-profile record.

    The caller validates source manifest/file bytes and records those file pins.
    This projection itself still contains source fields: keep it confined.
    """
    if source not in {'off','usda-files'} or entry.get('sourceId')!=source:raise ValueError('unselected food source')
    p=record.get('provenance',{});c=record.get('curation',{})
    if p.get('sourceId')!=source:raise ValueError('native provenance source differs')
    if p.get('visibility')!='public' or c.get('schema')!='offmenu-curation/1' or c.get('policyVersion')!='offmenu-curation/1':
        raise ValueError('unselected public curation')
    if c.get('status')!='selected-source-facts' or c.get('rawSourcePayloadPublished') is not False or c.get('automaticDietQualification') is not False:
        raise ValueError('source hold or unsupported curation state')
    if record.get('kind')!='nutrientProfile':return None
    rid=record.get('id') or p.get('recordId')
    if rid is None:raise ValueError('missing native record identity')
    resource=urn('resource',source,rid);cid=urn('citation',source,rid)
    identity={'sourceId':source,'originalRecordId':str(p.get('recordId') or rid),
              'revisionId':p.get('releaseId') or entry.get('releaseId'),
              'contentSha256':p.get('archiveSha256') or entry.get('archiveSha256'),
              'license':p.get('license') or entry.get('license'),
              'sourcePath':c.get('sourceRecordReference') or record.get('id','')}
    if any(v in (None,'') for v in identity.values()):raise ValueError('incomplete source identity')
    fields={};missing=0
    for key,n in record.get('data',{}).get('nutrients',{}).items():
        if not isinstance(n,dict):continue
        basis=n.get('basis')
        if not isinstance(basis,dict) or 'state' not in basis:
            missing+=1;continue
        # A source state may be unknown/null or an unregistered literal. Retain
        # it without translating it to a culinary preparation classification.
        if basis['state'] is not None and not isinstance(basis['state'],str):raise ValueError('unsupported source state shape')
        q=old_quantity(n.get('value'),n.get('unit'),old_quantity(basis.get('amount'),basis.get('unit')))
        fields[str(key)]={'sourceBasis':copy.deepcopy(basis),'expectedQuantitySha256':digest(q),
                          'nativeFieldCanonicalSha256':digest(n)}
    return {'schemaVersion':'offmenu-local-native-basis-evidence/1','rulesetVersion':VERSION,
            'resourceId':resource,'citationId':cid,'sourceId':source,'sourceIdentitySha256':digest(identity),
            'nativeOriginalReferenceSha256':digest({'kind':'identifier','value':str(rid)}),
            'inputNativeRecordCanonicalSha256':digest(record),'sourceCurationCanonicalSha256':digest(c),
            'sourceEntryCanonicalSha256':digest(entry),'humanReviewed':c.get('humanReviewed'),
            'independentlyAccepted':entry.get('independentlyAccepted'),
            'metrics':fields,'metricsWithoutOwnState':missing}


def restore(packet,projection):
    if projection is None:return None
    if projection['rulesetVersion']!=VERSION:raise ValueError('projection version differs')
    maps={}
    for k in ('resources','assertions','relations','citations'):
        maps[k]={r['id']:r for r in packet[k]}
        if len(maps[k])!=len(packet[k]):raise ValueError('duplicate packet identity')
    rid=projection['resourceId'];cid=projection['citationId'];resource=maps['resources'].get(rid);citation=maps['citations'].get(cid)
    if not resource or resource['type']!=TYPE+'FoodCompositionObservation' or resource['citationIds']!=[cid] or resource['scope']!=SCOPE:
        raise ValueError('exact source profile mismatch')
    if not citation or citation['scope']!=SCOPE:raise ValueError('source citation scope mismatch')
    identity={k:citation.get(k) for k in ['sourceId','originalRecordId','revisionId','contentSha256','license','sourcePath']}
    if digest(identity)!=projection['sourceIdentitySha256']:raise ValueError('source citation identity mismatch')
    fs=list(maps['assertions'].values())
    original=[f for f in fs if f['subjectId']==rid and f['propertyId']==PROP+'originalSourceRecord']
    if len(original)!=1 or digest(original[0]['value'])!=projection['nativeOriginalReferenceSha256']:
        raise ValueError('exact original record reference mismatch')
    if original[0]['citationIds']!=[cid] or original[0]['scope']!=SCOPE or original[0]['status']!='source-asserted' or original[0]['sourcePath']!='id':
        raise ValueError('original record source context mismatch')
    groups={};input_digests={original[0]['id']:digest(original[0])};matched=0
    for key,n in projection['metrics'].items():
        path='data.nutrients.'+key;aid=urn('assertion',rid,'nutrientObservation',path)
        selected=[f for f in fs if f['subjectId']==rid and f['propertyId']==PROP+'nutrientObservation' and f['sourcePath']==path]
        if len(selected)!=1 or selected[0]['id']!=aid:raise ValueError('exact normalized nutrient target required')
        q=selected[0]
        if q['citationIds']!=[cid] or q['scope']!=SCOPE or q['status']!='source-asserted':raise ValueError('nutrient source status scope differs')
        if digest(q['value'])!=n['expectedQuantitySha256']:raise ValueError('native normalized quantity fidelity mismatch')
        if 'state' in q['value'].get('basis',{}) or 'preparationStateId' in q['value'].get('basis',{}):
            raise ValueError('existing nutrient preparation is not replaceable')
        b=n['sourceBasis'];bh=digest(b);group=groups.setdefault(bh,{'sourceBasis':copy.deepcopy(b),'sourceBasisCanonicalSha256':bh,
            'stateStatus':'unknown' if b['state'] is None else 'source-literal-not-canonicalized','targets':[]})
        group['targets'].append({'inputAssertionId':aid,'sourcePath':path+'.basis','nativeMetricCanonicalSha256':n['nativeFieldCanonicalSha256'],
                                 'originalQuantityCanonicalSha256':digest(q['value'])})
        input_digests[aid]=digest(q);matched+=1
    if not matched:return None
    out={'schemaVersion':'offmenu-nutrient-basis-derivations/1','rulesetVersion':VERSION,
         'subjectId':rid,'citationIds':[cid],'scope':copy.deepcopy(SCOPE),'status':'candidate-not-admitted',
         'evidenceKind':'copied-same-source-per-nutrient-basis','basisGroups':[groups[k] for k in sorted(groups)],
         'inputPacketCanonicalSha256':digest(packet),'inputNativeRecordCanonicalSha256':projection['inputNativeRecordCanonicalSha256'],
         'sourceCurationCanonicalSha256':projection['sourceCurationCanonicalSha256'],'sourceEntryCanonicalSha256':projection['sourceEntryCanonicalSha256'],
         'derivation':{'methodId':'urn:offmenu:method:'+VERSION,'inputAssertionIds':sorted(input_digests),'inputDigests':input_digests,'reviewStatus':'candidate'},
         'matchedNutrientAssertions':matched,'sourceMetricsWithoutOwnState':projection['metricsWithoutOwnState'],
         'profileBasisUsed':False,'originalQuantityModified':False,'publicationEligible':False,'automaticPlanningEligible':False,
         'nutritionAggregationEligible':False,'identityEffect':'none','confidence':{'status':'not-calibrated','probability':None},
         'sourceQualifications':{'humanReviewed':projection['humanReviewed'],'independentlyAccepted':projection['independentlyAccepted']}}
    out['id']='urn:offmenu:derivation:'+digest(out)
    return out
