"""Invented reviewed translations: purpose permission is not review evidence."""
import copy
from dataclasses import replace
import unittest

from offmenu.refresh.acceptance import fingerprint
from offmenu.refresh.english_extension import ReviewedWitness
import test_english_extension as fixtures
from test_english_extension import encode


class ReviewedTranslationTests(unittest.TestCase):
    def setUp(self):
        fixtures.EnglishExtensionTest.setUp(self)
        self.f.policy = replace(self.f.policy, review_authorities=frozenset(['synthetic-reviewer']))
        self.reviews = {}
        self.f.translation = lambda key: self.reviews.get(key)
        self.assertEqual(self.f.ext['permissions'][1]['purpose'], 'translation')
        self.assertEqual(self.f.ext['permissions'][1]['state'], 'permitted')

    check = fixtures.ReviewedRelationshipTest.check

    def bind(self):
        t = self.f.t
        scope = {'type': 'translation-review', 'assertionId': t['assertionId'],
                 'assertionSha256': fingerprint(t), 'inputBinding': copy.deepcopy(self.f.ext['input']),
                 **{key: copy.deepcopy(t[key]) for key in ('englishText', 'origin', 'methodVersion', 'target')},
                 'decisionState': 'affirmed', 'reviewStatus': 'reviewed', 'reviewAuthority': 'synthetic-reviewer'}
        self.reviews[t['assertionId']] = ReviewedWitness(
            self.f.pin('translation-review.json', encode(scope)), scope, 'synthetic-reviewer')

    def mutate_scope(self, change):
        old = self.reviews['t']; scope = copy.deepcopy(old.scope); change(scope)
        self.reviews['t'] = ReviewedWitness(self.f.pin('translation-review.json', encode(scope)), scope, old.authority)

    def test_reviewed_generic_or_empty_evidence_requires_independent_review(self):
        self.f.t['state'] = 'reviewed'
        for evidence in ([self.f.ext['policies']['translation']], []):
            with self.subTest(evidence=evidence):
                self.f.t['evidence'] = evidence
                self.check(('english-translation-review-unqualified',))

    def test_selected_affirmative_exact_review_with_generic_or_empty_evidence_passes(self):
        self.f.t['state'] = 'reviewed'
        for evidence in ([self.f.ext['policies']['translation']], []):
            with self.subTest(evidence=evidence):
                self.f.t['evidence'] = evidence; self.bind(); self.check()

    def test_untyped_dictionary_is_not_review(self):
        self.f.t['state'] = 'reviewed'; self.bind(); old = self.reviews['t']
        self.reviews['t'] = {'pin': old.pin, 'scope': old.scope, 'authority': old.authority}
        self.check(('english-translation-review-unqualified',))

    def test_unselected_or_forged_authority_is_not_review(self):
        self.f.t['state'] = 'reviewed'; self.bind()
        self.f.policy = replace(self.f.policy, review_authorities=frozenset())
        self.check(('english-translation-review-unqualified',))
        self.f.policy = replace(self.f.policy, review_authorities=frozenset(['synthetic-reviewer']))
        old = self.reviews['t']; scope = {**old.scope, 'reviewAuthority': 'unselected'}
        self.reviews['t'] = ReviewedWitness(self.f.pin('unselected-review.json', encode(scope)), scope, 'unselected')
        self.check(('english-translation-review-unqualified',))

    def test_generic_pin_cannot_forge_typed_review(self):
        self.f.t['state'] = 'reviewed'; self.bind(); old = self.reviews['t']
        self.reviews['t'] = ReviewedWitness(self.f.ext['policies']['translation'], old.scope, old.authority)
        self.check(('english-translation-review-unqualified',))

    def test_stale_review_scope_text_origin_method_target_input_or_hash_rejected(self):
        self.f.t['state'] = 'reviewed'; self.bind(); original = self.reviews['t']
        changes = [lambda s: s.update(englishText='stale text'), lambda s: s.update(origin='model-proposal'),
                   lambda s: s.update(methodVersion='stale method'),
                   lambda s: s['target'].update(fieldPointer='/other'),
                   lambda s: s['inputBinding'].update(sourceRecordId='other'),
                   lambda s: s['inputBinding']['parsedArtifact'].update(sha256='0'*64),
                   lambda s: s.update(assertionSha256='0'*64)]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.reviews['t'] = original; self.mutate_scope(change)
                self.check(('english-translation-review-unqualified',))

    def test_mutating_actual_text_origin_or_method_invalidates_old_review(self):
        self.f.t['state'] = 'reviewed'; self.bind(); original = copy.deepcopy(self.f.t)
        for key, value in [('englishText', 'changed English proposal'), ('origin', 'glossary-proposal'),
                           ('methodVersion', 'changed method')]:
            with self.subTest(key=key):
                self.f.t.clear(); self.f.t.update(copy.deepcopy(original)); self.f.t[key] = value
                self.check(('english-translation-review-unqualified',))

    def test_nonaffirmative_or_wrong_review_type_rejected(self):
        self.f.t['state'] = 'reviewed'; self.bind(); original = self.reviews['t']
        for key, value in [('decisionState', 'unresolved'), ('reviewStatus', 'rejected'), ('type', 'generic-policy')]:
            with self.subTest(key=key):
                self.reviews['t'] = original; self.mutate_scope(lambda s: s.update({key: value}))
                self.check(('english-translation-review-unqualified',))

    def test_proposed_unresolved_and_rejected_behavior_preserved_without_review_lookup(self):
        def forbidden(key):
            raise AssertionError('unreviewed translation must not invoke review resolver')
        self.f.translation = forbidden
        for state in ('proposed', 'unresolved', 'rejected'):
            with self.subTest(state=state):
                self.f.t.update(state=state, evidence=[]); self.check()

    def test_affirmative_review_does_not_grant_translation_permission(self):
        self.f.t['state'] = 'reviewed'; self.bind()
        self.f.ext['permissions'][1]['state'] = 'unknown'
        self.check(('english-translation-permission-missing',))


if __name__ == '__main__':
    unittest.main()
