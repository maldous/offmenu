#!/usr/bin/env python3
"""One fixed, deterministic inventory/acquisition/preparation pass. No discovery or AI."""
from __future__ import annotations
from collections import Counter,defaultdict
from copy import deepcopy
import importlib.util,json,os,re,stat,sys,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('global_fixed_batch',ROOT/'scripts/acquire-fixed-batch.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
a=b.a;save=b.save
from offmenu.refresh import media_preparation as media
SCHEMA='offmenu-global-collection-result/1'
SELECTION_PIN=('docs/collection-selections/global-original-selection.json','d400e7aa7d998ec3e327095332a3ff1ccfe03f1421c5ccb15e237989bb8970c1')
MANIFEST_PIN=('docs/collection-selections/global-known-assets-runtime.json','8474db835ee63c70c01e0babce3cbfac77324eac51640a351eece47cdddb9bfb')
MAX_ASSETS=10000;MAX_SECONDS=1200;MAX_OUTPUT_BYTES=1024**3;MAX_SUMMARY=96*1024
STATES=('ready-nextstage','held','unsupported','error','unverified','missing-contract','retained','eligible')
CUSTODY=('unverified','held','no-path','inaccessible','path-absent','unsafe-path','not-regular','extent-mismatch','stat-observed','verified-original')
GLOBAL_ERRORS={'global-outer-failure','global-config-invalid','global-deadline-exhausted','global-output-budget','global-checkpoint-failed','global-preparation-unavailable','global-original-unavailable','global-source-conflict'}
ERRORS=b.ERRORS|GLOBAL_ERRORS|media.ERROR_CODES

def pinned(pin):return a.strict_json(a.preparation_module().pinned_bytes(ROOT,pin))

def selection_config():
 value=pinned(SELECTION_PIN)
 if not isinstance(value,dict) or value.get('schemaVersion')!='offmenu-global-source-selection/1' or set(value)!={'schemaVersion','batchId','sources','maximumRequests','maximumTransferBytes','wholeOperationSeconds','minimumCacheSeconds','planningGuardBytes','floorAlreadyIncluded','evidence','coordinatorIntent','privateOriginalDownload','preparation'}:raise a.RefreshError('global-config-invalid')
 if (not 1<=len(value['sources'])<=32 or value['maximumRequests']!=len(value['sources']) or value['wholeOperationSeconds']!=MAX_SECONDS
     or value['maximumTransferBytes']!=sum(s['hardTransferBytes'] for s in value['sources']) or value['maximumTransferBytes']>256*1024**2):raise a.RefreshError('global-config-invalid')
 # Reuse the reviewed closed source-contract validator in fixed bounded slices.
 for offset in range(0,len(value['sources']),b.MAX_SOURCES):
  chunk=deepcopy(value);chunk.pop('preparation');chunk['schemaVersion']='offmenu-fixed-source-batch-selection/1';chunk['sources']=value['sources'][offset:offset+b.MAX_SOURCES];chunk['maximumRequests']=len(chunk['sources']);keys={s['sourceKey'] for s in chunk['sources']}
  mode=chunk['privateOriginalDownload'];mode['predecessors']=[p for p in mode['predecessors'] if p['sourceKey'] in keys];mode['freshSources']=[k for k in mode['freshSources'] if k in keys]
  if not mode['predecessors']:mode['diagnosticReportPin']=None
  b.validate_selection(chunk)
 for index,source in enumerate(value['sources']):
  for other in value['sources'][:index]:
   if a.exact_source_match(source,other) or a.exact_source_match(other,source):raise a.RefreshError('global-config-invalid')
 save.validate_mode(value['privateOriginalDownload'],value,a)
 for pin in value['evidence']:a.preparation_module().pinned_bytes(ROOT,(pin['path'],pin['sha256']))
 seen=set()
 for p in value['preparation']:
  if not isinstance(p,dict) or set(p)!={'sourceKey','country','type','permissions','holds','expectedMediaTypes','parameters','retainedOriginal','downstreamHolds'} or p['sourceKey'] in seen:raise a.RefreshError('global-config-invalid')
  seen.add(p['sourceKey']);template={k:p[k] for k in ('permissions','holds','expectedMediaTypes','parameters')};media.validate_contract({'schemaVersion':media.SCHEMA,'assetId':'fixture','expectedSHA256':'0'*64,'expectedBytes':1,**template})
  retained=p['retainedOriginal']
  if retained is not None and (set(retained)!={'path','sha256','bytes'} or not re.fullmatch('[a-f0-9]{64}',retained['sha256']) or type(retained['bytes']) is not int or retained['bytes']<=0 or not retained['path'].startswith('/srv/offmenu-refresh/outputs/collection/source-cache/objects/')):raise a.RefreshError('global-config-invalid')
 return value

def manifest_config():
 if MANIFEST_PIN is None:raise a.RefreshError('global-config-invalid')
 value=pinned(MANIFEST_PIN)
 return validate_manifest(value)

def validate_manifest(value):
 if not isinstance(value,dict) or value.get('schemaVersion')!='offmenu-global-collection-manifest/1':raise a.RefreshError('global-config-invalid')
 countries=value['countries'];types=value['types'];assets=value['assets'];cells=value['cells']
 if len(countries)!=249 or len(set(countries))!=249 or any(not re.fullmatch('[A-Z]{2}',c) for c in countries) or len(types)!=13 or len(set(types))!=13 or not 1<=len(assets)<=MAX_ASSETS or len(cells)!=249*13:raise a.RefreshError('global-config-invalid')
 ids=set()
 for asset in assets:
  if not isinstance(asset,dict) or not isinstance(asset.get('assetId'),str) or asset['assetId'] in ids or asset['disposition'] not in STATES:raise a.RefreshError('global-config-invalid')
  ids.add(asset['assetId'])
  for bind in asset['bindings']:
   if set(bind)!={'country','type'} or bind['country'] not in countries or bind['type'] not in types:raise a.RefreshError('global-config-invalid')
 expected={(c,t) for c in countries for t in types};actual=set()
 for cell in cells:
  pair=(cell['country'],cell['type'])
  if pair not in expected or pair in actual or any(i not in ids for i in cell['assetIds']):raise a.RefreshError('global-config-invalid')
  actual.add(pair)
 return value

def stat_original(retained):
 """Only fixed metadata paths; never opens a source body or follows a symlink."""
 if not retained or not retained.get('path'):return 'no-path'
 path=Path(retained['path'])
 if not path.is_absolute() or '..' in path.parts:return 'unsafe-path'
 try:
  for parent in reversed(path.parents):
   info=parent.lstat()
   if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):return 'unsafe-path'
   if not os.access(parent,os.X_OK):return 'inaccessible'
  info=path.lstat()
  if stat.S_ISLNK(info.st_mode):return 'unsafe-path'
  if not stat.S_ISREG(info.st_mode):return 'not-regular'
  if retained.get('bytes') is not None and info.st_size!=retained['bytes']:return 'extent-mismatch'
  return 'stat-observed'
 except PermissionError:return 'inaccessible'
 except FileNotFoundError:return 'path-absent'
 except OSError:return 'inaccessible'

