#!/usr/bin/env python3
"""One exact Swiss v7.1 private original through the existing reviewed collector."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import re
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixed_original_adapter',ROOT/'scripts/acquire-fixed-zenodo.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
SCHEMA='offmenu-fixed-swiss-original/1'
PIN=('docs/collection-selections/swiss-v71-selection.json','14f516e7c7a8b2eca7645bd13b5608b7d332217412dd97920da1e0c45fb0d042')
SOURCE_KEY='ch.fsvo.food-composition.v7_1.xlsx'
URL='https://naehrwertdaten.ch/wp-content/uploads/2026/07/Swiss_food_composition_database.xlsx'
EXPECTED_BYTES=1014249
MAX_SECONDS=120


def exact_original_evidence(value):
    """Positive original identity only; a historical landing-page citation is not custody."""
    if isinstance(value,dict):
        if any(value.get(k)==URL for k in ('sourceUrl','sourceURL','source_url','url','canonicalUrl')): return True
        return any(exact_original_evidence(v) for v in value.values())
    if isinstance(value,list): return any(exact_original_evidence(v) for v in value)
    return False


def load_selection():
    prep=a.preparation_module(); selected=a.strict_json(prep.pinned_bytes(ROOT,PIN))
    if (selected.get('schemaVersion')!='offmenu-fixed-source-contract/1' or selected.get('sourceKey')!=SOURCE_KEY
            or selected.get('url')!=URL or selected.get('expectedBytes')!=EXPECTED_BYTES
            or selected.get('hardTransferBytes')!=EXPECTED_BYTES or selected.get('wholeOperationSeconds')!=MAX_SECONDS
            or selected.get('checksums')!={} or selected.get('validation')!={'kind':'xlsx'}
            or selected.get('cacheSeconds')!=a.TTL or selected.get('planningGuardBytes')!=a.GUARD
            or selected.get('floorAlreadyIncluded') is not True): raise a.RefreshError('fixed-selection-invalid')
    for pin in selected['evidence']: prep.pinned_bytes(ROOT,(pin['path'],pin['sha256']))
    snapshot=prep.imported_snapshot(ROOT); adopted=a.strict_json(prep.pinned_bytes(ROOT,prep.SUMMARY_PIN))
    if exact_original_evidence(snapshot) or exact_original_evidence(adopted): raise a.RefreshError('known-exact-source-observed')
    a.source_spec(selected).validate()
    return selected


def summary(detail=None,error=None):
    validation=(detail or {}).get('validation') or {}
    report={'schemaVersion':SCHEMA,'sourceKey':SOURCE_KEY,'selectionSHA256':PIN[1],
        'status':'blocked' if detail is None else detail['status'],
        'errorCode':error if detail is None else detail['errorCode'],
        'detailSHA256':None if detail is None else a.sha(a.canonical(detail)),
        'detailPersisted':bool(detail is not None and detail['receiptPersistence']=='written'),
        'responseMetadata':None if detail is None else detail.get('responseMetadata'),
        'networkRequests':0 if detail is None else detail['network']['requests'],
        'networkBytesRead':0 if detail is None else detail['network']['bodyBytesRead'],
        'verifiedBytes':validation.get('bytes',0),'originalSHA256':validation.get('sha256'),
        'originalAcquiredAt':validation.get('originalAcquiredAt'),
        'cacheStatus':None if detail is None else detail['cacheStatus'],
        'xlsxContainerAndCRCVerified':bool(validation),'publisherCryptographicChecksumAvailable':False,
        'minimumCacheSeconds':a.TTL,'wholeOperationSeconds':MAX_SECONDS,
        'historicalDiscoveryCitationWasNotCustody':True,**a.SAFETY}
    return sanitize_report(report)


def sanitize_report(value):
    keys={'schemaVersion','sourceKey','selectionSHA256','status','errorCode','detailSHA256','detailPersisted',
          'responseMetadata','networkRequests','networkBytesRead','verifiedBytes','originalSHA256','originalAcquiredAt',
          'cacheStatus','xlsxContainerAndCRCVerified','publisherCryptographicChecksumAvailable','minimumCacheSeconds',
          'wholeOperationSeconds','historicalDiscoveryCitationWasNotCustody'}|set(a.SAFETY)
    if (not isinstance(value,dict) or set(value)!=keys or value['schemaVersion']!=SCHEMA
            or value['sourceKey']!=SOURCE_KEY or value['selectionSHA256']!=PIN[1]
            or value['status'] not in {'blocked','failed','verified-private-original'}
            or value['errorCode'] not in a.ERRORS|{None}): raise ValueError('invalid-swiss-summary')
    success=value['status']=='verified-private-original'
    if success!=(value['errorCode'] is None) or value['xlsxContainerAndCRCVerified'] is not success:
        raise ValueError('invalid-swiss-summary')
    for key,limit in [('networkRequests',1),('networkBytesRead',EXPECTED_BYTES),('verifiedBytes',EXPECTED_BYTES)]:
        if type(value[key]) is not int or not 0<=value[key]<=limit: raise ValueError('invalid-swiss-summary')
    for key in ('originalSHA256','detailSHA256'):
        if value[key] is not None and (not isinstance(value[key],str) or not re.fullmatch('[a-f0-9]{64}',value[key])):
            raise ValueError('invalid-swiss-summary')
    if (type(value['detailPersisted']) is not bool
            or (success and (value['verifiedBytes']!=EXPECTED_BYTES or not value['originalSHA256'] or not value['detailPersisted'] or not value['detailSHA256']
                             or not isinstance(value['originalAcquiredAt'],str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+(?:Z|\+00:00)',value['originalAcquiredAt'])))
            or (not success and (value['verifiedBytes']!=0 or value['originalSHA256'] is not None or value['originalAcquiredAt'] is not None))):
        raise ValueError('invalid-swiss-summary')
    if value['cacheStatus'] not in {None,'downloaded-200','reused-fresh'}: raise ValueError('invalid-swiss-summary')
    a.validate_response_metadata(value['responseMetadata'])
    for key,expected in {**a.SAFETY,'publisherCryptographicChecksumAvailable':False,'historicalDiscoveryCitationWasNotCustody':True}.items():
        if value[key] is not expected: raise ValueError('invalid-swiss-summary')
    if value['minimumCacheSeconds']!=a.TTL or value['wholeOperationSeconds']!=MAX_SECONDS: raise ValueError('invalid-swiss-summary')
    return dict(value)


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if args: raise a.RefreshError('unexpected-arguments')
        selected=load_selection()
        report=summary(a.run_selected(selected,deadline=time.monotonic()+MAX_SECONDS))
    except (a.RefreshError,OSError,ValueError,TypeError,KeyError) as error:
        code=str(error) if isinstance(error,a.RefreshError) and str(error) in a.ERRORS else 'fixed-evidence-invalid'
        report=summary(error=code)
    print(a.canonical(report).decode(),end='')
    return 0 if report['status']=='verified-private-original' else 2


if __name__=='__main__':raise SystemExit(main())
