"""Offline synthetic fixtures only; never invoke real receive CLI or host paths."""
import importlib.util
import os
from pathlib import Path
import pty
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'tools/delivery/stokowski_credential_stage.py'
spec = importlib.util.spec_from_file_location('credential_stage', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SYNTHETIC = b'SYNTHETIC-only-test-value'


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp')
        self.root = Path(self.temp.name)
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.deadline = time.monotonic() + 2

    def tearDown(self):
        os.close(self.fd)
        self.temp.cleanup()

    def read(self, data, close=True):
        reader, writer = os.pipe()
        # Fixtures are deliberately small enough for one anonymous-pipe write.
        os.write(writer, data)
        if close:
            os.close(writer)
        try:
            return m.read_frame(reader, time.monotonic() + 0.03)
        finally:
            os.close(reader)
            if not close:
                os.close(writer)

    def stage(self):
        m.stage(self.fd, SYNTHETIC, self.deadline, os.getuid(), gid=os.getgid())

    def test_intact_and_maximum_frame(self):
        self.assertEqual(self.read(m.frame(SYNTHETIC)), SYNTHETIC)
        # A concurrent writer avoids pipe-capacity dependence at the upper bound.
        reader, writer = os.pipe()
        def produce():
            try:
                m.write_all(writer, m.frame(b'x' * m.LIMIT), self.deadline)
            finally:
                os.close(writer)
        thread = threading.Thread(target=produce)
        thread.start()
        try:
            self.assertEqual(m.read_frame(reader, self.deadline), b'x' * m.LIMIT)
        finally:
            os.close(reader)
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_bad_frames(self):
        good = m.frame(SYNTHETIC)
        cases = [b'', good[:3], good[:-1], good + b'x',
                 b'WRONG' + good[5:], m.MAGIC + struct.pack('!I', 0),
                 m.MAGIC + struct.pack('!I', m.LIMIT + 1),
                 good[:9] + b'X' + good[10:], good[:-len(m.TRAILER)] + b'bad']
        for data in cases:
            with self.subTest(case=cases.index(data)), self.assertRaises(m.Refused):
                self.read(data)

    def test_eof_required_and_timeout(self):
        for data in (b'', m.frame(SYNTHETIC), m.frame(SYNTHETIC)[:10]):
            with self.subTest(case=len(data)), self.assertRaisesRegex(m.Refused, '^transfer_timeout$'):
                self.read(data, close=False)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_empty_oversize_and_alias_rejected(self):
        for env in ({}, {'LINEAR_API_KEY': ''}, {'OFFMENU_LINEAR_API_KEY': 'synthetic'},
                    {'LINEAR_API_KEY': 'x' * (m.LIMIT + 1)}):
            reader, writer = os.pipe()
            try:
                with self.assertRaises(m.Refused):
                    m.send(writer, env, self.deadline)
                self.assertEqual(env, {})
            finally:
                os.close(reader)
                os.close(writer)

    def test_no_regular_or_tty_output(self):
        with tempfile.TemporaryFile(dir='/tmp') as regular:
            with self.assertRaisesRegex(m.Refused, '^pipe_required$'):
                m.send(regular.fileno(), {'LINEAR_API_KEY': 'synthetic'}, self.deadline)
            self.assertEqual(regular.tell(), 0)
        master, slave = pty.openpty()
        try:
            with self.assertRaisesRegex(m.Refused, '^pipe_required$'):
                m.send(slave, {'LINEAR_API_KEY': 'synthetic'}, self.deadline)
        finally:
            os.close(master)
            os.close(slave)

    def test_named_fifo_rejected(self):
        fifo = self.root / 'named'
        os.mkfifo(fifo, 0o600)
        fd = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
        try:
            with self.assertRaises(m.Refused):
                m.pipe_only(fd)
        finally:
            os.close(fd)

    def test_short_writes_interrupt_and_zero(self):
        original = os.write
        calls = 0
        def short(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise InterruptedError()
            return original(fd, data[:2])
        with patch.object(m.os, 'write', side_effect=short):
            self.stage()
        self.assertEqual((self.root / m.PARENT / m.FINAL).read_bytes(), SYNTHETIC)
        self.assertGreater(calls, 2)

    def test_zero_write_cleanup(self):
        with patch.object(m.os, 'write', return_value=0):
            with self.assertRaisesRegex(m.Refused, '^write_failed$'):
                self.stage()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_fsync_and_link_failure_cleanup(self):
        for operation in ('fsync', 'link'):
            with self.subTest(operation=operation), patch.object(m.os, operation, side_effect=OSError('synthetic')):
                with self.assertRaises(OSError):
                    self.stage()
            self.assertEqual(list(self.root.iterdir()), [])
        original = os.fsync
        calls = 0
        def fail_after_publication(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic')
            original(fd)
        with patch.object(m.os, 'fsync', side_effect=fail_after_publication):
            with self.assertRaises(OSError):
                self.stage()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_atomic_publication_and_nonoverwrite(self):
        original = os.link
        def inspect_then_link(src, dst, **kwargs):
            destination = self.root / m.PARENT / m.FINAL
            self.assertFalse(destination.exists())
            self.assertEqual((destination.parent / src).read_bytes(), SYNTHETIC)
            original(src, dst, **kwargs)
        with patch.object(m.os, 'link', side_effect=inspect_then_link):
            self.stage()
        target = self.root / m.PARENT / m.FINAL
        self.assertEqual(target.read_bytes(), SYNTHETIC)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual(target.read_bytes(), SYNTHETIC)
        self.assertEqual(len(list(target.parent.iterdir())), 1)

    def test_colliding_final_preserved(self):
        original = os.link
        def collision(src, dst, **kwargs):
            (self.root / m.PARENT / m.FINAL).write_bytes(b'preexisting-synthetic')
            original(src, dst, **kwargs)
        with patch.object(m.os, 'link', side_effect=collision):
            with self.assertRaises(FileExistsError):
                self.stage()
        self.assertEqual((self.root / m.PARENT / m.FINAL).read_bytes(), b'preexisting-synthetic')
        self.assertEqual([p.name for p in (self.root / m.PARENT).iterdir()], [m.FINAL])

    def test_preexisting_and_symlink_preserved(self):
        target = self.root / m.PARENT
        target.symlink_to('absent')
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertTrue(target.is_symlink())
        target.unlink()  # Synthetic fixture only.
        target.write_bytes(b'preexisting-synthetic')
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual(target.read_bytes(), b'preexisting-synthetic')

    def test_cleanup_preserves_replacement_inode(self):
        target = self.root / 'owned'
        target.write_bytes(b'first-synthetic')
        old = m.identity(target.stat())
        target.rename(self.root / 'retained')
        target.symlink_to('retained')
        m.remove_owned(self.fd, 'owned', old)
        self.assertTrue(target.is_symlink())

    def test_parent_permissions_rejected(self):
        self.root.chmod(0o777)
        with self.assertRaises(m.Refused):
            self.stage()
        self.assertEqual(list(self.root.iterdir()), [])
        self.root.chmod(0o700)

    def test_directory_owner_pair_rejects_each_wrong_id(self):
        uid, gid = os.getuid(), os.getgid()
        m.check_directory(self.fd, uid, 0o700, gid=gid)
        for expected_uid, expected_gid in ((uid + 1, gid), (uid, gid + 1)):
            with self.subTest(uid=expected_uid, gid=expected_gid):
                with self.assertRaisesRegex(m.Refused, '^directory_rejected$'):
                    m.check_directory(self.fd, expected_uid, 0o700, gid=expected_gid)
                with self.assertRaisesRegex(m.Refused, '^directory_rejected$'):
                    m.stage(self.fd, SYNTHETIC, self.deadline, expected_uid, gid=expected_gid)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_staging_file_wrong_group_rejected_and_cleaned(self):
        original_fstat = os.fstat
        def wrong_file_group(fd):
            info = original_fstat(fd)
            if m.stat.S_ISREG(info.st_mode):
                fields = list(info)
                fields[5] = os.getgid() + 1
                return os.stat_result(fields)
            return info
        # Inject bad file metadata; execute the real ownership guard and cleanup.
        with patch.object(m.os, 'fstat', side_effect=wrong_file_group):
            with self.assertRaisesRegex(m.Refused, '^file_rejected$'):
                self.stage()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_actual_synthetic_subprocess_pipeline(self):
        # Execute only internal core in child, never real receive CLI/root route.
        loader = ('import importlib.util,sys,os,time; '
                  's=importlib.util.spec_from_file_location("stage",sys.argv[1]); '
                  'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); ')
        sender = loader + 'm.send(1,os.environ,time.monotonic()+2)'
        receiver = loader + ('os.environ.clear(); f=os.open(sys.argv[2],os.O_RDONLY|os.O_DIRECTORY); '
                             'm.receive(0,f,time.monotonic()+2,os.getuid(), gid=os.getgid()); os.close(f)')
        environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
        with subprocess.Popen([sys.executable, '-I', '-c', sender, str(SOURCE)],
                              env={**environment, 'LINEAR_API_KEY': SYNTHETIC.decode()},
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as producer:
            result = subprocess.run([sys.executable, '-I', '-c', receiver, str(SOURCE), str(self.root)],
                                    env=environment, stdin=producer.stdout, capture_output=True, timeout=4)
            producer.stdout.close()
            _, diagnostics = producer.communicate(timeout=4)
        self.assertEqual(producer.returncode, 0)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(diagnostics + result.stdout + result.stderr, b'')
        self.assertEqual((self.root / m.PARENT / m.FINAL).read_bytes(), SYNTHETIC)

    def test_cli_fixed_diagnostics_without_receive(self):
        for args in ([], ['unknown'], ['send', 'extra']):
            result = subprocess.run([sys.executable, '-I', str(SOURCE), *args],
                                    env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'},
                                    capture_output=True, timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'status=mode_rejected\n')


class FileTests(TransferTests):
    def create_source(self, payload=SYNTHETIC):
        env = {'LINEAR_API_KEY': payload.decode(), 'UNRELATED': 'synthetic'}
        result = m.send_file(self.fd, env, self.deadline, os.getuid(), gid=os.getgid())
        self.assertEqual(env, {})
        self.directory = self.root / m.SOURCE_PARENT
        self.source = self.directory / m.SOURCE_FILE
        return result

    def test_file_roundtrip_bounds_and_preexistence(self):
        ids = self.create_source(b'x' * m.LIMIT)
        self.assertEqual(ids[1], m.identity(self.source.stat()))
        self.assertEqual(m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid()), b'x' * m.LIMIT)
        with self.assertRaises(FileExistsError):
            self.create_source()
        self.assertEqual(self.source.stat().st_size, m.MAX_FRAME)

    def test_source_routes_reject_wrong_directory_group(self):
        with self.assertRaisesRegex(m.Refused, '^directory_rejected$'):
            m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid() + 1)
        with self.assertRaisesRegex(m.Refused, '^directory_rejected$'):
            m.send_file(self.fd, {'LINEAR_API_KEY': SYNTHETIC.decode()},
                        self.deadline, os.getuid(), gid=os.getgid() + 1)

    def test_file_bad_metadata(self):
        self.create_source()
        for mode in (0o644, 0o400, 0o660):
            self.source.chmod(mode)
            with self.assertRaises(m.Refused):
                m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid())
        self.source.chmod(0o600)
        with self.assertRaises(m.Refused):
            m.read_source(self.fd, self.deadline, os.getuid() + 1, gid=os.getgid())
        # Exercise source UID independently of base-directory UID validation.
        with self.assertRaises(m.Refused):
            m.check_source(self.source.stat(), os.getuid() + 1)
        os.link(self.source, self.directory / 'extra')
        with self.assertRaises(m.Refused):
            m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid())

    def test_source_file_collision_preserved(self):
        original_mkdir = os.mkdir
        def collide(name, mode, **kwargs):
            original_mkdir(name, mode, **kwargs)
            directory = self.root / m.SOURCE_PARENT
            source = directory / m.SOURCE_FILE
            source.write_bytes(b'preexisting-synthetic')
            source.chmod(0o600)
        with patch.object(m.os, 'mkdir', side_effect=collide):
            with self.assertRaises(FileExistsError):
                self.create_source()
        self.assertEqual((self.root / m.SOURCE_PARENT / m.SOURCE_FILE).read_bytes(),
                         b'preexisting-synthetic')

    def test_source_symlinks_and_directory_modes(self):
        self.create_source()
        self.source.rename(self.directory / 'retained')
        self.source.symlink_to('retained')
        with self.assertRaises(OSError):
            m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid())
        self.directory.rename(self.root / 'retained-directory')
        self.directory.symlink_to('retained-directory')
        with self.assertRaises(OSError):
            m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid())
        with self.assertRaises(FileExistsError):
            self.create_source()
        self.assertTrue(self.directory.is_symlink())
        (self.root / 'retained-directory').chmod(0o755)
        fd = os.open(self.root / 'retained-directory', os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaises(m.Refused):
                m.check_directory(fd, os.getuid(), 0o700, gid=os.getgid())
        finally:
            os.close(fd)

    def test_file_frames_and_size(self):
        self.create_source()
        good = m.frame(SYNTHETIC)
        for data in (b'', good[:-1], good + b'x', b'x' * (m.MAX_FRAME + 1),
                     good[:9] + b'X' + good[10:], good[:-len(m.TRAILER)] + b'bad'):
            self.source.write_bytes(data)
            with self.assertRaises(m.Refused):
                m.read_source(self.fd, self.deadline, os.getuid(), gid=os.getgid())
        self.source.write_bytes(good)
        with self.assertRaisesRegex(m.Refused, 'transfer_timeout'):
            m.read_source(self.fd, time.monotonic() - 1, os.getuid(), gid=os.getgid())

    def test_change_and_path_replacement(self):
        for change in ('write', 'file', 'directory'):
            with self.subTest(change=change):
                # Each scenario owns a separate synthetic source/base.
                with tempfile.TemporaryDirectory(dir='/tmp') as base:
                    basefd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        m.send_file(basefd, {'LINEAR_API_KEY': SYNTHETIC.decode()},
                                    self.deadline, os.getuid(), gid=os.getgid())
                        directory = Path(base) / m.SOURCE_PARENT
                        source = directory / m.SOURCE_FILE
                        original = os.read
                        changed = False
                        def mutate(fd, count):
                            nonlocal changed
                            data = original(fd, count)
                            if not changed:
                                changed = True
                                if change == 'write':
                                    source.write_bytes(m.frame(b'changed-synthetic'))
                                elif change == 'file':
                                    source.rename(directory / 'retained')
                                    source.write_bytes(m.frame(SYNTHETIC))
                                    source.chmod(0o600)
                                else:
                                    directory.rename(Path(base) / 'retained')
                                    directory.mkdir(mode=0o700)
                            return data
                        with patch.object(m.os, 'read', side_effect=mutate):
                            with self.assertRaises(m.Refused):
                                m.read_source(basefd, self.deadline, os.getuid(), gid=os.getgid())
                    finally:
                        os.close(basefd)

    def test_sender_failure_cleanup_and_uncertainty(self):
        with patch.object(m.os, 'fsync', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                self.create_source()
        self.assertEqual(list(self.root.iterdir()), [])
        with patch.object(m.os, 'fsync', side_effect=OSError('synthetic')), \
                patch.object(m.os, 'unlink', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                self.create_source()
        self.assertTrue((self.root / m.SOURCE_PARENT / m.SOURCE_FILE).exists())
        with self.assertRaises(FileExistsError):
            self.create_source()

    def test_file_sender_environment_and_diagnostics(self):
        loader = ('import importlib.util,sys,os,time; '
                  's=importlib.util.spec_from_file_location("stage",sys.argv[1]); '
                  'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); ')
        code = loader + ('f=os.open(sys.argv[2],os.O_RDONLY|os.O_DIRECTORY); '
                         'm.send_file(f,os.environ,time.monotonic()+2,os.getuid(), gid=os.getgid()); '
                         'assert not os.environ; assert os.read(0,1)==b""; os.close(f)')
        argv = [sys.executable, '-I', '-c', code, str(SOURCE), str(self.root)]
        self.assertNotIn(SYNTHETIC.decode(), ' '.join(argv))
        result = subprocess.run(argv, env={'LINEAR_API_KEY': SYNTHETIC.decode()},
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=4)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, b'')

    def test_fixed_chain_symlinks(self):
        original_open = os.open
        original_check = m.check_directory
        for component in ('run', 'user', '1000'):
            with self.subTest(component=component), tempfile.TemporaryDirectory(dir='/tmp') as fixture:
                root = Path(fixture)
                (root / 'run/user/1000').mkdir(parents=True, mode=0o700)
                target = root / {'run': 'run', 'user': 'run/user',
                                 '1000': 'run/user/1000'}[component]
                retained = target.with_name('retained')
                target.rename(retained)
                target.symlink_to('retained')
                def redirected(path, flags, *args, **kwargs):
                    return original_open(fixture if path == '/' else path, flags, *args, **kwargs)
                def check(fd, uid, mode=None):
                    return original_check(fd, os.getuid(), mode, gid=os.getgid())
                with patch.object(m.os, 'open', side_effect=redirected), \
                        patch.object(m, 'check_directory', side_effect=check), \
                        patch.object(m, 'check_volatile') as volatile:
                    with self.assertRaises(OSError):
                        m.file_route('receive-file', self.deadline)
                    volatile.assert_not_called()

    def test_receive_cli_clears_environment_before_route(self):
        from io import StringIO
        environment = {'LINEAR_API_KEY': SYNTHETIC.decode()}
        def route(mode, deadline):
            self.assertEqual(environment, {})
            raise m.Refused('source_rejected')
        with patch.object(m.os, 'environ', environment), \
                patch.object(m.sys, 'argv', ['helper', 'receive-file']), \
                patch.object(m.sys, 'flags') as flags, \
                patch.object(m.os, 'getuid', return_value=0), \
                patch.object(m.os, 'geteuid', return_value=0), \
                patch.object(m.os, 'getegid', return_value=0), \
                patch.object(m.os, 'umask'), \
                patch.object(m.resource, 'setrlimit'), \
                patch.object(m.signal, 'signal'), patch.object(m.signal, 'alarm'), \
                patch.object(m, 'file_route', side_effect=route), \
                patch.object(m.sys, 'stderr', StringIO()) as diagnostics:
            flags.isolated = True
            self.assertEqual(m.main(), 1)
            self.assertEqual(diagnostics.getvalue(), 'status=source_rejected\n')
        self.assertEqual(environment, {})

    def test_receive_cli_rejects_wrong_user_or_group_before_route(self):
        from io import StringIO
        for uid, euid, egid in ((1, 0, 0), (0, 1, 0), (0, 0, 977)):
            with self.subTest(uid=uid, euid=euid, egid=egid), \
                    patch.object(m.os, 'environ', {}), \
                    patch.object(m.sys, 'argv', ['helper', 'receive-file']), \
                    patch.object(m.sys, 'flags') as flags, \
                    patch.object(m.os, 'getuid', return_value=uid), \
                    patch.object(m.os, 'geteuid', return_value=euid), \
                    patch.object(m.os, 'getegid', return_value=egid), \
                    patch.object(m.resource, 'setrlimit'), \
                    patch.object(m.signal, 'signal'), patch.object(m.signal, 'alarm'), \
                    patch.object(m, 'file_route') as route, \
                    patch.object(m.sys, 'stderr', StringIO()) as diagnostics:
                flags.isolated = True
                self.assertEqual(m.main(), 1)
                self.assertEqual(diagnostics.getvalue(), 'status=root_receiver_required\n')
                route.assert_not_called()

    def test_mount_unknown_refused(self):
        from io import StringIO
        device = os.fstat(self.fd).st_dev
        line = ('1 0 %d:%d / /run/user/1000 rw - tmpfs tmpfs rw\n'
                % (os.major(device), os.minor(device)))
        for text in ('', line.replace('tmpfs', 'ext4'), line + line,
                     line.replace('/run/user/1000', '/tmp'), line.replace(' / /run', ' /sub /run')):
            with patch('builtins.open', return_value=StringIO(text)):
                with self.assertRaises(m.Refused):
                    m.check_volatile(self.fd)
        with patch('builtins.open', return_value=StringIO(line)):
            m.check_volatile(self.fd)


if __name__ == '__main__':
    unittest.main()
