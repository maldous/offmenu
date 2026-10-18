"""Synthetic transports only: these tests never open a socket."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acquisition import CachedAcquirer, SourceSpec, ResourceBudget, HTTPSFileTransport, MIN_TTL, MAX_BODY
from offmenu.refresh.core import RefreshError

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)
SPEC = SourceSpec('shared-foods', 'https://publisher.example/data.json', 'a' * 64,
                  'reviewed-test-fixture', enabled=True, rights_approved=True, max_bytes=128)


class Response:
    def __init__(self, status=200, body=b'fixture', headers=None, fail=False):
        self.status, self.body, self.headers = status, io.BytesIO(body), headers or {}
        self.closed, self.fail = False, fail
    def read(self, size):
        if self.fail:
            raise ConnectionError('synthetic interruption')
        return self.body.read(size)
    def close(self):
        self.closed = True


class Transport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []
    def __call__(self, spec, headers):
        self.calls.append((spec, dict(headers)))
        if not self.responses:
            raise AssertionError('unexpected network request')
        return self.responses.pop(0)


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def acquirer(self, transport, spec=SPEC, **kwargs):
        return CachedAcquirer(self.root, {spec.source_key: spec}, transport=transport,
                              sleep=lambda _: None, **kwargs)
    def seed(self, headers=None):
        return self.acquirer(Transport(Response(headers=headers))).acquire(
            SPEC.source_key, fetch_policy='refresh', now=NOW)
    def test_missing_reuse_is_offline(self):
        transport = Transport()
        with self.assertRaisesRegex(RefreshError, 'cache-missing'):
            self.acquirer(transport).acquire(SPEC.source_key, now=NOW)
        self.assertEqual(transport.calls, [])
    def test_fresh_reuse_and_shared_source_single_download(self):
        transport = Transport(Response())
        acquirer = self.acquirer(transport)
        first = acquirer.acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        for country in range(249):
            result = acquirer.acquire(SPEC.source_key, fetch_policy='refresh', now=NOW + timedelta(days=29))
            self.assertEqual(result.path, first.path)
            self.assertEqual(result.status, 'reused-fresh')
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(list((self.root / 'objects').iterdir())), 1)
    def test_stale_reuse_is_offline(self):
        self.seed()
        with self.assertRaisesRegex(RefreshError, 'cache-stale'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW + timedelta(days=30))
    def test_conditional_304_preserves_acquisition_restarts_freshness(self):
        first = self.seed({'ETag': '"version1"', 'Last-Modified': 'Wed, 01 Oct 2025 00:00:00 GMT'})
        transport = Transport(Response(304))
        acquirer = self.acquirer(transport)
        result = acquirer.acquire(SPEC.source_key, fetch_policy='refresh', now=NOW + timedelta(days=30))
        self.assertEqual(result.path, first.path)
        self.assertEqual(result.provenance['originalAcquiredAt'], NOW.isoformat())
        self.assertEqual(transport.calls[0][1]['If-None-Match'], '"version1"')
        self.assertIn('If-Modified-Since', transport.calls[0][1])
        acquirer.acquire(SPEC.source_key, fetch_policy='refresh', now=NOW + timedelta(days=59))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(list(self.root.glob('requests/*/evidence/*.json'))), 2)
    def test_revalidate_inside_ttl(self):
        self.seed({'ETag': 'x'})
        transport = Transport(Response(304))
        result = self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='revalidate', now=NOW)
        self.assertEqual(result.status, 'not-modified-304')
    def test_force_download_omits_validators_deduplicates_identical(self):
        first = self.seed({'ETag': 'x'})
        transport = Transport(Response())
        result = self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='force-download', now=NOW + timedelta(days=1))
        self.assertEqual(transport.calls[0][1], {'Accept-Encoding': 'identity'})
        self.assertEqual(result.status, 'identical-body-200')
        self.assertEqual(result.path, first.path)
        self.assertEqual(result.provenance['originalAcquiredAt'], NOW.isoformat())
    def test_changed_body_new_object_and_acquisition_time(self):
        first = self.seed()
        result = self.acquirer(Transport(Response(body=b'new'))).acquire(
            SPEC.source_key, fetch_policy='refresh', now=NOW + timedelta(days=31))
        self.assertNotEqual(result.sha256, first.sha256)
        self.assertTrue(first.path.exists())
        self.assertEqual(result.provenance['originalAcquiredAt'], (NOW + timedelta(days=31)).isoformat())
    def test_gates_precede_cached_reuse(self):
        self.seed()
        for spec in (replace(SPEC, enabled=False), replace(SPEC, held=True), replace(SPEC, rights_approved=False)):
            with self.assertRaisesRegex(RefreshError, 'gate-closed'):
                self.acquirer(Transport(), spec).acquire(spec.source_key, now=NOW)
    def test_no_default_or_arbitrary_url_registry(self):
        with self.assertRaisesRegex(RefreshError, 'not-allowlisted'):
            CachedAcquirer(self.root, {}).acquire('unknown', fetch_policy='refresh', now=NOW)
        for url in ('http://publisher.example/a', 'https://u:p@publisher.example/a',
                    'https://publisher.example/a?token=secret', 'https://publisher.example:8443/a'):
            with self.assertRaisesRegex(RefreshError, 'locator'):
                self.acquirer(Transport(), replace(SPEC, url=url)).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
    def test_ttl_cannot_be_shorter_than_30_days(self):
        with self.assertRaisesRegex(RefreshError, 'bounds'):
            self.acquirer(Transport(), replace(SPEC, ttl_seconds=MIN_TTL-1)).acquire(SPEC.source_key, now=NOW)
    def test_corrupt_body_fails_closed_without_network(self):
        first = self.seed({'ETag': 'x'})
        first.path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(RefreshError, 'corrupt'):
            self.acquirer(Transport()).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW + timedelta(days=31))
    def test_not_modified_without_matching_cached_validator_rejected(self):
        for seeded in (False, True):
            if seeded:
                self.seed()
            with self.assertRaisesRegex(RefreshError, 'unexpected-not-modified'):
                self.acquirer(Transport(Response(304))).acquire(SPEC.source_key, fetch_policy='revalidate', now=NOW)
    def test_validator_mismatch_rejected(self):
        self.seed({'ETag': 'x'})
        with self.assertRaisesRegex(RefreshError, 'validator-mismatch'):
            self.acquirer(Transport(Response(304, headers={'ETag': 'y'}))).acquire(SPEC.source_key, fetch_policy='revalidate', now=NOW)
    def test_retries_bounded_and_connections_closed(self):
        responses = [Response(503) for _ in range(3)]
        transport = Transport(*responses)
        with self.assertRaisesRegex(RefreshError, 'retries-exhausted'):
            self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(all(r.closed for r in responses))
        self.assertEqual(list(self.root.glob('requests/*/body.partial')), [])
    def test_interruption_restarts_does_not_append_partial(self):
        transport = Transport(Response(fail=True), Response(body=b'complete'))
        result = self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        self.assertEqual(result.path.read_bytes(), b'complete')
        self.assertEqual(len(transport.calls), 2)
    def test_errors_redirects_and_challenges_never_retried(self):
        for status in (301, 302, 401, 403, 404, 206):
            transport = Transport(Response(status))
            with self.assertRaisesRegex(RefreshError, 'response-not-permitted'):
                self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
            self.assertEqual(len(transport.calls), 1)
    def test_response_bounds_and_policy(self):
        for headers, body, error in (({'Content-Length': '9999'}, b'x', 'size-limit'),
                                     ({}, b'x'*129, 'size-limit'),
                                     ({'Cache-Control': 'no-store'}, b'x', 'retention'),
                                     ({'Cache-Control': 'private'}, b'x', 'retention'),
                                     ({'Vary': 'Cookie'}, b'x', 'vary'),
                                     ({'Content-Encoding': 'gzip'}, b'x', 'encoding')):
            with self.assertRaisesRegex(RefreshError, error):
                self.acquirer(Transport(Response(body=body, headers=headers))).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
            self.assertEqual(list(self.root.glob('requests/*/body.partial')), [])
    def test_http_cache_restrictions_override_reuse_preference(self):
        self.seed({'Cache-Control': 'max-age=60', 'ETag': 'x'})
        with self.assertRaisesRegex(RefreshError, 'cache-stale'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW + timedelta(seconds=60))
    def test_secret_response_headers_not_persisted(self):
        self.seed({'ETag': 'x', 'Set-Cookie': 'secret'})
        self.acquirer(Transport(Response(304, headers={'Set-Cookie': 'more-secret'}))).acquire(SPEC.source_key, fetch_policy='revalidate', now=NOW)
        for record in self.root.glob('requests/**/*.json'):
            self.assertNotIn('secret', record.read_text())
    def test_policy_revision_invalidates_request_identity(self):
        self.seed()
        spec = replace(SPEC, policy_fingerprint='b'*64)
        with self.assertRaisesRegex(RefreshError, 'cache-missing'):
            self.acquirer(Transport(), spec).acquire(SPEC.source_key, now=NOW)
    def test_symlink_rejected(self):
        target = self.root / 'other'
        target.mkdir()
        (self.root / 'alias').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RefreshError, 'symlink'):
            CachedAcquirer(self.root / 'alias', {SPEC.source_key: SPEC})
    def test_interrupted_current_pointer_keeps_verified_evidence(self):
        from offmenu.refresh import acquisition
        original = acquisition.atomic_json
        def interrupted(path, value):
            if path.name == 'current.json':
                raise OSError('simulated interruption')
            return original(path, value)
        with patch.object(acquisition, 'atomic_json', interrupted):
            with self.assertRaises(OSError):
                self.seed()
        self.assertEqual(len(list(self.root.glob('requests/*/evidence/*.json'))), 1)
        result = self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW)
        self.assertEqual(result.path.read_bytes(), b'fixture')
        self.assertEqual(len(list((self.root / 'objects').iterdir())), 1)
    def test_restricted_scope_refused(self):
        with self.assertRaisesRegex(RefreshError, 'restricted-cache'):
            self.acquirer(Transport(), replace(SPEC, cache_scope='private')).acquire(SPEC.source_key, now=NOW)

    def test_missing_body_fails_closed(self):
        result = self.seed()
        result.path.unlink()
        with self.assertRaisesRegex(RefreshError, 'cached-body-missing'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW)

    def test_age_with_max_age_is_conservatively_stale(self):
        self.seed({'Cache-Control': 'max-age=3600', 'Age': '7200'})
        with self.assertRaisesRegex(RefreshError, 'cache-stale'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW)

    def test_early_http_staleness_does_not_trigger_automatic_network(self):
        self.seed({'Cache-Control': 'max-age=60', 'ETag': 'x'})
        with self.assertRaisesRegex(RefreshError, 'deferred-minimum'):
            self.acquirer(Transport()).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW+timedelta(seconds=120))
        self.acquirer(Transport(Response(304))).acquire(SPEC.source_key, fetch_policy='revalidate', now=NOW+timedelta(seconds=120))

    def test_current_pointer_requires_immutable_evidence(self):
        self.seed()
        record = next(self.root.glob('requests/*/current.json'))
        data = json.loads(record.read_text())
        data['checkedAt'] = (NOW+timedelta(days=29)).isoformat()
        record.write_text(json.dumps(data))
        with self.assertRaisesRegex(RefreshError, 'evidence-missing-or-corrupt'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW+timedelta(days=31))

    def test_malformed_receipt_fixed_error(self):
        self.seed()
        record = next(self.root.glob('requests/*/current.json'))
        data = json.loads(record.read_text())
        del data['checkedAt']
        record.write_text(json.dumps(data))
        with self.assertRaisesRegex(RefreshError, 'invalid-acquisition-record'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW)

    def test_publisher_retry_after_defers_without_second_request(self):
        transport = Transport(Response(429, headers={'Retry-After': '3600'}))
        with self.assertRaisesRegex(RefreshError, 'publisher-retry-deferred'):
            self.acquirer(transport).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        self.assertEqual(len(transport.calls), 1)

    def test_deadline_checked_after_eof(self):
        clock = [0]
        response = Response()
        def slow_eof(size):
            clock[0] = 181
            return b''
        response.read = slow_eof
        with patch('offmenu.refresh.acquisition.time.monotonic', lambda: clock[0]):
            with self.assertRaisesRegex(RefreshError, 'duration-limit'):
                self.acquirer(Transport(response)).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        self.assertFalse(list(self.root.glob('requests/*/current.json')))

    def test_large_source_needs_runner_bound_resource_policy(self):
        large = replace(SPEC, max_bytes=MAX_BODY+1)
        with self.assertRaisesRegex(RefreshError, 'runner-byte-budget'):
            self.acquirer(Transport(), large).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        budget = ResourceBudget(self.root, MAX_BODY+1, minimum_free_bytes=128, max_seconds=600)
        result = self.acquirer(Transport(Response()), large, resource_budget=budget).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        self.assertEqual(result.path.read_bytes(), b'fixture')
        with self.assertRaisesRegex(RefreshError, 'runner-resource-budget'):
            self.acquirer(Transport(), resource_budget=replace(budget, storage_root=self.root/'different'))

    def test_large_cached_source_denied_before_digest_and_transport(self):
        large = replace(SPEC, max_bytes=MAX_BODY+1)
        budget = ResourceBudget(self.root, MAX_BODY+1)
        self.acquirer(Transport(Response()), large, resource_budget=budget).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)
        with patch('offmenu.refresh.acquisition.digest', side_effect=AssertionError('must not hash')):
            with self.assertRaisesRegex(RefreshError, 'runner-byte-budget'):
                self.acquirer(Transport(), large).acquire(SPEC.source_key, now=NOW)

    def test_disk_reserve_precedes_network(self):
        from collections import namedtuple
        Usage = namedtuple('Usage', 'total used free')
        with patch('offmenu.refresh.acquisition.shutil.disk_usage', return_value=Usage(1000, 999, 1)):
            with self.assertRaisesRegex(RefreshError, 'disk-budget'):
                self.acquirer(Transport()).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)

    def test_retry_bytes_count_toward_cumulative_budget(self):
        first = Response(body=b'x'*100)
        original = first.read
        reads = [0]
        def interrupted(size):
            reads[0] += 1
            if reads[0] == 2:
                raise ConnectionError('interrupted')
            return original(size)
        first.read = interrupted
        budget = ResourceBudget(self.root, 128)
        with self.assertRaisesRegex(RefreshError, 'cumulative-transfer-budget'):
            self.acquirer(Transport(first, Response(body=b'x'*100)), resource_budget=budget).acquire(SPEC.source_key, fetch_policy='refresh', now=NOW)

    def test_transport_watchdog_shuts_detached_socket_and_uses_read1(self):
        from unittest.mock import Mock
        sock, raw, connection = Mock(), Mock(), Mock()
        connection.sock = sock
        raw.status, raw.getheaders.return_value = 200, []
        timers = []
        def timer_factory(seconds, callback):
            timer = Mock()
            timer.callback = callback
            timers.append(timer)
            return timer
        def getresponse():
            # HTTPConnection detaches sockets for Connection: close responses.
            connection.sock = None
            return raw
        connection.getresponse.side_effect = getresponse
        def drip(size):
            timers[0].callback()
            return b'x'
        raw.read1.side_effect = drip
        with patch('offmenu.refresh.acquisition.http.client.HTTPSConnection', return_value=connection), patch('offmenu.refresh.acquisition.threading.Timer', side_effect=timer_factory):
            response = HTTPSFileTransport()(SPEC, {})
            with self.assertRaises(TimeoutError):
                response.read(1024)
            response.close()
        raw.read1.assert_called_once_with(1024)
        raw.read.assert_not_called()
        sock.shutdown.assert_called_once()
        timers[0].cancel.assert_called_once()

    def test_invalid_clock_and_future_cache(self):
        with self.assertRaisesRegex(RefreshError, 'clock'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=datetime(2026, 1, 1))
        self.seed()
        with self.assertRaisesRegex(RefreshError, 'time'):
            self.acquirer(Transport()).acquire(SPEC.source_key, now=NOW-timedelta(seconds=1))


if __name__ == '__main__':
    unittest.main()
