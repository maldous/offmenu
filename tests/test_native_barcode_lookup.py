"""Synthetic qualified native outputs only; no actual source/index/runtime run."""
import copy
import gzip
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import Asset, SourceContract, canonical, fingerprint, ids_digest, qualify
from offmenu.refresh.native_barcode_lookup import lookup_native_barcode, NativeLookupError
from offmenu.refresh import native_barcode_lookup as retained


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


class RetainedProductShardTests(unittest.TestCase):
    def test_missing_null_and_present_field_pointers_agree_with_indexed_wrappers(self):
        from offmenu.refresh import product_detail_store as store
        for key, name in (('brand', 'brand'), ('ingredientsText', 'ingredientDeclaration')):
            for state, value in (('missing', None), ('null', None), ('present', ''), ('present', '  豆 source  ')):
                with self.subTest(key=key, state=state, value=value):
                    packet = copy.deepcopy(self.packet)
                    if state == 'missing': packet[0]['data'].pop(key, None)
                    else: packet[0]['data'][key] = value
                    self.prepare([packet]); direct = self.load()['sourceProducts'][0]
                    wrappers = [direct['fields'], store._fields(packet, 'off-legacy-paired-gzip'),
                                store._fields(packet, 'off-cached-qualified-pair')]
                    for fields in wrappers:
                        field = fields[name]
                        self.assertEqual(field['state'], state)
                        self.assertEqual(field['fieldPointer'], None if state == 'missing' else '/0/data/' + key)
                        self.assertEqual(field['value'], value)
                        self.assertIsNotNone(field['evidenceSha256'])
                        self.assertEqual(field['sourceFieldState'], 'unknown')
                        self.assertEqual(fields['imageUrlReferences']['state'], 'not-loaded')
                        self.assertIsNone(fields['imageUrlReferences']['fieldPointer'])
                        for entry in fields.values():
                            if entry['fieldPointer'] is None: continue
                            resolved = packet
                            for component in entry['fieldPointer'].lstrip('/').split('/'):
                                resolved = resolved[int(component)] if isinstance(resolved, list) else resolved[component]
                            self.assertEqual(resolved, entry['value'])
                    self.assertEqual(direct['records'], packet)

    """Generated paired projection packets only, never an OFF source shard."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.code = '00012345'
        self.key = hashlib.sha256(self.code.encode()).hexdigest()[:2]
        self.path = self.root / (self.key + '.jsonl.gz')
        self.packet = self.make_packet(self.code, 7)
        self.limits = retained.RetainedProductLimits(1048576, 4194304, 1048576, 100, 262144, 30)
        self.prepare([self.packet])

    def make_packet(self, code, ordinal):
        p = {'sourceId': 'off', 'releaseId': 'fixture-r1', 'archiveSha256': 'a'*64,
             'recordId': code, 'sourceRow': ordinal, 'transform': 'offmenu-bulk/1',
             'fetchedAt': 'fixture producer clock only', 'license': 'fixture-only', 'attribution': 'fixture'}
        product = {'schemaVersion': '1.0', 'kind': 'product', 'id': 'off:product:' + code,
            'countries': ['DE'], 'provenance': copy.deepcopy(p), 'data': {
            'identifiers': [{'system': 'barcode', 'value': code}], 'name': 'Crème 豆',
            'names': {'de': 'Crème 豆'}, 'brand': None, 'pack': {'value': 1.5, 'unit': 'kg', 'label': '1,50 kg'},
            'ingredientsText': '  Milch, 豆\n\u2028Salz  ', 'allergens': ['en:milk'], 'traces': [],
            'labels': ['en:vegetarian'], 'categories': ['en:test'], 'origins': [], 'manufacturingPlaces': [],
            'rawNutriments': {'sugars_100g': '0,10', 'unknown': None}, 'nutritionSourceBasis': None,
            'nutritionId': 'off:nutrientProfile:' + code, 'unknownSourceProjection': {'x': None}}}
        profile = {'schemaVersion': '1.0', 'kind': 'nutrientProfile', 'id': 'off:nutrientProfile:' + code,
            'countries': ['DE'], 'provenance': copy.deepcopy(p),
            'data': {'foodName': 'Crème 豆', 'basis': {'amount': 100, 'unit': 'g', 'state': 'as-sold'},
                     'nutrients': {'sugars': {'value': None, 'sourceAmount': '0,10'}}}}
        return [product, profile]

    def prepare(self, packets, raw=None):
        body = raw if raw is not None else b''.join(canonical(packet) + b'\n' for packet in packets)
        compressed = gzip.compress(body, mtime=0); self.path.write_bytes(compressed)
        info = self.path.stat()
        self.selection = retained.RetainedProductShard('fixture-r1', 'a'*64, 'b'*64, self.key,
            hashlib.sha256(compressed).hexdigest(), len(compressed), len(packets), retained._identity(info),
            'c'*64, 'd'*64, 'e'*64, 'f'*64, frozenset(['retain', 'parse', 'transform']), fixture=True)
        self.observations = [self.observation(7, 11)]

    def observation(self, ordinal, assertion):
        return {'run_id': 'fixture-run', 'input_id': 'parse-derived:off-occurrences:' + 'b'*64,
            'assertion_id': assertion, 'record_ordinal': ordinal, 'lexical_value': self.code,
            'namespace': 'barcode', 'source_id': 'off', 'release_id': 'fixture-r1',
            'artifact_sha256': 'b'*64, 'source_record_id': str(ordinal),
            'native_record_id': 'off:sourceOccurrence:' + 'a'*64 + ':' + str(ordinal),
            'disposition': 'source-asserted' if ordinal == 7 else 'unresolved'}

    def load(self, **changes):
        args = dict(selection=self.selection, observations=self.observations, limits=self.limits)
        args.update(changes); return retained.lookup_retained_off_products(self.path, **args)

    def test_all_details_exact_text_nulls_profiles_and_unknowns_survive_without_mapping(self):
        result = self.load(); detail = result['sourceProducts'][0]; fields = detail['fields']
        self.assertEqual(detail['records'], self.packet)
        self.assertEqual(fields['ingredientDeclaration']['value'], '  Milch, 豆\n\u2028Salz  ')
        self.assertEqual(fields['ingredientDeclaration']['fieldPointer'], '/0/data/ingredientsText')
        self.assertEqual(fields['brand']['state'], 'null')
        self.assertEqual(fields['packageQuantity']['value']['label'], '1,50 kg')
        self.assertEqual(fields['rawNutriments']['value']['sugars_100g'], '0,10')
        self.assertEqual(fields['nutrientProfile']['value'], self.packet[1]['data'])
        self.assertEqual(fields['names']['value'], {'de': 'Crème 豆'})
        self.assertIsNone(fields['name']['language'])
        self.assertEqual(fields['name']['sourceFieldState'], 'unknown')
        self.assertEqual(fields['imageUrlReferences']['state'], 'not-loaded')
        self.assertIsNone(detail['canonicalIngredient']['conceptId'])
        self.assertEqual((result['scannedPackets'], result['scannedRecords']), (1, 2))

    def test_exact_observation_not_barcode_fallback_and_all_observations_retained(self):
        self.observations.append(self.observation(8, 12))
        products = self.load()['sourceProducts']
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]['observationKey']['assertion_id'], 11)
        self.assertEqual(products[1]['fields']['name']['state'], 'not-loaded')
        self.assertIsNone(products[1]['records'])
        self.assertIsNone(products[1]['sourceBinding']['recordPointer'])

    def test_empty_null_missing_are_projection_states_not_original_presence(self):
        self.packet[0]['data']['ingredientsText'] = ''; self.packet[0]['data'].pop('brand')
        self.prepare([self.packet]); fields = self.load()['sourceProducts'][0]['fields']
        self.assertEqual((fields['ingredientDeclaration']['state'], fields['ingredientDeclaration']['value']), ('present', ''))
        self.assertEqual(fields['brand']['state'], 'missing')
        self.assertEqual(fields['brand']['sourceFieldState'], 'unknown')

    def test_wrong_profile_source_ordinal_release_and_schema_fail_closed(self):
        original = copy.deepcopy(self.packet)
        for part, key, value in [(1, 'sourceRow', 8), (1, 'releaseId', 'other'), (0, 'archiveSha256', '9'*64)]:
            with self.subTest(part=part, key=key):
                packet = copy.deepcopy(original); packet[part]['provenance'][key] = value; self.prepare([packet])
                with self.assertRaises(NativeLookupError): self.load()
        packet = copy.deepcopy(original); packet[0]['data']['nutritionId'] = 'off:wrong'
        self.prepare([packet])
        with self.assertRaisesRegex(NativeLookupError, 'profile-binding'): self.load()

    def test_late_hash_change_crc_and_truncated_gzip_never_return_partial_details(self):
        self.prepare([self.packet]); self.selection = replace(self.selection, sha256='9'*64)
        with self.assertRaisesRegex(NativeLookupError, 'hash-or-count'): self.load()
        for transform in (lambda b: b[:-4], lambda b: b[:-8] + bytes([b[-8] ^ 1]) + b[-7:]):
            self.prepare([self.packet]); data = transform(self.path.read_bytes()); self.path.write_bytes(data)
            self.selection = replace(self.selection, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), identity=retained._identity(self.path.stat()))
            with self.assertRaises(NativeLookupError): self.load()

    def test_finite_bounds_deadline_and_count_fail_without_partial_result(self):
        for changes in ({'max_packet_bytes': 10}, {'max_expanded_bytes': 100, 'max_packet_bytes': 100},
                        {'max_result_bytes': 10}, {'max_compressed_bytes': 1}):
            with self.subTest(changes=changes), self.assertRaises(NativeLookupError):
                self.load(limits=replace(self.limits, **changes))
        with self.assertRaisesRegex(NativeLookupError, 'hash-or-count'):
            self.load(selection=replace(self.selection, packets=2))
        with patch.object(retained.time, 'monotonic', side_effect=[100.0, 1000.0]):
            with self.assertRaisesRegex(NativeLookupError, 'time-bound'): self.load()

    def test_observation_and_permission_holds_fail_before_file_open(self):
        with patch.object(retained.os, 'open', side_effect=AssertionError('must not open')):
            for selection in (replace(self.selection, holds=('fixture-held',)),
                              replace(self.selection, permitted_operations=frozenset(['retain']))):
                with self.assertRaisesRegex(NativeLookupError, 'selection-invalid-or-held'): self.load(selection=selection)
            for changes in ({'lexical_value': 12345}, {'source_record_id': '8'}, {'artifact_sha256': '9'*64}):
                with self.assertRaisesRegex(NativeLookupError, 'observation-binding'):
                    self.load(observations=[{**self.observations[0], **changes}])

    def test_duplicate_packets_identity_changes_symlink_and_no_match_still_verify(self):
        self.prepare([self.packet, self.packet])
        with self.assertRaisesRegex(NativeLookupError, 'duplicate-native-key'): self.load()
        self.prepare([self.packet]); self.observations = [self.observation(999, 11)]
        self.selection = replace(self.selection, sha256='9'*64)
        with self.assertRaisesRegex(NativeLookupError, 'hash-or-count'): self.load()
        self.prepare([self.packet]); self.selection = replace(self.selection, identity=(0, 0, self.selection.bytes, 0, 0))
        with self.assertRaisesRegex(NativeLookupError, 'custody'): self.load()
        self.prepare([self.packet]); moved = self.root / 'original'; self.path.rename(moved); self.path.symlink_to(moved)
        with self.assertRaises(NativeLookupError): self.load()

    def test_reusable_different_code_and_final_deadline_before_return(self):
        other = next(str(n) for n in range(1000, 10000)
                     if hashlib.sha256(str(n).encode()).hexdigest()[:2] == self.key)
        packet = self.make_packet(other, 42); self.prepare([packet])
        row = self.observation(42, 12); row['lexical_value'] = other
        self.observations = [row]
        self.assertEqual(self.load()['sourceProducts'][0]['records'], packet)
        project = retained._retained_details
        with patch.object(retained.time, 'monotonic', return_value=100.0) as clock:
            def slow(*args):
                value = project(*args); clock.return_value = 1000.0; return value
            with patch.object(retained, '_retained_details', side_effect=slow):
                with self.assertRaisesRegex(NativeLookupError, 'time-bound'): self.load()


if __name__ == '__main__': unittest.main()
