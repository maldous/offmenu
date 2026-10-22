"""Generated control/config fixtures only; no real runtime or corpus is scanned."""
import copy
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_catalog as catalog
from runner_paths import resolve_layout


class CatalogRuntimeExclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/home/user/src/offmenu-data/runtime/layout-migration/worker26')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / 'data'
        runtime = self.data / 'runtime'
        roots = {'runtime': runtime / 'manual-runner', 'public_staging': self.data / 'staging/public',
                 'normalization': self.data / 'normalized/manual-runner', 'household': self.data / 'private/household'}
        runtime.mkdir(parents=True, mode=0o700)
        for path in roots.values(): path.mkdir(parents=True, mode=0o700)
        self.config = runtime / 'manual-runner-layout.json'
        self.value = {'schema': 'offmenu-runner-layout/1', **{k: str(v) for k, v in roots.items()},
                      'lock': str(runtime / 'manual-runner.lock')}
        self.config.write_text(json.dumps(self.value))
        self.config.chmod(0o600)
        env = {k: v for k, v in os.environ.items() if not k.startswith('OFFMENU_RUN_')}
        env['OFFMENU_RUN_LAYOUT'] = str(self.config)
        patched = patch.dict(os.environ, env, clear=True)
        patched.start(); self.addCleanup(patched.stop)
        patched = patch.object(catalog, 'DEFAULT_ROOT', str(self.data))
        patched.start(); self.addCleanup(patched.stop)
        fd = os.open(self.value['lock'], os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        resolve_layout(roots['runtime'] / 'ingest', require_lease=False).activate(fd)
        self.ledger = runtime / 'control/permanent-ledger/events.jsonl'
        self.review = runtime / 'layout-migration/worker64/report.json'
        for path in (self.ledger, self.review):
            path.parent.mkdir(parents=True, mode=0o700)
            path.write_text('{"provider":"synthetic-control"}\n')
        self.retained = self.data / 'retained/ingredients.csv'
        self.retained.parent.mkdir(mode=0o700)
        self.retained.write_text('ingredient,name\n1,Fixture\n')

    def discover(self, **options):
        return catalog.discover_sources({'roots': [str(self.data)], 'project_reports': [], **options})

    def protected(self, path):
        path = Path(path)
        return path == self.config or path.is_relative_to(self.data / 'runtime')

    def test_runtime_traversal_and_explicit_reports_never_sample_control_or_config(self):
        original = catalog._read_prefix
        reads = []
        def read(path, *args, **kwargs):
            self.assertFalse(self.protected(path), 'catalog sampled operational control/config')
            reads.append(Path(path))
            return original(path, *args, **kwargs)
        with patch.object(catalog, '_read_prefix', side_effect=read):
            result = self.discover(project_reports=[str(self.ledger), str(self.review), str(self.config)])
        self.assertIn(self.retained, reads)
        for source in result['sources']:
            if self.protected(source['path']):
                self.assertEqual(source['disposition'], 'excluded')
                self.assertEqual(source['domains'], [])

    def test_selected_config_outside_runtime_and_manifest_refs_are_excluded_before_admission(self):
        # The selected file is excluded even when it is outside reserved runtime.
        new_config = self.data / 'config/manifest.json'
        new_config.parent.mkdir(mode=0o700)
        self.config.rename(new_config)
        self.config = new_config
        os.environ['OFFMENU_RUN_LAYOUT'] = str(new_config)
        manifest = self.retained.parent / 'manifest.json'
        manifest.write_text(json.dumps({'files': [{'path': str(p)} for p in
                                                 (self.ledger, self.review, self.config, self.retained)]}))
        original = catalog._allow_report_ref
        original_read = catalog._read_prefix
        original_stat = catalog._stat
        references = []
        reads = []
        def allow(path, *args):
            self.assertFalse(self.protected(path), 'operational reference reached scope resolution')
            references.append(Path(path))
            return original(path, *args)
        def read(path, *args, **kwargs):
            self.assertFalse(self.protected(path), 'catalog sampled excluded reference/config')
            reads.append(Path(path))
            return original_read(path, *args, **kwargs)
        def stat_path(path):
            self.assertFalse(self.protected(path), 'catalog statted excluded operational path')
            return original_stat(path)
        with patch.object(catalog, '_allow_report_ref', side_effect=allow), patch.object(catalog, '_read_prefix', side_effect=read), patch.object(catalog, '_stat', side_effect=stat_path):
            self.discover(project_reports=[str(manifest), str(self.config)], allowed_report_roots=[str(self.data)])
        self.assertIn(self.retained, references)
        self.assertIn(self.retained, reads)

    def test_cursor_binds_reserved_runtime_and_exact_selected_config(self):
        first = self.discover(max_files=1)
        cursor = first['resume_cursor']
        self.assertIsNotNone(cursor)
        for required in (self.data / 'runtime', self.config):
            with self.subTest(required=required):
                self.assertIn(str(required), cursor['excluded'])
                stale = copy.deepcopy(cursor)
                stale['excluded'].remove(str(required))
                with patch.object(catalog, '_read_prefix', side_effect=AssertionError('stale cursor read')):
                    with self.assertRaisesRegex(ValueError, '^catalog_cursor_exclusions_changed$'):
                        self.discover(resume_cursor=stale)


if __name__ == '__main__': unittest.main()
