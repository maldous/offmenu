"""Source contract only. This suite neither files an issue nor contacts a tracker."""
import unittest
from pathlib import Path

import yaml  # Pinned in tools/delivery/requirements.lock.


FORM = Path(__file__).resolve().parents[2] / ".github/ISSUE_TEMPLATE/translation-feedback.yml"


class UniqueKeys(yaml.SafeLoader):
    """Don't silently accept a duplicate YAML key that changes a form contract."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"duplicate key: {key}")
            seen.add(key)
        return super().construct_mapping(node, deep)


class TranslationFeedbackForm(unittest.TestCase):
    def setUp(self):
        self.form = yaml.load(FORM.read_text(encoding="utf-8"), Loader=UniqueKeys)
        self.intro, *self.questions = self.form["body"]

    def test_uses_plain_named_fields_with_no_account_or_routing_choices(self):
        self.assertEqual(set(self.form), {"name", "description", "title", "body"})
        self.assertEqual(self.form["name"], "Suggest a better translation")
        self.assertTrue(self.form["description"].strip())
        self.assertEqual(self.form["title"].strip(), "Translation suggestion:")
        self.assertEqual(self.intro["type"], "markdown")
        self.assertEqual([q["id"] for q in self.questions],
                         ["language", "location", "current", "suggestion", "context"])
        labels = [q["attributes"]["label"] for q in self.questions]
        self.assertTrue(all(isinstance(label, str) and label.strip() for label in labels))
        self.assertEqual(len(labels), len(set(labels)))
        self.assertTrue(all(q["type"] == "input" for q in self.questions))

    def test_only_minimum_three_answers_are_required(self):
        for q in self.questions:
            with self.subTest(question=q["id"]):
                required = q.get("validations", {}).get("required", False)
                self.assertIs(type(required), bool)
                self.assertEqual(required, q["id"] in {"language", "location", "suggestion"})
                if not required:
                    self.assertIn("optional", q["attributes"]["label"].lower())

    def test_privacy_warning_comes_before_any_answer(self):
        text = self.intro["attributes"]["value"].lower()
        for warning in ("public", "github username", "private information",
                        "screenshots", "contact details", "security reports"):
            with self.subTest(warning=warning):
                self.assertIn(warning, text)
        self.assertNotIn("assignees", self.form)
        self.assertNotIn("labels", self.form)


if __name__ == "__main__":
    unittest.main()
