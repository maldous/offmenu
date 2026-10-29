# Documentation for maintainers

Start with [setup, checks, local run and configuration](maintainer.md), then
[operations and integration](operations.md). Use the accepted source/release
receipt for the work; dated reports do not establish current activation.

## Code and workflow map

| Area | Entry points and guides |
| --- | --- |
| Local CLI / small Python UI | `offmenu/cli.py`, `offmenu/server.py`, `offmenu/web.html`; [local demo](maintainer.md#local-python-demo-and-server). |
| Browser app / Worker | `public/`, `cloud/handler.mjs`, `scripts/build.mjs`; [build outputs](maintainer.md#checks-and-generated-files). |
| Retailer extension | `extension/popup-source.js`; [extension guide](../extension/README.md). |
| Authentication seam | [foundation](better-auth-foundation.md), [unmounted runtime seam](better-auth-runtime-seam.md); source integration is not activation. |
| Local originals / static delivery | [curation architecture](curation-architecture.md), [source acceptance](source-acceptance-contract.md), [refresh/acquisition](refresh-acquisition-contract.md). |
| Private source-only processing | [ingredient ingestion](ingredient-ingestion.md), [`tools/source-processing/`](source-processing/README.md) source interfaces; selected inputs and review are required. |
| Work and action status | [automatic canonical-ledger tracking](maintainer.md#automatic-work-tracking); GitHub PRs are code review, not a replacement task tracker. |

## Historical and specialist evidence

The [corpus/research index](OFFMENU_CORPUS_INDEX.md), dated handovers and
consolidation reports preserve their original provenance, paths and status cuts.
Use them as historical evidence, not current setup, worker allocation or release
commands. Foo runner documentation describes a separate selected execution
workflow; it is not required to build or run the small local demo. AI instruction
files have their own maintenance lane and are not a substitute for this human
maintainer guide.
