#!/usr/bin/env python3
"""Report actual collection evidence alongside all 249 country discovery queues."""
import argparse,datetime,gzip,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOMAINS=['foods','food-composition','recipes','dietary-guidelines','producers','retailers-prices']
def report(data,output):
 matrix=json.loads((ROOT/'docs/country-delivery-matrix.json').read_text());ledger=json.loads((ROOT/'docs/source-delivery-ledger.json').read_text());access=json.loads((data/'source-access-20261013/report.json').read_text());by_access={x['sourceId']:x for x in access['sources']};by_source={x['sourceId']:x for x in ledger['sources']}
 observed=collections.defaultdict(lambda:collections.defaultdict(collections.Counter));releases=[]
 directories=['off-2026-10-12-lf','usda-2026-04','prices-2026-10-12','afcd-3','ciqual-2025','cofid-2021','germany-bls-4.0','matvaretabellen-2026','frida-5.5','fineli-20.0','fineli-20.0-reference-tables','foodfiles-2024-v01','sweden-food-2026-07-01','cnf-2015','mext-2023-main','overture-food-places-2026-09-23.1','wikidata-businesses-20261013-native','dietary-guidelines-20261013','wikibooks-2026-10-13-live']
 for name in directories:
  directory=data/name;p=directory/'manifest.json'
  if not p.exists():continue
  m=json.loads(p.read_text());source=m['sourceId'];releases.append({'sourceId':source,'releaseId':m.get('releaseId',name),'normalizedRecords':m.get('normalizedRows',m.get('counts',{}).get('records')),'scope':m['scope'],'manifest':str(p)})
  if source in ['off','prices','overture-food-places']:
   for country,count in m.get('countries',{}).items():observed[country][source]['all-normalized-records']+=count
   continue
  if source=='usda-files':observed['US'][source]['all-normalized-records']+=m.get('normalizedRows',m.get('counts',{}).get('records',0));continue
  inputs=[directory/p['key'] for p in m.get('partitions',[])] or [directory/'normalized.jsonl.gz']
  for path in inputs:
   with gzip.open(path,'rt',encoding='utf8') as lines:
    for line in lines:
     for r in json.loads(line):
      for country in r['countries']:
       observed[country][source][r['kind']]+=1
       if r['kind']=='organization':
        for role in r['data'].get('roles',[]):observed[country][source]['role:'+role]+=1
 countries=[]
 for c in matrix['countries']:
  sources=[by_source[x] for x in c['sourceIds'] if x in by_source];checks=[by_access[x['sourceId']] for x in sources if x['sourceId'] in by_access]
  countries.append({'iso2':c['iso2'],'name':c['name'],'applicableRegisteredSourceIds':c['sourceIds'],'landingPagesChecked':len(checks),'landingPagesHTTP200':sum(x.get('httpStatus')==200 for x in checks),'sourcesWithDownloadCandidates':[x['sourceId'] for x in checks if x.get('downloadCandidates')],'sourcesWithRightsLinks':[x['sourceId'] for x in checks if x.get('rightsLinks')],'accessBlockers':[{'sourceId':x['sourceId'],'httpStatus':x.get('httpStatus'),'error':x.get('error')} for x in checks if x.get('httpStatus')!=200],'localObservedRecords':{s:dict(kinds) for s,kinds in observed[c['iso2']].items()},'domainsWithoutLocalDatasetEvidence':[d for d in DOMAINS if d not in {'foods' if any(s in observed[c['iso2']] for s in ['off','usda-files','afcd','ciqual','cofid','germany-bls','matvaretabellen','frida','cnf','mext','fineli','foodfiles','sweden-food']) else '', 'food-composition' if any(s in observed[c['iso2']] for s in ['off','usda-files','afcd','ciqual','cofid','germany-bls','matvaretabellen','frida','cnf','mext','fineli','foodfiles','sweden-food']) else '', 'recipes' if any(kinds.get('recipe',0)>0 for kinds in observed[c['iso2']].values()) else '', 'producers' if observed[c['iso2']].get('wikidata-food-businesses',{}).get('role:food-manufacturer',0) else '', 'dietary-guidelines' if 'dietary-guidelines' in observed[c['iso2']] else '', 'retailers-prices' if any(s in observed[c['iso2']] for s in ['prices','overture-food-places']) else ''}],'completeness':'Not established. Records are source assertions; global unknown-country rows are not allocated to countries. Business P17 is not market or production-origin coverage.'})
 result={'schema':'offmenu-country-execution/1','checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'countries':countries,'countryCount':len(countries),'sourceAccessSummary':{'registeredSources':len(access['sources']),'landingPagesHTTP200':sum(x.get('httpStatus')==200 for x in access['sources']),'downloadCandidateSources':sum(bool(x.get('downloadCandidates')) for x in access['sources']),'rightsLinkSources':sum(bool(x.get('rightsLinks')) for x in access['sources']),'scope':'Access evidence only. A download link is not licence acceptance, normalization or published coverage.'},'globalRouteSourceIds':matrix['globalSourceIds'],'collections':releases,'publication':'See expanded release acceptance; local collection counts here do not mean independently accepted food identity or countrywide completeness.'};output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'countries':len(countries),'sourcesChecked':len(access['sources']),'countriesWithLocalOFF':sum('off'in x['localObservedRecords'] for x in countries),'countriesWithPriceRecords':sum('prices'in x['localObservedRecords'] for x in countries),'countriesWithBusinessReferences':sum('wikidata-food-businesses'in x['localObservedRecords'] for x in countries),'countriesWithGuidelineReferences':sum('dietary-guidelines'in x['localObservedRecords'] for x in countries)}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('output',type=Path);a=p.parse_args();report(a.data,a.output)
