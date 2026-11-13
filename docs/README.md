# OffMenu documentation

Start with [setup, checks and the local demo](maintainer.md), then
[product operations and release boundaries](operations.md). These describe the
product source; source acceptance does not establish which version is deployed.

For personal REST/MCP, schema limits and offline executable examples, use the
[developer interface reference](developer-interfaces.md). For source-bound user
help, see [support and optional-service preferences](support-preferences-guide.md).
The help guide distinguishes reviewing a request from submitting it and native
help from optional third-party services.

## Product source map

| Area | Entry points and guides |
| --- | --- |
| Python CLI and small local UI | `src/offmenu/cli.py`, `src/offmenu/server.py`, `src/offmenu/web.html`; [local demo](maintainer.md#local-python-demo). |
| Browser app and Worker | `apps/web/{src,assets,server}/`, `scripts/build.mjs`; [web layout](development/web-layout.md). |
| Retailer extension | `apps/retailer-extension/popup-source.js`; [extension guide](../apps/retailer-extension/README.md). |
| Authentication | [Foundation](better-auth-foundation.md) and [runtime seam](better-auth-runtime-seam.md); optional source is not activated by building. |
| Source rights and curation | [Source acceptance](source-acceptance-contract.md), [curation architecture](curation-architecture.md), [refresh/acquisition](refresh-acquisition-contract.md). |
| Source processing | [Ingredient ingestion](ingredient-ingestion.md) and [source-processing interfaces](source-processing/README.md); exact selected inputs and permitted operations remain required. |
| Product structure | [Repository standard](standards/repository.md), [root layout](development/root-layout.md), [Python layout](development/python-layout.md). |
| Verification | [Validation workflow](development/validation-workflow.md), [test layout](development/test-layout.md), [generated assets](development/generated-assets.md). |

Maintained guides describe current product responsibilities. Frozen evidence
preserved elsewhere retains its original identity and scope; it does not become
a build dependency or establish current product behavior. Keep private data and
operational receipts outside tracked product source.
