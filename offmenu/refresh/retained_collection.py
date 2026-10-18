"""Pinned retained-job composition and count-only local-read accounting.

No runtime defaults activate the proposal. Original-read budgets are separate
from network transfer and bounded preparation output/scratch accounting.
"""
from copy import deepcopy
from .core import canonical,sha,RefreshError
from . import retained_contract_extension as extension
from . import retained_integrity_verification as verification
from . import known_asset_intake as intake
from . import media_preparation as media

EXTENSION_PIN={'path':'docs/collection-selections/retained-contract-extension-runtime.json','sha256':'44eeb91b9d47fd8c220810386f1bc9b391d6390f7903c314ef3e24cff0f77015'}
PLAN_PIN={'path':'docs/collection-selections/retained-verification-selection-review.json','sha256':'952b580dc6927c144892ce52badc1a1a5c8520c7aa9a23eaaa5bee3a2b01d09f'}
SCHEMA='offmenu-retained-collection-accounting/1'

def config(root):
 if EXTENSION_PIN is None or PLAN_PIN is None:raise RefreshError(extension.ERROR)
 ext=extension.load_extension(root,EXTENSION_PIN);plan=extension.read_pin(root,PLAN_PIN)
 ids=plan['proposedAssetIds'];rows={r['assetId']:r for r in ext['records']}
 if len(ids)!=988 or len(set(ids))!=988 or set(ids)!=set(ext['suggestedAssetIds']):raise RefreshError(extension.ERROR)
 media_ids=[k for k in ids if rows[k]['preparationContract'] is not None]
 stream_ids=[k for k in ids if rows[k]['preparationContract'] is None]
 structural=[k for k in media_ids if rows[k]['preparationContract']['permissions']['extract'] is True]
 if (set(media_ids)!=set(plan['proposedMediaAssetIds']) or set(stream_ids)!=set(plan['proposedStreamingAssetIds']) or set(structural)!=set(plan['proposedStructuralAssetIds'])
     or len(media_ids)!=928 or len(stream_ids)!=60 or len(structural)!=10 or plan['runtimeEnabled'] is not False or plan['selectedAssetIds']!=[]):raise RefreshError(extension.ERROR)
 payload=sum(rows[k]['retainedOriginal']['bytes'] for k in ids)
 if any(plan['budget'].get(k)!=v for k,v in {'payloadBytes':payload,'growthProbeBytes':928,'maximumOriginalReadBytes':payload+928,'maximumSeconds':1200}.items()):raise RefreshError(extension.ERROR)
 return ext,plan

def compose_for_review(base_manifest,manifest,selected,ext,plan):
 extension.validate_records(base_manifest,ext)
 extension.select_retained_verification(base_manifest,ext,selected_asset_ids=plan['proposedAssetIds'])
 admitted=extension.compose_retained_contracts(base_manifest,ext,selected_asset_ids=plan['proposedMediaAssetIds'])
 result=deepcopy(manifest);by_id={r['assetId']:r for r in admitted['assets']}
 for row in result['assets']:
  if row['assetId'] in set(plan['proposedMediaAssetIds']):row['preparationContract']=deepcopy(by_id[row['assetId']]['preparationContract'])
 result['retainedContractExtension']={'schemaVersion':extension.SCHEMA,'status':'prepared-for-review-not-active','extensionSHA256':sha(canonical(ext)),'selectedAssetIds':list(plan['proposedAssetIds']),'inventoryCount':998,'selectedCount':988,'additionalAcquisitionRequests':0,'sourcePermissionsInferred':False}
 selection=deepcopy(selected);selection['retainedVerification']={'status':'prepared-for-review-not-active','extensionSHA256':sha(canonical(ext)),'planSHA256':sha(canonical(plan))}
 return selection,result

def validate_combined(selected,manifest,root):
 ext,plan=config(root);successor=intake.successor_config(root)
 base=intake.read_pinned(root,successor['basePins']['global-original-selection.json']);baseline=intake.read_pinned(root,successor['basePins']['global-known-assets-runtime.json'])
 expected,mf=intake.compose_for_review(base,baseline,successor);expected,mf=compose_for_review(baseline,mf,expected,ext,plan)
 expected['knownIntakeSuccessor']['status']=expected['retainedVerification']['status']=mf['retainedContractExtension']['status']='parent-reviewed-owner-manual'
 if selected!=expected or manifest!=mf:raise RefreshError(extension.ERROR)
 return ext,plan,baseline