def ranges(indices):
 result=[]
 for index in sorted(indices):
  if result and index==result[-1][1]+1:result[-1][1]=index
  else:result.append([index,index])
 return result

def group_outcomes(outcomes):
 groups=defaultdict(list)
 for i,row in enumerate(outcomes):groups[(row['custody'],row['stage'],row['code'])].append(i)
 return [{'custody':key[0],'stage':key[1],'code':key[2],'assetRanges':ranges(indices)} for key,indices in sorted(groups.items(),key=lambda item:repr(item[0]))]

def expand_outcomes(groups,count):
 rows=[None]*count
 for group in groups:
  if not isinstance(group,dict) or set(group)!={'custody','stage','code','assetRanges'} or group['custody'] not in CUSTODY or group['stage'] not in STATES or (group['code'] is not None and group['code'] not in ERRORS):raise ValueError('invalid-global-summary')
  for pair in group['assetRanges']:
   if not isinstance(pair,list) or len(pair)!=2 or any(type(i) is not int for i in pair) or not 0<=pair[0]<=pair[1]<count:raise ValueError('invalid-global-summary')
   for i in range(pair[0],pair[1]+1):
    if rows[i] is not None:raise ValueError('invalid-global-summary')
    rows[i]={k:group[k] for k in ('custody','stage','code')}
 if any(row is None for row in rows):raise ValueError('invalid-global-summary')
 return rows

def country_cells(manifest,outcomes):
 ids={row['assetId']:i for i,row in enumerate(manifest['assets'])};cells=[]
 for cell in manifest['cells']:
  counts=[0]*len(STATES)
  for asset_id in set(cell['assetIds']):counts[STATES.index(outcomes[ids[asset_id]]['stage'])]+=1
  if not cell['assetIds']:counts[STATES.index('missing-contract')]=1
  cells.append(counts)
 default=[0]*len(STATES);default[STATES.index('missing-contract')]=1
 return {'default':default,'overrides':[[index,row] for index,row in enumerate(cells) if row!=default]}

