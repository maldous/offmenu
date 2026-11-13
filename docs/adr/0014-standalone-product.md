# ADR 0014: Standalone product repository

- Status: candidate for independent review and qualification
- Repository standard: 3.0.0
- Source baseline: `2ce27c847760ebacfdc2a6914f5a50a92209e04c`

## Decision

Keep the repository focused on OffMenu: installed Python packages, browser/Worker
and extension source, product contracts, offline examples, build tools and tests.
Installation and a complete local build must work from a real Git checkout using
its declared public dependencies, without another project checkout, service
credentials, host paths or a coordination service.

Move shared coordination/session infrastructure and its operational history out
of the tracked product tree. Preserve necessary originals and their hashes in
private custody outside the product checkout before removing source paths. This
records local preservation only; it does not claim transfer to another custodian,
external source acceptance, service adoption or runtime changes. Existing Git
history is not rewritten by this change.

Replace contributor setup and agent instructions with self-contained product
commands and safeguards. Layout/naming checks are ordinary local scripts;
release requirements remain product-owned in `config/release-policy.json`.
Keep independent review, one integration writer, exact source/artifact identities,
uncertain-effect reconciliation and reviewed immutable releases.

## Product compatibility

Preserve product import names, CLI entry points, browser URLs, source identities,
rights/privacy semantics and optional provider features. Product deployment
configuration remains separate from build requirements. Unmounted integrations
stay unmounted. Source/data admission, authentication activation, device behavior
and production deployment are not established by a source reorganization.

Original qualified inputs and historical evidence retain their original scope.
A current source binding must not inherit stale dataset acceptance after a code
or path change. Private runtime files and held consumers are outside this tracked
source cleanup and retain their actual handoff requirements.

## Required evidence

Bind validation to the final candidate's source head/tree and dependency inputs.
Use a fresh independent Git checkout with a clean ordinary environment. Verify
locked JavaScript installation and the complete application build, then build a
Python wheel and exercise its declared imports/resources/CLI outside the source
checkout. Check the repository/layout contract, current links and materially
affected product behavior. Record all failures, skips and unrun boundaries.

A passing local build proves that source/build path only. It does not prove
hosted account/provider availability, real-data rights, runtime adoption or a
production deployment. This ADR remains a candidate until actual reviewed
acceptance; its existence is not a successful-build receipt.
