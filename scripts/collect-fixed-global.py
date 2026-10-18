#!/usr/bin/env python3
"""One fixed, deterministic inventory/acquisition/preparation pass. No discovery or AI."""
from __future__ import annotations
from collections import Counter,defaultdict
from copy import deepcopy
import importlib.util,json,os,pwd,re,stat,sys,time,threading,math,multiprocessing
from contextlib import contextmanager,nullcontext
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('global_fixed_batch',ROOT/'scripts/acquire-fixed-batch.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
a=b.a;save=b.save
spec=importlib.util.spec_from_file_location('global_retained_taiwan',ROOT/'scripts/diagnose-retained-taiwan.py');taiwan=importlib.util.module_from_spec(spec);spec.loader.exec_module(taiwan)
spec=importlib.util.spec_from_file_location('global_retained_preparation',ROOT/'scripts/diagnose-retained-preparation.py');prepdiag=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepdiag)
from offmenu.refresh import media_preparation as media
from offmenu.refresh import known_asset_intake as intake
from offmenu.refresh import retained_contract_extension as retained_extension
from offmenu.refresh import retained_collection
from offmenu.refresh import retained_integrity_verification as retained_verification
spec=importlib.util.spec_from_file_location('global_taiwan_recovery',ROOT/'scripts/validate-retained-taiwan.py');twrecovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(twrecovery)
spec=importlib.util.spec_from_file_location('global_private_media_save',ROOT/'scripts/save-private-media-original.py');media_save=importlib.util.module_from_spec(spec);spec.loader.exec_module(media_save)
from offmenu.refresh.collection_progress import ProgressReporter,SharedActivity,initialize_preparation_worker,prepare_asset_observed,prepare_function_observed
SCHEMA='offmenu-global-collection-result/1'
SELECTION_PIN=('docs/collection-selections/global-original-selection.json','12bb04632ea6bbe078b68d28efab566f38c942e39a4339e91f02a738d7fe1008')
MANIFEST_PIN=('docs/collection-selections/global-known-assets-runtime.json','d846a735762e627fbf69475da958f39fa68418bea19c6b186e516f9e7feef270')
OWNER_PIN=('docs/collection-selections/owner-local-runtime.json','8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b')
LEGACY_OWNER_PIN=OWNER_PIN
OWNER_SUCCESSOR_PROFILE_PIN=None # Parent adoption pins an additive user-mode profile; runner/default remains unchanged.
MAX_ASSETS=10000;MAX_SECONDS=1200;MAX_OUTPUT_BYTES=1024**3;MAX_SUMMARY=96*1024
STATES=('ready-nextstage','held','unsupported','error','unverified','missing-contract','retained','eligible')
CUSTODY=('unverified','held','no-path','inaccessible','path-absent','unsafe-path','not-regular','extent-mismatch','stat-observed','verified-original')
GLOBAL_ERRORS={'global-worker-cancelled','global-preparation-state-uncertain','global-resource-capacity-unavailable','global-outer-failure','global-config-invalid','global-deadline-exhausted','global-output-budget','global-checkpoint-failed','global-preparation-unavailable','global-original-unavailable','global-source-conflict','global-local-read-budget'}
ERRORS=b.ERRORS|GLOBAL_ERRORS|media.ERROR_CODES|intake.ERROR_CODES|{retained_extension.ERROR}|retained_verification.ERROR_CODES

class SharedBudget:
 def __init__(self,requests,maximum):
  self.lock=threading.RLock();self.requests=0;self.bodyBytesRead=0;self.maximumRequests=requests;self.maximumBytes=maximum
 def child(self,key,maximum,maximum_requests=1):return SourceBudget(self,key,maximum,maximum_requests)
 def snapshot(self):
  with self.lock:return {'requests':self.requests,'bodyBytesRead':self.bodyBytesRead,'maximumRequests':self.maximumRequests,'maximumBytes':self.maximumBytes}
class SourceBudget:
 def __init__(self,parent,key,maximum,maximum_requests=1):self.parent=parent;self.key=key;self.requests=0;self.bodyBytesRead=0;self.maximumBytes=maximum;self.maximumRequests=maximum_requests
 def __getitem__(self,key):
  with self.parent.lock:return {'requests':self.requests,'bodyBytesRead':self.bodyBytesRead,'maximumRequests':self.maximumRequests,'maximumBytes':self.maximumBytes}[key]
 def start_request(self):
  with self.parent.lock:
   if self.requests>=self.maximumRequests or self.parent.requests>=self.parent.maximumRequests:raise a.RefreshError('network-request-limit')
   self.requests+=1;self.parent.requests+=1
 def remaining_bytes(self):
  with self.parent.lock:return min(self.maximumBytes-self.bodyBytesRead,self.parent.maximumBytes-self.parent.bodyBytesRead)
 def record_bytes(self,count):
  with self.parent.lock:
   self.bodyBytesRead+=count;self.parent.bodyBytesRead+=count
   if self.bodyBytesRead>self.maximumBytes or self.parent.bodyBytesRead>self.parent.maximumBytes:raise a.RefreshError('network-byte-limit')
 def snapshot(self):
  with self.parent.lock:return {'requests':self.requests,'bodyBytesRead':self.bodyBytesRead}
class ParallelCoordinator:
 """In-process workers share the existing exclusive kernel writer lease."""
 def __init__(self,work,fd):
  self.work=work;self.fd=fd;self.metadata=threading.RLock();self.storage=threading.RLock();self.active={};self.local=threading.local()
 @contextmanager
 def source_session(self,work):
  opened=os.fstat(self.fd);named=a.safe_path(work/'fixed-selection.lock').stat()
  if work!=self.work or (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino):raise a.RefreshError('unsafe-writer-lock')
  self.metadata.acquire();self.local.held=True
  try:yield
  finally:
   if getattr(self.local,'held',False):self.local.held=False;self.metadata.release()
 def transfer_start(self):
  if getattr(self.local,'held',False):self.local.held=False;self.metadata.release()
 @contextmanager
 def intent_write(self):
  with self.metadata:yield
 def reserve(self,key,path,folder,deadline,expected,maximum):
  with self.storage:
   if key in self.active:raise a.RefreshError('source-claim-uncertain')
   if a.capacity(folder)<a.GUARD+expected+maximum+sum(self.active.values()):raise a.RefreshError('capacity-planning-bound-not-protected')
   result=a.reserve(path,folder,deadline,expected_bytes=expected,max_bytes=maximum);self.active[key]=maximum;return result
 def write(self,key,stream,block,folder):
  with self.storage:
   if key not in self.active or len(block)>self.active[key] or a.capacity(folder)<a.GUARD+sum(self.active.values()):raise a.RefreshError('capacity-planning-bound-not-protected')
   written=stream.write(block)
   if written!=len(block):raise OSError('short-write')
   stream.flush();self.active[key]-=len(block)
 def release(self,key,path,fd,identity):
  with self.storage:
   try:a.release_own_reservation(path,fd,identity)
   finally:self.active.pop(key,None)

RESOURCE_PROBLEMS={'membership-unavailable','membership-invalid','mountinfo-unavailable','mount-invalid','controller-mount-unresolved','cpu-limit-unresolved','memory-limit-unresolved','ancestor-depth-limit'}
RESOURCE_READ_LABELS={'cgroup':'membership','mountinfo':'mountinfo','meminfo':'host-memory','cpu.max':'cpu-limit','cpu.cfs_quota_us':'cpu-limit','cpu.cfs_period_us':'cpu-period','memory.max':'memory-limit','memory.limit_in_bytes':'memory-limit','memory.current':'memory-current','memory.usage_in_bytes':'memory-current','cgroup.subtree_control':'parent-subtree-control'}
def validate_resource_diagnostics(value):
 keys={'schemaVersion','cgroupKinds','matchedMounts','levelsChecked','disabledCPUInterfaces','disabledMemoryInterfaces','rootExemptInterfaces','readFailures','problemCodes'}
 if not isinstance(value,dict) or set(value)!=keys or value['schemaVersion']!='offmenu-resource-observation/1':raise ValueError('invalid-global-summary')
 if value['cgroupKinds']!=sorted(set(value['cgroupKinds'])) or any(x not in {'cgroup','cgroup2'} for x in value['cgroupKinds']):raise ValueError('invalid-global-summary')
 for key in keys-{'schemaVersion','cgroupKinds','readFailures','problemCodes'}:
  if type(value[key]) is not int or not 0<=value[key]<=65536:raise ValueError('invalid-global-summary')
 if not isinstance(value['problemCodes'],list) or value['problemCodes']!=sorted(set(value['problemCodes'])) or any(x not in RESOURCE_PROBLEMS for x in value['problemCodes']):raise ValueError('invalid-global-summary')
 if not isinstance(value['readFailures'],list) or len(value['readFailures'])>32:raise ValueError('invalid-global-summary')
 seen=set()
 for row in value['readFailures']:
  if not isinstance(row,dict) or set(row)!={'interface','state','count'} or row['interface'] not in set(RESOURCE_READ_LABELS.values()) or row['state'] not in {'absent','permission-denied','io-error','invalid'} or type(row['count']) is not int or not 1<=row['count']<=65536:raise ValueError('invalid-global-summary')
  pair=(row['interface'],row['state'])
  if pair in seen:raise ValueError('invalid-global-summary')
  seen.add(pair)
 return value

