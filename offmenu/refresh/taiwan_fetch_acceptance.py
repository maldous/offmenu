"""Fetch-only bridge for the independently reviewed exact retained-reference writer.

No transfer adapter, parser expansion, or generic PDF exception is exposed.
The enclosing source selection remains inactive until separately adopted.
"""
from datetime import datetime
import importlib.util
from pathlib import Path
import re
from .core import RefreshError, canonical, sha, strict_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'offmenu-fetch-retained-reference-acceptance/1'
WRITER_PATH = 'scripts/accept-retained-taiwan.py'
WRITER_SHA = 'c8c7a6e62832dd1d56c25d5ec0e4d1b363c71cc4a7a1ec30580cc350f9bd4b86'
MANIFEST_PATH = 'docs/collection-selections/retained-taiwan-acceptance-proposal.json'
MANIFEST_SHA = '676293ceb7d7f7169ed103f7dd494c8da58f50148572ce1f941850ba476aee5e'
REVIEW_SHA = '3b63d07f9f7125094865729cd3ba7d733146d492b2ba3c0b11c8f11b6f265b74'
HANDOFF = 'owner-local-comprehensive-20261018-002'
MAX_REPORT = 8192
SELECTION = {'schemaVersion': 'offmenu-retained-taiwan-parent-selection/1',
    'acceptanceManifestSHA256': MANIFEST_SHA, 'reviewedWriterSHA256': WRITER_SHA,
    'handoffId': HANDOFF, 'scope': 'exact-three-unchanged-retained-reference-acceptance',
    'preparationSelected': False}


def _require(value):
    if not value: raise RefreshError('retained-reference-selection-invalid')


def load_manifest(root=ROOT):
    raw = (Path(root)/MANIFEST_PATH).read_bytes()
    _require(len(raw) <= 128*1024 and sha(raw) == MANIFEST_SHA)
    return raw, strict_json(raw)


def validate_selection(selection, sources, *, root=ROOT):
    _require(selection == SELECTION and all(type(selection[k]) is type(v) for k,v in SELECTION.items()))
    raw, manifest = load_manifest(root)
    source_map = {s['sourceKey']: s for s in sources}
    _require(len(manifest['items']) == 3)
    for row in manifest['items']:
        _require(source_map.get(row['sourceKey']) == row['sourceContract'])
    return raw, manifest


