"""Exercise the offline CLI against disposable target-layout Git repositories."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check_final_layout.py"


class FinalLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.policy = {
            "schema_version": 1,
            "version": "2.0.0",
            "roots": {name: {"kind": "source", "owner": "maintainers"} for name in (
                "repository-standard.json", ".gitignore", "app", "tools", "tests",
            )},
            "retired_roots": ["scripts", "old-app"],
            "required_paths": ["app/main.py", "tests"],
            "runtime_hold_paths": ["scripts/windmill/runtime.py"],
        }
        self.write_policy()
        self.write("app/main.py")
        self.write("tests/test_app.py")
        self.write(".gitignore", "node_modules/\n.delivery/\n.venv-delivery/\ndata/\n"
                   "output/\ndist/\n*.egg-info/\n__pycache__/\n.env\n.env.*\n*.key\n*.pem\n")
        self.git("add", ".")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, path, content="fixture\n"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def write_policy(self):
        self.write("repository-standard.json", json.dumps(self.policy))

    def run_audit(self, expected=0, root=None, default_root=False):
        command = [sys.executable, str(SCRIPT)]
        if not default_root:
            command.extend(["--root", str(root or self.root)])
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True,
                                timeout=15, check=False)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["violations"], len(report["violations"]))
        return report

    def test_valid_target_with_ignored_runtime_passes(self):
        for directory in ("node_modules", ".delivery", ".venv-delivery", "data",
                          "output", "dist", "package.egg-info", "__pycache__"):
            self.write(directory + "/not-scanned.py", "PRIVATE_CONTENT_MUST_NOT_APPEAR")
        self.write(".env", "PRIVATE_CONTENT_MUST_NOT_APPEAR")
        self.write("tools/check.py")  # Nonignored untracked current source is included.
        first = self.run_audit()
        self.assertEqual(first["violations"], [])
        self.assertEqual(first["counts"]["untracked"], 1)
        self.assertEqual(first["counts"]["checked"], 5)
        self.assertEqual(first, self.run_audit(default_root=True))
        self.assertTrue((self.root / "data/not-scanned.py").exists())

    def test_retired_source_tracked_or_untracked_fails(self):
        self.write("old-app/tracked.py")
        self.git("add", "old-app")
        self.write("scripts/new.py")
        self.assertEqual(self.run_audit(1)["violations"], [
            {"path": "old-app/tracked.py", "rule": "retired_root"},
            {"path": "scripts/new.py", "rule": "retired_root"},
        ])

    def test_exact_hold_excluded_nearby_source_checked(self):
        self.write("scripts/windmill/runtime.py")
        report = self.run_audit()
        self.assertEqual(report["counts"]["excluded_holds"], 1)
        self.write("scripts/windmill/runtime.py.extra")
        self.write("scripts/windmill/nearby.py")
        report = self.run_audit(1)
        self.assertEqual({v["path"] for v in report["violations"]}, {
            "scripts/windmill/runtime.py.extra", "scripts/windmill/nearby.py",
        })

    def test_tracked_hold_is_not_exempt(self):
        self.write("scripts/windmill/runtime.py")
        self.git("add", "scripts/windmill/runtime.py")
        self.assertEqual(self.run_audit(1)["violations"], [
            {"path": "scripts/windmill/runtime.py", "rule": "retired_root"},
        ])

    def test_unclassified_tracked_and_untracked_roots(self):
        self.write("unknown/committed.py")
        self.git("add", "unknown")
        self.write("other/untracked.py")
        report = self.run_audit(1)
        self.assertEqual({v["path"] for v in report["violations"]}, {
            "unknown/committed.py", "other/untracked.py",
        })
        self.assertTrue(all(v["rule"] == "unclassified_root" for v in report["violations"]))

    def test_missing_required_path(self):
        (self.root / "app/main.py").unlink()
        report = self.run_audit(1)
        self.assertEqual(report["counts"]["excluded_missing"], 1)
        self.assertEqual(report["violations"], [
            {"path": "app/main.py", "rule": "missing_required_path"},
        ])

    def test_missing_pending_rename_path_excluded(self):
        self.write("old-app/main.py")
        self.git("add", "old-app/main.py")
        (self.root / "old-app/main.py").rename(self.root / "app/moved.py")
        report = self.run_audit()
        self.assertEqual(report["counts"]["excluded_missing"], 1)
        self.assertEqual(report["counts"]["untracked"], 1)

    def test_tracked_private_artifacts_fail_even_when_ignored(self):
        paths = [directory + "/artifact" for directory in (
            "node_modules", ".delivery", ".venv-delivery", "data", "output",
            "dist", "pkg.egg-info", "__pycache__",
        )] + ["app/.env", "app/.env.local", "app/token.key", "app/cert.pem",
             "app/nested/node_modules/dependency.js"]
        for path in paths:
            self.write(path, "PRIVATE_CONTENT_MUST_NOT_APPEAR")
        self.git("add", "-f", "--", *paths)
        report = self.run_audit(1)
        self.assertEqual({v["path"] for v in report["violations"]
                          if v["rule"] == "tracked_private_artifact"}, set(paths))
        self.assertNotIn("PRIVATE_CONTENT_MUST_NOT_APPEAR", json.dumps(report))

    def test_nul_delimited_git_paths(self):
        self.write("unknown/space and\nnewline.py")
        self.assertEqual(self.run_audit(1)["violations"], [
            {"path": "unknown/space and\nnewline.py", "rule": "unclassified_root"},
        ])

    def test_malformed_contracts_fail_closed(self):
        original = json.dumps(self.policy)
        for field, value in (
            ("retired_roots", None), ("required_paths", "app"),
            ("runtime_hold_paths", ["scripts/"]), ("roots", []),
            ("roots", {"app": {}}), ("version", None), ("schema_version", True),
            ("required_paths", ["../outside"]), ("runtime_hold_paths", ["scripts/*"]),
            ("required_paths", ["app", "app"]),
        ):
            with self.subTest(field=field, value=value):
                self.policy = json.loads(original)
                self.policy[field] = value
                self.write_policy()
                self.assertEqual(self.run_audit(1)["violations"][0]["rule"], "contract." + field)
        for content in ("{", "[]", '{"version": "1.0.0", "version": "2.0.0"}'):
            with self.subTest(content=content):
                self.write("repository-standard.json", content)
                self.assertTrue(self.run_audit(1)["violations"][0]["rule"].startswith("contract."))

    def test_missing_contract_fails_closed(self):
        (self.root / "repository-standard.json").unlink()
        self.assertEqual(self.run_audit(1)["violations"][0]["rule"],
                         "contract.unreadable_or_invalid_json")

    def test_git_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as nonrepo:
            report = self.run_audit(1, root=Path(nonrepo))
            self.assertEqual(report["violations"], [
                {"path": ".", "rule": "git.command_failed"},
            ])

    def test_subdirectory_rejected(self):
        self.assertEqual(self.run_audit(1, root=self.root / "app")["violations"], [
            {"path": ".", "rule": "git.repository_root_required"},
        ])


if __name__ == "__main__":
    unittest.main()
