"""Exact national metric source-field joins; no nutrient equivalence or estimates."""
import copy
from north_star_derivations import derive as structural_derive, digest, PROP, TYPE, USABLE
VERSION='north-star-national-metric-context/1'

def derive(packet,contract):
    side=structural_derive(packet,contract)
    side['additionalRulesetVersions']=[VERSION]
    resources={r['id']:r for r in packet['resources']};citations={c['id']:c for c in packet['citations']}
    facts={}
    for fact in packet['assertions']:
        facts.setdefault((fact['subjectId'],fact['propertyId'],fact['sourcePath']),[]).append(fact)
    def issue(code,subject,inputs):
        side['issues'].append({'code':code,'subjectId':subject,'inputIds':sorted(f['id'] for f in inputs),'status':'unresolved'})
    for value in packet['assertions']:
        if value['propertyId']!=PROP+'metricValue':continue
        subject=value['subjectId'];path=value['sourcePath'];resource=resources.get(subject)
        if not resource or resource['type']!=TYPE+'FoodCompositionObservation':
            issue('national-metric-subject-type-mismatch',subject,[value]);continue
        if not path.endswith('.value'):
            issue('national-metric-value-path-not-explicit',subject,[value]);continue
        base=path[:-6]
        definitions=facts.get((subject,PROP+'metricDefinition',base+'.definition'),[])
        metadata=facts.get((subject,PROP+'originalMetricFields',base),[])
        if len(definitions)!=1 or len(metadata)!=1:
            issue('national-unique-metric-source-fields-required',subject,[value]);continue
        definition,meta=definitions[0],metadata[0];inputs=[value,definition,meta]
        if any(f['status'] not in USABLE for f in inputs):
            issue('national-metric-input-status-not-usable',subject,inputs);continue
        ids=set(value['citationIds'])
        if not ids or set(resource['citationIds'])!=ids or any(set(f['citationIds'])!=ids for f in inputs) or any(i not in citations for i in ids):
            issue('national-metric-source-citations-differ',subject,inputs);continue
        scope=value['scope']
        if any(f['scope']!=scope for f in [resource,*inputs,*[citations[i] for i in ids]]):
            issue('national-metric-source-scope-differs',subject,inputs);continue
        quantity=value['value']
        if quantity.get('kind')!='quantity' or definition['value'].get('kind')!='identifier':
            issue('national-metric-source-shape-mismatch',subject,inputs);continue
        basis=quantity.get('basis') or {}
        state_known=bool(basis.get('preparationStateId') or any(q.startswith('state:') for q in basis.get('qualifiers',[])))
        fields={'quantity':copy.deepcopy(quantity),'sourceMetricDefinition':copy.deepcopy(definition['value']),
                'sourceMetricMetadata':copy.deepcopy(meta['value']),
                'unknownValue':{'kind':'boolean','value':quantity.get('value') is None},
                'preparationBasisCarried':{'kind':'boolean','value':state_known},
                'comparability':{'kind':'identifier','value':'not-qualified'},
                'sourceMetricValueStatus':{'kind':'identifier','value':value['status']}}
        if not state_known:issue('national-preparation-basis-not-carried',subject,inputs)
        candidate={'subjectId':subject,'propertyId':PROP+'source-field:north-star-national-metric-context',
                   'sourcePath':base,'value':{'kind':'structure','fields':fields},'status':'candidate',
                   'citationIds':sorted(ids),'scope':copy.deepcopy(scope),
                   'confidence':{'status':'not-calibrated','probability':None},
                   'derivation':{'methodId':'urn:offmenu:method:'+VERSION+':exact-subject-path-metric-fields',
                                 'inputAssertionIds':sorted(f['id'] for f in inputs),'inputRelationIds':[],
                                 'inputDigests':{f['id']:digest(f) for f in inputs},'reviewStatus':'candidate'}}
        candidate['id']='urn:offmenu:derivation:'+digest([VERSION,candidate])
        side['assertions'].append(candidate)
    side['assertions'].sort(key=lambda x:x['id'])
    side['issues'].sort(key=lambda x:(x['code'],x['subjectId'],x['inputIds']))
    return side
