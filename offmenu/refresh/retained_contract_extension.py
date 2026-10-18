"""Pure source-bound retained-input composition, inactive until parent adoption.

This is a generic merge seam, not a grant of source rights or a selection of the
unresolved retained inventory. No source files, stat calls, or network are used.
"""
from copy import deepcopy
from pathlib import Path
from .core import RefreshError,canonical,sha,strict_json
from . import media_preparation as media
from . import retained_integrity_verification as verification

SCHEMA='offmenu-retained-contract-extension/1'
ERROR='retained-contract-extension-invalid'

def fail():raise RefreshError(ERROR)

def read_pin(root,pin):
 if not isinstance(pin,dict) or not {'path','sha256'}<=set(pin) or not set(pin)<={'path','sha256','bytes','canonicalSHA256'}:fail()
 name=pin['path'];path=Path(name)
 if not isinstance(name,str) or not name.startswith('docs/') or path.is_absolute() or '..' in path.parts:fail()
 raw=(Path(root)/path).read_bytes()
 if len(raw)>32*1024**2 or sha(raw)!=pin['sha256'] or ('bytes' in pin and len(raw)!=pin['bytes']):fail()
 value=strict_json(raw)
 if 'canonicalSHA256' in pin and sha(canonical(value))!=pin['canonicalSHA256']:fail()
 return value

def load_extension(root,pin):
 extension=read_pin(root,pin)
 if extension.get('schemaVersion')!=SCHEMA or extension.get('status')!='prepared-for-review-not-active':fail()
 manifest=read_pin(root,extension['baseManifestPin'])
 for evidence in (extension['evidencePins'].values() if isinstance(extension['evidencePins'],dict) else extension['evidencePins']):read_pin(root,evidence)
 validate_records(manifest,extension)
 return extension

def validate_records(manifest,extension):
 if not isinstance(extension,dict) or extension.get('schemaVersion')!=SCHEMA or extension.get('status')!='prepared-for-review-not-active':fail()
 rows=extension.get('records');assets={r['assetId']:r for r in manifest['assets']};seen=set()
 if not isinstance(rows,list) or not 1<=len(rows)<=10000:fail()
 required={'assetId','originalAssetSHA256','retainedOriginal','preparationContract','sourceStageHolds','downstreamHolds','verificationMode','permissionBasis','eligibility','missingFields','evidenceRefs'}
 for row in rows:
  if not isinstance(row,dict) or not required<=set(row):fail()
  key=row['assetId']
  if key not in assets or key in seen:fail()
  seen.add(key);asset=assets[key]
  if row['originalAssetSHA256']!=sha(canonical(asset)) or row['retainedOriginal']!=asset.get('retainedOriginal'):fail()
  for field in ('sourceStageHolds','downstreamHolds'):
   if row[field]!=asset.get(field,[]):fail()
  identity=row['retainedOriginal'];verify=row.get('verificationContract')
  if verify is not None:
   verification.validate_contract(verify)
   if not isinstance(identity,dict) or verify['assetId']!=key or verify['expectedSHA256']!=identity.get('sha256') or verify['expectedBytes']!=identity.get('bytes'):fail()
   restrictions={h for h in asset.get('sourceStageHolds',[])+asset.get('holds',[]) if isinstance(h,str)}&{'all','read','copy','extract'}
   if not restrictions<=set(verify['holds']):fail()
  contract=row['preparationContract']
  if contract is None:continue
  media.validate_contract(contract);identity=row['retainedOriginal']
  if not isinstance(identity,dict) or contract['assetId']!=key or contract['expectedSHA256']!=identity.get('sha256') or contract['expectedBytes']!=identity.get('bytes'):fail()
  if asset.get('preparationContract') is not None and contract!=asset['preparationContract']:fail()
  # Do not permit the extension to strip a source-stage denial from a contract.
  restrictions={h for h in asset.get('sourceStageHolds',[])+asset.get('holds',[]) if isinstance(h,str)}&{'all','read','copy','extract'}
  if not restrictions<=set(contract['holds']):fail()
 return extension

def compose_retained_contracts(manifest,extension,*,selected_asset_ids=()):
 """Explicit reviewed subset only. Empty selection does not read or admit inputs."""
 validate_records(manifest,extension)
 if not isinstance(selected_asset_ids,(tuple,list)) or len(selected_asset_ids)!=len(set(selected_asset_ids)):fail()
 rows={r['assetId']:r for r in extension['records']}
 if any(key not in rows for key in selected_asset_ids):fail()
 result=deepcopy(manifest);assets={r['assetId']:r for r in result['assets']}
 for key in selected_asset_ids:
  row=rows[key];contract=row['preparationContract'];asset=assets[key]
  if row.get('effectiveReadHolds') or contract is None or asset['disposition']=='held' or contract['permissions']['read'] is not True or 'all' in contract['holds'] or 'read' in contract['holds']:fail()
  # Unknown copy/extract permissions remain false/null; no OR across members.
  asset['preparationContract']=deepcopy(contract)
 result['retainedContractExtension']={'schemaVersion':SCHEMA,'status':'prepared-for-review-not-active','extensionSHA256':sha(canonical(extension)),
  'selectedAssetIds':list(selected_asset_ids),'inventoryCount':len(rows),'selectedCount':len(selected_asset_ids),'additionalAcquisitionRequests':0,'sourcePermissionsInferred':False}
 return result


def select_retained_verification(manifest,extension,*,selected_asset_ids=()):
 """Build review-only jobs; never falls back to parser preparation for large files."""
 validate_records(manifest,extension)
 if not isinstance(selected_asset_ids,(tuple,list)) or len(selected_asset_ids)!=len(set(selected_asset_ids)):fail()
 rows={r['assetId']:r for r in extension['records']};assets={r['assetId']:r for r in manifest['assets']};jobs=[]
 for key in selected_asset_ids:
  if key not in rows:fail()
  row=rows[key];contract=row.get('verificationContract')
  if row.get('effectiveReadHolds') or contract is None or assets[key]['disposition']=='held' or 'read' in contract['holds'] or 'all' in contract['holds']:fail()
  if Path(row['retainedOriginal']['path']).name.lower().endswith(('.part','.partial')):fail()
  jobs.append({'assetId':key,'originalAssetSHA256':row['originalAssetSHA256'],'original':deepcopy(row['retainedOriginal']),'verificationContract':deepcopy(contract),'status':'prepared-for-review-not-active'})
 return jobs
