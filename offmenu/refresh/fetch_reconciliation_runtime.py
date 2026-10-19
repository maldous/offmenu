"""Source-bound whole-inventory fetch amendment. Explicit selection, no default I/O."""
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path
import importlib.util,time,re,base64,hashlib,zlib
from .core import canonical,sha,strict_json,RefreshError
from . import fetch_metadata_reconciliation as metadata
from . import fetch_evidence as evidence
from . import reviewed_fetch_intake as intake
from . import owner_head_diagnostic as heads

ROOT=Path(__file__).resolve().parents[2]
CONFIG_PATH='docs/collection-selections/whole-inventory-fetch-selection.json'
CONFIG_SHA256='d07e940cc50c83963b3ded0d18546260be8aa4e902bd77c41c77a9b643d93f6e' # Final immutable candidate selection is pinned during composition.
HEAD_ACTIVATION_SHA='a275ce332a340b4e2eb735860f2caf9cd437edc7b74854faeaf4768b5cee5baf'
HEAD_COLLECTOR_PATH='scripts/owner-head-reviewed-collector.py'
HEAD_COLLECTOR_SHA='497b9b0776be2b2280f745fa38c185e765c7b3de0e2737e09c2d550d0725c767'
HEAD_SUPERVISOR_SHA='fbd39828ba82138e77e87fa6631fe3abf2ac2f183fd8b78fe2c7987130c61026'
INPUT_PATHS={'closure_raw':'docs/collection-selections/fetch-closure/all-4753-fetch-closure-input.json',
 'runtime_manifest_raw':'docs/collection-selections/global-comprehensive-manifest.json',
 'owner_config_raw':'docs/collection-selections/owner-comprehensive-runtime.json',
 'owner_selection_raw':'docs/collection-selections/global-comprehensive-selection.json',
 'dispatch_hold_raw':'docs/operations/global-comprehensive-manual-handoff-20261018.json'}
PROPOSAL_PATH='docs/collection-selections/fetch-closure/owner-metadata-reconciliation-proposal.json'
AUTHORITY_PATH='docs/operations/global-fetch-closure-authority-20261019.json'
AUTHORITY_BRANCH='integration/runner-cutover-disposition-20261018'
_REPORT_CONTEXT=None

def fail():raise RefreshError('fetch-reconciliation-config-invalid')

def configuration(root=ROOT,*,allow_inactive=False):
 if CONFIG_SHA256 is None:return None
 raw=(Path(root)/CONFIG_PATH).read_bytes()
 if len(raw)>1024*1024 or sha(raw)!=CONFIG_SHA256:fail()
 value=strict_json(raw)
 if value['status']=='prepared-for-review-not-active' and not allow_inactive:return None
 if value['status'] not in ('prepared-for-review-not-active','parent-reviewed-owner-manual')or value['schemaVersion']!='offmenu-whole-inventory-fetch-selection/1' or value['handoffId']!=metadata.HANDOFF_ID:fail()
 if value['oldSourceGETs']!=0 or value['maximumGETs']!=26 or value['maximumHEADs']!=5 or value['maximumBodyBytes']!=644874240 or value['maximumHeaderBytes']!=2031616 or value['maximumRetries']!=0 or value['globalCoverageComplete']is not False:fail()
 if value['maximumSeconds']!=1200 or value['maximumMetadataReadBytes']!=16493475:fail()
 if value['transferSelectionSHA256']!=sha(canonical(value['transferSelection'])):fail()
 if value['status']=='parent-reviewed-owner-manual':authority_document(value,root=root)
 return value

def authority_scope(config):
 return {'handoffId':metadata.HANDOFF_ID,'transferSelectionSHA256':config['transferSelectionSHA256'],
  'metadataSelectionSHA256':sha(canonical(config['metadataSelection'])),'headActivationSHA256':HEAD_ACTIVATION_SHA,
  'taiwanAcceptanceSHA256':sha(canonical(config['taiwanAcceptance'])),
  'oldSourceGETs':0,'maximumGETs':26,'maximumHEADs':5,'maximumRequests':31,
  'maximumBodyBytes':644874240,'maximumHeaderBytes':2031616,'maximumRetries':0,'maximumSeconds':1200,
  'maximumMetadataReadBytes':16493475,'globalCoverageComplete':False}

