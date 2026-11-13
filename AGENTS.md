# OffMenu project instructions

This repository contains the OffMenu product, its source contracts, examples,
build tools and tests. Work from the selected checkout and record its branch,
commit and local changes before editing. Preserve unrelated work and existing
source/data custody. Never infer that a source change authorizes a deployment,
account action, dataset read or permission change.

## Source and ownership

Use `develop` for reviewed integration and `main` for approved releases. Work on
an isolated `feature/` or `bugfix/` branch. Retain one integration writer and
independent review of the exact candidate. Reconcile uncertain external effects
before retrying an operation. Do not force-push, reset, clean or discard work to
establish a baseline.

Read [the repository standard](docs/standards/repository.md) and
[`repository-standard.json`](repository-standard.json) before changing structure.
Structural changes require a versioned decision and affected-consumer updates.
Product release requirements are in
[`config/release-policy.json`](config/release-policy.json). Freeze the exact
release candidate, source tree and artifact hashes; repairs produce a new
candidate. Promote only a reviewed, qualified candidate to `main`, verify its
canonical tree and immutable tag, and keep `main` static between releases.

## Local development

Use the ordinary project environment described in
[the maintainer guide](docs/maintainer.md). A fresh product checkout must build
without another project checkout, host-specific paths, service credentials or
an orchestration service. Product deployment and optional provider features have
their own configuration; a build does not activate them.

Run the source checks appropriate to the change:

```sh
python3 scripts/check_repository.py
python3 scripts/check_final_layout.py
```

Use focused behavior tests for changed interfaces. Imports, build wiring,
packaging and generated assets need their affected checks; run
`npm run check:generated` before rebuilding so generation cannot hide drift.
Reuse equivalent valid evidence rather than repeating unrelated suites. Record
commands, exits, source/artifact hashes, skipped checks and remaining limitations.
A layout check or source merge is not full product, device or deployment proof.

## Product boundaries and privacy

Keep the browser and Worker under `apps/web/`, the retailer extension under
`apps/retailer-extension/`, installed Python packages under `src/`, and product
contracts under `contracts/`. Source adapters preserve original identities,
units, unknown values, licences and rights. Acquisition, normalization, export
and publication are distinct operations; no code or fixture grants source rights.

Do not commit credentials, private account records, raw datasets, runtime
receipts, databases or screenshots. Use authored synthetic fixtures for tests
unless an exact source and operation is separately qualified. Preserve current
authentication, account isolation, consent, retention and withdrawal checks.
Never weaken them to obtain a passing result. Do not start services, install
models, create paid usage, dispatch hosted workflows or deploy the product
without the applicable user authorization.

Before moving or removing files, classify product source, generated output,
private runtime data and historical evidence. Preserve necessary originals and
hashes in the approved custody location outside the product source tree. Such
preservation does not prove transfer, adoption or runtime readiness. Keep held
private paths and consumers intact until their actual owner completes a handoff.

## Handoffs

Report completed source changes, actual checks and known blockers promptly.
Keep project delivery with its current owner; delegates receive a bounded scope,
immutable source, owned paths and required output. Do not create a competing
writer or claim completion from a proposed task, submitted request or unverified
receipt. Communicate a concrete missing input and continue eligible independent
work within the user's scope and existing access limits.
