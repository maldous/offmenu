"""Offline source-bound coverage tests; no filesystem body or source requests."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from offmenu.refresh import fetch_coverage as f


def fixture():
    binding = {'country': 'AA', 'type': 'recipes'}
    assets = [
        {'assetId': 'original:one', 'bindings': [binding], 'holds': ['parse-unselected'], 'sourceStageHolds': []},
        {'assetId': 'candidate:two', 'bindings': [], 'holds': [], 'sourceStageHolds': []},
    ]
    cell = {'country': 'AA', 'type': 'recipes', 'assetIds': ['original:one'],
            'canonicalAssetIds': ['original:one'], 'candidateAssetIds': [], 'sourceContractAssetIds': []}
    manifest = {'assets': assets, 'countries': ['AA'], 'types': ['recipes'], 'cells': [cell],
        'snapshotMetadataIndex': {'m': {'path': '/known/metadata.json', 'metadataSHA256': 'a'*64}},
        'snapshotUnjoinableEvidence': {'count': 1}}
    base = f.canonical(manifest)
    header = {'schemaVersion': 'offmenu-fetch-closure-inventory/1',
              'status': 'metadata-only-source-bound-closure-inventory-not-execution-selection',
              'controllingRun': {'executionStage': 'fetch', 'resultSHA256': 'b'*64},
              'inputPins': {'runtimeManifest': {'sha256': f.sha(base), 'bytes': len(base)}}}
    rows = []
    for index, asset in enumerate(assets):
        verified = index == 0
        rows.append({'assetId': asset['assetId'], 'manifestIndex': index,
            'baselineAssetCanonicalSHA256': f.sha(f.canonical(asset)),
            'actionCategory': 'verified-reuse' if verified else 'source-discovered-contract-incomplete',
            'exactBindings': deepcopy(asset['bindings']),
            'sourceRestrictions': {'sourceStageHolds': [], 'genericAndSourceHoldStatements': asset['holds'], 'genericWorkflowFlagIsLicenceBan': False},
            'closureSatisfied': False, 'directOriginalVerified': verified, 'failureResponseArtifact': False,
            'usableRoleIdentityVerified': verified, 'fetchSourceConditionHeld': False,
            'fetchBlockedByCurrentHold':False,'originalUsabilityScopeUnresolved':True,
            'originalIdentity': {'path': '/private/one.pdf', 'sha256': 'c'*64, 'bytes': 30} if verified else None,
            'currentOutcome': {'custody': 'verified-original' if verified else 'no-path'},
            'retainedVerification': None, 'endpointIds': ['e1' if verified else 'e2'],
            'concreteEndpointCandidateIds': [], 'role': 'reference-document-original', 'missingFetchContractFields': []})
    requirements = [{**deepcopy(cell), 'requirementId': 'AA/recipes',
        'baselineCellCanonicalSHA256': f.sha(f.canonical(cell)), 'exactBoundAssetIds': ['original:one'],
        'existingCandidateAssetIds': [], 'candidateMappingsAdopted': False,
        'fetchClosureSatisfied': False, 'countryTypeComplete': False,
        'applicability': {'state': 'unknown', 'nonApplicabilitySupported': False},
        'requiredScope': {'reviewedScopeContract': None}, 'closureGaps': ['source population unresolved'],
        'unselectedMappingCandidateAssetIds': ['candidate:two'],
        'verifiedOriginalAssetIds': ['original:one'], 'verifiedOriginalCanonicalAssetIds': ['original:one'],
        'verifiedOriginalExistingCandidateAssetIds': [], 'verifiedOriginalSourceContractAssetIds': [],
        'status': 'verified-local-original-contribution-existing-scope', 'sharedGroupCandidateIds': ['g']}]
    group = {'groupId': 'g', 'nativeAssetId': 'original:one', 'groupKind': 'shared-distribution',
        'scopeBindingAdopted': False, 'fetchClosureSatisfied': False, 'memberAssetIds': ['original:one'],
        'latestVerifiedMemberAssetIds': ['original:one'], 'latestNonverifiedMemberAssetIds': [], 'requiredClosure': ['scope']}
    metadata = {'targetId': 'm', 'path': '/known/metadata.json', 'expectedMetadataSHA256': 'a'*64,
        'executionEnabled': False, 'sourceBodiesRead': False, 'sourceBodiesUploaded': False,
        'followReferencedFiles': False, 'directoryDiscovery': False, 'relatedUnverifiedSnapshotAssetIds': ['candidate:two'],
        'candidateForBoundedOwnerMetadataReconciliation': True, 'readMode': 'json',
        'proposedMaximumReadBytes': 100, 'observedMetadataBytes': 100,
        'atomicUnjoinableFragmentReferences': [{'pin': 'sourceManifest', 'jsonPointer': '/unresolvedSnapshotEvidence/0'}]}
    docs = {
        'assets': {**deepcopy(header), 'records': rows, 'counts': {'assets': 2, 'countries': 1, 'types': 1, 'countryTypeRequirements': 1,
                    'assetActionCategories': {'verified-reuse': 1, 'source-discovered-contract-incomplete': 1}}},
        'requirements': {**deepcopy(header), 'requirements': requirements},
        'groups': {**deepcopy(header), 'groups': [group], 'contentIdentityGroups': [{
            'directAssetIds': ['original:one'], 'contentSHA256': 'c'*64, 'bytes': 30, 'sameDigestDoesNotEstablishScope': True}]},
        'endpoints': {**deepcopy(header), 'records': [
            {'endpointId': 'e1', 'assetId': 'original:one', 'endpointPresenceGrantsAuthority': False, 'sourceBodyRequestedByThisAudit': False},
            {'endpointId': 'e2', 'assetId': 'candidate:two', 'endpointPresenceGrantsAuthority': False, 'sourceBodyRequestedByThisAudit': False}]},
        'metadata': {**deepcopy(header), 'targets': [metadata], 'atomicUnjoinableEvidencePreserved': True, 'readOnlyMetadataProposal': True},
    }
    return base, docs


def admit(base, docs):
    raw = {k: f.canonical(v) for k,v in docs.items()}
    pins = {k: {'sha256': f.sha(v), 'bytes': len(v)} for k,v in raw.items()}
    return f.admit_bundle(raw, pins, baseline_manifest_raw=base)


class CoverageTests(unittest.TestCase):
    def setUp(self): self.base, self.docs = fixture()
    def rejects(self):
        with self.assertRaisesRegex(f.RefreshError, '^fetch-coverage-input-invalid$'): admit(self.base, self.docs)
    def test_complete_inventory_still_has_explicit_global_gap(self):
        result = f.review_projection(admit(self.base, self.docs))
        self.assertFalse(result['coverageComplete'])
        self.assertEqual(result['counts']['requirementsWithCanonicalOrSourceContractVerifiedContribution'], 1)
        self.assertEqual(result['counts']['satisfiedRequirements'], 0)
        self.assertEqual(len(result['assets']), 2)
        self.assertEqual(result['requirements'][0]['verifiedOriginalCanonicalAssetIds'], ['original:one'])
    def test_no_file_open_or_network_even_for_source_paths(self):
        with patch('builtins.open', side_effect=AssertionError('no source reads')), patch('socket.socket', side_effect=AssertionError('no network')):
            result = f.review_projection(admit(self.base, self.docs))
        self.assertEqual(result['localOriginalBytesRead'], 0)
        self.assertEqual(result['networkRequests'], 0)
    def test_removed_all_groups(self): self.docs['groups']['groups']=[]; self.rejects()
    def test_unknown_group_reference(self): self.docs['requirements']['requirements'][0]['sharedGroupCandidateIds']=['unknown'];self.rejects()
    def test_string_boolean_hold(self): self.docs['assets']['records'][0]['fetchBlockedByCurrentHold']='false';self.rejects()
    def test_missing_projected_contract_fields(self): del self.docs['assets']['records'][0]['missingFetchContractFields'];self.rejects()
    def test_invalid_projected_role(self): self.docs['assets']['records'][0]['role']={};self.rejects()
    def test_invalid_group_closure(self):self.docs['groups']['groups'][0]['requiredClosure']=False;self.rejects()
    def test_missing_asset(self): self.docs['assets']['records'].pop(); self.rejects()
    def test_duplicate_asset(self): self.docs['assets']['records'][1] = deepcopy(self.docs['assets']['records'][0]); self.rejects()
    def test_changed_baseline_asset(self): self.docs['assets']['records'][0]['baselineAssetCanonicalSHA256'] = '0'*64; self.rejects()
    def test_deleted_hold(self): self.docs['assets']['records'][0]['sourceRestrictions']['genericAndSourceHoldStatements'] = []; self.rejects()
    def test_generic_hold_is_not_a_licence_ban(self): self.docs['assets']['records'][0]['sourceRestrictions']['genericWorkflowFlagIsLicenceBan'] = True; self.rejects()
    def test_failed_response_never_usable_original(self): self.docs['assets']['records'][0]['failureResponseArtifact'] = True; self.rejects()
    def test_count_tampering(self): self.docs['assets']['counts']['assets'] = 1; self.rejects()
    def test_missing_cell(self): self.docs['requirements']['requirements'] = []; self.rejects()
    def test_cell_candidate_cannot_become_canonical(self): self.docs['requirements']['requirements'][0]['canonicalAssetIds'].append('candidate:two'); self.rejects()
    def test_unverified_copy_cannot_become_positive_contribution(self): self.docs['requirements']['requirements'][0]['verifiedOriginalAssetIds'].append('candidate:two'); self.rejects()
    def test_scope_unknown_does_not_mean_inapplicable(self): self.docs['requirements']['requirements'][0]['applicability']['state'] = 'not-applicable'; self.rejects()
    def test_new_scope_adoption_needs_new_review(self): self.docs['requirements']['requirements'][0]['candidateMappingsAdopted'] = True; self.rejects()
    def test_global_group_does_not_fanout(self): self.docs['groups']['groups'][0]['countryFanoutAllowed'] = True; self.rejects()
    def test_group_member_is_not_omitted(self): self.docs['groups']['groups'][0]['latestVerifiedMemberAssetIds'] = []; self.rejects()
    def test_byte_equality_does_not_grant_source_scope(self): self.docs['groups']['contentIdentityGroups'][0]['sameDigestDoesNotEstablishScope'] = False; self.rejects()
    def test_endpoint_is_not_request_permission(self): self.docs['endpoints']['records'][0]['endpointPresenceGrantsAuthority'] = True; self.rejects()
    def test_missing_endpoint(self): self.docs['endpoints']['records'].pop(); self.rejects()
    def test_metadata_path_substitution(self): self.docs['metadata']['targets'][0]['path'] = '/new/path'; self.rejects()
    def test_metadata_proposal_cannot_activate(self): self.docs['metadata']['targets'][0]['executionEnabled'] = True; self.rejects()
    def test_metadata_cannot_follow_files(self): self.docs['metadata']['targets'][0]['followReferencedFiles'] = True; self.rejects()
    def test_unjoinable_fragment_stays_visible(self): self.docs['metadata']['targets'][0]['atomicUnjoinableFragmentReferences'] = []; self.rejects()
    def test_mixed_predecessor_receipts_reject(self): self.docs['groups']['controllingRun']['resultSHA256'] = 'e'*64; self.rejects()
    def test_embedded_pin_does_not_replace_review_pin(self):
        raw = {k:f.canonical(v)for k,v in self.docs.items()}; pins = {k:{'sha256':f.sha(v),'bytes':len(v)}for k,v in raw.items()}
        raw['assets'] += b' '
        with self.assertRaises(f.RefreshError): f.admit_bundle(raw,pins,baseline_manifest_raw=self.base)

if __name__ == '__main__': unittest.main()