def _writer(root):
    path = Path(root)/WRITER_PATH
    raw = path.read_bytes()
    _require(len(raw) < 128*1024 and sha(raw) == WRITER_SHA)
    spec = importlib.util.spec_from_file_location('offmenu_exact_taiwan_fetch_writer', path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def perform(selection, sources, *, owner_runtime, lease_fd, current_adverse_evidence,
            absolute_deadline, root=ROOT):
    """Main-thread pre-fanout call; failure never falls back to acquisition."""
    raw, manifest = validate_selection(selection, sources, root=root)
    writer = _writer(root)
    result = {'schemaVersion': SCHEMA, 'selectionSHA256': sha(canonical(selection)),
              'acceptanceManifestSHA256': MANIFEST_SHA, 'reviewedWriterSHA256': WRITER_SHA,
              'independentReviewSHA256': REVIEW_SHA, 'status': 'blocked',
              'errorCode': None, 'dispositionApplied': False, 'receiptSHA256': None,
              'acceptedAtUTC': None, 'originalAcquiredAt': None, 'networkRequests': 0,
              'networkBodyBytes': 0, 'newOriginalCopies': 0,
              'preparationPerformed': False, 'sourceBodiesModified': False,
              'oldFailedRecordsModified': False, 'items': [],
              'maximumLocalOriginalReadBytes': 2*sum(r['proposedCustodyReference']['bytes'] for r in manifest['items']),
              'verifiedOriginalPayloadBytes': 0, 'localOriginalReadBytes': None,
              'localOriginalReadAccountingComplete': False}
    try:
        summary, capability = writer.accept_selected(raw, parent_selection=selection,
            owner_runtime=owner_runtime, lease_fd=lease_fd,
            current_adverse_evidence=current_adverse_evidence, absolute_deadline=absolute_deadline)
        refs = capability.references()
        _require(refs['receiptSHA256'] == summary['receiptSHA256'])
        result.update({key: summary[key] for key in (
            'status', 'dispositionApplied', 'receiptSHA256', 'acceptedAtUTC', 'originalAcquiredAt')})
        result['verifiedOriginalPayloadBytes'] = sum(r['proposedCustodyReference']['bytes'] for r in manifest['items'])
        result['localOriginalReadBytes'] = 2*result['verifiedOriginalPayloadBytes']
        result['localOriginalReadAccountingComplete'] = True
        result['items'] = [{'assetId': row['assetId'], 'sourceKey': row['sourceKey'],
            'sourceContractSHA256': row['sourceContractSHA256'],
            'originalSHA256': row['proposedCustodyReference']['sha256'],
            'originalBytes': row['proposedCustodyReference']['bytes'],
            'relativePath': row['proposedCustodyReference']['relativePath'],
            'oldFailedIntentSHA256': row['proposedCustodyReference']['oldFailedIntent']['sha256'],
            'oldFailedDetailSHA256': row['proposedCustodyReference']['oldFailedDetail']['sha256'],
            'originalAcquiredAt': None, 'downstreamHolds': row['preservedDownstreamHolds']}
            for row in manifest['items']]
        _require(refs['items'] == [{'sourceKey': row['sourceKey'], 'assetId': row['assetId'],
            'reference': row['proposedCustodyReference'], 'downstreamHolds': row['preservedDownstreamHolds']}
            for row in manifest['items']])
    except writer.AcceptanceError as error:
        result['errorCode'] = str(error) if str(error) in writer.ERRORS else 'acceptance-local-failure'
    return sanitize(result, selection, sources, root=root)


def sanitize(result, selection, sources, *, root=ROOT):
    _, manifest = validate_selection(selection, sources, root=root)
    writer = _writer(root)
    keys = {'schemaVersion','selectionSHA256','acceptanceManifestSHA256','reviewedWriterSHA256',
        'independentReviewSHA256','status','errorCode','dispositionApplied','receiptSHA256',
        'acceptedAtUTC','originalAcquiredAt','networkRequests','networkBodyBytes','newOriginalCopies',
        'preparationPerformed','sourceBodiesModified','oldFailedRecordsModified','items',
        'maximumLocalOriginalReadBytes','verifiedOriginalPayloadBytes','localOriginalReadBytes','localOriginalReadAccountingComplete'}
    _require(type(result) is dict and set(result) == keys and result['schemaVersion'] == SCHEMA
        and result['selectionSHA256'] == sha(canonical(selection))
        and result['acceptanceManifestSHA256'] == MANIFEST_SHA and result['reviewedWriterSHA256'] == WRITER_SHA
        and result['independentReviewSHA256'] == REVIEW_SHA
        and result['originalAcquiredAt'] is None
        and all(type(result[k]) is int and result[k] == 0 for k in ('networkRequests','networkBodyBytes','newOriginalCopies'))
        and all(result[k] is False for k in ('preparationPerformed','sourceBodiesModified','oldFailedRecordsModified')))
    payload = sum(r['proposedCustodyReference']['bytes'] for r in manifest['items'])
    _require(type(result['maximumLocalOriginalReadBytes']) is int and result['maximumLocalOriginalReadBytes'] == 2*payload)
    if result['status'] == 'blocked':
        _require(result['errorCode'] in writer.ERRORS and result['dispositionApplied'] is False
            and result['receiptSHA256'] is None and result['acceptedAtUTC'] is None and result['items'] == []
            and result['verifiedOriginalPayloadBytes'] == 0 and type(result['verifiedOriginalPayloadBytes']) is int
            and result['localOriginalReadBytes'] is None and result['localOriginalReadAccountingComplete'] is False)
    else:
        _require(result['status'] in ('accepted-retained-reference','reused-accepted-reference')
            and type(result['verifiedOriginalPayloadBytes']) is int and result['verifiedOriginalPayloadBytes'] == payload
            and type(result['localOriginalReadBytes']) is int and result['localOriginalReadBytes'] == 2*payload
            and result['localOriginalReadAccountingComplete'] is True
            and result['errorCode'] is None and result['dispositionApplied'] is (result['status'] == 'accepted-retained-reference')
            and isinstance(result['receiptSHA256'],str) and re.fullmatch('[0-9a-f]{64}',result['receiptSHA256'])
            and isinstance(result['acceptedAtUTC'],str) and len(result['acceptedAtUTC']) <= 40)
        try: _require(datetime.fromisoformat(result['acceptedAtUTC']).utcoffset() is not None)
        except (ValueError,TypeError): _require(False)
        expected = [{'assetId': row['assetId'], 'sourceKey': row['sourceKey'],
            'sourceContractSHA256': row['sourceContractSHA256'],
            'originalSHA256': row['proposedCustodyReference']['sha256'],
            'originalBytes': row['proposedCustodyReference']['bytes'],
            'relativePath': row['proposedCustodyReference']['relativePath'],
            'oldFailedIntentSHA256': row['proposedCustodyReference']['oldFailedIntent']['sha256'],
            'oldFailedDetailSHA256': row['proposedCustodyReference']['oldFailedDetail']['sha256'],
            'originalAcquiredAt': None, 'downstreamHolds': row['preservedDownstreamHolds']}
            for row in manifest['items']]
        _require(result['items'] == expected)
    _require(len(canonical(result)) <= MAX_REPORT)
    return result
