"""Exact full-contract private-file intake. No implicit authority or redirects.

Candidate descriptors are converted without consulting suffix-derived endpoint
projections. A separately reviewed active authority is required before custody
or transport. Parsing/extraction and licence inference are intentionally absent.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qsl
import hashlib
import importlib.util
import os
import re
import stat
from .core import RefreshError, canonical, sha, strict_json
from .acquisition import SourceSpec
from . import known_asset_intake as legacy_intake
from .retained_integrity_verification import open_fixed

ROOT=Path(__file__).resolve().parents[2]
CANDIDATE_PATH='docs/collection-selections/reviewed-fetch-candidate-contracts.json'
CANDIDATE_SHA='a2c10443af08406fc085c155f988c1e746882324f6d0a0f9f459ad34cc2b3682'
DEPENDENCY_SHA='fb6dce1deb03dafd5a7070c782c84e3e4d166db7afe8c6ff1cb7f6211cd1630b'
BASE_MANIFEST_SHA='7ffa2f5ce688c6fde5019b9252fbb9f96b3037f76337598cc05f76c37ef8754a'
BASE_SELECTION_SHA='81c0c919644d6df86681b4ef6ee946a25a191f85a0080a66e327c0b20d311a08'
SCHEMA='offmenu-reviewed-fetch-intake/1'
SAVER_SHA='e46e2ca68418b12ec863bec7d1471b1014b58753c90df3f3606ff79ac47a5b58'
ERROR_CODES=legacy_intake.ERROR_CODES|frozenset({'fetch-extension-custody-unresolved','fetch-extension-inactive','fetch-extension-contract-invalid','fetch-extension-media-mismatch','fetch-extension-identity-changed'})
MIMES={'application/pdf':('pdf','pdf-prefix-and-eof'),'application/json':('json','json-prefix'),
 'application/vnd.ms-excel':('xls','ole-container-prefix'),
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':('docx','zip-container-prefix'),
 'application/rss+xml':('xml','rss-root-prefix')}
_SEAL=object()


def fail(code='fetch-extension-contract-invalid'):raise RefreshError(code)
def require(value):
 if not value:fail()
def is_source(source):return isinstance(source,dict) and source.get('mediaIntake',{}).get('schemaVersion')==SCHEMA


def candidate_bundle(root=ROOT):
 raw=(Path(root)/CANDIDATE_PATH).read_bytes()
 require(len(raw)==328279 and sha(raw)==CANDIDATE_SHA)
 value=strict_json(raw)
 require(value['schemaVersion']=='offmenu-source-bound-fetch-candidate-extension/1'
         and value['selectedAssetIds']==[] and value['baseManifestPin']['sha256']==BASE_MANIFEST_SHA)
 return value


def convert_record(row):
 """Prospective deterministic conversion. Returning a descriptor grants no I/O."""
 c=row['contract'];q=c['request'];response=c['response'];b=c['bounds'];u=urlsplit(q['url'])
 require(c['schemaVersion']=='offmenu-candidate-transfer-contract/1' and c['assetId']==row['assetId']
  and row['selected'] is False and c['activation']['runtimeEnabled'] is False
  and c['activation']['privateCustodyApproved'] is None
  and q['method']=='GET' and q['bodyUTF8']=='' and q['bodySHA256']==sha(b'')
  and u.scheme=='https' and u.hostname==q['host'] and u.path==q['path']
  and not u.username and not u.password and not u.fragment and u.port in (None,443)
  and [list(x)for x in parse_qsl(u.query,keep_blank_values=True,strict_parsing=True)]==q['exactQueryPairs']
  and sorted(set(k for k,_ in q['exactQueryPairs']))==sorted(q['queryKeyAllowlist'])
  and q['cookies'] is False and q['credentials']=='none' and q['referer'] is None
  and q['headers']=={'Accept-Encoding':'identity'}
  and response['successStatus']==200 and len(response['acceptedContentTypes'])==1
  and response['acceptedContentTypes'][0]in MIMES
  and response['expectedBytes'] is None and response['expectedSHA256'] is None
  and response['rejectDuplicateCriticalHeaders'] is True
  and response['rejectUnexpectedEncoding'] is True and response['rejectAmbiguousFraming'] is True
  and b['metadataEnvelopeBytes']==65536 and b['maxWholeBodyGETs']==b['maxRequests']==1
  and b['maxHEADs']==b['maxRedirects']==b['maxRetries']==0 and b['rangeOrResume'] is False
  and b['maxSeconds']==300 and b['maxStallSeconds']==45
  and type(b['maxBodyBytes'])is int and 0<b['maxBodyBytes']<=64*1024**2
  and c['permissions']['proposedPrivateRead'] is True and c['permissions']['proposedPrivateCopy'] is True
  and c['permissions']['proposedExtract'] is False and c['permissions']['runtimeExtract'] is False
  and c['custody']['minimumDedupSeconds']>=30*86400
  and c['custody']['partialOrUncertainIntentBlocks'] is True
  and c['custody']['clearOrResetClaim'] is False)
 mime=response['acceptedContentTypes'][0];ext,observation=MIMES[mime]
 # Existing workflow flags are retained as evidence, not silently recast as publisher restrictions.
 holds=row['retainedConditions'];source_holds=holds['sourceStageHolds']
 require(not source_holds)
 downstream=list(dict.fromkeys(holds['downstreamHolds']+holds['extraDownstreamHolds']))
 source={'schemaVersion':'offmenu-fixed-source-contract/1','sourceKey':c['sourceKey'],
  'url':q['url'],'aliases':[],'expectedBytes':None,'hardTransferBytes':b['maxBodyBytes'],
  'wholeOperationSeconds':b['maxSeconds'],'checksums':{},'validation':{'kind':'fetch-prefix-only'},
  'rightsReference':'Exact reviewed public-offer private-original fetch only; commercial, redistribution, semantic and downstream terms remain separately unresolved.',
  'release':'unversioned-at-fetch','queryKeys':q['queryKeyAllowlist'],
  'expectedResponse':{'content-type':mime},'historicalPreparationExceptions':[],
  'privateCustodyApproved':True,'sourceAcquisitionHeld':False,'downstreamHolds':downstream,
  'mediaIntake':{'schemaVersion':SCHEMA,'assetId':row['assetId'],'originalFilename':'original.'+ext,
   'method':'GET','body':'','exactQueryPairs':q['exactQueryPairs'],'maximumHeaderBytes':65536,
   'maximumRequests':1,'maximumRedirects':0,'maximumRetries':0,'redirect':None,
   'permissions':{'read':True,'copy':True,'extract':False},
   'integrity':{'handler':'bounded-streamed-original-hash-and-media-sniff','maximumSniffBytes':65536,
                'observation':observation,'fullStructuralValidation':False,'decompressionAllowed':False},
   'attributionReference':{'sourceRole':row['sourceRole'],'candidateContractSHA256':sha(canonical(c)),
       'publisherEvidenceSHA256':sha(canonical(row['publicOfferEvidence'])),
       'releaseEvidenceSHA256':sha(canonical(c['release']))},
   'candidateRecordSHA256':sha(canonical(row)),'candidateContractSHA256':sha(canonical(c)),
   'originalAssetSHA256':row['originalAssetSHA256'],'retainedConditions':deepcopy(holds),
   'privateFetchAuthority':deepcopy(row['privateFetchAuthority']),
   'reviewStatus':'prepared-for-independent-runtime-review'}}
 source_spec(source).validate()
 return source


def prepared_sources(root=ROOT):return [convert_record(r)for r in candidate_bundle(root)['records']]
def source_spec(source):
 return SourceSpec(source_key=source['sourceKey'],url=source['url'],policy_fingerprint=sha(canonical(source)),
  rights_reference=source['rightsReference'],enabled=True,rights_approved=True,held=False,ttl_seconds=30*86400,
  max_bytes=source['hardTransferBytes'],release=source['release'],query_keys=tuple(source['queryKeys']))


class FetchAuthority:
 """Process-local selected contract set; created by exact owner admission only."""
 __slots__=('_seal','_sources','selectionSHA256','maximumRequests','maximumBytes','requiredMetadataTargets')
 def __init__(self,seal,sources,selection):
  if seal is not _SEAL:fail('fetch-extension-inactive')
  self._seal=seal;self._sources={s['sourceKey']:canonical(s)for s in sources}
  self.requiredMetadataTargets=deepcopy(selection['requiredMetadataTargetIds']);self.selectionSHA256=sha(canonical(selection));self.maximumRequests=selection['maximumRequests'];self.maximumBytes=selection['maximumBodyBytes']
 def validate(self,source):
  if self._seal is not _SEAL or self._sources.get(source.get('sourceKey'))!=canonical(source):fail('fetch-extension-inactive')
  return source


def admit_authority(selection, *, expected_selection_sha256, baseline_manifest_raw, baseline_selection_raw, root=ROOT):
 """Called only with the enclosing launcher's independently pinned selection.

 The candidate artifact's own inactive markers cannot supply an active selection.
 This verifies metadata only; current owner/claim/custody admission is mandatory
 in the saver before I/O. No old002 exception extends to these keys.
 """
 if selection is None or expected_selection_sha256 is None:fail('fetch-extension-inactive')
 require(sha(canonical(selection))==expected_selection_sha256
   and selection['schemaVersion']=='offmenu-reviewed-fetch-transfer-selection/1'
   and selection['status']=='parent-reviewed-owner-manual'
   and selection['executionStage']=='fetch' and selection['candidateSHA256']==CANDIDATE_SHA
   and sha(baseline_manifest_raw)==BASE_MANIFEST_SHA and sha(baseline_selection_raw)==BASE_SELECTION_SHA
   and selection['minimumCacheSeconds']>=30*86400 and selection['maximumRetries']==0
   and selection['maximumRedirects']==0 and selection['maximumHEADs']==0
   and selection['old002AuthorityExtended'] is False
   and selection.get('custodyGate')=='fresh-exact-metadata-plus-live-full-request-claims')
 dependencies=(Path(root)/'docs/collection-selections/reviewed-fetch-metadata-dependencies.json').read_bytes()
 require(sha(dependencies)==DEPENDENCY_SHA and selection['requiredMetadataTargetIds']==strict_json(dependencies)['requiredMetadataTargetIdsBySourceKey'])
 bundle=candidate_bundle(root);all_sources=prepared_sources(root);ids=selection['selectedAssetIds']
 require(type(ids)is list and len(ids)==len(set(ids)) and bool(ids))
 sources=[s for s in all_sources if s['mediaIntake']['assetId']in ids]
 require(len(sources)==len(ids) and selection['sourceContractSHA256s']==[sha(canonical(s))for s in sources]
   and selection['maximumRequests']==len(sources)
   and selection['maximumBodyBytes']==sum(s['hardTransferBytes']for s in sources)
   and selection['maximumHeaderBytes']==65536*len(sources)
   and selection['wholeOperationSeconds']==1200 and selection['perHostWorkers']==1
   and selection['currentClaimsAndCustodyRequired'] is True
   and selection['metadataReconciliationRequired'] is True
   and set(selection['requiredMetadataTargetIds'])=={s['sourceKey']for s in sources}
   and all(type(v)is list and len(v)==len(set(v)) and all(type(x)is str for x in v)for v in selection['requiredMetadataTargetIds'].values()))
 baseline=strict_json(baseline_manifest_raw);assets={a['assetId']:a for a in baseline['assets']}
 old=strict_json(baseline_selection_raw)
 require(bundle['existingSourceFingerprints']==[{'sourceKey':s['sourceKey'],'sha256':sha(canonical(s))}for s in old['sources']])
 for source in sources:
  asset=assets[source['mediaIntake']['assetId']]
  require(sha(canonical(asset))==source['mediaIntake']['originalAssetSHA256']
   and asset.get('retainedOriginal') is None and asset.get('sourceStageHolds',[])==[])
 return FetchAuthority(_SEAL,sources,selection)


def _matches(prefix,tail,rule):
 kind=rule['observation']
 if kind=='pdf-prefix-and-eof':return prefix.startswith(b'%PDF-')and bool(re.search(rb'%%EOF[\x00\x09\x0a\x0c\x0d\x20]*$',tail))
 if kind=='ole-container-prefix':return prefix.startswith(bytes.fromhex('d0cf11e0a1b11ae1'))
 if kind=='zip-container-prefix':return prefix.startswith(b'PK\x03\x04')
 if kind=='json-prefix':return (prefix[3:] if prefix.startswith(b'\xef\xbb\xbf') else prefix).lstrip(b' \t\r\n')[:1]in (b'{',b'[')
 if kind=='rss-root-prefix':
  value=(prefix[3:] if prefix.startswith(b'\xef\xbb\xbf') else prefix).lstrip(b' \t\r\n')
  if value.startswith(b'<?xml'):
   end=value.find(b'?>')
   if end<0:return False
   value=value[end+2:].lstrip()
  return re.match(rb'<rss(?:\s|>)',value)is not None
 return False


def validate_original(result,source,deadline,adapter):
 """One strict expected-extent scan; prefix observation is not parsing."""
 path=Path(result.path);maximum=source['hardTransferBytes'];fd=open_fixed(path)
 count=0;digest=hashlib.sha256();prefix=b'';tail=b''
 try:
  before=os.fstat(fd)
  require(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and before.st_uid==os.getuid()
      and before.st_mode&0o077==0 and type(result.bytes)is int and 0<result.bytes==before.st_size<=maximum)
  while count<result.bytes:
   adapter.deadline_check(deadline);block=os.read(fd,min(65536,result.bytes-count))
   if not block:fail('fetch-extension-identity-changed')
   count+=len(block);digest.update(block)
   if len(prefix)<65536:prefix+=block[:65536-len(prefix)]
   tail=(tail+block)[-4096:]
  adapter.deadline_check(deadline);after=os.fstat(fd)
 finally:os.close(fd)
 check=open_fixed(path)
 try:current=os.fstat(check)
 finally:os.close(check)
 same=lambda v:(v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns,v.st_ctime_ns,v.st_uid,v.st_mode,v.st_nlink)
 if same(before)!=same(after)or same(after)!=same(current)or digest.hexdigest()!=result.sha256:fail('fetch-extension-identity-changed')
 if not _matches(prefix,tail,source['mediaIntake']['integrity']):fail('fetch-extension-media-mismatch')
 return {'bytes':count,'sha256':result.sha256,'publisherMD5Verified':False,'headerVerified':True,
  'originalAcquiredAt':result.provenance['originalAcquiredAt'],'mediaObservation':source['mediaIntake']['integrity']['observation'],
  'fullStructuralValidation':False,'extractionPerformed':False,'localValidationBytesRead':count}


def run_selected(source, *, authority=None, owner_runtime=None, adapter=None, **kwargs):
 if type(authority)is not FetchAuthority:fail('fetch-extension-inactive')
 authority.validate(source)
 # Every new key requires the separate owner's explicit extension admission.
 if owner_runtime is None or getattr(owner_runtime,'fetchAuthoritySHA256',None)!=authority.selectionSHA256:fail('fetch-extension-inactive')
 path=ROOT/'scripts/save-private-media-original.py'
 require(sha(path.read_bytes())==SAVER_SHA)
 spec=importlib.util.spec_from_file_location('offmenu_reviewed_fetch_private_saver',path)
 saver=importlib.util.module_from_spec(spec);spec.loader.exec_module(saver)
 # Isolated module instance: legacy five-source validation stays byte-identical.
 saver.intake=SimpleNamespace(validate_source=authority.validate,
  original_filename=legacy_intake.original_filename,fetch_response=legacy_intake.fetch_response,
  checked_headers=legacy_intake.checked_headers,validate_original=validate_original,ERROR_CODES=ERROR_CODES)
 saver.ERRORS=saver.legacy.ERRORS|ERROR_CODES
 return saver.run_selected(source,owner_runtime=owner_runtime,adapter=adapter,**kwargs)


class OwnerExtension:
 """Same-pass source gate; no absence inference and no historical exception.

 Each source independently needs exact relevant metadata outcomes, no unresolved
 matching custody, a fresh hold check, and live native/local/historical full
 request claims. A failed source never grants or blocks another source's scope.
 """
 def __init__(self,base,authority,*,metadata_report,metadata_validator,current_holds,adapter):
  if type(authority)is not FetchAuthority or not callable(metadata_validator)or not callable(current_holds):fail('fetch-extension-inactive')
  metadata_validator(metadata_report)
  self.base=base;self.authority=authority;self.adapter=adapter
  self.metadata=deepcopy(metadata_report);self.current_holds=current_holds
  self.uid=base.uid;self.root=base.root;self.fetchAuthoritySHA256=authority.selectionSHA256
  if self.uid==0 or self.uid!=os.getuid():fail('fetch-extension-inactive')
 def provenance(self):
  return {**self.base.provenance(),'additionalFetchSelectionSHA256':self.authority.selectionSHA256}
 def reuse_provenance(self,source,existing):
  self.authority.validate(source)
  if existing.get('ownerHandover')!=self.provenance():fail('fetch-extension-custody-unresolved')
  return self.provenance()
 def metadata_gate(self,source,deadline):
  a=self.adapter;a.deadline_check(deadline);self.authority.validate(source)
  targets=self.authority.requiredMetadataTargets[source['sourceKey']]
  # An empty map is an unresolved dependency, never evidence of no custody.
  if not targets or self.metadata.get('status')!='metadata-proposals-only':fail('fetch-extension-custody-unresolved')
  rows={r['targetId']:r for r in self.metadata['outcomes']}
  if any(t not in rows or rows[t]['code']!='reconciled' or rows[t]['excludedObjects'] for t in targets):fail('fetch-extension-custody-unresolved')
  key=source['sourceKey'];asset=source['mediaIntake']['assetId'];url=sha(source['url'].encode())
  for row in self.metadata['rows']:
   ids=row['identifiers']
   if (ids.get('sourceKey')==key or ids.get('assetId')==asset or ids.get('descriptorId')==asset
       or any(v.get('exactURLSHA256')==url for v in row['urls'].values())):fail('fetch-extension-custody-unresolved')
  holds=self.current_holds(source)
  if type(holds)is not dict or holds!={'sourceContractSHA256':sha(canonical(source)),'read':True,'copy':True,'currentSourceHolds':[]}:fail('fetch-extension-custody-unresolved')
  a.deadline_check(deadline)
 def admit(self,work,source,intent,old_claim,prior,deadline):
  self.metadata_gate(source,deadline);a=self.adapter
  if prior is not None:fail('fetch-extension-custody-unresolved')
  roots=(self.base.native,work,self.base.runner_work,self.base.runner_cache)
  if any(self.base.access_state(p)!='readable'for p in roots):fail('fetch-extension-custody-unresolved')
  for url in [source['url'],*source.get('aliases',[])]:
   path=a.safe_path(self.base.native/(sha(url.encode())+'.json'))
   try:path.lstat()
   except FileNotFoundError:continue
   fail('fetch-extension-custody-unresolved')
  for directory in (work,self.base.runner_work):
   request=directory/'source-cache/requests'/sha(canonical(a.source_spec(source).identity()))
   claim=directory/'intents'/(sha(source['url'].encode())+'.json')
   paths=[claim,directory/('reservation-'+sha(source['url'].encode())+'.bin')]
   paths.extend(request/name for name in ('current.json','recovery.json','body.partial'))
   if directory!=work:paths.append(directory/'private-originals'/sha(canonical(source)))
   for path in paths:
    try:a.safe_path(path).lstat()
    except FileNotFoundError:continue
    fail('fetch-extension-custody-unresolved')
  coverage=a.inspect_runner_metadata(roots,source,intent,old_claim,deadline)
  self.metadata_gate(source,deadline)
  return coverage
