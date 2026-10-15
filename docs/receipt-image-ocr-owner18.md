# Worker18 local receipt image OCR

```json
{
  "prior_branch": "feature/stock-receipt-consumer-18-20261014",
  "prior_head": "cca1077cdd47e88e97c42f557d74cfc8527ddd15",
  "status": "",
  "main": "8652b312ce7989c5e4f2d49ae765d5d8daf5841d",
  "index": "4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389",
  "fetch_utc": "2026-10-14T16:34:34.776175+00:00",
  "fetch_exit": 0,
  "base": "4693cbc3fe17cdde2e292e6eb00cd83769ee45ae"
}
```

## Requirement and local runtime

Original PDF02 pages5–6 were read from the original research report. P1-01 calls for user-reviewed receipt/label OCR, duplicates, field extraction and minimal image retention without auto-confirmed purchases. Page6 distinguishes private imports from publication rights. DATA-10/TRUST-02 remain owner admission/privacy dependencies; no sample CSV becomes permission.

Available local runtime: /bin/tesseract5.3.4 (eng data), Pillow and DejaVuSans font; no install/provider/upload. Python module emits untrusted tokens/coordinates/confidence, explicit line review and retention instructions. OCR confidence is engine-reported confidence, not calibrated probability, accuracy or field identity. Label images can use the same bounded extraction, but label-specific field classification/device acceptance is not implemented.

image_proposal(bytes,context,extractor=local_tesseract,ledger=()) requires current account receipt-review consent, source private-use rights and explicit ownership. Trusted owner must establish those predicates; a client claiming them is not admission. Input3MiB max, PNG/JPEG single-frame,8Mpx max,4096 tokens,200 lines,2000chars per line. Native OCR timeout15s; TSV accepted only up to1MiB. Output-file cap is checked after local engine execution, not a filesystem quota. Private TemporaryDirectory decoded metadata-free PNG/TSV always removed on context exit; caller input bytes remain caller-owned. No input path deletion, image retention write, logger or external transport. Original is never kept by this module.

Coordinates are pixel boxes for the decoded input; words grouped by explicit engine line identity, kept in reading order. Extracted name/quantity/unit/price/receipt-ID fields default unknown. Numeric OCR text does not prove pack quantity, price/currency, expiry or purchase authority. review_proposal requires confirmation and an include/exclude decision for every line with exact IDs, preserves source tokens, accepts explicit user name/quantity/unit and optional price lexical amount+currency+basis/purchaseDate. Price fields remain user assertions; no parsed/inferred pack conversion, total arithmetic or legal-currency qualification. Missing quantity/unit remains null. Purchase date is distinct from expiry.

Duplicate ledger keys combine account/source and image SHA256 or explicit reviewed receipt ID. Receipt IDs must identify the merchant receipt within a source scope, not an OCR guess. Changed crops/re-encodings are not detected by image bytes; user receipt identity can cover them only when supplied and reviewed. Owner storage must atomically check/commit both identities; no transaction/persistence here. Ledger removal/retention ends remembered deduplication. Proposal objects are caller-held plain data; storage/load validation and revision/immutability remain owner responsibilities.

## Existing helper composition and adoption contract

prepareReceipt/reviewReceipt/receiptRetentionPlan from retained exacte3149b555789231b525b732e5b127fb7ba8d578d:public/receipt-review-model.js were inspected. SHA2561cbc78ce66253d1d429f3a9894166cf9ae354ccbe7bc5ad8e745a607b2b0e34a. Python image_proposal exports helperInput matching prepareReceipt (digest derived from image bytes, source/account, bounded lines/confidence, image:null). review_proposal emits helperReview for reviewReceipt; reviewedFields contains separate explicit user price/date extensions. Exported JS contract was actually invoked using the retained immutable helper and injected synthetic evidence: prepare, review with null quantity, deadline deletion all passed. That was a separate compatibility probe, not a mandatory hidden-Git dependency of Python tests/runtime, helper adoption, or helper acceptance.

