"""Source-bound, metadata-only fetch coverage admission and review projection.

This module opens no paths, performs no network requests, and grants no source
permission. Exact reviewed document bytes are supplied by the caller. Candidate
scheduling is deliberately distinct from an executable transfer selection.
"""
from collections import Counter
from copy import deepcopy
import re
from .core import RefreshError, canonical, sha, strict_json

SCHEMA = 'offmenu-fetch-coverage-review/1'
MiB = 1024 * 1024
DOCUMENT_LIMITS = {'assets': 48*MiB, 'requirements': 32*MiB,
                   'groups': 8*MiB, 'endpoints': 16*MiB, 'metadata': 8*MiB}
ACTIONS = frozenset({
    'verified-reuse', 'verified-alias-reuse-no-extra-copy',
    'source-family-reuse-member-review', 'source-condition-held',
    'blocked-response-diagnostic', 'recover-exact-retained-custody',
    'bounded-retained-verification-review', 'reviewed-transfer-candidate',
    'source-discovered-contract-incomplete',
    'source-discovered-original-endpoint-unresolved',
    'source-not-identified-or-local-record-unresolved',
    'exclude-confirmed-failure-artifact',
    'current-source-access-or-no-retry-hold',
    'snapshot-identity-reconciliation-before-transfer',
})
HEX = re.compile(r'[0-9a-f]{64}')


def invalid():
    raise RefreshError('fetch-coverage-input-invalid')


def require(test):
    if not test:
        invalid()


def unique(values):
    require(isinstance(values, list) and len(values) == len(set(values)))
    return set(values)


def identity(value):
    require(isinstance(value, dict)
            and (value.get('path') is None or (isinstance(value['path'], str)
                 and value['path'].startswith('/') and '\x00' not in value['path']))
            and isinstance(value.get('sha256'), str)
            and HEX.fullmatch(value['sha256']) is not None
            and type(value.get('bytes')) is int and value['bytes'] > 0)
    return value['sha256'], value['bytes']


def _admit_documents(raw_documents, expected_pins):
    """The pins must come from a separately reviewed source-bound selection.

    Artifact-supplied pins cannot replace the caller's expected pins. No embedded
    absolute path or endpoint is opened or dereferenced here.
    """
    require(set(raw_documents) == set(expected_pins) == set(DOCUMENT_LIMITS))
    docs = {}
    for key, limit in DOCUMENT_LIMITS.items():
        raw, pin = raw_documents[key], expected_pins[key]
        require(isinstance(raw, bytes) and type(pin.get('bytes')) is int
                and 0 < len(raw) == pin['bytes'] <= limit
                and sha(raw) == pin.get('sha256'))
        docs[key] = strict_json(raw)
        require(docs[key].get('schemaVersion') == 'offmenu-fetch-closure-inventory/1'
                and docs[key].get('status') ==
                'metadata-only-source-bound-closure-inventory-not-execution-selection')
    common = docs['assets']['controllingRun']
    require(common.get('executionStage') == 'fetch'
            and isinstance(common.get('resultSHA256'), str)
            and HEX.fullmatch(common['resultSHA256']) is not None)
    for doc in docs.values():
        require(doc['controllingRun'] == common)
    return docs


def _validate_assets(manifest, doc):
    records, originals = doc['records'], manifest['assets']
    require(isinstance(records, list) and len(records) == len(originals))
    result = {}
    for index, (row, original) in enumerate(zip(records, originals)):
        aid = original['assetId']
        require(row['assetId'] == aid and aid not in result
                and type(row['manifestIndex']) is int and row['manifestIndex'] == index
                and row['baselineAssetCanonicalSHA256'] == sha(canonical(original))
                and row['actionCategory'] in ACTIONS
                and row['exactBindings'] == original['bindings']
                and row['sourceRestrictions']['sourceStageHolds'] == original.get('sourceStageHolds', [])
                and row['sourceRestrictions']['genericAndSourceHoldStatements'] == original.get('holds', [])
                and row['sourceRestrictions']['genericWorkflowFlagIsLicenceBan'] is False
                and row['closureSatisfied'] is False)
        for field in ('directOriginalVerified', 'failureResponseArtifact',
                      'usableRoleIdentityVerified', 'fetchSourceConditionHeld',
                      'fetchBlockedByCurrentHold', 'originalUsabilityScopeUnresolved'):
            require(type(row[field]) is bool)
        require(type(row['role'])is str and bool(row['role'])
                and type(row['missingFetchContractFields'])is list
                and all(type(v)is str for v in row['missingFetchContractFields'])
                and type(row['currentOutcome'])is dict
                and type(row['currentOutcome']['custody'])is str)
        require(row['usableRoleIdentityVerified'] ==
                (row['directOriginalVerified'] and not row['failureResponseArtifact']))
        if row['directOriginalVerified']:
            identity(row['originalIdentity'])
            require(row['currentOutcome']['custody'] == 'verified-original')
        verification = row.get('retainedVerification')
        if verification:
            require(row['directOriginalVerified'] and verification['integrityVerified'] is True
                    and verification['state'] == 'completed-verified'
                    and verification['networkRequests'] == 0
                    and (verification['originalSHA256'], verification['originalBytes']) == identity(row['originalIdentity']))
        if row['failureResponseArtifact']:
            require(row['actionCategory'] == 'exclude-confirmed-failure-artifact')
        unique(row['endpointIds'])
        require(set(row['concreteEndpointCandidateIds']) <= set(row['endpointIds']))
        result[aid] = row
    counts = doc['counts']
    require(counts['assets'] == len(records)
            and counts['countries'] == len(manifest['countries'])
            and counts['types'] == len(manifest['types'])
            and counts['countryTypeRequirements'] == len(manifest['cells'])
            and counts['assetActionCategories'] == dict(Counter(r['actionCategory'] for r in records)))
    return result