def run_preparation(asset_id,contract,original,folder,deadline,remaining):
 if remaining<=0:return None,'global-output-budget',0
 maximum=min(remaining,media.MAX_OUTPUT_BYTES);reservation=folder/'reservation.bin';fd=identity=None;result=None;code=None;used=0
 try:
  save.private_directory(folder,a)
  fd,identity=a.reserve(reservation,folder,deadline,expected_bytes=maximum,max_bytes=maximum)
  result=media.prepare_asset(contract,original,folder/'prepared',deadline,maximum_output_bytes=maximum,minimum_free_bytes=a.GUARD)
  used=sum(row.get('bytes',0) for row in result.get('outputs',[]))
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError) as error:
  code=str(error) if isinstance(error,a.RefreshError) and str(error) in ERRORS else 'global-preparation-unavailable'
 finally:
  if fd is not None:
   try:a.release_own_reservation(reservation,fd,identity)
   except (a.RefreshError,OSError,ValueError,TypeError,KeyError):code='reservation-release-failed'
 return result,code,used


def preparation_summary(detail):
 if detail is None:return None
 metrics=detail.get('metrics') or {}
 allowed=('pageCount','selectedPageCount','sheetCount','selectedSheetCount','recordCount','cellCount','archiveMemberCount','selectedExtentComplete')
 return {'status':detail['status'],'errorCode':detail['errorCode'],'stages':detail['stages'],
  'actualMediaType':detail['actualMediaType'],'originalSHA256':detail['originalSHA256'],'originalBytes':detail['originalBytes'],
  'preparedBytes':0 if detail.get('reusedFromAssetIndex') is not None else sum(row['bytes'] for row in detail['outputs']),'preparedFiles':len(detail['outputs']),
  'nextStageReady':detail['nextStageReady'],'detailSHA256':a.sha(a.canonical(detail)),
  'metrics':{k:metrics[k] for k in allowed if k in metrics},'reusedFromAssetIndex':detail.get('reusedFromAssetIndex')}


def runtime_capabilities():
 try:return media.capabilities()
 except Exception:
  return {'handlerVersion':media.VERSION,'pythonVersion':sys.version.split()[0],'isolatedWorker':False,
   'stdlibFormats':['csv','tsv','json','xml','html','zip','xlsx','docx'],
   'optionalParsers':{key:{'available':False,'version':None} for key in ('pypdf','xlrd','poppler')}}

