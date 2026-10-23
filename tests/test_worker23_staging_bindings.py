"""Small authored metadata only; no private filesystem or real body required."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import core
from offmenu.refresh.portfolios import worker23 as binding


class Worker23BindingTests(unittest.TestCase):
    def setUp(self):
        self.raw = core.canonical({'country': 'CI', 'value': 0, 'unknown': None,
                                   'a/b': {'~value': 'source-native'}})
        self.spec = {'id': 'authored-ci-metadata', 'country': 'CI',
                     'sourceId': 'authored-ci', 'releaseId': 'fixture-only',
                     'metadataAsset': {'path': '/unused/fixture.json',
                                       'sha256': core.sha(self.raw), 'bytes': len(self.raw),
                                       'role': 'retained-metadata'},
                     'selectors': {'value': '/value', 'unknown': '/unknown',
                                   'escaped': '/a~1b/~0value'},
                     'nativeSemantics': {'basis': None, 'unit': None},
                     'originalAcquiredAt': '2026-10-01T00:00:00Z',
                     'metadataValidatedAt': '2026-10-02T00:00:00Z',
                     'payloadHolds': [], 'payloadAdapter': None}
        self.now = '2026-10-18T00:00:00Z'

    def assess(self, spec=None, raw=None, **kw):
        return binding.assess(spec or self.spec, self.raw if raw is None else raw,
                              now=kw.pop('now', self.now), **kw)

    def test_valid_scalar_projection_and_shared_origin_validation(self):
        result = self.assess()
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(result['packet']['data'],
                         {'value': 0, 'unknown': None, 'escaped': 'source-native'})
        self.assertFalse(result['payloadOperationAuthorized'])
        self.assertFalse(result['countryComplete'])
        self.assertEqual(result['acceptedRecords'], 0)
        self.assertEqual(result['cache']['networkRequests'], 0)

    def test_repeat_validation_and_clock_do_not_change_content_identity(self):
        first = self.assess()
        again = self.assess(previous_key=first['contentKey'], now='2026-10-19T00:00:00Z')
        self.assertEqual(first['packet'], again['packet'])
        self.assertEqual(again['replay'], 'no-op')
        self.assertFalse(again['emitPacket'])
        self.assertNotEqual(first['cache'], again['cache'])
        spec = deepcopy(self.spec)
        spec['metadataValidatedAt'] = '2026-10-17T00:00:00Z'
        self.assertEqual(first['contentKey'], self.assess(spec)['contentKey'])
        changed = self.assess(code_pins={'worker23': 'a' * 64})
        self.assertNotEqual(first['contentKey'], changed['contentKey'])

    def test_missing_metadata_and_acquisition(self):
        missing = binding.assess(self.spec, None, now=self.now)
        self.assertEqual(missing['status'], 'missing')
        spec = deepcopy(self.spec)
        spec['originalAcquiredAt'] = None
        self.assertEqual(self.assess(spec)['cache']['status'], 'missing')
        self.assertEqual(self.assess(spec, operation='payload-stage')['status'], 'missing')

    def test_payload_hold_preserved_without_blocking_metadata(self):
        spec = deepcopy(self.spec)
        spec['payloadHolds'] = ['actual-denial-no-retry']
        self.assertEqual(self.assess(spec)['status'], 'valid')
        result = self.assess(spec, operation='payload-stage')
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['payloadHolds'], ['actual-denial-no-retry'])

    def test_stale_at_exact_30_days_validation_does_not_reset_age(self):
        spec = deepcopy(self.spec)
        spec['metadataValidatedAt'] = '2026-10-30T23:59:59Z'
        result = self.assess(spec, now='2026-10-31T00:00:00Z', operation='payload-stage')
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['cache']['acquisitionAgeSeconds'], 30 * 86400)
        under = self.assess(now='2026-10-30T23:59:59Z')
        self.assertEqual(under['cache']['decision'], 'reuse-retained-no-download')

    def test_fresh_metadata_never_supplies_payload_adapter(self):
        result = self.assess(operation='payload-stage')
        self.assertEqual(result['diagnostics'], ['payload-adapter-not-bound'])
        self.assertFalse(result['payloadOperationAuthorized'])

    def test_wrong_pin_missing_selector_bad_country_fail_closed(self):
        for field, value in [('sha256', 'a' * 64), ('bytes', 10), ('role', 'source-body')]:
            spec = deepcopy(self.spec)
            spec['metadataAsset'][field] = value
            self.assertEqual(self.assess(spec)['status'], 'malformed')
        for selectors in ({'x': '/absent'}, {'x': '/a/b'}, {'x': '/a~2b'}, {'x': '/a~1b'}):
            spec = deepcopy(self.spec)
            spec['selectors'] = selectors
            self.assertEqual(self.assess(spec)['status'], 'malformed')
        spec = deepcopy(self.spec)
        spec['country'] = 'CK'
        self.assertEqual(self.assess(spec)['status'], 'malformed')

    def test_malformed_json_duplicate_keys_and_nonfinite(self):
        for raw in (b'{', b'{"country":"CI","value":0,"value":1}',
                    b'{"country":"CI","value":NaN}', b'[]'):
            spec = deepcopy(self.spec)
            spec['metadataAsset'].update(sha256=core.sha(raw), bytes=len(raw))
            result = self.assess(spec, raw)
            self.assertEqual(result['status'], 'malformed')
            self.assertIsNone(result['packet'])

    def test_bad_future_or_naive_timestamps_do_not_succeed(self):
        for value in ('not-a-date', '2026-10-19T00:00:00Z', '2026-10-01T00:00:00'):
            spec = deepcopy(self.spec)
            spec['originalAcquiredAt'] = value
            self.assertEqual(self.assess(spec)['status'], 'malformed')

    def test_acquisition_metadata_pin_and_timestamp_are_verified(self):
        raw = core.canonical({'acquired': self.spec['originalAcquiredAt']})
        spec = deepcopy(self.spec)
        spec['acquisitionEvidence'] = {'path': '/unused/acquisition.json',
                                      'sha256': core.sha(raw), 'selector': '/acquired'}
        self.assertEqual(self.assess(spec)['status'], 'missing')
        self.assertEqual(self.assess(spec, acquisition_raw=raw)['status'], 'valid')
        self.assertEqual(self.assess(spec, acquisition_raw=b'{}')['status'], 'malformed')
        spec['originalAcquiredAt'] = '2026-10-03T00:00:00Z'
        self.assertEqual(self.assess(spec, acquisition_raw=raw)['status'], 'malformed')

    def test_failure_isolated_and_fixed_allowlist_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'authored.json'
            path.write_bytes(self.raw)
            ok = deepcopy(self.spec)
            ok['metadataAsset']['path'] = str(path)
            missing = deepcopy(ok)
            missing['id'] = 'missing'
            missing['metadataAsset']['path'] = str(path.with_name('absent.json'))
            held = deepcopy(ok)
            held['id'] = 'held'
            held['payloadHolds'] = ['private-source']
            with patch.object(binding, 'registry', return_value={'sources': [missing, held, ok]}):
                report = binding.run(now=self.now)
            self.assertEqual([r['status'] for r in report['sources']], ['valid', 'valid', 'missing'])
            self.assertEqual(report['networkRequests'], 0)

    def test_installed_portfolio_roles_stay_separate_and_explicit(self):
        sources = binding.registry()['sources']
        self.assertEqual({s['country'] for s in sources}, {'CI', 'CK', 'CL', 'CM'})
        self.assertEqual(len(sources), 5)
        ck = [s for s in sources if s['country'] == 'CK']
        self.assertEqual(len({s['dataType'] for s in ck}), 2)
        self.assertTrue(all(s['nativeSemantics']['operatorRegister'] is False for s in ck))
        self.assertTrue(all(s['payloadHolds'] for s in sources))
        self.assertTrue(all(s['metadataAsset']['role'] == 'retained-metadata' for s in sources))


if __name__ == '__main__':
    unittest.main()
