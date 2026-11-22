"""Source-only drift checks; no browser, application import, account, or HTTP."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps/web/assets/data-workspace.html"
JS = ROOT / "apps/web/src/data-workspace.js"
GUIDE = ROOT / "docs/data-workspace-control-help.md"
IMPORT_GUIDE = ROOT / "docs/data-import-guide.md"
ROW = re.compile(r"^\| `([^`]+)` \| ([^|]+?) \| ([^|]+?) \|$", re.M)


class Surface(HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            key = "href:" + attrs["href"]
            if attrs["href"] == "/" and "workspace-brand" in (attrs.get("class") or "").split():
                key = 'a.workspace-brand[href="/"]'
        elif tag == "summary":
            key = "summary:" + attrs["data-i18n"]
        elif tag in {"button", "input", "select", "textarea"}:
            if tag == "button" and "data-theme-toggle" in attrs:
                key = "button[data-theme-toggle]"
            elif attrs.get("id"):
                key = attrs["id"]
            else:
                raise AssertionError(f"Unidentified <{tag}> control at H{self.getpos()[0]}")
        else:
            return
        self.controls.append((key, self.getpos()[0]))


class TestWorkspaceHelp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = GUIDE.read_text()
        cls.rows = ROW.findall(cls.doc)
        cls.by_id = {key: (source, help_text) for key, source, help_text in cls.rows}
        cls.surface = Surface()
        cls.surface.feed(HTML.read_text())
        cls.js = JS.read_text()

    def test_every_static_control_and_dynamic_group_has_one_row(self):
        expected = [key for key, _ in self.surface.controls]
        expected.append("dynamic:health-results/delete-group")
        self.assertEqual(Counter(key for key, _, _ in self.rows), Counter(expected))
        self.assertEqual(len(set(expected)), len(expected))
        for key, line in self.surface.controls:
            self.assertRegex(self.by_id[key][0], rf"\bH{line}\b", key)

    def test_action_rows_reference_the_current_binding(self):
        def cited_lines(source):
            result = set()
            for first, last in re.findall(r"\bJ(\d+)(?:[–-](\d+))?", source):
                result.update(range(int(first), int(last or first) + 1))
            return result
        for line_no, line in enumerate(self.js.splitlines(), start=1):
            for action in re.findall(r"\baction\('([^']+)'", line):
                self.assertIn(action, self.by_id)
                self.assertIn(line_no, cited_lines(self.by_id[action][0]), action)

    def test_dynamic_controls_have_explicit_classification(self):
        # Fail this bounded inventory when a new dynamic interactive element is
        # added rather than silently classifying it as one of today's controls.
        tags = re.findall(r"createElement\(['\"](a|button|input|select|option|textarea|summary)['\"]\)", self.js)
        self.assertEqual(Counter(tags), {"a": 1, "button": 1, "option": 1})
        dynamic = [line for line in self.js.splitlines() if "document.createElement('button')" in line]
        self.assertEqual(len(dynamic), 1)
        self.assertIn("Delete measurement group", dynamic[0])
        self.assertIn("$('health-results').append(button)", dynamic[0])
        self.assertIn("delete one returned group", self.by_id["dynamic:health-results/delete-group"][1])
        self.assertIn("download anchor", self.doc)
        self.assertIn("country options", self.doc)

    def test_navigation_and_distinct_task_destinations(self):
        self.assertIn("](data-workspace-control-help.md)", IMPORT_GUIDE.read_text())
        self.assertIn("](data-import-guide.md)", self.doc)
        headings = {
            re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
            for h in re.findall(r"^## (.+)$", self.doc, re.M)
        }
        task_links = re.findall(r"\]\(#([^\)]+)\)", self.doc)
        self.assertEqual(len(set(task_links)), 4)
        self.assertLessEqual(set(task_links), headings)


if __name__ == "__main__":
    unittest.main()