def run_global(manifest,selected,*,transport=None,adverse_evidence=(),prepare=run_preparation,progress=None):
 source_assets={}
 for i,asset in enumerate(manifest['assets']):
  if asset.get('sourceKey'):source_assets.setdefault(asset['sourceKey'],[]).append(i)
 needed={s['sourceKey'] for s in selected['sources']}|{p['sourceKey'] for p in selected['preparation']}
 if not needed<=set(source_assets):raise a.RefreshError('global-config-invalid')
 capabilities=runtime_capabilities()
 deadline=time.monotonic()+MAX_SECONDS-20;meter={'requests':0,'bodyBytesRead':0,'maximumRequests':selected['maximumRequests'],'maximumBytes':selected['maximumTransferBytes']}
 outcomes=[];changes=[]
 if progress is not None:progress.update(meter=meter,changes=changes)
 persisted=0;output_bytes=0;checkpoints={};errors=[];manifest_sha=a.sha(a.canonical(manifest))
 work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection');root=save.private_directory(work/'global-collection',a);run_dir=save.private_directory(root/manifest_sha,a)
 stat_rows=[];asset_paths=defaultdict(list)
 for target in manifest.get('statTargets',[]):
  extents={x.get('bytes') for x in target.get('recordedIdentities',[]) if type(x.get('bytes')) is int}
  state='unverified' if time.monotonic()>=deadline else stat_original({'path':target['path'],'bytes':next(iter(extents)) if len(extents)==1 else None})
  stat_rows.append(state)
  for identity in target['assetIds']:asset_paths[identity].append(state)
 for asset in manifest['assets']:
  retained=asset.get('retainedOriginal');custody=('unverified' if time.monotonic()>=deadline else stat_original(retained)) if retained else 'held' if asset['disposition']=='held' else 'no-path'
  if asset['assetId'] in asset_paths:
   observed=asset_paths[asset['assetId']];custody='stat-observed' if 'stat-observed' in observed else observed[0] if len(set(observed))==1 else 'unverified'
  stage=asset['disposition']
  if stage=='retained' and custody not in {'stat-observed','verified-original'}:stage='unverified'
  outcomes.append({'custody':custody,'stage':stage,'code':None})
 ids={row['assetId']:i for i,row in enumerate(manifest['assets'])};source_assets={}
 for i,asset in enumerate(manifest['assets']):
  if asset.get('sourceKey'):source_assets.setdefault(asset['sourceKey'],[]).append(i)
 preparation={row['sourceKey']:row for row in selected['preparation']};completed=set();preparation_seen={};host_started={};pending_preparation=[]
 def checkpoint(index,detail):
  nonlocal persisted
  if time.monotonic()>=deadline+10:
   errors.append('global-deadline-exhausted');return
  payload={'schemaVersion':'offmenu-global-asset-checkpoint/1','manifestSHA256':manifest_sha,'assetIndex':index,'assetId':manifest['assets'][index]['assetId'],'outcome':outcomes[index],'detail':detail}
  digest=a.sha(a.canonical(payload));path=run_dir/('asset-'+str(index)+'-'+digest+'.json')
  try:a.write_immutable(path,payload);checkpoints[index]=digest;persisted=len(checkpoints)
  except (a.RefreshError,OSError,ValueError,TypeError,KeyError):errors.append('global-checkpoint-failed')
 def prepare_one(index,p,identity,path):
  nonlocal output_bytes
  asset=manifest['assets'][index];template={key:deepcopy(p[key]) for key in ('permissions','holds','expectedMediaTypes','parameters')}
  source_stage_holds=set(asset.get('sourceStageHolds',[]))|set(asset.get('holds',[]))
  template['holds']=sorted(set(template['holds'])|(source_stage_holds&{'read','extract','copy','all'}))
  if asset['disposition']=='held':
   outcomes[index]['stage']='held';return None
  contract={'schemaVersion':media.SCHEMA,'assetId':asset['assetId'],'expectedSHA256':identity['sha256'],'expectedBytes':identity['bytes'],**template}
  identity_key=a.sha(a.canonical({'path':str(path),'sha256':identity['sha256'],'bytes':identity['bytes'],**template}))
  if identity_key in preparation_seen:
   previous,detail=preparation_seen[identity_key];outcomes[index]=dict(outcomes[previous]);return {**detail,'reusedFromAssetIndex':previous}
  try:
   detail,code,used=prepare(asset['assetId'],contract,Path(path),run_dir/a.sha(asset['assetId'].encode()),deadline,MAX_OUTPUT_BYTES-output_bytes);output_bytes+=used
  except Exception:detail=None;code='global-preparation-unavailable'
  if detail is None or code is not None:outcomes[index]['stage']='error';outcomes[index]['code']=code
  else:
   outcomes[index]['stage']={'ready':'ready-nextstage','held':'held','unsupported':'unsupported','failed':'error'}[detail['status']];outcomes[index]['code']=detail['errorCode']
   if detail['stages']['integrity']=='passed':outcomes[index]['custody']='verified-original'
  if detail is not None:preparation_seen[identity_key]=(index,detail)
  return detail
 for source in selected['sources']:
  indices=source_assets.get(source['sourceKey'],[])
  if not indices:raise a.RefreshError('global-config-invalid')
  index=indices[0];detail=None;error=None;before=dict(meter)
  try:
   if time.monotonic()>=deadline:raise a.RefreshError('global-deadline-exhausted')
   if any(a.exact_source_match(e,source) for e in adverse_evidence):raise a.RefreshError('global-source-conflict')
   if any(manifest['assets'][i]['disposition']!='eligible' for i in indices):raise a.RefreshError('global-source-conflict')
   host=urlsplit(source['url']).hostname;delay=max(0,host_started.get(host,0)+2-time.monotonic())
   if time.monotonic()+delay>=deadline:raise a.RefreshError('global-deadline-exhausted')
   if delay:time.sleep(delay)
   host_started[host]=time.monotonic()
   detail=save.run_selected(source,adapter=a,mode=selected['privateOriginalDownload'],transport=transport,deadline=deadline,batch_meter=meter)
  except Exception as failure:error=str(failure) if isinstance(failure,a.RefreshError) and str(failure) in ERRORS else 'collector-rejected'
  item=b.item_report(source,detail,error,{key:meter[key]-before[key] for key in ('requests','bodyBytesRead')});prep_detail=None
  for i in indices:
   outcomes[i]={'custody':'verified-original' if item['status']=='verified-private-original' else outcomes[i]['custody'],'stage':'retained' if item['status']=='verified-private-original' else 'error','code':item['errorCode']}
  if item['status']=='verified-private-original' and source['sourceKey'] in preparation:
   identity={'sha256':item['originalSHA256'],'bytes':item['verifiedBytes']};original=work/'private-originals'/a.sha(a.canonical(source))/'original.pdf';pending_preparation.append((index,indices,preparation[source['sourceKey']],identity,original,item))
  for i in indices:checkpoint(i,{'acquisition':item,'preparation':None});completed.add(i)
  changes.append({'assetIndex':index,'acquisition':item,'preparation':None})
 # Attempt every eligible transfer before spending the remaining envelope on preparation.
 for index,indices,p,identity,original,item in pending_preparation:
  detail=prepare_one(index,p,identity,original)
  for i in indices:outcomes[i]=dict(outcomes[index]);checkpoint(i,{'acquisition':item,'preparation':detail})
  next(change for change in changes if change['assetIndex']==index)['preparation']=preparation_summary(detail)
 for key,p in preparation.items():
  if p['retainedOriginal'] is None:continue
  indices=source_assets.get(key,[])
  if not indices:raise a.RefreshError('global-config-invalid')
  index=indices[0];identity=p['retainedOriginal'];detail=prepare_one(index,p,identity,identity['path'])
  for i in indices:outcomes[i]=dict(outcomes[index]);checkpoint(i,{'acquisition':None,'preparation':detail});completed.add(i)
  changes.append({'assetIndex':index,'acquisition':None,'preparation':preparation_summary(detail)})
 # Every known row receives a custody/source/format/preparation disposition.
 for i,asset in enumerate(manifest['assets']):
  if i in completed:continue
  contract=asset.get('preparationContract');original=asset.get('retainedOriginal')
  if contract is not None and original is not None and outcomes[i]['custody']=='stat-observed' and asset['disposition']!='held':
   p={key:contract[key] for key in ('permissions','holds','expectedMediaTypes','parameters')};detail=prepare_one(i,p,original,original['path']);changes.append({'assetIndex':i,'acquisition':None,'preparation':preparation_summary(detail)});checkpoint(i,{'acquisition':None,'preparation':detail})
  else:pass  # Complete static outcomes are atomically checkpointed once below.
 report={'schemaVersion':SCHEMA,'status':'complete-with-errors' if errors or any(row['stage']=='error' for row in outcomes) else 'complete','errorCode':None,
  'manifestSHA256':manifest_sha,'selectionSHA256':a.sha(a.canonical(selected)),'assetCount':len(outcomes),'countryCount':249,'typeCount':13,
  'networkRequests':meter['requests'],'networkBytesRead':meter['bodyBytesRead'],'preparedBytes':output_bytes,'assetOutcomeGroups':group_outcomes(outcomes),'cellStageCounts':country_cells(manifest,outcomes),'changes':changes,
  'statPathCount':len(stat_rows),'statOutcomeGroups':[{'state':state,'pathRanges':ranges([i for i,value in enumerate(stat_rows) if value==state])} for state in sorted(set(stat_rows))],
  'checkpointCount':persisted,'checkpointIndexSHA256':a.sha(a.canonical(sorted(checkpoints.items()))),'detailSHA256':None,'detailPersisted':False,
  'runtimeCapabilities':capabilities,'globalErrors':sorted(set(errors)),'maximumParallelTransfers':1,'maximumPerHostTransfers':1,'wholeOperationSeconds':MAX_SECONDS,**a.SAFETY}
 detail={'schemaVersion':'offmenu-global-collection-detail/1','summary':report,'checkpoints':sorted(checkpoints.items()),'assetOutcomes':outcomes};digest=a.sha(a.canonical(detail))
 try:a.write_immutable(run_dir/('result-'+digest+'.json'),detail);report.update(detailSHA256=digest,detailPersisted=True)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report['globalErrors']=sorted(set(report['globalErrors']+['global-checkpoint-failed']));report['status']='complete-with-errors'
 return report

