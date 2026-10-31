"""Source-only confinement contracts: no sudo, setpriv, model or live filter."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import stat
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0, str(TOOLS))
import coding_child_launch as launch
import stokowski_worker as worker


class LaunchContracts(unittest.TestCase):
    def test_root_control_rejects_writable_parent_and_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'policy'
            path.write_text('{}')
            with self.assertRaises(launch.ConfinementError):
                launch.trusted_file(path)
            link = Path(root)/'link'
            link.symlink_to(path)
            with self.assertRaises(launch.ConfinementError):
                launch.trusted_file(link)

    def test_root_ownership_mode_type_and_parent_contracts(self):
        target = Path('/etc/offmenu/fixture-policy.json')
        def info(path):
            return SimpleNamespace(st_uid=0, st_mode=(stat.S_IFREG|0o644) if path==target
                                   else (stat.S_IFDIR|0o755))
        with patch.object(Path, 'lstat', autospec=True, side_effect=info), patch.object(
                Path, 'stat', autospec=True, side_effect=info):
            self.assertEqual(launch.trusted_file(target,0o644),target)
        for uid, mode in ((1000,stat.S_IFREG|0o644),(0,stat.S_IFREG|0o664),
                          (0,stat.S_IFLNK|0o777),(0,stat.S_IFREG|0o4644),
                          (0,stat.S_IFDIR|0o644)):
            def altered(path):
                return SimpleNamespace(st_uid=uid,st_mode=mode) if path==target else info(path)
            with patch.object(Path,'lstat',autospec=True,side_effect=altered), patch.object(
                    Path,'stat',autospec=True,side_effect=altered):
                with self.assertRaises(launch.ConfinementError):
                    launch.trusted_file(target,0o644)
        def parent_symlink(path):
            return SimpleNamespace(st_uid=0,st_mode=stat.S_IFLNK|0o755) if path==target.parent else info(path)
        with patch.object(Path,'lstat',autospec=True,side_effect=parent_symlink):
            with self.assertRaises(launch.ConfinementError):
                launch.trusted_file(target)

    def test_policy_exact_hashes_no_executable_override(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            files = [root/name for name in ('dropper', 'guard', 'native')]
            for path in files:
                path.write_text(path.name)
            policy = root/'policy.json'
            record = dict(schema='coding-confinement-v1', sha256={
                str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            policy.write_text(json.dumps(record))
            with patch.multiple(launch, POLICY=policy, DROPPER=str(files[0]),
                                GUARD=str(files[1]), BINARY=str(files[2])), patch.object(
                                    launch, 'trusted_file', side_effect=lambda p, mode=None: Path(p)):
                self.assertEqual(launch.installed_policy(), record)
                files[1].write_text('changed')
                with self.assertRaises(launch.ConfinementError):
                    launch.installed_policy()

    def fixture(self, root):
        workspace = root/'workspaces'/'UIF-106'
        attempt = root/'attempts'/'UIF-106'
        home = attempt/'codex-home-fixture'
        workspace.mkdir(parents=True)
        home.mkdir(parents=True, mode=0o700)
        for directory in (workspace, workspace.parent, attempt, attempt.parent, home):
            directory.chmod(0o700)
        (home/'auth.json').symlink_to('/home/user/.codex/auth.json')
        return workspace, attempt, home

    def test_fixed_argv_env_auth_reference_and_rejections(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            workspace, attempt, home = self.fixture(root)
            env = dict(CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(attempt/'codex-state'),
                       LD_PRELOAD='untrusted', APP_TOKEN='untrusted', PYTHONPATH='untrusted')
            command = worker.codex_command(workspace, attempt/'final-message.txt')
            actual_lstat = Path.lstat
            def fixture_lstat(path, *args, **kwargs):
                info = actual_lstat(path, *args, **kwargs)
                if path == root or root in path.parents:
                    # Keep real type/mode/link metadata; only fixture owner is synthetic.
                    return os.stat_result((*info[:4], 1000, *info[5:]))
                return info
            with patch.object(launch, 'RUNTIME', root), patch.object(launch, 'installed_policy'), patch.object(
                    Path, 'lstat', autospec=True, side_effect=fixture_lstat):
                argv, clean = launch.bind_native(command, workspace, env)
                self.assertEqual(argv[:4], ['/usr/bin/sudo', '-n', '--', launch.DROPPER])
                self.assertEqual(set(clean), {'PATH', 'LANG'})
                for index, value in ((0, '/bin/sh'), (7, 'approval_policy="always"'),
                                     (11, 'other-model'), (5, 'danger-full-access')):
                    altered = list(command)
                    altered[index] = value
                    with self.assertRaises(launch.ConfinementError):
                        launch.bind_native(altered, workspace, env)
                (home/'auth.json').unlink()
                (home/'auth.json').symlink_to('/tmp/other-auth')
                with self.assertRaises(launch.ConfinementError):
                    launch.bind_native(command, workspace, env)

    def test_owned_paths_reject_symlinks_and_escape(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root/'real').mkdir()
            (root/'link').symlink_to(root/'real')
            with patch.object(launch, 'RUNTIME', root):
                for path in (root/'link', root/'..'/'outside'):
                    with self.assertRaises(launch.ConfinementError):
                        launch.owned_path(path)
                (root/'real').chmod(0o777)
                with self.assertRaises(launch.ConfinementError):
                    launch.owned_path(root/'real')

    def test_worker_native_prelaunch_refusal_has_no_process_or_uncertain_hold(self):
        with tempfile.TemporaryDirectory() as root, patch.object(
                worker, 'bind_native', side_effect=launch.ConfinementError('fixture')), patch.object(
                worker.subprocess, 'Popen') as popen:
            root = Path(root)
            result = worker.supervise(worker.codex_command(root, root/'final-message.txt'),
                                      'offline', root, {}, root, 1, {})
            popen.assert_not_called()
            self.assertFalse(result['child_started'])
            self.assertTrue(result['child_tree_gone'])
            self.assertEqual(result['status'], 'failed')
            self.assertIsNone(result['resolved_model'])

    def test_worker_actually_consumes_fixed_binding(self):
        with tempfile.TemporaryDirectory() as root, patch.object(
                worker, 'bind_native', return_value=(['fixed-fixture-launch'], {'LANG':'C'})) as bind, patch.object(
                worker.subprocess, 'Popen', side_effect=OSError('fixture no execution')) as popen:
            root = Path(root)
            worker.supervise(worker.codex_command(root,root/'final-message.txt'),
                             'offline',root,{},root,1,{})
            bind.assert_called_once()
            self.assertEqual(popen.call_args.args[0], ['fixed-fixture-launch'])
            self.assertTrue(popen.call_args.kwargs['close_fds'])
            self.assertEqual(popen.call_args.kwargs['env'], {'LANG':'C'})


class GuardContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cc'):
            raise unittest.SkipTest('existing compiler unavailable')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.binary = cls.root/'guard'
        subprocess.run(['cc','-Wall','-Wextra','-Werror','-O2',str(TOOLS/'coding_child_guard.c'),
                        '-o',str(cls.binary)],check=True, capture_output=True)
        # Offline harness exports the actual compiled filter; never installs it.
        harness = cls.root/'filter.c'
        harness.write_text('#define main guard_main\n#include "'+str(TOOLS/'coding_child_guard.c')+'"\n'
            '#undef main\nint main(void) { return fwrite(filter,sizeof(filter),1,stdout)!=1; }\n')
        subprocess.run(['cc','-Wall','-Wextra','-Werror',str(harness),'-o',str(cls.root/'filter')],
                       check=True, capture_output=True)
        cls.instructions = list(struct.iter_unpack('HBBI',subprocess.check_output([str(cls.root/'filter')])))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def evaluate(self, nr, family=0, arch=0xc000003e):
        data = struct.pack('<iIQQQQQQQ',nr,arch,0,family,0,0,0,0,0)
        pc = 0
        a = 0
        while True:
            code,jt,jf,k = self.instructions[pc]
            pc += 1
            if code == 0x20:
                a = struct.unpack_from('<I',data,k)[0]
            elif code == 0x15:
                pc += jt if a == k else jf
            elif code == 0x35:
                pc += jt if a >= k else jf
            elif code == 0x45:
                pc += jt if a & k else jf
            elif code == 0x06:
                return k
            else:
                self.fail('unexpected actual BPF opcode')

    def test_real_filter_offline_arch_x32_socket_uring_process_denials(self):
        self.assertEqual(self.evaluate(0,arch=0x40000003), 0x80000000)
        self.assertEqual(self.evaluate(0x40000000), 0x80000000)
        self.assertEqual(self.evaluate(521), 0x80000000)
        for nr in (53,425,426,427,101,310,311,438):
            self.assertEqual(self.evaluate(nr), 0x50001)
        for family in (socket.AF_UNIX, socket.AF_NETLINK, socket.AF_PACKET):
            self.assertEqual(self.evaluate(41,family), 0x50001)
        for family in (socket.AF_INET, socket.AF_INET6):
            self.assertEqual(self.evaluate(41,family), 0x7fff0000)
        self.assertEqual(self.evaluate(42), 0x7fff0000)

    def test_production_guard_rejects_current_bad_context_before_mutation(self):
        # Only run when read-only observations prove context() must reject.
        if os.getuid() == 0:
            self.skipTest('never invoke production guard as root')
        if os.getuid() == 1000 and os.getgid() == 1000 and not os.getgroups():
            self.skipTest('not a proven bad context; no filter installation allowed')
        result = subprocess.run([str(self.binary)],capture_output=True)
        self.assertEqual(result.returncode,126)
        self.assertEqual(result.stderr,b'coding confinement refused\n')

    def test_descriptor_closure_and_socket_stdio_with_mock_syscalls(self):
        harness = self.root/'descriptors.c'
        harness.write_text('#include <sys/stat.h>\n#include <sys/syscall.h>\n'
            '#include <stdarg.h>\n#include <stdlib.h>\n'
            'static int mode=0, called=0;\n'
            'static int mock_fstat(int fd,struct stat *st) { '
            'st->st_mode=(mode==1 && fd==0)?S_IFSOCK:S_IFREG; return 0; }\n'
            'static long mock_syscall(long nr,...) { va_list ap; va_start(ap,nr); '
            'unsigned low=va_arg(ap,unsigned), high=va_arg(ap,unsigned); '
            'int flags=va_arg(ap,int); va_end(ap); '
            'if(nr!=SYS_close_range || low!=3 || high!=~0U || flags!=0) abort(); '
            'called++; return mode==2?-1:0; }\n'
            '#define fstat mock_fstat\n#define syscall mock_syscall\n#define main guard_main\n'
            '#include "'+str(TOOLS/'coding_child_guard.c')+'"\n#undef main\n'
            'int main(int argc,char **argv) { (void)argc; mode=atoi(argv[1]); '
            'descriptors(); return called!=1; }\n')
        binary = self.root/'descriptors'
        subprocess.run(['cc','-D_GNU_SOURCE','-Wall','-Wextra','-Werror',str(harness),'-o',str(binary)],
                       check=True,capture_output=True)
        for mode, code in ((0,0),(1,126),(2,126)):
            result = subprocess.run([str(binary),str(mode)],capture_output=True)
            self.assertEqual(result.returncode,code)

    def test_sha256_and_fd_contracts_offline(self):
        harness = self.root/'hash.c'
        harness.write_text('#define main guard_main\n#include "'+str(TOOLS/'coding_child_guard.c')+'"\n'
            '#undef main\nint main(int argc,char **argv) { (void)argc; char h[65]; '
            'int fd=open(argv[1],O_RDONLY); hash_fd(fd,h); puts(h); return 0; }\n')
        subprocess.run(['cc','-Wall','-Wextra','-Werror',str(harness),'-o',str(self.root/'hash')],check=True)
        for size in (0,3,55,56,63,64,65,1000):
            payload = b'a'*size
            path = self.root/'payload'
            path.write_bytes(payload)
            self.assertEqual(subprocess.check_output([str(self.root/'hash'),str(path)]).decode().strip(),
                             hashlib.sha256(payload).hexdigest())
        source = (TOOLS/'coding_child_guard.c').read_text()
        self.assertIn('SYS_close_range,3U,~0U,0',source)
        self.assertIn('S_ISSOCK(st.st_mode)',source)
        self.assertLess(source.index('context();'),source.index('descriptors();'))
        dropper = (TOOLS.parents[1]/'deploy/stokowski/offmenu-coding-dropper.sh').read_text()
        self.assertIn('--clear-groups',dropper)
        self.assertIn('--bounding-set=-all',dropper)
        self.assertIn('--no-new-privs --reset-env',dropper)
        self.assertNotIn('eval',dropper)


if __name__ == '__main__':
    unittest.main()