Owner must supply reviewed JS helper package/import through owner-controlled integration after independent review, run source/account policies at each use, render original tokens/uncertainty, bind corrections to exact proposal/revision and atomically persist private review+ledger. RetentionPlan maps to helper retention semantics: original default delete, explicit current retainImage consent/deadline required (no later than proposal); expiry/withdrawal/invalid permission means delete proposal/tokens/ledger and retained original. Plans are instructions, not proof of storage/backup/cache deletion. Actual source original should remain only in an explicit owner store under that policy; this module never persists it. Neither helper nor Python output is received-stock authority. Reviewed stock adapter cca1077 and its rereview remain separate. No stock, central handler/schema/UI, source admission or production writes.

## Focused evidence and limits

PYTHONDONTWRITEBYTECODE=1 python3 tests/global-data-validation/test_receipt_image_ocr_owner18.py: final6/6pass, no skips. Cases cover coordinates/source text+user corrections, explicit price/date fields, image/receipt/account duplicate scope, denied current ownership/consent/rights before extractor, input/coordinate/review/scope bounds, retention withdrawal/expiry/default original deletion, and actual local engine through exported proposal/review/retention. One distinct synthetic generated receipt template was exercised, repeated in three focused runs as narrow policy/price changes were added; no real receipt or additional corpus/sample acquisitions. Actual engine recognized RICE with bounded coordinates/confidence; all numeric text remains unknown fields pending review. No confidence threshold implies correct receipt parsing or pack/price certainty. Synthetic tests do not qualify real receipts, device/browser usability, handwriting, languages, OCR accuracy or food safety.

The initial attempt to write tests failed because reserved tests/global-data-validation directory did not exist; directory was created, no prior files replaced. Test/runtime caches disabled. No broad tests/server/SDK/nativeprovider/network OCR calls. Generated image held in memory only; engine decoded temp files removed. Dependencies are existing installed runtime, not hermetic clean-machine provisioning. Default OCR test explicitly skips with actualOCRblocked if Tesseract absent; injected path is then the only qualified behavior. Pillow/font availability are declared local dependencies.

READY FOR DIFFERENT WORKER25 REVIEW after collections correction; no independent PASS yet. Current source stock-fix branch/pin and prior corpus/CoFID/helper artifacts preserved. Primary main/index and owned-three-file scope asserted before/after checkpoint. Private normal branch backup/readback required, no merge. ProductionSTOP and source/whole105 withholding remain. Supplied unrestricted filesystem/network enabled/mandatory auto_review unchanged; separate approval policy unavailable.

## W25-OCR1 correction — 15 October 2026

Different-author Worker25 review c2faa4ce5e642d540945cb9f5f2ae6c781b3b1ab found P2 capture/release inconsistency at source f078a3ea0e6e7e3c0321e398d506115aaa525a86. Both exact synthetic probes were reproduced before edit: extractor changed account/source and emitted a proposal without corresponding rights/consent, and consent withdrawal during extraction still returned needs-review. No raw token/PII logs or stock writes.

image_proposal now captures strict bounded own plain context data before first extraction/delayed operation. Custom mappings/hooks/unsupported objects reject. Emission uses that detached account/source/deadline. New required keyword recheck is a trusted owner callback reading current authenticated account, ownership, consent, rights, retention and authoritative clock. Missing callback fails before extractor; duplicate-image response also rechecks. After token validation, immediately before private output release, current admission is gated again and exact captured account/source/deadline must match; current clock cannot roll back. Valid advancing time is allowed. A callback simply returning a stale snapshot is not authoritative production admission. Tests returning live synthetic context qualify ordering only.

Focused new regression covers independently valid-but-different scope, withdrawal, expiry, ownership loss, missing provider, custom context rejection, mutation of stale client context while authoritative owner remains at captured scope, and advancing owner time. Passed one injected regression invocation. Only changed-API native positive test was then run with one synthetic image/Tesseract, passed. Old six-case suite was not repeated. Reviewer previously qualified native six-token/temp success+timeout cleanup and those prior receipts remain historical, not new acceptance. All existing 1MiB post-execution cap, dependency/resource quotas, exact-byte duplicate limitations and caller retention/deletion obligations remain unchanged.

