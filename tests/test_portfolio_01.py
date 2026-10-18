"""Authored fixtures only: no country source files or network are accessed."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha, strict_json
from offmenu.refresh import portfolio_01 as p
from offmenu.refresh.portfolio_01_contract import CONTRACT

NOW = '2026-10-18T00:00:00Z'


def metadata(country='AI'):
    declaration = CONTRACT['countries'][country]
    return {'receiptPins': copy.deepcopy(declaration['receiptPins']),
            'acquiredAt': declaration['acquiredAt'], 'lastValidatedAt': NOW}


def fixture(period='2012'):
    data = {**p.CONSTANTS, 'period': period, 'value': 105.25,
            'originalXMLNumericLexical': '105.250', 'publisherGroupCode': 11.01,
            'publisherLabel': 'Food And Non-Alcoholic Beverages'}
    column = p.SELECTORS['columns'][int(period) - 2010]
    return {'id': f'{p.FIXTURE_SOURCE}:{period}', 'kind': 'synthetic-cpi-observation',
            'schemaVersion': p.VERSION, 'data': data,
            'provenance': {'sourceId': p.FIXTURE_SOURCE, 'releaseId': p.FIXTURE_RELEASE,
                'fieldOrigins': p.cpi_origins(column, p.FIXTURE_SOURCE, p.FIXTURE_RELEASE,
                                            p.FIXTURE_INPUT, p.FIXTURE_SHA)}}


class Portfolio01Tests(unittest.TestCase):
    def test_valid_fixture_shared_serialization_and_origins(self):
        row = fixture()
        raw = p.stage_authored_fixture(row)
        self.assertEqual(raw, canonical([row]))
        self.assertEqual(strict_json(raw)[0]['data']['originalXMLNumericLexical'], '105.250')
        self.assertEqual(p.stage_authored_fixture(row), raw)
        self.assertEqual(p.field_origin_errors(row, {p.FIXTURE_INPUT: p.FIXTURE_SHA},
                         policy_pins=(p.POLICY_SHA,)), [])

    def test_null_is_preserved_without_imputation(self):
        row = fixture()
        row['data']['value'] = row['data']['originalXMLNumericLexical'] = None
        self.assertIsNone(strict_json(p.stage_authored_fixture(row))[0]['data']['value'])
        self.assertIsNone(row['data']['currency'])
        self.assertIsNone(row['data']['physicalQuantity'])

    def test_scope_native_units_and_exact_selectors_are_enforced(self):
        changes = [('unit', 'GBP'), ('base', 'per-100g'), ('currentOffer', True),
                   ('currency', 'XCD'), ('physicalQuantity', 1),
                   ('period', '2026'), ('value', True), ('value', float('nan')),
                   ('originalXMLNumericLexical', '105.26'), ('publisherLabel', 'Food')]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                row = fixture(); row['data'][field] = value
                with self.assertRaises(RefreshError): p.stage_authored_fixture(row)
        for field in ('sourceField', 'inputSha256', 'sourceRecordId'):
            row = fixture()
            row['provenance']['fieldOrigins']['/data/value'][field] = 'wrong'
            with self.assertRaises(RefreshError): p.stage_authored_fixture(row)
        row = fixture(); del row['provenance']['fieldOrigins']['/data/currency']
        with self.assertRaises(RefreshError): p.stage_authored_fixture(row)

    def test_retained_source_cannot_enter_fixture_adapter(self):
        row = fixture(); row['provenance']['sourceId'] = '6da4880fe235645f4c26'
        with self.assertRaisesRegex(RefreshError, 'portfolio-fixture-identity-invalid'):
            p.stage_authored_fixture(row)

    def test_real_metadata_valid_but_use_held_without_io(self):
        with patch('builtins.open', side_effect=AssertionError('source I/O forbidden')), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = p.plan('AI', metadata(), now=NOW)
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['sourceRecordsProcessed'], 0)
        self.assertFalse(result['sourceProcessingAllowed'])
        self.assertFalse(result['goldAdmitted'])
        self.assertFalse(result['countryComplete'])
        self.assertFalse(result['cache']['bodyVerifiedThisRun'])

    def test_missing_and_malformed_isolate_each_country(self):
        results = p.plan_portfolio({'AI': {'secret': 'must-not-leak'}, 'AG': metadata('AG')}, now=NOW)
        self.assertEqual(results['AI']['status'], 'quarantined')
        self.assertEqual(results['AG']['code'], 'portfolio-source-use-held')
        self.assertEqual(results['AD']['code'], 'portfolio-metadata-missing')
        self.assertEqual(results['AL']['code'], 'portfolio-metadata-missing')
        self.assertNotIn('must-not-leak', json.dumps(results))

    def test_trusted_pins_and_permissions_cannot_be_supplied(self):
        for mutation in ('rightsApproved', 'pin', 'acquiredAt'):
            data = metadata()
            if mutation == 'rightsApproved': data['rightsApproved'] = True
            elif mutation == 'pin': data['receiptPins'][0]['sha256'] = '0' * 64
            else: data['acquiredAt'] = NOW
            self.assertEqual(p.plan('AI', data, now=NOW)['status'], 'quarantined')

    def test_minimum_reuse_for_every_explicit_fetch_mode(self):
        for mode in ('reuse', 'refresh', 'revalidate', 'force-download'):
            r = p.plan('AI', metadata(), now=NOW, fetch_policy=mode)
            self.assertEqual(r['cache']['decision'], 'reuse-window-no-download')
            self.assertFalse(r['networkAllowed'])
        r = p.plan('AI', metadata(), now='2026-11-13T21:17:45.188626Z')
        self.assertEqual(r['cache']['acquisitionAgeSeconds'], p.MIN_TTL)
        self.assertEqual(r['cache']['decision'], 'stale-conditional-review-required')
        self.assertEqual(r['status'], 'held')
        self.assertFalse(r['networkAllowed'])

    def test_validation_does_not_reset_acquisition_age_or_content_key(self):
        first = p.plan('AI', metadata(), now=NOW)
        updated = metadata(); updated['lastValidatedAt'] = '2026-10-19T00:00:00Z'
        second = p.plan('AI', updated, now='2026-10-19T00:00:00Z', previous_key=first['metadataKey'])
        self.assertEqual(second['metadataKey'], first['metadataKey'])
        self.assertEqual(second['replay'], 'metadata-no-op')
        self.assertEqual(second['cache']['acquisitionAgeSeconds'] - first['cache']['acquisitionAgeSeconds'], 86400)
        self.assertEqual(second['cache']['validationAgeSeconds'], 0)
        self.assertEqual(p.plan('AI', updated, now=NOW)['status'], 'quarantined')
        changed = copy.deepcopy(CONTRACT)
        changed['countries']['AI']['holds'].append('new-hold')
        with patch.object(p, 'CONTRACT', changed):
            self.assertNotEqual(p.plan('AI', updated, now='2026-10-19T00:00:00Z')['metadataKey'], first['metadataKey'])

    def test_unknown_acquisition_time_not_fabricated_and_inventory_not_admitted(self):
        for country in ('AD', 'AG', 'AL'):
            r = p.plan(country, metadata(country), now=NOW)
            self.assertIsNone(r['cache']['acquisitionAgeSeconds'])
            self.assertEqual(r['cache']['decision'], 'acquisition-time-missing')
        self.assertEqual(sum(len(v['dataTypes']) for v in CONTRACT['countries'].values()), 24)
        self.assertTrue(all(not v['wholeCategoryAccepted'] for c in CONTRACT['countries'].values()
                            for v in c['dataTypes'].values()))

    def test_cli_deterministic_bounded_and_redacted(self):
        command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio_01', '--country', 'AI', '--now', NOW]
        request = canonical({'metadata': metadata(), 'previousKey': None, 'fetchPolicy': 'reuse'})
        runs = [subprocess.run(command, input=request, capture_output=True, check=True).stdout for _ in range(2)]
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(strict_json(runs[0])['status'], 'held')
        for invalid in (b'{"metadata":null,"metadata":null}', b'{"x":NaN}', b'x'*65537,
                        b'{"secret":"must-not-leak"}'):
            r = subprocess.run(command, input=invalid, capture_output=True)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn(b'must-not-leak', r.stdout + r.stderr)
            self.assertEqual(strict_json(r.stdout)['status'], 'quarantined')


if __name__ == '__main__':
    unittest.main()