def _validate_requirements(manifest, doc, assets):
    rows = doc['requirements']
    require(len(rows) == len(manifest['cells']))
    expected = {(c, t) for c in manifest['countries'] for t in manifest['types']}
    actual = set()
    for row, cell in zip(rows, manifest['cells']):
        pair = row['country'], row['type']
        require(pair == (cell['country'], cell['type']) and pair in expected
                and pair not in actual and row['requirementId'] == '/'.join(pair)
                and row['baselineCellCanonicalSHA256'] == sha(canonical(cell))
                and row['exactBoundAssetIds'] == cell['assetIds']
                and row['canonicalAssetIds'] == cell['canonicalAssetIds']
                and row['existingCandidateAssetIds'] == cell['candidateAssetIds']
                and row['sourceContractAssetIds'] == cell['sourceContractAssetIds']
                and row['candidateMappingsAdopted'] is False
                and row['fetchClosureSatisfied'] is False and row['countryTypeComplete'] is False)
        require(row['applicability']['state'] == 'unknown'
                and row['applicability']['nonApplicabilitySupported'] is False
                and row['requiredScope']['reviewedScopeContract'] is None
                and isinstance(row['closureGaps'], list) and bool(row['closureGaps']))
        for field in ('exactBoundAssetIds', 'canonicalAssetIds', 'existingCandidateAssetIds',
                      'sourceContractAssetIds', 'unselectedMappingCandidateAssetIds'):
            require(unique(row[field]) <= set(assets))
        for source, verified in (
            ('exactBoundAssetIds', 'verifiedOriginalAssetIds'),
            ('canonicalAssetIds', 'verifiedOriginalCanonicalAssetIds'),
            ('existingCandidateAssetIds', 'verifiedOriginalExistingCandidateAssetIds'),
            ('sourceContractAssetIds', 'verifiedOriginalSourceContractAssetIds')):
            require(unique(row[verified]) == {aid for aid in row[source]
                                             if assets[aid]['usableRoleIdentityVerified']})
        require(type(row['status'])is str and type(row['sharedGroupCandidateIds'])is list
                and all(type(v)is str for v in row['sharedGroupCandidateIds'])
                and all(type(v)is str for v in row['closureGaps']))
        actual.add(pair)
    require(actual == expected)


def _validate_groups(doc, assets, requirements=None):
    require(type(doc['groups'])is list and bool(doc['groups']))
    ids = set()
    for row in doc['groups']:
        require(row['groupId'] not in ids and row['nativeAssetId'] in assets
                and row['scopeBindingAdopted'] is False and row['fetchClosureSatisfied'] is False
                and row.get('runtimeEnabled', False) is False)
        require(type(row['groupKind'])is str and bool(row['groupKind'])
                and type(row['requiredClosure'])is list and bool(row['requiredClosure'])
                and all(type(v)is str for v in row['requiredClosure']))
        members = unique(row['memberAssetIds'])
        require(members <= set(assets)
                and unique(row['latestVerifiedMemberAssetIds']) ==
                    {aid for aid in members if assets[aid]['usableRoleIdentityVerified']}
                and unique(row['latestNonverifiedMemberAssetIds']) ==
                    {aid for aid in members if not assets[aid]['usableRoleIdentityVerified']})
        # Global distribution evidence is not a licence to fan out each member.
        require(row.get('countryFanoutAllowed', False) is False
                and row.get('countryFanoutToEveryMemberAllowed', False) is False)
        ids.add(row['groupId'])
    if requirements is not None:
        referenced={gid for r in requirements['requirements'] for gid in r['sharedGroupCandidateIds']}
        families={'family:'+aid for aid in assets if aid.startswith('native:')}
        require(ids==referenced|families)
    if 'counts'in doc:
        require(len(doc['groups'])==doc['counts']['sharedHistoricalDistributionGroups']+doc['counts']['sourceFamilyGroups'])
    direct = {aid for aid, row in assets.items() if row['directOriginalVerified']}
    grouped = set()
    for row in doc['contentIdentityGroups']:
        members = unique(row['directAssetIds'])
        require(bool(members) and members <= direct and not (members & grouped)
                and row['sameDigestDoesNotEstablishScope'] is True)
        require(all(identity(assets[aid]['originalIdentity']) ==
                    (row['contentSHA256'], row['bytes']) for aid in members))
        grouped.update(members)
    require(grouped == direct)


