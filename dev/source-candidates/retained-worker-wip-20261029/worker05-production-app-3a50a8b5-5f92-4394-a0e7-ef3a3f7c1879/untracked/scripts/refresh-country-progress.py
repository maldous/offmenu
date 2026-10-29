"""Export whitelisted metadata only. Never read raw corpus records or publish receipt headers."""
from pathlib import Path
import hashlib, json, datetime

OUT = Path(__file__).resolve().parents[1] / 'public'
DATA = Path('/home/user/src/offmenu-data')
BASE = Path('/home/user/Documents/Codex/2026-10-13/task-3/country-progress-ui-snapshot.json')
EXPECTED = 'ce4ccff4a59878f4c652bd728192e8d936ea325d4339d34ef86021585d61755c'
inputs = []

def read(path, label=None, asof=None):
    p = Path(path)
    raw = p.read_bytes()
    obj = json.loads(raw)
    if label:
        inputs.append({'label': label, 'sha256': hashlib.sha256(raw).hexdigest(), 'asOf': asof or obj.get('generatedUTC') or obj.get('completedAt') or obj.get('checkedAt') or obj.get('frozenUTC') or obj.get('date')})
    return obj

assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
snapshot = read(BASE, 'Gateway allocation and historical receipt snapshot')
ledger = read('/home/user/src/offmenu-freebuff/docs/source-delivery-ledger.json', 'Registered source ledger (discovery only)')
registry = read('/home/user/src/offmenu-freebuff/research/OffMenu_Enrichment_Source_Register_249.json')
discovery = read('/home/user/src/offmenu-freebuff/research/OffMenu_Global_Data_Source_Register.json')
execution = read(DATA/'dev-preview-20261014/source/docs/country-execution-20261013.json', 'Dated country execution index; not live coverage')
by_source = {s['sourceId']: s for s in ledger['sources']}
enrichment = {s['source_id']: s for s in registry['source_catalog']}
discovery_sources = {'discovery:'+s['id']: s for s in discovery['sources']}
discovery_countries = {c['code']: c for c in discovery['countries']}
countries = {}
type_names = {'company_sources':'Company records','food_sources':'Food safety & regulation','producer_sources':'Producers & provenance'}

for c in snapshot['countries']:
    sources = []
    for sid in c['sourceIds']:
        s = by_source.get(sid, {})
        contexts = enrichment.get(sid, {}).get('contexts', [])
        native_types = sorted({type_names.get(ctx.get('lane'), ctx.get('lane', 'Source reference')) for ctx in contexts if ctx.get('iso2') == c['code']})
        sources.append({'id':sid,'name':next(iter(s.get('names') or []), discovery_sources.get(sid,{}).get('title',sid)), 'url':s.get('url') or discovery_sources.get(sid,{}).get('url'), 'dataType':', '.join(native_types) or 'Food data / source reference'})
    receipts = []
    for r in c['receipts']:
        s = by_source.get(r.get('sourceId'),{})
        # No headers, cookies, raw records, personal profiles, or download payloads.
        receipts.append({**{key:r.get(key) for key in ['kind','sourceId','status','reportedBytes','asOf','rights','category']}, 'sourceName':next(iter(s.get('names') or []),None)})
    countries[c['code']] = {key:c.get(key) for key in ['code','name','owner','assignment','registeredSourceCount','asOf','gap']}
    countries[c['code']].update(sources=sources,receipts=receipts,categories=c['categories'],evidence=[])

def stages(acquired=None, normalized=None):
    return {'discovered':True,'acquired':acquired,'normalized':normalized,'gold-reviewed':None,'translated':None}

def add(code, **evidence):
    assert code in countries
    countries[code]['evidence'].append(evidence)