def effective_resources(config,read_text=None):
 def bounded_read(path):
  with open(path,encoding='utf-8') as stream:return stream.read(65537)
 read_text=read_text or bounded_read;missing=set();failures=Counter();problems=set();kinds=set()
 diagnostics={'schemaVersion':'offmenu-resource-observation/1','cgroupKinds':[],'matchedMounts':0,'levelsChecked':0,'disabledCPUInterfaces':0,'disabledMemoryInterfaces':0,'rootExemptInterfaces':0,'readFailures':[],'problemCodes':[]}
 def read(path):
  try:
   value=read_text(path)
   if not isinstance(value,str) or len(value)>65536:raise ValueError('bounded-resource-read')
   return value.strip()
  except FileNotFoundError:missing.add(path);state='absent'
  except PermissionError:state='permission-denied'
  except (OSError,KeyError):state='io-error'
  except ValueError:state='invalid'
  failures[(RESOURCE_READ_LABELS[Path(path).name],state)]+=1;return None
 def absent_uncontrolled(controller,path,location,ceiling,root):
  # Missing is accepted only with positive evidence of absent local control.
  if str(path) not in missing:return False
  if location==ceiling:
   if root=='/':diagnostics['rootExemptInterfaces']+=1;return True
   return False # A hidden parent cannot prove a delegated root unconstrained.
  enabled=read(str(location.parent/'cgroup.subtree_control'))
  if enabled is None or any(not re.fullmatch('[a-z][a-z0-9_]*',word) for word in enabled.split()):return False
  if controller in enabled.split():return False
  diagnostics['disabledCPUInterfaces' if controller=='cpu' else 'disabledMemoryInterfaces']+=1;return True
 try:affinity=len(os.sched_getaffinity(0))
 except (AttributeError,OSError):affinity=os.cpu_count() or 1
 observed=os.cpu_count() or 1;quotas=[];headrooms=[]
 membership=read('/proc/self/cgroup');mounts=read('/proc/self/mountinfo');controllers={}
 if membership and mounts:
  for row in membership.splitlines():
   fields=row.split(':',2)
   if len(fields)==3 and fields[2].startswith('/') and '..' not in Path(fields[2]).parts:
    for c in fields[1].split(','):controllers[c]=fields[2]
   else:problems.add('membership-invalid')
  found=set()
  for row in mounts.splitlines():
   fields=row.split()
   try:
    sep=fields.index('-');kind=fields[sep+1]
    if kind not in {'cgroup','cgroup2'}:continue
    kinds.add(kind);root,mount=fields[3:5]
    if '\\' in root+mount or not mount.startswith('/') or not root.startswith('/') or '..' in Path(root).parts+Path(mount).parts:problems.add('mount-invalid');continue
    names=[''] if kind=='cgroup2' else fields[sep+3].split(',')
    for name in names:
     if name not in controllers or (kind=='cgroup' and name not in {'cpu','memory'}):continue
     current=controllers[name]
     if root!='/' and current!=root and not current.startswith(root.rstrip('/')+'/'):continue
     relative=current[len(root):].lstrip('/') if root!='/' else current.lstrip('/')
     location=Path(mount)/relative;ceiling=Path(mount);found.add(name);diagnostics['matchedMounts']+=1;depth=0
     while True:
      depth+=1;diagnostics['levelsChecked']+=1
      if depth>64:problems.add('ancestor-depth-limit');break
      if kind=='cgroup2' or name=='cpu':
       path=location/('cpu.max' if kind=='cgroup2' else 'cpu.cfs_quota_us');q=read(str(path))
       if kind=='cgroup2':
        parts=(q or '').split();period=parts[1] if len(parts)==2 else None;quota=parts[0] if len(parts)==2 else None
       else:quota=q;period=read(str(location/'cpu.cfs_period_us'))
       if quota=='-1' and kind=='cgroup':pass
       elif quota=='max' and period and period.isdigit() and int(period)>0:pass
       elif kind=='cgroup2' and absent_uncontrolled('cpu',path,location,ceiling,root):pass
       elif quota and quota.isdigit() and period and period.isdigit() and int(period)>0 and int(quota)>0:quotas.append(max(1,int(quota)//int(period)))
       else:problems.add('cpu-limit-unresolved')
      if kind=='cgroup2' or name=='memory':
       path=location/('memory.max' if kind=='cgroup2' else 'memory.limit_in_bytes');cap=read(str(path));used=read(str(location/('memory.current' if kind=='cgroup2' else 'memory.usage_in_bytes')))
       if cap=='max':pass
       elif kind=='cgroup2' and absent_uncontrolled('memory',path,location,ceiling,root):pass
       elif cap and cap.isdigit() and used and used.isdigit():
        if int(cap)<1024**6:headrooms.append(max(0,int(cap)-int(used)))
       else:problems.add('memory-limit-unresolved')
      if location==ceiling:break
      if ceiling not in location.parents:problems.add('mount-invalid');break
      location=location.parent
   except (ValueError,IndexError):problems.add('mount-invalid')
  if ('' not in found and not {'cpu','memory'}<=found) or not (set(controllers)&{'cpu','memory'})<=found:problems.add('controller-mount-unresolved')
 else:
  if not membership:problems.add('membership-unavailable')
  if not mounts:problems.add('mountinfo-unavailable')
 quota=min(quotas) if quotas else None;cgroup=min(headrooms) if headrooms else None
 cpus=max(1,min(affinity,observed,quota if quota is not None else observed));mem=None;info=read('/proc/meminfo')
 if info:
  match=re.search(r'^MemAvailable:\s+(\d+)\s+kB$',info,re.M)
  if match:mem=int(match.group(1))*1024
 available=min(x for x in (mem,cgroup) if x is not None) if mem is not None or cgroup is not None else 0
 usable=max(0,available-config['memoryReserveBytes']);prep=min(config['preparationWorkers'],cpus,usable//config['memoryPerPreparationBytes'],MAX_OUTPUT_BYTES//config['maximumOutputPerPreparationBytes'])
 unknown=bool(problems)
 if unknown:cpus=1;prep=0
 diagnostics.update(cgroupKinds=sorted(kinds),readFailures=[{'interface':k[0],'state':k[1],'count':v} for k,v in sorted(failures.items())],problemCodes=sorted(problems));validate_resource_diagnostics(diagnostics)
 io=min(config['ioWorkers'],max(1,cpus*2));return {'logicalCPUs':observed,'affinityCPUs':affinity,'cgroupCPUCap':quota,'effectiveCPUs':cpus,'memoryAvailableBytes':mem,'cgroupMemoryHeadroomBytes':cgroup,'effectiveMemoryBytes':available,'resourceLimitsIncomplete':unknown,'ioWorkers':io,'preparationWorkers':prep,'perHostWorkers':config['perHostWorkers'],'memoryPerPreparationBytes':config['memoryPerPreparationBytes'],'memoryReserveBytes':config['memoryReserveBytes'],'diagnostics':diagnostics}

DEFAULT_PARALLELISM={'ioWorkers':8,'preparationWorkers':8,'perHostWorkers':1,'minimumHostStartSpacingSeconds':2,'memoryReserveBytes':2*1024**3,'memoryPerPreparationBytes':2560*1024**2,'maximumOutputPerPreparationBytes':128*1024**2}

def pinned(pin):return a.strict_json(a.preparation_module().pinned_bytes(ROOT,pin))

def selection_config():
 value=pinned(SELECTION_PIN)
 if 'retainedVerification' in value:
  retained_collection.validate_combined(value,manifest_config(),ROOT);return value
 if 'knownIntakeSuccessor' in value:
  intake.validate_successor_selection(value,manifest_config(),ROOT);return value
 if not isinstance(value,dict) or value.get('schemaVersion')!='offmenu-global-source-selection/1' or set(value)!={'schemaVersion','batchId','sources','maximumRequests','maximumTransferBytes','wholeOperationSeconds','minimumCacheSeconds','planningGuardBytes','floorAlreadyIncluded','evidence','coordinatorIntent','privateOriginalDownload','preparation','parallelism'}:raise a.RefreshError('global-config-invalid')
 if (not 1<=len(value['sources'])<=32 or value['maximumRequests']!=len(value['sources']) or value['wholeOperationSeconds']!=MAX_SECONDS
     or value['maximumTransferBytes']!=sum(s['hardTransferBytes'] for s in value['sources']) or value['maximumTransferBytes']>256*1024**2):raise a.RefreshError('global-config-invalid')
 if value['parallelism']!=DEFAULT_PARALLELISM:raise a.RefreshError('global-config-invalid')
 # Reuse the reviewed closed source-contract validator in fixed bounded slices.
 for offset in range(0,len(value['sources']),b.MAX_SOURCES):
  chunk=deepcopy(value);chunk.pop('preparation');chunk.pop('parallelism');chunk['schemaVersion']='offmenu-fixed-source-batch-selection/1';chunk['sources']=value['sources'][offset:offset+b.MAX_SOURCES];chunk['maximumRequests']=len(chunk['sources']);keys={s['sourceKey'] for s in chunk['sources']}
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

@contextmanager
def owner_successor_profile(args):
 global SELECTION_PIN,MANIFEST_PIN,OWNER_PIN
 if args not in (['--mode','user'],['--mode','user','--publish-only']) or OWNER_SUCCESSOR_PROFILE_PIN is None:
  yield;return
 profile=pinned(OWNER_SUCCESSOR_PROFILE_PIN)
 if set(profile)!={'schemaVersion','status','selectionPin','manifestPin','ownerRuntimePin'} or profile['schemaVersion']!='offmenu-owner-successor-profile/1' or profile['status']!='parent-reviewed-owner-manual':raise a.RefreshError('owner-handover-invalid')
 pins=[]
 for field in ('selectionPin','manifestPin','ownerRuntimePin'):
  pin=profile[field]
  if not isinstance(pin,dict) or not {'path','sha256'}<=set(pin) or not set(pin)<={'path','sha256','bytes'} or not isinstance(pin['path'],str) or not pin['path'].startswith('docs/') or '..' in Path(pin['path']).parts or not re.fullmatch('[a-f0-9]{64}',pin['sha256']):raise a.RefreshError('owner-handover-invalid')
  pins.append((pin['path'],pin['sha256']))
 prior=SELECTION_PIN,MANIFEST_PIN,OWNER_PIN
 if any(new[0]==old[0] for new,old in zip(pins,prior)):raise a.RefreshError('owner-handover-invalid')
 SELECTION_PIN,MANIFEST_PIN,OWNER_PIN=pins
 try:yield
 finally:SELECTION_PIN,MANIFEST_PIN,OWNER_PIN=prior

def prepared_successor_configs():
 """Offline review only. Active owner handoff and default pins remain unchanged."""
 return intake.compose_for_review(selection_config(),manifest_config(),intake.successor_config(ROOT))

def prepared_comprehensive_configs():
 selected,manifest=prepared_successor_configs();ext,plan=retained_collection.config(ROOT)
 return retained_collection.compose_for_review(manifest_config(),manifest,selected,ext,plan)

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
  'preparedBytes':0 if detail.get('reusedFromAssetIndex') is not None or detail.get('preparationReused',False) else sum(row['bytes'] for row in detail['outputs'])+detail.get('receiptBytes',0),'preparedFiles':len(detail['outputs']),
  'nextStageReady':detail['nextStageReady'],'detailSHA256':a.sha(a.canonical(detail)),
  'metrics':{k:metrics[k] for k in allowed if k in metrics and metrics[k] is not None},'reusedFromAssetIndex':detail.get('reusedFromAssetIndex'),'preparationReused':detail.get('preparationReused',False),'receiptSHA256':detail.get('receiptSHA256'),'receiptBytes':detail.get('receiptBytes',0),'storageAccountingComplete':detail.get('storageAccountingComplete',True)}


def runtime_capabilities():
 try:return media.capabilities()
 except Exception:
  return {'handlerVersion':media.VERSION,'pythonVersion':sys.version.split()[0],'isolatedWorker':False,
   'stdlibFormats':['csv','tsv','json','xml','html','zip','xlsx','docx'],
   'optionalParsers':{key:{'available':False,'version':None} for key in ('pypdf','xlrd','poppler')}}

def run_global(manifest,selected,*,transport=None,adverse_evidence=(),prepare=run_preparation,progress=None,owner_runtime=None,terminal=None):
 if selected.get('retainedVerification',{}).get('status')=='prepared-for-review-not-active':raise a.RefreshError('media-intake-successor-inactive')
 if manifest.get('retainedContractExtension',{}).get('status')=='prepared-for-review-not-active':raise a.RefreshError('media-intake-successor-inactive')
 if selected.get('knownIntakeSuccessor',{}).get('status')=='prepared-for-review-not-active':raise a.RefreshError('media-intake-successor-inactive')
 work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection')
 with a.writer_lock(work/'fixed-selection.lock') as lease:
  return _run_global_locked(manifest,selected,transport=transport,adverse_evidence=adverse_evidence,prepare=prepare,progress=progress,lease=lease,owner_runtime=owner_runtime,terminal=terminal)

def _run_global_locked(manifest,selected,*,transport=None,adverse_evidence=(),prepare=run_preparation,progress=None,lease=None,owner_runtime=None,terminal=None):
 retained_rows=retained_plan=binding_manifest=None;read_accounting=None
 if 'retainedVerification' in selected:
  if selected['retainedVerification']['status']!='parent-reviewed-owner-manual' or owner_runtime is None:raise a.RefreshError('media-intake-successor-inactive')
  retained_rows,retained_plan,binding_manifest=retained_collection.validate_combined(selected,manifest,ROOT)
  read_accounting=retained_collection.ReadAccounting(manifest,retained_rows,retained_plan)
 if 'knownIntakeSuccessor' in selected:
  if selected['knownIntakeSuccessor']['status']!='parent-reviewed-owner-manual' or owner_runtime is None:raise a.RefreshError('media-intake-successor-inactive')
  if read_accounting is None:intake.validate_successor_selection(selected,manifest,ROOT)
  intake.validate_joins(selected['knownIntakeSuccessor']['reuseJoins'],manifest,binding_manifest=binding_manifest)
 for source in selected['sources']:
  if intake.is_media_source(source):intake.validate_source(source)
 source_assets={}
 for i,asset in enumerate(manifest['assets']):
  if asset.get('sourceKey'):source_assets.setdefault(asset['sourceKey'],[]).append(i)
 needed={s['sourceKey'] for s in selected['sources']}|{p['sourceKey'] for p in selected['preparation']}
 if not needed<=set(source_assets):raise a.RefreshError('global-config-invalid')
 config=selected.get('parallelism',DEFAULT_PARALLELISM);resources=effective_resources(config);capabilities=runtime_capabilities()
 deadline=time.monotonic()+MAX_SECONDS-20;meter=SharedBudget(selected['maximumRequests'],selected['maximumTransferBytes'])
 if terminal is not None:
  terminal.update(download_configured=config['ioWorkers'],download_effective=resources['ioWorkers'],preparation_configured=config['preparationWorkers'],preparation_effective=resources['preparationWorkers'],download_total=len(selected['sources']),download_queued=len(selected['sources']),inventory_total=len(manifest['assets']),coverage_total=len(manifest['countries'])*len(manifest['types']),coverage_verified=None,network_bytes=0,prepared_bytes=0)
  terminal.observe(network_meter=meter);terminal.stage('inventory')
 outcomes=[];changes=[]
 if progress is not None:progress.update(meter=meter,changes=changes)
 persisted=0;output_bytes=0;checkpoints={};errors=[];manifest_sha=a.sha(a.canonical(manifest))
 work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection');root=save.private_directory(work/'global-collection',a);run_dir=save.private_directory(root/manifest_sha,a)
 taiwan_diagnostics=taiwan.run_diagnostics(a.OUTPUT,min(deadline,time.monotonic()+30)) if owner_runtime is not None else None
 recovery_proposals=None
 if owner_runtime is not None and 'knownIntakeSuccessor' in selected:
  recovery_deadline=min(deadline,time.monotonic()+90)
  recovery_proposals=[twrecovery.validate_selected(source,a.OUTPUT,recovery_deadline) for source in selected['sources'] if source['sourceKey'] in twrecovery.PINS]
 preparation_diagnostics=prepdiag.run_diagnostics(a.OUTPUT,min(deadline,time.monotonic()+60),assets=manifest['assets']) if owner_runtime is not None else None
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
 terminal_assets={'failed':sum(row['stage']=='error' for row in outcomes),'held':sum(row['stage']=='held' for row in outcomes)}
 if terminal is not None:terminal.update(inventory_classified=len(outcomes),**terminal_assets)
 def terminal_asset_change(indices,before):
  if terminal is not None:
   after=Counter(outcomes[i]['stage'] for i in indices)
   for key,state in (('failed','error'),('held','held')):terminal_assets[key]+=after[state]-before[state]
   terminal.update(**terminal_assets)
 preparation={row['sourceKey']:row for row in selected['preparation']};completed=set();pending_preparation=[];host_started={};active_hosts=Counter();peak_io=0;peak_prep=0
 def checkpoint(index,detail):
  nonlocal persisted
  if time.monotonic()>=deadline+10:errors.append('global-deadline-exhausted');return
  payload={'schemaVersion':'offmenu-global-asset-checkpoint/1','manifestSHA256':manifest_sha,'assetIndex':index,'assetId':manifest['assets'][index]['assetId'],'outcome':outcomes[index],'detail':detail}
  digest=a.sha(a.canonical(payload));path=run_dir/('asset-'+str(index)+'-'+digest+'.json')
  try:a.write_immutable(path,payload);checkpoints[index]=digest;persisted=len(checkpoints)
  except (a.RefreshError,OSError,ValueError,TypeError,KeyError):errors.append('global-checkpoint-failed')
 def acquire(source,child,coordinator):
  detail=None;error=None
  try:
   if time.monotonic()>=deadline:raise a.RefreshError('global-deadline-exhausted')
   indices=source_assets[source['sourceKey']]
   if any(a.exact_source_match(e,source) for e in adverse_evidence) or any(manifest['assets'][i]['disposition']!='eligible' for i in indices):raise a.RefreshError('global-source-conflict')
   handler=media_save if intake.is_media_source(source) else save
   chosen_transport=transport
   if terminal is not None:
    if chosen_transport is None:chosen_transport=(intake.BoundedHTTPSFileTransport(source['mediaIntake']['maximumHeaderBytes']) if intake.is_media_source(source) else a.HTTPSFileTransport())
    chosen_transport=terminal.wrap_transport(chosen_transport)
   detail=handler.run_selected(source,adapter=a,mode=selected['privateOriginalDownload'],transport=chosen_transport,deadline=deadline,batch_meter=child,coordinator=coordinator,owner_runtime=owner_runtime)
  except Exception as failure:error=str(failure) if isinstance(failure,a.RefreshError) and str(failure) in ERRORS else 'collector-rejected'
  return b.item_report(source,detail,error,child.snapshot())
 def acquired(source,item):
  indices=source_assets[source['sourceKey']];index=indices[0];before=Counter(outcomes[i]['stage'] for i in indices)
  for i in indices:
   outcomes[i]={'custody':'verified-original' if item['status']=='verified-private-original' else outcomes[i]['custody'],'stage':'retained' if item['status']=='verified-private-original' else 'error','code':item['errorCode']}
  if item['status']=='verified-private-original' and source['sourceKey'] in preparation:
   identity={'sha256':item['originalSHA256'],'bytes':item['verifiedBytes']};original=work/'private-originals'/a.sha(a.canonical(source))/intake.original_filename(source);pending_preparation.append((index,indices,preparation[source['sourceKey']],identity,original,item))
  for i in indices:checkpoint(i,{'acquisition':item,'preparation':None});completed.add(i)
  changes.append({'assetIndex':index,'acquisition':item,'preparation':None})
  if terminal is not None:
   terminal.increment(download_completed=1,download_reused=int(item.get('originalDisposition')=='retained-original-no-network'),downloaded=int(item['status']=='verified-private-original' and item['networkRequests']>0))
   terminal_asset_change(indices,before)
 # A single existing kernel lease covers all worker claim scans and transfers.
 # Only runnable hosts are submitted; same-host waits never occupy I/O slots.
 pending=list(selected['sources']);active={};pool=ThreadPoolExecutor(max_workers=resources['ioWorkers'],thread_name_prefix='fixed-original')
 if terminal is not None:terminal.stage('downloads')
 try:
  with nullcontext():
   coordinator=ParallelCoordinator(work,lease)
   while pending or active:
    now=time.monotonic()
    for source in list(pending):
     if len(active)>=resources['ioWorkers']:break
     hosts=intake.source_hosts(source)
     if now>=deadline:
      pending.remove(source);acquired(source,b.item_report(source,error='global-deadline-exhausted'));continue
     if any(active_hosts[host]>=config['perHostWorkers'] or now<host_started.get(host,0)+config['minimumHostStartSpacingSeconds'] for host in hosts):continue
     pending.remove(source)
     for host in hosts:host_started[host]=now;active_hosts[host]+=1
     child=meter.child(source['sourceKey'],source['hardTransferBytes'],intake.maximum_requests(source))
     future=pool.submit(acquire,source,child,coordinator);active[future]=(source,hosts,child);peak_io=max(peak_io,len(active))
    if terminal is not None:terminal.update(download_queued=len(pending))
    if active:
     done,_=wait(active,timeout=min(.1,max(0,deadline-time.monotonic())),return_when=FIRST_COMPLETED)
     for future in done:
      source,hosts,child=active.pop(future)
      for host in hosts:active_hosts[host]-=1;host_started[host]=time.monotonic()
      try:item=future.result()
      except Exception:item=b.item_report(source,error='collector-rejected',network=child.snapshot())
      acquired(source,item)
    elif pending:time.sleep(min(.05,max(0,deadline-time.monotonic())))
 except (a.RefreshError,OSError) as failure:
  code=str(failure) if str(failure) in ERRORS else 'global-outer-failure'
  for source in pending:acquired(source,b.item_report(source,error=code))
  pending=[]
 finally:pool.shutdown(wait=True,cancel_futures=True)
 if terminal is not None:terminal.update(download_queued=0)
 # Build the entire deterministic preparation queue only after acquisition finishes.
 for key,p in preparation.items():
  if p['retainedOriginal'] is None:continue
  indices=source_assets[key];identity=p['retainedOriginal'];pending_preparation.append((indices[0],indices,p,identity,identity['path'],None));completed.update(indices)
 for i,asset in enumerate(manifest['assets']):
  if i in completed:continue
  contract=asset.get('preparationContract');original=asset.get('retainedOriginal')
  if contract is not None and original is not None and outcomes[i]['custody']=='stat-observed' and asset['disposition']!='held':
   p={key:contract[key] for key in ('permissions','holds','expectedMediaTypes','parameters')};pending_preparation.append((i,[i],p,original,original['path'],None))
 jobs=[];identities={}
 def prepared(job,detail,code,used):
  nonlocal output_bytes
  index,indices,contract,path,item,duplicates=job;output_bytes+=used
  streaming=contract['schemaVersion']==retained_verification.SCHEMA
  compact=read_accounting is not None and index in read_accounting.rows and index not in read_accounting.structural
  if read_accounting is not None:read_accounting.finish(index,detail if code is None else None,uncertain=code in {'global-deadline-exhausted','global-preparation-state-uncertain','global-preparation-unavailable'})
  affected=sorted({i for group in [indices]+[row[1] for row in duplicates] for i in group});before=Counter(outcomes[i]['stage'] for i in affected)
  if detail is None or code is not None:outcomes[index].update(stage='error',code=code or 'global-preparation-unavailable')
  elif streaming:
   retained_verification.sanitize_report(detail,contract)
   outcomes[index].update(stage='held' if detail['integrityVerified'] else 'error',code='extract-permission-held' if detail['integrityVerified'] else detail['errorCode'])
   if detail['integrityVerified']:outcomes[index]['custody']='verified-original'
  else:
   outcomes[index].update(stage={'ready':'ready-nextstage','held':'held','unsupported':'unsupported','failed':'error'}[detail['status']],code=detail['errorCode'])
   if detail['stages']['integrity']=='passed':outcomes[index]['custody']='verified-original'
  for target,targets,original_item in [(index,indices,item)]+duplicates:
   current=detail if target==index or detail is None else {**detail,'reusedFromAssetIndex':index}
   for i in targets:outcomes[i]=dict(outcomes[index]);checkpoint(i,{'acquisition':original_item,'preparation':current})
   if compact:continue
   change=next((r for r in changes if r['assetIndex']==target),None)
   if change is None:changes.append({'assetIndex':target,'acquisition':original_item,'preparation':preparation_summary(current)})
   else:change['preparation']=preparation_summary(current)
  if terminal is not None:
   terminal.increment(preparation_completed=1,prepared=int(code is None and detail is not None and detail['status']=='ready'),preparation_reused=int(detail is not None and detail.get('preparationReused',False)))
   terminal.update(prepared_bytes=output_bytes);terminal_asset_change(affected,before)
 for index,indices,p,identity,path,item in sorted(pending_preparation,key=lambda x:x[0]):
  asset=manifest['assets'][index];template={key:deepcopy(p[key]) for key in ('permissions','holds','expectedMediaTypes','parameters')}
  template['holds']=sorted(set(template['holds'])|({h for h in asset.get('sourceStageHolds',[])+asset.get('holds',[]) if isinstance(h,str)}&{'read','extract','copy','all'}))
  if asset['disposition']=='held':
   for i in indices:outcomes[i]['stage']='held';checkpoint(i,{'acquisition':item,'preparation':None})
   if not any(c['assetIndex']==index for c in changes):changes.append({'assetIndex':index,'acquisition':item,'preparation':None})
   continue
  contract={'schemaVersion':media.SCHEMA,'assetId':asset['assetId'],'expectedSHA256':identity['sha256'],'expectedBytes':identity['bytes'],**template}
  identity_key=a.sha(a.canonical({'path':str(path),'sha256':identity['sha256'],'bytes':identity['bytes'],**template}))
  if identity_key in identities:identities[identity_key][5].append((index,indices,item));continue
  job=(index,indices,contract,Path(path),item,[]);identities[identity_key]=job;jobs.append(job)
 if read_accounting is not None:
  for index,row in read_accounting.rows.items():
   if row['preparationContract'] is None and outcomes[index]['custody']=='stat-observed':
    jobs.append((index,[index],deepcopy(row['verificationContract']),Path(row['retainedOriginal']['path']),None,[]))
  jobs.sort(key=lambda job:job[0])
 ctx=multiprocessing.get_context('spawn');storage=ctx.RLock();active={};pending=list(jobs);granted=0;pool=None;uncertain=[];uncertain_bytes=0;prep_root=None
 activity=SharedActivity(ctx,len(jobs)) if terminal is not None else None;activity_slots={job[0]:slot for slot,job in enumerate(jobs)}
 if terminal is not None:
  terminal.observe(preparation_activity=activity,network_meter=meter);terminal.update(preparation_total=len(jobs),preparation_queued=len(jobs));terminal.stage('preparing')
 try:prep_root=save.private_directory(work/'global-preparation',a)
 except (a.RefreshError,OSError):errors.append('global-preparation-unavailable')
 try:
  if jobs and prep_root is not None and resources['preparationWorkers']:
   try:pool=(ProcessPoolExecutor(max_workers=resources['preparationWorkers'],mp_context=ctx,initializer=initialize_preparation_worker if terminal is not None else media.configure_storage_lock,initargs=(storage,activity) if terminal is not None else (storage,)) if prepare is run_preparation else ThreadPoolExecutor(max_workers=resources['preparationWorkers']))
   except (OSError,RuntimeError):errors.append('global-preparation-unavailable')
  while pending or active:
   while pending and len(active)<max(1,resources['preparationWorkers']):
    job=pending[0];index,indices,contract,path,item,duplicates=job
    code='global-deadline-exhausted' if time.monotonic()>=deadline else 'global-resource-capacity-unavailable' if not pool else None
    streaming=contract['schemaVersion']==retained_verification.SCHEMA
    grant=0 if streaming else min(config['maximumOutputPerPreparationBytes'],MAX_OUTPUT_BYTES-output_bytes-granted-uncertain_bytes)
    if code is None and grant<=0 and not streaming:
     if active:break
     code='global-output-budget'
    pending.pop(0)
    if terminal is not None:terminal.update(preparation_queued=len(pending))
    if code:prepared(job,None,code,0);continue
    fd=identity=None
    try:
     if read_accounting is not None:read_accounting.reserve(index)
     if streaming:
      future=pool.submit(retained_collection.verify_worker,contract,path,deadline,activity_slots[index] if terminal is not None else None)
      active[future]=(job,None,None,None,0);peak_prep=max(peak_prep,len(active));continue
     folder=save.private_directory(prep_root/a.sha(a.canonical(contract)),a);reservation=folder/'reservation.bin'
     if not storage.acquire(timeout=min(1,max(0,deadline-time.monotonic()))):raise a.RefreshError('global-preparation-state-uncertain')
     try:
      if a.capacity(folder)<a.GUARD+2*grant+granted:raise a.RefreshError('capacity-planning-bound-not-protected')
      fd,identity=a.reserve(reservation,folder,deadline,expected_bytes=grant,max_bytes=grant)
     finally:storage.release()
     if prepare is run_preparation:
      if terminal is None:future=pool.submit(media.prepare_asset,contract,path,folder/'prepared',deadline,maximum_output_bytes=grant,minimum_free_bytes=a.GUARD)
      else:future=pool.submit(prepare_asset_observed,activity_slots[index],contract,path,folder/'prepared',deadline,maximum_output_bytes=grant,minimum_free_bytes=a.GUARD)
     elif terminal is None:future=pool.submit(prepare,contract['assetId'],contract,path,folder,deadline,grant)
     else:future=pool.submit(prepare_function_observed,activity,activity_slots[index],prepare,contract['assetId'],contract,path,folder,deadline,grant)
     active[future]=(job,reservation,fd,identity,grant);granted+=grant;peak_prep=max(peak_prep,len(active))
    except (a.RefreshError,OSError,ValueError,RuntimeError) as failure:
     if fd is not None:
      try:a.release_own_reservation(reservation,fd,identity)
      except Exception:pass
     prepared(job,None,str(failure) if str(failure) in ERRORS else 'global-preparation-unavailable',0)
   if active:
    done,_=wait(active,timeout=min(.1,max(0,deadline+2-time.monotonic())),return_when=FIRST_COMPLETED)
    if not done and time.monotonic()>=deadline+2:
     if activity is not None:activity.mark_uncertain()
     # Only our spawned processes are signalled. Their scoped handler cleans inner parser groups.
     if prepare is run_preparation:
      processes=list((getattr(pool,'_processes',None) or {}).values())
      for process in processes:process.terminate()
      for process in processes:
       process.join(max(0,min(1,deadline+6-time.monotonic())))
       if process.is_alive():process.kill();process.join(.2)
     done=set(active)
    for future in done:
     job,reservation,fd,identity,grant=active.pop(future);detail=None;code=None;used=0;known=False
     try:
      if not future.done():raise TimeoutError()
      result=future.result()
      if job[2]['schemaVersion']==retained_verification.SCHEMA:detail=result;used=0;retained_verification.sanitize_report(detail,job[2])
      elif prepare is run_preparation:detail=result;used=0 if detail.get('preparationReused') else sum(x['bytes'] for x in detail.get('outputs',[]))+detail.get('receiptBytes',0)
      else:detail,code,used=result
      if type(used) is not int or not 0<=used<=grant:raise ValueError('invalid-output-count')
      known=detail is None or detail.get('storageAccountingComplete',True) is True
     except (Exception,SystemExit):
      if activity is not None:activity.mark_uncertain()
      detail=None;used=0;code='global-deadline-exhausted' if time.monotonic()>=deadline else 'global-preparation-unavailable'
     if known and fd is not None:
      try:a.release_own_reservation(reservation,fd,identity)
      except Exception:code='reservation-release-failed';known=False
     elif fd is not None:
      # Unknown worker completion preserves the physical reservation and any private output.
      try:os.close(fd)
      except OSError:pass
     if not known:
      remaining=max(0,grant-used);uncertain.append([job[0],remaining]);uncertain_bytes+=remaining
      if code is None:code='global-preparation-state-uncertain'
     granted-=grant;prepared(job,detail,code,used)
 finally:
  if pool is not None:
   if prepare is run_preparation:
    processes=list((getattr(pool,'_processes',None) or {}).values());pool.shutdown(wait=False,cancel_futures=True)
    for process in processes:
     process.join(max(0,min(.5,deadline+10-time.monotonic())))
     if process.is_alive():process.terminate();process.join(max(0,min(.5,deadline+11-time.monotonic())))
     if process.is_alive():process.kill();process.join(.1)
   else:pool.shutdown(wait=True,cancel_futures=True)
   if activity is not None and (prepare is not run_preparation or not any(process.is_alive() for process in processes)):
    activity.confirm_all_stopped()
 if terminal is not None:terminal.update(preparation_queued=0);terminal.stage('saving')
 reuse_joins=None
 if 'knownIntakeSuccessor' in selected:
  reuse_joins=intake.join_outcomes(selected['knownIntakeSuccessor']['reuseJoins'],manifest,outcomes,binding_manifest=binding_manifest)
  for joined in reuse_joins:checkpoint(joined['assetIndex'],{'metadataReuseJoin':joined})
  if terminal is not None:terminal.update(failed=sum(r['stage']=='error' for r in outcomes),held=sum(r['stage']=='held' for r in outcomes))
 changes.sort(key=lambda row:row['assetIndex']);counts=meter.snapshot()
 report={'schemaVersion':SCHEMA,'status':'complete-with-errors' if errors or any(row['stage']=='error' for row in outcomes) else 'complete','errorCode':None,
  'manifestSHA256':manifest_sha,'selectionSHA256':a.sha(a.canonical(selected)),'assetCount':len(outcomes),'countryCount':249,'typeCount':13,
  'networkRequests':counts['requests'],'networkBytesRead':counts['bodyBytesRead'],'preparedBytes':output_bytes,'preparationUncertainGrants':sorted(uncertain),'preparedUncertainBytes':uncertain_bytes,'assetOutcomeGroups':group_outcomes(outcomes),'cellStageCounts':country_cells(manifest,outcomes),'changes':changes,
  'statPathCount':len(stat_rows),'statOutcomeGroups':[{'state':state,'pathRanges':ranges([i for i,value in enumerate(stat_rows) if value==state])} for state in sorted(set(stat_rows))],
  'checkpointCount':persisted,'checkpointIndexSHA256':a.sha(a.canonical(sorted(checkpoints.items()))),'detailSHA256':None,'detailPersisted':False,
  'runtimeCapabilities':capabilities,'resourceObservation':resources,'globalErrors':sorted(set(errors)),'maximumParallelTransfers':resources['ioWorkers'],'maximumPerHostTransfers':config['perHostWorkers'],'maximumParallelPreparations':resources['preparationWorkers'],'observedPeakTransfers':peak_io,'observedPeakPreparations':peak_prep,'wholeOperationSeconds':MAX_SECONDS,**a.SAFETY}
 if read_accounting is not None:report['retainedOriginalVerification']=read_accounting.summary(ranges)
 if recovery_proposals is not None:report['retainedTaiwanRecoveryProposals']=recovery_proposals
 if reuse_joins is not None:report['reuseOutcomeJoins']=reuse_joins
 if taiwan_diagnostics is not None:report['retainedTaiwanDiagnostics']=taiwan.sanitize_diagnostics(taiwan_diagnostics)
 if preparation_diagnostics is not None:report['retainedPreparationDiagnostics']=prepdiag.sanitize_diagnostics(preparation_diagnostics)
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
 for key,limit in [('networkRequests',intake.maximum_requests(source)),('networkBytesRead',source['hardTransferBytes']),('verifiedBytes',source['hardTransferBytes']),('localBodyBytes',source['hardTransferBytes'])]:
  if type(item[key]) is not int or not 0<=item[key]<=limit:raise ValueError('invalid-global-summary')
 a.validate_response_metadata(item['responseMetadata']);save.validate_policy(item['responsePolicy'])
 if item['cacheStatus'] not in {None,'downloaded-200','reused-fresh'} or item['originalDisposition'] not in {None,'saved-original','retained-original-no-network'} or item['privateSaveState'] not in {None,'none','partial-retained','uncommitted-original','saved-original'} or type(item['detailPersisted']) is not bool:raise ValueError('invalid-global-summary')
 for key in ('originalSHA256','detailSHA256'):
  if item[key] is not None and (not isinstance(item[key],str) or not re.fullmatch('[a-f0-9]{64}',item[key])):raise ValueError('invalid-global-summary')
 if success and (not item['verifiedBytes'] or not item['originalSHA256'] or not item['detailPersisted'] or not item['detailSHA256'] or not b.bounded_text(item['originalAcquiredAt'],64) or item['originalDisposition'] is None or (source['expectedBytes'] is not None and item['verifiedBytes']!=source['expectedBytes'])):raise ValueError('invalid-global-summary')
 if not success and (item['verifiedBytes'] or item['originalSHA256'] is not None or item['originalAcquiredAt'] is not None):raise ValueError('invalid-global-summary')

def validate_preparation(item):
 keys={'status','errorCode','stages','actualMediaType','originalSHA256','originalBytes','preparedBytes','preparedFiles','nextStageReady','detailSHA256','metrics','reusedFromAssetIndex','preparationReused','receiptSHA256','receiptBytes','storageAccountingComplete'}
 if type(item.get('storageAccountingComplete')) is not bool or type(item.get('preparationReused')) is not bool or type(item.get('receiptBytes')) is not int or not 0<=item['receiptBytes']<=1024**2:raise ValueError('invalid-global-summary')
 if item.get('receiptSHA256') is not None and (not isinstance(item['receiptSHA256'],str) or not re.fullmatch('[a-f0-9]{64}',item['receiptSHA256'])):raise ValueError('invalid-global-summary')
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
 meter=progress.get('meter',{'requests':0,'bodyBytesRead':0});meter=meter.snapshot() if hasattr(meter,'snapshot') else meter;items=[];sources={s['sourceKey']:s for s in selected['sources']}
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
 keys={'schemaVersion','status','errorCode','manifestSHA256','selectionSHA256','assetCount','countryCount','typeCount','networkRequests','networkBytesRead','preparedBytes','preparedUncertainBytes','preparationUncertainGrants','assetOutcomeGroups','cellStageCounts','changes','statPathCount','statOutcomeGroups','checkpointCount','checkpointIndexSHA256','detailSHA256','detailPersisted','runtimeCapabilities','globalErrors','maximumParallelTransfers','maximumPerHostTransfers','maximumParallelPreparations','observedPeakTransfers','observedPeakPreparations','resourceObservation','wholeOperationSeconds'}|set(a.SAFETY)
 optional=set(report)-keys
 if not keys<=set(report) or not optional<={'retainedTaiwanDiagnostics','reuseOutcomeJoins','retainedPreparationDiagnostics','retainedOriginalVerification','retainedTaiwanRecoveryProposals'}:raise ValueError('invalid-global-summary')
 if 'retainedTaiwanDiagnostics' in report:taiwan.sanitize_diagnostics(report['retainedTaiwanDiagnostics'])
 if 'retainedPreparationDiagnostics' in report:prepdiag.sanitize_diagnostics(report['retainedPreparationDiagnostics'])
 manifest=manifest_config();selected=selection_config();binding_manifest=None
 if 'retainedVerification' in selected:
  ext,plan,binding_manifest=retained_collection.validate_combined(selected,manifest,ROOT)
  retained_collection.sanitize_summary(report.get('retainedOriginalVerification'),manifest,ext,plan)
 elif 'retainedOriginalVerification' in report:raise ValueError('invalid-global-summary')
 if 'retainedTaiwanRecoveryProposals' in report:
  proposals=report['retainedTaiwanRecoveryProposals']
  if not isinstance(proposals,list) or len(proposals)!=3 or [r.get('sourceKey') for r in proposals]!=[s['sourceKey'] for s in selected['sources'] if s['sourceKey'] in twrecovery.PINS]:raise ValueError('invalid-global-summary')
  for row in proposals:twrecovery.sanitize_report(row)
 outcomes=expand_outcomes(report['assetOutcomeGroups'],len(manifest['assets']))
 if 'retainedOriginalVerification' in report:
  for index,state in retained_collection.observations(report['retainedOriginalVerification']).items():
   if state=='completed-verified' and outcomes[index]['custody']!='verified-original':raise ValueError('invalid-global-summary')
 if ('reuseOutcomeJoins' in report)!=('knownIntakeSuccessor' in selected):raise ValueError('invalid-global-summary')
 if 'reuseOutcomeJoins' in report:
  expected=intake.join_outcomes(selected['knownIntakeSuccessor']['reuseJoins'],manifest,deepcopy(outcomes),binding_manifest=binding_manifest)
  if report['reuseOutcomeJoins']!=expected:raise ValueError('invalid-global-summary')
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
 if not isinstance(report['preparationUncertainGrants'],list):raise ValueError('invalid-global-summary')
 uncertain_ids=set();uncertain_total=0
 for index,grant in report['preparationUncertainGrants']:
  if type(index) is not int or index in uncertain_ids or not 0<=index<len(outcomes) or type(grant) is not int or not 0<=grant<=DEFAULT_PARALLELISM['maximumOutputPerPreparationBytes']:raise ValueError('invalid-global-summary')
  uncertain_ids.add(index);uncertain_total+=grant
 if type(report['preparedUncertainBytes']) is not int or report['preparedUncertainBytes']!=uncertain_total or prepared+uncertain_total>MAX_OUTPUT_BYTES:raise ValueError('invalid-global-summary')
 for key in ('manifestSHA256','selectionSHA256','checkpointIndexSHA256','detailSHA256'):
  if key=='detailSHA256' and report[key] is None and report['detailPersisted'] is False:continue
  if not isinstance(report[key],str) or not re.fullmatch('[a-f0-9]{64}',report[key]):raise ValueError('invalid-global-summary')
 if type(report['checkpointCount']) is not int or not 0<=report['checkpointCount']<=len(outcomes) or type(report['detailPersisted']) is not bool or report['maximumPerHostTransfers']!=1 or report['wholeOperationSeconds']!=MAX_SECONDS:raise ValueError('invalid-global-summary')
 resource=report['resourceObservation']
 resource_keys={'logicalCPUs','affinityCPUs','cgroupCPUCap','effectiveCPUs','memoryAvailableBytes','cgroupMemoryHeadroomBytes','effectiveMemoryBytes','resourceLimitsIncomplete','ioWorkers','preparationWorkers','perHostWorkers','memoryPerPreparationBytes','memoryReserveBytes'}
 if not isinstance(resource,dict) or set(resource) not in (resource_keys,resource_keys|{'diagnostics'}) or type(resource['resourceLimitsIncomplete']) is not bool:raise ValueError('invalid-global-summary')
 if 'diagnostics' in resource:
  validate_resource_diagnostics(resource['diagnostics'])
  if resource['resourceLimitsIncomplete']!=bool(resource['diagnostics']['problemCodes']):raise ValueError('invalid-global-summary')
 for key in resource_keys-{'resourceLimitsIncomplete'}:
  if resource[key] is None and key in {'cgroupCPUCap','memoryAvailableBytes','cgroupMemoryHeadroomBytes'}:continue
  if type(resource[key]) is not int or not 0<=resource[key]<=1024**6:raise ValueError('invalid-global-summary')
 if not 1<=resource['ioWorkers']<=DEFAULT_PARALLELISM['ioWorkers'] or not 0<=resource['preparationWorkers']<=DEFAULT_PARALLELISM['preparationWorkers'] or resource['perHostWorkers']!=1:raise ValueError('invalid-global-summary')
 if report['maximumParallelTransfers']!=resource['ioWorkers'] or report['maximumParallelPreparations']!=resource['preparationWorkers']:raise ValueError('invalid-global-summary')
 for key,maximum in [('observedPeakTransfers',resource['ioWorkers']),('observedPeakPreparations',resource['preparationWorkers'])]:
  if type(report[key]) is not int or not 0<=report[key]<=maximum:raise ValueError('invalid-global-summary')
 if not isinstance(report['globalErrors'],list) or any(c not in GLOBAL_ERRORS for c in report['globalErrors']):raise ValueError('invalid-global-summary')
 caps=report['runtimeCapabilities'];expected={'stdlibFormats':['csv','tsv','json','xml','html','zip','xlsx','docx'],'optionalParsers':{'pypdf':None,'xlrd':None,'poppler':None},'handlerVersion':None,'pythonVersion':None,'isolatedWorker':None}
 if not isinstance(caps,dict) or set(caps)!=set(expected) or caps['handlerVersion']!=media.VERSION or type(caps['isolatedWorker']) is not bool or caps['stdlibFormats']!=expected['stdlibFormats'] or not isinstance(caps['pythonVersion'],str) or not re.fullmatch('[0-9.]{1,32}',caps['pythonVersion']):raise ValueError('invalid-global-summary')
 if not isinstance(caps['optionalParsers'],dict) or set(caps['optionalParsers'])!=set(expected['optionalParsers']):raise ValueError('invalid-global-summary')
 for parser in caps['optionalParsers'].values():
  if set(parser)!={'available','version'} or type(parser['available']) is not bool or (parser['version'] is not None and (not isinstance(parser['version'],str) or not re.fullmatch('[a-zA-Z0-9.+_() -]{1,128}',parser['version']))):raise ValueError('invalid-global-summary')
 if report['status']=='complete' and (report['globalErrors'] or any(r['stage']=='error' for r in outcomes)):raise ValueError('invalid-global-summary')
 if len(a.canonical(report))>MAX_SUMMARY:raise ValueError('invalid-global-summary')
 return report


class OwnerRuntime:
 """Exact one-time cross-route handover; stable owner-local custody thereafter."""
 def __init__(self,config,selected):
  self.config=config;self.selected=selected;self.uid=os.getuid()
  if self.uid==0:raise a.RefreshError('owner-handover-invalid')
  self.home=a.owned_directory(Path(pwd.getpwuid(self.uid).pw_dir))
  parent=a.owned_directory(self.home/'src/offmenu-data')
  self.root=save.private_directory(parent/'owner-collection-runtime',a)
  work=save.private_directory(self.root/'collection',a)
  save.private_directory(work/'intents',a);save.private_directory(self.root/'tmp',a)
  self.native=Path(config['nativeClaimsRoot']);self.runner_work=Path('/srv/offmenu-refresh/outputs/collection');self.runner_cache=Path('/srv/offmenu-refresh/cache')
  self.access={str(p):self.access_state(p) for p in (self.runner_work,self.runner_cache)}
 @staticmethod
 def access_state(path):
  try:
   path=a.safe_path(path);info=path.stat()
   if not stat.S_ISDIR(info.st_mode):return 'not-directory'
   with os.scandir(path) as entries:next(entries,None)
   return 'readable'
  except FileNotFoundError:return 'absent'
  except PermissionError:return 'inaccessible'
  except a.RefreshError:return 'unsafe-path'
  except OSError:return 'io-uncertain'
 def provenance(self):
  return {'handoffId':self.config['handoffId'],'runtimeConfigSHA256':OWNER_PIN[1],
   'dispatchHoldSHA256':self.config['dispatchHoldPin']['sha256'],'executionContext':'owner-manual-foo',
   'runnerResumeRequiresOutcomeImport':True}
 def admit(self,work,source,intent,old_claim,prior,deadline):
  a.deadline_check(deadline)
  if source['sourceKey'] not in self.config['sourceKeys']:raise a.RefreshError('owner-handover-invalid')
  if self.access_state(self.native)!='readable':raise a.RefreshError('owner-native-claims-unavailable')
  urls=[source['url']]+[u for u in source.get('aliases',[]) if u.startswith(('https://','http://'))]
  for url in urls:
   path=a.safe_path(self.native/(a.sha(url.encode())+'.json'))
   try:path.lstat()
   except FileNotFoundError:continue
   raise a.RefreshError('known-exact-source-alternate-cache')
  # Local old-style claims are never migrated or treated as our predecessor.
  cached=work/'source-cache/requests'/a.sha(a.canonical(a.source_spec(source).identity()))
  if old_claim.exists() or any((cached/n).exists() for n in ('current.json','recovery.json','body.partial')) or (work/('reservation-'+a.sha(source['url'].encode())+'.bin')).exists():raise a.RefreshError('source-claim-uncertain')
  coverage=a.inspect_runner_metadata((self.native,work),source,intent,old_claim,deadline)
  for historical in (self.runner_work,self.runner_cache):
   state=self.access_state(historical)
   if state in {'absent','inaccessible'}:continue # Exact source-bound dispatch hold + pinned diagnostic, never an empty-catalogue assertion.
   if state!='readable':raise a.RefreshError('owner-handover-invalid')
   historical_claim=self.runner_work/'intents'/(a.sha(source['url'].encode())+'.json')
   if historical==self.runner_work:
    cached=historical/'source-cache/requests'/a.sha(a.canonical(a.source_spec(source).identity()))
    private=historical/'private-originals'/a.sha(a.canonical(source))
    if any(a.safe_path(cached/n).exists() for n in ('current.json','recovery.json','body.partial')) or a.safe_path(historical/('reservation-'+a.sha(source['url'].encode())+'.bin')).exists() or a.safe_path(private).exists():raise a.RefreshError('source-claim-uncertain')
   if historical==self.runner_work and prior is not None:
    a.read_metadata(historical_claim,expected_sha256=prior['intentSHA256'])
    observed=save.diagnostic_module().local_state(self.runner_work,source,prior)
    if observed['intentSHA256']!=prior['intentSHA256'] or any(observed[k]['state']!='absent' for k in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation')):raise a.RefreshError('predecessor-evidence-mismatch')
   elif historical==self.runner_work and historical_claim.exists():raise a.RefreshError('source-claim-uncertain')
   extra=a.inspect_runner_metadata((historical,),source,intent,historical_claim if prior is not None else old_claim,deadline)
   for key in ('entriesExamined','metadataFilesRead','metadataBytesRead','missingRoots'):coverage[key]+=extra[key]
  return coverage

def owner_config(selected):
 value=a.strict_json(a.preparation_module().pinned_bytes(ROOT,OWNER_PIN))
 if (value.get('schemaVersion')!='offmenu-owner-local-runtime/1' or value.get('mode')!='owner-local'
     or value.get('runtimeRootSuffix')!='src/offmenu-data/owner-collection-runtime'
     or value.get('nativeClaimsRoot')!='/home/user/src/offmenu-data/originals/country-followthrough-20261015/claims'
     or value.get('sourceKeys')!=[s['sourceKey'] for s in selected['sources']]
     or value.get('sourceContractSHA256')!=[a.sha(a.canonical(s)) for s in selected['sources']]
     or value.get('runnerMustRemainPausedUntilManualOutcomeImported') is not True
     or value.get('globalRequestAdmitted') is not False):raise a.RefreshError('owner-handover-invalid')
 # validate_mode verifies every predecessor against the exact published five-source diagnostic.
 save.validate_mode(selected['privateOriginalDownload'],selected,a)
 pin=value['dispatchHoldPin'];hold=a.strict_json(a.preparation_module().pinned_bytes(ROOT,(pin['path'],pin['sha256'])))
 if (hold.get('handoffId')!=value['handoffId'] or [r['sourceKey'] for r in hold['selectedSources']]!=value['sourceKeys']
     or [r['sourceContractSHA256'] for r in hold['selectedSources']]!=value['sourceContractSHA256']
     or hold['historicalFailedPredecessors']!=selected['privateOriginalDownload']['predecessors']
     or hold['overlapHold']['active'] is not True or hold['overlapHold']['automaticRunnerSubmissionPermitted'] is not False
     or hold['runnerState']['queuedTotal']!=0 or hold['runnerState']['inProgressTotal']!=0):raise a.RefreshError('owner-handover-invalid')
 return value

def manual_envelope(report,runtime):
 return {'schemaVersion':'offmenu-owner-manual-global-result/1','executionContext':'owner-manual-foo',
  'invokingUID':runtime.uid,'outputRoot':str(runtime.root),'handover':runtime.provenance(),
  'historicalRunnerRootAccess':runtime.access,'nativeClaimsRoot':str(runtime.native),'nativeCoverageExhaustive':False,
  'globalReportSHA256':a.sha(a.canonical(report)),'globalReport':report}

def publisher_module():
 spec=importlib.util.spec_from_file_location('manual_results_publisher',ROOT/'scripts/publish-manual-global-result.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 if OWNER_PIN!=LEGACY_OWNER_PIN:
  config=owner_config(selection_config());pin=config['dispatchHoldPin'];hold=pinned((pin['path'],pin['sha256']))
  if not re.fullmatch('[a-f0-9]{40}',hold['source'].get('trustedCommit') or ''):raise a.RefreshError('owner-handover-invalid')
  m.HANDOFF=config['handoffId'];m.HANDOFF_PATH=pin['path'];m.HOLD_SHA256=pin['sha256'];m.RUNTIME_SHA256=OWNER_PIN[1];m.BASE_SOURCE=hold['source']['trustedCommit'];m.DEST='docs/handover/2026-10-18/foo-owner-custody/manual-global/'+m.HANDOFF
 return m

def saved_manual_result(runtime,envelope=None):
 folder=save.private_directory(runtime.root/'collection/manual-results',a)
 if envelope is not None:
  raw=a.canonical(envelope);digest=a.sha(raw);name='result-'+digest+'.json'
  a.write_immutable(folder/name,envelope)
  save.write_private_intent(folder/'latest.json',{'schemaVersion':'offmenu-manual-result-pointer/1','resultFilename':name,'resultSHA256':digest},a)
 else:
  pointer,_=a.read_metadata(folder/'latest.json')
  if set(pointer)!={'schemaVersion','resultFilename','resultSHA256'} or pointer['schemaVersion']!='offmenu-manual-result-pointer/1' or not re.fullmatch(r'result-[a-f0-9]{64}\.json',pointer['resultFilename']) or pointer['resultFilename']!='result-'+pointer['resultSHA256']+'.json':raise a.RefreshError('owner-handover-invalid')
  name=pointer['resultFilename'];digest=pointer['resultSHA256'];envelope,_=a.read_metadata(folder/name,expected_sha256=digest)
 return envelope,folder/name,digest

def verify_manual_handover():
 return publisher_module().verify_active_handover(sys.modules[__name__])

def publish_manual_result(envelope):
 return publisher_module().publish_result(envelope,sys.modules[__name__])

@contextmanager
def without_github_credentials():
 # Only the GitHub preflight/publisher may inherit these existing credentials.
 credentials={key:os.environ.pop(key) for key in ('GH_TOKEN','GITHUB_TOKEN') if key in os.environ}
 try:yield
 finally:
  for key in ('GH_TOKEN','GITHUB_TOKEN'):os.environ.pop(key,None)
  os.environ.update(credentials)

def main(argv=None):
 terminal=ProgressReporter().start()
 try:
  result=_main(argv,terminal=terminal)
 except BaseException as error:
  terminal.stop('interrupted' if isinstance(error,KeyboardInterrupt) else 'failed');raise
 terminal.stop('finished' if result==0 else 'failed');return result

def _main(argv=None,terminal=None):
 args=sys.argv[1:] if argv is None else argv
 try:
  with owner_successor_profile(args):return _main_in_profile(args,terminal=terminal)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):
  print(a.canonical(blocked_report('owner-handover-invalid')).decode(),end='');return 2

def _main_in_profile(argv=None,terminal=None):
 report=blocked_report('global-config-invalid');selected=None;progress={};runtime=None;old_output=a.OUTPUT
 args=sys.argv[1:] if argv is None else argv
 if args==['--mode','user','--publish-only']:
  if terminal is not None:terminal.stage('publishing')
  try:
   selected=selection_config();runtime=OwnerRuntime(owner_config(selected),selected);envelope,path,digest=saved_manual_result(runtime)
   publication=publish_manual_result(envelope)
   print(a.canonical({'schemaVersion':'offmenu-manual-command-outcome/1','resultPath':str(path),'resultSHA256':digest,'collectionStatus':envelope['globalReport']['status'],'publication':publication}).decode(),end='');return 0 if publication.get('verified') is True or publication.get('status') in {'published-and-verified','verified-existing','verified-after-uncertain-write'} else 3
  except Exception:
   print(a.canonical({'schemaVersion':'offmenu-manual-command-outcome/1','publication':{'status':'failed-local-results-retained'},'publishOnly':True,'networkRequests':0}).decode(),end='');return 3
 try:
  if args not in ([],['--mode','user'],['--mode','runner']):raise a.RefreshError('unexpected-arguments')
  if terminal is not None:terminal.stage('inventory')
  selected=selection_config();manifest=manifest_config();prep=a.preparation_module();snapshot=prep.imported_snapshot(ROOT);adopted=a.strict_json(prep.pinned_bytes(ROOT,prep.SUMMARY_PIN))
  if args==['--mode','user']:
   runtime=OwnerRuntime(owner_config(selected),selected);verify_manual_handover();a.OUTPUT=runtime.root
  with without_github_credentials():
   report=run_global(manifest,selected,adverse_evidence=b.source_conflicts(selected,snapshot,adopted),progress=progress,owner_runtime=runtime,terminal=terminal);report=sanitize_report(report)
 except Exception:
  if selected is not None and 'meter' in progress:report=projection_failure(selected,progress)
  elif runtime is not None:report=blocked_report('owner-handover-invalid')
 finally:a.OUTPUT=old_output
 if runtime is None:
  print(a.canonical(report).decode(),end='');return 0 if report['status']=='complete' else 2
 envelope=manual_envelope(report,runtime);outcome={'schemaVersion':'offmenu-manual-command-outcome/1','collectionStatus':report['status'],'publication':{'status':'not-attempted'},'resultPath':None,'resultSHA256':None}
 try:
  if terminal is not None:terminal.stage('saving')
  envelope,path,digest=saved_manual_result(runtime,envelope);outcome.update(resultPath=str(path),resultSHA256=digest)
  if terminal is not None:terminal.stage('publishing')
  outcome['publication']=publish_manual_result(envelope)
 except Exception:outcome['publication']={'status':'failed-local-results-retained'}
 print(a.canonical(outcome).decode(),end='')
 if outcome['publication'].get('status') not in {'published-and-verified','verified-existing','verified-after-uncertain-write'}:return 3
 return 0 if report['status']=='complete' else 2
if __name__=='__main__':raise SystemExit(main())