def blocked_report(code):
 return {'schemaVersion':SCHEMA,'status':'blocked','errorCode':code,'networkRequests':0,'networkBytesRead':0,**a.SAFETY}

def validate_acquisition(item,source):
 if set(item)!=set(b.item_report(source,error='collector-rejected')):raise ValueError('invalid-global-summary')
 if item['sourceKey']!=source['sourceKey'] or item['sourceContractSHA256']!=a.sha(a.canonical(source)) or item['downstreamHolds']!=source['downstreamHolds']:raise ValueError('invalid-global-summary')
 success=item['status']=='verified-private-original'
 if item['status'] not in {'blocked','failed','verified-private-original'} or item['errorCode'] not in ERRORS|{None} or success!=(item['errorCode'] is None):raise ValueError('invalid-global-summary')
 for key,limit in [('networkRequests',1),('networkBytesRead',source['hardTransferBytes']),('verifiedBytes',source['hardTransferBytes']),('localBodyBytes',source['hardTransferBytes'])]:
  if type(item[key]) is not int or not 0<=item[key]<=limit:raise ValueError('invalid-global-summary')
 a.validate_response_metadata(item['responseMetadata']);save.validate_policy(item['responsePolicy'])
 if item['cacheStatus'] not in {None,'downloaded-200','reused-fresh'} or item['originalDisposition'] not in {None,'saved-original','retained-original-no-network'} or item['privateSaveState'] not in {None,'none','partial-retained','uncommitted-original','saved-original'} or type(item['detailPersisted']) is not bool:raise ValueError('invalid-global-summary')
 for key in ('originalSHA256','detailSHA256'):
  if item[key] is not None and (not isinstance(item[key],str) or not re.fullmatch('[a-f0-9]{64}',item[key])):raise ValueError('invalid-global-summary')
 if success and (not item['verifiedBytes'] or not item['originalSHA256'] or not item['detailPersisted'] or not item['detailSHA256'] or not b.bounded_text(item['originalAcquiredAt'],64) or item['originalDisposition'] is None or (source['expectedBytes'] is not None and item['verifiedBytes']!=source['expectedBytes'])):raise ValueError('invalid-global-summary')
 if not success and (item['verifiedBytes'] or item['originalSHA256'] is not None or item['originalAcquiredAt'] is not None):raise ValueError('invalid-global-summary')

