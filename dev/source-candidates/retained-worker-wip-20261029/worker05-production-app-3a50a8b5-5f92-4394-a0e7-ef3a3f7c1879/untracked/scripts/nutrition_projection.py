"""Bounded UI projection: source numbers and interpretation qualifiers stay together."""
FIELDS=('value','unit','qualifier','originalText','name','sourceComponent','definition','method','acquisitionType','methodType','methodIndicator')
TERMS=('release','sourceComponentId','sourceUnitCode','citationKey','zeroMeaning','labelRelationship','semanticAcceptance')
VERSION='nutrition-source-qualified-v2'

def observation(value):
    if not isinstance(value,dict):return value
    result={key:value[key] for key in FIELDS if key in value}
    if isinstance(value.get('sourceTerminology'),dict):
        result['sourceTerminology']={key:value['sourceTerminology'][key] for key in TERMS if key in value['sourceTerminology']}
    return result

def project(raw):
    if 'data' in raw:
        data=raw['data'];provenance=raw.get('provenance',{})
        return {'id':raw['id'],'country':next(iter(raw.get('countries',[])),None),'label':data.get('foodName') or raw['id'],'dataType':'nutrition','values':{'basis':data.get('basis'),'nutrients':{key:observation(value) for key,value in data.get('nutrients',{}).items()}},'sourceId':provenance.get('sourceId'),'sourceURL':provenance.get('url'),'sourceDate':provenance.get('sourceDate'),'attribution':provenance.get('attribution'),'originalRecord':{'publisherRecordId':provenance.get('recordId'),'releaseId':provenance.get('releaseId'),'archiveSHA256':provenance.get('archiveSha256')},'recordFormat':'Retained normalized nutrient profile','projectionVersion':VERSION}
    result=dict(raw)
    result['id']=raw.get('id') or raw.get('stableid')
    result['values']={'basis':raw.get('basis'),'nutrients':{key:observation(value) for key,value in raw['values'].items()}}
    result['recordFormat']='Source nutrition profile'
    result['projectionVersion']=VERSION
    return result