source_info = {
    'off': ('Open Food Facts', 'ingredients', 'Product and nutrient-profile references', 'https://world.openfoodfacts.org/data'),
    'prices': ('Open Prices', 'prices/baskets', 'Price observation references', 'https://prices.openfoodfacts.org/'),
    'overture-food-places': ('Overture food places', 'retailers/providers', 'Indexed food-place references', 'https://docs.overturemaps.org/guides/places/'),
    'wikidata-food-businesses': ('Wikidata food businesses', 'retailers/providers', 'Organizations and source roles', 'https://www.wikidata.org/'),
    'dietary-guidelines': ('Dietary guideline references', 'dietary references', 'Source assertions; not guide content', 'https://www.fao.org/nutrition/education/food-dietary-guidelines/'),
    'afcd': ('Australian Food Composition Database', 'nutrition', 'Food composition', None),
    'ciqual': ('Ciqual', 'nutrition', 'Food composition', None),
    'cofid': ('CoFID', 'nutrition', 'Food composition', None),
    'germany-bls': ('German BLS', 'nutrition', 'Food composition', None),
    'matvaretabellen': ('Matvaretabellen', 'nutrition', 'Food composition', None),
    'frida': ('Frida', 'nutrition', 'Food composition', None),
    'fineli': ('Fineli', 'nutrition', 'Food composition and source flags', None),
    'foodfiles': ('FOODfiles', 'nutrition', 'Food composition', None),
    'sweden-food': ('Swedish food composition', 'nutrition', 'Food composition', None),
    'cnf': ('Canadian Nutrient File', 'nutrition', 'Food composition', None),
    'mext': ('MEXT food composition', 'nutrition', 'Food composition', None),
    'usda-files': ('USDA FoodData Central', 'nutrition', 'Food and nutrient records', 'https://fdc.nal.usda.gov/download-datasets/')
}
collections = {c['sourceId']: c for c in execution['collections']}
manifest_cache = {}

for c in execution['countries']:
    code = c['iso2']
    for sid, counts in c.get('localObservedRecords',{}).items():
        title, category, dtype, url = source_info[sid]
        col = collections.get(sid,{})
        manifest = {}
        # Only named national composition collections are attributed to their country here.
        if sid not in ['off','prices','overture-food-places','wikidata-food-businesses','dietary-guidelines','usda-files'] and col.get('manifest'):
            p = Path(col['manifest'])
            if p.exists():
                if p not in manifest_cache: manifest_cache[p] = read(p, 'Retained collection: '+title)
                manifest = manifest_cache[p]
        if not url:
            composition = discovery_countries.get(code,{}).get('composition')
            if isinstance(composition,dict):
                ds = discovery_sources.get('discovery:'+str(composition.get('source_id')), {})
                url = ds.get('url')
        metrics = [{'value':value,'unit':key.replace('all-normalized-records','indexed normalized records').replace('nutrientProfile','nutrient profiles').replace('sourceAssertion','source assertions').replace('organization','organizations')} for key,value in counts.items()]
        is_reference = sid == 'dietary-guidelines'
        scope = ('Country attribution and counts reported in the 13 October execution index. Source assertions, not current countrywide availability. Role counts may overlap organizations; metrics must not be added together.')
        if manifest:
            scope = manifest.get('scope') or col.get('scope') or scope
        add(code, title=title, category=category, dataType=dtype, url=url,
            stages=stages(True if manifest.get('sourceFiles') else None, None if is_reference else True),
            metrics=metrics,scope=scope,asOf=manifest.get('completedAt') or execution['checkedAt'],
            evidenceLabel='Retained collection manifest + country index' if manifest else 'Historical country execution index',
            gap=('Source reference count only; guide content, acquisition and semantic acceptance not established.' if is_reference else 'Gold review and translation are not established by normalization or an indexed record count. Current original custody is unknown unless a manifest is identified.'))

owner53 = DATA/'country-bundles-20261016/owner-53'
manifest53 = read(owner53/'manifest.json', 'Owner 53 scoped retained-original packet')
for code in manifest53['countries']:
    progress = read(owner53/code/'category-progress.json')
    for category in countries[code]['categories']:
        category['note'] = progress.get(category['name'])
    countries[code]['gap'] = progress.get('nextAction') or countries[code]['gap']
    countries[code]['asOf'] = progress.get('utc') or countries[code]['asOf']
for code, title, scope in [
    ('LK','Ministry of Health · Food Basket guide','One four-page donation / daily uncooked food basket guide. Not retail price observations. Source nutrient totals have unresolved inconsistencies; no silent correction or dietary suitability inferred.'),
    ('LR','Ministry of Health · Infant and young child feeding booklet','One finite infant / young child feeding booklet. Child-specific scope is not general adult or national dietary suitability.')]:
    receipt_path = owner53/code/'finite-original/receipt.json'
    r = read(receipt_path)
    assert Path(r['path']).is_file() and Path(r['path']).stat().st_size == r['bodyBytes']
    add(code,title=title,category='dietary references',dataType='Retained PDF original',url=r['url'],stages=stages(True),metrics=[{'value':1,'unit':'finite document'},{'value':r['bodyBytes'],'unit':'retained bytes'}],scope=scope,asOf=r['utc'],evidenceLabel='Original custody receipt',evidenceHash=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),gap=r.get('permission','Reuse and semantic admission remain held.'),review='Packet ready for independent review; no semantic gold or translation acceptance inferred')

