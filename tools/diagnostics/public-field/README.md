# Public field diagnostic representation

The reviewed capture helper retains 18 selected public field envelopes and five
binding containers. Nested keys are source data, including language tags and
nutrient identifiers. Null, absent, unknown and not-loaded values remain distinct.
The helper does not grant source access or qualify ingredient, nutrient or
canonical relationships.

The local diagnostic response formatter is an optional representation of the
existing identifier detail operation. It runs after that operation's existing
authorization and validation. Ordinary requests, status responses, failures and
unavailable details retain their original response. A diagnostic client explicitly
requests `application/vnd.offmenu.public-field-capture+json`; the separate output
shape carries field envelopes and bindings, never envelopes inside raw
`record.data`. Current selected rows and observations must still match.

The formatter makes no request and opens no source. Its product and output bounds
fail explicitly. It is generic across eligible returned products; the exact
retained regression covers one product and does not establish dataset coverage.
Copying these files does not register a route, publish source data or change a
runtime. Runtime adoption is a separately selected local composition operation.
