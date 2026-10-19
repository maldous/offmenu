# Fetch, parse, normalize, translate

The owner pipeline is `fetch -> parse -> normalize -> translate`.

This amendment implements only the first two explicit stages. It does not provide a `staging` command, pretend that normalization or translation has run, or use successful parsing as a condition for collecting a permitted original.

## Fetch

`~/offmenu-global-collection/fetch` acquires only the exact permitted source requests that do not already have a verified original or a blocking intent. It reuses existing verified private originals and verifies source-bound retained file hashes and exact extents with bounded streaming reads. Mandatory framing and bounded format-safety checks in the approved acquisition contract remain in place. Fetch does not invoke the extraction worker, materialize parsed tables/text, run Poppler traversal diagnostics, or probe parser versions. Verification-only scope is reported as retained, verified collection, without an extraction-held failure. Media sniff observations remain metadata, not proof of semantic or archive validity.

The existing handoff002 source selection, holds, current claim checks, one-writer lease, failed intents, original bytes, and acquisition provenance remain authoritative. A changed version or command name never clears a failed request. The five previously failed requests cannot repeat GETs merely because the private-file Vary rule is corrected. Inactive header diagnostics and Taiwan acceptance require their separately reviewed exact configuration before they can run.

## Parse

`~/offmenu-global-collection/parse` operates on already-held originals using current source-bound read/extraction contracts. It resolves exact existing verified private custody with a reuse-only path. An absent original, changed provenance, failed intent, partial body, or conflicting claim cannot fall through to source acquisition. There is no acquisition scheduler or source HTTP transport in parse. Parser workers independently rehash and check their originals under the existing bounded memory, output, deadline, and archive traversal limits. The reviewed OPC relationship resolution correction is included in this stage.

Parse can run now on originals already received, independently of unresolved acquisitions. Its current selection is the set of explicit source-bound extraction contracts; a verification-only row does not silently gain extraction authority. Unselected extraction is not a failed collection. The report does not claim every retained file, country, type, or multilingual source is parsed. Within the 998-row extension, 10 structural rows have selected extraction contracts; 978 other read-eligible rows are skipped for parse in this first implementation, and 10 exclusions remain held. The 978 are not permanently prohibited from parsing: follow-on eligibility review must distinguish actual source-specific no-read/no-extract or mandatory-agreement restrictions from deliberately unselected extraction and missing parser parameters. Existing authorized preparation contracts outside that extension remain available.

The existing parallel parser pool is retained. Concurrent fetch and parse processes are not supported: both acquire the same owner writer lease. Complete one invocation before starting the other. Worker parallelism does not weaken custody serialization or enable an automatic second command.

## Commands, receipts, and compatibility

The installed `run` command is a compatibility alias to fetch. It does not run the old combined acquisition/preparation pass. Existing source directories, custody files, and immutable result/checkpoint files remain preserved. Historical combined reports without an execution-stage label continue to validate.

New reports and publication receipts identify `executionStage` as `fetch` or `parse`. Each stage has its own latest-result pointer, so `fetch --publish-only` and `parse --publish-only` cannot publish the other stage's latest report. Publish-only never runs collection or parsing. Terminal progress distinguishes network body bytes from verified local payload bytes, fetch verification workers from parse preparation workers, and verified original records from parsed outputs. Country/type completion remains unknown unless separately established.

## Downstream contract: normalize

Normalization is not implemented in this delivery. Its input will be verified parsed artifacts with their source schemas, original language text, units, identifiers, country variants, and immutable original/parse provenance. It must interpret and translate source-language variables and values into a validated canonical English gold-standard corpus covering standard ingredients, recipes, dietary information, and controlled values. Shared concept identifiers, semantics, original wording, country-specific variants, and transformation provenance must remain traceable. Ambiguous mappings must remain explicit and reviewable; translating a label alone does not establish semantic equivalence, validate a recipe, or supply missing nutritional evidence.

## Downstream contract: translate

Translation is not implemented in this delivery. It will derive multilingual corpus standards from the canonical English gold-standard reference produced by normalize. Derived language forms must retain the same concept identifiers and semantics, source provenance and country-specific variants. Language-specific renderings must not overwrite the English reference or original source language. Validation and review requirements for these later stages will be specified before implementation; neither stage is silently performed by fetch or parse.

### Future semantic acceptance examples

A shared scrambled-eggs-on-toast concept should resolve across Australian, English, Portuguese, and Chinese menus without losing differences in ingredients, allergens, nutrition, preparation, or portion evidence. An unknown attribute stays unknown rather than being supplied by translation or a presumed standard recipe. Recipes require shared culinary-action definitions and localized instruction templates, with original wording, country variants, source provenance, and unspecified parameters preserved. These are acceptance requirements for later normalize/translate work, not capabilities claimed by this amendment.