for code in ['LR','LU']:
    profile_path = owner53/code/'retained-csv-profile.json'
    prof = read(profile_path)
    assert Path(prof['originalPath']).is_file() and Path(prof['originalPath']).stat().st_size == prof['originalBytes']
    original_receipt = read(prof['receipt'])
    url = original_receipt.get('canonicalURL') or original_receipt.get('url') or original_receipt.get('source_url')
    unit = prof.get('unitSourceLiterals', ['Weight per thousand'] if code=='LU' else [])
    rows = prof.get('nonHXLRows')
    if code=='LU': rows=15482
    add(code,title='WFP monitored-market observations' if code=='LR' else 'STATEC · E5407 index weights',category='prices/baskets',dataType='Retained CSV profile',url=url,stages=stages(True),metrics=[{'value':rows,'unit':'source data rows'},{'value':prof['originalBytes'],'unit':'retained bytes'}],units=unit,scope=prof.get('qualification') or prof.get('scope') or 'Source structure readback only. No accepted normalized records inferred.',asOf=manifest53['frozenUTC'],evidenceLabel='Retained CSV structural profile',evidenceHash=hashlib.sha256(profile_path.read_bytes()).hexdigest(),gap=prof.get('redistributionAdmission','Held; no semantic, normalized or translation admission.'),review='Structural readback only; not gold review')

jersey = DATA/'country-bundles-20261016/owner-45/JE/prices-increment-1'
j = read(jersey/'data-receipt.json', 'Jersey price-index finite-resource receipt')
freeze = read(jersey/'frozen-increment.json')
binding = read(jersey.parent.parent/'review46-binding.json', 'Prior scoped review binding; excludes new Jersey CSV')
assert Path(j['file']['path']).is_file() and Path(j['file']['path']).stat().st_size == j['file']['bytes']
add('JE',title='Statistics Jersey · RPI group indices',category='prices/baskets',dataType='Retained CSV original',url=j['sourceURL'],stages=stages(True),metrics=[{'value':j['validation']['rowsExcludingHeader'],'unit':'quarterly source rows'},{'value':j['file']['bytes'],'unit':'retained bytes'}],units=['RPI source index values; not retail prices'],scope=j['scope'],asOf=j['operations']['downloadedFileMtimeUTC'],evidenceLabel='Finite-resource receipt; source size/MD5 matched',evidenceHash=hashlib.sha256((jersey/'data-receipt.json').read_bytes()).hexdigest(),gap='New increment is unreviewed. Exact request timestamp unavailable; file modification time shown. '+j['licence'],review=binding['verdict']+'; prior exact bundle only, not this CSV')

result = {
    'schema':'offmenu-country-progress-view/1',
    'generatedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'evidenceAsOf':snapshot['evidenceAsOf'],
    'counts':snapshot['counts'],
    'limitations':snapshot['limitations'],
    'method':'Metadata snapshot only. Country allocation and discovery are from the Gateway snapshot. Historical normalized counts retain their own execution dates; newer finite originals are separate receipt-backed evidence. Metric types, countries, rights, gold review and translations are never inferred from discovery totals. Raw corpus files are not sent to this page.',
    'inputs':inputs,
    'countries':sorted(countries.values(),key=lambda c:c['name'].casefold()),
    'shared':[
        {'title':'Open Food Facts','url':'https://world.openfoodfacts.org/data','scope':'Global product source. Country-attributed index counts are shown separately; unknown-country rows are not allocated.'},
        {'title':'Open Prices','url':'https://prices.openfoodfacts.org/','scope':'Global price observations. No current national price completeness inferred.'},
        {'title':'Overture Maps','url':'https://docs.overturemaps.org/guides/places/','scope':'Global place references. A mapped place is not an acquired menu, current trading status or complete retailer census.'},
        {'title':'Wikidata','url':'https://www.wikidata.org/','scope':'Global source assertions. Organization country is not product market or ingredient origin.'}
    ]
}
assert len(result['countries']) == len({c['code'] for c in result['countries']}) == 249
assert sum(c['assignment']=='assigned' for c in result['countries']) == 155
payload = json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n'
(OUT/'country-progress.json').write_text(payload)
print(json.dumps({'countries':249,'assigned':155,'unassigned':94,'bytes':len(payload.encode()),'evidenceItems':sum(len(c['evidence']) for c in result['countries']),'sourceLeads':sum(len(c['sources']) for c in result['countries']),'gatewaySnapshotSha256':EXPECTED,'inputs':len(inputs)}))
