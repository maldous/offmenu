# Source-local category consumers

The reviewed pure modules in `public/source-categories` provide current-source category labels and declared parent candidates, plus a separate source-root type/icon candidate. They perform no network, storage, profile, product join or shared-resolver mutation.

```js
import {compileCategoryConsumer, compileTypeRules} from './public/source-categories/index.mjs';
const categories = compileCategoryConsumer({crosswalk, taxonomy});
const types = compileTypeRules({taxonomy, rules});
const labelView = categories.resolve('off', categoryId, {language: 'en'});
const typeIconCandidate = types.resolve('off', categoryId);
```

Callers must verify the selected input bytes and source-operation permission before compilation. Inputs and returned views are isolated snapshots. Preserve all declared parents, missing labels, ambiguity and fallback outcomes. The two outputs remain separate; neither establishes ingredient, product, allergen, nutrition, recipe or historical identity.

The accepted local bundle is recorded in the existing OffMenu permanent ledger. Its pinned `query.mjs` reads the retained, qualified OFF taxonomy and selected 6,392-ID crosswalk without fetching or processing products. Raw taxonomy and bindings remain outside Git. No HTTP, MCP, normal-app route or product classification is activated by these modules.

The eight SVGs are original OffMenu Worker13 geometric artwork, independently reviewed for this source-category presentation scope. `source-type-rules.json` changes only the reviewed icon filesystem paths to project asset URLs; SVG hashes, root IDs, English root labels, rights IDs and conflict behavior are preserved. Static packaging and a caller remain necessary before those URLs are served by an application.

Source taxonomy attribution: Open Food Facts, https://static.openfoodfacts.org/data/taxonomies/categories.full.json, retained snapshot SHA-256 `e069022e0cab0dd4034f0283c01783fa1c234daab72d3e3e137cf272898ed9aa`. Keep the accepted source-qualification, attribution and ODbL/DbCL packet with derived-data distribution. This does not claim rights to OFF artwork or logos.

The reviewed product-category adapter adds a retained source-product reference path for type illustrations. It preserves the genuine source reference and separate artifact, JSONL line, archive, audit and parsed-field hashes. It does not convert that reference into an identifier observation or widen the existing photo and ingredient paths.

A trusted server producer must await its exact current source/output decision before the synchronous adapter call. The selected operation, source eligibility and a browser-supplied status are insufficient by themselves: existing authentication and the current field, evidence, target and runtime binding must also be checked. Missing or mismatched evidence retains fallback. Source integration does not claim a displayed product, current-user acceptance or normal-app activation.
