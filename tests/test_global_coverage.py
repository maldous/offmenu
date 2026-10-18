"""Synthetic-only coverage contract tests; no publisher or dataset access."""
import copy
import tempfile
import unittest
from pathlib import Path
from offmenu.refresh import coverage


def inventory():
    mapped = sorted({sid for r in coverage.RELEASES for sid in r['discoveryIds']})
    ids = mapped + [f'test:{i}' for i in range(1303 - len(mapped))]
    sources = [{'sourceId': sid, 'countries': [], 'accessEvidence': {'httpStatus': 200}}
               for sid in ids]
    matrix = {'countries': [{'iso2': code, 'sourceIds': ids[:1]} for code in coverage.COUNTRIES],
              'domainDefaults': {domain: {} for domain in coverage.DOMAINS},
              'globalSourceIds': ids[-1:]}
    return matrix, {'sources': sources, 'sourceCount': 1303}


class CoverageTests(unittest.TestCase):
    def test_exhaustive_no_false_acceptance(self):
        report = coverage._reconcile(*inventory())
        self.assertEqual(len(report['countries']), 249)
        self.assertEqual(report['summary']['requiredCountryDomainCells'], 3237)
        self.assertEqual(report['summary']['wholeCountryAcceptances'], 0)
        self.assertEqual(report['summary']['heldSources'], 4)
        self.assertEqual(len(report['sources']), 1303)
        for country in report['countries']:
            self.assertEqual(len(country['domains']), 13)
            self.assertFalse(country['countryCoverageComplete'])
            for domain in country['domains'].values():
                self.assertEqual(domain['status'], 'unassessed')
                self.assertIsInstance(domain['sourceIds'], list)
        self.assertTrue(all(s['handlerBinding'] is None for s in report['sources']))
        self.assertTrue(all(not s['historicalLandingEvidence']['payloadVerified'] for s in report['sources']))

    def test_historical_capabilities_are_not_admission(self):
        report = coverage._reconcile(*inventory())
        self.assertEqual(report['summary']['sourceFamilyMappings'], 23)
        self.assertEqual(report['summary']['sourcesWithHistoricalHandlers'], 22)
        self.assertEqual(report['summary']['retainedReleasesWithHandlers'], 21)
        self.assertTrue(all(not r['executable'] for r in report['retainedReleases']))
        rows = {r['sourceId']: r for r in report['sources']}
        self.assertEqual(rows['discovery:S221']['normalizationStatus'], 'unsupported')
        self.assertEqual(rows['discovery:S221']['historicalCapability']['releaseId'], '2015')
        for sid in coverage.HOLDS:
            self.assertEqual(rows[sid]['normalizationStatus'], 'held')
        self.assertEqual(rows['discovery:S327']['historicalCapability']['sourceId'], 'afcd')
        self.assertEqual(rows['discovery:S164']['historicalCapability']['sourceId'], 'mext')
        self.assertEqual(len(report['supportingHandlers']), 5)

    def test_order_independence(self):
        matrix, ledger = inventory()
        expected = coverage._reconcile(matrix, ledger)
        matrix['countries'].reverse()
        ledger['sources'].reverse()
        self.assertEqual(expected, coverage._reconcile(matrix, ledger))

    def test_unknown_and_duplicate_country(self):
        for code in ('ZZ', 'AD'):
            matrix, ledger = inventory()
            matrix['countries'][-1]['iso2'] = code
            with self.assertRaisesRegex(coverage.CoverageError, 'country-set'):
                coverage._reconcile(matrix, ledger)

    def test_missing_domain_source_and_global_reference(self):
        for kind in ('domain', 'source', 'global', 'link'):
            matrix, ledger = inventory()
            if kind == 'domain':
                matrix['domainDefaults'].pop('recipes')
            elif kind == 'source':
                ledger['sources'].pop()
            elif kind == 'global':
                matrix['globalSourceIds'] = ['missing']
            else:
                matrix['countries'][0]['sourceIds'] = ['missing']
            with self.assertRaises(coverage.CoverageError):
                coverage._reconcile(matrix, ledger)

    def test_no_implicit_global_country_inheritance(self):
        report = coverage._reconcile(*inventory())
        global_row = next(s for s in report['sources'] if s['globalRoute'])
        self.assertEqual(global_row['countries'], [])
        self.assertEqual(global_row['domains'], [])

    def test_missing_altered_and_symlink_inventory_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'matrix.json'
            with self.assertRaisesRegex(coverage.CoverageError, 'unavailable'):
                coverage.assess(path, path)
            path.write_text('{}')
            with self.assertRaisesRegex(coverage.CoverageError, 'pin-mismatch'):
                coverage.assess(path, path)
            link = Path(temporary) / 'linked.json'
            link.symlink_to(path)
            with self.assertRaisesRegex(coverage.CoverageError, 'symlink'):
                coverage.assess(link, path)


if __name__ == '__main__':
    unittest.main()
