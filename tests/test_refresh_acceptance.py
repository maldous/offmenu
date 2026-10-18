import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.acceptance import (Asset, SourceContract, CellRequirement, accept,
                                       qualify, assess_cells, canonical, fingerprint, ids_digest)


def semantics(row):
    data = row.get('data', {})
    return [] if data.get('unit') == 'g' and data.get('basis') == 'per-100g' else ['unit-or-basis-unreviewed']


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        (self.bundle / 'csv').mkdir()
        assets = []
        for name, body in [('csv/input.csv', b'id,value\na,0\nb,2\n'),
                           ('rights.json', b'reviewed retain parse derive scope'),
                           ('scope.json', b'independent a,b inventory')]:
            (self.bundle / name).write_bytes(body)
            assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
        self.rows = [{'id': x, 'kind': 'nutrientProfile', 'schemaVersion': '1.0',
                      'data': {'value': value, 'unit': 'g', 'basis': 'per-100g'},
                      'provenance': {'sourceId': 'test-source', 'releaseId': '2026',
                                     'fetchedAt': '2026-10-01T00:00:00Z'}} for x, value in [('a', 0), ('b', 2)]]
        schemas = {'nutrientProfile': {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                   'properties': {'schemaVersion': {'const': '1.0'},
                                  'data': {'type': 'object', 'required': ['value', 'unit', 'basis'],
                                           'properties': {'value': {'type': ['number', 'null'], 'minimum': 0}}}}}}
        self.contract = SourceContract('test-source', '2026', 'complete-selected-native',
                                      '2026-10-01T00:00:00Z', tuple(assets), 2,
                                      ids_digest(['a', 'b']), schemas, fingerprint(schemas), semantics,
                                      'a' * 64, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                                      fixture=True)
        self.candidate = self.root / 'candidate.jsonl'
        self.write_rows(self.rows)

    def write_rows(self, rows):
        body = b''.join(canonical([r]) + b'\n' for r in rows)
        self.candidate.write_bytes(body)
        self.manifest = {'sourceId': self.contract.source_id, 'releaseId': self.contract.release_id,
                         'acquiredAt': self.contract.acquired_at, 'normalizedRecords': 2,
                         'candidateSha256': hashlib.sha256(body).hexdigest(), 'candidateBytes': len(body),
                         'rightsEvidenceSha256': self.contract.rights_evidence.sha256,
                         'scopeEvidenceSha256': self.contract.scope_evidence.sha256,
                         'inputFiles': [vars(a) for a in self.contract.inputs]}

    def run_accept(self, contract=None):
        return accept(contract or self.contract, self.bundle, self.candidate, self.manifest)

    def test_positive_deterministic_fixture_only(self):
        result = self.run_accept()
        self.assertTrue(result['accepted'])
        self.assertEqual(result['acceptedCount'], 2)
        self.assertFalse(result['productionAccepted'])
        self.assertEqual(result, self.run_accept())
        self.assertEqual(result['status'], 'accepted-fixture-scope')

    def test_partial_fixture_never_accepted(self):
        self.write_rows(self.rows[:1])
        result = self.run_accept()
        self.assertFalse(result['accepted'])
        self.assertIn('expected-record-count-mismatch', result['errors'])
        self.assertIn('expected-record-identities-mismatch', result['errors'])
        self.assertIsNone(result['acceptedCount'])

    def test_all_row_diagnostics_and_identity(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['data']['unit'] = 'unknown'
        rows[1]['provenance']['sourceId'] = 'foreign'
        rows[1]['id'] = 'a'
        rows[1]['schemaVersion'] = '2'
        self.write_rows(rows)
        errors = self.run_accept()['errors']
        for expected in ['unit-or-basis-unreviewed', 'record-provenance-mismatch',
                         'record-identity-duplicate', 'record-schema-invalid', 'expected-record-identities-mismatch']:
            self.assertIn(expected, errors)

    def test_custody_and_extra_nested_assets(self):
        (self.bundle / 'csv/input.csv').write_bytes(b'changed')
        (self.bundle / 'csv/extra.csv').write_bytes(b'new')
        self.candidate.write_bytes(self.candidate.read_bytes() + b'[]\n')
        errors = self.run_accept()['errors']
        for code in ['input-custody-mismatch', 'input-inventory-mismatch', 'candidate-custody-mismatch', 'record-invalid']:
            self.assertIn(code, errors)

    def test_operation_rights_and_holds_not_waived(self):
        c = replace(self.contract, permitted_operations=frozenset(('retain', 'parse')), holds=('semantic-hold',))
        result = self.run_accept(c)
        self.assertFalse(result['accepted'])
        self.assertIn('operation-rights-missing', result['errors'])
        self.assertIn('source-held', result['errors'])
        c = replace(self.contract, output_scope='curated', output_visibility='public')
        self.assertIn('publication-operation-rights-required', self.run_accept(c)['errors'])

    def test_schema_pin_and_remote_refs_fail_closed(self):
        schemas = {'nutrientProfile': {'$ref': 'https://example.invalid/schema'}}
        c = replace(self.contract, schemas=schemas, schemas_sha256=fingerprint(schemas))
        self.assertFalse(self.run_accept(c)['accepted'])
        self.assertFalse(self.run_accept(replace(self.contract, schemas_sha256='f' * 64))['accepted'])

    def test_unsafe_and_missing_assets_rejected(self):
        c = replace(self.contract, inputs=(Asset('../input', 0, 'a' * 64),))
        self.assertFalse(self.run_accept(c)['accepted'])
        (self.bundle / 'csv/input.csv').unlink()
        (self.bundle / 'csv/input.csv').symlink_to(self.bundle / 'rights.json')
        self.assertFalse(self.run_accept()['accepted'])

    def test_reaccept_revalidates_bytes(self):
        self.assertTrue(self.run_accept()['accepted'])
        self.candidate.write_bytes(b'[]\n')
        self.assertFalse(self.run_accept()['accepted'])

    def test_no_source_schema_or_semantic_validator_no_acceptance(self):
        self.assertFalse(self.run_accept(replace(self.contract, schemas={}))['accepted'])
        self.assertFalse(self.run_accept(replace(self.contract, semantic_validator=None))['accepted'])

    def test_country_contract_required_and_fixture_barred(self):
        receipt = self.run_accept()
        requirement = CellRequirement('AU', 'nutrition', (('test-source', '2026', 'complete-selected-native', receipt['qualificationSha256']),), 'b' * 64, 'c' * 64)
        result = assess_cells([requirement], [receipt], countries=['AU'], domains=['nutrition'])
        self.assertEqual(result['acceptedCountryDomainCells'], 0)
        self.assertFalse(result['countryCoverageComplete'])

    def test_country_acceptance_has_reachable_nonzero_path(self):
        # Synthetic test of the production contract path; no production admission installed.
        receipt = self.run_accept(replace(self.contract, fixture=False))
        requirement = CellRequirement('AU', 'nutrition', (('test-source', '2026', 'complete-selected-native', receipt['qualificationSha256']),), 'b' * 64, 'c' * 64)
        result = assess_cells([requirement], [receipt], countries=['AU'], domains=['nutrition', 'recipes'])
        self.assertEqual(result['acceptedCountryDomainCells'], 1)
        self.assertFalse(result['countryCoverageComplete'])
        result = assess_cells([requirement], [receipt], countries=['AU'], domains=['nutrition'])
        self.assertTrue(result['countryCoverageComplete'])
        wrong = replace(requirement, sources=(('test-source', '2025', 'complete-selected-native', receipt['qualificationSha256']),))
        self.assertEqual(assess_cells([wrong], [receipt], countries=['AU'], domains=['nutrition'])['acceptedCountryDomainCells'], 0)

    def test_endstate_requires_distinct_reviewed_transformations(self):
        from offmenu.refresh.acceptance import CandidateArtifact, endstate_handlers
        from offmenu.refresh.global_run import StageContext, Limits
        contract = replace(self.contract, required_operations=frozenset(('retain', 'parse', 'transform', 'serve', 'redistribute')),
                           permitted_operations=frozenset(('retain', 'parse', 'transform', 'serve', 'redistribute')))
        native = CandidateArtifact(contract, self.bundle, self.candidate, self.manifest)
        receipts = {}
        def projection(context, previous):
            scope = 'curated' if context.stage == 'curate' else 'common'
            return replace(previous, contract=replace(previous.contract, output_scope=scope, scope_id=scope))
        handlers, state = endstate_handlers(lambda context: native, projection, projection, receipts)
        for stage in ('validate', 'curate', 'graph', 'qualify', 'accept'):
            context = StageContext('test-source', stage, Limits(), None, False, ())
            self.assertEqual(handlers[stage](context).status, 'succeeded')
        self.assertEqual(len(receipts), 1)
        self.assertFalse(next(iter(receipts.values()))['productionAccepted'])
        missing, state = endstate_handlers(lambda context: native, None, None, {})
        context = StageContext('test-source', 'curate', Limits(), None, False, ())
        self.assertEqual(missing['curate'](context).status, 'unsupported')

    def test_nonfinite_and_tight_budget_fail_closed(self):
        self.candidate.write_bytes(self.candidate.read_bytes().replace(b'"value":0', b'"value":1e999'))
        self.assertFalse(self.run_accept()['accepted'])
        from offmenu.refresh.acceptance import CandidateArtifact, endstate_handlers
        from offmenu.refresh.global_run import StageContext, Limits
        artifact = CandidateArtifact(self.contract, self.bundle, self.candidate, self.manifest)
        handlers, _ = endstate_handlers(lambda c: artifact, None, None, {})
        context = StageContext('test-source', 'validate', Limits(input_bytes=1), None, False, ())
        self.assertEqual(handlers['validate'](context).code, 'artifact-byte-budget-exceeded')

    def test_wrong_source_binding_and_duplicate_json_keys(self):
        from offmenu.refresh.acceptance import CandidateArtifact, endstate_handlers
        from offmenu.refresh.global_run import StageContext, Limits
        artifact = CandidateArtifact(self.contract, self.bundle, self.candidate, self.manifest)
        handlers, _ = endstate_handlers(lambda c: artifact, None, None, {})
        context = StageContext('foreign', 'validate', Limits(), None, False, ())
        self.assertEqual(handlers['validate'](context).code, 'artifact-source-binding-mismatch')
        handlers, _ = endstate_handlers(lambda c: artifact, None, None, {}, discovery_id='discovery:S001')
        context = replace(context, source_id='discovery:S001')
        self.assertEqual(handlers['validate'](context).status, 'succeeded')
        self.candidate.write_bytes(self.candidate.read_bytes().replace(b'"value":0', b'"value":1,"value":0'))
        self.assertIn('record-invalid', self.run_accept()['errors'])

    def test_acceptance_receipt_tamper_not_country_evidence(self):
        receipt = self.run_accept(replace(self.contract, fixture=False))
        receipt['candidateSha256'] = 'f' * 64
        req = CellRequirement('AU', 'nutrition', (('test-source', '2026', 'complete-selected-native', receipt['qualificationSha256']),), 'b'*64, 'c'*64)
        self.assertFalse(assess_cells([req], [receipt], countries=['AU'], domains=['nutrition'])['countryCoverageComplete'])

    def test_global_wiring_requires_current_accept_stage_evidence(self):
        from offmenu.refresh.acceptance import CandidateArtifact, endstate_handlers
        from offmenu.refresh.global_run import Binding, StageResult, STAGES, run
        from offmenu.refresh.coverage import COUNTRIES, DOMAINS
        contract = replace(self.contract, fixture=False)
        native = CandidateArtifact(contract, self.bundle, self.candidate, self.manifest)
        receipts = {}
        def projection(context, previous):
            scope = 'curated' if context.stage == 'curate' else 'common'
            return replace(previous, contract=replace(previous.contract, output_scope=scope, scope_id=scope))
        handlers, state = endstate_handlers(lambda c: native, projection, projection, receipts)
        handlers = {**{stage: lambda c: StageResult('succeeded', evidence=('a'*64,)) for stage in STAGES}, **handlers}
        common = replace(contract, output_scope='common', scope_id='common')
        predicted = self.run_accept(common)
        requirement = CellRequirement('AU', 'food_composition',
                    (('test-source', '2026', 'common', predicted['qualificationSha256']),), 'b'*64, 'c'*64)
        coverage = {'countries': [{'iso2': c, 'domains': {d: {} for d in DOMAINS}} for c in COUNTRIES],
                    'domainNames': list(DOMAINS), 'sources': [{'sourceId': 'test-source'}]}
        binding = Binding(handlers, 'reviewed', True, state)
        report = run(coverage, bindings={'test-source': binding},
                     cell_requirements=[requirement], acceptance_receipts=receipts)
        self.assertEqual(report['summary']['acceptedCountryDomainCells'], 1)
        self.assertEqual(report['sources'][0]['acceptedCount'], 2)
        self.assertTrue(report['sources'][0]['normalizedCandidate'])
        self.assertIn('validate', report['sources'][0]['qualificationResults'])
        self.assertFalse(report['countryCoverageComplete'])
        # Reusing a binding after a successful run cannot display stale acceptance.
        binding.handlers['accept'] = lambda c: StageResult('failed', 'synthetic-failure')
        failed = run(coverage, bindings={'test-source': binding},
                     cell_requirements=[requirement], acceptance_receipts=receipts)
        self.assertIsNone(failed['sources'][0]['sourceAcceptance'])
        self.assertIsNone(failed['sources'][0]['acceptedCount'])
        self.assertEqual(failed['summary']['acceptedCountryDomainCells'], 0)
        # A stored receipt is insufficient when this run did not finish acceptance.
        report = run(coverage, cell_requirements=[requirement], acceptance_receipts=receipts)
        self.assertEqual(report['summary']['acceptedCountryDomainCells'], 0)

    def test_manifest_reordering_does_not_change_acceptance(self):
        self.manifest['inputFiles'].reverse()
        self.assertTrue(self.run_accept()['accepted'])

if __name__ == '__main__':
    unittest.main()
