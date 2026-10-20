"""Synthetic qualified native outputs only; no actual source/index/runtime run."""
import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import Asset, SourceContract, canonical, fingerprint, ids_digest, qualify
from offmenu.refresh.native_barcode_lookup import lookup_native_barcode, NativeLookupError


class NativeBarcodeLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.bundle = self.root / 'inputs'; self.bundle.mkdir()
        self.candidate = self.root / 'native.jsonl'
        for name in ['original.txt', 'rights.txt', 'scope.txt']:
            (self.bundle / name).write_bytes(b'invented fixture only')
        self.rows = [self.row('one', '00012345', '  豆腐, milk\n\u2028salt  '), self.row('two', '00012345', None)]
        self.prepare()

    def row(self, key, barcode, text):
        return {'schemaVersion': '1.0', 'kind': 'product', 'id': 'off:product:' + key, 'countries': [],
                'provenance': {'sourceId': 'off', 'releaseId': 'synthetic-r1', 'recordId': key,
                               'fetchedAt': '2026-10-21T00:00:00Z', 'visibility': 'private-candidate',
                               'license': 'synthetic', 'unknownClockNote': None},
                'data': {'identifiers': [{'system': 'barcode', 'value': barcode}], 'ingredientsText': text,
                         'qualificationStatus': 'unverified-source-assertions', 'unmapped': {'x': None, 'zero': 0}}}

    def prepare(self, source='off'):
        for row in self.rows:
            row['provenance']['sourceId'] = source
            row['id'] = source + ':' + row['kind'] + ':' + row['provenance']['recordId']
        self.candidate.write_bytes(b''.join(canonical([row]) + b'\n' for row in self.rows))
        assets = tuple(Asset(p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
                       for p in sorted(self.bundle.iterdir()))
        schema = {'type': 'object', 'required': ['id', 'schemaVersion', 'kind', 'provenance', 'data', 'countries']}
        schemas = {row['kind']: schema for row in self.rows}
        self.contract = SourceContract(source, 'synthetic-r1', 'fixture-native-products',
            '2026-10-21T00:00:00Z', assets, len(self.rows), ids_digest([r['id'] for r in self.rows]),
            schemas, fingerprint(schemas), lambda r: (), 'a'*64, assets[1], assets[2],
            frozenset(['retain', 'parse', 'transform']), fixture=True)
        raw = self.candidate.read_bytes()
        manifest = {'sourceId': source, 'releaseId': 'synthetic-r1', 'acquiredAt': self.contract.acquired_at,
                    'normalizedRecords': len(self.rows), 'rightsEvidenceSha256': assets[1].sha256,
                    'scopeEvidenceSha256': assets[2].sha256, 'candidateBytes': len(raw),
                    'candidateSha256': hashlib.sha256(raw).hexdigest(), 'inputFiles': [vars(a) for a in assets]}
        self.q = qualify(self.contract, self.bundle, self.candidate, manifest, scratch_root=self.root)
        self.assertTrue(self.q['qualified'], self.q['errors']); self.pin = self.q['qualificationSha256']

    def lookup(self, barcode='00012345', **kw):
        args = dict(contract=self.contract, qualification=self.q, qualification_sha256=self.pin, barcode=barcode)
        args.update(kw); return lookup_native_barcode(self.candidate, **args)

    def test_exact_text_native_ids_provenance_unknowns_and_collisions(self):
        before = copy.deepcopy(self.q); result = self.lookup()
        self.assertEqual([x['record'] for x in result['matches']], self.rows)
        self.assertEqual([x['nativeProductId'] for x in result['matches']], ['off:product:one', 'off:product:two'])
        self.assertEqual(result['matches'][0]['ingredientsText'], '  豆腐, milk\n\u2028salt  ')
        self.assertEqual(result['matches'][1]['ingredientsTextState'], 'null')
        self.assertEqual(self.q, before); self.assertTrue(result['fixture']); self.assertEqual(result['visibility'], 'private')

    def test_lexical_lookup_does_not_trim_or_strip_leading_zeros(self):
        self.assertEqual(self.lookup('12345')['matches'], []); self.assertEqual(self.lookup(' 00012345')['matches'], [])
        for value in [12345, '', None]:
            with self.subTest(value=value), self.assertRaisesRegex(NativeLookupError, 'barcode-invalid'): self.lookup(value)

    def test_missing_null_and_empty_ingredients_are_distinct(self):
        self.rows[0]['data'].pop('ingredientsText'); self.rows[1]['data']['ingredientsText'] = ''; self.prepare()
        rows = self.lookup()['matches']
        self.assertEqual([(r['ingredientsText'], r['ingredientsTextState']) for r in rows], [(None, 'missing'), ('', 'source-text')])

    def test_usda_native_record_id_is_not_replaced_by_barcode(self):
        self.prepare('usda-files'); result = self.lookup()
        self.assertEqual(result['sourceId'], 'usda-files')
        self.assertEqual(result['matches'][0]['nativeProductId'], 'usda-files:product:one')
        self.assertEqual(result['matches'][0]['sourceRecordId'], 'one')

    def test_nutrient_profiles_never_substitute_for_products(self):
        self.rows[1]['kind'] = 'nutrientProfile'; self.prepare()
        self.assertEqual(len(self.lookup()['matches']), 1); self.assertEqual(self.lookup()['scannedRecords'], 2)

    def test_duplicate_barcode_within_product_is_not_duplicate_match(self):
        self.rows[0]['data']['identifiers'] *= 2; self.prepare(); self.assertEqual(len(self.lookup()['matches']), 2)

    def test_wrong_or_rehashed_receipt_cannot_replace_selected_pin(self):
        for updates in [{'sourceId': 'usda-files'}, {'qualified': False}, {'fixture': False}]:
            q = {**self.q, **updates}; q['qualificationSha256'] = fingerprint({k:v for k,v in q.items() if k!='qualificationSha256'})
            with self.subTest(updates=updates), self.assertRaisesRegex(NativeLookupError, 'qualification-pin-mismatch'):
                self.lookup(qualification=q)

    def test_recomputed_selected_held_receipt_still_rejected(self):
        q = {**self.q, 'qualified': False, 'status': 'held', 'errors': ['fixture-held']}
        q['qualificationSha256'] = fingerprint({k:v for k,v in q.items() if k!='qualificationSha256'})
        with self.assertRaisesRegex(NativeLookupError, 'qualification-invalid'):
            self.lookup(qualification=q, qualification_sha256=q['qualificationSha256'])

    def test_contract_scope_or_policy_change_rejected(self):
        for updates in [{'source_id': 'usda-files'}, {'release_id': 'other'}, {'scope_id': 'other'},
                        {'policy_sha256': 'b'*64}, {'fixture': False}]:
            with self.subTest(updates=updates), self.assertRaisesRegex(NativeLookupError, 'qualification-invalid'):
                self.lookup(contract=replace(self.contract, **updates))

    def test_nonprivate_nonnative_held_or_unpermitted_contract_rejected(self):
        for updates in [{'source_id': 'prices'}, {'output_scope': 'curated'}, {'output_visibility': 'public'},
                        {'holds': ('source-held',)}, {'permitted_operations': frozenset(['retain'])}]:
            with self.subTest(updates=updates), self.assertRaisesRegex(NativeLookupError, 'private-native-contract-required'):
                self.lookup(contract=replace(self.contract, **updates))

    def test_changed_bytes_after_matching_row_never_return_partial_success(self):
        raw = self.candidate.read_bytes(); self.candidate.write_bytes(raw.replace(b'zero', b'Zero'))
        with self.assertRaisesRegex(NativeLookupError, 'artifact-pin-or-count-mismatch'): self.lookup()

    def test_no_match_still_requires_complete_verified_artifact(self):
        raw = self.candidate.read_bytes(); self.candidate.write_bytes(raw.replace(b'zero', b'Zero'))
        with self.assertRaisesRegex(NativeLookupError, 'artifact-pin-or-count-mismatch'):
            self.lookup('unmatched-lexical-value')

    def test_ingredients_objects_are_not_silently_stringified(self):
        self.rows[0]['data']['ingredientsText'] = ['not native text']; self.prepare()
        with self.assertRaisesRegex(NativeLookupError, 'ingredients-invalid'):
            self.lookup()

    def test_foreign_source_after_match_fails_closed(self):
        self.rows[1]['provenance']['sourceId'] = 'abc'
        self.candidate.write_bytes(b''.join(canonical([r])+b'\n' for r in self.rows))
        with self.assertRaisesRegex(NativeLookupError, 'record-scope-mismatch'): self.lookup()

    def test_scan_budget_rejected_before_open(self):
        with patch.object(Path, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(NativeLookupError, 'artifact-bound-or-type'): self.lookup(max_scan_bytes=1)

    def test_result_limit_is_error_not_silent_truncation(self):
        for limits in [{'max_matches': 1}, {'max_result_bytes': 1}]:
            with self.subTest(limits=limits), self.assertRaisesRegex(NativeLookupError, 'result-bound'): self.lookup(**limits)

    def test_symlink_candidate_rejected(self):
        link = self.root / 'link'; link.symlink_to(self.candidate)
        with self.assertRaisesRegex(NativeLookupError, 'invalid-input'):
            lookup_native_barcode(link, contract=self.contract, qualification=self.q, qualification_sha256=self.pin, barcode='00012345')

    def test_limits_reject_boolean_zero_and_negative(self):
        for limits in [{'max_scan_bytes': True}, {'max_matches': 0}, {'max_result_bytes': -1}]:
            with self.subTest(limits=limits), self.assertRaisesRegex(NativeLookupError, 'limits-invalid'): self.lookup(**limits)


if __name__ == '__main__': unittest.main()
