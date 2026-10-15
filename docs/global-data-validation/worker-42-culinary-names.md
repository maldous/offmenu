# Current portable invocation (PR15 follow-up)

The executable now reads body-free `portable_inputs` from the tracked report adjacent to this document. Historical commit IDs below are provenance labels, not required Git objects. No Git subprocess is executed. Original recipe bodies and rights files remain external and are never uploaded by this change.

```
python3 -B scripts/global-data-validation/worker-42-culinary-names.py --recipes /your/retained/recipe-release --foodon /your/retained/foodon-release --source-root /your/retained/root
python3 -B -m unittest discover -s tests/global-data-validation -p test_worker42_culinary_names.py
```

All three data paths are explicit; `--evidence` optionally selects another pinned metadata bundle. Source/rights paths within that bundle must be relative to source-root; absolute paths and traversal/symlink escapes are rejected. Missing files raise a path-specific error. Source hashes, original body/revision/page/date/locale attachment and rights-witness checks remain mandatory. Supplying a path or a synthetic fixture grants no source qualification.

The nine focused tests use test-authored temporary synthetic bodies, rights witnesses, normalized records and FoodOn packets. They need neither private Git objects nor fixed workstation data, and cover positive execution, all five attachment mismatch fields, missing fields, locale, custody/rights tampering, source path confinement and missing dependencies. They do not claim to qualify any real release. The retained historical report below remains bounded evidence, not a new run or future-head acceptance.

Both pre-fix issues were reproduced against merged PR15 bytes: a standalone initialized snapshot failed5 tests with6 errors on hidden Git evidence; supplying original metadata but denying the fixed external corpus caused a targeted FileNotFoundError. This does not prove absence from every repository ref. After-fix checks run the focused suite in a standalone snapshot using only the four declared paths. No broad suite, workflow/dependency changes or OCR tests. Worker18 owns its separate explicit OCR workflow invocation.

SAME52 independent review remains required for the new immutable candidate. The sole integration writer controls any PR/develop change; no adoption, deployment or source admission is authorized here.

---

# Worker 42 culinary name assertions

Fresh locked develop base 5f5bdb6ae716cbf80fab1e174d1af2e354468ead; branch feature/culinary-names-42-20261015. Old source/qualification/local-validation branches remain preserved.

Run `python3 -B scripts/global-data-validation/worker-42-culinary-names.py` for a read-only stdout report. Worker53 commit 8d468982f7bc905af01d5262c8eabb8db7051e96 supplies exact retained line/index/id references; Worker56 commit 3e7b381 supplies the FoodOn contract. Before/after release and manifest hashes match. Nine recipe records (hi/ar/cs/el/fa/zh) plus 991 FoodOn concepts stay within 1,000 retained records; traversal of compressed lines does not parse unselected recipe lines. Eighty-eight ingredient-name assertions yielded zero exact-locale matches in this bounded prefix. No claim about the full concept index is made.

Unicode retained names stay unmodified. original_lexeme is explicitly marked a retained normalized name; source_original_lexeme remains null pending original publisher-body verification. Original statements are referenced by ingredient coordinate and hash; no recipe body or directions are copied. CC BY-SA4.0 provenance and rights URLs gate lexical output; absent rights blocks lexeme output. FoodOn CC-BY4.0 citations/revision/file digest are checked. Similar spelling, transliteration, synonyms or translation do not establish ingredient identity, preparation form, nutrition/diet equivalence or origin. Even an exact locale match is only a candidate. Amount/unit parsing belongs to Worker54.

Missing qualification: locate and hash the exact original wiki slot body for each recordId/revisionId in retained recipe-wikis-20261013 language directories, then verify ingredient lexeme/coordinate and source rights independently. Body presence is not claimed absent; exact body identity is not verified by this adapter. Two focused tests pass on Unicode/locale boundaries, candidate uncertainty and rights blocking. PDF02 pages7/9 and PDF03 page8 informed source-role/reuse boundaries (PDF skill, read-only extraction).

No source acquisition, no raw corpus copies, no shared schema changes, no admission. Mandatory auto_review retained. Whole105 and production recipe STOP preserved. Private-origin backup withheld: gh CLI is unauthenticated, so private visibility cannot be verified; no new credentials requested or public push attempted. Immutable independent review is required before merge/publication.

## Original body proof follow-up

Worker53 candidate 6bf021a81d7660ae48b3eeba3656aa656f3553bf supplied six original-body proofs. The adapter now independently verifies local file hashes, JSON slot coordinates, page IDs, revisions, timestamps, UTF8 body digests and publisher rights declarations, with before/after checks. Greek uses the pinned linked-revisions file. Matching normalized provenance hashes/revisions are checked. No bodies are copied into artifacts. The current run reads nine normalized refs, six original bodies and 985 FoodOn concepts (1,000 total), superseding the earlier 991-concept count. Source name lexeme extraction remains unverified; exact body custody alone does not prove an ingredient-name crosswalk. Three tests pass. Three other normalized refs still lack original-body proof. Independent review and all production/admission stops remain.

## Normalized attachment guard correction

Owner42 delivery starts from exact merged develop46b989ac1ec93e3483b36f64b8a267e5a60ac528 on feature/culinary-names42-attachment-guards-20261015. Old candidate4a6bf717 and its branch remain unchanged. Worker52 review504e09d6234bb30228ad0f4842ea5eea6145c848 requested page ID/date/source-locale guard corrections; its old-head verdict remains changes requested.

The adapter retains verified proof source_id/language and rejects normalized recordId, sourceDate or originSourceId mismatches before proof attachment, alongside the existing body hash/revision checks. Declared normalized locales must include the verified source locale; proof source ID must agree with that source locale. No translation or origin claim follows from this check.

Five focused tests pass. Actual-run in-memory mutation subcases reject page ID/date/source ID as well as body-hash/revision mismatches with original files unchanged. Additional probes reject missing provenance fields and conflicting declared locale. The bounded actual retained run still produces9 recipe refs,6 original witnesses,985 FoodOn concepts,88 assertions and55 body-bound assertions. Three refs remain unverified. Before/after source hashes match; source_original_lexeme remains null, original crosswalk blockers remain and planning stays false.

This new head requires SAME52 independent review; no merge, public publication, release admission or production authorization is inferred. No source acquisition or shared fetch/ref repair occurred. Current result counts and pickup supersede historical sections above; historical work remains evidence rather than current acceptance.