No central metadata/state/caller adoption. Python test wrapper now explicitly supplies the synthetic live admission callback; production owner must implement fresh protected authority and fence release/persistence against concurrent revocation/account switching. Synchronous recheck alone does not implement a distributed policy transaction. Retained helper packaging/compatibility and stock adapter remain separate review gates. Same branch, original source retained as parent; successor needs SAME25 exact-delta rereview and private backup/readback before any caller adoption. ProductionSTOP unchanged.

## Fresh standalone composition

```json
{
  "source_branch": "feature/receipt-image-ocr-18-20261015",
  "source_head": "7d2c61b3f69754179f1b6c64dd46df5d03c2a046",
  "status": "",
  "main": "8652b312ce7989c5e4f2d49ae765d5d8daf5841d",
  "index": "4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389",
  "fetch_utc": "2026-10-14T17:37:09.972157+00:00",
  "fetch_exit": 0,
  "base": "4693cbc3fe17cdde2e292e6eb00cd83769ee45ae"
}
```

Root selected source7d2c61b after SAME25 narrow12-check scoped PASS, review5a90199bc60946bdabf09ff89d235d838714ad2e. Normal attributed source cherry-picks onto fresh locked develop; runtime/test bytes unchanged. Different SAME25 composition review and root acceptance are pending. Historical receipt below/above retains original source base and limits. This is standalone code composition, no consumer adoption or distributed authority/deletion/resource qualification. Published-clone checks use only declared three authored files and existing Python/Pillow; Tesseract/font/eng prerequisites remain external and unchanged native tests are not rerun.

## Delivery composition — 15 October 2026

DELIVERY-20261015-OWNER18 composes the preserved three-file candidate998f76e302400298ac1b2600e7c1f792c4924069 onto locally available merged develop46b989ac1ec93e3483b36f64b8a267e5a60ac528. Source commits are replayed with attribution; corrected runtime/test bytes remain identical to source7d2c61b3f69754179f1b6c64dd46df5d03c2a046. Earlier base/publication records above remain historical. Independent review of this new candidate is required.

Portable validation selects the six injected-extractor tests, including current admission/revocation regression; it excludes test_one_actual_synthetic_receipt explicitly. Native extraction is not qualified by that selection. Pillow remains required even for injected image decoding; native extraction additionally requires Tesseract, eng trained data and the declared font. Existing post-execution TSV cap is not an OS resource quota. No provider jobs, real images, user data, helper lookup, stock adoption, permission expansion, deployment or source-rights grant is involved. All authoritative owner, private admission, retention, atomic ledger and distributed revocation integration obligations above remain in force. Exact validation results are supplied with the candidate handoff.

## PR16 discovery correction

Standard root unittest discovery does not recurse into the non-package global-data-validation directory. The third-party-services workflow now explicitly runs the six portable ReceiptImage methods below after installing the test extra, which now declares Pillow for image decoding. It leaves ordinary discovery and other nested suites unchanged. No private dataset, historical Git object, native engine, font or trained language data is required by this invocation.

```sh
python3 -B tests/global-data-validation/test_receipt_image_ocr_owner18.py -v \
  ReceiptImage.test_bounds_scope_and_explicit_review \
  ReceiptImage.test_capture_and_current_recheck \
  ReceiptImage.test_duplicate_image_receipt_and_account_scope \
  ReceiptImage.test_permissions_precede_extraction \
  ReceiptImage.test_retention \
  ReceiptImage.test_unknown_source_and_user_corrections
```

The native test_one_actual_synthetic_receipt is intentionally excluded. Its historical evidence does not qualify this correction's native environment. The explicit method list fails if a selected method disappears; new portable tests must also be added to the CI list. No runtime, rights, admission or caller-adoption changes are made.