def _validate_endpoints(doc, assets):
    endpoints = {}
    for row in doc['records']:
        eid, aid = row['endpointId'], row['assetId']
        require(eid not in endpoints and aid in assets
                and eid in assets[aid]['endpointIds']
                and row['endpointPresenceGrantsAuthority'] is False
                and row['sourceBodyRequestedByThisAudit'] is False)
        endpoints[eid] = row
    require(set(endpoints) == {eid for row in assets.values() for eid in row['endpointIds']})


def _validate_metadata(doc, manifest, assets):
    targets = manifest['snapshotMetadataIndex']
    seen, fragments = set(), set()
    require(doc['atomicUnjoinableEvidencePreserved'] is True and doc['readOnlyMetadataProposal'] is True)
    for row in doc['targets']:
        tid = row['targetId']
        require(tid in targets and tid not in seen
                and row['path'] == targets[tid]['path']
                and row['expectedMetadataSHA256'] == targets[tid]['metadataSHA256']
                and row['executionEnabled'] is False
                and row['sourceBodiesRead'] is False and row['sourceBodiesUploaded'] is False
                and row['followReferencedFiles'] is False and row['directoryDiscovery'] is False
                and set(row['relatedUnverifiedSnapshotAssetIds']) <= set(assets))
        if row['candidateForBoundedOwnerMetadataReconciliation']:
            require(row['readMode'] == 'json' and type(row['proposedMaximumReadBytes']) is int
                    and 0 < row['proposedMaximumReadBytes'] == row['observedMetadataBytes'])
        else:
            require(row['proposedMaximumReadBytes'] is None)
        for ref in row['atomicUnjoinableFragmentReferences']:
            require(ref['pin'] == 'sourceManifest'
                    and re.fullmatch(r'/unresolvedSnapshotEvidence/[0-9]+', ref['jsonPointer']))
            fragments.add(int(ref['jsonPointer'].rsplit('/', 1)[1]))
        seen.add(tid)
    require(seen == set(targets)
            and fragments == set(range(manifest['snapshotUnjoinableEvidence']['count'])))


def admit_bundle(raw_documents, expected_pins, *, baseline_manifest_raw):
    """Validate a complete inactive audit without converting findings into jobs."""
    try:
        require(isinstance(baseline_manifest_raw, bytes) and len(baseline_manifest_raw) <= 16*MiB)
        manifest = strict_json(baseline_manifest_raw)
        docs = _admit_documents(raw_documents, expected_pins)
        for doc in docs.values():
            pin = doc['inputPins']['runtimeManifest']
            require(pin['sha256'] == sha(baseline_manifest_raw)
                    and pin['bytes'] == len(baseline_manifest_raw))
        assets = _validate_assets(manifest, docs['assets'])
        _validate_requirements(manifest, docs['requirements'], assets)
        _validate_groups(docs['groups'], assets, docs['requirements'])
        _validate_endpoints(docs['endpoints'], assets)
        _validate_metadata(docs['metadata'], manifest, assets)
        return {'documents': docs, 'manifest': manifest,
                'documentPins': deepcopy(expected_pins), 'baselineSHA256': sha(baseline_manifest_raw)}
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        invalid()


