#!/usr/bin/env python3
"""A fixed reviewed list through the existing private-original adapter and collector."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixed_original_adapter',ROOT/'scripts/acquire-fixed-zenodo.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
SCHEMA='offmenu-fixed-source-batch/1'
BATCH_PIN=('docs/collection-selections/recipe-originals-batch-selection.json','2b12090957ddc6cd9ab4393a1d1ea731132836fa35532ee0f6af59bbda84bc02')
MAX_SOURCES=8
MAX_SECONDS=1200
MAX_TOTAL_BYTES=256*1024**2
ERRORS=a.ERRORS | {'fixed-batch-unconfigured','fixed-batch-invalid','batch-deadline-exhausted','batch-byte-limit','batch-request-limit'}


def bounded_text(value, maximum=2048):
    return isinstance(value,str) and 0<len(value)<=maximum and not any(ord(c)<32 or ord(c)==127 for c in value)


def validate_selection(value):
    keys={'schemaVersion','batchId','sources','maximumRequests','maximumTransferBytes','wholeOperationSeconds',
          'minimumCacheSeconds','planningGuardBytes','floorAlreadyIncluded','evidence','coordinatorIntent'}
    if not isinstance(value,dict) or set(value)!=keys or value['schemaVersion']!='offmenu-fixed-source-batch-selection/1':
        raise a.RefreshError('fixed-batch-invalid')
    if not bounded_text(value['batchId'],128) or not isinstance(value['sources'],list) or not 1<=len(value['sources'])<=MAX_SOURCES:
        raise a.RefreshError('fixed-batch-invalid')
    for key,minimum,maximum in [('maximumRequests',1,len(value['sources'])),('maximumTransferBytes',1,MAX_TOTAL_BYTES),('wholeOperationSeconds',1,MAX_SECONDS)]:
        if type(value[key]) is not int or not minimum<=value[key]<=maximum: raise a.RefreshError('fixed-batch-invalid')
    if (value['minimumCacheSeconds']!=a.TTL or value['planningGuardBytes']!=a.GUARD or value['floorAlreadyIncluded'] is not True
            or value['coordinatorIntent']!={'owner':0,'singleWriter':True,'nativeClaimsExhaustive':False,'missingMatchMeansUnowned':False}):
        raise a.RefreshError('fixed-batch-invalid')
    if not isinstance(value['evidence'],list) or not 1<=len(value['evidence'])<=16: raise a.RefreshError('fixed-batch-invalid')
    for pin in value['evidence']:
        if (not isinstance(pin,dict) or set(pin)!={'path','sha256'} or not bounded_text(pin['path'])
                or not pin['path'].startswith('docs/collection-selections/') or '..' in Path(pin['path']).parts
                or not re.fullmatch('[a-f0-9]{64}',pin['sha256'])): raise a.RefreshError('fixed-batch-invalid')
    source_keys=set(); identities=set()
    entry_keys={'schemaVersion','sourceKey','url','aliases','release','rightsReference','privateCustodyApproved',
                'sourceAcquisitionHeld','downstreamHolds','expectedBytes','checksums','hardTransferBytes',
                'wholeOperationSeconds','validation','qualificationReference','queryKeys','expectedResponse','historicalPreparationExceptions'}
    for source in value['sources']:
        if not isinstance(source,dict) or set(source)!=entry_keys or source['schemaVersion']!='offmenu-fixed-source-contract/1':
            raise a.RefreshError('fixed-batch-invalid')
        if source['privateCustodyApproved'] is not True or source['sourceAcquisitionHeld'] is not False:
            raise a.RefreshError('fixed-batch-invalid')
        if (not bounded_text(source['sourceKey'],128) or source['sourceKey'] in source_keys
                or not bounded_text(source['url']) or source['url'] in identities
                or urlsplit(source['url']).hostname in {'zenodo.org','www.zenodo.org'}): raise a.RefreshError('fixed-batch-invalid')
        source_keys.add(source['sourceKey']); identities.add(source['url'])
        if not isinstance(source['aliases'],list) or len(source['aliases'])>32 or any(not bounded_text(v) for v in source['aliases']):
            raise a.RefreshError('fixed-batch-invalid')
        for key in ('release','rightsReference','qualificationReference'):
            if not bounded_text(source[key]): raise a.RefreshError('fixed-batch-invalid')
        if not isinstance(source['downstreamHolds'],list) or len(source['downstreamHolds'])>16 or any(not bounded_text(v,128) for v in source['downstreamHolds']):
            raise a.RefreshError('fixed-batch-invalid')
        for key,maximum in [('hardTransferBytes',value['maximumTransferBytes']),('wholeOperationSeconds',value['wholeOperationSeconds'])]:
            if type(source[key]) is not int or not 1<=source[key]<=maximum: raise a.RefreshError('fixed-batch-invalid')
        expected=source['expectedBytes']
        if expected is not None and (type(expected) is not int or not 1<=expected<=source['hardTransferBytes']): raise a.RefreshError('fixed-batch-invalid')
        checks=source['checksums']
        if not isinstance(checks,dict) or not set(checks)<={'md5','sha256'}: raise a.RefreshError('fixed-batch-invalid')
        for kind,digest in checks.items():
            if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{'+str(32 if kind=='md5' else 64)+'}',digest): raise a.RefreshError('fixed-batch-invalid')
        if source['validation']!={'kind':'pdf-original'}: raise a.RefreshError('fixed-batch-invalid')
        headers=source['expectedResponse']
        if (not isinstance(headers,dict) or not {'content-type'}<=set(headers)
                or not set(headers)<={'content-type','content-length','etag','last-modified','content-disposition'}
                or any(not bounded_text(v,256) for v in headers.values())
                or headers['content-type'] not in {'application/pdf','application/octet-stream'}
                or (expected is not None and headers.get('content-length')!=str(expected))
                or (expected is None and 'content-length' in headers)): raise a.RefreshError('fixed-batch-invalid')
        exceptions=source['historicalPreparationExceptions']
        if not isinstance(exceptions,list) or len(exceptions)>4: raise a.RefreshError('fixed-batch-invalid')
        for exception in exceptions:
            if (not isinstance(exception,dict) or set(exception)!={'metadataPath','metadataSHA256','sourceUrl'}
                    or not bounded_text(exception['metadataPath']) or exception['sourceUrl'] not in [source['url'],*source['aliases']]
                    or not re.fullmatch('[a-f0-9]{64}',exception['metadataSHA256'])): raise a.RefreshError('fixed-batch-invalid')
        a.source_spec(source).validate()
    if sum(s['hardTransferBytes'] for s in value['sources'])>value['maximumTransferBytes']:
        raise a.RefreshError('fixed-batch-invalid')
    # Same asset through aliases or publisher hash is one source, not another GET.
    for index,source in enumerate(value['sources']):
        for other in value['sources'][:index]:
            if a.exact_source_match(other,source) or a.exact_source_match(source,other): raise a.RefreshError('fixed-batch-invalid')
    return value


def selection_config():
    if BATCH_PIN is None: raise a.RefreshError('fixed-batch-unconfigured')
    return validate_selection(a.strict_json(a.preparation_module().pinned_bytes(ROOT,BATCH_PIN)))


def source_conflicts(selected,snapshot,adopted):
    """Preserve positive observations; skip only pinned bare historical preparation URLs."""
    conflicts=[]
    for source in selected['sources']:
        if a.exact_source_match(adopted,source):
            conflicts.append({'sourceKey':source['sourceKey']});continue
        claim_names={a.sha(url.encode())+'.json' for url in [source['url'],*source['aliases']] if url.startswith('https://')}
        observations=[(True,o) for o in snapshot.get('metadata',[])]+[(False,o) for o in snapshot.get('discoveredMetadata',[])]
        for is_pinned_metadata,observation in observations:
            observed_path=Path(observation.get('path',''))
            if (observation.get('category')=='claims'
                    and str(observed_path.parent)=='/home/user/src/offmenu-data/originals/country-followthrough-20261015/claims'
                    and observed_path.name in claim_names):
                conflicts.append({'sourceKey':source['sourceKey']})
            for record in (observation.get('reconciliation') or {}).get('records',[]):
                if not a.exact_source_match(record,source):continue
                historical=is_pinned_metadata and any(
                    observation.get('path')==e['metadataPath']
                    and observation.get('metadataSHA256')==e['metadataSHA256']
                    and observation.get('pinStatus')=='match'
                    and record=={'sourceUrl':e['sourceUrl']}
                    for e in source['historicalPreparationExceptions'])
                if not historical:
                    conflicts.append({'sourceKey':source['sourceKey']})
    return conflicts


def item_report(source,detail=None,error=None,network=None):
    network=network or {'requests':0,'bodyBytesRead':0}
    validation=(detail or {}).get('validation') or {}
    return {'sourceKey':source['sourceKey'],'sourceContractSHA256':a.sha(a.canonical(source)),
        'status':('failed' if network['requests'] else 'blocked') if detail is None else detail['status'],'errorCode':error if detail is None else detail['errorCode'],
        'networkRequests':network['requests'] if detail is None else detail['network']['requests'],
        'networkBytesRead':network['bodyBytesRead'] if detail is None else detail['network']['bodyBytesRead'],
        'responseMetadata':None if detail is None else detail.get('responseMetadata'),
        'cacheStatus':None if detail is None else detail['cacheStatus'],
        'verifiedBytes':validation.get('bytes',0),'originalSHA256':validation.get('sha256'),
        'originalAcquiredAt':validation.get('originalAcquiredAt'),
        'detailSHA256':None if detail is None else a.sha(a.canonical(detail)),
        'detailPersisted':bool(detail is not None and detail['receiptPersistence']=='written'),
        'downstreamHolds':source['downstreamHolds']}


def run_batch(selected, *, engine=a.CachedAcquirer, transport=None, adverse_evidence=()):
    selected=validate_selection(selected)
    meter={'requests':0,'bodyBytesRead':0,'maximumRequests':selected['maximumRequests'],'maximumBytes':selected['maximumTransferBytes']}
    deadline=time.monotonic()+selected['wholeOperationSeconds']; items=[]
    for source in selected['sources']:
        detail=None; error=None; before=dict(meter)
        try:
            if time.monotonic()>=deadline: raise a.RefreshError('batch-deadline-exhausted')
            if meter['bodyBytesRead']>=meter['maximumBytes']: raise a.RefreshError('batch-byte-limit')
            if any(a.exact_source_match(evidence,source) for evidence in adverse_evidence): raise a.RefreshError('known-exact-source-observed')
            detail=a.run_selected(source,engine=engine,transport=transport,deadline=deadline,batch_meter=meter)
        except Exception as failure:
            error=str(failure) if isinstance(failure,a.RefreshError) and str(failure) in ERRORS else 'collector-rejected'
        consumed={key:meter[key]-before[key] for key in ('requests','bodyBytesRead')}
        items.append(item_report(source,detail,error,consumed))
    return {'schemaVersion':SCHEMA,'batchId':selected['batchId'],'selectionSHA256':a.sha(a.canonical(selected)),
        'status':'complete' if all(i['status']=='verified-private-original' for i in items) else 'complete-with-errors',
        'errorCode':None,'networkRequests':meter['requests'],'networkBytesRead':meter['bodyBytesRead'],'items':items,**a.SAFETY}


def blocked_report(code):
    return {'schemaVersion':SCHEMA,'batchId':None,'selectionSHA256':None,'status':'blocked','errorCode':code,
            'networkRequests':0,'networkBytesRead':0,'items':[],**a.SAFETY}


def sanitize_report(report):
    if not isinstance(report,dict) or set(report)!=set(blocked_report('fixed-batch-invalid')): raise ValueError('invalid-batch-summary')
    if any(report[k] is not v for k,v in a.SAFETY.items()): raise ValueError('invalid-batch-summary')
    if report['status']=='blocked':
        if report!=blocked_report(report['errorCode']) or report['errorCode'] not in ERRORS: raise ValueError('invalid-batch-summary')
        return dict(report)
    selected=selection_config()
    if (report['batchId']!=selected['batchId'] or report['selectionSHA256']!=a.sha(a.canonical(selected))
            or report['errorCode'] is not None or not isinstance(report['items'],list)
            or len(report['items'])!=len(selected['sources'])): raise ValueError('invalid-batch-summary')
    totals={'networkRequests':0,'networkBytesRead':0}
    for item,source in zip(report['items'],selected['sources']):
        if not isinstance(item,dict) or set(item)!=set(item_report(source,error='collector-rejected')): raise ValueError('invalid-batch-summary')
        for key,expected in [('sourceKey',source['sourceKey']),('sourceContractSHA256',a.sha(a.canonical(source))),('downstreamHolds',source['downstreamHolds'])]:
            if item[key]!=expected: raise ValueError('invalid-batch-summary')
        success=item['status']=='verified-private-original'
        if item['status'] not in {'blocked','failed','verified-private-original'} or item['errorCode'] not in ERRORS|{None} or success!=(item['errorCode'] is None): raise ValueError('invalid-batch-summary')
        for key,limit in [('networkRequests',1),('networkBytesRead',source['hardTransferBytes']),('verifiedBytes',source['hardTransferBytes'])]:
            if type(item[key]) is not int or not 0<=item[key]<=limit: raise ValueError('invalid-batch-summary')
        a.validate_response_metadata(item['responseMetadata'])
        if type(item['detailPersisted']) is not bool: raise ValueError('invalid-batch-summary')
        for key in ('originalSHA256','detailSHA256'):
            if item[key] is not None and (not isinstance(item[key],str) or not re.fullmatch('[a-f0-9]{64}',item[key])): raise ValueError('invalid-batch-summary')
        if (success and (not item['verifiedBytes'] or not item['originalSHA256'] or not item['detailPersisted'] or not item['detailSHA256']
                         or not bounded_text(item['originalAcquiredAt'],64)
                         or (source['expectedBytes'] is not None and item['verifiedBytes']!=source['expectedBytes']))
                or (not success and (item['verifiedBytes']!=0 or item['originalSHA256'] is not None or item['originalAcquiredAt'] is not None))): raise ValueError('invalid-batch-summary')
        if item['cacheStatus'] not in {None,'downloaded-200','reused-fresh'}: raise ValueError('invalid-batch-summary')
        for key in totals: totals[key]+=item[key]
    for key,limit in [('networkRequests',selected['maximumRequests']),('networkBytesRead',selected['maximumTransferBytes'])]:
        if type(report[key]) is not int or report[key]!=totals[key] or not 0<=report[key]<=limit: raise ValueError('invalid-batch-summary')
    expected='complete' if all(i['status']=='verified-private-original' for i in report['items']) else 'complete-with-errors'
    if report['status']!=expected: raise ValueError('invalid-batch-summary')
    return dict(report)


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if args: raise a.RefreshError('unexpected-arguments')
        selected=selection_config(); prep=a.preparation_module()
        for pin in selected['evidence']: prep.pinned_bytes(ROOT,(pin['path'],pin['sha256']))
        snapshot=prep.imported_snapshot(ROOT); adopted=a.strict_json(prep.pinned_bytes(ROOT,prep.SUMMARY_PIN))
        report=run_batch(selected,adverse_evidence=source_conflicts(selected,snapshot,adopted))
        report=sanitize_report(report)
    except (a.RefreshError,OSError,ValueError,TypeError,KeyError) as error:
        code=str(error) if isinstance(error,a.RefreshError) and str(error) in ERRORS else 'fixed-batch-invalid'
        report=blocked_report(code)
    print(a.canonical(report).decode(),end='')
    return 0 if report['status']=='complete' else 2


if __name__=='__main__': raise SystemExit(main())
