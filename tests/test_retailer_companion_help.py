"""Check the distributed retailer README against the source, without a browser."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "apps/retailer-extension"
DOC = (PACKAGE / "README.md").read_text()


class Popup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.checkboxes = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button":
            self.buttons.append(attrs["data-i18n"])
        elif tag == "input":
            self.checkboxes.append((attrs["type"], attrs["id"]))
        elif tag == "a":
            self.links.append((attrs["href"], attrs["data-i18n"]))


class TestCompanionHelp(unittest.TestCase):
    def test_visible_control_labels_and_manifest_permissions(self):
        popup = Popup()
        popup.feed((PACKAGE / "popup.html").read_text())
        self.assertEqual(popup.checkboxes, [("checkbox", "confirm")])
        self.assertEqual(len(popup.buttons), 2)
        self.assertEqual(len(popup.links), 1)
        for label in popup.buttons + [popup.links[0][1]]:
            self.assertIn('**' + label + '**', DOC)
        self.assertIn("I reviewed the product, price, currency and source terms", DOC)
        manifest = json.loads((PACKAGE / "manifest.json").read_text())
        self.assertEqual(set(manifest["permissions"]), {"activeTab", "scripting"})
        self.assertNotIn("host_permissions", manifest)
        self.assertEqual(manifest["action"]["default_popup"], "popup.html")

    def test_build_paths_are_real_and_readme_survives_packaging(self):
        options = (ROOT / "scripts/extension-build-options.mjs").read_text()
        build = (ROOT / "scripts/build.mjs").read_text()
        for rel in ("apps/retailer-extension/popup.js", "apps/retailer-extension/popup-source.js"):
            self.assertIn(rel, DOC)
            self.assertIn(rel, options)
            self.assertTrue((ROOT / rel).is_file())
        self.assertIn("dist/retailer-extension.zip", build)
        self.assertIn("offmenu-retailer-extension/", build)
        self.assertIn("'README.md'", build)
        # The README also ships inside the ZIP without a docs/ directory.
        links = re.findall(r"\]\(([^)]+)\)", DOC)
        self.assertTrue(links)
        self.assertTrue(all(link.startswith("https://github.com/maldous/offmenu/") for link in links))
        for link in links:
            _, edition, target = link.rsplit("/offmenu/", 1)[1].split("/", 2)
            self.assertRegex(edition, r"^[a-f0-9]{40}$")
            self.assertTrue((ROOT / target).exists(), target)

    def test_import_route_and_caution_are_bound_to_current_source(self):
        self.assertIn("Bring your files, too", (ROOT / "docs/data-import-guide.md").read_text())
        self.assertIn("Your retailer browser session", (ROOT / "apps/web/src/sources.js").read_text())
        popup = (PACKAGE / "popup-source.js").read_text()
        for phrase in ("Unable to read this page", "No supported structured product data found", "offmenu-retailer-import.json"):
            self.assertIn(phrase, popup)
            self.assertIn(phrase, DOC)


if __name__ == "__main__":
    unittest.main()
