# Selected source-processing tools

The source modules, contracts, and synthetic tests live in
[`tools/source-processing/`](../../tools/source-processing/). This is a
trusted-caller seam for explicitly selected source inputs; moving it does not
admit new inputs, authorize live lookup, or accept unfinished application work.

| Guide | Scope |
| --- | --- |
| [Barcode lookup](gold-barcode-lookup.md) | Qualified selected barcode observations |
| [Generated menu](gold-generated-menu.md) | Verified generated menu reader |
| [Recipe-label scenario](gold-recipe-label-scenario.md) | Synthetic label demonstration |
| [Relation alternatives](relation-alternatives.md) | Source-scoped alternatives |
| [Context presentation](source-context-presentation.md) | Verified source context presentation |
| [Literal recipe quantities](source-literal-recipe-quantities.md) | Original source quantities |
| [Recipe literal facts](source-recipe-literal-facts.md) | Source literal recipe facts |
| [Recipe product proofs](source-recipe-product-proofs.md) | Trusted-caller proof obligations |
| [Reference profile](source-reference-profile.md) | Qualified source-reference subset |

Run generated-only Python tests from the repository root:

```sh
python3 -B -m unittest discover -s tools/source-processing/tests -v
```

The JavaScript scenario uses the same relocated source:

```sh
node --test tests/web/gold-recipe-label-scenario.test.mjs
```

The 2026-10-29 layout migration moved the former `manual-action/` source tree
into `tools/source-processing/` and its guides here using lower-case kebab
filenames. Historical native-helper source paths inside the pinned test closure
remain unchanged. Dated evidence and content hashes were not rewritten.

Check relocated source presence, Python syntax, schema paths, and native-fixture
bytes against the immutable pre-migration commit:

```sh
python3 scripts/check_source_processing_layout.py
```
