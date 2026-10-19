"""Stage labels derive from collector context, without changing observations."""
import io
import unittest

from offmenu.refresh.collection_progress import ProgressReporter


class StageProgressTests(unittest.TestCase):
    def reporter(self, stage=None):
        stream = io.StringIO()
        reporter = ProgressReporter(stream=stream)
        if stage is not None:
            reporter.execution_stage(stage)
        return reporter, stream

    def render(self, reporter, stream):
        reporter._emit(reporter.snapshot())
        return stream.getvalue()

    def test_fetch_uses_verification_and_does_not_present_parse_outcomes_as_failure(self):
        reporter, stream = self.reporter('fetch')
        reporter.stage('verifying')
        reporter.update(preparation_configured=8, preparation_effective=4, preparation_total=988,
                        preparation_completed=988, preparation_queued=0, prepared=23, preparation_reused=18,
                        failed=92, held=979, extraction_held_records=930, extraction_held_verified_records=929,
                        retained_preparation_unselected_held=913, retained_selected=988, retained_verified=988,
                        retained_verified_payload_bytes=28437595507, network_bytes=0, prepared_bytes=15336896,
                        verified_original_records=1041)
        text = self.render(reporter, stream)
        self.assertIn('OffMenu fetch stage=verifying', text)
        self.assertIn('verification active=0 effective=4 configured=8 queued=0 completed=988/988', text)
        self.assertIn('verified-original-records=1041 (aliases included)', text)
        self.assertIn('network-body-read=0', text)
        self.assertIn('retained payloads completed-verified=988/988 verified-payload-bytes=28437595507', text)
        for absent in ('prepared-ready', 'extraction-held', 'unselected-held', 'failed-stage', 'held-stage', 'preparation-storage', '| prep '):
            self.assertNotIn(absent, text)
        # Omitting irrelevant labels does not change any recorded observation.
        self.assertEqual(reporter.snapshot()['prepared'], 23)
        self.assertEqual(reporter.snapshot()['held'], 979)

    def test_fetch_preserves_genuine_collection_failures_and_holds(self):
        reporter, stream = self.reporter('fetch')
        reporter.update(failed=8, held=10, extraction_held_records=0, verified_original_records=1041)
        text = self.render(reporter, stream)
        self.assertIn('failed-collection=8 held-collection=10', text)
        self.assertNotIn('extraction-held', text)

    def test_parse_shows_zero_acquisition_and_separate_local_payloads(self):
        reporter, stream = self.reporter('parse')
        reporter.stage('preparing')
        reporter.update(download_total=0, download_completed=0, download_queued=0,
                        preparation_total=10, preparation_completed=5, preparation_queued=3,
                        prepared=5, preparation_reused=2, network_bytes=0,
                        retained_selected=10, retained_verified=5, retained_verified_payload_bytes=12345)
        text = self.render(reporter, stream)
        self.assertIn('OffMenu parse stage=preparing', text)
        self.assertIn('acquisition jobs=0 completed=0 queued=0 active=0', text)
        self.assertIn('| parse active=0', text)
        self.assertIn('prepared-ready-total=5 new=3 reused=2', text)
        self.assertIn('network-body-read=0', text)
        self.assertIn('local custody payloads completed-verified=5/10 verified-payload-bytes=12345 (excludes other local I/O)', text)
        self.assertNotIn('| download ', text)

    def test_parse_does_not_hide_unexpected_nonzero_or_unknown_acquisition(self):
        reporter, stream = self.reporter('parse')
        text = self.render(reporter, stream)
        self.assertIn('acquisition jobs=unknown', text)
        stream.seek(0);stream.truncate()
        reporter.update(download_total=2, download_completed=1, download_queued=1, network_bytes=7)
        text = self.render(reporter, stream)
        self.assertIn('acquisition jobs=2 completed=1 queued=1 active=0', text)
        self.assertIn('network-body-read=7', text)

    def test_stage_context_is_closed_and_activity_observation_is_preserved(self):
        reporter, stream = self.reporter()
        for invalid in ('combined', 'https://private.invalid', '', True, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                reporter.execution_stage(invalid)
        class Activity:
            def count(self):
                return 3
        reporter.observe(preparation_activity=Activity())
        reporter.execution_stage('fetch')
        self.assertEqual(reporter.snapshot()['preparation_active'], 3)
        self.assertIn('verification active=3', self.render(reporter, stream))
        self.assertNotIn('private.invalid', stream.getvalue())

    def test_validated_stage_change_flushes_and_closed_reporter_stays_closed(self):
        stream = io.StringIO()
        reporter = ProgressReporter(stream=stream).start()
        reporter.execution_stage('fetch')
        reporter.stage('verifying')
        reporter.stop()
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn('OffMenu pass stage=starting', lines[0])
        self.assertIn('OffMenu fetch stage=starting', lines[1])
        self.assertIn('OffMenu fetch stage=verifying', lines[2])
        self.assertIn('OffMenu fetch stage=finished', lines[3])
        reporter.execution_stage('parse')
        self.assertEqual(reporter.snapshot()['execution_stage'], 'fetch')
        self.assertEqual(len(stream.getvalue().splitlines()), 4)


if __name__ == '__main__':
    unittest.main()
