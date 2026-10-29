# ADR 0002: Source tools and reproducible delivery

- Status: adopted after source and implementation review
- Standard: repository 1.1.0
- Supersedes: the naming-baseline classification and manual-action disposition in ADR 0001

Discovery found a cohesive source-processing toolset, schemas and 384 local
Python tests under the ambiguous `manual-action/` root. These are developer tools,
not unstructured manual evidence. Move 42 source/schema/test files together into
`tools/source-processing/`, and their nine guides to lower kebab filenames under
`docs/source-processing/`. Update their schema and browser-test consumers. Keep
six pinned native fixture files byte-identical, including historical internal
paths. The migration verifier makes those obligations reproducible.

The 137 original naming exceptions were not all coding debt. Four private Python
modules and Netlify `_headers` are valid conventions; recognize them directly.
Rename the nine avoidable uppercase current guides. Retain 71 exact published
command paths and 52 custody/imported/pinned identities, with category and reason
for every exception. Do not rewrite immutable evidence or rename CLI contracts
speculatively. New exceptions still require a versioned decision.

Retain the actual Python packages and authored browser/Worker/extension roots:
their packaging and bundler consumers establish those boundaries. Retained
unfinished integration seams remain separate and inactive. Generated output,
installed dependencies, source provenance and private runtime data have explicit
dispositions in docs/development/root-layout.md. This is a selected safe migration,
not a claim that folder count alone establishes maintainability.

Use a committed transitive dependency lock and scripts/bootstrap_delivery.py to
create/check `.venv-delivery/` on Python 3.12. No temporary-directory environment
is a supported prerequisite. The bootstrap never installs into system Python or
configures services/credentials. Its clean local environment must pass all
locked-version checks, dependency consistency, and the delivery behavior suite.