def review_projection(admitted):
    """Full-cardinality receipt-friendly metadata, never an execution selection."""
    docs, manifest = admitted['documents'], admitted['manifest']
    assets = docs['assets']['records']
    requirements = docs['requirements']['requirements']
    groups = docs['groups']['groups']
    direct = [r for r in assets if r['directOriginalVerified']]
    payload = sum(r['originalIdentity']['bytes'] for r in direct)
    output = {
        'schemaVersion': SCHEMA, 'status': 'review-only-not-runtime-selection',
        'controllingRun': deepcopy(docs['assets']['controllingRun']),
        'inputDocumentPins': deepcopy(admitted['documentPins']),
        'baselineManifestSHA256': admitted['baselineSHA256'],
        'queueExecutionStatus': 'not-run-by-coverage-projection',
        'globalFetchAcceptance': 'incomplete-scope-and-custody-gaps',
        'coverageComplete': False, 'networkRequests': 0, 'localOriginalBytesRead': 0,
        'counts': {
            'assetRecords': len(assets), 'countries': len(manifest['countries']),
            'countryTypeRequirements': len(requirements), 'sharedAndFamilyGroups': len(groups),
            'verifiedOriginalRecordsIncludingAliases': sum(r['currentOutcome']['custody'] == 'verified-original' for r in assets),
            'directVerifiedOriginalUnits': len(direct),
            'usableDirectVerifiedOriginalUnits': sum(r['usableRoleIdentityVerified'] for r in assets),
            'verifiedFailureResponseUnits': sum(r['failureResponseArtifact'] for r in direct),
            'directVerifiedPayloadBytesFromEvidence': payload,
            'verifiedDirectOriginalRoleCounts': dict(sorted(Counter(r['role'] for r in direct).items())),
            'requirementsWithExactBoundVerifiedOriginal': sum(bool(r['verifiedOriginalAssetIds']) for r in requirements),
            'requirementsWithCanonicalOrSourceContractVerifiedContribution': sum(bool(r['verifiedOriginalCanonicalAssetIds'] or r['verifiedOriginalSourceContractAssetIds']) for r in requirements),
            'requirementsWithCandidateOnlyVerifiedContribution': sum(bool(r['verifiedOriginalExistingCandidateAssetIds']) and not (r['verifiedOriginalCanonicalAssetIds'] or r['verifiedOriginalSourceContractAssetIds']) for r in requirements),
            'requirementsWithUnknownApplicability': sum(r['applicability']['state'] == 'unknown' for r in requirements),
            'satisfiedRequirements': 0, 'satisfiedSharedGroups': 0,
            'snapshotAtomicUnresolvedFragments': manifest['snapshotUnjoinableEvidence']['count'],
            'metadataReconciliationTargets': len(docs['metadata']['targets']),
            'actionCategories': dict(sorted(Counter(r['actionCategory'] for r in assets).items())),
        },
        'assets': [], 'requirements': [], 'groups': [],
    }
    for row in assets:
        output['assets'].append({
            'assetId': row['assetId'], 'manifestIndex': row['manifestIndex'],
            'actionCategory': row['actionCategory'], 'role': row['role'],
            'originalIdentityVerified': row['directOriginalVerified'],
            'usableRoleIdentityVerified': row['usableRoleIdentityVerified'],
            'failureResponseArtifact': row['failureResponseArtifact'],
            'fetchSourceConditionHeld': row['fetchSourceConditionHeld'],
            'fetchBlockedByCurrentHold': row.get('fetchBlockedByCurrentHold',row['fetchSourceConditionHeld']),
            'originalUsabilityScopeUnresolved': row.get('originalUsabilityScopeUnresolved',True),
            'sourceRestrictionsSHA256': sha(canonical(row['sourceRestrictions'])),
            'sourceConditionEvidenceRetained': True,
            'missingFetchContractFields': deepcopy(row['missingFetchContractFields']),
            'exactBindings': deepcopy(row['exactBindings']),
            'inputEvidenceIndex': row['manifestIndex'], 'closureSatisfied': False,
        })
    for row in requirements:
        output['requirements'].append({key: deepcopy(row[key]) for key in (
            'requirementId', 'country', 'type', 'status', 'applicability',
            'canonicalAssetIds', 'existingCandidateAssetIds', 'sourceContractAssetIds',
            'verifiedOriginalAssetIds', 'verifiedOriginalCanonicalAssetIds',
            'verifiedOriginalSourceContractAssetIds', 'verifiedOriginalExistingCandidateAssetIds',
            'candidateMappingsAdopted', 'sharedGroupCandidateIds',
            'closureGaps', 'fetchClosureSatisfied')})
    for row in groups:
        output['groups'].append({key: deepcopy(row[key]) for key in (
            'groupId', 'groupKind', 'nativeAssetId', 'memberAssetIds',
            'latestVerifiedMemberAssetIds', 'latestNonverifiedMemberAssetIds',
            'scopeBindingAdopted', 'fetchClosureSatisfied', 'requiredClosure')})
    require(len(canonical(output)) <= 16*MiB)
    return output
