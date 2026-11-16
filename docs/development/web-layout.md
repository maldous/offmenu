# Web source and build layout

```text
apps/web/src/        browser modules and shared product models
apps/web/assets/     HTML, CSS, catalogues, icons, fonts and notices
apps/web/server/     Worker handlers, schemas and product server modules
apps/retailer-extension/
                     extension source and checked generated popup
deploy/netlify/public/
                     product curation landing template
deploy/auth-return/  authentication return-page adapter
integrations/        optional unmounted product components
```

The root `package.json` and lockfile define the JavaScript dependencies. The
application build retains product asset names, Worker routes, extension archive
layout and authentication return behavior. It does not require another project
checkout or service credentials.

`scripts/build.mjs` bundles browser entrypoints, reads local assets and composes
the Worker with `apps/web/server/handler.mjs`. A real Git checkout is required
because the build embeds HEAD. Generated outputs are ignored under `dist/`,
`apps/web/server/generated.mjs` and `deploy/auth-return/i18n.js`. The committed
extension popup is checked against its source before regeneration.

```sh
npm ci
npm run check:generated
npm run i18n:check
npm run build
```

The i18n extractor scans product browser/server/extension/auth-return source.
English inventory is `apps/web/assets/locales/en.json`; coverage is recorded in
`docs/i18n-coverage.json`. Arabic remains source translation with explicit
fallback, not a promise of complete coverage. Moving files does not translate
messages or qualify rendering.

`check:web-imports` checks relative imports without mounting components. An
optional staged authentication component has its own build procedure in the
maintainer guide. A retained unmounted component's prerequisites do not become
a service dependency of the product build.

Build success establishes compilation and asset packaging. It does not certify
hosted authentication, selected data-source availability, camera/scanner hardware,
browser layout or production deployment. Keep source-specific admission and
actual device/runtime evidence separate.
