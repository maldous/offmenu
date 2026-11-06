# Portable selected-contract test fixtures

`selected/package-contract/common-data.schema.json` contains the exact existing eight-package schema bytes, SHA256 `89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c`. These were copied byte-for-byte from the retained local producer source `offmenu-bulk-parallel256-20261028/corpus/common-data.schema.json`, not synthesized or changed.

Recipe inspector tests now resolve that fixture relative to this source packet rather than an author's absolute workspace path. The tested schema pin and runtime code remain unchanged. This is a test-fixture portability correction, not a repeated corpus execution or replacement schema.

The separate `selected/corpus/common-data.schema.json` is the retained newer Git04df schema, SHA256 `f1968889c5e1500e841517bd7546af9c223bf97dce40bb68a3f584e93559298c`. Some synthetic author fixtures deliberately use it with an explicit test-only schema parameter. Production runners continue to bind the canonical eight-package schema. These two contracts must not be conflated.

All test records are synthetic. The exact retained `selected/scripts/align-bulk-food-common.py` is imported only for its pure packet projection in basis-restoration tests, to verify compatibility with the real prior normalization semantics. No source acquisition or raw record export is performed by these tests.
