"""Read-only helper checks with generated directories/mocked statvfs; no network."""
import copy
import errno
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('fetch_capacity_fixture', Path(__file__).resolve().parents[1] / 'fetch_capacity.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def vfs(available, read_only=False):
    return types.SimpleNamespace(f_frsize=1, f_blocks=m.MINIMUM_BYTES*2,
        f_bfree=available+100, f_bavail=available, f_files=10000, f_ffree=5000,
        f_favail=4900, f_flag=m.os.ST_RDONLY if read_only else 0)


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def report(self, available=None):
        available=m.MINIMUM_BYTES if available is None else available
        with mock.patch.object(m,'open_directory_components',return_value=55),mock.patch.object(m.os,'close'),mock.patch.object(m.os,'fstatvfs',return_value=vfs(available)),mock.patch.object(m.os,'fstat',return_value=types.SimpleNamespace(st_dev=123)):
            return m.collect()
    def test_exact_fixed_paths_and_guard(self):
        self.assertEqual(m.PATHS,{'outputs':'/srv/offmenu-refresh/outputs','sourceCache':'/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache'})
        self.assertEqual(m.MINIMUM_BYTES,10737549312)
        self.assertEqual(m.SAFETY_BUFFER_BYTES,131072)
    def test_observed_low_capacity_is_complete_not_fetch_permission(self):
        result=m.sanitize_report(self.report(m.MINIMUM_BYTES-17))
        self.assertEqual(result['status'],'complete')
        self.assertFalse(result['sourceCache']['reserveSatisfied'])
        self.assertEqual(result['sourceCache']['initialDeficitBytes'],17)
        self.assertEqual(result['sourceCache']['freeBytes']-result['sourceCache']['availableBytes'],100)
        self.assertTrue(result['sameFilesystem'])
    def test_exact_boundary_deficit_zero(self):
        result=m.sanitize_report(self.report())
        self.assertEqual(result['sourceCache']['initialDeficitBytes'],0)
        self.assertTrue(result['sourceCache']['reserveSatisfied'])
    def test_real_generated_directory_read_only_observation(self):
        row,device=m.observe(str(self.root))
        self.assertEqual(row['status'],'observed');self.assertIsInstance(device,int)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_missing_does_not_create_directory(self):
        missing=self.root/'not-created'
        row,device=m.observe(str(missing))
        self.assertEqual(row['errorCode'],'missing');self.assertIsNone(device)
        self.assertFalse(missing.exists())
    def test_symlink_at_parent_or_final_refused(self):
        target=self.root/'target';target.mkdir();(target/'nested').mkdir()
        link=self.root/'link';link.symlink_to(target)
        for path in (link,link/'nested'):
            row,device=m.observe(str(path))
            self.assertEqual(row['errorCode'],'symlink_or_not_directory');self.assertIsNone(device)
    def test_permission_error_is_static(self):
        with mock.patch.object(m,'open_directory_components',side_effect=PermissionError(errno.EACCES,'secret-path')):
            row,device=m.observe('/fixed')
        self.assertEqual(row['errorCode'],'permission_denied')
        self.assertNotIn('secret',json.dumps(row))
    def test_close_on_stat_failure(self):
        with mock.patch.object(m,'open_directory_components',return_value=55),mock.patch.object(m.os,'fstatvfs',side_effect=OSError(errno.EIO,'private')),mock.patch.object(m.os,'close') as close:
            row,_=m.observe('/fixed')
        self.assertEqual(row['errorCode'],'io_error');close.assert_called_once_with(55)
    def test_readonly_and_distinct_filesystems(self):
        with mock.patch.object(m,'open_directory_components',return_value=55),mock.patch.object(m.os,'close'),mock.patch.object(m.os,'fstatvfs',return_value=vfs(m.MINIMUM_BYTES,True)),mock.patch.object(m.os,'fstat',side_effect=[types.SimpleNamespace(st_dev=1),types.SimpleNamespace(st_dev=2)]):
            result=m.sanitize_report(m.collect())
        self.assertTrue(result['outputs']['readOnly']);self.assertFalse(result['sameFilesystem'])
    def test_one_path_missing_gives_null_relation(self):
        good=self.report()['outputs']
        with mock.patch.object(m,'observe',side_effect=[(good,1),(m.blocked_row('missing'),None)]):result=m.sanitize_report(m.collect())
        self.assertEqual(result['status'],'blocked');self.assertIsNone(result['sameFilesystem'])
    def test_sanitizer_closed_and_contradiction_checks(self):
        result=self.report()
        for mutation in [lambda d:d.update(extra='private'),lambda d:d.update(homeFilesystemObserved=True),lambda d:d.update(downloads=1),lambda d:d['sourceCache'].update(initialDeficitBytes=1),lambda d:d['outputs'].update(availableBytes=-1),lambda d:d.update(status='blocked'),lambda d:d['outputs'].update(extra='private')]:
            changed=copy.deepcopy(result);mutation(changed)
            with self.assertRaises(ValueError):m.sanitize_report(changed)
    def test_main_refuses_host_and_arguments_without_observation(self):
        with mock.patch.object(m,'collect',side_effect=AssertionError('must not observe')),mock.patch.object(m.socket,'gethostname',return_value='cloud'),mock.patch.object(m.sys,'stderr',io.StringIO()):
            self.assertEqual(m.main([]),2);self.assertEqual(m.main(['--path','/home']),2)
    def test_main_exact_safe_json_contract(self):
        report=self.report(m.MINIMUM_BYTES-999)
        with mock.patch.object(m,'collect',return_value=report),mock.patch.object(m.socket,'gethostname',return_value='foo'),mock.patch.dict(m.os.environ,{'RUNNER_NAME':'foo-offmenu'}),mock.patch.object(m.sys,'stdout',io.StringIO()) as stdout:
            self.assertEqual(m.main([]),0)
        data=json.loads(stdout.getvalue());self.assertEqual(data['schemaVersion'],m.SCHEMA)
        self.assertEqual(data['sourceCache']['initialDeficitBytes'],999)
        self.assertLess(len(stdout.getvalue()),4096)
    def test_only_fixed_paths_are_observed(self):
        with mock.patch.object(m,'observe',return_value=(m.blocked_row('missing'),None)) as observe:m.collect()
        self.assertEqual([call.args for call in observe.call_args_list],[(p,) for p in m.PATHS.values()])
    def test_root_and_components_all_open_nofollow(self):
        original=m.os.open;calls=[]
        def recorded(*args,**kwargs):calls.append((args,kwargs));return original(*args,**kwargs)
        with mock.patch.object(m.os,'open',side_effect=recorded):fd=m.open_directory_components(str(self.root))
        m.os.close(fd)
        self.assertTrue(all(args[1]&m.os.O_NOFOLLOW and args[1]&m.os.O_DIRECTORY for args,_ in calls))
        self.assertEqual(calls[0][0][0],'/')
        self.assertTrue(all('dir_fd' in kw for _,kw in calls[1:]))


if __name__=='__main__':unittest.main()
