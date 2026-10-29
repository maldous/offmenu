# Web source and deployment layout

The JavaScript application now has explicit source, asset, and server boundaries:

```text
apps/
  web/
    src/              # Browser modules, shared models, and retained candidates
    assets/           # HTML, CSS, JSON, icons, fonts, and licence notices
    server/           # Worker handlers, schema/migrations, selected native hosts
  retailer-extension/ # Authored extension and checked generated popup
deploy/
  netlify/public/     # Curated-publication landing template
  auth-return/        # Separate authentication return-page adapter
integrations/
  staged/auth/        # Unmounted reviewed authentication source preparation
  staged/private-product-lookup/
  candidates/         # Retained unmounted domain and local-adapter candidates
```

The root `package.json` and lockfile remain the JavaScript workspace entrypoint.
This migration changes physical repository paths; the build retains existing
public asset names, Worker routes, extension archive layout, and authentication
return behavior. Relocating a staged component does not mount it.

`scripts/build.mjs` bundles `apps/web/src` entrypoints, reads static material
from `apps/web/assets`, and composes the Worker with `apps/web/server/handler.mjs`.
Outputs remain ignored under `dist/`, `apps/web/server/generated.mjs`, and
`deploy/auth-return/i18n.js`. The extension's committed generated popup remains
checked against its source by `npm run check:generated`.

The i18n extractor scans browser modules, server modules, extension markup and
auth-return markup at their new locations. Its authored English catalogue is
`apps/web/assets/locales/en.json`; `docs/i18n-coverage.json` records the current
source paths. The Arabic translation module remains importable source under
`apps/web/src/locales/ar.js`. Message and translation coverage are not expanded
by moving these files.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check:web-imports
npm run check:generated
npm run i18n:check
npm run build
node integrations/staged/auth/build.mjs
```

`check:web-imports` parses maintained modules and verifies relative imports
without executing or mounting them. It separately reports the existing unmounted
production-scanner worker's absent `scanner-decode.js` helper. That source hold
is not a new migration defect; introducing the candidate into a runtime build
closure makes the check fail. Historical snapshot fixtures and archived source
retain their original internal paths and hashes. Native identifier host and
private-lookup readers retain their explicitly pinned foreign-checkout and
source-selection dependencies.

Focused tests exercise migrated scanner models and WASM, selected-source photos,
label scenarios, auth/session boundaries, candidate and diagnostic modules,
extension regeneration, portable CLI behavior, and disposable local Worker/D1
routes. They do not accept unfinished scanner UI work or production source use.