def validate_preparation(item):
 keys={'status','errorCode','stages','actualMediaType','originalSHA256','originalBytes','preparedBytes','preparedFiles','nextStageReady','detailSHA256','metrics','reusedFromAssetIndex'}
 if set(item)!=keys or item['status'] not in {'ready','held','unsupported','failed'} or item['errorCode'] not in media.ERROR_CODES|{None} or type(item['nextStageReady']) is not bool:raise ValueError('invalid-global-summary')
 if item['nextStageReady']!=(item['status']=='ready') or (item['status']=='ready' and item['errorCode'] is not None):raise ValueError('invalid-global-summary')
 if not isinstance(item['stages'],dict) or set(item['stages'])!={'integrity','media','extraction'} or any(v not in {'not-run','passed','failed','held','unsupported'} for v in item['stages'].values()):raise ValueError('invalid-global-summary')
 if item['reusedFromAssetIndex'] is not None and (type(item['reusedFromAssetIndex']) is not int or not 0<=item['reusedFromAssetIndex']<MAX_ASSETS):raise ValueError('invalid-global-summary')
 if item['actualMediaType'] not in media.MIMES|{None}:raise ValueError('invalid-global-summary')
 for key in ('originalSHA256','detailSHA256'):
  if item[key] is not None and (not isinstance(item[key],str) or not re.fullmatch('[a-f0-9]{64}',item[key])):raise ValueError('invalid-global-summary')
 if item['detailSHA256'] is None:raise ValueError('invalid-global-summary')
 for key,limit in [('originalBytes',media.MAX_ORIGINAL_BYTES),('preparedBytes',media.MAX_OUTPUT_BYTES),('preparedFiles',media.MAX_OUTPUT_FILES)]:
  if item[key] is None and key=='originalBytes':continue
  if type(item[key]) is not int or not 0<=item[key]<=limit:raise ValueError('invalid-global-summary')
 if not isinstance(item['metrics'],dict) or not set(item['metrics'])<={'pageCount','selectedPageCount','sheetCount','selectedSheetCount','recordCount','cellCount','archiveMemberCount','selectedExtentComplete'}:raise ValueError('invalid-global-summary')
 for k,v in item['metrics'].items():
  if (type(v) is not bool if k=='selectedExtentComplete' else type(v) is not int or not 0<=v<=media.MAX_CELLS):raise ValueError('invalid-global-summary')