def verify_worker(contract,path,deadline,slot=None):
 if slot is None:return verification.verify_retained(contract,path,deadline)
 from . import collection_progress
 with collection_progress._worker_activity.running(slot):return verification.verify_retained(contract,path,deadline)

class ReadAccounting:
 def __init__(self,manifest,ext,plan):
  indices={r['assetId']:i for i,r in enumerate(manifest['assets'])};rows={r['assetId']:r for r in ext['records']}
  self.rows={indices[k]:rows[k] for k in plan['proposedAssetIds']};self.structural={indices[k] for k in plan['proposedStructuralAssetIds']};self.maximum=plan['budget']['maximumOriginalReadBytes'];self.attempted=set();self.completed=set();self.verified=set();self.uncertain=set();self.reserved=0
 def reserve(self,index):
  if index not in self.rows:return
  if index in self.attempted:raise RefreshError('global-local-read-budget')
  row=self.rows[index];bound=row['retainedOriginal']['bytes']+int(row['preparationContract'] is not None)
  if self.reserved+bound>self.maximum:raise RefreshError('global-local-read-budget')
  self.reserved+=bound;self.attempted.add(index)
 def finish(self,index,detail,uncertain=False):
  if index not in self.rows:return
  if index in self.attempted:
   if uncertain:self.uncertain.add(index)
   else:self.completed.add(index)
  if not uncertain and detail and (detail.get('integrityVerified') or detail.get('stages',{}).get('integrity')=='passed'):self.verified.add(index)
 def summary(self,ranges):
  return {'schemaVersion':SCHEMA,'inventoryCount':998,'selectedJobs':len(self.rows),'heldUnselected':10,'maximumOriginalReadBytes':self.maximum,'reservedOriginalReadBytes':self.reserved,'verifiedOriginalPayloadBytes':sum(self.rows[i]['retainedOriginal']['bytes'] for i in self.verified),'jobOutcomeGroups':[{'state':state,'assetIndices':sorted(indices)} for state,indices in [('completed-verified',self.verified),('completed-unverified',self.completed-self.verified),('uncertain',self.uncertain),('attempted',self.attempted-self.completed-self.uncertain)] if indices],'networkRequests':0,'completeExtentNotParse':True}

def sanitize_summary(value,manifest,ext,plan):
 account=ReadAccounting(manifest,ext,plan);expected=account.summary(lambda x:[])
 if not isinstance(value,dict) or set(value)!=set(expected) or value['schemaVersion']!=SCHEMA or value['inventoryCount']!=998 or value['selectedJobs']!=988 or value['heldUnselected']!=10 or value['maximumOriginalReadBytes']!=account.maximum or value['networkRequests']!=0 or value['completeExtentNotParse'] is not True:raise ValueError('invalid-retained-accounting')
 states={};seen=set()
 if not isinstance(value['jobOutcomeGroups'],list) or len(value['jobOutcomeGroups'])>4:raise ValueError('invalid-retained-accounting')
 for group in value['jobOutcomeGroups']:
  if not isinstance(group,dict) or set(group)!={'state','assetIndices'} or group['state'] not in {'completed-verified','completed-unverified','uncertain','attempted'} or group['state'] in states or not isinstance(group['assetIndices'],list):raise ValueError('invalid-retained-accounting')
  items=set()
  for index in group['assetIndices']:
   if type(index) is not int or index in seen or index not in account.rows:raise ValueError('invalid-retained-accounting')
   seen.add(index);items.add(index)
  if group['assetIndices']!=sorted(items):raise ValueError('invalid-retained-accounting')
  states[group['state']]=items
 attempted=seen;verified=states.get('completed-verified',set())
 reserved=sum(account.rows[i]['retainedOriginal']['bytes']+int(account.rows[i]['preparationContract'] is not None) for i in attempted)
 payload=sum(account.rows[i]['retainedOriginal']['bytes'] for i in verified)
 if type(value['reservedOriginalReadBytes']) is not int or value['reservedOriginalReadBytes']!=reserved or reserved>account.maximum or type(value['verifiedOriginalPayloadBytes']) is not int or value['verifiedOriginalPayloadBytes']!=payload:raise ValueError('invalid-retained-accounting')
 return value


def observations(summary):
 return {i:group['state'] for group in summary['jobOutcomeGroups'] for i in group['assetIndices']}
