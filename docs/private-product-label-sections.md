# Private source label sections and ingredient fragments

This standalone helper retains the selected PR84 label extraction intent. It
accepts caller-selected text only; it installs no product route, corpus reader,
ingestion job, model invocation or canonical ingredient mapping. Existing
`product_detail_import`, `product_detail_query` and federation contracts continue
to supply complete source records, field states, evidence and exact observation
bindings. Their split APIs are retained rather than duplicating the old PR84
monolithic product store or scanner exports.

`extract_label_sections` returns every character in source order, including
unclassified gaps. A marker or candidate opening span is a source claim, not
allergen safety, dietary certification or a verified ingredient identity.
`extract_ingredient_components` requires an explicitly selected start/end span.
It retains nesting, separators, character and UTF-8 byte offsets, text hashes,
unknowns and explicit quantity lexemes without interpreting their value or basis.

Commas inside a value recognized by the existing quantity grammar are retained:
`Sugar 1,5%, Salt` has two components, and the first keeps value `1,5` and unit
`%`. Decimal dots, decimal ranges and nested quantities retain the same source
coordinates. `Sugar 1,5, Salt` has no recognized unit and keeps both commas as
component separators. Semicolons and commas outside recognized values remain
separators. Existing byte, node and nesting limits raise errors rather than
silently truncating the source.

The native exact-barcode lookup also bounds its complete canonical response,
including no-match metadata. The final check follows full artifact verification;
the existing early per-match bound remains. An exact byte cap succeeds and one
byte less fails. Caller transport wrappers need their own bounds.

Focused verification uses generated fixtures only:

```
python -m unittest tests.test_native_barcode_lookup tests.test_product_label_sections
```

No real source processing, qualification, runtime activation, English/gold
admission or UI/provider configuration follows from these helpers or tests.