def authority_document(config,*,root=ROOT):
 pin=config.get('additionalAuthorityPin')
 if (type(pin)is not dict or set(pin)!={'path','sha256','bytes','gitBlobSha','commit'}
  or pin['path']!=AUTHORITY_PATH or type(pin['bytes'])is not int or not 0<pin['bytes']<=128*1024
  or any(type(pin[k])is not str or re.fullmatch('[a-f0-9]{'+str(n)+'}',pin[k])is None for k,n in [('sha256',64),('gitBlobSha',40),('commit',40)])):fail()
 raw=(Path(root)/AUTHORITY_PATH).read_bytes()
 blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or blob!=pin['gitBlobSha']:fail()
 doc=strict_json(raw)
 if (doc.get('schemaVersion')!='offmenu-additive-fetch-authority/1' or doc.get('status')!='parent-adopted-owner-manual'
  or doc.get('scope')!=authority_scope(config) or doc.get('overlapHold')!={'active':True,'automaticRunnerSubmissionPermitted':False,'scope':'exact26-new-GETs-five-HEADs-92-metadata-files-three-retained-references'}
  or doc.get('priorHandoffUnchanged')is not True or doc.get('failedAcquisitionIntentsMayReset')is not False):fail()
 return doc,raw

def verify_additional_authority(config,g,api=None):
 # Read-only current-branch check; this does not reinterpret the old002 hold.
 _,raw=authority_document(config);p=g.publisher_module();client=p.BudgetAPI(api if api is not None else p.github_api(g))
 client.end=min(client.end,time.monotonic()+60);client.api.deadline=client.end;p.identity(client)
 ref=client.call('GET','repos/'+p.REPOSITORY+'/git/ref/heads/'+AUTHORITY_BRANCH)
 commit=ref.get('object',{}).get('sha')
 if type(commit)is not str or re.fullmatch('[a-f0-9]{40}',commit)is None:fail()
 comparison=client.call('GET','repos/'+p.REPOSITORY+'/compare/'+config['additionalAuthorityPin']['commit']+'...'+commit)
 if comparison.get('status')not in ('ahead','identical'):fail()
 if not p.same_file(p.contents(client,AUTHORITY_PATH,commit),raw):fail()
 return {'status':'active-verified','commit':commit,'authoritySHA256':sha(raw)}

# Lossless source packaging only; downstream inventory pins remain unchanged.
CLOSURE_PACKED_PATH=INPUT_PATHS['closure_raw']+'.gz'
CLOSURE_PACKED_BYTES=1432400
CLOSURE_PACKED_SHA256='3dbfb85452f8ac9e4e99e6e468a83873a2e58dc6809d0eab52eb946cc128ce03'

def closure_bytes(root=ROOT):
 try:
  with (Path(root)/CLOSURE_PACKED_PATH).open('rb')as stream:
   packed=stream.read(CLOSURE_PACKED_BYTES+1)
  if len(packed)!=CLOSURE_PACKED_BYTES or sha(packed)!=CLOSURE_PACKED_SHA256:fail()
  expected,extent=metadata.INVENTORY_PINS['closure_raw']
  decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
  raw=decoder.decompress(packed,extent+1)
  if len(raw)!=extent or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or sha(raw)!=expected:fail()
  return raw
 except (OSError,zlib.error):fail()

@lru_cache(maxsize=1)
def inventory():
 return metadata.build_inventory(**{k:closure_bytes(ROOT)if k=='closure_raw'else(ROOT/v).read_bytes()for k,v in INPUT_PATHS.items()})

@lru_cache(maxsize=1)
def proposal():
 raw=(ROOT/PROPOSAL_PATH).read_bytes();metadata.inspect_proposal(raw);return raw

def metadata_validator(value,config=None):
 config=config or configuration(allow_inactive=True)
 return metadata.sanitize_report(value,proposal(),inventory=inventory(),parent_selection=config['metadataSelection'])

@contextmanager
def reviewed_head_dependencies():
 # Preserve the component's exact reviewed collector identity rather than
 # broadening its manifest to a changing collector. The relocated snapshot has
 # the same repository root and unchanged002 guards; no entrypoint is invoked.
 original_bytes,original_module=heads.repository_bytes,heads.collector_module
 def repository_bytes(root,path,expected):
  if path=='scripts/collect-fixed-global.py' and expected==HEAD_COLLECTOR_SHA:
   return original_bytes(root,HEAD_COLLECTOR_PATH,HEAD_COLLECTOR_SHA)
  return original_bytes(root,path,expected)
 def collector_module(root):
  raw=original_bytes(root,HEAD_COLLECTOR_PATH,HEAD_COLLECTOR_SHA)
  path=Path(root)/HEAD_COLLECTOR_PATH
  spec=importlib.util.spec_from_file_location('owner_head_existing_collector',path)
  module=importlib.util.module_from_spec(spec);exec(compile(raw,str(path),'exec'),module.__dict__)
  return module
 heads.repository_bytes,heads.collector_module=repository_bytes,collector_module
 try:yield
 finally:heads.repository_bytes,heads.collector_module=original_bytes,original_module

