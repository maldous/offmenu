import asyncio
import os
from pathlib import Path
import sys
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import native_harness_runtime as runtime


class FixedPublisherTransportTest(IsolatedAsyncioTestCase):
    async def test_retained_child_writer_does_not_keep_our_read_pipes_open(self):
        code = (
            "import os,sys,time\n"
            "sys.stdin.buffer.read()\n"
            "if os.fork() == 0:\n"
            " time.sleep(1.5); os._exit(0)\n"
            "os._exit(0)\n"
        )
        loop = asyncio.get_running_loop()
        original_connect, original_timeout = loop.connect_read_pipe, asyncio.timeout
        opened, deadlines, processes = [], [], []
        original_spawn = asyncio.create_subprocess_exec

        async def spawn(*args, **kwargs):
            process = await original_spawn(*args, **kwargs)
            processes.append(process)
            return process

        async def track(factory, source):
            result = await original_connect(factory, source)
            opened.append((source, result[0]))
            return result

        def shorter(seconds):
            deadlines.append(seconds)
            return original_timeout(0.2 if seconds == 25 else seconds)

        with patch.object(runtime, 'PUBLISHER_HELPER_ARGV', (sys.executable, '-c', code)), \
                patch.object(loop, 'connect_read_pipe', side_effect=track), \
                patch.object(asyncio, 'create_subprocess_exec', side_effect=spawn), \
                patch.object(asyncio, 'timeout', side_effect=shorter):
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(runtime.fixed_invocation_wire({'fixture': True}), 0.8)
        await asyncio.sleep(0)
        self.assertEqual(deadlines, [25])
        self.assertEqual([process.returncode for process in processes], [0])
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(source.closed and transport.is_closing() for source, transport in opened))

    async def test_fdopen_failure_closes_both_raw_descriptors(self):
        original_pipe, original_fdopen = os.pipe, os.fdopen
        target = []

        def pipe():
            descriptors = original_pipe()
            target.extend(descriptors)
            return descriptors

        def fdopen(fd, *args, **kwargs):
            if target and fd == target[0]:
                raise OSError('fixture-fdopen-failure')
            return original_fdopen(fd, *args, **kwargs)

        with patch.object(os, 'pipe', side_effect=pipe), \
                patch.object(os, 'fdopen', side_effect=fdopen):
            with self.assertRaisesRegex(OSError, 'fixture-fdopen-failure'):
                await runtime.fixed_invocation_wire({'fixture': True})
        self.assertEqual(len(target), 2)
        try:
            for fd in target:
                with self.assertRaises(OSError):
                    os.fstat(fd)
        finally:
            for fd in target:
                try:
                    os.close(fd)
                except OSError:
                    pass

    async def test_normal_stdout_stays_separate_from_stderr(self):
        code = "import sys; sys.stderr.write('diagnostic'); sys.stdout.buffer.write(sys.stdin.buffer.read())"
        with patch.object(runtime, 'PUBLISHER_HELPER_ARGV', (sys.executable, '-c', code)):
            self.assertEqual(await runtime.fixed_invocation_wire({'fixture': True}), b'{"fixture": true}')
