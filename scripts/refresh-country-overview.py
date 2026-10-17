from pathlib import Path
import json, hashlib, gzip, datetime

OUT=Path(__file__).resolve().parents[1]/'public'
BASE=Path('/home/user/Documents/Codex/2026-10-13/task-3')
DATA=Path('/home/user/src/offmenu-data')
x=json.loads((OUT/'country-progress.json').read_text())
p=BASE/'country-progress-ui-examples.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='351be520f9b7ec9e33d208afeb555591858c1f5f326a78a141832f12cd4facb9'
examples=json.loads(p.read_text())
allocation=json.loads((BASE/'country-allocation-extension-20261016-001.json').read_text())
obligations=json.loads((BASE/'interim-obligation-index.json').read_text())
countries={c['code']:c for c in x['countries']}
for assignment in allocation['assignments']:
    for item in assignment['countries']:
        c=countries[item['code']];c['owner']=assignment['owner'];c['assignment']='assigned'
for code in allocation['queuedCountries']:
    countries[code]['assignment']='unassigned';countries[code]['owner']=None
assert sum(c['assignment']=='assigned' for c in countries.values())==160
x['counts']['assigned']=160;x['counts']['unassigned']=89
x['allocationAsOf']=allocation['updatedUTC']
x['overview']=examples['overview']
x['currentWork']=examples['currentWork']
x['nextSteps']=examples['nextSteps']
for c in countries.values():
    c['samples']=[]
    requirement=next((r for r in obligations['requirements'] if r.get('owner')==c['owner'] and r.get('id','').startswith('COUNTRY-')),None)
    status=(requirement or {}).get('state','')
    if c['assignment']=='unassigned':label='Queued';now='Awaiting a country portfolio assignment';next_step='Assign the next portfolio'
    elif 'review' in status:label='In review';now='Source evidence and country portfolio prepared';next_step='Review the latest source records and corrections'
    elif 'active' in status or 'pickup' in status:label='In progress';now='Source metadata and retained records being reconciled';next_step='Finish the current source and category inventory'
    elif 'blocked' in status:label='On hold';now='Country portfolio has a recorded blocker';next_step='Resolve the current owner’s recorded blocker'
    elif 'complete' in status or 'frozen' in status:label='Prepared';now='A source-evidence packet has been prepared';next_step='Review the prepared packet and connect its records'
    else:label='Assigned';now='Country portfolio assigned';next_step='Reconcile the latest holdings and source evidence'
    c['work']={'label':label,'now':now,'next':next_step,'asOf':obligations['updatedUTC'],'sourceState':status}
for sample in examples['samples']:
    code=sample['country'];r=sample['record']
    if code=='LY':
        title=r['commodity'];subtitle=f"{r['market']} · {r['date']}"
        fields=[{'label':'Observed price','value':r['price']+' '+r['currency']},{'label':'Source unit','value':r['unit']},{'label':'Price type','value':r['pricetype']}]
    else:
        title='Food & all-items price indices';subtitle=r['Quarter']+' '+r['Year']
        fields=[{'label':'Food index','value':r['Food']},{'label':'All-items index','value':r['All Items']},{'label':'Units','value':'index points'}]
    countries[code]['samples'].append({'title':title,'subtitle':subtitle,'fields':fields,'sourceURL':sample.get('sourceURL'),'sourceHash':sample['sourceSHA256'],'recordId':'CSV line '+str(sample['csvLine']),'attribution':sample.get('attribution') or 'Statistics Jersey','issue':sample.get('specificIssue'),'category':'prices/baskets'})
countries['LY']['work'].update(label='In progress',now='Price observations and market-ID joins',next='Qualify observation fields and connect markets')
countries['LY']['evidence'].insert(0,{'title':'WFP price and market CSVs','category':'prices/baskets','dataType':'Retained CSVs','url':'https://data.humdata.org/dataset/wfp-food-prices-for-libya','stages':{'discovered':True,'acquired':True,'normalized':None,'gold-reviewed':None,'translated':None},'metrics':[{'value':69474,'unit':'price rows · custodian-reported'},{'value':53,'unit':'market rows · custodian-reported'}],'scope':'Retained custodian receipt reports June 2017–May 2026 observations. Counts not freshly enumerated.','asOf':examples['generatedUTC'],'evidenceLabel':'Gateway custodian-reported holdings','gap':'Exact observation semantics and market-ID joins are underway.'})

# Read only a bounded first record from each retained normalized collection.
# Export whitelisted sample fields, never full records or raw source archives.
for folder in ['afcd-3','ciqual-2025','cofid-2021','cnf-2015','mext-2023-main','germany-bls-4.0','matvaretabellen-2026','frida-5.5','fineli-20.0','foodfiles-2024-v01','sweden-food-2026-07-01']:
    path=DATA/folder/'normalized.jsonl.gz'
    if not path.exists():continue
    with gzip.open(path,'rt') as stream:record=json.loads(next(stream))
    if isinstance(record,list):record=record[0]
    d=record.get('data',{});provenance=record.get('provenance',{})
    if provenance.get('visibility') not in ['public',None]:continue
    fields=[]
    basis=d.get('basis',{})
    if basis.get('amount') is not None:fields.append({'label':'Basis','value':str(basis['amount'])+' '+str(basis.get('unit',''))})
    for key in ['protein','fat','energyKJ','energy']:
        value=d.get('nutrients',{}).get(key)
        if isinstance(value,dict) and value.get('value') is not None:
            fields.append({'label':{'energyKJ':'Energy','energy':'Energy','protein':'Protein','fat':'Fat'}[key],'value':str(value['value'])+' '+str(value.get('unit',''))})
        if len(fields)>=3:break
    if not fields:continue
    for code in record.get('countries',[]):
        if code not in countries:continue
        countries[code]['samples'].append({'title':d.get('foodName') or record['id'],'subtitle':'Food composition · '+str(provenance.get('sourceDate') or provenance.get('releaseId') or folder),'fields':fields,'sourceURL':provenance.get('url'),'recordId':record.get('id'),'attribution':provenance.get('attribution') or provenance.get('sourceId'),'category':'nutrition'})

# Exact retained CSV row from the structural profile; includes original unit and date.
profile=json.loads((DATA/'country-bundles-20261016/owner-53/LR/retained-csv-profile.json').read_text())
row=dict(zip(*profile['headerAndPreamble']))
countries['LR']['samples'].append({'title':row['commodity'],'subtitle':row['market']+' · '+row['date'],'fields':[{'label':'Observed price','value':row['price']+' '+row['currency']},{'label':'Source unit','value':row['unit']},{'label':'Price type','value':row['pricetype']}],'sourceHash':profile['originalSHA256'],'recordId':'First retained CSV data row','attribution':'WFP / HDX retained source profile','category':'prices/baskets'})
x['generatedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
x['inputs'].append({'label':'Gateway retained samples and current work','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'asOf':examples['generatedUTC']})
(OUT/'country-progress.json').write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'assigned':160,'queued':89,'samples':sum(len(c['samples']) for c in countries.values()),'sampleCountries':sum(bool(c['samples']) for c in countries.values()),'allocationAsOf':x['allocationAsOf']}))
