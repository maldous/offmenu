import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "origin_type_register_builder", ROOT / "scripts" / "build-origin-type-register.py"
)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def cell(*, parsed=None, exact=None, bound=None, candidates=None, unresolved=None):
    return {
        "parsedRecordIds": parsed or [],
        "sources": {
            "boundAssetIds": bound or [],
            "candidateAssetIds": candidates or [],
            "unresolvedAssetReferences": unresolved or [],
        },
        "evidence": {"exactTypeBindings": exact or []},
    }


class OriginTypeStatusTests(unittest.TestCase):
    def test_parsed_records_are_partial_evidence_even_with_bindings(self):
        status, _ = BUILDER.cell_status(cell(parsed=["record-1"], exact=["asset-1"]))
        self.assertEqual(status, "parsed-evidence-partial")

    def test_exact_binding_without_records(self):
        status, _ = BUILDER.cell_status(cell(exact=["asset-1"], bound=["asset-1"]))
        self.assertEqual(status, "explicit-type-binding-no-records")

    def test_registered_asset_without_exact_type_binding(self):
        status, _ = BUILDER.cell_status(cell(bound=["asset-1"]))
        self.assertEqual(status, "registered-source-evidence-unbound")

    def test_candidate_and_unresolved_reference(self):
        status, _ = BUILDER.cell_status(cell(candidates=["candidate-1"], unresolved=["unknown-1"]))
        self.assertEqual(status, "discovery-candidates-plus-unresolved-references")

    def test_candidate_only(self):
        status, _ = BUILDER.cell_status(cell(candidates=["candidate-1"]))
        self.assertEqual(status, "discovery-candidates-unbound")

    def test_unresolved_reference_only(self):
        status, _ = BUILDER.cell_status(cell(unresolved=["unknown-1"]))
        self.assertEqual(status, "unresolved-source-references")

    def test_no_candidate_is_not_a_source_absence_claim(self):
        status, basis = BUILDER.cell_status(cell())
        self.assertEqual(status, "no-candidate-in-reconciled-inputs")
        self.assertIn("not proof that no source exists", basis)

    def test_all_statuses_have_a_basis(self):
        self.assertEqual(set(BUILDER.STATUS_BASIS), BUILDER.KNOWN_CELL_STATUSES)
        self.assertTrue(all(BUILDER.STATUS_BASIS.values()))


if __name__ == "__main__":
    unittest.main()
