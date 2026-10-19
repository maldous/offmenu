#!/usr/bin/env python3
"""Pure metadata proposal for three exact retained references; no runtime API.

The caller supplies verified publication bytes. No paths, network, parser,
claims, original bodies, custody writes, or activation are performed here.
"""
import hashlib
import json

SCHEMA = 'offmenu-retained-taiwan-acceptance-proposal/1'
BASELINE_COMMIT = 'c74cfaee99c6d743c8d4982de4d8d8cce651b057'
REPORT_COMMIT = 'd6ce260a296e73a9a9f1985f8c2db79b7ec5ddbf'
RESULT_SHA256 = 'c36d6a2f8a34ad71e77d11f9bed89957cdde002d0e1820da4b4d0c1215f8556d'
RECEIPT_SHA256 = '6d363a25c06d9a6ffa8044e429de003290bcd2033c41ce23a9b2e3a25bf96825'
SELECTION_SHA256 = '81c0c919644d6df86681b4ef6ee946a25a191f85a0080a66e327c0b20d311a08'
ASSET_MANIFEST_SHA256 = '7ffa2f5ce688c6fde5019b9252fbb9f96b3037f76337598cc05f76c37ef8754a'
GLOBAL_REPORT_SHA256 = '95d44435b3d13aa2efa9a5d1410867aa8b4d048885d145a5cc5c7c4c59e7c9e6'
ROOT = '/home/user/src/offmenu-data/owner-collection-runtime'
PREFIX = ('docs/handover/2026-10-18/foo-owner-custody/manual-global/'
          'owner-local-comprehensive-20261018-002/results/' + RESULT_SHA256)
PINS = {
    'tw41-eastern-afa-14101-regional-bento-original': (4747, 8,
        'be9ca557429501f957f82ae712c92a9ac32318643c718f78b44646f420293422'),
    'tw41-eastern-afa-14102-regional-bento-original': (4748, 4,
        'b603fe15700c9a2fb6cf943ad917191614e982a5e852f26873cb41b2fa714f15'),
    'tw41-eastern-afa-14103-regional-bento-original': (4749, 10,
        'f9cd82661724d0030dce67b1e53dce8cb8739a6722dfee4e43b5d83a5bf598c5'),
}
HOLDS = ['redistribution-unselected', 'commercial-corpus-reuse-unqualified',
         'translation-unselected', 'normalization-unselected',
         'semantic-and-gold-admission-unselected', 'country-completeness-unestablished']


def canonical(value):
    """Acquisition-engine canonical JSON: sorted UTF-8, compact, one LF."""
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('invalid-retained-taiwan-acceptance-proposal')


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: require(False))
        require(isinstance(value, dict))
        return value
    except (TypeError, UnicodeError, json.JSONDecodeError):
        raise ValueError('invalid-retained-taiwan-acceptance-proposal') from None


def pinned(raw, digest):
    require(type(raw) is bytes and sha(raw) == digest)
    return strict_json(raw)


