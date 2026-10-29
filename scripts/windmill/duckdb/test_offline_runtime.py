import base64
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock
import zipfile

import install_offline as installer
import transfer_helper as transfer
import runtime


def fixture(path, extra=None, corrupt_record=False, duplicate=False):
    dist = installer.DIST
    values = {
        dist + "/METADATA": b'Name: duckdb\nVersion: 1.5.6\nRequires-Dist: numpy; extra == "all"\n',
        dist + "/WHEEL": b'Wheel-Version: 1.0\nTag: cp312-cp312-manylinux_2_26_x86_64\nTag: cp312-cp312-manylinux_2_28_x86_64\n',
        dist + "/licenses/LICENSE": b'Copyright 2018-2026 Stichting DuckDB Foundation\nPermission is hereby granted, free of charge',
        "duckdb/__init__.py": b"# synthetic, never executed\n",
    }
    if extra:
        values.update(extra)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    for name, value in values.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip("=")
        writer.writerow([name, "sha256=" + digest, str(len(value) + (1 if corrupt_record else 0))])
    writer.writerow([dist + "/RECORD", "", ""])
    values[dist + "/RECORD"] = stream.getvalue().encode()
    with zipfile.ZipFile(path, "w") as z:
        for name, value in values.items():
            if name.endswith("symlink"):
                i = zipfile.ZipInfo(name)
                i.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(i, value)
            else:
                z.writestr(name, value)
        if duplicate:
            z.writestr("duckdb/__init__.py", b"duplicate")
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.whl"

    def verify(self, **kwargs):
        digest, size = fixture(self.path, **kwargs)
        installer.verify_archive(self.path, digest, size)

    def test_reviewed_shape_passes(self):
        self.verify()

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(extra={"duckdb/../../escape": b"bad"})

    def test_absolute_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(extra={"/tmp/escape": b"bad"})

    def test_symlink_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(extra={"duckdb/symlink": b"/etc/passwd"})

    def test_pth_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(extra={"duckdb/evil.pth": b"import evil"})

    def test_record_tamper_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(corrupt_record=True)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(duplicate=True)

    def test_required_dependency_rejected(self):
        with self.assertRaises(ValueError):
            self.verify(extra={installer.DIST + "/METADATA": b"Name: duckdb\nVersion: 1.5.6\nRequires-Dist: unreviewed\n"})

    def test_digest_tamper_rejected(self):
        digest, size = fixture(self.path)
        with self.assertRaises(ValueError):
            installer.verify_archive(self.path, "0" * 64, size)

    def test_wheel_hardlink_rejected(self):
        digest, size = fixture(self.path)
        os.link(self.path, self.path.with_suffix(".linked"))
        with self.assertRaises(ValueError):
            installer.verify_archive(self.path, digest, size)


class TransferTests(unittest.TestCase):
    def test_chunk_bound(self):
        cmd = transfer.chunk_command("a" * 32, 0, b"\x00" * transfer.CHUNK_SIZE)
        self.assertLessEqual(len(json.dumps({"command": cmd}).encode()), 65536)
        compile(shlex.split(cmd)[-1], "<remote>", "exec")

    def test_invalid_stage_rejected(self):
        for value in ["../escape", "a" * 33, "A" * 32, "' ; id"]:
            with self.assertRaises(ValueError):
                transfer.status_command(value)

    def test_chunk_size_rejected(self):
        with self.assertRaises(ValueError):
            transfer.chunk_command("a" * 32, 0, b"a" * (transfer.CHUNK_SIZE + 1))

    def test_offset_bounds(self):
        for offset in [-1, transfer.SIZE, "1", True]:
            with self.assertRaises(ValueError):
                transfer.chunk_command("a" * 32, offset, b"x")

    def test_preparation_bound(self):
        names = {"install_offline.py", "runtime.py", "lock.json", "requirements.lock", "LICENSE.duckdb"}
        files = {n: Path(__file__).with_name(n).read_bytes() for n in names}
        cmd = transfer.prepare_command("a" * 32, files)
        self.assertLessEqual(len(json.dumps({"command": cmd}).encode()), 65536)
        compile(shlex.split(cmd)[-1], "<remote>", "exec")

    def test_install_command_syntax(self):
        compile(shlex.split(transfer.install_command("a" * 32))[-1], "<remote>", "exec")

    def test_budget_defaults(self):
        self.assertEqual(runtime.validated_budget(), {"threads":4,"memory_gib":8,"temp_gib":20})

    def test_reviewed_reduced_budget(self):
        self.assertEqual(runtime.validated_budget({"threads":1})["threads"], 1)

    def test_budget_escalation_rejected(self):
        for value in ({"threads":5},{"memory_gib":9},{"temp_gib":21},{"threads":True},{"threads":0},{"unbounded":1}):
            with self.assertRaises(ValueError):
                runtime.validated_budget(value)


class ReceiverExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        original = transfer.ROOT
        transfer.ROOT = self.temp.name
        self.addCleanup(setattr, transfer, "ROOT", original)
        self.stage = Path(transfer.stage_path("a" * 32))
        self.stage.mkdir(mode=0o700)
        self.wheel = self.stage / transfer.FILENAME
        self.wheel.touch(mode=0o600)

    def execute(self, offset, value):
        code = shlex.split(transfer.chunk_command("a" * 32, offset, value))[-1]
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exec(code, {"__name__": "synthetic_receiver"})
        return json.loads(stream.getvalue())

    def test_append_and_idempotent_retry(self):
        self.assertEqual(self.execute(0, b"first"), {"offset": 5})
        self.assertEqual(self.execute(0, b"first"), {"offset": 5})
        self.assertEqual(self.execute(5, b"second"), {"offset": 11})
        self.assertEqual(self.wheel.read_bytes(), b"firstsecond")

    def test_conflicting_retry_rejected(self):
        self.execute(0, b"first")
        with self.assertRaises(ValueError):
            self.execute(0, b"other")
        self.assertEqual(self.wheel.read_bytes(), b"first")

    def test_wrong_offset_rejected(self):
        with self.assertRaises(ValueError):
            self.execute(1, b"not-written")
        self.assertEqual(self.wheel.read_bytes(), b"")

    def test_symlink_target_rejected(self):
        target = self.stage / "untouched"
        target.write_bytes(b"untouched")
        self.wheel.unlink()
        self.wheel.symlink_to(target)
        with self.assertRaises(OSError):
            self.execute(0, b"not-written")
        self.assertEqual(target.read_bytes(), b"untouched")

    def test_hardlink_target_rejected(self):
        os.link(self.wheel, self.stage / "untouched")
        with self.assertRaises(ValueError):
            self.execute(0, b"not-written")
        self.assertEqual(self.wheel.read_bytes(), b"")


class ConfigurationOrderingTests(unittest.TestCase):
    def test_allowlist_precedes_external_disable_and_lock(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            connection = mock.Mock()
            fake = types.SimpleNamespace(__version__="1.5.6", connect=mock.Mock(return_value=connection))
            with mock.patch.dict(sys.modules, {"duckdb":fake}), mock.patch.object(sys, "path", list(sys.path)):
                self.assertIs(runtime.connect([directory], directory), connection)
            config = fake.connect.call_args.kwargs["config"]
            self.assertNotIn("allowed_directories", config)
            self.assertNotIn("enable_external_access", config)
            self.assertEqual(connection.execute.call_args_list, [
                mock.call("SET allowed_directories = ?", [[str(directory) + os.sep]]),
                mock.call("SET enable_external_access = false"),
                mock.call("SET lock_configuration = true"),
            ])

    def test_setup_failure_closes_connection(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            connection = mock.Mock()
            connection.execute.side_effect = RuntimeError("synthetic config failure")
            fake = types.SimpleNamespace(__version__="1.5.6", connect=mock.Mock(return_value=connection))
            with mock.patch.dict(sys.modules, {"duckdb":fake}), mock.patch.object(sys, "path", list(sys.path)):
                with self.assertRaises(RuntimeError):
                    runtime.connect([directory], directory)
            connection.close.assert_called_once()

    def test_allowlist_binds_paths_as_data(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td) / "test'path"
            directory.mkdir()
            connection = mock.Mock()
            fake = types.SimpleNamespace(__version__="1.5.6", connect=mock.Mock(return_value=connection))
            with mock.patch.dict(sys.modules, {"duckdb":fake}), mock.patch.object(sys, "path", list(sys.path)):
                runtime.connect([directory], directory)
            self.assertEqual(connection.execute.call_args_list[0],
                             mock.call("SET allowed_directories = ?", [[str(directory) + os.sep]]))



if __name__ == "__main__":
    unittest.main()
