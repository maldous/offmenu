"""Narrow private-original Vary correction; synthetic metadata/bodies only."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import acquisition as cache
from offmenu.refresh import known_asset_intake as intake
from offmenu.refresh.core import RefreshError

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


legacy = module('vary_private_legacy', 'scripts/save-private-original.py')
legacy_tests = module('vary_private_fixtures', 'tests/test_fixed_source_private_save.py')
media_tests = module('vary_media_fixtures', 'tests/test_known_asset_intake.py')


class VaryPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        selection = json.loads((ROOT / 'docs/collection-selections/global-comprehensive-selection.json').read_bytes())
        cls.sources = {s['sourceKey']: s for s in selection['sources']}
        cls.pdf_source = {'expectedResponse': {'content-type': 'application/pdf'},
            'hardTransferBytes': 1024, 'expectedBytes': None}

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name in ('socket', 'create_connection', 'getaddrinfo'):
            self.stack.enter_context(patch.object(socket, name, side_effect=AssertionError('live network forbidden')))

    def private_headers(self, raw, source=None):
        return legacy.download_headers(raw, source or self.pdf_source, cache)

    def media_headers(self, raw, key='so-wfp-metadata', **kwargs):
        return intake.checked_headers(raw, self.sources[key], **kwargs)

    @contextmanager
    def fixture(self, kind):
        fixture = (legacy_tests.SaveTests('test_five_private_downloads_no_http_cache_and_prior_intents_preserved')
            if kind == 'legacy' else media_tests.IntakeTests('test_all_five_strict_originals_save_and_reuse_with_exact_meters'))
        fixture.setUp()
        try:
            yield fixture
        finally:
            fixture.tearDown()

    def test_private_pdf_accepts_cookie_origin_and_mixed_vary_with_valid_framing(self):
        for vary in ('Cookie', 'Origin', 'Accept-Encoding, Origin', '*'):
            headers = [('Content-Type', 'application/pdf'), ('Content-Length', '12'), ('Vary', vary)]
            with self.subTest(vary=vary):
                self.assertEqual(self.private_headers(headers)['vary'], vary)
                facts = legacy.policy_facts(headers)
                self.assertEqual(facts['vary'], 'unsupported')
                self.assertFalse(facts['httpResponseCached'])
                self.assertFalse(facts['httpCacheReuse'])
                legacy.validate_policy(facts)

    def test_all_five_media_sources_accept_vary_with_their_exact_type_and_framing(self):
        keys = ['so-wfp-markets', 'so-wfp-metadata', 'so-wfp-prices',
            'pg58-plos-0184279-s001', 'pg58-plos-0184279-s002']
        for key in keys:
            for vary in ('Cookie', 'Origin'):
                headers = [('content-type', self.sources[key]['expectedResponse']['content-type']),
                    ('content-length', '12'), ('vary', vary)]
                with self.subTest(key=key, vary=vary):
                    self.assertEqual(self.media_headers(headers, key)['vary'], vary)
                    self.assertEqual(legacy.policy_facts(headers)['vary'], 'unsupported')

    def test_empty_and_accept_encoding_vary_description_unchanged(self):
        for vary, expected in [('', 'absent'), ('Accept-Encoding', 'accept-encoding')]:
            raw = [('content-type', 'application/json'), ('content-length', '12'), ('vary', vary)]
            self.media_headers(raw)
            self.assertEqual(legacy.policy_facts(raw)['vary'], expected)

    def test_shared_http_cache_policy_still_rejects_cookie_and_origin(self):
        for vary in ('Cookie', 'Origin'):
            with self.subTest(vary=vary), self.assertRaisesRegex(RefreshError, '^unsupported-response-vary$'):
                cache._retention({'vary': vary})
        cache._retention({'vary': 'Accept-Encoding'})
        for directive in ('private', 'no-store'):
            with self.assertRaisesRegex(RefreshError, '^response-retention-not-approved$'):
                cache._retention({'cache-control': directive})

    def test_actual_cached_acquirer_stops_before_body_for_vary(self):
        for vary in ('Cookie', 'Origin'):
            with tempfile.TemporaryDirectory() as folder, self.subTest(vary=vary):
                response = media_tests.Response(b'DO NOT READ', 200,
                    [('Content-Length', '11'), ('Vary', vary)])
                spec = cache.SourceSpec('public-fixture', 'https://example.invalid/public',
                    'a' * 64, 'synthetic-rights', enabled=True, rights_approved=True, max_bytes=128)
                acquirer = cache.CachedAcquirer(Path(folder), {spec.source_key: spec}, retries=0,
                    transport=lambda *args: response)
                with self.assertRaisesRegex(RefreshError, '^unsupported-response-vary$'):
                    acquirer.acquire(spec.source_key, fetch_policy='refresh', now=datetime.now(timezone.utc))
                self.assertEqual(response.reads, 0)
                self.assertTrue(response.closed)
                self.assertFalse(list(Path(folder).glob('requests/*/body.partial')))

    def test_source_specific_pdf_expected_response_still_controls_acceptance(self):
        source = deepcopy(self.pdf_source)
        source['expectedResponse']['vary'] = 'Origin'
        headers = [('content-type', 'application/pdf'), ('content-length', '12')]
        self.assertEqual(self.private_headers(headers + [('vary', 'Origin')], source)['vary'], 'Origin')
        with self.assertRaisesRegex(RefreshError, '^source-response-contract-changed$'):
            self.private_headers(headers + [('vary', 'Cookie')], source)

    def test_media_closed_contract_cannot_silently_add_a_vary_exception(self):
        source = deepcopy(self.sources['so-wfp-metadata'])
        source['expectedResponse']['vary'] = 'Origin'
        with self.assertRaisesRegex(RefreshError, '^media-intake-contract-invalid$'):
            intake.validate_source(source)

    def test_duplicate_critical_headers_remain_rejected_in_both_paths(self):
        for name in ('vary', 'content-length', 'content-type', 'location', 'cache-control',
                'content-encoding', 'transfer-encoding', 'strict-transport-security'):
            for checker, media_type in ((self.private_headers, 'application/pdf'),
                    (self.media_headers, 'application/json')):
                headers = [('content-type', media_type), ('content-length', '12'),
                    (name, 'Cookie'), (name.upper(), 'Origin')]
                with self.subTest(name=name, checker=checker.__name__), self.assertRaisesRegex(RefreshError, '^invalid-response-headers$'):
                    checker(headers)

    def test_oversized_and_crlf_vary_remain_rejected_in_both_paths(self):
        for value in ('V' * 8193, 'Cookie\r\nOrigin'):
            for checker, media_type in ((self.private_headers, 'application/pdf'),
                    (self.media_headers, 'application/json')):
                with self.subTest(size=len(value), checker=checker.__name__), self.assertRaises(RefreshError):
                    checker([('content-type', media_type), ('content-length', '12'), ('vary', value)])

    def test_encoding_rejection_and_framing_conflicts_remain(self):
        for checker, media_type in ((self.private_headers, 'application/pdf'),
                (self.media_headers, 'application/json')):
            headers = [('content-type', media_type), ('content-length', '12'), ('vary', 'Cookie')]
            for extra in [[('content-encoding', 'gzip')], [('transfer-encoding', 'chunked')]]:
                with self.subTest(checker=checker.__name__, extra=extra), self.assertRaises(RefreshError):
                    checker(headers + extra)
        with self.assertRaisesRegex(RefreshError, '^media-intake-framing-invalid$'):
            self.media_headers([('content-type', 'application/json'), ('vary', 'Origin')])
        with self.assertRaisesRegex(RefreshError, '^media-intake-header-invalid$'):
            self.media_headers([('content-type', 'application/json'), ('content-length', '12'),
                ('vary', 'Origin'), ('location', 'https://example.invalid/other')])

    def test_media_envelope_and_field_count_are_unchanged(self):
        base = [('content-type', 'application/json'), ('content-length', '12'), ('vary', 'Cookie')]
        for extra in ([('set-cookie', 'x' * 8192)] * 8, [('set-cookie', 'x')] * 98):
            with self.assertRaisesRegex(RefreshError, '^media-intake-header-invalid$'):
                self.media_headers(base + extra)

    def test_private_pdf_saves_vary_as_descriptive_fact_without_http_cache(self):
        with self.fixture('legacy') as fixture:
            def transport(*args, **kwargs):
                response = fixture.transport(*args, **kwargs)
                response.headers.append(('Vary', 'Cookie, Origin'))
                return response
            report = fixture.clean(fixture.run_batch(transport=transport))
            self.assertEqual(report['status'], 'complete')
            self.assertFalse((fixture.work / 'source-cache').exists())
            self.assertEqual({p.name: p.read_bytes() for p in (fixture.work / 'intents').iterdir()}, fixture.before)
            for item in report['items']:
                self.assertEqual(item['responsePolicy']['vary'], 'unsupported')
                self.assertFalse(item['responsePolicy']['httpResponseCached'])
                self.assertFalse(item['responsePolicy']['httpCacheReuse'])
            fixture.calls.clear()
            again = fixture.clean(fixture.run_batch(transport=transport))
            self.assertEqual(again['networkRequests'], 0)
            self.assertFalse(fixture.calls)

    def test_private_media_save_records_unsupported_fact_but_no_raw_vary_values(self):
        with self.fixture('media') as fixture:
            def transport(*args, **kwargs):
                response = fixture.transport(*args, **kwargs)
                response.headers.append(('Vary', 'Origin, Cookie, PRIVATE_SENTINEL'))
                return response
            report = fixture.run_source(1, transport=transport)
            self.assertEqual(report['status'], 'verified-private-original', report)
            self.assertEqual(report['responsePolicy']['vary'], 'unsupported')
            self.assertFalse(report['httpResponseCacheEnabled'])
            self.assertFalse((fixture.work / 'source-cache').exists())
            self.assertNotIn('PRIVATE_SENTINEL', json.dumps(report))
            for path in fixture.work.rglob('*.json'):
                self.assertNotIn('PRIVATE_SENTINEL', path.read_text())
            again = fixture.run_source(1, transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError('retry')))
            self.assertEqual(again['network']['requests'], 0)

    def test_wfp_redirect_still_stops_before_body_and_never_retries(self):
        with self.fixture('media') as fixture:
            response = media_tests.Response(b'DO NOT READ', 302,
                [('Location', 'https://unreviewed.example/file?secret=private'), ('Vary', 'Origin')])
            result = fixture.run_source(0, transport=lambda *a, **k: response)
            self.assertEqual(result['errorCode'], 'source-response-not-permitted')
            self.assertEqual(result['network'], {'requests': 1, 'bodyBytesRead': 0})
            self.assertEqual(response.reads, 0)
            again = fixture.run_source(0, transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError('retry')))
            self.assertEqual(again['errorCode'], 'private-save-intent-uncertain')
            self.assertEqual(again['network']['requests'], 0)

    def test_plos_duplicate_or_oversized_headers_still_stop_before_storage(self):
        for extra in ([('X-Header', 'one'), ('X-Header', 'two')], [('Set-Cookie', 'x' * 8193)]):
            with self.fixture('media') as fixture:
                response = media_tests.Response(b'DO NOT READ', 302,
                    [('Location', media_tests.capability(fixture.sources[3])), ('Vary', 'Cookie')] + extra)
                calls = []
                def transport(*args, **kwargs):
                    calls.append(1)
                    if len(calls) > 1:
                        raise AssertionError('unapproved storage request')
                    return response
                result = fixture.run_source(3, transport=transport)
                self.assertEqual(result['errorCode'], 'invalid-response-headers')
                self.assertEqual(result['network'], {'requests': 1, 'bodyBytesRead': 0})
                self.assertEqual(response.reads, 0)
                self.assertEqual(len(calls), 1)
                again = fixture.run_source(3, transport=transport)
                self.assertEqual(again['network']['requests'], 0)
                self.assertEqual(len(calls), 1)

    def test_plos_wrong_redirect_identity_remains_blocked_even_with_vary(self):
        with self.fixture('media') as fixture:
            response = media_tests.Response(b'DO NOT READ', 302,
                [('Location', 'https://unreviewed.example/file'), ('Vary', 'Origin')])
            result = fixture.run_source(3, transport=lambda *a, **k: response)
            self.assertEqual(result['errorCode'], 'media-intake-redirect-invalid')
            self.assertEqual(result['network'], {'requests': 1, 'bodyBytesRead': 0})
            self.assertEqual(response.reads, 0)


if __name__ == '__main__':
    unittest.main()