def build_proposal(result_bytes, receipt_bytes, selection_bytes, asset_manifest_bytes):
    """Return an INACTIVE review manifest from the exact four metadata inputs.

    Success verifies metadata binding only. It never accepts a disposition,
    reads custody, grants permissions, or builds a runnable preparation queue.
    """
    envelope = pinned(result_bytes, RESULT_SHA256)
    receipt = pinned(receipt_bytes, RECEIPT_SHA256)
    selection = pinned(selection_bytes, SELECTION_SHA256)
    assets = pinned(asset_manifest_bytes, ASSET_MANIFEST_SHA256)
    report = envelope['globalReport']
    require(envelope['globalReportSHA256'] == GLOBAL_REPORT_SHA256 == sha(canonical(report)))
    require(receipt['resultSHA256'] == RESULT_SHA256 and
            receipt['globalReportSHA256'] == GLOBAL_REPORT_SHA256 and
            report['selectionSHA256'] == SELECTION_SHA256 and
            report['manifestSHA256'] == ASSET_MANIFEST_SHA256)
    require(envelope['outputRoot'] == ROOT and envelope['invokingUID'] == 1000)
    require(receipt['rawSourceBodiesPublished'] is False and
            receipt['runnerResumeRequiresOutcomeImport'] is True)
    summary_entry = next(row for row in receipt['files'] if row['path'] == PREFIX + '/summary.json')
    require(summary_entry['sha256'] == RESULT_SHA256 and summary_entry['bytes'] == len(result_bytes))
    proposals = report['retainedTaiwanRecoveryProposals']
    require(len(proposals) == 3 and {row['sourceKey'] for row in proposals} == set(PINS))
    rows = []
    for key, (asset_index, pages, validation_sha) in sorted(PINS.items()):
        proposal = next(row for row in proposals if row['sourceKey'] == key)
        source = next(row for row in selection['sources'] if row['sourceKey'] == key)
        preparation = next(row for row in selection['preparation'] if row['sourceKey'] == key)
        asset = assets['assets'][asset_index]
        require(sha(canonical(proposal)) == validation_sha)
        require(sha(canonical(source)) == proposal['sourceContractSHA256'])
        require(proposal['status'] == 'validated-proposal' and proposal['dispositionApplied'] is False)
        require(proposal['parser']['pageCount'] == pages and proposal['parser']['allPagesTraversed'] is True)
        require(asset['assetId'] == 'source:' + key and asset['sourceKey'] == key)
        require(source['downstreamHolds'] == HOLDS == preparation['downstreamHolds'] == asset['downstreamHolds'])
        require(preparation['permissions'] == {'read': True, 'copy': True, 'extract': True})
        require(preparation['retainedOriginal'] is None and preparation['holds'] == [])
        contract = proposal['sourceContractSHA256']
        rows.append({
            'sourceKey': key, 'assetId': asset['assetId'], 'assetIndex': asset_index,
            'sourceContractSHA256': contract,
            'sourceContract': source,
            'validationProposalCanonicalSHA256': validation_sha,
            'validationProposal': proposal,
            'proposedCustodyReference': {
                **proposal['proposedDisposition'],
                'runtimeRoot': ROOT, 'expectedOwnerUID': 1000,
                'referenceOnly': True, 'acquisitionSuccessClaim': False,
                'originalBodyCreationOrCopyRequired': False,
                'oldFailedIntent': {
                    'relativePath': 'collection/private-originals/' + contract + '/successor-intent.json',
                    'sha256': proposal['oldFailedIntentSHA256'], 'state': 'failed-no-retry',
                    'preserveBytes': True,
                },
                'oldFailedDetail': {
                    'relativePath': 'collection/private-original-result-' + proposal['priorFailedDetailSHA256'] + '.json',
                    'sha256': proposal['priorFailedDetailSHA256'], 'preserveBytes': True,
                },
            },
            'existingPreparationSelection': preparation,
            'preparationSelectionCanonicalSHA256': sha(canonical(preparation)),
            'preparationEnabledByThisProposal': False,
            'preservedDownstreamHolds': HOLDS[:],
        })
    return {
        'schemaVersion': SCHEMA,
        'status': 'inactive-awaiting-independent-review-and-root-selection',
        'runtimeEnabled': False, 'acceptanceSelected': False, 'dispositionApplied': False,
        'preparationEnabled': False,
        'sourceBaseline': {'commit': BASELINE_COMMIT,
            'selectionPath': 'docs/collection-selections/global-comprehensive-selection.json',
            'selectionSHA256': SELECTION_SHA256,
            'assetManifestPath': 'docs/collection-selections/global-comprehensive-manifest.json',
            'assetManifestSHA256': ASSET_MANIFEST_SHA256},
        'publishedEvidence': {'repository': 'maldous/offmenu', 'reportCommit': REPORT_COMMIT,
            'resultPath': PREFIX + '/summary.json', 'resultSHA256': RESULT_SHA256,
            'publicationReceiptPath': PREFIX + '/receipt.json', 'publicationReceiptSHA256': RECEIPT_SHA256,
            'globalReportSHA256': GLOBAL_REPORT_SHA256,
            'publicationReceiptIsCustodyAcceptance': False,
            'sourceBaselineIsRuntimeAttestation': False},
        'existingOwnerContextBinding': {
            'handoffId': envelope['handover']['handoffId'],
            'runtimeConfigPath': 'docs/collection-selections/owner-comprehensive-runtime.json',
            'runtimeConfigSHA256': envelope['handover']['runtimeConfigSHA256'],
            'dispatchHoldPath': 'docs/operations/global-comprehensive-manual-handoff-20261018.json',
            'dispatchHoldSHA256': envelope['handover']['dispatchHoldSHA256'],
            'runnerResumeRequiresOutcomeImport': True,
            'existingRuntimeChanged': False, 'successorHandoffCreated': False,
            'progressAndOPCRemainOnExistingHandoff': True,
            'futureAcceptanceAuthority': 'unselected-requires-exact-manifest-root-selection',
        },
        'serialization': {'sourceContractAndValidationProposalDigests':
            'SHA256 of sorted compact UTF-8 JSON with ensure_ascii=false, allow_nan=false, and one final LF',
            'publishedEvidenceDigests': 'SHA256 of exact published file bytes'},
        'items': rows,
        'requiredGates': [
            {'gate': 'independent-review-of-exact-manifest-and-integration', 'status': 'pending'},
            {'gate': 'root-selection-binding-this-manifest-digest-and-exact-three-identities', 'status': 'pending'},
            {'gate': 'owner-runtime-and-existing-single-writer-lease', 'status': 'required-at-execution'},
            {'gate': 'fresh-no-follow-private-owner-single-link-body-intent-detail-and-parent-identity-checks', 'status': 'required-at-execution'},
            {'gate': 'fresh-bounded-exact-validator-pass-with-unchanged-body-and-failed-records', 'status': 'required-at-execution'},
            {'gate': 'append-only-private-custody-acceptance-receipt-before-reference-reuse', 'status': 'not-implemented'},
            {'gate': 'selected-source-preparation-permissions-holds-and-output-capacity-rechecked', 'status': 'required-before-preparation'},
            {'gate': 'reviewed-source-bound-bom-hook-through-existing-preparation-worker', 'status': 'not-integrated'},
        ],
        'invariants': {
            'networkRequests': 0, 'sourceBodyBytesUploaded': 0,
            'newDownloadOrRetryAllowed': False, 'oldFailedRecordsModified': False,
            'bodyRenameCopyDeleteOrNormalizationAllowed': False,
            'genericBOMAcceptanceAllowed': False, 'runnerResumeAuthorized': False,
            'publisherChecksumEstablished': False, 'historicalBodyIdentityEstablished': False,
            'strictISOConformanceEstablished': False, 'semanticOrGoldAdmission': False,
            'countryCoverageComplete': False, 'newPermissionsGranted': False,
        },
    }


def validate_proposal(proposal_bytes, result_bytes, receipt_bytes, selection_bytes, asset_manifest_bytes):
    """Validate exact inactive proposal semantics against pinned evidence bytes."""
    proposal = strict_json(proposal_bytes)
    expected = build_proposal(result_bytes, receipt_bytes, selection_bytes, asset_manifest_bytes)
    require(canonical(proposal) == canonical(expected))
    return {'schemaVersion': 'offmenu-retained-taiwan-proposal-validation/1',
            'status': 'verified-inactive-proposal', 'manifestSHA256': sha(proposal_bytes),
            'sourceCount': 3, 'dispositionApplied': False, 'runtimeEnabled': False,
            'preparationEnabled': False, 'custodyChecked': False,
            'ownerExecutionPerformed': False}