def projection_failure(selected,progress):
 meter=progress.get('meter',{'requests':0,'bodyBytesRead':0});items=[];sources={s['sourceKey']:s for s in selected['sources']}
 for change in progress.get('changes',[]):
  item=change.get('acquisition')
  if item is not None and item.get('sourceKey') in sources:
   try:validate_acquisition(item,sources[item['sourceKey']]);items.append(item)
   except (ValueError,TypeError,KeyError):pass
 return {'schemaVersion':SCHEMA,'status':'summary-projection-failed','errorCode':'global-outer-failure',
  'selectionSHA256':a.sha(a.canonical(selected)),'networkRequests':meter['requests'],'networkBytesRead':meter['bodyBytesRead'],
  'completedSources':items,**a.SAFETY}

def sanitize_report(report):
 if not isinstance(report,dict):raise ValueError('invalid-global-summary')
 if report.get('status')=='summary-projection-failed':
  selected=selection_config();sources={s['sourceKey']:s for s in selected['sources']}
  if set(report)!=set(projection_failure(selected,{})) or report['errorCode']!='global-outer-failure' or report['selectionSHA256']!=a.sha(a.canonical(selected)) or any(report[k] is not v for k,v in a.SAFETY.items()):raise ValueError('invalid-global-summary')
  if type(report['networkRequests']) is not int or not 0<=report['networkRequests']<=selected['maximumRequests'] or type(report['networkBytesRead']) is not int or not 0<=report['networkBytesRead']<=selected['maximumTransferBytes']:raise ValueError('invalid-global-summary')
  seen=set()
  for item in report['completedSources']:
   key=item['sourceKey']
   if key not in sources or key in seen:raise ValueError('invalid-global-summary')
   seen.add(key);validate_acquisition(item,sources[key])
  if sum(i['networkRequests'] for i in report['completedSources'])>report['networkRequests'] or sum(i['networkBytesRead'] for i in report['completedSources'])>report['networkBytesRead']:raise ValueError('invalid-global-summary')
  return report
 if report.get('status')=='blocked':
  if report!=blocked_report(report.get('errorCode')) or report['errorCode'] not in ERRORS:raise ValueError('invalid-global-summary')
  return report
 keys={'schemaVersion','status','errorCode','manifestSHA256','selectionSHA256','assetCount','countryCount','typeCount','networkRequests','networkBytesRead','preparedBytes','assetOutcomeGroups','cellStageCounts','changes','statPathCount','statOutcomeGroups','checkpointCount','checkpointIndexSHA256','detailSHA256','detailPersisted','runtimeCapabilities','globalErrors','maximumParallelTransfers','maximumPerHostTransfers','wholeOperationSeconds'}|set(a.SAFETY)
 if set(report)!=keys:raise ValueError('invalid-global-summary')
 manifest=manifest_config();selected=selection_config();outcomes=expand_outcomes(report['assetOutcomeGroups'],len(manifest['assets']))
 if report['schemaVersion']!=SCHEMA or report['status'] not in {'complete','complete-with-errors'} or report['errorCode'] is not None or report['manifestSHA256']!=a.sha(a.canonical(manifest)) or report['selectionSHA256']!=a.sha(a.canonical(selected)) or report['assetCount']!=len(outcomes) or report['countryCount']!=249 or report['typeCount']!=13:raise ValueError('invalid-global-summary')
 if report['cellStageCounts']!=country_cells(manifest,outcomes) or any(report[k] is not v for k,v in a.SAFETY.items()):raise ValueError('invalid-global-summary')
 if report['statPathCount']!=len(manifest.get('statTargets',[])):raise ValueError('invalid-global-summary')
 observed_paths=set()
 for group in report['statOutcomeGroups']:
  if set(group)!={'state','pathRanges'} or group['state'] not in CUSTODY:raise ValueError('invalid-global-summary')
  for low,high in group['pathRanges']:
   if type(low) is not int or type(high) is not int or not 0<=low<=high<report['statPathCount']:raise ValueError('invalid-global-summary')
   for i in range(low,high+1):
    if i in observed_paths:raise ValueError('invalid-global-summary')
    observed_paths.add(i)
 if len(observed_paths)!=report['statPathCount']:raise ValueError('invalid-global-summary')
 source_map={s['sourceKey']:s for s in selected['sources']};seen=set();acquired=set();requests=body=prepared=0
 if not isinstance(report['changes'],list) or len(report['changes'])>MAX_ASSETS:raise ValueError('invalid-global-summary')
 for change in report['changes']:
  if set(change)!={'assetIndex','acquisition','preparation'} or type(change['assetIndex']) is not int or not 0<=change['assetIndex']<len(outcomes) or change['assetIndex'] in seen:raise ValueError('invalid-global-summary')
  seen.add(change['assetIndex']);asset=manifest['assets'][change['assetIndex']];item=change['acquisition']
  if item is not None:
   key=asset.get('sourceKey')
   if key not in source_map or key in acquired:raise ValueError('invalid-global-summary')
   acquired.add(key);validate_acquisition(item,source_map[key]);requests+=item['networkRequests'];body+=item['networkBytesRead']
  if change['preparation'] is not None:validate_preparation(change['preparation']);prepared+=change['preparation']['preparedBytes']
 if acquired!=set(source_map) or report['networkRequests']!=requests or report['networkBytesRead']!=body or type(requests) is not int or requests>selected['maximumRequests'] or body>selected['maximumTransferBytes']:raise ValueError('invalid-global-summary')
 if type(report['preparedBytes']) is not int or report['preparedBytes']!=prepared or not 0<=prepared<=MAX_OUTPUT_BYTES:raise ValueError('invalid-global-summary')
 for key in ('manifestSHA256','selectionSHA256','checkpointIndexSHA256','detailSHA256'):
  if key=='detailSHA256' and report[key] is None and report['detailPersisted'] is False:continue
  if not isinstance(report[key],str) or not re.fullmatch('[a-f0-9]{64}',report[key]):raise ValueError('invalid-global-summary')
 if type(report['checkpointCount']) is not int or not 0<=report['checkpointCount']<=len(outcomes) or type(report['detailPersisted']) is not bool or report['maximumParallelTransfers']!=1 or report['maximumPerHostTransfers']!=1 or report['wholeOperationSeconds']!=MAX_SECONDS:raise ValueError('invalid-global-summary')
 if not isinstance(report['globalErrors'],list) or any(c not in GLOBAL_ERRORS for c in report['globalErrors']):raise ValueError('invalid-global-summary')
 caps=report['runtimeCapabilities'];expected={'stdlibFormats':['csv','tsv','json','xml','html','zip','xlsx','docx'],'optionalParsers':{'pypdf':None,'xlrd':None,'poppler':None},'handlerVersion':None,'pythonVersion':None,'isolatedWorker':None}
 if not isinstance(caps,dict) or set(caps)!=set(expected) or caps['handlerVersion']!=media.VERSION or type(caps['isolatedWorker']) is not bool or caps['stdlibFormats']!=expected['stdlibFormats'] or not isinstance(caps['pythonVersion'],str) or not re.fullmatch('[0-9.]{1,32}',caps['pythonVersion']):raise ValueError('invalid-global-summary')
 if not isinstance(caps['optionalParsers'],dict) or set(caps['optionalParsers'])!=set(expected['optionalParsers']):raise ValueError('invalid-global-summary')
 for parser in caps['optionalParsers'].values():
  if set(parser)!={'available','version'} or type(parser['available']) is not bool or (parser['version'] is not None and (not isinstance(parser['version'],str) or not re.fullmatch('[a-zA-Z0-9.+_() -]{1,128}',parser['version']))):raise ValueError('invalid-global-summary')
 if report['status']=='complete' and (report['globalErrors'] or any(r['stage']=='error' for r in outcomes)):raise ValueError('invalid-global-summary')
 if len(a.canonical(report))>MAX_SUMMARY:raise ValueError('invalid-global-summary')
 return report


def main(argv=None):
 report=blocked_report('global-config-invalid');selected=None;progress={}
 try:
  if sys.argv[1:] if argv is None else argv:raise a.RefreshError('unexpected-arguments')
  selected=selection_config();manifest=manifest_config();prep=a.preparation_module();snapshot=prep.imported_snapshot(ROOT);adopted=a.strict_json(prep.pinned_bytes(ROOT,prep.SUMMARY_PIN))
  report=run_global(manifest,selected,adverse_evidence=b.source_conflicts(selected,snapshot,adopted),progress=progress);report=sanitize_report(report)
 except Exception:
  if selected is not None and 'meter' in progress:report=projection_failure(selected,progress)
 print(a.canonical(report).decode(),end='');return 0 if report['status']=='complete' else 2
if __name__=='__main__':raise SystemExit(main())