def observe_headers(config,*,seconds=90):
 # Called before progress/worker threads and before the global writer lease.
 if config is None:return None
 if config['headActivationSHA256']!=HEAD_ACTIVATION_SHA:fail()
 heads.ACTIVATION_SHA256=HEAD_ACTIVATION_SHA
 raw=(ROOT/'scripts/diagnose-owner-five-heads.py').read_bytes()
 if sha(raw)!=HEAD_SUPERVISOR_SHA:fail()
 spec=importlib.util.spec_from_file_location('fetch_owner_head_supervisor',ROOT/'scripts/diagnose-owner-five-heads.py')
 module=importlib.util.module_from_spec(spec);exec(compile(raw,str(spec.origin),'exec'),module.__dict__)
 with reviewed_head_dependencies():value=module.supervise(seconds=min(90,seconds))
 heads.validate_report(value);return value

def begin(config,*,owner_runtime,lease_fd,deadline,adapter,private_directory,current_adverse_evidence):
 """Metadata recovery precedes any new-source claim admission, under one lease."""
 global _REPORT_CONTEXT
 _REPORT_CONTEXT=None
 if config is None:return None,None
 if not callable(current_adverse_evidence) or type(deadline)not in (int,float) or not time.monotonic()<deadline<=time.monotonic()+1200:fail()
 selected=config['metadataSelection'];targets={r['targetId']:r for r in selected['targets']}
 # The exact parent-selected metadata-only read is distinct from original access.
 # Recheck immutable selection and current path-specific no-read observations on
 # both sides of every read. All original no-read rows remain suppressed by the
 # reader's reviewed held-ID catalogue and never followed.
 def clear(binding):
  now=time.monotonic();fresh=configuration()
  decision='unknown'
  if fresh==config and targets.get(binding['targetId'])==binding:
   adverse=current_adverse_evidence()
   if type(adverse)not in (list,tuple):fail()
   blocked=any(type(r)is dict and binding['path']in (r.get('path'),r.get('originalPath'),r.get('metadataPath')) for r in adverse)
   decision='held' if blocked else 'clear'
  return {'schemaVersion':metadata.CLEARANCE_SCHEMA,'target':binding,'evidenceSHA256':selected['clearanceEvidenceSHA256'],'checkedMonotonic':now,'expiresMonotonic':min(deadline,now+5),'decision':decision}
 result=metadata.reconcile_metadata(proposal(),parent_selection=selected,inventory=inventory(),owner_runtime=owner_runtime,lease_fd=lease_fd,current_read_holds=clear,absolute_deadline=min(deadline,time.monotonic()+180))
 metadata_validator(result,config)
 ref=evidence.save('metadata-reconciliation',result,output_root=owner_runtime.root,adapter=adapter,validator=lambda v:metadata_validator(v,config),private_directory=private_directory)
 _REPORT_CONTEXT=(result,sha(canonical(result)),sha(canonical(config)),owner_runtime,deadline)
 return result,ref

def extension(config,result,*,owner_runtime,adapter,current_holds):
 if config is None:return None
 context=_REPORT_CONTEXT
 if context is None or context[0]is not result or context[1]!=sha(canonical(result))or context[2]!=sha(canonical(config))or context[3]is not owner_runtime or time.monotonic()>=context[4]:fail()
 selection=config['transferSelection']
 authority=intake.admit_authority(selection,expected_selection_sha256=config['transferSelectionSHA256'],baseline_manifest_raw=(ROOT/INPUT_PATHS['runtime_manifest_raw']).read_bytes(),baseline_selection_raw=(ROOT/INPUT_PATHS['owner_selection_raw']).read_bytes())
 runtime=intake.OwnerExtension(owner_runtime,authority,metadata_report=result,metadata_validator=lambda v:metadata_validator(v,config),current_holds=current_holds,adapter=adapter)
 return {'authority':authority,'owner_runtime':runtime,'sources':intake.prepared_sources(),'absoluteDeadline':context[4],'samePassMetadataSHA256':context[1],
  'mode':{'predecessors':[],'diagnosticReportPin':None,'freshSources':[s['sourceKey']for s in intake.prepared_sources()]}}

def validate_evidence_refs(refs):
 if type(refs)is not list or len(refs)>2:fail()
 seen=set()
 for ref in refs:
  evidence.validate_reference(ref)
  if ref['kind']in seen:fail()
  seen.add(ref['kind'])
 return refs

def load_evidence(ref,output_root):
 validate=evidence_validator(ref['kind'])
 return evidence.load(ref,output_root=output_root,validator=validate)

def evidence_validator(kind):
 if kind=='metadata-reconciliation':return metadata_validator
 if kind=='response-diagnostics':return heads.validate_report
 fail()
