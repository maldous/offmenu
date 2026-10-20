"""Invented variants through direct validation and existing offline qualify."""
import copy
from dataclasses import replace
import unittest

from offmenu.refresh.acceptance import contract_fingerprint, fingerprint
from offmenu.refresh.english_extension import ReviewedWitness
import test_english_extension as fixtures
from test_english_extension import encode

RELATIONS = ('regional-variant', 'ingredient-substitution', 'preparation-variant', 'competing-identity-claim')


class ReviewedVariantTests(unittest.TestCase):
    def setUp(self):
        fixtures.EnglishExtensionTest.setUp(self)
        self.f.policy = replace(self.f.policy, review_authorities=frozenset(['synthetic-reviewer']))
        self.external = {'role': 'recipe-source-record', 'graphIri': 'https://example.invalid/external-recipe',
                         'evidence': [self.f.ext['policies']['variants']]}
        self.f.set_claim('R', self.external, source='external-recipe-source')
        self.f.records['R'] = self.f.claims['R']

    check = fixtures.ReviewedRelationshipTest.check
    mutate_witness = fixtures.ReviewedRelationshipTest.mutate_witness

    def variant(self, relation='regional-variant', state='reviewed', region='synthetic-region'):
        a = {'assertionId': 'v', 'sourceRecordRefs': ['native-recipe', 'R'], 'relation': relation,
             'region': region, 'state': state, 'mergePerformed': False,
             'evidence': [self.f.ext['policies']['variants']]}
        self.f.ext['variantAssertions'] = [a]
        return a

    def bind(self, assertion):
        resolved = self.f.records['R']
        external = {'claimId': 'R', 'artifact': copy.deepcopy(resolved.artifact),
                    'recordPointer': resolved.record_pointer, 'line': resolved.line,
                    'qualificationSha256': resolved.qualification['qualificationSha256'],
                    'contractSha256': contract_fingerprint(resolved.contract), 'dataSha256': fingerprint(self.external)}
        scope = {'type': 'recipe-variant-relationship', 'assertionId': assertion['assertionId'],
                 'assertionSha256': fingerprint(assertion), 'relation': assertion['relation'],
                 'region': assertion['region'], 'inputBinding': copy.deepcopy(self.f.ext['input']),
                 'sourceRecords': [{'sourceRecordId': 'native-recipe', 'inputBinding': copy.deepcopy(self.f.ext['input'])}, external],
                 'decisionState': 'affirmed', 'reviewStatus': 'reviewed', 'reviewAuthority': 'synthetic-reviewer'}
        self.f.relationships[assertion['assertionId']] = ReviewedWitness(
            self.f.pin('variant-review.json', encode(scope)), scope, 'synthetic-reviewer')

    def test_all_reviewed_variant_relations_reject_generic_pins(self):
        for relation in RELATIONS:
            with self.subTest(relation=relation):
                self.variant(relation); self.check(('english-relationship-unqualified',))

    def test_all_reviewed_variant_relations_accept_exact_reviewed_witness(self):
        for relation in RELATIONS:
            with self.subTest(relation=relation):
                a = self.variant(relation); self.bind(a); self.check()
                self.assertFalse(a['mergePerformed'])

    def test_nonreviewed_variants_remain_unpromoted(self):
        for state in ('proposed', 'unresolved', 'rejected'):
            with self.subTest(state=state):
                self.variant(state=state); self.check()

    def test_region_relation_assertion_and_input_are_exact(self):
        a = self.variant(); self.bind(a); original = self.f.relationships['v']
        changes = [lambda s: s.update(region='other'), lambda s: s.update(relation='preparation-variant'),
                   lambda s: s.update(assertionId='other'), lambda s: s.update(assertionSha256='0'*64),
                   lambda s: s['inputBinding'].update(sourceRecordId='other'),
                   lambda s: s['inputBinding'].update(releaseId='other'),
                   lambda s: s['inputBinding']['parsedArtifact'].update(sha256='0'*64),
                   lambda s: s.update(type='generic-policy')]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.f.relationships['v'] = original
                self.mutate_witness(self.f.relationships, 'v', change)
                self.check(('english-relationship-unqualified',))

    def test_unknown_region_is_explicit_null_not_inferred(self):
        a = self.variant(region=None); self.bind(a); self.check()
        self.mutate_witness(self.f.relationships, 'v', lambda s: s.update(region='invented'))
        self.check(('english-relationship-unqualified',))

    def test_selected_authority_required(self):
        a = self.variant(); self.bind(a)
        self.f.policy = replace(self.f.policy, review_authorities=frozenset())
        self.check(('english-relationship-unqualified',))

    def test_untyped_or_rejected_witness_cannot_mark_reviewed(self):
        a = self.variant(); self.bind(a); original = self.f.relationships['v']
        self.f.relationships['v'] = {'pin': original.pin, 'scope': original.scope}
        self.check(('english-relationship-unqualified',))
        for key, value in [('reviewStatus', 'rejected'), ('decisionState', 'unresolved')]:
            self.f.relationships['v'] = original
            self.mutate_witness(self.f.relationships, 'v', lambda s: s.update({key: value}))
            self.check(('english-relationship-unqualified',))

    def test_external_record_version_is_bound(self):
        a = self.variant(); self.bind(a)
        self.external['revision'] = 'changed'
        self.f.set_claim('R', self.external, source='external-recipe-source')
        self.f.records['R'] = self.f.claims['R']
        self.check(('english-relationship-unqualified',))

    def test_external_record_reference_still_requires_qualification(self):
        a = self.variant(); self.bind(a); self.f.records.pop('R'); self.f.claims.pop('R')
        self.check(('english-identity-unresolved',))

    def test_changed_assertion_invalidates_old_witness(self):
        a = self.variant(); self.bind(a); a['region'] = 'changed'
        self.check(('english-relationship-unqualified',))


if __name__ == '__main__':
    unittest.main()
