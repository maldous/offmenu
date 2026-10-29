"""Authored inventory metadata only; no source bodies or network."""
import copy
import unittest
from offmenu.refresh import adapter_mapping as mapping, coverage, execution, reference_adapters
from test_global_coverage import inventory


def metadata():
    matrix, ledger = inventory()
    for source, sid in zip(ledger['sources'][-3:], mapping.SUPPORT_DOCUMENTS):
        old = source['sourceId']
        source['sourceId'] = sid
        matrix['globalSourceIds'] = [sid if x == old else x for x in matrix['globalSourceIds']]
    return matrix, ledger


class AdapterMappingTests(unittest.TestCase):
    def report(self):
        matrix, ledger = metadata()
        return mapping._annotate(coverage._reconcile(matrix, ledger), ledger)

    def test_fifteen_exact_retained_contracts(self):
        rows = mapping.retained_adapters()
        self.assertEqual(len(rows), 15)
        self.assertEqual({r['sourceId'] for r in rows if r['adapterFamily'] == 'national'}, set(execution.ADAPTERS))
        self.assertEqual({r['sourceId'] for r in rows if r['adapterFamily'] == 'product'}, {'off', 'prices', 'usda-files'})
        references = {r['sourceId']: r for r in rows if r['adapterFamily'] == 'reference'}
        self.assertEqual(set(references), set(reference_adapters.CONTRACTS))
        for sid, (release, fmt, blob) in reference_adapters.CONTRACTS.items():
            self.assertEqual(references[sid]['releaseId'], release)
            self.assertEqual(references[sid]['inputFormat'], fmt)
            self.assertEqual(references[sid]['historicalHandlerEvidence']['gitBlobSha'], blob)
        self.assertTrue(all(not r['productionAdmission'] and r['acceptedRecords'] == 0 for r in rows))

    def test_no_existing_gate_changes(self):
        matrix, ledger = metadata()
        before = coverage._reconcile(matrix, ledger)
        snapshot = copy.deepcopy(before)
        after = mapping._annotate(before, ledger)
        self.assertEqual(before, snapshot)
        for old, new in zip(before['sources'], after['sources']):
            self.assertEqual(old, {k: v for k, v in new.items() if k != 'adapterMapping'})
        self.assertEqual(before['countries'], after['countries'])
        self.assertEqual(before['summary'], after['summary'])
        self.assertFalse(after['executionAuthorized'])
        self.assertFalse(after['adapterMappingPolicy']['aiRefreshAllowed'])
        self.assertGreaterEqual(after['adapterMappingPolicy']['minimumRefreshSeconds'], 30 * 86400)

    def test_support_documents_never_become_payload_routes(self):
        report = self.report()
        rows = {r['sourceId']: r for r in report['sources']}
        for sid, (family, role) in mapping.SUPPORT_DOCUMENTS.items():
            row = rows[sid]
            self.assertIsNone(row['historicalCapability'])
            self.assertEqual(row['adapterMapping']['sourceFamily'], family)
            self.assertEqual(row['adapterMapping']['evidenceRole'], role)
            self.assertEqual(row['adapterMapping']['status'], 'support-document-only')
            self.assertFalse(row['adapterMapping']['payloadRouteAuthorized'])
            self.assertFalse(row['adapterMapping']['discoveryFormatCompatible'])
        self.assertEqual(report['adapterMappingSummary']['supportOnlyDiscoveryLinks'], 3)
        self.assertEqual(report['adapterMappingSummary']['compatibleDiscoveryPayloadBindings'], 0)

    def test_mismatch_holds_and_global_scope_remain(self):
        report = self.report()
        rows = {r['sourceId']: r for r in report['sources']}
        self.assertEqual(rows['discovery:S221']['adapterMapping']['status'], 'discovery-release-mismatch')
        for sid in coverage.HOLDS:
            self.assertEqual(rows[sid]['adapterMapping']['status'], 'held')
            self.assertIsNone(rows[sid]['adapterMapping']['retainedAdapter'])
        off = rows['discovery:S006']['adapterMapping']
        self.assertEqual(off['retainedAdapter']['countryScopeEvidence'], [])
        self.assertFalse(off['countryAcceptanceGranted'])
        self.assertEqual(off['status'], 'retained-format-available-discovery-compatibility-unverified')

    def test_unknown_ids_do_not_inherit_by_host_or_name(self):
        matrix, ledger = metadata()
        unknown = next(s for s in ledger['sources'] if s['sourceId'].startswith('test:'))
        unknown.update(url='https://fdc.nal.usda.gov/download-datasets/', names=['FoodData Central'])
        report = mapping._annotate(coverage._reconcile(matrix, ledger), ledger)
        row = next(r for r in report['sources'] if r['sourceId'] == unknown['sourceId'])
        self.assertEqual(row['adapterMapping']['status'], 'unsupported')
        self.assertIsNone(row['adapterMapping']['retainedAdapter'])

    def test_order_independent_and_missing_document_fails(self):
        matrix, ledger = metadata()
        first = mapping._annotate(coverage._reconcile(matrix, ledger), ledger)
        ledger['sources'].reverse()
        matrix['countries'].reverse()
        self.assertEqual(first, mapping._annotate(coverage._reconcile(matrix, ledger), ledger))
        ledger['sources'] = [s for s in ledger['sources'] if s['sourceId'] != 'discovery:S045']
        with self.assertRaisesRegex(coverage.CoverageError, 'support-document'):
            mapping._annotate(first, ledger)

    def test_descriptors_are_independent_copies(self):
        first = mapping.retained_adapters()
        first[0]['historicalHandlerEvidence']['path'] = 'changed'
        self.assertNotEqual(first, mapping.retained_adapters())
